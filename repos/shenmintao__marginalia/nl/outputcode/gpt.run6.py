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


def _safe_relpath(path: Path, root: Path) -> str:
    path = path.resolve()
    root = root.resolve()
    try:
        rel = path.relative_to(root)
    except Exception:
        raise ValueError("Path must be within root")
    return str(rel).replace("\\", "/")


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _normalize_text(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return s


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    return re.findall(r"[a-z0-9]+", text)


def _guess_mime(path: Path) -> str:
    mt, _ = mimetypes.guess_type(str(path))
    return mt or "application/octet-stream"


@dataclass(frozen=True)
class SourceWindow:
    document_id: str
    locator: str
    content: str


@dataclass(frozen=True)
class Citation:
    document_id: str
    locator: str


@dataclass(frozen=True)
class SearchHit:
    document_id: str
    score: float
    snippet: str


class MarginaliaError(Exception):
    pass


class ValidationError(MarginaliaError):
    pass


class NotFoundError(MarginaliaError):
    pass


class StorageError(MarginaliaError):
    pass


class Document:
    def __init__(
        self,
        document_id: str,
        relpath: str,
        title: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        created_at: str,
        updated_at: str,
        extracted_text: Optional[str],
        metadata: Dict[str, Any],
    ) -> None:
        self._id = document_id
        self._relpath = relpath
        self._title = title
        self._mime_type = mime_type
        self._size_bytes = int(size_bytes)
        self._sha256 = sha256
        self._created_at = created_at
        self._updated_at = updated_at
        self._extracted_text = extracted_text
        self._metadata = dict(metadata)

    @property
    def id(self) -> str:
        return self._id

    @property
    def relpath(self) -> str:
        return self._relpath

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
    def created_at(self) -> str:
        return self._created_at

    @property
    def updated_at(self) -> str:
        return self._updated_at

    @property
    def extracted_text(self) -> Optional[str]:
        return self._extracted_text

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)


class JournalEntry:
    def __init__(
        self,
        entry_id: str,
        created_at: str,
        kind: str,
        payload: Dict[str, Any],
    ) -> None:
        self._id = entry_id
        self._created_at = created_at
        self._kind = kind
        self._payload = dict(payload)

    @property
    def id(self) -> str:
        return self._id

    @property
    def created_at(self) -> str:
        return self._created_at

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def payload(self) -> Dict[str, Any]:
        return dict(self._payload)


class Catalog:
    def __init__(self, name: str, query: str) -> None:
        if not name or not name.strip():
            raise ValidationError("Catalog name required")
        if not query or not query.strip():
            raise ValidationError("Catalog query required")
        self._name = name.strip()
        self._query = query.strip()

    @property
    def name(self) -> str:
        return self._name

    @property
    def query(self) -> str:
        return self._query


class View:
    def __init__(self, name: str, filter_query: str) -> None:
        if not name or not name.strip():
            raise ValidationError("View name required")
        if not filter_query or not filter_query.strip():
            raise ValidationError("View filter_query required")
        self._name = name.strip()
        self._filter_query = filter_query.strip()

    @property
    def name(self) -> str:
        return self._name

    @property
    def filter_query(self) -> str:
        return self._filter_query


class Relation:
    def __init__(
        self,
        relation_id: str,
        src_document_id: str,
        dst_document_id: str,
        kind: str,
        score: float,
        evidence: str,
        created_at: str,
    ) -> None:
        self._id = relation_id
        self._src = src_document_id
        self._dst = dst_document_id
        self._kind = kind
        self._score = float(score)
        self._evidence = evidence
        self._created_at = created_at

    @property
    def id(self) -> str:
        return self._id

    @property
    def src_document_id(self) -> str:
        return self._src

    @property
    def dst_document_id(self) -> str:
        return self._dst

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def score(self) -> float:
        return self._score

    @property
    def evidence(self) -> str:
        return self._evidence

    @property
    def created_at(self) -> str:
        return self._created_at


class SourceQuota:
    def __init__(self, max_documents: int = 8, max_windows: int = 24, max_chars: int = 60000) -> None:
        if max_documents <= 0 or max_windows <= 0 or max_chars <= 0:
            raise ValidationError("Quota limits must be positive")
        self.max_documents = int(max_documents)
        self.max_windows = int(max_windows)
        self.max_chars = int(max_chars)


class TextExtractor:
    def extract(self, path: Path) -> Optional[str]:
        raise NotImplementedError


class PlainTextExtractor(TextExtractor):
    def extract(self, path: Path) -> Optional[str]:
        try:
            data = path.read_bytes()
        except Exception:
            return None
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return _normalize_text(data.decode(enc))
            except Exception:
                continue
        return None


