from __future__ import annotations

import abc
import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

T = TypeVar("T")
JsonValue = Union[None, bool, int, float, str, List["JsonValue"], Dict[str, "JsonValue"]]


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


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class InferenceMessage:
    role: str
    content: str
    name: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)

    def to_json(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "name": self.name,
            "tool_calls": [
                {"name": tc.name, "arguments": tc.arguments, "call_id": tc.call_id}
                for tc in self.tool_calls
            ],
        }

    @staticmethod
    def from_json(data: Mapping[str, Any]) -> "InferenceMessage":
        tool_calls = []
        for tc in data.get("tool_calls", []) or []:
            tool_calls.append(
                ToolCall(
                    name=str(tc.get("name", "")),
                    arguments=dict(tc.get("arguments", {}) or {}),
                    call_id=str(tc.get("call_id", str(uuid.uuid4()))),
                )
            )
        return InferenceMessage(
            role=str(data.get("role", "")),
            content=str(data.get("content", "")),
            name=data.get("name", None),
            tool_calls=tool_calls,
        )


@dataclass
class InferenceChunk:
    content_delta: str = ""
    tool_calls_delta: List[ToolCall] = field(default_factory=list)
    usage_delta: TokenUsage = field(default_factory=TokenUsage)
    is_final: bool = False


@dataclass
class InferenceResponse:
    message: InferenceMessage
    usage: TokenUsage = field(default_factory=TokenUsage)
    provider: str = ""
    model: str = ""
    cached: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)


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
        return

    def record_exception(self, exc: BaseException) -> None:
        return

    def end(self) -> None:
        self._ended = True


class NoopTracer:
    def start_span(self, name: str, attributes: Optional[Mapping[str, Any]] = None) -> TelemetrySpan:
        return _NoopSpan()


class Middleware(abc.ABC):
    async def before_node(self, ctx: "ExecutionContext", node: "Node") -> None:
        return

    async def after_node(self, ctx: "ExecutionContext", node: "Node", result: Any) -> None:
        return

    async def on_error(self, ctx: "ExecutionContext", node: "Node", error: BaseException) -> None:
        return


@dataclass
class Snapshot:
    snapshot_id: str
    created_at: float
    graph_id: str
    run_id: str
    state: Dict[str, Any]
    completed_nodes: List[str]
    pending_nodes: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class SnapshotStore(abc.ABC):
    @abc.abstractmethod
    async def save(self, snapshot: Snapshot) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def load(self, snapshot_id: str) -> Snapshot:
        raise NotImplementedError

    @abc.abstractmethod
    async def list(self, graph_id: Optional[str] = None, run_id: Optional[str] = None) -> List[Snapshot]:
        raise NotImplementedError


class InMemorySnapshotStore(SnapshotStore):
    def __init__(self) -> None:
        self._snapshots: Dict[str, Snapshot] = {}

    async def save(self, snapshot: Snapshot) -> None:
        self._snapshots[snapshot.snapshot_id] = snapshot

    async def load(self, snapshot_id: str) -> Snapshot:
        if snapshot_id not in self._snapshots:
            raise ValidationError(f"Snapshot not found: {snapshot_id}")
        return self._snapshots[snapshot_id]

    async def list(self, graph_id: Optional[str] = None, run_id: Optional[str] = None) -> List[Snapshot]:
        out = list(self._snapshots.values())
        if graph_id is not None:
            out = [s for s in out if s.graph_id == graph_id]
        if run_id is not None:
            out = [s for s in out if s.run_id == run_id]
        out.sort(key=lambda s: s.created_at)
        return out


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
    def mailbox(self, name: str) -> "Mailbox":
        raise NotImplementedError


class Mailbox(abc.ABC):
    @abc.abstractmethod
    async def publish(self, message: Any) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def subscribe(self) -> AsyncIterator[Any]:
        raise NotImplementedError


class _InMemoryMailbox(Mailbox):
    def __init__(self, queue: "asyncio.Queue[Any]") -> None:
        self._queue = queue

    async def publish(self, message: Any) -> None:
        await self._queue.put(message)

    async def subscribe(self) -> AsyncIterator[Any]:
        while True:
            msg = await self._queue.get()
            yield msg


