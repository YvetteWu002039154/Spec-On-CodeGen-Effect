"""Ephemeral PostgreSQL for driving the DB-backed generations.

vstorm's deepseek (asyncpg pool) and gemini (psycopg2 DSN) generations expose
only a Postgres backend — no in-memory path. To score them on behaviour rather
than on infrastructure availability, we stand up one throwaway PostgreSQL server
(via the pip-installable `pgserver`, no system deps) and hand each test its own
fresh, empty database so row-count assertions stay isolated.

Two consumers:
  * `fresh_db_dsn()`  -> a libpq URI to a brand-new empty database (gemini).
  * `LoopSafePool`    -> an asyncpg-pool substitute whose `.acquire()` opens a
                         connection in the *current* event loop, so a pool can be
                         reused across the adapter's per-call `asyncio.run(...)`
                         (a real asyncpg pool is bound to one loop and would
                         otherwise raise "attached to a different loop").
"""

import atexit
import tempfile
import uuid
from urllib.parse import urlparse, parse_qs

_server = None
_base_dsn = None


def _ensure_server():
    global _server, _base_dsn
    if _server is None:
        import pgserver  # lazy: only DB-backed drivers need it
        data_dir = tempfile.mkdtemp(prefix="vstorm_pg_")
        _server = pgserver.get_server(data_dir)
        _base_dsn = _server.get_uri()
        atexit.register(_cleanup)
    return _server


def _cleanup():
    global _server
    if _server is not None:
        try:
            _server.cleanup()
        except Exception:
            pass
        _server = None


def _socket_dir(uri):
    # pgserver serves over a Unix socket: postgresql://postgres:@/postgres?host=/tmp/xxx
    return parse_qs(urlparse(uri).query)["host"][0]


_uuid_registered = False


def _register_psycopg2_uuid():
    """Standard psycopg2 environment setup: teach it to adapt/cast Python
    ``uuid.UUID`` <-> PostgreSQL ``uuid``. This is process-global libpq/psycopg2
    configuration an application normally does once at startup — not a change to
    any generation's code — so a generation that passes ``UUID`` objects to
    parametrised SQL is exercised on its real logic rather than blocked by the
    absence of the adapter."""
    global _uuid_registered
    if not _uuid_registered:
        import psycopg2.extras
        psycopg2.extras.register_uuid()
        _uuid_registered = True


def fresh_db_dsn():
    """Create a brand-new empty database and return its libpq URI."""
    import psycopg2
    _ensure_server()
    _register_psycopg2_uuid()
    name = "t_" + uuid.uuid4().hex[:16]
    conn = psycopg2.connect(_base_dsn)
    conn.autocommit = True  # CREATE DATABASE cannot run inside a transaction
    try:
        conn.cursor().execute(f'CREATE DATABASE "{name}"')
    finally:
        conn.close()
    return f"postgresql://postgres:@/{name}?host={_socket_dir(_base_dsn)}"


class _AcquireCtx:
    def __init__(self, dsn):
        self._dsn = dsn
        self._conn = None

    async def __aenter__(self):
        import asyncpg
        self._conn = await asyncpg.connect(dsn=self._dsn)
        return self._conn

    async def __aexit__(self, *exc):
        await self._conn.close()


class LoopSafePool:
    """asyncpg.Pool stand-in. `.acquire()` yields a fresh connection bound to
    whatever loop is currently running.

    A real `asyncpg.Pool` also exposes the query methods directly (`fetch`,
    `fetchrow`, `fetchval`, `execute`, `executemany`) as documented pass-throughs
    that acquire a connection internally — using them instead of an explicit
    `async with pool.acquire()` is ordinary asyncpg style. They are forwarded
    here so a generation written that way is exercised on its real logic rather
    than failing on a gap in this stub."""

    def __init__(self, dsn):
        self._dsn = dsn

    def acquire(self):
        return _AcquireCtx(self._dsn)

    async def _via_conn(self, name, *args, **kwargs):
        async with _AcquireCtx(self._dsn) as conn:
            return await getattr(conn, name)(*args, **kwargs)

    async def fetch(self, *a, **k):
        return await self._via_conn("fetch", *a, **k)

    async def fetchrow(self, *a, **k):
        return await self._via_conn("fetchrow", *a, **k)

    async def fetchval(self, *a, **k):
        return await self._via_conn("fetchval", *a, **k)

    async def execute(self, *a, **k):
        return await self._via_conn("execute", *a, **k)

    async def executemany(self, *a, **k):
        return await self._via_conn("executemany", *a, **k)

    async def close(self):
        return None
