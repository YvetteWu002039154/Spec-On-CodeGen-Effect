import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from opentelemetry import trace
    from opentelemetry.trace import Span, Tracer
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EdgeType(Enum):
    DEFAULT = "default"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GraphError(Exception):
    pass


class CycleDetectedError(GraphError):
    pass


class NodeNotFoundError(GraphError):
    pass


class InferenceError(Exception):
    pass


class CacheError(Exception):
    pass


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class Message:
    role: MessageRole
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cached_tokens=self.cached_tokens + other.cached_tokens,
        )


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class InferenceResponse:
    content: str
    model: str
    usage: TokenUsage
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass
class StreamChunk:
    content: str
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class GraphState:
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> "GraphState":
        import copy
        return GraphState(
            data=copy.deepcopy(self.data),
            metadata=copy.deepcopy(self.metadata),
        )

    def update(self, updates: Dict[str, Any]) -> None:
        self.data.update(updates)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class MiddlewareContext:
    def __init__(self, node_name: str, state: GraphState, inputs: Dict[str, Any]):
        self.node_name = node_name
        self.state = state
        self.inputs = inputs
        self.outputs: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self.error: Optional[Exception] = None


class Middleware(ABC):
    @abstractmethod
    async def before_node(self, ctx: MiddlewareContext) -> None:
        pass

    @abstractmethod
    async def after_node(self, ctx: MiddlewareContext) -> None:
        pass

    async def on_error(self, ctx: MiddlewareContext, error: Exception) -> None:
        pass


class LoggingMiddleware(Middleware):
    def __init__(self, logger: Optional[Any] = None):
        import logging
        self.logger = logger or logging.getLogger(__name__)

    async def before_node(self, ctx: MiddlewareContext) -> None:
        self.logger.info(f"[Graph] Starting node: {ctx.node_name}")

    async def after_node(self, ctx: MiddlewareContext) -> None:
        elapsed = (ctx.end_time or time.time()) - ctx.start_time
        self.logger.info(
            f"[Graph] Completed node: {ctx.node_name} in {elapsed:.3f}s"
        )

    async def on_error(self, ctx: MiddlewareContext, error: Exception) -> None:
        self.logger.error(
            f"[Graph] Error in node {ctx.node_name}: {error}"
        )


class TimingMiddleware(Middleware):
    def __init__(self):
        self.timings: Dict[str, List[float]] = defaultdict(list)

    async def before_node(self, ctx: MiddlewareContext) -> None:
        ctx.metadata["_timing_start"] = time.perf_counter()

    async def after_node(self, ctx: MiddlewareContext) -> None:
        start = ctx.metadata.get("_timing_start", time.perf_counter())
        elapsed = time.perf_counter() - start
        self.timings[ctx.node_name].append(elapsed)

    def get_average(self, node_name: str) -> Optional[float]:
        times = self.timings.get(node_name)
        if not times:
            return None
        return sum(times) / len(times)


class OpenTelemetryMiddleware(Middleware):
    def __init__(self, tracer_name: str = "agent_framework"):
        if OTEL_AVAILABLE:
            self.tracer: Optional[Any] = trace.get_tracer(tracer_name)
        else:
            self.tracer = None
        self._spans: Dict[str, Any] = {}

    async def before_node(self, ctx: MiddlewareContext) -> None:
        if self.tracer is None:
            return
        span = self.tracer.start_span(f"node.{ctx.node_name}")
        span.set_attribute("node.name", ctx.node_name)
        self._spans[ctx.node_name] = span

    async def after_node(self, ctx: MiddlewareContext) -> None:
        span = self._spans.pop(ctx.node_name, None)
        if span:
            span.end()

    async def on_error(self, ctx: MiddlewareContext, error: Exception) -> None:
        span = self._spans.pop(ctx.node_name, None)
        if span:
            if OTEL_AVAILABLE:
                span.record_exception(error)
                span.set_status(trace.StatusCode.ERROR, str(error))
            span.end()


# ---------------------------------------------------------------------------
# Graph Nodes
# ---------------------------------------------------------------------------

NodeFunction = Callable[[GraphState, Dict[str, Any]], Any]


