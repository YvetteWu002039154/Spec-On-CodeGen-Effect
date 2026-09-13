from __future__ import annotations

import abc
import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)

# ---------------------------------------------------------------------------
# Opentelemetry integration (fallback to no-op if not installed)
# ---------------------------------------------------------------------------
try:
    from opentelemetry import trace
    from opentelemetry.trace import Span, Status, StatusCode

    _TRACER = trace.get_tracer(__name__)

    def _start_span(name: str, attributes: Optional[Dict[str, Any]] = None) -> Span:
        return _TRACER.start_as_current_span(name, attributes=attributes or {})

except ImportError:
    # Simple no‑op context manager and tracer
    class _NoopSpan:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def set_attribute(self, *args, **kwargs): pass
        def set_status(self, *args, **kwargs): pass
        def end(self, *args, **kwargs): pass

    def _start_span(name: str, attributes: Optional[Dict[str, Any]] = None) -> _NoopSpan:
        return _NoopSpan()

    class trace:
        @staticmethod
        def get_tracer(name: str) -> Any:
            return _NoopSpan


# ---------------------------------------------------------------------------
# Common data models
# ---------------------------------------------------------------------------
T = TypeVar("T")


@dataclass
class Message:
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None  # optional tool name


@dataclass
class Tool:
    type: str = "function"
    function: Dict[str, Any] = field(default_factory=dict)  # contains "name", "description", "parameters"


@dataclass
class ToolCall:
    id: str
    type: str = "function"
    function: Dict[str, Any] = field(default_factory=dict)  # {"name": "...", "arguments": "..."}


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class CompleteResponse:
    message: Message
    usage: Usage
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"


@dataclass
class StreamChunk:
    content: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: Optional[str] = None
    usage: Optional[Usage] = None


@dataclass
class GraphNodeState:
    """Holds the output of a node after execution."""
    result: Any
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Caching system
# ---------------------------------------------------------------------------
class Cache(abc.ABC):
    """Abstract asynchronous key‑value cache with namespace support and pub/sub."""

    def __init__(self, prefix: str = "", suffix: str = "") -> None:
        self.prefix = prefix
        self.suffix = suffix

    def _apply_namespace(self, key: str) -> str:
        return f"{self.prefix}{key}{self.suffix}"

    def _strip_namespace(self, key: str) -> str:
        if self.prefix and key.startswith(self.prefix):
            key = key[len(self.prefix):]
        if self.suffix and key.endswith(self.suffix):
            key = key[: -len(self.suffix)]
        return key

    @abc.abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a single value (deserialised from JSON)."""
        ...

    @abc.abstractmethod
    async def set(self, key: str, value: Any) -> None:
        """Store a value (serialised as JSON)."""
        ...

    @abc.abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a single key. Returns True if the key existed."""
        ...

    @abc.abstractmethod
    async def get_all(self, prefix: str = "") -> Dict[str, Any]:
        """Return all keys matching the given prefix (after namespacing)."""
        ...

    @abc.abstractmethod
    async def clear(self) -> int:
        """Remove all keys within the cache's namespace. Returns count of removed keys."""
        ...

    @abc.abstractmethod
    async def publish(self, channel: str, message: Any) -> int:
        """Publish a JSON‑serialisable message to a channel. Returns number of clients that received it."""
        ...

    @abc.abstractmethod
    async def subscribe(self, channel: str) -> AsyncIterator[Any]:
        """Subscribe to a channel and yield deserialised messages."""
        ...

    def mailbox(self, name: str) -> str:
        """Return a channel name suitable for pub/sub communication."""
        return self._apply_namespace(f"mailbox:{name}")


