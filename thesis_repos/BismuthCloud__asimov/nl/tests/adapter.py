import asyncio
import fnmatch


def _run(factory, timeout=5.0):
    async def _main():
        return await asyncio.wait_for(factory(), timeout)
    return asyncio.run(_main())


async def _wait(ready, spins=200):
    """Yield control until `ready()` is truthy (subscriber registered), or up to
    `spins` event-loop turns — enough for the subscribe coroutine to run before
    we publish, since delivery is deliver-if-listening."""
    for _ in range(spins):
        if ready():
            return
        await asyncio.sleep(0)


async def _gen_fifo(agen, ready, publish):
    """Drive an async-generator subscription deliver-if-listening: start the
    subscriber, wait until it is registered, publish a/b/c, collect three."""
    it = agen.__aiter__()
    first = asyncio.ensure_future(it.__anext__())
    await _wait(ready)
    for x in ("a", "b", "c"):
        await publish(x)
    return [await asyncio.wait_for(first, 1),
            await asyncio.wait_for(it.__anext__(), 1),
            await asyncio.wait_for(it.__anext__(), 1)]


async def _gen_empty(agen, ready):
    """A subscribed-but-idle mailbox yields nothing: expect a read to time out."""
    it = agen.__aiter__()
    task = asyncio.ensure_future(it.__anext__())
    await _wait(ready)
    try:
        return await asyncio.wait_for(task, 0.05)
    except asyncio.TimeoutError:
        task.cancel()
        return None


def _b(x):
    return x.encode() if isinstance(x, str) else x


def _s(x):
    return x.decode() if isinstance(x, bytes) else x


class _FakeRedis:
    """A small in-memory async Redis double: enough of the redis-py async API
    for a generated Redis-only cache to exercise its OWN logic (serialization,
    namespacing, CRUD, bulk ops) without a live server. Values/keys are stored
    as bytes, matching real redis, so impls that `.decode()` keys hit the same
    path."""

    def __init__(self, decode_responses=False):
        self._d = {}
        self._subs = {}          # channel(bytes) -> list[_FakePubSub]
        self._decode = decode_responses

    def _out(self, x):
        # Mirror redis-py: with decode_responses=True keys/values come back as
        # str; otherwise as bytes.
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

    async def keys(self, pattern="*"):
        pat = _s(pattern)
        return [self._out(k) for k in self._d if fnmatch.fnmatch(_s(k), pat)]

    def scan_iter(self, match="*", **kwargs):
        out = self._out
        store = self._d
        pat = _s(match)

        async def _gen():
            for k in list(store):
                if fnmatch.fnmatch(_s(k), pat):
                    yield out(k)
        return _gen()

    async def flushdb(self, *a, **k):
        self._d.clear()

    def pubsub(self, *a, **k):
        return _FakePubSub(self)

    async def publish(self, channel, message):
        # Deliver-if-listening: only subscribers registered *before* this
        # publish receive the message (real redis pub/sub, not a durable queue).
        cb = _b(channel)
        data = self._out(_b(message))
        subs = list(self._subs.get(cb, []))
        for s in subs:
            s._q.put_nowait({"type": "message", "channel": self._out(cb), "data": data})
        return len(subs)

    async def aclose(self):
        pass

    async def close(self):
        pass


class _FakePubSub:
    """Minimal async pub/sub double matching redis-py's pubsub() surface:
    subscribe registers interest, listen() async-yields a subscribe
    confirmation then each subsequently-published message."""

    def __init__(self, hub):
        self._hub = hub
        self._q = asyncio.Queue()
        self._channels = set()

    async def subscribe(self, *channels):
        for ch in channels:
            cb = _b(ch)
            self._channels.add(cb)
            self._hub._subs.setdefault(cb, []).append(self)
            self._q.put_nowait({"type": "subscribe", "channel": self._hub._out(cb), "data": 1})

    async def unsubscribe(self, *channels):
        for cb in ([_b(c) for c in channels] or list(self._channels)):
            self._channels.discard(cb)
            lst = self._hub._subs.get(cb)
            if lst and self in lst:
                lst.remove(self)

    async def listen(self):
        while True:
            yield await self._q.get()

    async def close(self):
        await self.unsubscribe()

    async def aclose(self):
        await self.unsubscribe()


