import asyncio
import json
import copy
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable, Tuple
from dataclasses import dataclass, field

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
    def __init__(self, redis_url: str, prefix: str = "", suffix: str = ""):
        self._redis = redis.from_url(redis_url)
        self._prefix = prefix
        self._suffix = suffix

    def _format_key(self, key: str) -> str:
        return f"{self._prefix}{key}{self._suffix}"

    def _extract_key(self, formatted_key: str) -> str:
        key = formatted_key
        if self._prefix and key.startswith(self._prefix):
            key = key[len(self._prefix):]
        if self._suffix and key.endswith(self._suffix):
            key = key[:-len(self._suffix)]
        return key

    async def get(self, key: str) -> Any:
        val = await self._redis.get(self._format_key(key))
        return json.loads(val) if val is not None else None

    async def set(self, key: str, value: Any) -> None:
        await self._redis.set(self._format_key(key), json.dumps(value))

    async def get_all(self) -> Dict[str, Any]:
        pattern = self._format_key("*")
        keys = await self._redis.keys(pattern)
        if not keys:
            return {}
        values = await self._redis.mget(keys)
        result = {}
        for k, v in zip(keys, values):
            if v is not None:
                decoded_key = k.decode('utf-8') if isinstance(k, bytes) else k
                result[self._extract_key(decoded_key)] = json.loads(v)
        return result

    async def clear(self) -> None:
        pattern = self._format_key("*")
        keys = await self._redis.keys(pattern)
        if keys:
            await self._redis.delete(*keys)

    async def publish(self, mailbox: str, message: Any) -> None:
        await self._redis.publish(self._format_key(mailbox), json.dumps(message))

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self._format_key(mailbox))
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(self._format_key(mailbox))
            await pubsub.close()

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

class InferenceClient(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        tools: Optional[List[Tool]] = None,
        use_prompt_caching: bool = False
    ) -> Tuple[str, TokenUsage]:
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        tools: Optional[List[Tool]] = None,
        use_prompt_caching: bool = False
    ) -> AsyncGenerator[Tuple[str, TokenUsage], None]:
        pass

class OpenAIClient(InferenceClient):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def generate(
        self,
        prompt: str,
        tools: Optional[List[Tool]] = None,
        use_prompt_caching: bool = False
    ) -> Tuple[str, TokenUsage]:
        with tracer.start_as_current_span("openai.generate") as span:
            span.set_attribute("llm.provider", "openai")
            span.set_attribute("llm.prompt_caching", use_prompt_caching)
            if tools:
                span.set_attribute("llm.tools_count", len(tools))
            
            await asyncio.sleep(0.1)
            response_text = f"OpenAI response to: {prompt}"
            usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
            return response_text, usage

    async def generate_stream(
        self,
        prompt: str,
        tools: Optional[List[Tool]] = None,
        use_prompt_caching: bool = False
    ) -> AsyncGenerator[Tuple[str, TokenUsage], None]:
        with tracer.start_as_current_span("openai.generate_stream") as span:
            span.set_attribute("llm.provider", "openai")
            span.set_attribute("llm.prompt_caching", use_prompt_caching)
            
            words = ["OpenAI", "stream", "response"]
            for i, word in enumerate(words):
                await asyncio.sleep(0.05)
                yield word, TokenUsage(prompt_tokens=10, completion_tokens=i+1, total_tokens=11+i)

