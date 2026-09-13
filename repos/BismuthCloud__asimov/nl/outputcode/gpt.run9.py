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


class ExecutionError(FrameworkError):
    pass


class CacheError(FrameworkError):
    pass


class InferenceError(FrameworkError):
    pass


def _json_dumps(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    except Exception as e:
        raise CacheError(f"JSON serialization failed: {e}") from e


def _json_loads(value: str) -> Any:
    try:
        return json.loads(value)
    except Exception as e:
        raise CacheError(f"JSON deserialization failed: {e}") from e


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass(frozen=True)
class InferenceChunk:
    text: str = ""
    tool_calls: Tuple[ToolCall, ...] = ()
    usage: Optional[TokenUsage] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    cached: bool = False


@dataclass(frozen=True)
class InferenceResult:
    text: str
    tool_calls: Tuple[ToolCall, ...] = ()
    usage: Optional[TokenUsage] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    cached: bool = False


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


class Cache(abc.ABC):
    @abc.abstractmethod
    async def get(self, key: str) -> Any:
        raise NotImplementedError

    @abc.abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, key: str) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def exists(self, key: str) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_all(self, prefix: str = "") -> Dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    async def clear(self, prefix: str = "") -> int:
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
    def __init__(self, bus: "_InMemoryPubSub", channel: str) -> None:
        self._bus = bus
        self._channel = channel

    async def publish(self, message: Any) -> None:
        await self._bus.publish(self._channel, message)

    async def subscribe(self) -> AsyncGenerator[Any, None]:
        queue = self._bus.subscribe(self._channel)
        try:
            while True:
                msg = await queue.get()
                yield msg
        finally:
            self._bus.unsubscribe(self._channel, queue)


