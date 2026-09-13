from __future__ import annotations

import asyncio
import json
import pathlib
import time
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
)
from uuid import UUID, uuid4
from collections import Counter


class AsimovBase:
    model_config: Dict[str, Any] = {}


class NonRetryableException(Exception):
    pass


class ModelFamily(AsimovBase):
    def __init__(self, name: str):
        self.name = name


class ModuleType(AsimovBase):
    def __init__(self, name: str):
        self.name = name


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class Task(AsimovBase):
    model_config: Dict[str, Any] = {}

    def __init__(
        self,
        objective: str,
        type: str,
        params: Optional[Dict[str, Any]] = None,
        id: Optional[UUID] = None,
    ):
        self.objective: str = objective
        self.type: str = type
        self.params: Optional[Dict[str, Any]] = params
        self.id: Optional[UUID] = id or uuid4()
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.status: TaskStatus = TaskStatus.PENDING

    def set_error(self, error: str) -> None:
        self.error = error

    def set_result(self, result: Any) -> None:
        self.result = result

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


class Cache(AsimovBase):
    def __init__(self, initial: Optional[Dict[str, Any]] = None):
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
    ):
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
        retry_on_failure: bool = True,
    ):
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if max_visits is not None and max_visits < 0:
            raise ValueError("max_visits must be >= 0")
        self.condition: Optional[str] = condition
        self.inputs: Optional[List[str]] = inputs
        self.max_retries: int = int(max_retries)
        self.max_visits: Optional[int] = max_visits
        self.outputs: Optional[List[str]] = outputs
        self.parallel: bool = bool(parallel)
        self.retry_from: Optional[str] = retry_from
        self.retry_on_failure: bool = bool(retry_on_failure)


class SnapshotControl(AsimovBase):
    def __init__(self, name: str):
        self.name = name


class FlowDecision(AsimovBase):
    def __init__(
        self,
        next_node: str,
        condition: Optional[str] = None,
        condition_variables: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        cleanup_on_jump: Optional[bool] = None,
    ):
        self.next_node: str = next_node
        self.condition: Optional[str] = condition
        self.condition_variables: Optional[List[str]] = condition_variables
        self.metadata: Optional[Dict[str, Any]] = metadata
        self.cleanup_on_jump: Optional[bool] = cleanup_on_jump


class FlowControlConfig(AsimovBase):
    def __init__(
        self,
        decisions: Sequence[FlowDecision],
        default: Optional[str] = None,
        cleanup_on_default: bool = False,
    ):
        self.decisions: Sequence[FlowDecision] = decisions
        self.default: Optional[str] = default
        self.cleanup_on_default: bool = bool(cleanup_on_default)


class AgentDrivenFlowDecision(FlowDecision):
    def __init__(
        self,
        next_node: str,
        condition: Optional[str] = None,
        condition_variables: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        cleanup_on_jump: Optional[bool] = None,
        examples: Optional[List["Example"]] = None,
    ):
        super().__init__(
            next_node=next_node,
            condition=condition,
            condition_variables=condition_variables,
            metadata=metadata,
            cleanup_on_jump=cleanup_on_jump,
        )
        self.examples: Optional[List["Example"]] = examples


class AgentDrivenFlowControlConfig(FlowControlConfig):
    def __init__(
        self,
        decisions: Sequence[AgentDrivenFlowDecision],
        default: Optional[str] = None,
        cleanup_on_default: bool = False,
    ):
        super().__init__(decisions=decisions, default=default, cleanup_on_default=cleanup_on_default)
        self.decisions: Sequence[AgentDrivenFlowDecision] = decisions


class Example(AsimovBase):
    def __init__(self, choice: str, choices: List[Dict[str, str]], message: str, reasoning: str):
        self.choice: str = choice
        self.choices: List[Dict[str, str]] = choices
        self.message: str = message
        self.reasoning: str = reasoning


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
    ):
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
        cfg = self.config or ModuleConfig()
        async with semaphore:
            if cfg.timeout and cfg.timeout > 0:
                res = await asyncio.wait_for(self.process(cache, semaphore), timeout=cfg.timeout)
            else:
                res = await self.process(cache, semaphore)

        if hasattr(res, "__aiter__"):
            collected: List[Any] = []
            async for item in res:  # type: ignore[misc]
                collected.append(item)
            result: Dict[str, Any] = {"items": collected}
        else:
            result = res  # type: ignore[assignment]

        if not isinstance(result, dict):
            result = {"result": result}

        if cfg.context:
            result = {**cfg.context, **result}

        if cfg.middlewares:
            for mw in cfg.middlewares:
                result = mw.process(result, cache)

        if self.output_mailbox:
            cache.set(self.output_mailbox, result)

        return result


