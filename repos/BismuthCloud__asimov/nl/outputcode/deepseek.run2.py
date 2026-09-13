import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, AsyncIterator, Union, Set, Tuple
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import logging

# ---------------------------------------------------------------------------
# OpenTelemetry imports – fallback to no-op if not installed
# ---------------------------------------------------------------------------
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode, SpanKind, Tracer
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor  # not used but example
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    class _NoOpTracer:
        def start_as_current_span(self, *args, **kwargs):
            class _Context:
                async def __aenter__(self): return self
                async def __aexit__(self, *args): pass
                def __enter__(self): return self
                def __exit__(self, *args): pass
            return _Context()
    trace = _NoOpTracer() if not OTEL_AVAILABLE else None  # type: ignore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Core dataclasses used across modules
# ---------------------------------------------------------------------------
@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Message:
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None

# ---------------------------------------------------------------------------
# Graph primitives
# ---------------------------------------------------------------------------
class Node:
    """A single task in the execution graph."""
    def __init__(
        self,
        id: str,
        func: Callable[[Dict[str, Any]], Any],
        input_keys: Optional[List[str]] = None,
        output_keys: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.func = func
        self.input_keys = input_keys or []
        self.output_keys = output_keys or []
        self.config = config or {}

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        inputs = {k: state.get(k) for k in self.input_keys}
        result = self.func(**inputs)
        if asyncio.iscoroutine(result):
            result = await result
        if not isinstance(result, dict):
            result = {self.output_keys[0]: result} if self.output_keys else {}
        else:
            # ensure only declared output keys are kept
            filtered = {k: result[k] for k in self.output_keys if k in result}
            result = filtered
        return result

class Edge:
    """Directed edge between two nodes."""
    def __init__(self, from_node: str, to_node: str, condition: Optional[Callable[[Dict[str, Any]], bool]] = None):
        self.from_node = from_node
        self.to_node = to_node
        self.condition = condition

class GraphSnapshot:
    """Serializable snapshot of graph execution state."""
    def __init__(self, state: Dict[str, Any], node_status: Dict[str, str]):
        self.state = state
        self.node_status = node_status

    def to_dict(self) -> Dict[str, Any]:
        return {"state": self.state, "node_status": self.node_status}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphSnapshot":
        return cls(state=data["state"], node_status=data["node_status"])

class Graph:
    """Graph of nodes and edges. Supports middleware and snapshotting."""
    def __init__(self, nodes: List[Node], edges: List[Edge], middleware: Optional[List["Middleware"]] = None):
        self.nodes: Dict[str, Node] = {n.id: n for n in nodes}
        self.edges = edges
        self.middleware = middleware or []
        self._validate()

    def _validate(self):
        node_ids = set(self.nodes.keys())
        for edge in self.edges:
            if edge.from_node not in node_ids:
                raise ValueError(f"Edge from unknown node: {edge.from_node}")
            if edge.to_node not in node_ids:
                raise ValueError(f"Edge to unknown node: {edge.to_node}")

    def _topological_sort(self) -> List[str]:
        adj: Dict[str, Set[str]] = {nid: set() for nid in self.nodes}
        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}
        for edge in self.edges:
            adj[edge.from_node].add(edge.to_node)
            in_degree[edge.to_node] += 1
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        if len(order) != len(self.nodes):
            raise RuntimeError("Graph contains a cycle")
        return order

    async def execute(self, initial_state: Dict[str, Any]) -> GraphSnapshot:
        state = dict(initial_state)
        node_status: Dict[str, str] = {}
        order = self._topological_sort()
        # middleware chain setup
        chain = MiddlewareChain(self.middleware, "execute")
        ctx = {"graph": self, "state": state}
        await chain.before_all(ctx)
        for nid in order:
            node = self.nodes[nid]
            node_status[nid] = "running"
            ctx["current_node"] = node
            await chain.before_node(ctx)
            try:
                updates = await node.run(state)
                state.update(updates)
                node_status[nid] = "completed"
                await chain.after_node(ctx, updates=updates)
            except Exception as e:
                node_status[nid] = f"failed: {str(e)}"
                await chain.on_node_error(ctx, error=e)
                raise
        await chain.after_all(ctx, final_state=state)
        return GraphSnapshot(state=state, node_status=node_status)

    def snapshot(self, state: Dict[str, Any]) -> GraphSnapshot:
        # create snapshot of current hypothetical state (not running)
        return GraphSnapshot(state=state, node_status={nid: "unknown" for nid in self.nodes})

