from __future__ import annotations
import asyncio
import pathlib
from enum import Enum
from typing import Optional, List, Dict, Any, Sequence, Awaitable, AsyncGenerator
from uuid import UUID
from pydantic import BaseModel, ConfigDict, PrivateAttr

class ModelFamily(str, Enum):
    DEFAULT = "default"

class ModuleType(str, Enum):
    DEFAULT = "default"

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Cache(Dict[str, Any]):
    pass

class InferenceClient:
    pass

class NonRetryableException(Exception):
    pass

class SnapshotControl(BaseModel):
    name: str

class Example(BaseModel):
    choice: str
    choices: List[Dict[str, str]]
    message: str
    reasoning: str

class ExecutionStep(BaseModel):
    executed: List[bool]
    nodes: List[str]
    skipped: List[bool]

ExecutionPlan = List[ExecutionStep]

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
    decisions: Sequence[FlowDecision]
    default: Optional[str] = None

class AgentDrivenFlowDecision(FlowDecision):
    examples: Optional[List[Example]] = None

class AgentDrivenFlowControlConfig(FlowControlConfig):
    decisions: Sequence[AgentDrivenFlowDecision]
    default: Optional[str] = None

class ExecutionState(AsimovBase):
    current_plan: Optional[ExecutionPlan] = None
    execution_history: Optional[List[ExecutionPlan]] = None
    execution_index: Optional[int] = None
    total_iterations: Optional[int] = None

    def mark_executed(self, step_index: int, node_index: int):
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

class Task(AsimovBase):
    error: Optional[str] = None
    id: Optional[UUID] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)
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

class AgentModule(AsimovBase):
    config: Optional[ModuleConfig] = None
    container: Optional['CompositeModule'] = None
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = 0
    input_mailboxes: Optional[List[str]] = None
    name: str
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = None
    type: Optional[ModuleType] = None

    def is_success(self, result: Dict[str, Any]) -> bool:
        return True

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Awaitable[dict[str, Any]] | AsyncGenerator:
        raise NotImplementedError

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> dict[str, Any]:
        async with semaphore:
            res = self.process(cache, semaphore)
            if hasattr(res, "__aiter__"):
                last_val = {}
                async for val in res:  # type: ignore
                    if isinstance(val, dict):
                        last_val = val
                return last_val
            else:
                val = await res  # type: ignore
                if isinstance(val, dict):
                    return val
                return {}

class CompositeModule(AgentModule):
    modules: List[AgentModule] = []
    node_config: Optional[NodeConfig] = None

    def apply_middlewares(self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        for mw in middlewares:
            data = mw.process(data, cache)
        return data

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            return await self.run_parallel_modules(cache, semaphore)
        return await self.run_sequential_modules(cache, semaphore)

    async def run_module_with_concurrency_control(self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await module.run(cache, semaphore)

    async def run_parallel_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        tasks = [self.run_module_with_concurrency_control(mod, cache, semaphore) for mod in self.modules]
        results = await asyncio.gather(*tasks)
        merged = {}
        for i, res in enumerate(results):
            merged[f"module_{i}"] = res
        return merged

    async def run_sequential_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        result = {}
        for mod in self.modules:
            res = await self.run_module_with_concurrency_control(mod, cache, semaphore)
            result.update(res)
            if self.config and self.config.stop_on_success and mod.is_success(res):
                break
        return result

class Node(CompositeModule):
    dependencies: Optional[List[str]] = None
    modules: Optional[List[AgentModule]] = None
    node_config: Optional[NodeConfig] = None
    snapshot: Optional[SnapshotControl] = None
    type: Optional[ModuleType] = None
    
    _nodes_map: Dict[str, 'Node'] = PrivateAttr(default_factory=dict)

    def cancel_gen(self, agen):
        pass

    def cleanup(self):
        pass

    def get_nodes(self) -> Dict[str, 'Node']:
        return self._nodes_map

    def set_nodes(self, nodes: Dict[str, 'Node']):
        self._nodes_map = nodes

class FlowControlModule(AgentModule):
    flow_config: Optional[FlowControlConfig] = None

    def evaluate_condition(self, condition: str, cache: Cache, cache_keys: set[str]) -> bool:
        return True

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}

class AgentDirectedFlowControl(FlowControlModule):
    flow_config: Optional[AgentDrivenFlowControlConfig] = None
    inference_client: Optional[InferenceClient] = None
    input_var: Optional[str] = None
    system_description: str = ""
    use_historicals: Optional[bool] = None
    voters: int = 1

    def gen(self, generation_input: Any, cache: Cache):
        pass

    def most_common_string(self, string_list: List[str]) -> Optional[str]:
        if not string_list:
            return None
        return max(set(string_list), key=string_list.count)

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}

    def set_attrs(self):
        pass

class Executor(AgentModule):
    type: Optional[ModuleType] = None

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> dict[str, Any]:
        raise NotImplementedError

class Agent(AsimovBase):
    auto_snapshot: bool = False
    cache: Optional[Cache] = None
    error_mailbox: str = "error"
    execution_state: Optional[ExecutionState] = None
    graph: Optional[Dict[str, List[str]]] = None
    max_concurrent_tasks: Optional[int] = None
    max_total_iterations: Optional[int] = None
    node_results: Optional[Dict[str, Any]] = None
    nodes: Optional[Dict[str, 'Node']] = None
    output_mailbox: str = "output"

    def add_multiple_nodes(self, nodes: List['Node']):
        for node in nodes:
            self.add_node(node)

    def add_node(self, node: 'Node'):
        if self.nodes is None:
            self.nodes = {}
        self.nodes[node.name] = node
        if self.graph is None:
            self.graph = {}
        self.graph[node.name] = node.dependencies or []

    def compile_execution_plan(self) -> ExecutionPlan:
        return []

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        return []

    def get_dependent_chains(self, node_name: str) -> tuple[str, ...]:
        return ()

    def is_success(self, result: Any) -> bool:
        return True

    def mark_node_and_deps_as_skipped(self, node_name: str):
        if self.execution_state and self.execution_state.current_plan:
            for step in self.execution_state.current_plan:
                if node_name in step.nodes:
                    idx = step.nodes.index(node_name)
                    step.skipped[idx] = True

    def run_from_snapshot(self, snapshot_dir: pathlib.Path):
        pass

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if self.nodes and node_name in self.nodes:
            sem = self.set_semaphore()
            return await self.nodes[node_name].run(self.cache or Cache(), sem)
        return {}

    async def run_task(self, task: Task) -> None:
        pass

    def set_semaphore(self) -> asyncio.Semaphore:
        return asyncio.Semaphore(self.max_concurrent_tasks if self.max_concurrent_tasks is not None else 1)

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        sliced = []
        for step in execution_plan:
            if node in step.get("nodes", []):
                break
            sliced.append(step)
        return sliced

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        return pathlib.Path(f"{name_hint}.snapshot")

    def update_dependencies(self, parent_node: str, new_node: str):
        if self.graph is not None and parent_node in self.graph:
            if new_node not in self.graph[parent_node]:
                self.graph[parent_node].append(new_node)