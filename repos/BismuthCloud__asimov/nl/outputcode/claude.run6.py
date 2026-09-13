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
    Generic,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
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


# ─────────────────────────────────────────────
# Type Variables
# ─────────────────────────────────────────────

T = TypeVar("T")
StateT = TypeVar("StateT")


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

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


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    CUSTOM = "custom"


# ─────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────

class GraphError(Exception):
    pass


class NodeNotFoundError(GraphError):
    pass


class CyclicDependencyError(GraphError):
    pass


class NodeExecutionError(GraphError):
    def __init__(self, node_id: str, original: Exception):
        self.node_id = node_id
        self.original = original
        super().__init__(f"Node '{node_id}' failed: {original}")


class CacheError(Exception):
    pass


class InferenceError(Exception):
    pass


class MiddlewareError(Exception):
    pass


# ─────────────────────────────────────────────
# Token Usage
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# Tool / Function Calling
# ─────────────────────────────────────────────

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    required: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required,
            },
        }


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    tool_call_id: str
    name: str
    result: Any
    error: Optional[str] = None


# ─────────────────────────────────────────────
# Messages
# ─────────────────────────────────────────────

@dataclass
class Message:
    role: str
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)}}
                for tc in self.tool_calls
            ]
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d


# ─────────────────────────────────────────────
# Inference Response
# ─────────────────────────────────────────────

@dataclass
class InferenceResponse:
    content: str
    model: str
    provider: LLMProvider
    usage: TokenUsage = field(default_factory=TokenUsage)
    tool_calls: Optional[List[ToolCall]] = None
    finish_reason: Optional[str] = None
    raw: Optional[Any] = None
    cached: bool = False
    latency_ms: float = 0.0


@dataclass
class StreamChunk:
    delta: str
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    usage: Optional[TokenUsage] = None


# ─────────────────────────────────────────────
# Cache Interface
# ─────────────────────────────────────────────

