import datetime
import os
import tempfile

TERM = "zolgensma"
ABSENT = "qqxxzzunfindable"
LINES = [f"line {i}" for i in range(1, 41)]


def _corpus():
    """A scratch folder holding one .md (containing TERM) and one .csv."""
    d = tempfile.mkdtemp(prefix="marg_")
    md = os.path.join(d, "notes.md")
    with open(md, "w") as fh:
        fh.write("# Heading\n" + "\n".join(LINES) + f"\n{TERM} appears here.\n")
    csv = os.path.join(d, "table.csv")
    with open(csv, "w") as fh:
        fh.write("a,b,c\n1,2,3\n4,5,6\n")
    return d, md, csv


class _Base:
    def __init__(self, module):
        self.m = module


class ClaudeDriver(_Base):
    def _app(self):
        base = tempfile.mkdtemp(prefix="marg_claude_")
        return self.m.Marginalia(base_path=base, llm_provider=None)

    def lexical_recall_relevance(self):
        app = self._app()
        _d, md, _csv = _corpus()
        app.ingest(md)
        return bool(app.search(TERM)) and not app.search(ABSENT)

    def recall_respects_quota(self):
        app = self._app()
        d, md, csv = _corpus()
        app.ingest(d)
        return len(app.search("line", limit=2)) <= 2

    def filetype_discriminates(self):
        app = self._app()
        _d, md, csv = _corpus()
        a = app.ingest(md)
        b = app.ingest(csv)
        return self._kind(a) != self._kind(b)

    @staticmethod
    def _kind(rec):
        r = rec[0] if isinstance(rec, list) and rec else rec
        return getattr(r, "content_type", None)

    def journal_roundtrip(self):
        app = self._app()
        app.create_journal_entry("t", f"{TERM} was decisive")
        return any(TERM in str(e.content) for e in app.list_journal_entries())

    def read_line_window(self):
        _d, md, _csv = _corpus()
        text = self.m.ContextBuilder._read_lines(None, md, 10, 12)
        return "line 10" in str(text) and "line 40" not in str(text)


class GptDriver(_Base):
    def _lib(self):
        return self.m.Library(tempfile.mkdtemp(prefix="marg_gpt_"))

    def lexical_recall_relevance(self):
        lib = self._lib()
        _d, md, _csv = _corpus()
        lib.ingest_path(md)
        return bool(lib.recall(TERM)) and not lib.recall(ABSENT)

    def recall_respects_quota(self):
        lib = self._lib()
        d, _md, _csv = _corpus()
        lib.ingest_folder(d)
        return len(lib.recall("line", self.m.RecallConfig(lexical_limit=2))) <= 2

    def filetype_discriminates(self):
        lib = self._lib()
        _d, md, csv = _corpus()
        # Document exposes the kind as `mime`
        return lib.ingest_path(md).mime != lib.ingest_path(csv).mime

    def journal_roundtrip(self):
        lib = self._lib()
        lib.catalog.upsert_note(self.m.InvestigationNote(
            note_id="n1", created_at="2024-01-01", updated_at="2024-01-01",
            title="t", body=f"{TERM} was decisive"))
        return any(TERM in str(n.body) for n in lib.catalog.list_notes())

    def read_line_window(self):
        lib = self._lib()
        _d, md, _csv = _corpus()
        doc = lib.ingest_path(md)
        text = lib.read_document_lines(doc.id, 10, 12)
        return "line 10" in str(text) and "line 40" not in str(text)


class DeepseekDriver(_Base):
    def _app(self):
        return self.m.Marginalia(root_folder=tempfile.mkdtemp(prefix="marg_ds_"))

    def lexical_recall_relevance(self):
        app = self._app()
        _d, md, _csv = _corpus()
        app.ingest_file(md)
        return bool(app.search(TERM, rerank=False)) and not app.search(ABSENT, rerank=False)

    def recall_respects_quota(self):
        app = self._app()
        d, _md, _csv = _corpus()
        app.ingest_folder(d)
        return len(app.search("line", top_k=2, rerank=False)) <= 2

    def filetype_discriminates(self):
        app = self._app()
        _d, md, csv = _corpus()
        return app.ingest_file(md).file_type != app.ingest_file(csv).file_type

    def journal_roundtrip(self):
        app = self._app()
        app.library.add_note(self.m.Note(
            id="n1", timestamp=datetime.datetime(2024, 1, 1), question="q",
            answer=f"{TERM} was decisive", citations=[], context_snippets=[], tags=[]))
        return any(TERM in str(n.answer) for n in app.library.get_notes())

    def read_line_window(self):
        _d, md, _csv = _corpus()
        text = self.m.DocumentReader().read_lines(md, 10, 12)
        return "line 10" in str(text) and "line 40" not in str(text)


class GeminiDriver(_Base):
    """Pieces are wired by hand: Ingestor -> LibraryCatalog -> SearchEngine."""

    def _stack(self):
        cat = self.m.LibraryCatalog()
        return self.m.Ingestor(), cat, self.m.SearchEngine(cat)

    def lexical_recall_relevance(self):
        ing, cat, se = self._stack()
        _d, md, _csv = _corpus()
        cat.add_document(ing.ingest(md))
        return bool(se.recall(TERM)) and not se.recall(ABSENT)

    def recall_respects_quota(self):
        ing, cat, se = self._stack()
        _d, md, csv = _corpus()
        cat.add_document(ing.ingest(md))
        cat.add_document(ing.ingest(csv))
        return len(se.recall("line", source_quota=1)) <= 1

    def filetype_discriminates(self):
        ing, _cat, _se = self._stack()
        _d, md, csv = _corpus()
        return ing.ingest(md).file_type != ing.ingest(csv).file_type

    def journal_roundtrip(self):
        _ing, cat, _se = self._stack()
        cat.add_journal_note(self.m.InvestigationNote(
            note_id="n1", timestamp=datetime.datetime(2024, 1, 1), query="q",
            content=f"{TERM} was decisive", citations=""))
        # no getter is exposed; read the generation's own journals table
        rows = cat.conn.execute("SELECT content FROM journals").fetchall()
        return any(TERM in str(r[0]) for r in rows)

    def read_line_window(self):
        ing, _cat, _se = self._stack()
        _d, md, _csv = _corpus()
        doc = ing.ingest(md)
        win = [w for w in doc.windows if "line 10" in str(w.content)]
        return bool(win) and "line 40" not in str(win[0].content)


GENERATIONS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """One hand-written driver per model, written against that model's run0."""
    return GENERATIONS[model](module)
