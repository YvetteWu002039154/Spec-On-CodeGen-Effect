"""Generic, capability-based driver for the asimov Redis-cache conformance suite.

WHY THIS EXISTS.  The original adapter carried one driver per model, each welded
to the exact class and method names that model's ORIGINAL generation happened to
emit — `with_namespace` in one, a constructor `prefix=` in another, a callback
`subscribe(channel, cb)` in a third — plus per-model private slots (`_client`,
`redis`, `_redis`, `_mailboxes`) poked at directly.  Any regeneration expressing
the SAME behaviour through different names or call shapes scored 0: an adapter
artefact, which makes the numbers measure the adapter rather than the code.

This driver DISCOVERS the generation's API instead:

  * picks the Redis-backed cache class (most cache capabilities, Redis/Cache
    name preferred);
  * constructs it by matching each `__init__` parameter *by name* (redis client
    / url / host / port / prefix / suffix), keeping the first recipe that
    provably round-trips a probe value;
  * resolves every operation through an alias table; and
  * probes the *call shape* of the ambiguous ones — `get_all()` vs
    `get_all(keys)` vs `get_all(pattern)`, `clear()` vs `clear(pattern)`,
    async-generator vs callback vs queue/handle `subscribe`, constructor
    namespacing vs a `with_namespace()` factory — on fresh state, keeping only a
    shape whose effect is observably correct.  A form is never accepted merely
    because it did not raise.

The in-file `_FakeRedis` / `_FakePubSub` harness is test infrastructure, not
model coupling: it lets a Redis-only generation exercise its own logic without a
live server.  It is installed over `redis.asyncio.{Redis, from_url}`, so a
generation that builds its own client — lazily or eagerly, by URL or by
host/port — is served the double without the adapter knowing where it lands.

Everything awaited runs on ONE persistent event loop (`_loop()`): `asyncio.run`
per call would destroy the loop between calls and break any generation holding a
long-lived async resource ("attached to a different loop").
"""
import asyncio
import fnmatch
import inspect


# ── one persistent event loop ────────────────────────────────────────────────
_LOOP = None


def _loop():
    global _LOOP
    if _LOOP is None or _LOOP.is_closed():
        _LOOP = asyncio.new_event_loop()
        asyncio.set_event_loop(_LOOP)
    return _LOOP


def _await(v, timeout=20.0):
    """Bridge sync -> async.  Only ever called at the outer boundary (never from
    inside a running scenario); everything inner uses `_call` / `_atry`."""
    if not inspect.isawaitable(v):
        return v

    async def _main():
        return await asyncio.wait_for(asyncio.ensure_future(v), timeout)
    return _loop().run_until_complete(_main())


async def _call(fn, *a, **k):
    r = fn(*a, **k)
    return await r if inspect.isawaitable(r) else r


async def _atry(fn, forms):
    """Call `fn` with the first (args, kwargs) form that does not raise.
    Returns (ok, value_or_last_exception).  Callers that care about an EFFECT
    validate the effect themselves — see `_probe_*`."""
    last = None
    for a, k in forms:
        try:
            return True, await _call(fn, *a, **k)
        except Exception as e:  # noqa: BLE001 — probing unknown signatures
            last = e
    return False, last


def _method(obj, aliases):
    for name in aliases:
        fn = getattr(obj, name, None)
        if callable(fn):
            return fn
    return None


async def _settle(spins=300):
    """Yield control for `spins` event-loop turns.

    Redis pub/sub is deliver-if-listening: only subscribers registered *before*
    a publish receive it.  Generations register from a coroutine (sometimes from
    a background listener task), so the loop must be turned over before we
    publish.  Spinning is name-agnostic — no peeking at anyone's internals."""
    for _ in range(spins):
        await asyncio.sleep(0)


def _b(x):
    return x.encode() if isinstance(x, str) else x


def _s(x):
    return x.decode() if isinstance(x, bytes) else x


