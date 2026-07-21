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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────

@dataclass
class DocumentRecord:
    """Represents a document in the knowledge base."""
    doc_id: str
    file_path: str
    title: str
    content_type: str
    file_size: int
    checksum: str
    created_at: str
    updated_at: str
    ingested_at: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    catalog_id: Optional[str] = None
    folder_path: str = ""
    language: str = "en"
    word_count: int = 0
    chunk_count: int = 0


@dataclass
class Chunk:
    """A text chunk from a document."""
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
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Catalog:
    """A named collection of documents."""
    catalog_id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Tag:
    """A tag for organizing documents."""
    tag_id: str
    name: str
    color: str = "#808080"
    description: str = ""
    parent_tag_id: Optional[str] = None
    created_at: str = ""


@dataclass
class View:
    """A saved search/filter configuration."""
    view_id: str
    name: str
    query: str
    filters: Dict[str, Any]
    sort_by: str
    created_at: str
    updated_at: str
    description: str = ""


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
class JournalEntry:
    """A journal/investigation note."""
    entry_id: str
    title: str
    content: str
    created_at: str
    updated_at: str
    tags: List[str] = field(default_factory=list)
    cited_docs: List[str] = field(default_factory=list)
    query: str = ""
    agent_session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """A search result with relevance scoring."""
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
    section_title: Optional[str] = None
    match_type: str = "lexical"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Citation:
    """A citation reference in an answer."""
    citation_id: str
    doc_id: str
    file_path: str
    title: str
    chunk_id: str
    excerpt: str
    page_number: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None


@dataclass
class AgentResponse:
    """Response from the research agent."""
    session_id: str
    query: str
    answer: str
    citations: List[Citation]
    sources_consulted: List[str]
    journal_entry_id: Optional[str]
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────
# Database Layer
# ─────────────────────────────────────────────