# ---------------------------------------------------------------------------
# Middleware base
# ---------------------------------------------------------------------------
class Middleware:
    """Base class for graph execution middleware."""
    async def before_all(self, context: Dict[str, Any]) -> None:
        pass

    async def after_all(self, context: Dict[str, Any], final_state: Dict[str, Any]) -> None:
        pass

    async def before_node(self, context: Dict[str, Any]) -> None:
        pass

    async def after_node(self, context: Dict[str, Any], updates: Dict[str, Any]) -> None:
        pass

    async def on_node_error(self, context: Dict[str, Any], error: Exception) -> None:
        pass

class MiddlewareChain:
    def __init__(self, middlewares: List[Middleware], phase: str):
        self.middlewares = middlewares
        self.phase = phase

    async def before_all(self, ctx):
        for m in self.middlewares:
            await m.before_all(ctx)

    async def after_all(self, ctx, final_state):
        for m in self.middlewares:
            await m.after_all(ctx, final_state)

    async def before_node(self, ctx):
        for m in self.middlewares:
            await m.before_node(ctx)

    async def after_node(self, ctx, updates):
        for m in self.middlewares:
            await m.after_node(ctx, updates)

    async def on_node_error(self, ctx, error):
        for m in self.middlewares:
            await m.on_node_error(ctx, error)

# ---------------------------------------------------------------------------
# Inference clients (LLM providers) with streaming, tool calls, OTEL, caching
# ---------------------------------------------------------------------------
class InferenceClient(ABC):
    """Abstract interface for LLM providers."""
    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
        **kwargs,
    ) -> Message:
        ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
        **kwargs,
    ) -> AsyncIterator[Message]:
        ...

    @abstractmethod
    async def get_token_usage(self) -> TokenUsage:
        """Return the accumulated token usage across requests."""
        ...

class OpenAIClient(InferenceClient):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
        self._token_usage = TokenUsage()

    async def chat(self, messages, tools=None, temperature=0.7, max_tokens=None, stop_sequences=None, **kwargs):
        # In a real implementation this would call the OpenAI API
        raise NotImplementedError("Real API call not implemented in skeleton")

    async def stream_chat(self, messages, tools=None, temperature=0.7, max_tokens=None, stop_sequences=None, **kwargs):
        raise NotImplementedError("Real streaming not implemented in skeleton")

    async def get_token_usage(self) -> TokenUsage:
        return self._token_usage

class AnthropicClient(InferenceClient):
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        self.api_key = api_key
        self.model = model
        self._token_usage = TokenUsage()

    async def chat(self, messages, tools=None, temperature=0.7, max_tokens=None, stop_sequences=None, **kwargs):
        raise NotImplementedError("Real API call not implemented in skeleton")

    async def stream_chat(self, messages, tools=None, temperature=0.7, max_tokens=None, stop_sequences=None, **kwargs):
        raise NotImplementedError("Real streaming not implemented in skeleton")

    async def get_token_usage(self) -> TokenUsage:
        return self._token_usage

class MockInferenceClient(InferenceClient):
    """Mock client for testing – returns predetermined responses."""
    def __init__(self, responses: Optional[List[Message]] = None):
        self.responses = responses or []
        self._idx = 0
        self._token_usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)

    async def chat(self, messages, tools=None, temperature=0.7, max_tokens=None, stop_sequences=None, **kwargs):
        await asyncio.sleep(0.01)
        if self._idx < len(self.responses):
            resp = self.responses[self._idx]
            self._idx += 1
            return resp
        return Message(role="assistant", content="Mock response")

    async def stream_chat(self, messages, tools=None, temperature=0.7, max_tokens=None, stop_sequences=None, **kwargs):
        for char in "Mock streaming response":
            await asyncio.sleep(0.001)
            yield Message(role="assistant", content=char)

    async def get_token_usage(self) -> TokenUsage:
        return self._token_usage

# Decorator to add OpenTelemetry instrumentation to inference calls
def instrument_inference(func):
    """Instruments an async inference method with span."""
    if not OTEL_AVAILABLE:
        return func
    tracer = trace.get_tracer(__name__)
    async def wrapper(self, *args, **kwargs):
        with tracer.start_as_current_span(f"InferenceClient.{func.__name__}", kind=SpanKind.CLIENT) as span:
            span.set_attribute("provider", self.__class__.__name__)
            try:
                result = await func(self, *args, **kwargs)
                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as ex:
                span.set_status(Status(StatusCode.ERROR, str(ex)))
                raise
    return wrapper

