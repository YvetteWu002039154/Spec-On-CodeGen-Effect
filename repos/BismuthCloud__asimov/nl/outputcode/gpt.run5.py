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


def _now_ms() -> int:
    return int(time.time() * 1000)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def _json_loads(value: str) -> Any:
    return json.loads(value)


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
    result: Any


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
class InferenceResponse:
    content: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    raw: Any = None
    cached: bool = False


@dataclass(frozen=True)
class InferenceChunk:
    delta: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: Optional[TokenUsage] = None
    raw: Any = None
    cached: bool = False


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
        return

    def record_exception(self, exc: BaseException) -> None:
        return

    def end(self) -> None:
        self._ended = True


class NoopTracer:
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> TelemetrySpan:
        return _NoopSpan()


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


class RedisCache(Cache):
    def __init__(self, prefix: str = "", suffix: str = "") -> None:
        self._prefix = prefix
        self._suffix = suffix
        self._store: Dict[str, Tuple[str, Optional[int]]] = {}
        self._lock = asyncio.Lock()
        self._mailboxes: Dict[str, "_InMemoryMailbox"] = {}

    def _ns(self, key: str) -> str:
        return f"{self._prefix}{key}{self._suffix}"

    def _is_expired(self, expires_at_ms: Optional[int]) -> bool:
        return expires_at_ms is not None and _now_ms() >= expires_at_ms

    async def get(self, key: str) -> Optional[Any]:
        k = self._ns(key)
        async with self._lock:
            item = self._store.get(k)
            if item is None:
                return None
            payload, expires_at_ms = item
            if self._is_expired(expires_at_ms):
                self._store.pop(k, None)
                return None
            return _json_loads(payload)

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        k = self._ns(key)
        expires_at_ms = None
        if ttl_seconds is not None:
            if ttl_seconds <= 0:
                raise ValidationError("ttl_seconds must be positive")
            expires_at_ms = _now_ms() + ttl_seconds * 1000
        payload = _json_dumps(value)
        async with self._lock:
            self._store[k] = (payload, expires_at_ms)

    async def delete(self, key: str) -> None:
        k = self._ns(key)
        async with self._lock:
            self._store.pop(k, None)

    async def get_all(self, prefix: str = "") -> Dict[str, Any]:
        p = self._ns(prefix)
        out: Dict[str, Any] = {}
        async with self._lock:
            keys = list(self._store.keys())
            for k in keys:
                if not k.startswith(p):
                    continue
                payload, expires_at_ms = self._store.get(k, ("", None))
                if self._is_expired(expires_at_ms):
                    self._store.pop(k, None)
                    continue
                out[k] = _json_loads(payload)
        return out

    async def clear(self, prefix: str = "") -> int:
        p = self._ns(prefix)
        removed = 0
        async with self._lock:
            keys = list(self._store.keys())
            for k in keys:
                if k.startswith(p):
                    self._store.pop(k, None)
                    removed += 1
        return removed

    def mailbox(self, name: str) -> Mailbox:
        if not name:
            raise ValidationError("mailbox name must be non-empty")
        mb = self._mailboxes.get(name)
        if mb is None:
            mb = _InMemoryMailbox(name=name)
            self._mailboxes[name] = mb
        return mb


class _InMemoryMailbox(Mailbox):
    def __init__(self, name: str) -> None:
        self._name = name
        self._subscribers: Set[asyncio.Queue[str]] = set()
        self._lock = asyncio.Lock()

    async def publish(self, message: Any) -> None:
        payload = _json_dumps(message)
        async with self._lock:
            subscribers = list(self._subscribers)
        for q in subscribers:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                await q.put(payload)

    async def subscribe(self) -> AsyncGenerator[Any, None]:
        q: asyncio.Queue[str] = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(q)
        try:
            while True:
                payload = await q.get()
                yield _json_loads(payload)
        finally:
            async with self._lock:
                self._subscribers.discard(q)


class InferenceClient(abc.ABC):
    @abc.abstractmethod
    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        raise NotImplementedError

    @abc.abstractmethod
    async def stream(self, request: InferenceRequest) -> AsyncGenerator[InferenceChunk, None]:
        raise NotImplementedError


