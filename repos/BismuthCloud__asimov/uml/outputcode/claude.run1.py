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
    MISTRAL = "mistral"


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
    SUB_AGENT = "sub_agent"


class SnapshotControl(Enum):
    BEFORE = "before"
    AFTER = "after"
    BOTH = "both"
    NEVER = "never"


class Cache:
    """Simple in-memory key/value cache used throughout the graph."""

    def __init__(self) -> None:
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

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    def update(self, data: Dict[str, Any]) -> None:
        self._data.update(data)


class NonRetryableException(Exception):
    """Raised when a node failure should not be retried."""


class Middleware(AsimovBase):
    async def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
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
    parallel: bool = False
    max_retries: int = 0
    retry_on_failure: bool = False
    retry_from: Optional[str] = None
    max_visits: Optional[int] = None


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
    container: Optional[Any] = None  # forward ref to CompositeModule
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = 0
    input_mailboxes: Optional[List[str]] = None
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = False

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
        if self.executions is None:
            self.executions = 0
        self.executions += 1

        timeout = 300.0
        if self.config and self.config.timeout:
            timeout = self.config.timeout

        result = await asyncio.wait_for(
            self._run_process(cache, semaphore), timeout=timeout
        )
        return result

    async def _run_process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
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
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            return await self.run_parallel_modules(cache, semaphore)
        return await self.run_sequential_modules(cache, semaphore)

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
                raise r
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
            if self.config and self.config.stop_on_success:
                if module.is_success(result):
                    break
        return combined

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        result = await self.process(cache, semaphore)
        if self.config and self.config.middlewares:
            result = await self.apply_middlewares(
                self.config.middlewares, result, cache
            )
        return result


class FlowControlModule(AgentModule):
    flow_config: FlowControlConfig = Field(default_factory=FlowControlConfig)

    def evaluate_condition(
        self, condition: str, cache: Cache, cache_keys: Set[str]
    ) -> bool:
        context: Dict[str, Any] = {}
        for key in cache_keys:
            context[key] = cache.get(key)
        try:
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
        cache_keys = cache.keys()
        for decision in self.flow_config.decisions:
            if decision.condition is None:
                return {"next_node": decision.next_node, "status": "success"}
            if self.evaluate_condition(decision.condition, cache, cache_keys):
                if decision.cleanup_on_jump and decision.condition_variables:
                    for var in decision.condition_variables:
                        cache.delete(var)
                return {"next_node": decision.next_node, "status": "success"}

        if self.flow_config.default:
            if self.flow_config.cleanup_on_default:
                for decision in self.flow_config.decisions:
                    if decision.condition_variables:
                        for var in decision.condition_variables:
                            cache.delete(var)
            return {"next_node": self.flow_config.default, "status": "success"}

        return {"next_node": None, "status": "no_decision"}


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
    execution_index: Optional[int] = 0
    total_iterations: Optional[int] = 0

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


class Node(CompositeModule):
    dependencies: Optional[List[str]] = None
    modules: List[AgentModule] = Field(default_factory=list)
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

    async def generate(self, prompt: str, **kwargs: Any) -> str:
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
    inference_client: InferenceClient = Field(default_factory=InferenceClient)
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
        prompt = str(generation_input)
        response = await self.inference_client.generate(prompt)
        return response

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        input_data = None
        if self.input_var:
            input_data = cache.get(self.input_var)

        votes: List[str] = []
        for _ in range(self.voters):
            response = await self.gen(input_data, cache)
            votes.append(response)

        chosen = self.most_common_string(votes)

        for decision in self.flow_config.decisions:
            if decision.next_node == chosen:
                return {"next_node": decision.next_node, "status": "success"}

        if self.flow_config.default:
            return {"next_node": self.flow_config.default, "status": "success"}

        return {"next_node": None, "status": "no_decision"}


