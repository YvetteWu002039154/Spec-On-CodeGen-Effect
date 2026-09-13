#!/usr/bin/env python3
"""
Marginalia: A library-science-inspired personal knowledge management system with LLM agents.
"""

import os
import re
import json
import math
import time
import uuid
import shutil
import hashlib
import logging
import sqlite3
import zipfile
import tarfile
import fnmatch
import datetime
import mimetypes
import threading
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
from collections import defaultdict, Counter

# Optional imports with graceful fallbacks
try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    try:
        import PyPDF2 as pypdf
        HAS_PYPDF = True
    except ImportError:
        HAS_PYPDF = False

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    import csv
    HAS_CSV = True
except ImportError:
    HAS_CSV = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import sqlite_vec
    HAS_SQLITE_VEC = True
except ImportError:
    HAS_SQLITE_VEC = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# Data Models
# ============================================================

@dataclass
class DocumentMetadata:
    doc_id: str
    file_path: str
    title: str
    file_type: str
    size_bytes: int
    created_at: str
    modified_at: str
    ingested_at: str
    checksum: str
    tags: List[str] = field(default_factory=list)
    catalog_id: Optional[str] = None
    folder_path: str = ""
    author: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> 'DocumentMetadata':
        return cls(**d)


@dataclass
class DocumentChunk:
    chunk_id: str
    doc_id: str
    content: str
    chunk_type: str  # 'text', 'page', 'line', 'table_row', 'archive_member'
    position: int
    start_offset: int
    end_offset: int
    page_number: Optional[int] = None
    line_number: Optional[int] = None
    section_title: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SearchResult:
    doc_id: str
    chunk_id: str
    file_path: str
    content: str
    score: float
    rank: int
    chunk_type: str
    page_number: Optional[int] = None
    line_number: Optional[int] = None
    section_title: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Citation:
    doc_id: str
    file_path: str
    chunk_id: str
    quote: str
    page_number: Optional[int] = None
    line_number: Optional[int] = None
    section_title: Optional[str] = None


@dataclass
class AgentResponse:
    answer: str
    citations: List[Citation]
    sources_consulted: List[str]
    investigation_note_id: Optional[str] = None
    reasoning: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())


@dataclass
class InvestigationNote:
    note_id: str
    query: str
    answer: str
    citations: List[Dict]
    sources_consulted: List[str]
    tags: List[str]
    created_at: str
    updated_at: str
    parent_note_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Catalog:
    catalog_id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    doc_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class View:
    view_id: str
    name: str
    description: str
    query_filter: Dict[str, Any]
    sort_by: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Relation:
    relation_id: str
    source_doc_id: str
    target_doc_id: str
    relation_type: str  # 'cites', 'related', 'contradicts', 'extends', 'summarizes'
    confidence: float
    evidence: str
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class JournalEntry:
    entry_id: str
    title: str
    content: str
    tags: List[str]
    linked_doc_ids: List[str]
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================
# Database Layer
# ============================================================