class RedisCache(Cache):
    def __init__(self, prefix: str = "", suffix: str = "") -> None:
        self._prefix = prefix
        self._suffix = suffix
        self._store: Dict[str, Tuple[str, Optional[float]]] = {}
        self._mailboxes: Dict[str, asyncio.Queue[Any]] = {}
        self._lock = asyncio.Lock()

    def _ns(self, key: str) -> str:
        return f"{self._prefix}{key}{self._suffix}"

    def _now(self) -> float:
        return time.time()

    def _is_expired(self, exp: Optional[float]) -> bool:
        return exp is not None and self._now() >= exp

    async def get(self, key: str) -> Optional[Any]:
        nkey = self._ns(key)
        async with self._lock:
            item = self._store.get(nkey)
            if item is None:
                return None
            raw, exp = item
            if self._is_expired(exp):
                self._store.pop(nkey, None)
                return None
        try:
            return json.loads(raw)
        except Exception as e:
            raise CacheError(f"Failed to deserialize cache value for key={key}") from e

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        nkey = self._ns(key)
        try:
            raw = json.dumps(value)
        except Exception as e:
            raise CacheError(f"Failed to serialize cache value for key={key}") from e
        exp: Optional[float] = None
        if ttl_seconds is not None:
            if ttl_seconds <= 0:
                raise ValidationError("ttl_seconds must be positive")
            exp = self._now() + ttl_seconds
        async with self._lock:
            self._store[nkey] = (raw, exp)

    async def delete(self, key: str) -> None:
        nkey = self._ns(key)
        async with self._lock:
            self._store.pop(nkey, None)

    async def get_all(self, keys: Sequence[str]) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        for k in keys:
            v = await self.get(k)
            if v is not None:
                results[k] = v
        return results

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    def mailbox(self, name: str) -> Mailbox:
        n = self._ns(f"mailbox:{name}")
        q = self._mailboxes.get(n)
        if q is None:
            q = asyncio.Queue()
            self._mailboxes[n] = q
        return _InMemoryMailbox(q)


