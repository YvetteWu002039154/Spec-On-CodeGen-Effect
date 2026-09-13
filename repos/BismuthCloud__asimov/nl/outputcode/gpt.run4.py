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

JSONPrimitive = Union[str, int, float, bool, None]
JSONValue = Union[JSONPrimitive, Dict[str, "JSONValue"], List["JSONValue"]]


class FrameworkError(Exception):
    pass


class ValidationError(FrameworkError):
    pass


class GraphExecutionError(FrameworkError):
    pass


class CacheError(FrameworkError):
    pass


class InferenceError(FrameworkError):
    pass


def _now_ms() -> int:
    return int(time.time() * 1000)


def _stable_json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return int(self.prompt_tokens) + int(self.completion_tokens)

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
class InferenceChunk:
    text: str = ""
    tool_calls: Tuple[ToolCall, ...] = ()
    usage: TokenUsage = field(default_factory=TokenUsage)
    finish_reason: Optional[str] = None


@dataclass(frozen=True)
class InferenceResult:
    text: str
    tool_calls: Tuple[ToolCall, ...] = ()
    usage: TokenUsage = field(default_factory=TokenUsage)
    raw: Any = None


class Middleware(Protocol):
    async def before_node(self, ctx: "ExecutionContext", node: "Node") -> None: ...
    async def after_node(self, ctx: "ExecutionContext", node: "Node", result: Any) -> None: ...
    async def on_error(self, ctx: "ExecutionContext", node: "Node", error: BaseException) -> None: ...


class NoopMiddleware:
    async def before_node(self, ctx: "ExecutionContext", node: "Node") -> None:
        return None

    async def after_node(self, ctx: "ExecutionContext", node: "Node", result: Any) -> None:
        return None

    async def on_error(self, ctx: "ExecutionContext", node: "Node", error: BaseException) -> None:
        return None


class Tracer(Protocol):
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> "Span": ...


class Span(Protocol):
    def set_attribute(self, key: str, value: Any) -> None: ...
    def record_exception(self, exc: BaseException) -> None: ...
    def end(self) -> None: ...


class NoopSpan:
    def set_attribute(self, key: str, value: Any) -> None:
        return None

    def record_exception(self, exc: BaseException) -> None:
        return None

    def end(self) -> None:
        return None


class NoopTracer:
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Span:
        return NoopSpan()


@dataclass(frozen=True)
class StateSnapshot:
    snapshot_id: str
    created_at_ms: int
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


