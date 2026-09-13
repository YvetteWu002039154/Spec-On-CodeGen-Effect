from __future__ import annotations

import asyncio
import pathlib
import uuid
from abc import abstractmethod
from collections import Counter
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
)

import pydantic


# ============== Base Classes ==============
class AsimovBase(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)


class Cache(pydantic.BaseModel):
    """Placeholder for cache."""
    data: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value


class InferenceClient:
    """Placeholder for inference client."""


class ExecutionPlan(AsimovBase):
    steps: List[ExecutionStep] = []


class ExecutionStep(AsimovBase):
    nodes: List[str] = []
    executed: List[bool] = []
    skipped: List[bool] = []


# ============== Enums and simple named types ==============
class ModelFamily(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ModuleType(Enum):
    EXECUTOR = "executor"
    FLOW_CONTROL = "flow_control"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"


# ============== Core Graph Components ==============
class Middleware(AsimovBase):
    async def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        return data


class ModuleConfig(AsimovBase):
    context: Optional[Dict[str, Any]] = None
    middlewares: Optional[List[Middleware]] = None
    stop_on_success: bool = False
    timeout: float = 30.0


class NodeConfig(AsimovBase):
    condition: Optional[str] = None
    inputs: Optional[List[str]] = None
    outputs: Optional[List[str]] = None
    max_retries: int = 0
    max_visits: Optional[int] = None
    parallel: bool = False
    retry_from: Optional[str] = None
    retry_on_failure: bool = False


class SnapshotControl(AsimovBase):
    name: str = "snapshot"


class AgentModule(AsimovBase):
    config: Optional[ModuleConfig] = None
    container: Optional[CompositeModule] = None
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = None
    input_mailboxes: Optional[List[str]] = None
    name: str = ""
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = None
    type: Optional[ModuleType] = None

    def is_success(self, result: Dict[str, Any]) -> bool:
        """Default implementation; override in subclasses."""
        return True

    @abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Awaitable[Dict[str, Any]] | AsyncGenerator:
        """Abstract async processing."""
        ...

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        result = await self.process(cache, semaphore)
        return result


class Executor(AgentModule):
    type: Optional[ModuleType] = ModuleType.EXECUTOR

    @abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        ...


class CompositeModule(AgentModule):
    modules: List[AgentModule] = []
    node_config: Optional[NodeConfig] = None

    async def apply_middlewares(
        self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache
    ) -> Dict[str, Any]:
        for mw in middlewares:
            data = await mw.process(data, cache)
        return data

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
        combined = {}
        for r in results:
            if r:
                combined.update(r)
        return combined

    async def run_sequential_modules(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        result = {}
        for module in self.modules:
            module_result = await self.run_module_with_concurrency_control(
                module, cache, semaphore
            )
            if module_result:
                result.update(module_result)
        return result

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            return await self.run_parallel_modules(cache, semaphore)
        return await self.run_sequential_modules(cache, semaphore)


class FlowDecision(AsimovBase):
    cleanup_on_jump: Optional[bool] = None
    condition: Optional[str] = None
    condition_variables: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    next_node: str = ""


class FlowControlConfig(AsimovBase):
    cleanup_on_default: bool = False
    decisions: Sequence[FlowDecision] = []
    default: Optional[str] = None


class FlowControlModule(AgentModule):
    flow_config: FlowControlConfig = FlowControlConfig()
    type: Optional[ModuleType] = ModuleType.FLOW_CONTROL

    def evaluate_condition(
        self, condition: str, cache: Cache, cache_keys: Set[str]
    ) -> bool:
        # Simple eval-like condition; assume condition is a boolean expression referencing cache data
        # For safety we just check if condition string is in cache and truthy
        if condition in cache.data:
            return bool(cache.data[condition])
        return False

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        # Flow control logic: evaluate decisions in order, jump to first matching next_node
        for decision in self.flow_config.decisions:
            if decision.condition:
                if self.evaluate_condition(decision.condition, cache, set()):
                    return {"next_node": decision.next_node}
        default = self.flow_config.default
        if default:
            return {"next_node": default}
        return {"next_node": None}


class AgentDirectedFlowDecision(FlowDecision):
    examples: Optional[List[Example]] = None


class AgentDrivenFlowControlConfig(FlowControlConfig):
    decisions: Sequence[AgentDrivenFlowDecision] = []


class Example(AsimovBase):
    choice: str = ""
    choices: List[Dict[str, str]] = []
    message: str = ""
    reasoning: str = ""


class AgentDirectedFlowControl(FlowControlModule):
    flow_config: AgentDrivenFlowControlConfig = AgentDrivenFlowControlConfig()
    inference_client: InferenceClient = InferenceClient()
    input_var: Optional[str] = None
    system_description: str = ""
    use_historicals: Optional[bool] = None
    voters: int = 1

    async def gen(self, generation_input: str, cache: Cache) -> Any:
        # Placeholder for LLM generation
        return "mock"

    @staticmethod
    def most_common_string(string_list: List[str]) -> str:
        if not string_list:
            return ""
        counter = Counter(string_list)
        return counter.most_common(1)[0][0]

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        # Use voting agents to decide a node
        # This simplified version just picks the first available decision
        # Real implementation would use gen and voters.
        return await super().run(cache, semaphore)


class NonRetryableException(Exception):
    """Custom exception for non-retryable failures."""


# ============== Node and Agent ==============
class Node(CompositeModule):
    dependencies: Optional[List[str]] = None
    modules: Optional[List[AgentModule]] = []
    snapshot: Optional[SnapshotControl] = None
    type: Optional[ModuleType] = None

    async def cancel_gen(self, agen: AsyncGenerator) -> None:
        """Cancel an async generator."""
        try:
            await agen.aclose()
        except Exception:
            pass

    def cleanup(self) -> None:
        """Cleanup resources."""
        pass

    def get_nodes(self) -> Dict[str, Node]:
        # Assuming set_nodes was called earlier to store all nodes in the graph.
        return getattr(self, "_all_nodes", {})

    def set_nodes(self, nodes: Dict[str, "Node"]) -> None:
        self._all_nodes = nodes


class ExecutionState(AsimovBase):
    current_plan: Optional[ExecutionPlan] = None
    execution_history: Optional[List[ExecutionPlan]] = []
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
            for i, name in enumerate(step.nodes):
                if name == node_name and step.executed[i]:
                    return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan.steps:
            for i, name in enumerate(step.nodes):
                if name == node_name and step.skipped[i]:
                    return True
        return False


class Task(AsimovBase):
    error: Optional[str] = None
    id: Optional[uuid.UUID] = None
    objective: str = ""
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    status: TaskStatus = TaskStatus.PENDING
    type: str = ""

    def set_error(self, error: str) -> None:
        self.error = error
        self.update_status(TaskStatus.FAILURE)

    def set_result(self, result: Any) -> None:
        self.result = result
        self.update_status(TaskStatus.SUCCESS)

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


class Agent(AsimovBase):
    auto_snapshot: bool = False
    cache: Optional[Cache] = Cache()
    error_mailbox: str = ""
    execution_state: Optional[ExecutionState] = ExecutionState()
    graph: Optional[Dict[str, List[str]]] = {}
    max_concurrent_tasks: Optional[int] = None
    max_total_iterations: Optional[int] = None
    node_results: Optional[Dict[str, Any]] = {}
    nodes: Optional[Dict[str, Node]] = {}
    output_mailbox: str = ""

    def add_node(self, node: Node) -> None:
        if self.nodes is None:
            self.nodes = {}
        self.nodes[node.name] = node
        node.set_nodes(self.nodes)

    def add_multiple_nodes(self, nodes: List[Node]) -> None:
        for node in nodes:
            self.add_node(node)

    def compile_execution_plan(self) -> ExecutionPlan:
        # Simple topological sort to produce an execution plan.
        if not self.nodes:
            return ExecutionPlan()
        # Build adjacency list from current graph (if any) otherwise from dependencies
        # Here we assume the graph is a dict mapping node_name -> list of dependent nodes
        graph = self.graph if self.graph is not None else {}
        # If no graph, derive from node dependencies
        if not graph and self.nodes:
            for name, node in self.nodes.items():
                if node.dependencies:
                    for dep in node.dependencies:
                        graph.setdefault(dep, []).append(name)
        # Topological sort
        in_degree = {name: 0 for name in self.nodes}
        for deps in graph.values():
            for dep in deps:
                in_degree[dep] = in_degree.get(dep, 0) + 1
        queue = [n for n, d in in_degree.items() if d == 0]
        plan_steps = []
        while queue:
            step_nodes = queue[:]  # in parallel if multiple roots, but we treat sequentially for simplicity
            plan_steps.append(step_nodes.copy())
            new_queue = []
            for node in step_nodes:
                for neighbor in graph.get(node, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        new_queue.append(neighbor)
            queue = new_queue
        # Convert to ExecutionStep objects
        steps = []
        for nodes_list in plan_steps:
            steps.append(
                ExecutionStep(
                    nodes=nodes_list,
                    executed=[False] * len(nodes_list),
                    skipped=[False] * len(nodes_list),
                )
            )
        return ExecutionPlan(steps=steps)

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        # Similar but only from a subgraph reachable from start_node
        # For simplicity, return full plan; override as needed.
        return self.compile_execution_plan()

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        """Return a tuple of node names that depend on the given node recursively."""
        if not self.graph:
            return ()
        visited = set()
        chain = []
        def dfs(n):
            if n in visited:
                return
            visited.add(n)
            chain.append(n)
            for neighbor in self.graph.get(n, []):
                dfs(neighbor)
        dfs(node_name)
        return tuple(chain)

    @staticmethod
    def is_success(result: Dict[str, Any]) -> bool:
        return True

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        # Mark the node and all downstream as skipped in execution_state
        deps = self.get_dependent_chains(node_name)
        es = self.execution_state
        if not es or not es.current_plan:
            return
        for step in es.current_plan.steps:
            for i, node in enumerate(step.nodes):
                if node in deps:
                    step.skipped[i] = True

    async def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        # Placeholder: restore state from snapshot
        pass

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if self.nodes and node_name in self.nodes:
            node = self.nodes[node_name]
            sem = self.set_semaphore()
            cache = self.cache if self.cache else Cache()
            result = await node.run(cache, sem)
            if self.node_results is None:
                self.node_results = {}
            self.node_results[node_name] = result
            return result
        return {}

    async def run_task(self, task: Task) -> None:
        # Process a Task object by running the graph
        # Simplified: execute all nodes according to compiled plan
        sem = self.set_semaphore()
        plan = self.compile_execution_plan()
        es = ExecutionState(current_plan=plan, total_iterations=0)
        self.execution_state = es
        for step in plan.steps:
            for node_name in step.nodes:
                await self.run_node(node_name)
        task.set_result(self.node_results)

    def set_semaphore(self) -> asyncio.Semaphore:
        # Create a semaphore based on max_concurrent_tasks, default 10
        max_tasks = self.max_concurrent_tasks if self.max_concurrent_tasks else 10
        return asyncio.Semaphore(max_tasks)

    def slice_before_node(
        self, execution_plan: List[dict], node: str
    ) -> List[dict]:
        """Return steps that occur before the given node in the plan."""
        sliced = []
        for step in execution_plan:
            if node in step.get("nodes", []):
                break
            sliced.append(step)
        return sliced

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        # Save state to a directory and return path
        snap_dir = pathlib.Path(f"snapshots/{task.id}_{name_hint}")
        snap_dir.mkdir(parents=True, exist_ok=True)
        # Serialization omitted for brevity
        return snap_dir

    def update_dependencies(self, parent_node: str, new_node: str) -> None:
        if self.graph is None:
            self.graph = {}
        if parent_node not in self.graph:
            self.graph[parent_node] = []
        if new_node not in self.graph[parent_node]:
            self.graph[parent_node].append(new_node)