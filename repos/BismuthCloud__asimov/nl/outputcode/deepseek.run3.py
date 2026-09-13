import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union, Awaitable, AsyncIterator
import hashlib

import redis.asyncio as redis
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

tracer = trace.get_tracer(__name__)


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GraphError(Exception):
    pass


class CycleError(GraphError):
    pass


@dataclass
class TaskOutput:
    node_id: str
    result: Any
    status: TaskStatus
    error: Optional[Exception] = None


@dataclass
class StateSnapshot:
    task_statuses: Dict[str, TaskStatus]
    task_outputs: Dict[str, Any]
    state: Dict[str, Any]


@dataclass
class TaskNode:
    id: str
    func: Callable[..., Union[Any, Awaitable[Any]]]
    dependencies: List[str] = field(default_factory=list)

    def __hash__(self):
        return hash(self.id)


class Graph:
    def __init__(self):
        self._nodes: Dict[str, TaskNode] = {}

    def add_node(self, node: TaskNode) -> None:
        if node.id in self._nodes:
            raise GraphError(f"Node with id '{node.id}' already exists")
        self._nodes[node.id] = node

    def remove_node(self, node_id: str) -> None:
        if node_id not in self._nodes:
            raise GraphError(f"Node '{node_id}' not found")
        del self._nodes[node_id]
        for n in self._nodes.values():
            if node_id in n.dependencies:
                n.dependencies.remove(node_id)

    def get_node(self, node_id: str) -> TaskNode:
        if node_id not in self._nodes:
            raise GraphError(f"Node '{node_id}' not found")
        return self._nodes[node_id]

    def get_nodes(self) -> Dict[str, TaskNode]:
        return dict(self._nodes)

    def get_dependencies(self, node_id: str) -> List[str]:
        return self.get_node(node_id).dependencies

    def get_dependents(self, node_id: str) -> List[str]:
        return [n.id for n in self._nodes.values() if node_id in n.dependencies]

    def _has_cycle(self) -> bool:
        visited = set()
        rec_stack = set()
        for node_id in self._nodes:
            if node_id not in visited:
                if self._has_cycle_util(node_id, visited, rec_stack):
                    return True
        return False

    def _has_cycle_util(self, node_id, visited, rec_stack):
        visited.add(node_id)
        rec_stack.add(node_id)
        node = self._nodes[node_id]
        for dep in node.dependencies:
            if dep not in visited:
                if self._has_cycle_util(dep, visited, rec_stack):
                    return True
            elif dep in rec_stack:
                return True
        rec_stack.remove(node_id)
        return False

    def topological_sort(self) -> List[str]:
        if self._has_cycle():
            raise CycleError("Graph contains a cycle")
        in_degree = {nid: 0 for nid in self._nodes}
        for nid, node in self._nodes.items():
            for dep in node.dependencies:
                in_degree[nid] = in_degree.get(nid, 0) + 1
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []
        while queue:
            current = queue.pop(0)
            result.append(current)
            for dependent in self.get_dependents(current):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        if len(result) != len(self._nodes):
            raise CycleError("Graph contains unknown cycle")
        return result


