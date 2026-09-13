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
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    status: TaskStatus = TaskStatus.CREATED

    def set_error(self, error: str) -> None:
        self.error = error
        self.status = TaskStatus.FAILED

    def set_result(self, result: Any) -> None:
        self.result = result
        self.status = TaskStatus.COMPLETE

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


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


# ─────────────────────────────────────────────
# Cache – minimal implementation
# ─────────────────────────────────────────────

class Cache:
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._mailboxes: Dict[str, List[Any]] = {}

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def keys(self) -> set:
        return set(self._data.keys())

    def has(self, key: str) -> bool:
        return key in self._data

    async def set_mailbox(self, mailbox: str, value: Any) -> None:
        if mailbox not in self._mailboxes:
            self._mailboxes[mailbox] = []
        self._mailboxes[mailbox].append(value)

    async def get_mailbox(self, mailbox: str) -> List[Any]:
        return self._mailboxes.get(mailbox, [])

    async def clear_mailbox(self, mailbox: str) -> None:
        self._mailboxes[mailbox] = []

    def copy(self) -> "Cache":
        new_cache = Cache()
        new_cache._data = dict(self._data)
        new_cache._mailboxes = {k: list(v) for k, v in self._mailboxes.items()}
        return new_cache


# ─────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────

class Middleware(AsimovBase):
    async def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        return data


# ─────────────────────────────────────────────
# ModuleConfig
# ─────────────────────────────────────────────

class ModuleConfig(AsimovBase):
    context: Optional[Dict[str, Any]] = None
    middlewares: Optional[List[Middleware]] = None
    stop_on_success: bool = False
    timeout: float = 300.0


# ─────────────────────────────────────────────
# AgentModule
# ─────────────────────────────────────────────

class AgentModule(AsimovBase):
    name: str = ""
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
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> "Awaitable[dict[str, Any]] | AsyncGenerator":
        raise NotImplementedError

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        timeout = 300.0
        if self.config and self.config.timeout:
            timeout = self.config.timeout

        try:
            result = await asyncio.wait_for(
                self.process(cache, semaphore), timeout=timeout
            )
        except asyncio.TimeoutError:
            result = {"status": "error", "error": "timeout"}

        if self.executions is None:
            self.executions = 0
        self.executions += 1

        if self.config and self.config.middlewares:
            result = await self._apply_middlewares(
                self.config.middlewares, result, cache
            )

        return result

    async def _apply_middlewares(
        self,
        middlewares: List[Middleware],
        data: Dict[str, Any],
        cache: Cache,
    ) -> Dict[str, Any]:
        for mw in middlewares:
            data = await mw.process(data, cache)
        return data


# ─────────────────────────────────────────────
# CompositeModule
# ─────────────────────────────────────────────