class Database:
    """SQLite-based persistence layer for Marginalia."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
            if HAS_SQLITE_VEC:
                self._local.conn.enable_load_extension(True)
                sqlite_vec.load(self._local.conn)
                self._local.conn.enable_load_extension(False)
        return self._local.conn

    @property
    def conn(self) -> sqlite3.Connection:
        return self._get_conn()

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                file_path TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                file_type TEXT NOT NULL,
                size_bytes INTEGER,
                created_at TEXT,
                modified_at TEXT,
                ingested_at TEXT,
                checksum TEXT,
                catalog_id TEXT,
                folder_path TEXT,
                author TEXT,
                description TEXT,
                language TEXT,
                page_count INTEGER,
                word_count INTEGER,
                custom_fields TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS document_tags (
                doc_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (doc_id, tag),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_type TEXT NOT NULL,
                position INTEGER,
                start_offset INTEGER,
                end_offset INTEGER,
                page_number INTEGER,
                line_number INTEGER,
                section_title TEXT,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                doc_id UNINDEXED,
                content,
                section_title,
                content='chunks',
                content_rowid='rowid'
            );

            CREATE TABLE IF NOT EXISTS catalogs (
                catalog_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT,
                updated_at TEXT,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS catalog_documents (
                catalog_id TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                PRIMARY KEY (catalog_id, doc_id),
                FOREIGN KEY (catalog_id) REFERENCES catalogs(catalog_id) ON DELETE CASCADE,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS views (
                view_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                query_filter TEXT DEFAULT '{}',
                sort_by TEXT DEFAULT 'ingested_at',
                created_at TEXT,
                updated_at TEXT,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS relations (
                relation_id TEXT PRIMARY KEY,
                source_doc_id TEXT NOT NULL,
                target_doc_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                confidence REAL,
                evidence TEXT,
                created_at TEXT,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (source_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (target_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                entry_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                linked_doc_ids TEXT DEFAULT '[]',
                created_at TEXT,
                updated_at TEXT,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS investigation_notes (
                note_id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                answer TEXT NOT NULL,
                citations TEXT DEFAULT '[]',
                sources_consulted TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                created_at TEXT,
                updated_at TEXT,
                parent_note_id TEXT,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                embedding BLOB,
                model_name TEXT,
                created_at TEXT,
                FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
            CREATE INDEX IF NOT EXISTS idx_document_tags_tag ON document_tags(tag);
            CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_doc_id);
            CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_doc_id);
            CREATE INDEX IF NOT EXISTS idx_documents_folder ON documents(folder_path);
            CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(file_type);
        """)
        conn.commit()

    def upsert_document(self, meta: DocumentMetadata):
        conn = self.conn
        conn.execute("""
            INSERT OR REPLACE INTO documents
            (doc_id, file_path, title, file_type, size_bytes, created_at, modified_at,
             ingested_at, checksum, catalog_id, folder_path, author, description,
             language, page_count, word_count, custom_fields)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            meta.doc_id, meta.file_path, meta.title, meta.file_type,
            meta.size_bytes, meta.created_at, meta.modified_at, meta.ingested_at,
            meta.checksum, meta.catalog_id, meta.folder_path, meta.author,
            meta.description, meta.language, meta.page_count, meta.word_count,
            json.dumps(meta.custom_fields)
        ))
        conn.execute("DELETE FROM document_tags WHERE doc_id=?", (meta.doc_id,))
        for tag in meta.tags:
            conn.execute("INSERT OR IGNORE INTO document_tags (doc_id, tag) VALUES (?,?)",
                         (meta.doc_id, tag))
        conn.commit()

    def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        row = self.conn.execute(
            "SELECT * FROM documents WHERE doc_id=?", (doc_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_metadata(row)

    def get_document_by_path(self, file_path: str) -> Optional[DocumentMetadata]:
        row = self.conn.execute(
            "SELECT * FROM documents WHERE file_path=?", (file_path,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_metadata(row)

    def _row_to_metadata(self, row) -> DocumentMetadata:
        tags = [r['tag'] for r in self.conn.execute(
            "SELECT tag FROM document_tags WHERE doc_id=?", (row['doc_id'],)
        ).fetchall()]
        return DocumentMetadata(
            doc_id=row['doc_id'],
            file_path=row['file_path'],
            title=row['title'],
            file_type=row['file_type'],
            size_bytes=row['size_bytes'],
            created_at=row['created_at'],
            modified_at=row['modified_at'],
            ingested_at=row['ingested_at'],
            checksum=row['checksum'],
            tags=tags,
            catalog_id=row['catalog_id'],
            folder_path=row['folder_path'],
            author=row['author'],
            description=row['description'],
            language=row['language'],
            page_count=row['page_count'],
            word_count=row['word_count'],
            custom_fields=json.loads(row['custom_fields'] or '{}')
        )

    def list_documents(self, folder_path: Optional[str] = None,
                       file_type: Optional[str] = None,
                       tags: Optional[List[str]] = None,
                       catalog_id: Optional[str] = None) -> List[DocumentMetadata]:
        query = "SELECT DISTINCT d.* FROM documents d"
        conditions = []
        params = []

        if tags:
            query += " JOIN document_tags dt ON d.doc_id = dt.doc_id"
            placeholders = ','.join('?' * len(tags))
            conditions.append(f"dt.tag IN ({placeholders})")
            params.extend(tags)

        if folder_path:
            conditions.append("d.folder_path LIKE ?")
            params.append(folder_path + '%')
        if file_type:
            conditions.append("d.file_type=?")
            params.append(file_type)
        if catalog_id:
            query += " JOIN catalog_documents cd ON d.doc_id = cd.doc_id"
            conditions.append("cd.catalog_id=?")
            params.append(catalog_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_metadata(r) for r in rows]

    def delete_document(self, doc_id: str):
        self.conn.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
        self.conn.commit()

    def upsert_chunk(self, chunk: DocumentChunk):
        self.conn.execute("""
            INSERT OR REPLACE INTO chunks
            (chunk_id, doc_id, content, chunk_type, position, start_offset, end_offset,
             page_number, line_number, section_title, metadata)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            chunk.chunk_id, chunk.doc_id, chunk.content, chunk.chunk_type,
            chunk.position, chunk.start_offset, chunk.end_offset,
            chunk.page_number, chunk.line_number, chunk.section_title,
            json.dumps(chunk.metadata)
        ))
        self.conn.execute("""
            INSERT OR REPLACE INTO chunks_fts (chunk_id, doc_id, content, section_title)
            VALUES (?,?,?,?)
        """, (chunk.chunk_id, chunk.doc_id, chunk.content, chunk.section_title or ''))
        self.conn.commit()

    def get_chunks_for_doc(self, doc_id: str) -> List[DocumentChunk]:
        rows = self.conn.execute(
            "SELECT * FROM chunks WHERE doc_id=? ORDER BY position", (doc_id,)
        ).fetchall()
        return [self._row_to_chunk(r) for r in rows]

    def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        row = self.conn.execute(
            "SELECT * FROM chunks WHERE chunk_id=?", (chunk_id,)
        ).fetchone()
        return self._row_to_chunk(row) if row else None

    def _row_to_chunk(self, row) -> DocumentChunk:
        return DocumentChunk(
            chunk_id=row['chunk_id'],
            doc_id=row['doc_id'],
            content=row['content'],
            chunk_type=row['chunk_type'],
            position=row['position'],
            start_offset=row['start_offset'],
            end_offset=row['end_offset'],
            page_number=row['page_number'],
            line_number=row['line_number'],
            section_title=row['section_title'],
            metadata=json.loads(row['metadata'] or '{}')
        )

    def fts_search(self, query: str, limit: int = 20,
                   doc_ids: Optional[List[str]] = None) -> List[Tuple[str, str, float]]:
        """Returns list of (chunk_id, doc_id, score)."""
        safe_query = query.replace('"', '""')
        if doc_ids:
            placeholders = ','.join('?' * len(doc_ids))
            sql = f"""
                SELECT chunk_id, doc_id, rank as score
                FROM chunks_fts
                WHERE chunks_fts MATCH ? AND doc_id IN ({placeholders})
                ORDER BY rank
                LIMIT ?
            """
            rows = self.conn.execute(sql, [safe_query] + doc_ids + [limit]).fetchall()
        else:
            sql = """
                SELECT chunk_id, doc_id, rank as score
                FROM chunks_fts
                WHERE chunks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            rows = self.conn.execute(sql, [safe_query, limit]).fetchall()
        return [(r['chunk_id'], r['doc_id'], float(r['score'])) for r in rows]

    def upsert_catalog(self, catalog: Catalog):
        self.conn.execute("""
            INSERT OR REPLACE INTO catalogs
            (catalog_id, name, description, created_at, updated_at, tags, metadata)
            VALUES (?,?,?,?,?,?,?)
        """, (
            catalog.catalog_id, catalog.name, catalog.description,
            catalog.created_at, catalog.updated_at,
            json.dumps(catalog.tags), json.dumps(catalog.metadata)
        ))
        self.conn.execute("DELETE FROM catalog_documents WHERE catalog_id=?",
                          (catalog.catalog_id,))
        for doc_id in catalog.doc_ids:
            self.conn.execute(
                "INSERT OR IGNORE INTO catalog_documents (catalog_id, doc_id) VALUES (?,?)",
                (catalog.catalog_id, doc_id)
            )
        self.conn.commit()

    def get_catalog(self, catalog_id: str) -> Optional[Catalog]:
        row = self.conn.execute(
            "SELECT * FROM catalogs WHERE catalog_id=?", (catalog_id,)
        ).fetchone()
        if not row:
            return None
        doc_ids = [r['doc_id'] for r in self.conn.execute(
            "SELECT doc_id FROM catalog_documents WHERE catalog_id=?", (catalog_id,)
        ).fetchall()]
        return Catalog(
            catalog_id=row['catalog_id'],
            name=row['name'],
            description=row['description'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            doc_ids=doc_ids,
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}')
        )

    def list_catalogs(self) -> List[Catalog]:
        rows = self.conn.execute("SELECT catalog_id FROM catalogs").fetchall()
        return [self.get_catalog(r['catalog_id']) for r in rows]

    def upsert_view(self, view: View):
        self.conn.execute("""
            INSERT OR REPLACE INTO views
            (view_id, name, description, query_filter, sort_by, created_at, updated_at, metadata)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            view.view_id, view.name, view.description,
            json.dumps(view.query_filter), view.sort_by,
            view.created_at, view.updated_at, json.dumps(view.metadata)
        ))
        self.conn.commit()

    def get_view(self, view_id: str) -> Optional[View]:
        row = self.conn.execute(
            "SELECT * FROM views WHERE view_id=?", (view_id,)
        ).fetchone()
        if not row:
            return None
        return View(
            view_id=row['view_id'],
            name=row['name'],
            description=row['description'],
            query_filter=json.loads(row['query_filter'] or '{}'),
            sort_by=row['sort_by'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            metadata=json.loads(row['metadata'] or '{}')
        )

    def list_views(self) -> List[View]:
        rows = self.conn.execute("SELECT view_id FROM views").fetchall()
        return [self.get_view(r['view_id']) for r in rows]

    def upsert_relation(self, relation: Relation):
        self.conn.execute("""
            INSERT OR REPLACE INTO relations
            (relation_id, source_doc_id, target_doc_id, relation_type,
             confidence, evidence, created_at, metadata)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            relation.relation_id, relation.source_doc_id, relation.target_doc_id,
            relation.relation_type, relation.confidence, relation.evidence,
            relation.created_at, json.dumps(relation.metadata)
        ))
        self.conn.commit()

    def get_relations_for_doc(self, doc_id: str) -> List[Relation]:
        rows = self.conn.execute("""
            SELECT * FROM relations
            WHERE source_doc_id=? OR target_doc_id=?
        """, (doc_id, doc_id)).fetchall()
        return [self._row_to_relation(r) for r in rows]

    def _row_to_relation(self, row) -> Relation:
        return Relation(
            relation_id=row['relation_id'],
            source_doc_id=row['source_doc_id'],
            target_doc_id=row['target_doc_id'],
            relation_type=row['relation_type'],
            confidence=row['confidence'],
            evidence=row['evidence'],
            created_at=row['created_at'],
            metadata=json.loads(row['metadata'] or '{}')
        )

    def upsert_journal_entry(self, entry: JournalEntry):
        self.conn.execute("""
            INSERT OR REPLACE INTO journal_entries
            (entry_id, title, content, tags, linked_doc_ids, created_at, updated_at, metadata)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            entry.entry_id, entry.title, entry.content,
            json.dumps(entry.tags), json.dumps(entry.linked_doc_ids),
            entry.created_at, entry.updated_at, json.dumps(entry.metadata)
        ))
        self.conn.commit()

    def get_journal_entry(self, entry_id: str) -> Optional[JournalEntry]:
        row = self.conn.execute(
            "SELECT * FROM journal_entries WHERE entry_id=?", (entry_id,)
        ).fetchone()
        if not row:
            return None
        return JournalEntry(
            entry_id=row['entry_id'],
            title=row['title'],
            content=row['content'],
            tags=json.loads(row['tags'] or '[]'),
            linked_doc_ids=json.loads(row['linked_doc_ids'] or '[]'),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            metadata=json.loads(row['metadata'] or '{}')
        )

    def list_journal_entries(self) -> List[JournalEntry]:
        rows = self.conn.execute(
            "SELECT entry_id FROM journal_entries ORDER BY created_at DESC"
        ).fetchall()
        return [self.get_journal_entry(r['entry_id']) for r in rows]

    def upsert_investigation_note(self, note: InvestigationNote):
        self.conn.execute("""
            INSERT OR REPLACE INTO investigation_notes
            (note_id, query, answer, citations, sources_consulted, tags,
             created_at, updated_at, parent_note_id, metadata)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            note.note_id, note.query, note.answer,
            json.dumps(note.citations), json.dumps(note.sources_consulted),
            json.dumps(note.tags), note.created_at, note.updated_at,
            note.parent_note_id, json.dumps(note.metadata)
        ))
        self.conn.commit()

    def get_investigation_note(self, note_id: str) -> Optional[InvestigationNote]:
        row = self.conn.execute(
            "SELECT * FROM investigation_notes WHERE note_id=?", (note_id,)
        ).fetchone()
        if not row:
            return None
        return InvestigationNote(
            note_id=row['note_id'],
            query=row['query'],
            answer=row['answer'],
            citations=json.loads(row['citations'] or '[]'),
            sources_consulted=json.loads(row['sources_consulted'] or '[]'),
            tags=json.loads(row['tags'] or '[]'),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            parent_note_id=row['parent_note_id'],
            metadata=json.loads(row['metadata'] or '{}')
        )

    def list_investigation_notes(self) -> List[InvestigationNote]:
        rows = self.conn.execute(
            "SELECT note_id FROM investigation_notes ORDER BY created_at DESC"
        ).fetchall()
        return [self.get_investigation_note(r['note_id']) for r in rows]

    def search_investigation_notes(self, query: str) -> List[InvestigationNote]:
        query_lower = f"%{query.lower()}%"
        rows = self.conn.execute("""
            SELECT note_id FROM investigation_notes
            WHERE LOWER(query) LIKE ? OR LOWER(answer) LIKE ?
            ORDER BY created_at DESC
        """, (query_lower, query_lower)).fetchall()
        return [self.get_investigation_note(r['note_id']) for r in rows]

    def store_embedding(self, chunk_id: str, doc_id: str,
                        embedding: List[float], model_name: str):
        if HAS_NUMPY:
            blob = np.array(embedding, dtype=np.float32).tobytes()
        else:
            import struct
            blob = struct.pack(f'{len(embedding)}f', *embedding)
        self.conn.execute("""
            INSERT OR REPLACE INTO embeddings
            (chunk_id, doc_id, embedding, model_name, created_at)
            VALUES (?,?,?,?,?)
        """, (chunk_id, doc_id, blob, model_name,
              datetime.datetime.utcnow().isoformat()))
        self.conn.commit()

    def get_all_embeddings(self, model_name: Optional[str] = None) -> List[Tuple[str, str, List[float]]]:
        if model_name:
            rows = self.conn.execute(
                "SELECT chunk_id, doc_id, embedding FROM embeddings WHERE model_name=?",
                (model_name,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT chunk_id, doc_id, embedding FROM embeddings"
            ).fetchall()
        results = []
        for row in rows:
            if HAS_NUMPY:
                emb = np.frombuffer(row['embedding'], dtype=np.float32).tolist()
            else:
                import struct
                n = len(row['embedding']) // 4
                emb = list(struct.unpack(f'{n}f', row['embedding']))
            results.append((row['chunk_id'], row['doc_id'], emb))
        return results

    def get_all_tags(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT tag FROM document_tags ORDER BY tag"
        ).fetchall()
        return [r['tag'] for r in rows]

    def get_tag_counts(self) -> Dict[str, int]:
        rows = self.conn.execute(
            "SELECT tag, COUNT(*) as cnt FROM document_tags GROUP BY tag ORDER BY cnt DESC"
        ).fetchall()
        return {r['tag']: r['cnt'] for r in rows}


# ============================================================
# File Parsers
# ============================================================

class BaseParser:
    """Base class for file parsers."""

    def can_parse(self, file_path: str) -> bool:
        raise NotImplementedError

    def parse(self, file_path: str) -> Tuple[str, List[DocumentChunk], Dict[str, Any]]:
        """Returns (full_text, chunks, extra_metadata)."""
        raise NotImplementedError


class TextParser(BaseParser):
    EXTENSIONS = {'.txt', '.md', '.rst', '.log', '.csv', '.tsv', '.json',
                  '.yaml', '.yml', '.xml', '.html', '.htm', '.py', '.js',
                  '.ts', '.java', '.c', '.cpp', '.h', '.go', '.rs', '.rb',
                  '.sh', '.bash', '.zsh', '.fish', '.toml', '.ini', '.cfg',
                  '.conf', '.env', '.gitignore', '.dockerfile'}

    def can_parse(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self.EXTENSIONS

    def parse(self, file_path: str) -> Tuple[str, List[DocumentChunk], Dict[str, Any]]:
        doc_id = str(uuid.uuid4())
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
            content = ""

        lines = content.split('\n')
        chunks = []
        chunk_size = 500
        current_chunk_lines = []
        current_start_line = 1
        position = 0
        offset = 0

        for i, line in enumerate(lines, 1):
            current_chunk_lines.append(line)
            if len('\n'.join(current_chunk_lines)) >= chunk_size or i == len(lines):
                chunk_text = '\n'.join(current_chunk_lines)
                if chunk_text.strip():
                    chunk = DocumentChunk(
                        chunk_id=str(uuid.uuid4()),
                        doc_id=doc_id,
                        content=chunk_text,
                        chunk_type='text',
                        position=position,
                        start_offset=offset,
                        end_offset=offset + len(chunk_text),
                        line_number=current_start_line,
                        metadata={'end_line': i}
                    )
                    chunks.append(chunk)
                    position += 1
                offset += len(chunk_text) + 1
                current_chunk_lines = []
                current_start_line = i + 1

        extra = {
            'word_count': len(content.split()),
            'line_count': len(lines)
        }
        return content, chunks, extra


class MarkdownParser(BaseParser):
    EXTENSIONS = {'.md', '.markdown', '.mdown', '.mkd'}

    def can_parse(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self.EXTENSIONS

    def parse(self, file_path: str) -> Tuple[str, List[DocumentChunk], Dict[str, Any]]:
        doc_id = str(uuid.uuid4())
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
            content = ""

        chunks = []
        sections = re.split(r'\n(#{1,6}\s+.+)\n', content)
        position = 0
        offset = 0
        current_section = None

        for part in sections:
            if re.match(r'#{1,6}\s+', part):
                current_section = part.strip()
                continue
            if part.strip():
                paragraphs = re.split(r'\n\n+', part)
                for para in paragraphs:
                    if para.strip():
                        chunk = DocumentChunk(
                            chunk_id=str(uuid.uuid4()),
                            doc_id=doc_id,
                            content=para.strip(),
                            chunk_type='text',
                            position=position,
                            start_offset=offset,
                            end_offset=offset + len(para),
                            section_title=current_section,
                            metadata={}
                        )
                        chunks.append(chunk)
                        position += 1
                    offset += len(para) + 2

        if not chunks:
            text_parser = TextParser()
            return text_parser.parse(file_path)

        extra = {
            'word_count': len(content.split()),
        }
        return content, chunks, extra


class PDFParser(BaseParser):
    EXTENSIONS = {'.pdf'}

    def can_parse(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() == '.pdf' and HAS_PYPDF

    def parse(self, file_path: str) -> Tuple[str, List[DocumentChunk], Dict[str, Any]]:
        doc_id = str(uuid.uuid4())
        chunks = []
        full_text_parts = []

        try:
            with open(file_path, 'rb') as f:
                if hasattr(pypdf, 'PdfReader'):
                    reader = pypdf.PdfReader(f)
                    pages = reader.pages
                else:
                    reader = pypdf.PdfFileReader(f)
                    pages = [reader.getPage(i) for i in range(reader.numPages)]

                for page_num, page in enumerate(pages, 1):
                    try:
                        if hasattr(page, 'extract_text'):
                            text = page.extract_text() or ''
                        else:
                            text = page.extractText() or ''
                    except Exception:
                        text = ''

                    full_text_parts.append(text)
                    if text.strip():
                        chunk = DocumentChunk(
                            chunk_id=str(uuid.uuid4()),
                            doc_id=doc_id,
                            content=text,
                            chunk_type='page',
                            position=page_num - 1,
                            start_offset=sum(len(p) for p in full_text_parts[:-1]),
                            end_offset=sum(len(p) for p in full_text_parts),
                            page_number=page_num,
                            metadata={}
                        )
                        chunks.append(chunk)

        except Exception as e:
            logger.warning(f"PDF parse error for {file_path}: {e}")

        full_text = '\n\n'.join(full_text_parts)
        extra = {
            'page_count': len(full_text_parts),
            'word_count': len(full_text.split())
        }
        return full_text, chunks, extra


class DocxParser(BaseParser):
    EXTENSIONS = {'.docx', '.doc'}

    def can_parse(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in self.EXTENSIONS and HAS_DOCX

    def parse(self, file_path: str) -> Tuple[str, List[DocumentChunk], Dict[str, Any]]:
        doc_id = str(uuid.uuid4())
        chunks = []

        try:
            document = docx.Document(file_path)
            paragraphs = document.paragraphs
            full_text_parts = []
            position = 0
            offset = 0
            current_section = None

            for para in paragraphs:
                text = para.text.strip()
                if not text:
                    continue

                style_name = para.style.name if para.style else ''
                if 'Heading' in style_name:
                    current_section = text

                full_text_parts.append(text)
                chunk = DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=text,
                    chunk_type='text',
                    position=position,
                    start_offset=offset,
                    end_offset=offset + len(text),
                    section_title=current_section,
                    metadata={'style': style_name}
                )
                chunks.append(chunk)
                position += 1
                offset += len(text) + 1

        except Exception as e:
            logger.warning(f"DOCX parse error for {file_path}: {e}")

        full_text = '\n'.join(c.content for c in chunks)
        extra = {
            'word_count': len(full_text.split())
        }
        return full_text, chunks, extra


class SpreadsheetParser(BaseParser):
    EXTENSIONS = {'.xlsx', '.xls', '.ods'}

    def can_parse(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self.EXTENSIONS and HAS_OPENPYXL

    def parse(self, file_path: str) -> Tuple[str, List[DocumentChunk], Dict[str, Any]]:
        doc_id = str(uuid.uuid4())
        chunks = []
        full_text_parts = []

        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            position = 0

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = list(ws.iter_rows(values_only=True))
                if not rows:
                    continue

                headers = [str(h) if h is not None else '' for h in rows[0]]
                offset = 0

                for row_idx, row in enumerate(rows[1:], 2):
                    row_data = {headers[i]: str(v) if v is not None else ''
                                for i, v in enumerate(row) if i < len(headers)}
                    row_text = ' | '.join(f"{k}: {v}" for k, v in row_data.items() if v)
                    if row_text.strip():
                        full_text_parts.append(row_text)
                        chunk = DocumentChunk(
                            chunk_id=str(uuid.uuid4()),
                            doc_id=doc_id,
                            content=row_text,
                            chunk_type='table_row',
                            position=position,
                            start_offset=offset,
                            end_offset=offset + len(row_text),
                            line_number=row_idx,
                            metadata={
                                'sheet': sheet_name,
                                'row': row_idx,
                                'headers': headers
                            }
                        )
                        chunks.append(chunk)
                        position += 1
                        offset += len(row_text) + 1

        except Exception as e:
            logger.warning(f"Spreadsheet parse error for {file_path}: {e}")

        full_text = '\n'.join(full_text_parts)
        extra = {'word_count': len(full_text.split())}
        return full_text, chunks, extra


class CSVParser(BaseParser):
    EXTENSIONS = {'.csv', '.tsv'}

    def can_parse(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in self.EXTENSIONS

    def parse(self, file_path: str) -> Tuple[str, List[DocumentChunk], Dict[str, Any]]:
        import csv as csv_module
        doc_id = str(uuid.uuid4())
        chunks = []
        full_text_parts = []

        try:
            delimiter = '\t' if file_path.endswith('.tsv') else ','
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv_module.DictReader(f, delimiter=delimiter)
                position = 0
                offset = 0

                for row_idx, row in enumerate(reader, 2):
                    row_text = ' | '.join(f"{k}: {v}" for k, v in row.items() if v)
                    if row_text.strip():
                        full_text_parts.append(row_text)
                        chunk = DocumentChunk(
                            chunk_id=str(uuid.uuid4()),
                            doc_id=doc_id,
                            content=row_text,
                            chunk_type='table_row',
                            position=position,
                            start_offset=offset,
                            end_offset=offset + len(row_text),
                            line_number=row_idx,
                            metadata={'row': row_idx}
                        )
                        chunks.append(chunk)
                        position += 1
                        offset += len(row_text) + 1

        except Exception as e:
            logger.warning(f"CSV parse error for {file_path}: {e}")

        full_text = '\n'.join(full_text_parts)
        extra = {'word_count': len(full_text.split())}
        return full_text, chunks, extra


class ImageParser(BaseParser):
    EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
                  '.webp', '.svg', '.ico'}

    def can_parse(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in self.EXTENSIONS

    def parse(self, file_path: str) -> Tuple[str, List[DocumentChunk], Dict[str, Any]]:
        doc_id = str(uuid.uuid4())
        extra = {}

        if HAS_PIL:
            try:
                with Image.open(file_path) as img:
                    extra['width'] = img.width
                    extra['height'] = img.height
                    extra['mode'] = img.mode
                    extra['format'] = img.format
            except Exception as e:
                logger.warning(f"Image parse error for {file_path}: {e}")

        description = f"Image file: {Path(file_path).name}"
        if extra:
            description += f" ({extra.get('width', '?')}x{extra.get('height', '?')} {extra.get('mode', '')})"

        chunk = DocumentChunk(
            chunk_id=str(uuid.uuid4()),
            doc_id=doc_id,
            content=description,
            chunk_type='text',
            position=0,
            start_offset=0,
            end_offset=len(description),
            metadata=extra
        )
        return description, [chunk], extra


class ArchiveParser(BaseParser):
    EXTENSIONS = {'.zip', '.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tar.xz',
                  '.gz', '.bz2', '.7z'}

    def can_parse(self, file_path: str) -> bool:
        path = file_path.lower()
        return any(path.endswith(ext) for ext in self.EXTENSIONS)

    def parse(self, file_path: str) -> Tuple[str, List[DocumentChunk], Dict[str, Any]]:
        doc_id = str(uuid.uuid4())
        chunks = []
        members = []

        try:
            if zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, 'r') as zf:
                    for info in zf.infolist():
                        members.append({
                            'name': info.filename,
                            'size': info.file_size,
                            'compress_size': info.compress_size,
                            'date_time': str(info.date_time)
                        })
                        try:
                            if info.file_size < 100000 and not info.filename.endswith('/'):
                                with zf.open(info) as mf:
                                    content = mf.read().decode('utf-8', errors='replace')
                                    if content.strip():
                                        chunk = DocumentChunk(
                                            chunk_id=str(uuid.uuid4()),
                                            doc_id=doc_id,
                                            content=content[:2000],
                                            chunk_type='archive_member',
                                            position=len(chunks),
                                            start_offset=0,
                                            end_offset=len(content),
                                            metadata={'member_name': info.filename,
                                                       'member_size': info.file_size}
                                        )
                                        chunks.append(chunk)
                        except Exception:
                            pass

            elif tarfile.is_tarfile(file_path):
                with tarfile.open(file_path, 'r:*') as tf:
                    for member in tf.getmembers():
                        members.append({
                            'name': member.name,
                            'size': member.size,
                            'mtime': member.mtime
                        })
                        try:
                            if member.size < 100000 and member.isfile():
                                f = tf.extractfile(member)
                                if f:
                                    content = f.read().decode('utf-8', errors='replace')
                                    if content.strip():
                                        chunk = DocumentChunk(
                                            chunk_id=str(uuid.uuid4()),
                                            doc_id=doc_id,
                                            content=content[:2000],
                                            chunk_type='archive_member',
                                            position=len(chunks),
                                            start_offset=0,
                                            end_offset=len(content),
                                            metadata={'member_name': member.name,
                                                       'member_size': member.size}
                                        )
                                        chunks.append(chunk)
                        except Exception:
                            pass

        except Exception as e:
            logger.warning(f"Archive parse error for {file_path}: {e}")

        member_list = '\n'.join(m['name'] for m in members[:100])
        full_text = f"Archive: {Path(file_path).name}\nMembers:\n{member_list}"

        if not chunks:
            chunk = DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                doc_id=doc_id,
                content=full_text,
                chunk_type='text',
                position=0,
                start_offset=0,
                end_offset=len(full_text),
                metadata={'member_count': len(members)}
            )
            chunks.append(chunk)

        extra = {
            'member_count': len(members),
            'members': members[:50]
        }
        return full_text, chunks, extra


class LogParser(BaseParser):
    EXTENSIONS = {'.log', '.logs'}

    def can_parse(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self.EXTENSIONS or 'log' in Path(file_path).name.lower()

    def parse(self, file_path: str) -> Tuple[str, List[DocumentChunk], Dict[str, Any]]:
        doc_id = str(uuid.uuid4())
        chunks = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except Exception as e:
            logger.warning(f"Log parse error for {file_path}: {e}")
            lines = []

        window_size = 50
        position = 0
        offset = 0

        for i in range(0, len(lines), window_size):
            window = lines[i:i + window_size]
            text = ''.join(window)
            if text.strip():
                chunk = DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=text,
                    chunk_type='line',
                    position=position,
                    start_offset=offset,
                    end_offset=offset + len(text),
                    line_number=i + 1,
                    metadata={'end_line': i + len(window)}
                )
                chunks.append(chunk)
                position += 1
            offset += len(text)

        full_text = ''.join(lines)
        extra = {
            'line_count': len(lines),
            'word_count': len(full_text.split())
        }
        return full_text, chunks, extra


class ParserRegistry:
    """Registry of all available parsers."""

    def __init__(self):
        self.parsers: List[BaseParser] = [
            MarkdownParser(),
            PDFParser(),
            DocxParser(),
            SpreadsheetParser(),
            CSVParser(),
            ImageParser(),
            ArchiveParser(),
            LogParser(),
            TextParser(),  # Fallback
        ]

    def get_parser(self, file_path: str) -> Optional[BaseParser]:
        for parser in self.parsers:
            if parser.can_parse(file_path):
                return parser
        return None

    def can_parse(self, file_path: str) -> bool:
        return self.get_parser(file_path) is not None


# ============================================================
# Ingestion Engine
# ============================================================

class IngestionEngine:
    """Handles file ingestion into the knowledge base."""

    def __init__(self, db: Database, parser_registry: ParserRegistry,
                 knowledge_base_path: str):
        self.db = db
        self.parser_registry = parser_registry
        self.kb_path = Path(knowledge_base_path)

    def _compute_checksum(self, file_path: str) -> str:
        h = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    h.update(chunk)
        except Exception:
            pass
        return h.hexdigest()

    def _get_file_type(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        mime, _ = mimetypes.guess_type(file_path)
        if mime:
            return mime
        return ext.lstrip('.') or 'unknown'

    def ingest_file(self, file_path: str,
                    tags: Optional[List[str]] = None,
                    catalog_id: Optional[str] = None,
                    metadata_overrides: Optional[Dict] = None) -> Optional[DocumentMetadata]:
        """Ingest a single file into the knowledge base."""
        file_path = str(Path(file_path).resolve())

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None

        checksum = self._compute_checksum(file_path)
        existing = self.db.get_document_by_path(file_path)
        if existing and existing.checksum == checksum:
            logger.info(f"File unchanged, skipping: {file_path}")
            return existing

        parser = self.parser_registry.get_parser(file_path)
        if not parser:
            logger.warning(f"No parser available for: {file_path}")
            return None

        logger.info(f"Ingesting: {file_path}")

        try:
            full_text, chunks, extra_meta = parser.parse(file_path)
        except Exception as e:
            logger.error(f"Parse error for {file_path}: {e}")
            return None

        stat = os.stat(file_path)
        doc_id = existing.doc_id if existing else str(uuid.uuid4())

        try:
            rel_path = str(Path(file_path).relative_to(self.kb_path))
            folder_path = str(Path(rel_path).parent)
        except ValueError:
            rel_path = file_path
            folder_path = str(Path(file_path).parent)

        meta = DocumentMetadata(
            doc_id=doc_id,
            file_path=file_path,
            title=metadata_overrides.get('title', Path(file_path).stem) if metadata_overrides else Path(file_path).stem,
            file_type=self._get_file_type(file_path),
            size_bytes=stat.st_size,
            created_at=datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified_at=datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            ingested_at=datetime.datetime.utcnow().isoformat(),
            checksum=checksum,
            tags=tags or [],
            catalog_id=catalog_id,
            folder_path=folder_path,
            page_count=extra_meta.get('page_count'),
            word_count=extra_meta.get('word_count'),
            custom_fields=extra_meta
        )

        if metadata_overrides:
            for k, v in metadata_overrides.items():
                if hasattr(meta, k):
                    setattr(meta, k, v)

        for chunk in chunks:
            chunk.doc_id = doc_id

        self.db.upsert_document(meta)
        for chunk in chunks:
            self.db.upsert_chunk(chunk)

        logger.info(f"Ingested {file_path}: {len(chunks)} chunks")
        return meta

    def ingest_directory(self, directory: str,
                         recursive: bool = True,
                         tags: Optional[List[str]] = None,
                         catalog_id: Optional[str] = None,
                         pattern: Optional[str] = None) -> List[DocumentMetadata]:
        """Ingest all files in a directory."""
        directory = Path(directory)
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return []

        results = []
        glob_pattern = '**/*' if recursive else '*'

        for file_path in directory.glob(glob_pattern):
            if not file_path.is_file():
                continue
            if pattern and not fnmatch.fnmatch(file_path.name, pattern):
                continue
            if file_path.name.startswith('.'):
                continue

            meta = self.ingest_file(str(file_path), tags=tags, catalog_id=catalog_id)
            if meta:
                results.append(meta)

        return results

    def remove_document(self, doc_id: str):
        """Remove a document from the knowledge base."""
        self.db.delete_document(doc_id)
        logger.info(f"Removed document: {doc_id}")

    def reindex_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        """Re-parse and re-index a document."""
        meta = self.db.get_document(doc_id)
        if not meta:
            return None
        return self.ingest_file(meta.file_path, tags=meta.tags,
                                catalog_id=meta.catalog_id)


# ============================================================
# Search Engine
# ============================================================

class LexicalSearchEngine:
    """BM25-inspired lexical search using SQLite FTS5."""

    def __init__(self, db: Database):
        self.db = db

    def search(self, query: str, limit: int = 20,
               doc_ids: Optional[List[str]] = None,
               source_quota: Optional[int] = None) -> List[SearchResult]:
        """Perform lexical search."""
        try:
            raw_results = self.db.fts_search(query, limit=limit * 2, doc_ids=doc_ids)
        except Exception as e:
            logger.warning(f"FTS search error: {e}")
            raw_results = self._fallback_search(query, limit * 2, doc_ids)

        results = []
        seen_docs = defaultdict(int)

        for rank, (chunk_id, doc_id, score) in enumerate(raw_results):
            if source_quota and seen_docs[doc_id] >= source_quota:
                continue

            chunk = self.db.get_chunk(chunk_id)
            doc = self.db.get_document(doc_id)
            if not chunk or not doc:
                continue

            results.append(SearchResult(
                doc_id=doc_id,
                chunk_id=chunk_id,
                file_path=doc.file_path,
                content=chunk.content,
                score=abs(score),
                rank=rank,
                chunk_type=chunk.chunk_type,
                page_number=chunk.page_number,
                line_number=chunk.line_number,
                section_title=chunk.section_title,
                metadata=chunk.metadata
            ))
            seen_docs[doc_id] += 1

            if len(results) >= limit:
                break

        return results

    def _fallback_search(self, query: str, limit: int,
                         doc_ids: Optional[List[str]]) -> List[Tuple[str, str, float]]:
        """Simple keyword matching fallback."""
        terms = query.lower().split()
        if doc_ids:
            placeholders = ','.join('?' * len(doc_ids))
            rows = self.db.conn.execute(
                f"SELECT chunk_id, doc_id, content FROM chunks WHERE doc_id IN ({placeholders})",
                doc_ids
            ).fetchall()
        else:
            rows = self.db.conn.execute(
                "SELECT chunk_id, doc_id, content FROM chunks LIMIT 10000"
            ).fetchall()

        scored = []
        for row in rows:
            content_lower = row['content'].lower()
            score = sum(content_lower.count(term) for term in terms)
            if score > 0:
                scored.append((row['chunk_id'], row['doc_id'], float(score)))

        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:limit]


class EmbeddingEngine:
    """Manages document embeddings for semantic search."""

    def __init__(self, db: Database, model_name: str = 'simple'):
        self.db = db
        self.model_name = model_name
        self._embedding_fn = None
        self._setup_embedding_fn()

    def _setup_embedding_fn(self):
        """Set up embedding function based on available libraries."""
        if self.model_name == 'simple':
            self._embedding_fn = self._simple_embedding
        else:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                self._embedding_fn = lambda text: self._model.encode(text).tolist()
            except ImportError:
                logger.warning("sentence-transformers not available, using simple embeddings")
                self._embedding_fn = self._simple_embedding

    def _simple_embedding(self, text: str) -> List[float]:
        """Simple TF-IDF-like embedding using character n-grams."""
        text = text.lower()[:1000]
        vocab_size = 256
        embedding = [0.0] * vocab_size

        words = text.split()
        for word in words:
            for i in range(len(word) - 1):
                bigram = word[i:i+2]
                idx = (ord(bigram[0]) * 31 + ord(bigram[1])) % vocab_size
                embedding[idx] += 1.0

        norm = math.sqrt(sum(x*x for x in embedding)) or 1.0
        return [x / norm for x in embedding]

    def embed_chunk(self, chunk: DocumentChunk):
        """Compute and store embedding for a chunk."""
        try:
            embedding = self._embedding_fn(chunk.content)
            self.db.store_embedding(chunk.chunk_id, chunk.doc_id,
                                    embedding, self.model_name)
        except Exception as e:
            logger.warning(f"Embedding error for chunk {chunk.chunk_id}: {e}")

    def embed_document(self, doc_id: str):
        """Embed all chunks for a document."""
        chunks = self.db.get_chunks_for_doc(doc_id)
        for chunk in chunks:
            self.embed_chunk(chunk)

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if HAS_NUMPY:
            a_arr = np.array(a)
            b_arr = np.array(b)
            norm_a = np.linalg.norm(a_arr)
            norm_b = np.linalg.norm(b_arr)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))
        else:
            dot = sum(x*y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x*x for x in a)) or 1.0
            norm_b = math.sqrt(sum(x*x for x in b)) or 1.0
            return dot / (norm_a * norm_b)

    def semantic_search(self, query: str, limit: int = 20,
                        doc_ids: Optional[List[str]] = None) -> List[SearchResult]:
        """Perform semantic similarity search."""
        query_embedding = self._embedding_fn(query)
        all_embeddings = self.db.get_all_embeddings(self.model_name)

        scored = []
        for chunk_id, doc_id, embedding in all_embeddings:
            if doc_ids and doc_id not in doc_ids:
                continue
            sim = self.cosine_similarity(query_embedding, embedding)
            scored.append((chunk_id, doc_id, sim))

        scored.sort(key=lambda x: x[2], reverse=True)
        scored = scored[:limit]

        results = []
        for rank, (chunk_id, doc_id, score) in enumerate(scored):
            chunk = self.db.get_chunk(chunk_id)
            doc = self.db.get_document(doc_id)
            if not chunk or not doc:
                continue
            results.append(SearchResult(
                doc_id=doc_id,
                chunk_id=chunk_id,
                file_path=doc.file_path,
                content=chunk.content,
                score=score,
                rank=rank,
                chunk_type=chunk.chunk_type,
                page_number=chunk.page_number,
                line_number=chunk.line_number,
                section_title=chunk.section_title,
                metadata=chunk.metadata
            ))

        return results


class Reranker:
    """Reranks search results using cross-encoder or simple heuristics."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name
        self._rerank_fn = None

        if model_name:
            try:
                from sentence_transformers import CrossEncoder
                self._cross_encoder = CrossEncoder(model_name)
                self._rerank_fn = self._cross_encoder_rerank
            except ImportError:
                logger.warning("CrossEncoder not available, using heuristic reranking")
                self._rerank_fn = self._heuristic_rerank
        else:
            self._rerank_fn = self._heuristic_rerank

    def _heuristic_rerank(self, query: str,
                           results: List[SearchResult]) -> List[SearchResult]:
        """Simple heuristic reranking based on term overlap."""
        query_terms = set(query.lower().split())

        for result in results:
            content_terms = set(result.content.lower().split())
            overlap = len(query_terms & content_terms)
            coverage = overlap / len(query_terms) if query_terms else 0
            result.score = result.score * 0.7 + coverage * 0.3

        results.sort(key=lambda x: x.score, reverse=True)
        for i, r in enumerate(results):
            r.rank = i
        return results

    def _cross_encoder_rerank(self, query: str,
                               results: List[SearchResult]) -> List[SearchResult]:
        pairs = [(query, r.content) for r in results]
        scores = self._cross_encoder.predict(pairs)
        for result, score in zip(results, scores):
            result.score = float(score)
        results.sort(key=lambda x: x.score, reverse=True)
        for i, r in enumerate(results):
            r.rank = i
        return results

    def rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        if not results:
            return results
        if self._rerank_fn:
            return self._rerank_fn(query, results)
        return results


class SearchEngine:
    """Unified search engine combining lexical and semantic search."""

    def __init__(self, db: Database,
                 use_embeddings: bool = False,
                 embedding_model: str = 'simple',
                 use_reranking: bool = False,
                 reranker_model: Optional[str] = None):
        self.db = db
        self.use_embeddings = use_embeddings
        self.use_reranking = use_reranking
        self.lexical = LexicalSearchEngine(db)
        self.embedding_engine = EmbeddingEngine(db, embedding_model) if use_embeddings else None
        self.reranker = Reranker(reranker_model) if use_reranking else None

    def search(self, query: str,
               limit: int = 10,
               doc_ids: Optional[List[str]] = None,
               source_quota: Optional[int] = None,
               search_mode: str = 'lexical') -> List[SearchResult]:
        """
        Perform search with specified mode.
        search_mode: 'lexical', 'semantic', 'hybrid'
        """
        if search_mode == 'semantic' and self.embedding_engine:
            results = self.embedding_engine.semantic_search(query, limit * 2, doc_ids)
        elif search_mode == 'hybrid' and self.embedding_engine:
            lex_results = self.lexical.search(query, limit, doc_ids, source_quota)
            sem_results = self.embedding_engine.semantic_search(query, limit, doc_ids)
            results = self._merge_results(lex_results, sem_results, limit)
        else:
            results = self.lexical.search(query, limit * 2, doc_ids, source_quota)

        if source_quota:
            results = self._apply_source_quota(results, source_quota)

        if self.use_reranking and self.reranker:
            results = self.reranker.rerank(query, results)

        return results[:limit]

    def _merge_results(self, lex: List[SearchResult],
                       sem: List[SearchResult],
                       limit: int) -> List[SearchResult]:
        """Merge lexical and semantic results with RRF."""
        scores = defaultdict(float)
        chunks = {}

        for rank, r in enumerate(lex):
            scores[r.chunk_id] += 1.0 / (60 + rank + 1)
            chunks[r.chunk_id] = r

        for rank, r in enumerate(sem):
            scores[r.chunk_id] += 1.0 / (60 + rank + 1)
            if r.chunk_id not in chunks:
                chunks[r.chunk_id] = r

        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        results = []
        for i, chunk_id in enumerate(sorted_ids[:limit]):
            r = chunks[chunk_id]
            r.score = scores[chunk_id]
            r.rank = i
            results.append(r)

        return results

    def _apply_source_quota(self, results: List[SearchResult],
                             quota: int) -> List[SearchResult]:
        seen = defaultdict(int)
        filtered = []
        for r in results:
            if seen[r.doc_id] < quota:
                filtered.append(r)
                seen[r.doc_id] += 1
        return filtered

    def embed_all_documents(self):
        """Embed all documents in the knowledge base."""
        if not self.embedding_engine:
            return
        docs = self.db.list_documents()
        for doc in docs:
            logger.info(f"Embedding document: {doc.doc_id}")
            self.embedding_engine.embed_document(doc.doc_id)


# ============================================================
# Relation Mining
# ============================================================

class RelationMiner:
    """Mines relations between documents."""

    def __init__(self, db: Database):
        self.db = db

    def mine_lexical_relations(self, doc_id: str,
                                threshold: float = 0.1) -> List[Relation]:
        """Find related documents based on shared terms."""
        source_chunks = self.db.get_chunks_for_doc(doc_id)
        if not source_chunks:
            return []

        source_terms = Counter()
        for chunk in source_chunks:
            terms = re.findall(r'\b\w{4,}\b', chunk.content.lower())
            source_terms.update(terms)

        all_docs = self.db.list_documents()
        relations = []

        for doc in all_docs:
            if doc.doc_id == doc_id:
                continue

            target_chunks = self.db.get_chunks_for_doc(doc.doc_id)
            target_terms = Counter()
            for chunk in target_chunks:
                terms = re.findall(r'\b\w{4,}\b', chunk.content.lower())
                target_terms.update(terms)

            shared = set(source_terms.keys()) & set(target_terms.keys())
            if not shared:
                continue

            source_total = sum(source_terms.values()) or 1
            target_total = sum(target_terms.values()) or 1
            shared_weight = sum(
                min(source_terms[t] / source_total, target_terms[t] / target_total)
                for t in shared
            )

            if shared_weight >= threshold:
                top_terms = sorted(shared, key=lambda t: source_terms[t] + target_terms[t],
                                   reverse=True)[:5]
                relation = Relation(
                    relation_id=str(uuid.uuid4()),
                    source_doc_id=doc_id,
                    target_doc_id=doc.doc_id,
                    relation_type='related',
                    confidence=min(shared_weight * 10, 1.0),
                    evidence=f"Shared terms: {', '.join(top_terms)}",
                    created_at=datetime.datetime.utcnow().isoformat()
                )
                self.db.upsert_relation(relation)
                relations.append(relation)

        return relations

    def mine_citation_relations(self, doc_id: str) -> List[Relation]:
        """Find citation-like relations (one doc references another by title)."""
        source_doc = self.db.get_document(doc_id)
        if not source_doc:
            return []

        source_chunks = self.db.get_chunks_for_doc(doc_id)
        source_text = ' '.join(c.content for c in source_chunks).lower()

        all_docs = self.db.list_documents()
        relations = []

        for doc in all_docs:
            if doc.doc_id == doc_id:
                continue
            if doc.title.lower() in source_text and len(doc.title) > 5:
                relation = Relation(
                    relation_id=str(uuid.uuid4()),
                    source_doc_id=doc_id,
                    target_doc_id=doc.doc_id,
                    relation_type='cites',
                    confidence=0.7,
                    evidence=f"Title '{doc.title}' found in source text",
                    created_at=datetime.datetime.utcnow().isoformat()
                )
                self.db.upsert_relation(relation)
                relations.append(relation)

        return relations

    def mine_all_relations(self, doc_id: str) -> List[Relation]:
        """Mine all types of relations for a document."""
        relations = []
        relations.extend(self.mine_lexical_relations(doc_id))
        relations.extend(self.mine_citation_relations(doc_id))
        return relations


# ============================================================
# LLM Client
# ============================================================

class LLMClient:
    """Unified LLM client supporting multiple providers."""

    def __init__(self, provider: str = 'anthropic',
                 model: Optional[str] = None,
                 api_key: Optional[str] = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self._client = None
        self._setup_client()

    def _setup_client(self):
        if self.provider == 'anthropic':
            if HAS_ANTHROPIC:
                key = self.api_key or os.environ.get('ANTHROPIC_API_KEY')
                if key:
                    self._client = anthropic.Anthropic(api_key=key)
                    self.model = self.model or 'claude-3-5-sonnet-20241022'
                else:
                    logger.warning("No Anthropic API key found")
            else:
                logger.warning("anthropic package not installed")

        elif self.provider == 'openai':
            if HAS_OPENAI:
                key = self.api_key or os.environ.get('OPENAI_API_KEY')
                if key:
                    self._client = openai.OpenAI(api_key=key)
                    self.model = self.model or 'gpt-4o'
                else:
                    logger.warning("No OpenAI API key found")
            else:
                logger.warning("openai package not installed")

        elif self.provider == 'mock':
            self._client = 'mock'
            self.model = self.model or 'mock-model'

    def complete(self, system_prompt: str, user_message: str,
                 max_tokens: int = 4096) -> str:
        """Generate a completion."""
        if self._client is None:
            return self._mock_complete(system_prompt, user_message)

        if self.provider == 'mock' or self._client == 'mock':
            return self._mock_complete(system_prompt, user_message)

        try:
            if self.provider == 'anthropic':
                response = self._client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}]
                )
                return response.content[0].text

            elif self.provider == 'openai':
                response = self._client.chat.completions.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ]
                )
                return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM completion error: {e}")
            return self._mock_complete(system_prompt, user_message)

        return ""

    def _mock_complete(self, system_prompt: str, user_message: str) -> str:
        """Mock completion for testing without API keys."""
        return (
            f"[Mock LLM Response]\n"
            f"Based on the provided context, here is a synthesized answer to your query.\n"
            f"The system prompt indicated: {system_prompt[:100]}...\n"
            f"Query: {user_message[:200]}...\n"
            f"This is a mock response. Configure an LLM provider for real answers."
        )


