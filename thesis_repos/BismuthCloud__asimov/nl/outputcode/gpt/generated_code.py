from __future__ import annotations

import abc
import asyncio
import dataclasses
import hashlib
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
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Union,
)


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
    is_final: bool = False


@dataclass(frozen=True)
class InferenceResponse:
    text: str
    tool_calls: Tuple[ToolCall, ...] = ()
    usage: Optional[TokenUsage] = None
    raw: Any = None


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


@dataclass
class StateSnapshot:
    snapshot_id: str
    timestamp: float
    state: Dict[str, Any]


class SnapshotStore:
    def __init__(self) -> None:
        self._snapshots: List[StateSnapshot] = []

    def add(self, state: Mapping[str, Any]) -> StateSnapshot:
        snap = StateSnapshot(snapshot_id=str(uuid.uuid4()), timestamp=time.time(), state=dict(state))
        self._snapshots.append(snap)
        return snap

    def list(self) -> List[StateSnapshot]:
        return list(self._snapshots)

    def latest(self) -> Optional[StateSnapshot]:
        return self._snapshots[-1] if self._snapshots else None

    def clear(self) -> None:
        self._snapshots.clear()


class ExecutionContext:
    def __init__(
        self,
        initial_state: Optional[Mapping[str, Any]] = None,
        *,
        tracer: Optional[TelemetryTracer] = None,
        cache: Optional["Cache"] = None,
        middleware: Optional[Sequence[Middleware]] = None,
        snapshotting: bool = True,
    ) -> None:
        self.state: Dict[str, Any] = dict(initial_state or {})
        self.tracer: TelemetryTracer = tracer or NoopTracer()
        self.cache: Optional["Cache"] = cache
        self.middleware: Tuple[Middleware, ...] = tuple(middleware or ())
        self.snapshotting: bool = bool(snapshotting)
        self.snapshots: SnapshotStore = SnapshotStore()
        self.history: List[Dict[str, Any]] = []

    def snapshot(self) -> Optional[StateSnapshot]:
        if not self.snapshotting:
            return None
        return self.snapshots.add(self.state)

    def record_event(self, event: Mapping[str, Any]) -> None:
        self.history.append(dict(event))


class Node(abc.ABC):
    def __init__(self, node_id: str) -> None:
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
    def __init__(self, node_id: str, func: Callable[[ExecutionContext], Awaitable[Any]]) -> None:
        super().__init__(node_id)
        if not callable(func):
            raise ValidationError("func must be callable")
        self._func = func

    async def run(self, ctx: ExecutionContext) -> Any:
        return await self._func(ctx)


class Graph:
    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, List[str]] = {}
        self._reverse_edges: Dict[str, List[str]] = {}

    def add_node(self, node: Node) -> None:
        if node.id in self._nodes:
            raise ValidationError(f"Duplicate node id: {node.id}")
        self._nodes[node.id] = node
        self._edges.setdefault(node.id, [])
        self._reverse_edges.setdefault(node.id, [])

    def add_edge(self, from_node_id: str, to_node_id: str) -> None:
        if from_node_id not in self._nodes or to_node_id not in self._nodes:
            raise ValidationError("Both nodes must exist before adding an edge")
        self._edges.setdefault(from_node_id, [])
        self._reverse_edges.setdefault(to_node_id, [])
        self._edges[from_node_id].append(to_node_id)
        self._reverse_edges[to_node_id].append(from_node_id)

    def get_node(self, node_id: str) -> Node:
        try:
            return self._nodes[node_id]
        except KeyError as e:
            raise ValidationError(f"Unknown node id: {node_id}") from e

    def nodes(self) -> List[Node]:
        return list(self._nodes.values())

    def successors(self, node_id: str) -> List[str]:
        return list(self._edges.get(node_id, []))

    def predecessors(self, node_id: str) -> List[str]:
        return list(self._reverse_edges.get(node_id, []))

    def validate_acyclic(self) -> None:
        visited: Dict[str, int] = {}  # 0=unvisited,1=visiting,2=done

        def dfs(nid: str) -> None:
            state = visited.get(nid, 0)
            if state == 1:
                raise ValidationError("Graph contains a cycle")
            if state == 2:
                return
            visited[nid] = 1
            for succ in self._edges.get(nid, []):
                dfs(succ)
            visited[nid] = 2

        for nid in self._nodes:
            if visited.get(nid, 0) == 0:
                dfs(nid)

    def topological_order(self) -> List[str]:
        self.validate_acyclic()
        indeg: Dict[str, int] = {nid: len(self.predecessors(nid)) for nid in self._nodes}
        q: List[str] = [nid for nid, d in indeg.items() if d == 0]
        out: List[str] = []
        while q:
            nid = q.pop(0)
            out.append(nid)
            for succ in self._edges.get(nid, []):
                indeg[succ] -= 1
                if indeg[succ] == 0:
                    q.append(succ)
        if len(out) != len(self._nodes):
            raise ValidationError("Graph contains a cycle")
        return out


