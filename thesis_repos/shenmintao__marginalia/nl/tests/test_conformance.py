"""Behavior-conformance suite for `marginalia` **NL track**.

Each of the 4 NL generations is driven by its own explicit driver (`adapter.py`)
that names the concrete classes/methods it uses. Expected behavior comes from
CONTRACT.md (derived by comparing `nl/input/description.txt` with the origin
`src/marginalia/`). There is no skip: a capability a generation does not expose
is a behavioral FAILURE. Each test pins one contract behavior (Nn).
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import build_driver  # noqa: E402
from loader import gencode_paths, load_gencodemodule  # noqa: E402

_DRIVERS = {
    ident: build_driver(ident.split("/")[-1], load_gencodemodule(ident, path))
    for ident, path in gencode_paths()
}


@pytest.fixture(params=sorted(_DRIVERS))
def driver(request):
    return _DRIVERS[request.param]


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