class CompositeModule(AgentModule):
    modules: List[AgentModule] = Field(default_factory=list)
    node_config: Optional["NodeConfig"] = None

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
            if isinstance(r, Exception):
                combined["status"] = "error"
                combined["error"] = str(r)
            elif isinstance(r, dict):
                combined.update(r)
        return combined

    async def run_sequential_modules(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for module in self.modules:
            result = await module.run(cache, semaphore)
            if self.config and self.config.stop_on_success:
                if module.is_success(result):
                    break
        return result

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        parallel = False
        if self.node_config:
            parallel = self.node_config.parallel

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


# ─────────────────────────────────────────────
# NodeConfig
# ─────────────────────────────────────────────

class NodeConfig(AsimovBase):
    parallel: bool = False
    max_retries: int = 0
    retry_on_failure: bool = False
    retry_from: Optional[str] = None
    condition: Optional[str] = None
    inputs: Optional[List[str]] = None
    outputs: Optional[List[str]] = None
    max_visits: Optional[int] = None


# ─────────────────────────────────────────────
# Node
# ─────────────────────────────────────────────

class Node(CompositeModule):
    dependencies: Optional[List[str]] = None
    node_config: Optional[NodeConfig] = None
    snapshot: Optional[SnapshotControl] = None
    type: Optional[ModuleType] = ModuleType.NODE
    _nodes: Optional[Dict[str, "Node"]] = None

    def get_nodes(self) -> Optional[Dict[str, "Node"]]:
        return self._nodes

    def set_nodes(self, nodes: Dict[str, "Node"]) -> None:
        self._nodes = nodes

    def cleanup(self) -> None:
        pass

    async def cancel_gen(self, agen: AsyncGenerator) -> None:
        await agen.aclose()


# ─────────────────────────────────────────────
# FlowDecision / FlowControlConfig
# ─────────────────────────────────────────────

class FlowDecision(AsimovBase):
    next_node: str
    condition: Optional[str] = None
    condition_variables: Optional[List[str]] = None
    cleanup_on_jump: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None


class FlowControlConfig(AsimovBase):
    decisions: Sequence[FlowDecision] = Field(default_factory=list)
    default: Optional[str] = None
    cleanup_on_default: bool = False


# ─────────────────────────────────────────────
# FlowControlModule
# ─────────────────────────────────────────────

class FlowControlModule(AgentModule):
    flow_config: Optional[FlowControlConfig] = None

    def evaluate_condition(
        self, condition: str, cache: Cache, cache_keys: set
    ) -> bool:
        try:
            context = {k: cache.get(k) for k in cache_keys}
            return bool(eval(condition, {}, context))
        except Exception:
            return False

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if not self.flow_config:
            return {"status": "error", "error": "no flow_config"}

        cache_keys = cache.keys()

        for decision in self.flow_config.decisions:
            if decision.condition is None:
                return {"status": "success", "next_node": decision.next_node}

            keys = set(decision.condition_variables or []) | cache_keys
            if self.evaluate_condition(decision.condition, cache, keys):
                if decision.cleanup_on_jump:
                    pass  # cleanup logic placeholder
                return {"status": "success", "next_node": decision.next_node}

        if self.flow_config.default:
            if self.flow_config.cleanup_on_default:
                pass  # cleanup logic placeholder
            return {"status": "success", "next_node": self.flow_config.default}

        return {"status": "error", "error": "no matching decision"}

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


# ─────────────────────────────────────────────
# ExecutionStep / ExecutionPlan / ExecutionState
# ─────────────────────────────────────────────

ExecutionPlan = List[Dict[str, Any]]


class ExecutionStep(AsimovBase):
    nodes: List[str] = Field(default_factory=list)
    executed: List[bool] = Field(default_factory=list)
    skipped: List[bool] = Field(default_factory=list)


class ExecutionState(AsimovBase):
    current_plan: Optional[ExecutionPlan] = None
    execution_history: Optional[List[ExecutionPlan]] = None
    execution_index: Optional[int] = 0
    total_iterations: Optional[int] = 0

    def mark_executed(self, step_index: int, node_index: int) -> None:
        if self.current_plan is None:
            return
        step = self.current_plan[step_index]
        if "executed" in step and node_index < len(step["executed"]):
            step["executed"][node_index] = True

    def was_executed(self, node_name: str) -> bool:
        if self.current_plan is None:
            return False
        for step in self.current_plan:
            nodes = step.get("nodes", [])
            executed = step.get("executed", [])
            for i, n in enumerate(nodes):
                if n == node_name and i < len(executed) and executed[i]:
                    return True
        if self.execution_history:
            for plan in self.execution_history:
                for step in plan:
                    nodes = step.get("nodes", [])
                    executed = step.get("executed", [])
                    for i, n in enumerate(nodes):
                        if n == node_name and i < len(executed) and executed[i]:
                            return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if self.current_plan is None:
            return False
        for step in self.current_plan:
            nodes = step.get("nodes", [])
            skipped = step.get("skipped", [])
            for i, n in enumerate(nodes):
                if n == node_name and i < len(skipped) and skipped[i]:
                    return True
        return False


# ─────────────────────────────────────────────
# Agent
# ─────────────────────────────────────────────

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

    def model_post_init(self, __context: Any) -> None:
        if self.nodes is None:
            self.nodes = {}
        if self.graph is None:
            self.graph = {}
        if self.node_results is None:
            self.node_results = {}
        if self.execution_state is None:
            self.execution_state = ExecutionState(
                current_plan=[],
                execution_history=[],
                execution_index=0,
                total_iterations=0,
            )
        if self.cache is None:
            self.cache = Cache()

    def add_node(self, node: Node) -> None:
        if self.nodes is None:
            self.nodes = {}
        if self.graph is None:
            self.graph = {}
        self.nodes[node.name] = node
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

        in_degree: Dict[str, int] = {n: 0 for n in self.nodes}
        for node_name, dependents in self.graph.items():
            for dep in dependents:
                if dep in in_degree:
                    in_degree[dep] += 1

        plan: ExecutionPlan = []
        visited: set = set()
        queue = [n for n, d in in_degree.items() if d == 0 and n in self.nodes]

        while queue:
            step_nodes = list(queue)
            step = {
                "nodes": step_nodes,
                "executed": [False] * len(step_nodes),
                "skipped": [False] * len(step_nodes),
            }
            plan.append(step)
            queue = []
            for node_name in step_nodes:
                visited.add(node_name)
                for dependent in self.graph.get(node_name, []):
                    if dependent in self.nodes:
                        in_degree[dependent] -= 1
                        if in_degree[dependent] == 0 and dependent not in visited:
                            queue.append(dependent)

        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        full_plan = self.compile_execution_plan()
        return self.slice_before_node(full_plan, start_node)

    def slice_before_node(
        self, execution_plan: List[dict], node: str
    ) -> List[dict]:
        result = []
        found = False
        for step in execution_plan:
            if node in step.get("nodes", []):
                found = True
            if found:
                result.append(step)
        return result

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        if not self.graph:
            return ()
        visited: set = set()
        stack = [node_name]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for dep in self.graph.get(current, []):
                stack.append(dep)
        visited.discard(node_name)
        return tuple(visited)

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if not self.execution_state or not self.execution_state.current_plan:
            return
        to_skip = {node_name} | set(self.get_dependent_chains(node_name))
        for step in self.execution_state.current_plan:
            for i, n in enumerate(step.get("nodes", [])):
                if n in to_skip:
                    step["skipped"][i] = True

    def is_success(self, result: Any) -> bool:
        if result is None:
            return False
        if isinstance(result, dict):
            return result.get("status") != "error"
        return True

    def set_semaphore(self) -> asyncio.Semaphore:
        limit = self.max_concurrent_tasks or 10
        return asyncio.Semaphore(limit)

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if not self.nodes or node_name not in self.nodes:
            return {"status": "error", "error": f"node {node_name} not found"}

        node = self.nodes[node_name]
        semaphore = self.set_semaphore()
        cache = self.cache or Cache()

        node_cfg = node.node_config
        max_retries = node_cfg.max_retries if node_cfg else 0
        retry_on_failure = node_cfg.retry_on_failure if node_cfg else False

        attempts = 0
        result: Dict[str, Any] = {}

        while True:
            try:
                result = await node.run(cache, semaphore)
            except NonRetryableException as e:
                result = {"status": "error", "error": str(e)}
                break
            except Exception as e:
                result = {"status": "error", "error": str(e)}

            if self.is_success(result):
                break

            if retry_on_failure and attempts < max_retries:
                attempts += 1
                continue
            else:
                break

        if self.node_results is None:
            self.node_results = {}
        self.node_results[node_name] = result
        return result

    async def run_task(self, task: Task) -> None:
        task.update_status(TaskStatus.RUNNING)
        cache = self.cache or Cache()
        cache.set("task", task)
        cache.set("objective", task.objective)
        if task.params:
            for k, v in task.params.items():
                cache.set(k, v)

        plan = self.compile_execution_plan()
        if self.execution_state is None:
            self.execution_state = ExecutionState(
                current_plan=plan,
                execution_history=[],
                execution_index=0,
                total_iterations=0,
            )
        else:
            self.execution_state.current_plan = plan

        semaphore = self.set_semaphore()
        max_iters = self.max_total_iterations or 100
        iteration = 0

        step_index = 0
        while step_index < len(self.execution_state.current_plan):
            if iteration >= max_iters:
                task.set_error("max_total_iterations exceeded")
                return

            step = self.execution_state.current_plan[step_index]
            nodes_in_step = step.get("nodes", [])
            skipped = step.get("skipped", [])
            executed = step.get("executed", [])

            parallel_tasks = []
            node_indices = []
            for i, node_name in enumerate(nodes_in_step):
                if skipped[i] or executed[i]:
                    continue
                if not self.nodes or node_name not in self.nodes:
                    continue
                node = self.nodes[node_name]
                node_cfg = node.node_config
                if node_cfg and node_cfg.condition:
                    try:
                        ctx = {k: cache.get(k) for k in cache.keys()}
                        if not eval(node_cfg.condition, {}, ctx):
                            self.mark_node_and_deps_as_skipped(node_name)
                            step["skipped"][i] = True
                            continue
                    except Exception:
                        pass

                parallel_tasks.append(node.run(cache, semaphore))
                node_indices.append(i)

            if parallel_tasks:
                results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
                next_node_override = None
                for idx, (ni, res) in enumerate(zip(node_indices, results)):
                    node_name = nodes_in_step[ni]
                    if isinstance(res, Exception):
                        res = {"status": "error", "error": str(res)}

                    if self.node_results is None:
                        self.node_results = {}
                    self.node_results[node_name] = res
                    step["executed"][ni] = True
                    self.execution_state.mark_executed(step_index, ni)

                    if isinstance(res, dict) and "next_node" in res:
                        next_node_override = res["next_node"]

                    if not self.is_success(res):
                        node = self.nodes.get(node_name)
                        node_cfg = node.node_config if node else None
                        if node_cfg and node_cfg.retry_on_failure:
                            retry_from = node_cfg.retry_from or node_name
                            new_plan = self.compile_execution_plan_from(retry_from)
                            if self.execution_state.execution_history is None:
                                self.execution_state.execution_history = []
                            self.execution_state.execution_history.append(
                                self.execution_state.current_plan
                            )
                            self.execution_state.current_plan = new_plan
                            step_index = 0
                            iteration += 1
                            break
                        else:
                            self.mark_node_and_deps_as_skipped(node_name)
                    else:
                        if next_node_override and self.nodes:
                            if next_node_override in self.nodes:
                                new_plan = self.compile_execution_plan_from(
                                    next_node_override
                                )
                                if self.execution_state.execution_history is None:
                                    self.execution_state.execution_history = []
                                self.execution_state.execution_history.append(
                                    self.execution_state.current_plan
                                )
                                self.execution_state.current_plan = new_plan
                                step_index = 0
                                iteration += 1
                                break
                else:
                    step_index += 1
                    iteration += 1
                    if self.execution_state.total_iterations is None:
                        self.execution_state.total_iterations = 0
                    self.execution_state.total_iterations += 1
            else:
                step_index += 1

        output = cache.get(self.output_mailbox)
        if output is not None:
            task.set_result(output)
        else:
            task.set_result(self.node_results)

        if task.status != TaskStatus.FAILED:
            task.update_status(TaskStatus.COMPLETE)

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        import tempfile
        snap_dir = pathlib.Path(tempfile.mkdtemp()) / name_hint
        snap_dir.mkdir(parents=True, exist_ok=True)

        state = {
            "task": {
                "id": str(task.id),
                "objective": task.objective,
                "type": task.type,
                "params": task.params,
                "status": task.status.value,
            },
            "node_results": self.node_results or {},
            "execution_state": {
                "current_plan": self.execution_state.current_plan
                if self.execution_state
                else [],
                "execution_index": self.execution_state.execution_index
                if self.execution_state
                else 0,
                "total_iterations": self.execution_state.total_iterations
                if self.execution_state
                else 0,
            },
            "cache": self.cache._data if self.cache else {},
        }

        with open(snap_dir / "state.json", "w") as f:
            json.dump(state, f, default=str)

        return snap_dir

    async def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        state_file = snapshot_dir / "state.json"
        if not state_file.exists():
            raise FileNotFoundError(f"Snapshot not found: {state_file}")

        with open(state_file) as f:
            state = json.load(f)

        task_data = state.get("task", {})
        task = Task(
            id=uuid.UUID(task_data["id"]) if task_data.get("id") else None,
            objective=task_data.get("objective", ""),
            type=task_data.get("type", "task"),
            params=task_data.get("params"),
            status=TaskStatus(task_data.get("status", "created")),
        )

        if self.cache is None:
            self.cache = Cache()
        for k, v in state.get("cache", {}).items():
            self.cache.set(k, v)

        self.node_results = state.get("node_results", {})

        exec_state_data = state.get("execution_state", {})
        self.execution_state = ExecutionState(
            current_plan=exec_state_data.get("current_plan", []),
            execution_history=[],
            execution_index=exec_state_data.get("execution_index", 0),
            total_iterations=exec_state_data.get("total_iterations", 0),
        )

        await self.run_task(task)


# ─────────────────────────────────────────────
# Executor
# ─────────────────────────────────────────────

class Executor(AgentModule):
    type: Optional[ModuleType] = ModuleType.EXECUTOR

    @abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        raise NotImplementedError


# ─────────────────────────────────────────────
# agent_directed_flow.py
# ─────────────────────────────────────────────

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
        if not self.inference_client:
            return ""

        prompt = str(generation_input)
        system = self.system_description

        if self.flow_config and self.flow_config.decisions:
            choices_text = "\n".join(
                f"- {d.next_node}: {d.condition or 'no condition'}"
                for d in self.flow_config.decisions
            )
            prompt = f"{prompt}\n\nChoices:\n{choices_text}"

        response = await self.inference_client.generate(prompt, system=system)
        return response

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if not self.flow_config:
            return {"status": "error", "error": "no flow_config"}

        input_data = None
        if self.input_var:
            input_data = cache.get(self.input_var)

        votes: List[str] = []
        for _ in range(self.voters):
            response = await self.gen(input_data, cache)
            votes.append(response)

        chosen = self.most_common_string(votes)

        for decision in self.flow_config.decisions:
            if decision.next_node == chosen or chosen in decision.next_node:
                return {"status": "success", "next_node": decision.next_node}

        if self.flow_config.default:
            return {"status": "success", "next_node": self.flow_config.default}

        return {"status": "error", "error": "no matching decision"}

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


# ─────────────────────────────────────────────
# Rebuild forward references
# ─────────────────────────────────────────────

Agent.model_rebuild()
Node.model_rebuild()
CompositeModule.model_rebuild()
AgentModule.model_rebuild()
FlowControlModule.model_rebuild()
AgentDirectedFlowControl.model_rebuild()