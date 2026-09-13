import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Union
from enum import Enum

import redis.asyncio as redis
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class Cache(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        pass

    @abstractmethod
    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        pass

    @abstractmethod
    async def clear(self, pattern: str = "*") -> None:
        pass

    @abstractmethod
    async def publish(self, channel: str, message: Any) -> int:
        pass

    @abstractmethod
    async def subscribe(self, channel: str) -> AsyncGenerator[Any, None]:
        pass


class RedisCache(Cache):
    def __init__(self, redis_url: str, prefix: str = "", suffix: str = ""):
        self.redis = redis.from_url(redis_url)
        self.prefix = prefix
        self.suffix = suffix

    def _format_key(self, key: str) -> str:
        return f"{self.prefix}{key}{self.suffix}"

    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(self._format_key(key))
        return json.loads(value) if value else None

    async def set(self, key: str, value: Any) -> None:
        await self.redis.set(self._format_key(key), json.dumps(value))

    async def delete(self, key: str) -> None:
        await self.redis.delete(self._format_key(key))

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        formatted_pattern = self._format_key(pattern)
        keys = await self.redis.keys(formatted_pattern)
        if not keys:
            return {}
        values = await self.redis.mget(keys)
        result = {}
        for k, v in zip(keys, values):
            decoded_key = k.decode("utf-8") if isinstance(k, bytes) else k
            result[decoded_key] = json.loads(v) if v else None
        return result

    async def clear(self, pattern: str = "*") -> None:
        formatted_pattern = self._format_key(pattern)
        keys = await self.redis.keys(formatted_pattern)
        if keys:
            await self.redis.delete(*keys)

    async def publish(self, channel: str, message: Any) -> int:
        return await self.redis.publish(self._format_key(channel), json.dumps(message))

    async def subscribe(self, channel: str) -> AsyncGenerator[Any, None]:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self._format_key(channel))
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield json.loads(message["data"])


class Mailbox:
    def __init__(self, cache: Cache, channel: str):
        self._cache = cache
        self._channel = channel

    async def send(self, message: Any) -> None:
        await self._cache.publish(self._channel, message)

    async def receive(self) -> AsyncGenerator[Any, None]:
        async for message in self._cache.subscribe(self._channel):
            yield message


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


@dataclass
class InferenceResponse:
    content: str
    usage: TokenUsage
    tool_calls: Optional[List[Dict[str, Any]]] = None


class InferenceClient(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        tools: Optional[List[Tool]] = None,
        use_prompt_caching: bool = False,
    ) -> InferenceResponse:
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        tools: Optional[List[Tool]] = None,
        use_prompt_caching: bool = False,
    ) -> AsyncGenerator[str, None]:
        pass


class OpenAIClient(InferenceClient):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        prompt: str,
        tools: Optional[List[Tool]] = None,
        use_prompt_caching: bool = False,
    ) -> InferenceResponse:
        with tracer.start_as_current_span("openai_generate") as span:
            span.set_attribute("model", self.model)
            span.set_attribute("prompt_caching", use_prompt_caching)
            
            await asyncio.sleep(0.1)
            
            usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
            return InferenceResponse(
                content=f"OpenAI response to: {prompt}",
                usage=usage,
                tool_calls=[]
            )

    async def generate_stream(
        self,
        prompt: str,
        tools: Optional[List[Tool]] = None,
        use_prompt_caching: bool = False,
    ) -> AsyncGenerator[str, None]:
        with tracer.start_as_current_span("openai_generate_stream") as span:
            span.set_attribute("model", self.model)
            span.set_attribute("prompt_caching", use_prompt_caching)
            
            words = ["Streaming", "OpenAI", "response", "for", prompt]
            for word in words:
                await asyncio.sleep(0.05)
                yield word + " "