class _InMemoryPubSub:
    def __init__(self) -> None:
        self._subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, channel: str, message: Any) -> None:
        async with self._lock:
            subs = list(self._subscribers.get(channel, set()))
        for q in subs:
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                await q.put(message)

    def subscribe(self, channel: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers[channel].add(q)
        return q

    def unsubscribe(self, channel: str, q: asyncio.Queue) -> None:
        subs = self._subscribers.get(channel)
        if not subs:
            return
        subs.discard(q)
        if not subs:
            self._subscribers.pop(channel, None)


class RedisCache(Cache):
    def __init__(self, prefix: str = "", suffix: str = "") -> None:
        self._prefix = prefix
        self._suffix = suffix
        self._store: Dict[str, Tuple[str, Optional[float]]] = {}
        self._lock = asyncio.Lock()
        self._pubsub = _InMemoryPubSub()

    def _ns(self, key: str) -> str:
        if key is None:
            raise ValidationError("key must not be None")
        return f"{self._prefix}{key}{self._suffix}"

    def _is_expired(self, expires_at: Optional[float]) -> bool:
        return expires_at is not None and time.time() >= expires_at

    async def get(self, key: str) -> Any:
        ns = self._ns(key)
        async with self._lock:
            item = self._store.get(ns)
            if item is None:
                return None
            raw, expires_at = item
            if self._is_expired(expires_at):
                self._store.pop(ns, None)
                return None
        return _json_loads(raw)

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValidationError("ttl_seconds must be positive when provided")
        ns = self._ns(key)
        raw = _json_dumps(value)
        expires_at = (time.time() + ttl_seconds) if ttl_seconds is not None else None
        async with self._lock:
            self._store[ns] = (raw, expires_at)

    async def delete(self, key: str) -> None:
        ns = self._ns(key)
        async with self._lock:
            self._store.pop(ns, None)

    async def exists(self, key: str) -> bool:
        ns = self._ns(key)
        async with self._lock:
            item = self._store.get(ns)
            if item is None:
                return False
            _, expires_at = item
            if self._is_expired(expires_at):
                self._store.pop(ns, None)
                return False
            return True

    async def get_all(self, prefix: str = "") -> Dict[str, Any]:
        ns_prefix = self._ns(prefix)
        now = time.time()
        out: Dict[str, Any] = {}
        async with self._lock:
            keys = list(self._store.keys())
            for k in keys:
                if not k.startswith(ns_prefix):
                    continue
                raw, expires_at = self._store.get(k, ("", None))
                if expires_at is not None and now >= expires_at:
                    self._store.pop(k, None)
                    continue
                out[k] = _json_loads(raw)
        return out

    async def clear(self, prefix: str = "") -> int:
        ns_prefix = self._ns(prefix)
        removed = 0
        async with self._lock:
            keys = [k for k in self._store.keys() if k.startswith(ns_prefix)]
            for k in keys:
                self._store.pop(k, None)
                removed += 1
        return removed

    def mailbox(self, name: str) -> Mailbox:
        if not name:
            raise ValidationError("mailbox name must be non-empty")
        channel = self._ns(f"mailbox:{name}")
        return _InMemoryMailbox(self._pubsub, channel)


@dataclass(frozen=True)
class Message:
    role: str
    content: str


@dataclass(frozen=True)
class InferenceRequest:
    messages: Tuple[Message, ...]
    model: str
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    tools: Tuple[Dict[str, Any], ...] = ()
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def cache_key(self, provider: str) -> str:
        payload = {
            "provider": provider,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [dataclasses.asdict(m) for m in self.messages],
            "tools": list(self.tools),
            "tool_choice": self.tool_choice,
            "metadata": self.metadata,
        }
        return _json_dumps(payload)


class InferenceClient(abc.ABC):
    @abc.abstractmethod
    async def infer(self, request: InferenceRequest) -> InferenceResult:
        raise NotImplementedError

    @abc.abstractmethod
    async def stream(self, request: InferenceRequest) -> AsyncGenerator[InferenceChunk, None]:
        raise NotImplementedError


class CachedInferenceClient(InferenceClient):
    def __init__(
        self,
        inner: InferenceClient,
        cache: Cache,
        cache_prefix: str = "prompt_cache:",
        ttl_seconds: Optional[int] = None,
    ) -> None:
        self._inner = inner
        self._cache = cache
        self._cache_prefix = cache_prefix
        self._ttl_seconds = ttl_seconds

    async def infer(self, request: InferenceRequest) -> InferenceResult:
        provider = getattr(self._inner, "provider", self._inner.__class__.__name__)
        key = self._cache_prefix + request.cache_key(provider)
        cached = await self._cache.get(key)
        if cached is not None:
            return InferenceResult(
                text=str(cached.get("text", "")),
                tool_calls=tuple(ToolCall(**tc) for tc in cached.get("tool_calls", [])),
                usage=TokenUsage(**cached["usage"]) if cached.get("usage") else None,
                model=cached.get("model"),
                provider=cached.get("provider"),
                cached=True,
            )

        result = await self._inner.infer(request)
        to_store = {
            "text": result.text,
            "tool_calls": [dataclasses.asdict(tc) for tc in result.tool_calls],
            "usage": dataclasses.asdict(result.usage) if result.usage else None,
            "model": result.model,
            "provider": result.provider,
        }
        await self._cache.set(key, to_store, ttl_seconds=self._ttl_seconds)
        return result

    async def stream(self, request: InferenceRequest) -> AsyncGenerator[InferenceChunk, None]:
        provider = getattr(self._inner, "provider", self._inner.__class__.__name__)
        key = self._cache_prefix + request.cache_key(provider)
        cached = await self._cache.get(key)
        if cached is not None:
            yield InferenceChunk(
                text=str(cached.get("text", "")),
                tool_calls=tuple(ToolCall(**tc) for tc in cached.get("tool_calls", [])),
                usage=TokenUsage(**cached["usage"]) if cached.get("usage") else None,
                model=cached.get("model"),
                provider=cached.get("provider"),
                cached=True,
            )
            return

        chunks: List[InferenceChunk] = []
        async for ch in self._inner.stream(request):
            chunks.append(ch)
            yield ch

        full_text = "".join(c.text for c in chunks)
        tool_calls: List[ToolCall] = []
        usage: Optional[TokenUsage] = None
        model: Optional[str] = None
        provider_out: Optional[str] = None
        for c in chunks:
            if c.tool_calls:
                tool_calls.extend(list(c.tool_calls))
            if c.usage is not None:
                usage = c.usage
            if c.model is not None:
                model = c.model
            if c.provider is not None:
                provider_out = c.provider

        to_store = {
            "text": full_text,
            "tool_calls": [dataclasses.asdict(tc) for tc in tool_calls],
            "usage": dataclasses.asdict(usage) if usage else None,
            "model": model,
            "provider": provider_out or provider,
        }
        await self._cache.set(key, to_store, ttl_seconds=self._ttl_seconds)


class MockInferenceClient(InferenceClient):
    def __init__(self, provider: str = "mock") -> None:
        self.provider = provider

    async def infer(self, request: InferenceRequest) -> InferenceResult:
        text = request.messages[-1].content if request.messages else ""
        usage = TokenUsage(prompt_tokens=len(text.split()), completion_tokens=0, total_tokens=len(text.split()))
        return InferenceResult(text=text, tool_calls=(), usage=usage, model=request.model, provider=self.provider, cached=False)

    async def stream(self, request: InferenceRequest) -> AsyncGenerator[InferenceChunk, None]:
        text = request.messages[-1].content if request.messages else ""
        for part in text.split(" "):
            await asyncio.sleep(0)
            yield InferenceChunk(text=(part + " "), tool_calls=(), usage=None, model=request.model, provider=self.provider, cached=False)
        usage = TokenUsage(prompt_tokens=len(text.split()), completion_tokens=0, total_tokens=len(text.split()))
        yield InferenceChunk(text="", tool_calls=(), usage=usage, model=request.model, provider=self.provider, cached=False)


@dataclass
class StateSnapshot:
    snapshot_id: str
    timestamp: float
    state: Dict[str, Any]


class SnapshotStore:
    def __init__(self) -> None:
        self._snapshots: List[StateSnapshot] = []

    def add(self, state: Dict[str, Any]) -> StateSnapshot:
        snap = StateSnapshot(snapshot_id=str(uuid.uuid4()), timestamp=time.time(), state=json.loads(_json_dumps(state)))
        self._snapshots.append(snap)
        return snap

    def list(self) -> Tuple[StateSnapshot, ...]:
        return tuple(self._snapshots)

    def latest(self) -> Optional[StateSnapshot]:
        return self._snapshots[-1] if self._snapshots else None


class Middleware(abc.ABC):
    async def before_node(self, ctx: "ExecutionContext", node: "Node") -> None:
        return None

    async def after_node(self, ctx: "ExecutionContext", node: "Node", result: Any) -> None:
        return None

    async def on_error(self, ctx: "ExecutionContext", node: Optional["Node"], error: BaseException) -> None:
        return None


class TelemetryMiddleware(Middleware):
    def __init__(self, tracer: Optional[TelemetryTracer] = None) -> None:
        self._tracer = tracer or NoopTracer()
        self._spans: Dict[str, TelemetrySpan] = {}

    async def before_node(self, ctx: "ExecutionContext", node: "Node") -> None:
        span = self._tracer.start_span(
            "graph.node",
            attributes={
                "node.id": node.node_id,
                "node.name": node.name,
                "graph.id": ctx.graph.graph_id,
            },
        )
        self._spans[node.node_id] = span

    async def after_node(self, ctx: "ExecutionContext", node: "Node", result: Any) -> None:
        span = self._spans.pop(node.node_id, None)
        if span is None:
            return
        try:
            span.set_attribute("node.status", "ok")
        finally:
            span.end()

    async def on_error(self, ctx: "ExecutionContext", node: Optional["Node"], error: BaseException) -> None:
        if node is None:
            return
        span = self._spans.pop(node.node_id, None)
        if span is None:
            return
        try:
            span.set_attribute("node.status", "error")
            span.record_exception(error)
        finally:
            span.end()


@dataclass(frozen=True)
class NodeResult:
    node_id: str
    output: Any
    started_at: float
    ended_at: float


class Node(abc.ABC):
    def __init__(self, node_id: str, name: Optional[str] = None) -> None:
        if not node_id:
            raise ValidationError("node_id must be non-empty")
        self._node_id = node_id
        self._name = name or node_id

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def name(self) -> str:
        return self._name

    @abc.abstractmethod
    async def run(self, ctx: "ExecutionContext") -> Any:
        raise NotImplementedError


class FunctionNode(Node):
    def __init__(self, node_id: str, func: Callable[["ExecutionContext"], Awaitable[Any]], name: Optional[str] = None) -> None:
        super().__init__(node_id=node_id, name=name)
        self._func = func

    async def run(self, ctx: "ExecutionContext") -> Any:
        return await self._func(ctx)


class LLMNode(Node):
    def __init__(
        self,
        node_id: str,
        client: InferenceClient,
        request_builder: Callable[["ExecutionContext"], InferenceRequest],
        name: Optional[str] = None,
        stream: bool = False,
        output_key: Optional[str] = None,
    ) -> None:
        super().__init__(node_id=node_id, name=name)
        self._client = client
        self._request_builder = request_builder
        self._stream = stream
        self._output_key = output_key

    async def run(self, ctx: "ExecutionContext") -> Any:
        req = self._request_builder(ctx)
        if not isinstance(req, InferenceRequest):
            raise ValidationError("request_builder must return an InferenceRequest")
        if self._stream:
            text_parts: List[str] = []
            tool_calls: List[ToolCall] = []
            usage: Optional[TokenUsage] = None
            model: Optional[str] = None
            provider: Optional[str] = None
            cached = False
            async for ch in self._client.stream(req):
                cached = cached or ch.cached
                if ch.text:
                    text_parts.append(ch.text)
                if ch.tool_calls:
                    tool_calls.extend(list(ch.tool_calls))
                if ch.usage is not None:
                    usage = ch.usage
                if ch.model is not None:
                    model = ch.model
                if ch.provider is not None:
                    provider = ch.provider
            result = InferenceResult(
                text="".join(text_parts),
                tool_calls=tuple(tool_calls),
                usage=usage,
                model=model or req.model,
                provider=provider,
                cached=cached,
            )
        else:
            result = await self._client.infer(req)

        if self._output_key:
            ctx.state[self._output_key] = dataclasses.asdict(result)
        return result


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str


class Graph:
    def __init__(self, graph_id: Optional[str] = None) -> None:
        self._graph_id = graph_id or str(uuid.uuid4())
        self._nodes: Dict[str, Node] = {}
        self._out_edges: Dict[str, Set[str]] = defaultdict(set)
        self._in_edges: Dict[str, Set[str]] = defaultdict(set)

    @property
    def graph_id(self) -> str:
        return self._graph_id

    def add_node(self, node: Node) -> None:
        if node.node_id in self._nodes:
            raise ValidationError(f"Duplicate node_id: {node.node_id}")
        self._nodes[node.node_id] = node

    def add_edge(self, src: str, dst: str) -> None:
        if src not in self._nodes:
            raise ValidationError(f"Unknown src node: {src}")
        if dst not in self._nodes:
            raise ValidationError(f"Unknown dst node: {dst}")
        if src == dst:
            raise ValidationError("Self edges are not allowed")
        self._out_edges[src].add(dst)
        self._in_edges[dst].add(src)

    def node(self, node_id: str) -> Node:
        try:
            return self._nodes[node_id]
        except KeyError as e:
            raise ValidationError(f"Unknown node_id: {node_id}") from e

    def nodes(self) -> Tuple[Node, ...]:
        return tuple(self._nodes.values())

    def edges(self) -> Tuple[Edge, ...]:
        out: List[Edge] = []
        for s, ds in self._out_edges.items():
            for d in ds:
                out.append(Edge(s, d))
        return tuple(out)

    def predecessors(self, node_id: str) -> Set[str]:
        return set(self._in_edges.get(node_id, set()))

    def successors(self, node_id: str) -> Set[str]:
        return set(self._out_edges.get(node_id, set()))

    def validate_acyclic(self) -> None:
        indeg: Dict[str, int] = {nid: len(self._in_edges.get(nid, set())) for nid in self._nodes}
        q: Deque[str] = deque([nid for nid, d in indeg.items() if d == 0])
        visited = 0
        while q:
            n = q.popleft()
            visited += 1
            for s in self._out_edges.get(n, set()):
                indeg[s] -= 1
                if indeg[s] == 0:
                    q.append(s)
        if visited != len(self._nodes):
            raise ValidationError("Graph contains a cycle")

    def topological_order(self) -> Tuple[str, ...]:
        self.validate_acyclic()
        indeg: Dict[str, int] = {nid: len(self._in_edges.get(nid, set())) for nid in self._nodes}
        q: Deque[str] = deque([nid for nid, d in indeg.items() if d == 0])
        order: List[str] = []
        while q:
            n = q.popleft()
            order.append(n)
            for s in sorted(self._out_edges.get(n, set())):
                indeg[s] -= 1
                if indeg[s] == 0:
                    q.append(s)
        return tuple(order)


class ExecutionContext:
    def __init__(
        self,
        graph: Graph,
        state: Optional[Dict[str, Any]] = None,
        cache: Optional[Cache] = None,
        tracer: Optional[TelemetryTracer] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        snapshotting: bool = True,
    ) -> None:
        self.graph = graph
        self.state: Dict[str, Any] = dict(state or {})
        self.cache = cache
        self.tracer = tracer or NoopTracer()
        self.middleware: Tuple[Middleware, ...] = tuple(middleware or ())
        self.snapshots = SnapshotStore()
        self.snapshotting = snapshotting
        self.results: Dict[str, NodeResult] = {}

    def snapshot(self) -> Optional[StateSnapshot]:
        if not self.snapshotting:
            return None
        return self.snapshots.add(self.state)


class GraphExecutor:
    def __init__(self, graph: Graph) -> None:
        self._graph = graph

    @property
    def graph(self) -> Graph:
        return self._graph

    async def execute(
        self,
        state: Optional[Dict[str, Any]] = None,
        cache: Optional[Cache] = None,
        tracer: Optional[TelemetryTracer] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        snapshotting: bool = True,
    ) -> ExecutionContext:
        ctx = ExecutionContext(
            graph=self._graph,
            state=state,
            cache=cache,
            tracer=tracer,
            middleware=middleware,
            snapshotting=snapshotting,
        )
        order = self._graph.topological_order()
        ctx.snapshot()

        for node_id in order:
            node = self._graph.node(node_id)
            started = time.time()
            try:
                for mw in ctx.middleware:
                    await mw.before_node(ctx, node)

                output = await node.run(ctx)

                ended = time.time()
                ctx.results[node_id] = NodeResult(node_id=node_id, output=output, started_at=started, ended_at=ended)
                ctx.snapshot()

                for mw in reversed(ctx.middleware):
                    await mw.after_node(ctx, node, output)
            except BaseException as e:
                for mw in reversed(ctx.middleware):
                    try:
                        await mw.on_error(ctx, node, e)
                    except Exception:
                        pass
                raise ExecutionError(f"Node execution failed: {node_id}") from e

        return ctx


class LLMDirectedGraphExecutor(GraphExecutor):
    def __init__(
        self,
        graph: Graph,
        director_client: InferenceClient,
        director_request_builder: Callable[[ExecutionContext, Tuple[str, ...], Tuple[str, ...]], InferenceRequest],
        decision_parser: Callable[[InferenceResult], Sequence[str]],
        max_steps: Optional[int] = None,
    ) -> None:
        super().__init__(graph)
        self._director_client = director_client
        self._director_request_builder = director_request_builder
        self._decision_parser = decision_parser
        self._max_steps = max_steps

    async def execute(
        self,
        state: Optional[Dict[str, Any]] = None,
        cache: Optional[Cache] = None,
        tracer: Optional[TelemetryTracer] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        snapshotting: bool = True,
    ) -> ExecutionContext:
        ctx = ExecutionContext(
            graph=self.graph,
            state=state,
            cache=cache,
            tracer=tracer,
            middleware=middleware,
            snapshotting=snapshotting,
        )
        self.graph.validate_acyclic()
        ctx.snapshot()

        completed: Set[str] = set()
        available: Set[str] = {nid for nid in (n.node_id for n in self.graph.nodes()) if not self.graph.predecessors(nid)}
        steps = 0

        while available:
            if self._max_steps is not None and steps >= self._max_steps:
                raise ExecutionError("Max steps exceeded in LLM-directed execution")
            steps += 1

            remaining = tuple(sorted(available))
            done = tuple(sorted(completed))
            req = self._director_request_builder(ctx, remaining, done)
            if not isinstance(req, InferenceRequest):
                raise ValidationError("director_request_builder must return an InferenceRequest")
            decision = await self._director_client.infer(req)
            chosen = list(self._decision_parser(decision))
            if not chosen:
                raise ExecutionError("Director did not choose any node to execute")
            for node_id in chosen:
                if node_id not in available:
                    raise ExecutionError(f"Director chose unavailable node: {node_id}")

                node = self.graph.node(node_id)
                started = time.time()
                try:
                    for mw in ctx.middleware:
                        await mw.before_node(ctx, node)

                    output = await node.run(ctx)

                    ended = time.time()
                    ctx.results[node_id] = NodeResult(node_id=node_id, output=output, started_at=started, ended_at=ended)
                    completed.add(node_id)
                    available.remove(node_id)
                    ctx.snapshot()

                    for mw in reversed(ctx.middleware):
                        await mw.after_node(ctx, node, output)
                except BaseException as e:
                    for mw in reversed(ctx.middleware):
                        try:
                            await mw.on_error(ctx, node, e)
                        except Exception:
                            pass
                    raise ExecutionError(f"Node execution failed: {node_id}") from e

                for succ in self.graph.successors(node_id):
                    if succ in completed:
                        continue
                    preds = self.graph.predecessors(succ)
                    if preds.issubset(completed):
                        available.add(succ)

        if len(completed) != len(self.graph.nodes()):
            missing = sorted({n.node_id for n in self.graph.nodes()} - completed)
            raise ExecutionError(f"Execution incomplete; missing nodes: {missing}")

        return ctx