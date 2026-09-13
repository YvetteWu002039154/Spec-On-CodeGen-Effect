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


class StorageError(MarginaliaError):
    pass


def _utc_now_iso() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _norm_path(path: str) -> str:
    return os.path.normpath(path).replace("\\", "/")


def _safe_relpath(path: str, root: str) -> str:
    root_abs = os.path.abspath(root)
    path_abs = os.path.abspath(path)
    if not (path_abs == root_abs or path_abs.startswith(root_abs + os.sep)):
        raise ValidationError("Path must be within root")
    rel = os.path.relpath(path_abs, root_abs)
    return _norm_path(rel)


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _guess_mime(path: str) -> str:
    mt, _ = mimetypes.guess_type(path)
    return mt or "application/octet-stream"


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9_]+", text.lower())


def _truncate(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: max(0, n - 1)] + "…"


@dataclass(frozen=True)
class DocumentRef:
    doc_id: str
    rel_path: str
    mime_type: str
    size_bytes: int
    sha256: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class WindowRef:
    window_id: str
    doc_id: str
    kind: str
    locator: str
    content: str
    created_at: str


@dataclass(frozen=True)
class Citation:
    doc_id: str
    rel_path: str
    window_id: str
    kind: str
    locator: str
    quote: str


@dataclass(frozen=True)
class Answer:
    answer_id: str
    question: str
    response: str
    citations: List[Citation]
    created_at: str


@dataclass(frozen=True)
class Note:
    note_id: str
    title: str
    body: str
    tags: List[str]
    related_doc_ids: List[str]
    created_at: str


