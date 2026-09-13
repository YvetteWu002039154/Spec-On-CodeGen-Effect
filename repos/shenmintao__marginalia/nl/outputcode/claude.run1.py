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
import zipfile
import tarfile
import sqlite3
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


# ─────────────────────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DocumentMetadata:
    doc_id: str
    file_path: str
    title: str
    file_type: str
    file_size: int
    created_at: str
    modified_at: str
    ingested_at: str
    checksum: str
    tags: List[str] = field(default_factory=list)
    catalog_id: Optional[str] = None
    folder_path: str = ""
    language: str = "en"
    word_count: int = 0
    page_count: int = 0
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    relations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'DocumentMetadata':
        return cls(**data)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    content: str
    chunk_index: int
    start_offset: int
    end_offset: int
    chunk_type: str = "text"
    page_number: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    section_title: Optional[str] = None
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        d.pop('embedding', None)
        return d


@dataclass
class SearchResult:
    doc_id: str
    chunk_id: str
    file_path: str
    title: str
    content: str
    score: float
    chunk_index: int
    page_number: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    section_title: Optional[str] = None
    match_type: str = "lexical"

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Citation:
    doc_id: str
    file_path: str
    title: str
    chunk_id: str
    content_excerpt: str
    page_number: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    section_title: Optional[str] = None

    def format(self) -> str:
        parts = [f"[{self.title}]"]
        if self.page_number:
            parts.append(f"p.{self.page_number}")
        if self.line_start:
            parts.append(f"L{self.line_start}")
        if self.section_title:
            parts.append(f"§{self.section_title}")
        parts.append(f"({self.file_path})")
        return " ".join(parts)


@dataclass
class InvestigationNote:
    note_id: str
    query: str
    answer: str
    citations: List[Citation]
    created_at: str
    tags: List[str] = field(default_factory=list)
    follow_up_questions: List[str] = field(default_factory=list)
    related_note_ids: List[str] = field(default_factory=list)
    journal_id: Optional[str] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'InvestigationNote':
        citations = [Citation(**c) for c in data.get('citations', [])]
        data['citations'] = citations
        return cls(**data)


@dataclass
class Catalog:
    catalog_id: str
    name: str
    description: str
    created_at: str
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
    created_at: str
    sort_by: str = "ingested_at"
    sort_order: str = "desc"
    tags_filter: List[str] = field(default_factory=list)
    file_types_filter: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Journal:
    journal_id: str
    name: str
    description: str
    created_at: str
    note_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Database Layer
# ─────────────────────────────────────────────────────────────────────────────

