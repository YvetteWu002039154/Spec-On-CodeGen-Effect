from __future__ import annotations

import abc
import dataclasses
import datetime as _dt
import hashlib
import io
import json
import os
import re
import sqlite3
import threading
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


class AgentError(MarginaliaError):
    pass


def _utc_now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _safe_relpath(path: Path, root: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except Exception as e:
        raise ValidationError(f"Path {path} is not within root {root}") from e
    return str(rel).replace("\\", "/")


def _normalize_tag(tag: str) -> str:
    t = tag.strip()
    if not t:
        raise ValidationError("Tag cannot be empty")
    if len(t) > 128:
        raise ValidationError("Tag too long")
    return t


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9_]+", text.lower())


@dataclass(frozen=True)
class DocumentRef:
    doc_id: int
    rel_path: str


@dataclass(frozen=True)
class CatalogRef:
    catalog_id: int
    name: str


@dataclass(frozen=True)
class ViewRef:
    view_id: int
    name: str


@dataclass(frozen=True)
class JournalEntryRef:
    entry_id: int


@dataclass(frozen=True)
class SearchCandidate:
    doc_id: int
    rel_path: str
    score: float
    reason: str


@dataclass(frozen=True)
class ReadWindow:
    doc_id: int
    rel_path: str
    window_type: str  # "lines" | "pages" | "section" | "archive_member" | "table_slice"
    locator: str
    content: str


@dataclass(frozen=True)
class Citation:
    doc_id: int
    rel_path: str
    window_type: str
    locator: str


@dataclass(frozen=True)
class Answer:
    text: str
    citations: List[Citation]
    report: Optional[str] = None


