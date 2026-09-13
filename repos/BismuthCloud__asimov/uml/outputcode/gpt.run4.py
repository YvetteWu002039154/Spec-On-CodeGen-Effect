from __future__ import annotations

import asyncio
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
from collections import Counter


class AsimovBase:
    model_config: Any = None

    def __init__(self, model_config: Any = None) -> None:
        self.model_config = model_config


class Cache(AsimovBase):
    def __init__(self, initial: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
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


class ModelFamily(AsimovBase):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name


class ModuleType(AsimovBase):
    def __init__(self, name: str) -> None:
        super().__init__()
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
        status: Optional[TaskStatus] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(model_config=model_config)
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


class SnapshotControl(AsimovBase):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name


class NonRetryableException(Exception):
    pass


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
            coro_or_gen = self.process(cache, semaphore)
            if hasattr(coro_or_gen, "__aiter__"):
                agen = coro_or_gen  # type: ignore[assignment]
                last: Dict[str, Any] = {}
                async for item in agen:  # type: ignore[misc]
                    if isinstance(item, dict):
                        last = item
                return last
            result = await coro_or_gen  # type: ignore[func-returns-value]
            if not isinstance(result, dict):
                return {"result": result}
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
                raise TypeError("Middleware.process must return Dict[str, Any]")
        return out

    async def run_module_with_concurrency_control(
        self, module: AgentModule, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        result = await module.run(cache, semaphore)
        mws = module.config.middlewares if module.config and module.config.middlewares else None
        if mws:
            result = self.apply_middlewares(mws, result, cache)
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
    ) -> None:
        super().__init__(name=name, modules=modules, node_config=node_config, type=type)
        self.dependencies: Optional[List[str]] = dependencies
        self.snapshot: Optional[SnapshotControl] = snapshot
        self._nodes: Optional[Dict[str, "Node"]] = None

    def set_nodes(self, nodes: Dict[str, "Node"]) -> None:
        self._nodes = nodes

    def get_nodes(self) -> Optional[Dict[str, "Node"]]:
        return self._nodes

    async def cancel_gen(self, agen: Any) -> None:
        aclose = getattr(agen, "aclose", None)
        if callable(aclose):
            await aclose()

    def cleanup(self) -> None:
        return


class FlowDecision(AsimovBase):
    def __init__(
        self,
        next_node: str,
        condition: Optional[str] = None,
        condition_variables: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        cleanup_on_jump: Optional[bool] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(model_config=model_config)
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
    ) -> None:
        super().__init__(name=name, type=type, config=config)
        self.flow_config = flow_config

    def evaluate_condition(self, condition: str, cache: Cache, cache_keys: Set[str]) -> bool:
        safe_globals: Dict[str, Any] = {"__builtins__": {}}
        safe_locals: Dict[str, Any] = {k: cache.get(k) for k in cache_keys}
        safe_locals["cache"] = cache
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


class Example(AsimovBase):
    def __init__(
        self,
        choice: str,
        choices: List[Dict[str, str]],
        message: str,
        reasoning: str,
    ) -> None:
        super().__init__()
        self.choice: str = choice
        self.choices: List[Dict[str, str]] = choices
        self.message: str = message
        self.reasoning: str = reasoning


class AgentDrivenFlowDecision(FlowDecision):
    def __init__(
        self,
        next_node: str,
        condition: Optional[str] = None,
        condition_variables: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        cleanup_on_jump: Optional[bool] = None,
        examples: Optional[List[Example]] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(
            next_node=next_node,
            condition=condition,
            condition_variables=condition_variables,
            metadata=metadata,
            cleanup_on_jump=cleanup_on_jump,
            model_config=model_config,
        )
        self.examples: Optional[List[Example]] = examples


class AgentDrivenFlowControlConfig(FlowControlConfig):
    def __init__(
        self,
        decisions: Sequence[AgentDrivenFlowDecision],
        default: Optional[str] = None,
        model_config: Any = None,
    ) -> None:
        super().__init__(decisions=decisions, default=default, cleanup_on_default=False, model_config=model_config)


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
    ) -> None:
        super().__init__(name=name, flow_config=flow_config, type=type, config=config)
        self.inference_client: InferenceClient = inference_client
        self.system_description: str = system_description
        self.voters: int = int(voters)
        self.input_var: Optional[str] = input_var
        self.use_historicals: Optional[bool] = use_historicals

    def set_attrs(self) -> None:
        return

    def most_common_string(self, string_list: List[str]) -> Optional[str]:
        if not string_list:
            return None
        c = Counter(string_list)
        return c.most_common(1)[0][0]

    async def gen(self, generation_input: str, cache: Cache) -> str:
        system = self.system_description
        user = generation_input
        return await self.inference_client.generate(system=system, user=user)

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        async with semaphore:
            decisions: Sequence[AgentDrivenFlowDecision] = self.flow_config.decisions  # type: ignore[assignment]
            choices = [d.next_node for d in decisions]
            input_value = cache.get(self.input_var) if self.input_var else None
            payload = {
                "input_var": self.input_var,
                "input": input_value,
                "choices": choices,
            }
            generation_input = json.dumps(payload, ensure_ascii=False)
            votes: List[str] = []
            for _ in range(max(1, self.voters)):
                out = await self.gen(generation_input, cache)
                out_str = str(out).strip()
                if out_str in choices:
                    votes.append(out_str)
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


class Agent(AsimovBase):
    def __init__(
        self,
        auto_snapshot: bool = False,
        cache: Optional[Cache] = None,
        error_mailbox: str = "error",
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
        if self.node_results is None:
            self.node_results = {}
        if self.nodes is None:
            self.nodes = {}
        if self.graph is None:
            self.graph = {}
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

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        out: List[dict] = []
        for step in execution_plan:
            nodes = step.get("nodes", [])
            if node in nodes:
                break
            out.append(step)
        return out

    def compile_execution_plan(self) -> ExecutionPlan:
        if self.nodes is None:
            return []
        indeg: Dict[str, int] = {n: 0 for n in self.nodes.keys()}
        if self.graph:
            for parent, children in self.graph.items():
                for c in children:
                    if c in indeg:
                        indeg[c] += 1
                    else:
                        indeg[c] = 1
                if parent not in indeg:
                    indeg[parent] = 0

        ready = sorted([n for n, d in indeg.items() if d == 0])
        plan: ExecutionPlan = []
        remaining_children: Dict[str, List[str]] = {k: list(v) for k, v in (self.graph or {}).items()}

        while ready:
            step_nodes = ready
            plan.append(ExecutionStep(nodes=step_nodes, executed=[False] * len(step_nodes), skipped=[False] * len(step_nodes)))
            next_ready: List[str] = []
            for n in step_nodes:
                for child in remaining_children.get(n, []):
                    indeg[child] -= 1
                    if indeg[child] == 0:
                        next_ready.append(child)
            ready = sorted(next_ready)

        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        full = self.compile_execution_plan()
        if not full:
            return []
        seen_start = False
        out: ExecutionPlan = []
        for step in full:
            if not seen_start:
                if start_node in step.nodes:
                    seen_start = True
                else:
                    continue
            out.append(step)
        return out

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if self.nodes is None or self.cache is None:
            raise ValueError("Agent not initialized with nodes/cache")
        if node_name not in self.nodes:
            raise KeyError(node_name)
        if self._semaphore is None:
            self.set_semaphore()
        semaphore = self._semaphore
        node = self.nodes[node_name]

        if node.node_config and node.node_config.condition:
            fcm = FlowControlModule(name=f"{node_name}__condition", flow_config=FlowControlConfig(decisions=[]))
            ok = fcm.evaluate_condition(node.node_config.condition, self.cache, self.cache.keys())
            if not ok:
                return {"skipped": True, "node": node_name}

        max_retries = node.node_config.max_retries if node.node_config else 0
        attempts = 0
        last_exc: Optional[BaseException] = None
        while True:
            try:
                result = await node.run(self.cache, semaphore)
                self.node_results[node_name] = result
                return result
            except NonRetryableException as e:
                last_exc = e
                break
            except Exception as e:
                last_exc = e
                if not (node.node_config and node.node_config.retry_on_failure):
                    break
                attempts += 1
                if attempts > max_retries:
                    break
                continue
        err = str(last_exc) if last_exc is not None else "Unknown error"
        self.cache.set(self.error_mailbox, err)
        raise last_exc  # type: ignore[misc]

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        base = pathlib.Path.cwd() / "snapshots"
        base.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        safe_hint = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name_hint)[:64]
        snap_dir = base / f"{safe_hint}_{ts}"
        snap_dir.mkdir(parents=True, exist_ok=True)

        cache_path = snap_dir / "cache.json"
        state_path = snap_dir / "state.json"
        task_path = snap_dir / "task.json"

        cache_data = self.cache.to_dict() if self.cache else {}
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2, default=str)

        state_data: Dict[str, Any] = {}
        if self.execution_state and self.execution_state.current_plan is not None:
            state_data["current_plan"] = [
                {"nodes": s.nodes, "executed": s.executed, "skipped": s.skipped} for s in self.execution_state.current_plan
            ]
        if self.execution_state and self.execution_state.execution_index is not None:
            state_data["execution_index"] = self.execution_state.execution_index
        if self.execution_state and self.execution_state.total_iterations is not None:
            state_data["total_iterations"] = self.execution_state.total_iterations
        with state_path.open("w", encoding="utf-8") as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2, default=str)

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
                indent=2,
                default=str,
            )

        return snap_dir

    def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        cache_path = snapshot_dir / "cache.json"
        state_path = snapshot_dir / "state.json"
        if cache_path.exists():
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if self.cache is None:
                self.cache = Cache()
            self.cache.update(data)
        if state_path.exists():
            with state_path.open("r", encoding="utf-8") as f:
                sdata = json.load(f)
            plan = None
            if "current_plan" in sdata and isinstance(sdata["current_plan"], list):
                plan = []
                for step in sdata["current_plan"]:
                    plan.append(
                        ExecutionStep(
                            nodes=list(step.get("nodes", [])),
                            executed=list(step.get("executed", [False] * len(step.get("nodes", [])))),
                            skipped=list(step.get("skipped", [False] * len(step.get("nodes", [])))),
                        )
                    )
            self.execution_state = ExecutionState(
                current_plan=plan,
                execution_history=None,
                execution_index=sdata.get("execution_index"),
                total_iterations=sdata.get("total_iterations"),
            )

    async def run_task(self, task: Task) -> None:
        if self.cache is None:
            self.cache = Cache()
        if self.node_results is None:
            self.node_results = {}
        if self.execution_state is None:
            self.execution_state = ExecutionState(current_plan=None, execution_history=[], execution_index=0, total_iterations=0)

        self.set_semaphore()
        task.update_status(TaskStatus.RUNNING)

        plan = self.compile_execution_plan()
        self.execution_state.current_plan = plan
        if self.execution_state.execution_history is None:
            self.execution_state.execution_history = []
        self.execution_state.execution_history.append(plan)
        self.execution_state.execution_index = (self.execution_state.execution_index or 0) + 1

        total_iters = self.execution_state.total_iterations or 0
        for si, step in enumerate(plan):
            for ni, node_name in enumerate(step.nodes):
                if step.skipped[ni]:
                    continue
                if self.max_total_iterations is not None and total_iters >= self.max_total_iterations:
                    task.set_error("Max total iterations exceeded")
                    task.update_status(TaskStatus.FAILED)
                    return
                if self.execution_state.was_executed(node_name):
                    continue
                try:
                    res = await self.run_node(node_name)
                    self.execution_state.mark_executed(si, ni)
                    total_iters += 1
                    self.execution_state.total_iterations = total_iters
                    if self.auto_snapshot:
                        self.snapshot(task, f"{task.type}_{node_name}")
                    self.cache.set(self.output_mailbox, res)
                except Exception as e:
                    task.set_error(str(e))
                    task.update_status(TaskStatus.FAILED)
                    return

        task.set_result(self.node_results)
        task.update_status(TaskStatus.SUCCESS)