class TracedInferenceClient(InferenceClient):
    """Wrapper that adds OTEL tracing to any InferenceClient."""
    def __init__(self, client: InferenceClient):
        self._client = client

    async def chat(self, messages, tools=None, temperature=0.7, max_tokens=None, stop_sequences=None, **kwargs):
        return await instrument_inference(self._client.chat)(self._client, messages, tools, temperature, max_tokens, stop_sequences, **kwargs)  # type: ignore[call-arg]

    async def stream_chat(self, messages, tools=None, temperature=0.7, max_tokens=None, stop_sequences=None, **kwargs):
        # For streaming we trace the whole stream
        if OTEL_AVAILABLE:
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span("InferenceClient.stream_chat", kind=SpanKind.CLIENT) as span:
                span.set_attribute("provider", self._client.__class__.__name__)
                try:
                    async for chunk in self._client.stream_chat(messages, tools, temperature, max_tokens, stop_sequences, **kwargs):
                        yield chunk
                    span.set_status(Status(StatusCode.OK))
                except Exception as ex:
                    span.set_status(Status(StatusCode.ERROR, str(ex)))
                    raise
        else:
            async for chunk in self._client.stream_chat(messages, tools, temperature, max_tokens, stop_sequences, **kwargs):
                yield chunk

    async def get_token_usage(self) -> TokenUsage:
        return await self._client.get_token_usage()

# Prompt caching support via decorators or mixin
class PromptCacheMixin:
    """Mixin that adds prompt caching to an InferenceClient using a Cache instance."""
    _cache: "Cache"
    _cache_ttl: int

    def __init__(self, cache: "Cache", ttl: int = 60):
        self._cache = cache
        self._cache_ttl = ttl

    def _cache_key(self, messages: List[Message], prefix: str = "prompt") -> str:
        # naive key based on first few messages to represent the "prefix"
        serialized = json.dumps([m.__dict__ for m in messages[:3]])
        return f"{prefix}:{serialized}"

    async def cached_chat(self, messages, **kwargs) -> Message:
        key = self._cache_key(messages)
        cached = await self._cache.get(key)
        if cached:
            return Message(**json.loads(cached))
        resp = await self.chat(messages, **kwargs)
        await self._cache.set(key, json.dumps(resp.__dict__), ttl=self._cache_ttl)
        return resp

# ---------------------------------------------------------------------------
# Caching system
# ---------------------------------------------------------------------------
class Cache(ABC):
    """Abstract asynchronous cache interface."""
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
    async def get_all(self, prefix: str = "") -> Dict[str, str]:
        ...

    @abstractmethod
    async def clear(self) -> None:
        ...

    @abstractmethod
    async def publish(self, channel: str, message: str) -> None:
        ...

    @abstractmethod
    async def subscribe(self, channel: str, callback: Callable[[str], None]) -> None:
        ...

    @abstractmethod
    async def unsubscribe(self, channel: str) -> None:
        ...

    def with_prefix(self, prefix: str) -> "PrefixedCache":
        """Return a Cache that prepends a prefix to all keys."""
        return PrefixedCache(self, prefix=prefix, suffix="")

    def with_suffix(self, suffix: str) -> "PrefixedCache":
        """Return a Cache that appends a suffix to all keys."""
        return PrefixedCache(self, prefix="", suffix=suffix)

    def with_prefix_suffix(self, prefix: str, suffix: str) -> "PrefixedCache":
        return PrefixedCache(self, prefix=prefix, suffix=suffix)

class PrefixedCache(Cache):
    """Wraps a Cache to add prefix/suffix to keys."""
    def __init__(self, cache: Cache, prefix: str = "", suffix: str = ""):
        self._cache = cache
        self._prefix = prefix
        self._suffix = suffix

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}{key}{self._suffix}"

    async def get(self, key: str) -> Optional[str]:
        return await self._cache.get(self._full_key(key))

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        await self._cache.set(self._full_key(key), value, ttl)

    async def delete(self, key: str) -> None:
        await self._cache.delete(self._full_key(key))

    async def get_all(self, prefix: str = "") -> Dict[str, str]:
        full_prefix = self._full_key(prefix)
        all_items = await self._cache.get_all(full_prefix)
        # strip out prefix/suffix from returned keys for caller
        stripped = {}
        for k, v in all_items.items():
            if k.startswith(self._prefix) and k.endswith(self._suffix):
                inner = k[len(self._prefix):-len(self._suffix)] if self._suffix else k[len(self._prefix):]
                stripped[inner] = v
        return stripped

    async def clear(self) -> None:
        # This is tricky: clearing all keys with this prefix only
        # We'll approximate by fetching all keys matching prefix and deleting them
        # Better: use pattern scanning in Redis directly.
        await self._cache.clear()  # simple pass-through, but not ideal

    async def publish(self, channel: str, message: str) -> None:
        await self._cache.publish(channel, message)  # channels usually not prefixed

    async def subscribe(self, channel: str, callback: Callable[[str], None]) -> None:
        await self._cache.subscribe(channel, callback)

    async def unsubscribe(self, channel: str) -> None:
        await self._cache.unsubscribe(channel)

