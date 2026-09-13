import asyncio
import json
import datetime
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable, Awaitable
from dataclasses import dataclass, field

class DummySpan:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    def set_attribute(self, key: str, value: Any):
        pass

class DummyTracer:
    def start_as_current_span(self, name: str):
        return DummySpan()

try:
    from opentelemetry import trace
    tracer = trace.get_tracer(__name__)
except ImportError:
    tracer = DummyTracer()

class Cache(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
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
    def __init__(self, redis_url: str = "redis://localhost", prefix: str = "", suffix: str = ""):
        self.prefix = prefix
        self.suffix = suffix
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(redis_url, decode_responses=True)
            self._has_redis = True
        except ImportError:
            self._has_redis = False
            self._mock_store: Dict[str, str] = {}
            self._mock_pubsub: Dict[str, List[asyncio.Queue]] = {}

    def _format_key(self, key: str) -> str:
        return f"{self.prefix}{key}{self.suffix}"

    def _extract_key(self, formatted_key: str) -> str:
        key = formatted_key
        if self.prefix and key.startswith(self.prefix):
            key = key[len(self.prefix):]
        if self.suffix and key.endswith(self.suffix):
            key = key[:-len(self.suffix)]
        return key

    async def get(self, key: str) -> Optional[Any]:
        full_key = self._format_key(key)
        if self._has_redis:
            val = await self._redis.get(full_key)
            return json.loads(val) if val else None
        else:
            val = self._mock_store.get(full_key)
            return json.loads(val) if val else None

    async def set(self, key: str, value: Any) -> None:
        full_key = self._format_key(key)
        val = json.dumps(value)
        if self._has_redis:
            await self._redis.set(full_key, val)
        else:
            self._mock_store[full_key] = val

    async def get_all(self) -> Dict[str, Any]:
        result = {}
        if self._has_redis:
            pattern = self._format_key("*")
            keys = await self._redis.keys(pattern)
            for k in keys:
                val = await self._redis.get(k)
                if val:
                    result[self._extract_key(k)] = json.loads(val)
        else:
            for k, val in self._mock_store.items():
                if k.startswith(self.prefix) and (not self.suffix or k.endswith(self.suffix)):
                    result[self._extract_key(k)] = json.loads(val)
        return result

    async def clear(self) -> None:
        if self._has_redis:
            pattern = self._format_key("*")
            keys = await self._redis.keys(pattern)
            if keys:
                await self._redis.delete(*keys)
        else:
            keys_to_delete = [
                k for k in self._mock_store.keys() 
                if k.startswith(self.prefix) and (not self.suffix or k.endswith(self.suffix))
            ]
            for k in keys_to_delete:
                del self._mock_store[k]

    async def publish(self, mailbox: str, message: Any) -> None:
        full_mailbox = self._format_key(mailbox)
        val = json.dumps(message)
        if self._has_redis:
            await self._redis.publish(full_mailbox, val)
        else:
            if full_mailbox not in self._mock_pubsub:
                self._mock_pubsub[full_mailbox] = []
            for queue in self._mock_pubsub[full_mailbox]:
                await queue.put(val)

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        full_mailbox = self._format_key(mailbox)
        if self._has_redis:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(full_mailbox)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield json.loads(message["data"])
        else:
            queue = asyncio.Queue()
            if full_mailbox not in self._mock_pubsub:
                self._mock_pubsub[full_mailbox] = []
            self._mock_pubsub[full_mailbox].append(queue)
            try:
                while True:
                    val = await queue.get()
                    yield json.loads(val)
            finally:
                self._mock_pubsub[full_mailbox].remove(queue)

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
class LLMResponse:
    content: str
    usage: TokenUsage
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    cached_prompt: bool = False

class InferenceClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, tools: Optional[List[Tool]] = None, use_cache: bool = False) -> LLMResponse:
        pass

    @abstractmethod
    async def generate_stream(self, prompt: str, tools: Optional[List[Tool]] = None, use_cache: bool = False) -> AsyncGenerator[str, None]:
        pass

