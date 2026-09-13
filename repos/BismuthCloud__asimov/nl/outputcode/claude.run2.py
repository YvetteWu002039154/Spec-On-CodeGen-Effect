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
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> "GraphState":
        import copy
        return GraphState(
            data=copy.deepcopy(self.data),
            messages=list(self.messages),
            metadata=copy.deepcopy(self.metadata),
        )

    def update(self, updates: Dict[str, Any]) -> None:
        self.data.update(updates)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value


# ---------------------------------------------------------------------------
# Cache System
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
    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        pass

    @abstractmethod
    async def clear(self, pattern: str = "*") -> None:
        pass

    @abstractmethod
    async def publish(self, mailbox: str, message: Any) -> None:
        pass

    @abstractmethod
    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass


class InMemoryCache(AbstractCache):
    def __init__(self, prefix: str = "", suffix: str = ""):
        self._store: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}
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
        if full_key in self._ttl:
            return time.time() > self._ttl[full_key]
        return False

    async def get(self, key: str) -> Optional[Any]:
        full_key = self._make_key(key)
        if self._is_expired(full_key):
            del self._store[full_key]
            del self._ttl[full_key]
            return None
        return self._store.get(full_key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        full_key = self._make_key(key)
        self._store[full_key] = value
        if ttl is not None:
            self._ttl[full_key] = time.time() + ttl

    async def delete(self, key: str) -> None:
        full_key = self._make_key(key)
        self._store.pop(full_key, None)
        self._ttl.pop(full_key, None)

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        import fnmatch
        result = {}
        for k, v in list(self._store.items()):
            if not self._is_expired(k) and fnmatch.fnmatch(k, pattern):
                result[k] = v
        return result

    async def clear(self, pattern: str = "*") -> None:
        import fnmatch
        keys_to_delete = [k for k in list(self._store.keys()) if fnmatch.fnmatch(k, pattern)]
        for k in keys_to_delete:
            del self._store[k]
            self._ttl.pop(k, None)

    async def publish(self, mailbox: str, message: Any) -> None:
        await self._mailboxes[mailbox].put(message)

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        queue = self._mailboxes[mailbox]
        while True:
            message = await queue.get()
            yield message

    async def exists(self, key: str) -> bool:
        full_key = self._make_key(key)
        if self._is_expired(full_key):
            return False
        return full_key in self._store


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
        return json.loads(value)

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

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        client = await self._get_client()
        keys = await client.keys(pattern)
        result = {}
        if keys:
            values = await client.mget(keys)
            for k, v in zip(keys, values):
                if v is not None:
                    result[k] = json.loads(v)
        return result

    async def clear(self, pattern: str = "*") -> None:
        client = await self._get_client()
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)

    async def publish(self, mailbox: str, message: Any) -> None:
        client = await self._get_client()
        serialized = json.dumps(message)
        await client.publish(mailbox, serialized)

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        client = await self._get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(mailbox)
        async for msg in pubsub.listen():
            if msg["type"] == "message":
                yield json.loads(msg["data"])

    async def exists(self, key: str) -> bool:
        client = await self._get_client()
        full_key = self._make_key(key)
        return bool(await client.exists(full_key))

    async def close(self) -> None:
        if self._client:
            await self._client.close()


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class MiddlewareContext:
    def __init__(self, node_name: str, state: GraphState, metadata: Dict[str, Any]):
        self.node_name = node_name
        self.state = state
        self.metadata = metadata
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self.error: Optional[Exception] = None
        self.result: Optional[Any] = None


class Middleware(ABC):
    @abstractmethod
    async def before_node(self, context: MiddlewareContext) -> None:
        pass

    @abstractmethod
    async def after_node(self, context: MiddlewareContext) -> None:
        pass

    @abstractmethod
    async def on_error(self, context: MiddlewareContext, error: Exception) -> None:
        pass


