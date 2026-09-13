import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None

try:
    from opentelemetry import trace
    from opentelemetry.trace import Span, Status, StatusCode
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    trace = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graph Primitives
# ---------------------------------------------------------------------------

class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class GraphNode:
    id: str
    task: Callable
    dependencies: Set[str] = field(default_factory=set)
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None

    @property
    def is_ready(self) -> bool:
        return self.status == NodeStatus.PENDING and not self.dependencies

    def reset(self):
        self.status = NodeStatus.PENDING
        self.result = None
        self.error = None

class Graph:
    """Manages directed acyclic graph of tasks and executes them topologically."""
    def __init__(self, name: str = ""):
        self.name = name
        self.nodes: Dict[str, GraphNode] = {}

    def add_node(self, node_id: str, task: Callable, depends_on: Optional[Iterable[str]] = None):
        if node_id in self.nodes:
            raise ValueError(f"Node {node_id} already exists.")
        deps = set(depends_on) if depends_on else set()
        self.nodes[node_id] = GraphNode(id=node_id, task=task, dependencies=deps)
        for dep in deps:
            if dep not in self.nodes:
                raise ValueError(f"Dependency {dep} not found.")

    def add_edge(self, from_node: str, to_node: str):
        if from_node not in self.nodes or to_node not in self.nodes:
            raise ValueError("Both nodes must exist.")
        self.nodes[to_node].dependencies.add(from_node)

    def compile(self) -> List[str]:
        """Perform topological sort. Returns execution order."""
        in_degree = {nid: len(node.dependencies) for nid, node in self.nodes.items()}
        ready = deque([nid for nid, deg in in_degree.items() if deg == 0])
        order = []
        while ready:
            nid = ready.popleft()
            order.append(nid)
            # find dependents: nodes that list nid as dependency
            for other_nid, node in self.nodes.items():
                if nid in node.dependencies:
                    in_degree[other_nid] -= 1
                    if in_degree[other_nid] == 0:
                        ready.append(other_nid)
        if len(order) != len(self.nodes):
            raise ValueError("Graph contains a cycle.")
        return order

    async def execute(self, state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run each node in topological order, passing and updating state."""
        order = self.compile()
        ctx = state or {}
        for nid in order:
            node = self.nodes[nid]
            node.status = NodeStatus.RUNNING
            try:
                result = node.task(ctx)
                if asyncio.iscoroutine(result):
                    result = await result
                node.result = result
                node.status = NodeStatus.COMPLETED
                ctx[nid] = result
            except Exception as e:
                node.error = e
                node.status = NodeStatus.FAILED
                raise
        return ctx

    def snapshot(self) -> "GraphSnapshot":
        """Capture current state of all nodes."""
        return GraphSnapshot(
            graph_name=self.name,
            nodes={
                nid: NodeSnapshot(
                    id=nid,
                    status=node.status,
                    result=node.result,
                    error=str(node.error) if node.error else None,
                )
                for nid, node in self.nodes.items()
            },
        )

    def restore(self, snapshot: "GraphSnapshot"):
        """Restore node statuses from snapshot. Does not re-execute."""
        for nid, node_snap in snapshot.nodes.items():
            if nid in self.nodes:
                node = self.nodes[nid]
                node.status = node_snap.status
                node.result = node_snap.result
                node.error = Exception(node_snap.error) if node_snap.error else None

    def reset(self):
        for node in self.nodes.values():
            node.reset()


@dataclass
class NodeSnapshot:
    id: str
    status: NodeStatus
    result: Any = None
    error: Optional[str] = None

@dataclass
class GraphSnapshot:
    graph_name: str
    nodes: Dict[str, NodeSnapshot]

# ---------------------------------------------------------------------------
# LLM-Directed Graph Execution
# ---------------------------------------------------------------------------

class LLMDirectedGraph(Graph):
    """
    Graph where the next node to run is chosen by an LLM based on current state.
    Requires an inference client with function-calling capability.
    """
    def __init__(self, name: str, inference_client, decision_prompt: str):
        super().__init__(name)
        self.inference_client = inference_client
        self.decision_prompt = decision_prompt

    async def execute(self, state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ctx = state or {}
        available_nodes = set(self.nodes.keys())
        finished_nodes = set()

        while available_nodes - finished_nodes:
            # Ask LLM which node to run next
            node_choices = [
                {"name": nid} for nid in available_nodes - finished_nodes
            ]
            response = await self.inference_client.function_call(
                messages=[{"role": "system", "content": self.decision_prompt}],
                functions=[{
                    "name": "choose_next_node",
                    "description": "Select the next node to execute",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "node_id": {"type": "string", "enum": list(node_choices)}
                        },
                        "required": ["node_id"]
                    }
                }],
                function_call={"name": "choose_next_node"}
            )
            chosen_node = response["arguments"]["node_id"]
            if chosen_node not in self.nodes:
                raise ValueError(f"LLM chose unknown node {chosen_node}")

            node = self.nodes[chosen_node]
            node.status = NodeStatus.RUNNING
            try:
                result = node.task(ctx)
                if asyncio.iscoroutine(result):
                    result = await result
                node.result = result
                node.status = NodeStatus.COMPLETED
                ctx[chosen_node] = result
                finished_nodes.add(chosen_node)
            except Exception as e:
                node.error = e
                node.status = NodeStatus.FAILED
                raise
        return ctx

# ---------------------------------------------------------------------------
# Caching System
# ---------------------------------------------------------------------------

class Cache(ABC):
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
    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        ...

    @abstractmethod
    async def clear(self, pattern: str = "*") -> None:
        ...

    @abstractmethod
    async def publish(self, channel: str, message: Any) -> None:
        ...

    @abstractmethod
    async def subscribe(self, channel: str) -> AsyncIterator[Any]:
        ...


class RedisCache(Cache):
    """Redis-backed cache with JSON serialization, prefix/suffix namespacing, pub/sub mailboxes."""
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        prefix: str = "",
        suffix: str = "",
    ):
        if not REDIS_AVAILABLE:
            raise RuntimeError("redis-py is required for RedisCache")
        self.redis: aioredis.Redis
        self._redis_url = redis_url
        self._prefix = prefix
        self._suffix = suffix
        self._pubsub = None

    async def _connect(self):
        if not hasattr(self, "redis") or self.redis is None:
            self.redis = aioredis.from_url(self._redis_url, decode_responses=True)

    def _make_key(self, key: str) -> str:
        return f"{self._prefix}{key}{self._suffix}"

    def _unmake_key(self, full_key: str) -> str:
        if self._prefix and full_key.startswith(self._prefix):
            full_key = full_key[len(self._prefix):]
        if self._suffix and full_key.endswith(self._suffix):
            full_key = full_key[:-len(self._suffix)]
        return full_key

    async def get(self, key: str) -> Optional[Any]:
        await self._connect()
        value = await self.redis.get(self._make_key(key))
        if value is None:
            return None
        return json.loads(value)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        await self._connect()
        full_key = self._make_key(key)
        serialized = json.dumps(value)
        if ttl:
            await self.redis.setex(full_key, ttl, serialized)
        else:
            await self.redis.set(full_key, serialized)

    async def delete(self, key: str) -> None:
        await self._connect()
        await self.redis.delete(self._make_key(key))

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        await self._connect()
        full_pattern = self._make_key(pattern)
        keys = []
        async for k in self.redis.scan_iter(match=full_pattern):
            keys.append(k)
        result = {}
        if keys:
            values = await self.redis.mget(keys)
            for k, v in zip(keys, values):
                if v is not None:
                    result[self._unmake_key(k)] = json.loads(v)
        return result

    async def clear(self, pattern: str = "*") -> None:
        await self._connect()
        full_pattern = self._make_key(pattern)
        keys = []
        async for k in self.redis.scan_iter(match=full_pattern):
            keys.append(k)
        if keys:
            await self.redis.delete(*keys)

    async def publish(self, channel: str, message: Any) -> None:
        await self._connect()
        serialized = json.dumps(message)
        await self.redis.publish(channel, serialized)

    async def subscribe(self, channel: str) -> AsyncIterator[Any]:
        await self._connect()
        if self._pubsub is None:
            self._pubsub = self.redis.pubsub()
        await self._pubsub.subscribe(channel)
        async for msg in self._pubsub.listen():
            if msg["type"] == "message":
                yield json.loads(msg["data"])


class InMemoryCache(Cache):
    """Simple in-memory cache for testing; supports same interface except pub/sub is no-op."""
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}

    async def get(self, key: str) -> Optional[Any]:
        return self._data.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self._data[key] = value
        if ttl:
            # simplistic TTL: schedule deletion
            asyncio.create_task(self._expire(key, ttl))

    async def _expire(self, key: str, delay: int):
        await asyncio.sleep(delay)
        self._data.pop(key, None)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        import fnmatch
        return {k: v for k, v in self._data.items() if fnmatch.fnmatch(k, pattern)}

    async def clear(self, pattern: str = "*") -> None:
        import fnmatch
        keys_to_del = [k for k in self._data if fnmatch.fnmatch(k, pattern)]
        for k in keys_to_del:
            del self._data[k]

    async def publish(self, channel: str, message: Any) -> None:
        if channel in self._subscribers:
            for q in self._subscribers[channel]:
                await q.put(message)

    async def subscribe(self, channel: str) -> AsyncIterator[Any]:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(channel, []).append(q)
        try:
            while True:
                yield await q.get()
        finally:
            self._subscribers[channel].remove(q)

# ---------------------------------------------------------------------------
# Inference Clients
# ---------------------------------------------------------------------------

class TokenUsage:
    def __init__(self, prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens

class InferenceResult:
    def __init__(self, text: str, usage: Optional[TokenUsage] = None, raw_response: Any = None):
        self.text = text
        self.usage = usage
        self.raw_response = raw_response

class FunctionCallResult:
    def __init__(self, name: str, arguments: Dict[str, Any]):
        self.name = name
        self.arguments = arguments

class InferenceClient(ABC):
    """Abstract base for LLM providers with streaming, function calling, token tracking."""
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        functions: Optional[List[Dict]] = None,
        function_call: Optional[Union[str, Dict]] = None,
        **kwargs,
    ) -> InferenceResult:
        ...

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> AsyncIterator[str]:
        ...

    @abstractmethod
    async def function_call(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict],
        function_call: Union[str, Dict] = "auto",
        **kwargs,
    ) -> FunctionCallResult:
        ...


class OpenAIClient(InferenceClient):
    def __init__(self, api_key: str, model: str = "gpt-4", organization: Optional[str] = None):
        try:
            import openai
            self.openai = openai
        except ImportError:
            raise RuntimeError("openai package required for OpenAIClient")
        self.api_key = api_key
        self.model = model
        self.organization = organization
        self.client = openai.AsyncOpenAI(api_key=api_key, organization=organization)

    async def generate(self, messages, functions=None, function_call=None, **kwargs):
        params = {
            "model": self.model,
            "messages": messages,
            **kwargs,
        }
        if functions:
            params["functions"] = functions
        if function_call:
            params["function_call"] = function_call
        response = await self.client.chat.completions.create(**params)
        choice = response.choices[0]
        content = choice.message.content or ""
        usage = TokenUsage(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )
        return InferenceResult(text=content, usage=usage, raw_response=response)

    async def generate_stream(self, messages, **kwargs):
        params = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            **kwargs,
        }
        stream = await self.client.chat.completions.create(**params)
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def function_call(self, messages, functions, function_call="auto", **kwargs):
        response = await self.generate(
            messages=messages,
            functions=functions,
            function_call=function_call,
            **kwargs,
        )
        choice = response.raw_response.choices[0]
        if choice.message.function_call:
            fc = choice.message.function_call
            return FunctionCallResult(
                name=fc.name,
                arguments=json.loads(fc.arguments),
            )
        else:
            raise RuntimeError("No function call returned")


class AnthropicClient(InferenceClient):
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        try:
            import anthropic
            self.anthropic = anthropic
        except ImportError:
            raise RuntimeError("anthropic package required")
        self.api_key = api_key
        self.model = model
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate(self, messages, functions=None, function_call=None, **kwargs):
        # Convert to Anthropic format: system message separate, user/assistant alternating.
        system = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system += m["content"] + "\n"
            else:
                chat_messages.append(m)
        if not chat_messages:
            raise ValueError("At least one user/assistant message required")
        resp = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system.strip() or None,
            messages=chat_messages,
            **kwargs,
        )
        content_blocks = resp.content
        text = "".join(block.text for block in content_blocks if block.type == "text")
        # Approximate tokens (Anthropic returns usage in response headers)
        usage = TokenUsage(
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            total_tokens=resp.usage.input_tokens + resp.usage.output_tokens,
        )
        return InferenceResult(text=text, usage=usage, raw_response=resp)

    async def generate_stream(self, messages, **kwargs):
        # Not fully implemented; would require message streaming.
        raise NotImplementedError("Streaming not implemented for Anthropic")

    async def function_call(self, messages, functions, function_call="auto", **kwargs):
        # Anthropic doesn't have native function calling; fallback to text.
        raise NotImplementedError("Anthropic function calling not implemented")


class MockInferenceClient(InferenceClient):
    """Testing double that returns predefined responses."""
    def __init__(self, fixed_response: str = "mock response"):
        self.fixed_response = fixed_response

    async def generate(self, messages, functions=None, function_call=None, **kwargs):
        return InferenceResult(text=self.fixed_response, usage=TokenUsage(0, 0, 0))

    async def generate_stream(self, messages, **kwargs):
        async def _stream():
            for word in self.fixed_response.split():
                yield word + " "
                await asyncio.sleep(0.01)
        return _stream()

    async def function_call(self, messages, functions, function_call="auto", **kwargs):
        return FunctionCallResult(name="mock_fn", arguments={"key": "value"})


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class InferenceMiddleware:
    """Base class for middleware that wraps around inference calls."""
    def __init__(self, client: InferenceClient):
        self.client = client

    async def generate(self, messages, functions=None, function_call=None, **kwargs):
        return await self.client.generate(messages, functions, function_call, **kwargs)

    async def generate_stream(self, messages, **kwargs):
        return self.client.generate_stream(messages, **kwargs)

    async def function_call(self, messages, functions, function_call="auto", **kwargs):
        return await self.client.function_call(messages, functions, function_call, **kwargs)


class PromptCachingMiddleware(InferenceMiddleware):
    """Uses cache to avoid repeat API calls for identical messages."""
    def __init__(self, client: InferenceClient, cache: Cache, ttl: int = 3600):
        super().__init__(client)
        self.cache = cache
        self.ttl = ttl

    @staticmethod
    def _cache_key(messages, functions=None, function_call=None, **kwargs) -> str:
        data = {
            "messages": messages,
            "functions": functions,
            "function_call": function_call,
            "kwargs": kwargs,
        }
        return "prompt_cache:" + json.dumps(data, sort_keys=True)

    async def generate(self, messages, functions=None, function_call=None, **kwargs):
        key = self._cache_key(messages, functions, function_call, **kwargs)
        cached = await self.cache.get(key)
        if cached is not None:
            return InferenceResult(text=cached["text"], usage=TokenUsage(0, 0, 0))
        result = await super().generate(messages, functions, function_call, **kwargs)
        await self.cache.set(key, {"text": result.text}, ttl=self.ttl)
        return result

    async def function_call(self, messages, functions, function_call="auto", **kwargs):
        # caching for function calls could be done similarly
        key = self._cache_key(messages, functions, function_call, **kwargs)
        cached = await self.cache.get(key)
        if cached is not None:
            return FunctionCallResult(**cached["result"])
        result = await super().function_call(messages, functions, function_call, **kwargs)
        await self.cache.set(key, {"result": {"name": result.name, "arguments": result.arguments}}, ttl=self.ttl)
        return result

    async def generate_stream(self, messages, **kwargs):
        # Streaming not cached normally; pass through.
        return await self.client.generate_stream(messages, **kwargs)


class TelemetryMiddleware(InferenceMiddleware):
    """Adds OpenTelemetry spans around inference calls."""
    def __init__(self, client: InferenceClient):
        super().__init__(client)
        if not OPENTELEMETRY_AVAILABLE:
            raise RuntimeError("opentelemetry not installed")
        self.tracer = trace.get_tracer(__name__)

    async def generate(self, messages, functions=None, function_call=None, **kwargs):
        with self.tracer.start_as_current_span("inference.generate") as span:
            span.set_attribute("model", getattr(self.client, "model", "unknown"))
            result = await super().generate(messages, functions, function_call, **kwargs)
            if result.usage:
                span.set_attribute("prompt_tokens", result.usage.prompt_tokens)
                span.set_attribute("completion_tokens", result.usage.completion_tokens)
            return result

    async def generate_stream(self, messages, **kwargs):
        with self.tracer.start_as_current_span("inference.generate_stream") as span:
            span.set_attribute("model", getattr(self.client, "model", "unknown"))
            async for chunk in self.client.generate_stream(messages, **kwargs):
                yield chunk

    async def function_call(self, messages, functions, function_call="auto", **kwargs):
        with self.tracer.start_as_current_span("inference.function_call") as span:
            span.set_attribute("model", getattr(self.client, "model", "unknown"))
            return await super().function_call(messages, functions, function_call, **kwargs)


# ---------------------------------------------------------------------------
# OpenTelemetry Integration for Graph Execution
# ---------------------------------------------------------------------------

def instrument_graph(graph: Graph):
    """Decorate the graph's execute method with OpenTelemetry spans."""
    if not OPENTELEMETRY_AVAILABLE:
        return graph
    original_execute = graph.execute
    async def traced_execute(state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("graph.execute", attributes={"graph.name": graph.name}) as span:
            try:
                result = await original_execute(state)
                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
    graph.execute = traced_execute
    return graph

# ---------------------------------------------------------------------------
# Example usage (optional, not executed if imported)
# ---------------------------------------------------------------------------
async def _demo():
    # Create a simple graph
    graph = Graph("my_agent")
    def step1(ctx):
        return "hello"
    def step2(ctx):
        return ctx["step1"] + " world"
    graph.add_node("step1", step1)
    graph.add_node("step2", step2, depends_on=["step1"])
    result = await graph.execute()
    print(result)  # {'step1': 'hello', 'step2': 'hello world'}

    # Snapshot
    snap = graph.snapshot()
    print(snap)

    # Cache example
    cache = InMemoryCache()
    await cache.set("greeting", "hi")
    print(await cache.get("greeting"))

    # Inference with mock
    client = MockInferenceClient("AI response")
    print(await client.generate([{"role":"user","content":"hello"}]))

if __name__ == "__main__":
    asyncio.run(_demo())