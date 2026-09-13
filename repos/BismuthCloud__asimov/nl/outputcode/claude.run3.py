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
    List,
    Optional,
    Set,
    Tuple,
    Type,
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


# ---------------------------------------------------------------------------
# Enums and Constants
# ---------------------------------------------------------------------------

class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EdgeType(Enum):
    DEFAULT = "default"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GraphError(Exception):
    pass


class CycleDetectedError(GraphError):
    pass


class NodeNotFoundError(GraphError):
    pass


class InferenceError(Exception):
    pass


class CacheError(Exception):
    pass


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class Message:
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.name:
            d["name"] = self.name
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        return d


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass
class InferenceResponse:
    content: str
    model: str
    usage: TokenUsage
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: Optional[str] = None
    cached: bool = False
    raw: Optional[Dict[str, Any]] = None


@dataclass
class StreamChunk:
    content: str
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class GraphState:
    data: Dict[str, Any] = field(default_factory=dict)
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> "GraphState":
        import copy
        return GraphState(
            data=copy.deepcopy(self.data),
            messages=list(self.messages),
            metadata=copy.deepcopy(self.metadata),
        )

    def update(self, updates: Dict[str, Any]) -> None:
        self.data.update(updates)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def add_message(self, message: Message) -> None:
        self.messages.append(message)


# ---------------------------------------------------------------------------
# Snapshot Manager
# ---------------------------------------------------------------------------

class SnapshotManager:
    def __init__(self, max_snapshots: int = 50):
        self._snapshots: List[Tuple[str, GraphState]] = []
        self._max_snapshots = max_snapshots

    def save(self, label: str, state: GraphState) -> str:
        snapshot_id = f"{label}_{uuid.uuid4().hex[:8]}"
        self._snapshots.append((snapshot_id, state.snapshot()))
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots.pop(0)
        return snapshot_id

    def restore(self, snapshot_id: str) -> Optional[GraphState]:
        for sid, state in self._snapshots:
            if sid == snapshot_id:
                return state.snapshot()
        return None

    def list_snapshots(self) -> List[str]:
        return [sid for sid, _ in self._snapshots]

    def clear(self) -> None:
        self._snapshots.clear()


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class MiddlewareContext:
    def __init__(self, node_name: str, state: GraphState, metadata: Dict[str, Any]):
        self.node_name = node_name
        self.state = state
        self.metadata = metadata
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self.error: Optional[Exception] = None
        self.result: Any = None


class Middleware(ABC):
    @abstractmethod
    async def before_node(self, ctx: MiddlewareContext) -> None:
        pass

    @abstractmethod
    async def after_node(self, ctx: MiddlewareContext) -> None:
        pass

    async def on_error(self, ctx: MiddlewareContext) -> None:
        pass


class LoggingMiddleware(Middleware):
    def __init__(self, logger: Optional[Any] = None):
        import logging
        self._logger = logger or logging.getLogger(__name__)

    async def before_node(self, ctx: MiddlewareContext) -> None:
        self._logger.info(f"[Graph] Starting node: {ctx.node_name}")

    async def after_node(self, ctx: MiddlewareContext) -> None:
        elapsed = (ctx.end_time or time.time()) - ctx.start_time
        self._logger.info(
            f"[Graph] Completed node: {ctx.node_name} in {elapsed:.3f}s"
        )

    async def on_error(self, ctx: MiddlewareContext) -> None:
        self._logger.error(
            f"[Graph] Error in node: {ctx.node_name} - {ctx.error}"
        )


class TimingMiddleware(Middleware):
    def __init__(self):
        self.timings: Dict[str, List[float]] = defaultdict(list)

    async def before_node(self, ctx: MiddlewareContext) -> None:
        ctx.metadata["_timing_start"] = time.time()

    async def after_node(self, ctx: MiddlewareContext) -> None:
        start = ctx.metadata.get("_timing_start", ctx.start_time)
        elapsed = time.time() - start
        self.timings[ctx.node_name].append(elapsed)

    def get_average(self, node_name: str) -> Optional[float]:
        times = self.timings.get(node_name)
        if not times:
            return None
        return sum(times) / len(times)


# ---------------------------------------------------------------------------
# OpenTelemetry Integration
# ---------------------------------------------------------------------------

class TelemetryManager:
    def __init__(self, service_name: str = "ai-agent-framework"):
        self._service_name = service_name
        self._tracer: Optional[Any] = None
        self._enabled = OTEL_AVAILABLE

        if self._enabled:
            try:
                self._tracer = trace.get_tracer(service_name)
            except Exception:
                self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Any:
        if not self._enabled or not self._tracer:
            return _NoOpSpan()
        span = self._tracer.start_span(name)
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, str(v))
        return span

    def record_inference(
        self,
        span: Any,
        model: str,
        usage: TokenUsage,
        cached: bool = False,
    ) -> None:
        if not self._enabled:
            return
        try:
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.prompt_tokens", usage.prompt_tokens)
            span.set_attribute("llm.completion_tokens", usage.completion_tokens)
            span.set_attribute("llm.total_tokens", usage.total_tokens)
            span.set_attribute("llm.cached", cached)
        except Exception:
            pass


