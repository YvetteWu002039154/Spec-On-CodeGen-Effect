import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from opentelemetry import trace
    from opentelemetry.trace import Span, Tracer
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

T = TypeVar("T")
StateT = TypeVar("StateT")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GraphError(Exception):
    pass


class CycleDetectedError(GraphError):
    pass


class NodeNotFoundError(GraphError):
    pass


class ExecutionError(GraphError):
    pass


class InferenceError(Exception):
    pass


class CacheError(Exception):
    pass


# ---------------------------------------------------------------------------
# Caching System
# ---------------------------------------------------------------------------

class AbstractCache(ABC):
    """Abstract base class for cache implementations."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        pass

    @abstractmethod
    async def clear(self, pattern: str = "*") -> int:
        pass

    @abstractmethod
    async def publish(self, mailbox: str, message: Any) -> None:
        pass

    @abstractmethod
    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        pass


class InMemoryCache(AbstractCache):
    """In-memory cache implementation for testing and development."""

    def __init__(self, prefix: str = "", suffix: str = ""):
        self._store: Dict[str, Any] = {}
        self._ttl_store: Dict[str, float] = {}
        self._mailboxes: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self.prefix = prefix
        self.suffix = suffix

    def _make_key(self, key: str) -> str:
        parts = []
        if self.prefix:
            parts.append(self.prefix)
        parts.append(key)
        if self.suffix:
            parts.append(self.suffix)
        return ":".join(parts)

    def _is_expired(self, full_key: str) -> bool:
        if full_key in self._ttl_store:
            return time.time() > self._ttl_store[full_key]
        return False

    async def get(self, key: str) -> Optional[Any]:
        full_key = self._make_key(key)
        if self._is_expired(full_key):
            del self._store[full_key]
            del self._ttl_store[full_key]
            return None
        return self._store.get(full_key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        full_key = self._make_key(key)
        self._store[full_key] = value
        if ttl is not None:
            self._ttl_store[full_key] = time.time() + ttl
        elif full_key in self._ttl_store:
            del self._ttl_store[full_key]

    async def delete(self, key: str) -> None:
        full_key = self._make_key(key)
        self._store.pop(full_key, None)
        self._ttl_store.pop(full_key, None)

    async def exists(self, key: str) -> bool:
        full_key = self._make_key(key)
        if self._is_expired(full_key):
            self._store.pop(full_key, None)
            self._ttl_store.pop(full_key, None)
            return False
        return full_key in self._store

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        import fnmatch
        result = {}
        for k, v in list(self._store.items()):
            if self._is_expired(k):
                continue
            if fnmatch.fnmatch(k, pattern):
                result[k] = v
        return result

    async def clear(self, pattern: str = "*") -> int:
        import fnmatch
        keys_to_delete = [k for k in list(self._store.keys()) if fnmatch.fnmatch(k, pattern)]
        for k in keys_to_delete:
            del self._store[k]
            self._ttl_store.pop(k, None)
        return len(keys_to_delete)

    async def publish(self, mailbox: str, message: Any) -> None:
        await self._mailboxes[mailbox].put(message)

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        queue = self._mailboxes[mailbox]
        while True:
            message = await queue.get()
            yield message


class RedisCache(AbstractCache):
    """Redis-backed cache implementation."""

    def __init__(
        self,
        url: str = "redis://localhost:6379",
        prefix: str = "",
        suffix: str = "",
        db: int = 0,
    ):
        if not REDIS_AVAILABLE:
            raise ImportError("redis package is required for RedisCache. Install with: pip install redis")
        self.url = url
        self.prefix = prefix
        self.suffix = suffix
        self.db = db
        self._client: Optional[Any] = None

    def _make_key(self, key: str) -> str:
        parts = []
        if self.prefix:
            parts.append(self.prefix)
        parts.append(key)
        if self.suffix:
            parts.append(self.suffix)
        return ":".join(parts)

    async def _get_client(self) -> Any:
        if self._client is None:
            self._client = aioredis.from_url(self.url, db=self.db, decode_responses=True)
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        client = await self._get_client()
        full_key = self._make_key(key)
        value = await client.get(full_key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        client = await self._get_client()
        full_key = self._make_key(key)
        serialized = json.dumps(value)
        if ttl is not None:
            await client.setex(full_key, ttl, serialized)
        else:
            await client.set(full_key, serialized)

    async def delete(self, key: str) -> None:
        client = await self._get_client()
        full_key = self._make_key(key)
        await client.delete(full_key)

    async def exists(self, key: str) -> bool:
        client = await self._get_client()
        full_key = self._make_key(key)
        return bool(await client.exists(full_key))

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        client = await self._get_client()
        keys = await client.keys(pattern)
        result = {}
        for k in keys:
            value = await client.get(k)
            if value is not None:
                try:
                    result[k] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    result[k] = value
        return result

    async def clear(self, pattern: str = "*") -> int:
        client = await self._get_client()
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
        return len(keys)

    async def publish(self, mailbox: str, message: Any) -> None:
        client = await self._get_client()
        serialized = json.dumps(message)
        await client.publish(mailbox, serialized)

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        client = await self._get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(mailbox)
        try:
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    try:
                        yield json.loads(msg["data"])
                    except (json.JSONDecodeError, TypeError):
                        yield msg["data"]
        finally:
            await pubsub.unsubscribe(mailbox)
            await pubsub.close()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


# ---------------------------------------------------------------------------
# Token Usage Tracking
# ---------------------------------------------------------------------------

@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cached_tokens=self.cached_tokens + other.cached_tokens,
        )


# ---------------------------------------------------------------------------
# Tool / Function Calling
# ---------------------------------------------------------------------------

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Optional[Callable] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    tool_call_id: str
    name: str
    result: Any
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    role: MessageRole
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                }
                for tc in self.tool_calls
            ]
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d


# ---------------------------------------------------------------------------
# Inference Response
# ---------------------------------------------------------------------------

@dataclass
class InferenceResponse:
    content: str
    model: str
    usage: TokenUsage
    tool_calls: Optional[List[ToolCall]] = None
    finish_reason: Optional[str] = None
    raw: Optional[Any] = None


@dataclass
class StreamChunk:
    content: str
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    usage: Optional[TokenUsage] = None


# ---------------------------------------------------------------------------
# Inference Clients
# ---------------------------------------------------------------------------

class AbstractInferenceClient(ABC):
    """Abstract base class for LLM inference clients."""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        tracer: Optional[Any] = None,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.tracer = tracer
        self._total_usage = TokenUsage()

    @property
    def total_usage(self) -> TokenUsage:
        return self._total_usage

    def _track_usage(self, usage: TokenUsage) -> None:
        self._total_usage = self._total_usage + usage

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        pass

    def _start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Any:
        if OTEL_AVAILABLE and self.tracer:
            span = self.tracer.start_span(name)
            if attributes:
                for k, v in attributes.items():
                    span.set_attribute(k, str(v))
            return span
        return None

    def _end_span(self, span: Any) -> None:
        if OTEL_AVAILABLE and span is not None:
            span.end()


class OpenAIInferenceClient(AbstractInferenceClient):
    """OpenAI-compatible inference client."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        tracer: Optional[Any] = None,
        enable_prompt_caching: bool = False,
    ):
        super().__init__(model=model, api_key=api_key, base_url=base_url, tracer=tracer)
        self.enable_prompt_caching = enable_prompt_caching
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        try:
            import openai
        except ImportError:
            raise ImportError("openai package is required. Install with: pip install openai")
        if self._client is None:
            kwargs: Dict[str, Any] = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = openai.AsyncOpenAI(**kwargs)
        return self._client

    def _build_tools_payload(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    def _parse_tool_calls(self, raw_tool_calls: Any) -> List[ToolCall]:
        result = []
        if raw_tool_calls:
            for tc in raw_tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, AttributeError):
                    args = {}
                result.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
        return result

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        span = self._start_span(
            "openai.complete",
            {"model": self.model, "message_count": len(messages)},
        )
        try:
            client = self._get_client()
            payload: Dict[str, Any] = {
                "model": self.model,
                "messages": [m.to_dict() for m in messages],
                "temperature": temperature,
            }
            if max_tokens:
                payload["max_tokens"] = max_tokens
            if tools:
                payload["tools"] = self._build_tools_payload(tools)
            if self.enable_prompt_caching:
                payload["store"] = True

            response = await client.chat.completions.create(**payload, **kwargs)
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
                cached_tokens=getattr(response.usage, "prompt_tokens_details", None) and
                              getattr(response.usage.prompt_tokens_details, "cached_tokens", 0) or 0,
            )
            self._track_usage(usage)
            choice = response.choices[0]
            tool_calls = self._parse_tool_calls(choice.message.tool_calls)
            return InferenceResponse(
                content=choice.message.content or "",
                model=response.model,
                usage=usage,
                tool_calls=tool_calls if tool_calls else None,
                finish_reason=choice.finish_reason,
                raw=response,
            )
        finally:
            self._end_span(span)

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        span = self._start_span(
            "openai.stream",
            {"model": self.model, "message_count": len(messages)},
        )
        try:
            client = self._get_client()
            payload: Dict[str, Any] = {
                "model": self.model,
                "messages": [m.to_dict() for m in messages],
                "temperature": temperature,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            if max_tokens:
                payload["max_tokens"] = max_tokens
            if tools:
                payload["tools"] = self._build_tools_payload(tools)

            async with await client.chat.completions.create(**payload, **kwargs) as stream:
                async for chunk in stream:
                    if not chunk.choices:
                        if chunk.usage:
                            usage = TokenUsage(
                                prompt_tokens=chunk.usage.prompt_tokens,
                                completion_tokens=chunk.usage.completion_tokens,
                                total_tokens=chunk.usage.total_tokens,
                            )
                            self._track_usage(usage)
                            yield StreamChunk(content="", usage=usage)
                        continue
                    choice = chunk.choices[0]
                    content = ""
                    if choice.delta and choice.delta.content:
                        content = choice.delta.content
                    yield StreamChunk(
                        content=content,
                        finish_reason=choice.finish_reason,
                    )
        finally:
            self._end_span(span)


class AnthropicInferenceClient(AbstractInferenceClient):
    """Anthropic Claude inference client."""

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        tracer: Optional[Any] = None,
        enable_prompt_caching: bool = False,
        max_tokens: int = 4096,
    ):
        super().__init__(model=model, api_key=api_key, base_url=base_url, tracer=tracer)
        self.enable_prompt_caching = enable_prompt_caching
        self.default_max_tokens = max_tokens
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package is required. Install with: pip install anthropic")
        if self._client is None:
            kwargs: Dict[str, Any] = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = anthropic.AsyncAnthropic(**kwargs)
        return self._client

    def _convert_messages(
        self, messages: List[Message]
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        system_prompt = None
        converted = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_prompt = msg.content
            else:
                converted.append({"role": msg.role.value, "content": msg.content})
        return system_prompt, converted

    def _build_tools_payload(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        span = self._start_span(
            "anthropic.complete",
            {"model": self.model, "message_count": len(messages)},
        )
        try:
            client = self._get_client()
            system_prompt, converted_messages = self._convert_messages(messages)
            payload: Dict[str, Any] = {
                "model": self.model,
                "messages": converted_messages,
                "max_tokens": max_tokens or self.default_max_tokens,
                "temperature": temperature,
            }
            if system_prompt:
                if self.enable_prompt_caching:
                    payload["system"] = [
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ]
                else:
                    payload["system"] = system_prompt
            if tools:
                payload["tools"] = self._build_tools_payload(tools)

            response = await client.messages.create(**payload, **kwargs)
            usage = TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                cached_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            )
            self._track_usage(usage)
            content = ""
            tool_calls = []
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text
                elif hasattr(block, "type") and block.type == "tool_use":
                    tool_calls.append(
                        ToolCall(
                            id=block.id,
                            name=block.name,
                            arguments=block.input if isinstance(block.input, dict) else {},
                        )
                    )
            return InferenceResponse(
                content=content,
                model=self.model,
                usage=usage,
                tool_calls=tool_calls if tool_calls else None,
                finish_reason=response.stop_reason,
                raw=response,
            )
        finally:
            self._end_span(span)

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        span = self._start_span(
            "anthropic.stream",
            {"model": self.model, "message_count": len(messages)},
        )
        try:
            client = self._get_client()
            system_prompt, converted_messages = self._convert_messages(messages)
            payload: Dict[str, Any] = {
                "model": self.model,
                "messages": converted_messages,
                "max_tokens": max_tokens or self.default_max_tokens,
                "temperature": temperature,
            }
            if system_prompt:
                payload["system"] = system_prompt
            if tools:
                payload["tools"] = self._build_tools_payload(tools)

            async with client.messages.stream(**payload, **kwargs) as stream:
                async for text in stream.text_stream:
                    yield StreamChunk(content=text)
                final = await stream.get_final_message()
                usage = TokenUsage(
                    prompt_tokens=final.usage.input_tokens,
                    completion_tokens=final.usage.output_tokens,
                    total_tokens=final.usage.input_tokens + final.usage.output_tokens,
                )
                self._track_usage(usage)
                yield StreamChunk(content="", finish_reason=final.stop_reason, usage=usage)
        finally:
            self._end_span(span)


class MockInferenceClient(AbstractInferenceClient):
    """Mock inference client for testing."""

    def __init__(
        self,
        model: str = "mock-model",
        responses: Optional[List[str]] = None,
        tracer: Optional[Any] = None,
    ):
        super().__init__(model=model, tracer=tracer)
        self._responses = responses or ["Mock response"]
        self._call_count = 0
        self._call_history: List[Dict[str, Any]] = []

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def call_history(self) -> List[Dict[str, Any]]:
        return self._call_history

    def _get_next_response(self) -> str:
        if not self._responses:
            return "Mock response"
        response = self._responses[self._call_count % len(self._responses)]
        return response

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        content = self._get_next_response()
        self._call_history.append({"messages": messages, "tools": tools, "response": content})
        self._call_count += 1
        usage = TokenUsage(
            prompt_tokens=sum(len(m.content.split()) for m in messages),
            completion_tokens=len(content.split()),
            total_tokens=sum(len(m.content.split()) for m in messages) + len(content.split()),
        )
        self._track_usage(usage)
        return InferenceResponse(
            content=content,
            model=self.model,
            usage=usage,
            finish_reason="stop",
        )

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        content = self._get_next_response()
        self._call_history.append({"messages": messages, "tools": tools, "response": content})
        self._call_count += 1
        words = content.split()
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield StreamChunk(content=chunk)
            await asyncio.sleep(0)
        usage = TokenUsage(
            prompt_tokens=sum(len(m.content.split()) for m in messages),
            completion_tokens=len(words),
            total_tokens=sum(len(m.content.split()) for m in messages) + len(words),
        )
        self._track_usage(usage)
        yield StreamChunk(content="", finish_reason="stop", usage=usage)


# ---------------------------------------------------------------------------
# Graph Primitives
# ---------------------------------------------------------------------------

class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class NodeResult:
    node_id: str
    status: NodeStatus
    output: Any = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class GraphState(Generic[StateT]):
    data: StateT
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    snapshots: List[Dict[str, Any]] = field(default_factory=list)

    def snapshot(self) -> Dict[str, Any]:
        import copy
        snap = {
            "timestamp": time.time(),
            "data": copy.deepcopy(self.data),
            "node_results": copy.deepcopy(self.node_results),
            "metadata": copy.deepcopy(self.metadata),
        }
        self.snapshots.append(snap)
        return snap

    def restore(self, snapshot_index: int = -1) -> None:
        import copy
        if not self.snapshots:
            raise GraphError("No snapshots available")
        snap = self.snapshots[snapshot_index]
        self.data = copy.deepcopy(snap["data"])
        self.node_results = copy.deepcopy(snap["node_results"])
        self.metadata = copy.deepcopy(snap["metadata"])


class Node(ABC):
    """Abstract base class for graph nodes."""

    def __init__(
        self,
        node_id: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.node_id = node_id or str(uuid.uuid4())
        self.name = name or self.__class__.__name__
        self.metadata = metadata or {}
        self._status = NodeStatus.PENDING

    @property
    def status(self) -> NodeStatus:
        return self._status

    @abstractmethod
    async def execute(self, state: GraphState, **kwargs: Any) -> Any:
        pass

    async def on_error(self, error: Exception, state: GraphState) -> Optional[Any]:
        return None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.node_id}, name={self.name})"


