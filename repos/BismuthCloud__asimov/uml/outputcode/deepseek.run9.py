from __future__ import annotations

import asyncio
import pathlib
import uuid
from abc import ABC, abstractmethod
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Dict,
    List,
    Optional,
    Sequence,
    Union,
    Tuple,
    Set,
    Type,
)

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
Cache = Dict[str, Any]


# ---------------------------------------------------------------------------
# Base class for all domain objects that carry Pydantic configuration
# ---------------------------------------------------------------------------
class AsimovBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class NonRetryableException(Exception):
    """An exception that should not trigger retry logic."""
    pass


# ---------------------------------------------------------------------------
# Simple enumerative helpers
# ---------------------------------------------------------------------------
class ModelFamily(BaseModel):
    name: str


class ModuleType(BaseModel):
    name: str


class TaskStatus(BaseModel):
    name: str


class SnapshotControl(BaseModel):
    name: str


class Example(BaseModel):
    choice: str
    choices: List[Dict[str, str]]
    message: str
    reasoning: str


# ---------------------------------------------------------------------------
# Execution plan supporting structures
# ---------------------------------------------------------------------------
class ExecutionStep(BaseModel):
    nodes: List[str]
    executed: List[bool] = Field(default_factory=list)
    skipped: List[bool] = Field(default_factory=list)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.executed:
            self.executed = [False] * len(self.nodes)
        if not self.skipped:
            self.skipped = [False] * len(self.nodes)


class ExecutionPlan(BaseModel):
    steps: List[ExecutionStep] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# ExecutionState