class PromptCache:
    def __init__(self, cache: Cache, namespace: str = "prompt_cache:", ttl_seconds: Optional[int] = None) -> None:
        if not namespace:
            raise ValidationError("namespace must be non-empty")
        self._cache = cache
        self._namespace = namespace
        self._ttl_seconds = ttl_seconds

    def _key(self, request: InferenceRequest) -> str:
        stable = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "tools": request.tools,
            "tool_choice": request.tool_choice,
            "metadata": request.metadata,
        }
        return self._namespace + _json_dumps(stable)

    async def get(self, request: InferenceRequest) -> Optional[InferenceResponse]:
        key = self._key(request)
        value = await self._cache.get(key)
        if value is None:
            return None
        try:
            tool_calls = [ToolCall(**tc) for tc in value.get("tool_calls", [])]
            usage = TokenUsage(**value.get("usage", {}))
            return InferenceResponse(
                content=value.get("content"),
                tool_calls=tool_calls,
                usage=usage,
                raw=value.get("raw"),
                cached=True,
            )
        except Exception as e:
            raise CacheError(f"Invalid cached inference response: {e}") from e

    async def set(self, request: InferenceRequest, response: InferenceResponse) -> None:
        key = self._key(request)
        value = {
            "content": response.content,
            "tool_calls": [dataclasses.asdict(tc) for tc in response.tool_calls],
            "usage": dataclasses.asdict(response.usage),
            "raw": response.raw,
        }
        await self._cache.set(key, value, ttl_seconds=self._ttl_seconds)


class CachedInferenceClient(InferenceClient):
    def __init__(
        self,
        inner: InferenceClient,
        prompt_cache: PromptCache,
        tracer: Optional[TelemetryTracer] = None,
    ) -> None:
        self._inner = inner
        self._prompt_cache = prompt_cache
        self._tracer = tracer or NoopTracer()

    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        span = self._tracer.start_span("inference.infer", {"model": request.model, "stream": False})
        try:
            cached = await self._prompt_cache.get(request)
            if cached is not None:
                span.set_attribute("cache.hit", True)
                return cached
            span.set_attribute("cache.hit", False)
            resp = await self._inner.infer(request)
            await self._prompt_cache.set(request, resp)
            return resp
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()

    async def stream(self, request: InferenceRequest) -> AsyncGenerator[InferenceChunk, None]:
        span = self._tracer.start_span("inference.stream", {"model": request.model, "stream": True})
        try:
            cached = await self._prompt_cache.get(request)
            if cached is not None:
                span.set_attribute("cache.hit", True)
                if cached.content:
                    yield InferenceChunk(delta=cached.content, usage=cached.usage, cached=True, raw=cached.raw)
                else:
                    yield InferenceChunk(delta="", tool_calls=cached.tool_calls, usage=cached.usage, cached=True, raw=cached.raw)
                return
            span.set_attribute("cache.hit", False)

            collected_text: List[str] = []
            collected_tool_calls: List[ToolCall] = []
            final_usage: Optional[TokenUsage] = None
            last_raw: Any = None

            async for chunk in self._inner.stream(request):
                if chunk.delta:
                    collected_text.append(chunk.delta)
                if chunk.tool_calls:
                    collected_tool_calls.extend(chunk.tool_calls)
                if chunk.usage is not None:
                    final_usage = chunk.usage
                if chunk.raw is not None:
                    last_raw = chunk.raw
                yield chunk

            resp = InferenceResponse(
                content="".join(collected_text) if collected_text else None,
                tool_calls=collected_tool_calls,
                usage=final_usage or TokenUsage(),
                raw=last_raw,
                cached=False,
            )
            await self._prompt_cache.set(request, resp)
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()


class Middleware(abc.ABC):
    async def before_node(self, ctx: "ExecutionContext", node: "Node") -> None:
        return

    async def after_node(self, ctx: "ExecutionContext", node: "Node", result: Any) -> None:
        return

    async def on_error(self, ctx: "ExecutionContext", node: Optional["Node"], error: BaseException) -> None:
        return


@dataclass(frozen=True)
class StateSnapshot:
    snapshot_id: str
    timestamp_ms: int
    state: Dict[str, Any]
    node_id: Optional[str] = None


class ExecutionContext:
    def __init__(
        self,
        initial_state: Optional[Dict[str, Any]] = None,
        tracer: Optional[TelemetryTracer] = None,
        cache: Optional[Cache] = None,
        inference: Optional[InferenceClient] = None,
    ) -> None:
        self._state: Dict[str, Any] = dict(initial_state or {})
        self._snapshots: List[StateSnapshot] = []
        self._tracer = tracer or NoopTracer()
        self._cache = cache
        self._inference = inference
        self._history: List[Dict[str, Any]] = []

    @property
    def tracer(self) -> TelemetryTracer:
        return self._tracer

    @property
    def cache(self) -> Optional[Cache]:
        return self._cache

    @property
    def inference(self) -> Optional[InferenceClient]:
        return self._inference

    def get_state(self) -> Dict[str, Any]:
        return dict(self._state)

    def set_state(self, updates: Mapping[str, Any]) -> None:
        if updates is None:
            raise ValidationError("updates must not be None")
        self._state.update(dict(updates))

    def snapshot(self, node_id: Optional[str] = None) -> StateSnapshot:
        snap = StateSnapshot(
            snapshot_id=str(uuid.uuid4()),
            timestamp_ms=_now_ms(),
            state=dict(self._state),
            node_id=node_id,
        )
        self._snapshots.append(snap)
        return snap

    def snapshots(self) -> List[StateSnapshot]:
        return list(self._snapshots)

    def record_event(self, event: Mapping[str, Any]) -> None:
        self._history.append(dict(event))

    def history(self) -> List[Dict[str, Any]]:
        return list(self._history)