# ============================================================
# Context Builder
# ============================================================

class ContextBuilder:
    """Builds context windows from search results for LLM consumption."""

    def __init__(self, db: Database, max_context_tokens: int = 8000):
        self.db = db
        self.max_context_tokens = max_context_tokens

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def build_context(self, search_results: List[SearchResult],
                      include_surrounding: bool = True) -> Tuple[str, List[Citation]]:
        """Build a context string from search results with citations."""
        context_parts = []
        citations = []
        total_tokens = 0

        for result in search_results:
            doc = self.db.get_document(result.doc_id)
            if not doc:
                continue

            content = result.content
            if include_surrounding:
                content = self._get_surrounding_context(result)

            source_header = self._format_source_header(result, doc)
            section = f"{source_header}\n{content}\n"
            tokens = self._estimate_tokens(section)

            if total_tokens + tokens > self.max_context_tokens:
                remaining = self.max_context_tokens - total_tokens
                if remaining < 200:
                    break
                content = content[:remaining * 4]
                section = f"{source_header}\n{content}\n[truncated]"

            context_parts.append(section)
            total_tokens += tokens

            citation = Citation(
                doc_id=result.doc_id,
                file_path=result.file_path,
                chunk_id=result.chunk_id,
                quote=result.content[:200],
                page_number=result.page_number,
                line_number=result.line_number,
                section_title=result.section_title
            )
            citations.append(citation)

        context = '\n---\n'.join(context_parts)
        return context, citations

    def _format_source_header(self, result: SearchResult,
                               doc: DocumentMetadata) -> str:
        parts = [f"[SOURCE: {doc.title}]"]
        parts.append(f"File: {result.file_path}")
        if result.page_number:
            parts.append(f"Page: {result.page_number}")
        if result.line_number:
            parts.append(f"Line: {result.line_number}")
        if result.section_title:
            parts.append(f"Section: {result.section_title}")
        return ' | '.join(parts)

    def _get_surrounding_context(self, result: SearchResult,
                                  window: int = 1) -> str:
        """Get surrounding chunks for better context."""
        chunks = self.db.get_chunks_for_doc(result.doc_id)
        if not chunks:
            return result.content

        current_idx = None
        for i, chunk in enumerate(chunks):
            if chunk.chunk_id == result.chunk_id:
                current_idx = i
                break

        if current_idx is None:
            return result.content

        start = max(0, current_idx - window)
        end = min(len(chunks), current_idx + window + 1)
        surrounding = chunks[start:end]

        return '\n'.join(c.content for c in surrounding)


