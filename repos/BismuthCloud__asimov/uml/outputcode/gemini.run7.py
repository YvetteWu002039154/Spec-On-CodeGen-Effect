from __future__ import annotations

import asyncio
import pathlib
from abc import ABC, abstractmethod
from enum import Enum
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, Field


class ModelFamily(Enum):
    GPT = "GPT"
    CLAUDE = "CLAUDE"
    LLAMA = "LLAMA"


class ModuleType(Enum):
    EXECUTOR = "EXECUTOR"
    FLOW_CONTROL = "FLOW_CONTROL"
    NODE = "NODE"


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class NonRetryableException(Exception):
    pass


class Cache(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict)


class InferenceClient(BaseModel):
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


class Example(BaseModel):
    choice: str
    choices: List[Dict[str, str]]
    message: str
    reasoning: str


class AgentDrivenFlowDecision(FlowDecision):
    examples: Optional[List[Example]] = None


class AgentDrivenFlowControlConfig(FlowControlConfig):
    decisions: Sequence[AgentDrivenFlowDecision] = Field(default_factory=list)
    default: Optional[str] = None


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

    def set_result(self, result: Any) -> None:
        self.result = result

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


class ExecutionStep(BaseModel):
    executed: List[bool] = Field(default_factory=list)
    nodes: List[str] = Field(default_factory=list)
    skipped: List[bool] = Field(default_factory=list)


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
            if node_name in step.nodes:
                idx = step.nodes.index(node_name)
                if step.executed[idx]:
                    return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan:
            if node_name in step.nodes:
                idx = step.nodes.index(node_name)
                if step.skipped[idx]:
                    return True
        return False


class SnapshotControl(BaseModel):
    name: str


class AgentModule(AsimovBase, ABC):
    config: Optional[ModuleConfig] = None
    container: Optional[CompositeModule] = None
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = 0
    input_mailboxes: Optional[List[str]] = None
    name: str
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = None
    type: Optional[ModuleType] = None

    def is_success(self, result: Dict[str, Any]) -> bool:
        return True

    @abstractmethod
    def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Union[Awaitable[Dict[str, Any]], AsyncGenerator]:
        pass

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}


class CompositeModule(AgentModule):
    modules: List[AgentModule] = Field(default_factory=list)
    node_config: Optional[NodeConfig] = None

    def apply_middlewares(
        self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache
    ) -> Dict[str, Any]:
        for mw in middlewares:
            data = mw.process(data, cache)
        return data

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}

    def run_module_with_concurrency_control(
        self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return {}

    def run_parallel_modules(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return {}

    def run_sequential_modules(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return {}


class Node(CompositeModule):
    dependencies: Optional[List[str]] = None
    modules: Optional[List[AgentModule]] = None
    node_config: Optional[NodeConfig] = None
    snapshot: Optional[SnapshotControl] = None
    type: Optional[ModuleType] = None
    _nodes: Dict[str, Node] = Field(default_factory=dict, exclude=True)

    def cancel_gen(self, agen: Any) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def get_nodes(self) -> Dict[str, Node]:
        return self._nodes

    def set_nodes(self, nodes: Dict[str, Node]) -> None:
        self._nodes = nodes


class Executor(AgentModule):
    type: Optional[ModuleType] = None

    @abstractmethod
    def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        pass


class FlowControlModule(AgentModule):
    flow_config: Optional[FlowControlConfig] = None

    def evaluate_condition(
        self, condition: str, cache: Cache, cache_keys: Set[str]
    ) -> bool:
        return False

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}


class AgentDirectedFlowControl(FlowControlModule):
    flow_config: Optional[AgentDrivenFlowControlConfig] = None
    inference_client: Optional[InferenceClient] = None
    input_var: Optional[str] = None
    system_description: str = ""
    use_historicals: Optional[bool] = None
    voters: int = 1

    def gen(self, generation_input: Any, cache: Cache) -> Any:
        pass

    def most_common_string(self, string_list: List[str]) -> str:
        if not string_list:
            return ""
        return max(set(string_list), key=string_list.count)

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}

    def set_attrs(self) -> None:
        pass


class Agent(AsimovBase):
    auto_snapshot: bool = False
    cache: Optional[Cache] = None
    error_mailbox: str = ""
    execution_state: Optional[ExecutionState] = None
    graph: Optional[Dict[str, List[str]]] = None
    max_concurrent_tasks: Optional[int] = None
    max_total_iterations: Optional[int] = None
    node_results: Optional[Dict[str, Any]] = None
    nodes: Optional[Dict[str, Node]] = None
    output_mailbox: str = ""

    def add_multiple_nodes(self, nodes: List[Node]) -> None:
        if self.nodes is None:
            self.nodes = {}
        for node in nodes:
            self.nodes[node.name] = node

    def add_node(self, node: Node) -> None:
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

    def slice_before_node(
        self, execution_plan: List[Dict[str, Any]], node: str
    ) -> List[Dict[str, Any]]:
        return []

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        return pathlib.Path()

    def update_dependencies(self, parent_node: str, new_node: str) -> None:
        pass