class _NoOpSpan:
    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def end(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Cache System
# ---------------------------------------------------------------------------

class AbstractCache(ABC):
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
    async def clear(self, pattern: Optional[str] = None) -> int:
        pass

    @abstractmethod
    async def publish(self, mailbox: str, message: Any) -> None:
        pass

    @abstractmethod
    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        pass


class InMemoryCache(AbstractCache):
    def __init__(self, prefix: str = "", suffix: str = ""):
        self._store: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        self._prefix = prefix
        self._suffix = suffix
        self._mailboxes: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    def _make_key(self, key: str) -> str:
        parts = []
        if self._prefix:
            parts.append(self._prefix)
        parts.append(key)
        if self._suffix:
            parts.append(self._suffix)
        return ":".join(parts)

    def _is_expired(self, full_key: str) -> bool:
        if full_key in self._expiry:
            if time.time() > self._expiry[full_key]:
                del self._store[full_key]
                del self._expiry[full_key]
                return True
        return False

    async def get(self, key: str) -> Optional[Any]:
        full_key = self._make_key(key)
        if self._is_expired(full_key):
            return None
        raw = self._store.get(full_key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        full_key = self._make_key(key)
        self._store[full_key] = json.dumps(value)
        if ttl is not None:
            self._expiry[full_key] = time.time() + ttl

    async def delete(self, key: str) -> None:
        full_key = self._make_key(key)
        self._store.pop(full_key, None)
        self._expiry.pop(full_key, None)

    async def exists(self, key: str) -> bool:
        full_key = self._make_key(key)
        if self._is_expired(full_key):
            return False
        return full_key in self._store

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        import fnmatch
        result = {}
        for full_key, raw in list(self._store.items()):
            if self._is_expired(full_key):
                continue
            if fnmatch.fnmatch(full_key, pattern):
                try:
                    result[full_key] = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    result[full_key] = raw
        return result

    async def clear(self, pattern: Optional[str] = None) -> int:
        import fnmatch
        if pattern is None:
            count = len(self._store)
            self._store.clear()
            self._expiry.clear()
            return count
        keys_to_delete = [
            k for k in list(self._store.keys())
            if fnmatch.fnmatch(k, pattern)
        ]
        for k in keys_to_delete:
            del self._store[k]
            self._expiry.pop(k, None)
        return len(keys_to_delete)

    async def publish(self, mailbox: str, message: Any) -> None:
        await self._mailboxes[mailbox].put(message)

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        queue = self._mailboxes[mailbox]
        while True:
            message = await queue.get()
            yield message


class RedisCache(AbstractCache):
    def __init__(
        self,
        url: str = "redis://localhost:6379",
        prefix: str = "",
        suffix: str = "",
        db: int = 0,
    ):
        if not REDIS_AVAILABLE:
            raise CacheError("redis package is not installed. Install with: pip install redis")
        self._url = url
        self._prefix = prefix
        self._suffix = suffix
        self._db = db
        self._client: Optional[Any] = None
        self._pubsub_clients: Dict[str, Any] = {}

    async def _get_client(self) -> Any:
        if self._client is None:
            self._client = aioredis.from_url(self._url, db=self._db, decode_responses=True)
        return self._client

    def _make_key(self, key: str) -> str:
        parts = []
        if self._prefix:
            parts.append(self._prefix)
        parts.append(key)
        if self._suffix:
            parts.append(self._suffix)
        return ":".join(parts)

    async def get(self, key: str) -> Optional[Any]:
        client = await self._get_client()
        full_key = self._make_key(key)
        raw = await client.get(full_key)
        if raw is None:
            return None
        return json.loads(raw)

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

    async def clear(self, pattern: Optional[str] = None) -> int:
        client = await self._get_client()
        if pattern is None:
            pattern = "*"
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
            async for raw_message in pubsub.listen():
                if raw_message["type"] == "message":
                    try:
                        yield json.loads(raw_message["data"])
                    except (json.JSONDecodeError, TypeError):
                        yield raw_message["data"]
        finally:
            await pubsub.unsubscribe(mailbox)
            await pubsub.close()

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None


# ---------------------------------------------------------------------------
# Inference Clients
# ---------------------------------------------------------------------------

class BaseInferenceClient(ABC):
    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        telemetry: Optional[TelemetryManager] = None,
        cache: Optional[AbstractCache] = None,
        cache_ttl: int = 3600,
    ):
        self._model = model
        self._api_key = api_key
        self._telemetry = telemetry or TelemetryManager()
        self._cache = cache
        self._cache_ttl = cache_ttl
        self._total_usage = TokenUsage()

    @property
    def model(self) -> str:
        return self._model

    @property
    def total_usage(self) -> TokenUsage:
        return self._total_usage

    def _make_cache_key(self, messages: List[Message], **kwargs) -> str:
        payload = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
            **kwargs,
        }
        import hashlib
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        use_cache: bool = False,
    ) -> Union[InferenceResponse, AsyncGenerator[StreamChunk, None]]:
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        pass