class ExecutionContext:
    def __init__(
        self,
        *,
        initial_state: Optional[Dict[str, Any]] = None,
        tracer: Optional[Tracer] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        snapshotting: bool = True,
    ) -> None:
        self._state: Dict[str, Any] = dict(initial_state or {})
        self._tracer: Tracer = tracer or NoopTracer()
        self._middleware: Tuple[Middleware, ...] = tuple(middleware or (NoopMiddleware(),))
        self._snapshotting: bool = bool(snapshotting)
        self._snapshots = SnapshotStore()
        self._node_results: Dict[str, Any] = {}
        self._node_errors: Dict[str, str] = {}
        self._usage: TokenUsage = TokenUsage()

    @property
    def state(self) -> Dict[str, Any]:
        return self._state

    @property
    def tracer(self) -> Tracer:
        return self._tracer

    @property
    def middleware(self) -> Tuple[Middleware, ...]:
        return self._middleware

    @property
    def snapshots(self) -> SnapshotStore:
        return self._snapshots

    @property
    def node_results(self) -> Dict[str, Any]:
        return self._node_results

    @property
    def node_errors(self) -> Dict[str, str]:
        return self._node_errors

    @property
    def usage(self) -> TokenUsage:
        return self._usage

    def add_usage(self, usage: TokenUsage) -> None:
        self._usage = self._usage + usage

    def set_result(self, node_id: str, result: Any) -> None:
        self._node_results[node_id] = result

    def set_error(self, node_id: str, error: BaseException) -> None:
        self._node_errors[node_id] = f"{type(error).__name__}: {error}"

    def snapshot(self, *, metadata: Optional[Dict[str, Any]] = None) -> Optional[StateSnapshot]:
        if not self._snapshotting:
            return None
        snap = StateSnapshot(
            snapshot_id=str(uuid.uuid4()),
            created_at_ms=_now_ms(),
            state=json.loads(_stable_json_dumps(self._state)),
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


class Graph:
    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        self._edges_out: Dict[str, Set[str]] = defaultdict(set)
        self._edges_in: Dict[str, Set[str]] = defaultdict(set)

    @property
    def nodes(self) -> Dict[str, Node]:
        return dict(self._nodes)

    def add_node(self, node: Node) -> None:
        if node.id in self._nodes:
            raise ValidationError(f"Duplicate node id: {node.id}")
        self._nodes[node.id] = node
        _ = self._edges_out[node.id]
        _ = self._edges_in[node.id]

    def add_edge(self, from_node_id: str, to_node_id: str) -> None:
        if from_node_id not in self._nodes or to_node_id not in self._nodes:
            raise ValidationError("Both nodes must be added before creating an edge")
        if from_node_id == to_node_id:
            raise ValidationError("Self edges are not allowed")
        self._edges_out[from_node_id].add(to_node_id)
        self._edges_in[to_node_id].add(from_node_id)

    def predecessors(self, node_id: str) -> Set[str]:
        if node_id not in self._nodes:
            raise ValidationError(f"Unknown node: {node_id}")
        return set(self._edges_in[node_id])

    def successors(self, node_id: str) -> Set[str]:
        if node_id not in self._nodes:
            raise ValidationError(f"Unknown node: {node_id}")
        return set(self._edges_out[node_id])

    def validate_acyclic(self) -> None:
        indeg: Dict[str, int] = {nid: len(self._edges_in[nid]) for nid in self._nodes}
        q: Deque[str] = deque([nid for nid, d in indeg.items() if d == 0])
        visited = 0
        while q:
            n = q.popleft()
            visited += 1
            for s in self._edges_out[n]:
                indeg[s] -= 1
                if indeg[s] == 0:
                    q.append(s)
        if visited != len(self._nodes):
            raise ValidationError("Graph contains a cycle")

    def topological_order(self) -> List[str]:
        self.validate_acyclic()
        indeg: Dict[str, int] = {nid: len(self._edges_in[nid]) for nid in self._nodes}
        q: Deque[str] = deque([nid for nid, d in indeg.items() if d == 0])
        order: List[str] = []
        while q:
            n = q.popleft()
            order.append(n)
            for s in sorted(self._edges_out[n]):
                indeg[s] -= 1
                if indeg[s] == 0:
                    q.append(s)
        return order


class GraphExecutionEngine:
    def __init__(
        self,
        graph: Graph,
        *,
        tracer: Optional[Tracer] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        snapshotting: bool = True,
    ) -> None:
        self._graph = graph
        self._tracer = tracer or NoopTracer()
        self._middleware = tuple(middleware or (NoopMiddleware(),))
        self._snapshotting = bool(snapshotting)

    @property
    def graph(self) -> Graph:
        return self._graph

    async def run(
        self,
        *,
        initial_state: Optional[Dict[str, Any]] = None,
    ) -> ExecutionContext:
        ctx = ExecutionContext(
            initial_state=initial_state,
            tracer=self._tracer,
            middleware=self._middleware,
            snapshotting=self._snapshotting,
        )
        order = self._graph.topological_order()
        for node_id in order:
            node = self._graph.nodes[node_id]
            span = ctx.tracer.start_span("graph.node", {"node.id": node.id, "node.name": node.name})
            try:
                for mw in ctx.middleware:
                    await mw.before_node(ctx, node)
                ctx.snapshot(metadata={"event": "before_node", "node_id": node.id})
                result = await node.run(ctx)
                ctx.set_result(node.id, result)
                ctx.snapshot(metadata={"event": "after_node", "node_id": node.id})
                for mw in ctx.middleware:
                    await mw.after_node(ctx, node, result)
                span.set_attribute("node.status", "ok")
            except BaseException as e:
                ctx.set_error(node.id, e)
                for mw in ctx.middleware:
                    try:
                        await mw.on_error(ctx, node, e)
                    except BaseException:
                        pass
                span.set_attribute("node.status", "error")
                span.record_exception(e)
                span.end()
                raise GraphExecutionError(f"Node {node.id} failed: {type(e).__name__}: {e}") from e
            finally:
                try:
                    span.end()
                except BaseException:
                    pass
        return ctx


class Cache(abc.ABC):
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
    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    async def publish(self, message: Any) -> None:
        async with self._lock:
            for q in list(self._subscribers):
                try:
                    q.put_nowait(message)
                except asyncio.QueueFull:
                    pass

    async def subscribe(self) -> AsyncGenerator[Any, None]:
        q: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(q)
        try:
            while True:
                msg = await q.get()
                yield msg
        finally:
            async with self._lock:
                self._subscribers.discard(q)


class RedisCache(Cache):
    def __init__(
        self,
        *,
        prefix: str = "",
        suffix: str = "",
    ) -> None:
        self._prefix = prefix
        self._suffix = suffix
        self._store: Dict[str, Tuple[str, Optional[int]]] = {}
        self._lock = asyncio.Lock()
        self._mailboxes: Dict[str, _InMemoryMailbox] = {}

    def _ns(self, key: str) -> str:
        if not isinstance(key, str) or not key:
            raise ValidationError("key must be a non-empty string")
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
        try:
            return json.loads(payload)
        except Exception as e:
            raise CacheError(f"Failed to deserialize cached value for key={key}") from e

    async def set(self, key: str, value: Any, *, ttl_seconds: Optional[int] = None) -> None:
        k = self._ns(key)
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValidationError("ttl_seconds must be positive when provided")
        try:
            payload = _stable_json_dumps(value)
        except Exception as e:
            raise CacheError("Failed to serialize value to JSON") from e
        expires_at_ms = None
        if ttl_seconds is not None:
            expires_at_ms = _now_ms() + int(ttl_seconds * 1000)
        async with self._lock:
            self._store[k] = (payload, expires_at_ms)

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
            self._store.clear()

    def mailbox(self, name: str) -> Mailbox:
        if not isinstance(name, str) or not name:
            raise ValidationError("mailbox name must be a non-empty string")
        if name not in self._mailboxes:
            self._mailboxes[name] = _InMemoryMailbox()
        return self._mailboxes[name]


@dataclass(frozen=True)
class Prompt:
    messages: Tuple[Dict[str, Any], ...]
    model: str
    temperature: Optional[float] = None
    tools: Tuple[Dict[str, Any], ...] = ()
    tool_choice: Optional[Dict[str, Any]] = None

    def cache_key(self) -> str:
        payload = {
            "messages": self.messages,
            "model": self.model,
            "temperature": self.temperature,
            "tools": self.tools,
            "tool_choice": self.tool_choice,
        }
        return _hash_text(_stable_json_dumps(payload))


class InferenceClient(abc.ABC):
    def __init__(
        self,
        *,
        tracer: Optional[Tracer] = None,
        cache: Optional[Cache] = None,
        cache_prefix: str = "prompt:",
    ) -> None:
        self._tracer = tracer or NoopTracer()
        self._cache = cache
        self._cache_prefix = cache_prefix

    @property
    def tracer(self) -> Tracer:
        return self._tracer

    @property
    def cache(self) -> Optional[Cache]:
        return self._cache

    def _cache_key(self, prompt: Prompt) -> str:
        return f"{self._cache_prefix}{prompt.cache_key()}"

    async def infer(self, prompt: Prompt, *, use_cache: bool = True) -> InferenceResult:
        span = self.tracer.start_span("inference.infer", {"model": prompt.model})
        try:
            if use_cache and self._cache is not None:
                cached = await self._cache.get(self._cache_key(prompt))
                if cached is not None:
                    try:
                        res = InferenceResult(
                            text=str(cached.get("text", "")),
                            tool_calls=tuple(
                                ToolCall(
                                    name=tc["name"],
                                    arguments=dict(tc.get("arguments", {})),
                                    call_id=str(tc.get("call_id", str(uuid.uuid4()))),
                                )
                                for tc in cached.get("tool_calls", []) or []
                            ),
                            usage=TokenUsage(
                                prompt_tokens=int((cached.get("usage") or {}).get("prompt_tokens", 0)),
                                completion_tokens=int((cached.get("usage") or {}).get("completion_tokens", 0)),
                            ),
                            raw=cached.get("raw"),
                        )
                        span.set_attribute("cache.hit", True)
                        return res
                    except Exception:
                        pass
            span.set_attribute("cache.hit", False)
            result = await self._infer_impl(prompt)
            if self._cache is not None and use_cache:
                await self._cache.set(
                    self._cache_key(prompt),
                    {
                        "text": result.text,
                        "tool_calls": [
                            {"name": tc.name, "arguments": tc.arguments, "call_id": tc.call_id}
                            for tc in result.tool_calls
                        ],
                        "usage": {
                            "prompt_tokens": result.usage.prompt_tokens,
                            "completion_tokens": result.usage.completion_tokens,
                        },
                        "raw": result.raw,
                    },
                )
            return result
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()

    async def stream(self, prompt: Prompt) -> AsyncGenerator[InferenceChunk, None]:
        span = self.tracer.start_span("inference.stream", {"model": prompt.model})
        try:
            async for chunk in self._stream_impl(prompt):
                yield chunk
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()

    @abc.abstractmethod
    async def _infer_impl(self, prompt: Prompt) -> InferenceResult:
        raise NotImplementedError

    @abc.abstractmethod
    async def _stream_impl(self, prompt: Prompt) -> AsyncGenerator[InferenceChunk, None]:
        raise NotImplementedError


class MockInferenceClient(InferenceClient):
    def __init__(
        self,
        *,
        tracer: Optional[Tracer] = None,
        cache: Optional[Cache] = None,
        cache_prefix: str = "prompt:",
        response_text: str = "OK",
        tool_calls: Optional[Sequence[ToolCall]] = None,
        usage: Optional[TokenUsage] = None,
    ) -> None:
        super().__init__(tracer=tracer, cache=cache, cache_prefix=cache_prefix)
        self._response_text = response_text
        self._tool_calls = tuple(tool_calls or ())
        self._usage = usage or TokenUsage()

    async def _infer_impl(self, prompt: Prompt) -> InferenceResult:
        _ = prompt
        return InferenceResult(text=self._response_text, tool_calls=self._tool_calls, usage=self._usage, raw=None)

    async def _stream_impl(self, prompt: Prompt) -> AsyncGenerator[InferenceChunk, None]:
        _ = prompt
        text = self._response_text
        if not text:
            yield InferenceChunk(text="", tool_calls=self._tool_calls, usage=self._usage, finish_reason="stop")
            return
        for i in range(len(text)):
            yield InferenceChunk(text=text[i : i + 1], tool_calls=(), usage=TokenUsage(), finish_reason=None)
            await asyncio.sleep(0)
        yield InferenceChunk(text="", tool_calls=self._tool_calls, usage=self._usage, finish_reason="stop")


class LLMDirectedGraphExecutor:
    def __init__(
        self,
        graph: Graph,
        inference_client: InferenceClient,
        *,
        tracer: Optional[Tracer] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        snapshotting: bool = True,
    ) -> None:
        self._graph = graph
        self._client = inference_client
        self._tracer = tracer or NoopTracer()
        self._middleware = tuple(middleware or (NoopMiddleware(),))
        self._snapshotting = bool(snapshotting)

    @property
    def graph(self) -> Graph:
        return self._graph

    @property
    def inference_client(self) -> InferenceClient:
        return self._client

    async def run(
        self,
        *,
        initial_state: Optional[Dict[str, Any]] = None,
        planner_prompt: Prompt,
        max_steps: Optional[int] = None,
    ) -> ExecutionContext:
        if max_steps is not None and max_steps <= 0:
            raise ValidationError("max_steps must be positive when provided")

        ctx = ExecutionContext(
            initial_state=initial_state,
            tracer=self._tracer,
            middleware=self._middleware,
            snapshotting=self._snapshotting,
        )

        remaining: Set[str] = set(self._graph.nodes.keys())
        completed: Set[str] = set()
        steps = 0

        self._graph.validate_acyclic()

        while remaining:
            if max_steps is not None and steps >= max_steps:
                raise GraphExecutionError("LLM-directed execution exceeded max_steps")
            steps += 1

            ready = sorted([nid for nid in remaining if self._graph.predecessors(nid).issubset(completed)])
            if not ready:
                raise GraphExecutionError("No executable nodes available (possible cycle or missing dependencies)")

            plan_span = ctx.tracer.start_span("graph.plan", {"ready.count": len(ready)})
            try:
                plan_state = {
                    "ready_nodes": [{"id": nid, "name": self._graph.nodes[nid].name} for nid in ready],
                    "completed_nodes": sorted(list(completed)),
                    "remaining_nodes": sorted(list(remaining)),
                    "state": ctx.state,
                }
                plan_prompt = Prompt(
                    messages=planner_prompt.messages
                    + (
                        {
                            "role": "user",
                            "content": _stable_json_dumps(plan_state),
                        },
                    ),
                    model=planner_prompt.model,
                    temperature=planner_prompt.temperature,
                    tools=planner_prompt.tools,
                    tool_choice=planner_prompt.tool_choice,
                )
                plan_result = await self._client.infer(plan_prompt, use_cache=True)
                ctx.add_usage(plan_result.usage)

                chosen_id = self._select_node_id_from_plan(plan_result.text, ready)
                plan_span.set_attribute("chosen.node_id", chosen_id)
            except BaseException as e:
                plan_span.record_exception(e)
                raise
            finally:
                plan_span.end()

            node = self._graph.nodes[chosen_id]
            span = ctx.tracer.start_span("graph.node", {"node.id": node.id, "node.name": node.name})
            try:
                for mw in ctx.middleware:
                    await mw.before_node(ctx, node)
                ctx.snapshot(metadata={"event": "before_node", "node_id": node.id})
                result = await node.run(ctx)
                ctx.set_result(node.id, result)
                ctx.snapshot(metadata={"event": "after_node", "node_id": node.id})
                for mw in ctx.middleware:
                    await mw.after_node(ctx, node, result)
                completed.add(node.id)
                remaining.discard(node.id)
                span.set_attribute("node.status", "ok")
            except BaseException as e:
                ctx.set_error(node.id, e)
                for mw in ctx.middleware:
                    try:
                        await mw.on_error(ctx, node, e)
                    except BaseException:
                        pass
                span.set_attribute("node.status", "error")
                span.record_exception(e)
                span.end()
                raise GraphExecutionError(f"Node {node.id} failed: {type(e).__name__}: {e}") from e
            finally:
                try:
                    span.end()
                except BaseException:
                    pass

        return ctx

    def _select_node_id_from_plan(self, plan_text: str, ready: Sequence[str]) -> str:
        if not ready:
            raise GraphExecutionError("No ready nodes to select from")
        text = (plan_text or "").strip()
        if not text:
            return ready[0]

        # Accept either raw node id, or JSON like {"node_id": "..."} or {"id": "..."}
        if text in ready:
            return text
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                cand = obj.get("node_id") or obj.get("id") or obj.get("node")
                if isinstance(cand, str) and cand in ready:
                    return cand
        except Exception:
            pass

        # Fallback: find first ready id mentioned in text
        for nid in ready:
            if nid in text:
                return nid
        return ready[0]


__all__ = [
    "FrameworkError",
    "ValidationError",
    "GraphExecutionError",
    "CacheError",
    "InferenceError",
    "TokenUsage",
    "ToolCall",
    "InferenceChunk",
    "InferenceResult",
    "Middleware",
    "NoopMiddleware",
    "Tracer",
    "Span",
    "NoopTracer",
    "NoopSpan",
    "StateSnapshot",
    "SnapshotStore",
    "ExecutionContext",
    "Node",
    "FunctionNode",
    "Graph",
    "GraphExecutionEngine",
    "Cache",
    "Mailbox",
    "RedisCache",
    "Prompt",
    "InferenceClient",
    "MockInferenceClient",
    "LLMDirectedGraphExecutor",
]