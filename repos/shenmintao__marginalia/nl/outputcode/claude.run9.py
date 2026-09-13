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
    created_at: str
    modified_at: str
    ingested_at: str
    checksum: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    catalog_id: Optional[str] = None
    folder_path: str = ""
    language: str = "en"
    word_count: int = 0
    page_count: int = 0
    summary: str = ""
    relations: List[str] = field(default_factory=list)


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
    highlight: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Citation:
    """A citation for a piece of information."""
    citation_id: str
    doc_id: str
    file_path: str
    title: str
    quote: str
    page_number: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    section_title: Optional[str] = None
    relevance_note: str = ""


@dataclass
class InvestigationNote:
    """A durable investigation note for future recall."""
    note_id: str
    query: str
    answer: str
    citations: List[Citation]
    created_at: str
    tags: List[str] = field(default_factory=list)
    follow_up_questions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Catalog:
    """A catalog grouping related documents."""
    catalog_id: str
    name: str
    description: str
    created_at: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class View:
    """A saved search/filter view."""
    view_id: str
    name: str
    query: str
    filters: Dict[str, Any]
    created_at: str
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
    """A journal entry for tracking research activity."""
    entry_id: str
    content: str
    created_at: str
    tags: List[str] = field(default_factory=list)
    linked_docs: List[str] = field(default_factory=list)
    linked_notes: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Database Layer
