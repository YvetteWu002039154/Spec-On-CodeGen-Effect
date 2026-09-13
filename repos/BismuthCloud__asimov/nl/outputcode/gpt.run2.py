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
        return int(self.prompt_tokens) + int(self.completion_tokens)


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class InferenceResult:
    text: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    provider: str = ""
    model: str = ""
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceRequest:
    prompt: str
    model: str
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    stream: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


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
    async def get(self, key: str) -> Any:
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
    def __init__(self, queue: "asyncio.Queue[str]"):
        self._queue = queue

    async def publish(self, message: Any) -> None:
        await self._queue.put(JSONSerializer.dumps(message))

    async def subscribe(self) -> AsyncGenerator[Any, None]:
        while True:
            raw = await self._queue.get()
            yield JSONSerializer.loads(raw)


class RedisCache(Cache):
    def __init__(
        self,
        prefix: str = "",
        suffix: str = "",
    ):
        self._prefix = prefix or ""
        self._suffix = suffix or ""
        self._store: Dict[str, Tuple[Optional[float], str]] = {}
        self._mailboxes: Dict[str, asyncio.Queue[str]] = defaultdict(asyncio.Queue)
        self._lock = asyncio.Lock()

    def _ns(self, key: str) -> str:
        if not isinstance(key, str) or not key:
            raise ValidationError("Cache key must be a non-empty string")
        return f"{self._prefix}{key}{self._suffix}"

    def mailbox(self, name: str) -> Mailbox:
        if not isinstance(name, str) or not name:
            raise ValidationError("Mailbox name must be a non-empty string")
        q = self._mailboxes[name]
        return _InMemoryMailbox(q)

    async def _purge_if_expired(self, nkey: str) -> None:
        item = self._store.get(nkey)
        if item is None:
            return
        expires_at, _ = item
        if expires_at is not None and time.time() >= expires_at:
            self._store.pop(nkey, None)

    async def get(self, key: str) -> Any:
        nkey = self._ns(key)
        async with self._lock:
            await self._purge_if_expired(nkey)
            item = self._store.get(nkey)
            if item is None:
                return None
            _, raw = item
        return JSONSerializer.loads(raw)

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        if ttl_seconds is not None:
            if not isinstance(ttl_seconds, int) or ttl_seconds <= 0:
                raise ValidationError("ttl_seconds must be a positive integer when provided")
        nkey = self._ns(key)
        raw = JSONSerializer.dumps(value)
        expires_at = (time.time() + ttl_seconds) if ttl_seconds is not None else None
        async with self._lock:
            self._store[nkey] = (expires_at, raw)

    async def delete(self, key: str) -> None:
        nkey = self._ns(key)
        async with self._lock:
            self._store.pop(nkey, None)

    async def get_all(self, keys: Sequence[str]) -> Dict[str, Any]:
        if keys is None:
            raise ValidationError("keys must not be None")
        result: Dict[str, Any] = {}
        async with self._lock:
            for key in keys:
                nkey = self._ns(key)
                await self._purge_if_expired(nkey)
                item = self._store.get(nkey)
                if item is None:
                    continue
                _, raw = item
                result[key] = JSONSerializer.loads(raw)
        return result

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()


class Tracer(Protocol):
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> "Span":
        ...


class Span(Protocol):
    def set_attribute(self, key: str, value: Any) -> None:
        ...

    def record_exception(self, exc: BaseException) -> None:
        ...

    def end(self) -> None:
        ...


class NoopSpan:
    def __init__(self) -> None:
        self._ended = False

    def set_attribute(self, key: str, value: Any) -> None:
        return None

    def record_exception(self, exc: BaseException) -> None:
        return None

    def end(self) -> None:
        self._ended = True


class NoopTracer:
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Span:
        return NoopSpan()


class Middleware(abc.ABC):
    @abc.abstractmethod
    async def before_node(self, ctx: "ExecutionContext", node: "Node") -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def after_node(self, ctx: "ExecutionContext", node: "Node", result: Any) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def on_error(self, ctx: "ExecutionContext", node: "Node", error: BaseException) -> None:
        raise NotImplementedError


