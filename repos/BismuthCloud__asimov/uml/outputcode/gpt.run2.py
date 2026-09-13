from __future__ import annotations

import asyncio
import inspect
import json
import pathlib
import uuid
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
        status: TaskStatus = TaskStatus.PENDING,
    ) -> None:
        super().__init__()
        self.error: Optional[str] = None
        self.id: Optional[uuid.UUID] = id
        self.objective: str = objective
        self.params: Optional[Dict[str, Any]] = params
        self.result: Optional[Any] = None
        self.status: TaskStatus = status
        self.type: str = type

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
    ) -> None:
        super().__init__()
        self.context: Optional[Dict[str, Any]] = context
        self.middlewares: Optional[List[Middleware]] = middlewares
        self.stop_on_success: bool = bool(stop_on_success)
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
    ) -> None:
        super().__init__()
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if max_visits is not None and max_visits < 0:
            raise ValueError("max_visits must be >= 0 when provided")
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
    ) -> None:
        super().__init__()
        self.config: Optional[ModuleConfig] = config
        self.container: Optional["CompositeModule"] = container
        self.dependencies: Optional[List[str]] = dependencies
        self.executions: Optional[int] = executions
        self.input_mailboxes: Optional[List[str]] = input_mailboxes
        self.name: str = name
        self.output_mailbox: Optional[str] = output_mailbox
        self.trace: Optional[bool] = trace
        self.type: Optional[ModuleType] = type

    def is_success(self, result: Dict[str, Any]) -> bool:
        if not isinstance(result, dict):
            return False
        if "success" in result:
            return bool(result.get("success"))
        if "status" in result:
            return str(result.get("status")).lower() in {"success", "ok", "passed", "true"}
        return False

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Union[Dict[str, Any], AsyncGenerator]:
        raise NotImplementedError

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        cfg = self.config or ModuleConfig()
        async with semaphore:
            coro_or_agen = self.process(cache, semaphore)
            if inspect.isasyncgen(coro_or_agen):
                agen = coro_or_agen
                last: Any = None
                try:
                    async for item in agen:
                        last = item
                finally:
                    try:
                        await agen.aclose()
                    except Exception:
                        pass
                if isinstance(last, dict):
                    result = last
                else:
                    result = {"result": last}
            else:
                if cfg.timeout and cfg.timeout > 0:
                    result = await asyncio.wait_for(coro_or_agen, timeout=cfg.timeout)
                else:
                    result = await coro_or_agen

        if not isinstance(result, dict):
            result = {"result": result}

        if cfg.context:
            cache.update(cfg.context)

        if cfg.middlewares:
            for mw in cfg.middlewares:
                result = mw.process(result, cache)
                if not isinstance(result, dict):
                    raise TypeError("Middleware.process must return a dict")

        return result


class Executor(AgentModule):
    def __init__(
        self,
        name: str,
        type: Optional[ModuleType] = None,
        config: Optional[ModuleConfig] = None,
    ) -> None:
        super().__init__(name=name, type=type, config=config)

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
    ) -> None:
        super().__init__(name=name, type=type, config=config)
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
        return await module.run(cache, semaphore)

    async def run_parallel_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        tasks = [asyncio.create_task(self.run_module_with_concurrency_control(m, cache, semaphore)) for m in self.modules]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        combined: Dict[str, Any] = {}
        for m, r in zip(self.modules, results):
            combined[m.name] = r
        return combined

    async def run_sequential_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        combined: Dict[str, Any] = {}
        stop_on_success = bool((self.config or ModuleConfig()).stop_on_success)
        for m in self.modules:
            r = await self.run_module_with_concurrency_control(m, cache, semaphore)
            combined[m.name] = r
            if stop_on_success and m.is_success(r):
                break
        return combined

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        cfg = self.config or ModuleConfig()
        parallel = bool(self.node_config.parallel) if self.node_config else False
        if parallel:
            result = await self.run_parallel_modules(cache, semaphore)
        else:
            result = await self.run_sequential_modules(cache, semaphore)

        if cfg.middlewares:
            result = self.apply_middlewares(cfg.middlewares, result, cache)
        return result


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
    ) -> None:
        super().__init__(name=name, modules=modules, node_config=node_config, type=type, config=config)
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
        if hasattr(agen, "aclose") and inspect.isasyncgen(agen):
            try:
                await agen.aclose()
            except Exception:
                pass

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
    ) -> None:
        super().__init__()
        self.current_plan: Optional[ExecutionPlan] = current_plan
        self.execution_history: Optional[List[ExecutionPlan]] = execution_history
        self.execution_index: Optional[int] = execution_index
        self.total_iterations: Optional[int] = total_iterations

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
    ) -> None:
        super().__init__()
        self.cleanup_on_jump: Optional[bool] = cleanup_on_jump
        self.condition: Optional[str] = condition
        self.condition_variables: Optional[List[str]] = condition_variables
        self.metadata: Optional[Dict[str, Any]] = metadata
        self.next_node: str = next_node


