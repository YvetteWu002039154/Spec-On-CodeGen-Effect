from __future__ import annotations

import asyncio
import copy
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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

# ---------------------------------------------------------------------------
# Optional OpenTelemetry instrumentation
# ---------------------------------------------------------------------------
try:
    from opentelemetry import trace
    from opentelemetry.trace import Span, Tracer

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    Tracer = None

# ---------------------------------------------------------------------------
# Helper: tracing decorator for inference clients
# ---------------------------------------------------------------------------
def trace_inference(span_name: str, attributes_builder: Optional[Callable[..., Dict[str, Any]]] = None):
    """Decorator that instruments an async generator or coroutine with OTel spans."""
    def decorator(func):
        if not OTEL_AVAILABLE:
            return func

        tracer = trace.get_tracer(__name__)

        if asyncio.iscoroutinefunction(func):
            async def wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name) as span:
                    if attributes_builder:
                        span.set_attributes(attributes_builder(*args, **kwargs))
                    return await func(*args, **kwargs)
            return wrapper
        else:
            # For async generators (streaming)
            async def wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name) as span:
                    if attributes_builder:
                        span.set_attributes(attributes_builder(*args, **kwargs))
                    async for item in func(*args, **kwargs):
                        yield item
            return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Inference Response
# ---------------------------------------------------------------------------
@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]


@dataclass
class InferenceChunk:
    text: str
    finish_reason: Optional[str] = None


@dataclass
class InferenceResponse:
    text: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: Optional[Usage] = None
    finish_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Abstract Inference Client
