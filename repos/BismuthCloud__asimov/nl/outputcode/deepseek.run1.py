import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Set, Tuple, Type, Union

# Optional OpenTelemetry imports
try:
    from opentelemetry import trace
    from opentelemetry.trace import Span, Status, StatusCode
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    # Dummy classes for type hints if not available
    class Span:
        pass
    class Status:
        pass
    class StatusCode:
        pass
    class trace:
        @staticmethod
        def get_tracer(*args, **kwargs):
            class NoopTracer:
                def start_as_current_span(self, *args, **kwargs):
                    class NoopSpan:
                        def __enter__(self): return self
                        def __exit__(self, *args): pass
                        def set_attribute(self, *args, **kwargs): pass
                        def set_status(self, *args, **kwargs): pass
                        def record_exception(self, *args, **kwargs): pass
                    return NoopSpan()
            return NoopTracer()

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------------
# Graph Primitives
# --------------------------------------------------------------------------------
@dataclass
class NodeResult:
    node_id: str
    output: Any
    error: Optional[Exception] = None
    duration: float = 0.0

@dataclass
class Edge:
    source: str
    target: str
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None

class Node(ABC):
    """Abstract node representing a unit of work in the graph."""
    def __init__(self, node_id: str):
        self.node_id = node_id

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Any:
        """Execute the node's logic given the current execution context."""
        pass

class FunctionNode(Node):
    """A node that executes a simple async function."""
    def __init__(self, node_id: str, func: Callable[[Dict[str, Any]], Any]):
        super().__init__(node_id)
        self.func = func

    async def execute(self, context: Dict[str, Any]) -> Any:
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(context)
        else:
            return self.func(context)

class GraphMiddleware(ABC):
    """Middleware for graph execution, can intercept node execution."""
    @abstractmethod
    async def process(self, node: Node, context: Dict[str, Any], next_handler: Callable) -> Any:
        pass

class LoggingMiddleware(GraphMiddleware):
    async def process(self, node: Node, context: Dict[str, Any], next_handler: Callable) -> Any:
        logger.info(f"Executing node: {node.node_id}")
        start = time.time()
        result = await next_handler(node, context)
        duration = time.time() - start
        logger.info(f"Completed node: {node.node_id} in {duration:.3f}s")
        return result

class TracingMiddleware(GraphMiddleware):
    def __init__(self, tracer: Optional['trace.Tracer'] = None):
        self.tracer = tracer or trace.get_tracer(__name__)

    async def process(self, node: Node, context: Dict[str, Any], next_handler: Callable) -> Any:
        with self.tracer.start_as_current_span(f"graph.node.{node.node_id}") as span:
            span.set_attribute("node.id", node.node_id)
            try:
                result = await next_handler(node, context)
                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

