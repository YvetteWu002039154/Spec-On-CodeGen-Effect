from __future__ import annotations

import abc
import asyncio
import dataclasses
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
    Generic,
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
JSONPrimitive = Union[str, int, float, bool, None]
JSONValue = Union[JSONPrimitive, Dict[str, "JSONValue"], List["JSONValue"]]


class FrameworkError(Exception):
    pass


class ValidationError(FrameworkError):
    pass


class ExecutionError(FrameworkError):
    pass


class CacheError(FrameworkError):
    pass


class InferenceError(FrameworkError):
    pass


def _now_ms() -> int:
    return int(time.time() * 1000)


def _ensure_jsonable(value: Any) -> JSONValue:
    try:
        json.dumps(value)
        return value
    except Exception as e:
        raise ValidationError(f"Value is not JSON serializable: {e}") from e


class JSONSerializer:
    @staticmethod
    def dumps(value: Any) -> str:
        _ensure_jsonable(value)
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def loads(data: str) -> Any:
        return json.loads(data)


class TelemetrySpan(Protocol):
    def set_attribute(self, key: str, value: Any) -> None: ...
    def record_exception(self, exc: BaseException) -> None: ...
    def end(self) -> None: ...


class TelemetryTracer(Protocol):
    def start_span(self, name: str, attributes: Optional[Mapping[str, Any]] = None) -> TelemetrySpan: ...


class _NoopSpan:
    def __init__(self) -> None:
        self._ended = False

    def set_attribute(self, key: str, value: Any) -> None:
        return None

    def record_exception(self, exc: BaseException) -> None:
        return None

    def end(self) -> None:
        self._ended = True


class NoopTracer:
    def start_span(self, name: str, attributes: Optional[Mapping[str, Any]] = None) -> TelemetrySpan:
        return _NoopSpan()


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InferenceResult:
    text: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    provider: str = ""
    model: str = ""
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InferenceChunk:
    text_delta: str = ""
    tool_call_delta: Optional[ToolCall] = None
    usage_delta: TokenUsage = field(default_factory=TokenUsage)
    provider: str = ""
    model: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


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


