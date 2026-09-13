import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

try:
    from opentelemetry import trace
    from opentelemetry.trace import Span, Tracer
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Enums and Constants
# ---------------------------------------------------------------------------

class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EdgeType(Enum):
    DEFAULT = "default"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GraphError(Exception):
    pass


class CycleDetectedError(GraphError):
    pass


class NodeNotFoundError(GraphError):
    pass


class InferenceError(Exception):
    pass


class CacheError(Exception):
    pass


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class Message:
    role: MessageRole
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cached_tokens=self.cached_tokens + other.cached_tokens,
        )


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class InferenceResponse:
    content: str
    model: str
    usage: TokenUsage
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass
class StreamChunk:
    content: str
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    usage: Optional[TokenUsage] = None


# ---------------------------------------------------------------------------
# Graph State
# ---------------------------------------------------------------------------

class GraphState:
    def __init__(self, initial: Optional[Dict[str, Any]] = None):
        self._data: Dict[str, Any] = initial.copy() if initial else {}
        self._snapshots: List[Dict[str, Any]] = []

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def update(self, data: Dict[str, Any]) -> None:
        self._data.update(data)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def snapshot(self) -> int:
        self._snapshots.append(self._data.copy())
        return len(self._snapshots) - 1

    def restore(self, snapshot_id: int) -> None:
        if snapshot_id < 0 or snapshot_id >= len(self._snapshots):
            raise ValueError(f"Invalid snapshot_id: {snapshot_id}")
        self._data = self._snapshots[snapshot_id].copy()

    def list_snapshots(self) -> List[int]:
        return list(range(len(self._snapshots)))

    def to_dict(self) -> Dict[str, Any]:
        return self._data.copy()

    def __repr__(self) -> str:
        return f"GraphState({self._data})"


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class MiddlewareContext:
    def __init__(self, node_name: str, state: GraphState, metadata: Optional[Dict[str, Any]] = None):
        self.node_name = node_name
        self.state = state
        self.metadata: Dict[str, Any] = metadata or {}
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self.error: Optional[Exception] = None

    def elapsed(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time


class Middleware(ABC):
    @abstractmethod
    async def before_node(self, ctx: MiddlewareContext) -> None:
        pass

    @abstractmethod
    async def after_node(self, ctx: MiddlewareContext) -> None:
        pass

    async def on_error(self, ctx: MiddlewareContext, error: Exception) -> None:
        pass


class LoggingMiddleware(Middleware):
    async def before_node(self, ctx: MiddlewareContext) -> None:
        print(f"[LOG] Starting node: {ctx.node_name}")

    async def after_node(self, ctx: MiddlewareContext) -> None:
        ctx.end_time = time.time()
        print(f"[LOG] Completed node: {ctx.node_name} in {ctx.elapsed():.3f}s")

    async def on_error(self, ctx: MiddlewareContext, error: Exception) -> None:
        print(f"[LOG] Error in node {ctx.node_name}: {error}")


class TimingMiddleware(Middleware):
    def __init__(self):
        self.timings: Dict[str, List[float]] = defaultdict(list)

    async def before_node(self, ctx: MiddlewareContext) -> None:
        ctx.metadata["_timing_start"] = time.time()

    async def after_node(self, ctx: MiddlewareContext) -> None:
        start = ctx.metadata.get("_timing_start", ctx.start_time)
        elapsed = time.time() - start
        self.timings[ctx.node_name].append(elapsed)

    def get_average(self, node_name: str) -> Optional[float]:
        times = self.timings.get(node_name)
        if not times:
            return None
        return sum(times) / len(times)


class OpenTelemetryMiddleware(Middleware):
    def __init__(self, tracer_name: str = "graph_engine"):
        self._tracer_name = tracer_name
        self._spans: Dict[str, Any] = {}
        if OTEL_AVAILABLE:
            self._tracer = trace.get_tracer(tracer_name)
        else:
            self._tracer = None

    async def before_node(self, ctx: MiddlewareContext) -> None:
        if self._tracer and OTEL_AVAILABLE:
            span = self._tracer.start_span(f"node.{ctx.node_name}")
            span.set_attribute("node.name", ctx.node_name)
            self._spans[ctx.node_name] = span

    async def after_node(self, ctx: MiddlewareContext) -> None:
        span = self._spans.pop(ctx.node_name, None)
        if span and OTEL_AVAILABLE:
            span.set_attribute("node.status", "completed")
            span.end()

    async def on_error(self, ctx: MiddlewareContext, error: Exception) -> None:
        span = self._spans.pop(ctx.node_name, None)
        if span and OTEL_AVAILABLE:
            span.set_attribute("node.status", "failed")
            span.record_exception(error)
            span.end()


# ---------------------------------------------------------------------------
# Graph Nodes and Edges
# ---------------------------------------------------------------------------

NodeFunction = Callable[[GraphState], Any]


class Node:
    def __init__(
        self,
        name: str,
        func: NodeFunction,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.func = func
        self.metadata: Dict[str, Any] = metadata or {}
        self.status: NodeStatus = NodeStatus.PENDING

    async def execute(self, state: GraphState) -> Any:
        self.status = NodeStatus.RUNNING
        try:
            if asyncio.iscoroutinefunction(self.func):
                result = await self.func(state)
            else:
                result = self.func(state)
            self.status = NodeStatus.COMPLETED
            return result
        except Exception as e:
            self.status = NodeStatus.FAILED
            raise

    def reset(self) -> None:
        self.status = NodeStatus.PENDING

    def __repr__(self) -> str:
        return f"Node(name={self.name!r}, status={self.status})"


@dataclass
class Edge:
    source: str
    target: str
    edge_type: EdgeType = EdgeType.DEFAULT
    condition: Optional[Callable[[GraphState], bool]] = None
    weight: float = 1.0

    def is_traversable(self, state: GraphState) -> bool:
        if self.edge_type == EdgeType.CONDITIONAL and self.condition:
            return self.condition(state)
        return True


# ---------------------------------------------------------------------------
# Graph Engine
# ---------------------------------------------------------------------------

class Graph:
    def __init__(self, name: str = "default"):
        self.name = name
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._entry_point: Optional[str] = None
        self._end_points: Set[str] = set()
        self._middlewares: List[Middleware] = []

    def add_node(self, name: str, func: NodeFunction, metadata: Optional[Dict[str, Any]] = None) -> "Graph":
        self._nodes[name] = Node(name=name, func=func, metadata=metadata or {})
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType = EdgeType.DEFAULT,
        condition: Optional[Callable[[GraphState], bool]] = None,
        weight: float = 1.0,
    ) -> "Graph":
        self._validate_node_exists(source)
        self._validate_node_exists(target)
        self._edges.append(Edge(source=source, target=target, edge_type=edge_type, condition=condition, weight=weight))
        return self

    def add_conditional_edge(
        self,
        source: str,
        target: str,
        condition: Callable[[GraphState], bool],
    ) -> "Graph":
        return self.add_edge(source, target, EdgeType.CONDITIONAL, condition)

    def set_entry_point(self, node_name: str) -> "Graph":
        self._validate_node_exists(node_name)
        self._entry_point = node_name
        return self

    def set_end_point(self, node_name: str) -> "Graph":
        self._validate_node_exists(node_name)
        self._end_points.add(node_name)
        return self

    def add_middleware(self, middleware: Middleware) -> "Graph":
        self._middlewares.append(middleware)
        return self

    def _validate_node_exists(self, name: str) -> None:
        if name not in self._nodes:
            raise NodeNotFoundError(f"Node '{name}' not found in graph")

    def _get_outgoing_edges(self, node_name: str) -> List[Edge]:
        return [e for e in self._edges if e.source == node_name]

    def _detect_cycles(self) -> bool:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for edge in self._get_outgoing_edges(node):
                if edge.target not in visited:
                    if dfs(edge.target):
                        return True
                elif edge.target in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        for node_name in self._nodes:
            if node_name not in visited:
                if dfs(node_name):
                    return True
        return False

    def validate(self) -> None:
        if not self._entry_point:
            raise GraphError("No entry point set")
        if self._detect_cycles():
            raise CycleDetectedError("Graph contains cycles")

    def reset(self) -> None:
        for node in self._nodes.values():
            node.reset()

    async def _run_middlewares_before(self, ctx: MiddlewareContext) -> None:
        for mw in self._middlewares:
            await mw.before_node(ctx)

    async def _run_middlewares_after(self, ctx: MiddlewareContext) -> None:
        for mw in self._middlewares:
            await mw.after_node(ctx)

    async def _run_middlewares_error(self, ctx: MiddlewareContext, error: Exception) -> None:
        for mw in self._middlewares:
            await mw.on_error(ctx, error)

    async def _execute_node(self, node: Node, state: GraphState) -> Any:
        ctx = MiddlewareContext(node_name=node.name, state=state)
        await self._run_middlewares_before(ctx)
        try:
            result = await node.execute(state)
            await self._run_middlewares_after(ctx)
            return result
        except Exception as e:
            ctx.error = e
            await self._run_middlewares_error(ctx, e)
            raise

    async def execute(self, state: Optional[GraphState] = None) -> GraphState:
        self.validate()
        self.reset()
        if state is None:
            state = GraphState()

        current_node_name = self._entry_point
        visited: Set[str] = set()

        while current_node_name:
            if current_node_name in visited:
                break
            visited.add(current_node_name)

            node = self._nodes[current_node_name]
            await self._execute_node(node, state)

            if current_node_name in self._end_points:
                break

            outgoing = self._get_outgoing_edges(current_node_name)
            next_node_name = None

            parallel_edges = [e for e in outgoing if e.edge_type == EdgeType.PARALLEL and e.is_traversable(state)]
            if parallel_edges:
                await self._execute_parallel(parallel_edges, state, visited)
                break

            for edge in outgoing:
                if edge.is_traversable(state):
                    next_node_name = edge.target
                    break

            current_node_name = next_node_name

        return state

    async def _execute_parallel(self, edges: List[Edge], state: GraphState, visited: Set[str]) -> None:
        tasks = []
        for edge in edges:
            if edge.target not in visited:
                node = self._nodes[edge.target]
                tasks.append(self._execute_node(node, state))
        if tasks:
            await asyncio.gather(*tasks)

    def get_node(self, name: str) -> Node:
        self._validate_node_exists(name)
        return self._nodes[name]

    def get_nodes(self) -> Dict[str, Node]:
        return dict(self._nodes)

    def get_edges(self) -> List[Edge]:
        return list(self._edges)

    def __repr__(self) -> str:
        return f"Graph(name={self.name!r}, nodes={list(self._nodes.keys())})"


# ---------------------------------------------------------------------------
# LLM Directed Graph Execution
# ---------------------------------------------------------------------------

class LLMRouter:
    def __init__(self, inference_client: "BaseInferenceClient", system_prompt: Optional[str] = None):
        self._client = inference_client
        self._system_prompt = system_prompt or (
            "You are a routing assistant. Given the current state, "
            "decide which node to execute next. Respond with only the node name."
        )

    async def route(self, state: GraphState, available_nodes: List[str]) -> Optional[str]:
        messages = [
            Message(role=MessageRole.SYSTEM, content=self._system_prompt),
            Message(
                role=MessageRole.USER,
                content=(
                    f"Current state: {json.dumps(state.to_dict())}\n"
                    f"Available nodes: {available_nodes}\n"
                    "Which node should execute next? Reply with only the node name or 'END' to stop."
                ),
            ),
        ]
        response = await self._client.complete(messages=messages)
        chosen = response.content.strip()
        if chosen == "END" or chosen not in available_nodes:
            return None
        return chosen


class LLMDirectedGraph(Graph):
    def __init__(self, name: str = "llm_directed", router: Optional[LLMRouter] = None):
        super().__init__(name=name)
        self._router = router

    def set_router(self, router: LLMRouter) -> "LLMDirectedGraph":
        self._router = router
        return self

    async def execute(self, state: Optional[GraphState] = None) -> GraphState:
        if not self._router:
            return await super().execute(state)

        if state is None:
            state = GraphState()

        self.reset()
        current_node_name = self._entry_point
        if not current_node_name:
            raise GraphError("No entry point set")

        visited_count: Dict[str, int] = defaultdict(int)
        max_visits = 10

        while current_node_name:
            if visited_count[current_node_name] >= max_visits:
                break
            visited_count[current_node_name] += 1

            node = self._nodes[current_node_name]
            await self._execute_node(node, state)

            if current_node_name in self._end_points:
                break

            available = [
                e.target for e in self._get_outgoing_edges(current_node_name)
                if e.is_traversable(state)
            ]
            if not available:
                break

            current_node_name = await self._router.route(state, available)

        return state


# ---------------------------------------------------------------------------
# Cache System
# ---------------------------------------------------------------------------

class BaseCache(ABC):
    def __init__(self, prefix: str = "", suffix: str = ""):
        self._prefix = prefix
        self._suffix = suffix

    def _make_key(self, key: str) -> str:
        parts = []
        if self._prefix:
            parts.append(self._prefix)
        parts.append(key)
        if self._suffix:
            parts.append(self._suffix)
        return ":".join(parts)

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def get_all(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass

    @abstractmethod
    async def publish(self, mailbox: str, message: Any) -> None:
        pass

    @abstractmethod
    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        pass


class InMemoryCache(BaseCache):
    def __init__(self, prefix: str = "", suffix: str = ""):
        super().__init__(prefix=prefix, suffix=suffix)
        self._store: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        self._mailboxes: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    def _is_expired(self, full_key: str) -> bool:
        if full_key in self._expiry:
            return time.time() > self._expiry[full_key]
        return False

    async def get(self, key: str) -> Optional[Any]:
        full_key = self._make_key(key)
        if self._is_expired(full_key):
            del self._store[full_key]
            del self._expiry[full_key]
            return None
        raw = self._store.get(full_key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        full_key = self._make_key(key)
        self._store[full_key] = json.dumps(value)
        if ttl is not None:
            self._expiry[full_key] = time.time() + ttl
        elif full_key in self._expiry:
            del self._expiry[full_key]

    async def delete(self, key: str) -> None:
        full_key = self._make_key(key)
        self._store.pop(full_key, None)
        self._expiry.pop(full_key, None)

    async def exists(self, key: str) -> bool:
        full_key = self._make_key(key)
        if self._is_expired(full_key):
            self._store.pop(full_key, None)
            self._expiry.pop(full_key, None)
            return False
        return full_key in self._store

    async def get_all(self) -> Dict[str, Any]:
        result = {}
        expired_keys = []
        for full_key, raw in self._store.items():
            if self._is_expired(full_key):
                expired_keys.append(full_key)
                continue
            result[full_key] = json.loads(raw)
        for k in expired_keys:
            del self._store[k]
            self._expiry.pop(k, None)
        return result

    async def clear(self) -> None:
        self._store.clear()
        self._expiry.clear()

    async def publish(self, mailbox: str, message: Any) -> None:
        await self._mailboxes[mailbox].put(message)

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        queue = self._mailboxes[mailbox]
        while True:
            message = await queue.get()
            yield message


class RedisCache(BaseCache):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "",
        suffix: str = "",
    ):
        super().__init__(prefix=prefix, suffix=suffix)
        if not REDIS_AVAILABLE:
            raise ImportError("redis package is required for RedisCache. Install with: pip install redis")
        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._client: Optional[Any] = None
        self._pubsub: Optional[Any] = None

    async def _get_client(self) -> Any:
        if self._client is None:
            self._client = aioredis.Redis(
                host=self._host,
                port=self._port,
                db=self._db,
                password=self._password,
                decode_responses=True,
            )
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        client = await self._get_client()
        full_key = self._make_key(key)
        raw = await client.get(full_key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        client = await self._get_client()
        full_key = self._make_key(key)
        serialized = json.dumps(value)
        if ttl is not None:
            await client.setex(full_key, ttl, serialized)
        else:
            await client.set(full_key, serialized)

    async def delete(self, key: str) -> None:
        client = await self._get_client()
        full_key = self._make_key(key)
        await client.delete(full_key)

    async def exists(self, key: str) -> bool:
        client = await self._get_client()
        full_key = self._make_key(key)
        return bool(await client.exists(full_key))

    async def get_all(self) -> Dict[str, Any]:
        client = await self._get_client()
        pattern = self._make_key("*")
        keys = await client.keys(pattern)
        if not keys:
            return {}
        values = await client.mget(*keys)
        result = {}
        for k, v in zip(keys, values):
            if v is not None:
                result[k] = json.loads(v)
        return result

    async def clear(self) -> None:
        client = await self._get_client()
        pattern = self._make_key("*")
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)

    async def publish(self, mailbox: str, message: Any) -> None:
        client = await self._get_client()
        await client.publish(mailbox, json.dumps(message))

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        client = await self._get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(mailbox)
        try:
            async for raw_message in pubsub.listen():
                if raw_message["type"] == "message":
                    yield json.loads(raw_message["data"])
        finally:
            await pubsub.unsubscribe(mailbox)
            await pubsub.close()

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None


# ---------------------------------------------------------------------------
# Inference Clients
# ---------------------------------------------------------------------------

class BaseInferenceClient(ABC):
    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        cache: Optional[BaseCache] = None,
        enable_prompt_caching: bool = False,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self._cache = cache
        self._enable_prompt_caching = enable_prompt_caching
        self._total_usage = TokenUsage()
        self._tracer = None
        if OTEL_AVAILABLE:
            self._tracer = trace.get_tracer("inference_client")

    def _make_cache_key(self, messages: List[Message], **kwargs: Any) -> str:
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            **kwargs,
        }
        return f"inference:{hash(json.dumps(payload, sort_keys=True))}"

    async def _get_cached_response(self, cache_key: str) -> Optional[InferenceResponse]:
        if self._cache is None:
            return None
        cached = await self._cache.get(cache_key)
        if cached:
            usage = TokenUsage(**cached.get("usage", {}))
            return InferenceResponse(
                content=cached["content"],
                model=cached["model"],
                usage=usage,
                tool_calls=cached.get("tool_calls"),
                finish_reason=cached.get("finish_reason"),
            )
        return None

    async def _store_cached_response(self, cache_key: str, response: InferenceResponse) -> None:
        if self._cache is None:
            return
        await self._cache.set(cache_key, {
            "content": response.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "cached_tokens": response.usage.cached_tokens,
            },
            "tool_calls": response.tool_calls,
            "finish_reason": response.finish_reason,
        })

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        pass

    def get_total_usage(self) -> TokenUsage:
        return self._total_usage

    def reset_usage(self) -> None:
        self._total_usage = TokenUsage()


