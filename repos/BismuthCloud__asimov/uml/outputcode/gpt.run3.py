from __future__ import annotations

import asyncio
import inspect
import json
import pathlib
import shutil
import time
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
    Tuple,
    Union,
    Set,
)
from uuid import UUID, uuid4


class AsimovBase:
    model_config: Any

    def __init__(self, model_config: Any = None) -> None:
        self.model_config = model_config


class Cache(AsimovBase):
    def __init__(self, initial: Optional[Dict[str, Any]] = None, model_config: Any = None) -> None:
        super().__init__(model_config=model_config)
        self._data: Dict[str, Any] = dict(initial or {})

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def update(self, data: Dict[str, Any]) -> None:
        self._data.update(data)

    def keys(self) -> Set[str]:
        return set(self._data.keys())

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)


class ModelFamily(AsimovBase):
    def __init__(self, name: str, model_config: Any = None) -> None:
        super().__init__(model_config=model_config)
        self.name = name


class ModuleType(AsimovBase):
    def __init__(self, name: str, model_config: Any = None) -> None:
        super().__init__(model_config=model_config)
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
        id: Optional[UUID] = None,
        status: TaskStatus = TaskStatus.PENDING,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(model_config=model_config)
        self.objective = objective
        self.type = type
        self.params = params
        self.id = id or uuid4()
        self.status = status
        self.result = result
        self.error = error

    def set_error(self, error: str) -> None:
        self.error = error

    def set_result(self, result: Any) -> None:
        self.result = result

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


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
        self.context = context
        self.middlewares = middlewares
        self.stop_on_success = stop_on_success
        self.timeout = float(timeout)


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
        self.condition = condition
        self.inputs = inputs
        self.max_retries = int(max_retries)
        self.max_visits = max_visits
        self.outputs = outputs
        self.parallel = bool(parallel)
        self.retry_from = retry_from
        self.retry_on_failure = bool(retry_on_failure)


class NonRetryableException(Exception):
    pass