class Storage:
    def __init__(self, db_path: Union[str, Path]) -> None:
        self._db_path = str(db_path)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._init_schema()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rel_path TEXT NOT NULL UNIQUE,
                abs_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                mtime_ns INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS document_text (
                doc_id INTEGER PRIMARY KEY,
                text TEXT NOT NULL,
                extracted_at TEXT NOT NULL,
                FOREIGN KEY(doc_id) REFERENCES documents(id) ON DELETE CASCADE
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
                doc_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY(doc_id, tag_id),
                FOREIGN KEY(doc_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS catalogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT ''
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_members (
                catalog_id INTEGER NOT NULL,
                doc_id INTEGER NOT NULL,
                PRIMARY KEY(catalog_id, doc_id),
                FOREIGN KEY(catalog_id) REFERENCES catalogs(id) ON DELETE CASCADE,
                FOREIGN KEY(doc_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                doc_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY(doc_id, key),
                FOREIGN KEY(doc_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                src_doc_id INTEGER NOT NULL,
                dst_doc_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(src_doc_id, dst_doc_id, relation_type),
                FOREIGN KEY(src_doc_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY(dst_doc_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS journals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                related_doc_ids TEXT NOT NULL DEFAULT '[]'
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                query_json TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS investigations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                question TEXT NOT NULL,
                answer_text TEXT NOT NULL,
                citations_json TEXT NOT NULL,
                notes TEXT NOT NULL
            )
            """
        )

        self._conn.commit()

    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def query(self, sql: str, params: Sequence[Any] = ()) -> List[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.fetchall()

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> Optional[sqlite3.Row]:
        rows = self.query(sql, params)
        return rows[0] if rows else None


class Extractor(abc.ABC):
    @abc.abstractmethod
    def can_handle(self, path: Path) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def extract_text(self, path: Path) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def file_type(self) -> str:
        raise NotImplementedError


class PlainTextExtractor(Extractor):
    def __init__(self, encoding: str = "utf-8") -> None:
        self._encoding = encoding

    @property
    def file_type(self) -> str:
        return "text"

    def can_handle(self, path: Path) -> bool:
        ext = path.suffix.lower()
        return ext in {".txt", ".md", ".markdown", ".log", ".csv", ".tsv", ".json", ".yaml", ".yml"}

    def extract_text(self, path: Path) -> str:
        try:
            data = path.read_bytes()
            try:
                return data.decode(self._encoding)
            except UnicodeDecodeError:
                return data.decode("utf-8", errors="replace")
        except Exception as e:
            raise IngestError(f"Failed to read text file: {path}") from e


class PDFExtractor(Extractor):
    @property
    def file_type(self) -> str:
        return "pdf"

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".pdf"

    def extract_text(self, path: Path) -> str:
        try:
            import PyPDF2  # type: ignore
        except Exception as e:
            raise IngestError("PDF support requires PyPDF2") from e
        try:
            reader = PyPDF2.PdfReader(str(path))
            parts: List[str] = []
            for i, page in enumerate(reader.pages):
                try:
                    txt = page.extract_text() or ""
                except Exception:
                    txt = ""
                parts.append(f"[page {i+1}]\n{txt}".rstrip())
            return "\n\n".join(parts).strip()
        except Exception as e:
            raise IngestError(f"Failed to extract PDF text: {path}") from e


class DOCXExtractor(Extractor):
    @property
    def file_type(self) -> str:
        return "docx"

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".docx"

    def extract_text(self, path: Path) -> str:
        try:
            import docx  # type: ignore
        except Exception as e:
            raise IngestError("DOCX support requires python-docx") from e
        try:
            d = docx.Document(str(path))
            paras = [p.text for p in d.paragraphs if p.text is not None]
            return "\n".join(paras).strip()
        except Exception as e:
            raise IngestError(f"Failed to extract DOCX text: {path}") from e


class ImageExtractor(Extractor):
    @property
    def file_type(self) -> str:
        return "image"

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp"}

    def extract_text(self, path: Path) -> str:
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore
        except Exception as e:
            raise IngestError("Image OCR support requires pillow and pytesseract") from e
        try:
            img = Image.open(str(path))
            txt = pytesseract.image_to_string(img)
            return txt.strip()
        except Exception as e:
            raise IngestError(f"Failed to OCR image: {path}") from e


class SpreadsheetExtractor(Extractor):
    @property
    def file_type(self) -> str:
        return "spreadsheet"

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in {".xlsx", ".xlsm", ".xls", ".ods"}

    def extract_text(self, path: Path) -> str:
        try:
            import pandas as pd  # type: ignore
        except Exception as e:
            raise IngestError("Spreadsheet support requires pandas") from e
        try:
            ext = path.suffix.lower()
            if ext in {".xlsx", ".xlsm", ".xls"}:
                xls = pd.ExcelFile(str(path))
                parts: List[str] = []
                for sheet in xls.sheet_names:
                    df = xls.parse(sheet)
                    parts.append(f"[sheet {sheet}]\n{df.to_csv(index=False)}".rstrip())
                return "\n\n".join(parts).strip()
            if ext == ".ods":
                df = pd.read_excel(str(path), engine="odf")
                return df.to_csv(index=False).strip()
            raise IngestError(f"Unsupported spreadsheet type: {ext}")
        except Exception as e:
            raise IngestError(f"Failed to extract spreadsheet: {path}") from e


class ArchiveExtractor(Extractor):
    @property
    def file_type(self) -> str:
        return "archive"

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in {".zip"}

    def extract_text(self, path: Path) -> str:
        try:
            with zipfile.ZipFile(str(path), "r") as zf:
                members = zf.namelist()
                parts: List[str] = []
                for name in members:
                    if name.endswith("/"):
                        continue
                    try:
                        data = zf.read(name)
                    except Exception:
                        continue
                    if len(data) > 5_000_000:
                        continue
                    text = None
                    try:
                        text = data.decode("utf-8")
                    except Exception:
                        try:
                            text = data.decode("utf-8", errors="replace")
                        except Exception:
                            text = None
                    if text is None:
                        continue
                    parts.append(f"[member {name}]\n{text}".rstrip())
                return "\n\n".join(parts).strip()
        except Exception as e:
            raise IngestError(f"Failed to extract archive: {path}") from e


class ExtractorRegistry:
    def __init__(self, extractors: Optional[List[Extractor]] = None) -> None:
        self._extractors: List[Extractor] = extractors[:] if extractors else [
            PlainTextExtractor(),
            PDFExtractor(),
            DOCXExtractor(),
            ImageExtractor(),
            SpreadsheetExtractor(),
            ArchiveExtractor(),
        ]

    def pick(self, path: Path) -> Extractor:
        for ex in self._extractors:
            if ex.can_handle(path):
                return ex
        return PlainTextExtractor()

    def file_type_for(self, path: Path) -> str:
        return self.pick(path).file_type


class KnowledgeBase:
    def __init__(self, root_dir: Union[str, Path], storage: Storage, extractor_registry: Optional[ExtractorRegistry] = None) -> None:
        self._root = Path(root_dir).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._storage = storage
        self._extractors = extractor_registry or ExtractorRegistry()

    @property
    def root_dir(self) -> Path:
        return self._root

    @property
    def storage(self) -> Storage:
        return self._storage

    def _abs_path(self, rel_path: str) -> Path:
        p = (self._root / rel_path).resolve()
        _safe_relpath(p, self._root)
        return p

    def ingest_path(self, path: Union[str, Path]) -> DocumentRef:
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = (self._root / p).resolve()
        if not p.exists() or not p.is_file():
            raise IngestError(f"Path does not exist or is not a file: {p}")
        rel = _safe_relpath(p, self._root)
        ex = self._extractors.pick(p)
        file_type = ex.file_type
        stat = p.stat()
        sha = _sha256_file(p)
        now = _utc_now_iso()

        row = self._storage.query_one("SELECT id, sha256, mtime_ns, size_bytes FROM documents WHERE rel_path = ?", (rel,))
        if row is None:
            cur = self._storage.execute(
                """
                INSERT INTO documents(rel_path, abs_path, file_type, size_bytes, mtime_ns, sha256, created_at, updated_at)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (rel, str(p), file_type, int(stat.st_size), int(stat.st_mtime_ns), sha, now, now),
            )
            doc_id = int(cur.lastrowid)
        else:
            doc_id = int(row["id"])
            if row["sha256"] == sha and int(row["mtime_ns"]) == int(stat.st_mtime_ns) and int(row["size_bytes"]) == int(stat.st_size):
                return DocumentRef(doc_id=doc_id, rel_path=rel)
            self._storage.execute(
                """
                UPDATE documents
                SET abs_path = ?, file_type = ?, size_bytes = ?, mtime_ns = ?, sha256 = ?, updated_at = ?
                WHERE id = ?
                """,
                (str(p), file_type, int(stat.st_size), int(stat.st_mtime_ns), sha, now, doc_id),
            )

        text = ex.extract_text(p)
        self._storage.execute(
            """
            INSERT INTO document_text(doc_id, text, extracted_at)
            VALUES(?,?,?)
            ON CONFLICT(doc_id) DO UPDATE SET text=excluded.text, extracted_at=excluded.extracted_at
            """,
            (doc_id, text, now),
        )
        return DocumentRef(doc_id=doc_id, rel_path=rel)

    def ingest_tree(self, subdir: Union[str, Path] = ".", include_hidden: bool = False) -> List[DocumentRef]:
        base = Path(subdir)
        if not base.is_absolute():
            base = (self._root / base).resolve()
        _safe_relpath(base, self._root)
        if not base.exists() or not base.is_dir():
            raise IngestError(f"Not a directory: {base}")

        refs: List[DocumentRef] = []
        for dirpath, dirnames, filenames in os.walk(str(base)):
            dp = Path(dirpath)
            if not include_hidden:
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                filenames = [f for f in filenames if not f.startswith(".")]
            for fn in filenames:
                p = dp / fn
                if p.is_file():
                    try:
                        refs.append(self.ingest_path(p))
                    except IngestError:
                        continue
        return refs

    def get_document(self, doc_id: int) -> DocumentRef:
        row = self._storage.query_one("SELECT id, rel_path FROM documents WHERE id = ?", (doc_id,))
        if row is None:
            raise NotFoundError(f"Document not found: {doc_id}")
        return DocumentRef(doc_id=int(row["id"]), rel_path=str(row["rel_path"]))

    def get_document_text(self, doc_id: int) -> str:
        row = self._storage.query_one("SELECT text FROM document_text WHERE doc_id = ?", (doc_id,))
        if row is None:
            raise NotFoundError(f"No extracted text for document: {doc_id}")
        return str(row["text"])

    def set_metadata(self, doc_id: int, key: str, value: str) -> None:
        k = key.strip()
        if not k:
            raise ValidationError("Metadata key cannot be empty")
        if len(k) > 128:
            raise ValidationError("Metadata key too long")
        v = value if value is not None else ""
        self.get_document(doc_id)
        self._storage.execute(
            """
            INSERT INTO metadata(doc_id, key, value) VALUES(?,?,?)
            ON CONFLICT(doc_id, key) DO UPDATE SET value=excluded.value
            """,
            (doc_id, k, v),
        )

    def get_metadata(self, doc_id: int) -> Dict[str, str]:
        self.get_document(doc_id)
        rows = self._storage.query("SELECT key, value FROM metadata WHERE doc_id = ? ORDER BY key", (doc_id,))
        return {str(r["key"]): str(r["value"]) for r in rows}

    def add_tag(self, doc_id: int, tag: str) -> None:
        t = _normalize_tag(tag)
        self.get_document(doc_id)
        self._storage.execute("INSERT OR IGNORE INTO tags(name) VALUES(?)", (t,))
        tag_row = self._storage.query_one("SELECT id FROM tags WHERE name = ?", (t,))
        if tag_row is None:
            raise MarginaliaError("Failed to create tag")
        tag_id = int(tag_row["id"])
        self._storage.execute("INSERT OR IGNORE INTO document_tags(doc_id, tag_id) VALUES(?,?)", (doc_id, tag_id))

    def remove_tag(self, doc_id: int, tag: str) -> None:
        t = _normalize_tag(tag)
        self.get_document(doc_id)
        row = self._storage.query_one("SELECT id FROM tags WHERE name = ?", (t,))
        if row is None:
            return
        tag_id = int(row["id"])
        self._storage.execute("DELETE FROM document_tags WHERE doc_id = ? AND tag_id = ?", (doc_id, tag_id))

    def list_tags(self, doc_id: int) -> List[str]:
        self.get_document(doc_id)
        rows = self._storage.query(
            """
            SELECT tags.name AS name
            FROM document_tags
            JOIN tags ON tags.id = document_tags.tag_id
            WHERE document_tags.doc_id = ?
            ORDER BY tags.name
            """,
            (doc_id,),
        )
        return [str(r["name"]) for r in rows]

    def create_catalog(self, name: str, description: str = "") -> CatalogRef:
        n = name.strip()
        if not n:
            raise ValidationError("Catalog name cannot be empty")
        if len(n) > 128:
            raise ValidationError("Catalog name too long")
        d = description or ""
        self._storage.execute("INSERT INTO catalogs(name, description) VALUES(?,?)", (n, d))
        row = self._storage.query_one("SELECT id, name FROM catalogs WHERE name = ?", (n,))
        if row is None:
            raise MarginaliaError("Failed to create catalog")
        return CatalogRef(catalog_id=int(row["id"]), name=str(row["name"]))

    def add_to_catalog(self, catalog_id: int, doc_id: int) -> None:
        self.get_document(doc_id)
        row = self._storage.query_one("SELECT id FROM catalogs WHERE id = ?", (catalog_id,))
        if row is None:
            raise NotFoundError(f"Catalog not found: {catalog_id}")
        self._storage.execute("INSERT OR IGNORE INTO catalog_members(catalog_id, doc_id) VALUES(?,?)", (catalog_id, doc_id))

    def remove_from_catalog(self, catalog_id: int, doc_id: int) -> None:
        self._storage.execute("DELETE FROM catalog_members WHERE catalog_id = ? AND doc_id = ?", (catalog_id, doc_id))

    def list_catalog_members(self, catalog_id: int) -> List[DocumentRef]:
        row = self._storage.query_one("SELECT id FROM catalogs WHERE id = ?", (catalog_id,))
        if row is None:
            raise NotFoundError(f"Catalog not found: {catalog_id}")
        rows = self._storage.query(
            """
            SELECT documents.id AS id, documents.rel_path AS rel_path
            FROM catalog_members
            JOIN documents ON documents.id = catalog_members.doc_id
            WHERE catalog_members.catalog_id = ?
            ORDER BY documents.rel_path
            """,
            (catalog_id,),
        )
        return [DocumentRef(doc_id=int(r["id"]), rel_path=str(r["rel_path"])) for r in rows]

    def create_view(self, name: str, query: Dict[str, Any]) -> ViewRef:
        n = name.strip()
        if not n:
            raise ValidationError("View name cannot be empty")
        if len(n) > 128:
            raise ValidationError("View name too long")
        qj = json.dumps(query, ensure_ascii=False, sort_keys=True)
        self._storage.execute("INSERT INTO views(name, query_json) VALUES(?,?)", (n, qj))
        row = self._storage.query_one("SELECT id, name FROM views WHERE name = ?", (n,))
        if row is None:
            raise MarginaliaError("Failed to create view")
        return ViewRef(view_id=int(row["id"]), name=str(row["name"]))

    def get_view_query(self, view_id: int) -> Dict[str, Any]:
        row = self._storage.query_one("SELECT query_json FROM views WHERE id = ?", (view_id,))
        if row is None:
            raise NotFoundError(f"View not found: {view_id}")
        return json.loads(str(row["query_json"]))

    def add_journal_entry(self, title: str, content: str, related_doc_ids: Optional[List[int]] = None) -> JournalEntryRef:
        t = title.strip()
        if not t:
            raise ValidationError("Journal title cannot be empty")
        c = content if content is not None else ""
        ids = related_doc_ids or []
        for did in ids:
            self.get_document(int(did))
        now = _utc_now_iso()
        self._storage.execute(
            "INSERT INTO journals(created_at, title, content, related_doc_ids) VALUES(?,?,?,?)",
            (now, t, c, json.dumps([int(x) for x in ids])),
        )
        row = self._storage.query_one("SELECT last_insert_rowid() AS id")
        if row is None:
            raise MarginaliaError("Failed to create journal entry")
        return JournalEntryRef(entry_id=int(row["id"]))

    def list_journal_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        if limit <= 0 or limit > 1000:
            raise ValidationError("limit must be between 1 and 1000")
        rows = self._storage.query(
            "SELECT id, created_at, title, content, related_doc_ids FROM journals ORDER BY id DESC LIMIT ?",
            (int(limit),),
        )
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": int(r["id"]),
                    "created_at": str(r["created_at"]),
                    "title": str(r["title"]),
                    "content": str(r["content"]),
                    "related_doc_ids": json.loads(str(r["related_doc_ids"])),
                }
            )
        return out

    def mine_relations(self, doc_id: int, max_relations: int = 20) -> List[Tuple[int, str, float]]:
        if max_relations <= 0 or max_relations > 200:
            raise ValidationError("max_relations must be between 1 and 200")
        self.get_document(doc_id)
        src_text = self.get_document_text(doc_id)
        src_tokens = set(_tokenize(src_text))
        if not src_tokens:
            return []

        rows = self._storage.query(
            """
            SELECT documents.id AS id, documents.rel_path AS rel_path, document_text.text AS text
            FROM documents
            JOIN document_text ON document_text.doc_id = documents.id
            WHERE documents.id != ?
            """,
            (doc_id,),
        )
        scored: List[Tuple[int, str, float]] = []
        for r in rows:
            did = int(r["id"])
            txt = str(r["text"])
            toks = set(_tokenize(txt))
            if not toks:
                continue
            inter = len(src_tokens & toks)
            union = len(src_tokens | toks)
            if union == 0:
                continue
            jacc = inter / union
            if jacc <= 0:
                continue
            scored.append((did, str(r["rel_path"]), float(jacc)))

        scored.sort(key=lambda x: x[2], reverse=True)
        scored = scored[: int(max_relations)]
        now = _utc_now_iso()
        for did, _, strength in scored:
            self._storage.execute(
                """
                INSERT INTO relations(src_doc_id, dst_doc_id, relation_type, strength, created_at)
                VALUES(?,?,?,?,?)
                ON CONFLICT(src_doc_id, dst_doc_id, relation_type)
                DO UPDATE SET strength=excluded.strength, created_at=excluded.created_at
                """,
                (doc_id, did, "lexical_overlap", float(strength), now),
            )
        return scored


class SearchQuery:
    def __init__(
        self,
        text: str,
        tags_any: Optional[List[str]] = None,
        tags_all: Optional[List[str]] = None,
        catalogs_any: Optional[List[int]] = None,
        rel_path_prefix: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        self.text = text or ""
        self.tags_any = [ _normalize_tag(t) for t in (tags_any or []) ]
        self.tags_all = [ _normalize_tag(t) for t in (tags_all or []) ]
        self.catalogs_any = [ int(x) for x in (catalogs_any or []) ]
        self.rel_path_prefix = (rel_path_prefix.strip().lstrip("/")) if rel_path_prefix else None
        self.metadata = { (k.strip()): (v if v is not None else "") for k, v in (metadata or {}).items() }
        for k in list(self.metadata.keys()):
            if not k:
                raise ValidationError("Metadata filter key cannot be empty")


class SearchEngine:
    def __init__(self, kb: KnowledgeBase) -> None:
        self._kb = kb

    def lexical_search(self, query: SearchQuery, limit: int = 20) -> List[SearchCandidate]:
        if limit <= 0 or limit > 500:
            raise ValidationError("limit must be between 1 and 500")

        tokens = _tokenize(query.text)
        token_set = set(tokens)

        base_sql = """
            SELECT d.id AS id, d.rel_path AS rel_path, dt.text AS text
            FROM documents d
            JOIN document_text dt ON dt.doc_id = d.id
        """
        where: List[str] = []
        params: List[Any] = []

        if query.rel_path_prefix:
            where.append("d.rel_path LIKE ?")
            params.append(query.rel_path_prefix.replace("\\", "/").rstrip("/") + "/%")

        if query.catalogs_any:
            base_sql += " JOIN catalog_members cm ON cm.doc_id = d.id "
            where.append("cm.catalog_id IN (" + ",".join(["?"] * len(query.catalogs_any)) + ")")
            params.extend(query.catalogs_any)

        if query.tags_any or query.tags_all:
            base_sql += " LEFT JOIN document_tags dtag ON dtag.doc_id = d.id LEFT JOIN tags t ON t.id = dtag.tag_id "

        if query.tags_any:
            where.append("t.name IN (" + ",".join(["?"] * len(query.tags_any)) + ")")
            params.extend(query.tags_any)

        if query.metadata:
            for k, v in query.metadata.items():
                base_sql += " JOIN metadata m_" + re.sub(r"[^A-Za-z0-9_]", "_", k) + " ON m_" + re.sub(r"[^A-Za-z0-9_]", "_", k) + ".doc_id = d.id "
                where.append("m_" + re.sub(r"[^A-Za-z0-9_]", "_", k) + ".key = ? AND m_" + re.sub(r"[^A-Za-z0-9_]", "_", k) + ".value = ?")
                params.extend([k, v])

        sql = base_sql
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " GROUP BY d.id "

        rows = self._kb.storage.query(sql, params)

        if query.tags_all:
            required = set(query.tags_all)
            filtered: List[sqlite3.Row] = []
            for r in rows:
                did = int(r["id"])
                tags = set(self._kb.list_tags(did))
                if required.issubset(tags):
                    filtered.append(r)
            rows = filtered

        candidates: List[SearchCandidate] = []
        for r in rows:
            did = int(r["id"])
            rel = str(r["rel_path"])
            text = str(r["text"])
            if not token_set:
                score = 0.0
                reason = "no_query_tokens"
            else:
                doc_tokens = _tokenize(text)
                if not doc_tokens:
                    score = 0.0
                    reason = "empty_document"
                else:
                    counts: Dict[str, int] = {}
                    for tok in doc_tokens:
                        if tok in token_set:
                            counts[tok] = counts.get(tok, 0) + 1
                    score = float(sum(counts.values()))
                    reason = "lexical_tf"
            if score > 0.0 or not token_set:
                candidates.append(SearchCandidate(doc_id=did, rel_path=rel, score=score, reason=reason))

        candidates.sort(key=lambda c: (c.score, -len(c.rel_path)), reverse=True)
        return candidates[: int(limit)]


class Reader:
    def __init__(self, kb: KnowledgeBase) -> None:
        self._kb = kb

    def read_lines(self, doc_id: int, start_line: int, end_line: int) -> ReadWindow:
        if start_line < 1 or end_line < start_line:
            raise ValidationError("Invalid line range")
        ref = self._kb.get_document(doc_id)
        text = self._kb.get_document_text(doc_id)
        lines = text.splitlines()
        s = start_line - 1
        e = min(end_line, len(lines))
        content = "\n".join(lines[s:e])
        locator = f"{start_line}-{e}"
        return ReadWindow(doc_id=ref.doc_id, rel_path=ref.rel_path, window_type="lines", locator=locator, content=content)

    def read_pages(self, doc_id: int, page_numbers: List[int]) -> ReadWindow:
        if not page_numbers:
            raise ValidationError("page_numbers cannot be empty")
        if any(p <= 0 for p in page_numbers):
            raise ValidationError("page_numbers must be positive")
        ref = self._kb.get_document(doc_id)
        text = self._kb.get_document_text(doc_id)
        pages: Dict[int, str] = {}
        current_page = 0
        buf: List[str] = []
        for line in text.splitlines():
            m = re.match(r"^\[page\s+(\d+)\]\s*$", line.strip())
            if m:
                if current_page > 0:
                    pages[current_page] = "\n".join(buf).strip()
                current_page = int(m.group(1))
                buf = []
            else:
                buf.append(line)
        if current_page > 0:
            pages[current_page] = "\n".join(buf).strip()

        parts: List[str] = []
        for p in page_numbers:
            if p in pages:
                parts.append(f"[page {p}]\n{pages[p]}".rstrip())
        locator = ",".join(str(p) for p in page_numbers)
        return ReadWindow(doc_id=ref.doc_id, rel_path=ref.rel_path, window_type="pages", locator=locator, content="\n\n".join(parts).strip())

    def read_section(self, doc_id: int, heading: str) -> ReadWindow:
        h = heading.strip()
        if not h:
            raise ValidationError("heading cannot be empty")
        ref = self._kb.get_document(doc_id)
        text = self._kb.get_document_text(doc_id)
        lines = text.splitlines()
        idxs: List[int] = []
        for i, line in enumerate(lines):
            if re.match(r"^\s{0,3}#{1,6}\s+", line):
                title = re.sub(r"^\s{0,3}#{1,6}\s+", "", line).strip()
                if title.lower() == h.lower():
                    idxs.append(i)
        if not idxs:
            raise NotFoundError(f"Heading not found: {heading}")
        start = idxs[0]
        end = len(lines)
        for j in range(start + 1, len(lines)):
            if re.match(r"^\s{0,3}#{1,6}\s+", lines[j]):
                end = j
                break
        content = "\n".join(lines[start:end]).strip()
        locator = h
        return ReadWindow(doc_id=ref.doc_id, rel_path=ref.rel_path, window_type="section", locator=locator, content=content)

    def read_archive_member(self, doc_id: int, member_name: str) -> ReadWindow:
        m = member_name.strip()
        if not m:
            raise ValidationError("member_name cannot be empty")
        ref = self._kb.get_document(doc_id)
        abs_path = self._kb._abs_path(ref.rel_path)
        if abs_path.suffix.lower() != ".zip":
            raise ReadError("Document is not a supported archive")
        try:
            with zipfile.ZipFile(str(abs_path), "r") as zf:
                if m not in zf.namelist():
                    raise NotFoundError(f"Archive member not found: {m}")
                data = zf.read(m)
                if len(data) > 5_000_000:
                    raise ReadError("Archive member too large to read")
                try:
                    content = data.decode("utf-8")
                except Exception:
                    content = data.decode("utf-8", errors="replace")
        except MarginaliaError:
            raise
        except Exception as e:
            raise ReadError("Failed to read archive member") from e
        return ReadWindow(doc_id=ref.doc_id, rel_path=ref.rel_path, window_type="archive_member", locator=m, content=content.strip())

    def read_table_slice(self, doc_id: int, sheet: Optional[str] = None, start_row: int = 1, end_row: int = 50) -> ReadWindow:
        if start_row < 1 or end_row < start_row:
            raise ValidationError("Invalid row range")
        ref = self._kb.get_document(doc_id)
        abs_path = self._kb._abs_path(ref.rel_path)
        ext = abs_path.suffix.lower()
        if ext not in {".xlsx", ".xlsm", ".xls", ".ods"}:
            raise ReadError("Document is not a supported spreadsheet")
        try:
            import pandas as pd  # type: ignore
        except Exception as e:
            raise ReadError("Spreadsheet reading requires pandas") from e
        try:
            if ext in {".xlsx", ".xlsm", ".xls"}:
                xls = pd.ExcelFile(str(abs_path))
                target_sheet = sheet or (xls.sheet_names[0] if xls.sheet_names else None)
                if not target_sheet:
                    raise ReadError("No sheets found")
                if target_sheet not in xls.sheet_names:
                    raise NotFoundError(f"Sheet not found: {target_sheet}")
                df = xls.parse(target_sheet)
            else:
                df = pd.read_excel(str(abs_path), engine="odf")
                target_sheet = sheet or "sheet1"
            s = start_row - 1
            e = min(end_row, len(df))
            sliced = df.iloc[s:e]
            content = sliced.to_csv(index=False).strip()
            locator = f"{target_sheet}:{start_row}-{e}"
            return ReadWindow(doc_id=ref.doc_id, rel_path=ref.rel_path, window_type="table_slice", locator=locator, content=content)
        except MarginaliaError:
            raise
        except Exception as e:
            raise ReadError("Failed to read table slice") from e


class SourceQuota:
    def __init__(self, max_sources: int = 8, max_windows_per_source: int = 3) -> None:
        if max_sources <= 0 or max_sources > 100:
            raise ValidationError("max_sources must be between 1 and 100")
        if max_windows_per_source <= 0 or max_windows_per_source > 50:
            raise ValidationError("max_windows_per_source must be between 1 and 50")
        self.max_sources = int(max_sources)
        self.max_windows_per_source = int(max_windows_per_source)


class InvestigationNotes:
    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def write(self, question: str, answer: Answer, notes: str) -> int:
        q = (question or "").strip()
        if not q:
            raise ValidationError("question cannot be empty")
        n = notes if notes is not None else ""
        now = _utc_now_iso()
        citations_json = json.dumps([dataclasses.asdict(c) for c in answer.citations], ensure_ascii=False)
        self._storage.execute(
            """
            INSERT INTO investigations(created_at, updated_at, question, answer_text, citations_json, notes)
            VALUES(?,?,?,?,?,?)
            """,
            (now, now, q, answer.text, citations_json, n),
        )
        row = self._storage.query_one("SELECT last_insert_rowid() AS id")
        if row is None:
            raise MarginaliaError("Failed to write investigation")
        return int(row["id"])

    def list_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        if limit <= 0 or limit > 500:
            raise ValidationError("limit must be between 1 and 500")
        rows = self._storage.query(
            "SELECT id, created_at, updated_at, question, answer_text, citations_json, notes FROM investigations ORDER BY id DESC LIMIT ?",
            (int(limit),),
        )
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": int(r["id"]),
                    "created_at": str(r["created_at"]),
                    "updated_at": str(r["updated_at"]),
                    "question": str(r["question"]),
                    "answer_text": str(r["answer_text"]),
                    "citations": json.loads(str(r["citations_json"])),
                    "notes": str(r["notes"]),
                }
            )
        return out


class LLM(abc.ABC):
    @abc.abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class DeterministicLLM(LLM):
    def generate(self, prompt: str) -> str:
        digest = hashlib.sha256(prompt.encode("utf-8", errors="replace")).hexdigest()[:12]
        return f"Generated response (deterministic:{digest})."


class Agent:
    def __init__(
        self,
        kb: KnowledgeBase,
        search: SearchEngine,
        reader: Reader,
        notes: InvestigationNotes,
        llm: Optional[LLM] = None,
        source_quota: Optional[SourceQuota] = None,
    ) -> None:
        self._kb = kb
        self._search = search
        self._reader = reader
        self._notes = notes
        self._llm = llm or DeterministicLLM()
        self._quota = source_quota or SourceQuota()

    def recall(self, query: SearchQuery, limit: int = 20) -> List[SearchCandidate]:
        return self._search.lexical_search(query, limit=limit)

    def _select_sources(self, candidates: List[SearchCandidate]) -> List[SearchCandidate]:
        if not candidates:
            return []
        by_doc: Dict[int, SearchCandidate] = {}
        for c in candidates:
            if c.doc_id not in by_doc or c.score > by_doc[c.doc_id].score:
                by_doc[c.doc_id] = c
        uniq = list(by_doc.values())
        uniq.sort(key=lambda c: c.score, reverse=True)
        return uniq[: self._quota.max_sources]

    def _read_relevant_windows(self, question: str, sources: List[SearchCandidate]) -> List[ReadWindow]:
        q_tokens = set(_tokenize(question))
        windows: List[ReadWindow] = []
        for src in sources:
            text = self._kb.get_document_text(src.doc_id)
            lines = text.splitlines()
            if not lines:
                continue
            if not q_tokens:
                start = 1
                end = min(60, len(lines))
                windows.append(self._reader.read_lines(src.doc_id, start, end))
                continue

            best: Tuple[int, int, int] = (0, 0, 0)  # score, start_idx, end_idx
            window_size = 60
            for i in range(0, len(lines), max(1, window_size // 2)):
                chunk = lines[i : min(len(lines), i + window_size)]
                toks = set(_tokenize("\n".join(chunk)))
                score = len(toks & q_tokens)
                if score > best[0]:
                    best = (score, i, min(len(lines), i + window_size))
            if best[0] == 0:
                start = 1
                end = min(60, len(lines))
                windows.append(self._reader.read_lines(src.doc_id, start, end))
            else:
                start = best[1] + 1
                end = best[2]
                windows.append(self._reader.read_lines(src.doc_id, start, end))
        return windows

    def answer(self, question: str, query: Optional[SearchQuery] = None, candidate_limit: int = 30) -> Answer:
        q = (question or "").strip()
        if not q:
            raise ValidationError("question cannot be empty")

        qobj = query or SearchQuery(text=q)
        candidates = self.recall(qobj, limit=candidate_limit)
        sources = self._select_sources(candidates)
        windows = self._read_relevant_windows(q, sources)

        citations: List[Citation] = []
        for w in windows:
            citations.append(Citation(doc_id=w.doc_id, rel_path=w.rel_path, window_type=w.window_type, locator=w.locator))

        prompt_parts: List[str] = []
        prompt_parts.append("You are a local-first research agent. Answer using only the provided sources. Include citations.")
        prompt_parts.append(f"Question: {q}")
        prompt_parts.append("Sources:")
        for i, w in enumerate(windows, start=1):
            prompt_parts.append(f"[S{i}] {w.rel_path} ({w.window_type}:{w.locator})\n{w.content}")
        prompt = "\n\n".join(prompt_parts).strip()

        try:
            generated = self._llm.generate(prompt).strip()
        except Exception as e:
            raise AgentError("LLM generation failed") from e

        report = None
        if windows:
            report = "Read windows:\n" + "\n".join([f"- {w.rel_path} ({w.window_type}:{w.locator})" for w in windows])

        ans = Answer(text=generated, citations=citations, report=report)
        self._notes.write(question=q, answer=ans, notes="Durable investigation notes recorded.")
        return ans


class Marginalia:
    def __init__(self, root_dir: Union[str, Path], db_path: Union[str, Path]) -> None:
        self._storage = Storage(db_path)
        self._kb = KnowledgeBase(root_dir=root_dir, storage=self._storage)
        self._search = SearchEngine(self._kb)
        self._reader = Reader(self._kb)
        self._notes = InvestigationNotes(self._storage)
        self._agent = Agent(self._kb, self._search, self._reader, self._notes)

    @property
    def kb(self) -> KnowledgeBase:
        return self._kb

    @property
    def agent(self) -> Agent:
        return self._agent

    @property
    def search(self) -> SearchEngine:
        return self._search

    @property
    def reader(self) -> Reader:
        return self._reader

    @property
    def notes(self) -> InvestigationNotes:
        return self._notes

    def close(self) -> None:
        self._storage.close()