class RedisCache(Cache):
    """Asynchronous Redis implementation of the Cache interface."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        prefix: str = "",
        suffix: str = "",
    ) -> None:
        super().__init__(prefix, suffix)
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(redis_url)
        except ImportError:
            raise ImportError("redis package is required for RedisCache. Install it with 'pip install redis'")

    async def _raw_get(self, namespaced_key: str) -> Optional[str]:
        return await self._redis.get(namespaced_key)

    async def _raw_set(self, namespaced_key: str, serialized: str) -> None:
        await self._redis.set(namespaced_key, serialized)

    async def _raw_delete(self, namespaced_key: str) -> bool:
        return await self._redis.delete(namespaced_key) > 0

    async def get(self, key: str) -> Optional[Any]:
        raw = await self._raw_get(self._apply_namespace(key))
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any) -> None:
        await self._raw_set(self._apply_namespace(key), json.dumps(value))

    async def delete(self, key: str) -> bool:
        return await self._raw_delete(self._apply_namespace(key))

    async def get_all(self, prefix: str = "") -> Dict[str, Any]:
        pattern = self._apply_namespace(prefix) + "*"
        cursor = 0
        result = {}
        while True:
            cursor, keys = await self._redis.scan(cursor, match=pattern)
            if keys:
                values = await self._redis.mget(keys)
                for k, v in zip(keys, values):
                    if v is not None:
                        stripped = self._strip_namespace(k.decode("utf-8"))
                        result[stripped] = json.loads(v)
            if cursor == 0:
                break
        return result

    async def clear(self) -> int:
        pattern = self._apply_namespace("*")
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = await self._redis.scan(cursor, match=pattern)
            if keys:
                deleted += await self._redis.delete(*keys)
            if cursor == 0:
                break
        return deleted

    async def publish(self, channel: str, message: Any) -> int:
        full_channel = self._apply_namespace(channel)
        payload = json.dumps(message)
        return await self._redis.publish(full_channel, payload)

    async def subscribe(self, channel: str) -> AsyncIterator[Any]:
        full_channel = self._apply_namespace(channel)
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(full_channel)
        try:
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg["type"] == "message":
                    yield json.loads(msg["data"])
                await asyncio.sleep(0.001)
        finally:
            await pubsub.unsubscribe(full_channel)
            await pubsub.close()


# ---------------------------------------------------------------------------
# Graph primitives
# ---------------------------------------------------------------------------
class Node(abc.ABC):
    """A unit of work in the graph."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abc.abstractmethod
    async def run(self, state: Dict[str, GraphNodeState]) -> Any:
        """
        Execute the node logic.
        Receives the current state (mapping node names to their outputs).
        Returns the output that will be stored in the state under this node's name.
        """
        ...

    def get_next_nodes(self, state: Dict[str, GraphNodeState]) -> List[str]:
        """
        Return a dynamic list of downstream node names.
        If empty, the static graph edges are used instead.
        """
        return []

    def __repr__(self) -> str:
        return f"<Node {self.name}>"


class Graph:
    """A directed acyclic graph of nodes with named static edges."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, List[str]] = {}   # source -> list of targets

    def add_node(self, node: Node) -> None:
        if node.name in self.nodes:
            raise ValueError(f"Node '{node.name}' already exists in graph '{self.name}'")
        self.nodes[node.name] = node
        self.edges.setdefault(node.name, [])

    def add_edge(self, from_node: str, to_node: str) -> None:
        if from_node not in self.nodes:
            raise ValueError(f"Source node '{from_node}' not found")
        if to_node not in self.nodes:
            raise ValueError(f"Target node '{to_node}' not found")
        self.edges[from_node].append(to_node)

    def validate(self) -> None:
        """Check for cycles using Kahn's algorithm."""
        in_degree: Dict[str, int] = {name: 0 for name in self.nodes}
        for source, targets in self.edges.items():
            for target in targets:
                in_degree[target] += 1

        queue = [name for name, deg in in_degree.items() if deg == 0]
        visited = 0
        while queue:
            node = queue.pop(0)
            visited += 1
            for target in self.edges[node]:
                in_degree[target] -= 1
                if in_degree[target] == 0:
                    queue.append(target)

        if visited != len(self.nodes):
            raise RuntimeError(f"Graph '{self.name}' contains a cycle")


Middleware = Callable[[Node, Dict[str, GraphNodeState], Callable[[], Awaitable[Any]]], Awaitable[Any]]


