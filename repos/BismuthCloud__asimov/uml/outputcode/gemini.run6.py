import asyncio
import enum
import pathlib
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Awaitable, Dict, List, Optional, Sequence, Set, Tuple, Union
from uuid import UUID

from pydantic import BaseModel, Field


class Cache:
    pass


class InferenceClient:
    pass


class ModelFamily(enum.Enum):
    pass


class ModuleType(enum.Enum):
    pass


class TaskStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class NonRetryableException(Exception):
    pass


class AsimovBase(BaseModel):
    model_config = {"arbitrary_types_allowed": True}


class Middleware(AsimovBase):
    def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        return data


class ModuleConfig(AsimovBase):
    context: Optional[Dict[str, Any]] = None
    middlewares: Optional[List[Middleware]] = None
    stop_on_success: bool = False
    timeout: float = 0.0


class NodeConfig(AsimovBase):
    condition: Optional[str] = None
    inputs: Optional[List[str]] = None
    max_retries: int = 0
    max_visits: Optional[int] = None
    outputs: Optional[List[str]] = None
    parallel: bool = False
    retry_from: Optional[str] = None
    retry_on_failure: bool = False


class SnapshotControl(AsimovBase):
    name: str


class Task(AsimovBase):
    error: Optional[str] = None
    id: Optional[UUID] = None
    objective: str
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    status: Optional[TaskStatus] = None
    type: str

    def set_error(self, error: str) -> None:
        self.error = error
        self.status = TaskStatus.FAILED

    def set_result(self, result: Any) -> None:
        self.result = result
        self.status = TaskStatus.COMPLETED

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


class ExecutionStep(AsimovBase):
    executed: List[bool] = Field(default_factory=list)
    nodes: List[str] = Field(default_factory=list)
    skipped: List[bool] = Field(default_factory=list)


ExecutionPlan = List[ExecutionStep]


class ExecutionState(AsimovBase):
    current_plan: Optional[ExecutionPlan] = None
    execution_history: Optional[List[ExecutionPlan]] = None
    execution_index: Optional[int] = 0
    total_iterations: Optional[int] = 0

    def mark_executed(self, step_index: int, node_index: int):
        if self.current_plan and step_index < len(self.current_plan):
            step = self.current_plan[step_index]
            if node_index < len(step.executed):
                step.executed[node_index] = True

    def was_executed(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan:
            for i, node in enumerate(step.nodes):
                if node == node_name and i < len(step.executed) and step.executed[i]:
                    return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan:
            for i, node in enumerate(step.nodes):
                if node == node_name and i < len(step.skipped) and step.skipped[i]:
                    return True
        return False


class AgentModule(AsimovBase, ABC):
    config: Optional[ModuleConfig] = None
    container: Optional['CompositeModule'] = None
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = 0
    input_mailboxes: Optional[List[str]] = None
    name: str
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = False
    type: Optional[ModuleType] = None

    def is_success(self, result: Dict[str, Any]) -> bool:
        return result.get("success", True)

    @abstractmethod
    def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Union[Awaitable[Dict[str, Any]], AsyncGenerator[Any, Any]]:
        pass

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}


class CompositeModule(AgentModule):
    modules: List[AgentModule] = Field(default_factory=list)
    node_config: Optional[NodeConfig] = None

    def apply_middlewares(self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        for mw in middlewares:
            data = mw.process(data, cache)
        return data

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            return self.run_parallel_modules(cache, semaphore)
        return self.run_sequential_modules(cache, semaphore)

    def run_module_with_concurrency_control(self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return module.run(cache, semaphore)

    def run_parallel_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}

    def run_sequential_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}