# ── fake Redis harness (test infrastructure) ─────────────────────────────────
class _Hub:
    """The shared "server": one keyspace + one set of pub/sub registrations.
    Reset between scenarios; every client view resolves it dynamically, so two
    caches built in the same scenario really do share a backend."""

    def __init__(self):
        self.d = {}
        self.subs = {}           # channel(bytes) -> list[_FakePubSub]


_HUB = _Hub()
_DECODE = False                  # decode_responses default for clients we hand out


def _new_hub():
    global _HUB
    _HUB = _Hub()
    return _HUB


class _FakeRedis:
    """A small in-memory async Redis double: enough of the redis-py async API for
    a generated Redis-only cache to exercise its OWN logic without a live server.
    Values/keys are stored as bytes, matching real redis, so impls that
    `.decode()` keys hit the same path."""

    def __init__(self, *a, **kw):
        self._decode = kw.get("decode_responses", _DECODE)

    # a couple of generations `await aioredis.from_url(...)`
    def __await__(self):
        async def _self():
            return self
        return _self().__await__()

    @classmethod
    def from_url(cls, *a, **kw):
        return cls(**kw)

    @property
    def _d(self):
        return _HUB.d

    def _out(self, x):
        # Mirror redis-py: decode_responses=True -> str, otherwise bytes.
        return _s(x) if self._decode else x

    async def get(self, key):
        v = self._d.get(_b(key))
        return None if v is None else self._out(v)

    async def set(self, key, value, *args, **kwargs):
        self._d[_b(key)] = _b(value)
        return True

    async def setex(self, key, ttl, value):
        self._d[_b(key)] = _b(value)
        return True

    async def delete(self, *keys):
        n = 0
        for k in keys:
            if _b(k) in self._d:
                del self._d[_b(k)]
                n += 1
        return n

    async def exists(self, *keys):
        return sum(1 for k in keys if _b(k) in self._d)

    async def mget(self, keys, *more):
        if more:
            keys = [keys, *more]
        elif isinstance(keys, (str, bytes)):
            keys = [keys]
        return [None if (v := self._d.get(_b(k))) is None else self._out(v)
                for k in keys]

    def _match(self, pattern):
        pat = _s(pattern)
        return [k for k in list(self._d) if fnmatch.fnmatch(_s(k), pat)]

    async def keys(self, pattern="*"):
        return [self._out(k) for k in self._match(pattern)]

    async def scan(self, cursor=0, match="*", count=None, **kw):
        return 0, [self._out(k) for k in self._match(match or "*")]

    def scan_iter(self, match="*", **kwargs):
        keys = [self._out(k) for k in self._match(match or "*")]

        async def _gen():
            for k in keys:
                yield k
        return _gen()

    def pipeline(self, *a, **k):
        return _FakePipeline(self)

    async def flushdb(self, *a, **k):
        self._d.clear()

    def pubsub(self, *a, **k):
        return _FakePubSub(self)

    async def publish(self, channel, message):
        # Deliver-if-listening: only subscribers registered *before* this publish
        # receive it (real redis pub/sub, not a durable queue).
        cb = _b(channel)
        data = self._out(_b(message))
        subs = list(_HUB.subs.get(cb, []))
        for s in subs:
            s._q.put_nowait({"type": "message", "channel": self._out(cb), "data": data})
        return len(subs)

    async def aclose(self):
        pass

    async def close(self):
        pass