class MockInferenceClient(BaseInferenceClient):
    def __init__(
        self,
        model: str = "mock-model",
        response_template: str = "Mock response for: {content}",
        cache: Optional[BaseCache] = None,
        enable_prompt_caching: bool = False,
    ):
        super().__init__(
            model=model,
            cache=cache,
            enable_prompt_caching=enable_prompt_caching,
        )
        self._response_template = response_template
        self._call_count = 0

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        cache_key = self._make_cache_key(messages, temperature=temperature)
        cached = await self._get_cached_response(cache_key)
        if cached:
            cached.usage.cached_tokens = cached.usage.prompt_tokens
            return cached

        self._call_count += 1
        last_user_message = ""
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                last_user_message = msg.content
                break

        content = self._response_template.format(content=last_user_message)
        usage = TokenUsage(
            prompt_tokens=len(last_user_message.split()),
            completion_tokens=len(content.split()),
            total_tokens=len(last_user_message.split()) + len(content.split()),
        )
        self._total_usage = self._total_usage + usage

        tool_calls = None
        if tools:
            tool_calls = [
                {
                    "id": str(uuid.uuid4()),
                    "type": "function",
                    "function": {
                        "name": tools[0].name,
                        "arguments": json.dumps({}),
                    },
                }
            ]

        response = InferenceResponse(
            content=content,
            model=self.model,
            usage=usage,
            tool_calls=tool_calls,
            finish_reason="stop" if not tool_calls else "tool_calls",
        )
        await self._store_cached_response(cache_key, response)
        return response

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        response = await self.complete(messages, tools, temperature, max_tokens, **kwargs)
        words = response.content.split()
        for i, word in enumerate(words):
            is_last = i == len(words) - 1
            yield StreamChunk(
                content=word + ("" if is_last else " "),
                finish_reason="stop" if is_last else None,
                usage=response.usage if is_last else None,
            )
            await asyncio.sleep(0)

    def get_call_count(self) -> int:
        return self._call_count