# ============================================================
# Research Agent
# ============================================================

class ResearchAgent:
    """The main LLM-powered research agent."""

    SYSTEM_PROMPT = """You are Marginalia, a research assistant for a personal knowledge base.
Your role is to answer questions by carefully reading the provided source documents and synthesizing accurate, well-cited answers.

Guidelines:
1. Base your answers ONLY on the provided source documents
2. Always cite your sources using [SOURCE: filename] notation
3. Quote relevant passages when they directly support your answer
4. If the sources don't contain enough information, say so clearly
5. Organize complex answers with clear structure
6. Note any contradictions or uncertainties in the sources
7. Be precise about page numbers, line numbers, or sections when available
"""

    def __init__(self, db: Database,
                 search_engine: SearchEngine,
                 llm_client: LLMClient,
                 context_builder: ContextBuilder,
                 relation_miner: Optional[RelationMiner] = None):
        self.db = db
        self.search_engine = search_engine
        self.llm_client = llm_client
        self.context_builder = context_builder
        self.relation_miner = relation_miner

    def answer(self, query: str,
               search_limit: int = 10,
               source_quota: Optional[int] = None,
               search_mode: str = 'lexical',
               catalog_id: Optional[str] = None,
               tags: Optional[List[str]] = None,
               save_note: bool = True,
               parent_note_id: Optional[str] = None) -> AgentResponse:
        """Answer a research query."""
        doc_ids = None

        if catalog_id:
            catalog = self.db.get_catalog(catalog_id)
            if catalog:
                doc_ids = catalog.doc_ids

        if tags:
            tagged_docs = self.db.list_documents(tags=tags)
            tagged_ids = [d.doc_id for d in tagged_docs]
            if doc_ids:
                doc_ids = [d for d in doc_ids if d in tagged_ids]
            else:
                doc_ids = tagged_ids

        search_results = self.search_engine.search(
            query,
            limit=search_limit,
            doc_ids=doc_ids,
            source_quota=source_quota,
            search_mode=search_mode
        )

        past_notes = self.db.search_investigation_notes(query)
        past_context = ""
        if past_notes:
            past_context = "\n\nRELEVANT PAST INVESTIGATIONS:\n"
            for note in past_notes[:3]:
                past_context += f"\n[Past Note: {note.query[:100]}]\n{note.answer[:500]}\n"

        context, citations = self.context_builder.build_context(search_results)

        if not context.strip():
            answer_text = (
                "I could not find relevant information in the knowledge base to answer "
                f"your query: '{query}'. Please ensure relevant documents have been ingested."
            )
            return AgentResponse(
                answer=answer_text,
                citations=[],
                sources_consulted=[]
            )

        user_message = f"""Query: {query}

{past_context}

Source Documents:
{context}

Please provide a comprehensive, well-cited answer to the query based on the source documents above."""

        answer_text = self.llm_client.complete(self.SYSTEM_PROMPT, user_message)

        sources_consulted = list(set(r.file_path for r in search_results))

        note_id = None
        if save_note:
            note = self._save_investigation_note(
                query=query,
                answer=answer_text,
                citations=citations,
                sources_consulted=sources_consulted,
                parent_note_id=parent_note_id
            )
            note_id = note.note_id

        return AgentResponse(
            answer=answer_text,
            citations=citations,
            sources_consulted=sources_consulted,
            investigation_note_id=note_id
        )

    def _save_investigation_note(self, query: str, answer: str,
                                  citations: List[Citation],
                                  sources_consulted: List[str],
                                  parent_note_id: Optional[str] = None) -> InvestigationNote:
        """Save an investigation note for future reference."""
        now = datetime.datetime.utcnow().isoformat()
        tags = self._extract_tags_from_query(query)

        note = InvestigationNote(
            note_id=str(uuid.uuid4()),
            query=query,
            answer=answer,
            citations=[{
                'doc_id': c.doc_id,
                'file_path': c.file_path,
                'chunk_id': c.chunk_id,
                'quote': c.quote,
                'page_number': c.page_number,
                'line_number': c.line_number,
                'section_title': c.section_title
            } for c in citations],
            sources_consulted=sources_consulted,
            tags=tags,
            created_at=now,
            updated_at=now,
            parent_note_id=parent_note_id
        )
        self.db.upsert_investigation_note(note)
        return note

    def _extract_tags_from_query(self, query: str) -> List[str]:
        """Extract potential tags from a query."""
        words = re.findall(r'\b[A-Za-z]{4,}\b', query)
        stopwords = {'what', 'when', 'where', 'which', 'that', 'this', 'with',
                     'from', 'have', 'been', 'will', 'does', 'about', 'into',
                     'more', 'some', 'than', 'then', 'they', 'were', 'your',
                     'their', 'there', 'these', 'those', 'would', 'could',
                     'should', 'might', 'must', 'shall', 'also', 'each',
                     'other', 'such', 'only', 'over', 'both', 'very'}
        tags = [w.lower() for w in words if w.lower() not in stopwords]
        return list(set(tags))[:10]

    def generate_report(self, topic: str,
                        search_limit: int = 20,
                        catalog_id: Optional[str] = None) -> str:
        """Generate a structured research report on a topic."""
        response = self.answer(
            query=f"Provide a comprehensive overview of: {topic}",
            search_limit=search_limit,
            catalog_id=catalog_id,
            save_note=True
        )

        report_prompt = f"""Based on the following research answer, format it as a structured report with:
1. Executive Summary
2. Key Findings
3. Detailed Analysis
4. Sources and Citations
5. Gaps and Uncertainties

Research Answer:
{response.answer}

Sources consulted: {', '.join(response.sources_consulted)}
"""
        report = self.llm_client.complete(
            "You are a research report formatter. Create clear, well-structured reports.",
            report_prompt
        )
        return report

    def suggest_relations(self, doc_id: str) -> List[Relation]:
        """Use the relation miner to find document relations."""
        if self.relation_miner:
            return self.relation_miner.mine_all_relations(doc_id)
        return []


