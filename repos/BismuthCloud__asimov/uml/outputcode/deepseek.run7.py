from __future__ import annotations

import abc
import asyncio
import enum
import pathlib
import uuid
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Set,
)

# ---------------------------------------------------------------------------
# Placeholder / minimal classes for external types
# ---------------------------------------------------------------------------

class AsimovBase:
    model_config: Dict[str, Any] = {}

class Cache:
    pass

# ExecutionStep
class ExecutionStep:
    def __init__(self, nodes: List[str]) -> None:
        self.nodes: List[str] = nodes
        self.executed: List[bool] = [False] * len(nodes)
        self.skipped: List[bool] = [False] * len(nodes)

# ExecutionPlan
class ExecutionPlan:
    def __init__(self, steps: List[ExecutionStep] = None) -> None:
        self.steps: List[ExecutionStep] = steps or []

# TaskStatus
class TaskStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    # name attribute is available via enum member's .name

# ModuleType
class ModuleType(enum.Enum):
    AGENT = "agent"
    FLOW_CONTROL = "flow_control"
    EXECUTOR = "executor"
    # others as needed

# ModelFamily (placeholder)
class ModelFamily(enum.Enum):
    GPT = "gpt"
    CLAUDE = "claude"

# ---------------------------------------------------------------------------
# Base configuration / leaf classes
# ---------------------------------------------------------------------------

class NodeConfig(AsimovBase):
    def __init__(
        self,
        condition: Optional[str] = None,
        inputs: Optional[List[str]] = None,
        max_retries: int = 0,
        max_visits: Optional[int] = None,
        outputs: Optional[List[str]] = None,
        parallel: bool = False,
        retry_from: Optional[str] = None,
        retry_on_failure: bool = False,
    ) -> None:
        self.condition = condition
        self.inputs = inputs
        self.max_retries = max_retries
        self.max_visits = max_visits
        self.outputs = outputs
        self.parallel = parallel
        self.retry_from = retry_from
        self.retry_on_failure = retry_on_failure

class ModuleConfig(AsimovBase):
    def __init__(
        self,
        context: Optional[Dict[str, Any]] = None,
        middlewares: Optional[List[Middleware]] = None,
        stop_on_success: bool = False,
        timeout: float = 60.0,
    ) -> None:
        self.context = context
        self.middlewares = middlewares or []
        self.stop_on_success = stop_on_success
        self.timeout = timeout

class Middleware(AsimovBase):
    def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        return data

class SnapshotControl:
    def __init__(self, name: str) -> None:
        self.name = name

class NonRetryableException(Exception):
    pass

# ---------------------------------------------------------------------------
# ExecutionState
# ---------------------------------------------------------------------------

class ExecutionState(AsimovBase):
    def __init__(
        self,
        current_plan: Optional[ExecutionPlan] = None,
        execution_history: Optional[List[ExecutionPlan]] = None,
        execution_index: Optional[int] = None,
        total_iterations: Optional[int] = None,
    ) -> None:
        self.current_plan = current_plan
        self.execution_history = execution_history or []
        self.execution_index = execution_index
        self.total_iterations = total_iterations

    def mark_executed(self, step_index: int, node_index: int) -> None:
        if self.current_plan and step_index < len(self.current_plan.steps):
            self.current_plan.steps[step_index].executed[node_index] = True

    def was_executed(self, node_name: str) -> bool:
        for step in self.current_plan.steps if self.current_plan else []:
            if node_name in step.nodes:
                idx = step.nodes.index(node_name)
                return step.executed[idx]
        return False

    def was_skipped(self, node_name: str) -> bool:
        for step in self.current_plan.steps if self.current_plan else []:
            if node_name in step.nodes:
                idx = step.nodes.index(node_name)
                return step.skipped[idx]
        return False

# ---------------------------------------------------------------------------
# Flow control basics
# ---------------------------------------------------------------------------

class FlowDecision(AsimovBase):
    def __init__(
        self,
        cleanup_on_jump: Optional[bool] = None,
        condition: Optional[str] = None,
        condition_variables: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        next_node: str = "",
    ) -> None:
        self.cleanup_on_jump = cleanup_on_jump
        self.condition = condition
        self.condition_variables = condition_variables
        self.metadata = metadata
        self.next_node = next_node

class FlowControlConfig(AsimovBase):
    def __init__(
        self,
        cleanup_on_default: bool = False,
        decisions: Sequence[FlowDecision] = (),
        default: Optional[str] = None,
    ) -> None:
        self.cleanup_on_default = cleanup_on_default
        self.decisions = list(decisions)
        self.default = default

