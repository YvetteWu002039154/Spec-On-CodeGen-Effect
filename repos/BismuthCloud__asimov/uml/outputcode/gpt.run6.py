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
    model_config: Any = None

    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


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
        id: Optional[UUID] = None,
        status: Optional[TaskStatus] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.objective: str = objective
        self.type: str = type
        self.params: Optional[Dict[str, Any]] = params
        self.id: Optional[UUID] = id or uuid4()
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
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
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
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
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
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
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
        async def _run_process() -> Dict[str, Any]:
            out = self.process(cache, semaphore)
            if inspect.isasyncgen(out):
                last: Dict[str, Any] = {}
                async for item in out:
                    if isinstance(item, dict):
                        last = item
                return last
            if inspect.isawaitable(out):
                res = await out  # type: ignore[func-returns-value]
                if not isinstance(res, dict):
                    return {"result": res}
                return res
            if isinstance(out, dict):
                return out
            return {"result": out}

        timeout = float(self.config.timeout) if self.config and self.config.timeout else 0.0
        if timeout and timeout > 0:
            return await asyncio.wait_for(_run_process(), timeout=timeout)
        return await _run_process()


class Executor(AgentModule):
    def __init__(
        self,
        name: str,
        type: Optional[ModuleType] = None,
        config: Optional[ModuleConfig] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, type=type, config=config, **kwargs)

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
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, type=type, config=config, **kwargs)
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
                out = {"result": out}
        return out

    async def run_module_with_concurrency_control(
        self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        async with semaphore:
            res = await module.run(cache, semaphore)
        if module.config and module.config.middlewares:
            res = self.apply_middlewares(module.config.middlewares, res, cache)
        return res

    async def run_parallel_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        results = await asyncio.gather(
            *[self.run_module_with_concurrency_control(m, cache, semaphore) for m in self.modules],
            return_exceptions=True,
        )
        out: Dict[str, Any] = {}
        for m, r in zip(self.modules, results):
            if isinstance(r, Exception):
                out[m.name] = {"error": str(r), "success": False}
            else:
                out[m.name] = r
        return out

    async def run_sequential_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for m in self.modules:
            res = await self.run_module_with_concurrency_control(m, cache, semaphore)
            out[m.name] = res
            if m.config and m.config.stop_on_success and m.is_success(res):
                break
        return out

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        parallel = bool(self.node_config.parallel) if self.node_config else False
        if parallel:
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
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, modules=modules, node_config=node_config, type=type, config=config, **kwargs)
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


class FlowDecision(AsimovBase):
    def __init__(
        self,
        next_node: str,
        cleanup_on_jump: Optional[bool] = None,
        condition: Optional[str] = None,
        condition_variables: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
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
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
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
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, type=type, config=config, **kwargs)
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
        **kwargs: Any,
    ) -> None:
        super().__init__(
            next_node=next_node,
            cleanup_on_jump=cleanup_on_jump,
            condition=condition,
            condition_variables=condition_variables,
            metadata=metadata,
            **kwargs,
        )
        self.examples: Optional[List[Example]] = examples


class AgentDrivenFlowControlConfig(FlowControlConfig):
    def __init__(
        self,
        decisions: Sequence[AgentDrivenFlowDecision],
        default: Optional[str] = None,
        cleanup_on_default: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(decisions=decisions, default=default, cleanup_on_default=cleanup_on_default, **kwargs)


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
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, flow_config=flow_config, type=type, config=config, **kwargs)
        self.inference_client: InferenceClient = inference_client
        self.system_description: str = system_description
        self.voters: int = int(voters)
        self.input_var: Optional[str] = input_var
        self.use_historicals: Optional[bool] = use_historicals

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
        async with semaphore:
            inp = ""
            if self.input_var:
                v = cache.get(self.input_var)
                inp = "" if v is None else str(v)
            else:
                inp = json.dumps(cache.to_dict(), default=str)

            choices = [d.next_node for d in self.flow_config.decisions]
            prompt = (
                f"{self.system_description}\n\n"
                f"Available choices: {choices}\n"
                f"Input: {inp}\n"
                f"Return exactly one choice."
            )

            votes: List[str] = []
            for _ in range(max(1, self.voters)):
                try:
                    out = await self.gen(prompt, cache)
                except Exception:
                    out = ""
                out = (out or "").strip()
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


ExecutionPlan = List[ExecutionStep]