# ============================================================
# Catalog Manager
# ============================================================

class CatalogManager:
    """Manages document catalogs."""

    def __init__(self, db: Database):
        self.db = db

    def create_catalog(self, name: str, description: str = "",
                       tags: Optional[List[str]] = None) -> Catalog:
        now = datetime.datetime.utcnow().isoformat()
        catalog = Catalog(
            catalog_id=str(uuid.uuid4()),
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
            doc_ids=[],
            tags=tags or []
        )
        self.db.upsert_catalog(catalog)
        return catalog

    def get_catalog(self, catalog_id: str) -> Optional[Catalog]:
        return self.db.get_catalog(catalog_id)

    def get_catalog_by_name(self, name: str) -> Optional[Catalog]:
        catalogs = self.db.list_catalogs()
        for c in catalogs:
            if c.name == name:
                return c
        return None

    def list_catalogs(self) -> List[Catalog]:
        return self.db.list_catalogs()

    def add_document(self, catalog_id: str, doc_id: str) -> bool:
        catalog = self.db.get_catalog(catalog_id)
        if not catalog:
            return False
        if doc_id not in catalog.doc_ids:
            catalog.doc_ids.append(doc_id)
            catalog.updated_at = datetime.datetime.utcnow().isoformat()
            self.db.upsert_catalog(catalog)
        return True

    def remove_document(self, catalog_id: str, doc_id: str) -> bool:
        catalog = self.db.get_catalog(catalog_id)
        if not catalog:
            return False
        if doc_id in catalog.doc_ids:
            catalog.doc_ids.remove(doc_id)
            catalog.updated_at = datetime.datetime.utcnow().isoformat()
            self.db.upsert_catalog(catalog)
        return True

    def delete_catalog(self, catalog_id: str):
        self.db.conn.execute("DELETE FROM catalogs WHERE catalog_id=?", (catalog_id,))
        self.db.conn.commit()

    def update_catalog(self, catalog_id: str, **kwargs) -> Optional[Catalog]:
        catalog = self.db.get_catalog(catalog_id)
        if not catalog:
            return None
        for k, v in kwargs.items():
            if hasattr(catalog, k):
                setattr(catalog, k, v)
        catalog.updated_at = datetime.datetime.utcnow().isoformat()
        self.db.upsert_catalog(catalog)
        return catalog