class BaseMiddleware(Middleware):
    async def before_node(self, ctx: "ExecutionContext", node: "Node") -> None:
        return None

    async def after_node(self, ctx: "ExecutionContext", node: "Node", result: Any) -> None:
        return None

    async def on_error(self, ctx: "ExecutionContext", node: "Node", error: BaseException) -> None:
        return None


@dataclass
class StateSnapshot:
    snapshot_id: str
    created_at: float
    state: Dict[str, Any]
    node_results: Dict[str, Any]
    completed_nodes: List[str]


class SnapshotStore(abc.ABC):
    @abc.abstractmethod
    async def save(self, snapshot: StateSnapshot) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def load(self, snapshot_id: str) -> Optional[StateSnapshot]:
        raise NotImplementedError


class InMemorySnapshotStore(SnapshotStore):
    def __init__(self) -> None:
        self._snapshots: Dict[str, StateSnapshot] = {}
        self._lock = asyncio.Lock()

    async def save(self, snapshot: StateSnapshot) -> None:
        async with self._lock:
            self._snapshots[snapshot.snapshot_id] = snapshot

    async def load(self, snapshot_id: str) -> Optional[StateSnapshot]:
        async with self._lock:
            return self._snapshots.get(snapshot_id)


@dataclass
class ExecutionContext:
    state: Dict[str, Any] = field(default_factory=dict)
    node_results: Dict[str, Any] = field(default_factory=dict)
    tracer: Tracer = field(default_factory=NoopTracer)
    cache: Optional[Cache] = None
    snapshot_store: Optional[SnapshotStore] = None
    middleware: List[Middleware] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.state[key] = value

    async def snapshot(self, snapshot_id: Optional[str] = None) -> StateSnapshot:
        sid = snapshot_id or str(uuid.uuid4())
        snap = StateSnapshot(
            snapshot_id=sid,
            created_at=time.time(),
            state=json.loads(JSONSerializer.dumps(self.state)),
            node_results=json.loads(JSONSerializer.dumps(self.node_results)),
            completed_nodes=list(self.node_results.keys()),
        )
        if self.snapshot_store is not None:
            await self.snapshot_store.save(snap)
        return snap


NodeFunc = Callable[[ExecutionContext], Awaitable[Any]]


class Node:
    def __init__(self, node_id: str, func: NodeFunc):
        if not isinstance(node_id, str) or not node_id:
            raise ValidationError("node_id must be a non-empty string")
        if not callable(func):
            raise ValidationError("func must be callable")
        self._id = node_id
        self._func = func

    @property
    def id(self) -> str:
        return self._id

    async def run(self, ctx: ExecutionContext) -> Any:
        return await self._func(ctx)


class Graph:
    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_edges: Dict[str, Set[str]] = defaultdict(set)

    def add_node(self, node: Node) -> None:
        if node.id in self._nodes:
            raise ValidationError(f"Duplicate node id: {node.id}")
        self._nodes[node.id] = node

    def add_edge(self, from_node_id: str, to_node_id: str) -> None:
        if from_node_id not in self._nodes or to_node_id not in self._nodes:
            raise ValidationError("Both nodes must be added before creating an edge")
        if from_node_id == to_node_id:
            raise ValidationError("Self edges are not allowed")
        self._edges[from_node_id].add(to_node_id)
        self._reverse_edges[to_node_id].add(from_node_id)

    def node(self, node_id: str) -> Node:
        try:
            return self._nodes[node_id]
        except KeyError as e:
            raise ValidationError(f"Unknown node id: {node_id}") from e

    @property
    def nodes(self) -> Mapping[str, Node]:
        return dict(self._nodes)

    def dependencies_of(self, node_id: str) -> Set[str]:
        if node_id not in self._nodes:
            raise ValidationError(f"Unknown node id: {node_id}")
        return set(self._reverse_edges.get(node_id, set()))

    def dependents_of(self, node_id: str) -> Set[str]:
        if node_id not in self._nodes:
            raise ValidationError(f"Unknown node id: {node_id}")
        return set(self._edges.get(node_id, set()))

    def _topological_order(self) -> List[str]:
        indeg: Dict[str, int] = {nid: 0 for nid in self._nodes}
        for to_id, deps in self._reverse_edges.items():
            indeg[to_id] = len(deps)
        q: Deque[str] = deque([nid for nid, d in indeg.items() if d == 0])
        order: List[str] = []
        edges = {k: set(v) for k, v in self._edges.items()}
        while q:
            n = q.popleft()
            order.append(n)
            for m in edges.get(n, set()):
                indeg[m] -= 1
                if indeg[m] == 0:
                    q.append(m)
        if len(order) != len(self._nodes):
            raise GraphError("Graph contains a cycle")
        return order