class MockInferenceClient(BaseInferenceClient):
    def __init__(
        self,
        model: str = "mock-model",
        response_template: str = "Mock response for: {content}",
        telemetry: Optional[TelemetryManager] = None,
        cache: Optional[AbstractCache] = None,
        cache_ttl: int = 3600,
    ):
        super().__init__(model, telemetry=telemetry, cache=cache, cache_ttl=cache_ttl)
        self._response_template = response_template
        self._call_count = 0

    @property
    def call_count(self) -> int:
        return self._call_count

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        use_cache: bool = False,
    ) -> Union[InferenceResponse, AsyncGenerator[StreamChunk, None]]:
        if stream:
            return self.stream(messages, tools, temperature, max_tokens)

        if use_cache and self._cache:
            cache_key = self._make_cache_key(messages, temperature=temperature)
            cached = await self._cache.get(cache_key)
            if cached:
                usage = TokenUsage(**cached["usage"])
                return InferenceResponse(
                    content=cached["content"],
                    model=self._model,
                    usage=usage,
                    tool_calls=cached.get("tool_calls"),
                    finish_reason=cached.get("finish_reason"),
                    cached=True,
                )

        span = self._telemetry.start_span(
            "inference.complete",
            {"llm.model": self._model, "llm.stream": False},
        )

        self._call_count += 1
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                last_user_msg = msg.content
                break

        content = self._response_template.format(content=last_user_msg)
        usage = TokenUsage(
            prompt_tokens=len(last_user_msg.split()),
            completion_tokens=len(content.split()),
            total_tokens=len(last_user_msg.split()) + len(content.split()),
        )
        self._total_usage = self._total_usage + usage

        tool_calls = None
        if tools:
            tool_calls = [
                {
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {
                        "name": tools[0].name,
                        "arguments": "{}",
                    },
                }
            ]

        response = InferenceResponse(
            content=content,
            model=self._model,
            usage=usage,
            tool_calls=tool_calls,
            finish_reason="stop",
            cached=False,
        )

        self._telemetry.record_inference(span, self._model, usage)
        span.end()

        if use_cache and self._cache:
            cache_key = self._make_cache_key(messages, temperature=temperature)
            await self._cache.set(
                cache_key,
                {
                    "content": content,
                    "usage": {
                        "prompt_tokens": usage.prompt_tokens,
                        "completion_tokens": usage.completion_tokens,
                        "total_tokens": usage.total_tokens,
                    },
                    "tool_calls": tool_calls,
                    "finish_reason": "stop",
                },
                ttl=self._cache_ttl,
            )

        return response

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        self._call_count += 1
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                last_user_msg = msg.content
                break

        content = self._response_template.format(content=last_user_msg)
        words = content.split()

        async def _gen():
            for i, word in enumerate(words):
                chunk_text = word + (" " if i < len(words) - 1 else "")
                yield StreamChunk(content=chunk_text)
                await asyncio.sleep(0)
            yield StreamChunk(content="", finish_reason="stop")

        return _gen()


