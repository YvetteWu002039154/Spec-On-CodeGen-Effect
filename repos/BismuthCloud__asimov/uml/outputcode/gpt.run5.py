from __future__ import annotations

import asyncio
import inspect
import json
import pathlib
import uuid
from collections import Counter
from dataclasses import dataclass
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


class Cache(dict):
    pass


class InferenceClient:
    async def generate(self, system: str, user: str) -> str:
        raise NotImplementedError


class AsimovBase:
    model_config: Any = None

    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class ModelFamily(AsimovBase):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name


class ModuleType(AsimovBase):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name


class TaskStatus(AsimovBase):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name


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
    ) -> None:
        super().__init__()
        self.objective = objective
        self.type = type
        self.params = params
        self.id = id or uuid.uuid4()
        self.status = status or TaskStatus("created")
        self.result = result
        self.error = error

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
    ) -> None:
        super().__init__()
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if max_visits is not None and max_visits < 0:
            raise ValueError("max_visits must be >= 0 when provided")
        self.condition = condition
        self.inputs = inputs
        self.max_retries = int(max_retries)
        self.max_visits = max_visits
        self.outputs = outputs
        self.parallel = bool(parallel)
        self.retry_from = retry_from
        self.retry_on_failure = bool(retry_on_failure)


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
        async def _run_process() -> Dict[str, Any]:
            out = await self.process(cache, semaphore)
            if inspect.isasyncgen(out):
                last: Any = None
                async for item in out:
                    last = item
                if last is None:
                    return {}
                if isinstance(last, dict):
                    return last
                return {"result": last}
            if isinstance(out, dict):
                return out
            return {"result": out}

        timeout = float(self.config.timeout) if self.config and self.config.timeout else 0.0
        if timeout > 0:
            return await asyncio.wait_for(_run_process(), timeout=timeout)
        return await _run_process()


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
        self.modules: List[AgentModule] = modules or []
        self.node_config = node_config
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
        async with semaphore:
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

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        parallel = bool(self.node_config.parallel) if self.node_config else False
        if parallel:
            return await self.run_parallel_modules(cache, semaphore)
        return await self.run_sequential_modules(cache, semaphore)


class SnapshotControl(AsimovBase):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name


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
    ) -> None:
        super().__init__()
        self.current_plan = current_plan
        self.execution_history = execution_history
        self.execution_index = execution_index
        self.total_iterations = total_iterations

    def mark_executed(self, step_index: int, node_index: int) -> None:
        if not self.current_plan:
            return
        if step_index < 0 or step_index >= len(self.current_plan):
            raise IndexError("step_index out of range")
        step = self.current_plan[step_index]
        if node_index < 0 or node_index >= len(step.nodes):
            raise IndexError("node_index out of range")
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
    ) -> None:
        super().__init__()
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
        cache_keys: Set[str] = set(cache.keys())
        for d in self.flow_config.decisions:
            if d.condition is None:
                continue
            keys = set(d.condition_variables or [])
            keys = keys.intersection(cache_keys) if keys else cache_keys
            if self.evaluate_condition(d.condition, cache, keys):
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
        self.choice = choice
        self.choices = choices
        self.message = message
        self.reasoning = reasoning


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
        self.examples = examples


