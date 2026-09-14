import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import build_driver  # noqa: E402
from loader import dependency_used, gencode_paths, load_gencodemodule  # noqa: E402

_PATHS = dict(gencode_paths())
_CACHE = {}


class _Unloadable:
    """Stand-in for a generation that raised on import."""

    def __init__(self, exc):
        self._exc = exc

    def __getattr__(self, name):
        raise self._exc


def _driver_for(ident):
    if ident not in _CACHE:
        try:
            module = load_gencodemodule(ident, _PATHS[ident])
        except Exception as exc:                          # noqa: BLE001
            module = _Unloadable(exc)
        _CACHE[ident] = build_driver(ident.split("/")[-1], module)
    return _CACHE[ident]


@pytest.fixture(params=sorted(_PATHS))
def driver(request):
    return _driver_for(request.param)


@pytest.fixture(params=sorted(_PATHS))
def ident(request):
    return request.param


# ---------------------------------------------------------------------------
# Key-value storage
# ---------------------------------------------------------------------------
def test_set_get_roundtrip(driver):
    assert driver.roundtrip() == "v"


def test_get_missing_returns_none(driver):
    # The description pins "key-value storage" but no missing-key contract
    # (KeyError / default); returning None for an absent key is the behavior all
    # implementations share and is consistent with the description.
    assert driver.missing_returns_none() is True


def test_get_returns_deep_copy(driver):
    assert driver.deepcopy_value() == 1


def test_set_overwrites(driver):
    assert driver.overwrite() == "second"


def test_delete_removes_key(driver):
    assert driver.delete_absent() is True


# ---------------------------------------------------------------------------
# Bulk operations
# ---------------------------------------------------------------------------
def test_clear_empties(driver):
    assert driver.clear_count() == 0


def test_get_all_contains_entries(driver):
    assert driver.get_all_mapping() is True


# ---------------------------------------------------------------------------
# Prefix/suffix namespacing
# ---------------------------------------------------------------------------
def test_prefix_roundtrip(driver):
    assert driver.prefix_roundtrip() == "v"


def test_prefix_isolation(driver):
    assert driver.prefix_isolation() is True


# ---------------------------------------------------------------------------
# Pub/sub mailboxes
# ---------------------------------------------------------------------------
def test_mailbox_fifo(driver):
    assert driver.mailbox_fifo() == ["a", "b", "c"]


def test_mailbox_empty_returns_none(driver):
    assert driver.mailbox_empty_none() is None


# ---------------------------------------------------------------------------
# Dependency usage — does the generation import and use the packages the
# description names?
# ---------------------------------------------------------------------------
def _assert_dependency_used(ident, dep):
    assert dependency_used(_PATHS[ident], dep), (
        f"{ident} does not import and use '{dep}' — the description names it, so "
        f"a hand-rolled substitute does not use the dependency"
    )


def test_uses_named_dependency_redis(ident):
    _assert_dependency_used(ident, "redis")


def test_uses_named_dependency_opentelemetry(ident):
    _assert_dependency_used(ident, "opentelemetry")
