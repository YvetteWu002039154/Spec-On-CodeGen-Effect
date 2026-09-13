from __future__ import annotations

import abc
import asyncio
import dataclasses
import hashlib
import json
import time
from dataclasses import dataclass
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
    Set,
    Tuple,
    Union,
)


JsonPrimitive = Union[str, int, float, bool, None]
JsonValue = Union[JsonPrimitive, Dict[str, "JsonValue"], List["JsonValue"]]


class CacheError(Exception):
    pass


class GraphError(Exception):
    pass


class InferenceError(Exception):
    pass


class ValidationError(Exception):
    pass


def _json_dumps(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, default=str)
    except Exception as e:
        raise CacheError(f"Failed to serialize value to JSON: {e}") from e


def _json_loads(value: str) -> Any:
    try:
        return json.loads(value)
    except Exception as e:
        raise CacheError(f"Failed to deserialize JSON: {e}") from e


def _now_ms() -> int:
    return int(time.time() * 1000)


class Middleware(Protocol):
    async def before_node(self, ctx: "ExecutionContext", node: "Node") -> None: ...
    async def after_node(self, ctx: "ExecutionContext", node: "Node", result: Any) -> None: ...
    async def on_error(self, ctx: "ExecutionContext", node: "Node", error: BaseException) -> None: ...


class NoopMiddleware:
    async def before_node(self, ctx: "ExecutionContext", node: "Node") -> None:
        return

    async def after_node(self, ctx: "ExecutionContext", node: "Node", result: Any) -> None:
        return

    async def on_error(self, ctx: "ExecutionContext", node: "Node", error: BaseException) -> None:
        return


class Tracer(Protocol):
    def start_span(self, name: str, attributes: Optional[Mapping[str, Any]] = None) -> "Span": ...


class Span(Protocol):
    def set_attribute(self, key: str, value: Any) -> None: ...
    def record_exception(self, exc: BaseException) -> None: ...
    def end(self) -> None: ...


class NoopSpan:
    def set_attribute(self, key: str, value: Any) -> None:
        return

    def record_exception(self, exc: BaseException) -> None:
        return

    def end(self) -> None:
        return


class NoopTracer:
    def start_span(self, name: str, attributes: Optional[Mapping[str, Any]] = None) -> Span:
        return NoopSpan()


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return int(self.prompt_tokens) + int(self.completion_tokens)


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: Dict[str, Any]


@dataclass(frozen=True)
class InferenceResponse:
    content: str
    tool_calls: Tuple[ToolCall, ...] = ()
    usage: TokenUsage = TokenUsage()
    provider: str = "unknown"
    model: str = "unknown"
    cached: bool = False


@dataclass(frozen=True)
class StreamChunk:
    delta: str = ""
    tool_calls: Tuple[ToolCall, ...] = ()
    usage: Optional[TokenUsage] = None
    is_final: bool = False


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
    def __init__(self, queue: "asyncio.Queue[str]") -> None:
        self._queue = queue

    async def publish(self, message: Any) -> None:
        await self._queue.put(_json_dumps(message))

    async def subscribe(self) -> AsyncIterator[Any]:
        while True:
            raw = await self._queue.get()
            yield _json_loads(raw)