class FlowControlConfig(AsimovBase):
    def __init__(
        self,
        decisions: Sequence[FlowDecision],
        default: Optional[str] = None,
        cleanup_on_default: bool = False,
    ) -> None:
        super().__init__()
        self.cleanup_on_default: bool = bool(cleanup_on_default)
        self.decisions: Sequence[FlowDecision] = decisions
        self.default: Optional[str] = default


class FlowControlModule(AgentModule):
    def __init__(
        self,
        name: str,
        flow_config: FlowControlConfig,
        type: Optional[ModuleType] = None,
        config: Optional[ModuleConfig] = None,
    ) -> None:
        super().__init__(name=name, type=type, config=config)
        self.flow_config = flow_config

    def evaluate_condition(self, condition: str, cache: Cache, cache_keys: Set[str]) -> bool:
        env: Dict[str, Any] = {k: cache.get(k) for k in cache_keys}
        env["cache"] = cache
        try:
            return bool(eval(condition, {"__builtins__": {}}, env))
        except Exception:
            return False

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        cache_keys = cache.keys()
        for decision in self.flow_config.decisions:
            cond = decision.condition
            if cond is None:
                continue
            keys = set(decision.condition_variables or [])
            if not keys:
                keys = cache_keys
            if self.evaluate_condition(cond, cache, keys):
                return {"next_node": decision.next_node, "metadata": decision.metadata}
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
    ) -> None:
        super().__init__(
            next_node=next_node,
            cleanup_on_jump=cleanup_on_jump,
            condition=condition,
            condition_variables=condition_variables,
            metadata=metadata,
        )
        self.examples: Optional[List[Example]] = examples


