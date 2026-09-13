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


# ─────────────────────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DocumentRecord:
    """Represents a document in the knowledge base."""
    doc_id: str
    file_path: str
    title: str
    file_type: str
    size_bytes: int
    checksum: str
    created_at: str
    modified_at: str
    ingested_at: str
    catalog_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_count: int = 0
    language: str = "en"
    summary: Optional[str] = None


@dataclass
class Chunk:
    """A text chunk extracted from a document."""
    chunk_id: str
    doc_id: str
    content: str
    chunk_index: int
    start_offset: int
    end_offset: int
    page_number: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    section_title: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Catalog:
    """A collection/folder of related documents."""
    catalog_id: str
    name: str
    description: str
    parent_id: Optional[str]
    created_at: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Tag:
    """A tag for organizing documents."""
    tag_id: str
    name: str
    color: Optional[str] = None
    description: Optional[str] = None
    created_at: str = ""


@dataclass
class View:
    """A saved search/filter view."""
    view_id: str
    name: str
    query: str
    filters: Dict[str, Any]
    created_at: str
    description: Optional[str] = None


@dataclass
class JournalEntry:
    """A research journal entry."""
    entry_id: str
    title: str
    content: str
    created_at: str
    modified_at: str
    tags: List[str] = field(default_factory=list)
    related_docs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    """A relation between two documents."""
    relation_id: str
    source_doc_id: str
    target_doc_id: str
    relation_type: str
    confidence: float
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """A search result with relevance score."""
    chunk: Chunk
    doc: DocumentRecord
    score: float
    match_type: str  # 'lexical', 'semantic', 'hybrid'
    snippet: str = ""


@dataclass
class Citation:
    """A citation reference in an answer."""
    doc_id: str
    file_path: str
    title: str
    chunk_id: str
    page_number: Optional[int]
    line_start: Optional[int]
    line_end: Optional[int]
    section_title: Optional[str]
    snippet: str


@dataclass
class AgentAnswer:
    """An answer produced by the agent."""
    answer_id: str
    query: str
    answer: str
    citations: List[Citation]
    created_at: str
    model: str
    tokens_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InvestigationNote:
    """A durable investigation note for future recall."""
    note_id: str
    title: str
    query: str
    answer: str
    citations: List[Citation]
    created_at: str
    tags: List[str] = field(default_factory=list)
    follow_up_questions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Database Layer
# ─────────────────────────────────────────────────────────────────────────────