class AnthropicClient(InferenceClient):
    def __init__(self, api_key: str, model: str = "claude-3-opus"):
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        prompt: str,
        tools: Optional[List[Tool]] = None,
        use_prompt_caching: bool = False,
    ) -> InferenceResponse:
        with tracer.start_as_current_span("anthropic_generate") as span:
            span.set_attribute("model", self.model)
            span.set_attribute("prompt_caching", use_prompt_caching)
            
            await asyncio.sleep(0.1)
            
            usage = TokenUsage(prompt_tokens=15, completion_tokens=25, total_tokens=40)
            return InferenceResponse(
                content=f"Anthropic response to: {prompt}",
                usage=usage,
                tool_calls=[]
            )

    async def generate_stream(
        self,
        prompt: str,
        tools: Optional[List[Tool]] = None,
        use_prompt_caching: bool = False,
    ) -> AsyncGenerator[str, None]:
        with tracer.start_as_current_span("anthropic_generate_stream") as span:
            span.set_attribute("model", self.model)
            span.set_attribute("prompt_caching", use_prompt_caching)
            
            words = ["Streaming", "Anthropic", "response", "for", prompt]
            for word in words:
                await asyncio.sleep(0.05)
                yield word + " "


@dataclass
class GraphState:
    data: Dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> 'GraphState':
        return GraphState(data=json.loads(json.dumps(self.data)))

    def update(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


Middleware = Callable[[Callable[['GraphState'], Any], 'GraphState'], Any]


class Node:
    def __init__(
        self,
        name: str,
        action: Callable[['GraphState'], Any],
        middlewares: Optional[List[Middleware]] = None
    ):
        self.name = name
        self._action = action
        self._middlewares = middlewares or []

    async def execute(self, state: GraphState) -> Any:
        async def base_action(s: GraphState) -> Any:
            if asyncio.iscoroutinefunction(self._action):
                return await self._action(s)
            return self._action(s)

        current_func = base_action

        for middleware in reversed(self._middlewares):
            current_func = self._wrap_middleware(middleware, current_func)

        with tracer.start_as_current_span(f"node_execute_{self.name}"):
            return await current_func(state)

    def _wrap_middleware(
        self,
        middleware: Middleware,
        next_func: Callable[['GraphState'], Any]
    ) -> Callable[['GraphState'], Any]:
        async def wrapped(state: GraphState) -> Any:
            if asyncio.iscoroutinefunction(middleware):
                return await middleware(next_func, state)
            return middleware(next_func, state)
        return wrapped


class Edge:
    def __init__(
        self,
        source: str,
        target: str,
        condition: Optional[Callable[['GraphState'], Union[bool, Any]]] = None
    ):
        self.source = source
        self.target = target
        self._condition = condition

    async def evaluate(self, state: GraphState) -> bool:
        if self._condition is None:
            return True
        
        with tracer.start_as_current_span(f"edge_evaluate_{self.source}_to_{self.target}"):
            if asyncio.iscoroutinefunction(self._condition):
                return await self._condition(state)
            return self._condition(state)


class Graph:
    def __init__(self):
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._entry_point: Optional[str] = None
        self._history: List[GraphState] = []

    def add_node(self, node: Node) -> None:
        self._nodes[node.name] = node

    def add_edge(self, edge: Edge) -> None:
        self._edges.append(edge)

    def set_entry_point(self, node_name: str) -> None:
        if node_name not in self._nodes:
            raise ValueError(f"Node '{node_name}' does not exist in the graph.")
        self._entry_point = node_name

    def get_history(self) -> List[GraphState]:
        return self._history

    async def execute(self, initial_state: Optional[GraphState] = None) -> GraphState:
        if not self._entry_point:
            raise ValueError("Entry point not set for the graph.")

        state = initial_state or GraphState()
        current_node_name = self._entry_point
        self._history = []

        with tracer.start_as_current_span("graph_execution") as span:
            while current_node_name:
                self._history.append(state.snapshot())
                
                node = self._nodes[current_node_name]
                await node.execute(state)

                next_node_name = None
                for edge in self._edges:
                    if edge.source == current_node_name:
                        if await edge.evaluate(state):
                            next_node_name = edge.target
                            break
                
                current_node_name = next_node_name

        self._history.append(state.snapshot())
        return state


class LLMDirectedRouter:
    def __init__(self, client: InferenceClient, prompt_template: str):
        self.client = client
        self.prompt_template = prompt_template

    async def route(self, state: GraphState, target_node: str) -> bool:
        prompt = self.prompt_template.format(state=json.dumps(state.data))
        response = await self.client.generate(prompt=prompt, use_prompt_caching=True)
        decision = response.content.strip().lower()
        return target_node.lower() in decision