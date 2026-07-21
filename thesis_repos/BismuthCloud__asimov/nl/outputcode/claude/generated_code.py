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
# Enums
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
# Data classes
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
    tool_calls: Optional[List[Dict[str, Any]]] = None
    usage: Optional[TokenUsage] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


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


# ---------------------------------------------------------------------------
# Cache Interface
# ---------------------------------------------------------------------------

class AbstractCache(ABC):
    """Abstract cache interface."""

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
    """In-memory cache implementation for testing/development."""

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
        for k, v in self._store.items():
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
    """Redis-backed cache implementation."""

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

    async def _get_client(self) -> Any:
        if self._client is None:
            self._client = aioredis.from_url(self.url, db=self.db, decode_responses=True)
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
        if self._client is not None:
            await self._client.close()
            self._client = None


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


class BaseMiddleware(ABC):
    @abstractmethod
    async def before_node(self, ctx: MiddlewareContext) -> None:
        ...

    @abstractmethod
    async def after_node(self, ctx: MiddlewareContext) -> None:
        ...


class LoggingMiddleware(BaseMiddleware):
    def __init__(self, logger: Optional[Any] = None):
        import logging
        self.logger = logger or logging.getLogger(__name__)

    async def before_node(self, ctx: MiddlewareContext) -> None:
        self.logger.info(f"[Graph] Starting node: {ctx.node_id}")

    async def after_node(self, ctx: MiddlewareContext) -> None:
        duration = (time.time() - ctx.start_time) * 1000
        status = ctx.result.status.value if ctx.result else "unknown"
        self.logger.info(
            f"[Graph] Completed node: {ctx.node_id} | status={status} | duration={duration:.2f}ms"
        )


class TracingMiddleware(BaseMiddleware):
    def __init__(self, tracer_name: str = "agent_framework"):
        self._tracer_name = tracer_name
        self._spans: Dict[str, Any] = {}

    def _get_tracer(self) -> Optional[Any]:
        if OTEL_AVAILABLE:
            return trace.get_tracer(self._tracer_name)
        return None

    async def before_node(self, ctx: MiddlewareContext) -> None:
        tracer = self._get_tracer()
        if tracer:
            span = tracer.start_span(f"node.{ctx.node_id}")
            span.set_attribute("node.id", ctx.node_id)
            self._spans[ctx.node_id] = span

    async def after_node(self, ctx: MiddlewareContext) -> None:
        span = self._spans.pop(ctx.node_id, None)
        if span:
            if ctx.result:
                span.set_attribute("node.status", ctx.result.status.value)
                span.set_attribute("node.duration_ms", ctx.result.duration_ms)
                if ctx.result.error:
                    span.record_exception(ctx.result.error)
            span.end()


class CachingMiddleware(BaseMiddleware):
    def __init__(self, cache: AbstractCache, ttl: Optional[int] = None):
        self.cache = cache
        self.ttl = ttl

    async def before_node(self, ctx: MiddlewareContext) -> None:
        cache_key = f"node_result:{ctx.node_id}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            ctx.metadata["cached_result"] = cached

    async def after_node(self, ctx: MiddlewareContext) -> None:
        if ctx.result and ctx.result.status == NodeStatus.COMPLETED:
            cache_key = f"node_result:{ctx.node_id}"
            try:
                serializable = {
                    "node_id": ctx.result.node_id,
                    "status": ctx.result.status.value,
                    "output": ctx.result.output,
                    "duration_ms": ctx.result.duration_ms,
                }
                await self.cache.set(cache_key, serializable, ttl=self.ttl)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Graph Nodes
# ---------------------------------------------------------------------------

NodeFunction = Callable[[GraphState], Any]