class Node:
    def __init__(
        self,
        name: str,
        func: NodeFunction,
        description: str = "",
        retry_count: int = 0,
        retry_delay: float = 0.0,
        timeout: Optional[float] = None,
    ):
        self.name = name
        self.func = func
        self.description = description
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.status: NodeStatus = NodeStatus.PENDING

    async def execute(self, state: GraphState, inputs: Dict[str, Any]) -> Any:
        attempts = 0
        last_error: Optional[Exception] = None
        while attempts <= self.retry_count:
            try:
                if asyncio.iscoroutinefunction(self.func):
                    if self.timeout:
                        result = await asyncio.wait_for(
                            self.func(state, inputs), timeout=self.timeout
                        )
                    else:
                        result = await self.func(state, inputs)
                else:
                    if self.timeout:
                        loop = asyncio.get_event_loop()
                        result = await asyncio.wait_for(
                            loop.run_in_executor(None, self.func, state, inputs),
                            timeout=self.timeout,
                        )
                    else:
                        result = self.func(state, inputs)
                return result
            except Exception as e:
                last_error = e
                attempts += 1
                if attempts <= self.retry_count and self.retry_delay > 0:
                    await asyncio.sleep(self.retry_delay)
        raise last_error  # type: ignore


class ConditionalNode(Node):
    def __init__(
        self,
        name: str,
        func: NodeFunction,
        condition: Callable[[GraphState, Any], str],
        description: str = "",
        retry_count: int = 0,
        retry_delay: float = 0.0,
        timeout: Optional[float] = None,
    ):
        super().__init__(name, func, description, retry_count, retry_delay, timeout)
        self.condition = condition

    def evaluate_condition(self, state: GraphState, result: Any) -> str:
        return self.condition(state, result)


class LLMDirectedNode(Node):
    def __init__(
        self,
        name: str,
        func: NodeFunction,
        llm_client: "BaseInferenceClient",
        routing_prompt: str,
        available_routes: List[str],
        description: str = "",
        retry_count: int = 0,
        retry_delay: float = 0.0,
        timeout: Optional[float] = None,
    ):
        super().__init__(name, func, description, retry_count, retry_delay, timeout)
        self.llm_client = llm_client
        self.routing_prompt = routing_prompt
        self.available_routes = available_routes

    async def determine_next_node(self, state: GraphState, result: Any) -> str:
        messages = [
            Message(
                role=MessageRole.SYSTEM,
                content=(
                    f"You are a routing agent. Based on the current state and result, "
                    f"choose the next node from: {self.available_routes}. "
                    f"Respond with only the node name."
                ),
            ),
            Message(
                role=MessageRole.USER,
                content=(
                    f"{self.routing_prompt}\n\n"
                    f"Current state: {json.dumps(state.data, default=str)}\n"
                    f"Last result: {json.dumps(result, default=str) if result is not None else 'None'}"
                ),
            ),
        ]
        response = await self.llm_client.complete(messages)
        chosen = response.content.strip()
        if chosen in self.available_routes:
            return chosen
        return self.available_routes[0]


# ---------------------------------------------------------------------------
# Graph Edges
# ---------------------------------------------------------------------------

@dataclass
class Edge:
    source: str
    target: str
    edge_type: EdgeType = EdgeType.DEFAULT
    condition: Optional[Callable[[GraphState, Any], bool]] = None
    label: Optional[str] = None


# ---------------------------------------------------------------------------
# State Snapshot Manager
# ---------------------------------------------------------------------------

class SnapshotManager:
    def __init__(self, max_snapshots: int = 50):
        self.max_snapshots = max_snapshots
        self._snapshots: List[Tuple[str, float, GraphState]] = []

    def save(self, label: str, state: GraphState) -> str:
        snapshot_id = f"{label}_{uuid.uuid4().hex[:8]}"
        snapshot = state.snapshot()
        self._snapshots.append((snapshot_id, time.time(), snapshot))
        if len(self._snapshots) > self.max_snapshots:
            self._snapshots.pop(0)
        return snapshot_id

    def restore(self, snapshot_id: str) -> Optional[GraphState]:
        for sid, _, state in self._snapshots:
            if sid == snapshot_id:
                return state.snapshot()
        return None

    def list_snapshots(self) -> List[Tuple[str, float]]:
        return [(sid, ts) for sid, ts, _ in self._snapshots]

    def clear(self) -> None:
        self._snapshots.clear()


# ---------------------------------------------------------------------------
# Graph Execution Engine
# ---------------------------------------------------------------------------

