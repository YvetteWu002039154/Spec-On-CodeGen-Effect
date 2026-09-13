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
    from opentelemetry import trace
    from opentelemetry.trace import Span, Tracer
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


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
# Telemetry
# ---------------------------------------------------------------------------

class TelemetryManager:
    def __init__(self, service_name: str = "ai-agent-framework"):
        self.service_name = service_name
        self._tracer: Optional[Any] = None
        self._spans: Dict[str, Any] = {}

        if OTEL_AVAILABLE:
            self._tracer = trace.get_tracer(service_name)

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        if not OTEL_AVAILABLE or self._tracer is None:
            return None
        span = self._tracer.start_span(name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        span_id = str(uuid.uuid4())
        self._spans[span_id] = span
        return span_id

    def end_span(self, span_id: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        if not OTEL_AVAILABLE or span_id not in self._spans:
            return
        span = self._spans.pop(span_id)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        span.end()

    def record_event(self, span_id: str, event_name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        if not OTEL_AVAILABLE or span_id not in self._spans:
            return
        self._spans[span_id].add_event(event_name, attributes=attributes or {})


_telemetry = TelemetryManager()


# ---------------------------------------------------------------------------
# Caching System
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
    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        pass

    @abstractmethod
    async def clear(self, pattern: Optional[str] = None) -> None:
        pass

    @abstractmethod
    async def publish(self, mailbox: str, message: Any) -> None:
        pass

    @abstractmethod
    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass


class InMemoryCache(AbstractCache):
    def __init__(self, prefix: str = "", suffix: str = ""):
        self._store: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
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
        if full_key in self._expiry:
            return time.time() > self._expiry[full_key]
        return False

    async def get(self, key: str) -> Optional[Any]:
        full_key = self._make_key(key)
        if self._is_expired(full_key):
            del self._store[full_key]
            del self._expiry[full_key]
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
        elif full_key in self._expiry:
            del self._expiry[full_key]

    async def delete(self, key: str) -> None:
        full_key = self._make_key(key)
        self._store.pop(full_key, None)
        self._expiry.pop(full_key, None)

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        import fnmatch
        result = {}
        for full_key, raw in list(self._store.items()):
            if self._is_expired(full_key):
                continue
            if fnmatch.fnmatch(full_key, pattern):
                result[full_key] = json.loads(raw)
        return result

    async def clear(self, pattern: Optional[str] = None) -> None:
        import fnmatch
        if pattern is None:
            self._store.clear()
            self._expiry.clear()
        else:
            keys_to_delete = [k for k in self._store if fnmatch.fnmatch(k, pattern)]
            for k in keys_to_delete:
                del self._store[k]
                self._expiry.pop(k, None)

    async def publish(self, mailbox: str, message: Any) -> None:
        await self._mailboxes[mailbox].put(message)

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        queue = self._mailboxes[mailbox]
        while True:
            message = await queue.get()
            yield message

    async def exists(self, key: str) -> bool:
        full_key = self._make_key(key)
        if self._is_expired(full_key):
            return False
        return full_key in self._store


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
        self.url = url
        self.prefix = prefix
        self.suffix = suffix
        self.db = db
        self._client: Optional[Any] = None
        self._pubsub: Optional[Any] = None

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

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        client = await self._get_client()
        keys = await client.keys(pattern)
        result = {}
        if keys:
            values = await client.mget(*keys)
            for k, v in zip(keys, values):
                if v is not None:
                    result[k] = json.loads(v)
        return result

    async def clear(self, pattern: Optional[str] = None) -> None:
        client = await self._get_client()
        if pattern is None:
            await client.flushdb()
        else:
            keys = await client.keys(pattern)
            if keys:
                await client.delete(*keys)

    async def publish(self, mailbox: str, message: Any) -> None:
        client = await self._get_client()
        await client.publish(mailbox, json.dumps(message))

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        client = await self._get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(mailbox)
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield json.loads(message["data"])

    async def exists(self, key: str) -> bool:
        client = await self._get_client()
        full_key = self._make_key(key)
        return bool(await client.exists(full_key))

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
# Messages and Tools
# ---------------------------------------------------------------------------

@dataclass
class Message:
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.name:
            d["name"] = self.name
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        return d


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Optional[Callable] = None

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
class InferenceResponse:
    content: str
    model: str
    usage: TokenUsage
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: Optional[str] = None
    raw: Optional[Any] = None


@dataclass
class StreamChunk:
    content: str
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


# ---------------------------------------------------------------------------
# Inference Clients
# ---------------------------------------------------------------------------

class BaseInferenceClient(ABC):
    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        telemetry: Optional[TelemetryManager] = None,
        cache: Optional[AbstractCache] = None,
        prompt_caching: bool = False,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.telemetry = telemetry or _telemetry
        self.cache = cache
        self.prompt_caching = prompt_caching
        self._total_usage = TokenUsage()

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        pass

    def _make_cache_key(self, messages: List[Message], **kwargs: Any) -> str:
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            **kwargs,
        }
        return f"inference:{hash(json.dumps(payload, sort_keys=True))}"

    async def _get_cached_response(self, cache_key: str) -> Optional[InferenceResponse]:
        if self.cache is None:
            return None
        cached = await self.cache.get(cache_key)
        if cached is None:
            return None
        usage = TokenUsage(**cached.get("usage", {}))
        return InferenceResponse(
            content=cached["content"],
            model=cached["model"],
            usage=usage,
            tool_calls=cached.get("tool_calls"),
            finish_reason=cached.get("finish_reason"),
        )

    async def _cache_response(self, cache_key: str, response: InferenceResponse, ttl: Optional[int] = 3600) -> None:
        if self.cache is None:
            return
        await self.cache.set(
            cache_key,
            {
                "content": response.content,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                    "cached_tokens": response.usage.cached_tokens,
                },
                "tool_calls": response.tool_calls,
                "finish_reason": response.finish_reason,
            },
            ttl=ttl,
        )

    @property
    def total_usage(self) -> TokenUsage:
        return self._total_usage


class OpenAIClient(BaseInferenceClient):
    def __init__(self, model: str = "gpt-4o", **kwargs: Any):
        super().__init__(model=model, **kwargs)
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        except ImportError:
            self._client = None

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
        **kwargs: Any,
    ) -> InferenceResponse:
        if self._client is None:
            raise InferenceError("openai package is not installed. Install with: pip install openai")

        span_id = self.telemetry.start_span(
            "openai.complete",
            {"model": self.model, "messages_count": len(messages)},
        )

        cache_key = self._make_cache_key(messages, temperature=temperature, max_tokens=max_tokens)
        if use_cache and self.prompt_caching:
            cached = await self._get_cached_response(cache_key)
            if cached is not None:
                self.telemetry.end_span(span_id, {"cache_hit": True})
                return cached

        try:
            params: Dict[str, Any] = {
                "model": self.model,
                "messages": [m.to_dict() for m in messages],
                "temperature": temperature,
                **kwargs,
            }
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            if tools:
                params["tools"] = [t.to_dict() for t in tools]

            response = await self._client.chat.completions.create(**params)
            choice = response.choices[0]
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                cached_tokens=getattr(response.usage, "prompt_tokens_details", {}).get("cached_tokens", 0)
                if hasattr(response.usage, "prompt_tokens_details") else 0,
            )
            self._total_usage = self._total_usage + usage

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

            result = InferenceResponse(
                content=choice.message.content or "",
                model=self.model,
                usage=usage,
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason,
                raw=response,
            )

            if use_cache and self.prompt_caching:
                await self._cache_response(cache_key, result)

            self.telemetry.end_span(span_id, {"finish_reason": choice.finish_reason})
            return result

        except Exception as e:
            self.telemetry.end_span(span_id, {"error": str(e)})
            raise InferenceError(f"OpenAI completion failed: {e}") from e

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        if self._client is None:
            raise InferenceError("openai package is not installed.")

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        if tools:
            params["tools"] = [t.to_dict() for t in tools]

        async with await self._client.chat.completions.create(**params) as stream:
            async for chunk in stream:
                if chunk.choices:
                    choice = chunk.choices[0]
                    delta = choice.delta
                    yield StreamChunk(
                        content=delta.content or "",
                        finish_reason=choice.finish_reason,
                    )


