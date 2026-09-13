from abc import ABC, abstractmethod
import asyncio
from collections import Counter
from dataclasses import dataclass, field
import inspect
import json
from pathlib import Path
from typing import Any, AsyncGenerator, Awaitable, Dict, List, Optional, Sequence, Set, Tuple, Union
from uuid import UUID


class Cache:
    def __init__(self) -> None:
        self.data: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def __contains__(self, key: object) -> bool:
        return key in self.data

    def keys(self) -> Any:
        return self.data.keys()

    def items(self) -> Any:
        return self.data.items()

    def update(self, other: Dict[str, Any]) -> None:
        self.data.update(other)

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value


class InferenceClient:
    async def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        raise NotImplementedError


@dataclass
class AsimovBase:
    model_config: Any = None


@dataclass
class ExecutionStep:
    executed: List[bool] = field(default_factory=list)
    nodes: List[str] = field(default_factory=list)
    skipped: List[bool] = field(default_factory=list)

    def __post_init__(self) -> None:
        count = len(self.nodes)
        if not self.executed:
            self.executed = [False] * count
        if not self.skipped:
            self.skipped = [False] * count


@dataclass
class ExecutionPlan:
    steps: List[ExecutionStep] = field(default_factory=list)

    def get_step_index(self, node_name: str) -> Optional[int]:
        for index, step in enumerate(self.steps):
            if node_name in step.nodes:
                return index
        return None


class ModuleType:
    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"ModuleType(name={self.name!r})"


class ModelFamily:
    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"ModelFamily(name={self.name!r})"


class TaskStatus:
    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"TaskStatus(name={self.name!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TaskStatus) and self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)


class NonRetryableException(Exception):
    pass


@dataclass
class Middleware(AsimovBase):
    def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        return data


@dataclass
class ModuleConfig(AsimovBase):
    context: Optional[Dict[str, Any]] = None
    middlewares: Optional[List[Middleware]] = None
    stop_on_success: bool = False
    timeout: float = 60.0


@dataclass
class NodeConfig(AsimovBase):
    condition: Optional[str] = None
    inputs: Optional[List[str]] = None
    max_retries: int = 0
    max_visits: Optional[int] = None
    outputs: Optional[List[str]] = None
    parallel: bool = False
    retry_from: Optional[str] = None
    retry_on_failure: bool = False


@dataclass
class SnapshotControl(AsimovBase):
    name: str = ""


@dataclass
class Example:
    choice: str = ""
    choices: List[Dict[str, str]] = field(default_factory=list)
    message: str = ""
    reasoning: str = ""


@dataclass
class FlowDecision(AsimovBase):
    cleanup_on_jump: Optional[bool] = None
    condition: Optional[str] = None
    condition_variables: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    next_node: str = ""


@dataclass
class AgentDrivenFlowDecision(FlowDecision):
    examples: Optional[List[Example]] = None


@dataclass
class FlowControlConfig(AsimovBase):
    cleanup_on_default: bool = False
    decisions: Sequence[FlowDecision] = field(default_factory=list)
    default: Optional[str] = None


@dataclass
class AgentDrivenFlowControlConfig(FlowControlConfig):
    decisions: Sequence[AgentDrivenFlowDecision] = field(default_factory=list)
    default: Optional[str] = None


@dataclass
class AgentModule(AsimovBase, ABC):
    config: Optional[ModuleConfig] = None
    container: Optional['CompositeModule'] = None
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = None
    input_mailboxes: Optional[List[str]] = None
    name: str = ""
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = None
    type: Optional[ModuleType] = None

    def is_success(self, result: Dict[str, Any]) -> bool:
        if isinstance(result, dict):
            return bool(result.get("success", False))
        return bool(result)

    @abstractmethod
    def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Union[Awaitable[Dict[str, Any]], AsyncGenerator[Any, Any]]:
        raise NotImplementedError

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> dict[str, Any]:
        async def _run() -> Dict[str, Any]:
            result = self.process(cache, semaphore)
            if inspect.isawaitable(result):
                return await result
            if hasattr(result, "__aiter__"):
                collected: Any = None
                async for item in result:
                    collected = item
                if isinstance(collected, dict):
                    return collected
                return {"result": collected}
            if isinstance(result, dict):
                return result
            return {"result": result}

        return asyncio.run(_run())


