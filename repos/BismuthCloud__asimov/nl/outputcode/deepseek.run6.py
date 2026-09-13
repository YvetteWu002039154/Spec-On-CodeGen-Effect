from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

# ------------------------------------------------------------------------------
# Graph Primitives
# ------------------------------------------------------------------------------

logger = logging.getLogger(__name__)


@dataclass
class GraphContext:
    """Carries execution-wide state, variables, and utilities for graph nodes."""

    state: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    logger: logging.Logger = field(default_factory=lambda: logger)


@dataclass
class Node:
    """
    A single node in the execution graph.

    Attributes:
        id: Unique identifier within the graph.
        task: Async callable that receives the outputs of predecessor nodes and a GraphContext.
              Signature: async def task(predecessor_outputs: Dict[str, Any], ctx: GraphContext) -> Any
        metadata: Arbitrary information attached to the node (e.g. description for LLM selection).
    """

    id: str
    task: Callable[[Dict[str, Any], GraphContext], Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Graph:
    """Defines a collection of nodes and directed edges representing a computation DAG."""

    name: str
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: List[Tuple[str, str]] = field(default_factory=list)

    def add_node(self, node: Node) -> None:
        if node.id in self.nodes:
            raise ValueError(f"Node with id '{node.id}' already exists")
        self.nodes[node.id] = node

    def add_edge(self, from_id: str, to_id: str) -> None:
        if from_id not in self.nodes:
            raise ValueError(f"Source node '{from_id}' does not exist")
        if to_id not in self.nodes:
            raise ValueError(f"Target node '{to_id}' does not exist")
        self.edges.append((from_id, to_id))

    def predecessors(self, node_id: str) -> Set[str]:
        return {src for src, dst in self.edges if dst == node_id}

    def successors(self, node_id: str) -> Set[str]:
        return {dst for src, dst in self.edges if src == node_id}

    def topological_sort(self) -> List[Set[str]]:
        """Returns a list of node-sets, each containing nodes that can be executed in parallel."""
        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}
        adj: Dict[str, Set[str]] = {nid: set() for nid in self.nodes}
        for src, dst in self.edges:
            adj[src].add(dst)
            in_degree[dst] = in_degree.get(dst, 0) + 1

        # Start with all nodes having in_degree 0
        ready = {nid for nid, deg in in_degree.items() if deg == 0}
        order = []
        while ready:
            order.append(ready.copy())
            next_ready = set()
            for nid in ready:
                for neighbor in adj[nid]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_ready.add(neighbor)
            ready = next_ready

        if sum(len(s) for s in order) != len(self.nodes):
            raise RuntimeError("Graph contains a cycle")
        return order


# ------------------------------------------------------------------------------
# Middleware support
# ------------------------------------------------------------------------------

MiddlewareHook = Callable[["str", Dict[str, Any], GraphContext], None]
"""Signature: async def hook(node_id: str, outputs: Dict[str, Any], ctx: GraphContext) -> None"""


class MiddlewareManager:
    """Manages a list of pre/post execution hooks."""

    def __init__(self):
        self._pre_hooks: List[MiddlewareHook] = []
        self._post_hooks: List[MiddlewareHook] = []

    def add_pre_hook(self, hook: MiddlewareHook) -> None:
        self._pre_hooks.append(hook)

    def add_post_hook(self, hook: MiddlewareHook) -> None:
        self._post_hooks.append(hook)

    async def execute_pre_hooks(self, node_id: str, inputs: Dict[str, Any], ctx: GraphContext) -> None:
        for hook in self._pre_hooks:
            await hook(node_id, inputs, ctx)

    async def execute_post_hooks(self, node_id: str, outputs: Dict[str, Any], ctx: GraphContext) -> None:
        for hook in self._post_hooks:
            await hook(node_id, outputs, ctx)


# ------------------------------------------------------------------------------
# State Snapshotting
# ------------------------------------------------------------------------------