class OpenAIInferenceClient(BaseInferenceClient):
    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        telemetry: Optional[TelemetryManager] = None,
        cache: Optional[AbstractCache] = None,
        cache_ttl: int = 3600,
        organization: Optional[str] = None,
    ):
        super().__init__(model, api_key=api_key, telemetry=telemetry, cache=cache, cache_ttl=cache_ttl)
        self._base_url = base_url
        self._organization = organization
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import openai
                kwargs: Dict[str, Any] = {}
                if self._api_key:
                    kwargs["api_key"] = self._api_key
                if self._base_url:
                    kwargs["base_url"] = self._base_url
                if self._organization:
                    kwargs["organization"] = self._organization
                self._client = openai.AsyncOpenAI(**kwargs)
            except ImportError:
                raise InferenceError("openai package is not installed. Install with: pip install openai")
        return self._client

    def _build_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in messages]

    def _build_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in tools]

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        use_cache: bool = False,
    ) -> Union[InferenceResponse, AsyncGenerator[StreamChunk, None]]:
        if stream:
            return self.stream(messages, tools, temperature, max_tokens)

        if use_cache and self._cache:
            cache_key = self._make_cache_key(messages, temperature=temperature)
            cached = await self._cache.get(cache_key)
            if cached:
                usage = TokenUsage(**cached["usage"])
                self._total_usage = self._total_usage + usage
                return InferenceResponse(
                    content=cached["content"],
                    model=self._model,
                    usage=usage,
                    tool_calls=cached.get("tool_calls"),
                    finish_reason=cached.get("finish_reason"),
                    cached=True,
                )

        span = self._telemetry.start_span(
            "inference.openai.complete",
            {"llm.model": self._model},
        )

        try:
            client = self._get_client()
            kwargs: Dict[str, Any] = {
                "model": self._model,
                "messages": self._build_messages(messages),
                "temperature": temperature,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            if tools:
                kwargs["tools"] = self._build_tools(tools)

            raw_response = await client.chat.completions.create(**kwargs)
            choice = raw_response.choices[0]
            content = choice.message.content or ""
            tool_calls = None
            if choice.message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in choice.message.tool_calls
                ]

            usage = TokenUsage(
                prompt_tokens=raw_response.usage.prompt_tokens,
                completion_tokens=raw_response.usage.completion_tokens,
                total_tokens=raw_response.usage.total_tokens,
            )
            self._total_usage = self._total_usage + usage
            self._telemetry.record_inference(span, self._model, usage)

            response = InferenceResponse(
                content=content,
                model=self._model,
                usage=usage,
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason,
                cached=False,
                raw=raw_response.model_dump() if hasattr(raw_response, "model_dump") else None,
            )

            if use_cache and self._cache:
                cache_key = self._make_cache_key(messages, temperature=temperature)
                await self._cache.set(
                    cache_key,
                    {
                        "content": content,
                        "usage": {
                            "prompt_tokens": usage.prompt_tokens,
                            "completion_tokens": usage.completion_tokens,
                            "total_tokens": usage.total_tokens,
                        },
                        "tool_calls": tool_calls,
                        "finish_reason": choice.finish_reason,
                    },
                    ttl=self._cache_ttl,
                )

            return response
        except Exception as e:
            raise InferenceError(f"OpenAI inference failed: {e}") from e
        finally:
            span.end()

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        client = self._get_client()
        kwargs: Dict[str, Any] = {
            "model": self._model,
            "messages": self._build_messages(messages),
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if tools:
            kwargs["tools"] = self._build_tools(tools)

        async def _gen():
            try:
                async with await client.chat.completions.create(**kwargs) as response:
                    async for chunk in response:
                        if chunk.choices:
                            delta = chunk.choices[0].delta
                            content = delta.content or ""
                            finish_reason = chunk.choices[0].finish_reason
                            yield StreamChunk(content=content, finish_reason=finish_reason)
            except Exception as e:
                raise InferenceError(f"OpenAI streaming failed: {e}") from e

        return _gen()


class AnthropicInferenceClient(BaseInferenceClient):
    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        telemetry: Optional[TelemetryManager] = None,
        cache: Optional[AbstractCache] = None,
        cache_ttl: int = 3600,
        max_tokens: int = 4096,
    ):
        super().__init__(model, api_key=api_key, telemetry=telemetry, cache=cache, cache_ttl=cache_ttl)
        self._default_max_tokens = max_tokens
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import anthropic
                kwargs: Dict[str, Any] = {}
                if self._api_key:
                    kwargs["api_key"] = self._api_key
                self._client = anthropic.AsyncAnthropic(**kwargs)
            except ImportError:
                raise InferenceError("anthropic package is not installed. Install with: pip install anthropic")
        return self._client

    def _build_messages(self, messages: List[Message]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        system_prompt = None
        user_messages = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_prompt = msg.content
            else:
                user_messages.append(msg.to_dict())
        return system_prompt, user_messages

    def _build_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
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
        stream: bool = False,
        use_cache: bool = False,
    ) -> Union[InferenceResponse, AsyncGenerator[StreamChunk, None]]:
        if stream:
            return self.stream(messages, tools, temperature, max_tokens)

        if use_cache and self._cache:
            cache_key = self._make_cache_key(messages, temperature=temperature)
            cached = await self._cache.get(cache_key)
            if cached:
                usage = TokenUsage(**cached["usage"])
                self._total_usage = self._total_usage + usage
                return InferenceResponse(
                    content=cached["content"],
                    model=self._model,
                    usage=usage,
                    tool_calls=cached.get("tool_calls"),
                    finish_reason=cached.get("finish_reason"),
                    cached=True,
                )

        span = self._telemetry.start_span(
            "inference.anthropic.complete",
            {"llm.model": self._model},
        )

        try:
            client = self._get_client()
            system_prompt, user_messages = self._build_messages(messages)
            effective_max_tokens = max_tokens or self._default_max_tokens

            kwargs: Dict[str, Any] = {
                "model": self._model,
                "messages": user_messages,
                "max_tokens": effective_max_tokens,
                "temperature": temperature,
            }
            if system_prompt:
                kwargs["system"] = system_prompt
            if tools:
                kwargs["tools"] = self._build_tools(tools)

            raw_response = await client.messages.create(**kwargs)
            content = ""
            tool_calls = None

            for block in raw_response.content:
                if hasattr(block, "text"):
                    content += block.text
                elif hasattr(block, "type") and block.type == "tool_use":
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append({
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.input),
                        },
                    })

            usage = TokenUsage(
                prompt_tokens=raw_response.usage.input_tokens,
                completion_tokens=raw_response.usage.output_tokens,
                total_tokens=raw_response.usage.input_tokens + raw_response.usage.output_tokens,
            )
            self._total_usage = self._total_usage + usage
            self._telemetry.record_inference(span, self._model, usage)

            response = InferenceResponse(
                content=content,
                model=self._model,
                usage=usage,
                tool_calls=tool_calls,
                finish_reason=raw_response.stop_reason,
                cached=False,
            )

            if use_cache and self._cache:
                cache_key = self._make_cache_key(messages, temperature=temperature)
                await self._cache.set(
                    cache_key,
                    {
                        "content": content,
                        "usage": {
                            "prompt_tokens": usage.prompt_tokens,
                            "completion_tokens": usage.completion_tokens,
                            "total_tokens": usage.total_tokens,
                        },
                        "tool_calls": tool_calls,
                        "finish_reason": raw_response.stop_reason,
                    },
                    ttl=self._cache_ttl,
                )

            return response
        except Exception as e:
            raise InferenceError(f"Anthropic inference failed: {e}") from e
        finally:
            span.end()

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        client = self._get_client()
        system_prompt, user_messages = self._build_messages(messages)
        effective_max_tokens = max_tokens or self._default_max_tokens

        kwargs: Dict[str, Any] = {
            "model": self._model,
            "messages": user_messages,
            "max_tokens": effective_max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = self._build_tools(tools)

        async def _gen():
            try:
                async with client.messages.stream(**kwargs) as response:
                    async for text in response.text_stream:
                        yield StreamChunk(content=text)
                    yield StreamChunk(content="", finish_reason="end_turn")
            except Exception as e:
                raise InferenceError(f"Anthropic streaming failed: {e}") from e

        return _gen()


# ---------------------------------------------------------------------------
# Graph Primitives
# ---------------------------------------------------------------------------

NodeFunction = Callable[["GraphState", Dict[str, Any]], Any]


@dataclass
class Edge:
    source: str
    target: str
    edge_type: EdgeType = EdgeType.DEFAULT
    condition: Optional[Callable[["GraphState"], bool]] = None
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class Node:
    def __init__(
        self,
        name: str,
        func: Optional[Callable] = None,
        description: str = "",
        retry_count: int = 0,
        retry_delay: float = 0.0,
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self._name = name
        self._func = func
        self._description = description
        self._retry_count = retry_count
        self._retry_delay = retry_delay
        self._timeout = timeout
        self._metadata = metadata or {}
        self._status = NodeStatus.PENDING

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def status(self) -> NodeStatus:
        return self._status

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata

    async def execute(self, state: GraphState, context: Dict[str, Any]) -> Any:
        if self._func is None:
            return None

        self._status = NodeStatus.RUNNING
        last_error: Optional[Exception] = None

        for attempt in range(self._retry_count + 1):
            try:
                if self._timeout:
                    result = await asyncio.wait_for(
                        self._call_func(state, context),
                        timeout=self._timeout,
                    )
                else:
                    result = await self._call_func(state, context)
                self._status = NodeStatus.COMPLETED
                return result
            except Exception as e:
                last_error = e
                if attempt < self._retry_count:
                    if self._retry_delay > 0:
                        await asyncio.sleep(self._retry_delay)
                else:
                    self._status = NodeStatus.FAILED
                    raise

        self._status = NodeStatus.FAILED
        raise last_error  # type: ignore

    async def _call_func(self, state: GraphState, context: Dict[str, Any]) -> Any:
        if asyncio.iscoroutinefunction(self._func):
            return await self._func(state, context)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._func, state, context)

    def reset(self) -> None:
        self._status = NodeStatus.PENDING

    def __repr__(self) -> str:
        return f"Node(name={self._name!r}, status={self._status.value})"


class LLMNode(Node):
    def __init__(
        self,
        name: str,
        client: BaseInferenceClient,
        prompt_template: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_cache: bool = False,
        description: str = "",
        retry_count: int = 0,
        retry_delay: float = 0.0,
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name=name,
            description=description,
            retry_count=retry_count,
            retry_delay=retry_delay,
            timeout=timeout,
            metadata=metadata,
        )
        self._client = client
        self._prompt_template = prompt_template
        self._system_prompt = system_prompt
        self._tools = tools
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._use_cache = use_cache
        self._last_response: Optional[InferenceResponse] = None

    @property
    def last_response(self) -> Optional[InferenceResponse]:
        return self._last_response

    async def execute(self, state: GraphState, context: Dict[str, Any]) -> InferenceResponse:
        self._status = NodeStatus.RUNNING
        try:
            messages = self._build_messages(state, context)
            response = await self._client.complete(
                messages=messages,
                tools=self._tools,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                use_cache=self._use_cache,
            )
            self._last_response = response
            state.add_message(Message(role=MessageRole.ASSISTANT, content=response.content))
            state.set(f"{self._name}_response", response.content)
            state.set(f"{self._name}_usage", {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            })
            self._status = NodeStatus.COMPLETED
            return response
        except Exception as e:
            self._status = NodeStatus.FAILED
            raise

    def _build_messages(self, state: GraphState, context: Dict[str, Any]) -> List[Message]:
        messages: List[Message] = []
        if self._system_prompt:
            messages.append(Message(role=MessageRole.SYSTEM, content=self._system_prompt))

        messages.extend(state.messages)

        if self._prompt_template:
            try:
                prompt = self._prompt_template.format(**state.data, **context)
            except KeyError:
                prompt = self._prompt_template
            messages.append(Message(role=MessageRole.USER, content=prompt))

        return messages


class RouterNode(Node):
    def __init__(
        self,
        name: str,
        client: BaseInferenceClient,
        routes: Dict[str, str],
        routing_prompt: str = "Based on the context, which route should be taken?",
        system_prompt: Optional[str] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name=name, description=description, metadata=metadata)
        self._client = client
        self._routes = routes
        self._routing_prompt = routing_prompt
        self._system_prompt = system_prompt
        self._selected_route: Optional[str] = None

    @property
    def selected_route(self) -> Optional[str]:
        return self._selected_route

    async def execute(self, state: GraphState, context: Dict[str, Any]) -> str:
        self._status = NodeStatus.RUNNING
        try:
            route_options = "\n".join([f"- {k}: {v}" for k, v in self._routes.items()])
            prompt = f"{self._routing_prompt}\n\nAvailable routes:\n{route_options}\n\nRespond with only the route key."

            messages: List[Message] = []
            if self._system_prompt:
                messages.append(Message(role=MessageRole.SYSTEM, content=self._system_prompt))
            messages.extend(state.messages)
            messages.append(Message(role=MessageRole.USER, content=prompt))

            response = await self._client.complete(messages=messages)
            selected = response.content.strip().lower()

            matched_route = None
            for route_key in self._routes:
                if route_key.lower() in selected:
                    matched_route = route_key
                    break

            if matched_route is None:
                matched_route = list(self._routes.keys())[0]

            self._selected_route = matched_route
            state.set(f"{self._name}_route", matched_route)
            self._status = NodeStatus.COMPLETED
            return matched_route
        except Exception as e:
            self._status = NodeStatus.FAILED
            raise


# ---------------------------------------------------------------------------
# Graph Engine
# ---------------------------------------------------------------------------

class Graph:
    def __init__(
        self,
        name: str = "graph",
        telemetry: Optional[TelemetryManager] = None,
        snapshot_manager: Optional[SnapshotManager] = None,
    ):
        self._name = name
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._adjacency: Dict[str, List[Edge]] = defaultdict(list)
        self._reverse_adjacency: Dict[str, List[str]] = defaultdict(list)
        self._entry_point: Optional[str] = None
        self._end_points: Set[str] = set()
        self._middleware: List[Middleware] = []
        self._telemetry = telemetry or TelemetryManager()
        self._snapshot_manager = snapshot_manager or SnapshotManager()
        self._execution_history: List[Dict[str, Any]] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def nodes(self) -> Dict[str, Node]:
        return dict(self._nodes)

    @property
    def edges(self) -> List[Edge]:
        return list(self._edges)

    @property
    def execution_history(self) -> List[Dict[str, Any]]:
        return list(self._execution_history)

    def add_node(self, node: Node) -> "Graph":
        if node.name in self._nodes:
            raise GraphError(f"Node '{node.name}' already exists in graph")
        self._nodes[node.name] = node
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType = EdgeType.DEFAULT,
        condition: Optional[Callable[[GraphState], bool]] = None,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Graph":
        if source not in self._nodes:
            raise NodeNotFoundError(f"Source node '{source}' not found")
        if target not in self._nodes:
            raise NodeNotFoundError(f"Target node '{target}' not found")

        edge = Edge(
            source=source,
            target=target,
            edge_type=edge_type,
            condition=condition,
            weight=weight,
            metadata=metadata or {},
        )
        self._edges.append(edge)
        self._adjacency[source].append(edge)
        self._reverse_adjacency[target].append(source)
        return self

    def set_entry_point(self, node_name: str) -> "Graph":
        if node_name not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_name}' not found")
        self._entry_point = node_name
        return self

    def set_end_point(self, node_name: str) -> "Graph":
        if node_name not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_name}' not found")
        self._end_points.add(node_name)
        return self

    def add_middleware(self, middleware: Middleware) -> "Graph":
        self._middleware.append(middleware)
        return self

    def validate(self) -> None:
        if not self._nodes:
            raise GraphError("Graph has no nodes")
        if self._entry_point is None:
            raise GraphError("Graph has no entry point")
        self._detect_cycles()

    def _detect_cycles(self) -> None:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for edge in self._adjacency.get(node, []):
                neighbor = edge.target
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        for node_name in self._nodes:
            if node_name not in visited:
                if dfs(node_name):
                    raise CycleDetectedError("Cycle detected in graph")

    def _get_next_nodes(self, current_node: str, state: GraphState) -> List[str]:
        edges = self._adjacency.get(current_node, [])
        next_nodes = []

        for edge in edges:
            if edge.edge_type == EdgeType.CONDITIONAL:
                if edge.condition and edge.condition(state):
                    next_nodes.append(edge.target)
            elif edge.edge_type == EdgeType.PARALLEL:
                next_nodes.append(edge.target)
            else:
                next_nodes.append(edge.target)

        return next_nodes

    async def _run_middleware_before(self, ctx: MiddlewareContext) -> None:
        for mw in self._middleware:
            await mw.before_node(ctx)

    async def _run_middleware_after(self, ctx: MiddlewareContext) -> None:
        for mw in reversed(self._middleware):
            await mw.after_node(ctx)

    async def _run_middleware_error(self, ctx: MiddlewareContext) -> None:
        for mw in reversed(self._middleware):
            await mw.on_error(ctx)

    async def _execute_node(
        self,
        node_name: str,
        state: GraphState,
        context: Dict[str, Any],
    ) -> Any:
        node = self._nodes[node_name]
        ctx = MiddlewareContext(node_name=node_name, state=state, metadata={})

        await self._run_middleware_before(ctx)
        span = self._telemetry.start_span(
            f"graph.node.{node_name}",
            {"graph.name": self._name, "node.name": node_name},
        )

        try:
            result = await node.execute(state, context)
            ctx.result = result
            ctx.end_time = time.time()
            await self._run_middleware_after(ctx)
            span.end()

            self._execution_history.append({
                "node": node_name,
                "status": "completed",
                "timestamp": ctx.end_time,
                "duration": ctx.end_time - ctx.start_time,
            })
            return result
        except Exception as e:
            ctx.error = e
            ctx.end_time = time.time()
            await self._run_middleware_error(ctx)
            span.end()

            self._execution_history.append({
                "node": node_name,
                "status": "failed",
                "timestamp": ctx.end_time,
                "error": str(e),
            })
            raise

    async def run(
        self,
        initial_state: Optional[GraphState] = None,
        context: Optional[Dict[str, Any]] = None,
        snapshot_interval: Optional[int] = None,
    ) -> GraphState:
        self.validate()

        state = initial_state or GraphState()
        context = context or {}

        for node in self._nodes.values():
            node.reset()

        span = self._telemetry.start_span(
            f"graph.run.{self._name}",
            {"graph.name": self._name},
        )

        try:
            current_nodes = [self._entry_point]
            visited: Set[str] = set()
            step_count = 0

            while current_nodes:
                next_batch: List[str] = []

                parallel_nodes = [
                    n for n in current_nodes
                    if any(
                        e.edge_type == EdgeType.PARALLEL
                        for e in self._adjacency.get(n, [])
                    )
                ]
                sequential_nodes = [n for n in current_nodes if n not in parallel_nodes]

                if parallel_nodes:
                    tasks = [
                        self._execute_node(node_name, state, context)
                        for node_name in parallel_nodes
                        if node_name not in visited
                    ]
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=False)
                        for node_name in parallel_nodes:
                            visited.add(node_name)
                            next_nodes = self._get_next_nodes(node_name, state)
                            next_batch.extend(
                                n for n in next_nodes
                                if n not in visited and n not in next_batch
                            )

                for node_name in sequential_nodes:
                    if node_name in visited:
                        continue

                    node = self._nodes[node_name]
                    result = await self._execute_node(node_name, state, context)
                    visited.add(node_name)

                    if isinstance(node, RouterNode) and node.selected_route:
                        route = node.selected_route
                        route_edges = [
                            e for e in self._adjacency.get(node_name, [])
                            if e.metadata.get("route") == route or e.target == route
                        ]
                        if route_edges:
                            next_batch.extend(
                                e.target for e in route_edges
                                if e.target not in visited
                            )
                        else:
                            next_nodes = self._get_next_nodes(node_name, state)
                            next_batch.extend(
                                n for n in next_nodes
                                if n not in visited and n not in next_batch
                            )
                    else:
                        next_nodes = self._get_next_nodes(node_name, state)
                        next_batch.extend(
                            n for n in next_nodes
                            if n not in visited and n not in next_batch
                        )

                    if self._end_points and node_name in self._end_points:
                        current_nodes = []
                        break

                step_count += 1
                if snapshot_interval and step_count % snapshot_interval == 0:
                    self._snapshot_manager.save(f"step_{step_count}", state)

                current_nodes = next_batch

            span.end()
            return state
        except Exception as e:
            span.end()
            raise

    def get_snapshot_manager(self) -> SnapshotManager:
        return self._snapshot_manager

    def restore_snapshot(self, snapshot_id: str) -> Optional[GraphState]:
        return self._snapshot_manager.restore(snapshot_id)

    def __repr__(self) -> str:
        return f"Graph(name={self._name!r}, nodes={list(self._nodes.keys())})"