class SnapshotControl(AsimovBase):
    def __init__(self, name: str, model_config: Any = None) -> None:
        super().__init__(model_config=model_config)
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
        if not isinstance(result, dict):
            return False
        if "success" in result:
            return bool(result.get("success"))
        if "status" in result:
            return str(result.get("status")).lower() in {"success", "ok", "passed", "true"}
        return True

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Union[Awaitable[Dict[str, Any]], AsyncGenerator]:
        raise NotImplementedError

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        async def _apply_middlewares(data: Dict[str, Any]) -> Dict[str, Any]:
            cfg = self.config
            if cfg and cfg.middlewares:
                for mw in cfg.middlewares:
                    data = mw.process(data, cache)
            return data

        async def _run_process() -> Dict[str, Any]:
            res = self.process(cache, semaphore)
            if inspect.isasyncgen(res):
                last: Any = None
                async for item in res:  # type: ignore[misc]
                    last = item
                if last is None:
                    last = {}
                if not isinstance(last, dict):
                    last = {"result": last}
                return last
            if inspect.isawaitable(res):
                out = await res  # type: ignore[assignment]
                if out is None:
                    out = {}
                if not isinstance(out, dict):
                    out = {"result": out}
                return out
            if res is None:
                return {}
            if not isinstance(res, dict):
                return {"result": res}
            return res

        timeout = 0.0
        if self.config is not None:
            timeout = float(self.config.timeout or 0.0)

        if timeout and timeout > 0:
            result = await asyncio.wait_for(_run_process(), timeout=timeout)
        else:
            result = await _run_process()

        result = await _apply_middlewares(result)
        return result


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
        self.modules: List[AgentModule] = list(modules or [])
        self.node_config = node_config
        for m in self.modules:
            m.container = self

    def apply_middlewares(self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        out = data
        for mw in middlewares:
            out = mw.process(out, cache)
        return out

    async def run_module_with_concurrency_control(
        self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        async with semaphore:
            return await module.run(cache, semaphore)

    async def run_parallel_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        tasks = [asyncio.create_task(self.run_module_with_concurrency_control(m, cache, semaphore)) for m in self.modules]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        combined: Dict[str, Any] = {}
        for m, r in zip(self.modules, results):
            if isinstance(r, Exception):
                raise r
            combined[m.name] = r
            if self.config and self.config.stop_on_success and m.is_success(r):
                break
        return combined

    async def run_sequential_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        combined: Dict[str, Any] = {}
        for m in self.modules:
            r = await self.run_module_with_concurrency_control(m, cache, semaphore)
            combined[m.name] = r
            if self.config and self.config.stop_on_success and m.is_success(r):
                break
        return combined

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        parallel = bool(self.node_config.parallel) if self.node_config is not None else False
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
        self.dependencies = dependencies
        self.snapshot = snapshot
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
        self.current_plan = current_plan
        self.execution_history = execution_history
        self.execution_index = execution_index
        self.total_iterations = total_iterations

    def mark_executed(self, step_index: int, node_index: int) -> None:
        if self.current_plan is None:
            raise ValueError("No current_plan set")
        if step_index < 0 or step_index >= len(self.current_plan):
            raise IndexError("step_index out of range")
        step = self.current_plan[step_index]
        if node_index < 0 or node_index >= len(step.nodes):
            raise IndexError("node_index out of range")
        step.executed[node_index] = True

    def was_executed(self, node_name: str) -> bool:
        if self.current_plan is None:
            return False
        for step in self.current_plan:
            for i, n in enumerate(step.nodes):
                if n == node_name and i < len(step.executed) and step.executed[i]:
                    return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if self.current_plan is None:
            return False
        for step in self.current_plan:
            for i, n in enumerate(step.nodes):
                if n == node_name and i < len(step.skipped) and step.skipped[i]:
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
        self.next_node = next_node
        self.cleanup_on_jump = cleanup_on_jump
        self.condition = condition
        self.condition_variables = condition_variables
        self.metadata = metadata


class FlowControlConfig(AsimovBase):
    def __init__(
        self,
        decisions: Sequence[FlowDecision],
        default: Optional[str] = None,
        cleanup_on_default: bool = False,
        model_config: Any = None,
    ) -> None:
        super().__init__(model_config=model_config)
        self.decisions = decisions
        self.default = default
        self.cleanup_on_default = bool(cleanup_on_default)


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
        for d in self.flow_config.decisions:
            if d.condition is None:
                continue
            if self.evaluate_condition(d.condition, cache, cache_keys):
                return {"next_node": d.next_node, "metadata": d.metadata}
        if self.flow_config.default is not None:
            return {"next_node": self.flow_config.default, "metadata": None}
        return {"next_node": None, "metadata": None}

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


class Example(AsimovBase):
    def __init__(
        self,
        choice: str,
        choices: List[Dict[str, str]],
        message: str,
        reasoning: str,
        model_config: Any = None,
    ) -> None:
        super().__init__(model_config=model_config)
        self.choice = choice
        self.choices = choices
        self.message = message
        self.reasoning = reasoning


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
        self.examples = examples


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


class InferenceClient(AsimovBase):
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
        self.inference_client = inference_client
        self.input_var = input_var
        self.system_description = system_description
        self.use_historicals = use_historicals
        self.voters = int(voters)

    def set_attrs(self) -> None:
        return

    async def gen(self, generation_input: str, cache: Cache) -> str:
        system = self.system_description
        user = generation_input
        return await self.inference_client.generate(system=system, user=user)

    def most_common_string(self, string_list: List[str]) -> Optional[str]:
        if not string_list:
            return None
        counts: Dict[str, int] = {}
        for s in string_list:
            counts[s] = counts.get(s, 0) + 1
        best = max(counts.items(), key=lambda kv: kv[1])[0]
        return best

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        choices = [d.next_node for d in self.flow_config.decisions]
        default = self.flow_config.default
        input_value = None
        if self.input_var is not None:
            input_value = cache.get(self.input_var)
        generation_input = json.dumps(
            {
                "input_var": self.input_var,
                "input_value": input_value,
                "choices": choices,
                "default": default,
            },
            ensure_ascii=False,
        )

        async def _vote() -> str:
            async with semaphore:
                out = await self.gen(generation_input, cache)
            out = (out or "").strip()
            if out in choices:
                return out
            if default is not None:
                return default
            return out

        voters = max(1, self.voters)
        votes = await asyncio.gather(*[asyncio.create_task(_vote()) for _ in range(voters)])
        selected = self.most_common_string(list(votes))
        if selected in choices:
            return {"next_node": selected, "metadata": None}
        if default is not None:
            return {"next_node": default, "metadata": None}
        return {"next_node": None, "metadata": None}


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
        self.auto_snapshot = bool(auto_snapshot)
        self.cache = cache
        self.error_mailbox = error_mailbox
        self.execution_state = execution_state
        self.graph = graph
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_total_iterations = max_total_iterations
        self.node_results = node_results
        self.nodes = nodes
        self.output_mailbox = output_mailbox
        self._semaphore: Optional[asyncio.Semaphore] = None

        if self.nodes is not None:
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
        for n in self.nodes.values():
            n.set_nodes(self.nodes)
        if self.graph is None:
            self.graph = {}
        self.graph.setdefault(node.name, [])
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

    def _topological_steps(self, start_nodes: Optional[Set[str]] = None) -> ExecutionPlan:
        if self.nodes is None:
            return []
        deps: Dict[str, Set[str]] = {}
        for name, node in self.nodes.items():
            deps[name] = set(node.dependencies or [])

        if start_nodes is not None:
            allowed: Set[str] = set()
            stack = list(start_nodes)
            while stack:
                cur = stack.pop()
                if cur in allowed:
                    continue
                allowed.add(cur)
                for child in (self.graph or {}).get(cur, []):
                    stack.append(child)
            deps = {k: v for k, v in deps.items() if k in allowed}
            for k in list(deps.keys()):
                deps[k] = {d for d in deps[k] if d in deps}

        plan: ExecutionPlan = []
        remaining = set(deps.keys())
        while remaining:
            ready = sorted([n for n in remaining if not deps[n]])
            if not ready:
                raise ValueError("Cyclic or unresolved dependencies in graph")
            step = ExecutionStep(nodes=ready, executed=[False] * len(ready), skipped=[False] * len(ready))
            plan.append(step)
            for r in ready:
                remaining.remove(r)
            for n in remaining:
                deps[n].difference_update(ready)
        return plan

    def compile_execution_plan(self) -> ExecutionPlan:
        plan = self._topological_steps()
        if self.execution_state is None:
            self.execution_state = ExecutionState()
        self.execution_state.current_plan = plan
        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        plan = self._topological_steps(start_nodes={start_node})
        if self.execution_state is None:
            self.execution_state = ExecutionState()
        self.execution_state.current_plan = plan
        return plan

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        out: List[dict] = []
        for step in execution_plan:
            if not isinstance(step, dict):
                continue
            nodes = step.get("nodes", [])
            if node in nodes:
                break
            out.append(step)
        return out

    def is_success(self, result: Any) -> bool:
        if isinstance(result, dict):
            if "success" in result:
                return bool(result.get("success"))
            if "status" in result:
                return str(result.get("status")).lower() in {"success", "ok", "passed", "true"}
        return result is not None

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if self.execution_state is None or self.execution_state.current_plan is None:
            return
        to_skip = {node_name, *self.get_dependent_chains(node_name)}
        for step in self.execution_state.current_plan:
            for i, n in enumerate(step.nodes):
                if n in to_skip:
                    step.skipped[i] = True

    def _ensure_cache(self) -> Cache:
        if self.cache is None:
            self.cache = Cache()
        return self.cache

    def _ensure_results(self) -> Dict[str, Any]:
        if self.node_results is None:
            self.node_results = {}
        return self.node_results

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        base = pathlib.Path.cwd() / "snapshots"
        base.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        safe_hint = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in (name_hint or "snapshot"))
        snap_dir = base / f"{safe_hint}_{ts}"
        snap_dir.mkdir(parents=True, exist_ok=True)

        cache = self.cache.to_dict() if self.cache is not None else {}
        results = dict(self.node_results or {})
        state: Dict[str, Any] = {
            "task": {
                "id": str(task.id) if task.id else None,
                "objective": task.objective,
                "type": task.type,
                "params": task.params,
                "status": task.status.value if isinstance(task.status, TaskStatus) else str(task.status),
                "result": task.result,
                "error": task.error,
            },
            "cache": cache,
            "node_results": results,
        }
        (snap_dir / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        return snap_dir

    def run_from_snapshot(self, snapshot_dir: pathlib.Path):
        state_path = snapshot_dir / "state.json"
        data = json.loads(state_path.read_text(encoding="utf-8"))
        self.cache = Cache(data.get("cache") or {})
        self.node_results = data.get("node_results") or {}
        return data

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if self.nodes is None or node_name not in self.nodes:
            raise KeyError(f"Unknown node: {node_name}")
        cache = self._ensure_cache()
        results = self._ensure_results()
        if self._semaphore is None:
            self.set_semaphore()
        assert self._semaphore is not None

        node = self.nodes[node_name]
        node.set_nodes(self.nodes)

        cfg = node.node_config
        if cfg is not None and cfg.condition:
            ok = FlowControlModule(name="__cond__", flow_config=FlowControlConfig(decisions=[])).evaluate_condition(
                cfg.condition, cache, cache.keys()
            )
            if not ok:
                results[node_name] = {"skipped": True, "reason": "condition_false"}
                return results[node_name]

        max_visits = cfg.max_visits if cfg is not None else None
        visits = int(results.get(f"__visits__:{node_name}", 0))
        if max_visits is not None and visits >= max_visits:
            results[node_name] = {"skipped": True, "reason": "max_visits_reached"}
            return results[node_name]
        results[f"__visits__:{node_name}"] = visits + 1

        max_retries = int(cfg.max_retries) if cfg is not None else 0
        retry_on_failure = bool(cfg.retry_on_failure) if cfg is not None else False

        attempt = 0
        last_exc: Optional[BaseException] = None
        while True:
            try:
                out = await node.run(cache, self._semaphore)
                results[node_name] = out
                return out
            except NonRetryableException as e:
                last_exc = e
                break
            except Exception as e:
                last_exc = e
                if not retry_on_failure:
                    break
                attempt += 1
                if attempt > max_retries:
                    break
                continue

        err = {"error": str(last_exc) if last_exc else "unknown_error"}
        results[node_name] = err
        return err

    async def run_task(self, task: Task) -> None:
        cache = self._ensure_cache()
        self._ensure_results()
        if self._semaphore is None:
            self.set_semaphore()
        assert self._semaphore is not None

        task.update_status(TaskStatus.RUNNING)

        if self.execution_state is None:
            self.execution_state = ExecutionState()
        if self.execution_state.execution_history is None:
            self.execution_state.execution_history = []
        if self.execution_state.total_iterations is None:
            self.execution_state.total_iterations = 0

        if self.execution_state.current_plan is None:
            self.compile_execution_plan()

        total_iter_limit = self.max_total_iterations
        if total_iter_limit is not None and self.execution_state.total_iterations >= total_iter_limit:
            task.update_status(TaskStatus.FAILED)
            task.set_error("max_total_iterations reached")
            return

        plan = self.execution_state.current_plan
        for step_index, step in enumerate(plan):
            for node_index, node_name in enumerate(step.nodes):
                if step.skipped[node_index]:
                    continue
                if step.executed[node_index]:
                    continue
                if self.execution_state.total_iterations is None:
                    self.execution_state.total_iterations = 0
                if total_iter_limit is not None and self.execution_state.total_iterations >= total_iter_limit:
                    task.update_status(TaskStatus.FAILED)
                    task.set_error("max_total_iterations reached")
                    return

                self.execution_state.total_iterations += 1
                out = await self.run_node(node_name)
                self.execution_state.mark_executed(step_index, node_index)

                if self.auto_snapshot:
                    self.snapshot(task, name_hint=f"node_{node_name}")

                if isinstance(out, dict) and "next_node" in out:
                    next_node = out.get("next_node")
                    if isinstance(next_node, str) and next_node:
                        self.execution_state.execution_history.append(plan)
                        plan = self.compile_execution_plan_from(next_node)
                        self.execution_state.current_plan = plan
                        break
            else:
                continue
            break

        task.set_result(self.node_results)
        task.update_status(TaskStatus.SUCCESS)


__all__ = [
    "Agent",
    "AgentDirectedFlowControl",
    "AgentDrivenFlowControlConfig",
    "AgentDrivenFlowDecision",
    "AgentModule",
    "AsimovBase",
    "Cache",
    "CompositeModule",
    "Example",
    "ExecutionState",
    "ExecutionStep",
    "Executor",
    "FlowControlConfig",
    "FlowControlModule",
    "FlowDecision",
    "InferenceClient",
    "Middleware",
    "ModelFamily",
    "ModuleConfig",
    "ModuleType",
    "Node",
    "NodeConfig",
    "NonRetryableException",
    "SnapshotControl",
    "Task",
    "TaskStatus",
]