class Database:
    """SQLite-backed storage for all Marginalia data."""

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
                file_size INTEGER,
                created_at TEXT,
                modified_at TEXT,
                ingested_at TEXT,
                checksum TEXT,
                tags TEXT DEFAULT '[]',
                catalog_id TEXT,
                folder_path TEXT DEFAULT '',
                language TEXT DEFAULT 'en',
                word_count INTEGER DEFAULT 0,
                page_count INTEGER DEFAULT 0,
                custom_metadata TEXT DEFAULT '{}',
                relations TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_index INTEGER,
                start_offset INTEGER,
                end_offset INTEGER,
                chunk_type TEXT DEFAULT 'text',
                page_number INTEGER,
                line_start INTEGER,
                line_end INTEGER,
                section_title TEXT,
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

            CREATE TABLE IF NOT EXISTS chunk_embeddings (
                chunk_id TEXT PRIMARY KEY,
                embedding BLOB,
                dim INTEGER,
                FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS catalogs (
                catalog_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT,
                doc_ids TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS views (
                view_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                query_filter TEXT DEFAULT '{}',
                created_at TEXT,
                sort_by TEXT DEFAULT 'ingested_at',
                sort_order TEXT DEFAULT 'desc',
                tags_filter TEXT DEFAULT '[]',
                file_types_filter TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS journals (
                journal_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT,
                note_ids TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS investigation_notes (
                note_id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                answer TEXT NOT NULL,
                citations TEXT DEFAULT '[]',
                created_at TEXT,
                tags TEXT DEFAULT '[]',
                follow_up_questions TEXT DEFAULT '[]',
                related_note_ids TEXT DEFAULT '[]',
                journal_id TEXT
            );

            CREATE TABLE IF NOT EXISTS relations (
                relation_id TEXT PRIMARY KEY,
                source_doc_id TEXT NOT NULL,
                target_doc_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                created_at TEXT,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS tags (
                tag_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                color TEXT,
                description TEXT,
                created_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
            CREATE INDEX IF NOT EXISTS idx_documents_folder ON documents(folder_path);
            CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(file_type);
            CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_doc_id);
            CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_doc_id);
        """)
        conn.commit()

    def upsert_document(self, meta: DocumentMetadata):
        self.conn.execute("""
            INSERT OR REPLACE INTO documents
            (doc_id, file_path, title, file_type, file_size, created_at, modified_at,
             ingested_at, checksum, tags, catalog_id, folder_path, language,
             word_count, page_count, custom_metadata, relations)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            meta.doc_id, meta.file_path, meta.title, meta.file_type,
            meta.file_size, meta.created_at, meta.modified_at, meta.ingested_at,
            meta.checksum, json.dumps(meta.tags), meta.catalog_id, meta.folder_path,
            meta.language, meta.word_count, meta.page_count,
            json.dumps(meta.custom_metadata), json.dumps(meta.relations)
        ))
        self.conn.commit()

    def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        row = self.conn.execute(
            "SELECT * FROM documents WHERE doc_id=?", (doc_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_doc(row)

    def get_document_by_path(self, file_path: str) -> Optional[DocumentMetadata]:
        row = self.conn.execute(
            "SELECT * FROM documents WHERE file_path=?", (file_path,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_doc(row)

    def _row_to_doc(self, row) -> DocumentMetadata:
        d = dict(row)
        d['tags'] = json.loads(d.get('tags', '[]'))
        d['custom_metadata'] = json.loads(d.get('custom_metadata', '{}'))
        d['relations'] = json.loads(d.get('relations', '[]'))
        return DocumentMetadata(**d)

    def list_documents(self, folder_path: Optional[str] = None,
                       file_type: Optional[str] = None,
                       tags: Optional[List[str]] = None,
                       limit: int = 100, offset: int = 0) -> List[DocumentMetadata]:
        query = "SELECT * FROM documents WHERE 1=1"
        params = []
        if folder_path:
            query += " AND folder_path LIKE ?"
            params.append(f"{folder_path}%")
        if file_type:
            query += " AND file_type=?"
            params.append(file_type)
        query += " ORDER BY ingested_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self.conn.execute(query, params).fetchall()
        docs = [self._row_to_doc(r) for r in rows]
        if tags:
            filtered = []
            for doc in docs:
                if any(t in doc.tags for t in tags):
                    filtered.append(doc)
            return filtered
        return docs

    def delete_document(self, doc_id: str):
        self.conn.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
        self.conn.commit()

    def insert_chunk(self, chunk: Chunk):
        self.conn.execute("""
            INSERT OR REPLACE INTO chunks
            (chunk_id, doc_id, content, chunk_index, start_offset, end_offset,
             chunk_type, page_number, line_start, line_end, section_title)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            chunk.chunk_id, chunk.doc_id, chunk.content, chunk.chunk_index,
            chunk.start_offset, chunk.end_offset, chunk.chunk_type,
            chunk.page_number, chunk.line_start, chunk.line_end, chunk.section_title
        ))
        self.conn.execute("""
            INSERT OR REPLACE INTO chunks_fts(chunk_id, doc_id, content, section_title)
            VALUES (?,?,?,?)
        """, (chunk.chunk_id, chunk.doc_id, chunk.content, chunk.section_title or ""))
        self.conn.commit()

    def insert_chunks_batch(self, chunks: List[Chunk]):
        self.conn.executemany("""
            INSERT OR REPLACE INTO chunks
            (chunk_id, doc_id, content, chunk_index, start_offset, end_offset,
             chunk_type, page_number, line_start, line_end, section_title)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, [
            (c.chunk_id, c.doc_id, c.content, c.chunk_index,
             c.start_offset, c.end_offset, c.chunk_type,
             c.page_number, c.line_start, c.line_end, c.section_title)
            for c in chunks
        ])
        self.conn.executemany("""
            INSERT OR REPLACE INTO chunks_fts(chunk_id, doc_id, content, section_title)
            VALUES (?,?,?,?)
        """, [(c.chunk_id, c.doc_id, c.content, c.section_title or "") for c in chunks])
        self.conn.commit()

    def get_chunks_for_doc(self, doc_id: str) -> List[Chunk]:
        rows = self.conn.execute(
            "SELECT * FROM chunks WHERE doc_id=? ORDER BY chunk_index", (doc_id,)
        ).fetchall()
        return [self._row_to_chunk(r) for r in rows]

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        row = self.conn.execute(
            "SELECT * FROM chunks WHERE chunk_id=?", (chunk_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_chunk(row)

    def _row_to_chunk(self, row) -> Chunk:
        d = dict(row)
        d['embedding'] = None
        return Chunk(**d)

    def delete_chunks_for_doc(self, doc_id: str):
        self.conn.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        self.conn.commit()

    def fts_search(self, query: str, limit: int = 20) -> List[Dict]:
        safe_query = query.replace('"', '""')
        try:
            rows = self.conn.execute("""
                SELECT c.chunk_id, c.doc_id, c.content, c.chunk_index,
                       c.page_number, c.line_start, c.line_end, c.section_title,
                       bm25(chunks_fts) as score
                FROM chunks_fts
                JOIN chunks c ON chunks_fts.chunk_id = c.chunk_id
                WHERE chunks_fts MATCH ?
                ORDER BY score
                LIMIT ?
            """, (safe_query, limit)).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.OperationalError as e:
            logger.warning(f"FTS search error: {e}")
            return self._fallback_search(query, limit)

    def _fallback_search(self, query: str, limit: int = 20) -> List[Dict]:
        terms = query.lower().split()
        rows = self.conn.execute(
            "SELECT chunk_id, doc_id, content, chunk_index, page_number, "
            "line_start, line_end, section_title FROM chunks LIMIT 1000"
        ).fetchall()
        results = []
        for row in rows:
            content_lower = row['content'].lower()
            score = sum(content_lower.count(t) for t in terms)
            if score > 0:
                d = dict(row)
                d['score'] = -score
                results.append(d)
        results.sort(key=lambda x: x['score'])
        return results[:limit]

    def store_embedding(self, chunk_id: str, embedding: List[float]):
        if not HAS_NUMPY:
            return
        arr = np.array(embedding, dtype=np.float32)
        self.conn.execute("""
            INSERT OR REPLACE INTO chunk_embeddings(chunk_id, embedding, dim)
            VALUES (?,?,?)
        """, (chunk_id, arr.tobytes(), len(embedding)))
        self.conn.commit()

    def get_embedding(self, chunk_id: str) -> Optional[List[float]]:
        if not HAS_NUMPY:
            return None
        row = self.conn.execute(
            "SELECT embedding, dim FROM chunk_embeddings WHERE chunk_id=?", (chunk_id,)
        ).fetchone()
        if not row:
            return None
        arr = np.frombuffer(row['embedding'], dtype=np.float32)
        return arr.tolist()

    def get_all_embeddings(self) -> List[Tuple[str, List[float]]]:
        if not HAS_NUMPY:
            return []
        rows = self.conn.execute(
            "SELECT chunk_id, embedding FROM chunk_embeddings"
        ).fetchall()
        result = []
        for row in rows:
            arr = np.frombuffer(row['embedding'], dtype=np.float32)
            result.append((row['chunk_id'], arr.tolist()))
        return result

    def upsert_catalog(self, catalog: Catalog):
        self.conn.execute("""
            INSERT OR REPLACE INTO catalogs
            (catalog_id, name, description, created_at, doc_ids, tags, metadata)
            VALUES (?,?,?,?,?,?,?)
        """, (
            catalog.catalog_id, catalog.name, catalog.description,
            catalog.created_at, json.dumps(catalog.doc_ids),
            json.dumps(catalog.tags), json.dumps(catalog.metadata)
        ))
        self.conn.commit()

    def get_catalog(self, catalog_id: str) -> Optional[Catalog]:
        row = self.conn.execute(
            "SELECT * FROM catalogs WHERE catalog_id=?", (catalog_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d['doc_ids'] = json.loads(d.get('doc_ids', '[]'))
        d['tags'] = json.loads(d.get('tags', '[]'))
        d['metadata'] = json.loads(d.get('metadata', '{}'))
        return Catalog(**d)

    def list_catalogs(self) -> List[Catalog]:
        rows = self.conn.execute("SELECT * FROM catalogs").fetchall()
        catalogs = []
        for row in rows:
            d = dict(row)
            d['doc_ids'] = json.loads(d.get('doc_ids', '[]'))
            d['tags'] = json.loads(d.get('tags', '[]'))
            d['metadata'] = json.loads(d.get('metadata', '{}'))
            catalogs.append(Catalog(**d))
        return catalogs

    def upsert_view(self, view: View):
        self.conn.execute("""
            INSERT OR REPLACE INTO views
            (view_id, name, description, query_filter, created_at, sort_by,
             sort_order, tags_filter, file_types_filter)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            view.view_id, view.name, view.description,
            json.dumps(view.query_filter), view.created_at,
            view.sort_by, view.sort_order,
            json.dumps(view.tags_filter), json.dumps(view.file_types_filter)
        ))
        self.conn.commit()

    def get_view(self, view_id: str) -> Optional[View]:
        row = self.conn.execute(
            "SELECT * FROM views WHERE view_id=?", (view_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d['query_filter'] = json.loads(d.get('query_filter', '{}'))
        d['tags_filter'] = json.loads(d.get('tags_filter', '[]'))
        d['file_types_filter'] = json.loads(d.get('file_types_filter', '[]'))
        return View(**d)

    def list_views(self) -> List[View]:
        rows = self.conn.execute("SELECT * FROM views").fetchall()
        views = []
        for row in rows:
            d = dict(row)
            d['query_filter'] = json.loads(d.get('query_filter', '{}'))
            d['tags_filter'] = json.loads(d.get('tags_filter', '[]'))
            d['file_types_filter'] = json.loads(d.get('file_types_filter', '[]'))
            views.append(View(**d))
        return views

    def upsert_journal(self, journal: Journal):
        self.conn.execute("""
            INSERT OR REPLACE INTO journals
            (journal_id, name, description, created_at, note_ids, tags)
            VALUES (?,?,?,?,?,?)
        """, (
            journal.journal_id, journal.name, journal.description,
            journal.created_at, json.dumps(journal.note_ids), json.dumps(journal.tags)
        ))
        self.conn.commit()

    def get_journal(self, journal_id: str) -> Optional[Journal]:
        row = self.conn.execute(
            "SELECT * FROM journals WHERE journal_id=?", (journal_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d['note_ids'] = json.loads(d.get('note_ids', '[]'))
        d['tags'] = json.loads(d.get('tags', '[]'))
        return Journal(**d)

    def list_journals(self) -> List[Journal]:
        rows = self.conn.execute("SELECT * FROM journals").fetchall()
        journals = []
        for row in rows:
            d = dict(row)
            d['note_ids'] = json.loads(d.get('note_ids', '[]'))
            d['tags'] = json.loads(d.get('tags', '[]'))
            journals.append(Journal(**d))
        return journals

    def upsert_note(self, note: InvestigationNote):
        self.conn.execute("""
            INSERT OR REPLACE INTO investigation_notes
            (note_id, query, answer, citations, created_at, tags,
             follow_up_questions, related_note_ids, journal_id)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            note.note_id, note.query, note.answer,
            json.dumps([asdict(c) for c in note.citations]),
            note.created_at, json.dumps(note.tags),
            json.dumps(note.follow_up_questions),
            json.dumps(note.related_note_ids), note.journal_id
        ))
        self.conn.commit()

    def get_note(self, note_id: str) -> Optional[InvestigationNote]:
        row = self.conn.execute(
            "SELECT * FROM investigation_notes WHERE note_id=?", (note_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_note(row)

    def _row_to_note(self, row) -> InvestigationNote:
        d = dict(row)
        citations_data = json.loads(d.get('citations', '[]'))
        d['citations'] = [Citation(**c) for c in citations_data]
        d['tags'] = json.loads(d.get('tags', '[]'))
        d['follow_up_questions'] = json.loads(d.get('follow_up_questions', '[]'))
        d['related_note_ids'] = json.loads(d.get('related_note_ids', '[]'))
        return InvestigationNote(**d)

    def list_notes(self, journal_id: Optional[str] = None,
                   tags: Optional[List[str]] = None,
                   limit: int = 50) -> List[InvestigationNote]:
        query = "SELECT * FROM investigation_notes WHERE 1=1"
        params = []
        if journal_id:
            query += " AND journal_id=?"
            params.append(journal_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(query, params).fetchall()
        notes = [self._row_to_note(r) for r in rows]
        if tags:
            filtered = []
            for note in notes:
                if any(t in note.tags for t in tags):
                    filtered.append(note)
            return filtered
        return notes

    def search_notes(self, query: str, limit: int = 10) -> List[InvestigationNote]:
        query_lower = query.lower()
        rows = self.conn.execute(
            "SELECT * FROM investigation_notes ORDER BY created_at DESC LIMIT 200"
        ).fetchall()
        scored = []
        for row in rows:
            note = self._row_to_note(row)
            score = 0
            if query_lower in note.query.lower():
                score += 3
            if query_lower in note.answer.lower():
                score += 1
            if score > 0:
                scored.append((score, note))
        scored.sort(key=lambda x: -x[0])
        return [n for _, n in scored[:limit]]

    def upsert_relation(self, source_id: str, target_id: str,
                        relation_type: str, confidence: float = 1.0,
                        metadata: Optional[Dict] = None):
        relation_id = str(uuid.uuid4())
        self.conn.execute("""
            INSERT OR REPLACE INTO relations
            (relation_id, source_doc_id, target_doc_id, relation_type,
             confidence, created_at, metadata)
            VALUES (?,?,?,?,?,?,?)
        """, (
            relation_id, source_id, target_id, relation_type,
            confidence, datetime.datetime.utcnow().isoformat(),
            json.dumps(metadata or {})
        ))
        self.conn.commit()

    def get_relations(self, doc_id: str) -> List[Dict]:
        rows = self.conn.execute("""
            SELECT * FROM relations
            WHERE source_doc_id=? OR target_doc_id=?
        """, (doc_id, doc_id)).fetchall()
        return [dict(r) for r in rows]

    def upsert_tag(self, name: str, color: Optional[str] = None,
                   description: Optional[str] = None):
        tag_id = str(uuid.uuid4())
        self.conn.execute("""
            INSERT OR IGNORE INTO tags(tag_id, name, color, description, created_at)
            VALUES (?,?,?,?,?)
        """, (tag_id, name, color, description,
              datetime.datetime.utcnow().isoformat()))
        self.conn.commit()

    def list_tags(self) -> List[Dict]:
        rows = self.conn.execute("SELECT * FROM tags ORDER BY name").fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# File Ingestion
# ─────────────────────────────────────────────────────────────────────────────

class FileIngester:
    """Handles reading and extracting text from various file types."""

    SUPPORTED_EXTENSIONS = {
        '.txt', '.md', '.markdown', '.rst', '.org',
        '.pdf', '.docx', '.doc',
        '.xlsx', '.xls', '.csv', '.tsv',
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp',
        '.log', '.json', '.xml', '.html', '.htm', '.yaml', '.yml',
        '.zip', '.tar', '.gz', '.tar.gz', '.tar.bz2', '.tar.xz',
        '.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.go',
        '.rs', '.rb', '.php', '.sh', '.bash', '.zsh',
    }

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    def can_ingest(self, file_path: str) -> bool:
        path = Path(file_path)
        suffix = path.suffix.lower()
        return suffix in self.SUPPORTED_EXTENSIONS

    def ingest_file(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Returns (text_content, extra_metadata)."""
        path = Path(file_path)
        suffix = path.suffix.lower()
        extra = {}

        try:
            if suffix in ('.txt', '.md', '.markdown', '.rst', '.org',
                          '.log', '.json', '.xml', '.html', '.htm',
                          '.yaml', '.yml', '.py', '.js', '.ts', '.java',
                          '.c', '.cpp', '.h', '.go', '.rs', '.rb', '.php',
                          '.sh', '.bash', '.zsh'):
                text = self._read_text_file(file_path)
            elif suffix == '.pdf':
                text, extra = self._read_pdf(file_path)
            elif suffix in ('.docx', '.doc'):
                text, extra = self._read_docx(file_path)
            elif suffix in ('.xlsx', '.xls'):
                text, extra = self._read_excel(file_path)
            elif suffix in ('.csv', '.tsv'):
                text = self._read_csv(file_path)
            elif suffix in ('.png', '.jpg', '.jpeg', '.gif', '.bmp',
                            '.tiff', '.webp'):
                text, extra = self._read_image(file_path)
            elif suffix in ('.zip', '.tar', '.gz', '.tar.gz',
                            '.tar.bz2', '.tar.xz'):
                text, extra = self._read_archive(file_path)
            else:
                text = self._read_text_file(file_path)
        except Exception as e:
            logger.warning(f"Error ingesting {file_path}: {e}")
            text = f"[Error reading file: {e}]"

        return text, extra

    def _read_text_file(self, file_path: str) -> str:
        encodings = ['utf-8', 'latin-1', 'cp1252', 'ascii']
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        with open(file_path, 'rb') as f:
            return f.read().decode('utf-8', errors='replace')

    def _read_pdf(self, file_path: str) -> Tuple[str, Dict]:
        if not HAS_PYPDF:
            return f"[PDF: {Path(file_path).name} - pypdf not installed]", {}
        pages = []
        page_count = 0
        try:
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                page_count = len(reader.pages)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    pages.append(f"[Page {i+1}]\n{text}")
        except Exception as e:
            return f"[PDF read error: {e}]", {}
        return "\n\n".join(pages), {"page_count": page_count}

    def _read_docx(self, file_path: str) -> Tuple[str, Dict]:
        if not HAS_DOCX:
            return f"[DOCX: {Path(file_path).name} - python-docx not installed]", {}
        try:
            doc = docx.Document(file_path)
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            text = "\n\n".join(paragraphs)
            return text, {"paragraph_count": len(paragraphs)}
        except Exception as e:
            return f"[DOCX read error: {e}]", {}

    def _read_excel(self, file_path: str) -> Tuple[str, Dict]:
        if not HAS_OPENPYXL:
            return f"[Excel: {Path(file_path).name} - openpyxl not installed]", {}
        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheets_text = []
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = []
                for row in ws.iter_rows(values_only=True):
                    row_str = "\t".join(str(c) if c is not None else "" for c in row)
                    if row_str.strip():
                        rows.append(row_str)
                if rows:
                    sheets_text.append(f"[Sheet: {sheet_name}]\n" + "\n".join(rows))
            return "\n\n".join(sheets_text), {"sheet_count": len(wb.sheetnames)}
        except Exception as e:
            return f"[Excel read error: {e}]", {}

    def _read_csv(self, file_path: str) -> str:
        try:
            import csv as csv_module
            lines = []
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv_module.reader(f)
                for row in reader:
                    lines.append("\t".join(row))
            return "\n".join(lines)
        except Exception as e:
            return f"[CSV read error: {e}]"

    def _read_image(self, file_path: str) -> Tuple[str, Dict]:
        extra = {}
        if HAS_PIL:
            try:
                img = Image.open(file_path)
                extra = {
                    "image_size": f"{img.width}x{img.height}",
                    "image_mode": img.mode,
                    "image_format": img.format
                }
            except Exception:
                pass
        text = f"[Image: {Path(file_path).name}]"
        if extra:
            text += f" [{extra.get('image_size', '')} {extra.get('image_format', '')}]"
        return text, extra

    def _read_archive(self, file_path: str) -> Tuple[str, Dict]:
        members = []
        member_texts = []
        try:
            if zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, 'r') as zf:
                    for name in zf.namelist():
                        members.append(name)
                        if not name.endswith('/'):
                            try:
                                data = zf.read(name)
                                text = data.decode('utf-8', errors='replace')
                                if len(text) < 50000:
                                    member_texts.append(f"[Member: {name}]\n{text}")
                            except Exception:
                                member_texts.append(f"[Member: {name}] (binary)")
            elif tarfile.is_tarfile(file_path):
                with tarfile.open(file_path, 'r:*') as tf:
                    for member in tf.getmembers():
                        members.append(member.name)
                        if member.isfile():
                            try:
                                f = tf.extractfile(member)
                                if f:
                                    data = f.read()
                                    text = data.decode('utf-8', errors='replace')
                                    if len(text) < 50000:
                                        member_texts.append(
                                            f"[Member: {member.name}]\n{text}"
                                        )
                            except Exception:
                                member_texts.append(
                                    f"[Member: {member.name}] (binary)"
                                )
        except Exception as e:
            return f"[Archive read error: {e}]", {}

        content = f"[Archive: {Path(file_path).name}]\n"
        content += f"Members ({len(members)}):\n" + "\n".join(members[:50])
        if member_texts:
            content += "\n\n" + "\n\n".join(member_texts[:10])
        return content, {"member_count": len(members), "members": members[:100]}


# ─────────────────────────────────────────────────────────────────────────────
# Chunking
# ─────────────────────────────────────────────────────────────────────────────

class TextChunker:
    """Splits document text into overlapping chunks with metadata."""

    def __init__(self, chunk_size: int = 800, overlap: int = 150):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str, doc_id: str,
                   file_type: str = "text",
                   extra_meta: Optional[Dict] = None) -> List[Chunk]:
        if not text or not text.strip():
            return []

        if file_type == '.pdf' or (extra_meta and 'page_count' in extra_meta):
            return self._chunk_by_pages(text, doc_id)
        elif file_type in ('.md', '.markdown', '.rst'):
            return self._chunk_markdown(text, doc_id)
        elif file_type in ('.log', '.txt') and '\n' in text:
            return self._chunk_by_lines(text, doc_id)
        else:
            return self._chunk_sliding_window(text, doc_id)

    def _chunk_sliding_window(self, text: str, doc_id: str) -> List[Chunk]:
        chunks = []
        words = text.split()
        if not words:
            return []

        chunk_words = self.chunk_size // 5
        overlap_words = self.overlap // 5

        i = 0
        chunk_index = 0
        offset = 0

        while i < len(words):
            end = min(i + chunk_words, len(words))
            chunk_text = " ".join(words[i:end])
            start_offset = text.find(words[i], offset) if i < len(words) else offset
            end_offset = start_offset + len(chunk_text)

            line_start = text[:start_offset].count('\n') + 1
            line_end = text[:end_offset].count('\n') + 1

            chunk = Chunk(
                chunk_id=str(uuid.uuid4()),
                doc_id=doc_id,
                content=chunk_text,
                chunk_index=chunk_index,
                start_offset=start_offset,
                end_offset=end_offset,
                chunk_type="text",
                line_start=line_start,
                line_end=line_end
            )
            chunks.append(chunk)
            chunk_index += 1
            offset = start_offset

            if end >= len(words):
                break
            i = end - overlap_words
            if i <= 0:
                i = end

        return chunks

    def _chunk_by_pages(self, text: str, doc_id: str) -> List[Chunk]:
        chunks = []
        page_pattern = re.compile(r'\[Page (\d+)\]')
        pages = page_pattern.split(text)

        chunk_index = 0
        offset = 0

        if len(pages) <= 1:
            return self._chunk_sliding_window(text, doc_id)

        i = 1
        while i < len(pages) - 1:
            page_num = int(pages[i])
            page_text = pages[i + 1].strip()
            if page_text:
                start_offset = text.find(page_text, offset)
                if start_offset == -1:
                    start_offset = offset
                end_offset = start_offset + len(page_text)

                if len(page_text) > self.chunk_size * 2:
                    sub_chunks = self._chunk_sliding_window(page_text, doc_id)
                    for sc in sub_chunks:
                        sc.chunk_index = chunk_index
                        sc.page_number = page_num
                        sc.start_offset += start_offset
                        sc.end_offset += start_offset
                        chunks.append(sc)
                        chunk_index += 1
                else:
                    chunk = Chunk(
                        chunk_id=str(uuid.uuid4()),
                        doc_id=doc_id,
                        content=page_text,
                        chunk_index=chunk_index,
                        start_offset=start_offset,
                        end_offset=end_offset,
                        chunk_type="page",
                        page_number=page_num
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                offset = end_offset
            i += 2

        return chunks

    def _chunk_markdown(self, text: str, doc_id: str) -> List[Chunk]:
        chunks = []
        section_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        sections = []
        last_end = 0

        for match in section_pattern.finditer(text):
            if last_end < match.start():
                sections.append((None, text[last_end:match.start()], last_end))
            last_end = match.start()

        sections.append((None, text[last_end:], last_end))

        chunk_index = 0
        current_section = None

        for section_title, content, start_pos in sections:
            lines = content.split('\n')
            current_title = current_section

            for line in lines:
                m = section_pattern.match(line)
                if m:
                    current_title = m.group(2).strip()

            if content.strip():
                sub_chunks = self._chunk_sliding_window(content, doc_id)
                for sc in sub_chunks:
                    sc.chunk_index = chunk_index
                    sc.section_title = current_title
                    sc.start_offset += start_pos
                    sc.end_offset += start_pos
                    sc.chunk_type = "section"
                    chunks.append(sc)
                    chunk_index += 1

            current_section = current_title

        if not chunks:
            return self._chunk_sliding_window(text, doc_id)
        return chunks

    def _chunk_by_lines(self, text: str, doc_id: str,
                        lines_per_chunk: int = 50) -> List[Chunk]:
        chunks = []
        lines = text.split('\n')
        chunk_index = 0
        overlap_lines = 5

        i = 0
        while i < len(lines):
            end = min(i + lines_per_chunk, len(lines))
            chunk_lines = lines[i:end]
            chunk_text = "\n".join(chunk_lines)

            if chunk_text.strip():
                start_offset = sum(len(l) + 1 for l in lines[:i])
                end_offset = start_offset + len(chunk_text)

                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=chunk_text,
                    chunk_index=chunk_index,
                    start_offset=start_offset,
                    end_offset=end_offset,
                    chunk_type="lines",
                    line_start=i + 1,
                    line_end=end
                )
                chunks.append(chunk)
                chunk_index += 1

            if end >= len(lines):
                break
            i = end - overlap_lines
            if i <= 0:
                i = end

        return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Embedding Provider
# ─────────────────────────────────────────────────────────────────────────────

class EmbeddingProvider:
    """Provides text embeddings via various backends."""

    def __init__(self, provider: str = "none", model: str = "",
                 api_key: Optional[str] = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client:
            return self._client
        if self.provider == "openai" and HAS_OPENAI:
            import openai as oa
            self._client = oa.OpenAI(api_key=self.api_key or os.environ.get("OPENAI_API_KEY"))
        return self._client

    def embed(self, texts: List[str]) -> List[List[float]]:
        if self.provider == "none" or not texts:
            return [[] for _ in texts]

        if self.provider == "openai":
            return self._embed_openai(texts)
        elif self.provider == "simple":
            return [self._simple_embed(t) for t in texts]
        else:
            return [[] for _ in texts]

    def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        client = self._get_client()
        if not client:
            return [[] for _ in texts]
        try:
            model = self.model or "text-embedding-3-small"
            response = client.embeddings.create(input=texts, model=model)
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.warning(f"OpenAI embedding error: {e}")
            return [[] for _ in texts]

    def _simple_embed(self, text: str, dim: int = 128) -> List[float]:
        """Deterministic hash-based embedding for testing."""
        if not HAS_NUMPY:
            return []
        words = text.lower().split()
        vec = np.zeros(dim, dtype=np.float32)
        for word in words:
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = h % dim
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not HAS_NUMPY or not a or not b:
            return 0.0
        va = np.array(a, dtype=np.float32)
        vb = np.array(b, dtype=np.float32)
        na = np.linalg.norm(va)
        nb = np.linalg.norm(vb)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(va, vb) / (na * nb))


# ─────────────────────────────────────────────────────────────────────────────
# Relation Miner
# ─────────────────────────────────────────────────────────────────────────────

class RelationMiner:
    """Discovers relations between documents based on shared terms and links."""

    def __init__(self, db: Database):
        self.db = db

    def mine_relations(self, doc_id: str, top_k: int = 5):
        """Find documents related to the given doc via shared vocabulary."""
        source_chunks = self.db.get_chunks_for_doc(doc_id)
        if not source_chunks:
            return

        source_terms = self._extract_terms(
            " ".join(c.content for c in source_chunks)
        )

        all_docs = self.db.list_documents(limit=500)
        scores = []

        for doc in all_docs:
            if doc.doc_id == doc_id:
                continue
            target_chunks = self.db.get_chunks_for_doc(doc.doc_id)
            if not target_chunks:
                continue
            target_terms = self._extract_terms(
                " ".join(c.content for c in target_chunks)
            )
            score = self._jaccard_similarity(source_terms, target_terms)
            if score > 0.05:
                scores.append((doc.doc_id, score))

        scores.sort(key=lambda x: -x[1])
        for target_id, score in scores[:top_k]:
            self.db.upsert_relation(
                doc_id, target_id, "similar_content", confidence=score
            )

    def mine_link_relations(self, doc_id: str, all_doc_paths: List[str]):
        """Find wiki-style [[links]] or file references in document text."""
        chunks = self.db.get_chunks_for_doc(doc_id)
        if not chunks:
            return

        full_text = " ".join(c.content for c in chunks)
        link_pattern = re.compile(r'\[\[([^\]]+)\]\]')
        links = link_pattern.findall(full_text)

        path_map = {Path(p).stem.lower(): p for p in all_doc_paths}

        for link in links:
            link_lower = link.lower()
            if link_lower in path_map:
                target_doc = self.db.get_document_by_path(path_map[link_lower])
                if target_doc:
                    self.db.upsert_relation(
                        doc_id, target_doc.doc_id, "wiki_link", confidence=1.0
                    )

    def _extract_terms(self, text: str) -> set:
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        stopwords = {
            'this', 'that', 'with', 'from', 'have', 'been', 'were',
            'they', 'their', 'there', 'what', 'when', 'where', 'which',
            'will', 'would', 'could', 'should', 'about', 'into', 'than',
            'then', 'also', 'some', 'more', 'very', 'just', 'like',
            'your', 'each', 'such', 'only', 'over', 'after', 'before'
        }
        return set(w for w in words if w not in stopwords)

    def _jaccard_similarity(self, a: set, b: set) -> float:
        if not a or not b:
            return 0.0
        intersection = len(a & b)
        union = len(a | b)
        return intersection / union if union > 0 else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Search Engine
# ─────────────────────────────────────────────────────────────────────────────

class SearchEngine:
    """Multi-modal search: lexical FTS, optional embeddings, reranking."""

    def __init__(self, db: Database,
                 embedding_provider: Optional[EmbeddingProvider] = None):
        self.db = db
        self.embedding_provider = embedding_provider or EmbeddingProvider()

    def search(self, query: str,
               mode: str = "lexical",
               limit: int = 10,
               source_quota: Optional[Dict[str, int]] = None,
               file_type_filter: Optional[List[str]] = None,
               folder_filter: Optional[str] = None,
               tags_filter: Optional[List[str]] = None,
               rerank: bool = False) -> List[SearchResult]:

        if mode == "lexical":
            results = self._lexical_search(query, limit * 3)
        elif mode == "semantic":
            results = self._semantic_search(query, limit * 3)
        elif mode == "hybrid":
            lex = self._lexical_search(query, limit * 2)
            sem = self._semantic_search(query, limit * 2)
            results = self._merge_results(lex, sem)
        else:
            results = self._lexical_search(query, limit * 3)

        results = self._apply_filters(
            results, file_type_filter, folder_filter, tags_filter
        )

        if rerank:
            results = self._rerank(query, results)

        if source_quota:
            results = self._apply_source_quota(results, source_quota)

        return results[:limit]

    def _lexical_search(self, query: str, limit: int) -> List[SearchResult]:
        raw = self.db.fts_search(query, limit)
        results = []
        for r in raw:
            doc = self.db.get_document(r['doc_id'])
            if not doc:
                continue
            score = abs(r.get('score', 0))
            results.append(SearchResult(
                doc_id=r['doc_id'],
                chunk_id=r['chunk_id'],
                file_path=doc.file_path,
                title=doc.title,
                content=r['content'],
                score=score,
                chunk_index=r.get('chunk_index', 0),
                page_number=r.get('page_number'),
                line_start=r.get('line_start'),
                line_end=r.get('line_end'),
                section_title=r.get('section_title'),
                match_type="lexical"
            ))
        return results

    def _semantic_search(self, query: str, limit: int) -> List[SearchResult]:
        if not self.embedding_provider or self.embedding_provider.provider == "none":
            return self._lexical_search(query, limit)

        query_emb = self.embedding_provider.embed([query])
        if not query_emb or not query_emb[0]:
            return self._lexical_search(query, limit)

        q_vec = query_emb[0]
        all_embeddings = self.db.get_all_embeddings()

        scored = []
        for chunk_id, emb in all_embeddings:
            sim = self.embedding_provider.cosine_similarity(q_vec, emb)
            scored.append((chunk_id, sim))

        scored.sort(key=lambda x: -x[1])
        results = []
        for chunk_id, sim in scored[:limit]:
            chunk = self.db.get_chunk(chunk_id)
            if not chunk:
                continue
            doc = self.db.get_document(chunk.doc_id)
            if not doc:
                continue
            results.append(SearchResult(
                doc_id=chunk.doc_id,
                chunk_id=chunk_id,
                file_path=doc.file_path,
                title=doc.title,
                content=chunk.content,
                score=sim,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                line_start=chunk.line_start,
                line_end=chunk.line_end,
                section_title=chunk.section_title,
                match_type="semantic"
            ))
        return results

    def _merge_results(self, lex: List[SearchResult],
                       sem: List[SearchResult]) -> List[SearchResult]:
        seen = {}
        for r in lex:
            seen[r.chunk_id] = r
        for r in sem:
            if r.chunk_id in seen:
                existing = seen[r.chunk_id]
                existing.score = (existing.score + r.score) / 2
                existing.match_type = "hybrid"
            else:
                r.match_type = "hybrid"
                seen[r.chunk_id] = r
        merged = list(seen.values())
        merged.sort(key=lambda x: -x.score)
        return merged

    def _apply_filters(self, results: List[SearchResult],
                       file_type_filter: Optional[List[str]],
                       folder_filter: Optional[str],
                       tags_filter: Optional[List[str]]) -> List[SearchResult]:
        if not any([file_type_filter, folder_filter, tags_filter]):
            return results

        filtered = []
        for r in results:
            doc = self.db.get_document(r.doc_id)
            if not doc:
                continue
            if file_type_filter and doc.file_type not in file_type_filter:
                continue
            if folder_filter and not doc.folder_path.startswith(folder_filter):
                continue
            if tags_filter and not any(t in doc.tags for t in tags_filter):
                continue
            filtered.append(r)
        return filtered

    def _rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Simple BM25-inspired reranking."""
        query_terms = set(query.lower().split())
        for r in results:
            content_lower = r.content.lower()
            term_score = sum(
                content_lower.count(t) * (1 + math.log(1 + content_lower.count(t)))
                for t in query_terms
            )
            r.score = r.score * 0.5 + term_score * 0.5
        results.sort(key=lambda x: -x.score)
        return results

    def _apply_source_quota(self, results: List[SearchResult],
                            quota: Dict[str, int]) -> List[SearchResult]:
        """Limit results per source document."""
        counts = defaultdict(int)
        filtered = []
        default_quota = quota.get('default', 3)
        for r in results:
            doc_quota = quota.get(r.doc_id, default_quota)
            if counts[r.doc_id] < doc_quota:
                filtered.append(r)
                counts[r.doc_id] += 1
        return filtered


# ─────────────────────────────────────────────────────────────────────────────
# LLM Provider
# ─────────────────────────────────────────────────────────────────────────────

class LLMProvider:
    """Abstraction over LLM backends (Anthropic, OpenAI, mock)."""

    def __init__(self, provider: str = "mock",
                 model: str = "",
                 api_key: Optional[str] = None,
                 max_tokens: int = 4096):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.max_tokens = max_tokens
        self._client = None

    def _get_client(self):
        if self._client:
            return self._client
        if self.provider == "anthropic" and HAS_ANTHROPIC:
            self._client = anthropic.Anthropic(
                api_key=self.api_key or os.environ.get("ANTHROPIC_API_KEY")
            )
        elif self.provider == "openai" and HAS_OPENAI:
            import openai as oa
            self._client = oa.OpenAI(
                api_key=self.api_key or os.environ.get("OPENAI_API_KEY")
            )
        return self._client

    def complete(self, system_prompt: str, user_message: str) -> str:
        if self.provider == "anthropic":
            return self._complete_anthropic(system_prompt, user_message)
        elif self.provider == "openai":
            return self._complete_openai(system_prompt, user_message)
        else:
            return self._mock_complete(system_prompt, user_message)

    def _complete_anthropic(self, system_prompt: str, user_message: str) -> str:
        client = self._get_client()
        if not client:
            return self._mock_complete(system_prompt, user_message)
        try:
            model = self.model or "claude-3-5-sonnet-20241022"
            response = client.messages.create(
                model=model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return f"[LLM Error: {e}]"

    def _complete_openai(self, system_prompt: str, user_message: str) -> str:
        client = self._get_client()
        if not client:
            return self._mock_complete(system_prompt, user_message)
        try:
            model = self.model or "gpt-4o"
            response = client.chat.completions.create(
                model=model,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"[LLM Error: {e}]"

    def _mock_complete(self, system_prompt: str, user_message: str) -> str:
        return (
            f"[Mock LLM Response]\n"
            f"Query: {user_message[:200]}\n"
            f"This is a mock response. Configure a real LLM provider for actual answers.\n"
            f"System context length: {len(system_prompt)} chars"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Context Window Builder
# ─────────────────────────────────────────────────────────────────────────────

class ContextWindowBuilder:
    """Reads original file sections to build grounded context for the LLM."""

    def __init__(self, ingester: FileIngester, max_context_chars: int = 32000):
        self.ingester = ingester
        self.max_context_chars = max_context_chars

    def build_context(self, search_results: List[SearchResult],
                      query: str) -> Tuple[str, List[Citation]]:
        """Build a context string from search results with citations."""
        context_parts = []
        citations = []
        total_chars = 0
        seen_chunks = set()

        for result in search_results:
            if result.chunk_id in seen_chunks:
                continue
            seen_chunks.add(result.chunk_id)

            window = self._get_window(result)
            if not window:
                window = result.content

            entry = self._format_context_entry(result, window)
            if total_chars + len(entry) > self.max_context_chars:
                break

            context_parts.append(entry)
            total_chars += len(entry)

            citation = Citation(
                doc_id=result.doc_id,
                file_path=result.file_path,
                title=result.title,
                chunk_id=result.chunk_id,
                content_excerpt=result.content[:200],
                page_number=result.page_number,
                line_start=result.line_start,
                line_end=result.line_end,
                section_title=result.section_title
            )
            citations.append(citation)

        context = "\n\n---\n\n".join(context_parts)
        return context, citations

    def _get_window(self, result: SearchResult) -> Optional[str]:
        """Try to read a larger window from the original file."""
        try:
            if not os.path.exists(result.file_path):
                return None

            file_type = Path(result.file_path).suffix.lower()

            if file_type == '.pdf' and result.page_number:
                return self._get_pdf_page(result.file_path, result.page_number)
            elif result.line_start and result.line_end:
                return self._get_line_window(
                    result.file_path, result.line_start, result.line_end
                )
            else:
                return None
        except Exception as e:
            logger.debug(f"Window read error for {result.file_path}: {e}")
            return None

    def _get_pdf_page(self, file_path: str, page_number: int) -> Optional[str]:
        if not HAS_PYPDF:
            return None
        try:
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                if page_number <= len(reader.pages):
                    return reader.pages[page_number - 1].extract_text()
        except Exception:
            pass
        return None

    def _get_line_window(self, file_path: str,
                         line_start: int, line_end: int,
                         context_lines: int = 5) -> Optional[str]:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            start = max(0, line_start - context_lines - 1)
            end = min(len(lines), line_end + context_lines)
            return "".join(lines[start:end])
        except Exception:
            return None

    def _format_context_entry(self, result: SearchResult, content: str) -> str:
        header_parts = [f"SOURCE: {result.title}"]
        header_parts.append(f"FILE: {result.file_path}")
        if result.page_number:
            header_parts.append(f"PAGE: {result.page_number}")
        if result.line_start:
            header_parts.append(f"LINES: {result.line_start}-{result.line_end}")
        if result.section_title:
            header_parts.append(f"SECTION: {result.section_title}")
        header = " | ".join(header_parts)
        return f"{header}\n\n{content}"


# ─────────────────────────────────────────────────────────────────────────────
# Research Agent
# ─────────────────────────────────────────────────────────────────────────────

class ResearchAgent:
    """The main LLM agent that answers queries with citations."""

    SYSTEM_PROMPT = """You are Marginalia, a research assistant with access to a personal knowledge base.

Your task is to answer the user's query based ONLY on the provided source documents.
Always cite your sources using the format [Title | File | Page/Line/Section].
If the sources don't contain enough information, say so clearly.
Be precise, thorough, and scholarly in your responses.
After your answer, suggest 2-3 follow-up questions the user might want to explore."""

    def __init__(self, db: Database,
                 search_engine: SearchEngine,
                 context_builder: ContextWindowBuilder,
                 llm_provider: LLMProvider):
        self.db = db
        self.search_engine = search_engine
        self.context_builder = context_builder
        self.llm = llm_provider

    def answer(self, query: str,
               search_mode: str = "lexical",
               search_limit: int = 10,
               source_quota: Optional[Dict[str, int]] = None,
               file_type_filter: Optional[List[str]] = None,
               folder_filter: Optional[str] = None,
               tags_filter: Optional[List[str]] = None,
               rerank: bool = False,
               journal_id: Optional[str] = None,
               note_tags: Optional[List[str]] = None,
               include_prior_notes: bool = True) -> InvestigationNote:

        prior_context = ""
        if include_prior_notes:
            prior_notes = self.db.search_notes(query, limit=3)
            if prior_notes:
                prior_parts = []
                for note in prior_notes:
                    prior_parts.append(
                        f"PRIOR INVESTIGATION ({note.created_at[:10]}):\n"
                        f"Q: {note.query}\n"
                        f"A: {note.answer[:500]}..."
                    )
                prior_context = "\n\n".join(prior_parts)

        results = self.search_engine.search(
            query=query,
            mode=search_mode,
            limit=search_limit,
            source_quota=source_quota,
            file_type_filter=file_type_filter,
            folder_filter=folder_filter,
            tags_filter=tags_filter,
            rerank=rerank
        )

        context, citations = self.context_builder.build_context(results, query)

        user_message = self._build_user_message(
            query, context, prior_context
        )

        answer_text = self.llm.complete(self.SYSTEM_PROMPT, user_message)

        follow_ups = self._extract_follow_ups(answer_text)

        note = InvestigationNote(
            note_id=str(uuid.uuid4()),
            query=query,
            answer=answer_text,
            citations=citations,
            created_at=datetime.datetime.utcnow().isoformat(),
            tags=note_tags or [],
            follow_up_questions=follow_ups,
            related_note_ids=[],
            journal_id=journal_id
        )

        self.db.upsert_note(note)

        if journal_id:
            journal = self.db.get_journal(journal_id)
            if journal:
                journal.note_ids.append(note.note_id)
                self.db.upsert_journal(journal)

        return note

    def _build_user_message(self, query: str, context: str,
                             prior_context: str) -> str:
        parts = []
        if prior_context:
            parts.append(f"RELEVANT PRIOR INVESTIGATIONS:\n{prior_context}\n")
        if context:
            parts.append(f"SOURCE DOCUMENTS:\n{context}\n")
        else:
            parts.append("No relevant source documents found in the knowledge base.\n")
        parts.append(f"QUERY: {query}")
        return "\n\n".join(parts)

    def _extract_follow_ups(self, answer: str) -> List[str]:
        """Extract follow-up questions from the answer."""
        follow_ups = []
        lines = answer.split('\n')
        in_followup = False
        for line in lines:
            line = line.strip()
            if any(kw in line.lower() for kw in
                   ['follow-up', 'follow up', 'further questions',
                    'you might want to explore', 'related questions']):
                in_followup = True
                continue
            if in_followup and line:
                cleaned = re.sub(r'^[\d\.\-\*\•]+\s*', '', line)
                if cleaned and '?' in cleaned:
                    follow_ups.append(cleaned)
                if len(follow_ups) >= 3:
                    break
        return follow_ups

    def generate_report(self, topic: str,
                        queries: List[str],
                        journal_id: Optional[str] = None) -> str:
        """Generate a multi-section research report."""
        sections = []
        all_citations = []

        for q in queries:
            note = self.answer(
                query=q,
                journal_id=journal_id,
                include_prior_notes=False
            )
            sections.append(f"## {q}\n\n{note.answer}")
            all_citations.extend(note.citations)

        unique_citations = {c.chunk_id: c for c in all_citations}

        report_parts = [f"# Research Report: {topic}\n"]
        report_parts.append(f"*Generated: {datetime.datetime.utcnow().isoformat()}*\n")
        report_parts.extend(sections)

        if unique_citations:
            report_parts.append("\n## References\n")
            for i, (_, cit) in enumerate(unique_citations.items(), 1):
                report_parts.append(f"{i}. {cit.format()}")

        return "\n\n".join(report_parts)


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class IngestionPipeline:
    """Orchestrates file discovery, ingestion, chunking, and indexing."""

    def __init__(self, db: Database,
                 ingester: FileIngester,
                 chunker: TextChunker,
                 embedding_provider: Optional[EmbeddingProvider] = None,
                 relation_miner: Optional[RelationMiner] = None):
        self.db = db
        self.ingester = ingester
        self.chunker = chunker
        self.embedding_provider = embedding_provider or EmbeddingProvider()
        self.relation_miner = relation_miner

    def ingest_file(self, file_path: str,
                    catalog_id: Optional[str] = None,
                    tags: Optional[List[str]] = None,
                    force_reingest: bool = False) -> Optional[DocumentMetadata]:
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"File not found: {file_path}")
            return None

        if not self.ingester.can_ingest(file_path):
            logger.info(f"Unsupported file type: {file_path}")
            return None

        checksum = self._compute_checksum(file_path)
        existing = self.db.get_document_by_path(str(path.resolve()))

        if existing and existing.checksum == checksum and not force_reingest:
            logger.debug(f"File unchanged, skipping: {file_path}")
            return existing

        text, extra_meta = self.ingester.ingest_file(file_path)

        stat = path.stat()
        doc_id = existing.doc_id if existing else str(uuid.uuid4())

        meta = DocumentMetadata(
            doc_id=doc_id,
            file_path=str(path.resolve()),
            title=path.stem,
            file_type=path.suffix.lower(),
            file_size=stat.st_size,
            created_at=datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified_at=datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            ingested_at=datetime.datetime.utcnow().isoformat(),
            checksum=checksum,
            tags=tags or [],
            catalog_id=catalog_id,
            folder_path=str(path.parent.resolve()),
            word_count=len(text.split()),
            page_count=extra_meta.get('page_count', 0),
            custom_metadata=extra_meta
        )

        self.db.upsert_document(meta)

        if existing:
            self.db.delete_chunks_for_doc(doc_id)

        chunks = self.chunker.chunk_text(
            text, doc_id, path.suffix.lower(), extra_meta
        )
        if chunks:
            self.db.insert_chunks_batch(chunks)

            if self.embedding_provider.provider != "none":
                self._embed_chunks(chunks)

        if catalog_id:
            catalog = self.db.get_catalog(catalog_id)
            if catalog and doc_id not in catalog.doc_ids:
                catalog.doc_ids.append(doc_id)
                self.db.upsert_catalog(catalog)

        logger.info(f"Ingested: {file_path} ({len(chunks)} chunks)")
        return meta

    def ingest_directory(self, directory: str,
                         recursive: bool = True,
                         catalog_id: Optional[str] = None,
                         tags: Optional[List[str]] = None,
                         exclude_patterns: Optional[List[str]] = None) -> List[DocumentMetadata]:
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.warning(f"Directory not found: {directory}")
            return []

        exclude_patterns = exclude_patterns or [
            '.git', '__pycache__', 'node_modules', '.DS_Store',
            '*.pyc', '*.pyo', '.env', 'venv'
        ]

        pattern = "**/*" if recursive else "*"
        all_files = list(dir_path.glob(pattern))

        ingested = []
        for file_path in all_files:
            if not file_path.is_file():
                continue
            if self._should_exclude(file_path, exclude_patterns):
                continue
            meta = self.ingest_file(
                str(file_path), catalog_id=catalog_id, tags=tags
            )
            if meta:
                ingested.append(meta)

        if self.relation_miner and ingested:
            all_paths = [m.file_path for m in ingested]
            for meta in ingested:
                try:
                    self.relation_miner.mine_relations(meta.doc_id)
                    self.relation_miner.mine_link_relations(meta.doc_id, all_paths)
                except Exception as e:
                    logger.debug(f"Relation mining error for {meta.doc_id}: {e}")

        logger.info(f"Ingested {len(ingested)} files from {directory}")
        return ingested

    def _embed_chunks(self, chunks: List[Chunk]):
        batch_size = 20
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c.content for c in batch]
            try:
                embeddings = self.embedding_provider.embed(texts)
                for chunk, emb in zip(batch, embeddings):
                    if emb:
                        self.db.store_embedding(chunk.chunk_id, emb)
            except Exception as e:
                logger.warning(f"Embedding error: {e}")

    def _compute_checksum(self, file_path: str) -> str:
        h = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for block in iter(lambda: f.read(65536), b''):
                    h.update(block)
        except Exception:
            pass
        return h.hexdigest()

    def _should_exclude(self, path: Path, patterns: List[str]) -> bool:
        path_str = str(path)
        for pattern in patterns:
            if pattern.startswith('*'):
                if path.name.endswith(pattern[1:]):
                    return True
            elif pattern in path_str:
                return True
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Catalog Manager
# ─────────────────────────────────────────────────────────────────────────────

class CatalogManager:
    """Manages catalogs, views, tags, and organizational metadata."""

    def __init__(self, db: Database):
        self.db = db

    def create_catalog(self, name: str, description: str = "",
                       tags: Optional[List[str]] = None) -> Catalog:
        catalog = Catalog(
            catalog_id=str(uuid.uuid4()),
            name=name,
            description=description,
            created_at=datetime.datetime.utcnow().isoformat(),
            tags=tags or []
        )
        self.db.upsert_catalog(catalog)
        return catalog

    def get_catalog(self, catalog_id: str) -> Optional[Catalog]:
        return self.db.get_catalog(catalog_id)

    def list_catalogs(self) -> List[Catalog]:
        return self.db.list_catalogs()

    def add_to_catalog(self, catalog_id: str, doc_id: str):
        catalog = self.db.get_catalog(catalog_id)
        if catalog and doc_id not in catalog.doc_ids:
            catalog.doc_ids.append(doc_id)
            self.db.upsert_catalog(catalog)
            doc = self.db.get_document(doc_id)
            if doc:
                doc.catalog_id = catalog_id
                self.db.upsert_document(doc)

    def remove_from_catalog(self, catalog_id: str, doc_id: str):
        catalog = self.db.get_catalog(catalog_id)
        if catalog and doc_id in catalog.doc_ids:
            catalog.doc_ids.remove(doc_id)
            self.db.upsert_catalog(catalog)

    def create_view(self, name: str, description: str = "",
                    query_filter: Optional[Dict] = None,
                    tags_filter: Optional[List[str]] = None,
                    file_types_filter: Optional[List[str]] = None,
                    sort_by: str = "ingested_at",
                    sort_order: str = "desc") -> View:
        view = View(
            view_id=str(uuid.uuid4()),
            name=name,
            description=description,
            query_filter=query_filter or {},
            created_at=datetime.datetime.utcnow().isoformat(),
            sort_by=sort_by,
            sort_order=sort_order,
            tags_filter=tags_filter or [],
            file_types_filter=file_types_filter or []
        )
        self.db.upsert_view(view)
        return view

    def get_view(self, view_id: str) -> Optional[View]:
        return self.db.get_view(view_id)

    def list_views(self) -> List[View]:
        return self.db.list_views()

    def apply_view(self, view_id: str) -> List[DocumentMetadata]:
        view = self.db.get_view(view_id)
        if not view:
            return []
        docs = self.db.list_documents(
            tags=view.tags_filter if view.tags_filter else None,
            limit=500
        )
        if view.file_types_filter:
            docs = [d for d in docs if d.file_type in view.file_types_filter]
        reverse = view.sort_order == "desc"
        sort_key = view.sort_by
        try:
            docs.sort(key=lambda d: getattr(d, sort_key, ""), reverse=reverse)
        except Exception:
            pass
        return docs

    def tag_document(self, doc_id: str, tags: List[str]):
        doc = self.db.get_document(doc_id)
        if doc:
            for tag in tags:
                if tag not in doc.tags:
                    doc.tags.append(tag)
                self.db.upsert_tag(tag)
            self.db.upsert_document(doc)

    def untag_document(self, doc_id: str, tags: List[str]):
        doc = self.db.get_document(doc_id)
        if doc:
            doc.tags = [t for t in doc.tags if t not in tags]
            self.db.upsert_document(doc)

    def list_tags(self) -> List[Dict]:
        return self.db.list_tags()

    def get_tag_cloud(self) -> Dict[str, int]:
        docs = self.db.list_documents(limit=10000)
        counts = Counter()
        for doc in docs:
            for tag in doc.tags:
                counts[tag] += 1
        return dict(counts)


# ─────────────────────────────────────────────────────────────────────────────
# Journal Manager
# ─────────────────────────────────────────────────────────────────────────────

class JournalManager:
    """Manages investigation journals and notes."""

    def __init__(self, db: Database):
        self.db = db

    def create_journal(self, name: str, description: str = "",
                       tags: Optional[List[str]] = None) -> Journal:
        journal = Journal(
            journal_id=str(uuid.uuid4()),
            name=name,
            description=description,
            created_at=datetime.datetime.utcnow().isoformat(),
            tags=tags or []
        )
        self.db.upsert_journal(journal)
        return journal

    def get_journal(self, journal_id: str) -> Optional[Journal]:
        return self.db.get_journal(journal_id)

    def list_journals(self) -> List[Journal]:
        return self.db.list_journals()

    def get_notes_for_journal(self, journal_id: str) -> List[InvestigationNote]:
        return self.db.list_notes(journal_id=journal_id)

    def get_note(self, note_id: str) -> Optional[InvestigationNote]:
        return self.db.get_note(note_id)

    def list_notes(self, tags: Optional[List[str]] = None,
                   limit: int = 50) -> List[InvestigationNote]:
        return self.db.list_notes(tags=tags, limit=limit)

    def search_notes(self, query: str, limit: int = 10) -> List[InvestigationNote]:
        return self.db.search_notes(query, limit)

    def link_notes(self, note_id_a: str, note_id_b: str):
        note_a = self.db.get_note(note_id_a)
        note_b = self.db.get_note(note_id_b)
        if note_a and note_b:
            if note_id_b not in note_a.related_note_ids:
                note_a.related_note_ids.append(note_id_b)
                self.db.upsert_note(note_a)
            if note_id_a not in note_b.related_note_ids:
                note_b.related_note_ids.append(note_id_a)
                self.db.upsert_note(note_b)

    def export_journal_markdown(self, journal_id: str) -> str:
        journal = self.db.get_journal(journal_id)
        if not journal:
            return ""
        notes = self.get_notes_for_journal(journal_id)
        parts = [f"# Journal: {journal.name}\n\n{journal.description}\n"]
        for note in notes:
            parts.append(f"## {note.created_at[:10]} — {note.query}\n")
            parts.append(note.answer)
            if note.citations:
                parts.append("\n### Sources\n")
                for i, cit in enumerate(note.citations, 1):
                    parts.append(f"{i}. {cit.format()}")
            if note.follow_up_questions:
                parts.append("\n### Follow-up Questions\n")
                for q in note.follow_up_questions:
                    parts.append(f"- {q}")
            parts.append("\n---\n")
        return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Marginalia: Main Application
# ─────────────────────────────────────────────────────────────────────────────

class Marginalia:
    """
    Main entry point for the Marginalia knowledge management system.
    Wires together all components.
    """

    def __init__(self, base_path: str,
                 llm_provider: str = "mock",
                 llm_model: str = "",
                 llm_api_key: Optional[str] = None,
                 embedding_provider: str = "none",
                 embedding_model: str = "",
                 embedding_api_key: Optional[str] = None,
                 chunk_size: int = 800,
                 chunk_overlap: int = 150,
                 max_context_chars: int = 32000):

        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        db_path = str(self.base_path / "marginalia.db")
        self.db = Database(db_path)

        self.ingester = FileIngester(str(self.base_path))
        self.chunker = TextChunker(chunk_size=chunk_size, overlap=chunk_overlap)

        self.embedding_provider = EmbeddingProvider(
            provider=embedding_provider,
            model=embedding_model,
            api_key=embedding_api_key
        )

        self.relation_miner = RelationMiner(self.db)

        self.pipeline = IngestionPipeline(
            db=self.db,
            ingester=self.ingester,
            chunker=self.chunker,
            embedding_provider=self.embedding_provider,
            relation_miner=self.relation_miner
        )

        self.search_engine = SearchEngine(
            db=self.db,
            embedding_provider=self.embedding_provider
        )

        self.context_builder = ContextWindowBuilder(
            ingester=self.ingester,
            max_context_chars=max_context_chars
        )

        self.llm = LLMProvider(
            provider=llm_provider,
            model=llm_model,
            api_key=llm_api_key
        )

        self.agent = ResearchAgent(
            db=self.db,
            search_engine=self.search_engine,
            context_builder=self.context_builder,
            llm_provider=self.llm
        )

        self.catalog_manager = CatalogManager(self.db)
        self.journal_manager = JournalManager(self.db)

        logger.info(f"Marginalia initialized at {base_path}")

    # ── Ingestion ──────────────────────────────────────────────────────────

    def ingest(self, path: str,
               catalog_id: Optional[str] = None,
               tags: Optional[List[str]] = None,
               recursive: bool = True,
               force: bool = False) -> Union[Optional[DocumentMetadata], List[DocumentMetadata]]:
        p = Path(path)
        if p.is_file():
            return self.pipeline.ingest_file(
                str(p), catalog_id=catalog_id, tags=tags, force_reingest=force
            )
        elif p.is_dir():
            return self.pipeline.ingest_directory(
                str(p), recursive=recursive, catalog_id=catalog_id, tags=tags
            )
        else:
            logger.warning(f"Path not found: {path}")
            return None

    def reingest(self, doc_id: str) -> Optional[DocumentMetadata]:
        doc = self.db.get_document(doc_id)
        if not doc:
            return None
        return self.pipeline.ingest_file(
            doc.file_path, catalog_id=doc.catalog_id,
            tags=doc.tags, force_reingest=True
        )

    # ── Search ─────────────────────────────────────────────────────────────

    def search(self, query: str,
               mode: str = "lexical",
               limit: int = 10,
               **kwargs) -> List[SearchResult]:
        return self.search_engine.search(query, mode=mode, limit=limit, **kwargs)

    # ── Agent ──────────────────────────────────────────────────────────────

    def ask(self, query: str,
            search_mode: str = "lexical",
            search_limit: int = 10,
            journal_id: Optional[str] = None,
            tags: Optional[List[str]] = None,
            rerank: bool = False,
            source_quota: Optional[Dict[str, int]] = None,
            file_type_filter: Optional[List[str]] = None,
            folder_filter: Optional[str] = None,
            tags_filter: Optional[List[str]] = None) -> InvestigationNote:
        return self.agent.answer(
            query=query,
            search_mode=search_mode,
            search_limit=search_limit,
            source_quota=source_quota,
            file_type_filter=file_type_filter,
            folder_filter=folder_filter,
            tags_filter=tags_filter,
            rerank=rerank,
            journal_id=journal_id,
            note_tags=tags
        )

    def report(self, topic: str, questions: List[str],
               journal_id: Optional[str] = None) -> str:
        return self.agent.generate_report(topic, questions, journal_id)

    # ── Documents ──────────────────────────────────────────────────────────

    def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        return self.db.get_document(doc_id)

    def get_document_by_path(self, path: str) -> Optional[DocumentMetadata]:
        return self.db.get_document_by_path(str(Path(path).resolve()))

    def list_documents(self, folder: Optional[str] = None,
                       file_type: Optional[str] = None,
                       tags: Optional[List[str]] = None,
                       limit: int = 100) -> List[DocumentMetadata]:
        return self.db.list_documents(
            folder_path=folder, file_type=file_type, tags=tags, limit=limit
        )

    def delete_document(self, doc_id: str):
        self.db.delete_chunks_for_doc(doc_id)
        self.db.delete_document(doc_id)

    def update_document_tags(self, doc_id: str, tags: List[str]):
        self.catalog_manager.tag_document(doc_id, tags)

    def get_document_relations(self, doc_id: str) -> List[Dict]:
        return self.db.get_relations(doc_id)

    def mine_relations(self, doc_id: str):
        self.relation_miner.mine_relations(doc_id)

    # ── Catalogs ───────────────────────────────────────────────────────────

    def create_catalog(self, name: str, description: str = "",
                       tags: Optional[List[str]] = None) -> Catalog:
        return self.catalog_manager.create_catalog(name, description, tags)

    def get_catalog(self, catalog_id: str) -> Optional[Catalog]:
        return self.catalog_manager.get_catalog(catalog_id)

    def list_catalogs(self) -> List[Catalog]:
        return self.catalog_manager.list_catalogs()

    def add_to_catalog(self, catalog_id: str, doc_id: str):
        self.catalog_manager.add_to_catalog(catalog_id, doc_id)

    # ── Views ──────────────────────────────────────────────────────────────

    def create_view(self, name: str, description: str = "",
                    tags_filter: Optional[List[str]] = None,
                    file_types_filter: Optional[List[str]] = None,
                    sort_by: str = "ingested_at",
                    sort_order: str = "desc") -> View:
        return self.catalog_manager.create_view(
            name, description,
            tags_filter=tags_filter,
            file_types_filter=file_types_filter,
            sort_by=sort_by,
            sort_order=sort_order
        )

    def apply_view(self, view_id: str) -> List[DocumentMetadata]:
        return self.catalog_manager.apply_view(view_id)

    def list_views(self) -> List[View]:
        return self.catalog_manager.list_views()

    # ── Journals ───────────────────────────────────────────────────────────

    def create_journal(self, name: str, description: str = "",
                       tags: Optional[List[str]] = None) -> Journal:
        return self.journal_manager.create_journal(name, description, tags)

    def get_journal(self, journal_id: str) -> Optional[Journal]:
        return self.journal_manager.get_journal(journal_id)

    def list_journals(self) -> List[Journal]:
        return self.journal_manager.list_journals()

    def get_note(self, note_id: str) -> Optional[InvestigationNote]:
        return self.journal_manager.get_note(note_id)

    def list_notes(self, journal_id: Optional[str] = None,
                   tags: Optional[List[str]] = None,
                   limit: int = 50) -> List[InvestigationNote]:
        if journal_id:
            return self.journal_manager.get_notes_for_journal(journal_id)
        return self.journal_manager.list_notes(tags=tags, limit=limit)

    def search_notes(self, query: str, limit: int = 10) -> List[InvestigationNote]:
        return self.journal_manager.search_notes(query, limit)

    def export_journal(self, journal_id: str) -> str:
        return self.journal_manager.export_journal_markdown(journal_id)

    # ── Tags ───────────────────────────────────────────────────────────────

    def list_tags(self) -> List[Dict]:
        return self.catalog_manager.list_tags()

    def get_tag_cloud(self) -> Dict[str, int]:
        return self.catalog_manager.get_tag_cloud()

    # ── Stats ──────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        docs = self.db.list_documents(limit=100000)
        notes = self.db.list_notes(limit=100000)
        catalogs = self.db.list_catalogs()
        journals = self.db.list_journals()

        type_counts = Counter(d.file_type for d in docs)
        total_words = sum(d.word_count for d in docs)
        total_size = sum(d.file_size for d in docs)

        return {
            "total_documents": len(docs),
            "total_notes": len(notes),
            "total_catalogs": len(catalogs),
            "total_journals": len(journals),
            "total_words": total_words,
            "total_size_bytes": total_size,
            "file_types": dict(type_counts),
            "db_path": self.db.db_path,
            "base_path": str(self.base_path)
        }

    def __repr__(self) -> str:
        s = self.stats()
        return (
            f"Marginalia(base={self.base_path}, "
            f"docs={s['total_documents']}, "
            f"notes={s['total_notes']})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

class CLI:
    """Simple command-line interface for Marginalia."""

    def __init__(self, marginalia: Marginalia):
        self.m = marginalia

    def run(self):
        import sys
        args = sys.argv[1:]
        if not args:
            self._print_help()
            return

        cmd = args[0]
        rest = args[1:]

        commands = {
            'ingest': self._cmd_ingest,
            'search': self._cmd_search,
            'ask': self._cmd_ask,
            'stats': self._cmd_stats,
            'list': self._cmd_list,
            'catalog': self._cmd_catalog,
            'journal': self._cmd_journal,
            'note': self._cmd_note,
            'tags': self._cmd_tags,
            'report': self._cmd_report,
            'help': lambda _: self._print_help(),
        }

        handler = commands.get(cmd)
        if handler:
            handler(rest)
        else:
            print(f"Unknown command: {cmd}")
            self._print_help()

    def _print_help(self):
        print("""
Marginalia - Personal Knowledge Management System

Commands:
  ingest <path> [--tags tag1,tag2] [--catalog id]
  search <query> [--mode lexical|semantic|hybrid] [--limit N]
  ask <query> [--journal id] [--mode lexical] [--rerank]
  stats
  list [--type ext] [--folder path] [--tags tag1,tag2]
  catalog create <name> [--desc text]
  catalog list
  journal create <name> [--desc text]
  journal list
  journal export <id>
  note list [--journal id]
  note show <id>
  tags list
  report <topic> --questions "q1|q2|q3" [--journal id]
  help
""")

    def _cmd_ingest(self, args: List[str]):
        if not args:
            print("Usage: ingest <path> [--tags tag1,tag2] [--catalog id]")
            return
        path = args[0]
        tags = []
        catalog_id = None
        i = 1
        while i < len(args):
            if args[i] == '--tags' and i + 1 < len(args):
                tags = args[i + 1].split(',')
                i += 2
            elif args[i] == '--catalog' and i + 1 < len(args):
                catalog_id = args[i + 1]
                i += 2
            else:
                i += 1
        result = self.m.ingest(path, catalog_id=catalog_id, tags=tags)
        if isinstance(result, list):
            print(f"Ingested {len(result)} files")
        elif result:
            print(f"Ingested: {result.title} ({result.doc_id})")
        else:
            print("Nothing ingested")

    def _cmd_search(self, args: List[str]):
        if not args:
            print("Usage: search <query> [--mode lexical|semantic|hybrid] [--limit N]")
            return
        query = args[0]
        mode = "lexical"
        limit = 5
        i = 1
        while i < len(args):
            if args[i] == '--mode' and i + 1 < len(args):
                mode = args[i + 1]
                i += 2
            elif args[i] == '--limit' and i + 1 < len(args):
                limit = int(args[i + 1])
                i += 2
            else:
                i += 1
        results = self.m.search(query, mode=mode, limit=limit)
        print(f"\nSearch results for '{query}' ({mode}):\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. [{r.title}] score={r.score:.3f}")
            if r.page_number:
                print(f"   Page {r.page_number}")
            if r.section_title:
                print(f"   Section: {r.section_title}")
            print(f"   {r.content[:150]}...")
            print()

    def _cmd_ask(self, args: List[str]):
        if not args:
            print("Usage: ask <query> [--journal id] [--mode lexical] [--rerank]")
            return
        query = args[0]
        journal_id = None
        mode = "lexical"
        rerank = False
        i = 1
        while i < len(args):
            if args[i] == '--journal' and i + 1 < len(args):
                journal_id = args[i + 1]
                i += 2
            elif args[i] == '--mode' and i + 1 < len(args):
                mode = args[i + 1]
                i += 2
            elif args[i] == '--rerank':
                rerank = True
                i += 1
            else:
                i += 1
        note = self.m.ask(query, search_mode=mode, journal_id=journal_id, rerank=rerank)
        print(f"\n{'='*60}")
        print(f"QUERY: {note.query}")
        print(f"{'='*60}\n")
        print(note.answer)
        if note.citations:
            print(f"\n{'─'*40}")
            print("SOURCES:")
            for i, cit in enumerate(note.citations, 1):
                print(f"  {i}. {cit.format()}")
        if note.follow_up_questions:
            print(f"\n{'─'*40}")
            print("FOLLOW-UP QUESTIONS:")
            for q in note.follow_up_questions:
                print(f"  • {q}")
        print(f"\nNote saved: {note.note_id}")

    def _cmd_stats(self, args: List[str]):
        s = self.m.stats()
        print("\nMarginalia Statistics:")
        print(f"  Documents:  {s['total_documents']}")
        print(f"  Notes:      {s['total_notes']}")
        print(f"  Catalogs:   {s['total_catalogs']}")
        print(f"  Journals:   {s['total_journals']}")
        print(f"  Total words: {s['total_words']:,}")
        print(f"  Total size:  {s['total_size_bytes']:,} bytes")
        print(f"  File types: {s['file_types']}")
        print(f"  Base path:  {s['base_path']}")

    def _cmd_list(self, args: List[str]):
        file_type = None
        folder = None
        tags = None
        i = 0
        while i < len(args):
            if args[i] == '--type' and i + 1 < len(args):
                file_type = args[i + 1]
                i += 2
            elif args[i] == '--folder' and i + 1 < len(args):
                folder = args[i + 1]
                i += 2
            elif args[i] == '--tags' and i + 1 < len(args):
                tags = args[i + 1].split(',')
                i += 2
            else:
                i += 1
        docs = self.m.list_documents(folder=folder, file_type=file_type, tags=tags)
        print(f"\nDocuments ({len(docs)}):\n")
        for doc in docs:
            tag_str = f" [{', '.join(doc.tags)}]" if doc.tags else ""
            print(f"  {doc.title}{tag_str}")
            print(f"    {doc.file_path} ({doc.file_type}, {doc.word_count} words)")

    def _cmd_catalog(self, args: List[str]):
        if not args:
            print("Usage: catalog create <name> | catalog list")
            return
        sub = args[0]
        if sub == 'create' and len(args) > 1:
            name = args[1]
            desc = ""
            if '--desc' in args:
                idx = args.index('--desc')
                if idx + 1 < len(args):
                    desc = args[idx + 1]
            cat = self.m.create_catalog(name, desc)
            print(f"Created catalog: {cat.name} ({cat.catalog_id})")
        elif sub == 'list':
            cats = self.m.list_catalogs()
            print(f"\nCatalogs ({len(cats)}):")
            for c in cats:
                print(f"  {c.name} ({c.catalog_id}) - {len(c.doc_ids)} docs")

    def _cmd_journal(self, args: List[str]):
        if not args:
            print("Usage: journal create <name> | journal list | journal export <id>")
            return
        sub = args[0]
        if sub == 'create' and len(args) > 1:
            name = args[1]
            j = self.m.create_journal(name)
            print(f"Created journal: {j.name} ({j.journal_id})")
        elif sub == 'list':
            journals = self.m.list_journals()
            print(f"\nJournals ({len(journals)}):")
            for j in journals:
                print(f"  {j.name} ({j.journal_id}) - {len(j.note_ids)} notes")
        elif sub == 'export' and len(args) > 1:
            md = self.m.export_journal(args[1])
            print(md)

    def _cmd_note(self, args: List[str]):
        if not args:
            print("Usage: note list [--journal id] | note show <id>")
            return
        sub = args[0]
        if sub == 'list':
            journal_id = None
            if '--journal' in args:
                idx = args.index('--journal')
                if idx + 1 < len(args):
                    journal_id = args[idx + 1]
            notes = self.m.list_notes(journal_id=journal_id)
            print(f"\nNotes ({len(notes)}):")
            for n in notes:
                print(f"  [{n.created_at[:10]}] {n.query[:60]}... ({n.note_id})")
        elif sub == 'show' and len(args) > 1:
            note = self.m.get_note(args[1])
            if note:
                print(f"\nQ: {note.query}")
                print(f"\n{note.answer}")
                if note.citations:
                    print("\nSources:")
                    for c in note.citations:
                        print(f"  - {c.format()}")
            else:
                print(f"Note not found: {args[1]}")

    def _cmd_tags(self, args: List[str]):
        tags = self.m.list_tags()
        cloud = self.m.get_tag_cloud()
        print(f"\nTags ({len(tags)}):")
        for tag in tags:
            count = cloud.get(tag['name'], 0)
            print(f"  {tag['name']} ({count} docs)")

    def _cmd_report(self, args: List[str]):
        if not args:
            print("Usage: report <topic> --questions 'q1|q2|q3' [--journal id]")
            return
        topic = args[0]
        questions = []
        journal_id = None
        i = 1
        while i < len(args):
            if args[i] == '--questions' and i + 1 < len(args):
                questions = args[i + 1].split('|')
                i += 2
            elif args[i] == '--journal' and i + 1 < len(args):
                journal_id = args[i + 1]
                i += 2
            else:
                i += 1
        if not questions:
            print("No questions provided")
            return
        report = self.m.report(topic, questions, journal_id)
        print(report)


# ─────────────────────────────────────────────────────────────────────────────
# Factory / Convenience
# ─────────────────────────────────────────────────────────────────────────────

def create_marginalia(base_path: str = "~/.marginalia",
                      llm_provider: str = "mock",
                      llm_model: str = "",
                      llm_api_key: Optional[str] = None,
                      embedding_provider: str = "none",
                      embedding_model: str = "",
                      embedding_api_key: Optional[str] = None,
                      **kwargs) -> Marginalia:
    """Convenience factory for creating a Marginalia instance."""
    expanded_path = os.path.expanduser(base_path)
    return Marginalia(
        base_path=expanded_path,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        embedding_api_key=embedding_api_key,
        **kwargs
    )


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    base_path = os.environ.get("MARGINALIA_PATH", os.path.expanduser("~/.marginalia"))
    llm_provider = os.environ.get("MARGINALIA_LLM", "mock")
    llm_model = os.environ.get("MARGINALIA_LLM_MODEL", "")
    llm_api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
    embedding_provider = os.environ.get("MARGINALIA_EMBED", "none")

    m = create_marginalia(
        base_path=base_path,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        embedding_provider=embedding_provider
    )

    cli = CLI(m)
    cli.run()