from __future__ import annotations

import os
import re
import io
import json
import time
import math
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


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _guess_mime(path: Path) -> str:
    mt, _ = mimetypes.guess_type(str(path))
    return mt or "application/octet-stream"


def _normalize_whitespace(s: str) -> str:
    return re.sub(r"[ \t]+", " ", re.sub(r"\r\n?", "\n", s)).strip()


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9_]+", text.lower())


def _chunk_lines(lines: List[str], start: int, end: int) -> str:
    start = max(1, start)
    end = max(start, end)
    start_idx = start - 1
    end_idx = min(len(lines), end)
    return "\n".join(lines[start_idx:end_idx])


def _chunk_chars(text: str, start: int, end: int) -> str:
    start = max(0, start)
    end = max(start, end)
    return text[start:end]


class MarginaliaError(Exception):
    pass


class ValidationError(MarginaliaError):
    pass


class NotFoundError(MarginaliaError):
    pass


class QuotaError(MarginaliaError):
    pass


@dataclass(frozen=True)
class DocumentRef:
    doc_id: str
    relpath: str
    mime: str
    sha256: str


@dataclass(frozen=True)
class Citation:
    doc_id: str
    relpath: str
    locator: str
    quote: str


@dataclass(frozen=True)
class SearchHit:
    doc_id: str
    relpath: str
    score: float
    snippet: str


@dataclass(frozen=True)
class ReadWindow:
    doc_id: str
    relpath: str
    locator: str
    content: str


@dataclass(frozen=True)
class Answer:
    text: str
    citations: List[Citation]
    created_at: str


class Storage:
    def __init__(self, root: Union[str, Path]):
        self._root = Path(root).expanduser().resolve()
        _ensure_dir(self._root)

    @property
    def root(self) -> Path:
        return self._root

    def resolve_relpath(self, relpath: str) -> Path:
        p = (self._root / relpath).resolve()
        if not str(p).startswith(str(self._root)):
            raise ValidationError("relpath escapes root")
        return p

    def list_files(self) -> List[str]:
        out: List[str] = []
        for p in self._root.rglob("*"):
            if p.is_file():
                out.append(_safe_relpath(p, self._root))
        out.sort()
        return out

    def read_bytes(self, relpath: str) -> bytes:
        p = self.resolve_relpath(relpath)
        if not p.exists() or not p.is_file():
            raise NotFoundError(f"File not found: {relpath}")
        return p.read_bytes()

    def read_text(self, relpath: str, encoding: str = "utf-8", errors: str = "replace") -> str:
        return self.read_bytes(relpath).decode(encoding, errors=errors)

    def write_bytes(self, relpath: str, data: bytes) -> None:
        p = self.resolve_relpath(relpath)
        _ensure_dir(p.parent)
        p.write_bytes(data)

    def write_text(self, relpath: str, text: str, encoding: str = "utf-8") -> None:
        self.write_bytes(relpath, text.encode(encoding))

    def exists(self, relpath: str) -> bool:
        p = self.resolve_relpath(relpath)
        return p.exists()

    def stat(self, relpath: str) -> os.stat_result:
        p = self.resolve_relpath(relpath)
        return p.stat()