class Node(abc.ABC):
    def __init__(self, node_id: str, name: Optional[str] = None) -> None:
        if not node_id:
            raise ValidationError("node_id must be non-empty")
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
        name: Optional[str] = None,
    ) -> None:
        super().__init__(node_id=node_id, name=name)
        if func is None:
            raise ValidationError("func must not be None")
        self._func = func

    async def run(self, ctx: ExecutionContext) -> Any:
        res = self._func(ctx)
        if asyncio.iscoroutine(res):
            return await res
        return res


class InferenceNode(Node):
    def __init__(
        self,
        node_id: str,
        request_builder: Callable[[ExecutionContext], InferenceRequest],
        response_handler: Optional[Callable[[ExecutionContext, InferenceResponse], Any]] = None,
        name: Optional[str] = None,
        stream: bool = False,
    ) -> None:
        super().__init__(node_id=node_id, name=name)
        if request_builder is None:
            raise ValidationError("request_builder must not be None")
        self._request_builder = request_builder
        self._response_handler = response_handler
        self._stream = stream

    async def run(self, ctx: ExecutionContext) -> Any:
        if ctx.inference is None:
            raise ExecutionError("No inference client configured in context")
        req = self._request_builder(ctx)
        if not isinstance(req, InferenceRequest):
            raise ValidationError("request_builder must return an InferenceRequest")

        if self._stream:
            chunks: List[InferenceChunk] = []
            async for ch in ctx.inference.stream(dataclasses.replace(req, stream=True)):
                chunks.append(ch)
            text = "".join([c.delta for c in chunks if c.delta])
            tool_calls: List[ToolCall] = []
            usage: Optional[TokenUsage] = None
            raw: Any = None
            cached = any(c.cached for c in chunks)
            for c in chunks:
                if c.tool_calls:
                    tool_calls.extend(c.tool_calls)
                if c.usage is not None:
                    usage = c.usage
                if c.raw is not None:
                    raw = c.raw
            resp = InferenceResponse(content=text or None, tool_calls=tool_calls, usage=usage or TokenUsage(), raw=raw, cached=cached)
        else:
            resp = await ctx.inference.infer(dataclasses.replace(req, stream=False))

        if self._response_handler is not None:
            out = self._response_handler(ctx, resp)
            if asyncio.iscoroutine(out):
                return await out
            return out
        return resp


class DirectedGraphPolicy(abc.ABC):
    @abc.abstractmethod
    async def choose_next(self, ctx: ExecutionContext, graph: "Graph", completed: Set[str]) -> Optional[str]:
        raise NotImplementedError


class TopologicalPolicy(DirectedGraphPolicy):
    async def choose_next(self, ctx: ExecutionContext, graph: "Graph", completed: Set[str]) -> Optional[str]:
        ready = graph.ready_nodes(completed)
        if not ready:
            return None
        return sorted(ready)[0]


