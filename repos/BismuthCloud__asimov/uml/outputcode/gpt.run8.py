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
    Set,
    Tuple,
    Union,
)
from uuid import UUID, uuid4


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

    def update(self, data: Dict[str, Any]) -> None:
        self._data.update(data)

    def keys(self) -> Set[str]:
        return set(self._data.keys())

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Cache":
        return cls(initial=data)


class ModuleType:
    def __init__(self, name: str) -> None:
        self.name = name


class ModelFamily:
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
        id: Optional[UUID] = None,
        status: TaskStatus = TaskStatus.PENDING,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(model_config=model_config)
        self.objective: str = objective
        self.type: str = type
        self.params: Optional[Dict[str, Any]] = params
        self.id: Optional[UUID] = id or uuid4()
        self.status: TaskStatus = status
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
    ) -> Union[Awaitable[Dict[str, Any]], AsyncGenerator]:
        raise NotImplementedError

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        async with semaphore:
            proc = self.process(cache, semaphore)
            if inspect.isasyncgen(proc):
                last: Dict[str, Any] = {}
                async for item in proc:  # type: ignore[misc]
                    if isinstance(item, dict):
                        last = item
                return last
            if inspect.isawaitable(proc):
                if self.config and self.config.timeout and self.config.timeout > 0:
                    return await asyncio.wait_for(proc, timeout=self.config.timeout)  # type: ignore[arg-type]
                return await proc  # type: ignore[misc]
            if isinstance(proc, dict):
                return proc
            raise TypeError("process() must return an awaitable dict or an async generator")


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
        self.node_config: Optional[NodeConfig] = node_config
        for m in self.modules:
            m.container = self

    def apply_middlewares(
        self, middlewares: List[Middleware], data: Dict[str, Any], cache: Cache
    ) -> Dict[str, Any]:
        out = data
        for mw in middlewares:
            out = mw.process(out, cache)
            if not isinstance(out, dict):
                raise TypeError("Middleware.process must return a dict")
        return out

    async def run_module_with_concurrency_control(
        self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        result = await module.run(cache, semaphore)
        if module.config and module.config.middlewares:
            result = self.apply_middlewares(module.config.middlewares, result, cache)
        return result

    async def run_parallel_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        tasks = [asyncio.create_task(self.run_module_with_concurrency_control(m, cache, semaphore)) for m in self.modules]
        results = await asyncio.gather(*tasks)
        merged: Dict[str, Any] = {}
        for r in results:
            if isinstance(r, dict):
                merged.update(r)
        return merged

    async def run_sequential_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        for m in self.modules:
            r = await self.run_module_with_concurrency_control(m, cache, semaphore)
            if isinstance(r, dict):
                merged.update(r)
            if m.config and m.config.stop_on_success and m.is_success(r):
                break
        return merged

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            return await self.run_parallel_modules(cache, semaphore)
        return await self.run_sequential_modules(cache, semaphore)


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

    async def cancel_gen(self, agen: Any) -> None:
        if agen is None:
            return
        aclose = getattr(agen, "aclose", None)
        if callable(aclose):
            await aclose()

    def cleanup(self) -> None:
        return


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

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await self.run(cache, semaphore)

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
    async def generate(self, generation_input: Any) -> str:
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
        self.inference_client: InferenceClient = inference_client
        self.input_var: Optional[str] = input_var
        self.system_description: str = system_description
        self.use_historicals: Optional[bool] = use_historicals
        self.voters: int = int(voters)

    def set_attrs(self) -> None:
        return

    async def gen(self, generation_input: Any, cache: Cache) -> str:
        _ = cache
        return await self.inference_client.generate(generation_input)

    def most_common_string(self, string_list: List[str]) -> Optional[str]:
        if not string_list:
            return None
        counts: Dict[str, int] = {}
        for s in string_list:
            counts[s] = counts.get(s, 0) + 1
        best = max(counts.items(), key=lambda kv: kv[1])[0]
        return best

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        async with semaphore:
            choices = [d.next_node for d in self.flow_config.decisions]
            payload = {
                "system_description": self.system_description,
                "choices": choices,
                "input_var": self.input_var,
                "input": cache.get(self.input_var) if self.input_var else None,
                "use_historicals": self.use_historicals,
            }
            votes: List[str] = []
            for _ in range(max(1, self.voters)):
                out = await self.gen(payload, cache)
                if out in choices:
                    votes.append(out)
            selected = self.most_common_string(votes)
            if selected is None:
                selected = self.flow_config.default
            return {"next_node": selected, "votes": votes}


@dataclass
class ExecutionStep:
    nodes: List[str]
    executed: List[bool]
    skipped: List[bool]

    def __init__(self, nodes: List[str]) -> None:
        self.nodes = list(nodes)
        self.executed = [False for _ in self.nodes]
        self.skipped = [False for _ in self.nodes]


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
            for i, n in enumerate(step.nodes):
                if n == node_name and step.executed[i]:
                    return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if self.current_plan is None:
            return False
        for step in self.current_plan:
            for i, n in enumerate(step.nodes):
                if n == node_name and step.skipped[i]:
                    return True
        return False


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
                current_plan=None, execution_history=[], execution_index=0, total_iterations=0
            )

    def set_semaphore(self) -> None:
        limit = self.max_concurrent_tasks if self.max_concurrent_tasks and self.max_concurrent_tasks > 0 else 1
        self._semaphore = asyncio.Semaphore(limit)

    def add_node(self, node: Node) -> None:
        if self.nodes is None:
            self.nodes = {}
        if self.graph is None:
            self.graph = {}
        self.nodes[node.name] = node
        node.set_nodes(self.nodes)
        deps = list(node.dependencies or [])
        self.graph.setdefault(node.name, [])
        for dep in deps:
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

    def is_success(self, result: Any) -> bool:
        if result is None:
            return False
        if isinstance(result, dict) and "success" in result:
            return bool(result.get("success"))
        return True

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if not self.execution_state or not self.execution_state.current_plan:
            return
        to_skip = {node_name, *self.get_dependent_chains(node_name)}
        for step in self.execution_state.current_plan:
            for i, n in enumerate(step.nodes):
                if n in to_skip:
                    step.skipped[i] = True

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        out: List[dict] = []
        for item in execution_plan:
            if item.get("node") == node:
                break
            out.append(item)
        return out

    def compile_execution_plan(self) -> ExecutionPlan:
        if not self.nodes:
            return []
        deps: Dict[str, Set[str]] = {}
        for name, node in self.nodes.items():
            deps[name] = set(node.dependencies or [])
        plan: ExecutionPlan = []
        remaining = set(deps.keys())
        while remaining:
            ready = sorted([n for n in remaining if not (deps[n] & remaining)])
            if not ready:
                ready = sorted(list(remaining))
            step = ExecutionStep(ready)
            plan.append(step)
            for n in ready:
                remaining.remove(n)
        if self.execution_state is None:
            self.execution_state = ExecutionState(current_plan=plan, execution_history=[], execution_index=0, total_iterations=0)
        else:
            self.execution_state.current_plan = plan
        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        if not self.nodes or start_node not in self.nodes:
            return []
        reachable: Set[str] = set()

        def dfs(n: str) -> None:
            if n in reachable:
                return
            reachable.add(n)
            for child in (self.graph or {}).get(n, []):
                dfs(child)

        dfs(start_node)
        sub_nodes = {k: v for k, v in self.nodes.items() if k in reachable}
        deps: Dict[str, Set[str]] = {}
        for name, node in sub_nodes.items():
            deps[name] = set([d for d in (node.dependencies or []) if d in sub_nodes])
        plan: ExecutionPlan = []
        remaining = set(deps.keys())
        while remaining:
            ready = sorted([n for n in remaining if not (deps[n] & remaining)])
            if not ready:
                ready = sorted(list(remaining))
            step = ExecutionStep(ready)
            plan.append(step)
            for n in ready:
                remaining.remove(n)
        if self.execution_state is None:
            self.execution_state = ExecutionState(current_plan=plan, execution_history=[], execution_index=0, total_iterations=0)
        else:
            self.execution_state.current_plan = plan
        return plan

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        base = pathlib.Path.cwd() / "snapshots"
        base.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        safe_hint = "".join(c for c in name_hint if c.isalnum() or c in ("-", "_"))[:64] or "snapshot"
        snap_dir = base / f"{safe_hint}_{ts}_{task.id}"
        snap_dir.mkdir(parents=True, exist_ok=True)

        cache_path = snap_dir / "cache.json"
        nodes_path = snap_dir / "node_results.json"
        task_path = snap_dir / "task.json"

        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(self.cache.to_dict() if self.cache else {}, f)

        with nodes_path.open("w", encoding="utf-8") as f:
            json.dump(self.node_results or {}, f)

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
            )
        return snap_dir

    def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        cache_path = snapshot_dir / "cache.json"
        nodes_path = snapshot_dir / "node_results.json"
        if cache_path.exists():
            with cache_path.open("r", encoding="utf-8") as f:
                self.cache = Cache.from_dict(json.load(f))
        if nodes_path.exists():
            with nodes_path.open("r", encoding="utf-8") as f:
                self.node_results = json.load(f)

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if not self.nodes or node_name not in self.nodes:
            raise KeyError(f"Unknown node: {node_name}")
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()
        node = self.nodes[node_name]
        node.set_nodes(self.nodes)

        if node.node_config and node.node_config.condition:
            fc = FlowControlModule(
                name=f"{node_name}__condition",
                flow_config=FlowControlConfig(
                    decisions=[FlowDecision(next_node=node_name, condition=node.node_config.condition)],
                    default=None,
                    cleanup_on_default=False,
                ),
            )
            cond_res = await fc.run(self.cache, self._semaphore)
            if cond_res.get("next_node") is None:
                return {"skipped": True}

        max_retries = node.node_config.max_retries if node.node_config else 0
        attempts = 0
        last_exc: Optional[BaseException] = None
        while True:
            try:
                result = await node.run(self.cache, self._semaphore)
                if isinstance(result, dict):
                    self.cache.update(result)
                self.node_results[node_name] = result
                return result if isinstance(result, dict) else {"result": result}
            except NonRetryableException as e:
                last_exc = e
                break
            except BaseException as e:
                last_exc = e
                if attempts >= max_retries:
                    break
                attempts += 1
                continue
        err = {"error": str(last_exc) if last_exc else "Unknown error"}
        self.node_results[node_name] = err
        self.cache.set(self.error_mailbox, err)
        return err

    async def run_task(self, task: Task) -> None:
        if self.cache is None:
            self.cache = Cache()
        if self.execution_state is None:
            self.execution_state = ExecutionState(current_plan=None, execution_history=[], execution_index=0, total_iterations=0)
        if self._semaphore is None:
            self.set_semaphore()

        task.update_status(TaskStatus.RUNNING)
        self.cache.set("task", {"id": str(task.id), "objective": task.objective, "type": task.type, "params": task.params})

        plan = self.compile_execution_plan()
        if self.execution_state.execution_history is None:
            self.execution_state.execution_history = []
        self.execution_state.execution_history.append(plan)
        self.execution_state.current_plan = plan

        visits: Dict[str, int] = {}
        total_iterations = 0

        for step_index, step in enumerate(plan):
            for node_index, node_name in enumerate(step.nodes):
                if step.skipped[node_index]:
                    continue
                if self.max_total_iterations is not None and total_iterations >= self.max_total_iterations:
                    task.set_error("Max total iterations exceeded")
                    task.update_status(TaskStatus.FAILED)
                    self.cache.set(self.error_mailbox, {"error": task.error})
                    return

                node = self.nodes.get(node_name) if self.nodes else None
                if node and node.node_config and node.node_config.max_visits is not None:
                    visits[node_name] = visits.get(node_name, 0) + 1
                    if visits[node_name] > node.node_config.max_visits:
                        step.skipped[node_index] = True
                        continue

                res = await self.run_node(node_name)
                self.execution_state.mark_executed(step_index, node_index)
                total_iterations += 1
                if self.execution_state.total_iterations is None:
                    self.execution_state.total_iterations = 0
                self.execution_state.total_iterations += 1

                if isinstance(res, dict) and res.get("skipped") is True:
                    step.skipped[node_index] = True
                    continue

                if node and node.node_config and node.node_config.retry_on_failure:
                    if not self.is_success(res):
                        retry_from = node.node_config.retry_from
                        if retry_from:
                            self.mark_node_and_deps_as_skipped(node_name)
                            new_plan = self.compile_execution_plan_from(retry_from)
                            if self.execution_state.execution_history is None:
                                self.execution_state.execution_history = []
                            self.execution_state.execution_history.append(new_plan)
                            plan = new_plan
                            break

                if self.auto_snapshot:
                    self.snapshot(task, name_hint=f"after_{node_name}")

        task.set_result(self.cache.get(self.output_mailbox))
        if task.result is None:
            task.set_result(self.node_results)
        task.update_status(TaskStatus.SUCCESS)
        self.cache.set(self.output_mailbox, task.result)


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