class Graph:
    """Represents a directed graph of nodes."""
    def __init__(self, name: str = "default"):
        self.name = name
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.middlewares: List[GraphMiddleware] = []

    def add_node(self, node: Node):
        self.nodes[node.node_id] = node

    def add_edge(self, source: str, target: str, condition: Optional[Callable] = None):
        self.edges.append(Edge(source, target, condition))

    def add_middleware(self, middleware: GraphMiddleware):
        self.middlewares.append(middleware)

    def _topological_sort(self) -> List[str]:
        """Topological sort of node IDs. Returns list in execution order. Raises on cycles."""
        in_degree = {node_id: 0 for node_id in self.nodes}
        adjacency = {node_id: [] for node_id in self.nodes}
        for edge in self.edges:
            if edge.source in self.nodes and edge.target in self.nodes:
                adjacency[edge.source].append(edge.target)
                in_degree[edge.target] += 1

        queue = deque([node_id for node_id, deg in in_degree.items() if deg == 0])
        sorted_list = []
        while queue:
            current = queue.popleft()
            sorted_list.append(current)
            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_list) != len(self.nodes):
            raise ValueError("Graph contains a cycle")
        return sorted_list

    async def execute(self, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, NodeResult]:
        context = initial_context.copy() if initial_context else {}
        results: Dict[str, NodeResult] = {}
        dependencies: Dict[str, Set[str]] = defaultdict(set)
        pending_nodes: Dict[str, asyncio.Event] = {nid: asyncio.Event() for nid in self.nodes}
        # Build dependency map from edges
        for edge in self.edges:
            if edge.source in self.nodes and edge.target in self.nodes:
                dependencies[edge.target].add(edge.source)

        # Topological order but concurrency allowed: nodes become runnable when all dependencies done
        # We will use an asyncio.Queue for tasks that are ready
        ready_queue: asyncio.Queue[str] = asyncio.Queue()
        for nid in self.nodes:
            if not dependencies[nid]:
                ready_queue.put_nowait(nid)

        async def execute_node(node_id: str):
            node = self.nodes[node_id]
            # Build middleware chain
            handler = self._build_middleware_chain()
            start = time.time()
            try:
                output = await handler(node, context)
                error = None
            except Exception as e:
                output = None
                error = e
                logger.error(f"Node {node_id} failed: {e}")
            duration = time.time() - start
            results[node_id] = NodeResult(node_id=node_id, output=output, error=error, duration=duration)
            # Store output in context for downstream nodes; use node_id as key
            context[node_id] = output
            # Signal that this node is complete
            pending_nodes[node_id].set()

        async def process_queue():
            while len(results) < len(self.nodes):
                node_id = await ready_queue.get()
                # Check if all dependencies are done
                deps = dependencies[node_id]
                # Wait for each dependency event
                await asyncio.gather(*(pending_nodes[dep].wait() for dep in deps))
                # Check edge conditions
                can_execute = True
                for edge in self.edges:
                    if edge.target == node_id and edge.condition:
                        # Evaluate condition based on context or dependency output
                        if not edge.condition(context):
                            can_execute = False
                            break
                if can_execute:
                    # Execute node in a task
                    asyncio.create_task(execute_node(node_id))
                else:
                    # Mark as skipped? We still set the event so downstream can proceed
                    # But we need to set results and event
                    start = time.time()
                    results[node_id] = NodeResult(node_id=node_id, output=None, error=None, duration=0)
                    pending_nodes[node_id].set()
                    logger.info(f"Node {node_id} skipped due to condition")
                # Optionally, check if any node becomes ready after this one
                # (but we rely on the ready_queue to be filled initially; we might need to react to completions)
                # Instead, we'll monitor completions and enqueue newly ready nodes.
                # Actually, this design is flawed for dynamic readiness; we'll fix by using a task that checks all nodes
                # simpler: keep a watch loop that checks all unfinished nodes.
                # For simplicity, we'll process in topological order but still allow concurrency by launching tasks
                # as soon as ready. We'll use a gather approach. Let's restructure.

        # Improved execution: Use topological order to determine which nodes can run concurrently.
        # We'll group nodes by dependency level (distance from sources). But with conditions, it's more complex.
        # For this implementation, we'll execute nodes sequentially in topological order but we can still have concurrency
        # if a node's dependencies are satisfied earlier. However, the simple queue approach above needs completion events monitored.
        # Let's implement a more robust solution:

        # We'll use a worker coroutine per node that waits for all its dependencies' events.
        # Then checks conditions, then executes.
        # All tasks are created but they'll block until dependencies are ready.

        tasks = []
        for nid in self.nodes:
            tasks.append(self._execute_node_when_ready(nid, context, results, pending_nodes, dependencies))
        await asyncio.gather(*tasks)
        return results

    async def _execute_node_when_ready(self, node_id: str, context: Dict, results: Dict, events: Dict[str, asyncio.Event], dependencies: Dict[str, Set[str]]):
        # Wait for all dependencies
        deps = dependencies[node_id]
        if deps:
            await asyncio.gather(*(events[dep].wait() for dep in deps))
        # Check conditions on incoming edges
        for edge in self.edges:
            if edge.target == node_id and edge.condition:
                if not edge.condition(context):
                    logger.info(f"Node {node_id} skipped (condition false)")
                    results[node_id] = NodeResult(node_id=node_id, output=None, error=None, duration=0)
                    events[node_id].set()
                    return
        # Execute
        node = self.nodes[node_id]
        handler = self._build_middleware_chain()
        start = time.time()
        try:
            output = await handler(node, context)
            error = None
        except Exception as e:
            output = None
            error = e
            logger.error(f"Node {node_id} failed: {e}")
        duration = time.time() - start
        results[node_id] = NodeResult(node_id=node_id, output=output, error=error, duration=duration)
        context[node_id] = output
        events[node_id].set()

    def _build_middleware_chain(self) -> Callable:
        """Build a middleware chain around node execution."""
        chain = self._execute_node_core  # base handler
        for mw in reversed(self.middlewares):
            # Capture middleware and next handler in closure
            current_mw = mw
            next_handler = chain
            async def wrapped(node, ctx, mw=current_mw, next_h=next_handler):
                return await mw.process(node, ctx, next_h)
            chain = wrapped
        return chain

    async def _execute_node_core(self, node: Node, context: Dict[str, Any]) -> Any:
        return await node.execute(context)

    def snapshot(self) -> Dict[str, Any]:
        """Create a snapshot of the graph structure (not runtime state)."""
        return {
            "name": self.name,
            "nodes": [nid for nid in self.nodes],
            "edges": [{"source": e.source, "target": e.target} for e in self.edges],
        }

    @staticmethod
    def from_snapshot(snapshot: Dict[str, Any], node_factory: Callable[[str], Node]) -> 'Graph':
        """Restore graph structure from a snapshot (requires node instances)."""
        g = Graph(snapshot["name"])
        for nid in snapshot["nodes"]:
            g.add_node(node_factory(nid))
        for e in snapshot["edges"]:
            g.add_edge(e["source"], e["target"])
        return g


