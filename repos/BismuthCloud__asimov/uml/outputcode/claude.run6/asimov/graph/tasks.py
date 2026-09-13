# ---------------------------------------------------------------------------

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


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
    SUBAGENT = "subagent"


class SnapshotControl(Enum):
    BEFORE = "before"
    AFTER = "after"
    BOTH = "both"
    NONE = "none"


class NonRetryableException(Exception):
    pass


class ModuleConfig(AsimovBase):
    context: Optional[Dict[str, Any]] = None
    middlewares: Optional[List["Middleware"]] = None
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


class Middleware(AsimovBase):
    async def process(self, data: Dict[str, Any], cache: Any) -> Dict[str, Any]:
        return data


class FlowDecision(AsimovBase):
    next_node: str
    condition: Optional[str] = None
    condition_variables: Optional[List[str]] = None
    cleanup_on_jump: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class FlowControlConfig(AsimovBase):
    decisions: Sequence[FlowDecision] = []
    default: Optional[str] = None
    cleanup_on_default: bool = False


class ExecutionStep(BaseModel):
    nodes: List[str] = Field(default_factory=list)
    executed: List[bool] = Field(default_factory=list)
    skipped: List[bool] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


ExecutionPlan = List[ExecutionStep]


class ExecutionState(AsimovBase):
    current_plan: Optional[ExecutionPlan] = None
    execution_history: Optional[List[ExecutionPlan]] = None
    execution_index: Optional[int] = None
    total_iterations: Optional[int] = None

    def mark_executed(self, step_index: int, node_index: int) -> None:
        if self.current_plan is None:
            return
        if 0 <= step_index < len(self.current_plan):
            step = self.current_plan[step_index]
            if 0 <= node_index < len(step.executed):
                step.executed[node_index] = True

    def was_executed(self, node_name: str) -> bool:
        if self.current_plan is None:
            return False
        for step in self.current_plan:
            for i, name in enumerate(step.nodes):
                if name == node_name and i < len(step.executed) and step.executed[i]:
                    return True
        return False

    def was_skipped(self, node_name: str) -> bool:
        if self.current_plan is None:
            return False
        for step in self.current_plan:
            for i, name in enumerate(step.nodes):
                if name == node_name and i < len(step.skipped) and step.skipped[i]:
                    return True
        return False


# ---------------------------------------------------------------------------
# Cache placeholder (used throughout)
# ---------------------------------------------------------------------------

class Cache:
    def __init__(self):
        self._store: Dict[str, Any] = {}

    async def get(self, key: str) -> Any:
        return self._store.get(key)

    async def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def keys(self):
        return set(self._store.keys())


# ---------------------------------------------------------------------------
# AgentModule
# ---------------------------------------------------------------------------

class AgentModule(AsimovBase):
    name: str = ""
    type: Optional[ModuleType] = None
    config: Optional[ModuleConfig] = None
    dependencies: Optional[List[str]] = None
    executions: Optional[int] = None
    input_mailboxes: Optional[List[str]] = None
    output_mailbox: Optional[str] = None
    trace: Optional[bool] = None
    container: Optional[Any] = None  # forward ref to CompositeModule

    model_config = {"arbitrary_types_allowed": True}

    def is_success(self, result: Dict[str, Any]) -> bool:
        if result is None:
            return False
        return result.get("status") != "failure"

    @abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Awaitable[Dict[str, Any]] | AsyncGenerator:
        raise NotImplementedError

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        result = await self.process(cache, semaphore)
        if self.executions is not None:
            self.executions += 1
        else:
            self.executions = 1
        return result


# ---------------------------------------------------------------------------
# CompositeModule
# ---------------------------------------------------------------------------