class OpenAIInferenceClient(BaseInferenceClient):
    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        cache: Optional[BaseCache] = None,
        enable_prompt_caching: bool = False,
        organization: Optional[str] = None,
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            cache=cache,
            enable_prompt_caching=enable_prompt_caching,
        )
        self._organization = organization
        self._client = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                kwargs: Dict[str, Any] = {}
                if self.api_key:
                    kwargs["api_key"] = self.api_key
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                if self._organization:
                    kwargs["organization"] = self._organization
                self._client = AsyncOpenAI(**kwargs)
            except ImportError:
                raise ImportError("openai package is required. Install with: pip install openai")
        return self._client

    def _build_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in messages]

    def _build_tools(self, tools: Optional[List[ToolDefinition]]) -> Optional[List[Dict[str, Any]]]:
        if not tools:
            return None
        return [t.to_dict() for t in tools]

    def _parse_usage(self, usage_obj: Any) -> TokenUsage:
        if usage_obj is None:
            return TokenUsage()
        cached = 0
        if hasattr(usage_obj, "prompt_tokens_details") and usage_obj.prompt_tokens_details:
            cached = getattr(usage_obj.prompt_tokens_details, "cached_tokens", 0) or 0
        return TokenUsage(
            prompt_tokens=getattr(usage_obj, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage_obj, "completion_tokens", 0) or 0,
            total_tokens=getattr(usage_obj, "total_tokens", 0) or 0,
            cached_tokens=cached,
        )

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        cache_key = self._make_cache_key(messages, temperature=temperature)
        cached = await self._get_cached_response(cache_key)
        if cached:
            return cached

        client = self._get_client()
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": self._build_messages(messages),
            "temperature": temperature,
        }
        if max_tokens:
            params["max_tokens"] = max_tokens
        built_tools = self._build_tools(tools)
        if built_tools:
            params["tools"] = built_tools
        params.update(kwargs)

        span = None
        if self._tracer and OTEL_AVAILABLE:
            span = self._tracer.start_span("openai.complete")
            span.set_attribute("llm.model", self.model)

        try:
            raw_response = await client.chat.completions.create(**params)
            choice = raw_response.choices[0]
            usage = self._parse_usage(raw_response.usage)
            self._total_usage = self._total_usage + usage

            tool_calls = None
            if choice.message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in choice.message.tool_calls
                ]

            response = InferenceResponse(
                content=choice.message.content or "",
                model=raw_response.model,
                usage=usage,
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason,
                raw=raw_response.model_dump() if hasattr(raw_response, "model_dump") else None,
            )

            if span and OTEL_AVAILABLE:
                span.set_attribute("llm.prompt_tokens", usage.prompt_tokens)
                span.set_attribute("llm.completion_tokens", usage.completion_tokens)
                span.end()

            await self._store_cached_response(cache_key, response)
            return response

        except Exception as e:
            if span and OTEL_AVAILABLE:
                span.record_exception(e)
                span.end()
            raise InferenceError(f"OpenAI completion failed: {e}") from e

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        client = self._get_client()
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": self._build_messages(messages),
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if max_tokens:
            params["max_tokens"] = max_tokens
        built_tools = self._build_tools(tools)
        if built_tools:
            params["tools"] = built_tools
        params.update(kwargs)

        try:
            async with await client.chat.completions.create(**params) as stream:
                async for chunk in stream:
                    if not chunk.choices:
                        if chunk.usage:
                            usage = self._parse_usage(chunk.usage)
                            self._total_usage = self._total_usage + usage
                            yield StreamChunk(content="", usage=usage)
                        continue
                    choice = chunk.choices[0]
                    delta = choice.delta
                    content = delta.content or ""
                    finish_reason = choice.finish_reason
                    yield StreamChunk(
                        content=content,
                        finish_reason=finish_reason,
                    )
        except Exception as e:
            raise InferenceError(f"OpenAI streaming failed: {e}") from e