class MarkdownExtractor(PlainTextExtractor):
    pass


class LogExtractor(PlainTextExtractor):
    pass


class PDFExtractor(TextExtractor):
    def extract(self, path: Path) -> Optional[str]:
        return None


class DocxExtractor(TextExtractor):
    def extract(self, path: Path) -> Optional[str]:
        return None


class ImageExtractor(TextExtractor):
    def extract(self, path: Path) -> Optional[str]:
        return None


class SpreadsheetExtractor(TextExtractor):
    def extract(self, path: Path) -> Optional[str]:
        return None


class ArchiveExtractor(TextExtractor):
    def extract(self, path: Path) -> Optional[str]:
        try:
            with zipfile.ZipFile(path, "r") as zf:
                names = [n for n in zf.namelist() if not n.endswith("/")]
                parts: List[str] = []
                for n in names[:200]:
                    try:
                        info = zf.getinfo(n)
                        parts.append(f"Member: {n} ({info.file_size} bytes)")
                    except Exception:
                        parts.append(f"Member: {n}")
                return _normalize_text("\n".join(parts))
        except Exception:
            return None


class ExtractorRegistry:
    def __init__(self) -> None:
        self._by_ext: Dict[str, TextExtractor] = {}
        self._default = PlainTextExtractor()

    def register(self, extensions: Sequence[str], extractor: TextExtractor) -> None:
        for ext in extensions:
            e = ext.lower().strip()
            if not e.startswith("."):
                e = "." + e
            self._by_ext[e] = extractor

    def get(self, path: Path) -> TextExtractor:
        ext = path.suffix.lower()
        return self._by_ext.get(ext, self._default)


class LexicalIndex:
    def __init__(self) -> None:
        self._doc_tf: Dict[str, Dict[str, int]] = {}
        self._df: Dict[str, int] = {}
        self._doc_len: Dict[str, int] = {}
        self._doc_count = 0

    def remove(self, document_id: str) -> None:
        tf = self._doc_tf.pop(document_id, None)
        if tf is None:
            return
        self._doc_count = max(0, self._doc_count - 1)
        self._doc_len.pop(document_id, None)
        for term in tf.keys():
            self._df[term] = max(0, self._df.get(term, 0) - 1)
            if self._df[term] == 0:
                self._df.pop(term, None)

    def upsert(self, document_id: str, text: str) -> None:
        self.remove(document_id)
        tokens = _tokenize(text)
        tf: Dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        self._doc_tf[document_id] = tf
        self._doc_len[document_id] = len(tokens)
        self._doc_count += 1
        for term in tf.keys():
            self._df[term] = self._df.get(term, 0) + 1

    def search(self, query: str, top_k: int = 20) -> List[Tuple[str, float]]:
        q_tokens = _tokenize(query)
        if not q_tokens or self._doc_count == 0:
            return []
        q_tf: Dict[str, int] = {}
        for t in q_tokens:
            q_tf[t] = q_tf.get(t, 0) + 1

        avgdl = (sum(self._doc_len.values()) / max(1, len(self._doc_len))) if self._doc_len else 0.0
        k1 = 1.2
        b = 0.75

        scores: Dict[str, float] = {}
        for term, qf in q_tf.items():
            df = self._df.get(term, 0)
            if df == 0:
                continue
            idf = math.log(1 + (self._doc_count - df + 0.5) / (df + 0.5))
            for doc_id, tf in self._doc_tf.items():
                f = tf.get(term, 0)
                if f == 0:
                    continue
                dl = self._doc_len.get(doc_id, 0)
                denom = f + k1 * (1 - b + b * (dl / (avgdl or 1.0)))
                score = idf * (f * (k1 + 1)) / (denom or 1.0)
                scores[doc_id] = scores.get(doc_id, 0.0) + score

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[: max(1, int(top_k))]


class MetadataStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                relpath TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                extracted_text TEXT,
                metadata_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tags (
                name TEXT PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS document_tags (
                document_id TEXT NOT NULL,
                tag_name TEXT NOT NULL,
                PRIMARY KEY (document_id, tag_name),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_name) REFERENCES tags(name) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS catalogs (
                name TEXT PRIMARY KEY,
                query TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS views (
                name TEXT PRIMARY KEY,
                filter_query TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS journal (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS relations (
                id TEXT PRIMARY KEY,
                src_document_id TEXT NOT NULL,
                dst_document_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                score REAL NOT NULL,
                evidence TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (src_document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (dst_document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_documents_sha256 ON documents(sha256);
            CREATE INDEX IF NOT EXISTS idx_documents_title ON documents(title);
            CREATE INDEX IF NOT EXISTS idx_document_tags_tag ON document_tags(tag_name);
            CREATE INDEX IF NOT EXISTS idx_relations_src ON relations(src_document_id);
            CREATE INDEX IF NOT EXISTS idx_relations_dst ON relations(dst_document_id);
            """
        )
        self._conn.commit()

    def upsert_document(self, doc: Document) -> None:
        self._conn.execute(
            """
            INSERT INTO documents (id, relpath, title, mime_type, size_bytes, sha256, created_at, updated_at, extracted_text, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                relpath=excluded.relpath,
                title=excluded.title,
                mime_type=excluded.mime_type,
                size_bytes=excluded.size_bytes,
                sha256=excluded.sha256,
                updated_at=excluded.updated_at,
                extracted_text=excluded.extracted_text,
                metadata_json=excluded.metadata_json
            """,
            (
                doc.id,
                doc.relpath,
                doc.title,
                doc.mime_type,
                doc.size_bytes,
                doc.sha256,
                doc.created_at,
                doc.updated_at,
                doc.extracted_text,
                json.dumps(doc.metadata, ensure_ascii=False),
            ),
        )
        self._conn.commit()

    def get_document(self, document_id: str) -> Document:
        cur = self._conn.execute(
            "SELECT id, relpath, title, mime_type, size_bytes, sha256, created_at, updated_at, extracted_text, metadata_json FROM documents WHERE id=?",
            (document_id,),
        )
        row = cur.fetchone()
        if not row:
            raise NotFoundError("Document not found")
        return Document(
            document_id=row[0],
            relpath=row[1],
            title=row[2],
            mime_type=row[3],
            size_bytes=row[4],
            sha256=row[5],
            created_at=row[6],
            updated_at=row[7],
            extracted_text=row[8],
            metadata=json.loads(row[9]) if row[9] else {},
        )

    def get_document_by_relpath(self, relpath: str) -> Optional[Document]:
        cur = self._conn.execute(
            "SELECT id, relpath, title, mime_type, size_bytes, sha256, created_at, updated_at, extracted_text, metadata_json FROM documents WHERE relpath=?",
            (relpath,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return Document(
            document_id=row[0],
            relpath=row[1],
            title=row[2],
            mime_type=row[3],
            size_bytes=row[4],
            sha256=row[5],
            created_at=row[6],
            updated_at=row[7],
            extracted_text=row[8],
            metadata=json.loads(row[9]) if row[9] else {},
        )

    def list_documents(self) -> List[Document]:
        cur = self._conn.execute(
            "SELECT id, relpath, title, mime_type, size_bytes, sha256, created_at, updated_at, extracted_text, metadata_json FROM documents ORDER BY relpath"
        )
        docs: List[Document] = []
        for row in cur.fetchall():
            docs.append(
                Document(
                    document_id=row[0],
                    relpath=row[1],
                    title=row[2],
                    mime_type=row[3],
                    size_bytes=row[4],
                    sha256=row[5],
                    created_at=row[6],
                    updated_at=row[7],
                    extracted_text=row[8],
                    metadata=json.loads(row[9]) if row[9] else {},
                )
            )
        return docs

    def delete_document(self, document_id: str) -> None:
        self._conn.execute("DELETE FROM documents WHERE id=?", (document_id,))
        self._conn.commit()

    def add_tag(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise ValidationError("Tag name required")
        self._conn.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (name,))
        self._conn.commit()

    def tag_document(self, document_id: str, tag_name: str) -> None:
        tag_name = tag_name.strip()
        if not tag_name:
            raise ValidationError("Tag name required")
        self.add_tag(tag_name)
        self._conn.execute(
            "INSERT OR IGNORE INTO document_tags(document_id, tag_name) VALUES (?, ?)",
            (document_id, tag_name),
        )
        self._conn.commit()

    def untag_document(self, document_id: str, tag_name: str) -> None:
        self._conn.execute(
            "DELETE FROM document_tags WHERE document_id=? AND tag_name=?",
            (document_id, tag_name),
        )
        self._conn.commit()

    def list_tags_for_document(self, document_id: str) -> List[str]:
        cur = self._conn.execute(
            "SELECT tag_name FROM document_tags WHERE document_id=? ORDER BY tag_name",
            (document_id,),
        )
        return [r[0] for r in cur.fetchall()]

    def list_documents_for_tag(self, tag_name: str) -> List[str]:
        cur = self._conn.execute(
            "SELECT document_id FROM document_tags WHERE tag_name=? ORDER BY document_id",
            (tag_name,),
        )
        return [r[0] for r in cur.fetchall()]

    def upsert_catalog(self, catalog: Catalog) -> None:
        self._conn.execute(
            """
            INSERT INTO catalogs(name, query) VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET query=excluded.query
            """,
            (catalog.name, catalog.query),
        )
        self._conn.commit()

    def get_catalog(self, name: str) -> Catalog:
        cur = self._conn.execute("SELECT name, query FROM catalogs WHERE name=?", (name,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("Catalog not found")
        return Catalog(name=row[0], query=row[1])

    def list_catalogs(self) -> List[Catalog]:
        cur = self._conn.execute("SELECT name, query FROM catalogs ORDER BY name")
        return [Catalog(name=r[0], query=r[1]) for r in cur.fetchall()]

    def delete_catalog(self, name: str) -> None:
        self._conn.execute("DELETE FROM catalogs WHERE name=?", (name,))
        self._conn.commit()

    def upsert_view(self, view: View) -> None:
        self._conn.execute(
            """
            INSERT INTO views(name, filter_query) VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET filter_query=excluded.filter_query
            """,
            (view.name, view.filter_query),
        )
        self._conn.commit()

    def get_view(self, name: str) -> View:
        cur = self._conn.execute("SELECT name, filter_query FROM views WHERE name=?", (name,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("View not found")
        return View(name=row[0], filter_query=row[1])

    def list_views(self) -> List[View]:
        cur = self._conn.execute("SELECT name, filter_query FROM views ORDER BY name")
        return [View(name=r[0], filter_query=r[1]) for r in cur.fetchall()]

    def delete_view(self, name: str) -> None:
        self._conn.execute("DELETE FROM views WHERE name=?", (name,))
        self._conn.commit()

    def append_journal(self, entry: JournalEntry) -> None:
        self._conn.execute(
            "INSERT INTO journal(id, created_at, kind, payload_json) VALUES (?, ?, ?, ?)",
            (entry.id, entry.created_at, entry.kind, json.dumps(entry.payload, ensure_ascii=False)),
        )
        self._conn.commit()

    def list_journal(self, limit: int = 200) -> List[JournalEntry]:
        limit = max(1, int(limit))
        cur = self._conn.execute(
            "SELECT id, created_at, kind, payload_json FROM journal ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        out: List[JournalEntry] = []
        for r in cur.fetchall():
            out.append(JournalEntry(entry_id=r[0], created_at=r[1], kind=r[2], payload=json.loads(r[3]) if r[3] else {}))
        return out

    def add_relation(self, relation: Relation) -> None:
        self._conn.execute(
            """
            INSERT INTO relations(id, src_document_id, dst_document_id, kind, score, evidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                relation.id,
                relation.src_document_id,
                relation.dst_document_id,
                relation.kind,
                relation.score,
                relation.evidence,
                relation.created_at,
            ),
        )
        self._conn.commit()

    def list_relations_for_document(self, document_id: str, limit: int = 200) -> List[Relation]:
        limit = max(1, int(limit))
        cur = self._conn.execute(
            """
            SELECT id, src_document_id, dst_document_id, kind, score, evidence, created_at
            FROM relations
            WHERE src_document_id=? OR dst_document_id=?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (document_id, document_id, limit),
        )
        out: List[Relation] = []
        for r in cur.fetchall():
            out.append(
                Relation(
                    relation_id=r[0],
                    src_document_id=r[1],
                    dst_document_id=r[2],
                    kind=r[3],
                    score=r[4],
                    evidence=r[5],
                    created_at=r[6],
                )
            )
        return out


class QueryParser:
    def parse(self, query: str) -> Dict[str, Any]:
        query = (query or "").strip()
        if not query:
            raise ValidationError("Query required")
        tokens = query.split()
        terms: List[str] = []
        tags: List[str] = []
        path_prefix: Optional[str] = None
        title_terms: List[str] = []
        for tok in tokens:
            if tok.startswith("tag:") and len(tok) > 4:
                tags.append(tok[4:])
            elif tok.startswith("path:") and len(tok) > 5:
                path_prefix = tok[5:].strip().lstrip("/")
            elif tok.startswith("title:") and len(tok) > 6:
                title_terms.append(tok[6:])
            else:
                terms.append(tok)
        return {
            "raw": query,
            "terms": " ".join(terms).strip(),
            "tags": [t for t in tags if t],
            "path_prefix": path_prefix if path_prefix else None,
            "title_terms": " ".join(title_terms).strip(),
        }


class KnowledgeBase:
    def __init__(self, root_folder: Union[str, Path], db_path: Optional[Union[str, Path]] = None) -> None:
        self._root = Path(root_folder).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        if db_path is None:
            db_path = self._root / ".marginalia" / "marginalia.sqlite3"
        self._db_path = Path(db_path).expanduser().resolve()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._store = MetadataStore(self._db_path)
        self._extractors = ExtractorRegistry()
        self._register_default_extractors()
        self._index = LexicalIndex()
        self._parser = QueryParser()
        self._rebuild_index_from_store()

    @property
    def root(self) -> Path:
        return self._root

    def close(self) -> None:
        self._store.close()

    def _register_default_extractors(self) -> None:
        self._extractors.register([".txt"], PlainTextExtractor())
        self._extractors.register([".md", ".markdown"], MarkdownExtractor())
        self._extractors.register([".log"], LogExtractor())
        self._extractors.register([".pdf"], PDFExtractor())
        self._extractors.register([".docx"], DocxExtractor())
        self._extractors.register([".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"], ImageExtractor())
        self._extractors.register([".csv", ".tsv", ".xlsx", ".xls", ".ods"], SpreadsheetExtractor())
        self._extractors.register([".zip"], ArchiveExtractor())

    def _rebuild_index_from_store(self) -> None:
        for doc in self._store.list_documents():
            if doc.extracted_text:
                self._index.upsert(doc.id, doc.extracted_text)

    def _make_title(self, path: Path) -> str:
        return path.stem

    def ingest_file(self, path: Union[str, Path]) -> Document:
        p = Path(path).expanduser().resolve()
        if not p.exists() or not p.is_file():
            raise NotFoundError("File not found")
        rel = _safe_relpath(p, self._root)
        mime = _guess_mime(p)
        size = p.stat().st_size
        sha = _sha256_file(p)
        now = _iso(_utc_now())

        existing = self._store.get_document_by_relpath(rel)
        if existing is None:
            doc_id = str(uuid.uuid4())
            created_at = now
        else:
            doc_id = existing.id
            created_at = existing.created_at

        extractor = self._extractors.get(p)
        extracted = extractor.extract(p)
        if extracted is not None:
            extracted = _normalize_text(extracted)

        metadata: Dict[str, Any] = {
            "filename": p.name,
            "extension": p.suffix.lower(),
        }

        doc = Document(
            document_id=doc_id,
            relpath=rel,
            title=self._make_title(p),
            mime_type=mime,
            size_bytes=size,
            sha256=sha,
            created_at=created_at,
            updated_at=now,
            extracted_text=extracted,
            metadata=metadata,
        )
        self._store.upsert_document(doc)
        if extracted:
            self._index.upsert(doc.id, extracted)
        else:
            self._index.remove(doc.id)

        self._store.append_journal(
            JournalEntry(
                entry_id=str(uuid.uuid4()),
                created_at=now,
                kind="ingest",
                payload={"document_id": doc.id, "relpath": doc.relpath, "sha256": doc.sha256},
            )
        )
        return doc

    def ingest_folder(self, folder: Union[str, Path]) -> List[Document]:
        f = Path(folder).expanduser().resolve()
        if not f.exists() or not f.is_dir():
            raise NotFoundError("Folder not found")
        _safe_relpath(f, self._root)
        docs: List[Document] = []
        for p in sorted(f.rglob("*")):
            if p.is_file():
                try:
                    docs.append(self.ingest_file(p))
                except MarginaliaError:
                    continue
        return docs

    def list_documents(self) -> List[Document]:
        return self._store.list_documents()

    def get_document(self, document_id: str) -> Document:
        return self._store.get_document(document_id)

    def add_tag(self, name: str) -> None:
        self._store.add_tag(name)

    def tag_document(self, document_id: str, tag_name: str) -> None:
        self._store.get_document(document_id)
        self._store.tag_document(document_id, tag_name)
        self._store.append_journal(
            JournalEntry(
                entry_id=str(uuid.uuid4()),
                created_at=_iso(_utc_now()),
                kind="tag",
                payload={"document_id": document_id, "tag": tag_name},
            )
        )

    def untag_document(self, document_id: str, tag_name: str) -> None:
        self._store.get_document(document_id)
        self._store.untag_document(document_id, tag_name)
        self._store.append_journal(
            JournalEntry(
                entry_id=str(uuid.uuid4()),
                created_at=_iso(_utc_now()),
                kind="untag",
                payload={"document_id": document_id, "tag": tag_name},
            )
        )

    def list_tags_for_document(self, document_id: str) -> List[str]:
        self._store.get_document(document_id)
        return self._store.list_tags_for_document(document_id)

    def create_catalog(self, name: str, query: str) -> None:
        self._store.upsert_catalog(Catalog(name=name, query=query))
        self._store.append_journal(
            JournalEntry(
                entry_id=str(uuid.uuid4()),
                created_at=_iso(_utc_now()),
                kind="catalog_upsert",
                payload={"name": name, "query": query},
            )
        )

    def list_catalogs(self) -> List[Catalog]:
        return self._store.list_catalogs()

    def create_view(self, name: str, filter_query: str) -> None:
        self._store.upsert_view(View(name=name, filter_query=filter_query))
        self._store.append_journal(
            JournalEntry(
                entry_id=str(uuid.uuid4()),
                created_at=_iso(_utc_now()),
                kind="view_upsert",
                payload={"name": name, "filter_query": filter_query},
            )
        )

    def list_views(self) -> List[View]:
        return self._store.list_views()

    def list_journal(self, limit: int = 200) -> List[JournalEntry]:
        return self._store.list_journal(limit=limit)

    def search(self, query: str, top_k: int = 20) -> List[SearchHit]:
        parsed = self._parser.parse(query)
        terms = parsed["terms"]
        ranked = self._index.search(terms if terms else parsed["raw"], top_k=max(1, int(top_k) * 3))

        candidates: List[Tuple[str, float]] = ranked
        if parsed["tags"] or parsed["path_prefix"] or parsed["title_terms"]:
            filtered: List[Tuple[str, float]] = []
            for doc_id, score in candidates:
                try:
                    doc = self._store.get_document(doc_id)
                except NotFoundError:
                    continue
                if parsed["path_prefix"] and not doc.relpath.startswith(parsed["path_prefix"].rstrip("/") + "/") and doc.relpath != parsed["path_prefix"].rstrip("/"):
                    continue
                if parsed["title_terms"]:
                    tt = parsed["title_terms"].lower()
                    if tt not in doc.title.lower():
                        continue
                if parsed["tags"]:
                    doc_tags = set(self._store.list_tags_for_document(doc_id))
                    if not set(parsed["tags"]).issubset(doc_tags):
                        continue
                filtered.append((doc_id, score))
            candidates = filtered

        hits: List[SearchHit] = []
        for doc_id, score in candidates[: max(1, int(top_k))]:
            doc = self._store.get_document(doc_id)
            snippet = ""
            if doc.extracted_text:
                q = parsed["terms"] or parsed["raw"]
                snippet = self._make_snippet(doc.extracted_text, q)
            hits.append(SearchHit(document_id=doc_id, score=float(score), snippet=snippet))
        self._store.append_journal(
            JournalEntry(
                entry_id=str(uuid.uuid4()),
                created_at=_iso(_utc_now()),
                kind="search",
                payload={"query": query, "top_k": top_k, "returned": len(hits)},
            )
        )
        return hits

    def _make_snippet(self, text: str, query: str, max_len: int = 240) -> str:
        text = _normalize_text(text)
        q_tokens = _tokenize(query)
        if not q_tokens:
            return text[:max_len]
        lower = text.lower()
        best_pos = None
        for t in q_tokens[:6]:
            pos = lower.find(t)
            if pos != -1:
                best_pos = pos if best_pos is None else min(best_pos, pos)
        if best_pos is None:
            return text[:max_len]
        start = max(0, best_pos - max_len // 3)
        end = min(len(text), start + max_len)
        snippet = text[start:end]
        snippet = snippet.strip()
        return snippet

    def read_windows(
        self,
        document_id: str,
        *,
        mode: str = "sections",
        max_windows: int = 6,
        max_chars_per_window: int = 2500,
        query: Optional[str] = None,
    ) -> List[SourceWindow]:
        doc = self._store.get_document(document_id)
        if not doc.extracted_text:
            return []
        text = _normalize_text(doc.extracted_text)
        max_windows = max(1, int(max_windows))
        max_chars_per_window = max(200, int(max_chars_per_window))

        windows: List[SourceWindow] = []
        if mode == "lines":
            lines = text.split("\n")
            if query:
                q_tokens = set(_tokenize(query))
                scored: List[Tuple[int, float]] = []
                for i, ln in enumerate(lines):
                    toks = set(_tokenize(ln))
                    overlap = len(q_tokens.intersection(toks))
                    if overlap > 0:
                        scored.append((i, float(overlap)))
                scored.sort(key=lambda x: x[1], reverse=True)
                idxs = [i for i, _ in scored[: max_windows]]
                idxs = sorted(set(idxs))
            else:
                idxs = list(range(min(max_windows, len(lines))))
            for i in idxs:
                content = lines[i][:max_chars_per_window]
                windows.append(SourceWindow(document_id=document_id, locator=f"line:{i+1}", content=content))
        elif mode == "sections":
            parts = re.split(r"\n{2,}", text)
            parts = [p.strip() for p in parts if p.strip()]
            if not parts:
                return []
            if query:
                q_tokens = set(_tokenize(query))
                scored2: List[Tuple[int, float]] = []
                for i, p in enumerate(parts):
                    toks = set(_tokenize(p))
                    overlap = len(q_tokens.intersection(toks))
                    if overlap > 0:
                        scored2.append((i, float(overlap)))
                scored2.sort(key=lambda x: x[1], reverse=True)
                idxs2 = [i for i, _ in scored2[: max_windows]]
                if not idxs2:
                    idxs2 = list(range(min(max_windows, len(parts))))
            else:
                idxs2 = list(range(min(max_windows, len(parts))))
            for i in idxs2:
                content = parts[i][:max_chars_per_window]
                windows.append(SourceWindow(document_id=document_id, locator=f"section:{i+1}", content=content))
        else:
            raise ValidationError("Unsupported read mode")

        self._store.append_journal(
            JournalEntry(
                entry_id=str(uuid.uuid4()),
                created_at=_iso(_utc_now()),
                kind="read_windows",
                payload={
                    "document_id": document_id,
                    "mode": mode,
                    "max_windows": max_windows,
                    "max_chars_per_window": max_chars_per_window,
                    "returned": len(windows),
                },
            )
        )
        return windows

    def read_archive_member(self, document_id: str, member_name: str, max_bytes: int = 200000) -> SourceWindow:
        doc = self._store.get_document(document_id)
        abs_path = (self._root / doc.relpath).resolve()
        if not abs_path.exists():
            raise NotFoundError("Underlying file missing")
        if abs_path.suffix.lower() != ".zip":
            raise ValidationError("Document is not a zip archive")
        max_bytes = max(1, int(max_bytes))
        try:
            with zipfile.ZipFile(abs_path, "r") as zf:
                with zf.open(member_name, "r") as f:
                    data = f.read(max_bytes + 1)
        except KeyError:
            raise NotFoundError("Archive member not found")
        except Exception as e:
            raise StorageError(str(e))
        if len(data) > max_bytes:
            data = data[:max_bytes]
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            text = repr(data)
        text = _normalize_text(text)
        win = SourceWindow(document_id=document_id, locator=f"zip:{member_name}", content=text)
        self._store.append_journal(
            JournalEntry(
                entry_id=str(uuid.uuid4()),
                created_at=_iso(_utc_now()),
                kind="read_archive_member",
                payload={"document_id": document_id, "member_name": member_name, "max_bytes": max_bytes},
            )
        )
        return win

    def mine_relations(self, document_id: str, limit: int = 10) -> List[Relation]:
        doc = self._store.get_document(document_id)
        if not doc.extracted_text:
            return []
        limit = max(1, int(limit))
        hits = self.search(doc.title, top_k=limit * 3)
        rels: List[Relation] = []
        for h in hits:
            if h.document_id == document_id:
                continue
            try:
                other = self._store.get_document(h.document_id)
            except NotFoundError:
                continue
            evidence = (h.snippet or "").strip()
            rel = Relation(
                relation_id=str(uuid.uuid4()),
                src_document_id=document_id,
                dst_document_id=other.id,
                kind="lexical_related",
                score=float(h.score),
                evidence=evidence[:500],
                created_at=_iso(_utc_now()),
            )
            self._store.add_relation(rel)
            rels.append(rel)
            if len(rels) >= limit:
                break
        self._store.append_journal(
            JournalEntry(
                entry_id=str(uuid.uuid4()),
                created_at=_iso(_utc_now()),
                kind="mine_relations",
                payload={"document_id": document_id, "created": len(rels)},
            )
        )
        return rels


class LLMClient:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class StubLLMClient(LLMClient):
    def generate(self, prompt: str) -> str:
        return prompt


class ResearchAgent:
    def __init__(self, kb: KnowledgeBase, llm: Optional[LLMClient] = None) -> None:
        self._kb = kb
        self._llm = llm or StubLLMClient()

    def answer(
        self,
        question: str,
        *,
        top_k: int = 8,
        quota: Optional[SourceQuota] = None,
        read_mode: str = "sections",
        windows_per_doc: int = 3,
        max_chars_per_window: int = 2000,
    ) -> Dict[str, Any]:
        question = (question or "").strip()
        if not question:
            raise ValidationError("Question required")
        quota = quota or SourceQuota()

        hits = self._kb.search(question, top_k=top_k)
        doc_ids = [h.document_id for h in hits][: quota.max_documents]

        windows: List[SourceWindow] = []
        total_chars = 0
        for doc_id in doc_ids:
            if len(windows) >= quota.max_windows:
                break
            remaining_windows = quota.max_windows - len(windows)
            per_doc = min(max(1, int(windows_per_doc)), remaining_windows)
            ws = self._kb.read_windows(
                doc_id,
                mode=read_mode,
                max_windows=per_doc,
                max_chars_per_window=max_chars_per_window,
                query=question,
            )
            for w in ws:
                if len(windows) >= quota.max_windows:
                    break
                if total_chars + len(w.content) > quota.max_chars:
                    continue
                windows.append(w)
                total_chars += len(w.content)

        citations: List[Citation] = [Citation(document_id=w.document_id, locator=w.locator) for w in windows]

        prompt = self._build_prompt(question, windows)
        response_text = self._llm.generate(prompt)
        answer_text = self._format_answer_with_citations(response_text, citations)

        note_id = self._write_investigation_note(question, answer_text, citations, windows)

        return {
            "question": question,
            "answer": answer_text,
            "citations": [c.__dict__ for c in citations],
            "note_document_id": note_id,
            "sources_read": [{"document_id": w.document_id, "locator": w.locator, "chars": len(w.content)} for w in windows],
        }

    def _build_prompt(self, question: str, windows: Sequence[SourceWindow]) -> str:
        parts: List[str] = []
        parts.append("You are a local-first research agent. Use only the provided sources.")
        parts.append(f"Question: {question}")
        parts.append("Sources:")
        for i, w in enumerate(windows, start=1):
            parts.append(f"[{i}] document_id={w.document_id} locator={w.locator}\n{w.content}")
        parts.append("Write an answer grounded in the sources.")
        return "\n\n".join(parts)

    def _format_answer_with_citations(self, model_text: str, citations: Sequence[Citation]) -> str:
        model_text = (model_text or "").strip()
        if not citations:
            return model_text
        uniq: List[Citation] = []
        seen = set()
        for c in citations:
            key = (c.document_id, c.locator)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(c)
        cite_lines = ["Citations:"]
        for c in uniq:
            cite_lines.append(f"- {c.document_id} @ {c.locator}")
        return model_text + "\n\n" + "\n".join(cite_lines)

    def _write_investigation_note(
        self,
        question: str,
        answer_text: str,
        citations: Sequence[Citation],
        windows: Sequence[SourceWindow],
    ) -> str:
        notes_dir = self._kb.root / "_marginalia_notes"
        notes_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        note_name = f"investigation_{ts}_{uuid.uuid4().hex[:8]}.md"
        note_path = notes_dir / note_name

        payload = {
            "created_at": _iso(_utc_now()),
            "question": question,
            "citations": [c.__dict__ for c in citations],
            "sources_read": [{"document_id": w.document_id, "locator": w.locator} for w in windows],
        }
        body = []
        body.append(f"# Investigation Note\n")
        body.append(f"Created: {payload['created_at']}\n")
        body.append(f"## Question\n{question}\n")
        body.append(f"## Answer\n{answer_text}\n")
        body.append("## Citations")
        for c in citations:
            body.append(f"- {c.document_id} @ {c.locator}")
        body.append("\n## Metadata\n")
        body.append("```json")
        body.append(json.dumps(payload, ensure_ascii=False, indent=2))
        body.append("```")
        note_path.write_text(_normalize_text("\n".join(body)), encoding="utf-8")

        doc = self._kb.ingest_file(note_path)
        self._kb._store.append_journal(
            JournalEntry(
                entry_id=str(uuid.uuid4()),
                created_at=_iso(_utc_now()),
                kind="investigation_note",
                payload={"note_document_id": doc.id, "relpath": doc.relpath},
            )
        )
        return doc.id


__all__ = [
    "KnowledgeBase",
    "ResearchAgent",
    "LLMClient",
    "StubLLMClient",
    "Document",
    "JournalEntry",
    "Catalog",
    "View",
    "Relation",
    "SourceWindow",
    "Citation",
    "SearchHit",
    "SourceQuota",
    "MarginaliaError",
    "ValidationError",
    "NotFoundError",
    "StorageError",
]