# Conformance results — `asimov` (BismuthCloud) **UML track**

Reference: origin `asimov-main/asimov/` (graph package family) · Suite:
`uml/tests/test_conformance.py` (10 structural facts, see [CONTRACT.md](CONTRACT.md))
· pytest 9.

## Matrix (P = pass, F = fail)

| Fact | uml/cla | uml/gpt | uml/dee | uml/gem |
|---|---|---|---|---|
| U1 `AgentModule ➝ AsimovBase` | P | P | P | F |
| U2 `Agent ➝ AsimovBase` | P | P | P | F |
| U3 `CompositeModule ➝ AgentModule` | P | P | P | F |
| U4 `Node ➝ CompositeModule` | P | P | P | F |
| U5 `FlowControlModule ➝ AgentModule` | P | P | P | F |
| U6 `Task ➝ AsimovBase` | P | P | P | F |
| U7 `AgentModule --* ModuleType` (`type`) | P | F | F | F |
| U8 `Task --o TaskStatus` (`status`) | P | F | F | F |
| U9 `CompositeModule --* NodeConfig` (`node_config`) | P | F | F | F |
| U10 `Agent` core method set | P | P | P | F |
| **Pass / 10** | 10 | 7 | 7 | 0 |
| **Score** | 1.000 | 0.700 | 0.700 | 0.000 |

Run summary: **24 passed, 16 failed, 0 skipped.**

## How the structure diverged

The inheritance skeleton is reproduced with **high fidelity** — all three
loadable generations (`claude`, `gpt`, `deepseek`) match every `--|>` link (U1–U6)
and the `Agent` method set (U10). `uml/claude` reproduces the whole diagram,
associations included (10/10).

This track does **not** skip / mark N/A: a diagrammed link/attribute a generation
does not expose is a **FAIL**.

- **`uml/gpt`, `uml/deepseek` drop the three association types (U7–U9 → FAIL).**
  Both define `AgentModule`, `Task`, and `CompositeModule` as `AsimovBase`
  subclasses but declare their fields **imperatively in `__init__`** rather than as
  class-level annotations, so `type` / `status` / `node_config` are absent from
  `__annotations__`. The modelled associations are therefore not expressed
  structurally → FAIL (the diagram draws the association and the generation does
  not expose it).
- **`uml/gemini` fails to load (0/10 → all FAIL).** Its `Node` declares a pydantic
  field named `_nodes`; real pydantic rejects leading-underscore field names at
  class-definition time (`NameError: Fields must not use names with leading
  underscores`). A genuine defect in the generation — it loads nothing, so it
  exposes none of the diagrammed structure and every fact FAILS.

## Classification

- **`uml/claude` reproduces the whole diagram (10/10).** `uml/gpt` and
  `uml/deepseek` match every inheritance link and the method set but fail the
  three association types (U7–U9) they declare only imperatively. `uml/gemini`
  fails all 10 (does not load).
- The failing cells are honest structural gaps, not over-strict tests — the
  method check is a subset test, and the association checks accept any annotation
  that names the target type. A generation that does not expose the diagrammed
  structure fails rather than being skipped.

## Reproduce

```bash
cd repos/BismuthCloud__asimov/uml/tests
python3 -m pytest -p no:warnings -q               # full matrix
```
