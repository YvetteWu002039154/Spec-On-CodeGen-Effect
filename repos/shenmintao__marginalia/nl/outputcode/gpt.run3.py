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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


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


def _safe_relpath(path: Path, root: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except Exception:
        raise ValueError("Path is not within root")
    return rel.as_posix()


def _normalize_text(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return s


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    return re.findall(r"[a-z0-9]+", text)


def _guess_mime(path: Path) -> str:
    mt, _ = mimetypes.guess_type(str(path))
    return mt or "application/octet-stream"


def _clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


@dataclass(frozen=True)
class FileWindow:
    document_id: int
    source_path: str
    kind: str
    locator: str
    content: str


@dataclass(frozen=True)
class SearchCandidate:
    document_id: int
    score: float
    source_path: str
    title: str
    snippet: str


@dataclass(frozen=True)
class Citation:
    document_id: int
    source_path: str
    kind: str
    locator: str


@dataclass(frozen=True)
class Answer:
    text: str
    citations: List[Citation]
    created_at: str


class Storage:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        _ensure_dir(db_path.parent)
        self._conn = sqlite3.connect(str(db_path))
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                content_text TEXT NOT NULL
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
            """
        )

        c.execute(
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

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS catalogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                query_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS journals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_document_id INTEGER NOT NULL,
                to_document_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                score REAL NOT NULL,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                citations_json TEXT NOT NULL
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS investigations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                query TEXT NOT NULL,
                answer_text TEXT NOT NULL,
                citations_json TEXT NOT NULL,
                notes_id INTEGER,
                FOREIGN KEY (notes_id) REFERENCES notes(id) ON DELETE SET NULL
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                spec_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        c.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts
            USING fts5(
                title,
                content_text,
                source_path,
                content='documents',
                content_rowid='id'
            )
            """
        )

        c.execute(
            """
            CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
                INSERT INTO documents_fts(rowid, title, content_text, source_path)
                VALUES (new.id, new.title, new.content_text, new.source_path);
            END
            """
        )
        c.execute(
            """
            CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, title, content_text, source_path)
                VALUES('delete', old.id, old.title, old.content_text, old.source_path);
            END
            """
        )
        c.execute(
            """
            CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, title, content_text, source_path)
                VALUES('delete', old.id, old.title, old.content_text, old.source_path);
                INSERT INTO documents_fts(rowid, title, content_text, source_path)
                VALUES (new.id, new.title, new.content_text, new.source_path);
            END
            """
        )

        self._conn.commit()


class FileExtractor:
    def extract(self, path: Path) -> Tuple[str, str]:
        raise NotImplementedError


class TextExtractor(FileExtractor):
    def extract(self, path: Path) -> Tuple[str, str]:
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1", errors="replace")
        title = path.stem
        return title, _normalize_text(text)


class MarkdownExtractor(FileExtractor):
    def extract(self, path: Path) -> Tuple[str, str]:
        title, text = TextExtractor().extract(path)
        return title, text


class LogExtractor(FileExtractor):
    def extract(self, path: Path) -> Tuple[str, str]:
        title, text = TextExtractor().extract(path)
        return title, text


class PdfExtractor(FileExtractor):
    def extract(self, path: Path) -> Tuple[str, str]:
        try:
            import PyPDF2  # type: ignore
        except Exception:
            raise RuntimeError("PDF extraction requires PyPDF2")
        reader = PyPDF2.PdfReader(str(path))
        parts: List[str] = []
        for i, page in enumerate(reader.pages):
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            parts.append(f"[page {i+1}]\n{t}")
        title = path.stem
        return title, _normalize_text("\n\n".join(parts))


class DocxExtractor(FileExtractor):
    def extract(self, path: Path) -> Tuple[str, str]:
        try:
            import docx  # type: ignore
        except Exception:
            raise RuntimeError("DOCX extraction requires python-docx")
        d = docx.Document(str(path))
        parts = [p.text for p in d.paragraphs if p.text is not None]
        title = path.stem
        return title, _normalize_text("\n".join(parts))


class ImageExtractor(FileExtractor):
    def extract(self, path: Path) -> Tuple[str, str]:
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore
        except Exception:
            raise RuntimeError("Image OCR requires pillow and pytesseract")
        img = Image.open(str(path))
        text = pytesseract.image_to_string(img)
        title = path.stem
        return title, _normalize_text(text)


class SpreadsheetExtractor(FileExtractor):
    def extract(self, path: Path) -> Tuple[str, str]:
        suffix = path.suffix.lower()
        title = path.stem
        if suffix in (".csv", ".tsv"):
            data = path.read_bytes()
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = data.decode("latin-1", errors="replace")
            return title, _normalize_text(text)
        if suffix in (".xlsx", ".xlsm", ".xltx", ".xltm"):
            try:
                import openpyxl  # type: ignore
            except Exception:
                raise RuntimeError("XLSX extraction requires openpyxl")
            wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
            parts: List[str] = []
            for ws in wb.worksheets:
                parts.append(f"[sheet {ws.title}]")
                max_row = min(ws.max_row or 0, 2000)
                max_col = min(ws.max_column or 0, 50)
                for r in range(1, max_row + 1):
                    row_vals: List[str] = []
                    for c in range(1, max_col + 1):
                        v = ws.cell(row=r, column=c).value
                        if v is None:
                            row_vals.append("")
                        else:
                            row_vals.append(str(v))
                    parts.append("\t".join(row_vals).rstrip())
            return title, _normalize_text("\n".join(parts))
        raise RuntimeError("Unsupported spreadsheet format")


class ArchiveExtractor(FileExtractor):
    def extract(self, path: Path) -> Tuple[str, str]:
        suffix = path.suffix.lower()
        if suffix != ".zip":
            raise RuntimeError("Only .zip archives are supported")
        parts: List[str] = []
        with zipfile.ZipFile(str(path), "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                parts.append(f"[member {name}]")
                try:
                    data = zf.read(info)
                except Exception:
                    continue
                if len(data) > 2_000_000:
                    parts.append("(member too large to inline)")
                    continue
                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError:
                    text = data.decode("latin-1", errors="replace")
                parts.append(_normalize_text(text))
        title = path.stem
        return title, _normalize_text("\n".join(parts))


class ExtractorRegistry:
    def __init__(self) -> None:
        self._by_suffix: Dict[str, FileExtractor] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for s in (".txt",):
            self._by_suffix[s] = TextExtractor()
        for s in (".md", ".markdown"):
            self._by_suffix[s] = MarkdownExtractor()
        for s in (".log",):
            self._by_suffix[s] = LogExtractor()
        for s in (".pdf",):
            self._by_suffix[s] = PdfExtractor()
        for s in (".docx",):
            self._by_suffix[s] = DocxExtractor()
        for s in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"):
            self._by_suffix[s] = ImageExtractor()
        for s in (".csv", ".tsv", ".xlsx", ".xlsm", ".xltx", ".xltm"):
            self._by_suffix[s] = SpreadsheetExtractor()
        for s in (".zip",):
            self._by_suffix[s] = ArchiveExtractor()

    def get_extractor(self, path: Path) -> FileExtractor:
        ext = path.suffix.lower()
        if ext in self._by_suffix:
            return self._by_suffix[ext]
        raise RuntimeError(f"No extractor registered for {ext}")

    def can_extract(self, path: Path) -> bool:
        return path.suffix.lower() in self._by_suffix


class TagManager:
    def __init__(self, storage: Storage) -> None:
        self._s = storage

    def ensure_tag(self, name: str) -> int:
        name = name.strip()
        if not name:
            raise ValueError("Tag name cannot be empty")
        cur = self._s.conn.execute("SELECT id FROM tags WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            return int(row["id"])
        cur = self._s.conn.execute("INSERT INTO tags(name) VALUES (?)", (name,))
        self._s.conn.commit()
        return int(cur.lastrowid)

    def set_document_tags(self, document_id: int, tags: Sequence[str]) -> None:
        tag_ids = [self.ensure_tag(t) for t in tags]
        self._s.conn.execute("DELETE FROM document_tags WHERE document_id = ?", (document_id,))
        self._s.conn.executemany(
            "INSERT OR IGNORE INTO document_tags(document_id, tag_id) VALUES (?, ?)",
            [(document_id, tid) for tid in tag_ids],
        )
        self._s.conn.commit()

    def get_document_tags(self, document_id: int) -> List[str]:
        cur = self._s.conn.execute(
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


class Journal:
    def __init__(self, storage: Storage) -> None:
        self._s = storage

    def write(self, kind: str, payload: Dict[str, Any]) -> int:
        kind = kind.strip()
        if not kind:
            raise ValueError("Journal kind cannot be empty")
        created_at = _utc_now_iso()
        cur = self._s.conn.execute(
            "INSERT INTO journals(created_at, kind, payload_json) VALUES (?, ?, ?)",
            (created_at, kind, json.dumps(payload, ensure_ascii=False)),
        )
        self._s.conn.commit()
        return int(cur.lastrowid)

    def list(self, limit: int = 100) -> List[Dict[str, Any]]:
        limit = _clamp(int(limit), 1, 1000)
        cur = self._s.conn.execute(
            "SELECT id, created_at, kind, payload_json FROM journals ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        out: List[Dict[str, Any]] = []
        for r in cur.fetchall():
            out.append(
                {
                    "id": int(r["id"]),
                    "created_at": str(r["created_at"]),
                    "kind": str(r["kind"]),
                    "payload": json.loads(str(r["payload_json"])),
                }
            )
        return out


class CatalogManager:
    def __init__(self, storage: Storage) -> None:
        self._s = storage

    def upsert_catalog(self, name: str, query: Dict[str, Any]) -> int:
        name = name.strip()
        if not name:
            raise ValueError("Catalog name cannot be empty")
        now = _utc_now_iso()
        qj = json.dumps(query, ensure_ascii=False)
        cur = self._s.conn.execute("SELECT id FROM catalogs WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            cid = int(row["id"])
            self._s.conn.execute(
                "UPDATE catalogs SET query_json = ?, updated_at = ? WHERE id = ?",
                (qj, now, cid),
            )
            self._s.conn.commit()
            return cid
        cur = self._s.conn.execute(
            "INSERT INTO catalogs(name, query_json, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (name, qj, now, now),
        )
        self._s.conn.commit()
        return int(cur.lastrowid)

    def get_catalog(self, name: str) -> Optional[Dict[str, Any]]:
        cur = self._s.conn.execute(
            "SELECT id, name, query_json, created_at, updated_at FROM catalogs WHERE name = ?",
            (name,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "query": json.loads(str(row["query_json"])),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    def list_catalogs(self) -> List[Dict[str, Any]]:
        cur = self._s.conn.execute("SELECT id, name, query_json, created_at, updated_at FROM catalogs ORDER BY name")
        out: List[Dict[str, Any]] = []
        for r in cur.fetchall():
            out.append(
                {
                    "id": int(r["id"]),
                    "name": str(r["name"]),
                    "query": json.loads(str(r["query_json"])),
                    "created_at": str(r["created_at"]),
                    "updated_at": str(r["updated_at"]),
                }
            )
        return out


class ViewManager:
    def __init__(self, storage: Storage) -> None:
        self._s = storage

    def upsert_view(self, name: str, spec: Dict[str, Any]) -> int:
        name = name.strip()
        if not name:
            raise ValueError("View name cannot be empty")
        now = _utc_now_iso()
        sj = json.dumps(spec, ensure_ascii=False)
        cur = self._s.conn.execute("SELECT id FROM views WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            vid = int(row["id"])
            self._s.conn.execute("UPDATE views SET spec_json = ?, updated_at = ? WHERE id = ?", (sj, now, vid))
            self._s.conn.commit()
            return vid
        cur = self._s.conn.execute(
            "INSERT INTO views(name, spec_json, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (name, sj, now, now),
        )
        self._s.conn.commit()
        return int(cur.lastrowid)

    def get_view(self, name: str) -> Optional[Dict[str, Any]]:
        cur = self._s.conn.execute("SELECT id, name, spec_json, created_at, updated_at FROM views WHERE name = ?", (name,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "spec": json.loads(str(row["spec_json"])),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    def list_views(self) -> List[Dict[str, Any]]:
        cur = self._s.conn.execute("SELECT id, name, spec_json, created_at, updated_at FROM views ORDER BY name")
        out: List[Dict[str, Any]] = []
        for r in cur.fetchall():
            out.append(
                {
                    "id": int(r["id"]),
                    "name": str(r["name"]),
                    "spec": json.loads(str(r["spec_json"])),
                    "created_at": str(r["created_at"]),
                    "updated_at": str(r["updated_at"]),
                }
            )
        return out


class DocumentStore:
    def __init__(self, storage: Storage, root: Path, extractor_registry: ExtractorRegistry, journal: Journal) -> None:
        self._s = storage
        self._root = root
        self._x = extractor_registry
        self._journal = journal

    @property
    def root(self) -> Path:
        return self._root

    def ingest_path(self, path: Path) -> int:
        path = path.resolve()
        if not path.exists():
            raise FileNotFoundError(str(path))
        if path.is_dir():
            raise ValueError("ingest_path expects a file, not a directory")
        if not self._x.can_extract(path):
            raise RuntimeError(f"Unsupported file type: {path.suffix.lower()}")

        rel = _safe_relpath(path, self._root)
        mime = _guess_mime(path)
        size = path.stat().st_size
        sha = _sha256_file(path)
        title, content = self._x.get_extractor(path).extract(path)
        title = (title or Path(rel).stem).strip() or Path(rel).name
        content = _normalize_text(content or "")

        now = _utc_now_iso()
        cur = self._s.conn.execute("SELECT id, sha256 FROM documents WHERE source_path = ?", (rel,))
        row = cur.fetchone()
        if row:
            doc_id = int(row["id"])
            old_sha = str(row["sha256"])
            if old_sha != sha:
                self._s.conn.execute(
                    """
                    UPDATE documents
                    SET title = ?, mime_type = ?, size_bytes = ?, sha256 = ?, updated_at = ?, content_text = ?
                    WHERE id = ?
                    """,
                    (title, mime, int(size), sha, now, content, doc_id),
                )
                self._s.conn.commit()
                self._journal.write(
                    "document_updated",
                    {"document_id": doc_id, "source_path": rel, "sha256": sha, "size_bytes": int(size)},
                )
            return doc_id

        cur = self._s.conn.execute(
            """
            INSERT INTO documents(source_path, title, mime_type, size_bytes, sha256, created_at, updated_at, ingested_at, content_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (rel, title, mime, int(size), sha, now, now, now, content),
        )
        self._s.conn.commit()
        doc_id = int(cur.lastrowid)
        self._journal.write(
            "document_ingested",
            {"document_id": doc_id, "source_path": rel, "sha256": sha, "size_bytes": int(size)},
        )
        return doc_id

    def ingest_tree(self, folder: Path) -> List[int]:
        folder = folder.resolve()
        if not folder.exists() or not folder.is_dir():
            raise FileNotFoundError(str(folder))
        ids: List[int] = []
        for p in sorted(folder.rglob("*")):
            if p.is_file() and self._x.can_extract(p):
                try:
                    ids.append(self.ingest_path(p))
                except Exception:
                    continue
        return ids

    def get_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        cur = self._s.conn.execute(
            """
            SELECT id, source_path, title, mime_type, size_bytes, sha256, created_at, updated_at, ingested_at, content_text
            FROM documents WHERE id = ?
            """,
            (int(document_id),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": int(row["id"]),
            "source_path": str(row["source_path"]),
            "title": str(row["title"]),
            "mime_type": str(row["mime_type"]),
            "size_bytes": int(row["size_bytes"]),
            "sha256": str(row["sha256"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
            "ingested_at": str(row["ingested_at"]),
            "content_text": str(row["content_text"]),
        }

    def list_documents(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        limit = _clamp(int(limit), 1, 1000)
        offset = max(0, int(offset))
        cur = self._s.conn.execute(
            """
            SELECT id, source_path, title, mime_type, size_bytes, sha256, created_at, updated_at, ingested_at
            FROM documents
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        out: List[Dict[str, Any]] = []
        for r in cur.fetchall():
            out.append(
                {
                    "id": int(r["id"]),
                    "source_path": str(r["source_path"]),
                    "title": str(r["title"]),
                    "mime_type": str(r["mime_type"]),
                    "size_bytes": int(r["size_bytes"]),
                    "sha256": str(r["sha256"]),
                    "created_at": str(r["created_at"]),
                    "updated_at": str(r["updated_at"]),
                    "ingested_at": str(r["ingested_at"]),
                }
            )
        return out


class RelationMiner:
    def __init__(self, storage: Storage, journal: Journal) -> None:
        self._s = storage
        self._journal = journal

    def mine_relations(self, document_id: int, top_k: int = 10) -> List[Dict[str, Any]]:
        top_k = _clamp(int(top_k), 1, 100)
        cur = self._s.conn.execute("SELECT id, content_text FROM documents WHERE id = ?", (int(document_id),))
        row = cur.fetchone()
        if not row:
            raise ValueError("Unknown document_id")
        src_text = str(row["content_text"])
        src_tokens = set(_tokenize(src_text))
        if not src_tokens:
            return []

        cur = self._s.conn.execute("SELECT id, content_text FROM documents WHERE id != ?", (int(document_id),))
        scores: List[Tuple[int, float]] = []
        for r in cur.fetchall():
            did = int(r["id"])
            toks = set(_tokenize(str(r["content_text"])))
            if not toks:
                continue
            inter = len(src_tokens & toks)
            union = len(src_tokens | toks)
            if union == 0:
                continue
            j = inter / union
            if j > 0:
                scores.append((did, float(j)))
        scores.sort(key=lambda x: x[1], reverse=True)
        scores = scores[:top_k]

        now = _utc_now_iso()
        out: List[Dict[str, Any]] = []
        for to_id, sc in scores:
            self._s.conn.execute(
                """
                INSERT INTO relations(from_document_id, to_document_id, relation_type, score, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(from_document_id, to_document_id, relation_type)
                DO UPDATE SET score = excluded.score, created_at = excluded.created_at
                """,
                (int(document_id), int(to_id), "lexical_overlap", float(sc), now),
            )
            out.append(
                {
                    "from_document_id": int(document_id),
                    "to_document_id": int(to_id),
                    "relation_type": "lexical_overlap",
                    "score": float(sc),
                    "created_at": now,
                }
            )
        self._s.conn.commit()
        self._journal.write(
            "relations_mined",
            {"document_id": int(document_id), "relation_type": "lexical_overlap", "count": len(out)},
        )
        return out

    def list_relations(self, document_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        limit = _clamp(int(limit), 1, 500)
        cur = self._s.conn.execute(
            """
            SELECT id, from_document_id, to_document_id, relation_type, score, created_at
            FROM relations
            WHERE from_document_id = ?
            ORDER BY score DESC
            LIMIT ?
            """,
            (int(document_id), limit),
        )
        out: List[Dict[str, Any]] = []
        for r in cur.fetchall():
            out.append(
                {
                    "id": int(r["id"]),
                    "from_document_id": int(r["from_document_id"]),
                    "to_document_id": int(r["to_document_id"]),
                    "relation_type": str(r["relation_type"]),
                    "score": float(r["score"]),
                    "created_at": str(r["created_at"]),
                }
            )
        return out


class SearchEngine:
    def __init__(self, storage: Storage) -> None:
        self._s = storage

    def lexical_search(self, query: str, limit: int = 20) -> List[SearchCandidate]:
        query = (query or "").strip()
        if not query:
            return []
        limit = _clamp(int(limit), 1, 200)

        fts_query = self._to_fts_query(query)
        cur = self._s.conn.execute(
            """
            SELECT d.id as id, d.source_path as source_path, d.title as title,
                   snippet(documents_fts, 1, '[', ']', '…', 12) as snip,
                   bm25(documents_fts, 5.0, 1.0, 2.0) as rank
            FROM documents_fts
            JOIN documents d ON d.id = documents_fts.rowid
            WHERE documents_fts MATCH ?
            ORDER BY rank ASC
            LIMIT ?
            """,
            (fts_query, limit),
        )
        out: List[SearchCandidate] = []
        for r in cur.fetchall():
            rank = float(r["rank"])
            score = 1.0 / (1.0 + max(0.0, rank))
            out.append(
                SearchCandidate(
                    document_id=int(r["id"]),
                    score=float(score),
                    source_path=str(r["source_path"]),
                    title=str(r["title"]),
                    snippet=str(r["snip"] or ""),
                )
            )
        return out

    def _to_fts_query(self, query: str) -> str:
        toks = _tokenize(query)
        if not toks:
            return query
        toks = toks[:12]
        return " ".join([f'"{t}"' for t in toks])


class Reader:
    def __init__(self, storage: Storage) -> None:
        self._s = storage

    def read_windows(
        self,
        document_id: int,
        *,
        kind: str = "lines",
        start: int = 1,
        count: int = 60,
    ) -> List[FileWindow]:
        kind = kind.strip().lower()
        if kind not in ("lines", "pages", "sections", "table_slices", "archive_members"):
            raise ValueError("Unsupported window kind")
        start = max(1, int(start))
        count = _clamp(int(count), 1, 500)

        cur = self._s.conn.execute("SELECT id, source_path, content_text FROM documents WHERE id = ?", (int(document_id),))
        row = cur.fetchone()
        if not row:
            raise ValueError("Unknown document_id")
        source_path = str(row["source_path"])
        text = _normalize_text(str(row["content_text"]))

        if kind == "lines":
            lines = text.split("\n")
            i0 = start - 1
            i1 = min(len(lines), i0 + count)
            chunk = "\n".join(lines[i0:i1])
            locator = f"lines {start}-{i1}"
            return [FileWindow(document_id=int(document_id), source_path=source_path, kind="lines", locator=locator, content=chunk)]

        if kind == "pages":
            page_size = 1800
            pages = [text[i : i + page_size] for i in range(0, len(text), page_size)]
            i0 = start - 1
            i1 = min(len(pages), i0 + count)
            chunk = "\n\n".join([f"[page {idx+1}]\n{pages[idx]}" for idx in range(i0, i1)])
            locator = f"pages {start}-{i1}"
            return [FileWindow(document_id=int(document_id), source_path=source_path, kind="pages", locator=locator, content=chunk)]

        if kind == "sections":
            parts = re.split(r"\n(?=#{1,6}\s)", text)
            parts = [p.strip("\n") for p in parts if p.strip()]
            if not parts:
                parts = [text]
            i0 = start - 1
            i1 = min(len(parts), i0 + count)
            chunk = "\n\n".join([f"[section {idx+1}]\n{parts[idx]}" for idx in range(i0, i1)])
            locator = f"sections {start}-{i1}"
            return [FileWindow(document_id=int(document_id), source_path=source_path, kind="sections", locator=locator, content=chunk)]

        if kind == "archive_members":
            members: List[Tuple[str, str]] = []
            current_name: Optional[str] = None
            buf: List[str] = []
            for line in text.split("\n"):
                m = re.match(r"^\[member\s+(.+?)\]\s*$", line.strip())
                if m:
                    if current_name is not None:
                        members.append((current_name, "\n".join(buf).strip("\n")))
                    current_name = m.group(1)
                    buf = []
                else:
                    buf.append(line)
            if current_name is not None:
                members.append((current_name, "\n".join(buf).strip("\n")))
            if not members:
                members = [("unknown", text)]
            i0 = start - 1
            i1 = min(len(members), i0 + count)
            chunk = "\n\n".join([f"[member {members[idx][0]}]\n{members[idx][1]}" for idx in range(i0, i1)])
            locator = f"members {start}-{i1}"
            return [FileWindow(document_id=int(document_id), source_path=source_path, kind="archive_members", locator=locator, content=chunk)]

        if kind == "table_slices":
            lines = text.split("\n")
            rows = [ln for ln in lines if ("\t" in ln or "," in ln)]
            if not rows:
                rows = lines
            i0 = start - 1
            i1 = min(len(rows), i0 + count)
            chunk = "\n".join(rows[i0:i1])
            locator = f"rows {start}-{i1}"
            return [FileWindow(document_id=int(document_id), source_path=source_path, kind="table_slices", locator=locator, content=chunk)]

        raise ValueError("Unsupported window kind")


class SourceQuota:
    def __init__(self, max_documents: int = 6, max_windows: int = 10, max_total_chars: int = 24_000) -> None:
        self.max_documents = _clamp(int(max_documents), 1, 50)
        self.max_windows = _clamp(int(max_windows), 1, 200)
        self.max_total_chars = _clamp(int(max_total_chars), 500, 500_000)

    def enforce_candidates(self, candidates: List[SearchCandidate]) -> List[SearchCandidate]:
        return candidates[: self.max_documents]

    def enforce_windows(self, windows: List[FileWindow]) -> List[FileWindow]:
        windows = windows[: self.max_windows]
        total = 0
        out: List[FileWindow] = []
        for w in windows:
            remaining = self.max_total_chars - total
            if remaining <= 0:
                break
            content = w.content
            if len(content) > remaining:
                content = content[:remaining]
                w = FileWindow(
                    document_id=w.document_id,
                    source_path=w.source_path,
                    kind=w.kind,
                    locator=w.locator,
                    content=content,
                )
            out.append(w)
            total += len(w.content)
        return out


class NotesManager:
    def __init__(self, storage: Storage, journal: Journal) -> None:
        self._s = storage
        self._journal = journal

    def create_note(self, title: str, body: str, citations: List[Citation]) -> int:
        title = (title or "").strip()
        if not title:
            title = "Investigation Note"
        body = _normalize_text(body or "")
        now = _utc_now_iso()
        cj = json.dumps([c.__dict__ for c in citations], ensure_ascii=False)
        cur = self._s.conn.execute(
            "INSERT INTO notes(created_at, updated_at, title, body, citations_json) VALUES (?, ?, ?, ?, ?)",
            (now, now, title, body, cj),
        )
        self._s.conn.commit()
        nid = int(cur.lastrowid)
        self._journal.write("note_created", {"note_id": nid, "title": title})
        return nid

    def update_note(self, note_id: int, *, title: Optional[str] = None, body: Optional[str] = None) -> None:
        cur = self._s.conn.execute("SELECT id, title, body FROM notes WHERE id = ?", (int(note_id),))
        row = cur.fetchone()
        if not row:
            raise ValueError("Unknown note_id")
        new_title = str(row["title"]) if title is None else (title or "").strip() or str(row["title"])
        new_body = str(row["body"]) if body is None else _normalize_text(body or "")
        now = _utc_now_iso()
        self._s.conn.execute(
            "UPDATE notes SET title = ?, body = ?, updated_at = ? WHERE id = ?",
            (new_title, new_body, now, int(note_id)),
        )
        self._s.conn.commit()
        self._journal.write("note_updated", {"note_id": int(note_id)})

    def get_note(self, note_id: int) -> Optional[Dict[str, Any]]:
        cur = self._s.conn.execute(
            "SELECT id, created_at, updated_at, title, body, citations_json FROM notes WHERE id = ?",
            (int(note_id),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": int(row["id"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
            "title": str(row["title"]),
            "body": str(row["body"]),
            "citations": json.loads(str(row["citations_json"])),
        }

    def search_notes(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return []
        limit = _clamp(int(limit), 1, 200)
        toks = _tokenize(query)
        if not toks:
            return []
        like = "%" + "%".join(toks[:6]) + "%"
        cur = self._s.conn.execute(
            """
            SELECT id, created_at, updated_at, title, body, citations_json
            FROM notes
            WHERE lower(title) LIKE lower(?) OR lower(body) LIKE lower(?)
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (like, like, limit),
        )
        out: List[Dict[str, Any]] = []
        for r in cur.fetchall():
            out.append(
                {
                    "id": int(r["id"]),
                    "created_at": str(r["created_at"]),
                    "updated_at": str(r["updated_at"]),
                    "title": str(r["title"]),
                    "body": str(r["body"]),
                    "citations": json.loads(str(r["citations_json"])),
                }
            )
        return out


class InvestigationManager:
    def __init__(self, storage: Storage, journal: Journal) -> None:
        self._s = storage
        self._journal = journal

    def create_investigation(self, query: str, answer: Answer, notes_id: Optional[int]) -> int:
        now = _utc_now_iso()
        cj = json.dumps([c.__dict__ for c in answer.citations], ensure_ascii=False)
        cur = self._s.conn.execute(
            """
            INSERT INTO investigations(created_at, updated_at, query, answer_text, citations_json, notes_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (now, now, (query or "").strip(), answer.text, cj, notes_id),
        )
        self._s.conn.commit()
        iid = int(cur.lastrowid)
        self._journal.write("investigation_created", {"investigation_id": iid, "notes_id": notes_id})
        return iid

    def list_investigations(self, limit: int = 50) -> List[Dict[str, Any]]:
        limit = _clamp(int(limit), 1, 500)
        cur = self._s.conn.execute(
            """
            SELECT id, created_at, updated_at, query, answer_text, citations_json, notes_id
            FROM investigations
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        out: List[Dict[str, Any]] = []
        for r in cur.fetchall():
            out.append(
                {
                    "id": int(r["id"]),
                    "created_at": str(r["created_at"]),
                    "updated_at": str(r["updated_at"]),
                    "query": str(r["query"]),
                    "answer_text": str(r["answer_text"]),
                    "citations": json.loads(str(r["citations_json"])),
                    "notes_id": (int(r["notes_id"]) if r["notes_id"] is not None else None),
                }
            )
        return out


class LLMClient:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class DeterministicLLM(LLMClient):
    def generate(self, prompt: str) -> str:
        prompt = prompt or ""
        lines = [ln.strip() for ln in prompt.splitlines() if ln.strip()]
        q = ""
        for ln in lines[::-1]:
            if ln.lower().startswith("question:"):
                q = ln.split(":", 1)[1].strip()
                break
        if not q:
            q = "the question"
        return f"Answer based on provided sources: {q}"


class Agent:
    def __init__(
        self,
        storage: Storage,
        search: SearchEngine,
        reader: Reader,
        notes: NotesManager,
        investigations: InvestigationManager,
        journal: Journal,
        llm: LLMClient,
    ) -> None:
        self._s = storage
        self._search = search
        self._reader = reader
        self._notes = notes
        self._investigations = investigations
        self._journal = journal
        self._llm = llm

    def answer(
        self,
        query: str,
        *,
        candidate_limit: int = 20,
        window_kind: str = "lines",
        window_start: int = 1,
        window_count: int = 80,
        quota: Optional[SourceQuota] = None,
        write_investigation_note: bool = True,
    ) -> Answer:
        query = (query or "").strip()
        if not query:
            raise ValueError("Query cannot be empty")

        quota = quota or SourceQuota()
        candidates = self._search.lexical_search(query, limit=candidate_limit)
        candidates = quota.enforce_candidates(candidates)

        windows: List[FileWindow] = []
        for cand in candidates:
            try:
                ws = self._reader.read_windows(
                    cand.document_id,
                    kind=window_kind,
                    start=window_start,
                    count=window_count,
                )
                windows.extend(ws)
            except Exception:
                continue
        windows = quota.enforce_windows(windows)

        prompt = self._build_prompt(query, windows)
        text = self._llm.generate(prompt)
        citations = [Citation(document_id=w.document_id, source_path=w.source_path, kind=w.kind, locator=w.locator) for w in windows]
        ans = Answer(text=text, citations=citations, created_at=_utc_now_iso())

        note_id: Optional[int] = None
        if write_investigation_note:
            note_title = f"Investigation: {query[:80]}"
            note_body = self._build_note_body(query, ans, windows)
            note_id = self._notes.create_note(note_title, note_body, citations)

        self._investigations.create_investigation(query, ans, note_id)
        self._journal.write(
            "agent_answered",
            {
                "query": query,
                "candidate_count": len(candidates),
                "window_count": len(windows),
                "note_id": note_id,
            },
        )
        return ans

    def _build_prompt(self, query: str, windows: List[FileWindow]) -> str:
        parts: List[str] = []
        parts.append("You are a local-first research agent. Use ONLY the provided source windows.")
        parts.append("Cite sources by their source_path and locator.")
        parts.append("")
        parts.append(f"Question: {query}")
        parts.append("")
        parts.append("Sources:")
        for i, w in enumerate(windows, start=1):
            parts.append(f"[{i}] {w.source_path} ({w.kind}, {w.locator})")
            parts.append(w.content)
            parts.append("")
        parts.append("Write a concise answer with citations.")
        return "\n".join(parts).strip() + "\n"

    def _build_note_body(self, query: str, ans: Answer, windows: List[FileWindow]) -> str:
        lines: List[str] = []
        lines.append(f"Query: {query}")
        lines.append(f"Created: {ans.created_at}")
        lines.append("")
        lines.append("Answer:")
        lines.append(ans.text)
        lines.append("")
        lines.append("Citations:")
        for c in ans.citations:
            lines.append(f"- {c.source_path} ({c.kind}, {c.locator})")
        lines.append("")
        lines.append("Read windows:")
        for w in windows:
            lines.append(f"--- {w.source_path} ({w.kind}, {w.locator}) ---")
            lines.append(w.content)
            lines.append("")
        return "\n".join(lines).strip() + "\n"


class Marginalia:
    def __init__(self, root_folder: Union[str, Path], db_path: Optional[Union[str, Path]] = None) -> None:
        self._root = Path(root_folder).expanduser().resolve()
        _ensure_dir(self._root)

        if db_path is None:
            db_path = self._root / ".marginalia" / "marginalia.sqlite3"
        self._db_path = Path(db_path).expanduser().resolve()
        _ensure_dir(self._db_path.parent)

        self.storage = Storage(self._db_path)
        self.journal = Journal(self.storage)
        self.extractors = ExtractorRegistry()
        self.documents = DocumentStore(self.storage, self._root, self.extractors, self.journal)
        self.tags = TagManager(self.storage)
        self.catalogs = CatalogManager(self.storage)
        self.views = ViewManager(self.storage)
        self.relations = RelationMiner(self.storage, self.journal)
        self.search = SearchEngine(self.storage)
        self.reader = Reader(self.storage)
        self.notes = NotesManager(self.storage, self.journal)
        self.investigations = InvestigationManager(self.storage, self.journal)
        self.agent = Agent(
            storage=self.storage,
            search=self.search,
            reader=self.reader,
            notes=self.notes,
            investigations=self.investigations,
            journal=self.journal,
            llm=DeterministicLLM(),
        )

    @property
    def root(self) -> Path:
        return self._root

    @property
    def db_path(self) -> Path:
        return self._db_path

    def close(self) -> None:
        self.storage.close()

    def ingest(self, path: Union[str, Path]) -> int:
        return self.documents.ingest_path(Path(path))

    def ingest_all(self, folder: Optional[Union[str, Path]] = None) -> List[int]:
        folder_path = self._root if folder is None else Path(folder)
        return self.documents.ingest_tree(folder_path)

    def set_tags(self, document_id: int, tags: Sequence[str]) -> None:
        self.tags.set_document_tags(document_id, tags)
        self.journal.write("tags_set", {"document_id": int(document_id), "tags": list(tags)})

    def get_tags(self, document_id: int) -> List[str]:
        return self.tags.get_document_tags(document_id)

    def create_catalog(self, name: str, query: Dict[str, Any]) -> int:
        cid = self.catalogs.upsert_catalog(name, query)
        self.journal.write("catalog_upserted", {"catalog_id": cid, "name": name})
        return cid

    def create_view(self, name: str, spec: Dict[str, Any]) -> int:
        vid = self.views.upsert_view(name, spec)
        self.journal.write("view_upserted", {"view_id": vid, "name": name})
        return vid

    def search_lexical(self, query: str, limit: int = 20) -> List[SearchCandidate]:
        return self.search.lexical_search(query, limit=limit)

    def read(self, document_id: int, *, kind: str = "lines", start: int = 1, count: int = 60) -> List[FileWindow]:
        return self.reader.read_windows(document_id, kind=kind, start=start, count=count)

    def answer(
        self,
        query: str,
        *,
        candidate_limit: int = 20,
        window_kind: str = "lines",
        window_start: int = 1,
        window_count: int = 80,
        quota: Optional[SourceQuota] = None,
        write_investigation_note: bool = True,
    ) -> Answer:
        return self.agent.answer(
            query,
            candidate_limit=candidate_limit,
            window_kind=window_kind,
            window_start=window_start,
            window_count=window_count,
            quota=quota,
            write_investigation_note=write_investigation_note,
        )