class GraphExecutionEngine:
    def __init__(self, graph: Graph):
        self._graph = graph

    async def execute(
        self,
        ctx: ExecutionContext,
        *,
        start_nodes: Optional[Sequence[str]] = None,
        stop_nodes: Optional[Set[str]] = None,
        snapshot_each_node: bool = False,
    ) -> Dict[str, Any]:
        if stop_nodes is None:
            stop_nodes = set()

        if start_nodes is None:
            order = self._graph._topological_order()
            allowed: Set[str] = set(order)
        else:
            for nid in start_nodes:
                if nid not in self._graph.nodes:
                    raise ValidationError(f"Unknown start node id: {nid}")
            allowed = self._reachable_from(set(start_nodes))
            order = [nid for nid in self._graph._topological_order() if nid in allowed]

        completed: Set[str] = set(ctx.node_results.keys())
        for nid in order:
            if nid in completed:
                continue
            if nid in stop_nodes:
                break
            deps = self._graph.dependencies_of(nid)
            if not deps.issubset(completed):
                missing = sorted(list(deps - completed))
                raise GraphError(f"Node '{nid}' dependencies not satisfied: {missing}")

            node = self._graph.node(nid)
            span = ctx.tracer.start_span("graph.node", attributes={"node.id": node.id})
            try:
                for mw in ctx.middleware:
                    await mw.before_node(ctx, node)
                result = await node.run(ctx)
                ctx.node_results[node.id] = result
                for mw in ctx.middleware:
                    await mw.after_node(ctx, node, result)
                if snapshot_each_node:
                    await ctx.snapshot()
            except BaseException as e:
                try:
                    for mw in ctx.middleware:
                        await mw.on_error(ctx, node, e)
                finally:
                    span.record_exception(e)
                    span.end()
                raise
            span.end()
            completed.add(nid)

        return dict(ctx.node_results)

    def _reachable_from(self, starts: Set[str]) -> Set[str]:
        seen: Set[str] = set()
        q: Deque[str] = deque(starts)
        while q:
            n = q.popleft()
            if n in seen:
                continue
            seen.add(n)
            for m in self._graph.dependents_of(n):
                if m not in seen:
                    q.append(m)
        return seen