class RedisCache(Cache):
    """Redis implementation of the Cache interface."""
    def __init__(self, redis_url: str = "redis://localhost:6379", encoding: str = "utf-8"):
        self._redis = None
        self._redis_url = redis_url
        self._encoding = encoding
        self._pubsub = None
        self._subscriptions: Dict[str, List[Callable]] = {}

    async def _ensure_connection(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def _ensure_pubsub(self):
        if self._pubsub is None:
            redis = await self._ensure_connection()
            self._pubsub = redis.pubsub()
        return self._pubsub

    async def get(self, key: str) -> Optional[str]:
        r = await self._ensure_connection()
        val = await r.get(key)
        return val

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        r = await self._ensure_connection()
        if ttl:
            await r.setex(key, ttl, value)
        else:
            await r.set(key, value)

    async def delete(self, key: str) -> None:
        r = await self._ensure_connection()
        await r.delete(key)

    async def get_all(self, prefix: str = "") -> Dict[str, str]:
        r = await self._ensure_connection()
        pattern = f"{prefix}*" if prefix else "*"
        keys = []
        async for key in r.scan_iter(match=pattern):
            keys.append(key)
        if not keys:
            return {}
        values = await r.mget(keys)
        return dict(zip(keys, values))

    async def clear(self) -> None:
        r = await self._ensure_connection()
        await r.flushdb()

    async def publish(self, channel: str, message: str) -> None:
        r = await self._ensure_connection()
        await r.publish(channel, message)

    async def subscribe(self, channel: str, callback: Callable[[str], None]) -> None:
        ps = await self._ensure_pubsub()
        await ps.subscribe(channel)
        if channel not in self._subscriptions:
            self._subscriptions[channel] = []
            # start a background task to listen
            asyncio.create_task(self._listen_channel(channel))
        self._subscriptions[channel].append(callback)

    async def unsubscribe(self, channel: str) -> None:
        if channel in self._subscriptions:
            ps = await self._ensure_pubsub()
            await ps.unsubscribe(channel)
            del self._subscriptions[channel]

    async def _listen_channel(self, channel: str):
        ps = await self._ensure_pubsub()
        async for msg in ps.listen():
            if msg["type"] == "message":
                for cb in self._subscriptions.get(channel, []):
                    try:
                        if asyncio.iscoroutinefunction(cb):
                            await cb(msg["data"])
                        else:
                            cb(msg["data"])
                    except Exception:
                        logger.exception("Error in pubsub callback")

# ---------------------------------------------------------------------------
# Mailbox: higher-level messaging over pub/sub
# ---------------------------------------------------------------------------
class Mailbox:
    """A named mailbox for agent communication using pub/sub."""
    def __init__(self, name: str, cache: Cache):
        self.name = name
        self.cache = cache
        self._callbacks: List[Callable] = []

    async def send(self, message: str) -> None:
        await self.cache.publish(self.name, message)

    async def receive(self, callback: Callable[[str], None]) -> None:
        self._callbacks.append(callback)
        await self.cache.subscribe(self.name, callback)

    async def stop(self) -> None:
        for cb in self._callbacks:
            await self.cache.unsubscribe(self.name)

# ---------------------------------------------------------------------------
# LLM Directed Graph Execution
# ---------------------------------------------------------------------------
class LLMGraphExecutor:
    """Uses an LLM to dynamically decide which nodes to execute next based on state."""
    def __init__(self, inference_client: InferenceClient, available_nodes: Dict[str, Node], system_prompt: str = ""):
        self.client = inference_client
        self.nodes = available_nodes
        self.system_prompt = system_prompt

    async def plan_next_node(self, state: Dict[str, Any], done_nodes: Set[str]) -> Optional[str]:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": node_id,
                    "description": f"Execute node {node_id}",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
            for node_id in self.nodes if node_id not in done_nodes
        ]
        messages = [Message(role="system", content=self.system_prompt)]
        # Add current state summary
        state_summary = json.dumps(state, indent=2)
        messages.append(Message(role="user", content=f"Current state: {state_summary}\nBased on the available tools, which node should be executed next? If none, respond with reason."))
        resp = await self.client.chat(messages, tools=tools, temperature=0)
        if resp.tool_calls:
            # Take first tool call as the chosen node
            return resp.tool_calls[0].name
        return None

    async def execute(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        state = dict(initial_state)
        done: Set[str] = set()
        while True:
            next_node_id = await self.plan_next_node(state, done)
            if next_node_id is None:
                break
            node = self.nodes[next_node_id]
            updates = await node.run(state)
            state.update(updates)
            done.add(next_node_id)
        return state

# ---------------------------------------------------------------------------
# Telemetry initialization
# ---------------------------------------------------------------------------
def init_telemetry(service_name: str = "agent-framework", exporter: Any = None):
    """Initialize OpenTelemetry tracer provider."""
    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry not installed. Tracing disabled.")
        return
    provider = TracerProvider()
    if exporter is None:
        exporter = ConsoleSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

# ---------------------------------------------------------------------------
# State Snapshotting utilities
# ---------------------------------------------------------------------------
class StateManager:
    """Manages snapshots of graph states."""
    def __init__(self, cache: Cache):
        self.cache = cache

    async def save_snapshot(self, execution_id: str, snapshot: GraphSnapshot) -> None:
        key = f"snapshot:{execution_id}"
        await self.cache.set(key, json.dumps(snapshot.to_dict()))

    async def load_snapshot(self, execution_id: str) -> Optional[GraphSnapshot]:
        key = f"snapshot:{execution_id}"
        data = await self.cache.get(key)
        if data:
            return GraphSnapshot.from_dict(json.loads(data))
        return None

    async def delete_snapshot(self, execution_id: str) -> None:
        key = f"snapshot:{execution_id}"
        await self.cache.delete(key)

# ---------------------------------------------------------------------------
# Example usage (if run directly)
# ---------------------------------------------------------------------------
async def main():
    # Initialize OpenTelemetry
    init_telemetry(service_name="agent-framework-example")

    # Create a mock inference client
    mock_client = MockInferenceClient(responses=[
        Message(role="assistant", content="Hello from mock"),
        Message(role="assistant", tool_calls=[ToolCall(name="node2", arguments={})]),
    ])

    # Create Redis cache (will fail if Redis not running, so fallback to a simple dict cache for demo)
    try:
        redis_cache = RedisCache(redis_url="redis://localhost:6379")
        cache: Cache = redis_cache
    except Exception:
        # fallback in-memory for testing
        class DictCache(Cache):
            def __init__(self):
                self.store = {}
                self.pubsub = {}
            async def get(self, key): return self.store.get(key)
            async def set(self, key, value, ttl=None): self.store[key] = value
            async def delete(self, key): self.store.pop(key, None)
            async def get_all(self, prefix=""): return {k:v for k,v in self.store.items() if k.startswith(prefix)}
            async def clear(self): self.store.clear()
            async def publish(self, channel, message):
                if channel in self.pubsub:
                    for cb in self.pubsub[channel]:
                        await cb(message)
            async def subscribe(self, channel, callback):
                self.pubsub.setdefault(channel, []).append(callback)
            async def unsubscribe(self, channel):
                self.pubsub.pop(channel, None)
        cache = DictCache()

    # Use cache with prefix
    agent_cache = cache.with_prefix("myagent:")

    # Build a simple graph
    async def node1_func(x: int) -> dict:
        return {"x_plus_one": x + 1}

    async def node2_func(x_plus_one: int) -> dict:
        return {"final": x_plus_one * 2}

    node1 = Node("node1", node1_func, input_keys=["x"], output_keys=["x_plus_one"])
    node2 = Node("node2", node2_func, input_keys=["x_plus_one"], output_keys=["final"])
    edge1 = Edge("node1", "node2")
    graph = Graph(nodes=[node1, node2], edges=[edge1])

    snapshot = await graph.execute({"x": 5})
    print("Graph snapshot state:", snapshot.state)
    print("Node status:", snapshot.node_status)

    # LLM directed execution
    llm_executor = LLMGraphExecutor(mock_client, available_nodes={"node1": node1, "node2": node2})
    final_state = await llm_executor.execute({"x": 5})
    print("LLM directed final state:", final_state)

if __name__ == "__main__":
    asyncio.run(main())