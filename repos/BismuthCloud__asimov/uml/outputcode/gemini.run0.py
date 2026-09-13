from __future__ import annotations

import asyncio
import pathlib
from abc import ABC, abstractmethod
from collections import Counter
from enum import Enum
from typing import Any, AsyncGenerator, Awaitable, Dict, List, Optional, Sequence, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelFamily(Enum):
    name = "name"


class ModuleType(Enum):
    name = "name"


class TaskStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    name = "name"


class NonRetryableException(Exception):
    pass


class Cache(dict):
    pass


class InferenceClient:
    pass


class AsimovBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


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


class SnapshotControl(AsimovBase):
    name: str


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

    def mark_executed(self, step_index: int, node_index: int) -> None:
        if self.current_plan and 0 <= step_index < len(self.current_plan):
            step = self.current_plan[step_index]
            if 0 <= node_index < len(step.executed):
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


class Task(AsimovBase):
    error: Optional[str] = None
    id: Optional[UUID] = None
    objective: str
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    status: TaskStatus = TaskStatus.PENDING
    type: str

    def set_error(self, error: str) -> None:
        self.error = error
        self.status = TaskStatus.FAILED

    def set_result(self, result: Any) -> None:
        self.result = result
        self.status = TaskStatus.COMPLETED

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


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
        return result.get("status") == "success"

    @abstractmethod
    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Union[Dict[str, Any], AsyncGenerator]:
        pass

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        self.executions = (self.executions or 0) + 1
        result = await self.process(cache, semaphore)
        if isinstance(result, dict):
            return result
        return {}


class Executor(AgentModule, ABC):
    type: Optional[ModuleType] = None

    @abstractmethod
    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        pass


