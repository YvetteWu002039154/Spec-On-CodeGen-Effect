import asyncio
import pathlib
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncGenerator, Awaitable, Dict, List, Optional, Sequence, Set, Tuple, Union
from uuid import UUID, uuid4


class ExecutionPlan:
    pass


class Cache:
    pass


class AsimovBase:
    model_config: Any = None


class ModuleType(Enum):
    pass


class ModelFamily(Enum):
    pass


class SnapshotControl:
    def __init__(self, name: str):
        self.name = name


class ExecutionStep:
    def __init__(self, nodes: List[str], executed: Optional[List[bool]] = None, skipped: Optional[List[bool]] = None):
        self.nodes = nodes
        self.executed = executed if executed is not None else [False] * len(nodes)
        self.skipped = skipped if skipped is not None else [False] * len(nodes)


class ExecutionState(AsimovBase):
    def __init__(self,
                 current_plan: Optional[ExecutionPlan] = None,
                 execution_history: Optional[List[ExecutionPlan]] = None,
                 execution_index: Optional[int] = None,
                 total_iterations: Optional[int] = None):
        self.current_plan = current_plan
        self.execution_history = execution_history if execution_history is not None else []
        self.execution_index = execution_index
        self.total_iterations = total_iterations

    def mark_executed(self, step_index: int, node_index: int) -> None:
        if self.current_plan and hasattr(self.current_plan, 'steps'):
            step = self.current_plan.steps[step_index]
            if 0 <= node_index < len(step.nodes):
                step.executed[node_index] = True

    def was_executed(self, node_name: str) -> bool:
        if self.execution_history:
            for plan in self.execution_history:
                if hasattr(plan, 'steps'):
                    for step in plan.steps:
                        if node_name in step.nodes:
                            idx = step.nodes.index(node_name)
                            return step.executed[idx]
        return False

    def was_skipped(self, node_name: str) -> bool:
        if self.execution_history:
            for plan in self.execution_history:
                if hasattr(plan, 'steps'):
                    for step in plan.steps:
                        if node_name in step.nodes:
                            idx = step.nodes.index(node_name)
                            return step.skipped[idx]
        return False


class NodeConfig(AsimovBase):
    def __init__(self,
                 condition: Optional[str] = None,
                 inputs: Optional[List[str]] = None,
                 max_retries: int = 0,
                 max_visits: Optional[int] = None,
                 outputs: Optional[List[str]] = None,
                 parallel: bool = False,
                 retry_from: Optional[str] = None,
                 retry_on_failure: bool = False):
        self.condition = condition
        self.inputs = inputs
        self.max_retries = max_retries
        self.max_visits = max_visits
        self.outputs = outputs
        self.parallel = parallel
        self.retry_from = retry_from
        self.retry_on_failure = retry_on_failure


class ModuleConfig(AsimovBase):
    def __init__(self,
                 context: Optional[Dict[str, Any]] = None,
                 middlewares: Optional[List['Middleware']] = None,
                 stop_on_success: bool = False,
                 timeout: float = 0.0):
        self.context = context
        self.middlewares = middlewares if middlewares is not None else []
        self.stop_on_success = stop_on_success
        self.timeout = timeout


class Middleware(AsimovBase):
    def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        return data


