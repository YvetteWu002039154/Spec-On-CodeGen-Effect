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

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def keys(self) -> Set[str]:
        return set(self._data.keys())

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __repr__(self) -> str:
        return f"Cache({self._data})"


class Middleware(AsimovBase):
    async def process(self, data: Dict[str, Any], cache: "Cache") -> Dict[str, Any]:
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
        step = self.current_plan[step_index]
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


class AgentModule(AsimovBase):
    name: str
    type: Optional[ModuleType] = None
    config: Optional[ModuleConfig] = None
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = None
    input_mailboxes: Optional[List[str]] = None
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = None
    container: Optional[Any] = None  # forward ref to CompositeModule

    def is_success(self, result: Dict[str, Any]) -> bool:
        return result.get("status") != "failure"

    @abstractmethod
    async def process(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> "Awaitable[dict[str, Any]] | AsyncGenerator":
        raise NotImplementedError

    async def run(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        timeout = 300.0
        if self.config is not None:
            timeout = self.config.timeout

        result = await asyncio.wait_for(
            self._run_process(cache, semaphore), timeout=timeout
        )
        if self.executions is not None:
            self.executions += 1
        else:
            self.executions = 1
        return result

    async def _run_process(
        self, cache: "Cache", semaphore: asyncio.Semaphore
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


class CompositeModule(AgentModule):
    modules: List[AgentModule] = Field(default_factory=list)
    node_config: Optional[NodeConfig] = None

    async def process(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            return await self.run_parallel_modules(cache, semaphore)
        return await self.run_sequential_modules(cache, semaphore)

    async def apply_middlewares(
        self,
        middlewares: List[Middleware],
        data: Dict[str, Any],
        cache: "Cache",
    ) -> Dict[str, Any]:
        for mw in middlewares:
            data = await mw.process(data, cache)
        return data

    async def run_module_with_concurrency_control(
        self,
        module: AgentModule,
        cache: "Cache",
        semaphore: asyncio.Semaphore,
    ) -> Dict[str, Any]:
        async with semaphore:
            return await module.run(cache, semaphore)

    async def run_parallel_modules(
        self, cache: "Cache", semaphore: asyncio.Semaphore
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
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        combined: Dict[str, Any] = {}
        for module in self.modules:
            result = await module.run(cache, semaphore)
            combined.update(result)
            if self.config and self.config.stop_on_success:
                if module.is_success(result):
                    break
            if self.config and self.config.middlewares:
                combined = await self.apply_middlewares(
                    self.config.middlewares, combined, cache
                )
        return combined

    async def run(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.process(cache, semaphore)


class FlowControlModule(AgentModule):
    flow_config: FlowControlConfig = Field(default_factory=FlowControlConfig)

    def evaluate_condition(
        self, condition: str, cache: "Cache", cache_keys: set
    ) -> bool:
        local_vars: Dict[str, Any] = {}
        for key in cache_keys:
            local_vars[key] = cache.get(key)
        try:
            return bool(eval(condition, {}, local_vars))
        except Exception:
            return False

    async def process(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        cache_keys = cache.keys()
        for decision in self.flow_config.decisions:
            if decision.condition is None:
                return {"next_node": decision.next_node}
            if self.evaluate_condition(decision.condition, cache, cache_keys):
                if decision.cleanup_on_jump and decision.condition_variables:
                    for var in decision.condition_variables:
                        cache.delete(var)
                return {"next_node": decision.next_node}

        if self.flow_config.default is not None:
            if self.flow_config.cleanup_on_default:
                for decision in self.flow_config.decisions:
                    if decision.condition_variables:
                        for var in decision.condition_variables:
                            cache.delete(var)
            return {"next_node": self.flow_config.default}

        return {"next_node": None}

    async def run(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.process(cache, semaphore)


class Node(CompositeModule):
    dependencies: Optional[List[str]] = None
    modules: Optional[List[AgentModule]] = Field(default_factory=list)
    node_config: Optional[NodeConfig] = None
    snapshot: Optional[SnapshotControl] = None
    type: Optional[ModuleType] = None
    _nodes_registry: Optional[Dict[str, "Node"]] = None

    async def cancel_gen(self, agen: AsyncGenerator) -> None:
        await agen.aclose()

    async def cleanup(self) -> None:
        pass

    def get_nodes(self) -> Optional[Dict[str, "Node"]]:
        return self._nodes_registry

    def set_nodes(self, nodes: Dict[str, "Node"]) -> None:
        self._nodes_registry = nodes

    async def process(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            return await self.run_parallel_modules(cache, semaphore)
        return await self.run_sequential_modules(cache, semaphore)


# ─────────────────────────────────────────────
# asimov/executors/executor.py
# ─────────────────────────────────────────────

class Executor(AgentModule):
    type: Optional[ModuleType] = ModuleType.EXECUTOR

    @abstractmethod
    async def process(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        raise NotImplementedError


# ─────────────────────────────────────────────
# asimov/graph/agent_directed_flow.py
# ─────────────────────────────────────────────

class InferenceClient:
    """Minimal stub for an inference client."""

    async def generate(self, prompt: str, **kwargs) -> str:
        return ""


class Example(BaseModel):
    message: str
    choices: List[Dict[str, str]] = Field(default_factory=list)
    choice: str
    reasoning: str

    model_config = {"arbitrary_types_allowed": True}


class AgentDrivenFlowDecision(FlowDecision):
    examples: Optional[List[Example]] = None


class AgentDrivenFlowControlConfig(FlowControlConfig):
    decisions: Sequence[AgentDrivenFlowDecision] = []
    default: Optional[str] = None


class AgentDirectedFlowControl(FlowControlModule):
    flow_config: AgentDrivenFlowControlConfig = Field(
        default_factory=AgentDrivenFlowControlConfig
    )
    inference_client: Any = None  # InferenceClient
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

    async def gen(self, generation_input: Any, cache: "Cache") -> str:
        if self.inference_client is None:
            return ""
        prompt = str(generation_input)
        return await self.inference_client.generate(prompt)

    async def run(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        generation_input = None
        if self.input_var is not None:
            generation_input = cache.get(self.input_var)

        votes: List[str] = []
        for _ in range(self.voters):
            response = await self.gen(generation_input, cache)
            votes.append(response)

        chosen = self.most_common_string(votes)

        for decision in self.flow_config.decisions:
            if decision.next_node == chosen:
                return {"next_node": decision.next_node}

        if self.flow_config.default is not None:
            return {"next_node": self.flow_config.default}

        return {"next_node": None}

    async def process(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
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
        limit = self.max_concurrent_tasks if self.max_concurrent_tasks else 10
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
        if self.nodes is None or self.graph is None:
            return []
        return self._topological_sort(list(self.nodes.keys()))

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        if self.nodes is None or self.graph is None:
            return []
        reachable = self._get_reachable_nodes(start_node)
        return self._topological_sort(list(reachable))

    def _get_reachable_nodes(self, start: str) -> Set[str]:
        visited: Set[str] = set()
        stack = [start]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            if self.graph and node in self.graph:
                stack.extend(self.graph[node])
        return visited

    def _topological_sort(self, node_names: List[str]) -> ExecutionPlan:
        if self.nodes is None or self.graph is None:
            return []

        in_degree: Dict[str, int] = {n: 0 for n in node_names}
        for parent, children in self.graph.items():
            if parent not in in_degree:
                continue
            for child in children:
                if child in in_degree:
                    in_degree[child] += 1

        plan: ExecutionPlan = []
        remaining = set(node_names)

        while remaining:
            zero_in = [n for n in remaining if in_degree[n] == 0]
            if not zero_in:
                # cycle or disconnected – add remaining as one step
                step = ExecutionStep(
                    nodes=list(remaining),
                    executed=[False] * len(remaining),
                    skipped=[False] * len(remaining),
                )
                plan.append(step)
                break

            step = ExecutionStep(
                nodes=zero_in,
                executed=[False] * len(zero_in),
                skipped=[False] * len(zero_in),
            )
            plan.append(step)

            for n in zero_in:
                remaining.remove(n)
                if n in self.graph:
                    for child in self.graph[n]:
                        if child in in_degree:
                            in_degree[child] -= 1

        return plan

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        if self.graph is None:
            return ()
        visited: Set[str] = set()
        stack = [node_name]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            if current in self.graph:
                stack.extend(self.graph[current])
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

    def slice_before_node(
        self, execution_plan: List[dict], node: str
    ) -> List[dict]:
        result = []
        for step in execution_plan:
            nodes = step.get("nodes", []) if isinstance(step, dict) else step.nodes
            if node in nodes:
                break
            result.append(step)
        return result

    def is_success(self, result: Any) -> bool:
        if isinstance(result, dict):
            return result.get("status") != "failure"
        return True

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if self.nodes is None or node_name not in self.nodes:
            raise ValueError(f"Node '{node_name}' not found")
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()
        node = self.nodes[node_name]
        node.set_nodes(self.nodes)
        result = await node.run(self.cache, self._semaphore)
        if self.node_results is None:
            self.node_results = {}
        self.node_results[node_name] = result
        return result

    async def run_task(self, task: Task) -> None:
        task.update_status(TaskStatus.RUNNING)
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()

        self.cache.set("task", task)
        self.cache.set("objective", task.objective)
        if task.params:
            for k, v in task.params.items():
                self.cache.set(k, v)

        plan = self.compile_execution_plan()
        self.execution_state = ExecutionState(
            current_plan=plan,
            execution_history=[],
            execution_index=0,
            total_iterations=0,
        )

        try:
            await self._execute_plan(task)
            result = self.cache.get(self.output_mailbox)
            task.set_result(result)
        except Exception as exc:
            self.cache.set(self.error_mailbox, str(exc))
            task.set_error(str(exc))

    async def _execute_plan(self, task: Task) -> None:
        if self.execution_state is None or self.execution_state.current_plan is None:
            return

        max_iter = self.max_total_iterations or 1000
        iteration = 0
        step_index = 0

        while step_index < len(self.execution_state.current_plan):
            if iteration >= max_iter:
                raise RuntimeError("Max total iterations exceeded")
            iteration += 1
            if self.execution_state.total_iterations is not None:
                self.execution_state.total_iterations += 1

            step = self.execution_state.current_plan[step_index]
            next_node_override: Optional[str] = None

            for node_index, node_name in enumerate(step.nodes):
                if step.skipped[node_index]:
                    continue
                if step.executed[node_index]:
                    continue

                node = self.nodes[node_name] if self.nodes else None
                if node is None:
                    continue

                # Check node condition
                if node.node_config and node.node_config.condition:
                    cache_keys = self.cache.keys() if self.cache else set()
                    local_vars = {k: self.cache.get(k) for k in cache_keys}
                    try:
                        cond_result = eval(node.node_config.condition, {}, local_vars)
                    except Exception:
                        cond_result = False
                    if not cond_result:
                        step.skipped[node_index] = True
                        self.mark_node_and_deps_as_skipped(node_name)
                        continue

                retries = 0
                max_retries = 0
                if node.node_config:
                    max_retries = node.node_config.max_retries

                while True:
                    try:
                        result = await node.run(self.cache, self._semaphore)
                        if self.node_results is None:
                            self.node_results = {}
                        self.node_results[node_name] = result
                        self.execution_state.mark_executed(step_index, node_index)

                        if self.auto_snapshot:
                            await self.snapshot(task, node_name)

                        # Handle flow control
                        if "next_node" in result and result["next_node"] is not None:
                            next_node_override = result["next_node"]

                        break
                    except NonRetryableException:
                        raise
                    except Exception as exc:
                        if node.node_config and node.node_config.retry_on_failure and retries < max_retries:
                            retries += 1
                            continue
                        raise

            if next_node_override is not None:
                # Find the step containing next_node_override
                found = False
                for si, s in enumerate(self.execution_state.current_plan):
                    if next_node_override in s.nodes:
                        step_index = si
                        found = True
                        break
                if not found:
                    step_index += 1
            else:
                step_index += 1

    async def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        import tempfile
        snap_dir = pathlib.Path(tempfile.mkdtemp())
        snap_file = snap_dir / f"{name_hint}.json"
        data = {
            "task": {
                "id": str(task.id),
                "objective": task.objective,
                "status": task.status.value,
            },
            "node_results": self.node_results or {},
            "execution_state": {
                "execution_index": self.execution_state.execution_index
                if self.execution_state
                else None,
                "total_iterations": self.execution_state.total_iterations
                if self.execution_state
                else None,
            },
        }
        snap_file.write_text(json.dumps(data, default=str))
        return snap_dir

    async def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        snap_files = list(snapshot_dir.glob("*.json"))
        if not snap_files:
            raise FileNotFoundError("No snapshot files found")
        snap_file = snap_files[-1]
        data = json.loads(snap_file.read_text())
        task_data = data.get("task", {})
        task = Task(
            id=uuid.UUID(task_data["id"]),
            objective=task_data["objective"],
            type="task",
        )
        self.node_results = data.get("node_results", {})
        await self.run_task(task)