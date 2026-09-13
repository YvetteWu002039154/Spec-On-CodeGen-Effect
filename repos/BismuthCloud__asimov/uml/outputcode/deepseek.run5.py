from __future__ import annotations

import asyncio
import pathlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)
from uuid import UUID


# ---------------------------------------------------------------------------
# Placeholder types – provided by other parts of the system
# ---------------------------------------------------------------------------

class Cache:
    """External cache abstraction."""
    pass


class InferenceClient:
    """External LLM inference client."""
    pass


class ExecutionPlan:
    """Represents a compiled execution plan."""
    pass


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

@dataclass
class ModelFamily:
    name: str


@dataclass
class ModuleType:
    name: str


@dataclass
class TaskStatus:
    name: str


@dataclass
class SnapshotControl:
    name: str


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

@dataclass
class AsimovBase:
    model_config: Dict[str, Any] = field(default_factory=dict)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # preserver default field order for dataclasses
        cls.__annotations__ = getattr(cls, '__annotations__', {})


# Note: using @dataclass inheritance requires careful field ordering.
# We'll manually declare __init__ in the following classes to keep the
# same attribute order and defaults as in the diagram.

# ---------------------------------------------------------------------------
# Graph – Core
# ---------------------------------------------------------------------------

class Middleware(ABC, AsimovBase):
    """Base middleware processor."""
    def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        raise NotImplementedError


@dataclass
class NodeConfig(AsimovBase):
    condition: Optional[str] = None
    inputs: Optional[List[str]] = None
    max_retries: int = 0
    max_visits: Optional[int] = None
    outputs: Optional[List[str]] = None
    parallel: bool = False
    retry_from: Optional[str] = None
    retry_on_failure: bool = False


@dataclass
class ModuleConfig(AsimovBase):
    context: Optional[Dict[str, Any]] = None
    middlewares: Optional[List[Middleware]] = None
    stop_on_success: bool = False
    timeout: float = 60.0


@dataclass
class ExecutionStep:
    executed: List[bool] = field(default_factory=list)
    nodes: List[str] = field(default_factory=list)
    skipped: List[bool] = field(default_factory=list)


@dataclass
class ExecutionState(AsimovBase):
    current_plan: Optional[ExecutionPlan] = None
    execution_history: Optional[List[ExecutionPlan]] = None
    execution_index: Optional[int] = None
    total_iterations: Optional[int] = None

    def mark_executed(self, step_index: int, node_index: int) -> None:
        # update the plan's step tracking – stub
        pass

    def was_executed(self, node_name: str) -> bool:
        # check history – stub
        return False

    def was_skipped(self, node_name: str) -> bool:
        # check skipped flags – stub
        return False


class NonRetryableException(Exception):
    """Exception that should not trigger retry logic."""
    pass


# Forward declarations for circular references
class AgentModule(AsimovBase):
    config: Optional[ModuleConfig] = None
    container: Optional['CompositeModule'] = None
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = None
    input_mailboxes: Optional[List[str]] = None
    name: str = ""
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = None
    type: Optional[ModuleType] = None

    def is_success(self, result: Dict[str, Any]) -> bool:
        # Default success check – override in subclasses
        return True

    @abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Union[Dict[str, Any], AsyncGenerator]:
        ...

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        result = await self.process(cache, semaphore)
        if isinstance(result, dict):
            return result
        # If generator, exhaust it – stub
        raise RuntimeError("Generator returned, not handled in base run")


# ---------------------------------------------------------------------------
# Composite Module & Node
# ---------------------------------------------------------------------------