class RedisCache(Cache):
    def __init__(self, prefix: str = "", suffix: str = "") -> None:
        self._prefix = prefix or ""
        self._suffix = suffix or ""
        self._store: Dict[str, Tuple[str, Optional[float]]] = {}
        self._mailboxes: Dict[str, asyncio.Queue[str]] = {}
        self._lock = asyncio.Lock()

    def _ns(self, key: str) -> str:
        if not isinstance(key, str) or not key:
            raise ValidationError("Cache key must be a non-empty string")
        return f"{self._prefix}{key}{self._suffix}"

    def _purge_if_expired(self, nkey: str) -> None:
        item = self._store.get(nkey)
        if item is None:
            return
        _, exp = item
        if exp is not None and time.time() >= exp:
            self._store.pop(nkey, None)

    async def get(self, key: str) -> Optional[Any]:
        nkey = self._ns(key)
        async with self._lock:
            self._purge_if_expired(nkey)
            item = self._store.get(nkey)
            if item is None:
                return None
            raw, _ = item
        return _json_loads(raw)

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        nkey = self._ns(key)
        exp: Optional[float] = None
        if ttl_seconds is not None:
            if not isinstance(ttl_seconds, int) or ttl_seconds <= 0:
                raise ValidationError("ttl_seconds must be a positive integer when provided")
            exp = time.time() + ttl_seconds
        raw = _json_dumps(value)
        async with self._lock:
            self._store[nkey] = (raw, exp)

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
                self._purge_if_expired(nkey)
                item = self._store.get(nkey)
                if item is None:
                    continue
                raw, _ = item
                result[key] = _json_loads(raw)
        return result

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    def mailbox(self, name: str) -> Mailbox:
        if not isinstance(name, str) or not name:
            raise ValidationError("Mailbox name must be a non-empty string")
        q = self._mailboxes.get(name)
        if q is None:
            q = asyncio.Queue()
            self._mailboxes[name] = q
        return _InMemoryMailbox(q)


