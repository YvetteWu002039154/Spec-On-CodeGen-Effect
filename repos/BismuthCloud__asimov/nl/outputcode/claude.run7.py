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
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from opentelemetry import trace
    from opentelemetry.trace import Span, Tracer
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


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


class ExecutionError(GraphError):
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
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.name:
            d["name"] = self.name
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
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


@dataclass
class GraphState:
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def update(self, updates: Dict[str, Any]) -> None:
        self.data.update(updates)

    def snapshot(self) -> "GraphState":
        import copy
        return GraphState(
            data=copy.deepcopy(self.data),
            metadata=copy.deepcopy(self.metadata),
        )


@dataclass
class NodeResult:
    node_id: str
    status: NodeStatus
    output: Any = None
    error: Optional[Exception] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphSnapshot:
    snapshot_id: str
    timestamp: float
    state: GraphState
    completed_nodes: Set[str]
    failed_nodes: Set[str]

    @classmethod
    def create(
        cls,
        state: GraphState,
        completed_nodes: Set[str],
        failed_nodes: Set[str],
    ) -> "GraphSnapshot":
        return cls(
            snapshot_id=str(uuid.uuid4()),
            timestamp=time.time(),
            state=state.snapshot(),
            completed_nodes=set(completed_nodes),
            failed_nodes=set(failed_nodes),
        )


# ---------------------------------------------------------------------------
# Cache Abstraction
# ---------------------------------------------------------------------------

class AbstractCache(ABC):
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
    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        pass

    @abstractmethod
    async def clear(self, pattern: str = "*") -> int:
        pass

    @abstractmethod
    async def publish(self, mailbox: str, message: Any) -> None:
        pass

    @abstractmethod
    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        pass