@dataclass
class ExecutionSnapshot:
    """Encapsulates the state of a graph execution for save/restore."""

    node_outputs: Dict[str, Any] = field(default_factory=dict)
    executed: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ------------------------------------------------------------------------------
# Execution Engine
# ------------------------------------------------------------------------------

class ExecutionEngine:
    """
    Executes a Graph with parallel node execution (where topology allows),
    middleware, and optional OpenTelemetry tracing.
    """

    def __init__(
        self,
        middleware: Optional[MiddlewareManager] = None,
        tracer: Optional[Any] = None,  # opentelemetry.trace.Tracer
    ):
        self.middleware = middleware or MiddlewareManager()
        self.tracer = tracer
        self._snapshot: Optional[ExecutionSnapshot] = None

    @property
    def snapshot(self) -> Optional[ExecutionSnapshot]:
        return self._snapshot

    async def execute(
        self,
        graph: Graph,
        initial_context: Optional[GraphContext] = None,
        restore_from: Optional[ExecutionSnapshot] = None,
    ) -> Dict[str, Any]:
        """
        Runs all nodes in the graph following a parallel topological schedule.
        Returns a dictionary of node_id -> output.
        """
        ctx = initial_context or GraphContext()
        order = graph.topological_sort()
        outputs: Dict[str, Any] = {}
        executed: Set[str] = set()

        if restore_from:
            outputs.update(restore_from.node_outputs)
            executed.update(restore_from.executed)

        for group in order:
            # Determine which nodes in this group are still unexecuted (in case of restore)
            unexecuted = {nid for nid in group if nid not in executed}
            if not unexecuted:
                continue

            # Gather inputs for each node from its predecessors
            tasks = {}
            for nid in unexecuted:
                preds = graph.predecessors(nid)
                # For each predecessor we need its output; if missing, that's an error
                node_inputs = {}
                for pred in preds:
                    if pred not in outputs:
                        raise RuntimeError(
                            f"Missing output from predecessor '{pred}' required by node '{nid}'"
                        )
                    node_inputs[pred] = outputs[pred]
                # The node's input is a dict of {predecessor_id: output}
                tasks[nid] = self._exec_node(nid, graph.nodes[nid], node_inputs, ctx)

            # Execute concurrently
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for nid, result in zip(tasks.keys(), results):
                if isinstance(result, Exception):
                    raise result
                outputs[nid] = result
                executed.add(nid)

        self._snapshot = ExecutionSnapshot(node_outputs=outputs, executed=executed)
        return outputs

    async def _exec_node(
        self,
        node_id: str,
        node: Node,
        inputs: Dict[str, Any],
        ctx: GraphContext,
    ) -> Any:
        span_context = None
        if self.tracer:
            span = self.tracer.start_as_current_span(f"node.{node_id}")
            span.set_attribute("node.id", node_id)
            span_context = span

        try:
            # Pre hooks
            await self.middleware.execute_pre_hooks(node_id, inputs, ctx)

            # Execute node task
            result = await node.task(inputs, ctx)

            # Post hooks
            await self.middleware.execute_post_hooks(node_id, {"output": result}, ctx)

            return result
        finally:
            if span_context:
                span_context.end()


# ------------------------------------------------------------------------------
# LLM Directed Graph Execution
# ------------------------------------------------------------------------------

