from __future__ import annotations

import asyncio
import inspect
import json
import pathlib
import uuid
from dataclasses import dataclass, field
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
    Union,
    Set,
    Callable,
)


class AsimovBase:
    model_config: Any = None

    def __init__(self, model_config: Any = None) -> None:
        self.model_config = model_config


class Cache:
    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def update(self, mapping: Dict[str, Any]) -> None:
        self._data.update(mapping)

    def keys(self) -> Set[str]:
        return set(self._data.keys())

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)


class ModelFamily:
    def __init__(self, name: str) -> None:
        self.name = name


class ModuleType:
    def __init__(self, name: str) -> None:
        self.name = name


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class Task(AsimovBase):
    def __init__(
        self,
        objective: str,
        type: str,
        params: Optional[Dict[str, Any]] = None,
        id: Optional[uuid.UUID] = None,
        status: Optional[TaskStatus] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(model_config=model_config)
        self.objective: str = objective
        self.type: str = type
        self.params: Optional[Dict[str, Any]] = params
        self.id: Optional[uuid.UUID] = id
        self.status: TaskStatus = status or TaskStatus.PENDING
        self.result: Optional[Any] = result
        self.error: Optional[str] = error

    def update_status(self, status: TaskStatus) -> None:
        self.status = status

    def set_result(self, result: Any) -> None:
        self.result = result

    def set_error(self, error: str) -> None:
        self.error = error


class NonRetryableException(Exception):
    pass


class Middleware(AsimovBase):
    def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        return data


class ModuleConfig(AsimovBase):
    def __init__(
        self,
        context: Optional[Dict[str, Any]] = None,
        middlewares: Optional[List[Middleware]] = None,
        stop_on_success: bool = False,
        timeout: float = 0.0,
        model_config: Any = None,
    ) -> None:
        super().__init__(model_config=model_config)
        self.context: Optional[Dict[str, Any]] = context
        self.middlewares: Optional[List[Middleware]] = middlewares
        self.stop_on_success: bool = stop_on_success
        self.timeout: float = float(timeout)


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
        model_config: Any = None,
    ) -> None:
        super().__init__(model_config=model_config)
        self.condition: Optional[str] = condition
        self.inputs: Optional[List[str]] = inputs
        self.max_retries: int = int(max_retries)
        self.max_visits: Optional[int] = max_visits
        self.outputs: Optional[List[str]] = outputs
        self.parallel: bool = bool(parallel)
        self.retry_from: Optional[str] = retry_from
        self.retry_on_failure: bool = bool(retry_on_failure)


class SnapshotControl:
    def __init__(self, name: str) -> None:
        self.name = name


