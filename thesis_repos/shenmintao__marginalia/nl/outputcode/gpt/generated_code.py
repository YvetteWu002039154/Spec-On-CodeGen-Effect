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
    try:
        rel = path.resolve().relative_to(root.resolve())
    except Exception:
        raise ValueError("Path must be within the library root")
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


def _normalize_text(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return s


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9_]+", text.lower())


def _detect_mime(path: Path) -> str:
    mt, _ = mimetypes.guess_type(str(path))
    return mt or "application/octet-stream"


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


@dataclass(frozen=True)
class SourceRef:
    document_id: str
    relpath: str
    kind: str
    locator: str
    excerpt: str


@dataclass(frozen=True)
class Candidate:
    document_id: str
    score: float
    reason: str


@dataclass(frozen=True)
class Window:
    document_id: str
    relpath: str
    kind: str
    locator: str
    text: str


class Metadata:
    def __init__(self, **fields: Any) -> None:
        self._fields: Dict[str, Any] = dict(fields)

    def get(self, key: str, default: Any = None) -> Any:
        return self._fields.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if not isinstance(key, str) or not key:
            raise ValidationError("Metadata key must be a non-empty string")
        self._fields[key] = value

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._fields)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Metadata":
        if not isinstance(d, dict):
            raise ValidationError("Metadata must be a dict")
        return cls(**d)


class TagSet:
    def __init__(self, tags: Optional[Iterable[str]] = None) -> None:
        self._tags: Dict[str, None] = {}
        if tags:
            for t in tags:
                self.add(t)

    def add(self, tag: str) -> None:
        if not isinstance(tag, str) or not tag.strip():
            raise ValidationError("Tag must be a non-empty string")
        t = tag.strip()
        self._tags[t] = None

    def remove(self, tag: str) -> None:
        self._tags.pop(tag, None)

    def has(self, tag: str) -> bool:
        return tag in self._tags

    def to_list(self) -> List[str]:
        return sorted(self._tags.keys())

    @classmethod
    def from_list(cls, tags: Sequence[str]) -> "TagSet":
        return cls(tags)


class Journal:
    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []

    def add(self, event: str, **data: Any) -> None:
        if not isinstance(event, str) or not event:
            raise ValidationError("Journal event must be a non-empty string")
        entry = {"ts": _iso(_utc_now()), "event": event, "data": data}
        self._entries.append(entry)

    def entries(self) -> List[Dict[str, Any]]:
        return list(self._entries)

    def to_json(self) -> str:
        return json.dumps(self._entries, ensure_ascii=False)

    @classmethod
    def from_json(cls, s: str) -> "Journal":
        j = cls()
        if not s:
            return j
        data = json.loads(s)
        if not isinstance(data, list):
            raise ValidationError("Journal JSON must be a list")
        j._entries = data
        return j


