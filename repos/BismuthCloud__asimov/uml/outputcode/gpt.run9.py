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
        status: TaskStatus = TaskStatus.PENDING,
    ) -> None:
        super().__init__()
        self.error: Optional[str] = None
        self.id: Optional[UUID] = id or uuid4()
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
    ) -> None:
        super().__init__()
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
        return True

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Union[Dict[str, Any], AsyncGenerator]:
        raise NotImplementedError

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        cfg = self.config or ModuleConfig()
        async with semaphore:
            if cfg.timeout and cfg.timeout > 0:
                res = await asyncio.wait_for(self.process(cache, semaphore), timeout=cfg.timeout)
            else:
                res = await self.process(cache, semaphore)

        if inspect.isasyncgen(res):
            last: Any = None
            async for item in res:  # type: ignore[misc]
                last = item
            if isinstance(last, dict):
                return last
            return {"result": last}

        if isinstance(res, dict):
            return res
        return {"result": res}


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
        cfg = module.config
        if cfg and cfg.middlewares:
            result = self.apply_middlewares(cfg.middlewares, result, cache)
        return result

    async def run_parallel_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        tasks = [asyncio.create_task(self.run_module_with_concurrency_control(m, cache, semaphore)) for m in self.modules]
        results = await asyncio.gather(*tasks)
        combined: Dict[str, Any] = {}
        for m, r in zip(self.modules, results):
            combined[m.name] = r
        return combined

    async def run_sequential_modules(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        combined: Dict[str, Any] = {}
        for m in self.modules:
            r = await self.run_module_with_concurrency_control(m, cache, semaphore)
            combined[m.name] = r
            cfg = m.config
            if cfg and cfg.stop_on_success and m.is_success(r):
                break
        return combined

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
    ) -> None:
        super().__init__(name=name, modules=modules, node_config=node_config, type=type, config=config)
        self.dependencies: Optional[List[str]] = dependencies
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
    ) -> None:
        super().__init__()
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

    def _find_node(self, node_name: str) -> Optional[Tuple[int, int, ExecutionStep]]:
        if not self.current_plan:
            return None
        for si, step in enumerate(self.current_plan):
            for ni, n in enumerate(step.nodes):
                if n == node_name:
                    return si, ni, step
        return None

    def was_executed(self, node_name: str) -> bool:
        found = self._find_node(node_name)
        if not found:
            return False
        _, ni, step = found
        return bool(step.executed[ni])

    def was_skipped(self, node_name: str) -> bool:
        found = self._find_node(node_name)
        if not found:
            return False
        _, ni, step = found
        return bool(step.skipped[ni])


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
        env: Dict[str, Any] = {}
        for k in cache_keys:
            env[k] = cache.get(k)
        try:
            return bool(eval(condition, {"__builtins__": {}}, env))
        except Exception:
            return False

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        cache_keys = cache.keys()
        for decision in self.flow_config.decisions:
            if decision.condition is None:
                continue
            if self.evaluate_condition(decision.condition, cache, cache_keys):
                return {"next_node": decision.next_node, "decision": decision.metadata or {}}
        if self.flow_config.default is not None:
            return {"next_node": self.flow_config.default, "decision": {"default": True}}
        return {"next_node": None, "decision": {"default": True}}


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
        return ""


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
        system = self.system_description
        user = generation_input
        return await self.inference_client.generate(system=system, user=user)

    async def run(self, cache: Cache, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        self.set_attrs()
        choices = [d.next_node for d in self.flow_config.decisions]
        if self.flow_config.default is not None:
            choices.append(self.flow_config.default)

        if not choices:
            return {"next_node": None, "decision": {"default": True}}

        input_text = ""
        if self.input_var:
            v = cache.get(self.input_var)
            input_text = "" if v is None else str(v)

        prompt = {
            "input": input_text,
            "choices": choices,
        }
        generation_input = json.dumps(prompt, ensure_ascii=False)

        votes: List[str] = []
        async with semaphore:
            for _ in range(max(1, self.voters)):
                out = await self.gen(generation_input, cache)
                out = (out or "").strip()
                if out in choices:
                    votes.append(out)

        selected = self.most_common_string(votes)
        if selected is None:
            selected = self.flow_config.default if self.flow_config.default is not None else choices[0]
            return {"next_node": selected, "decision": {"default": True, "votes": votes}}
        return {"next_node": selected, "decision": {"votes": votes}}


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
        self.graph.setdefault(new_node, [])
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

    def compile_execution_plan(self) -> ExecutionPlan:
        if not self.nodes:
            return []
        indeg: Dict[str, int] = {n: 0 for n in self.nodes.keys()}
        for n, node in self.nodes.items():
            deps = node.dependencies or []
            for d in deps:
                if d in indeg:
                    indeg[n] += 1

        remaining: Set[str] = set(self.nodes.keys())
        plan: ExecutionPlan = []
        while remaining:
            ready = sorted([n for n in remaining if indeg.get(n, 0) == 0])
            if not ready:
                ready = sorted(list(remaining))
            step = ExecutionStep(ready)
            plan.append(step)
            for n in ready:
                remaining.remove(n)
                for child in (self.graph or {}).get(n, []):
                    if child in indeg:
                        indeg[child] = max(0, indeg[child] - 1)
        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        full = self.compile_execution_plan()
        if not full:
            return []
        flattened: List[str] = []
        for step in full:
            flattened.extend(step.nodes)
        if start_node not in flattened:
            return []
        idx = flattened.index(start_node)
        subset = flattened[idx:]
        return [ExecutionStep(subset)]

    def slice_before_node(self, execution_plan: List[dict], node: str) -> List[dict]:
        out: List[dict] = []
        for step in execution_plan:
            nodes = step.get("nodes", [])
            if node in nodes:
                break
            out.append(step)
        return out

    def is_success(self, result: Any) -> bool:
        if isinstance(result, dict) and "success" in result:
            return bool(result.get("success"))
        if isinstance(result, dict) and "status" in result:
            return str(result.get("status")).lower() in {"success", "ok", "passed", "true"}
        return result is not None

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
        ts = int(time.time() * 1000)
        safe_hint = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name_hint)[:80]
        snap_dir = base / f"{safe_hint}_{ts}"
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
            "node_results": dict(self.node_results or {}),
        }
        (snap_dir / "snapshot.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return snap_dir

    def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        snap_file = snapshot_dir / "snapshot.json"
        data = json.loads(snap_file.read_text(encoding="utf-8"))
        if self.cache is None:
            self.cache = Cache()
        self.cache.update(data.get("cache", {}))
        if self.node_results is None:
            self.node_results = {}
        self.node_results.update(data.get("node_results", {}))

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if not self.nodes or node_name not in self.nodes:
            raise KeyError(f"Unknown node: {node_name}")
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()
        assert self._semaphore is not None

        node = self.nodes[node_name]
        cfg = node.node_config or NodeConfig()

        if cfg.condition:
            cache_keys = self.cache.keys()
            ok = FlowControlModule(name="__cond__", flow_config=FlowControlConfig(decisions=[])).evaluate_condition(
                cfg.condition, self.cache, cache_keys
            )
            if not ok:
                if self.execution_state and self.execution_state.current_plan:
                    for step in self.execution_state.current_plan:
                        for i, n in enumerate(step.nodes):
                            if n == node_name:
                                step.skipped[i] = True
                return {"skipped": True, "reason": "condition"}

        retries = max(0, cfg.max_retries)
        attempt = 0
        last_exc: Optional[BaseException] = None
        while True:
            try:
                result = await node.run(self.cache, self._semaphore)
                self.node_results[node_name] = result
                if cfg.outputs:
                    for k in cfg.outputs:
                        if isinstance(result, dict) and k in result:
                            self.cache.set(k, result[k])
                return result
            except NonRetryableException as e:
                last_exc = e
                break
            except Exception as e:
                last_exc = e
                if not cfg.retry_on_failure or attempt >= retries:
                    break
                attempt += 1
                continue

        err = {"error": str(last_exc) if last_exc else "Unknown error"}
        self.node_results[node_name] = err
        return err

    async def run_task(self, task: Task) -> None:
        if self.cache is None:
            self.cache = Cache()
        if self.nodes is None:
            self.nodes = {}
        if self.graph is None:
            self.graph = {}
        if self.execution_state is None:
            self.execution_state = ExecutionState()

        self.set_semaphore()
        assert self._semaphore is not None

        task.update_status(TaskStatus.RUNNING)
        self.cache.set("task_objective", task.objective)
        self.cache.set("task_params", task.params or {})
        self.cache.set("task_type", task.type)

        plan = self.compile_execution_plan()
        self.execution_state.current_plan = plan
        if self.execution_state.execution_history is None:
            self.execution_state.execution_history = []
        self.execution_state.execution_history.append(plan)
        self.execution_state.execution_index = 0
        self.execution_state.total_iterations = 0

        try:
            for si, step in enumerate(plan):
                for ni, node_name in enumerate(step.nodes):
                    if step.skipped[ni]:
                        continue
                    if self.execution_state.total_iterations is not None:
                        self.execution_state.total_iterations += 1
                        if self.max_total_iterations is not None and self.execution_state.total_iterations > self.max_total_iterations:
                            raise RuntimeError("Max total iterations exceeded")

                    res = await self.run_node(node_name)
                    self.execution_state.mark_executed(si, ni)

                    if self.auto_snapshot:
                        self.snapshot(task, f"node_{node_name}")

                    if isinstance(res, dict) and res.get("error"):
                        self.cache.set(self.error_mailbox, res)
                    else:
                        self.cache.set(self.output_mailbox, res)

            task.set_result(self.node_results)
            task.update_status(TaskStatus.SUCCESS)
        except Exception as e:
            task.set_error(str(e))
            task.update_status(TaskStatus.FAILED)
            if self.cache is not None:
                self.cache.set(self.error_mailbox, {"error": str(e)})
            if self.auto_snapshot:
                self.snapshot(task, "task_failed")


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