class _InMemoryPubSub:
    def __init__(self) -> None:
        self._topics: Dict[str, Set[asyncio.Queue[str]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, payload: str) -> None:
        async with self._lock:
            queues = list(self._topics.get(topic, set()))
        for q in queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                await q.put(payload)

    async def subscribe(self, topic: str) -> AsyncGenerator[str, None]:
        q: asyncio.Queue[str] = asyncio.Queue()
        async with self._lock:
            self._topics[topic].add(q)
        try:
            while True:
                payload = await q.get()
                yield payload
        finally:
            async with self._lock:
                self._topics[topic].discard(q)
                if not self._topics[topic]:
                    self._topics.pop(topic, None)


class RedisCache(Cache):
    def __init__(
        self,
        prefix: str = "",
        suffix: str = "",
        serializer: Optional[JSONSerializer] = None,
        _store: Optional[Dict[str, Tuple[str, Optional[float]]]] = None,
        _pubsub: Optional[_InMemoryPubSub] = None,
    ) -> None:
        self._prefix = prefix or ""
        self._suffix = suffix or ""
        self._serializer = serializer or JSONSerializer()
        self._store = _store if _store is not None else {}
        self._pubsub = _pubsub if _pubsub is not None else _InMemoryPubSub()
        self._lock = asyncio.Lock()

    def _ns(self, key: str) -> str:
        if not isinstance(key, str) or not key:
            raise ValidationError("Cache key must be a non-empty string")
        return f"{self._prefix}{key}{self._suffix}"

    def _is_expired(self, expires_at: Optional[float]) -> bool:
        return expires_at is not None and time.time() >= expires_at

    async def get(self, key: str) -> Optional[Any]:
        k = self._ns(key)
        async with self._lock:
            item = self._store.get(k)
            if item is None:
                return None
            payload, expires_at = item
            if self._is_expired(expires_at):
                self._store.pop(k, None)
                return None
        try:
            return self._serializer.loads(payload)
        except Exception as e:
            raise CacheError(f"Failed to deserialize cache value for key={key}: {e}") from e

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValidationError("ttl_seconds must be positive when provided")
        k = self._ns(key)
        try:
            payload = self._serializer.dumps(value)
        except Exception as e:
            raise CacheError(f"Failed to serialize cache value for key={key}: {e}") from e
        expires_at = (time.time() + ttl_seconds) if ttl_seconds is not None else None
        async with self._lock:
            self._store[k] = (payload, expires_at)

    async def delete(self, key: str) -> None:
        k = self._ns(key)
        async with self._lock:
            self._store.pop(k, None)

    async def get_all(self, keys: Sequence[str]) -> Dict[str, Any]:
        if keys is None:
            raise ValidationError("keys must not be None")
        results: Dict[str, Any] = {}
        for key in keys:
            val = await self.get(key)
            if val is not None:
                results[key] = val
        return results

    async def clear(self) -> None:
        async with self._lock:
            if not self._prefix and not self._suffix:
                self._store.clear()
                return
            to_delete = [k for k in self._store.keys() if k.startswith(self._prefix) and k.endswith(self._suffix)]
            for k in to_delete:
                self._store.pop(k, None)

    def with_namespace(self, prefix: str = "", suffix: str = "") -> "Cache":
        return RedisCache(
            prefix=f"{self._prefix}{prefix}",
            suffix=f"{suffix}{self._suffix}",
            serializer=self._serializer,
            _store=self._store,
            _pubsub=self._pubsub,
        )

    def mailbox(self, name: str) -> "Mailbox":
        if not isinstance(name, str) or not name:
            raise ValidationError("Mailbox name must be a non-empty string")
        topic = self._ns(f"mailbox:{name}")
        return RedisMailbox(topic=topic, pubsub=self._pubsub, serializer=self._serializer)


class RedisMailbox(Mailbox):
    def __init__(self, topic: str, pubsub: _InMemoryPubSub, serializer: JSONSerializer) -> None:
        self._topic = topic
        self._pubsub = pubsub
        self._serializer = serializer

    async def publish(self, message: Any) -> None:
        try:
            payload = self._serializer.dumps(message)
        except Exception as e:
            raise CacheError(f"Failed to serialize mailbox message: {e}") from e
        await self._pubsub.publish(self._topic, payload)

    async def subscribe(self) -> AsyncGenerator[Any, None]:
        async for payload in self._pubsub.subscribe(self._topic):
            try:
                yield self._serializer.loads(payload)
            except Exception as e:
                raise CacheError(f"Failed to deserialize mailbox message: {e}") from e


class InferenceClient(abc.ABC):
    @abc.abstractmethod
    async def infer(
        self,
        prompt: str,
        *,
        model: str,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        cache: Optional[Cache] = None,
        cache_ttl_seconds: Optional[int] = None,
    ) -> InferenceResult:
        raise NotImplementedError

    @abc.abstractmethod
    async def stream(
        self,
        prompt: str,
        *,
        model: str,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        cache: Optional[Cache] = None,
        cache_ttl_seconds: Optional[int] = None,
    ) -> AsyncGenerator[InferenceChunk, None]:
        raise NotImplementedError


class _PromptCacheKey:
    @staticmethod
    def build(provider: str, model: str, prompt: str, tools: Optional[Sequence[Mapping[str, Any]]], tool_choice: Any) -> str:
        tools_norm = tools if tools is not None else []
        payload = {
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "tools": tools_norm,
            "tool_choice": tool_choice,
        }
        s = JSONSerializer.dumps(payload)
        return f"prompt_cache:{uuid.uuid5(uuid.NAMESPACE_URL, s)}"


class Middleware(abc.ABC):
    async def before_node(self, ctx: "ExecutionContext", node: "Node") -> None:
        return None

    async def after_node(self, ctx: "ExecutionContext", node: "Node", result: Any) -> None:
        return None

    async def on_error(self, ctx: "ExecutionContext", node: Optional["Node"], exc: BaseException) -> None:
        return None


@dataclass
class NodeExecutionRecord:
    node_id: str
    name: str
    started_at_ms: int
    ended_at_ms: int
    status: str
    error: Optional[str] = None


@dataclass
class StateSnapshot:
    snapshot_id: str
    created_at_ms: int
    state: Dict[str, Any]


class ExecutionContext:
    def __init__(
        self,
        *,
        initial_state: Optional[Mapping[str, Any]] = None,
        cache: Optional[Cache] = None,
        tracer: Optional[TelemetryTracer] = None,
        middleware: Optional[Sequence[Middleware]] = None,
    ) -> None:
        self._state: Dict[str, Any] = dict(initial_state or {})
        self._cache = cache
        self._tracer: TelemetryTracer = tracer or NoopTracer()
        self._middleware: List[Middleware] = list(middleware or [])
        self._history: List[NodeExecutionRecord] = []
        self._snapshots: List[StateSnapshot] = []

    @property
    def state(self) -> Dict[str, Any]:
        return self._state

    @property
    def cache(self) -> Optional[Cache]:
        return self._cache

    @property
    def tracer(self) -> TelemetryTracer:
        return self._tracer

    @property
    def middleware(self) -> Sequence[Middleware]:
        return tuple(self._middleware)

    @property
    def history(self) -> Sequence[NodeExecutionRecord]:
        return tuple(self._history)

    @property
    def snapshots(self) -> Sequence[StateSnapshot]:
        return tuple(self._snapshots)

    def snapshot(self) -> StateSnapshot:
        snap = StateSnapshot(snapshot_id=str(uuid.uuid4()), created_at_ms=_now_ms(), state=json.loads(JSONSerializer.dumps(self._state)))
        self._snapshots.append(snap)
        return snap

    def _record(self, rec: NodeExecutionRecord) -> None:
        self._history.append(rec)


class Node(abc.ABC):
    def __init__(self, node_id: str, name: Optional[str] = None) -> None:
        if not isinstance(node_id, str) or not node_id:
            raise ValidationError("node_id must be a non-empty string")
        self._id = node_id
        self._name = name or node_id

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @abc.abstractmethod
    async def run(self, ctx: ExecutionContext) -> Any:
        raise NotImplementedError


class FunctionNode(Node):
    def __init__(self, node_id: str, func: Callable[[ExecutionContext], Awaitable[Any]], name: Optional[str] = None) -> None:
        super().__init__(node_id=node_id, name=name)
        if not callable(func):
            raise ValidationError("func must be callable")
        self._func = func

    async def run(self, ctx: ExecutionContext) -> Any:
        return await self._func(ctx)


class InferenceNode(Node):
    def __init__(
        self,
        node_id: str,
        client: InferenceClient,
        prompt: Union[str, Callable[[ExecutionContext], str]],
        *,
        model: str,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        cache_ttl_seconds: Optional[int] = None,
        name: Optional[str] = None,
        output_state_key: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(node_id=node_id, name=name)
        self._client = client
        self._prompt = prompt
        self._model = model
        self._tools = list(tools) if tools is not None else None
        self._tool_choice = tool_choice
        self._cache_ttl_seconds = cache_ttl_seconds
        self._output_state_key = output_state_key
        self._metadata = dict(metadata or {})

        if not isinstance(model, str) or not model:
            raise ValidationError("model must be a non-empty string")

    def _render_prompt(self, ctx: ExecutionContext) -> str:
        if isinstance(self._prompt, str):
            return self._prompt
        if callable(self._prompt):
            p = self._prompt(ctx)
            if not isinstance(p, str):
                raise ValidationError("prompt callable must return a string")
            return p
        raise ValidationError("prompt must be a string or callable")

    async def run(self, ctx: ExecutionContext) -> Any:
        prompt = self._render_prompt(ctx)
        res = await self._client.infer(
            prompt,
            model=self._model,
            tools=self._tools,
            tool_choice=self._tool_choice,
            metadata=self._metadata,
            cache=ctx.cache,
            cache_ttl_seconds=self._cache_ttl_seconds,
        )
        if self._output_state_key:
            ctx.state[self._output_state_key] = dataclasses.asdict(res)
        return res


class EdgeCondition(Protocol):
    def __call__(self, ctx: ExecutionContext, last_result: Any) -> bool: ...


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    condition: Optional[EdgeCondition] = None


class Graph:
    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        self._out_edges: Dict[str, List[Edge]] = defaultdict(list)
        self._in_degree: Dict[str, int] = defaultdict(int)

    def add_node(self, node: Node) -> None:
        if node.id in self._nodes:
            raise ValidationError(f"Duplicate node id: {node.id}")
        self._nodes[node.id] = node
        self._in_degree.setdefault(node.id, 0)

    def add_edge(self, src: str, dst: str, condition: Optional[EdgeCondition] = None) -> None:
        if src not in self._nodes or dst not in self._nodes:
            raise ValidationError("Both src and dst must be added as nodes before adding an edge")
        self._out_edges[src].append(Edge(src=src, dst=dst, condition=condition))
        self._in_degree[dst] = self._in_degree.get(dst, 0) + 1

    @property
    def nodes(self) -> Mapping[str, Node]:
        return dict(self._nodes)

    def _topological_order(self) -> List[str]:
        indeg = dict(self._in_degree)
        q: Deque[str] = deque([nid for nid, d in indeg.items() if d == 0])
        order: List[str] = []
        while q:
            n = q.popleft()
            order.append(n)
            for e in self._out_edges.get(n, []):
                indeg[e.dst] -= 1
                if indeg[e.dst] == 0:
                    q.append(e.dst)
        if len(order) != len(self._nodes):
            raise ValidationError("Graph contains a cycle or disconnected in-degree accounting error")
        return order

    def validate(self) -> None:
        if not self._nodes:
            raise ValidationError("Graph must contain at least one node")
        self._topological_order()

    def entry_nodes(self) -> List[str]:
        return [nid for nid, d in self._in_degree.items() if d == 0]


class GraphExecutionEngine:
    def __init__(self, graph: Graph) -> None:
        self._graph = graph
        self._graph.validate()

    async def run(
        self,
        ctx: ExecutionContext,
        *,
        start_nodes: Optional[Sequence[str]] = None,
        snapshot_before_each_node: bool = False,
        snapshot_after_each_node: bool = False,
    ) -> Dict[str, Any]:
        if start_nodes is None:
            start = set(self._graph.entry_nodes())
        else:
            start = set(start_nodes)
            for nid in start:
                if nid not in self._graph.nodes:
                    raise ValidationError(f"Unknown start node: {nid}")

        order = self._graph._topological_order()
        allowed: Set[str] = set()
        if start:
            reachable = self._reachable_from(start)
            allowed = reachable
        else:
            allowed = set(order)

        results: Dict[str, Any] = {}
        for nid in order:
            if nid not in allowed:
                continue
            node = self._graph.nodes[nid]
            if snapshot_before_each_node:
                ctx.snapshot()

            started = _now_ms()
            span = ctx.tracer.start_span("graph.node", attributes={"node.id": node.id, "node.name": node.name})
            status = "ok"
            err_str: Optional[str] = None
            try:
                for mw in ctx.middleware:
                    await mw.before_node(ctx, node)

                # Determine if node should run based on incoming conditional edges.
                if self._should_run_node(ctx, nid, results, start):
                    result = await node.run(ctx)
                    results[nid] = result
                else:
                    result = None
                    results[nid] = None

                for mw in ctx.middleware:
                    await mw.after_node(ctx, node, result)

            except BaseException as e:
                status = "error"
                err_str = f"{type(e).__name__}: {e}"
                span.record_exception(e)
                for mw in ctx.middleware:
                    try:
                        await mw.on_error(ctx, node, e)
                    except BaseException:
                        pass
                raise ExecutionError(f"Node execution failed: {node.id}") from e
            finally:
                span.set_attribute("status", status)
                span.end()
                ended = _now_ms()
                ctx._record(
                    NodeExecutionRecord(
                        node_id=node.id,
                        name=node.name,
                        started_at_ms=started,
                        ended_at_ms=ended,
                        status=status,
                        error=err_str,
                    )
                )
                if snapshot_after_each_node:
                    ctx.snapshot()

        return results

    def _reachable_from(self, start: Set[str]) -> Set[str]:
        visited: Set[str] = set()
        stack: List[str] = list(start)
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            for e in self._graph._out_edges.get(n, []):
                stack.append(e.dst)
        return visited

    def _should_run_node(self, ctx: ExecutionContext, node_id: str, results: Mapping[str, Any], start: Set[str]) -> bool:
        if node_id in start:
            return True
        incoming: List[Edge] = []
        for src, edges in self._graph._out_edges.items():
            for e in edges:
                if e.dst == node_id:
                    incoming.append(e)

        if not incoming:
            return True

        # If any incoming edge condition passes, run. If edge has no condition, it is considered passing.
        for e in incoming:
            if e.src not in results:
                continue
            last = results.get(e.src)
            if e.condition is None:
                return True
            try:
                if bool(e.condition(ctx, last)):
                    return True
            except Exception as ex:
                raise ExecutionError(f"Edge condition failed for {e.src} -> {e.dst}: {ex}") from ex
        return False


class CachingInferenceClient(InferenceClient):
    def __init__(
        self,
        inner: InferenceClient,
        *,
        provider_name: Optional[str] = None,
        tracer: Optional[TelemetryTracer] = None,
        cache_namespace_prefix: str = "",
        cache_namespace_suffix: str = "",
    ) -> None:
        self._inner = inner
        self._provider_name = provider_name or getattr(inner, "provider", "") or inner.__class__.__name__
        self._tracer: TelemetryTracer = tracer or NoopTracer()
        self._ns_prefix = cache_namespace_prefix
        self._ns_suffix = cache_namespace_suffix

    async def infer(
        self,
        prompt: str,
        *,
        model: str,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        cache: Optional[Cache] = None,
        cache_ttl_seconds: Optional[int] = None,
    ) -> InferenceResult:
        if not isinstance(prompt, str):
            raise ValidationError("prompt must be a string")
        if not isinstance(model, str) or not model:
            raise ValidationError("model must be a non-empty string")

        span = self._tracer.start_span(
            "inference.infer",
            attributes={"provider": self._provider_name, "model": model, "cached": False},
        )
        try:
            effective_cache = None
            if cache is not None:
                effective_cache = cache.with_namespace(prefix=self._ns_prefix, suffix=self._ns_suffix)

            cache_key = None
            if effective_cache is not None:
                cache_key = _PromptCacheKey.build(self._provider_name, model, prompt, tools, tool_choice)
                cached_val = await effective_cache.get(cache_key)
                if cached_val is not None:
                    span.set_attribute("cached", True)
                    try:
                        return InferenceResult(**cached_val)
                    except Exception as e:
                        # If cached payload is malformed, ignore and fall through.
                        span.record_exception(e)

            res = await self._inner.infer(
                prompt,
                model=model,
                tools=tools,
                tool_choice=tool_choice,
                metadata=metadata,
                cache=cache,
                cache_ttl_seconds=cache_ttl_seconds,
            )

            if effective_cache is not None and cache_key is not None:
                await effective_cache.set(cache_key, dataclasses.asdict(res), ttl_seconds=cache_ttl_seconds)

            return res
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()

    async def stream(
        self,
        prompt: str,
        *,
        model: str,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        cache: Optional[Cache] = None,
        cache_ttl_seconds: Optional[int] = None,
    ) -> AsyncGenerator[InferenceChunk, None]:
        if not isinstance(prompt, str):
            raise ValidationError("prompt must be a string")
        if not isinstance(model, str) or not model:
            raise ValidationError("model must be a non-empty string")

        span = self._tracer.start_span(
            "inference.stream",
            attributes={"provider": self._provider_name, "model": model, "cached": False},
        )

        effective_cache = None
        if cache is not None:
            effective_cache = cache.with_namespace(prefix=self._ns_prefix, suffix=self._ns_suffix)

        cache_key = None
        if effective_cache is not None:
            cache_key = _PromptCacheKey.build(self._provider_name, model, prompt, tools, tool_choice)
            cached_val = await effective_cache.get(cache_key)
            if cached_val is not None:
                span.set_attribute("cached", True)
                try:
                    res = InferenceResult(**cached_val)
                    # Emit as a single chunk for cached streaming.
                    yield InferenceChunk(
                        text_delta=res.text,
                        tool_call_delta=None,
                        usage_delta=res.usage,
                        provider=res.provider,
                        model=res.model,
                        metadata={"cached": True, **(res.metadata or {})},
                    )
                    return
                except Exception as e:
                    span.record_exception(e)

        try:
            collected_text: List[str] = []
            collected_tool_calls: List[ToolCall] = []
            usage = TokenUsage()
            provider = ""
            model_out = model
            meta_out: Dict[str, Any] = {}

            async for chunk in self._inner.stream(
                prompt,
                model=model,
                tools=tools,
                tool_choice=tool_choice,
                metadata=metadata,
                cache=cache,
                cache_ttl_seconds=cache_ttl_seconds,
            ):
                if chunk.text_delta:
                    collected_text.append(chunk.text_delta)
                if chunk.tool_call_delta is not None:
                    collected_tool_calls.append(chunk.tool_call_delta)
                if chunk.usage_delta:
                    usage = TokenUsage(
                        prompt_tokens=usage.prompt_tokens + chunk.usage_delta.prompt_tokens,
                        completion_tokens=usage.completion_tokens + chunk.usage_delta.completion_tokens,
                    )
                provider = chunk.provider or provider
                model_out = chunk.model or model_out
                if chunk.metadata:
                    meta_out.update(dict(chunk.metadata))
                yield chunk

            if effective_cache is not None and cache_key is not None:
                res = InferenceResult(
                    text="".join(collected_text),
                    tool_calls=collected_tool_calls,
                    usage=usage,
                    provider=provider or self._provider_name,
                    model=model_out,
                    cached=False,
                    metadata=meta_out,
                )
                await effective_cache.set(cache_key, dataclasses.asdict(res), ttl_seconds=cache_ttl_seconds)
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()


class MockInferenceClient(InferenceClient):
    def __init__(self, provider: str = "mock") -> None:
        self.provider = provider

    async def infer(
        self,
        prompt: str,
        *,
        model: str,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        cache: Optional[Cache] = None,
        cache_ttl_seconds: Optional[int] = None,
    ) -> InferenceResult:
        if not isinstance(prompt, str):
            raise ValidationError("prompt must be a string")
        if not isinstance(model, str) or not model:
            raise ValidationError("model must be a non-empty string")

        # Minimal tool calling simulation: if tool_choice is a dict with {"name": ...}, return a tool call.
        tool_calls: List[ToolCall] = []
        if isinstance(tool_choice, Mapping) and "name" in tool_choice:
            tool_calls.append(ToolCall(name=str(tool_choice["name"]), arguments=dict(tool_choice.get("arguments", {}))))
        usage = TokenUsage(prompt_tokens=len(prompt.split()), completion_tokens=max(1, len(prompt.split()) // 2))
        return InferenceResult(
            text=f"[{self.provider}:{model}] {prompt}",
            tool_calls=tool_calls,
            usage=usage,
            provider=self.provider,
            model=model,
            cached=False,
            metadata=dict(metadata or {}),
        )

    async def stream(
        self,
        prompt: str,
        *,
        model: str,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        cache: Optional[Cache] = None,
        cache_ttl_seconds: Optional[int] = None,
    ) -> AsyncGenerator[InferenceChunk, None]:
        res = await self.infer(
            prompt,
            model=model,
            tools=tools,
            tool_choice=tool_choice,
            metadata=metadata,
            cache=cache,
            cache_ttl_seconds=cache_ttl_seconds,
        )
        text = res.text
        # Stream in small chunks
        step = max(1, min(16, max(1, len(text) // 8)))
        sent_prompt_usage = False
        for i in range(0, len(text), step):
            delta = text[i : i + step]
            usage_delta = TokenUsage(prompt_tokens=res.usage.prompt_tokens, completion_tokens=0) if not sent_prompt_usage else TokenUsage()
            sent_prompt_usage = True
            yield InferenceChunk(
                text_delta=delta,
                tool_call_delta=None,
                usage_delta=usage_delta,
                provider=res.provider,
                model=res.model,
                metadata=dict(res.metadata),
            )
            await asyncio.sleep(0)
        yield InferenceChunk(
            text_delta="",
            tool_call_delta=None,
            usage_delta=TokenUsage(prompt_tokens=0, completion_tokens=res.usage.completion_tokens),
            provider=res.provider,
            model=res.model,
            metadata=dict(res.metadata),
        )


__all__ = [
    "FrameworkError",
    "ValidationError",
    "ExecutionError",
    "CacheError",
    "InferenceError",
    "TokenUsage",
    "ToolCall",
    "InferenceResult",
    "InferenceChunk",
    "Cache",
    "Mailbox",
    "RedisCache",
    "RedisMailbox",
    "TelemetrySpan",
    "TelemetryTracer",
    "NoopTracer",
    "Middleware",
    "NodeExecutionRecord",
    "StateSnapshot",
    "ExecutionContext",
    "Node",
    "FunctionNode",
    "InferenceNode",
    "EdgeCondition",
    "Edge",
    "Graph",
    "GraphExecutionEngine",
    "InferenceClient",
    "CachingInferenceClient",
    "MockInferenceClient",
]