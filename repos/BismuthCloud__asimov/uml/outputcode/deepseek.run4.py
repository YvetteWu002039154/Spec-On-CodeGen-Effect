import asyncio
import pathlib
import uuid
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
    Union,
)

# ---------------------------------------------------------------------------
# Base / utility stubs for types referenced but not defined in the diagram
# ---------------------------------------------------------------------------

class Cache:
    """Simplified stub for a cache used across the system."""
    def __init__(self):
        self.data: Dict[str, Any] = {}
    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)
    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

class InferenceClient:
    """Stub for an LLM inference client."""
    pass

class ExecutionPlan:
    def __init__(self, steps: List['ExecutionStep']):
        self.steps = steps

class BaseModel:
    """Stub for a Pydantic-like base."""
    pass

# ---------------------------------------------------------------------------
# Core classes from the diagram
# ---------------------------------------------------------------------------

class AsimovBase:
    model_config: dict = {}

class Agent(AsimovBase):
    def __init__(self):
        self.auto_snapshot: bool = False
        self.cache: Optional[Cache] = None
        self.error_mailbox: str = ""
        self.execution_state: Optional[ExecutionState] = None
        self.graph: Optional[Dict[str, List[str]]] = None
        self.max_concurrent_tasks: Optional[int] = None
        self.max_total_iterations: Optional[int] = None
        self.node_results: Optional[Dict[str, Any]] = None
        self.nodes: Optional[Dict[str, 'Node']] = None
        self.output_mailbox: str = ""

    def add_multiple_nodes(self, nodes: List['Node']):
        for node in nodes:
            self.add_node(node)

    def add_node(self, node: 'Node'):
        if self.nodes is None:
            self.nodes = {}
        self.nodes[node.name] = node
        if self.graph is None:
            self.graph = {}
        self.graph[node.name] = node.dependencies or []

    def compile_execution_plan(self) -> ExecutionPlan:
        return ExecutionPlan(steps=[])

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        return ExecutionPlan(steps=[])

    def get_dependent_chains(self, node_name: str) -> tuple:
        return ()

    def is_success(self, result: Any) -> bool:
        return True

    def mark_node_and_deps_as_skipped(self, node_name: str):
        pass

    def run_from_snapshot(self, snapshot_dir: pathlib.Path):
        pass

    def run_node(self, node_name: str) -> Dict[str, Any]:
        return {}

    def run_task(self, task: 'Task') -> None:
        pass

    def set_semaphore(self):
        pass

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        return execution_plan

    def snapshot(self, task: 'Task', name_hint: str) -> pathlib.Path:
        return pathlib.Path(".")

    def update_dependencies(self, parent_node: str, new_node: str):
        if self.graph is not None and parent_node in self.graph:
            self.graph[parent_node].append(new_node)


class AgentModule(AsimovBase):
    def __init__(self, name: str = "", config: Optional['ModuleConfig'] = None,
                 container: Optional['CompositeModule'] = None,
                 dependencies: Optional[List[str]] = None,
                 executions: Optional[int] = None,
                 input_mailboxes: Optional[List[str]] = None,
                 output_mailbox: Optional[str] = None,
                 trace: Optional[bool] = None,
                 type: Optional['ModuleType'] = None):
        self.config = config
        self.container = container
        self.dependencies = dependencies
        self.executions = executions
        self.input_mailboxes = input_mailboxes
        self.name = name
        self.output_mailbox = output_mailbox
        self.trace = trace
        self.type = type

    def is_success(self, result: Dict[str, Any]) -> bool:
        return True

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Union[Dict[str, Any], AsyncGenerator]:
        return {}

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await self.process(cache, semaphore)