class GraphExecutor:
    """
    Executes a Graph, respecting dependencies (static + dynamic) and
    running independent nodes concurrently.
    Supports middleware, state snapshotting and LLM‑directed routing.
    """

    def __init__(
        self,
        graph: Graph,
        middleware: Optional[List[Middleware]] = None,
    ) -> None:
        self.graph = graph
        graph.validate()
        self.middleware = middleware or []
        self.state: Dict[str, GraphNodeState] = {}
        self._executed: Set[str] = set()
        self._pending: Set[str] = set()
        self._dynamic_futures: Dict[str, asyncio.Task] = {}

    async def execute(self) -> Dict[str, GraphNodeState]:
        """Run the graph to completion. Returns the final state."""
        self.state.clear()
        self._executed.clear()
        self._pending = set(self.graph.nodes.keys())

        # Determine initial executable nodes (zero in-degree from static edges)
        static_in_degree: Dict[str, int] = {name: 0 for name in self.graph.nodes}
        for src, targets in self.graph.edges.items():
            for tgt in targets:
                static_in_degree[tgt] += 1

        ready = [name for name, deg in static_in_degree.items() if deg == 0]
        tasks: List[asyncio.Task] = []

        async def run_node(name: str) -> None:
            node = self.graph.nodes[name]
            result = await self._apply_middleware(node, self.state)
            self.state[name] = GraphNodeState(result=result)
            self._executed.add(name)
            self._pending.discard(name)

            # Determine downstream nodes (combine static + dynamic)
            next_nodes = set(self.graph.edges.get(name, []))
            dynamic = node.get_next_nodes(self.state)
            if dynamic:
                next_nodes.update(dynamic)

            # For dynamic edges, we may need to update in-degree on the fly.
            # Here we simply allow immediate scheduling for both static and dynamic.
            # (A proper engine would maintain a runnable queue; for simplicity we
            # just launch all downstream that have all static preconditions met.)
            ready_local = []
            for n in next_nodes:
                if n not in self._executed and n not in self._pending:
                    continue
                # Check static dependencies: all upstream nodes must be executed.
                static_deps = [
                    src for src, tgt_list in self.graph.edges.items() if n in tgt_list
                ]
                if all(dep in self._executed for dep in static_deps):
                    ready_local.append(n)

            # Spawn ready nodes
            for n in sorted(set(ready_local)):
                if n not in self._executed and n not in self._pending:
                    self._pending.add(n)
                    tasks.append(asyncio.create_task(run_node(n)))

        # Start initial nodes
        for name in ready:
            self._pending.add(name)
            tasks.append(asyncio.create_task(run_node(name)))

        # Wait for all tasks to finish
        if tasks:
            await asyncio.gather(*tasks)

        return self.state

    async def _apply_middleware(self, node: Node, state: Dict[str, GraphNodeState]) -> Any:
        core = _NodeCore(node, state)

        # Build the middleware chain
        handler = core.run
        for mw in reversed(self.middleware):
            handler = _make_mw_callable(mw, node, state, handler)

        return await handler()

    def get_snapshot(self) -> Dict[str, Any]:
        """Return a serialisable snapshot of the current execution state."""
        return {
            "graph_name": self.graph.name,
            "executed": list(self._executed),
            "state": {
                name: {"result": ns.result, "timestamp": ns.timestamp, "metadata": ns.metadata}
                for name, ns in self.state.items()
            },
        }

    def restore_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """Restore execution state from a previously taken snapshot."""
        self._executed = set(snapshot["executed"])
        self.state = {
            name: GraphNodeState(
                result=item["result"],
                timestamp=item.get("timestamp", 0.0),
                metadata=item.get("metadata", {}),
            )
            for name, item in snapshot["state"].items()
        }
        self._pending = set(self.graph.nodes.keys()) - self._executed


class _NodeCore:
    """Small helper that calls the node's run method."""
    def __init__(self, node: Node, state: Dict[str, GraphNodeState]) -> None:
        self.node = node
        self.state = state

    async def run(self) -> Any:
        return await self.node.run(self.state)


def _make_mw_callable(
    mw: Middleware,
    node: Node,
    state: Dict[str, GraphNodeState],
    next_handler: Callable[[], Awaitable[Any]],
) -> Callable[[], Awaitable[Any]]:
    async def wrapper() -> Any:
        return await mw(node, state, next_handler)

    return wrapper


