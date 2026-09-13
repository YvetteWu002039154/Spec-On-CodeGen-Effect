import asyncio
import json
import copy
import uuid
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Union, Set
from dataclasses import dataclass, field
from datetime import datetime

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

try:
    from opentelemetry import trace
except ImportError:
    trace = None

def get_tracer():
    if trace:
        return trace.get_tracer(__name__)
    
    class DummySpan:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def set_attribute(self, *args): pass
        def add_event(self, *args): pass

    class DummyTracer:
        def start_as_current_span(self, *args, **kwargs): return DummySpan()
        
    return DummyTracer()

tracer = get_tracer()

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
    def __init__(self, url: str = "redis://localhost", prefix: str = "", suffix: str = ""):
        if redis is None:
            raise RuntimeError("redis package is not installed. Install with `pip install redis`.")
        self.redis = redis.from_url(url)
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
        result = {}
        for k, v in zip(keys, values):
            if v:
                decoded_key = k.decode('utf-8') if isinstance(k, bytes) else k
                result[decoded_key] = json.loads(v)
        return result

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
    cached_prompt_used: bool = False

class InferenceClient(ABC):
    def __init__(self, cache: Optional[Cache] = None):
        self.cache = cache

    @abstractmethod
    async def generate(self, prompt: str, tools: Optional[List[Tool]] = None, use_prompt_caching: bool = False) -> InferenceResponse:
        pass

    @abstractmethod
    async def stream(self, prompt: str, tools: Optional[List[Tool]] = None, use_prompt_caching: bool = False) -> AsyncGenerator[str, None]:
        pass

class GenericLLMClient(InferenceClient):
    def __init__(self, provider_name: str, cache: Optional[Cache] = None):
        super().__init__(cache)
        self.provider_name = provider_name

    async def generate(self, prompt: str, tools: Optional[List[Tool]] = None, use_prompt_caching: bool = False) -> InferenceResponse:
        with tracer.start_as_current_span(f"{self.provider_name}.generate") as span:
            span.set_attribute("llm.provider", self.provider_name)
            span.set_attribute("llm.prompt", prompt)
            
            cached_used = False
            if use_prompt_caching and self.cache:
                cache_key = f"prompt_cache:{hash(prompt)}"
                cached_response = await self.cache.get(cache_key)
                if cached_response:
                    span.set_attribute("llm.cache_hit", True)
                    return InferenceResponse(**cached_response)
            
            span.set_attribute("llm.cache_hit", False)
            
            await asyncio.sleep(0.1)
            
            response_content = f"[{self.provider_name}] Processed: {prompt[:20]}..."
            tool_calls = []
            
            if tools and "tool" in prompt.lower():
                tool_calls.append({
                    "name": tools[0].name,
                    "arguments": {"arg1": "value1"}
                })

            usage = TokenUsage(
                prompt_tokens=len(prompt.split()),
                completion_tokens=len(response_content.split()),
                total_tokens=len(prompt.split()) + len(response_content.split())
            )
            
            span.set_attribute("llm.usage.total_tokens", usage.total_tokens)
            
            response = InferenceResponse(
                content=response_content,
                usage=usage,
                tool_calls=tool_calls,
                cached_prompt_used=cached_used
            )
            
            if use_prompt_caching and self.cache:
                cache_key = f"prompt_cache:{hash(prompt)}"
                await self.cache.set(cache_key, {
                    "content": response.content,
                    "usage": {
                        "prompt_tokens": usage.prompt_tokens,
                        "completion_tokens": usage.completion_tokens,
                        "total_tokens": usage.total_tokens
                    },
                    "tool_calls": response.tool_calls,
                    "cached_prompt_used": True
                })
                
            return response

    async def stream(self, prompt: str, tools: Optional[List[Tool]] = None, use_prompt_caching: bool = False) -> AsyncGenerator[str, None]:
        with tracer.start_as_current_span(f"{self.provider_name}.stream") as span:
            span.set_attribute("llm.provider", self.provider_name)
            
            words = f"[{self.provider_name}] Streaming response for {prompt[:10]}...".split()
            for word in words:
                await asyncio.sleep(0.05)
                yield word + " "

class GraphState:
    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        self.data: Dict[str, Any] = initial_data or {}
        self._history: List[Dict[str, Any]] = []

    def update(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def snapshot(self) -> str:
        snapshot_id = str(uuid.uuid4())
        snapshot_data = {
            "id": snapshot_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": copy.deepcopy(self.data)
        }
        self._history.append(snapshot_data)
        return snapshot_id

    def restore(self, snapshot_id: str) -> bool:
        for snap in self._history:
            if snap["id"] == snapshot_id:
                self.data = copy.deepcopy(snap["data"])
                return True
        return False

    def get_history(self) -> List[Dict[str, Any]]:
        return self._history

class Middleware(ABC):
    @abstractmethod
    async def before_node(self, node_name: str, state: GraphState) -> None:
        pass

    @abstractmethod
    async def after_node(self, node_name: str, state: GraphState) -> None:
        pass

class LoggingMiddleware(Middleware):
    async def before_node(self, node_name: str, state: GraphState) -> None:
        print(f"Executing node: {node_name}")

    async def after_node(self, node_name: str, state: GraphState) -> None:
        print(f"Completed node: {node_name}")

class Node:
    def __init__(self, name: str, action: Callable[[GraphState], Any]):
        self.name = name
        self.action = action

    async def execute(self, state: GraphState) -> None:
        if asyncio.iscoroutinefunction(self.action):
            await self.action(state)
        else:
            self.action(state)

class LLMDirectedNode(Node):
    def __init__(self, name: str, client: InferenceClient, prompt_template: str, output_key: str):
        super().__init__(name, self._llm_action)
        self.client = client
        self.prompt_template = prompt_template
        self.output_key = output_key

    async def _llm_action(self, state: GraphState) -> None:
        prompt = self.prompt_template.format(**state.data)
        response = await self.client.generate(prompt)
        state.update(self.output_key, response.content)

class Edge:
    def __init__(self, from_node: str, to_node: str, condition: Optional[Callable[[GraphState], bool]] = None):
        self.from_node = from_node
        self.to_node = to_node
        self.condition = condition

class Graph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.middlewares: List[Middleware] = []
        self.entry_point: Optional[str] = None

    def add_node(self, node: Node) -> None:
        self.nodes[node.name] = node

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def set_entry_point(self, node_name: str) -> None:
        if node_name not in self.nodes:
            raise ValueError(f"Node {node_name} does not exist.")
        self.entry_point = node_name

    def add_middleware(self, middleware: Middleware) -> None:
        self.middlewares.append(middleware)

    async def execute(self, initial_state: Optional[GraphState] = None) -> GraphState:
        if not self.entry_point:
            raise ValueError("Entry point not set for the graph.")

        state = initial_state or GraphState()
        current_node_name: Optional[str] = self.entry_point

        with tracer.start_as_current_span("Graph.execute") as span:
            span.set_attribute("graph.entry_point", self.entry_point)
            
            while current_node_name:
                node = self.nodes[current_node_name]
                
                with tracer.start_as_current_span(f"Node.{current_node_name}") as node_span:
                    state.snapshot()
                    
                    for mw in self.middlewares:
                        await mw.before_node(current_node_name, state)
                        
                    await node.execute(state)
                    
                    for mw in self.middlewares:
                        await mw.after_node(current_node_name, state)
                        
                    next_node_name = None
                    for edge in self.edges:
                        if edge.from_node == current_node_name:
                            if edge.condition is None or edge.condition(state):
                                next_node_name = edge.to_node
                                break
                                
                    current_node_name = next_node_name

        return state