class LoggingMiddleware(Middleware):
    def __init__(self, logger: Optional[Any] = None):
        import logging
        self.logger = logger or logging.getLogger(__name__)

    async def before_node(self, context: MiddlewareContext) -> None:
        self.logger.info(f"[Graph] Starting node: {context.node_name}")

    async def after_node(self, context: MiddlewareContext) -> None:
        elapsed = (context.end_time or time.time()) - context.start_time
        self.logger.info(f"[Graph] Completed node: {context.node_name} in {elapsed:.3f}s")

    async def on_error(self, context: MiddlewareContext, error: Exception) -> None:
        self.logger.error(f"[Graph] Error in node {context.node_name}: {error}")


class OpenTelemetryMiddleware(Middleware):
    def __init__(self, tracer_name: str = "agent_framework"):
        if not OTEL_AVAILABLE:
            raise ImportError("opentelemetry package is required. Install with: pip install opentelemetry-api")
        self.tracer: Tracer = trace.get_tracer(tracer_name)
        self._spans: Dict[str, Any] = {}

    async def before_node(self, context: MiddlewareContext) -> None:
        span = self.tracer.start_span(f"node.{context.node_name}")
        span.set_attribute("node.name", context.node_name)
        self._spans[context.node_name] = span

    async def after_node(self, context: MiddlewareContext) -> None:
        span = self._spans.pop(context.node_name, None)
        if span:
            elapsed = (context.end_time or time.time()) - context.start_time
            span.set_attribute("node.duration_ms", elapsed * 1000)
            span.end()

    async def on_error(self, context: MiddlewareContext, error: Exception) -> None:
        span = self._spans.pop(context.node_name, None)
        if span:
            span.record_exception(error)
            span.set_status(trace.StatusCode.ERROR, str(error))
            span.end()


class TimingMiddleware(Middleware):
    def __init__(self):
        self.timings: Dict[str, List[float]] = defaultdict(list)

    async def before_node(self, context: MiddlewareContext) -> None:
        context.metadata["_timing_start"] = time.time()

    async def after_node(self, context: MiddlewareContext) -> None:
        start = context.metadata.get("_timing_start", context.start_time)
        elapsed = time.time() - start
        self.timings[context.node_name].append(elapsed)

    async def on_error(self, context: MiddlewareContext, error: Exception) -> None:
        start = context.metadata.get("_timing_start", context.start_time)
        elapsed = time.time() - start
        self.timings[context.node_name].append(elapsed)

    def get_average(self, node_name: str) -> Optional[float]:
        times = self.timings.get(node_name)
        if not times:
            return None
        return sum(times) / len(times)


# ---------------------------------------------------------------------------
# Graph Primitives
# ---------------------------------------------------------------------------

