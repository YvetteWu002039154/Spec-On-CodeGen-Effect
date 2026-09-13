import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

try:
    from opentelemetry import trace
    tracer = trace.get_tracer(__name__)
except ImportError:
    class DummySpan:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def set_attribute(self, *args): pass
    class DummyTracer:
        def start_as_current_span(self, *args, **kwargs): return DummySpan()
    tracer = DummyTracer()


class Cache(ABC):
    @abstractmethod
    async def get(self, key: str) -> Any:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any) -> None:
        pass

    @abstractmethod
    async def get_all(self, pattern: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def clear(self, pattern: str) -> None:
        pass

    @abstractmethod
    async def publish(self, mailbox: str, message: Any) -> None:
        pass

    @abstractmethod
    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        pass


class RedisCache(Cache):
    def __init__(self, redis_url: str, prefix: str = "", suffix: str = ""):
        if redis is None:
            raise ImportError("redis package is required for RedisCache")
        self.redis = redis.from_url(redis_url)
        self.prefix = prefix
        self.suffix = suffix

    def _format_key(self, key: str) -> str:
        return f"{self.prefix}{key}{self.suffix}"

    async def get(self, key: str) -> Any:
        val = await self.redis.get(self._format_key(key))
        return json.loads(val) if val else None

    async def set(self, key: str, value: Any) -> None:
        await self.redis.set(self._format_key(key), json.dumps(value))

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        keys = await self.redis.keys(self._format_key(pattern))
        if not keys:
            return {}
        values = await self.redis.mget(keys)
        result = {}
        for k, v in zip(keys, values):
            decoded_key = k.decode('utf-8') if isinstance(k, bytes) else k
            result[decoded_key] = json.loads(v) if v else None
        return result

    async def clear(self, pattern: str = "*") -> None:
        keys = await self.redis.keys(self._format_key(pattern))
        if keys:
            await self.redis.delete(*keys)

    async def publish(self, mailbox: str, message: Any) -> None:
        await self.redis.publish(self._format_key(mailbox), json.dumps(message))

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self._format_key(mailbox))
        async for message in pubsub.listen():
            if message['type'] == 'message':
                yield json.loads(message['data'])


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    cached: bool = False


class InferenceClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None, use_cache: bool = True) -> LLMResponse:
        pass

    @abstractmethod
    async def generate_stream(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None) -> AsyncGenerator[str, None]:
        pass


class OpenAIClient(InferenceClient):
    def __init__(self, cache: Optional[Cache] = None):
        self.cache = cache

    async def generate(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None, use_cache: bool = True) -> LLMResponse:
        with tracer.start_as_current_span("OpenAI.generate") as span:
            span.set_attribute("prompt", prompt)
            
            cache_key = f"llm_cache:openai:{prompt}"
            if use_cache and self.cache:
                cached = await self.cache.get(cache_key)
                if cached:
                    span.set_attribute("cached", True)
                    usage_data = cached.get("usage", {})
                    tool_calls_data = cached.get("tool_calls", [])
                    return LLMResponse(
                        content=cached["content"],
                        tool_calls=[ToolCall(**tc) for tc in tool_calls_data],
                        usage=TokenUsage(**usage_data),
                        cached=True
                    )

            tool_calls = []
            if tools:
                tool_calls.append(ToolCall(id="call_1", name=tools[0]["name"], arguments={"arg": "value"}))

            response = LLMResponse(
                content=f"OpenAI response to: {prompt}",
                tool_calls=tool_calls,
                usage=TokenUsage(prompt_tokens=15, completion_tokens=20, total_tokens=35)
            )

            if use_cache and self.cache:
                await self.cache.set(cache_key, {
                    "content": response.content,
                    "tool_calls": [tc.__dict__ for tc in response.tool_calls],
                    "usage": response.usage.__dict__
                })

            return response

    async def generate_stream(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None) -> AsyncGenerator[str, None]:
        with tracer.start_as_current_span("OpenAI.generate_stream"):
            words = f"Streaming OpenAI response to: {prompt}".split()
            for word in words:
                yield word + " "
                await asyncio.sleep(0.01)