# ---------------------------------------------------------------------------
# Graph Builder (Fluent API)
# ---------------------------------------------------------------------------

class GraphBuilder:
    def __init__(self, name: str = "graph"):
        self._graph = Graph(name=name)

    def with_telemetry(self, telemetry: TelemetryManager) -> "GraphBuilder":
        self._graph._telemetry = telemetry
        return self

    def with_snapshot_manager(self, manager: SnapshotManager) -> "GraphBuilder":
        self._graph._snapshot_manager = manager
        return self

    def node(
        self,
        name: str,
        func: Optional[Callable] = None,
        description: str = "",
        retry_count: int = 0,
        retry_delay: float = 0.0,
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "GraphBuilder":
        n = Node(
            name=name,
            func=func,
            description=description,
            retry_count=retry_count,
            retry_delay=retry_delay,
            timeout=timeout,
            metadata=metadata,
        )
        self._graph.add_node(n)
        return self

    def llm_node(
        self,
        name: str,
        client: BaseInferenceClient,
        prompt_template: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_cache: bool = False,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "GraphBuilder":
        n = LLMNode(
            name=name,
            client=client,
            prompt_template=prompt_template,
            system_prompt=system_prompt,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            use_cache=use_cache,
            description=description,
            metadata=metadata,
        )
        self._graph.add_node(n)
        return self

    def router_node(
        self,
        name: str,
        client: BaseInferenceClient,
        routes: Dict[str, str],
        routing_prompt: str = "Based on the context, which route should be taken?",
        system_prompt: Optional[str] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "GraphBuilder":
        n = RouterNode(
            name=name,
            client=client,
            routes=routes,
            routing_prompt=routing_prompt,
            system_prompt=system_prompt,
            description=description,
            metadata=metadata,
        )
        self._graph.add_node(n)
        return self

    def edge(
        self,
        source: str,
        target: str,
        condition: Optional[Callable[[GraphState], bool]] = None,
        edge_type: EdgeType = EdgeType.DEFAULT,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "GraphBuilder":
        self._graph.add_edge(
            source=source,
            target=target,
            edge_type=edge_type,
            condition=condition,
            weight=weight,
            metadata=metadata,
        )
        return self

    def conditional_edge(
        self,
        source: str,
        target: str,
        condition: Callable[[GraphState], bool],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "GraphBuilder":
        return self.edge(
            source=source,
            target=target,
            condition=condition,
            edge_type=EdgeType.CONDITIONAL,
            metadata=metadata,
        )

    def parallel_edge(
        self,
        source: str,
        target: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "GraphBuilder":
        return self.edge(
            source=source,
            target=target,
            edge_type=EdgeType.PARALLEL,
            metadata=metadata,
        )

    def entry_point(self, node_name: str) -> "GraphBuilder":
        self._graph.set_entry_point(node_name)
        return self

    def end_point(self, node_name: str) -> "GraphBuilder":
        self._graph.set_end_point(node_name)
        return self

    def middleware(self, mw: Middleware) -> "GraphBuilder":
        self._graph.add_middleware(mw)
        return self

    def build(self) -> Graph:
        return self._graph


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Agent:
    def __init__(
        self,
        name: str,
        graph: Graph,
        cache: Optional[AbstractCache] = None,
        telemetry: Optional[TelemetryManager] = None,
    ):
        self._name = name
        self._graph = graph
        self._cache = cache
        self._telemetry = telemetry or TelemetryManager()
        self._run_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def graph(self) -> Graph:
        return self._graph

    @property
    def run_count(self) -> int:
        return self._run_count

    async def run(
        self,
        input_data: Optional[Dict[str, Any]] = None,
        messages: Optional[List[Message]] = None,
        context: Optional[Dict[str, Any]] = None,
        snapshot_interval: Optional[int] = None,
    ) -> GraphState:
        state = GraphState()
        if input_data:
            state.update(input_data)
        if messages:
            for msg in messages:
                state.add_message(msg)

        self._run_count += 1
        span = self._telemetry.start_span(
            f"agent.run.{self._name}",
            {"agent.name": self._name, "agent.run_count": self._run_count},
        )

        try:
            result = await self._graph.run(
                initial_state=state,
                context=context,
                snapshot_interval=snapshot_interval,
            )
            span.end()
            return result
        except Exception as e:
            span.end()
            raise

    async def run_with_cache(
        self,
        cache_key: str,
        input_data: Optional[Dict[str, Any]] = None,
        messages: Optional[List[Message]] = None,
        context: Optional[Dict[str, Any]] = None,
        ttl: int = 3600,
    ) -> GraphState:
        if self._cache:
            cached = await self._cache.get(cache_key)
            if cached:
                state = GraphState(
                    data=cached.get("data", {}),
                    metadata=cached.get("metadata", {}),
                )
                return state

        result = await self.run(input_data=input_data, messages=messages, context=context)

        if self._cache:
            await self._cache.set(
                cache_key,
                {
                    "data": result.data,
                    "metadata": result.metadata,
                },
                ttl=ttl,
            )

        return result


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tuple[ToolDefinition, Callable]] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        func: Callable,
    ) -> None:
        definition = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
        )
        self._tools[name] = (definition, func)

    def tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
    ) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.register(name, description, parameters, func)
            return func
        return decorator

    def get_definition(self, name: str) -> Optional[ToolDefinition]:
        entry = self._tools.get(name)
        return entry[0] if entry else None

    def get_all_definitions(self) -> List[ToolDefinition]:
        return [entry[0] for entry in self._tools.values()]

    async def call(self, name: str, arguments: Union[str, Dict[str, Any]]) -> Any:
        entry = self._tools.get(name)
        if entry is None:
            raise ValueError(f"Tool '{name}' not found in registry")

        _, func = entry
        if isinstance(arguments, str):
            try:
                args = json.loads(arguments)
            except json.JSONDecodeError:
                args = {}
        else:
            args = arguments

        if asyncio.iscoroutinefunction(func):
            return await func(**args)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(**args))

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())


# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------

class PromptTemplate:
    def __init__(self, template: str, input_variables: Optional[List[str]] = None):
        self._template = template
        self._input_variables = input_variables or self._extract_variables()

    def _extract_variables(self) -> List[str]:
        import re
        return re.findall(r"\{(\w+)\}", self._template)

    @property
    def template(self) -> str:
        return self._template

    @property
    def input_variables(self) -> List[str]:
        return list(self._input_variables)

    def format(self, **kwargs: Any) -> str:
        return self._template.format(**kwargs)

    def to_message(self, role: MessageRole = MessageRole.USER, **kwargs: Any) -> Message:
        content = self.format(**kwargs)
        return Message(role=role, content=content)

    def __repr__(self) -> str:
        return f"PromptTemplate(variables={self._input_variables})"


class ChatPromptTemplate:
    def __init__(self, messages: List[Tuple[MessageRole, str]]):
        self._message_templates = messages

    def format_messages(self, **kwargs: Any) -> List[Message]:
        result = []
        for role, template in self._message_templates:
            content = template.format(**kwargs)
            result.append(Message(role=role, content=content))
        return result

    @classmethod
    def from_messages(cls, messages: List[Tuple[str, str]]) -> "ChatPromptTemplate":
        role_map = {
            "system": MessageRole.SYSTEM,
            "user": MessageRole.USER,
            "assistant": MessageRole.ASSISTANT,
        }
        converted = [
            (role_map.get(role, MessageRole.USER), template)
            for role, template in messages
        ]
        return cls(converted)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class Pipeline:
    def __init__(
        self,
        name: str,
        steps: Optional[List[Callable]] = None,
        cache: Optional[AbstractCache] = None,
    ):
        self._name = name
        self._steps: List[Callable] = steps or []
        self._cache = cache

    @property
    def name(self) -> str:
        return self._name

    def add_step(self, step: Callable) -> "Pipeline":
        self._steps.append(step)
        return self

    async def run(self, input_data: Any) -> Any:
        result = input_data
        for step in self._steps:
            if asyncio.iscoroutinefunction(step):
                result = await step(result)
            else:
                result = step(result)
        return result

    def __repr__(self) -> str:
        return f"Pipeline(name={self._name!r}, steps={len(self._steps)})"


