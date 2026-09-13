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
    Tuple,
)
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# asimov/asimov_base.py
# ---------------------------------------------------------------------------

class AsimovBase(BaseModel):
    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# asimov/constants.py
# ---------------------------------------------------------------------------

class ModelFamily(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    COHERE = "cohere"


# ---------------------------------------------------------------------------
# asimov/graph/__init__.py  (core graph types)
# ---------------------------------------------------------------------------

class ModuleType(Enum):
    EXECUTOR = "executor"
    FLOW_CONTROL = "flow_control"
    COMPOSITE = "composite"
    AGENT_DIRECTED_FLOW = "agent_directed_flow"


class SnapshotControl(Enum):
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
    max_retries: int = 3
    max_visits: Optional[int] = None
    outputs: Optional[List[str]] = None
    parallel: bool = False
    retry_from: Optional[str] = None
    retry_on_failure: bool = True


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


class ExecutionStep(BaseModel):
    nodes: List[str] = Field(default_factory=list)
    executed: List[bool] = Field(default_factory=list)
    skipped: List[bool] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        if len(self.executed) != len(self.nodes):
            self.executed = [False] * len(self.nodes)
        if len(self.skipped) != len(self.nodes):
            self.skipped = [False] * len(self.nodes)


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
            if 0 <= node_index < len(step.nodes):
                step.executed[node_index] = True

    def was_executed(self, node_name: str) -> bool:
        if self.current_plan is None:
            return False
        for step in self.current_plan:
            for i, name in enumerate(step.nodes):
                if name == node_name and step.executed[i]:
                    return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if self.current_plan is None:
            return False
        for step in self.current_plan:
            for i, name in enumerate(step.nodes):
                if name == node_name and step.skipped[i]:
                    return True
        return False


# ---------------------------------------------------------------------------
# Cache placeholder (used throughout)
# ---------------------------------------------------------------------------

class Cache:
    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def keys(self):
        return set(self._store.keys())

    def __contains__(self, key: str) -> bool:
        return key in self._store


# ---------------------------------------------------------------------------
# AgentModule
# ---------------------------------------------------------------------------

class AgentModule(AsimovBase):
    config: Optional[ModuleConfig] = None
    container: Optional[Any] = None  # 'CompositeModule'
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = 0
    input_mailboxes: Optional[List[str]] = None
    name: str = ""
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = False
    type: Optional[ModuleType] = None

    def is_success(self, result: Dict[str, Any]) -> bool:
        if result is None:
            return False
        status = result.get("status", "")
        if isinstance(status, str):
            return status.lower() in ("success", "complete", "completed")
        return bool(status)

    @abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> "Awaitable[dict[str, Any]] | AsyncGenerator":
        raise NotImplementedError

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        if self.executions is None:
            self.executions = 0
        self.executions += 1

        timeout = 300.0
        if self.config and self.config.timeout:
            timeout = self.config.timeout

        try:
            result = await asyncio.wait_for(
                self._run_process(cache, semaphore), timeout=timeout
            )
        except asyncio.TimeoutError:
            result = {"status": "error", "error": "timeout"}

        return result

    async def _run_process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        result = self.process(cache, semaphore)
        if asyncio.iscoroutine(result):
            return await result
        elif hasattr(result, "__aiter__"):
            collected: Dict[str, Any] = {}
            async for chunk in result:
                if isinstance(chunk, dict):
                    collected.update(chunk)
            return collected
        else:
            return await result


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
            if self.config and self.config.stop_on_success:
                if module.is_success(result):
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

        if self.config and self.config.middlewares:
            result = await self.apply_middlewares(
                self.config.middlewares, result, cache
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

    _nodes_registry: Optional[Dict[str, "Node"]] = None

    def get_nodes(self) -> Optional[Dict[str, "Node"]]:
        return self._nodes_registry

    def set_nodes(self, nodes: Dict[str, "Node"]) -> None:
        self._nodes_registry = nodes

    async def cancel_gen(self, agen: AsyncGenerator) -> None:
        try:
            await agen.aclose()
        except Exception:
            pass

    async def cleanup(self) -> None:
        pass

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        modules = self.modules or []
        node_config = self.node_config or NodeConfig()
        parallel = node_config.parallel

        if parallel:
            result = await self.run_parallel_modules(cache, semaphore)
        else:
            result = await self.run_sequential_modules(cache, semaphore)

        if self.config and self.config.middlewares:
            result = await self.apply_middlewares(
                self.config.middlewares, result, cache
            )

        return result

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
        self, condition: str, cache: Cache, cache_keys: set
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
            return {"status": "success", "next_node": None}

        cache_keys = cache.keys() if hasattr(cache, "keys") else set()

        for decision in self.flow_config.decisions:
            if decision.condition is None:
                return {
                    "status": "success",
                    "next_node": decision.next_node,
                    "cleanup_on_jump": decision.cleanup_on_jump,
                }
            condition_keys = set(decision.condition_variables or []) | cache_keys
            if self.evaluate_condition(decision.condition, cache, condition_keys):
                return {
                    "status": "success",
                    "next_node": decision.next_node,
                    "cleanup_on_jump": decision.cleanup_on_jump,
                }

        default_node = self.flow_config.default
        return {
            "status": "success",
            "next_node": default_node,
            "cleanup_on_default": self.flow_config.cleanup_on_default,
        }

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


# ---------------------------------------------------------------------------
# asimov/graph/tasks.py
# ---------------------------------------------------------------------------

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(AsimovBase):
    error: Optional[str] = None
    id: Optional[UUID] = Field(default_factory=uuid.uuid4)
    model_config = {"arbitrary_types_allowed": True}
    objective: str
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    status: TaskStatus = TaskStatus.PENDING
    type: str = "task"

    def set_error(self, error: str) -> None:
        self.error = error
        self.status = TaskStatus.FAILED

    def set_result(self, result: Any) -> None:
        self.result = result
        self.status = TaskStatus.COMPLETE

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


# ---------------------------------------------------------------------------
# asimov/executors/executor.py
# ---------------------------------------------------------------------------

class Executor(AgentModule):
    type: Optional[ModuleType] = ModuleType.EXECUTOR

    @abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# asimov/graph/agent_directed_flow.py
# ---------------------------------------------------------------------------

class Example(BaseModel):
    choice: str
    choices: List[Dict[str, str]] = Field(default_factory=list)
    message: str
    reasoning: str


class AgentDrivenFlowDecision(FlowDecision):
    examples: Optional[List[Example]] = None


class AgentDrivenFlowControlConfig(FlowControlConfig):
    decisions: Sequence[AgentDrivenFlowDecision] = Field(default_factory=list)
    default: Optional[str] = None


class InferenceClient:
    async def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        return ""


class AgentDirectedFlowControl(FlowControlModule):
    flow_config: Optional[AgentDrivenFlowControlConfig] = None
    inference_client: Optional[InferenceClient] = None
    input_var: Optional[str] = None
    system_description: str = ""
    use_historicals: Optional[bool] = True
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
        system = self.system_description
        response = await self.inference_client.generate(prompt, system=system)
        return response

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.flow_config is None:
            return {"status": "success", "next_node": None}

        input_data = None
        if self.input_var:
            input_data = cache.get(self.input_var)

        votes: List[str] = []
        for _ in range(self.voters):
            response = await self.gen(input_data, cache)
            votes.append(response.strip())

        chosen = self.most_common_string(votes)

        for decision in self.flow_config.decisions:
            if decision.next_node == chosen:
                return {
                    "status": "success",
                    "next_node": decision.next_node,
                    "cleanup_on_jump": decision.cleanup_on_jump,
                }

        default_node = self.flow_config.default
        return {
            "status": "success",
            "next_node": default_node,
            "cleanup_on_default": self.flow_config.cleanup_on_default,
        }

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


# ---------------------------------------------------------------------------
# asimov/graph/Agent
# ---------------------------------------------------------------------------

class Agent(AsimovBase):
    auto_snapshot: bool = False
    cache: Optional[Cache] = None
    error_mailbox: str = "error"
    execution_state: Optional[ExecutionState] = None
    graph: Optional[Dict[str, List[str]]] = None
    max_concurrent_tasks: Optional[int] = None
    max_total_iterations: Optional[int] = None
    node_results: Optional[Dict[str, Any]] = None
    nodes: Optional[Dict[str, Node]] = None
    output_mailbox: str = "output"

    _semaphore: Optional[asyncio.Semaphore] = None

    def set_semaphore(self) -> None:
        max_tasks = self.max_concurrent_tasks or 10
        self._semaphore = asyncio.Semaphore(max_tasks)

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
        if self.nodes is None or self.graph is None:
            return []

        in_degree: Dict[str, int] = {name: 0 for name in self.nodes}
        for node_name, dependents in self.graph.items():
            for dep in dependents:
                if dep in in_degree:
                    in_degree[dep] += 1

        plan: ExecutionPlan = []
        visited: set = set()
        queue = [n for n, d in in_degree.items() if d == 0]

        while queue:
            step_nodes = sorted(queue)
            step = ExecutionStep(nodes=step_nodes)
            plan.append(step)
            visited.update(step_nodes)
            next_queue: List[str] = []
            for node_name in step_nodes:
                for dependent in self.graph.get(node_name, []):
                    if dependent not in visited:
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
        for i, step in enumerate(execution_plan):
            if node in step.nodes:
                return execution_plan[i:]
        return execution_plan

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        if self.graph is None:
            return ()
        visited: set = set()
        queue = [node_name]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for dep in self.graph.get(current, []):
                if dep not in visited:
                    queue.append(dep)
        visited.discard(node_name)
        return tuple(visited)

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if self.execution_state is None or self.execution_state.current_plan is None:
            return
        to_skip = {node_name} | set(self.get_dependent_chains(node_name))
        for step in self.execution_state.current_plan:
            for i, name in enumerate(step.nodes):
                if name in to_skip:
                    step.skipped[i] = True

    def is_success(self, result: Any) -> bool:
        if result is None:
            return False
        if isinstance(result, dict):
            status = result.get("status", "")
            if isinstance(status, str):
                return status.lower() in ("success", "complete", "completed")
            return bool(status)
        return bool(result)

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if self.nodes is None or node_name not in self.nodes:
            return {"status": "error", "error": f"Node {node_name} not found"}

        node = self.nodes[node_name]
        cache = self.cache or Cache()

        if self._semaphore is None:
            self.set_semaphore()

        semaphore = self._semaphore

        node_config = node.node_config or NodeConfig()
        max_retries = node_config.max_retries
        retry_on_failure = node_config.retry_on_failure

        result: Dict[str, Any] = {}
        for attempt in range(max_retries + 1):
            try:
                result = await node.run(cache, semaphore)
                if self.is_success(result):
                    break
                if not retry_on_failure:
                    break
            except NonRetryableException as e:
                result = {"status": "error", "error": str(e)}
                break
            except Exception as e:
                result = {"status": "error", "error": str(e)}
                if not retry_on_failure or attempt >= max_retries:
                    break

        if self.node_results is None:
            self.node_results = {}
        self.node_results[node_name] = result

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
            await self._execute_plan(task)
            if task.status == TaskStatus.RUNNING:
                output = self.cache.get(self.output_mailbox)
                task.set_result(output)
        except Exception as e:
            error_msg = str(e)
            self.cache.set(self.error_mailbox, error_msg)
            task.set_error(error_msg)

    async def _execute_plan(self, task: Task) -> None:
        if self.execution_state is None or self.execution_state.current_plan is None:
            return

        plan = self.execution_state.current_plan
        iteration = 0
        step_index = 0

        while step_index < len(plan):
            if (
                self.max_total_iterations is not None
                and iteration >= self.max_total_iterations
            ):
                break

            step = plan[step_index]
            next_step_index = step_index + 1
            jump_node: Optional[str] = None

            for node_index, node_name in enumerate(step.nodes):
                if step.skipped[node_index]:
                    continue
                if step.executed[node_index]:
                    continue

                result = await self.run_node(node_name)
                self.execution_state.mark_executed(step_index, node_index)
                iteration += 1

                if self.auto_snapshot:
                    await self.snapshot(task, node_name)

                if not self.is_success(result):
                    node = self.nodes.get(node_name) if self.nodes else None
                    node_config = node.node_config if node else None
                    if node_config and node_config.retry_from:
                        jump_node = node_config.retry_from
                        break
                    self.mark_node_and_deps_as_skipped(node_name)
                else:
                    next_node = result.get("next_node")
                    if next_node:
                        jump_node = next_node
                        break

            if jump_node:
                new_plan = self.compile_execution_plan_from(jump_node)
                self.execution_state.current_plan = new_plan
                if self.execution_state.execution_history is not None:
                    self.execution_state.execution_history.append(plan)
                plan = new_plan
                step_index = 0
            else:
                step_index = next_step_index

        if self.execution_state.total_iterations is not None:
            self.execution_state.total_iterations += iteration

    async def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        snapshot_dir = pathlib.Path(f"snapshots/{task.id}/{name_hint}")
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        state_file = snapshot_dir / "state.json"
        state_data = {
            "task_id": str(task.id),
            "task_status": task.status.value,
            "node_results": self.node_results or {},
            "name_hint": name_hint,
        }
        with open(state_file, "w") as f:
            json.dump(state_data, f, default=str)

        return snapshot_dir

    async def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        state_file = snapshot_dir / "state.json"
        if not state_file.exists():
            raise FileNotFoundError(f"Snapshot state file not found: {state_file}")

        with open(state_file, "r") as f:
            state_data = json.load(f)

        if self.node_results is None:
            self.node_results = {}
        self.node_results.update(state_data.get("node_results", {}))

        last_node = state_data.get("name_hint", "")
        if last_node and self.nodes and last_node in self.nodes:
            plan = self.compile_execution_plan_from(last_node)
        else:
            plan = self.compile_execution_plan()

        self.execution_state = ExecutionState(
            current_plan=plan,
            execution_history=[],
            execution_index=0,
            total_iterations=0,
        )


# ---------------------------------------------------------------------------
# Rebuild forward references
# ---------------------------------------------------------------------------

AgentModule.model_rebuild()
CompositeModule.model_rebuild()
Node.model_rebuild()
Agent.model_rebuild()
FlowControlModule.model_rebuild()
AgentDirectedFlowControl.model_rebuild()