class Node:
    def __init__(
        self,
        node_id: str,
        func: NodeFunction,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.node_id = node_id
        self.func = func
        self.metadata: Dict[str, Any] = metadata or {}
        self.status: NodeStatus = NodeStatus.PENDING

    async def execute(self, state: GraphState) -> NodeResult:
        start = time.time()
        try:
            if asyncio.iscoroutinefunction(self.func):
                output = await self.func(state)
            else:
                output = self.func(state)
            duration = (time.time() - start) * 1000
            return NodeResult(
                node_id=self.node_id,
                status=NodeStatus.COMPLETED,
                output=output,
                duration_ms=duration,
            )
        except Exception as exc:
            duration = (time.time() - start) * 1000
            return NodeResult(
                node_id=self.node_id,
                status=NodeStatus.FAILED,
                error=exc,
                duration_ms=duration,
            )


class ConditionalNode(Node):
    def __init__(
        self,
        node_id: str,
        func: NodeFunction,
        condition: Callable[[GraphState], bool],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(node_id, func, metadata)
        self.condition = condition

    async def execute(self, state: GraphState) -> NodeResult:
        try:
            if asyncio.iscoroutinefunction(self.condition):
                should_run = await self.condition(state)
            else:
                should_run = self.condition(state)
        except Exception as exc:
            return NodeResult(
                node_id=self.node_id,
                status=NodeStatus.FAILED,
                error=exc,
            )

        if not should_run:
            return NodeResult(
                node_id=self.node_id,
                status=NodeStatus.SKIPPED,
            )
        return await super().execute(state)


class LLMNode(Node):
    def __init__(
        self,
        node_id: str,
        inference_client: "BaseInferenceClient",
        messages_builder: Callable[[GraphState], List[Message]],
        tools: Optional[List[ToolDefinition]] = None,
        output_key: str = "llm_output",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        async def _llm_func(state: GraphState) -> Any:
            if asyncio.iscoroutinefunction(messages_builder):
                messages = await messages_builder(state)
            else:
                messages = messages_builder(state)
            response = await inference_client.complete(messages, tools=tools)
            state.set(output_key, response.content)
            state.set(f"{output_key}_response", response)
            return response

        super().__init__(node_id, _llm_func, metadata)
        self.inference_client = inference_client
        self.tools = tools
        self.output_key = output_key


# ---------------------------------------------------------------------------
# Graph Edges
# ---------------------------------------------------------------------------

@dataclass
class Edge:
    source: str
    target: str
    edge_type: EdgeType = EdgeType.DEFAULT
    condition: Optional[Callable[[GraphState], bool]] = None
    weight: float = 1.0


# ---------------------------------------------------------------------------
# Graph Execution Engine
# ---------------------------------------------------------------------------

class GraphExecutionError(Exception):
    def __init__(self, message: str, node_id: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message)
        self.node_id = node_id
        self.cause = cause


class Graph:
    def __init__(
        self,
        graph_id: Optional[str] = None,
        enable_snapshots: bool = False,
        max_snapshots: int = 10,
    ):
        self.graph_id = graph_id or str(uuid.uuid4())
        self.enable_snapshots = enable_snapshots
        self.max_snapshots = max_snapshots

        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._adjacency: Dict[str, List[Edge]] = defaultdict(list)
        self._reverse_adjacency: Dict[str, List[str]] = defaultdict(list)
        self._entry_points: Set[str] = set()
        self._middleware: List[BaseMiddleware] = []
        self._snapshots: List[Tuple[str, GraphState]] = []
        self._results: Dict[str, NodeResult] = {}

    def add_node(self, node: Node) -> "Graph":
        self._nodes[node.node_id] = node
        return self

    def add_edge(self, edge: Edge) -> "Graph":
        self._edges.append(edge)
        self._adjacency[edge.source].append(edge)
        self._reverse_adjacency[edge.target].append(edge.source)
        return self

    def set_entry_point(self, node_id: str) -> "Graph":
        if node_id not in self._nodes:
            raise ValueError(f"Node '{node_id}' not found in graph")
        self._entry_points.add(node_id)
        return self

    def add_middleware(self, middleware: BaseMiddleware) -> "Graph":
        self._middleware.append(middleware)
        return self

    def _take_snapshot(self, label: str, state: GraphState) -> None:
        if self.enable_snapshots:
            snapshot = state.snapshot()
            self._snapshots.append((label, snapshot))
            if len(self._snapshots) > self.max_snapshots:
                self._snapshots.pop(0)

    def get_snapshots(self) -> List[Tuple[str, GraphState]]:
        return list(self._snapshots)

    def restore_snapshot(self, index: int) -> GraphState:
        if index < 0 or index >= len(self._snapshots):
            raise IndexError(f"Snapshot index {index} out of range")
        _, snapshot = self._snapshots[index]
        return snapshot.snapshot()

    def _get_ready_nodes(self, completed: Set[str], failed: Set[str], skipped: Set[str]) -> List[str]:
        ready = []
        done = completed | failed | skipped
        for node_id, node in self._nodes.items():
            if node_id in done:
                continue
            deps = self._reverse_adjacency.get(node_id, [])
            if all(d in done for d in deps):
                if not deps and node_id not in self._entry_points and self._entry_points:
                    continue
                ready.append(node_id)
        return ready

    async def _run_node_with_middleware(
        self, node: Node, state: GraphState
    ) -> NodeResult:
        ctx = MiddlewareContext(
            node_id=node.node_id,
            state=state,
            metadata={},
        )

        for mw in self._middleware:
            await mw.before_node(ctx)

        if "cached_result" in ctx.metadata:
            cached = ctx.metadata["cached_result"]
            result = NodeResult(
                node_id=node.node_id,
                status=NodeStatus.COMPLETED,
                output=cached.get("output"),
                duration_ms=cached.get("duration_ms", 0),
                metadata={"from_cache": True},
            )
        else:
            result = await node.execute(state)

        ctx.result = result

        for mw in reversed(self._middleware):
            await mw.after_node(ctx)

        return result

    async def execute(
        self,
        initial_state: Optional[GraphState] = None,
        max_iterations: int = 1000,
    ) -> Tuple[GraphState, Dict[str, NodeResult]]:
        state = initial_state or GraphState()
        self._results = {}
        completed: Set[str] = set()
        failed: Set[str] = set()
        skipped: Set[str] = set()

        self._take_snapshot("initial", state)

        if self._entry_points:
            queue = list(self._entry_points)
        else:
            queue = [
                nid for nid in self._nodes
                if not self._reverse_adjacency.get(nid)
            ]

        iterations = 0
        pending: Set[str] = set(queue)

        while pending and iterations < max_iterations:
            iterations += 1
            current_batch = list(pending)
            pending = set()

            tasks = []
            for node_id in current_batch:
                node = self._nodes.get(node_id)
                if node is None:
                    continue
                deps = self._reverse_adjacency.get(node_id, [])
                done = completed | failed | skipped
                if not all(d in done for d in deps):
                    pending.add(node_id)
                    continue
                tasks.append((node_id, node))

            if not tasks:
                break

            results = await asyncio.gather(
                *[self._run_node_with_middleware(node, state) for _, node in tasks],
                return_exceptions=False,
            )

            for (node_id, _), result in zip(tasks, results):
                self._results[node_id] = result
                if result.status == NodeStatus.COMPLETED:
                    completed.add(node_id)
                elif result.status == NodeStatus.FAILED:
                    failed.add(node_id)
                elif result.status == NodeStatus.SKIPPED:
                    skipped.add(node_id)

                self._take_snapshot(f"after_{node_id}", state)

                for edge in self._adjacency.get(node_id, []):
                    if edge.edge_type == EdgeType.CONDITIONAL and edge.condition:
                        try:
                            if asyncio.iscoroutinefunction(edge.condition):
                                should_follow = await edge.condition(state)
                            else:
                                should_follow = edge.condition(state)
                        except Exception:
                            should_follow = False
                        if not should_follow:
                            continue
                    if edge.target not in (completed | failed | skipped):
                        pending.add(edge.target)

        self._take_snapshot("final", state)
        return state, self._results

    def get_results(self) -> Dict[str, NodeResult]:
        return dict(self._results)

    def visualize(self) -> str:
        lines = [f"Graph: {self.graph_id}"]
        lines.append("Nodes:")
        for nid in self._nodes:
            marker = " [ENTRY]" if nid in self._entry_points else ""
            lines.append(f"  - {nid}{marker}")
        lines.append("Edges:")
        for edge in self._edges:
            cond = " [conditional]" if edge.edge_type == EdgeType.CONDITIONAL else ""
            lines.append(f"  {edge.source} -> {edge.target}{cond}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Graph Builder (fluent API)
# ---------------------------------------------------------------------------

class GraphBuilder:
    def __init__(self, graph_id: Optional[str] = None):
        self._graph = Graph(graph_id=graph_id)

    def with_snapshots(self, max_snapshots: int = 10) -> "GraphBuilder":
        self._graph.enable_snapshots = True
        self._graph.max_snapshots = max_snapshots
        return self

    def add_node(
        self,
        node_id: str,
        func: NodeFunction,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "GraphBuilder":
        self._graph.add_node(Node(node_id, func, metadata))
        return self

    def add_conditional_node(
        self,
        node_id: str,
        func: NodeFunction,
        condition: Callable[[GraphState], bool],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "GraphBuilder":
        self._graph.add_node(ConditionalNode(node_id, func, condition, metadata))
        return self

    def add_llm_node(
        self,
        node_id: str,
        inference_client: "BaseInferenceClient",
        messages_builder: Callable[[GraphState], List[Message]],
        tools: Optional[List[ToolDefinition]] = None,
        output_key: str = "llm_output",
    ) -> "GraphBuilder":
        self._graph.add_node(
            LLMNode(node_id, inference_client, messages_builder, tools, output_key)
        )
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType = EdgeType.DEFAULT,
        condition: Optional[Callable[[GraphState], bool]] = None,
    ) -> "GraphBuilder":
        self._graph.add_edge(Edge(source, target, edge_type, condition))
        return self

    def set_entry_point(self, node_id: str) -> "GraphBuilder":
        self._graph.set_entry_point(node_id)
        return self

    def add_middleware(self, middleware: BaseMiddleware) -> "GraphBuilder":
        self._graph.add_middleware(middleware)
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
        tracer_name: str = "inference_client",
        cache: Optional[AbstractCache] = None,
        prompt_caching: bool = False,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.cache = cache
        self.prompt_caching = prompt_caching
        self._total_usage = TokenUsage()
        self._tracer_name = tracer_name

    def _get_tracer(self) -> Optional[Any]:
        if OTEL_AVAILABLE:
            return trace.get_tracer(self._tracer_name)
        return None

    def _messages_to_cache_key(self, messages: List[Message], tools: Optional[List[ToolDefinition]]) -> str:
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "tools": [t.to_dict() for t in tools] if tools else None,
        }
        return f"inference:{hash(json.dumps(payload, sort_keys=True))}"

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        ...

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        ...

    def get_total_usage(self) -> TokenUsage:
        return self._total_usage

    def reset_usage(self) -> None:
        self._total_usage = TokenUsage()


class MockInferenceClient(BaseInferenceClient):
    """Mock inference client for testing."""

    def __init__(
        self,
        model: str = "mock-model",
        response_template: str = "Mock response for: {prompt}",
        cache: Optional[AbstractCache] = None,
        prompt_caching: bool = False,
    ):
        super().__init__(model=model, cache=cache, prompt_caching=prompt_caching)
        self.response_template = response_template
        self._call_count = 0

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        self._call_count += 1

        if self.cache and self.prompt_caching:
            cache_key = self._messages_to_cache_key(messages, tools)
            cached = await self.cache.get(cache_key)
            if cached:
                return InferenceResponse(**cached)

        last_user_msg = ""
        for m in reversed(messages):
            if m.role == MessageRole.USER:
                last_user_msg = m.content
                break

        content = self.response_template.format(prompt=last_user_msg)
        usage = TokenUsage(
            prompt_tokens=len(last_user_msg.split()),
            completion_tokens=len(content.split()),
            total_tokens=len(last_user_msg.split()) + len(content.split()),
        )
        self._total_usage = self._total_usage + usage

        response = InferenceResponse(
            content=content,
            usage=usage,
            model=self.model,
            finish_reason="stop",
        )

        if self.cache and self.prompt_caching:
            cache_key = self._messages_to_cache_key(messages, tools)
            await self.cache.set(cache_key, {
                "content": response.content,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "cached_tokens": usage.cached_tokens,
                },
                "model": response.model,
                "finish_reason": response.finish_reason,
            })

        return response

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        response = await self.complete(messages, tools, temperature, max_tokens, **kwargs)
        words = response.content.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0)


class OpenAIInferenceClient(BaseInferenceClient):
    """OpenAI inference client."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        cache: Optional[AbstractCache] = None,
        prompt_caching: bool = False,
        tracer_name: str = "openai_client",
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            cache=cache,
            prompt_caching=prompt_caching,
            tracer_name=tracer_name,
        )
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        try:
            import openai
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")
        if self._client is None:
            kwargs: Dict[str, Any] = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = openai.AsyncOpenAI(**kwargs)
        return self._client

    def _build_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in messages]

    def _build_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in tools]

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        if self.cache and self.prompt_caching:
            cache_key = self._messages_to_cache_key(messages, tools)
            cached = await self.cache.get(cache_key)
            if cached:
                return InferenceResponse(**cached)

        client = self._get_client()
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": self._build_messages(messages),
            "temperature": temperature,
        }
        if max_tokens:
            params["max_tokens"] = max_tokens
        if tools:
            params["tools"] = self._build_tools(tools)
        params.update(kwargs)

        tracer = self._get_tracer()
        span = None
        if tracer:
            span = tracer.start_span("openai.complete")
            span.set_attribute("llm.model", self.model)

        try:
            raw = await client.chat.completions.create(**params)
            choice = raw.choices[0]
            content = choice.message.content or ""
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

            usage = None
            if raw.usage:
                usage = TokenUsage(
                    prompt_tokens=raw.usage.prompt_tokens,
                    completion_tokens=raw.usage.completion_tokens,
                    total_tokens=raw.usage.total_tokens,
                    cached_tokens=getattr(raw.usage, "cached_tokens", 0) or 0,
                )
                self._total_usage = self._total_usage + usage

            response = InferenceResponse(
                content=content,
                tool_calls=tool_calls,
                usage=usage,
                model=raw.model,
                finish_reason=choice.finish_reason,
                raw=raw.model_dump() if hasattr(raw, "model_dump") else None,
            )

            if self.cache and self.prompt_caching:
                cache_key = self._messages_to_cache_key(messages, tools)
                await self.cache.set(cache_key, {
                    "content": response.content,
                    "tool_calls": response.tool_calls,
                    "model": response.model,
                    "finish_reason": response.finish_reason,
                })

            if span:
                span.set_attribute("llm.usage.total_tokens", usage.total_tokens if usage else 0)

            return response
        except Exception as exc:
            if span:
                span.record_exception(exc)
            raise
        finally:
            if span:
                span.end()

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": self._build_messages(messages),
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            params["max_tokens"] = max_tokens
        if tools:
            params["tools"] = self._build_tools(tools)
        params.update(kwargs)

        async with await client.chat.completions.create(**params) as stream:
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content


class AnthropicInferenceClient(BaseInferenceClient):
    """Anthropic Claude inference client."""

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        cache: Optional[AbstractCache] = None,
        prompt_caching: bool = False,
        tracer_name: str = "anthropic_client",
        max_tokens: int = 4096,
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            cache=cache,
            prompt_caching=prompt_caching,
            tracer_name=tracer_name,
        )
        self._default_max_tokens = max_tokens
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")
        if self._client is None:
            kwargs: Dict[str, Any] = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            self._client = anthropic.AsyncAnthropic(**kwargs)
        return self._client

    def _split_messages(
        self, messages: List[Message]
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        system_content = None
        chat_messages = []
        for m in messages:
            if m.role == MessageRole.SYSTEM:
                system_content = m.content
            else:
                chat_messages.append(m.to_dict())
        return system_content, chat_messages

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        if self.cache and self.prompt_caching:
            cache_key = self._messages_to_cache_key(messages, tools)
            cached = await self.cache.get(cache_key)
            if cached:
                return InferenceResponse(**cached)

        client = self._get_client()
        system_content, chat_messages = self._split_messages(messages)

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": max_tokens or self._default_max_tokens,
            "temperature": temperature,
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

        tracer = self._get_tracer()
        span = None
        if tracer:
            span = tracer.start_span("anthropic.complete")
            span.set_attribute("llm.model", self.model)

        try:
            raw = await client.messages.create(**params)
            content = ""
            tool_calls = None

            for block in raw.content:
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

            usage = None
            if raw.usage:
                usage = TokenUsage(
                    prompt_tokens=raw.usage.input_tokens,
                    completion_tokens=raw.usage.output_tokens,
                    total_tokens=raw.usage.input_tokens + raw.usage.output_tokens,
                    cached_tokens=getattr(raw.usage, "cache_read_input_tokens", 0) or 0,
                )
                self._total_usage = self._total_usage + usage

            response = InferenceResponse(
                content=content,
                tool_calls=tool_calls,
                usage=usage,
                model=raw.model,
                finish_reason=raw.stop_reason,
            )

            if self.cache and self.prompt_caching:
                cache_key = self._messages_to_cache_key(messages, tools)
                await self.cache.set(cache_key, {
                    "content": response.content,
                    "tool_calls": response.tool_calls,
                    "model": response.model,
                    "finish_reason": response.finish_reason,
                })

            if span:
                span.set_attribute("llm.usage.total_tokens", usage.total_tokens if usage else 0)

            return response
        except Exception as exc:
            if span:
                span.record_exception(exc)
            raise
        finally:
            if span:
                span.end()

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        system_content, chat_messages = self._split_messages(messages)

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": max_tokens or self._default_max_tokens,
            "temperature": temperature,
        }
        if system_content:
            params["system"] = system_content
        params.update(kwargs)

        async with client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                yield text


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Agent:
    def __init__(
        self,
        agent_id: Optional[str] = None,
        inference_client: Optional[BaseInferenceClient] = None,
        tools: Optional[List[ToolDefinition]] = None,
        system_prompt: Optional[str] = None,
        cache: Optional[AbstractCache] = None,
        max_iterations: int = 10,
    ):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.inference_client = inference_client
        self.tools = tools or []
        self.system_prompt = system_prompt
        self.cache = cache
        self.max_iterations = max_iterations
        self._conversation_history: List[Message] = []
        self._tool_handlers: Dict[str, Callable] = {}

        if system_prompt:
            self._conversation_history.append(
                Message(role=MessageRole.SYSTEM, content=system_prompt)
            )

    def register_tool(self, tool_def: ToolDefinition, handler: Callable) -> None:
        self.tools.append(tool_def)
        self._tool_handlers[tool_def.name] = handler

    def add_message(self, message: Message) -> None:
        self._conversation_history.append(message)

    def get_history(self) -> List[Message]:
        return list(self._conversation_history)

    def clear_history(self) -> None:
        self._conversation_history = []
        if self.system_prompt:
            self._conversation_history.append(
                Message(role=MessageRole.SYSTEM, content=self.system_prompt)
            )

    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        handler = self._tool_handlers.get(tool_name)
        if handler is None:
            raise ValueError(f"No handler registered for tool: {tool_name}")
        if asyncio.iscoroutinefunction(handler):
            return await handler(**arguments)
        return handler(**arguments)

    async def run(self, user_input: str) -> str:
        if self.inference_client is None:
            raise ValueError("No inference client configured")

        self._conversation_history.append(
            Message(role=MessageRole.USER, content=user_input)
        )

        for _ in range(self.max_iterations):
            response = await self.inference_client.complete(
                self._conversation_history,
                tools=self.tools if self.tools else None,
            )

            self._conversation_history.append(
                Message(role=MessageRole.ASSISTANT, content=response.content or "")
            )

            if not response.tool_calls:
                return response.content or ""

            for tool_call in response.tool_calls:
                tool_name = tool_call["function"]["name"]
                try:
                    arguments = json.loads(tool_call["function"]["arguments"])
                except (json.JSONDecodeError, KeyError):
                    arguments = {}

                try:
                    result = await self._execute_tool(tool_name, arguments)
                    result_str = json.dumps(result) if not isinstance(result, str) else result
                except Exception as exc:
                    result_str = f"Error: {str(exc)}"

                self._conversation_history.append(
                    Message(
                        role=MessageRole.TOOL,
                        content=result_str,
                        tool_call_id=tool_call.get("id"),
                        name=tool_name,
                    )
                )

        return "Max iterations reached"

    async def stream_run(self, user_input: str) -> AsyncGenerator[str, None]:
        if self.inference_client is None:
            raise ValueError("No inference client configured")

        self._conversation_history.append(
            Message(role=MessageRole.USER, content=user_input)
        )

        full_content = ""
        async for chunk in self.inference_client.stream(
            self._conversation_history,
            tools=self.tools if self.tools else None,
        ):
            full_content += chunk
            yield chunk

        self._conversation_history.append(
            Message(role=MessageRole.ASSISTANT, content=full_content)
        )


# ---------------------------------------------------------------------------
# LLM Directed Graph Execution
# ---------------------------------------------------------------------------

class LLMDirectedGraph:
    """A graph where an LLM decides which node to execute next."""

    def __init__(
        self,
        inference_client: BaseInferenceClient,
        nodes: Dict[str, Node],
        system_prompt: Optional[str] = None,
        max_steps: int = 20,
    ):
        self.inference_client = inference_client
        self.nodes = nodes
        self.system_prompt = system_prompt or (
            "You are a task orchestrator. Given the current state and available nodes, "
            "decide which node to execute next. Respond with just the node name or 'DONE' to finish."
        )
        self.max_steps = max_steps
        self._middleware: List[BaseMiddleware] = []
        self._results: Dict[str, NodeResult] = {}

    def add_middleware(self, middleware: BaseMiddleware) -> "LLMDirectedGraph":
        self._middleware.append(middleware)
        return self

    async def _decide_next_node(self, state: GraphState, executed: List[str]) -> Optional[str]:
        node_descriptions = "\n".join(
            f"- {nid}: {node.metadata.get('description', 'No description')}"
            for nid, node in self.nodes.items()
            if nid not in executed
        )

        messages = [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt),
            Message(
                role=MessageRole.USER,
                content=(
                    f"Current state: {json.dumps(state.data, default=str)}\n"
                    f"Already executed: {executed}\n"
                    f"Available nodes:\n{node_descriptions}\n\n"
                    "Which node should execute next? Reply with just the node name or 'DONE'."
                ),
            ),
        ]

        response = await self.inference_client.complete(messages)
        decision = response.content.strip()

        if decision.upper() == "DONE":
            return None

        for node_id in self.nodes:
            if node_id.lower() == decision.lower() or decision.lower() in node_id.lower():
                return node_id

        return None

    async def execute(
        self, initial_state: Optional[GraphState] = None
    ) -> Tuple[GraphState, Dict[str, NodeResult]]:
        state = initial_state or GraphState()
        executed: List[str] = []
        self._results = {}

        for _ in range(self.max_steps):
            next_node_id = await self._decide_next_node(state, executed)
            if next_node_id is None:
                break

            node = self.nodes.get(next_node_id)
            if node is None:
                break

            ctx = MiddlewareContext(node_id=next_node_id, state=state, metadata={})
            for mw in self._middleware:
                await mw.before_node(ctx)

            result = await node.execute(state)
            self._results[next_node_id] = result
            executed.append(next_node_id)

            ctx.result = result
            for mw in reversed(self._middleware):
                await mw.after_node(ctx)

            if result.status == NodeStatus.FAILED:
                break

        return state, self._results


# ---------------------------------------------------------------------------
# OpenTelemetry Integration
# ---------------------------------------------------------------------------

class OTelInstrumentation:
    """OpenTelemetry instrumentation helper."""

    def __init__(self, service_name: str = "agent-framework"):
        self.service_name = service_name
        self._tracer: Optional[Any] = None

    def setup(
        self,
        endpoint: Optional[str] = None,
        export_to_console: bool = False,
    ) -> None:
        if not OTEL_AVAILABLE:
            raise ImportError(
                "opentelemetry packages required. Install with: "
                "pip install opentelemetry-api opentelemetry-sdk"
            )
        try:
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
            from opentelemetry.sdk.resources import Resource

            resource = Resource.create({"service.name": self.service_name})
            provider = TracerProvider(resource=resource)

            if export_to_console:
                provider.add_span_processor(
                    BatchSpanProcessor(ConsoleSpanExporter())
                )

            if endpoint:
                try:
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                    otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
                    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                except ImportError:
                    pass

            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(self.service_name)
        except ImportError as exc:
            raise ImportError(f"OpenTelemetry SDK not available: {exc}")

    def get_tracer(self) -> Optional[Any]:
        return self._tracer

    def create_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Any:
        if not OTEL_AVAILABLE or self._tracer is None:
            return None
        span = self._tracer.start_span(name)
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, str(v))
        return span


# ---------------------------------------------------------------------------
# Framework Entry Point / Registry
# ---------------------------------------------------------------------------

class AgentFramework:
    """Main framework registry and factory."""

    _instance: Optional["AgentFramework"] = None

    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._graphs: Dict[str, Graph] = {}
        self._caches: Dict[str, AbstractCache] = {}
        self._inference_clients: Dict[str, BaseInferenceClient] = {}
        self._otel: Optional[OTelInstrumentation] = None

    @classmethod
    def get_instance(cls) -> "AgentFramework":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_agent(self, agent: Agent) -> None:
        self._agents[agent.agent_id] = agent

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    def register_graph(self, graph: Graph) -> None:
        self._graphs[graph.graph_id] = graph

    def get_graph(self, graph_id: str) -> Optional[Graph]:
        return self._graphs.get(graph_id)

    def register_cache(self, name: str, cache: AbstractCache) -> None:
        self._caches[name] = cache

    def get_cache(self, name: str) -> Optional[AbstractCache]:
        return self._caches.get(name)

    def register_inference_client(self, name: str, client: BaseInferenceClient) -> None:
        self._inference_clients[name] = client

    def get_inference_client(self, name: str) -> Optional[BaseInferenceClient]:
        return self._inference_clients.get(name)

    def setup_otel(
        self,
        service_name: str = "agent-framework",
        endpoint: Optional[str] = None,
        export_to_console: bool = False,
    ) -> OTelInstrumentation:
        self._otel = OTelInstrumentation(service_name=service_name)
        self._otel.setup(endpoint=endpoint, export_to_console=export_to_console)
        return self._otel

    def create_graph_builder(self, graph_id: Optional[str] = None) -> GraphBuilder:
        return GraphBuilder(graph_id=graph_id)

    def create_agent(
        self,
        inference_client: Optional[BaseInferenceClient] = None,
        tools: Optional[List[ToolDefinition]] = None,
        system_prompt: Optional[str] = None,
        cache: Optional[AbstractCache] = None,
    ) -> Agent:
        agent = Agent(
            inference_client=inference_client,
            tools=tools,
            system_prompt=system_prompt,
            cache=cache,
        )
        self.register_agent(agent)
        return agent

    def create_in_memory_cache(self, prefix: str = "", suffix: str = "") -> InMemoryCache:
        cache = InMemoryCache(prefix=prefix, suffix=suffix)
        return cache

    def create_redis_cache(
        self,
        url: str = "redis://localhost:6379",
        prefix: str = "",
        suffix: str = "",
        db: int = 0,
    ) -> RedisCache:
        return RedisCache(url=url, prefix=prefix, suffix=suffix, db=db)


# ---------------------------------------------------------------------------
# Convenience exports
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "NodeStatus",
    "EdgeType",
    "MessageRole",
    # Data classes
    "Message",
    "TokenUsage",
    "ToolDefinition",
    "InferenceResponse",
    "GraphState",
    "NodeResult",
    # Cache
    "AbstractCache",
    "InMemoryCache",
    "RedisCache",
    # Middleware
    "MiddlewareContext",
    "BaseMiddleware",
    "LoggingMiddleware",
    "TracingMiddleware",
    "CachingMiddleware",
    # Graph
    "Node",
    "ConditionalNode",
    "LLMNode",
    "Edge",
    "Graph",
    "GraphBuilder",
    "GraphExecutionError",
    # Inference
    "BaseInferenceClient",
    "MockInferenceClient",
    "OpenAIInferenceClient",
    "AnthropicInferenceClient",
    # Agent
    "Agent",
    # LLM Directed Graph
    "LLMDirectedGraph",
    # OTel
    "OTelInstrumentation",
    # Framework
    "AgentFramework",
]