class Node(CompositeModule):
    dependencies: Optional[List[str]] = None
    modules: Optional[List[AgentModule]] = None
    node_config: Optional[NodeConfig] = None
    snapshot: Optional[SnapshotControl] = None
    type: Optional[ModuleType] = None

    def cancel_gen(self, agen: Any):
        if hasattr(agen, 'aclose'):
            asyncio.create_task(agen.aclose())

    def cleanup(self):
        pass

    def get_nodes(self):
        return self.modules

    def set_nodes(self, nodes: Dict[str, 'Node']):
        self.modules = list(nodes.values())


class Executor(AgentModule, ABC):
    type: Optional[ModuleType] = None

    @abstractmethod
    def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        pass


class FlowDecision(AsimovBase):
    cleanup_on_jump: Optional[bool] = None
    condition: Optional[str] = None
    condition_variables: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    next_node: str


class FlowControlConfig(AsimovBase):
    cleanup_on_default: bool = False
    decisions: Sequence[FlowDecision] = Field(default_factory=list)
    default: Optional[str] = None


class FlowControlModule(AgentModule):
    flow_config: Optional[FlowControlConfig] = None

    def evaluate_condition(self, condition: str, cache: Cache, cache_keys: Set[str]) -> bool:
        return True

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}

    def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Awaitable[Dict[str, Any]]:
        async def _process():
            return self.run(cache, semaphore)
        return _process()


class Example(AsimovBase):
    choice: str
    choices: List[Dict[str, str]]
    message: str
    reasoning: str


class AgentDrivenFlowDecision(FlowDecision):
    examples: Optional[List[Example]] = None


class AgentDrivenFlowControlConfig(FlowControlConfig):
    decisions: Sequence[AgentDrivenFlowDecision] = Field(default_factory=list)
    default: Optional[str] = None


class AgentDirectedFlowControl(FlowControlModule):
    flow_config: Optional[AgentDrivenFlowControlConfig] = None
    inference_client: Optional[InferenceClient] = None
    input_var: Optional[str] = None
    system_description: str = ""
    use_historicals: Optional[bool] = None
    voters: int = 1

    def gen(self, generation_input: Any, cache: Cache):
        pass

    def most_common_string(self, string_list: List[str]) -> str:
        if not string_list:
            return ""
        return max(set(string_list), key=string_list.count)

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}

    def set_attrs(self):
        pass


class Agent(AsimovBase):
    auto_snapshot: bool = False
    cache: Optional[Cache] = None
    error_mailbox: str = "error"
    execution_state: Optional[ExecutionState] = None
    graph: Optional[Dict[str, List[str]]] = None
    max_concurrent_tasks: Optional[int] = None
    max_total_iterations: Optional[int] = None
    node_results: Optional[Dict[str, Any]] = None
    nodes: Optional[Dict[str, Node]] = None
    output_mailbox: str = "output"

    def add_multiple_nodes(self, nodes: List[Node]):
        if self.nodes is None:
            self.nodes = {}
        for node in nodes:
            self.add_node(node)

    def add_node(self, node: Node):
        if self.nodes is None:
            self.nodes = {}
        self.nodes[node.name] = node

    def compile_execution_plan(self) -> ExecutionPlan:
        return []

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        return []

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        return ()

    def is_success(self, result: Any) -> bool:
        return True

    def mark_node_and_deps_as_skipped(self, node_name: str):
        pass

    def run_from_snapshot(self, snapshot_dir: pathlib.Path):
        pass

    def run_node(self, node_name: str) -> Dict[str, Any]:
        return {}

    def run_task(self, task: Task) -> None:
        pass

    def set_semaphore(self):
        pass

    def slice_before_node(self, execution_plan: List[Dict[str, Any]], node: str) -> List[Dict[str, Any]]:
        return []

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        return pathlib.Path(name_hint)

    def update_dependencies(self, parent_node: str, new_node: str):
        if self.graph is None:
            self.graph = {}
        if parent_node in self.graph:
            self.graph[parent_node].append(new_node)
        else:
            self.graph[parent_node] = [new_node]


AgentModule.model_rebuild()
CompositeModule.model_rebuild()
Node.model_rebuild()