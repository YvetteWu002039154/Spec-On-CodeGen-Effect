from __future__ import annotations

import asyncio
import inspect
import json
import pathlib
import uuid
from collections import Counter
from dataclasses import dataclass
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
    Union,
    Iterable,
)


class AsimovBase:
    model_config: Any

    def __init__(self, model_config: Any = None) -> None:
        self.model_config = model_config


class Cache:
    def __init__(self, initial: Optional[Dict[str, Any]] = None) -> None:
        self._data: Dict[str, Any] = dict(initial or {})

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def delete(self, key: str) -> None:
        if key in self._data:
            del self._data[key]

    def keys(self) -> Set[str]:
        return set(self._data.keys())

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    def update(self, data: Dict[str, Any]) -> None:
        self._data.update(data)


class ModelFamily:
    def __init__(self, name: str) -> None:
        self.name = name


class ModuleType:
    def __init__(self, name: str) -> None:
        self.name = name


class TaskStatus(Enum):
    name = "name"
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
        self.id: Optional[uuid.UUID] = id or uuid.uuid4()
        self.status: TaskStatus = status or TaskStatus.PENDING
        self.result: Optional[Any] = result
        self.error: Optional[str] = error

    def set_error(self, error: str) -> None:
        self.error = error

    def set_result(self, result: Any) -> None:
        self.result = result

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


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

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        async with semaphore:
            if self.executions is not None and self.executions <= 0:
                return {"success": True, "skipped": True, "module": self.name}

            async def _call_process() -> Any:
                return await self.process(cache, semaphore)

            timeout = 0.0
            if self.config is not None:
                timeout = float(self.config.timeout or 0.0)

            try:
                if timeout and timeout > 0:
                    out = await asyncio.wait_for(_call_process(), timeout=timeout)
                else:
                    out = await _call_process()
            except asyncio.TimeoutError as e:
                raise e

            if inspect.isasyncgen(out):
                last: Any = None
                async for item in out:
                    last = item
                out = last

            if out is None:
                out = {}

            if not isinstance(out, dict):
                out = {"result": out}

            if self.config and self.config.middlewares:
                for mw in self.config.middlewares:
                    out = mw.process(out, cache)

            if self.executions is not None:
                self.executions -= 1

            return out


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
        self.modules: List[AgentModule] = list(modules or [])
        self.node_config: Optional[NodeConfig] = node_config
        for m in self.modules:
            m.container = self

    def apply_middlewares(
        self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache
    ) -> Dict[str, Any]:
        out = dict(data)
        for mw in middlewares:
            out = mw.process(out, cache)
        return out

    async def run_module_with_concurrency_control(
        self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await module.run(cache, semaphore)

    async def run_parallel_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        tasks = [asyncio.create_task(self.run_module_with_concurrency_control(m, cache, semaphore)) for m in self.modules]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out: Dict[str, Any] = {"modules": {}}
        for m, r in zip(self.modules, results):
            if isinstance(r, Exception):
                raise r
            out["modules"][m.name] = r
            if m.output_mailbox:
                cache.set(m.output_mailbox, r)
        return out

    async def run_sequential_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        out: Dict[str, Any] = {"modules": {}}
        for m in self.modules:
            r = await self.run_module_with_concurrency_control(m, cache, semaphore)
            out["modules"][m.name] = r
            if m.output_mailbox:
                cache.set(m.output_mailbox, r)
            if m.config and m.config.stop_on_success and m.is_success(r):
                break
        return out

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        parallel = False
        if self.node_config is not None:
            parallel = bool(self.node_config.parallel)
        if parallel:
            return await self.run_parallel_modules(cache, semaphore)
        return await self.run_sequential_modules(cache, semaphore)

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Union[Dict[str, Any], AsyncGenerator]:
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
        self.dependencies: Optional[List[str]] = dependencies
        self.snapshot: Optional[SnapshotControl] = snapshot
        self._nodes: Optional[Dict[str, "Node"]] = None

    def set_nodes(self, nodes: Dict[str, "Node"]) -> None:
        self._nodes = nodes

    def get_nodes(self) -> Optional[Dict[str, "Node"]]:
        return self._nodes

    async def cancel_gen(self, agen: Any) -> None:
        if agen is None:
            return
        aclose = getattr(agen, "aclose", None)
        if callable(aclose):
            await aclose()

    def cleanup(self) -> None:
        return


@dataclass
class ExecutionStep:
    nodes: List[str]
    executed: List[bool]
    skipped: List[bool]


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
        if self.current_plan is None:
            return
        if step_index < 0 or step_index >= len(self.current_plan):
            return
        step = self.current_plan[step_index]
        if node_index < 0 or node_index >= len(step.nodes):
            return
        step.executed[node_index] = True

    def was_executed(self, node_name: str) -> bool:
        if self.current_plan is None:
            return False
        for step in self.current_plan:
            for n, ex in zip(step.nodes, step.executed):
                if n == node_name and ex:
                    return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if self.current_plan is None:
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
        safe_locals: Dict[str, Any] = {"cache": cache.to_dict(), "keys": cache_keys}
        try:
            return bool(eval(condition, safe_globals, safe_locals))
        except Exception:
            return False

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        cache_keys = cache.keys()
        chosen: Optional[str] = None
        chosen_decision: Optional[FlowDecision] = None

        for d in self.flow_config.decisions:
            if d.condition is None:
                continue
            if self.evaluate_condition(d.condition, cache, cache_keys):
                chosen = d.next_node
                chosen_decision = d
                break

        if chosen is None:
            chosen = self.flow_config.default
            if chosen is None:
                return {"success": False, "next_node": None}
            if self.flow_config.cleanup_on_default:
                if self.container is not None:
                    self.container.modules = []
        else:
            if chosen_decision is not None and chosen_decision.cleanup_on_jump:
                if self.container is not None:
                    self.container.modules = []

        return {"success": True, "next_node": chosen}

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Union[Dict[str, Any], AsyncGenerator]:
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
        examples: Optional[List[Example]] = None,
        cleanup_on_jump: Optional[bool] = None,
        condition: Optional[str] = None,
        condition_variables: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
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
        self.decisions: Sequence[AgentDrivenFlowDecision] = decisions


class InferenceClient:
    async def generate(self, system: str, user: str) -> str:
        return ""


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

    async def gen(self, generation_input: Any, cache: Cache) -> str:
        system = self.system_description or ""
        user = json.dumps(generation_input, ensure_ascii=False, default=str)
        return await self.inference_client.generate(system=system, user=user)

    def most_common_string(self, string_list: Iterable[str]) -> Optional[str]:
        items = [s for s in string_list if isinstance(s, str)]
        if not items:
            return None
        return Counter(items).most_common(1)[0][0]

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        async with semaphore:
            choices = [d.next_node for d in self.flow_config.decisions]
            payload: Dict[str, Any] = {
                "choices": choices,
                "default": self.flow_config.default,
            }
            if self.input_var:
                payload["input"] = cache.get(self.input_var)
            else:
                payload["input"] = cache.to_dict()

            votes: List[str] = []
            for _ in range(max(1, self.voters)):
                out = await self.gen(payload, cache)
                votes.append(out)

            chosen = self.most_common_string(votes)
            if chosen not in choices:
                chosen = self.flow_config.default

            if chosen is None:
                return {"success": False, "next_node": None, "votes": votes}

            return {"success": True, "next_node": chosen, "votes": votes}

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Union[Dict[str, Any], AsyncGenerator]:
        return await self.run(cache, semaphore)


class Agent(AsimovBase):
    def __init__(
        self,
        auto_snapshot: bool = False,
        cache: Optional[Cache] = None,
        error_mailbox: str = "errors",
        execution_state: Optional[ExecutionState] = None,
        graph: Optional[Dict[str, List[str]]] = None,
        max_concurrent_tasks: Optional[int] = None,
        max_total_iterations: Optional[int] = None,
        node_results: Optional[Dict[str, Any]] = None,
        nodes: Optional[Dict[str, Node]] = None,
        output_mailbox: str = "output",
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
            self.execution_state = ExecutionState(current_plan=None, execution_history=[], execution_index=0, total_iterations=0)

        for n in self.nodes.values():
            n.set_nodes(self.nodes)

    def set_semaphore(self) -> None:
        limit = self.max_concurrent_tasks if self.max_concurrent_tasks is not None else 1
        if limit <= 0:
            limit = 1
        self._semaphore = asyncio.Semaphore(limit)

    def add_node(self, node: Node) -> None:
        if self.nodes is None:
            self.nodes = {}
        self.nodes[node.name] = node
        node.set_nodes(self.nodes)
        if self.graph is None:
            self.graph = {}
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
        if self.graph is None:
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

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if self.execution_state is None or self.execution_state.current_plan is None:
            return
        to_skip = {node_name, *self.get_dependent_chains(node_name)}
        for step in self.execution_state.current_plan:
            for i, n in enumerate(step.nodes):
                if n in to_skip:
                    step.skipped[i] = True

    def is_success(self, result: Any) -> bool:
        if result is None:
            return False
        if isinstance(result, dict) and "success" in result:
            return bool(result.get("success"))
        return True

    def _topological_plan(self, start_nodes: List[str]) -> ExecutionPlan:
        if self.nodes is None:
            return []
        deps: Dict[str, Set[str]] = {}
        for name, node in self.nodes.items():
            deps[name] = set(node.dependencies or [])

        included: Set[str] = set()

        def include_with_deps(n: str) -> None:
            if n in included:
                return
            included.add(n)
            for d in deps.get(n, set()):
                include_with_deps(d)

        for s in start_nodes:
            include_with_deps(s)

        indeg: Dict[str, int] = {}
        children: Dict[str, Set[str]] = {n: set() for n in included}
        for n in included:
            indeg[n] = 0
        for n in included:
            for d in deps.get(n, set()):
                if d in included:
                    children.setdefault(d, set()).add(n)
                    indeg[n] += 1

        layers: List[List[str]] = []
        ready = sorted([n for n in included if indeg.get(n, 0) == 0])
        while ready:
            layer = ready
            layers.append(layer)
            next_ready: List[str] = []
            for n in layer:
                for ch in sorted(children.get(n, set())):
                    indeg[ch] -= 1
                    if indeg[ch] == 0:
                        next_ready.append(ch)
            ready = sorted(next_ready)

        planned = [n for layer in layers for n in layer]
        if len(planned) != len(included):
            remaining = sorted(list(included - set(planned)))
            for r in remaining:
                layers.append([r])

        plan: ExecutionPlan = []
        for layer in layers:
            plan.append(ExecutionStep(nodes=list(layer), executed=[False] * len(layer), skipped=[False] * len(layer)))
        return plan

    def compile_execution_plan(self) -> ExecutionPlan:
        if self.nodes is None:
            return []
        all_nodes = list(self.nodes.keys())
        plan = self._topological_plan(all_nodes)
        if self.execution_state is not None:
            self.execution_state.current_plan = plan
            if self.execution_state.execution_history is None:
                self.execution_state.execution_history = []
            self.execution_state.execution_history.append(plan)
        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        plan = self._topological_plan([start_node])
        if self.execution_state is not None:
            self.execution_state.current_plan = plan
            if self.execution_state.execution_history is None:
                self.execution_state.execution_history = []
            self.execution_state.execution_history.append(plan)
        return plan

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        out: List[dict] = []
        for step in execution_plan:
            nodes = step.get("nodes", [])
            if node in nodes:
                break
            out.append(step)
        return out

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        base = pathlib.Path.cwd() / "snapshots"
        base.mkdir(parents=True, exist_ok=True)
        snap_dir = base / f"{name_hint}_{task.id}"
        snap_dir.mkdir(parents=True, exist_ok=True)

        cache_path = snap_dir / "cache.json"
        task_path = snap_dir / "task.json"
        results_path = snap_dir / "node_results.json"

        cache_data = self.cache.to_dict() if self.cache is not None else {}
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, default=str)

        with task_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "id": str(task.id) if task.id else None,
                    "objective": task.objective,
                    "type": task.type,
                    "params": task.params,
                    "status": task.status.value if isinstance(task.status, TaskStatus) else str(task.status),
                    "result": task.result,
                    "error": task.error,
                },
                f,
                ensure_ascii=False,
                default=str,
            )

        with results_path.open("w", encoding="utf-8") as f:
            json.dump(self.node_results or {}, f, ensure_ascii=False, default=str)

        return snap_dir

    def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        cache_path = snapshot_dir / "cache.json"
        results_path = snapshot_dir / "node_results.json"
        if cache_path.exists():
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if self.cache is None:
                self.cache = Cache(data)
            else:
                self.cache.update(data)
        if results_path.exists():
            with results_path.open("r", encoding="utf-8") as f:
                self.node_results = json.load(f)

    async def run_task(self, task: Task) -> None:
        if self.cache is None:
            self.cache = Cache()
        if self.node_results is None:
            self.node_results = {}
        if self.execution_state is None:
            self.execution_state = ExecutionState(current_plan=None, execution_history=[], execution_index=0, total_iterations=0)

        self.set_semaphore()
        semaphore = self._semaphore or asyncio.Semaphore(1)

        task.update_status(TaskStatus.RUNNING)
        self.cache.set("task", {"id": str(task.id), "objective": task.objective, "type": task.type, "params": task.params})

        plan = self.compile_execution_plan()
        total_iterations = 0
        if self.execution_state.total_iterations is None:
            self.execution_state.total_iterations = 0

        try:
            for step_index, step in enumerate(plan):
                for node_index, node_name in enumerate(step.nodes):
                    if step.skipped[node_index]:
                        self.execution_state.mark_executed(step_index, node_index)
                        continue

                    if self.max_total_iterations is not None and total_iterations >= self.max_total_iterations:
                        raise NonRetryableException("Maximum total iterations exceeded")

                    res = await self.run_node(node_name)
                    self.node_results[node_name] = res
                    self.execution_state.mark_executed(step_index, node_index)

                    total_iterations += 1
                    self.execution_state.total_iterations = (self.execution_state.total_iterations or 0) + 1

                    if self.auto_snapshot:
                        self.snapshot(task, f"after_{node_name}")

            self.cache.set(self.output_mailbox, self.node_results)
            task.set_result(self.node_results)
            task.update_status(TaskStatus.SUCCESS)
        except Exception as e:
            task.set_error(str(e))
            task.update_status(TaskStatus.FAILED)
            self.cache.set(self.error_mailbox, {"error": str(e), "task_id": str(task.id)})
            raise

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if self.nodes is None or node_name not in self.nodes:
            raise KeyError(f"Node not found: {node_name}")
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()
        semaphore = self._semaphore or asyncio.Semaphore(1)

        node = self.nodes[node_name]
        node.set_nodes(self.nodes)

        if node.node_config and node.node_config.condition:
            cond = node.node_config.condition
            ok = FlowControlModule(name="_cond", flow_config=FlowControlConfig(decisions=[])).evaluate_condition(
                cond, self.cache, self.cache.keys()
            )
            if not ok:
                self.mark_node_and_deps_as_skipped(node_name)
                return {"success": True, "skipped": True, "node": node_name}

        max_visits = node.node_config.max_visits if node.node_config else None
        visit_key = f"__visits__:{node_name}"
        visits = int(self.cache.get(visit_key, 0))
        if max_visits is not None and visits >= max_visits:
            raise NonRetryableException(f"Max visits exceeded for node {node_name}")
        self.cache.set(visit_key, visits + 1)

        retries = node.node_config.max_retries if node.node_config else 0
        retry_on_failure = bool(node.node_config.retry_on_failure) if node.node_config else False

        attempt = 0
        last_exc: Optional[BaseException] = None
        while True:
            try:
                result = await node.run(self.cache, semaphore)
                if node.output_mailbox:
                    self.cache.set(node.output_mailbox, result)
                return result
            except NonRetryableException:
                raise
            except Exception as e:
                last_exc = e
                attempt += 1
                if not retry_on_failure or attempt > retries:
                    raise
                continue

        if last_exc is not None:
            raise last_exc
        return {"success": False, "node": node_name}