# ============================================================
# Tag Manager
# ============================================================

class TagManager:
    """Manages document tags."""

    def __init__(self, db: Database):
        self.db = db

    def add_tags(self, doc_id: str, tags: List[str]) -> bool:
        doc = self.db.get_document(doc_id)
        if not doc:
            return False
        existing = set(doc.tags)
        new_tags = list(existing | set(tags))
        doc.tags = new_tags
        self.db.upsert_document(doc)
        return True

    def remove_tags(self, doc_id: str, tags: List[str]) -> bool:
        doc = self.db.get_document(doc_id)
        if not doc:
            return False
        doc.tags = [t for t in doc.tags if t not in tags]
        self.db.upsert_document(doc)
        return True

    def get_all_tags(self) -> List[str]:
        return self.db.get_all_tags()

    def get_tag_counts(self) -> Dict[str, int]:
        return self.db.get_tag_counts()

    def get_documents_by_tag(self, tag: str) -> List[DocumentMetadata]:
        return self.db.list_documents(tags=[tag])

    def rename_tag(self, old_tag: str, new_tag: str):
        docs = self.get_documents_by_tag(old_tag)
        for doc in docs:
            self.remove_tags(doc.doc_id, [old_tag])
            self.add_tags(doc.doc_id, [new_tag])

    def auto_tag_document(self, doc_id: str,
                           existing_tags: Optional[List[str]] = None) -> List[str]:
        """Auto-tag a document based on its content."""
        doc = self.db.get_document(doc_id)
        if not doc:
            return []

        chunks = self.db.get_chunks_for_doc(doc_id)
        text = ' '.join(c.content for c in chunks[:5])

        words = re.findall(r'\b[A-Za-z]{5,}\b', text.lower())
        word_freq = Counter(words)

        stopwords = {'about', 'above', 'after', 'again', 'against', 'being',
                     'below', 'between', 'could', 'during', 'every', 'first',
                     'found', 'great', 'group', 'having', 'large', 'later',
                     'light', 'might', 'never', 'often', 'other', 'place',
                     'point', 'right', 'shall', 'since', 'small', 'sound',
                     'still', 'study', 'their', 'there', 'these', 'thing',
                     'think', 'those', 'three', 'through', 'under', 'until',
                     'using', 'water', 'where', 'which', 'while', 'world',
                     'would', 'write', 'years', 'young'}

        candidate_tags = [w for w, _ in word_freq.most_common(20)
                          if w not in stopwords][:10]

        if existing_tags:
            candidate_tags = [t for t in candidate_tags if t in existing_tags]

        if candidate_tags:
            self.add_tags(doc_id, candidate_tags)

        return candidate_tags


# ============================================================
# View Manager
# ============================================================

class ViewManager:
    """Manages document views (saved filters)."""

    def __init__(self, db: Database):
        self.db = db

    def create_view(self, name: str, description: str = "",
                    query_filter: Optional[Dict] = None,
                    sort_by: str = 'ingested_at') -> View:
        now = datetime.datetime.utcnow().isoformat()
        view = View(
            view_id=str(uuid.uuid4()),
            name=name,
            description=description,
            query_filter=query_filter or {},
            sort_by=sort_by,
            created_at=now,
            updated_at=now
        )
        self.db.upsert_view(view)
        return view

    def get_view(self, view_id: str) -> Optional[View]:
        return self.db.get_view(view_id)

    def list_views(self) -> List[View]:
        return self.db.list_views()

    def apply_view(self, view_id: str) -> List[DocumentMetadata]:
        """Apply a view's filters and return matching documents."""
        view = self.db.get_view(view_id)
        if not view:
            return []

        f = view.query_filter
        docs = self.db.list_documents(
            folder_path=f.get('folder_path'),
            file_type=f.get('file_type'),
            tags=f.get('tags'),
            catalog_id=f.get('catalog_id')
        )

        sort_key = view.sort_by
        reverse = True

        if sort_key == 'title':
            docs.sort(key=lambda d: d.title.lower(), reverse=False)
        elif sort_key == 'size_bytes':
            docs.sort(key=lambda d: d.size_bytes or 0, reverse=reverse)
        elif sort_key == 'modified_at':
            docs.sort(key=lambda d: d.modified_at or '', reverse=reverse)
        else:
            docs.sort(key=lambda d: d.ingested_at or '', reverse=reverse)

        return docs

    def delete_view(self, view_id: str):
        self.db.conn.execute("DELETE FROM views WHERE view_id=?", (view_id,))
        self.db.conn.commit()

    def update_view(self, view_id: str, **kwargs) -> Optional[View]:
        view = self.db.get_view(view_id)
        if not view:
            return None
        for k, v in kwargs.items():
            if hasattr(view, k):
                setattr(view, k, v)
        view.updated_at = datetime.datetime.utcnow().isoformat()
        self.db.upsert_view(view)
        return view


# ============================================================
# Journal Manager
# ============================================================

class JournalManager:
    """Manages research journal entries."""

    def __init__(self, db: Database):
        self.db = db

    def create_entry(self, title: str, content: str,
                     tags: Optional[List[str]] = None,
                     linked_doc_ids: Optional[List[str]] = None) -> JournalEntry:
        now = datetime.datetime.utcnow().isoformat()
        entry = JournalEntry(
            entry_id=str(uuid.uuid4()),
            title=title,
            content=content,
            tags=tags or [],
            linked_doc_ids=linked_doc_ids or [],
            created_at=now,
            updated_at=now
        )
        self.db.upsert_journal_entry(entry)
        return entry

    def get_entry(self, entry_id: str) -> Optional[JournalEntry]:
        return self.db.get_journal_entry(entry_id)

    def list_entries(self) -> List[JournalEntry]:
        return self.db.list_journal_entries()

    def update_entry(self, entry_id: str, **kwargs) -> Optional[JournalEntry]:
        entry = self.db.get_journal_entry(entry_id)
        if not entry:
            return None
        for k, v in kwargs.items():
            if hasattr(entry, k):
                setattr(entry, k, v)
        entry.updated_at = datetime.datetime.utcnow().isoformat()
        self.db.upsert_journal_entry(entry)
        return entry

    def delete_entry(self, entry_id: str):
        self.db.conn.execute("DELETE FROM journal_entries WHERE entry_id=?", (entry_id,))
        self.db.conn.commit()

    def search_entries(self, query: str) -> List[JournalEntry]:
        query_lower = f"%{query.lower()}%"
        rows = self.db.conn.execute("""
            SELECT entry_id FROM journal_entries
            WHERE LOWER(title) LIKE ? OR LOWER(content) LIKE ?
            ORDER BY created_at DESC
        """, (query_lower, query_lower)).fetchall()
        return [self.db.get_journal_entry(r['entry_id']) for r in rows]

    def link_document(self, entry_id: str, doc_id: str) -> bool:
        entry = self.db.get_journal_entry(entry_id)
        if not entry:
            return False
        if doc_id not in entry.linked_doc_ids:
            entry.linked_doc_ids.append(doc_id)
            entry.updated_at = datetime.datetime.utcnow().isoformat()
            self.db.upsert_journal_entry(entry)
        return True


# ============================================================
# Metadata Manager
# ============================================================

class MetadataManager:
    """Manages document metadata."""

    def __init__(self, db: Database):
        self.db = db

    def update_metadata(self, doc_id: str, **kwargs) -> Optional[DocumentMetadata]:
        doc = self.db.get_document(doc_id)
        if not doc:
            return None
        for k, v in kwargs.items():
            if hasattr(doc, k):
                setattr(doc, k, v)
            else:
                doc.custom_fields[k] = v
        self.db.upsert_document(doc)
        return doc

    def get_metadata(self, doc_id: str) -> Optional[DocumentMetadata]:
        return self.db.get_document(doc_id)

    def bulk_update_metadata(self, updates: Dict[str, Dict]) -> int:
        """Update metadata for multiple documents. Returns count of updated docs."""
        count = 0
        for doc_id, fields in updates.items():
            result = self.update_metadata(doc_id, **fields)
            if result:
                count += 1
        return count

    def export_metadata(self, doc_ids: Optional[List[str]] = None) -> List[Dict]:
        if doc_ids:
            docs = [self.db.get_document(d) for d in doc_ids]
            docs = [d for d in docs if d]
        else:
            docs = self.db.list_documents()
        return [d.to_dict() for d in docs]

    def import_metadata(self, metadata_list: List[Dict]) -> int:
        count = 0
        for meta_dict in metadata_list:
            try:
                meta = DocumentMetadata.from_dict(meta_dict)
                self.db.upsert_document(meta)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to import metadata: {e}")
        return count


# ============================================================
# Investigation Notes Manager
# ============================================================