class Graph:
    def __init__(
        self,
        name: str = "graph",
        state: Optional[GraphState] = None,
        middleware: Optional[List[Middleware]] = None,
        snapshot_manager: Optional[SnapshotManager] = None,
    ):
        self.name = name
        self.state: GraphState = state or GraphState()
        self.middleware: List[Middleware] = middleware or []
        self.snapshot_manager: SnapshotManager = snapshot_manager or SnapshotManager()
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._entry_point: Optional[str] = None
        self._end_points: Set[str] = set()
        self._execution_history: List[Dict[str, Any]] = []

    def add_node(self, node: Node) -> "Graph":
        self._nodes[node.name] = node
        return self

    def add_edge(self, edge: Edge) -> "Graph":
        if edge.source not in self._nodes:
            raise NodeNotFoundError(f"Source node '{edge.source}' not found")
        if edge.target not in self._nodes and edge.target != "__end__":
            raise NodeNotFoundError(f"Target node '{edge.target}' not found")
        self._edges.append(edge)
        return self

    def set_entry_point(self, node_name: str) -> "Graph":
        if node_name not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_name}' not found")
        self._entry_point = node_name
        return self

    def set_end_point(self, node_name: str) -> "Graph":
        self._end_points.add(node_name)
        return self

    def add_middleware(self, mw: Middleware) -> "Graph":
        self.middleware.append(mw)
        return self

    def _get_next_nodes(
        self, node_name: str, state: GraphState, result: Any
    ) -> List[str]:
        next_nodes = []
        for edge in self._edges:
            if edge.source != node_name:
                continue
            if edge.edge_type == EdgeType.DEFAULT:
                next_nodes.append(edge.target)
            elif edge.edge_type == EdgeType.CONDITIONAL:
                if edge.condition and edge.condition(state, result):
                    next_nodes.append(edge.target)
            elif edge.edge_type == EdgeType.PARALLEL:
                next_nodes.append(edge.target)
        return next_nodes

    def _detect_cycles(self) -> bool:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for edge in self._edges:
                if edge.source == node:
                    neighbor = edge.target
                    if neighbor == "__end__":
                        continue
                    if neighbor not in visited:
                        if dfs(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        return True
            rec_stack.discard(node)
            return False

        for node_name in self._nodes:
            if node_name not in visited:
                if dfs(node_name):
                    return True
        return False

    def validate(self) -> List[str]:
        errors = []
        if self._entry_point is None:
            errors.append("No entry point set")
        if self._detect_cycles():
            errors.append("Cycle detected in graph")
        return errors

    async def _run_middleware_before(self, ctx: MiddlewareContext) -> None:
        for mw in self.middleware:
            await mw.before_node(ctx)

    async def _run_middleware_after(self, ctx: MiddlewareContext) -> None:
        for mw in self.middleware:
            await mw.after_node(ctx)

    async def _run_middleware_error(
        self, ctx: MiddlewareContext, error: Exception
    ) -> None:
        for mw in self.middleware:
            await mw.on_error(ctx, error)

    async def _execute_node(
        self, node: Node, state: GraphState, inputs: Dict[str, Any]
    ) -> Any:
        ctx = MiddlewareContext(node.name, state, inputs)
        await self._run_middleware_before(ctx)
        node.status = NodeStatus.RUNNING
        try:
            result = await node.execute(state, inputs)
            node.status = NodeStatus.COMPLETED
            ctx.outputs = result if isinstance(result, dict) else {"result": result}
            ctx.end_time = time.time()
            await self._run_middleware_after(ctx)
            self._execution_history.append(
                {
                    "node": node.name,
                    "status": NodeStatus.COMPLETED.value,
                    "timestamp": ctx.end_time,
                    "duration": ctx.end_time - ctx.start_time,
                }
            )
            return result
        except Exception as e:
            node.status = NodeStatus.FAILED
            ctx.error = e
            ctx.end_time = time.time()
            await self._run_middleware_error(ctx, e)
            self._execution_history.append(
                {
                    "node": node.name,
                    "status": NodeStatus.FAILED.value,
                    "timestamp": ctx.end_time,
                    "error": str(e),
                }
            )
            raise

    async def run(
        self,
        inputs: Optional[Dict[str, Any]] = None,
        snapshot_on_complete: bool = False,
    ) -> GraphState:
        errors = self.validate()
        if errors:
            raise GraphError(f"Graph validation failed: {errors}")

        inputs = inputs or {}
        self.state.update(inputs)

        current_node_name = self._entry_point
        visited_count: Dict[str, int] = defaultdict(int)
        max_visits = 100

        while current_node_name and current_node_name != "__end__":
            if current_node_name not in self._nodes:
                raise NodeNotFoundError(f"Node '{current_node_name}' not found")

            visited_count[current_node_name] += 1
            if visited_count[current_node_name] > max_visits:
                raise GraphError(
                    f"Node '{current_node_name}' visited too many times (possible infinite loop)"
                )

            node = self._nodes[current_node_name]
            result = await self._execute_node(node, self.state, inputs)

            if isinstance(result, dict):
                self.state.update(result)

            if current_node_name in self._end_points:
                break

            if isinstance(node, LLMDirectedNode):
                next_node = await node.determine_next_node(self.state, result)
                current_node_name = next_node
            elif isinstance(node, ConditionalNode):
                route = node.evaluate_condition(self.state, result)
                current_node_name = route
            else:
                next_nodes = self._get_next_nodes(current_node_name, self.state, result)
                if not next_nodes:
                    break
                if len(next_nodes) == 1:
                    current_node_name = next_nodes[0]
                else:
                    parallel_results = await asyncio.gather(
                        *[
                            self._execute_node(
                                self._nodes[n], self.state, inputs
                            )
                            for n in next_nodes
                            if n != "__end__" and n in self._nodes
                        ],
                        return_exceptions=True,
                    )
                    for pr in parallel_results:
                        if isinstance(pr, dict):
                            self.state.update(pr)
                    break

        if snapshot_on_complete:
            self.snapshot_manager.save(f"{self.name}_complete", self.state)

        return self.state

    def get_execution_history(self) -> List[Dict[str, Any]]:
        return list(self._execution_history)

    def reset(self) -> None:
        for node in self._nodes.values():
            node.status = NodeStatus.PENDING
        self._execution_history.clear()
        self.state = GraphState()


# ---------------------------------------------------------------------------
# Graph Builder (Fluent API)
# ---------------------------------------------------------------------------

class GraphBuilder:
    def __init__(self, name: str = "graph"):
        self._graph = Graph(name=name)

    def with_state(self, state: GraphState) -> "GraphBuilder":
        self._graph.state = state
        return self

    def with_middleware(self, *middleware: Middleware) -> "GraphBuilder":
        for mw in middleware:
            self._graph.add_middleware(mw)
        return self

    def with_snapshot_manager(self, sm: SnapshotManager) -> "GraphBuilder":
        self._graph.snapshot_manager = sm
        return self

    def node(
        self,
        name: str,
        func: NodeFunction,
        description: str = "",
        retry_count: int = 0,
        retry_delay: float = 0.0,
        timeout: Optional[float] = None,
    ) -> "GraphBuilder":
        self._graph.add_node(
            Node(name, func, description, retry_count, retry_delay, timeout)
        )
        return self

    def conditional_node(
        self,
        name: str,
        func: NodeFunction,
        condition: Callable[[GraphState, Any], str],
        description: str = "",
    ) -> "GraphBuilder":
        self._graph.add_node(ConditionalNode(name, func, condition, description))
        return self

    def llm_node(
        self,
        name: str,
        func: NodeFunction,
        llm_client: "BaseInferenceClient",
        routing_prompt: str,
        available_routes: List[str],
        description: str = "",
    ) -> "GraphBuilder":
        self._graph.add_node(
            LLMDirectedNode(
                name, func, llm_client, routing_prompt, available_routes, description
            )
        )
        return self

    def edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType = EdgeType.DEFAULT,
        condition: Optional[Callable[[GraphState, Any], bool]] = None,
        label: Optional[str] = None,
    ) -> "GraphBuilder":
        self._graph.add_edge(Edge(source, target, edge_type, condition, label))
        return self

    def entry(self, node_name: str) -> "GraphBuilder":
        self._graph.set_entry_point(node_name)
        return self

    def end(self, node_name: str) -> "GraphBuilder":
        self._graph.set_end_point(node_name)
        return self

    def build(self) -> Graph:
        return self._graph