class CompositeModule(AgentModule):
    modules: List[AgentModule] = field(default_factory=list)
    node_config: Optional[NodeConfig] = None

    def apply_middlewares(
        self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache
    ) -> Dict[str, Any]:
        # run each middleware in sequence
        result = data
        for mw in middlewares:
            result = mw.process(result, cache)
        return result

    async def run_module_with_concurrency_control(
        self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        async with semaphore:
            return await module.run(cache, semaphore)

    async def run_parallel_modules(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        tasks = [
            self.run_module_with_concurrency_control(m, cache, semaphore)
            for m in self.modules
        ]
        results = await asyncio.gather(*tasks)
        # combine results – stub
        return {"results": results}

    async def run_sequential_modules(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        results = {}
        for m in self.modules:
            results[m.name] = await self.run_module_with_concurrency_control(
                m, cache, semaphore
            )
        return results

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            return await self.run_parallel_modules(cache, semaphore)
        return await self.run_sequential_modules(cache, semaphore)


class Node(CompositeModule):
    def cancel_gen(self, agen: AsyncGenerator) -> None:
        """Cancel an async generator."""
        pass

    def cleanup(self) -> None:
        """Release resources."""
        pass

    def get_nodes(self) -> Dict[str, 'Node']:
        # In a real implementation this returns the whole graph; stub
        return {}

    def set_nodes(self, nodes: Dict[str, 'Node']) -> None:
        # set the global node registry; stub
        pass


# ---------------------------------------------------------------------------
# Flow Control
# ---------------------------------------------------------------------------

@dataclass
class FlowDecision(AsimovBase):
    cleanup_on_jump: Optional[bool] = None
    condition: Optional[str] = None
    condition_variables: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    next_node: str = ""


@dataclass
class FlowControlConfig(AsimovBase):
    cleanup_on_default: bool = False
    decisions: Sequence[FlowDecision] = field(default_factory=list)
    default: Optional[str] = None


class FlowControlModule(AgentModule):
    flow_config: FlowControlConfig = field(default_factory=FlowControlConfig)

    def evaluate_condition(
        self, condition: str, cache: Cache, cache_keys: set[str]
    ) -> bool:
        # evaluate a condition against cache values – stub
        return False

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        # default implementation – stubbed
        return {}


# ---------------------------------------------------------------------------
# Agent Directed Flow
# ---------------------------------------------------------------------------

@dataclass
class Example:
    choice: str = ""
    choices: List[Dict[str, str]] = field(default_factory=list)
    message: str = ""
    reasoning: str = ""


@dataclass
class AgentDrivenFlowDecision(FlowDecision):
    examples: Optional[List[Example]] = None


@dataclass
class AgentDrivenFlowControlConfig(FlowControlConfig):
    decisions: Sequence[AgentDrivenFlowDecision] = field(default_factory=list)


class AgentDirectedFlowControl(FlowControlModule):
    flow_config: AgentDrivenFlowControlConfig = field(
        default_factory=AgentDrivenFlowControlConfig
    )
    inference_client: Optional[InferenceClient] = None
    input_var: Optional[str] = None
    system_description: str = ""
    use_historicals: Optional[bool] = None
    voters: int = 1

    async def gen(self, generation_input: Any, cache: Cache) -> AsyncGenerator:
        # generate decisions using LLM – stub
        yield {}

    def most_common_string(self, string_list: List[str]) -> str:
        # return the most frequent choice
        return max(set(string_list), key=string_list.count)

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        # custom run logic using LLM – stub
        return {}

    def set_attrs(self) -> None:
        # configure internal attributes – stub
        pass


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class Executor(AgentModule, ABC):
    type: Optional[ModuleType] = None

    @abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        ...


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task(AsimovBase):
    error: Optional[str] = None
    id: Optional[UUID] = None
    model_config: Dict[str, Any] = field(default_factory=dict)
    objective: str = ""
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    status: Optional[TaskStatus] = None
    type: str = ""

    def set_error(self, error: str) -> None:
        self.error = error
        # optionally update status – stub

    def set_result(self, result: Any) -> None:
        self.result = result

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


# ---------------------------------------------------------------------------
# Agent (the orchestrator)
# ---------------------------------------------------------------------------

@dataclass
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
        for node in nodes:
            self.add_node(node)

    def add_node(self, node: Node) -> None:
        if self.nodes is None:
            self.nodes = {}
        self.nodes[node.name] = node

    def compile_execution_plan(self) -> ExecutionPlan:
        # compile the full graph into an ExecutionPlan – stub
        return ExecutionPlan()

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        # compile plan starting from a specific node – stub
        return ExecutionPlan()

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        # return chain of dependencies – stub
        return ()

    def is_success(self, result: Any) -> bool:
        # default success check
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
        self, execution_plan: List[dict], node: str
    ) -> List[dict]:
        return []

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        return pathlib.Path("/tmp/snapshot")

    def update_dependencies(self, parent_node: str, new_node: str) -> None:
        pass