class InMemoryCache(AbstractCache):
    def __init__(self, prefix: str = "", suffix: str = ""):
        self._store: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        self._mailboxes: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self.prefix = prefix
        self.suffix = suffix

    def _make_key(self, key: str) -> str:
        parts = []
        if self.prefix:
            parts.append(self.prefix)
        parts.append(key)
        if self.suffix:
            parts.append(self.suffix)
        return ":".join(parts)

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
        return self._store.get(full_key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        full_key = self._make_key(key)
        self._store[full_key] = value
        if ttl is not None:
            self._expiry[full_key] = time.time() + ttl

    async def delete(self, key: str) -> None:
        full_key = self._make_key(key)
        self._store.pop(full_key, None)
        self._expiry.pop(full_key, None)

    async def exists(self, key: str) -> bool:
        full_key = self._make_key(key)
        if self._is_expired(full_key):
            return False
        return full_key in self._store

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        import fnmatch
        result = {}
        for k, v in list(self._store.items()):
            if not self._is_expired(k) and fnmatch.fnmatch(k, pattern):
                result[k] = v
        return result

    async def clear(self, pattern: str = "*") -> int:
        import fnmatch
        keys_to_delete = [
            k for k in list(self._store.keys())
            if fnmatch.fnmatch(k, pattern)
        ]
        for k in keys_to_delete:
            del self._store[k]
            self._expiry.pop(k, None)
        return len(keys_to_delete)

    async def publish(self, mailbox: str, message: Any) -> None:
        await self._mailboxes[mailbox].put(message)

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        queue = self._mailboxes[mailbox]
        while True:
            message = await queue.get()
            yield message


class RedisCache(AbstractCache):
    def __init__(
        self,
        url: str = "redis://localhost:6379",
        prefix: str = "",
        suffix: str = "",
        db: int = 0,
    ):
        if not REDIS_AVAILABLE:
            raise ImportError("redis package is required for RedisCache")
        self._url = url
        self._db = db
        self.prefix = prefix
        self.suffix = suffix
        self._client: Optional[Any] = None
        self._pubsub_client: Optional[Any] = None

    async def _get_client(self) -> Any:
        if self._client is None:
            self._client = aioredis.from_url(self._url, db=self._db, decode_responses=True)
        return self._client

    def _make_key(self, key: str) -> str:
        parts = []
        if self.prefix:
            parts.append(self.prefix)
        parts.append(key)
        if self.suffix:
            parts.append(self.suffix)
        return ":".join(parts)

    async def get(self, key: str) -> Optional[Any]:
        client = await self._get_client()
        full_key = self._make_key(key)
        raw = await client.get(full_key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

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

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        client = await self._get_client()
        keys = await client.keys(pattern)
        result = {}
        if keys:
            values = await client.mget(keys)
            for k, v in zip(keys, values):
                if v is not None:
                    try:
                        result[k] = json.loads(v)
                    except (json.JSONDecodeError, TypeError):
                        result[k] = v
        return result

    async def clear(self, pattern: str = "*") -> int:
        client = await self._get_client()
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
        return len(keys)

    async def publish(self, mailbox: str, message: Any) -> None:
        client = await self._get_client()
        serialized = json.dumps(message)
        await client.publish(mailbox, serialized)

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        client = await self._get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(mailbox)
        async for raw_message in pubsub.listen():
            if raw_message["type"] == "message":
                data = raw_message["data"]
                try:
                    yield json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    yield data

    async def close(self) -> None:
        if self._client:
            await self._client.close()


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class MiddlewareContext:
    def __init__(self, node_id: str, state: GraphState, metadata: Dict[str, Any]):
        self.node_id = node_id
        self.state = state
        self.metadata = metadata
        self.start_time: float = time.time()
        self.result: Optional[NodeResult] = None


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
    def __init__(self, logger: Optional[Any] = None):
        import logging
        self._logger = logger or logging.getLogger(__name__)

    async def before_node(self, ctx: MiddlewareContext) -> None:
        self._logger.info(f"[Graph] Starting node: {ctx.node_id}")

    async def after_node(self, ctx: MiddlewareContext) -> None:
        duration = (time.time() - ctx.start_time) * 1000
        status = ctx.result.status.value if ctx.result else "unknown"
        self._logger.info(
            f"[Graph] Completed node: {ctx.node_id} | status={status} | duration={duration:.2f}ms"
        )

    async def on_error(self, ctx: MiddlewareContext, error: Exception) -> None:
        self._logger.error(f"[Graph] Error in node: {ctx.node_id} | error={error}")


class TimingMiddleware(Middleware):
    def __init__(self):
        self.timings: Dict[str, float] = {}

    async def before_node(self, ctx: MiddlewareContext) -> None:
        ctx.metadata["_timing_start"] = time.time()

    async def after_node(self, ctx: MiddlewareContext) -> None:
        start = ctx.metadata.get("_timing_start", time.time())
        duration = (time.time() - start) * 1000
        self.timings[ctx.node_id] = duration
        if ctx.result:
            ctx.result.duration_ms = duration


class OpenTelemetryMiddleware(Middleware):
    def __init__(self, tracer_name: str = "agent_framework"):
        if not OTEL_AVAILABLE:
            raise ImportError("opentelemetry package is required")
        self._tracer: Tracer = trace.get_tracer(tracer_name)
        self._spans: Dict[str, Any] = {}

    async def before_node(self, ctx: MiddlewareContext) -> None:
        span = self._tracer.start_span(f"node.{ctx.node_id}")
        span.set_attribute("node.id", ctx.node_id)
        self._spans[ctx.node_id] = span
        ctx.metadata["_otel_span"] = span

    async def after_node(self, ctx: MiddlewareContext) -> None:
        span = self._spans.pop(ctx.node_id, None)
        if span:
            if ctx.result:
                span.set_attribute("node.status", ctx.result.status.value)
            span.end()

    async def on_error(self, ctx: MiddlewareContext, error: Exception) -> None:
        span = self._spans.pop(ctx.node_id, None)
        if span:
            span.record_exception(error)
            span.set_status(trace.StatusCode.ERROR, str(error))
            span.end()


# ---------------------------------------------------------------------------
# Graph Nodes and Edges
# ---------------------------------------------------------------------------

NodeFunction = Callable[[GraphState], Any]


class Node:
    def __init__(
        self,
        node_id: str,
        func: Optional[NodeFunction] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.node_id = node_id
        self.func = func
        self.metadata: Dict[str, Any] = metadata or {}
        self._is_entry: bool = False
        self._is_exit: bool = False

    async def execute(self, state: GraphState) -> Any:
        if self.func is None:
            return None
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(state)
        return self.func(state)

    def __repr__(self) -> str:
        return f"Node(id={self.node_id})"


class Edge:
    def __init__(
        self,
        source: str,
        target: str,
        edge_type: EdgeType = EdgeType.DEFAULT,
        condition: Optional[Callable[[GraphState], bool]] = None,
        weight: float = 1.0,
    ):
        self.source = source
        self.target = target
        self.edge_type = edge_type
        self.condition = condition
        self.weight = weight

    async def is_active(self, state: GraphState) -> bool:
        if self.condition is None:
            return True
        if asyncio.iscoroutinefunction(self.condition):
            return await self.condition(state)
        return self.condition(state)

    def __repr__(self) -> str:
        return f"Edge({self.source} -> {self.target}, type={self.edge_type.value})"


class ConditionalEdge(Edge):
    def __init__(
        self,
        source: str,
        condition: Callable[[GraphState], str],
        target_map: Dict[str, str],
    ):
        super().__init__(source=source, target="", edge_type=EdgeType.CONDITIONAL)
        self._router = condition
        self.target_map = target_map

    async def resolve_target(self, state: GraphState) -> Optional[str]:
        if asyncio.iscoroutinefunction(self._router):
            key = await self._router(state)
        else:
            key = self._router(state)
        return self.target_map.get(key)

    async def is_active(self, state: GraphState) -> bool:
        target = await self.resolve_target(state)
        return target is not None


# ---------------------------------------------------------------------------
# Graph Engine
# ---------------------------------------------------------------------------

class Graph:
    def __init__(self, name: str = "graph"):
        self.name = name
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._entry_point: Optional[str] = None
        self._exit_points: Set[str] = set()
        self._middleware: List[Middleware] = []
        self._snapshots: List[GraphSnapshot] = []
        self._snapshot_enabled: bool = False

    def add_node(self, node: Node) -> "Graph":
        self._nodes[node.node_id] = node
        return self

    def add_edge(self, edge: Edge) -> "Graph":
        if edge.source not in self._nodes:
            raise NodeNotFoundError(f"Source node '{edge.source}' not found")
        if not isinstance(edge, ConditionalEdge) and edge.target not in self._nodes:
            raise NodeNotFoundError(f"Target node '{edge.target}' not found")
        self._edges.append(edge)
        return self

    def set_entry_point(self, node_id: str) -> "Graph":
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found")
        self._entry_point = node_id
        self._nodes[node_id]._is_entry = True
        return self

    def set_exit_point(self, node_id: str) -> "Graph":
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found")
        self._exit_points.add(node_id)
        self._nodes[node_id]._is_exit = True
        return self

    def add_middleware(self, middleware: Middleware) -> "Graph":
        self._middleware.append(middleware)
        return self

    def enable_snapshots(self, enabled: bool = True) -> "Graph":
        self._snapshot_enabled = enabled
        return self

    def _detect_cycles(self) -> bool:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for edge in self._edges:
                if edge.source == node_id and not isinstance(edge, ConditionalEdge):
                    neighbor = edge.target
                    if neighbor not in visited:
                        if dfs(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        return True
            rec_stack.discard(node_id)
            return False

        for node_id in self._nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False

    def validate(self) -> None:
        if not self._nodes:
            raise GraphError("Graph has no nodes")
        if self._entry_point is None:
            raise GraphError("Graph has no entry point")
        if self._detect_cycles():
            raise CycleDetectedError("Graph contains a cycle")

    async def _get_next_nodes(
        self, node_id: str, state: GraphState
    ) -> List[str]:
        next_nodes = []
        for edge in self._edges:
            if edge.source != node_id:
                continue
            if isinstance(edge, ConditionalEdge):
                target = await edge.resolve_target(state)
                if target:
                    next_nodes.append(target)
            else:
                if await edge.is_active(state):
                    next_nodes.append(edge.target)
        return next_nodes

    async def _run_middleware_before(self, ctx: MiddlewareContext) -> None:
        for mw in self._middleware:
            await mw.before_node(ctx)

    async def _run_middleware_after(self, ctx: MiddlewareContext) -> None:
        for mw in self._middleware:
            await mw.after_node(ctx)

    async def _run_middleware_error(
        self, ctx: MiddlewareContext, error: Exception
    ) -> None:
        for mw in self._middleware:
            await mw.on_error(ctx, error)

    async def _execute_node(
        self, node: Node, state: GraphState
    ) -> NodeResult:
        ctx = MiddlewareContext(
            node_id=node.node_id,
            state=state,
            metadata={},
        )
        await self._run_middleware_before(ctx)
        start = time.time()
        try:
            output = await node.execute(state)
            duration = (time.time() - start) * 1000
            result = NodeResult(
                node_id=node.node_id,
                status=NodeStatus.COMPLETED,
                output=output,
                duration_ms=duration,
            )
            ctx.result = result
            await self._run_middleware_after(ctx)
            return result
        except Exception as e:
            duration = (time.time() - start) * 1000
            result = NodeResult(
                node_id=node.node_id,
                status=NodeStatus.FAILED,
                error=e,
                duration_ms=duration,
            )
            ctx.result = result
            await self._run_middleware_error(ctx, e)
            return result

    async def execute(
        self,
        initial_state: Optional[GraphState] = None,
        max_steps: int = 1000,
    ) -> Tuple[GraphState, List[NodeResult]]:
        self.validate()
        state = initial_state or GraphState()
        results: List[NodeResult] = []
        completed: Set[str] = set()
        failed: Set[str] = set()
        current_node_id = self._entry_point
        steps = 0

        while current_node_id and steps < max_steps:
            if current_node_id in self._exit_points:
                node = self._nodes[current_node_id]
                result = await self._execute_node(node, state)
                results.append(result)
                if result.status == NodeStatus.COMPLETED:
                    completed.add(current_node_id)
                else:
                    failed.add(current_node_id)
                if self._snapshot_enabled:
                    self._snapshots.append(
                        GraphSnapshot.create(state, completed, failed)
                    )
                break

            if current_node_id not in self._nodes:
                raise NodeNotFoundError(f"Node '{current_node_id}' not found")

            node = self._nodes[current_node_id]
            result = await self._execute_node(node, state)
            results.append(result)

            if result.status == NodeStatus.FAILED:
                failed.add(current_node_id)
                if self._snapshot_enabled:
                    self._snapshots.append(
                        GraphSnapshot.create(state, completed, failed)
                    )
                raise ExecutionError(
                    f"Node '{current_node_id}' failed: {result.error}"
                ) from result.error

            completed.add(current_node_id)

            if self._snapshot_enabled:
                self._snapshots.append(
                    GraphSnapshot.create(state, completed, failed)
                )

            next_nodes = await self._get_next_nodes(current_node_id, state)
            if not next_nodes:
                break

            if len(next_nodes) == 1:
                current_node_id = next_nodes[0]
            else:
                parallel_results = await self._execute_parallel(
                    next_nodes, state
                )
                results.extend(parallel_results)
                for r in parallel_results:
                    if r.status == NodeStatus.FAILED:
                        failed.add(r.node_id)
                    else:
                        completed.add(r.node_id)
                break

            steps += 1

        return state, results

    async def _execute_parallel(
        self, node_ids: List[str], state: GraphState
    ) -> List[NodeResult]:
        tasks = []
        for node_id in node_ids:
            if node_id not in self._nodes:
                raise NodeNotFoundError(f"Node '{node_id}' not found")
            node = self._nodes[node_id]
            tasks.append(self._execute_node(node, state))
        return list(await asyncio.gather(*tasks))

    def get_snapshots(self) -> List[GraphSnapshot]:
        return list(self._snapshots)

    def restore_snapshot(self, snapshot_id: str) -> Optional[GraphSnapshot]:
        for snap in self._snapshots:
            if snap.snapshot_id == snapshot_id:
                return snap
        return None

    def __repr__(self) -> str:
        return (
            f"Graph(name={self.name}, nodes={len(self._nodes)}, "
            f"edges={len(self._edges)})"
        )


# ---------------------------------------------------------------------------
# Graph Builder (Fluent API)
# ---------------------------------------------------------------------------

class GraphBuilder:
    def __init__(self, name: str = "graph"):
        self._graph = Graph(name=name)

    def node(
        self,
        node_id: str,
        func: Optional[NodeFunction] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "GraphBuilder":
        self._graph.add_node(Node(node_id=node_id, func=func, metadata=metadata))
        return self

    def edge(
        self,
        source: str,
        target: str,
        condition: Optional[Callable[[GraphState], bool]] = None,
    ) -> "GraphBuilder":
        edge_type = EdgeType.CONDITIONAL if condition else EdgeType.DEFAULT
        self._graph.add_edge(
            Edge(source=source, target=target, edge_type=edge_type, condition=condition)
        )
        return self

    def conditional_edge(
        self,
        source: str,
        router: Callable[[GraphState], str],
        target_map: Dict[str, str],
    ) -> "GraphBuilder":
        self._graph.add_edge(
            ConditionalEdge(source=source, condition=router, target_map=target_map)
        )
        return self

    def entry(self, node_id: str) -> "GraphBuilder":
        self._graph.set_entry_point(node_id)
        return self

    def exit(self, node_id: str) -> "GraphBuilder":
        self._graph.set_exit_point(node_id)
        return self

    def middleware(self, mw: Middleware) -> "GraphBuilder":
        self._graph.add_middleware(mw)
        return self

    def snapshots(self, enabled: bool = True) -> "GraphBuilder":
        self._graph.enable_snapshots(enabled)
        return self

    def build(self) -> Graph:
        return self._graph


# ---------------------------------------------------------------------------
# Inference Clients
# ---------------------------------------------------------------------------

class BaseInferenceClient(ABC):
    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._total_usage = TokenUsage()

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

    def _accumulate_usage(self, usage: TokenUsage) -> None:
        self._total_usage = self._total_usage + usage


class OpenAIClient(BaseInferenceClient):
    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
        enable_prompt_caching: bool = False,
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.enable_prompt_caching = enable_prompt_caching
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        try:
            import openai
        except ImportError:
            raise ImportError("openai package is required for OpenAIClient")
        if self._client is None:
            kwargs: Dict[str, Any] = {
                "api_key": self.api_key,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
            }
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = openai.AsyncOpenAI(**kwargs)
        return self._client

    def _build_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        result = []
        for msg in messages:
            d = msg.to_dict()
            if self.enable_prompt_caching and msg.role == MessageRole.SYSTEM:
                d["content"] = [
                    {
                        "type": "text",
                        "text": msg.content,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            result.append(d)
        return result

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        client = self._get_client()
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": self._build_messages(messages),
            "temperature": temperature,
        }
        if max_tokens:
            params["max_tokens"] = max_tokens
        if tools:
            params["tools"] = [t.to_dict() for t in tools]
        params.update(kwargs)

        response = await client.chat.completions.create(**params)
        choice = response.choices[0]
        usage = TokenUsage(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            cached_tokens=getattr(
                getattr(response.usage, "prompt_tokens_details", None),
                "cached_tokens",
                0,
            ) or 0,
        )
        self._accumulate_usage(usage)
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
        return InferenceResponse(
            content=choice.message.content or "",
            model=response.model,
            usage=usage,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            raw=response.model_dump() if hasattr(response, "model_dump") else None,
        )

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
        if tools:
            params["tools"] = [t.to_dict() for t in tools]
        params.update(kwargs)

        async with await client.chat.completions.create(**params) as stream:
            async for chunk in stream:
                if not chunk.choices:
                    if chunk.usage:
                        usage = TokenUsage(
                            prompt_tokens=chunk.usage.prompt_tokens,
                            completion_tokens=chunk.usage.completion_tokens,
                            total_tokens=chunk.usage.total_tokens,
                        )
                        self._accumulate_usage(usage)
                        yield StreamChunk(content="", usage=usage)
                    continue
                choice = chunk.choices[0]
                delta = choice.delta
                content = delta.content or ""
                tool_calls = None
                if delta.tool_calls:
                    tool_calls = [
                        {
                            "index": tc.index,
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": getattr(tc.function, "name", None),
                                "arguments": getattr(tc.function, "arguments", ""),
                            },
                        }
                        for tc in delta.tool_calls
                    ]
                yield StreamChunk(
                    content=content,
                    finish_reason=choice.finish_reason,
                    tool_calls=tool_calls,
                )


class AnthropicClient(BaseInferenceClient):
    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
        enable_prompt_caching: bool = False,
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.enable_prompt_caching = enable_prompt_caching
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package is required for AnthropicClient")
        if self._client is None:
            kwargs: Dict[str, Any] = {
                "api_key": self.api_key,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
            }
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = anthropic.AsyncAnthropic(**kwargs)
        return self._client

    def _split_messages(
        self, messages: List[Message]
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        system_content = None
        chat_messages = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_content = msg.content
            else:
                chat_messages.append(msg.to_dict())
        return system_content, chat_messages

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        client = self._get_client()
        system_content, chat_messages = self._split_messages(messages)
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }
        if system_content:
            if self.enable_prompt_caching:
                params["system"] = [
                    {
                        "type": "text",
                        "text": system_content,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            else:
                params["system"] = system_content
        if tools:
            params["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.parameters,
                }
                for t in tools
            ]
        params.update(kwargs)

        response = await client.messages.create(**params)
        content_text = ""
        tool_calls = None
        for block in response.content:
            if hasattr(block, "text"):
                content_text += block.text
            elif hasattr(block, "type") and block.type == "tool_use":
                if tool_calls is None:
                    tool_calls = []
                tool_calls.append(
                    {
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.input),
                        },
                    }
                )
        usage = TokenUsage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            cached_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        )
        self._accumulate_usage(usage)
        return InferenceResponse(
            content=content_text,
            model=response.model,
            usage=usage,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason,
        )

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        client = self._get_client()
        system_content, chat_messages = self._split_messages(messages)
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }
        if system_content:
            params["system"] = system_content
        if tools:
            params["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.parameters,
                }
                for t in tools
            ]
        params.update(kwargs)

        async with client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                yield StreamChunk(content=text)
            final = await stream.get_final_message()
            usage = TokenUsage(
                prompt_tokens=final.usage.input_tokens,
                completion_tokens=final.usage.output_tokens,
                total_tokens=final.usage.input_tokens + final.usage.output_tokens,
            )
            self._accumulate_usage(usage)
            yield StreamChunk(
                content="",
                finish_reason=final.stop_reason,
                usage=usage,
            )


class MockInferenceClient(BaseInferenceClient):
    def __init__(
        self,
        model: str = "mock-model",
        responses: Optional[List[str]] = None,
        tool_call_responses: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(model=model)
        self._responses = responses or ["Mock response"]
        self._tool_call_responses = tool_call_responses or []
        self._call_count = 0

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        idx = self._call_count % len(self._responses)
        content = self._responses[idx]
        self._call_count += 1
        usage = TokenUsage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )
        self._accumulate_usage(usage)
        tool_calls = None
        if self._tool_call_responses and tools:
            tc_idx = (self._call_count - 1) % len(self._tool_call_responses)
            tool_calls = [self._tool_call_responses[tc_idx]]
        return InferenceResponse(
            content=content,
            model=self.model,
            usage=usage,
            tool_calls=tool_calls,
            finish_reason="stop",
        )

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        idx = self._call_count % len(self._responses)
        content = self._responses[idx]
        self._call_count += 1
        words = content.split()
        for i, word in enumerate(words):
            chunk_text = word + (" " if i < len(words) - 1 else "")
            yield StreamChunk(content=chunk_text)
            await asyncio.sleep(0)
        usage = TokenUsage(
            prompt_tokens=10,
            completion_tokens=len(words),
            total_tokens=10 + len(words),
        )
        self._accumulate_usage(usage)
        yield StreamChunk(content="", finish_reason="stop", usage=usage)


# ---------------------------------------------------------------------------
# LLM Directed Graph Execution
# ---------------------------------------------------------------------------

class LLMRouter:
    def __init__(
        self,
        client: BaseInferenceClient,
        system_prompt: Optional[str] = None,
    ):
        self._client = client
        self._system_prompt = system_prompt or (
            "You are a routing agent. Based on the current state, "
            "decide which node to execute next. Respond with only the node name."
        )

    async def route(
        self,
        state: GraphState,
        available_nodes: List[str],
        context: Optional[str] = None,
    ) -> Optional[str]:
        state_summary = json.dumps(state.data, indent=2, default=str)
        nodes_list = ", ".join(available_nodes)
        user_content = (
            f"Current state:\n{state_summary}\n\n"
            f"Available next nodes: {nodes_list}\n\n"
        )
        if context:
            user_content += f"Context: {context}\n\n"
        user_content += "Which node should execute next? Respond with only the node name."

        messages = [
            Message(role=MessageRole.SYSTEM, content=self._system_prompt),
            Message(role=MessageRole.USER, content=user_content),
        ]
        response = await self._client.complete(messages, temperature=0.0)
        chosen = response.content.strip()
        if chosen in available_nodes:
            return chosen
        for node in available_nodes:
            if node.lower() in chosen.lower():
                return node
        return None


class LLMDirectedGraph(Graph):
    def __init__(
        self,
        name: str = "llm_directed_graph",
        router: Optional[LLMRouter] = None,
    ):
        super().__init__(name=name)
        self._router = router
        self._routing_context: Optional[str] = None

    def set_router(self, router: LLMRouter) -> "LLMDirectedGraph":
        self._router = router
        return self

    def set_routing_context(self, context: str) -> "LLMDirectedGraph":
        self._routing_context = context
        return self

    async def _get_next_nodes(
        self, node_id: str, state: GraphState
    ) -> List[str]:
        static_next = await super()._get_next_nodes(node_id, state)
        if static_next or self._router is None:
            return static_next
        all_nodes = [
            nid for nid in self._nodes
            if nid != node_id
        ]
        if not all_nodes:
            return []
        chosen = await self._router.route(
            state=state,
            available_nodes=all_nodes,
            context=self._routing_context,
        )
        return [chosen] if chosen else []


# ---------------------------------------------------------------------------
# Agent Framework
# ---------------------------------------------------------------------------

class Tool:
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        func: Callable[..., Any],
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self._func = func

    def to_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )

    async def execute(self, **kwargs: Any) -> Any:
        if asyncio.iscoroutinefunction(self._func):
            return await self._func(**kwargs)
        return self._func(**kwargs)