class Node:
    def __init__(
        self,
        name: str,
        func: Callable,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.func = func
        self.metadata = metadata or {}
        self.status: NodeStatus = NodeStatus.PENDING

    async def execute(self, state: GraphState) -> Any:
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(state)
        return self.func(state)

    def __repr__(self) -> str:
        return f"Node(name={self.name!r}, status={self.status})"


class Edge:
    def __init__(
        self,
        source: str,
        target: str,
        edge_type: EdgeType = EdgeType.DEFAULT,
        condition: Optional[Callable[[GraphState], bool]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.source = source
        self.target = target
        self.edge_type = edge_type
        self.condition = condition
        self.metadata = metadata or {}

    def should_traverse(self, state: GraphState) -> bool:
        if self.condition is None:
            return True
        return self.condition(state)

    def __repr__(self) -> str:
        return f"Edge(source={self.source!r}, target={self.target!r}, type={self.edge_type})"


class StateSnapshot:
    def __init__(self, state: GraphState, node_name: str, timestamp: Optional[float] = None):
        self.state = state.snapshot()
        self.node_name = node_name
        self.timestamp = timestamp or time.time()
        self.snapshot_id = str(uuid.uuid4())

    def __repr__(self) -> str:
        return f"StateSnapshot(node={self.node_name!r}, id={self.snapshot_id!r})"


class Graph:
    START = "__start__"
    END = "__end__"

    def __init__(self, name: str = "graph"):
        self.name = name
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._middleware: List[Middleware] = []
        self._snapshots: List[StateSnapshot] = []
        self._snapshot_enabled: bool = False
        self._compiled: bool = False

    def add_node(self, name: str, func: Callable, metadata: Optional[Dict[str, Any]] = None) -> "Graph":
        if name in self._nodes:
            raise ValueError(f"Node '{name}' already exists in graph")
        self._nodes[name] = Node(name=name, func=func, metadata=metadata or {})
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType = EdgeType.DEFAULT,
        condition: Optional[Callable[[GraphState], bool]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Graph":
        edge = Edge(
            source=source,
            target=target,
            edge_type=edge_type,
            condition=condition,
            metadata=metadata or {},
        )
        self._edges.append(edge)
        return self

    def add_conditional_edge(
        self,
        source: str,
        condition: Callable[[GraphState], str],
        target_map: Optional[Dict[str, str]] = None,
    ) -> "Graph":
        def make_condition(target: str, cond: Callable, tmap: Optional[Dict[str, str]]) -> Callable[[GraphState], bool]:
            def check(state: GraphState) -> bool:
                result = cond(state)
                if tmap:
                    return tmap.get(result) == target
                return result == target
            return check

        if target_map:
            for result_key, target_node in target_map.items():
                edge = Edge(
                    source=source,
                    target=target_node,
                    edge_type=EdgeType.CONDITIONAL,
                    condition=make_condition(target_node, condition, target_map),
                )
                self._edges.append(edge)
        return self

    def add_middleware(self, middleware: Middleware) -> "Graph":
        self._middleware.append(middleware)
        return self

    def enable_snapshots(self, enabled: bool = True) -> "Graph":
        self._snapshot_enabled = enabled
        return self

    def compile(self) -> "Graph":
        self._validate()
        self._compiled = True
        return self

    def _validate(self) -> None:
        for edge in self._edges:
            if edge.source != self.START and edge.source not in self._nodes:
                raise ValueError(f"Edge source '{edge.source}' not found in nodes")
            if edge.target != self.END and edge.target not in self._nodes:
                raise ValueError(f"Edge target '{edge.target}' not found in nodes")

    def _get_next_nodes(self, current: str, state: GraphState) -> List[str]:
        next_nodes = []
        for edge in self._edges:
            if edge.source == current and edge.should_traverse(state):
                next_nodes.append(edge.target)
        return next_nodes

    def _get_start_nodes(self) -> List[str]:
        return self._get_next_nodes(self.START, GraphState())

    async def _run_middleware_before(self, context: MiddlewareContext) -> None:
        for mw in self._middleware:
            await mw.before_node(context)

    async def _run_middleware_after(self, context: MiddlewareContext) -> None:
        for mw in self._middleware:
            await mw.after_node(context)

    async def _run_middleware_error(self, context: MiddlewareContext, error: Exception) -> None:
        for mw in self._middleware:
            await mw.on_error(context, error)

    async def _execute_node(self, node: Node, state: GraphState) -> Any:
        context = MiddlewareContext(
            node_name=node.name,
            state=state,
            metadata={},
        )
        await self._run_middleware_before(context)
        node.status = NodeStatus.RUNNING

        try:
            result = await node.execute(state)
            node.status = NodeStatus.COMPLETED
            context.end_time = time.time()
            context.result = result
            await self._run_middleware_after(context)

            if self._snapshot_enabled:
                snapshot = StateSnapshot(state=state, node_name=node.name)
                self._snapshots.append(snapshot)

            return result
        except Exception as e:
            node.status = NodeStatus.FAILED
            context.end_time = time.time()
            context.error = e
            await self._run_middleware_error(context, e)
            raise

    async def invoke(self, state: Optional[GraphState] = None) -> GraphState:
        if not self._compiled:
            self.compile()

        if state is None:
            state = GraphState()

        for node in self._nodes.values():
            node.status = NodeStatus.PENDING

        queue: List[str] = self._get_start_nodes()
        visited: Set[str] = set()

        while queue:
            current_name = queue.pop(0)

            if current_name == self.END:
                break

            if current_name in visited:
                continue

            if current_name not in self._nodes:
                continue

            visited.add(current_name)
            node = self._nodes[current_name]

            await self._execute_node(node, state)

            next_nodes = self._get_next_nodes(current_name, state)
            for next_node in next_nodes:
                if next_node != self.END and next_node not in visited:
                    queue.append(next_node)
                elif next_node == self.END:
                    queue.append(next_node)

        return state

    async def stream(self, state: Optional[GraphState] = None) -> AsyncGenerator[Tuple[str, GraphState], None]:
        if not self._compiled:
            self.compile()

        if state is None:
            state = GraphState()

        for node in self._nodes.values():
            node.status = NodeStatus.PENDING

        queue: List[str] = self._get_start_nodes()
        visited: Set[str] = set()

        while queue:
            current_name = queue.pop(0)

            if current_name == self.END:
                break

            if current_name in visited:
                continue

            if current_name not in self._nodes:
                continue

            visited.add(current_name)
            node = self._nodes[current_name]

            await self._execute_node(node, state)
            yield current_name, state.snapshot()

            next_nodes = self._get_next_nodes(current_name, state)
            for next_node in next_nodes:
                if next_node != self.END and next_node not in visited:
                    queue.append(next_node)
                elif next_node == self.END:
                    queue.append(next_node)

    def get_snapshots(self) -> List[StateSnapshot]:
        return list(self._snapshots)

    def restore_snapshot(self, snapshot_id: str) -> Optional[GraphState]:
        for snapshot in self._snapshots:
            if snapshot.snapshot_id == snapshot_id:
                return snapshot.state.snapshot()
        return None

    def get_node(self, name: str) -> Optional[Node]:
        return self._nodes.get(name)

    def get_nodes(self) -> Dict[str, Node]:
        return dict(self._nodes)

    def get_edges(self) -> List[Edge]:
        return list(self._edges)

    def __repr__(self) -> str:
        return f"Graph(name={self.name!r}, nodes={list(self._nodes.keys())})"


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
        cache: Optional[AbstractCache] = None,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.cache = cache
        self._total_usage = TokenUsage()

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> InferenceResponse:
        pass

    @abstractmethod
    async def stream_complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        pass

    def get_total_usage(self) -> TokenUsage:
        return self._total_usage

    def _update_usage(self, usage: TokenUsage) -> None:
        self._total_usage = self._total_usage + usage

    def _make_cache_key(self, messages: List[Message], **kwargs: Any) -> str:
        key_data = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            **kwargs,
        }
        return f"inference:{hash(json.dumps(key_data, sort_keys=True))}"

    async def _get_cached_response(self, cache_key: str) -> Optional[InferenceResponse]:
        if self.cache is None:
            return None
        cached = await self.cache.get(cache_key)
        if cached:
            return InferenceResponse(**cached)
        return None

    async def _cache_response(self, cache_key: str, response: InferenceResponse, ttl: Optional[int] = None) -> None:
        if self.cache is None:
            return
        data = {
            "content": response.content,
            "tool_calls": response.tool_calls,
            "model": response.model,
            "finish_reason": response.finish_reason,
        }
        if response.usage:
            data["usage"] = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "cached_tokens": response.usage.cached_tokens,
            }
        await self.cache.set(cache_key, data, ttl=ttl)


class OpenAIInferenceClient(BaseInferenceClient):
    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
        cache: Optional[AbstractCache] = None,
        enable_prompt_caching: bool = False,
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            cache=cache,
        )
        self.enable_prompt_caching = enable_prompt_caching
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        try:
            import openai
        except ImportError:
            raise ImportError("openai package is required. Install with: pip install openai")

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

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        cache_key = self._make_cache_key(messages, temperature=temperature, max_tokens=max_tokens)

        if use_cache and self.cache:
            cached = await self._get_cached_response(cache_key)
            if cached:
                if cached.usage:
                    cached.usage.cached_tokens = cached.usage.prompt_tokens
                return cached

        client = self._get_client()
        request_messages = [m.to_dict() for m in messages]

        request_kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": request_messages,
            "temperature": temperature,
            **kwargs,
        }

        if max_tokens:
            request_kwargs["max_tokens"] = max_tokens

        if tools:
            request_kwargs["tools"] = [t.to_dict() for t in tools]

        response = await client.chat.completions.create(**request_kwargs)

        content = response.choices[0].message.content or ""
        tool_calls = None
        if response.choices[0].message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response.choices[0].message.tool_calls
            ]

        usage = None
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
            self._update_usage(usage)

        result = InferenceResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            model=response.model,
            finish_reason=response.choices[0].finish_reason,
            raw=response.model_dump() if hasattr(response, "model_dump") else None,
        )

        if use_cache and self.cache:
            await self._cache_response(cache_key, result, ttl=cache_ttl)

        return result

    async def stream_complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        request_messages = [m.to_dict() for m in messages]

        request_kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": request_messages,
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }

        if max_tokens:
            request_kwargs["max_tokens"] = max_tokens

        if tools:
            request_kwargs["tools"] = [t.to_dict() for t in tools]

        async with client.chat.completions.stream(**request_kwargs) as stream:
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content