# ---------------------------------------------------------------------------
# Inference Clients
# ---------------------------------------------------------------------------

class BaseInferenceClient(ABC):
    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        enable_telemetry: bool = False,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.enable_telemetry = enable_telemetry
        self._total_usage = TokenUsage()
        self._tracer: Optional[Any] = None
        if enable_telemetry and OTEL_AVAILABLE:
            self._tracer = trace.get_tracer(f"inference.{self.__class__.__name__}")

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        pass

    def get_total_usage(self) -> TokenUsage:
        return self._total_usage

    def reset_usage(self) -> None:
        self._total_usage = TokenUsage()

    def _update_usage(self, usage: TokenUsage) -> None:
        self._total_usage = self._total_usage + usage

    def _messages_to_dicts(self, messages: List[Message]) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in messages]

    def _tools_to_dicts(
        self, tools: Optional[List[ToolDefinition]]
    ) -> Optional[List[Dict[str, Any]]]:
        if tools is None:
            return None
        return [t.to_dict() for t in tools]


class OpenAIInferenceClient(BaseInferenceClient):
    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        enable_telemetry: bool = False,
        prompt_caching: bool = False,
    ):
        super().__init__(model, api_key, base_url, timeout, max_retries, enable_telemetry)
        self.prompt_caching = prompt_caching
        self._client: Optional[Any] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        try:
            import openai
            kwargs: Dict[str, Any] = {
                "timeout": self.timeout,
                "max_retries": self.max_retries,
            }
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = openai.AsyncOpenAI(**kwargs)
        except ImportError:
            self._client = None

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        if self._client is None:
            raise InferenceError("openai package not installed")

        span = None
        if self._tracer and OTEL_AVAILABLE:
            span = self._tracer.start_span("openai.complete")

        try:
            params: Dict[str, Any] = {
                "model": self.model,
                "messages": self._messages_to_dicts(messages),
                "temperature": temperature,
            }
            if max_tokens:
                params["max_tokens"] = max_tokens
            if stop:
                params["stop"] = stop
            tools_dicts = self._tools_to_dicts(tools)
            if tools_dicts:
                params["tools"] = tools_dicts
            params.update(kwargs)

            response = await self._client.chat.completions.create(**params)
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                cached_tokens=getattr(
                    response.usage, "prompt_tokens_details", None
                ) and getattr(
                    response.usage.prompt_tokens_details, "cached_tokens", 0
                ) or 0,
            )
            self._update_usage(usage)

            choice = response.choices[0]
            tool_calls = None
            if choice.message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in choice.message.tool_calls
                ]

            return InferenceResponse(
                content=choice.message.content or "",
                model=response.model,
                usage=usage,
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason,
                raw=response.model_dump() if hasattr(response, "model_dump") else None,
            )
        except Exception as e:
            if span and OTEL_AVAILABLE:
                span.record_exception(e)
            raise InferenceError(f"OpenAI completion failed: {e}") from e
        finally:
            if span:
                span.end()

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        if self._client is None:
            raise InferenceError("openai package not installed")

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": self._messages_to_dicts(messages),
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            params["max_tokens"] = max_tokens
        if stop:
            params["stop"] = stop
        tools_dicts = self._tools_to_dicts(tools)
        if tools_dicts:
            params["tools"] = tools_dicts
        params.update(kwargs)

        try:
            async with await self._client.chat.completions.create(**params) as stream:
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    content = delta.content or ""
                    finish_reason = chunk.choices[0].finish_reason
                    yield StreamChunk(
                        content=content,
                        finish_reason=finish_reason,
                    )
        except Exception as e:
            raise InferenceError(f"OpenAI streaming failed: {e}") from e