class AnthropicClient(BaseInferenceClient):
    def __init__(self, model: str = "claude-3-5-sonnet-20241022", **kwargs: Any):
        super().__init__(model=model, **kwargs)
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            self._anthropic = anthropic
        except ImportError:
            self._client = None
            self._anthropic = None

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
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
        **kwargs: Any,
    ) -> InferenceResponse:
        if self._client is None:
            raise InferenceError("anthropic package is not installed. Install with: pip install anthropic")

        span_id = self.telemetry.start_span(
            "anthropic.complete",
            {"model": self.model, "messages_count": len(messages)},
        )

        cache_key = self._make_cache_key(messages, temperature=temperature, max_tokens=max_tokens)
        if use_cache and self.prompt_caching:
            cached = await self._get_cached_response(cache_key)
            if cached is not None:
                self.telemetry.end_span(span_id, {"cache_hit": True})
                return cached

        try:
            system_prompt, converted_messages = self._convert_messages(messages)
            params: Dict[str, Any] = {
                "model": self.model,
                "messages": converted_messages,
                "max_tokens": max_tokens or 4096,
                **kwargs,
            }
            if system_prompt:
                params["system"] = system_prompt
            if tools:
                params["tools"] = [
                    {
                        "name": t.name,
                        "description": t.description,
                        "input_schema": t.parameters,
                    }
                    for t in tools
                ]

            response = await self._client.messages.create(**params)
            content_text = ""
            tool_calls = None

            for block in response.content:
                if hasattr(block, "text"):
                    content_text += block.text
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
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                cached_tokens=getattr(response.usage, "cache_read_input_tokens", 0),
            )
            self._total_usage = self._total_usage + usage

            result = InferenceResponse(
                content=content_text,
                model=self.model,
                usage=usage,
                tool_calls=tool_calls,
                finish_reason=response.stop_reason,
                raw=response,
            )

            if use_cache and self.prompt_caching:
                await self._cache_response(cache_key, result)

            self.telemetry.end_span(span_id, {"finish_reason": response.stop_reason})
            return result

        except Exception as e:
            self.telemetry.end_span(span_id, {"error": str(e)})
            raise InferenceError(f"Anthropic completion failed: {e}") from e

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        if self._client is None:
            raise InferenceError("anthropic package is not installed.")

        system_prompt, converted_messages = self._convert_messages(messages)
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "max_tokens": max_tokens or 4096,
            **kwargs,
        }
        if system_prompt:
            params["system"] = system_prompt

        async with self._client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                yield StreamChunk(content=text)


