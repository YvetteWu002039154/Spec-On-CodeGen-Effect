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


# ─────────────────────────────────────────────
# asimov/asimov_base.py
# ─────────────────────────────────────────────

class AsimovBase(BaseModel):
    model_config = {"arbitrary_types_allowed": True}


# ─────────────────────────────────────────────
# asimov/constants.py
# ─────────────────────────────────────────────

class ModelFamily(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    META = "meta"


# ─────────────────────────────────────────────
# asimov/graph/tasks.py
# ─────────────────────────────────────────────

class TaskStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(AsimovBase):
    model_config = {"arbitrary_types_allowed": True}

    id: Optional[UUID] = Field(default_factory=uuid.uuid4)
    objective: str
    type: str = "task"
    status: TaskStatus = TaskStatus.CREATED
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[str] = None

    def update_status(self, status: TaskStatus) -> None:
        self.status = status

    def set_result(self, result: Any) -> None:
        self.result = result
        self.status = TaskStatus.COMPLETE

    def set_error(self, error: str) -> None:
        self.error = error
        self.status = TaskStatus.FAILED


# ─────────────────────────────────────────────
# asimov/graph/__init__.py  (core graph types)
# ─────────────────────────────────────────────

class ModuleType(Enum):
    EXECUTOR = "executor"
    FLOW_CONTROL = "flow_control"
    COMPOSITE = "composite"
    SUBAGENT = "subagent"


class SnapshotControl(Enum):
    ALWAYS = "always"
    NEVER = "never"
    ON_SUCCESS = "on_success"
    ON_FAILURE = "on_failure"


class NonRetryableException(Exception):
    pass


class Cache:
    """Simple in-memory cache used throughout the graph."""

    def __init__(self):
        self._data: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def keys(self) -> Set[str]:
        return set(self._data.keys())

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    def update(self, data: Dict[str, Any]) -> None:
        self._data.update(data)


class Middleware(AsimovBase):
    async def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        return data


class ModuleConfig(AsimovBase):
    context: Optional[Dict[str, Any]] = None
    middlewares: Optional[List[Middleware]] = None
    stop_on_success: bool = False
    timeout: float = 300.0


class AgentModule(AsimovBase):
    name: str = ""
    type: Optional[ModuleType] = None
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = None
    input_mailboxes: Optional[List[str]] = None
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = None
    config: Optional[ModuleConfig] = None
    container: Optional[Any] = None  # forward ref to CompositeModule

    def is_success(self, result: Dict[str, Any]) -> bool:
        if result is None:
            return False
        status = result.get("status")
        if status is not None:
            return status not in ("error", "failed", TaskStatus.FAILED)
        return True

    @abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> "Awaitable[dict[str, Any]] | AsyncGenerator":
        raise NotImplementedError

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.executions is not None:
            self.executions += 1
        else:
            self.executions = 1

        timeout = None
        if self.config and self.config.timeout:
            timeout = self.config.timeout

        try:
            if timeout:
                result = await asyncio.wait_for(
                    self._run_process(cache, semaphore), timeout=timeout
                )
            else:
                result = await self._run_process(cache, semaphore)
        except asyncio.TimeoutError:
            return {"status": "error", "error": "timeout"}

        return result

    async def _run_process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        result = self.process(cache, semaphore)
        if asyncio.iscoroutine(result):
            return await result
        elif hasattr(result, "__aiter__"):
            collected = {}
            async for chunk in result:
                if isinstance(chunk, dict):
                    collected.update(chunk)
            return collected
        else:
            return await result


class CompositeModule(AgentModule):
    modules: List[AgentModule] = Field(default_factory=list)
    node_config: Optional["NodeConfig"] = None

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            return await self.run_parallel_modules(cache, semaphore)
        return await self.run_sequential_modules(cache, semaphore)

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.process(cache, semaphore)

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
            if isinstance(result, dict):
                combined.update(result)
            if self.node_config and self.node_config.max_retries:
                pass  # retry logic handled at Node level
            # apply middlewares if configured
            if module.config and module.config.middlewares:
                result = await self.apply_middlewares(
                    module.config.middlewares, result, cache
                )
                combined.update(result)
            if module.config and module.config.stop_on_success:
                if module.is_success(result):
                    break
        return combined


class NodeConfig(AsimovBase):
    parallel: bool = False
    max_retries: int = 0
    retry_on_failure: bool = False
    retry_from: Optional[str] = None
    condition: Optional[str] = None
    inputs: Optional[List[str]] = None
    outputs: Optional[List[str]] = None
    max_visits: Optional[int] = None


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

    def cleanup(self) -> None:
        pass

    async def cancel_gen(self, agen: AsyncGenerator) -> None:
        await agen.aclose()

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            return await self.run_parallel_modules(cache, semaphore)
        return await self.run_sequential_modules(cache, semaphore)


class FlowDecision(AsimovBase):
    next_node: str
    condition: Optional[str] = None
    condition_variables: Optional[List[str]] = None
    cleanup_on_jump: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class FlowControlConfig(AsimovBase):
    decisions: Sequence[FlowDecision] = Field(default_factory=list)
    default: Optional[str] = None
    cleanup_on_default: bool = False


class FlowControlModule(AgentModule):
    flow_config: Optional[FlowControlConfig] = None

    def evaluate_condition(
        self, condition: str, cache: Cache, cache_keys: Set[str]
    ) -> bool:
        try:
            context = {k: cache.get(k) for k in cache_keys}
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception:
            return False

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if not self.flow_config:
            return {"status": "error", "error": "no flow_config"}

        for decision in self.flow_config.decisions:
            if decision.condition is None:
                return {"next_node": decision.next_node, "status": "success"}

            cache_keys = set(decision.condition_variables or []) | cache.keys()
            if self.evaluate_condition(decision.condition, cache, cache_keys):
                if decision.cleanup_on_jump:
                    pass  # cleanup logic
                return {"next_node": decision.next_node, "status": "success"}

        if self.flow_config.default:
            if self.flow_config.cleanup_on_default:
                pass  # cleanup logic
            return {"next_node": self.flow_config.default, "status": "success"}

        return {"status": "error", "error": "no matching decision"}


# ─────────────────────────────────────────────
# asimov/graph/execution.py
# ─────────────────────────────────────────────

class ExecutionStep(AsimovBase):
    nodes: List[str] = Field(default_factory=list)
    executed: List[bool] = Field(default_factory=list)
    skipped: List[bool] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        if len(self.executed) < len(self.nodes):
            self.executed.extend([False] * (len(self.nodes) - len(self.executed)))
        if len(self.skipped) < len(self.nodes):
            self.skipped.extend([False] * (len(self.nodes) - len(self.skipped)))


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
            for i, name in enumerate(step.nodes):
                if name == node_name and i < len(step.executed) and step.executed[i]:
                    return True
        if self.execution_history:
            for plan in self.execution_history:
                for step in plan:
                    for i, name in enumerate(step.nodes):
                        if (
                            name == node_name
                            and i < len(step.executed)
                            and step.executed[i]
                        ):
                            return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan:
            for i, name in enumerate(step.nodes):
                if name == node_name and i < len(step.skipped) and step.skipped[i]:
                    return True
        return False


# ─────────────────────────────────────────────
# asimov/executors/executor.py
# ─────────────────────────────────────────────

class Executor(AgentModule):
    type: Optional[ModuleType] = ModuleType.EXECUTOR

    @abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        raise NotImplementedError


# ─────────────────────────────────────────────
# asimov/graph/agent_directed_flow.py
# ─────────────────────────────────────────────

class InferenceClient:
    """Minimal stub for an inference client."""

    async def generate(self, prompt: str, **kwargs) -> str:
        return ""


class Example(AsimovBase):
    message: str
    choices: List[Dict[str, str]] = Field(default_factory=list)
    choice: str
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
        if not self.flow_config:
            return {"status": "error", "error": "no flow_config"}

        generation_input = None
        if self.input_var:
            generation_input = cache.get(self.input_var)

        votes: List[str] = []
        for _ in range(self.voters):
            response = await self.gen(generation_input, cache)
            votes.append(response)

        chosen = self.most_common_string(votes)

        for decision in self.flow_config.decisions:
            if decision.next_node == chosen:
                return {"next_node": decision.next_node, "status": "success"}

        if self.flow_config.default:
            return {"next_node": self.flow_config.default, "status": "success"}

        return {"status": "error", "error": "no matching decision"}

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


# ─────────────────────────────────────────────
# asimov/graph/agent.py  (Agent)
# ─────────────────────────────────────────────

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

    def compile_execution_plan(self) -> ExecutionPlan:
        if not self.nodes or not self.graph:
            return []

        in_degree: Dict[str, int] = {name: 0 for name in self.nodes}
        for node_name, deps in self.graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        plan: ExecutionPlan = []
        visited: Set[str] = set()
        queue = [n for n, d in in_degree.items() if d == 0]

        while queue:
            step_nodes = sorted(queue)
            step = ExecutionStep(
                nodes=step_nodes,
                executed=[False] * len(step_nodes),
                skipped=[False] * len(step_nodes),
            )
            plan.append(step)
            next_queue: List[str] = []
            for node_name in step_nodes:
                visited.add(node_name)
                for child in self.graph.get(node_name, []):
                    in_degree[child] -= 1
                    if in_degree[child] == 0 and child not in visited:
                        next_queue.append(child)
            queue = next_queue

        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        full_plan = self.compile_execution_plan()
        return self.slice_before_node(full_plan, start_node)

    def slice_before_node(
        self, execution_plan: List[ExecutionStep], node: str
    ) -> List[ExecutionStep]:
        for i, step in enumerate(execution_plan):
            if node in step.nodes:
                return execution_plan[i:]
        return execution_plan

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        if not self.graph:
            return ()
        visited: Set[str] = set()
        queue = [node_name]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for child in self.graph.get(current, []):
                queue.append(child)
        visited.discard(node_name)
        return tuple(visited)

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if not self.execution_state or not self.execution_state.current_plan:
            return
        nodes_to_skip = {node_name} | set(self.get_dependent_chains(node_name))
        for step in self.execution_state.current_plan:
            for i, name in enumerate(step.nodes):
                if name in nodes_to_skip:
                    step.skipped[i] = True

    def is_success(self, result: Any) -> bool:
        if result is None:
            return False
        if isinstance(result, dict):
            status = result.get("status")
            if status is not None:
                return status not in ("error", "failed")
        return True

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if not self.nodes or node_name not in self.nodes:
            return {"status": "error", "error": f"node {node_name} not found"}

        node = self.nodes[node_name]
        cache = self.cache or Cache()
        semaphore = self._semaphore or asyncio.Semaphore(10)

        node_config = node.node_config
        max_retries = node_config.max_retries if node_config else 0
        retry_on_failure = node_config.retry_on_failure if node_config else False

        # Check condition
        if node_config and node_config.condition:
            try:
                context = {k: cache.get(k) for k in cache.keys()}
                if not eval(node_config.condition, {"__builtins__": {}}, context):
                    self.mark_node_and_deps_as_skipped(node_name)
                    return {"status": "skipped"}
            except Exception:
                pass

        attempts = 0
        result: Dict[str, Any] = {}
        while True:
            try:
                result = await node.run(cache, semaphore)
                break
            except NonRetryableException as e:
                result = {"status": "error", "error": str(e)}
                break
            except Exception as e:
                attempts += 1
                if retry_on_failure and attempts <= max_retries:
                    continue
                result = {"status": "error", "error": str(e)}
                break

        if self.node_results is None:
            self.node_results = {}
        self.node_results[node_name] = result

        if isinstance(result, dict):
            cache.update({k: v for k, v in result.items() if k != "status"})

        return result

    async def run_task(self, task: Task) -> None:
        task.update_status(TaskStatus.RUNNING)

        if self.cache is None:
            self.cache = Cache()

        self.cache.set("task", task)
        self.cache.set("objective", task.objective)
        if task.params:
            for k, v in task.params.items():
                self.cache.set(k, v)

        self.set_semaphore()

        plan = self.compile_execution_plan()
        self.execution_state = ExecutionState(
            current_plan=plan,
            execution_history=[],
            execution_index=0,
            total_iterations=0,
        )

        iteration = 0
        step_index = 0

        while step_index < len(plan):
            if (
                self.max_total_iterations is not None
                and iteration >= self.max_total_iterations
            ):
                task.set_error("max_total_iterations exceeded")
                return

            step = plan[step_index]
            next_node_override: Optional[str] = None

            if self.node_config_parallel(step):
                tasks_coros = []
                for i, node_name in enumerate(step.nodes):
                    if step.skipped[i]:
                        continue
                    tasks_coros.append(self.run_node(node_name))
                results = await asyncio.gather(*tasks_coros, return_exceptions=True)
                for i, res in enumerate(results):
                    if isinstance(res, dict):
                        self.execution_state.mark_executed(step_index, i)
            else:
                for i, node_name in enumerate(step.nodes):
                    if step.skipped[i]:
                        continue
                    result = await self.run_node(node_name)
                    self.execution_state.mark_executed(step_index, i)

                    if isinstance(result, dict) and "next_node" in result:
                        next_node_override = result["next_node"]

                    if self.auto_snapshot:
                        await self._do_snapshot(task, node_name)

            if next_node_override and self.nodes and next_node_override in self.nodes:
                new_plan = self.compile_execution_plan_from(next_node_override)
                if self.execution_state.execution_history is None:
                    self.execution_state.execution_history = []
                self.execution_state.execution_history.append(plan)
                plan = new_plan
                self.execution_state.current_plan = plan
                step_index = 0
                iteration += 1
                if self.execution_state.total_iterations is not None:
                    self.execution_state.total_iterations += 1
                continue

            step_index += 1
            iteration += 1
            if self.execution_state.total_iterations is not None:
                self.execution_state.total_iterations += 1

        output = self.cache.get(self.output_mailbox)
        error = self.cache.get(self.error_mailbox)

        if error:
            task.set_error(str(error))
        else:
            task.set_result(output)

    def node_config_parallel(self, step: ExecutionStep) -> bool:
        if not self.nodes:
            return False
        for node_name in step.nodes:
            node = self.nodes.get(node_name)
            if node and node.node_config and node.node_config.parallel:
                return True
        return len(step.nodes) > 1

    async def _do_snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        return await asyncio.get_event_loop().run_in_executor(
            None, self._snapshot_sync, task, name_hint
        )

    def _snapshot_sync(self, task: Task, name_hint: str) -> pathlib.Path:
        import tempfile
        snap_dir = pathlib.Path(tempfile.mkdtemp())
        data = {
            "task_id": str(task.id),
            "name_hint": name_hint,
            "node_results": self.node_results or {},
            "cache": self.cache.to_dict() if self.cache else {},
        }
        snap_file = snap_dir / "snapshot.json"
        with open(snap_file, "w") as f:
            json.dump(data, f, default=str)
        return snap_dir

    async def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        return await self._do_snapshot(task, name_hint)

    async def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        snap_file = snapshot_dir / "snapshot.json"
        if not snap_file.exists():
            raise FileNotFoundError(f"Snapshot not found: {snap_file}")
        with open(snap_file) as f:
            data = json.load(f)
        if self.cache is None:
            self.cache = Cache()
        cache_data = data.get("cache", {})
        self.cache.update(cache_data)
        self.node_results = data.get("node_results", {})


# ─────────────────────────────────────────────
# Re-export everything at package level
# ─────────────────────────────────────────────

__all__ = [
    "AsimovBase",
    "ModelFamily",
    "TaskStatus",
    "Task",
    "ModuleType",
    "SnapshotControl",
    "NonRetryableException",
    "Cache",
    "Middleware",
    "ModuleConfig",
    "AgentModule",
    "CompositeModule",
    "NodeConfig",
    "Node",
    "FlowDecision",
    "FlowControlConfig",
    "FlowControlModule",
    "ExecutionStep",
    "ExecutionPlan",
    "ExecutionState",
    "Executor",
    "InferenceClient",
    "Example",
    "AgentDrivenFlowDecision",
    "AgentDrivenFlowControlConfig",
    "AgentDirectedFlowControl",
    "Agent",
]