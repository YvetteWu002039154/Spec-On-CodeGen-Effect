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
    MISTRAL = "mistral"
    COHERE = "cohere"


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

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4)
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
    NODE = "node"


class SnapshotControl(Enum):
    BEFORE = "before"
    AFTER = "after"
    BOTH = "both"
    NEVER = "never"


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

    def keys(self) -> set:
        return set(self._data.keys())

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    def update(self, data: Dict[str, Any]) -> None:
        self._data.update(data)


class Middleware(AsimovBase):
    def process(self, data: Dict[str, Any], cache: "Cache") -> Dict[str, Any]:
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


class AgentModule(AsimovBase):
    name: str
    type: Optional[ModuleType] = None
    config: Optional[ModuleConfig] = None
    container: Optional[Any] = None  # 'CompositeModule'
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = 0
    input_mailboxes: Optional[List[str]] = None
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = False

    def is_success(self, result: Dict[str, Any]) -> bool:
        if result is None:
            return False
        return result.get("status") != "failure"

    @abstractmethod
    async def process(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> "Awaitable[dict[str, Any]] | AsyncGenerator":
        raise NotImplementedError

    async def run(
        self, cache: "Cache", semaphore: asyncio.Semaphore
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
            return {"status": "failure", "error": "timeout"}

        return result

    async def _run_process(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
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
            data = mw.process(data, cache)
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
            if isinstance(result, dict):
                combined.update(result)
                if self.config and self.config.stop_on_success:
                    if module.is_success(result):
                        break
        return combined

    async def run(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.executions is None:
            self.executions = 0
        self.executions += 1
        return await self.process(cache, semaphore)


class FlowControlModule(AgentModule):
    flow_config: FlowControlConfig = Field(default_factory=FlowControlConfig)

    def evaluate_condition(
        self, condition: str, cache: "Cache", cache_keys: set
    ) -> bool:
        try:
            context = {k: cache.get(k) for k in cache_keys}
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception:
            return False

    async def process(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)

    async def run(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        cache_keys = cache.keys()
        for decision in self.flow_config.decisions:
            if decision.condition is None:
                return {"next_node": decision.next_node, "status": "success"}
            keys = set(decision.condition_variables or []) | cache_keys
            if self.evaluate_condition(decision.condition, cache, keys):
                if decision.cleanup_on_jump:
                    pass  # cleanup logic placeholder
                return {"next_node": decision.next_node, "status": "success"}

        if self.flow_config.default:
            if self.flow_config.cleanup_on_default:
                pass  # cleanup logic placeholder
            return {"next_node": self.flow_config.default, "status": "success"}

        return {"status": "failure", "error": "no matching flow decision"}


class ExecutionStep(AsimovBase):
    nodes: List[str] = Field(default_factory=list)
    executed: List[bool] = Field(default_factory=list)
    skipped: List[bool] = Field(default_factory=list)

    def __init__(self, **data):
        super().__init__(**data)
        if len(self.executed) < len(self.nodes):
            self.executed = [False] * len(self.nodes)
        if len(self.skipped) < len(self.nodes):
            self.skipped = [False] * len(self.nodes)


ExecutionPlan = List[ExecutionStep]


class ExecutionState(AsimovBase):
    current_plan: Optional[ExecutionPlan] = None
    execution_history: Optional[List[ExecutionPlan]] = None
    execution_index: Optional[int] = 0
    total_iterations: Optional[int] = 0

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
                if name == node_name and i < len(step.executed):
                    if step.executed[i]:
                        return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan:
            for i, name in enumerate(step.nodes):
                if name == node_name and i < len(step.skipped):
                    if step.skipped[i]:
                        return True
        return False


class Node(CompositeModule):
    dependencies: Optional[List[str]] = None
    modules: List[AgentModule] = Field(default_factory=list)
    node_config: Optional[NodeConfig] = None
    snapshot: Optional[SnapshotControl] = None
    type: Optional[ModuleType] = ModuleType.NODE

    _nodes_registry: Optional[Dict[str, "Node"]] = None

    def get_nodes(self) -> Optional[Dict[str, "Node"]]:
        return self._nodes_registry

    def set_nodes(self, nodes: Dict[str, "Node"]) -> None:
        self._nodes_registry = nodes

    def cleanup(self) -> None:
        pass

    async def cancel_gen(self, agen) -> None:
        try:
            await agen.aclose()
        except Exception:
            pass

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
    async def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        return ""


class Example(AsimovBase):
    message: str
    choices: List[Dict[str, str]] = Field(default_factory=list)
    choice: str
    reasoning: str


class AgentDrivenFlowDecision(FlowDecision):
    examples: Optional[List[Example]] = None


class AgentDrivenFlowControlConfig(FlowControlConfig):
    decisions: Sequence[AgentDrivenFlowDecision] = []
    default: Optional[str] = None


class AgentDirectedFlowControl(FlowControlModule):
    flow_config: AgentDrivenFlowControlConfig = Field(
        default_factory=AgentDrivenFlowControlConfig
    )
    inference_client: Any = Field(default_factory=InferenceClient)
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

    async def gen(self, generation_input: Any, cache: "Cache") -> str:
        prompt = str(generation_input)
        system = self.system_description

        choices_text = "\n".join(
            f"- {d.next_node}" for d in self.flow_config.decisions
        )
        if self.flow_config.default:
            choices_text += f"\n- {self.flow_config.default}"

        full_prompt = f"{prompt}\n\nChoices:\n{choices_text}"

        try:
            response = await self.inference_client.generate(
                full_prompt, system=system
            )
            return response.strip()
        except Exception:
            return self.flow_config.default or ""

    async def run(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        input_data = ""
        if self.input_var:
            input_data = cache.get(self.input_var, "")

        votes = []
        for _ in range(self.voters):
            vote = await self.gen(input_data, cache)
            votes.append(vote)

        chosen = self.most_common_string(votes)

        valid_nodes = {d.next_node for d in self.flow_config.decisions}
        if self.flow_config.default:
            valid_nodes.add(self.flow_config.default)

        if chosen not in valid_nodes:
            chosen = self.flow_config.default or ""

        return {"next_node": chosen, "status": "success"}

    async def process(
        self, cache: "Cache", semaphore: asyncio.Semaphore
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
        if not self.graph:
            return ()
        visited = set()
        result = []

        def dfs(name: str):
            if name in visited:
                return
            visited.add(name)
            for dependent in self.graph.get(name, []):
                result.append(dependent)
                dfs(dependent)

        dfs(node_name)
        return tuple(result)

    def compile_execution_plan(self) -> ExecutionPlan:
        if not self.nodes:
            return []
        return self._topological_sort(list(self.nodes.keys()))

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        if not self.nodes:
            return []
        reachable = self._get_reachable_nodes(start_node)
        return self._topological_sort(list(reachable))

    def _get_reachable_nodes(self, start: str) -> set:
        visited = set()
        queue = [start]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            for dep in (self.graph or {}).get(node, []):
                queue.append(dep)
        return visited

    def _topological_sort(self, node_names: List[str]) -> ExecutionPlan:
        if not self.nodes:
            return []

        in_degree: Dict[str, int] = {n: 0 for n in node_names}
        adjacency: Dict[str, List[str]] = {n: [] for n in node_names}

        for name in node_names:
            node = self.nodes.get(name)
            if node and node.dependencies:
                for dep in node.dependencies:
                    if dep in in_degree:
                        in_degree[name] += 1
                        adjacency[dep].append(name)

        plan: ExecutionPlan = []
        queue = [n for n in node_names if in_degree[n] == 0]

        while queue:
            step_nodes = list(queue)
            queue = []
            step = ExecutionStep(
                nodes=step_nodes,
                executed=[False] * len(step_nodes),
                skipped=[False] * len(step_nodes),
            )
            plan.append(step)
            for node_name in step_nodes:
                for dependent in adjacency.get(node_name, []):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        return plan

    def slice_before_node(
        self, execution_plan: List[dict], node: str
    ) -> List[dict]:
        result = []
        for step in execution_plan:
            nodes = step.nodes if isinstance(step, ExecutionStep) else step.get("nodes", [])
            if node in nodes:
                break
            result.append(step)
        return result

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
            return result.get("status") != "failure"
        return True

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if not self.nodes or node_name not in self.nodes:
            return {"status": "failure", "error": f"Node {node_name} not found"}

        node = self.nodes[node_name]
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()

        node_config = node.node_config
        max_retries = 0
        retry_on_failure = False
        if node_config:
            max_retries = node_config.max_retries
            retry_on_failure = node_config.retry_on_failure

        attempts = 0
        result = {}
        while True:
            try:
                result = await node.run(self.cache, self._semaphore)
                if self.node_results is None:
                    self.node_results = {}
                self.node_results[node_name] = result
                if self.is_success(result):
                    break
                if not retry_on_failure or attempts >= max_retries:
                    break
                attempts += 1
            except NonRetryableException as e:
                result = {"status": "failure", "error": str(e)}
                if self.node_results is None:
                    self.node_results = {}
                self.node_results[node_name] = result
                break
            except Exception as e:
                result = {"status": "failure", "error": str(e)}
                if self.node_results is None:
                    self.node_results = {}
                self.node_results[node_name] = result
                if not retry_on_failure or attempts >= max_retries:
                    break
                attempts += 1

        return result

    async def run_task(self, task: Task) -> None:
        task.update_status(TaskStatus.RUNNING)
        if self.cache is None:
            self.cache = Cache()
        self.cache.set("task", task)

        if self._semaphore is None:
            self.set_semaphore()

        execution_plan = self.compile_execution_plan()
        if self.execution_state is None:
            self.execution_state = ExecutionState(
                current_plan=execution_plan,
                execution_history=[],
                execution_index=0,
                total_iterations=0,
            )
        else:
            self.execution_state.current_plan = execution_plan

        total_iterations = 0
        step_index = 0

        while step_index < len(self.execution_state.current_plan):
            if (
                self.max_total_iterations
                and total_iterations >= self.max_total_iterations
            ):
                task.set_error("Max total iterations reached")
                return

            step = self.execution_state.current_plan[step_index]
            next_node_override = None

            for node_index, node_name in enumerate(step.nodes):
                if step.skipped[node_index] or step.executed[node_index]:
                    continue

                node = self.nodes.get(node_name) if self.nodes else None
                if node is None:
                    step.skipped[node_index] = True
                    continue

                if self.auto_snapshot:
                    await self.snapshot(task, f"before_{node_name}")

                result = await self.run_node(node_name)
                self.execution_state.mark_executed(step_index, node_index)
                total_iterations += 1
                self.execution_state.total_iterations = total_iterations

                if not self.is_success(result):
                    if node.node_config and node.node_config.retry_on_failure:
                        retry_from = node.node_config.retry_from
                        if retry_from:
                            new_plan = self.compile_execution_plan_from(retry_from)
                            self.execution_state.current_plan = new_plan
                            step_index = 0
                            break
                    self.mark_node_and_deps_as_skipped(node_name)
                    error_msg = result.get("error", "unknown error") if isinstance(result, dict) else str(result)
                    self.cache.set(self.error_mailbox, error_msg)
                else:
                    if isinstance(result, dict) and "next_node" in result:
                        next_node_override = result["next_node"]

                if self.auto_snapshot:
                    await self.snapshot(task, f"after_{node_name}")

            if next_node_override and self.nodes and next_node_override in self.nodes:
                new_plan = self.compile_execution_plan_from(next_node_override)
                self.execution_state.current_plan = new_plan
                step_index = 0
                continue

            step_index += 1

        output = self.cache.get(self.output_mailbox)
        if output is not None:
            task.set_result(output)
        else:
            task.update_status(TaskStatus.COMPLETE)

    async def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        snapshot_dir = pathlib.Path(f"/tmp/snapshots/{task.id}/{name_hint}")
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        state_file = snapshot_dir / "state.json"
        state = {
            "task_id": str(task.id),
            "task_status": task.status.value,
            "name_hint": name_hint,
            "node_results": self.node_results or {},
            "cache": self.cache.to_dict() if self.cache else {},
        }
        with open(state_file, "w") as f:
            json.dump(state, f, default=str)

        return snapshot_dir

    async def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        state_file = snapshot_dir / "state.json"
        if not state_file.exists():
            raise FileNotFoundError(f"Snapshot state file not found: {state_file}")

        with open(state_file) as f:
            state = json.load(f)

        if self.cache is None:
            self.cache = Cache()
        self.cache.update(state.get("cache", {}))
        self.node_results = state.get("node_results", {})

        task_id = state.get("task_id")
        objective = state.get("objective", "restored task")
        task = Task(
            id=uuid.UUID(task_id) if task_id else uuid.uuid4(),
            objective=objective,
        )
        await self.run_task(task)