class Executor(AgentModule):
    def __init__(
        self,
        name: str,
        type: Optional[ModuleType] = None,
        config: Optional[ModuleConfig] = None,
    ):
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
    ):
        super().__init__(name=name, type=type, config=config)
        self.modules: List[AgentModule] = modules or []
        self.node_config: Optional[NodeConfig] = node_config
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
        return await module.run(cache, semaphore)

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
            cfg = m.config or ModuleConfig()
            if cfg.stop_on_success and m.is_success(r):
                break
        return merged

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        parallel = bool(self.node_config.parallel) if self.node_config else False
        if parallel:
            result = await self.run_parallel_modules(cache, semaphore)
        else:
            result = await self.run_sequential_modules(cache, semaphore)

        cfg = self.config or ModuleConfig()
        if cfg.middlewares:
            result = self.apply_middlewares(cfg.middlewares, result, cache)
        if self.output_mailbox:
            cache.set(self.output_mailbox, result)
        return result

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
    ):
        super().__init__(name=name, modules=modules, node_config=node_config, type=type)
        self.dependencies: Optional[List[str]] = dependencies
        self.snapshot: Optional[SnapshotControl] = snapshot
        self._nodes: Optional[Dict[str, "Node"]] = None

    def set_nodes(self, nodes: Dict[str, "Node"]) -> None:
        self._nodes = nodes

    def get_nodes(self):
        return self._nodes

    def cancel_gen(self, agen):
        try:
            aclose = getattr(agen, "aclose", None)
            if callable(aclose):
                return aclose()
        except Exception:
            return None
        return None

    def cleanup(self):
        return None


class ExecutionStep(AsimovBase):
    def __init__(self, nodes: List[str]):
        self.nodes: List[str] = list(nodes)
        self.executed: List[bool] = [False for _ in self.nodes]
        self.skipped: List[bool] = [False for _ in self.nodes]


ExecutionPlan = List[ExecutionStep]


class ExecutionState(AsimovBase):
    def __init__(
        self,
        current_plan: Optional[ExecutionPlan] = None,
        execution_history: Optional[List[ExecutionPlan]] = None,
        execution_index: Optional[int] = None,
        total_iterations: Optional[int] = None,
    ):
        self.current_plan: Optional[ExecutionPlan] = current_plan
        self.execution_history: Optional[List[ExecutionPlan]] = execution_history
        self.execution_index: Optional[int] = execution_index
        self.total_iterations: Optional[int] = total_iterations

    def mark_executed(self, step_index: int, node_index: int):
        if self.current_plan is None:
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