class AgentGraph(Graph):
    """
    A graph whose execution flow is directed by an LLM at each step.
    The LLM selects which executable node to run next based on the current state.
    """

    def __init__(
        self,
        name: str,
        llm_client: "BaseLLMClient",
        system_prompt: Optional[str] = None,
    ):
        super().__init__(name)
        self.llm_client = llm_client
        self.system_prompt = system_prompt or "You are an AI that decides which action to take next."

    async def run(
        self,
        initial_context: Optional[GraphContext] = None,
        max_steps: int = 10,
        restore_from: Optional[ExecutionSnapshot] = None,
    ) -> ExecutionSnapshot:
        """
        Run the graph by repeatedly asking the LLM to choose the next node until
        no more actions are available or max_steps is reached.
        """
        ctx = initial_context or GraphContext()
        outputs: Dict[str, Any] = {}
        executed: Set[str] = set()
        if restore_from:
            outputs.update(restore_from.node_outputs)
            executed.update(restore_from.executed)

        for _ in range(max_steps):
            # Determine currently available nodes: entry nodes (predecessors empty) and
            # nodes whose all predecessors are executed
            available = set()
            for nid in self.nodes:
                if nid in executed:
                    continue
                preds = self.predecessors(nid)
                if all(p in executed for p in preds):
                    available.add(nid)
            if not available:
                break

            # Ask LLM to choose the next node
            chosen_id = await self._llm_choose_action(available, outputs, ctx)
            if chosen_id is None or chosen_id not in available:
                raise RuntimeError(f"LLM returned invalid action: {chosen_id}")

            # Execute the chosen node
            node = self.nodes[chosen_id]
            node_inputs = {p: outputs[p] for p in self.predecessors(chosen_id)}
            # Here we use the same execution engine with middleware, but to keep it simple
            # we directly call the task (could be wrapped in engine). We'll use a basic engine.
            result = await node.task(node_inputs, ctx)
            outputs[chosen_id] = result
            executed.add(chosen_id)

            # Optionally, allow LLM to decide to stop (via "STOP" token). We'll handle that in the prompt.
            if chosen_id == "__STOP__":
                break

        return ExecutionSnapshot(node_outputs=outputs, executed=executed)

    async def _llm_choose_action(
        self, available: Set[str], outputs: Dict[str, Any], ctx: GraphContext
    ) -> str:
        """
        Sends a prompt to the LLM listing available actions with descriptions and context,
        and returns the chosen node id.
        """
        # Build a description of the current state
        state_summary = json.dumps({"outputs": outputs, "context": ctx.state}, indent=2)

        # Build a list of actions with id and description
        action_list = []
        for nid in available:
            desc = self.nodes[nid].metadata.get("description", nid)
            action_list.append(f"- {nid}: {desc}")
        action_text = "\n".join(action_list)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": (
                    "Current state:\n" + state_summary + "\n\n"
                    "Available actions:\n" + action_text + "\n\n"
                    "Choose the next action by returning its ID and nothing else."
                    " If no further actions are needed, return '__STOP__'."
                ),
            },
        ]

        response = await self.llm_client.generate(messages)
        choice = response.content.strip()
        return choice


# ------------------------------------------------------------------------------
# Inference Clients
# ------------------------------------------------------------------------------

@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    token_usage: Optional[TokenUsage] = None
    model: Optional[str] = None