class InvestigationNotesManager:
    """Manages investigation notes."""

    def __init__(self, db: Database):
        self.db = db

    def get_note(self, note_id: str) -> Optional[InvestigationNote]:
        return self.db.get_investigation_note(note_id)

    def list_notes(self) -> List[InvestigationNote]:
        return self.db.list_investigation_notes()

    def search_notes(self, query: str) -> List[InvestigationNote]:
        return self.db.search_investigation_notes(query)

    def update_note(self, note_id: str, **kwargs) -> Optional[InvestigationNote]:
        note = self.db.get_investigation_note(note_id)
        if not note:
            return None
        for k, v in kwargs.items():
            if hasattr(note, k):
                setattr(note, k, v)
        note.updated_at = datetime.datetime.utcnow().isoformat()
        self.db.upsert_investigation_note(note)
        return note

    def delete_note(self, note_id: str):
        self.db.conn.execute(
            "DELETE FROM investigation_notes WHERE note_id=?", (note_id,)
        )
        self.db.conn.commit()

    def get_note_thread(self, note_id: str) -> List[InvestigationNote]:
        """Get a note and all its descendants."""
        note = self.db.get_investigation_note(note_id)
        if not note:
            return []

        thread = [note]
        all_notes = self.db.list_investigation_notes()

        def find_children(parent_id: str) -> List[InvestigationNote]:
            children = [n for n in all_notes if n.parent_note_id == parent_id]
            result = []
            for child in children:
                result.append(child)
                result.extend(find_children(child.note_id))
            return result

        thread.extend(find_children(note_id))
        return thread

    def export_notes(self, format: str = 'json') -> str:
        notes = self.list_notes()
        if format == 'json':
            return json.dumps([n.to_dict() for n in notes], indent=2)
        elif format == 'markdown':
            parts = []
            for note in notes:
                parts.append(f"# {note.query}\n")
                parts.append(f"*Created: {note.created_at}*\n\n")
                parts.append(f"{note.answer}\n\n")
                if note.sources_consulted:
                    parts.append("**Sources:**\n")
                    for src in note.sources_consulted:
                        parts.append(f"- {src}\n")
                parts.append("\n---\n\n")
            return ''.join(parts)
        return ""


# ============================================================
# Folder Manager
# ============================================================

class FolderManager:
    """Manages the folder structure of the knowledge base."""

    def __init__(self, db: Database, kb_path: str):
        self.db = db
        self.kb_path = Path(kb_path)

    def list_folders(self) -> List[str]:
        rows = self.db.conn.execute(
            "SELECT DISTINCT folder_path FROM documents ORDER BY folder_path"
        ).fetchall()
        return [r['folder_path'] for r in rows if r['folder_path']]

    def get_documents_in_folder(self, folder_path: str,
                                 recursive: bool = True) -> List[DocumentMetadata]:
        return self.db.list_documents(folder_path=folder_path)

    def create_folder(self, folder_path: str):
        full_path = self.kb_path / folder_path
        full_path.mkdir(parents=True, exist_ok=True)

    def move_document(self, doc_id: str, new_folder: str) -> bool:
        doc = self.db.get_document(doc_id)
        if not doc:
            return False

        old_path = Path(doc.file_path)
        new_dir = self.kb_path / new_folder
        new_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_dir / old_path.name

        try:
            shutil.move(str(old_path), str(new_path))
            doc.file_path = str(new_path)
            doc.folder_path = new_folder
            self.db.upsert_document(doc)
            return True
        except Exception as e:
            logger.error(f"Failed to move document: {e}")
            return False

    def get_folder_stats(self) -> Dict[str, Dict]:
        folders = self.list_folders()
        stats = {}
        for folder in folders:
            docs = self.get_documents_in_folder(folder)
            stats[folder] = {
                'document_count': len(docs),
                'total_size': sum(d.size_bytes or 0 for d in docs),
                'file_types': Counter(d.file_type for d in docs)
            }
        return stats


# ============================================================
# Main Marginalia System
# ============================================================

class Marginalia:
    """
    Main entry point for the Marginalia knowledge management system.
    Orchestrates all components.
    """

    def __init__(self, knowledge_base_path: str,
                 db_path: Optional[str] = None,
                 llm_provider: str = 'anthropic',
                 llm_model: Optional[str] = None,
                 llm_api_key: Optional[str] = None,
                 use_embeddings: bool = False,
                 embedding_model: str = 'simple',
                 use_reranking: bool = False,
                 reranker_model: Optional[str] = None,
                 max_context_tokens: int = 8000):

        self.kb_path = Path(knowledge_base_path)
        self.kb_path.mkdir(parents=True, exist_ok=True)

        if db_path is None:
            db_path = str(self.kb_path / '.marginalia' / 'marginalia.db')

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.db = Database(db_path)
        self.parser_registry = ParserRegistry()

        self.ingestion_engine = IngestionEngine(
            self.db, self.parser_registry, str(self.kb_path)
        )

        self.search_engine = SearchEngine(
            self.db,
            use_embeddings=use_embeddings,
            embedding_model=embedding_model,
            use_reranking=use_reranking,
            reranker_model=reranker_model
        )

        self.llm_client = LLMClient(
            provider=llm_provider,
            model=llm_model,
            api_key=llm_api_key
        )

        self.context_builder = ContextBuilder(self.db, max_context_tokens)
        self.relation_miner = RelationMiner(self.db)

        self.agent = ResearchAgent(
            self.db,
            self.search_engine,
            self.llm_client,
            self.context_builder,
            self.relation_miner
        )

        self.catalog_manager = CatalogManager(self.db)
        self.tag_manager = TagManager(self.db)
        self.view_manager = ViewManager(self.db)
        self.journal_manager = JournalManager(self.db)
        self.metadata_manager = MetadataManager(self.db)
        self.notes_manager = InvestigationNotesManager(self.db)
        self.folder_manager = FolderManager(self.db, str(self.kb_path))

        logger.info(f"Marginalia initialized at {self.kb_path}")

    # ---- Ingestion ----

    def ingest(self, path: str,
               tags: Optional[List[str]] = None,
               catalog: Optional[str] = None,
               recursive: bool = True) -> Union[DocumentMetadata, List[DocumentMetadata]]:
        """Ingest a file or directory."""
        catalog_id = None
        if catalog:
            cat = self.catalog_manager.get_catalog_by_name(catalog)
            if not cat:
                cat = self.catalog_manager.create_catalog(catalog)
            catalog_id = cat.catalog_id

        p = Path(path)
        if p.is_dir():
            results = self.ingestion_engine.ingest_directory(
                str(p), recursive=recursive, tags=tags, catalog_id=catalog_id
            )
            if catalog_id:
                for doc in results:
                    self.catalog_manager.add_document(catalog_id, doc.doc_id)
            return results
        else:
            result = self.ingestion_engine.ingest_file(
                str(p), tags=tags, catalog_id=catalog_id
            )
            if result and catalog_id:
                self.catalog_manager.add_document(catalog_id, result.doc_id)
            return result

    def watch_directory(self, directory: str, interval: int = 60,
                        tags: Optional[List[str]] = None,
                        catalog: Optional[str] = None):
        """Watch a directory for new/changed files and auto-ingest them."""
        def _watch():
            while True:
                self.ingest(directory, tags=tags, catalog=catalog)
                time.sleep(interval)

        thread = threading.Thread(target=_watch, daemon=True)
        thread.start()
        logger.info(f"Watching directory: {directory}")
        return thread

    # ---- Search ----

    def search(self, query: str,
               limit: int = 10,
               mode: str = 'lexical',
               catalog: Optional[str] = None,
               tags: Optional[List[str]] = None,
               source_quota: Optional[int] = None) -> List[SearchResult]:
        """Search the knowledge base."""
        doc_ids = None

        if catalog:
            cat = self.catalog_manager.get_catalog_by_name(catalog)
            if cat:
                doc_ids = cat.doc_ids

        if tags:
            tagged_docs = self.db.list_documents(tags=tags)
            tagged_ids = [d.doc_id for d in tagged_docs]
            if doc_ids:
                doc_ids = [d for d in doc_ids if d in tagged_ids]
            else:
                doc_ids = tagged_ids

        return self.search_engine.search(
            query, limit=limit, doc_ids=doc_ids,
            source_quota=source_quota, search_mode=mode
        )

    # ---- Agent ----

    def ask(self, query: str,
            search_limit: int = 10,
            catalog: Optional[str] = None,
            tags: Optional[List[str]] = None,
            source_quota: Optional[int] = None,
            search_mode: str = 'lexical',
            save_note: bool = True,
            parent_note_id: Optional[str] = None) -> AgentResponse:
        """Ask the research agent a question."""
        catalog_id = None
        if catalog:
            cat = self.catalog_manager.get_catalog_by_name(catalog)
            if cat:
                catalog_id = cat.catalog_id

        return self.agent.answer(
            query=query,
            search_limit=search_limit,
            source_quota=source_quota,
            search_mode=search_mode,
            catalog_id=catalog_id,
            tags=tags,
            save_note=save_note,
            parent_note_id=parent_note_id
        )

    def report(self, topic: str,
               search_limit: int = 20,
               catalog: Optional[str] = None) -> str:
        """Generate a research report on a topic."""
        catalog_id = None
        if catalog:
            cat = self.catalog_manager.get_catalog_by_name(catalog)
            if cat:
                catalog_id = cat.catalog_id
        return self.agent.generate_report(topic, search_limit, catalog_id)

    # ---- Documents ----

    def list_documents(self, folder: Optional[str] = None,
                       file_type: Optional[str] = None,
                       tags: Optional[List[str]] = None,
                       catalog: Optional[str] = None) -> List[DocumentMetadata]:
        """List documents in the knowledge base."""
        catalog_id = None
        if catalog:
            cat = self.catalog_manager.get_catalog_by_name(catalog)
            if cat:
                catalog_id = cat.catalog_id
        return self.db.list_documents(
            folder_path=folder, file_type=file_type,
            tags=tags, catalog_id=catalog_id
        )

    def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        return self.db.get_document(doc_id)

    def remove_document(self, doc_id: str):
        self.ingestion_engine.remove_document(doc_id)

    def reindex_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        return self.ingestion_engine.reindex_document(doc_id)

    def reindex_all(self) -> int:
        docs = self.db.list_documents()
        count = 0
        for doc in docs:
            result = self.ingestion_engine.reindex_document(doc.doc_id)
            if result:
                count += 1
        return count

    # ---- Tags ----

    def tag(self, doc_id: str, tags: List[str]) -> bool:
        return self.tag_manager.add_tags(doc_id, tags)

    def untag(self, doc_id: str, tags: List[str]) -> bool:
        return self.tag_manager.remove_tags(doc_id, tags)

    def list_tags(self) -> Dict[str, int]:
        return self.tag_manager.get_tag_counts()

    def auto_tag(self, doc_id: str) -> List[str]:
        existing_tags = self.tag_manager.get_all_tags()
        return self.tag_manager.auto_tag_document(doc_id, existing_tags)

    # ---- Catalogs ----

    def create_catalog(self, name: str, description: str = "") -> Catalog:
        return self.catalog_manager.create_catalog(name, description)

    def list_catalogs(self) -> List[Catalog]:
        return self.catalog_manager.list_catalogs()

    def add_to_catalog(self, catalog_name: str, doc_id: str) -> bool:
        cat = self.catalog_manager.get_catalog_by_name(catalog_name)
        if not cat:
            cat = self.catalog_manager.create_catalog(catalog_name)
        return self.catalog_manager.add_document(cat.catalog_id, doc_id)

    # ---- Views ----

    def create_view(self, name: str, description: str = "",
                    filter: Optional[Dict] = None,
                    sort_by: str = 'ingested_at') -> View:
        return self.view_manager.create_view(name, description, filter, sort_by)

    def list_views(self) -> List[View]:
        return self.view_manager.list_views()

    def apply_view(self, view_name: str) -> List[DocumentMetadata]:
        views = self.view_manager.list_views()
        for v in views:
            if v.name == view_name:
                return self.view_manager.apply_view(v.view_id)
        return []

    # ---- Journal ----

    def journal(self, title: str, content: str,
                tags: Optional[List[str]] = None,
                linked_docs: Optional[List[str]] = None) -> JournalEntry:
        return self.journal_manager.create_entry(title, content, tags, linked_docs)

    def list_journal(self) -> List[JournalEntry]:
        return self.journal_manager.list_entries()

    def search_journal(self, query: str) -> List[JournalEntry]:
        return self.journal_manager.search_entries(query)

    # ---- Investigation Notes ----

    def list_notes(self) -> List[InvestigationNote]:
        return self.notes_manager.list_notes()

    def get_note(self, note_id: str) -> Optional[InvestigationNote]:
        return self.notes_manager.get_note(note_id)

    def search_notes(self, query: str) -> List[InvestigationNote]:
        return self.notes_manager.search_notes(query)

    def export_notes(self, format: str = 'markdown') -> str:
        return self.notes_manager.export_notes(format)

    # ---- Relations ----

    def mine_relations(self, doc_id: str) -> List[Relation]:
        return self.relation_miner.mine_all_relations(doc_id)

    def get_relations(self, doc_id: str) -> List[Relation]:
        return self.db.get_relations_for_doc(doc_id)

    def add_relation(self, source_doc_id: str, target_doc_id: str,
                     relation_type: str, evidence: str = "",
                     confidence: float = 1.0) -> Relation:
        relation = Relation(
            relation_id=str(uuid.uuid4()),
            source_doc_id=source_doc_id,
            target_doc_id=target_doc_id,
            relation_type=relation_type,
            confidence=confidence,
            evidence=evidence,
            created_at=datetime.datetime.utcnow().isoformat()
        )
        self.db.upsert_relation(relation)
        return relation

    # ---- Metadata ----

    def update_metadata(self, doc_id: str, **kwargs) -> Optional[DocumentMetadata]:
        return self.metadata_manager.update_metadata(doc_id, **kwargs)

    def export_metadata(self, doc_ids: Optional[List[str]] = None) -> List[Dict]:
        return self.metadata_manager.export_metadata(doc_ids)

    # ---- Embeddings ----

    def embed_all(self):
        """Compute embeddings for all documents."""
        if self.search_engine.embedding_engine:
            self.search_engine.embed_all_documents()
        else:
            logger.warning("Embeddings not enabled. Initialize with use_embeddings=True")

    def embed_document(self, doc_id: str):
        """Compute embeddings for a specific document."""
        if self.search_engine.embedding_engine:
            self.search_engine.embedding_engine.embed_document(doc_id)

    # ---- Statistics ----

    def stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        docs = self.db.list_documents()
        tags = self.db.get_tag_counts()
        catalogs = self.db.list_catalogs()
        notes = self.db.list_investigation_notes()
        journal = self.db.list_journal_entries()

        file_types = Counter(d.file_type for d in docs)
        total_size = sum(d.size_bytes or 0 for d in docs)
        total_words = sum(d.word_count or 0 for d in docs)

        return {
            'document_count': len(docs),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'total_words': total_words,
            'file_types': dict(file_types),
            'tag_count': len(tags),
            'top_tags': dict(list(tags.items())[:10]),
            'catalog_count': len(catalogs),
            'investigation_note_count': len(notes),
            'journal_entry_count': len(journal),
            'kb_path': str(self.kb_path)
        }

    # ---- Export ----

    def export_knowledge_base(self, output_path: str,
                               format: str = 'json') -> str:
        """Export the entire knowledge base metadata."""
        output = {
            'exported_at': datetime.datetime.utcnow().isoformat(),
            'stats': self.stats(),
            'documents': self.metadata_manager.export_metadata(),
            'catalogs': [c.to_dict() for c in self.catalog_manager.list_catalogs()],
            'views': [v.to_dict() for v in self.view_manager.list_views()],
            'journal_entries': [e.to_dict() for e in self.journal_manager.list_entries()],
            'investigation_notes': [n.to_dict() for n in self.notes_manager.list_notes()]
        }

        output_path = Path(output_path)
        if format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, default=str)
        elif format == 'markdown':
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# Marginalia Knowledge Base Export\n\n")
                f.write(f"Exported: {output['exported_at']}\n\n")
                f.write(f"## Statistics\n\n")
                for k, v in output['stats'].items():
                    f.write(f"- **{k}**: {v}\n")
                f.write(f"\n## Documents\n\n")
                for doc in output['documents']:
                    f.write(f"### {doc['title']}\n")
                    f.write(f"- Path: {doc['file_path']}\n")
                    f.write(f"- Type: {doc['file_type']}\n")
                    f.write(f"- Tags: {', '.join(doc['tags'])}\n\n")

        return str(output_path)

    def __repr__(self) -> str:
        stats = self.stats()
        return (
            f"Marginalia(kb_path='{self.kb_path}', "
            f"documents={stats['document_count']}, "
            f"tags={stats['tag_count']})"
        )