class AbstractCache(ABC):

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        ...

    @abstractmethod
    async def clear(self, pattern: str = "*") -> int:
        ...

    @abstractmethod
    async def publish(self, mailbox: str, message: Any) -> None:
        ...

    @abstractmethod
    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        ...


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
        keys_to_delete = [k for k in list(self._store.keys()) if fnmatch.fnmatch(k, pattern)]
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
            raise ImportError("redis package is required for RedisCache. Install with: pip install redis")
        self.url = url
        self.prefix = prefix
        self.suffix = suffix
        self.db = db
        self._client: Optional[Any] = None
        self._pubsub_clients: Dict[str, Any] = {}

    def _make_key(self, key: str) -> str:
        parts = []
        if self.prefix:
            parts.append(self.prefix)
        parts.append(key)
        if self.suffix:
            parts.append(self.suffix)
        return ":".join(parts)

    async def _get_client(self) -> Any:
        if self._client is None:
            self._client = aioredis.from_url(self.url, db=self.db, decode_responses=True)
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        client = await self._get_client()
        full_key = self._make_key(key)
        value = await client.get(full_key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

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
        try:
            async for raw_message in pubsub.listen():
                if raw_message["type"] == "message":
                    data = raw_message["data"]
                    try:
                        yield json.loads(data)
                    except (json.JSONDecodeError, TypeError):
                        yield data
        finally:
            await pubsub.unsubscribe(mailbox)
            await pubsub.close()

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None


# ─────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────

class Middleware(ABC):

    @abstractmethod
    async def before_node(self, node_id: str, state: Any, context: Dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def after_node(self, node_id: str, state: Any, context: Dict[str, Any], result: Any) -> Any:
        ...

    async def on_error(self, node_id: str, state: Any, context: Dict[str, Any], error: Exception) -> None:
        pass


class LoggingMiddleware(Middleware):

    def __init__(self, logger: Optional[Any] = None):
        import logging
        self.logger = logger or logging.getLogger(__name__)

    async def before_node(self, node_id: str, state: Any, context: Dict[str, Any]) -> Any:
        self.logger.info(f"[Graph] Starting node: {node_id}")
        return state

    async def after_node(self, node_id: str, state: Any, context: Dict[str, Any], result: Any) -> Any:
        self.logger.info(f"[Graph] Completed node: {node_id}")
        return result

    async def on_error(self, node_id: str, state: Any, context: Dict[str, Any], error: Exception) -> None:
        self.logger.error(f"[Graph] Error in node {node_id}: {error}")


class TimingMiddleware(Middleware):

    def __init__(self):
        self._start_times: Dict[str, float] = {}
        self.timings: Dict[str, float] = {}

    async def before_node(self, node_id: str, state: Any, context: Dict[str, Any]) -> Any:
        self._start_times[node_id] = time.time()
        return state

    async def after_node(self, node_id: str, state: Any, context: Dict[str, Any], result: Any) -> Any:
        if node_id in self._start_times:
            elapsed = (time.time() - self._start_times.pop(node_id)) * 1000
            self.timings[node_id] = elapsed
        return result


class CachingMiddleware(Middleware):

    def __init__(self, cache: AbstractCache, ttl: Optional[int] = None):
        self.cache = cache
        self.ttl = ttl
        self._cache_keys: Dict[str, str] = {}

    def _make_cache_key(self, node_id: str, state: Any) -> str:
        try:
            state_hash = hash(json.dumps(state, sort_keys=True, default=str))
        except Exception:
            state_hash = id(state)
        return f"node:{node_id}:state:{state_hash}"

    async def before_node(self, node_id: str, state: Any, context: Dict[str, Any]) -> Any:
        cache_key = self._make_cache_key(node_id, state)
        self._cache_keys[node_id] = cache_key
        cached = await self.cache.get(cache_key)
        if cached is not None:
            context["_cached_result"] = cached
        return state

    async def after_node(self, node_id: str, state: Any, context: Dict[str, Any], result: Any) -> Any:
        if "_cached_result" not in context:
            cache_key = self._cache_keys.get(node_id)
            if cache_key:
                try:
                    await self.cache.set(cache_key, result, ttl=self.ttl)
                except Exception:
                    pass
        return result


# ─────────────────────────────────────────────
# State Snapshot
# ─────────────────────────────────────────────

@dataclass
class StateSnapshot:
    snapshot_id: str
    node_id: str
    state: Any
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "node_id": self.node_id,
            "state": self.state,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateSnapshot":
        return cls(
            snapshot_id=data["snapshot_id"],
            node_id=data["node_id"],
            state=data["state"],
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


class SnapshotManager:

    def __init__(self, cache: Optional[AbstractCache] = None, max_snapshots: int = 100):
        self._snapshots: List[StateSnapshot] = []
        self._cache = cache
        self.max_snapshots = max_snapshots

    async def save(self, node_id: str, state: Any, metadata: Optional[Dict[str, Any]] = None) -> StateSnapshot:
        snapshot = StateSnapshot(
            snapshot_id=str(uuid.uuid4()),
            node_id=node_id,
            state=state,
            metadata=metadata or {},
        )
        self._snapshots.append(snapshot)
        if len(self._snapshots) > self.max_snapshots:
            self._snapshots = self._snapshots[-self.max_snapshots:]
        if self._cache:
            await self._cache.set(f"snapshot:{snapshot.snapshot_id}", snapshot.to_dict())
        return snapshot

    async def load(self, snapshot_id: str) -> Optional[StateSnapshot]:
        for snap in reversed(self._snapshots):
            if snap.snapshot_id == snapshot_id:
                return snap
        if self._cache:
            data = await self._cache.get(f"snapshot:{snapshot_id}")
            if data:
                return StateSnapshot.from_dict(data)
        return None

    def get_history(self, node_id: Optional[str] = None) -> List[StateSnapshot]:
        if node_id:
            return [s for s in self._snapshots if s.node_id == node_id]
        return list(self._snapshots)

    def latest(self, node_id: Optional[str] = None) -> Optional[StateSnapshot]:
        history = self.get_history(node_id)
        return history[-1] if history else None

    def clear(self) -> None:
        self._snapshots.clear()


# ─────────────────────────────────────────────
# Graph Nodes
# ─────────────────────────────────────────────

NodeFunction = Callable[[Any, Dict[str, Any]], Any]


@dataclass
class Edge:
    source: str
    target: str
    edge_type: EdgeType = EdgeType.DEFAULT
    condition: Optional[Callable[[Any], bool]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Node:

    def __init__(
        self,
        node_id: str,
        func: NodeFunction,
        metadata: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        retry_delay: float = 0.0,
    ):
        self.node_id = node_id
        self.func = func
        self.metadata = metadata or {}
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.status: NodeStatus = NodeStatus.PENDING

    async def execute(self, state: Any, context: Dict[str, Any]) -> Any:
        last_error: Optional[Exception] = None
        attempts = self.retry_count + 1
        for attempt in range(attempts):
            try:
                self.status = NodeStatus.RUNNING
                if asyncio.iscoroutinefunction(self.func):
                    result = await self.func(state, context)
                else:
                    result = self.func(state, context)
                self.status = NodeStatus.COMPLETED
                return result
            except Exception as e:
                last_error = e
                if attempt < attempts - 1 and self.retry_delay > 0:
                    await asyncio.sleep(self.retry_delay)
        self.status = NodeStatus.FAILED
        raise NodeExecutionError(self.node_id, last_error)

    def reset(self) -> None:
        self.status = NodeStatus.PENDING


# ─────────────────────────────────────────────
# Graph Execution Engine
# ─────────────────────────────────────────────

class ExecutionContext:

    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.node_results: Dict[str, Any] = {}
        self.errors: Dict[str, Exception] = {}
        self.execution_order: List[str] = []
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None

    @property
    def elapsed_ms(self) -> float:
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


class Graph:

    def __init__(
        self,
        name: str = "graph",
        snapshot_manager: Optional[SnapshotManager] = None,
        enable_snapshots: bool = False,
    ):
        self.name = name
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._entry_points: Set[str] = set()
        self._middlewares: List[Middleware] = []
        self._snapshot_manager = snapshot_manager or SnapshotManager()
        self.enable_snapshots = enable_snapshots
        self._tracer: Optional[Any] = None

    def add_node(self, node: Node) -> "Graph":
        self._nodes[node.node_id] = node
        return self

    def add_edge(self, edge: Edge) -> "Graph":
        if edge.source not in self._nodes:
            raise NodeNotFoundError(f"Source node '{edge.source}' not found")
        if edge.target not in self._nodes:
            raise NodeNotFoundError(f"Target node '{edge.target}' not found")
        self._edges.append(edge)
        return self

    def set_entry_point(self, node_id: str) -> "Graph":
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found")
        self._entry_points.add(node_id)
        return self

    def add_middleware(self, middleware: Middleware) -> "Graph":
        self._middlewares.append(middleware)
        return self

    def set_tracer(self, tracer: Any) -> "Graph":
        self._tracer = tracer
        return self

    def _get_successors(self, node_id: str, state: Any) -> List[str]:
        successors = []
        for edge in self._edges:
            if edge.source == node_id:
                if edge.edge_type == EdgeType.CONDITIONAL:
                    if edge.condition and edge.condition(state):
                        successors.append(edge.target)
                else:
                    successors.append(edge.target)
        return successors

    def _get_predecessors(self, node_id: str) -> List[str]:
        return [e.source for e in self._edges if e.target == node_id]

    def _topological_sort(self) -> List[str]:
        in_degree: Dict[str, int] = {nid: 0 for nid in self._nodes}
        for edge in self._edges:
            in_degree[edge.target] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order = []

        while queue:
            node_id = queue.pop(0)
            order.append(node_id)
            for edge in self._edges:
                if edge.source == node_id:
                    in_degree[edge.target] -= 1
                    if in_degree[edge.target] == 0:
                        queue.append(edge.target)

        if len(order) != len(self._nodes):
            raise CyclicDependencyError("Graph contains a cycle")
        return order

    def validate(self) -> List[str]:
        issues = []
        try:
            self._topological_sort()
        except CyclicDependencyError as e:
            issues.append(str(e))

        all_targets = {e.target for e in self._edges}
        all_sources = {e.source for e in self._edges}
        isolated = set(self._nodes.keys()) - all_targets - all_sources
        if isolated and len(self._nodes) > 1:
            issues.append(f"Isolated nodes detected: {isolated}")

        return issues

    def reset(self) -> None:
        for node in self._nodes.values():
            node.reset()

    async def _run_middlewares_before(
        self, node_id: str, state: Any, context: ExecutionContext
    ) -> Any:
        for mw in self._middlewares:
            state = await mw.before_node(node_id, state, context.data)
        return state

    async def _run_middlewares_after(
        self, node_id: str, state: Any, context: ExecutionContext, result: Any
    ) -> Any:
        for mw in self._middlewares:
            result = await mw.after_node(node_id, state, context.data, result)
        return result

    async def _run_middlewares_error(
        self, node_id: str, state: Any, context: ExecutionContext, error: Exception
    ) -> None:
        for mw in self._middlewares:
            await mw.on_error(node_id, state, context.data, error)

    async def execute(
        self,
        initial_state: Any = None,
        context: Optional[ExecutionContext] = None,
        entry_point: Optional[str] = None,
    ) -> Tuple[Any, ExecutionContext]:
        if context is None:
            context = ExecutionContext()

        self.reset()
        state = initial_state

        if entry_point:
            start_nodes = [entry_point]
        elif self._entry_points:
            start_nodes = list(self._entry_points)
        else:
            try:
                topo = self._topological_sort()
                start_nodes = [topo[0]] if topo else []
            except CyclicDependencyError:
                start_nodes = list(self._nodes.keys())[:1]

        visited: Set[str] = set()
        queue: List[str] = list(start_nodes)

        while queue:
            node_id = queue.pop(0)
            if node_id in visited:
                continue

            preds = self._get_predecessors(node_id)
            if any(p not in visited and p not in queue for p in preds):
                queue.append(node_id)
                continue

            visited.add(node_id)
            node = self._nodes.get(node_id)
            if node is None:
                raise NodeNotFoundError(f"Node '{node_id}' not found")

            if "_cached_result" in context.data:
                del context.data["_cached_result"]

            state = await self._run_middlewares_before(node_id, state, context)

            if "_cached_result" in context.data:
                result = context.data.pop("_cached_result")
                node.status = NodeStatus.COMPLETED
            else:
                span = None
                if self._tracer and OTEL_AVAILABLE:
                    span = self._tracer.start_span(f"node:{node_id}")

                try:
                    result = await node.execute(state, context.data)
                    context.node_results[node_id] = result
                    context.execution_order.append(node_id)

                    if self.enable_snapshots:
                        await self._snapshot_manager.save(node_id, result)

                    if span:
                        span.set_attribute("node.id", node_id)
                        span.set_attribute("node.status", "completed")

                except NodeExecutionError as e:
                    context.errors[node_id] = e
                    await self._run_middlewares_error(node_id, state, context, e)
                    if span:
                        span.set_attribute("node.status", "failed")
                        span.record_exception(e)
                    raise
                finally:
                    if span:
                        span.end()

            result = await self._run_middlewares_after(node_id, state, context, result)
            state = result

            successors = self._get_successors(node_id, state)
            for s in successors:
                if s not in visited:
                    queue.append(s)

        context.end_time = time.time()
        return state, context

    async def stream_execute(
        self,
        initial_state: Any = None,
        context: Optional[ExecutionContext] = None,
        entry_point: Optional[str] = None,
    ) -> AsyncGenerator[Tuple[str, Any], None]:
        if context is None:
            context = ExecutionContext()

        self.reset()
        state = initial_state

        if entry_point:
            start_nodes = [entry_point]
        elif self._entry_points:
            start_nodes = list(self._entry_points)
        else:
            try:
                topo = self._topological_sort()
                start_nodes = [topo[0]] if topo else []
            except CyclicDependencyError:
                start_nodes = list(self._nodes.keys())[:1]

        visited: Set[str] = set()
        queue: List[str] = list(start_nodes)

        while queue:
            node_id = queue.pop(0)
            if node_id in visited:
                continue

            preds = self._get_predecessors(node_id)
            if any(p not in visited and p not in queue for p in preds):
                queue.append(node_id)
                continue

            visited.add(node_id)
            node = self._nodes.get(node_id)
            if node is None:
                raise NodeNotFoundError(f"Node '{node_id}' not found")

            state = await self._run_middlewares_before(node_id, state, context)

            try:
                result = await node.execute(state, context.data)
                context.node_results[node_id] = result
                context.execution_order.append(node_id)

                if self.enable_snapshots:
                    await self._snapshot_manager.save(node_id, result)

                result = await self._run_middlewares_after(node_id, state, context, result)
                state = result
                yield node_id, state

            except NodeExecutionError as e:
                context.errors[node_id] = e
                await self._run_middlewares_error(node_id, state, context, e)
                raise

            successors = self._get_successors(node_id, state)
            for s in successors:
                if s not in visited:
                    queue.append(s)

        context.end_time = time.time()


# ─────────────────────────────────────────────
# Graph Builder (Fluent API)
# ─────────────────────────────────────────────

class GraphBuilder:

    def __init__(self, name: str = "graph"):
        self._graph = Graph(name=name)

    def node(
        self,
        node_id: str,
        func: NodeFunction,
        metadata: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        retry_delay: float = 0.0,
    ) -> "GraphBuilder":
        n = Node(
            node_id=node_id,
            func=func,
            metadata=metadata,
            retry_count=retry_count,
            retry_delay=retry_delay,
        )
        self._graph.add_node(n)
        return self

    def edge(self, source: str, target: str) -> "GraphBuilder":
        self._graph.add_edge(Edge(source=source, target=target))
        return self

    def conditional_edge(
        self, source: str, target: str, condition: Callable[[Any], bool]
    ) -> "GraphBuilder":
        self._graph.add_edge(
            Edge(source=source, target=target, edge_type=EdgeType.CONDITIONAL, condition=condition)
        )
        return self

    def entry_point(self, node_id: str) -> "GraphBuilder":
        self._graph.set_entry_point(node_id)
        return self

    def middleware(self, mw: Middleware) -> "GraphBuilder":
        self._graph.add_middleware(mw)
        return self

    def snapshots(self, enabled: bool = True, manager: Optional[SnapshotManager] = None) -> "GraphBuilder":
        self._graph.enable_snapshots = enabled
        if manager:
            self._graph._snapshot_manager = manager
        return self

    def build(self) -> Graph:
        return self._graph


# ─────────────────────────────────────────────
# LLM Inference Clients
# ─────────────────────────────────────────────

class BaseInferenceClient(ABC):

    def __init__(
        self,
        model: str,
        provider: LLMProvider,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_temperature: float = 0.7,
        default_max_tokens: int = 1024,
        cache: Optional[AbstractCache] = None,
        enable_prompt_caching: bool = False,
    ):
        self.model = model
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self.cache = cache
        self.enable_prompt_caching = enable_prompt_caching
        self._total_usage = TokenUsage()
        self._tracer: Optional[Any] = None

    def set_tracer(self, tracer: Any) -> None:
        self._tracer = tracer

    @property
    def total_usage(self) -> TokenUsage:
        return self._total_usage

    def _update_usage(self, usage: TokenUsage) -> None:
        self._total_usage = self._total_usage + usage

    def _make_cache_key(self, messages: List[Message], **kwargs) -> str:
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            **{k: v for k, v in kwargs.items() if isinstance(v, (str, int, float, bool, type(None)))},
        }
        return f"inference:{hash(json.dumps(payload, sort_keys=True, default=str))}"

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> InferenceResponse:
        ...

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        ...

    async def complete_with_tools(
        self,
        messages: List[Message],
        tools: List[ToolDefinition],
        tool_handlers: Dict[str, Callable],
        max_iterations: int = 10,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> InferenceResponse:
        current_messages = list(messages)
        total_usage = TokenUsage()

        for _ in range(max_iterations):
            response = await self.complete(
                current_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
            )
            total_usage = total_usage + response.usage

            if not response.tool_calls:
                response.usage = total_usage
                return response

            current_messages.append(
                Message(
                    role="assistant",
                    content=response.content or "",
                    tool_calls=response.tool_calls,
                )
            )

            for tc in response.tool_calls:
                handler = tool_handlers.get(tc.name)
                if handler:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            result = await handler(**tc.arguments)
                        else:
                            result = handler(**tc.arguments)
                        tool_result = ToolResult(
                            tool_call_id=tc.id,
                            name=tc.name,
                            result=result,
                        )
                    except Exception as e:
                        tool_result = ToolResult(
                            tool_call_id=tc.id,
                            name=tc.name,
                            result=None,
                            error=str(e),
                        )
                    current_messages.append(
                        Message(
                            role="tool",
                            content=json.dumps(tool_result.result) if tool_result.result is not None else "",
                            tool_call_id=tool_result.tool_call_id,
                            name=tool_result.name,
                        )
                    )

        response = await self.complete(current_messages, temperature=temperature, max_tokens=max_tokens)
        response.usage = total_usage + response.usage
        return response


class MockInferenceClient(BaseInferenceClient):

    def __init__(
        self,
        model: str = "mock-model",
        response_template: str = "Mock response for: {content}",
        cache: Optional[AbstractCache] = None,
        **kwargs,
    ):
        super().__init__(
            model=model,
            provider=LLMProvider.CUSTOM,
            cache=cache,
            **kwargs,
        )
        self.response_template = response_template
        self._call_count = 0

    async def complete(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> InferenceResponse:
        if self.cache:
            cache_key = self._make_cache_key(messages, temperature=temperature, max_tokens=max_tokens)
            cached = await self.cache.get(cache_key)
            if cached:
                resp = InferenceResponse(**cached)
                resp.cached = True
                return resp

        self._call_count += 1
        last_content = messages[-1].content if messages else ""
        content = self.response_template.format(content=last_content)
        usage = TokenUsage(
            prompt_tokens=len(last_content.split()),
            completion_tokens=len(content.split()),
            total_tokens=len(last_content.split()) + len(content.split()),
        )
        self._update_usage(usage)

        response = InferenceResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            usage=usage,
            finish_reason="stop",
        )

        if self.cache:
            await self.cache.set(cache_key, {
                "content": response.content,
                "model": response.model,
                "provider": response.provider.value,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "cached_tokens": usage.cached_tokens,
                },
                "finish_reason": response.finish_reason,
                "cached": False,
                "latency_ms": 0.0,
            })

        return response

    async def stream(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        response = await self.complete(messages, temperature=temperature, max_tokens=max_tokens)
        words = response.content.split()
        for i, word in enumerate(words):
            is_last = i == len(words) - 1
            yield StreamChunk(
                delta=word + ("" if is_last else " "),
                finish_reason="stop" if is_last else None,
                usage=response.usage if is_last else None,
            )
            await asyncio.sleep(0)


class OpenAIInferenceClient(BaseInferenceClient):

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        cache: Optional[AbstractCache] = None,
        enable_prompt_caching: bool = False,
        **kwargs,
    ):
        super().__init__(
            model=model,
            provider=LLMProvider.OPENAI,
            api_key=api_key,
            base_url=base_url,
            cache=cache,
            enable_prompt_caching=enable_prompt_caching,
            **kwargs,
        )
        self.organization = organization
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")
        if self._client is None:
            kwargs: Dict[str, Any] = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url
            if self.organization:
                kwargs["organization"] = self.organization
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    def _parse_tool_calls(self, raw_tool_calls: Any) -> List[ToolCall]:
        result = []
        if raw_tool_calls:
            for tc in raw_tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, AttributeError):
                    args = {}
                result.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
        return result

    async def complete(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> InferenceResponse:
        if self.cache:
            cache_key = self._make_cache_key(messages, temperature=temperature, max_tokens=max_tokens)
            cached = await self.cache.get(cache_key)
            if cached:
                return InferenceResponse(
                    content=cached.get("content", ""),
                    model=self.model,
                    provider=self.provider,
                    usage=TokenUsage(**cached.get("usage", {})),
                    finish_reason=cached.get("finish_reason"),
                    cached=True,
                )

        client = self._get_client()
        start = time.time()

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature or self.default_temperature,
            "max_tokens": max_tokens or self.default_max_tokens,
        }
        if tools:
            params["tools"] = [{"type": "function", "function": t.to_dict()} for t in tools]
        if stop:
            params["stop"] = stop
        params.update(kwargs)

        try:
            response = await client.chat.completions.create(**params)
        except Exception as e:
            raise InferenceError(f"OpenAI API error: {e}") from e

        latency = (time.time() - start) * 1000
        choice = response.choices[0]
        usage = TokenUsage(
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            total_tokens=response.usage.total_tokens if response.usage else 0,
            cached_tokens=getattr(response.usage, "prompt_tokens_details", None) and
                          getattr(response.usage.prompt_tokens_details, "cached_tokens", 0) or 0,
        )
        self._update_usage(usage)

        tool_calls = self._parse_tool_calls(choice.message.tool_calls)

        result = InferenceResponse(
            content=choice.message.content or "",
            model=self.model,
            provider=self.provider,
            usage=usage,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=choice.finish_reason,
            raw=response,
            latency_ms=latency,
        )

        if self.cache:
            await self.cache.set(cache_key, {
                "content": result.content,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "cached_tokens": usage.cached_tokens,
                },
                "finish_reason": result.finish_reason,
            })

        return result

    async def stream(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        client = self._get_client()

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature or self.default_temperature,
            "max_tokens": max_tokens or self.default_max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            params["tools"] = [{"type": "function", "function": t.to_dict()} for t in tools]
        if stop:
            params["stop"] = stop
        params.update(kwargs)

        try:
            async with await client.chat.completions.create(**params) as stream:
                async for chunk in stream:
                    if not chunk.choices:
                        if chunk.usage:
                            usage = TokenUsage(
                                prompt_tokens=chunk.usage.prompt_tokens,
                                completion_tokens=chunk.usage.completion_tokens,
                                total_tokens=chunk.usage.total_tokens,
                            )
                            self._update_usage(usage)
                            yield StreamChunk(delta="", finish_reason="stop", usage=usage)
                        continue
                    choice = chunk.choices[0]
                    delta_content = choice.delta.content or ""
                    finish_reason = choice.finish_reason
                    yield StreamChunk(delta=delta_content, finish_reason=finish_reason)
        except Exception as e:
            raise InferenceError(f"OpenAI streaming error: {e}") from e


class AnthropicInferenceClient(BaseInferenceClient):

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        cache: Optional[AbstractCache] = None,
        enable_prompt_caching: bool = False,
        **kwargs,
    ):
        super().__init__(
            model=model,
            provider=LLMProvider.ANTHROPIC,
            api_key=api_key,
            cache=cache,
            enable_prompt_caching=enable_prompt_caching,
            **kwargs,
        )
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")
        if self._client is None:
            kwargs: Dict[str, Any] = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            self._client = AsyncAnthropic(**kwargs)
        return self._client

    def _convert_messages(self, messages: List[Message]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        system_prompt = None
        converted = []
        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                converted.append({"role": msg.role, "content": msg.content})
        return system_prompt, converted

    async def complete(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> InferenceResponse:
        if self.cache:
            cache_key = self._make_cache_key(messages, temperature=temperature, max_tokens=max_tokens)
            cached = await self.cache.get(cache_key)
            if cached:
                return InferenceResponse(
                    content=cached.get("content", ""),
                    model=self.model,
                    provider=self.provider,
                    usage=TokenUsage(**cached.get("usage", {})),
                    finish_reason=cached.get("finish_reason"),
                    cached=True,
                )

        client = self._get_client()
        system_prompt, converted_messages = self._convert_messages(messages)
        start = time.time()

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "max_tokens": max_tokens or self.default_max_tokens,
            "temperature": temperature or self.default_temperature,
        }
        if system_prompt:
            params["system"] = system_prompt
        if tools:
            params["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": {"type": "object", "properties": t.parameters, "required": t.required},
                }
                for t in tools
            ]
        if stop:
            params["stop_sequences"] = stop
        params.update(kwargs)

        try:
            response = await client.messages.create(**params)
        except Exception as e:
            raise InferenceError(f"Anthropic API error: {e}") from e

        latency = (time.time() - start) * 1000
        content = ""
        tool_calls = []

        for block in response.content:
            if hasattr(block, "text"):
                content += block.text
            elif hasattr(block, "type") and block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=block.input or {})
                )

        usage = TokenUsage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            cached_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        )
        self._update_usage(usage)

        result = InferenceResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            usage=usage,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=response.stop_reason,
            raw=response,
            latency_ms=latency,
        )

        if self.cache:
            await self.cache.set(cache_key, {
                "content": result.content,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "cached_tokens": usage.cached_tokens,
                },
                "finish_reason": result.finish_reason,
            })

        return result

    async def stream(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        client = self._get_client()
        system_prompt, converted_messages = self._convert_messages(messages)

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "max_tokens": max_tokens or self.default_max_tokens,
            "temperature": temperature or self.default_temperature,
        }
        if system_prompt:
            params["system"] = system_prompt
        if stop:
            params["stop_sequences"] = stop
        params.update(kwargs)

        try:
            async with client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield StreamChunk(delta=text)
                final = await stream.get_final_message()
                usage = TokenUsage(
                    prompt_tokens=final.usage.input_tokens,
                    completion_tokens=final.usage.output_tokens,
                    total_tokens=final.usage.input_tokens + final.usage.output_tokens,
                )
                self._update_usage(usage)
                yield StreamChunk(delta="", finish_reason=final.stop_reason, usage=usage)
        except Exception as e:
            raise InferenceError(f"Anthropic streaming error: {e}") from e