class CompositeModule(AgentModule):
    modules: List[AgentModule] = Field(default_factory=list)
    node_config: Optional[NodeConfig] = None

    def apply_middlewares(self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        for mw in middlewares:
            data = mw.process(data, cache)
        return data

    async def run_module_with_concurrency_control(self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        async with semaphore:
            return await module.run(cache, semaphore)

    async def run_parallel_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        tasks = [self.run_module_with_concurrency_control(m, cache, semaphore) for m in self.modules]
        results = await asyncio.gather(*tasks)
        return {"results": results}

    async def run_sequential_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        results = []
        for m in self.modules:
            res = await m.run(cache, semaphore)
            results.append(res)
            if self.config and self.config.stop_on_success and m.is_success(res):
                break
        return {"results": results}

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        self.executions = (self.executions or 0) + 1
        if self.node_config and self.node_config.parallel:
            res = await self.run_parallel_modules(cache, semaphore)
        else:
            res = await self.run_sequential_modules(cache, semaphore)
        
        if self.config and self.config.middlewares:
            res = self.apply_middlewares(self.config.middlewares, res, cache)
        return res

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


class Node(CompositeModule):
    dependencies: Optional[List[str]] = Field(default_factory=list)
    modules: Optional[List[AgentModule]] = Field(default_factory=list)
    node_config: Optional[NodeConfig] = None
    snapshot: Optional[SnapshotControl] = None
    type: Optional[ModuleType] = None
    _nodes: Dict[str, 'Node'] = Field(default_factory=dict, exclude=True)

    def cancel_gen(self, agen: Any) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def get_nodes(self) -> Dict[str, 'Node']:
        return self._nodes

    def set_nodes(self, nodes: Dict[str, 'Node']) -> None:
        self._nodes = nodes


class FlowControlModule(AgentModule):
    flow_config: FlowControlConfig

    def evaluate_condition(self, condition: str, cache: Cache, cache_keys: set[str]) -> bool:
        return True

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await self.run(cache, semaphore)

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        self.executions = (self.executions or 0) + 1
        for decision in self.flow_config.decisions:
            if decision.condition and self.evaluate_condition(decision.condition, cache, set()):
                return {"next_node": decision.next_node}
        return {"next_node": self.flow_config.default}


class AgentDirectedFlowControl(FlowControlModule):
    flow_config: AgentDrivenFlowControlConfig
    inference_client: InferenceClient
    input_var: Optional[str] = None
    system_description: str
    use_historicals: Optional[bool] = False
    voters: int = 1

    def gen(self, generation_input: Any, cache: Cache) -> Any:
        pass

    def most_common_string(self, string_list: List[str]) -> str:
        if not string_list:
            return ""
        return Counter(string_list).most_common(1)[0][0]

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        self.executions = (self.executions or 0) + 1
        return {"next_node": self.flow_config.default}

    def set_attrs(self) -> None:
        pass


class Agent(AsimovBase):
    auto_snapshot: bool = False
    cache: Optional[Cache] = None
    error_mailbox: str = "error"
    execution_state: Optional[ExecutionState] = None
    graph: Optional[Dict[str, List[str]]] = Field(default_factory=dict)
    max_concurrent_tasks: Optional[int] = 10
    max_total_iterations: Optional[int] = 100
    node_results: Optional[Dict[str, Any]] = Field(default_factory=dict)
    nodes: Optional[Dict[str, Node]] = Field(default_factory=dict)
    output_mailbox: str = "output"
    _semaphore: Optional[asyncio.Semaphore] = Field(default=None, exclude=True)

    def add_multiple_nodes(self, nodes: List[Node]) -> None:
        for node in nodes:
            self.add_node(node)

    def add_node(self, node: Node) -> None:
        if self.nodes is None:
            self.nodes = {}
        if self.graph is None:
            self.graph = {}
        self.nodes[node.name] = node
        self.graph[node.name] = node.dependencies or []

    def compile_execution_plan(self) -> ExecutionPlan:
        plan = []
        if self.nodes:
            step = ExecutionStep(
                nodes=list(self.nodes.keys()),
                executed=[False] * len(self.nodes),
                skipped=[False] * len(self.nodes)
            )
            plan.append(step)
        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        return self.compile_execution_plan()

    def get_dependent_chains(self, node_name: str) -> tuple[str, ...]:
        deps = []
        if self.graph:
            for n, d in self.graph.items():
                if node_name in d:
                    deps.append(n)
        return tuple(deps)

    def is_success(self, result: Any) -> bool:
        if isinstance(result, dict):
            return result.get("status") == "success"
        return False

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if self.execution_state and self.execution_state.current_plan:
            for step in self.execution_state.current_plan:
                if node_name in step.nodes:
                    idx = step.nodes.index(node_name)
                    step.skipped[idx] = True

    def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        pass

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if not self.nodes or node_name not in self.nodes:
            raise ValueError(f"Node {node_name} not found")
        
        node = self.nodes[node_name]
        if not self._semaphore:
            self.set_semaphore()
        if self.cache is None:
            self.cache = Cache()
            
        res = await node.run(self.cache, self._semaphore)
        
        if self.node_results is None:
            self.node_results = {}
        self.node_results[node_name] = res
        return res

    async def run_task(self, task: Task) -> None:
        task.update_status(TaskStatus.IN_PROGRESS)
        self.execution_state = ExecutionState(current_plan=self.compile_execution_plan())
        
        try:
            if self.execution_state.current_plan:
                for step_idx, step in enumerate(self.execution_state.current_plan):
                    for node_idx, node_name in enumerate(step.nodes):
                        if not step.skipped[node_idx]:
                            await self.run_node(node_name)
                            self.execution_state.mark_executed(step_idx, node_idx)
            task.set_result(self.node_results)
        except Exception as e:
            task.set_error(str(e))

    def set_semaphore(self) -> None:
        limit = self.max_concurrent_tasks if self.max_concurrent_tasks else 10
        self._semaphore = asyncio.Semaphore(limit)

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        sliced = []
        for step in execution_plan:
            if isinstance(step, dict) and node in step.get("nodes", []):
                break
            sliced.append(step)
        return sliced

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        return pathlib.Path(f"/tmp/{name_hint}_{task.id}")

    def update_dependencies(self, parent_node: str, new_node: str) -> None:
        if self.graph is not None:
            if new_node not in self.graph:
                self.graph[new_node] = []
            if parent_node not in self.graph[new_node]:
                self.graph[new_node].append(parent_node)