# Behavioral contract — `asimov` (BismuthCloud) **NL track**

Reference: 
- `asimov-main/asimov/caches/`
    - `cache.py` — the abstract `Cache` base with prefix/suffix namespacing mailboxes
    - `redis_cache.py` — the concrete Redis implementation.
- `nl/input/description.txt`

**Caching System** is the self-contained, deterministic, dependency-free surface
the description describes explicitly:

> "Caching System — Abstract Cache interface with Redis implementation for:
> Key-value storage with JSON serialization, Prefix/suffix namespacing, Pub/sub
> messaging via mailboxes, Bulk operations (get_all, clear), Async interface."

## Conformance philosophy — the description, not a specific API

Each generation is driven by its **own explicit driver** (`adapter.py`) that
names the concrete Cache class and calls *that generation's real API* to produce
the observable effect each behavior asserts. Async scenarios run under a short
timeout so no call can hang the suite.

Every generation exposes the Cache as a Redis-backed class, exercised through an
in-memory Redis double (`_FakeRedis`) so its own logic (serialization,
namespacing, CRUD, bulk ops, pub/sub) is observed without a live server —
mirroring how a mock Redis stands in for a real server:

- **claude** drives `RedisCache` with `_FakeRedis(decode_responses=True)` injected
  into the lazily-built client slot (it calls `from_url(decode_responses=True)`).
- **gpt** drives its self-contained `RedisCache` over an in-memory
  `InMemoryRedisLike`, and its `mailbox(name)` factory for pub/sub.
- **deepseek** and **gemini** drive their Redis-only `RedisCache` over `_FakeRedis`.

### Namespacing

Driven through **each generation's own namespacing API**: gpt via
`with_namespace(prefix=…)`, and claude/deepseek/gemini via their constructor
`prefix`/`suffix`. Isolation is checked by giving two namespaced views the
**same** backend and confirming a key written under one prefix is not visible
under another. Assertions are on the observable round-trip/isolation, not the
literal `prefix:key` string, so they are independent of the separator.

### Mailboxes — deliver-if-listening (pub/sub)

The description says "Pub/sub messaging via mailboxes." This is pinned as
**pub/sub semantics**: a subscriber receives messages published *after* it is
listening (no durable backlog replay). The driver **subscribes first, then
publishes a,b,c, then reads three**, per each generation's real API:
claude/gemini expose a `subscribe()` async generator, gpt a `mailbox(name)`
object with `subscribe()`, and deepseek a `subscribe(channel, callback)` with a
background listener. An idle (subscribed-but-unpublished) mailbox yields nothing,
observed as a short read timeout returning `None`.

## Description clause → grounding

| Description clause | Grounding |
|---|---|
| "Key-value storage" | `Cache.get`/`set`; missing key returns `None` |
| "with JSON serialization" | values are (de)serialized, so `get` yields a fresh object (mutation-isolated copy) |
| "Prefix/suffix namespacing" | a prefixed view round-trips and isolates keys from other prefixes |
| "Pub/sub messaging via mailboxes" | publish → deliver-if-listening; empty mailbox yields nothing |
| "Bulk operations (get_all, clear)" | `get_all` returns the stored mapping; `clear` empties |
| "Async interface" | `async def get/set/...` |

## Behaviors pinned by the suite

| # | Behavior |
|---|---|
| N1  | `set` then `get` round-trips the value |
| N2  | `get` on a missing key returns `None` |
| N3  | `get` returns a **fresh object** (JSON serialization: mutating the result leaves the store intact) |
| N4  | `set` on an existing key **overwrites** the value |
| N5  | `delete` removes a key (subsequent `get` no longer finds it) |
| N6  | `clear` empties the cache (`get_all` becomes empty) |
| N7  | `get_all` returns the stored key→value mapping |
| N8  | a value written **under a prefix** round-trips under that same prefix |
| N9  | prefixes **isolate** keys (a key in namespace A is not seen in namespace B) |
| N10 | mailbox delivers messages **FIFO** to a listening subscriber (publish a,b,c → read a,b,c) |
| N11 | an empty (idle) mailbox yields nothing (**`None` on timeout**) |

## Dependency usage

The behaviors above are deliberately **dependency-agnostic**: the suite fakes
Redis (`_FakeRedis`) and stubs OpenTelemetry, so a generation that reimplemented a
dependency with a plain substitute still passes. This section pins the
complementary axis — does a generation **import and use the packages the
description names**, rather than hand-roll a substitute?

> "Abstract Cache interface with **Redis** implementation" ·
> "**OpenTelemetry** instrumentation"

The check is **static** (`loader.dependency_used`, AST only — it never imports the
module, so it is independent of whether the package is installed). A dependency
passes when the file both **imports** the package *and* **references** what it
imported at least once (guarding against a dead import). This is deliberately
scoped to import-and-use, not detailed correct-API verification.

| # | Check |
|---|---|
| D1 | imports and uses `redis` |
| D2 | imports and uses `opentelemetry` |

A generation **FAILS** when it does not use a named package at all. **gpt** passes
all 11 behaviors (its `InMemoryRedisLike` + `NoopTracer` substitutes behave
correctly) but fails D1 and D2 — it imports neither `redis` nor `opentelemetry`,
the exact gap this axis exists to surface. claude imports both lazily, deepseek
under `try/except`, gemini at module top; the AST check detects all three forms.