# State Snapshotting for execution context
class StateSnapshot:
    """Captures the state of an execution (context + results) for later restoration."""
    def __init__(self, context: Dict[str, Any], results: Dict[str, NodeResult]):
        self.context = context
        # Serialize NodeResult, potentially with errors represented as strings
        self.results: Dict[str, Dict] = {}
        for nid, res in results.items():
            self.results[nid] = {
                "output": res.output,
                "error": str(res.error) if res.error else None,
                "duration": res.duration
            }

    def to_dict(self) -> Dict:
        return {"context": self.context, "results": self.results}

    @classmethod
    def from_dict(cls, data: Dict) -> 'StateSnapshot':
        return cls(data.get("context", {}), data.get("results", {}))


# --------------------------------------------------------------------------------
# Inference Client
# --------------------------------------------------------------------------------
@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema for parameters

@dataclass
class ToolCall:
    id: str
    tool: ToolDefinition
    arguments: Dict[str, Any]

@dataclass
class InferenceResponse:
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None  # token usage

class BaseInferenceClient(ABC):
    """Abstract inference client with methods for completion, streaming, and tool calling."""
    def __init__(self, model: str, **kwargs):
        self.model = model
        self.total_tokens_used = 0
        if OPENTELEMETRY_AVAILABLE:
            self.tracer = trace.get_tracer(__name__)
        else:
            self.tracer = None

    @abstractmethod
    async def generate(self, prompt: Union[str, List[Dict]], **kwargs) -> InferenceResponse:
        """Generate a completion given a prompt (string or messages list)."""
        pass

    @abstractmethod
    async def stream_generate(self, prompt: Union[str, List[Dict]], **kwargs) -> AsyncGenerator[str, None]:
        """Stream generation token by token. Yields text chunks."""
        pass

    @abstractmethod
    async def function_call(self, prompt: Union[str, List[Dict]], tools: List[ToolDefinition], **kwargs) -> InferenceResponse:
        """Perform a function/tool call and return the tool calls."""
        pass

    def _record_tokens(self, usage: Dict[str, int]):
        if usage:
            self.total_tokens_used += usage.get("total_tokens", 0)

    def _start_span(self, name: str) -> Optional[Span]:
        if self.tracer:
            return self.tracer.start_span(name)
        return None

# Example implementation using a placeholder (since actual API calls require external libraries)
# We'll simulate with a dummy client that logs.
class DummyInferenceClient(BaseInferenceClient):
    """A dummy inference client for testing; returns fixed responses."""
    async def generate(self, prompt, **kwargs) -> InferenceResponse:
        return InferenceResponse(content="dummy response", usage={"total_tokens": 10})

    async def stream_generate(self, prompt, **kwargs) -> AsyncGenerator[str, None]:
        yield "dummy "
        yield "stream"

    async def function_call(self, prompt, tools, **kwargs) -> InferenceResponse:
        tool_calls = [ToolCall(id="call_1", tool=tools[0], arguments={"arg": "value"})]
        return InferenceResponse(content="", tool_calls=tool_calls, finish_reason="tool_use", usage={"total_tokens": 20})