class _FakePipeline:
    """Just enough of redis-py's pipeline to serve the mget-by-pipeline idiom."""

    def __init__(self, r):
        self._r = r
        self._ops = []

    def get(self, k):
        self._ops.append(("get", (k,)))
        return self

    def set(self, k, v, *a, **kw):
        self._ops.append(("set", (k, v)))
        return self

    def delete(self, *k):
        self._ops.append(("delete", k))
        return self

    async def execute(self, *a, **k):
        ops, self._ops = self._ops, []
        return [await getattr(self._r, n)(*args) for n, args in ops]

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _FakePubSub:
    """Minimal async pub/sub double matching redis-py's pubsub() surface:
    subscribe registers interest, listen() async-yields a subscribe confirmation
    then each subsequently-published message."""

    def __init__(self, hub):
        self._client = hub
        self._q = asyncio.Queue()
        self._channels = set()

    async def subscribe(self, *channels, **kw):
        for ch in list(channels) + list(kw):
            cb = _b(ch)
            self._channels.add(cb)
            _HUB.subs.setdefault(cb, []).append(self)
            self._q.put_nowait({"type": "subscribe",
                                "channel": self._client._out(cb), "data": 1})

    psubscribe = subscribe

    async def unsubscribe(self, *channels):
        for cb in ([_b(c) for c in channels] or list(self._channels)):
            self._channels.discard(cb)
            lst = _HUB.subs.get(cb)
            if lst and self in lst:
                lst.remove(self)

    punsubscribe = unsubscribe

    async def listen(self):
        while True:
            yield await self._q.get()

    async def get_message(self, ignore_subscribe_messages=False, timeout=0.0):
        while True:
            try:
                msg = self._q.get_nowait()
            except asyncio.QueueEmpty:
                return None
            if ignore_subscribe_messages and msg["type"] != "message":
                continue
            return msg

    async def close(self):
        await self.unsubscribe()

    async def aclose(self):
        await self.unsubscribe()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        await self.unsubscribe()
        return False


def _install_redis_double():
    """Serve the double to generations that build their own client.  Patching the
    `redis.asyncio` module attributes covers every construction form the domain
    uses (`from_url`, `Redis(host=..., port=...)`, `Redis.from_url`) without the
    adapter knowing where the client is stored.  `Redis` must stay a *class*:
    generations annotate with `Optional[aioredis.Redis]`, which is evaluated at
    runtime and rejects a non-type."""
    try:
        import redis.asyncio as ra
    except ImportError:      # pragma: no cover - the test env installs redis
        return
    ra.Redis = _FakeRedis
    ra.StrictRedis = _FakeRedis
    ra.from_url = lambda *a, **kw: _FakeRedis(**kw)


_install_redis_double()


# ── operation alias tables ───────────────────────────────────────────────────
A_GET = ["get", "fetch", "retrieve", "get_value", "read", "load"]
A_SET = ["set", "put", "store", "write", "set_value", "save"]
A_DELETE = ["delete", "remove", "delete_key", "invalidate", "evict", "unset"]
A_CLEAR = ["clear", "clear_all", "flush", "flushdb", "reset", "purge", "wipe"]
A_GET_ALL = ["get_all", "get_many", "all", "items", "mget", "list_all", "dump",
             "get_all_values", "as_dict"]
A_PUBLISH = ["publish", "send", "post", "emit", "push"]
A_SUBSCRIBE = ["subscribe", "listen", "stream", "consume", "messages",
               "iter_messages", "receive"]
A_MAILBOX = ["mailbox", "get_mailbox", "open_mailbox", "channel", "topic", "queue"]
A_NEXT = ["get", "receive", "recv", "read", "next", "get_message", "pop"]
A_NAMESPACE = ["with_namespace", "namespace", "with_prefix", "with_prefix_suffix",
               "scoped", "scope", "namespaced", "child", "derive", "sub"]
# Lifecycle hooks some generations require before the cache is usable.  Kept
# deliberately narrow: `run` / `serve` / `listen` / `start` are excluded because
# calling one of those during discovery can block the suite forever.
A_CONNECT = ["connect", "initialize", "init", "setup", "open", "aconnect"]

_CAP_GROUPS = (A_GET, A_SET, A_DELETE, A_CLEAR, A_GET_ALL, A_PUBLISH,
               A_SUBSCRIBE, A_MAILBOX)

# probe tokens: deliberately unrelated to anything test_conformance.py asserts
_PK, _PV = "__probe_key__", "__probe_value__"