class SQLiteStore:
    def __init__(self, db_path: str):
        self._db_path = db_path
        _ensure_dir(os.path.dirname(os.path.abspath(db_path)) or ".")
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")
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
                doc_id TEXT PRIMARY KEY,
                rel_path TEXT UNIQUE NOT NULL,
                abs_path TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tags (
                tag TEXT PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS document_tags (
                doc_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (doc_id, tag),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (tag) REFERENCES tags(tag) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS catalogs (
                catalog_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                query_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS windows (
                window_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                locator TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS lexical_index (
                doc_id TEXT NOT NULL,
                token TEXT NOT NULL,
                freq INTEGER NOT NULL,
                PRIMARY KEY (doc_id, token),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS relations (
                relation_id TEXT PRIMARY KEY,
                src_doc_id TEXT NOT NULL,
                dst_doc_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                evidence TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (src_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (dst_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS journals (
                entry_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notes (
                note_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                related_doc_ids_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_documents_rel_path ON documents(rel_path);
            CREATE INDEX IF NOT EXISTS idx_lexical_token ON lexical_index(token);
            CREATE INDEX IF NOT EXISTS idx_windows_doc ON windows(doc_id);
            CREATE INDEX IF NOT EXISTS idx_relations_src ON relations(src_doc_id);
            CREATE INDEX IF NOT EXISTS idx_relations_dst ON relations(dst_doc_id);
            """
        )
        self._conn.commit()

    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        try:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            return cur
        except sqlite3.Error as e:
            raise StorageError(str(e)) from e

    def executemany(self, sql: str, seq_of_params: Iterable[Sequence[Any]]) -> sqlite3.Cursor:
        try:
            cur = self._conn.cursor()
            cur.executemany(sql, seq_of_params)
            return cur
        except sqlite3.Error as e:
            raise StorageError(str(e)) from e

    def commit(self) -> None:
        try:
            self._conn.commit()
        except sqlite3.Error as e:
            raise StorageError(str(e)) from e

    def rollback(self) -> None:
        try:
            self._conn.rollback()
        except sqlite3.Error:
            pass


class FileIngestor:
    def __init__(self, root_dir: str):
        self._root_dir = os.path.abspath(root_dir)
        _ensure_dir(self._root_dir)

    @property
    def root_dir(self) -> str:
        return self._root_dir

    def ingest_path(self, src_path: str, dest_rel_path: Optional[str] = None) -> str:
        src_path_abs = os.path.abspath(src_path)
        if not os.path.exists(src_path_abs):
            raise NotFoundError("Source path not found")

        if dest_rel_path is None:
            base = os.path.basename(src_path_abs)
            dest_rel_path = base
        dest_rel_path = _norm_path(dest_rel_path).lstrip("/")

        dest_abs = os.path.join(self._root_dir, dest_rel_path)
        dest_abs = os.path.abspath(dest_abs)
        _safe_relpath(dest_abs, self._root_dir)

        _ensure_dir(os.path.dirname(dest_abs))
        if os.path.isdir(src_path_abs):
            if os.path.exists(dest_abs):
                raise ValidationError("Destination already exists")
            shutil.copytree(src_path_abs, dest_abs)
        else:
            shutil.copy2(src_path_abs, dest_abs)
        return dest_abs

    def list_files(self) -> List[str]:
        out: List[str] = []
        for dirpath, _, filenames in os.walk(self._root_dir):
            for fn in filenames:
                abs_path = os.path.join(dirpath, fn)
                rel = _safe_relpath(abs_path, self._root_dir)
                out.append(rel)
        out.sort()
        return out


class ContentExtractor:
    def __init__(self, max_bytes: int = 5 * 1024 * 1024):
        self._max_bytes = max_bytes

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    def extract_text(self, abs_path: str) -> str:
        if not os.path.exists(abs_path):
            raise NotFoundError("File not found")
        size = os.path.getsize(abs_path)
        if size > self._max_bytes:
            raise ValidationError("File too large to extract")
        mime = _guess_mime(abs_path)
        ext = os.path.splitext(abs_path)[1].lower()

        if ext in (".md", ".markdown", ".txt", ".log", ".csv", ".tsv", ".json", ".yaml", ".yml"):
            return self._read_text(abs_path)
        if ext in (".pdf", ".docx", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"):
            return f"[binary:{mime}] {os.path.basename(abs_path)}"
        if ext in (".zip",):
            return self._summarize_zip(abs_path)
        return self._read_text(abs_path)

    def _read_text(self, abs_path: str) -> str:
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                with open(abs_path, "r", encoding=enc, errors="strict") as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def _summarize_zip(self, abs_path: str) -> str:
        try:
            with zipfile.ZipFile(abs_path, "r") as zf:
                names = zf.namelist()
                names = names[:500]
                return "[archive:zip]\n" + "\n".join(names)
        except zipfile.BadZipFile:
            return "[archive:zip] (unreadable)"


class LexicalIndexer:
    def __init__(self):
        pass

    def build_index(self, text: str) -> Dict[str, int]:
        tokens = _tokenize(text)
        freq: Dict[str, int] = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1
        return freq


class RelationMiner:
    def __init__(self):
        self._link_re = re.compile(r"\[\[([^\]]+)\]\]|\bhttps?://\S+|\bfile:([^\s]+)", re.IGNORECASE)

    def mine(self, doc_id: str, text: str, path_lookup: Dict[str, str]) -> List[Tuple[str, str, str]]:
        relations: List[Tuple[str, str, str]] = []
        for m in self._link_re.finditer(text):
            target = m.group(1) or m.group(0) or m.group(2) or ""
            target = target.strip()
            if not target:
                continue
            dst = path_lookup.get(target)
            if dst and dst != doc_id:
                relations.append((doc_id, dst, target))
        return relations


class WindowReader:
    def __init__(self, extractor: ContentExtractor):
        self._extractor = extractor

    def read_windows(
        self,
        abs_path: str,
        kind: str = "lines",
        start: int = 1,
        end: int = 50,
    ) -> Tuple[str, str]:
        text = self._extractor.extract_text(abs_path)
        if kind == "lines":
            lines = text.splitlines()
            s = max(1, start)
            e = max(s, end)
            s0 = s - 1
            e0 = min(len(lines), e)
            content = "\n".join(lines[s0:e0])
            locator = f"lines:{s}-{e0}"
            return locator, content
        if kind == "chars":
            s = max(0, start)
            e = max(s, end)
            content = text[s:e]
            locator = f"chars:{s}-{e}"
            return locator, content
        raise ValidationError("Unsupported window kind")


class SearchEngine:
    def __init__(self, store: SQLiteStore):
        self._store = store

    def lexical_search(self, query: str, limit: int = 20) -> List[Tuple[str, float]]:
        if limit <= 0:
            return []
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        q_counts: Dict[str, int] = {}
        for t in q_tokens:
            q_counts[t] = q_counts.get(t, 0) + 1

        placeholders = ",".join(["?"] * len(q_counts))
        cur = self._store.execute(
            f"""
            SELECT token, doc_id, freq
            FROM lexical_index
            WHERE token IN ({placeholders})
            """,
            tuple(q_counts.keys()),
        )
        rows = cur.fetchall()
        doc_scores: Dict[str, float] = {}
        for token, doc_id, freq in rows:
            qf = q_counts.get(token, 0)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + float(qf) * math.log(1.0 + float(freq))
        ranked = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:limit]


class Catalog:
    def __init__(self, catalog_id: str, name: str, query: Dict[str, Any], created_at: str):
        self._catalog_id = catalog_id
        self._name = name
        self._query = query
        self._created_at = created_at

    @property
    def catalog_id(self) -> str:
        return self._catalog_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def query(self) -> Dict[str, Any]:
        return dict(self._query)

    @property
    def created_at(self) -> str:
        return self._created_at


class View:
    def __init__(self, name: str, doc_ids: List[str]):
        self._name = name
        self._doc_ids = list(doc_ids)

    @property
    def name(self) -> str:
        return self._name

    @property
    def doc_ids(self) -> List[str]:
        return list(self._doc_ids)


class Journal:
    def __init__(self, store: SQLiteStore):
        self._store = store

    def append(self, kind: str, payload: Dict[str, Any]) -> str:
        entry_id = str(uuid.uuid4())
        created_at = _utc_now_iso()
        self._store.execute(
            "INSERT INTO journals(entry_id, kind, payload_json, created_at) VALUES(?,?,?,?)",
            (entry_id, kind, json.dumps(payload, ensure_ascii=False), created_at),
        )
        self._store.commit()
        return entry_id

    def list(self, limit: int = 100) -> List[Dict[str, Any]]:
        cur = self._store.execute(
            "SELECT entry_id, kind, payload_json, created_at FROM journals ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        out: List[Dict[str, Any]] = []
        for entry_id, kind, payload_json, created_at in cur.fetchall():
            out.append(
                {
                    "entry_id": entry_id,
                    "kind": kind,
                    "payload": json.loads(payload_json),
                    "created_at": created_at,
                }
            )
        return out


class KnowledgeBase:
    def __init__(self, root_dir: str, db_path: str):
        self._root_dir = os.path.abspath(root_dir)
        _ensure_dir(self._root_dir)
        self._store = SQLiteStore(db_path)
        self._ingestor = FileIngestor(self._root_dir)
        self._extractor = ContentExtractor()
        self._indexer = LexicalIndexer()
        self._miner = RelationMiner()
        self._reader = WindowReader(self._extractor)
        self._search = SearchEngine(self._store)
        self._journal = Journal(self._store)

    @property
    def root_dir(self) -> str:
        return self._root_dir

    @property
    def journal(self) -> Journal:
        return self._journal

    def close(self) -> None:
        self._store.close()

    def ingest(self, src_path: str, dest_rel_path: Optional[str] = None, tags: Optional[List[str]] = None) -> DocumentRef:
        dest_abs = self._ingestor.ingest_path(src_path, dest_rel_path=dest_rel_path)
        rel = _safe_relpath(dest_abs, self._root_dir)
        return self.register_existing(rel, tags=tags)

    def register_existing(self, rel_path: str, tags: Optional[List[str]] = None) -> DocumentRef:
        rel_path = _norm_path(rel_path).lstrip("/")
        abs_path = os.path.abspath(os.path.join(self._root_dir, rel_path))
        _safe_relpath(abs_path, self._root_dir)
        if not os.path.exists(abs_path) or os.path.isdir(abs_path):
            raise NotFoundError("File not found")

        mime = _guess_mime(abs_path)
        size = os.path.getsize(abs_path)
        sha = _sha256_file(abs_path)
        now = _utc_now_iso()

        cur = self._store.execute("SELECT doc_id, sha256, created_at FROM documents WHERE rel_path = ?", (rel_path,))
        row = cur.fetchone()
        if row is None:
            doc_id = str(uuid.uuid4())
            created_at = now
            self._store.execute(
                "INSERT INTO documents(doc_id, rel_path, abs_path, mime_type, size_bytes, sha256, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (doc_id, rel_path, abs_path, mime, size, sha, created_at, now),
            )
        else:
            doc_id, old_sha, created_at = row
            self._store.execute(
                "UPDATE documents SET abs_path=?, mime_type=?, size_bytes=?, sha256=?, updated_at=? WHERE doc_id=?",
                (abs_path, mime, size, sha, now, doc_id),
            )

        if tags:
            self.set_tags(doc_id, tags)

        self._reindex_document(doc_id, abs_path)
        self._remine_relations(doc_id, abs_path)

        self._journal.append(
            "ingest",
            {"doc_id": doc_id, "rel_path": rel_path, "mime_type": mime, "size_bytes": size, "sha256": sha},
        )
        self._store.commit()
        return self.get_document(doc_id)

    def get_document(self, doc_id: str) -> DocumentRef:
        cur = self._store.execute(
            "SELECT doc_id, rel_path, mime_type, size_bytes, sha256, created_at, updated_at FROM documents WHERE doc_id=?",
            (doc_id,),
        )
        row = cur.fetchone()
        if not row:
            raise NotFoundError("Document not found")
        return DocumentRef(
            doc_id=row[0],
            rel_path=row[1],
            mime_type=row[2],
            size_bytes=int(row[3]),
            sha256=row[4],
            created_at=row[5],
            updated_at=row[6],
        )

    def get_document_by_path(self, rel_path: str) -> DocumentRef:
        rel_path = _norm_path(rel_path).lstrip("/")
        cur = self._store.execute(
            "SELECT doc_id FROM documents WHERE rel_path=?",
            (rel_path,),
        )
        row = cur.fetchone()
        if not row:
            raise NotFoundError("Document not found")
        return self.get_document(row[0])

    def list_documents(self, limit: int = 1000, offset: int = 0) -> List[DocumentRef]:
        cur = self._store.execute(
            "SELECT doc_id FROM documents ORDER BY rel_path LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [self.get_document(r[0]) for r in cur.fetchall()]

    def delete_document(self, doc_id: str, delete_file: bool = False) -> None:
        doc = self.get_document(doc_id)
        abs_path = os.path.abspath(os.path.join(self._root_dir, doc.rel_path))
        if delete_file and os.path.exists(abs_path):
            os.remove(abs_path)
        self._store.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
        self._store.commit()
        self._journal.append("delete", {"doc_id": doc_id, "rel_path": doc.rel_path, "delete_file": delete_file})

    def set_tags(self, doc_id: str, tags: List[str]) -> None:
        self.get_document(doc_id)
        norm_tags = []
        for t in tags:
            if not isinstance(t, str) or not t.strip():
                continue
            tt = t.strip()
            if len(tt) > 64:
                raise ValidationError("Tag too long")
            norm_tags.append(tt)
        norm_tags = sorted(set(norm_tags))
        self._store.execute("DELETE FROM document_tags WHERE doc_id=?", (doc_id,))
        self._store.executemany("INSERT OR IGNORE INTO tags(tag) VALUES(?)", [(t,) for t in norm_tags])
        self._store.executemany(
            "INSERT INTO document_tags(doc_id, tag) VALUES(?,?)",
            [(doc_id, t) for t in norm_tags],
        )
        self._store.commit()
        self._journal.append("tags", {"doc_id": doc_id, "tags": norm_tags})

    def get_tags(self, doc_id: str) -> List[str]:
        self.get_document(doc_id)
        cur = self._store.execute(
            "SELECT tag FROM document_tags WHERE doc_id=? ORDER BY tag",
            (doc_id,),
        )
        return [r[0] for r in cur.fetchall()]

    def create_catalog(self, name: str, query: Dict[str, Any]) -> Catalog:
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("Catalog name required")
        catalog_id = str(uuid.uuid4())
        created_at = _utc_now_iso()
        self._store.execute(
            "INSERT INTO catalogs(catalog_id, name, query_json, created_at) VALUES(?,?,?,?)",
            (catalog_id, name.strip(), json.dumps(query, ensure_ascii=False), created_at),
        )
        self._store.commit()
        self._journal.append("catalog_create", {"catalog_id": catalog_id, "name": name.strip(), "query": query})
        return Catalog(catalog_id, name.strip(), query, created_at)

    def get_catalog(self, name: str) -> Catalog:
        cur = self._store.execute(
            "SELECT catalog_id, name, query_json, created_at FROM catalogs WHERE name=?",
            (name,),
        )
        row = cur.fetchone()
        if not row:
            raise NotFoundError("Catalog not found")
        return Catalog(row[0], row[1], json.loads(row[2]), row[3])

    def list_catalogs(self) -> List[Catalog]:
        cur = self._store.execute("SELECT catalog_id, name, query_json, created_at FROM catalogs ORDER BY name")
        out: List[Catalog] = []
        for catalog_id, name, query_json, created_at in cur.fetchall():
            out.append(Catalog(catalog_id, name, json.loads(query_json), created_at))
        return out

    def run_catalog(self, name: str, limit: int = 200) -> View:
        cat = self.get_catalog(name)
        q = cat.query
        tags_any = q.get("tags_any")
        tags_all = q.get("tags_all")
        path_prefix = q.get("path_prefix")
        mime_prefix = q.get("mime_prefix")

        sql = "SELECT d.doc_id FROM documents d"
        params: List[Any] = []
        joins: List[str] = []
        wheres: List[str] = []

        if tags_any or tags_all:
            joins.append("JOIN document_tags dt ON dt.doc_id = d.doc_id")

        if path_prefix:
            wheres.append("d.rel_path LIKE ?")
            params.append(_norm_path(str(path_prefix)).lstrip("/") + "%")
        if mime_prefix:
            wheres.append("d.mime_type LIKE ?")
            params.append(str(mime_prefix) + "%")

        if tags_any:
            ta = [t.strip() for t in tags_any if isinstance(t, str) and t.strip()]
            if ta:
                wheres.append("dt.tag IN (" + ",".join(["?"] * len(ta)) + ")")
                params.extend(ta)

        if tags_all:
            ta = [t.strip() for t in tags_all if isinstance(t, str) and t.strip()]
            if ta:
                joins.append(
                    "JOIN (SELECT doc_id FROM document_tags WHERE tag IN ("
                    + ",".join(["?"] * len(ta))
                    + ") GROUP BY doc_id HAVING COUNT(DISTINCT tag)=?) dta ON dta.doc_id = d.doc_id"
                )
                params.extend(ta)
                params.append(len(set(ta)))

        if joins:
            sql += " " + " ".join(joins)
        if wheres:
            sql += " WHERE " + " AND ".join(wheres)
        sql += " GROUP BY d.doc_id ORDER BY d.rel_path LIMIT ?"
        params.append(limit)

        cur = self._store.execute(sql, tuple(params))
        doc_ids = [r[0] for r in cur.fetchall()]
        return View(name, doc_ids)

    def search(self, query: str, limit: int = 20) -> List[DocumentRef]:
        ranked = self._search.lexical_search(query, limit=limit)
        return [self.get_document(doc_id) for doc_id, _ in ranked]

    def recall_candidates(
        self,
        query: str,
        limit: int = 20,
        source_quota: Optional[Dict[str, int]] = None,
    ) -> List[DocumentRef]:
        ranked = self._search.lexical_search(query, limit=max(limit * 5, limit))
        if not ranked:
            return []
        if not source_quota:
            return [self.get_document(doc_id) for doc_id, _ in ranked[:limit]]

        quotas: Dict[str, int] = {}
        for k, v in source_quota.items():
            if not isinstance(k, str):
                continue
            try:
                iv = int(v)
            except Exception:
                continue
            if iv < 0:
                continue
            quotas[k] = iv

        selected: List[str] = []
        used: Dict[str, int] = {}
        for doc_id, _ in ranked:
            doc = self.get_document(doc_id)
            key = doc.mime_type
            if key in quotas:
                if used.get(key, 0) >= quotas[key]:
                    continue
            selected.append(doc_id)
            used[key] = used.get(key, 0) + 1
            if len(selected) >= limit:
                break
        return [self.get_document(d) for d in selected]

    def read_document_window(
        self,
        doc_id: str,
        kind: str = "lines",
        start: int = 1,
        end: int = 50,
    ) -> WindowRef:
        doc = self.get_document(doc_id)
        abs_path = os.path.abspath(os.path.join(self._root_dir, doc.rel_path))
        locator, content = self._reader.read_windows(abs_path, kind=kind, start=start, end=end)
        window_id = str(uuid.uuid4())
        created_at = _utc_now_iso()
        self._store.execute(
            "INSERT INTO windows(window_id, doc_id, kind, locator, content, created_at) VALUES(?,?,?,?,?,?)",
            (window_id, doc_id, kind, locator, content, created_at),
        )
        self._store.commit()
        self._journal.append(
            "read_window",
            {"window_id": window_id, "doc_id": doc_id, "kind": kind, "locator": locator, "size": len(content)},
        )
        return WindowRef(window_id, doc_id, kind, locator, content, created_at)

    def list_windows(self, doc_id: str, limit: int = 50) -> List[WindowRef]:
        self.get_document(doc_id)
        cur = self._store.execute(
            "SELECT window_id, doc_id, kind, locator, content, created_at FROM windows WHERE doc_id=? ORDER BY created_at DESC LIMIT ?",
            (doc_id, limit),
        )
        out: List[WindowRef] = []
        for window_id, d, kind, locator, content, created_at in cur.fetchall():
            out.append(WindowRef(window_id, d, kind, locator, content, created_at))
        return out

    def create_note(self, title: str, body: str, tags: Optional[List[str]] = None, related_doc_ids: Optional[List[str]] = None) -> Note:
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("Note title required")
        if not isinstance(body, str):
            raise ValidationError("Note body required")
        tgs = []
        if tags:
            for t in tags:
                if isinstance(t, str) and t.strip():
                    tt = t.strip()
                    if len(tt) > 64:
                        raise ValidationError("Tag too long")
                    tgs.append(tt)
        tgs = sorted(set(tgs))
        rds: List[str] = []
        if related_doc_ids:
            for d in related_doc_ids:
                if isinstance(d, str) and d.strip():
                    self.get_document(d.strip())
                    rds.append(d.strip())
        rds = sorted(set(rds))
        note_id = str(uuid.uuid4())
        created_at = _utc_now_iso()
        self._store.execute(
            "INSERT INTO notes(note_id, title, body, tags_json, related_doc_ids_json, created_at) VALUES(?,?,?,?,?,?)",
            (note_id, title.strip(), body, json.dumps(tgs, ensure_ascii=False), json.dumps(rds), created_at),
        )
        self._store.commit()
        self._journal.append(
            "note_create",
            {"note_id": note_id, "title": title.strip(), "tags": tgs, "related_doc_ids": rds},
        )
        return Note(note_id, title.strip(), body, tgs, rds, created_at)

    def list_notes(self, limit: int = 100) -> List[Note]:
        cur = self._store.execute(
            "SELECT note_id, title, body, tags_json, related_doc_ids_json, created_at FROM notes ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        out: List[Note] = []
        for note_id, title, body, tags_json, related_json, created_at in cur.fetchall():
            out.append(
                Note(
                    note_id=note_id,
                    title=title,
                    body=body,
                    tags=json.loads(tags_json),
                    related_doc_ids=json.loads(related_json),
                    created_at=created_at,
                )
            )
        return out

    def search_notes(self, query: str, limit: int = 50) -> List[Note]:
        q = query.strip().lower()
        if not q:
            return []
        cur = self._store.execute(
            "SELECT note_id, title, body, tags_json, related_doc_ids_json, created_at FROM notes ORDER BY created_at DESC"
        )
        out: List[Tuple[float, Note]] = []
        for note_id, title, body, tags_json, related_json, created_at in cur.fetchall():
            text = (title + "\n" + body).lower()
            score = float(text.count(q))
            if score <= 0:
                continue
            out.append(
                (
                    score,
                    Note(
                        note_id=note_id,
                        title=title,
                        body=body,
                        tags=json.loads(tags_json),
                        related_doc_ids=json.loads(related_json),
                        created_at=created_at,
                    ),
                )
            )
        out.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in out[:limit]]

    def _reindex_document(self, doc_id: str, abs_path: str) -> None:
        text = self._extractor.extract_text(abs_path)
        freq = self._indexer.build_index(text)
        self._store.execute("DELETE FROM lexical_index WHERE doc_id=?", (doc_id,))
        self._store.executemany(
            "INSERT INTO lexical_index(doc_id, token, freq) VALUES(?,?,?)",
            [(doc_id, tok, int(fr)) for tok, fr in freq.items()],
        )

    def _remine_relations(self, doc_id: str, abs_path: str) -> None:
        text = self._extractor.extract_text(abs_path)
        cur = self._store.execute("SELECT doc_id, rel_path FROM documents")
        path_lookup: Dict[str, str] = {}
        for did, rel in cur.fetchall():
            path_lookup[rel] = did
            path_lookup[os.path.basename(rel)] = did
            path_lookup[_norm_path(rel)] = did
        mined = self._miner.mine(doc_id, text, path_lookup)
        self._store.execute("DELETE FROM relations WHERE src_doc_id=?", (doc_id,))
        now = _utc_now_iso()
        self._store.executemany(
            "INSERT INTO relations(relation_id, src_doc_id, dst_doc_id, relation_type, evidence, created_at) VALUES(?,?,?,?,?,?)",
            [(str(uuid.uuid4()), s, d, "mentions", ev, now) for (s, d, ev) in mined],
        )

    def list_relations(self, doc_id: str, direction: str = "out", limit: int = 200) -> List[Dict[str, Any]]:
        self.get_document(doc_id)
        if direction not in ("out", "in"):
            raise ValidationError("direction must be 'out' or 'in'")
        if direction == "out":
            cur = self._store.execute(
                "SELECT relation_id, src_doc_id, dst_doc_id, relation_type, evidence, created_at FROM relations WHERE src_doc_id=? ORDER BY created_at DESC LIMIT ?",
                (doc_id, limit),
            )
        else:
            cur = self._store.execute(
                "SELECT relation_id, src_doc_id, dst_doc_id, relation_type, evidence, created_at FROM relations WHERE dst_doc_id=? ORDER BY created_at DESC LIMIT ?",
                (doc_id, limit),
            )
        out: List[Dict[str, Any]] = []
        for relation_id, src, dst, rtype, evidence, created_at in cur.fetchall():
            out.append(
                {
                    "relation_id": relation_id,
                    "src_doc_id": src,
                    "dst_doc_id": dst,
                    "relation_type": rtype,
                    "evidence": evidence,
                    "created_at": created_at,
                }
            )
        return out


class LLMEngine:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class DeterministicLLM(LLMEngine):
    def generate(self, prompt: str) -> str:
        lines = [ln.strip() for ln in prompt.splitlines() if ln.strip()]
        if not lines:
            return ""
        q = lines[-1]
        return f"{q}\n\n(Generated locally; provide your own LLMEngine for richer output.)"


class ResearchAgent:
    def __init__(self, kb: KnowledgeBase, llm: Optional[LLMEngine] = None):
        self._kb = kb
        self._llm = llm or DeterministicLLM()

    def answer(
        self,
        question: str,
        candidate_limit: int = 10,
        windows_per_doc: int = 1,
        window_kind: str = "lines",
        window_size: int = 60,
        source_quota: Optional[Dict[str, int]] = None,
    ) -> Answer:
        if not isinstance(question, str) or not question.strip():
            raise ValidationError("Question required")
        if candidate_limit <= 0:
            raise ValidationError("candidate_limit must be positive")
        if windows_per_doc <= 0:
            raise ValidationError("windows_per_doc must be positive")
        if window_size <= 0:
            raise ValidationError("window_size must be positive")

        candidates = self._kb.recall_candidates(question, limit=candidate_limit, source_quota=source_quota)
        windows: List[WindowRef] = []
        citations: List[Citation] = []

        for doc in candidates:
            for i in range(windows_per_doc):
                start = 1 + i * window_size
                end = start + window_size - 1
                w = self._kb.read_document_window(doc.doc_id, kind=window_kind, start=start, end=end)
                windows.append(w)
                quote = _truncate(w.content.strip(), 280)
                citations.append(
                    Citation(
                        doc_id=doc.doc_id,
                        rel_path=doc.rel_path,
                        window_id=w.window_id,
                        kind=w.kind,
                        locator=w.locator,
                        quote=quote,
                    )
                )

        prompt_parts: List[str] = []
        prompt_parts.append("You are a local-first research agent. Answer using only the provided excerpts and cite sources.")
        prompt_parts.append(f"Question: {question.strip()}")
        prompt_parts.append("Excerpts:")
        for idx, w in enumerate(windows, start=1):
            doc = self._kb.get_document(w.doc_id)
            prompt_parts.append(f"[{idx}] {doc.rel_path} ({w.locator})")
            prompt_parts.append(w.content)
        prompt_parts.append("Write an answer with citations like [1], [2] referring to excerpt numbers.")
        prompt = "\n".join(prompt_parts)

        response = self._llm.generate(prompt).strip()
        if not response:
            response = "No answer generated."

        answer_id = str(uuid.uuid4())
        created_at = _utc_now_iso()

        self._kb.journal.append(
            "answer",
            {
                "answer_id": answer_id,
                "question": question.strip(),
                "candidate_doc_ids": [d.doc_id for d in candidates],
                "window_ids": [w.window_id for w in windows],
            },
        )

        note_title = f"Investigation: {_truncate(question.strip(), 80)}"
        note_body_parts: List[str] = []
        note_body_parts.append(f"Question: {question.strip()}")
        note_body_parts.append("")
        note_body_parts.append("Answer:")
        note_body_parts.append(response)
        note_body_parts.append("")
        note_body_parts.append("Citations:")
        for c in citations:
            note_body_parts.append(f"- {c.rel_path} ({c.locator}) window={c.window_id}: {c.quote}")
        note_body = "\n".join(note_body_parts)

        related_doc_ids = sorted({c.doc_id for c in citations})
        self._kb.create_note(
            title=note_title,
            body=note_body,
            tags=["investigation"],
            related_doc_ids=related_doc_ids,
        )

        return Answer(
            answer_id=answer_id,
            question=question.strip(),
            response=response,
            citations=citations,
            created_at=created_at,
        )


class Marginalia:
    def __init__(self, root_dir: str, db_path: str, llm: Optional[LLMEngine] = None):
        self._kb = KnowledgeBase(root_dir=root_dir, db_path=db_path)
        self._agent = ResearchAgent(self._kb, llm=llm)

    @property
    def kb(self) -> KnowledgeBase:
        return self._kb

    @property
    def agent(self) -> ResearchAgent:
        return self._agent

    def close(self) -> None:
        self._kb.close()