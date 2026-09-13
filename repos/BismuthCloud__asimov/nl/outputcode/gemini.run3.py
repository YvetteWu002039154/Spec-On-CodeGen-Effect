import asyncio
import json
import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional, Union

try:
    import redis.asyncio as redis
except ImportError:
    class MockPubSub:
        async def subscribe(self, *args: Any) -> None:
            pass
        async def listen(self) -> AsyncGenerator[Dict[str, Any], None]:
            yield {'type': 'message', 'data': '"{}"'}

    class MockRedis:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.store: Dict[str, str] = {}

        async def get(self, key: str) -> Optional[str]:
            return self.store.get(key)

        async def set(self, key: str, val: str) -> None:
            self.store[key] = val

        async def keys(self, pattern: str) -> List[str]:
            return list(self.store.keys())

        async def mget(self, keys: List[str]) -> List[Optional[str]]:
            return [self.store.get(k) for k in keys]

        async def delete(self, *keys: str) -> None:
            for k in keys:
                self.store.pop(k, None)

        async def publish(self, channel: str, message: str) -> None:
            pass

        def pubsub(self) -> MockPubSub:
            return MockPubSub()

    class redis_mock:
        Redis = MockRedis

    redis = redis_mock

try:
    from opentelemetry import trace
except ImportError:
    class MockSpan:
        def __enter__(self) -> 'MockSpan':
            return self
        def __exit__(self, *args: Any) -> None:
            pass
        def set_attribute(self, key: str, value: Any) -> None:
            pass

    class MockTracer:
        def start_as_current_span(self, name: str, *args: Any, **kwargs: Any) -> MockSpan:
            return MockSpan()

    class trace_mock:
        @staticmethod
        def get_tracer(name: str) -> MockTracer:
            return MockTracer()

    trace = trace_mock


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
    def __init__(self, host: str = 'localhost', port: int = 6379, prefix: str = "", suffix: str = "") -> None:
        self.client = redis.Redis(host=host, port=port, decode_responses=True)
        self.prefix = prefix
        self.suffix = suffix

    def _format_key(self, key: str) -> str:
        return f"{self.prefix}{key}{self.suffix}"

    async def get(self, key: str) -> Any:
        val = await self.client.get(self._format_key(key))
        return json.loads(val) if val else None

    async def set(self, key: str, value: Any) -> None:
        await self.client.set(self._format_key(key), json.dumps(value))

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        keys = await self.client.keys(self._format_key(pattern))
        if not keys:
            return {}
        values = await self.client.mget(keys)
        return {k: json.loads(v) if v else None for k, v in zip(keys, values)}

    async def clear(self, pattern: str = "*") -> None:
        keys = await self.client.keys(self._format_key(pattern))
        if keys:
            await self.client.delete(*keys)

    async def publish(self, mailbox: str, message: Any) -> None:
        await self.client.publish(self._format_key(mailbox), json.dumps(message))

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        pubsub = self.client.pubsub()
        await pubsub.subscribe(self._format_key(mailbox))
        async for message in pubsub.listen():
            if message['type'] == 'message':
                yield json.loads(message['data'])


@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class ToolCall:
    id: str
    function_name: str
    arguments: Dict[str, Any]


@dataclass
class InferenceResponse:
    content: str
    usage: TokenUsage
    tool_calls: List[ToolCall] = field(default_factory=list)
    cached_prompt: bool = False


class InferenceClient(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        use_prompt_caching: bool = False
    ) -> InferenceResponse:
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
        pass


