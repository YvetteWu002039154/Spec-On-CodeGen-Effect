# Behavioral contract — `marginalia` **NL track**

Reference for grounding (not a test subject): origin repo
`marginalia-main/src/marginalia/`. There is **no reference subject** in the NL
track — behaviors are pinned by comparing the **NL description**
(`nl/input/description.txt`) with the origin code, then asserting the observable
capabilities every reasonable implementation of that prose would expose.

Behaviors are asserted on **observable capability and effect**. The four
generations diverge sharply (a sqlite-FTS `Marginalia` facade, a
`Library`/`Catalog` + FTS `RecallEngine`, standalone in-memory components, and a
`LibraryCatalog` + `SearchEngine` stack), so each generation is driven by its
own explicit driver (`adapter.py`) that names the exact concrete classes and
methods it uses. A capability a generation does not expose is a behavioral
**FAILURE** — this suite does not skip / mark N/A. The driver attempts the real
API and the resulting empty result, wrong value, or `AttributeError` fails the
assert.

## Description feature → origin grounding

| Description feature | Origin evidence |
|---|---|
| "Recalls candidates with lexical search by default" | `pipelines/_text_indexer.py` + repositories drive SQLite FTS lexical recall |
| "plus … source quotas" | recall caps candidates per query / per source (search API `limit`/quota) |
| "Ingests text, Markdown, PDFs, DOCX, images, spreadsheets, logs, and archives" | `pipelines/registry.py` dispatches per file *kind* (`text`/`pdf`/`docx`/`image`/`spreadsheet`/`log`/`archive`) |
| "Reads original sections, pages, lines, archive members, or table slices" | `agent/read_compression.py` + pipeline window readers return a bounded slice |
| "writes durable investigation notes that future turns can recall" | `db/models/ai_recall.py::Journal` + `repositories/journal.py` persist & re-read notes |

## Behaviors pinned

### Recall (lexical search with source quotas)
- **N1. Lexical relevance.** A term present in an indexed document is recalled;
  a term present in **no** document yields no hit.
- **N2. Source quota.** Capping recall to *k* returns at most *k* candidates
  (asserted only where the search API exposes a limit/quota knob; the engine
  must first surface a multi-hit set, so the cap is a real reduction).

### Ingest (many file kinds)
- **N3. File-kind discrimination.** Ingesting a `.md` file and a `.csv` file
  yields **distinct** recognized kinds (markdown ≠ spreadsheet), not a single
  generic bucket.

### Durable investigation notes
- **N4. Journal round-trip.** A written investigation note is retrievable
  afterwards (a later turn can recall it).

### Reading original file windows
- **N5. Windowed line read.** Reading a narrow line range returns target line(s)
  from that range and excludes the far-away boundary lines (a *window*, not the
  whole file). Line-index conventions (0- vs 1-based, inclusive/exclusive) vary,
  so the assertion tolerates the exact offset.

## Notes for the drivers

Each generation's driver wires the behavior through that generation's own API:

- **Search (N1/N2)** — claude drives the `Marginalia` facade (`ingest` +
  `search(limit=…)`), gpt the `Library` facade (`ingest_path` + `recall` with
  `RecallConfig(lexical_limit=…)`), deepseek the standalone `LexicalIndex`
  (`add_document` + `search(top_k=…)`), gemini the `Ingestor` +
  `LibraryCatalog` + `SearchEngine.recall(source_quota=…)` stack. Absent-term →
  empty guards against an engine that returns everything regardless of
  relevance; the quota knob must cut a multi-hit set down.
- **N3** — claude `FileIngester._detect_content_type`, gpt `_detect_mime`,
  gemini `Ingestor.supported_extensions` (via `ingest().file_type`), deepseek
  `FileIngestor._get_extractor`. deepseek FAILS: its `TextExtractor.can_handle`
  accepts both `.md` and `.csv`, so both collapse to the same extractor.
- **N4** — a write-note method paired with a list-note reader on the same
  object (claude `create_journal_entry`/`list_journal_entries`, gpt
  `write_note`/`list_notes`, deepseek `Note` + `add_note`/`get_notes`). gemini
  FAILS: `LibraryCatalog.add_journal_note` persists a note but the class exposes
  no reader (`AttributeError`).
- **N5** — a direct line-range reader (deepseek `DocumentReader.read_lines`, gpt
  `Library.read_document_lines`). claude FAILS: its `get_chunks_by_lines` returns
  a whole-file chunk (no true line window); gemini FAILS: it only produces
  windows at ingest with no on-demand "read lines a–b".