class MockInferenceClient(BaseInferenceClient):
    def __init__(self, model: str = "mock-model", responses: Optional[List[str]] = None, **kwargs: Any):
        super().__init__(model=model, **kwargs)
        self._responses = responses or ["Mock response"]
        self._response_index = 0

    def _next_response(self) -> str:
        response = self._responses[self._response_index % len(self._responses)]
        self._response_index += 1
        return response

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        content = self._next_response()
        usage = TokenUsage(
            prompt_tokens=sum(len(m.content.split()) for m in messages),
            completion_tokens=len(content.split()),
            total_tokens=sum(len(m.content.split()) for m in messages) + len(content.split()),
        )
        self._total_usage = self._total_usage + usage
        return InferenceResponse(
            content=content,
            model=self.model,
            usage=usage,
            finish_reason="stop",
        )

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        content = self._next_response()
        words = content.split()
        for i, word in enumerate(words):
            chunk_text = word + (" " if i < len(words) - 1 else "")
            yield StreamChunk(
                content=chunk_text,
                finish_reason="stop" if i == len(words) - 1 else None,
            )
            await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# Graph State
# ---------------------------------------------------------------------------

@dataclass
class GraphState:
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def update(self, updates: Dict[str, Any]) -> None:
        self.data.update(updates)

    def snapshot(self) -> "GraphState":
        import copy
        return GraphState(
            data=copy.deepcopy(self.data),
            metadata=copy.deepcopy(self.metadata),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"data": self.data, "metadata": self.metadata}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GraphState":
        return cls(data=d.get("data", {}), metadata=d.get("metadata", {}))


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class Middleware(ABC):
    @abstractmethod
    async def before_node(self, node_id: str, state: GraphState) -> GraphState:
        pass

    @abstractmethod
    async def after_node(self, node_id: str, state: GraphState, result: Any) -> GraphState:
        pass

    async def on_error(self, node_id: str, state: GraphState, error: Exception) -> Optional[GraphState]:
        return None


class LoggingMiddleware(Middleware):
    def __init__(self, log_fn: Optional[Callable] = None):
        self._log = log_fn or print

    async def before_node(self, node_id: str, state: GraphState) -> GraphState:
        self._log(f"[Graph] Starting node: {node_id}")
        return state

    async def after_node(self, node_id: str, state: GraphState, result: Any) -> GraphState:
        self._log(f"[Graph] Completed node: {node_id}")
        return state

    async def on_error(self, node_id: str, state: GraphState, error: Exception) -> Optional[GraphState]:
        self._log(f"[Graph] Error in node {node_id}: {error}")
        return None


class CachingMiddleware(Middleware):
    def __init__(self, cache: AbstractCache, ttl: int = 3600):
        self._cache = cache
        self._ttl = ttl

    def _cache_key(self, node_id: str, state: GraphState) -> str:
        state_hash = hash(json.dumps(state.data, sort_keys=True, default=str))
        return f"node:{node_id}:{state_hash}"

    async def before_node(self, node_id: str, state: GraphState) -> GraphState:
        return state

    async def after_node(self, node_id: str, state: GraphState, result: Any) -> GraphState:
        return state


class TelemetryMiddleware(Middleware):
    def __init__(self, telemetry: Optional[TelemetryManager] = None):
        self._telemetry = telemetry or _telemetry
        self._span_ids: Dict[str, str] = {}

    async def before_node(self, node_id: str, state: GraphState) -> GraphState:
        span_id = self._telemetry.start_span(f"node.{node_id}", {"node_id": node_id})
        if span_id:
            self._span_ids[node_id] = span_id
        return state

    async def after_node(self, node_id: str, state: GraphState, result: Any) -> GraphState:
        span_id = self._span_ids.pop(node_id, None)
        if span_id:
            self._telemetry.end_span(span_id, {"status": "completed"})
        return state

    async def on_error(self, node_id: str, state: GraphState, error: Exception) -> Optional[GraphState]:
        span_id = self._span_ids.pop(node_id, None)
        if span_id:
            self._telemetry.end_span(span_id, {"status": "error", "error": str(error)})
        return None


# ---------------------------------------------------------------------------
# Graph Nodes and Edges
# ---------------------------------------------------------------------------

NodeFunction = Callable[[GraphState], Any]
ConditionalFunction = Callable[[GraphState], str]


@dataclass
class Edge:
    source: str
    target: str
    edge_type: EdgeType = EdgeType.DEFAULT
    condition: Optional[ConditionalFunction] = None
    label: Optional[str] = None


@dataclass
class NodeResult:
    node_id: str
    status: NodeStatus
    state: GraphState
    output: Any = None
    error: Optional[Exception] = None
    duration: float = 0.0