class GraphExecutionEngine:
    def __init__(self, graph: Graph) -> None:
        self._graph = graph

    async def execute(
        self,
        ctx: ExecutionContext,
        *,
        start_nodes: Optional[Sequence[str]] = None,
        directed_selector: Optional["LLMDirectedSelector"] = None,
    ) -> Dict[str, Any]:
        if start_nodes is not None:
            for nid in start_nodes:
                if nid not in {n.id for n in self._graph.nodes()}:
                    raise ValidationError(f"Unknown start node id: {nid}")

        self._graph.validate_acyclic()

        executed: Dict[str, Any] = {}
        ready: List[str] = []

        if start_nodes is None:
            ready = [nid for nid in self._graph.topological_order() if len(self._graph.predecessors(nid)) == 0]
        else:
            ready = list(start_nodes)

        pending: set[str] = set(ready)
        completed: set[str] = set()

        def deps_satisfied(nid: str) -> bool:
            return all(pred in completed for pred in self._graph.predecessors(nid))

        while pending:
            candidates = [nid for nid in list(pending) if deps_satisfied(nid)]
            if not candidates:
                raise ExecutionError("No executable nodes found; dependency deadlock")

            if directed_selector is not None and len(candidates) > 1:
                chosen = await directed_selector.choose_next(ctx, self._graph, candidates)
                if chosen not in candidates:
                    raise ExecutionError("Directed selector returned an invalid node id")
                nid = chosen
            else:
                nid = candidates[0]

            pending.remove(nid)
            node = self._graph.get_node(nid)

            span = ctx.tracer.start_span("graph.node", attributes={"node.id": node.id})
            ctx.record_event({"type": "node_start", "node_id": node.id, "ts": time.time()})
            try:
                for mw in ctx.middleware:
                    await mw.before_node(ctx, node)

                result = await node.run(ctx)
                executed[node.id] = result

                for mw in ctx.middleware:
                    await mw.after_node(ctx, node, result)

                ctx.snapshot()
                ctx.record_event({"type": "node_end", "node_id": node.id, "ts": time.time()})
                completed.add(node.id)

                for succ in self._graph.successors(node.id):
                    if succ not in completed:
                        pending.add(succ)

                span.set_attribute("node.successors", len(self._graph.successors(node.id)))
                span.end()
            except BaseException as e:
                try:
                    for mw in ctx.middleware:
                        await mw.on_error(ctx, node, e)
                finally:
                    span.record_exception(e)
                    span.end()
                raise

        return executed


class LLMDirectedSelector:
    def __init__(self, client: "InferenceClient", *, prompt_template: Optional[str] = None) -> None:
        self._client = client
        self._prompt_template = prompt_template or (
            "You are directing execution of a DAG of tasks.\n"
            "Given the candidate next node ids:\n"
            "{candidates}\n"
            "Choose exactly one node id to execute next. Reply with only the node id."
        )

    async def choose_next(self, ctx: ExecutionContext, graph: Graph, candidates: Sequence[str]) -> str:
        prompt = self._prompt_template.format(candidates="\n".join(candidates))
        resp = await self._client.complete(prompt, ctx=ctx)
        choice = (resp.text or "").strip()
        if choice in candidates:
            return choice
        normalized = choice.split()
        if normalized and normalized[0] in candidates:
            return normalized[0]
        raise ExecutionError("LLM directed selector could not choose a valid candidate")


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
    def with_namespace(self, *, prefix: str = "", suffix: str = "") -> "Cache":
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