class Document:
    def __init__(
        self,
        document_id: str,
        relpath: str,
        mime: str,
        size_bytes: int,
        sha256: str,
        created_at: str,
        updated_at: str,
        metadata: Optional[Metadata] = None,
        tags: Optional[TagSet] = None,
        journal: Optional[Journal] = None,
    ) -> None:
        if not document_id:
            raise ValidationError("document_id required")
        if not relpath:
            raise ValidationError("relpath required")
        self._id = document_id
        self._relpath = relpath
        self._mime = mime
        self._size_bytes = int(size_bytes)
        self._sha256 = sha256
        self._created_at = created_at
        self._updated_at = updated_at
        self._metadata = metadata or Metadata()
        self._tags = tags or TagSet()
        self._journal = journal or Journal()

    @property
    def id(self) -> str:
        return self._id

    @property
    def relpath(self) -> str:
        return self._relpath

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
    def metadata(self) -> Metadata:
        return self._metadata

    @property
    def tags(self) -> TagSet:
        return self._tags

    @property
    def journal(self) -> Journal:
        return self._journal

    def touch_updated(self) -> None:
        self._updated_at = _iso(_utc_now())

    def to_record(self) -> Dict[str, Any]:
        return {
            "id": self._id,
            "relpath": self._relpath,
            "mime": self._mime,
            "size_bytes": self._size_bytes,
            "sha256": self._sha256,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "metadata_json": json.dumps(self._metadata.to_dict(), ensure_ascii=False),
            "tags_json": json.dumps(self._tags.to_list(), ensure_ascii=False),
            "journal_json": self._journal.to_json(),
        }

    @classmethod
    def from_record(cls, r: Dict[str, Any]) -> "Document":
        md = Metadata.from_dict(json.loads(r.get("metadata_json") or "{}"))
        tags = TagSet.from_list(json.loads(r.get("tags_json") or "[]"))
        journal = Journal.from_json(r.get("journal_json") or "[]")
        return cls(
            document_id=r["id"],
            relpath=r["relpath"],
            mime=r["mime"],
            size_bytes=r["size_bytes"],
            sha256=r["sha256"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            metadata=md,
            tags=tags,
            journal=journal,
        )


class Catalog:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                relpath TEXT UNIQUE NOT NULL,
                mime TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                journal_json TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                sources_json TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS relations (
                id TEXT PRIMARY KEY,
                a_id TEXT NOT NULL,
                b_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                score REAL NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(a_id, b_id, kind)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS fts_docs (
                doc_id TEXT PRIMARY KEY,
                content TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_index
            USING fts5(doc_id, content, tokenize='porter')
            """
        )
        self._conn.commit()

    def upsert_document(self, doc: Document) -> None:
        r = doc.to_record()
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO documents (id, relpath, mime, size_bytes, sha256, created_at, updated_at, metadata_json, tags_json, journal_json)
            VALUES (:id, :relpath, :mime, :size_bytes, :sha256, :created_at, :updated_at, :metadata_json, :tags_json, :journal_json)
            ON CONFLICT(id) DO UPDATE SET
                relpath=excluded.relpath,
                mime=excluded.mime,
                size_bytes=excluded.size_bytes,
                sha256=excluded.sha256,
                updated_at=excluded.updated_at,
                metadata_json=excluded.metadata_json,
                tags_json=excluded.tags_json,
                journal_json=excluded.journal_json
            """,
            r,
        )
        self._conn.commit()

    def get_document_by_id(self, document_id: str) -> Document:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("Document not found")
        return Document.from_record(dict(row))

    def get_document_by_relpath(self, relpath: str) -> Document:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM documents WHERE relpath = ?", (relpath,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("Document not found")
        return Document.from_record(dict(row))

    def list_documents(self) -> List[Document]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM documents ORDER BY relpath ASC")
        return [Document.from_record(dict(r)) for r in cur.fetchall()]

    def delete_document(self, document_id: str) -> None:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        cur.execute("DELETE FROM fts_docs WHERE doc_id = ?", (document_id,))
        cur.execute("DELETE FROM fts_index WHERE doc_id = ?", (document_id,))
        cur.execute("DELETE FROM relations WHERE a_id = ? OR b_id = ?", (document_id, document_id))
        self._conn.commit()

    def upsert_fts_content(self, document_id: str, content: str) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO fts_docs (doc_id, content) VALUES (?, ?)
            ON CONFLICT(doc_id) DO UPDATE SET content=excluded.content
            """,
            (document_id, content),
        )
        cur.execute("DELETE FROM fts_index WHERE doc_id = ?", (document_id,))
        cur.execute("INSERT INTO fts_index (doc_id, content) VALUES (?, ?)", (document_id, content))
        self._conn.commit()

    def fts_search(self, query: str, limit: int) -> List[Tuple[str, float]]:
        if not isinstance(query, str) or not query.strip():
            return []
        if limit <= 0:
            return []
        cur = self._conn.cursor()
        try:
            cur.execute(
                """
                SELECT doc_id, bm25(fts_index) AS score
                FROM fts_index
                WHERE fts_index MATCH ?
                ORDER BY score ASC
                LIMIT ?
                """,
                (query, limit),
            )
            rows = cur.fetchall()
        except sqlite3.OperationalError as e:
            raise SearchError(str(e))
        results: List[Tuple[str, float]] = []
        for r in rows:
            doc_id = r["doc_id"]
            score = float(r["score"])
            results.append((doc_id, -score))
        return results

    def add_relation(self, a_id: str, b_id: str, kind: str, score: float) -> None:
        if not a_id or not b_id or a_id == b_id:
            raise ValidationError("Invalid relation endpoints")
        if not kind:
            raise ValidationError("Relation kind required")
        rid = str(uuid.uuid4())
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO relations (id, a_id, b_id, kind, score, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(a_id, b_id, kind) DO UPDATE SET score=excluded.score
            """,
            (rid, a_id, b_id, kind, float(score), _iso(_utc_now())),
        )
        self._conn.commit()

    def list_relations_for(self, document_id: str) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT * FROM relations
            WHERE a_id = ? OR b_id = ?
            ORDER BY score DESC
            """,
            (document_id, document_id),
        )
        return [dict(r) for r in cur.fetchall()]

    def upsert_note(self, note: "InvestigationNote") -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO notes (id, created_at, updated_at, title, body, tags_json, sources_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                updated_at=excluded.updated_at,
                title=excluded.title,
                body=excluded.body,
                tags_json=excluded.tags_json,
                sources_json=excluded.sources_json
            """,
            (
                note.id,
                note.created_at,
                note.updated_at,
                note.title,
                note.body,
                json.dumps(note.tags.to_list(), ensure_ascii=False),
                json.dumps([s.__dict__ for s in note.sources], ensure_ascii=False),
            ),
        )
        self._conn.commit()

    def list_notes(self) -> List["InvestigationNote"]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM notes ORDER BY updated_at DESC")
        notes: List[InvestigationNote] = []
        for r in cur.fetchall():
            tags = TagSet.from_list(json.loads(r["tags_json"] or "[]"))
            sources_raw = json.loads(r["sources_json"] or "[]")
            sources = [SourceRef(**sr) for sr in sources_raw]
            notes.append(
                InvestigationNote(
                    note_id=r["id"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                    title=r["title"],
                    body=r["body"],
                    tags=tags,
                    sources=sources,
                )
            )
        return notes


class Ingestor:
    def __init__(self, root: Path) -> None:
        self._root = root

    def _read_text_file(self, path: Path, max_bytes: int) -> str:
        data = path.read_bytes()
        if len(data) > max_bytes:
            data = data[:max_bytes]
        try:
            return _normalize_text(data.decode("utf-8"))
        except UnicodeDecodeError:
            return _normalize_text(data.decode("latin-1", errors="replace"))

    def extract_text(self, path: Path, max_bytes: int = 5_000_000) -> str:
        if not path.exists() or not path.is_file():
            raise IngestError("File not found")
        mime = _detect_mime(path)
        suffix = path.suffix.lower()

        if suffix in {".txt", ".md", ".markdown", ".log", ".csv", ".tsv", ".json", ".yaml", ".yml"}:
            return self._read_text_file(path, max_bytes)

        if suffix in {".zip"}:
            return self._extract_zip_listing(path, max_members=2000)

        if suffix in {".pdf", ".docx", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}:
            return f"[binary:{mime}] {path.name}"

        return f"[binary:{mime}] {path.name}"

    def _extract_zip_listing(self, path: Path, max_members: int) -> str:
        out: List[str] = []
        try:
            with zipfile.ZipFile(str(path), "r") as z:
                names = z.namelist()
                if len(names) > max_members:
                    names = names[:max_members]
                out.append(f"[archive:zip] {path.name}")
                for n in names:
                    out.append(n)
        except Exception as e:
            raise IngestError(str(e))
        return "\n".join(out)


class WindowReader:
    def __init__(self, root: Path, ingestor: Ingestor) -> None:
        self._root = root
        self._ingestor = ingestor

    def read_lines(self, relpath: str, start_line: int, end_line: int, max_bytes: int = 2_000_000) -> Window:
        if start_line < 1 or end_line < start_line:
            raise ValidationError("Invalid line range")
        path = (self._root / relpath).resolve()
        if not path.exists() or not path.is_file():
            raise ReadError("File not found")
        text = self._ingestor.extract_text(path, max_bytes=max_bytes)
        lines = _normalize_text(text).split("\n")
        s = start_line - 1
        e = min(end_line, len(lines))
        slice_text = "\n".join(lines[s:e])
        return Window(
            document_id="",
            relpath=relpath,
            kind="lines",
            locator=f"lines:{start_line}-{end_line}",
            text=slice_text,
        )

    def read_text_window(self, relpath: str, start: int, length: int, max_bytes: int = 2_000_000) -> Window:
        if start < 0 or length <= 0:
            raise ValidationError("Invalid window")
        path = (self._root / relpath).resolve()
        if not path.exists() or not path.is_file():
            raise ReadError("File not found")
        text = self._ingestor.extract_text(path, max_bytes=max_bytes)
        t = _normalize_text(text)
        w = t[start : start + length]
        return Window(
            document_id="",
            relpath=relpath,
            kind="chars",
            locator=f"chars:{start}+{length}",
            text=w,
        )

    def read_archive_member(self, relpath: str, member: str, max_bytes: int = 2_000_000) -> Window:
        path = (self._root / relpath).resolve()
        if not path.exists() or not path.is_file():
            raise ReadError("File not found")
        if path.suffix.lower() != ".zip":
            raise ReadError("Not a supported archive")
        try:
            with zipfile.ZipFile(str(path), "r") as z:
                with z.open(member, "r") as f:
                    data = f.read(max_bytes)
        except KeyError:
            raise ReadError("Archive member not found")
        except Exception as e:
            raise ReadError(str(e))
        try:
            text = _normalize_text(data.decode("utf-8"))
        except UnicodeDecodeError:
            text = _normalize_text(data.decode("latin-1", errors="replace"))
        return Window(
            document_id="",
            relpath=relpath,
            kind="archive_member",
            locator=f"zip:{member}",
            text=text,
        )


class RelationMiner:
    def __init__(self) -> None:
        pass

    def mine(self, doc_id: str, content: str, other_docs: Sequence[Tuple[str, str]]) -> List[Tuple[str, str, float]]:
        tokens = _tokenize(content)
        if not tokens:
            return []
        tf: Dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        top = sorted(tf.items(), key=lambda x: x[1], reverse=True)[:50]
        vocab = {t for t, _ in top}
        if not vocab:
            return []

        results: List[Tuple[str, str, float]] = []
        for other_id, other_content in other_docs:
            if other_id == doc_id:
                continue
            other_tokens = set(_tokenize(other_content))
            inter = len(vocab.intersection(other_tokens))
            if inter <= 0:
                continue
            score = inter / math.sqrt(len(vocab) * max(1, len(other_tokens)))
            if score > 0:
                results.append((doc_id, other_id, float(score)))
        results.sort(key=lambda x: x[2], reverse=True)
        return results[:25]


class View:
    def __init__(self, name: str, query: str, tags: Optional[Iterable[str]] = None) -> None:
        if not name:
            raise ValidationError("View name required")
        if not isinstance(query, str):
            raise ValidationError("View query must be a string")
        self._name = name
        self._query = query
        self._tags = TagSet(tags)

    @property
    def name(self) -> str:
        return self._name

    @property
    def query(self) -> str:
        return self._query

    @property
    def tags(self) -> TagSet:
        return self._tags


class SourceQuota:
    def __init__(self, max_sources: int = 8, max_windows_per_source: int = 2) -> None:
        if max_sources <= 0:
            raise ValidationError("max_sources must be > 0")
        if max_windows_per_source <= 0:
            raise ValidationError("max_windows_per_source must be > 0")
        self.max_sources = int(max_sources)
        self.max_windows_per_source = int(max_windows_per_source)


class RecallConfig:
    def __init__(self, lexical_limit: int = 30, use_embeddings: bool = False, use_rerank: bool = False) -> None:
        if lexical_limit <= 0:
            raise ValidationError("lexical_limit must be > 0")
        self.lexical_limit = int(lexical_limit)
        self.use_embeddings = bool(use_embeddings)
        self.use_rerank = bool(use_rerank)


class RecallEngine:
    def __init__(self, catalog: Catalog) -> None:
        self._catalog = catalog

    def recall(self, query: str, config: RecallConfig) -> List[Candidate]:
        scored = self._catalog.fts_search(query, limit=config.lexical_limit)
        cands = [Candidate(document_id=doc_id, score=score, reason="lexical") for doc_id, score in scored]
        cands.sort(key=lambda c: c.score, reverse=True)
        return cands


class InvestigationNote:
    def __init__(
        self,
        note_id: str,
        created_at: str,
        updated_at: str,
        title: str,
        body: str,
        tags: Optional[TagSet] = None,
        sources: Optional[List[SourceRef]] = None,
    ) -> None:
        if not note_id:
            raise ValidationError("note_id required")
        if not title:
            raise ValidationError("title required")
        self._id = note_id
        self._created_at = created_at
        self._updated_at = updated_at
        self._title = title
        self._body = body
        self._tags = tags or TagSet()
        self._sources = sources or []

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
    def tags(self) -> TagSet:
        return self._tags

    @property
    def sources(self) -> List[SourceRef]:
        return list(self._sources)

    def touch_updated(self) -> None:
        self._updated_at = _iso(_utc_now())


class CitedAnswer:
    def __init__(self, answer: str, sources: List[SourceRef], report: Optional[str] = None) -> None:
        self._answer = answer
        self._sources = list(sources)
        self._report = report or ""

    @property
    def answer(self) -> str:
        return self._answer

    @property
    def sources(self) -> List[SourceRef]:
        return list(self._sources)

    @property
    def report(self) -> str:
        return self._report


class Agent:
    def __init__(self, library: "Library") -> None:
        self._library = library

    def answer(self, question: str, recall: Optional[RecallConfig] = None, quota: Optional[SourceQuota] = None) -> CitedAnswer:
        if not isinstance(question, str) or not question.strip():
            raise ValidationError("Question must be a non-empty string")
        recall = recall or RecallConfig()
        quota = quota or SourceQuota()

        candidates = self._library.recall(question, recall)
        if not candidates:
            ans = "I couldn't find relevant material in your library."
            note = self._library.write_note(
                title="Investigation: no results",
                body=f"Q: {question}\n\nA: {ans}",
                tags=["investigation"],
                sources=[],
            )
            return CitedAnswer(ans, [], report=f"note_id={note.id}")

        selected = candidates[: quota.max_sources]
        windows: List[Window] = []
        sources: List[SourceRef] = []

        for cand in selected:
            doc = self._library.catalog.get_document_by_id(cand.document_id)
            relpath = doc.relpath
            path = (self._library.root / relpath)
            content = self._library.ingestor.extract_text(path, max_bytes=2_000_000)
            content = _normalize_text(content)
            lines = content.split("\n")
            if not lines:
                continue
            per_source = min(quota.max_windows_per_source, 2)
            if per_source == 1:
                start = 1
                end = min(40, len(lines))
                wtext = "\n".join(lines[start - 1 : end])
                windows.append(Window(doc.id, relpath, "lines", f"lines:{start}-{end}", wtext))
            else:
                start1, end1 = 1, min(30, len(lines))
                start2 = max(1, len(lines) - 29)
                end2 = len(lines)
                w1 = "\n".join(lines[start1 - 1 : end1])
                w2 = "\n".join(lines[start2 - 1 : end2])
                windows.append(Window(doc.id, relpath, "lines", f"lines:{start1}-{end1}", w1))
                if start2 > end1:
                    windows.append(Window(doc.id, relpath, "lines", f"lines:{start2}-{end2}", w2))

        if not windows:
            ans = "I found candidate files but couldn't read usable sections."
            note = self._library.write_note(
                title="Investigation: unreadable sources",
                body=f"Q: {question}\n\nA: {ans}",
                tags=["investigation"],
                sources=[],
            )
            return CitedAnswer(ans, [], report=f"note_id={note.id}")

        assembled: List[str] = []
        for i, w in enumerate(windows, start=1):
            excerpt = w.text.strip()
            if len(excerpt) > 800:
                excerpt = excerpt[:800].rstrip() + "…"
            sources.append(
                SourceRef(
                    document_id=w.document_id,
                    relpath=w.relpath,
                    kind=w.kind,
                    locator=w.locator,
                    excerpt=excerpt,
                )
            )
            assembled.append(f"[S{i}] {w.relpath} ({w.locator})\n{excerpt}")

        answer_text = self._synthesize(question, assembled)
        report = self._build_report(question, candidates, windows)

        note = self._library.write_note(
            title="Investigation: answer",
            body=f"Q: {question}\n\nA:\n{answer_text}\n\nSources:\n" + "\n".join(
                [f"- [S{i+1}] {s.relpath} {s.locator}" for i, s in enumerate(sources)]
            ),
            tags=["investigation"],
            sources=sources,
        )
        return CitedAnswer(answer_text, sources, report=report + f"\nnote_id={note.id}")

    def _synthesize(self, question: str, assembled_sources: List[str]) -> str:
        q = question.strip()
        src = "\n\n".join(assembled_sources)
        return (
            f"{q}\n\n"
            f"Relevant excerpts:\n{src}\n\n"
            f"Answer (with citations):\n"
            f"- Based on [S1] and related excerpts, the library contains material relevant to your question.\n"
            f"- Review the cited windows above for exact wording and context.\n"
        )

    def _build_report(self, question: str, candidates: List[Candidate], windows: List[Window]) -> str:
        lines: List[str] = []
        lines.append(f"question={question}")
        lines.append(f"candidates={len(candidates)}")
        lines.append(f"windows={len(windows)}")
        if candidates:
            top = candidates[:10]
            lines.append("top_candidates=" + ",".join([f"{c.document_id}:{c.score:.3f}" for c in top]))
        return "\n".join(lines)


class Library:
    def __init__(self, root: Union[str, Path]) -> None:
        self._root = Path(root).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._state_dir = self._root / ".marginalia"
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._state_dir / "catalog.sqlite"
        self._catalog = Catalog(self._db_path)
        self._ingestor = Ingestor(self._root)
        self._reader = WindowReader(self._root, self._ingestor)
        self._recall = RecallEngine(self._catalog)
        self._miner = RelationMiner()
        self._views: Dict[str, View] = {}

    @property
    def root(self) -> Path:
        return self._root

    @property
    def catalog(self) -> Catalog:
        return self._catalog

    @property
    def ingestor(self) -> Ingestor:
        return self._ingestor

    @property
    def reader(self) -> WindowReader:
        return self._reader

    def close(self) -> None:
        self._catalog.close()

    def ingest_path(self, path: Union[str, Path], rel_destination: Optional[str] = None, tags: Optional[Iterable[str]] = None) -> Document:
        src = Path(path).expanduser().resolve()
        if not src.exists() or not src.is_file():
            raise IngestError("Source file not found")
        if rel_destination:
            if rel_destination.startswith("/") or rel_destination.startswith("\\"):
                raise ValidationError("rel_destination must be relative")
            dest_rel = rel_destination.replace("\\", "/")
        else:
            dest_rel = src.name
        dest = (self._root / dest_rel).resolve()
        if not str(dest).startswith(str(self._root)):
            raise ValidationError("Destination must be within library root")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src != dest:
            shutil.copy2(str(src), str(dest))

        relpath = _safe_relpath(dest, self._root)
        mime = _detect_mime(dest)
        size_bytes = dest.stat().st_size
        sha = _sha256_file(dest)
        now = _iso(_utc_now())

        try:
            existing = self._catalog.get_document_by_relpath(relpath)
            doc_id = existing.id
            created_at = existing.created_at
            md = existing.metadata
            tset = existing.tags
            j = existing.journal
            j.add("ingest_update", relpath=relpath, sha256=sha, size_bytes=size_bytes)
        except NotFoundError:
            doc_id = str(uuid.uuid4())
            created_at = now
            md = Metadata()
            tset = TagSet()
            j = Journal()
            j.add("ingest_create", relpath=relpath, sha256=sha, size_bytes=size_bytes)

        if tags:
            for t in tags:
                tset.add(t)

        doc = Document(
            document_id=doc_id,
            relpath=relpath,
            mime=mime,
            size_bytes=size_bytes,
            sha256=sha,
            created_at=created_at,
            updated_at=now,
            metadata=md,
            tags=tset,
            journal=j,
        )
        self._catalog.upsert_document(doc)

        content = self._ingestor.extract_text(dest, max_bytes=5_000_000)
        self._catalog.upsert_fts_content(doc.id, content)

        self._update_relations_for(doc.id, content)
        return doc

    def ingest_folder(self, folder: Union[str, Path], include_hidden: bool = False) -> List[Document]:
        base = Path(folder).expanduser().resolve()
        if not base.exists() or not base.is_dir():
            raise IngestError("Folder not found")
        docs: List[Document] = []
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if not include_hidden:
                parts = p.relative_to(base).parts
                if any(part.startswith(".") for part in parts):
                    continue
            rel = str(p.relative_to(base)).replace("\\", "/")
            docs.append(self.ingest_path(p, rel_destination=rel))
        return docs

    def _update_relations_for(self, doc_id: str, content: str) -> None:
        others: List[Tuple[str, str]] = []
        for d in self._catalog.list_documents():
            if d.id == doc_id:
                continue
            cur = self._catalog._conn.cursor()
            cur.execute("SELECT content FROM fts_docs WHERE doc_id = ?", (d.id,))
            row = cur.fetchone()
            if row:
                others.append((d.id, row["content"]))
        rels = self._miner.mine(doc_id, content, others)
        for a, b, score in rels:
            self._catalog.add_relation(a, b, "lexical_overlap", score)

    def add_tag(self, document_id: str, tag: str) -> None:
        doc = self._catalog.get_document_by_id(document_id)
        doc.tags.add(tag)
        doc.journal.add("tag_add", tag=tag)
        doc.touch_updated()
        self._catalog.upsert_document(doc)

    def remove_tag(self, document_id: str, tag: str) -> None:
        doc = self._catalog.get_document_by_id(document_id)
        doc.tags.remove(tag)
        doc.journal.add("tag_remove", tag=tag)
        doc.touch_updated()
        self._catalog.upsert_document(doc)

    def set_metadata(self, document_id: str, key: str, value: Any) -> None:
        doc = self._catalog.get_document_by_id(document_id)
        doc.metadata.set(key, value)
        doc.journal.add("metadata_set", key=key)
        doc.touch_updated()
        self._catalog.upsert_document(doc)

    def create_view(self, name: str, query: str, tags: Optional[Iterable[str]] = None) -> View:
        v = View(name=name, query=query, tags=tags)
        self._views[v.name] = v
        return v

    def get_view(self, name: str) -> View:
        v = self._views.get(name)
        if not v:
            raise NotFoundError("View not found")
        return v

    def list_views(self) -> List[View]:
        return list(self._views.values())

    def run_view(self, name: str, limit: int = 50) -> List[Document]:
        v = self.get_view(name)
        cands = self.recall(v.query, RecallConfig(lexical_limit=max(1, limit)))
        docs: List[Document] = []
        for c in cands[:limit]:
            d = self._catalog.get_document_by_id(c.document_id)
            if v.tags.to_list():
                if not all(d.tags.has(t) for t in v.tags.to_list()):
                    continue
            docs.append(d)
        return docs

    def recall(self, query: str, config: Optional[RecallConfig] = None) -> List[Candidate]:
        config = config or RecallConfig()
        return self._recall.recall(query, config)

    def read_document_lines(self, document_id: str, start_line: int, end_line: int) -> Window:
        doc = self._catalog.get_document_by_id(document_id)
        w = self._reader.read_lines(doc.relpath, start_line, end_line)
        return Window(doc.id, doc.relpath, w.kind, w.locator, w.text)

    def read_document_text_window(self, document_id: str, start: int, length: int) -> Window:
        doc = self._catalog.get_document_by_id(document_id)
        w = self._reader.read_text_window(doc.relpath, start, length)
        return Window(doc.id, doc.relpath, w.kind, w.locator, w.text)

    def read_archive_member(self, document_id: str, member: str) -> Window:
        doc = self._catalog.get_document_by_id(document_id)
        w = self._reader.read_archive_member(doc.relpath, member)
        return Window(doc.id, doc.relpath, w.kind, w.locator, w.text)

    def write_note(self, title: str, body: str, tags: Optional[Iterable[str]] = None, sources: Optional[List[SourceRef]] = None) -> InvestigationNote:
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("title required")
        if not isinstance(body, str):
            raise ValidationError("body must be a string")
        now = _iso(_utc_now())
        note = InvestigationNote(
            note_id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            title=title.strip(),
            body=body,
            tags=TagSet(tags),
            sources=sources or [],
        )
        self._catalog.upsert_note(note)
        return note

    def list_notes(self) -> List[InvestigationNote]:
        return self._catalog.list_notes()

    def agent(self) -> Agent:
        return Agent(self)


__all__ = [
    "MarginaliaError",
    "ValidationError",
    "NotFoundError",
    "IngestError",
    "SearchError",
    "ReadError",
    "AnswerError",
    "SourceRef",
    "Candidate",
    "Window",
    "Metadata",
    "TagSet",
    "Journal",
    "Document",
    "Catalog",
    "Ingestor",
    "WindowReader",
    "RelationMiner",
    "View",
    "SourceQuota",
    "RecallConfig",
    "RecallEngine",
    "InvestigationNote",
    "CitedAnswer",
    "Agent",
    "Library",
]