class AgentDrivenFlowControlConfig(FlowControlConfig):
    def __init__(
        self,
        decisions: Sequence[AgentDrivenFlowDecision],
        default: Optional[str] = None,
        cleanup_on_default: bool = False,
    ) -> None:
        super().__init__(decisions=decisions, default=default, cleanup_on_default=cleanup_on_default)


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
        self.inference_client = inference_client
        self.input_var = input_var
        self.system_description = system_description
        self.use_historicals = use_historicals
        self.voters = int(voters)
        if self.voters <= 0:
            raise ValueError("voters must be >= 1")

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
        choices = [d.next_node for d in self.flow_config.decisions]
        if self.flow_config.default is not None:
            choices.append(self.flow_config.default)

        input_text = ""
        if self.input_var:
            v = cache.get(self.input_var)
            input_text = "" if v is None else str(v)

        prompt = {
            "input": input_text,
            "choices": choices,
        }
        generation_input = json.dumps(prompt, ensure_ascii=False)

        async def _vote() -> str:
            async with semaphore:
                out = await self.gen(generation_input, cache)
            out_s = (out or "").strip()
            if out_s in choices:
                return out_s
            return self.flow_config.default if self.flow_config.default is not None else ""

        votes = await asyncio.gather(*[asyncio.create_task(_vote()) for _ in range(self.voters)])
        selected = self.most_common_string([v for v in votes if v])
        if not selected:
            selected = self.flow_config.default
        return {"next_node": selected, "metadata": None}


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
    ) -> None:
        super().__init__()
        self.auto_snapshot = bool(auto_snapshot)
        self.cache: Optional[Cache] = cache
        self.error_mailbox = error_mailbox
        self.execution_state = execution_state
        self.graph = graph
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_total_iterations = max_total_iterations
        self.node_results = node_results
        self.nodes = nodes
        self.output_mailbox = output_mailbox
        self._semaphore: Optional[asyncio.Semaphore] = None

        if self.nodes:
            for n in self.nodes.values():
                n.set_nodes(self.nodes)

    def set_semaphore(self) -> None:
        limit = self.max_concurrent_tasks if self.max_concurrent_tasks is not None else 1
        if limit <= 0:
            raise ValueError("max_concurrent_tasks must be >= 1")
        self._semaphore = asyncio.Semaphore(limit)

    def add_node(self, node: Node) -> None:
        if self.nodes is None:
            self.nodes = {}
        if node.name in self.nodes:
            raise ValueError(f"Node '{node.name}' already exists")
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

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        out: List[dict] = []
        for step in execution_plan:
            if step.get("node") == node:
                break
            out.append(step)
        return out

    def compile_execution_plan(self) -> ExecutionPlan:
        if not self.nodes:
            return []
        remaining = set(self.nodes.keys())
        deps: Dict[str, Set[str]] = {}
        for name, node in self.nodes.items():
            deps[name] = set(node.dependencies or [])
        plan: ExecutionPlan = []
        while remaining:
            ready = sorted([n for n in remaining if not (deps.get(n) or set())])
            if not ready:
                raise ValueError("Cyclic or unresolved dependencies in graph")
            step_nodes = ready
            plan.append(ExecutionStep(nodes=step_nodes, executed=[False] * len(step_nodes), skipped=[False] * len(step_nodes)))
            for n in step_nodes:
                remaining.remove(n)
            for n in list(remaining):
                deps[n] = set(d for d in deps.get(n, set()) if d not in step_nodes)
        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        if not self.nodes or start_node not in self.nodes:
            raise ValueError("start_node not found")
        full = self.compile_execution_plan()
        started = False
        sliced: ExecutionPlan = []
        for step in full:
            if not started and start_node in step.nodes:
                started = True
            if started:
                sliced.append(step)
        return sliced

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

    def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        base = pathlib.Path.cwd() / "snapshots"
        base.mkdir(parents=True, exist_ok=True)
        snap_dir = base / f"{name_hint}_{task.id}"
        snap_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "task": {
                "id": str(task.id) if task.id else None,
                "objective": task.objective,
                "type": task.type,
                "params": task.params,
                "status": task.status.name if task.status else None,
                "result": task.result,
                "error": task.error,
            },
            "cache": dict(self.cache) if self.cache is not None else None,
            "node_results": self.node_results,
        }
        (snap_dir / "snapshot.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return snap_dir

    def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        p = snapshot_dir / "snapshot.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        cache_data = data.get("cache")
        self.cache = Cache(cache_data) if isinstance(cache_data, dict) else Cache()
        self.node_results = data.get("node_results") if isinstance(data.get("node_results"), dict) else {}

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if not self.nodes or node_name not in self.nodes:
            raise ValueError(f"Unknown node '{node_name}'")
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()
        node = self.nodes[node_name]
        result = await node.run(self.cache, self._semaphore)
        if self.node_results is None:
            self.node_results = {}
        self.node_results[node_name] = result
        if isinstance(result, dict):
            self.cache.update(result)
        return result

    async def run_task(self, task: Task) -> None:
        if self.cache is None:
            self.cache = Cache()
        if self.node_results is None:
            self.node_results = {}
        if self.execution_state is None:
            self.execution_state = ExecutionState(current_plan=None, execution_history=[], execution_index=0, total_iterations=0)
        if self._semaphore is None:
            self.set_semaphore()

        task.update_status(TaskStatus("running"))

        plan = self.compile_execution_plan()
        self.execution_state.current_plan = plan
        if self.execution_state.execution_history is None:
            self.execution_state.execution_history = []
        self.execution_state.execution_history.append(plan)
        self.execution_state.execution_index = (self.execution_state.execution_index or 0) + 1
        self.execution_state.total_iterations = (self.execution_state.total_iterations or 0) + 1

        if self.max_total_iterations is not None and self.execution_state.total_iterations > self.max_total_iterations:
            task.set_error("Max total iterations exceeded")
            task.update_status(TaskStatus("error"))
            return

        try:
            for si, step in enumerate(plan):
                for ni, node_name in enumerate(step.nodes):
                    if step.skipped[ni]:
                        continue
                    if self.execution_state.was_executed(node_name):
                        continue
                    node = self.nodes[node_name]
                    visits_key = f"__visits__:{node_name}"
                    visits = int(self.cache.get(visits_key, 0))
                    if node.node_config and node.node_config.max_visits is not None and visits >= node.node_config.max_visits:
                        step.skipped[ni] = True
                        continue

                    if node.node_config and node.node_config.condition:
                        cache_keys = set(self.cache.keys())
                        ok = FlowControlModule(name="__cond__", flow_config=FlowControlConfig(decisions=[])).evaluate_condition(
                            node.node_config.condition, self.cache, cache_keys
                        )
                        if not ok:
                            step.skipped[ni] = True
                            continue

                    self.cache[visits_key] = visits + 1

                    retries = 0
                    max_retries = node.node_config.max_retries if node.node_config else 0
                    while True:
                        try:
                            res = await self.run_node(node_name)
                            self.execution_state.mark_executed(si, ni)
                            if self.auto_snapshot and node.snapshot:
                                self.snapshot(task, node.snapshot.name)
                            break
                        except NonRetryableException as e:
                            task.set_error(str(e))
                            task.update_status(TaskStatus("error"))
                            raise
                        except Exception as e:
                            retries += 1
                            if not (node.node_config and node.node_config.retry_on_failure):
                                task.set_error(str(e))
                                task.update_status(TaskStatus("error"))
                                raise
                            if retries > max_retries:
                                task.set_error(str(e))
                                task.update_status(TaskStatus("error"))
                                raise
                            if node.node_config and node.node_config.retry_from:
                                self.mark_node_and_deps_as_skipped(node.node_config.retry_from)
                                break

            task.set_result(self.node_results)
            task.update_status(TaskStatus("completed"))
        except Exception as e:
            if task.error is None:
                task.set_error(str(e))
            if task.status.name != "error":
                task.update_status(TaskStatus("error"))