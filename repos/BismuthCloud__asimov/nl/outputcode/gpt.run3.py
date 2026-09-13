from __future__ import annotations

import abc
import asyncio
import dataclasses
import hashlib
import json
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Deque,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

T = TypeVar("T")


class FrameworkError(Exception):
    pass


class ValidationError(FrameworkError):
    pass


class GraphError(FrameworkError):
    pass


class CacheError(FrameworkError):
    pass


class InferenceError(FrameworkError):
    pass


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
        )


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    name: str
    output: Any


@dataclass(frozen=True)
class InferenceChunk:
    text: str = ""
    tool_calls: Tuple[ToolCall, ...] = ()
    usage_delta: TokenUsage = field(default_factory=TokenUsage)


@dataclass(frozen=True)
class InferenceResponse:
    text: str
    tool_calls: Tuple[ToolCall, ...] = ()
    usage: TokenUsage = field(default_factory=TokenUsage)
    provider: str = ""
    model: str = ""
    cached: bool = False
    raw: Any = None


class JSONSerializer:
    @staticmethod
    def dumps(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=JSONSerializer._default)

    @staticmethod
    def loads(value: str) -> Any:
        return json.loads(value)

    @staticmethod
    def _default(obj: Any) -> Any:
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        if isinstance(obj, (set, frozenset)):
            return list(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class Cache(abc.ABC):
    @abc.abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    @abc.abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, key: str) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_all(self, keys: Sequence[str]) -> Dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    async def clear(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def with_namespace(self, prefix: str = "", suffix: str = "") -> "Cache":
        raise NotImplementedError

    @abc.abstractmethod
    def mailbox(self, name: str) -> "Mailbox":
        raise NotImplementedError


class Mailbox(abc.ABC):
    @abc.abstractmethod
    async def publish(self, message: Any) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def subscribe(self) -> AsyncGenerator[Any, None]:
        raise NotImplementedError


class _InMemoryMailbox(Mailbox):
    def __init__(self, channel: str, bus: "_InMemoryPubSubBus", serializer: JSONSerializer):
        self._channel = channel
        self._bus = bus
        self._serializer = serializer

    async def publish(self, message: Any) -> None:
        payload = self._serializer.dumps(message)
        await self._bus.publish(self._channel, payload)

    async def subscribe(self) -> AsyncGenerator[Any, None]:
        queue = await self._bus.subscribe(self._channel)
        try:
            while True:
                payload = await queue.get()
                yield self._serializer.loads(payload)
        finally:
            await self._bus.unsubscribe(self._channel, queue)


class _InMemoryPubSubBus:
    def __init__(self):
        self._channels: Dict[str, Set[asyncio.Queue[str]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, channel: str, payload: str) -> None:
        async with self._lock:
            queues = list(self._channels.get(channel, set()))
        for q in queues:
            q.put_nowait(payload)

    async def subscribe(self, channel: str) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue()
        async with self._lock:
            self._channels[channel].add(q)
        return q

    async def unsubscribe(self, channel: str, q: asyncio.Queue[str]) -> None:
        async with self._lock:
            if channel in self._channels and q in self._channels[channel]:
                self._channels[channel].remove(q)
                if not self._channels[channel]:
                    del self._channels[channel]


class RedisCache(Cache):
    def __init__(
        self,
        prefix: str = "",
        suffix: str = "",
        serializer: JSONSerializer = JSONSerializer(),
        _store: Optional[Dict[str, Tuple[Optional[float], str]]] = None,
        _bus: Optional[_InMemoryPubSubBus] = None,
    ):
        self._prefix = prefix
        self._suffix = suffix
        self._serializer = serializer
        self._store = _store if _store is not None else {}
        self._bus = _bus if _bus is not None else _InMemoryPubSubBus()
        self._lock = asyncio.Lock()

    def _ns(self, key: str) -> str:
        return f"{self._prefix}{key}{self._suffix}"

    def with_namespace(self, prefix: str = "", suffix: str = "") -> "Cache":
        return RedisCache(
            prefix=self._prefix + prefix,
            suffix=suffix + self._suffix,
            serializer=self._serializer,
            _store=self._store,
            _bus=self._bus,
        )

    def mailbox(self, name: str) -> Mailbox:
        channel = self._ns(f"mailbox:{name}")
        return _InMemoryMailbox(channel=channel, bus=self._bus, serializer=self._serializer)

    def _is_expired(self, expires_at: Optional[float]) -> bool:
        return expires_at is not None and time.time() >= expires_at

    async def get(self, key: str) -> Optional[Any]:
        k = self._ns(key)
        async with self._lock:
            item = self._store.get(k)
            if item is None:
                return None
            expires_at, payload = item
            if self._is_expired(expires_at):
                del self._store[k]
                return None
        try:
            return self._serializer.loads(payload)
        except Exception as e:
            raise CacheError(str(e)) from e

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        k = self._ns(key)
        try:
            payload = self._serializer.dumps(value)
        except Exception as e:
            raise CacheError(str(e)) from e
        expires_at = None if ttl_seconds is None else (time.time() + int(ttl_seconds))
        async with self._lock:
            self._store[k] = (expires_at, payload)

    async def delete(self, key: str) -> None:
        k = self._ns(key)
        async with self._lock:
            self._store.pop(k, None)

    async def get_all(self, keys: Sequence[str]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        now = time.time()
        async with self._lock:
            for key in keys:
                k = self._ns(key)
                item = self._store.get(k)
                if item is None:
                    continue
                expires_at, payload = item
                if expires_at is not None and now >= expires_at:
                    self._store.pop(k, None)
                    continue
                result[key] = payload
        out: Dict[str, Any] = {}
        for key, payload in result.items():
            try:
                out[key] = self._serializer.loads(payload)
            except Exception as e:
                raise CacheError(str(e)) from e
        return out

    async def clear(self) -> None:
        async with self._lock:
            if not self._prefix and not self._suffix:
                self._store.clear()
                return
            keys_to_delete = [k for k in self._store.keys() if k.startswith(self._prefix) and k.endswith(self._suffix)]
            for k in keys_to_delete:
                del self._store[k]


class TelemetrySpan(Protocol):
    def set_attribute(self, key: str, value: Any) -> None: ...
    def record_exception(self, exc: BaseException) -> None: ...
    def end(self) -> None: ...


class Telemetry(abc.ABC):
    @abc.abstractmethod
    def start_span(self, name: str, attributes: Optional[Mapping[str, Any]] = None) -> TelemetrySpan:
        raise NotImplementedError


class _NoopSpan:
    def __init__(self, _name: str, _attributes: Optional[Mapping[str, Any]] = None):
        self._ended = False

    def set_attribute(self, key: str, value: Any) -> None:
        return

    def record_exception(self, exc: BaseException) -> None:
        return

    def end(self) -> None:
        self._ended = True


class NoopTelemetry(Telemetry):
    def start_span(self, name: str, attributes: Optional[Mapping[str, Any]] = None) -> TelemetrySpan:
        return _NoopSpan(name, attributes)


class Middleware(abc.ABC):
    async def before_node(self, ctx: "ExecutionContext", node: "Node") -> None:
        return

    async def after_node(self, ctx: "ExecutionContext", node: "Node", result: Any) -> None:
        return

    async def on_error(self, ctx: "ExecutionContext", node: "Node", error: BaseException) -> None:
        return


@dataclass(frozen=True)
class StateSnapshot:
    snapshot_id: str
    created_at: float
    state: Dict[str, Any]


class StateStore:
    def __init__(self):
        self._snapshots: List[StateSnapshot] = []

    def snapshot(self, state: Mapping[str, Any]) -> StateSnapshot:
        snap = StateSnapshot(snapshot_id=str(uuid.uuid4()), created_at=time.time(), state=dict(state))
        self._snapshots.append(snap)
        return snap

    @property
    def snapshots(self) -> Tuple[StateSnapshot, ...]:
        return tuple(self._snapshots)

    def latest(self) -> Optional[StateSnapshot]:
        return self._snapshots[-1] if self._snapshots else None


class ExecutionContext:
    def __init__(
        self,
        *,
        initial_state: Optional[Mapping[str, Any]] = None,
        cache: Optional[Cache] = None,
        telemetry: Optional[Telemetry] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        enable_snapshotting: bool = True,
    ):
        self._state: Dict[str, Any] = dict(initial_state or {})
        self._cache = cache
        self._telemetry = telemetry or NoopTelemetry()
        self._middleware: Tuple[Middleware, ...] = tuple(middleware or ())
        self._state_store = StateStore()
        self._enable_snapshotting = bool(enable_snapshotting)
        self._node_results: Dict[str, Any] = {}
        self._node_errors: Dict[str, BaseException] = {}
        self._usage: TokenUsage = TokenUsage()

    @property
    def state(self) -> Dict[str, Any]:
        return self._state

    @property
    def cache(self) -> Optional[Cache]:
        return self._cache

    @property
    def telemetry(self) -> Telemetry:
        return self._telemetry

    @property
    def middleware(self) -> Tuple[Middleware, ...]:
        return self._middleware

    @property
    def state_store(self) -> StateStore:
        return self._state_store

    @property
    def node_results(self) -> Dict[str, Any]:
        return self._node_results

    @property
    def node_errors(self) -> Dict[str, BaseException]:
        return self._node_errors

    @property
    def usage(self) -> TokenUsage:
        return self._usage

    def add_usage(self, usage: TokenUsage) -> None:
        self._usage = self._usage + usage

    def snapshot(self) -> Optional[StateSnapshot]:
        if not self._enable_snapshotting:
            return None
        return self._state_store.snapshot(self._state)


class Node(abc.ABC):
    def __init__(self, node_id: str):
        if not node_id or not isinstance(node_id, str):
            raise ValidationError("node_id must be a non-empty string")
        self._id = node_id

    @property
    def id(self) -> str:
        return self._id

    @abc.abstractmethod
    async def run(self, ctx: ExecutionContext) -> Any:
        raise NotImplementedError


class FunctionNode(Node):
    def __init__(self, node_id: str, func: Callable[[ExecutionContext], Awaitable[Any]]):
        super().__init__(node_id=node_id)
        if not callable(func):
            raise ValidationError("func must be callable")
        self._func = func

    async def run(self, ctx: ExecutionContext) -> Any:
        return await self._func(ctx)


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str


class Graph:
    def __init__(self):
        self._nodes: Dict[str, Node] = {}
        self._out_edges: Dict[str, Set[str]] = defaultdict(set)
        self._in_edges: Dict[str, Set[str]] = defaultdict(set)

    def add_node(self, node: Node) -> None:
        if node.id in self._nodes:
            raise ValidationError(f"Duplicate node id: {node.id}")
        self._nodes[node.id] = node

    def add_edge(self, src: str, dst: str) -> None:
        if src not in self._nodes or dst not in self._nodes:
            raise ValidationError("Both src and dst must be added as nodes before adding an edge")
        if dst == src:
            raise ValidationError("Self edges are not allowed")
        self._out_edges[src].add(dst)
        self._in_edges[dst].add(src)

    @property
    def nodes(self) -> Mapping[str, Node]:
        return self._nodes

    def predecessors(self, node_id: str) -> Set[str]:
        return set(self._in_edges.get(node_id, set()))

    def successors(self, node_id: str) -> Set[str]:
        return set(self._out_edges.get(node_id, set()))

    def _topological_order(self) -> List[str]:
        indeg: Dict[str, int] = {nid: len(self._in_edges.get(nid, set())) for nid in self._nodes}
        q: Deque[str] = deque([nid for nid, d in indeg.items() if d == 0])
        order: List[str] = []
        while q:
            n = q.popleft()
            order.append(n)
            for m in self._out_edges.get(n, set()):
                indeg[m] -= 1
                if indeg[m] == 0:
                    q.append(m)
        if len(order) != len(self._nodes):
            raise GraphError("Graph contains a cycle or disconnected dependency structure")
        return order

    def validate_acyclic(self) -> None:
        self._topological_order()

    def entry_nodes(self) -> Set[str]:
        return {nid for nid in self._nodes if len(self._in_edges.get(nid, set())) == 0}

    def exit_nodes(self) -> Set[str]:
        return {nid for nid in self._nodes if len(self._out_edges.get(nid, set())) == 0}


class GraphExecutionEngine:
    def __init__(self, graph: Graph):
        self._graph = graph
        self._graph.validate_acyclic()

    @property
    def graph(self) -> Graph:
        return self._graph

    async def execute(self, ctx: ExecutionContext) -> Dict[str, Any]:
        order = self._graph._topological_order()
        for node_id in order:
            node = self._graph.nodes[node_id]
            span = ctx.telemetry.start_span("graph.node", {"node.id": node_id, "node.type": type(node).__name__})
            try:
                for mw in ctx.middleware:
                    await mw.before_node(ctx, node)
                ctx.snapshot()
                result = await node.run(ctx)
                ctx.node_results[node_id] = result
                for mw in ctx.middleware:
                    await mw.after_node(ctx, node, result)
                ctx.snapshot()
            except BaseException as e:
                ctx.node_errors[node_id] = e
                for mw in ctx.middleware:
                    try:
                        await mw.on_error(ctx, node, e)
                    except BaseException:
                        pass
                span.record_exception(e)
                span.end()
                raise
            span.end()
        return dict(ctx.node_results)


class PromptCache:
    def __init__(self, cache: Cache, namespace: str = "prompt_cache:"):
        self._cache = cache.with_namespace(prefix=namespace)

    @staticmethod
    def _hash_payload(payload: Mapping[str, Any]) -> str:
        s = JSONSerializer.dumps(payload)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    async def get(self, payload: Mapping[str, Any]) -> Optional[InferenceResponse]:
        key = self._hash_payload(payload)
        data = await self._cache.get(key)
        if data is None:
            return None
        if not isinstance(data, dict):
            return None
        try:
            return InferenceResponse(
                text=str(data.get("text", "")),
                tool_calls=tuple(ToolCall(**tc) for tc in data.get("tool_calls", []) or []),
                usage=TokenUsage(**(data.get("usage") or {})),
                provider=str(data.get("provider", "")),
                model=str(data.get("model", "")),
                cached=True,
                raw=data.get("raw"),
            )
        except Exception:
            return None

    async def set(self, payload: Mapping[str, Any], response: InferenceResponse, ttl_seconds: Optional[int] = None) -> None:
        key = self._hash_payload(payload)
        data = {
            "text": response.text,
            "tool_calls": [dataclasses.asdict(tc) for tc in response.tool_calls],
            "usage": dataclasses.asdict(response.usage),
            "provider": response.provider,
            "model": response.model,
            "raw": response.raw,
        }
        await self._cache.set(key, data, ttl_seconds=ttl_seconds)


class InferenceClient(abc.ABC):
    def __init__(
        self,
        *,
        provider: str,
        model: str,
        telemetry: Optional[Telemetry] = None,
        cache: Optional[PromptCache] = None,
        cache_ttl_seconds: Optional[int] = None,
    ):
        if not provider:
            raise ValidationError("provider must be non-empty")
        if not model:
            raise ValidationError("model must be non-empty")
        self._provider = provider
        self._model = model
        self._telemetry = telemetry or NoopTelemetry()
        self._prompt_cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

    @property
    def telemetry(self) -> Telemetry:
        return self._telemetry

    def _cache_payload(
        self,
        *,
        messages: Sequence[Mapping[str, Any]],
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        temperature: Optional[float] = None,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "provider": self._provider,
            "model": self._model,
            "messages": list(messages),
            "tools": list(tools) if tools is not None else None,
            "tool_choice": tool_choice,
            "temperature": temperature,
            "extra": dict(extra or {}),
        }

    async def infer(
        self,
        *,
        messages: Sequence[Mapping[str, Any]],
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        temperature: Optional[float] = None,
        extra: Optional[Mapping[str, Any]] = None,
        use_cache: bool = True,
    ) -> InferenceResponse:
        payload = self._cache_payload(
            messages=messages, tools=tools, tool_choice=tool_choice, temperature=temperature, extra=extra
        )
        if use_cache and self._prompt_cache is not None:
            cached = await self._prompt_cache.get(payload)
            if cached is not None:
                return cached

        span = self._telemetry.start_span(
            "inference.request",
            {
                "llm.provider": self._provider,
                "llm.model": self._model,
                "llm.streaming": False,
                "llm.tool_calling": tools is not None,
            },
        )
        try:
            resp = await self._infer_impl(
                messages=messages, tools=tools, tool_choice=tool_choice, temperature=temperature, extra=extra
            )
            span.set_attribute("llm.usage.prompt_tokens", resp.usage.prompt_tokens)
            span.set_attribute("llm.usage.completion_tokens", resp.usage.completion_tokens)
            span.set_attribute("llm.usage.total_tokens", resp.usage.total_tokens)
            if use_cache and self._prompt_cache is not None:
                await self._prompt_cache.set(payload, resp, ttl_seconds=self._cache_ttl_seconds)
            return resp
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()

    async def stream(
        self,
        *,
        messages: Sequence[Mapping[str, Any]],
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        temperature: Optional[float] = None,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> AsyncGenerator[InferenceChunk, None]:
        span = self._telemetry.start_span(
            "inference.request",
            {
                "llm.provider": self._provider,
                "llm.model": self._model,
                "llm.streaming": True,
                "llm.tool_calling": tools is not None,
            },
        )
        usage = TokenUsage()
        try:
            async for chunk in self._stream_impl(
                messages=messages, tools=tools, tool_choice=tool_choice, temperature=temperature, extra=extra
            ):
                if chunk.usage_delta.total_tokens:
                    usage = usage + chunk.usage_delta
                yield chunk
            span.set_attribute("llm.usage.prompt_tokens", usage.prompt_tokens)
            span.set_attribute("llm.usage.completion_tokens", usage.completion_tokens)
            span.set_attribute("llm.usage.total_tokens", usage.total_tokens)
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()

    @abc.abstractmethod
    async def _infer_impl(
        self,
        *,
        messages: Sequence[Mapping[str, Any]],
        tools: Optional[Sequence[Mapping[str, Any]]],
        tool_choice: Optional[Union[str, Mapping[str, Any]]],
        temperature: Optional[float],
        extra: Optional[Mapping[str, Any]],
    ) -> InferenceResponse:
        raise NotImplementedError

    @abc.abstractmethod
    async def _stream_impl(
        self,
        *,
        messages: Sequence[Mapping[str, Any]],
        tools: Optional[Sequence[Mapping[str, Any]]],
        tool_choice: Optional[Union[str, Mapping[str, Any]]],
        temperature: Optional[float],
        extra: Optional[Mapping[str, Any]],
    ) -> AsyncGenerator[InferenceChunk, None]:
        raise NotImplementedError


class EchoInferenceClient(InferenceClient):
    def __init__(
        self,
        *,
        provider: str = "echo",
        model: str = "echo-1",
        telemetry: Optional[Telemetry] = None,
        cache: Optional[PromptCache] = None,
        cache_ttl_seconds: Optional[int] = None,
    ):
        super().__init__(provider=provider, model=model, telemetry=telemetry, cache=cache, cache_ttl_seconds=cache_ttl_seconds)

    def _estimate_tokens(self, text: str) -> int:
        text = text.strip()
        if not text:
            return 0
        return max(1, len(text.split()))

    def _messages_to_text(self, messages: Sequence[Mapping[str, Any]]) -> str:
        parts: List[str] = []
        for m in messages:
            role = str(m.get("role", ""))
            content = m.get("content", "")
            if isinstance(content, list):
                content_str = JSONSerializer.dumps(content)
            else:
                content_str = "" if content is None else str(content)
            parts.append(f"{role}:{content_str}")
        return "\n".join(parts)

    async def _infer_impl(
        self,
        *,
        messages: Sequence[Mapping[str, Any]],
        tools: Optional[Sequence[Mapping[str, Any]]],
        tool_choice: Optional[Union[str, Mapping[str, Any]]],
        temperature: Optional[float],
        extra: Optional[Mapping[str, Any]],
    ) -> InferenceResponse:
        prompt = self._messages_to_text(messages)
        text = prompt
        usage = TokenUsage(prompt_tokens=self._estimate_tokens(prompt), completion_tokens=self._estimate_tokens(text))
        tool_calls: Tuple[ToolCall, ...] = ()
        if tools and tool_choice:
            if isinstance(tool_choice, str) and tool_choice != "none":
                tool_calls = (ToolCall(name=tool_choice, arguments={}),)
            elif isinstance(tool_choice, dict) and "name" in tool_choice:
                tool_calls = (ToolCall(name=str(tool_choice["name"]), arguments=dict(tool_choice.get("arguments") or {})),)
        return InferenceResponse(
            text=text,
            tool_calls=tool_calls,
            usage=usage,
            provider=self.provider,
            model=self.model,
            cached=False,
            raw={"echo": True},
        )

    async def _stream_impl(
        self,
        *,
        messages: Sequence[Mapping[str, Any]],
        tools: Optional[Sequence[Mapping[str, Any]]],
        tool_choice: Optional[Union[str, Mapping[str, Any]]],
        temperature: Optional[float],
        extra: Optional[Mapping[str, Any]],
    ) -> AsyncGenerator[InferenceChunk, None]:
        prompt = self._messages_to_text(messages)
        words = prompt.split()
        if not words:
            yield InferenceChunk(text="", usage_delta=TokenUsage(prompt_tokens=0, completion_tokens=0))
            return
        prompt_tokens = self._estimate_tokens(prompt)
        yielded_prompt = False
        for w in words:
            if not yielded_prompt:
                yielded_prompt = True
                yield InferenceChunk(text=w, usage_delta=TokenUsage(prompt_tokens=prompt_tokens, completion_tokens=1))
            else:
                yield InferenceChunk(text=" " + w, usage_delta=TokenUsage(prompt_tokens=0, completion_tokens=1))
            await asyncio.sleep(0)


class LLMDirectedGraphExecutor:
    def __init__(self, graph: Graph, inference_client: InferenceClient):
        self._graph = graph
        self._client = inference_client
        self._graph.validate_acyclic()

    @property
    def graph(self) -> Graph:
        return self._graph

    @property
    def client(self) -> InferenceClient:
        return self._client

    def _available_nodes(self, completed: Set[str], failed: Set[str]) -> List[str]:
        available: List[str] = []
        for nid in self._graph.nodes.keys():
            if nid in completed or nid in failed:
                continue
            preds = self._graph.predecessors(nid)
            if preds.issubset(completed):
                available.append(nid)
        return available

    async def execute(self, ctx: ExecutionContext, *, max_steps: Optional[int] = None) -> Dict[str, Any]:
        completed: Set[str] = set()
        failed: Set[str] = set()
        steps = 0

        while True:
            available = self._available_nodes(completed, failed)
            if not available:
                break
            if max_steps is not None and steps >= max_steps:
                raise GraphError("max_steps exceeded during LLM directed execution")

            prompt_state = {
                "completed": sorted(completed),
                "available": sorted(available),
                "results": {k: ctx.node_results.get(k) for k in sorted(completed)},
            }
            messages = [
                {
                    "role": "system",
                    "content": "Select the next node to execute from the available list. Respond with the node id only.",
                },
                {"role": "user", "content": JSONSerializer.dumps(prompt_state)},
            ]
            resp = await self._client.infer(messages=messages, use_cache=True)
            ctx.add_usage(resp.usage)
            choice = resp.text.strip().splitlines()[0].strip() if resp.text else ""
            if choice not in available:
                choice = available[0]

            node = self._graph.nodes[choice]
            span = ctx.telemetry.start_span("graph.node", {"node.id": choice, "node.type": type(node).__name__})
            try:
                for mw in ctx.middleware:
                    await mw.before_node(ctx, node)
                ctx.snapshot()
                result = await node.run(ctx)
                ctx.node_results[choice] = result
                completed.add(choice)
                for mw in ctx.middleware:
                    await mw.after_node(ctx, node, result)
                ctx.snapshot()
            except BaseException as e:
                ctx.node_errors[choice] = e
                failed.add(choice)
                for mw in ctx.middleware:
                    try:
                        await mw.on_error(ctx, node, e)
                    except BaseException:
                        pass
                span.record_exception(e)
                span.end()
                raise
            span.end()
            steps += 1

        return dict(ctx.node_results)