class BaseLLMClient(ABC):
    """Abstract LLM client exposing generate, generate_stream, and tool_calling."""

    def __init__(
        self,
        model_name: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        cache: Optional["CacheInterface"] = None,
        cache_ttl: Optional[int] = 3600,
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.cache = cache
        self.cache_ttl = cache_ttl

    @abstractmethod
    async def generate(self, messages: List[Dict], **kwargs) -> LLMResponse:
        ...

    @abstractmethod
    async def generate_stream(self, messages: List[Dict], **kwargs) -> AsyncIterator[LLMResponse]:
        """Yields partial response chunks."""
        ...

    @abstractmethod
    async def tool_call(
        self,
        messages: List[Dict],
        tools: List[Dict],
        **kwargs,
    ) -> LLMResponse:
        ...

    def _cache_key(self, messages: List[Dict], **kwargs) -> str:
        """Generates a deterministic cache key from messages and parameters."""
        payload = {
            "model": self.model_name,
            "temperature": self.temperature,
            "messages": messages,
            "kwargs": kwargs,
        }
        return "llm:" + json.dumps(payload, sort_keys=True)

    async def _cached_generate(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """Checks cache before calling generate."""
        if self.cache is None:
            return await self.generate(messages, **kwargs)

        key = self._cache_key(messages, **kwargs)
        cached = await self.cache.get(key)
        if cached is not None:
            # Deserialize cached result
            data = json.loads(cached)
            return LLMResponse(
                content=data.get("content", ""),
                tool_calls=data.get("tool_calls"),
                token_usage=TokenUsage(**data["token_usage"]) if "token_usage" in data else None,
                model=data.get("model"),
            )

        response = await self.generate(messages, **kwargs)
        # Serialize and cache
        value = {
            "content": response.content,
            "tool_calls": response.tool_calls,
            "token_usage": {
                "prompt_tokens": response.token_usage.prompt_tokens if response.token_usage else 0,
                "completion_tokens": response.token_usage.completion_tokens if response.token_usage else 0,
                "total_tokens": response.token_usage.total_tokens if response.token_usage else 0,
            },
            "model": response.model,
        }
        await self.cache.set(key, json.dumps(value), self.cache_ttl)
        return response


# ------------------------------------------------------------------------------
# OpenAI implementation
# ------------------------------------------------------------------------------

try:
    import openai
    from openai.types.chat import ChatCompletionChunk
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

if OPENAI_AVAILABLE:

    class OpenAIClient(BaseLLMClient):
        def __init__(
            self,
            model_name: str = "gpt-4",
            api_key: Optional[str] = None,
            **kwargs,
        ):
            super().__init__(model_name, **kwargs)
            self.client = openai.AsyncOpenAI(api_key=api_key)

        async def generate(self, messages: List[Dict], **kwargs) -> LLMResponse:
            resp = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs,
            )
            choice = resp.choices[0]
            return LLMResponse(
                content=choice.message.content or "",
                tool_calls=choice.message.tool_calls,
                token_usage=TokenUsage(
                    prompt_tokens=resp.usage.prompt_tokens,
                    completion_tokens=resp.usage.completion_tokens,
                    total_tokens=resp.usage.total_tokens,
                ) if resp.usage else None,
                model=resp.model,
            )

        async def generate_stream(self, messages: List[Dict], **kwargs) -> AsyncIterator[LLMResponse]:
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
                **kwargs,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                yield LLMResponse(
                    content=delta.content or "",
                    model=chunk.model,
                )

        async def tool_call(
            self,
            messages: List[Dict],
            tools: List[Dict],
            **kwargs,
        ) -> LLMResponse:
            resp = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs,
            )
            choice = resp.choices[0]
            return LLMResponse(
                content=choice.message.content or "",
                tool_calls=choice.message.tool_calls,
                token_usage=TokenUsage(
                    prompt_tokens=resp.usage.prompt_tokens,
                    completion_tokens=resp.usage.completion_tokens,
                    total_tokens=resp.usage.total_tokens,
                ) if resp.usage else None,
                model=resp.model,
            )

else:
    OpenAIClient = None  # type: ignore


# ------------------------------------------------------------------------------
# Anthropic implementation
# ------------------------------------------------------------------------------

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