class CompositeModule(AgentModule):
    def __init__(self, modules: Optional[List[AgentModule]] = None, node_config: Optional['NodeConfig'] = None, **kwargs):
        super().__init__(**kwargs)
        self.modules = modules if modules is not None else []
        self.node_config = node_config

    def apply_middlewares(self, middlewares: List['Middleware'], data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        for mw in middlewares:
            data = mw.process(data, cache)
        return data

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            return await self.run_parallel_modules(cache, semaphore)
        else:
            return await self.run_sequential_modules(cache, semaphore)

    async def run_module_with_concurrency_control(self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await module.run(cache, semaphore)

    async def run_parallel_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        tasks = [self.run_module_with_concurrency_control(m, cache, semaphore) for m in self.modules]
        results = await asyncio.gather(*tasks)
        return {"results": results}

    async def run_sequential_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        final = {}
        for module in self.modules:
            final = await self.run_module_with_concurrency_control(module, cache, semaphore)
        return final


class Node(CompositeModule):
    def __init__(self,
                 dependencies: Optional[List[str]] = None,
                 modules: Optional[List[AgentModule]] = None,
                 node_config: Optional['NodeConfig'] = None,
                 snapshot: Optional['SnapshotControl'] = None,
                 type: Optional['ModuleType'] = None,
                 **kwargs):
        super().__init__(modules=modules, node_config=node_config, **kwargs)
        self.dependencies = dependencies
        self.snapshot = snapshot
        self.type = type
        self._nodes: Optional[Dict[str, 'Node']] = None

    def cancel_gen(self, agen):
        pass

    def cleanup(self):
        pass

    def get_nodes(self) -> Optional[Dict[str, 'Node']]:
        return self._nodes

    def set_nodes(self, nodes: Dict[str, 'Node']):
        self._nodes = nodes


class ExecutionState(AsimovBase):
    def __init__(self):
        self.current_plan: Optional[ExecutionPlan] = None
        self.execution_history: Optional[List[ExecutionPlan]] = None
        self.execution_index: Optional[int] = None
        self.total_iterations: Optional[int] = None

    def mark_executed(self, step_index: int, node_index: int):
        if self.current_plan and self.current_plan.steps:
            step = self.current_plan.steps[step_index]
            step.executed[node_index] = True

    def was_executed(self, node_name: str) -> bool:
        # Minimal implementation
        return False

    def was_skipped(self, node_name: str) -> bool:
        return False


class ExecutionStep:
    def __init__(self, nodes: List[str]):
        self.executed: List[bool] = [False] * len(nodes)
        self.nodes: List[str] = nodes
        self.skipped: List[bool] = [False] * len(nodes)


class Middleware(AsimovBase):
    def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        return data


class ModuleConfig(AsimovBase):
    def __init__(self, context: Optional[Dict[str, Any]] = None,
                 middlewares: Optional[List[Middleware]] = None,
                 stop_on_success: bool = False,
                 timeout: float = 60.0):
        self.context = context
        self.middlewares = middlewares
        self.stop_on_success = stop_on_success
        self.timeout = timeout


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


class SnapshotControl:
    def __init__(self, name: str = ""):
        self.name = name


class ModuleType:
    def __init__(self, name: str = ""):
        self.name = name


class ModelFamily:
    def __init__(self, name: str = ""):
        self.name = name


class NonRetryableException(Exception):
    """Exception that should not trigger retry."""
    pass


class Task(AsimovBase):
    def __init__(self,
                 error: Optional[str] = None,
                 id: Optional[uuid.UUID] = None,
                 objective: str = "",
                 params: Optional[Dict[str, Any]] = None,
                 result: Optional[Any] = None,
                 status: Optional['TaskStatus'] = None,
                 type: str = ""):
        self.error = error
        self.id = id or uuid.uuid4()
        self.objective = objective
        self.params = params
        self.result = result
        self.status = status or TaskStatus.PENDING
        self.type = type

    def set_error(self, error: str) -> None:
        self.error = error
        self.status = TaskStatus.FAILED

    def set_result(self, result: Any) -> None:
        self.result = result
        self.status = TaskStatus.COMPLETED

    def update_status(self, status: 'TaskStatus') -> None:
        self.status = status


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FlowControlConfig(AsimovBase):
    def __init__(self,
                 cleanup_on_default: bool = False,
                 decisions: Sequence['FlowDecision'] = (),
                 default: Optional[str] = None):
        self.cleanup_on_default = cleanup_on_default
        self.decisions = decisions
        self.default = default


class FlowDecision(AsimovBase):
    def __init__(self,
                 cleanup_on_jump: Optional[bool] = None,
                 condition: Optional[str] = None,
                 condition_variables: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 next_node: str = ""):
        self.cleanup_on_jump = cleanup_on_jump
        self.condition = condition
        self.condition_variables = condition_variables
        self.metadata = metadata
        self.next_node = next_node


class FlowControlModule(AgentModule):
    def __init__(self, flow_config: FlowControlConfig, **kwargs):
        super().__init__(**kwargs)
        self.flow_config = flow_config

    def evaluate_condition(self, condition: str, cache: Cache, cache_keys: set) -> bool:
        return True

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}


class AgentDrivenFlowDecision(FlowDecision):
    def __init__(self, examples: Optional[List['Example']] = None, **kwargs):
        super().__init__(**kwargs)
        self.examples = examples


class AgentDrivenFlowControlConfig(FlowControlConfig):
    def __init__(self,
                 decisions: Sequence[AgentDrivenFlowDecision] = (),
                 default: Optional[str] = None,
                 **kwargs):
        super().__init__(decisions=decisions, default=default, **kwargs)


class AgentDirectedFlowControl(FlowControlModule):
    def __init__(self,
                 flow_config: AgentDrivenFlowControlConfig,
                 inference_client: InferenceClient,
                 input_var: Optional[str] = None,
                 system_description: str = "",
                 use_historicals: Optional[bool] = None,
                 voters: int = 1,
                 **kwargs):
        super().__init__(flow_config=flow_config, **kwargs)
        self.inference_client = inference_client
        self.input_var = input_var
        self.system_description = system_description
        self.use_historicals = use_historicals
        self.voters = voters

    def gen(self, generation_input, cache):
        """Yield or return generation results (placeholder)."""
        return {}

    def most_common_string(self, string_list: List[str]) -> str:
        if not string_list:
            return ""
        return max(set(string_list), key=string_list.count)

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return {}

    def set_attrs(self):
        pass


class Example:
    def __init__(self,
                 choice: str = "",
                 choices: Optional[List[Dict[str, str]]] = None,
                 message: str = "",
                 reasoning: str = ""):
        self.choice = choice
        self.choices = choices
        self.message = message
        self.reasoning = reasoning


# ---------------------------------------------------------------------------
# Executor (abstract)
# ---------------------------------------------------------------------------

class Executor(AgentModule):
    def __init__(self, type: Optional[ModuleType] = None, **kwargs):
        super().__init__(**kwargs)
        self.type = type

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement process")