class Database:
    """SQLite database manager for Marginalia."""

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
        return self._local.conn

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS catalogs (
                catalog_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                parent_id TEXT,
                created_at TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                file_type TEXT NOT NULL,
                size_bytes INTEGER,
                checksum TEXT,
                created_at TEXT,
                modified_at TEXT,
                ingested_at TEXT NOT NULL,
                catalog_id TEXT,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                chunk_count INTEGER DEFAULT 0,
                language TEXT DEFAULT 'en',
                summary TEXT,
                FOREIGN KEY (catalog_id) REFERENCES catalogs(catalog_id)
            );

            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                start_offset INTEGER,
                end_offset INTEGER,
                page_number INTEGER,
                line_start INTEGER,
                line_end INTEGER,
                section_title TEXT,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                doc_id UNINDEXED,
                content,
                section_title,
                tokenize='porter unicode61'
            );

            CREATE TABLE IF NOT EXISTS tags (
                tag_id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                color TEXT,
                description TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS document_tags (
                doc_id TEXT NOT NULL,
                tag_id TEXT NOT NULL,
                PRIMARY KEY (doc_id, tag_id),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS views (
                view_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                query TEXT,
                filters TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                description TEXT
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                entry_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                related_docs TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS journal_fts USING fts5(
                entry_id UNINDEXED,
                title,
                content,
                tokenize='porter unicode61'
            );

            CREATE TABLE IF NOT EXISTS relations (
                relation_id TEXT PRIMARY KEY,
                source_doc_id TEXT NOT NULL,
                target_doc_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (source_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (target_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS investigation_notes (
                note_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                query TEXT NOT NULL,
                answer TEXT NOT NULL,
                citations TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                follow_up_questions TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                note_id UNINDEXED,
                title,
                query,
                answer,
                tokenize='porter unicode61'
            );

            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                embedding BLOB,
                model TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_documents_catalog ON documents(catalog_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
            CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_doc_id);
            CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_doc_id);
        """)
        conn.commit()
        conn.close()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def executemany(self, sql: str, params_list: list) -> sqlite3.Cursor:
        return self.conn.executemany(sql, params_list)

    def commit(self):
        self.conn.commit()

    def fetchall(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchone()


# ─────────────────────────────────────────────────────────────────────────────
# File Ingestion
# ─────────────────────────────────────────────────────────────────────────────

class TextExtractor:
    """Extracts text content from various file types."""

    def extract(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text and metadata from a file."""
        path = Path(file_path)
        ext = path.suffix.lower()
        metadata = {}

        try:
            if ext in ('.txt', '.md', '.rst', '.log', '.csv', '.tsv', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.xml', '.html', '.htm'):
                return self._extract_text(file_path, metadata)
            elif ext == '.pdf':
                return self._extract_pdf(file_path, metadata)
            elif ext in ('.docx', '.doc'):
                return self._extract_docx(file_path, metadata)
            elif ext in ('.xlsx', '.xls', '.ods'):
                return self._extract_spreadsheet(file_path, metadata)
            elif ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'):
                return self._extract_image(file_path, metadata)
            elif ext in ('.zip', '.tar', '.gz', '.bz2', '.tar.gz', '.tar.bz2', '.tgz'):
                return self._extract_archive(file_path, metadata)
            else:
                return self._extract_text(file_path, metadata)
        except Exception as e:
            logger.warning(f"Failed to extract {file_path}: {e}")
            return "", {"error": str(e)}

    def _extract_text(self, file_path: str, metadata: dict) -> Tuple[str, dict]:
        encodings = ['utf-8', 'latin-1', 'cp1252', 'ascii']
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    content = f.read()
                metadata['encoding'] = enc
                metadata['line_count'] = content.count('\n') + 1
                return content, metadata
            except (UnicodeDecodeError, UnicodeError):
                continue
        with open(file_path, 'rb') as f:
            content = f.read().decode('utf-8', errors='replace')
        metadata['encoding'] = 'utf-8-replace'
        return content, metadata

    def _extract_pdf(self, file_path: str, metadata: dict) -> Tuple[str, dict]:
        if not HAS_PYPDF:
            return f"[PDF file: {file_path} - pypdf not installed]", metadata
        pages = []
        try:
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                metadata['page_count'] = len(reader.pages)
                if reader.metadata:
                    for k, v in reader.metadata.items():
                        metadata[k.lstrip('/')] = str(v)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    pages.append(f"[Page {i+1}]\n{text}")
        except Exception as e:
            return f"[PDF extraction error: {e}]", metadata
        return "\n\n".join(pages), metadata

    def _extract_docx(self, file_path: str, metadata: dict) -> Tuple[str, dict]:
        if not HAS_DOCX:
            return f"[DOCX file: {file_path} - python-docx not installed]", metadata
        try:
            doc = docx.Document(file_path)
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            metadata['paragraph_count'] = len(paragraphs)
            core_props = doc.core_properties
            if core_props.author:
                metadata['author'] = core_props.author
            if core_props.title:
                metadata['title'] = core_props.title
            return "\n\n".join(paragraphs), metadata
        except Exception as e:
            return f"[DOCX extraction error: {e}]", metadata

    def _extract_spreadsheet(self, file_path: str, metadata: dict) -> Tuple[str, dict]:
        if not HAS_OPENPYXL:
            if HAS_CSV:
                return self._extract_text(file_path, metadata)
            return f"[Spreadsheet: {file_path} - openpyxl not installed]", metadata
        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheets_text = []
            metadata['sheet_names'] = wb.sheetnames
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = []
                for row in ws.iter_rows(values_only=True):
                    row_text = "\t".join(str(cell) if cell is not None else "" for cell in row)
                    if row_text.strip():
                        rows.append(row_text)
                sheets_text.append(f"[Sheet: {sheet_name}]\n" + "\n".join(rows))
            return "\n\n".join(sheets_text), metadata
        except Exception as e:
            return f"[Spreadsheet extraction error: {e}]", metadata

    def _extract_image(self, file_path: str, metadata: dict) -> Tuple[str, dict]:
        if not HAS_PIL:
            return f"[Image file: {file_path}]", metadata
        try:
            img = Image.open(file_path)
            metadata['image_size'] = f"{img.width}x{img.height}"
            metadata['image_mode'] = img.mode
            metadata['image_format'] = img.format
            if hasattr(img, '_getexif') and img._getexif():
                exif = img._getexif()
                if exif:
                    metadata['has_exif'] = True
            return f"[Image: {Path(file_path).name}, {img.width}x{img.height}, {img.mode}]", metadata
        except Exception as e:
            return f"[Image extraction error: {e}]", metadata

    def _extract_archive(self, file_path: str, metadata: dict) -> Tuple[str, dict]:
        members_text = []
        try:
            if zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, 'r') as zf:
                    members = zf.namelist()
                    metadata['archive_members'] = members
                    metadata['member_count'] = len(members)
                    for name in members[:20]:
                        info = zf.getinfo(name)
                        members_text.append(f"[Member: {name}, size: {info.file_size}]")
                        if not name.endswith('/') and info.file_size < 1_000_000:
                            try:
                                content = zf.read(name).decode('utf-8', errors='replace')
                                members_text.append(content[:2000])
                            except Exception:
                                pass
            elif tarfile.is_tarfile(file_path):
                with tarfile.open(file_path, 'r:*') as tf:
                    members = tf.getnames()
                    metadata['archive_members'] = members
                    metadata['member_count'] = len(members)
                    for name in members[:20]:
                        members_text.append(f"[Member: {name}]")
        except Exception as e:
            return f"[Archive extraction error: {e}]", metadata
        return "\n".join(members_text), metadata


class ChunkingStrategy:
    """Splits document text into chunks for indexing."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, doc_id: str, file_type: str = "txt") -> List[Chunk]:
        """Split text into overlapping chunks."""
        if not text.strip():
            return []

        if file_type == 'pdf':
            return self._chunk_by_pages(text, doc_id)
        elif file_type in ('md', 'rst'):
            return self._chunk_by_sections(text, doc_id)
        else:
            return self._chunk_by_size(text, doc_id)

    def _chunk_by_size(self, text: str, doc_id: str) -> List[Chunk]:
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_size = 0
        chunk_index = 0
        start_line = 0
        current_line = 0

        for line in lines:
            line_size = len(line) + 1
            if current_size + line_size > self.chunk_size and current_chunk:
                content = '\n'.join(current_chunk)
                chunk_id = str(uuid.uuid4())
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    content=content,
                    chunk_index=chunk_index,
                    start_offset=0,
                    end_offset=len(content),
                    line_start=start_line,
                    line_end=current_line - 1
                ))
                chunk_index += 1
                # Overlap: keep last few lines
                overlap_lines = current_chunk[-3:] if len(current_chunk) > 3 else current_chunk
                current_chunk = overlap_lines[:]
                current_size = sum(len(l) + 1 for l in current_chunk)
                start_line = current_line - len(overlap_lines)

            current_chunk.append(line)
            current_size += line_size
            current_line += 1

        if current_chunk:
            content = '\n'.join(current_chunk)
            chunk_id = str(uuid.uuid4())
            chunks.append(Chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                content=content,
                chunk_index=chunk_index,
                start_offset=0,
                end_offset=len(content),
                line_start=start_line,
                line_end=current_line - 1
            ))

        return chunks

    def _chunk_by_pages(self, text: str, doc_id: str) -> List[Chunk]:
        chunks = []
        page_pattern = re.compile(r'\[Page (\d+)\]')
        pages = page_pattern.split(text)
        chunk_index = 0

        i = 0
        while i < len(pages):
            if page_pattern.match(f'[Page {pages[i]}]') or (i > 0 and pages[i-1].isdigit()):
                i += 1
                continue
            if i + 1 < len(pages) and pages[i+1].isdigit() if i < len(pages)-1 else False:
                page_num = int(pages[i+1]) if i+1 < len(pages) else None
                content = pages[i+2] if i+2 < len(pages) else pages[i]
                i += 3
            else:
                content = pages[i]
                page_num = None
                i += 1

            if not content.strip():
                continue

            sub_chunks = self._chunk_by_size(content, doc_id)
            for sc in sub_chunks:
                sc.chunk_index = chunk_index
                sc.page_number = page_num
                chunks.append(sc)
                chunk_index += 1

        if not chunks:
            return self._chunk_by_size(text, doc_id)
        return chunks

    def _chunk_by_sections(self, text: str, doc_id: str) -> List[Chunk]:
        chunks = []
        section_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        sections = section_pattern.split(text)
        chunk_index = 0
        current_section = None

        lines = text.split('\n')
        current_section_lines = []
        current_section_title = None

        for line in lines:
            m = re.match(r'^(#{1,6})\s+(.+)$', line)
            if m:
                if current_section_lines:
                    content = '\n'.join(current_section_lines)
                    if content.strip():
                        sub_chunks = self._chunk_by_size(content, doc_id)
                        for sc in sub_chunks:
                            sc.chunk_index = chunk_index
                            sc.section_title = current_section_title
                            chunks.append(sc)
                            chunk_index += 1
                current_section_title = m.group(2)
                current_section_lines = [line]
            else:
                current_section_lines.append(line)

        if current_section_lines:
            content = '\n'.join(current_section_lines)
            if content.strip():
                sub_chunks = self._chunk_by_size(content, doc_id)
                for sc in sub_chunks:
                    sc.chunk_index = chunk_index
                    sc.section_title = current_section_title
                    chunks.append(sc)
                    chunk_index += 1

        if not chunks:
            return self._chunk_by_size(text, doc_id)
        return chunks


class Ingester:
    """Ingests files into the knowledge base."""

    def __init__(self, db: 'Database', vault_path: str, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.db = db
        self.vault_path = Path(vault_path)
        self.extractor = TextExtractor()
        self.chunker = ChunkingStrategy(chunk_size, chunk_overlap)

    def ingest_file(self, file_path: str, catalog_id: Optional[str] = None, tags: Optional[List[str]] = None) -> Optional[DocumentRecord]:
        """Ingest a single file."""
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        checksum = self._compute_checksum(file_path)
        existing = self.db.fetchone("SELECT doc_id, checksum FROM documents WHERE file_path = ?", (str(path),))
        if existing and existing['checksum'] == checksum:
            logger.info(f"File unchanged, skipping: {file_path}")
            return self._load_document(existing['doc_id'])

        stat = path.stat()
        file_type = path.suffix.lstrip('.').lower() or 'txt'
        title = path.stem
        now = datetime.datetime.utcnow().isoformat()

        doc_id = existing['doc_id'] if existing else str(uuid.uuid4())

        text, file_metadata = self.extractor.extract(file_path)

        if existing:
            self.db.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
            self.db.execute("DELETE FROM chunks_fts WHERE doc_id = ?", (doc_id,))

        chunks = self.chunker.chunk_text(text, doc_id, file_type)

        doc = DocumentRecord(
            doc_id=doc_id,
            file_path=str(path),
            title=title,
            file_type=file_type,
            size_bytes=stat.st_size,
            checksum=checksum,
            created_at=datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified_at=datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            ingested_at=now,
            catalog_id=catalog_id,
            tags=tags or [],
            metadata=file_metadata,
            chunk_count=len(chunks),
            language="en"
        )

        if existing:
            self.db.execute("""
                UPDATE documents SET title=?, file_type=?, size_bytes=?, checksum=?,
                modified_at=?, ingested_at=?, catalog_id=?, tags=?, metadata=?,
                chunk_count=?, language=?, summary=?
                WHERE doc_id=?
            """, (doc.title, doc.file_type, doc.size_bytes, doc.checksum,
                  doc.modified_at, doc.ingested_at, doc.catalog_id,
                  json.dumps(doc.tags), json.dumps(doc.metadata),
                  doc.chunk_count, doc.language, doc.summary, doc_id))
        else:
            self.db.execute("""
                INSERT INTO documents (doc_id, file_path, title, file_type, size_bytes, checksum,
                created_at, modified_at, ingested_at, catalog_id, tags, metadata, chunk_count, language, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (doc.doc_id, doc.file_path, doc.title, doc.file_type, doc.size_bytes,
                  doc.checksum, doc.created_at, doc.modified_at, doc.ingested_at,
                  doc.catalog_id, json.dumps(doc.tags), json.dumps(doc.metadata),
                  doc.chunk_count, doc.language, doc.summary))

        for chunk in chunks:
            self.db.execute("""
                INSERT INTO chunks (chunk_id, doc_id, content, chunk_index, start_offset, end_offset,
                page_number, line_start, line_end, section_title, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (chunk.chunk_id, chunk.doc_id, chunk.content, chunk.chunk_index,
                  chunk.start_offset, chunk.end_offset, chunk.page_number,
                  chunk.line_start, chunk.line_end, chunk.section_title,
                  json.dumps(chunk.metadata)))

            self.db.execute("""
                INSERT INTO chunks_fts (chunk_id, doc_id, content, section_title)
                VALUES (?, ?, ?, ?)
            """, (chunk.chunk_id, chunk.doc_id, chunk.content, chunk.section_title or ""))

        if tags:
            for tag_name in tags:
                tag = self._ensure_tag(tag_name)
                try:
                    self.db.execute("INSERT OR IGNORE INTO document_tags (doc_id, tag_id) VALUES (?, ?)",
                                    (doc_id, tag.tag_id))
                except Exception:
                    pass

        self.db.commit()
        logger.info(f"Ingested: {file_path} ({len(chunks)} chunks)")
        return doc

    def ingest_directory(self, dir_path: str, catalog_id: Optional[str] = None,
                         recursive: bool = True, pattern: str = "*") -> List[DocumentRecord]:
        """Ingest all matching files in a directory."""
        path = Path(dir_path)
        if not path.exists():
            logger.error(f"Directory not found: {dir_path}")
            return []

        docs = []
        glob_fn = path.rglob if recursive else path.glob
        for file_path in glob_fn(pattern):
            if file_path.is_file() and not file_path.name.startswith('.'):
                doc = self.ingest_file(str(file_path), catalog_id=catalog_id)
                if doc:
                    docs.append(doc)
        return docs

    def _compute_checksum(self, file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(65536), b''):
                h.update(block)
        return h.hexdigest()

    def _ensure_tag(self, name: str) -> Tag:
        row = self.db.fetchone("SELECT * FROM tags WHERE name = ?", (name,))
        if row:
            return Tag(tag_id=row['tag_id'], name=row['name'], color=row['color'],
                       description=row['description'], created_at=row['created_at'])
        tag = Tag(
            tag_id=str(uuid.uuid4()),
            name=name,
            created_at=datetime.datetime.utcnow().isoformat()
        )
        self.db.execute("INSERT INTO tags (tag_id, name, created_at) VALUES (?, ?, ?)",
                        (tag.tag_id, tag.name, tag.created_at))
        return tag

    def _load_document(self, doc_id: str) -> Optional[DocumentRecord]:
        row = self.db.fetchone("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        if not row:
            return None
        return DocumentRecord(
            doc_id=row['doc_id'],
            file_path=row['file_path'],
            title=row['title'],
            file_type=row['file_type'],
            size_bytes=row['size_bytes'],
            checksum=row['checksum'],
            created_at=row['created_at'],
            modified_at=row['modified_at'],
            ingested_at=row['ingested_at'],
            catalog_id=row['catalog_id'],
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}'),
            chunk_count=row['chunk_count'],
            language=row['language'],
            summary=row['summary']
        )


# ─────────────────────────────────────────────────────────────────────────────
# Search Engine
# ─────────────────────────────────────────────────────────────────────────────

class LexicalSearchEngine:
    """BM25-style lexical search using SQLite FTS5."""

    def __init__(self, db: Database):
        self.db = db

    def search(self, query: str, limit: int = 20, doc_ids: Optional[List[str]] = None,
               catalog_id: Optional[str] = None, tags: Optional[List[str]] = None) -> List[SearchResult]:
        """Perform lexical search."""
        fts_query = self._build_fts_query(query)

        sql = """
            SELECT c.chunk_id, c.doc_id, c.content, c.chunk_index, c.start_offset, c.end_offset,
                   c.page_number, c.line_start, c.line_end, c.section_title, c.metadata,
                   d.file_path, d.title, d.file_type, d.size_bytes, d.checksum,
                   d.created_at, d.modified_at, d.ingested_at, d.catalog_id,
                   d.tags, d.metadata as doc_metadata, d.chunk_count, d.language, d.summary,
                   bm25(chunks_fts) as score
            FROM chunks_fts
            JOIN chunks c ON chunks_fts.chunk_id = c.chunk_id
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE chunks_fts MATCH ?
        """
        params = [fts_query]

        if doc_ids:
            placeholders = ','.join('?' * len(doc_ids))
            sql += f" AND c.doc_id IN ({placeholders})"
            params.extend(doc_ids)

        if catalog_id:
            sql += " AND d.catalog_id = ?"
            params.append(catalog_id)

        if tags:
            for tag in tags:
                sql += """ AND c.doc_id IN (
                    SELECT dt.doc_id FROM document_tags dt
                    JOIN tags t ON dt.tag_id = t.tag_id
                    WHERE t.name = ?
                )"""
                params.append(tag)

        sql += " ORDER BY score LIMIT ?"
        params.append(limit)

        try:
            rows = self.db.fetchall(sql, tuple(params))
        except sqlite3.OperationalError as e:
            logger.warning(f"FTS search error: {e}")
            return []

        results = []
        for row in rows:
            chunk = Chunk(
                chunk_id=row['chunk_id'],
                doc_id=row['doc_id'],
                content=row['content'],
                chunk_index=row['chunk_index'],
                start_offset=row['start_offset'] or 0,
                end_offset=row['end_offset'] or 0,
                page_number=row['page_number'],
                line_start=row['line_start'],
                line_end=row['line_end'],
                section_title=row['section_title'],
                metadata=json.loads(row['metadata'] or '{}')
            )
            doc = DocumentRecord(
                doc_id=row['doc_id'],
                file_path=row['file_path'],
                title=row['title'],
                file_type=row['file_type'],
                size_bytes=row['size_bytes'],
                checksum=row['checksum'],
                created_at=row['created_at'],
                modified_at=row['modified_at'],
                ingested_at=row['ingested_at'],
                catalog_id=row['catalog_id'],
                tags=json.loads(row['tags'] or '[]'),
                metadata=json.loads(row['doc_metadata'] or '{}'),
                chunk_count=row['chunk_count'],
                language=row['language'],
                summary=row['summary']
            )
            score = abs(row['score']) if row['score'] else 0.0
            snippet = self._make_snippet(chunk.content, query)
            results.append(SearchResult(chunk=chunk, doc=doc, score=score,
                                        match_type='lexical', snippet=snippet))

        return results

    def _build_fts_query(self, query: str) -> str:
        """Build FTS5 query from natural language query."""
        words = re.findall(r'\w+', query.lower())
        if not words:
            return '""'
        # Try phrase first, fall back to individual terms
        terms = []
        for word in words:
            if len(word) > 2:
                terms.append(word)
        if not terms:
            terms = words
        return ' OR '.join(terms)

    def _make_snippet(self, content: str, query: str, max_len: int = 200) -> str:
        """Extract a relevant snippet from content."""
        words = re.findall(r'\w+', query.lower())
        content_lower = content.lower()
        best_pos = 0
        best_score = 0
        for word in words:
            pos = content_lower.find(word)
            if pos >= 0:
                score = len(word)
                if score > best_score:
                    best_score = score
                    best_pos = pos

        start = max(0, best_pos - 50)
        end = min(len(content), start + max_len)
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        return snippet


class EmbeddingEngine:
    """Manages document embeddings for semantic search."""

    def __init__(self, db: Database, model: str = "text-embedding-3-small"):
        self.db = db
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None and HAS_OPENAI:
            self._client = openai.OpenAI()
        return self._client

    def embed_text(self, text: str) -> Optional[List[float]]:
        """Get embedding for text."""
        client = self._get_client()
        if client is None:
            return None
        try:
            response = client.embeddings.create(input=text[:8000], model=self.model)
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Embedding error: {e}")
            return None

    def embed_chunk(self, chunk: Chunk) -> bool:
        """Embed a chunk and store it."""
        embedding = self.embed_text(chunk.content)
        if embedding is None:
            return False

        if HAS_NUMPY:
            blob = np.array(embedding, dtype=np.float32).tobytes()
        else:
            import struct
            blob = struct.pack(f'{len(embedding)}f', *embedding)

        now = datetime.datetime.utcnow().isoformat()
        self.db.execute("""
            INSERT OR REPLACE INTO embeddings (chunk_id, doc_id, embedding, model, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (chunk.chunk_id, chunk.doc_id, blob, self.model, now))
        return True

    def semantic_search(self, query: str, limit: int = 20) -> List[Tuple[str, float]]:
        """Search by semantic similarity. Returns (chunk_id, score) pairs."""
        query_embedding = self.embed_text(query)
        if query_embedding is None:
            return []

        rows = self.db.fetchall("SELECT chunk_id, embedding FROM embeddings WHERE embedding IS NOT NULL")
        if not rows:
            return []

        if HAS_NUMPY:
            q_vec = np.array(query_embedding, dtype=np.float32)
            q_norm = np.linalg.norm(q_vec)
            if q_norm == 0:
                return []
            q_vec = q_vec / q_norm

            scores = []
            for row in rows:
                try:
                    import struct
                    n = len(row['embedding']) // 4
                    vec = np.frombuffer(row['embedding'], dtype=np.float32)
                    norm = np.linalg.norm(vec)
                    if norm > 0:
                        sim = float(np.dot(q_vec, vec / norm))
                        scores.append((row['chunk_id'], sim))
                except Exception:
                    continue

            scores.sort(key=lambda x: x[1], reverse=True)
            return scores[:limit]
        return []


class Reranker:
    """Reranks search results using cross-encoder or LLM scoring."""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def rerank(self, query: str, results: List[SearchResult], top_k: int = 10) -> List[SearchResult]:
        """Rerank results by relevance to query."""
        if not results:
            return results

        # Simple TF-IDF-like reranking without external model
        query_terms = set(re.findall(r'\w+', query.lower()))
        scored = []
        for result in results:
            content_terms = re.findall(r'\w+', result.chunk.content.lower())
            content_freq = Counter(content_terms)
            tf_score = sum(content_freq.get(term, 0) for term in query_terms)
            idf_boost = len(query_terms & set(content_terms)) / max(len(query_terms), 1)
            combined = result.score * 0.7 + tf_score * 0.2 + idf_boost * 0.1
            scored.append((result, combined))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [r for r, _ in scored[:top_k]]


class SearchEngine:
    """Unified search engine combining lexical and semantic search."""

    def __init__(self, db: Database, use_embeddings: bool = False,
                 use_reranking: bool = False, source_quota: int = 5):
        self.db = db
        self.lexical = LexicalSearchEngine(db)
        self.embedding_engine = EmbeddingEngine(db) if use_embeddings else None
        self.reranker = Reranker() if use_reranking else None
        self.source_quota = source_quota
        self.use_embeddings = use_embeddings
        self.use_reranking = use_reranking

    def search(self, query: str, limit: int = 20, mode: str = 'lexical',
               doc_ids: Optional[List[str]] = None, catalog_id: Optional[str] = None,
               tags: Optional[List[str]] = None) -> List[SearchResult]:
        """Search the knowledge base."""
        results = []

        if mode in ('lexical', 'hybrid'):
            lex_results = self.lexical.search(query, limit=limit, doc_ids=doc_ids,
                                               catalog_id=catalog_id, tags=tags)
            results.extend(lex_results)

        if mode in ('semantic', 'hybrid') and self.embedding_engine:
            sem_pairs = self.embedding_engine.semantic_search(query, limit=limit)
            chunk_ids = [p[0] for p in sem_pairs]
            score_map = {p[0]: p[1] for p in sem_pairs}

            if chunk_ids:
                placeholders = ','.join('?' * len(chunk_ids))
                rows = self.db.fetchall(f"""
                    SELECT c.*, d.file_path, d.title, d.file_type, d.size_bytes, d.checksum,
                           d.created_at, d.modified_at, d.ingested_at, d.catalog_id,
                           d.tags, d.metadata as doc_metadata, d.chunk_count, d.language, d.summary
                    FROM chunks c JOIN documents d ON c.doc_id = d.doc_id
                    WHERE c.chunk_id IN ({placeholders})
                """, tuple(chunk_ids))

                for row in rows:
                    chunk = Chunk(
                        chunk_id=row['chunk_id'], doc_id=row['doc_id'],
                        content=row['content'], chunk_index=row['chunk_index'],
                        start_offset=row['start_offset'] or 0, end_offset=row['end_offset'] or 0,
                        page_number=row['page_number'], line_start=row['line_start'],
                        line_end=row['line_end'], section_title=row['section_title'],
                        metadata=json.loads(row['metadata'] or '{}')
                    )
                    doc = DocumentRecord(
                        doc_id=row['doc_id'], file_path=row['file_path'],
                        title=row['title'], file_type=row['file_type'],
                        size_bytes=row['size_bytes'], checksum=row['checksum'],
                        created_at=row['created_at'], modified_at=row['modified_at'],
                        ingested_at=row['ingested_at'], catalog_id=row['catalog_id'],
                        tags=json.loads(row['tags'] or '[]'),
                        metadata=json.loads(row['doc_metadata'] or '{}'),
                        chunk_count=row['chunk_count'], language=row['language'],
                        summary=row['summary']
                    )
                    score = score_map.get(row['chunk_id'], 0.0)
                    snippet = self.lexical._make_snippet(chunk.content, query)
                    results.append(SearchResult(chunk=chunk, doc=doc, score=score,
                                                match_type='semantic', snippet=snippet))

        # Deduplicate by chunk_id
        seen = set()
        unique_results = []
        for r in results:
            if r.chunk.chunk_id not in seen:
                seen.add(r.chunk.chunk_id)
                unique_results.append(r)

        # Apply source quota
        if self.source_quota > 0:
            unique_results = self._apply_source_quota(unique_results)

        if self.reranker and unique_results:
            unique_results = self.reranker.rerank(query, unique_results, top_k=limit)

        return unique_results[:limit]

    def _apply_source_quota(self, results: List[SearchResult]) -> List[SearchResult]:
        """Limit results per source document."""
        doc_counts = defaultdict(int)
        filtered = []
        for r in results:
            if doc_counts[r.doc.doc_id] < self.source_quota:
                filtered.append(r)
                doc_counts[r.doc.doc_id] += 1
        return filtered

    def search_notes(self, query: str, limit: int = 10) -> List[InvestigationNote]:
        """Search investigation notes."""
        fts_query = self.lexical._build_fts_query(query)
        try:
            rows = self.db.fetchall("""
                SELECT n.* FROM notes_fts
                JOIN investigation_notes n ON notes_fts.note_id = n.note_id
                WHERE notes_fts MATCH ?
                ORDER BY bm25(notes_fts) LIMIT ?
            """, (fts_query, limit))
        except sqlite3.OperationalError:
            rows = self.db.fetchall("SELECT * FROM investigation_notes LIMIT ?", (limit,))

        notes = []
        for row in rows:
            notes.append(InvestigationNote(
                note_id=row['note_id'],
                title=row['title'],
                query=row['query'],
                answer=row['answer'],
                citations=json.loads(row['citations'] or '[]'),
                created_at=row['created_at'],
                tags=json.loads(row['tags'] or '[]'),
                follow_up_questions=json.loads(row['follow_up_questions'] or '[]'),
                metadata=json.loads(row['metadata'] or '{}')
            ))
        return notes


# ─────────────────────────────────────────────────────────────────────────────
# Catalog & Organization
# ─────────────────────────────────────────────────────────────────────────────

class CatalogManager:
    """Manages catalogs (collections) of documents."""

    def __init__(self, db: Database):
        self.db = db

    def create_catalog(self, name: str, description: str = "",
                       parent_id: Optional[str] = None,
                       tags: Optional[List[str]] = None) -> Catalog:
        catalog = Catalog(
            catalog_id=str(uuid.uuid4()),
            name=name,
            description=description,
            parent_id=parent_id,
            created_at=datetime.datetime.utcnow().isoformat(),
            tags=tags or []
        )
        self.db.execute("""
            INSERT INTO catalogs (catalog_id, name, description, parent_id, created_at, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (catalog.catalog_id, catalog.name, catalog.description, catalog.parent_id,
              catalog.created_at, json.dumps(catalog.tags), json.dumps(catalog.metadata)))
        self.db.commit()
        return catalog

    def get_catalog(self, catalog_id: str) -> Optional[Catalog]:
        row = self.db.fetchone("SELECT * FROM catalogs WHERE catalog_id = ?", (catalog_id,))
        if not row:
            return None
        return Catalog(
            catalog_id=row['catalog_id'], name=row['name'],
            description=row['description'], parent_id=row['parent_id'],
            created_at=row['created_at'], tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}')
        )

    def list_catalogs(self, parent_id: Optional[str] = None) -> List[Catalog]:
        if parent_id is None:
            rows = self.db.fetchall("SELECT * FROM catalogs ORDER BY name")
        else:
            rows = self.db.fetchall("SELECT * FROM catalogs WHERE parent_id = ? ORDER BY name", (parent_id,))
        return [Catalog(
            catalog_id=r['catalog_id'], name=r['name'],
            description=r['description'], parent_id=r['parent_id'],
            created_at=r['created_at'], tags=json.loads(r['tags'] or '[]'),
            metadata=json.loads(r['metadata'] or '{}')
        ) for r in rows]

    def delete_catalog(self, catalog_id: str) -> bool:
        self.db.execute("UPDATE documents SET catalog_id = NULL WHERE catalog_id = ?", (catalog_id,))
        self.db.execute("DELETE FROM catalogs WHERE catalog_id = ?", (catalog_id,))
        self.db.commit()
        return True

    def get_catalog_documents(self, catalog_id: str) -> List[DocumentRecord]:
        rows = self.db.fetchall("SELECT * FROM documents WHERE catalog_id = ?", (catalog_id,))
        return [self._row_to_doc(r) for r in rows]

    def _row_to_doc(self, row) -> DocumentRecord:
        return DocumentRecord(
            doc_id=row['doc_id'], file_path=row['file_path'],
            title=row['title'], file_type=row['file_type'],
            size_bytes=row['size_bytes'], checksum=row['checksum'],
            created_at=row['created_at'], modified_at=row['modified_at'],
            ingested_at=row['ingested_at'], catalog_id=row['catalog_id'],
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}'),
            chunk_count=row['chunk_count'], language=row['language'],
            summary=row['summary']
        )


class TagManager:
    """Manages tags for documents."""

    def __init__(self, db: Database):
        self.db = db

    def create_tag(self, name: str, color: Optional[str] = None,
                   description: Optional[str] = None) -> Tag:
        existing = self.db.fetchone("SELECT * FROM tags WHERE name = ?", (name,))
        if existing:
            return Tag(tag_id=existing['tag_id'], name=existing['name'],
                       color=existing['color'], description=existing['description'],
                       created_at=existing['created_at'])
        tag = Tag(
            tag_id=str(uuid.uuid4()), name=name, color=color,
            description=description, created_at=datetime.datetime.utcnow().isoformat()
        )
        self.db.execute("INSERT INTO tags (tag_id, name, color, description, created_at) VALUES (?, ?, ?, ?, ?)",
                        (tag.tag_id, tag.name, tag.color, tag.description, tag.created_at))
        self.db.commit()
        return tag

    def list_tags(self) -> List[Tag]:
        rows = self.db.fetchall("SELECT * FROM tags ORDER BY name")
        return [Tag(tag_id=r['tag_id'], name=r['name'], color=r['color'],
                    description=r['description'], created_at=r['created_at']) for r in rows]

    def tag_document(self, doc_id: str, tag_name: str) -> bool:
        tag = self.create_tag(tag_name)
        try:
            self.db.execute("INSERT OR IGNORE INTO document_tags (doc_id, tag_id) VALUES (?, ?)",
                            (doc_id, tag.tag_id))
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Tag error: {e}")
            return False

    def untag_document(self, doc_id: str, tag_name: str) -> bool:
        row = self.db.fetchone("SELECT tag_id FROM tags WHERE name = ?", (tag_name,))
        if not row:
            return False
        self.db.execute("DELETE FROM document_tags WHERE doc_id = ? AND tag_id = ?",
                        (doc_id, row['tag_id']))
        self.db.commit()
        return True

    def get_documents_by_tag(self, tag_name: str) -> List[str]:
        rows = self.db.fetchall("""
            SELECT dt.doc_id FROM document_tags dt
            JOIN tags t ON dt.tag_id = t.tag_id
            WHERE t.name = ?
        """, (tag_name,))
        return [r['doc_id'] for r in rows]


class ViewManager:
    """Manages saved search views."""

    def __init__(self, db: Database):
        self.db = db

    def create_view(self, name: str, query: str, filters: Optional[Dict] = None,
                    description: Optional[str] = None) -> View:
        view = View(
            view_id=str(uuid.uuid4()), name=name, query=query,
            filters=filters or {}, created_at=datetime.datetime.utcnow().isoformat(),
            description=description
        )
        self.db.execute("""
            INSERT INTO views (view_id, name, query, filters, created_at, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (view.view_id, view.name, view.query, json.dumps(view.filters),
              view.created_at, view.description))
        self.db.commit()
        return view

    def list_views(self) -> List[View]:
        rows = self.db.fetchall("SELECT * FROM views ORDER BY name")
        return [View(view_id=r['view_id'], name=r['name'], query=r['query'],
                     filters=json.loads(r['filters'] or '{}'),
                     created_at=r['created_at'], description=r['description']) for r in rows]

    def get_view(self, view_id: str) -> Optional[View]:
        row = self.db.fetchone("SELECT * FROM views WHERE view_id = ?", (view_id,))
        if not row:
            return None
        return View(view_id=row['view_id'], name=row['name'], query=row['query'],
                    filters=json.loads(row['filters'] or '{}'),
                    created_at=row['created_at'], description=row['description'])

    def delete_view(self, view_id: str) -> bool:
        self.db.execute("DELETE FROM views WHERE view_id = ?", (view_id,))
        self.db.commit()
        return True


class JournalManager:
    """Manages research journal entries."""

    def __init__(self, db: Database):
        self.db = db

    def create_entry(self, title: str, content: str, tags: Optional[List[str]] = None,
                     related_docs: Optional[List[str]] = None) -> JournalEntry:
        now = datetime.datetime.utcnow().isoformat()
        entry = JournalEntry(
            entry_id=str(uuid.uuid4()), title=title, content=content,
            created_at=now, modified_at=now,
            tags=tags or [], related_docs=related_docs or []
        )
        self.db.execute("""
            INSERT INTO journal_entries (entry_id, title, content, created_at, modified_at, tags, related_docs, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (entry.entry_id, entry.title, entry.content, entry.created_at,
              entry.modified_at, json.dumps(entry.tags), json.dumps(entry.related_docs),
              json.dumps(entry.metadata)))
        self.db.execute("""
            INSERT INTO journal_fts (entry_id, title, content) VALUES (?, ?, ?)
        """, (entry.entry_id, entry.title, entry.content))
        self.db.commit()
        return entry

    def update_entry(self, entry_id: str, title: Optional[str] = None,
                     content: Optional[str] = None) -> Optional[JournalEntry]:
        entry = self.get_entry(entry_id)
        if not entry:
            return None
        if title:
            entry.title = title
        if content:
            entry.content = content
        entry.modified_at = datetime.datetime.utcnow().isoformat()
        self.db.execute("""
            UPDATE journal_entries SET title=?, content=?, modified_at=? WHERE entry_id=?
        """, (entry.title, entry.content, entry.modified_at, entry_id))
        self.db.execute("DELETE FROM journal_fts WHERE entry_id = ?", (entry_id,))
        self.db.execute("INSERT INTO journal_fts (entry_id, title, content) VALUES (?, ?, ?)",
                        (entry_id, entry.title, entry.content))
        self.db.commit()
        return entry

    def get_entry(self, entry_id: str) -> Optional[JournalEntry]:
        row = self.db.fetchone("SELECT * FROM journal_entries WHERE entry_id = ?", (entry_id,))
        if not row:
            return None
        return JournalEntry(
            entry_id=row['entry_id'], title=row['title'], content=row['content'],
            created_at=row['created_at'], modified_at=row['modified_at'],
            tags=json.loads(row['tags'] or '[]'),
            related_docs=json.loads(row['related_docs'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}')
        )

    def list_entries(self, limit: int = 50) -> List[JournalEntry]:
        rows = self.db.fetchall("SELECT * FROM journal_entries ORDER BY created_at DESC LIMIT ?", (limit,))
        return [JournalEntry(
            entry_id=r['entry_id'], title=r['title'], content=r['content'],
            created_at=r['created_at'], modified_at=r['modified_at'],
            tags=json.loads(r['tags'] or '[]'),
            related_docs=json.loads(r['related_docs'] or '[]'),
            metadata=json.loads(r['metadata'] or '{}')
        ) for r in rows]

    def search_entries(self, query: str, limit: int = 20) -> List[JournalEntry]:
        fts_query = ' OR '.join(re.findall(r'\w+', query.lower()))
        if not fts_query:
            return []
        try:
            rows = self.db.fetchall("""
                SELECT je.* FROM journal_fts
                JOIN journal_entries je ON journal_fts.entry_id = je.entry_id
                WHERE journal_fts MATCH ?
                ORDER BY bm25(journal_fts) LIMIT ?
            """, (fts_query, limit))
        except sqlite3.OperationalError:
            rows = self.db.fetchall("SELECT * FROM journal_entries LIMIT ?", (limit,))
        return [JournalEntry(
            entry_id=r['entry_id'], title=r['title'], content=r['content'],
            created_at=r['created_at'], modified_at=r['modified_at'],
            tags=json.loads(r['tags'] or '[]'),
            related_docs=json.loads(r['related_docs'] or '[]'),
            metadata=json.loads(r['metadata'] or '{}')
        ) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Relation Mining
# ─────────────────────────────────────────────────────────────────────────────

class RelationMiner:
    """Mines relations between documents."""

    def __init__(self, db: Database):
        self.db = db

    def mine_relations(self, doc_id: str, top_k: int = 5) -> List[Relation]:
        """Find related documents using term overlap."""
        doc_chunks = self.db.fetchall("SELECT content FROM chunks WHERE doc_id = ?", (doc_id,))
        if not doc_chunks:
            return []

        doc_text = ' '.join(r['content'] for r in doc_chunks)
        doc_terms = Counter(re.findall(r'\w+', doc_text.lower()))
        doc_terms_set = set(t for t, c in doc_terms.most_common(100) if len(t) > 3)

        other_docs = self.db.fetchall("""
            SELECT DISTINCT d.doc_id, d.title FROM documents d
            WHERE d.doc_id != ?
        """, (doc_id,))

        scores = []
        for other in other_docs:
            other_chunks = self.db.fetchall("SELECT content FROM chunks WHERE doc_id = ?", (other['doc_id'],))
            if not other_chunks:
                continue
            other_text = ' '.join(r['content'] for r in other_chunks)
            other_terms = set(re.findall(r'\w+', other_text.lower()))
            overlap = len(doc_terms_set & other_terms)
            if overlap > 0:
                jaccard = overlap / len(doc_terms_set | other_terms)
                scores.append((other['doc_id'], jaccard))

        scores.sort(key=lambda x: x[1], reverse=True)
        relations = []
        now = datetime.datetime.utcnow().isoformat()

        for other_doc_id, confidence in scores[:top_k]:
            if confidence < 0.01:
                continue
            existing = self.db.fetchone("""
                SELECT relation_id FROM relations
                WHERE source_doc_id = ? AND target_doc_id = ? AND relation_type = 'similar'
            """, (doc_id, other_doc_id))

            if existing:
                continue

            relation = Relation(
                relation_id=str(uuid.uuid4()),
                source_doc_id=doc_id,
                target_doc_id=other_doc_id,
                relation_type='similar',
                confidence=confidence,
                created_at=now
            )
            self.db.execute("""
                INSERT INTO relations (relation_id, source_doc_id, target_doc_id, relation_type, confidence, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (relation.relation_id, relation.source_doc_id, relation.target_doc_id,
                  relation.relation_type, relation.confidence, relation.created_at,
                  json.dumps(relation.metadata)))
            relations.append(relation)

        self.db.commit()
        return relations

    def add_relation(self, source_doc_id: str, target_doc_id: str,
                     relation_type: str, confidence: float = 1.0) -> Relation:
        relation = Relation(
            relation_id=str(uuid.uuid4()),
            source_doc_id=source_doc_id,
            target_doc_id=target_doc_id,
            relation_type=relation_type,
            confidence=confidence,
            created_at=datetime.datetime.utcnow().isoformat()
        )
        self.db.execute("""
            INSERT INTO relations (relation_id, source_doc_id, target_doc_id, relation_type, confidence, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (relation.relation_id, relation.source_doc_id, relation.target_doc_id,
              relation.relation_type, relation.confidence, relation.created_at,
              json.dumps(relation.metadata)))
        self.db.commit()
        return relation

    def get_relations(self, doc_id: str) -> List[Relation]:
        rows = self.db.fetchall("""
            SELECT * FROM relations WHERE source_doc_id = ? OR target_doc_id = ?
            ORDER BY confidence DESC
        """, (doc_id, doc_id))
        return [Relation(
            relation_id=r['relation_id'],
            source_doc_id=r['source_doc_id'],
            target_doc_id=r['target_doc_id'],
            relation_type=r['relation_type'],
            confidence=r['confidence'],
            created_at=r['created_at'],
            metadata=json.loads(r['metadata'] or '{}')
        ) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Document Reader (reads original file windows)
# ─────────────────────────────────────────────────────────────────────────────

class DocumentReader:
    """Reads specific sections/windows from original files."""

    def __init__(self):
        self.extractor = TextExtractor()

    def read_chunk_window(self, chunk: Chunk, doc: DocumentRecord,
                          context_lines: int = 5) -> str:
        """Read the original file window around a chunk."""
        file_path = doc.file_path
        if not Path(file_path).exists():
            return chunk.content

        file_type = doc.file_type

        if file_type == 'pdf':
            return self._read_pdf_page(file_path, chunk.page_number)
        elif file_type in ('zip', 'tar', 'gz', 'tgz'):
            return self._read_archive_member(file_path, chunk)
        elif file_type in ('xlsx', 'xls', 'ods'):
            return self._read_spreadsheet_slice(file_path, chunk)
        else:
            return self._read_text_lines(file_path, chunk, context_lines)

    def _read_text_lines(self, file_path: str, chunk: Chunk, context_lines: int = 5) -> str:
        """Read lines from a text file."""
        try:
            encodings = ['utf-8', 'latin-1', 'cp1252']
            content = None
            for enc in encodings:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        content = f.read()
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue

            if content is None:
                with open(file_path, 'rb') as f:
                    content = f.read().decode('utf-8', errors='replace')

            lines = content.split('\n')
            if chunk.line_start is not None and chunk.line_end is not None:
                start = max(0, chunk.line_start - context_lines)
                end = min(len(lines), chunk.line_end + context_lines + 1)
                window = lines[start:end]
                return '\n'.join(window)
            else:
                return chunk.content
        except Exception as e:
            logger.warning(f"Read error {file_path}: {e}")
            return chunk.content

    def _read_pdf_page(self, file_path: str, page_number: Optional[int]) -> str:
        """Read a specific page from a PDF."""
        if not HAS_PYPDF or page_number is None:
            return f"[PDF page {page_number}]"
        try:
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                if 0 < page_number <= len(reader.pages):
                    return reader.pages[page_number - 1].extract_text() or ""
        except Exception as e:
            logger.warning(f"PDF read error: {e}")
        return f"[PDF page {page_number} - read error]"

    def _read_archive_member(self, file_path: str, chunk: Chunk) -> str:
        """Read a specific member from an archive."""
        member_name = chunk.metadata.get('member_name')
        if not member_name:
            return chunk.content
        try:
            if zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, 'r') as zf:
                    return zf.read(member_name).decode('utf-8', errors='replace')
        except Exception as e:
            logger.warning(f"Archive read error: {e}")
        return chunk.content

    def _read_spreadsheet_slice(self, file_path: str, chunk: Chunk) -> str:
        """Read a slice from a spreadsheet."""
        if not HAS_OPENPYXL:
            return chunk.content
        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheet_name = chunk.metadata.get('sheet_name', wb.sheetnames[0] if wb.sheetnames else None)
            if not sheet_name:
                return chunk.content
            ws = wb[sheet_name]
            rows = []
            for row in ws.iter_rows(values_only=True):
                row_text = "\t".join(str(c) if c is not None else "" for c in row)
                rows.append(row_text)
            return '\n'.join(rows[:100])
        except Exception as e:
            logger.warning(f"Spreadsheet read error: {e}")
        return chunk.content


# ─────────────────────────────────────────────────────────────────────────────
# LLM Client
# ─────────────────────────────────────────────────────────────────────────────

class LLMClient:
    """Unified LLM client supporting multiple providers."""

    def __init__(self, provider: str = "anthropic", model: Optional[str] = None,
                 api_key: Optional[str] = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self._client = None
        self._setup_client()

    def _setup_client(self):
        if self.provider == "anthropic" and HAS_ANTHROPIC:
            kwargs = {}
            if self.api_key:
                kwargs['api_key'] = self.api_key
            self._client = anthropic.Anthropic(**kwargs)
            if not self.model:
                self.model = "claude-3-5-sonnet-20241022"
        elif self.provider == "openai" and HAS_OPENAI:
            kwargs = {}
            if self.api_key:
                kwargs['api_key'] = self.api_key
            self._client = openai.OpenAI(**kwargs)
            if not self.model:
                self.model = "gpt-4o"
        else:
            logger.warning(f"LLM provider '{self.provider}' not available. Using mock responses.")
            self._client = None
            if not self.model:
                self.model = "mock"

    def complete(self, messages: List[Dict[str, str]], system: Optional[str] = None,
                 max_tokens: int = 4096, temperature: float = 0.3) -> Tuple[str, int]:
        """Complete a conversation. Returns (response_text, tokens_used)."""
        if self._client is None:
            return self._mock_complete(messages, system), 0

        try:
            if self.provider == "anthropic":
                return self._anthropic_complete(messages, system, max_tokens, temperature)
            elif self.provider == "openai":
                return self._openai_complete(messages, system, max_tokens, temperature)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return f"[LLM error: {e}]", 0

        return self._mock_complete(messages, system), 0

    def _anthropic_complete(self, messages, system, max_tokens, temperature):
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature
        }
        if system:
            kwargs["system"] = system
        response = self._client.messages.create(**kwargs)
        text = response.content[0].text if response.content else ""
        tokens = response.usage.input_tokens + response.usage.output_tokens
        return text, tokens

    def _openai_complete(self, messages, system, max_tokens, temperature):
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)
        response = self._client.chat.completions.create(
            model=self.model,
            messages=all_messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        text = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0
        return text, tokens

    def _mock_complete(self, messages, system) -> str:
        last_msg = messages[-1]['content'] if messages else ""
        return f"[Mock response to: {last_msg[:100]}...]"


# ─────────────────────────────────────────────────────────────────────────────
# Agent
# ─────────────────────────────────────────────────────────────────────────────

class ContextBuilder:
    """Builds context windows for LLM from search results."""

    def __init__(self, reader: DocumentReader, max_context_tokens: int = 8000):
        self.reader = reader
        self.max_context_tokens = max_context_tokens

    def build_context(self, results: List[SearchResult], query: str) -> Tuple[str, List[Citation]]:
        """Build context string and citations from search results."""
        context_parts = []
        citations = []
        total_chars = 0
        max_chars = self.max_context_tokens * 4  # rough token estimate

        for i, result in enumerate(results):
            window = self.reader.read_chunk_window(result.chunk, result.doc)
            ref_num = i + 1

            header = f"[Source {ref_num}] {result.doc.title}"
            if result.chunk.page_number:
                header += f" (Page {result.chunk.page_number})"
            if result.chunk.line_start is not None:
                header += f" (Lines {result.chunk.line_start}-{result.chunk.line_end})"
            if result.chunk.section_title:
                header += f" § {result.chunk.section_title}"
            header += f"\nFile: {result.doc.file_path}\n"

            part = f"{header}\n{window}\n"

            if total_chars + len(part) > max_chars:
                # Truncate
                remaining = max_chars - total_chars
                if remaining > 200:
                    part = part[:remaining] + "\n[...truncated...]"
                    context_parts.append(part)
                    total_chars += len(part)
                break

            context_parts.append(part)
            total_chars += len(part)

            citation = Citation(
                doc_id=result.doc.doc_id,
                file_path=result.doc.file_path,
                title=result.doc.title,
                chunk_id=result.chunk.chunk_id,
                page_number=result.chunk.page_number,
                line_start=result.chunk.line_start,
                line_end=result.chunk.line_end,
                section_title=result.chunk.section_title,
                snippet=result.snippet
            )
            citations.append(citation)

        context = "\n---\n".join(context_parts)
        return context, citations


class ResearchAgent:
    """The main research agent that answers queries using the knowledge base."""

    SYSTEM_PROMPT = """You are Marginalia, a research assistant with access to a personal knowledge base.
You have been given relevant excerpts from the user's documents. Your job is to:
1. Read the provided source material carefully
2. Answer the user's question based on the sources
3. Cite your sources using [Source N] notation
4. Be precise and quote directly when relevant
5. Acknowledge when information is incomplete or uncertain
6. Suggest follow-up questions when appropriate

Always ground your answers in the provided sources. Do not make up information."""

    def __init__(self, llm: LLMClient, search_engine: SearchEngine,
                 context_builder: ContextBuilder, db: Database,
                 search_mode: str = 'lexical', search_limit: int = 10):
        self.llm = llm
        self.search_engine = search_engine
        self.context_builder = context_builder
        self.db = db
        self.search_mode = search_mode
        self.search_limit = search_limit
        self.conversation_history: List[Dict[str, str]] = []

    def query(self, question: str, catalog_id: Optional[str] = None,
              tags: Optional[List[str]] = None, save_note: bool = True,
              include_notes: bool = True) -> AgentAnswer:
        """Answer a research question."""
        # Search for relevant content
        results = self.search_engine.search(
            question, limit=self.search_limit, mode=self.search_mode,
            catalog_id=catalog_id, tags=tags
        )

        # Also search investigation notes for prior research
        prior_notes = []
        if include_notes:
            prior_notes = self.search_engine.search_notes(question, limit=3)

        # Build context
        context, citations = self.context_builder.build_context(results, question)

        # Add prior notes context
        notes_context = ""
        if prior_notes:
            notes_parts = []
            for note in prior_notes:
                notes_parts.append(f"[Prior Research: {note.title}]\n{note.answer[:500]}")
            notes_context = "\n\nPrior investigation notes:\n" + "\n---\n".join(notes_parts)

        # Build prompt
        user_message = f"""Question: {question}

Relevant sources from knowledge base:
{context}
{notes_context}

Please answer the question based on the sources above, citing them with [Source N] notation."""

        self.conversation_history.append({"role": "user", "content": user_message})

        response_text, tokens = self.llm.complete(
            messages=self.conversation_history,
            system=self.SYSTEM_PROMPT
        )

        self.conversation_history.append({"role": "assistant", "content": response_text})

        # Keep conversation history manageable
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        answer = AgentAnswer(
            answer_id=str(uuid.uuid4()),
            query=question,
            answer=response_text,
            citations=citations,
            created_at=datetime.datetime.utcnow().isoformat(),
            model=self.llm.model,
            tokens_used=tokens
        )

        if save_note and citations:
            self._save_investigation_note(answer)

        return answer

    def generate_report(self, topic: str, catalog_id: Optional[str] = None,
                        tags: Optional[List[str]] = None) -> AgentAnswer:
        """Generate a comprehensive report on a topic."""
        results = self.search_engine.search(
            topic, limit=20, mode=self.search_mode,
            catalog_id=catalog_id, tags=tags
        )

        context, citations = self.context_builder.build_context(results, topic)

        user_message = f"""Generate a comprehensive research report on: {topic}

Available sources:
{context}

Please write a structured report with:
1. Executive Summary
2. Key Findings (with citations)
3. Detailed Analysis
4. Gaps and Uncertainties
5. Recommendations for Further Research

Cite all sources using [Source N] notation."""

        response_text, tokens = self.llm.complete(
            messages=[{"role": "user", "content": user_message}],
            system=self.SYSTEM_PROMPT,
            max_tokens=8192
        )

        answer = AgentAnswer(
            answer_id=str(uuid.uuid4()),
            query=f"Report: {topic}",
            answer=response_text,
            citations=citations,
            created_at=datetime.datetime.utcnow().isoformat(),
            model=self.llm.model,
            tokens_used=tokens,
            metadata={"type": "report"}
        )

        self._save_investigation_note(answer)
        return answer

    def _save_investigation_note(self, answer: AgentAnswer):
        """Save an investigation note for future recall."""
        # Extract follow-up questions from the answer
        follow_ups = self._extract_follow_up_questions(answer.answer)

        note = InvestigationNote(
            note_id=str(uuid.uuid4()),
            title=answer.query[:100],
            query=answer.query,
            answer=answer.answer,
            citations=answer.citations,
            created_at=answer.created_at,
            follow_up_questions=follow_ups,
            metadata={"model": answer.model, "tokens": answer.tokens_used}
        )

        citations_json = json.dumps([asdict(c) for c in answer.citations])

        self.db.execute("""
            INSERT INTO investigation_notes (note_id, title, query, answer, citations, created_at, tags, follow_up_questions, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (note.note_id, note.title, note.query, note.answer, citations_json,
              note.created_at, json.dumps(note.tags),
              json.dumps(note.follow_up_questions), json.dumps(note.metadata)))

        self.db.execute("""
            INSERT INTO notes_fts (note_id, title, query, answer) VALUES (?, ?, ?, ?)
        """, (note.note_id, note.title, note.query, note.answer))

        self.db.commit()

    def _extract_follow_up_questions(self, text: str) -> List[str]:
        """Extract follow-up questions from agent response."""
        questions = []
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line.endswith('?') and len(line) > 20:
                questions.append(line)
        return questions[:5]

    def reset_conversation(self):
        """Reset conversation history."""
        self.conversation_history = []


# ─────────────────────────────────────────────────────────────────────────────
# Metadata Manager
# ─────────────────────────────────────────────────────────────────────────────

class MetadataManager:
    """Manages document metadata."""

    def __init__(self, db: Database):
        self.db = db

    def update_metadata(self, doc_id: str, metadata: Dict[str, Any]) -> bool:
        row = self.db.fetchone("SELECT metadata FROM documents WHERE doc_id = ?", (doc_id,))
        if not row:
            return False
        existing = json.loads(row['metadata'] or '{}')
        existing.update(metadata)
        self.db.execute("UPDATE documents SET metadata = ? WHERE doc_id = ?",
                        (json.dumps(existing), doc_id))
        self.db.commit()
        return True

    def get_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        row = self.db.fetchone("SELECT metadata FROM documents WHERE doc_id = ?", (doc_id,))
        if not row:
            return None
        return json.loads(row['metadata'] or '{}')

    def set_summary(self, doc_id: str, summary: str) -> bool:
        self.db.execute("UPDATE documents SET summary = ? WHERE doc_id = ?", (summary, doc_id))
        self.db.commit()
        return True

    def get_document_stats(self) -> Dict[str, Any]:
        total = self.db.fetchone("SELECT COUNT(*) as cnt FROM documents")['cnt']
        by_type = self.db.fetchall("SELECT file_type, COUNT(*) as cnt FROM documents GROUP BY file_type")
        total_chunks = self.db.fetchone("SELECT COUNT(*) as cnt FROM chunks")['cnt']
        total_size = self.db.fetchone("SELECT SUM(size_bytes) as s FROM documents")['s'] or 0
        return {
            "total_documents": total,
            "total_chunks": total_chunks,
            "total_size_bytes": total_size,
            "by_type": {r['file_type']: r['cnt'] for r in by_type}
        }


# ─────────────────────────────────────────────────────────────────────────────
# Main Marginalia System
# ─────────────────────────────────────────────────────────────────────────────

class Marginalia:
    """
    Marginalia: A local-first personal knowledge management system with LLM agents.

    Keeps files in a normal folder tree, builds library metadata around them,
    and makes the agent read relevant original file windows before writing cited answers.
    """

    def __init__(self, vault_path: str, db_path: Optional[str] = None,
                 llm_provider: str = "anthropic", llm_model: Optional[str] = None,
                 llm_api_key: Optional[str] = None,
                 use_embeddings: bool = False, use_reranking: bool = False,
                 chunk_size: int = 1000, chunk_overlap: int = 200,
                 search_mode: str = 'lexical', search_limit: int = 10,
                 source_quota: int = 5):
        """
        Initialize Marginalia.

        Args:
            vault_path: Root directory of the knowledge base
            db_path: Path to SQLite database (defaults to vault_path/.marginalia/db.sqlite)
            llm_provider: LLM provider ('anthropic', 'openai')
            llm_model: Specific model to use
            llm_api_key: API key (uses env vars if not provided)
            use_embeddings: Enable semantic search with embeddings
            use_reranking: Enable result reranking
            chunk_size: Characters per chunk
            chunk_overlap: Overlap between chunks
            search_mode: Default search mode ('lexical', 'semantic', 'hybrid')
            search_limit: Default number of search results
            source_quota: Max results per source document
        """
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(parents=True, exist_ok=True)

        marginalia_dir = self.vault_path / '.marginalia'
        marginalia_dir.mkdir(exist_ok=True)

        if db_path is None:
            db_path = str(marginalia_dir / 'db.sqlite')

        self.db = Database(db_path)

        # Core components
        self.ingester = Ingester(self.db, str(self.vault_path), chunk_size, chunk_overlap)
        self.catalog_manager = CatalogManager(self.db)
        self.tag_manager = TagManager(self.db)
        self.view_manager = ViewManager(self.db)
        self.journal_manager = JournalManager(self.db)
        self.relation_miner = RelationMiner(self.db)
        self.metadata_manager = MetadataManager(self.db)

        self.search_engine = SearchEngine(
            self.db, use_embeddings=use_embeddings,
            use_reranking=use_reranking, source_quota=source_quota
        )

        self.reader = DocumentReader()
        self.context_builder = ContextBuilder(self.reader)

        self.llm = LLMClient(provider=llm_provider, model=llm_model, api_key=llm_api_key)

        self.agent = ResearchAgent(
            llm=self.llm,
            search_engine=self.search_engine,
            context_builder=self.context_builder,
            db=self.db,
            search_mode=search_mode,
            search_limit=search_limit
        )

        logger.info(f"Marginalia initialized. Vault: {vault_path}, DB: {db_path}")

    # ── Ingestion ──────────────────────────────────────────────────────────

    def ingest(self, path: str, catalog: Optional[str] = None,
               tags: Optional[List[str]] = None,
               recursive: bool = True) -> Union[DocumentRecord, List[DocumentRecord]]:
        """Ingest a file or directory."""
        p = Path(path)
        catalog_id = None
        if catalog:
            cat = self._find_or_create_catalog(catalog)
            catalog_id = cat.catalog_id

        if p.is_file():
            return self.ingester.ingest_file(str(p), catalog_id=catalog_id, tags=tags)
        elif p.is_dir():
            return self.ingester.ingest_directory(str(p), catalog_id=catalog_id, recursive=recursive)
        else:
            logger.error(f"Path not found: {path}")
            return []

    def ingest_vault(self) -> List[DocumentRecord]:
        """Ingest all files in the vault."""
        return self.ingester.ingest_directory(str(self.vault_path), recursive=True)

    def _find_or_create_catalog(self, name: str) -> Catalog:
        rows = self.db.fetchall("SELECT * FROM catalogs WHERE name = ?", (name,))
        if rows:
            r = rows[0]
            return Catalog(catalog_id=r['catalog_id'], name=r['name'],
                           description=r['description'], parent_id=r['parent_id'],
                           created_at=r['created_at'])
        return self.catalog_manager.create_catalog(name)

    # ── Search ─────────────────────────────────────────────────────────────

    def search(self, query: str, limit: int = 20, mode: str = 'lexical',
               catalog: Optional[str] = None, tags: Optional[List[str]] = None) -> List[SearchResult]:
        """Search the knowledge base."""
        catalog_id = None
        if catalog:
            rows = self.db.fetchall("SELECT catalog_id FROM catalogs WHERE name = ?", (catalog,))
            if rows:
                catalog_id = rows[0]['catalog_id']

        return self.search_engine.search(query, limit=limit, mode=mode,
                                          catalog_id=catalog_id, tags=tags)

    # ── Agent ──────────────────────────────────────────────────────────────

    def ask(self, question: str, catalog: Optional[str] = None,
            tags: Optional[List[str]] = None, save_note: bool = True) -> AgentAnswer:
        """Ask the research agent a question."""
        catalog_id = None
        if catalog:
            rows = self.db.fetchall("SELECT catalog_id FROM catalogs WHERE name = ?", (catalog,))
            if rows:
                catalog_id = rows[0]['catalog_id']

        return self.agent.query(question, catalog_id=catalog_id, tags=tags, save_note=save_note)

    def report(self, topic: str, catalog: Optional[str] = None,
               tags: Optional[List[str]] = None) -> AgentAnswer:
        """Generate a research report on a topic."""
        catalog_id = None
        if catalog:
            rows = self.db.fetchall("SELECT catalog_id FROM catalogs WHERE name = ?", (catalog,))
            if rows:
                catalog_id = rows[0]['catalog_id']

        return self.agent.generate_report(topic, catalog_id=catalog_id, tags=tags)

    def reset_conversation(self):
        """Reset the agent's conversation history."""
        self.agent.reset_conversation()

    # ── Catalogs ───────────────────────────────────────────────────────────

    def create_catalog(self, name: str, description: str = "",
                       parent: Optional[str] = None) -> Catalog:
        """Create a new catalog."""
        parent_id = None
        if parent:
            rows = self.db.fetchall("SELECT catalog_id FROM catalogs WHERE name = ?", (parent,))
            if rows:
                parent_id = rows[0]['catalog_id']
        return self.catalog_manager.create_catalog(name, description, parent_id)

    def list_catalogs(self) -> List[Catalog]:
        """List all catalogs."""
        return self.catalog_manager.list_catalogs()

    def get_catalog_documents(self, catalog_name: str) -> List[DocumentRecord]:
        """Get documents in a catalog."""
        rows = self.db.fetchall("SELECT catalog_id FROM catalogs WHERE name = ?", (catalog_name,))
        if not rows:
            return []
        return self.catalog_manager.get_catalog_documents(rows[0]['catalog_id'])

    # ── Tags ───────────────────────────────────────────────────────────────

    def create_tag(self, name: str, color: Optional[str] = None,
                   description: Optional[str] = None) -> Tag:
        """Create a new tag."""
        return self.tag_manager.create_tag(name, color, description)

    def list_tags(self) -> List[Tag]:
        """List all tags."""
        return self.tag_manager.list_tags()

    def tag_document(self, doc_id: str, tag_name: str) -> bool:
        """Tag a document."""
        return self.tag_manager.tag_document(doc_id, tag_name)

    def get_documents_by_tag(self, tag_name: str) -> List[str]:
        """Get document IDs with a specific tag."""
        return self.tag_manager.get_documents_by_tag(tag_name)

    # ── Views ──────────────────────────────────────────────────────────────

    def create_view(self, name: str, query: str, filters: Optional[Dict] = None,
                    description: Optional[str] = None) -> View:
        """Create a saved search view."""
        return self.view_manager.create_view(name, query, filters, description)

    def list_views(self) -> List[View]:
        """List all saved views."""
        return self.view_manager.list_views()

    def execute_view(self, view_name: str) -> List[SearchResult]:
        """Execute a saved view."""
        rows = self.db.fetchall("SELECT * FROM views WHERE name = ?", (view_name,))
        if not rows:
            return []
        view = View(view_id=rows[0]['view_id'], name=rows[0]['name'],
                    query=rows[0]['query'],
                    filters=json.loads(rows[0]['filters'] or '{}'),
                    created_at=rows[0]['created_at'])
        return self.search(view.query, **{k: v for k, v in view.filters.items()
                                          if k in ('limit', 'mode', 'catalog', 'tags')})

    # ── Journal ────────────────────────────────────────────────────────────

    def journal_write(self, title: str, content: str, tags: Optional[List[str]] = None,
                      related_docs: Optional[List[str]] = None) -> JournalEntry:
        """Write a journal entry."""
        return self.journal_manager.create_entry(title, content, tags, related_docs)

    def journal_list(self, limit: int = 50) -> List[JournalEntry]:
        """List journal entries."""
        return self.journal_manager.list_entries(limit)

    def journal_search(self, query: str) -> List[JournalEntry]:
        """Search journal entries."""
        return self.journal_manager.search_entries(query)

    # ── Relations ──────────────────────────────────────────────────────────

    def mine_relations(self, doc_id: str) -> List[Relation]:
        """Mine relations for a document."""
        return self.relation_miner.mine_relations(doc_id)

    def add_relation(self, source_doc_id: str, target_doc_id: str,
                     relation_type: str, confidence: float = 1.0) -> Relation:
        """Manually add a relation between documents."""
        return self.relation_miner.add_relation(source_doc_id, target_doc_id,
                                                 relation_type, confidence)

    def get_relations(self, doc_id: str) -> List[Relation]:
        """Get relations for a document."""
        return self.relation_miner.get_relations(doc_id)

    # ── Documents ──────────────────────────────────────────────────────────

    def list_documents(self, limit: int = 100, offset: int = 0) -> List[DocumentRecord]:
        """List all documents."""
        rows = self.db.fetchall("""
            SELECT * FROM documents ORDER BY ingested_at DESC LIMIT ? OFFSET ?
        """, (limit, offset))
        return [DocumentRecord(
            doc_id=r['doc_id'], file_path=r['file_path'], title=r['title'],
            file_type=r['file_type'], size_bytes=r['size_bytes'], checksum=r['checksum'],
            created_at=r['created_at'], modified_at=r['modified_at'],
            ingested_at=r['ingested_at'], catalog_id=r['catalog_id'],
            tags=json.loads(r['tags'] or '[]'),
            metadata=json.loads(r['metadata'] or '{}'),
            chunk_count=r['chunk_count'], language=r['language'], summary=r['summary']
        ) for r in rows]

    def get_document(self, doc_id: str) -> Optional[DocumentRecord]:
        """Get a document by ID."""
        row = self.db.fetchone("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        if not row:
            return None
        return DocumentRecord(
            doc_id=row['doc_id'], file_path=row['file_path'], title=row['title'],
            file_type=row['file_type'], size_bytes=row['size_bytes'], checksum=row['checksum'],
            created_at=row['created_at'], modified_at=row['modified_at'],
            ingested_at=row['ingested_at'], catalog_id=row['catalog_id'],
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}'),
            chunk_count=row['chunk_count'], language=row['language'], summary=row['summary']
        )

    def delete_document(self, doc_id: str) -> bool:
        """Remove a document from the index."""
        self.db.execute("DELETE FROM chunks_fts WHERE doc_id = ?", (doc_id,))
        self.db.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        self.db.commit()
        return True

    def get_document_chunks(self, doc_id: str) -> List[Chunk]:
        """Get all chunks for a document."""
        rows = self.db.fetchall("SELECT * FROM chunks WHERE doc_id = ? ORDER BY chunk_index", (doc_id,))
        return [Chunk(
            chunk_id=r['chunk_id'], doc_id=r['doc_id'], content=r['content'],
            chunk_index=r['chunk_index'], start_offset=r['start_offset'] or 0,
            end_offset=r['end_offset'] or 0, page_number=r['page_number'],
            line_start=r['line_start'], line_end=r['line_end'],
            section_title=r['section_title'],
            metadata=json.loads(r['metadata'] or '{}')
        ) for r in rows]

    # ── Metadata ───────────────────────────────────────────────────────────

    def update_metadata(self, doc_id: str, metadata: Dict[str, Any]) -> bool:
        """Update document metadata."""
        return self.metadata_manager.update_metadata(doc_id, metadata)

    def set_summary(self, doc_id: str, summary: str) -> bool:
        """Set document summary."""
        return self.metadata_manager.set_summary(doc_id, summary)

    def stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        return self.metadata_manager.get_document_stats()

    # ── Investigation Notes ────────────────────────────────────────────────

    def list_notes(self, limit: int = 50) -> List[InvestigationNote]:
        """List investigation notes."""
        rows = self.db.fetchall("""
            SELECT * FROM investigation_notes ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        return [InvestigationNote(
            note_id=r['note_id'], title=r['title'], query=r['query'],
            answer=r['answer'], citations=json.loads(r['citations'] or '[]'),
            created_at=r['created_at'], tags=json.loads(r['tags'] or '[]'),
            follow_up_questions=json.loads(r['follow_up_questions'] or '[]'),
            metadata=json.loads(r['metadata'] or '{}')
        ) for r in rows]

    def search_notes(self, query: str) -> List[InvestigationNote]:
        """Search investigation notes."""
        return self.search_engine.search_notes(query)

    # ── Export ─────────────────────────────────────────────────────────────

    def export_answer(self, answer: AgentAnswer, format: str = 'markdown') -> str:
        """Export an answer to a formatted string."""
        if format == 'markdown':
            return self._export_markdown(answer)
        elif format == 'json':
            return json.dumps({
                'query': answer.query,
                'answer': answer.answer,
                'citations': [asdict(c) for c in answer.citations],
                'created_at': answer.created_at,
                'model': answer.model
            }, indent=2)
        else:
            return answer.answer

    def _export_markdown(self, answer: AgentAnswer) -> str:
        lines = [
            f"# Research Answer",
            f"",
            f"**Query:** {answer.query}",
            f"**Date:** {answer.created_at}",
            f"**Model:** {answer.model}",
            f"",
            f"## Answer",
            f"",
            answer.answer,
            f"",
            f"## Sources",
            f""
        ]
        for i, citation in enumerate(answer.citations, 1):
            lines.append(f"**[Source {i}]** {citation.title}")
            lines.append(f"- File: `{citation.file_path}`")
            if citation.page_number:
                lines.append(f"- Page: {citation.page_number}")
            if citation.line_start is not None:
                lines.append(f"- Lines: {citation.line_start}-{citation.line_end}")
            if citation.section_title:
                lines.append(f"- Section: {citation.section_title}")
            if citation.snippet:
                lines.append(f"- Excerpt: *{citation.snippet[:200]}*")
            lines.append("")
        return '\n'.join(lines)

    def save_answer_to_file(self, answer: AgentAnswer, output_path: str,
                             format: str = 'markdown') -> bool:
        """Save an answer to a file."""
        try:
            content = self.export_answer(answer, format)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Save error: {e}")
            return False

    # ── Watcher ────────────────────────────────────────────────────────────

    def watch_vault(self, interval: int = 60) -> threading.Thread:
        """Start watching the vault for new/changed files."""
        def _watch():
            logger.info(f"Watching vault: {self.vault_path} (interval: {interval}s)")
            while True:
                try:
                    self.ingest_vault()
                except Exception as e:
                    logger.error(f"Watch error: {e}")
                time.sleep(interval)

        t = threading.Thread(target=_watch, daemon=True)
        t.start()
        return t

    def __repr__(self) -> str:
        stats = self.stats()
        return (f"Marginalia(vault='{self.vault_path}', "
                f"docs={stats['total_documents']}, "
                f"chunks={stats['total_chunks']}, "
                f"llm={self.llm.model})")


# ─────────────────────────────────────────────────────────────────────────────
# CLI Interface
# ─────────────────────────────────────────────────────────────────────────────

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
        print(f"  Vault: {self.m.vault_path}")
        stats = self.m.stats()
        print(f"  Documents: {stats['total_documents']} | Chunks: {stats['total_chunks']}")
        print(f"  LLM: {self.m.llm.model}")
        print(f"{'='*60}")
        print("  Commands: ingest, search, ask, report, catalog, tag, journal,")
        print("            notes, stats, help, quit")
        print(f"{'='*60}\n")

        while self.running:
            try:
                line = input("marginalia> ").strip()
                if not line:
                    continue
                self._dispatch(line)
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit.")
            except EOFError:
                break

    def _dispatch(self, line: str):
        parts = line.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handlers = {
            'ingest': self._cmd_ingest,
            'search': self._cmd_search,
            'ask': self._cmd_ask,
            'report': self._cmd_report,
            'catalog': self._cmd_catalog,
            'tag': self._cmd_tag,
            'journal': self._cmd_journal,
            'notes': self._cmd_notes,
            'stats': self._cmd_stats,
            'docs': self._cmd_docs,
            'help': self._cmd_help,
            'quit': self._cmd_quit,
            'exit': self._cmd_quit,
            'reset': lambda _: self.m.reset_conversation() or print("Conversation reset."),
        }

        handler = handlers.get(cmd)
        if handler:
            handler(args)
        else:
            print(f"Unknown command: {cmd}. Type 'help' for commands.")

    def _cmd_ingest(self, args: str):
        if not args:
            print("Usage: ingest <path> [--catalog <name>] [--tags tag1,tag2]")
            return
        parts = args.split()
        path = parts[0]
        catalog = None
        tags = None
        i = 1
        while i < len(parts):
            if parts[i] == '--catalog' and i+1 < len(parts):
                catalog = parts[i+1]
                i += 2
            elif parts[i] == '--tags' and i+1 < len(parts):
                tags = parts[i+1].split(',')
                i += 2
            else:
                i += 1
        result = self.m.ingest(path, catalog=catalog, tags=tags)
        if isinstance(result, list):
            print(f"Ingested {len(result)} documents.")
        elif result:
            print(f"Ingested: {result.title} ({result.chunk_count} chunks)")
        else:
            print("Ingestion failed.")

    def _cmd_search(self, args: str):
        if not args:
            print("Usage: search <query>")
            return
        results = self.m.search(args, limit=5)
        if not results:
            print("No results found.")
            return
        print(f"\nFound {len(results)} results:\n")
        for i, r in enumerate(results, 1):
            print(f"[{i}] {r.doc.title} (score: {r.score:.3f})")
            if r.chunk.page_number:
                print(f"    Page {r.chunk.page_number}", end="")
            if r.chunk.line_start is not None:
                print(f"    Lines {r.chunk.line_start}-{r.chunk.line_end}", end="")
            print()
            print(f"    {r.snippet[:150]}")
            print()

    def _cmd_ask(self, args: str):
        if not args:
            print("Usage: ask <question>")
            return
        print("\nSearching and reading sources...")
        answer = self.m.ask(args)
        print(f"\n{answer.answer}\n")
        if answer.citations:
            print(f"Sources ({len(answer.citations)}):")
            for i, c in enumerate(answer.citations, 1):
                print(f"  [{i}] {c.title} - {c.file_path}")
        print()

    def _cmd_report(self, args: str):
        if not args:
            print("Usage: report <topic>")
            return
        print("\nGenerating report...")
        answer = self.m.report(args)
        print(f"\n{answer.answer}\n")

    def _cmd_catalog(self, args: str):
        parts = args.split(None, 1)
        sub = parts[0] if parts else 'list'
        if sub == 'list':
            catalogs = self.m.list_catalogs()
            if not catalogs:
                print("No catalogs.")
                return
            for c in catalogs:
                print(f"  {c.name}: {c.description}")
        elif sub == 'create' and len(parts) > 1:
            cat = self.m.create_catalog(parts[1])
            print(f"Created catalog: {cat.name}")
        else:
            print("Usage: catalog list | catalog create <name>")

    def _cmd_tag(self, args: str):
        parts = args.split(None, 1)
        sub = parts[0] if parts else 'list'
        if sub == 'list':
            tags = self.m.list_tags()
            if not tags:
                print("No tags.")
                return
            for t in tags:
                print(f"  #{t.name}")
        elif sub == 'create' and len(parts) > 1:
            tag = self.m.create_tag(parts[1])
            print(f"Created tag: #{tag.name}")
        else:
            print("Usage: tag list | tag create <name>")

    def _cmd_journal(self, args: str):
        parts = args.split(None, 1)
        sub = parts[0] if parts else 'list'
        if sub == 'list':
            entries = self.m.journal_list(limit=10)
            if not entries:
                print("No journal entries.")
                return
            for e in entries:
                print(f"  [{e.created_at[:10]}] {e.title}")
        elif sub == 'write':
            title = input("Title: ").strip()
            print("Content (end with '.' on a line by itself):")
            lines = []
            while True:
                line = input()
                if line == '.':
                    break
                lines.append(line)
            entry = self.m.journal_write(title, '\n'.join(lines))
            print(f"Journal entry saved: {entry.entry_id}")
        elif sub == 'search' and len(parts) > 1:
            entries = self.m.journal_search(parts[1])
            for e in entries:
                print(f"  [{e.created_at[:10]}] {e.title}")
        else:
            print("Usage: journal list | journal write | journal search <query>")

    def _cmd_notes(self, args: str):
        if args:
            notes = self.m.search_notes(args)
        else:
            notes = self.m.list_notes(limit=10)
        if not notes:
            print("No investigation notes.")
            return
        for n in notes:
            print(f"  [{n.created_at[:10]}] {n.title}")
            print(f"    {n.answer[:100]}...")
            print()

    def _cmd_stats(self, args: str):
        stats = self.m.stats()
        print(f"\nKnowledge Base Statistics:")
        print(f"  Documents: {stats['total_documents']}")
        print(f"  Chunks: {stats['total_chunks']}")
        print(f"  Total size: {stats['total_size_bytes'] / 1024:.1f} KB")
        print(f"  By type: {stats['by_type']}")
        print()

    def _cmd_docs(self, args: str):
        docs = self.m.list_documents(limit=20)
        if not docs:
            print("No documents.")
            return
        print(f"\nDocuments ({len(docs)}):")
        for d in docs:
            print(f"  [{d.file_type}] {d.title} ({d.chunk_count} chunks)")
        print()

    def _cmd_help(self, args: str):
        print("""
Commands:
  ingest <path> [--catalog <name>] [--tags t1,t2]  - Ingest file or directory
  search <query>                                     - Search knowledge base
  ask <question>                                     - Ask the research agent
  report <topic>                                     - Generate a research report
  catalog list|create <name>                         - Manage catalogs
  tag list|create <name>                             - Manage tags
  journal list|write|search <query>                  - Research journal
  notes [query]                                      - Investigation notes
  docs                                               - List documents
  stats                                              - Knowledge base statistics
  reset                                              - Reset conversation history
  help                                               - Show this help
  quit                                               - Exit
""")

    def _cmd_quit(self, args: str):
        print("Goodbye!")
        self.running = False


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def create_marginalia(vault_path: str = "~/marginalia-vault",
                      llm_provider: str = "anthropic",
                      **kwargs) -> Marginalia:
    """Convenience factory function."""
    vault_path = str(Path(vault_path).expanduser())
    return Marginalia(vault_path=vault_path, llm_provider=llm_provider, **kwargs)


def main():
    """Main entry point for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Marginalia - Personal Knowledge Management System"
    )
    parser.add_argument('--vault', default='~/marginalia-vault',
                        help='Path to vault directory')
    parser.add_argument('--db', default=None, help='Path to database file')
    parser.add_argument('--provider', default='anthropic',
                        choices=['anthropic', 'openai'],
                        help='LLM provider')
    parser.add_argument('--model', default=None, help='LLM model name')
    parser.add_argument('--embeddings', action='store_true',
                        help='Enable semantic search')
    parser.add_argument('--rerank', action='store_true',
                        help='Enable result reranking')
    parser.add_argument('--mode', default='lexical',
                        choices=['lexical', 'semantic', 'hybrid'],
                        help='Search mode')
    parser.add_argument('--ingest', default=None,
                        help='Ingest a file or directory and exit')
    parser.add_argument('--ask', default=None,
                        help='Ask a question and exit')
    parser.add_argument('--report', default=None,
                        help='Generate a report and exit')

    args = parser.parse_args()

    m = Marginalia(
        vault_path=str(Path(args.vault).expanduser()),
        db_path=args.db,
        llm_provider=args.provider,
        llm_model=args.model,
        use_embeddings=args.embeddings,
        use_reranking=args.rerank,
        search_mode=args.mode
    )

    if args.ingest:
        result = m.ingest(args.ingest)
        if isinstance(result, list):
            print(f"Ingested {len(result)} documents.")
        elif result:
            print(f"Ingested: {result.title}")
        return

    if args.ask:
        answer = m.ask(args.ask)
        print(answer.answer)
        if answer.citations:
            print(f"\nSources:")
            for i, c in enumerate(answer.citations, 1):
                print(f"  [{i}] {c.title}")
        return

    if args.report:
        answer = m.report(args.report)
        print(answer.answer)
        return

    # Interactive shell
    shell = MarginaliaShell(m)
    shell.run()


if __name__ == '__main__':
    main()