# ============================================================
# CLI Interface
# ============================================================

class MarginaliaShell:
    """Interactive shell for Marginalia."""

    def __init__(self, marginalia: Marginalia):
        self.m = marginalia
        self.running = True

    def run(self):
        """Run the interactive shell."""
        print(f"\n{'='*60}")
        print("  Marginalia - Personal Knowledge Management System")
        print(f"{'='*60}")
        print(f"  Knowledge base: {self.m.kb_path}")
        stats = self.m.stats()
        print(f"  Documents: {stats['document_count']} | "
              f"Tags: {stats['tag_count']} | "
              f"Notes: {stats['investigation_note_count']}")
        print(f"{'='*60}")
        print("  Type 'help' for commands\n")

        while self.running:
            try:
                line = input("marginalia> ").strip()
                if not line:
                    continue
                self._dispatch(line)
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except EOFError:
                break

    def _dispatch(self, line: str):
        parts = line.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        commands = {
            'help': self._cmd_help,
            'ingest': self._cmd_ingest,
            'search': self._cmd_search,
            'ask': self._cmd_ask,
            'report': self._cmd_report,
            'list': self._cmd_list,
            'stats': self._cmd_stats,
            'tag': self._cmd_tag,
            'catalog': self._cmd_catalog,
            'note': self._cmd_note,
            'journal': self._cmd_journal,
            'quit': self._cmd_quit,
            'exit': self._cmd_quit,
        }

        handler = commands.get(cmd)
        if handler:
            handler(args)
        else:
            print(f"Unknown command: {cmd}. Type 'help' for commands.")

    def _cmd_help(self, args: str):
        print("""
Commands:
  ingest <path>          - Ingest a file or directory
  search <query>         - Search the knowledge base
  ask <question>         - Ask the research agent
  report <topic>         - Generate a research report
  list [folder]          - List documents
  stats                  - Show knowledge base statistics
  tag <doc_id> <tags>    - Tag a document
  catalog <name>         - List or create catalogs
  note [query]           - List or search investigation notes
  journal <title>        - Create a journal entry
  quit/exit              - Exit Marginalia
""")

    def _cmd_ingest(self, args: str):
        if not args:
            print("Usage: ingest <path>")
            return
        result = self.m.ingest(args)
        if isinstance(result, list):
            print(f"Ingested {len(result)} documents")
        elif result:
            print(f"Ingested: {result.title} ({result.doc_id[:8]}...)")
        else:
            print("Ingestion failed")

    def _cmd_search(self, args: str):
        if not args:
            print("Usage: search <query>")
            return
        results = self.m.search(args, limit=5)
        if not results:
            print("No results found")
            return
        print(f"\nFound {len(results)} results:\n")
        for r in results:
            print(f"  [{r.rank+1}] {Path(r.file_path).name}")
            if r.section_title:
                print(f"      Section: {r.section_title}")
            if r.page_number:
                print(f"      Page: {r.page_number}")
            print(f"      Score: {r.score:.4f}")
            print(f"      {r.content[:150]}...")
            print()

    def _cmd_ask(self, args: str):
        if not args:
            print("Usage: ask <question>")
            return
        print(f"\nResearching: {args}\n")
        response = self.m.ask(args)
        print("Answer:")
        print("-" * 40)
        print(response.answer)
        print("-" * 40)
        if response.citations:
            print(f"\nCitations ({len(response.citations)}):")
            for c in response.citations[:5]:
                print(f"  - {Path(c.file_path).name}: {c.quote[:80]}...")
        if response.investigation_note_id:
            print(f"\nNote saved: {response.investigation_note_id[:8]}...")
        print()

    def _cmd_report(self, args: str):
        if not args:
            print("Usage: report <topic>")
            return
        print(f"\nGenerating report on: {args}\n")
        report = self.m.report(args)
        print(report)
        print()

    def _cmd_list(self, args: str):
        docs = self.m.list_documents(folder=args if args else None)
        if not docs:
            print("No documents found")
            return
        print(f"\n{len(docs)} documents:\n")
        for doc in docs[:20]:
            tags_str = ', '.join(doc.tags[:3]) if doc.tags else 'no tags'
            print(f"  {doc.doc_id[:8]}... | {doc.title[:40]} | {doc.file_type} | [{tags_str}]")
        if len(docs) > 20:
            print(f"  ... and {len(docs) - 20} more")
        print()

    def _cmd_stats(self, args: str):
        stats = self.m.stats()
        print("\nKnowledge Base Statistics:")
        print("-" * 40)
        for k, v in stats.items():
            if k not in ('file_types', 'top_tags'):
                print(f"  {k}: {v}")
        if stats.get('file_types'):
            print("\n  File Types:")
            for ft, count in stats['file_types'].items():
                print(f"    {ft}: {count}")
        if stats.get('top_tags'):
            print("\n  Top Tags:")
            for tag, count in list(stats['top_tags'].items())[:10]:
                print(f"    {tag}: {count}")
        print()

    def _cmd_tag(self, args: str):
        parts = args.split(None, 1)
        if len(parts) < 2:
            print("Usage: tag <doc_id> <tag1> [tag2] ...")
            return
        doc_id = parts[0]
        tags = parts[1].split()
        if self.m.tag(doc_id, tags):
            print(f"Tagged {doc_id[:8]}... with: {', '.join(tags)}")
        else:
            print(f"Document not found: {doc_id}")

    def _cmd_catalog(self, args: str):
        if not args:
            catalogs = self.m.list_catalogs()
            if not catalogs:
                print("No catalogs found")
                return
            print(f"\n{len(catalogs)} catalogs:\n")
            for c in catalogs:
                print(f"  {c.catalog_id[:8]}... | {c.name} | {len(c.doc_ids)} docs")
            print()
        else:
            cat = self.m.create_catalog(args)
            print(f"Created catalog: {cat.name} ({cat.catalog_id[:8]}...)")

    def _cmd_note(self, args: str):
        if args:
            notes = self.m.search_notes(args)
        else:
            notes = self.m.list_notes()

        if not notes:
            print("No notes found")
            return

        print(f"\n{len(notes)} investigation notes:\n")
        for note in notes[:10]:
            print(f"  {note.note_id[:8]}... | {note.query[:60]}")
            print(f"    Created: {note.created_at[:10]}")
            print(f"    Sources: {len(note.sources_consulted)}")
            print()

    def _cmd_journal(self, args: str):
        if not args:
            entries = self.m.list_journal()
            if not entries:
                print("No journal entries found")
                return
            print(f"\n{len(entries)} journal entries:\n")
            for e in entries[:10]:
                print(f"  {e.entry_id[:8]}... | {e.title} | {e.created_at[:10]}")
            print()
        else:
            content = input("Content: ")
            tags_input = input("Tags (comma-separated): ")
            tags = [t.strip() for t in tags_input.split(',') if t.strip()]
            entry = self.m.journal(args, content, tags)
            print(f"Journal entry created: {entry.entry_id[:8]}...")

    def _cmd_quit(self, args: str):
        print("Goodbye!")
        self.running = False


# ============================================================
# Factory Functions
# ============================================================

def create_marginalia(kb_path: str = "./knowledge_base",
                      llm_provider: str = 'anthropic',
                      llm_model: Optional[str] = None,
                      llm_api_key: Optional[str] = None,
                      use_embeddings: bool = False,
                      use_reranking: bool = False) -> Marginalia:
    """Factory function to create a Marginalia instance."""
    return Marginalia(
        knowledge_base_path=kb_path,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        use_embeddings=use_embeddings,
        use_reranking=use_reranking
    )


def run_shell(kb_path: str = "./knowledge_base",
              llm_provider: str = 'anthropic',
              llm_api_key: Optional[str] = None):
    """Run the interactive Marginalia shell."""
    m = create_marginalia(kb_path, llm_provider=llm_provider, llm_api_key=llm_api_key)
    shell = MarginaliaShell(m)
    shell.run()


# ============================================================
# Entry Point
# ============================================================

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        kb_path = sys.argv[1]
    else:
        kb_path = "./knowledge_base"

    llm_provider = os.environ.get('MARGINALIA_LLM_PROVIDER', 'anthropic')
    llm_api_key = os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('OPENAI_API_KEY')

    if not llm_api_key:
        llm_provider = 'mock'

    run_shell(kb_path=kb_path, llm_provider=llm_provider, llm_api_key=llm_api_key)