if ANTHROPIC_AVAILABLE:

    class AnthropicClient(BaseLLMClient):
        def __init__(
            self,
            model_name: str = "claude-3-opus-20240229",
            api_key: Optional[str] = None,
            **kwargs,
        ):
            super().__init__(model_name, **kwargs)
            self.client = anthropic.AsyncAnthropic(api_key=api_key)

        async def generate(self, messages: List[Dict], **kwargs) -> LLMResponse:
            # Anthropic API expects system message separately
            system = None
            if messages and messages[0]["role"] == "system":
                system = messages[0]["content"]
                messages = messages[1:]

            resp = await self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system,
                messages=messages,
                **kwargs,
            )
            return LLMResponse(
                content=resp.content[0].text,
                token_usage=TokenUsage(
                    prompt_tokens=resp.usage.input_tokens,
                    completion_tokens=resp.usage.output_tokens,
                    total_tokens=resp.usage.input_tokens + resp.usage.output_tokens,
                ),
                model=resp.model,
            )

        async def generate_stream(self, messages: List[Dict], **kwargs) -> AsyncIterator[LLMResponse]:
            system = None
            if messages and messages[0]["role"] == "system":
                system = messages[0]["content"]
                messages = messages[1:]

            async with self.client.messages.stream(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system,
                messages=messages,
                **kwargs,
            ) as stream:
                async for text_chunk in stream.text_stream:
                    yield LLMResponse(content=text_chunk, model=self.model_name)

        async def tool_call(
            self,
            messages: List[Dict],
            tools: List[Dict],
            **kwargs,
        ) -> LLMResponse:
            # Anthropic tool calling requires conversion to Anthropic tool format
            anthropic_tools = [
                {
                    "name": t["function"]["name"],
                    "description": t["function"]["description"],
                    "input_schema": t["function"]["parameters"],
                }
                for t in tools
            ]
            system = None
            if messages and messages[0]["role"] == "system":
                system = messages[0]["content"]
                messages = messages[1:]

            resp = await self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system,
                messages=messages,
                tools=anthropic_tools,
                **kwargs,
            )
            content = resp.content[0].text if resp.content[0].type == "text" else ""
            tool_calls = [
                {"name": block.name, "arguments": block.input} for block in resp.content if block.type == "tool_use"
            ]
            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                token_usage=TokenUsage(
                    prompt_tokens=resp.usage.input_tokens,
                    completion_tokens=resp.usage.output_tokens,
                    total_tokens=resp.usage.input_tokens + resp.usage.output_tokens,
                ),
                model=resp.model,
            )

else:
    AnthropicClient = None  # type: ignore


# ------------------------------------------------------------------------------
# OpenTelemetry instrumentation helper
# ------------------------------------------------------------------------------

try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


def get_tracer(name: str = "ai-agent-framework"):
    if OTEL_AVAILABLE:
        return trace.get_tracer(name)
    else:
        return None


# ------------------------------------------------------------------------------
# Caching System
# ------------------------------------------------------------------------------

