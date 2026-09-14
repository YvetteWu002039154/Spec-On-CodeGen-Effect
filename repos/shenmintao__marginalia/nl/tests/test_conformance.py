import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import build_driver  # noqa: E402
from loader import gencode_paths, load_gencodemodule  # noqa: E402

_PATHS = dict(gencode_paths())
_CACHE = {}


class _Unloadable:
    """Stand-in for a generation that raised on import.

    Building all four drivers eagerly meant one unloadable generation took down
    collection for the whole module — scoring every OTHER model 0-of-0 too, and,
    having no [impl_id] in its name, the crash was dropped by the scorer rather
    than counted. Loading lazily and capturing the exception makes an unloadable
    generation fail its own tests (the correct score for it) and leaves the rest
    intact. See Reports/variance_pilot/: across runs, one bad generation would
    otherwise blank an entire run.
    """

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


# ---------------------------------------------------------------------------
# Recall (lexical search with source quotas)
# ---------------------------------------------------------------------------
def test_lexical_recall_relevance(driver):
    assert driver.lexical_recall_relevance() is True


def test_recall_respects_quota(driver):
    assert driver.recall_respects_quota() is True


# ---------------------------------------------------------------------------
# Ingest (many file kinds)
# ---------------------------------------------------------------------------
def test_filetype_detection(driver):
    assert driver.filetype_discriminates() is True


# ---------------------------------------------------------------------------
# Durable investigation notes (journal recall)
# ---------------------------------------------------------------------------
def test_journal_note_roundtrip(driver):
    assert driver.journal_roundtrip() is True


# ---------------------------------------------------------------------------
# Reading original file windows (sections / pages / lines / slices)
# ---------------------------------------------------------------------------
def test_windowed_line_reading(driver):
    assert driver.read_line_window() is True