class _JsonCodec:
    @staticmethod
    def dumps(value: Any) -> str:
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def loads(value: str) -> Any:
        return json.loads(value)


class InMemoryRedisLike:
    def __init__(self) -> None:
        self._kv: Dict[str, Tuple[str, Optional[float]]] = {}
        self._mailboxes: Dict[str, List[asyncio.Queue[str]]] = {}
        self._lock = asyncio.Lock()

    def _now(self) -> float:
        return time.time()

    def _is_expired(self, exp: Optional[float]) -> bool:
        return exp is not None and self._now() >= exp

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            item = self._kv.get(key)
            if item is None:
                return None
            val, exp = item
            if self._is_expired(exp):
                self._kv.pop(key, None)
                return None
            return val

    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> None:
        exp = None
        if ttl_seconds is not None:
            if ttl_seconds <= 0:
                exp = self._now()
            else:
                exp = self._now() + ttl_seconds
        async with self._lock:
            self._kv[key] = (value, exp)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._kv.pop(key, None)

    async def mget(self, keys: Sequence[str]) -> List[Optional[str]]:
        async with self._lock:
            out: List[Optional[str]] = []
            for k in keys:
                item = self._kv.get(k)
                if item is None:
                    out.append(None)
                    continue
                val, exp = item
                if self._is_expired(exp):
                    self._kv.pop(k, None)
                    out.append(None)
                else:
                    out.append(val)
            return out

    async def flushdb(self) -> None:
        async with self._lock:
            self._kv.clear()

    async def publish(self, channel: str, message: str) -> None:
        async with self._lock:
            queues = list(self._mailboxes.get(channel, []))
        for q in queues:
            q.put_nowait(message)

    async def subscribe(self, channel: str) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue()
        async with self._lock:
            self._mailboxes.setdefault(channel, []).append(q)
        return q

    async def unsubscribe(self, channel: str, q: asyncio.Queue[str]) -> None:
        async with self._lock:
            lst = self._mailboxes.get(channel)
            if not lst:
                return
            try:
                lst.remove(q)
            except ValueError:
                return
            if not lst:
                self._mailboxes.pop(channel, None)