class AgentDrivenFlowControlConfig(FlowControlConfig):
    def __init__(
        self,
        decisions: Sequence[AgentDrivenFlowDecision],
        default: Optional[str] = None,
        cleanup_on_default: bool = False,
    ) -> None:
        super().__init__(decisions=decisions, default=default, cleanup_on_default=cleanup_on_default)
        self.decisions: Sequence[AgentDrivenFlowDecision] = decisions


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
    ) -> None:
        super().__init__(name=name, flow_config=flow_config, type=type, config=config)
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

    async def gen(self, generation_input: Any, cache: Cache) -> str:
        user = str(generation_input)
        system = self.system_description
        return await self.inference_client.generate(system=system, user=user)

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        async with semaphore:
            inp = cache.get(self.input_var) if self.input_var else cache.to_dict()
            votes: List[str] = []
            for _ in range(max(1, self.voters)):
                out = await self.gen(inp, cache)
                votes.append(out)
            choice = self.most_common_string(votes)

        if choice is None:
            if self.flow_config.default is not None:
                return {"next_node": self.flow_config.default, "metadata": None}
            return {"next_node": None, "metadata": None}

        for d in self.flow_config.decisions:
            if d.next_node == choice:
                return {"next_node": d.next_node, "metadata": d.metadata}

        if self.flow_config.default is not None:
            return {"next_node": self.flow_config.default, "metadata": None}
        return {"next_node": None, "metadata": None}


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
    ) -> None:
        super().__init__()
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
        limit = self.max_concurrent_tasks if self.max_concurrent_tasks is not None else 1
        if limit <= 0:
            raise ValueError("max_concurrent_tasks must be > 0")
        self._semaphore = asyncio.Semaphore(limit)

    def add_node(self, node: Node) -> None:
        if self.nodes is None:
            self.nodes = {}
        if self.graph is None:
            self.graph = {}
        self.nodes[node.name] = node
        node.set_nodes(self.nodes)
        deps = list(node.dependencies or [])
        self.graph[node.name] = deps

    def add_multiple_nodes(self, nodes: List[Node]) -> None:
        for n in nodes:
            self.add_node(n)

    def update_dependencies(self, parent_node: str, new_node: str) -> None:
        if self.graph is None:
            self.graph = {}
        deps = self.graph.get(new_node, [])
        if parent_node not in deps:
            deps.append(parent_node)
        self.graph[new_node] = deps
        if self.nodes and new_node in self.nodes:
            node = self.nodes[new_node]
            node.dependencies = deps

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        if not self.graph:
            return tuple()
        visited: Set[str] = set()
        order: List[str] = []

        def dfs(n: str) -> None:
            for child, deps in self.graph.items():
                if n in (deps or []) and child not in visited:
                    visited.add(child)
                    order.append(child)
                    dfs(child)

        dfs(node_name)
        return tuple(order)

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if not self.execution_state or not self.execution_state.current_plan:
            return
        targets = {node_name, *self.get_dependent_chains(node_name)}
        for step in self.execution_state.current_plan:
            for i, n in enumerate(step.nodes):
                if n in targets:
                    step.skipped[i] = True

    def is_success(self, result: Any) -> bool:
        if isinstance(result, dict) and "success" in result:
            return bool(result.get("success"))
        if isinstance(result, dict) and "status" in result:
            return str(result.get("status")).lower() in {"success", "ok", "passed", "true"}
        return result is not None

    def compile_execution_plan(self) -> ExecutionPlan:
        if not self.nodes:
            return []
        remaining = set(self.nodes.keys())
        deps_map: Dict[str, Set[str]] = {}
        for n in remaining:
            deps = set((self.graph or {}).get(n, []) or [])
            deps_map[n] = deps

        plan: ExecutionPlan = []
        while remaining:
            ready = sorted([n for n in remaining if deps_map.get(n, set()).issubset(set(self.nodes.keys()) - remaining)])
            if not ready:
                ready = sorted(list(remaining))
            step = ExecutionStep(nodes=ready, executed=[False] * len(ready), skipped=[False] * len(ready))
            plan.append(step)
            for n in ready:
                remaining.remove(n)
        if self.execution_state is None:
            self.execution_state = ExecutionState()
        self.execution_state.current_plan = plan
        if self.execution_state.execution_history is None:
            self.execution_state.execution_history = []
        self.execution_state.execution_history.append(plan)
        self.execution_state.execution_index = 0
        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        if not self.nodes or start_node not in self.nodes:
            return []
        plan = self.compile_execution_plan()
        filtered: ExecutionPlan = []
        include = False
        for step in plan:
            if start_node in step.nodes:
                include = True
            if include:
                filtered.append(step)
        if self.execution_state:
            self.execution_state.current_plan = filtered
        return filtered

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        out: List[dict] = []
        for step in execution_plan:
            out.append(step)
            if isinstance(step, dict) and step.get("node") == node:
                break
        return out

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        base = pathlib.Path(name_hint)
        base.mkdir(parents=True, exist_ok=True)
        snap_dir = base / f"snapshot_{uuid.uuid4().hex}"
        snap_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "task": {
                "id": str(task.id) if task.id else None,
                "objective": task.objective,
                "type": task.type,
                "params": task.params,
                "status": task.status.value if isinstance(task.status, TaskStatus) else str(task.status),
                "error": task.error,
                "result": task.result,
            },
            "cache": self.cache.to_dict() if self.cache else {},
            "node_results": self.node_results or {},
            "graph": self.graph or {},
        }
        (snap_dir / "snapshot.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return snap_dir

    def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        p = snapshot_dir / "snapshot.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        if self.cache is None:
            self.cache = Cache()
        self.cache.update(data.get("cache", {}) or {})
        self.node_results = data.get("node_results", {}) or {}
        self.graph = data.get("graph", {}) or {}

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if not self.nodes or node_name not in self.nodes:
            raise KeyError(f"Unknown node: {node_name}")
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()
        node = self.nodes[node_name]

        cfg = node.node_config or NodeConfig()
        if cfg.condition:
            ok = FlowControlModule(name="__cond__", flow_config=FlowControlConfig(decisions=[])).evaluate_condition(
                cfg.condition, self.cache, self.cache.keys()
            )
            if not ok:
                self.node_results[node_name] = {"skipped": True}
                return {"skipped": True}

        result: Dict[str, Any] = {}
        attempts = 0
        max_attempts = 1 + max(0, cfg.max_retries)
        while True:
            attempts += 1
            try:
                result = await node.run(self.cache, self._semaphore)
                self.node_results[node_name] = result
                return result
            except NonRetryableException as e:
                err = {"error": str(e), "non_retryable": True}
                self.node_results[node_name] = err
                raise
            except Exception as e:
                if not cfg.retry_on_failure or attempts >= max_attempts:
                    err = {"error": str(e)}
                    self.node_results[node_name] = err
                    raise
                continue

    async def run_task(self, task: Task) -> None:
        if task.id is None:
            task.id = uuid.uuid4()
        task.update_status(TaskStatus.RUNNING)

        if self.execution_state is None:
            self.execution_state = ExecutionState(current_plan=None, execution_history=[], execution_index=0, total_iterations=0)
        if self.execution_state.total_iterations is None:
            self.execution_state.total_iterations = 0

        if self.max_total_iterations is not None and self.execution_state.total_iterations >= self.max_total_iterations:
            task.update_status(TaskStatus.FAILED)
            task.set_error("max_total_iterations exceeded")
            return

        try:
            plan = self.compile_execution_plan()
            self.execution_state.current_plan = plan
            for si, step in enumerate(plan):
                for ni, node_name in enumerate(step.nodes):
                    if step.skipped[ni]:
                        continue
                    if self.execution_state.was_executed(node_name):
                        continue
                    await self.run_node(node_name)
                    self.execution_state.mark_executed(si, ni)
                    if self.auto_snapshot:
                        self.snapshot(task, name_hint="snapshots")
            task.set_result(self.node_results)
            task.update_status(TaskStatus.SUCCESS)
        except Exception as e:
            task.set_error(str(e))
            task.update_status(TaskStatus.FAILED)
        finally:
            self.execution_state.total_iterations = (self.execution_state.total_iterations or 0) + 1