import asyncio
import json
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
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# asimov.asimov_base
# ---------------------------------------------------------------------------

class AsimovBase(BaseModel):
    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# asimov.graph.tasks
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(AsimovBase):
    id: Optional[UUID] = Field(default_factory=uuid.uuid4)
    objective: str
    type: str = "task"
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    model_config = {"arbitrary_types_allowed": True}

    def update_status(self, status: TaskStatus) -> None:
        self.status = status

    def set_result(self, result: Any) -> None:
        self.result = result

    def set_error(self, error: str) -> None:
        self.error = error


# ---------------------------------------------------------------------------
# asimov.constants
# ---------------------------------------------------------------------------

class ModelFamily(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    OTHER = "other"


# ---------------------------------------------------------------------------
# asimov.graph (core types)
# ---------------------------------------------------------------------------

class ModuleType(str, Enum):
    EXECUTOR = "executor"
    FLOW_CONTROL = "flow_control"
    COMPOSITE = "composite"
    SUBAGENT = "subagent"


class SnapshotControl(str, Enum):
    BEFORE = "before"
    AFTER = "after"
    BOTH = "both"
    NONE = "none"


class NonRetryableException(Exception):
    pass


class Middleware(AsimovBase):
    async def process(self, data: Dict[str, Any], cache: Any) -> Dict[str, Any]:
        return data


class ModuleConfig(AsimovBase):
    context: Optional[Dict[str, Any]] = None
    middlewares: Optional[List[Middleware]] = None
    stop_on_success: bool = False
    timeout: float = 300.0


class NodeConfig(AsimovBase):
    condition: Optional[str] = None
    inputs: Optional[List[str]] = None
    outputs: Optional[List[str]] = None
    max_retries: int = 0
    max_visits: Optional[int] = None
    parallel: bool = False
    retry_on_failure: bool = False
    retry_from: Optional[str] = None


class FlowDecision(AsimovBase):
    next_node: str
    condition: Optional[str] = None
    condition_variables: Optional[List[str]] = None
    cleanup_on_jump: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class FlowControlConfig(AsimovBase):
    decisions: Sequence[FlowDecision] = []
    default: Optional[str] = None
    cleanup_on_default: bool = False


class ExecutionStep(BaseModel):
    nodes: List[str] = Field(default_factory=list)
    executed: List[bool] = Field(default_factory=list)
    skipped: List[bool] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


ExecutionPlan = List[ExecutionStep]


class ExecutionState(AsimovBase):
    current_plan: Optional[ExecutionPlan] = None
    execution_history: Optional[List[ExecutionPlan]] = None
    execution_index: Optional[int] = None
    total_iterations: Optional[int] = None

    def mark_executed(self, step_index: int, node_index: int) -> None:
        if self.current_plan is None:
            return
        if 0 <= step_index < len(self.current_plan):
            step = self.current_plan[step_index]
            if 0 <= node_index < len(step.executed):
                step.executed[node_index] = True

    def was_executed(self, node_name: str) -> bool:
        if self.current_plan is None:
            return False
        for step in self.current_plan:
            for i, name in enumerate(step.nodes):
                if name == node_name and i < len(step.executed) and step.executed[i]:
                    return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if self.current_plan is None:
            return False
        for step in self.current_plan:
            for i, name in enumerate(step.nodes):
                if name == node_name and i < len(step.skipped) and step.skipped[i]:
                    return True
        return False


# ---------------------------------------------------------------------------
# Cache placeholder (used throughout)
# ---------------------------------------------------------------------------

class Cache:
    def __init__(self):
        self._store: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def keys(self) -> Set[str]:
        return set(self._store.keys())

    def __contains__(self, key: str) -> bool:
        return key in self._store


# ---------------------------------------------------------------------------
# AgentModule
# ---------------------------------------------------------------------------

class AgentModule(AsimovBase):
    name: str = ""
    type: Optional[ModuleType] = None
    config: Optional[ModuleConfig] = None
    container: Optional[Any] = None  # 'CompositeModule'
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = None
    input_mailboxes: Optional[List[str]] = None
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = None

    def is_success(self, result: Dict[str, Any]) -> bool:
        if result is None:
            return False
        status = result.get("status")
        if status is not None:
            return status == "success"
        return True

    @abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> "Awaitable[dict[str, Any]] | AsyncGenerator":
        raise NotImplementedError

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        result = await self.process(cache, semaphore)
        if self.executions is not None:
            self.executions += 1
        else:
            self.executions = 1
        return result


# ---------------------------------------------------------------------------
# CompositeModule
# ---------------------------------------------------------------------------

class CompositeModule(AgentModule):
    modules: List[AgentModule] = Field(default_factory=list)
    node_config: Optional[NodeConfig] = None

    async def apply_middlewares(
        self,
        middlewares: List[Middleware],
        data: Dict[str, Any],
        cache: Cache,
    ) -> Dict[str, Any]:
        for mw in middlewares:
            data = await mw.process(data, cache)
        return data

    async def run_module_with_concurrency_control(
        self,
        module: AgentModule,
        cache: Cache,
        semaphore: asyncio.Semaphore,
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
        results = await asyncio.gather(*tasks, return_exceptions=True)
        combined: Dict[str, Any] = {}
        for r in results:
            if isinstance(r, dict):
                combined.update(r)
        return combined

    async def run_sequential_modules(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        combined: Dict[str, Any] = {}
        for module in self.modules:
            result = await module.run(cache, semaphore)
            combined.update(result)
            if self.node_config and self.node_config.condition:
                pass  # condition evaluation handled elsewhere
            config = module.config
            if config and config.stop_on_success and module.is_success(result):
                break
        return combined

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        parallel = self.node_config.parallel if self.node_config else False
        if parallel:
            result = await self.run_parallel_modules(cache, semaphore)
        else:
            result = await self.run_sequential_modules(cache, semaphore)

        # Apply middlewares from module configs
        for module in self.modules:
            if module.config and module.config.middlewares:
                result = await self.apply_middlewares(
                    module.config.middlewares, result, cache
                )
        return result

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class Node(CompositeModule):
    dependencies: Optional[List[str]] = None
    modules: Optional[List[AgentModule]] = Field(default_factory=list)
    node_config: Optional[NodeConfig] = None
    snapshot: Optional[SnapshotControl] = None
    type: Optional[ModuleType] = None
    _nodes: Optional[Dict[str, "Node"]] = None

    def get_nodes(self) -> Optional[Dict[str, "Node"]]:
        return self._nodes

    def set_nodes(self, nodes: Dict[str, "Node"]) -> None:
        self._nodes = nodes

    async def cancel_gen(self, agen: AsyncGenerator) -> None:
        await agen.aclose()

    async def cleanup(self) -> None:
        pass

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        modules = self.modules or []
        parallel = self.node_config.parallel if self.node_config else False

        if parallel:
            tasks = [
                self.run_module_with_concurrency_control(m, cache, semaphore)
                for m in modules
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            combined: Dict[str, Any] = {}
            for r in results:
                if isinstance(r, dict):
                    combined.update(r)
            return combined
        else:
            combined = {}
            for module in modules:
                result = await module.run(cache, semaphore)
                combined.update(result)
                config = module.config
                if config and config.stop_on_success and module.is_success(result):
                    break
            return combined

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


# ---------------------------------------------------------------------------
# FlowControlModule
# ---------------------------------------------------------------------------

class FlowControlModule(AgentModule):
    flow_config: Optional[FlowControlConfig] = None

    def evaluate_condition(
        self, condition: str, cache: Cache, cache_keys: Set[str]
    ) -> bool:
        try:
            context = {key: cache.get(key) for key in cache_keys}
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception:
            return False

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.flow_config is None:
            return {}

        for decision in self.flow_config.decisions:
            if decision.condition is None:
                return {"next_node": decision.next_node}

            cache_keys: Set[str] = set()
            if decision.condition_variables:
                cache_keys = set(decision.condition_variables)
            else:
                cache_keys = cache.keys()

            if self.evaluate_condition(decision.condition, cache, cache_keys):
                if decision.cleanup_on_jump:
                    pass  # cleanup logic
                return {"next_node": decision.next_node}

        if self.flow_config.default:
            if self.flow_config.cleanup_on_default:
                pass  # cleanup logic
            return {"next_node": self.flow_config.default}

        return {}

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class Executor(AgentModule):
    type: Optional[ModuleType] = ModuleType.EXECUTOR

    @abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Agent(AsimovBase):
    nodes: Optional[Dict[str, Node]] = None
    graph: Optional[Dict[str, List[str]]] = None
    node_results: Optional[Dict[str, Any]] = None
    execution_state: Optional[ExecutionState] = None
    cache: Optional[Cache] = None
    output_mailbox: str = "output"
    error_mailbox: str = "error"
    max_concurrent_tasks: Optional[int] = None
    max_total_iterations: Optional[int] = None
    auto_snapshot: bool = False
    _semaphore: Optional[asyncio.Semaphore] = None

    model_config = {"arbitrary_types_allowed": True}

    def set_semaphore(self) -> None:
        limit = self.max_concurrent_tasks or 10
        self._semaphore = asyncio.Semaphore(limit)

    def add_node(self, node: Node) -> None:
        if self.nodes is None:
            self.nodes = {}
        self.nodes[node.name] = node
        if self.graph is None:
            self.graph = {}
        if node.name not in self.graph:
            self.graph[node.name] = []
        if node.dependencies:
            for dep in node.dependencies:
                if dep not in self.graph:
                    self.graph[dep] = []
                if node.name not in self.graph[dep]:
                    self.graph[dep].append(node.name)

    def add_multiple_nodes(self, nodes: List[Node]) -> None:
        for node in nodes:
            self.add_node(node)

    def update_dependencies(self, parent_node: str, new_node: str) -> None:
        if self.graph is None:
            self.graph = {}
        if parent_node not in self.graph:
            self.graph[parent_node] = []
        if new_node not in self.graph[parent_node]:
            self.graph[parent_node].append(new_node)

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        if self.graph is None:
            return ()
        visited: List[str] = []
        queue = [node_name]
        while queue:
            current = queue.pop(0)
            if current not in visited:
                visited.append(current)
                for dependent in self.graph.get(current, []):
                    queue.append(dependent)
        visited.remove(node_name)
        return tuple(visited)

    def compile_execution_plan(self) -> ExecutionPlan:
        if self.nodes is None:
            return []
        if self.graph is None:
            return []

        # Topological sort using Kahn's algorithm
        in_degree: Dict[str, int] = {name: 0 for name in self.nodes}
        for node_name, dependents in self.graph.items():
            for dep in dependents:
                if dep in in_degree:
                    in_degree[dep] += 1

        # Group nodes by level (BFS layers)
        plan: ExecutionPlan = []
        queue = [n for n, d in in_degree.items() if d == 0]

        while queue:
            step = ExecutionStep(
                nodes=list(queue),
                executed=[False] * len(queue),
                skipped=[False] * len(queue),
            )
            plan.append(step)
            next_queue: List[str] = []
            for node_name in queue:
                for dependent in self.graph.get(node_name, []):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_queue.append(dependent)
            queue = next_queue

        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        full_plan = self.compile_execution_plan()
        return self.slice_before_node(full_plan, start_node)

    def slice_before_node(
        self, execution_plan: List[ExecutionStep], node: str
    ) -> List[ExecutionStep]:
        result: List[ExecutionStep] = []
        found = False
        for step in execution_plan:
            if node in step.nodes:
                found = True
                result.append(step)
                break
            result.append(step)
        if not found:
            return execution_plan
        idx = None
        for i, step in enumerate(result):
            if node in step.nodes:
                idx = i
                break
        if idx is not None:
            return result[idx:]
        return result

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if self.execution_state is None or self.execution_state.current_plan is None:
            return
        nodes_to_skip = {node_name} | set(self.get_dependent_chains(node_name))
        for step in self.execution_state.current_plan:
            for i, name in enumerate(step.nodes):
                if name in nodes_to_skip:
                    if i < len(step.skipped):
                        step.skipped[i] = True

    def is_success(self, result: Any) -> bool:
        if result is None:
            return False
        if isinstance(result, dict):
            status = result.get("status")
            if status is not None:
                return status == "success"
        return True

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if self.nodes is None or node_name not in self.nodes:
            raise ValueError(f"Node '{node_name}' not found")

        node = self.nodes[node_name]
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()

        semaphore = self._semaphore

        retries = 0
        max_retries = 0
        if node.node_config:
            max_retries = node.node_config.max_retries

        while True:
            try:
                result = await node.run(self.cache, semaphore)
                if self.node_results is None:
                    self.node_results = {}
                self.node_results[node_name] = result
                return result
            except NonRetryableException:
                raise
            except Exception as e:
                if retries < max_retries and (
                    node.node_config and node.node_config.retry_on_failure
                ):
                    retries += 1
                    continue
                raise

    async def run_task(self, task: Task) -> None:
        task.update_status(TaskStatus.RUNNING)

        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()

        plan = self.compile_execution_plan()
        self.execution_state = ExecutionState(
            current_plan=plan,
            execution_history=[],
            execution_index=0,
            total_iterations=0,
        )

        try:
            iteration = 0
            step_index = 0

            while step_index < len(plan):
                if (
                    self.max_total_iterations is not None
                    and iteration >= self.max_total_iterations
                ):
                    break

                step = plan[step_index]
                next_node_override: Optional[str] = None

                for node_index, node_name in enumerate(step.nodes):
                    if step.skipped[node_index]:
                        continue

                    try:
                        result = await self.run_node(node_name)
                        self.execution_state.mark_executed(step_index, node_index)

                        # Check for flow control
                        if isinstance(result, dict) and "next_node" in result:
                            next_node_override = result["next_node"]

                    except NonRetryableException as e:
                        task.set_error(str(e))
                        task.update_status(TaskStatus.FAILED)
                        return
                    except Exception as e:
                        task.set_error(str(e))
                        task.update_status(TaskStatus.FAILED)
                        return

                if next_node_override and self.nodes and next_node_override in self.nodes:
                    # Find the step containing next_node_override
                    found_step = None
                    for si, s in enumerate(plan):
                        if next_node_override in s.nodes:
                            found_step = si
                            break
                    if found_step is not None:
                        step_index = found_step
                    else:
                        step_index += 1
                else:
                    step_index += 1

                iteration += 1
                if self.execution_state.total_iterations is not None:
                    self.execution_state.total_iterations += 1

            task.update_status(TaskStatus.COMPLETE)

        except Exception as e:
            task.set_error(str(e))
            task.update_status(TaskStatus.FAILED)

    async def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        import tempfile
        snap_dir = pathlib.Path(tempfile.mkdtemp()) / name_hint
        snap_dir.mkdir(parents=True, exist_ok=True)

        state = {
            "task": task.model_dump(mode="json"),
            "node_results": self.node_results or {},
            "execution_state": (
                self.execution_state.model_dump(mode="json")
                if self.execution_state
                else None
            ),
        }
        with open(snap_dir / "state.json", "w") as f:
            json.dump(state, f, default=str)

        return snap_dir

    async def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        state_file = snapshot_dir / "state.json"
        if not state_file.exists():
            raise FileNotFoundError(f"Snapshot state file not found: {state_file}")

        with open(state_file) as f:
            state = json.load(f)

        self.node_results = state.get("node_results", {})
        if state.get("execution_state"):
            self.execution_state = ExecutionState(**state["execution_state"])

        task_data = state.get("task", {})
        task = Task(**task_data)
        await self.run_task(task)


# ---------------------------------------------------------------------------
# asimov.graph.agent_directed_flow
# ---------------------------------------------------------------------------

class InferenceClient:
    async def generate(self, prompt: str, **kwargs) -> str:
        return ""


class Example(BaseModel):
    message: str = ""
    choice: str = ""
    choices: List[Dict[str, str]] = Field(default_factory=list)
    reasoning: str = ""

    model_config = {"arbitrary_types_allowed": True}


class AgentDrivenFlowDecision(FlowDecision):
    examples: Optional[List[Example]] = None


class AgentDrivenFlowControlConfig(FlowControlConfig):
    decisions: Sequence[AgentDrivenFlowDecision] = []
    default: Optional[str] = None


class AgentDirectedFlowControl(FlowControlModule):
    flow_config: Optional[AgentDrivenFlowControlConfig] = None
    inference_client: Optional[InferenceClient] = None
    input_var: Optional[str] = None
    system_description: str = ""
    use_historicals: Optional[bool] = None
    voters: int = 1

    model_config = {"arbitrary_types_allowed": True}

    def set_attrs(self) -> None:
        pass

    def most_common_string(self, string_list: List[str]) -> str:
        if not string_list:
            return ""
        counter = Counter(string_list)
        return counter.most_common(1)[0][0]

    async def gen(self, generation_input: Any, cache: Cache) -> str:
        if self.inference_client is None:
            return ""
        prompt = str(generation_input)
        return await self.inference_client.generate(prompt)

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.flow_config is None:
            return {}

        generation_input = None
        if self.input_var:
            generation_input = cache.get(self.input_var)

        votes: List[str] = []
        for _ in range(self.voters):
            vote = await self.gen(generation_input, cache)
            votes.append(vote)

        chosen = self.most_common_string(votes)

        for decision in self.flow_config.decisions:
            if decision.next_node == chosen:
                return {"next_node": decision.next_node}

        if self.flow_config.default:
            return {"next_node": self.flow_config.default}

        return {}

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


# ---------------------------------------------------------------------------
# asimov.executors.executor (re-export)
# ---------------------------------------------------------------------------

__all__ = [
    "AsimovBase",
    "Task",
    "TaskStatus",
    "ModelFamily",
    "ModuleType",
    "SnapshotControl",
    "NonRetryableException",
    "Middleware",
    "ModuleConfig",
    "NodeConfig",
    "FlowDecision",
    "FlowControlConfig",
    "ExecutionStep",
    "ExecutionState",
    "Cache",
    "AgentModule",
    "CompositeModule",
    "Node",
    "FlowControlModule",
    "Executor",
    "Agent",
    "InferenceClient",
    "Example",
    "AgentDrivenFlowDecision",
    "AgentDrivenFlowControlConfig",
    "AgentDirectedFlowControl",
]