import asyncio
import copy
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Union

import redis.asyncio as redis
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class BaseCache(ABC):
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

    def _extract_key(self, formatted_key: Union[str, bytes]) -> str:
        k_str = formatted_key.decode("utf-8") if isinstance(formatted_key, bytes) else formatted_key
        if self.prefix and k_str.startswith(self.prefix):
            k_str = k_str[len(self.prefix):]
        if self.suffix and k_str.endswith(self.suffix):
            k_str = k_str[:-len(self.suffix)]
        return k_str

    async def get(self, key: str) -> Optional[Any]:
        val = await self.redis.get(self._format_key(key))
        return json.loads(val) if val else None

    async def set(self, key: str, value: Any) -> None:
        await self.redis.set(self._format_key(key), json.dumps(value))

    async def delete(self, key: str) -> None:
        await self.redis.delete(self._format_key(key))

    async def get_all(self) -> Dict[str, Any]:
        pattern = f"{self.prefix}*{self.suffix}"
        keys = await self.redis.keys(pattern)
        if not keys:
            return {}
        values = await self.redis.mget(keys)
        result = {}
        for k, v in zip(keys, values):
            if v:
                result[self._extract_key(k)] = json.loads(v)
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
            if message["type"] == "message":
                yield json.loads(message["data"])


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
class Message:
    role: str
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    token_usage: Optional[TokenUsage] = None


class BaseInferenceClient(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        use_prompt_caching: bool = False
    ) -> Message:
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        use_prompt_caching: bool = False
    ) -> AsyncGenerator[Message, None]:
        pass


class OpenAIInferenceClient(BaseInferenceClient):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        use_prompt_caching: bool = False
    ) -> Message:
        with tracer.start_as_current_span("llm.generate") as span:
            span.set_attribute("llm.provider", "openai")
            span.set_attribute("llm.model", self.model)
            span.set_attribute("llm.prompt_caching", use_prompt_caching)
            if tools:
                span.set_attribute("llm.tools_count", len(tools))
            
            await asyncio.sleep(0.1)
            
            usage = TokenUsage(prompt_tokens=15, completion_tokens=25, total_tokens=40)
            span.set_attribute("llm.usage.total_tokens", usage.total_tokens)
            
            return Message(
                role="assistant",
                content=f"Processed: {prompt[:10]}...",
                token_usage=usage
            )

    async def generate_stream(
        self,
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        use_prompt_caching: bool = False
    ) -> AsyncGenerator[Message, None]:
        with tracer.start_as_current_span("llm.generate_stream") as span:
            span.set_attribute("llm.provider", "openai")
            span.set_attribute("llm.model", self.model)
            span.set_attribute("llm.prompt_caching", use_prompt_caching)
            
            chunks = ["Streamed", " response", " chunks"]
            for chunk in chunks:
                await asyncio.sleep(0.05)
                yield Message(role="assistant", content=chunk)
            
            usage = TokenUsage(prompt_tokens=10, completion_tokens=15, total_tokens=25)
            span.set_attribute("llm.usage.total_tokens", usage.total_tokens)
            yield Message(role="assistant", content="", token_usage=usage)


class GraphState:
    def __init__(self, initial_state: Optional[Dict[str, Any]] = None):
        self._state = initial_state or {}

    def update(self, updates: Dict[str, Any]) -> None:
        self._state.update(updates)

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def snapshot(self) -> Dict[str, Any]:
        return copy.deepcopy(self._state)


class Middleware(ABC):
    @abstractmethod
    async def before_node(self, node_name: str, state: GraphState) -> None:
        pass

    @abstractmethod
    async def after_node(self, node_name: str, state: GraphState) -> None:
        pass


class Node(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def execute(self, state: GraphState) -> Dict[str, Any]:
        pass


class Graph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, List[str]] = {}
        self.middlewares: List[Middleware] = []
        self.snapshots: List[Dict[str, Any]] = []

    def add_node(self, node: Node) -> None:
        self.nodes[node.name] = node

    def add_edge(self, from_node: str, to_node: str) -> None:
        if from_node not in self.edges:
            self.edges[from_node] = []
        self.edges[from_node].append(to_node)

    def add_middleware(self, middleware: Middleware) -> None:
        self.middlewares.append(middleware)

    async def execute(self, start_node: str, initial_state: Optional[Dict[str, Any]] = None) -> GraphState:
        state = GraphState(initial_state)
        current_node: Optional[str] = start_node

        while current_node:
            self.snapshots.append(state.snapshot())
            node = self.nodes[current_node]

            for mw in self.middlewares:
                await mw.before_node(current_node, state)

            with tracer.start_as_current_span(f"graph.node.{current_node}"):
                updates = await node.execute(state)
                state.update(updates)

            for mw in self.middlewares:
                await mw.after_node(current_node, state)

            current_node = self._determine_next_node(current_node, state)

        self.snapshots.append(state.snapshot())
        return state

    def _determine_next_node(self, current_node: str, state: GraphState) -> Optional[str]:
        possible_next = self.edges.get(current_node, [])
        return possible_next[0] if possible_next else None


class LLMDirectedGraph(Graph):
    def __init__(self, llm_client: BaseInferenceClient):
        super().__init__()
        self.llm_client = llm_client

    def _determine_next_node(self, current_node: str, state: GraphState) -> Optional[str]:
        raise NotImplementedError("LLMDirectedGraph requires async node determination.")

    async def execute(self, start_node: str, initial_state: Optional[Dict[str, Any]] = None) -> GraphState:
        state = GraphState(initial_state)
        current_node: Optional[str] = start_node

        while current_node:
            self.snapshots.append(state.snapshot())
            node = self.nodes[current_node]

            for mw in self.middlewares:
                await mw.before_node(current_node, state)

            with tracer.start_as_current_span(f"graph.node.{current_node}"):
                updates = await node.execute(state)
                state.update(updates)

            for mw in self.middlewares:
                await mw.after_node(current_node, state)

            possible_next = self.edges.get(current_node, [])
            if not possible_next:
                current_node = None
            elif len(possible_next) == 1:
                current_node = possible_next[0]
            else:
                prompt = (
                    f"Current state: {json.dumps(state.snapshot())}\n"
                    f"Possible next steps: {possible_next}\n"
                    "Based on the state, output ONLY the exact name of the next step to execute."
                )
                response = await self.llm_client.generate(prompt=prompt, use_prompt_caching=True)
                chosen_node = response.content.strip()
                
                if chosen_node in possible_next:
                    current_node = chosen_node
                else:
                    current_node = possible_next[0]

        self.snapshots.append(state.snapshot())
        return state