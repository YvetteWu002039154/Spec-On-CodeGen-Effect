# Behavioral contract — `marginalia` **NL track**

## Description features

| Description feature |
|---|
| "Recalls candidates with lexical search by default" |
| "plus … source quotas" |
| "Ingests text, Markdown, PDFs, DOCX, images, spreadsheets, logs, and archives" |
| "Reads original sections, pages, lines, archive members, or table slices" |
| "writes durable investigation notes that future turns can recall" |

## Behaviors pinned

| # | Group | Behavior |
|---|---|---|
| N1 | Recall (lexical search with source quotas) | **Lexical relevance.** A term present in an indexed document is recalled; a term present in **no** document yields no hit. |
| N2 | Recall (lexical search with source quotas) | **Source quota.** Capping recall to *k* returns at most *k* candidates (asserted only where the search API exposes a limit/quota knob; the engine must first surface a multi-hit set, so the cap is a real reduction). |
| N3 | Ingest (many file kinds) | **File-kind discrimination.** Ingesting a `.md` file and a `.csv` file yields **distinct** recognized kinds (markdown ≠ spreadsheet), not a single generic bucket. |
| N4 | Durable investigation notes | **Journal round-trip.** A written investigation note is retrievable afterwards (a later turn can recall it). |
| N5 | Reading original file windows | **Windowed line read.** Reading a narrow line range returns target line(s) from that range and excludes the far-away boundary lines (a *window*, not the whole file). Line-index conventions (0- vs 1-based, inclusive/exclusive) vary, so the assertion tolerates the exact offset. |