# ============================================================================
# One driver per generation. `m` is that generation's loaded module.
# ============================================================================

class ClaudeDriver:
    model = "claude"

    def __init__(self, m):
        self.m = m

    def _on(self, redis, **kw):
        # Exercise the Redis-backed implementation (not InMemoryCache): claude's
        # RedisCache builds its client lazily via aioredis.from_url, so inject
        # the in-memory double into the slot _get_client() returns. claude uses
        # from_url(decode_responses=True), so the double decodes to str.
        c = self.m.RedisCache(**kw)
        c._client = redis
        return c

    def _cache(self, **kw):
        return self._on(_FakeRedis(decode_responses=True), **kw)

    def roundtrip(self):
        async def go():
            c = self._cache()
            await c.set("k", "v")
            return await c.get("k")
        return _run(go)

    def missing_returns_none(self):
        async def go():
            c = self._cache()
            return await c.get("absent-xyz") is None
        return _run(go)

    def deepcopy_value(self):
        async def go():
            c = self._cache()
            await c.set("d", {"n": 1})
            g = await c.get("d")
            g["n"] = 999
            again = await c.get("d")
            return again["n"]
        return _run(go)

    def overwrite(self):
        async def go():
            c = self._cache()
            await c.set("k", "first")
            await c.set("k", "second")
            return await c.get("k")
        return _run(go)

    def delete_absent(self):
        async def go():
            c = self._cache()
            await c.set("k", "v")
            await c.delete("k")
            return await c.get("k") is None
        return _run(go)

    def clear_count(self):
        async def go():
            c = self._cache()
            for k in ("a", "b", "c"):
                await c.set(k, k)
            await c.clear()
            return len(await c.get_all())
        return _run(go)

    def get_all_mapping(self):
        async def go():
            c = self._cache()
            pairs = {"x": 1, "y": 2}
            for k, v in pairs.items():
                await c.set(k, v)
            allv = dict(await c.get_all())
            return all(allv.get(k) == v for k, v in pairs.items())
        return _run(go)

    # claude namespaces via constructor prefix/suffix (no with_namespace factory).
    def prefix_roundtrip(self):
        async def go():
            c = self._on(_FakeRedis(decode_responses=True), prefix="ns1")
            await c.set("k", "v")
            return await c.get("k")
        return _run(go)

    def prefix_isolation(self):
        async def go():
            redis = _FakeRedis(decode_responses=True)          # shared backend
            a = self._on(redis, prefix="nsA")
            b = self._on(redis, prefix="nsB")
            await a.set("k", "v")
            return await b.get("k") is None
        return _run(go)

    # claude exposes mailboxes as publish + subscribe (async generator).
    def mailbox_fifo(self):
        async def go():
            c = self._cache()
            return await _gen_fifo(c.subscribe("mb"),
                                   lambda: c._client._subs.get(b"mb"),
                                   lambda x: c.publish("mb", x))
        return _run(go)

    def mailbox_empty_none(self):
        async def go():
            c = self._cache()
            return await _gen_empty(c.subscribe("emptybox"),
                                    lambda: c._client._subs.get(b"emptybox"))
        return _run(go)