# ─────────────────────────────────────────────
# LLM Directed Graph Execution
# ─────────────────────────────────────────────

class LLMRouter:

    def __init__(
        self,
        client: BaseInferenceClient,
        available_nodes: List[str],
        system_prompt: Optional[str] = None,
    ):
        self.client = client
        self.available_nodes = available_nodes
        self.system_prompt = system_prompt or (
            "You are a routing agent. Given the current state, choose the next node to execute. "
            f"Available nodes: {', '.join(available_nodes)}. "
            "Respond with ONLY the node name, nothing else."
        )

    async def route(self, state: Any, context: Dict[str, Any]) -> Optional[str]:
        state_str = json.dumps(state, default=str) if not isinstance(state, str) else state
        messages = [
            Message(role="system", content=self.system_prompt),
            Message(
                role="user",
                content=f"Current state: {state_str}\nContext: {json.dumps(context, default=str)}\nWhich node should execute next?",
            ),
        ]
        try:
            response = await self.client.complete(messages, temperature=0.0, max_tokens=50)
            chosen = response.content.strip()
            if chosen in self.available_nodes:
                return chosen
            for node in self.available_nodes:
                if node.lower() in chosen.lower():
                    return node
        except Exception:
            pass
        return None


class LLMDirectedGraph(Graph):

    def __init__(
        self,
        name: str = "llm_directed_graph",
        router: Optional[LLMRouter] = None,
        max_steps: int = 50,
        **kwargs,
    ):
        super().__init__(name=name, **kwargs)
        self.router = router
        self.max_steps = max_steps

    async def execute(
        self,
        initial_state: Any = None,
        context: Optional[ExecutionContext] = None,
        entry_point: Optional[str] = None,
    ) -> Tuple[Any, ExecutionContext]:
        if self.router is None:
            return await super().execute(initial_state, context, entry_point)

        if context is None:
            context = ExecutionContext()

        self.reset()
        state = initial_state

        if entry_point:
            current_node_id = entry_point
        elif self._entry_points:
            current_node_id = next(iter(self._entry_points))
        else:
            nodes = list(self._nodes.keys())
            current_node_id = nodes[0] if nodes else None

        if current_node_id is None:
            return state, context

        steps = 0
        while current_node_id and steps < self.max_steps:
            steps += 1
            node = self._nodes.get(current_node_id)
            if node is None:
                break

            state = await self._run_middlewares_before(current_node_id, state, context)

            try:
                result = await node.execute(state, context.data)
                context.node_results[current_node_id] = result
                context.execution_order.append(current_node_id)

                if self.enable_snapshots:
                    await self._snapshot_manager.save(current_node_id, result)

                result = await self._run_middlewares_after(current_node_id, state, context, result)
                state = result

            except NodeExecutionError as e:
                context.errors[current_node_id] = e
                await self._run_middlewares_error(current_node_id, state, context, e)
                raise

            next_node = await self.router.route(state, context.data)
            current_node_id = next_node

        context.end_time = time.time()
        return state, context


