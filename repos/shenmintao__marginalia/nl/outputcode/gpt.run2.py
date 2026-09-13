from __future__ import annotations

import base64
import dataclasses
import datetime as _dt
import hashlib
import io
import json
import math
import os
import re
import shutil
import sqlite3
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union


class MarginaliaError(Exception):
    pass


class ValidationError(MarginaliaError):
    pass


class NotFoundError(MarginaliaError):
    pass


class IngestError(MarginaliaError):
    pass


class SearchError(MarginaliaError):
    pass


class ReadError(MarginaliaError):
    pass


class AnswerError(MarginaliaError):
    pass


def _utc_now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_relpath(path: Path, root: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except Exception as e:
        raise ValidationError(f"Path {path} is not under root {root}") from e
    return str(rel).replace("\\", "/")


def _normalize_tag(tag: str) -> str:
    tag = tag.strip()
    if not tag:
        raise ValidationError("Tag cannot be empty")
    if len(tag) > 128:
        raise ValidationError("Tag too long")
    if any(c in tag for c in "\n\r\t"):
        raise ValidationError("Tag contains invalid whitespace")
    return tag


def _normalize_catalog(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValidationError("Catalog name cannot be empty")
    if len(name) > 128:
        raise ValidationError("Catalog name too long")
    return name


def _normalize_view(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValidationError("View name cannot be empty")
    if len(name) > 128:
        raise ValidationError("View name too long")
    return name


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9_]+", text.lower())


def _bm25_idf(n_docs: int, df: int) -> float:
    return math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))


def _clamp_int(name: str, value: int, min_v: int, max_v: int) -> int:
    if not isinstance(value, int):
        raise ValidationError(f"{name} must be int")
    if value < min_v or value > max_v:
        raise ValidationError(f"{name} must be in [{min_v}, {max_v}]")
    return value


def _clamp_float(name: str, value: float, min_v: float, max_v: float) -> float:
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be float")
    v = float(value)
    if v < min_v or v > max_v:
        raise ValidationError(f"{name} must be in [{min_v}, {max_v}]")
    return v


@dataclass(frozen=True)
class SourceRef:
    document_id: int
    relpath: str
    window_type: str
    start: int
    end: int
    locator: str


@dataclass(frozen=True)
class EvidenceWindow:
    source: SourceRef
    text: str


@dataclass(frozen=True)
class Candidate:
    document_id: int
    relpath: str
    score: float
    reason: str


@dataclass(frozen=True)
class Answer:
    question: str
    answer: str
    citations: List[SourceRef]
    created_at: str
    investigation_note_id: int