class CompositeModule(AgentModule):
    modules: List[AgentModule] = Field(default_factory=list)
    node_config: Optional[NodeConfig] = None

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
        results = await asyncio.gather(*tasks)
        combined: Dict[str, Any] = {}
        for r in results:
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
                if self.node_config and self.node_config.parallel is False:
                    config = module.config
                    if config and config.stop_on_success and module.is_success(result):
                        break
        return combined

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.node_config and self.node_config.parallel:
            result = await self.run_parallel_modules(cache, semaphore)
        else:
            result = await self.run_sequential_modules(cache, semaphore)

        # Apply middlewares if any module has them
        for module in self.modules:
            if module.config and module.config.middlewares:
                result = await self.apply_middlewares(
                    module.config.middlewares, result, cache
                )
        return result

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class Node(CompositeModule):
    dependencies: Optional[List[str]] = None
    modules: Optional[List[AgentModule]] = Field(default_factory=list)
    node_config: Optional[NodeConfig] = None
    snapshot: Optional[SnapshotControl] = None
    type: Optional[ModuleType] = None
    _nodes: Optional[Dict[str, "Node"]] = None

    model_config = {"arbitrary_types_allowed": True}

    def get_nodes(self) -> Optional[Dict[str, "Node"]]:
        return self._nodes

    def set_nodes(self, nodes: Dict[str, "Node"]) -> None:
        self._nodes = nodes

    async def cancel_gen(self, agen: AsyncGenerator) -> None:
        await agen.aclose()

    async def cleanup(self) -> None:
        pass

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.modules is None:
            return {}
        if self.node_config and self.node_config.parallel:
            result = await self.run_parallel_modules(cache, semaphore)
        else:
            result = await self.run_sequential_modules(cache, semaphore)
        return result

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


# ---------------------------------------------------------------------------
# FlowControlModule
# ---------------------------------------------------------------------------

