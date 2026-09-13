import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional, Union

import redis.asyncio as redis
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

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

    async def delete(self, key: str) -> None:
        await self.redis.delete(self._format_key(key))

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        formatted_pattern = self._format_key(pattern)
        keys = await self.redis.keys(formatted_pattern)
        if not keys:
            return {}
        values = await self.redis.mget(keys)
        return {
            k.decode('utf-8'): json.loads(v) 
            for k, v in zip(keys, values) if v
        }

    async def clear(self, pattern: str = "*") -> None:
        formatted_pattern = self._format_key(pattern)
        keys = await self.redis.keys(formatted_pattern)
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
    func: Callable[..., Any]

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

class GenericLLMClient(InferenceClient):
    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    async def generate(
        self, 
        prompt: str, 
        tools: Optional[List[Tool]] = None, 
        use_prompt_caching: bool = False
    ) -> InferenceResponse:
        with tracer.start_as_current_span(f"{self.provider_name}.generate") as span:
            span.set_attribute("llm.provider", self.provider_name)
            span.set_attribute("llm.prompt", prompt)
            span.set_attribute("llm.prompt_caching_enabled", use_prompt_caching)
            if tools:
                span.set_attribute("llm.tools_count", len(tools))
            
            usage = TokenUsage(prompt_tokens=15, completion_tokens=25, total_tokens=40)
            span.set_attribute("llm.usage.total_tokens", usage.total_tokens)
            
            return InferenceResponse(
                content=f"[{self.provider_name}] Processed: {prompt}",
                usage=usage,
                tool_calls=[]
            )

    async def generate_stream(
        self, 
        prompt: str, 
        tools: Optional[List[Tool]] = None, 
        use_prompt_caching: bool = False
    ) -> AsyncGenerator[str, None]:
        with tracer.start_as_current_span(f"{self.provider_name}.generate_stream") as span:
            span.set_attribute("llm.provider", self.provider_name)
            span.set_attribute("llm.prompt", prompt)
            span.set_attribute("llm.prompt_caching_enabled", use_prompt_caching)
            
            tokens = ["Streamed", "response", "for", prompt]
            for token in tokens:
                yield token + " "
                await asyncio.sleep(0.01)

class GraphState:
    def __init__(self, initial_state: Optional[Dict[str, Any]] = None):
        self._state: Dict[str, Any] = initial_state or {}
        self._history: List[Dict[str, Any]] = []

    @property
    def state(self) -> Dict[str, Any]:
        return self._state

    def update(self, updates: Dict[str, Any]) -> None:
        self._history.append(self._state.copy())
        self._state.update(updates)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "state": self._state.copy(),
            "history": [h.copy() for h in self._history]
        }

    def restore(self, snapshot: Dict[str, Any]) -> None:
        self._state = snapshot["state"].copy()
        self._history = [h.copy() for h in snapshot["history"]]

class Node:
    def __init__(self, name: str, func: Callable[[GraphState], Any]):
        self.name = name
        self.func = func

    async def execute(self, state: GraphState) -> Any:
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(state)
        return self.func(state)

Middleware = Callable[[Node, GraphState, Callable[[], Awaitable[Any]]], Awaitable[Any]]

class Graph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, List[str]] = {}
        self.middlewares: List[Middleware] = []
        self.entry_point: Optional[str] = None

    def add_node(self, node: Node) -> None:
        self.nodes[node.name] = node
        if node.name not in self.edges:
            self.edges[node.name] = []

    def add_edge(self, from_node: str, to_node: str) -> None:
        if from_node not in self.nodes or to_node not in self.nodes:
            raise ValueError("Both nodes must be added to the graph before creating an edge.")
        self.edges[from_node].append(to_node)

    def set_entry_point(self, node_name: str) -> None:
        if node_name not in self.nodes:
            raise ValueError(f"Node {node_name} not found in graph.")
        self.entry_point = node_name

    def add_middleware(self, middleware: Middleware) -> None:
        self.middlewares.append(middleware)

    async def _run_node_with_middleware(self, node: Node, state: GraphState) -> Any:
        async def execute_chain(index: int) -> Any:
            if index < len(self.middlewares):
                return await self.middlewares[index](node, state, lambda: execute_chain(index + 1))
            return await node.execute(state)
        return await execute_chain(0)

    async def execute(self, state: GraphState) -> GraphState:
        if not self.entry_point:
            raise ValueError("Entry point not set for the graph.")

        current_node_name: Optional[str] = self.entry_point
        
        while current_node_name:
            node = self.nodes[current_node_name]
            result = await self._run_node_with_middleware(node, state)
            state.update({f"{current_node_name}_result": result})

            next_nodes = self.edges.get(current_node_name, [])
            current_node_name = next_nodes[0] if next_nodes else None
            
        return state

class LLMDirectedGraph(Graph):
    def __init__(self, llm_client: InferenceClient):
        super().__init__()
        self.llm_client = llm_client

    async def execute(self, state: GraphState) -> GraphState:
        if not self.entry_point:
            raise ValueError("Entry point not set for the graph.")

        current_node_name: Optional[str] = self.entry_point
        
        while current_node_name:
            node = self.nodes[current_node_name]
            result = await self._run_node_with_middleware(node, state)
            state.update({f"{current_node_name}_result": result})

            next_nodes = self.edges.get(current_node_name, [])
            if not next_nodes:
                break
            elif len(next_nodes) == 1:
                current_node_name = next_nodes[0]
            else:
                prompt = (
                    f"Current state: {json.dumps(state.state)}. "
                    f"Available next steps: {next_nodes}. "
                    f"Which step should be taken next? Reply with only the exact step name."
                )
                response = await self.llm_client.generate(
                    prompt=prompt, 
                    use_prompt_caching=True
                )
                decision = response.content.strip()
                
                if decision in next_nodes:
                    current_node_name = decision
                else:
                    raise ValueError(f"LLM returned invalid next node: {decision}")
                    
        return state