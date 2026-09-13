import abc
import asyncio
import contextlib
import pathlib
import uuid
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
    Union,
)

from pydantic import BaseModel, ConfigDict


# =============================================================================
# asimov.asimov_base
# =============================================================================

class AsimovBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


# =============================================================================
# asimov.constants
# =============================================================================

class ModelFamily(str, Enum):
    name: str


class ModuleType(str, Enum):
    name: str


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# cache
# =============================================================================

class Cache(dict):
    """Simple dict-based cache with attribute access."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"Cache has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


# =============================================================================
# asimov.graph.tasks
# =============================================================================

class Task(AsimovBase):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: Optional[uuid.UUID] = None
    objective: str = ""
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    status: TaskStatus = TaskStatus.PENDING
    type: str = ""
    error: Optional[str] = None

    def set_error(self, error: str) -> None:
        self.error = error
        self.status = TaskStatus.FAILED

    def set_result(self, result: Any) -> None:
        self.result = result
        self.status = TaskStatus.COMPLETED

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


# =============================================================================
# asimov.graph.Middleware
# =============================================================================

class Middleware(AsimovBase):
    def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        return data


# =============================================================================
# asimov.graph.ModuleConfig
# =============================================================================

class ModuleConfig(AsimovBase):
    context: Optional[Dict[str, Any]] = None
    middlewares: Optional[List[Middleware]] = None
    stop_on_success: bool = False
    timeout: float = 300.0


# =============================================================================
# asimov.graph.NodeConfig
# =============================================================================

class NodeConfig(AsimovBase):
    condition: Optional[str] = None
    inputs: Optional[List[str]] = None
    max_retries: int = 0
    max_visits: Optional[int] = None
    outputs: Optional[List[str]] = None
    parallel: bool = False
    retry_from: Optional[str] = None
    retry_on_failure: bool = False


# =============================================================================
# asimov.graph.SnapshotControl
# =============================================================================

class SnapshotControl(BaseModel):
    name: str = "snapshot"


# =============================================================================
# asimov.graph.NonRetryableException
# =============================================================================

class NonRetryableException(Exception):
    pass


# =============================================================================
# asimov.graph.ExecutionStep
# =============================================================================

class ExecutionStep(BaseModel):
    nodes: List[str] = []
    executed: List[bool] = []
    skipped: List[bool] = []

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.executed:
            self.executed = [False] * len(self.nodes)
        if not self.skipped:
            self.skipped = [False] * len(self.nodes)


# =============================================================================
# asimov.graph.ExecutionPlan
# =============================================================================

class ExecutionPlan(BaseModel):
    steps: List[ExecutionStep] = []

    def __iter__(self):
        return iter(self.steps)

    def __len__(self) -> int:
        return len(self.steps)

    def __getitem__(self, index: int) -> ExecutionStep:
        return self.steps[index]


# =============================================================================
# asimov.graph.ExecutionState
# =============================================================================

class ExecutionState(AsimovBase):
    current_plan: Optional[ExecutionPlan] = None
    execution_history: Optional[List[ExecutionPlan]] = None
    execution_index: Optional[int] = None
    total_iterations: Optional[int] = None
    _executed_nodes: Set[str] = set()
    _skipped_nodes: Set[str] = set()

    def mark_executed(self, step_index: int, node_index: int) -> None:
        if self.current_plan and step_index < len(self.current_plan.steps):
            step = self.current_plan.steps[step_index]
            if node_index < len(step.nodes):
                step.executed[node_index] = True
                self._executed_nodes.add(step.nodes[node_index])

    def was_executed(self, node_name: str) -> bool:
        return node_name in self._executed_nodes

    def was_skipped(self, node_name: str) -> bool:
        return node_name in self._skipped_nodes


# =============================================================================
# asimov.graph.AgentModule
# =============================================================================

class AgentModule(AsimovBase, abc.ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = ""
    type: ModuleType = ModuleType("default")
    config: Optional[ModuleConfig] = None
    container: Optional['CompositeModule'] = None
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = None
    input_mailboxes: Optional[List[str]] = None
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = None

    def is_success(self, result: Dict[str, Any]) -> bool:
        return result.get("success", False)

    @abc.abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Union[Dict[str, Any], AsyncGenerator]:
        ...

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        async with semaphore:
            result = await self.process(cache, semaphore)
            if isinstance(result, dict):
                return result
            # If it's an async generator, collect all yields
            collected: Dict[str, Any] = {}
            async for chunk in result:
                collected.update(chunk)
            return collected


# =============================================================================
# asimov.graph.CompositeModule
# =============================================================================

class CompositeModule(AgentModule):
    modules: List[AgentModule] = []
    node_config: Optional[NodeConfig] = None

    def apply_middlewares(
        self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache
    ) -> Dict[str, Any]:
        result = data
        for middleware in middlewares:
            result = middleware.process(result, cache)
        return result

    async def run_module_with_concurrency_control(
        self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await module.run(cache, semaphore)

    async def run_parallel_modules(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        tasks = []
        for module in self.modules:
            tasks.append(self.run_module_with_concurrency_control(module, cache, semaphore))
        results = await asyncio.gather(*tasks)
        combined: Dict[str, Any] = {}
        for result in results:
            combined.update(result)
        return combined

    async def run_sequential_modules(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        combined: Dict[str, Any] = {}
        for module in self.modules:
            result = await self.run_module_with_concurrency_control(module, cache, semaphore)
            combined.update(result)
        return combined

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            result = await self.run_parallel_modules(cache, semaphore)
        else:
            result = await self.run_sequential_modules(cache, semaphore)
        if self.config and self.config.middlewares:
            result = self.apply_middlewares(self.config.middlewares, result, cache)
        return result

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Union[Dict[str, Any], AsyncGenerator]:
        return await self.run(cache, semaphore)


# =============================================================================
# asimov.graph.Node
# =============================================================================

class Node(CompositeModule):
    dependencies: Optional[List[str]] = None
    modules: Optional[List[AgentModule]] = None
    node_config: Optional[NodeConfig] = None
    snapshot: Optional[SnapshotControl] = None
    type: Optional[ModuleType] = None
    _nodes: Optional[Dict[str, 'Node']] = None
    _active_generators: List[AsyncGenerator] = []

    def cancel_gen(self, agen: AsyncGenerator) -> None:
        if agen in self._active_generators:
            self._active_generators.remove(agen)
        try:
            asyncio.create_task(agen.aclose())
        except Exception:
            pass

    def cleanup(self) -> None:
        for gen in list(self._active_generators):
            self.cancel_gen(gen)
        self._active_generators.clear()

    def get_nodes(self) -> Dict[str, 'Node']:
        return self._nodes or {}

    def set_nodes(self, nodes: Dict[str, 'Node']) -> None:
        self._nodes = nodes


# =============================================================================
# asimov.graph.FlowDecision
# =============================================================================

class FlowDecision(AsimovBase):
    cleanup_on_jump: Optional[bool] = None
    condition: Optional[str] = None
    condition_variables: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    next_node: str = ""


# =============================================================================
# asimov.graph.FlowControlConfig
# =============================================================================

class FlowControlConfig(AsimovBase):
    cleanup_on_default: bool = False
    decisions: Sequence[FlowDecision] = []
    default: Optional[str] = None


# =============================================================================
# asimov.graph.FlowControlModule
# =============================================================================

class FlowControlModule(AgentModule):
    flow_config: FlowControlConfig = FlowControlConfig()

    def evaluate_condition(
        self, condition: str, cache: Cache, cache_keys: Set[str]
    ) -> bool:
        if not condition:
            return False
        try:
            env: Dict[str, Any] = {k: cache.get(k) for k in cache_keys}
            return bool(eval(condition, {"__builtins__": {}}, env))
        except Exception:
            return False

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        for decision in self.flow_config.decisions:
            condition_met = False
            if decision.condition:
                cache_keys = set(decision.condition_variables or [])
                condition_met = self.evaluate_condition(
                    decision.condition, cache, cache_keys
                )
            if condition_met or not decision.condition:
                return {"next_node": decision.next_node, "decision_metadata": decision.metadata}
        if self.flow_config.default:
            return {"next_node": self.flow_config.default}
        return {"next_node": None}

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Union[Dict[str, Any], AsyncGenerator]:
        return await self.run(cache, semaphore)


# =============================================================================
# asimov.graph.agent_directed_flow.Example
# =============================================================================

class Example(BaseModel):
    choice: str = ""
    choices: List[Dict[str, str]] = []
    message: str = ""
    reasoning: str = ""


# =============================================================================
# asimov.graph.agent_directed_flow.AgentDrivenFlowDecision
# =============================================================================

class AgentDrivenFlowDecision(FlowDecision):
    examples: Optional[List[Example]] = None


# =============================================================================
# asimov.graph.agent_directed_flow.AgentDrivenFlowControlConfig
# =============================================================================

class AgentDrivenFlowControlConfig(FlowControlConfig):
    decisions: Sequence[FlowDecision] = []
    default: Optional[str] = None


# =============================================================================
# asimov.graph.agent_directed_flow.InferenceClient (stub)
# =============================================================================

class InferenceClient(BaseModel):
    """Stub for an inference client."""

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return ""


# =============================================================================
# asimov.graph.agent_directed_flow.AgentDirectedFlowControl
# =============================================================================

class AgentDirectedFlowControl(FlowControlModule):
    flow_config: AgentDrivenFlowControlConfig = AgentDrivenFlowControlConfig()
    inference_client: InferenceClient = InferenceClient()
    input_var: Optional[str] = None
    system_description: str = ""
    use_historicals: Optional[bool] = False
    voters: int = 1

    async def gen(
        self, generation_input: Any, cache: Cache
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate responses from the inference client."""
        import json

        choices_data = []
        for decision in self.flow_config.decisions:
            choices_data.append({
                "next_node": decision.next_node,
                "description": decision.metadata.get("description", "") if decision.metadata else "",
            })

        prompt = f"System: {self.system_description}\n"
        prompt += f"Input: {generation_input}\n"
        prompt += f"Choices: {json.dumps(choices_data)}\n"

        responses = []
        for _ in range(self.voters):
            response = await self.inference_client.generate(prompt)
            responses.append(response)
            yield {"raw_response": response, "voter_index": _}

        chosen = self.most_common_string(responses)
        for decision in self.flow_config.decisions:
            if decision.next_node == chosen:
                yield {"next_node": decision.next_node, "decision_metadata": decision.metadata}
                return

        if self.flow_config.default:
            yield {"next_node": self.flow_config.default}
        else:
            yield {"next_node": None}

    @staticmethod
    def most_common_string(string_list: List[str]) -> str:
        if not string_list:
            return ""
        counter = Counter(string_list)
        return counter.most_common(1)[0][0]

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        async with semaphore:
            generation_input = cache.get(self.input_var) if self.input_var else None
            collected: Dict[str, Any] = {}
            async for chunk in self.gen(generation_input, cache):
                collected.update(chunk)
            return collected

    def set_attrs(self) -> None:
        pass