class FlowControlModule(AgentModule):
    def __init__(
        self,
        name: str,
        flow_config: FlowControlConfig,
        type: Optional[ModuleType] = None,
        config: Optional[ModuleConfig] = None,
    ):
        super().__init__(name=name, type=type, config=config)
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
            if decision.condition is None:
                continue
            if self.evaluate_condition(decision.condition, cache, cache_keys):
                return {"next_node": decision.next_node, "metadata": decision.metadata}
        if self.flow_config.default is not None:
            return {"next_node": self.flow_config.default, "metadata": None}
        return {"next_node": None, "metadata": None}

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


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
        voters: int = 1,
        input_var: Optional[str] = None,
        use_historicals: Optional[bool] = None,
        type: Optional[ModuleType] = None,
        config: Optional[ModuleConfig] = None,
    ):
        super().__init__(name=name, flow_config=flow_config, type=type, config=config)
        self.flow_config: AgentDrivenFlowControlConfig = flow_config
        self.inference_client: InferenceClient = inference_client
        self.system_description: str = system_description
        self.voters: int = int(voters)
        self.input_var: Optional[str] = input_var
        self.use_historicals: Optional[bool] = use_historicals

    def set_attrs(self):
        return None

    def most_common_string(self, string_list):
        if not string_list:
            return None
        return Counter(string_list).most_common(1)[0][0]

    async def gen(self, generation_input, cache):
        system = self.system_description
        user = str(generation_input)
        return await self.inference_client.generate(system=system, user=user)

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        choices = [d.next_node for d in self.flow_config.decisions]
        if self.flow_config.default is not None:
            choices.append(self.flow_config.default)

        if self.input_var:
            generation_input = cache.get(self.input_var, "")
        else:
            generation_input = cache.to_dict()

        async def vote_once() -> Optional[str]:
            text = await self.gen(generation_input, cache)
            text_norm = (text or "").strip()
            if text_norm in choices:
                return text_norm
            return None

        async with semaphore:
            votes = await asyncio.gather(*[vote_once() for _ in range(max(1, self.voters))])

        winner = self.most_common_string([v for v in votes if v is not None])
        if winner is None:
            winner = self.flow_config.default
        return {"next_node": winner, "votes": votes}

    async def process(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


class Agent(AsimovBase):
    def __init__(
        self,
        output_mailbox: str = "output",
        error_mailbox: str = "error",
        auto_snapshot: bool = False,
        cache: Optional[Cache] = None,
        max_concurrent_tasks: Optional[int] = None,
        max_total_iterations: Optional[int] = None,
    ):
        self.auto_snapshot: bool = bool(auto_snapshot)
        self.cache: Optional[Cache] = cache
        self.error_mailbox: str = error_mailbox
        self.execution_state: Optional[ExecutionState] = None
        self.graph: Optional[Dict[str, List[str]]] = None
        self.max_concurrent_tasks: Optional[int] = max_concurrent_tasks
        self.max_total_iterations: Optional[int] = max_total_iterations
        self.node_results: Optional[Dict[str, Any]] = None
        self.nodes: Optional[Dict[str, Node]] = None
        self.output_mailbox: str = output_mailbox
        self._semaphore: Optional[asyncio.Semaphore] = None

    def set_semaphore(self):
        limit = self.max_concurrent_tasks if self.max_concurrent_tasks is not None else 1
        if limit <= 0:
            limit = 1
        self._semaphore = asyncio.Semaphore(limit)

    def add_node(self, node: Node):
        if self.nodes is None:
            self.nodes = {}
        if node.name in self.nodes:
            raise ValueError(f"Node '{node.name}' already exists")
        self.nodes[node.name] = node
        node.set_nodes(self.nodes)
        if self.graph is None:
            self.graph = {}
        self.graph[node.name] = list(node.dependencies or [])
        for n in self.nodes.values():
            n.set_nodes(self.nodes)

    def add_multiple_nodes(self, nodes: List[Node]):
        for n in nodes:
            self.add_node(n)

    def update_dependencies(self, parent_node: str, new_node: str):
        if self.graph is None:
            self.graph = {}
        deps = self.graph.get(new_node, [])
        if parent_node not in deps:
            deps.append(parent_node)
        self.graph[new_node] = deps
        if self.nodes and new_node in self.nodes:
            self.nodes[new_node].dependencies = list(deps)

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        if not self.graph:
            return tuple()
        reverse: Dict[str, List[str]] = {}
        for n, deps in self.graph.items():
            for d in deps:
                reverse.setdefault(d, []).append(n)

        visited: Set[str] = set()
        order: List[str] = []

        def dfs(n: str):
            for child in reverse.get(n, []):
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
        if self.graph is None:
            self.graph = {name: list(node.dependencies or []) for name, node in self.nodes.items()}

        indeg: Dict[str, int] = {n: 0 for n in self.nodes.keys()}
        adj: Dict[str, List[str]] = {n: [] for n in self.nodes.keys()}
        for n, deps in self.graph.items():
            for d in deps:
                if d not in indeg:
                    raise ValueError(f"Unknown dependency '{d}' for node '{n}'")
                indeg[n] += 1
                adj[d].append(n)

        remaining = set(self.nodes.keys())
        plan: ExecutionPlan = []
        while remaining:
            layer = sorted([n for n in remaining if indeg.get(n, 0) == 0])
            if not layer:
                raise ValueError("Cycle detected in graph dependencies")
            plan.append(ExecutionStep(nodes=layer))
            for n in layer:
                remaining.remove(n)
                for m in adj.get(n, []):
                    indeg[m] -= 1
        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        full = self.compile_execution_plan()
        if start_node not in (self.nodes or {}):
            raise ValueError(f"Unknown start_node '{start_node}'")
        return self.slice_before_node(full, start_node)

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        if not execution_plan:
            return []
        if isinstance(execution_plan[0], ExecutionStep):
            plan_steps: ExecutionPlan = execution_plan  # type: ignore[assignment]
            new_plan: ExecutionPlan = []
            found = False
            for step in plan_steps:
                if node in step.nodes:
                    idx = step.nodes.index(node)
                    new_nodes = step.nodes[idx:]
                    new_step = ExecutionStep(nodes=new_nodes)
                    new_plan.append(new_step)
                    found = True
                elif found:
                    new_plan.append(ExecutionStep(nodes=list(step.nodes)))
            if not found:
                raise ValueError(f"Node '{node}' not found in execution plan")
            return new_plan  # type: ignore[return-value]
        else:
            found = False
            out: List[dict] = []
            for step in execution_plan:
                nodes = step.get("nodes", [])
                if node in nodes:
                    idx = nodes.index(node)
                    out.append({**step, "nodes": nodes[idx:]})
                    found = True
                elif found:
                    out.append(step)
            if not found:
                raise ValueError(f"Node '{node}' not found in execution plan")
            return out

    def is_success(self, result):
        if isinstance(result, dict) and "success" in result:
            return bool(result.get("success"))
        if isinstance(result, dict) and "status" in result:
            return str(result.get("status")).lower() in {"success", "ok", "passed", "true"}
        return result is not None

    def mark_node_and_deps_as_skipped(self, node_name: str):
        if not self.execution_state or not self.execution_state.current_plan:
            return
        to_skip = {node_name, *self.get_dependent_chains(node_name)}
        for step in self.execution_state.current_plan:
            for i, n in enumerate(step.nodes):
                if n in to_skip:
                    step.skipped[i] = True

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        base = pathlib.Path.cwd() / "snapshots"
        base.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        safe_hint = "".join(c for c in name_hint if c.isalnum() or c in ("-", "_"))[:64] or "snapshot"
        path = base / f"{safe_hint}_{ts}"
        path.mkdir(parents=True, exist_ok=True)

        cache_dict = self.cache.to_dict() if self.cache else {}
        node_results = dict(self.node_results or {})
        state = self.execution_state

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
            "cache": cache_dict,
            "node_results": node_results,
            "execution_state": self._serialize_execution_state(state),
        }
        (path / "snapshot.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _serialize_execution_state(self, state: Optional[ExecutionState]) -> Optional[Dict[str, Any]]:
        if state is None:
            return None
        def ser_plan(plan: Optional[ExecutionPlan]) -> Optional[List[Dict[str, Any]]]:
            if plan is None:
                return None
            return [{"nodes": s.nodes, "executed": s.executed, "skipped": s.skipped} for s in plan]

        return {
            "current_plan": ser_plan(state.current_plan),
            "execution_history": [ser_plan(p) for p in (state.execution_history or [])],
            "execution_index": state.execution_index,
            "total_iterations": state.total_iterations,
        }

    def _deserialize_execution_state(self, data: Optional[Dict[str, Any]]) -> Optional[ExecutionState]:
        if data is None:
            return None

        def deser_plan(plan_data: Optional[List[Dict[str, Any]]]) -> Optional[ExecutionPlan]:
            if plan_data is None:
                return None
            plan: ExecutionPlan = []
            for s in plan_data:
                step = ExecutionStep(nodes=list(s.get("nodes", [])))
                step.executed = list(s.get("executed", [False] * len(step.nodes)))
                step.skipped = list(s.get("skipped", [False] * len(step.nodes)))
                plan.append(step)
            return plan

        hist_raw = data.get("execution_history") or []
        history: List[ExecutionPlan] = []
        for p in hist_raw:
            dp = deser_plan(p)
            if dp is not None:
                history.append(dp)

        return ExecutionState(
            current_plan=deser_plan(data.get("current_plan")),
            execution_history=history if history else None,
            execution_index=data.get("execution_index"),
            total_iterations=data.get("total_iterations"),
        )

    def run_from_snapshot(self, snapshot_dir: pathlib.Path):
        snap_file = snapshot_dir / "snapshot.json"
        payload = json.loads(snap_file.read_text(encoding="utf-8"))
        self.cache = Cache(payload.get("cache") or {})
        self.node_results = payload.get("node_results") or {}
        self.execution_state = self._deserialize_execution_state(payload.get("execution_state"))

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if not self.nodes or node_name not in self.nodes:
            raise ValueError(f"Unknown node '{node_name}'")
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()
        assert self._semaphore is not None

        node = self.nodes[node_name]
        cfg = node.node_config or NodeConfig()
        if cfg.condition:
            ok = FlowControlModule(name="_cond", flow_config=FlowControlConfig(decisions=[])).evaluate_condition(
                cfg.condition, self.cache, self.cache.keys()
            )
            if not ok:
                return {"skipped": True, "reason": "condition_false"}

        if cfg.max_visits is not None:
            visits_key = f"__visits__:{node_name}"
            visits = int(self.cache.get(visits_key, 0))
            if visits >= cfg.max_visits:
                return {"skipped": True, "reason": "max_visits_reached"}
            self.cache.set(visits_key, visits + 1)

        attempts = 0
        last_exc: Optional[BaseException] = None
        while True:
            try:
                result = await node.run(self.cache, self._semaphore)
                if self.node_results is None:
                    self.node_results = {}
                self.node_results[node_name] = result
                return result
            except NonRetryableException as e:
                last_exc = e
                raise
            except BaseException as e:
                last_exc = e
                attempts += 1
                if attempts > cfg.max_retries or not cfg.retry_on_failure:
                    raise
                if cfg.retry_from:
                    self.mark_node_and_deps_as_skipped(cfg.retry_from)
                continue
            finally:
                if last_exc is not None and self.cache is not None:
                    self.cache.set(self.error_mailbox, str(last_exc))

    async def run_task(self, task: Task) -> None:
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()
        assert self._semaphore is not None

        task.update_status(TaskStatus.RUNNING)
        if self.node_results is None:
            self.node_results = {}

        if self.execution_state is None:
            self.execution_state = ExecutionState(
                current_plan=self.compile_execution_plan(),
                execution_history=[],
                execution_index=0,
                total_iterations=0,
            )
        if self.execution_state.current_plan is None:
            self.execution_state.current_plan = self.compile_execution_plan()
        if self.execution_state.execution_history is None:
            self.execution_state.execution_history = []
        if self.execution_state.total_iterations is None:
            self.execution_state.total_iterations = 0

        try:
            plan = self.execution_state.current_plan
            total_iters = 0
            for step_index, step in enumerate(plan):
                node_tasks: List[asyncio.Task] = []
                node_indices: List[int] = []
                for node_index, node_name in enumerate(step.nodes):
                    if step.skipped[node_index] or self.execution_state.was_skipped(node_name):
                        continue
                    if step.executed[node_index] or self.execution_state.was_executed(node_name):
                        continue
                    node_tasks.append(asyncio.create_task(self.run_node(node_name)))
                    node_indices.append(node_index)

                if node_tasks:
                    results = await asyncio.gather(*node_tasks, return_exceptions=True)
                    for idx, res in zip(node_indices, results):
                        if isinstance(res, BaseException):
                            raise res
                        self.execution_state.mark_executed(step_index, idx)

                total_iters += 1
                self.execution_state.total_iterations = total_iters
                if self.max_total_iterations is not None and total_iters >= self.max_total_iterations:
                    break

            task.set_result(self.node_results)
            task.update_status(TaskStatus.SUCCESS)
            self.cache.set(self.output_mailbox, self.node_results)
        except BaseException as e:
            task.set_error(str(e))
            task.update_status(TaskStatus.FAILED)
            self.cache.set(self.error_mailbox, str(e))
            raise
        finally:
            if self.auto_snapshot:
                self.snapshot(task, name_hint=f"task_{task.id}")