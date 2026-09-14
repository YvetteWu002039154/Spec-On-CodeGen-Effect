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


# ── per-model drivers ────────────────────────────────────────────────────────
#
# One driver per model, written by reading that model's run0 source. The four
# generations differ in backend, namespacing and mailbox shape:
#
#   claude    InMemoryCache(prefix=, suffix=) — genuinely in-memory.
#             subscribe(mailbox) is an async GENERATOR.
#   gpt       RedisCache(redis) over the fake client, namespaced by
#             with_namespace(); mailboxes are objects: cache.mailbox(name)
#             .publish()/.subscribe().
#   deepseek  AsyncCache(prefix=, suffix=), Redis-backed. subscribe takes a
#             CALLBACK rather than yielding.
#   gemini    RedisCache(redis_client, prefix, suffix); Cache itself is an ABC,
#             so Redis is its only backend. subscribe is an async generator.
#
# _FakeRedis above is harness, not model coupling: it lets a Redis-only
# generation run its own logic without a server.

_MSGS = ["a", "b", "c"]


class _Base:
    def __init__(self, module):
        self.m = module
        _install_redis_double()

    def _cache(self, prefix=None):
        raise NotImplementedError

    def _get_all(self, cache, keys):
        """get_all() is parameterless in most generations but takes the key list
        in gpt's; both are named explicitly per driver via GET_ALL_TAKES_KEYS."""
        return _await(cache.get_all(keys) if self.GET_ALL_TAKES_KEYS
                      else cache.get_all()) or {}

    GET_ALL_TAKES_KEYS = False

    # ---- key/value behaviours (return shapes match test_conformance) -----
    def roundtrip(self):
        c = self._cache()
        _await(c.set("k", "v"))
        return _await(c.get("k"))

    def missing_returns_none(self):
        return _await(self._cache().get("nope")) is None

    def deepcopy_value(self):
        """N3: mutating what get() handed back must not change the store."""
        c = self._cache()
        _await(c.set("k", {"n": 1}))
        got = _await(c.get("k"))
        got["n"] = 999
        return _await(c.get("k"))["n"]

    def overwrite(self):
        c = self._cache()
        _await(c.set("k", "first"))
        _await(c.set("k", "second"))
        return _await(c.get("k"))

    def delete_absent(self):
        c = self._cache()
        _await(c.set("k", 1))
        _await(c.delete("k"))
        return _await(c.get("k")) is None

    def clear_count(self):
        c = self._cache()
        _await(c.set("a", 1))
        _await(c.set("b", 2))
        _await(c.clear())
        return len(self._get_all(c, ["a", "b"]))

    def get_all_mapping(self):
        c = self._cache()
        _await(c.set("a", 1))
        _await(c.set("b", 2))
        got = self._get_all(c, ["a", "b"])
        vals = {str(k).split(":")[-1]: v for k, v in got.items()}
        return vals.get("a") == 1 and vals.get("b") == 2

    def prefix_roundtrip(self):
        c = self._cache(prefix="ns1")
        _await(c.set("k", "v"))
        return _await(c.get("k"))

    def prefix_isolation(self):
        a = self._cache(prefix="nsA")
        b = self._cache(prefix="nsB")
        _await(a.set("k", "v"))
        return _await(b.get("k")) is None


class _GeneratorMailbox:
    """subscribe(mailbox) yields messages; read N with a timeout."""

    def _drain(self, cache, box, n):
        async def go():
            agen = cache.subscribe(box)
            out = []
            for _ in range(n):
                try:
                    out.append(await asyncio.wait_for(agen.__anext__(), 2.0))
                except Exception:
                    break
            return out
        return go

    def mailbox_fifo(self):
        c = self._cache()
        async def scenario():
            agen = c.subscribe("box")
            task = asyncio.ensure_future(agen.__anext__())
            await asyncio.sleep(0.05)
            for msg in _MSGS:
                await c.publish("box", msg)
            out = [await asyncio.wait_for(task, 2.0)]
            for _ in range(len(_MSGS) - 1):
                out.append(await asyncio.wait_for(agen.__anext__(), 2.0))
            return out
        return _loop().run_until_complete(scenario())

    def mailbox_empty_none(self):
        c = self._cache()
        async def scenario():
            agen = c.subscribe("idle")
            try:
                return await asyncio.wait_for(agen.__anext__(), 0.5)
            except Exception:
                return None
        return _loop().run_until_complete(scenario())


class ClaudeDriver(_Base, _GeneratorMailbox):
    def _cache(self, prefix=None):
        return self.m.InMemoryCache(prefix=prefix) if prefix else self.m.InMemoryCache()


class GptDriver(_Base):
    """Namespacing via with_namespace(prefix=...) (keyword-only); mailboxes are
    objects; get_all takes the key list."""

    GET_ALL_TAKES_KEYS = True

    def _cache(self, prefix=None):
        c = self.m.RedisCache(self.m.InMemoryRedisLike())
        return c.with_namespace(prefix=prefix) if prefix else c

    def mailbox_fifo(self):
        c = self._cache()
        async def scenario():
            box = c.mailbox("box")
            agen = box.subscribe()
            task = asyncio.ensure_future(agen.__anext__())
            await asyncio.sleep(0.05)
            for msg in _MSGS:
                await box.publish(msg)
            out = [await asyncio.wait_for(task, 2.0)]
            for _ in range(len(_MSGS) - 1):
                out.append(await asyncio.wait_for(agen.__anext__(), 2.0))
            return out
        return _loop().run_until_complete(scenario())

    def mailbox_empty_none(self):
        c = self._cache()
        async def scenario():
            agen = c.mailbox("idle").subscribe()
            try:
                return await asyncio.wait_for(agen.__anext__(), 0.5)
            except Exception:
                return None
        return _loop().run_until_complete(scenario())


class DeepseekDriver(_Base):
    """subscribe(channel, callback) — messages arrive by callback."""

    def _cache(self, prefix=None):
        import redis.asyncio as aioredis
        return self.m.RedisCache(aioredis.Redis(), prefix or "", "")

    def mailbox_fifo(self):
        c = self._cache()
        got = []
        async def scenario():
            async def cb(msg):
                got.append(msg)
            await c.subscribe("box", cb)
            await asyncio.sleep(0.05)
            for msg in _MSGS:
                await c.publish("box", msg)
            await asyncio.sleep(0.3)
            return got
        return _loop().run_until_complete(scenario())

    def mailbox_empty_none(self):
        c = self._cache()
        got = []
        async def scenario():
            async def cb(msg):
                got.append(msg)
            await c.subscribe("idle", cb)
            await asyncio.sleep(0.3)
            return got[0] if got else None
        return _loop().run_until_complete(scenario())


class GeminiDriver(_Base, _GeneratorMailbox):
    """Cache is an ABC here, so RedisCache is the only backend."""

    def _cache(self, prefix=None):
        import redis.asyncio as aioredis
        return self.m.RedisCache(aioredis.Redis(), prefix or "", "")


GENERATIONS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """One hand-written driver per model, written against that model's run0."""
    return GENERATIONS[model](module)