class CacheInterface(ABC):
    """Abstract async cache with prefix support, pub/sub, and bulk operations."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value by key; returns None if not found."""
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store a value with optional TTL in seconds."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        """
        Get all keys matching pattern and their values.
        Implementation should handle namespace prefix implicitly.
        """
        ...

    @abstractmethod
    async def clear(self, pattern: str = "*") -> int:
        """Delete all keys matching pattern, returns number of deleted keys."""
        ...

    @abstractmethod
    async def subscribe(self, channel: str, callback: Callable[[str, Any], None]) -> None:
        """
        Subscribe to a pub/sub channel. The callback receives the channel and message.
        The subscription remains active until the client is closed.
        """
        ...

    @abstractmethod
    async def publish(self, channel: str, message: Any) -> None:
        ...


class RedisCache(CacheInterface):
    """
    Redis-backed cache with JSON serialization and prefix namespacing.
    Requires 'redis' package with async support.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        prefix: str = "agent",
        suffix: str = "",
        **redis_kwargs,
    ):
        try:
            import redis.asyncio as aioredis
        except ImportError:
            raise ImportError("RedisCache requires the 'redis' package (pip install redis)")

        self.redis = aioredis.from_url(redis_url, **redis_kwargs)
        self.prefix = prefix.rstrip(":") + ":" if prefix else ""
        self.suffix = ":" + suffix.lstrip(":") if suffix else ""
        self._pubsub = self.redis.pubsub()
        self._listener_tasks: Dict[str, asyncio.Task] = {}

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}{key}{self.suffix}"

    def _strip_prefix(self, full_key: str) -> str:
        """Removes prefix/suffix to return the logical key."""
        if self.prefix and full_key.startswith(self.prefix):
            full_key = full_key[len(self.prefix):]
        if self.suffix and full_key.endswith(self.suffix):
            full_key = full_key[: -len(self.suffix)]
        return full_key

    async def get(self, key: str) -> Optional[Any]:
        raw = await self.redis.get(self._full_key(key))
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        data = json.dumps(value)
        full_key = self._full_key(key)
        if ttl:
            await self.redis.setex(full_key, ttl, data)
        else:
            await self.redis.set(full_key, data)

    async def delete(self, key: str) -> None:
        await self.redis.delete(self._full_key(key))

    async def exists(self, key: str) -> bool:
        return await self.redis.exists(self._full_key(key)) > 0

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        full_pattern = self._full_key(pattern)
        keys = []
        cursor = 0
        while True:
            cursor, batch = await self.redis.scan(cursor=cursor, match=full_pattern)
            keys.extend(batch)
            if cursor == 0:
                break
        result = {}
        for k in keys:
            value = await self.redis.get(k)
            if value:
                result[self._strip_prefix(k.decode())] = json.loads(value)
        return result

    async def clear(self, pattern: str = "*") -> int:
        full_pattern = self._full_key(pattern)
        keys = []
        cursor = 0
        while True:
            cursor, batch = await self.redis.scan(cursor=cursor, match=full_pattern)
            keys.extend(batch)
            if cursor == 0:
                break
        if keys:
            return await self.redis.delete(*keys)
        return 0

    async def subscribe(self, channel: str, callback: Callable[[str, Any], None]) -> None:
        """Start a listener for the given channel. This method returns immediately."""
        # Ensure a single listener per channel (overwrites existing)
        if channel in self._listener_tasks:
            self._listener_tasks[channel].cancel()

        async def listener():
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(channel)
            try:
                async for msg in pubsub.listen():
                    if msg["type"] == "message":
                        data = json.loads(msg["data"])
                        await callback(channel, data)
            finally:
                await pubsub.unsubscribe(channel)

        self._listener_tasks[channel] = asyncio.create_task(listener())

    async def publish(self, channel: str, message: Any) -> None:
        data = json.dumps(message)
        await self.redis.publish(channel, data)

    async def close(self):
        """Clean up all listeners and redis connection."""
        for task in self._listener_tasks.values():
            task.cancel()
        await self.redis.close()
        if hasattr(self.redis, "connection_pool"):
            await self.redis.connection_pool.disconnect()


# ------------------------------------------------------------------------------
# Mailbox abstraction using cache pub/sub
# ------------------------------------------------------------------------------

class Mailbox:
    """Simple mailbox that uses a CacheInterface for message exchange."""

    def __init__(self, cache: CacheInterface):
        self.cache = cache

    async def send(self, address: str, message: Any) -> None:
        await self.cache.publish(address, message)

    async def receive(self, address: str, handler: Callable[[Any], None]) -> None:
        async def wrapper(channel: str, msg: Any):
            await handler(msg)

        await self.cache.subscribe(address, wrapper)


# ------------------------------------------------------------------------------
# Utility: Cached LLM Client decorator mixin
# ------------------------------------------------------------------------------

class CachedLLMClient(BaseLLMClient):
    """
    Wraps an LLM client with prompt caching using the provided CacheInterface.
    Delegates all calls to the inner client but caches generate responses.
    """

    def __init__(self, base_client: BaseLLMClient, cache: CacheInterface, cache_ttl: int = 3600):
        super().__init__(model_name=base_client.model_name,
                         temperature=base_client.temperature,
                         max_tokens=base_client.max_tokens,
                         cache=cache,
                         cache_ttl=cache_ttl)
        self._base = base_client

    async def generate(self, messages: List[Dict], **kwargs) -> LLMResponse:
        return await self._cached_generate(messages, **kwargs)

    async def generate_stream(self, messages: List[Dict], **kwargs) -> AsyncIterator[LLMResponse]:
        # Streaming is not cached
        async for chunk in self._base.generate_stream(messages, **kwargs):
            yield chunk

    async def tool_call(self, messages: List[Dict], tools: List[Dict], **kwargs) -> LLMResponse:
        # Tool calls can be cached too
        return await self._cached_generate(messages, tools=tools, **kwargs)

    async def _cached_generate(self, messages: List[Dict], **kwargs) -> LLMResponse:
        # Override to use base client's generate for caching
        if self.cache is None:
            return await self._base.generate(messages, **kwargs)

        key = self._cache_key(messages, **kwargs)
        cached = await self.cache.get(key)
        if cached is not None:
            data = json.loads(cached)
            return LLMResponse(
                content=data.get("content", ""),
                tool_calls=data.get("tool_calls"),
                token_usage=TokenUsage(**data["token_usage"]) if "token_usage" in data else None,
                model=data.get("model"),
            )

        response = await self._base.generate(messages, **kwargs)
        value = {
            "content": response.content,
            "tool_calls": response.tool_calls,
            "token_usage": {
                "prompt_tokens": response.token_usage.prompt_tokens if response.token_usage else 0,
                "completion_tokens": response.token_usage.completion_tokens if response.token_usage else 0,
                "total_tokens": response.token_usage.total_tokens if response.token_usage else 0,
            },
            "model": response.model,
        }
        await self.cache.set(key, json.dumps(value), self.cache_ttl)
        return response