def tool(
    name: Optional[str] = None,
    description: str = "",
    parameters: Optional[Dict[str, Any]] = None,
) -> Callable:
    def decorator(func: Callable) -> Tool:
        tool_name = name or func.__name__
        tool_params = parameters or {"type": "object", "properties": {}}
        return Tool(
            name=tool_name,
            description=description or func.__doc__ or "",
            parameters=tool_params,
            func=func,
        )
    return decorator


class Agent:
    def __init__(
        self,
        name: str,
        client: BaseInferenceClient,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Tool]] = None,
        max_iterations: int = 10,
        cache: Optional[AbstractCache] = None,
    ):
        self.name = name
        self._client = client
        self._system_prompt = system_prompt or f"You are {name}, a helpful AI assistant."
        self._tools: Dict[str, Tool] = {t.name: t for t in (tools or [])}
        self.max_iterations = max_iterations
        self._cache = cache
        self._conversation_history: List[Message] = []

    def add_tool(self, t: Tool) -> "Agent":
        self._tools[t.name] = t
        return self

    def _build_messages(self, user_message: str) -> List[Message]:
        messages = [Message(role=MessageRole.SYSTEM, content=self._system_prompt)]
        messages.extend(self._conversation_history)
        messages.append(Message(role=MessageRole.USER, content=user_message))
        return messages

    async def _execute_tool_calls(
        self, tool_calls: List[Dict[str, Any]]
    ) -> List[Message]:
        results = []
        for tc in tool_calls:
            tool_name = tc.get("function", {}).get("name", "")
            tool_args_str = tc.get("function", {}).get("arguments", "{}")
            try:
                tool_args = json.loads(tool_args_str)
            except json.JSONDecodeError:
                tool_args = {}
            if tool_name in self._tools:
                try:
                    result = await self._tools[tool_name].execute(**tool_args)
                    content = json.dumps(result) if not isinstance(result, str) else result
                except Exception as e:
                    content = f"Error: {e}"
            else:
                content = f"Tool '{tool_name}' not found"
            results.append(
                Message(
                    role=MessageRole.TOOL,
                    content=content,
                    tool_call_id=tc.get("id"),
                )
            )
        return results

    async def run(self, user_message: str) -> str:
        tool_definitions = [t.to_definition() for t in self._tools.values()]
        messages = self._build_messages(user_message)
        self._conversation_history.append(
            Message(role=MessageRole.USER, content=user_message)
        )

        for _ in range(self.max_iterations):
            response = await self._client.complete(
                messages=messages,
                tools=tool_definitions if tool_definitions else None,
            )
            if response.tool_calls:
                assistant_msg = Message(
                    role=MessageRole.ASSISTANT,
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
                messages.append(assistant_msg)
                self._conversation_history.append(assistant_msg)
                tool_results = await self._execute_tool_calls(response.tool_calls)
                messages.extend(tool_results)
                self._conversation_history.extend(tool_results)
            else:
                assistant_msg = Message(
                    role=MessageRole.ASSISTANT,
                    content=response.content,
                )
                self._conversation_history.append(assistant_msg)
                return response.content

        return "Max iterations reached without a final response."

    async def stream_run(
        self, user_message: str
    ) -> AsyncGenerator[str, None]:
        messages = self._build_messages(user_message)
        self._conversation_history.append(
            Message(role=MessageRole.USER, content=user_message)
        )
        full_content = ""
        async for chunk in await self._client.stream(messages=messages):
            if chunk.content:
                full_content += chunk.content
                yield chunk.content
        self._conversation_history.append(
            Message(role=MessageRole.ASSISTANT, content=full_content)
        )

    def clear_history(self) -> None:
        self._conversation_history.clear()

    def get_history(self) -> List[Message]:
        return list(self._conversation_history)


# ---------------------------------------------------------------------------
# Multi-Agent Orchestration
# ---------------------------------------------------------------------------

class AgentOrchestrator:
    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._graph: Optional[Graph] = None

    def register_agent(self, agent: Agent) -> "AgentOrchestrator":
        self._agents[agent.name] = agent
        return self

    def set_graph(self, graph: Graph) -> "AgentOrchestrator":
        self._graph = graph
        return self

    def _create_agent_node(self, agent_name: str, message_key: str) -> Node:
        agent = self._agents[agent_name]

        async def agent_func(state: GraphState) -> str:
            message = state.get(message_key, "")
            response = await agent.run(message)
            state.set(f"{agent_name}_response", response)
            return response

        return Node(node_id=agent_name, func=agent_func)

    async def run_pipeline(
        self,
        initial_message: str,
        agent_sequence: List[str],
    ) -> Dict[str, str]:
        results: Dict[str, str] = {}
        current_message = initial_message
        for agent_name in agent_sequence:
            if agent_name not in self._agents:
                raise ValueError(f"Agent '{agent_name}' not registered")
            agent = self._agents[agent_name]
            response = await agent.run(current_message)
            results[agent_name] = response
            current_message = response
        return results


# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------

class PromptTemplate:
    def __init__(self, template: str, input_variables: Optional[List[str]] = None):
        self.template = template
        self.input_variables = input_variables or self._extract_variables()

    def _extract_variables(self) -> List[str]:
        import re
        return re.findall(r"\{(\w+)\}", self.template)

    def format(self, **kwargs: Any) -> str:
        missing = set(self.input_variables) - set(kwargs.keys())
        if missing:
            raise ValueError(f"Missing template variables: {missing}")
        return self.template.format(**kwargs)

    def to_message(self, role: MessageRole, **kwargs: Any) -> Message:
        return Message(role=role, content=self.format(**kwargs))


class ChatPromptTemplate:
    def __init__(self, messages: List[Tuple[MessageRole, str]]):
        self._templates = [
            (role, PromptTemplate(template))
            for role, template in messages
        ]

    def format_messages(self, **kwargs: Any) -> List[Message]:
        return [
            Message(role=role, content=template.format(**kwargs))
            for role, template in self._templates
        ]

    @classmethod
    def from_messages(
        cls, messages: List[Tuple[str, str]]
    ) -> "ChatPromptTemplate":
        role_map = {
            "system": MessageRole.SYSTEM,
            "user": MessageRole.USER,
            "assistant": MessageRole.ASSISTANT,
        }
        return cls(
            [
                (role_map.get(role, MessageRole.USER), template)
                for role, template in messages
            ]
        )


# ---------------------------------------------------------------------------
# OpenTelemetry Instrumentation
# ---------------------------------------------------------------------------

class TelemetryConfig:
    def __init__(
        self,
        service_name: str = "agent-framework",
        endpoint: Optional[str] = None,
        enabled: bool = True,
    ):
        self.service_name = service_name
        self.endpoint = endpoint
        self.enabled = enabled


class TelemetryManager:
    _instance: Optional["TelemetryManager"] = None

    def __init__(self, config: TelemetryConfig):
        self.config = config
        self._tracer: Optional[Any] = None
        self._initialized = False

    @classmethod
    def get_instance(cls) -> Optional["TelemetryManager"]:
        return cls._instance

    @classmethod
    def initialize(cls, config: TelemetryConfig) -> "TelemetryManager":
        instance = cls(config)
        if config.enabled and OTEL_AVAILABLE:
            instance._setup_otel()
        cls._instance = instance
        return instance

    def _setup_otel(self) -> None:
        try:
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            provider = TracerProvider()
            if self.config.endpoint:
                try:
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                        OTLPSpanExporter,
                    )
                    exporter = OTLPSpanExporter(endpoint=self.config.endpoint)
                    provider.add_span_processor(BatchSpanProcessor(exporter))
                except ImportError:
                    pass
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(self.config.service_name)
            self._initialized = True
        except Exception:
            pass

    def get_tracer(self) -> Optional[Any]:
        return self._tracer

    def create_span(self, name: str) -> Any:
        if self._tracer and OTEL_AVAILABLE:
            return self._tracer.start_span(name)
        return None


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def create_graph(name: str = "graph") -> GraphBuilder:
    return GraphBuilder(name=name)


