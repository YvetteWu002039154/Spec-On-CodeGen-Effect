import asyncio
import pathlib
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple, Union, AsyncGenerator, Awaitable
from collections import Counter
from enum import Enum
import sys

# =============================================================================
# Constants & Base Classes
# =============================================================================

class AsimovBase:
    model_config: Any

class NonRetryableException(Exception):
    pass

class ModelFamily:
    def __init__(self, name: str):
        self.name = name

class ModuleType:
    def __init__(self, name: str):
        self.name = name

class TaskStatus:
    def __init__(self, name: str):
        self.name = name

class Cache(dict):
    pass

class InferenceClient:
    pass

class ExecutionPlan:
    def __init__(self, steps: Optional[List['ExecutionStep']] = None):
        self.steps = steps or []

class ExecutionStep(AsimovBase):
    def __init__(self, nodes: List[str], executed: Optional[List[bool]] = None, skipped: Optional[List[bool]] = None):
        self.nodes = nodes
        self.executed = executed or [False] * len(nodes)
        self.skipped = skipped or [False] * len(nodes)

# =============================================================================
# Middleware
# =============================================================================

class Middleware(AsimovBase):
    def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        return data

# =============================================================================
# ModuleConfig
# =============================================================================

class ModuleConfig(AsimovBase):
    def __init__(self, context: Optional[Dict[str, Any]] = None, middlewares: Optional[List[Middleware]] = None,
                 stop_on_success: bool = False, timeout: float = 60.0):
        self.context = context or {}
        self.middlewares = middlewares or []
        self.stop_on_success = stop_on_success
        self.timeout = timeout

# =============================================================================
# NodeConfig
# =============================================================================

class NodeConfig(AsimovBase):
    def __init__(self, condition: Optional[str] = None, inputs: Optional[List[str]] = None,
                 max_retries: int = 0, max_visits: Optional[int] = None,
                 outputs: Optional[List[str]] = None, parallel: bool = False,
                 retry_from: Optional[str] = None, retry_on_failure: bool = False):
        self.condition = condition
        self.inputs = inputs or []
        self.max_retries = max_retries
        self.max_visits = max_visits
        self.outputs = outputs or []
        self.parallel = parallel
        self.retry_from = retry_from
        self.retry_on_failure = retry_on_failure

# =============================================================================
# SnapshotControl
# =============================================================================

class SnapshotControl(AsimovBase):
    def __init__(self, name: str):
        self.name = name

# =============================================================================
# FlowDecision
# =============================================================================