class AnthropicInferenceClient(BaseInferenceClient):
    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
        cache: Optional[AbstractCache] = None,
        enable_prompt_caching: bool = False,
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            cache=cache,
        )
        self.enable_prompt_caching = enable_prompt_caching
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package is required. Install with: pip install anthropic")

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

    def _convert_messages(self, messages: List[Message]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        system_prompt = None
        converted = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_prompt = msg.content
            else:
                converted.append(msg.to_dict())
        return system_prompt, converted

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        cache_key = self._make_cache_key(messages, temperature=temperature, max_tokens=max_tokens)

        if use_cache and self.cache:
            cached = await self._get_cached_response(cache_key)
            if cached:
                return cached

        client = self._get_client()
        system_prompt, converted_messages = self._convert_messages(messages)

        request_kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            **kwargs,
        }

        if system_prompt:
            request_kwargs["system"] = system_prompt

        if tools:
            request_kwargs["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.parameters,
                }
                for t in tools
            ]

        response = await client.messages.create(**request_kwargs)

        content = ""
        tool_calls = None

        for block in response.content:
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
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                cached_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            )
            self._update_usage(usage)

        result = InferenceResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            model=response.model,
            finish_reason=response.stop_reason,
        )

        if use_cache and self.cache:
            await self._cache_response(cache_key, result, ttl=cache_ttl)

        return result

    async def stream_complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        system_prompt, converted_messages = self._convert_messages(messages)

        request_kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            **kwargs,
        }

        if system_prompt:
            request_kwargs["system"] = system_prompt

        if tools:
            request_kwargs["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.parameters,
                }
                for t in tools
            ]

        async with client.messages.stream(**request_kwargs) as stream:
            async for text in stream.text_stream:
                yield text