# ---------------------------------------------------------------------------
# Framework Entry Point
# ---------------------------------------------------------------------------

class AgentFramework:
    def __init__(
        self,
        name: str = "ai-agent-framework",
        cache: Optional[AbstractCache] = None,
        telemetry: Optional[TelemetryManager] = None,
    ):
        self._name = name
        self._cache = cache or InMemoryCache()
        self._telemetry = telemetry or TelemetryManager(name)
        self._agents: Dict[str, Agent] = {}
        self._tool_registry = ToolRegistry()
        self._graphs: Dict[str, Graph] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def cache(self) -> AbstractCache:
        return self._cache

    @property
    def telemetry(self) -> TelemetryManager:
        return self._telemetry

    @property
    def tool_registry(self) -> ToolRegistry:
        return self._tool_registry

    def register_agent(self, agent: Agent) -> None:
        self._agents[agent.name] = agent

    def get_agent(self, name: str) -> Optional[Agent]:
        return self._agents.get(name)

    def register_graph(self, graph: Graph) -> None:
        self._graphs[graph.name] = graph

    def get_graph(self, name: str) -> Optional[Graph]:
        return self._graphs.get(name)

    def create_graph_builder(self, name: str = "graph") -> GraphBuilder:
        return GraphBuilder(name=name)

    def create_in_memory_cache(
        self,
        prefix: str = "",
        suffix: str = "",
    ) -> InMemoryCache:
        return InMemoryCache(prefix=prefix, suffix=suffix)

    def create_redis_cache(
        self,
        url: str = "redis://localhost:6379",
        prefix: str = "",
        suffix: str = "",
        db: int = 0,
    ) -> RedisCache:
        return RedisCache(url=url, prefix=prefix, suffix=suffix, db=db)

    def create_mock_client(
        self,
        model: str = "mock-model",
        response_template: str = "Mock response for: {content}",
    ) -> MockInferenceClient:
        return MockInferenceClient(
            model=model,
            response_template=response_template,
            telemetry=self._telemetry,
            cache=self._cache,
        )

    def create_openai_client(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> OpenAIInferenceClient:
        return OpenAIInferenceClient(
            model=model,
            api_key=api_key,
            base_url=base_url,
            telemetry=self._telemetry,
            cache=self._cache,
        )

    def create_anthropic_client(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
    ) -> AnthropicInferenceClient:
        return AnthropicInferenceClient(
            model=model,
            api_key=api_key,
            telemetry=self._telemetry,
            cache=self._cache,
        )

    def list_agents(self) -> List[str]:
        return list(self._agents.keys())

    def list_graphs(self) -> List[str]:
        return list(self._graphs.keys())

    def __repr__(self) -> str:
        return (
            f"AgentFramework(name={self._name!r}, "
            f"agents={len(self._agents)}, "
            f"graphs={len(self._graphs)})"
        )