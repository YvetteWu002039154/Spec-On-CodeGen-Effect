import asyncio
import json
import pathlib
import uuid
from abc import abstractmethod
from collections import Counter
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
)
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# asimov/asimov_base.py
# ---------------------------------------------------------------------------

class AsimovBase(BaseModel):
    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# asimov/constants.py
# ---------------------------------------------------------------------------

class ModelFamily(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    COHERE = "cohere"


# ---------------------------------------------------------------------------
# asimov/graph/tasks.py
# ---------------------------------------------------------------------------

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(AsimovBase):
    id: Optional[UUID] = Field(default_factory=uuid.uuid4)
    objective: str
    type: str = "task"
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    model_config = {"arbitrary_types_allowed": True}

    def set_error(self, error: str) -> None:
        self.error = error
        self.status = TaskStatus.FAILED

    def set_result(self, result: Any) -> None:
        self.result = result
        self.status = TaskStatus.COMPLETE

    def update_status(self, status: TaskStatus) -> None:
        self.status = status


# ---------------------------------------------------------------------------
# asimov/graph/__init__.py  (core graph types)
# ---------------------------------------------------------------------------

class ModuleType(Enum):
    EXECUTOR = "executor"
    FLOW_CONTROL = "flow_control"
    COMPOSITE = "composite"
    SUB_AGENT = "sub_agent"


class SnapshotControl(Enum):
    BEFORE = "before"
    AFTER = "after"
    BOTH = "both"
    NONE = "none"


class NonRetryableException(Exception):
    pass


class Cache:
    """Simple in-memory cache used throughout the graph."""

    def __init__(self):
        self._data: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def keys(self) -> Set[str]:
        return set(self._data.keys())

    def update(self, data: Dict[str, Any]) -> None:
        self._data.update(data)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)


class Middleware(AsimovBase):
    async def process(self, data: Dict[str, Any], cache: Cache) -> Dict[str, Any]:
        return data


class ModuleConfig(AsimovBase):
    context: Optional[Dict[str, Any]] = None
    middlewares: Optional[List[Middleware]] = None
    stop_on_success: bool = False
    timeout: float = 300.0


class NodeConfig(AsimovBase):
    condition: Optional[str] = None
    inputs: Optional[List[str]] = None
    outputs: Optional[List[str]] = None
    max_retries: int = 0
    max_visits: Optional[int] = None
    parallel: bool = False
    retry_on_failure: bool = False
    retry_from: Optional[str] = None


class AgentModule(AsimovBase):
    name: str
    type: Optional[ModuleType] = None
    config: Optional[ModuleConfig] = None
    container: Optional[Any] = None  # 'CompositeModule'
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = 0
    input_mailboxes: Optional[List[str]] = None
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = False

    def is_success(self, result: Dict[str, Any]) -> bool:
        if result is None:
            return False
        status = result.get("status", "")
        if isinstance(status, str):
            return status.lower() not in ("error", "failed", "failure")
        return True

    @abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Awaitable[dict[str, Any]] | AsyncGenerator:
        raise NotImplementedError

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        timeout = 300.0
        if self.config and self.config.timeout:
            timeout = self.config.timeout

        result = await asyncio.wait_for(
            self._run_process(cache, semaphore), timeout=timeout
        )

        if self.executions is None:
            self.executions = 0
        self.executions += 1

        return result

    async def _run_process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        result = self.process(cache, semaphore)
        if asyncio.iscoroutine(result):
            return await result
        elif hasattr(result, "__aiter__"):
            collected = {}
            async for chunk in result:
                if isinstance(chunk, dict):
                    collected.update(chunk)
            return collected
        else:
            return await result