class MockInferenceClient(BaseInferenceClient):
    def __init__(
        self,
        model: str = "mock-model",
        responses: Optional[List[str]] = None,
        cache: Optional[AbstractCache] = None,
    ):
        super().__init__(model=model, cache=cache)
        self.responses = responses or ["Mock response"]
        self._response_index = 0

    def _get_next_response(self) -> str:
        response = self.responses[self._response_index % len(self.responses)]
        self._response_index += 1
        return response

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        content = self._get_next_response()
        usage = TokenUsage(
            prompt_tokens=sum(len(m.content.split()) for m in messages),
            completion_tokens=len(content.split()),
            total_tokens=sum(len(m.content.split()) for m in messages) + len(content.split()),
        )
        self._update_usage(usage)
        return InferenceResponse(
            content=content,
            usage=usage,
            model=self.model,
            finish_reason="stop",
        )

    async def stream_complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        content = self._get_next_response()
        for word in content.split():
            yield word + " "
            await asyncio.sleep(0.01)


# ---------------------------------------------------------------------------
# LLM Directed Graph Execution
# ---------------------------------------------------------------------------

class LLMRouter:
    def __init__(
        self,
        inference_client: BaseInferenceClient,
        system_prompt: Optional[str] = None,
    ):
        self.inference_client = inference_client
        self.system_prompt = system_prompt or (
            "You are a routing assistant. Given the current state and available nodes, "
            "decide which node to execute next. Respond with only the node name."
        )

    async def route(
        self,
        state: GraphState,
        available_nodes: List[str],
        context: Optional[str] = None,
    ) -> str:
        messages = [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt),
            Message(
                role=MessageRole.USER,
                content=(
                    f"Current state: {json.dumps(state.data, indent=2)}\n"
                    f"Available nodes: {available_nodes}\n"
                    f"Context: {context or 'None'}\n"
                    f"Which node should execute next? Respond with only the node name."
                ),
            ),
        ]

        response = await self.inference_client.complete(messages=messages, temperature=0.0)
        chosen = response.content.strip()

        if chosen in available_nodes:
            return chosen

        for node in available_nodes:
            if node.lower() in chosen.lower():
                return node

        return available_nodes[0] if available_nodes else Graph.END