class Node:
    def __init__(
        self,
        node_id: str,
        func: NodeFunction,
        name: Optional[str] = None,
        description: Optional[str] = None,
        retry_count: int = 0,
        retry_delay: float = 1.0,
        timeout: Optional[float] = None,
    ):
        self.node_id = node_id
        self.func = func
        self.name = name or node_id
        self.description = description or ""
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.status = NodeStatus.PENDING

    async def execute(self, state: GraphState) -> Any:
        last_error: Optional[Exception] = None
        for attempt in range(self.retry_count + 1):
            try:
                if self.timeout is not None:
                    result = await asyncio.wait_for(
                        self._run(state), timeout=self.timeout
                    )
                else:
                    result = await self._run(state)
                return result
            except asyncio.TimeoutError as e:
                last_error = e
                if attempt < self.retry_count:
                    await asyncio.sleep(self.retry_delay)
            except Exception as e:
                last_error = e
                if attempt < self.retry_count:
                    await asyncio.sleep(self.retry_delay)
        raise last_error or Exception(f"Node {self.node_id} failed")

    async def _run(self, state: GraphState) -> Any:
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(state)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.func, state)


class LLMNode(Node):
    def __init__(
        self,
        node_id: str,
        client: BaseInferenceClient,
        prompt_template: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Tool]] = None,
        output_key: str = "llm_output",
        **kwargs: Any,
    ):
        async def llm_func(state: GraphState) -> Any:
            messages = []
            if self.system_prompt:
                messages.append(Message(role=MessageRole.SYSTEM, content=self.system_prompt))

            if self.prompt_template:
                user_content = self.prompt_template.format(**state.data)
            else:
                user_content = state.get("input", "")

            messages.append(Message(role=MessageRole.USER, content=str(user_content)))

            history = state.get("messages", [])
            if history:
                messages = history + [messages[-1]]

            response = await self.client.complete(messages, tools=self.tools)
            state.set(self.output_key, response.content)
            state.set("last_response", response)
            return response

        super().__init__(node_id=node_id, func=llm_func, **kwargs)
        self.client = client
        self.prompt_template = prompt_template
        self.system_prompt = system_prompt
        self.tools = tools
        self.output_key = output_key


class ConditionalNode(Node):
    def __init__(
        self,
        node_id: str,
        condition_func: ConditionalFunction,
        **kwargs: Any,
    ):
        async def wrapper(state: GraphState) -> str:
            if asyncio.iscoroutinefunction(condition_func):
                return await condition_func(state)
            return condition_func(state)

        super().__init__(node_id=node_id, func=wrapper, **kwargs)
        self.condition_func = condition_func


# ---------------------------------------------------------------------------
# State Snapshots
# ---------------------------------------------------------------------------

@dataclass
class Snapshot:
    snapshot_id: str
    node_id: str
    state: GraphState
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class SnapshotManager:
    def __init__(self, cache: Optional[AbstractCache] = None, max_snapshots: int = 100):
        self._snapshots: List[Snapshot] = []
        self._cache = cache
        self._max_snapshots = max_snapshots

    async def save(self, node_id: str, state: GraphState, metadata: Optional[Dict[str, Any]] = None) -> Snapshot:
        snapshot = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            node_id=node_id,
            state=state.snapshot(),
            timestamp=time.time(),
            metadata=metadata or {},
        )
        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]

        if self._cache is not None:
            await self._cache.set(
                f"snapshot:{snapshot.snapshot_id}",
                {
                    "snapshot_id": snapshot.snapshot_id,
                    "node_id": snapshot.node_id,
                    "state": snapshot.state.to_dict(),
                    "timestamp": snapshot.timestamp,
                    "metadata": snapshot.metadata,
                },
            )
        return snapshot

    async def restore(self, snapshot_id: str) -> Optional[Snapshot]:
        for snap in self._snapshots:
            if snap.snapshot_id == snapshot_id:
                return snap

        if self._cache is not None:
            data = await self._cache.get(f"snapshot:{snapshot_id}")
            if data:
                return Snapshot(
                    snapshot_id=data["snapshot_id"],
                    node_id=data["node_id"],
                    state=GraphState.from_dict(data["state"]),
                    timestamp=data["timestamp"],
                    metadata=data.get("metadata", {}),
                )
        return None

    def get_all(self) -> List[Snapshot]:
        return list(self._snapshots)

    def get_by_node(self, node_id: str) -> List[Snapshot]:
        return [s for s in self._snapshots if s.node_id == node_id]

    def latest(self) -> Optional[Snapshot]:
        if not self._snapshots:
            return None
        return max(self._snapshots, key=lambda s: s.timestamp)


# ---------------------------------------------------------------------------
# Graph Execution Engine
# ---------------------------------------------------------------------------