# ─────────────────────────────────────────────
# asimov/graph/agent.py  (Agent)
# ─────────────────────────────────────────────

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

    def model_post_init(self, __context: Any) -> None:
        if self.cache is None:
            self.cache = Cache()
        if self.execution_state is None:
            self.execution_state = ExecutionState()
        if self.node_results is None:
            self.node_results = {}
        if self.nodes is None:
            self.nodes = {}
        if self.graph is None:
            self.graph = {}

    def set_semaphore(self) -> None:
        limit = self.max_concurrent_tasks or 10
        self._semaphore = asyncio.Semaphore(limit)

    def add_node(self, node: Node) -> None:
        if self.nodes is None:
            self.nodes = {}
        if self.graph is None:
            self.graph = {}
        self.nodes[node.name] = node
        if node.name not in self.graph:
            self.graph[node.name] = list(node.dependencies or [])
        node.set_nodes(self.nodes)

    def add_multiple_nodes(self, nodes: List[Node]) -> None:
        for node in nodes:
            self.add_node(node)

    def update_dependencies(self, parent_node: str, new_node: str) -> None:
        if self.graph is None:
            self.graph = {}
        if new_node not in self.graph:
            self.graph[new_node] = []
        self.graph[new_node].append(parent_node)

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        """Return all nodes that depend (directly or transitively) on node_name."""
        if self.graph is None:
            return ()
        dependents: List[str] = []
        visited: Set[str] = set()

        def _collect(name: str) -> None:
            for node, deps in self.graph.items():  # type: ignore[union-attr]
                if name in deps and node not in visited:
                    visited.add(node)
                    dependents.append(node)
                    _collect(node)

        _collect(node_name)
        return tuple(dependents)

    def _topological_sort(self) -> List[List[str]]:
        """Return nodes grouped by execution level (topological layers)."""
        if not self.nodes or not self.graph:
            return []

        in_degree: Dict[str, int] = {n: 0 for n in self.nodes}
        for node, deps in self.graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[node] = in_degree.get(node, 0)
            in_degree[node] = len([d for d in deps if d in self.nodes])

        layers: List[List[str]] = []
        remaining = set(self.nodes.keys())

        while remaining:
            layer = [n for n in remaining if in_degree[n] == 0]
            if not layer:
                # cycle or unresolved deps – add remaining as one layer
                layer = list(remaining)
            layers.append(sorted(layer))
            for n in layer:
                remaining.remove(n)
                for other in remaining:
                    if n in self.graph.get(other, []):
                        in_degree[other] -= 1

        return layers

    def compile_execution_plan(self) -> ExecutionPlan:
        layers = self._topological_sort()
        plan: ExecutionPlan = []
        for layer in layers:
            step = ExecutionStep(
                nodes=layer,
                executed=[False] * len(layer),
                skipped=[False] * len(layer),
            )
            plan.append(step)
        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        full_plan = self.compile_execution_plan()
        return self.slice_before_node(
            [s.model_dump() for s in full_plan], start_node
        )

    def slice_before_node(
        self, execution_plan: List[dict], node: str
    ) -> ExecutionPlan:
        """Return the portion of the plan starting from the step containing node."""
        steps = [ExecutionStep(**s) for s in execution_plan]
        for i, step in enumerate(steps):
            if node in step.nodes:
                return steps[i:]
        return steps

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if self.execution_state is None or self.execution_state.current_plan is None:
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
                return status == "success"
        return True

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if self.nodes is None:
            raise ValueError("No nodes registered")
        node = self.nodes.get(node_name)
        if node is None:
            raise ValueError(f"Node '{node_name}' not found")

        if self._semaphore is None:
            self.set_semaphore()

        assert self._semaphore is not None
        assert self.cache is not None

        node_config = node.node_config or NodeConfig()
        max_retries = node_config.max_retries
        retry_on_failure = node_config.retry_on_failure

        attempt = 0
        last_result: Dict[str, Any] = {}
        while True:
            try:
                result = await node.run(self.cache, self._semaphore)
                last_result = result if isinstance(result, dict) else {}
                if self.node_results is None:
                    self.node_results = {}
                self.node_results[node_name] = last_result
                return last_result
            except NonRetryableException:
                raise
            except Exception as exc:
                if retry_on_failure and attempt < max_retries:
                    attempt += 1
                    continue
                raise exc

    async def run_task(self, task: Task) -> None:
        task.update_status(TaskStatus.RUNNING)
        try:
            plan = self.compile_execution_plan()
            if self.execution_state is None:
                self.execution_state = ExecutionState()
            self.execution_state.current_plan = plan
            if self.execution_state.execution_history is None:
                self.execution_state.execution_history = []
            self.execution_state.total_iterations = 0

            iteration = 0
            step_index = 0

            while step_index < len(plan):
                if (
                    self.max_total_iterations is not None
                    and iteration >= self.max_total_iterations
                ):
                    break

                step = plan[step_index]
                nodes_to_run = [
                    (i, name)
                    for i, name in enumerate(step.nodes)
                    if not step.executed[i] and not step.skipped[i]
                ]

                if not nodes_to_run:
                    step_index += 1
                    continue

                node_config_parallel = False
                if nodes_to_run:
                    first_node = self.nodes.get(nodes_to_run[0][1]) if self.nodes else None
                    if first_node and first_node.node_config:
                        node_config_parallel = first_node.node_config.parallel

                if node_config_parallel or len(nodes_to_run) > 1:
                    tasks_coros = [
                        self.run_node(name) for _, name in nodes_to_run
                    ]
                    results = await asyncio.gather(*tasks_coros, return_exceptions=True)
                    for (idx, name), result in zip(nodes_to_run, results):
                        if isinstance(result, Exception):
                            self.mark_node_and_deps_as_skipped(name)
                        else:
                            step.executed[idx] = True
                            self.execution_state.mark_executed(step_index, idx)
                else:
                    idx, name = nodes_to_run[0]
                    try:
                        result = await self.run_node(name)
                        step.executed[idx] = True
                        self.execution_state.mark_executed(step_index, idx)

                        # Check for flow control redirect
                        if isinstance(result, dict) and "next_node" in result:
                            next_node = result["next_node"]
                            if next_node and self.nodes and next_node in self.nodes:
                                new_plan = self.compile_execution_plan_from(next_node)
                                plan = new_plan
                                self.execution_state.current_plan = plan
                                step_index = 0
                                iteration += 1
                                if self.execution_state.total_iterations is not None:
                                    self.execution_state.total_iterations += 1
                                continue
                    except NonRetryableException as exc:
                        task.set_error(str(exc))
                        return
                    except Exception as exc:
                        self.mark_node_and_deps_as_skipped(name)

                step_index += 1
                iteration += 1
                if self.execution_state.total_iterations is not None:
                    self.execution_state.total_iterations += 1

            if self.auto_snapshot:
                await self.snapshot(task, "final")

            output = None
            if self.cache:
                output = self.cache.get(self.output_mailbox)
            task.set_result(output)

        except Exception as exc:
            task.set_error(str(exc))

    async def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        snap_dir = pathlib.Path(f"snapshots/{task.id}/{name_hint}")
        snap_dir.mkdir(parents=True, exist_ok=True)

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
        snap_file = snap_dir / "state.json"
        with open(snap_file, "w") as f:
            json.dump(state_data, f, default=str)

        return snap_dir

    async def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        snap_file = snapshot_dir / "state.json"
        if not snap_file.exists():
            raise FileNotFoundError(f"Snapshot file not found: {snap_file}")

        with open(snap_file) as f:
            state_data = json.load(f)

        if self.cache is None:
            self.cache = Cache()
        self.cache.update(state_data.get("cache", {}))

        self.node_results = state_data.get("node_results", {})

        exec_state_data = state_data.get("execution_state")
        if exec_state_data:
            self.execution_state = ExecutionState(**exec_state_data)