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


class NodeNotFoundError(GraphError):
    pass


class CycleDetectedError(GraphError):
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

    async def _get_client(self) -> Any:
        if self._client is None:
            self._client = aioredis.from_url(self.url, db=self.db, decode_responses=True)
        return self._client

    def _make_key(self, key: str) -> str:
        parts = []
        if self.prefix:
            parts.append(self.prefix)
        parts.append(key)
        if self.suffix:
            parts.append(self.suffix)
        return ":".join(parts)

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
        if keys:
            values = await client.mget(keys)
            for k, v in zip(keys, values):
                if v is not None:
                    try:
                        result[k] = json.loads(v)
                    except (json.JSONDecodeError, TypeError):
                        result[k] = v
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
    required: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required,
            },
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

class BaseInferenceClient(ABC):
    """Abstract base class for LLM inference clients."""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
        tracer: Optional[Any] = None,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.tracer = tracer
        self._total_usage = TokenUsage()

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

    def get_total_usage(self) -> TokenUsage:
        return self._total_usage

    def reset_usage(self) -> None:
        self._total_usage = TokenUsage()

    def _track_usage(self, usage: TokenUsage) -> None:
        self._total_usage = self._total_usage + usage


class OpenAIInferenceClient(BaseInferenceClient):
    """OpenAI-compatible inference client."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
        tracer: Optional[Any] = None,
        enable_prompt_caching: bool = False,
    ):
        super().__init__(model, api_key, base_url, timeout, max_retries, tracer)
        self.enable_prompt_caching = enable_prompt_caching
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        try:
            import openai
        except ImportError:
            raise ImportError("openai package is required. Install with: pip install openai")
        if self._client is None:
            kwargs: Dict[str, Any] = {
                "api_key": self.api_key,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
            }
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = openai.AsyncOpenAI(**kwargs)
        return self._client

    def _build_tools_payload(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        return [{"type": "function", "function": t.to_dict()} for t in tools]

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
        payload.update(kwargs)

        span = None
        if self.tracer and OTEL_AVAILABLE:
            span = self.tracer.start_span("openai.complete")

        try:
            response = await client.chat.completions.create(**payload)
            choice = response.choices[0]
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                cached_tokens=getattr(response.usage, "prompt_tokens_details", None) and
                              getattr(response.usage.prompt_tokens_details, "cached_tokens", 0) or 0,
            )
            self._track_usage(usage)
            tool_calls = self._parse_tool_calls(choice.message.tool_calls)
            return InferenceResponse(
                content=choice.message.content or "",
                model=response.model,
                usage=usage,
                tool_calls=tool_calls if tool_calls else None,
                finish_reason=choice.finish_reason,
                raw=response,
            )
        except Exception as e:
            raise InferenceError(f"OpenAI completion failed: {e}") from e
        finally:
            if span:
                span.end()

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
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
        payload.update(kwargs)

        try:
            async with await client.chat.completions.create(**payload) as stream:
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
        except Exception as e:
            raise InferenceError(f"OpenAI streaming failed: {e}") from e


class AnthropicInferenceClient(BaseInferenceClient):
    """Anthropic Claude inference client."""

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
        tracer: Optional[Any] = None,
        enable_prompt_caching: bool = False,
    ):
        super().__init__(model, api_key, None, timeout, max_retries, tracer)
        self.enable_prompt_caching = enable_prompt_caching
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package is required. Install with: pip install anthropic")
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(
                api_key=self.api_key,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
        return self._client

    def _convert_messages(self, messages: List[Message]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        system_prompt = None
        converted = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_prompt = msg.content
            else:
                converted.append({"role": msg.role.value, "content": msg.content})
        return system_prompt, converted

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        client = self._get_client()
        system_prompt, converted_messages = self._convert_messages(messages)
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if tools:
            payload["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": {
                        "type": "object",
                        "properties": t.parameters,
                        "required": t.required,
                    },
                }
                for t in tools
            ]
        payload.update(kwargs)

        try:
            response = await client.messages.create(**payload)
            content = ""
            tool_calls = []
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text
                elif hasattr(block, "type") and block.type == "tool_use":
                    tool_calls.append(
                        ToolCall(id=block.id, name=block.name, arguments=block.input)
                    )
            usage = TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                cached_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            )
            self._track_usage(usage)
            return InferenceResponse(
                content=content,
                model=response.model,
                usage=usage,
                tool_calls=tool_calls if tool_calls else None,
                finish_reason=response.stop_reason,
                raw=response,
            )
        except Exception as e:
            raise InferenceError(f"Anthropic completion failed: {e}") from e

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        client = self._get_client()
        system_prompt, converted_messages = self._convert_messages(messages)
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }
        if system_prompt:
            payload["system"] = system_prompt
        payload.update(kwargs)

        try:
            async with client.messages.stream(**payload) as stream:
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
        except Exception as e:
            raise InferenceError(f"Anthropic streaming failed: {e}") from e


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


class GraphState(Generic[StateT]):
    """Manages the state of a graph execution."""

    def __init__(self, initial_state: StateT):
        self._state = initial_state
        self._history: List[Tuple[float, StateT]] = []
        self._snapshots: Dict[str, StateT] = {}

    @property
    def state(self) -> StateT:
        return self._state

    def update(self, new_state: StateT) -> None:
        self._history.append((time.time(), self._state))
        self._state = new_state

    def snapshot(self, name: str) -> None:
        """Create a named snapshot of the current state."""
        import copy
        self._snapshots[name] = copy.deepcopy(self._state)

    def restore(self, name: str) -> None:
        """Restore state from a named snapshot."""
        if name not in self._snapshots:
            raise KeyError(f"Snapshot '{name}' not found")
        import copy
        self._history.append((time.time(), self._state))
        self._state = copy.deepcopy(self._snapshots[name])

    def get_history(self) -> List[Tuple[float, StateT]]:
        return list(self._history)

    def list_snapshots(self) -> List[str]:
        return list(self._snapshots.keys())


class Node(ABC):
    """Base class for graph nodes."""

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
    async def execute(self, state: Any, context: "ExecutionContext") -> Any:
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.node_id}, name={self.name})"


class FunctionNode(Node):
    """A node that wraps a callable function."""

    def __init__(
        self,
        func: Callable,
        node_id: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(node_id, name or func.__name__, metadata)
        self.func = func

    async def execute(self, state: Any, context: "ExecutionContext") -> Any:
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(state, context)
        return self.func(state, context)


class LLMNode(Node):
    """A node that uses an LLM for execution."""

    def __init__(
        self,
        client: BaseInferenceClient,
        prompt_template: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        node_id: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(node_id, name, metadata)
        self.client = client
        self.prompt_template = prompt_template
        self.system_prompt = system_prompt
        self.tools = tools
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _build_messages(self, state: Any, context: "ExecutionContext") -> List[Message]:
        messages = []
        if self.system_prompt:
            messages.append(Message(role=MessageRole.SYSTEM, content=self.system_prompt))
        if self.prompt_template:
            try:
                content = self.prompt_template.format(state=state, context=context)
            except (KeyError, AttributeError):
                content = self.prompt_template
        else:
            content = str(state)
        messages.append(Message(role=MessageRole.USER, content=content))
        return messages

    async def execute(self, state: Any, context: "ExecutionContext") -> InferenceResponse:
        messages = self._build_messages(state, context)
        response = await self.client.complete(
            messages=messages,
            tools=self.tools,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response


class ConditionalNode(Node):
    """A node that routes execution based on a condition."""

    def __init__(
        self,
        condition: Callable[[Any, "ExecutionContext"], Union[str, bool]],
        node_id: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(node_id, name, metadata)
        self.condition = condition

    async def execute(self, state: Any, context: "ExecutionContext") -> Union[str, bool]:
        if asyncio.iscoroutinefunction(self.condition):
            return await self.condition(state, context)
        return self.condition(state, context)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class Middleware(ABC):
    """Abstract middleware for graph execution."""

    @abstractmethod
    async def before_node(self, node: Node, state: Any, context: "ExecutionContext") -> Any:
        pass

    @abstractmethod
    async def after_node(self, node: Node, result: NodeResult, state: Any, context: "ExecutionContext") -> Any:
        pass

    async def on_error(self, node: Node, error: Exception, context: "ExecutionContext") -> None:
        pass


class LoggingMiddleware(Middleware):
    """Middleware that logs node execution."""

    def __init__(self, logger: Optional[Any] = None):
        import logging
        self.logger = logger or logging.getLogger(__name__)

    async def before_node(self, node: Node, state: Any, context: "ExecutionContext") -> Any:
        self.logger.info(f"Starting node: {node.name} (id={node.node_id})")
        return state

    async def after_node(self, node: Node, result: NodeResult, state: Any, context: "ExecutionContext") -> Any:
        self.logger.info(
            f"Completed node: {node.name} (id={node.node_id}) "
            f"status={result.status} duration={result.duration:.3f}s"
            if result.duration else f"Completed node: {node.name} status={result.status}"
        )
        return state

    async def on_error(self, node: Node, error: Exception, context: "ExecutionContext") -> None:
        self.logger.error(f"Error in node: {node.name} (id={node.node_id}): {error}")


class CachingMiddleware(Middleware):
    """Middleware that caches node results."""

    def __init__(self, cache: AbstractCache, ttl: Optional[int] = None):
        self.cache = cache
        self.ttl = ttl
        self._cache_keys: Dict[str, str] = {}

    def _make_cache_key(self, node: Node, state: Any) -> str:
        state_hash = hash(json.dumps(state, default=str, sort_keys=True))
        return f"node:{node.node_id}:state:{state_hash}"

    async def before_node(self, node: Node, state: Any, context: "ExecutionContext") -> Any:
        cache_key = self._make_cache_key(node, state)
        self._cache_keys[node.node_id] = cache_key
        cached = await self.cache.get(cache_key)
        if cached is not None:
            context.set_metadata(f"cache_hit_{node.node_id}", True)
        return state

    async def after_node(self, node: Node, result: NodeResult, state: Any, context: "ExecutionContext") -> Any:
        if result.status == NodeStatus.COMPLETED and result.output is not None:
            cache_key = self._cache_keys.get(node.node_id)
            if cache_key:
                try:
                    await self.cache.set(cache_key, result.output, ttl=self.ttl)
                except (TypeError, ValueError):
                    pass
        return state

    async def on_error(self, node: Node, error: Exception, context: "ExecutionContext") -> None:
        pass


class OpenTelemetryMiddleware(Middleware):
    """Middleware that instruments graph execution with OpenTelemetry."""

    def __init__(self, tracer_name: str = "agent_framework"):
        if not OTEL_AVAILABLE:
            raise ImportError("opentelemetry package is required. Install with: pip install opentelemetry-api")
        self.tracer = trace.get_tracer(tracer_name)
        self._spans: Dict[str, Any] = {}

    async def before_node(self, node: Node, state: Any, context: "ExecutionContext") -> Any:
        span = self.tracer.start_span(f"node.{node.name}")
        span.set_attribute("node.id", node.node_id)
        span.set_attribute("node.name", node.name)
        span.set_attribute("node.type", node.__class__.__name__)
        self._spans[node.node_id] = span
        return state

    async def after_node(self, node: Node, result: NodeResult, state: Any, context: "ExecutionContext") -> Any:
        span = self._spans.pop(node.node_id, None)
        if span:
            span.set_attribute("node.status", result.status.value)
            if result.duration:
                span.set_attribute("node.duration_ms", result.duration * 1000)
            span.end()
        return state

    async def on_error(self, node: Node, error: Exception, context: "ExecutionContext") -> None:
        span = self._spans.pop(node.node_id, None)
        if span:
            span.record_exception(error)
            span.set_status(trace.StatusCode.ERROR, str(error))
            span.end()


# ---------------------------------------------------------------------------
# Execution Context
# ---------------------------------------------------------------------------

class ExecutionContext:
    """Context passed to nodes during execution."""

    def __init__(
        self,
        graph_id: str,
        execution_id: str,
        cache: Optional[AbstractCache] = None,
        inference_client: Optional[BaseInferenceClient] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.graph_id = graph_id
        self.execution_id = execution_id
        self.cache = cache
        self.inference_client = inference_client
        self._metadata: Dict[str, Any] = metadata or {}
        self._node_results: Dict[str, NodeResult] = {}
        self.created_at = time.time()

    def set_metadata(self, key: str, value: Any) -> None:
        self._metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        return self._metadata.get(key, default)

    def record_result(self, result: NodeResult) -> None:
        self._node_results[result.node_id] = result

    def get_result(self, node_id: str) -> Optional[NodeResult]:
        return self._node_results.get(node_id)

    def get_all_results(self) -> Dict[str, NodeResult]:
        return dict(self._node_results)

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)


# ---------------------------------------------------------------------------
# Graph Engine
# ---------------------------------------------------------------------------

class Edge:
    """Represents a directed edge between two nodes."""

    def __init__(
        self,
        source_id: str,
        target_id: str,
        condition: Optional[Callable[[Any], bool]] = None,
        label: Optional[str] = None,
    ):
        self.source_id = source_id
        self.target_id = target_id
        self.condition = condition
        self.label = label

    def is_active(self, result: Any) -> bool:
        if self.condition is None:
            return True
        return bool(self.condition(result))


class Graph:
    """Directed graph for task execution."""

    def __init__(
        self,
        graph_id: Optional[str] = None,
        name: Optional[str] = None,
    ):
        self.graph_id = graph_id or str(uuid.uuid4())
        self.name = name or "Graph"
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, List[Edge]] = defaultdict(list)
        self._entry_points: Set[str] = set()
        self._end_points: Set[str] = set()

    def add_node(self, node: Node, entry: bool = False, end: bool = False) -> "Graph":
        self._nodes[node.node_id] = node
        if entry:
            self._entry_points.add(node.node_id)
        if end:
            self._end_points.add(node.node_id)
        return self

    def add_edge(
        self,
        source: Union[Node, str],
        target: Union[Node, str],
        condition: Optional[Callable[[Any], bool]] = None,
        label: Optional[str] = None,
    ) -> "Graph":
        source_id = source.node_id if isinstance(source, Node) else source
        target_id = target.node_id if isinstance(target, Node) else target
        if source_id not in self._nodes:
            raise NodeNotFoundError(f"Source node '{source_id}' not found in graph")
        if target_id not in self._nodes:
            raise NodeNotFoundError(f"Target node '{target_id}' not found in graph")
        edge = Edge(source_id, target_id, condition, label)
        self._edges[source_id].append(edge)
        return self

    def set_entry_point(self, node: Union[Node, str]) -> "Graph":
        node_id = node.node_id if isinstance(node, Node) else node
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found in graph")
        self._entry_points.add(node_id)
        return self

    def set_end_point(self, node: Union[Node, str]) -> "Graph":
        node_id = node.node_id if isinstance(node, Node) else node
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found in graph")
        self._end_points.add(node_id)
        return self

    def get_node(self, node_id: str) -> Optional[Node]:
        return self._nodes.get(node_id)

    def get_successors(self, node_id: str) -> List[str]:
        return [e.target_id for e in self._edges.get(node_id, [])]

    def get_edges(self, node_id: str) -> List[Edge]:
        return self._edges.get(node_id, [])

    def has_cycle(self) -> bool:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for edge in self._edges.get(node_id, []):
                if edge.target_id not in visited:
                    if dfs(edge.target_id):
                        return True
                elif edge.target_id in rec_stack:
                    return True
            rec_stack.discard(node_id)
            return False

        for node_id in self._nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False

    def topological_sort(self) -> List[str]:
        if self.has_cycle():
            raise CycleDetectedError("Graph contains a cycle")
        in_degree: Dict[str, int] = {nid: 0 for nid in self._nodes}
        for edges in self._edges.values():
            for edge in edges:
                in_degree[edge.target_id] += 1
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []
        while queue:
            node_id = queue.pop(0)
            result.append(node_id)
            for edge in self._edges.get(node_id, []):
                in_degree[edge.target_id] -= 1
                if in_degree[edge.target_id] == 0:
                    queue.append(edge.target_id)
        return result

    @property
    def nodes(self) -> Dict[str, Node]:
        return dict(self._nodes)

    @property
    def entry_points(self) -> Set[str]:
        return set(self._entry_points)

    @property
    def end_points(self) -> Set[str]:
        return set(self._end_points)


class GraphExecutor:
    """Executes a graph with middleware support."""

    def __init__(
        self,
        graph: Graph,
        cache: Optional[AbstractCache] = None,
        inference_client: Optional[BaseInferenceClient] = None,
        middleware: Optional[List[Middleware]] = None,
        max_iterations: int = 100,
        parallel: bool = False,
    ):
        self.graph = graph
        self.cache = cache
        self.inference_client = inference_client
        self.middleware = middleware or []
        self.max_iterations = max_iterations
        self.parallel = parallel

    def _create_context(self) -> ExecutionContext:
        return ExecutionContext(
            graph_id=self.graph.graph_id,
            execution_id=str(uuid.uuid4()),
            cache=self.cache,
            inference_client=self.inference_client,
        )

    async def _run_middleware_before(
        self, node: Node, state: Any, context: ExecutionContext
    ) -> Any:
        for mw in self.middleware:
            state = await mw.before_node(node, state, context)
        return state

    async def _run_middleware_after(
        self, node: Node, result: NodeResult, state: Any, context: ExecutionContext
    ) -> Any:
        for mw in self.middleware:
            state = await mw.after_node(node, result, state, context)
        return state

    async def _run_middleware_error(
        self, node: Node, error: Exception, context: ExecutionContext
    ) -> None:
        for mw in self.middleware:
            await mw.on_error(node, error, context)

    async def _execute_node(
        self, node: Node, state: Any, context: ExecutionContext
    ) -> NodeResult:
        node._status = NodeStatus.RUNNING
        result = NodeResult(
            node_id=node.node_id,
            status=NodeStatus.RUNNING,
            start_time=time.time(),
        )
        state = await self._run_middleware_before(node, state, context)
        try:
            output = await node.execute(state, context)
            result.status = NodeStatus.COMPLETED
            result.output = output
            node._status = NodeStatus.COMPLETED
        except Exception as e:
            result.status = NodeStatus.FAILED
            result.error = str(e)
            node._status = NodeStatus.FAILED
            await self._run_middleware_error(node, e, context)
            raise ExecutionError(f"Node '{node.name}' failed: {e}") from e
        finally:
            result.end_time = time.time()
        await self._run_middleware_after(node, result, state, context)
        context.record_result(result)
        return result

    async def execute(self, initial_state: Any = None) -> Dict[str, NodeResult]:
        context = self._create_context()
        state = initial_state

        if not self.graph.entry_points:
            raise GraphError("Graph has no entry points defined")

        visited: Set[str] = set()
        queue: List[str] = list(self.graph.entry_points)
        iterations = 0

        while queue and iterations < self.max_iterations:
            iterations += 1
            current_id = queue.pop(0)

            if current_id in visited:
                continue

            node = self.graph.get_node(current_id)
            if node is None:
                raise NodeNotFoundError(f"Node '{current_id}' not found")

            result = await self._execute_node(node, state, context)
            visited.add(current_id)

            if result.output is not None:
                state = result.output

            if current_id in self.graph.end_points:
                continue

            edges = self.graph.get_edges(current_id)
            for edge in edges:
                if edge.is_active(result.output):
                    if edge.target_id not in visited:
                        queue.append(edge.target_id)

        if iterations >= self.max_iterations:
            raise ExecutionError(f"Graph execution exceeded maximum iterations ({self.max_iterations})")

        return context.get_all_results()

    async def execute_with_state(
        self, initial_state: Any = None
    ) -> Tuple[Any, Dict[str, NodeResult]]:
        context = self._create_context()
        state = initial_state

        if not self.graph.entry_points:
            raise GraphError("Graph has no entry points defined")

        visited: Set[str] = set()
        queue: List[str] = list(self.graph.entry_points)
        iterations = 0
        final_state = state

        while queue and iterations < self.max_iterations:
            iterations += 1
            current_id = queue.pop(0)

            if current_id in visited:
                continue

            node = self.graph.get_node(current_id)
            if node is None:
                raise NodeNotFoundError(f"Node '{current_id}' not found")

            result = await self._execute_node(node, state, context)
            visited.add(current_id)

            if result.output is not None:
                state = result.output
                final_state = state

            if current_id in self.graph.end_points:
                continue

            edges = self.graph.get_edges(current_id)
            for edge in edges:
                if edge.is_active(result.output):
                    if edge.target_id not in visited:
                        queue.append(edge.target_id)

        if iterations >= self.max_iterations:
            raise ExecutionError(f"Graph execution exceeded maximum iterations ({self.max_iterations})")

        return final_state, context.get_all_results()


# ---------------------------------------------------------------------------
# LLM Directed Graph Execution
# ---------------------------------------------------------------------------

class LLMDirectedExecutor:
    """Uses an LLM to direct graph execution flow."""

    def __init__(
        self,
        graph: Graph,
        director_client: BaseInferenceClient,
        cache: Optional[AbstractCache] = None,
        middleware: Optional[List[Middleware]] = None,
        max_iterations: int = 50,
        system_prompt: Optional[str] = None,
    ):
        self.graph = graph
        self.director_client = director_client
        self.cache = cache
        self.middleware = middleware or []
        self.max_iterations = max_iterations
        self.system_prompt = system_prompt or (
            "You are a graph execution director. Given the current state and available next nodes, "
            "decide which node to execute next. Respond with only the node ID or name."
        )

    async def _get_next_node(
        self,
        current_node_id: str,
        state: Any,
        available_nodes: List[str],
        context: ExecutionContext,
    ) -> Optional[str]:
        if not available_nodes:
            return None
        if len(available_nodes) == 1:
            return available_nodes[0]

        node_descriptions = []
        for nid in available_nodes:
            node = self.graph.get_node(nid)
            if node:
                node_descriptions.append(f"- {nid}: {node.name}")

        prompt = (
            f"Current node: {current_node_id}\n"
            f"Current state: {json.dumps(state, default=str)[:500]}\n"
            f"Available next nodes:\n" + "\n".join(node_descriptions) + "\n\n"
            f"Which node should execute next? Respond with only the node ID."
        )

        messages = [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt),
            Message(role=MessageRole.USER, content=prompt),
        ]

        response = await self.director_client.complete(messages=messages, temperature=0.1)
        chosen = response.content.strip()

        if chosen in available_nodes:
            return chosen
        for nid in available_nodes:
            node = self.graph.get_node(nid)
            if node and (node.name == chosen or nid.startswith(chosen)):
                return nid
        return available_nodes[0]

    async def execute(self, initial_state: Any = None) -> Tuple[Any, Dict[str, NodeResult]]:
        context = ExecutionContext(
            graph_id=self.graph.graph_id,
            execution_id=str(uuid.uuid4()),
            cache=self.cache,
            inference_client=self.director_client,
        )
        state = initial_state
        executor = GraphExecutor(
            graph=self.graph,
            cache=self.cache,
            inference_client=self.director_client,
            middleware=self.middleware,
        )

        if not self.graph.entry_points:
            raise GraphError("Graph has no entry points defined")

        current_ids = list(self.graph.entry_points)
        visited: Set[str] = set()
        iterations = 0
        final_state = state

        while current_ids and iterations < self.max_iterations:
            iterations += 1
            current_id = current_ids[0]

            if current_id in visited:
                current_ids.pop(0)
                continue

            node = self.graph.get_node(current_id)
            if node is None:
                raise NodeNotFoundError(f"Node '{current_id}' not found")

            result = await executor._execute_node(node, state, context)
            visited.add(current_id)

            if result.output is not None:
                state = result.output
                final_state = state

            if current_id in self.graph.end_points:
                break

            edges = self.graph.get_edges(current_id)
            available = [e.target_id for e in edges if e.is_active(result.output) and e.target_id not in visited]

            if available:
                next_id = await self._get_next_node(current_id, state, available, context)
                current_ids = [next_id] if next_id else []
            else:
                current_ids = []

        return final_state, context.get_all_results()


# ---------------------------------------------------------------------------
# Agent Builder
# ---------------------------------------------------------------------------

class AgentBuilder:
    """Fluent builder for creating AI agents."""

    def __init__(self, name: str = "Agent"):
        self.name = name
        self._graph = Graph(name=name)
        self._cache: Optional[AbstractCache] = None
        self._inference_client: Optional[BaseInferenceClient] = None
        self._middleware: List[Middleware] = []
        self._max_iterations = 100
        self._llm_directed = False
        self._director_client: Optional[BaseInferenceClient] = None

    def with_cache(self, cache: AbstractCache) -> "AgentBuilder":
        self._cache = cache
        return self

    def with_inference_client(self, client: BaseInferenceClient) -> "AgentBuilder":
        self._inference_client = client
        return self

    def with_middleware(self, middleware: Middleware) -> "AgentBuilder":
        self._middleware.append(middleware)
        return self

    def with_max_iterations(self, max_iterations: int) -> "AgentBuilder":
        self._max_iterations = max_iterations
        return self

    def with_llm_direction(self, director_client: BaseInferenceClient) -> "AgentBuilder":
        self._llm_directed = True
        self._director_client = director_client
        return self

    def add_node(self, node: Node, entry: bool = False, end: bool = False) -> "AgentBuilder":
        self._graph.add_node(node, entry=entry, end=end)
        return self

    def add_edge(
        self,
        source: Union[Node, str],
        target: Union[Node, str],
        condition: Optional[Callable[[Any], bool]] = None,
        label: Optional[str] = None,
    ) -> "AgentBuilder":
        self._graph.add_edge(source, target, condition, label)
        return self

    def build(self) -> "Agent":
        return Agent(
            name=self.name,
            graph=self._graph,
            cache=self._cache,
            inference_client=self._inference_client,
            middleware=self._middleware,
            max_iterations=self._max_iterations,
            llm_directed=self._llm_directed,
            director_client=self._director_client,
        )


class Agent:
    """An AI agent that executes a graph."""

    def __init__(
        self,
        name: str,
        graph: Graph,
        cache: Optional[AbstractCache] = None,
        inference_client: Optional[BaseInferenceClient] = None,
        middleware: Optional[List[Middleware]] = None,
        max_iterations: int = 100,
        llm_directed: bool = False,
        director_client: Optional[BaseInferenceClient] = None,
    ):
        self.name = name
        self.graph = graph
        self.cache = cache
        self.inference_client = inference_client
        self.middleware = middleware or []
        self.max_iterations = max_iterations
        self.llm_directed = llm_directed
        self.director_client = director_client
        self._state_manager: Optional[GraphState] = None

    async def run(self, initial_state: Any = None) -> Tuple[Any, Dict[str, NodeResult]]:
        if self._state_manager is None:
            self._state_manager = GraphState(initial_state)

        if self.llm_directed and self.director_client:
            executor = LLMDirectedExecutor(
                graph=self.graph,
                director_client=self.director_client,
                cache=self.cache,
                middleware=self.middleware,
                max_iterations=self.max_iterations,
            )
            final_state, results = await executor.execute(initial_state)
        else:
            executor = GraphExecutor(
                graph=self.graph,
                cache=self.cache,
                inference_client=self.inference_client,
                middleware=self.middleware,
                max_iterations=self.max_iterations,
            )
            final_state, results = await executor.execute_with_state(initial_state)

        self._state_manager.update(final_state)
        return final_state, results

    def snapshot_state(self, name: str) -> None:
        if self._state_manager:
            self._state_manager.snapshot(name)

    def restore_state(self, name: str) -> None:
        if self._state_manager:
            self._state_manager.restore(name)

    @property
    def current_state(self) -> Any:
        if self._state_manager:
            return self._state_manager.state
        return None

    @staticmethod
    def builder(name: str = "Agent") -> AgentBuilder:
        return AgentBuilder(name)


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def function_node(
    node_id: Optional[str] = None,
    name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Callable:
    """Decorator to create a FunctionNode from a function."""
    def decorator(func: Callable) -> FunctionNode:
        return FunctionNode(func=func, node_id=node_id, name=name or func.__name__, metadata=metadata)
    return decorator


def create_openai_client(
    model: str = "gpt-4o",
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> OpenAIInferenceClient:
    return OpenAIInferenceClient(model=model, api_key=api_key, **kwargs)


def create_anthropic_client(
    model: str = "claude-3-5-sonnet-20241022",
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> AnthropicInferenceClient:
    return AnthropicInferenceClient(model=model, api_key=api_key, **kwargs)


def create_in_memory_cache(prefix: str = "", suffix: str = "") -> InMemoryCache:
    return InMemoryCache(prefix=prefix, suffix=suffix)


def create_redis_cache(
    url: str = "redis://localhost:6379",
    prefix: str = "",
    suffix: str = "",
    db: int = 0,
) -> RedisCache:
    return RedisCache(url=url, prefix=prefix, suffix=suffix, db=db)


# ---------------------------------------------------------------------------
# Pipeline Helper
# ---------------------------------------------------------------------------

class Pipeline:
    """A simple linear pipeline of nodes."""

    def __init__(
        self,
        name: str = "Pipeline",
        cache: Optional[AbstractCache] = None,
        inference_client: Optional[BaseInferenceClient] = None,
        middleware: Optional[List[Middleware]] = None,
    ):
        self.name = name
        self.cache = cache
        self.inference_client = inference_client
        self.middleware = middleware or []
        self._nodes: List[Node] = []

    def add_step(self, node: Node) -> "Pipeline":
        self._nodes.append(node)
        return self

    def build_graph(self) -> Graph:
        graph = Graph(name=self.name)
        for i, node in enumerate(self._nodes):
            is_entry = i == 0
            is_end = i == len(self._nodes) - 1
            graph.add_node(node, entry=is_entry, end=is_end)
        for i in range(len(self._nodes) - 1):
            graph.add_edge(self._nodes[i], self._nodes[i + 1])
        return graph

    async def run(self, initial_state: Any = None) -> Tuple[Any, Dict[str, NodeResult]]:
        graph = self.build_graph()
        executor = GraphExecutor(
            graph=graph,
            cache=self.cache,
            inference_client=self.inference_client,
            middleware=self.middleware,
        )
        return await executor.execute_with_state(initial_state)


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Exceptions
    "GraphError",
    "NodeNotFoundError",
    "CycleDetectedError",
    "ExecutionError",
    "InferenceError",
    "CacheError",
    # Cache
    "AbstractCache",
    "InMemoryCache",
    "RedisCache",
    # Token Usage
    "TokenUsage",
    # Tools
    "ToolDefinition",
    "ToolCall",
    "ToolResult",
    # Messages
    "MessageRole",
    "Message",
    # Inference
    "InferenceResponse",
    "StreamChunk",
    "BaseInferenceClient",
    "OpenAIInferenceClient",
    "AnthropicInferenceClient",
    # Graph
    "NodeStatus",
    "NodeResult",
    "GraphState",
    "Node",
    "FunctionNode",
    "LLMNode",
    "ConditionalNode",
    "Edge",
    "Graph",
    # Middleware
    "Middleware",
    "LoggingMiddleware",
    "CachingMiddleware",
    "OpenTelemetryMiddleware",
    # Execution
    "ExecutionContext",
    "GraphExecutor",
    "LLMDirectedExecutor",
    # Agent
    "AgentBuilder",
    "Agent",
    # Pipeline
    "Pipeline",
    # Utilities
    "function_node",
    "create_openai_client",
    "create_anthropic_client",
    "create_in_memory_cache",
    "create_redis_cache",
]