class Graph:
    START = "__start__"
    END = "__end__"

    def __init__(
        self,
        name: str = "graph",
        cache: Optional[AbstractCache] = None,
        telemetry: Optional[TelemetryManager] = None,
        snapshot_manager: Optional[SnapshotManager] = None,
        middleware: Optional[List[Middleware]] = None,
    ):
        self.name = name
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._entry_point: Optional[str] = None
        self._finish_points: Set[str] = set()
        self._cache = cache
        self._telemetry = telemetry or _telemetry
        self._snapshot_manager = snapshot_manager or SnapshotManager(cache=cache)
        self._middleware: List[Middleware] = middleware or []
        self._execution_history: List[NodeResult] = []

    def add_node(self, node: Node) -> "Graph":
        self._nodes[node.node_id] = node
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType = EdgeType.DEFAULT,
        condition: Optional[ConditionalFunction] = None,
        label: Optional[str] = None,
    ) -> "Graph":
        edge = Edge(
            source=source,
            target=target,
            edge_type=edge_type,
            condition=condition,
            label=label,
        )
        self._edges.append(edge)
        return self

    def add_conditional_edges(
        self,
        source: str,
        condition: ConditionalFunction,
        path_map: Dict[str, str],
    ) -> "Graph":
        for label, target in path_map.items():
            self._edges.append(
                Edge(
                    source=source,
                    target=target,
                    edge_type=EdgeType.CONDITIONAL,
                    condition=condition,
                    label=label,
                )
            )
        return self

    def set_entry_point(self, node_id: str) -> "Graph":
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found in graph")
        self._entry_point = node_id
        return self

    def set_finish_point(self, node_id: str) -> "Graph":
        self._finish_points.add(node_id)
        return self

    def add_middleware(self, middleware: Middleware) -> "Graph":
        self._middleware.append(middleware)
        return self

    def _get_outgoing_edges(self, node_id: str) -> List[Edge]:
        return [e for e in self._edges if e.source == node_id]

    def _detect_cycles(self) -> bool:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for edge in self._get_outgoing_edges(node_id):
                if edge.target not in visited:
                    if dfs(edge.target):
                        return True
                elif edge.target in rec_stack:
                    return True
            rec_stack.discard(node_id)
            return False

        for node_id in self._nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False

    def validate(self) -> None:
        if self._entry_point is None:
            raise GraphError("No entry point set for graph")
        if self._detect_cycles():
            raise CycleDetectedError("Graph contains a cycle")

    async def _run_middleware_before(self, node_id: str, state: GraphState) -> GraphState:
        for mw in self._middleware:
            state = await mw.before_node(node_id, state)
        return state

    async def _run_middleware_after(self, node_id: str, state: GraphState, result: Any) -> GraphState:
        for mw in self._middleware:
            state = await mw.after_node(node_id, state, result)
        return state

    async def _run_middleware_error(self, node_id: str, state: GraphState, error: Exception) -> Optional[GraphState]:
        for mw in reversed(self._middleware):
            recovered = await mw.on_error(node_id, state, error)
            if recovered is not None:
                return recovered
        return None

    async def _execute_node(self, node: Node, state: GraphState) -> Tuple[Any, GraphState]:
        start_time = time.time()
        node.status = NodeStatus.RUNNING

        state = await self._run_middleware_before(node.node_id, state)

        try:
            result = await node.execute(state)
            node.status = NodeStatus.COMPLETED
            state = await self._run_middleware_after(node.node_id, state, result)
            duration = time.time() - start_time

            node_result = NodeResult(
                node_id=node.node_id,
                status=NodeStatus.COMPLETED,
                state=state.snapshot(),
                output=result,
                duration=duration,
            )
            self._execution_history.append(node_result)

            await self._snapshot_manager.save(node.node_id, state)
            return result, state

        except Exception as e:
            node.status = NodeStatus.FAILED
            duration = time.time() - start_time

            recovered_state = await self._run_middleware_error(node.node_id, state, e)

            node_result = NodeResult(
                node_id=node.node_id,
                status=NodeStatus.FAILED,
                state=state.snapshot(),
                error=e,
                duration=duration,
            )
            self._execution_history.append(node_result)

            if recovered_state is not None:
                return None, recovered_state
            raise

    async def _determine_next_node(self, current_node_id: str, result: Any, state: GraphState) -> Optional[str]:
        outgoing = self._get_outgoing_edges(current_node_id)
        if not outgoing:
            return None

        conditional_edges = [e for e in outgoing if e.edge_type == EdgeType.CONDITIONAL]
        default_edges = [e for e in outgoing if e.edge_type == EdgeType.DEFAULT]

        if conditional_edges:
            condition_func = conditional_edges[0].condition
            if condition_func is not None:
                if asyncio.iscoroutinefunction(condition_func):
                    chosen_label = await condition_func(state)
                else:
                    chosen_label = condition_func(state)

                for edge in conditional_edges:
                    if edge.label == chosen_label or edge.target == chosen_label:
                        return edge.target

        if default_edges:
            return default_edges[0].target

        return None

    async def run(
        self,
        initial_state: Optional[Union[GraphState, Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> GraphState:
        self.validate()

        if initial_state is None:
            state = GraphState()
        elif isinstance(initial_state, dict):
            state = GraphState(data=initial_state)
        else:
            state = initial_state

        if config:
            state.metadata.update(config)

        span_id = self._telemetry.start_span(
            f"graph.{self.name}",
            {"graph_name": self.name, "entry_point": self._entry_point},
        )

        current_node_id = self._entry_point
        visited: Set[str] = set()

        try:
            while current_node_id is not None:
                if current_node_id in self._finish_points:
                    break

                if current_node_id not in self._nodes:
                    raise NodeNotFoundError(f"Node '{current_node_id}' not found")

                node = self._nodes[current_node_id]
                result, state = await self._execute_node(node, state)
                next_node_id = await self._determine_next_node(current_node_id, result, state)
                current_node_id = next_node_id

            self._telemetry.end_span(span_id, {"status": "completed"})
            return state

        except Exception as e:
            self._telemetry.end_span(span_id, {"status": "error", "error": str(e)})
            raise

    async def stream_run(
        self,
        initial_state: Optional[Union[GraphState, Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[NodeResult, None]:
        self.validate()

        if initial_state is None:
            state = GraphState()
        elif isinstance(initial_state, dict):
            state = GraphState(data=initial_state)
        else:
            state = initial_state

        if config:
            state.metadata.update(config)

        current_node_id = self._entry_point

        while current_node_id is not None:
            if current_node_id in self._finish_points:
                break

            if current_node_id not in self._nodes:
                raise NodeNotFoundError(f"Node '{current_node_id}' not found")

            node = self._nodes[current_node_id]
            start_time = time.time()
            node.status = NodeStatus.RUNNING

            state = await self._run_middleware_before(node.node_id, state)

            try:
                result = await node.execute(state)
                node.status = NodeStatus.COMPLETED
                state = await self._run_middleware_after(node.node_id, state, result)
                duration = time.time() - start_time

                node_result = NodeResult(
                    node_id=node.node_id,
                    status=NodeStatus.COMPLETED,
                    state=state.snapshot(),
                    output=result,
                    duration=duration,
                )
                self._execution_history.append(node_result)
                await self._snapshot_manager.save(node.node_id, state)
                yield node_result

                next_node_id = await self._determine_next_node(current_node_id, result, state)
                current_node_id = next_node_id

            except Exception as e:
                node.status = NodeStatus.FAILED
                duration = time.time() - start_time
                node_result = NodeResult(
                    node_id=node.node_id,
                    status=NodeStatus.FAILED,
                    state=state.snapshot(),
                    error=e,
                    duration=duration,
                )
                self._execution_history.append(node_result)
                yield node_result
                raise

    @property
    def execution_history(self) -> List[NodeResult]:
        return list(self._execution_history)

    @property
    def snapshot_manager(self) -> SnapshotManager:
        return self._snapshot_manager

    def get_node(self, node_id: str) -> Optional[Node]:
        return self._nodes.get(node_id)

    def get_nodes(self) -> Dict[str, Node]:
        return dict(self._nodes)

    def get_edges(self) -> List[Edge]:
        return list(self._edges)

    def reset(self) -> None:
        for node in self._nodes.values():
            node.status = NodeStatus.PENDING
        self._execution_history.clear()


# ---------------------------------------------------------------------------
# Graph Builder (Fluent API)
# ---------------------------------------------------------------------------

class GraphBuilder:
    def __init__(self, name: str = "graph"):
        self._graph = Graph(name=name)

    def with_cache(self, cache: AbstractCache) -> "GraphBuilder":
        self._graph._cache = cache
        self._graph._snapshot_manager = SnapshotManager(cache=cache)
        return self

    def with_telemetry(self, telemetry: TelemetryManager) -> "GraphBuilder":
        self._graph._telemetry = telemetry
        return self

    def with_middleware(self, middleware: Middleware) -> "GraphBuilder":
        self._graph.add_middleware(middleware)
        return self

    def with_snapshot_manager(self, manager: SnapshotManager) -> "GraphBuilder":
        self._graph._snapshot_manager = manager
        return self

    def add_node(
        self,
        node_id: str,
        func: NodeFunction,
        name: Optional[str] = None,
        description: Optional[str] = None,
        retry_count: int = 0,
        retry_delay: float = 1.0,
        timeout: Optional[float] = None,
    ) -> "GraphBuilder":
        node = Node(
            node_id=node_id,
            func=func,
            name=name,
            description=description,
            retry_count=retry_count,
            retry_delay=retry_delay,
            timeout=timeout,
        )
        self._graph.add_node(node)
        return self

    def add_llm_node(
        self,
        node_id: str,
        client: BaseInferenceClient,
        prompt_template: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Tool]] = None,
        output_key: str = "llm_output",
        **kwargs: Any,
    ) -> "GraphBuilder":
        node = LLMNode(
            node_id=node_id,
            client=client,
            prompt_template=prompt_template,
            system_prompt=system_prompt,
            tools=tools,
            output_key=output_key,
            **kwargs,
        )
        self._graph.add_node(node)
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType = EdgeType.DEFAULT,
        condition: Optional[ConditionalFunction] = None,
        label: Optional[str] = None,
    ) -> "GraphBuilder":
        self._graph.add_edge(source, target, edge_type, condition, label)
        return self

    def add_conditional_edges(
        self,
        source: str,
        condition: ConditionalFunction,
        path_map: Dict[str, str],
    ) -> "GraphBuilder":
        self._graph.add_conditional_edges(source, condition, path_map)
        return self

    def set_entry_point(self, node_id: str) -> "GraphBuilder":
        self._graph.set_entry_point(node_id)
        return self

    def set_finish_point(self, node_id: str) -> "GraphBuilder":
        self._graph.set_finish_point(node_id)
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
        client: BaseInferenceClient,
        tools: Optional[List[Tool]] = None,
        system_prompt: Optional[str] = None,
        max_iterations: int = 10,
        cache: Optional[AbstractCache] = None,
    ):
        self.name = name
        self.client = client
        self.tools = tools or []
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.cache = cache
        self._conversation_history: List[Message] = []
        self._tool_registry: Dict[str, Tool] = {t.name: t for t in self.tools}

    def add_tool(self, tool: Tool) -> None:
        self.tools.append(tool)
        self._tool_registry[tool.name] = tool

    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        tool = self._tool_registry.get(tool_name)
        if tool is None:
            return f"Error: Tool '{tool_name}' not found"
        if tool.function is None:
            return f"Error: Tool '{tool_name}' has no implementation"
        if asyncio.iscoroutinefunction(tool.function):
            return await tool.function(**arguments)
        return tool.function(**arguments)

    async def run(self, user_input: str) -> str:
        messages: List[Message] = []
        if self.system_prompt:
            messages.append(Message(role=MessageRole.SYSTEM, content=self.system_prompt))

        messages.extend(self._conversation_history)
        messages.append(Message(role=MessageRole.USER, content=user_input))

        for iteration in range(self.max_iterations):
            response = await self.client.complete(
                messages=messages,
                tools=self.tools if self.tools else None,
            )

            assistant_message = Message(
                role=MessageRole.ASSISTANT,
                content=response.content,
                tool_calls=response.tool_calls,
            )
            messages.append(assistant_message)

            if not response.tool_calls:
                self._conversation_history.append(Message(role=MessageRole.USER, content=user_input))
                self._conversation_history.append(assistant_message)
                return response.content

            for tool_call in response.tool_calls:
                tool_name = tool_call["function"]["name"]
                try:
                    arguments = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    arguments = {}

                tool_result = await self._execute_tool(tool_name, arguments)
                tool_message = Message(
                    role=MessageRole.TOOL,
                    content=str(tool_result),
                    tool_call_id=tool_call.get("id"),
                    name=tool_name,
                )
                messages.append(tool_message)

        return "Max iterations reached without a final response."

    async def stream_run(self, user_input: str) -> AsyncGenerator[str, None]:
        messages: List[Message] = []
        if self.system_prompt:
            messages.append(Message(role=MessageRole.SYSTEM, content=self.system_prompt))
        messages.extend(self._conversation_history)
        messages.append(Message(role=MessageRole.USER, content=user_input))

        full_content = ""
        async for chunk in await self.client.stream(messages=messages):
            full_content += chunk.content
            yield chunk.content

        self._conversation_history.append(Message(role=MessageRole.USER, content=user_input))
        self._conversation_history.append(Message(role=MessageRole.ASSISTANT, content=full_content))

    def clear_history(self) -> None:
        self._conversation_history.clear()

    @property
    def conversation_history(self) -> List[Message]:
        return list(self._conversation_history)


# ---------------------------------------------------------------------------
# LLM Directed Graph Execution
# ---------------------------------------------------------------------------

class LLMDirectedGraph:
    def __init__(
        self,
        client: BaseInferenceClient,
        nodes: Dict[str, Node],
        system_prompt: Optional[str] = None,
        cache: Optional[AbstractCache] = None,
        telemetry: Optional[TelemetryManager] = None,
    ):
        self.client = client
        self.nodes = nodes
        self.system_prompt = system_prompt or (
            "You are a graph execution controller. Given the current state and available nodes, "
            "decide which node to execute next. Respond with ONLY the node ID or 'END' to finish."
        )
        self.cache = cache
        self.telemetry = telemetry or _telemetry

    async def _decide_next_node(self, state: GraphState, available_nodes: List[str]) -> Optional[str]:
        node_descriptions = "\n".join(
            f"- {nid}: {self.nodes[nid].description}" for nid in available_nodes
        )
        prompt = (
            f"Current state: {json.dumps(state.data, default=str)}\n\n"
            f"Available nodes:\n{node_descriptions}\n\n"
            f"Which node should execute next? Reply with just the node ID or 'END'."
        )
        messages = [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt),
            Message(role=MessageRole.USER, content=prompt),
        ]
        response = await self.client.complete(messages)
        decision = response.content.strip()
        if decision == "END" or decision not in available_nodes:
            return None
        return decision

    async def run(
        self,
        initial_state: Optional[Union[GraphState, Dict[str, Any]]] = None,
        max_steps: int = 20,
    ) -> GraphState:
        if initial_state is None:
            state = GraphState()
        elif isinstance(initial_state, dict):
            state = GraphState(data=initial_state)
        else:
            state = initial_state

        available_nodes = list(self.nodes.keys())
        executed: List[str] = []

        for step in range(max_steps):
            remaining = [n for n in available_nodes if n not in executed]
            if not remaining:
                break

            next_node_id = await self._decide_next_node(state, remaining)
            if next_node_id is None:
                break

            node = self.nodes[next_node_id]
            if asyncio.iscoroutinefunction(node.func):
                result = await node.func(state)
            else:
                result = node.func(state)

            executed.append(next_node_id)

        return state


# ---------------------------------------------------------------------------
# Parallel Graph Execution
# ---------------------------------------------------------------------------

class ParallelGraph(Graph):
    async def run_parallel(
        self,
        node_ids: List[str],
        state: GraphState,
    ) -> Tuple[List[Any], GraphState]:
        tasks = []
        for node_id in node_ids:
            if node_id not in self._nodes:
                raise NodeNotFoundError(f"Node '{node_id}' not found")
            node = self._nodes[node_id]
            tasks.append(self._execute_node(node, state.snapshot()))

        results_and_states = await asyncio.gather(*tasks, return_exceptions=True)
        results = []
        for item in results_and_states:
            if isinstance(item, Exception):
                raise item
            result, node_state = item
            results.append(result)
            state.update(node_state.data)

        return results, state


# ---------------------------------------------------------------------------
# Framework Entry Point / Factory
# ---------------------------------------------------------------------------

class AgentFramework:
    def __init__(
        self,
        cache: Optional[AbstractCache] = None,
        telemetry: Optional[TelemetryManager] = None,
    ):
        self.cache = cache or InMemoryCache()
        self.telemetry = telemetry or TelemetryManager()

    def create_graph(self, name: str = "graph") -> GraphBuilder:
        return (
            GraphBuilder(name=name)
            .with_cache(self.cache)
            .with_telemetry(self.telemetry)
        )

    def create_agent(
        self,
        name: str,
        client: BaseInferenceClient,
        tools: Optional[List[Tool]] = None,
        system_prompt: Optional[str] = None,
        max_iterations: int = 10,
    ) -> Agent:
        return Agent(
            name=name,
            client=client,
            tools=tools,
            system_prompt=system_prompt,
            max_iterations=max_iterations,
            cache=self.cache,
        )

    def create_openai_client(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        prompt_caching: bool = False,
    ) -> OpenAIClient:
        return OpenAIClient(
            model=model,
            api_key=api_key,
            telemetry=self.telemetry,
            cache=self.cache if prompt_caching else None,
            prompt_caching=prompt_caching,
        )

    def create_anthropic_client(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        prompt_caching: bool = False,
    ) -> AnthropicClient:
        return AnthropicClient(
            model=model,
            api_key=api_key,
            telemetry=self.telemetry,
            cache=self.cache if prompt_caching else None,
            prompt_caching=prompt_caching,
        )

    def create_mock_client(
        self,
        model: str = "mock-model",
        responses: Optional[List[str]] = None,
    ) -> MockInferenceClient:
        return MockInferenceClient(
            model=model,
            responses=responses,
            telemetry=self.telemetry,
        )

    @staticmethod
    def create_redis_cache(
        url: str = "redis://localhost:6379",
        prefix: str = "",
        suffix: str = "",
        db: int = 0,
    ) -> RedisCache:
        return RedisCache(url=url, prefix=prefix, suffix=suffix, db=db)

    @staticmethod
    def create_memory_cache(prefix: str = "", suffix: str = "") -> InMemoryCache:
        return InMemoryCache(prefix=prefix, suffix=suffix)


# ---------------------------------------------------------------------------
# Utility decorators
# ---------------------------------------------------------------------------

def node(
    node_id: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    retry_count: int = 0,
    retry_delay: float = 1.0,
    timeout: Optional[float] = None,
) -> Callable:
    def decorator(func: Callable) -> Node:
        _node_id = node_id or func.__name__
        return Node(
            node_id=_node_id,
            func=func,
            name=name or _node_id,
            description=description or func.__doc__ or "",
            retry_count=retry_count,
            retry_delay=retry_delay,
            timeout=timeout,
        )
    return decorator


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
) -> Callable:
    def decorator(func: Callable) -> Tool:
        _name = name or func.__name__
        _description = description or func.__doc__ or ""
        _parameters = parameters or {"type": "object", "properties": {}, "required": []}
        return Tool(
            name=_name,
            description=_description,
            parameters=_parameters,
            function=func,
        )
    return decorator