# ---------------------------------------------------------------------------
class BaseInferenceClient(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def complete(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> InferenceResponse:
        """Execute a single completion request."""
        ...

    @abstractmethod
    async def stream_complete(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncGenerator[InferenceChunk, None]:
        """Stream completion tokens."""
        ...

    async def cached_complete(
        self,
        cache: AbstractCache,
        cache_key: str,
        prompt: Union[str, List[Dict[str, str]]],
        tools: Optional[List[Dict[str, Any]]] = None,
        ttl: Optional[int] = None,
        **kwargs,
    ) -> InferenceResponse:
        """Complete with prompt caching support."""
        cached = await cache.get(cache_key)
        if cached is not None:
            data = json.loads(cached)
            return InferenceResponse(
                text=data.get("text", ""),
                tool_calls=[ToolCall(**tc) for tc in data.get("tool_calls", [])],
                usage=Usage(**data.get("usage", {})) if data.get("usage") else None,
                finish_reason=data.get("finish_reason"),
            )
        response = await self.complete(prompt, tools=tools, **kwargs)
        # Store response in cache
        cache_data = {
            "text": response.text,
            "tool_calls": [tc.__dict__ for tc in response.tool_calls],
            "usage": response.usage.__dict__ if response.usage else None,
            "finish_reason": response.finish_reason,
        }
        await cache.set(cache_key, json.dumps(cache_data), ttl=ttl)
        return response


# ---------------------------------------------------------------------------
# Mock Inference Client for testing / demos
# ---------------------------------------------------------------------------
class MockInferenceClient(BaseInferenceClient):
    """A simple client that returns pre-defined responses."""

    def __init__(self, fixed_response: str = "Hello, world!", stream_chunks: Optional[List[str]] = None):
        self.fixed_response = fixed_response
        self.stream_chunks = stream_chunks or ["Hello", ", ", "world!"]

    async def complete(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> InferenceResponse:
        return InferenceResponse(
            text=self.fixed_response,
            usage=Usage(
                prompt_tokens=len(prompt) if isinstance(prompt, str) else sum(len(m.get("content", "")) for m in prompt),
                completion_tokens=len(self.fixed_response),
                total_tokens=len(prompt) + len(self.fixed_response) if isinstance(prompt, str) else sum(len(m.get("content", "")) for m in prompt) + len(self.fixed_response),
            ),
            finish_reason="stop",
        )

    async def stream_complete(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncGenerator[InferenceChunk, None]:
        for chunk in self.stream_chunks:
            yield InferenceChunk(text=chunk)
        yield InferenceChunk(text="", finish_reason="stop")


# ---------------------------------------------------------------------------
# Abstract Cache Interface
# ---------------------------------------------------------------------------
class AbstractCache(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        ...

    @abstractmethod
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    async def get_all(self, keys: List[str]) -> Dict[str, Optional[str]]:
        ...

    @abstractmethod
    async def clear(self, pattern: str = "*") -> None:
        """Clear all keys matching pattern."""
        ...

    @abstractmethod
    async def publish(self, channel: str, message: str) -> None:
        """Publish a message to a pub/sub channel."""
        ...

    @abstractmethod
    async def subscribe(self, channel: str) -> AsyncGenerator[str, None]:
        """Subscribe to a channel and yield messages."""
        ...

    @abstractmethod
    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel."""
        ...


# ---------------------------------------------------------------------------
# Redis Implementation
# ---------------------------------------------------------------------------
class RedisCache(AbstractCache):
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        prefix: str = "",
        suffix: str = "",
        **redis_kwargs,
    ):
        import redis.asyncio as aioredis
        self.redis = aioredis.from_url(redis_url, **redis_kwargs)
        self.prefix = prefix
        self.suffix = suffix
        self._pubsub = None
        self._pubsub_lock = asyncio.Lock()

    def _build_key(self, key: str) -> str:
        return f"{self.prefix}{key}{self.suffix}"

    def _strip_key(self, full_key: str) -> str:
        if self.prefix and full_key.startswith(self.prefix):
            full_key = full_key[len(self.prefix):]
        if self.suffix and full_key.endswith(self.suffix):
            full_key = full_key[:-len(self.suffix)]
        return full_key

    async def get(self, key: str) -> Optional[str]:
        val = await self.redis.get(self._build_key(key))
        return val.decode() if val else None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        if ttl:
            await self.redis.setex(self._build_key(key), ttl, value)
        else:
            await self.redis.set(self._build_key(key), value)

    async def delete(self, key: str) -> None:
        await self.redis.delete(self._build_key(key))

    async def exists(self, key: str) -> bool:
        return await self.redis.exists(self._build_key(key)) > 0

    async def get_all(self, keys: List[str]) -> Dict[str, Optional[str]]:
        full_keys = [self._build_key(k) for k in keys]
        values = await self.redis.mget(full_keys)
        result = {}
        for k, v in zip(keys, values):
            result[k] = v.decode() if v else None
        return result

    async def clear(self, pattern: str = "*") -> None:
        full_pattern = self._build_key(pattern)
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=full_pattern)
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break

    async def publish(self, channel: str, message: str) -> None:
        await self.redis.publish(channel, message)

    async def subscribe(self, channel: str) -> AsyncGenerator[str, None]:
        async with self._pubsub_lock:
            if self._pubsub is None:
                self._pubsub = self.redis.pubsub()
                await self._pubsub.subscribe(channel)
            else:
                await self._pubsub.subscribe(channel)

        try:
            async for raw_message in self._pubsub.listen():
                if raw_message["type"] == "message":
                    yield raw_message["data"].decode()
        finally:
            await self.unsubscribe(channel)

    async def unsubscribe(self, channel: str) -> None:
        if self._pubsub:
            await self._pubsub.unsubscribe(channel)

    async def close(self):
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None
        await self.redis.close()

    # ----- Mailbox convenience methods -----
    async def publish_to_mailbox(self, mailbox_name: str, message: str) -> None:
        channel = f"mailbox:{mailbox_name}"
        await self.publish(channel, message)

    async def subscribe_mailbox(self, mailbox_name: str) -> AsyncGenerator[str, None]:
        channel = f"mailbox:{mailbox_name}"
        async for msg in self.subscribe(channel):
            yield msg


# ---------------------------------------------------------------------------
# Graph Execution Engine
# ---------------------------------------------------------------------------
class GraphNode:
    """Represents a unit of work (task) in the graph."""

    def __init__(
        self,
        name: str,
        func: Callable[..., Any],
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.dependencies: Set[GraphNode] = set()
        self.dependents: Set[GraphNode] = set()
        self._output = None

    def add_dependency(self, node: GraphNode):
        self.dependencies.add(node)
        node.dependents.add(self)

    def __repr__(self):
        return f"GraphNode({self.name})"


class GraphEdge:
    """Edge between two nodes (directional)."""

    def __init__(self, source: GraphNode, target: GraphNode):
        self.source = source
        self.target = target


class Middleware(ABC):
    """Hook into node execution life cycle."""

    async def pre_execute(self, node: GraphNode, state: Dict[str, Any]) -> None:
        pass

    async def post_execute(self, node: GraphNode, result: Any, state: Dict[str, Any]) -> None:
        pass

    async def on_error(self, node: GraphNode, error: Exception, state: Dict[str, Any]) -> None:
        pass


class GraphEngine:
    def __init__(
        self,
        state: Optional[Dict[str, Any]] = None,
        middlewares: Optional[List[Middleware]] = None,
    ):
        self.nodes: Dict[str, GraphNode] = {}
        self.state = state or {}
        self.middlewares = middlewares or []
        self._executed = set()  # track executed nodes
        self._snapshots: List[Dict[str, Any]] = []

    def add_node(self, node: GraphNode):
        self.nodes[node.name] = node

    def add_edge(self, source: GraphNode, target: GraphNode):
        target.add_dependency(source)

    def build_from_nodes_and_edges(self, nodes: List[GraphNode], edges: List[GraphEdge]):
        for node in nodes:
            self.add_node(node)
        for edge in edges:
            self.add_edge(edge.source, edge.target)

    def _topological_sort(self) -> List[GraphNode]:
        # Kahn's algorithm
        in_degree = {node: len(node.dependencies) for node in self.nodes.values()}
        queue = [node for node in self.nodes.values() if in_degree[node] == 0]
        sorted_nodes = []
        while queue:
            node = queue.pop(0)
            sorted_nodes.append(node)
            for dep in node.dependents:
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)
        if len(sorted_nodes) != len(self.nodes):
            raise RuntimeError("Graph contains a cycle")
        return sorted_nodes

    async def execute(self) -> Dict[str, Any]:
        """Execute all nodes in dependency order, with middleware hooks."""
        sorted_nodes = self._topological_sort()
        for node in sorted_nodes:
            # Pre-execute hooks
            for mw in self.middlewares:
                try:
                    await mw.pre_execute(node, self.state)
                except Exception as e:
                    # Optionally log
                    pass

            try:
                # Pass dependencies' outputs as kwargs if needed
                dep_outputs = {dep.name: dep._output for dep in node.dependencies}
                merged_kwargs = {**dep_outputs, **node.kwargs}
                merged_kwargs["state"] = self.state
                # Support async and sync functions
                if asyncio.iscoroutinefunction(node.func):
                    result = await node.func(*node.args, **merged_kwargs)
                else:
                    result = node.func(*node.args, **merged_kwargs)
                node._output = result
                # Store in state? Optionally
                self.state[node.name] = result
            except Exception as e:
                for mw in self.middlewares:
                    await mw.on_error(node, e, self.state)
                raise

            # Post-execute hooks
            for mw in self.middlewares:
                try:
                    await mw.post_execute(node, node._output, self.state)
                except Exception:
                    pass

            self._executed.add(node.name)
        return self.state

    def snapshot_state(self) -> str:
        """Take a snapshot of the current state and store it."""
        snapshot = copy.deepcopy(self.state)
        snapshot_id = str(uuid.uuid4())
        self._snapshots.append({"id": snapshot_id, "state": snapshot})
        return snapshot_id

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """Restore state from a snapshot. Returns True if successful."""
        for snap in self._snapshots:
            if snap["id"] == snapshot_id:
                self.state = copy.deepcopy(snap["state"])
                return True
        return False

    def get_state(self) -> Dict[str, Any]:
        return self.state

    def reset(self):
        self.state = {}
        self._executed.clear()
        for node in self.nodes.values():
            node._output = None


# ---------------------------------------------------------------------------
# LLM Directed Graph Execution Helper
# ---------------------------------------------------------------------------
async def llm_decide_next_nodes(
    client: BaseInferenceClient,
    context: str,
    possible_nodes: List[str],
    instruction: str = "Choose the next node to execute.",
) -> str:
    """
    Use an LLM to decide which node to execute next. Returns the node name.
    """
    prompt = f"{instruction}\nContext: {context}\nAvailable nodes: {', '.join(possible_nodes)}"
    response = await client.complete(prompt)
    # Very naive parsing: expected node name in text
    for node in possible_nodes:
        if node in response.text:
            return node
    return possible_nodes[0]  # fallback


class DynamicGraphExecutor(GraphEngine):
    """Graph executor that can dynamically determine execution order via LLM."""

    def __init__(
        self,
        state: Optional[Dict[str, Any]] = None,
        middlewares: Optional[List[Middleware]] = None,
        client: Optional[BaseInferenceClient] = None,
    ):
        super().__init__(state, middlewares)
        self.client = client

    async def execute_dynamic(self, start_node_name: str, max_steps: int = 10) -> Dict[str, Any]:
        """Execute starting from start_node, using LLM to choose next node each step."""
        current_node = self.nodes[start_node_name]
        steps = 0
        while steps < max_steps:
            # Execute current node
            for mw in self.middlewares:
                await mw.pre_execute(current_node, self.state)
            try:
                dep_outputs = {dep.name: dep._output for dep in current_node.dependencies}
                merged_kwargs = {**dep_outputs, **current_node.kwargs, "state": self.state}
                if asyncio.iscoroutinefunction(current_node.func):
                    result = await current_node.func(*current_node.args, **merged_kwargs)
                else:
                    result = current_node.func(*current_node.args, **merged_kwargs)
                current_node._output = result
                self.state[current_node.name] = result
            except Exception as e:
                for mw in self.middlewares:
                    await mw.on_error(current_node, e, self.state)
                raise
            for mw in self.middlewares:
                await mw.post_execute(current_node, result, self.state)

            self._executed.add(current_node.name)
            steps += 1

            # Decide next node using LLM
            if self.client is None:
                break  # no client, stop
            # Find unexecuted dependents or all nodes
            possible_next = [n.name for n in self.nodes.values() if n.name not in self._executed]
            if not possible_next:
                break
            context = f"Previous node: {current_node.name}\nOutput: {result}"
            next_node_name = await llm_decide_next_nodes(
                self.client, context, possible_next
            )
            if next_node_name in self.nodes:
                current_node = self.nodes[next_node_name]
            else:
                break
        return self.state


# ---------------------------------------------------------------------------
# Optional: OpenTelemetry instrumentation for graph execution
# ---------------------------------------------------------------------------
class TracedMiddleware(Middleware):
    """Middleware that creates OTel spans around node execution."""

    def __init__(self, tracer_name: str = __name__):
        self.tracer = trace.get_tracer(tracer_name) if OTEL_AVAILABLE else None

    async def pre_execute(self, node: GraphNode, state: Dict[str, Any]) -> None:
        if self.tracer:
            span = self.tracer.start_span(f"graph.node.{node.name}")
            span.set_attribute("execution.order", len(state))
            # Store span in node for post_execute
            node._otel_span = span

    async def post_execute(self, node: GraphNode, result: Any, state: Dict[str, Any]) -> None:
        if self.tracer and hasattr(node, '_otel_span'):
            span = node._otel_span
            span.set_attribute("output", str(result)[:1000])
            span.end()
            del node._otel_span

    async def on_error(self, node: GraphNode, error: Exception, state: Dict[str, Any]) -> None:
        if self.tracer and hasattr(node, '_otel_span'):
            span = node._otel_span
            span.record_exception(error)
            span.end()
            del node._otel_span


# ---------------------------------------------------------------------------
# Example usage (not executed)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # This is just a placeholder; in a real framework we would provide comprehensive tests.
    pass