---
name: conformance-tests
description: Generate behavior-conformance tests that pin the reference repo's behavior and run the same tests against every LLM-generated implementation. Use when comparing generated code against a ground-truth repo, building a black-box test harness across multiple implementations, or producing a per-implementation pass/fail matrix.
argument-hint: [path-or-description of the unit under test, e.g. "the parser in <origin_repo>/src"]
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash(python3 *) Bash(python *) Bash(pytest *) Write Edit
---

# Behavior-conformance test generator

You are a test engineer. Produce a pytest suite that pins the REFERENCE
implementation's observable behavior and runs it, unchanged, against every
LLM-generated implementation. Target: `$ARGUMENTS`

## Ground truth and layout

- `<origin_repo>/` is the REFERENCE and the ONLY source of expected behavior.
- Implementations under test (8 total = 2 sources x 4 models), all named
  `generated_code.py`:
    <nl>/<outputcode>/{claude,gpt,deepseek,gemini}/generated_code.py
    <uml>/<outputcode>/{claude,gpt,deepseek,gemini}/generated_code.py
- Treat every `generated_code.py` as an opaque box. Never derive expected
  behavior from a generated file; derive it only from `<origin_repo>`.

## Hard rules

- Black box only. Assert on observable outputs and side effects. Never assert
  on internal structure, private helpers, or naming.
- The eight files share the filename `generated_code.py`, so they collide on
  module name. Load each by full path under a UNIQUE module name with
  `importlib.util.spec_from_file_location` + a per-path name. Never plain
  `import generated_code`.
- One shared test body runs against all implementations via an adapter that
  absorbs signature/shape differences. Do not fork the suite per model.
- Tests independent and deterministic. Names describe the behavior, not the
  function. One short comment per test naming the behavior in `<origin_repo>`
  it pins.

## Workflow — stop and report after each phase; wait for my go-ahead

1. **Derive the contract.** Read only `<origin_repo>`. Write the behavioral
   contract (public entry points, inputs, outputs, side effects, error
   handling, edge cases) to `tests/CONTRACT.md`. Stop. Let me review it before
   anything downstream is built.

2. **Map the shapes.** Read all 8 `generated_code.py` files. Report a table of
   how their public surfaces differ (bare functions vs class wrappers, arg
   order, return types, error types). This is the adapter's input. Stop.

3. **Build the harness.** Write:
   - a path-based loader (source in {nl,uml}, model in
     {claude,gpt,deepseek,gemini}) using `spec_from_file_location`;
   - an adapter exposing one stable interface that normalizes the shape
     differences found in phase 2;
   - the reference behind the same adapter interface.
   Stop.

4. **Write the tests.** 10-15 pytest tests, parameterized over the reference
   plus all 8 implementations, spread across: happy path, boundaries/edges,
   invalid input / error handling, and any stateful or ordering behavior.
   Stop.

5. **Run and report.** First run the suite against the reference alone and
   confirm it passes (sanity check; if it fails, the tests are wrong, not the
   implementations). Then run the full matrix and produce a per-implementation
   pass/fail table (rows = the 8 implementations, columns = tests). Flag
   whether each failure looks like an implementation bug or an over-strict
   test.

## Output

- pytest + Python.
- `tests/CONTRACT.md`, the loader, the adapter, the parameterized suite, and
  the final matrix report.

If `<origin_repo>`, `<nl>`, `<uml>`, or `<outputcode>` are placeholders, ask me
for the real paths before phase 1. Use `ultrathink` when deriving the contract
and designing the adapter.