class DefaultLLMClient(InferenceClient):
    def __init__(self, provider_name: str = "default_provider") -> None:
        self.provider_name = provider_name
        self.tracer = trace.get_tracer(__name__)

    async def generate(
        self,
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        use_prompt_caching: bool = False
    ) -> InferenceResponse:
        with self.tracer.start_as_current_span(f"{self.provider_name}.generate") as span:
            span.set_attribute("llm.provider", self.provider_name)
            span.set_attribute("llm.prompt", prompt)
            span.set_attribute("llm.use_prompt_caching", use_prompt_caching)
            if tools:
                span.set_attribute("llm.tools_count", len(tools))

            usage = TokenUsage(
                prompt_tokens=len(prompt) // 4,
                completion_tokens=15,
                total_tokens=(len(prompt) // 4) + 15
            )
            span.set_attribute("llm.usage.total_tokens", usage.total_tokens)

            tool_calls = []
            if tools:
                tool_calls.append(
                    ToolCall(
                        id="call_mock_1",
                        function_name=tools[0].get("name", "unknown_tool"),
                        arguments={}
                    )
                )

            return InferenceResponse(
                content=f"Processed: {prompt[:20]}...",
                usage=usage,
                tool_calls=tool_calls,
                cached_prompt=use_prompt_caching
            )

    async def generate_stream(
        self,
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
        with self.tracer.start_as_current_span(f"{self.provider_name}.generate_stream") as span:
            span.set_attribute("llm.provider", self.provider_name)
            tokens = ["Streamed", " response", " for", " the", " prompt."]
            for token in tokens:
                await asyncio.sleep(0.01)
                yield token


class Node(ABC):
    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        pass


class LLMRouter:
    def __init__(self, llm_client: InferenceClient, routing_prompt: str, routes: List[str]) -> None:
        self.llm_client = llm_client
        self.routing_prompt = routing_prompt
        self.routes = routes

    async def route(self, state: Dict[str, Any]) -> str:
        prompt = f"{self.routing_prompt}\nState: {json.dumps(state)}\nAvailable Routes: {self.routes}"
        response = await self.llm_client.generate(prompt)
        
        for route in self.routes:
            if route.lower() in response.content.lower():
                return route
        return self.routes[0]


class Edge:
    def __init__(
        self,
        source: str,
        target: Optional[str] = None,
        condition: Optional[Callable[[Dict[str, Any]], Awaitable[bool]]] = None,
        llm_router: Optional[LLMRouter] = None
    ) -> None:
        self.source = source
        self.target = target
        self.condition = condition
        self.llm_router = llm_router


class Graph:
    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, List[Edge]] = {}
        self.entry_point: Optional[str] = None
        self.middlewares: List[Callable[[Node, Dict[str, Any], Callable], Awaitable[Dict[str, Any]]]] = []
        self.snapshots: Dict[str, Dict[str, Any]] = {}

    def add_node(self, node: Node) -> None:
        self.nodes[node.name] = node

    def add_edge(self, edge: Edge) -> None:
        if edge.source not in self.edges:
            self.edges[edge.source] = []
        self.edges[edge.source].append(edge)

    def set_entry_point(self, node_name: str) -> None:
        self.entry_point = node_name

    def add_middleware(self, middleware: Callable[[Node, Dict[str, Any], Callable], Awaitable[Dict[str, Any]]]) -> None:
        self.middlewares.append(middleware)

    def save_snapshot(self, snapshot_id: str, state: Dict[str, Any]) -> None:
        self.snapshots[snapshot_id] = copy.deepcopy(state)

    def load_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        state = self.snapshots.get(snapshot_id)
        return copy.deepcopy(state) if state else None

    def _wrap_middleware(
        self, 
        mw: Callable[[Node, Dict[str, Any], Callable], Awaitable[Dict[str, Any]]], 
        node: Node, 
        next_func: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
    ) -> Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]:
        async def wrapped(s: Dict[str, Any]) -> Dict[str, Any]:
            return await mw(node, s, next_func)
        return wrapped

    async def execute(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        if not self.entry_point:
            raise ValueError("Graph entry point is not set.")

        current_node_name: Optional[str] = self.entry_point
        state = copy.deepcopy(initial_state)

        while current_node_name:
            if current_node_name not in self.nodes:
                break

            node = self.nodes[current_node_name]

            async def base_execute(s: Dict[str, Any]) -> Dict[str, Any]:
                return await node.execute(s)

            execution_chain = base_execute
            for mw in reversed(self.middlewares):
                execution_chain = self._wrap_middleware(mw, node, execution_chain)

            state = await execution_chain(state)

            edges = self.edges.get(current_node_name, [])
            next_node_name = None

            for edge in edges:
                if edge.condition:
                    if await edge.condition(state):
                        next_node_name = edge.target
                        break
                elif edge.llm_router:
                    next_node_name = await edge.llm_router.route(state)
                    break
                else:
                    next_node_name = edge.target
                    break

            current_node_name = next_node_name

        return state