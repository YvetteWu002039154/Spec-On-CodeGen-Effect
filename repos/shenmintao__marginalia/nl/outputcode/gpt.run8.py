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
import datetime as _dt
from dataclasses import dataclass
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
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _norm_relpath(path: str) -> str:
    path = path.replace("\\", "/")
    path = re.sub(r"/+", "/", path)
    path = path.strip("/")
    return path


def _safe_join(root: str, rel: str) -> str:
    rel = _norm_relpath(rel)
    full = os.path.abspath(os.path.join(root, rel))
    root_abs = os.path.abspath(root)
    if not (full == root_abs or full.startswith(root_abs + os.sep)):
        raise ValidationError("Path escapes root")
    return full


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _guess_mime(path: str) -> str:
    mt, _ = mimetypes.guess_type(path)
    return mt or "application/octet-stream"


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", text)


def _normalize_whitespace(s: str) -> str:
    return re.sub(r"[ \t]+", " ", re.sub(r"\r\n|\r", "\n", s)).strip()


@dataclass(frozen=True)
class SourceRef:
    document_id: str
    window_id: str
    label: str


@dataclass(frozen=True)
class ReadWindow:
    window_id: str
    document_id: str
    kind: str
    start: int
    end: int
    text: str
    label: str


@dataclass(frozen=True)
class Candidate:
    document_id: str
    score: float
    title: str
    relpath: str
    mime: str


@dataclass(frozen=True)
class Answer:
    answer_id: str
    created_at: str
    query: str
    text: str
    citations: List[SourceRef]
    note_id: str


class SQLiteStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        _ensure_dir(os.path.dirname(os.path.abspath(db_path)) or ".")
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")
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
                relpath TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                mime TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                extra_json TEXT NOT NULL
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
                document_id TEXT NOT NULL,
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
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_members (
                catalog_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                PRIMARY KEY (catalog_id, document_id),
                FOREIGN KEY (catalog_id) REFERENCES catalogs(id) ON DELETE CASCADE,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS journals (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS journal_entries (
                id TEXT PRIMARY KEY,
                journal_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                FOREIGN KEY (journal_id) REFERENCES journals(id) ON DELETE CASCADE
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
                related_document_id TEXT,
                FOREIGN KEY (related_document_id) REFERENCES documents(id) ON DELETE SET NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS relations (
                id TEXT PRIMARY KEY,
                from_document_id TEXT NOT NULL,
                to_document_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                score REAL NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(from_document_id, to_document_id, kind),
                FOREIGN KEY (from_document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (to_document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS lexical_index (
                document_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                document_id TEXT PRIMARY KEY,
                dim INTEGER NOT NULL,
                vector_json TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS investigations (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                query TEXT NOT NULL,
                answer_text TEXT NOT NULL,
                citations_json TEXT NOT NULL,
                note_id TEXT NOT NULL,
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
            )
            """
        )
        self._conn.commit()


class FileRepository:
    def __init__(self, root_dir: str) -> None:
        self._root_dir = os.path.abspath(root_dir)
        _ensure_dir(self._root_dir)

    @property
    def root_dir(self) -> str:
        return self._root_dir

    def resolve(self, relpath: str) -> str:
        return _safe_join(self._root_dir, relpath)

    def exists(self, relpath: str) -> bool:
        return os.path.exists(self.resolve(relpath))

    def stat(self, relpath: str) -> os.stat_result:
        return os.stat(self.resolve(relpath))

    def read_bytes(self, relpath: str) -> bytes:
        path = self.resolve(relpath)
        with open(path, "rb") as f:
            return f.read()

    def read_text(self, relpath: str, encoding: str = "utf-8") -> str:
        path = self.resolve(relpath)
        with open(path, "r", encoding=encoding, errors="replace") as f:
            return f.read()

    def write_bytes(self, relpath: str, data: bytes, overwrite: bool = False) -> None:
        relpath = _norm_relpath(relpath)
        path = self.resolve(relpath)
        parent = os.path.dirname(path)
        _ensure_dir(parent)
        if os.path.exists(path) and not overwrite:
            raise ValidationError("File exists")
        with open(path, "wb") as f:
            f.write(data)

    def copy_in(self, src_path: str, dest_relpath: str, overwrite: bool = False) -> None:
        dest_relpath = _norm_relpath(dest_relpath)
        dest_path = self.resolve(dest_relpath)
        _ensure_dir(os.path.dirname(dest_path))
        if os.path.exists(dest_path) and not overwrite:
            raise ValidationError("File exists")
        shutil.copy2(src_path, dest_path)

    def list_files(self) -> List[str]:
        out: List[str] = []
        for root, _, files in os.walk(self._root_dir):
            for fn in files:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, self._root_dir)
                out.append(_norm_relpath(rel))
        out.sort()
        return out


class Document:
    def __init__(
        self,
        document_id: str,
        relpath: str,
        title: str,
        mime: str,
        size_bytes: int,
        sha256: str,
        created_at: str,
        updated_at: str,
        ingested_at: str,
        kind: str,
        extra: Dict[str, Any],
    ) -> None:
        self._id = document_id
        self._relpath = relpath
        self._title = title
        self._mime = mime
        self._size_bytes = size_bytes
        self._sha256 = sha256
        self._created_at = created_at
        self._updated_at = updated_at
        self._ingested_at = ingested_at
        self._kind = kind
        self._extra = dict(extra)

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
    def mime(self) -> str:
        return self._mime

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
    def ingested_at(self) -> str:
        return self._ingested_at

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def extra(self) -> Dict[str, Any]:
        return dict(self._extra)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self._id,
            "relpath": self._relpath,
            "title": self._title,
            "mime": self._mime,
            "size_bytes": self._size_bytes,
            "sha256": self._sha256,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "ingested_at": self._ingested_at,
            "kind": self._kind,
            "extra": dict(self._extra),
        }

    @staticmethod
    def from_row(row: sqlite3.Row) -> "Document":
        extra = json.loads(row["extra_json"])
        return Document(
            document_id=row["id"],
            relpath=row["relpath"],
            title=row["title"],
            mime=row["mime"],
            size_bytes=int(row["size_bytes"]),
            sha256=row["sha256"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            ingested_at=row["ingested_at"],
            kind=row["kind"],
            extra=extra,
        )


class Catalog:
    def __init__(self, catalog_id: str, name: str, created_at: str) -> None:
        self._id = catalog_id
        self._name = name
        self._created_at = created_at

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def created_at(self) -> str:
        return self._created_at


class Journal:
    def __init__(self, journal_id: str, name: str, created_at: str) -> None:
        self._id = journal_id
        self._name = name
        self._created_at = created_at

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def created_at(self) -> str:
        return self._created_at


class Note:
    def __init__(
        self,
        note_id: str,
        created_at: str,
        updated_at: str,
        title: str,
        body: str,
        related_document_id: Optional[str],
    ) -> None:
        self._id = note_id
        self._created_at = created_at
        self._updated_at = updated_at
        self._title = title
        self._body = body
        self._related_document_id = related_document_id

    @property
    def id(self) -> str:
        return self._id

    @property
    def created_at(self) -> str:
        return self._created_at

    @property
    def updated_at(self) -> str:
        return self._updated_at

    @property
    def title(self) -> str:
        return self._title

    @property
    def body(self) -> str:
        return self._body

    @property
    def related_document_id(self) -> Optional[str]:
        return self._related_document_id


class Ingestor:
    SUPPORTED_TEXT_EXTS = {
        ".txt",
        ".md",
        ".markdown",
        ".log",
        ".csv",
        ".tsv",
        ".json",
        ".yaml",
        ".yml",
        ".py",
        ".js",
        ".ts",
        ".html",
        ".htm",
        ".css",
        ".xml",
    }

    def __init__(self, repo: FileRepository) -> None:
        self._repo = repo

    def detect_kind(self, relpath: str) -> str:
        ext = os.path.splitext(relpath)[1].lower()
        if ext in self.SUPPORTED_TEXT_EXTS:
            return "text"
        if ext in {".pdf"}:
            return "pdf"
        if ext in {".docx"}:
            return "docx"
        if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}:
            return "image"
        if ext in {".xlsx", ".xls"}:
            return "spreadsheet"
        if ext in {".zip"}:
            return "archive"
        return "binary"

    def extract_text(self, relpath: str, max_chars: int = 2_000_000) -> Tuple[str, Dict[str, Any]]:
        kind = self.detect_kind(relpath)
        path = self._repo.resolve(relpath)
        extra: Dict[str, Any] = {"kind": kind}

        if kind == "text":
            try:
                text = self._repo.read_text(relpath)
            except Exception as e:
                raise IngestError(str(e)) from e
            text = _normalize_whitespace(text)
            if len(text) > max_chars:
                text = text[:max_chars]
                extra["truncated"] = True
            return text, extra

        if kind == "archive":
            try:
                with zipfile.ZipFile(path, "r") as zf:
                    members = [m for m in zf.namelist() if not m.endswith("/")]
                    extra["members"] = members[:5000]
                    texts: List[str] = []
                    for name in members[:200]:
                        ext = os.path.splitext(name)[1].lower()
                        if ext in self.SUPPORTED_TEXT_EXTS:
                            try:
                                data = zf.read(name)
                            except Exception:
                                continue
                            try:
                                s = data.decode("utf-8", errors="replace")
                            except Exception:
                                continue
                            s = _normalize_whitespace(s)
                            if s:
                                texts.append(f"[archive:{name}]\n{s}")
                        if sum(len(t) for t in texts) >= max_chars:
                            break
                    text = "\n\n".join(texts)
                    if len(text) > max_chars:
                        text = text[:max_chars]
                        extra["truncated"] = True
                    return text, extra
            except Exception as e:
                raise IngestError(str(e)) from e

        if kind in {"pdf", "docx", "image", "spreadsheet", "binary"}:
            extra["note"] = "No built-in extractor for this type; indexed by filename and metadata only."
            return "", extra

        return "", extra


class LexicalSearchEngine:
    def __init__(self, store: SQLiteStore) -> None:
        self._store = store
        self._store.conn.row_factory = sqlite3.Row

    def upsert_document_content(self, document_id: str, content: str) -> None:
        content = content or ""
        self._store.conn.execute(
            """
            INSERT INTO lexical_index(document_id, content)
            VALUES(?, ?)
            ON CONFLICT(document_id) DO UPDATE SET content=excluded.content
            """,
            (document_id, content),
        )
        self._store.conn.commit()

    def delete_document(self, document_id: str) -> None:
        self._store.conn.execute("DELETE FROM lexical_index WHERE document_id=?", (document_id,))
        self._store.conn.commit()

    def search(self, query: str, limit: int = 20) -> List[Tuple[str, float]]:
        if limit <= 0:
            raise ValidationError("limit must be positive")
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        q_set = set(q_tokens)

        cur = self._store.conn.execute(
            """
            SELECT d.id as id, d.title as title, d.relpath as relpath, d.mime as mime, li.content as content
            FROM documents d
            LEFT JOIN lexical_index li ON li.document_id = d.id
            """
        )
        scored: List[Tuple[str, float]] = []
        for row in cur.fetchall():
            content = row["content"] or ""
            hay = f"{row['title']} {row['relpath']} {content}".lower()
            tokens = _tokenize(hay)
            if not tokens:
                continue
            t_set = set(tokens)
            overlap = len(q_set.intersection(t_set))
            if overlap == 0:
                continue
            denom = math.sqrt(len(q_set) * len(t_set))
            score = overlap / denom if denom else 0.0
            scored.append((row["id"], float(score)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]


class EmbeddingEngine:
    def __init__(self, store: SQLiteStore, dim: int = 128) -> None:
        if dim <= 0:
            raise ValidationError("dim must be positive")
        self._store = store
        self._dim = dim
        self._store.conn.row_factory = sqlite3.Row

    @property
    def dim(self) -> int:
        return self._dim

    def _embed(self, text: str) -> List[float]:
        vec = [0.0] * self._dim
        tokens = _tokenize(text)
        if not tokens:
            return vec
        for t in tokens:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            idx = int.from_bytes(h[:4], "big") % self._dim
            sign = 1.0 if (h[4] & 1) == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def upsert(self, document_id: str, text: str) -> None:
        vec = self._embed(text or "")
        self._store.conn.execute(
            """
            INSERT INTO embeddings(document_id, dim, vector_json)
            VALUES(?, ?, ?)
            ON CONFLICT(document_id) DO UPDATE SET dim=excluded.dim, vector_json=excluded.vector_json
            """,
            (document_id, self._dim, json.dumps(vec)),
        )
        self._store.conn.commit()

    def delete(self, document_id: str) -> None:
        self._store.conn.execute("DELETE FROM embeddings WHERE document_id=?", (document_id,))
        self._store.conn.commit()

    def search(self, query: str, limit: int = 20) -> List[Tuple[str, float]]:
        if limit <= 0:
            raise ValidationError("limit must be positive")
        qv = self._embed(query)
        cur = self._store.conn.execute("SELECT document_id, dim, vector_json FROM embeddings")
        scored: List[Tuple[str, float]] = []
        for row in cur.fetchall():
            if int(row["dim"]) != self._dim:
                continue
            dv = json.loads(row["vector_json"])
            if not dv:
                continue
            score = float(sum(float(a) * float(b) for a, b in zip(qv, dv)))
            scored.append((row["document_id"], score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]


class RelationMiner:
    def __init__(self, store: SQLiteStore) -> None:
        self._store = store
        self._store.conn.row_factory = sqlite3.Row

    def mine(self, document_id: str, content: str, top_k: int = 5) -> None:
        if top_k <= 0:
            raise ValidationError("top_k must be positive")
        tokens = _tokenize(content or "")
        if not tokens:
            return
        freq: Dict[str, int] = {}
        for t in tokens:
            if len(t) < 4:
                continue
            freq[t] = freq.get(t, 0) + 1
        keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:20]
        if not keywords:
            return
        kw_set = {k for k, _ in keywords}

        cur = self._store.conn.execute(
            """
            SELECT d.id as id, li.content as content
            FROM documents d
            LEFT JOIN lexical_index li ON li.document_id = d.id
            WHERE d.id != ?
            """,
            (document_id,),
        )
        scored: List[Tuple[str, float]] = []
        for row in cur.fetchall():
            other_content = row["content"] or ""
            other_tokens = set(_tokenize(other_content))
            overlap = len(kw_set.intersection(other_tokens))
            if overlap <= 0:
                continue
            score = overlap / max(1.0, len(kw_set))
            scored.append((row["id"], float(score)))
        scored.sort(key=lambda x: x[1], reverse=True)
        scored = scored[:top_k]

        now = _utc_now_iso()
        for other_id, score in scored:
            rel_id = str(uuid.uuid4())
            self._store.conn.execute(
                """
                INSERT INTO relations(id, from_document_id, to_document_id, kind, score, created_at)
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(from_document_id, to_document_id, kind)
                DO UPDATE SET score=excluded.score, created_at=excluded.created_at
                """,
                (rel_id, document_id, other_id, "keyword_overlap", score, now),
            )
        self._store.conn.commit()


class Reader:
    def __init__(self, repo: FileRepository, ingestor: Ingestor) -> None:
        self._repo = repo
        self._ingestor = ingestor

    def read_windows(
        self,
        document: Document,
        query: str,
        max_windows: int = 5,
        window_chars: int = 1200,
        overlap_chars: int = 200,
    ) -> List[ReadWindow]:
        if max_windows <= 0:
            raise ValidationError("max_windows must be positive")
        if window_chars <= 0:
            raise ValidationError("window_chars must be positive")
        if overlap_chars < 0 or overlap_chars >= window_chars:
            raise ValidationError("overlap_chars must be in [0, window_chars)")

        text, _ = self._ingestor.extract_text(document.relpath)
        if not text:
            label = f"{document.title} ({document.relpath})"
            return [
                ReadWindow(
                    window_id=str(uuid.uuid4()),
                    document_id=document.id,
                    kind="metadata",
                    start=0,
                    end=0,
                    text=f"Title: {document.title}\nPath: {document.relpath}\nMIME: {document.mime}\nKind: {document.kind}",
                    label=label,
                )
            ]

        q_tokens = set(_tokenize(query))
        if not q_tokens:
            q_tokens = set(_tokenize(document.title))

        step = max(1, window_chars - overlap_chars)
        windows: List[Tuple[int, int, str]] = []
        for start in range(0, len(text), step):
            end = min(len(text), start + window_chars)
            chunk = text[start:end]
            windows.append((start, end, chunk))
            if end >= len(text):
                break

        scored: List[Tuple[float, int, int, str]] = []
        for start, end, chunk in windows:
            tokens = set(_tokenize(chunk))
            overlap = len(tokens.intersection(q_tokens))
            if overlap == 0:
                continue
            score = overlap / max(1.0, len(q_tokens))
            scored.append((float(score), start, end, chunk))
        if not scored:
            scored = [(0.0, windows[0][0], windows[0][1], windows[0][2])] if windows else []

        scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
        picked = scored[:max_windows]

        out: List[ReadWindow] = []
        for score, start, end, chunk in picked:
            label = f"{document.title} ({document.relpath}) chars[{start}:{end}]"
            out.append(
                ReadWindow(
                    window_id=str(uuid.uuid4()),
                    document_id=document.id,
                    kind="text_window",
                    start=start,
                    end=end,
                    text=chunk,
                    label=label,
                )
            )
        return out


class SourceQuota:
    def __init__(self, max_sources: int = 8, max_windows_per_source: int = 3) -> None:
        if max_sources <= 0:
            raise ValidationError("max_sources must be positive")
        if max_windows_per_source <= 0:
            raise ValidationError("max_windows_per_source must be positive")
        self.max_sources = max_sources
        self.max_windows_per_source = max_windows_per_source


class View:
    def __init__(
        self,
        name: str,
        query: str,
        use_embeddings: bool = False,
        rerank: bool = False,
        limit: int = 20,
    ) -> None:
        if not name.strip():
            raise ValidationError("View name required")
        if limit <= 0:
            raise ValidationError("limit must be positive")
        self._name = name
        self._query = query
        self._use_embeddings = bool(use_embeddings)
        self._rerank = bool(rerank)
        self._limit = int(limit)

    @property
    def name(self) -> str:
        return self._name

    @property
    def query(self) -> str:
        return self._query

    @property
    def use_embeddings(self) -> bool:
        return self._use_embeddings

    @property
    def rerank(self) -> bool:
        return self._rerank

    @property
    def limit(self) -> int:
        return self._limit


class KnowledgeBase:
    def __init__(self, root_dir: str, db_path: str) -> None:
        self._repo = FileRepository(root_dir)
        self._store = SQLiteStore(db_path)
        self._ingestor = Ingestor(self._repo)
        self._lex = LexicalSearchEngine(self._store)
        self._emb = EmbeddingEngine(self._store)
        self._miner = RelationMiner(self._store)
        self._reader = Reader(self._repo, self._ingestor)
        self._store.conn.row_factory = sqlite3.Row

    @property
    def repo(self) -> FileRepository:
        return self._repo

    @property
    def store(self) -> SQLiteStore:
        return self._store

    def close(self) -> None:
        self._store.close()

    def _get_document_by_id(self, document_id: str) -> Document:
        cur = self._store.conn.execute("SELECT * FROM documents WHERE id=?", (document_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("Document not found")
        return Document.from_row(row)

    def _get_document_by_relpath(self, relpath: str) -> Optional[Document]:
        relpath = _norm_relpath(relpath)
        cur = self._store.conn.execute("SELECT * FROM documents WHERE relpath=?", (relpath,))
        row = cur.fetchone()
        return Document.from_row(row) if row else None

    def list_documents(self) -> List[Document]:
        cur = self._store.conn.execute("SELECT * FROM documents ORDER BY relpath ASC")
        return [Document.from_row(r) for r in cur.fetchall()]

    def ingest_file(
        self,
        src_path: str,
        dest_relpath: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        catalogs: Optional[Sequence[str]] = None,
        overwrite: bool = False,
        build_embeddings: bool = False,
        mine_relations: bool = True,
    ) -> Document:
        if not os.path.isfile(src_path):
            raise ValidationError("src_path must be a file")
        if dest_relpath is None:
            dest_relpath = os.path.basename(src_path)
        dest_relpath = _norm_relpath(dest_relpath)
        if not dest_relpath:
            raise ValidationError("dest_relpath required")

        self._repo.copy_in(src_path, dest_relpath, overwrite=overwrite)

        return self.ingest_existing(
            dest_relpath=dest_relpath,
            title=title,
            tags=tags,
            catalogs=catalogs,
            build_embeddings=build_embeddings,
            mine_relations=mine_relations,
        )

    def ingest_existing(
        self,
        dest_relpath: str,
        title: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        catalogs: Optional[Sequence[str]] = None,
        build_embeddings: bool = False,
        mine_relations: bool = True,
    ) -> Document:
        dest_relpath = _norm_relpath(dest_relpath)
        if not self._repo.exists(dest_relpath):
            raise NotFoundError("File not found in repository")

        path = self._repo.resolve(dest_relpath)
        st = os.stat(path)
        sha = _sha256_file(path)
        mime = _guess_mime(path)
        kind = self._ingestor.detect_kind(dest_relpath)
        now = _utc_now_iso()
        created_at = _dt.datetime.utcfromtimestamp(st.st_ctime).replace(microsecond=0).isoformat() + "Z"
        updated_at = _dt.datetime.utcfromtimestamp(st.st_mtime).replace(microsecond=0).isoformat() + "Z"
        ingested_at = now

        if title is None or not title.strip():
            base = os.path.basename(dest_relpath)
            title = os.path.splitext(base)[0] or base

        existing = self._get_document_by_relpath(dest_relpath)
        if existing:
            doc_id = existing.id
            self._store.conn.execute(
                """
                UPDATE documents
                SET title=?, mime=?, size_bytes=?, sha256=?, created_at=?, updated_at=?, ingested_at=?, kind=?, extra_json=?
                WHERE id=?
                """,
                (
                    title,
                    mime,
                    int(st.st_size),
                    sha,
                    created_at,
                    updated_at,
                    ingested_at,
                    kind,
                    json.dumps({}),
                    doc_id,
                ),
            )
        else:
            doc_id = str(uuid.uuid4())
            self._store.conn.execute(
                """
                INSERT INTO documents(id, relpath, title, mime, size_bytes, sha256, created_at, updated_at, ingested_at, kind, extra_json)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    dest_relpath,
                    title,
                    mime,
                    int(st.st_size),
                    sha,
                    created_at,
                    updated_at,
                    ingested_at,
                    kind,
                    json.dumps({}),
                ),
            )

        extracted_text, extra = self._ingestor.extract_text(dest_relpath)
        self._store.conn.execute("UPDATE documents SET extra_json=? WHERE id=?", (json.dumps(extra), doc_id))
        self._store.conn.commit()

        self._lex.upsert_document_content(doc_id, extracted_text)

        if build_embeddings:
            self._emb.upsert(doc_id, f"{title}\n{dest_relpath}\n{extracted_text}")

        if tags:
            for t in tags:
                self.add_tag(doc_id, t)

        if catalogs:
            for c in catalogs:
                self.add_to_catalog(doc_id, c)

        if mine_relations:
            self._miner.mine(doc_id, extracted_text)

        self._append_journal_event(
            journal_name="ingest",
            kind="document_ingested",
            payload={
                "document_id": doc_id,
                "relpath": dest_relpath,
                "title": title,
                "mime": mime,
                "kind": kind,
                "size_bytes": int(st.st_size),
                "sha256": sha,
                "ingested_at": ingested_at,
            },
        )

        return self._get_document_by_id(doc_id)

    def delete_document(self, document_id: str, delete_file: bool = False) -> None:
        doc = self._get_document_by_id(document_id)
        if delete_file and self._repo.exists(doc.relpath):
            os.remove(self._repo.resolve(doc.relpath))
        self._store.conn.execute("DELETE FROM documents WHERE id=?", (document_id,))
        self._store.conn.commit()
        self._append_journal_event(
            journal_name="ingest",
            kind="document_deleted",
            payload={"document_id": document_id, "relpath": doc.relpath, "delete_file": bool(delete_file)},
        )

    def add_tag(self, document_id: str, tag: str) -> None:
        tag = tag.strip()
        if not tag:
            raise ValidationError("tag required")
        self._get_document_by_id(document_id)
        cur = self._store.conn.execute("SELECT id FROM tags WHERE name=?", (tag,))
        row = cur.fetchone()
        if row:
            tag_id = int(row["id"])
        else:
            self._store.conn.execute("INSERT INTO tags(name) VALUES(?)", (tag,))
            tag_id = int(self._store.conn.execute("SELECT id FROM tags WHERE name=?", (tag,)).fetchone()["id"])
        self._store.conn.execute(
            "INSERT OR IGNORE INTO document_tags(document_id, tag_id) VALUES(?, ?)",
            (document_id, tag_id),
        )
        self._store.conn.commit()

    def remove_tag(self, document_id: str, tag: str) -> None:
        tag = tag.strip()
        if not tag:
            raise ValidationError("tag required")
        cur = self._store.conn.execute("SELECT id FROM tags WHERE name=?", (tag,))
        row = cur.fetchone()
        if not row:
            return
        tag_id = int(row["id"])
        self._store.conn.execute("DELETE FROM document_tags WHERE document_id=? AND tag_id=?", (document_id, tag_id))
        self._store.conn.commit()

    def list_tags(self, document_id: Optional[str] = None) -> List[str]:
        if document_id is None:
            cur = self._store.conn.execute("SELECT name FROM tags ORDER BY name ASC")
            return [r["name"] for r in cur.fetchall()]
        self._get_document_by_id(document_id)
        cur = self._store.conn.execute(
            """
            SELECT t.name as name
            FROM tags t
            JOIN document_tags dt ON dt.tag_id = t.id
            WHERE dt.document_id=?
            ORDER BY t.name ASC
            """,
            (document_id,),
        )
        return [r["name"] for r in cur.fetchall()]

    def create_catalog(self, name: str) -> Catalog:
        name = name.strip()
        if not name:
            raise ValidationError("Catalog name required")
        cur = self._store.conn.execute("SELECT id, name, created_at FROM catalogs WHERE name=?", (name,))
        row = cur.fetchone()
        if row:
            return Catalog(row["id"], row["name"], row["created_at"])
        cid = str(uuid.uuid4())
        now = _utc_now_iso()
        self._store.conn.execute("INSERT INTO catalogs(id, name, created_at) VALUES(?, ?, ?)", (cid, name, now))
        self._store.conn.commit()
        return Catalog(cid, name, now)

    def add_to_catalog(self, document_id: str, catalog_name: str) -> None:
        self._get_document_by_id(document_id)
        cat = self.create_catalog(catalog_name)
        self._store.conn.execute(
            "INSERT OR IGNORE INTO catalog_members(catalog_id, document_id) VALUES(?, ?)",
            (cat.id, document_id),
        )
        self._store.conn.commit()

    def remove_from_catalog(self, document_id: str, catalog_name: str) -> None:
        catalog_name = catalog_name.strip()
        if not catalog_name:
            raise ValidationError("catalog_name required")
        cur = self._store.conn.execute("SELECT id FROM catalogs WHERE name=?", (catalog_name,))
        row = cur.fetchone()
        if not row:
            return
        cid = row["id"]
        self._store.conn.execute(
            "DELETE FROM catalog_members WHERE catalog_id=? AND document_id=?",
            (cid, document_id),
        )
        self._store.conn.commit()

    def list_catalogs(self) -> List[str]:
        cur = self._store.conn.execute("SELECT name FROM catalogs ORDER BY name ASC")
        return [r["name"] for r in cur.fetchall()]

    def list_catalog_members(self, catalog_name: str) -> List[Document]:
        catalog_name = catalog_name.strip()
        if not catalog_name:
            raise ValidationError("catalog_name required")
        cur = self._store.conn.execute("SELECT id FROM catalogs WHERE name=?", (catalog_name,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("Catalog not found")
        cid = row["id"]
        cur2 = self._store.conn.execute(
            """
            SELECT d.*
            FROM documents d
            JOIN catalog_members cm ON cm.document_id = d.id
            WHERE cm.catalog_id=?
            ORDER BY d.relpath ASC
            """,
            (cid,),
        )
        return [Document.from_row(r) for r in cur2.fetchall()]

    def create_journal(self, name: str) -> Journal:
        name = name.strip()
        if not name:
            raise ValidationError("Journal name required")
        cur = self._store.conn.execute("SELECT id, name, created_at FROM journals WHERE name=?", (name,))
        row = cur.fetchone()
        if row:
            return Journal(row["id"], row["name"], row["created_at"])
        jid = str(uuid.uuid4())
        now = _utc_now_iso()
        self._store.conn.execute("INSERT INTO journals(id, name, created_at) VALUES(?, ?, ?)", (jid, name, now))
        self._store.conn.commit()
        return Journal(jid, name, now)

    def _append_journal_event(self, journal_name: str, kind: str, payload: Dict[str, Any]) -> None:
        journal = self.create_journal(journal_name)
        eid = str(uuid.uuid4())
        now = _utc_now_iso()
        self._store.conn.execute(
            "INSERT INTO journal_entries(id, journal_id, created_at, kind, payload_json) VALUES(?, ?, ?, ?, ?)",
            (eid, journal.id, now, kind, json.dumps(payload)),
        )
        self._store.conn.commit()

    def list_journal_entries(self, journal_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        if limit <= 0:
            raise ValidationError("limit must be positive")
        journal_name = journal_name.strip()
        if not journal_name:
            raise ValidationError("journal_name required")
        cur = self._store.conn.execute("SELECT id FROM journals WHERE name=?", (journal_name,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("Journal not found")
        jid = row["id"]
        cur2 = self._store.conn.execute(
            """
            SELECT id, created_at, kind, payload_json
            FROM journal_entries
            WHERE journal_id=?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (jid, limit),
        )
        out: List[Dict[str, Any]] = []
        for r in cur2.fetchall():
            out.append(
                {
                    "id": r["id"],
                    "created_at": r["created_at"],
                    "kind": r["kind"],
                    "payload": json.loads(r["payload_json"]),
                }
            )
        return out

    def create_note(self, title: str, body: str, related_document_id: Optional[str] = None) -> Note:
        title = title.strip()
        if not title:
            raise ValidationError("Note title required")
        if related_document_id is not None:
            self._get_document_by_id(related_document_id)
        nid = str(uuid.uuid4())
        now = _utc_now_iso()
        self._store.conn.execute(
            "INSERT INTO notes(id, created_at, updated_at, title, body, related_document_id) VALUES(?, ?, ?, ?, ?, ?)",
            (nid, now, now, title, body, related_document_id),
        )
        self._store.conn.commit()
        return self.get_note(nid)

    def update_note(self, note_id: str, title: Optional[str] = None, body: Optional[str] = None) -> Note:
        note = self.get_note(note_id)
        new_title = note.title if title is None else title.strip()
        if not new_title:
            raise ValidationError("Note title required")
        new_body = note.body if body is None else body
        now = _utc_now_iso()
        self._store.conn.execute(
            "UPDATE notes SET title=?, body=?, updated_at=? WHERE id=?",
            (new_title, new_body, now, note_id),
        )
        self._store.conn.commit()
        return self.get_note(note_id)

    def get_note(self, note_id: str) -> Note:
        cur = self._store.conn.execute("SELECT * FROM notes WHERE id=?", (note_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("Note not found")
        return Note(
            note_id=row["id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            title=row["title"],
            body=row["body"],
            related_document_id=row["related_document_id"],
        )

    def list_notes(self, limit: int = 50) -> List[Note]:
        if limit <= 0:
            raise ValidationError("limit must be positive")
        cur = self._store.conn.execute("SELECT * FROM notes ORDER BY updated_at DESC LIMIT ?", (limit,))
        return [
            Note(
                note_id=r["id"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                title=r["title"],
                body=r["body"],
                related_document_id=r["related_document_id"],
            )
            for r in cur.fetchall()
        ]

    def list_relations(self, document_id: str, kind: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        if limit <= 0:
            raise ValidationError("limit must be positive")
        self._get_document_by_id(document_id)
        if kind is None:
            cur = self._store.conn.execute(
                """
                SELECT r.*, d2.title as to_title, d2.relpath as to_relpath
                FROM relations r
                JOIN documents d2 ON d2.id = r.to_document_id
                WHERE r.from_document_id=?
                ORDER BY r.score DESC
                LIMIT ?
                """,
                (document_id, limit),
            )
        else:
            cur = self._store.conn.execute(
                """
                SELECT r.*, d2.title as to_title, d2.relpath as to_relpath
                FROM relations r
                JOIN documents d2 ON d2.id = r.to_document_id
                WHERE r.from_document_id=? AND r.kind=?
                ORDER BY r.score DESC
                LIMIT ?
                """,
                (document_id, kind, limit),
            )
        out: List[Dict[str, Any]] = []
        for r in cur.fetchall():
            out.append(
                {
                    "id": r["id"],
                    "from_document_id": r["from_document_id"],
                    "to_document_id": r["to_document_id"],
                    "to_title": r["to_title"],
                    "to_relpath": r["to_relpath"],
                    "kind": r["kind"],
                    "score": float(r["score"]),
                    "created_at": r["created_at"],
                }
            )
        return out

    def search(
        self,
        query: str,
        limit: int = 20,
        use_embeddings: bool = False,
        rerank: bool = False,
    ) -> List[Candidate]:
        if limit <= 0:
            raise ValidationError("limit must be positive")
        query = query.strip()
        if not query:
            return []

        lex = self._lex.search(query, limit=max(limit, 50))
        lex_map = {doc_id: score for doc_id, score in lex}

        emb_map: Dict[str, float] = {}
        if use_embeddings:
            emb = self._emb.search(query, limit=max(limit, 50))
            emb_map = {doc_id: score for doc_id, score in emb}

        combined_ids = set(lex_map.keys()) | set(emb_map.keys())
        if not combined_ids:
            return []

        def comb_score(doc_id: str) -> float:
            a = lex_map.get(doc_id, 0.0)
            b = emb_map.get(doc_id, 0.0)
            return 0.7 * a + 0.3 * b if use_embeddings else a

        ranked = sorted(((doc_id, comb_score(doc_id)) for doc_id in combined_ids), key=lambda x: x[1], reverse=True)

        if rerank:
            q_tokens = set(_tokenize(query))
            reranked: List[Tuple[str, float]] = []
            for doc_id, base in ranked[: max(limit, 50)]:
                doc = self._get_document_by_id(doc_id)
                content_row = self._store.conn.execute(
                    "SELECT content FROM lexical_index WHERE document_id=?",
                    (doc_id,),
                ).fetchone()
                content = (content_row["content"] if content_row else "") or ""
                tokens = set(_tokenize(f"{doc.title} {doc.relpath} {content[:5000]}"))
                overlap = len(tokens.intersection(q_tokens))
                bonus = overlap / max(1.0, len(q_tokens))
                reranked.append((doc_id, float(base + 0.2 * bonus)))
            ranked = sorted(reranked, key=lambda x: x[1], reverse=True)

        top = ranked[:limit]
        out: List[Candidate] = []
        for doc_id, score in top:
            doc = self._get_document_by_id(doc_id)
            out.append(Candidate(document_id=doc.id, score=float(score), title=doc.title, relpath=doc.relpath, mime=doc.mime))
        return out

    def read_for_answer(
        self,
        candidates: Sequence[Candidate],
        query: str,
        quota: Optional[SourceQuota] = None,
        max_windows: int = 5,
        window_chars: int = 1200,
        overlap_chars: int = 200,
    ) -> List[ReadWindow]:
        quota = quota or SourceQuota()
        picked_docs = list(candidates)[: quota.max_sources]
        windows: List[ReadWindow] = []
        per_doc_count: Dict[str, int] = {}
        for cand in picked_docs:
            doc = self._get_document_by_id(cand.document_id)
            doc_windows = self._reader.read_windows(
                doc,
                query=query,
                max_windows=max_windows,
                window_chars=window_chars,
                overlap_chars=overlap_chars,
            )
            for w in doc_windows:
                if per_doc_count.get(doc.id, 0) >= quota.max_windows_per_source:
                    break
                windows.append(w)
                per_doc_count[doc.id] = per_doc_count.get(doc.id, 0) + 1
        return windows

    def answer(
        self,
        query: str,
        view: Optional[View] = None,
        quota: Optional[SourceQuota] = None,
        candidate_limit: int = 20,
        use_embeddings: bool = False,
        rerank: bool = False,
    ) -> Answer:
        query = query.strip()
        if not query:
            raise ValidationError("query required")

        if view is not None:
            candidates = self.search(view.query, limit=view.limit, use_embeddings=view.use_embeddings, rerank=view.rerank)
        else:
            candidates = self.search(query, limit=candidate_limit, use_embeddings=use_embeddings, rerank=rerank)

        windows = self.read_for_answer(candidates, query=query, quota=quota)

        citations: List[SourceRef] = []
        for w in windows:
            citations.append(SourceRef(document_id=w.document_id, window_id=w.window_id, label=w.label))

        text = self._synthesize_answer(query, windows)

        note_body = self._format_investigation_note(query, candidates, windows, text)
        note = self.create_note(title=f"Investigation: {query}", body=note_body, related_document_id=None)

        inv_id = str(uuid.uuid4())
        now = _utc_now_iso()
        self._store.conn.execute(
            "INSERT INTO investigations(id, created_at, query, answer_text, citations_json, note_id) VALUES(?, ?, ?, ?, ?, ?)",
            (inv_id, now, query, text, json.dumps([c.__dict__ for c in citations]), note.id),
        )
        self._store.conn.commit()

        self._append_journal_event(
            journal_name="investigations",
            kind="answer_created",
            payload={"investigation_id": inv_id, "query": query, "note_id": note.id, "citation_count": len(citations)},
        )

        return Answer(
            answer_id=inv_id,
            created_at=now,
            query=query,
            text=text,
            citations=citations,
            note_id=note.id,
        )

    def _synthesize_answer(self, query: str, windows: Sequence[ReadWindow]) -> str:
        q_tokens = set(_tokenize(query))
        if not windows:
            return "No relevant sources were found in the local knowledge base."

        scored_snips: List[Tuple[float, ReadWindow, str]] = []
        for w in windows:
            lines = [ln.strip() for ln in (w.text or "").splitlines()]
            lines = [ln for ln in lines if ln]
            if not lines:
                continue
            best_line = ""
            best_score = 0.0
            for ln in lines[:200]:
                t = set(_tokenize(ln))
                overlap = len(t.intersection(q_tokens))
                score = overlap / max(1.0, len(q_tokens)) if q_tokens else 0.0
                if score > best_score:
                    best_score = score
                    best_line = ln
            if not best_line:
                best_line = lines[0]
            scored_snips.append((best_score, w, best_line))

        scored_snips.sort(key=lambda x: x[0], reverse=True)
        top = scored_snips[: min(6, len(scored_snips))]

        parts: List[str] = []
        parts.append(f"Query: {query}")
        parts.append("")
        parts.append("Findings (with citations):")
        for _, w, snip in top:
            parts.append(f"- {snip} [{w.window_id}]")
        parts.append("")
        parts.append("Sources:")
        for w in windows:
            parts.append(f"- [{w.window_id}] {w.label}")
        return "\n".join(parts).strip()

    def _format_investigation_note(
        self,
        query: str,
        candidates: Sequence[Candidate],
        windows: Sequence[ReadWindow],
        answer_text: str,
    ) -> str:
        lines: List[str] = []
        lines.append(f"Created: {_utc_now_iso()}")
        lines.append(f"Query: {query}")
        lines.append("")
        lines.append("Top candidates:")
        for c in list(candidates)[:20]:
            lines.append(f"- {c.title} ({c.relpath}) score={c.score:.4f} id={c.document_id}")
        lines.append("")
        lines.append("Read windows:")
        for w in windows:
            excerpt = _normalize_whitespace(w.text)
            if len(excerpt) > 400:
                excerpt = excerpt[:400] + "…"
            lines.append(f"- [{w.window_id}] {w.label}")
            lines.append(f"  Excerpt: {excerpt}")
        lines.append("")
        lines.append("Answer:")
        lines.append(answer_text)
        return "\n".join(lines).strip()

    def list_investigations(self, limit: int = 50) -> List[Dict[str, Any]]:
        if limit <= 0:
            raise ValidationError("limit must be positive")
        cur = self._store.conn.execute(
            "SELECT id, created_at, query, note_id FROM investigations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [{"id": r["id"], "created_at": r["created_at"], "query": r["query"], "note_id": r["note_id"]} for r in cur.fetchall()]

    def get_investigation(self, investigation_id: str) -> Dict[str, Any]:
        cur = self._store.conn.execute("SELECT * FROM investigations WHERE id=?", (investigation_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("Investigation not found")
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "query": row["query"],
            "answer_text": row["answer_text"],
            "citations": json.loads(row["citations_json"]),
            "note_id": row["note_id"],
        }


class Agent:
    def __init__(self, kb: KnowledgeBase) -> None:
        self._kb = kb

    @property
    def kb(self) -> KnowledgeBase:
        return self._kb

    def run(
        self,
        query: str,
        view: Optional[View] = None,
        quota: Optional[SourceQuota] = None,
        candidate_limit: int = 20,
        use_embeddings: bool = False,
        rerank: bool = False,
    ) -> Answer:
        return self._kb.answer(
            query=query,
            view=view,
            quota=quota,
            candidate_limit=candidate_limit,
            use_embeddings=use_embeddings,
            rerank=rerank,
        )


class Marginalia:
    def __init__(self, root_dir: str, db_path: str) -> None:
        self._kb = KnowledgeBase(root_dir=root_dir, db_path=db_path)
        self._agent = Agent(self._kb)

    @property
    def kb(self) -> KnowledgeBase:
        return self._kb

    @property
    def agent(self) -> Agent:
        return self._agent

    def close(self) -> None:
        self._kb.close()