class AgentModule(AsimovBase):
    def __init__(
        self,
        name: str,
        type: Optional[ModuleType] = None,
        config: Optional[ModuleConfig] = None,
        container: Optional["CompositeModule"] = None,
        dependencies: Optional[List[str]] = None,
        executions: Optional[int] = None,
        input_mailboxes: Optional[List[str]] = None,
        output_mailbox: Optional[str] = None,
        trace: Optional[bool] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(model_config=model_config)
        self.name: str = name
        self.type: Optional[ModuleType] = type
        self.config: Optional[ModuleConfig] = config
        self.container: Optional["CompositeModule"] = container
        self.dependencies: Optional[List[str]] = dependencies
        self.executions: Optional[int] = executions
        self.input_mailboxes: Optional[List[str]] = input_mailboxes
        self.output_mailbox: Optional[str] = output_mailbox
        self.trace: Optional[bool] = trace

    def is_success(self, result: Dict[str, Any]) -> bool:
        if result is None:
            return False
        if isinstance(result, dict) and "success" in result:
            return bool(result.get("success"))
        return True

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Union[Dict[str, Any], AsyncGenerator]:
        raise NotImplementedError

    async def _run_async(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        cfg = self.config or ModuleConfig()
        coro_or_agen = self.process(cache, semaphore)

        async def _await_with_timeout(awaitable: Awaitable[Any]) -> Any:
            if cfg.timeout and cfg.timeout > 0:
                return await asyncio.wait_for(awaitable, timeout=cfg.timeout)
            return await awaitable

        result: Any
        if inspect.isasyncgen(coro_or_agen):
            agen = coro_or_agen  # type: ignore[assignment]
            last: Any = None
            async for item in agen:
                last = item
            result = last if last is not None else {}
        else:
            result = await _await_with_timeout(coro_or_agen)  # type: ignore[arg-type]

        if result is None:
            result = {}
        if not isinstance(result, dict):
            result = {"result": result}

        if cfg.context:
            result = {**cfg.context, **result}

        if cfg.middlewares:
            for mw in cfg.middlewares:
                result = mw.process(result, cache)

        return result

    def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return asyncio.run(self._run_async(cache, semaphore))


class Executor(AgentModule):
    def __init__(
        self,
        name: str,
        type: Optional[ModuleType] = None,
        config: Optional[ModuleConfig] = None,
        container: Optional["CompositeModule"] = None,
        dependencies: Optional[List[str]] = None,
        executions: Optional[int] = None,
        input_mailboxes: Optional[List[str]] = None,
        output_mailbox: Optional[str] = None,
        trace: Optional[bool] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(
            name=name,
            type=type,
            config=config,
            container=container,
            dependencies=dependencies,
            executions=executions,
            input_mailboxes=input_mailboxes,
            output_mailbox=output_mailbox,
            trace=trace,
            model_config=model_config,
        )

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        raise NotImplementedError


class CompositeModule(AgentModule):
    def __init__(
        self,
        name: str,
        modules: Optional[List[AgentModule]] = None,
        node_config: Optional[NodeConfig] = None,
        type: Optional[ModuleType] = None,
        config: Optional[ModuleConfig] = None,
        container: Optional["CompositeModule"] = None,
        dependencies: Optional[List[str]] = None,
        executions: Optional[int] = None,
        input_mailboxes: Optional[List[str]] = None,
        output_mailbox: Optional[str] = None,
        trace: Optional[bool] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(
            name=name,
            type=type,
            config=config,
            container=container,
            dependencies=dependencies,
            executions=executions,
            input_mailboxes=input_mailboxes,
            output_mailbox=output_mailbox,
            trace=trace,
            model_config=model_config,
        )
        self.modules: List[AgentModule] = modules or []
        self.node_config: Optional[NodeConfig] = node_config
        for m in self.modules:
            m.container = self

    def apply_middlewares(
        self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache
    ) -> Dict[str, Any]:
        out = data
        for mw in middlewares:
            out = mw.process(out, cache)
        return out

    async def run_module_with_concurrency_control(
        self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        async with semaphore:
            return await module._run_async(cache, semaphore)

    async def run_parallel_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        tasks = [asyncio.create_task(self.run_module_with_concurrency_control(m, cache, semaphore)) for m in self.modules]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        merged: Dict[str, Any] = {}
        for r in results:
            if isinstance(r, Exception):
                raise r
            if isinstance(r, dict):
                merged.update(r)
        return merged

    async def run_sequential_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        for m in self.modules:
            res = await self.run_module_with_concurrency_control(m, cache, semaphore)
            if isinstance(res, dict):
                merged.update(res)
            if m.config and m.config.stop_on_success and m.is_success(res):
                break
        return merged

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        parallel = bool(self.node_config.parallel) if self.node_config else False
        if parallel:
            return await self.run_parallel_modules(cache, semaphore)
        return await self.run_sequential_modules(cache, semaphore)

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


class Node(CompositeModule):
    def __init__(
        self,
        name: str,
        dependencies: Optional[List[str]] = None,
        modules: Optional[List[AgentModule]] = None,
        node_config: Optional[NodeConfig] = None,
        snapshot: Optional[SnapshotControl] = None,
        type: Optional[ModuleType] = None,
        config: Optional[ModuleConfig] = None,
        container: Optional["CompositeModule"] = None,
        executions: Optional[int] = None,
        input_mailboxes: Optional[List[str]] = None,
        output_mailbox: Optional[str] = None,
        trace: Optional[bool] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(
            name=name,
            modules=modules,
            node_config=node_config,
            type=type,
            config=config,
            container=container,
            dependencies=dependencies,
            executions=executions,
            input_mailboxes=input_mailboxes,
            output_mailbox=output_mailbox,
            trace=trace,
            model_config=model_config,
        )
        self.snapshot: Optional[SnapshotControl] = snapshot
        self._nodes: Optional[Dict[str, "Node"]] = None

    def set_nodes(self, nodes: Dict[str, "Node"]) -> None:
        self._nodes = nodes

    def get_nodes(self) -> Optional[Dict[str, "Node"]]:
        return self._nodes

    def cleanup(self) -> None:
        return

    async def cancel_gen(self, agen: Any) -> None:
        if agen is None:
            return
        aclose = getattr(agen, "aclose", None)
        if callable(aclose):
            await aclose()


@dataclass
class ExecutionStep:
    nodes: List[str]
    executed: List[bool] = field(default_factory=list)
    skipped: List[bool] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.executed:
            self.executed = [False for _ in self.nodes]
        if not self.skipped:
            self.skipped = [False for _ in self.nodes]
        if len(self.executed) != len(self.nodes) or len(self.skipped) != len(self.nodes):
            raise ValueError("ExecutionStep lists must match nodes length")


ExecutionPlan = List[ExecutionStep]


class ExecutionState(AsimovBase):
    def __init__(
        self,
        current_plan: Optional[ExecutionPlan] = None,
        execution_history: Optional[List[ExecutionPlan]] = None,
        execution_index: Optional[int] = None,
        total_iterations: Optional[int] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(model_config=model_config)
        self.current_plan: Optional[ExecutionPlan] = current_plan
        self.execution_history: Optional[List[ExecutionPlan]] = execution_history
        self.execution_index: Optional[int] = execution_index
        self.total_iterations: Optional[int] = total_iterations

    def mark_executed(self, step_index: int, node_index: int) -> None:
        if not self.current_plan:
            raise ValueError("No current_plan set")
        self.current_plan[step_index].executed[node_index] = True

    def was_executed(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan:
            for n, ex in zip(step.nodes, step.executed):
                if n == node_name and ex:
                    return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan:
            for n, sk in zip(step.nodes, step.skipped):
                if n == node_name and sk:
                    return True
        return False


class FlowDecision(AsimovBase):
    def __init__(
        self,
        next_node: str,
        cleanup_on_jump: Optional[bool] = None,
        condition: Optional[str] = None,
        condition_variables: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(model_config=model_config)
        self.next_node: str = next_node
        self.cleanup_on_jump: Optional[bool] = cleanup_on_jump
        self.condition: Optional[str] = condition
        self.condition_variables: Optional[List[str]] = condition_variables
        self.metadata: Optional[Dict[str, Any]] = metadata


class FlowControlConfig(AsimovBase):
    def __init__(
        self,
        decisions: Sequence[FlowDecision],
        default: Optional[str] = None,
        cleanup_on_default: bool = False,
        model_config: Any = None,
    ) -> None:
        super().__init__(model_config=model_config)
        self.decisions: Sequence[FlowDecision] = decisions
        self.default: Optional[str] = default
        self.cleanup_on_default: bool = bool(cleanup_on_default)


class FlowControlModule(AgentModule):
    def __init__(
        self,
        name: str,
        flow_config: FlowControlConfig,
        type: Optional[ModuleType] = None,
        config: Optional[ModuleConfig] = None,
        container: Optional["CompositeModule"] = None,
        dependencies: Optional[List[str]] = None,
        executions: Optional[int] = None,
        input_mailboxes: Optional[List[str]] = None,
        output_mailbox: Optional[str] = None,
        trace: Optional[bool] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(
            name=name,
            type=type,
            config=config,
            container=container,
            dependencies=dependencies,
            executions=executions,
            input_mailboxes=input_mailboxes,
            output_mailbox=output_mailbox,
            trace=trace,
            model_config=model_config,
        )
        self.flow_config = flow_config

    def evaluate_condition(self, condition: str, cache: Cache, cache_keys: Set[str]) -> bool:
        safe_globals: Dict[str, Any] = {"__builtins__": {}}
        safe_locals: Dict[str, Any] = {"cache": cache.to_dict()}
        for k in cache_keys:
            safe_locals[k] = cache.get(k)
        try:
            return bool(eval(condition, safe_globals, safe_locals))
        except Exception:
            return False

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        cache_keys = cache.keys()
        for decision in self.flow_config.decisions:
            if decision.condition:
                if self.evaluate_condition(decision.condition, cache, cache_keys):
                    return {"next_node": decision.next_node, "metadata": decision.metadata}
            else:
                return {"next_node": decision.next_node, "metadata": decision.metadata}

        if self.flow_config.default is not None:
            return {"next_node": self.flow_config.default, "metadata": None}
        return {"next_node": None, "metadata": None}

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


class Example:
    def __init__(
        self,
        choice: str,
        choices: List[Dict[str, str]],
        message: str,
        reasoning: str,
    ) -> None:
        self.choice: str = choice
        self.choices: List[Dict[str, str]] = choices
        self.message: str = message
        self.reasoning: str = reasoning


class AgentDrivenFlowDecision(FlowDecision):
    def __init__(
        self,
        next_node: str,
        cleanup_on_jump: Optional[bool] = None,
        condition: Optional[str] = None,
        condition_variables: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        examples: Optional[List[Example]] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(
            next_node=next_node,
            cleanup_on_jump=cleanup_on_jump,
            condition=condition,
            condition_variables=condition_variables,
            metadata=metadata,
            model_config=model_config,
        )
        self.examples: Optional[List[Example]] = examples


class AgentDrivenFlowControlConfig(FlowControlConfig):
    def __init__(
        self,
        decisions: Sequence[AgentDrivenFlowDecision],
        default: Optional[str] = None,
        cleanup_on_default: bool = False,
        model_config: Any = None,
    ) -> None:
        super().__init__(
            decisions=decisions,
            default=default,
            cleanup_on_default=cleanup_on_default,
            model_config=model_config,
        )


class InferenceClient:
    async def generate(self, system: str, user: str) -> str:
        raise NotImplementedError


class AgentDirectedFlowControl(FlowControlModule):
    def __init__(
        self,
        name: str,
        flow_config: AgentDrivenFlowControlConfig,
        inference_client: InferenceClient,
        system_description: str,
        voters: int,
        input_var: Optional[str] = None,
        use_historicals: Optional[bool] = None,
        type: Optional[ModuleType] = None,
        config: Optional[ModuleConfig] = None,
        container: Optional["CompositeModule"] = None,
        dependencies: Optional[List[str]] = None,
        executions: Optional[int] = None,
        input_mailboxes: Optional[List[str]] = None,
        output_mailbox: Optional[str] = None,
        trace: Optional[bool] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(
            name=name,
            flow_config=flow_config,
            type=type,
            config=config,
            container=container,
            dependencies=dependencies,
            executions=executions,
            input_mailboxes=input_mailboxes,
            output_mailbox=output_mailbox,
            trace=trace,
            model_config=model_config,
        )
        self.flow_config: AgentDrivenFlowControlConfig = flow_config
        self.inference_client: InferenceClient = inference_client
        self.input_var: Optional[str] = input_var
        self.system_description: str = system_description
        self.use_historicals: Optional[bool] = use_historicals
        self.voters: int = int(voters)

    def set_attrs(self) -> None:
        return

    def most_common_string(self, string_list: List[str]) -> Optional[str]:
        if not string_list:
            return None
        counts: Dict[str, int] = {}
        for s in string_list:
            counts[s] = counts.get(s, 0) + 1
        best = max(counts.items(), key=lambda kv: kv[1])[0]
        return best

    async def gen(self, generation_input: str, cache: Cache) -> str:
        system = self.system_description or ""
        user = generation_input
        return await self.inference_client.generate(system=system, user=user)

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        choices = [d.next_node for d in self.flow_config.decisions]
        if self.flow_config.default is not None:
            choices.append(self.flow_config.default)

        input_value = None
        if self.input_var:
            input_value = cache.get(self.input_var)
        generation_input = json.dumps(
            {
                "input_var": self.input_var,
                "input_value": input_value,
                "choices": choices,
            },
            default=str,
        )

        votes: List[str] = []
        for _ in range(max(1, self.voters)):
            async with semaphore:
                out = await self.gen(generation_input, cache)
            out_str = str(out).strip()
            votes.append(out_str)

        selected = self.most_common_string(votes)
        if selected not in choices:
            selected = self.flow_config.default

        return {"next_node": selected, "votes": votes}

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


class Agent(AsimovBase):
    def __init__(
        self,
        output_mailbox: str,
        error_mailbox: str,
        auto_snapshot: bool = False,
        cache: Optional[Cache] = None,
        execution_state: Optional[ExecutionState] = None,
        graph: Optional[Dict[str, List[str]]] = None,
        max_concurrent_tasks: Optional[int] = None,
        max_total_iterations: Optional[int] = None,
        node_results: Optional[Dict[str, Any]] = None,
        nodes: Optional[Dict[str, Node]] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(model_config=model_config)
        self.auto_snapshot: bool = bool(auto_snapshot)
        self.cache: Optional[Cache] = cache
        self.error_mailbox: str = error_mailbox
        self.execution_state: Optional[ExecutionState] = execution_state
        self.graph: Optional[Dict[str, List[str]]] = graph
        self.max_concurrent_tasks: Optional[int] = max_concurrent_tasks
        self.max_total_iterations: Optional[int] = max_total_iterations
        self.node_results: Optional[Dict[str, Any]] = node_results
        self.nodes: Optional[Dict[str, Node]] = nodes
        self.output_mailbox: str = output_mailbox
        self._semaphore: Optional[asyncio.Semaphore] = None

        if self.cache is None:
            self.cache = Cache()
        if self.nodes is None:
            self.nodes = {}
        if self.graph is None:
            self.graph = {}
        if self.node_results is None:
            self.node_results = {}
        if self.execution_state is None:
            self.execution_state = ExecutionState(
                current_plan=None,
                execution_history=[],
                execution_index=0,
                total_iterations=0,
            )

    def set_semaphore(self) -> None:
        limit = self.max_concurrent_tasks if self.max_concurrent_tasks is not None else 1
        if limit <= 0:
            limit = 1
        self._semaphore = asyncio.Semaphore(limit)

    def add_node(self, node: Node) -> None:
        if self.nodes is None:
            self.nodes = {}
        if self.graph is None:
            self.graph = {}
        self.nodes[node.name] = node
        node.set_nodes(self.nodes)
        if node.name not in self.graph:
            self.graph[node.name] = []
        if node.dependencies:
            for dep in node.dependencies:
                self.update_dependencies(dep, node.name)

    def add_multiple_nodes(self, nodes: List[Node]) -> None:
        for n in nodes:
            self.add_node(n)

    def update_dependencies(self, parent_node: str, new_node: str) -> None:
        if self.graph is None:
            self.graph = {}
        self.graph.setdefault(parent_node, [])
        if new_node not in self.graph[parent_node]:
            self.graph[parent_node].append(new_node)
        self.graph.setdefault(new_node, [])

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        if not self.graph:
            return tuple()
        visited: Set[str] = set()
        order: List[str] = []

        def dfs(n: str) -> None:
            for child in self.graph.get(n, []):
                if child in visited:
                    continue
                visited.add(child)
                order.append(child)
                dfs(child)

        dfs(node_name)
        return tuple(order)

    def compile_execution_plan(self) -> ExecutionPlan:
        if not self.nodes:
            return []
        indeg: Dict[str, int] = {n: 0 for n in self.nodes.keys()}
        for n, node in self.nodes.items():
            if node.dependencies:
                for dep in node.dependencies:
                    if dep in indeg:
                        indeg[n] += 1
                    else:
                        indeg.setdefault(dep, 0)
                        indeg[n] += 1

        remaining = set(indeg.keys())
        plan: ExecutionPlan = []
        while remaining:
            ready = sorted([n for n in remaining if indeg.get(n, 0) == 0])
            if not ready:
                ready = sorted(list(remaining))
            plan.append(ExecutionStep(nodes=ready))
            for r in ready:
                remaining.discard(r)
                for child in (self.graph or {}).get(r, []):
                    if child in indeg:
                        indeg[child] = max(0, indeg[child] - 1)
        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        full = self.compile_execution_plan()
        if not full:
            return []
        included: Set[str] = set([start_node])
        if self.nodes and start_node in self.nodes:
            deps = self.nodes[start_node].dependencies or []
            included.update(deps)
        included.update(self.get_dependent_chains(start_node))

        sliced: ExecutionPlan = []
        for step in full:
            nodes = [n for n in step.nodes if n in included]
            if nodes:
                sliced.append(ExecutionStep(nodes=nodes))
        return sliced

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        out: List[dict] = []
        for step in execution_plan:
            nodes = step.get("nodes", [])
            if node in nodes:
                break
            out.append(step)
        return out

    def is_success(self, result: Any) -> bool:
        if result is None:
            return False
        if isinstance(result, dict) and "success" in result:
            return bool(result.get("success"))
        return True

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if not self.execution_state or not self.execution_state.current_plan:
            return
        to_skip = {node_name}
        to_skip.update(self.get_dependent_chains(node_name))
        for step in self.execution_state.current_plan:
            for i, n in enumerate(step.nodes):
                if n in to_skip:
                    step.skipped[i] = True

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        base = pathlib.Path.cwd() / "snapshots"
        base.mkdir(parents=True, exist_ok=True)
        snap_dir = base / f"{name_hint}_{task.id or uuid.uuid4()}"
        snap_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "task": {
                "id": str(task.id) if task.id else None,
                "objective": task.objective,
                "type": task.type,
                "params": task.params,
                "status": task.status.value if isinstance(task.status, TaskStatus) else str(task.status),
                "result": task.result,
                "error": task.error,
            },
            "cache": self.cache.to_dict() if self.cache else {},
            "node_results": self.node_results or {},
        }
        (snap_dir / "snapshot.json").write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")
        return snap_dir

    def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        data = json.loads((snapshot_dir / "snapshot.json").read_text(encoding="utf-8"))
        if self.cache is None:
            self.cache = Cache()
        self.cache.update(data.get("cache", {}))
        if self.node_results is None:
            self.node_results = {}
        self.node_results.update(data.get("node_results", {}))

    def run_node(self, node_name: str) -> Dict[str, Any]:
        if not self.nodes or node_name not in self.nodes:
            raise KeyError(f"Unknown node: {node_name}")
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()
        semaphore = self._semaphore or asyncio.Semaphore(1)
        node = self.nodes[node_name]
        result = asyncio.run(node.run(self.cache, semaphore))
        if self.node_results is None:
            self.node_results = {}
        self.node_results[node_name] = result
        if self.cache is not None and isinstance(result, dict):
            self.cache.update(result)
        return result

    def run_task(self, task: Task) -> None:
        if task.id is None:
            task.id = uuid.uuid4()
        if self.cache is None:
            self.cache = Cache()
        if self.execution_state is None:
            self.execution_state = ExecutionState(current_plan=None, execution_history=[], execution_index=0, total_iterations=0)
        if self._semaphore is None:
            self.set_semaphore()

        task.update_status(TaskStatus.RUNNING)

        try:
            plan = self.compile_execution_plan()
            self.execution_state.current_plan = plan
            if self.execution_state.execution_history is None:
                self.execution_state.execution_history = []
            self.execution_state.execution_history.append(plan)
            self.execution_state.execution_index = 0
            if self.execution_state.total_iterations is None:
                self.execution_state.total_iterations = 0

            total_iters = 0
            for si, step in enumerate(plan):
                for ni, node_name in enumerate(step.nodes):
                    if step.skipped[ni]:
                        continue
                    if self.max_total_iterations is not None and total_iters >= self.max_total_iterations:
                        raise RuntimeError("max_total_iterations exceeded")
                    total_iters += 1
                    self.execution_state.total_iterations = total_iters

                    node = self.nodes.get(node_name) if self.nodes else None
                    if node is None:
                        raise KeyError(f"Unknown node: {node_name}")

                    if node.node_config and node.node_config.condition:
                        cond_ok = FlowControlModule(
                            name="_cond_eval",
                            flow_config=FlowControlConfig(decisions=[]),
                        ).evaluate_condition(node.node_config.condition, self.cache, self.cache.keys())
                        if not cond_ok:
                            step.skipped[ni] = True
                            continue

                    max_visits = node.node_config.max_visits if node.node_config else None
                    visits = 0
                    retries = 0
                    max_retries = node.node_config.max_retries if node.node_config else 0
                    retry_on_failure = bool(node.node_config.retry_on_failure) if node.node_config else False

                    while True:
                        if max_visits is not None and visits >= max_visits:
                            raise RuntimeError(f"max_visits exceeded for node {node_name}")
                        visits += 1
                        try:
                            res = self.run_node(node_name)
                            self.execution_state.mark_executed(si, ni)
                            if self.auto_snapshot:
                                self.snapshot(task, f"node_{node_name}")
                            break
                        except NonRetryableException:
                            raise
                        except Exception as e:
                            if not retry_on_failure or retries >= max_retries:
                                raise
                            retries += 1
                            continue

            task.set_result(self.node_results)
            task.update_status(TaskStatus.SUCCESS)
        except Exception as e:
            task.set_error(str(e))
            task.update_status(TaskStatus.FAILED)