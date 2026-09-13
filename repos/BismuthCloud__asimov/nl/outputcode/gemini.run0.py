import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional, Union

import redis.asyncio as redis
from opentelemetry import trace

class Cache(ABC):
    @abstractmethod
    async def get(self, key: str) -> Any:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
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

class RedisCache(Cache):
    def __init__(self, redis_client: redis.Redis, prefix: str = "", suffix: str = ""):
        self.redis = redis_client
        self.prefix = prefix
        self.suffix = suffix

    def _build_key(self, key: str) -> str:
        return f"{self.prefix}{key}{self.suffix}"

    async def get(self, key: str) -> Any:
        val = await self.redis.get(self._build_key(key))
        return json.loads(val) if val else None

    async def set(self, key: str, value: Any) -> None:
        await self.redis.set(self._build_key(key), json.dumps(value))

    async def delete(self, key: str) -> None:
        await self.redis.delete(self._build_key(key))

    async def get_all(self) -> Dict[str, Any]:
        pattern = self._build_key("*")
        keys = await self.redis.keys(pattern)
        if not keys:
            return {}
        
        values = await self.redis.mget(keys)
        result = {}
        
        for k, v in zip(keys, values):
            k_str = k.decode('utf-8') if isinstance(k, bytes) else k
            if self.prefix and k_str.startswith(self.prefix):
                k_str = k_str[len(self.prefix):]
            if self.suffix and k_str.endswith(self.suffix):
                k_str = k_str[:-len(self.suffix)]
            result[k_str] = json.loads(v) if v else None
            
        return result

    async def clear(self) -> None:
        pattern = self._build_key("*")
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

    async def publish(self, mailbox: str, message: Any) -> None:
        await self.redis.publish(self._build_key(mailbox), json.dumps(message))

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self._build_key(mailbox))
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
    name: str
    arguments: Dict[str, Any]

@dataclass
class InferenceResult:
    content: str
    usage: TokenUsage
    tool_calls: List[ToolCall] = field(default_factory=list)

class InferenceClient(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        use_prompt_caching: bool = False
    ) -> Union[InferenceResult, AsyncGenerator[InferenceResult, None]]:
        pass

class LLMClient(InferenceClient):
    def __init__(self, provider: str):
        self.provider = provider
        self.tracer = trace.get_tracer(__name__)

    async def generate(
        self,
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        use_prompt_caching: bool = False
    ) -> Union[InferenceResult, AsyncGenerator[InferenceResult, None]]:
        with self.tracer.start_as_current_span(f"{self.provider}.generate") as span:
            span.set_attribute("llm.provider", self.provider)
            span.set_attribute("llm.prompt", prompt)
            span.set_attribute("llm.use_prompt_caching", use_prompt_caching)
            if tools:
                span.set_attribute("llm.tools_count", len(tools))

            usage = TokenUsage(
                prompt_tokens=len(prompt.split()),
                completion_tokens=15,
                total_tokens=len(prompt.split()) + 15
            )

            if stream:
                return self._stream_response(usage)
            else:
                tool_calls = []
                if tools:
                    tool_calls.append(ToolCall(name=tools[0].get("name", "tool"), arguments={"arg": "val"}))
                return InferenceResult(
                    content="Simulated LLM response",
                    usage=usage,
                    tool_calls=tool_calls
                )

    async def _stream_response(self, usage: TokenUsage) -> AsyncGenerator[InferenceResult, None]:
        words = ["Simulated", "streaming", "LLM", "response"]
        for word in words:
            yield InferenceResult(content=word + " ", usage=usage)
            await asyncio.sleep(0.01)

State = Dict[str, Any]
NodeFunc = Callable[[State], Union[State, Awaitable[State]]]
NextFunc = Callable[[State], Awaitable[State]]
MiddlewareFunc = Callable[[State, NextFunc], Awaitable[State]]
ConditionFunc = Callable[[State], bool]

class Graph:
    def __init__(self):
        self.nodes: Dict[str, NodeFunc] = {}
        self.edges: Dict[str, List[Dict[str, Any]]] = {}
        self.middlewares: List[MiddlewareFunc] = []
        self.entry_point: Optional[str] = None
        self.history: List[State] = []

    def add_node(self, name: str, func: NodeFunc) -> None:
        self.nodes[name] = func

    def add_edge(self, from_node: str, to_node: str, condition: Optional[ConditionFunc] = None) -> None:
        if from_node not in self.edges:
            self.edges[from_node] = []
        self.edges[from_node].append({"to": to_node, "condition": condition})

    def set_entry_point(self, name: str) -> None:
        self.entry_point = name

    def add_middleware(self, middleware: MiddlewareFunc) -> None:
        self.middlewares.append(middleware)

    def snapshot(self) -> List[State]:
        return [dict(state) for state in self.history]

    async def execute(self, initial_state: State) -> State:
        if not self.entry_point:
            raise ValueError("Entry point not set")

        current_node: Optional[str] = self.entry_point
        state = initial_state.copy()
        self.history.append(state.copy())

        while current_node:
            node_func = self.nodes[current_node]

            async def _run_node(s: State) -> State:
                if asyncio.iscoroutinefunction(node_func):
                    return await node_func(s)
                return node_func(s)

            chain = _run_node
            for mw in reversed(self.middlewares):
                def wrap(m: MiddlewareFunc, c: NextFunc) -> NextFunc:
                    async def wrapped(s: State) -> State:
                        return await m(s, c)
                    return wrapped
                chain = wrap(mw, chain)

            state = await chain(state)
            self.history.append(state.copy())

            next_node = None
            if current_node in self.edges:
                for edge in self.edges[current_node]:
                    condition = edge["condition"]
                    if condition is None or condition(state):
                        next_node = edge["to"]
                        break

            current_node = next_node

        return state

class LLMDirectedRouter:
    def __init__(self, client: InferenceClient, prompt_template: str, routes: List[str], state_key: str = "next_route"):
        self.client = client
        self.prompt_template = prompt_template
        self.routes = routes
        self.state_key = state_key

    async def __call__(self, state: State) -> State:
        prompt = f"{self.prompt_template}\nState: {json.dumps(state)}\nAvailable routes: {self.routes}"
        result = await self.client.generate(prompt=prompt, stream=False, use_prompt_caching=True)
        
        if isinstance(result, AsyncGenerator):
            raise ValueError("Streaming not supported for routing")
            
        chosen_route = self.routes[0]
        for route in self.routes:
            if route in result.content:
                chosen_route = route
                break
                
        state[self.state_key] = chosen_route
        return state