class LLMDirectedPolicy(DirectedGraphPolicy):
    def __init__(
        self,
        model: str,
        prompt_builder: Callable[[ExecutionContext, "Graph", Set[str], List[str]], List[Dict[str, Any]]],
        allowed_nodes: Optional[Callable[[ExecutionContext, "Graph", Set[str]], Sequence[str]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        if not model:
            raise ValidationError("model must be non-empty")
        if prompt_builder is None:
            raise ValidationError("prompt_builder must not be None")
        self._model = model
        self._prompt_builder = prompt_builder
        self._allowed_nodes = allowed_nodes
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def choose_next(self, ctx: ExecutionContext, graph: "Graph", completed: Set[str]) -> Optional[str]:
        if ctx.inference is None:
            raise ExecutionError("No inference client configured in context")

        candidates = list(self._allowed_nodes(ctx, graph, completed)) if self._allowed_nodes else sorted(graph.ready_nodes(completed))
        if not candidates:
            return None

        messages = self._prompt_builder(ctx, graph, completed, candidates)
        req = InferenceRequest(
            model=self._model,
            messages=messages,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            stream=False,
            metadata={"policy": "llm_directed", "candidates": candidates},
        )
        resp = await ctx.inference.infer(req)
        choice = (resp.content or "").strip()
        if choice in candidates:
            return choice
        return candidates[0]


class Graph:
    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        self._deps: Dict[str, Set[str]] = defaultdict(set)
        self._rev: Dict[str, Set[str]] = defaultdict(set)

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

    def node(self, node_id: str) -> Node:
        try:
            return self._nodes[node_id]
        except KeyError as e:
            raise ValidationError(f"Unknown node id: {node_id}") from e

    def nodes(self) -> List[Node]:
        return list(self._nodes.values())

    def dependencies(self, node_id: str) -> Set[str]:
        if node_id not in self._nodes:
            raise ValidationError(f"Unknown node id: {node_id}")
        return set(self._deps.get(node_id, set()))

    def dependents(self, node_id: str) -> Set[str]:
        if node_id not in self._nodes:
            raise ValidationError(f"Unknown node id: {node_id}")
        return set(self._rev.get(node_id, set()))

    def ready_nodes(self, completed: Set[str]) -> Set[str]:
        ready: Set[str] = set()
        for nid in self._nodes.keys():
            if nid in completed:
                continue
            deps = self._deps.get(nid, set())
            if deps.issubset(completed):
                ready.add(nid)
        return ready

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


@dataclass(frozen=True)
class NodeResult:
    node_id: str
    started_ms: int
    ended_ms: int
    output: Any = None
    error: Optional[str] = None


@dataclass(frozen=True)
class GraphRunResult:
    run_id: str
    results: List[NodeResult]
    final_state: Dict[str, Any]
    snapshots: List[StateSnapshot]
    history: List[Dict[str, Any]]


class GraphExecutor:
    def __init__(
        self,
        graph: Graph,
        middleware: Optional[Sequence[Middleware]] = None,
        policy: Optional[DirectedGraphPolicy] = None,
        snapshot_each_node: bool = True,
        tracer: Optional[TelemetryTracer] = None,
    ) -> None:
        self._graph = graph
        self._middleware = list(middleware or [])
        self._policy = policy or TopologicalPolicy()
        self._snapshot_each_node = snapshot_each_node
        self._tracer = tracer or NoopTracer()

    async def run(self, ctx: ExecutionContext) -> GraphRunResult:
        self._graph.validate_acyclic()
        run_id = str(uuid.uuid4())
        span = self._tracer.start_span("graph.run", {"run_id": run_id})
        results: List[NodeResult] = []
        completed: Set[str] = set()

        try:
            while len(completed) < len(self._graph.nodes()):
                next_id = await self._policy.choose_next(ctx, self._graph, completed)
                if next_id is None:
                    remaining = set(n.id for n in self._graph.nodes()) - completed
                    raise ExecutionError(f"No runnable nodes found; remaining={sorted(remaining)} completed={sorted(completed)}")

                node = self._graph.node(next_id)
                node_span = ctx.tracer.start_span("graph.node", {"node_id": node.id, "node_name": node.name})
                started = _now_ms()
                try:
                    for mw in self._middleware:
                        await mw.before_node(ctx, node)

                    if self._snapshot_each_node:
                        ctx.snapshot(node_id=node.id)

                    output = await node.run(ctx)

                    for mw in reversed(self._middleware):
                        await mw.after_node(ctx, node, output)

                    ended = _now_ms()
                    results.append(NodeResult(node_id=node.id, started_ms=started, ended_ms=ended, output=output))
                    completed.add(node.id)
                    ctx.record_event({"type": "node_completed", "node_id": node.id, "timestamp_ms": ended})
                except BaseException as e:
                    ended = _now_ms()
                    for mw in reversed(self._middleware):
                        try:
                            await mw.on_error(ctx, node, e)
                        except Exception:
                            pass
                    results.append(NodeResult(node_id=node.id, started_ms=started, ended_ms=ended, output=None, error=str(e)))
                    ctx.record_event({"type": "node_failed", "node_id": node.id, "timestamp_ms": ended, "error": str(e)})
                    node_span.record_exception(e)
                    raise
                finally:
                    node_span.end()

            return GraphRunResult(
                run_id=run_id,
                results=results,
                final_state=ctx.get_state(),
                snapshots=ctx.snapshots(),
                history=ctx.history(),
            )
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()


__all__ = [
    "FrameworkError",
    "ValidationError",
    "ExecutionError",
    "CacheError",
    "InferenceError",
    "TokenUsage",
    "ToolCall",
    "ToolResult",
    "InferenceRequest",
    "InferenceResponse",
    "InferenceChunk",
    "TelemetrySpan",
    "TelemetryTracer",
    "NoopTracer",
    "Cache",
    "Mailbox",
    "RedisCache",
    "InferenceClient",
    "PromptCache",
    "CachedInferenceClient",
    "Middleware",
    "StateSnapshot",
    "ExecutionContext",
    "Node",
    "FunctionNode",
    "InferenceNode",
    "DirectedGraphPolicy",
    "TopologicalPolicy",
    "LLMDirectedPolicy",
    "Graph",
    "NodeResult",
    "GraphRunResult",
    "GraphExecutor",
]