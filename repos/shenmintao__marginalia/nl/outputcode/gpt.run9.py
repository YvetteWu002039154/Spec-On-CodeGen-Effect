from __future__ import annotations

import os
import re
import io
import json
import math
import time
import uuid
import shutil
import sqlite3
import zipfile
import hashlib
import mimetypes
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _safe_relpath(path: Path, root: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except Exception:
        raise ValueError("Path must be within root")
    return str(rel).replace("\\", "/")


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _normalize_text(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return s


def _tokenize(s: str) -> List[str]:
    s = s.lower()
    return re.findall(r"[a-z0-9]+", s)


def _bm25_idf(n_docs: int, df: int) -> float:
    return math.log(1 + (n_docs - df + 0.5) / (df + 0.5))


def _clamp_int(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


@dataclass(frozen=True)
class DocumentRef:
    doc_id: str
    rel_path: str


@dataclass(frozen=True)
class WindowRef:
    doc_id: str
    window_id: str


@dataclass(frozen=True)
class Citation:
    doc_id: str
    rel_path: str
    window_id: str
    kind: str
    start: int
    end: int
    excerpt: str


@dataclass(frozen=True)
class SearchResult:
    doc_id: str
    rel_path: str
    score: float
    snippet: str


@dataclass(frozen=True)
class ReadWindow:
    doc_id: str
    rel_path: str
    window_id: str
    kind: str
    start: int
    end: int
    content: str


@dataclass(frozen=True)
class AgentAnswer:
    answer: str
    citations: List[Citation]
    notes_doc_id: Optional[str]


class ValidationError(ValueError):
    pass


class NotFoundError(KeyError):
    pass


class StorageError(RuntimeError):
    pass


class SourceQuotaError(RuntimeError):
    pass


class Catalog:
    def __init__(self, name: str, description: str = "") -> None:
        name = name.strip()
        if not name:
            raise ValidationError("Catalog name required")
        self._name = name
        self._description = description.strip()

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description


class Tag:
    def __init__(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise ValidationError("Tag name required")
        if any(ch.isspace() for ch in name):
            raise ValidationError("Tag name must not contain whitespace")
        self._name = name

    @property
    def name(self) -> str:
        return self._name


class View:
    def __init__(self, name: str, query: str, description: str = "") -> None:
        name = name.strip()
        if not name:
            raise ValidationError("View name required")
        query = query.strip()
        if not query:
            raise ValidationError("View query required")
        self._name = name
        self._query = query
        self._description = description.strip()

    @property
    def name(self) -> str:
        return self._name

    @property
    def query(self) -> str:
        return self._query

    @property
    def description(self) -> str:
        return self._description


class JournalEntry:
    def __init__(self, entry_id: str, created_at: datetime, kind: str, payload: Dict[str, Any]) -> None:
        if not entry_id:
            raise ValidationError("entry_id required")
        kind = kind.strip()
        if not kind:
            raise ValidationError("kind required")
        self._entry_id = entry_id
        self._created_at = created_at
        self._kind = kind
        self._payload = dict(payload)

    @property
    def entry_id(self) -> str:
        return self._entry_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def payload(self) -> Dict[str, Any]:
        return dict(self._payload)


class Document:
    def __init__(
        self,
        doc_id: str,
        rel_path: str,
        title: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        created_at: datetime,
        updated_at: datetime,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not doc_id:
            raise ValidationError("doc_id required")
        rel_path = rel_path.strip()
        if not rel_path:
            raise ValidationError("rel_path required")
        title = title.strip()
        if not title:
            title = Path(rel_path).name
        mime_type = (mime_type or "application/octet-stream").strip()
        if size_bytes < 0:
            raise ValidationError("size_bytes must be >= 0")
        sha256 = sha256.strip()
        if not sha256:
            raise ValidationError("sha256 required")
        self._doc_id = doc_id
        self._rel_path = rel_path
        self._title = title
        self._mime_type = mime_type
        self._size_bytes = int(size_bytes)
        self._sha256 = sha256
        self._created_at = created_at
        self._updated_at = updated_at
        self._metadata = dict(metadata or {})

    @property
    def doc_id(self) -> str:
        return self._doc_id

    @property
    def rel_path(self) -> str:
        return self._rel_path

    @property
    def title(self) -> str:
        return self._title

    @property
    def mime_type(self) -> str:
        return self._mime_type

    @property
    def size_bytes(self) -> int:
        return self._size_bytes

    @property
    def sha256(self) -> str:
        return self._sha256

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)


class Window:
    def __init__(
        self,
        window_id: str,
        doc_id: str,
        kind: str,
        start: int,
        end: int,
        content: str,
        created_at: datetime,
    ) -> None:
        if not window_id:
            raise ValidationError("window_id required")
        if not doc_id:
            raise ValidationError("doc_id required")
        kind = kind.strip()
        if not kind:
            raise ValidationError("kind required")
        if start < 0 or end < start:
            raise ValidationError("invalid window range")
        self._window_id = window_id
        self._doc_id = doc_id
        self._kind = kind
        self._start = int(start)
        self._end = int(end)
        self._content = content
        self._created_at = created_at

    @property
    def window_id(self) -> str:
        return self._window_id

    @property
    def doc_id(self) -> str:
        return self._doc_id

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def start(self) -> int:
        return self._start

    @property
    def end(self) -> int:
        return self._end

    @property
    def content(self) -> str:
        return self._content

    @property
    def created_at(self) -> datetime:
        return self._created_at


class Relation:
    def __init__(self, rel_id: str, src_doc_id: str, dst_doc_id: str, kind: str, score: float) -> None:
        if not rel_id:
            raise ValidationError("rel_id required")
        if not src_doc_id or not dst_doc_id:
            raise ValidationError("src/dst required")
        kind = kind.strip()
        if not kind:
            raise ValidationError("kind required")
        if not (0.0 <= score <= 1.0):
            raise ValidationError("score must be in [0,1]")
        self._rel_id = rel_id
        self._src_doc_id = src_doc_id
        self._dst_doc_id = dst_doc_id
        self._kind = kind
        self._score = float(score)

    @property
    def rel_id(self) -> str:
        return self._rel_id

    @property
    def src_doc_id(self) -> str:
        return self._src_doc_id

    @property
    def dst_doc_id(self) -> str:
        return self._dst_doc_id

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def score(self) -> float:
        return self._score


class SourceQuota:
    def __init__(self, max_documents: int = 8, max_windows: int = 16, max_total_chars: int = 24000) -> None:
        if max_documents <= 0 or max_windows <= 0 or max_total_chars <= 0:
            raise ValidationError("quota limits must be > 0")
        self.max_documents = int(max_documents)
        self.max_windows = int(max_windows)
        self.max_total_chars = int(max_total_chars)


class SQLiteStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        _ensure_dir(db_path.parent)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                rel_path TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tags (
                name TEXT PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS doc_tags (
                doc_id TEXT NOT NULL,
                tag_name TEXT NOT NULL,
                PRIMARY KEY (doc_id, tag_name),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (tag_name) REFERENCES tags(name) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS catalogs (
                name TEXT PRIMARY KEY,
                description TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS doc_catalogs (
                doc_id TEXT NOT NULL,
                catalog_name TEXT NOT NULL,
                PRIMARY KEY (doc_id, catalog_name),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (catalog_name) REFERENCES catalogs(name) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS views (
                name TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                description TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS windows (
                window_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                start INTEGER NOT NULL,
                end INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS journal (
                entry_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS relations (
                rel_id TEXT PRIMARY KEY,
                src_doc_id TEXT NOT NULL,
                dst_doc_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                score REAL NOT NULL,
                FOREIGN KEY (src_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (dst_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS doc_text (
                doc_id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS lexicon (
                term TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                tf INTEGER NOT NULL,
                PRIMARY KEY (term, doc_id),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_lexicon_term ON lexicon(term);
            CREATE INDEX IF NOT EXISTS idx_lexicon_doc ON lexicon(doc_id);

            CREATE TABLE IF NOT EXISTS doc_stats (
                doc_id TEXT PRIMARY KEY,
                length INTEGER NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );
            """
        )
        self._conn.commit()

    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql: str, seq_of_params: Iterable[Sequence[Any]]) -> sqlite3.Cursor:
        cur = self._conn.cursor()
        cur.executemany(sql, seq_of_params)
        return cur

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()


class FileRepository:
    def __init__(self, root: Path) -> None:
        self._root = root
        _ensure_dir(root)

    @property
    def root(self) -> Path:
        return self._root

    def abs_path(self, rel_path: str) -> Path:
        p = (self._root / rel_path).resolve()
        if self._root.resolve() not in p.parents and p != self._root.resolve():
            raise ValueError("Path escapes root")
        return p

    def read_bytes(self, rel_path: str) -> bytes:
        p = self.abs_path(rel_path)
        return p.read_bytes()

    def read_text(self, rel_path: str, encoding: str = "utf-8", errors: str = "replace") -> str:
        p = self.abs_path(rel_path)
        return p.read_text(encoding=encoding, errors=errors)

    def write_bytes(self, rel_path: str, data: bytes) -> None:
        p = self.abs_path(rel_path)
        _ensure_dir(p.parent)
        p.write_bytes(data)

    def write_text(self, rel_path: str, text: str, encoding: str = "utf-8") -> None:
        p = self.abs_path(rel_path)
        _ensure_dir(p.parent)
        p.write_text(text, encoding=encoding)

    def exists(self, rel_path: str) -> bool:
        return self.abs_path(rel_path).exists()

    def list_files(self) -> List[str]:
        out: List[str] = []
        for p in self._root.rglob("*"):
            if p.is_file():
                out.append(_safe_relpath(p, self._root))
        out.sort()
        return out


class Ingestor:
    def __init__(self, repo: FileRepository) -> None:
        self._repo = repo

    def detect_mime(self, rel_path: str) -> str:
        mime, _ = mimetypes.guess_type(rel_path)
        return mime or "application/octet-stream"

    def extract_text(self, rel_path: str, mime_type: Optional[str] = None) -> str:
        mime_type = (mime_type or self.detect_mime(rel_path)).lower()
        suffix = Path(rel_path).suffix.lower()

        if mime_type.startswith("text/") or suffix in {".md", ".markdown", ".txt", ".log", ".csv", ".tsv", ".json"}:
            return _normalize_text(self._repo.read_text(rel_path))

        if suffix in {".zip"} or mime_type in {"application/zip"}:
            b = self._repo.read_bytes(rel_path)
            return self._extract_zip_listing(b)

        if suffix in {".pdf", ".docx", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}:
            return ""

        return ""

    def _extract_zip_listing(self, data: bytes) -> str:
        try:
            with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
                names = zf.namelist()
        except Exception:
            return ""
        lines = ["ZIP archive members:"]
        for n in names[:5000]:
            lines.append(n)
        return _normalize_text("\n".join(lines))


class LexicalIndex:
    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def index_document(self, doc_id: str, text: str) -> None:
        tokens = _tokenize(text)
        tf: Dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        length = len(tokens)

        self._store.execute("DELETE FROM lexicon WHERE doc_id = ?", (doc_id,))
        self._store.execute("DELETE FROM doc_stats WHERE doc_id = ?", (doc_id,))
        self._store.execute("INSERT OR REPLACE INTO doc_text(doc_id, text) VALUES(?, ?)", (doc_id, text))
        if tf:
            self._store.executemany(
                "INSERT INTO lexicon(term, doc_id, tf) VALUES(?, ?, ?)",
                ((term, doc_id, freq) for term, freq in tf.items()),
            )
        self._store.execute("INSERT INTO doc_stats(doc_id, length) VALUES(?, ?)", (doc_id, length))
        self._store.commit()

    def delete_document(self, doc_id: str) -> None:
        self._store.execute("DELETE FROM doc_text WHERE doc_id = ?", (doc_id,))
        self._store.execute("DELETE FROM lexicon WHERE doc_id = ?", (doc_id,))
        self._store.execute("DELETE FROM doc_stats WHERE doc_id = ?", (doc_id,))
        self._store.commit()

    def search(self, query: str, limit: int = 20) -> List[Tuple[str, float]]:
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        q_terms = list(dict.fromkeys(q_tokens))

        cur = self._store.execute("SELECT COUNT(*) FROM documents")
        n_docs = int(cur.fetchone()[0] or 0)
        if n_docs <= 0:
            return []

        placeholders = ",".join("?" for _ in q_terms)
        df_rows = self._store.execute(
            f"SELECT term, COUNT(*) FROM lexicon WHERE term IN ({placeholders}) GROUP BY term",
            tuple(q_terms),
        ).fetchall()
        df: Dict[str, int] = {t: int(c) for t, c in df_rows}

        avgdl_row = self._store.execute("SELECT AVG(length) FROM doc_stats").fetchone()
        avgdl = float(avgdl_row[0] or 0.0)
        if avgdl <= 0:
            avgdl = 1.0

        rows = self._store.execute(
            f"""
            SELECT l.doc_id, l.term, l.tf, s.length
            FROM lexicon l
            JOIN doc_stats s ON s.doc_id = l.doc_id
            WHERE l.term IN ({placeholders})
            """,
            tuple(q_terms),
        ).fetchall()

        k1 = 1.2
        b = 0.75
        scores: Dict[str, float] = {}
        for doc_id, term, tf, dl in rows:
            tf = int(tf)
            dl = int(dl)
            dfi = df.get(term, 0)
            if dfi <= 0:
                continue
            idf = _bm25_idf(n_docs, dfi)
            denom = tf + k1 * (1 - b + b * (dl / avgdl))
            score = idf * (tf * (k1 + 1) / (denom if denom else 1.0))
            scores[doc_id] = scores.get(doc_id, 0.0) + float(score)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[: max(1, int(limit))]


class WindowReader:
    def __init__(self, store: SQLiteStore, repo: FileRepository, ingestor: Ingestor) -> None:
        self._store = store
        self._repo = repo
        self._ingestor = ingestor

    def read_windows_for_doc(
        self,
        doc: Document,
        query: str,
        max_windows: int = 3,
        window_chars: int = 1200,
        overlap_chars: int = 150,
    ) -> List[ReadWindow]:
        max_windows = _clamp_int(int(max_windows), 1, 50)
        window_chars = _clamp_int(int(window_chars), 200, 10000)
        overlap_chars = _clamp_int(int(overlap_chars), 0, window_chars - 1)

        text_row = self._store.execute("SELECT text FROM doc_text WHERE doc_id = ?", (doc.doc_id,)).fetchone()
        if text_row is None:
            text = self._ingestor.extract_text(doc.rel_path, doc.mime_type)
        else:
            text = str(text_row[0] or "")

        text = _normalize_text(text)
        if not text:
            return []

        q_terms = set(_tokenize(query))
        if not q_terms:
            return self._slice_windows(doc, text, max_windows, window_chars, overlap_chars)

        positions: List[int] = []
        lower = text.lower()
        for term in list(q_terms)[:20]:
            for m in re.finditer(re.escape(term.lower()), lower):
                positions.append(m.start())
                if len(positions) >= 200:
                    break
            if len(positions) >= 200:
                break

        if not positions:
            return self._slice_windows(doc, text, max_windows, window_chars, overlap_chars)

        positions.sort()
        chosen: List[Tuple[int, int]] = []
        for pos in positions:
            start = max(0, pos - window_chars // 3)
            end = min(len(text), start + window_chars)
            start = max(0, end - window_chars)
            if chosen and start <= chosen[-1][1] - overlap_chars:
                continue
            chosen.append((start, end))
            if len(chosen) >= max_windows:
                break

        out: List[ReadWindow] = []
        for start, end in chosen:
            content = text[start:end]
            window_id = str(uuid.uuid4())
            self._store.execute(
                "INSERT INTO windows(window_id, doc_id, kind, start, end, content, created_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
                (window_id, doc.doc_id, "text", start, end, content, _iso(_utc_now())),
            )
            out.append(ReadWindow(doc.doc_id, doc.rel_path, window_id, "text", start, end, content))
        self._store.commit()
        return out

    def _slice_windows(
        self, doc: Document, text: str, max_windows: int, window_chars: int, overlap_chars: int
    ) -> List[ReadWindow]:
        out: List[ReadWindow] = []
        step = max(1, window_chars - overlap_chars)
        start = 0
        while start < len(text) and len(out) < max_windows:
            end = min(len(text), start + window_chars)
            content = text[start:end]
            window_id = str(uuid.uuid4())
            self._store.execute(
                "INSERT INTO windows(window_id, doc_id, kind, start, end, content, created_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
                (window_id, doc.doc_id, "text", start, end, content, _iso(_utc_now())),
            )
            out.append(ReadWindow(doc.doc_id, doc.rel_path, window_id, "text", start, end, content))
            start += step
        self._store.commit()
        return out


class RelationMiner:
    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def mine_relations(self, doc_id: str, top_k: int = 5) -> List[Relation]:
        top_k = _clamp_int(int(top_k), 0, 50)
        if top_k == 0:
            return []

        row = self._store.execute("SELECT text FROM doc_text WHERE doc_id = ?", (doc_id,)).fetchone()
        if row is None:
            return []
        text = str(row[0] or "")
        tokens = _tokenize(text)
        if not tokens:
            return []

        tf: Dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        terms = sorted(tf.items(), key=lambda x: x[1], reverse=True)[:50]
        query = " ".join(t for t, _ in terms[:12]).strip()
        if not query:
            return []

        idx = LexicalIndex(self._store)
        candidates = idx.search(query, limit=50)
        candidates = [(d, s) for d, s in candidates if d != doc_id]
        if not candidates:
            return []

        max_score = max((s for _, s in candidates), default=0.0)
        if max_score <= 0:
            return []

        self._store.execute("DELETE FROM relations WHERE src_doc_id = ? AND kind = ?", (doc_id, "lexical_overlap"))
        rels: List[Relation] = []
        for dst_doc_id, score in candidates[:top_k]:
            norm = float(score / max_score)
            rel_id = str(uuid.uuid4())
            self._store.execute(
                "INSERT INTO relations(rel_id, src_doc_id, dst_doc_id, kind, score) VALUES(?, ?, ?, ?, ?)",
                (rel_id, doc_id, dst_doc_id, "lexical_overlap", norm),
            )
            rels.append(Relation(rel_id, doc_id, dst_doc_id, "lexical_overlap", norm))
        self._store.commit()
        return rels


class NotesManager:
    def __init__(self, repo: FileRepository, store: SQLiteStore, ingestor: Ingestor, index: LexicalIndex) -> None:
        self._repo = repo
        self._store = store
        self._ingestor = ingestor
        self._index = index

    def write_investigation_notes(
        self,
        title: str,
        body: str,
        citations: List[Citation],
        folder: str = "marginalia_notes",
        tags: Optional[List[str]] = None,
        catalogs: Optional[List[str]] = None,
    ) -> Document:
        title = title.strip() or "Investigation Notes"
        folder = folder.strip().strip("/")

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", title).strip("_")[:60] or "notes"
        filename = f"{ts}_{slug}.md"
        rel_path = f"{folder}/{filename}" if folder else filename

        lines: List[str] = []
        lines.append(f"# {title}")
        lines.append("")
        lines.append(body.rstrip())
        lines.append("")
        if citations:
            lines.append("## Citations")
            lines.append("")
            for c in citations:
                lines.append(f"- {c.rel_path} [{c.kind} {c.start}-{c.end}] (window {c.window_id})")
            lines.append("")
        content = _normalize_text("\n".join(lines)).rstrip() + "\n"

        self._repo.write_text(rel_path, content, encoding="utf-8")
        doc = self._upsert_document_from_file(rel_path, title_override=title)

        if tags:
            for t in tags:
                self._store.execute("INSERT OR IGNORE INTO tags(name) VALUES(?)", (Tag(t).name,))
                self._store.execute("INSERT OR IGNORE INTO doc_tags(doc_id, tag_name) VALUES(?, ?)", (doc.doc_id, t))
        if catalogs:
            for c in catalogs:
                cat = Catalog(c)
                self._store.execute("INSERT OR IGNORE INTO catalogs(name, description) VALUES(?, ?)", (cat.name, ""))
                self._store.execute(
                    "INSERT OR IGNORE INTO doc_catalogs(doc_id, catalog_name) VALUES(?, ?)", (doc.doc_id, cat.name)
                )
        self._store.commit()

        text = self._ingestor.extract_text(rel_path, doc.mime_type)
        self._index.index_document(doc.doc_id, text)
        return doc

    def _upsert_document_from_file(self, rel_path: str, title_override: Optional[str] = None) -> Document:
        abs_path = self._repo.abs_path(rel_path)
        if not abs_path.exists() or not abs_path.is_file():
            raise NotFoundError(rel_path)

        mime, _ = mimetypes.guess_type(rel_path)
        mime_type = mime or "application/octet-stream"
        size_bytes = abs_path.stat().st_size
        sha = _sha256_file(abs_path)
        now = _utc_now()

        row = self._store.execute("SELECT doc_id, created_at FROM documents WHERE rel_path = ?", (rel_path,)).fetchone()
        if row:
            doc_id = str(row[0])
            created_at = datetime.fromisoformat(str(row[1]))
            title = (title_override or Path(rel_path).name).strip() or Path(rel_path).name
            self._store.execute(
                """
                UPDATE documents
                SET title = ?, mime_type = ?, size_bytes = ?, sha256 = ?, updated_at = ?, metadata_json = ?
                WHERE doc_id = ?
                """,
                (title, mime_type, size_bytes, sha, _iso(now), json.dumps({}), doc_id),
            )
        else:
            doc_id = str(uuid.uuid4())
            title = (title_override or Path(rel_path).name).strip() or Path(rel_path).name
            self._store.execute(
                """
                INSERT INTO documents(doc_id, rel_path, title, mime_type, size_bytes, sha256, created_at, updated_at, metadata_json)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (doc_id, rel_path, title, mime_type, size_bytes, sha, _iso(now), _iso(now), json.dumps({})),
            )
            created_at = now

        self._store.commit()
        return Document(
            doc_id=doc_id,
            rel_path=rel_path,
            title=title,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha,
            created_at=created_at,
            updated_at=now,
            metadata={},
        )


class KnowledgeBase:
    def __init__(self, root_folder: Union[str, Path], db_path: Optional[Union[str, Path]] = None) -> None:
        self._root = Path(root_folder).expanduser().resolve()
        _ensure_dir(self._root)
        if db_path is None:
            db_path = self._root / ".marginalia" / "marginalia.sqlite3"
        self._db_path = Path(db_path).expanduser().resolve()
        self._store = SQLiteStore(self._db_path)
        self._repo = FileRepository(self._root)
        self._ingestor = Ingestor(self._repo)
        self._index = LexicalIndex(self._store)
        self._reader = WindowReader(self._store, self._repo, self._ingestor)
        self._miner = RelationMiner(self._store)
        self._notes = NotesManager(self._repo, self._store, self._ingestor, self._index)

    @property
    def root(self) -> Path:
        return self._root

    def close(self) -> None:
        self._store.close()

    def ingest_path(self, path: Union[str, Path], rel_dest: Optional[str] = None) -> DocumentRef:
        src = Path(path).expanduser().resolve()
        if not src.exists() or not src.is_file():
            raise NotFoundError(str(path))

        if rel_dest is None:
            rel_dest = src.name
        rel_dest = rel_dest.strip().lstrip("/").replace("\\", "/")
        if not rel_dest:
            raise ValidationError("rel_dest required")

        data = src.read_bytes()
        self._repo.write_bytes(rel_dest, data)

        doc = self._upsert_document(rel_dest)
        text = self._ingestor.extract_text(rel_dest, doc.mime_type)
        self._index.index_document(doc.doc_id, text)
        self._journal("ingest", {"doc_id": doc.doc_id, "rel_path": doc.rel_path, "sha256": doc.sha256})
        self._miner.mine_relations(doc.doc_id, top_k=5)
        return DocumentRef(doc.doc_id, doc.rel_path)

    def ingest_folder(self, folder: Union[str, Path]) -> List[DocumentRef]:
        src_root = Path(folder).expanduser().resolve()
        if not src_root.exists() or not src_root.is_dir():
            raise NotFoundError(str(folder))

        refs: List[DocumentRef] = []
        for p in sorted(src_root.rglob("*")):
            if not p.is_file():
                continue
            rel = _safe_relpath(p, src_root)
            dest = rel.replace("\\", "/")
            refs.append(self.ingest_path(p, rel_dest=dest))
        return refs

    def rescan(self) -> List[DocumentRef]:
        refs: List[DocumentRef] = []
        for rel_path in self._repo.list_files():
            if rel_path.startswith(".marginalia/"):
                continue
            doc = self._upsert_document(rel_path)
            text = self._ingestor.extract_text(rel_path, doc.mime_type)
            self._index.index_document(doc.doc_id, text)
            refs.append(DocumentRef(doc.doc_id, doc.rel_path))
        self._journal("rescan", {"count": len(refs)})
        return refs

    def add_tag(self, doc_id: str, tag: str) -> None:
        t = Tag(tag).name
        self._require_doc(doc_id)
        self._store.execute("INSERT OR IGNORE INTO tags(name) VALUES(?)", (t,))
        self._store.execute("INSERT OR IGNORE INTO doc_tags(doc_id, tag_name) VALUES(?, ?)", (doc_id, t))
        self._store.commit()
        self._journal("tag_add", {"doc_id": doc_id, "tag": t})

    def remove_tag(self, doc_id: str, tag: str) -> None:
        t = Tag(tag).name
        self._require_doc(doc_id)
        self._store.execute("DELETE FROM doc_tags WHERE doc_id = ? AND tag_name = ?", (doc_id, t))
        self._store.commit()
        self._journal("tag_remove", {"doc_id": doc_id, "tag": t})

    def create_catalog(self, name: str, description: str = "") -> None:
        c = Catalog(name, description)
        self._store.execute("INSERT OR REPLACE INTO catalogs(name, description) VALUES(?, ?)", (c.name, c.description))
        self._store.commit()
        self._journal("catalog_upsert", {"name": c.name})

    def add_to_catalog(self, doc_id: str, catalog_name: str) -> None:
        self._require_doc(doc_id)
        cat = Catalog(catalog_name)
        self._store.execute("INSERT OR IGNORE INTO catalogs(name, description) VALUES(?, ?)", (cat.name, ""))
        self._store.execute(
            "INSERT OR IGNORE INTO doc_catalogs(doc_id, catalog_name) VALUES(?, ?)", (doc_id, cat.name)
        )
        self._store.commit()
        self._journal("catalog_add_doc", {"doc_id": doc_id, "catalog": cat.name})

    def remove_from_catalog(self, doc_id: str, catalog_name: str) -> None:
        self._require_doc(doc_id)
        cat = Catalog(catalog_name)
        self._store.execute("DELETE FROM doc_catalogs WHERE doc_id = ? AND catalog_name = ?", (doc_id, cat.name))
        self._store.commit()
        self._journal("catalog_remove_doc", {"doc_id": doc_id, "catalog": cat.name})

    def create_view(self, name: str, query: str, description: str = "") -> None:
        v = View(name, query, description)
        self._store.execute(
            "INSERT OR REPLACE INTO views(name, query, description) VALUES(?, ?, ?)",
            (v.name, v.query, v.description),
        )
        self._store.commit()
        self._journal("view_upsert", {"name": v.name})

    def list_documents(self, limit: int = 100, offset: int = 0) -> List[Document]:
        limit = _clamp_int(int(limit), 1, 1000)
        offset = max(0, int(offset))
        rows = self._store.execute(
            """
            SELECT doc_id, rel_path, title, mime_type, size_bytes, sha256, created_at, updated_at, metadata_json
            FROM documents
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [self._row_to_doc(r) for r in rows]

    def get_document(self, doc_id: str) -> Document:
        row = self._store.execute(
            """
            SELECT doc_id, rel_path, title, mime_type, size_bytes, sha256, created_at, updated_at, metadata_json
            FROM documents WHERE doc_id = ?
            """,
            (doc_id,),
        ).fetchone()
        if not row:
            raise NotFoundError(doc_id)
        return self._row_to_doc(row)

    def search(self, query: str, limit: int = 20) -> List[SearchResult]:
        ranked = self._index.search(query, limit=limit)
        if not ranked:
            return []
        doc_ids = [d for d, _ in ranked]
        placeholders = ",".join("?" for _ in doc_ids)
        rows = self._store.execute(
            f"""
            SELECT doc_id, rel_path, title
            FROM documents
            WHERE doc_id IN ({placeholders})
            """,
            tuple(doc_ids),
        ).fetchall()
        info = {doc_id: (rel_path, title) for doc_id, rel_path, title in rows}

        out: List[SearchResult] = []
        for doc_id, score in ranked:
            rel_path, title = info.get(doc_id, ("", ""))
            snippet = title or rel_path
            out.append(SearchResult(doc_id=doc_id, rel_path=rel_path, score=float(score), snippet=snippet))
        return out

    def read_relevant_windows(
        self,
        doc_ids: List[str],
        query: str,
        max_windows_per_doc: int = 3,
        window_chars: int = 1200,
    ) -> List[ReadWindow]:
        out: List[ReadWindow] = []
        for doc_id in doc_ids:
            doc = self.get_document(doc_id)
            out.extend(
                self._reader.read_windows_for_doc(
                    doc, query=query, max_windows=max_windows_per_doc, window_chars=window_chars
                )
            )
        self._journal(
            "read_windows",
            {"query": query, "doc_ids": doc_ids, "windows": [w.window_id for w in out]},
        )
        return out

    def write_notes(
        self,
        title: str,
        body: str,
        citations: List[Citation],
        folder: str = "marginalia_notes",
        tags: Optional[List[str]] = None,
        catalogs: Optional[List[str]] = None,
    ) -> DocumentRef:
        doc = self._notes.write_investigation_notes(
            title=title, body=body, citations=citations, folder=folder, tags=tags, catalogs=catalogs
        )
        self._journal("write_notes", {"doc_id": doc.doc_id, "rel_path": doc.rel_path})
        return DocumentRef(doc.doc_id, doc.rel_path)

    def list_journal(self, limit: int = 200, offset: int = 0) -> List[JournalEntry]:
        limit = _clamp_int(int(limit), 1, 2000)
        offset = max(0, int(offset))
        rows = self._store.execute(
            """
            SELECT entry_id, created_at, kind, payload_json
            FROM journal
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        out: List[JournalEntry] = []
        for entry_id, created_at, kind, payload_json in rows:
            out.append(
                JournalEntry(
                    entry_id=str(entry_id),
                    created_at=datetime.fromisoformat(str(created_at)),
                    kind=str(kind),
                    payload=json.loads(str(payload_json) or "{}"),
                )
            )
        return out

    def list_relations(self, doc_id: str, kind: Optional[str] = None, limit: int = 50) -> List[Relation]:
        self._require_doc(doc_id)
        limit = _clamp_int(int(limit), 1, 500)
        if kind is None:
            rows = self._store.execute(
                "SELECT rel_id, src_doc_id, dst_doc_id, kind, score FROM relations WHERE src_doc_id = ? ORDER BY score DESC LIMIT ?",
                (doc_id, limit),
            ).fetchall()
        else:
            k = kind.strip()
            rows = self._store.execute(
                "SELECT rel_id, src_doc_id, dst_doc_id, kind, score FROM relations WHERE src_doc_id = ? AND kind = ? ORDER BY score DESC LIMIT ?",
                (doc_id, k, limit),
            ).fetchall()
        return [Relation(str(r[0]), str(r[1]), str(r[2]), str(r[3]), float(r[4])) for r in rows]

    def _row_to_doc(self, row: Sequence[Any]) -> Document:
        doc_id, rel_path, title, mime_type, size_bytes, sha256, created_at, updated_at, metadata_json = row
        md = json.loads(str(metadata_json) or "{}")
        return Document(
            doc_id=str(doc_id),
            rel_path=str(rel_path),
            title=str(title),
            mime_type=str(mime_type),
            size_bytes=int(size_bytes),
            sha256=str(sha256),
            created_at=datetime.fromisoformat(str(created_at)),
            updated_at=datetime.fromisoformat(str(updated_at)),
            metadata=md,
        )

    def _upsert_document(self, rel_path: str) -> Document:
        abs_path = self._repo.abs_path(rel_path)
        if not abs_path.exists() or not abs_path.is_file():
            raise NotFoundError(rel_path)

        mime_type = self._ingestor.detect_mime(rel_path)
        size_bytes = abs_path.stat().st_size
        sha = _sha256_file(abs_path)
        now = _utc_now()

        row = self._store.execute("SELECT doc_id, created_at, sha256 FROM documents WHERE rel_path = ?", (rel_path,)).fetchone()
        if row:
            doc_id = str(row[0])
            created_at = datetime.fromisoformat(str(row[1]))
            prev_sha = str(row[2])
            title = Path(rel_path).name
            if prev_sha != sha:
                self._store.execute(
                    """
                    UPDATE documents
                    SET title = ?, mime_type = ?, size_bytes = ?, sha256 = ?, updated_at = ?
                    WHERE doc_id = ?
                    """,
                    (title, mime_type, size_bytes, sha, _iso(now), doc_id),
                )
            else:
                self._store.execute(
                    "UPDATE documents SET updated_at = ? WHERE doc_id = ?",
                    (_iso(now), doc_id),
                )
        else:
            doc_id = str(uuid.uuid4())
            created_at = now
            title = Path(rel_path).name
            self._store.execute(
                """
                INSERT INTO documents(doc_id, rel_path, title, mime_type, size_bytes, sha256, created_at, updated_at, metadata_json)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (doc_id, rel_path, title, mime_type, size_bytes, sha, _iso(now), _iso(now), json.dumps({})),
            )
        self._store.commit()
        return Document(
            doc_id=doc_id,
            rel_path=rel_path,
            title=title,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha,
            created_at=created_at,
            updated_at=now,
            metadata={},
        )

    def _require_doc(self, doc_id: str) -> None:
        row = self._store.execute("SELECT 1 FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
        if not row:
            raise NotFoundError(doc_id)

    def _journal(self, kind: str, payload: Dict[str, Any]) -> None:
        entry_id = str(uuid.uuid4())
        self._store.execute(
            "INSERT INTO journal(entry_id, created_at, kind, payload_json) VALUES(?, ?, ?, ?)",
            (entry_id, _iso(_utc_now()), kind, json.dumps(payload)),
        )
        self._store.commit()


class LLMClient:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class DeterministicLLM(LLMClient):
    def generate(self, prompt: str) -> str:
        prompt = prompt.strip()
        if not prompt:
            return ""
        lines = [ln.strip() for ln in prompt.splitlines() if ln.strip()]
        tail = "\n".join(lines[-12:])
        return _normalize_text(
            "Cited synthesis (deterministic stub):\n"
            + tail[:2000]
        )


class ResearchAgent:
    def __init__(
        self,
        kb: KnowledgeBase,
        llm: Optional[LLMClient] = None,
        quota: Optional[SourceQuota] = None,
    ) -> None:
        self._kb = kb
        self._llm = llm or DeterministicLLM()
        self._quota = quota or SourceQuota()

    @property
    def quota(self) -> SourceQuota:
        return self._quota

    def answer(self, question: str, search_limit: int = 20) -> AgentAnswer:
        question = question.strip()
        if not question:
            raise ValidationError("question required")

        candidates = self._kb.search(question, limit=search_limit)
        doc_ids: List[str] = []
        for r in candidates:
            if r.doc_id not in doc_ids:
                doc_ids.append(r.doc_id)
            if len(doc_ids) >= self._quota.max_documents:
                break

        windows: List[ReadWindow] = []
        total_chars = 0
        for doc_id in doc_ids:
            if len(windows) >= self._quota.max_windows:
                break
            remaining_windows = self._quota.max_windows - len(windows)
            per_doc = min(3, remaining_windows)
            ws = self._kb.read_relevant_windows([doc_id], query=question, max_windows_per_doc=per_doc, window_chars=1200)
            for w in ws:
                if len(windows) >= self._quota.max_windows:
                    break
                if total_chars + len(w.content) > self._quota.max_total_chars:
                    break
                windows.append(w)
                total_chars += len(w.content)
            if total_chars >= self._quota.max_total_chars:
                break

        if not windows and candidates:
            raise SourceQuotaError("No readable windows available within quota")

        citations: List[Citation] = []
        for w in windows:
            excerpt = w.content[:400].strip()
            citations.append(
                Citation(
                    doc_id=w.doc_id,
                    rel_path=w.rel_path,
                    window_id=w.window_id,
                    kind=w.kind,
                    start=w.start,
                    end=w.end,
                    excerpt=excerpt,
                )
            )

        prompt = self._build_prompt(question, windows)
        answer_text = self._llm.generate(prompt).strip()
        if not answer_text:
            answer_text = "No answer generated."

        notes_doc_id: Optional[str] = None
        notes_ref = self._kb.write_notes(
            title=f"Investigation: {question[:80]}",
            body=answer_text,
            citations=citations,
            folder="marginalia_notes",
            tags=["investigation"],
            catalogs=None,
        )
        notes_doc_id = notes_ref.doc_id

        return AgentAnswer(answer=answer_text, citations=citations, notes_doc_id=notes_doc_id)

    def _build_prompt(self, question: str, windows: List[ReadWindow]) -> str:
        parts: List[str] = []
        parts.append("You are Marginalia, a local-first research agent.")
        parts.append("Answer the question using ONLY the provided source windows. Include citations by window id.")
        parts.append("")
        parts.append(f"Question: {question}")
        parts.append("")
        parts.append("Source windows:")
        for w in windows:
            parts.append(f"[{w.window_id}] {w.rel_path} ({w.kind} {w.start}-{w.end})")
            parts.append(w.content.strip())
            parts.append("")
        parts.append("Write a concise answer with citations like [window_id].")
        return _normalize_text("\n".join(parts)).strip() + "\n"


__all__ = [
    "KnowledgeBase",
    "ResearchAgent",
    "LLMClient",
    "DeterministicLLM",
    "SourceQuota",
    "Document",
    "Window",
    "Relation",
    "Catalog",
    "Tag",
    "View",
    "JournalEntry",
    "DocumentRef",
    "WindowRef",
    "Citation",
    "SearchResult",
    "ReadWindow",
    "AgentAnswer",
    "ValidationError",
    "NotFoundError",
    "StorageError",
    "SourceQuotaError",
]