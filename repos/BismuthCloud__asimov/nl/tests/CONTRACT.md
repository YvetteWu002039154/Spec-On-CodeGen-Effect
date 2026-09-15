# Behavioral contract — `asimov` (BismuthCloud) **NL track**

## Description features

| Description clause |
|---|
| "Key-value storage" |
| "with JSON serialization" |
| "Prefix/suffix namespacing" |
| "Pub/sub messaging via mailboxes" |
| "Bulk operations (get_all, clear)" |
| "Async interface" |

## Behaviors pinned

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

> "Abstract Cache interface with **Redis** implementation" ·
> "**OpenTelemetry** instrumentation"

| # | Check |
|---|---|
| D1 | imports and uses `redis` |
| D2 | imports and uses `opentelemetry` |