@dataclass
class CompositeModule(AgentModule):
    modules: List[AgentModule] = field(default_factory=list)
    node_config: Optional[NodeConfig] = None

    def apply_middlewares(self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        current = data
        for middleware in middlewares or []:
            current = middleware.process(current, cache) or current
        return current

    def run_module_with_concurrency_control(self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return module.run(cache, semaphore)

    async def _run_module_async(self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore) -> Any:
        result = module.process(cache, semaphore)
        if inspect.isawaitable(result):
            return await result
        if hasattr(result, "__aiter__"):
            collected: Any = None
            async for item in result:
                collected = item
            return collected
        return result

    def run_parallel_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        async def _run() -> List[Any]:
            return await asyncio.gather(*(self._run_module_async(module, cache, semaphore) for module in self.modules))

        results = asyncio.run(_run())
        return {"results": results}

    def run_sequential_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        results = [self.run_module_with_concurrency_control(module, cache, semaphore) for module in self.modules]
        return {"results": results}

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            data = self.run_parallel_modules(cache, semaphore)
        else:
            data = self.run_sequential_modules(cache, semaphore)

        if self.config and self.config.middlewares:
            data = self.apply_middlewares(self.config.middlewares, data, cache)

        return data

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return self.run(cache, semaphore)


@dataclass
class Node(CompositeModule):
    snapshot: Optional[SnapshotControl] = None
    _nodes: Optional[Dict[str, 'Node']] = field(default=None, repr=False)

    def cancel_gen(self, agen: Any) -> None:
        if agen is None:
            return
        aclose = getattr(agen, "aclose", None)
        if callable(aclose):
            try:
                asyncio.run(aclose())
            except Exception:
                pass
        else:
            close = getattr(agen, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass

    def cleanup(self) -> None:
        self.modules = []
        self.executions = None
        self._nodes = {}

    def get_nodes(self) -> Dict[str, 'Node']:
        return self._nodes or {}

    def set_nodes(self, nodes: Dict[str, 'Node']) -> None:
        self._nodes = nodes


class Executor(AgentModule, ABC):
    @abstractmethod
    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        raise NotImplementedError


@dataclass
class FlowControlModule(AgentModule):
    flow_config: Optional[FlowControlConfig] = None

    def evaluate_condition(self, condition: str, cache: Cache, cache_keys: Set[str]) -> bool:
        if not condition:
            return True
        if condition in cache_keys:
            return bool(cache.get(condition))
        data = getattr(cache, "data", {})
        try:
            return bool(eval(condition, {"__builtins__": {}}, data))
        except Exception:
            return False

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        if not self.flow_config:
            return {}

        for decision in self.flow_config.decisions:
            if decision.condition and self.evaluate_condition(decision.condition, cache, set(cache.keys())):
                return {"next_node": decision.next_node}

        if self.flow_config.default:
            return {"next_node": self.flow_config.default}

        return {}

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return self.run(cache, semaphore)


@dataclass
class AgentDirectedFlowControl(FlowControlModule):
    flow_config: Optional[AgentDrivenFlowControlConfig] = None
    inference_client: Optional[InferenceClient] = None
    input_var: Optional[str] = None
    system_description: str = ""
    use_historicals: Optional[bool] = None
    voters: int = 1

    async def gen(self, generation_input: Any, cache: Cache) -> str:
        if self.inference_client is None:
            return str(generation_input)

        messages: List[Dict[str, str]] = []
        if self.system_description:
            messages.append({"role": "system", "content": self.system_description})
        messages.append({"role": "user", "content": str(generation_input)})

        try:
            return await self.inference_client.generate(messages, cache=cache, use_historicals=self.use_historicals)
        except TypeError:
            return await self.inference_client.generate(messages)

    def most_common_string(self, string_list: List[str]) -> str:
        if not string_list:
            return ""
        return Counter(string_list).most_common(1)[0][0]

    def set_attrs(self) -> None:
        if self.flow_config is None:
            self.flow_config = AgentDrivenFlowControlConfig()
        if self.voters <= 0:
            self.voters = 1
        if self.input_var is None:
            self.input_var = "input"

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        self.set_attrs()

        if not self.flow_config or not self.flow_config.decisions:
            return {}

        choices = [decision.next_node for decision in self.flow_config.decisions]
        if not choices:
            return {}

        generation_input = cache.get(self.input_var) if self.input_var else cache.get("input")

        async def _vote() -> List[str]:
            votes = []
            for _ in range(self.voters):
                votes.append((await self.gen(generation_input, cache)).strip())
            return votes

        votes = asyncio.run(_vote())
        chosen = self.most_common_string(votes)

        for decision in self.flow_config.decisions:
            if chosen == decision.next_node:
                return {"next_node": decision.next_node}
            if decision.examples:
                for example in decision.examples:
                    if example.choice == chosen:
                        return {"next_node": decision.next_node}

        if self.flow_config.default:
            return {"next_node": self.flow_config.default}

        return {"next_node": choices[0]}


@dataclass
class ExecutionState(AsimovBase):
    current_plan: Optional[ExecutionPlan] = None
    execution_history: Optional[List[ExecutionPlan]] = field(default_factory=list)
    execution_index: Optional[int] = None
    total_iterations: Optional[int] = None

    def mark_executed(self, step_index: int, node_index: int) -> None:
        if not self.current_plan or step_index < 0 or step_index >= len(self.current_plan.steps):
            return
        step = self.current_plan.steps[step_index]
        if node_index < 0 or node_index >= len(step.nodes):
            return
        step.executed[node_index] = True
        step.skipped[node_index] = False
        self.execution_index = step_index

    def was_executed(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan.steps:
            for index, name in enumerate(step.nodes):
                if name == node_name:
                    return index < len(step.executed) and step.executed[index]
        return False

    def was_skipped(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan.steps:
            for index, name in enumerate(step.nodes):
                if name == node_name:
                    return index < len(step.skipped) and step.skipped[index]
        return False


@dataclass
class Agent(AsimovBase):
    auto_snapshot: bool = False
    cache: Optional[Cache] = None
    error_mailbox: str = ""
    execution_state: Optional[ExecutionState] = None
    graph: Optional[Dict[str, List[str]]] = None
    max_concurrent_tasks: Optional[int] = None
    max_total_iterations: Optional[int] = None
    node_results: Optional[Dict[str, Any]] = None
    nodes: Optional[Dict[str, Node]] = None
    output_mailbox: str = ""

    def add_multiple_nodes(self, nodes: List[Node]) -> None:
        for node in nodes:
            self.add_node(node)

    def add_node(self, node: Node) -> None:
        if self.nodes is None:
            self.nodes = {}
        if self.graph is None:
            self.graph = {}

        self.nodes[node.name] = node
        node.set_nodes(self.nodes)
        self.graph[node.name] = list(node.dependencies or [])

    def compile_execution_plan(self) -> ExecutionPlan:
        if not self.nodes:
            return ExecutionPlan()

        node_names = list(self.nodes.keys())
        graph = self.graph or {}
        adj: Dict[str, List[str]] = {name: [] for name in node_names}
        indegree: Dict[str, int] = {name: 0 for name in node_names}

        for name in node_names:
            for dep in graph.get(name, []):
                if dep in adj:
                    adj[dep].append(name)
                    indegree[name] += 1

        ready = [name for name in node_names if indegree[name] == 0]
        steps: List[ExecutionStep] = []

        while ready:
            steps.append(ExecutionStep(nodes=list(ready), executed=[False] * len(ready), skipped=[False] * len(ready)))
            next_ready: List[str] = []
            for name in ready:
                for dependent in adj.get(name, []):
                    indegree[dependent] -= 1
                    if indegree[dependent] == 0:
                        next_ready.append(dependent)
            ready = next_ready

        return ExecutionPlan(steps=steps)

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        full_plan = self.compile_execution_plan()
        index = full_plan.get_step_index(start_node)
        if index is None:
            return ExecutionPlan()
        return ExecutionPlan(steps=full_plan.steps[index:])

    def get_dependent_chains(self, node_name: str) -> tuple[str, ...]:
        if not self.graph:
            return ()

        dependents: Dict[str, List[str]] = {}
        for node, deps in self.graph.items():
            for dep in deps:
                dependents.setdefault(dep, [])
                if node not in dependents[dep]:
                    dependents[dep].append(node)

        chain: List[str] = []
        queue = [node_name]

        while queue:
            current = queue.pop(0)
            if current in chain:
                continue
            chain.append(current)
            for downstream in dependents.get(current, []):
                if downstream not in chain:
                    queue.append(downstream)

        return tuple(chain)

    def is_success(self, result: Any) -> bool:
        if isinstance(result, dict):
            return bool(result.get("success", False))
        return bool(result)

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        chain = set(self.get_dependent_chains(node_name))
        if not self.execution_state or not self.execution_state.current_plan:
            return
        for step in self.execution_state.current_plan.steps:
            for index, name in enumerate(step.nodes):
                if name in chain and index < len(step.skipped):
                    step.skipped[index] = True

    def run_from_snapshot(self, snapshot_dir: Path) -> None:
        if snapshot_dir.exists():
            self.cache = Cache()
            self.cache.set("snapshot_dir", str(snapshot_dir))

    def run_node(self, node_name: str) -> Dict[str, Any]:
        if not self.nodes or node_name not in self.nodes:
            return {}

        cache = self.cache if self.cache is not None else Cache()
        semaphore = self.set_semaphore()
        result = self.nodes[node_name].run(cache, semaphore)

        if self.node_results is None:
            self.node_results = {}
        self.node_results[node_name] = result
        return result

    def run_task(self, task: Task) -> None:
        if self.execution_state is None:
            self.execution_state = ExecutionState()
        self.execution_state.current_plan = self.compile_execution_plan()
        self.execution_state.total_iterations = self.max_total_iterations

        if self.node_results is None:
            self.node_results = {}

        task.update_status(TaskStatus("running"))

        for step_index, step in enumerate(self.execution_state.current_plan.steps):
            for node_index, node_name in enumerate(step.nodes):
                if step.executed[node_index] or step.skipped[node_index]:
                    continue

                try:
                    self.run_node(node_name)
                    step.executed[node_index] = True
                    self.execution_state.mark_executed(step_index, node_index)
                except NonRetryableException as exc:
                    step.skipped[node_index] = True
                    self.mark_node_and_deps_as_skipped(node_name)
                    task.set_error(str(exc))
                    task.update_status(TaskStatus("failed"))
                    return
                except Exception as exc:
                    step.skipped[node_index] = True
                    self.mark_node_and_deps_as_skipped(node_name)
                    task.set_error(str(exc))
                    task.update_status(TaskStatus("failed"))
                    return

        task.set_result(self.node_results)
        task.update_status(TaskStatus("completed"))

    def set_semaphore(self) -> asyncio.Semaphore:
        limit = self.max_concurrent_tasks if self.max_concurrent_tasks and self.max_concurrent_tasks > 0 else 1
        semaphore = asyncio.Semaphore(limit)
        self._semaphore = semaphore
        return semaphore

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        for index, step in enumerate(execution_plan):
            nodes = step.get("nodes") or [step.get("node")]
            if node in nodes:
                return execution_plan[:index]
        return execution_plan

    def snapshot(self, task: Task, name_hint: str) -> Path:
        snapshot_dir = Path("snapshots") / f"{task.id}-{name_hint}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "task_id": str(task.id) if task.id else None,
            "objective": task.objective,
            "node_results": self.node_results,
        }
        (snapshot_dir / "snapshot.json").write_text(json.dumps(payload, default=str))
        return snapshot_dir

    def update_dependencies(self, parent_node: str, new_node: str) -> None:
        if self.graph is None:
            self.graph = {}

        if parent_node not in self.graph:
            self.graph[parent_node] = []

        if new_node not in self.graph[parent_node]:
            self.graph[parent_node].append(new_node)

        if self.nodes and parent_node in self.nodes:
            deps = self.nodes[parent_node].dependencies
            if deps is None:
                deps = []
                self.nodes[parent_node].dependencies = deps
            if new_node not in deps:
                deps.append(new_node)


@dataclass
class Task(AsimovBase):
    error: Optional[str] = None
    id: Optional[UUID] = None
    objective: str = ""
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    status: Optional[TaskStatus] = None
    type: str = ""

    def set_error(self, error: str) -> None:
        self.error = error

    def set_result(self, result: Any) -> None:
        self.result = result

    def update_status(self, status: TaskStatus) -> None:
        self.status = status