class DefaultInferenceClient(InferenceClient):
    def __init__(self, provider_name: str = "default_provider", cache: Optional[Cache] = None):
        self.provider_name = provider_name
        self.cache = cache

    async def generate(self, prompt: str, tools: Optional[List[Tool]] = None, use_cache: bool = False) -> LLMResponse:
        with tracer.start_as_current_span(f"{self.provider_name}.generate") as span:
            span.set_attribute("prompt.length", len(prompt))
            
            if use_cache and self.cache:
                cache_key = f"prompt_cache:{hash(prompt)}"
                cached_response = await self.cache.get(cache_key)
                if cached_response:
                    span.set_attribute("cache.hit", True)
                    return LLMResponse(
                        content=cached_response["content"],
                        usage=TokenUsage(**cached_response["usage"]),
                        cached_prompt=True
                    )

            span.set_attribute("cache.hit", False)
            
            simulated_content = f"Simulated response for: {prompt[:20]}..."
            usage = TokenUsage(prompt_tokens=len(prompt), completion_tokens=len(simulated_content), total_tokens=len(prompt) + len(simulated_content))
            
            response = LLMResponse(content=simulated_content, usage=usage, cached_prompt=False)
            
            if use_cache and self.cache:
                cache_key = f"prompt_cache:{hash(prompt)}"
                await self.cache.set(cache_key, {
                    "content": response.content,
                    "usage": {"prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens, "total_tokens": usage.total_tokens}
                })
                
            return response

    async def generate_stream(self, prompt: str, tools: Optional[List[Tool]] = None, use_cache: bool = False) -> AsyncGenerator[str, None]:
        with tracer.start_as_current_span(f"{self.provider_name}.generate_stream") as span:
            simulated_words = ["Simulated", " streaming", " response", " for", " prompt."]
            for word in simulated_words:
                await asyncio.sleep(0.01)
                yield word

State = Dict[str, Any]
NodeAction = Callable[[State], Awaitable[State]]
Middleware = Callable[[str, State, NodeAction], Awaitable[State]]

class Node:
    def __init__(self, name: str, action: NodeAction):
        self.name = name
        self.action = action

class Edge:
    def __init__(self, source: str, target: str, condition: Optional[Callable[[State], bool]] = None):
        self.source = source
        self.target = target
        self.condition = condition

class Graph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.entry_point: Optional[str] = None

    def add_node(self, name: str, action: NodeAction):
        self.nodes[name] = Node(name, action)

    def add_edge(self, source: str, target: str, condition: Optional[Callable[[State], bool]] = None):
        self.edges.append(Edge(source, target, condition))

    def set_entry_point(self, name: str):
        self.entry_point = name

class GraphExecutor:
    def __init__(self, graph: Graph, middlewares: Optional[List[Middleware]] = None):
        self.graph = graph
        self.middlewares = middlewares or []
        self.state_snapshots: List[Dict[str, Any]] = []

    async def execute(self, initial_state: State) -> State:
        if not self.graph.entry_point:
            raise ValueError("Graph entry point not set")

        current_node_name: Optional[str] = self.graph.entry_point
        state = initial_state.copy()

        with tracer.start_as_current_span("graph_execution") as span:
            while current_node_name:
                self.state_snapshots.append({
                    "node": current_node_name,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "state": state.copy()
                })

                node = self.graph.nodes[current_node_name]
                action = node.action

                for mw in reversed(self.middlewares):
                    action = self._wrap_middleware(mw, current_node_name, action)

                with tracer.start_as_current_span(f"node_{current_node_name}"):
                    state = await action(state)

                next_node_name = None
                for edge in self.graph.edges:
                    if edge.source == current_node_name:
                        if edge.condition is None or edge.condition(state):
                            next_node_name = edge.target
                            break
                
                current_node_name = next_node_name

            self.state_snapshots.append({
                "node": "__end__",
                "timestamp": datetime.datetime.now().isoformat(),
                "state": state.copy()
            })

            return state

    def _wrap_middleware(self, mw: Middleware, node_name: str, next_action: NodeAction) -> NodeAction:
        async def wrapped(state: State) -> State:
            return await mw(node_name, state, next_action)
        return wrapped

class LLMDirectedRouter:
    def __init__(self, client: InferenceClient, state_key: str = "next_route"):
        self.client = client
        self.state_key = state_key

    async def route_node_action(self, state: State, prompt_template: str, available_routes: List[str]) -> State:
        prompt = prompt_template.format(**state)
        full_prompt = f"{prompt}\nAvailable routes: {', '.join(available_routes)}\nReply with ONLY the route name."
        
        response = await self.client.generate(full_prompt, use_cache=True)
        decision = response.content.strip()
        
        if decision not in available_routes:
            decision = available_routes[0]
            
        state[self.state_key] = decision
        return state

async def logging_middleware(node_name: str, state: State, next_action: NodeAction) -> State:
    state["log"] = state.get("log", []) + [f"Entering {node_name}"]
    new_state = await next_action(state)
    new_state["log"] = new_state.get("log", []) + [f"Exiting {node_name}"]
    return new_state

async def main():
    cache = RedisCache(prefix="agent:", suffix=":v1")
    await cache.clear()
    
    llm_client = DefaultInferenceClient(cache=cache)
    router = LLMDirectedRouter(client=llm_client)

    async def node_a(state: State) -> State:
        state["data"] = "Processed by A"
        return await router.route_node_action(
            state, 
            "Analyze this data: {data}. Should we go to B or C?", 
            ["node_b", "node_c"]
        )

    async def node_b(state: State) -> State:
        state["final_result"] = "Finished in B"
        return state

    async def node_c(state: State) -> State:
        state["final_result"] = "Finished in C"
        return state

    graph = Graph()
    graph.add_node("node_a", node_a)
    graph.add_node("node_b", node_b)
    graph.add_node("node_c", node_c)

    graph.add_edge("node_a", "node_b", lambda s: s.get("next_route") == "node_b")
    graph.add_edge("node_a", "node_c", lambda s: s.get("next_route") == "node_c")
    
    graph.set_entry_point("node_a")

    executor = GraphExecutor(graph, middlewares=[logging_middleware])
    
    final_state = await executor.execute({"input": "start"})
    
    await cache.set("final_execution_state", final_state)
    cached_state = await cache.get("final_execution_state")

if __name__ == "__main__":
    asyncio.run(main())