class FunctionNode(Node):
    """Node that wraps a callable function."""

    def __init__(
        self,
        func: Callable,
        node_id: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(node_id=node_id, name=name or func.__name__, metadata=metadata)
        self.func = func

    async def execute(self, state: GraphState, **kwargs: Any) -> Any:
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(state, **kwargs)
        return self.func(state, **kwargs)


class LLMNode(Node):
    """Node that uses an LLM inference client."""

    def __init__(
        self,
        client: AbstractInferenceClient,
        prompt_template: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[ToolDefinition]] = None,
        node_id: Optional[str] = None,
        name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(node_id=node_id, name=name, metadata=metadata)
        self.client = client
        self.prompt_template = prompt_template
        self.system_prompt = system_prompt
        self.tools = tools
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _build_messages(self, state: GraphState, **kwargs: Any) -> List[Message]:
        messages = []
        if self.system_prompt:
            messages.append(Message(role=MessageRole.SYSTEM, content=self.system_prompt))
        if self.prompt_template:
            try:
                content = self.prompt_template.format(state=state, **kwargs)
            except (KeyError, AttributeError):
                content = self.prompt_template
            messages.append(Message(role=MessageRole.USER, content=content))
        elif hasattr(state.data, "messages") and isinstance(state.data.messages, list):
            messages.extend(state.data.messages)
        else:
            messages.append(Message(role=MessageRole.USER, content=str(state.data)))
        return messages

    async def execute(self, state: GraphState, **kwargs: Any) -> InferenceResponse:
        messages = self._build_messages(state, **kwargs)
        response = await self.client.complete(
            messages=messages,
            tools=self.tools,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response


class ConditionalNode(Node):
    """Node that routes execution based on a condition."""

    def __init__(
        self,
        condition: Callable[[GraphState], str],
        node_id: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(node_id=node_id, name=name, metadata=metadata)
        self.condition = condition

    async def execute(self, state: GraphState, **kwargs: Any) -> str:
        if asyncio.iscoroutinefunction(self.condition):
            return await self.condition(state)
        return self.condition(state)


class LLMDirectedNode(Node):
    """Node where an LLM decides the next execution path."""

    def __init__(
        self,
        client: AbstractInferenceClient,
        choices: List[str],
        system_prompt: Optional[str] = None,
        node_id: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(node_id=node_id, name=name, metadata=metadata)
        self.client = client
        self.choices = choices
        self.system_prompt = system_prompt or (
            f"You are a routing agent. Based on the current state, "
            f"choose the next step. Available choices: {', '.join(choices)}. "
            f"Respond with ONLY the choice name, nothing else."
        )

    async def execute(self, state: GraphState, **kwargs: Any) -> str:
        messages = [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt),
            Message(
                role=MessageRole.USER,
                content=f"Current state: {json.dumps(state.data if isinstance(state.data, dict) else str(state.data))}\n"
                        f"Choose from: {', '.join(self.choices)}",
            ),
        ]
        response = await self.client.complete(messages=messages, temperature=0.0)
        chosen = response.content.strip()
        for choice in self.choices:
            if choice.lower() in chosen.lower():
                return choice
        return self.choices[0]


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class Middleware(ABC):
    """Abstract middleware for graph execution."""

    @abstractmethod
    async def before_node(self, node: Node, state: GraphState) -> None:
        pass

    @abstractmethod
    async def after_node(self, node: Node, state: GraphState, result: NodeResult) -> None:
        pass

    async def on_error(self, node: Node, state: GraphState, error: Exception) -> None:
        pass


class LoggingMiddleware(Middleware):
    """Middleware that logs node execution."""

    def __init__(self, logger: Optional[Any] = None):
        import logging
        self.logger = logger or logging.getLogger(__name__)

    async def before_node(self, node: Node, state: GraphState) -> None:
        self.logger.info(f"Starting node: {node.name} (id={node.node_id})")

    async def after_node(self, node: Node, state: GraphState, result: NodeResult) -> None:
        self.logger.info(
            f"Completed node: {node.name} (id={node.node_id}) "
            f"status={result.status} duration={result.duration:.3f}s"
            if result.duration else
            f"Completed node: {node.name} (id={node.node_id}) status={result.status}"
        )

    async def on_error(self, node: Node, state: GraphState, error: Exception) -> None:
        self.logger.error(f"Error in node: {node.name} (id={node.node_id}): {error}")


class TracingMiddleware(Middleware):
    """OpenTelemetry tracing middleware."""

    def __init__(self, tracer: Optional[Any] = None, service_name: str = "agent-graph"):
        self.service_name = service_name
        self._spans: Dict[str, Any] = {}
        if OTEL_AVAILABLE:
            self.tracer = tracer or trace.get_tracer(service_name)
        else:
            self.tracer = None

    async def before_node(self, node: Node, state: GraphState) -> None:
        if OTEL_AVAILABLE and self.tracer:
            span = self.tracer.start_span(f"node.{node.name}")
            span.set_attribute("node.id", node.node_id)
            span.set_attribute("node.name", node.name)
            self._spans[node.node_id] = span

    async def after_node(self, node: Node, state: GraphState, result: NodeResult) -> None:
        if OTEL_AVAILABLE and node.node_id in self._spans:
            span = self._spans.pop(node.node_id)
            span.set_attribute("node.status", result.status.value)
            if result.duration:
                span.set_attribute("node.duration_ms", result.duration * 1000)
            span.end()

    async def on_error(self, node: Node, state: GraphState, error: Exception) -> None:
        if OTEL_AVAILABLE and node.node_id in self._spans:
            span = self._spans.pop(node.node_id)
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(error))
            span.end()


class CachingMiddleware(Middleware):
    """Middleware that caches node results."""

    def __init__(self, cache: AbstractCache, ttl: Optional[int] = None):
        self.cache = cache
        self.ttl = ttl
        self._cache_keys: Dict[str, str] = {}

    def _make_cache_key(self, node: Node, state: GraphState) -> str:
        state_hash = hash(json.dumps(state.data, sort_keys=True, default=str))
        return f"node:{node.node_id}:state:{state_hash}"

    async def before_node(self, node: Node, state: GraphState) -> None:
        pass

    async def after_node(self, node: Node, state: GraphState, result: NodeResult) -> None:
        if result.status == NodeStatus.COMPLETED and result.output is not None:
            cache_key = self._make_cache_key(node, state)
            try:
                await self.cache.set(cache_key, result.output, ttl=self.ttl)
            except Exception:
                pass

    async def get_cached(self, node: Node, state: GraphState) -> Optional[Any]:
        cache_key = self._make_cache_key(node, state)
        try:
            return await self.cache.get(cache_key)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Graph Engine
# ---------------------------------------------------------------------------

class Edge:
    """Represents a directed edge between nodes."""

    def __init__(
        self,
        source_id: str,
        target_id: str,
        condition: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.source_id = source_id
        self.target_id = target_id
        self.condition = condition
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        cond = f" [{self.condition}]" if self.condition else ""
        return f"Edge({self.source_id} -> {self.target_id}{cond})"


class Graph:
    """Directed graph for task execution."""

    def __init__(self, name: str = "graph"):
        self.name = name
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, List[Edge]] = defaultdict(list)
        self._entry_point: Optional[str] = None
        self._end_points: Set[str] = set()

    def add_node(self, node: Node) -> "Graph":
        self._nodes[node.node_id] = node
        return self

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        condition: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Graph":
        if source_id not in self._nodes:
            raise NodeNotFoundError(f"Source node '{source_id}' not found")
        if target_id not in self._nodes:
            raise NodeNotFoundError(f"Target node '{target_id}' not found")
        edge = Edge(source_id=source_id, target_id=target_id, condition=condition, metadata=metadata)
        self._edges[source_id].append(edge)
        return self

    def set_entry_point(self, node_id: str) -> "Graph":
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found")
        self._entry_point = node_id
        return self

    def set_end_point(self, node_id: str) -> "Graph":
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found")
        self._end_points.add(node_id)
        return self

    def get_node(self, node_id: str) -> Node:
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found")
        return self._nodes[node_id]

    def get_edges(self, node_id: str) -> List[Edge]:
        return self._edges.get(node_id, [])

    def get_next_nodes(self, node_id: str, condition: Optional[str] = None) -> List[str]:
        edges = self.get_edges(node_id)
        if condition is not None:
            return [e.target_id for e in edges if e.condition == condition or e.condition is None]
        return [e.target_id for e in edges]

    def validate(self) -> None:
        if not self._entry_point:
            raise GraphError("No entry point set")
        self._detect_cycles()

    def _detect_cycles(self) -> None:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for edge in self._edges.get(node_id, []):
                neighbor = edge.target_id
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.discard(node_id)
            return False

        for node_id in self._nodes:
            if node_id not in visited:
                if dfs(node_id):
                    raise CycleDetectedError("Cycle detected in graph")

    @property
    def nodes(self) -> Dict[str, Node]:
        return self._nodes

    @property
    def entry_point(self) -> Optional[str]:
        return self._entry_point

    @property
    def end_points(self) -> Set[str]:
        return self._end_points


class GraphExecutor:
    """Executes a graph with state management and middleware support."""

    def __init__(
        self,
        graph: Graph,
        middleware: Optional[List[Middleware]] = None,
        max_iterations: int = 100,
        enable_snapshots: bool = False,
        tracer: Optional[Any] = None,
    ):
        self.graph = graph
        self.middleware = middleware or []
        self.max_iterations = max_iterations
        self.enable_snapshots = enable_snapshots
        self.tracer = tracer

    async def _run_middleware_before(self, node: Node, state: GraphState) -> None:
        for mw in self.middleware:
            await mw.before_node(node, state)

    async def _run_middleware_after(self, node: Node, state: GraphState, result: NodeResult) -> None:
        for mw in self.middleware:
            await mw.after_node(node, state, result)

    async def _run_middleware_error(self, node: Node, state: GraphState, error: Exception) -> None:
        for mw in self.middleware:
            await mw.on_error(node, state, error)

    async def _execute_node(self, node: Node, state: GraphState, **kwargs: Any) -> NodeResult:
        result = NodeResult(
            node_id=node.node_id,
            status=NodeStatus.RUNNING,
            start_time=time.time(),
        )
        node._status = NodeStatus.RUNNING

        await self._run_middleware_before(node, state)

        try:
            output = await node.execute(state, **kwargs)
            result.output = output
            result.status = NodeStatus.COMPLETED
            node._status = NodeStatus.COMPLETED
        except Exception as e:
            result.status = NodeStatus.FAILED
            result.error = str(e)
            node._status = NodeStatus.FAILED
            await self._run_middleware_error(node, state, e)
            recovery = await node.on_error(e, state)
            if recovery is not None:
                result.output = recovery
                result.status = NodeStatus.COMPLETED
                node._status = NodeStatus.COMPLETED
            else:
                result.end_time = time.time()
                state.node_results[node.node_id] = result
                await self._run_middleware_after(node, state, result)
                raise ExecutionError(f"Node '{node.name}' failed: {e}") from e

        result.end_time = time.time()
        state.node_results[node.node_id] = result
        await self._run_middleware_after(node, state, result)
        return result

    async def execute(
        self,
        state: GraphState,
        **kwargs: Any,
    ) -> GraphState:
        self.graph.validate()

        if self.enable_snapshots:
            state.snapshot()

        current_node_id = self.graph.entry_point
        iterations = 0

        while current_node_id is not None:
            if iterations >= self.max_iterations:
                raise ExecutionError(f"Max iterations ({self.max_iterations}) exceeded")

            node = self.graph.get_node(current_node_id)
            result = await self._execute_node(node, state, **kwargs)

            if self.enable_snapshots:
                state.snapshot()

            if current_node_id in self.graph.end_points:
                break

            edges = self.graph.get_edges(current_node_id)
            if not edges:
                break

            if isinstance(node, (ConditionalNode, LLMDirectedNode)):
                chosen_condition = result.output
                next_nodes = [
                    e.target_id for e in edges
                    if e.condition == chosen_condition
                ]
                if not next_nodes:
                    next_nodes = [e.target_id for e in edges if e.condition is None]
                current_node_id = next_nodes[0] if next_nodes else None
            else:
                current_node_id = edges[0].target_id if edges else None

            iterations += 1

        return state

    async def execute_parallel(
        self,
        node_ids: List[str],
        state: GraphState,
        **kwargs: Any,
    ) -> List[NodeResult]:
        tasks = []
        for node_id in node_ids:
            node = self.graph.get_node(node_id)
            tasks.append(self._execute_node(node, state, **kwargs))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        node_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                node_results.append(
                    NodeResult(
                        node_id=node_ids[i],
                        status=NodeStatus.FAILED,
                        error=str(result),
                    )
                )
            else:
                node_results.append(result)
        return node_results


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

@dataclass
class AgentConfig:
    name: str
    system_prompt: str
    tools: List[ToolDefinition] = field(default_factory=list)
    max_iterations: int = 10
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    enable_caching: bool = False
    cache: Optional[AbstractCache] = None


class Agent:
    """High-level agent that combines LLM inference with tool execution."""

    def __init__(
        self,
        config: AgentConfig,
        client: AbstractInferenceClient,
        tracer: Optional[Any] = None,
    ):
        self.config = config
        self.client = client
        self.tracer = tracer
        self._conversation_history: List[Message] = []
        self._tool_registry: Dict[str, ToolDefinition] = {
            t.name: t for t in config.tools
        }

    @property
    def conversation_history(self) -> List[Message]:
        return self._conversation_history.copy()

    def add_tool(self, tool: ToolDefinition) -> None:
        self.config.tools.append(tool)
        self._tool_registry[tool.name] = tool

    def reset(self) -> None:
        self._conversation_history.clear()

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        tool_def = self._tool_registry.get(tool_call.name)
        if not tool_def:
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                result=None,
                error=f"Tool '{tool_call.name}' not found",
            )
        if not tool_def.function:
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                result=None,
                error=f"Tool '{tool_call.name}' has no implementation",
            )
        try:
            if asyncio.iscoroutinefunction(tool_def.function):
                result = await tool_def.function(**tool_call.arguments)
            else:
                result = tool_def.function(**tool_call.arguments)
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                result=result,
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                result=None,
                error=str(e),
            )

    async def run(self, user_message: str) -> str:
        self._conversation_history.append(
            Message(role=MessageRole.USER, content=user_message)
        )
        messages = [
            Message(role=MessageRole.SYSTEM, content=self.config.system_prompt)
        ] + self._conversation_history

        for iteration in range(self.config.max_iterations):
            response = await self.client.complete(
                messages=messages,
                tools=self.config.tools if self.config.tools else None,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            if response.tool_calls:
                assistant_msg = Message(
                    role=MessageRole.ASSISTANT,
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
                self._conversation_history.append(assistant_msg)
                messages.append(assistant_msg)

                for tool_call in response.tool_calls:
                    tool_result = await self._execute_tool(tool_call)
                    result_content = (
                        json.dumps(tool_result.result, default=str)
                        if tool_result.result is not None
                        else tool_result.error or ""
                    )
                    tool_msg = Message(
                        role=MessageRole.TOOL,
                        content=result_content,
                        tool_call_id=tool_call.id,
                        name=tool_call.name,
                    )
                    self._conversation_history.append(tool_msg)
                    messages.append(tool_msg)
            else:
                assistant_msg = Message(
                    role=MessageRole.ASSISTANT,
                    content=response.content,
                )
                self._conversation_history.append(assistant_msg)
                return response.content

        return "Max iterations reached without a final response."

    async def stream_run(self, user_message: str) -> AsyncGenerator[str, None]:
        self._conversation_history.append(
            Message(role=MessageRole.USER, content=user_message)
        )
        messages = [
            Message(role=MessageRole.SYSTEM, content=self.config.system_prompt)
        ] + self._conversation_history

        full_content = ""
        async for chunk in self.client.stream(
            messages=messages,
            tools=self.config.tools if self.config.tools else None,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        ):
            if chunk.content:
                full_content += chunk.content
                yield chunk.content

        self._conversation_history.append(
            Message(role=MessageRole.ASSISTANT, content=full_content)
        )


# ---------------------------------------------------------------------------
# Graph Builder (Fluent API)
# ---------------------------------------------------------------------------

class GraphBuilder:
    """Fluent builder for constructing graphs."""

    def __init__(self, name: str = "graph"):
        self._graph = Graph(name=name)
        self._middleware: List[Middleware] = []
        self._max_iterations: int = 100
        self._enable_snapshots: bool = False

    def add_node(self, node: Node) -> "GraphBuilder":
        self._graph.add_node(node)
        return self

    def add_function_node(
        self,
        func: Callable,
        node_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> "GraphBuilder":
        node = FunctionNode(func=func, node_id=node_id, name=name)
        self._graph.add_node(node)
        return self

    def add_llm_node(
        self,
        client: AbstractInferenceClient,
        prompt_template: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[ToolDefinition]] = None,
        node_id: Optional[str] = None,
        name: Optional[str] = None,
        temperature: float = 0.7,
    ) -> "GraphBuilder":
        node = LLMNode(
            client=client,
            prompt_template=prompt_template,
            system_prompt=system_prompt,
            tools=tools,
            node_id=node_id,
            name=name,
            temperature=temperature,
        )
        self._graph.add_node(node)
        return self

    def connect(
        self,
        source_id: str,
        target_id: str,
        condition: Optional[str] = None,
    ) -> "GraphBuilder":
        self._graph.add_edge(source_id, target_id, condition=condition)
        return self

    def set_entry(self, node_id: str) -> "GraphBuilder":
        self._graph.set_entry_point(node_id)
        return self

    def set_end(self, node_id: str) -> "GraphBuilder":
        self._graph.set_end_point(node_id)
        return self

    def with_middleware(self, middleware: Middleware) -> "GraphBuilder":
        self._middleware.append(middleware)
        return self

    def with_max_iterations(self, max_iterations: int) -> "GraphBuilder":
        self._max_iterations = max_iterations
        return self

    def with_snapshots(self, enabled: bool = True) -> "GraphBuilder":
        self._enable_snapshots = enabled
        return self

    def build(self) -> Tuple[Graph, GraphExecutor]:
        executor = GraphExecutor(
            graph=self._graph,
            middleware=self._middleware,
            max_iterations=self._max_iterations,
            enable_snapshots=self._enable_snapshots,
        )
        return self._graph, executor


# ---------------------------------------------------------------------------
# OpenTelemetry Setup Helper
# ---------------------------------------------------------------------------

class TelemetryConfig:
    """Helper for configuring OpenTelemetry."""

    def __init__(
        self,
        service_name: str = "agent-framework",
        endpoint: Optional[str] = None,
        enable_console_export: bool = False,
    ):
        self.service_name = service_name
        self.endpoint = endpoint
        self.enable_console_export = enable_console_export
        self._tracer: Optional[Any] = None

    def setup(self) -> Optional[Any]:
        if not OTEL_AVAILABLE:
            return None
        try:
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
            from opentelemetry.sdk.resources import Resource

            resource = Resource.create({"service.name": self.service_name})
            provider = TracerProvider(resource=resource)

            if self.enable_console_export:
                provider.add_span_processor(
                    BatchSpanProcessor(ConsoleSpanExporter())
                )

            if self.endpoint:
                try:
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                    exporter = OTLPSpanExporter(endpoint=self.endpoint)
                    provider.add_span_processor(BatchSpanProcessor(exporter))
                except ImportError:
                    pass

            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(self.service_name)
            return self._tracer
        except Exception:
            return None

    @property
    def tracer(self) -> Optional[Any]:
        return self._tracer


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def create_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any],
    function: Optional[Callable] = None,
) -> ToolDefinition:
    """Helper to create a ToolDefinition."""
    return ToolDefinition(
        name=name,
        description=description,
        parameters=parameters,
        function=function,
    )