# ---------------------------------------------------------------------------
class ExecutionState(AsimovBase):
    current_plan: Optional[ExecutionPlan] = None
    execution_history: Optional[List[ExecutionPlan]] = Field(default_factory=list)
    execution_index: Optional[int] = None
    total_iterations: Optional[int] = None

    def mark_executed(self, step_index: int, node_index: int) -> None:
        if self.current_plan:
            step = self.current_plan.steps[step_index]
            step.executed[node_index] = True

    def was_executed(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan.steps:
            for idx, name in enumerate(step.nodes):
                if name == node_name and step.executed[idx]:
                    return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan.steps:
            for idx, name in enumerate(step.nodes):
                if name == node_name and step.skipped[idx]:
                    return True
        return False


# ---------------------------------------------------------------------------
# Module configuration helpers
# ---------------------------------------------------------------------------
class Middleware(ABC, AsimovBase):
    @abstractmethod
    def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        """Apply middleware logic."""
        ...


class ModuleConfig(AsimovBase):
    context: Optional[Dict[str, Any]] = None
    middlewares: Optional[List[Middleware]] = Field(default_factory=list)
    stop_on_success: bool = False
    timeout: float = 300.0


class NodeConfig(AsimovBase):
    condition: Optional[str] = None
    inputs: Optional[List[str]] = None
    max_retries: int = 0
    max_visits: Optional[int] = None
    outputs: Optional[List[str]] = None
    parallel: bool = False
    retry_from: Optional[str] = None
    retry_on_failure: bool = False


# ---------------------------------------------------------------------------
# Flow control decisions
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Agent‑driven flow control specializations
# ---------------------------------------------------------------------------
class AgentDrivenFlowDecision(FlowDecision):
    examples: Optional[List[Example]] = None


class AgentDrivenFlowControlConfig(FlowControlConfig):
    decisions: Sequence[AgentDrivenFlowDecision] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Core module classes
# ---------------------------------------------------------------------------
class AgentModule(ABC, AsimovBase):
    name: str
    config: Optional[ModuleConfig] = None
    container: Optional['CompositeModule'] = None
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = None
    input_mailboxes: Optional[List[str]] = None
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = None
    type: Optional[ModuleType] = None

    @abstractmethod
    def is_success(self, result: Dict[str, Any]) -> bool:
        ...

    @abstractmethod
    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        ...

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        result = await self.process(cache, semaphore)
        if isinstance(result, dict):
            return result
        # If it's an async generator, collect all yields (simplistic)
        results = []
        async for chunk in result:
            results.append(chunk)
        return {"collected": results}


class CompositeModule(AgentModule):
    modules: List[AgentModule] = Field(default_factory=list)
    node_config: Optional[NodeConfig] = None  # enriched by Node subclass

    async def run_module_with_concurrency_control(
        self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        async with semaphore:
            return await module.run(cache, semaphore)

    async def run_sequential_modules(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        for mod in self.modules:
            results[mod.name] = await self.run_module_with_concurrency_control(mod, cache, semaphore)
        return results

    async def run_parallel_modules(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        tasks = []
        for mod in self.modules:
            tasks.append(self.run_module_with_concurrency_control(mod, cache, semaphore))
        gathered = await asyncio.gather(*tasks)
        return {mod.name: res for mod, res in zip(self.modules, gathered)}

    async def apply_middlewares(
        self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache
    ) -> Dict[str, Any]:
        for mw in middlewares:
            data = mw.process(data, cache)
        return data

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            return await self.run_parallel_modules(cache, semaphore)
        return await self.run_sequential_modules(cache, semaphore)

    def is_success(self, result: Dict[str, Any]) -> bool:
        # Simplistic: assume success if no explicit error key
        return "error" not in result


class Node(CompositeModule):
    dependencies: Optional[List[str]] = None
    snapshot: Optional[SnapshotControl] = None
    # node_config is already inherited; type is inherited from AgentModule

    def get_nodes(self) -> Dict[str, 'Node']:
        """Return a dict of child nodes keyed by name (stub)."""
        # In a real implementation this would walk the graph; here we just return self.
        return {self.name: self}

    def set_nodes(self, nodes: Dict[str, 'Node']) -> None:
        """Inject the full node map so the node can resolve dependencies."""
        self._nodes = nodes

    async def cancel_gen(self, agen: AsyncGenerator[Any, None]) -> None:
        """Cancel an async generator."""
        await agen.aclose()

    async def cleanup(self) -> None:
        """Clean up any resources."""
        pass


# ---------------------------------------------------------------------------
# FlowControlModule
# ---------------------------------------------------------------------------
class FlowControlModule(AgentModule):
    flow_config: Optional[FlowControlConfig] = None

    def evaluate_condition(self, condition: str, cache: Cache, cache_keys: Set[str]) -> bool:
        """Evaluate a simple string condition against cache values."""
        # Minimal stub: always true if condition is truthy
        return bool(condition)

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        if not self.flow_config:
            return {"next": None}
        # Determine next node based on condition evaluations
        for decision in self.flow_config.decisions:
            if decision.condition and self.evaluate_condition(decision.condition, cache, set()):
                return {"next": decision.next_node, "cleanup": decision.cleanup_on_jump}
        return {"next": self.flow_config.default}

    def is_success(self, result: Dict[str, Any]) -> bool:
        return True

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


# ---------------------------------------------------------------------------
# AgentDirectedFlowControl
# ---------------------------------------------------------------------------
class AgentDirectedFlowControl(FlowControlModule):
    flow_config: Optional[AgentDrivenFlowControlConfig] = None
    inference_client: Any  # placeholder for actual inference client
    input_var: Optional[str] = None
    system_description: str = ""
    use_historicals: Optional[bool] = False
    voters: int = 1

    def set_attrs(self) -> None:
        """Post-init attribute derivation."""
        if self.flow_config and self.flow_config.decisions:
            # Example: pre-load something
            pass

    @staticmethod
    def most_common_string(string_list: List[str]) -> str:
        """Return the most frequent string in the list."""
        if not string_list:
            return ""
        counts: Dict[str, int] = {}
        for s in string_list:
            counts[s] = counts.get(s, 0) + 1
        return max(counts.keys(), key=lambda k: counts[k])

    async def gen(self, generation_input: Any, cache: Cache) -> AsyncGenerator[str, None]:
        """Async generator that yields strings (stub)."""
        yield "simulated_choice"

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        self.set_attrs()
        # Simplified: call gen, collect results, find decision
        choices: List[str] = []
        async for token in self.gen(self.input_var, cache):
            choices.append(token)
        final_choice = self.most_common_string(choices)
        return {"next": final_choice}


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------
class Executor(AgentModule):
    type: Optional[ModuleType] = None

    @abstractmethod
    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        ...


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------
class Task(AsimovBase):
    error: Optional[str] = None
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4)
    model_config = ConfigDict(arbitrary_types_allowed=True)
    objective: str = ""
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    status: Optional[TaskStatus] = None
    type: str = "default"

    def set_error(self, error: str) -> None:
        self.error = error

    def set_result(self, result: Any) -> None:
        self.result = result

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


# ---------------------------------------------------------------------------
# Agent (orchestrator)
# ---------------------------------------------------------------------------
class Agent(AsimovBase):
    auto_snapshot: bool = False
    cache: Optional[Cache] = None
    error_mailbox: str = ""
    execution_state: Optional[ExecutionState] = None
    graph: Optional[Dict[str, List[str]]] = None
    max_concurrent_tasks: Optional[int] = None
    max_total_iterations: Optional[int] = None
    node_results: Optional[Dict[str, Any]] = Field(default_factory=dict)
    nodes: Optional[Dict[str, Node]] = Field(default_factory=dict)
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
        """Create an execution plan from the entire graph."""
        # Stub: create a single step with all node names
        plan = ExecutionPlan()
        if self.nodes:
            step = ExecutionStep(nodes=list(self.nodes.keys()))
            plan.steps.append(step)
        self.execution_state = ExecutionState(current_plan=plan)
        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        """Create a plan starting from a specific node."""
        plan = ExecutionPlan()
        visited: Set[str] = set()
        to_visit = [start_node]
        while to_visit:
            current = to_visit.pop(0)
            if current in visited:
                continue
            visited.add(current)
            step = ExecutionStep(nodes=[current])
            plan.steps.append(step)
            if self.graph and current in self.graph:
                for neighbor in self.graph[current]:
                    to_visit.append(neighbor)
        self.execution_state = ExecutionState(current_plan=plan)
        return plan

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        """Return a tuple of node names that depend on the given node."""
        if not self.graph:
            return ()
        chains: List[str] = []
        stack = [node_name]
        while stack:
            current = stack.pop()
            chains.append(current)
            if current in self.graph:
                stack.extend(self.graph[current])
        return tuple(chains)

    def is_success(self, result: Any) -> bool:
        return result is not None and "error" not in str(result)

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if self.execution_state and self.execution_state.current_plan:
            deps = set(self.get_dependent_chains(node_name))
            for step in self.execution_state.current_plan.steps:
                for idx, name in enumerate(step.nodes):
                    if name == node_name or name in deps:
                        step.skipped[idx] = True

    def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        """Restore agent state from snapshot (stub)."""
        pass

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        """Run a single node and return its result."""
        if not self.nodes or node_name not in self.nodes:
            return {}
        node = self.nodes[node_name]
        cache = self.cache or {}
        sem = asyncio.Semaphore(self.max_concurrent_tasks or 1)
        result = await node.run(cache, sem)
        if self.node_results is not None:
            self.node_results[node_name] = result
        return result

    def run_task(self, task: Task) -> None:
        """Execute a task and update its status (stub)."""
        task.update_status(TaskStatus(name="completed"))

    def set_semaphore(self) -> None:
        """Configure the internal semaphore for concurrent execution."""
        pass

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        """Trim the execution plan up to (but not including) the given node."""
        sliced = []
        for step in execution_plan:
            if node in step.get("nodes", []):
                break
            sliced.append(step)
        return sliced

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        """Take a snapshot and return its path (stub)."""
        return pathlib.Path(f"/snapshots/{name_hint}")

    def update_dependencies(self, parent_node: str, new_node: str) -> None:
        """Add a new node as a dependent of parent_node in the graph."""
        if self.graph is None:
            self.graph = {}
        if parent_node not in self.graph:
            self.graph[parent_node] = []
        self.graph[parent_node].append(new_node)