class AnthropicInferenceClient(BaseInferenceClient):
    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        enable_telemetry: bool = False,
        prompt_caching: bool = False,
    ):
        super().__init__(model, api_key, base_url, timeout, max_retries, enable_telemetry)
        self.prompt_caching = prompt_caching
        self._client: Optional[Any] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        try:
            import anthropic
            kwargs: Dict[str, Any] = {
                "timeout": self.timeout,
                "max_retries": self.max_retries,
            }
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = anthropic.AsyncAnthropic(**kwargs)
        except ImportError:
            self._client = None

    def _convert_messages(
        self, messages: List[Message]
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        system_prompt = None
        converted = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_prompt = msg.content
            else:
                converted.append(
                    {"role": msg.role.value, "content": msg.content}
                )
        return system_prompt, converted

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        if self._client is None:
            raise InferenceError("anthropic package not installed")

        system_prompt, converted_messages = self._convert_messages(messages)

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }
        if system_prompt:
            params["system"] = system_prompt
        if stop:
            params["stop_sequences"] = stop
        if tools:
            params["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.parameters,
                }
                for t in tools
            ]
        params.update(kwargs)

        try:
            response = await self._client.messages.create(**params)
            usage = TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                cached_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            )
            self._update_usage(usage)

            content = ""
            tool_calls = None
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text
                elif hasattr(block, "type") and block.type == "tool_use":
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append(
                        {
                            "id": block.id,
                            "type": "function",
                            "function": {
                                "name": block.name,
                                "arguments": json.dumps(block.input),
                            },
                        }
                    )

            return InferenceResponse(
                content=content,
                model=response.model,
                usage=usage,
                tool_calls=tool_calls,
                finish_reason=response.stop_reason,
            )
        except Exception as e:
            raise InferenceError(f"Anthropic completion failed: {e}") from e

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        if self._client is None:
            raise InferenceError("anthropic package not installed")

        system_prompt, converted_messages = self._convert_messages(messages)

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }
        if system_prompt:
            params["system"] = system_prompt
        if stop:
            params["stop_sequences"] = stop
        params.update(kwargs)

        try:
            async with self._client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield StreamChunk(content=text)
        except Exception as e:
            raise InferenceError(f"Anthropic streaming failed: {e}") from e