# ─────────────────────────────────────────────────────────────────────────────

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
                summary TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                relations TEXT DEFAULT '[]'
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

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                doc_id UNINDEXED,
                content,
                section_title,
                tokenize='porter unicode61'
            );

            CREATE TABLE IF NOT EXISTS catalogs (
                catalog_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS views (
                view_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                query TEXT,
                filters TEXT DEFAULT '{}',
                created_at TEXT,
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
                content TEXT NOT NULL,
                created_at TEXT,
                tags TEXT DEFAULT '[]',
                linked_docs TEXT DEFAULT '[]',
                linked_notes TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS investigation_notes (
                note_id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                answer TEXT NOT NULL,
                citations TEXT DEFAULT '[]',
                created_at TEXT,
                tags TEXT DEFAULT '[]',
                follow_up_questions TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS tags (
                tag_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                color TEXT DEFAULT '#888888',
                description TEXT DEFAULT '',
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS doc_tags (
                doc_id TEXT NOT NULL,
                tag_name TEXT NOT NULL,
                PRIMARY KEY (doc_id, tag_name),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
            CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_doc_id);
            CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_doc_id);
            CREATE INDEX IF NOT EXISTS idx_documents_folder ON documents(folder_path);
            CREATE INDEX IF NOT EXISTS idx_documents_catalog ON documents(catalog_id);
            CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(file_type);
        """)
        conn.commit()

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.conn.execute(query, params)

    def executemany(self, query: str, params_list: list) -> sqlite3.Cursor:
        return self.conn.executemany(query, params_list)

    def commit(self):
        self.conn.commit()

    def fetchall(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        return self.conn.execute(query, params).fetchall()

    def fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        return self.conn.execute(query, params).fetchone()


# ─────────────────────────────────────────────────────────────────────────────
# Text Extraction
# ─────────────────────────────────────────────────────────────────────────────

class TextExtractor:
    """Extracts text content from various file types."""

    SUPPORTED_TYPES = {
        'text': ['.txt', '.md', '.rst', '.log', '.csv', '.tsv', '.json', '.xml',
                 '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.py', '.js',
                 '.html', '.htm', '.css', '.sh', '.bash', '.zsh', '.fish'],
        'pdf': ['.pdf'],
        'docx': ['.docx', '.doc'],
        'spreadsheet': ['.xlsx', '.xls', '.ods'],
        'image': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'],
        'archive': ['.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.tar.gz', '.tar.bz2'],
    }

    def __init__(self):
        self._type_map = {}
        for ftype, exts in self.SUPPORTED_TYPES.items():
            for ext in exts:
                self._type_map[ext] = ftype

    def get_file_type(self, file_path: str) -> str:
        path = Path(file_path)
        suffix = path.suffix.lower()
        # Check compound extensions
        if path.name.endswith('.tar.gz'):
            return 'archive'
        if path.name.endswith('.tar.bz2'):
            return 'archive'
        return self._type_map.get(suffix, 'binary')

    def extract(self, file_path: str) -> Dict[str, Any]:
        """Extract text and metadata from a file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_type = self.get_file_type(file_path)
        result = {
            'text': '',
            'pages': [],
            'lines': [],
            'metadata': {},
            'file_type': file_type,
            'word_count': 0,
            'page_count': 0,
        }

        try:
            if file_type == 'text':
                result.update(self._extract_text(file_path))
            elif file_type == 'pdf':
                result.update(self._extract_pdf(file_path))
            elif file_type == 'docx':
                result.update(self._extract_docx(file_path))
            elif file_type == 'spreadsheet':
                result.update(self._extract_spreadsheet(file_path))
            elif file_type == 'image':
                result.update(self._extract_image(file_path))
            elif file_type == 'archive':
                result.update(self._extract_archive(file_path))
            else:
                result['text'] = f"[Binary file: {path.name}]"
        except Exception as e:
            logger.warning(f"Extraction error for {file_path}: {e}")
            result['text'] = f"[Extraction failed: {e}]"
            result['metadata']['extraction_error'] = str(e)

        if result['text']:
            result['word_count'] = len(result['text'].split())
            result['lines'] = result['text'].splitlines()

        return result

    def _extract_text(self, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        suffix = path.suffix.lower()

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
        except Exception:
            with open(file_path, 'rb') as f:
                text = f.read().decode('utf-8', errors='replace')

        metadata = {}
        if suffix == '.json':
            try:
                data = json.loads(text)
                metadata['json_keys'] = list(data.keys()) if isinstance(data, dict) else []
            except Exception:
                pass
        elif suffix in ('.yaml', '.yml'):
            metadata['format'] = 'yaml'
        elif suffix == '.md':
            metadata['format'] = 'markdown'
            # Extract headers
            headers = re.findall(r'^#{1,6}\s+(.+)$', text, re.MULTILINE)
            metadata['headers'] = headers

        return {'text': text, 'metadata': metadata}

    def _extract_pdf(self, file_path: str) -> Dict[str, Any]:
        if not HAS_PYPDF:
            return {'text': f"[PDF extraction requires pypdf: {Path(file_path).name}]",
                    'metadata': {'error': 'pypdf not installed'}}

        pages = []
        text_parts = []
        metadata = {}

        try:
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                metadata['page_count'] = len(reader.pages)

                if reader.metadata:
                    for key, val in reader.metadata.items():
                        if val:
                            metadata[key.strip('/')] = str(val)

                for i, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text() or ''
                        pages.append({'page': i + 1, 'text': page_text})
                        text_parts.append(f"[Page {i+1}]\n{page_text}")
                    except Exception as e:
                        pages.append({'page': i + 1, 'text': f'[Error: {e}]'})

        except Exception as e:
            return {'text': f"[PDF read error: {e}]", 'metadata': {'error': str(e)}}

        return {
            'text': '\n\n'.join(text_parts),
            'pages': pages,
            'page_count': len(pages),
            'metadata': metadata,
        }

    def _extract_docx(self, file_path: str) -> Dict[str, Any]:
        if not HAS_DOCX:
            return {'text': f"[DOCX extraction requires python-docx: {Path(file_path).name}]",
                    'metadata': {'error': 'python-docx not installed'}}

        try:
            doc = docx.Document(file_path)
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)

            # Extract tables
            table_texts = []
            for table in doc.tables:
                rows = []
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    rows.append(' | '.join(cells))
                table_texts.append('\n'.join(rows))

            text = '\n\n'.join(paragraphs)
            if table_texts:
                text += '\n\n[Tables]\n' + '\n\n'.join(table_texts)

            metadata = {}
            try:
                core_props = doc.core_properties
                if core_props.author:
                    metadata['author'] = core_props.author
                if core_props.title:
                    metadata['title'] = core_props.title
                if core_props.subject:
                    metadata['subject'] = core_props.subject
            except Exception:
                pass

            return {'text': text, 'metadata': metadata}
        except Exception as e:
            return {'text': f"[DOCX read error: {e}]", 'metadata': {'error': str(e)}}

    def _extract_spreadsheet(self, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == '.csv' or suffix == '.tsv':
            return self._extract_text(file_path)

        if not HAS_OPENPYXL:
            return {'text': f"[Spreadsheet extraction requires openpyxl: {path.name}]",
                    'metadata': {'error': 'openpyxl not installed'}}

        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheets_text = []
            metadata = {'sheets': []}

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                metadata['sheets'].append(sheet_name)
                rows = []
                for row in ws.iter_rows(values_only=True):
                    cells = [str(c) if c is not None else '' for c in row]
                    if any(c.strip() for c in cells):
                        rows.append(' | '.join(cells))
                if rows:
                    sheets_text.append(f"[Sheet: {sheet_name}]\n" + '\n'.join(rows))

            return {'text': '\n\n'.join(sheets_text), 'metadata': metadata}
        except Exception as e:
            return {'text': f"[Spreadsheet read error: {e}]", 'metadata': {'error': str(e)}}

    def _extract_image(self, file_path: str) -> Dict[str, Any]:
        metadata = {}
        if HAS_PIL:
            try:
                with Image.open(file_path) as img:
                    metadata['width'] = img.width
                    metadata['height'] = img.height
                    metadata['mode'] = img.mode
                    metadata['format'] = img.format
                    if hasattr(img, '_getexif') and img._getexif():
                        metadata['has_exif'] = True
            except Exception as e:
                metadata['error'] = str(e)

        text = f"[Image file: {Path(file_path).name}"
        if metadata:
            if 'width' in metadata:
                text += f", {metadata['width']}x{metadata['height']}"
            if 'format' in metadata:
                text += f", {metadata['format']}"
        text += "]"

        return {'text': text, 'metadata': metadata}

    def _extract_archive(self, file_path: str) -> Dict[str, Any]:
        members = []
        text_parts = []
        metadata = {}

        try:
            if zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, 'r') as zf:
                    members = zf.namelist()
                    metadata['archive_type'] = 'zip'
                    metadata['member_count'] = len(members)
                    # Extract text from small text files within archive
                    for name in members[:50]:  # Limit to first 50
                        if any(name.endswith(ext) for ext in ['.txt', '.md', '.json', '.csv', '.log']):
                            try:
                                with zf.open(name) as f:
                                    content = f.read(65536).decode('utf-8', errors='replace')
                                    text_parts.append(f"[Archive member: {name}]\n{content}")
                            except Exception:
                                pass
            elif tarfile.is_tarfile(file_path):
                with tarfile.open(file_path, 'r:*') as tf:
                    members = tf.getnames()
                    metadata['archive_type'] = 'tar'
                    metadata['member_count'] = len(members)
                    for member in tf.getmembers()[:50]:
                        if member.isfile() and any(member.name.endswith(ext)
                                                    for ext in ['.txt', '.md', '.json', '.csv', '.log']):
                            try:
                                f = tf.extractfile(member)
                                if f:
                                    content = f.read(65536).decode('utf-8', errors='replace')
                                    text_parts.append(f"[Archive member: {member.name}]\n{content}")
                            except Exception:
                                pass
        except Exception as e:
            metadata['error'] = str(e)

        member_list = '\n'.join(members[:100])
        text = f"[Archive: {Path(file_path).name}, {len(members)} members]\n\nContents:\n{member_list}"
        if text_parts:
            text += '\n\n' + '\n\n'.join(text_parts)

        metadata['members'] = members[:200]
        return {'text': text, 'metadata': metadata}


# ─────────────────────────────────────────────────────────────────────────────
# Chunker
# ─────────────────────────────────────────────────────────────────────────────

class Chunker:
    """Splits document text into searchable chunks."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, doc_id: str, text: str, pages: List[Dict] = None,
                       file_type: str = 'text') -> List[Chunk]:
        """Chunk a document into overlapping text windows."""
        if not text or not text.strip():
            return []

        if pages and len(pages) > 1:
            return self._chunk_by_pages(doc_id, pages)
        else:
            return self._chunk_by_words(doc_id, text)

    def _chunk_by_pages(self, doc_id: str, pages: List[Dict]) -> List[Chunk]:
        chunks = []
        for page_info in pages:
            page_num = page_info.get('page', 1)
            page_text = page_info.get('text', '')
            if not page_text.strip():
                continue

            # Split page into sub-chunks if large
            sub_chunks = self._split_text(page_text)
            for i, (sub_text, start, end) in enumerate(sub_chunks):
                chunk_id = str(uuid.uuid4())
                chunk = Chunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    content=sub_text,
                    chunk_index=len(chunks),
                    start_offset=start,
                    end_offset=end,
                    page_number=page_num,
                )
                chunks.append(chunk)
        return chunks

    def _chunk_by_words(self, doc_id: str, text: str) -> List[Chunk]:
        chunks = []
        # Try to split by sections first
        sections = self._split_by_sections(text)

        if len(sections) > 1:
            for section_title, section_text, section_start in sections:
                sub_chunks = self._split_text(section_text)
                for sub_text, start, end in sub_chunks:
                    chunk_id = str(uuid.uuid4())
                    # Find line numbers
                    line_start = text[:section_start + start].count('\n') + 1
                    line_end = text[:section_start + end].count('\n') + 1
                    chunk = Chunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        content=sub_text,
                        chunk_index=len(chunks),
                        start_offset=section_start + start,
                        end_offset=section_start + end,
                        section_title=section_title,
                        line_start=line_start,
                        line_end=line_end,
                    )
                    chunks.append(chunk)
        else:
            sub_chunks = self._split_text(text)
            for sub_text, start, end in sub_chunks:
                chunk_id = str(uuid.uuid4())
                line_start = text[:start].count('\n') + 1
                line_end = text[:end].count('\n') + 1
                chunk = Chunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    content=sub_text,
                    chunk_index=len(chunks),
                    start_offset=start,
                    end_offset=end,
                    line_start=line_start,
                    line_end=line_end,
                )
                chunks.append(chunk)

        return chunks

    def _split_by_sections(self, text: str) -> List[Tuple[str, str, int]]:
        """Split text by markdown headers or similar section markers."""
        sections = []
        pattern = re.compile(r'^(#{1,6}\s+.+)$', re.MULTILINE)
        matches = list(pattern.finditer(text))

        if not matches:
            return [('', text, 0)]

        # Add content before first header
        if matches[0].start() > 0:
            sections.append(('', text[:matches[0].start()], 0))

        for i, match in enumerate(matches):
            title = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_text = text[start:end].strip()
            if section_text:
                sections.append((title, section_text, start))

        return sections if sections else [('', text, 0)]

    def _split_text(self, text: str) -> List[Tuple[str, int, int]]:
        """Split text into overlapping word-based chunks."""
        words = text.split()
        if not words:
            return []

        chunks = []
        i = 0
        pos = 0

        while i < len(words):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)

            # Find actual position in text
            start_pos = text.find(words[i], pos) if i < len(words) else len(text)
            end_pos = start_pos + len(chunk_text)

            chunks.append((chunk_text, start_pos, min(end_pos, len(text))))

            if i + self.chunk_size >= len(words):
                break

            i += self.chunk_size - self.chunk_overlap
            pos = start_pos

        return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Embedding Engine
# ─────────────────────────────────────────────────────────────────────────────

class EmbeddingEngine:
    """Manages text embeddings for semantic search."""

    def __init__(self, model: str = "text-embedding-3-small", provider: str = "openai"):
        self.model = model
        self.provider = provider
        self._client = None
        self._available = False
        self._init_client()

    def _init_client(self):
        if self.provider == "openai" and HAS_OPENAI:
            try:
                self._client = openai.OpenAI()
                self._available = True
            except Exception as e:
                logger.warning(f"OpenAI embedding client init failed: {e}")
        elif self.provider == "anthropic":
            logger.info("Anthropic does not provide embeddings; using TF-IDF fallback")

    @property
    def available(self) -> bool:
        return self._available

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts."""
        if not self._available or not texts:
            return [self._tfidf_embed(t) for t in texts]

        try:
            if self.provider == "openai":
                response = self._client.embeddings.create(
                    model=self.model,
                    input=texts
                )
                return [item.embedding for item in response.data]
        except Exception as e:
            logger.warning(f"Embedding API error: {e}, falling back to TF-IDF")
            return [self._tfidf_embed(t) for t in texts]

        return [self._tfidf_embed(t) for t in texts]

    def embed_single(self, text: str) -> List[float]:
        """Embed a single text."""
        results = self.embed([text])
        return results[0] if results else []

    def _tfidf_embed(self, text: str, dim: int = 128) -> List[float]:
        """Simple TF-IDF-like embedding as fallback."""
        words = re.findall(r'\w+', text.lower())
        if not words:
            return [0.0] * dim

        freq = Counter(words)
        total = sum(freq.values())
        vec = [0.0] * dim

        for word, count in freq.items():
            tf = count / total
            h = hash(word) % dim
            vec[h] += tf

        # Normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    def serialize_embedding(self, embedding: List[float]) -> bytes:
        """Serialize embedding to bytes for storage."""
        import struct
        return struct.pack(f'{len(embedding)}f', *embedding)

    def deserialize_embedding(self, data: bytes) -> List[float]:
        """Deserialize embedding from bytes."""
        import struct
        n = len(data) // 4
        return list(struct.unpack(f'{n}f', data))


# ─────────────────────────────────────────────────────────────────────────────
# Search Engine
# ─────────────────────────────────────────────────────────────────────────────

class SearchEngine:
    """Handles lexical and semantic search over the knowledge base."""

    def __init__(self, db: Database, embedding_engine: Optional[EmbeddingEngine] = None):
        self.db = db
        self.embedding_engine = embedding_engine

    def lexical_search(self, query: str, limit: int = 20,
                       filters: Optional[Dict] = None) -> List[SearchResult]:
        """BM25-style full-text search using SQLite FTS5."""
        results = []

        try:
            # Build filter conditions
            filter_sql, filter_params = self._build_filters(filters)

            sql = f"""
                SELECT
                    c.chunk_id, c.doc_id, c.content, c.page_number,
                    c.line_start, c.line_end, c.section_title,
                    d.file_path, d.title, d.file_type, d.tags, d.metadata,
                    rank
                FROM chunks_fts
                JOIN chunks c ON chunks_fts.chunk_id = c.chunk_id
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE chunks_fts MATCH ?
                {filter_sql}
                ORDER BY rank
                LIMIT ?
            """
            params = (self._prepare_fts_query(query),) + filter_params + (limit,)
            rows = self.db.fetchall(sql, params)

            for i, row in enumerate(rows):
                highlight = self._highlight(row['content'], query)
                result = SearchResult(
                    doc_id=row['doc_id'],
                    chunk_id=row['chunk_id'],
                    file_path=row['file_path'],
                    title=row['title'],
                    content=row['content'],
                    score=float(-row['rank']) if row['rank'] else 0.0,
                    rank=i + 1,
                    page_number=row['page_number'],
                    line_start=row['line_start'],
                    line_end=row['line_end'],
                    section_title=row['section_title'],
                    highlight=highlight,
                    metadata=json.loads(row['metadata'] or '{}'),
                )
                results.append(result)
        except Exception as e:
            logger.warning(f"FTS search error: {e}, falling back to LIKE search")
            results = self._fallback_search(query, limit, filters)

        return results

    def _fallback_search(self, query: str, limit: int,
                         filters: Optional[Dict] = None) -> List[SearchResult]:
        """Simple LIKE-based search as fallback."""
        results = []
        terms = query.lower().split()
        if not terms:
            return results

        like_conditions = ' AND '.join(['LOWER(c.content) LIKE ?' for _ in terms])
        params = tuple(f'%{term}%' for term in terms) + (limit,)

        sql = f"""
            SELECT c.chunk_id, c.doc_id, c.content, c.page_number,
                   c.line_start, c.line_end, c.section_title,
                   d.file_path, d.title, d.metadata
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE {like_conditions}
            LIMIT ?
        """

        try:
            rows = self.db.fetchall(sql, params)
            for i, row in enumerate(rows):
                result = SearchResult(
                    doc_id=row['doc_id'],
                    chunk_id=row['chunk_id'],
                    file_path=row['file_path'],
                    title=row['title'],
                    content=row['content'],
                    score=1.0 / (i + 1),
                    rank=i + 1,
                    page_number=row['page_number'],
                    line_start=row['line_start'],
                    line_end=row['line_end'],
                    section_title=row['section_title'],
                    highlight=self._highlight(row['content'], query),
                    metadata=json.loads(row['metadata'] or '{}'),
                )
                results.append(result)
        except Exception as e:
            logger.error(f"Fallback search error: {e}")

        return results

    def semantic_search(self, query: str, limit: int = 20,
                        filters: Optional[Dict] = None) -> List[SearchResult]:
        """Semantic search using embeddings."""
        if not self.embedding_engine or not self.embedding_engine.available:
            logger.info("Semantic search not available, using lexical search")
            return self.lexical_search(query, limit, filters)

        query_embedding = self.embedding_engine.embed_single(query)
        if not query_embedding:
            return self.lexical_search(query, limit, filters)

        # Fetch all chunks with embeddings
        rows = self.db.fetchall("""
            SELECT c.chunk_id, c.doc_id, c.content, c.page_number,
                   c.line_start, c.line_end, c.section_title, c.embedding,
                   d.file_path, d.title, d.metadata
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.embedding IS NOT NULL
        """)

        scored = []
        for row in rows:
            try:
                emb = self.embedding_engine.deserialize_embedding(row['embedding'])
                score = self.embedding_engine.cosine_similarity(query_embedding, emb)
                scored.append((score, row))
            except Exception:
                pass

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for i, (score, row) in enumerate(scored[:limit]):
            result = SearchResult(
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
                highlight=self._highlight(row['content'], query),
                metadata=json.loads(row['metadata'] or '{}'),
            )
            results.append(result)

        return results

    def hybrid_search(self, query: str, limit: int = 20,
                      filters: Optional[Dict] = None,
                      lexical_weight: float = 0.5) -> List[SearchResult]:
        """Combine lexical and semantic search results."""
        lexical = self.lexical_search(query, limit * 2, filters)
        semantic = self.semantic_search(query, limit * 2, filters)

        # Reciprocal rank fusion
        scores: Dict[str, float] = defaultdict(float)
        chunk_map: Dict[str, SearchResult] = {}

        k = 60  # RRF constant
        for i, r in enumerate(lexical):
            scores[r.chunk_id] += lexical_weight * (1.0 / (k + i + 1))
            chunk_map[r.chunk_id] = r

        for i, r in enumerate(semantic):
            scores[r.chunk_id] += (1 - lexical_weight) * (1.0 / (k + i + 1))
            if r.chunk_id not in chunk_map:
                chunk_map[r.chunk_id] = r

        sorted_chunks = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for rank, (chunk_id, score) in enumerate(sorted_chunks[:limit]):
            r = chunk_map[chunk_id]
            r.score = score
            r.rank = rank + 1
            results.append(r)

        return results

    def rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Simple keyword-based reranking."""
        query_terms = set(re.findall(r'\w+', query.lower()))

        for result in results:
            content_lower = result.content.lower()
            content_terms = set(re.findall(r'\w+', content_lower))

            # Boost for exact phrase match
            if query.lower() in content_lower:
                result.score *= 2.0

            # Boost for term overlap
            overlap = len(query_terms & content_terms) / max(len(query_terms), 1)
            result.score *= (1 + overlap)

        results.sort(key=lambda x: x.score, reverse=True)
        for i, r in enumerate(results):
            r.rank = i + 1

        return results

    def search_by_source_quota(self, query: str, max_per_source: int = 3,
                                total_limit: int = 20,
                                filters: Optional[Dict] = None) -> List[SearchResult]:
        """Search with per-source quotas to ensure diversity."""
        all_results = self.lexical_search(query, total_limit * max_per_source, filters)

        source_counts: Dict[str, int] = defaultdict(int)
        filtered = []

        for result in all_results:
            if source_counts[result.doc_id] < max_per_source:
                filtered.append(result)
                source_counts[result.doc_id] += 1
            if len(filtered) >= total_limit:
                break

        return filtered

    def _prepare_fts_query(self, query: str) -> str:
        """Prepare query for FTS5."""
        # Escape special FTS5 characters
        query = re.sub(r'[^\w\s"*-]', ' ', query)
        terms = query.strip().split()
        if not terms:
            return '""'
        # Use phrase search for multi-word queries
        if len(terms) == 1:
            return f'"{terms[0]}"*'
        return ' '.join(f'"{t}"*' for t in terms)

    def _build_filters(self, filters: Optional[Dict]) -> Tuple[str, tuple]:
        """Build SQL filter conditions."""
        if not filters:
            return '', ()

        conditions = []
        params = []

        if 'file_type' in filters:
            conditions.append("AND d.file_type = ?")
            params.append(filters['file_type'])

        if 'catalog_id' in filters:
            conditions.append("AND d.catalog_id = ?")
            params.append(filters['catalog_id'])

        if 'folder_path' in filters:
            conditions.append("AND d.folder_path LIKE ?")
            params.append(f"{filters['folder_path']}%")

        if 'tags' in filters and filters['tags']:
            tag_placeholders = ','.join('?' * len(filters['tags']))
            conditions.append(f"""AND d.doc_id IN (
                SELECT doc_id FROM doc_tags WHERE tag_name IN ({tag_placeholders})
            )""")
            params.extend(filters['tags'])

        return ' '.join(conditions), tuple(params)

    def _highlight(self, text: str, query: str, context_words: int = 10) -> str:
        """Create a highlighted snippet."""
        terms = re.findall(r'\w+', query.lower())
        if not terms:
            return text[:200]

        words = text.split()
        best_pos = 0
        best_score = 0

        for i, word in enumerate(words):
            score = sum(1 for t in terms if t in word.lower())
            if score > best_score:
                best_score = score
                best_pos = i

        start = max(0, best_pos - context_words)
        end = min(len(words), best_pos + context_words)
        snippet = ' '.join(words[start:end])

        # Mark matching terms
        for term in terms:
            snippet = re.sub(
                f'({re.escape(term)})',
                r'**\1**',
                snippet,
                flags=re.IGNORECASE
            )

        return ('...' if start > 0 else '') + snippet + ('...' if end < len(words) else '')


# ─────────────────────────────────────────────────────────────────────────────
# Relation Miner
# ─────────────────────────────────────────────────────────────────────────────

class RelationMiner:
    """Mines relations between documents."""

    def __init__(self, db: Database):
        self.db = db

    def mine_relations(self, doc_id: str, text: str,
                       all_docs: List[DocumentRecord]) -> List[Relation]:
        """Mine relations between a document and others."""
        relations = []
        doc_titles = {d.doc_id: d.title for d in all_docs if d.doc_id != doc_id}

        # Citation/reference detection
        for other_id, other_title in doc_titles.items():
            if other_title and len(other_title) > 3:
                if other_title.lower() in text.lower():
                    relation = Relation(
                        relation_id=str(uuid.uuid4()),
                        source_doc_id=doc_id,
                        target_doc_id=other_id,
                        relation_type='references',
                        confidence=0.8,
                        created_at=datetime.datetime.utcnow().isoformat(),
                    )
                    relations.append(relation)

        # URL/file path references
        urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', text)
        file_refs = re.findall(r'(?:file://|\.\.?/)[^\s<>"{}|\\^`\[\]]+', text)

        for other_doc in all_docs:
            if other_doc.doc_id == doc_id:
                continue
            other_path = other_doc.file_path
            for ref in file_refs:
                if Path(ref).name in other_path:
                    relation = Relation(
                        relation_id=str(uuid.uuid4()),
                        source_doc_id=doc_id,
                        target_doc_id=other_doc.doc_id,
                        relation_type='links_to',
                        confidence=0.9,
                        created_at=datetime.datetime.utcnow().isoformat(),
                        metadata={'reference': ref},
                    )
                    relations.append(relation)

        return relations

    def compute_similarity_relations(self, doc_id: str,
                                     chunks: List[Chunk],
                                     all_chunks: List[Chunk],
                                     embedding_engine: EmbeddingEngine,
                                     threshold: float = 0.8) -> List[Relation]:
        """Find similar documents using embedding similarity."""
        if not embedding_engine.available or not chunks:
            return []

        relations = []
        doc_embedding = self._average_embedding(
            [c.embedding for c in chunks if c.embedding], embedding_engine
        )
        if not doc_embedding:
            return []

        # Group chunks by doc
        doc_chunks: Dict[str, List[Chunk]] = defaultdict(list)
        for chunk in all_chunks:
            if chunk.doc_id != doc_id:
                doc_chunks[chunk.doc_id].append(chunk)

        for other_doc_id, other_chunks in doc_chunks.items():
            other_embedding = self._average_embedding(
                [c.embedding for c in other_chunks if c.embedding], embedding_engine
            )
            if not other_embedding:
                continue

            sim = embedding_engine.cosine_similarity(doc_embedding, other_embedding)
            if sim >= threshold:
                relation = Relation(
                    relation_id=str(uuid.uuid4()),
                    source_doc_id=doc_id,
                    target_doc_id=other_doc_id,
                    relation_type='similar_to',
                    confidence=sim,
                    created_at=datetime.datetime.utcnow().isoformat(),
                    metadata={'similarity': sim},
                )
                relations.append(relation)

        return relations

    def _average_embedding(self, embeddings: List[Optional[List[float]]],
                            engine: EmbeddingEngine) -> Optional[List[float]]:
        """Compute average of embeddings."""
        valid = [e for e in embeddings if e]
        if not valid:
            return None

        dim = len(valid[0])
        avg = [0.0] * dim
        for emb in valid:
            for i, v in enumerate(emb):
                avg[i] += v / len(valid)

        return avg


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class IngestionPipeline:
    """Handles document ingestion into the knowledge base."""

    def __init__(self, db: Database, extractor: TextExtractor,
                 chunker: Chunker, embedding_engine: Optional[EmbeddingEngine] = None,
                 relation_miner: Optional[RelationMiner] = None):
        self.db = db
        self.extractor = extractor
        self.chunker = chunker
        self.embedding_engine = embedding_engine
        self.relation_miner = relation_miner

    def ingest_file(self, file_path: str, catalog_id: Optional[str] = None,
                    tags: Optional[List[str]] = None,
                    metadata: Optional[Dict] = None) -> Optional[DocumentRecord]:
        """Ingest a single file into the knowledge base."""
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        # Check if already ingested (by checksum)
        checksum = self._compute_checksum(file_path)
        existing = self.db.fetchone(
            "SELECT doc_id FROM documents WHERE checksum = ? AND file_path = ?",
            (checksum, str(path.resolve()))
        )
        if existing:
            logger.info(f"File already ingested: {file_path}")
            return self._load_document(existing['doc_id'])

        # Extract content
        extraction = self.extractor.extract(file_path)
        file_type = extraction['file_type']
        text = extraction['text']
        pages = extraction.get('pages', [])
        ext_metadata = extraction.get('metadata', {})

        # Determine title
        title = ext_metadata.get('title') or path.stem

        # Build document record
        stat = path.stat()
        doc_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()

        doc_metadata = {**ext_metadata, **(metadata or {})}
        doc_tags = tags or []

        doc = DocumentRecord(
            doc_id=doc_id,
            file_path=str(path.resolve()),
            title=title,
            file_type=file_type,
            size_bytes=stat.st_size,
            created_at=datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified_at=datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            ingested_at=now,
            checksum=checksum,
            tags=doc_tags,
            metadata=doc_metadata,
            catalog_id=catalog_id,
            folder_path=str(path.parent.resolve()),
            word_count=extraction.get('word_count', 0),
            page_count=extraction.get('page_count', len(pages)),
        )

        # Store document
        self._store_document(doc)

        # Store tags
        for tag in doc_tags:
            self._ensure_tag(tag)
            try:
                self.db.execute(
                    "INSERT OR IGNORE INTO doc_tags (doc_id, tag_name) VALUES (?, ?)",
                    (doc_id, tag)
                )
            except Exception:
                pass

        # Chunk and store
        chunks = self.chunker.chunk_document(doc_id, text, pages, file_type)

        # Generate embeddings if available
        if self.embedding_engine and chunks:
            texts = [c.content for c in chunks]
            try:
                embeddings = self.embedding_engine.embed(texts)
                for chunk, emb in zip(chunks, embeddings):
                    chunk.embedding = emb
            except Exception as e:
                logger.warning(f"Embedding generation failed: {e}")

        self._store_chunks(chunks)
        self.db.commit()

        logger.info(f"Ingested: {file_path} ({len(chunks)} chunks)")
        return doc

    def ingest_directory(self, dir_path: str, recursive: bool = True,
                         catalog_id: Optional[str] = None,
                         tags: Optional[List[str]] = None,
                         exclude_patterns: Optional[List[str]] = None) -> List[DocumentRecord]:
        """Ingest all supported files in a directory."""
        path = Path(dir_path)
        if not path.is_dir():
            logger.error(f"Not a directory: {dir_path}")
            return []

        exclude_patterns = exclude_patterns or ['.git', '__pycache__', 'node_modules', '.DS_Store']
        docs = []

        glob_pattern = '**/*' if recursive else '*'
        for file_path in path.glob(glob_pattern):
            if not file_path.is_file():
                continue

            # Check exclusions
            skip = False
            for pattern in exclude_patterns:
                if pattern in str(file_path):
                    skip = True
                    break
            if skip:
                continue

            file_type = self.extractor.get_file_type(str(file_path))
            if file_type == 'binary':
                continue

            doc = self.ingest_file(str(file_path), catalog_id=catalog_id, tags=tags)
            if doc:
                docs.append(doc)

        return docs

    def update_file(self, file_path: str) -> Optional[DocumentRecord]:
        """Re-ingest a file if it has changed."""
        path = Path(file_path)
        if not path.exists():
            return None

        new_checksum = self._compute_checksum(file_path)
        existing = self.db.fetchone(
            "SELECT doc_id, checksum FROM documents WHERE file_path = ?",
            (str(path.resolve()),)
        )

        if existing and existing['checksum'] == new_checksum:
            logger.info(f"File unchanged: {file_path}")
            return self._load_document(existing['doc_id'])

        if existing:
            # Delete old chunks and re-ingest
            self.db.execute("DELETE FROM chunks WHERE doc_id = ?", (existing['doc_id'],))
            self.db.execute("DELETE FROM documents WHERE doc_id = ?", (existing['doc_id'],))
            self.db.commit()

        return self.ingest_file(file_path)

    def _compute_checksum(self, file_path: str) -> str:
        """Compute SHA256 checksum of a file."""
        h = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    h.update(chunk)
        except Exception:
            h.update(file_path.encode())
        return h.hexdigest()

    def _store_document(self, doc: DocumentRecord):
        """Store a document record in the database."""
        self.db.execute("""
            INSERT OR REPLACE INTO documents
            (doc_id, file_path, title, file_type, size_bytes, created_at, modified_at,
             ingested_at, checksum, catalog_id, folder_path, language, word_count,
             page_count, summary, tags, metadata, relations)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc.doc_id, doc.file_path, doc.title, doc.file_type, doc.size_bytes,
            doc.created_at, doc.modified_at, doc.ingested_at, doc.checksum,
            doc.catalog_id, doc.folder_path, doc.language, doc.word_count,
            doc.page_count, doc.summary, json.dumps(doc.tags),
            json.dumps(doc.metadata), json.dumps(doc.relations)
        ))

    def _store_chunks(self, chunks: List[Chunk]):
        """Store chunks in the database."""
        for chunk in chunks:
            emb_bytes = None
            if chunk.embedding and self.embedding_engine:
                emb_bytes = self.embedding_engine.serialize_embedding(chunk.embedding)

            self.db.execute("""
                INSERT OR REPLACE INTO chunks
                (chunk_id, doc_id, content, chunk_index, start_offset, end_offset,
                 page_number, line_start, line_end, section_title, embedding, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk.chunk_id, chunk.doc_id, chunk.content, chunk.chunk_index,
                chunk.start_offset, chunk.end_offset, chunk.page_number,
                chunk.line_start, chunk.line_end, chunk.section_title,
                emb_bytes, json.dumps(chunk.metadata)
            ))

            # Update FTS index
            try:
                self.db.execute("""
                    INSERT OR REPLACE INTO chunks_fts (chunk_id, doc_id, content, section_title)
                    VALUES (?, ?, ?, ?)
                """, (chunk.chunk_id, chunk.doc_id, chunk.content, chunk.section_title or ''))
            except Exception as e:
                logger.debug(f"FTS insert error: {e}")

    def _load_document(self, doc_id: str) -> Optional[DocumentRecord]:
        """Load a document record from the database."""
        row = self.db.fetchone("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        if not row:
            return None
        return self._row_to_document(row)

    def _row_to_document(self, row: sqlite3.Row) -> DocumentRecord:
        return DocumentRecord(
            doc_id=row['doc_id'],
            file_path=row['file_path'],
            title=row['title'],
            file_type=row['file_type'],
            size_bytes=row['size_bytes'] or 0,
            created_at=row['created_at'] or '',
            modified_at=row['modified_at'] or '',
            ingested_at=row['ingested_at'] or '',
            checksum=row['checksum'] or '',
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}'),
            catalog_id=row['catalog_id'],
            folder_path=row['folder_path'] or '',
            language=row['language'] or 'en',
            word_count=row['word_count'] or 0,
            page_count=row['page_count'] or 0,
            summary=row['summary'] or '',
            relations=json.loads(row['relations'] or '[]'),
        )

    def _ensure_tag(self, tag_name: str):
        """Ensure a tag exists in the tags table."""
        existing = self.db.fetchone("SELECT tag_id FROM tags WHERE name = ?", (tag_name,))
        if not existing:
            self.db.execute(
                "INSERT OR IGNORE INTO tags (tag_id, name, created_at) VALUES (?, ?, ?)",
                (str(uuid.uuid4()), tag_name, datetime.datetime.utcnow().isoformat())
            )


# ─────────────────────────────────────────────────────────────────────────────
# Document Reader
# ─────────────────────────────────────────────────────────────────────────────

class DocumentReader:
    """Reads specific sections/windows from original files."""

    def __init__(self, extractor: TextExtractor):
        self.extractor = extractor

    def read_window(self, file_path: str, start_line: Optional[int] = None,
                    end_line: Optional[int] = None,
                    page_number: Optional[int] = None,
                    section_title: Optional[str] = None,
                    context_lines: int = 5) -> str:
        """Read a specific window from a file."""
        if not Path(file_path).exists():
            return f"[File not found: {file_path}]"

        extraction = self.extractor.extract(file_path)
        text = extraction['text']
        pages = extraction.get('pages', [])

        if page_number is not None and pages:
            return self._read_page(pages, page_number)

        if section_title:
            return self._read_section(text, section_title, context_lines)

        if start_line is not None:
            return self._read_lines(text, start_line, end_line, context_lines)

        # Return beginning of document
        lines = text.splitlines()
        return '\n'.join(lines[:50])

    def read_page(self, file_path: str, page_number: int) -> str:
        """Read a specific page from a document."""
        extraction = self.extractor.extract(file_path)
        pages = extraction.get('pages', [])
        return self._read_page(pages, page_number)

    def read_lines(self, file_path: str, start_line: int,
                   end_line: Optional[int] = None, context: int = 3) -> str:
        """Read specific lines from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except Exception:
            extraction = self.extractor.extract(file_path)
            lines = extraction['text'].splitlines(keepends=True)

        start = max(0, start_line - 1 - context)
        end = min(len(lines), (end_line or start_line) + context)
        return ''.join(lines[start:end])

    def read_archive_member(self, archive_path: str, member_name: str) -> str:
        """Read a specific member from an archive."""
        try:
            if zipfile.is_zipfile(archive_path):
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    with zf.open(member_name) as f:
                        return f.read(1024 * 1024).decode('utf-8', errors='replace')
            elif tarfile.is_tarfile(archive_path):
                with tarfile.open(archive_path, 'r:*') as tf:
                    member = tf.getmember(member_name)
                    f = tf.extractfile(member)
                    if f:
                        return f.read(1024 * 1024).decode('utf-8', errors='replace')
        except Exception as e:
            return f"[Archive read error: {e}]"
        return f"[Member not found: {member_name}]"

    def read_table_slice(self, file_path: str, sheet: Optional[str] = None,
                         row_start: int = 0, row_end: int = 50,
                         col_start: int = 0, col_end: int = 20) -> str:
        """Read a slice of a spreadsheet."""
        if not HAS_OPENPYXL:
            return "[openpyxl required for spreadsheet reading]"

        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            ws = wb[sheet] if sheet else wb.active
            rows = []
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i < row_start:
                    continue
                if i >= row_end:
                    break
                cells = [str(c) if c is not None else '' for c in row[col_start:col_end]]
                rows.append(' | '.join(cells))
            return '\n'.join(rows)
        except Exception as e:
            return f"[Table read error: {e}]"

    def _read_page(self, pages: List[Dict], page_number: int) -> str:
        """Read a specific page from extracted pages."""
        for page in pages:
            if page.get('page') == page_number:
                return page.get('text', f"[Empty page {page_number}]")
        return f"[Page {page_number} not found]"

    def _read_section(self, text: str, section_title: str, context_lines: int) -> str:
        """Read a section by title."""
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if section_title.lower() in line.lower():
                start = max(0, i - 1)
                end = min(len(lines), i + 50)
                return '\n'.join(lines[start:end])
        return f"[Section not found: {section_title}]"

    def _read_lines(self, text: str, start_line: int,
                    end_line: Optional[int], context_lines: int) -> str:
        """Read specific lines from text."""
        lines = text.splitlines()
        start = max(0, start_line - 1 - context_lines)
        end = min(len(lines), (end_line or start_line) + context_lines)
        return '\n'.join(lines[start:end])


# ─────────────────────────────────────────────────────────────────────────────
# LLM Client
# ─────────────────────────────────────────────────────────────────────────────

class LLMClient:
    """Unified LLM client supporting multiple providers."""

    def __init__(self, provider: str = "anthropic", model: Optional[str] = None,
                 api_key: Optional[str] = None):
        self.provider = provider
        self.model = model
        self._client = None
        self._init_client(api_key)

    def _init_client(self, api_key: Optional[str] = None):
        if self.provider == "anthropic":
            if not HAS_ANTHROPIC:
                logger.warning("anthropic package not installed")
                return
            try:
                kwargs = {}
                if api_key:
                    kwargs['api_key'] = api_key
                self._client = anthropic.Anthropic(**kwargs)
                self.model = self.model or "claude-3-5-sonnet-20241022"
            except Exception as e:
                logger.warning(f"Anthropic client init failed: {e}")

        elif self.provider == "openai":
            if not HAS_OPENAI:
                logger.warning("openai package not installed")
                return
            try:
                kwargs = {}
                if api_key:
                    kwargs['api_key'] = api_key
                self._client = openai.OpenAI(**kwargs)
                self.model = self.model or "gpt-4o"
            except Exception as e:
                logger.warning(f"OpenAI client init failed: {e}")

    @property
    def available(self) -> bool:
        return self._client is not None

    def complete(self, messages: List[Dict[str, str]],
                 system: Optional[str] = None,
                 max_tokens: int = 4096,
                 temperature: float = 0.3) -> str:
        """Generate a completion."""
        if not self._client:
            return self._mock_completion(messages)

        try:
            if self.provider == "anthropic":
                return self._anthropic_complete(messages, system, max_tokens, temperature)
            elif self.provider == "openai":
                return self._openai_complete(messages, system, max_tokens, temperature)
        except Exception as e:
            logger.error(f"LLM completion error: {e}")
            return f"[LLM error: {e}]"

        return self._mock_completion(messages)

    def _anthropic_complete(self, messages: List[Dict], system: Optional[str],
                             max_tokens: int, temperature: float) -> str:
        kwargs = {
            'model': self.model,
            'max_tokens': max_tokens,
            'messages': messages,
        }
        if system:
            kwargs['system'] = system

        response = self._client.messages.create(**kwargs)
        return response.content[0].text

    def _openai_complete(self, messages: List[Dict], system: Optional[str],
                          max_tokens: int, temperature: float) -> str:
        all_messages = []
        if system:
            all_messages.append({'role': 'system', 'content': system})
        all_messages.extend(messages)

        response = self._client.chat.completions.create(
            model=self.model,
            messages=all_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    def _mock_completion(self, messages: List[Dict]) -> str:
        """Mock completion when no LLM is available."""
        last_msg = messages[-1]['content'] if messages else ''
        return (f"[Mock response - no LLM configured]\n"
                f"Query: {last_msg[:100]}...\n"
                f"Please configure an LLM provider (anthropic or openai).")


# ─────────────────────────────────────────────────────────────────────────────
# Research Agent
# ─────────────────────────────────────────────────────────────────────────────

class ResearchAgent:
    """The main research agent that answers queries with citations."""

    SYSTEM_PROMPT = """You are Marginalia, a research assistant for a personal knowledge base.
Your role is to:
1. Answer questions based ONLY on the provided document excerpts
2. Cite your sources precisely with document titles, page numbers, or line numbers
3. Acknowledge when information is incomplete or uncertain
4. Identify follow-up questions that would deepen the research
5. Be concise but thorough

Format your response as:
## Answer
[Your answer here]

## Citations
[List each citation with: Title, location (page/line/section), and relevant quote]

## Follow-up Questions
[2-3 questions for deeper investigation]

## Confidence
[High/Medium/Low with brief explanation]
"""

    def __init__(self, db: Database, search_engine: SearchEngine,
                 document_reader: DocumentReader, llm_client: LLMClient,
                 ingestion_pipeline: IngestionPipeline):
        self.db = db
        self.search_engine = search_engine
        self.document_reader = document_reader
        self.llm_client = llm_client
        self.ingestion_pipeline = ingestion_pipeline
        self._conversation_history: List[Dict] = []

    def query(self, question: str, search_mode: str = 'lexical',
              max_sources: int = 5, max_chunks_per_source: int = 3,
              filters: Optional[Dict] = None,
              save_note: bool = True) -> Dict[str, Any]:
        """Answer a research question with citations."""

        # 1. Search for relevant chunks
        if search_mode == 'semantic':
            results = self.search_engine.semantic_search(question, limit=max_sources * max_chunks_per_source, filters=filters)
        elif search_mode == 'hybrid':
            results = self.search_engine.hybrid_search(question, limit=max_sources * max_chunks_per_source, filters=filters)
        else:
            results = self.search_engine.lexical_search(question, limit=max_sources * max_chunks_per_source, filters=filters)

        # Apply source quota
        results = self._apply_source_quota(results, max_sources, max_chunks_per_source)

        # 2. Read original file windows for each result
        enriched_contexts = []
        for result in results:
            window = self.document_reader.read_window(
                result.file_path,
                start_line=result.line_start,
                end_line=result.line_end,
                page_number=result.page_number,
                section_title=result.section_title,
            )
            enriched_contexts.append({
                'result': result,
                'window': window,
            })

        # 3. Build context for LLM
        context_text = self._build_context(enriched_contexts)

        # 4. Generate answer
        messages = self._build_messages(question, context_text)
        answer_text = self.llm_client.complete(
            messages,
            system=self.SYSTEM_PROMPT,
            max_tokens=4096,
        )

        # 5. Parse citations from answer
        citations = self._extract_citations(answer_text, enriched_contexts)

        # 6. Build investigation note
        note = None
        if save_note:
            note = self._save_investigation_note(question, answer_text, citations)

        # 7. Update conversation history
        self._conversation_history.append({'role': 'user', 'content': question})
        self._conversation_history.append({'role': 'assistant', 'content': answer_text})

        return {
            'question': question,
            'answer': answer_text,
            'citations': [asdict(c) for c in citations],
            'sources_used': len(set(r['result'].doc_id for r in enriched_contexts)),
            'chunks_retrieved': len(results),
            'note_id': note.note_id if note else None,
            'search_mode': search_mode,
        }

    def generate_report(self, topic: str, outline: Optional[List[str]] = None,
                        search_mode: str = 'hybrid',
                        max_sources_per_section: int = 5) -> Dict[str, Any]:
        """Generate a structured research report on a topic."""

        if not outline:
            # Generate outline first
            outline_prompt = f"Generate a 5-section research outline for: {topic}"
            outline_response = self.llm_client.complete(
                [{'role': 'user', 'content': outline_prompt}],
                max_tokens=512,
            )
            outline = self._parse_outline(outline_response)

        sections = []
        all_citations = []

        for section_title in outline:
            section_query = f"{topic}: {section_title}"
            section_result = self.query(
                section_query,
                search_mode=search_mode,
                max_sources=max_sources_per_section,
                save_note=False,
            )
            sections.append({
                'title': section_title,
                'content': section_result['answer'],
                'citations': section_result['citations'],
            })
            all_citations.extend(section_result['citations'])

        # Generate executive summary
        section_summaries = '\n\n'.join(
            f"## {s['title']}\n{s['content'][:500]}" for s in sections
        )
        summary_prompt = f"Write a 200-word executive summary for this report on '{topic}':\n\n{section_summaries}"
        summary = self.llm_client.complete(
            [{'role': 'user', 'content': summary_prompt}],
            max_tokens=512,
        )

        report = {
            'topic': topic,
            'summary': summary,
            'sections': sections,
            'all_citations': all_citations,
            'generated_at': datetime.datetime.utcnow().isoformat(),
            'total_sources': len(set(c.get('doc_id', '') for c in all_citations)),
        }

        # Save as investigation note
        note = self._save_investigation_note(
            f"Report: {topic}",
            summary + '\n\n' + '\n\n'.join(f"## {s['title']}\n{s['content']}" for s in sections),
            [Citation(**c) for c in all_citations if all(k in c for k in ['citation_id', 'doc_id', 'file_path', 'title', 'quote'])],
            tags=['report'],
        )
        report['note_id'] = note.note_id if note else None

        return report

    def recall_notes(self, query: str, limit: int = 10) -> List[InvestigationNote]:
        """Recall past investigation notes relevant to a query."""
        rows = self.db.fetchall("""
            SELECT * FROM investigation_notes
            WHERE LOWER(query) LIKE ? OR LOWER(answer) LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (f'%{query.lower()}%', f'%{query.lower()}%', limit))

        notes = []
        for row in rows:
            citations_data = json.loads(row['citations'] or '[]')
            citations = []
            for c in citations_data:
                try:
                    citations.append(Citation(**c))
                except Exception:
                    pass

            note = InvestigationNote(
                note_id=row['note_id'],
                query=row['query'],
                answer=row['answer'],
                citations=citations,
                created_at=row['created_at'],
                tags=json.loads(row['tags'] or '[]'),
                follow_up_questions=json.loads(row['follow_up_questions'] or '[]'),
                metadata=json.loads(row['metadata'] or '{}'),
            )
            notes.append(note)

        return notes

    def continue_conversation(self, message: str, **kwargs) -> Dict[str, Any]:
        """Continue a multi-turn research conversation."""
        # Include conversation history context
        history_context = ""
        if self._conversation_history:
            recent = self._conversation_history[-6:]  # Last 3 turns
            history_context = "\n\nPrevious conversation:\n" + '\n'.join(
                f"{m['role'].upper()}: {m['content'][:200]}" for m in recent
            )

        enhanced_query = message + history_context
        return self.query(enhanced_query, **kwargs)

    def reset_conversation(self):
        """Reset the conversation history."""
        self._conversation_history = []

    def _apply_source_quota(self, results: List[SearchResult],
                             max_sources: int, max_per_source: int) -> List[SearchResult]:
        """Apply source quotas to search results."""
        source_counts: Dict[str, int] = defaultdict(int)
        source_seen: set = set()
        filtered = []

        for result in results:
            if source_counts[result.doc_id] < max_per_source:
                filtered.append(result)
                source_counts[result.doc_id] += 1
                source_seen.add(result.doc_id)

            if len(source_seen) >= max_sources and all(
                source_counts[s] >= max_per_source for s in source_seen
            ):
                break

        return filtered

    def _build_context(self, enriched_contexts: List[Dict]) -> str:
        """Build context string for LLM from enriched search results."""
        parts = []
        for i, ctx in enumerate(enriched_contexts):
            result = ctx['result']
            window = ctx['window']

            part = f"""
[Source {i+1}]
Title: {result.title}
File: {result.file_path}
"""
            if result.page_number:
                part += f"Page: {result.page_number}\n"
            if result.line_start:
                part += f"Lines: {result.line_start}-{result.line_end or result.line_start}\n"
            if result.section_title:
                part += f"Section: {result.section_title}\n"

            part += f"\nContent:\n{window}\n"
            parts.append(part)

        return '\n---\n'.join(parts)

    def _build_messages(self, question: str, context: str) -> List[Dict]:
        """Build message list for LLM."""
        user_content = f"""Based on the following document excerpts, please answer this question:

**Question:** {question}

**Document Excerpts:**
{context}

Please provide a thorough answer with precise citations."""

        return [{'role': 'user', 'content': user_content}]

    def _extract_citations(self, answer_text: str,
                            enriched_contexts: List[Dict]) -> List[Citation]:
        """Extract citations from the answer and match to sources."""
        citations = []

        for ctx in enriched_contexts:
            result = ctx['result']
            window = ctx['window']

            # Check if this source is referenced in the answer
            if (result.title.lower() in answer_text.lower() or
                    Path(result.file_path).name.lower() in answer_text.lower() or
                    any(word in answer_text.lower()
                        for word in result.title.lower().split()[:3] if len(word) > 4)):

                # Extract a relevant quote
                quote = self._extract_quote(window, answer_text)

                citation = Citation(
                    citation_id=str(uuid.uuid4()),
                    doc_id=result.doc_id,
                    file_path=result.file_path,
                    title=result.title,
                    quote=quote,
                    page_number=result.page_number,
                    line_start=result.line_start,
                    line_end=result.line_end,
                    section_title=result.section_title,
                )
                citations.append(citation)

        # If no citations matched, create generic ones for top sources
        if not citations and enriched_contexts:
            for ctx in enriched_contexts[:3]:
                result = ctx['result']
                window = ctx['window']
                citation = Citation(
                    citation_id=str(uuid.uuid4()),
                    doc_id=result.doc_id,
                    file_path=result.file_path,
                    title=result.title,
                    quote=window[:200],
                    page_number=result.page_number,
                    line_start=result.line_start,
                    line_end=result.line_end,
                    section_title=result.section_title,
                )
                citations.append(citation)

        return citations

    def _extract_quote(self, source_text: str, answer_text: str,
                       max_length: int = 200) -> str:
        """Extract the most relevant quote from source text."""
        sentences = re.split(r'[.!?]+', source_text)
        answer_words = set(re.findall(r'\w+', answer_text.lower()))

        best_sentence = ''
        best_score = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
            words = set(re.findall(r'\w+', sentence.lower()))
            score = len(words & answer_words) / max(len(words), 1)
            if score > best_score:
                best_score = score
                best_sentence = sentence

        return (best_sentence or source_text)[:max_length]

    def _save_investigation_note(self, query: str, answer: str,
                                  citations: List[Citation],
                                  tags: Optional[List[str]] = None) -> InvestigationNote:
        """Save an investigation note to the database."""
        # Extract follow-up questions from answer
        follow_ups = self._extract_follow_up_questions(answer)

        note = InvestigationNote(
            note_id=str(uuid.uuid4()),
            query=query,
            answer=answer,
            citations=citations,
            created_at=datetime.datetime.utcnow().isoformat(),
            tags=tags or [],
            follow_up_questions=follow_ups,
        )

        citations_data = []
        for c in citations:
            citations_data.append({
                'citation_id': c.citation_id,
                'doc_id': c.doc_id,
                'file_path': c.file_path,
                'title': c.title,
                'quote': c.quote,
                'page_number': c.page_number,
                'line_start': c.line_start,
                'line_end': c.line_end,
                'section_title': c.section_title,
                'relevance_note': c.relevance_note,
            })

        self.db.execute("""
            INSERT INTO investigation_notes
            (note_id, query, answer, citations, created_at, tags, follow_up_questions, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            note.note_id, note.query, note.answer,
            json.dumps(citations_data),
            note.created_at,
            json.dumps(note.tags),
            json.dumps(note.follow_up_questions),
            json.dumps(note.metadata),
        ))
        self.db.commit()

        return note

    def _extract_follow_up_questions(self, answer_text: str) -> List[str]:
        """Extract follow-up questions from answer text."""
        questions = []

        # Look for "Follow-up Questions" section
        match = re.search(r'##\s*Follow-up Questions\s*\n(.*?)(?=##|\Z)',
                          answer_text, re.DOTALL | re.IGNORECASE)
        if match:
            section = match.group(1)
            for line in section.splitlines():
                line = line.strip().lstrip('0123456789.-) ')
                if line and '?' in line:
                    questions.append(line)

        return questions[:5]

    def _parse_outline(self, outline_text: str) -> List[str]:
        """Parse an outline from LLM response."""
        sections = []
        for line in outline_text.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                # Remove numbering
                line = re.sub(r'^[\d]+[.)]\s*', '', line)
                line = re.sub(r'^[-*]\s*', '', line)
                if len(line) > 5:
                    sections.append(line)

        return sections[:7] if sections else [
            'Introduction', 'Background', 'Main Findings',
            'Analysis', 'Conclusions'
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Catalog Manager
# ─────────────────────────────────────────────────────────────────────────────

class CatalogManager:
    """Manages catalogs, tags, views, and metadata."""

    def __init__(self, db: Database):
        self.db = db

    # ── Catalogs ──────────────────────────────────────────────────────────────

    def create_catalog(self, name: str, description: str = '',
                       tags: Optional[List[str]] = None) -> Catalog:
        """Create a new catalog."""
        catalog = Catalog(
            catalog_id=str(uuid.uuid4()),
            name=name,
            description=description,
            created_at=datetime.datetime.utcnow().isoformat(),
            tags=tags or [],
        )
        self.db.execute("""
            INSERT INTO catalogs (catalog_id, name, description, created_at, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (catalog.catalog_id, catalog.name, catalog.description,
              catalog.created_at, json.dumps(catalog.tags), json.dumps(catalog.metadata)))
        self.db.commit()
        return catalog

    def get_catalog(self, catalog_id: str) -> Optional[Catalog]:
        """Get a catalog by ID."""
        row = self.db.fetchone("SELECT * FROM catalogs WHERE catalog_id = ?", (catalog_id,))
        if not row:
            return None
        return Catalog(
            catalog_id=row['catalog_id'],
            name=row['name'],
            description=row['description'] or '',
            created_at=row['created_at'] or '',
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}'),
        )

    def list_catalogs(self) -> List[Catalog]:
        """List all catalogs."""
        rows = self.db.fetchall("SELECT * FROM catalogs ORDER BY name")
        catalogs = []
        for row in rows:
            catalogs.append(Catalog(
                catalog_id=row['catalog_id'],
                name=row['name'],
                description=row['description'] or '',
                created_at=row['created_at'] or '',
                tags=json.loads(row['tags'] or '[]'),
                metadata=json.loads(row['metadata'] or '{}'),
            ))
        return catalogs

    def assign_to_catalog(self, doc_id: str, catalog_id: str):
        """Assign a document to a catalog."""
        self.db.execute(
            "UPDATE documents SET catalog_id = ? WHERE doc_id = ?",
            (catalog_id, doc_id)
        )
        self.db.commit()

    def get_catalog_documents(self, catalog_id: str) -> List[Dict]:
        """Get all documents in a catalog."""
        rows = self.db.fetchall(
            "SELECT doc_id, title, file_path, file_type, word_count FROM documents WHERE catalog_id = ?",
            (catalog_id,)
        )
        return [dict(row) for row in rows]

    def delete_catalog(self, catalog_id: str, reassign_to: Optional[str] = None):
        """Delete a catalog."""
        if reassign_to:
            self.db.execute(
                "UPDATE documents SET catalog_id = ? WHERE catalog_id = ?",
                (reassign_to, catalog_id)
            )
        else:
            self.db.execute(
                "UPDATE documents SET catalog_id = NULL WHERE catalog_id = ?",
                (catalog_id,)
            )
        self.db.execute("DELETE FROM catalogs WHERE catalog_id = ?", (catalog_id,))
        self.db.commit()

    # ── Tags ──────────────────────────────────────────────────────────────────

    def create_tag(self, name: str, color: str = '#888888',
                   description: str = '') -> Dict:
        """Create a new tag."""
        tag_id = str(uuid.uuid4())
        self.db.execute("""
            INSERT OR IGNORE INTO tags (tag_id, name, color, description, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (tag_id, name, color, description, datetime.datetime.utcnow().isoformat()))
        self.db.commit()
        return {'tag_id': tag_id, 'name': name, 'color': color, 'description': description}

    def list_tags(self) -> List[Dict]:
        """List all tags with document counts."""
        rows = self.db.fetchall("""
            SELECT t.tag_id, t.name, t.color, t.description,
                   COUNT(dt.doc_id) as doc_count
            FROM tags t
            LEFT JOIN doc_tags dt ON t.name = dt.tag_name
            GROUP BY t.tag_id
            ORDER BY t.name
        """)
        return [dict(row) for row in rows]

    def tag_document(self, doc_id: str, tag_name: str):
        """Add a tag to a document."""
        self.create_tag(tag_name)
        self.db.execute(
            "INSERT OR IGNORE INTO doc_tags (doc_id, tag_name) VALUES (?, ?)",
            (doc_id, tag_name)
        )
        # Update document tags JSON
        row = self.db.fetchone("SELECT tags FROM documents WHERE doc_id = ?", (doc_id,))
        if row:
            tags = json.loads(row['tags'] or '[]')
            if tag_name not in tags:
                tags.append(tag_name)
                self.db.execute(
                    "UPDATE documents SET tags = ? WHERE doc_id = ?",
                    (json.dumps(tags), doc_id)
                )
        self.db.commit()

    def untag_document(self, doc_id: str, tag_name: str):
        """Remove a tag from a document."""
        self.db.execute(
            "DELETE FROM doc_tags WHERE doc_id = ? AND tag_name = ?",
            (doc_id, tag_name)
        )
        row = self.db.fetchone("SELECT tags FROM documents WHERE doc_id = ?", (doc_id,))
        if row:
            tags = json.loads(row['tags'] or '[]')
            tags = [t for t in tags if t != tag_name]
            self.db.execute(
                "UPDATE documents SET tags = ? WHERE doc_id = ?",
                (json.dumps(tags), doc_id)
            )
        self.db.commit()

    def get_documents_by_tag(self, tag_name: str) -> List[Dict]:
        """Get all documents with a specific tag."""
        rows = self.db.fetchall("""
            SELECT d.doc_id, d.title, d.file_path, d.file_type
            FROM documents d
            JOIN doc_tags dt ON d.doc_id = dt.doc_id
            WHERE dt.tag_name = ?
        """, (tag_name,))
        return [dict(row) for row in rows]

    # ── Views ─────────────────────────────────────────────────────────────────

    def create_view(self, name: str, query: str, filters: Optional[Dict] = None,
                    description: str = '') -> View:
        """Create a saved search view."""
        view = View(
            view_id=str(uuid.uuid4()),
            name=name,
            query=query,
            filters=filters or {},
            created_at=datetime.datetime.utcnow().isoformat(),
            description=description,
        )
        self.db.execute("""
            INSERT INTO views (view_id, name, query, filters, created_at, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (view.view_id, view.name, view.query,
              json.dumps(view.filters), view.created_at, view.description))
        self.db.commit()
        return view

    def list_views(self) -> List[View]:
        """List all saved views."""
        rows = self.db.fetchall("SELECT * FROM views ORDER BY name")
        views = []
        for row in rows:
            views.append(View(
                view_id=row['view_id'],
                name=row['name'],
                query=row['query'] or '',
                filters=json.loads(row['filters'] or '{}'),
                created_at=row['created_at'] or '',
                description=row['description'] or '',
            ))
        return views

    def get_view(self, view_id: str) -> Optional[View]:
        """Get a view by ID."""
        row = self.db.fetchone("SELECT * FROM views WHERE view_id = ?", (view_id,))
        if not row:
            return None
        return View(
            view_id=row['view_id'],
            name=row['name'],
            query=row['query'] or '',
            filters=json.loads(row['filters'] or '{}'),
            created_at=row['created_at'] or '',
            description=row['description'] or '',
        )

    def delete_view(self, view_id: str):
        """Delete a view."""
        self.db.execute("DELETE FROM views WHERE view_id = ?", (view_id,))
        self.db.commit()

    # ── Metadata ──────────────────────────────────────────────────────────────

    def update_document_metadata(self, doc_id: str, metadata: Dict):
        """Update document metadata."""
        row = self.db.fetchone("SELECT metadata FROM documents WHERE doc_id = ?", (doc_id,))
        if row:
            existing = json.loads(row['metadata'] or '{}')
            existing.update(metadata)
            self.db.execute(
                "UPDATE documents SET metadata = ? WHERE doc_id = ?",
                (json.dumps(existing), doc_id)
            )
            self.db.commit()

    def update_document_summary(self, doc_id: str, summary: str):
        """Update document summary."""
        self.db.execute(
            "UPDATE documents SET summary = ? WHERE doc_id = ?",
            (summary, doc_id)
        )
        self.db.commit()

    def get_document_metadata(self, doc_id: str) -> Optional[Dict]:
        """Get document metadata."""
        row = self.db.fetchone(
            "SELECT title, file_path, file_type, tags, metadata, summary, word_count, page_count FROM documents WHERE doc_id = ?",
            (doc_id,)
        )
        if not row:
            return None
        return {
            'title': row['title'],
            'file_path': row['file_path'],
            'file_type': row['file_type'],
            'tags': json.loads(row['tags'] or '[]'),
            'metadata': json.loads(row['metadata'] or '{}'),
            'summary': row['summary'],
            'word_count': row['word_count'],
            'page_count': row['page_count'],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Journal Manager
# ─────────────────────────────────────────────────────────────────────────────

class JournalManager:
    """Manages research journal entries."""

    def __init__(self, db: Database):
        self.db = db

    def create_entry(self, content: str, tags: Optional[List[str]] = None,
                     linked_docs: Optional[List[str]] = None,
                     linked_notes: Optional[List[str]] = None) -> JournalEntry:
        """Create a new journal entry."""
        entry = JournalEntry(
            entry_id=str(uuid.uuid4()),
            content=content,
            created_at=datetime.datetime.utcnow().isoformat(),
            tags=tags or [],
            linked_docs=linked_docs or [],
            linked_notes=linked_notes or [],
        )
        self.db.execute("""
            INSERT INTO journal_entries
            (entry_id, content, created_at, tags, linked_docs, linked_notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            entry.entry_id, entry.content, entry.created_at,
            json.dumps(entry.tags), json.dumps(entry.linked_docs),
            json.dumps(entry.linked_notes)
        ))
        self.db.commit()
        return entry

    def get_entry(self, entry_id: str) -> Optional[JournalEntry]:
        """Get a journal entry by ID."""
        row = self.db.fetchone(
            "SELECT * FROM journal_entries WHERE entry_id = ?", (entry_id,)
        )
        if not row:
            return None
        return self._row_to_entry(row)

    def list_entries(self, limit: int = 50, offset: int = 0,
                     tag: Optional[str] = None) -> List[JournalEntry]:
        """List journal entries."""
        if tag:
            rows = self.db.fetchall("""
                SELECT * FROM journal_entries
                WHERE LOWER(tags) LIKE ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (f'%{tag.lower()}%', limit, offset))
        else:
            rows = self.db.fetchall("""
                SELECT * FROM journal_entries
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

        return [self._row_to_entry(row) for row in rows]

    def search_entries(self, query: str, limit: int = 20) -> List[JournalEntry]:
        """Search journal entries."""
        rows = self.db.fetchall("""
            SELECT * FROM journal_entries
            WHERE LOWER(content) LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (f'%{query.lower()}%', limit))
        return [self._row_to_entry(row) for row in rows]

    def update_entry(self, entry_id: str, content: Optional[str] = None,
                     tags: Optional[List[str]] = None) -> bool:
        """Update a journal entry."""
        entry = self.get_entry(entry_id)
        if not entry:
            return False

        if content is not None:
            entry.content = content
        if tags is not None:
            entry.tags = tags

        self.db.execute("""
            UPDATE journal_entries SET content = ?, tags = ? WHERE entry_id = ?
        """, (entry.content, json.dumps(entry.tags), entry_id))
        self.db.commit()
        return True

    def delete_entry(self, entry_id: str) -> bool:
        """Delete a journal entry."""
        self.db.execute("DELETE FROM journal_entries WHERE entry_id = ?", (entry_id,))
        self.db.commit()
        return True

    def link_document(self, entry_id: str, doc_id: str):
        """Link a document to a journal entry."""
        entry = self.get_entry(entry_id)
        if entry and doc_id not in entry.linked_docs:
            entry.linked_docs.append(doc_id)
            self.db.execute(
                "UPDATE journal_entries SET linked_docs = ? WHERE entry_id = ?",
                (json.dumps(entry.linked_docs), entry_id)
            )
            self.db.commit()

    def _row_to_entry(self, row: sqlite3.Row) -> JournalEntry:
        return JournalEntry(
            entry_id=row['entry_id'],
            content=row['content'],
            created_at=row['created_at'] or '',
            tags=json.loads(row['tags'] or '[]'),
            linked_docs=json.loads(row['linked_docs'] or '[]'),
            linked_notes=json.loads(row['linked_notes'] or '[]'),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge Base
# ─────────────────────────────────────────────────────────────────────────────

class KnowledgeBase:
    """High-level interface to the Marginalia knowledge base."""

    def __init__(self, base_path: str, llm_provider: str = "anthropic",
                 llm_model: Optional[str] = None,
                 embedding_provider: str = "openai",
                 embedding_model: str = "text-embedding-3-small",
                 chunk_size: int = 512, chunk_overlap: int = 64,
                 use_embeddings: bool = False):

        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Initialize components
        db_path = str(self.base_path / 'marginalia.db')
        self.db = Database(db_path)

        self.extractor = TextExtractor()
        self.chunker = Chunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        self.embedding_engine = None
        if use_embeddings:
            self.embedding_engine = EmbeddingEngine(
                model=embedding_model,
                provider=embedding_provider
            )

        self.ingestion = IngestionPipeline(
            db=self.db,
            extractor=self.extractor,
            chunker=self.chunker,
            embedding_engine=self.embedding_engine,
        )

        self.search = SearchEngine(
            db=self.db,
            embedding_engine=self.embedding_engine,
        )

        self.reader = DocumentReader(self.extractor)

        self.llm = LLMClient(
            provider=llm_provider,
            model=llm_model,
        )

        self.catalog_manager = CatalogManager(self.db)
        self.journal = JournalManager(self.db)
        self.relation_miner = RelationMiner(self.db)

        self.agent = ResearchAgent(
            db=self.db,
            search_engine=self.search,
            document_reader=self.reader,
            llm_client=self.llm,
            ingestion_pipeline=self.ingestion,
        )

        logger.info(f"Marginalia initialized at {base_path}")

    # ── Ingestion ─────────────────────────────────────────────────────────────

    def ingest(self, path: str, **kwargs) -> Union[DocumentRecord, List[DocumentRecord]]:
        """Ingest a file or directory."""
        p = Path(path)
        if p.is_dir():
            return self.ingestion.ingest_directory(str(p), **kwargs)
        else:
            return self.ingestion.ingest_file(str(p), **kwargs)

    def update(self, file_path: str) -> Optional[DocumentRecord]:
        """Update an ingested file."""
        return self.ingestion.update_file(file_path)

    # ── Search ────────────────────────────────────────────────────────────────

    def find(self, query: str, mode: str = 'lexical', limit: int = 10,
             filters: Optional[Dict] = None) -> List[SearchResult]:
        """Search the knowledge base."""
        if mode == 'semantic':
            return self.search.semantic_search(query, limit=limit, filters=filters)
        elif mode == 'hybrid':
            return self.search.hybrid_search(query, limit=limit, filters=filters)
        else:
            return self.search.lexical_search(query, limit=limit, filters=filters)

    # ── Agent ─────────────────────────────────────────────────────────────────

    def ask(self, question: str, **kwargs) -> Dict[str, Any]:
        """Ask the research agent a question."""
        return self.agent.query(question, **kwargs)

    def report(self, topic: str, **kwargs) -> Dict[str, Any]:
        """Generate a research report."""
        return self.agent.generate_report(topic, **kwargs)

    def recall(self, query: str, limit: int = 10) -> List[InvestigationNote]:
        """Recall past investigation notes."""
        return self.agent.recall_notes(query, limit=limit)

    # ── Documents ─────────────────────────────────────────────────────────────

    def list_documents(self, folder: Optional[str] = None,
                       file_type: Optional[str] = None,
                       catalog_id: Optional[str] = None,
                       tag: Optional[str] = None,
                       limit: int = 100, offset: int = 0) -> List[Dict]:
        """List documents with optional filters."""
        conditions = []
        params = []

        if folder:
            conditions.append("folder_path LIKE ?")
            params.append(f"{folder}%")
        if file_type:
            conditions.append("file_type = ?")
            params.append(file_type)
        if catalog_id:
            conditions.append("catalog_id = ?")
            params.append(catalog_id)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        if tag:
            where_tag = f"""
                {'AND' if where else 'WHERE'} doc_id IN (
                    SELECT doc_id FROM doc_tags WHERE tag_name = ?
                )
            """
            where += where_tag
            params.append(tag)

        sql = f"""
            SELECT doc_id, title, file_path, file_type, word_count, page_count,
                   ingested_at, tags, catalog_id, folder_path
            FROM documents
            {where}
            ORDER BY ingested_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = self.db.fetchall(sql, tuple(params))
        return [dict(row) for row in rows]

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get a document by ID."""
        row = self.db.fetchone("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        if not row:
            return None
        return dict(row)

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the knowledge base."""
        self.db.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        self.db.commit()
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        stats = {}

        row = self.db.fetchone("SELECT COUNT(*) as count FROM documents")
        stats['total_documents'] = row['count'] if row else 0

        row = self.db.fetchone("SELECT COUNT(*) as count FROM chunks")
        stats['total_chunks'] = row['count'] if row else 0

        row = self.db.fetchone("SELECT COUNT(*) as count FROM investigation_notes")
        stats['total_notes'] = row['count'] if row else 0

        row = self.db.fetchone("SELECT COUNT(*) as count FROM journal_entries")
        stats['total_journal_entries'] = row['count'] if row else 0

        row = self.db.fetchone("SELECT COUNT(*) as count FROM catalogs")
        stats['total_catalogs'] = row['count'] if row else 0

        row = self.db.fetchone("SELECT COUNT(*) as count FROM tags")
        stats['total_tags'] = row['count'] if row else 0

        rows = self.db.fetchall("""
            SELECT file_type, COUNT(*) as count
            FROM documents
            GROUP BY file_type
            ORDER BY count DESC
        """)
        stats['documents_by_type'] = {row['file_type']: row['count'] for row in rows}

        row = self.db.fetchone("SELECT SUM(word_count) as total FROM documents")
        stats['total_words'] = row['total'] if row and row['total'] else 0

        row = self.db.fetchone("SELECT SUM(size_bytes) as total FROM documents")
        stats['total_size_bytes'] = row['total'] if row and row['total'] else 0

        return stats

    # ── Relations ─────────────────────────────────────────────────────────────

    def mine_relations(self, doc_id: str) -> List[Relation]:
        """Mine relations for a document."""
        row = self.db.fetchone("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        if not row:
            return []

        # Get document text
        file_path = row['file_path']
        extraction = self.extractor.extract(file_path)
        text = extraction['text']

        # Get all documents
        all_rows = self.db.fetchall("SELECT doc_id, title, file_path FROM documents")
        all_docs = [
            DocumentRecord(
                doc_id=r['doc_id'],
                file_path=r['file_path'],
                title=r['title'],
                file_type='',
                size_bytes=0,
                created_at='',
                modified_at='',
                ingested_at='',
                checksum='',
            )
            for r in all_rows
        ]

        relations = self.relation_miner.mine_relations(doc_id, text, all_docs)

        # Store relations
        for rel in relations:
            try:
                self.db.execute("""
                    INSERT OR IGNORE INTO relations
                    (relation_id, source_doc_id, target_doc_id, relation_type,
                     confidence, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    rel.relation_id, rel.source_doc_id, rel.target_doc_id,
                    rel.relation_type, rel.confidence, rel.created_at,
                    json.dumps(rel.metadata)
                ))
            except Exception as e:
                logger.debug(f"Relation insert error: {e}")

        self.db.commit()
        return relations

    def get_relations(self, doc_id: str) -> List[Dict]:
        """Get all relations for a document."""
        rows = self.db.fetchall("""
            SELECT r.*, d.title as target_title, d.file_path as target_path
            FROM relations r
            JOIN documents d ON r.target_doc_id = d.doc_id
            WHERE r.source_doc_id = ?
            UNION
            SELECT r.*, d.title as target_title, d.file_path as target_path
            FROM relations r
            JOIN documents d ON r.source_doc_id = d.doc_id
            WHERE r.target_doc_id = ?
        """, (doc_id, doc_id))
        return [dict(row) for row in rows]

    # ── Export ────────────────────────────────────────────────────────────────

    def export_notes(self, output_path: str, format: str = 'markdown'):
        """Export investigation notes to a file."""
        notes = self.db.fetchall(
            "SELECT * FROM investigation_notes ORDER BY created_at DESC"
        )

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        if format == 'json':
            data = [dict(row) for row in notes]
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# Marginalia Investigation Notes\n\n")
                for row in notes:
                    f.write(f"## {row['query']}\n")
                    f.write(f"*{row['created_at']}*\n\n")
                    f.write(row['answer'] + '\n\n')
                    f.write("---\n\n")

        logger.info(f"Exported {len(notes)} notes to {output_path}")

    def export_report(self, report: Dict, output_path: str, format: str = 'markdown'):
        """Export a generated report to a file."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        if format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# {report['topic']}\n\n")
                f.write(f"*Generated: {report.get('generated_at', '')}*\n\n")
                f.write("## Executive Summary\n\n")
                f.write(report.get('summary', '') + '\n\n')

                for section in report.get('sections', []):
                    f.write(f"## {section['title']}\n\n")
                    f.write(section['content'] + '\n\n')

                f.write("## References\n\n")
                seen = set()
                for citation in report.get('all_citations', []):
                    title = citation.get('title', 'Unknown')
                    if title not in seen:
                        seen.add(title)
                        f.write(f"- {title}: {citation.get('file_path', '')}\n")

        logger.info(f"Report exported to {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI Interface
# ─────────────────────────────────────────────────────────────────────────────

class CLI:
    """Command-line interface for Marginalia."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def run(self):
        """Run the interactive CLI."""
        print("\n╔══════════════════════════════════════╗")
        print("║         MARGINALIA v1.0               ║")
        print("║  Personal Knowledge Management System ║")
        print("╚══════════════════════════════════════╝\n")

        stats = self.kb.get_stats()
        print(f"Knowledge base: {self.kb.base_path}")
        print(f"Documents: {stats['total_documents']} | "
              f"Chunks: {stats['total_chunks']} | "
              f"Notes: {stats['total_notes']}\n")

        print("Commands: ingest, find, ask, report, recall, stats, catalog, tag, journal, help, quit\n")

        while True:
            try:
                cmd = input("marginalia> ").strip()
                if not cmd:
                    continue

                parts = cmd.split(None, 1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ''

                if command in ('quit', 'exit', 'q'):
                    print("Goodbye!")
                    break
                elif command == 'help':
                    self._show_help()
                elif command == 'ingest':
                    self._cmd_ingest(args)
                elif command == 'find':
                    self._cmd_find(args)
                elif command == 'ask':
                    self._cmd_ask(args)
                elif command == 'report':
                    self._cmd_report(args)
                elif command == 'recall':
                    self._cmd_recall(args)
                elif command == 'stats':
                    self._cmd_stats()
                elif command == 'catalog':
                    self._cmd_catalog(args)
                elif command == 'tag':
                    self._cmd_tag(args)
                elif command == 'journal':
                    self._cmd_journal(args)
                elif command == 'list':
                    self._cmd_list(args)
                else:
                    print(f"Unknown command: {command}. Type 'help' for help.")

            except KeyboardInterrupt:
                print("\nInterrupted. Type 'quit' to exit.")
            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}")
                logger.exception(e)

    def _show_help(self):
        help_text = """
Commands:
  ingest <path>          - Ingest a file or directory
  find <query>           - Search the knowledge base
  ask <question>         - Ask the research agent
  report <topic>         - Generate a research report
  recall <query>         - Recall past investigation notes
  list [type]            - List documents (optionally filter by type)
  stats                  - Show knowledge base statistics
  catalog list           - List catalogs
  catalog create <name>  - Create a catalog
  tag list               - List all tags
  tag <doc_id> <tag>     - Tag a document
  journal add <text>     - Add a journal entry
  journal list           - List journal entries
  help                   - Show this help
  quit                   - Exit
"""
        print(help_text)

    def _cmd_ingest(self, args: str):
        if not args:
            print("Usage: ingest <path>")
            return
        path = args.strip().strip('"\'')
        print(f"Ingesting: {path}")
        result = self.kb.ingest(path)
        if isinstance(result, list):
            print(f"Ingested {len(result)} documents")
        elif result:
            print(f"Ingested: {result.title} ({result.file_type}, {result.word_count} words)")
        else:
            print("Ingestion failed or file already up to date")

    def _cmd_find(self, args: str):
        if not args:
            print("Usage: find <query>")
            return
        results = self.kb.find(args, limit=5)
        if not results:
            print("No results found")
            return
        print(f"\nFound {len(results)} results:\n")
        for r in results:
            print(f"[{r.rank}] {r.title}")
            print(f"    Score: {r.score:.3f} | {r.file_path}")
            if r.page_number:
                print(f"    Page: {r.page_number}")
            if r.line_start:
                print(f"    Lines: {r.line_start}-{r.line_end}")
            print(f"    {r.highlight[:150]}")
            print()

    def _cmd_ask(self, args: str):
        if not args:
            print("Usage: ask <question>")
            return
        print(f"\nResearching: {args}\n")
        result = self.kb.ask(args)
        print(result['answer'])
        print(f"\n[Sources used: {result['sources_used']}, "
              f"Chunks retrieved: {result['chunks_retrieved']}]")
        if result.get('note_id'):
            print(f"[Saved as note: {result['note_id']}]")

    def _cmd_report(self, args: str):
        if not args:
            print("Usage: report <topic>")
            return
        print(f"\nGenerating report on: {args}\n")
        report = self.kb.report(args)
        print(f"## {report['topic']}\n")
        print(report['summary'])
        print(f"\n[{len(report['sections'])} sections, "
              f"{report['total_sources']} sources]")
        if report.get('note_id'):
            print(f"[Saved as note: {report['note_id']}]")

    def _cmd_recall(self, args: str):
        if not args:
            print("Usage: recall <query>")
            return
        notes = self.kb.recall(args, limit=5)
        if not notes:
            print("No matching notes found")
            return
        print(f"\nFound {len(notes)} notes:\n")
        for note in notes:
            print(f"[{note.note_id[:8]}] {note.query}")
            print(f"    {note.created_at}")
            print(f"    {note.answer[:200]}...")
            print()

    def _cmd_stats(self):
        stats = self.kb.get_stats()
        print("\nKnowledge Base Statistics:")
        print(f"  Documents: {stats['total_documents']}")
        print(f"  Chunks: {stats['total_chunks']}")
        print(f"  Investigation Notes: {stats['total_notes']}")
        print(f"  Journal Entries: {stats['total_journal_entries']}")
        print(f"  Catalogs: {stats['total_catalogs']}")
        print(f"  Tags: {stats['total_tags']}")
        print(f"  Total Words: {stats['total_words']:,}")
        size_mb = stats['total_size_bytes'] / (1024 * 1024)
        print(f"  Total Size: {size_mb:.1f} MB")
        if stats['documents_by_type']:
            print("  By Type:")
            for ftype, count in stats['documents_by_type'].items():
                print(f"    {ftype}: {count}")

    def _cmd_catalog(self, args: str):
        parts = args.split(None, 1)
        subcmd = parts[0].lower() if parts else 'list'
        subargs = parts[1] if len(parts) > 1 else ''

        if subcmd == 'list':
            catalogs = self.kb.catalog_manager.list_catalogs()
            if not catalogs:
                print("No catalogs found")
                return
            for cat in catalogs:
                print(f"[{cat.catalog_id[:8]}] {cat.name}: {cat.description}")
        elif subcmd == 'create':
            if not subargs:
                print("Usage: catalog create <name>")
                return
            cat = self.kb.catalog_manager.create_catalog(subargs)
            print(f"Created catalog: {cat.name} ({cat.catalog_id})")
        else:
            print("Usage: catalog [list|create <name>]")

    def _cmd_tag(self, args: str):
        parts = args.split()
        if not parts or parts[0] == 'list':
            tags = self.kb.catalog_manager.list_tags()
            if not tags:
                print("No tags found")
                return
            for tag in tags:
                print(f"  {tag['name']} ({tag['doc_count']} docs)")
        elif len(parts) >= 2:
            doc_id, tag_name = parts[0], parts[1]
            self.kb.catalog_manager.tag_document(doc_id, tag_name)
            print(f"Tagged document {doc_id[:8]} with '{tag_name}'")
        else:
            print("Usage: tag list | tag <doc_id> <tag_name>")

    def _cmd_journal(self, args: str):
        parts = args.split(None, 1)
        subcmd = parts[0].lower() if parts else 'list'
        subargs = parts[1] if len(parts) > 1 else ''

        if subcmd == 'add':
            if not subargs:
                print("Usage: journal add <text>")
                return
            entry = self.kb.journal.create_entry(subargs)
            print(f"Journal entry created: {entry.entry_id[:8]}")
        elif subcmd == 'list':
            entries = self.kb.journal.list_entries(limit=10)
            if not entries:
                print("No journal entries")
                return
            for entry in entries:
                print(f"[{entry.entry_id[:8]}] {entry.created_at}")
                print(f"  {entry.content[:150]}")
                print()
        else:
            print("Usage: journal [add <text>|list]")

    def _cmd_list(self, args: str):
        filters = {}
        if args:
            filters['file_type'] = args.strip()
        docs = self.kb.list_documents(limit=20, **filters)
        if not docs:
            print("No documents found")
            return
        print(f"\n{len(docs)} documents:\n")
        for doc in docs:
            print(f"[{doc['doc_id'][:8]}] {doc['title']}")
            print(f"    {doc['file_type']} | {doc['word_count']} words | {doc['file_path']}")


# ─────────────────────────────────────────────────────────────────────────────
# Factory / Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def create_knowledge_base(base_path: str = "./marginalia_kb",
                           llm_provider: str = "anthropic",
                           llm_model: Optional[str] = None,
                           use_embeddings: bool = False,
                           **kwargs) -> KnowledgeBase:
    """Factory function to create a KnowledgeBase instance."""
    return KnowledgeBase(
        base_path=base_path,
        llm_provider=llm_provider,
        llm_model=llm_model,
        use_embeddings=use_embeddings,
        **kwargs
    )


def main():
    """Main entry point for the Marginalia CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Marginalia: Personal Knowledge Management System'
    )
    parser.add_argument('--base-path', default='./marginalia_kb',
                        help='Path to the knowledge base directory')
    parser.add_argument('--llm-provider', default='anthropic',
                        choices=['anthropic', 'openai'],
                        help='LLM provider to use')
    parser.add_argument('--llm-model', default=None,
                        help='LLM model name')
    parser.add_argument('--use-embeddings', action='store_true',
                        help='Enable semantic embeddings')
    parser.add_argument('--ingest', metavar='PATH',
                        help='Ingest a file or directory and exit')
    parser.add_argument('--ask', metavar='QUESTION',
                        help='Ask a question and exit')
    parser.add_argument('--report', metavar='TOPIC',
                        help='Generate a report and exit')
    parser.add_argument('--stats', action='store_true',
                        help='Show statistics and exit')

    args = parser.parse_args()

    kb = create_knowledge_base(
        base_path=args.base_path,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        use_embeddings=args.use_embeddings,
    )

    if args.ingest:
        result = kb.ingest(args.ingest)
        if isinstance(result, list):
            print(f"Ingested {len(result)} documents")
        elif result:
            print(f"Ingested: {result.title}")
        return

    if args.ask:
        result = kb.ask(args.ask)
        print(result['answer'])
        return

    if args.report:
        result = kb.report(args.report)
        print(f"# {result['topic']}\n")
        print(result['summary'])
        return

    if args.stats:
        stats = kb.get_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")
        return

    # Interactive CLI
    cli = CLI(kb)
    cli.run()


if __name__ == '__main__':
    main()