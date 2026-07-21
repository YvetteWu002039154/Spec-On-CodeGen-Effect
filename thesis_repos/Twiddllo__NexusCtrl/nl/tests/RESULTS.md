# Conformance results — `NexusCtrl` NL track

Subjects: the 4 NL generations. Each is driven by its own explicit driver in
`adapter.py`. `pass` = behavior matches the contract · `FAIL` = capability
wrong or **not exposed** (this suite does not skip / mark N/A).

Tests are grouped by side: **Agent Capabilities** (N2–N5) run on the remote
target machine; the rest are controller/local behaviors.

| behavior (contract) | claude | gpt | deepseek | gemini |
|---|---|---|---|---|
| N1  performance history retained | FAIL | pass | pass | pass |
| N2  metrics collection (strict: real self-collection) | pass | FAIL | pass | FAIL |
| N3  view active processes (strict: real enumeration) | pass | FAIL | pass | FAIL |
| N4  runs as background service (structural) | pass | FAIL | pass | pass |
| N5  responds to remote kill (bogus PID) | pass | pass | pass | pass |
| N6  create task | pass | pass | pass | pass |
| N7  manage multiple tasks | pass | pass | pass | pass |
| N8  priority vocabulary (critical/high/medium/low) | pass | pass | pass | pass |
| N9  completion tracked | pass | pass | pass | pass |
| N10 server status online/offline | pass | pass | FAIL | pass |

**Totals:** 33 passed, 7 failed.

## The failures

- **claude / N1** — metrics history is appended only inside
  `ServerConnection.metrics_history` by `fetch_metrics()` over a live socket to a
  running agent; headless there is no way to accumulate a series → FAIL.
- **gpt / N2, N3, N4** — gpt's agent is a passive recorder: no self-collecting
  metrics method (must be fed values), no real process enumeration (only holds
  what is reported to it), and no `start()` service entry point. Three
  agent-side failures.
- **gemini / N2, N3** — gemini's agent is simulated: `collect_metrics()` returns
  hardcoded values (`ram_percent=42.0`) that don't match the host, and
  `get_processes()` returns hardcoded mock PIDs. Both strict tests fail. (It
  does expose `start()`, so N4 passes structurally.)
- **deepseek / N10** — server up/down is modeled as a `ServerState.online`
  boolean, not a `ServerStatus` enum, so there is no status *vocabulary* to
  read (`AttributeError`) → FAIL.

Run with: `python3 -m pytest test_conformance.py -q` from this directory.
