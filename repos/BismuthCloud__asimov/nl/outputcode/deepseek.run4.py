import asyncio
import json
import abc
import uuid
import time
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    Callable,
    Coroutine,
    AsyncIterator,
    TypeVar,
    Generic,
    Awaitable,
)
from collections import deque
from contextlib import asynccontextmanager

# Optional OpenTelemetry imports
try:
    from opentelemetry import trace
    from opentelemetry.trace import Span, Status, StatusCode
    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False

logger = logging.getLogger(__name__)

# ---------- Exceptions ----------
class GraphError(Exception):
    pass

class CyclicDependencyError(GraphError):
    pass

class NodeExecutionError(GraphError):
    pass

class SnapshotError(Exception):
    pass

class CacheError(Exception):
    pass

class InferenceError(Exception):
    pass

# ---------- Graph Primitives ----------
class Node:
    """
    A single task node in the execution graph.
    """
    def __init__(
        self,
        name: str,
        func: Callable[..., Coroutine[Any, Any, Dict[str, Any]]],
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[List[str]] = None,
    ):
        self.name = name
        self.func = func
        self.inputs = inputs or {}   # default values for inputs
        self.outputs = outputs or [] # expected output keys
        self._is_llm_directed = False

    async def execute(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the node function with the provided context data.
        Context data is a dictionary of all available values.
        """
        # merge default inputs with context (context overrides)
        merged = {**self.inputs, **context_data}
        result = await self.func(**merged)
        if not isinstance(result, dict):
            raise NodeExecutionError(f"Node '{self.name}' must return a dict, got {type(result)}")
        return result

    def __repr__(self):
        return f"<Node {self.name}>"

class Edge:
    """
    Represents a directed dependency from one node to another.
    """
    def __init__(self, from_node: Node, to_node: Node):
        if from_node is to_node:
            raise GraphError("Self-referencing edges are not allowed")
        self.from_node = from_node
        self.to_node = to_node

class Graph:
    """
    Directed graph of nodes and edges.
    """
    def __init__(self):
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._outgoing: Dict[str, List[Node]] = {}   # adjacency list: node -> successors
        self._incoming: Dict[str, List[Node]] = {}   # node -> predecessors

    @property
    def nodes(self) -> List[Node]:
        return list(self._nodes.values())

    @property
    def edges(self) -> List[Edge]:
        return self._edges.copy()

    def add_node(self, node: Node) -> None:
        if node.name in self._nodes:
            raise GraphError(f"Node '{node.name}' already exists in graph")
        self._nodes[node.name] = node
        self._outgoing[node.name] = []
        self._incoming[node.name] = []

    def add_edge(self, from_node: Node, to_node: Node) -> None:
        if from_node.name not in self._nodes:
            raise GraphError(f"Node '{from_node.name}' not found in graph")
        if to_node.name not in self._nodes:
            raise GraphError(f"Node '{to_node.name}' not found in graph")
        edge = Edge(from_node, to_node)
        self._edges.append(edge)
        self._outgoing[from_node.name].append(to_node)
        self._incoming[to_node.name].append(from_node)

    def get_successors(self, node: Node) -> List[Node]:
        return self._outgoing[node.name]

    def get_predecessors(self, node: Node) -> List[Node]:
        return self._incoming[node.name]

    def validate(self) -> None:
        """
        Check for cycles and completeness.
        """
        # Check all referenced nodes exist
        for edge in self._edges:
            if edge.from_node.name not in self._nodes or edge.to_node.name not in self._nodes:
                raise GraphError(f"Edge refers to missing node: {edge}")
        # Topological sort to detect cycles
        indeg = {name: len(pre) for name, pre in self._incoming.items()}
        queue = deque([name for name, deg in indeg.items() if deg == 0])
        visited = []
        while queue:
            current = queue.popleft()
            visited.append(current)
            for succ in self._outgoing[current]:
                indeg[succ.name] -= 1
                if indeg[succ.name] == 0:
                    queue.append(succ.name)
        if len(visited) != len(self._nodes):
            raise CyclicDependencyError("Graph contains a cycle")

    def __repr__(self):
        return f"<Graph nodes={len(self._nodes)} edges={len(self._edges)}>"

# ---------- Execution Engine ----------
class ExecutionContext:
    """
    Holds the runtime state of the graph execution.
    """
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.executed_nodes: Set[str] = set()
        self.current_node: Optional[str] = None

    def snapshot(self) -> Dict[str, Any]:
        return {
            "data": self.data.copy(),
            "executed_nodes": list(self.executed_nodes),
            "current_node": self.current_node,
        }

    @classmethod
    def from_snapshot(cls, snapshot: Dict[str, Any]) -> "ExecutionContext":
        ctx = cls(snapshot["data"])
        ctx.executed_nodes = set(snapshot["executed_nodes"])
        ctx.current_node = snapshot["current_node"]
        return ctx

class Middleware(abc.ABC):
    """
    Abstract middleware that can hook into node execution lifecycle.
    """
    @abc.abstractmethod
    async def before_execution(self, node: Node, context: ExecutionContext) -> None:
        pass

    @abc.abstractmethod
    async def after_execution(self, node: Node, context: ExecutionContext, result: Dict[str, Any]) -> None:
        pass

class MiddlewareChain(Middleware):
    """
    Executes a chain of middlewares in order.
    """
    def __init__(self, middlewares: Optional[List[Middleware]] = None):
        self.middlewares = middlewares or []

    async def before_execution(self, node: Node, context: ExecutionContext) -> None:
        for mw in self.middlewares:
            await mw.before_execution(node, context)

    async def after_execution(self, node: Node, context: ExecutionContext, result: Dict[str, Any]) -> None:
        for mw in self.middlewares:
            await mw.after_execution(node, context, result)

class ExecutionEngine:
    """
    Orchestrates the execution of a graph, respecting dependencies and supporting dynamic LLM-directed paths.
    """
    def __init__(self, middleware: Optional[MiddlewareChain] = None, enable_snapshots: bool = False):
        self.middleware = middleware or MiddlewareChain()
        self.enable_snapshots = enable_snapshots
        # Snapshot store placeholder; could be injected
        self.snapshot_store: Optional["SnapshotStore"] = None

    async def execute(self, graph: Graph, initial_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the entire graph from start nodes to all reachable nodes.
        Supports LLM-directed nodes that return a list of successor names to override static edges.
        Returns final context data after execution.
        """
        graph.validate()
        context = ExecutionContext(initial_data or {})
        # Find start nodes (no incoming edges)
        indeg = {node.name: len(graph.get_predecessors(node)) for node in graph.nodes}
        ready = deque([node for node in graph.nodes if indeg[node.name] == 0])

        # Track executed nodes
        executed = set()

        while ready:
            node = ready.popleft()
            if node.name in executed:
                continue
            context.current_node = node.name

            # Middleware before
            await self.middleware.before_execution(node, context)

            # Execute node
            try:
                result = await node.execute(context.data)
            except Exception as e:
                raise NodeExecutionError(f"Error in node '{node.name}': {e}") from e

            # Update context data
            context.data.update(result)
            context.executed_nodes.add(node.name)
            executed.add(node.name)

            # Middleware after
            await self.middleware.after_execution(node, context, result)

            # Handle LLM-directed nodes: if node is marked as llm_directed, result should contain a "next_nodes" key
            next_nodes_override = None
            if hasattr(node, '_is_llm_directed') and node._is_llm_directed:
                if "next_nodes" in result:
                    next_nodes_override = result["next_nodes"]  # list of node names

            # Determine successors
            if next_nodes_override is not None:
                successors = [graph._nodes[n] for n in next_nodes_override if n in graph._nodes]
            else:
                successors = graph.get_successors(node)

            # Update indegree of successors and add to ready if all predecessors done
            for succ in successors:
                indeg[succ.name] -= 1
                if indeg[succ.name] == 0:
                    ready.append(succ)

            # Optional snapshot after node execution
            if self.enable_snapshots and self.snapshot_store:
                snap = self.create_snapshot(graph, context)
                await self.snapshot_store.save(snap)

        context.current_node = None
        return context.data

    def create_snapshot(self, graph: Graph, context: ExecutionContext) -> "Snapshot":
        return Snapshot(
            graph_id=id(graph),
            graph_nodes={n.name: n.__class__.__name__ for n in graph.nodes},
            context_snapshot=context.snapshot(),
        )

    async def restore_from_snapshot(self, graph: Graph, snapshot_id: str) -> ExecutionContext:
        if not self.snapshot_store:
            raise SnapshotError("No snapshot store configured")
        snap = await self.snapshot_store.load(snapshot_id)
        if snap is None:
            raise SnapshotError(f"Snapshot '{snapshot_id}' not found")
        ctx = ExecutionContext.from_snapshot(snap.context_snapshot)
        # Could rebuild graph nodes if needed
        return ctx

class LLMDirectedNode(Node):
    """
    A special node whose result dictionary may specify dynamic next nodes via 'next_nodes' key.
    """
    def __init__(self, name: str, func, inputs=None, outputs=None):
        super().__init__(name, func, inputs, outputs)
        self._is_llm_directed = True

# ---------- Snapshotting ----------
class Snapshot:
    def __init__(self, graph_id: int, graph_nodes: Dict[str, str], context_snapshot: Dict[str, Any], snapshot_id: Optional[str] = None):
        self.snapshot_id = snapshot_id or str(uuid.uuid4())
        self.graph_id = graph_id
        self.graph_nodes = graph_nodes
        self.context_snapshot = context_snapshot
        self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "graph_id": self.graph_id,
            "graph_nodes": self.graph_nodes,
            "context_snapshot": self.context_snapshot,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Snapshot":
        return cls(
            graph_id=data["graph_id"],
            graph_nodes=data["graph_nodes"],
            context_snapshot=data["context_snapshot"],
            snapshot_id=data.get("snapshot_id"),
        )

class SnapshotStore(abc.ABC):
    @abc.abstractmethod
    async def save(self, snapshot: Snapshot) -> None:
        pass

    @abc.abstractmethod
    async def load(self, snapshot_id: str) -> Optional[Snapshot]:
        pass

    @abc.abstractmethod
    async def list_snapshots(self) -> List[str]:
        pass

    @abc.abstractmethod
    async def delete(self, snapshot_id: str) -> None:
        pass

class CacheSnapshotStore(SnapshotStore):
    """
    Stores snapshots using a Cache backend.
    """
    KEY_PREFIX = "snapshot:"

    def __init__(self, cache: "Cache"):
        self.cache = cache

    async def save(self, snapshot: Snapshot) -> None:
        key = self.KEY_PREFIX + snapshot.snapshot_id
        await self.cache.set(key, snapshot.to_dict())

    async def load(self, snapshot_id: str) -> Optional[Snapshot]:
        key = self.KEY_PREFIX + snapshot_id
        data = await self.cache.get(key)
        if data is None:
            return None
        return Snapshot.from_dict(data)

    async def list_snapshots(self) -> List[str]:
        all_keys = await self.cache.get_all(prefix=self.KEY_PREFIX)
        return [k[len(self.KEY_PREFIX):] for k in all_keys]

    async def delete(self, snapshot_id: str) -> None:
        key = self.KEY_PREFIX + snapshot_id
        await self.cache.delete(key)

# ---------- Inference ----------
class ToolDefinition:
    def __init__(self, name: str, description: str, parameters: Dict[str, Any]):
        self.name = name
        self.description = description
        self.parameters = parameters  # JSON Schema for parameters

class LLMResponse:
    def __init__(
        self,
        text: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        usage: Optional[Dict[str, int]] = None,
    ):
        self.text = text or ""
        self.tool_calls = tool_calls or []
        self.usage = usage or {"prompt_tokens": 0, "completion_tokens": 0}

class LLMClient(abc.ABC):
    """
    Abstract LLM client with support for streaming, tool calling, and usage tracking.
    """
    def __init__(self, model: str, tools: Optional[List[ToolDefinition]] = None, enable_telemetry: bool = False):
        self.model = model
        self.tools = tools or []
        self.enable_telemetry = enable_telemetry
        self.tracer = None
        if HAS_OTEL and enable_telemetry:
            self.tracer = trace.get_tracer(__name__)

    @abc.abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        pass

    @abc.abstractmethod
    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Yields chunks of text as they arrive."""
        pass

    def _start_span(self, name: str, attributes: Dict[str, Any]) -> Optional[Span]:
        if self.tracer:
            span = self.tracer.start_span(name)
            for k, v in attributes.items():
                span.set_attribute(k, v)
            return span
        return None

    def _end_span(self, span: Optional[Span]):
        if span:
            span.set_status(Status(StatusCode.OK))
            span.end()

class MockLLMClient(LLMClient):
    """
    A simple mock LLM client for testing and development.
    """
    def __init__(self, model: str = "mock-model", **kwargs):
        super().__init__(model, **kwargs)

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        span = self._start_span("inference.generate", {"model": self.model, "prompt": prompt})
        usage = {"prompt_tokens": len(prompt.split()), "completion_tokens": 50}
        # Simulate a tool call if tools are defined
        tool_calls = []
        if self.tools:
            tool_calls.append({
                "id": f"call_{uuid.uuid4().hex[:6]}",
                "type": "function",
                "function": {"name": self.tools[0].name, "arguments": '{"arg1":"value"}'}
            })
        response = LLMResponse(
            text=f"Mock response to: {prompt[:50]}...",
            tool_calls=tool_calls,
            usage=usage
        )
        self._end_span(span)
        return response

    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        span = self._start_span("inference.stream", {"model": self.model, "prompt": prompt})
        words = f"Streaming mock response for: {prompt[:30]}...".split()
        for i, word in enumerate(words):
            yield word + (" " if i < len(words)-1 else "")
            await asyncio.sleep(0.05)  # simulate latency
        self._end_span(span)

# Example integration of prompt caching
class CachedLLMClient(LLMClient):
    """
    Wraps an LLMClient with a caching layer for identical prompts.
    """
    def __init__(self, base_client: LLMClient, cache: "Cache", ttl: Optional[int] = 300):
        super().__init__(model=base_client.model, tools=base_client.tools, enable_telemetry=base_client.enable_telemetry)
        self.base = base_client
        self.cache = cache
        self.ttl = ttl

    def _cache_key(self, prompt: str, **kwargs) -> str:
        # create a deterministic key from prompt and relevant kwargs
        raw = json.dumps({"prompt": prompt, "kwargs": kwargs}, sort_keys=True)
        return f"llm_cache:{self.model}:{hash(raw)}"

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        cache_key = self._cache_key(prompt, **kwargs)
        cached = await self.cache.get(cache_key)
        if cached:
            return LLMResponse(**json.loads(cached))
        response = await self.base.generate(prompt, **kwargs)
        # Store in cache
        await self.cache.set(cache_key, json.dumps({
            "text": response.text,
            "tool_calls": response.tool_calls,
            "usage": response.usage,
        }), ttl=self.ttl)
        return response

    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        # Streaming bypasses cache for simplicity (could implement later)
        async for chunk in self.base.stream(prompt, **kwargs):
            yield chunk

# ---------- Caching ----------
class Cache(abc.ABC):
    """
    Abstract asynchronous key-value cache with JSON serialization.
    """
    @abc.abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abc.abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass

    @abc.abstractmethod
    async def delete(self, key: str) -> None:
        pass

    @abc.abstractmethod
    async def get_all(self, prefix: Optional[str] = None) -> Dict[str, Any]:
        """Return all keys (optionally filtered by prefix) and their values."""
        pass

    @abc.abstractmethod
    async def clear(self) -> None:
        """Delete all keys."""
        pass

    # Mailbox (pub/sub) abstract interface
    @abc.abstractmethod
    async def subscribe(self, channel: str) -> "Mailbox":
        pass

    @abc.abstractmethod
    async def publish(self, channel: str, message: Any) -> None:
        pass

class Mailbox(abc.ABC):
    """
    Abstraction for receiving messages from a subscribed channel.
    """
    @abc.abstractmethod
    async def get(self) -> Any:
        pass

    @abc.abstractmethod
    async def close(self) -> None:
        pass

# Redis Implementation
class RedisCache(Cache):
    """
    Async Redis cache with JSON serialization.
    Requires 'redis' package with asyncio support.
    """
    def __init__(self, redis_client, prefix: str = "", suffix: str = "", serializer=json):
        self._redis = redis_client  # expects redis.asyncio.Redis instance
        self.prefix = prefix
        self.suffix = suffix
        self.serializer = serializer

    def _serialize(self, value: Any) -> str:
        return self.serializer.dumps(value)

    def _deserialize(self, data: Optional[bytes]) -> Optional[Any]:
        if data is None:
            return None
        return self.serializer.loads(data.decode())

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}{key}{self.suffix}"

    def _strip_prefix_suffix(self, full_key: str) -> str:
        if self.prefix and full_key.startswith(self.prefix):
            full_key = full_key[len(self.prefix):]
        if self.suffix and full_key.endswith(self.suffix):
            full_key = full_key[:-len(self.suffix)]
        return full_key

    async def get(self, key: str) -> Optional[Any]:
        val = await self._redis.get(self._full_key(key))
        return self._deserialize(val)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        fkey = self._full_key(key)
        serialized = self._serialize(value)
        if ttl:
            await self._redis.setex(fkey, ttl, serialized)
        else:
            await self._redis.set(fkey, serialized)

    async def delete(self, key: str) -> None:
        await self._redis.delete(self._full_key(key))

    async def get_all(self, prefix: Optional[str] = None) -> Dict[str, Any]:
        # Use SCAN to iterate keys matching pattern
        pattern = f"{self.prefix}{prefix or ''}*{self.suffix}"
        cursor = 0
        result = {}
        while True:
            cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
            if keys:
                pipeline = self._redis.pipeline()
                for k in keys:
                    pipeline.get(k)
                values = await pipeline.execute()
                for k, v in zip(keys, values):
                    stripped = self._strip_prefix_suffix(k.decode())
                    result[stripped] = self._deserialize(v)
            if cursor == 0:
                break
        return result

    async def clear(self) -> None:
        # Flush all keys matching prefix and suffix; cautious: may delete unintended keys
        pattern = f"{self.prefix}*{self.suffix}"
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
            if keys:
                await self._redis.delete(*keys)
            if cursor == 0:
                break

    async def publish(self, channel: str, message: Any) -> None:
        fchannel = self._full_key(channel)
        await self._redis.publish(fchannel, self._serialize(message))

    async def subscribe(self, channel: str) -> Mailbox:
        pubsub = self._redis.pubsub()
        fchannel = self._full_key(channel)
        await pubsub.subscribe(fchannel)
        return RedisMailbox(pubsub, fchannel, self)

class RedisMailbox(Mailbox):
    def __init__(self, pubsub, channel: str, cache: RedisCache):
        self._pubsub = pubsub
        self._channel = channel
        self.cache = cache

    async def get(self) -> Any:
        # Wait for next message from the channel
        while True:
            msg = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=None)
            if msg and msg["type"] == "message":
                data = msg["data"]
                return self.cache._deserialize(data)
            await asyncio.sleep(0.01)

    async def close(self) -> None:
        await self._pubsub.unsubscribe(self._channel)
        await self._pubsub.close()

# Example of a simple middleware
class LoggingMiddleware(Middleware):
    async def before_execution(self, node, context):
        logger.info(f"Executing node: {node.name}")

    async def after_execution(self, node, context, result):
        logger.info(f"Node {node.name} executed, result: {list(result.keys())}")

# ---------- Optional OpenTelemetry instrumentation for execution ----------
class TelemetryMiddleware(Middleware):
    def __init__(self):
        if not HAS_OTEL:
            raise ImportError("OpenTelemetry is not available. Install opentelemetry packages.")
        self.tracer = trace.get_tracer(__name__)

    async def before_execution(self, node, context):
        span = self.tracer.start_span(f"graph.node.{node.name}")
        context._span = span

    async def after_execution(self, node, context, result):
        span: Optional[Span] = getattr(context, "_span", None)
        if span:
            span.set_status(Status(StatusCode.OK))
            span.end()

# Example helper to create graph with simple async tasks
async def example_usage():
    # Define some async node functions
    async def fetch_data(query: str) -> dict:
        await asyncio.sleep(0.1)
        return {"data": f"data for {query}"}

    async def process_data(data: str) -> dict:
        await asyncio.sleep(0.1)
        return {"processed": data.upper()}

    # Build graph
    g = Graph()
    node1 = Node("fetch", fetch_data, inputs={"query": "default_query"})
    node2 = Node("process", process_data)
    g.add_node(node1)
    g.add_node(node2)
    g.add_edge(node1, node2)

    # Execution engine with middleware
    engine = ExecutionEngine(middleware=MiddlewareChain([LoggingMiddleware()]))
    result = await engine.execute(g, {"query": "hello world"})
    print("Final result:", result)

    # LLM directed node example
    async def decide_next(query: str) -> dict:
        # Simulate LLM decision
        return {"next_nodes": ["node_a", "node_b"], "decision": "branch"}
    llm_node = LLMDirectedNode("decider", decide_next)
    # ... add to graph and use

if __name__ == "__main__":
    asyncio.run(example_usage())