class LLMDirectedGraph(Graph):
    def __init__(
        self,
        name: str = "llm_directed_graph",
        inference_client: Optional[BaseInferenceClient] = None,
        router: Optional[LLMRouter] = None,
    ):
        super().__init__(name=name)
        self.inference_client = inference_client
        self.router = router or (LLMRouter(inference_client) if inference_client else None)

    async def invoke(self, state: Optional[GraphState] = None) -> GraphState:
        if not self._compiled:
            self.compile()

        if state is None:
            state = GraphState()

        for node in self._nodes.values():
            node.status = NodeStatus.PENDING

        if self.router is None:
            return await super().invoke(state)

        start_nodes = self._get_start_nodes()
        if not start_nodes:
            return state

        current_name = start_nodes[0]
        visited: Set[str] = set()
        max_iterations = len(self._nodes) * 2

        for _ in range(max_iterations):
            if current_name == self.END or current_name not in self._nodes:
                break

            if current_name in visited:
                break

            visited.add(current_name)
            node = self._nodes[current_name]
            await self._execute_node(node, state)

            next_nodes = self._get_next_nodes(current_name, state)
            valid_next = [n for n in next_nodes if n != self.END and n not in visited]

            if not valid_next:
                if self.END in next_nodes:
                    break
                break

            if len(valid_next) == 1:
                current_name = valid_next[0]
            else:
                current_name = await self.router.route(
                    state=state,
                    available_nodes=valid_next,
                    context=f"Just completed node: {current_name}",
                )

        return state


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Tool:
    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.description = description
        self.func = func
        self.parameters = parameters or {"type": "object", "properties": {}}

    def to_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )

    async def execute(self, **kwargs: Any) -> Any:
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(**kwargs)
        return self.func(**kwargs)


class Agent:
    def __init__(
        self,
        name: str,
        inference_client: BaseInferenceClient,
        tools: Optional[List[Tool]] = None,
        system_prompt: Optional[str] = None,
        max_iterations: int = 10,
        cache: Optional[AbstractCache] = None,
    ):
        self.name = name
        self.inference_client = inference_client
        self.tools: Dict[str, Tool] = {t.name: t for t in (tools or [])}
        self.system_prompt = system_prompt or f"You are {name}, a helpful AI assistant."
        self.max_iterations = max_iterations
        self.cache = cache
        self.conversation_history: List[Message] = []
        self._total_usage = TokenUsage()

    def add_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def _build_messages(self, user_message: str) -> List[Message]:
        messages = [Message(role=MessageRole.SYSTEM, content=self.system_prompt)]
        messages.extend(self.conversation_history)
        messages.append(Message(role=MessageRole.USER, content=user_message))
        return messages

    async def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Message]:
        tool_messages = []
        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            tool_args_str = tc["function"]["arguments"]

            try:
                tool_args = json.loads(tool_args_str)
            except json.JSONDecodeError:
                tool_args = {}

            tool = self.tools.get(tool_name)
            if tool:
                try:
                    result = await tool.execute(**tool_args)
                    result_str = json.dumps(result) if not isinstance(result, str) else result
                except Exception as e:
                    result_str = f"Error executing tool {tool_name}: {str(e)}"
            else:
                result_str = f"Tool '{tool_name}' not found"

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
        tool_definitions = [t.to_definition() for t in self.tools.values()]
        messages = self._build_messages(user_message)

        for iteration in range(self.max_iterations):
            response = await self.inference_client.complete(
                messages=messages,
                tools=tool_definitions if tool_definitions else None,
            )

            if response.usage:
                self._total_usage = self._total_usage + response.usage

            assistant_message = Message(
                role=MessageRole.ASSISTANT,
                content=response.content,
                tool_calls=response.tool_calls,
            )
            messages.append(assistant_message)

            if not response.tool_calls:
                self.conversation_history.append(Message(role=MessageRole.USER, content=user_message))
                self.conversation_history.append(assistant_message)
                return response.content

            tool_messages = await self._handle_tool_calls(response.tool_calls)
            messages.extend(tool_messages)

        return "Max iterations reached without a final response."

    async def stream_run(self, user_message: str) -> AsyncGenerator[str, None]:
        messages = self._build_messages(user_message)
        async for chunk in self.inference_client.stream_complete(messages=messages):
            yield chunk

    def reset_conversation(self) -> None:
        self.conversation_history.clear()

    def get_total_usage(self) -> TokenUsage:
        return self._total_usage


