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
    mime_type: str
    size_bytes: int
    created_at: str
    modified_at: str
    ingested_at: str
    checksum: str
    tags: List[str] = field(default_factory=list)
    catalog: str = ""
    folder: str = ""
    language: str = "en"
    author: str = ""
    description: str = ""
    page_count: int = 0
    word_count: int = 0
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "DocumentMetadata":
        return cls(**d)


@dataclass
class TextChunk:
    chunk_id: str
    doc_id: str
    content: str
    chunk_index: int
    start_offset: int
    end_offset: int
    page_number: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    section: Optional[str] = None
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['embedding'] = None  # Don't serialize embedding to JSON
        return d


@dataclass
class SearchResult:
    doc_id: str
    chunk_id: str
    file_path: str
    title: str
    content: str
    score: float
    rank: int
    page_number: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    section: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    catalog: str = ""


@dataclass
class Citation:
    doc_id: str
    file_path: str
    title: str
    chunk_id: str
    quote: str
    page_number: Optional[int] = None
    line_start: Optional[int] = None
    section: Optional[str] = None

    def format(self) -> str:
        parts = [f'[{self.title}]']
        if self.page_number:
            parts.append(f'p.{self.page_number}')
        if self.line_start:
            parts.append(f'L{self.line_start}')
        if self.section:
            parts.append(f'§{self.section}')
        return ' '.join(parts)


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

    def to_dict(self) -> Dict:
        return {
            'note_id': self.note_id,
            'query': self.query,
            'answer': self.answer,
            'citations': [asdict(c) for c in self.citations],
            'created_at': self.created_at,
            'tags': self.tags,
            'follow_up_questions': self.follow_up_questions,
            'related_note_ids': self.related_note_ids,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "InvestigationNote":
        citations = [Citation(**c) for c in d.get('citations', [])]
        return cls(
            note_id=d['note_id'],
            query=d['query'],
            answer=d['answer'],
            citations=citations,
            created_at=d['created_at'],
            tags=d.get('tags', []),
            follow_up_questions=d.get('follow_up_questions', []),
            related_note_ids=d.get('related_note_ids', []),
        )


@dataclass
class Relation:
    relation_id: str
    source_doc_id: str
    target_doc_id: str
    relation_type: str
    strength: float
    evidence: str = ""
    created_at: str = ""


@dataclass
class View:
    view_id: str
    name: str
    description: str
    query: str
    filters: Dict[str, Any]
    sort_by: str
    created_at: str
    doc_ids: List[str] = field(default_factory=list)


@dataclass
class Journal:
    journal_id: str
    name: str
    description: str
    entries: List[Dict] = field(default_factory=list)
    created_at: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Database Layer
# ─────────────────────────────────────────────────────────────────────────────

class Database:
    """SQLite-backed storage for all Marginalia data."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
            if HAS_SQLITE_VEC:
                self._local.conn.enable_load_extension(True)
                sqlite_vec.load(self._local.conn)
                self._local.conn.enable_load_extension(False)
        return self._local.conn

    def _init_db(self):
        c = self.conn
        c.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                file_path TEXT UNIQUE NOT NULL,
                title TEXT,
                file_type TEXT,
                mime_type TEXT,
                size_bytes INTEGER,
                created_at TEXT,
                modified_at TEXT,
                ingested_at TEXT,
                checksum TEXT,
                tags TEXT DEFAULT '[]',
                catalog TEXT DEFAULT '',
                folder TEXT DEFAULT '',
                language TEXT DEFAULT 'en',
                author TEXT DEFAULT '',
                description TEXT DEFAULT '',
                page_count INTEGER DEFAULT 0,
                word_count INTEGER DEFAULT 0,
                custom_fields TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_index INTEGER,
                start_offset INTEGER,
                end_offset INTEGER,
                page_number INTEGER,
                line_start INTEGER,
                line_end INTEGER,
                section TEXT,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                doc_id UNINDEXED,
                content,
                content='chunks',
                content_rowid='rowid'
            );

            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                embedding BLOB,
                model TEXT,
                FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tags (
                tag_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                color TEXT DEFAULT '',
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS catalogs (
                catalog_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                parent_catalog TEXT DEFAULT '',
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS relations (
                relation_id TEXT PRIMARY KEY,
                source_doc_id TEXT NOT NULL,
                target_doc_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                evidence TEXT DEFAULT '',
                created_at TEXT,
                FOREIGN KEY (source_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (target_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS views (
                view_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                query TEXT DEFAULT '',
                filters TEXT DEFAULT '{}',
                sort_by TEXT DEFAULT 'ingested_at',
                created_at TEXT,
                doc_ids TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS journals (
                journal_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                entries TEXT DEFAULT '[]',
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS investigation_notes (
                note_id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                answer TEXT NOT NULL,
                citations TEXT DEFAULT '[]',
                created_at TEXT,
                tags TEXT DEFAULT '[]',
                follow_up_questions TEXT DEFAULT '[]',
                related_note_ids TEXT DEFAULT '[]'
            );

            CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
            CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_doc_id);
            CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_doc_id);
            CREATE INDEX IF NOT EXISTS idx_documents_catalog ON documents(catalog);
            CREATE INDEX IF NOT EXISTS idx_documents_folder ON documents(folder);
        """)
        c.commit()

    def upsert_document(self, meta: DocumentMetadata):
        self.conn.execute("""
            INSERT OR REPLACE INTO documents
            (doc_id, file_path, title, file_type, mime_type, size_bytes,
             created_at, modified_at, ingested_at, checksum, tags, catalog,
             folder, language, author, description, page_count, word_count, custom_fields)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            meta.doc_id, meta.file_path, meta.title, meta.file_type,
            meta.mime_type, meta.size_bytes, meta.created_at, meta.modified_at,
            meta.ingested_at, meta.checksum, json.dumps(meta.tags),
            meta.catalog, meta.folder, meta.language, meta.author,
            meta.description, meta.page_count, meta.word_count,
            json.dumps(meta.custom_fields)
        ))
        self.conn.commit()

    def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        row = self.conn.execute(
            "SELECT * FROM documents WHERE doc_id = ?", (doc_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_metadata(row)

    def get_document_by_path(self, file_path: str) -> Optional[DocumentMetadata]:
        row = self.conn.execute(
            "SELECT * FROM documents WHERE file_path = ?", (file_path,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_metadata(row)

    def _row_to_metadata(self, row) -> DocumentMetadata:
        d = dict(row)
        d['tags'] = json.loads(d['tags'])
        d['custom_fields'] = json.loads(d['custom_fields'])
        return DocumentMetadata(**d)

    def list_documents(self, catalog: str = "", folder: str = "",
                       tags: List[str] = None, limit: int = 1000,
                       offset: int = 0) -> List[DocumentMetadata]:
        query = "SELECT * FROM documents WHERE 1=1"
        params = []
        if catalog:
            query += " AND catalog = ?"
            params.append(catalog)
        if folder:
            query += " AND folder LIKE ?"
            params.append(f"{folder}%")
        query += f" ORDER BY ingested_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self.conn.execute(query, params).fetchall()
        results = [self._row_to_metadata(r) for r in rows]
        if tags:
            results = [r for r in results if any(t in r.tags for t in tags)]
        return results

    def delete_document(self, doc_id: str):
        self.conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        self.conn.commit()

    def insert_chunk(self, chunk: TextChunk):
        self.conn.execute("""
            INSERT OR REPLACE INTO chunks
            (chunk_id, doc_id, content, chunk_index, start_offset, end_offset,
             page_number, line_start, line_end, section)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            chunk.chunk_id, chunk.doc_id, chunk.content, chunk.chunk_index,
            chunk.start_offset, chunk.end_offset, chunk.page_number,
            chunk.line_start, chunk.line_end, chunk.section
        ))
        self.conn.execute("""
            INSERT OR REPLACE INTO chunks_fts(chunk_id, doc_id, content)
            VALUES (?,?,?)
        """, (chunk.chunk_id, chunk.doc_id, chunk.content))
        self.conn.commit()

    def get_chunks_for_doc(self, doc_id: str) -> List[TextChunk]:
        rows = self.conn.execute(
            "SELECT * FROM chunks WHERE doc_id = ? ORDER BY chunk_index",
            (doc_id,)
        ).fetchall()
        return [self._row_to_chunk(r) for r in rows]

    def get_chunk(self, chunk_id: str) -> Optional[TextChunk]:
        row = self.conn.execute(
            "SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_chunk(row)

    def _row_to_chunk(self, row) -> TextChunk:
        d = dict(row)
        return TextChunk(
            chunk_id=d['chunk_id'],
            doc_id=d['doc_id'],
            content=d['content'],
            chunk_index=d['chunk_index'],
            start_offset=d['start_offset'],
            end_offset=d['end_offset'],
            page_number=d.get('page_number'),
            line_start=d.get('line_start'),
            line_end=d.get('line_end'),
            section=d.get('section'),
        )

    def delete_chunks_for_doc(self, doc_id: str):
        self.conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        self.conn.commit()

    def fts_search(self, query: str, limit: int = 20,
                   doc_ids: List[str] = None) -> List[Tuple[str, str, float]]:
        """Returns list of (chunk_id, doc_id, score)."""
        safe_query = query.replace('"', '""')
        sql = """
            SELECT chunk_id, doc_id, rank
            FROM chunks_fts
            WHERE chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """
        try:
            rows = self.conn.execute(sql, (safe_query, limit * 3)).fetchall()
        except sqlite3.OperationalError:
            # Fallback to LIKE search
            rows = self._like_search(query, limit * 3)

        results = []
        for row in rows:
            cid, did, rank = row['chunk_id'], row['doc_id'], row['rank']
            if doc_ids and did not in doc_ids:
                continue
            score = 1.0 / (1.0 + abs(float(rank)))
            results.append((cid, did, score))
        return results[:limit]

    def _like_search(self, query: str, limit: int) -> List:
        terms = query.lower().split()
        if not terms:
            return []
        conditions = " AND ".join(["LOWER(content) LIKE ?" for _ in terms])
        params = [f"%{t}%" for t in terms] + [limit]
        sql = f"SELECT chunk_id, doc_id, -1.0 as rank FROM chunks WHERE {conditions} LIMIT ?"
        return self.conn.execute(sql, params).fetchall()

    def store_embedding(self, chunk_id: str, doc_id: str,
                        embedding: List[float], model: str):
        import struct
        blob = struct.pack(f'{len(embedding)}f', *embedding)
        self.conn.execute("""
            INSERT OR REPLACE INTO embeddings (chunk_id, doc_id, embedding, model)
            VALUES (?,?,?,?)
        """, (chunk_id, doc_id, blob, model))
        self.conn.commit()

    def get_embedding(self, chunk_id: str) -> Optional[List[float]]:
        row = self.conn.execute(
            "SELECT embedding FROM embeddings WHERE chunk_id = ?", (chunk_id,)
        ).fetchone()
        if not row or not row['embedding']:
            return None
        import struct
        blob = row['embedding']
        n = len(blob) // 4
        return list(struct.unpack(f'{n}f', blob))

    def get_all_embeddings(self) -> List[Tuple[str, str, List[float]]]:
        import struct
        rows = self.conn.execute(
            "SELECT chunk_id, doc_id, embedding FROM embeddings WHERE embedding IS NOT NULL"
        ).fetchall()
        results = []
        for row in rows:
            blob = row['embedding']
            n = len(blob) // 4
            emb = list(struct.unpack(f'{n}f', blob))
            results.append((row['chunk_id'], row['doc_id'], emb))
        return results

    def upsert_relation(self, relation: Relation):
        self.conn.execute("""
            INSERT OR REPLACE INTO relations
            (relation_id, source_doc_id, target_doc_id, relation_type, strength, evidence, created_at)
            VALUES (?,?,?,?,?,?,?)
        """, (
            relation.relation_id, relation.source_doc_id, relation.target_doc_id,
            relation.relation_type, relation.strength, relation.evidence, relation.created_at
        ))
        self.conn.commit()

    def get_relations(self, doc_id: str) -> List[Relation]:
        rows = self.conn.execute("""
            SELECT * FROM relations WHERE source_doc_id = ? OR target_doc_id = ?
        """, (doc_id, doc_id)).fetchall()
        return [Relation(**dict(r)) for r in rows]

    def upsert_view(self, view: View):
        self.conn.execute("""
            INSERT OR REPLACE INTO views
            (view_id, name, description, query, filters, sort_by, created_at, doc_ids)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            view.view_id, view.name, view.description, view.query,
            json.dumps(view.filters), view.sort_by, view.created_at,
            json.dumps(view.doc_ids)
        ))
        self.conn.commit()

    def get_view(self, name: str) -> Optional[View]:
        row = self.conn.execute(
            "SELECT * FROM views WHERE name = ?", (name,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d['filters'] = json.loads(d['filters'])
        d['doc_ids'] = json.loads(d['doc_ids'])
        return View(**d)

    def list_views(self) -> List[View]:
        rows = self.conn.execute("SELECT * FROM views").fetchall()
        views = []
        for row in rows:
            d = dict(row)
            d['filters'] = json.loads(d['filters'])
            d['doc_ids'] = json.loads(d['doc_ids'])
            views.append(View(**d))
        return views

    def upsert_journal(self, journal: Journal):
        self.conn.execute("""
            INSERT OR REPLACE INTO journals
            (journal_id, name, description, entries, created_at)
            VALUES (?,?,?,?,?)
        """, (
            journal.journal_id, journal.name, journal.description,
            json.dumps(journal.entries), journal.created_at
        ))
        self.conn.commit()

    def get_journal(self, name: str) -> Optional[Journal]:
        row = self.conn.execute(
            "SELECT * FROM journals WHERE name = ?", (name,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d['entries'] = json.loads(d['entries'])
        return Journal(**d)

    def save_investigation_note(self, note: InvestigationNote):
        d = note.to_dict()
        self.conn.execute("""
            INSERT OR REPLACE INTO investigation_notes
            (note_id, query, answer, citations, created_at, tags, follow_up_questions, related_note_ids)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            d['note_id'], d['query'], d['answer'],
            json.dumps(d['citations']), d['created_at'],
            json.dumps(d['tags']), json.dumps(d['follow_up_questions']),
            json.dumps(d['related_note_ids'])
        ))
        self.conn.commit()

    def get_investigation_note(self, note_id: str) -> Optional[InvestigationNote]:
        row = self.conn.execute(
            "SELECT * FROM investigation_notes WHERE note_id = ?", (note_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_note(row)

    def list_investigation_notes(self, limit: int = 50) -> List[InvestigationNote]:
        rows = self.conn.execute(
            "SELECT * FROM investigation_notes ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [self._row_to_note(r) for r in rows]

    def search_investigation_notes(self, query: str, limit: int = 10) -> List[InvestigationNote]:
        terms = query.lower().split()
        if not terms:
            return []
        conditions = " AND ".join(["(LOWER(query) LIKE ? OR LOWER(answer) LIKE ?)" for _ in terms])
        params = []
        for t in terms:
            params.extend([f"%{t}%", f"%{t}%"])
        params.append(limit)
        rows = self.conn.execute(
            f"SELECT * FROM investigation_notes WHERE {conditions} ORDER BY created_at DESC LIMIT ?",
            params
        ).fetchall()
        return [self._row_to_note(r) for r in rows]

    def _row_to_note(self, row) -> InvestigationNote:
        d = dict(row)
        citations_data = json.loads(d['citations'])
        citations = [Citation(**c) for c in citations_data]
        return InvestigationNote(
            note_id=d['note_id'],
            query=d['query'],
            answer=d['answer'],
            citations=citations,
            created_at=d['created_at'],
            tags=json.loads(d['tags']),
            follow_up_questions=json.loads(d['follow_up_questions']),
            related_note_ids=json.loads(d['related_note_ids']),
        )

    def upsert_tag(self, name: str, description: str = "", color: str = ""):
        tag_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()
        self.conn.execute("""
            INSERT OR IGNORE INTO tags (tag_id, name, description, color, created_at)
            VALUES (?,?,?,?,?)
        """, (tag_id, name, description, color, now))
        self.conn.commit()

    def list_tags(self) -> List[Dict]:
        rows = self.conn.execute("SELECT * FROM tags ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def upsert_catalog(self, name: str, description: str = "", parent: str = ""):
        cat_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()
        self.conn.execute("""
            INSERT OR IGNORE INTO catalogs (catalog_id, name, description, parent_catalog, created_at)
            VALUES (?,?,?,?,?)
        """, (cat_id, name, description, parent, now))
        self.conn.commit()

    def list_catalogs(self) -> List[Dict]:
        rows = self.conn.execute("SELECT * FROM catalogs ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> Dict:
        stats = {}
        stats['total_documents'] = self.conn.execute(
            "SELECT COUNT(*) FROM documents"
        ).fetchone()[0]
        stats['total_chunks'] = self.conn.execute(
            "SELECT COUNT(*) FROM chunks"
        ).fetchone()[0]
        stats['total_embeddings'] = self.conn.execute(
            "SELECT COUNT(*) FROM embeddings"
        ).fetchone()[0]
        stats['total_relations'] = self.conn.execute(
            "SELECT COUNT(*) FROM relations"
        ).fetchone()[0]
        stats['total_notes'] = self.conn.execute(
            "SELECT COUNT(*) FROM investigation_notes"
        ).fetchone()[0]
        stats['catalogs'] = self.conn.execute(
            "SELECT catalog, COUNT(*) as cnt FROM documents GROUP BY catalog"
        ).fetchall()
        return stats


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
        '.log', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg',
        '.zip', '.tar', '.gz', '.bz2', '.tar.gz', '.tar.bz2',
        '.html', '.htm', '.xml',
        '.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.go', '.rs',
        '.sh', '.bash', '.zsh', '.fish',
        '.tex', '.bib',
    }

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def can_ingest(self, file_path: str) -> bool:
        p = Path(file_path)
        ext = p.suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def ingest_file(self, file_path: str) -> Tuple[DocumentMetadata, List[TextChunk]]:
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        stat = p.stat()
        checksum = self._compute_checksum(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"
        file_type = p.suffix.lower().lstrip('.')
        now = datetime.datetime.utcnow().isoformat()

        doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, file_path))

        meta = DocumentMetadata(
            doc_id=doc_id,
            file_path=str(p.resolve()),
            title=p.stem,
            file_type=file_type,
            mime_type=mime_type,
            size_bytes=stat.st_size,
            created_at=datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified_at=datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            ingested_at=now,
            checksum=checksum,
            folder=str(p.parent.resolve()),
        )

        pages_and_text = self._extract_text(file_path, file_type, mime_type)
        chunks = self._create_chunks(doc_id, pages_and_text)

        # Update metadata with derived info
        all_text = " ".join(pt[1] for pt in pages_and_text)
        meta.word_count = len(all_text.split())
        meta.page_count = len(pages_and_text)

        return meta, chunks

    def _compute_checksum(self, file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()

    def _extract_text(self, file_path: str, file_type: str,
                      mime_type: str) -> List[Tuple[Optional[int], str, Optional[int], Optional[int]]]:
        """Returns list of (page_number, text, line_start, line_end)."""
        ext = Path(file_path).suffix.lower()

        if ext in ('.txt', '.md', '.markdown', '.rst', '.org', '.log',
                   '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg',
                   '.html', '.htm', '.xml', '.tex', '.bib',
                   '.py', '.js', '.ts', '.java', '.c', '.cpp', '.h',
                   '.go', '.rs', '.sh', '.bash', '.zsh', '.fish'):
            return self._extract_text_file(file_path)

        elif ext == '.pdf':
            return self._extract_pdf(file_path)

        elif ext == '.docx':
            return self._extract_docx(file_path)

        elif ext in ('.xlsx', '.xls'):
            return self._extract_spreadsheet(file_path)

        elif ext in ('.csv', '.tsv'):
            return self._extract_csv(file_path)

        elif ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'):
            return self._extract_image(file_path)

        elif ext in ('.zip', '.tar', '.gz', '.bz2') or file_path.endswith('.tar.gz') or file_path.endswith('.tar.bz2'):
            return self._extract_archive(file_path)

        else:
            # Try as text
            try:
                return self._extract_text_file(file_path)
            except Exception:
                return [(None, f"[Binary file: {Path(file_path).name}]", None, None)]

    def _extract_text_file(self, file_path: str) -> List[Tuple]:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except Exception as e:
            return [(None, f"[Error reading file: {e}]", None, None)]

        # Split into logical pages of ~50 lines
        page_size = 50
        results = []
        for i in range(0, max(1, len(lines)), page_size):
            page_lines = lines[i:i + page_size]
            text = ''.join(page_lines)
            page_num = i // page_size + 1
            line_start = i + 1
            line_end = i + len(page_lines)
            results.append((page_num, text, line_start, line_end))

        if not results:
            results = [(1, "", 1, 1)]
        return results

    def _extract_pdf(self, file_path: str) -> List[Tuple]:
        if not HAS_PYPDF:
            return [(None, f"[PDF: {Path(file_path).name} - pypdf not installed]", None, None)]
        try:
            results = []
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for i, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text() or ""
                    except Exception:
                        text = ""
                    results.append((i + 1, text, None, None))
            return results if results else [(1, "", None, None)]
        except Exception as e:
            return [(None, f"[PDF error: {e}]", None, None)]

    def _extract_docx(self, file_path: str) -> List[Tuple]:
        if not HAS_DOCX:
            return [(None, f"[DOCX: {Path(file_path).name} - python-docx not installed]", None, None)]
        try:
            doc = docx.Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs]
            # Group into pages of ~20 paragraphs
            page_size = 20
            results = []
            for i in range(0, max(1, len(paragraphs)), page_size):
                chunk_paras = paragraphs[i:i + page_size]
                text = '\n'.join(chunk_paras)
                results.append((i // page_size + 1, text, None, None))
            return results if results else [(1, "", None, None)]
        except Exception as e:
            return [(None, f"[DOCX error: {e}]", None, None)]

    def _extract_spreadsheet(self, file_path: str) -> List[Tuple]:
        if not HAS_OPENPYXL:
            return [(None, f"[Spreadsheet: {Path(file_path).name} - openpyxl not installed]", None, None)]
        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            results = []
            for sheet_idx, sheet_name in enumerate(wb.sheetnames):
                ws = wb[sheet_name]
                rows_text = []
                for row in ws.iter_rows(values_only=True):
                    row_str = '\t'.join(str(c) if c is not None else '' for c in row)
                    rows_text.append(row_str)
                text = f"Sheet: {sheet_name}\n" + '\n'.join(rows_text)
                results.append((sheet_idx + 1, text, None, None))
            return results if results else [(1, "", None, None)]
        except Exception as e:
            return [(None, f"[Spreadsheet error: {e}]", None, None)]

    def _extract_csv(self, file_path: str) -> List[Tuple]:
        try:
            import csv as csv_module
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv_module.reader(f)
                rows = list(reader)
            # Group into slices of 100 rows
            slice_size = 100
            results = []
            for i in range(0, max(1, len(rows)), slice_size):
                slice_rows = rows[i:i + slice_size]
                text = '\n'.join('\t'.join(str(c) for c in row) for row in slice_rows)
                results.append((i // slice_size + 1, text, i + 1, i + len(slice_rows)))
            return results if results else [(1, "", 1, 1)]
        except Exception as e:
            return [(None, f"[CSV error: {e}]", None, None)]

    def _extract_image(self, file_path: str) -> List[Tuple]:
        if not HAS_PIL:
            return [(None, f"[Image: {Path(file_path).name} - PIL not installed]", None, None)]
        try:
            img = Image.open(file_path)
            info = f"Image: {Path(file_path).name}\nFormat: {img.format}\nMode: {img.mode}\nSize: {img.size[0]}x{img.size[1]}"
            # Try OCR if available
            try:
                import pytesseract
                text = pytesseract.image_to_string(img)
                info += f"\n\nOCR Text:\n{text}"
            except ImportError:
                info += "\n[OCR not available - install pytesseract]"
            return [(1, info, None, None)]
        except Exception as e:
            return [(None, f"[Image error: {e}]", None, None)]

    def _extract_archive(self, file_path: str) -> List[Tuple]:
        results = []
        try:
            if zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, 'r') as zf:
                    for i, name in enumerate(zf.namelist()):
                        try:
                            with zf.open(name) as member:
                                content = member.read(65536)  # First 64KB
                                try:
                                    text = content.decode('utf-8', errors='replace')
                                except Exception:
                                    text = f"[Binary member: {name}]"
                                results.append((i + 1, f"Archive member: {name}\n{text}", None, None))
                        except Exception:
                            results.append((i + 1, f"[Could not read: {name}]", None, None))
            elif tarfile.is_tarfile(file_path):
                with tarfile.open(file_path, 'r:*') as tf:
                    for i, member in enumerate(tf.getmembers()):
                        if member.isfile():
                            try:
                                f = tf.extractfile(member)
                                if f:
                                    content = f.read(65536)
                                    try:
                                        text = content.decode('utf-8', errors='replace')
                                    except Exception:
                                        text = f"[Binary member: {member.name}]"
                                    results.append((i + 1, f"Archive member: {member.name}\n{text}", None, None))
                            except Exception:
                                results.append((i + 1, f"[Could not read: {member.name}]", None, None))
        except Exception as e:
            results.append((None, f"[Archive error: {e}]", None, None))

        return results if results else [(1, f"[Empty archive: {Path(file_path).name}]", None, None)]

    def _create_chunks(self, doc_id: str,
                       pages: List[Tuple]) -> List[TextChunk]:
        chunks = []
        chunk_index = 0
        global_offset = 0

        for page_num, text, line_start, line_end in pages:
            if not text.strip():
                global_offset += len(text)
                continue

            # Split text into overlapping chunks
            text_chunks = self._split_text(text)
            page_offset = 0

            for chunk_text in text_chunks:
                if not chunk_text.strip():
                    page_offset += len(chunk_text)
                    continue

                chunk_id = str(uuid.uuid4())
                # Estimate line numbers within chunk
                chunk_line_start = None
                chunk_line_end = None
                if line_start is not None:
                    lines_before = text[:page_offset].count('\n')
                    chunk_lines = chunk_text.count('\n')
                    chunk_line_start = line_start + lines_before
                    chunk_line_end = chunk_line_start + chunk_lines

                chunk = TextChunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    content=chunk_text,
                    chunk_index=chunk_index,
                    start_offset=global_offset + page_offset,
                    end_offset=global_offset + page_offset + len(chunk_text),
                    page_number=page_num,
                    line_start=chunk_line_start,
                    line_end=chunk_line_end,
                    section=self._detect_section(chunk_text),
                )
                chunks.append(chunk)
                chunk_index += 1
                page_offset += len(chunk_text) - self.chunk_overlap

            global_offset += len(text)

        return chunks

    def _split_text(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            if end >= len(text):
                chunks.append(text[start:])
                break

            # Try to break at paragraph boundary
            break_pos = text.rfind('\n\n', start, end)
            if break_pos == -1 or break_pos <= start:
                # Try sentence boundary
                break_pos = text.rfind('. ', start, end)
            if break_pos == -1 or break_pos <= start:
                # Try word boundary
                break_pos = text.rfind(' ', start, end)
            if break_pos == -1 or break_pos <= start:
                break_pos = end

            chunks.append(text[start:break_pos + 1])
            start = max(start + 1, break_pos + 1 - self.chunk_overlap)

        return chunks

    def _detect_section(self, text: str) -> Optional[str]:
        lines = text.strip().split('\n')
        for line in lines[:3]:
            line = line.strip()
            if line.startswith('#'):
                return line.lstrip('#').strip()
            if re.match(r'^[A-Z][A-Z\s]{3,50}$', line):
                return line
        return None

    def ingest_directory(self, directory: str,
                         recursive: bool = True) -> List[Tuple[DocumentMetadata, List[TextChunk]]]:
        results = []
        p = Path(directory)
        if not p.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        pattern = '**/*' if recursive else '*'
        for file_path in p.glob(pattern):
            if file_path.is_file() and self.can_ingest(str(file_path)):
                try:
                    meta, chunks = self.ingest_file(str(file_path))
                    results.append((meta, chunks))
                except Exception as e:
                    logger.warning(f"Failed to ingest {file_path}: {e}")

        return results


# ─────────────────────────────────────────────────────────────────────────────
# Embedding Engine
# ─────────────────────────────────────────────────────────────────────────────

class EmbeddingEngine:
    """Generates and manages text embeddings."""

    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 backend: str = "auto"):
        self.model_name = model
        self.backend = backend
        self._model = None
        self._dimension = 384

    def _load_model(self):
        if self._model is not None:
            return

        if self.backend == "auto":
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
                self.backend = "sentence_transformers"
                logger.info(f"Loaded SentenceTransformer model: {self.model_name}")
                return
            except ImportError:
                pass

            if HAS_OPENAI:
                self.backend = "openai"
                self._dimension = 1536
                logger.info("Using OpenAI embeddings")
                return

            logger.warning("No embedding backend available. Using TF-IDF fallback.")
            self.backend = "tfidf"

    def embed(self, texts: List[str]) -> List[List[float]]:
        self._load_model()

        if self.backend == "sentence_transformers":
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            return [e.tolist() for e in embeddings]

        elif self.backend == "openai":
            client = openai.OpenAI()
            response = client.embeddings.create(
                input=texts,
                model="text-embedding-ada-002"
            )
            return [item.embedding for item in response.data]

        else:
            return [self._tfidf_embed(t) for t in texts]

    def embed_single(self, text: str) -> List[float]:
        return self.embed([text])[0]

    def _tfidf_embed(self, text: str, dim: int = 384) -> List[float]:
        """Simple hash-based pseudo-embedding for fallback."""
        words = text.lower().split()
        vec = [0.0] * dim
        for word in words:
            h = hash(word) % dim
            vec[h] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not HAS_NUMPY:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
            norm_b = math.sqrt(sum(x * x for x in b)) or 1.0
            return dot / (norm_a * norm_b)
        else:
            a_arr = np.array(a)
            b_arr = np.array(b)
            return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr) + 1e-10))

    @property
    def dimension(self) -> int:
        self._load_model()
        return self._dimension


# ─────────────────────────────────────────────────────────────────────────────
# Search Engine
# ─────────────────────────────────────────────────────────────────────────────

class SearchEngine:
    """Multi-modal search: lexical, semantic, and hybrid."""

    def __init__(self, db: Database, embedding_engine: Optional[EmbeddingEngine] = None):
        self.db = db
        self.embedding_engine = embedding_engine
        self._reranker = None

    def search(self, query: str, limit: int = 10,
               mode: str = "lexical",
               catalog: str = "",
               tags: List[str] = None,
               source_quota: int = 3,
               rerank: bool = False) -> List[SearchResult]:
        """
        Search modes: lexical, semantic, hybrid
        source_quota: max results per source document
        """
        if mode == "semantic" and self.embedding_engine:
            raw_results = self._semantic_search(query, limit * 3)
        elif mode == "hybrid" and self.embedding_engine:
            lex_results = self._lexical_search(query, limit * 2)
            sem_results = self._semantic_search(query, limit * 2)
            raw_results = self._merge_results(lex_results, sem_results)
        else:
            raw_results = self._lexical_search(query, limit * 3)

        # Filter by catalog/tags
        if catalog or tags:
            filtered = []
            for chunk_id, doc_id, score in raw_results:
                meta = self.db.get_document(doc_id)
                if not meta:
                    continue
                if catalog and meta.catalog != catalog:
                    continue
                if tags and not any(t in meta.tags for t in tags):
                    continue
                filtered.append((chunk_id, doc_id, score))
            raw_results = filtered

        # Apply source quota
        if source_quota > 0:
            raw_results = self._apply_source_quota(raw_results, source_quota)

        # Build SearchResult objects
        results = []
        for rank, (chunk_id, doc_id, score) in enumerate(raw_results[:limit]):
            chunk = self.db.get_chunk(chunk_id)
            meta = self.db.get_document(doc_id)
            if not chunk or not meta:
                continue
            results.append(SearchResult(
                doc_id=doc_id,
                chunk_id=chunk_id,
                file_path=meta.file_path,
                title=meta.title,
                content=chunk.content,
                score=score,
                rank=rank + 1,
                page_number=chunk.page_number,
                line_start=chunk.line_start,
                line_end=chunk.line_end,
                section=chunk.section,
                tags=meta.tags,
                catalog=meta.catalog,
            ))

        if rerank and results:
            results = self._rerank(query, results)

        return results

    def _lexical_search(self, query: str, limit: int) -> List[Tuple[str, str, float]]:
        return self.db.fts_search(query, limit)

    def _semantic_search(self, query: str, limit: int) -> List[Tuple[str, str, float]]:
        if not self.embedding_engine:
            return []
        query_emb = self.embedding_engine.embed_single(query)
        all_embeddings = self.db.get_all_embeddings()
        if not all_embeddings:
            return []

        scored = []
        for chunk_id, doc_id, emb in all_embeddings:
            sim = self.embedding_engine.cosine_similarity(query_emb, emb)
            scored.append((chunk_id, doc_id, sim))

        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:limit]

    def _merge_results(self, lex: List[Tuple], sem: List[Tuple],
                       lex_weight: float = 0.5,
                       sem_weight: float = 0.5) -> List[Tuple]:
        scores = defaultdict(lambda: {'lex': 0.0, 'sem': 0.0, 'doc_id': ''})

        for chunk_id, doc_id, score in lex:
            scores[chunk_id]['lex'] = score
            scores[chunk_id]['doc_id'] = doc_id

        for chunk_id, doc_id, score in sem:
            scores[chunk_id]['sem'] = score
            scores[chunk_id]['doc_id'] = doc_id

        merged = []
        for chunk_id, vals in scores.items():
            combined = lex_weight * vals['lex'] + sem_weight * vals['sem']
            merged.append((chunk_id, vals['doc_id'], combined))

        merged.sort(key=lambda x: x[2], reverse=True)
        return merged

    def _apply_source_quota(self, results: List[Tuple],
                            quota: int) -> List[Tuple]:
        doc_counts = defaultdict(int)
        filtered = []
        for chunk_id, doc_id, score in results:
            if doc_counts[doc_id] < quota:
                filtered.append((chunk_id, doc_id, score))
                doc_counts[doc_id] += 1
        return filtered

    def _rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Simple BM25-style reranking."""
        query_terms = set(query.lower().split())
        for result in results:
            content_lower = result.content.lower()
            term_matches = sum(1 for t in query_terms if t in content_lower)
            boost = 1.0 + 0.1 * term_matches
            result.score *= boost

        results.sort(key=lambda r: r.score, reverse=True)
        for i, r in enumerate(results):
            r.rank = i + 1
        return results

    def search_notes(self, query: str, limit: int = 5) -> List[InvestigationNote]:
        return self.db.search_investigation_notes(query, limit)


# ─────────────────────────────────────────────────────────────────────────────
# Relation Miner
# ─────────────────────────────────────────────────────────────────────────────

class RelationMiner:
    """Discovers relationships between documents."""

    def __init__(self, db: Database, embedding_engine: Optional[EmbeddingEngine] = None):
        self.db = db
        self.embedding_engine = embedding_engine

    def mine_relations(self, doc_id: str, top_k: int = 5) -> List[Relation]:
        """Find related documents for a given document."""
        relations = []

        # Tag-based relations
        meta = self.db.get_document(doc_id)
        if not meta:
            return []

        all_docs = self.db.list_documents(limit=500)
        for other in all_docs:
            if other.doc_id == doc_id:
                continue

            # Tag overlap
            shared_tags = set(meta.tags) & set(other.tags)
            if shared_tags:
                strength = len(shared_tags) / max(len(meta.tags), len(other.tags), 1)
                rel = Relation(
                    relation_id=str(uuid.uuid4()),
                    source_doc_id=doc_id,
                    target_doc_id=other.doc_id,
                    relation_type="shared_tags",
                    strength=strength,
                    evidence=f"Shared tags: {', '.join(shared_tags)}",
                    created_at=datetime.datetime.utcnow().isoformat(),
                )
                relations.append(rel)

        # Semantic similarity
        if self.embedding_engine:
            source_chunks = self.db.get_chunks_for_doc(doc_id)
            if source_chunks:
                source_embs = [self.db.get_embedding(c.chunk_id) for c in source_chunks[:3]]
                source_embs = [e for e in source_embs if e]
                if source_embs:
                    avg_source = self._average_embeddings(source_embs)
                    all_embs = self.db.get_all_embeddings()
                    doc_scores = defaultdict(list)
                    for chunk_id, other_doc_id, emb in all_embs:
                        if other_doc_id == doc_id:
                            continue
                        sim = self.embedding_engine.cosine_similarity(avg_source, emb)
                        doc_scores[other_doc_id].append(sim)

                    for other_doc_id, sims in doc_scores.items():
                        avg_sim = sum(sims) / len(sims)
                        if avg_sim > 0.5:
                            rel = Relation(
                                relation_id=str(uuid.uuid4()),
                                source_doc_id=doc_id,
                                target_doc_id=other_doc_id,
                                relation_type="semantic_similarity",
                                strength=avg_sim,
                                evidence=f"Semantic similarity: {avg_sim:.3f}",
                                created_at=datetime.datetime.utcnow().isoformat(),
                            )
                            relations.append(rel)

        # Lexical co-occurrence
        relations.extend(self._find_lexical_relations(doc_id, all_docs))

        # Deduplicate and sort
        seen = set()
        unique_relations = []
        for rel in sorted(relations, key=lambda r: r.strength, reverse=True):
            key = (rel.source_doc_id, rel.target_doc_id, rel.relation_type)
            if key not in seen:
                seen.add(key)
                unique_relations.append(rel)

        return unique_relations[:top_k]

    def _average_embeddings(self, embeddings: List[List[float]]) -> List[float]:
        if not embeddings:
            return []
        dim = len(embeddings[0])
        avg = [0.0] * dim
        for emb in embeddings:
            for i, v in enumerate(emb):
                avg[i] += v
        n = len(embeddings)
        return [v / n for v in avg]

    def _find_lexical_relations(self, doc_id: str,
                                all_docs: List[DocumentMetadata]) -> List[Relation]:
        relations = []
        source_chunks = self.db.get_chunks_for_doc(doc_id)
        source_text = ' '.join(c.content for c in source_chunks).lower()
        source_words = set(re.findall(r'\b\w{4,}\b', source_text))

        for other in all_docs:
            if other.doc_id == doc_id:
                continue
            other_chunks = self.db.get_chunks_for_doc(other.doc_id)
            other_text = ' '.join(c.content for c in other_chunks[:5]).lower()
            other_words = set(re.findall(r'\b\w{4,}\b', other_text))

            overlap = source_words & other_words
            if len(overlap) > 10:
                strength = len(overlap) / max(len(source_words), len(other_words), 1)
                if strength > 0.1:
                    rel = Relation(
                        relation_id=str(uuid.uuid4()),
                        source_doc_id=doc_id,
                        target_doc_id=other.doc_id,
                        relation_type="lexical_overlap",
                        strength=strength,
                        evidence=f"Shared vocabulary ({len(overlap)} words)",
                        created_at=datetime.datetime.utcnow().isoformat(),
                    )
                    relations.append(rel)

        return relations

    def mine_all_relations(self, batch_size: int = 50) -> int:
        """Mine relations for all documents."""
        docs = self.db.list_documents(limit=batch_size)
        count = 0
        for doc in docs:
            relations = self.mine_relations(doc.doc_id)
            for rel in relations:
                self.db.upsert_relation(rel)
                count += 1
        return count


# ─────────────────────────────────────────────────────────────────────────────
# Catalog & Organization
# ─────────────────────────────────────────────────────────────────────────────

class CatalogManager:
    """Manages catalogs, tags, views, and journals."""

    def __init__(self, db: Database):
        self.db = db

    def create_catalog(self, name: str, description: str = "",
                       parent: str = "") -> str:
        self.db.upsert_catalog(name, description, parent)
        return name

    def assign_to_catalog(self, doc_id: str, catalog: str):
        meta = self.db.get_document(doc_id)
        if meta:
            meta.catalog = catalog
            self.db.upsert_document(meta)
            self.db.upsert_catalog(catalog)

    def add_tag(self, doc_id: str, tag: str):
        meta = self.db.get_document(doc_id)
        if meta and tag not in meta.tags:
            meta.tags.append(tag)
            self.db.upsert_document(meta)
            self.db.upsert_tag(tag)

    def remove_tag(self, doc_id: str, tag: str):
        meta = self.db.get_document(doc_id)
        if meta and tag in meta.tags:
            meta.tags.remove(tag)
            self.db.upsert_document(meta)

    def create_view(self, name: str, description: str = "",
                    query: str = "", filters: Dict = None,
                    sort_by: str = "ingested_at") -> View:
        view = View(
            view_id=str(uuid.uuid4()),
            name=name,
            description=description,
            query=query,
            filters=filters or {},
            sort_by=sort_by,
            created_at=datetime.datetime.utcnow().isoformat(),
        )
        # Populate doc_ids based on filters
        docs = self.db.list_documents(
            catalog=filters.get('catalog', '') if filters else '',
            tags=filters.get('tags', []) if filters else [],
        )
        view.doc_ids = [d.doc_id for d in docs]
        self.db.upsert_view(view)
        return view

    def get_view(self, name: str) -> Optional[View]:
        return self.db.get_view(name)

    def list_views(self) -> List[View]:
        return self.db.list_views()

    def create_journal(self, name: str, description: str = "") -> Journal:
        journal = Journal(
            journal_id=str(uuid.uuid4()),
            name=name,
            description=description,
            entries=[],
            created_at=datetime.datetime.utcnow().isoformat(),
        )
        self.db.upsert_journal(journal)
        return journal

    def add_journal_entry(self, journal_name: str, entry: Dict) -> bool:
        journal = self.db.get_journal(journal_name)
        if not journal:
            return False
        entry['timestamp'] = datetime.datetime.utcnow().isoformat()
        entry['entry_id'] = str(uuid.uuid4())
        journal.entries.append(entry)
        self.db.upsert_journal(journal)
        return True

    def get_journal(self, name: str) -> Optional[Journal]:
        return self.db.get_journal(name)

    def auto_tag_document(self, doc_id: str, tags: List[str]):
        for tag in tags:
            self.add_tag(doc_id, tag)

    def suggest_catalog(self, meta: DocumentMetadata) -> str:
        """Suggest a catalog based on file type and path."""
        ext = Path(meta.file_path).suffix.lower()
        type_map = {
            '.pdf': 'papers',
            '.docx': 'documents',
            '.doc': 'documents',
            '.md': 'notes',
            '.markdown': 'notes',
            '.txt': 'notes',
            '.py': 'code',
            '.js': 'code',
            '.ts': 'code',
            '.java': 'code',
            '.csv': 'data',
            '.xlsx': 'data',
            '.xls': 'data',
            '.png': 'images',
            '.jpg': 'images',
            '.jpeg': 'images',
            '.log': 'logs',
            '.zip': 'archives',
            '.tar': 'archives',
        }
        return type_map.get(ext, 'general')


# ─────────────────────────────────────────────────────────────────────────────
# LLM Client
# ─────────────────────────────────────────────────────────────────────────────

class LLMClient:
    """Unified interface for LLM providers."""

    def __init__(self, provider: str = "auto", model: str = None,
                 api_key: str = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self._client = None

        if provider == "auto":
            if HAS_ANTHROPIC and (api_key or os.environ.get("ANTHROPIC_API_KEY")):
                self.provider = "anthropic"
                self.model = model or "claude-3-5-sonnet-20241022"
            elif HAS_OPENAI and (api_key or os.environ.get("OPENAI_API_KEY")):
                self.provider = "openai"
                self.model = model or "gpt-4o"
            else:
                self.provider = "mock"
                self.model = "mock"

    def _get_client(self):
        if self._client:
            return self._client

        if self.provider == "anthropic":
            key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
            self._client = anthropic.Anthropic(api_key=key)
        elif self.provider == "openai":
            key = self.api_key or os.environ.get("OPENAI_API_KEY")
            self._client = openai.OpenAI(api_key=key)

        return self._client

    def complete(self, system_prompt: str, user_message: str,
                 max_tokens: int = 4096, temperature: float = 0.3) -> str:
        if self.provider == "mock":
            return self._mock_complete(system_prompt, user_message)

        client = self._get_client()

        if self.provider == "anthropic":
            response = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            )
            return response.content[0].text

        elif self.provider == "openai":
            response = client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            return response.choices[0].message.content

        return ""

    def _mock_complete(self, system_prompt: str, user_message: str) -> str:
        return (
            f"[Mock LLM Response]\n"
            f"Query: {user_message[:100]}...\n"
            f"Note: Configure ANTHROPIC_API_KEY or OPENAI_API_KEY for real responses."
        )

    @property
    def is_available(self) -> bool:
        return self.provider != "mock"


# ─────────────────────────────────────────────────────────────────────────────
# Research Agent
# ─────────────────────────────────────────────────────────────────────────────

class ResearchAgent:
    """
    The main LLM-powered research agent that reads original file windows
    before writing cited answers.
    """

    SYSTEM_PROMPT = """You are Marginalia, a research assistant with access to a personal knowledge base.

Your task is to answer questions by carefully reading the provided source excerpts and producing well-cited answers.

Guidelines:
1. Read ALL provided source excerpts carefully before answering
2. Ground every claim in the sources - use inline citations like [Source Title, p.N]
3. Quote directly when precision matters
4. Acknowledge when sources are insufficient or contradictory
5. Suggest follow-up questions when appropriate
6. Be concise but thorough

Citation format: [Document Title] or [Document Title, p.N] or [Document Title, L.N] for line numbers.
"""

    def __init__(self, db: Database, search_engine: SearchEngine,
                 llm_client: LLMClient, catalog_manager: CatalogManager):
        self.db = db
        self.search_engine = search_engine
        self.llm_client = llm_client
        self.catalog_manager = catalog_manager

    def answer(self, query: str,
               search_mode: str = "lexical",
               search_limit: int = 10,
               catalog: str = "",
               tags: List[str] = None,
               source_quota: int = 3,
               rerank: bool = False,
               include_notes: bool = True,
               save_note: bool = True) -> InvestigationNote:
        """
        Main entry point: search, read windows, generate cited answer,
        save investigation note.
        """
        # Step 1: Search for relevant chunks
        search_results = self.search_engine.search(
            query=query,
            limit=search_limit,
            mode=search_mode,
            catalog=catalog,
            tags=tags,
            source_quota=source_quota,
            rerank=rerank,
        )

        # Step 2: Optionally include relevant past notes
        past_notes = []
        if include_notes:
            past_notes = self.search_engine.search_notes(query, limit=3)

        # Step 3: Read original file windows for top results
        enriched_results = self._read_file_windows(search_results)

        # Step 4: Build context for LLM
        context = self._build_context(query, enriched_results, past_notes)

        # Step 5: Generate answer
        answer_text = self.llm_client.complete(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=context,
        )

        # Step 6: Extract citations
        citations = self._extract_citations(answer_text, enriched_results)

        # Step 7: Extract follow-up questions
        follow_ups = self._extract_follow_ups(answer_text)

        # Step 8: Create investigation note
        note = InvestigationNote(
            note_id=str(uuid.uuid4()),
            query=query,
            answer=answer_text,
            citations=citations,
            created_at=datetime.datetime.utcnow().isoformat(),
            tags=self._extract_tags_from_results(enriched_results),
            follow_up_questions=follow_ups,
            related_note_ids=[n.note_id for n in past_notes],
        )

        # Step 9: Save note
        if save_note:
            self.db.save_investigation_note(note)
            # Add to journal
            journal = self.db.get_journal("research_log")
            if not journal:
                self.catalog_manager.create_journal("research_log", "Automatic research log")
            self.catalog_manager.add_journal_entry("research_log", {
                'note_id': note.note_id,
                'query': query,
                'num_sources': len(citations),
            })

        return note

    def _read_file_windows(self, results: List[SearchResult]) -> List[Dict]:
        """Read the actual file sections for each search result."""
        enriched = []
        for result in results:
            window = self._read_window(result)
            enriched.append({
                'result': result,
                'window': window,
            })
        return enriched

    def _read_window(self, result: SearchResult) -> str:
        """Read a window of text around the matched chunk from the original file."""
        try:
            file_path = result.file_path
            if not Path(file_path).exists():
                return result.content

            ext = Path(file_path).suffix.lower()

            if ext == '.pdf' and HAS_PYPDF:
                return self._read_pdf_window(file_path, result.page_number)
            elif ext in ('.txt', '.md', '.markdown', '.rst', '.log',
                         '.py', '.js', '.json', '.yaml', '.yml',
                         '.html', '.htm', '.xml', '.csv', '.tsv'):
                return self._read_text_window(file_path, result.line_start, result.line_end)
            elif ext == '.docx' and HAS_DOCX:
                return self._read_docx_window(file_path, result.page_number)
            elif ext in ('.xlsx', '.xls') and HAS_OPENPYXL:
                return self._read_spreadsheet_window(file_path, result.page_number)
            elif ext in ('.zip',) and zipfile.is_zipfile(file_path):
                return self._read_archive_window(file_path, result.page_number)
            else:
                return result.content

        except Exception as e:
            logger.warning(f"Could not read window for {result.file_path}: {e}")
            return result.content

    def _read_pdf_window(self, file_path: str, page_number: Optional[int]) -> str:
        try:
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                if page_number and 1 <= page_number <= len(reader.pages):
                    page = reader.pages[page_number - 1]
                    return page.extract_text() or ""
                elif reader.pages:
                    return reader.pages[0].extract_text() or ""
        except Exception as e:
            return f"[PDF read error: {e}]"
        return ""

    def _read_text_window(self, file_path: str,
                          line_start: Optional[int],
                          line_end: Optional[int],
                          context_lines: int = 10) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()

            if line_start and line_end:
                start = max(0, line_start - context_lines - 1)
                end = min(len(lines), line_end + context_lines)
                return ''.join(lines[start:end])
            else:
                return ''.join(lines[:100])
        except Exception as e:
            return f"[Text read error: {e}]"

    def _read_docx_window(self, file_path: str, page_number: Optional[int]) -> str:
        try:
            doc = docx.Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs]
            if page_number:
                start = (page_number - 1) * 20
                end = start + 20
                return '\n'.join(paragraphs[start:end])
            return '\n'.join(paragraphs[:20])
        except Exception as e:
            return f"[DOCX read error: {e}]"

    def _read_spreadsheet_window(self, file_path: str, page_number: Optional[int]) -> str:
        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheet_names = wb.sheetnames
            if page_number and 1 <= page_number <= len(sheet_names):
                ws = wb[sheet_names[page_number - 1]]
            else:
                ws = wb.active

            rows = []
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i >= 50:
                    break
                rows.append('\t'.join(str(c) if c is not None else '' for c in row))
            return '\n'.join(rows)
        except Exception as e:
            return f"[Spreadsheet read error: {e}]"

    def _read_archive_window(self, file_path: str, page_number: Optional[int]) -> str:
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                names = zf.namelist()
                if page_number and 1 <= page_number <= len(names):
                    name = names[page_number - 1]
                    with zf.open(name) as f:
                        content = f.read(8192).decode('utf-8', errors='replace')
                    return f"Archive member: {name}\n{content}"
                elif names:
                    with zf.open(names[0]) as f:
                        content = f.read(8192).decode('utf-8', errors='replace')
                    return f"Archive member: {names[0]}\n{content}"
        except Exception as e:
            return f"[Archive read error: {e}]"
        return ""

    def _build_context(self, query: str, enriched_results: List[Dict],
                       past_notes: List[InvestigationNote]) -> str:
        parts = [f"## Research Query\n{query}\n"]

        if past_notes:
            parts.append("## Relevant Past Research Notes")
            for note in past_notes[:2]:
                parts.append(f"### Previous Note: {note.query}")
                parts.append(note.answer[:500] + "..." if len(note.answer) > 500 else note.answer)
                parts.append("")

        if enriched_results:
            parts.append("## Source Excerpts")
            for i, item in enumerate(enriched_results):
                result = item['result']
                window = item['window']
                parts.append(f"### Source {i+1}: {result.title}")
                parts.append(f"File: {result.file_path}")
                if result.page_number:
                    parts.append(f"Page: {result.page_number}")
                if result.line_start:
                    parts.append(f"Lines: {result.line_start}-{result.line_end}")
                if result.section:
                    parts.append(f"Section: {result.section}")
                parts.append(f"Relevance score: {result.score:.3f}")
                parts.append("")
                parts.append("```")
                parts.append(window[:2000] if len(window) > 2000 else window)
                parts.append("```")
                parts.append("")
        else:
            parts.append("## Note\nNo relevant sources found in the knowledge base.")

        parts.append("## Instructions")
        parts.append(
            "Please provide a comprehensive, well-cited answer to the research query above. "
            "Use inline citations referencing the source titles. "
            "If the sources are insufficient, say so clearly. "
            "End with 2-3 follow-up questions prefixed with 'Follow-up:'"
        )

        return '\n'.join(parts)

    def _extract_citations(self, answer_text: str,
                           enriched_results: List[Dict]) -> List[Citation]:
        citations = []
        seen = set()

        for item in enriched_results:
            result = item['result']
            title = result.title

            # Check if this source is referenced in the answer
            if title.lower() in answer_text.lower() or f"Source" in answer_text:
                if result.chunk_id not in seen:
                    seen.add(result.chunk_id)
                    # Extract a relevant quote
                    quote = result.content[:200].strip()
                    citation = Citation(
                        doc_id=result.doc_id,
                        file_path=result.file_path,
                        title=title,
                        chunk_id=result.chunk_id,
                        quote=quote,
                        page_number=result.page_number,
                        line_start=result.line_start,
                        section=result.section,
                    )
                    citations.append(citation)

        return citations

    def _extract_follow_ups(self, answer_text: str) -> List[str]:
        follow_ups = []
        lines = answer_text.split('\n')
        for line in lines:
            if line.strip().lower().startswith('follow-up:'):
                q = line.split(':', 1)[1].strip()
                if q:
                    follow_ups.append(q)
        return follow_ups[:5]

    def _extract_tags_from_results(self, enriched_results: List[Dict]) -> List[str]:
        tags = set()
        for item in enriched_results:
            tags.update(item['result'].tags)
        return list(tags)[:10]

    def generate_report(self, topic: str, notes: List[InvestigationNote] = None,
                        search_limit: int = 20) -> str:
        """Generate a comprehensive research report on a topic."""
        if notes is None:
            notes = self.db.search_investigation_notes(topic, limit=10)

        search_results = self.search_engine.search(
            query=topic, limit=search_limit, mode="lexical"
        )
        enriched = self._read_file_windows(search_results)

        report_prompt = f"""Generate a comprehensive research report on: {topic}

## Available Sources
{self._build_source_summary(enriched)}

## Previous Research Notes
{self._build_notes_summary(notes)}

Please write a structured report with:
1. Executive Summary
2. Key Findings (with citations)
3. Evidence Analysis
4. Gaps and Limitations
5. Recommendations for Further Research

Use proper citations throughout."""

        return self.llm_client.complete(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=report_prompt,
            max_tokens=8192,
        )

    def _build_source_summary(self, enriched_results: List[Dict]) -> str:
        lines = []
        for item in enriched_results[:10]:
            r = item['result']
            lines.append(f"- {r.title} (score: {r.score:.3f}): {r.content[:100]}...")
        return '\n'.join(lines)

    def _build_notes_summary(self, notes: List[InvestigationNote]) -> str:
        lines = []
        for note in notes[:5]:
            lines.append(f"- [{note.created_at[:10]}] {note.query}: {note.answer[:100]}...")
        return '\n'.join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Marginalia - Main System
# ─────────────────────────────────────────────────────────────────────────────

class Marginalia:
    """
    Main entry point for the Marginalia knowledge management system.
    Orchestrates ingestion, organization, search, and research.
    """

    def __init__(self, base_dir: str = "~/.marginalia",
                 llm_provider: str = "auto",
                 llm_model: str = None,
                 llm_api_key: str = None,
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 use_embeddings: bool = False):

        self.base_dir = Path(base_dir).expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)

        db_path = str(self.base_dir / "marginalia.db")
        self.db = Database(db_path)

        self.ingester = FileIngester(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        self.embedding_engine = None
        if use_embeddings:
            self.embedding_engine = EmbeddingEngine(model=embedding_model)

        self.search_engine = SearchEngine(self.db, self.embedding_engine)
        self.catalog_manager = CatalogManager(self.db)
        self.relation_miner = RelationMiner(self.db, self.embedding_engine)

        self.llm_client = LLMClient(
            provider=llm_provider,
            model=llm_model,
            api_key=llm_api_key,
        )

        self.agent = ResearchAgent(
            db=self.db,
            search_engine=self.search_engine,
            llm_client=self.llm_client,
            catalog_manager=self.catalog_manager,
        )

        logger.info(f"Marginalia initialized at {self.base_dir}")
        logger.info(f"LLM provider: {self.llm_client.provider} / {self.llm_client.model}")

    # ── Ingestion ──────────────────────────────────────────────────────────

    def ingest(self, path: str,
               catalog: str = "",
               tags: List[str] = None,
               recursive: bool = True,
               auto_catalog: bool = True,
               mine_relations: bool = False) -> List[DocumentMetadata]:
        """Ingest a file or directory."""
        p = Path(path)
        results = []

        if p.is_file():
            pairs = [self.ingester.ingest_file(str(p))]
        elif p.is_dir():
            pairs = self.ingester.ingest_directory(str(p), recursive=recursive)
        else:
            raise FileNotFoundError(f"Path not found: {path}")

        for meta, chunks in pairs:
            # Auto-assign catalog
            if auto_catalog and not catalog:
                meta.catalog = self.catalog_manager.suggest_catalog(meta)
            elif catalog:
                meta.catalog = catalog

            # Add tags
            if tags:
                meta.tags.extend(tags)

            # Save to DB
            self.db.upsert_document(meta)
            self.db.delete_chunks_for_doc(meta.doc_id)
            for chunk in chunks:
                self.db.insert_chunk(chunk)

            # Generate embeddings if enabled
            if self.embedding_engine:
                self._embed_chunks(meta.doc_id, chunks)

            # Ensure catalog exists
            if meta.catalog:
                self.db.upsert_catalog(meta.catalog)

            # Ensure tags exist
            for tag in meta.tags:
                self.db.upsert_tag(tag)

            results.append(meta)
            logger.info(f"Ingested: {meta.file_path} ({len(chunks)} chunks)")

        # Mine relations
        if mine_relations:
            for meta in results:
                relations = self.relation_miner.mine_relations(meta.doc_id)
                for rel in relations:
                    self.db.upsert_relation(rel)

        return results

    def _embed_chunks(self, doc_id: str, chunks: List[TextChunk]):
        if not self.embedding_engine:
            return
        texts = [c.content for c in chunks]
        try:
            embeddings = self.embedding_engine.embed(texts)
            for chunk, emb in zip(chunks, embeddings):
                self.db.store_embedding(
                    chunk.chunk_id, doc_id, emb,
                    self.embedding_engine.model_name
                )
        except Exception as e:
            logger.warning(f"Embedding failed for doc {doc_id}: {e}")

    def re_ingest(self, doc_id: str) -> Optional[DocumentMetadata]:
        """Re-ingest a document (e.g., after file change)."""
        meta = self.db.get_document(doc_id)
        if not meta:
            return None
        return self.ingest(meta.file_path, catalog=meta.catalog, tags=meta.tags)[0]

    def remove(self, doc_id: str) -> bool:
        """Remove a document from the knowledge base."""
        meta = self.db.get_document(doc_id)
        if not meta:
            return False
        self.db.delete_document(doc_id)
        logger.info(f"Removed document: {doc_id}")
        return True

    # ── Search ─────────────────────────────────────────────────────────────

    def search(self, query: str,
               limit: int = 10,
               mode: str = "lexical",
               catalog: str = "",
               tags: List[str] = None,
               source_quota: int = 3,
               rerank: bool = False) -> List[SearchResult]:
        """Search the knowledge base."""
        return self.search_engine.search(
            query=query,
            limit=limit,
            mode=mode,
            catalog=catalog,
            tags=tags,
            source_quota=source_quota,
            rerank=rerank,
        )

    # ── Research ───────────────────────────────────────────────────────────

    def ask(self, question: str,
            search_mode: str = "lexical",
            search_limit: int = 10,
            catalog: str = "",
            tags: List[str] = None,
            source_quota: int = 3,
            rerank: bool = False,
            include_notes: bool = True,
            save_note: bool = True) -> InvestigationNote:
        """Ask a research question and get a cited answer."""
        return self.agent.answer(
            query=question,
            search_mode=search_mode,
            search_limit=search_limit,
            catalog=catalog,
            tags=tags,
            source_quota=source_quota,
            rerank=rerank,
            include_notes=include_notes,
            save_note=save_note,
        )

    def report(self, topic: str, search_limit: int = 20) -> str:
        """Generate a comprehensive research report."""
        return self.agent.generate_report(topic, search_limit=search_limit)

    # ── Organization ───────────────────────────────────────────────────────

    def tag(self, doc_id: str, *tags: str):
        """Add tags to a document."""
        for tag in tags:
            self.catalog_manager.add_tag(doc_id, tag)

    def untag(self, doc_id: str, *tags: str):
        """Remove tags from a document."""
        for tag in tags:
            self.catalog_manager.remove_tag(doc_id, tag)

    def catalog(self, doc_id: str, catalog_name: str):
        """Assign a document to a catalog."""
        self.catalog_manager.assign_to_catalog(doc_id, catalog_name)

    def create_catalog(self, name: str, description: str = "",
                       parent: str = "") -> str:
        """Create a new catalog."""
        return self.catalog_manager.create_catalog(name, description, parent)

    def create_view(self, name: str, description: str = "",
                    query: str = "", filters: Dict = None,
                    sort_by: str = "ingested_at") -> View:
        """Create a saved view."""
        return self.catalog_manager.create_view(name, description, query, filters, sort_by)

    def create_journal(self, name: str, description: str = "") -> Journal:
        """Create a research journal."""
        return self.catalog_manager.create_journal(name, description)

    def journal_entry(self, journal_name: str, content: str,
                      entry_type: str = "note", **kwargs):
        """Add an entry to a journal."""
        entry = {'content': content, 'type': entry_type, **kwargs}
        return self.catalog_manager.add_journal_entry(journal_name, entry)

    # ── Relations ──────────────────────────────────────────────────────────

    def find_related(self, doc_id: str, top_k: int = 5) -> List[Relation]:
        """Find documents related to a given document."""
        return self.relation_miner.mine_relations(doc_id, top_k)

    def mine_all_relations(self) -> int:
        """Mine relations across all documents."""
        return self.relation_miner.mine_all_relations()

    # ── Notes ──────────────────────────────────────────────────────────────

    def get_note(self, note_id: str) -> Optional[InvestigationNote]:
        """Retrieve an investigation note."""
        return self.db.get_investigation_note(note_id)

    def list_notes(self, limit: int = 50) -> List[InvestigationNote]:
        """List recent investigation notes."""
        return self.db.list_investigation_notes(limit)

    def search_notes(self, query: str, limit: int = 10) -> List[InvestigationNote]:
        """Search investigation notes."""
        return self.db.search_investigation_notes(query, limit)

    # ── Documents ──────────────────────────────────────────────────────────

    def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        """Get document metadata."""
        return self.db.get_document(doc_id)

    def list_documents(self, catalog: str = "", folder: str = "",
                       tags: List[str] = None, limit: int = 100,
                       offset: int = 0) -> List[DocumentMetadata]:
        """List documents with optional filters."""
        return self.db.list_documents(catalog, folder, tags, limit, offset)

    def update_metadata(self, doc_id: str, **kwargs):
        """Update document metadata fields."""
        meta = self.db.get_document(doc_id)
        if not meta:
            raise ValueError(f"Document not found: {doc_id}")
        for key, value in kwargs.items():
            if hasattr(meta, key):
                setattr(meta, key, value)
        self.db.upsert_document(meta)

    # ── Stats & Info ───────────────────────────────────────────────────────

    def stats(self) -> Dict:
        """Get system statistics."""
        return self.db.get_stats()

    def list_catalogs(self) -> List[Dict]:
        """List all catalogs."""
        return self.db.list_catalogs()

    def list_tags(self) -> List[Dict]:
        """List all tags."""
        return self.db.list_tags()

    def list_views(self) -> List[View]:
        """List all saved views."""
        return self.db.list_views()

    def get_view(self, name: str) -> Optional[View]:
        """Get a saved view by name."""
        return self.db.get_view(name)

    def get_journal(self, name: str) -> Optional[Journal]:
        """Get a journal by name."""
        return self.db.get_journal(name)

    def export_note(self, note_id: str, format: str = "markdown") -> str:
        """Export an investigation note."""
        note = self.db.get_investigation_note(note_id)
        if not note:
            raise ValueError(f"Note not found: {note_id}")

        if format == "markdown":
            return self._note_to_markdown(note)
        elif format == "json":
            return json.dumps(note.to_dict(), indent=2)
        else:
            return note.answer

    def _note_to_markdown(self, note: InvestigationNote) -> str:
        lines = [
            f"# Research Note",
            f"",
            f"**Query:** {note.query}",
            f"**Date:** {note.created_at[:10]}",
            f"**Tags:** {', '.join(note.tags) if note.tags else 'none'}",
            f"",
            f"## Answer",
            f"",
            note.answer,
            f"",
        ]

        if note.citations:
            lines.append("## Sources")
            lines.append("")
            for i, cit in enumerate(note.citations, 1):
                lines.append(f"{i}. **{cit.title}**")
                lines.append(f"   - File: `{cit.file_path}`")
                if cit.page_number:
                    lines.append(f"   - Page: {cit.page_number}")
                if cit.line_start:
                    lines.append(f"   - Line: {cit.line_start}")
                if cit.quote:
                    lines.append(f"   - Quote: *\"{cit.quote[:100]}...\"*")
                lines.append("")

        if note.follow_up_questions:
            lines.append("## Follow-up Questions")
            lines.append("")
            for q in note.follow_up_questions:
                lines.append(f"- {q}")
            lines.append("")

        return '\n'.join(lines)

    def watch_directory(self, directory: str, interval: int = 60,
                        catalog: str = "", tags: List[str] = None):
        """Watch a directory for new/changed files and auto-ingest."""
        logger.info(f"Watching directory: {directory} (interval: {interval}s)")
        known_files = {}

        while True:
            try:
                p = Path(directory)
                for file_path in p.rglob('*'):
                    if file_path.is_file() and self.ingester.can_ingest(str(file_path)):
                        mtime = file_path.stat().st_mtime
                        if str(file_path) not in known_files or known_files[str(file_path)] != mtime:
                            try:
                                self.ingest(str(file_path), catalog=catalog, tags=tags)
                                known_files[str(file_path)] = mtime
                            except Exception as e:
                                logger.warning(f"Watch ingest failed for {file_path}: {e}")
            except Exception as e:
                logger.error(f"Watch error: {e}")

            time.sleep(interval)

    def interactive_session(self):
        """Start an interactive research session."""
        print("=" * 60)
        print("Marginalia - Personal Knowledge Management System")
        print("=" * 60)
        print(f"Knowledge base: {self.base_dir}")
        stats = self.stats()
        print(f"Documents: {stats['total_documents']} | Chunks: {stats['total_chunks']}")
        print(f"LLM: {self.llm_client.provider}/{self.llm_client.model}")
        print()
        print("Commands: ask, search, ingest, list, stats, note, report, quit")
        print()

        while True:
            try:
                user_input = input("marginalia> ").strip()
                if not user_input:
                    continue

                parts = user_input.split(None, 1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""

                if cmd in ('quit', 'exit', 'q'):
                    print("Goodbye!")
                    break

                elif cmd == 'ask':
                    if not args:
                        print("Usage: ask <question>")
                        continue
                    print(f"\nResearching: {args}")
                    print("-" * 40)
                    note = self.ask(args)
                    print(note.answer)
                    if note.citations:
                        print(f"\nSources ({len(note.citations)}):")
                        for cit in note.citations:
                            print(f"  - {cit.format()}: {cit.file_path}")
                    if note.follow_up_questions:
                        print("\nFollow-up questions:")
                        for q in note.follow_up_questions:
                            print(f"  - {q}")
                    print(f"\n[Note saved: {note.note_id}]")

                elif cmd == 'search':
                    if not args:
                        print("Usage: search <query>")
                        continue
                    results = self.search(args, limit=5)
                    print(f"\nFound {len(results)} results:")
                    for r in results:
                        print(f"  [{r.rank}] {r.title} (score: {r.score:.3f})")
                        if r.page_number:
                            print(f"      Page {r.page_number}", end="")
                        if r.line_start:
                            print(f" Lines {r.line_start}-{r.line_end}", end="")
                        print()
                        print(f"      {r.content[:100]}...")

                elif cmd == 'ingest':
                    if not args:
                        print("Usage: ingest <path>")
                        continue
                    docs = self.ingest(args)
                    print(f"Ingested {len(docs)} document(s)")
                    for d in docs:
                        print(f"  - {d.title} ({d.file_type}) -> {d.catalog}")

                elif cmd == 'list':
                    catalog_filter = args if args else ""
                    docs = self.list_documents(catalog=catalog_filter, limit=20)
                    print(f"\nDocuments ({len(docs)}):")
                    for d in docs:
                        print(f"  [{d.doc_id[:8]}] {d.title} | {d.catalog} | {', '.join(d.tags[:3])}")

                elif cmd == 'stats':
                    s = self.stats()
                    print(f"\nKnowledge Base Statistics:")
                    print(f"  Documents: {s['total_documents']}")
                    print(f"  Chunks: {s['total_chunks']}")
                    print(f"  Embeddings: {s['total_embeddings']}")
                    print(f"  Relations: {s['total_relations']}")
                    print(f"  Notes: {s['total_notes']}")

                elif cmd == 'note':
                    if args:
                        note = self.get_note(args)
                        if note:
                            print(self._note_to_markdown(note))
                        else:
                            print(f"Note not found: {args}")
                    else:
                        notes = self.list_notes(limit=10)
                        print(f"\nRecent notes ({len(notes)}):")
                        for n in notes:
                            print(f"  [{n.note_id[:8]}] {n.created_at[:10]} - {n.query[:60]}")

                elif cmd == 'report':
                    if not args:
                        print("Usage: report <topic>")
                        continue
                    print(f"\nGenerating report on: {args}")
                    print("-" * 40)
                    report = self.report(args)
                    print(report)

                elif cmd == 'help':
                    print("""
Commands:
  ask <question>     - Research a question with cited answer
  search <query>     - Search the knowledge base
  ingest <path>      - Ingest a file or directory
  list [catalog]     - List documents
  stats              - Show statistics
  note [id]          - Show note(s)
  report <topic>     - Generate research report
  quit               - Exit
""")
                else:
                    print(f"Unknown command: {cmd}. Type 'help' for commands.")

            except KeyboardInterrupt:
                print("\nInterrupted. Type 'quit' to exit.")
            except EOFError:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
                logger.exception(e)


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def create_marginalia(base_dir: str = "~/.marginalia",
                      llm_provider: str = "auto",
                      llm_model: str = None,
                      llm_api_key: str = None,
                      use_embeddings: bool = False,
                      chunk_size: int = 1000,
                      chunk_overlap: int = 200) -> Marginalia:
    """Factory function to create a Marginalia instance."""
    return Marginalia(
        base_dir=base_dir,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        use_embeddings=use_embeddings,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Marginalia - Personal Knowledge Management System"
    )
    parser.add_argument('--base-dir', default='~/.marginalia',
                        help='Base directory for knowledge base')
    parser.add_argument('--llm-provider', default='auto',
                        choices=['auto', 'anthropic', 'openai', 'mock'],
                        help='LLM provider')
    parser.add_argument('--llm-model', default=None, help='LLM model name')
    parser.add_argument('--llm-api-key', default=None, help='LLM API key')
    parser.add_argument('--embeddings', action='store_true',
                        help='Enable semantic embeddings')
    parser.add_argument('--chunk-size', type=int, default=1000,
                        help='Text chunk size')
    parser.add_argument('--chunk-overlap', type=int, default=200,
                        help='Chunk overlap size')

    subparsers = parser.add_subparsers(dest='command')

    # Interactive mode
    subparsers.add_parser('interactive', help='Start interactive session')

    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Ingest files')
    ingest_parser.add_argument('path', help='File or directory to ingest')
    ingest_parser.add_argument('--catalog', default='', help='Catalog name')
    ingest_parser.add_argument('--tags', nargs='+', default=[], help='Tags')
    ingest_parser.add_argument('--no-recursive', action='store_true')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search knowledge base')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=10)
    search_parser.add_argument('--mode', default='lexical',
                               choices=['lexical', 'semantic', 'hybrid'])
    search_parser.add_argument('--catalog', default='')
    search_parser.add_argument('--tags', nargs='+', default=[])

    # Ask command
    ask_parser = subparsers.add_parser('ask', help='Ask a research question')
    ask_parser.add_argument('question', help='Research question')
    ask_parser.add_argument('--mode', default='lexical',
                            choices=['lexical', 'semantic', 'hybrid'])
    ask_parser.add_argument('--limit', type=int, default=10)
    ask_parser.add_argument('--catalog', default='')
    ask_parser.add_argument('--no-save', action='store_true')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate research report')
    report_parser.add_argument('topic', help='Report topic')

    # List command
    list_parser = subparsers.add_parser('list', help='List documents')
    list_parser.add_argument('--catalog', default='')
    list_parser.add_argument('--tags', nargs='+', default=[])
    list_parser.add_argument('--limit', type=int, default=50)

    # Stats command
    subparsers.add_parser('stats', help='Show statistics')

    # Notes command
    notes_parser = subparsers.add_parser('notes', help='List/show notes')
    notes_parser.add_argument('note_id', nargs='?', default=None)
    notes_parser.add_argument('--limit', type=int, default=20)

    args = parser.parse_args()

    m = create_marginalia(
        base_dir=args.base_dir,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        llm_api_key=args.llm_api_key,
        use_embeddings=args.embeddings,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    if args.command == 'interactive' or args.command is None:
        m.interactive_session()

    elif args.command == 'ingest':
        docs = m.ingest(
            args.path,
            catalog=args.catalog,
            tags=args.tags,
            recursive=not args.no_recursive,
        )
        print(f"Ingested {len(docs)} document(s):")
        for d in docs:
            print(f"  [{d.doc_id[:8]}] {d.title} ({d.file_type}) -> catalog:{d.catalog}")

    elif args.command == 'search':
        results = m.search(
            args.query,
            limit=args.limit,
            mode=args.mode,
            catalog=args.catalog,
            tags=args.tags if args.tags else None,
        )
        print(f"Search results for '{args.query}' ({len(results)} found):\n")
        for r in results:
            print(f"[{r.rank}] {r.title} (score: {r.score:.3f})")
            print(f"    {r.file_path}")
            if r.page_number:
                print(f"    Page {r.page_number}", end="")
            if r.line_start:
                print(f" | Lines {r.line_start}-{r.line_end}", end="")
            print()
            print(f"    {r.content[:150]}...")
            print()

    elif args.command == 'ask':
        note = m.ask(
            args.question,
            search_mode=args.mode,
            search_limit=args.limit,
            catalog=args.catalog,
            save_note=not args.no_save,
        )
        print(f"\n{'='*60}")
        print(f"Query: {note.query}")
        print(f"{'='*60}\n")
        print(note.answer)
        if note.citations:
            print(f"\n{'─'*40}")
            print(f"Sources ({len(note.citations)}):")
            for cit in note.citations:
                print(f"  {cit.format()}")
                print(f"    {cit.file_path}")
        if note.follow_up_questions:
            print(f"\nFollow-up questions:")
            for q in note.follow_up_questions:
                print(f"  • {q}")
        if not args.no_save:
            print(f"\n[Note saved: {note.note_id}]")

    elif args.command == 'report':
        report = m.report(args.topic)
        print(report)

    elif args.command == 'list':
        docs = m.list_documents(
            catalog=args.catalog,
            tags=args.tags if args.tags else None,
            limit=args.limit,
        )
        print(f"Documents ({len(docs)}):\n")
        for d in docs:
            tags_str = ', '.join(d.tags[:5]) if d.tags else 'no tags'
            print(f"[{d.doc_id[:8]}] {d.title}")
            print(f"  Type: {d.file_type} | Catalog: {d.catalog or 'none'} | Tags: {tags_str}")
            print(f"  Path: {d.file_path}")
            print()

    elif args.command == 'stats':
        s = m.stats()
        print("Marginalia Knowledge Base Statistics")
        print("=" * 40)
        print(f"Documents:   {s['total_documents']}")
        print(f"Chunks:      {s['total_chunks']}")
        print(f"Embeddings:  {s['total_embeddings']}")
        print(f"Relations:   {s['total_relations']}")
        print(f"Notes:       {s['total_notes']}")
        print()
        if s.get('catalogs'):
            print("Catalogs:")
            for row in s['catalogs']:
                print(f"  {row[0] or '(none)'}: {row[1]} docs")

    elif args.command == 'notes':
        if args.note_id:
            note = m.get_note(args.note_id)
            if note:
                print(m.export_note(args.note_id, format='markdown'))
            else:
                print(f"Note not found: {args.note_id}")
        else:
            notes = m.list_notes(limit=args.limit)
            print(f"Investigation Notes ({len(notes)}):\n")
            for n in notes:
                print(f"[{n.note_id[:8]}] {n.created_at[:10]} - {n.query[:70]}")
                print(f"  Citations: {len(n.citations)} | Tags: {', '.join(n.tags[:3])}")
                print()


if __name__ == '__main__':
    main()