def create_agent(
    name: str,
    client: BaseInferenceClient,
    system_prompt: Optional[str] = None,
    tools: Optional[List[Tool]] = None,
    max_iterations: int = 10,
) -> Agent:
    return Agent(
        name=name,
        client=client,
        system_prompt=system_prompt,
        tools=tools,
        max_iterations=max_iterations,
    )


def create_openai_client(
    model: str = "gpt-4o",
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> OpenAIClient:
    return OpenAIClient(model=model, api_key=api_key, **kwargs)


def create_anthropic_client(
    model: str = "claude-3-5-sonnet-20241022",
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> AnthropicClient:
    return AnthropicClient(model=model, api_key=api_key, **kwargs)


def create_mock_client(
    responses: Optional[List[str]] = None,
    **kwargs: Any,
) -> MockInferenceClient:
    return MockInferenceClient(responses=responses, **kwargs)


def create_redis_cache(
    url: str = "redis://localhost:6379",
    prefix: str = "",
    suffix: str = "",
) -> RedisCache:
    return RedisCache(url=url, prefix=prefix, suffix=suffix)


def create_memory_cache(prefix: str = "", suffix: str = "") -> InMemoryCache:
    return InMemoryCache(prefix=prefix, suffix=suffix)


# ---------------------------------------------------------------------------
# __all__
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
    "ExecutionError",
    "InferenceError",
    "CacheError",
    # Data Models
    "Message",
    "TokenUsage",
    "ToolDefinition",
    "InferenceResponse",
    "StreamChunk",
    "GraphState",
    "NodeResult",
    "GraphSnapshot",
    # Cache
    "AbstractCache",
    "InMemoryCache",
    "RedisCache",
    # Middleware
    "MiddlewareContext",
    "Middleware",
    "LoggingMiddleware",
    "TimingMiddleware",
    "OpenTelemetryMiddleware",
    # Graph
    "Node",
    "Edge",
    "ConditionalEdge",
    "Graph",
    "GraphBuilder",
    # Inference
    "BaseInferenceClient",
    "OpenAIClient",
    "AnthropicClient",
    "MockInferenceClient",
    # LLM Directed Graph
    "LLMRouter",
    "LLMDirectedGraph",
    # Agent
    "Tool",
    "tool",
    "Agent",
    "AgentOrchestrator",
    # Prompts
    "PromptTemplate",
    "ChatPromptTemplate",
    # Telemetry
    "TelemetryConfig",
    "TelemetryManager",
    # Utilities
    "create_graph",
    "create_agent",
    "create_openai_client",
    "create_anthropic_client",
    "create_mock_client",
    "create_redis_cache",
    "create_memory_cache",
]