def tool(
    name: Optional[str] = None,
    description: str = "",
    parameters: Optional[Dict[str, Any]] = None,
) -> Callable:
    """Decorator to create a ToolDefinition from a function."""
    def decorator(func: Callable) -> ToolDefinition:
        tool_name = name or func.__name__
        tool_params = parameters or {
            "type": "object",
            "properties": {},
            "required": [],
        }
        return ToolDefinition(
            name=tool_name,
            description=description or func.__doc__ or "",
            parameters=tool_params,
            function=func,
        )
    return decorator


async def run_graph(
    graph: Graph,
    initial_state: Any,
    middleware: Optional[List[Middleware]] = None,
    max_iterations: int = 100,
    enable_snapshots: bool = False,
    **kwargs: Any,
) -> GraphState:
    """Convenience function to run a graph with an initial state."""
    state = GraphState(data=initial_state)
    executor = GraphExecutor(
        graph=graph,
        middleware=middleware or [],
        max_iterations=max_iterations,
        enable_snapshots=enable_snapshots,
    )
    return await executor.execute(state, **kwargs)


# ---------------------------------------------------------------------------
# Registry for managing multiple graphs and agents
# ---------------------------------------------------------------------------

class AgentRegistry:
    """Registry for managing multiple agents and graphs."""

    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._graphs: Dict[str, Graph] = {}
        self._executors: Dict[str, GraphExecutor] = {}

    def register_agent(self, name: str, agent: Agent) -> None:
        self._agents[name] = agent

    def get_agent(self, name: str) -> Agent:
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not found in registry")
        return self._agents[name]

    def register_graph(self, name: str, graph: Graph, executor: Optional[GraphExecutor] = None) -> None:
        self._graphs[name] = graph
        if executor:
            self._executors[name] = executor

    def get_graph(self, name: str) -> Tuple[Graph, Optional[GraphExecutor]]:
        if name not in self._graphs:
            raise KeyError(f"Graph '{name}' not found in registry")
        return self._graphs[name], self._executors.get(name)

    def list_agents(self) -> List[str]:
        return list(self._agents.keys())

    def list_graphs(self) -> List[str]:
        return list(self._graphs.keys())


# ---------------------------------------------------------------------------
# Module-level registry instance
# ---------------------------------------------------------------------------

registry = AgentRegistry()