class Cache(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    async def get_all(self, prefix: str = "") -> Dict[str, Any]:
        ...

    @abstractmethod
    async def clear(self, prefix: str = "") -> None:
        ...

    @abstractmethod
    async def publish(self, channel: str, message: Any) -> None:
        ...

    @abstractmethod
    async def subscribe(self, channel: str, callback: Callable[[Any], Awaitable[None]]) -> None:
        ...

    @abstractmethod
    async def unsubscribe(self, channel: str, callback: Callable[[Any], Awaitable[None]]) -> None:
        ...


class RedisCache(Cache):
    def __init__(self, redis_url: str = "redis://localhost:6379/0", namespace_prefix: str = "", namespace_suffix: str = ""):
        self._redis: redis.Redis = redis.from_url(redis_url, decode_responses=False)
        self._prefix = namespace_prefix
        self._suffix = namespace_suffix
        self._pubsub_tasks: Dict[str, asyncio.Task] = {}
        self._channel_callbacks: Dict[str, Set[Callable]] = {}

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}{key}{self._suffix}"

    async def get(self, key: str) -> Optional[Any]:
        full_key = self._full_key(key)
        data = await self._redis.get(full_key)
        if data is None:
            return None
        return json.loads(data)

    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        full_key = self._full_key(key)
        serialized = json.dumps(value, default=str)
        if ttl:
            await self._redis.setex(full_key, ttl, serialized)
        else:
            await self._redis.set(full_key, serialized)

    async def delete(self, key: str) -> None:
        full_key = self._full_key(key)
        await self._redis.delete(full_key)

    async def get_all(self, prefix: str = "") -> Dict[str, Any]:
        pattern = self._full_key(f"{prefix}*")
        keys = []
        async for key in self._redis.scan_iter(match=pattern):
            keys.append(key)
        if not keys:
            return {}
        values = await self._redis.mget(keys)
        result = {}
        for k, v in zip(keys, values):
            if v is not None:
                orig_key = k[len(self._prefix):-len(self._suffix)] if self._suffix else k[len(self._prefix):]
                result[orig_key] = json.loads(v)
        return result

    async def clear(self, prefix: str = "") -> None:
        pattern = self._full_key(f"{prefix}*")
        keys = []
        async for key in self._redis.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await self._redis.delete(*keys)

    async def publish(self, channel: str, message: Any) -> None:
        payload = json.dumps(message, default=str)
        await self._redis.publish(channel, payload)

    async def subscribe(self, channel: str, callback: Callable[[Any], Awaitable[None]]) -> None:
        if channel not in self._channel_callbacks:
            self._channel_callbacks[channel] = set()
            self._pubsub_tasks[channel] = asyncio.create_task(self._listen_channel(channel))
        self._channel_callbacks[channel].add(callback)

    async def _listen_channel(self, channel: str):
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    callbacks = self._channel_callbacks.get(channel, set())
                    for cb in callbacks:
                        await cb(data)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    async def unsubscribe(self, channel: str, callback: Callable[[Any], Awaitable[None]]) -> None:
        if channel in self._channel_callbacks:
            self._channel_callbacks[channel].discard(callback)
            if not self._channel_callbacks[channel]:
                task = self._pubsub_tasks.pop(channel, None)
                if task:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del self._channel_callbacks[channel]