class GptDriver:
    model = "gpt"

    def __init__(self, m):
        self.m = m

    def _cache(self):
        return self.m.RedisCache()

    def roundtrip(self):
        async def go():
            c = self._cache()
            await c.set("k", "v")
            return await c.get("k")
        return _run(go)

    def missing_returns_none(self):
        async def go():
            c = self._cache()
            return await c.get("absent-xyz") is None
        return _run(go)

    def deepcopy_value(self):
        async def go():
            c = self._cache()
            await c.set("d", {"n": 1})
            g = await c.get("d")
            g["n"] = 999
            again = await c.get("d")
            return again["n"]
        return _run(go)

    def overwrite(self):
        async def go():
            c = self._cache()
            await c.set("k", "first")
            await c.set("k", "second")
            return await c.get("k")
        return _run(go)

    def delete_absent(self):
        async def go():
            c = self._cache()
            await c.set("k", "v")
            await c.delete("k")
            return await c.get("k") is None
        return _run(go)

    def clear_count(self):
        async def go():
            c = self._cache()
            for k in ("a", "b", "c"):
                await c.set(k, k)
            await c.clear()
            return len(await c.get_all(["a", "b", "c"]))
        return _run(go)

    def get_all_mapping(self):
        async def go():
            c = self._cache()
            pairs = {"x": 1, "y": 2}
            for k, v in pairs.items():
                await c.set(k, v)
            allv = dict(await c.get_all(list(pairs)))
            return all(allv.get(k) == v for k, v in pairs.items())
        return _run(go)

    def prefix_roundtrip(self):
        async def go():
            c = self._cache()
            scoped = c.with_namespace(prefix="ns1")
            await scoped.set("k", "v")
            return await scoped.get("k")
        return _run(go)

    def prefix_isolation(self):
        async def go():
            c = self._cache()
            a = c.with_namespace(prefix="nsA")
            await a.set("k", "v")
            b = c.with_namespace(prefix="nsB")
            return await b.get("k") is None
        return _run(go)

    # gpt exposes mailboxes via a mailbox(name) factory -> publish + subscribe.
    def mailbox_fifo(self):
        async def go():
            mb = self._cache().mailbox("mb")
            return await _gen_fifo(mb.subscribe(),
                                   lambda: mb._redis._mailboxes.get(mb._channel),
                                   lambda x: mb.publish(x))
        return _run(go)

    def mailbox_empty_none(self):
        async def go():
            mb = self._cache().mailbox("emptybox")
            return await _gen_empty(mb.subscribe(),
                                    lambda: mb._redis._mailboxes.get(mb._channel))
        return _run(go)


class DeepseekDriver:
    model = "deepseek"

    def __init__(self, m):
        self.m = m

    def _cache(self):
        return self.m.RedisCache(_FakeRedis())

    def roundtrip(self):
        async def go():
            c = self._cache()
            await c.set("k", "v")
            return await c.get("k")
        return _run(go)

    def missing_returns_none(self):
        async def go():
            c = self._cache()
            return await c.get("absent-xyz") is None
        return _run(go)

    def deepcopy_value(self):
        async def go():
            c = self._cache()
            await c.set("d", {"n": 1})
            g = await c.get("d")
            g["n"] = 999
            again = await c.get("d")
            return again["n"]
        return _run(go)

    def overwrite(self):
        async def go():
            c = self._cache()
            await c.set("k", "first")
            await c.set("k", "second")
            return await c.get("k")
        return _run(go)

    def delete_absent(self):
        async def go():
            c = self._cache()
            await c.set("k", "v")
            await c.delete("k")
            return await c.get("k") is None
        return _run(go)

    def clear_count(self):
        async def go():
            c = self._cache()
            for k in ("a", "b", "c"):
                await c.set(k, k)
            await c.clear()
            return len(await c.get_all())
        return _run(go)

    def get_all_mapping(self):
        async def go():
            c = self._cache()
            pairs = {"x": 1, "y": 2}
            for k, v in pairs.items():
                await c.set(k, v)
            allv = dict(await c.get_all())
            return all(allv.get(k) == v for k, v in pairs.items())
        return _run(go)

    # deepseek namespaces via constructor prefix/suffix (_apply_namespace).
    def prefix_roundtrip(self):
        async def go():
            c = self.m.RedisCache(_FakeRedis(), prefix="ns1")
            await c.set("k", "v")
            return await c.get("k")
        return _run(go)

    def prefix_isolation(self):
        async def go():
            redis = _FakeRedis()                               # shared backend
            a = self.m.RedisCache(redis, prefix="nsA")
            b = self.m.RedisCache(redis, prefix="nsB")
            await a.set("k", "v")
            return await b.get("k") is None
        return _run(go)

    # deepseek exposes mailboxes as publish + subscribe(channel, callback),
    # delivering into the callback from a background listener task.
    def mailbox_fifo(self):
        async def go():
            redis = _FakeRedis()
            c = self.m.RedisCache(redis)
            got = []

            async def cb(msg):
                got.append(msg)

            await c.subscribe("mb", cb)
            await _wait(lambda: redis._subs.get(b"mb"))
            for x in ("a", "b", "c"):
                await c.publish("mb", x)
            await _wait(lambda: len(got) >= 3)
            return got
        return _run(go)

    def mailbox_empty_none(self):
        async def go():
            redis = _FakeRedis()
            c = self.m.RedisCache(redis)
            got = []

            async def cb(msg):
                got.append(msg)

            await c.subscribe("emptybox", cb)
            await _wait(lambda: False)                         # let the loop idle
            return got[0] if got else None
        return _run(go)