class AnthropicClient(InferenceClient):
    def __init__(self, cache: Optional[Cache] = None):
        self.cache = cache

    async def generate(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None, use_cache: bool = True) -> LLMResponse:
        with tracer.start_as_current_span("Anthropic.generate") as span:
            span.set_attribute("prompt", prompt)
            
            cache_key = f"llm_cache:anthropic:{prompt}"
            if use_cache and self.cache:
                cached = await self.cache.get(cache_key)
                if cached:
                    span.set_attribute("cached", True)
                    usage_data = cached.get("usage", {})
                    tool_calls_data = cached.get("tool_calls", [])
                    return LLMResponse(
                        content=cached["content"],
                        tool_calls=[ToolCall(**tc) for tc in tool_calls_data],
                        usage=TokenUsage(**usage_data),
                        cached=True
                    )

            response = LLMResponse(
                content=f"Anthropic response to: {prompt}",
                usage=TokenUsage(prompt_tokens=12, completion_tokens=18, total_tokens=30)
            )

            if use_cache and self.cache:
                await self.cache.set(cache_key, {
                    "content": response.content,
                    "tool_calls": [tc.__dict__ for tc in response.tool_calls],
                    "usage": response.usage.__dict__
                })

            return response

    async def generate_stream(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None) -> AsyncGenerator[str, None]:
        with tracer.start_as_current_span("Anthropic.generate_stream"):
            words = f"Streaming Anthropic response to: {prompt}".split()
            for word in words:
                yield word + " "
                await asyncio.sleep(0.01)


@dataclass
class Snapshot:
    state: Dict[str, Any]
    node: str
    timestamp: float


class Middleware(ABC):
    @abstractmethod
    async def __call__(self, state: Dict[str, Any], next_call: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]) -> Dict[str, Any]:
        pass


class Node:
    def __init__(self, name: str, action: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]):
        self.name = name
        self.action = action
        self.middlewares: List[Middleware] = []

    def add_middleware(self, middleware: Middleware) -> None:
        self.middlewares.append(middleware)

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        async def _base_action(s: Dict[str, Any]) -> Dict[str, Any]:
            return await self.action(s)

        chain = _base_action
        for mw in reversed(self.middlewares):
            def make_chain(middleware: Middleware, next_func: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]) -> Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]:
                async def _chain_wrapper(s: Dict[str, Any]) -> Dict[str, Any]:
                    return await middleware(s, next_func)
                return _chain_wrapper
            chain = make_chain(mw, chain)

        return await chain(state)


class Edge:
    def __init__(self, source: str, target: str, condition: Optional[Callable[[Dict[str, Any]], Awaitable[bool]]] = None):
        self.source = source
        self.target = target
        self.condition = condition

    async def evaluate(self, state: Dict[str, Any]) -> bool:
        if self.condition is None:
            return True
        return await self.condition(state)


class LLMDirectedEdge(Edge):
    def __init__(self, source: str, target: str, llm_client: InferenceClient, prompt_template: str):
        super().__init__(source, target)
        self.llm_client = llm_client
        self.prompt_template = prompt_template

    async def evaluate(self, state: Dict[str, Any]) -> bool:
        prompt = self.prompt_template.format(state=json.dumps(state))
        response = await self.llm_client.generate(prompt, use_cache=True)
        return "true" in response.content.lower()


class Graph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.entry_point: Optional[str] = None
        self.snapshots: List[Snapshot] = []

    def add_node(self, node: Node) -> None:
        self.nodes[node.name] = node

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def set_entry_point(self, node_name: str) -> None:
        self.entry_point = node_name

    def _save_snapshot(self, node_name: str, state: Dict[str, Any]) -> None:
        self.snapshots.append(Snapshot(state=state.copy(), node=node_name, timestamp=time.time()))

    async def execute(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        if not self.entry_point:
            raise ValueError("Entry point not set")

        current_node_name: Optional[str] = self.entry_point
        state = initial_state.copy()
        self._save_snapshot("__start__", state)

        while current_node_name:
            if current_node_name not in self.nodes:
                raise ValueError(f"Node {current_node_name} not found in graph")
                
            node = self.nodes[current_node_name]
            
            with tracer.start_as_current_span(f"Graph.execute_node:{current_node_name}") as span:
                span.set_attribute("node.name", current_node_name)
                state = await node.execute(state)
                self._save_snapshot(current_node_name, state)

            next_node_name = None
            for edge in self.edges:
                if edge.source == current_node_name:
                    if await edge.evaluate(state):
                        next_node_name = edge.target
                        break
            
            current_node_name = next_node_name

        return state