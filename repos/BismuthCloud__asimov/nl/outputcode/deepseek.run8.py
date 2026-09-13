import asyncio
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

try:
    import openai
except ImportError:
    openai = None

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    tracer = trace.get_tracer(__name__)
except ImportError:
    tracer = None

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None


# ---------------------------------------------------------------------------
# Graph Primitives
# ---------------------------------------------------------------------------

@dataclass
class Node:
    name: str
    func: Callable[..., Coroutine[Any, Any, Any]]
    dependencies: Set['Node'] = field(default_factory=set)

    def add_dependency(self, node: 'Node') -> None:
        self.dependencies.add(node)


@dataclass
class Edge:
    source: Node
    target: Node


@dataclass
class GraphState:
    node_results: Dict[str, Any] = field(default_factory=dict)
    node_statuses: Dict[str, str] = field(default_factory=dict)  # pending, running, completed, failed
    context: Dict[str, Any] = field(default_factory=dict)


class Graph:
    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []

    def add_node(self, node: Node) -> None:
        self.nodes[node.name] = node

    def add_edge(self, source: Node, target: Node) -> None:
        if source.name not in self.nodes or target.name not in self.nodes:
            raise ValueError("Both nodes must be added to the graph before creating an edge")
        self.edges.append(Edge(source, target))
        target.dependencies.add(source)

    def validate_acyclic(self) -> bool:
        visited: Set[Node] = set()
        stack: Set[Node] = set()

        def dfs(node: Node) -> bool:
            if node in stack:
                return False
            if node in visited:
                return True
            stack.add(node)
            for dep in node.dependencies:
                if not dfs(dep):
                    return False
            stack.remove(node)
            visited.add(node)
            return True

        return all(dfs(node) for node in self.nodes.values())

    def topological_sort(self) -> List[Node]:
        if not self.validate_acyclic():
            raise ValueError("Graph contains a cycle")
        visited: Set[Node] = set()
        temp: Set[Node] = set()
        order: List[Node] = []

        def visit(node: Node) -> None:
            if node in temp:
                raise ValueError("Cycle detected")
            if node not in visited:
                temp.add(node)
                for dep in node.dependencies:
                    visit(dep)
                temp.remove(node)
                visited.add(node)
                order.append(node)

        for node in self.nodes.values():
            visit(node)
        return order