# --------------------------------------------------------------------------------
# Caching System
# --------------------------------------------------------------------------------
class Cache(ABC):
    """Abstract asynchronous cache interface."""
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def get_all(self, keys: List[str]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass

    @abstractmethod
    async def publish(self, channel: str, message: Any) -> int:
        """Publish a message to a channel (mailbox). Returns number of subscribers that received it."""
        pass

    @abstractmethod
    async def subscribe(self, channel: str) -> AsyncGenerator[Any, None]:
        """Subscribe to a channel and yield messages."""
        pass

class RedisCache(Cache):
    """Redis-backed cache with JSON serialization and prefix/suffix namespacing."""
    def __init__(self, redis_url: str = "redis://localhost:6379", prefix: str = "", suffix: str = "", **kwargs):
        if not REDIS_AVAILABLE:
            raise ImportError("redis package is required for RedisCache. Install with 'pip install redis'")
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True, **kwargs)
        self.prefix = prefix
        self.suffix = suffix
        self._pubsub: Optional[redis.client.PubSub] = None

    def _build_key(self, key: str) -> str:
        return f"{self.prefix}{key}{self.suffix}"

    async def get(self, key: str) -> Optional[Any]:
        full_key = self._build_key(key)
        value = await self.redis.get(full_key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except Exception:
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        full_key = self._build_key(key)
        serialized = json.dumps(value)
        if ttl:
            await self.redis.setex(full_key, ttl, serialized)
        else:
            await self.redis.set(full_key, serialized)

    async def delete(self, key: str) -> bool:
        full_key = self._build_key(key)
        result = await self.redis.delete(full_key)
        return result > 0

    async def exists(self, key: str) -> bool:
        full_key = self._build_key(key)
        return await self.redis.exists(full_key) > 0

    async def get_all(self, keys: List[str]) -> Dict[str, Any]:
        pipeline = self.redis.pipeline()
        for key in keys:
            pipeline.get(self._build_key(key))
        values = await pipeline.execute()
        result = {}
        for key, val in zip(keys, values):
            if val is not None:
                try:
                    result[key] = json.loads(val)
                except Exception:
                    result[key] = val
        return result

    async def clear(self) -> None:
        """Clear all keys matching the prefix/suffix pattern."""
        pattern = self._build_key("*")
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break

    async def publish(self, channel: str, message: Any) -> int:
        full_channel = self._build_key(channel)
        serialized = json.dumps(message)
        return await self.redis.publish(full_channel, serialized)

    async def subscribe(self, channel: str) -> AsyncGenerator[Any, None]:
        full_channel = self._build_key(channel)
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(full_channel)
        self._pubsub = pubsub
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield data
                    except Exception:
                        yield message["data"]
        finally:
            await pubsub.unsubscribe(full_channel)
            await pubsub.punsubscribe()  # just to be safe


# --------------------------------------------------------------------------------
# Prompt Caching Support (inference-level)
# --------------------------------------------------------------------------------
class PromptCache:
    """Simple prompt cache using a Cache backend to store/retrieve completed inferences."""
    def __init__(self, cache: Cache, ttl: Optional[int] = 3600):
        self.cache = cache
        self.ttl = ttl

    async def get_cached_response(self, prompt: str, model: str) -> Optional[InferenceResponse]:
        key = f"prompt:{model}:{prompt}"
        data = await self.cache.get(key)
        if data:
            return InferenceResponse(**data)
        return None

    async def cache_response(self, prompt: str, model: str, response: InferenceResponse):
        key = f"prompt:{model}:{prompt}"
        await self.cache.set(key, response.__dict__, ttl=self.ttl)


# --------------------------------------------------------------------------------
# Full framework integration example (graph + inference + cache)
# --------------------------------------------------------------------------------
class AgentFramework:
    """Orchestrates graph execution with inference and caching."""
    def __init__(self, inference_client: Optional[BaseInferenceClient] = None, cache: Optional[Cache] = None):
        self.inference_client = inference_client or DummyInferenceClient()
        self.cache = cache
        self.prompt_cache = PromptCache(cache) if cache else None

    async def run_graph(self, graph: Graph, initial_context: Optional[Dict] = None) -> Dict[str, NodeResult]:
        """Execute a graph, optionally injecting framework services into context."""
        context = initial_context or {}
        context.setdefault("inference_client", self.inference_client)
        context.setdefault("cache", self.cache)
        context.setdefault("prompt_cache", self.prompt_cache)
        return await graph.execute(context)


# --------------------------------------------------------------------------------
# Tool/Function calling utility
# --------------------------------------------------------------------------------
class ToolExecutor:
    """Utility to execute tool calls from inference responses."""
    @staticmethod
    async def execute_tool_call(tool_call: ToolCall, context: Dict[str, Any]) -> Any:
        """Dispatch tool call to a registered function. This is a stub."""
        # In a real system, you'd have a registry of tools.
        logger.info(f"Executing tool call: {tool_call.tool.name}")
        return {"result": "stub"}

# --------------------------------------------------------------------------------
# Example usage (not executed as part of the import)
# --------------------------------------------------------------------------------
if __name__ == "__main__":
    async def main():
        # Create graph
        graph = Graph("example")
        node1 = FunctionNode("node1", lambda ctx: "Hello")
        node2 = FunctionNode("node2", lambda ctx: f"{ctx['node1']} World")
        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_edge("node1", "node2")
        # Add middleware
        graph.add_middleware(LoggingMiddleware())
        if OPENTELEMETRY_AVAILABLE:
            graph.add_middleware(TracingMiddleware())
        # Execute
        results = await graph.execute()
        print(results)
    asyncio.run(main())