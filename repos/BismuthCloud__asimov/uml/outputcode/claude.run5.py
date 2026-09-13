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
# asimov/graph/tasks.py
# ---------------------------------------------------------------------------

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


class Task(AsimovBase):
    model_config = {"arbitrary_types_allowed": True}

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4)
    objective: str
    type: str = "task"
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING

    def update_status(self, status: TaskStatus) -> None:
        self.status = status

    def set_result(self, result: Any) -> None:
        self.result = result

    def set_error(self, error: str) -> None:
        self.error = error


# ---------------------------------------------------------------------------
# asimov/graph/__init__.py  (core graph types)
# ---------------------------------------------------------------------------

class ModuleType(Enum):
    EXECUTOR = "executor"
    FLOW_CONTROL = "flow_control"
    COMPOSITE = "composite"
    SUBAGENT = "subagent"


class SnapshotControl(Enum):
    BEFORE = "before"
    AFTER = "after"
    BOTH = "both"
    NONE = "none"


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

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def keys(self) -> set:
        return set(self._data.keys())

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def update(self, data: Dict[str, Any]) -> None:
        self._data.update(data)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)


class Middleware(AsimovBase):
    def process(self, data: Dict[str, Any], cache: "Cache") -> Dict[str, Any]:
        return data


class ModuleConfig(AsimovBase):
    context: Optional[Dict[str, Any]] = None
    middlewares: Optional[List[Middleware]] = None
    stop_on_success: bool = False
    timeout: float = 300.0


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
        return result.get("status") != "error"

    @abstractmethod
    async def process(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> "Awaitable[dict[str, Any]] | AsyncGenerator":
        raise NotImplementedError

    async def run(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        timeout = 300.0
        if self.config and self.config.timeout:
            timeout = self.config.timeout

        try:
            result = await asyncio.wait_for(
                self._execute(cache, semaphore), timeout=timeout
            )
        except asyncio.TimeoutError:
            result = {"status": "error", "error": "timeout"}
        except NonRetryableException:
            raise
        except Exception as e:
            result = {"status": "error", "error": str(e)}

        if self.executions is None:
            self.executions = 0
        self.executions += 1
        return result

    async def _execute(
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
            return result


class FlowDecision(AsimovBase):
    next_node: str
    condition: Optional[str] = None
    condition_variables: Optional[List[str]] = None
    cleanup_on_jump: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None


class FlowControlConfig(AsimovBase):
    decisions: Sequence[FlowDecision] = []
    default: Optional[str] = None
    cleanup_on_default: bool = False


class FlowControlModule(AgentModule):
    flow_config: Optional[FlowControlConfig] = None

    def evaluate_condition(
        self, condition: str, cache: "Cache", cache_keys: set
    ) -> bool:
        try:
            context = {key: cache.get(key) for key in cache_keys}
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception:
            return False

    async def run(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.flow_config is None:
            return {"status": "success", "next_node": None}

        cache_keys = cache.keys()

        for decision in self.flow_config.decisions:
            if decision.condition is None:
                if decision.cleanup_on_jump and decision.condition_variables:
                    for var in decision.condition_variables:
                        cache.delete(var)
                return {"status": "success", "next_node": decision.next_node}

            if self.evaluate_condition(decision.condition, cache, cache_keys):
                if decision.cleanup_on_jump and decision.condition_variables:
                    for var in decision.condition_variables:
                        cache.delete(var)
                return {"status": "success", "next_node": decision.next_node}

        if self.flow_config.default:
            if self.flow_config.cleanup_on_default:
                for decision in self.flow_config.decisions:
                    if decision.condition_variables:
                        for var in decision.condition_variables:
                            cache.delete(var)
            return {"status": "success", "next_node": self.flow_config.default}

        return {"status": "success", "next_node": None}

    async def process(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        return await self.run(cache, semaphore)


class NodeConfig(AsimovBase):
    parallel: bool = False
    max_retries: int = 3
    retry_on_failure: bool = False
    retry_from: Optional[str] = None
    condition: Optional[str] = None
    inputs: Optional[List[str]] = None
    outputs: Optional[List[str]] = None
    max_visits: Optional[int] = None


class CompositeModule(AgentModule):
    modules: List[AgentModule] = Field(default_factory=list)
    node_config: Optional[NodeConfig] = None

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
            self.run_module_with_concurrency_control(module, cache, semaphore)
            for module in self.modules
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        combined: Dict[str, Any] = {}
        for result in results:
            if isinstance(result, Exception):
                combined["status"] = "error"
                combined["error"] = str(result)
            elif isinstance(result, dict):
                combined.update(result)
        return combined

    async def run_sequential_modules(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        combined: Dict[str, Any] = {}
        for module in self.modules:
            result = await module.run(cache, semaphore)
            if isinstance(result, dict):
                combined.update(result)
                if self.node_config and hasattr(module, "config"):
                    config = module.config
                    if config and config.stop_on_success and module.is_success(result):
                        break
        return combined

    async def run(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            result = await self.run_parallel_modules(cache, semaphore)
        else:
            result = await self.run_sequential_modules(cache, semaphore)

        middlewares: List[Middleware] = []
        for module in self.modules:
            if module.config and module.config.middlewares:
                middlewares.extend(module.config.middlewares)

        if middlewares:
            result = await self.apply_middlewares(middlewares, result, cache)

        return result

    async def process(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        return await self.run(cache, semaphore)


class ExecutionStep(AsimovBase):
    nodes: List[str] = Field(default_factory=list)
    executed: List[bool] = Field(default_factory=list)
    skipped: List[bool] = Field(default_factory=list)


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
            for i, node in enumerate(step.nodes):
                if node == node_name and i < len(step.executed) and step.executed[i]:
                    return True
        if self.execution_history:
            for plan in self.execution_history:
                for step in plan:
                    for i, node in enumerate(step.nodes):
                        if (
                            node == node_name
                            and i < len(step.executed)
                            and step.executed[i]
                        ):
                            return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan:
            for i, node in enumerate(step.nodes):
                if node == node_name and i < len(step.skipped) and step.skipped[i]:
                    return True
        return False


class Node(CompositeModule):
    dependencies: Optional[List[str]] = None
    modules: List[AgentModule] = Field(default_factory=list)
    node_config: Optional[NodeConfig] = None
    snapshot: Optional[SnapshotControl] = None
    type: Optional[ModuleType] = None
    _nodes_ref: Optional[Dict[str, "Node"]] = None

    def get_nodes(self) -> Optional[Dict[str, "Node"]]:
        return self._nodes_ref

    def set_nodes(self, nodes: Dict[str, "Node"]) -> None:
        self._nodes_ref = nodes

    def cleanup(self) -> None:
        pass

    async def cancel_gen(self, agen: AsyncGenerator) -> None:
        await agen.aclose()


# ---------------------------------------------------------------------------
# asimov/executors/executor.py
# ---------------------------------------------------------------------------

class Executor(AgentModule):
    type: Optional[ModuleType] = ModuleType.EXECUTOR

    @abstractmethod
    async def process(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# asimov/graph/agent_directed_flow.py
# ---------------------------------------------------------------------------

class InferenceClient:
    """Placeholder inference client."""

    async def generate(self, prompt: str, system: str = "") -> str:
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
    flow_config: Optional[AgentDrivenFlowControlConfig] = None
    inference_client: Optional[InferenceClient] = None
    system_description: str = ""
    input_var: Optional[str] = None
    use_historicals: Optional[bool] = True
    voters: int = 1

    model_config = {"arbitrary_types_allowed": True}

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
        return await self.inference_client.generate(prompt, self.system_description)

    async def run(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.flow_config is None:
            return {"status": "success", "next_node": None}

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
                return {"status": "success", "next_node": decision.next_node}

        if self.flow_config.default:
            return {"status": "success", "next_node": self.flow_config.default}

        return {"status": "success", "next_node": None}

    async def process(
        self, cache: "Cache", semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        return await self.run(cache, semaphore)


# ---------------------------------------------------------------------------
# asimov/graph/agent.py  (Agent)
# ---------------------------------------------------------------------------

class Agent(AsimovBase):
    nodes: Optional[Dict[str, Node]] = None
    graph: Optional[Dict[str, List[str]]] = None
    node_results: Optional[Dict[str, Any]] = None
    execution_state: Optional[ExecutionState] = None
    cache: Optional[Cache] = None
    output_mailbox: str = "output"
    error_mailbox: str = "error"
    max_concurrent_tasks: Optional[int] = 10
    max_total_iterations: Optional[int] = 100
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
        visited = set()
        result = []

        def dfs(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            result.append(name)
            for child in self.graph.get(name, []):
                dfs(child)

        for child in self.graph.get(node_name, []):
            dfs(child)

        return tuple(result)

    def compile_execution_plan(self) -> ExecutionPlan:
        if self.nodes is None or self.graph is None:
            return []

        in_degree: Dict[str, int] = {name: 0 for name in self.nodes}
        for parent, children in self.graph.items():
            for child in children:
                if child in in_degree:
                    in_degree[child] += 1

        plan: ExecutionPlan = []
        remaining = set(self.nodes.keys())

        while remaining:
            ready = [n for n in remaining if in_degree.get(n, 0) == 0]
            if not ready:
                break
            step = ExecutionStep(
                nodes=ready,
                executed=[False] * len(ready),
                skipped=[False] * len(ready),
            )
            plan.append(step)
            for node_name in ready:
                remaining.remove(node_name)
                for child in self.graph.get(node_name, []):
                    in_degree[child] = in_degree.get(child, 1) - 1

        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        full_plan = self.compile_execution_plan()
        return self.slice_before_node(
            [step.model_dump() for step in full_plan], start_node
        )

    def slice_before_node(
        self, execution_plan: List[dict], node: str
    ) -> List[dict]:
        result = []
        for step_dict in execution_plan:
            step = ExecutionStep(**step_dict)
            if node in step.nodes:
                idx = step.nodes.index(node)
                new_step = ExecutionStep(
                    nodes=step.nodes[idx:],
                    executed=step.executed[idx:],
                    skipped=step.skipped[idx:],
                )
                result.append(new_step)
                break
            result.append(step)
        return result

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if self.execution_state is None or self.execution_state.current_plan is None:
            return
        deps = self.get_dependent_chains(node_name)
        to_skip = {node_name} | set(deps)
        for step in self.execution_state.current_plan:
            for i, n in enumerate(step.nodes):
                if n in to_skip and i < len(step.skipped):
                    step.skipped[i] = True

    def is_success(self, result: Any) -> bool:
        if result is None:
            return False
        if isinstance(result, dict):
            return result.get("status") != "error"
        return True

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if self.nodes is None or node_name not in self.nodes:
            return {"status": "error", "error": f"Node {node_name} not found"}

        node = self.nodes[node_name]
        node.set_nodes(self.nodes)

        if self.cache is None:
            self.cache = Cache()

        if self._semaphore is None:
            self.set_semaphore()

        node_config = node.node_config or NodeConfig()
        max_retries = node_config.max_retries
        retry_on_failure = node_config.retry_on_failure

        result: Dict[str, Any] = {}
        attempts = 0

        while True:
            try:
                result = await node.run(self.cache, self._semaphore)
                if self.node_results is None:
                    self.node_results = {}
                self.node_results[node_name] = result

                if self.is_success(result):
                    break
                elif retry_on_failure and attempts < max_retries:
                    attempts += 1
                    continue
                else:
                    break
            except NonRetryableException:
                result = {"status": "error", "error": "non_retryable"}
                break
            except Exception as e:
                if retry_on_failure and attempts < max_retries:
                    attempts += 1
                    continue
                result = {"status": "error", "error": str(e)}
                break

        return result

    async def run_task(self, task: Task) -> None:
        task.update_status(TaskStatus.RUNNING)

        if self.cache is None:
            self.cache = Cache()

        self.cache.set("task", task)
        self.cache.set("objective", task.objective)
        if task.params:
            self.cache.update(task.params)

        if self._semaphore is None:
            self.set_semaphore()

        plan = self.compile_execution_plan()
        self.execution_state = ExecutionState(
            current_plan=plan,
            execution_history=[],
            execution_index=0,
            total_iterations=0,
        )

        max_iterations = self.max_total_iterations or 100
        iteration = 0

        try:
            while iteration < max_iterations:
                iteration += 1
                if self.execution_state.total_iterations is None:
                    self.execution_state.total_iterations = 0
                self.execution_state.total_iterations += 1

                if not self.execution_state.current_plan:
                    break

                all_done = True
                for step_idx, step in enumerate(self.execution_state.current_plan):
                    for node_idx, node_name in enumerate(step.nodes):
                        if step_idx < len(self.execution_state.current_plan):
                            executed = (
                                node_idx < len(step.executed)
                                and step.executed[node_idx]
                            )
                            skipped = (
                                node_idx < len(step.skipped)
                                and step.skipped[node_idx]
                            )
                            if not executed and not skipped:
                                all_done = False
                                result = await self.run_node(node_name)
                                self.execution_state.mark_executed(
                                    step_idx, node_idx
                                )

                                if self.auto_snapshot:
                                    await self.snapshot(task, node_name)

                                if isinstance(result, dict) and "next_node" in result:
                                    next_node = result.get("next_node")
                                    if next_node:
                                        new_plan = self.compile_execution_plan_from(
                                            next_node
                                        )
                                        if self.execution_state.execution_history is None:
                                            self.execution_state.execution_history = []
                                        self.execution_state.execution_history.append(
                                            self.execution_state.current_plan
                                        )
                                        self.execution_state.current_plan = new_plan
                                        all_done = False
                                        break

                                if not self.is_success(result):
                                    node = self.nodes.get(node_name) if self.nodes else None
                                    node_config = (
                                        node.node_config if node else None
                                    ) or NodeConfig()
                                    if not node_config.retry_on_failure:
                                        self.mark_node_and_deps_as_skipped(node_name)
                    else:
                        continue
                    break

                if all_done:
                    break

            output = self.cache.get(self.output_mailbox)
            error = self.cache.get(self.error_mailbox)

            if error:
                task.set_error(str(error))
                task.update_status(TaskStatus.FAILED)
            else:
                task.set_result(output)
                task.update_status(TaskStatus.COMPLETE)

        except Exception as e:
            task.set_error(str(e))
            task.update_status(TaskStatus.FAILED)

    async def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        snapshot_dir = pathlib.Path(f"/tmp/asimov_snapshots/{task.id}/{name_hint}")
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        state_data = {
            "task_id": str(task.id),
            "name_hint": name_hint,
            "node_results": self.node_results or {},
            "cache": self.cache.to_dict() if self.cache else {},
            "execution_state": (
                self.execution_state.model_dump()
                if self.execution_state
                else None
            ),
        }

        state_file = snapshot_dir / "state.json"
        with open(state_file, "w") as f:
            json.dump(state_data, f, default=str)

        return snapshot_dir

    async def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        state_file = snapshot_dir / "state.json"
        if not state_file.exists():
            raise FileNotFoundError(f"Snapshot state file not found: {state_file}")

        with open(state_file, "r") as f:
            state_data = json.load(f)

        if self.cache is None:
            self.cache = Cache()

        cache_data = state_data.get("cache", {})
        self.cache.update(cache_data)

        self.node_results = state_data.get("node_results", {})

        execution_state_data = state_data.get("execution_state")
        if execution_state_data:
            self.execution_state = ExecutionState(**execution_state_data)

        task_data = self.cache.get("task")
        if task_data is None:
            task = Task(
                objective=state_data.get("objective", "restored task"),
                id=uuid.UUID(state_data["task_id"]) if state_data.get("task_id") else None,
            )
        else:
            task = task_data

        await self.run_task(task)