class AnthropicInferenceClient(BaseInferenceClient):
    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        cache: Optional[BaseCache] = None,
        enable_prompt_caching: bool = False,
        max_tokens: int = 4096,
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            cache=cache,
            enable_prompt_caching=enable_prompt_caching,
        )
        self._default_max_tokens = max_tokens
        self._client = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                kwargs: Dict[str, Any] = {}
                if self.api_key:
                    kwargs["api_key"] = self.api_key
                self._client = AsyncAnthropic(**kwargs)
            except ImportError:
                raise ImportError("anthropic package is required. Install with: pip install anthropic")
        return self._client

    def _build_messages_and_system(
        self, messages: List[Message]
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        system_prompt = None
        anthropic_messages = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_prompt = msg.content
            elif msg.role == MessageRole.TOOL:
                anthropic_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content,
                        }
                    ],
                })
            else:
                role = "user" if msg.role == MessageRole.USER else "assistant"
                content: Any = msg.content
                if msg.tool_calls:
                    content = [{"type": "text", "text": msg.content}] if msg.content else []
                    for tc in msg.tool_calls:
                        content.append({
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "input": json.loads(tc["function"]["arguments"]),
                        })
                anthropic_messages.append({"role": role, "content": content})
        return system_prompt, anthropic_messages

    def _build_tools(self, tools: Optional[List[ToolDefinition]]) -> Optional[List[Dict[str, Any]]]:
        if not tools:
            return None
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]

    def _parse_usage(self, usage_obj: Any) -> TokenUsage:
        if usage_obj is None:
            return TokenUsage()
        cached = getattr(usage_obj, "cache_read_input_tokens", 0) or 0
        return TokenUsage(
            prompt_tokens=getattr(usage_obj, "input_tokens", 0) or 0,
            completion_tokens=getattr(usage_obj, "output_tokens", 0) or 0,
            total_tokens=(getattr(usage_obj, "input_tokens", 0) or 0) + (getattr(usage_obj, "output_tokens", 0) or 0),
            cached_tokens=cached,
        )

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        cache_key = self._make_cache_key(messages, temperature=temperature)
        cached = await self._get_cached_response(cache_key)
        if cached:
            return cached

        client = self._get_client()
        system_prompt, anthropic_messages = self._build_messages_and_system(messages)

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens or self._default_max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            params["system"] = system_prompt
        built_tools = self._build_tools(tools)
        if built_tools:
            params["tools"] = built_tools
        params.update(kwargs)

        try:
            raw_response = await client.messages.create(**params)
            usage = self._parse_usage(raw_response.usage)
            self._total_usage = self._total_usage + usage

            content = ""
            tool_calls = None
            for block in raw_response.content:
                if hasattr(block, "text"):
                    content += block.text
                elif hasattr(block, "type") and block.type == "tool_use":
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append({
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.input),
                        },
                    })

            response = InferenceResponse(
                content=content,
                model=raw_response.model,
                usage=usage,
                tool_calls=tool_calls,
                finish_reason=raw_response.stop_reason,
            )
            await self._store_cached_response(cache_key, response)
            return response

        except Exception as e:
            raise InferenceError(f"Anthropic completion failed: {e}") from e

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        client = self._get_client()
        system_prompt, anthropic_messages = self._build_messages_and_system(messages)

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens or self._default_max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            params["system"] = system_prompt
        built_tools = self._build_tools(tools)
        if built_tools:
            params["tools"] = built_tools
        params.update(kwargs)

        try:
            async with client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield StreamChunk(content=text)
                final = await stream.get_final_message()
                usage = self._parse_usage(final.usage)
                self._total_usage = self._total_usage + usage
                yield StreamChunk(content="", finish_reason=final.stop_reason, usage=usage)
        except Exception as e:
            raise InferenceError(f"Anthropic streaming failed: {e}") from e


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Agent:
    def __init__(
        self,
        name: str,
        inference_client: BaseInferenceClient,
        system_prompt: Optional[str] = None,
        tools: Optional[List[ToolDefinition]] = None,
        cache: Optional[BaseCache] = None,
        max_iterations: int = 10,
    ):
        self.name = name
        self._client = inference_client
        self._system_prompt = system_prompt
        self._tools = tools or []
        self._cache = cache
        self._max_iterations = max_iterations
        self._conversation_history: List[Message] = []
        self._tool_handlers: Dict[str, Callable] = {}

    def register_tool_handler(self, tool_name: str, handler: Callable) -> None:
        self._tool_handlers[tool_name] = handler

    def _build_messages(self, user_message: str) -> List[Message]:
        messages = []
        if self._system_prompt:
            messages.append(Message(role=MessageRole.SYSTEM, content=self._system_prompt))
        messages.extend(self._conversation_history)
        messages.append(Message(role=MessageRole.USER, content=user_message))
        return messages

    async def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Message]:
        tool_messages = []
        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            tool_args = json.loads(tc["function"]["arguments"])
            handler = self._tool_handlers.get(tool_name)
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(**tool_args)
                else:
                    result = handler(**tool_args)
                result_str = json.dumps(result) if not isinstance(result, str) else result
            else:
                result_str = json.dumps({"error": f"No handler for tool: {tool_name}"})
            tool_messages.append(
                Message(
                    role=MessageRole.TOOL,
                    content=result_str,
                    tool_call_id=tc["id"],
                    name=tool_name,
                )
            )
        return tool_messages

    async def run(self, user_message: str) -> str:
        messages = self._build_messages(user_message)
        self._conversation_history.append(Message(role=MessageRole.USER, content=user_message))

        for _ in range(self._max_iterations):
            response = await self._client.complete(
                messages=messages,
                tools=self._tools if self._tools else None,
            )

            if response.tool_calls:
                assistant_msg = Message(
                    role=MessageRole.ASSISTANT,
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
                messages.append(assistant_msg)
                self._conversation_history.append(assistant_msg)

                tool_messages = await self._handle_tool_calls(response.tool_calls)
                messages.extend(tool_messages)
                self._conversation_history.extend(tool_messages)
            else:
                assistant_msg = Message(role=MessageRole.ASSISTANT, content=response.content)
                self._conversation_history.append(assistant_msg)
                return response.content

        return "Max iterations reached without a final response."

    async def stream_run(self, user_message: str) -> AsyncGenerator[str, None]:
        messages = self._build_messages(user_message)
        self._conversation_history.append(Message(role=MessageRole.USER, content=user_message))

        full_content = ""
        async for chunk in self._client.stream(messages=messages, tools=self._tools if self._tools else None):
            if chunk.content:
                full_content += chunk.content
                yield chunk.content

        self._conversation_history.append(Message(role=MessageRole.ASSISTANT, content=full_content))

    def clear_history(self) -> None:
        self._conversation_history.clear()

    def get_history(self) -> List[Message]:
        return list(self._conversation_history)

    def get_usage(self) -> TokenUsage:
        return self._client.get_total_usage()


# ---------------------------------------------------------------------------
# Graph Builder (Fluent API)
# ---------------------------------------------------------------------------

class GraphBuilder:
    def __init__(self, name: str = "default"):
        self._graph = Graph(name=name)

    def node(self, name: str, func: NodeFunction, metadata: Optional[Dict[str, Any]] = None) -> "GraphBuilder":
        self._graph.add_node(name, func, metadata)
        return self

    def edge(self, source: str, target: str) -> "GraphBuilder":
        self._graph.add_edge(source, target)
        return self

    def conditional_edge(self, source: str, target: str, condition: Callable[[GraphState], bool]) -> "GraphBuilder":
        self._graph.add_conditional_edge(source, target, condition)
        return self

    def parallel_edge(self, source: str, target: str) -> "GraphBuilder":
        self._graph.add_edge(source, target, EdgeType.PARALLEL)
        return self

    def entry(self, node_name: str) -> "GraphBuilder":
        self._graph.set_entry_point(node_name)
        return self

    def end(self, node_name: str) -> "GraphBuilder":
        self._graph.set_end_point(node_name)
        return self

    def middleware(self, mw: Middleware) -> "GraphBuilder":
        self._graph.add_middleware(mw)
        return self

    def build(self) -> Graph:
        return self._graph


# ---------------------------------------------------------------------------
# Pipeline (Sequential Graph Helper)
# ---------------------------------------------------------------------------

class Pipeline:
    def __init__(self, name: str = "pipeline"):
        self._name = name
        self._steps: List[Tuple[str, NodeFunction]] = []
        self._middlewares: List[Middleware] = []

    def add_step(self, name: str, func: NodeFunction) -> "Pipeline":
        self._steps.append((name, func))
        return self

    def add_middleware(self, mw: Middleware) -> "Pipeline":
        self._middlewares.append(mw)
        return self

    def build(self) -> Graph:
        if not self._steps:
            raise GraphError("Pipeline has no steps")

        builder = GraphBuilder(name=self._name)
        for name, func in self._steps:
            builder.node(name, func)

        builder.entry(self._steps[0][0])
        builder.end(self._steps[-1][0])

        for i in range(len(self._steps) - 1):
            builder.edge(self._steps[i][0], self._steps[i + 1][0])

        for mw in self._middlewares:
            builder.middleware(mw)

        return builder.build()

    async def execute(self, state: Optional[GraphState] = None) -> GraphState:
        graph = self.build()
        return await graph.execute(state)


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "NodeStatus",
    "EdgeType",
    "MessageRole",
    # Exceptions
    "GraphError",
    "CycleDetectedError",
    "NodeNotFoundError",
    "InferenceError",
    "CacheError",
    # Data Models
    "Message",
    "TokenUsage",
    "ToolDefinition",
    "InferenceResponse",
    "StreamChunk",
    # Graph
    "GraphState",
    "Node",
    "Edge",
    "Graph",
    "LLMRouter",
    "LLMDirectedGraph",
    "GraphBuilder",
    "Pipeline",
    # Middleware
    "MiddlewareContext",
    "Middleware",
    "LoggingMiddleware",
    "TimingMiddleware",
    "OpenTelemetryMiddleware",
    # Cache
    "BaseCache",
    "InMemoryCache",
    "RedisCache",
    # Inference
    "BaseInferenceClient",
    "MockInferenceClient",
    "OpenAIInferenceClient",
    "AnthropicInferenceClient",
    # Agent
    "Agent",
]