# ---------------------------------------------------------------------------
# Example usage (runs when executed directly)
# ---------------------------------------------------------------------------

async def _example():
    framework = AgentFramework()
    mock_client = framework.create_mock_client(
        responses=["Hello! I'm an AI assistant.", "The answer is 42.", "Task completed."]
    )

    async def preprocess(state: GraphState) -> None:
        state.set("processed", True)
        state.set("input", state.get("input", "default input"))

    async def postprocess(state: GraphState) -> None:
        output = state.get("llm_output", "")
        state.set("final_output", f"Processed: {output}")

    def route_decision(state: GraphState) -> str:
        if state.get("processed"):
            return "llm_node"
        return "end"

    graph = (
        framework.create_graph("example")
        .add_node("preprocess", preprocess, description="Preprocesses input")
        .add_llm_node(
            "llm_node",
            mock_client,
            prompt_template="Answer this: {input}",
            output_key="llm_output",
        )
        .add_node("postprocess", postprocess, description="Postprocesses output")
        .add_edge("preprocess", "llm_node")
        .add_edge("llm_node", "postprocess")
        .set_entry_point("preprocess")
        .set_finish_point("postprocess")
        .build()
    )

    initial_state = GraphState(data={"input": "What is the meaning of life?"})
    final_state = await graph.run(initial_state)
    print(f"Final output: {final_state.get('final_output')}")
    print(f"Execution history: {[r.node_id for r in graph.execution_history]}")

    agent = framework.create_agent(
        name="test-agent",
        client=mock_client,
        system_prompt="You are a helpful assistant.",
    )
    response = await agent.run("Hello, how are you?")
    print(f"Agent response: {response}")

    cache = framework.create_memory_cache(prefix="test")
    await cache.set("key1", {"value": 1})
    await cache.set("key2", {"value": 2})
    val = await cache.get("key1")
    print(f"Cached value: {val}")
    all_vals = await cache.get_all("test:*")
    print(f"All cached values: {all_vals}")


if __name__ == "__main__":
    asyncio.run(_example())