# ---------------------------------------------------------------------------
# Agent modules
# ---------------------------------------------------------------------------

class AgentModule(AsimovBase, abc.ABC):
    def __init__(
        self,
        name: str,
        type: Optional[ModuleType] = None,
        config: Optional[ModuleConfig] = None,
        container: Optional[CompositeModule] = None,
        dependencies: Optional[List[str]] = None,
        executions: Optional[int] = None,
        input_mailboxes: Optional[List[str]] = None,
        output_mailbox: Optional[str] = None,
        trace: Optional[bool] = None,
    ) -> None:
        self.name = name
        self.type = type
        self.config = config or ModuleConfig()
        self.container = container
        self.dependencies = dependencies or []
        self.executions = executions
        self.input_mailboxes = input_mailboxes or []
        self.output_mailbox = output_mailbox
        self.trace = trace

    @abc.abstractmethod
    def is_success(self, result: Dict[str, Any]) -> bool:
        ...

    @abc.abstractmethod
    def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Awaitable[dict[str, Any]] | AsyncGenerator:
        ...

    def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        # Consume async generator or await coroutine; placeholder
        return {}


class Executor(AgentModule, abc.ABC):
    def __init__(self, name: str, type: Optional[ModuleType] = None, **kwargs) -> None:
        super().__init__(name=name, type=type or ModuleType.EXECUTOR, **kwargs)

    @abc.abstractmethod
    def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        ...


class FlowControlModule(AgentModule):
    def __init__(self, name: str, flow_config: FlowControlConfig, **kwargs) -> None:
        super().__init__(name=name, type=ModuleType.FLOW_CONTROL, **kwargs)
        self.flow_config = flow_config

    def evaluate_condition(
        self, condition: str, cache: Cache, cache_keys: Set[str]
    ) -> bool:
        # Stub: always false
        return False

    def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        # Implementation would evaluate conditions and route; placeholder
        return {}