class InferenceClient(abc.ABC):
    @property
    @abc.abstractmethod
    def provider(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    async def infer(self, request: InferenceRequest, *, ctx: Optional[ExecutionContext] = None) -> InferenceResult:
        raise NotImplementedError

    @abc.abstractmethod
    async def stream(self, request: InferenceRequest, *, ctx: Optional[ExecutionContext] = None) -> AsyncGenerator[str, None]:
        raise NotImplementedError


class PromptCache:
    def __init__(self, cache: Cache, *, prefix: str = "prompt_cache:"):
        if cache is None:
            raise ValidationError("cache must not be None")
        self._cache = cache
        self._prefix = prefix

    def _key(self, request: InferenceRequest, provider: str) -> str:
        payload = {
            "provider": provider,
            "model": request.model,
            "prompt": request.prompt,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "tools": request.tools,
            "tool_choice": request.tool_choice,
            "metadata": request.metadata,
        }
        raw = JSONSerializer.dumps(payload)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"{self._prefix}{digest}"

    async def get(self, request: InferenceRequest, provider: str) -> Optional[InferenceResult]:
        key = self._key(request, provider)
        data = await self._cache.get(key)
        if data is None:
            return None
        if not isinstance(data, dict):
            return None
        try:
            tool_calls = [ToolCall(**tc) for tc in data.get("tool_calls", [])]
            usage = TokenUsage(**data.get("usage", {}))
            return InferenceResult(
                text=str(data.get("text", "")),
                tool_calls=tool_calls,
                usage=usage,
                provider=str(data.get("provider", provider)),
                model=str(data.get("model", request.model)),
                cached=True,
                metadata=dict(data.get("metadata", {})),
            )
        except Exception:
            return None

    async def set(self, request: InferenceRequest, provider: str, result: InferenceResult, ttl_seconds: Optional[int] = None) -> None:
        key = self._key(request, provider)
        payload = {
            "text": result.text,
            "tool_calls": [dataclasses.asdict(tc) for tc in result.tool_calls],
            "usage": dataclasses.asdict(result.usage),
            "provider": result.provider,
            "model": result.model,
            "metadata": result.metadata,
        }
        await self._cache.set(key, payload, ttl_seconds=ttl_seconds)


class SimpleLLMClient(InferenceClient):
    def __init__(
        self,
        *,
        provider: str,
        model: str,
        tracer: Optional[Tracer] = None,
        cache: Optional[PromptCache] = None,
        cache_ttl_seconds: Optional[int] = None,
    ):
        if not isinstance(provider, str) or not provider:
            raise ValidationError("provider must be a non-empty string")
        if not isinstance(model, str) or not model:
            raise ValidationError("model must be a non-empty string")
        if cache_ttl_seconds is not None and (not isinstance(cache_ttl_seconds, int) or cache_ttl_seconds <= 0):
            raise ValidationError("cache_ttl_seconds must be a positive integer when provided")
        self._provider = provider
        self._default_model = model
        self._tracer = tracer or NoopTracer()
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds

    @property
    def provider(self) -> str:
        return self._provider

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    def _validate_request(self, request: InferenceRequest) -> None:
        if not isinstance(request.prompt, str):
            raise ValidationError("prompt must be a string")
        if not isinstance(request.model, str) or not request.model:
            raise ValidationError("model must be a non-empty string")
        if not isinstance(request.temperature, (int, float)):
            raise ValidationError("temperature must be a number")
        if request.max_tokens is not None and (not isinstance(request.max_tokens, int) or request.max_tokens <= 0):
            raise ValidationError("max_tokens must be a positive integer when provided")
        if request.tools is not None and not isinstance(request.tools, list):
            raise ValidationError("tools must be a list when provided")

    def _maybe_tool_call(self, request: InferenceRequest) -> List[ToolCall]:
        if not request.tools:
            return []
        if request.tool_choice is None:
            return []
        if isinstance(request.tool_choice, str):
            if request.tool_choice == "none":
                return []
            if request.tool_choice == "auto":
                return []
            name = request.tool_choice
            return [ToolCall(name=name, arguments={})]
        if isinstance(request.tool_choice, dict):
            name = request.tool_choice.get("name")
            if isinstance(name, str) and name:
                args = request.tool_choice.get("arguments")
                if args is None:
                    args = {}
                if not isinstance(args, dict):
                    raise ValidationError("tool_choice.arguments must be a dict when provided")
                return [ToolCall(name=name, arguments=args)]
        return []

    async def infer(self, request: InferenceRequest, *, ctx: Optional[ExecutionContext] = None) -> InferenceResult:
        self._validate_request(request)
        model = request.model or self._default_model
        tracer = (ctx.tracer if ctx is not None else self._tracer) or NoopTracer()
        span = tracer.start_span("inference.infer", attributes={"provider": self.provider, "model": model})
        try:
            if self._cache is not None:
                cached = await self._cache.get(request, self.provider)
                if cached is not None:
                    span.set_attribute("cache.hit", True)
                    return cached
                span.set_attribute("cache.hit", False)

            tool_calls = self._maybe_tool_call(request)
            if tool_calls:
                text = ""
                completion_tokens = 0
            else:
                text = f"{request.prompt}"
                completion_tokens = self._estimate_tokens(text)

            prompt_tokens = self._estimate_tokens(request.prompt)
            usage = TokenUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
            result = InferenceResult(
                text=text,
                tool_calls=tool_calls,
                usage=usage,
                provider=self.provider,
                model=model,
                cached=False,
                metadata=dict(request.metadata),
            )

            if self._cache is not None:
                await self._cache.set(request, self.provider, result, ttl_seconds=self._cache_ttl_seconds)

            return result
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()

    async def stream(self, request: InferenceRequest, *, ctx: Optional[ExecutionContext] = None) -> AsyncGenerator[str, None]:
        self._validate_request(request)
        model = request.model or self._default_model
        tracer = (ctx.tracer if ctx is not None else self._tracer) or NoopTracer()
        span = tracer.start_span("inference.stream", attributes={"provider": self.provider, "model": model})
        try:
            if self._cache is not None:
                cached = await self._cache.get(request, self.provider)
                if cached is not None:
                    span.set_attribute("cache.hit", True)
                    if cached.text:
                        yield cached.text
                    return
                span.set_attribute("cache.hit", False)

            tool_calls = self._maybe_tool_call(request)
            if tool_calls:
                return

            text = f"{request.prompt}"
            chunk_size = 32
            for i in range(0, len(text), chunk_size):
                await asyncio.sleep(0)
                yield text[i : i + chunk_size]

            if self._cache is not None:
                prompt_tokens = self._estimate_tokens(request.prompt)
                completion_tokens = self._estimate_tokens(text)
                result = InferenceResult(
                    text=text,
                    tool_calls=[],
                    usage=TokenUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
                    provider=self.provider,
                    model=model,
                    cached=False,
                    metadata=dict(request.metadata),
                )
                await self._cache.set(request, self.provider, result, ttl_seconds=self._cache_ttl_seconds)
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()


class LLMDirectedGraphExecutor:
    def __init__(
        self,
        graph: Graph,
        llm: InferenceClient,
        *,
        tracer: Optional[Tracer] = None,
    ):
        self._graph = graph
        self._engine = GraphExecutionEngine(graph)
        self._llm = llm
        self._tracer = tracer or NoopTracer()

    async def execute(
        self,
        ctx: ExecutionContext,
        *,
        planner_prompt: str,
        allowed_nodes: Optional[Set[str]] = None,
        snapshot_each_node: bool = False,
    ) -> Dict[str, Any]:
        if not isinstance(planner_prompt, str) or not planner_prompt:
            raise ValidationError("planner_prompt must be a non-empty string")
        if allowed_nodes is not None:
            unknown = [n for n in allowed_nodes if n not in self._graph.nodes]
            if unknown:
                raise ValidationError(f"Unknown allowed node ids: {unknown}")

        tracer = ctx.tracer if ctx is not None else self._tracer
        span = tracer.start_span("graph.llm_directed_execute")
        try:
            plan_request = InferenceRequest(prompt=planner_prompt, model=getattr(self._llm, "_default_model", ""))
            plan = await self._llm.infer(plan_request, ctx=ctx)
            node_order = self._parse_plan(plan.text)
            if not node_order:
                raise GraphError("LLM plan did not specify any nodes")

            for nid in node_order:
                if nid not in self._graph.nodes:
                    raise GraphError(f"LLM plan referenced unknown node id: {nid}")
                if allowed_nodes is not None and nid not in allowed_nodes:
                    raise GraphError(f"LLM plan referenced disallowed node id: {nid}")

            return await self._engine.execute(ctx, start_nodes=node_order, snapshot_each_node=snapshot_each_node)
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()

    def _parse_plan(self, text: str) -> List[str]:
        if not text:
            return []
        stripped = text.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            try:
                data = json.loads(stripped)
                if isinstance(data, list) and all(isinstance(x, str) for x in data):
                    return [x for x in data if x]
            except Exception:
                pass
        parts = [p.strip() for p in stripped.replace("\n", ",").split(",")]
        return [p for p in parts if p]


__all__ = [
    "FrameworkError",
    "ValidationError",
    "GraphError",
    "CacheError",
    "InferenceError",
    "TokenUsage",
    "ToolCall",
    "InferenceResult",
    "InferenceRequest",
    "Cache",
    "Mailbox",
    "RedisCache",
    "Tracer",
    "Span",
    "NoopTracer",
    "NoopSpan",
    "Middleware",
    "BaseMiddleware",
    "StateSnapshot",
    "SnapshotStore",
    "InMemorySnapshotStore",
    "ExecutionContext",
    "Node",
    "Graph",
    "GraphExecutionEngine",
    "InferenceClient",
    "PromptCache",
    "SimpleLLMClient",
    "LLMDirectedGraphExecutor",
]