@dataclass
class InferenceRequest:
    messages: List[InferenceMessage]
    model: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    stream: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def cache_key(self, provider: str) -> str:
        payload = {
            "provider": provider,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "tools": self.tools,
            "tool_choice": self.tool_choice,
            "messages": [m.to_json() for m in self.messages],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"inference:{uuid.uuid5(uuid.NAMESPACE_URL, raw)}"


class InferenceClient(abc.ABC):
    def __init__(
        self,
        provider: str,
        *,
        cache: Optional[Cache] = None,
        tracer: Optional[TelemetryTracer] = None,
        enable_prompt_cache: bool = True,
        default_ttl_seconds: int = 3600,
    ) -> None:
        if not provider:
            raise ValidationError("provider must be non-empty")
        if default_ttl_seconds <= 0:
            raise ValidationError("default_ttl_seconds must be positive")
        self._provider = provider
        self._cache = cache
        self._tracer = tracer or NoopTracer()
        self._enable_prompt_cache = enable_prompt_cache
        self._default_ttl_seconds = default_ttl_seconds

    @property
    def provider(self) -> str:
        return self._provider

    @abc.abstractmethod
    async def complete(self, request: InferenceRequest) -> InferenceResponse:
        raise NotImplementedError

    @abc.abstractmethod
    async def stream(self, request: InferenceRequest) -> AsyncIterator[InferenceChunk]:
        raise NotImplementedError

    async def _get_cached(self, request: InferenceRequest) -> Optional[InferenceResponse]:
        if not self._enable_prompt_cache or self._cache is None:
            return None
        key = request.cache_key(self._provider)
        cached = await self._cache.get(key)
        if cached is None:
            return None
        try:
            msg = InferenceMessage.from_json(cached["message"])
            usage = TokenUsage(
                prompt_tokens=int(cached.get("usage", {}).get("prompt_tokens", 0)),
                completion_tokens=int(cached.get("usage", {}).get("completion_tokens", 0)),
            )
            return InferenceResponse(
                message=msg,
                usage=usage,
                provider=str(cached.get("provider", self._provider)),
                model=str(cached.get("model", request.model)),
                cached=True,
                raw=dict(cached.get("raw", {}) or {}),
            )
        except Exception as e:
            raise CacheError("Invalid cached inference response format") from e

    async def _set_cached(self, request: InferenceRequest, response: InferenceResponse) -> None:
        if not self._enable_prompt_cache or self._cache is None:
            return
        key = request.cache_key(self._provider)
        payload = {
            "message": response.message.to_json(),
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
            "provider": response.provider or self._provider,
            "model": response.model or request.model,
            "raw": response.raw,
        }
        await self._cache.set(key, payload, ttl_seconds=self._default_ttl_seconds)


class EchoInferenceClient(InferenceClient):
    def __init__(
        self,
        *,
        provider: str = "echo",
        cache: Optional[Cache] = None,
        tracer: Optional[TelemetryTracer] = None,
        enable_prompt_cache: bool = True,
        default_ttl_seconds: int = 3600,
    ) -> None:
        super().__init__(
            provider,
            cache=cache,
            tracer=tracer,
            enable_prompt_cache=enable_prompt_cache,
            default_ttl_seconds=default_ttl_seconds,
        )

    def _estimate_tokens(self, text: str) -> int:
        text = text.strip()
        if not text:
            return 0
        return max(1, len(text) // 4)

    async def complete(self, request: InferenceRequest) -> InferenceResponse:
        if request.stream:
            raise ValidationError("Use stream() for streaming requests")
        span = self._tracer.start_span(
            "inference.complete",
            attributes={"provider": self.provider, "model": request.model},
        )
        try:
            cached = await self._get_cached(request)
            if cached is not None:
                span.set_attribute("cached", True)
                return cached

            content = request.messages[-1].content if request.messages else ""
            msg = InferenceMessage(role="assistant", content=content)
            usage = TokenUsage(
                prompt_tokens=sum(self._estimate_tokens(m.content) for m in request.messages),
                completion_tokens=self._estimate_tokens(content),
            )
            resp = InferenceResponse(
                message=msg,
                usage=usage,
                provider=self.provider,
                model=request.model,
                cached=False,
                raw={"echo": True},
            )
            await self._set_cached(request, resp)
            span.set_attribute("cached", False)
            span.set_attribute("usage.total_tokens", resp.usage.total_tokens)
            return resp
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()

    async def stream(self, request: InferenceRequest) -> AsyncIterator[InferenceChunk]:
        if not request.stream:
            raise ValidationError("Request must set stream=True for stream()")
        span = self._tracer.start_span(
            "inference.stream",
            attributes={"provider": self.provider, "model": request.model},
        )
        try:
            cached = await self._get_cached(request)
            if cached is not None:
                span.set_attribute("cached", True)
                yield InferenceChunk(
                    content_delta=cached.message.content,
                    usage_delta=cached.usage,
                    is_final=True,
                )
                return

            content = request.messages[-1].content if request.messages else ""
            usage = TokenUsage(
                prompt_tokens=sum(self._estimate_tokens(m.content) for m in request.messages),
                completion_tokens=self._estimate_tokens(content),
            )
            for ch in content:
                yield InferenceChunk(content_delta=ch, usage_delta=TokenUsage(), is_final=False)
                await asyncio.sleep(0)
            yield InferenceChunk(content_delta="", usage_delta=usage, is_final=True)

            resp = InferenceResponse(
                message=InferenceMessage(role="assistant", content=content),
                usage=usage,
                provider=self.provider,
                model=request.model,
                cached=False,
                raw={"echo": True},
            )
            await self._set_cached(request, resp)
            span.set_attribute("cached", False)
            span.set_attribute("usage.total_tokens", usage.total_tokens)
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()


class Tool(Protocol):
    name: str

    async def __call__(self, arguments: Dict[str, Any], ctx: "ExecutionContext") -> Any: ...


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        name = getattr(tool, "name", None)
        if not isinstance(name, str) or not name:
            raise ValidationError("Tool must have a non-empty 'name' attribute")
        if name in self._tools:
            raise ValidationError(f"Tool already registered: {name}")
        self._tools[name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ValidationError(f"Tool not found: {name}")
        return self._tools[name]

    def list(self) -> List[str]:
        return sorted(self._tools.keys())


@dataclass
class NodeResult:
    node_id: str
    output: Any = None
    started_at: float = 0.0
    ended_at: float = 0.0
    error: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        if self.started_at <= 0 or self.ended_at <= 0:
            return 0.0
        return max(0.0, self.ended_at - self.started_at)


class Node(abc.ABC):
    def __init__(self, node_id: str, *, name: Optional[str] = None) -> None:
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
    async def run(self, ctx: "ExecutionContext") -> Any:
        raise NotImplementedError


class FunctionNode(Node):
    def __init__(
        self,
        node_id: str,
        func: Callable[["ExecutionContext"], Awaitable[Any]],
        *,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(node_id, name=name)
        if not callable(func):
            raise ValidationError("func must be callable")
        self._func = func

    async def run(self, ctx: "ExecutionContext") -> Any:
        return await self._func(ctx)


class InferenceNode(Node):
    def __init__(
        self,
        node_id: str,
        client: InferenceClient,
        request_builder: Callable[["ExecutionContext"], InferenceRequest],
        *,
        name: Optional[str] = None,
        output_key: Optional[str] = None,
    ) -> None:
        super().__init__(node_id, name=name)
        self._client = client
        self._request_builder = request_builder
        self._output_key = output_key

    async def run(self, ctx: "ExecutionContext") -> Any:
        req = self._request_builder(ctx)
        if not isinstance(req, InferenceRequest):
            raise ValidationError("request_builder must return an InferenceRequest")
        if req.stream:
            content_parts: List[str] = []
            usage = TokenUsage()
            async for chunk in self._client.stream(req):
                if chunk.content_delta:
                    content_parts.append(chunk.content_delta)
                if chunk.is_final:
                    usage = TokenUsage(
                        prompt_tokens=usage.prompt_tokens + chunk.usage_delta.prompt_tokens,
                        completion_tokens=usage.completion_tokens + chunk.usage_delta.completion_tokens,
                    )
            msg = InferenceMessage(role="assistant", content="".join(content_parts))
            resp = InferenceResponse(message=msg, usage=usage, provider=self._client.provider, model=req.model)
        else:
            resp = await self._client.complete(req)

        if self._output_key:
            ctx.state[self._output_key] = resp
        return resp


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str


class Graph:
    def __init__(self, graph_id: str) -> None:
        if not graph_id:
            raise ValidationError("graph_id must be non-empty")
        self._id = graph_id
        self._nodes: Dict[str, Node] = {}
        self._deps: Dict[str, set[str]] = {}
        self._outs: Dict[str, set[str]] = {}

    @property
    def id(self) -> str:
        return self._id

    def add_node(self, node: Node) -> None:
        if node.id in self._nodes:
            raise ValidationError(f"Duplicate node id: {node.id}")
        self._nodes[node.id] = node
        self._deps.setdefault(node.id, set())
        self._outs.setdefault(node.id, set())

    def add_edge(self, src: str, dst: str) -> None:
        if src not in self._nodes:
            raise ValidationError(f"Unknown src node: {src}")
        if dst not in self._nodes:
            raise ValidationError(f"Unknown dst node: {dst}")
        if src == dst:
            raise ValidationError("Self edges are not allowed")
        self._deps.setdefault(dst, set()).add(src)
        self._outs.setdefault(src, set()).add(dst)

    def node(self, node_id: str) -> Node:
        if node_id not in self._nodes:
            raise ValidationError(f"Unknown node: {node_id}")
        return self._nodes[node_id]

    def nodes(self) -> List[Node]:
        return list(self._nodes.values())

    def dependencies_of(self, node_id: str) -> List[str]:
        if node_id not in self._nodes:
            raise ValidationError(f"Unknown node: {node_id}")
        return sorted(self._deps.get(node_id, set()))

    def dependents_of(self, node_id: str) -> List[str]:
        if node_id not in self._nodes:
            raise ValidationError(f"Unknown node: {node_id}")
        return sorted(self._outs.get(node_id, set()))

    def validate_acyclic(self) -> None:
        temp: set[str] = set()
        perm: set[str] = set()

        def visit(n: str) -> None:
            if n in perm:
                return
            if n in temp:
                raise ValidationError("Graph contains a cycle")
            temp.add(n)
            for m in self._outs.get(n, set()):
                visit(m)
            temp.remove(n)
            perm.add(n)

        for nid in self._nodes.keys():
            visit(nid)

    def roots(self) -> List[str]:
        return sorted([nid for nid in self._nodes.keys() if len(self._deps.get(nid, set())) == 0])


@dataclass
class ExecutionContext:
    graph: Graph
    run_id: str
    state: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, NodeResult] = field(default_factory=dict)
    tracer: TelemetryTracer = field(default_factory=NoopTracer)
    cache: Optional[Cache] = None
    tool_registry: ToolRegistry = field(default_factory=ToolRegistry)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> Snapshot:
        completed = [nid for nid, r in self.results.items() if r.error is None and r.ended_at > 0]
        pending = [n.id for n in self.graph.nodes() if n.id not in completed]
        return Snapshot(
            snapshot_id=str(uuid.uuid4()),
            created_at=time.time(),
            graph_id=self.graph.id,
            run_id=self.run_id,
            state=json.loads(json.dumps(self.state, default=str)),
            completed_nodes=sorted(completed),
            pending_nodes=sorted(pending),
            metadata=json.loads(json.dumps(self.metadata, default=str)),
        )


class GraphEngine:
    def __init__(
        self,
        *,
        tracer: Optional[TelemetryTracer] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        snapshot_store: Optional[SnapshotStore] = None,
        snapshot_every_n_nodes: Optional[int] = None,
    ) -> None:
        if snapshot_every_n_nodes is not None and snapshot_every_n_nodes <= 0:
            raise ValidationError("snapshot_every_n_nodes must be positive")
        self._tracer = tracer or NoopTracer()
        self._middleware = list(middleware or [])
        self._snapshot_store = snapshot_store
        self._snapshot_every_n_nodes = snapshot_every_n_nodes

    async def run(
        self,
        graph: Graph,
        *,
        initial_state: Optional[Dict[str, Any]] = None,
        cache: Optional[Cache] = None,
        tool_registry: Optional[ToolRegistry] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionContext:
        graph.validate_acyclic()
        rid = run_id or str(uuid.uuid4())
        ctx = ExecutionContext(
            graph=graph,
            run_id=rid,
            state=dict(initial_state or {}),
            tracer=self._tracer,
            cache=cache,
            tool_registry=tool_registry or ToolRegistry(),
            metadata=dict(metadata or {}),
        )

        span = self._tracer.start_span("graph.run", attributes={"graph_id": graph.id, "run_id": rid})
        try:
            await self._execute(ctx)
            return ctx
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()

    async def resume_from_snapshot(
        self,
        graph: Graph,
        snapshot: Snapshot,
        *,
        cache: Optional[Cache] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> ExecutionContext:
        if snapshot.graph_id != graph.id:
            raise ValidationError("Snapshot graph_id does not match graph.id")
        graph.validate_acyclic()
        ctx = ExecutionContext(
            graph=graph,
            run_id=snapshot.run_id,
            state=dict(snapshot.state),
            tracer=self._tracer,
            cache=cache,
            tool_registry=tool_registry or ToolRegistry(),
            metadata=dict(snapshot.metadata),
        )
        for nid in snapshot.completed_nodes:
            ctx.results[nid] = NodeResult(node_id=nid, output=None, started_at=0.0, ended_at=time.time(), error=None)

        span = self._tracer.start_span(
            "graph.resume",
            attributes={"graph_id": graph.id, "run_id": snapshot.run_id, "snapshot_id": snapshot.snapshot_id},
        )
        try:
            await self._execute(ctx)
            return ctx
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()

    async def _execute(self, ctx: ExecutionContext) -> None:
        completed: set[str] = set(nid for nid, r in ctx.results.items() if r.error is None and r.ended_at > 0)
        total_executed = 0

        while True:
            ready = self._ready_nodes(ctx.graph, completed)
            if not ready:
                remaining = [n.id for n in ctx.graph.nodes() if n.id not in completed]
                if not remaining:
                    return
                raise ExecutionError("No executable nodes found; graph may be blocked by missing dependencies")

            for node_id in ready:
                if node_id in completed:
                    continue
                node = ctx.graph.node(node_id)
                node_span = ctx.tracer.start_span(
                    "graph.node",
                    attributes={"graph_id": ctx.graph.id, "run_id": ctx.run_id, "node_id": node.id, "node_name": node.name},
                )
                started = time.time()
                result = NodeResult(node_id=node.id, started_at=started)
                ctx.results[node.id] = result
                try:
                    for mw in self._middleware:
                        await mw.before_node(ctx, node)

                    out = await node.run(ctx)

                    result.output = out
                    result.ended_at = time.time()
                    result.error = None
                    completed.add(node.id)

                    for mw in reversed(self._middleware):
                        await mw.after_node(ctx, node, out)

                    node_span.set_attribute("duration_seconds", result.duration_seconds)
                except BaseException as e:
                    result.ended_at = time.time()
                    result.error = f"{type(e).__name__}: {e}"
                    try:
                        for mw in reversed(self._middleware):
                            await mw.on_error(ctx, node, e)
                    finally:
                        node_span.record_exception(e)
                        node_span.end()
                    raise
                finally:
                    if result.error is None:
                        node_span.end()

                total_executed += 1
                if (
                    self._snapshot_store is not None
                    and self._snapshot_every_n_nodes is not None
                    and total_executed % self._snapshot_every_n_nodes == 0
                ):
                    snap = ctx.snapshot()
                    await self._snapshot_store.save(snap)

    def _ready_nodes(self, graph: Graph, completed: set[str]) -> List[str]:
        ready: List[str] = []
        for node in graph.nodes():
            if node.id in completed:
                continue
            deps = graph.dependencies_of(node.id)
            if all(d in completed for d in deps):
                ready.append(node.id)
        ready.sort()
        return ready


class LLMDirectedGraphExecutor:
    def __init__(
        self,
        client: InferenceClient,
        *,
        tracer: Optional[TelemetryTracer] = None,
        max_steps: int = 50,
    ) -> None:
        if max_steps <= 0:
            raise ValidationError("max_steps must be positive")
        self._client = client
        self._tracer = tracer or NoopTracer()
        self._max_steps = max_steps

    async def run(
        self,
        graph: Graph,
        *,
        start_node_id: str,
        ctx: ExecutionContext,
        prompt_builder: Callable[[ExecutionContext, str, List[str]], InferenceRequest],
        parse_next_node: Callable[[InferenceResponse, List[str]], str],
    ) -> ExecutionContext:
        graph.validate_acyclic()
        if start_node_id not in [n.id for n in graph.nodes()]:
            raise ValidationError(f"Unknown start_node_id: {start_node_id}")

        span = self._tracer.start_span(
            "graph.llm_directed_run",
            attributes={"graph_id": graph.id, "run_id": ctx.run_id, "start_node_id": start_node_id},
        )
        try:
            current = start_node_id
            completed: set[str] = set(nid for nid, r in ctx.results.items() if r.error is None and r.ended_at > 0)
            steps = 0

            while steps < self._max_steps:
                steps += 1
                if current in completed:
                    candidates = graph.dependents_of(current)
                else:
                    candidates = [current]

                if not candidates:
                    return ctx

                if len(candidates) == 1 and candidates[0] == current and current not in completed:
                    node = graph.node(current)
                    node_span = ctx.tracer.start_span(
                        "graph.node",
                        attributes={"graph_id": graph.id, "run_id": ctx.run_id, "node_id": node.id, "node_name": node.name},
                    )
                    started = time.time()
                    result = NodeResult(node_id=node.id, started_at=started)
                    ctx.results[node.id] = result
                    try:
                        out = await node.run(ctx)
                        result.output = out
                        result.ended_at = time.time()
                        completed.add(node.id)
                        node_span.set_attribute("duration_seconds", result.duration_seconds)
                    except BaseException as e:
                        result.ended_at = time.time()
                        result.error = f"{type(e).__name__}: {e}"
                        node_span.record_exception(e)
                        raise
                    finally:
                        node_span.end()
                    continue

                ready = [nid for nid in candidates if all(d in completed for d in graph.dependencies_of(nid))]
                if not ready:
                    return ctx

                req = prompt_builder(ctx, current, ready)
                if not isinstance(req, InferenceRequest):
                    raise ValidationError("prompt_builder must return an InferenceRequest")
                req.stream = False
                resp = await self._client.complete(req)
                next_node = parse_next_node(resp, ready)
                if next_node not in ready:
                    raise ValidationError("parse_next_node must return one of the provided candidate node ids")
                current = next_node

            raise ExecutionError("LLM-directed execution exceeded max_steps")
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()