# ─────────────────────────────────────────────
# OpenTelemetry Integration
# ─────────────────────────────────────────────

class OTelInstrumentation:

    def __init__(self, service_name: str = "ai-agent-framework", tracer_name: str = "graph-engine"):
        self.service_name = service_name
        self.tracer_name = tracer_name
        self._tracer: Optional[Any] = None

    def setup(self) -> Optional[Any]:
        if not OTEL_AVAILABLE:
            return None
        self._tracer = trace.get_tracer(self.tracer_name)
        return self._tracer

    def get_tracer(self) -> Optional[Any]:
        if self._tracer is None:
            return self.setup()
        return self._tracer

    def instrument_graph(self, graph: Graph) -> Graph:
        tracer = self.get_tracer()
        if tracer:
            graph.set_tracer(tracer)
        return graph

    def instrument_client(self, client: BaseInferenceClient) -> BaseInferenceClient:
        tracer = self.get_tracer()
        if tracer:
            client.set_tracer(tracer)
        return client


# ─────────────────────────────────────────────
# Agent
# ─────────────────────────────────────────────

class Agent:

    def __init__(
        self,
        name: str,
        graph: Graph,
        inference_client: Optional[BaseInferenceClient] = None,
        cache: Optional[AbstractCache] = None,
        tools: Optional[List[ToolDefinition]] = None,
        system_prompt: Optional[str] = None,
    ):
        self.name = name
        self.graph = graph
        self.inference_client = inference_client
        self.cache = cache
        self.tools = tools or []
        self.system_prompt = system_prompt
        self._conversation_history: List[Message] = []

    def add_tool(self, tool: ToolDefinition) -> None:
        self.tools.append(tool)

    def clear_history(self) -> None:
        self._conversation_history.clear()

    @property
    def conversation_history(self) -> List[Message]:
        return list(self._conversation_history)

    async def chat(
        self,
        user_message: str,
        tool_handlers: Optional[Dict[str, Callable]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> InferenceResponse:
        if self.inference_client is None:
            raise InferenceError("No inference client configured")

        messages = []
        if self.system_prompt:
            messages.append(Message(role="system", content=self.system_prompt))
        messages.extend(self._conversation_history)
        messages.append(Message(role="user", content=user_message))

        if self.tools and tool_handlers:
            response = await self.inference_client.complete_with_tools(
                messages=messages,
                tools=self.tools,
                tool_handlers=tool_handlers,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            response = await self.inference_client.complete(
                messages=messages,
                tools=self.tools if self.tools else None,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        self._conversation_history.append(Message(role="user", content=user_message))
        self._conversation_history.append(Message(role="assistant", content=response.content))

        return response

    async def run(
        self,
        initial_state: Any = None,
        context: Optional[ExecutionContext] = None,
    ) -> Tuple[Any, ExecutionContext]:
        return await self.graph.execute(initial_state=initial_state, context=context)

    async def stream_chat(
        self,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        if self.inference_client is None:
            raise InferenceError("No inference client configured")

        messages = []
        if self.system_prompt:
            messages.append(Message(role="system", content=self.system_prompt))
        messages.extend(self._conversation_history)
        messages.append(Message(role="user", content=user_message))

        full_content = ""
        async for chunk in self.inference_client.stream(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            full_content += chunk.delta
            yield chunk

        self._conversation_history.append(Message(role="user", content=user_message))
        self._conversation_history.append(Message(role="assistant", content=full_content))


# ─────────────────────────────────────────────
# Agent Builder
# ─────────────────────────────────────────────

class AgentBuilder:

    def __init__(self, name: str):
        self._name = name
        self._graph: Optional[Graph] = None
        self._client: Optional[BaseInferenceClient] = None
        self._cache: Optional[AbstractCache] = None
        self._tools: List[ToolDefinition] = []
        self._system_prompt: Optional[str] = None
        self._middlewares: List[Middleware] = []
        self._enable_snapshots: bool = False

    def with_graph(self, graph: Graph) -> "AgentBuilder":
        self._graph = graph
        return self

    def with_inference_client(self, client: BaseInferenceClient) -> "AgentBuilder":
        self._client = client
        return self

    def with_cache(self, cache: AbstractCache) -> "AgentBuilder":
        self._cache = cache
        return self

    def with_tool(self, tool: ToolDefinition) -> "AgentBuilder":
        self._tools.append(tool)
        return self

    def with_system_prompt(self, prompt: str) -> "AgentBuilder":
        self._system_prompt = prompt
        return self

    def with_middleware(self, middleware: Middleware) -> "AgentBuilder":
        self._middlewares.append(middleware)
        return self

    def with_snapshots(self, enabled: bool = True) -> "AgentBuilder":
        self._enable_snapshots = enabled
        return self

    def build(self) -> Agent:
        if self._graph is None:
            self._graph = Graph(name=f"{self._name}_graph")

        for mw in self._middlewares:
            self._graph.add_middleware(mw)

        if self._enable_snapshots:
            self._graph.enable_snapshots = True

        return Agent(
            name=self._name,
            graph=self._graph,
            inference_client=self._client,
            cache=self._cache,
            tools=self._tools,
            system_prompt=self._system_prompt,
        )


# ─────────────────────────────────────────────
# Convenience Functions
# ─────────────────────────────────────────────

def node(
    node_id: str,
    retry_count: int = 0,
    retry_delay: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Callable:
    def decorator(func: NodeFunction) -> Node:
        return Node(
            node_id=node_id,
            func=func,
            metadata=metadata,
            retry_count=retry_count,
            retry_delay=retry_delay,
        )
    return decorator


def create_graph(name: str = "graph") -> GraphBuilder:
    return GraphBuilder(name=name)


def create_agent(name: str) -> AgentBuilder:
    return AgentBuilder(name=name)


def create_cache(
    backend: str = "memory",
    prefix: str = "",
    suffix: str = "",
    **kwargs,
) -> AbstractCache:
    if backend == "memory":
        return InMemoryCache(prefix=prefix, suffix=suffix)
    elif backend == "redis":
        return RedisCache(prefix=prefix, suffix=suffix, **kwargs)
    else:
        raise ValueError(f"Unknown cache backend: {backend}")


def create_inference_client(
    provider: Union[str, LLMProvider],
    model: str,
    api_key: Optional[str] = None,
    cache: Optional[AbstractCache] = None,
    **kwargs,
) -> BaseInferenceClient:
    if isinstance(provider, str):
        provider = LLMProvider(provider.lower())

    if provider == LLMProvider.OPENAI:
        return OpenAIInferenceClient(model=model, api_key=api_key, cache=cache, **kwargs)
    elif provider == LLMProvider.ANTHROPIC:
        return AnthropicInferenceClient(model=model, api_key=api_key, cache=cache, **kwargs)
    elif provider == LLMProvider.CUSTOM:
        return MockInferenceClient(model=model, cache=cache, **kwargs)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


# ─────────────────────────────────────────────
# Example / Demo
# ─────────────────────────────────────────────

async def _demo():
    cache = create_cache("memory", prefix="demo")

    async def step_one(state: Dict, ctx: Dict) -> Dict:
        state["step1"] = "done"
        return state

    async def step_two(state: Dict, ctx: Dict) -> Dict:
        state["step2"] = "done"
        return state

    async def step_three(state: Dict, ctx: Dict) -> Dict:
        state["step3"] = "done"
        return state

    graph = (
        create_graph("demo")
        .node("step1", step_one)
        .node("step2", step_two)
        .node("step3", step_three)
        .edge("step1", "step2")
        .edge("step2", "step3")
        .entry_point("step1")
        .middleware(LoggingMiddleware())
        .middleware(TimingMiddleware())
        .snapshots(True)
        .build()
    )

    client = MockInferenceClient(model="mock", cache=cache)

    agent = (
        create_agent("demo_agent")
        .with_graph(graph)
        .with_inference_client(client)
        .with_cache(cache)
        .with_system_prompt("You are a helpful assistant.")
        .build()
    )

    initial_state = {"input": "hello world"}
    final_state, ctx = await agent.run(initial_state)
    print("Final state:", final_state)
    print("Execution order:", ctx.execution_order)
    print("Elapsed ms:", ctx.elapsed_ms)

    response = await agent.chat("What is 2+2?")
    print("Chat response:", response.content)
    print("Token usage:", response.usage)

    await cache.set("test_key", {"foo": "bar"}, ttl=60)
    val = await cache.get("test_key")
    print("Cache get:", val)

    all_keys = await cache.get_all()
    print("All cache keys:", list(all_keys.keys()))


if __name__ == "__main__":
    asyncio.run(_demo())