# ---------------------------------------------------------------------------
# Graph Builder (Fluent API)
# ---------------------------------------------------------------------------

class GraphBuilder:
    def __init__(self, name: str = "graph"):
        self._graph = Graph(name=name)

    def node(self, name: str, func: Callable, metadata: Optional[Dict[str, Any]] = None) -> "GraphBuilder":
        self._graph.add_node(name, func, metadata)
        return self

    def edge(
        self,
        source: str,
        target: str,
        condition: Optional[Callable[[GraphState], bool]] = None,
    ) -> "GraphBuilder":
        edge_type = EdgeType.CONDITIONAL if condition else EdgeType.DEFAULT
        self._graph.add_edge(source, target, edge_type=edge_type, condition=condition)
        return self

    def start_edge(self, target: str) -> "GraphBuilder":
        self._graph.add_edge(Graph.START, target)
        return self

    def end_edge(self, source: str) -> "GraphBuilder":
        self._graph.add_edge(source, Graph.END)
        return self

    def conditional_edges(
        self,
        source: str,
        condition: Callable[[GraphState], str],
        target_map: Dict[str, str],
    ) -> "GraphBuilder":
        self._graph.add_conditional_edge(source, condition, target_map)
        return self

    def middleware(self, mw: Middleware) -> "GraphBuilder":
        self._graph.add_middleware(mw)
        return self

    def with_snapshots(self) -> "GraphBuilder":
        self._graph.enable_snapshots(True)
        return self

    def build(self) -> Graph:
        return self._graph.compile()


# ---------------------------------------------------------------------------
# Convenience factory functions
# ---------------------------------------------------------------------------

def create_graph(name: str = "graph") -> GraphBuilder:
    return GraphBuilder(name=name)


def create_openai_client(
    model: str = "gpt-4o",
    api_key: Optional[str] = None,
    cache: Optional[AbstractCache] = None,
    **kwargs: Any,
) -> OpenAIInferenceClient:
    return OpenAIInferenceClient(model=model, api_key=api_key, cache=cache, **kwargs)


def create_anthropic_client(
    model: str = "claude-3-5-sonnet-20241022",
    api_key: Optional[str] = None,
    cache: Optional[AbstractCache] = None,
    **kwargs: Any,
) -> AnthropicInferenceClient:
    return AnthropicInferenceClient(model=model, api_key=api_key, cache=cache, **kwargs)


def create_mock_client(
    responses: Optional[List[str]] = None,
    cache: Optional[AbstractCache] = None,
) -> MockInferenceClient:
    return MockInferenceClient(responses=responses, cache=cache)


def create_in_memory_cache(prefix: str = "", suffix: str = "") -> InMemoryCache:
    return InMemoryCache(prefix=prefix, suffix=suffix)


def create_redis_cache(
    url: str = "redis://localhost:6379",
    prefix: str = "",
    suffix: str = "",
    db: int = 0,
) -> RedisCache:
    return RedisCache(url=url, prefix=prefix, suffix=suffix, db=db)


def create_agent(
    name: str,
    inference_client: BaseInferenceClient,
    tools: Optional[List[Tool]] = None,
    system_prompt: Optional[str] = None,
    max_iterations: int = 10,
    cache: Optional[AbstractCache] = None,
) -> Agent:
    return Agent(
        name=name,
        inference_client=inference_client,
        tools=tools,
        system_prompt=system_prompt,
        max_iterations=max_iterations,
        cache=cache,
    )