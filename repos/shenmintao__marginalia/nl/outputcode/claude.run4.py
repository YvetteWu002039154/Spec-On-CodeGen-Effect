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
    language: str = "en"
    word_count: int = 0
    page_count: int = 0
    author: str = ""
    description: str = ""
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentChunk:
    chunk_id: str
    doc_id: str
    content: str
    chunk_type: str  # "text", "page", "line_range", "table_slice", "archive_member"
    start_offset: int
    end_offset: int
    page_num: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    section_title: Optional[str] = None
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    doc_id: str
    chunk_id: str
    file_path: str
    title: str
    content: str
    score: float
    match_type: str  # "lexical", "semantic", "hybrid"
    chunk_type: str
    page_num: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    section_title: Optional[str] = None


@dataclass
class Citation:
    doc_id: str
    file_path: str
    title: str
    chunk_id: str
    excerpt: str
    page_num: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    section_title: Optional[str] = None


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


@dataclass
class Relation:
    relation_id: str
    source_doc_id: str
    target_doc_id: str
    relation_type: str  # "references", "similar_to", "contradicts", "extends", "cites"
    confidence: float
    evidence: str = ""
    created_at: str = ""


@dataclass
class Catalog:
    catalog_id: str
    name: str
    description: str
    folder_patterns: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    doc_count: int = 0


@dataclass
class View:
    view_id: str
    name: str
    description: str
    filter_tags: List[str] = field(default_factory=list)
    filter_catalogs: List[str] = field(default_factory=list)
    filter_file_types: List[str] = field(default_factory=list)
    sort_by: str = "modified_at"
    sort_order: str = "desc"
    created_at: str = ""


@dataclass
class JournalEntry:
    entry_id: str
    date: str
    content: str
    tags: List[str] = field(default_factory=list)
    linked_doc_ids: List[str] = field(default_factory=list)
    created_at: str = ""


# ============================================================
# Database Layer
# ============================================================

