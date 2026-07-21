# Conformance results — `marginalia` **NL track**

Subjects: the 4 NL generations (`nl/outputcode/{claude,gpt,deepseek,gemini}`).
No reference in this track. Each is driven by its own explicit driver in
`adapter.py`. Suite: `nl/tests/test_conformance.py` (5 behaviors, see
[CONTRACT.md](CONTRACT.md)).

`pass` = behavior matches the contract · `FAIL` = capability wrong or **not
exposed** (this suite does not skip / mark N/A).

## Matrix

| behavior (contract) | claude | gpt | deepseek | gemini |
|---|---|---|---|---|
| N1  lexical recall relevance | pass | pass | pass | pass |
| N2  recall respects a quota/limit | pass | pass | pass | pass |
| N3  file-kind discrimination (.md ≠ .csv) | pass | pass | FAIL | pass |
| N4  journal note round-trip | pass | pass | pass | FAIL |
| N5  windowed line read | FAIL | pass | pass | FAIL |
| **pass / 5** | **4** | **5** | **4** | **3** |

Run summary: **16 passed, 4 failed.**

## Interpretation

All four generations reproduce the two headline recall behaviors — **lexical
relevance** (N1) and a **source quota** (N2) — each over a completely different
engine (SQLite FTS for claude/gpt; an in-memory TF-IDF `LexicalIndex` for
deepseek; a windowed lexical scorer for gemini). No generation returns an
irrelevant document for a term present in nothing, and every one honors its
result-limit knob, so N1/N2 are a clean sweep.

The 4 failures are genuine structural gaps — capabilities the driver exercises
through the real API that the generation does not expose (or exposes wrongly):

- **deepseek / N3.** Its ingest routes files through ordered extractors, and
  `TextExtractor.can_handle` already accepts `.csv`, so both `.md` and `.csv`
  resolve to the *same* text extractor — the pipeline never distinguishes
  markdown from spreadsheet. `_get_extractor` returns `TextExtractor` for both →
  FAIL.
- **gemini / N4.** `LibraryCatalog.add_journal_note` persists a note to a
  `journals` table but the class exposes **no reader** — a written note cannot
  be recalled through the API; the driver's read attempt raises
  `AttributeError` → FAIL. (claude/gpt/deepseek all pair a writer with a
  `list_*`/`get_notes` reader → pass.)
- **claude / N5 and gemini / N5.** claude's line-range reader
  (`get_chunks_by_lines`) returns a whole-file chunk for a small document, so
  the "window" includes the far-away boundary lines (not a real slice); gemini
  produces line windows *at ingest* but has no on-demand "read lines a–b"
  method, so its only window is the whole file. Both → FAIL. deepseek
  (`DocumentReader.read_lines`) and gpt (`Library.read_document_lines`) expose a
  direct range reader → pass.

## Classification

The two lowest scorers (deepseek 4/5, gemini 3/5) are low because of *missing*
surfaces (coarse file-kind routing, write-only journal, no range reader),
which — with explicit per-generation drivers and no skip — are now scored as
behavioral **failures** rather than N/A.

## Reproduce

```bash
cd thesis_repos/shenmintao__marginalia/nl/tests
python3 -m pytest -q -p no:warnings
```