class PromptCache:
    def __init__(self, cache: Cache, namespace: str = "prompt_cache:") -> None:
        if not namespace:
            raise ValidationError("namespace must be non-empty")
        self._cache = cache
        self._ns = namespace

    def _key(self, provider: str, model: str, prompt: str, extra: Optional[Mapping[str, Any]] = None) -> str:
        if not provider or not model:
            raise ValidationError("provider and model must be non-empty")
        if not isinstance(prompt, str):
            raise ValidationError("prompt must be a string")
        payload = {
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "extra": dict(extra) if extra else {},
        }
        digest = hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()
        return f"{self._ns}{digest}"

    async def get(self, provider: str, model: str, prompt: str, extra: Optional[Mapping[str, Any]] = None) -> Optional[InferenceResponse]:
        key = self._key(provider, model, prompt, extra)
        data = await self._cache.get(key)
        if data is None:
            return None
        try:
            tool_calls = tuple(ToolCall(name=tc["name"], arguments=dict(tc.get("arguments", {}))) for tc in data.get("tool_calls", []))
            usage_d = data.get("usage", {}) or {}
            usage = TokenUsage(prompt_tokens=int(usage_d.get("prompt_tokens", 0)), completion_tokens=int(usage_d.get("completion_tokens", 0)))
            return InferenceResponse(
                content=str(data.get("content", "")),
                tool_calls=tool_calls,
                usage=usage,
                provider=str(data.get("provider", provider)),
                model=str(data.get("model", model)),
                cached=True,
            )
        except Exception as e:
            raise CacheError(f"Invalid cached inference response: {e}") from e

    async def set(
        self,
        provider: str,
        model: str,
        prompt: str,
        response: InferenceResponse,
        extra: Optional[Mapping[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        key = self._key(provider, model, prompt, extra)
        data = {
            "content": response.content,
            "tool_calls": [{"name": tc.name, "arguments": tc.arguments} for tc in response.tool_calls],
            "usage": {"prompt_tokens": response.usage.prompt_tokens, "completion_tokens": response.usage.completion_tokens},
            "provider": response.provider,
            "model": response.model,
        }
        await self._cache.set(key, data, ttl_seconds=ttl_seconds)


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
    ) -> InferenceResponse:
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
    ) -> AsyncIterator[StreamChunk]:
        raise NotImplementedError


class SimpleLLMClient(InferenceClient):
    def __init__(
        self,
        provider: str,
        *,
        tracer: Optional[Tracer] = None,
        prompt_cache: Optional[PromptCache] = None,
        cache_ttl_seconds: Optional[int] = None,
    ) -> None:
        if not provider:
            raise ValidationError("provider must be non-empty")
        if cache_ttl_seconds is not None and (not isinstance(cache_ttl_seconds, int) or cache_ttl_seconds <= 0):
            raise ValidationError("cache_ttl_seconds must be a positive integer when provided")
        self._provider = provider
        self._tracer = tracer or NoopTracer()
        self._prompt_cache = prompt_cache
        self._cache_ttl_seconds = cache_ttl_seconds

    @property
    def provider(self) -> str:
        return self._provider

    def _estimate_usage(self, prompt: str, completion: str) -> TokenUsage:
        def est_tokens(s: str) -> int:
            s = s.strip()
            if not s:
                return 0
            return max(1, len(s) // 4)

        return TokenUsage(prompt_tokens=est_tokens(prompt), completion_tokens=est_tokens(completion))

    def _extract_tool_calls(self, prompt: str) -> Tuple[ToolCall, ...]:
        marker = "TOOL_CALL:"
        if marker not in prompt:
            return ()
        calls: List[ToolCall] = []
        for part in prompt.split(marker)[1:]:
            seg = part.strip()
            if not seg:
                continue
            if seg.startswith("{"):
                try:
                    obj = json.loads(seg)
                    name = str(obj.get("name", "")).strip()
                    if not name:
                        continue
                    args = obj.get("arguments", {})
                    if args is None:
                        args = {}
                    if not isinstance(args, dict):
                        args = {"value": args}
                    calls.append(ToolCall(name=name, arguments=dict(args)))
                except Exception:
                    continue
            else:
                name = seg.split()[0].strip()
                if name:
                    calls.append(ToolCall(name=name, arguments={}))
        return tuple(calls)

    async def infer(
        self,
        prompt: str,
        *,
        model: str,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> InferenceResponse:
        if not isinstance(prompt, str):
            raise ValidationError("prompt must be a string")
        if not model:
            raise ValidationError("model must be non-empty")

        span = self._tracer.start_span(
            "inference.infer",
            attributes={"provider": self._provider, "model": model},
        )
        try:
            extra = {"tools": list(tools) if tools else None, "tool_choice": tool_choice, "metadata": dict(metadata) if metadata else None}
            if self._prompt_cache is not None:
                cached = await self._prompt_cache.get(self._provider, model, prompt, extra=extra)
                if cached is not None:
                    span.set_attribute("cache.hit", True)
                    return cached

            tool_calls = self._extract_tool_calls(prompt)
            completion = f"[{self._provider}:{model}] {prompt}"
            usage = self._estimate_usage(prompt, completion)
            resp = InferenceResponse(
                content=completion,
                tool_calls=tool_calls,
                usage=usage,
                provider=self._provider,
                model=model,
                cached=False,
            )
            if self._prompt_cache is not None:
                await self._prompt_cache.set(self._provider, model, prompt, resp, extra=extra, ttl_seconds=self._cache_ttl_seconds)
            span.set_attribute("cache.hit", False)
            span.set_attribute("usage.total_tokens", resp.usage.total_tokens)
            return resp
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
    ) -> AsyncIterator[StreamChunk]:
        if not isinstance(prompt, str):
            raise ValidationError("prompt must be a string")
        if not model:
            raise ValidationError("model must be non-empty")

        span = self._tracer.start_span(
            "inference.stream",
            attributes={"provider": self._provider, "model": model},
        )
        try:
            extra = {"tools": list(tools) if tools else None, "tool_choice": tool_choice, "metadata": dict(metadata) if metadata else None}
            if self._prompt_cache is not None:
                cached = await self._prompt_cache.get(self._provider, model, prompt, extra=extra)
                if cached is not None:
                    span.set_attribute("cache.hit", True)
                    yield StreamChunk(delta=cached.content, tool_calls=cached.tool_calls, usage=cached.usage, is_final=True)
                    return

            tool_calls = self._extract_tool_calls(prompt)
            completion = f"[{self._provider}:{model}] {prompt}"
            for i in range(0, len(completion), 32):
                await asyncio.sleep(0)
                yield StreamChunk(delta=completion[i : i + 32], tool_calls=(), usage=None, is_final=False)
            usage = self._estimate_usage(prompt, completion)
            final = StreamChunk(delta="", tool_calls=tool_calls, usage=usage, is_final=True)
            yield final

            if self._prompt_cache is not None:
                resp = InferenceResponse(
                    content=completion,
                    tool_calls=tool_calls,
                    usage=usage,
                    provider=self._provider,
                    model=model,
                    cached=False,
                )
                await self._prompt_cache.set(self._provider, model, prompt, resp, extra=extra, ttl_seconds=self._cache_ttl_seconds)
            span.set_attribute("cache.hit", False)
            span.set_attribute("usage.total_tokens", usage.total_tokens)
        except BaseException as e:
            span.record_exception(e)
            raise
        finally:
            span.end()


@dataclass(frozen=True)
class Snapshot:
    snapshot_id: str
    created_at_ms: int
    state: Dict[str, Any]
    node_status: Dict[str, str]
    results: Dict[str, Any]


class SnapshotStore:
    def __init__(self) -> None:
        self._snapshots: Dict[str, Snapshot] = {}

    def save(self, snapshot: Snapshot) -> None:
        if not snapshot.snapshot_id:
            raise ValidationError("snapshot_id must be non-empty")
        self._snapshots[snapshot.snapshot_id] = snapshot

    def get(self, snapshot_id: str) -> Optional[Snapshot]:
        return self._snapshots.get(snapshot_id)

    def list_ids(self) -> List[str]:
        return list(self._snapshots.keys())


class Node(abc.ABC):
    def __init__(self, node_id: str, *, depends_on: Optional[Sequence[str]] = None) -> None:
        if not isinstance(node_id, str) or not node_id:
            raise ValidationError("node_id must be a non-empty string")
        self._id = node_id
        self._depends_on = tuple(depends_on) if depends_on else ()

        for d in self._depends_on:
            if not isinstance(d, str) or not d:
                raise ValidationError("depends_on must contain non-empty strings")

    @property
    def id(self) -> str:
        return self._id

    @property
    def depends_on(self) -> Tuple[str, ...]:
        return self._depends_on

    @abc.abstractmethod
    async def run(self, ctx: "ExecutionContext") -> Any:
        raise NotImplementedError


class FunctionNode(Node):
    def __init__(
        self,
        node_id: str,
        func: Callable[["ExecutionContext"], Union[Any, Awaitable[Any]]],
        *,
        depends_on: Optional[Sequence[str]] = None,
    ) -> None:
        super().__init__(node_id, depends_on=depends_on)
        if not callable(func):
            raise ValidationError("func must be callable")
        self._func = func

    async def run(self, ctx: "ExecutionContext") -> Any:
        res = self._func(ctx)
        if asyncio.iscoroutine(res):
            return await res
        return res


class LLMNode(Node):
    def __init__(
        self,
        node_id: str,
        client: InferenceClient,
        *,
        model: str,
        prompt: Union[str, Callable[["ExecutionContext"], Union[str, Awaitable[str]]]],
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[Union[str, Mapping[str, Any]]] = None,
        depends_on: Optional[Sequence[str]] = None,
        stream: bool = False,
    ) -> None:
        super().__init__(node_id, depends_on=depends_on)
        if not model:
            raise ValidationError("model must be non-empty")
        self._client = client
        self._model = model
        self._prompt = prompt
        self._tools = list(tools) if tools else None
        self._tool_choice = tool_choice
        self._stream = bool(stream)

    async def _resolve_prompt(self, ctx: "ExecutionContext") -> str:
        p = self._prompt
        if isinstance(p, str):
            return p
        if callable(p):
            res = p(ctx)
            if asyncio.iscoroutine(res):
                res = await res
            if not isinstance(res, str):
                raise ValidationError("prompt callable must return a string")
            return res
        raise ValidationError("prompt must be a string or callable")

    async def run(self, ctx: "ExecutionContext") -> Any:
        prompt = await self._resolve_prompt(ctx)
        if not self._stream:
            return await self._client.infer(prompt, model=self._model, tools=self._tools, tool_choice=self._tool_choice, metadata=ctx.metadata)
        chunks: List[StreamChunk] = []
        async for ch in self._client.stream(prompt, model=self._model, tools=self._tools, tool_choice=self._tool_choice, metadata=ctx.metadata):
            chunks.append(ch)
        content = "".join(c.delta for c in chunks)
        final_usage: TokenUsage = TokenUsage()
        final_tool_calls: Tuple[ToolCall, ...] = ()
        for c in reversed(chunks):
            if c.usage is not None:
                final_usage = c.usage
                break
        for c in reversed(chunks):
            if c.tool_calls:
                final_tool_calls = c.tool_calls
                break
        return InferenceResponse(
            content=content,
            tool_calls=final_tool_calls,
            usage=final_usage,
            provider=getattr(self._client, "provider", "unknown"),
            model=self._model,
            cached=False,
        )


class ExecutionContext:
    def __init__(
        self,
        *,
        state: Optional[Dict[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        cache: Optional[Cache] = None,
        tracer: Optional[Tracer] = None,
        snapshot_store: Optional[SnapshotStore] = None,
    ) -> None:
        self._state: Dict[str, Any] = dict(state) if state else {}
        self._metadata: Dict[str, Any] = dict(metadata) if metadata else {}
        self._cache = cache
        self._tracer = tracer or NoopTracer()
        self._snapshot_store = snapshot_store or SnapshotStore()

        self._results: Dict[str, Any] = {}
        self._node_status: Dict[str, str] = {}
        self._history: List[Dict[str, Any]] = []

    @property
    def state(self) -> Dict[str, Any]:
        return self._state

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata

    @property
    def cache(self) -> Optional[Cache]:
        return self._cache

    @property
    def tracer(self) -> Tracer:
        return self._tracer

    @property
    def snapshot_store(self) -> SnapshotStore:
        return self._snapshot_store

    @property
    def results(self) -> Dict[str, Any]:
        return self._results

    @property
    def node_status(self) -> Dict[str, str]:
        return self._node_status

    @property
    def history(self) -> List[Dict[str, Any]]:
        return self._history

    def snapshot(self, snapshot_id: Optional[str] = None) -> Snapshot:
        sid = snapshot_id or hashlib.sha256(f"{_now_ms()}:{id(self)}".encode("utf-8")).hexdigest()
        snap = Snapshot(
            snapshot_id=sid,
            created_at_ms=_now_ms(),
            state=json.loads(_json_dumps(self._state)),
            node_status=dict(self._node_status),
            results=json.loads(_json_dumps(self._results)),
        )
        self._snapshot_store.save(snap)
        return snap


class Graph:
    def __init__(self, *, middleware: Optional[Sequence[Middleware]] = None, tracer: Optional[Tracer] = None) -> None:
        self._nodes: Dict[str, Node] = {}
        self._middleware: List[Middleware] = list(middleware) if middleware else []
        self._tracer = tracer or NoopTracer()

    @property
    def tracer(self) -> Tracer:
        return self._tracer

    def add_node(self, node: Node) -> None:
        if node.id in self._nodes:
            raise ValidationError(f"Duplicate node id: {node.id}")
        self._nodes[node.id] = node

    def get_node(self, node_id: str) -> Node:
        try:
            return self._nodes[node_id]
        except KeyError as e:
            raise ValidationError(f"Unknown node id: {node_id}") from e

    def _validate(self) -> None:
        for node in self._nodes.values():
            for dep in node.depends_on:
                if dep not in self._nodes:
                    raise ValidationError(f"Node '{node.id}' depends on unknown node '{dep}'")
        self._toposort()  # cycle check

    def _toposort(self) -> List[str]:
        nodes = self._nodes
        indeg: Dict[str, int] = {nid: 0 for nid in nodes}
        adj: Dict[str, List[str]] = {nid: [] for nid in nodes}
        for nid, node in nodes.items():
            for dep in node.depends_on:
                adj[dep].append(nid)
                indeg[nid] += 1

        q: List[str] = [nid for nid, d in indeg.items() if d == 0]
        order: List[str] = []
        while q:
            nid = q.pop(0)
            order.append(nid)
            for nxt in adj[nid]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    q.append(nxt)

        if len(order) != len(nodes):
            raise GraphError("Graph contains a cycle")
        return order

    async def execute(
        self,
        ctx: ExecutionContext,
        *,
        target_nodes: Optional[Sequence[str]] = None,
        snapshot_before: bool = False,
        snapshot_after: bool = False,
    ) -> Dict[str, Any]:
        if ctx is None:
            raise ValidationError("ctx must not be None")
        self._validate()

        targets: Optional[Set[str]] = None
        if target_nodes is not None:
            targets = set()
            for t in target_nodes:
                if t not in self._nodes:
                    raise ValidationError(f"Unknown target node id: {t}")
                targets.add(t)

            needed: Set[str] = set()

            def add_deps(nid: str) -> None:
                if nid in needed:
                    return
                needed.add(nid)
                for d in self._nodes[nid].depends_on:
                    add_deps(d)

            for t in targets:
                add_deps(t)
            targets = needed

        order = self._toposort()
        if targets is not None:
            order = [nid for nid in order if nid in targets]

        if snapshot_before:
            ctx.snapshot()

        for nid in order:
            node = self._nodes[nid]
            span = self._tracer.start_span("graph.node", attributes={"node.id": nid})
            ctx.node_status[nid] = "running"
            start_ms = _now_ms()
            for mw in self._middleware:
                await mw.before_node(ctx, node)
            try:
                result = await node.run(ctx)
                ctx.results[nid] = result
                ctx.node_status[nid] = "completed"
                end_ms = _now_ms()
                ctx.history.append(
                    {
                        "node_id": nid,
                        "status": "completed",
                        "started_at_ms": start_ms,
                        "ended_at_ms": end_ms,
                        "duration_ms": end_ms - start_ms,
                    }
                )
                for mw in self._middleware:
                    await mw.after_node(ctx, node, result)
                span.set_attribute("node.status", "completed")
            except BaseException as e:
                ctx.node_status[nid] = "failed"
                end_ms = _now_ms()
                ctx.history.append(
                    {
                        "node_id": nid,
                        "status": "failed",
                        "started_at_ms": start_ms,
                        "ended_at_ms": end_ms,
                        "duration_ms": end_ms - start_ms,
                        "error": repr(e),
                    }
                )
                for mw in self._middleware:
                    await mw.on_error(ctx, node, e)
                span.set_attribute("node.status", "failed")
                span.record_exception(e)
                raise
            finally:
                span.end()

        if snapshot_after:
            ctx.snapshot()

        return ctx.results


__all__ = [
    "Cache",
    "CacheError",
    "ExecutionContext",
    "FunctionNode",
    "Graph",
    "GraphError",
    "InferenceClient",
    "InferenceError",
    "InferenceResponse",
    "LLMNode",
    "Mailbox",
    "Middleware",
    "NoopMiddleware",
    "NoopTracer",
    "PromptCache",
    "RedisCache",
    "Snapshot",
    "SnapshotStore",
    "Span",
    "StreamChunk",
    "TokenUsage",
    "ToolCall",
    "Tracer",
    "ValidationError",
]