class GeminiDriver:
    model = "gemini"

    def __init__(self, m):
        self.m = m

    def _cache(self):
        return self.m.RedisCache(_FakeRedis())

    def roundtrip(self):
        async def go():
            c = self._cache()
            await c.set("k", "v")
            return await c.get("k")
        return _run(go)

    def missing_returns_none(self):
        async def go():
            c = self._cache()
            return await c.get("absent-xyz") is None
        return _run(go)

    def deepcopy_value(self):
        async def go():
            c = self._cache()
            await c.set("d", {"n": 1})
            g = await c.get("d")
            g["n"] = 999
            again = await c.get("d")
            return again["n"]
        return _run(go)

    def overwrite(self):
        async def go():
            c = self._cache()
            await c.set("k", "first")
            await c.set("k", "second")
            return await c.get("k")
        return _run(go)

    def delete_absent(self):
        async def go():
            c = self._cache()
            await c.set("k", "v")
            await c.delete("k")
            return await c.get("k") is None
        return _run(go)

    def clear_count(self):
        async def go():
            c = self._cache()
            for k in ("a", "b", "c"):
                await c.set(k, k)
            await c.clear()
            return len(await c.get_all())
        return _run(go)

    def get_all_mapping(self):
        async def go():
            c = self._cache()
            pairs = {"x": 1, "y": 2}
            for k, v in pairs.items():
                await c.set(k, v)
            allv = dict(await c.get_all())
            return all(allv.get(k) == v for k, v in pairs.items())
        return _run(go)

    # gemini namespaces via constructor prefix/suffix (no with_namespace factory).
    def prefix_roundtrip(self):
        async def go():
            c = self.m.RedisCache(_FakeRedis(), prefix="ns1")
            await c.set("k", "v")
            return await c.get("k")
        return _run(go)

    def prefix_isolation(self):
        async def go():
            redis = _FakeRedis()                               # shared backend
            a = self.m.RedisCache(redis, prefix="nsA")
            b = self.m.RedisCache(redis, prefix="nsB")
            await a.set("k", "v")
            return await b.get("k") is None
        return _run(go)

    # gemini exposes mailboxes as publish + subscribe (async generator); its
    # publish/subscribe apply _build_key(mailbox), so the channel stays "mb".
    def mailbox_fifo(self):
        async def go():
            c = self._cache()
            return await _gen_fifo(c.subscribe("mb"),
                                   lambda: c.redis._subs.get(b"mb"),
                                   lambda x: c.publish("mb", x))
        return _run(go)

    def mailbox_empty_none(self):
        async def go():
            c = self._cache()
            return await _gen_empty(c.subscribe("emptybox"),
                                    lambda: c.redis._subs.get(b"emptybox"))
        return _run(go)


DRIVERS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """Wrap a loaded generation module in its explicit driver."""
    return DRIVERS[model](module)
