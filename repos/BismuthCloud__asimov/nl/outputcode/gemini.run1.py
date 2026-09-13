import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional

import redis.asyncio as redis
from opentelemetry import trace

class BaseCache(ABC):
    @abstractmethod
    async def get(self, key: str) -> Any:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any) -> None:
        pass

    @abstractmethod
    async def get_all(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass

    @abstractmethod
    async def publish(self, mailbox: str, message: Any) -> None:
        pass

    @abstractmethod
    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        pass

class RedisCache(BaseCache):
    def __init__(self, redis_url: str, prefix: str = "", suffix: str = ""):
        self.redis = redis.from_url(redis_url)
        self.prefix = prefix
        self.suffix = suffix

    def _format_key(self, key: str) -> str:
        return f"{self.prefix}{key}{self.suffix}"

    def _extract_key(self, formatted_key: str) -> str:
        key = formatted_key
        if self.prefix and key.startswith(self.prefix):
            key = key[len(self.prefix):]
        if self.suffix and key.endswith(self.suffix):
            key = key[:-len(self.suffix)]
        return key

    async def get(self, key: str) -> Any:
        val = await self.redis.get(self._format_key(key))
        return json.loads(val) if val else None

    async def set(self, key: str, value: Any) -> None:
        await self.redis.set(self._format_key(key), json.dumps(value))

    async def get_all(self) -> Dict[str, Any]:
        pattern = f"{self.prefix}*{self.suffix}"
        keys = await self.redis.keys(pattern)
        result = {}
        for k in keys:
            val = await self.redis.get(k)
            if val:
                decoded_key = k.decode('utf-8') if isinstance(k, bytes) else k
                orig_key = self._extract_key(decoded_key)
                result[orig_key] = json.loads(val)
        return result

    async def clear(self) -> None:
        pattern = f"{self.prefix}*{self.suffix}"
        keys = await self.redis.keys(pattern)
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
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    callable: Callable[..., Any]

@dataclass
class InferenceResponse:
    content: str
    usage: TokenUsage
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)

class InferenceClient(ABC):
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        tools: Optional[List[Tool]] = None, 
        use_prompt_caching: bool = False
    ) -> InferenceResponse:
        pass

    @abstractmethod
    async def generate_stream(
        self, 
        prompt: str, 
        tools: Optional[List[Tool]] = None, 
        use_prompt_caching: bool = False
    ) -> AsyncGenerator[str, None]:
        pass

class LLMProviderClient(InferenceClient):
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.tracer = trace.get_tracer(__name__)

    async def generate(
        self, 
        prompt: str, 
        tools: Optional[List[Tool]] = None, 
        use_prompt_caching: bool = False
    ) -> InferenceResponse:
        with self.tracer.start_as_current_span(f"{self.provider_name}.generate") as span:
            span.set_attribute("llm.provider", self.provider_name)
            span.set_attribute("llm.prompt", prompt)
            span.set_attribute("llm.use_prompt_caching", use_prompt_caching)
            if tools:
                span.set_attribute("llm.tools_count", len(tools))

            usage = TokenUsage(prompt_tokens=15, completion_tokens=25, total_tokens=40)
            span.set_attribute("llm.usage.total_tokens", usage.total_tokens)
            
            return InferenceResponse(
                content=f"Executed prompt on {self.provider_name}",
                usage=usage,
                tool_calls=[]
            )

    async def generate_stream(
        self, 
        prompt: str, 
        tools: Optional[List[Tool]] = None, 
        use_prompt_caching: bool = False
    ) -> AsyncGenerator[str, None]:
        with self.tracer.start_as_current_span(f"{self.provider_name}.generate_stream") as span:
            span.set_attribute("llm.provider", self.provider_name)
            span.set_attribute("llm.prompt", prompt)
            span.set_attribute("llm.use_prompt_caching", use_prompt_caching)
            
            chunks = ["Streaming", "response", "from", self.provider_name]
            for chunk in chunks:
                await asyncio.sleep(0.01)
                yield chunk + " "

State = Dict[str, Any]
NodeFunc = Callable[[State], Awaitable[State]]
MiddlewareFunc = Callable[[State, NodeFunc], Awaitable[State]]

class Node:
    def __init__(self, name: str, func: NodeFunc):
        self.name = name
        self.func = func

class Edge:
    def __init__(
        self, 
        source: str, 
        target: str, 
        condition: Optional[Callable[[State], bool]] = None
    ):
        self.source = source
        self.target = target
        self.condition = condition

class Graph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.middlewares: List[MiddlewareFunc] = []
        self.entry_point: Optional[str] = None
        self.snapshots: List[Dict[str, Any]] = []

    def add_node(self, name: str, func: NodeFunc) -> None:
        self.nodes[name] = Node(name, func)

    def add_edge(
        self, 
        source: str, 
        target: str, 
        condition: Optional[Callable[[State], bool]] = None
    ) -> None:
        self.edges.append(Edge(source, target, condition))

    def set_entry_point(self, name: str) -> None:
        if name not in self.nodes:
            raise ValueError(f"Node '{name}' does not exist.")
        self.entry_point = name

    def use_middleware(self, middleware: MiddlewareFunc) -> None:
        self.middlewares.append(middleware)

    async def _apply_middlewares(self, node: Node, state: State) -> State:
        func = node.func
        for mw in reversed(self.middlewares):
            def wrap(f: NodeFunc, m: MiddlewareFunc) -> NodeFunc:
                async def wrapped(s: State) -> State:
                    return await m(s, f)
                return wrapped
            func = wrap(func, mw)
        return await func(state)

    async def execute(self, initial_state: State) -> State:
        if not self.entry_point:
            raise ValueError("Entry point not set for the graph.")

        current_node_name: Optional[str] = self.entry_point
        state = initial_state.copy()
        
        self.snapshots.clear()
        self.snapshots.append({"node": "__start__", "state": state.copy()})

        while current_node_name:
            node = self.nodes[current_node_name]
            
            state = await self._apply_middlewares(node, state)
            
            self.snapshots.append({"node": current_node_name, "state": state.copy()})

            next_node_name = None
            for edge in self.edges:
                if edge.source == current_node_name:
                    if edge.condition is None or edge.condition(state):
                        next_node_name = edge.target
                        break 
            
            current_node_name = next_node_name

        return state