class AnthropicClient(InferenceClient):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def generate(
        self,
        prompt: str,
        tools: Optional[List[Tool]] = None,
        use_prompt_caching: bool = False
    ) -> Tuple[str, TokenUsage]:
        with tracer.start_as_current_span("anthropic.generate") as span:
            span.set_attribute("llm.provider", "anthropic")
            span.set_attribute("llm.prompt_caching", use_prompt_caching)
            
            await asyncio.sleep(0.1)
            response_text = f"Anthropic response to: {prompt}"
            usage = TokenUsage(prompt_tokens=15, completion_tokens=25, total_tokens=40)
            return response_text, usage

    async def generate_stream(
        self,
        prompt: str,
        tools: Optional[List[Tool]] = None,
        use_prompt_caching: bool = False
    ) -> AsyncGenerator[Tuple[str, TokenUsage], None]:
        with tracer.start_as_current_span("anthropic.generate_stream") as span:
            span.set_attribute("llm.provider", "anthropic")
            span.set_attribute("llm.prompt_caching", use_prompt_caching)
            
            words = ["Anthropic", "stream", "response"]
            for i, word in enumerate(words):
                await asyncio.sleep(0.05)
                yield word, TokenUsage(prompt_tokens=15, completion_tokens=i+1, total_tokens=16+i)

class Middleware(ABC):
    @abstractmethod
    async def before_node(self, node_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def after_node(self, node_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
        pass

@dataclass
class Node:
    name: str
    action: Callable[[Dict[str, Any]], Any]
    dependencies: List[str] = field(default_factory=list)

class Graph:
    def __init__(self):
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, List[str]] = {}
        self._middlewares: List[Middleware] = []
        self._state: Dict[str, Any] = {}

    def add_node(self, name: str, action: Callable[[Dict[str, Any]], Any]) -> None:
        self._nodes[name] = Node(name=name, action=action)
        if name not in self._edges:
            self._edges[name] = []

    def add_edge(self, from_node: str, to_node: str) -> None:
        if from_node not in self._nodes or to_node not in self._nodes:
            raise ValueError("Both nodes must exist in the graph before adding an edge.")
        self._edges[from_node].append(to_node)
        self._nodes[to_node].dependencies.append(from_node)

    def add_middleware(self, middleware: Middleware) -> None:
        self._middlewares.append(middleware)

    def snapshot_state(self) -> Dict[str, Any]:
        return copy.deepcopy(self._state)

    def load_state(self, state_snapshot: Dict[str, Any]) -> None:
        self._state = copy.deepcopy(state_snapshot)

    async def _execute_node(self, node_name: str) -> None:
        for mw in self._middlewares:
            self._state = await mw.before_node(node_name, self._state)
        
        node = self._nodes[node_name]
        if asyncio.iscoroutinefunction(node.action):
            result = await node.action(self._state)
        else:
            result = node.action(self._state)
        
        if isinstance(result, dict):
            self._state.update(result)

        for mw in reversed(self._middlewares):
            self._state = await mw.after_node(node_name, self._state)

    async def execute(self) -> None:
        in_degree = {name: len(node.dependencies) for name, node in self._nodes.items()}
        queue = [name for name, degree in in_degree.items() if degree == 0]
        
        while queue:
            current_batch = queue[:]
            queue.clear()
            
            await asyncio.gather(*(self._execute_node(name) for name in current_batch))
            
            for name in current_batch:
                for neighbor in self._edges.get(name, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

    async def llm_directed_execute(
        self, 
        start_node: str, 
        llm_client: InferenceClient, 
        max_steps: int = 10
    ) -> None:
        current_node = start_node
        steps = 0
        
        while current_node and steps < max_steps:
            await self._execute_node(current_node)
            steps += 1
            
            possible_next_nodes = self._edges.get(current_node, [])
            if not possible_next_nodes:
                break
            
            if len(possible_next_nodes) == 1:
                current_node = possible_next_nodes[0]
                continue
            
            prompt = (
                f"Current state: {json.dumps(self._state)}\n"
                f"Possible next steps: {', '.join(possible_next_nodes)}\n"
                "Based on the state, which step should be executed next? Reply with only the step name."
            )
            
            response, _ = await llm_client.generate(prompt=prompt, use_prompt_caching=True)
            chosen_node = response.strip()
            
            if chosen_node in possible_next_nodes:
                current_node = chosen_node
            else:
                current_node = possible_next_nodes[0]