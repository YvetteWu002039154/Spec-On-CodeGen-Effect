from __future__ import annotations

import asyncio
import pathlib
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncGenerator, Awaitable, Dict, List, Optional, Sequence, Set, Tuple
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Cache:
    pass


class InferenceClient:
    pass


class NonRetryableException(Exception):
    pass


class ModelFamily(Enum):
    DEFAULT = "DEFAULT"


class ModuleType(Enum):
    DEFAULT = "DEFAULT"


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AsimovBase(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class SnapshotControl(AsimovBase):
    name: str


class Example(AsimovBase):
    choice: str
    choices: List[Dict[str, str]]
    message: str
    reasoning: str


class Middleware(AsimovBase):
    def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        return data


class ModuleConfig(AsimovBase):
    context: Optional[Dict[str, Any]] = None
    middlewares: Optional[List[Middleware]] = None
    stop_on_success: bool
    timeout: float


class NodeConfig(AsimovBase):
    condition: Optional[str] = None
    inputs: Optional[List[str]] = None
    max_retries: int
    max_visits: Optional[int] = None
    outputs: Optional[List[str]] = None
    parallel: bool
    retry_from: Optional[str] = None
    retry_on_failure: bool


class FlowDecision(AsimovBase):
    cleanup_on_jump: Optional[bool] = None
    condition: Optional[str] = None
    condition_variables: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    next_node: str


class FlowControlConfig(AsimovBase):
    cleanup_on_default: bool
    decisions: Sequence[FlowDecision]
    default: Optional[str] = None


class AgentDrivenFlowDecision(FlowDecision):
    examples: Optional[List[Example]] = None


class AgentDrivenFlowControlConfig(FlowControlConfig):
    decisions: Sequence[AgentDrivenFlowDecision]
    default: Optional[str] = None


class ExecutionStep(AsimovBase):
    executed: List[bool]
    nodes: List[str]
    skipped: List[bool]


ExecutionPlan = List[ExecutionStep]


class ExecutionState(AsimovBase):
    current_plan: Optional[ExecutionPlan] = None
    execution_history: Optional[List[ExecutionPlan]] = None
    execution_index: Optional[int] = None
    total_iterations: Optional[int] = None

    def mark_executed(self, step_index: int, node_index: int) -> None:
        if self.current_plan and step_index < len(self.current_plan):
            step = self.current_plan[step_index]
            if node_index < len(step.executed):
                step.executed[node_index] = True

    def was_executed(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan:
            for i, node in enumerate(step.nodes):
                if node == node_name and step.executed[i]:
                    return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan:
            for i, node in enumerate(step.nodes):
                if node == node_name and step.skipped[i]:
                    return True
        return False


class Task(AsimovBase):
    error: Optional[str] = None
    id: Optional[UUID] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)
    objective: str
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    status: TaskStatus
    type: str

    def set_error(self, error: str) -> None:
        self.error = error

    def set_result(self, result: Any) -> None:
        self.result = result

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


class AgentModule(AsimovBase):
    config: Optional[ModuleConfig] = None
    container: Optional[CompositeModule] = None
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = None
    input_mailboxes: Optional[List[str]] = None
    name: str
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = None
    type: ModuleType

    def is_success(self, result: Dict[str, Any]) -> bool:
        return True

    @abstractmethod
    def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Awaitable[Dict[str, Any]] | AsyncGenerator:
        pass

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}


class Executor(AgentModule):
    type: Optional[ModuleType] = None

    @abstractmethod
    def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        pass


class CompositeModule(AgentModule):
    modules: List[AgentModule]
    node_config: NodeConfig

    def apply_middlewares(self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        for mw in middlewares:
            data = mw.process(data, cache)
        return data

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}

    def run_module_with_concurrency_control(self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}

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

    def cancel_gen(self, agen: Any) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def get_nodes(self) -> Dict[str, Node]:
        return {}

    def set_nodes(self, nodes: Dict[str, Node]) -> None:
        pass


class FlowControlModule(AgentModule):
    flow_config: FlowControlConfig

    def evaluate_condition(self, condition: str, cache: Cache, cache_keys: Set[str]) -> bool:
        return False

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}


class AgentDirectedFlowControl(FlowControlModule):
    flow_config: AgentDrivenFlowControlConfig
    inference_client: InferenceClient
    input_var: Optional[str] = None
    system_description: str
    use_historicals: Optional[bool] = None
    voters: int

    def gen(self, generation_input: Any, cache: Cache) -> Any:
        pass

    def most_common_string(self, string_list: List[str]) -> str:
        return ""

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}

    def set_attrs(self) -> None:
        pass


class Agent(AsimovBase):
    auto_snapshot: bool
    cache: Optional[Cache] = None
    error_mailbox: str
    execution_state: Optional[ExecutionState] = None
    graph: Optional[Dict[str, List[str]]] = None
    max_concurrent_tasks: Optional[int] = None
    max_total_iterations: Optional[int] = None
    node_results: Optional[Dict[str, Any]] = None
    nodes: Optional[Dict[str, Node]] = None
    output_mailbox: str

    def add_multiple_nodes(self, nodes: List[Node]) -> None:
        pass

    def add_node(self, node: Node) -> None:
        pass

    def compile_execution_plan(self) -> ExecutionPlan:
        return []

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        return []

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        return tuple()

    def is_success(self, result: Any) -> bool:
        return True

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        pass

    def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        pass

    def run_node(self, node_name: str) -> Dict[str, Any]:
        return {}

    def run_task(self, task: Task) -> None:
        pass

    def set_semaphore(self) -> None:
        pass

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        return []

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        return pathlib.Path()

    def update_dependencies(self, parent_node: str, new_node: str) -> None:
        pass


AgentModule.model_rebuild()
CompositeModule.model_rebuild()
Node.model_rebuild()