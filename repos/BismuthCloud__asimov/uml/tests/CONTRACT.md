# Structural contract — `asimov` (BismuthCloud) **UML track**

This contract is derived from the **UML class diagram**
(`uml/input/classes.puml`, a pyreverse extraction of the origin). A class diagram records *structure*, not runtime behavior, so
the pinned facts are the three things the diagram actually draws:

1. **Inheritance links** — `Child --|> Parent`.
2. **Association links** — `A --* B : attr` / `A --o B : attr` (an attribute of
   `A` is typed as `B`).
3. **Methods under a class**.

## Facts pinned

| # | Diagram fact | Origin evidence |
|---|---|---|
| U1 | `AgentModule ➝ AsimovBase` | `class AgentModule(AsimovBase)` (`graph/__init__.py` L69) |
| U2 | `Agent ➝ AsimovBase` | `class Agent(AsimovBase)` (`graph/__init__.py` L376) |
| U3 | `CompositeModule ➝ AgentModule` | `class CompositeModule(AgentModule)` (`graph/__init__.py` L217) |
| U4 | `Node ➝ CompositeModule` | `class Node(CompositeModule)` (`graph/__init__.py` L311) |
| U5 | `FlowControlModule ➝ AgentModule` | `class FlowControlModule(AgentModule)` (`graph/__init__.py` L127) |
| U6 | `Task ➝ AsimovBase` | `class Task(AsimovBase)` (`graph/tasks.py` L16) |
| U7 | `ModuleType --* AgentModule : type` | `type: ModuleType` (`graph/__init__.py` L71) |
| U8 | `TaskStatus --o Task : status` | `status: TaskStatus = TaskStatus.WAITING` (`graph/tasks.py` L21) |
| U9 | `NodeConfig --* CompositeModule : node_config` | `node_config: NodeConfig` (`graph/__init__.py` L219) |
| U10 | `Agent` methods | `add_node`/`add_multiple_nodes`/`run_task`/`run_node`/`compile_execution_plan` (`graph/__init__.py` L413–826) |