class Middleware(ABC):
    @abstractmethod
    async def before_node(self, node_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def after_node(self, node_id: str, state: Dict[str, Any], result: TaskOutput) -> Dict[str, Any]:
        ...


class TelemetryMiddleware(Middleware):
    def __init__(self, service_name: str = "graph-executor"):
        self._tracer = trace.get_tracer(service_name)

    async def before_node(self, node_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        span = self._tracer.start_span(f"execute_{node_id}", kind=SpanKind.INTERNAL)
        state.setdefault("__spans__", {})[node_id] = span
        return state

    async def after_node(self, node_id: str, state: Dict[str, Any], result: TaskOutput) -> Dict[str, Any]:
        span = state.get("__spans__", {}).pop(node_id, None)
        if span:
            if result.status == TaskStatus.FAILED:
                span.set_status(Status(StatusCode.ERROR))
                if result.error:
                    span.record_exception(result.error)
            else:
                span.set_status(Status(StatusCode.OK))
            span.end()
        return state


class GraphExecutor:
    def __init__(self, graph: Graph, middlewares: Optional[List[Middleware]] = None):
        self.graph = graph
        self.middlewares = middlewares or []
        self.state: Dict[str, Any] = {}
        self._task_statuses: Dict[str, TaskStatus] = {}
        self._task_outputs: Dict[str, Any] = {}

    async def run(self, initial_state: Optional[Dict[str, Any]] = None, stream: bool = False) -> AsyncIterator[TaskOutput]:
        if initial_state:
            self.state.update(initial_state)
        for node_id in self.graph.topological_sort():
            self._task_statuses[node_id] = TaskStatus.RUNNING
            for mw in self.middlewares:
                self.state = await mw.before_node(node_id, self.state)
            node = self.graph.get_node(node_id)
            try:
                func = node.func
                if asyncio.iscoroutinefunction(func):
                    result = await func(self.state)
                else:
                    result = func(self.state)
                status = TaskStatus.COMPLETED
                error = None
            except Exception as e:
                result = None
                status = TaskStatus.FAILED
                error = e
            output = TaskOutput(node_id=node_id, result=result, status=status, error=error)
            self._task_statuses[node_id] = status
            if status == TaskStatus.COMPLETED:
                self._task_outputs[node_id] = result
            for mw in self.middlewares:
                self.state = await mw.after_node(node_id, self.state, output)
            yield output
            if status == TaskStatus.FAILED:
                raise GraphError(f"Node '{node_id}' failed: {error}")

    def snapshot(self) -> StateSnapshot:
        return StateSnapshot(
            task_statuses=dict(self._task_statuses),
            task_outputs=dict(self._task_outputs),
            state=dict(self.state),
        )

    async def restore(self, snapshot: StateSnapshot) -> None:
        self._task_statuses = dict(snapshot.task_statuses)
        self._task_outputs = dict(snapshot.task_outputs)
        self.state = dict(snapshot.state)


class Tool(ABC):
    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        ...


class InferenceClient(ABC):
    @abstractmethod
    async def generate(self, messages: List[Dict[str, str]], tools: Optional[List[Tool]] = None) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def stream_generate(self, messages: List[Dict[str, str]], tools: Optional[List[Tool]] = None) -> AsyncIterator[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_token_usage(self) -> Dict[str, int]:
        ...

    def cache_key(self, messages: List[Dict[str, str]], tools: Optional[List[Tool]]) -> str:
        content = json.dumps({"messages": messages, "tools": [t.schema() for t in tools] if tools else None}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


class DummyInferenceClient(InferenceClient):
    def __init__(self):
        self._usage = {"prompt_tokens": 0, "completion_tokens": 0}

    async def generate(self, messages: List[Dict[str, str]], tools: Optional[List[Tool]] = None) -> Dict[str, Any]:
        self._usage["prompt_tokens"] += 10
        self._usage["completion_tokens"] += 20
        return {"role": "assistant", "content": "Dummy response"}

    async def stream_generate(self, messages: List[Dict[str, str]], tools: Optional[List[Tool]] = None) -> AsyncIterator[Dict[str, Any]]:
        self._usage["prompt_tokens"] += 10
        for token in "Dummy streaming response".split():
            self._usage["completion_tokens"] += 1
            yield {"token": token}
            await asyncio.sleep(0.01)

    def get_token_usage(self) -> Dict[str, int]:
        return dict(self._usage)


class OpenAIInferenceClient(InferenceClient):
    def __init__(self, api_key: str, model: str = "gpt-4", cache: Optional[Cache] = None, telemetry_name: str = "openai-client"):
        try:
            import openai
            self._client = openai.AsyncOpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("openai package is required for OpenAIInferenceClient")
        self._model = model
        self._cache = cache
        self._usage = {"prompt_tokens": 0, "completion_tokens": 0}
        self._tracer = trace.get_tracer(telemetry_name)

    async def generate(self, messages: List[Dict[str, str]], tools: Optional[List[Tool]] = None) -> Dict[str, Any]:
        with self._tracer.start_as_current_span("openai_generate", kind=SpanKind.CLIENT) as span:
            if self._cache:
                ck = self.cache_key(messages, tools)
                cached = await self._cache.get(ck)
                if cached is not None:
                    span.set_attribute("cache.hit", True)
                    self._usage["prompt_tokens"] += cached.get("usage", {}).get("prompt_tokens", 0)
                    self._usage["completion_tokens"] += cached.get("usage", {}).get("completion_tokens", 0)
                    return cached["response"]
                span.set_attribute("cache.hit", False)
            tool_schemas = [t.schema() for t in tools] if tools else None
            kwargs = {
                "model": self._model,
                "messages": messages,
                "stream": False,
            }
            if tool_schemas:
                kwargs["tools"] = tool_schemas
            try:
                response = await self._client.chat.completions.create(**kwargs)
                usage = response.usage
                if usage:
                    self._usage["prompt_tokens"] += usage.prompt_tokens
                    self._usage["completion_tokens"] += usage.completion_tokens
                result = response.choices[0].message.model_dump()
                if self._cache:
                    cache_value = {
                        "response": result,
                        "usage": {
                            "prompt_tokens": usage.prompt_tokens if usage else 0,
                            "completion_tokens": usage.completion_tokens if usage else 0,
                        }
                    }
                    await self._cache.set(ck, cache_value)
                return result
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
                raise

    async def stream_generate(self, messages: List[Dict[str, str]], tools: Optional[List[Tool]] = None) -> AsyncIterator[Dict[str, Any]]:
        with self._tracer.start_as_current_span("openai_stream") as span:
            if self._cache:
                ck = self.cache_key(messages, tools)
                cached = await self._cache.get(ck)
                if cached is not None:
                    span.set_attribute("cache.hit", True)
                    self._usage["prompt_tokens"] += cached.get("usage", {}).get("prompt_tokens", 0)
                    self._usage["completion_tokens"] += cached.get("usage", {}).get("completion_tokens", 0)
                    full_text = cached["response"].get("content", "")
                    for chunk in full_text.split():
                        yield {"token": chunk, "role": "assistant"}
                        await asyncio.sleep(0.01)
                    return
                span.set_attribute("cache.hit", False)
            tool_schemas = [t.schema() for t in tools] if tools else None
            kwargs = {
                "model": self._model,
                "messages": messages,
                "stream": True,
            }
            if tool_schemas:
                kwargs["tools"] = tool_schemas
            try:
                stream = await self._client.chat.completions.create(**kwargs)
                collected_content = ""
                collected_usage = None
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            collected_content += delta.content
                            yield {"token": delta.content, "role": "assistant"}
                    if chunk.usage:
                        collected_usage = chunk.usage
                if collected_usage:
                    self._usage["prompt_tokens"] += collected_usage.prompt_tokens
                    self._usage["completion_tokens"] += collected_usage.completion_tokens
                if self._cache:
                    cache_value = {
                        "response": {"role": "assistant", "content": collected_content},
                        "usage": {
                            "prompt_tokens": collected_usage.prompt_tokens if collected_usage else 0,
                            "completion_tokens": collected_usage.completion_tokens if collected_usage else 0,
                        }
                    }
                    await self._cache.set(ck, cache_value)
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
                raise

    def get_token_usage(self) -> Dict[str, int]:
        return dict(self._usage)


class LLMGraphExecutor(GraphExecutor):
    def __init__(self, graph: Graph, inference_client: InferenceClient, middlewares: Optional[List[Middleware]] = None):
        super().__init__(graph, middlewares)
        self.inference_client = inference_client
        self._decision_prompt = (
            "You are a graph execution scheduler. Given the current state and the list of available nodes "
            "(nodes whose dependencies are all completed), decide which node to execute next. Reply with a JSON object "
            'containing a key "next_node" with the node ID. If no node should be executed, return "next_node": null.'
        )

    async def run(self, initial_state: Optional[Dict[str, Any]] = None, stream: bool = False) -> AsyncIterator[TaskOutput]:
        if initial_state:
            self.state.update(initial_state)
        completed = set()
        while len(completed) < len(self.graph.get_nodes()):
            available = []
            for node_id, node in self.graph.get_nodes().items():
                if node_id not in completed:
                    if all(dep in completed for dep in node.dependencies):
                        available.append(node_id)
            if not available:
                break
            if len(available) == 1:
                chosen = available[0]
            else:
                state_desc = json.dumps(self.state, default=str)
                prompt = [
                    {"role": "system", "content": self._decision_prompt},
                    {"role": "user", "content": f"State: {state_desc}\nAvailable nodes: {available}"},
                ]
                response = await self.inference_client.generate(prompt)
                try:
                    content = response.get("content", "{}")
                    decision = json.loads(content)
                    chosen = decision.get("next_node")
                except (json.JSONDecodeError, KeyError):
                    chosen = available[0]
                if chosen not in available:
                    chosen = available[0]
            self._task_statuses[chosen] = TaskStatus.RUNNING
            for mw in self.middlewares:
                self.state = await mw.before_node(chosen, self.state)
            node = self.graph.get_node(chosen)
            try:
                func = node.func
                if asyncio.iscoroutinefunction(func):
                    result = await func(self.state)
                else:
                    result = func(self.state)
                status = TaskStatus.COMPLETED
                error = None
            except Exception as e:
                result = None
                status = TaskStatus.FAILED
                error = e
            output = TaskOutput(node_id=chosen, result=result, status=status, error=error)
            self._task_statuses[chosen] = status
            if status == TaskStatus.COMPLETED:
                self._task_outputs[chosen] = result
                completed.add(chosen)
            for mw in self.middlewares:
                self.state = await mw.after_node(chosen, self.state, output)
            yield output
            if status == TaskStatus.FAILED:
                raise GraphError(f"Node '{chosen}' failed: {error}")


def snapshot_to_file(snapshot: StateSnapshot, filepath: str) -> None:
    with open(filepath, 'w') as f:
        json.dump({
            "task_statuses": {k: v.value for k, v in snapshot.task_statuses.items()},
            "task_outputs": snapshot.task_outputs,
            "state": snapshot.state,
        }, f, default=str, indent=2)


def snapshot_from_file(filepath: str) -> StateSnapshot:
    with open(filepath, 'r') as f:
        data = json.load(f)
    return StateSnapshot(
        task_statuses={k: TaskStatus(v) for k, v in data["task_statuses"].items()},
        task_outputs=data["task_outputs"],
        state=data["state"],
    )