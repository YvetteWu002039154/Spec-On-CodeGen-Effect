import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Union

# External imports (assumed installed)
try:
    from opentelemetry import trace
    from opentelemetry.trace import SpanKind, Status, StatusCode
except ImportError:
    trace = None

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

# --------------------- Telemetry Integration ---------------------
class Telemetry:
    """Simple OpenTelemetry wrapper."""
    @staticmethod
    def get_tracer(name: str):
        if trace is not None:
            return trace.get_tracer(name)
        return None

    @staticmethod
    def traced(name: str):
        """Decorator to wrap a function with a span."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                tracer = Telemetry.get_tracer("ai_agent_framework")
                if tracer:
                    with tracer.start_as_current_span(name) as span:
                        try:
                            result = await func(*args, **kwargs)
                            span.set_status(Status(StatusCode.OK))
                            return result
                        except Exception as e:
                            span.set_status(Status(StatusCode.ERROR, str(e)))
                            raise
                else:
                    return await func(*args, **kwargs)
            return wrapper
        return decorator


# --------------------- Cache System ---------------------
class AsyncCache(ABC):
    """Abstract cache interface with async operations, namespacing, and pub/sub mailboxes."""

    def __init__(self, prefix: str = "", suffix: str = ""):
        self.prefix = prefix
        self.suffix = suffix

    def _apply_namespace(self, key: str) -> str:
        if self.prefix:
            key = f"{self.prefix}:{key}"
        if self.suffix:
            key = f"{key}:{self.suffix}"
        return key

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

    # Mailbox (pub/sub) interface
    @abstractmethod
    async def publish(self, channel: str, message: Any) -> None:
        ...

    @abstractmethod
    async def subscribe(self, channel: str, callback: Callable[[Any], Awaitable[None]]) -> None:
        ...

    @abstractmethod
    async def unsubscribe(self, channel: str) -> None:
        ...


class RedisCache(AsyncCache):
    """Redis implementation of AsyncCache with JSON serialization and mailbox support."""

    def __init__(self, redis_client: "aioredis.Redis", prefix: str = "", suffix: str = ""):
        super().__init__(prefix, suffix)
        self.redis = redis_client
        self._pubsub: Optional[aioredis.client.PubSub] = None
        self._sub_tasks: Dict[str, asyncio.Task] = {}

    async def get(self, key: str) -> Optional[Any]:
        ns_key = self._apply_namespace(key)
        raw = await self.redis.get(ns_key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ns_key = self._apply_namespace(key)
        serialized = json.dumps(value, default=str)
        if ttl:
            await self.redis.setex(ns_key, ttl, serialized)
        else:
            await self.redis.set(ns_key, serialized)

    async def delete(self, key: str) -> None:
        ns_key = self._apply_namespace(key)
        await self.redis.delete(ns_key)

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        ns_pattern = self._apply_namespace(pattern)
        keys = []
        async for key in self.redis.scan_iter(match=ns_pattern):
            keys.append(key)
        if not keys:
            return {}
        values = await self.redis.mget(keys)
        result = {}
        for k, v in zip(keys, values):
            if v is not None:
                result[k.decode() if isinstance(k, bytes) else k] = json.loads(v)
        return result

    async def clear(self, pattern: str = "*") -> None:
        ns_pattern = self._apply_namespace(pattern)
        keys = []
        async for key in self.redis.scan_iter(match=ns_pattern):
            keys.append(key)
        if keys:
            await self.redis.delete(*keys)

    async def publish(self, channel: str, message: Any) -> None:
        ns_channel = self._apply_namespace(channel)
        serialized = json.dumps(message, default=str)
        await self.redis.publish(ns_channel, serialized)

    async def subscribe(self, channel: str, callback: Callable[[Any], Awaitable[None]]) -> None:
        ns_channel = self._apply_namespace(channel)
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(ns_channel)
        self._pubsub = pubsub
        task = asyncio.create_task(self._listen(pubsub, callback))
        self._sub_tasks[channel] = task

    async def _listen(self, pubsub, callback):
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await callback(data)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe()

    async def unsubscribe(self, channel: str) -> None:
        ns_channel = self._apply_namespace(channel)
        task = self._sub_tasks.pop(channel, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        # pubsub handles unsubscription
        if self._pubsub:
            await self._pubsub.unsubscribe(ns_channel)


# --------------------- Inference Clients ---------------------
@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]


@dataclass
class ChatMessage:
    role: str  # "system", "user", "assistant"
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class StreamingResponse:
    """Async iterator for streaming completions."""
    def __init__(self, async_iter):
        self._iter = async_iter

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self._iter.__anext__()


class InferenceClient(ABC):
    """Abstract base for LLM inference clients with streaming, tool calling, and token tracking."""

    def __init__(self, cache: Optional[AsyncCache] = None):
        self.cache = cache
        self._token_usage = TokenUsage()

    @property
    def token_usage(self) -> TokenUsage:
        return self._token_usage

    def reset_token_usage(self) -> None:
        self._token_usage = TokenUsage()

    @abstractmethod
    async def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> ChatMessage:
        """Non-streaming completion."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> StreamingResponse:
        """Streaming completion."""
        ...

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """Return token count for a given text."""
        ...

    def _cache_key(self, messages: List[ChatMessage], **kwargs) -> Optional[str]:
        if self.cache is None:
            return None
        # Simplified deterministic key
        key_dict = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "kwargs": kwargs,
        }
        raw = json.dumps(key_dict, sort_keys=True)
        return f"llm:cache:{hash(raw)}"

    async def _cached_or_generate(
        self, messages: List[ChatMessage], generate_fn: Callable[..., Awaitable[ChatMessage]], **kwargs
    ) -> ChatMessage:
        key = self._cache_key(messages, **kwargs)
        if key and self.cache:
            cached = await self.cache.get(key)
            if cached is not None:
                return ChatMessage(**cached)
        result = await generate_fn()
        if key and self.cache:
            await self.cache.set(key, result.__dict__, ttl=3600)
        return result


