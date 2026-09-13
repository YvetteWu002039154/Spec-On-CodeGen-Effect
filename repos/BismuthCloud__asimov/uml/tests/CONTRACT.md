# Structural contract — `asimov` (BismuthCloud) **UML track**

Reference: origin repo `asimov-main/asimov/` — the modules the class diagram was
extracted from: `asimov_base.py` (the pydantic `AsimovBase`), `constants.py`
(`ModelFamily`), `graph/tasks.py` (`Task` / `TaskStatus`), `graph/__init__.py`
(the graph-primitive family — `Agent`, `AgentModule`, `CompositeModule`, `Node`,
`FlowControl*`, `ModuleType`, `NodeConfig`, …) and `executors/executor.py`
(`Executor`).

This contract is derived from the **UML class diagram**
(`uml/input/classes.puml`, a pyreverse extraction of the origin) and grounded in
that origin code. A class diagram records *structure*, not runtime behavior, so
the pinned facts are the three things the diagram actually draws:

1. **Inheritance links** — `Child --|> Parent`.
2. **Association links** — `A --* B : attr` / `A --o B : attr` (an attribute of
   `A` is typed as `B`).
3. **Methods under a class** — e.g. the method set drawn under `Agent`.

## Diagram fact → origin grounding

| Diagram fact | Origin evidence |
|---|---|
| `AgentModule ➝ AsimovBase` | `class AgentModule(AsimovBase)` (`graph/__init__.py` L69) |
| `Agent ➝ AsimovBase` | `class Agent(AsimovBase)` (`graph/__init__.py` L376) |
| `CompositeModule ➝ AgentModule` | `class CompositeModule(AgentModule)` (`graph/__init__.py` L217) |
| `Node ➝ CompositeModule` | `class Node(CompositeModule)` (`graph/__init__.py` L311) |
| `FlowControlModule ➝ AgentModule` | `class FlowControlModule(AgentModule)` (`graph/__init__.py` L127) |
| `Task ➝ AsimovBase` | `class Task(AsimovBase)` (`graph/tasks.py` L16) |
| `ModuleType --* AgentModule : type` | `type: ModuleType` (`graph/__init__.py` L71) |
| `TaskStatus --o Task : status` | `status: TaskStatus = TaskStatus.WAITING` (`graph/tasks.py` L21) |
| `NodeConfig --* CompositeModule : node_config` | `node_config: NodeConfig` (`graph/__init__.py` L219) |
| `Agent` methods | `add_node`/`add_multiple_nodes`/`run_task`/`run_node`/`compile_execution_plan` (`graph/__init__.py` L413–826) |

## Facts pinned

### Inheritance links (`--|>`)
- **U1. `AgentModule --|> AsimovBase`.** `AgentModule` is a proper subclass of `AsimovBase`.
- **U2. `Agent --|> AsimovBase`.** `Agent` is a proper subclass of `AsimovBase`.
- **U3. `CompositeModule --|> AgentModule`.** `CompositeModule` is a proper subclass of `AgentModule`.
- **U4. `Node --|> CompositeModule`.** `Node` is a proper subclass of `CompositeModule`.
- **U5. `FlowControlModule --|> AgentModule`.** `FlowControlModule` is a proper subclass of `AgentModule`.
- **U6. `Task --|> AsimovBase`.** `Task` is a proper subclass of `AsimovBase`.

### Association links (`--* / --o : attr`)
- **U7. `AgentModule --* ModuleType`.** `AgentModule.type`'s annotation references
  `ModuleType` (composition — every module carries a `ModuleType`).
- **U8. `Task --o TaskStatus`.** `Task.status`'s annotation references `TaskStatus`.
- **U9. `CompositeModule --* NodeConfig`.** `CompositeModule.node_config`'s annotation
  references `NodeConfig`.

### Methods under a class
- **U10. `Agent` core method set.** `Agent` defines the core graph-execution set:
  `add_node`, `add_multiple_nodes`, `run_task`, `run_node`,
  `compile_execution_plan` (asserted as a subset, so extra methods are tolerated).
  Each must be a **real (non-stub) implementation**: a method present only as a
  placeholder body (`pass` / `...` / `return None` / `raise NotImplementedError`)
  is judged statically (from source, never executed) as *not* implemented and so
  fails the set — a generation cannot satisfy the drawn operation by stubbing it.

## Harness

The pinned surface is the **structure the class diagram draws** — inheritance
links (`--|>`), association links (`--* / --o : attr`), and the method set under
`Agent` — asserted by **reflection on the loaded classes** (subclass relations,
attribute annotations, method names) plus **static source inspection** of a
method's body to reject stubs, never by executing behavior. A class or
attribute a generation does not define is a **FAILURE**, as is a present-but-wrong
structural link/method (the class exists but the link/method is wrong, absent, or
present only as a stub body).
This track does not skip / mark N/A.
Subjects are the 4 UML generations (`uml/outputcode/{claude,gpt,deepseek,gemini}`);
the origin graph package the diagram was extracted from is the grounding for the
facts above but is not itself a test subject.

## Portability

The contract is purely structural, so nothing behavioral runs — modules only
need to *define* their classes. `pydantic` is kept **real** (it is installed; the
`--|> AsimovBase` family and pydantic-typed annotations depend on genuine class
objects, and `AsimovBase(BaseModel, ABC)` needs pydantic's ABC-aware metaclass).
Only the heavy third-party tops the origin imports that are *missing* on the host
(`jsonpickle`, `opentelemetry`, `lupa`, and — for over-generating impls —
`google`, `boto3`, `backoff`, …) are resolved to permissive stubs so each module
execs far enough to define its classes; `redis` is real. Each generation loads as
a single module.
