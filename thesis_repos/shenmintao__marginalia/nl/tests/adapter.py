import datetime
import os
import pathlib
import tempfile

_TOKEN = "zorblatt"      # distinctive term present in a seeded doc
_ABSENT = "qwxzzyq"      # term present in no doc

_WINDOW_LINES = [
    "other1",
    "LINE2_" + _TOKEN,
    "LINE3_" + _TOKEN,
    "other4",
    "other5",
]


def _tmp(prefix="marg_"):
    return tempfile.mkdtemp(prefix=prefix)


def _write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _keys(results):
    """Normalize a recall result set to a flat list of document keys."""
    out = []
    for item in results or []:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, (tuple, list)) and item:
            out.append(str(item[0]))
        else:
            for attr in ("doc_id", "document_id", "id", "window_id"):
                v = getattr(item, attr, None)
                if v:
                    out.append(str(v))
                    break
    return out


def _window_ok(txt):
    """A windowed read returns a target line and excludes the far boundaries."""
    return (("LINE2_" in txt or "LINE3_" in txt)
            and "other1" not in txt and "other5" not in txt)


# ============================================================================
# One driver per generation. `m` is that generation's loaded module.
# ============================================================================

class ClaudeDriver:
    model = "claude"

    def __init__(self, m):
        self.m = m

    def _facade(self):
        return self.m.Marginalia(base_path=_tmp("marg_claude_"))

    def _ingest_corpus(self, corpus):
        marg = self._facade()
        src = _tmp("marg_claude_src_")
        for key, text in corpus:
            p = os.path.join(src, key + ".txt")
            _write(p, text)
            marg.ingest(p)
        return marg

    def lexical_recall_relevance(self):
        marg = self._ingest_corpus([
            ("alpha", f"alpha beta {_TOKEN} gamma delta"),
            ("bravo", "lorem ipsum dolor sit amet")])
        present = _keys(marg.search(_TOKEN, limit=50))
        absent = _keys(marg.search(_ABSENT, limit=50))
        return len(present) >= 1 and len(absent) == 0

    def recall_respects_quota(self):
        marg = self._ingest_corpus(
            [(f"d{i}", f"{_TOKEN} filler content number {i}") for i in range(4)])
        full = _keys(marg.search(_TOKEN, limit=50))
        capped = _keys(marg.search(_TOKEN, limit=1))
        return len(full) > 1 and len(capped) <= 1

    def filetype_discriminates(self):
        ing = self.m.FileIngester()
        tmp = _tmp("marg_claude_ft_")
        md = os.path.join(tmp, "note.md")
        cs = os.path.join(tmp, "table.csv")
        _write(md, "# Title\n\nbody\n")
        _write(cs, "a,b,c\n1,2,3\n")
        return ing._detect_content_type(md) != ing._detect_content_type(cs)

    def journal_roundtrip(self):
        marg = self._facade()
        marker = "MARKER_" + _TOKEN
        marg.create_journal_entry("t", marker)
        notes = marg.list_journal_entries()
        return any(marker in (getattr(n, "content", "") or "") for n in notes)

    def read_line_window(self):
        db = self.m.Database(os.path.join(_tmp("marg_claude_db_"), "m.db"))
        store = self.m.DocumentStore(db, _tmp("marg_claude_base_"))
        path = os.path.join(_tmp("marg_claude_doc_"), "doc.txt")
        _write(path, "\n".join(_WINDOW_LINES) + "\n")
        doc = store.ingest_file(path)
        chunks = store.get_chunks_by_lines(doc.doc_id, 2, 3)
        return _window_ok("\n".join(c.content for c in chunks))


class GptDriver:
    model = "gpt"

    def __init__(self, m):
        self.m = m

    def _library(self):
        return self.m.Library(_tmp("marg_gpt_"))

    def _ingest_corpus(self, corpus):
        lib = self._library()
        src = _tmp("marg_gpt_src_")
        for key, text in corpus:
            p = os.path.join(src, key + ".txt")
            _write(p, text)
            lib.ingest_path(p)
        return lib

    def lexical_recall_relevance(self):
        lib = self._ingest_corpus([
            ("alpha", f"alpha beta {_TOKEN} gamma delta"),
            ("bravo", "lorem ipsum dolor sit amet")])
        present = _keys(lib.recall(_TOKEN, self.m.RecallConfig(lexical_limit=50)))
        absent = _keys(lib.recall(_ABSENT, self.m.RecallConfig(lexical_limit=50)))
        return len(present) >= 1 and len(absent) == 0

    def recall_respects_quota(self):
        lib = self._ingest_corpus(
            [(f"d{i}", f"{_TOKEN} filler content number {i}") for i in range(4)])
        full = _keys(lib.recall(_TOKEN, self.m.RecallConfig(lexical_limit=50)))
        capped = _keys(lib.recall(_TOKEN, self.m.RecallConfig(lexical_limit=1)))
        return len(full) > 1 and len(capped) <= 1

    def filetype_discriminates(self):
        return self.m._detect_mime(pathlib.Path("note.md")) != \
            self.m._detect_mime(pathlib.Path("table.csv"))

    def journal_roundtrip(self):
        lib = self._library()
        marker = "MARKER_" + _TOKEN
        lib.write_note("t", marker)
        notes = lib.list_notes()
        return any(marker in (getattr(n, "body", "") or "") for n in notes)

    def read_line_window(self):
        lib = self._library()
        p = os.path.join(_tmp("marg_gpt_rd_"), "doc.txt")
        _write(p, "\n".join(_WINDOW_LINES) + "\n")
        doc = lib.ingest_path(p)
        return _window_ok(lib.read_document_lines(doc.id, 2, 3).text)