class RedisCache(Cache):
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

    def _ns(self, key: str) -> str:
        if not isinstance(key, str) or not key:
            raise ValidationError("Cache key must be a non-empty string")
        return f"{self._prefix}{key}{self._suffix}"

    async def get(self, key: str) -> Optional[Any]:
        raw = await self._redis.get(self._ns(key))
        if raw is None:
            return None
        try:
            return _JsonCodec.loads(raw)
        except Exception as e:
            raise CacheError("Failed to deserialize cached value") from e

    async def set(self, key: str, value: Any, *, ttl_seconds: Optional[int] = None) -> None:
        try:
            raw = _JsonCodec.dumps(value)
        except Exception as e:
            raise CacheError("Failed to serialize value to JSON") from e
        await self._redis.set(self._ns(key), raw, ttl_seconds=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self._redis.delete(self._ns(key))

    async def get_all(self, keys: Sequence[str]) -> Dict[str, Any]:
        if keys is None:
            raise ValidationError("keys must not be None")
        ns_keys = [self._ns(k) for k in keys]
        raws = await self._redis.mget(ns_keys)
        out: Dict[str, Any] = {}
        for original_key, raw in zip(keys, raws):
            if raw is None:
                continue
            try:
                out[original_key] = _JsonCodec.loads(raw)
            except Exception as e:
                raise CacheError("Failed to deserialize cached value") from e
        return out

    async def clear(self) -> None:
        await self._redis.flushdb()

    def with_namespace(self, *, prefix: str = "", suffix: str = "") -> Cache:
        return RedisCache(self._redis, prefix=self._prefix + prefix, suffix=suffix + self._suffix)

    def mailbox(self, name: str) -> Mailbox:
        if not isinstance(name, str) or not name:
            raise ValidationError("Mailbox name must be a non-empty string")
        channel = self._ns(f"mailbox:{name}")
        return RedisMailbox(self._redis, channel)


class RedisMailbox(Mailbox):
    def __init__(self, redis: InMemoryRedisLike, channel: str) -> None:
        self._redis = redis
        self._channel = channel

    async def publish(self, message: Any) -> None:
        try:
            raw = _JsonCodec.dumps(message)
        except Exception as e:
            raise CacheError("Failed to serialize mailbox message") from e
        await self._redis.publish(self._channel, raw)

    async def subscribe(self) -> AsyncIterator[Any]:
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


class InferenceClient(abc.ABC):
    @abc.abstractmethod
    async def complete(
        self,
        prompt: str,
        *,
        ctx: Optional[ExecutionContext] = None,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        stream: bool = False,
        cache_key: Optional[str] = None,
    ) -> InferenceResponse:
        raise NotImplementedError

    @abc.abstractmethod
    async def stream(
        self,
        prompt: str,
        *,
        ctx: Optional[ExecutionContext] = None,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        cache_key: Optional[str] = None,
    ) -> AsyncIterator[InferenceChunk]:
        raise NotImplementedError


class PromptCache:
    def __init__(self, cache: Cache, *, namespace_prefix: str = "prompt_cache:") -> None:
        self._cache = cache.with_namespace(prefix=namespace_prefix)

    @staticmethod
    def _hash_payload(payload: Mapping[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def get(self, payload: Mapping[str, Any]) -> Optional[InferenceResponse]:
        key = self._hash_payload(payload)
        data = await self._cache.get(key)
        if data is None:
            return None
        if not isinstance(data, dict) or "text" not in data:
            return None
        tool_calls: Tuple[ToolCall, ...] = ()
        if isinstance(data.get("tool_calls"), list):
            tcs: List[ToolCall] = []
            for item in data["tool_calls"]:
                if isinstance(item, dict) and "name" in item:
                    tcs.append(
                        ToolCall(
                            name=str(item["name"]),
                            arguments=dict(item.get("arguments") or {}),
                            call_id=str(item.get("call_id") or str(uuid.uuid4())),
                        )
                    )
            tool_calls = tuple(tcs)
        usage = None
        if isinstance(data.get("usage"), dict):
            u = data["usage"]
            usage = TokenUsage(prompt_tokens=int(u.get("prompt_tokens", 0)), completion_tokens=int(u.get("completion_tokens", 0)))
        return InferenceResponse(text=str(data["text"]), tool_calls=tool_calls, usage=usage, raw=data.get("raw"))

    async def set(self, payload: Mapping[str, Any], response: InferenceResponse, *, ttl_seconds: Optional[int] = None) -> None:
        key = self._hash_payload(payload)
        data: Dict[str, Any] = {
            "text": response.text,
            "tool_calls": [dataclasses.asdict(tc) for tc in response.tool_calls],
            "usage": dataclasses.asdict(response.usage) if response.usage is not None else None,
            "raw": response.raw,
        }
        await self._cache.set(key, data, ttl_seconds=ttl_seconds)


class InstrumentedInferenceClient(InferenceClient):
    def __init__(
        self,
        inner: InferenceClient,
        *,
        tracer: Optional[TelemetryTracer] = None,
    ) -> None:
        self._inner = inner
        self._tracer = tracer or NoopTracer()

    async def complete(
        self,
        prompt: str,
        *,
        ctx: Optional[ExecutionContext] = None,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        stream: bool = False,
        cache_key: Optional[str] = None,
    ) -> InferenceResponse:
        tracer = (ctx.tracer if ctx is not None else self._tracer) or NoopTracer()
        span = tracer.start_span("inference.complete", attributes={"stream": bool(stream)})
        try:
            resp = await self._inner.complete(
                prompt,
                ctx=ctx,
                tools=tools,
                tool_choice=tool_choice,
                stream=stream,
                cache_key=cache_key,
            )
            if resp.usage is not None:
                span.set_attribute("usage.prompt_tokens", resp.usage.prompt_tokens)
                span.set_attribute("usage.completion_tokens", resp.usage.completion_tokens)
                span.set_attribute("usage.total_tokens", resp.usage.total_tokens)
            span.end()
            return resp
        except BaseException as e:
            span.record_exception(e)
            span.end()
            raise

    async def stream(
        self,
        prompt: str,
        *,
        ctx: Optional[ExecutionContext] = None,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        cache_key: Optional[str] = None,
    ) -> AsyncIterator[InferenceChunk]:
        tracer = (ctx.tracer if ctx is not None else self._tracer) or NoopTracer()
        span = tracer.start_span("inference.stream")
        try:
            async for chunk in self._inner.stream(
                prompt,
                ctx=ctx,
                tools=tools,
                tool_choice=tool_choice,
                cache_key=cache_key,
            ):
                if chunk.usage is not None:
                    span.set_attribute("usage.prompt_tokens", chunk.usage.prompt_tokens)
                    span.set_attribute("usage.completion_tokens", chunk.usage.completion_tokens)
                    span.set_attribute("usage.total_tokens", chunk.usage.total_tokens)
                yield chunk
            span.end()
        except BaseException as e:
            span.record_exception(e)
            span.end()
            raise


class CachedInferenceClient(InferenceClient):
    def __init__(
        self,
        inner: InferenceClient,
        cache: Cache,
        *,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        self._inner = inner
        self._prompt_cache = PromptCache(cache)
        self._ttl_seconds = ttl_seconds

    def _payload(
        self,
        prompt: str,
        tools: Optional[Sequence[Mapping[str, Any]]],
        tool_choice: Optional[Union[str, Mapping[str, Any]]],
        cache_key: Optional[str],
    ) -> Dict[str, Any]:
        return {
            "prompt": prompt,
            "tools": list(tools) if tools is not None else None,
            "tool_choice": tool_choice,
            "cache_key": cache_key,
        }

    async def complete(
        self,
        prompt: str,
        *,
        ctx: Optional[ExecutionContext] = None,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        stream: bool = False,
        cache_key: Optional[str] = None,
    ) -> InferenceResponse:
        if stream:
            chunks: List[str] = []
            tool_calls: List[ToolCall] = []
            usage: Optional[TokenUsage] = None
            async for ch in self.stream(prompt, ctx=ctx, tools=tools, tool_choice=tool_choice, cache_key=cache_key):
                if ch.text:
                    chunks.append(ch.text)
                if ch.tool_calls:
                    tool_calls.extend(list(ch.tool_calls))
                if ch.usage is not None:
                    usage = ch.usage
            return InferenceResponse(text="".join(chunks), tool_calls=tuple(tool_calls), usage=usage, raw=None)

        payload = self._payload(prompt, tools, tool_choice, cache_key)
        cached = await self._prompt_cache.get(payload)
        if cached is not None:
            return cached

        resp = await self._inner.complete(prompt, ctx=ctx, tools=tools, tool_choice=tool_choice, stream=False, cache_key=cache_key)
        await self._prompt_cache.set(payload, resp, ttl_seconds=self._ttl_seconds)
        return resp

    async def stream(
        self,
        prompt: str,
        *,
        ctx: Optional[ExecutionContext] = None,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        cache_key: Optional[str] = None,
    ) -> AsyncIterator[InferenceChunk]:
        payload = self._payload(prompt, tools, tool_choice, cache_key)
        cached = await self._prompt_cache.get(payload)
        if cached is not None:
            yield InferenceChunk(text=cached.text, tool_calls=cached.tool_calls, usage=cached.usage, is_final=True)
            return

        chunks: List[InferenceChunk] = []
        text_parts: List[str] = []
        tool_calls: List[ToolCall] = []
        usage: Optional[TokenUsage] = None

        async for ch in self._inner.stream(prompt, ctx=ctx, tools=tools, tool_choice=tool_choice, cache_key=cache_key):
            chunks.append(ch)
            if ch.text:
                text_parts.append(ch.text)
            if ch.tool_calls:
                tool_calls.extend(list(ch.tool_calls))
            if ch.usage is not None:
                usage = ch.usage
            yield ch

        final_text = "".join(text_parts)
        resp = InferenceResponse(text=final_text, tool_calls=tuple(tool_calls), usage=usage, raw=None)
        await self._prompt_cache.set(payload, resp, ttl_seconds=self._ttl_seconds)
        if not chunks or not chunks[-1].is_final:
            yield InferenceChunk(text="", tool_calls=(), usage=usage, is_final=True)


class SimpleInferenceClient(InferenceClient):
    def __init__(self, *, model_name: str = "simple") -> None:
        self._model_name = model_name

    def _estimate_usage(self, prompt: str, completion: str) -> TokenUsage:
        def est_tokens(s: str) -> int:
            s = s.strip()
            if not s:
                return 0
            return max(1, len(s.split()))
        return TokenUsage(prompt_tokens=est_tokens(prompt), completion_tokens=est_tokens(completion))

    async def complete(
        self,
        prompt: str,
        *,
        ctx: Optional[ExecutionContext] = None,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        stream: bool = False,
        cache_key: Optional[str] = None,
    ) -> InferenceResponse:
        if stream:
            chunks: List[str] = []
            tool_calls: List[ToolCall] = []
            usage: Optional[TokenUsage] = None
            async for ch in self.stream(prompt, ctx=ctx, tools=tools, tool_choice=tool_choice, cache_key=cache_key):
                if ch.text:
                    chunks.append(ch.text)
                if ch.tool_calls:
                    tool_calls.extend(list(ch.tool_calls))
                if ch.usage is not None:
                    usage = ch.usage
            return InferenceResponse(text="".join(chunks), tool_calls=tuple(tool_calls), usage=usage, raw=None)

        if not isinstance(prompt, str):
            raise ValidationError("prompt must be a string")
        completion = prompt
        usage = self._estimate_usage(prompt, completion)
        return InferenceResponse(text=completion, tool_calls=(), usage=usage, raw={"model": self._model_name})

    async def stream(
        self,
        prompt: str,
        *,
        ctx: Optional[ExecutionContext] = None,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        cache_key: Optional[str] = None,
    ) -> AsyncIterator[InferenceChunk]:
        if not isinstance(prompt, str):
            raise ValidationError("prompt must be a string")
        text = prompt
        usage = self._estimate_usage(prompt, text)
        if not text:
            yield InferenceChunk(text="", tool_calls=(), usage=usage, is_final=True)
            return
        step = max(1, min(32, len(text)))
        for i in range(0, len(text), step):
            part = text[i : i + step]
            is_final = (i + step) >= len(text)
            yield InferenceChunk(text=part, tool_calls=(), usage=(usage if is_final else None), is_final=is_final)
            await asyncio.sleep(0)


__all__ = [
    "FrameworkError",
    "ValidationError",
    "ExecutionError",
    "CacheError",
    "InferenceError",
    "TokenUsage",
    "ToolCall",
    "InferenceChunk",
    "InferenceResponse",
    "TelemetrySpan",
    "TelemetryTracer",
    "NoopTracer",
    "Middleware",
    "BaseMiddleware",
    "StateSnapshot",
    "SnapshotStore",
    "ExecutionContext",
    "Node",
    "FunctionNode",
    "Graph",
    "GraphExecutionEngine",
    "LLMDirectedSelector",
    "Cache",
    "Mailbox",
    "RedisCache",
    "RedisMailbox",
    "InferenceClient",
    "PromptCache",
    "InstrumentedInferenceClient",
    "CachedInferenceClient",
    "SimpleInferenceClient",
]