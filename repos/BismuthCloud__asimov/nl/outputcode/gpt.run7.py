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


class TelemetryError(FrameworkError):
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
class InferenceRequest:
    model: str
    messages: List[Dict[str, Any]]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    stream: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InferenceDelta:
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    usage: Optional[TokenUsage] = None
    raw: Any = None


@dataclass(frozen=True)
class InferenceResponse:
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    raw: Any = None


class TelemetrySpan(Protocol):
    def set_attribute(self, key: str, value: Any) -> None: ...
    def record_exception(self, exc: BaseException) -> None: ...
    def end(self) -> None: ...


class TelemetryTracer(Protocol):
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> TelemetrySpan: ...


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
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> TelemetrySpan:
        return _NoopSpan()


class Middleware(Protocol):
    async def before_node(self, ctx: "ExecutionContext", node: "Node") -> None: ...
    async def after_node(self, ctx: "ExecutionContext", node: "Node", result: Any) -> None: ...
    async def on_error(self, ctx: "ExecutionContext", node: "Node", error: BaseException) -> None: ...


class BaseMiddleware:
    async def before_node(self, ctx: "ExecutionContext", node: "Node") -> None:
        return None

    async def after_node(self, ctx: "ExecutionContext", node: "Node", result: Any) -> None:
        return None

    async def on_error(self, ctx: "ExecutionContext", node: "Node", error: BaseException) -> None:
        return None


@dataclass(frozen=True)
class StateSnapshot:
    snapshot_id: str
    timestamp: float
    state: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


class SnapshotStore:
    def __init__(self) -> None:
        self._snapshots: List[StateSnapshot] = []

    def add(self, snapshot: StateSnapshot) -> None:
        self._snapshots.append(snapshot)

    def list(self) -> List[StateSnapshot]:
        return list(self._snapshots)

    def latest(self) -> Optional[StateSnapshot]:
        return self._snapshots[-1] if self._snapshots else None

    def get(self, snapshot_id: str) -> Optional[StateSnapshot]:
        for s in self._snapshots:
            if s.snapshot_id == snapshot_id:
                return s
        return None


class ExecutionContext:
    def __init__(
        self,
        initial_state: Optional[Dict[str, Any]] = None,
        *,
        tracer: Optional[TelemetryTracer] = None,
        cache: Optional["AbstractCache"] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        enable_snapshots: bool = True,
    ) -> None:
        self._state: Dict[str, Any] = dict(initial_state or {})
        self._tracer: TelemetryTracer = tracer or NoopTracer()
        self._cache = cache
        self._middleware: List[Middleware] = list(middleware or [])
        self._snapshots_enabled = enable_snapshots
        self._snapshots = SnapshotStore()
        self._node_results: Dict[str, Any] = {}
        self._node_errors: Dict[str, BaseException] = {}
        self._token_usage: TokenUsage = TokenUsage()

    @property
    def state(self) -> Dict[str, Any]:
        return self._state

    @property
    def tracer(self) -> TelemetryTracer:
        return self._tracer

    @property
    def cache(self) -> Optional["AbstractCache"]:
        return self._cache

    @property
    def middleware(self) -> Sequence[Middleware]:
        return tuple(self._middleware)

    @property
    def snapshots(self) -> SnapshotStore:
        return self._snapshots

    @property
    def node_results(self) -> Mapping[str, Any]:
        return dict(self._node_results)

    @property
    def node_errors(self) -> Mapping[str, BaseException]:
        return dict(self._node_errors)

    @property
    def token_usage(self) -> TokenUsage:
        return self._token_usage

    def add_token_usage(self, usage: TokenUsage) -> None:
        self._token_usage = self._token_usage + usage

    def set_result(self, node_id: str, result: Any) -> None:
        self._node_results[node_id] = result

    def set_error(self, node_id: str, error: BaseException) -> None:
        self._node_errors[node_id] = error

    def snapshot(self, *, metadata: Optional[Dict[str, Any]] = None) -> Optional[StateSnapshot]:
        if not self._snapshots_enabled:
            return None
        snap = StateSnapshot(
            snapshot_id=str(uuid.uuid4()),
            timestamp=time.time(),
            state=json.loads(json.dumps(self._state, default=str)),
            metadata=dict(metadata or {}),
        )
        self._snapshots.add(snap)
        return snap