# =============================================================================
# asimov.executors.executor.Executor
# =============================================================================

class Executor(AgentModule, abc.ABC):
    type: Optional[ModuleType] = None

    @abc.abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        ...


# =============================================================================
# asimov.graph.Agent
# =============================================================================

class Agent(AsimovBase):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    auto_snapshot: bool = False
    cache: Optional[Cache] = None
    error_mailbox: str = "errors"
    execution_state: Optional[ExecutionState] = None
    graph: Optional[Dict[str, List[str]]] = None
    max_concurrent_tasks: Optional[int] = None
    max_total_iterations: Optional[int] = None
    node_results: Optional[Dict[str, Any]] = None
    nodes: Optional[Dict[str, Node]] = None
    output_mailbox: str = "output"
    _semaphore: Optional[asyncio.Semaphore] = None

    def add_node(self, node: Node) -> None:
        if self.nodes is None:
            self.nodes = {}
        if self.graph is None:
            self.graph = {}
        self.nodes[node.name] = node
        node.set_nodes(self.nodes)
        if node.name not in self.graph:
            self.graph[node.name] = []

    def add_multiple_nodes(self, nodes: List[Node]) -> None:
        for node in nodes:
            self.add_node(node)

    def compile_execution_plan(self) -> ExecutionPlan:
        return self._build_execution_plan()

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        return self._build_execution_plan(start_node=start_node)

    def _build_execution_plan(self, start_node: Optional[str] = None) -> ExecutionPlan:
        if not self.graph or not self.nodes:
            return ExecutionPlan()

        in_degree: Dict[str, int] = {name: 0 for name in self.graph}
        for node_name, deps in self.graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[node_name] = in_degree.get(node_name, 0) + 1

        # Kahn's algorithm for topological sorting
        roots: List[str] = [start_node] if start_node else [
            name for name, deg in in_degree.items() if deg == 0
        ]

        if start_node and start_node not in self.graph:
            return ExecutionPlan()

        visited: Set[str] = set()
        steps: List[ExecutionStep] = []
        current_level = list(roots)

        while current_level:
            next_level: List[str] = []
            step_nodes: List[str] = []
            for node_name in current_level:
                if node_name in visited:
                    continue
                visited.add(node_name)
                step_nodes.append(node_name)
                for neighbor, deps in self.graph.items():
                    if node_name in deps:
                        in_degree[neighbor] -= 1
                        if in_degree[neighbor] == 0:
                            next_level.append(neighbor)
            if step_nodes:
                steps.append(ExecutionStep(nodes=step_nodes))
            current_level = next_level

        # Add any remaining nodes not reached
        remaining = [n for n in self.graph if n not in visited]
        if remaining:
            steps.append(ExecutionStep(nodes=remaining))

        plan = ExecutionPlan(steps=steps)
        if self.execution_state is None:
            self.execution_state = ExecutionState()
        self.execution_state.current_plan = plan
        self.execution_state.execution_index = 0
        self.execution_state.total_iterations = 0

        return plan

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        if not self.graph:
            return ()
        chains: List[str] = []
        to_visit = [node_name]
        while to_visit:
            current = to_visit.pop(0)
            for neighbor, deps in self.graph.items():
                if current in deps and neighbor not in chains:
                    chains.append(neighbor)
                    to_visit.append(neighbor)
        return tuple(chains)

    @staticmethod
    def is_success(result: Dict[str, Any]) -> bool:
        return result.get("success", False)

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if self.execution_state is None:
            return
        deps = self.get_dependent_chains(node_name)
        self.execution_state._skipped_nodes.add(node_name)
        for dep in deps:
            self.execution_state._skipped_nodes.add(dep)

    async def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> Dict[str, Any]:
        import json

        snapshot_file = snapshot_dir / "snapshot.json"
        if snapshot_file.exists():
            with open(snapshot_file, "r") as f:
                data = json.load(f)
            if self.cache is None:
                self.cache = Cache()
            self.cache.update(data.get("cache", {}))
            self.execution_state = ExecutionState(**data.get("execution_state", {}))
        return await self.run_node("__resume__")

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if self.nodes is None or node_name not in self.nodes:
            return {"error": f"Node '{node_name}' not found"}
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()
        node = self.nodes[node_name]
        try:
            result = await node.run(self.cache, self._semaphore)  # type: ignore
            if self.node_results is None:
                self.node_results = {}
            self.node_results[node_name] = result
            return result
        except Exception as e:
            return {"error": str(e), "node": node_name}

    async def run_task(self, task: Task) -> None:
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()
        try:
            if not self.execution_state or not self.execution_state.current_plan:
                self.compile_execution_plan()
            task.update_status(TaskStatus.RUNNING)
            results: Dict[str, Any] = {}
            if self.execution_state and self.execution_state.current_plan:
                for step in self.execution_state.current_plan.steps:
                    tasks_ = []
                    for node_name in step.nodes:
                        if self.execution_state.was_skipped(node_name):
                            continue
                        if self.nodes and node_name in self.nodes:
                            tasks_.append(self.nodes[node_name].run(self.cache, self._semaphore))
                    if tasks_:
                        step_results = await asyncio.gather(*tasks_)
                        for name, res in zip(step.nodes, step_results):
                            if not self.execution_state.was_skipped(name):
                                results[name] = res
                    if self.execution_state.total_iterations is not None:
                        self.execution_state.total_iterations += 1
                    if (
                        self.max_total_iterations
                        and self.execution_state.total_iterations
                        and self.execution_state.total_iterations >= self.max_total_iterations
                    ):
                        break
            if self.node_results is None:
                self.node_results = {}
            self.node_results.update(results)
            task.set_result(results)
        except Exception as e:
            task.set_error(str(e))

    def set_semaphore(self) -> None:
        import asyncio

        limit = self.max_concurrent_tasks or 10
        self._semaphore = asyncio.Semaphore(limit)

    def slice_before_node(
        self, execution_plan: List[dict], node: str
    ) -> List[dict]:
        sliced = []
        for step in execution_plan:
            if node in step.get("nodes", []):
                break
            sliced.append(step)
        return sliced

    async def snapshot(
        self, task: Task, name_hint: str
    ) -> pathlib.Path:
        import json
        import tempfile

        snapshot_dir = pathlib.Path(tempfile.mkdtemp(prefix=f"asimov_snapshot_{name_hint}_"))
        snapshot_file = snapshot_dir / "snapshot.json"
        snapshot_data = {
            "task_id": str(task.id) if task.id else None,
            "cache": dict(self.cache) if self.cache else {},
            "execution_state": (
                self.execution_state.model_dump() if self.execution_state else {}
            ),
            "name_hint": name_hint,
        }
        with open(snapshot_file, "w") as f:
            json.dump(snapshot_data, f, indent=2, default=str)
        return snapshot_dir

    def update_dependencies(
        self, parent_node: str, new_node: str
    ) -> None:
        if self.graph is None:
            self.graph = {}
        if parent_node not in self.graph:
            self.graph[parent_node] = []
        if new_node not in self.graph[parent_node]:
            self.graph[parent_node].append(new_node)


# =============================================================================
# __init__.py exports (for completeness)
# =============================================================================

__all__ = [
    "Agent",
    "AgentDirectedFlowControl",
    "AgentDrivenFlowControlConfig",
    "AgentDrivenFlowDecision",
    "AgentModule",
    "AsimovBase",
    "Cache",
    "CompositeModule",
    "Example",
    "ExecutionPlan",
    "ExecutionState",
    "ExecutionStep",
    "Executor",
    "FlowControlConfig",
    "FlowControlModule",
    "FlowDecision",
    "InferenceClient",
    "Middleware",
    "ModelFamily",
    "ModuleConfig",
    "ModuleType",
    "Node",
    "NodeConfig",
    "NonRetryableException",
    "SnapshotControl",
    "Task",
    "TaskStatus",
]