class Database:
    """SQLite database manager for Marginalia."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
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
                language TEXT DEFAULT 'en',
                word_count INTEGER DEFAULT 0,
                page_count INTEGER DEFAULT 0,
                author TEXT DEFAULT '',
                description TEXT DEFAULT '',
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
                start_offset INTEGER,
                end_offset INTEGER,
                page_num INTEGER,
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
                embedding_dim INTEGER,
                FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS catalogs (
                catalog_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                folder_patterns TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                created_at TEXT,
                doc_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS views (
                view_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                filter_tags TEXT DEFAULT '[]',
                filter_catalogs TEXT DEFAULT '[]',
                filter_file_types TEXT DEFAULT '[]',
                sort_by TEXT DEFAULT 'modified_at',
                sort_order TEXT DEFAULT 'desc',
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS tags (
                tag TEXT PRIMARY KEY,
                description TEXT DEFAULT '',
                color TEXT DEFAULT '',
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS relations (
                relation_id TEXT PRIMARY KEY,
                source_doc_id TEXT NOT NULL,
                target_doc_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                confidence REAL,
                evidence TEXT DEFAULT '',
                created_at TEXT,
                FOREIGN KEY (source_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (target_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
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

            CREATE TABLE IF NOT EXISTS journal_entries (
                entry_id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                linked_doc_ids TEXT DEFAULT '[]',
                created_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_documents_file_path ON documents(file_path);
            CREATE INDEX IF NOT EXISTS idx_documents_catalog_id ON documents(catalog_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
            CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_doc_id);
            CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_doc_id);
        """)
        conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def executemany(self, sql: str, params_list: List[tuple]):
        self.conn.executemany(sql, params_list)

    def commit(self):
        self.conn.commit()

    def fetchall(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchone()


# ============================================================
# File Ingestion
# ============================================================

class FileIngester:
    """Handles ingestion of various file types."""

    SUPPORTED_EXTENSIONS = {
        '.txt', '.md', '.markdown', '.rst', '.org',
        '.pdf',
        '.docx', '.doc',
        '.xlsx', '.xls', '.csv',
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp',
        '.log',
        '.zip', '.tar', '.gz', '.tar.gz', '.tgz', '.bz2',
        '.json', '.yaml', '.yml', '.toml', '.xml', '.html', '.htm',
        '.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.go', '.rs',
    }

    def __init__(self, knowledge_base_path: str):
        self.kb_path = Path(knowledge_base_path)
        self.kb_path.mkdir(parents=True, exist_ok=True)

    def compute_checksum(self, file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()

    def get_file_type(self, file_path: str) -> str:
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix in {'.txt', '.md', '.markdown', '.rst', '.org'}:
            return 'text'
        elif suffix == '.pdf':
            return 'pdf'
        elif suffix in {'.docx', '.doc'}:
            return 'docx'
        elif suffix in {'.xlsx', '.xls'}:
            return 'spreadsheet'
        elif suffix == '.csv':
            return 'csv'
        elif suffix in {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}:
            return 'image'
        elif suffix == '.log':
            return 'log'
        elif suffix in {'.zip', '.tar', '.gz', '.bz2', '.tgz'}:
            return 'archive'
        elif suffix in {'.json', '.yaml', '.yml', '.toml', '.xml', '.html', '.htm'}:
            return 'markup'
        elif suffix in {'.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.go', '.rs'}:
            return 'code'
        else:
            return 'unknown'

    def extract_text(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text content and metadata from a file."""
        file_type = self.get_file_type(file_path)
        meta = {}

        try:
            if file_type == 'text':
                return self._extract_text_file(file_path, meta)
            elif file_type == 'pdf':
                return self._extract_pdf(file_path, meta)
            elif file_type == 'docx':
                return self._extract_docx(file_path, meta)
            elif file_type in ('spreadsheet', 'csv'):
                return self._extract_spreadsheet(file_path, meta)
            elif file_type == 'image':
                return self._extract_image(file_path, meta)
            elif file_type == 'log':
                return self._extract_text_file(file_path, meta)
            elif file_type == 'archive':
                return self._extract_archive(file_path, meta)
            elif file_type in ('markup', 'code'):
                return self._extract_text_file(file_path, meta)
            else:
                return self._extract_text_file(file_path, meta)
        except Exception as e:
            logger.warning(f"Error extracting text from {file_path}: {e}")
            return "", meta

    def _extract_text_file(self, file_path: str, meta: Dict) -> Tuple[str, Dict]:
        encodings = ['utf-8', 'latin-1', 'cp1252', 'utf-16']
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    content = f.read()
                meta['encoding'] = enc
                return content, meta
            except (UnicodeDecodeError, UnicodeError):
                continue
        with open(file_path, 'rb') as f:
            content = f.read().decode('utf-8', errors='replace')
        return content, meta

    def _extract_pdf(self, file_path: str, meta: Dict) -> Tuple[str, Dict]:
        if not HAS_PYPDF:
            logger.warning("pypdf not available, cannot extract PDF text")
            return f"[PDF file: {Path(file_path).name}]", meta

        pages = []
        try:
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                meta['page_count'] = len(reader.pages)
                if reader.metadata:
                    meta['author'] = str(reader.metadata.get('/Author', ''))
                    meta['title'] = str(reader.metadata.get('/Title', ''))
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ''
                    pages.append(f"[Page {i+1}]\n{text}")
        except Exception as e:
            logger.warning(f"PDF extraction error: {e}")
            return f"[PDF file: {Path(file_path).name}]", meta

        return '\n\n'.join(pages), meta

    def _extract_docx(self, file_path: str, meta: Dict) -> Tuple[str, Dict]:
        if not HAS_DOCX:
            logger.warning("python-docx not available")
            return f"[DOCX file: {Path(file_path).name}]", meta

        try:
            doc = docx.Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            meta['page_count'] = 1
            return '\n\n'.join(paragraphs), meta
        except Exception as e:
            logger.warning(f"DOCX extraction error: {e}")
            return f"[DOCX file: {Path(file_path).name}]", meta

    def _extract_spreadsheet(self, file_path: str, meta: Dict) -> Tuple[str, Dict]:
        path = Path(file_path)
        if path.suffix.lower() == '.csv':
            try:
                import csv as csv_module
                rows = []
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    reader = csv_module.reader(f)
                    for row in reader:
                        rows.append('\t'.join(row))
                meta['row_count'] = len(rows)
                return '\n'.join(rows), meta
            except Exception as e:
                logger.warning(f"CSV extraction error: {e}")
                return f"[CSV file: {path.name}]", meta
        else:
            if not HAS_OPENPYXL:
                logger.warning("openpyxl not available")
                return f"[Spreadsheet file: {path.name}]", meta
            try:
                wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
                sheets = []
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    rows = []
                    for row in ws.iter_rows(values_only=True):
                        row_str = '\t'.join(str(c) if c is not None else '' for c in row)
                        rows.append(row_str)
                    sheets.append(f"[Sheet: {sheet_name}]\n" + '\n'.join(rows))
                meta['sheet_count'] = len(wb.sheetnames)
                return '\n\n'.join(sheets), meta
            except Exception as e:
                logger.warning(f"Spreadsheet extraction error: {e}")
                return f"[Spreadsheet file: {path.name}]", meta

    def _extract_image(self, file_path: str, meta: Dict) -> Tuple[str, Dict]:
        if HAS_PIL:
            try:
                img = Image.open(file_path)
                meta['image_size'] = f"{img.width}x{img.height}"
                meta['image_mode'] = img.mode
                return f"[Image: {Path(file_path).name}, Size: {img.width}x{img.height}, Mode: {img.mode}]", meta
            except Exception as e:
                logger.warning(f"Image extraction error: {e}")
        return f"[Image file: {Path(file_path).name}]", meta

    def _extract_archive(self, file_path: str, meta: Dict) -> Tuple[str, Dict]:
        members = []
        path = Path(file_path)

        try:
            if path.suffix.lower() == '.zip' or zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, 'r') as zf:
                    names = zf.namelist()
                    meta['member_count'] = len(names)
                    members = names[:100]  # limit
                    text_members = []
                    for name in names[:20]:
                        try:
                            with zf.open(name) as mf:
                                content = mf.read(4096).decode('utf-8', errors='replace')
                                text_members.append(f"[Member: {name}]\n{content}")
                        except Exception:
                            text_members.append(f"[Member: {name}] (binary)")
                    return f"[Archive: {path.name}]\nMembers:\n" + '\n'.join(names) + '\n\n' + '\n\n'.join(text_members), meta
        except Exception:
            pass

        try:
            if tarfile.is_tarfile(file_path):
                with tarfile.open(file_path, 'r:*') as tf:
                    names = tf.getnames()
                    meta['member_count'] = len(names)
                    return f"[Archive: {path.name}]\nMembers:\n" + '\n'.join(names[:100]), meta
        except Exception:
            pass

        return f"[Archive file: {path.name}]", meta

    def chunk_text(self, text: str, doc_id: str, file_type: str,
                   chunk_size: int = 1000, overlap: int = 100) -> List[DocumentChunk]:
        """Split text into chunks with appropriate strategy per file type."""
        chunks = []

        if file_type == 'pdf':
            # Split by page markers
            page_pattern = re.compile(r'\[Page (\d+)\]')
            pages = page_pattern.split(text)
            if len(pages) > 1:
                i = 1
                while i < len(pages):
                    page_num = int(pages[i])
                    content = pages[i + 1].strip() if i + 1 < len(pages) else ''
                    if content:
                        chunk_id = str(uuid.uuid4())
                        chunks.append(DocumentChunk(
                            chunk_id=chunk_id,
                            doc_id=doc_id,
                            content=content,
                            chunk_type='page',
                            start_offset=0,
                            end_offset=len(content),
                            page_num=page_num
                        ))
                    i += 2
                if chunks:
                    return chunks

        if file_type in ('log', 'code'):
            # Split by lines
            lines = text.split('\n')
            batch_size = 50
            for i in range(0, len(lines), batch_size - 10):
                batch = lines[i:i + batch_size]
                content = '\n'.join(batch)
                if content.strip():
                    chunk_id = str(uuid.uuid4())
                    chunks.append(DocumentChunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        content=content,
                        chunk_type='line_range',
                        start_offset=i,
                        end_offset=min(i + batch_size, len(lines)),
                        line_start=i + 1,
                        line_end=min(i + batch_size, len(lines))
                    ))
            if chunks:
                return chunks

        if file_type in ('spreadsheet', 'csv'):
            # Split by rows
            lines = text.split('\n')
            batch_size = 100
            for i in range(0, len(lines), batch_size):
                batch = lines[i:i + batch_size]
                content = '\n'.join(batch)
                if content.strip():
                    chunk_id = str(uuid.uuid4())
                    chunks.append(DocumentChunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        content=content,
                        chunk_type='table_slice',
                        start_offset=i,
                        end_offset=min(i + batch_size, len(lines)),
                        line_start=i + 1,
                        line_end=min(i + batch_size, len(lines))
                    ))
            if chunks:
                return chunks

        # Default: sliding window with section detection
        sections = self._split_by_sections(text)
        if len(sections) > 1:
            for section_title, section_content in sections:
                if not section_content.strip():
                    continue
                # Further chunk large sections
                sub_chunks = self._sliding_window_chunks(
                    section_content, doc_id, chunk_size, overlap, section_title
                )
                chunks.extend(sub_chunks)
        else:
            chunks = self._sliding_window_chunks(text, doc_id, chunk_size, overlap)

        return chunks

    def _split_by_sections(self, text: str) -> List[Tuple[str, str]]:
        """Split markdown/text by headers."""
        header_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        matches = list(header_pattern.finditer(text))
        if not matches:
            return [('', text)]

        sections = []
        for i, match in enumerate(matches):
            title = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            sections.append((title, content))

        return sections

    def _sliding_window_chunks(self, text: str, doc_id: str,
                                chunk_size: int = 1000, overlap: int = 100,
                                section_title: str = '') -> List[DocumentChunk]:
        chunks = []
        words = text.split()
        if not words:
            return chunks

        i = 0
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            content = ' '.join(chunk_words)
            if content.strip():
                chunk_id = str(uuid.uuid4())
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    content=content,
                    chunk_type='text',
                    start_offset=i,
                    end_offset=min(i + chunk_size, len(words)),
                    section_title=section_title if section_title else None
                ))
            i += chunk_size - overlap

        return chunks

    def ingest_file(self, file_path: str, catalog_id: Optional[str] = None,
                    tags: Optional[List[str]] = None) -> DocumentMetadata:
        """Ingest a single file and return its metadata."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        stat = path.stat()
        doc_id = str(uuid.uuid4())
        file_type = self.get_file_type(file_path)
        checksum = self.compute_checksum(file_path)

        text, extra_meta = self.extract_text(file_path)
        word_count = len(text.split()) if text else 0

        title = extra_meta.get('title', '') or path.stem
        author = extra_meta.get('author', '')
        page_count = extra_meta.get('page_count', 0)

        now = datetime.datetime.utcnow().isoformat()
        meta = DocumentMetadata(
            doc_id=doc_id,
            file_path=str(path.resolve()),
            title=title,
            file_type=file_type,
            size_bytes=stat.st_size,
            created_at=datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified_at=datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            ingested_at=now,
            checksum=checksum,
            tags=tags or [],
            catalog_id=catalog_id,
            folder_path=str(path.parent),
            word_count=word_count,
            page_count=page_count,
            author=author,
        )

        return meta, text

    def scan_directory(self, directory: str, recursive: bool = True) -> List[str]:
        """Scan directory for supported files."""
        path = Path(directory)
        files = []

        if recursive:
            for f in path.rglob('*'):
                if f.is_file() and f.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    files.append(str(f))
        else:
            for f in path.iterdir():
                if f.is_file() and f.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    files.append(str(f))

        return files


# ============================================================
# Embedding Manager
# ============================================================

class EmbeddingManager:
    """Manages text embeddings for semantic search."""

    def __init__(self, model: str = "text-embedding-3-small", provider: str = "openai"):
        self.model = model
        self.provider = provider
        self._client = None

    def _get_client(self):
        if self._client is None:
            if self.provider == "openai" and HAS_OPENAI:
                self._client = openai.OpenAI()
            elif self.provider == "anthropic" and HAS_ANTHROPIC:
                self._client = anthropic.Anthropic()
        return self._client

    def embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text."""
        client = self._get_client()
        if client is None:
            return self._fallback_embedding(text)

        try:
            if self.provider == "openai":
                response = client.embeddings.create(
                    model=self.model,
                    input=text[:8000]
                )
                return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Embedding error: {e}")
            return self._fallback_embedding(text)

        return self._fallback_embedding(text)

    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for a batch of texts."""
        client = self._get_client()
        if client is None:
            return [self._fallback_embedding(t) for t in texts]

        try:
            if self.provider == "openai":
                truncated = [t[:8000] for t in texts]
                response = client.embeddings.create(
                    model=self.model,
                    input=truncated
                )
                return [item.embedding for item in response.data]
        except Exception as e:
            logger.warning(f"Batch embedding error: {e}")

        return [self._fallback_embedding(t) for t in texts]

    def _fallback_embedding(self, text: str) -> List[float]:
        """Simple TF-IDF-like fallback embedding."""
        if not HAS_NUMPY:
            return []
        words = re.findall(r'\w+', text.lower())
        vocab = sorted(set(words))[:512]
        word_idx = {w: i for i, w in enumerate(vocab)}
        vec = np.zeros(512)
        for w in words:
            if w in word_idx:
                vec[word_idx[w]] += 1
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        if HAS_NUMPY:
            va = np.array(a)
            vb = np.array(b)
            norm_a = np.linalg.norm(va)
            norm_b = np.linalg.norm(vb)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(np.dot(va, vb) / (norm_a * norm_b))
        else:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)


# ============================================================
# Search Engine
# ============================================================

class SearchEngine:
    """Handles lexical and semantic search over the knowledge base."""

    def __init__(self, db: Database, embedding_manager: Optional[EmbeddingManager] = None):
        self.db = db
        self.embedding_manager = embedding_manager

    def lexical_search(self, query: str, limit: int = 20,
                       filter_tags: Optional[List[str]] = None,
                       filter_catalogs: Optional[List[str]] = None,
                       filter_file_types: Optional[List[str]] = None) -> List[SearchResult]:
        """Full-text search using SQLite FTS5."""
        results = []

        # Clean query for FTS5
        clean_query = re.sub(r'[^\w\s]', ' ', query).strip()
        if not clean_query:
            return results

        fts_query = ' OR '.join(f'"{w}"' for w in clean_query.split() if w)

        try:
            sql = """
                SELECT c.chunk_id, c.doc_id, c.content, c.chunk_type,
                       c.page_num, c.line_start, c.line_end, c.section_title,
                       c.start_offset, c.end_offset,
                       d.file_path, d.title, d.file_type,
                       bm25(chunks_fts) as score
                FROM chunks_fts
                JOIN chunks c ON chunks_fts.chunk_id = c.chunk_id
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE chunks_fts MATCH ?
            """
            params = [fts_query]

            if filter_tags:
                placeholders = ','.join('?' * len(filter_tags))
                sql += f" AND c.doc_id IN (SELECT doc_id FROM document_tags WHERE tag IN ({placeholders}))"
                params.extend(filter_tags)

            if filter_catalogs:
                placeholders = ','.join('?' * len(filter_catalogs))
                sql += f" AND d.catalog_id IN ({placeholders})"
                params.extend(filter_catalogs)

            if filter_file_types:
                placeholders = ','.join('?' * len(filter_file_types))
                sql += f" AND d.file_type IN ({placeholders})"
                params.extend(filter_file_types)

            sql += " ORDER BY score LIMIT ?"
            params.append(limit)

            rows = self.db.fetchall(sql, tuple(params))
            for row in rows:
                results.append(SearchResult(
                    doc_id=row['doc_id'],
                    chunk_id=row['chunk_id'],
                    file_path=row['file_path'],
                    title=row['title'],
                    content=row['content'],
                    score=abs(float(row['score'])),
                    match_type='lexical',
                    chunk_type=row['chunk_type'],
                    page_num=row['page_num'],
                    line_start=row['line_start'],
                    line_end=row['line_end'],
                    section_title=row['section_title']
                ))
        except Exception as e:
            logger.warning(f"FTS search error: {e}")
            # Fallback to LIKE search
            results = self._like_search(query, limit, filter_tags, filter_catalogs, filter_file_types)

        return results

    def _like_search(self, query: str, limit: int,
                     filter_tags: Optional[List[str]] = None,
                     filter_catalogs: Optional[List[str]] = None,
                     filter_file_types: Optional[List[str]] = None) -> List[SearchResult]:
        """Fallback LIKE-based search."""
        results = []
        words = query.lower().split()
        if not words:
            return results

        sql = """
            SELECT c.chunk_id, c.doc_id, c.content, c.chunk_type,
                   c.page_num, c.line_start, c.line_end, c.section_title,
                   d.file_path, d.title, d.file_type
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 1=1
        """
        params = []

        like_clauses = ' AND '.join(f"LOWER(c.content) LIKE ?" for _ in words)
        if like_clauses:
            sql += f" AND ({like_clauses})"
            params.extend([f'%{w}%' for w in words])

        sql += f" LIMIT {limit}"

        rows = self.db.fetchall(sql, tuple(params))
        for row in rows:
            content = row['content']
            score = sum(content.lower().count(w) for w in words)
            results.append(SearchResult(
                doc_id=row['doc_id'],
                chunk_id=row['chunk_id'],
                file_path=row['file_path'],
                title=row['title'],
                content=content,
                score=float(score),
                match_type='lexical',
                chunk_type=row['chunk_type'],
                page_num=row['page_num'],
                line_start=row['line_start'],
                line_end=row['line_end'],
                section_title=row['section_title']
            ))

        return results

    def semantic_search(self, query: str, limit: int = 20,
                        filter_tags: Optional[List[str]] = None,
                        filter_catalogs: Optional[List[str]] = None) -> List[SearchResult]:
        """Semantic search using embeddings."""
        if self.embedding_manager is None:
            return []

        query_embedding = self.embedding_manager.embed_text(query)
        if not query_embedding:
            return []

        # Load all embeddings and compute similarity
        rows = self.db.fetchall("""
            SELECT ce.chunk_id, ce.embedding, ce.embedding_dim,
                   c.doc_id, c.content, c.chunk_type,
                   c.page_num, c.line_start, c.line_end, c.section_title,
                   d.file_path, d.title
            FROM chunk_embeddings ce
            JOIN chunks c ON ce.chunk_id = c.chunk_id
            JOIN documents d ON c.doc_id = d.doc_id
        """)

        scored = []
        for row in rows:
            try:
                emb_bytes = row['embedding']
                if emb_bytes and HAS_NUMPY:
                    emb = np.frombuffer(emb_bytes, dtype=np.float32).tolist()
                    sim = self.embedding_manager.cosine_similarity(query_embedding, emb)
                    scored.append((sim, row))
            except Exception:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, row in scored[:limit]:
            results.append(SearchResult(
                doc_id=row['doc_id'],
                chunk_id=row['chunk_id'],
                file_path=row['file_path'],
                title=row['title'],
                content=row['content'],
                score=sim,
                match_type='semantic',
                chunk_type=row['chunk_type'],
                page_num=row['page_num'],
                line_start=row['line_start'],
                line_end=row['line_end'],
                section_title=row['section_title']
            ))

        return results

    def hybrid_search(self, query: str, limit: int = 20,
                      lexical_weight: float = 0.6, semantic_weight: float = 0.4,
                      filter_tags: Optional[List[str]] = None,
                      filter_catalogs: Optional[List[str]] = None,
                      filter_file_types: Optional[List[str]] = None,
                      source_quota: Optional[Dict[str, int]] = None) -> List[SearchResult]:
        """Hybrid search combining lexical and semantic results."""
        lexical = self.lexical_search(query, limit * 2, filter_tags, filter_catalogs, filter_file_types)
        semantic = self.semantic_search(query, limit * 2, filter_tags, filter_catalogs)

        # Normalize scores
        def normalize(results: List[SearchResult]) -> Dict[str, float]:
            if not results:
                return {}
            max_score = max(r.score for r in results) or 1.0
            return {r.chunk_id: r.score / max_score for r in results}

        lex_scores = normalize(lexical)
        sem_scores = normalize(semantic)

        # Merge
        all_chunks = {r.chunk_id: r for r in lexical + semantic}
        combined_scores = {}
        for chunk_id in all_chunks:
            l_score = lex_scores.get(chunk_id, 0.0)
            s_score = sem_scores.get(chunk_id, 0.0)
            combined_scores[chunk_id] = lexical_weight * l_score + semantic_weight * s_score

        sorted_chunks = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)

        results = []
        doc_counts: Dict[str, int] = defaultdict(int)

        for chunk_id, score in sorted_chunks:
            if len(results) >= limit:
                break
            result = all_chunks[chunk_id]

            if source_quota:
                quota = source_quota.get(result.doc_id, source_quota.get('default', 999))
                if doc_counts[result.doc_id] >= quota:
                    continue

            result.score = score
            result.match_type = 'hybrid'
            results.append(result)
            doc_counts[result.doc_id] += 1

        return results

    def rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Rerank results using cross-encoder or heuristics."""
        query_words = set(re.findall(r'\w+', query.lower()))

        def rerank_score(result: SearchResult) -> float:
            content_words = set(re.findall(r'\w+', result.content.lower()))
            overlap = len(query_words & content_words)
            coverage = overlap / len(query_words) if query_words else 0
            density = overlap / len(content_words) if content_words else 0
            return result.score * 0.5 + coverage * 0.3 + density * 0.2

        for r in results:
            r.score = rerank_score(r)

        results.sort(key=lambda x: x.score, reverse=True)
        return results


# ============================================================
# Relation Miner
# ============================================================

class RelationMiner:
    """Mines relations between documents."""

    def __init__(self, db: Database, embedding_manager: Optional[EmbeddingManager] = None):
        self.db = db
        self.embedding_manager = embedding_manager

    def mine_lexical_relations(self, doc_id: str, threshold: float = 0.3) -> List[Relation]:
        """Find documents with high lexical overlap."""
        relations = []

        # Get source document chunks
        source_chunks = self.db.fetchall(
            "SELECT content FROM chunks WHERE doc_id = ?", (doc_id,)
        )
        if not source_chunks:
            return relations

        source_text = ' '.join(c['content'] for c in source_chunks)
        source_words = Counter(re.findall(r'\w+', source_text.lower()))
        source_total = sum(source_words.values())

        # Get all other documents
        other_docs = self.db.fetchall(
            "SELECT doc_id FROM documents WHERE doc_id != ?", (doc_id,)
        )

        for other_doc in other_docs:
            other_id = other_doc['doc_id']
            other_chunks = self.db.fetchall(
                "SELECT content FROM chunks WHERE doc_id = ?", (other_id,)
            )
            if not other_chunks:
                continue

            other_text = ' '.join(c['content'] for c in other_chunks)
            other_words = Counter(re.findall(r'\w+', other_text.lower()))
            other_total = sum(other_words.values())

            # Jaccard similarity
            intersection = sum((source_words & other_words).values())
            union = source_total + other_total - intersection
            if union == 0:
                continue

            similarity = intersection / union
            if similarity >= threshold:
                relation = Relation(
                    relation_id=str(uuid.uuid4()),
                    source_doc_id=doc_id,
                    target_doc_id=other_id,
                    relation_type='similar_to',
                    confidence=similarity,
                    evidence=f"Lexical similarity: {similarity:.3f}",
                    created_at=datetime.datetime.utcnow().isoformat()
                )
                relations.append(relation)

        return relations

    def mine_citation_relations(self, doc_id: str) -> List[Relation]:
        """Find documents that reference other documents by filename or title."""
        relations = []

        source_chunks = self.db.fetchall(
            "SELECT content FROM chunks WHERE doc_id = ?", (doc_id,)
        )
        if not source_chunks:
            return relations

        source_text = ' '.join(c['content'] for c in source_chunks)

        all_docs = self.db.fetchall(
            "SELECT doc_id, title, file_path FROM documents WHERE doc_id != ?", (doc_id,)
        )

        for doc in all_docs:
            title = doc['title']
            filename = Path(doc['file_path']).name

            if title and len(title) > 3 and title.lower() in source_text.lower():
                relation = Relation(
                    relation_id=str(uuid.uuid4()),
                    source_doc_id=doc_id,
                    target_doc_id=doc['doc_id'],
                    relation_type='references',
                    confidence=0.8,
                    evidence=f"Title '{title}' found in source text",
                    created_at=datetime.datetime.utcnow().isoformat()
                )
                relations.append(relation)
            elif filename and filename.lower() in source_text.lower():
                relation = Relation(
                    relation_id=str(uuid.uuid4()),
                    source_doc_id=doc_id,
                    target_doc_id=doc['doc_id'],
                    relation_type='references',
                    confidence=0.7,
                    evidence=f"Filename '{filename}' found in source text",
                    created_at=datetime.datetime.utcnow().isoformat()
                )
                relations.append(relation)

        return relations

    def save_relations(self, relations: List[Relation]):
        """Save relations to database."""
        for rel in relations:
            try:
                self.db.execute("""
                    INSERT OR REPLACE INTO relations
                    (relation_id, source_doc_id, target_doc_id, relation_type, confidence, evidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (rel.relation_id, rel.source_doc_id, rel.target_doc_id,
                      rel.relation_type, rel.confidence, rel.evidence, rel.created_at))
            except Exception as e:
                logger.warning(f"Error saving relation: {e}")
        self.db.commit()

    def get_related_documents(self, doc_id: str,
                               relation_types: Optional[List[str]] = None) -> List[Relation]:
        """Get all relations for a document."""
        sql = """
            SELECT * FROM relations
            WHERE source_doc_id = ? OR target_doc_id = ?
        """
        params = [doc_id, doc_id]

        if relation_types:
            placeholders = ','.join('?' * len(relation_types))
            sql += f" AND relation_type IN ({placeholders})"
            params.extend(relation_types)

        rows = self.db.fetchall(sql, tuple(params))
        relations = []
        for row in rows:
            relations.append(Relation(
                relation_id=row['relation_id'],
                source_doc_id=row['source_doc_id'],
                target_doc_id=row['target_doc_id'],
                relation_type=row['relation_type'],
                confidence=row['confidence'],
                evidence=row['evidence'],
                created_at=row['created_at']
            ))
        return relations


# ============================================================
# Knowledge Base Manager
# ============================================================

class KnowledgeBase:
    """Core knowledge base management."""

    def __init__(self, base_path: str, db_path: Optional[str] = None,
                 use_embeddings: bool = False, embedding_provider: str = "openai"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        db_path = db_path or str(self.base_path / '.marginalia' / 'marginalia.db')
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.db = Database(db_path)
        self.ingester = FileIngester(str(self.base_path))

        self.embedding_manager = None
        if use_embeddings:
            self.embedding_manager = EmbeddingManager(provider=embedding_provider)

        self.search_engine = SearchEngine(self.db, self.embedding_manager)
        self.relation_miner = RelationMiner(self.db, self.embedding_manager)

    def ingest_file(self, file_path: str, catalog_id: Optional[str] = None,
                    tags: Optional[List[str]] = None,
                    generate_embeddings: bool = False) -> DocumentMetadata:
        """Ingest a file into the knowledge base."""
        path = Path(file_path)

        # Check if already ingested
        existing = self.db.fetchone(
            "SELECT doc_id, checksum FROM documents WHERE file_path = ?",
            (str(path.resolve()),)
        )

        checksum = self.ingester.compute_checksum(file_path)

        if existing and existing['checksum'] == checksum:
            logger.info(f"File unchanged, skipping: {file_path}")
            return self.get_document(existing['doc_id'])

        meta, text = self.ingester.ingest_file(file_path, catalog_id, tags)

        if existing:
            # Update existing
            meta.doc_id = existing['doc_id']
            self._update_document(meta, text, generate_embeddings)
        else:
            self._insert_document(meta, text, generate_embeddings)

        return meta

    def _insert_document(self, meta: DocumentMetadata, text: str,
                          generate_embeddings: bool = False):
        """Insert a new document into the database."""
        self.db.execute("""
            INSERT INTO documents
            (doc_id, file_path, title, file_type, size_bytes, created_at, modified_at,
             ingested_at, checksum, catalog_id, folder_path, language, word_count,
             page_count, author, description, custom_fields)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (meta.doc_id, meta.file_path, meta.title, meta.file_type, meta.size_bytes,
              meta.created_at, meta.modified_at, meta.ingested_at, meta.checksum,
              meta.catalog_id, meta.folder_path, meta.language, meta.word_count,
              meta.page_count, meta.author, meta.description,
              json.dumps(meta.custom_fields)))

        # Insert tags
        for tag in meta.tags:
            self._ensure_tag(tag)
            self.db.execute(
                "INSERT OR IGNORE INTO document_tags (doc_id, tag) VALUES (?, ?)",
                (meta.doc_id, tag)
            )

        # Insert chunks
        chunks = self.ingester.chunk_text(text, meta.doc_id, meta.file_type)
        self._insert_chunks(chunks, generate_embeddings)

        self.db.commit()
        logger.info(f"Ingested: {meta.file_path} ({len(chunks)} chunks)")

    def _update_document(self, meta: DocumentMetadata, text: str,
                          generate_embeddings: bool = False):
        """Update an existing document."""
        self.db.execute("""
            UPDATE documents SET
            title=?, file_type=?, size_bytes=?, modified_at=?, ingested_at=?,
            checksum=?, catalog_id=?, word_count=?, page_count=?, author=?,
            description=?, custom_fields=?
            WHERE doc_id=?
        """, (meta.title, meta.file_type, meta.size_bytes, meta.modified_at,
              meta.ingested_at, meta.checksum, meta.catalog_id, meta.word_count,
              meta.page_count, meta.author, meta.description,
              json.dumps(meta.custom_fields), meta.doc_id))

        # Delete old chunks and FTS entries
        self.db.execute("DELETE FROM chunks WHERE doc_id = ?", (meta.doc_id,))
        self.db.execute(
            "DELETE FROM chunks_fts WHERE doc_id = ?", (meta.doc_id,)
        )

        # Re-insert chunks
        chunks = self.ingester.chunk_text(text, meta.doc_id, meta.file_type)
        self._insert_chunks(chunks, generate_embeddings)

        self.db.commit()
        logger.info(f"Updated: {meta.file_path}")

    def _insert_chunks(self, chunks: List[DocumentChunk], generate_embeddings: bool = False):
        """Insert chunks into database."""
        for chunk in chunks:
            self.db.execute("""
                INSERT INTO chunks
                (chunk_id, doc_id, content, chunk_type, start_offset, end_offset,
                 page_num, line_start, line_end, section_title)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (chunk.chunk_id, chunk.doc_id, chunk.content, chunk.chunk_type,
                  chunk.start_offset, chunk.end_offset, chunk.page_num,
                  chunk.line_start, chunk.line_end, chunk.section_title))

            # Update FTS
            self.db.execute("""
                INSERT INTO chunks_fts (chunk_id, doc_id, content, section_title)
                VALUES (?, ?, ?, ?)
            """, (chunk.chunk_id, chunk.doc_id, chunk.content,
                  chunk.section_title or ''))

        if generate_embeddings and self.embedding_manager:
            texts = [c.content for c in chunks]
            embeddings = self.embedding_manager.embed_batch(texts)
            for chunk, emb in zip(chunks, embeddings):
                if emb and HAS_NUMPY:
                    import numpy as np
                    emb_bytes = np.array(emb, dtype=np.float32).tobytes()
                    self.db.execute("""
                        INSERT OR REPLACE INTO chunk_embeddings
                        (chunk_id, embedding, embedding_dim)
                        VALUES (?, ?, ?)
                    """, (chunk.chunk_id, emb_bytes, len(emb)))

    def _ensure_tag(self, tag: str):
        """Ensure a tag exists in the tags table."""
        self.db.execute("""
            INSERT OR IGNORE INTO tags (tag, created_at)
            VALUES (?, ?)
        """, (tag, datetime.datetime.utcnow().isoformat()))

    def ingest_directory(self, directory: str, recursive: bool = True,
                          catalog_id: Optional[str] = None,
                          tags: Optional[List[str]] = None,
                          generate_embeddings: bool = False) -> List[DocumentMetadata]:
        """Ingest all supported files in a directory."""
        files = self.ingester.scan_directory(directory, recursive)
        results = []
        for f in files:
            try:
                meta = self.ingest_file(f, catalog_id, tags, generate_embeddings)
                results.append(meta)
            except Exception as e:
                logger.error(f"Error ingesting {f}: {e}")
        return results

    def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        """Get document metadata by ID."""
        row = self.db.fetchone(
            "SELECT * FROM documents WHERE doc_id = ?", (doc_id,)
        )
        if not row:
            return None

        tags = [r['tag'] for r in self.db.fetchall(
            "SELECT tag FROM document_tags WHERE doc_id = ?", (doc_id,)
        )]

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
            language=row['language'],
            word_count=row['word_count'],
            page_count=row['page_count'],
            author=row['author'],
            description=row['description'],
            custom_fields=json.loads(row['custom_fields'] or '{}')
        )

    def get_document_chunks(self, doc_id: str) -> List[DocumentChunk]:
        """Get all chunks for a document."""
        rows = self.db.fetchall(
            "SELECT * FROM chunks WHERE doc_id = ? ORDER BY start_offset", (doc_id,)
        )
        return [DocumentChunk(
            chunk_id=row['chunk_id'],
            doc_id=row['doc_id'],
            content=row['content'],
            chunk_type=row['chunk_type'],
            start_offset=row['start_offset'],
            end_offset=row['end_offset'],
            page_num=row['page_num'],
            line_start=row['line_start'],
            line_end=row['line_end'],
            section_title=row['section_title']
        ) for row in rows]

    def read_file_window(self, doc_id: str, chunk_id: Optional[str] = None,
                          page_num: Optional[int] = None,
                          line_start: Optional[int] = None,
                          line_end: Optional[int] = None,
                          context_chunks: int = 1) -> str:
        """Read a specific window of a file."""
        doc = self.get_document(doc_id)
        if not doc:
            return ""

        if chunk_id:
            row = self.db.fetchone(
                "SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)
            )
            if not row:
                return ""

            # Get surrounding context
            all_chunks = self.db.fetchall(
                "SELECT * FROM chunks WHERE doc_id = ? ORDER BY start_offset",
                (doc_id,)
            )
            chunk_ids = [c['chunk_id'] for c in all_chunks]
            try:
                idx = chunk_ids.index(chunk_id)
            except ValueError:
                return row['content']

            start_idx = max(0, idx - context_chunks)
            end_idx = min(len(all_chunks), idx + context_chunks + 1)
            context = all_chunks[start_idx:end_idx]
            return '\n\n'.join(c['content'] for c in context)

        if page_num is not None:
            rows = self.db.fetchall(
                "SELECT content FROM chunks WHERE doc_id = ? AND page_num = ?",
                (doc_id, page_num)
            )
            return '\n\n'.join(r['content'] for r in rows)

        if line_start is not None:
            rows = self.db.fetchall("""
                SELECT content FROM chunks
                WHERE doc_id = ? AND line_start >= ? AND line_end <= ?
                ORDER BY line_start
            """, (doc_id, line_start, line_end or line_start + 50))
            return '\n'.join(r['content'] for r in rows)

        # Return full document
        chunks = self.get_document_chunks(doc_id)
        return '\n\n'.join(c.content for c in chunks)

    def add_tag(self, doc_id: str, tag: str):
        """Add a tag to a document."""
        self._ensure_tag(tag)
        self.db.execute(
            "INSERT OR IGNORE INTO document_tags (doc_id, tag) VALUES (?, ?)",
            (doc_id, tag)
        )
        self.db.commit()

    def remove_tag(self, doc_id: str, tag: str):
        """Remove a tag from a document."""
        self.db.execute(
            "DELETE FROM document_tags WHERE doc_id = ? AND tag = ?",
            (doc_id, tag)
        )
        self.db.commit()

    def list_tags(self) -> List[str]:
        """List all tags."""
        rows = self.db.fetchall("SELECT tag FROM tags ORDER BY tag")
        return [r['tag'] for r in rows]

    def get_documents_by_tag(self, tag: str) -> List[DocumentMetadata]:
        """Get all documents with a specific tag."""
        rows = self.db.fetchall(
            "SELECT doc_id FROM document_tags WHERE tag = ?", (tag,)
        )
        docs = []
        for row in rows:
            doc = self.get_document(row['doc_id'])
            if doc:
                docs.append(doc)
        return docs

    def create_catalog(self, name: str, description: str = '',
                        folder_patterns: Optional[List[str]] = None,
                        tags: Optional[List[str]] = None) -> Catalog:
        """Create a new catalog."""
        catalog = Catalog(
            catalog_id=str(uuid.uuid4()),
            name=name,
            description=description,
            folder_patterns=folder_patterns or [],
            tags=tags or [],
            created_at=datetime.datetime.utcnow().isoformat()
        )
        self.db.execute("""
            INSERT INTO catalogs (catalog_id, name, description, folder_patterns, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (catalog.catalog_id, catalog.name, catalog.description,
              json.dumps(catalog.folder_patterns), json.dumps(catalog.tags),
              catalog.created_at))
        self.db.commit()
        return catalog

    def get_catalog(self, catalog_id: str) -> Optional[Catalog]:
        """Get a catalog by ID."""
        row = self.db.fetchone(
            "SELECT * FROM catalogs WHERE catalog_id = ?", (catalog_id,)
        )
        if not row:
            return None
        return Catalog(
            catalog_id=row['catalog_id'],
            name=row['name'],
            description=row['description'],
            folder_patterns=json.loads(row['folder_patterns'] or '[]'),
            tags=json.loads(row['tags'] or '[]'),
            created_at=row['created_at'],
            doc_count=row['doc_count']
        )

    def list_catalogs(self) -> List[Catalog]:
        """List all catalogs."""
        rows = self.db.fetchall("SELECT * FROM catalogs ORDER BY name")
        catalogs = []
        for row in rows:
            count_row = self.db.fetchone(
                "SELECT COUNT(*) as cnt FROM documents WHERE catalog_id = ?",
                (row['catalog_id'],)
            )
            catalogs.append(Catalog(
                catalog_id=row['catalog_id'],
                name=row['name'],
                description=row['description'],
                folder_patterns=json.loads(row['folder_patterns'] or '[]'),
                tags=json.loads(row['tags'] or '[]'),
                created_at=row['created_at'],
                doc_count=count_row['cnt'] if count_row else 0
            ))
        return catalogs

    def create_view(self, name: str, description: str = '',
                    filter_tags: Optional[List[str]] = None,
                    filter_catalogs: Optional[List[str]] = None,
                    filter_file_types: Optional[List[str]] = None,
                    sort_by: str = 'modified_at',
                    sort_order: str = 'desc') -> View:
        """Create a named view."""
        view = View(
            view_id=str(uuid.uuid4()),
            name=name,
            description=description,
            filter_tags=filter_tags or [],
            filter_catalogs=filter_catalogs or [],
            filter_file_types=filter_file_types or [],
            sort_by=sort_by,
            sort_order=sort_order,
            created_at=datetime.datetime.utcnow().isoformat()
        )
        self.db.execute("""
            INSERT INTO views
            (view_id, name, description, filter_tags, filter_catalogs,
             filter_file_types, sort_by, sort_order, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (view.view_id, view.name, view.description,
              json.dumps(view.filter_tags), json.dumps(view.filter_catalogs),
              json.dumps(view.filter_file_types), view.sort_by, view.sort_order,
              view.created_at))
        self.db.commit()
        return view

    def get_view_documents(self, view_id: str) -> List[DocumentMetadata]:
        """Get documents matching a view's filters."""
        row = self.db.fetchone(
            "SELECT * FROM views WHERE view_id = ?", (view_id,)
        )
        if not row:
            return []

        filter_tags = json.loads(row['filter_tags'] or '[]')
        filter_catalogs = json.loads(row['filter_catalogs'] or '[]')
        filter_file_types = json.loads(row['filter_file_types'] or '[]')
        sort_by = row['sort_by']
        sort_order = row['sort_order']

        sql = "SELECT DISTINCT d.doc_id FROM documents d"
        params = []
        conditions = []

        if filter_tags:
            sql += " JOIN document_tags dt ON d.doc_id = dt.doc_id"
            placeholders = ','.join('?' * len(filter_tags))
            conditions.append(f"dt.tag IN ({placeholders})")
            params.extend(filter_tags)

        if filter_catalogs:
            placeholders = ','.join('?' * len(filter_catalogs))
            conditions.append(f"d.catalog_id IN ({placeholders})")
            params.extend(filter_catalogs)

        if filter_file_types:
            placeholders = ','.join('?' * len(filter_file_types))
            conditions.append(f"d.file_type IN ({placeholders})")
            params.extend(filter_file_types)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        valid_sort = {'modified_at', 'created_at', 'title', 'size_bytes', 'word_count'}
        if sort_by not in valid_sort:
            sort_by = 'modified_at'
        sort_order = 'DESC' if sort_order.lower() == 'desc' else 'ASC'
        sql += f" ORDER BY d.{sort_by} {sort_order}"

        rows = self.db.fetchall(sql, tuple(params))
        docs = []
        for r in rows:
            doc = self.get_document(r['doc_id'])
            if doc:
                docs.append(doc)
        return docs

    def add_journal_entry(self, content: str, date: Optional[str] = None,
                           tags: Optional[List[str]] = None,
                           linked_doc_ids: Optional[List[str]] = None) -> JournalEntry:
        """Add a journal entry."""
        now = datetime.datetime.utcnow().isoformat()
        entry = JournalEntry(
            entry_id=str(uuid.uuid4()),
            date=date or now[:10],
            content=content,
            tags=tags or [],
            linked_doc_ids=linked_doc_ids or [],
            created_at=now
        )
        self.db.execute("""
            INSERT INTO journal_entries
            (entry_id, date, content, tags, linked_doc_ids, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (entry.entry_id, entry.date, entry.content,
              json.dumps(entry.tags), json.dumps(entry.linked_doc_ids),
              entry.created_at))
        self.db.commit()
        return entry

    def get_journal_entries(self, date: Optional[str] = None,
                             tags: Optional[List[str]] = None) -> List[JournalEntry]:
        """Get journal entries."""
        sql = "SELECT * FROM journal_entries WHERE 1=1"
        params = []

        if date:
            sql += " AND date = ?"
            params.append(date)

        sql += " ORDER BY created_at DESC"

        rows = self.db.fetchall(sql, tuple(params))
        entries = []
        for row in rows:
            entry = JournalEntry(
                entry_id=row['entry_id'],
                date=row['date'],
                content=row['content'],
                tags=json.loads(row['tags'] or '[]'),
                linked_doc_ids=json.loads(row['linked_doc_ids'] or '[]'),
                created_at=row['created_at']
            )
            if tags:
                if not any(t in entry.tags for t in tags):
                    continue
            entries.append(entry)
        return entries

    def save_investigation_note(self, note: InvestigationNote):
        """Save an investigation note."""
        self.db.execute("""
            INSERT OR REPLACE INTO investigation_notes
            (note_id, query, answer, citations, created_at, tags,
             follow_up_questions, related_note_ids)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (note.note_id, note.query, note.answer,
              json.dumps([asdict(c) for c in note.citations]),
              note.created_at, json.dumps(note.tags),
              json.dumps(note.follow_up_questions),
              json.dumps(note.related_note_ids)))
        self.db.commit()

    def get_investigation_notes(self, query: Optional[str] = None,
                                  tags: Optional[List[str]] = None,
                                  limit: int = 50) -> List[InvestigationNote]:
        """Get investigation notes."""
        sql = "SELECT * FROM investigation_notes WHERE 1=1"
        params = []

        if query:
            sql += " AND (query LIKE ? OR answer LIKE ?)"
            params.extend([f'%{query}%', f'%{query}%'])

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = self.db.fetchall(sql, tuple(params))
        notes = []
        for row in rows:
            citations_data = json.loads(row['citations'] or '[]')
            citations = [Citation(**c) for c in citations_data]
            note = InvestigationNote(
                note_id=row['note_id'],
                query=row['query'],
                answer=row['answer'],
                citations=citations,
                created_at=row['created_at'],
                tags=json.loads(row['tags'] or '[]'),
                follow_up_questions=json.loads(row['follow_up_questions'] or '[]'),
                related_note_ids=json.loads(row['related_note_ids'] or '[]')
            )
            if tags:
                if not any(t in note.tags for t in tags):
                    continue
            notes.append(note)
        return notes

    def list_documents(self, limit: int = 100, offset: int = 0,
                        file_type: Optional[str] = None) -> List[DocumentMetadata]:
        """List all documents."""
        sql = "SELECT doc_id FROM documents WHERE 1=1"
        params = []

        if file_type:
            sql += " AND file_type = ?"
            params.append(file_type)

        sql += f" ORDER BY ingested_at DESC LIMIT {limit} OFFSET {offset}"

        rows = self.db.fetchall(sql, tuple(params))
        docs = []
        for row in rows:
            doc = self.get_document(row['doc_id'])
            if doc:
                docs.append(doc)
        return docs

    def delete_document(self, doc_id: str):
        """Delete a document from the knowledge base."""
        self.db.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        self.db.commit()

    def update_document_metadata(self, doc_id: str, **kwargs):
        """Update document metadata fields."""
        allowed = {'title', 'description', 'author', 'language', 'catalog_id'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return

        set_clause = ', '.join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [doc_id]
        self.db.execute(
            f"UPDATE documents SET {set_clause} WHERE doc_id = ?",
            tuple(values)
        )
        self.db.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        stats = {}

        row = self.db.fetchone("SELECT COUNT(*) as cnt FROM documents")
        stats['total_documents'] = row['cnt'] if row else 0

        row = self.db.fetchone("SELECT COUNT(*) as cnt FROM chunks")
        stats['total_chunks'] = row['cnt'] if row else 0

        row = self.db.fetchone("SELECT COUNT(*) as cnt FROM tags")
        stats['total_tags'] = row['cnt'] if row else 0

        row = self.db.fetchone("SELECT COUNT(*) as cnt FROM catalogs")
        stats['total_catalogs'] = row['cnt'] if row else 0

        row = self.db.fetchone("SELECT COUNT(*) as cnt FROM investigation_notes")
        stats['total_notes'] = row['cnt'] if row else 0

        row = self.db.fetchone("SELECT COUNT(*) as cnt FROM relations")
        stats['total_relations'] = row['cnt'] if row else 0

        rows = self.db.fetchall(
            "SELECT file_type, COUNT(*) as cnt FROM documents GROUP BY file_type"
        )
        stats['by_file_type'] = {r['file_type']: r['cnt'] for r in rows}

        row = self.db.fetchone("SELECT SUM(size_bytes) as total FROM documents")
        stats['total_size_bytes'] = row['total'] if row and row['total'] else 0

        return stats


# ============================================================
# LLM Client
# ============================================================

class LLMClient:
    """Abstraction over LLM providers."""

    def __init__(self, provider: str = "openai", model: str = "gpt-4o",
                 api_key: Optional[str] = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.environ.get(
            'OPENAI_API_KEY' if provider == 'openai' else 'ANTHROPIC_API_KEY', ''
        )
        self._client = None

    def _get_client(self):
        if self._client is None:
            if self.provider == "openai" and HAS_OPENAI:
                self._client = openai.OpenAI(api_key=self.api_key or None)
            elif self.provider == "anthropic" and HAS_ANTHROPIC:
                self._client = anthropic.Anthropic(api_key=self.api_key or None)
        return self._client

    def complete(self, messages: List[Dict[str, str]],
                 max_tokens: int = 4096,
                 temperature: float = 0.3) -> str:
        """Generate a completion."""
        client = self._get_client()

        if client is None:
            return self._mock_completion(messages)

        try:
            if self.provider == "openai":
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return response.choices[0].message.content or ""

            elif self.provider == "anthropic":
                system_msg = next(
                    (m['content'] for m in messages if m['role'] == 'system'), ''
                )
                user_messages = [m for m in messages if m['role'] != 'system']
                response = client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_msg,
                    messages=user_messages
                )
                return response.content[0].text if response.content else ""

        except Exception as e:
            logger.error(f"LLM completion error: {e}")
            return f"[LLM Error: {e}]"

        return self._mock_completion(messages)

    def _mock_completion(self, messages: List[Dict[str, str]]) -> str:
        """Mock completion for testing without API keys."""
        last_user = next(
            (m['content'] for m in reversed(messages) if m['role'] == 'user'), ''
        )
        return f"[Mock response to: {last_user[:100]}...]"


# ============================================================
# Research Agent
# ============================================================

class ResearchAgent:
    """LLM-powered research agent for the knowledge base."""

    SYSTEM_PROMPT = """You are Marginalia, a research assistant for a personal knowledge base.
Your role is to help users find, synthesize, and understand information from their documents.

When answering questions:
1. Base your answers on the provided document excerpts
2. Always cite your sources with specific references (document title, page/section/line)
3. Be precise and acknowledge uncertainty when the documents don't fully address the question
4. Identify connections between different documents when relevant
5. Suggest follow-up questions that might deepen the investigation

Format citations as: [Source: <title>, <location>]
"""

    def __init__(self, knowledge_base: KnowledgeBase, llm_client: LLMClient,
                 max_context_chunks: int = 10, use_reranking: bool = True,
                 use_hybrid_search: bool = False):
        self.kb = knowledge_base
        self.llm = llm_client
        self.max_context_chunks = max_context_chunks
        self.use_reranking = use_reranking
        self.use_hybrid_search = use_hybrid_search
        self.conversation_history: List[Dict[str, str]] = []

    def search_and_retrieve(self, query: str,
                             filter_tags: Optional[List[str]] = None,
                             filter_catalogs: Optional[List[str]] = None,
                             filter_file_types: Optional[List[str]] = None,
                             source_quota: Optional[Dict[str, int]] = None) -> List[SearchResult]:
        """Search for relevant content."""
        if self.use_hybrid_search:
            results = self.kb.search_engine.hybrid_search(
                query,
                limit=self.max_context_chunks * 2,
                filter_tags=filter_tags,
                filter_catalogs=filter_catalogs,
                filter_file_types=filter_file_types,
                source_quota=source_quota
            )
        else:
            results = self.kb.search_engine.lexical_search(
                query,
                limit=self.max_context_chunks * 2,
                filter_tags=filter_tags,
                filter_catalogs=filter_catalogs,
                filter_file_types=filter_file_types
            )

        if self.use_reranking and results:
            results = self.kb.search_engine.rerank(query, results)

        return results[:self.max_context_chunks]

    def read_source_windows(self, results: List[SearchResult]) -> List[Tuple[SearchResult, str]]:
        """Read the actual file windows for search results."""
        windows = []
        for result in results:
            window = self.kb.read_file_window(
                result.doc_id,
                chunk_id=result.chunk_id,
                context_chunks=1
            )
            windows.append((result, window))
        return windows

    def build_context(self, windows: List[Tuple[SearchResult, str]]) -> str:
        """Build context string from source windows."""
        parts = []
        for result, window in windows:
            location = self._format_location(result)
            parts.append(
                f"--- Document: {result.title} | {location} ---\n{window}\n"
            )
        return '\n'.join(parts)

    def _format_location(self, result: SearchResult) -> str:
        """Format location string for a search result."""
        parts = []
        if result.page_num:
            parts.append(f"Page {result.page_num}")
        if result.line_start:
            parts.append(f"Lines {result.line_start}-{result.line_end or result.line_start}")
        if result.section_title:
            parts.append(f"Section: {result.section_title}")
        if not parts:
            parts.append(f"File: {Path(result.file_path).name}")
        return ', '.join(parts)

    def extract_citations(self, answer: str,
                           results: List[SearchResult]) -> List[Citation]:
        """Extract citations from the answer."""
        citations = []
        seen_chunks = set()

        for result in results:
            if result.chunk_id in seen_chunks:
                continue

            # Check if this source is referenced in the answer
            title_mentioned = result.title.lower() in answer.lower()
            file_mentioned = Path(result.file_path).name.lower() in answer.lower()

            if title_mentioned or file_mentioned or len(citations) < 3:
                excerpt = result.content[:200] + '...' if len(result.content) > 200 else result.content
                citations.append(Citation(
                    doc_id=result.doc_id,
                    file_path=result.file_path,
                    title=result.title,
                    chunk_id=result.chunk_id,
                    excerpt=excerpt,
                    page_num=result.page_num,
                    line_start=result.line_start,
                    line_end=result.line_end,
                    section_title=result.section_title
                ))
                seen_chunks.add(result.chunk_id)

        return citations

    def answer(self, query: str,
               filter_tags: Optional[List[str]] = None,
               filter_catalogs: Optional[List[str]] = None,
               filter_file_types: Optional[List[str]] = None,
               source_quota: Optional[Dict[str, int]] = None,
               save_note: bool = True,
               note_tags: Optional[List[str]] = None) -> InvestigationNote:
        """Answer a query using the knowledge base."""
        logger.info(f"Processing query: {query}")

        # Search and retrieve
        results = self.search_and_retrieve(
            query, filter_tags, filter_catalogs, filter_file_types, source_quota
        )

        if not results:
            answer_text = "I couldn't find any relevant documents in the knowledge base to answer this question."
            note = InvestigationNote(
                note_id=str(uuid.uuid4()),
                query=query,
                answer=answer_text,
                citations=[],
                created_at=datetime.datetime.utcnow().isoformat(),
                tags=note_tags or []
            )
            if save_note:
                self.kb.save_investigation_note(note)
            return note

        # Read source windows
        windows = self.read_source_windows(results)

        # Build context
        context = self.build_context(windows)

        # Build messages
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]

        # Add conversation history (last 4 turns)
        messages.extend(self.conversation_history[-8:])

        # Add current query with context
        user_message = f"""Please answer the following question based on the provided document excerpts.

Question: {query}

Document Excerpts:
{context}

Please provide a comprehensive answer with citations to the specific documents and locations."""

        messages.append({"role": "user", "content": user_message})

        # Generate answer
        answer_text = self.llm.complete(messages)

        # Extract citations
        citations = self.extract_citations(answer_text, results)

        # Generate follow-up questions
        follow_up_questions = self._generate_follow_ups(query, answer_text)

        # Find related notes
        related_notes = self.kb.get_investigation_notes(query=query[:50], limit=5)
        related_note_ids = [n.note_id for n in related_notes[:3]]

        # Create investigation note
        note = InvestigationNote(
            note_id=str(uuid.uuid4()),
            query=query,
            answer=answer_text,
            citations=citations,
            created_at=datetime.datetime.utcnow().isoformat(),
            tags=note_tags or [],
            follow_up_questions=follow_up_questions,
            related_note_ids=related_note_ids
        )

        # Save note
        if save_note:
            self.kb.save_investigation_note(note)

        # Update conversation history
        self.conversation_history.append({"role": "user", "content": query})
        self.conversation_history.append({"role": "assistant", "content": answer_text})

        return note

    def _generate_follow_ups(self, query: str, answer: str) -> List[str]:
        """Generate follow-up questions."""
        messages = [
            {"role": "system", "content": "Generate 3 concise follow-up research questions based on the query and answer. Return only the questions, one per line."},
            {"role": "user", "content": f"Query: {query}\n\nAnswer summary: {answer[:500]}"}
        ]
        response = self.llm.complete(messages, max_tokens=200)
        questions = [q.strip() for q in response.split('\n') if q.strip() and '?' in q]
        return questions[:3]

    def generate_report(self, topic: str, outline: Optional[List[str]] = None,
                         filter_tags: Optional[List[str]] = None,
                         filter_catalogs: Optional[List[str]] = None) -> str:
        """Generate a comprehensive report on a topic."""
        if not outline:
            # Generate outline first
            outline_messages = [
                {"role": "system", "content": "You are a research assistant. Generate a report outline."},
                {"role": "user", "content": f"Create a 5-section outline for a research report on: {topic}. Return only section titles, one per line."}
            ]
            outline_response = self.llm.complete(outline_messages, max_tokens=300)
            outline = [s.strip() for s in outline_response.split('\n') if s.strip()][:5]

        sections = []
        all_citations = []

        for section_title in outline:
            section_query = f"{topic}: {section_title}"
            results = self.search_and_retrieve(
                section_query, filter_tags, filter_catalogs
            )
            windows = self.read_source_windows(results)
            context = self.build_context(windows)

            section_messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Write the '{section_title}' section of a report on '{topic}'.\n\nRelevant sources:\n{context}\n\nWrite a detailed, well-cited section."}
            ]
            section_text = self.llm.complete(section_messages, max_tokens=1000)
            sections.append(f"## {section_title}\n\n{section_text}")

            citations = self.extract_citations(section_text, results)
            all_citations.extend(citations)

        # Build references section
        seen_docs = set()
        references = []
        for cit in all_citations:
            if cit.doc_id not in seen_docs:
                loc = self._format_citation_location(cit)
                references.append(f"- {cit.title} ({Path(cit.file_path).name}){loc}")
                seen_docs.add(cit.doc_id)

        report = f"# {topic}\n\n"
        report += '\n\n'.join(sections)
        if references:
            report += "\n\n## References\n\n" + '\n'.join(references)

        return report

    def _format_citation_location(self, citation: Citation) -> str:
        """Format citation location."""
        parts = []
        if citation.page_num:
            parts.append(f"p. {citation.page_num}")
        if citation.section_title:
            parts.append(f"§ {citation.section_title}")
        if citation.line_start:
            parts.append(f"ll. {citation.line_start}-{citation.line_end or citation.line_start}")
        return f" [{', '.join(parts)}]" if parts else ""

    def mine_relations(self, doc_id: Optional[str] = None,
                        all_docs: bool = False) -> List[Relation]:
        """Mine relations between documents."""
        relations = []

        if doc_id:
            lex_rels = self.kb.relation_miner.mine_lexical_relations(doc_id)
            cit_rels = self.kb.relation_miner.mine_citation_relations(doc_id)
            relations = lex_rels + cit_rels
            self.kb.relation_miner.save_relations(relations)
        elif all_docs:
            docs = self.kb.list_documents(limit=1000)
            for doc in docs:
                lex_rels = self.kb.relation_miner.mine_lexical_relations(doc.doc_id)
                cit_rels = self.kb.relation_miner.mine_citation_relations(doc.doc_id)
                doc_relations = lex_rels + cit_rels
                self.kb.relation_miner.save_relations(doc_relations)
                relations.extend(doc_relations)

        return relations

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []


# ============================================================
# CLI Interface
# ============================================================

class MarginaliaApp:
    """Main application class for Marginalia."""

    def __init__(self, base_path: str = "~/marginalia",
                 llm_provider: str = "openai",
                 llm_model: str = "gpt-4o",
                 use_embeddings: bool = False,
                 use_hybrid_search: bool = False,
                 use_reranking: bool = True):
        self.base_path = Path(base_path).expanduser()
        self.kb = KnowledgeBase(
            str(self.base_path),
            use_embeddings=use_embeddings,
            embedding_provider=llm_provider
        )
        self.llm = LLMClient(provider=llm_provider, model=llm_model)
        self.agent = ResearchAgent(
            self.kb, self.llm,
            use_hybrid_search=use_hybrid_search,
            use_reranking=use_reranking
        )

    def ingest(self, path: str, catalog: Optional[str] = None,
               tags: Optional[List[str]] = None,
               recursive: bool = True) -> Dict[str, Any]:
        """Ingest files or directories."""
        p = Path(path)
        catalog_id = None

        if catalog:
            catalogs = self.kb.list_catalogs()
            for c in catalogs:
                if c.name == catalog:
                    catalog_id = c.catalog_id
                    break
            if not catalog_id:
                cat = self.kb.create_catalog(catalog)
                catalog_id = cat.catalog_id

        if p.is_dir():
            docs = self.kb.ingest_directory(str(p), recursive, catalog_id, tags)
            return {
                'status': 'success',
                'ingested': len(docs),
                'documents': [{'id': d.doc_id, 'title': d.title, 'type': d.file_type} for d in docs]
            }
        elif p.is_file():
            doc = self.kb.ingest_file(str(p), catalog_id, tags)
            return {
                'status': 'success',
                'ingested': 1,
                'documents': [{'id': doc.doc_id, 'title': doc.title, 'type': doc.file_type}]
            }
        else:
            return {'status': 'error', 'message': f"Path not found: {path}"}

    def search(self, query: str, mode: str = 'lexical',
               limit: int = 10, tags: Optional[List[str]] = None,
               catalogs: Optional[List[str]] = None,
               file_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search the knowledge base."""
        catalog_ids = None
        if catalogs:
            all_cats = self.kb.list_catalogs()
            catalog_ids = [c.catalog_id for c in all_cats if c.name in catalogs]

        if mode == 'semantic':
            results = self.kb.search_engine.semantic_search(query, limit, tags, catalog_ids)
        elif mode == 'hybrid':
            results = self.kb.search_engine.hybrid_search(
                query, limit, filter_tags=tags, filter_catalogs=catalog_ids,
                filter_file_types=file_types
            )
        else:
            results = self.kb.search_engine.lexical_search(
                query, limit, tags, catalog_ids, file_types
            )

        return [{
            'doc_id': r.doc_id,
            'title': r.title,
            'file_path': r.file_path,
            'score': r.score,
            'match_type': r.match_type,
            'excerpt': r.content[:200],
            'location': self.agent._format_location(r)
        } for r in results]

    def ask(self, query: str, tags: Optional[List[str]] = None,
            catalogs: Optional[List[str]] = None,
            file_types: Optional[List[str]] = None,
            save: bool = True) -> Dict[str, Any]:
        """Ask a question and get a cited answer."""
        catalog_ids = None
        if catalogs:
            all_cats = self.kb.list_catalogs()
            catalog_ids = [c.catalog_id for c in all_cats if c.name in catalogs]

        note = self.agent.answer(
            query,
            filter_tags=tags,
            filter_catalogs=catalog_ids,
            filter_file_types=file_types,
            save_note=save
        )

        return {
            'note_id': note.note_id,
            'query': note.query,
            'answer': note.answer,
            'citations': [{
                'title': c.title,
                'file_path': c.file_path,
                'excerpt': c.excerpt,
                'location': self.agent._format_citation_location(c)
            } for c in note.citations],
            'follow_up_questions': note.follow_up_questions,
            'created_at': note.created_at
        }

    def report(self, topic: str, outline: Optional[List[str]] = None,
               tags: Optional[List[str]] = None,
               catalogs: Optional[List[str]] = None) -> str:
        """Generate a research report."""
        catalog_ids = None
        if catalogs:
            all_cats = self.kb.list_catalogs()
            catalog_ids = [c.catalog_id for c in all_cats if c.name in catalogs]

        return self.agent.generate_report(topic, outline, tags, catalog_ids)

    def journal(self, content: str, date: Optional[str] = None,
                tags: Optional[List[str]] = None,
                linked_docs: Optional[List[str]] = None) -> Dict[str, Any]:
        """Add a journal entry."""
        entry = self.kb.add_journal_entry(content, date, tags, linked_docs)
        return {
            'entry_id': entry.entry_id,
            'date': entry.date,
            'content': entry.content,
            'tags': entry.tags,
            'created_at': entry.created_at
        }

    def stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        return self.kb.get_stats()

    def tag(self, doc_id: str, tags: List[str], remove: bool = False):
        """Add or remove tags from a document."""
        for tag in tags:
            if remove:
                self.kb.remove_tag(doc_id, tag)
            else:
                self.kb.add_tag(doc_id, tag)

    def catalog(self, action: str, name: str, description: str = '',
                folder_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """Manage catalogs."""
        if action == 'create':
            cat = self.kb.create_catalog(name, description, folder_patterns)
            return asdict(cat)
        elif action == 'list':
            cats = self.kb.list_catalogs()
            return {'catalogs': [asdict(c) for c in cats]}
        else:
            return {'error': f"Unknown action: {action}"}

    def view(self, action: str, name: str = '', **kwargs) -> Dict[str, Any]:
        """Manage views."""
        if action == 'create':
            v = self.kb.create_view(name, **kwargs)
            return asdict(v)
        elif action == 'list':
            rows = self.kb.db.fetchall("SELECT * FROM views ORDER BY name")
            views = []
            for row in rows:
                views.append({
                    'view_id': row['view_id'],
                    'name': row['name'],
                    'description': row['description']
                })
            return {'views': views}
        elif action == 'show':
            rows = self.kb.db.fetchall(
                "SELECT view_id FROM views WHERE name = ?", (name,)
            )
            if not rows:
                return {'error': f"View not found: {name}"}
            docs = self.kb.get_view_documents(rows[0]['view_id'])
            return {
                'view': name,
                'documents': [{'id': d.doc_id, 'title': d.title, 'type': d.file_type} for d in docs]
            }
        else:
            return {'error': f"Unknown action: {action}"}

    def mine_relations(self, doc_id: Optional[str] = None,
                        all_docs: bool = False) -> Dict[str, Any]:
        """Mine document relations."""
        relations = self.agent.mine_relations(doc_id, all_docs)
        return {
            'relations_found': len(relations),
            'relations': [{
                'source': r.source_doc_id,
                'target': r.target_doc_id,
                'type': r.relation_type,
                'confidence': r.confidence,
                'evidence': r.evidence
            } for r in relations[:20]]
        }

    def notes(self, query: Optional[str] = None,
              tags: Optional[List[str]] = None,
              limit: int = 20) -> List[Dict[str, Any]]:
        """List investigation notes."""
        notes = self.kb.get_investigation_notes(query, tags, limit)
        return [{
            'note_id': n.note_id,
            'query': n.query,
            'answer_preview': n.answer[:200],
            'citations_count': len(n.citations),
            'tags': n.tags,
            'created_at': n.created_at
        } for n in notes]

    def read(self, doc_id: str, page: Optional[int] = None,
             lines: Optional[Tuple[int, int]] = None) -> str:
        """Read a document or specific window."""
        return self.kb.read_file_window(
            doc_id,
            page_num=page,
            line_start=lines[0] if lines else None,
            line_end=lines[1] if lines else None
        )

    def interactive(self):
        """Start an interactive research session."""
        print("Marginalia Research Agent")
        print("=" * 50)
        print("Commands: ask, search, ingest, stats, notes, quit")
        print("=" * 50)

        while True:
            try:
                user_input = input("\n> ").strip()
                if not user_input:
                    continue

                if user_input.lower() in ('quit', 'exit', 'q'):
                    print("Goodbye!")
                    break

                elif user_input.lower() == 'stats':
                    stats = self.stats()
                    print(json.dumps(stats, indent=2))

                elif user_input.lower().startswith('ingest '):
                    path = user_input[7:].strip()
                    result = self.ingest(path)
                    print(json.dumps(result, indent=2))

                elif user_input.lower().startswith('search '):
                    query = user_input[7:].strip()
                    results = self.search(query)
                    for r in results:
                        print(f"\n[{r['score']:.3f}] {r['title']}")
                        print(f"  Location: {r['location']}")
                        print(f"  {r['excerpt'][:150]}...")

                elif user_input.lower().startswith('notes'):
                    notes = self.notes(limit=10)
                    for n in notes:
                        print(f"\n[{n['created_at'][:10]}] {n['query'][:80]}")
                        print(f"  {n['answer_preview'][:100]}...")

                elif user_input.lower() == 'clear':
                    self.agent.clear_history()
                    print("Conversation history cleared.")

                else:
                    # Treat as a question
                    result = self.ask(user_input)
                    print(f"\n{result['answer']}")
                    if result['citations']:
                        print("\nSources:")
                        for c in result['citations']:
                            print(f"  - {c['title']}{c['location']}")
                    if result['follow_up_questions']:
                        print("\nFollow-up questions:")
                        for q in result['follow_up_questions']:
                            print(f"  ? {q}")

            except KeyboardInterrupt:
                print("\nInterrupted. Type 'quit' to exit.")
            except EOFError:
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                print(f"Error: {e}")


# ============================================================
# Entry Point
# ============================================================

def create_app(base_path: str = "~/marginalia",
               llm_provider: str = "openai",
               llm_model: str = "gpt-4o",
               use_embeddings: bool = False,
               use_hybrid_search: bool = False,
               use_reranking: bool = True) -> MarginaliaApp:
    """Create and return a Marginalia application instance."""
    return MarginaliaApp(
        base_path=base_path,
        llm_provider=llm_provider,
        llm_model=llm_model,
        use_embeddings=use_embeddings,
        use_hybrid_search=use_hybrid_search,
        use_reranking=use_reranking
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Marginalia - Personal Knowledge Management")
    parser.add_argument('--base-path', default='~/marginalia', help='Knowledge base path')
    parser.add_argument('--provider', default='openai', choices=['openai', 'anthropic'])
    parser.add_argument('--model', default='gpt-4o')
    parser.add_argument('--embeddings', action='store_true', help='Enable embeddings')
    parser.add_argument('--hybrid', action='store_true', help='Enable hybrid search')
    parser.add_argument('--no-rerank', action='store_true', help='Disable reranking')

    subparsers = parser.add_subparsers(dest='command')

    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Ingest files')
    ingest_parser.add_argument('path', help='File or directory to ingest')
    ingest_parser.add_argument('--catalog', help='Catalog name')
    ingest_parser.add_argument('--tags', nargs='+', help='Tags to apply')
    ingest_parser.add_argument('--no-recursive', action='store_true')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search knowledge base')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--mode', default='lexical', choices=['lexical', 'semantic', 'hybrid'])
    search_parser.add_argument('--limit', type=int, default=10)
    search_parser.add_argument('--tags', nargs='+')
    search_parser.add_argument('--catalogs', nargs='+')

    # Ask command
    ask_parser = subparsers.add_parser('ask', help='Ask a question')
    ask_parser.add_argument('query', help='Question to ask')
    ask_parser.add_argument('--tags', nargs='+')
    ask_parser.add_argument('--catalogs', nargs='+')
    ask_parser.add_argument('--no-save', action='store_true')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate a report')
    report_parser.add_argument('topic', help='Report topic')
    report_parser.add_argument('--tags', nargs='+')

    # Stats command
    subparsers.add_parser('stats', help='Show statistics')

    # Interactive command
    subparsers.add_parser('interactive', help='Start interactive session')

    # Journal command
    journal_parser = subparsers.add_parser('journal', help='Add journal entry')
    journal_parser.add_argument('content', help='Journal entry content')
    journal_parser.add_argument('--date', help='Entry date (YYYY-MM-DD)')
    journal_parser.add_argument('--tags', nargs='+')

    # Notes command
    notes_parser = subparsers.add_parser('notes', help='List investigation notes')
    notes_parser.add_argument('--query', help='Filter by query text')
    notes_parser.add_argument('--tags', nargs='+')
    notes_parser.add_argument('--limit', type=int, default=20)

    args = parser.parse_args()

    app = create_app(
        base_path=args.base_path,
        llm_provider=args.provider,
        llm_model=args.model,
        use_embeddings=args.embeddings,
        use_hybrid_search=args.hybrid,
        use_reranking=not args.no_rerank
    )

    if args.command == 'ingest':
        result = app.ingest(
            args.path,
            catalog=args.catalog,
            tags=args.tags,
            recursive=not args.no_recursive
        )
        print(json.dumps(result, indent=2))

    elif args.command == 'search':
        results = app.search(
            args.query,
            mode=args.mode,
            limit=args.limit,
            tags=args.tags,
            catalogs=args.catalogs
        )
        for r in results:
            print(f"\n[{r['score']:.3f}] {r['title']}")
            print(f"  {r['location']}")
            print(f"  {r['excerpt'][:200]}")

    elif args.command == 'ask':
        result = app.ask(
            args.query,
            tags=args.tags,
            catalogs=args.catalogs,
            save=not args.no_save
        )
        print(f"\n{result['answer']}")
        if result['citations']:
            print("\nSources:")
            for c in result['citations']:
                print(f"  - {c['title']}{c['location']}")

    elif args.command == 'report':
        report = app.report(args.topic, tags=args.tags)
        print(report)

    elif args.command == 'stats':
        stats = app.stats()
        print(json.dumps(stats, indent=2))

    elif args.command == 'interactive':
        app.interactive()

    elif args.command == 'journal':
        result = app.journal(args.content, date=args.date, tags=args.tags)
        print(json.dumps(result, indent=2))

    elif args.command == 'notes':
        notes = app.notes(query=args.query, tags=args.tags, limit=args.limit)
        for n in notes:
            print(f"\n[{n['created_at'][:10]}] {n['query']}")
            print(f"  {n['answer_preview'][:150]}...")

    else:
        app.interactive()