class MockInferenceClient(BaseInferenceClient):
    def __init__(
        self,
        model: str = "mock-model",
        responses: Optional[List[str]] = None,
        tool_responses: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(model)
        self._responses = responses or ["Mock response"]
        self._tool_responses = tool_responses or []
        self._call_count = 0

    async def complete(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> InferenceResponse:
        idx = self._call_count % len(self._responses)
        content = self._responses[idx]
        self._call_count += 1

        usage = TokenUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
        self._update_usage(usage)

        tool_calls = None
        if self._tool_responses and tools:
            tool_calls = self._tool_responses

        return InferenceResponse(
            content=content,
            model=self.model,
            usage=usage,
            tool_calls=tool_calls,
            finish_reason="stop",
        )

    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        idx = self._call_count % len(self._responses)
        content = self._responses[idx]
        self._call_count += 1

        for char in content:
            yield StreamChunk(content=char)
            await asyncio.sleep(0)
        yield StreamChunk(content="", finish_reason="stop")


# ---------------------------------------------------------------------------
# Cache System
# ---------------------------------------------------------------------------

class BaseCache(ABC):
    def __init__(self, prefix: str = "", suffix: str = ""):
        self.prefix = prefix
        self.suffix = suffix

    def _make_key(self, key: str) -> str:
        parts = []
        if self.prefix:
            parts.append(self.prefix)
        parts.append(key)
        if self.suffix:
            parts.append(self.suffix)
        return ":".join(parts)

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
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


class InMemoryCache(BaseCache):
    def __init__(self, prefix: str = "", suffix: str = ""):
        super().__init__(prefix, suffix)
        self._store: Dict[str, Tuple[Any, Optional[float]]] = {}
        self._mailboxes: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    def _is_expired(self, key: str) -> bool:
        if key not in self._store:
            return True
        _, expiry = self._store[key]
        if expiry is None:
            return False
        return time.time() > expiry

    async def get(self, key: str) -> Optional[Any]:
        full_key = self._make_key(key)
        if self._is_expired(full_key):
            self._store.pop(full_key, None)
            return None
        value, _ = self._store[full_key]
        return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        full_key = self._make_key(key)
        expiry = time.time() + ttl if ttl else None
        self._store[full_key] = (value, expiry)

    async def delete(self, key: str) -> bool:
        full_key = self._make_key(key)
        if full_key in self._store:
            del self._store[full_key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        full_key = self._make_key(key)
        if self._is_expired(full_key):
            self._store.pop(full_key, None)
            return False
        return full_key in self._store

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        import fnmatch
        result = {}
        keys_to_delete = []
        for full_key, (value, expiry) in self._store.items():
            if expiry and time.time() > expiry:
                keys_to_delete.append(full_key)
                continue
            if fnmatch.fnmatch(full_key, pattern):
                result[full_key] = value
        for k in keys_to_delete:
            del self._store[k]
        return result

    async def clear(self) -> None:
        self._store.clear()

    async def publish(self, mailbox: str, message: Any) -> None:
        await self._mailboxes[mailbox].put(message)

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        queue = self._mailboxes[mailbox]
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=1.0)
                yield message
            except asyncio.TimeoutError:
                continue


class RedisCache(BaseCache):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "",
        suffix: str = "",
        url: Optional[str] = None,
    ):
        super().__init__(prefix, suffix)
        if not REDIS_AVAILABLE:
            raise CacheError("redis package not installed. Install with: pip install redis")
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.url = url
        self._client: Optional[Any] = None
        self._pubsub_clients: Dict[str, Any] = {}

    async def _get_client(self) -> Any:
        if self._client is None:
            if self.url:
                self._client = aioredis.from_url(self.url)
            else:
                self._client = aioredis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True,
                )
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        client = await self._get_client()
        full_key = self._make_key(key)
        try:
            value = await client.get(full_key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            raise CacheError(f"Redis get failed: {e}") from e

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        client = await self._get_client()
        full_key = self._make_key(key)
        try:
            serialized = json.dumps(value)
            if ttl:
                await client.setex(full_key, ttl, serialized)
            else:
                await client.set(full_key, serialized)
        except Exception as e:
            raise CacheError(f"Redis set failed: {e}") from e

    async def delete(self, key: str) -> bool:
        client = await self._get_client()
        full_key = self._make_key(key)
        try:
            result = await client.delete(full_key)
            return result > 0
        except Exception as e:
            raise CacheError(f"Redis delete failed: {e}") from e

    async def exists(self, key: str) -> bool:
        client = await self._get_client()
        full_key = self._make_key(key)
        try:
            return bool(await client.exists(full_key))
        except Exception as e:
            raise CacheError(f"Redis exists failed: {e}") from e

    async def get_all(self, pattern: str = "*") -> Dict[str, Any]:
        client = await self._get_client()
        try:
            keys = await client.keys(pattern)
            if not keys:
                return {}
            values = await client.mget(keys)
            result = {}
            for k, v in zip(keys, values):
                if v is not None:
                    try:
                        result[k] = json.loads(v)
                    except json.JSONDecodeError:
                        result[k] = v
            return result
        except Exception as e:
            raise CacheError(f"Redis get_all failed: {e}") from e

    async def clear(self) -> None:
        client = await self._get_client()
        try:
            if self.prefix:
                keys = await client.keys(f"{self.prefix}:*")
                if keys:
                    await client.delete(*keys)
            else:
                await client.flushdb()
        except Exception as e:
            raise CacheError(f"Redis clear failed: {e}") from e

    async def publish(self, mailbox: str, message: Any) -> None:
        client = await self._get_client()
        try:
            serialized = json.dumps(message)
            await client.publish(mailbox, serialized)
        except Exception as e:
            raise CacheError(f"Redis publish failed: {e}") from e

    async def subscribe(self, mailbox: str) -> AsyncGenerator[Any, None]:
        client = await self._get_client()
        pubsub = client.pubsub()
        try:
            await pubsub.subscribe(mailbox)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        yield json.loads(message["data"])
                    except json.JSONDecodeError:
                        yield message["data"]
        finally:
            await pubsub.unsubscribe(mailbox)
            await pubsub.close()

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Agent:
    def __init__(
        self,
        name: str,
        llm_client: BaseInferenceClient,
        tools: Optional[List[ToolDefinition]] = None,
        system_prompt: Optional[str] = None,
        cache: Optional[BaseCache] = None,
        max_iterations: int = 10,
    ):
        self.name = name
        self.llm_client = llm_client
        self.tools = tools or []
        self.system_prompt = system_prompt
        self.cache = cache
        self.max_iterations = max_iterations
        self._conversation_history: List[Message] = []
        self._tool_handlers: Dict[str, Callable] = {}

        if system_prompt:
            self._conversation_history.append(
                Message(role=MessageRole.SYSTEM, content=system_prompt)
            )

    def register_tool_handler(
        self, tool_name: str, handler: Callable
    ) -> None:
        self._tool_handlers[tool_name] = handler

    async def _execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> str:
        handler = self._tool_handlers.get(tool_name)
        if handler is None:
            return f"Error: No handler registered for tool '{tool_name}'"
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)
            return json.dumps(result, default=str)
        except Exception as e:
            return f"Error executing tool '{tool_name}': {e}"

    async def run(self, user_message: str) -> str:
        self._conversation_history.append(
            Message(role=MessageRole.USER, content=user_message)
        )

        cache_key = None
        if self.cache:
            cache_key = f"agent:{self.name}:{hash(user_message)}"
            cached = await self.cache.get(cache_key)
            if cached:
                return cached

        for _ in range(self.max_iterations):
            response = await self.llm_client.complete(
                messages=self._conversation_history,
                tools=self.tools if self.tools else None,
            )

            assistant_message = Message(
                role=MessageRole.ASSISTANT,
                content=response.content,
                tool_calls=response.tool_calls,
            )
            self._conversation_history.append(assistant_message)

            if not response.tool_calls:
                if self.cache and cache_key:
                    await self.cache.set(cache_key, response.content, ttl=3600)
                return response.content

            for tool_call in response.tool_calls:
                tool_name = tool_call["function"]["name"]
                try:
                    arguments = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    arguments = {}

                tool_result = await self._execute_tool(tool_name, arguments)
                self._conversation_history.append(
                    Message(
                        role=MessageRole.TOOL,
                        content=tool_result,
                        tool_call_id=tool_call.get("id"),
                        name=tool_name,
                    )
                )

        return "Max iterations reached without a final response."

    async def stream_run(
        self, user_message: str
    ) -> AsyncGenerator[str, None]:
        self._conversation_history.append(
            Message(role=MessageRole.USER, content=user_message)
        )

        full_content = ""
        async for chunk in self.llm_client.stream(
            messages=self._conversation_history,
            tools=self.tools if self.tools else None,
        ):
            if chunk.content:
                full_content += chunk.content
                yield chunk.content

        self._conversation_history.append(
            Message(role=MessageRole.ASSISTANT, content=full_content)
        )

    def clear_history(self) -> None:
        self._conversation_history.clear()
        if self.system_prompt:
            self._conversation_history.append(
                Message(role=MessageRole.SYSTEM, content=self.system_prompt)
            )

    def get_history(self) -> List[Message]:
        return list(self._conversation_history)