class FlowControlModule(AgentModule):
    flow_config: Optional[FlowControlConfig] = None

    async def evaluate_condition(
        self, condition: str, cache: Cache, cache_keys: set
    ) -> bool:
        context: Dict[str, Any] = {}
        for key in cache_keys:
            val = await cache.get(key)
            context[key] = val
        try:
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception:
            return False

    async def run(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        if self.flow_config is None:
            return {"next_node": None}

        cache_keys = cache.keys()

        for decision in self.flow_config.decisions:
            if decision.condition is None:
                return {"next_node": decision.next_node}
            condition_met = await self.evaluate_condition(
                decision.condition, cache, cache_keys
            )
            if condition_met:
                return {"next_node": decision.next_node}

        if self.flow_config.default is not None:
            return {"next_node": self.flow_config.default}

        return {"next_node": None}

    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        return await self.run(cache, semaphore)


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class Executor(AgentModule):
    type: Optional[ModuleType] = ModuleType.EXECUTOR

    @abstractmethod
    async def process(
        self, cache: Cache, semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Agent
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
        if self.nodes is None or self.graph is None:
            return []

        in_degree: Dict[str, int] = {name: 0 for name in self.nodes}
        for node_name, deps in self.graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        plan: ExecutionPlan = []
        visited: set = set()
        queue = [n for n, d in in_degree.items() if d == 0]

        while queue:
            step_nodes = sorted(queue)
            step = ExecutionStep(
                nodes=step_nodes,
                executed=[False] * len(step_nodes),
                skipped=[False] * len(step_nodes),
            )
            plan.append(step)
            next_queue = []
            for node_name in step_nodes:
                visited.add(node_name)
                for child in self.graph.get(node_name, []):
                    in_degree[child] -= 1
                    if in_degree[child] == 0 and child not in visited:
                        next_queue.append(child)
            queue = next_queue

        return plan

    def compile_execution_plan_from(self, start_node: str) -> ExecutionPlan:
        full_plan = self.compile_execution_plan()
        return self.slice_before_node(full_plan, start_node)

    def slice_before_node(
        self, execution_plan: List[ExecutionStep], node: str
    ) -> List[ExecutionStep]:
        result = []
        for step in execution_plan:
            if node in step.nodes:
                idx = step.nodes.index(node)
                remaining_nodes = step.nodes[idx:]
                new_step = ExecutionStep(
                    nodes=remaining_nodes,
                    executed=[False] * len(remaining_nodes),
                    skipped=[False] * len(remaining_nodes),
                )
                result.append(new_step)
                break
            result.append(step)
        return result

    def get_dependent_chains(self, node_name: str) -> Tuple[str, ...]:
        if self.graph is None:
            return ()
        visited: set = set()
        stack = [node_name]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for child in self.graph.get(current, []):
                stack.append(child)
        visited.discard(node_name)
        return tuple(visited)

    def mark_node_and_deps_as_skipped(self, node_name: str) -> None:
        if self.execution_state is None or self.execution_state.current_plan is None:
            return
        deps = self.get_dependent_chains(node_name)
        to_skip = {node_name} | set(deps)
        for step in self.execution_state.current_plan:
            for i, name in enumerate(step.nodes):
                if name in to_skip:
                    if i < len(step.skipped):
                        step.skipped[i] = True

    def is_success(self, result: Any) -> bool:
        if result is None:
            return False
        if isinstance(result, dict):
            return result.get("status") != "failure"
        return True

    async def run_node(self, node_name: str) -> Dict[str, Any]:
        if self.nodes is None or node_name not in self.nodes:
            raise ValueError(f"Node '{node_name}' not found")
        node = self.nodes[node_name]
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()
        result = await node.run(self.cache, self._semaphore)
        if self.node_results is None:
            self.node_results = {}
        self.node_results[node_name] = result
        return result

    async def run_task(self, task: Task) -> None:
        task.update_status(TaskStatus.RUNNING)
        if self.cache is None:
            self.cache = Cache()
        if self._semaphore is None:
            self.set_semaphore()

        await self.cache.set("task", task)
        await self.cache.set("objective", task.objective)
        if task.params:
            for k, v in task.params.items():
                await self.cache.set(k, v)

        plan = self.compile_execution_plan()
        self.execution_state = ExecutionState(
            current_plan=plan,
            execution_history=[],
            execution_index=0,
            total_iterations=0,
        )

        if self.node_results is None:
            self.node_results = {}

        try:
            iteration = 0
            step_index = 0
            while step_index < len(plan):
                if (
                    self.max_total_iterations is not None
                    and iteration >= self.max_total_iterations
                ):
                    break
                step = plan[step_index]
                node_tasks = []
                for node_index, node_name in enumerate(step.nodes):
                    if step.skipped[node_index]:
                        continue
                    node_tasks.append((node_index, node_name))

                if step.nodes and all(
                    self.nodes[n].node_config and self.nodes[n].node_config.parallel
                    for n in step.nodes
                    if n in (self.nodes or {})
                ):
                    results = await asyncio.gather(
                        *[self.run_node(n) for _, n in node_tasks]
                    )
                    for (node_index, node_name), result in zip(node_tasks, results):
                        self.execution_state.mark_executed(step_index, node_index)
                        self.node_results[node_name] = result
                else:
                    for node_index, node_name in node_tasks:
                        result = await self.run_node(node_name)
                        self.execution_state.mark_executed(step_index, node_index)
                        self.node_results[node_name] = result

                        if isinstance(result, dict) and "next_node" in result:
                            next_node = result["next_node"]
                            if next_node and self.nodes and next_node in self.nodes:
                                new_plan = self.compile_execution_plan_from(next_node)
                                self.execution_state.current_plan = new_plan
                                plan = new_plan
                                step_index = 0
                                iteration += 1
                                if self.execution_state.total_iterations is not None:
                                    self.execution_state.total_iterations += 1
                                break
                        else:
                            step_index += 1
                            iteration += 1
                            if self.execution_state.total_iterations is not None:
                                self.execution_state.total_iterations += 1
                            continue
                continue

            output = await self.cache.get(self.output_mailbox)
            if output is not None:
                task.set_result(output)
            else:
                task.set_result(self.node_results)
        except Exception as e:
            error_msg = str(e)
            await self.cache.set(self.error_mailbox, error_msg)
            task.set_error(error_msg)

    async def snapshot(self, task: Task, name_hint: str) -> pathlib.Path:
        snapshot_dir = pathlib.Path(f"snapshots/{task.id}/{name_hint}")
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        state_data = {
            "task_id": str(task.id),
            "task_objective": task.objective,
            "task_status": task.status.value,
            "node_results": self.node_results or {},
            "execution_state": (
                self.execution_state.model_dump()
                if self.execution_state
                else None
            ),
        }

        state_file = snapshot_dir / "state.json"
        with open(state_file, "w") as f:
            json.dump(state_data, f, default=str)

        return snapshot_dir

    async def run_from_snapshot(self, snapshot_dir: pathlib.Path) -> None:
        state_file = snapshot_dir / "state.json"
        if not state_file.exists():
            raise FileNotFoundError(f"Snapshot state file not found: {state_file}")

        with open(state_file, "r") as f:
            state_data = json.load(f)

        if self.cache is None:
            self.cache = Cache()

        self.node_results = state_data.get("node_results", {})

        execution_state_data = state_data.get("execution_state")
        if execution_state_data:
            self.execution_state = ExecutionState(**execution_state_data)


# ---------------------------------------------------------------------------
