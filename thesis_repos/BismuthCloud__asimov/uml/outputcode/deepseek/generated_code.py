from __future__ import annotations

import asyncio
import pathlib
import uuid
from abc import ABC, abstractmethod
from collections import Counter
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


# ------------------------------------------------------------
# Base classes and simple data holders
# ------------------------------------------------------------

class AsimovBase:
    model_config: Dict[str, Any] = {}


class Cache:
    """Simple dict‑like cache used throughout the system."""
    def __init__(self, initial: Optional[Dict[str, Any]] = None) -> None:
        self._data = initial or {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def keys(self) -> Set[str]:
        return set(self._data.keys())

    def update(self, other: Dict[str, Any]) -> None:
        self._data.update(other)


class ModuleType(AsimovBase):
    def __init__(self, name: str = ""):
        self.name = name


class ModelFamily(AsimovBase):
    def __init__(self, name: str = ""):
        self.name = name


class TaskStatus(AsimovBase):
    def __init__(self, name: str = ""):
        self.name = name


class SnapshotControl(AsimovBase):
    def __init__(self, name: str = ""):
        self.name = name


class NonRetryableException(Exception):
    pass


class Example(AsimovBase):
    def __init__(
        self,
        choice: str = "",
        choices: Optional[List[Dict[str, str]]] = None,
        message: str = "",
        reasoning: str = "",
    ):
        self.choice = choice
        self.choices = choices or []
        self.message = message
        self.reasoning = reasoning


# ------------------------------------------------------------
# Configuration / decision data classes
# ------------------------------------------------------------

class FlowDecision(AsimovBase):
    def __init__(
        self,
        cleanup_on_jump: Optional[bool] = None,
        condition: Optional[str] = None,
        condition_variables: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        next_node: str = "",
    ):
        self.cleanup_on_jump = cleanup_on_jump
        self.condition = condition
        self.condition_variables = condition_variables or []
        self.metadata = metadata or {}
        self.next_node = next_node


class FlowControlConfig(AsimovBase):
    def __init__(
        self,
        cleanup_on_default: bool = False,
        decisions: Sequence[FlowDecision] = (),
        default: Optional[str] = None,
    ):
        self.cleanup_on_default = cleanup_on_default
        self.decisions = list(decisions)
        self.default = default


class ModuleConfig(AsimovBase):
    def __init__(
        self,
        context: Optional[Dict[str, Any]] = None,
        middlewares: Optional[List[Middleware]] = None,
        stop_on_success: bool = False,
        timeout: float = 30.0,
    ):
        self.context = context or {}
        self.middlewares = middlewares or []
        self.stop_on_success = stop_on_success
        self.timeout = timeout


class NodeConfig(AsimovBase):
    def __init__(
        self,
        condition: Optional[str] = None,
        inputs: Optional[List[str]] = None,
        max_retries: int = 0,
        max_visits: Optional[int] = None,
        outputs: Optional[List[str]] = None,
        parallel: bool = False,
        retry_from: Optional[str] = None,
        retry_on_failure: bool = False,
    ):
        self.condition = condition
        self.inputs = inputs or []
        self.max_retries = max_retries
        self.max_visits = max_visits
        self.outputs = outputs or []
        self.parallel = parallel
        self.retry_from = retry_from
        self.retry_on_failure = retry_on_failure


class AgentDrivenFlowDecision(FlowDecision):
    def __init__(
        self,
        *args,
        examples: Optional[List[Example]] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.examples = examples or []


class AgentDrivenFlowControlConfig(FlowControlConfig):
    def __init__(
        self,
        *args,
        decisions: Sequence[AgentDrivenFlowDecision] = (),
        **kwargs,
    ):
        super().__init__(*args, decisions=decisions, **kwargs)


# ------------------------------------------------------------
# Middleware
# ------------------------------------------------------------

class Middleware(AsimovBase):
    def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        raise NotImplementedError


# ------------------------------------------------------------
# Execution state & plan
# ------------------------------------------------------------

class ExecutionStep:
    def __init__(self, nodes: List[str]):
        self.nodes = nodes
        self.executed = [False] * len(nodes)
        self.skipped = [False] * len(nodes)


class ExecutionPlan:
    def __init__(self, steps: Optional[List[ExecutionStep]] = None):
        self.steps = steps or []
        self.current_step_index = 0
        self.current_node_index = 0


class ExecutionState(AsimovBase):
    def __init__(self):
        self.current_plan: Optional[ExecutionPlan] = None
        self.execution_history: List[ExecutionPlan] = []
        self.execution_index: Optional[int] = None
        self.total_iterations: Optional[int] = None
        self._node_execution_map: Dict[str, Tuple[int, int]] = {}  # node_name -> (step_idx, node_idx)
        self._node_skipped: Dict[str, bool] = {}

    def mark_executed(self, step_index: int, node_index: int) -> None:
        if self.current_plan:
            self.current_plan.steps[step_index].executed[node_index] = True
            node_name = self.current_plan.steps[step_index].nodes[node_index]
            self._node_execution_map[node_name] = (step_index, node_index)

    def was_executed(self, node_name: str) -> bool:
        return node_name in self._node_execution_map

    def was_skipped(self, node_name: str) -> bool:
        return self._node_skipped.get(node_name, False)

    def mark_skipped(self, node_name: str) -> None:
        self._node_skipped[node_name] = True


# ------------------------------------------------------------
# Agent Module hierarchy
# ------------------------------------------------------------

class AgentModule(AsimovBase):
    def __init__(
        self,
        name: str = "",
        type: Optional[ModuleType] = None,
        config: Optional[ModuleConfig] = None,
        container: Optional[CompositeModule] = None,
        dependencies: Optional[List[str]] = None,
        executions: Optional[int] = None,
        input_mailboxes: Optional[List[str]] = None,
        output_mailbox: Optional[str] = None,
        trace: Optional[bool] = None,
    ):
        self.name = name
        self.type = type
        self.config = config or ModuleConfig()
        self.container = container
        self.dependencies = dependencies or []
        self.executions = executions
        self.input_mailboxes = input_mailboxes or []
        self.output_mailbox = output_mailbox
        self.trace = trace

    def is_success(self, result: Dict[str, Any]) -> bool:
        # default: consider non-error results successful
        return result.get("error") is None

    @abstractmethod
    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Union[Dict[str, Any], AsyncGenerator]:
        ...

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        # default implementation: just call process (which returns a dict) with semaphore
        async with semaphore:
            result = await self.process(cache, semaphore)
            if isinstance(result, dict):
                return result
            # if async generator, consume it? This is a placeholder
            return {}


class Executor(AgentModule, ABC):
    def __init__(
        self,
        name: str = "",
        type: Optional[ModuleType] = None,
        *args,
        **kwargs,
    ):
        super().__init__(name=name, type=type, *args, **kwargs)

    @abstractmethod
    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        ...


# ------------------------------------------------------------
# CompositeModule & Node
# ------------------------------------------------------------

class CompositeModule(AgentModule, ABC):
    def __init__(
        self,
        modules: Optional[List[AgentModule]] = None,
        node_config: Optional[NodeConfig] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.modules = modules or []
        self.node_config = node_config or NodeConfig()

    def apply_middlewares(self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        for mw in middlewares:
            data = mw.process(data, cache)
        return data

    async def run_module_with_concurrency_control(
        self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        async with semaphore:
            return await module.run(cache, semaphore)

    async def run_parallel_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        tasks = []
        for mod in self.modules:
            tasks.append(asyncio.create_task(self.run_module_with_concurrency_control(mod, cache, semaphore)))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        combined = {}
        for r in results:
            if isinstance(r, Exception):
                # handle exception or raise
                raise r
            combined.update(r)
        return combined

    async def run_sequential_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        result = {}
        for mod in self.modules:
            res = await self.run_module_with_concurrency_control(mod, cache, semaphore)
            result.update(res)
            if self.is_success(res):
                if self.config.stop_on_success:
                    break
            else:
                if not self.config.stop_on_success:
                    # continue?
                    pass
        return result

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        if self.node_config.parallel:
            return await self.run_parallel_modules(cache, semaphore)
        else:
            return await self.run_sequential_modules(cache, semaphore)


class Node(CompositeModule):
    def __init__(
        self,
        dependencies: Optional[List[str]] = None,
        snapshot: Optional[SnapshotControl] = None,
        *args,
        node_config: Optional[NodeConfig] = None,
        **kwargs,
    ):
        super().__init__(*args, node_config=node_config, **kwargs)
        self.dependencies = dependencies or []
        self.snapshot = snapshot
        self._all_nodes: Dict[str, Node] = {}

    def get_nodes(self) -> Dict[str, Node]:
        return self._all_nodes

    def set_nodes(self, nodes: Dict[str, Node]) -> None:
        self._all_nodes = nodes

    async def cancel_gen(self, agen):
        # Placeholder: cancel an async generator
        if hasattr(agen, 'aclose'):
            await agen.aclose()

    def cleanup(self):
        pass  # Release resources if needed


# ------------------------------------------------------------
# Flow Control Module
# ------------------------------------------------------------

class FlowControlModule(AgentModule):
    def __init__(self, flow_config: Optional[FlowControlConfig] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flow_config = flow_config or FlowControlConfig()

    def evaluate_condition(self, condition: str, cache: Cache, cache_keys: Set[str]) -> bool:
        # Simple evaluation: condition is a key in cache, value is truthy
        if condition in cache_keys:
            return bool(cache.get(condition))
        return False

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        # Evaluate flow decisions and jump to next node if condition matches
        # In practice this would trigger execution of the chosen node.
        # Here we just return the chosen node name for demonstration.
        chosen_node = self.flow_config.default
        for decision in self.flow_config.decisions:
            if decision.condition and self.evaluate_condition(
                decision.condition, cache, cache.keys()
            ):
                chosen_node = decision.next_node
                break
        return {"next_node": chosen_node}


# ------------------------------------------------------------
# Agent Directed Flow Control
# ------------------------------------------------------------

class InferenceClient:
    """Stub for an external inference client."""
    async def generate(self, prompt: str) -> str:
        # Simulate a response
        return "some_choice"


class AgentDirectedFlowControl(FlowControlModule):
    def __init__(
        self,
        inference_client: Optional[InferenceClient] = None,
        input_var: Optional[str] = None,
        system_description: str = "",
        use_historicals: Optional[bool] = None,
        voters: int = 1,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.flow_config = kwargs.get('flow_config') or AgentDrivenFlowControlConfig()  # ensure proper type
        self.inference_client = inference_client or InferenceClient()
        self.input_var = input_var
        self.system_description = system_description
        self.use_historicals = use_historicals
        self.voters = voters

    def set_attrs(self):
        pass

    async def gen(self, generation_input, cache):
        # Placeholder for generation that returns a decision string
        # Could use inference_client.
        resp = await self.inference_client.generate(generation_input)
        return resp

    @staticmethod
    def most_common_string(string_list: List[str]) -> str:
        if not string_list:
            return ""
        return Counter(string_list).most_common(1)[0][0]

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        # Voter‑based decision: generate multiple responses and take majority
        choices = []
        for _ in range(self.voters):
            resp = await self.gen(self.input_var, cache)
            choices.append(resp)
        chosen = self.most_common_string(choices)
        # Use chosen to match a decision? Simplified.
        return {"next_node": chosen}


# ------------------------------------------------------------
# Task
# ------------------------------------------------------------

class Task(AsimovBase):
    def __init__(
        self,
        objective: str = "",
        type: str = "",
        id: Optional[uuid.UUID] = None,
        params: Optional[Dict[str, Any]] = None,
        status: Optional[TaskStatus] = None,
    ):
        self.objective = objective
        self.type = type
        self.id = id or uuid.uuid4()
        self.params = params or {}
        self.status = status or TaskStatus("pending")
        self.result: Optional[Any] = None
        self.error: Optional[str] = None

    def set_error(self, error: str) -> None:
        self.error = error
        self.status = TaskStatus("error")

    def set_result(self, result: Any) -> None:
        self.result = result
        self.status = TaskStatus("completed")

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


# ------------------------------------------------------------
# Agent (graph orchestrator)
# ------------------------------------------------------------

class Agent(AsimovBase):
    def __init__(
        self,
        auto_snapshot: bool = False,
        cache: Optional[Cache] = None,
        error_mailbox: str = "",
        execution_state: Optional[ExecutionState] = None,
        graph: Optional[Dict[str, List[str]]] = None,
        max_concurrent_tasks: Optional[int] = None,
        max_total_iterations: Optional[int] = None,
        node_results: Optional[Dict[str, Any]] = None,
        nodes: Optional[Dict[str, Node]] = None,
        output_mailbox: str = "",
    ):
        self.auto_snapshot = auto_snapshot
        self.cache = cache or Cache()
        self.error_mailbox = error_mailbox
        self.execution_state = execution_state or ExecutionState()
        self.graph = graph or {}
        self.max_concurrent_tasks = max_concurrent_tasks or 1
        self.max_total_iterations = max_total_iterations
        self.node_results = node_results or {}
        self.nodes = nodes or {}
        self.output_mailbox = output_mailbox
        self._semaphore: Optional[asyncio.Semaphore] = None

    def set_semaphore(self) -> None:
        self._semaphore = asyncio.Semaphore(self.max_concurrent_tasks)

    def add_node(self, node: Node) -> None:
        self.nodes[node.name] = node
        node.set_nodes(self.nodes)
        # Update graph automatically? We'll rely on update_dependencies for edges.

    def add_multiple_nodes(self, nodes: List[Node]) -> None:
        for n in nodes:
            self.add_node(n)

    def update_dependencies(self, parent_node: str, new_node: str) -> None:
        if parent_node not in self.graph:
            self.graph[parent_node] = []
        if new_node not in self.graph[parent_node]:
            self.graph[parent_node].append(new_node)

    def _topological_sort(self, start: Optional[str] = None) -> List[ExecutionStep]:
        # Simple BFS-like level grouping based on dependencies.
        # Here we assume nodes' `dependencies` attribute gives the edges.
        # We'll build steps: each step contains nodes whose all deps are in previous steps.
        in_degree = {name: len(node.dependencies) for name, node in self.nodes.items()}
        ready = [name for name, deg in in_degree.items() if deg == 0]
        if start:
            # force start from given node (ignore others)
            ready = [start]
            in_degree = {name: 0 for name in self.nodes}
            in_degree[start] = 0
            for n in self.graph.get(start, []):
                in_degree[n] = 1  # make them depend on start

        execution_steps = []
        visited = set()
        while ready:
            step_nodes = []
            next_ready = []
            for name in ready:
                if name in visited:
                    continue
                visited.add(name)
                step_nodes.append(name)
                for child in self.graph.get(name, []):
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        next_ready.append(child)
            if step_nodes:
                execution_steps.append(ExecutionStep(step_nodes))
            ready = next_ready
        return execution_steps

    def compile_execution_plan(self) -> ExecutionPlan:
        steps = self._topological_sort()
        plan = ExecutionPlan(steps)
        self.execution_state.current_plan = plan
        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        steps = self._topological_sort(start=start_node)
        plan = ExecutionPlan(steps)
        self.execution_state.current_plan = plan
        return plan

    def get_dependent_chains(self, node_name: str) -> tuple[str, ...]:
        # Return a tuple of node names that depend on node_name (transitive closure)
        deps = set()
        stack = [node_name]
        while stack:
            cur = stack.pop()
            for child in self.graph.get(cur, []):
                if child not in deps:
                    deps.add(child)
                    stack.append(child)
        return tuple(sorted(deps))

    @staticmethod
    def is_success(result: Dict[str, Any]) -> bool:
        return result.get("error") is None

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        self.execution_state.mark_skipped(node_name)
        for dep in self.get_dependent_chains(node_name):
            self.execution_state.mark_skipped(dep)

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        # Return steps up to but not including the one containing `node`
        sliced = []
        for step in execution_plan:
            if node in step.get("nodes", []):
                break
            sliced.append(step)
        return sliced

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if self._semaphore is None:
            self.set_semaphore()
        node = self.nodes.get(node_name)
        if not node:
            raise ValueError(f"Node {node_name} not found")
        result = await node.run(self.cache, self._semaphore)
        self.node_results[node_name] = result
        # Mark as executed in plan
        plan = self.execution_state.current_plan
        if plan:
            for i, step in enumerate(plan.steps):
                if node_name in step.nodes:
                    idx = step.nodes.index(node_name)
                    self.execution_state.mark_executed(i, idx)
                    break
        return result

    async def run_task(self, task: Task) -> None:
        if self._semaphore is None:
            self.set_semaphore()
        # Generate and execute plan
        plan = self.compile_execution_plan()
        # Execute steps sequentially; within a step all nodes run concurrently
        for step_index, step in enumerate(plan.steps):
            tasks = []
            for node_index, node_name in enumerate(step.nodes):
                if self.execution_state.was_executed(node_name) or self.execution_state.was_skipped(node_name):
                    continue
                tasks.append(
                    asyncio.create_task(self.run_node(node_name))
                )
            if tasks:
                await asyncio.gather(*tasks)
            # Check if we need to stop? Not defined.
        task.set_result(self.node_results)

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        # Placeholder: save agent state to a directory
        snap_dir = pathlib.Path(name_hint) / str(task.id)
        snap_dir.mkdir(parents=True, exist_ok=True)
        # Save cache, results, execution state, etc.
        return snap_dir

    def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        # Placeholder: load state from directory
        pass