class OpenAIInferenceClient(InferenceClient):
    """OpenAI API client with streaming, tool calls, and token tracking."""

    def __init__(self, api_key: str, model: str = "gpt-4", cache: Optional[AsyncCache] = None):
        super().__init__(cache)
        self.client = AsyncOpenAI(api_key=api_key) if AsyncOpenAI else None
        self.model = model

    async def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> ChatMessage:
        @Telemetry.traced("OpenAI.generate")
        async def do_generate():
            msgs = [{"role": m.role, "content": m.content} for m in messages]
            params = {"model": self.model, "messages": msgs}
            if tools:
                params["tools"] = tools
            response = await self.client.chat.completions.create(**params)
            choice = response.choices[0]
            msg = ChatMessage(role="assistant", content=choice.message.content)
            if choice.message.tool_calls:
                msg.tool_calls = [
                    ToolCall(name=tc.function.name, arguments=json.loads(tc.function.arguments))
                    for tc in choice.message.tool_calls
                ]
            usage = response.usage
            if usage:
                self._token_usage += TokenUsage(
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                )
            return msg

        if self.cache:
            return await self._cached_or_generate(messages, do_generate, model=self.model, tools=tools, **kwargs)
        return await do_generate()

    async def stream(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> StreamingResponse:
        @Telemetry.traced("OpenAI.stream")
        async def stream_inner():
            msgs = [{"role": m.role, "content": m.content} for m in messages]
            params = {"model": self.model, "messages": msgs, "stream": True}
            if tools:
                params["tools"] = tools
            stream = await self.client.chat.completions.create(**params)
            async def iter_response():
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            return StreamingResponse(iter_response())

        return await stream_inner()

    async def count_tokens(self, text: str) -> int:
        # Approximate: 1 token ~ 4 characters for GPT models
        return len(text) // 4


class AnthropicInferenceClient(InferenceClient):
    """Anthropic Claude client (simplified; requires anthropic package)."""

    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229", cache: Optional[AsyncCache] = None):
        super().__init__(cache)
        self.client = AsyncAnthropic(api_key=api_key) if AsyncAnthropic else None
        self.model = model

    async def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> ChatMessage:
        @Telemetry.traced("Anthropic.generate")
        async def do_generate():
            # Anthropic requires system message extracted
            system = ""
            msg_list = []
            for m in messages:
                if m.role == "system":
                    system = m.content or ""
                else:
                    msg_list.append({"role": m.role, "content": m.content})
            params = {
                "model": self.model,
                "max_tokens": 1024,
                "system": system,
                "messages": msg_list,
            }
            if tools:
                params["tools"] = tools
            response = await self.client.messages.create(**params)
            content = response.content[0].text if response.content else ""
            msg = ChatMessage(role="assistant", content=content)
            # Token usage tracking (Anthropic provides input/output tokens)
            usage = response.usage
            if usage:
                self._token_usage += TokenUsage(
                    prompt_tokens=usage.input_tokens,
                    completion_tokens=usage.output_tokens,
                    total_tokens=usage.input_tokens + usage.output_tokens,
                )
            return msg

        if self.cache:
            return await self._cached_or_generate(messages, do_generate, model=self.model, tools=tools, **kwargs)
        return await do_generate()

    async def stream(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> StreamingResponse:
        @Telemetry.traced("Anthropic.stream")
        async def stream_inner():
            system = ""
            msg_list = []
            for m in messages:
                if m.role == "system":
                    system = m.content or ""
                else:
                    msg_list.append({"role": m.role, "content": m.content})
            params = {
                "model": self.model,
                "max_tokens": 1024,
                "system": system,
                "messages": msg_list,
                "stream": True,
            }
            if tools:
                params["tools"] = tools
            stream = await self.client.messages.create(**params)
            async def iter_response():
                async for event in stream:
                    if event.type == "content_block_delta" and event.delta.text:
                        yield event.delta.text
            return StreamingResponse(iter_response())

        return await stream_inner()

    async def count_tokens(self, text: str) -> int:
        # Rough estimate
        return len(text) // 4


# --------------------- Graph Primitives ---------------------
class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class GraphNode:
    name: str
    task: Callable[["GraphContext"], Awaitable[Any]]
    dependencies: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    output: Any = None


class GraphContext:
    """Holds shared state during graph execution."""

    def __init__(self, initial_state: Dict[str, Any] = None):
        self.state: Dict[str, Any] = initial_state or {}
        self.results: Dict[str, Any] = {}

    def snapshot(self) -> Dict[str, Any]:
        """Return a snapshot of the current state."""
        return json.loads(json.dumps(self.state, default=str))

    def restore(self, snapshot: Dict[str, Any]) -> None:
        """Restore state from a snapshot."""
        self.state = snapshot


class Graph:
    """Directed Acyclic Graph of tasks."""

    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}

    def add_node(self, node: GraphNode) -> None:
        if node.name in self.nodes:
            raise ValueError(f"Node '{node.name}' already exists")
        self.nodes[node.name] = node

    def get_node(self, name: str) -> GraphNode:
        return self.nodes[name]

    def get_execution_order(self) -> List[str]:
        """Topological sort to determine execution order."""
        in_degree = {name: 0 for name in self.nodes}
        for node in self.nodes.values():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    raise ValueError(f"Dependency '{dep}' not found for node '{node.name}'")
                in_degree[node.name] += 1

        queue = [name for name, deg in in_degree.items() if deg == 0]
        order = []
        while queue:
            name = queue.pop(0)
            order.append(name)
            for node in self.nodes.values():
                if name in node.dependencies:
                    in_degree[node.name] -= 1
                    if in_degree[node.name] == 0:
                        queue.append(node.name)
        if len(order) != len(self.nodes):
            raise ValueError("Graph contains cycles")
        return order


class GraphExecutor(ABC):
    """Base executor that walks the graph with optional middleware."""

    def __init__(self, graph: Graph, middleware: Optional[List["Middleware"]] = None):
        self.graph = graph
        self.middleware = middleware or []
        self.tracer = Telemetry.get_tracer("graph_executor")

    @abstractmethod
    async def execute(self, context: GraphContext) -> Dict[str, Any]:
        ...

    async def _execute_node(self, node: GraphNode, context: GraphContext):
        node.status = NodeStatus.RUNNING
        for mw in self.middleware:
            await mw.before_execution(node, context)
        try:
            with self.tracer.start_as_current_span(node.name) as span:
                span.set_attribute("node", node.name)
                result = await node.task(context)
                node.output = result
                context.results[node.name] = result
                node.status = NodeStatus.COMPLETED
                span.set_status(Status(StatusCode.OK))
        except Exception as e:
            node.status = NodeStatus.FAILED
            if self.tracer:
                span = trace.get_current_span()
                span.set_status(Status(StatusCode.ERROR, str(e)))
            for mw in self.middleware:
                await mw.on_error(node, context, e)
            raise
        finally:
            for mw in self.middleware:
                await mw.after_execution(node, context)


class DefaultGraphExecutor(GraphExecutor):
    """Execute nodes in topological order."""

    async def execute(self, context: GraphContext) -> Dict[str, Any]:
        order = self.graph.get_execution_order()
        for name in order:
            node = self.graph.get_node(name)
            await self._execute_node(node, context)
        return context.results


class LLMDirectedExecutor(GraphExecutor):
    """
    LLM-driven execution: uses an inference client to decide the next node
    dynamically based on current context and available nodes.
    """

    def __init__(
        self,
        graph: Graph,
        llm_client: InferenceClient,
        middleware: Optional[List["Middleware"]] = None,
    ):
        super().__init__(graph, middleware)
        self.llm = llm_client

    async def execute(self, context: GraphContext) -> Dict[str, Any]:
        available = set(self.graph.nodes.keys())
        completed = set()
        failed = set()

        while available:
            # Ask LLM which node to execute next
            next_node = await self._choose_next_node(context, list(available), completed, failed)
            if next_node is None:
                break  # LLM may decide to stop
            if next_node not in available:
                raise ValueError(f"LLM selected non-existent node: {next_node}")
            node = self.graph.get_node(next_node)
            try:
                await self._execute_node(node, context)
                completed.add(next_node)
                available.remove(next_node)
            except Exception:
                failed.add(next_node)
                available.remove(next_node)

        return context.results

    async def _choose_next_node(
        self,
        context: GraphContext,
        available: List[str],
        completed: Set[str],
        failed: Set[str],
    ) -> Optional[str]:
        # Build a prompt for the LLM to choose the next logical step
        prompt = f"""
Available nodes: {available}
Completed: {completed}
Failed: {failed}
Context state: {json.dumps(context.snapshot())}
Which node should be executed next? Respond only with the node name, or 'STOP'.
"""
        msgs = [ChatMessage(role="user", content=prompt)]
        response = await self.llm.generate(msgs)
        choice = (response.content or "").strip().upper()
        if choice == "STOP":
            return None
        return choice.lower()


# --------------------- Middleware ---------------------
class Middleware(ABC):
    """Hooks for graph execution."""

    @abstractmethod
    async def before_execution(self, node: GraphNode, context: GraphContext) -> None:
        ...

    @abstractmethod
    async def after_execution(self, node: GraphNode, context: GraphContext) -> None:
        ...

    @abstractmethod
    async def on_error(self, node: GraphNode, context: GraphContext, error: Exception) -> None:
        ...


class LoggingMiddleware(Middleware):
    """Simple logging middleware."""

    async def before_execution(self, node: GraphNode, context: GraphContext) -> None:
        print(f"[LOG] Starting node: {node.name}")

    async def after_execution(self, node: GraphNode, context: GraphContext) -> None:
        print(f"[LOG] Completed node: {node.name}, status: {node.status.value}")

    async def on_error(self, node: GraphNode, context: GraphContext, error: Exception) -> None:
        print(f"[LOG] Error in node: {node.name}: {error}")


# --------------------- State Snapshotting Manager ---------------------
class StateManager:
    """Manages state snapshots and restoration for a graph context."""

    def __init__(self, cache: AsyncCache):
        self.cache = cache

    async def save_snapshot(self, snapshot_id: str, context: GraphContext) -> None:
        snapshot = context.snapshot()
        await self.cache.set(f"snapshot:{snapshot_id}", snapshot)

    async def load_snapshot(self, snapshot_id: str, context: GraphContext) -> bool:
        snapshot = await self.cache.get(f"snapshot:{snapshot_id}")
        if snapshot is None:
            return False
        context.restore(snapshot)
        return True

    async def delete_snapshot(self, snapshot_id: str) -> None:
        await self.cache.delete(f"snapshot:{snapshot_id}")


# --------------------- Helper Factory ---------------------
def create_inference_client(provider: str, **kwargs) -> InferenceClient:
    """Factory for creating inference clients."""
    provider = provider.lower()
    if provider == "openai":
        return OpenAIInferenceClient(**kwargs)
    elif provider == "anthropic":
        return AnthropicInferenceClient(**kwargs)
    else:
        raise ValueError(f"Unsupported provider: {provider}")