class FlowDecision(AsimovBase):
    def __init__(self,
                 next_node: str,
                 cleanup_on_jump: Optional[bool] = None,
                 condition: Optional[str] = None,
                 condition_variables: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.next_node = next_node
        self.cleanup_on_jump = cleanup_on_jump
        self.condition = condition
        self.condition_variables = condition_variables
        self.metadata = metadata


class FlowControlConfig(AsimovBase):
    def __init__(self,
                 decisions: Sequence[FlowDecision],
                 default: Optional[str] = None,
                 cleanup_on_default: bool = False):
        self.decisions = list(decisions)
        self.default = default
        self.cleanup_on_default = cleanup_on_default


class AgentDirectedFlowDecision(FlowDecision):
    def __init__(self,
                 next_node: str,
                 cleanup_on_jump: Optional[bool] = None,
                 condition: Optional[str] = None,
                 condition_variables: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 examples: Optional[List['Example']] = None):
        super().__init__(next_node, cleanup_on_jump, condition, condition_variables, metadata)
        self.examples = examples


class AgentDrivenFlowControlConfig(FlowControlConfig):
    def __init__(self,
                 decisions: Sequence[AgentDirectedFlowDecision],
                 default: Optional[str] = None,
                 cleanup_on_default: bool = False):
        super().__init__(decisions, default, cleanup_on_default)


class Example:
    def __init__(self, choice: str, choices: List[Dict[str, str]], message: str, reasoning: str):
        self.choice = choice
        self.choices = choices
        self.message = message
        self.reasoning = reasoning


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(AsimovBase):
    def __init__(self,
                 objective: str,
                 type: str,
                 params: Optional[Dict[str, Any]] = None,
                 error: Optional[str] = None,
                 id: Optional[UUID] = None,
                 result: Optional[Any] = None,
                 status: TaskStatus = TaskStatus.PENDING):
        self.objective = objective
        self.type = type
        self.params = params
        self.error = error
        self.id = id or uuid4()
        self.result = result
        self.status = status

    def set_error(self, error: str) -> None:
        self.error = error

    def set_result(self, result: Any) -> None:
        self.result = result

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


class NonRetryableException(Exception):
    pass


class AgentModule(AsimovBase, ABC):
    def __init__(self,
                 name: str,
                 type: Optional[ModuleType] = None,
                 config: Optional[ModuleConfig] = None,
                 container: Optional['CompositeModule'] = None,
                 dependencies: Optional[List[str]] = None,
                 executions: Optional[int] = None,
                 input_mailboxes: Optional[List[str]] = None,
                 output_mailbox: Optional[str] = None,
                 trace: Optional[bool] = None):
        self.name = name
        self.type = type
        self.config = config
        self.container = container
        self.dependencies = dependencies
        self.executions = executions
        self.input_mailboxes = input_mailboxes
        self.output_mailbox = output_mailbox
        self.trace = trace

    def is_success(self, result: Dict[str, Any]) -> bool:
        return True

    @abstractmethod
    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Union[Awaitable[Dict[str, Any]], AsyncGenerator]:
        ...

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        async with semaphore:
            result = await self.process(cache, semaphore)
            return result


class CompositeModule(AgentModule):
    def __init__(self,
                 name: str,
                 type: Optional[ModuleType] = None,
                 config: Optional[ModuleConfig] = None,
                 container: Optional['CompositeModule'] = None,
                 dependencies: Optional[List[str]] = None,
                 executions: Optional[int] = None,
                 input_mailboxes: Optional[List[str]] = None,
                 output_mailbox: Optional[str] = None,
                 trace: Optional[bool] = None,
                 modules: Optional[List[AgentModule]] = None,
                 node_config: Optional[NodeConfig] = None):
        super().__init__(name, type, config, container, dependencies, executions, input_mailboxes, output_mailbox, trace)
        self.modules = modules if modules is not None else []
        self.node_config = node_config

    def apply_middlewares(self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        for mw in middlewares:
            data = mw.process(data, cache)
        return data

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        self.set_nodes()  # ensure nodes are set before running
        return await super().run(cache, semaphore)

    async def run_module_with_concurrency_control(self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await module.run(cache, semaphore)

    async def run_parallel_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        tasks = [self.run_module_with_concurrency_control(m, cache, semaphore) for m in self.modules]
        results = await asyncio.gather(*tasks)
        return {"results": results}

    async def run_sequential_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        results = []
        for module in self.modules:
            results.append(await self.run_module_with_concurrency_control(module, cache, semaphore))
        return {"results": results}


class Node(CompositeModule):
    def __init__(self,
                 name: str,
                 type: Optional[ModuleType] = None,
                 config: Optional[ModuleConfig] = None,
                 container: Optional['CompositeModule'] = None,
                 dependencies: Optional[List[str]] = None,
                 executions: Optional[int] = None,
                 input_mailboxes: Optional[List[str]] = None,
                 output_mailbox: Optional[str] = None,
                 trace: Optional[bool] = None,
                 modules: Optional[List[AgentModule]] = None,
                 node_config: Optional[NodeConfig] = None,
                 snapshot: Optional[SnapshotControl] = None):
        super().__init__(name, type, config, container, dependencies, executions, input_mailboxes, output_mailbox, trace, modules, node_config)
        self.snapshot = snapshot
        self._nodes_dict: Dict[str, 'Node'] = {}

    def get_nodes(self) -> Dict[str, 'Node']:
        return self._nodes_dict

    def set_nodes(self, nodes: Dict[str, 'Node']) -> None:
        self._nodes_dict = nodes

    async def cancel_gen(self, agen: AsyncGenerator) -> None:
        try:
            await agen.aclose()
        except Exception:
            pass

    async def cleanup(self) -> None:
        pass


class Executor(AgentModule, ABC):
    def __init__(self,
                 name: str,
                 type: Optional[ModuleType] = None,
                 config: Optional[ModuleConfig] = None,
                 container: Optional['CompositeModule'] = None,
                 dependencies: Optional[List[str]] = None,
                 executions: Optional[int] = None,
                 input_mailboxes: Optional[List[str]] = None,
                 output_mailbox: Optional[str] = None,
                 trace: Optional[bool] = None):
        super().__init__(name, type, config, container, dependencies, executions, input_mailboxes, output_mailbox, trace)

    @abstractmethod
    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        ...


class FlowControlModule(AgentModule):
    def __init__(self,
                 name: str,
                 type: Optional[ModuleType] = None,
                 config: Optional[ModuleConfig] = None,
                 container: Optional['CompositeModule'] = None,
                 dependencies: Optional[List[str]] = None,
                 executions: Optional[int] = None,
                 input_mailboxes: Optional[List[str]] = None,
                 output_mailbox: Optional[str] = None,
                 trace: Optional[bool] = None,
                 flow_config: Optional[FlowControlConfig] = None):
        super().__init__(name, type, config, container, dependencies, executions, input_mailboxes, output_mailbox, trace)
        self.flow_config = flow_config

    def evaluate_condition(self, condition: str, cache: Cache, cache_keys: Set[str]) -> bool:
        return True

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await super().run(cache, semaphore)


class AgentDirectedFlowControl(FlowControlModule):
    def __init__(self,
                 name: str,
                 type: Optional[ModuleType] = None,
                 config: Optional[ModuleConfig] = None,
                 container: Optional['CompositeModule'] = None,
                 dependencies: Optional[List[str]] = None,
                 executions: Optional[int] = None,
                 input_mailboxes: Optional[List[str]] = None,
                 output_mailbox: Optional[str] = None,
                 trace: Optional[bool] = None,
                 flow_config: Optional[AgentDrivenFlowControlConfig] = None,
                 inference_client: Any = None,
                 input_var: Optional[str] = None,
                 system_description: str = "",
                 use_historicals: Optional[bool] = None,
                 voters: int = 1):
        super().__init__(name, type, config, container, dependencies, executions, input_mailboxes, output_mailbox, trace, flow_config)
        self.inference_client = inference_client
        self.input_var = input_var
        self.system_description = system_description
        self.use_historicals = use_historicals
        self.voters = voters

    def gen(self, generation_input: Any, cache: Cache) -> Any:
        pass

    def most_common_string(self, string_list: List[str]) -> str:
        if not string_list:
            return ""
        from collections import Counter
        return Counter(string_list).most_common(1)[0][0]

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await super().run(cache, semaphore)

    def set_attrs(self) -> None:
        pass


class Agent(AsimovBase):
    def __init__(self,
                 auto_snapshot: bool = False,
                 cache: Optional[Cache] = None,
                 error_mailbox: str = "errors",
                 execution_state: Optional[ExecutionState] = None,
                 graph: Optional[Dict[str, List[str]]] = None,
                 max_concurrent_tasks: Optional[int] = None,
                 max_total_iterations: Optional[int] = None,
                 node_results: Optional[Dict[str, Any]] = None,
                 nodes: Optional[Dict[str, Node]] = None,
                 output_mailbox: str = "output"):
        self.auto_snapshot = auto_snapshot
        self.cache = cache
        self.error_mailbox = error_mailbox
        self.execution_state = execution_state
        self.graph = graph if graph is not None else {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_total_iterations = max_total_iterations
        self.node_results = node_results if node_results is not None else {}
        self.nodes = nodes if nodes is not None else {}
        self.output_mailbox = output_mailbox

    def add_node(self, node: Node) -> None:
        self.nodes[node.name] = node
        if hasattr(node, 'set_nodes'):
            node.set_nodes(self.nodes)
        if not self.graph and node.dependencies:
            for dep in node.dependencies:
                self.graph.setdefault(dep, []).append(node.name)

    def add_multiple_nodes(self, nodes: List[Node]) -> None:
        for node in nodes:
            self.add_node(node)

    def compile_execution_plan(self) -> ExecutionPlan:
        return ExecutionPlan()

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        return ExecutionPlan()

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        if node_name not in self.graph:
            return ()
        chain = [node_name]
        stack = [node_name]
        while stack:
            current = stack.pop()
            for neighbor in self.graph.get(current, []):
                if neighbor not in chain:
                    chain.append(neighbor)
                    stack.append(neighbor)
        return tuple(chain)

    def is_success(self, result: Dict[str, Any]) -> bool:
        return True

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if self.execution_state:
            pass

    def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        pass

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        node = self.nodes.get(node_name)
        if node:
            semaphore = asyncio.Semaphore(self.max_concurrent_tasks or 1)
            return await node.run(self.cache or Cache(), semaphore)
        return {}

    async def run_task(self, task: Task) -> None:
        pass

    def set_semaphore(self) -> asyncio.Semaphore:
        return asyncio.Semaphore(self.max_concurrent_tasks or 1)

    def slice_before_node(self, execution_plan: List[Dict], node: str) -> List[Dict]:
        result = []
        for step in execution_plan:
            result.append(step)
            if step.get("node") == node:
                break
        return result

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        return pathlib.Path(name_hint)

    def update_dependencies(self, parent_node: str, new_node: str) -> None:
        if parent_node not in self.graph:
            self.graph[parent_node] = [new_node]
        elif new_node not in self.graph[parent_node]:
            self.graph[parent_node].append(new_node)