class CompositeModule(AgentModule):
    modules: List[AgentModule] = Field(default_factory=list)
    node_config: Optional[NodeConfig] = None

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            return await self.run_parallel_modules(cache, semaphore)
        return await self.run_sequential_modules(cache, semaphore)

    async def apply_middlewares(
        self,
        middlewares: List[Middleware],
        data: Dict[str, Any],
        cache: Cache,
    ) -> Dict[str, Any]:
        for mw in middlewares:
            data = await mw.process(data, cache)
        return data

    async def run_module_with_concurrency_control(
        self,
        module: AgentModule,
        cache: Cache,
        semaphore: asyncio.Semaphore,
    ) -> Dict[str, Any]:
        async with semaphore:
            return await module.run(cache, semaphore)

    async def run_parallel_modules(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        tasks = [
            self.run_module_with_concurrency_control(m, cache, semaphore)
            for m in self.modules
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        combined: Dict[str, Any] = {}
        for r in results:
            if isinstance(r, Exception):
                raise r
            if isinstance(r, dict):
                combined.update(r)
        return combined

    async def run_sequential_modules(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        combined: Dict[str, Any] = {}
        for module in self.modules:
            result = await module.run(cache, semaphore)
            if isinstance(result, dict):
                combined.update(result)
            if (
                self.node_config is None
                or (module.config and module.config.stop_on_success and module.is_success(result))
            ):
                pass
        return combined

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.process(cache, semaphore)


class FlowDecision(AsimovBase):
    next_node: str
    condition: Optional[str] = None
    condition_variables: Optional[List[str]] = None
    cleanup_on_jump: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None


class FlowControlConfig(AsimovBase):
    decisions: Sequence[FlowDecision] = Field(default_factory=list)
    default: Optional[str] = None
    cleanup_on_default: bool = False


class FlowControlModule(AgentModule):
    flow_config: Optional[FlowControlConfig] = None

    def evaluate_condition(
        self, condition: str, cache: Cache, cache_keys: set[str]
    ) -> bool:
        context = {k: cache.get(k) for k in cache_keys}
        try:
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception:
            return False

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.flow_config is None:
            return {"next_node": None}

        cache_keys = cache.keys()

        for decision in self.flow_config.decisions:
            if decision.condition is None:
                return {"next_node": decision.next_node, "decision": decision}
            if self.evaluate_condition(decision.condition, cache, cache_keys):
                if decision.cleanup_on_jump and decision.condition_variables:
                    for var in decision.condition_variables:
                        cache.delete(var)
                return {"next_node": decision.next_node, "decision": decision}

        if self.flow_config.default:
            if self.flow_config.cleanup_on_default:
                for decision in self.flow_config.decisions:
                    if decision.condition_variables:
                        for var in decision.condition_variables:
                            cache.delete(var)
            return {"next_node": self.flow_config.default}

        return {"next_node": None}


class ExecutionStep(AsimovBase):
    nodes: List[str] = Field(default_factory=list)
    executed: List[bool] = Field(default_factory=list)
    skipped: List[bool] = Field(default_factory=list)


ExecutionPlan = List[ExecutionStep]


class ExecutionState(AsimovBase):
    current_plan: Optional[ExecutionPlan] = None
    execution_history: Optional[List[ExecutionPlan]] = None
    execution_index: Optional[int] = 0
    total_iterations: Optional[int] = 0

    def mark_executed(self, step_index: int, node_index: int) -> None:
        if self.current_plan and step_index < len(self.current_plan):
            step = self.current_plan[step_index]
            if node_index < len(step.executed):
                step.executed[node_index] = True

    def was_executed(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan:
            for i, node in enumerate(step.nodes):
                if node == node_name and i < len(step.executed) and step.executed[i]:
                    return True
        if self.execution_history:
            for plan in self.execution_history:
                for step in plan:
                    for i, node in enumerate(step.nodes):
                        if node == node_name and i < len(step.executed) and step.executed[i]:
                            return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if not self.current_plan:
            return False
        for step in self.current_plan:
            for i, node in enumerate(step.nodes):
                if node == node_name and i < len(step.skipped) and step.skipped[i]:
                    return True
        return False


class NodeVisitTracker:
    def __init__(self):
        self._visits: Dict[str, int] = {}

    def increment(self, node_name: str) -> int:
        self._visits[node_name] = self._visits.get(node_name, 0) + 1
        return self._visits[node_name]

    def get(self, node_name: str) -> int:
        return self._visits.get(node_name, 0)


class Node(CompositeModule):
    dependencies: Optional[List[str]] = None
    modules: List[AgentModule] = Field(default_factory=list)
    node_config: Optional[NodeConfig] = None
    snapshot: Optional[SnapshotControl] = None
    type: Optional[ModuleType] = None
    _nodes: Optional[Dict[str, "Node"]] = None

    def cancel_gen(self, agen) -> None:
        if hasattr(agen, "aclose"):
            asyncio.ensure_future(agen.aclose())

    def cleanup(self) -> None:
        pass

    def get_nodes(self) -> Optional[Dict[str, "Node"]]:
        return self._nodes

    def set_nodes(self, nodes: Dict[str, "Node"]) -> None:
        self._nodes = nodes


# ---------------------------------------------------------------------------
# asimov/executors/executor.py
# ---------------------------------------------------------------------------

class Executor(AgentModule):
    type: Optional[ModuleType] = ModuleType.EXECUTOR

    @abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# asimov/graph/agent_directed_flow.py
# ---------------------------------------------------------------------------

class InferenceClient:
    async def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        return ""


class Example(AsimovBase):
    message: str
    choices: List[Dict[str, str]] = Field(default_factory=list)
    choice: str
    reasoning: str


class AgentDrivenFlowDecision(FlowDecision):
    examples: Optional[List[Example]] = None


class AgentDrivenFlowControlConfig(FlowControlConfig):
    decisions: Sequence[AgentDrivenFlowDecision] = Field(default_factory=list)
    default: Optional[str] = None


class AgentDirectedFlowControl(FlowControlModule):
    flow_config: Optional[AgentDrivenFlowControlConfig] = None
    inference_client: Optional[Any] = None
    system_description: str = ""
    input_var: Optional[str] = None
    use_historicals: Optional[bool] = True
    voters: int = 1

    def set_attrs(self) -> None:
        pass

    def most_common_string(self, string_list: List[str]) -> str:
        if not string_list:
            return ""
        counter = Counter(string_list)
        return counter.most_common(1)[0][0]

    async def gen(self, generation_input: Any, cache: Cache) -> str:
        if self.inference_client is None:
            return ""

        prompt = self._build_prompt(generation_input)
        response = await self.inference_client.generate(
            prompt=prompt, system=self.system_description
        )
        return response

    def _build_prompt(self, generation_input: Any) -> str:
        if self.flow_config is None:
            return str(generation_input)

        choices_text = "\n".join(
            f"- {d.next_node}" for d in self.flow_config.decisions
        )
        if self.flow_config.default:
            choices_text += f"\n- {self.flow_config.default}"

        examples_text = ""
        for decision in self.flow_config.decisions:
            if isinstance(decision, AgentDrivenFlowDecision) and decision.examples:
                for ex in decision.examples:
                    examples_text += (
                        f"Message: {ex.message}\n"
                        f"Reasoning: {ex.reasoning}\n"
                        f"Choice: {ex.choice}\n\n"
                    )

        prompt = (
            f"Given the following input, choose the most appropriate next step.\n\n"
            f"Input: {generation_input}\n\n"
            f"Available choices:\n{choices_text}\n\n"
        )
        if examples_text:
            prompt += f"Examples:\n{examples_text}\n"
        prompt += "Respond with only the name of the chosen next step."
        return prompt

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.flow_config is None:
            return {"next_node": None}

        generation_input = None
        if self.input_var:
            generation_input = cache.get(self.input_var)

        votes = []
        for _ in range(self.voters):
            vote = await self.gen(generation_input, cache)
            if vote:
                votes.append(vote.strip())

        chosen = self.most_common_string(votes) if votes else None

        if chosen:
            for decision in self.flow_config.decisions:
                if decision.next_node == chosen:
                    return {"next_node": decision.next_node, "decision": decision}

        if self.flow_config.default:
            return {"next_node": self.flow_config.default}

        return {"next_node": None}

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


# ---------------------------------------------------------------------------
# asimov/graph/agent.py  (Agent)
# ---------------------------------------------------------------------------

class Agent(AsimovBase):
    nodes: Optional[Dict[str, Node]] = None
    graph: Optional[Dict[str, List[str]]] = None
    node_results: Optional[Dict[str, Any]] = None
    execution_state: Optional[ExecutionState] = None
    cache: Optional[Cache] = None
    output_mailbox: str = "output"
    error_mailbox: str = "error"
    max_concurrent_tasks: Optional[int] = None
    max_total_iterations: Optional[int] = None
    auto_snapshot: bool = False
    _semaphore: Optional[asyncio.Semaphore] = None
    _visit_tracker: Optional[NodeVisitTracker] = None

    model_config = {"arbitrary_types_allowed": True}

    def set_semaphore(self) -> None:
        limit = self.max_concurrent_tasks or 10
        self._semaphore = asyncio.Semaphore(limit)

    def add_node(self, node: Node) -> None:
        if self.nodes is None:
            self.nodes = {}
        self.nodes[node.name] = node
        if self.graph is None:
            self.graph = {}
        if node.name not in self.graph:
            self.graph[node.name] = []
        if node.dependencies:
            for dep in node.dependencies:
                if dep not in self.graph:
                    self.graph[dep] = []
                if node.name not in self.graph[dep]:
                    self.graph[dep].append(node.name)

    def add_multiple_nodes(self, nodes: List[Node]) -> None:
        for node in nodes:
            self.add_node(node)

    def update_dependencies(self, parent_node: str, new_node: str) -> None:
        if self.graph is None:
            self.graph = {}
        if parent_node not in self.graph:
            self.graph[parent_node] = []
        if new_node not in self.graph[parent_node]:
            self.graph[parent_node].append(new_node)

    def compile_execution_plan(self) -> ExecutionPlan:
        if not self.nodes:
            return []

        graph = self.graph or {}
        in_degree: Dict[str, int] = {n: 0 for n in self.nodes}
        for node_name, deps in graph.items():
            if node_name not in in_degree:
                in_degree[node_name] = 0
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] = in_degree.get(dep, 0) + 1

        queue = [n for n, d in in_degree.items() if d == 0]
        plan: ExecutionPlan = []

        while queue:
            step_nodes = list(queue)
            queue = []
            step = ExecutionStep(
                nodes=step_nodes,
                executed=[False] * len(step_nodes),
                skipped=[False] * len(step_nodes),
            )
            plan.append(step)
            for node_name in step_nodes:
                for successor in graph.get(node_name, []):
                    in_degree[successor] -= 1
                    if in_degree[successor] == 0:
                        queue.append(successor)

        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        full_plan = self.compile_execution_plan()
        return self.slice_before_node(full_plan, start_node)

    def slice_before_node(
        self, execution_plan: List[ExecutionStep], node: str
    ) -> List[ExecutionStep]:
        for i, step in enumerate(execution_plan):
            if node in step.nodes:
                return execution_plan[i:]
        return execution_plan

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        if not self.graph:
            return ()
        visited: Set[str] = set()
        stack = [node_name]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for successor in self.graph.get(current, []):
                stack.append(successor)
        visited.discard(node_name)
        return tuple(visited)

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if self.execution_state is None or self.execution_state.current_plan is None:
            return
        deps = self.get_dependent_chains(node_name)
        to_skip = {node_name} | set(deps)
        for step in self.execution_state.current_plan:
            for i, n in enumerate(step.nodes):
                if n in to_skip:
                    if i < len(step.skipped):
                        step.skipped[i] = True

    def is_success(self, result: Any) -> bool:
        if result is None:
            return False
        if isinstance(result, dict):
            status = result.get("status", "")
            if isinstance(status, str):
                return status.lower() not in ("error", "failed", "failure")
        return True

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if not self.nodes or node_name not in self.nodes:
            raise ValueError(f"Node '{node_name}' not found")

        node = self.nodes[node_name]
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()

        node.set_nodes(self.nodes)

        node_config = node.node_config
        max_retries = 0
        retry_on_failure = False
        max_visits = None

        if node_config:
            max_retries = node_config.max_retries
            retry_on_failure = node_config.retry_on_failure
            max_visits = node_config.max_visits

        if self._visit_tracker is None:
            self._visit_tracker = NodeVisitTracker()

        visit_count = self._visit_tracker.increment(node_name)
        if max_visits is not None and visit_count > max_visits:
            return {"status": "skipped", "reason": "max_visits exceeded"}

        attempts = 0
        last_result: Dict[str, Any] = {}

        while True:
            try:
                result = await node.run(self.cache, self._semaphore)
                last_result = result or {}

                if self.node_results is None:
                    self.node_results = {}
                self.node_results[node_name] = last_result

                if isinstance(last_result, dict):
                    self.cache.update(
                        {k: v for k, v in last_result.items() if k != "status"}
                    )

                return last_result

            except NonRetryableException:
                raise
            except Exception as e:
                attempts += 1
                if retry_on_failure and attempts <= max_retries:
                    continue
                raise

    async def run_task(self, task: Task) -> None:
        task.update_status(TaskStatus.RUNNING)

        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()
        if self._visit_tracker is None:
            self._visit_tracker = NodeVisitTracker()

        self.cache.set("task", task)
        if task.params:
            self.cache.update(task.params)

        plan = self.compile_execution_plan()
        self.execution_state = ExecutionState(
            current_plan=plan,
            execution_history=[],
            execution_index=0,
            total_iterations=0,
        )

        iteration = 0
        step_index = 0

        try:
            while step_index < len(plan):
                if (
                    self.max_total_iterations is not None
                    and iteration >= self.max_total_iterations
                ):
                    break

                step = plan[step_index]
                next_step_override: Optional[str] = None

                if self.execution_state.current_plan[step_index].nodes[0] if self.execution_state.current_plan else None:
                    pass

                for node_idx, node_name in enumerate(step.nodes):
                    if step.skipped[node_idx]:
                        continue

                    node = self.nodes.get(node_name) if self.nodes else None
                    if node is None:
                        continue

                    node_config = node.node_config
                    if node_config and node_config.condition:
                        cache_keys = self.cache.keys()
                        try:
                            context = {k: self.cache.get(k) for k in cache_keys}
                            cond_result = eval(
                                node_config.condition,
                                {"__builtins__": {}},
                                context,
                            )
                            if not cond_result:
                                step.skipped[node_idx] = True
                                self.mark_node_and_deps_as_skipped(node_name)
                                continue
                        except Exception:
                            pass

                    if self.auto_snapshot:
                        await self.snapshot(task, f"before_{node_name}")

                    result = await self.run_node(node_name)
                    step.executed[node_idx] = True
                    self.execution_state.mark_executed(step_index, node_idx)

                    if self.auto_snapshot:
                        await self.snapshot(task, f"after_{node_name}")

                    if isinstance(result, dict) and "next_node" in result:
                        next_node = result["next_node"]
                        if next_node:
                            next_step_override = next_node

                iteration += 1
                if self.execution_state.total_iterations is not None:
                    self.execution_state.total_iterations += 1

                if next_step_override:
                    found = False
                    for si, s in enumerate(plan):
                        if next_step_override in s.nodes:
                            step_index = si
                            found = True
                            break
                    if not found:
                        step_index += 1
                else:
                    step_index += 1

            output = self.cache.get(self.output_mailbox)
            if output is not None:
                task.set_result(output)
            else:
                task.set_result(self.node_results)

        except Exception as e:
            error_msg = str(e)
            self.cache.set(self.error_mailbox, error_msg)
            task.set_error(error_msg)
            raise

    async def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        import tempfile
        import os

        snapshot_dir = pathlib.Path(tempfile.mkdtemp())
        snapshot_data = {
            "task_id": str(task.id),
            "name_hint": name_hint,
            "node_results": self.node_results or {},
            "cache": self.cache.to_dict() if self.cache else {},
            "execution_state": (
                self.execution_state.model_dump()
                if self.execution_state
                else None
            ),
        }

        snapshot_file = snapshot_dir / f"{name_hint}.json"
        with open(snapshot_file, "w") as f:
            json.dump(snapshot_data, f, default=str)

        return snapshot_dir

    async def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        snapshot_files = list(snapshot_dir.glob("*.json"))
        if not snapshot_files:
            raise ValueError(f"No snapshot files found in {snapshot_dir}")

        snapshot_file = sorted(snapshot_files)[-1]
        with open(snapshot_file, "r") as f:
            snapshot_data = json.load(f)

        if self.cache is None:
            self.cache = Cache()

        cache_data = snapshot_data.get("cache", {})
        self.cache.update(cache_data)

        self.node_results = snapshot_data.get("node_results", {})

        exec_state_data = snapshot_data.get("execution_state")
        if exec_state_data:
            self.execution_state = ExecutionState(**exec_state_data)


__all__ = [
    "AsimovBase",
    "ModelFamily",
    "TaskStatus",
    "Task",
    "ModuleType",
    "SnapshotControl",
    "NonRetryableException",
    "Cache",
    "Middleware",
    "ModuleConfig",
    "NodeConfig",
    "AgentModule",
    "CompositeModule",
    "FlowDecision",
    "FlowControlConfig",
    "FlowControlModule",
    "ExecutionStep",
    "ExecutionPlan",
    "ExecutionState",
    "Node",
    "Executor",
    "Example",
    "AgentDrivenFlowDecision",
    "AgentDrivenFlowControlConfig",
    "AgentDirectedFlowControl",
    "Agent",
    "InferenceClient",
]