class ExecutionState(AsimovBase):
    def __init__(
        self,
        current_plan: Optional[ExecutionPlan] = None,
        execution_history: Optional[List[ExecutionPlan]] = None,
        execution_index: Optional[int] = None,
        total_iterations: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.current_plan: Optional[ExecutionPlan] = current_plan
        self.execution_history: Optional[List[ExecutionPlan]] = execution_history
        self.execution_index: Optional[int] = execution_index
        self.total_iterations: Optional[int] = total_iterations

    def mark_executed(self, step_index: int, node_index: int) -> None:
        if not self.current_plan:
            return
        if step_index < 0 or step_index >= len(self.current_plan):
            return
        step = self.current_plan[step_index]
        if node_index < 0 or node_index >= len(step.nodes):
            return
        step.executed[node_index] = True

    def was_executed(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan:
            for i, n in enumerate(step.nodes):
                if n == node_name and i < len(step.executed) and step.executed[i]:
                    return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan:
            for i, n in enumerate(step.nodes):
                if n == node_name and i < len(step.skipped) and step.skipped[i]:
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
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
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
        n = self.max_concurrent_tasks if self.max_concurrent_tasks is not None else 1
        if n <= 0:
            n = 1
        self._semaphore = asyncio.Semaphore(n)

    def add_node(self, node: Node) -> None:
        if self.nodes is None:
            self.nodes = {}
        self.nodes[node.name] = node
        node.set_nodes(self.nodes)
        if self.graph is None:
            self.graph = {}
        self.graph.setdefault(node.name, [])
        deps = node.dependencies or []
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

    def is_success(self, result: Any) -> bool:
        if result is None:
            return False
        if isinstance(result, dict) and "success" in result:
            return bool(result.get("success"))
        return True

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if not self.execution_state or not self.execution_state.current_plan:
            return
        targets = {node_name, *self.get_dependent_chains(node_name)}
        for step in self.execution_state.current_plan:
            for i, n in enumerate(step.nodes):
                if n in targets:
                    if i < len(step.skipped):
                        step.skipped[i] = True

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        out: List[dict] = []
        for step in execution_plan:
            nodes = step.get("nodes", [])
            if node in nodes:
                break
            out.append(step)
        return out

    def compile_execution_plan(self) -> ExecutionPlan:
        if not self.nodes:
            return []
        indeg: Dict[str, int] = {n: 0 for n in self.nodes.keys()}
        for n, node in self.nodes.items():
            for dep in (node.dependencies or []):
                if dep in indeg:
                    indeg[n] += 1
                else:
                    indeg.setdefault(dep, 0)
                    indeg[n] += 1

        remaining: Set[str] = set(self.nodes.keys())
        plan: ExecutionPlan = []
        while remaining:
            ready = sorted([n for n in remaining if indeg.get(n, 0) == 0])
            if not ready:
                ready = sorted(list(remaining))
            step_nodes = ready
            for n in step_nodes:
                remaining.remove(n)
                for child in self.graph.get(n, []) if self.graph else []:
                    if child in indeg:
                        indeg[child] = max(0, indeg[child] - 1)
            plan.append(ExecutionStep(nodes=step_nodes, executed=[False] * len(step_nodes), skipped=[False] * len(step_nodes)))
        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        full = self.compile_execution_plan()
        if not full:
            return []
        included: Set[str] = {start_node, *self.get_dependent_chains(start_node)}
        out: ExecutionPlan = []
        for step in full:
            nodes = [n for n in step.nodes if n in included]
            if not nodes:
                continue
            out.append(ExecutionStep(nodes=nodes, executed=[False] * len(nodes), skipped=[False] * len(nodes)))
        return out

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        base = pathlib.Path(name_hint)
        base.mkdir(parents=True, exist_ok=True)
        snap_dir = base / f"snapshot_{task.id}"
        if snap_dir.exists():
            shutil.rmtree(snap_dir)
        snap_dir.mkdir(parents=True, exist_ok=True)

        cache_path = snap_dir / "cache.json"
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(self.cache.to_dict() if self.cache else {}, f, default=str)

        results_path = snap_dir / "node_results.json"
        with results_path.open("w", encoding="utf-8") as f:
            json.dump(self.node_results or {}, f, default=str)

        state_path = snap_dir / "execution_state.json"
        state_obj: Dict[str, Any] = {}
        if self.execution_state and self.execution_state.current_plan is not None:
            state_obj["current_plan"] = [
                {"nodes": s.nodes, "executed": s.executed, "skipped": s.skipped}
                for s in self.execution_state.current_plan
            ]
        else:
            state_obj["current_plan"] = None
        state_obj["execution_index"] = self.execution_state.execution_index if self.execution_state else None
        state_obj["total_iterations"] = self.execution_state.total_iterations if self.execution_state else None
        with state_path.open("w", encoding="utf-8") as f:
            json.dump(state_obj, f, default=str)

        task_path = snap_dir / "task.json"
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
                default=str,
            )
        return snap_dir

    def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        cache_path = snapshot_dir / "cache.json"
        if cache_path.exists():
            with cache_path.open("r", encoding="utf-8") as f:
                self.cache = Cache(json.load(f))
        results_path = snapshot_dir / "node_results.json"
        if results_path.exists():
            with results_path.open("r", encoding="utf-8") as f:
                self.node_results = json.load(f)
        state_path = snapshot_dir / "execution_state.json"
        if state_path.exists():
            with state_path.open("r", encoding="utf-8") as f:
                state_obj = json.load(f)
            plan_obj = state_obj.get("current_plan")
            plan: Optional[ExecutionPlan]
            if plan_obj is None:
                plan = None
            else:
                plan = [
                    ExecutionStep(
                        nodes=list(s.get("nodes", [])),
                        executed=list(s.get("executed", [])),
                        skipped=list(s.get("skipped", [])),
                    )
                    for s in plan_obj
                ]
            self.execution_state = ExecutionState(
                current_plan=plan,
                execution_history=[],
                execution_index=state_obj.get("execution_index"),
                total_iterations=state_obj.get("total_iterations"),
            )

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if not self.nodes or node_name not in self.nodes:
            raise KeyError(node_name)
        if self._semaphore is None:
            self.set_semaphore()
        assert self.cache is not None
        assert self._semaphore is not None

        node = self.nodes[node_name]
        node.set_nodes(self.nodes)

        if node.node_config and node.node_config.condition:
            cond_mod = FlowControlModule(
                name=f"{node_name}.__condition__",
                flow_config=FlowControlConfig(decisions=[], default=None),
            )
            ok = cond_mod.evaluate_condition(node.node_config.condition, self.cache, self.cache.keys())
            if not ok:
                return {"skipped": True, "success": True}

        max_retries = node.node_config.max_retries if node.node_config else 0
        attempts = 0
        last_exc: Optional[Exception] = None
        while True:
            try:
                res = await node.run(self.cache, self._semaphore)
                self.node_results[node_name] = res
                if isinstance(res, dict):
                    self.cache.set(node_name, res)
                if self.auto_snapshot and node.snapshot:
                    t = Task(objective=f"node:{node_name}", type="node")
                    self.snapshot(t, node.snapshot.name)
                return res
            except NonRetryableException as e:
                last_exc = e
                break
            except Exception as e:
                last_exc = e
                attempts += 1
                if attempts > max_retries:
                    break
                await asyncio.sleep(0)

        err = {"error": str(last_exc) if last_exc else "Unknown error", "success": False}
        self.node_results[node_name] = err
        self.cache.set(node_name, err)
        return err

    async def run_task(self, task: Task) -> None:
        if self.execution_state is None:
            self.execution_state = ExecutionState(current_plan=None, execution_history=[], execution_index=0, total_iterations=0)
        if self.execution_state.execution_history is None:
            self.execution_state.execution_history = []
        if self.execution_state.total_iterations is None:
            self.execution_state.total_iterations = 0

        if self.max_total_iterations is not None and self.execution_state.total_iterations >= self.max_total_iterations:
            task.update_status(TaskStatus.FAILED)
            task.set_error("Max total iterations exceeded")
            return

        if self._semaphore is None:
            self.set_semaphore()
        assert self.cache is not None

        task.update_status(TaskStatus.RUNNING)
        self.cache.set(self.output_mailbox, None)
        self.cache.set(self.error_mailbox, None)

        plan = self.compile_execution_plan()
        self.execution_state.current_plan = plan
        self.execution_state.execution_history.append(plan)
        self.execution_state.execution_index = (self.execution_state.execution_index or 0) + 1
        self.execution_state.total_iterations = (self.execution_state.total_iterations or 0) + 1

        try:
            for si, step in enumerate(plan):
                for ni, node_name in enumerate(step.nodes):
                    if step.skipped[ni]:
                        continue
                    if self.execution_state.was_executed(node_name):
                        continue
                    res = await self.run_node(node_name)
                    if isinstance(res, dict) and res.get("skipped") is True:
                        step.skipped[ni] = True
                        continue
                    self.execution_state.mark_executed(si, ni)
                    if not self.is_success(res):
                        if self.nodes and node_name in self.nodes:
                            node = self.nodes[node_name]
                            if node.node_config and node.node_config.retry_on_failure and node.node_config.retry_from:
                                self.mark_node_and_deps_as_skipped(node_name)
                                retry_plan = self.compile_execution_plan_from(node.node_config.retry_from)
                                self.execution_state.current_plan = retry_plan
                                self.execution_state.execution_history.append(retry_plan)
                                plan = retry_plan
                                break
                        self.cache.set(self.error_mailbox, res)
                        task.set_error(str(res.get("error", "Node failed")) if isinstance(res, dict) else "Node failed")
                        task.update_status(TaskStatus.FAILED)
                        return
                else:
                    continue
                continue

            self.cache.set(self.output_mailbox, self.node_results)
            task.set_result(self.node_results)
            task.update_status(TaskStatus.SUCCESS)
        except Exception as e:
            self.cache.set(self.error_mailbox, str(e))
            task.set_error(str(e))
            task.update_status(TaskStatus.FAILED)


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