class CompositeModule(AgentModule):
    def __init__(
        self,
        name: str,
        modules: Optional[List[AgentModule]] = None,
        node_config: Optional[NodeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(name=name, **kwargs)
        self.modules = modules or []
        self.node_config = node_config

    def apply_middlewares(
        self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache
    ) -> Dict[str, Any]:
        for mw in middlewares:
            data = mw.process(data, cache)
        return data

    def run_module_with_concurrency_control(
        self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return module.run(cache, semaphore)

    def run_parallel_modules(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        # Placeholder: run modules concurrently
        return {}

    def run_sequential_modules(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        for module in self.modules:
            self.run_module_with_concurrency_control(module, cache, semaphore)
        return {}

    def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            return self.run_parallel_modules(cache, semaphore)
        else:
            return self.run_sequential_modules(cache, semaphore)


# ---------------------------------------------------------------------------
# Node (a CompositeModule with extra graph abilities)
# ---------------------------------------------------------------------------

class Node(CompositeModule):
    def __init__(
        self,
        name: str,
        dependencies: Optional[List[str]] = None,
        modules: Optional[List[AgentModule]] = None,
        node_config: Optional[NodeConfig] = None,
        snapshot: Optional[SnapshotControl] = None,
        type: Optional[ModuleType] = None,
        **kwargs,
    ) -> None:
        super().__init__(name=name, modules=modules, node_config=node_config, type=type, **kwargs)
        self.dependencies = dependencies or []
        self.snapshot = snapshot

    def cancel_gen(self, agen: AsyncGenerator) -> None:
        # Placeholder: close async generator
        pass

    def cleanup(self) -> None:
        pass

    def get_nodes(self) -> Dict[str, Node]:
        # If used as a sub-graph composed of nodes, placeholder
        return {}

    def set_nodes(self, nodes: Dict[str, Node]) -> None:
        pass


# ---------------------------------------------------------------------------
# Agent-Directed Flow Control
# ---------------------------------------------------------------------------

class Example:
    def __init__(
        self,
        choice: str,
        choices: List[Dict[str, str]],
        message: str,
        reasoning: str,
    ) -> None:
        self.choice = choice
        self.choices = choices
        self.message = message
        self.reasoning = reasoning


class AgentDrivenFlowDecision(FlowDecision):
    def __init__(
        self,
        examples: Optional[List[Example]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.examples = examples or []


class AgentDrivenFlowControlConfig(FlowControlConfig):
    def __init__(
        self,
        decisions: Sequence[AgentDrivenFlowDecision] = (),
        default: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(decisions=decisions, default=default, **kwargs)


class AgentDirectedFlowControl(FlowControlModule):
    def __init__(
        self,
        name: str,
        flow_config: AgentDrivenFlowControlConfig,
        inference_client: Any = None,
        input_var: Optional[str] = None,
        system_description: str = "",
        use_historicals: Optional[bool] = None,
        voters: int = 1,
        **kwargs,
    ) -> None:
        super().__init__(name=name, flow_config=flow_config, **kwargs)
        self.inference_client = inference_client
        self.input_var = input_var
        self.system_description = system_description
        self.use_historicals = use_historicals
        self.voters = voters

    def gen(self, generation_input: Any, cache: Cache) -> Any:
        return None

    def most_common_string(self, string_list: List[str]) -> str:
        if not string_list:
            return ""
        return max(set(string_list), key=string_list.count)

    def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        # Use flow_config, generate decisions, etc.
        return {}

    def set_attrs(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

class Task(AsimovBase):
    def __init__(
        self,
        objective: str = "",
        type: str = "default",
        params: Optional[Dict[str, Any]] = None,
        id: Optional[uuid.UUID] = None,
        status: TaskStatus = TaskStatus.PENDING,
        error: Optional[str] = None,
        result: Optional[Any] = None,
        model_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.id = id or uuid.uuid4()
        self.objective = objective
        self.type = type
        self.params = params or {}
        self.status = status
        self.error = error
        self.result = result
        self.model_config = model_config or {}

    def set_error(self, error: str) -> None:
        self.error = error
        self.status = TaskStatus.ERROR

    def set_result(self, result: Any) -> None:
        self.result = result
        self.status = TaskStatus.SUCCESS

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


# ---------------------------------------------------------------------------
# Agent (the top-level orchestrator)
# ---------------------------------------------------------------------------

class Agent(AsimovBase):
    def __init__(
        self,
        auto_snapshot: bool = False,
        cache: Optional[Cache] = None,
        error_mailbox: str = "",
        execution_state: Optional[ExecutionState] = None,
        graph: Optional[Dict[str, List[str]]] = None,
        max_concurrent_tasks: Optional[int] = None,
        max_total_iterations: Optional[int] = None,
        node_results: Optional[Dict[str, Any]] = None,
        nodes: Optional[Dict[str, Node]] = None,
        output_mailbox: str = "",
    ) -> None:
        self.auto_snapshot = auto_snapshot
        self.cache = cache or Cache()
        self.error_mailbox = error_mailbox
        self.execution_state = execution_state or ExecutionState()
        self.graph = graph or {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_total_iterations = max_total_iterations
        self.node_results = node_results or {}
        self.nodes = nodes or {}
        self.output_mailbox = output_mailbox

    def add_multiple_nodes(self, nodes: List[Node]) -> None:
        for node in nodes:
            self.add_node(node)

    def add_node(self, node: Node) -> None:
        self.nodes[node.name] = node
        # Update graph structure if node has dependencies
        for dep in node.dependencies:
            self.graph.setdefault(dep, []).append(node.name)

    def compile_execution_plan(self) -> ExecutionPlan:
        # Stub: create a simple plan from all nodes
        steps = [ExecutionStep(list(self.nodes.keys()))]
        return ExecutionPlan(steps)

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        # Stub: sub-graph plan starting from start_node
        steps = [ExecutionStep([start_node])]
        return ExecutionPlan(steps)

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        return ()

    @staticmethod
    def is_success(result: Dict[str, Any]) -> bool:
        return bool(result.get("success", False))

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        pass

    def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        pass

    def run_node(self, node_name: str) -> Dict[str, Any]:
        node = self.nodes.get(node_name)
        if not node:
            return {}
        # Simulate running the node (requires cache and semaphore)
        # Placeholder
        return {}

    def run_task(self, task: Task) -> None:
        pass

    def set_semaphore(self) -> None:
        pass

    def slice_before_node(
        self, execution_plan: List[dict], node: str
    ) -> List[dict]:
        return []

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        # Stub: return simulated snapshot path
        return pathlib.Path(f"/snapshots/{task.id}_{name_hint}.snap")

    def update_dependencies(self, parent_node: str, new_node: str) -> None:
        if parent_node in self.graph:
            self.graph[parent_node].append(new_node)
        else:
            self.graph[parent_node] = [new_node]