class DeepseekDriver:
    model = "deepseek"

    def __init__(self, m):
        self.m = m

    def _index(self, corpus):
        idx = self.m.LexicalIndex()
        for key, text in corpus:
            idx.add_document(key, text)
        return idx

    def lexical_recall_relevance(self):
        idx = self._index([
            ("alpha", f"alpha beta {_TOKEN} gamma delta"),
            ("bravo", "lorem ipsum dolor sit amet")])
        present = _keys(idx.search(_TOKEN, top_k=50))
        absent = _keys(idx.search(_ABSENT, top_k=50))
        return len(present) >= 1 and len(absent) == 0

    def recall_respects_quota(self):
        idx = self._index(
            [(f"d{i}", f"{_TOKEN} filler content number {i}") for i in range(4)])
        full = _keys(idx.search(_TOKEN, top_k=50))
        capped = _keys(idx.search(_TOKEN, top_k=1))
        return len(full) > 1 and len(capped) <= 1

    def filetype_discriminates(self):
        lib = self.m.Library(_tmp("marg_ds_"))
        ing = self.m.FileIngestor(lib)
        tmp = _tmp("marg_ds_ft_")
        md = os.path.join(tmp, "note.md")
        cs = os.path.join(tmp, "table.csv")
        _write(md, "# Title\n\nbody\n")
        _write(cs, "a,b,c\n1,2,3\n")
        return type(ing._get_extractor(md)).__name__ != \
            type(ing._get_extractor(cs)).__name__

    def journal_roundtrip(self):
        lib = self.m.Library(_tmp("marg_ds_j_"))
        marker = "MARKER_" + _TOKEN
        note = self.m.Note(id="n1", timestamp=datetime.datetime.now(),
                           question=marker, answer="a")
        lib.add_note(note)
        return any(marker in (getattr(n, "question", "") or "") for n in lib.get_notes())

    def read_line_window(self):
        reader = self.m.DocumentReader()
        path = os.path.join(_tmp("marg_ds_rd_"), "doc.txt")
        _write(path, "\n".join(_WINDOW_LINES) + "\n")
        return _window_ok(reader.read_lines(path, 2, 3) or "")


class GeminiDriver:
    model = "gemini"

    def __init__(self, m):
        self.m = m

    def _catalog_with(self, corpus):
        cat = self.m.LibraryCatalog()
        ing = self.m.Ingestor()
        src = _tmp("marg_gm_")
        for key, text in corpus:
            p = os.path.join(src, key + ".txt")
            _write(p, text)
            cat.add_document(ing.ingest(p))
        return cat

    def lexical_recall_relevance(self):
        cat = self._catalog_with([
            ("alpha", f"alpha beta {_TOKEN} gamma delta"),
            ("bravo", "lorem ipsum dolor sit amet")])
        eng = self.m.SearchEngine(cat)
        present = _keys(eng.recall(_TOKEN, source_quota=50))
        absent = _keys(eng.recall(_ABSENT, source_quota=50))
        return len(present) >= 1 and len(absent) == 0

    def recall_respects_quota(self):
        cat = self._catalog_with(
            [(f"d{i}", f"{_TOKEN} filler content number {i}") for i in range(4)])
        eng = self.m.SearchEngine(cat)
        full = _keys(eng.recall(_TOKEN, source_quota=50))
        capped = _keys(eng.recall(_TOKEN, source_quota=1))
        return len(full) > 1 and len(capped) <= 1

    def filetype_discriminates(self):
        ing = self.m.Ingestor()
        tmp = _tmp("marg_gm_ft_")
        md = os.path.join(tmp, "note.md")
        cs = os.path.join(tmp, "table.csv")
        _write(md, "# Title\n\nbody\n")
        _write(cs, "a,b,c\n1,2,3\n")
        return ing.ingest(md).file_type != ing.ingest(cs).file_type

    def journal_roundtrip(self):
        cat = self.m.LibraryCatalog()
        marker = "MARKER_" + _TOKEN
        note = self.m.InvestigationNote(note_id="n1", timestamp=datetime.datetime.now(),
                                        query="q", content=marker, citations=[])
        cat.add_journal_note(note)
        notes = cat.list_journal_notes()
        return any(marker in (getattr(n, "content", "") or "") for n in notes)

    def read_line_window(self):
        cat = self.m.LibraryCatalog()
        ing = self.m.Ingestor()
        path = os.path.join(_tmp("marg_gm_rd_"), "doc.txt")
        _write(path, "\n".join(_WINDOW_LINES) + "\n")
        cat.add_document(ing.ingest(path))
        return _window_ok(" ".join(w.content for w in cat.get_all_windows()))


DRIVERS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """Wrap a loaded generation module in its explicit driver."""
    return DRIVERS[model](module)