# ---------------------------------------------------------------------------
# Inference client
# ---------------------------------------------------------------------------
class InferenceClient(abc.ABC):
    """Abstract language model client with streaming, tool calling, token tracking."""

    def __init__(self, cache: Optional[Cache] = None) -> None:
        self.cache = cache

    @abc.abstractmethod
    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        stream: bool = False,
    ) -> Union[CompleteResponse, AsyncIterator[StreamChunk]]:
        ...

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Convenience method that calls complete with stream=True and yields chunks."""
        result = await self.complete(messages, tools, stream=True)
        if isinstance(result, CompleteResponse):
            # Fallback for non-streaming implementations
            yield StreamChunk(content=result.message.content, finish_reason="stop", usage=result.usage)
            return
        async for chunk in result:
            yield chunk

    async def _compute_cache_key(self, messages: List[Message], tools: Optional[List[Tool]] = None) -> str:
        payload = {
            "messages": [(m.role, m.content, getattr(m, "name", None)) for m in messages],
            "tools": None if tools is None else [t.function for t in tools],
        }
        key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return f"llm_cache:{key}"


class DummyOpenAI(InferenceClient):
    """Simplistic OpenAI clone for demonstration purposes."""

    def __init__(self, api_key: str = "dummy", model: str = "gpt-4", cache: Optional[Cache] = None) -> None:
        super().__init__(cache)
        self.api_key = api_key
        self.model = model

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        stream: bool = False,
    ) -> Union[CompleteResponse, AsyncIterator[StreamChunk]]:
        with _start_span("llm.complete", attributes={"model": self.model}):
            if self.cache:
                cache_key = await self._compute_cache_key(messages, tools)
                cached = await self.cache.get(cache_key)
                if cached is not None:
                    return cached

            # Simulate token usage
            prompt_tokens = sum(len(m.content.split()) for m in messages)
            completion_tokens = 10
            usage = Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )
            if stream:
                async def stream_gen():
                    for i in range(5):
                        await asyncio.sleep(0.01)
                        yield StreamChunk(content=f"chunk{i} ", usage=None)
                    yield StreamChunk(content=None, finish_reason="stop", usage=usage)

                return stream_gen()

            response = CompleteResponse(
                message=Message(role="assistant", content="This is a dummy response."),
                usage=usage,
            )
            if self.cache:
                await self.cache.set(cache_key, response)
            return response


class DummyAnthropic(InferenceClient):
    """Simulated Anthropic Claude client."""

    def __init__(self, api_key: str = "dummy", model: str = "claude-3-opus-20240229", cache: Optional[Cache] = None) -> None:
        super().__init__(cache)
        self.api_key = api_key
        self.model = model

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        stream: bool = False,
    ) -> Union[CompleteResponse, AsyncIterator[StreamChunk]]:
        with _start_span("llm.complete", attributes={"model": self.model}):
            if self.cache:
                cache_key = await self._compute_cache_key(messages, tools)
                cached = await self.cache.get(cache_key)
                if cached is not None:
                    return cached

            prompt_tokens = sum(len(m.content.split()) for m in messages)
            completion_tokens = 8
            usage = Usage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                          total_tokens=prompt_tokens + completion_tokens)

            if stream:
                async def stream_gen():
                    for i in range(3):
                        await asyncio.sleep(0.01)
                        yield StreamChunk(content=f"Claude chunk {i} ", usage=None)
                    yield StreamChunk(content=None, finish_reason="stop", usage=usage)
                return stream_gen()

            response = CompleteResponse(
                message=Message(role="assistant", content="Claude's dummy thinking."),
                usage=usage,
            )
            if self.cache:
                await self.cache.set(cache_key, response)
            return response


# Decorator to wrap a client with OpenTelemetry instrumentation (already done inside complete,
# but this can be used as a mixin)
class InstrumentedClient(InferenceClient):
    """Wrapper that adds OpenTelemetry spans around a base client."""

    def __init__(self, base: InferenceClient) -> None:
        super().__init__(cache=getattr(base, "cache", None))
        self._base = base

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        stream: bool = False,
    ) -> Union[CompleteResponse, AsyncIterator[StreamChunk]]:
        with _start_span("inference_call", attributes={"provider": type(self._base).__name__}):
            return await self._base.complete(messages, tools, stream)


# ---------------------------------------------------------------------------
# Example specialised nodes
# ---------------------------------------------------------------------------
class LLMDirectedDecisionNode(Node):
    """
    A node that uses an LLM to decide which downstream node(s) to execute next.
    """

    def __init__(
        self,
        name: str,
        client: InferenceClient,
        prompt: Callable[[Dict[str, GraphNodeState]], List[Message]],
        choices: List[str],
    ) -> None:
        super().__init__(name)
        self.client = client
        self.prompt = prompt
        self.choices = choices

    async def run(self, state: Dict[str, GraphNodeState]) -> str:
        messages = self.prompt(state)
        response = await self.client.complete(messages, stream=False)
        answer = response.message.content.strip().lower()
        # Simple rule: the response must be one of the choices
        for choice in self.choices:
            if choice.lower() in answer:
                return choice
        return self.choices[0]

    def get_next_nodes(self, state: Dict[str, GraphNodeState]) -> List[str]:
        chosen = state.get(self.name)
        if chosen is None:
            return []
        result = chosen.result
        # result is the chosen node name
        if result in self.choices:
            return [result]
        return []


# ---------------------------------------------------------------------------
# Example usage (callable directly)
# ---------------------------------------------------------------------------
async def _example():
    # Set up cache (in-memory Redis would require a running instance; we use a mock)
    # For demonstration we will just run without a real Redis.
    # Build a simple graph
    graph = Graph("demo")

    class PrintNode(Node):
        def __init__(self, name: str, text: str) -> None:
            super().__init__(name)
            self.text = text

        async def run(self, state: Dict[str, GraphNodeState]) -> None:
            print(f"[{self.name}] {self.text}")

    graph.add_node(PrintNode("start", "Hello"))
    graph.add_node(PrintNode("middle", "Middle step"))
    graph.add_node(PrintNode("end", "Finished"))
    graph.add_edge("start", "middle")
    graph.add_edge("middle", "end")

    # Create executor with a simple logging middleware
    async def log_middleware(node, state, next_handler):
        print(f"-> Entering node '{node.name}'")
        res = await next_handler()
        print(f"<- Exiting node '{node.name}'")
        return res

    executor = GraphExecutor(graph, middleware=[log_middleware])
    result_state = await executor.execute()
    snapshot = executor.get_snapshot()
    print("Snapshot:", snapshot)


# Only run the example when the module is executed directly
if __name__ == "__main__":
    asyncio.run(_example())