class Middleware(ABC):
    @abstractmethod
    async def before_node_execution(self, node: Node, context: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    async def after_node_execution(
        self, node: Node, context: Dict[str, Any], result: Any, error: Optional[Exception] = None
    ) -> None:
        ...


class LoggingMiddleware(Middleware):
    async def before_node_execution(self, node: Node, context: Dict[str, Any]) -> None:
        print(f"Executing node: {node.name}")

    async def after_node_execution(
        self, node: Node, context: Dict[str, Any], result: Any, error: Optional[Exception] = None
    ) -> None:
        if error:
            print(f"Node {node.name} failed: {error}")
        else:
            print(f"Node {node.name} completed")


class GraphExecutor:
    def __init__(self, graph: Graph, middlewares: Optional[List[Middleware]] = None) -> None:
        self.graph = graph
        self.middlewares = middlewares or []
        self.state = GraphState()

    def snapshot_state(self) -> GraphState:
        return self.state

    def load_state(self, state: GraphState) -> None:
        self.state = state

    async def run(self) -> Dict[str, Any]:
        if not self.graph.validate_acyclic():
            raise ValueError("Graph contains a cycle – aborting execution")

        successors: Dict[str, List[str]] = {name: [] for name in self.graph.nodes}
        for edge in self.graph.edges:
            successors[edge.source.name].append(edge.target.name)

        dependents: Dict[str, Set[str]] = {
            name: set(dep.name for dep in node.dependencies) for name, node in self.graph.nodes.items()
        }

        ready: asyncio.Queue[str] = asyncio.Queue()
        for name, node in self.graph.nodes.items():
            if not node.dependencies:
                ready.put_nowait(name)

        async def execute_node(name: str) -> None:
            node = self.graph.nodes[name]
            for mw in self.middlewares:
                await mw.before_node_execution(node, self.state.context)
            try:
                result = await node.func(self.state.context)
                self.state.node_results[name] = result
                self.state.node_statuses[name] = "completed"
                for mw in self.middlewares:
                    await mw.after_node_execution(node, self.state.context, result, None)
            except Exception as e:
                self.state.node_statuses[name] = "failed"
                for mw in self.middlewares:
                    await mw.after_node_execution(node, self.state.context, None, e)
                raise
            else:
                for succ in successors[name]:
                    dependents[succ].discard(name)
                    if not dependents[succ]:
                        ready.put_nowait(succ)

        tasks: List[asyncio.Task] = []
        while not ready.empty() or any(not t.done() for t in tasks):
            try:
                next_node = ready.get_nowait()
            except asyncio.QueueEmpty:
                done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                tasks = [t for t in tasks if not t.done()]
                continue
            tasks.append(asyncio.create_task(execute_node(next_node)))

        await asyncio.gather(*tasks, return_exceptions=True)
        return self.state.node_results


# ---------------------------------------------------------------------------
# Inference Clients
# ---------------------------------------------------------------------------

@dataclass
class CompletionResponse:
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FunctionCallResponse:
    content: Optional[str] = None
    function_name: Optional[str] = None
    function_arguments: Optional[Dict[str, Any]] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class InferenceClient(ABC):
    @abstractmethod
    async def complete(self, messages: List[Dict[str, str]], **kwargs: Any) -> CompletionResponse:
        ...

    @abstractmethod
    async def stream_complete(self, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        ...

    @abstractmethod
    async def function_call(
        self, messages: List[Dict[str, str]], functions: List[Dict[str, Any]], **kwargs: Any
    ) -> FunctionCallResponse:
        ...

    @abstractmethod
    def supports_tools(self) -> bool:
        ...


class OpenAIInferenceClient(InferenceClient):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        **client_kwargs: Any,
    ) -> None:
        if openai is None:
            raise ImportError("The 'openai' package is not installed. Install it to use OpenAIInferenceClient.")
        self.client = openai.AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"), **client_kwargs)
        self.model = model

    async def complete(self, messages: List[Dict[str, str]], **kwargs: Any) -> CompletionResponse:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs,
        )
        choice = response.choices[0]
        usage = response.usage
        return CompletionResponse(
            content=choice.message.content or "",
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        )

    async def stream_complete(self, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    async def function_call(
        self, messages: List[Dict[str, str]], functions: List[Dict[str, Any]], **kwargs: Any
    ) -> FunctionCallResponse:
        tools = [{"type": "function", "function": func} for func in functions]
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice=kwargs.pop("tool_choice", "auto"),
            **kwargs,
        )
        choice = response.choices[0]
        usage = response.usage
        if choice.message.tool_calls:
            tool_call = choice.message.tool_calls[0]
            args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
            return FunctionCallResponse(
                content=choice.message.content,
                function_name=tool_call.function.name,
                function_arguments=args,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
        return FunctionCallResponse(
            content=choice.message.content,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        )

    def supports_tools(self) -> bool:
        return True


class AnthropicInferenceClient(InferenceClient):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-opus-20240229",
        **client_kwargs: Any,
    ) -> None:
        if anthropic is None:
            raise ImportError("The 'anthropic' package is not installed. Install it to use AnthropicInferenceClient.")
        self.client = anthropic.AsyncAnthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"), **client_kwargs)
        self.model = model

    async def complete(self, messages: List[Dict[str, str]], **kwargs: Any) -> CompletionResponse:
        system = None
        user_messages: List[Dict[str, str]] = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                user_messages.append(msg)
        max_tokens = kwargs.pop("max_tokens", 1024)
        response = await self.client.messages.create(
            model=self.model,
            system=system,
            messages=user_messages,
            max_tokens=max_tokens,
            **kwargs,
        )
        content = response.content[0].text if response.content else ""
        usage = response.usage
        return CompletionResponse(
            content=content,
            prompt_tokens=usage.input_tokens,
            completion_tokens=usage.output_tokens,
            total_tokens=usage.input_tokens + usage.output_tokens,
        )

    async def stream_complete(self, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        system = None
        user_messages: List[Dict[str, str]] = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                user_messages.append(msg)
        max_tokens = kwargs.pop("max_tokens", 1024)
        async with self.client.messages.stream(
            model=self.model,
            system=system,
            messages=user_messages,
            max_tokens=max_tokens,
            **kwargs,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def function_call(
        self, messages: List[Dict[str, str]], functions: List[Dict[str, Any]], **kwargs: Any
    ) -> FunctionCallResponse:
        system = None
        user_messages: List[Dict[str, str]] = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                user_messages.append(msg)
        tools = [
            {
                "name": f["name"],
                "description": f.get("description", ""),
                "input_schema": f.get("parameters", {}),
            }
            for f in functions
        ]
        max_tokens = kwargs.pop("max_tokens", 1024)
        response = await self.client.messages.create(
            model=self.model,
            system=system,
            messages=user_messages,
            tools=tools,
            max_tokens=max_tokens,
            **kwargs,
        )
        usage = response.usage
        if response.stop_reason == "tool_use":
            tool_use = next(block for block in response.content if block.type == "tool_use")
            return FunctionCallResponse(
                function_name=tool_use.name,
                function_arguments=tool_use.input,
                prompt_tokens=usage.input_tokens,
                completion_tokens=usage.output_tokens,
                total_tokens=usage.input_tokens + usage.output_tokens,
            )
        content = response.content[0].text if response.content else ""
        return FunctionCallResponse(
            content=content,
            prompt_tokens=usage.input_tokens,
            completion_tokens=usage.output_tokens,
            total_tokens=usage.input_tokens + usage.output_tokens,
        )

    def supports_tools(self) -> bool:
        return True


class InstrumentedInferenceClient(InferenceClient):
    def __init__(
        self,
        inner: InferenceClient,
        tracer_provider: Optional[Any] = None,
    ) -> None:
        self.inner = inner
        if tracer_provider:
            self.tracer = trace.get_tracer(__name__, tracer_provider=tracer_provider)
        else:
            self.tracer = tracer

    async def complete(self, messages: List[Dict[str, str]], **kwargs: Any) -> CompletionResponse:
        if not self.tracer:
            return await self.inner.complete(messages, **kwargs)
        with self.tracer.start_as_current_span("InferenceClient.complete") as span:
            span.set_attribute("provider", type(self.inner).__name__)
            result = await self.inner.complete(messages, **kwargs)
            span.set_attribute("prompt_tokens", result.prompt_tokens)
            span.set_attribute("completion_tokens", result.completion_tokens)
            span.set_status(Status(StatusCode.OK))
            return result

    async def stream_complete(self, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        if not self.tracer:
            async for token in self.inner.stream_complete(messages, **kwargs):
                yield token
            return
        with self.tracer.start_as_current_span("InferenceClient.stream_complete") as span:
            span.set_attribute("provider", type(self.inner).__name__)
            async for token in self.inner.stream_complete(messages, **kwargs):
                yield token
            span.set_status(Status(StatusCode.OK))

    async def function_call(
        self, messages: List[Dict[str, str]], functions: List[Dict[str, Any]], **kwargs: Any
    ) -> FunctionCallResponse:
        if not self.tracer:
            return await self.inner.function_call(messages, functions, **kwargs)
        with self.tracer.start_as_current_span("InferenceClient.function_call") as span:
            span.set_attribute("provider", type(self.inner).__name__)
            result = await self.inner.function_call(messages, functions, **kwargs)
            span.set_attribute("prompt_tokens", result.prompt_tokens)
            span.set_attribute("completion_tokens", result.completion_tokens)
            span.set_status(Status(StatusCode.OK))
            return result

    def supports_tools(self) -> bool:
        return self.inner.supports_tools()


class CachingInferenceClient(InferenceClient):
    def __init__(
        self,
        inner: InferenceClient,
        cache: "Cache",
        key_builder: Optional[Callable[..., str]] = None,
    ) -> None:
        self.inner = inner
        self.cache = cache
        self.key_builder = key_builder or self._default_key_builder

    @staticmethod
    def _default_key_builder(method: str, messages: List[Dict[str, str]], kwargs: Dict[str, Any]) -> str:
        data = json.dumps({"method": method, "messages": messages, "kwargs": kwargs}, sort_keys=True)
        return f"inference:{hash(data)}"

    async def complete(self, messages: List[Dict[str, str]], **kwargs: Any) -> CompletionResponse:
        key = self.key_builder("complete", messages, kwargs)
        cached = await self.cache.get(key)
        if cached is not None:
            return CompletionResponse(**cached)
        result = await self.inner.complete(messages, **kwargs)
        await self.cache.set(key, result.__dict__)
        return result

    async def stream_complete(self, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncIterator[str]:
        async for token in self.inner.stream_complete(messages, **kwargs):
            yield token

    async def function_call(
        self, messages: List[Dict[str, str]], functions: List[Dict[str, Any]], **kwargs: Any
    ) -> FunctionCallResponse:
        key = self.key_builder("function_call", messages, {**kwargs, "functions": functions})
        cached = await self.cache.get(key)
        if cached is not None:
            return FunctionCallResponse(**cached)
        result = await self.inner.function_call(messages, functions, **kwargs)
        await self.cache.set(key, result.__dict__)
        return result

    def supports_tools(self) -> bool:
        return self.inner.supports_tools()


# ---------------------------------------------------------------------------
# Caching System
# ---------------------------------------------------------------------------

class Cache(ABC):
    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    async def get_all(self, pattern: Optional[str] = None) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def clear(self, pattern: Optional[str] = None) -> int:
        ...

    @abstractmethod
    async def publish(self, channel: str, message: Any) -> None:
        ...

    @abstractmethod
    async def subscribe(self, channel: str, handler: Callable[[Any], Any]) -> None:
        ...


class RedisCache(Cache):
    def __init__(
        self,
        url: str = "redis://localhost:6379",
        prefix: str = "",
        suffix: str = "",
        **redis_kwargs: Any,
    ) -> None:
        if aioredis is None:
            raise ImportError("The 'redis' package is not installed. Install it to use RedisCache.")
        self.url = url
        self.prefix = prefix
        self.suffix = suffix
        self.redis_kwargs = redis_kwargs
        self.redis: Optional[aioredis.Redis] = None

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}{key}{self.suffix}"

    async def connect(self) -> None:
        self.redis = await aioredis.from_url(self.url, **self.redis_kwargs)

    async def disconnect(self) -> None:
        if self.redis:
            await self.redis.close()
            self.redis = None

    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(self._full_key(key))
        if value is not None:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        serialized = json.dumps(value)
        if ttl is not None:
            await self.redis.setex(self._full_key(key), ttl, serialized)
        else:
            await self.redis.set(self._full_key(key), serialized)

    async def delete(self, key: str) -> bool:
        return bool(await self.redis.delete(self._full_key(key)))

    async def exists(self, key: str) -> bool:
        return await self.redis.exists(self._full_key(key)) > 0

    async def get_all(self, pattern: Optional[str] = None) -> Dict[str, Any]:
        if pattern is None:
            pattern = "*"
        full_pattern = f"{self.prefix}{pattern}{self.suffix}"
        keys: List[str] = []
        async for key in self.redis.scan_iter(match=full_pattern):
            keys.append(key)
        if not keys:
            return {}
        values = await self.redis.mget(keys)
        result: Dict[str, Any] = {}
        for k, v in zip(keys, values):
            if v is not None:
                stripped = k
                if self.prefix and k.startswith(self.prefix):
                    stripped = k[len(self.prefix):]
                if self.suffix and stripped.endswith(self.suffix):
                    stripped = stripped[:-len(self.suffix)]
                result[stripped] = json.loads(v)
        return result

    async def clear(self, pattern: Optional[str] = None) -> int:
        if pattern is None:
            pattern = "*"
        full_pattern = f"{self.prefix}{pattern}{self.suffix}"
        count = 0
        async for key in self.redis.scan_iter(match=full_pattern):
            await self.redis.delete(key)
            count += 1
        return count

    async def publish(self, channel: str, message: Any) -> None:
        full_channel = f"{self.prefix}mailbox:{channel}{self.suffix}"
        await self.redis.publish(full_channel, json.dumps(message))

    async def subscribe(self, channel: str, handler: Callable[[Any], Any]) -> None:
        full_channel = f"{self.prefix}mailbox:{channel}{self.suffix}"
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(full_channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await handler(data)
        finally:
            await pubsub.unsubscribe(full_channel)
            await pubsub.close()


__all__ = [
    "Node",
    "Edge",
    "GraphState",
    "Graph",
    "Middleware",
    "LoggingMiddleware",
    "GraphExecutor",
    "CompletionResponse",
    "FunctionCallResponse",
    "InferenceClient",
    "OpenAIInferenceClient",
    "AnthropicInferenceClient",
    "InstrumentedInferenceClient",
    "CachingInferenceClient",
    "Cache",
    "RedisCache",
]