class FlowDecision(AsimovBase):
    def __init__(self, next_node: str, cleanup_on_jump: Optional[bool] = None,
                 condition: Optional[str] = None, condition_variables: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.next_node = next_node
        self.cleanup_on_jump = cleanup_on_jump
        self.condition = condition
        self.condition_variables = condition_variables or []
        self.metadata = metadata or {}

# =============================================================================
# AgentDrivenFlowDecision
# =============================================================================

class AgentDrivenFlowDecision(FlowDecision):
    def __init__(self, next_node: str, examples: Optional[List['Example']] = None,
                 cleanup_on_jump: Optional[bool] = None,
                 condition: Optional[str] = None, condition_variables: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        super().__init__(next_node=next_node, cleanup_on_jump=cleanup_on_jump,
                         condition=condition, condition_variables=condition_variables,
                         metadata=metadata)
        self.examples = examples or []

class Example(AsimovBase):
    def __init__(self, choice: str, choices: List[Dict[str, str]], message: str, reasoning: str):
        self.choice = choice
        self.choices = choices
        self.message = message
        self.reasoning = reasoning

# =============================================================================
# FlowControlConfig
# =============================================================================

class FlowControlConfig(AsimovBase):
    def __init__(self, cleanup_on_default: bool = False,
                 decisions: Optional[List[FlowDecision]] = None,
                 default: Optional[str] = None):
        self.cleanup_on_default = cleanup_on_default
        self.decisions = decisions or []
        self.default = default

class AgentDrivenFlowControlConfig(FlowControlConfig):
    def __init__(self, cleanup_on_default: bool = False,
                 decisions: Optional[List[AgentDrivenFlowDecision]] = None,
                 default: Optional[str] = None):
        super().__init__(cleanup_on_default=cleanup_on_default, decisions=decisions, default=default)

# =============================================================================
# ExecutionState
# =============================================================================

class ExecutionState(AsimovBase):
    def __init__(self, current_plan: Optional[ExecutionPlan] = None,
                 execution_history: Optional[List[ExecutionPlan]] = None,
                 execution_index: Optional[int] = None,
                 total_iterations: Optional[int] = None):
        self.current_plan = current_plan
        self.execution_history = execution_history or []
        self.execution_index = execution_index
        self.total_iterations = total_iterations

    def mark_executed(self, step_index: int, node_index: int):
        if self.current_plan and step_index < len(self.current_plan.steps):
            self.current_plan.steps[step_index].executed[node_index] = True

    def was_executed(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan.steps:
            if node_name in step.nodes:
                idx = step.nodes.index(node_name)
                return step.executed[idx]
        return False

    def was_skipped(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan.steps:
            if node_name in step.nodes:
                idx = step.nodes.index(node_name)
                return step.skipped[idx]
        return False

# =============================================================================
# AgentModule (Abstract)
# =============================================================================

class AgentModule(AsimovBase, ABC):
    def __init__(self, name: str, type: Optional[ModuleType] = None,
                 config: Optional[ModuleConfig] = None,
                 container: Optional['CompositeModule'] = None,
                 dependencies: Optional[List[str]] = None,
                 executions: Optional[int] = None,
                 input_mailboxes: Optional[List[str]] = None,
                 output_mailbox: Optional[str] = None,
                 trace: Optional[bool] = None):
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
        return result.get("success", False)

    @abstractmethod
    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Union[Dict[str, Any], AsyncGenerator]:
        ...

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        async with semaphore:
            result = await self.process(cache, semaphore)
            if isinstance(result, dict):
                return result
            # If it's an AsyncGenerator, collect items
            collected = {}
            async for item in result:
                collected.update(item)
            return collected

# =============================================================================
# Executor (Abstract)
# =============================================================================

class Executor(AgentModule, ABC):
    def __init__(self, name: str, type: Optional[ModuleType] = None, **kwargs):
        super().__init__(name=name, type=type, **kwargs)

    @abstractmethod
    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        pass

# =============================================================================
# CompositeModule
# =============================================================================

class CompositeModule(AgentModule):
    def __init__(self, name: str, modules: Optional[List[AgentModule]] = None,
                 node_config: Optional[NodeConfig] = None, **kwargs):
        super().__init__(name=name, **kwargs)
        self.modules = modules or []
        self.node_config = node_config or NodeConfig()

    def apply_middlewares(self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        for mw in middlewares:
            data = mw.process(data, cache)
        return data

    async def run_module_with_concurrency_control(self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await module.run(cache, semaphore)

    async def run_parallel_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        tasks = [self.run_module_with_concurrency_control(mod, cache, semaphore) for mod in self.modules]
        results = await asyncio.gather(*tasks)
        combined = {}
        for res in results:
            combined.update(res)
        return combined

    async def run_sequential_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        combined = {}
        for mod in self.modules:
            res = await self.run_module_with_concurrency_control(mod, cache, semaphore)
            combined.update(res)
            if self.node_config.retry_on_failure and not self.is_success(res):
                break
        return combined

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        if self.node_config.parallel:
            return await self.run_parallel_modules(cache, semaphore)
        return await self.run_sequential_modules(cache, semaphore)

# =============================================================================
# FlowControlModule
# =============================================================================

class FlowControlModule(AgentModule):
    def __init__(self, name: str, flow_config: FlowControlConfig, **kwargs):
        super().__init__(name=name, **kwargs)
        self.flow_config = flow_config

    def evaluate_condition(self, condition: str, cache: Cache, cache_keys: Set[str]) -> bool:
        # Simple evaluation: check if condition string evaluates to True in context of cache
        try:
            return bool(cache.get(condition, False))
        except Exception:
            return False

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        # Determine next node based on flow decisions
        chosen = self.flow_config.default
        for decision in self.flow_config.decisions:
            if decision.condition and self.evaluate_condition(decision.condition, cache, set(cache.keys())):
                chosen = decision.next_node
                break
        return {"next_node": chosen, "flow_decision": True}

# =============================================================================
# AgentDirectedFlowControl
# =============================================================================

class AgentDirectedFlowControl(FlowControlModule):
    def __init__(self, name: str, flow_config: AgentDrivenFlowControlConfig,
                 inference_client: InferenceClient,
                 input_var: Optional[str] = None,
                 system_description: str = "",
                 use_historicals: Optional[bool] = None,
                 voters: int = 1,
                 **kwargs):
        super().__init__(name=name, flow_config=flow_config, **kwargs)
        self.flow_config = flow_config
        self.inference_client = inference_client
        self.input_var = input_var
        self.system_description = system_description
        self.use_historicals = use_historicals
        self.voters = voters

    async def gen(self, generation_input: Any, cache: Cache) -> str:
        # Simulate generation using inference client
        return "mock_decision"

    def most_common_string(self, string_list: List[str]) -> str:
        if not string_list:
            return ""
        counter = Counter(string_list)
        return counter.most_common(1)[0][0]

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        # Use voters to generate decisions
        decisions = []
        for _ in range(self.voters):
            dec = await self.gen(self.input_var, cache)
            decisions.append(dec)
        chosen = self.most_common_string(decisions)
        return {"next_node": chosen, "agent_directed": True}

    def set_attrs(self):
        pass

# =============================================================================
# Node (inherits CompositeModule)
# =============================================================================

class Node(CompositeModule):
    def __init__(self, name: str, modules: Optional[List[AgentModule]] = None,
                 node_config: Optional[NodeConfig] = None,
                 dependencies: Optional[List[str]] = None,
                 type: Optional[ModuleType] = None,
                 snapshot: Optional[SnapshotControl] = None,
                 **kwargs):
        super().__init__(name=name, modules=modules, node_config=node_config, type=type, **kwargs)
        self.dependencies = dependencies or []
        self.snapshot = snapshot
        self._nodes_dict: Optional[Dict[str, 'Node']] = None

    def get_nodes(self) -> Dict[str, 'Node']:
        return self._nodes_dict or {}

    def set_nodes(self, nodes: Dict[str, 'Node']):
        self._nodes_dict = nodes

    async def cancel_gen(self, agen: AsyncGenerator):
        if agen is not None:
            await agen.aclose()

    def cleanup(self):
        pass

# =============================================================================
# Task
# =============================================================================

class Task(AsimovBase):
    def __init__(self, type: str, objective: str = "",
                 params: Optional[Dict[str, Any]] = None,
                 id: Optional[uuid.UUID] = None,
                 status: Optional[TaskStatus] = None,
                 error: Optional[str] = None,
                 result: Optional[Any] = None):
        self.type = type
        self.objective = objective
        self.params = params or {}
        self.id = id or uuid.uuid4()
        self.status = status or TaskStatus("pending")
        self.error = error
        self.result = result

    def set_error(self, error: str) -> None:
        self.error = error
        self.status = TaskStatus("error")

    def set_result(self, result: Any) -> None:
        self.result = result
        self.status = TaskStatus("completed")

    def update_status(self, status: TaskStatus) -> None:
        self.status = status

# =============================================================================
# Agent (Main Controller)
# =============================================================================

class Agent(AsimovBase):
    def __init__(self,
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
                 **kwargs):
        self.auto_snapshot = auto_snapshot
        self.cache = cache or Cache()
        self.error_mailbox = error_mailbox
        self.execution_state = execution_state or ExecutionState()
        self.graph = graph or {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_total_iterations = max_total_iterations
        self.node_results = node_results or {}
        self.nodes: Dict[str, Node] = nodes or {}
        self.output_mailbox = output_mailbox
        self._semaphore: Optional[asyncio.Semaphore] = None

    def add_node(self, node: Node):
        self.nodes[node.name] = node
        node.set_nodes(self.nodes)
        self.graph.setdefault(node.name, [])
        for dep in node.dependencies:
            self.graph.setdefault(dep, []).append(node.name)

    def add_multiple_nodes(self, nodes: List[Node]):
        for node in nodes:
            self.add_node(node)

    def compile_execution_plan(self) -> ExecutionPlan:
        # topological sort based on dependencies
        in_degree = {n: 0 for n in self.graph}
        for src, dsts in self.graph.items():
            for dst in dsts:
                in_degree[dst] = in_degree.get(dst, 0) + 1
        queue = [n for n in self.nodes if in_degree.get(n, 0) == 0]
        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in self.graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        # Build steps (each step groups independent nodes?)
        # Simple: one step per node
        steps = [ExecutionStep(nodes=[n]) for n in order]
        return ExecutionPlan(steps=steps)

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        # DFS from start node
        visited = set()
        order = []
        def dfs(n):
            if n in visited:
                return
            visited.add(n)
            for dep in self.nodes[n].dependencies:
                dfs(dep)
            order.append(n)
        dfs(start_node)
        # reverse to get dependencies first
        order.reverse()
        # Build steps similarly
        # Actually we need to respect full graph dependencies? For simplicity:
        steps = [ExecutionStep(nodes=[n]) for n in order]
        return ExecutionPlan(steps=steps)

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        chain = []
        visited = set()
        def dfs(n):
            if n in visited:
                return
            visited.add(n)
            chain.append(n)
            for child in self.graph.get(n, []):
                dfs(child)
        dfs(node_name)
        return tuple(chain)

    def is_success(self, result: Dict[str, Any]) -> bool:
        return result.get("success", False)

    def mark_node_and_deps_as_skipped(self, node_name: str):
        if not self.execution_state.current_plan:
            return
        for step in self.execution_state.current_plan.steps:
            if node_name in step.nodes:
                idx = step.nodes.index(node_name)
                step.skipped[idx] = True
                # also mark dependencies as skipped?
                for dep in self.nodes[node_name].dependencies:
                    self.mark_node_and_deps_as_skipped(dep)

    async def run_from_snapshot(self, snapshot_dir: pathlib.Path):
        pass

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        node = self.nodes.get(node_name)
        if not node:
            return {"success": False, "error": f"Node {node_name} not found"}
        if self._semaphore is None:
            self.set_semaphore()
        result = await node.run(self.cache, self._semaphore)
        self.node_results[node_name] = result
        if self.auto_snapshot:
            await self.snapshot(None, name_hint=node_name)
        return result

    async def run_task(self, task: Task) -> None:
        # Execute based on task.type? For simplicity, run whole plan
        plan = self.compile_execution_plan()
        self.execution_state.current_plan = plan
        for i, step in enumerate(plan.steps):
            for j, node_name in enumerate(step.nodes):
                self.execution_state.mark_executed(i, j)
                await self.run_node(node_name)

    def set_semaphore(self):
        if self.max_concurrent_tasks:
            self._semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        else:
            self._semaphore = asyncio.Semaphore(10)  # default

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        # Slice the plan up to the node (not including?)
        sliced = []
        for step in execution_plan:
            if node in step.get("nodes", []):
                break
            sliced.append(step)
        return sliced

    async def snapshot(self, task: Optional[Task], name_hint: str) -> pathlib.Path:
        # Simulate saving snapshot
        dir_name = f"snapshot_{name_hint}"
        path = pathlib.Path(dir_name)
        path.mkdir(exist_ok=True)
        return path

    def update_dependencies(self, parent_node: str, new_node: str):
        self.graph.setdefault(parent_node, []).append(new_node)
        self.nodes[new_node].dependencies.append(parent_node)

# =============================================================================
# Helper to satisfy missing references
# =============================================================================

# Ensure all forward references are resolved
CompositeModule.update_forward_refs()
AgentModule.update_forward_refs()
Node.update_forward_refs()