class MetadataStore:
    def __init__(self, db_path: Union[str, Path]):
        self._db_path = Path(db_path).expanduser().resolve()
        _ensure_dir(self._db_path.parent)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        c = self._conn.cursor()
        c.execute("PRAGMA journal_mode=WAL;")
        c.execute("PRAGMA foreign_keys=ON;")

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                relpath TEXT UNIQUE NOT NULL,
                mime TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                mtime_ns INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                tag TEXT PRIMARY KEY
            );
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS document_tags (
                doc_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (doc_id, tag),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (tag) REFERENCES tags(tag) ON DELETE CASCADE
            );
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                doc_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (doc_id, key),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS journals (
                entry_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                related_doc_ids TEXT NOT NULL
            );
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS relations (
                rel_id TEXT PRIMARY KEY,
                src_doc_id TEXT NOT NULL,
                dst_doc_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                score REAL NOT NULL,
                evidence TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (src_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (dst_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS lexical_index (
                doc_id TEXT NOT NULL,
                token TEXT NOT NULL,
                freq INTEGER NOT NULL,
                PRIMARY KEY (doc_id, token),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );
            """
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_lex_token ON lexical_index(token);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_docs_relpath ON documents(relpath);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_rel_src ON relations(src_doc_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_rel_dst ON relations(dst_doc_id);")
        self._conn.commit()

    def upsert_document(
        self,
        relpath: str,
        mime: str,
        sha256: str,
        size_bytes: int,
        mtime_ns: int,
    ) -> DocumentRef:
        if not relpath or relpath.startswith("/") or ".." in Path(relpath).parts:
            raise ValidationError("Invalid relpath")
        now = _iso(_utc_now())
        c = self._conn.cursor()
        row = c.execute("SELECT doc_id, sha256, mtime_ns FROM documents WHERE relpath=?", (relpath,)).fetchone()
        if row is None:
            doc_id = str(uuid.uuid4())
            c.execute(
                """
                INSERT INTO documents (doc_id, relpath, mime, sha256, size_bytes, mtime_ns, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (doc_id, relpath, mime, sha256, size_bytes, mtime_ns, now, now),
            )
        else:
            doc_id = row["doc_id"]
            c.execute(
                """
                UPDATE documents
                SET mime=?, sha256=?, size_bytes=?, mtime_ns=?, updated_at=?
                WHERE doc_id=?
                """,
                (mime, sha256, size_bytes, mtime_ns, now, doc_id),
            )
        self._conn.commit()
        return DocumentRef(doc_id=doc_id, relpath=relpath, mime=mime, sha256=sha256)

    def get_document_by_id(self, doc_id: str) -> DocumentRef:
        c = self._conn.cursor()
        row = c.execute("SELECT doc_id, relpath, mime, sha256 FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Document not found: {doc_id}")
        return DocumentRef(doc_id=row["doc_id"], relpath=row["relpath"], mime=row["mime"], sha256=row["sha256"])

    def get_document_by_relpath(self, relpath: str) -> DocumentRef:
        c = self._conn.cursor()
        row = c.execute("SELECT doc_id, relpath, mime, sha256 FROM documents WHERE relpath=?", (relpath,)).fetchone()
        if row is None:
            raise NotFoundError(f"Document not found: {relpath}")
        return DocumentRef(doc_id=row["doc_id"], relpath=row["relpath"], mime=row["mime"], sha256=row["sha256"])

    def list_documents(self) -> List[DocumentRef]:
        c = self._conn.cursor()
        rows = c.execute("SELECT doc_id, relpath, mime, sha256 FROM documents ORDER BY relpath").fetchall()
        return [DocumentRef(doc_id=r["doc_id"], relpath=r["relpath"], mime=r["mime"], sha256=r["sha256"]) for r in rows]

    def delete_document(self, doc_id: str) -> None:
        c = self._conn.cursor()
        c.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
        self._conn.commit()

    def set_tags(self, doc_id: str, tags: Sequence[str]) -> None:
        norm: List[str] = []
        for t in tags:
            t2 = _normalize_whitespace(t)
            if not t2:
                continue
            if len(t2) > 128:
                raise ValidationError("Tag too long")
            norm.append(t2)
        norm = sorted(set(norm))
        c = self._conn.cursor()
        for t in norm:
            c.execute("INSERT OR IGNORE INTO tags(tag) VALUES (?)", (t,))
        c.execute("DELETE FROM document_tags WHERE doc_id=?", (doc_id,))
        for t in norm:
            c.execute("INSERT INTO document_tags(doc_id, tag) VALUES (?, ?)", (doc_id, t))
        self._conn.commit()

    def get_tags(self, doc_id: str) -> List[str]:
        c = self._conn.cursor()
        rows = c.execute(
            "SELECT tag FROM document_tags WHERE doc_id=? ORDER BY tag",
            (doc_id,),
        ).fetchall()
        return [r["tag"] for r in rows]

    def set_metadata(self, doc_id: str, key: str, value: str) -> None:
        key2 = _normalize_whitespace(key)
        if not key2:
            raise ValidationError("Metadata key required")
        if len(key2) > 128:
            raise ValidationError("Metadata key too long")
        if len(value) > 10000:
            raise ValidationError("Metadata value too long")
        c = self._conn.cursor()
        c.execute(
            "INSERT INTO metadata(doc_id, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT(doc_id, key) DO UPDATE SET value=excluded.value",
            (doc_id, key2, value),
        )
        self._conn.commit()

    def get_metadata(self, doc_id: str) -> Dict[str, str]:
        c = self._conn.cursor()
        rows = c.execute("SELECT key, value FROM metadata WHERE doc_id=? ORDER BY key", (doc_id,)).fetchall()
        return {r["key"]: r["value"] for r in rows}

    def add_journal_entry(
        self,
        kind: str,
        title: str,
        body: str,
        related_doc_ids: Sequence[str],
    ) -> str:
        kind2 = _normalize_whitespace(kind)
        title2 = _normalize_whitespace(title)
        if not kind2:
            raise ValidationError("Journal kind required")
        if not title2:
            raise ValidationError("Journal title required")
        if len(kind2) > 64:
            raise ValidationError("Journal kind too long")
        if len(title2) > 256:
            raise ValidationError("Journal title too long")
        if len(body) > 200000:
            raise ValidationError("Journal body too long")
        entry_id = str(uuid.uuid4())
        now = _iso(_utc_now())
        rel = json.dumps(list(related_doc_ids))
        c = self._conn.cursor()
        c.execute(
            "INSERT INTO journals(entry_id, created_at, kind, title, body, related_doc_ids) VALUES (?, ?, ?, ?, ?, ?)",
            (entry_id, now, kind2, title2, body, rel),
        )
        self._conn.commit()
        return entry_id

    def list_journal_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        if limit <= 0 or limit > 500:
            raise ValidationError("Invalid limit")
        c = self._conn.cursor()
        rows = c.execute(
            "SELECT entry_id, created_at, kind, title, body, related_doc_ids FROM journals ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "entry_id": r["entry_id"],
                    "created_at": r["created_at"],
                    "kind": r["kind"],
                    "title": r["title"],
                    "body": r["body"],
                    "related_doc_ids": json.loads(r["related_doc_ids"] or "[]"),
                }
            )
        return out

    def upsert_lexical_index(self, doc_id: str, token_freq: Dict[str, int]) -> None:
        c = self._conn.cursor()
        c.execute("DELETE FROM lexical_index WHERE doc_id=?", (doc_id,))
        rows = [(doc_id, tok, int(freq)) for tok, freq in token_freq.items() if tok and freq > 0]
        c.executemany("INSERT INTO lexical_index(doc_id, token, freq) VALUES (?, ?, ?)", rows)
        self._conn.commit()

    def lexical_search(self, tokens: Sequence[str], limit: int = 20) -> List[Tuple[str, float]]:
        if limit <= 0 or limit > 200:
            raise ValidationError("Invalid limit")
        toks = [t for t in (_normalize_whitespace(t) for t in tokens) if t]
        if not toks:
            return []
        toks = [t.lower() for t in toks]
        placeholders = ",".join("?" for _ in toks)
        c = self._conn.cursor()
        rows = c.execute(
            f"""
            SELECT doc_id, SUM(freq) AS score
            FROM lexical_index
            WHERE token IN ({placeholders})
            GROUP BY doc_id
            ORDER BY score DESC
            LIMIT ?
            """,
            (*toks, limit),
        ).fetchall()
        return [(r["doc_id"], float(r["score"] or 0.0)) for r in rows]

    def add_relation(
        self,
        src_doc_id: str,
        dst_doc_id: str,
        kind: str,
        score: float,
        evidence: str,
    ) -> str:
        kind2 = _normalize_whitespace(kind)
        if not kind2:
            raise ValidationError("Relation kind required")
        if len(kind2) > 64:
            raise ValidationError("Relation kind too long")
        if not (0.0 <= score <= 1.0):
            raise ValidationError("Relation score must be in [0,1]")
        if len(evidence) > 20000:
            raise ValidationError("Evidence too long")
        rel_id = str(uuid.uuid4())
        now = _iso(_utc_now())
        c = self._conn.cursor()
        c.execute(
            """
            INSERT INTO relations(rel_id, src_doc_id, dst_doc_id, kind, score, evidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (rel_id, src_doc_id, dst_doc_id, kind2, float(score), evidence, now),
        )
        self._conn.commit()
        return rel_id

    def list_relations_for_doc(self, doc_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        if limit <= 0 or limit > 1000:
            raise ValidationError("Invalid limit")
        c = self._conn.cursor()
        rows = c.execute(
            """
            SELECT rel_id, src_doc_id, dst_doc_id, kind, score, evidence, created_at
            FROM relations
            WHERE src_doc_id=? OR dst_doc_id=?
            ORDER BY score DESC, created_at DESC
            LIMIT ?
            """,
            (doc_id, doc_id, limit),
        ).fetchall()
        return [
            {
                "rel_id": r["rel_id"],
                "src_doc_id": r["src_doc_id"],
                "dst_doc_id": r["dst_doc_id"],
                "kind": r["kind"],
                "score": float(r["score"]),
                "evidence": r["evidence"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]


class ContentExtractor:
    def extract_text(self, storage: Storage, relpath: str, mime: str) -> str:
        mime = (mime or "").lower()
        p = storage.resolve_relpath(relpath)
        suffix = p.suffix.lower()

        if mime.startswith("text/") or suffix in {".md", ".markdown", ".txt", ".log", ".csv", ".tsv", ".json", ".yaml", ".yml"}:
            try:
                return storage.read_text(relpath)
            except Exception:
                return storage.read_bytes(relpath).decode("utf-8", errors="replace")

        if suffix == ".pdf" or mime == "application/pdf":
            return ""

        if suffix == ".docx" or mime in {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        }:
            if suffix != ".docx":
                return ""
            try:
                data = storage.read_bytes(relpath)
                with zipfile.ZipFile(io.BytesIO(data), "r") as z:
                    try:
                        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
                    except KeyError:
                        return ""
                xml = re.sub(r"</w:p>", "\n", xml)
                xml = re.sub(r"<[^>]+>", "", xml)
                return _normalize_whitespace(xml)
            except Exception:
                return ""

        if suffix in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"} or mime.startswith("image/"):
            return ""

        if suffix in {".xlsx", ".xls"} or mime in {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        }:
            return ""

        if suffix in {".zip"} or mime in {"application/zip"}:
            return ""

        return ""


class Catalog:
    def __init__(self, storage: Storage, meta: MetadataStore, extractor: Optional[ContentExtractor] = None):
        self._storage = storage
        self._meta = meta
        self._extractor = extractor or ContentExtractor()

    @property
    def storage(self) -> Storage:
        return self._storage

    @property
    def meta(self) -> MetadataStore:
        return self._meta

    def ingest_file(self, relpath: str, tags: Optional[Sequence[str]] = None, metadata: Optional[Dict[str, str]] = None) -> DocumentRef:
        p = self._storage.resolve_relpath(relpath)
        if not p.exists() or not p.is_file():
            raise NotFoundError(f"File not found: {relpath}")
        st = p.stat()
        mime = _guess_mime(p)
        sha = _sha256_file(p)
        doc = self._meta.upsert_document(relpath=relpath, mime=mime, sha256=sha, size_bytes=int(st.st_size), mtime_ns=int(st.st_mtime_ns))
        if tags is not None:
            self._meta.set_tags(doc.doc_id, tags)
        if metadata:
            for k, v in metadata.items():
                self._meta.set_metadata(doc.doc_id, str(k), str(v))
        text = self._extractor.extract_text(self._storage, relpath, mime)
        token_freq: Dict[str, int] = {}
        for tok in _tokenize(text):
            token_freq[tok] = token_freq.get(tok, 0) + 1
        self._meta.upsert_lexical_index(doc.doc_id, token_freq)
        return doc

    def ingest_tree(self, folder_relpath: str = "", include_hidden: bool = False) -> List[DocumentRef]:
        folder = self._storage.resolve_relpath(folder_relpath)
        if not folder.exists() or not folder.is_dir():
            raise NotFoundError(f"Folder not found: {folder_relpath}")
        docs: List[DocumentRef] = []
        for p in folder.rglob("*"):
            if not p.is_file():
                continue
            rel = _safe_relpath(p, self._storage.root)
            parts = Path(rel).parts
            if not include_hidden and any(part.startswith(".") for part in parts):
                continue
            docs.append(self.ingest_file(rel))
        return docs

    def set_tags(self, relpath: str, tags: Sequence[str]) -> None:
        doc = self._meta.get_document_by_relpath(relpath)
        self._meta.set_tags(doc.doc_id, tags)

    def set_metadata(self, relpath: str, key: str, value: str) -> None:
        doc = self._meta.get_document_by_relpath(relpath)
        self._meta.set_metadata(doc.doc_id, key, value)

    def get_document(self, relpath: str) -> DocumentRef:
        return self._meta.get_document_by_relpath(relpath)

    def list_documents(self) -> List[DocumentRef]:
        return self._meta.list_documents()


class View:
    def __init__(self, name: str, query: str, tags_any: Optional[Sequence[str]] = None):
        self._name = _normalize_whitespace(name)
        self._query = _normalize_whitespace(query)
        self._tags_any = [t for t in (_normalize_whitespace(x) for x in (tags_any or [])) if t]
        if not self._name:
            raise ValidationError("View name required")
        if len(self._name) > 128:
            raise ValidationError("View name too long")

    @property
    def name(self) -> str:
        return self._name

    @property
    def query(self) -> str:
        return self._query

    @property
    def tags_any(self) -> List[str]:
        return list(self._tags_any)


class SearchEngine:
    def __init__(self, catalog: Catalog):
        self._catalog = catalog

    def search(self, query: str, limit: int = 20, tags_any: Optional[Sequence[str]] = None) -> List[SearchHit]:
        q = _normalize_whitespace(query)
        if not q:
            return []
        tokens = _tokenize(q)
        scored = self._catalog.meta.lexical_search(tokens, limit=limit * 5 if limit <= 40 else limit)
        hits: List[SearchHit] = []
        tag_filter = [t for t in (_normalize_whitespace(x) for x in (tags_any or [])) if t]
        for doc_id, score in scored:
            doc = self._catalog.meta.get_document_by_id(doc_id)
            if tag_filter:
                dtags = set(self._catalog.meta.get_tags(doc_id))
                if not any(t in dtags for t in tag_filter):
                    continue
            snippet = self._make_snippet(doc.relpath, tokens)
            hits.append(SearchHit(doc_id=doc.doc_id, relpath=doc.relpath, score=float(score), snippet=snippet))
            if len(hits) >= limit:
                break
        return hits

    def _make_snippet(self, relpath: str, tokens: Sequence[str], max_len: int = 240) -> str:
        doc = self._catalog.meta.get_document_by_relpath(relpath)
        text = self._catalog._extractor.extract_text(self._catalog.storage, relpath, doc.mime)
        if not text:
            return ""
        low = text.lower()
        idx = -1
        for t in tokens:
            i = low.find(t.lower())
            if i != -1 and (idx == -1 or i < idx):
                idx = i
        if idx == -1:
            snippet = _normalize_whitespace(text[:max_len])
            return snippet[:max_len]
        start = max(0, idx - max_len // 3)
        end = min(len(text), start + max_len)
        snippet = _normalize_whitespace(text[start:end])
        return snippet[:max_len]


class Reader:
    def __init__(self, catalog: Catalog):
        self._catalog = catalog

    def read_lines(self, relpath: str, start_line: int, end_line: int) -> ReadWindow:
        doc = self._catalog.meta.get_document_by_relpath(relpath)
        text = self._catalog._extractor.extract_text(self._catalog.storage, relpath, doc.mime)
        lines = text.split("\n") if text else []
        content = _chunk_lines(lines, start_line, end_line) if lines else ""
        locator = f"lines:{start_line}-{end_line}"
        return ReadWindow(doc_id=doc.doc_id, relpath=doc.relpath, locator=locator, content=content)

    def read_chars(self, relpath: str, start: int, end: int) -> ReadWindow:
        doc = self._catalog.meta.get_document_by_relpath(relpath)
        text = self._catalog._extractor.extract_text(self._catalog.storage, relpath, doc.mime)
        content = _chunk_chars(text or "", start, end)
        locator = f"chars:{start}-{end}"
        return ReadWindow(doc_id=doc.doc_id, relpath=doc.relpath, locator=locator, content=content)

    def read_archive_member(self, relpath: str, member: str, max_bytes: int = 200_000) -> ReadWindow:
        if max_bytes <= 0 or max_bytes > 5_000_000:
            raise ValidationError("Invalid max_bytes")
        doc = self._catalog.meta.get_document_by_relpath(relpath)
        p = self._catalog.storage.resolve_relpath(relpath)
        if p.suffix.lower() != ".zip":
            raise ValidationError("Only .zip archives supported")
        data = self._catalog.storage.read_bytes(relpath)
        with zipfile.ZipFile(io.BytesIO(data), "r") as z:
            try:
                with z.open(member, "r") as f:
                    b = f.read(max_bytes + 1)
            except KeyError:
                raise NotFoundError(f"Archive member not found: {member}")
        if len(b) > max_bytes:
            b = b[:max_bytes]
        try:
            content = b.decode("utf-8", errors="replace")
        except Exception:
            content = ""
        locator = f"zip:{member}"
        return ReadWindow(doc_id=doc.doc_id, relpath=doc.relpath, locator=locator, content=content)

    def read_table_slice(self, relpath: str, start_row: int, end_row: int, start_col: int = 1, end_col: int = 50) -> ReadWindow:
        if start_row <= 0 or end_row < start_row:
            raise ValidationError("Invalid row range")
        if start_col <= 0 or end_col < start_col:
            raise ValidationError("Invalid col range")
        doc = self._catalog.meta.get_document_by_relpath(relpath)
        p = self._catalog.storage.resolve_relpath(relpath)
        suffix = p.suffix.lower()
        if suffix not in {".csv", ".tsv"}:
            raise ValidationError("Only .csv/.tsv supported for table slices")
        text = self._catalog.storage.read_text(relpath)
        delim = "," if suffix == ".csv" else "\t"
        rows = text.splitlines()
        selected = rows[start_row - 1 : end_row]
        out_rows: List[str] = []
        for r in selected:
            cols = r.split(delim)
            slice_cols = cols[start_col - 1 : end_col]
            out_rows.append(delim.join(slice_cols))
        locator = f"table:{start_row}-{end_row},cols:{start_col}-{end_col}"
        return ReadWindow(doc_id=doc.doc_id, relpath=doc.relpath, locator=locator, content="\n".join(out_rows))


class SourceQuota:
    def __init__(self, max_documents: int = 8, max_total_chars: int = 40_000):
        if max_documents <= 0 or max_documents > 100:
            raise ValidationError("Invalid max_documents")
        if max_total_chars <= 0 or max_total_chars > 2_000_000:
            raise ValidationError("Invalid max_total_chars")
        self._max_documents = max_documents
        self._max_total_chars = max_total_chars

    @property
    def max_documents(self) -> int:
        return self._max_documents

    @property
    def max_total_chars(self) -> int:
        return self._max_total_chars


class RelationMiner:
    def __init__(self, catalog: Catalog):
        self._catalog = catalog

    def mine_relations(self, doc_id: str, candidate_doc_ids: Sequence[str], max_relations: int = 10) -> List[str]:
        if max_relations <= 0 or max_relations > 100:
            raise ValidationError("Invalid max_relations")
        src = self._catalog.meta.get_document_by_id(doc_id)
        src_text = self._catalog._extractor.extract_text(self._catalog.storage, src.relpath, src.mime)
        src_tokens = set(_tokenize(src_text))
        created: List[str] = []
        for dst_id in candidate_doc_ids:
            if dst_id == doc_id:
                continue
            if len(created) >= max_relations:
                break
            dst = self._catalog.meta.get_document_by_id(dst_id)
            dst_text = self._catalog._extractor.extract_text(self._catalog.storage, dst.relpath, dst.mime)
            dst_tokens = set(_tokenize(dst_text))
            if not src_tokens or not dst_tokens:
                continue
            inter = src_tokens.intersection(dst_tokens)
            union = src_tokens.union(dst_tokens)
            score = len(inter) / max(1, len(union))
            if score <= 0.0:
                continue
            evidence = "shared_tokens:" + ",".join(sorted(list(inter))[:25])
            rel_id = self._catalog.meta.add_relation(src_doc_id=doc_id, dst_doc_id=dst_id, kind="token_overlap", score=float(min(1.0, score)), evidence=evidence)
            created.append(rel_id)
        return created


class InvestigationNotes:
    def __init__(self, meta: MetadataStore):
        self._meta = meta

    def write(self, title: str, body: str, related_doc_ids: Sequence[str]) -> str:
        return self._meta.add_journal_entry(kind="investigation", title=title, body=body, related_doc_ids=related_doc_ids)

    def list_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._meta.list_journal_entries(limit=limit)


class Agent:
    def __init__(self, catalog: Catalog, search: SearchEngine, reader: Reader, notes: InvestigationNotes):
        self._catalog = catalog
        self._search = search
        self._reader = reader
        self._notes = notes

    def answer(
        self,
        question: str,
        view: Optional[View] = None,
        quota: Optional[SourceQuota] = None,
        search_limit: int = 20,
        read_window_lines: int = 40,
    ) -> Answer:
        q = _normalize_whitespace(question)
        if not q:
            raise ValidationError("Question required")
        if search_limit <= 0 or search_limit > 200:
            raise ValidationError("Invalid search_limit")
        if read_window_lines <= 0 or read_window_lines > 500:
            raise ValidationError("Invalid read_window_lines")
        quota = quota or SourceQuota()

        tags_any = view.tags_any if view else None
        query = view.query if view and view.query else q
        hits = self._search.search(query=query, limit=search_limit, tags_any=tags_any)

        selected_hits = hits[: quota.max_documents]
        windows: List[ReadWindow] = []
        total_chars = 0
        for h in selected_hits:
            w = self._best_effort_read_window(h.relpath, q, read_window_lines)
            if not w.content:
                continue
            if total_chars + len(w.content) > quota.max_total_chars:
                remaining = quota.max_total_chars - total_chars
                if remaining <= 0:
                    break
                w = ReadWindow(doc_id=w.doc_id, relpath=w.relpath, locator=w.locator, content=w.content[:remaining])
            windows.append(w)
            total_chars += len(w.content)
            if len(windows) >= quota.max_documents:
                break

        if not windows:
            text = "No relevant sources could be read from the local knowledge base."
            ans = Answer(text=text, citations=[], created_at=_iso(_utc_now()))
            self._notes.write(title=f"Q: {q}", body=text, related_doc_ids=[])
            return ans

        citations: List[Citation] = []
        for w in windows:
            quote = _normalize_whitespace(w.content)
            if len(quote) > 600:
                quote = quote[:600].rstrip() + "…"
            citations.append(Citation(doc_id=w.doc_id, relpath=w.relpath, locator=w.locator, quote=quote))

        answer_text = self._synthesize_answer(q, windows)
        ans = Answer(text=answer_text, citations=citations, created_at=_iso(_utc_now()))

        related = [w.doc_id for w in windows]
        notes_body = self._format_notes(q, ans)
        self._notes.write(title=f"Q: {q}", body=notes_body, related_doc_ids=related)
        return ans

    def _best_effort_read_window(self, relpath: str, question: str, window_lines: int) -> ReadWindow:
        doc = self._catalog.meta.get_document_by_relpath(relpath)
        text = self._catalog._extractor.extract_text(self._catalog.storage, relpath, doc.mime)
        if not text:
            return ReadWindow(doc_id=doc.doc_id, relpath=doc.relpath, locator="unreadable", content="")
        lines = text.split("\n")
        q_tokens = _tokenize(question)
        low_lines = [ln.lower() for ln in lines]
        best_line = 1
        best_score = -1
        for i, ln in enumerate(low_lines, start=1):
            s = 0
            for t in q_tokens:
                if t and t in ln:
                    s += 1
            if s > best_score:
                best_score = s
                best_line = i
        half = max(1, window_lines // 2)
        start = max(1, best_line - half)
        end = min(len(lines), start + window_lines - 1)
        start = max(1, end - window_lines + 1)
        return self._reader.read_lines(relpath, start, end)

    def _synthesize_answer(self, question: str, windows: Sequence[ReadWindow]) -> str:
        q_tokens = set(_tokenize(question))
        scored: List[Tuple[float, ReadWindow]] = []
        for w in windows:
            t = w.content.lower()
            score = 0.0
            for tok in q_tokens:
                if tok and tok in t:
                    score += 1.0
            score += min(1.0, len(w.content) / 2000.0) * 0.2
            scored.append((score, w))
        scored.sort(key=lambda x: x[0], reverse=True)

        parts: List[str] = []
        parts.append(f"Question: {question}")
        parts.append("")
        parts.append("Findings (with sources):")
        for idx, (_, w) in enumerate(scored[: min(6, len(scored))], start=1):
            excerpt = _normalize_whitespace(w.content)
            if len(excerpt) > 500:
                excerpt = excerpt[:500].rstrip() + "…"
            parts.append(f"{idx}. {excerpt} [{w.relpath} @ {w.locator}]")
        parts.append("")
        parts.append("Answer:")
        merged = " ".join(_normalize_whitespace(w.content) for _, w in scored[: min(4, len(scored))] if w.content)
        merged = _normalize_whitespace(merged)
        if not merged:
            parts.append("Insufficient readable source text to answer.")
        else:
            parts.append(merged[:1200] + ("…" if len(merged) > 1200 else ""))
        return "\n".join(parts)

    def _format_notes(self, question: str, answer: Answer) -> str:
        lines: List[str] = []
        lines.append(f"Question: {question}")
        lines.append(f"Created: {answer.created_at}")
        lines.append("")
        lines.append("Answer:")
        lines.append(answer.text)
        lines.append("")
        lines.append("Citations:")
        for c in answer.citations:
            lines.append(f"- {c.relpath} @ {c.locator}: {c.quote}")
        return "\n".join(lines)


class Marginalia:
    def __init__(self, root_folder: Union[str, Path], db_path: Optional[Union[str, Path]] = None):
        self._storage = Storage(root_folder)
        if db_path is None:
            db_path = self._storage.root / ".marginalia" / "marginalia.sqlite3"
        self._meta = MetadataStore(db_path)
        self._catalog = Catalog(self._storage, self._meta)
        self._search = SearchEngine(self._catalog)
        self._reader = Reader(self._catalog)
        self._notes = InvestigationNotes(self._meta)
        self._miner = RelationMiner(self._catalog)
        self._agent = Agent(self._catalog, self._search, self._reader, self._notes)

    @property
    def storage(self) -> Storage:
        return self._storage

    @property
    def meta(self) -> MetadataStore:
        return self._meta

    @property
    def catalog(self) -> Catalog:
        return self._catalog

    @property
    def search(self) -> SearchEngine:
        return self._search

    @property
    def reader(self) -> Reader:
        return self._reader

    @property
    def notes(self) -> InvestigationNotes:
        return self._notes

    @property
    def miner(self) -> RelationMiner:
        return self._miner

    @property
    def agent(self) -> Agent:
        return self._agent

    def close(self) -> None:
        self._meta.close()

    def ingest(self, relpath: str, tags: Optional[Sequence[str]] = None, metadata: Optional[Dict[str, str]] = None) -> DocumentRef:
        return self._catalog.ingest_file(relpath, tags=tags, metadata=metadata)

    def ingest_all(self, folder_relpath: str = "", include_hidden: bool = False) -> List[DocumentRef]:
        return self._catalog.ingest_tree(folder_relpath=folder_relpath, include_hidden=include_hidden)

    def ask(
        self,
        question: str,
        view: Optional[View] = None,
        quota: Optional[SourceQuota] = None,
        search_limit: int = 20,
        read_window_lines: int = 40,
    ) -> Answer:
        return self._agent.answer(
            question=question,
            view=view,
            quota=quota,
            search_limit=search_limit,
            read_window_lines=read_window_lines,
        )

    def mine_relations_for(self, relpath: str, candidate_limit: int = 20, max_relations: int = 10) -> List[str]:
        if candidate_limit <= 0 or candidate_limit > 200:
            raise ValidationError("Invalid candidate_limit")
        doc = self._meta.get_document_by_relpath(relpath)
        hits = self._search.search(query=Path(relpath).stem, limit=candidate_limit)
        candidate_ids = [h.doc_id for h in hits if h.doc_id != doc.doc_id]
        return self._miner.mine_relations(doc_id=doc.doc_id, candidate_doc_ids=candidate_ids, max_relations=max_relations)