# ------------------------------------------------------------------------------
# OpenTelemetry integration example (decorator)
# ------------------------------------------------------------------------------

def trace_llm_call(method_name: str):
    """
    Decorator to add OpenTelemetry spans around LLM client calls.
    Can be applied to methods of BaseLLMClient.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            tracer = get_tracer()
            if tracer is None:
                return await func(self, *args, **kwargs)
            with tracer.start_as_current_span(f"llm.{method_name}") as span:
                span.set_attribute("model", self.model_name)
                span.set_attribute("temperature", self.temperature)
                try:
                    result = await func(self, *args, **kwargs)
                    if hasattr(result, "token_usage") and result.token_usage:
                        span.set_attribute("prompt_tokens", result.token_usage.prompt_tokens)
                        span.set_attribute("completion_tokens", result.token_usage.completion_tokens)
                        span.set_attribute("total_tokens", result.token_usage.total_tokens)
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        return wrapper
    return decorator


# Apply tracing to clients if OTEL available
if OTEL_AVAILABLE and OpenAIClient:
    OpenAIClient.generate = trace_llm_call("generate")(OpenAIClient.generate)
    OpenAIClient.generate_stream = trace_llm_call("stream")(OpenAIClient.generate_stream)
    OpenAIClient.tool_call = trace_llm_call("tool_call")(OpenAIClient.tool_call)

if OTEL_AVAILABLE and AnthropicClient:
    AnthropicClient.generate = trace_llm_call("generate")(AnthropicClient.generate)
    AnthropicClient.generate_stream = trace_llm_call("stream")(AnthropicClient.generate_stream)
    AnthropicClient.tool_call = trace_llm_call("tool_call")(AnthropicClient.tool_call)


# ------------------------------------------------------------------------------
# Example run (if executed as script)
# ------------------------------------------------------------------------------

async def _example():
    # Simple graph with two parallel nodes
    async def task_a(inputs, ctx):
        return f"A( {ctx.state.get('init')} )"

    async def task_b(inputs, ctx):
        return f"B( {ctx.state.get('init')} )"

    async def task_c(inputs, ctx):
        a_out = inputs.get("a", "")
        b_out = inputs.get("b", "")
        return f"C({a_out}, {b_out})"

    g = Graph("demo")
    g.add_node(Node("a", task_a))
    g.add_node(Node("b", task_b))
    g.add_node(Node("c", task_c))
    g.add_edge("a", "c")
    g.add_edge("b", "c")

    engine = ExecutionEngine()
    ctx = GraphContext(state={"init": "start"})
    outputs = await engine.execute(g, initial_context=ctx)
    print(outputs)  # {'a': 'A( start )', 'b': 'B( start )', 'c': 'C(A( start ), B( start ))'

    # AgentGraph demonstration (requires an LLM client; not provided in example)
    pass


if __name__ == "__main__":
    asyncio.run(_example())