# ---------------------------------------------------------------------------
# Multi-Agent Orchestrator
# ---------------------------------------------------------------------------

class AgentOrchestrator:
    def __init__(
        self,
        cache: Optional[BaseCache] = None,
        middleware: Optional[List[Middleware]] = None,
    ):
        self._agents: Dict[str, Agent] = {}
        self.cache = cache
        self.middleware = middleware or []
        self._graphs: Dict[str, Graph] = {}

    def register_agent(self, agent: Agent) -> "AgentOrchestrator":
        self._agents[agent.name] = agent
        return self

    def register_graph(self, name: str, graph: Graph) -> "AgentOrchestrator":
        self._graphs[name] = graph
        return self

    def get_agent(self, name: str) -> Optional[Agent]:
        return self._agents.get(name)

    def get_graph(self, name: str) -> Optional[Graph]:
        return self._graphs.get(name)

    async def run_agent(self, agent_name: str, message: str) -> str:
        agent = self._agents.get(agent_name)
        if agent is None:
            raise ValueError(f"Agent '{agent_name}' not found")
        return await agent.run(message)

    async def run_graph(
        self,
        graph_name: str,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> GraphState:
        graph = self._graphs.get(graph_name)
        if graph is None:
            raise ValueError(f"Graph '{graph_name}' not found")
        return await graph.run(inputs)

    async def broadcast(
        self, message: str, agent_names: Optional[List[str]] = None
    ) -> Dict[str, str]:
        targets = agent_names or list(self._agents.keys())
        tasks = {
            name: self._agents[name].run(message)
            for name in targets
            if name in self._agents
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        return {
            name: str(result) if isinstance(result, Exception) else result
            for name, result in zip(tasks.keys(), results)
        }


# ---------------------------------------------------------------------------
# Convenience Factory Functions
# ---------------------------------------------------------------------------

def create_graph(name: str = "graph") -> GraphBuilder:
    return GraphBuilder(name=name)


def create_openai_client(
    model: str = "gpt-4o",
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> OpenAIInferenceClient:
    return OpenAIInferenceClient(model=model, api_key=api_key, **kwargs)


def create_anthropic_client(
    model: str = "claude-3-5-sonnet-20241022",
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> AnthropicInferenceClient:
    return AnthropicInferenceClient(model=model, api_key=api_key, **kwargs)


def create_mock_client(
    responses: Optional[List[str]] = None,
    **kwargs: Any,
) -> MockInferenceClient:
    return MockInferenceClient(responses=responses, **kwargs)


def create_memory_cache(prefix: str = "", suffix: str = "") -> InMemoryCache:
    return InMemoryCache(prefix=prefix, suffix=suffix)


def create_redis_cache(
    host: str = "localhost",
    port: int = 6379,
    prefix: str = "",
    url: Optional[str] = None,
    **kwargs: Any,
) -> RedisCache:
    return RedisCache(host=host, port=port, prefix=prefix, url=url, **kwargs)


def create_agent(
    name: str,
    llm_client: BaseInferenceClient,
    tools: Optional[List[ToolDefinition]] = None,
    system_prompt: Optional[str] = None,
    cache: Optional[BaseCache] = None,
) -> Agent:
    return Agent(
        name=name,
        llm_client=llm_client,
        tools=tools,
        system_prompt=system_prompt,
        cache=cache,
    )