class Node(abc.ABC):
    def __init__(self, node_id: str, *, name: Optional[str] = None) -> None:
        if not node_id or not isinstance(node_id, str):
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
    def __init__(
        self,
        node_id: str,
        func: Callable[[ExecutionContext], Union[Any, Awaitable[Any]]],
        *,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(node_id, name=name)
        if not callable(func):
            raise ValidationError("func must be callable")
        self._func = func

    async def run(self, ctx: ExecutionContext) -> Any:
        res = self._func(ctx)
        if asyncio.iscoroutine(res):
            return await res
        return res


class InferenceClient(abc.ABC):
    def __init__(self, *, tracer: Optional[TelemetryTracer] = None, cache: Optional["AbstractCache"] = None) -> None:
        self._tracer: TelemetryTracer = tracer or NoopTracer()
        self._cache = cache

    @property
    def tracer(self) -> TelemetryTracer:
        return self._tracer

    @property
    def cache(self) -> Optional["AbstractCache"]:
        return self._cache

    @abc.abstractmethod
    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        raise NotImplementedError

    @abc.abstractmethod
    async def stream(self, request: InferenceRequest) -> AsyncGenerator[InferenceDelta, None]:
        raise NotImplementedError


class PromptCacheKey:
    @staticmethod
    def build(request: InferenceRequest) -> str:
        payload = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "tools": request.tools,
            "tool_choice": request.tool_choice,
            "metadata": request.metadata,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return f"prompt:{_stable_hash(raw)}"


def _stable_hash(s: str) -> str:
    import hashlib

    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class CachedInferenceClient(InferenceClient):
    def __init__(
        self,
        inner: InferenceClient,
        *,
        cache: "AbstractCache",
        ttl_seconds: Optional[int] = None,
        tracer: Optional[TelemetryTracer] = None,
        namespace_prefix: str = "llm",
    ) -> None:
        super().__init__(tracer=tracer or inner.tracer, cache=cache)
        self._inner = inner
        self._ttl = ttl_seconds
        self._prefix = namespace_prefix

    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        if request.stream:
            raise ValidationError("infer() does not accept stream=True; use stream()")
        key = f"{self._prefix}:{PromptCacheKey.build(request)}"
        span = self.tracer.start_span("inference.cached.infer", {"cache.key": key, "model": request.model})
        try:
            cached = await self.cache.get(key)
            if cached is not None:
                span.set_attribute("cache.hit", True)
                return _deserialize_inference_response(cached)
            span.set_attribute("cache.hit", False)
            resp = await self._inner.infer(request)
            await self.cache.set(key, _serialize_inference_response(resp), ttl_seconds=self._ttl)
            return resp
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()

    async def stream(self, request: InferenceRequest) -> AsyncGenerator[InferenceDelta, None]:
        if not request.stream:
            request = dataclasses.replace(request, stream=True)
        span = self.tracer.start_span("inference.cached.stream", {"model": request.model})
        try:
            async for d in self._inner.stream(request):
                yield d
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()


def _serialize_inference_response(resp: InferenceResponse) -> Dict[str, Any]:
    return {
        "content": resp.content,
        "tool_calls": [{"name": tc.name, "arguments": tc.arguments, "call_id": tc.call_id} for tc in resp.tool_calls],
        "usage": {"prompt_tokens": resp.usage.prompt_tokens, "completion_tokens": resp.usage.completion_tokens},
        "raw": resp.raw,
    }


def _deserialize_inference_response(obj: Any) -> InferenceResponse:
    if not isinstance(obj, dict):
        raise CacheError("Invalid cached inference response")
    tool_calls = []
    for tc in obj.get("tool_calls", []) or []:
        tool_calls.append(ToolCall(name=tc["name"], arguments=dict(tc.get("arguments") or {}), call_id=tc["call_id"]))
    usage_obj = obj.get("usage") or {}
    usage = TokenUsage(
        prompt_tokens=int(usage_obj.get("prompt_tokens", 0)),
        completion_tokens=int(usage_obj.get("completion_tokens", 0)),
    )
    return InferenceResponse(content=str(obj.get("content", "")), tool_calls=tool_calls, usage=usage, raw=obj.get("raw"))


class LLMNode(Node):
    def __init__(
        self,
        node_id: str,
        client: InferenceClient,
        request_builder: Callable[[ExecutionContext], Union[InferenceRequest, Awaitable[InferenceRequest]]],
        *,
        name: Optional[str] = None,
        state_key: Optional[str] = None,
        record_usage: bool = True,
    ) -> None:
        super().__init__(node_id, name=name)
        self._client = client
        self._request_builder = request_builder
        self._state_key = state_key
        self._record_usage = record_usage

    async def run(self, ctx: ExecutionContext) -> Any:
        req = self._request_builder(ctx)
        if asyncio.iscoroutine(req):
            req = await req
        if not isinstance(req, InferenceRequest):
            raise ValidationError("request_builder must return InferenceRequest")
        span = ctx.tracer.start_span("node.llm.run", {"node.id": self.id, "model": req.model})
        try:
            if req.stream:
                content_parts: List[str] = []
                tool_calls: List[ToolCall] = []
                usage = TokenUsage()
                async for delta in self._client.stream(req):
                    if delta.content:
                        content_parts.append(delta.content)
                    if delta.tool_calls:
                        tool_calls.extend(delta.tool_calls)
                    if delta.usage:
                        usage = usage + delta.usage
                resp = InferenceResponse(content="".join(content_parts), tool_calls=tool_calls, usage=usage, raw=None)
            else:
                resp = await self._client.infer(req)
            if self._record_usage:
                ctx.add_token_usage(resp.usage)
            if self._state_key:
                ctx.state[self._state_key] = _serialize_inference_response(resp)
            return resp
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()


class Graph:
    def __init__(self, *, graph_id: Optional[str] = None, name: Optional[str] = None) -> None:
        self._id = graph_id or str(uuid.uuid4())
        self._name = name or self._id
        self._nodes: Dict[str, Node] = {}
        self._deps: Dict[str, Set[str]] = defaultdict(set)
        self._rev: Dict[str, Set[str]] = defaultdict(set)

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    def add_node(self, node: Node) -> None:
        if node.id in self._nodes:
            raise ValidationError(f"Duplicate node id: {node.id}")
        self._nodes[node.id] = node
        self._deps.setdefault(node.id, set())
        self._rev.setdefault(node.id, set())

    def add_edge(self, from_node_id: str, to_node_id: str) -> None:
        if from_node_id not in self._nodes or to_node_id not in self._nodes:
            raise ValidationError("Both nodes must be added before creating an edge")
        if from_node_id == to_node_id:
            raise ValidationError("Self edges are not allowed")
        self._deps[to_node_id].add(from_node_id)
        self._rev[from_node_id].add(to_node_id)

    def nodes(self) -> List[Node]:
        return list(self._nodes.values())

    def get_node(self, node_id: str) -> Node:
        try:
            return self._nodes[node_id]
        except KeyError:
            raise ValidationError(f"Unknown node id: {node_id}") from None

    def dependencies_of(self, node_id: str) -> Set[str]:
        if node_id not in self._nodes:
            raise ValidationError(f"Unknown node id: {node_id}")
        return set(self._deps.get(node_id, set()))

    def dependents_of(self, node_id: str) -> Set[str]:
        if node_id not in self._nodes:
            raise ValidationError(f"Unknown node id: {node_id}")
        return set(self._rev.get(node_id, set()))

    def validate_acyclic(self) -> None:
        indeg: Dict[str, int] = {nid: len(self._deps.get(nid, set())) for nid in self._nodes}
        q: Deque[str] = deque([nid for nid, d in indeg.items() if d == 0])
        visited = 0
        while q:
            n = q.popleft()
            visited += 1
            for m in self._rev.get(n, set()):
                indeg[m] -= 1
                if indeg[m] == 0:
                    q.append(m)
        if visited != len(self._nodes):
            raise ValidationError("Graph contains a cycle")

    def topological_order(self) -> List[str]:
        self.validate_acyclic()
        indeg: Dict[str, int] = {nid: len(self._deps.get(nid, set())) for nid in self._nodes}
        q: Deque[str] = deque([nid for nid, d in indeg.items() if d == 0])
        order: List[str] = []
        while q:
            n = q.popleft()
            order.append(n)
            for m in self._rev.get(n, set()):
                indeg[m] -= 1
                if indeg[m] == 0:
                    q.append(m)
        return order


class GraphExecutionEngine:
    def __init__(
        self,
        graph: Graph,
        *,
        tracer: Optional[TelemetryTracer] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        snapshot_each_node: bool = True,
    ) -> None:
        self._graph = graph
        self._tracer = tracer or NoopTracer()
        self._middleware = list(middleware or [])
        self._snapshot_each_node = snapshot_each_node

    @property
    def graph(self) -> Graph:
        return self._graph

    async def run(self, ctx: ExecutionContext, *, node_ids: Optional[Sequence[str]] = None) -> ExecutionContext:
        span = self._tracer.start_span("graph.run", {"graph.id": self._graph.id, "graph.name": self._graph.name})
        try:
            self._graph.validate_acyclic()
            order = self._graph.topological_order()
            selected: Optional[Set[str]] = set(node_ids) if node_ids is not None else None
            if selected is not None:
                for nid in selected:
                    if nid not in {n.id for n in self._graph.nodes()}:
                        raise ValidationError(f"Unknown node id in selection: {nid}")
                needed = self._closure_with_deps(selected)
                order = [nid for nid in order if nid in needed]

            combined_mw: List[Middleware] = list(ctx.middleware) + list(self._middleware)

            for nid in order:
                node = self._graph.get_node(nid)
                node_span = ctx.tracer.start_span("graph.node", {"node.id": node.id, "node.name": node.name})
                try:
                    for mw in combined_mw:
                        await mw.before_node(ctx, node)
                    result = await node.run(ctx)
                    ctx.set_result(node.id, result)
                    for mw in reversed(combined_mw):
                        await mw.after_node(ctx, node, result)
                    if self._snapshot_each_node:
                        ctx.snapshot(metadata={"node_id": node.id, "node_name": node.name})
                except BaseException as e:
                    ctx.set_error(node.id, e)
                    for mw in reversed(combined_mw):
                        try:
                            await mw.on_error(ctx, node, e)
                        except BaseException:
                            pass
                    node_span.record_exception(e)
                    raise ExecutionError(f"Node failed: {node.id}") from e
                finally:
                    node_span.end()
            return ctx
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()

    def _closure_with_deps(self, node_ids: Set[str]) -> Set[str]:
        needed: Set[str] = set()
        stack: List[str] = list(node_ids)
        while stack:
            nid = stack.pop()
            if nid in needed:
                continue
            needed.add(nid)
            for dep in self._graph.dependencies_of(nid):
                stack.append(dep)
        return needed


class DirectedGraphPolicy(abc.ABC):
    @abc.abstractmethod
    async def choose_next(self, ctx: ExecutionContext, graph: Graph, completed: Set[str]) -> Optional[str]:
        raise NotImplementedError


class TopologicalPolicy(DirectedGraphPolicy):
    def __init__(self) -> None:
        self._cached_order: Dict[str, List[str]] = {}

    async def choose_next(self, ctx: ExecutionContext, graph: Graph, completed: Set[str]) -> Optional[str]:
        order = self._cached_order.get(graph.id)
        if order is None:
            graph.validate_acyclic()
            order = graph.topological_order()
            self._cached_order[graph.id] = order
        for nid in order:
            if nid in completed:
                continue
            deps = graph.dependencies_of(nid)
            if deps.issubset(completed):
                return nid
        return None


class LLMDirectedPolicy(DirectedGraphPolicy):
    def __init__(
        self,
        client: InferenceClient,
        request_builder: Callable[[ExecutionContext, Graph, Set[str]], Union[InferenceRequest, Awaitable[InferenceRequest]]],
        *,
        allowed_node_ids: Optional[Set[str]] = None,
    ) -> None:
        self._client = client
        self._request_builder = request_builder
        self._allowed = set(allowed_node_ids) if allowed_node_ids is not None else None

    async def choose_next(self, ctx: ExecutionContext, graph: Graph, completed: Set[str]) -> Optional[str]:
        req = self._request_builder(ctx, graph, completed)
        if asyncio.iscoroutine(req):
            req = await req
        if not isinstance(req, InferenceRequest):
            raise ValidationError("request_builder must return InferenceRequest")
        resp = await self._client.infer(dataclasses.replace(req, stream=False))
        choice = (resp.content or "").strip()
        if not choice:
            return None
        if choice not in {n.id for n in graph.nodes()}:
            raise ValidationError("LLMDirectedPolicy returned unknown node id")
        if self._allowed is not None and choice not in self._allowed:
            raise ValidationError("LLMDirectedPolicy returned node id not in allowed set")
        if choice in completed:
            return None
        if not graph.dependencies_of(choice).issubset(completed):
            return None
        return choice


class DirectedGraphExecutionEngine:
    def __init__(
        self,
        graph: Graph,
        policy: DirectedGraphPolicy,
        *,
        tracer: Optional[TelemetryTracer] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        snapshot_each_node: bool = True,
        max_steps: Optional[int] = None,
    ) -> None:
        self._graph = graph
        self._policy = policy
        self._tracer = tracer or NoopTracer()
        self._middleware = list(middleware or [])
        self._snapshot_each_node = snapshot_each_node
        self._max_steps = max_steps

    async def run(self, ctx: ExecutionContext) -> ExecutionContext:
        span = self._tracer.start_span("graph.directed.run", {"graph.id": self._graph.id, "graph.name": self._graph.name})
        try:
            self._graph.validate_acyclic()
            combined_mw: List[Middleware] = list(ctx.middleware) + list(self._middleware)
            completed: Set[str] = set()
            steps = 0
            while True:
                if self._max_steps is not None and steps >= self._max_steps:
                    raise ExecutionError("Maximum directed execution steps exceeded")
                nid = await self._policy.choose_next(ctx, self._graph, completed)
                if nid is None:
                    break
                node = self._graph.get_node(nid)
                node_span = ctx.tracer.start_span("graph.directed.node", {"node.id": node.id, "node.name": node.name})
                try:
                    for mw in combined_mw:
                        await mw.before_node(ctx, node)
                    result = await node.run(ctx)
                    ctx.set_result(node.id, result)
                    completed.add(node.id)
                    for mw in reversed(combined_mw):
                        await mw.after_node(ctx, node, result)
                    if self._snapshot_each_node:
                        ctx.snapshot(metadata={"node_id": node.id, "node_name": node.name})
                except BaseException as e:
                    ctx.set_error(node.id, e)
                    for mw in reversed(combined_mw):
                        try:
                            await mw.on_error(ctx, node, e)
                        except BaseException:
                            pass
                    node_span.record_exception(e)
                    raise ExecutionError(f"Node failed: {node.id}") from e
                finally:
                    node_span.end()
                steps += 1
            return ctx
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()


class AbstractCache(abc.ABC):
    @abc.abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    @abc.abstractmethod
    async def set(self, key: str, value: Any, *, ttl_seconds: Optional[int] = None) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, key: str) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_all(self, keys: Sequence[str]) -> Dict[str, Optional[Any]]:
        raise NotImplementedError

    @abc.abstractmethod
    async def clear(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def namespace(self, *, prefix: str = "", suffix: str = "") -> "AbstractCache":
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


class _JsonCodec:
    @staticmethod
    def dumps(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)

    @staticmethod
    def loads(data: str) -> Any:
        return json.loads(data)


class InMemoryRedisLike:
    def __init__(self) -> None:
        self._data: Dict[str, Tuple[str, Optional[float]]] = {}
        self._lock = asyncio.Lock()
        self._mailboxes: Dict[str, List[asyncio.Queue[str]]] = defaultdict(list)

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            value, expires_at = item
            if expires_at is not None and time.time() >= expires_at:
                self._data.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> None:
        expires_at = None
        if ttl_seconds is not None:
            if ttl_seconds <= 0:
                expires_at = time.time() - 1.0
            else:
                expires_at = time.time() + float(ttl_seconds)
        async with self._lock:
            self._data[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._data.pop(key, None)

    async def mget(self, keys: Sequence[str]) -> List[Optional[str]]:
        async with self._lock:
            now = time.time()
            out: List[Optional[str]] = []
            for k in keys:
                item = self._data.get(k)
                if item is None:
                    out.append(None)
                    continue
                value, expires_at = item
                if expires_at is not None and now >= expires_at:
                    self._data.pop(k, None)
                    out.append(None)
                else:
                    out.append(value)
            return out

    async def clear(self) -> None:
        async with self._lock:
            self._data.clear()

    async def publish(self, channel: str, message: str) -> None:
        async with self._lock:
            queues = list(self._mailboxes.get(channel, []))
        for q in queues:
            q.put_nowait(message)

    async def subscribe(self, channel: str) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue()
        async with self._lock:
            self._mailboxes[channel].append(q)
        return q

    async def unsubscribe(self, channel: str, q: asyncio.Queue[str]) -> None:
        async with self._lock:
            if channel in self._mailboxes:
                try:
                    self._mailboxes[channel].remove(q)
                except ValueError:
                    pass
                if not self._mailboxes[channel]:
                    self._mailboxes.pop(channel, None)


class RedisCache(AbstractCache):
    def __init__(
        self,
        redis: Optional[InMemoryRedisLike] = None,
        *,
        prefix: str = "",
        suffix: str = "",
    ) -> None:
        self._redis = redis or InMemoryRedisLike()
        self._prefix = prefix
        self._suffix = suffix

    def _k(self, key: str) -> str:
        if not isinstance(key, str) or not key:
            raise ValidationError("Cache key must be a non-empty string")
        return f"{self._prefix}{key}{self._suffix}"

    async def get(self, key: str) -> Optional[Any]:
        data = await self._redis.get(self._k(key))
        if data is None:
            return None
        try:
            return _JsonCodec.loads(data)
        except Exception as e:
            raise CacheError("Failed to deserialize cached value") from e

    async def set(self, key: str, value: Any, *, ttl_seconds: Optional[int] = None) -> None:
        try:
            data = _JsonCodec.dumps(value)
        except Exception as e:
            raise CacheError("Failed to serialize cached value") from e
        await self._redis.set(self._k(key), data, ttl_seconds=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self._redis.delete(self._k(key))

    async def get_all(self, keys: Sequence[str]) -> Dict[str, Optional[Any]]:
        if keys is None:
            raise ValidationError("keys must not be None")
        mapped_keys = [self._k(k) for k in keys]
        values = await self._redis.mget(mapped_keys)
        out: Dict[str, Optional[Any]] = {}
        for orig, raw in zip(keys, values):
            if raw is None:
                out[orig] = None
            else:
                try:
                    out[orig] = _JsonCodec.loads(raw)
                except Exception as e:
                    raise CacheError("Failed to deserialize cached value in bulk get") from e
        return out

    async def clear(self) -> None:
        await self._redis.clear()

    def namespace(self, *, prefix: str = "", suffix: str = "") -> AbstractCache:
        return RedisCache(self._redis, prefix=self._prefix + prefix, suffix=suffix + self._suffix)

    def mailbox(self, name: str) -> "Mailbox":
        if not isinstance(name, str) or not name:
            raise ValidationError("Mailbox name must be a non-empty string")
        channel = self._k(f"mailbox:{name}")
        return RedisMailbox(self._redis, channel)


class RedisMailbox(Mailbox):
    def __init__(self, redis: InMemoryRedisLike, channel: str) -> None:
        self._redis = redis
        self._channel = channel

    async def publish(self, message: Any) -> None:
        try:
            data = _JsonCodec.dumps(message)
        except Exception as e:
            raise CacheError("Failed to serialize mailbox message") from e
        await self._redis.publish(self._channel, data)

    async def subscribe(self) -> AsyncGenerator[Any, None]:
        q = await self._redis.subscribe(self._channel)
        try:
            while True:
                raw = await q.get()
                try:
                    yield _JsonCodec.loads(raw)
                except Exception as e:
                    raise CacheError("Failed to deserialize mailbox message") from e
        finally:
            await self._redis.unsubscribe(self._channel, q)


class SimpleEchoInferenceClient(InferenceClient):
    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        span = self.tracer.start_span("inference.echo.infer", {"model": request.model})
        try:
            content = ""
            for m in request.messages:
                if isinstance(m, dict) and m.get("role") == "user":
                    content += str(m.get("content", ""))
            usage = TokenUsage(prompt_tokens=len(json.dumps(request.messages)), completion_tokens=len(content))
            return InferenceResponse(content=content, tool_calls=[], usage=usage, raw={"provider": "echo"})
        except BaseException as e:
            span.record_exception(e)
            raise InferenceError("Echo inference failed") from e
        finally:
            span.end()

    async def stream(self, request: InferenceRequest) -> AsyncGenerator[InferenceDelta, None]:
        if not request.stream:
            request = dataclasses.replace(request, stream=True)
        span = self.tracer.start_span("inference.echo.stream", {"model": request.model})
        try:
            resp = await self.infer(dataclasses.replace(request, stream=False))
            for ch in resp.content:
                yield InferenceDelta(content=ch, usage=None, raw=None)
            yield InferenceDelta(content=None, usage=resp.usage, raw=None)
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()