class Storage:
    def __init__(self, db_path: Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def _migrate(self) -> None:
        cur = self._conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                relpath TEXT NOT NULL UNIQUE,
                abspath TEXT NOT NULL,
                filetype TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                mtime REAL NOT NULL,
                sha256 TEXT NOT NULL,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS document_metadata (
                document_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (document_id, key),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS document_tags (
                document_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (document_id, tag_id),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS catalogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_documents (
                catalog_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                PRIMARY KEY (catalog_id, document_id),
                FOREIGN KEY (catalog_id) REFERENCES catalogs(id) ON DELETE CASCADE,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                query_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS journals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                journal_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                title TEXT,
                body TEXT NOT NULL,
                FOREIGN KEY (journal_id) REFERENCES journals(id) ON DELETE CASCADE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_document_id INTEGER NOT NULL,
                to_document_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                weight REAL NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(from_document_id, to_document_id, relation_type),
                FOREIGN KEY (from_document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (to_document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                text TEXT NOT NULL,
                token_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(document_id, chunk_index),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chunk_terms (
                chunk_id INTEGER NOT NULL,
                term TEXT NOT NULL,
                tf INTEGER NOT NULL,
                PRIMARY KEY (chunk_id, term),
                FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS term_stats (
                term TEXT PRIMARY KEY,
                df INTEGER NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS investigations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                citations_json TEXT NOT NULL,
                note TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ingest_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                relpath TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT
            )
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


class FileIngestor:
    SUPPORTED_EXTENSIONS = {
        ".txt",
        ".md",
        ".markdown",
        ".log",
        ".csv",
        ".tsv",
        ".json",
        ".pdf",
        ".docx",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".webp",
        ".zip",
        ".tar",
        ".gz",
        ".tgz",
        ".tar.gz",
    }

    def __init__(self, root: Path):
        self._root = Path(root)

    def detect_filetype(self, path: Path) -> str:
        p = Path(path)
        name = p.name.lower()
        if name.endswith(".tar.gz"):
            return "archive:tar.gz"
        if name.endswith(".tgz"):
            return "archive:tar.gz"
        ext = p.suffix.lower()
        if ext in (".txt", ".md", ".markdown", ".log"):
            return "text"
        if ext in (".csv", ".tsv"):
            return "spreadsheet"
        if ext == ".json":
            return "json"
        if ext == ".pdf":
            return "pdf"
        if ext == ".docx":
            return "docx"
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
            return "image"
        if ext == ".zip":
            return "archive:zip"
        if ext == ".tar":
            return "archive:tar"
        if ext == ".gz":
            return "archive:gz"
        return "binary"

    def _read_text_bytes(self, path: Path, max_bytes: int) -> bytes:
        with path.open("rb") as f:
            data = f.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise IngestError(f"File too large for text ingestion: {path}")
        return data

    def extract_text(self, path: Path, max_bytes: int = 10_000_000) -> str:
        filetype = self.detect_filetype(path)
        if filetype in ("text", "json", "spreadsheet"):
            data = self._read_text_bytes(path, max_bytes=max_bytes)
            for enc in ("utf-8", "utf-8-sig", "latin-1"):
                try:
                    return data.decode(enc)
                except Exception:
                    continue
            return data.decode("utf-8", errors="replace")

        if filetype == "pdf":
            return self._extract_pdf_text(path, max_bytes=max_bytes)

        if filetype == "docx":
            return self._extract_docx_text(path, max_bytes=max_bytes)

        if filetype == "image":
            return self._extract_image_stub(path)

        if filetype.startswith("archive:"):
            return self._extract_archive_listing(path, filetype)

        return ""

    def _extract_pdf_text(self, path: Path, max_bytes: int) -> str:
        try:
            import PyPDF2  # type: ignore
        except Exception:
            return ""
        try:
            with path.open("rb") as f:
                reader = PyPDF2.PdfReader(f)
                texts: List[str] = []
                total = 0
                for page in reader.pages:
                    t = page.extract_text() or ""
                    total += len(t.encode("utf-8", errors="ignore"))
                    if total > max_bytes:
                        break
                    texts.append(t)
                return "\n\n".join(texts)
        except Exception:
            return ""

    def _extract_docx_text(self, path: Path, max_bytes: int) -> str:
        try:
            import docx  # type: ignore
        except Exception:
            return ""
        try:
            doc = docx.Document(str(path))
            parts: List[str] = []
            total = 0
            for para in doc.paragraphs:
                t = para.text or ""
                total += len(t.encode("utf-8", errors="ignore"))
                if total > max_bytes:
                    break
                parts.append(t)
            return "\n".join(parts)
        except Exception:
            return ""

    def _extract_image_stub(self, path: Path) -> str:
        try:
            from PIL import Image  # type: ignore
        except Exception:
            return ""
        try:
            with Image.open(str(path)) as im:
                w, h = im.size
                mode = im.mode
            return f"[image] {path.name} {w}x{h} mode={mode}"
        except Exception:
            return ""

    def _extract_archive_listing(self, path: Path, filetype: str) -> str:
        try:
            if filetype == "archive:zip":
                with zipfile.ZipFile(str(path), "r") as zf:
                    names = zf.namelist()
                return "[archive:zip]\n" + "\n".join(names)
            if filetype == "archive:tar":
                with tarfile.open(str(path), "r") as tf:
                    names = [m.name for m in tf.getmembers()]
                return "[archive:tar]\n" + "\n".join(names)
            if filetype == "archive:tar.gz":
                with tarfile.open(str(path), "r:gz") as tf:
                    names = [m.name for m in tf.getmembers()]
                return "[archive:tar.gz]\n" + "\n".join(names)
            if filetype == "archive:gz":
                return "[archive:gz]"
        except Exception:
            return ""
        return ""


class Chunker:
    def __init__(self, max_lines: int = 80, overlap_lines: int = 10):
        self._max_lines = _clamp_int("max_lines", max_lines, 10, 500)
        self._overlap_lines = _clamp_int("overlap_lines", overlap_lines, 0, self._max_lines - 1)

    def chunk_text(self, text: str) -> List[Tuple[int, int, str]]:
        lines = text.splitlines()
        if not lines:
            return []
        chunks: List[Tuple[int, int, str]] = []
        start = 0
        idx = 0
        while start < len(lines):
            end = min(len(lines), start + self._max_lines)
            chunk_lines = lines[start:end]
            chunk_text = "\n".join(chunk_lines).strip("\n")
            if chunk_text.strip():
                chunks.append((start + 1, end, chunk_text))
                idx += 1
            if end >= len(lines):
                break
            start = max(0, end - self._overlap_lines)
        return chunks


class LexicalIndex:
    def __init__(self, storage: Storage):
        self._s = storage

    def _remove_document_chunks(self, document_id: int) -> None:
        cur = self._s.execute("SELECT id FROM chunks WHERE document_id = ?", (document_id,))
        chunk_ids = [int(r["id"]) for r in cur.fetchall()]
        if not chunk_ids:
            return
        self._s.executemany("DELETE FROM chunk_terms WHERE chunk_id = ?", [(cid,) for cid in chunk_ids])
        self._s.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))

    def index_document(self, document_id: int, text: str, chunker: Chunker) -> None:
        self._remove_document_chunks(document_id)

        chunks = chunker.chunk_text(text)
        created_at = _utc_now_iso()

        chunk_rows: List[Tuple[int, int, int, int, str, int, str]] = []
        term_rows: List[Tuple[int, str, int]] = []
        df_delta: Dict[str, int] = {}

        for i, (start_line, end_line, ctext) in enumerate(chunks):
            tokens = _tokenize(ctext)
            token_count = len(tokens)
            chunk_rows.append((document_id, i, start_line, end_line, ctext, token_count, created_at))

        cur = self._s.executemany(
            """
            INSERT INTO chunks (document_id, chunk_index, start_line, end_line, text, token_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            chunk_rows,
        )

        cur = self._s.execute("SELECT id, chunk_index FROM chunks WHERE document_id = ? ORDER BY chunk_index", (document_id,))
        chunk_id_by_index = {int(r["chunk_index"]): int(r["id"]) for r in cur.fetchall()}

        for i, (_, _, ctext) in enumerate([(a, b, c) for (a, b, c) in [(c[0], c[1], c[2]) for c in chunks]]):
            chunk_id = chunk_id_by_index.get(i)
            if chunk_id is None:
                continue
            tokens = _tokenize(ctext)
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            for term, count in tf.items():
                term_rows.append((chunk_id, term, count))
            for term in tf.keys():
                df_delta[term] = df_delta.get(term, 0) + 1

        if term_rows:
            self._s.executemany(
                "INSERT INTO chunk_terms (chunk_id, term, tf) VALUES (?, ?, ?)",
                term_rows,
            )

        for term, delta in df_delta.items():
            self._s.execute(
                """
                INSERT INTO term_stats (term, df) VALUES (?, ?)
                ON CONFLICT(term) DO UPDATE SET df = df + excluded.df
                """,
                (term, delta),
            )

    def _doc_count(self) -> int:
        cur = self._s.execute("SELECT COUNT(*) AS n FROM chunks")
        return int(cur.fetchone()["n"])

    def search_chunks(self, query: str, limit: int = 50) -> List[Tuple[int, float, str]]:
        limit = _clamp_int("limit", limit, 1, 500)
        q_terms = _tokenize(query)
        if not q_terms:
            return []

        placeholders = ",".join(["?"] * len(q_terms))
        cur = self._s.execute(
            f"""
            SELECT ct.chunk_id, ct.term, ct.tf, c.token_count, c.text, c.document_id
            FROM chunk_terms ct
            JOIN chunks c ON c.id = ct.chunk_id
            WHERE ct.term IN ({placeholders})
            """,
            q_terms,
        )
        rows = cur.fetchall()
        if not rows:
            return []

        n_docs = self._doc_count()
        df_map: Dict[str, int] = {}
        cur2 = self._s.execute(
            f"SELECT term, df FROM term_stats WHERE term IN ({placeholders})",
            q_terms,
        )
        for r in cur2.fetchall():
            df_map[str(r["term"])] = int(r["df"])

        k1 = 1.2
        b = 0.75

        token_counts: List[int] = []
        chunk_text: Dict[int, str] = {}
        chunk_doc: Dict[int, int] = {}
        for r in rows:
            cid = int(r["chunk_id"])
            token_counts.append(int(r["token_count"]))
            chunk_text[cid] = str(r["text"])
            chunk_doc[cid] = int(r["document_id"])
        avgdl = (sum(token_counts) / len(token_counts)) if token_counts else 1.0

        scores: Dict[int, float] = {}
        matched_terms: Dict[int, set[str]] = {}
        for r in rows:
            cid = int(r["chunk_id"])
            term = str(r["term"])
            tf = int(r["tf"])
            dl = int(r["token_count"])
            df = df_map.get(term, 0)
            if df <= 0:
                continue
            idf = _bm25_idf(n_docs=max(n_docs, 1), df=df)
            denom = tf + k1 * (1 - b + b * (dl / max(avgdl, 1e-9)))
            score = idf * (tf * (k1 + 1)) / max(denom, 1e-9)
            scores[cid] = scores.get(cid, 0.0) + score
            matched_terms.setdefault(cid, set()).add(term)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        out: List[Tuple[int, float, str]] = []
        for cid, sc in ranked:
            reason = "matched:" + ",".join(sorted(matched_terms.get(cid, set())))
            out.append((cid, float(sc), reason))
        return out


class MetadataManager:
    def __init__(self, storage: Storage):
        self._s = storage

    def set_metadata(self, document_id: int, key: str, value: str) -> None:
        key = key.strip()
        if not key:
            raise ValidationError("Metadata key cannot be empty")
        if len(key) > 128:
            raise ValidationError("Metadata key too long")
        if len(value) > 10_000:
            raise ValidationError("Metadata value too long")
        self._s.execute(
            """
            INSERT INTO document_metadata (document_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(document_id, key) DO UPDATE SET value = excluded.value
            """,
            (document_id, key, value),
        )

    def get_metadata(self, document_id: int) -> Dict[str, str]:
        cur = self._s.execute("SELECT key, value FROM document_metadata WHERE document_id = ?", (document_id,))
        return {str(r["key"]): str(r["value"]) for r in cur.fetchall()}

    def delete_metadata(self, document_id: int, key: str) -> None:
        self._s.execute("DELETE FROM document_metadata WHERE document_id = ? AND key = ?", (document_id, key))


class TagManager:
    def __init__(self, storage: Storage):
        self._s = storage

    def _get_or_create_tag_id(self, tag: str) -> int:
        tag = _normalize_tag(tag)
        cur = self._s.execute("SELECT id FROM tags WHERE name = ?", (tag,))
        row = cur.fetchone()
        if row:
            return int(row["id"])
        cur = self._s.execute("INSERT INTO tags (name) VALUES (?)", (tag,))
        return int(cur.lastrowid)

    def add_tag(self, document_id: int, tag: str) -> None:
        tag_id = self._get_or_create_tag_id(tag)
        self._s.execute(
            "INSERT OR IGNORE INTO document_tags (document_id, tag_id) VALUES (?, ?)",
            (document_id, tag_id),
        )

    def remove_tag(self, document_id: int, tag: str) -> None:
        tag = _normalize_tag(tag)
        cur = self._s.execute("SELECT id FROM tags WHERE name = ?", (tag,))
        row = cur.fetchone()
        if not row:
            return
        tag_id = int(row["id"])
        self._s.execute("DELETE FROM document_tags WHERE document_id = ? AND tag_id = ?", (document_id, tag_id))

    def list_tags(self, document_id: int) -> List[str]:
        cur = self._s.execute(
            """
            SELECT t.name
            FROM tags t
            JOIN document_tags dt ON dt.tag_id = t.id
            WHERE dt.document_id = ?
            ORDER BY t.name
            """,
            (document_id,),
        )
        return [str(r["name"]) for r in cur.fetchall()]


class CatalogManager:
    def __init__(self, storage: Storage):
        self._s = storage

    def create_catalog(self, name: str, description: Optional[str] = None) -> int:
        name = _normalize_catalog(name)
        created_at = _utc_now_iso()
        cur = self._s.execute(
            "INSERT INTO catalogs (name, description, created_at) VALUES (?, ?, ?)",
            (name, description, created_at),
        )
        return int(cur.lastrowid)

    def add_document(self, catalog_name: str, document_id: int) -> None:
        catalog_name = _normalize_catalog(catalog_name)
        cur = self._s.execute("SELECT id FROM catalogs WHERE name = ?", (catalog_name,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError(f"Catalog not found: {catalog_name}")
        catalog_id = int(row["id"])
        self._s.execute(
            "INSERT OR IGNORE INTO catalog_documents (catalog_id, document_id) VALUES (?, ?)",
            (catalog_id, document_id),
        )

    def remove_document(self, catalog_name: str, document_id: int) -> None:
        catalog_name = _normalize_catalog(catalog_name)
        cur = self._s.execute("SELECT id FROM catalogs WHERE name = ?", (catalog_name,))
        row = cur.fetchone()
        if not row:
            return
        catalog_id = int(row["id"])
        self._s.execute("DELETE FROM catalog_documents WHERE catalog_id = ? AND document_id = ?", (catalog_id, document_id))

    def list_documents(self, catalog_name: str) -> List[int]:
        catalog_name = _normalize_catalog(catalog_name)
        cur = self._s.execute("SELECT id FROM catalogs WHERE name = ?", (catalog_name,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError(f"Catalog not found: {catalog_name}")
        catalog_id = int(row["id"])
        cur2 = self._s.execute(
            "SELECT document_id FROM catalog_documents WHERE catalog_id = ? ORDER BY document_id",
            (catalog_id,),
        )
        return [int(r["document_id"]) for r in cur2.fetchall()]


class ViewManager:
    def __init__(self, storage: Storage):
        self._s = storage

    def create_view(self, name: str, query: Dict[str, Any]) -> int:
        name = _normalize_view(name)
        created_at = _utc_now_iso()
        query_json = json.dumps(query, ensure_ascii=False, sort_keys=True)
        cur = self._s.execute(
            "INSERT INTO views (name, query_json, created_at) VALUES (?, ?, ?)",
            (name, query_json, created_at),
        )
        return int(cur.lastrowid)

    def get_view(self, name: str) -> Dict[str, Any]:
        name = _normalize_view(name)
        cur = self._s.execute("SELECT query_json FROM views WHERE name = ?", (name,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError(f"View not found: {name}")
        return json.loads(str(row["query_json"]))

    def list_views(self) -> List[str]:
        cur = self._s.execute("SELECT name FROM views ORDER BY name")
        return [str(r["name"]) for r in cur.fetchall()]


class JournalManager:
    def __init__(self, storage: Storage):
        self._s = storage

    def create_journal(self, name: str) -> int:
        name = name.strip()
        if not name:
            raise ValidationError("Journal name cannot be empty")
        if len(name) > 128:
            raise ValidationError("Journal name too long")
        created_at = _utc_now_iso()
        cur = self._s.execute("INSERT INTO journals (name, created_at) VALUES (?, ?)", (name, created_at))
        return int(cur.lastrowid)

    def add_entry(self, journal_name: str, title: Optional[str], body: str) -> int:
        journal_name = journal_name.strip()
        if not journal_name:
            raise ValidationError("Journal name cannot be empty")
        if not body.strip():
            raise ValidationError("Journal entry body cannot be empty")
        cur = self._s.execute("SELECT id FROM journals WHERE name = ?", (journal_name,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError(f"Journal not found: {journal_name}")
        journal_id = int(row["id"])
        created_at = _utc_now_iso()
        cur2 = self._s.execute(
            "INSERT INTO journal_entries (journal_id, created_at, title, body) VALUES (?, ?, ?, ?)",
            (journal_id, created_at, title, body),
        )
        return int(cur2.lastrowid)

    def list_entries(self, journal_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        limit = _clamp_int("limit", limit, 1, 500)
        cur = self._s.execute("SELECT id FROM journals WHERE name = ?", (journal_name.strip(),))
        row = cur.fetchone()
        if not row:
            raise NotFoundError(f"Journal not found: {journal_name}")
        journal_id = int(row["id"])
        cur2 = self._s.execute(
            """
            SELECT id, created_at, title, body
            FROM journal_entries
            WHERE journal_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (journal_id, limit),
        )
        return [
            {"id": int(r["id"]), "created_at": str(r["created_at"]), "title": r["title"], "body": str(r["body"])}
            for r in cur2.fetchall()
        ]


class RelationMiner:
    def __init__(self, storage: Storage):
        self._s = storage

    def mine_relations(self, document_id: int, text: str, max_relations: int = 25) -> None:
        max_relations = _clamp_int("max_relations", max_relations, 0, 200)
        if max_relations == 0:
            return

        tokens = _tokenize(text)
        if not tokens:
            return
        freq: Dict[str, int] = {}
        for t in tokens:
            if len(t) < 4:
                continue
            freq[t] = freq.get(t, 0) + 1
        if not freq:
            return
        top_terms = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:50]
        term_set = {t for t, _ in top_terms}

        placeholders = ",".join(["?"] * len(term_set))
        cur = self._s.execute(
            f"""
            SELECT DISTINCT c.document_id
            FROM chunk_terms ct
            JOIN chunks c ON c.id = ct.chunk_id
            WHERE ct.term IN ({placeholders})
            """,
            list(term_set),
        )
        candidates = [int(r["document_id"]) for r in cur.fetchall() if int(r["document_id"]) != document_id]
        if not candidates:
            return

        weights: List[Tuple[int, float]] = []
        for other_id in candidates:
            cur2 = self._s.execute(
                f"""
                SELECT ct.term, SUM(ct.tf) AS tf_sum
                FROM chunk_terms ct
                JOIN chunks c ON c.id = ct.chunk_id
                WHERE c.document_id = ? AND ct.term IN ({placeholders})
                GROUP BY ct.term
                """,
                (other_id, *list(term_set)),
            )
            overlap = 0.0
            for r in cur2.fetchall():
                overlap += float(int(r["tf_sum"]))
            if overlap > 0:
                weights.append((other_id, overlap))

        weights.sort(key=lambda x: x[1], reverse=True)
        weights = weights[:max_relations]
        created_at = _utc_now_iso()
        for other_id, w in weights:
            self._s.execute(
                """
                INSERT INTO relations (from_document_id, to_document_id, relation_type, weight, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(from_document_id, to_document_id, relation_type)
                DO UPDATE SET weight = excluded.weight, created_at = excluded.created_at
                """,
                (document_id, other_id, "lexical_overlap", float(w), created_at),
            )


class Reader:
    def __init__(self, storage: Storage, root: Path, ingestor: FileIngestor):
        self._s = storage
        self._root = Path(root)
        self._ingestor = ingestor

    def read_chunk_window(self, chunk_id: int) -> EvidenceWindow:
        cur = self._s.execute(
            """
            SELECT c.id, c.document_id, c.start_line, c.end_line, c.text, d.relpath
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.id = ?
            """,
            (chunk_id,),
        )
        row = cur.fetchone()
        if not row:
            raise NotFoundError(f"Chunk not found: {chunk_id}")
        doc_id = int(row["document_id"])
        relpath = str(row["relpath"])
        start_line = int(row["start_line"])
        end_line = int(row["end_line"])
        text = str(row["text"])
        src = SourceRef(
            document_id=doc_id,
            relpath=relpath,
            window_type="lines",
            start=start_line,
            end=end_line,
            locator=f"lines:{start_line}-{end_line}",
        )
        return EvidenceWindow(source=src, text=text)

    def read_document_window_lines(self, document_id: int, start_line: int, end_line: int) -> EvidenceWindow:
        if start_line < 1 or end_line < start_line:
            raise ValidationError("Invalid line window")
        cur = self._s.execute("SELECT relpath, abspath FROM documents WHERE id = ?", (document_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError(f"Document not found: {document_id}")
        relpath = str(row["relpath"])
        abspath = Path(str(row["abspath"]))
        if not abspath.exists():
            raise ReadError(f"File missing: {abspath}")
        text = self._ingestor.extract_text(abspath)
        lines = text.splitlines()
        s = start_line - 1
        e = min(len(lines), end_line)
        window_text = "\n".join(lines[s:e])
        src = SourceRef(
            document_id=document_id,
            relpath=relpath,
            window_type="lines",
            start=start_line,
            end=end_line,
            locator=f"lines:{start_line}-{end_line}",
        )
        return EvidenceWindow(source=src, text=window_text)

    def read_archive_member(self, document_id: int, member_path: str, max_bytes: int = 2_000_000) -> EvidenceWindow:
        member_path = member_path.strip().lstrip("/")
        if not member_path:
            raise ValidationError("member_path cannot be empty")
        cur = self._s.execute("SELECT relpath, abspath, filetype FROM documents WHERE id = ?", (document_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError(f"Document not found: {document_id}")
        relpath = str(row["relpath"])
        abspath = Path(str(row["abspath"]))
        filetype = str(row["filetype"])
        if not abspath.exists():
            raise ReadError(f"File missing: {abspath}")

        data: bytes = b""
        try:
            if filetype == "archive:zip":
                with zipfile.ZipFile(str(abspath), "r") as zf:
                    with zf.open(member_path, "r") as f:
                        data = f.read(max_bytes + 1)
            elif filetype == "archive:tar":
                with tarfile.open(str(abspath), "r") as tf:
                    m = tf.getmember(member_path)
                    f = tf.extractfile(m)
                    if f is None:
                        raise ReadError("Member not readable")
                    data = f.read(max_bytes + 1)
            elif filetype == "archive:tar.gz":
                with tarfile.open(str(abspath), "r:gz") as tf:
                    m = tf.getmember(member_path)
                    f = tf.extractfile(m)
                    if f is None:
                        raise ReadError("Member not readable")
                    data = f.read(max_bytes + 1)
            else:
                raise ReadError("Not an archive document")
        except KeyError as e:
            raise NotFoundError(f"Archive member not found: {member_path}") from e
        except Exception as e:
            raise ReadError(f"Failed to read archive member: {member_path}") from e

        if len(data) > max_bytes:
            raise ReadError("Archive member too large")

        try:
            text = data.decode("utf-8")
        except Exception:
            text = data.decode("utf-8", errors="replace")

        src = SourceRef(
            document_id=document_id,
            relpath=relpath,
            window_type="archive_member",
            start=0,
            end=0,
            locator=f"member:{member_path}",
        )
        return EvidenceWindow(source=src, text=text)


class SearchQuery:
    def __init__(
        self,
        text: str,
        limit_candidates: int = 20,
        per_source_quota: int = 3,
        use_embeddings: bool = False,
        use_rerank: bool = False,
    ):
        self.text = text
        self.limit_candidates = _clamp_int("limit_candidates", limit_candidates, 1, 200)
        self.per_source_quota = _clamp_int("per_source_quota", per_source_quota, 1, 50)
        self.use_embeddings = bool(use_embeddings)
        self.use_rerank = bool(use_rerank)


class SearchEngine:
    def __init__(self, storage: Storage, lexical_index: LexicalIndex):
        self._s = storage
        self._lex = lexical_index

    def search(self, query: SearchQuery) -> List[Candidate]:
        ranked_chunks = self._lex.search_chunks(query.text, limit=max(query.limit_candidates * 5, 50))
        if not ranked_chunks:
            return []

        cur = self._s.execute("SELECT id, relpath FROM documents")
        rel_by_id = {int(r["id"]): str(r["relpath"]) for r in cur.fetchall()}

        per_doc_count: Dict[int, int] = {}
        candidates: List[Candidate] = []
        for chunk_id, score, reason in ranked_chunks:
            cur2 = self._s.execute("SELECT document_id FROM chunks WHERE id = ?", (chunk_id,))
            r2 = cur2.fetchone()
            if not r2:
                continue
            doc_id = int(r2["document_id"])
            if per_doc_count.get(doc_id, 0) >= query.per_source_quota:
                continue
            per_doc_count[doc_id] = per_doc_count.get(doc_id, 0) + 1
            rel = rel_by_id.get(doc_id, f"doc:{doc_id}")
            candidates.append(Candidate(document_id=doc_id, relpath=rel, score=float(score), reason=f"chunk:{chunk_id} {reason}"))
            if len(candidates) >= query.limit_candidates:
                break

        if query.use_embeddings or query.use_rerank:
            pass

        return candidates


class InvestigationNotes:
    def __init__(self, storage: Storage):
        self._s = storage

    def write(self, question: str, answer: str, citations: List[SourceRef], note: str) -> int:
        if not question.strip():
            raise ValidationError("Question cannot be empty")
        if not answer.strip():
            raise ValidationError("Answer cannot be empty")
        citations_json = json.dumps([dataclasses.asdict(c) for c in citations], ensure_ascii=False)
        created_at = _utc_now_iso()
        cur = self._s.execute(
            """
            INSERT INTO investigations (created_at, question, answer, citations_json, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (created_at, question, answer, citations_json, note),
        )
        return int(cur.lastrowid)

    def get(self, investigation_id: int) -> Dict[str, Any]:
        cur = self._s.execute(
            "SELECT id, created_at, question, answer, citations_json, note FROM investigations WHERE id = ?",
            (investigation_id,),
        )
        row = cur.fetchone()
        if not row:
            raise NotFoundError(f"Investigation not found: {investigation_id}")
        return {
            "id": int(row["id"]),
            "created_at": str(row["created_at"]),
            "question": str(row["question"]),
            "answer": str(row["answer"]),
            "citations": json.loads(str(row["citations_json"])),
            "note": str(row["note"]),
        }

    def search_notes(self, text: str, limit: int = 20) -> List[Dict[str, Any]]:
        limit = _clamp_int("limit", limit, 1, 200)
        q = f"%{text.strip()}%"
        cur = self._s.execute(
            """
            SELECT id, created_at, question, answer, note
            FROM investigations
            WHERE question LIKE ? OR answer LIKE ? OR note LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (q, q, q, limit),
        )
        return [
            {
                "id": int(r["id"]),
                "created_at": str(r["created_at"]),
                "question": str(r["question"]),
                "answer": str(r["answer"]),
                "note": str(r["note"]),
            }
            for r in cur.fetchall()
        ]


class Agent:
    def __init__(self, reader: Reader, storage: Storage, notes: InvestigationNotes):
        self._reader = reader
        self._s = storage
        self._notes = notes

    def _compose_answer(self, question: str, evidence: List[EvidenceWindow]) -> Tuple[str, List[SourceRef], str]:
        if not evidence:
            return ("I couldn't find relevant sources in the local knowledge base.", [], "No evidence windows were read.")
        citations: List[SourceRef] = [ev.source for ev in evidence]
        parts: List[str] = []
        for i, ev in enumerate(evidence, start=1):
            snippet = ev.text.strip()
            if len(snippet) > 800:
                snippet = snippet[:800].rstrip() + "…"
            parts.append(f"Source {i} ({ev.source.relpath} {ev.source.locator}):\n{snippet}")
        answer = "\n\n".join(parts)
        note = f"Question: {question}\n\nRead {len(evidence)} evidence windows and returned excerpts with citations."
        return (answer, citations, note)

    def answer_with_citations(self, question: str, chunk_ids: List[int]) -> Answer:
        if not question.strip():
            raise ValidationError("Question cannot be empty")
        if not chunk_ids:
            raise ValidationError("chunk_ids cannot be empty")
        evidence: List[EvidenceWindow] = []
        for cid in chunk_ids:
            evidence.append(self._reader.read_chunk_window(int(cid)))
        answer_text, citations, note = self._compose_answer(question, evidence)
        inv_id = self._notes.write(question=question, answer=answer_text, citations=citations, note=note)
        return Answer(
            question=question,
            answer=answer_text,
            citations=citations,
            created_at=_utc_now_iso(),
            investigation_note_id=inv_id,
        )


class Marginalia:
    def __init__(self, root_folder: Union[str, Path], db_path: Optional[Union[str, Path]] = None):
        self._root = Path(root_folder).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

        if db_path is None:
            db_path = self._root / ".marginalia" / "marginalia.sqlite3"
        self._db_path = Path(db_path).expanduser().resolve()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._storage = Storage(self._db_path)
        self._ingestor = FileIngestor(self._root)
        self._chunker = Chunker()
        self._lex = LexicalIndex(self._storage)
        self._metadata = MetadataManager(self._storage)
        self._tags = TagManager(self._storage)
        self._catalogs = CatalogManager(self._storage)
        self._views = ViewManager(self._storage)
        self._journals = JournalManager(self._storage)
        self._relations = RelationMiner(self._storage)
        self._reader = Reader(self._storage, self._root, self._ingestor)
        self._search = SearchEngine(self._storage, self._lex)
        self._notes = InvestigationNotes(self._storage)
        self._agent = Agent(self._reader, self._storage, self._notes)

    @property
    def root(self) -> Path:
        return self._root

    def close(self) -> None:
        self._storage.commit()
        self._storage.close()

    def ingest_path(self, path: Union[str, Path], title: Optional[str] = None, tags: Optional[List[str]] = None) -> int:
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = (self._root / p).resolve()
        if not p.exists():
            raise NotFoundError(f"Path not found: {p}")
        if p.is_dir():
            raise ValidationError("ingest_path expects a file, not a directory")

        relpath = _safe_relpath(p, self._root)
        filetype = self._ingestor.detect_filetype(p)
        stat = p.stat()
        size_bytes = int(stat.st_size)
        mtime = float(stat.st_mtime)
        sha256 = _sha256_file(p)
        now = _utc_now_iso()

        try:
            self._storage.execute("BEGIN")
            cur = self._storage.execute("SELECT id, sha256, mtime FROM documents WHERE relpath = ?", (relpath,))
            row = cur.fetchone()
            action = "created"
            if row:
                doc_id = int(row["id"])
                old_sha = str(row["sha256"])
                old_mtime = float(row["mtime"])
                if old_sha == sha256 and abs(old_mtime - mtime) < 1e-6:
                    action = "unchanged"
                self._storage.execute(
                    """
                    UPDATE documents
                    SET abspath = ?, filetype = ?, size_bytes = ?, mtime = ?, sha256 = ?, title = COALESCE(?, title), updated_at = ?
                    WHERE id = ?
                    """,
                    (str(p), filetype, size_bytes, mtime, sha256, title, now, doc_id),
                )
            else:
                cur2 = self._storage.execute(
                    """
                    INSERT INTO documents (relpath, abspath, filetype, size_bytes, mtime, sha256, title, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (relpath, str(p), filetype, size_bytes, mtime, sha256, title, now, now),
                )
                doc_id = int(cur2.lastrowid)

            if tags:
                for t in tags:
                    self._tags.add_tag(doc_id, t)

            text = self._ingestor.extract_text(p)
            self._lex.index_document(doc_id, text, self._chunker)
            self._relations.mine_relations(doc_id, text)

            self._storage.execute(
                "INSERT INTO ingest_history (created_at, relpath, action, details) VALUES (?, ?, ?, ?)",
                (now, relpath, action, json.dumps({"filetype": filetype, "size_bytes": size_bytes}, ensure_ascii=False)),
            )

            self._storage.commit()
            return doc_id
        except Exception:
            self._storage.rollback()
            raise

    def ingest_folder(self, folder: Union[str, Path], recursive: bool = True) -> List[int]:
        f = Path(folder).expanduser()
        if not f.is_absolute():
            f = (self._root / f).resolve()
        if not f.exists() or not f.is_dir():
            raise NotFoundError(f"Folder not found: {f}")

        ids: List[int] = []
        if recursive:
            it = f.rglob("*")
        else:
            it = f.glob("*")
        for p in it:
            if p.is_dir():
                continue
            try:
                ids.append(self.ingest_path(p))
            except Exception:
                continue
        return ids

    def set_metadata(self, document_id: int, key: str, value: str) -> None:
        self._metadata.set_metadata(document_id, key, value)
        self._storage.commit()

    def get_metadata(self, document_id: int) -> Dict[str, str]:
        return self._metadata.get_metadata(document_id)

    def add_tag(self, document_id: int, tag: str) -> None:
        self._tags.add_tag(document_id, tag)
        self._storage.commit()

    def remove_tag(self, document_id: int, tag: str) -> None:
        self._tags.remove_tag(document_id, tag)
        self._storage.commit()

    def list_tags(self, document_id: int) -> List[str]:
        return self._tags.list_tags(document_id)

    def create_catalog(self, name: str, description: Optional[str] = None) -> int:
        cid = self._catalogs.create_catalog(name, description)
        self._storage.commit()
        return cid

    def catalog_add_document(self, catalog_name: str, document_id: int) -> None:
        self._catalogs.add_document(catalog_name, document_id)
        self._storage.commit()

    def catalog_remove_document(self, catalog_name: str, document_id: int) -> None:
        self._catalogs.remove_document(catalog_name, document_id)
        self._storage.commit()

    def catalog_list_documents(self, catalog_name: str) -> List[int]:
        return self._catalogs.list_documents(catalog_name)

    def create_view(self, name: str, query: Dict[str, Any]) -> int:
        vid = self._views.create_view(name, query)
        self._storage.commit()
        return vid

    def get_view(self, name: str) -> Dict[str, Any]:
        return self._views.get_view(name)

    def list_views(self) -> List[str]:
        return self._views.list_views()

    def create_journal(self, name: str) -> int:
        jid = self._journals.create_journal(name)
        self._storage.commit()
        return jid

    def journal_add_entry(self, journal_name: str, title: Optional[str], body: str) -> int:
        eid = self._journals.add_entry(journal_name, title, body)
        self._storage.commit()
        return eid

    def journal_list_entries(self, journal_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self._journals.list_entries(journal_name, limit=limit)

    def search(self, text: str, limit_candidates: int = 20, per_source_quota: int = 3) -> List[Candidate]:
        q = SearchQuery(text=text, limit_candidates=limit_candidates, per_source_quota=per_source_quota)
        return self._search.search(q)

    def read_chunk(self, chunk_id: int) -> EvidenceWindow:
        return self._reader.read_chunk_window(chunk_id)

    def read_document_lines(self, document_id: int, start_line: int, end_line: int) -> EvidenceWindow:
        return self._reader.read_document_window_lines(document_id, start_line, end_line)

    def read_archive_member(self, document_id: int, member_path: str, max_bytes: int = 2_000_000) -> EvidenceWindow:
        return self._reader.read_archive_member(document_id, member_path, max_bytes=max_bytes)

    def answer(self, question: str, candidate_limit: int = 20, per_source_quota: int = 3, read_windows: int = 6) -> Answer:
        read_windows = _clamp_int("read_windows", read_windows, 1, 50)
        candidates = self.search(question, limit_candidates=candidate_limit, per_source_quota=per_source_quota)
        chunk_ids: List[int] = []
        for c in candidates:
            m = re.search(r"chunk:(\d+)", c.reason)
            if not m:
                continue
            chunk_ids.append(int(m.group(1)))
            if len(chunk_ids) >= read_windows:
                break
        if not chunk_ids:
            inv_id = self._notes.write(
                question=question,
                answer="I couldn't find relevant sources in the local knowledge base.",
                citations=[],
                note="No evidence windows were read because no candidates were found.",
            )
            return Answer(
                question=question,
                answer="I couldn't find relevant sources in the local knowledge base.",
                citations=[],
                created_at=_utc_now_iso(),
                investigation_note_id=inv_id,
            )
        ans = self._agent.answer_with_citations(question, chunk_ids)
        self._storage.commit()
        return ans

    def get_investigation(self, investigation_id: int) -> Dict[str, Any]:
        return self._notes.get(investigation_id)

    def search_investigations(self, text: str, limit: int = 20) -> List[Dict[str, Any]]:
        return self._notes.search_notes(text, limit=limit)

    def list_documents(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        limit = _clamp_int("limit", limit, 1, 1000)
        offset = _clamp_int("offset", offset, 0, 1_000_000)
        cur = self._storage.execute(
            """
            SELECT id, relpath, filetype, size_bytes, mtime, sha256, title, created_at, updated_at
            FROM documents
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        return [
            {
                "id": int(r["id"]),
                "relpath": str(r["relpath"]),
                "filetype": str(r["filetype"]),
                "size_bytes": int(r["size_bytes"]),
                "mtime": float(r["mtime"]),
                "sha256": str(r["sha256"]),
                "title": r["title"],
                "created_at": str(r["created_at"]),
                "updated_at": str(r["updated_at"]),
            }
            for r in cur.fetchall()
        ]

    def get_document(self, document_id: int) -> Dict[str, Any]:
        cur = self._storage.execute(
            """
            SELECT id, relpath, abspath, filetype, size_bytes, mtime, sha256, title, created_at, updated_at
            FROM documents
            WHERE id = ?
            """,
            (document_id,),
        )
        r = cur.fetchone()
        if not r:
            raise NotFoundError(f"Document not found: {document_id}")
        return {
            "id": int(r["id"]),
            "relpath": str(r["relpath"]),
            "abspath": str(r["abspath"]),
            "filetype": str(r["filetype"]),
            "size_bytes": int(r["size_bytes"]),
            "mtime": float(r["mtime"]),
            "sha256": str(r["sha256"]),
            "title": r["title"],
            "created_at": str(r["created_at"]),
            "updated_at": str(r["updated_at"]),
            "tags": self.list_tags(document_id),
            "metadata": self.get_metadata(document_id),
        }