class Database:
    """SQLite database manager for Marginalia."""

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
        return self._local.conn

    @property
    def conn(self) -> sqlite3.Connection:
        return self._get_conn()

    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                file_path TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                content_type TEXT NOT NULL,
                file_size INTEGER,
                checksum TEXT,
                created_at TEXT,
                updated_at TEXT,
                ingested_at TEXT,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                catalog_id TEXT,
                folder_path TEXT DEFAULT '',
                language TEXT DEFAULT 'en',
                word_count INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0
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
                section_title TEXT,
                embedding BLOB,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
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

            CREATE TABLE IF NOT EXISTS tags (
                tag_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                color TEXT DEFAULT '#808080',
                description TEXT DEFAULT '',
                parent_tag_id TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS views (
                view_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                query TEXT,
                filters TEXT DEFAULT '{}',
                sort_by TEXT DEFAULT 'relevance',
                created_at TEXT,
                updated_at TEXT,
                description TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS relations (
                relation_id TEXT PRIMARY KEY,
                source_doc_id TEXT NOT NULL,
                target_doc_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                created_at TEXT,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (source_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (target_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                entry_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT,
                updated_at TEXT,
                tags TEXT DEFAULT '[]',
                cited_docs TEXT DEFAULT '[]',
                query TEXT DEFAULT '',
                agent_session_id TEXT,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS document_tags (
                doc_id TEXT NOT NULL,
                tag_id TEXT NOT NULL,
                PRIMARY KEY (doc_id, tag_id),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                doc_id UNINDEXED,
                content,
                section_title,
                tokenize='porter unicode61'
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                doc_id UNINDEXED,
                title,
                content_type UNINDEXED,
                tokenize='porter unicode61'
            );

            CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_page ON chunks(page_number);
            CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_doc_id);
            CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_doc_id);
            CREATE INDEX IF NOT EXISTS idx_documents_catalog ON documents(catalog_id);
            CREATE INDEX IF NOT EXISTS idx_documents_folder ON documents(folder_path);
        """)
        conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def executemany(self, sql: str, params_list: List[tuple]) -> sqlite3.Cursor:
        return self.conn.executemany(sql, params_list)

    def commit(self):
        self.conn.commit()

    def fetchall(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchone()


# ─────────────────────────────────────────────
# File Ingestion
# ─────────────────────────────────────────────

class FileIngester:
    """Handles ingestion of various file types."""

    SUPPORTED_EXTENSIONS = {
        '.txt', '.md', '.markdown', '.rst', '.org',
        '.pdf', '.docx', '.doc',
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp',
        '.xlsx', '.xls', '.csv', '.tsv',
        '.log', '.jsonl', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg',
        '.zip', '.tar', '.tar.gz', '.tgz', '.tar.bz2',
        '.html', '.htm', '.xml',
        '.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.go', '.rs',
        '.sh', '.bash', '.zsh',
    }

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def ingest_file(self, file_path: str) -> Tuple[str, List[Chunk], Dict[str, Any]]:
        """
        Ingest a file and return (full_text, chunks, metadata).
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = path.suffix.lower()
        content_type = self._detect_content_type(file_path)
        metadata = {}

        try:
            if ext in ('.txt', '.md', '.markdown', '.rst', '.org', '.html', '.htm'):
                text, metadata = self._ingest_text(file_path)
            elif ext == '.pdf':
                text, metadata = self._ingest_pdf(file_path)
            elif ext in ('.docx', '.doc'):
                text, metadata = self._ingest_docx(file_path)
            elif ext in ('.xlsx', '.xls'):
                text, metadata = self._ingest_spreadsheet(file_path)
            elif ext in ('.csv', '.tsv'):
                text, metadata = self._ingest_csv(file_path)
            elif ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'):
                text, metadata = self._ingest_image(file_path)
            elif ext in ('.zip', '.tar', '.tar.gz', '.tgz', '.tar.bz2'):
                text, metadata = self._ingest_archive(file_path)
            elif ext in ('.json', '.jsonl'):
                text, metadata = self._ingest_json(file_path)
            else:
                text, metadata = self._ingest_text(file_path)
        except Exception as e:
            logger.warning(f"Failed to ingest {file_path} with specific handler: {e}. Falling back to text.")
            text, metadata = self._ingest_text_fallback(file_path)

        doc_id = str(uuid.uuid4())
        chunks = self._create_chunks(doc_id, text, metadata)
        metadata['content_type'] = content_type
        metadata['word_count'] = len(text.split())
        return text, chunks, metadata

    def _detect_content_type(self, file_path: str) -> str:
        mime, _ = mimetypes.guess_type(file_path)
        return mime or 'application/octet-stream'

    def _ingest_text(self, file_path: str) -> Tuple[str, Dict]:
        """Ingest plain text / markdown files."""
        metadata = {}
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
        except Exception:
            with open(file_path, 'rb') as f:
                text = f.read().decode('utf-8', errors='replace')

        # Extract markdown frontmatter if present
        if file_path.endswith(('.md', '.markdown')):
            fm, text = self._extract_frontmatter(text)
            metadata.update(fm)

        return text, metadata

    def _extract_frontmatter(self, text: str) -> Tuple[Dict, str]:
        """Extract YAML frontmatter from markdown."""
        fm = {}
        if text.startswith('---'):
            end = text.find('---', 3)
            if end != -1:
                fm_text = text[3:end].strip()
                body = text[end+3:].strip()
                for line in fm_text.split('\n'):
                    if ':' in line:
                        k, _, v = line.partition(':')
                        fm[k.strip()] = v.strip()
                return fm, body
        return fm, text

    def _ingest_text_fallback(self, file_path: str) -> Tuple[str, Dict]:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read(), {}
        except Exception:
            return f"[Binary file: {file_path}]", {}

    def _ingest_pdf(self, file_path: str) -> Tuple[str, Dict]:
        """Ingest PDF files."""
        if not HAS_PYPDF:
            return self._ingest_text_fallback(file_path)

        metadata = {}
        pages = []
        try:
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                metadata['page_count'] = len(reader.pages)
                if reader.metadata:
                    for k, v in reader.metadata.items():
                        if k.startswith('/'):
                            metadata[k[1:].lower()] = str(v)
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    pages.append(f"[Page {i+1}]\n{page_text}")
        except Exception as e:
            logger.warning(f"PDF extraction error for {file_path}: {e}")
            return f"[PDF extraction failed: {e}]", metadata

        return '\n\n'.join(pages), metadata

    def _ingest_docx(self, file_path: str) -> Tuple[str, Dict]:
        """Ingest DOCX files."""
        if not HAS_DOCX:
            return self._ingest_text_fallback(file_path)

        metadata = {}
        try:
            doc = docx.Document(file_path)
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            # Extract tables
            for table in doc.tables:
                rows = []
                for row in table.rows:
                    rows.append('\t'.join(cell.text for cell in row.cells))
                paragraphs.append('\n'.join(rows))

            core_props = doc.core_properties
            if core_props.author:
                metadata['author'] = core_props.author
            if core_props.title:
                metadata['title'] = core_props.title
            if core_props.created:
                metadata['created'] = str(core_props.created)

            return '\n\n'.join(paragraphs), metadata
        except Exception as e:
            logger.warning(f"DOCX extraction error: {e}")
            return f"[DOCX extraction failed: {e}]", metadata

    def _ingest_spreadsheet(self, file_path: str) -> Tuple[str, Dict]:
        """Ingest Excel spreadsheets."""
        if not HAS_OPENPYXL:
            return self._ingest_text_fallback(file_path)

        metadata = {}
        sheets_text = []
        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            metadata['sheet_names'] = wb.sheetnames
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = []
                for row in ws.iter_rows(values_only=True):
                    row_text = '\t'.join(str(cell) if cell is not None else '' for cell in row)
                    if row_text.strip():
                        rows.append(row_text)
                if rows:
                    sheets_text.append(f"[Sheet: {sheet_name}]\n" + '\n'.join(rows))
            wb.close()
        except Exception as e:
            logger.warning(f"Spreadsheet extraction error: {e}")
            return f"[Spreadsheet extraction failed: {e}]", metadata

        return '\n\n'.join(sheets_text), metadata

    def _ingest_csv(self, file_path: str) -> Tuple[str, Dict]:
        """Ingest CSV/TSV files."""
        metadata = {}
        rows = []
        try:
            delimiter = '\t' if file_path.endswith('.tsv') else ','
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                import csv as csv_module
                reader = csv_module.reader(f, delimiter=delimiter)
                for i, row in enumerate(reader):
                    rows.append('\t'.join(row))
                    if i == 0:
                        metadata['headers'] = row
            metadata['row_count'] = len(rows)
        except Exception as e:
            logger.warning(f"CSV extraction error: {e}")
            return f"[CSV extraction failed: {e}]", metadata

        return '\n'.join(rows), metadata

    def _ingest_image(self, file_path: str) -> Tuple[str, Dict]:
        """Ingest image files (extract metadata, no OCR by default)."""
        metadata = {}
        text_parts = [f"[Image file: {Path(file_path).name}]"]

        if HAS_PIL:
            try:
                with Image.open(file_path) as img:
                    metadata['width'] = img.width
                    metadata['height'] = img.height
                    metadata['mode'] = img.mode
                    metadata['format'] = img.format
                    text_parts.append(f"Dimensions: {img.width}x{img.height}, Mode: {img.mode}, Format: {img.format}")

                    # Try to get EXIF data
                    if hasattr(img, '_getexif') and img._getexif():
                        exif = img._getexif()
                        if exif:
                            metadata['has_exif'] = True
            except Exception as e:
                logger.warning(f"Image metadata extraction error: {e}")

        return '\n'.join(text_parts), metadata

    def _ingest_archive(self, file_path: str) -> Tuple[str, Dict]:
        """Ingest archive files (list members, extract text from text members)."""
        metadata = {}
        text_parts = [f"[Archive: {Path(file_path).name}]"]
        members = []

        try:
            if file_path.endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zf:
                    members = zf.namelist()
                    metadata['member_count'] = len(members)
                    text_parts.append(f"Members ({len(members)}):")
                    for name in members[:100]:  # Limit listing
                        text_parts.append(f"  - {name}")
                        # Extract text from small text files
                        info = zf.getinfo(name)
                        if info.file_size < 100000 and self._is_text_member(name):
                            try:
                                content = zf.read(name).decode('utf-8', errors='replace')
                                text_parts.append(f"\n[Member: {name}]\n{content[:2000]}")
                            except Exception:
                                pass
            elif tarfile.is_tarfile(file_path):
                with tarfile.open(file_path, 'r:*') as tf:
                    members = tf.getnames()
                    metadata['member_count'] = len(members)
                    text_parts.append(f"Members ({len(members)}):")
                    for name in members[:100]:
                        text_parts.append(f"  - {name}")
                        if self._is_text_member(name):
                            try:
                                member = tf.getmember(name)
                                if member.size < 100000:
                                    f = tf.extractfile(member)
                                    if f:
                                        content = f.read().decode('utf-8', errors='replace')
                                        text_parts.append(f"\n[Member: {name}]\n{content[:2000]}")
                            except Exception:
                                pass
        except Exception as e:
            logger.warning(f"Archive extraction error: {e}")
            text_parts.append(f"[Archive extraction failed: {e}]")

        metadata['members'] = members[:200]
        return '\n'.join(text_parts), metadata

    def _is_text_member(self, name: str) -> bool:
        ext = Path(name).suffix.lower()
        return ext in ('.txt', '.md', '.py', '.js', '.json', '.yaml', '.yml', '.csv', '.log', '.rst', '.html')

    def _ingest_json(self, file_path: str) -> Tuple[str, Dict]:
        """Ingest JSON/JSONL files."""
        metadata = {}
        try:
            if file_path.endswith('.jsonl'):
                lines = []
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    for i, line in enumerate(f):
                        line = line.strip()
                        if line:
                            try:
                                obj = json.loads(line)
                                lines.append(json.dumps(obj, indent=2))
                            except Exception:
                                lines.append(line)
                metadata['line_count'] = len(lines)
                return '\n---\n'.join(lines), metadata
            else:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    data = json.load(f)
                return json.dumps(data, indent=2), metadata
        except Exception as e:
            return self._ingest_text_fallback(file_path)

    def _create_chunks(self, doc_id: str, text: str, metadata: Dict) -> List[Chunk]:
        """Split text into overlapping chunks."""
        chunks = []
        lines = text.split('\n')
        current_chunk_lines = []
        current_size = 0
        chunk_index = 0
        line_start = 0
        current_line = 0
        current_section = None
        char_offset = 0

        # Detect page markers
        page_pattern = re.compile(r'^\[Page (\d+)\]')
        section_pattern = re.compile(r'^#{1,6}\s+(.+)$')

        current_page = None

        for line_num, line in enumerate(lines):
            page_match = page_pattern.match(line)
            if page_match:
                current_page = int(page_match.group(1))

            section_match = section_pattern.match(line)
            if section_match:
                current_section = section_match.group(1)

            line_words = len(line.split())
            current_chunk_lines.append(line)
            current_size += line_words

            if current_size >= self.chunk_size:
                chunk_text = '\n'.join(current_chunk_lines)
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=chunk_text,
                    chunk_index=chunk_index,
                    start_offset=char_offset,
                    end_offset=char_offset + len(chunk_text),
                    page_number=current_page,
                    line_start=line_start,
                    line_end=line_num,
                    section_title=current_section,
                    metadata={}
                )
                chunks.append(chunk)
                chunk_index += 1

                # Overlap: keep last N words worth of lines
                overlap_lines = []
                overlap_size = 0
                for ol in reversed(current_chunk_lines):
                    ol_words = len(ol.split())
                    if overlap_size + ol_words <= self.chunk_overlap:
                        overlap_lines.insert(0, ol)
                        overlap_size += ol_words
                    else:
                        break

                char_offset += len(chunk_text) + 1
                line_start = line_num - len(overlap_lines) + 1
                current_chunk_lines = overlap_lines
                current_size = overlap_size

        # Final chunk
        if current_chunk_lines:
            chunk_text = '\n'.join(current_chunk_lines)
            if chunk_text.strip():
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=chunk_text,
                    chunk_index=chunk_index,
                    start_offset=char_offset,
                    end_offset=char_offset + len(chunk_text),
                    page_number=current_page,
                    line_start=line_start,
                    line_end=len(lines) - 1,
                    section_title=current_section,
                    metadata={}
                )
                chunks.append(chunk)

        return chunks if chunks else [Chunk(
            chunk_id=str(uuid.uuid4()),
            doc_id=doc_id,
            content=text[:self.chunk_size * 5],
            chunk_index=0,
            start_offset=0,
            end_offset=len(text),
            metadata={}
        )]


# ─────────────────────────────────────────────
# Catalog Manager
# ─────────────────────────────────────────────

class CatalogManager:
    """Manages catalogs, tags, views, and document organization."""

    def __init__(self, db: Database):
        self.db = db

    def create_catalog(self, name: str, description: str = "", tags: List[str] = None) -> Catalog:
        catalog = Catalog(
            catalog_id=str(uuid.uuid4()),
            name=name,
            description=description,
            created_at=datetime.datetime.utcnow().isoformat(),
            updated_at=datetime.datetime.utcnow().isoformat(),
            tags=tags or [],
        )
        self.db.execute(
            "INSERT INTO catalogs VALUES (?,?,?,?,?,?,?)",
            (catalog.catalog_id, catalog.name, catalog.description,
             catalog.created_at, catalog.updated_at,
             json.dumps(catalog.tags), json.dumps(catalog.metadata))
        )
        self.db.commit()
        return catalog

    def get_catalog(self, catalog_id: str) -> Optional[Catalog]:
        row = self.db.fetchone("SELECT * FROM catalogs WHERE catalog_id=?", (catalog_id,))
        if row:
            return self._row_to_catalog(row)
        return None

    def get_catalog_by_name(self, name: str) -> Optional[Catalog]:
        row = self.db.fetchone("SELECT * FROM catalogs WHERE name=?", (name,))
        if row:
            return self._row_to_catalog(row)
        return None

    def list_catalogs(self) -> List[Catalog]:
        rows = self.db.fetchall("SELECT * FROM catalogs ORDER BY name")
        return [self._row_to_catalog(r) for r in rows]

    def delete_catalog(self, catalog_id: str):
        self.db.execute("UPDATE documents SET catalog_id=NULL WHERE catalog_id=?", (catalog_id,))
        self.db.execute("DELETE FROM catalogs WHERE catalog_id=?", (catalog_id,))
        self.db.commit()

    def _row_to_catalog(self, row: sqlite3.Row) -> Catalog:
        return Catalog(
            catalog_id=row['catalog_id'],
            name=row['name'],
            description=row['description'] or '',
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}'),
        )

    def create_tag(self, name: str, color: str = "#808080", description: str = "",
                   parent_tag_id: Optional[str] = None) -> Tag:
        tag = Tag(
            tag_id=str(uuid.uuid4()),
            name=name,
            color=color,
            description=description,
            parent_tag_id=parent_tag_id,
            created_at=datetime.datetime.utcnow().isoformat(),
        )
        self.db.execute(
            "INSERT INTO tags VALUES (?,?,?,?,?,?)",
            (tag.tag_id, tag.name, tag.color, tag.description, tag.parent_tag_id, tag.created_at)
        )
        self.db.commit()
        return tag

    def get_tag_by_name(self, name: str) -> Optional[Tag]:
        row = self.db.fetchone("SELECT * FROM tags WHERE name=?", (name,))
        if row:
            return self._row_to_tag(row)
        return None

    def get_or_create_tag(self, name: str) -> Tag:
        tag = self.get_tag_by_name(name)
        if tag:
            return tag
        return self.create_tag(name)

    def list_tags(self) -> List[Tag]:
        rows = self.db.fetchall("SELECT * FROM tags ORDER BY name")
        return [self._row_to_tag(r) for r in rows]

    def _row_to_tag(self, row: sqlite3.Row) -> Tag:
        return Tag(
            tag_id=row['tag_id'],
            name=row['name'],
            color=row['color'],
            description=row['description'] or '',
            parent_tag_id=row['parent_tag_id'],
            created_at=row['created_at'],
        )

    def create_view(self, name: str, query: str, filters: Dict = None,
                    sort_by: str = "relevance", description: str = "") -> View:
        view = View(
            view_id=str(uuid.uuid4()),
            name=name,
            query=query,
            filters=filters or {},
            sort_by=sort_by,
            created_at=datetime.datetime.utcnow().isoformat(),
            updated_at=datetime.datetime.utcnow().isoformat(),
            description=description,
        )
        self.db.execute(
            "INSERT INTO views VALUES (?,?,?,?,?,?,?,?)",
            (view.view_id, view.name, view.query, json.dumps(view.filters),
             view.sort_by, view.created_at, view.updated_at, view.description)
        )
        self.db.commit()
        return view

    def list_views(self) -> List[View]:
        rows = self.db.fetchall("SELECT * FROM views ORDER BY name")
        return [self._row_to_view(r) for r in rows]

    def _row_to_view(self, row: sqlite3.Row) -> View:
        return View(
            view_id=row['view_id'],
            name=row['name'],
            query=row['query'] or '',
            filters=json.loads(row['filters'] or '{}'),
            sort_by=row['sort_by'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            description=row['description'] or '',
        )


# ─────────────────────────────────────────────
# Document Store
# ─────────────────────────────────────────────

class DocumentStore:
    """Manages document storage and retrieval."""

    def __init__(self, db: Database, base_path: str):
        self.db = db
        self.base_path = Path(base_path)
        self.ingester = FileIngester()

    def ingest_file(self, file_path: str, catalog_id: Optional[str] = None,
                    tags: List[str] = None, metadata: Dict = None) -> DocumentRecord:
        """Ingest a file into the knowledge base."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check if already ingested
        existing = self.get_document_by_path(str(path.resolve()))
        checksum = self._compute_checksum(file_path)

        if existing and existing.checksum == checksum:
            logger.info(f"File already ingested and unchanged: {file_path}")
            return existing

        # Ingest content
        text, chunks, file_metadata = self.ingester.ingest_file(file_path)

        if metadata:
            file_metadata.update(metadata)

        now = datetime.datetime.utcnow().isoformat()
        stat = path.stat()

        doc_id = existing.doc_id if existing else str(uuid.uuid4())
        title = file_metadata.get('title', path.stem)
        content_type = file_metadata.get('content_type', 'text/plain')
        folder_path = str(path.parent.resolve())

        doc = DocumentRecord(
            doc_id=doc_id,
            file_path=str(path.resolve()),
            title=title,
            content_type=content_type,
            file_size=stat.st_size,
            checksum=checksum,
            created_at=datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            updated_at=datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            ingested_at=now,
            tags=tags or [],
            metadata=file_metadata,
            catalog_id=catalog_id,
            folder_path=folder_path,
            word_count=file_metadata.get('word_count', 0),
            chunk_count=len(chunks),
        )

        # Set doc_id on chunks
        for chunk in chunks:
            chunk.doc_id = doc_id

        # Store in database
        if existing:
            self._update_document(doc)
            self._delete_chunks(doc_id)
        else:
            self._insert_document(doc)

        self._insert_chunks(chunks)
        self._update_fts(doc, chunks)

        logger.info(f"Ingested: {file_path} ({len(chunks)} chunks)")
        return doc

    def ingest_directory(self, dir_path: str, recursive: bool = True,
                         catalog_id: Optional[str] = None,
                         tags: List[str] = None) -> List[DocumentRecord]:
        """Ingest all supported files in a directory."""
        dir_path = Path(dir_path)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        docs = []
        pattern = '**/*' if recursive else '*'
        for file_path in dir_path.glob(pattern):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                # Check compound extensions
                name = file_path.name.lower()
                if (ext in self.ingester.SUPPORTED_EXTENSIONS or
                        name.endswith('.tar.gz') or name.endswith('.tar.bz2')):
                    try:
                        doc = self.ingest_file(str(file_path), catalog_id=catalog_id, tags=tags)
                        docs.append(doc)
                    except Exception as e:
                        logger.warning(f"Failed to ingest {file_path}: {e}")

        return docs

    def _compute_checksum(self, file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()

    def _insert_document(self, doc: DocumentRecord):
        self.db.execute(
            """INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (doc.doc_id, doc.file_path, doc.title, doc.content_type,
             doc.file_size, doc.checksum, doc.created_at, doc.updated_at,
             doc.ingested_at, json.dumps(doc.tags), json.dumps(doc.metadata),
             doc.catalog_id, doc.folder_path, doc.language,
             doc.word_count, doc.chunk_count)
        )
        self.db.commit()

    def _update_document(self, doc: DocumentRecord):
        self.db.execute(
            """UPDATE documents SET title=?, content_type=?, file_size=?, checksum=?,
               updated_at=?, ingested_at=?, tags=?, metadata=?, catalog_id=?,
               folder_path=?, word_count=?, chunk_count=?
               WHERE doc_id=?""",
            (doc.title, doc.content_type, doc.file_size, doc.checksum,
             doc.updated_at, doc.ingested_at, json.dumps(doc.tags),
             json.dumps(doc.metadata), doc.catalog_id, doc.folder_path,
             doc.word_count, doc.chunk_count, doc.doc_id)
        )
        self.db.commit()

    def _delete_chunks(self, doc_id: str):
        self.db.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        self.db.execute("DELETE FROM chunks_fts WHERE doc_id=?", (doc_id,))
        self.db.commit()

    def _insert_chunks(self, chunks: List[Chunk]):
        for chunk in chunks:
            self.db.execute(
                """INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (chunk.chunk_id, chunk.doc_id, chunk.content, chunk.chunk_index,
                 chunk.start_offset, chunk.end_offset, chunk.page_number,
                 chunk.line_start, chunk.line_end, chunk.section_title,
                 None,  # embedding stored separately
                 json.dumps(chunk.metadata))
            )
        self.db.commit()

    def _update_fts(self, doc: DocumentRecord, chunks: List[Chunk]):
        # Update documents FTS
        self.db.execute("DELETE FROM documents_fts WHERE doc_id=?", (doc.doc_id,))
        self.db.execute(
            "INSERT INTO documents_fts VALUES (?,?,?)",
            (doc.doc_id, doc.title, doc.content_type)
        )
        # Update chunks FTS
        self.db.execute("DELETE FROM chunks_fts WHERE doc_id=?", (doc.doc_id,))
        for chunk in chunks:
            self.db.execute(
                "INSERT INTO chunks_fts VALUES (?,?,?,?)",
                (chunk.chunk_id, chunk.doc_id, chunk.content, chunk.section_title or '')
            )
        self.db.commit()

    def get_document(self, doc_id: str) -> Optional[DocumentRecord]:
        row = self.db.fetchone("SELECT * FROM documents WHERE doc_id=?", (doc_id,))
        if row:
            return self._row_to_doc(row)
        return None

    def get_document_by_path(self, file_path: str) -> Optional[DocumentRecord]:
        row = self.db.fetchone("SELECT * FROM documents WHERE file_path=?", (file_path,))
        if row:
            return self._row_to_doc(row)
        return None

    def list_documents(self, catalog_id: Optional[str] = None,
                       tags: Optional[List[str]] = None,
                       limit: int = 100, offset: int = 0) -> List[DocumentRecord]:
        sql = "SELECT * FROM documents WHERE 1=1"
        params = []
        if catalog_id:
            sql += " AND catalog_id=?"
            params.append(catalog_id)
        sql += " ORDER BY ingested_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self.db.fetchall(sql, tuple(params))
        docs = [self._row_to_doc(r) for r in rows]

        if tags:
            docs = [d for d in docs if any(t in d.tags for t in tags)]

        return docs

    def delete_document(self, doc_id: str):
        self.db.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
        self.db.execute("DELETE FROM documents_fts WHERE doc_id=?", (doc_id,))
        self.db.commit()

    def get_chunks(self, doc_id: str) -> List[Chunk]:
        rows = self.db.fetchall(
            "SELECT * FROM chunks WHERE doc_id=? ORDER BY chunk_index",
            (doc_id,)
        )
        return [self._row_to_chunk(r) for r in rows]

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        row = self.db.fetchone("SELECT * FROM chunks WHERE chunk_id=?", (chunk_id,))
        if row:
            return self._row_to_chunk(row)
        return None

    def get_chunks_by_page(self, doc_id: str, page_number: int) -> List[Chunk]:
        rows = self.db.fetchall(
            "SELECT * FROM chunks WHERE doc_id=? AND page_number=? ORDER BY chunk_index",
            (doc_id, page_number)
        )
        return [self._row_to_chunk(r) for r in rows]

    def get_chunks_by_lines(self, doc_id: str, line_start: int, line_end: int) -> List[Chunk]:
        rows = self.db.fetchall(
            """SELECT * FROM chunks WHERE doc_id=?
               AND line_start <= ? AND line_end >= ?
               ORDER BY chunk_index""",
            (doc_id, line_end, line_start)
        )
        return [self._row_to_chunk(r) for r in rows]

    def _row_to_doc(self, row: sqlite3.Row) -> DocumentRecord:
        return DocumentRecord(
            doc_id=row['doc_id'],
            file_path=row['file_path'],
            title=row['title'],
            content_type=row['content_type'],
            file_size=row['file_size'],
            checksum=row['checksum'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            ingested_at=row['ingested_at'],
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}'),
            catalog_id=row['catalog_id'],
            folder_path=row['folder_path'] or '',
            language=row['language'] or 'en',
            word_count=row['word_count'] or 0,
            chunk_count=row['chunk_count'] or 0,
        )

    def _row_to_chunk(self, row: sqlite3.Row) -> Chunk:
        return Chunk(
            chunk_id=row['chunk_id'],
            doc_id=row['doc_id'],
            content=row['content'],
            chunk_index=row['chunk_index'],
            start_offset=row['start_offset'],
            end_offset=row['end_offset'],
            page_number=row['page_number'],
            line_start=row['line_start'],
            line_end=row['line_end'],
            section_title=row['section_title'],
            embedding=None,
            metadata=json.loads(row['metadata'] or '{}'),
        )


# ─────────────────────────────────────────────
# Search Engine
# ─────────────────────────────────────────────

class LexicalSearchEngine:
    """BM25-style lexical search using SQLite FTS5."""

    def __init__(self, db: Database):
        self.db = db

    def search(self, query: str, limit: int = 20,
               catalog_id: Optional[str] = None,
               tags: Optional[List[str]] = None,
               content_types: Optional[List[str]] = None,
               source_quota: Optional[int] = None) -> List[SearchResult]:
        """Search chunks using FTS5."""
        if not query.strip():
            return []

        # Sanitize query for FTS5
        fts_query = self._sanitize_fts_query(query)

        sql = """
            SELECT c.chunk_id, c.doc_id, c.content, c.page_number,
                   c.line_start, c.line_end, c.section_title,
                   d.file_path, d.title, d.catalog_id, d.tags, d.content_type,
                   rank
            FROM chunks_fts
            JOIN chunks c ON chunks_fts.chunk_id = c.chunk_id
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE chunks_fts MATCH ?
        """
        params = [fts_query]

        if catalog_id:
            sql += " AND d.catalog_id = ?"
            params.append(catalog_id)

        if content_types:
            placeholders = ','.join('?' * len(content_types))
            sql += f" AND d.content_type IN ({placeholders})"
            params.extend(content_types)

        sql += " ORDER BY rank LIMIT ?"
        params.append(limit * 3 if source_quota else limit)

        try:
            rows = self.db.fetchall(sql, tuple(params))
        except Exception as e:
            logger.warning(f"FTS search error: {e}. Falling back to LIKE search.")
            return self._fallback_search(query, limit, catalog_id)

        results = []
        seen_docs = defaultdict(int)

        for i, row in enumerate(rows):
            doc_id = row['doc_id']
            doc_tags = json.loads(row['tags'] or '[]')

            # Tag filter
            if tags and not any(t in doc_tags for t in tags):
                continue

            # Source quota
            if source_quota and seen_docs[doc_id] >= source_quota:
                continue

            seen_docs[doc_id] += 1

            score = abs(row['rank']) if row['rank'] else 0.0

            results.append(SearchResult(
                doc_id=doc_id,
                chunk_id=row['chunk_id'],
                file_path=row['file_path'],
                title=row['title'],
                content=row['content'],
                score=score,
                rank=i + 1,
                page_number=row['page_number'],
                line_start=row['line_start'],
                line_end=row['line_end'],
                section_title=row['section_title'],
                match_type='lexical',
            ))

            if len(results) >= limit:
                break

        return results

    def _sanitize_fts_query(self, query: str) -> str:
        """Sanitize query for FTS5."""
        # Remove special FTS5 characters that might cause errors
        query = re.sub(r'["\(\)\*\+\-\^]', ' ', query)
        query = query.strip()
        if not query:
            return '""'
        # Quote multi-word phrases
        words = query.split()
        if len(words) == 1:
            return f'"{words[0]}"*'
        return ' OR '.join(f'"{w}"*' for w in words if w)

    def _fallback_search(self, query: str, limit: int,
                         catalog_id: Optional[str] = None) -> List[SearchResult]:
        """Fallback LIKE-based search."""
        words = query.lower().split()
        if not words:
            return []

        sql = """
            SELECT c.chunk_id, c.doc_id, c.content, c.page_number,
                   c.line_start, c.line_end, c.section_title,
                   d.file_path, d.title
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE LOWER(c.content) LIKE ?
        """
        params = [f'%{words[0]}%']

        if catalog_id:
            sql += " AND d.catalog_id = ?"
            params.append(catalog_id)

        sql += " LIMIT ?"
        params.append(limit)

        rows = self.db.fetchall(sql, tuple(params))
        results = []
        for i, row in enumerate(rows):
            # Score by word frequency
            content_lower = row['content'].lower()
            score = sum(content_lower.count(w) for w in words)
            results.append(SearchResult(
                doc_id=row['doc_id'],
                chunk_id=row['chunk_id'],
                file_path=row['file_path'],
                title=row['title'],
                content=row['content'],
                score=float(score),
                rank=i + 1,
                page_number=row['page_number'],
                line_start=row['line_start'],
                line_end=row['line_end'],
                section_title=row['section_title'],
                match_type='lexical_fallback',
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results


class EmbeddingEngine:
    """Optional embedding-based semantic search."""

    def __init__(self, db: Database, model_name: str = "text-embedding-3-small"):
        self.db = db
        self.model_name = model_name
        self._client = None

    def _get_client(self):
        if self._client is None:
            if HAS_OPENAI:
                self._client = openai.OpenAI()
            else:
                raise RuntimeError("OpenAI package not available for embeddings")
        return self._client

    def embed_text(self, text: str) -> Optional[List[float]]:
        """Get embedding for text."""
        try:
            client = self._get_client()
            response = client.embeddings.create(
                model=self.model_name,
                input=text[:8000]
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Embedding error: {e}")
            return None

    def embed_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """Embed a list of chunks."""
        for chunk in chunks:
            embedding = self.embed_text(chunk.content)
            if embedding:
                chunk.embedding = embedding
                # Store in DB
                import struct
                blob = struct.pack(f'{len(embedding)}f', *embedding)
                self.db.execute(
                    "UPDATE chunks SET embedding=? WHERE chunk_id=?",
                    (blob, chunk.chunk_id)
                )
        self.db.commit()
        return chunks

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not HAS_NUMPY:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)
        else:
            a_arr = np.array(a)
            b_arr = np.array(b)
            norm_a = np.linalg.norm(a_arr)
            norm_b = np.linalg.norm(b_arr)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))

    def search(self, query: str, limit: int = 20,
               catalog_id: Optional[str] = None) -> List[SearchResult]:
        """Semantic search using embeddings."""
        query_embedding = self.embed_text(query)
        if not query_embedding:
            return []

        # Load all chunks with embeddings
        sql = """
            SELECT c.chunk_id, c.doc_id, c.content, c.page_number,
                   c.line_start, c.line_end, c.section_title, c.embedding,
                   d.file_path, d.title
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.embedding IS NOT NULL
        """
        params = []
        if catalog_id:
            sql += " AND d.catalog_id = ?"
            params.append(catalog_id)

        rows = self.db.fetchall(sql, tuple(params))

        scored = []
        import struct
        for row in rows:
            if row['embedding']:
                try:
                    n = len(row['embedding']) // 4
                    emb = list(struct.unpack(f'{n}f', row['embedding']))
                    sim = self.cosine_similarity(query_embedding, emb)
                    scored.append((sim, row))
                except Exception:
                    pass

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for i, (score, row) in enumerate(scored[:limit]):
            results.append(SearchResult(
                doc_id=row['doc_id'],
                chunk_id=row['chunk_id'],
                file_path=row['file_path'],
                title=row['title'],
                content=row['content'],
                score=score,
                rank=i + 1,
                page_number=row['page_number'],
                line_start=row['line_start'],
                line_end=row['line_end'],
                section_title=row['section_title'],
                match_type='semantic',
            ))

        return results


class Reranker:
    """Reranks search results using cross-encoder or LLM scoring."""

    def __init__(self):
        pass

    def rerank(self, query: str, results: List[SearchResult],
               top_k: int = 10) -> List[SearchResult]:
        """Rerank results by relevance to query using simple scoring."""
        query_words = set(query.lower().split())

        for result in results:
            content_lower = result.content.lower()
            # Count exact phrase matches
            phrase_score = 1.0 if query.lower() in content_lower else 0.0
            # Count word matches
            word_score = sum(1 for w in query_words if w in content_lower) / max(len(query_words), 1)
            # Combine with original score
            result.score = result.score * 0.5 + phrase_score * 0.3 + word_score * 0.2

        results.sort(key=lambda r: r.score, reverse=True)
        for i, r in enumerate(results):
            r.rank = i + 1

        return results[:top_k]


class SearchEngine:
    """Unified search engine combining lexical and semantic search."""

    def __init__(self, db: Database, base_path: str,
                 use_embeddings: bool = False,
                 use_reranking: bool = False):
        self.db = db
        self.base_path = base_path
        self.lexical = LexicalSearchEngine(db)
        self.embedding_engine = EmbeddingEngine(db) if use_embeddings else None
        self.reranker = Reranker() if use_reranking else None
        self.use_embeddings = use_embeddings
        self.use_reranking = use_reranking

    def search(self, query: str, limit: int = 20,
               catalog_id: Optional[str] = None,
               tags: Optional[List[str]] = None,
               content_types: Optional[List[str]] = None,
               source_quota: Optional[int] = None,
               use_semantic: bool = False) -> List[SearchResult]:
        """Unified search."""
        results = self.lexical.search(
            query, limit=limit * 2,
            catalog_id=catalog_id,
            tags=tags,
            content_types=content_types,
            source_quota=source_quota
        )

        if use_semantic and self.embedding_engine:
            semantic_results = self.embedding_engine.search(
                query, limit=limit, catalog_id=catalog_id
            )
            # Merge results
            seen_chunks = {r.chunk_id for r in results}
            for sr in semantic_results:
                if sr.chunk_id not in seen_chunks:
                    results.append(sr)
                    seen_chunks.add(sr.chunk_id)

        if self.reranker and results:
            results = self.reranker.rerank(query, results, top_k=limit)
        else:
            results = results[:limit]
            for i, r in enumerate(results):
                r.rank = i + 1

        return results


# ─────────────────────────────────────────────
# Relation Miner
# ─────────────────────────────────────────────

class RelationMiner:
    """Mines relations between documents."""

    def __init__(self, db: Database, doc_store: DocumentStore):
        self.db = db
        self.doc_store = doc_store

    def mine_relations(self, doc_id: str, method: str = "keyword_overlap") -> List[Relation]:
        """Mine relations for a document."""
        if method == "keyword_overlap":
            return self._mine_keyword_overlap(doc_id)
        elif method == "citation":
            return self._mine_citations(doc_id)
        return []

    def _mine_keyword_overlap(self, doc_id: str, threshold: float = 0.1,
                               max_relations: int = 10) -> List[Relation]:
        """Find related documents by keyword overlap."""
        doc = self.doc_store.get_document(doc_id)
        if not doc:
            return []

        chunks = self.doc_store.get_chunks(doc_id)
        doc_text = ' '.join(c.content for c in chunks).lower()
        doc_words = Counter(re.findall(r'\b\w{4,}\b', doc_text))
        total_doc = sum(doc_words.values())

        if total_doc == 0:
            return []

        # Get all other documents
        all_docs = self.doc_store.list_documents(limit=500)
        relations = []

        for other_doc in all_docs:
            if other_doc.doc_id == doc_id:
                continue

            other_chunks = self.doc_store.get_chunks(other_doc.doc_id)
            other_text = ' '.join(c.content for c in other_chunks).lower()
            other_words = Counter(re.findall(r'\b\w{4,}\b', other_text))
            total_other = sum(other_words.values())

            if total_other == 0:
                continue

            # Jaccard similarity on top keywords
            top_doc = set(w for w, _ in doc_words.most_common(50))
            top_other = set(w for w, _ in other_words.most_common(50))

            intersection = len(top_doc & top_other)
            union = len(top_doc | top_other)
            similarity = intersection / union if union > 0 else 0.0

            if similarity >= threshold:
                relation = Relation(
                    relation_id=str(uuid.uuid4()),
                    source_doc_id=doc_id,
                    target_doc_id=other_doc.doc_id,
                    relation_type='keyword_similar',
                    confidence=similarity,
                    created_at=datetime.datetime.utcnow().isoformat(),
                    metadata={'similarity': similarity}
                )
                relations.append(relation)

        relations.sort(key=lambda r: r.confidence, reverse=True)
        relations = relations[:max_relations]

        # Store relations
        for rel in relations:
            self._store_relation(rel)

        return relations

    def _mine_citations(self, doc_id: str) -> List[Relation]:
        """Find citation-like references between documents."""
        doc = self.doc_store.get_document(doc_id)
        if not doc:
            return []

        chunks = self.doc_store.get_chunks(doc_id)
        doc_text = ' '.join(c.content for c in chunks)

        # Look for file name references
        all_docs = self.doc_store.list_documents(limit=500)
        relations = []

        for other_doc in all_docs:
            if other_doc.doc_id == doc_id:
                continue
            other_name = Path(other_doc.file_path).stem
            if len(other_name) > 3 and other_name.lower() in doc_text.lower():
                relation = Relation(
                    relation_id=str(uuid.uuid4()),
                    source_doc_id=doc_id,
                    target_doc_id=other_doc.doc_id,
                    relation_type='references',
                    confidence=0.7,
                    created_at=datetime.datetime.utcnow().isoformat(),
                )
                relations.append(relation)
                self._store_relation(relation)

        return relations

    def _store_relation(self, relation: Relation):
        try:
            self.db.execute(
                "INSERT OR REPLACE INTO relations VALUES (?,?,?,?,?,?,?)",
                (relation.relation_id, relation.source_doc_id, relation.target_doc_id,
                 relation.relation_type, relation.confidence, relation.created_at,
                 json.dumps(relation.metadata))
            )
            self.db.commit()
        except Exception as e:
            logger.warning(f"Failed to store relation: {e}")

    def get_relations(self, doc_id: str) -> List[Relation]:
        rows = self.db.fetchall(
            "SELECT * FROM relations WHERE source_doc_id=? OR target_doc_id=? ORDER BY confidence DESC",
            (doc_id, doc_id)
        )
        return [self._row_to_relation(r) for r in rows]

    def _row_to_relation(self, row: sqlite3.Row) -> Relation:
        return Relation(
            relation_id=row['relation_id'],
            source_doc_id=row['source_doc_id'],
            target_doc_id=row['target_doc_id'],
            relation_type=row['relation_type'],
            confidence=row['confidence'],
            created_at=row['created_at'],
            metadata=json.loads(row['metadata'] or '{}'),
        )


# ─────────────────────────────────────────────
# Journal Manager
# ─────────────────────────────────────────────

class JournalManager:
    """Manages investigation journal entries."""

    def __init__(self, db: Database):
        self.db = db

    def create_entry(self, title: str, content: str,
                     tags: List[str] = None,
                     cited_docs: List[str] = None,
                     query: str = "",
                     agent_session_id: Optional[str] = None,
                     metadata: Dict = None) -> JournalEntry:
        now = datetime.datetime.utcnow().isoformat()
        entry = JournalEntry(
            entry_id=str(uuid.uuid4()),
            title=title,
            content=content,
            created_at=now,
            updated_at=now,
            tags=tags or [],
            cited_docs=cited_docs or [],
            query=query,
            agent_session_id=agent_session_id,
            metadata=metadata or {},
        )
        self.db.execute(
            "INSERT INTO journal_entries VALUES (?,?,?,?,?,?,?,?,?,?)",
            (entry.entry_id, entry.title, entry.content, entry.created_at,
             entry.updated_at, json.dumps(entry.tags), json.dumps(entry.cited_docs),
             entry.query, entry.agent_session_id, json.dumps(entry.metadata))
        )
        self.db.commit()
        return entry

    def get_entry(self, entry_id: str) -> Optional[JournalEntry]:
        row = self.db.fetchone("SELECT * FROM journal_entries WHERE entry_id=?", (entry_id,))
        if row:
            return self._row_to_entry(row)
        return None

    def update_entry(self, entry_id: str, content: str = None,
                     tags: List[str] = None) -> Optional[JournalEntry]:
        entry = self.get_entry(entry_id)
        if not entry:
            return None
        if content is not None:
            entry.content = content
        if tags is not None:
            entry.tags = tags
        entry.updated_at = datetime.datetime.utcnow().isoformat()
        self.db.execute(
            "UPDATE journal_entries SET content=?, tags=?, updated_at=? WHERE entry_id=?",
            (entry.content, json.dumps(entry.tags), entry.updated_at, entry_id)
        )
        self.db.commit()
        return entry

    def list_entries(self, limit: int = 50, offset: int = 0,
                     tags: Optional[List[str]] = None,
                     query: Optional[str] = None) -> List[JournalEntry]:
        sql = "SELECT * FROM journal_entries WHERE 1=1"
        params = []
        if query:
            sql += " AND (title LIKE ? OR content LIKE ?)"
            params.extend([f'%{query}%', f'%{query}%'])
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self.db.fetchall(sql, tuple(params))
        entries = [self._row_to_entry(r) for r in rows]
        if tags:
            entries = [e for e in entries if any(t in e.tags for t in tags)]
        return entries

    def search_entries(self, query: str, limit: int = 20) -> List[JournalEntry]:
        rows = self.db.fetchall(
            """SELECT * FROM journal_entries
               WHERE title LIKE ? OR content LIKE ? OR query LIKE ?
               ORDER BY created_at DESC LIMIT ?""",
            (f'%{query}%', f'%{query}%', f'%{query}%', limit)
        )
        return [self._row_to_entry(r) for r in rows]

    def _row_to_entry(self, row: sqlite3.Row) -> JournalEntry:
        return JournalEntry(
            entry_id=row['entry_id'],
            title=row['title'],
            content=row['content'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            tags=json.loads(row['tags'] or '[]'),
            cited_docs=json.loads(row['cited_docs'] or '[]'),
            query=row['query'] or '',
            agent_session_id=row['agent_session_id'],
            metadata=json.loads(row['metadata'] or '{}'),
        )


# ─────────────────────────────────────────────
# LLM Client
# ─────────────────────────────────────────────

class LLMClient:
    """Abstraction over LLM providers."""

    def __init__(self, provider: str = "anthropic",
                 model: str = None,
                 api_key: Optional[str] = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self._client = None

        if provider == "anthropic":
            self.model = model or "claude-3-5-sonnet-20241022"
        elif provider == "openai":
            self.model = model or "gpt-4o"
        else:
            self.model = model or "unknown"

    def _get_client(self):
        if self._client is None:
            if self.provider == "anthropic":
                if not HAS_ANTHROPIC:
                    raise RuntimeError("anthropic package not installed")
                kwargs = {}
                if self.api_key:
                    kwargs['api_key'] = self.api_key
                self._client = anthropic.Anthropic(**kwargs)
            elif self.provider == "openai":
                if not HAS_OPENAI:
                    raise RuntimeError("openai package not installed")
                kwargs = {}
                if self.api_key:
                    kwargs['api_key'] = self.api_key
                self._client = openai.OpenAI(**kwargs)
            else:
                raise RuntimeError(f"Unknown provider: {self.provider}")
        return self._client

    def complete(self, messages: List[Dict[str, str]],
                 system: str = "",
                 max_tokens: int = 4096,
                 temperature: float = 0.3) -> str:
        """Get a completion from the LLM."""
        try:
            client = self._get_client()
            if self.provider == "anthropic":
                response = client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=messages
                )
                return response.content[0].text
            elif self.provider == "openai":
                all_messages = []
                if system:
                    all_messages.append({"role": "system", "content": system})
                all_messages.extend(messages)
                response = client.chat.completions.create(
                    model=self.model,
                    messages=all_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM completion error: {e}")
            raise

    def is_available(self) -> bool:
        """Check if the LLM is available."""
        try:
            self._get_client()
            return True
        except Exception:
            return False


# ─────────────────────────────────────────────
# Context Builder
# ─────────────────────────────────────────────

class ContextBuilder:
    """Builds context windows from search results for LLM consumption."""

    def __init__(self, doc_store: DocumentStore, max_context_tokens: int = 8000):
        self.doc_store = doc_store
        self.max_context_tokens = max_context_tokens
        self.chars_per_token = 4  # Rough estimate

    def build_context(self, results: List[SearchResult],
                      query: str) -> Tuple[str, List[Citation]]:
        """Build a context string and citations from search results."""
        context_parts = []
        citations = []
        total_chars = 0
        max_chars = self.max_context_tokens * self.chars_per_token

        for i, result in enumerate(results):
            # Read original file section
            section_text = self._read_original_section(result)
            if not section_text:
                section_text = result.content

            citation_id = f"[{i+1}]"
            location_info = self._format_location(result)

            header = f"\n{citation_id} Source: {result.title} ({result.file_path}){location_info}\n"
            entry = header + section_text + "\n"

            if total_chars + len(entry) > max_chars:
                # Truncate
                remaining = max_chars - total_chars - len(header) - 100
                if remaining > 100:
                    entry = header + section_text[:remaining] + "...\n"
                else:
                    break

            context_parts.append(entry)
            total_chars += len(entry)

            citation = Citation(
                citation_id=citation_id,
                doc_id=result.doc_id,
                file_path=result.file_path,
                title=result.title,
                chunk_id=result.chunk_id,
                excerpt=section_text[:300],
                page_number=result.page_number,
                line_start=result.line_start,
                line_end=result.line_end,
            )
            citations.append(citation)

        context = '\n'.join(context_parts)
        return context, citations

    def _read_original_section(self, result: SearchResult) -> Optional[str]:
        """Read the original file section for a search result."""
        try:
            file_path = result.file_path
            if not Path(file_path).exists():
                return None

            ext = Path(file_path).suffix.lower()

            if result.page_number is not None and ext == '.pdf':
                return self._read_pdf_page(file_path, result.page_number)
            elif result.line_start is not None and result.line_end is not None:
                return self._read_lines(file_path, result.line_start, result.line_end)
            else:
                return result.content

        except Exception as e:
            logger.warning(f"Failed to read original section: {e}")
            return result.content

    def _read_pdf_page(self, file_path: str, page_number: int) -> Optional[str]:
        """Read a specific page from a PDF."""
        if not HAS_PYPDF:
            return None
        try:
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                if 0 < page_number <= len(reader.pages):
                    return reader.pages[page_number - 1].extract_text()
        except Exception as e:
            logger.warning(f"PDF page read error: {e}")
        return None

    def _read_lines(self, file_path: str, line_start: int, line_end: int,
                    context_lines: int = 5) -> Optional[str]:
        """Read specific lines from a text file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()

            start = max(0, line_start - context_lines)
            end = min(len(lines), line_end + context_lines + 1)
            return ''.join(lines[start:end])
        except Exception as e:
            logger.warning(f"Line read error: {e}")
            return None

    def _format_location(self, result: SearchResult) -> str:
        """Format location information for a citation."""
        parts = []
        if result.page_number:
            parts.append(f"p.{result.page_number}")
        if result.line_start is not None:
            parts.append(f"lines {result.line_start}-{result.line_end}")
        if result.section_title:
            parts.append(f"§{result.section_title}")
        if parts:
            return f" [{', '.join(parts)}]"
        return ""


# ─────────────────────────────────────────────
# Research Agent
# ─────────────────────────────────────────────

class ResearchAgent:
    """The main LLM-powered research agent."""

    SYSTEM_PROMPT = """You are Marginalia, a research assistant for a personal knowledge base.
You have access to the user's documents and will answer questions based on the provided source material.

Guidelines:
1. Base your answers primarily on the provided source documents
2. Always cite your sources using the citation numbers [1], [2], etc.
3. If information is not in the sources, say so clearly
4. Be precise about what the sources say vs. your own knowledge
5. When quoting, use exact quotes from the sources
6. Organize complex answers with clear structure
7. Note any contradictions between sources
"""

    def __init__(self, llm_client: LLMClient,
                 search_engine: SearchEngine,
                 doc_store: DocumentStore,
                 journal_manager: JournalManager,
                 context_builder: ContextBuilder,
                 max_search_results: int = 10,
                 use_semantic: bool = False):
        self.llm = llm_client
        self.search = search_engine
        self.doc_store = doc_store
        self.journal = journal_manager
        self.context_builder = context_builder
        self.max_search_results = max_search_results
        self.use_semantic = use_semantic
        self.conversation_history: List[Dict[str, str]] = []
        self.session_id = str(uuid.uuid4())

    def query(self, question: str,
              catalog_id: Optional[str] = None,
              tags: Optional[List[str]] = None,
              source_quota: Optional[int] = None,
              save_to_journal: bool = True,
              additional_context: str = "") -> AgentResponse:
        """Answer a research question."""
        logger.info(f"Agent query: {question[:100]}...")

        # Search for relevant documents
        results = self.search.search(
            question,
            limit=self.max_search_results,
            catalog_id=catalog_id,
            tags=tags,
            source_quota=source_quota,
            use_semantic=self.use_semantic
        )

        # Also search journal entries for prior investigations
        journal_entries = self.journal.search_entries(question, limit=3)

        # Build context
        context, citations = self.context_builder.build_context(results, question)

        # Add journal context if available
        journal_context = ""
        if journal_entries:
            journal_context = "\n\nPrior investigations on related topics:\n"
            for entry in journal_entries:
                journal_context += f"\n[Prior Note: {entry.title}]\n{entry.content[:500]}...\n"

        # Build prompt
        user_message = self._build_user_message(
            question, context, journal_context, additional_context
        )

        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": user_message})

        # Get LLM response
        try:
            answer = self.llm.complete(
                messages=self.conversation_history,
                system=self.SYSTEM_PROMPT,
                max_tokens=4096,
                temperature=0.3
            )
        except Exception as e:
            logger.error(f"LLM error: {e}")
            answer = f"[Error getting LLM response: {e}]\n\nBased on the sources found:\n{context[:2000]}"

        # Add assistant response to history
        self.conversation_history.append({"role": "assistant", "content": answer})

        # Create response
        sources_consulted = list(set(r.file_path for r in results))
        now = datetime.datetime.utcnow().isoformat()

        response = AgentResponse(
            session_id=self.session_id,
            query=question,
            answer=answer,
            citations=citations,
            sources_consulted=sources_consulted,
            journal_entry_id=None,
            created_at=now,
        )

        # Save to journal
        if save_to_journal:
            journal_entry = self._save_to_journal(question, answer, citations, results)
            response.journal_entry_id = journal_entry.entry_id

        return response

    def _build_user_message(self, question: str, context: str,
                             journal_context: str, additional_context: str) -> str:
        """Build the user message for the LLM."""
        parts = []

        if context:
            parts.append(f"SOURCE DOCUMENTS:\n{context}")

        if journal_context:
            parts.append(journal_context)

        if additional_context:
            parts.append(f"ADDITIONAL CONTEXT:\n{additional_context}")

        parts.append(f"QUESTION: {question}")
        parts.append("Please answer the question based on the source documents above. Cite sources using [1], [2], etc.")

        return '\n\n'.join(parts)

    def _save_to_journal(self, question: str, answer: str,
                          citations: List[Citation],
                          results: List[SearchResult]) -> JournalEntry:
        """Save the investigation to the journal."""
        # Format journal entry
        title = f"Investigation: {question[:80]}"

        cited_doc_ids = list(set(c.doc_id for c in citations))

        # Build citation list
        citation_text = "\n\n## Sources\n"
        for citation in citations:
            location = ""
            if citation.page_number:
                location += f" (p.{citation.page_number})"
            if citation.line_start:
                location += f" (lines {citation.line_start}-{citation.line_end})"
            citation_text += f"\n{citation.citation_id} {citation.title}{location}\n"
            citation_text += f"   Path: {citation.file_path}\n"
            citation_text += f"   Excerpt: {citation.excerpt[:200]}...\n"

        content = f"## Query\n{question}\n\n## Answer\n{answer}{citation_text}"

        entry = self.journal.create_entry(
            title=title,
            content=content,
            tags=['agent-investigation'],
            cited_docs=cited_doc_ids,
            query=question,
            agent_session_id=self.session_id,
        )
        return entry

    def generate_report(self, topic: str, outline: Optional[List[str]] = None,
                        catalog_id: Optional[str] = None) -> str:
        """Generate a structured research report on a topic."""
        if not outline:
            # Generate outline first
            outline_prompt = f"Create a detailed outline for a research report on: {topic}\nList 5-7 main sections."
            outline_response = self.llm.complete(
                messages=[{"role": "user", "content": outline_prompt}],
                system=self.SYSTEM_PROMPT,
                max_tokens=500
            )
            outline = [line.strip() for line in outline_response.split('\n')
                       if line.strip() and not line.strip().startswith('#')]

        report_parts = [f"# Research Report: {topic}\n"]
        report_parts.append(f"*Generated: {datetime.datetime.utcnow().isoformat()}*\n")

        for section in outline[:7]:
            section_query = f"{topic}: {section}"
            results = self.search.search(section_query, limit=5, catalog_id=catalog_id)
            context, citations = self.context_builder.build_context(results, section_query)

            section_prompt = f"""Write a detailed section for a research report.

Topic: {topic}
Section: {section}

Source material:
{context}

Write a comprehensive section with citations [1], [2], etc."""

            try:
                section_content = self.llm.complete(
                    messages=[{"role": "user", "content": section_prompt}],
                    system=self.SYSTEM_PROMPT,
                    max_tokens=1000
                )
            except Exception as e:
                section_content = f"[Error generating section: {e}]"

            report_parts.append(f"\n## {section}\n{section_content}\n")

        report = '\n'.join(report_parts)

        # Save report to journal
        self.journal.create_entry(
            title=f"Report: {topic}",
            content=report,
            tags=['report', 'agent-generated'],
            query=topic,
            agent_session_id=self.session_id,
        )

        return report

    def reset_conversation(self):
        """Reset conversation history."""
        self.conversation_history = []
        self.session_id = str(uuid.uuid4())


# ─────────────────────────────────────────────
# Metadata Manager
# ─────────────────────────────────────────────

class MetadataManager:
    """Manages document metadata."""

    def __init__(self, db: Database):
        self.db = db

    def update_metadata(self, doc_id: str, metadata: Dict[str, Any]) -> bool:
        """Update document metadata."""
        row = self.db.fetchone("SELECT metadata FROM documents WHERE doc_id=?", (doc_id,))
        if not row:
            return False
        existing = json.loads(row['metadata'] or '{}')
        existing.update(metadata)
        self.db.execute(
            "UPDATE documents SET metadata=? WHERE doc_id=?",
            (json.dumps(existing), doc_id)
        )
        self.db.commit()
        return True

    def get_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document metadata."""
        row = self.db.fetchone("SELECT metadata FROM documents WHERE doc_id=?", (doc_id,))
        if row:
            return json.loads(row['metadata'] or '{}')
        return None

    def add_tags(self, doc_id: str, tags: List[str]) -> bool:
        """Add tags to a document."""
        row = self.db.fetchone("SELECT tags FROM documents WHERE doc_id=?", (doc_id,))
        if not row:
            return False
        existing_tags = json.loads(row['tags'] or '[]')
        new_tags = list(set(existing_tags + tags))
        self.db.execute(
            "UPDATE documents SET tags=? WHERE doc_id=?",
            (json.dumps(new_tags), doc_id)
        )
        self.db.commit()
        return True

    def remove_tags(self, doc_id: str, tags: List[str]) -> bool:
        """Remove tags from a document."""
        row = self.db.fetchone("SELECT tags FROM documents WHERE doc_id=?", (doc_id,))
        if not row:
            return False
        existing_tags = json.loads(row['tags'] or '[]')
        new_tags = [t for t in existing_tags if t not in tags]
        self.db.execute(
            "UPDATE documents SET tags=? WHERE doc_id=?",
            (json.dumps(new_tags), doc_id)
        )
        self.db.commit()
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        stats = {}

        row = self.db.fetchone("SELECT COUNT(*) as count FROM documents")
        stats['total_documents'] = row['count'] if row else 0

        row = self.db.fetchone("SELECT COUNT(*) as count FROM chunks")
        stats['total_chunks'] = row['count'] if row else 0

        row = self.db.fetchone("SELECT SUM(word_count) as total FROM documents")
        stats['total_words'] = row['total'] if row and row['total'] else 0

        row = self.db.fetchone("SELECT COUNT(*) as count FROM catalogs")
        stats['total_catalogs'] = row['count'] if row else 0

        row = self.db.fetchone("SELECT COUNT(*) as count FROM tags")
        stats['total_tags'] = row['count'] if row else 0

        row = self.db.fetchone("SELECT COUNT(*) as count FROM journal_entries")
        stats['total_journal_entries'] = row['count'] if row else 0

        row = self.db.fetchone("SELECT COUNT(*) as count FROM relations")
        stats['total_relations'] = row['count'] if row else 0

        # Content type distribution
        rows = self.db.fetchall(
            "SELECT content_type, COUNT(*) as count FROM documents GROUP BY content_type ORDER BY count DESC"
        )
        stats['content_types'] = {r['content_type']: r['count'] for r in rows}

        # Top tags
        rows = self.db.fetchall("SELECT tags FROM documents WHERE tags != '[]'")
        tag_counter = Counter()
        for row in rows:
            for tag in json.loads(row['tags'] or '[]'):
                tag_counter[tag] += 1
        stats['top_tags'] = dict(tag_counter.most_common(10))

        return stats


# ─────────────────────────────────────────────
# Main Marginalia System
# ─────────────────────────────────────────────

class Marginalia:
    """
    Main entry point for the Marginalia knowledge management system.
    """

    def __init__(self, base_path: str,
                 llm_provider: str = "anthropic",
                 llm_model: Optional[str] = None,
                 llm_api_key: Optional[str] = None,
                 use_embeddings: bool = False,
                 use_reranking: bool = False,
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 max_search_results: int = 10,
                 max_context_tokens: int = 8000):
        """
        Initialize Marginalia.

        Args:
            base_path: Root directory for the knowledge base
            llm_provider: LLM provider ('anthropic' or 'openai')
            llm_model: Specific model to use
            llm_api_key: API key (uses env var if not provided)
            use_embeddings: Enable semantic search with embeddings
            use_reranking: Enable result reranking
            chunk_size: Words per chunk
            chunk_overlap: Overlap words between chunks
            max_search_results: Max results to retrieve
            max_context_tokens: Max tokens for context window
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_path = str(self.base_path / "marginalia.db")
        self.db = Database(db_path)

        # Initialize components
        self.doc_store = DocumentStore(self.db, str(self.base_path))
        self.doc_store.ingester = FileIngester(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        self.catalog_manager = CatalogManager(self.db)
        self.metadata_manager = MetadataManager(self.db)
        self.journal_manager = JournalManager(self.db)
        self.relation_miner = RelationMiner(self.db, self.doc_store)

        self.search_engine = SearchEngine(
            self.db, str(self.base_path),
            use_embeddings=use_embeddings,
            use_reranking=use_reranking
        )

        self.context_builder = ContextBuilder(
            self.doc_store,
            max_context_tokens=max_context_tokens
        )

        # Initialize LLM
        self.llm_client = LLMClient(
            provider=llm_provider,
            model=llm_model,
            api_key=llm_api_key
        )

        # Initialize agent
        self.agent = ResearchAgent(
            llm_client=self.llm_client,
            search_engine=self.search_engine,
            doc_store=self.doc_store,
            journal_manager=self.journal_manager,
            context_builder=self.context_builder,
            max_search_results=max_search_results,
            use_semantic=use_embeddings
        )

        logger.info(f"Marginalia initialized at {base_path}")

    # ── Ingestion ──────────────────────────────

    def ingest(self, path: str,
               catalog: Optional[str] = None,
               tags: Optional[List[str]] = None,
               recursive: bool = True) -> Union[DocumentRecord, List[DocumentRecord]]:
        """
        Ingest a file or directory.

        Args:
            path: File or directory path
            catalog: Catalog name to assign documents to
            tags: Tags to apply
            recursive: Whether to recurse into subdirectories

        Returns:
            DocumentRecord or list of DocumentRecords
        """
        catalog_id = None
        if catalog:
            cat = self.catalog_manager.get_catalog_by_name(catalog)
            if not cat:
                cat = self.catalog_manager.create_catalog(catalog)
            catalog_id = cat.catalog_id

        p = Path(path)
        if p.is_dir():
            return self.doc_store.ingest_directory(
                str(p), recursive=recursive,
                catalog_id=catalog_id, tags=tags
            )
        else:
            return self.doc_store.ingest_file(
                str(p), catalog_id=catalog_id, tags=tags
            )

    def watch_directory(self, dir_path: str, catalog: Optional[str] = None,
                        tags: Optional[List[str]] = None,
                        interval: int = 60) -> threading.Thread:
        """
        Watch a directory for new/changed files and auto-ingest them.

        Args:
            dir_path: Directory to watch
            catalog: Catalog to assign new files to
            tags: Tags to apply
            interval: Check interval in seconds

        Returns:
            Background thread
        """
        def _watch():
            logger.info(f"Watching directory: {dir_path}")
            while True:
                try:
                    self.ingest(dir_path, catalog=catalog, tags=tags, recursive=True)
                except Exception as e:
                    logger.error(f"Watch error: {e}")
                time.sleep(interval)

        thread = threading.Thread(target=_watch, daemon=True)
        thread.start()
        return thread

    # ── Search ─────────────────────────────────

    def search(self, query: str,
               limit: int = 20,
               catalog: Optional[str] = None,
               tags: Optional[List[str]] = None,
               content_types: Optional[List[str]] = None,
               source_quota: Optional[int] = None,
               use_semantic: bool = False) -> List[SearchResult]:
        """
        Search the knowledge base.

        Args:
            query: Search query
            limit: Maximum results
            catalog: Filter by catalog name
            tags: Filter by tags
            content_types: Filter by MIME types
            source_quota: Max results per source document
            use_semantic: Use semantic search

        Returns:
            List of SearchResult objects
        """
        catalog_id = None
        if catalog:
            cat = self.catalog_manager.get_catalog_by_name(catalog)
            if cat:
                catalog_id = cat.catalog_id

        return self.search_engine.search(
            query, limit=limit,
            catalog_id=catalog_id,
            tags=tags,
            content_types=content_types,
            source_quota=source_quota,
            use_semantic=use_semantic
        )

    # ── Agent ──────────────────────────────────

    def ask(self, question: str,
            catalog: Optional[str] = None,
            tags: Optional[List[str]] = None,
            source_quota: Optional[int] = None,
            save_to_journal: bool = True) -> AgentResponse:
        """
        Ask the research agent a question.

        Args:
            question: Research question
            catalog: Limit search to this catalog
            tags: Filter sources by tags
            source_quota: Max chunks per source
            save_to_journal: Save investigation to journal

        Returns:
            AgentResponse with answer and citations
        """
        catalog_id = None
        if catalog:
            cat = self.catalog_manager.get_catalog_by_name(catalog)
            if cat:
                catalog_id = cat.catalog_id

        return self.agent.query(
            question,
            catalog_id=catalog_id,
            tags=tags,
            source_quota=source_quota,
            save_to_journal=save_to_journal
        )

    def generate_report(self, topic: str,
                        outline: Optional[List[str]] = None,
                        catalog: Optional[str] = None) -> str:
        """
        Generate a research report on a topic.

        Args:
            topic: Report topic
            outline: Optional section outline
            catalog: Limit to this catalog

        Returns:
            Formatted report string
        """
        catalog_id = None
        if catalog:
            cat = self.catalog_manager.get_catalog_by_name(catalog)
            if cat:
                catalog_id = cat.catalog_id

        return self.agent.generate_report(topic, outline=outline, catalog_id=catalog_id)

    def reset_conversation(self):
        """Reset the agent's conversation history."""
        self.agent.reset_conversation()

    # ── Catalogs ───────────────────────────────

    def create_catalog(self, name: str, description: str = "") -> Catalog:
        """Create a new catalog."""
        return self.catalog_manager.create_catalog(name, description)

    def list_catalogs(self) -> List[Catalog]:
        """List all catalogs."""
        return self.catalog_manager.list_catalogs()

    def get_catalog(self, name: str) -> Optional[Catalog]:
        """Get a catalog by name."""
        return self.catalog_manager.get_catalog_by_name(name)

    # ── Tags ───────────────────────────────────

    def create_tag(self, name: str, color: str = "#808080",
                   description: str = "") -> Tag:
        """Create a new tag."""
        return self.catalog_manager.create_tag(name, color, description)

    def list_tags(self) -> List[Tag]:
        """List all tags."""
        return self.catalog_manager.list_tags()

    def tag_document(self, doc_id: str, tags: List[str]) -> bool:
        """Add tags to a document."""
        # Ensure tags exist
        for tag_name in tags:
            self.catalog_manager.get_or_create_tag(tag_name)
        return self.metadata_manager.add_tags(doc_id, tags)

    def untag_document(self, doc_id: str, tags: List[str]) -> bool:
        """Remove tags from a document."""
        return self.metadata_manager.remove_tags(doc_id, tags)

    # ── Views ──────────────────────────────────

    def create_view(self, name: str, query: str,
                    filters: Dict = None,
                    sort_by: str = "relevance",
                    description: str = "") -> View:
        """Create a saved view."""
        return self.catalog_manager.create_view(name, query, filters, sort_by, description)

    def list_views(self) -> List[View]:
        """List all saved views."""
        return self.catalog_manager.list_views()

    def execute_view(self, view_name: str, limit: int = 20) -> List[SearchResult]:
        """Execute a saved view."""
        views = self.catalog_manager.list_views()
        view = next((v for v in views if v.name == view_name), None)
        if not view:
            raise ValueError(f"View not found: {view_name}")

        catalog_id = view.filters.get('catalog_id')
        tags = view.filters.get('tags')
        content_types = view.filters.get('content_types')

        return self.search_engine.search(
            view.query, limit=limit,
            catalog_id=catalog_id,
            tags=tags,
            content_types=content_types
        )

    # ── Documents ──────────────────────────────

    def get_document(self, doc_id: str) -> Optional[DocumentRecord]:
        """Get a document by ID."""
        return self.doc_store.get_document(doc_id)

    def list_documents(self, catalog: Optional[str] = None,
                       tags: Optional[List[str]] = None,
                       limit: int = 100) -> List[DocumentRecord]:
        """List documents."""
        catalog_id = None
        if catalog:
            cat = self.catalog_manager.get_catalog_by_name(catalog)
            if cat:
                catalog_id = cat.catalog_id

        return self.doc_store.list_documents(
            catalog_id=catalog_id, tags=tags, limit=limit
        )

    def delete_document(self, doc_id: str):
        """Delete a document from the knowledge base."""
        self.doc_store.delete_document(doc_id)

    def update_metadata(self, doc_id: str, metadata: Dict[str, Any]) -> bool:
        """Update document metadata."""
        return self.metadata_manager.update_metadata(doc_id, metadata)

    # ── Relations ──────────────────────────────

    def mine_relations(self, doc_id: str,
                       method: str = "keyword_overlap") -> List[Relation]:
        """Mine relations for a document."""
        return self.relation_miner.mine_relations(doc_id, method)

    def get_relations(self, doc_id: str) -> List[Relation]:
        """Get relations for a document."""
        return self.relation_miner.get_relations(doc_id)

    def mine_all_relations(self, method: str = "keyword_overlap",
                           limit: int = 100) -> int:
        """Mine relations for all documents."""
        docs = self.doc_store.list_documents(limit=limit)
        total = 0
        for doc in docs:
            relations = self.relation_miner.mine_relations(doc.doc_id, method)
            total += len(relations)
        return total

    # ── Journal ────────────────────────────────

    def create_journal_entry(self, title: str, content: str,
                              tags: List[str] = None) -> JournalEntry:
        """Create a manual journal entry."""
        return self.journal_manager.create_entry(title, content, tags=tags)

    def list_journal_entries(self, limit: int = 50,
                              tags: Optional[List[str]] = None,
                              query: Optional[str] = None) -> List[JournalEntry]:
        """List journal entries."""
        return self.journal_manager.list_entries(limit=limit, tags=tags, query=query)

    def get_journal_entry(self, entry_id: str) -> Optional[JournalEntry]:
        """Get a journal entry."""
        return self.journal_manager.get_entry(entry_id)

    def search_journal(self, query: str, limit: int = 20) -> List[JournalEntry]:
        """Search journal entries."""
        return self.journal_manager.search_entries(query, limit=limit)

    # ── Statistics ─────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        return self.metadata_manager.get_statistics()

    def summary(self) -> str:
        """Get a human-readable summary of the knowledge base."""
        s = self.stats()
        lines = [
            "═══ Marginalia Knowledge Base ═══",
            f"  Documents:      {s.get('total_documents', 0):,}",
            f"  Chunks:         {s.get('total_chunks', 0):,}",
            f"  Total words:    {s.get('total_words', 0):,}",
            f"  Catalogs:       {s.get('total_catalogs', 0)}",
            f"  Tags:           {s.get('total_tags', 0)}",
            f"  Journal entries:{s.get('total_journal_entries', 0)}",
            f"  Relations:      {s.get('total_relations', 0)}",
            "",
            "Content types:",
        ]
        for ct, count in list(s.get('content_types', {}).items())[:5]:
            lines.append(f"  {ct}: {count}")

        if s.get('top_tags'):
            lines.append("\nTop tags:")
            for tag, count in list(s['top_tags'].items())[:5]:
                lines.append(f"  #{tag}: {count}")

        return '\n'.join(lines)

    # ── Export ─────────────────────────────────

    def export_catalog(self, catalog_name: str, output_path: str,
                       format: str = "json") -> str:
        """Export a catalog to a file."""
        cat = self.catalog_manager.get_catalog_by_name(catalog_name)
        if not cat:
            raise ValueError(f"Catalog not found: {catalog_name}")

        docs = self.list_documents(catalog=catalog_name)
        output = Path(output_path)

        if format == "json":
            data = {
                'catalog': asdict(cat),
                'documents': [asdict(d) for d in docs],
                'exported_at': datetime.datetime.utcnow().isoformat(),
            }
            with open(output, 'w') as f:
                json.dump(data, f, indent=2)
        elif format == "markdown":
            lines = [f"# Catalog: {catalog_name}\n"]
            lines.append(f"*{cat.description}*\n")
            lines.append(f"*Exported: {datetime.datetime.utcnow().isoformat()}*\n\n")
            lines.append(f"## Documents ({len(docs)})\n")
            for doc in docs:
                lines.append(f"### {doc.title}")
                lines.append(f"- Path: `{doc.file_path}`")
                lines.append(f"- Type: {doc.content_type}")
                lines.append(f"- Words: {doc.word_count:,}")
                if doc.tags:
                    lines.append(f"- Tags: {', '.join(doc.tags)}")
                lines.append("")
            with open(output, 'w') as f:
                f.write('\n'.join(lines))

        return str(output)

    def export_journal(self, output_path: str, format: str = "markdown") -> str:
        """Export journal entries."""
        entries = self.journal_manager.list_entries(limit=10000)
        output = Path(output_path)

        if format == "markdown":
            lines = ["# Marginalia Journal\n"]
            lines.append(f"*Exported: {datetime.datetime.utcnow().isoformat()}*\n\n")
            for entry in entries:
                lines.append(f"## {entry.title}")
                lines.append(f"*{entry.created_at}*\n")
                lines.append(entry.content)
                if entry.tags:
                    lines.append(f"\nTags: {', '.join(entry.tags)}")
                lines.append("\n---\n")
            with open(output, 'w') as f:
                f.write('\n'.join(lines))
        elif format == "json":
            data = {
                'entries': [asdict(e) for e in entries],
                'exported_at': datetime.datetime.utcnow().isoformat(),
            }
            with open(output, 'w') as f:
                json.dump(data, f, indent=2)

        return str(output)

    # ── Maintenance ────────────────────────────

    def reindex(self, doc_id: Optional[str] = None):
        """Reindex documents (rebuild FTS index)."""
        if doc_id:
            doc = self.doc_store.get_document(doc_id)
            if doc:
                chunks = self.doc_store.get_chunks(doc_id)
                self.doc_store._update_fts(doc, chunks)
                logger.info(f"Reindexed: {doc.file_path}")
        else:
            docs = self.doc_store.list_documents(limit=100000)
            for doc in docs:
                chunks = self.doc_store.get_chunks(doc.doc_id)
                self.doc_store._update_fts(doc, chunks)
            logger.info(f"Reindexed {len(docs)} documents")

    def sync_directory(self, dir_path: str,
                       catalog: Optional[str] = None,
                       tags: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Sync a directory: ingest new/changed files, remove deleted ones.

        Returns dict with counts of added, updated, removed files.
        """
        dir_path = Path(dir_path)
        catalog_id = None
        if catalog:
            cat = self.catalog_manager.get_catalog_by_name(catalog)
            if not cat:
                cat = self.catalog_manager.create_catalog(catalog)
            catalog_id = cat.catalog_id

        # Get current files
        current_files = set()
        for f in dir_path.rglob('*'):
            if f.is_file():
                ext = f.suffix.lower()
                if ext in self.doc_store.ingester.SUPPORTED_EXTENSIONS:
                    current_files.add(str(f.resolve()))

        # Get ingested files
        ingested_docs = self.doc_store.list_documents(catalog_id=catalog_id, limit=100000)
        ingested_paths = {d.file_path: d for d in ingested_docs}

        counts = {'added': 0, 'updated': 0, 'removed': 0, 'unchanged': 0}

        # Ingest new/changed files
        for file_path in current_files:
            existing = ingested_paths.get(file_path)
            try:
                checksum = self.doc_store._compute_checksum(file_path)
                if not existing:
                    self.doc_store.ingest_file(file_path, catalog_id=catalog_id, tags=tags)
                    counts['added'] += 1
                elif existing.checksum != checksum:
                    self.doc_store.ingest_file(file_path, catalog_id=catalog_id, tags=tags)
                    counts['updated'] += 1
                else:
                    counts['unchanged'] += 1
            except Exception as e:
                logger.warning(f"Sync error for {file_path}: {e}")

        # Remove deleted files
        for file_path, doc in ingested_paths.items():
            if file_path not in current_files and file_path.startswith(str(dir_path)):
                self.doc_store.delete_document(doc.doc_id)
                counts['removed'] += 1

        logger.info(f"Sync complete: {counts}")
        return counts


# ─────────────────────────────────────────────
# CLI Interface
# ─────────────────────────────────────────────

class CLI:
    """Command-line interface for Marginalia."""

    def __init__(self, marginalia: Marginalia):
        self.m = marginalia

    def run(self):
        """Run the interactive CLI."""
        print("╔══════════════════════════════════════╗")
        print("║         MARGINALIA v1.0               ║")
        print("║  Personal Knowledge Management        ║")
        print("╚══════════════════════════════════════╝")
        print(f"\nKnowledge base: {self.m.base_path}")
        print(self.m.summary())
        print("\nCommands: ingest, search, ask, report, catalogs, tags, journal, stats, help, quit\n")

        while True:
            try:
                cmd = input("marginalia> ").strip()
                if not cmd:
                    continue
                self._dispatch(cmd)
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit.")
            except EOFError:
                break

    def _dispatch(self, cmd: str):
        parts = cmd.split(None, 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handlers = {
            'ingest': self._cmd_ingest,
            'search': self._cmd_search,
            'ask': self._cmd_ask,
            'report': self._cmd_report,
            'catalogs': self._cmd_catalogs,
            'tags': self._cmd_tags,
            'journal': self._cmd_journal,
            'stats': self._cmd_stats,
            'docs': self._cmd_docs,
            'relations': self._cmd_relations,
            'sync': self._cmd_sync,
            'help': self._cmd_help,
            'quit': self._cmd_quit,
            'exit': self._cmd_quit,
        }

        handler = handlers.get(command)
        if handler:
            handler(args)
        else:
            print(f"Unknown command: {command}. Type 'help' for help.")

    def _cmd_ingest(self, args: str):
        if not args:
            print("Usage: ingest <path> [--catalog <name>] [--tags <tag1,tag2>]")
            return
        parts = args.split()
        path = parts[0]
        catalog = None
        tags = None

        for i, p in enumerate(parts):
            if p == '--catalog' and i + 1 < len(parts):
                catalog = parts[i + 1]
            elif p == '--tags' and i + 1 < len(parts):
                tags = parts[i + 1].split(',')

        try:
            result = self.m.ingest(path, catalog=catalog, tags=tags)
            if isinstance(result, list):
                print(f"✓ Ingested {len(result)} documents")
            else:
                print(f"✓ Ingested: {result.title} ({result.chunk_count} chunks)")
        except Exception as e:
            print(f"✗ Error: {e}")

    def _cmd_search(self, args: str):
        if not args:
            print("Usage: search <query> [--limit N] [--catalog <name>]")
            return

        parts = args.split('--')
        query = parts[0].strip()
        limit = 10
        catalog = None

        for part in parts[1:]:
            if part.startswith('limit '):
                try:
                    limit = int(part.split()[1])
                except Exception:
                    pass
            elif part.startswith('catalog '):
                catalog = part.split(None, 1)[1].strip()

        results = self.m.search(query, limit=limit, catalog=catalog)
        if not results:
            print("No results found.")
            return

        print(f"\nFound {len(results)} results for '{query}':\n")
        for r in results:
            location = ""
            if r.page_number:
                location = f" [p.{r.page_number}]"
            elif r.line_start:
                location = f" [lines {r.line_start}-{r.line_end}]"
            print(f"[{r.rank}] {r.title}{location} (score: {r.score:.3f})")
            print(f"    {r.file_path}")
            print(f"    {r.content[:150].strip()}...")
            print()

    def _cmd_ask(self, args: str):
        if not args:
            print("Usage: ask <question> [--catalog <name>]")
            return

        parts = args.split('--catalog')
        question = parts[0].strip()
        catalog = parts[1].strip() if len(parts) > 1 else None

        print(f"\nSearching knowledge base for: {question}\n")

        try:
            response = self.m.ask(question, catalog=catalog)
            print("─" * 60)
            print(response.answer)
            print("─" * 60)
            print(f"\nSources consulted: {len(response.sources_consulted)}")
            for src in response.sources_consulted[:5]:
                print(f"  • {src}")
            if response.journal_entry_id:
                print(f"\n✓ Saved to journal: {response.journal_entry_id}")
        except Exception as e:
            print(f"✗ Error: {e}")
            logger.exception("Ask error")

    def _cmd_report(self, args: str):
        if not args:
            print("Usage: report <topic>")
            return
        print(f"\nGenerating report on: {args}\n")
        try:
            report = self.m.generate_report(args)
            print(report[:3000])
            if len(report) > 3000:
                print(f"\n... (report truncated, {len(report)} chars total)")
        except Exception as e:
            print(f"✗ Error: {e}")

    def _cmd_catalogs(self, args: str):
        catalogs = self.m.list_catalogs()
        if not catalogs:
            print("No catalogs found.")
            return
        print(f"\nCatalogs ({len(catalogs)}):")
        for cat in catalogs:
            print(f"  • {cat.name}: {cat.description}")

    def _cmd_tags(self, args: str):
        tags = self.m.list_tags()
        if not tags:
            print("No tags found.")
            return
        print(f"\nTags ({len(tags)}):")
        for tag in tags:
            print(f"  • {tag.name} ({tag.color})")

    def _cmd_journal(self, args: str):
        if args.startswith('search '):
            query = args[7:].strip()
            entries = self.m.search_journal(query)
        else:
            entries = self.m.list_journal_entries(limit=10)

        if not entries:
            print("No journal entries found.")
            return

        print(f"\nJournal entries ({len(entries)}):")
        for entry in entries:
            print(f"\n  [{entry.entry_id[:8]}] {entry.title}")
            print(f"  {entry.created_at}")
            print(f"  {entry.content[:200].strip()}...")

    def _cmd_docs(self, args: str):
        catalog = args.strip() if args else None
        docs = self.m.list_documents(catalog=catalog, limit=20)
        if not docs:
            print("No documents found.")
            return
        print(f"\nDocuments ({len(docs)}):")
        for doc in docs:
            print(f"  [{doc.doc_id[:8]}] {doc.title}")
            print(f"    {doc.file_path}")
            print(f"    {doc.content_type} | {doc.word_count:,} words | {doc.chunk_count} chunks")

    def _cmd_relations(self, args: str):
        if not args:
            print("Usage: relations <doc_id>")
            return
        relations = self.m.get_relations(args)
        if not relations:
            print("No relations found.")
            return
        print(f"\nRelations for {args}:")
        for rel in relations:
            print(f"  {rel.source_doc_id[:8]} --[{rel.relation_type}]--> {rel.target_doc_id[:8]} (conf: {rel.confidence:.2f})")

    def _cmd_sync(self, args: str):
        if not args:
            print("Usage: sync <directory>")
            return
        try:
            counts = self.m.sync_directory(args)
            print(f"✓ Sync complete: {counts}")
        except Exception as e:
            print(f"✗ Error: {e}")

    def _cmd_stats(self, args: str):
        print(self.m.summary())

    def _cmd_help(self, args: str):
        print("""
Marginalia Commands:
  ingest <path> [--catalog <name>] [--tags <t1,t2>]
      Ingest a file or directory

  search <query> [--limit N] [--catalog <name>]
      Search the knowledge base

  ask <question> [--catalog <name>]
      Ask the research agent a question

  report <topic>
      Generate a research report

  catalogs
      List all catalogs

  tags
      List all tags

  journal [search <query>]
      View or search journal entries

  docs [catalog_name]
      List documents

  relations <doc_id>
      Show document relations

  sync <directory>
      Sync a directory with the knowledge base

  stats
      Show knowledge base statistics

  quit / exit
      Exit Marginalia
""")

    def _cmd_quit(self, args: str):
        print("Goodbye!")
        raise SystemExit(0)


# ─────────────────────────────────────────────
# Factory / Entry Point
# ─────────────────────────────────────────────

def create_marginalia(base_path: str = "~/.marginalia",
                      llm_provider: str = "anthropic",
                      **kwargs) -> Marginalia:
    """
    Create a Marginalia instance with sensible defaults.

    Args:
        base_path: Knowledge base directory
        llm_provider: 'anthropic' or 'openai'
        **kwargs: Additional arguments passed to Marginalia

    Returns:
        Configured Marginalia instance
    """
    base_path = str(Path(base_path).expanduser())
    return Marginalia(
        base_path=base_path,
        llm_provider=llm_provider,
        **kwargs
    )


def main():
    """Main entry point for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Marginalia - Personal Knowledge Management System'
    )
    parser.add_argument('--base-path', default='~/.marginalia',
                        help='Knowledge base directory')
    parser.add_argument('--provider', default='anthropic',
                        choices=['anthropic', 'openai'],
                        help='LLM provider')
    parser.add_argument('--model', default=None,
                        help='LLM model name')
    parser.add_argument('--embeddings', action='store_true',
                        help='Enable semantic search')
    parser.add_argument('--reranking', action='store_true',
                        help='Enable result reranking')

    # Subcommands
    subparsers = parser.add_subparsers(dest='command')

    # Interactive mode
    subparsers.add_parser('interactive', help='Start interactive CLI')

    # Ingest
    ingest_parser = subparsers.add_parser('ingest', help='Ingest files')
    ingest_parser.add_argument('path', help='File or directory to ingest')
    ingest_parser.add_argument('--catalog', help='Catalog name')
    ingest_parser.add_argument('--tags', help='Comma-separated tags')

    # Search
    search_parser = subparsers.add_parser('search', help='Search knowledge base')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=10)
    search_parser.add_argument('--catalog', help='Filter by catalog')

    # Ask
    ask_parser = subparsers.add_parser('ask', help='Ask the research agent')
    ask_parser.add_argument('question', help='Research question')
    ask_parser.add_argument('--catalog', help='Filter by catalog')

    # Stats
    subparsers.add_parser('stats', help='Show statistics')

    args = parser.parse_args()

    # Create Marginalia instance
    m = create_marginalia(
        base_path=args.base_path,
        llm_provider=args.provider,
        llm_model=args.model,
        use_embeddings=args.embeddings,
        use_reranking=args.reranking,
    )

    if args.command == 'ingest' or (hasattr(args, 'path') and args.command == 'ingest'):
        tags = args.tags.split(',') if args.tags else None
        result = m.ingest(args.path, catalog=args.catalog, tags=tags)
        if isinstance(result, list):
            print(f"Ingested {len(result)} documents")
        else:
            print(f"Ingested: {result.title}")

    elif args.command == 'search':
        results = m.search(args.query, limit=args.limit, catalog=args.catalog)
        for r in results:
            print(f"[{r.rank}] {r.title} (score: {r.score:.3f})")
            print(f"    {r.content[:200]}...")
            print()

    elif args.command == 'ask':
        response = m.ask(args.question, catalog=args.catalog)
        print(response.answer)

    elif args.command == 'stats':
        print(m.summary())

    else:
        # Default: interactive mode
        cli = CLI(m)
        cli.run()


if __name__ == '__main__':
    main()