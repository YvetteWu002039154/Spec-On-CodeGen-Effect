from __future__ import annotations

import os
import re
import io
import json
import math
import time
import uuid
import glob
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


def _safe_relpath(path: Path, root: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except Exception:
        raise ValueError("Path must be within root")
    return str(rel).replace("\\", "/")


def _normalize_text(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return s


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", text)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _guess_mime(path: Path) -> str:
    mt, _ = mimetypes.guess_type(str(path))
    return mt or "application/octet-stream"


class MarginaliaError(Exception):
    pass


class ValidationError(MarginaliaError):
    pass


class NotFoundError(MarginaliaError):
    pass


class QuotaError(MarginaliaError):
    pass


@dataclass(frozen=True)
class SourceRef:
    document_id: str
    locator: str
    snippet: str


@dataclass(frozen=True)
class CitedAnswer:
    answer: str
    sources: List[SourceRef]
    created_at: str


class Storage:
    def __init__(self, root: Union[str, Path]) -> None:
        self._root = Path(root).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def resolve(self, rel_path: str) -> Path:
        p = (self._root / rel_path).resolve()
        if self._root not in p.parents and p != self._root:
            raise ValidationError("Path escapes root")
        return p

    def list_files(self, patterns: Optional[Sequence[str]] = None) -> List[Path]:
        if not patterns:
            patterns = ["**/*"]
        out: List[Path] = []
        for pat in patterns:
            for p in self._root.glob(pat):
                if p.is_file():
                    out.append(p)
        out.sort()
        return out

    def read_bytes(self, rel_path: str) -> bytes:
        p = self.resolve(rel_path)
        if not p.exists() or not p.is_file():
            raise NotFoundError(f"File not found: {rel_path}")
        return p.read_bytes()

    def read_text(self, rel_path: str, encoding: str = "utf-8") -> str:
        data = self.read_bytes(rel_path)
        try:
            return data.decode(encoding)
        except Exception:
            return data.decode("utf-8", errors="replace")

    def write_bytes(self, rel_path: str, data: bytes) -> None:
        p = self.resolve(rel_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def write_text(self, rel_path: str, text: str, encoding: str = "utf-8") -> None:
        self.write_bytes(rel_path, text.encode(encoding))

    def ensure_dir(self, rel_dir: str) -> Path:
        p = self.resolve(rel_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


class Database:
    def __init__(self, db_path: Union[str, Path]) -> None:
        self._db_path = Path(db_path).expanduser().resolve()
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        c = self._conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                rel_path TEXT NOT NULL UNIQUE,
                title TEXT,
                mime TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                extra_json TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS document_tags (
                document_id TEXT NOT NULL,
                tag_id TEXT NOT NULL,
                PRIMARY KEY (document_id, tag_id),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS catalogs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                query_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS journals (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                title TEXT,
                body TEXT NOT NULL,
                extra_json TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS relations (
                id TEXT PRIMARY KEY,
                from_document_id TEXT NOT NULL,
                to_document_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL NOT NULL,
                evidence_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(from_document_id, to_document_id, relation_type),
                FOREIGN KEY (from_document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (to_document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                extra_json TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS note_links (
                note_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                PRIMARY KEY (note_id, document_id),
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS note_history (
                id TEXT PRIMARY KEY,
                note_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                extra_json TEXT NOT NULL,
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                locator TEXT NOT NULL,
                text TEXT NOT NULL,
                token_count INTEGER NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                UNIQUE(document_id, locator)
            )
            """
        )
        c.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
            USING fts5(text, document_id UNINDEXED, locator UNINDEXED, content='chunks', content_rowid='rowid')
            """
        )
        c.execute(
            """
            CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                INSERT INTO chunks_fts(rowid, text, document_id, locator) VALUES (new.rowid, new.text, new.document_id, new.locator);
            END;
            """
        )
        c.execute(
            """
            CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, text, document_id, locator) VALUES ('delete', old.rowid, old.text, old.document_id, old.locator);
            END;
            """
        )
        c.execute(
            """
            CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, text, document_id, locator) VALUES ('delete', old.rowid, old.text, old.document_id, old.locator);
                INSERT INTO chunks_fts(rowid, text, document_id, locator) VALUES (new.rowid, new.text, new.document_id, new.locator);
            END;
            """
        )
        self._conn.commit()


class DocumentKind:
    TEXT = "text"
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    IMAGE = "image"
    SPREADSHEET = "spreadsheet"
    LOG = "log"
    ARCHIVE = "archive"
    OTHER = "other"


@dataclass(frozen=True)
class Document:
    id: str
    rel_path: str
    title: Optional[str]
    mime: str
    size_bytes: int
    sha256: str
    modified_at: str
    ingested_at: str
    kind: str
    extra: Dict[str, Any]


class Ingestor:
    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def detect_kind(self, rel_path: str, mime: str) -> str:
        p = Path(rel_path)
        ext = p.suffix.lower()
        if ext in {".md", ".markdown"}:
            return DocumentKind.MARKDOWN
        if ext in {".txt"}:
            return DocumentKind.TEXT
        if ext in {".log"}:
            return DocumentKind.LOG
        if ext in {".pdf"}:
            return DocumentKind.PDF
        if ext in {".docx"}:
            return DocumentKind.DOCX
        if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}:
            return DocumentKind.IMAGE
        if ext in {".csv", ".tsv", ".xlsx", ".xls"}:
            return DocumentKind.SPREADSHEET
        if ext in {".zip"}:
            return DocumentKind.ARCHIVE
        if mime.startswith("text/"):
            return DocumentKind.TEXT
        return DocumentKind.OTHER

    def extract_text(self, rel_path: str, kind: str) -> Tuple[str, Dict[str, Any]]:
        p = self._storage.resolve(rel_path)
        extra: Dict[str, Any] = {}
        if kind in {DocumentKind.TEXT, DocumentKind.MARKDOWN, DocumentKind.LOG}:
            text = self._storage.read_text(rel_path)
            return _normalize_text(text), extra
        if kind == DocumentKind.SPREADSHEET:
            ext = p.suffix.lower()
            if ext in {".csv", ".tsv"}:
                text = self._storage.read_text(rel_path)
                delim = "\t" if ext == ".tsv" else ","
                lines = _normalize_text(text).split("\n")
                extra["delimiter"] = delim
                extra["row_count"] = max(0, len([ln for ln in lines if ln.strip() != ""]))
                return _normalize_text(text), extra
            extra["note"] = "Binary spreadsheet; text extraction not available"
            return "", extra
        if kind == DocumentKind.ARCHIVE:
            members: List[Dict[str, Any]] = []
            try:
                with zipfile.ZipFile(str(p), "r") as zf:
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        members.append(
                            {
                                "name": info.filename,
                                "size": info.file_size,
                                "compressed_size": info.compress_size,
                            }
                        )
                extra["members"] = members
            except Exception as e:
                extra["error"] = str(e)
            return "", extra
        if kind in {DocumentKind.PDF, DocumentKind.DOCX, DocumentKind.IMAGE, DocumentKind.OTHER}:
            extra["note"] = "Text extraction not available for this type"
            return "", extra
        return "", extra


class Chunker:
    def __init__(self, max_chars: int = 2000, overlap_chars: int = 200) -> None:
        if max_chars <= 0:
            raise ValidationError("max_chars must be > 0")
        if overlap_chars < 0:
            raise ValidationError("overlap_chars must be >= 0")
        if overlap_chars >= max_chars:
            raise ValidationError("overlap_chars must be < max_chars")
        self._max_chars = max_chars
        self._overlap = overlap_chars

    @property
    def max_chars(self) -> int:
        return self._max_chars

    @property
    def overlap_chars(self) -> int:
        return self._overlap

    def chunk_text(self, text: str) -> List[Tuple[str, str]]:
        text = _normalize_text(text)
        if not text.strip():
            return []
        chunks: List[Tuple[str, str]] = []
        n = len(text)
        start = 0
        idx = 0
        while start < n:
            end = min(n, start + self._max_chars)
            if end < n:
                cut = text.rfind("\n", start, end)
                if cut != -1 and cut > start + int(self._max_chars * 0.5):
                    end = cut + 1
            chunk = text[start:end]
            locator = f"chars:{start}-{end}"
            chunks.append((locator, chunk))
            idx += 1
            if end >= n:
                break
            start = max(0, end - self._overlap)
        return chunks


class Catalog:
    def __init__(self, id: str, name: str, query: Dict[str, Any], created_at: str) -> None:
        self.id = id
        self.name = name
        self.query = query
        self.created_at = created_at


class JournalEntry:
    def __init__(self, id: str, created_at: str, title: Optional[str], body: str, extra: Dict[str, Any]) -> None:
        self.id = id
        self.created_at = created_at
        self.title = title
        self.body = body
        self.extra = extra


class Note:
    def __init__(
        self,
        id: str,
        created_at: str,
        updated_at: str,
        title: str,
        body: str,
        sources: List[SourceRef],
        extra: Dict[str, Any],
    ) -> None:
        self.id = id
        self.created_at = created_at
        self.updated_at = updated_at
        self.title = title
        self.body = body
        self.sources = sources
        self.extra = extra


class MetadataStore:
    def __init__(self, db: Database) -> None:
        self._db = db

    def upsert_document(self, doc: Document) -> None:
        self._db.conn.execute(
            """
            INSERT INTO documents(id, rel_path, title, mime, size_bytes, sha256, modified_at, ingested_at, kind, extra_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(rel_path) DO UPDATE SET
                title=excluded.title,
                mime=excluded.mime,
                size_bytes=excluded.size_bytes,
                sha256=excluded.sha256,
                modified_at=excluded.modified_at,
                ingested_at=excluded.ingested_at,
                kind=excluded.kind,
                extra_json=excluded.extra_json
            """,
            (
                doc.id,
                doc.rel_path,
                doc.title,
                doc.mime,
                doc.size_bytes,
                doc.sha256,
                doc.modified_at,
                doc.ingested_at,
                doc.kind,
                json.dumps(doc.extra, ensure_ascii=False),
            ),
        )
        self._db.conn.commit()

    def get_document_by_path(self, rel_path: str) -> Optional[Document]:
        row = self._db.conn.execute("SELECT * FROM documents WHERE rel_path = ?", (rel_path,)).fetchone()
        if not row:
            return None
        return self._row_to_document(row)

    def get_document(self, document_id: str) -> Document:
        row = self._db.conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        if not row:
            raise NotFoundError("Document not found")
        return self._row_to_document(row)

    def list_documents(self) -> List[Document]:
        rows = self._db.conn.execute("SELECT * FROM documents ORDER BY rel_path").fetchall()
        return [self._row_to_document(r) for r in rows]

    def delete_document(self, document_id: str) -> None:
        self._db.conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        self._db.conn.commit()

    def _row_to_document(self, row: sqlite3.Row) -> Document:
        return Document(
            id=row["id"],
            rel_path=row["rel_path"],
            title=row["title"],
            mime=row["mime"],
            size_bytes=int(row["size_bytes"]),
            sha256=row["sha256"],
            modified_at=row["modified_at"],
            ingested_at=row["ingested_at"],
            kind=row["kind"],
            extra=json.loads(row["extra_json"] or "{}"),
        )

    def ensure_tag(self, name: str) -> str:
        name = name.strip()
        if not name:
            raise ValidationError("Tag name cannot be empty")
        row = self._db.conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
        if row:
            return str(row["id"])
        tag_id = str(uuid.uuid4())
        self._db.conn.execute("INSERT INTO tags(id, name) VALUES (?, ?)", (tag_id, name))
        self._db.conn.commit()
        return tag_id

    def set_document_tags(self, document_id: str, tag_names: Sequence[str]) -> None:
        self.get_document(document_id)
        tag_ids = [self.ensure_tag(n) for n in sorted(set([t.strip() for t in tag_names if t.strip()]))]
        self._db.conn.execute("DELETE FROM document_tags WHERE document_id = ?", (document_id,))
        self._db.conn.executemany(
            "INSERT INTO document_tags(document_id, tag_id) VALUES (?, ?)",
            [(document_id, tid) for tid in tag_ids],
        )
        self._db.conn.commit()

    def get_document_tags(self, document_id: str) -> List[str]:
        rows = self._db.conn.execute(
            """
            SELECT t.name FROM tags t
            JOIN document_tags dt ON dt.tag_id = t.id
            WHERE dt.document_id = ?
            ORDER BY t.name
            """,
            (document_id,),
        ).fetchall()
        return [str(r["name"]) for r in rows]

    def create_catalog(self, name: str, query: Dict[str, Any]) -> Catalog:
        name = name.strip()
        if not name:
            raise ValidationError("Catalog name cannot be empty")
        cat_id = str(uuid.uuid4())
        created_at = _iso(_utc_now())
        self._db.conn.execute(
            "INSERT INTO catalogs(id, name, query_json, created_at) VALUES (?, ?, ?, ?)",
            (cat_id, name, json.dumps(query, ensure_ascii=False), created_at),
        )
        self._db.conn.commit()
        return Catalog(cat_id, name, query, created_at)

    def list_catalogs(self) -> List[Catalog]:
        rows = self._db.conn.execute("SELECT * FROM catalogs ORDER BY name").fetchall()
        out: List[Catalog] = []
        for r in rows:
            out.append(Catalog(str(r["id"]), str(r["name"]), json.loads(r["query_json"] or "{}"), str(r["created_at"])))
        return out

    def get_catalog(self, catalog_id: str) -> Catalog:
        r = self._db.conn.execute("SELECT * FROM catalogs WHERE id = ?", (catalog_id,)).fetchone()
        if not r:
            raise NotFoundError("Catalog not found")
        return Catalog(str(r["id"]), str(r["name"]), json.loads(r["query_json"] or "{}"), str(r["created_at"]))

    def add_journal_entry(self, body: str, title: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> JournalEntry:
        body = body or ""
        if not body.strip():
            raise ValidationError("Journal body cannot be empty")
        jid = str(uuid.uuid4())
        created_at = _iso(_utc_now())
        ex = extra or {}
        self._db.conn.execute(
            "INSERT INTO journals(id, created_at, title, body, extra_json) VALUES (?, ?, ?, ?, ?)",
            (jid, created_at, title, body, json.dumps(ex, ensure_ascii=False)),
        )
        self._db.conn.commit()
        return JournalEntry(jid, created_at, title, body, ex)

    def list_journal_entries(self, limit: int = 50) -> List[JournalEntry]:
        if limit <= 0:
            raise ValidationError("limit must be > 0")
        rows = self._db.conn.execute("SELECT * FROM journals ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        out: List[JournalEntry] = []
        for r in rows:
            out.append(
                JournalEntry(
                    str(r["id"]),
                    str(r["created_at"]),
                    r["title"],
                    str(r["body"]),
                    json.loads(r["extra_json"] or "{}"),
                )
            )
        return out

    def upsert_relation(
        self,
        from_document_id: str,
        to_document_id: str,
        relation_type: str,
        strength: float,
        evidence: Dict[str, Any],
    ) -> None:
        if from_document_id == to_document_id:
            raise ValidationError("Cannot relate a document to itself")
        self.get_document(from_document_id)
        self.get_document(to_document_id)
        relation_type = relation_type.strip()
        if not relation_type:
            raise ValidationError("relation_type cannot be empty")
        if not (0.0 <= strength <= 1.0):
            raise ValidationError("strength must be between 0 and 1")
        rid = str(uuid.uuid4())
        created_at = _iso(_utc_now())
        self._db.conn.execute(
            """
            INSERT INTO relations(id, from_document_id, to_document_id, relation_type, strength, evidence_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(from_document_id, to_document_id, relation_type) DO UPDATE SET
                strength=excluded.strength,
                evidence_json=excluded.evidence_json,
                created_at=excluded.created_at
            """,
            (rid, from_document_id, to_document_id, relation_type, float(strength), json.dumps(evidence, ensure_ascii=False), created_at),
        )
        self._db.conn.commit()

    def list_relations(self, document_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        if limit <= 0:
            raise ValidationError("limit must be > 0")
        self.get_document(document_id)
        rows = self._db.conn.execute(
            """
            SELECT * FROM relations
            WHERE from_document_id = ? OR to_document_id = ?
            ORDER BY strength DESC, created_at DESC
            LIMIT ?
            """,
            (document_id, document_id, limit),
        ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": str(r["id"]),
                    "from_document_id": str(r["from_document_id"]),
                    "to_document_id": str(r["to_document_id"]),
                    "relation_type": str(r["relation_type"]),
                    "strength": float(r["strength"]),
                    "evidence": json.loads(r["evidence_json"] or "{}"),
                    "created_at": str(r["created_at"]),
                }
            )
        return out

    def create_note(
        self,
        title: str,
        body: str,
        sources: Optional[List[SourceRef]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Note:
        title = (title or "").strip()
        body = body or ""
        if not title:
            raise ValidationError("Note title cannot be empty")
        if not body.strip():
            raise ValidationError("Note body cannot be empty")
        nid = str(uuid.uuid4())
        now = _iso(_utc_now())
        srcs = sources or []
        ex = extra or {}
        self._db.conn.execute(
            "INSERT INTO notes(id, created_at, updated_at, title, body, sources_json, extra_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nid, now, now, title, body, json.dumps([s.__dict__ for s in srcs], ensure_ascii=False), json.dumps(ex, ensure_ascii=False)),
        )
        doc_ids = sorted(set([s.document_id for s in srcs if s.document_id]))
        self._db.conn.executemany(
            "INSERT OR IGNORE INTO note_links(note_id, document_id) VALUES (?, ?)",
            [(nid, did) for did in doc_ids],
        )
        self._db.conn.commit()
        return Note(nid, now, now, title, body, srcs, ex)

    def update_note(
        self,
        note_id: str,
        title: Optional[str] = None,
        body: Optional[str] = None,
        sources: Optional[List[SourceRef]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Note:
        row = self._db.conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not row:
            raise NotFoundError("Note not found")
        prev_title = str(row["title"])
        prev_body = str(row["body"])
        prev_sources = json.loads(row["sources_json"] or "[]")
        prev_extra = json.loads(row["extra_json"] or "{}")

        hist_id = str(uuid.uuid4())
        self._db.conn.execute(
            "INSERT INTO note_history(id, note_id, created_at, title, body, sources_json, extra_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (hist_id, note_id, _iso(_utc_now()), prev_title, prev_body, json.dumps(prev_sources, ensure_ascii=False), json.dumps(prev_extra, ensure_ascii=False)),
        )

        new_title = prev_title if title is None else (title or "").strip()
        new_body = prev_body if body is None else (body or "")
        if not new_title:
            raise ValidationError("Note title cannot be empty")
        if not new_body.strip():
            raise ValidationError("Note body cannot be empty")
        new_sources_list = prev_sources if sources is None else [s.__dict__ for s in (sources or [])]
        new_extra = prev_extra if extra is None else (extra or {})

        now = _iso(_utc_now())
        self._db.conn.execute(
            "UPDATE notes SET updated_at = ?, title = ?, body = ?, sources_json = ?, extra_json = ? WHERE id = ?",
            (now, new_title, new_body, json.dumps(new_sources_list, ensure_ascii=False), json.dumps(new_extra, ensure_ascii=False), note_id),
        )
        self._db.conn.execute("DELETE FROM note_links WHERE note_id = ?", (note_id,))
        doc_ids = sorted(set([d.get("document_id", "") for d in new_sources_list if d.get("document_id")]))
        self._db.conn.executemany(
            "INSERT OR IGNORE INTO note_links(note_id, document_id) VALUES (?, ?)",
            [(note_id, did) for did in doc_ids],
        )
        self._db.conn.commit()
        return self.get_note(note_id)

    def get_note(self, note_id: str) -> Note:
        r = self._db.conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not r:
            raise NotFoundError("Note not found")
        sources = []
        for s in json.loads(r["sources_json"] or "[]"):
            sources.append(SourceRef(document_id=str(s["document_id"]), locator=str(s["locator"]), snippet=str(s["snippet"])))
        return Note(
            id=str(r["id"]),
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"]),
            title=str(r["title"]),
            body=str(r["body"]),
            sources=sources,
            extra=json.loads(r["extra_json"] or "{}"),
        )

    def list_notes(self, limit: int = 50) -> List[Note]:
        if limit <= 0:
            raise ValidationError("limit must be > 0")
        rows = self._db.conn.execute("SELECT id FROM notes ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
        return [self.get_note(str(r["id"])) for r in rows]

    def list_note_history(self, note_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        if limit <= 0:
            raise ValidationError("limit must be > 0")
        self.get_note(note_id)
        rows = self._db.conn.execute(
            "SELECT * FROM note_history WHERE note_id = ? ORDER BY created_at DESC LIMIT ?",
            (note_id, limit),
        ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": str(r["id"]),
                    "note_id": str(r["note_id"]),
                    "created_at": str(r["created_at"]),
                    "title": str(r["title"]),
                    "body": str(r["body"]),
                    "sources": json.loads(r["sources_json"] or "[]"),
                    "extra": json.loads(r["extra_json"] or "{}"),
                }
            )
        return out

    def upsert_chunks(self, document_id: str, chunks: Sequence[Tuple[str, str]]) -> None:
        self.get_document(document_id)
        self._db.conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        rows = []
        for locator, text in chunks:
            t = _normalize_text(text)
            rows.append((str(uuid.uuid4()), document_id, locator, t, len(_tokenize(t))))
        self._db.conn.executemany(
            "INSERT INTO chunks(id, document_id, locator, text, token_count) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        self._db.conn.commit()

    def get_chunk(self, document_id: str, locator: str) -> Optional[Dict[str, Any]]:
        r = self._db.conn.execute(
            "SELECT * FROM chunks WHERE document_id = ? AND locator = ?",
            (document_id, locator),
        ).fetchone()
        if not r:
            return None
        return {
            "id": str(r["id"]),
            "document_id": str(r["document_id"]),
            "locator": str(r["locator"]),
            "text": str(r["text"]),
            "token_count": int(r["token_count"]),
        }

    def list_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        self.get_document(document_id)
        rows = self._db.conn.execute(
            "SELECT * FROM chunks WHERE document_id = ? ORDER BY locator",
            (document_id,),
        ).fetchall()
        return [
            {"id": str(r["id"]), "document_id": str(r["document_id"]), "locator": str(r["locator"]), "text": str(r["text"]), "token_count": int(r["token_count"])}
            for r in rows
        ]


class LexicalSearch:
    def __init__(self, db: Database) -> None:
        self._db = db

    def search_chunks(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            raise ValidationError("Query cannot be empty")
        if limit <= 0:
            raise ValidationError("limit must be > 0")
        fts_query = self._to_fts_query(query)
        rows = self._db.conn.execute(
            """
            SELECT c.document_id, c.locator, c.text, bm25(chunks_fts) AS score
            FROM chunks_fts
            JOIN chunks c ON c.rowid = chunks_fts.rowid
            WHERE chunks_fts MATCH ?
            ORDER BY score ASC
            LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "document_id": str(r["document_id"]),
                    "locator": str(r["locator"]),
                    "text": str(r["text"]),
                    "score": float(r["score"]),
                }
            )
        return out

    def _to_fts_query(self, query: str) -> str:
        toks = _tokenize(query)
        if not toks:
            return query
        return " ".join([f'"{t}"' for t in toks])


class SourceQuota:
    def __init__(self, max_sources: int = 8, max_per_document: int = 3) -> None:
        if max_sources <= 0:
            raise ValidationError("max_sources must be > 0")
        if max_per_document <= 0:
            raise ValidationError("max_per_document must be > 0")
        self.max_sources = max_sources
        self.max_per_document = max_per_document

    def apply(self, candidates: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        per_doc: Dict[str, int] = {}
        for c in candidates:
            did = str(c["document_id"])
            if len(out) >= self.max_sources:
                break
            if per_doc.get(did, 0) >= self.max_per_document:
                continue
            out.append(c)
            per_doc[did] = per_doc.get(did, 0) + 1
        return out


class Reader:
    def __init__(self, store: MetadataStore) -> None:
        self._store = store

    def read_window(self, document_id: str, locator: str) -> SourceRef:
        doc = self._store.get_document(document_id)
        chunk = self._store.get_chunk(document_id, locator)
        if not chunk:
            raise NotFoundError("Requested window not found")
        snippet = chunk["text"]
        return SourceRef(document_id=doc.id, locator=locator, snippet=snippet)

    def read_many(self, windows: Sequence[Tuple[str, str]]) -> List[SourceRef]:
        out: List[SourceRef] = []
        for did, loc in windows:
            out.append(self.read_window(did, loc))
        return out


class RelationMiner:
    def __init__(self, store: MetadataStore) -> None:
        self._store = store

    def mine(self, document_id: str, top_k: int = 5) -> None:
        if top_k <= 0:
            raise ValidationError("top_k must be > 0")
        doc = self._store.get_document(document_id)
        chunks = self._store.list_chunks(document_id)
        if not chunks:
            return
        doc_tokens: Dict[str, int] = {}
        for ch in chunks:
            for t in _tokenize(ch["text"]):
                doc_tokens[t] = doc_tokens.get(t, 0) + 1

        docs = self._store.list_documents()
        scored: List[Tuple[float, str, Dict[str, Any]]] = []
        for other in docs:
            if other.id == doc.id:
                continue
            other_chunks = self._store.list_chunks(other.id)
            if not other_chunks:
                continue
            other_tokens: Dict[str, int] = {}
            for ch in other_chunks:
                for t in _tokenize(ch["text"]):
                    other_tokens[t] = other_tokens.get(t, 0) + 1
            inter = set(doc_tokens.keys()) & set(other_tokens.keys())
            if not inter:
                continue
            num = sum(min(doc_tokens[t], other_tokens[t]) for t in inter)
            den = sum(doc_tokens.values()) + sum(other_tokens.values())
            strength = (2.0 * num / den) if den > 0 else 0.0
            if strength <= 0:
                continue
            evidence = {"shared_terms": sorted(list(inter))[:25], "from_path": doc.rel_path, "to_path": other.rel_path}
            scored.append((strength, other.id, evidence))

        scored.sort(key=lambda x: x[0], reverse=True)
        for strength, other_id, evidence in scored[:top_k]:
            self._store.upsert_relation(doc.id, other_id, "lexical_overlap", float(min(1.0, strength)), evidence)


class Agent:
    def __init__(
        self,
        store: MetadataStore,
        search: LexicalSearch,
        reader: Reader,
        quota: Optional[SourceQuota] = None,
    ) -> None:
        self._store = store
        self._search = search
        self._reader = reader
        self._quota = quota or SourceQuota()

    def answer(self, question: str, candidate_limit: int = 30) -> CitedAnswer:
        question = (question or "").strip()
        if not question:
            raise ValidationError("Question cannot be empty")
        candidates = self._search.search_chunks(question, limit=candidate_limit)
        candidates = self._quota.apply(candidates)
        if not candidates:
            created_at = _iso(_utc_now())
            return CitedAnswer(
                answer="I couldn't find relevant material in your local knowledge base for that question.",
                sources=[],
                created_at=created_at,
            )
        windows = [(c["document_id"], c["locator"]) for c in candidates]
        sources = self._reader.read_many(windows)
        answer = self._synthesize(question, sources)
        created_at = _iso(_utc_now())
        return CitedAnswer(answer=answer, sources=sources, created_at=created_at)

    def _synthesize(self, question: str, sources: Sequence[SourceRef]) -> str:
        q_toks = set(_tokenize(question))
        scored: List[Tuple[float, SourceRef]] = []
        for s in sources:
            toks = _tokenize(s.snippet)
            if not toks:
                continue
            overlap = sum(1 for t in toks if t in q_toks)
            score = overlap / max(1, len(toks))
            scored.append((score, s))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [s for _, s in scored[: min(5, len(scored))]] if scored else list(sources)[: min(5, len(sources))]

        lines: List[str] = []
        lines.append(f"Question: {question}")
        lines.append("")
        lines.append("Findings (with citations):")
        for i, s in enumerate(top, start=1):
            snippet = s.snippet.strip()
            if len(snippet) > 400:
                snippet = snippet[:400].rstrip() + "…"
            lines.append(f"{i}. {snippet} [{s.document_id} @ {s.locator}]")
        lines.append("")
        lines.append("Answer:")
        if top:
            combined = " ".join([s.snippet.strip() for s in top]).strip()
            combined = re.sub(r"\s+", " ", combined)
            if len(combined) > 900:
                combined = combined[:900].rstrip() + "…"
            lines.append(combined)
        else:
            lines.append("Insufficient evidence in retrieved windows.")
        return "\n".join(lines)


class Marginalia:
    def __init__(self, root: Union[str, Path], db_path: Optional[Union[str, Path]] = None) -> None:
        self._storage = Storage(root)
        if db_path is None:
            db_path = self._storage.root / ".marginalia" / "marginalia.sqlite3"
        db_path = Path(db_path).expanduser().resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = Database(db_path)
        self._store = MetadataStore(self._db)
        self._ingestor = Ingestor(self._storage)
        self._chunker = Chunker()
        self._search = LexicalSearch(self._db)
        self._reader = Reader(self._store)
        self._miner = RelationMiner(self._store)
        self._agent = Agent(self._store, self._search, self._reader)

    @property
    def storage(self) -> Storage:
        return self._storage

    @property
    def store(self) -> MetadataStore:
        return self._store

    @property
    def agent(self) -> Agent:
        return self._agent

    def close(self) -> None:
        self._db.close()

    def ingest_file(self, rel_path: str, title: Optional[str] = None, tags: Optional[Sequence[str]] = None) -> Document:
        rel_path = rel_path.replace("\\", "/").lstrip("/")
        p = self._storage.resolve(rel_path)
        if not p.exists() or not p.is_file():
            raise NotFoundError(f"File not found: {rel_path}")

        stat = p.stat()
        mime = _guess_mime(p)
        kind = self._ingestor.detect_kind(rel_path, mime)
        sha = _sha256_file(p)
        modified_at = _iso(datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc))
        ingested_at = _iso(_utc_now())

        existing = self._store.get_document_by_path(rel_path)
        doc_id = existing.id if existing else str(uuid.uuid4())

        extracted_text, extra = self._ingestor.extract_text(rel_path, kind)
        extra = dict(extra)
        extra["extracted_text_available"] = bool(extracted_text.strip())
        extra["ingest"] = {"mime_guess": mime}

        doc = Document(
            id=doc_id,
            rel_path=rel_path,
            title=title,
            mime=mime,
            size_bytes=int(stat.st_size),
            sha256=sha,
            modified_at=modified_at,
            ingested_at=ingested_at,
            kind=kind,
            extra=extra,
        )
        self._store.upsert_document(doc)

        if tags is not None:
            self._store.set_document_tags(doc.id, tags)

        chunks = self._chunker.chunk_text(extracted_text)
        self._store.upsert_chunks(doc.id, chunks)

        return self._store.get_document(doc.id)

    def ingest_tree(self, patterns: Optional[Sequence[str]] = None, tags: Optional[Sequence[str]] = None) -> List[Document]:
        docs: List[Document] = []
        for p in self._storage.list_files(patterns=patterns):
            rel = _safe_relpath(p, self._storage.root)
            docs.append(self.ingest_file(rel, tags=tags))
        return docs

    def build_relations(self, document_id: str, top_k: int = 5) -> None:
        self._miner.mine(document_id, top_k=top_k)

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        return self._search.search_chunks(query, limit=limit)

    def read(self, document_id: str, locator: str) -> SourceRef:
        return self._reader.read_window(document_id, locator)

    def answer(self, question: str, candidate_limit: int = 30, note_title: Optional[str] = None) -> CitedAnswer:
        cited = self._agent.answer(question, candidate_limit=candidate_limit)
        if cited.sources:
            title = (note_title or f"Investigation: {question}").strip()
            body = cited.answer
            self._store.create_note(title=title, body=body, sources=cited.sources, extra={"kind": "investigation_note"})
        return cited

    def add_journal(self, body: str, title: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> JournalEntry:
        return self._store.add_journal_entry(body=body, title=title, extra=extra)

    def create_view_catalog(self, name: str, query: Dict[str, Any]) -> Catalog:
        return self._store.create_catalog(name=name, query=query)

    def apply_catalog(self, catalog_id: str) -> List[Document]:
        cat = self._store.get_catalog(catalog_id)
        q = cat.query or {}
        tag = (q.get("tag") or "").strip()
        kind = (q.get("kind") or "").strip()
        path_prefix = (q.get("path_prefix") or "").strip().lstrip("/").replace("\\", "/")
        docs = self._store.list_documents()
        out: List[Document] = []
        for d in docs:
            if kind and d.kind != kind:
                continue
            if path_prefix and not d.rel_path.startswith(path_prefix):
                continue
            if tag:
                tags = self._store.get_document_tags(d.id)
                if tag not in tags:
                    continue
            out.append(d)
        return out


__all__ = [
    "Marginalia",
    "MarginaliaError",
    "ValidationError",
    "NotFoundError",
    "QuotaError",
    "Document",
    "DocumentKind",
    "Catalog",
    "JournalEntry",
    "Note",
    "SourceRef",
    "CitedAnswer",
    "SourceQuota",
]