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
    content_hash: str
    size_bytes: int
    created_at: str
    modified_at: str
    ingested_at: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    catalog_id: Optional[str] = None
    folder_path: str = ""
    language: str = "en"
    word_count: int = 0
    page_count: int = 0
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentRecord':
        return cls(**data)


@dataclass
class Chunk:
    """A text chunk from a document."""
    chunk_id: str
    doc_id: str
    content: str
    chunk_index: int
    start_line: int
    end_line: int
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    section_title: str = ""
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['embedding'] = None  # Don't serialize embeddings to dict
        return d


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
    start_line: int
    end_line: int
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    section_title: str = ""
    match_type: str = "lexical"  # lexical, semantic, hybrid
    highlights: List[str] = field(default_factory=list)


@dataclass
class Citation:
    """A citation reference in an answer."""
    citation_id: str
    doc_id: str
    file_path: str
    title: str
    quote: str
    location: str  # e.g., "page 3", "lines 45-67", "section Introduction"
    relevance_note: str = ""


@dataclass
class InvestigationNote:
    """A durable note from an investigation session."""
    note_id: str
    session_id: str
    query: str
    answer: str
    citations: List[Citation]
    created_at: str
    tags: List[str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    follow_up_questions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class Catalog:
    """A named collection of documents."""
    catalog_id: str
    name: str
    description: str
    created_at: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Tag:
    """A tag for organizing documents."""
    tag_id: str
    name: str
    color: str = "#888888"
    description: str = ""
    parent_tag_id: Optional[str] = None


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
    relation_type: str  # cites, references, similar, contradicts, extends
    confidence: float
    evidence: str = ""
    created_at: str = ""
    auto_detected: bool = True


@dataclass
class JournalEntry:
    """A journal entry for tracking research progress."""
    entry_id: str
    session_id: str
    content: str
    created_at: str
    tags: List[str] = field(default_factory=list)
    linked_doc_ids: List[str] = field(default_factory=list)
    entry_type: str = "note"  # note, query, finding, todo


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
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                file_path TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                file_type TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                catalog_id TEXT,
                folder_path TEXT DEFAULT '',
                language TEXT DEFAULT 'en',
                word_count INTEGER DEFAULT 0,
                page_count INTEGER DEFAULT 0,
                summary TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                start_page INTEGER,
                end_page INTEGER,
                section_title TEXT DEFAULT '',
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

            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                embedding BLOB NOT NULL,
                model_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS catalogs (
                catalog_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS tags (
                tag_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                color TEXT DEFAULT '#888888',
                description TEXT DEFAULT '',
                parent_tag_id TEXT
            );

            CREATE TABLE IF NOT EXISTS views (
                view_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                query TEXT NOT NULL,
                filters TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                description TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS relations (
                relation_id TEXT PRIMARY KEY,
                source_doc_id TEXT NOT NULL,
                target_doc_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                evidence TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                auto_detected INTEGER DEFAULT 1,
                FOREIGN KEY (source_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (target_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                entry_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                linked_doc_ids TEXT DEFAULT '[]',
                entry_type TEXT DEFAULT 'note'
            );

            CREATE TABLE IF NOT EXISTS investigation_notes (
                note_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                query TEXT NOT NULL,
                answer TEXT NOT NULL,
                citations TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                follow_up_questions TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS document_tags (
                doc_id TEXT NOT NULL,
                tag_id TEXT NOT NULL,
                PRIMARY KEY (doc_id, tag_id),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_documents_folder ON documents(folder_path);
            CREATE INDEX IF NOT EXISTS idx_documents_catalog ON documents(catalog_id);
            CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(file_type);
            CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
            CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_doc_id);
            CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_doc_id);
            CREATE INDEX IF NOT EXISTS idx_journal_session ON journal_entries(session_id);
            CREATE INDEX IF NOT EXISTS idx_notes_session ON investigation_notes(session_id);
        """)
        conn.commit()
        conn.close()

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


# ─────────────────────────────────────────────────────────────────────────────
# File Ingestion
# ─────────────────────────────────────────────────────────────────────────────

class FileIngester:
    """Handles ingestion of various file types."""

    SUPPORTED_EXTENSIONS = {
        '.txt', '.md', '.markdown', '.rst', '.org',
        '.pdf',
        '.docx', '.doc',
        '.xlsx', '.xls', '.csv', '.tsv',
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp',
        '.log', '.jsonl', '.ndjson',
        '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
        '.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.go', '.rs',
        '.html', '.htm', '.xml',
        '.zip', '.tar', '.tar.gz', '.tgz', '.tar.bz2',
    }

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    def ingest_file(self, file_path: str) -> Tuple[DocumentRecord, List[Chunk]]:
        """Ingest a file and return document record and chunks."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_type = self._detect_file_type(path)
        content_hash = self._compute_hash(path)
        stat = path.stat()

        doc_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()

        doc = DocumentRecord(
            doc_id=doc_id,
            file_path=str(path.resolve()),
            title=path.stem,
            file_type=file_type,
            content_hash=content_hash,
            size_bytes=stat.st_size,
            created_at=datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified_at=datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            ingested_at=now,
            folder_path=str(path.parent.resolve()),
        )

        text_content, metadata, page_count = self._extract_content(path, file_type)
        doc.metadata = metadata
        doc.page_count = page_count
        doc.word_count = len(text_content.split()) if text_content else 0

        chunks = self._chunk_content(text_content, doc_id, file_type, path)

        return doc, chunks

    def _detect_file_type(self, path: Path) -> str:
        """Detect file type from extension and mime type."""
        ext = path.suffix.lower()
        mime, _ = mimetypes.guess_type(str(path))

        if ext in ('.txt', '.rst', '.org'):
            return 'text'
        elif ext in ('.md', '.markdown'):
            return 'markdown'
        elif ext == '.pdf':
            return 'pdf'
        elif ext in ('.docx', '.doc'):
            return 'docx'
        elif ext in ('.xlsx', '.xls'):
            return 'spreadsheet'
        elif ext in ('.csv', '.tsv'):
            return 'csv'
        elif ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'):
            return 'image'
        elif ext in ('.log', '.jsonl', '.ndjson'):
            return 'log'
        elif ext in ('.json',):
            return 'json'
        elif ext in ('.yaml', '.yml'):
            return 'yaml'
        elif ext in ('.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.go', '.rs'):
            return 'code'
        elif ext in ('.html', '.htm'):
            return 'html'
        elif ext in ('.xml',):
            return 'xml'
        elif ext in ('.zip',):
            return 'zip'
        elif ext in ('.tar', '.tar.gz', '.tgz', '.tar.bz2'):
            return 'tar'
        elif mime and mime.startswith('text/'):
            return 'text'
        else:
            return 'binary'

    def _compute_hash(self, path: Path) -> str:
        """Compute SHA-256 hash of file."""
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()

    def _extract_content(self, path: Path, file_type: str) -> Tuple[str, Dict, int]:
        """Extract text content from file."""
        metadata = {}
        page_count = 1

        try:
            if file_type in ('text', 'markdown', 'rst', 'code', 'yaml', 'toml', 'ini', 'xml'):
                content = self._read_text_file(path)
                page_count = max(1, len(content.split('\n')) // 50)

            elif file_type == 'pdf':
                content, page_count = self._extract_pdf(path)

            elif file_type == 'docx':
                content, metadata = self._extract_docx(path)

            elif file_type == 'spreadsheet':
                content, metadata = self._extract_spreadsheet(path)

            elif file_type == 'csv':
                content = self._extract_csv(path)

            elif file_type == 'image':
                content, metadata = self._extract_image(path)

            elif file_type in ('log', 'jsonl'):
                content = self._read_text_file(path)

            elif file_type == 'json':
                content = self._extract_json(path)

            elif file_type == 'html':
                content = self._extract_html(path)

            elif file_type == 'zip':
                content, metadata = self._extract_zip(path)

            elif file_type == 'tar':
                content, metadata = self._extract_tar(path)

            else:
                content = f"[Binary file: {path.name}]"

        except Exception as e:
            logger.warning(f"Error extracting content from {path}: {e}")
            content = f"[Error extracting content: {e}]"

        return content, metadata, page_count

    def _read_text_file(self, path: Path) -> str:
        """Read a text file with encoding detection."""
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'ascii']
        for enc in encodings:
            try:
                return path.read_text(encoding=enc)
            except (UnicodeDecodeError, UnicodeError):
                continue
        return path.read_bytes().decode('utf-8', errors='replace')

    def _extract_pdf(self, path: Path) -> Tuple[str, int]:
        """Extract text from PDF."""
        if not HAS_PYPDF:
            return f"[PDF: {path.name} - pypdf not installed]", 0

        pages = []
        try:
            reader = pypdf.PdfReader(str(path))
            page_count = len(reader.pages)
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages.append(f"[Page {i+1}]\n{text}")
            return "\n\n".join(pages), page_count
        except Exception as e:
            return f"[PDF extraction error: {e}]", 0

    def _extract_docx(self, path: Path) -> Tuple[str, Dict]:
        """Extract text from DOCX."""
        if not HAS_DOCX:
            return f"[DOCX: {path.name} - python-docx not installed]", {}

        try:
            doc = docx.Document(str(path))
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    style = para.style.name if para.style else ""
                    if style.startswith('Heading'):
                        paragraphs.append(f"\n## {para.text}\n")
                    else:
                        paragraphs.append(para.text)

            metadata = {}
            if doc.core_properties:
                props = doc.core_properties
                metadata = {
                    'author': props.author or '',
                    'title': props.title or '',
                    'subject': props.subject or '',
                    'created': str(props.created) if props.created else '',
                }

            return "\n".join(paragraphs), metadata
        except Exception as e:
            return f"[DOCX extraction error: {e}]", {}

    def _extract_spreadsheet(self, path: Path) -> Tuple[str, Dict]:
        """Extract text from Excel spreadsheet."""
        if not HAS_OPENPYXL:
            return f"[Spreadsheet: {path.name} - openpyxl not installed]", {}

        try:
            wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
            sheets_content = []
            metadata = {'sheets': []}

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                metadata['sheets'].append(sheet_name)
                rows = []
                for row in ws.iter_rows(values_only=True):
                    row_str = '\t'.join(str(cell) if cell is not None else '' for cell in row)
                    if row_str.strip():
                        rows.append(row_str)
                if rows:
                    sheets_content.append(f"[Sheet: {sheet_name}]\n" + "\n".join(rows))

            return "\n\n".join(sheets_content), metadata
        except Exception as e:
            return f"[Spreadsheet extraction error: {e}]", {}

    def _extract_csv(self, path: Path) -> str:
        """Extract text from CSV."""
        try:
            import csv as csv_module
            content = self._read_text_file(path)
            return content
        except Exception as e:
            return f"[CSV extraction error: {e}]"

    def _extract_image(self, path: Path) -> Tuple[str, Dict]:
        """Extract metadata from image."""
        metadata = {}
        if HAS_PIL:
            try:
                with Image.open(str(path)) as img:
                    metadata = {
                        'format': img.format,
                        'mode': img.mode,
                        'size': f"{img.width}x{img.height}",
                        'width': img.width,
                        'height': img.height,
                    }
                    if hasattr(img, '_getexif') and img._getexif():
                        exif = img._getexif()
                        if exif:
                            metadata['has_exif'] = True
            except Exception as e:
                metadata['error'] = str(e)

        content = f"[Image: {path.name}, {metadata.get('size', 'unknown size')}, format: {metadata.get('format', 'unknown')}]"
        return content, metadata

    def _extract_json(self, path: Path) -> str:
        """Extract text from JSON."""
        try:
            content = self._read_text_file(path)
            data = json.loads(content)
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception:
            return self._read_text_file(path)

    def _extract_html(self, path: Path) -> str:
        """Extract text from HTML."""
        content = self._read_text_file(path)
        # Simple HTML tag stripping
        text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&quot;', '"', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _extract_zip(self, path: Path) -> Tuple[str, Dict]:
        """Extract listing and text content from ZIP."""
        try:
            with zipfile.ZipFile(str(path), 'r') as zf:
                members = zf.namelist()
                metadata = {'members': members, 'count': len(members)}
                content_parts = [f"[ZIP Archive: {path.name}]", f"Members ({len(members)}):"]

                for member in members[:100]:  # Limit to first 100
                    info = zf.getinfo(member)
                    content_parts.append(f"  - {member} ({info.file_size} bytes)")

                # Try to read text members
                text_parts = []
                for member in members:
                    if any(member.endswith(ext) for ext in ('.txt', '.md', '.json', '.csv', '.log')):
                        try:
                            with zf.open(member) as f:
                                text = f.read(65536).decode('utf-8', errors='replace')
                                text_parts.append(f"\n[Member: {member}]\n{text[:2000]}")
                        except Exception:
                            pass

                return "\n".join(content_parts) + "\n".join(text_parts), metadata
        except Exception as e:
            return f"[ZIP extraction error: {e}]", {}

    def _extract_tar(self, path: Path) -> Tuple[str, Dict]:
        """Extract listing from TAR archive."""
        try:
            with tarfile.open(str(path), 'r:*') as tf:
                members = tf.getnames()
                metadata = {'members': members, 'count': len(members)}
                content_parts = [f"[TAR Archive: {path.name}]", f"Members ({len(members)}):"]

                for member in members[:100]:
                    content_parts.append(f"  - {member}")

                return "\n".join(content_parts), metadata
        except Exception as e:
            return f"[TAR extraction error: {e}]", {}

    def _chunk_content(self, content: str, doc_id: str, file_type: str, path: Path) -> List[Chunk]:
        """Split content into chunks."""
        if not content or content.startswith('['):
            # For non-text files, create a single chunk
            return [Chunk(
                chunk_id=str(uuid.uuid4()),
                doc_id=doc_id,
                content=content,
                chunk_index=0,
                start_line=1,
                end_line=1,
                section_title=path.name,
            )]

        chunks = []
        lines = content.split('\n')

        if file_type == 'pdf':
            chunks = self._chunk_by_pages(content, doc_id)
        elif file_type in ('markdown', 'rst', 'org'):
            chunks = self._chunk_by_sections(lines, doc_id)
        else:
            chunks = self._chunk_by_lines(lines, doc_id)

        return chunks if chunks else [Chunk(
            chunk_id=str(uuid.uuid4()),
            doc_id=doc_id,
            content=content[:4000],
            chunk_index=0,
            start_line=1,
            end_line=len(lines),
        )]

    def _chunk_by_pages(self, content: str, doc_id: str) -> List[Chunk]:
        """Chunk PDF content by pages."""
        chunks = []
        page_pattern = re.compile(r'\[Page (\d+)\]')
        pages = page_pattern.split(content)

        chunk_idx = 0
        i = 1
        while i < len(pages) - 1:
            page_num = int(pages[i])
            page_content = pages[i + 1].strip() if i + 1 < len(pages) else ""
            if page_content:
                chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=page_content,
                    chunk_index=chunk_idx,
                    start_line=1,
                    end_line=len(page_content.split('\n')),
                    start_page=page_num,
                    end_page=page_num,
                    section_title=f"Page {page_num}",
                ))
                chunk_idx += 1
            i += 2

        return chunks

    def _chunk_by_sections(self, lines: List[str], doc_id: str) -> List[Chunk]:
        """Chunk markdown/structured content by sections."""
        chunks = []
        current_section = ""
        current_lines = []
        current_start = 1
        chunk_idx = 0

        heading_pattern = re.compile(r'^#{1,6}\s+(.+)$')

        for i, line in enumerate(lines, 1):
            match = heading_pattern.match(line)
            if match and current_lines:
                # Save current section
                content = "\n".join(current_lines).strip()
                if content:
                    chunks.append(Chunk(
                        chunk_id=str(uuid.uuid4()),
                        doc_id=doc_id,
                        content=content,
                        chunk_index=chunk_idx,
                        start_line=current_start,
                        end_line=i - 1,
                        section_title=current_section,
                    ))
                    chunk_idx += 1

                current_section = match.group(1)
                current_lines = [line]
                current_start = i
            else:
                current_lines.append(line)

                # Also chunk by size
                if len("\n".join(current_lines)) > 3000:
                    content = "\n".join(current_lines).strip()
                    if content:
                        chunks.append(Chunk(
                            chunk_id=str(uuid.uuid4()),
                            doc_id=doc_id,
                            content=content,
                            chunk_index=chunk_idx,
                            start_line=current_start,
                            end_line=i,
                            section_title=current_section,
                        ))
                        chunk_idx += 1
                    current_lines = []
                    current_start = i + 1

        # Last section
        if current_lines:
            content = "\n".join(current_lines).strip()
            if content:
                chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=content,
                    chunk_index=chunk_idx,
                    start_line=current_start,
                    end_line=len(lines),
                    section_title=current_section,
                ))

        return chunks

    def _chunk_by_lines(self, lines: List[str], doc_id: str, chunk_size: int = 100, overlap: int = 10) -> List[Chunk]:
        """Chunk content by line windows."""
        chunks = []
        chunk_idx = 0
        i = 0

        while i < len(lines):
            end = min(i + chunk_size, len(lines))
            chunk_lines = lines[i:end]
            content = "\n".join(chunk_lines).strip()

            if content:
                chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=content,
                    chunk_index=chunk_idx,
                    start_line=i + 1,
                    end_line=end,
                ))
                chunk_idx += 1

            i += chunk_size - overlap

        return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Search Engine
# ─────────────────────────────────────────────────────────────────────────────

class LexicalSearchEngine:
    """BM25-based lexical search engine using SQLite FTS5."""

    def __init__(self, db: Database):
        self.db = db

    def index_chunk(self, chunk: Chunk):
        """Index a chunk for full-text search."""
        try:
            self.db.execute(
                "INSERT OR REPLACE INTO chunks_fts(chunk_id, doc_id, content, section_title) VALUES (?, ?, ?, ?)",
                (chunk.chunk_id, chunk.doc_id, chunk.content, chunk.section_title)
            )
        except Exception as e:
            logger.warning(f"FTS index error: {e}")

    def search(self, query: str, limit: int = 20, doc_ids: Optional[List[str]] = None) -> List[Tuple[str, str, float]]:
        """Search chunks using FTS5. Returns (chunk_id, doc_id, score) tuples."""
        # Sanitize query for FTS5
        fts_query = self._prepare_fts_query(query)

        try:
            if doc_ids:
                placeholders = ','.join('?' * len(doc_ids))
                rows = self.db.fetchall(
                    f"""SELECT chunk_id, doc_id, rank
                        FROM chunks_fts
                        WHERE chunks_fts MATCH ?
                        AND doc_id IN ({placeholders})
                        ORDER BY rank
                        LIMIT ?""",
                    (fts_query, *doc_ids, limit)
                )
            else:
                rows = self.db.fetchall(
                    """SELECT chunk_id, doc_id, rank
                       FROM chunks_fts
                       WHERE chunks_fts MATCH ?
                       ORDER BY rank
                       LIMIT ?""",
                    (fts_query, limit)
                )

            results = []
            for row in rows:
                # FTS5 rank is negative (lower = better), normalize to positive score
                score = max(0.0, -float(row['rank']))
                results.append((row['chunk_id'], row['doc_id'], score))

            return results

        except Exception as e:
            logger.warning(f"FTS search error: {e}")
            return self._fallback_search(query, limit, doc_ids)

    def _prepare_fts_query(self, query: str) -> str:
        """Prepare query for FTS5."""
        # Remove special FTS5 characters
        query = re.sub(r'[^\w\s\-]', ' ', query)
        terms = query.split()
        if not terms:
            return '""'
        # Use phrase search for multi-word queries
        if len(terms) == 1:
            return f'"{terms[0]}"*'
        # Try to match all terms
        return ' OR '.join(f'"{term}"*' for term in terms if len(term) > 2)

    def _fallback_search(self, query: str, limit: int, doc_ids: Optional[List[str]]) -> List[Tuple[str, str, float]]:
        """Fallback LIKE-based search."""
        terms = query.lower().split()
        if not terms:
            return []

        conditions = ' AND '.join(['LOWER(content) LIKE ?' for _ in terms])
        params = [f'%{term}%' for term in terms]

        if doc_ids:
            placeholders = ','.join('?' * len(doc_ids))
            sql = f"SELECT chunk_id, doc_id FROM chunks WHERE {conditions} AND doc_id IN ({placeholders}) LIMIT ?"
            params.extend(doc_ids)
        else:
            sql = f"SELECT chunk_id, doc_id FROM chunks WHERE {conditions} LIMIT ?"

        params.append(limit)

        try:
            rows = self.db.fetchall(sql, tuple(params))
            return [(row['chunk_id'], row['doc_id'], 1.0) for row in rows]
        except Exception as e:
            logger.error(f"Fallback search error: {e}")
            return []

    def highlight(self, chunk_id: str, query: str) -> List[str]:
        """Extract highlighted snippets from a chunk."""
        row = self.db.fetchone("SELECT content FROM chunks WHERE chunk_id = ?", (chunk_id,))
        if not row:
            return []

        content = row['content']
        terms = query.lower().split()
        highlights = []

        lines = content.split('\n')
        for line in lines:
            if any(term in line.lower() for term in terms):
                highlights.append(line.strip())
                if len(highlights) >= 3:
                    break

        return highlights


class SemanticSearchEngine:
    """Embedding-based semantic search engine."""

    def __init__(self, db: Database, model_name: str = "text-embedding-3-small"):
        self.db = db
        self.model_name = model_name
        self._embeddings_cache: Dict[str, List[float]] = {}

    def embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text."""
        if not HAS_OPENAI:
            return None

        try:
            client = openai.OpenAI()
            response = client.embeddings.create(
                input=text[:8000],
                model=self.model_name
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Embedding error: {e}")
            return None

    def store_embedding(self, chunk_id: str, doc_id: str, embedding: List[float]):
        """Store embedding in database."""
        import struct
        blob = struct.pack(f'{len(embedding)}f', *embedding)
        now = datetime.datetime.utcnow().isoformat()
        self.db.execute(
            "INSERT OR REPLACE INTO embeddings (chunk_id, doc_id, embedding, model_name, created_at) VALUES (?, ?, ?, ?, ?)",
            (chunk_id, doc_id, blob, self.model_name, now)
        )
        self._embeddings_cache[chunk_id] = embedding

    def load_embedding(self, chunk_id: str) -> Optional[List[float]]:
        """Load embedding from database."""
        if chunk_id in self._embeddings_cache:
            return self._embeddings_cache[chunk_id]

        import struct
        row = self.db.fetchone("SELECT embedding FROM embeddings WHERE chunk_id = ?", (chunk_id,))
        if row:
            blob = row['embedding']
            n = len(blob) // 4
            embedding = list(struct.unpack(f'{n}f', blob))
            self._embeddings_cache[chunk_id] = embedding
            return embedding
        return None

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

    def search(self, query: str, limit: int = 20, doc_ids: Optional[List[str]] = None) -> List[Tuple[str, str, float]]:
        """Semantic search using embeddings."""
        query_embedding = self.embed_text(query)
        if not query_embedding:
            return []

        # Load all embeddings
        if doc_ids:
            placeholders = ','.join('?' * len(doc_ids))
            rows = self.db.fetchall(
                f"SELECT chunk_id, doc_id, embedding FROM embeddings WHERE doc_id IN ({placeholders})",
                tuple(doc_ids)
            )
        else:
            rows = self.db.fetchall("SELECT chunk_id, doc_id, embedding FROM embeddings")

        import struct
        results = []
        for row in rows:
            blob = row['embedding']
            n = len(blob) // 4
            emb = list(struct.unpack(f'{n}f', blob))
            score = self.cosine_similarity(query_embedding, emb)
            results.append((row['chunk_id'], row['doc_id'], score))

        results.sort(key=lambda x: x[2], reverse=True)
        return results[:limit]


class HybridSearchEngine:
    """Combines lexical and semantic search with reranking."""

    def __init__(self, db: Database, lexical: LexicalSearchEngine, semantic: Optional[SemanticSearchEngine] = None):
        self.db = db
        self.lexical = lexical
        self.semantic = semantic

    def search(
        self,
        query: str,
        limit: int = 20,
        use_semantic: bool = False,
        doc_ids: Optional[List[str]] = None,
        source_quota: Optional[Dict[str, int]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Perform hybrid search and return ranked results."""

        # Apply filters to get candidate doc_ids
        if filters:
            doc_ids = self._apply_filters(filters, doc_ids)

        # Lexical search
        lexical_results = self.lexical.search(query, limit=limit * 2, doc_ids=doc_ids)

        # Semantic search
        semantic_results = []
        if use_semantic and self.semantic:
            semantic_results = self.semantic.search(query, limit=limit * 2, doc_ids=doc_ids)

        # Combine scores using Reciprocal Rank Fusion
        combined = self._reciprocal_rank_fusion(lexical_results, semantic_results)

        # Apply source quotas
        if source_quota:
            combined = self._apply_source_quota(combined, source_quota)

        # Build SearchResult objects
        results = []
        for rank, (chunk_id, doc_id, score) in enumerate(combined[:limit]):
            chunk_row = self.db.fetchone(
                "SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)
            )
            doc_row = self.db.fetchone(
                "SELECT * FROM documents WHERE doc_id = ?", (doc_id,)
            )

            if not chunk_row or not doc_row:
                continue

            match_type = "lexical"
            if use_semantic and semantic_results:
                match_type = "hybrid"

            highlights = self.lexical.highlight(chunk_id, query)

            results.append(SearchResult(
                doc_id=doc_id,
                chunk_id=chunk_id,
                file_path=doc_row['file_path'],
                title=doc_row['title'],
                content=chunk_row['content'],
                score=score,
                rank=rank + 1,
                start_line=chunk_row['start_line'],
                end_line=chunk_row['end_line'],
                start_page=chunk_row['start_page'],
                end_page=chunk_row['end_page'],
                section_title=chunk_row['section_title'],
                match_type=match_type,
                highlights=highlights,
            ))

        return results

    def _reciprocal_rank_fusion(
        self,
        lexical: List[Tuple[str, str, float]],
        semantic: List[Tuple[str, str, float]],
        k: int = 60,
        lexical_weight: float = 0.7,
        semantic_weight: float = 0.3,
    ) -> List[Tuple[str, str, float]]:
        """Combine results using Reciprocal Rank Fusion."""
        scores: Dict[str, Dict] = {}

        for rank, (chunk_id, doc_id, _) in enumerate(lexical):
            if chunk_id not in scores:
                scores[chunk_id] = {'doc_id': doc_id, 'score': 0.0}
            scores[chunk_id]['score'] += lexical_weight * (1.0 / (k + rank + 1))

        for rank, (chunk_id, doc_id, _) in enumerate(semantic):
            if chunk_id not in scores:
                scores[chunk_id] = {'doc_id': doc_id, 'score': 0.0}
            scores[chunk_id]['score'] += semantic_weight * (1.0 / (k + rank + 1))

        sorted_results = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)
        return [(chunk_id, data['doc_id'], data['score']) for chunk_id, data in sorted_results]

    def _apply_filters(self, filters: Dict[str, Any], existing_doc_ids: Optional[List[str]]) -> Optional[List[str]]:
        """Apply filters to get matching doc_ids."""
        conditions = []
        params = []

        if 'file_type' in filters:
            conditions.append("file_type = ?")
            params.append(filters['file_type'])

        if 'catalog_id' in filters:
            conditions.append("catalog_id = ?")
            params.append(filters['catalog_id'])

        if 'folder_path' in filters:
            conditions.append("folder_path LIKE ?")
            params.append(f"{filters['folder_path']}%")

        if 'tags' in filters:
            tag_names = filters['tags']
            if isinstance(tag_names, str):
                tag_names = [tag_names]
            for tag in tag_names:
                conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')

        if 'modified_after' in filters:
            conditions.append("modified_at >= ?")
            params.append(filters['modified_after'])

        if not conditions:
            return existing_doc_ids

        where = " AND ".join(conditions)
        rows = self.db.fetchall(f"SELECT doc_id FROM documents WHERE {where}", tuple(params))
        filtered_ids = [row['doc_id'] for row in rows]

        if existing_doc_ids:
            filtered_ids = [d for d in filtered_ids if d in existing_doc_ids]

        return filtered_ids if filtered_ids else None

    def _apply_source_quota(
        self,
        results: List[Tuple[str, str, float]],
        quota: Dict[str, int]
    ) -> List[Tuple[str, str, float]]:
        """Apply per-source quotas to results."""
        doc_counts: Dict[str, int] = defaultdict(int)
        filtered = []

        for chunk_id, doc_id, score in results:
            max_per_doc = quota.get(doc_id, quota.get('default', 999))
            if doc_counts[doc_id] < max_per_doc:
                filtered.append((chunk_id, doc_id, score))
                doc_counts[doc_id] += 1

        return filtered


# ─────────────────────────────────────────────────────────────────────────────
# Document Reader
# ─────────────────────────────────────────────────────────────────────────────

class DocumentReader:
    """Reads specific sections/windows from original files."""

    def __init__(self, ingester: FileIngester):
        self.ingester = ingester

    def read_lines(self, file_path: str, start_line: int, end_line: int, context: int = 5) -> str:
        """Read specific lines from a file."""
        path = Path(file_path)
        if not path.exists():
            return f"[File not found: {file_path}]"

        try:
            content = self.ingester._read_text_file(path)
            lines = content.split('\n')
            start = max(0, start_line - 1 - context)
            end = min(len(lines), end_line + context)
            selected = lines[start:end]
            return '\n'.join(selected)
        except Exception as e:
            return f"[Error reading lines: {e}]"

    def read_pages(self, file_path: str, start_page: int, end_page: int) -> str:
        """Read specific pages from a PDF."""
        path = Path(file_path)
        if not path.exists():
            return f"[File not found: {file_path}]"

        if not HAS_PYPDF:
            return "[pypdf not installed]"

        try:
            reader = pypdf.PdfReader(str(path))
            pages = []
            for i in range(start_page - 1, min(end_page, len(reader.pages))):
                text = reader.pages[i].extract_text() or ""
                pages.append(f"[Page {i+1}]\n{text}")
            return "\n\n".join(pages)
        except Exception as e:
            return f"[Error reading pages: {e}]"

    def read_section(self, file_path: str, section_title: str) -> str:
        """Read a specific section from a structured document."""
        path = Path(file_path)
        if not path.exists():
            return f"[File not found: {file_path}]"

        try:
            content = self.ingester._read_text_file(path)
            lines = content.split('\n')
            in_section = False
            section_lines = []
            heading_pattern = re.compile(r'^#{1,6}\s+(.+)$')

            for line in lines:
                match = heading_pattern.match(line)
                if match:
                    if in_section:
                        break
                    if section_title.lower() in match.group(1).lower():
                        in_section = True
                        section_lines.append(line)
                elif in_section:
                    section_lines.append(line)

            if section_lines:
                return '\n'.join(section_lines)
            return f"[Section '{section_title}' not found]"
        except Exception as e:
            return f"[Error reading section: {e}]"

    def read_archive_member(self, archive_path: str, member_name: str) -> str:
        """Read a specific member from an archive."""
        path = Path(archive_path)
        if not path.exists():
            return f"[Archive not found: {archive_path}]"

        try:
            if archive_path.endswith('.zip'):
                with zipfile.ZipFile(str(path), 'r') as zf:
                    with zf.open(member_name) as f:
                        return f.read().decode('utf-8', errors='replace')
            elif any(archive_path.endswith(ext) for ext in ('.tar', '.tar.gz', '.tgz', '.tar.bz2')):
                with tarfile.open(str(path), 'r:*') as tf:
                    member = tf.getmember(member_name)
                    f = tf.extractfile(member)
                    if f:
                        return f.read().decode('utf-8', errors='replace')
            return "[Unsupported archive format]"
        except Exception as e:
            return f"[Error reading archive member: {e}]"

    def read_table_slice(self, file_path: str, sheet: Optional[str] = None,
                         row_start: int = 1, row_end: int = 50,
                         col_start: int = 1, col_end: int = 20) -> str:
        """Read a slice of a spreadsheet."""
        path = Path(file_path)
        if not path.exists():
            return f"[File not found: {file_path}]"

        if not HAS_OPENPYXL:
            return "[openpyxl not installed]"

        try:
            wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
            ws = wb[sheet] if sheet and sheet in wb.sheetnames else wb.active

            rows = []
            for i, row in enumerate(ws.iter_rows(
                min_row=row_start, max_row=row_end,
                min_col=col_start, max_col=col_end,
                values_only=True
            )):
                row_str = '\t'.join(str(cell) if cell is not None else '' for cell in row)
                rows.append(row_str)

            return '\n'.join(rows)
        except Exception as e:
            return f"[Error reading table slice: {e}]"

    def read_chunk_window(self, search_result: SearchResult, context_lines: int = 10) -> str:
        """Read the original file window for a search result."""
        file_path = search_result.file_path
        path = Path(file_path)

        if not path.exists():
            return search_result.content  # Fall back to stored content

        file_type = self.ingester._detect_file_type(path)

        if file_type == 'pdf' and search_result.start_page:
            return self.read_pages(file_path, search_result.start_page, search_result.end_page or search_result.start_page)
        elif search_result.start_line and search_result.end_line:
            return self.read_lines(file_path, search_result.start_line, search_result.end_line, context_lines)
        else:
            return search_result.content


# ─────────────────────────────────────────────────────────────────────────────
# Relation Mining
# ─────────────────────────────────────────────────────────────────────────────

class RelationMiner:
    """Mines relations between documents."""

    def __init__(self, db: Database):
        self.db = db

    def mine_lexical_relations(self, doc_id: str, top_k: int = 10) -> List[Relation]:
        """Find related documents using term overlap."""
        # Get terms from source document
        chunks = self.db.fetchall("SELECT content FROM chunks WHERE doc_id = ?", (doc_id,))
        if not chunks:
            return []

        source_text = " ".join(row['content'] for row in chunks).lower()
        source_terms = set(re.findall(r'\b[a-z]{4,}\b', source_text))
        source_terms -= self._stopwords()

        # Compare with other documents
        all_docs = self.db.fetchall("SELECT doc_id FROM documents WHERE doc_id != ?", (doc_id,))
        similarities = []

        for doc_row in all_docs:
            other_id = doc_row['doc_id']
            other_chunks = self.db.fetchall("SELECT content FROM chunks WHERE doc_id = ?", (other_id,))
            if not other_chunks:
                continue

            other_text = " ".join(row['content'] for row in other_chunks).lower()
            other_terms = set(re.findall(r'\b[a-z]{4,}\b', other_text))
            other_terms -= self._stopwords()

            if not source_terms or not other_terms:
                continue

            # Jaccard similarity
            intersection = len(source_terms & other_terms)
            union = len(source_terms | other_terms)
            similarity = intersection / union if union > 0 else 0.0

            if similarity > 0.05:
                similarities.append((other_id, similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)

        relations = []
        now = datetime.datetime.utcnow().isoformat()
        for other_id, score in similarities[:top_k]:
            relations.append(Relation(
                relation_id=str(uuid.uuid4()),
                source_doc_id=doc_id,
                target_doc_id=other_id,
                relation_type='similar',
                confidence=score,
                evidence=f"Term overlap similarity: {score:.3f}",
                created_at=now,
                auto_detected=True,
            ))

        return relations

    def mine_citation_relations(self, doc_id: str) -> List[Relation]:
        """Find citation relations by looking for file references."""
        chunks = self.db.fetchall("SELECT content FROM chunks WHERE doc_id = ?", (doc_id,))
        if not chunks:
            return []

        source_text = " ".join(row['content'] for row in chunks)

        # Look for file references
        file_patterns = [
            r'\b[\w\-]+\.(pdf|docx|txt|md|csv)\b',
            r'\[([^\]]+)\]\([^\)]+\)',  # Markdown links
        ]

        referenced_names = set()
        for pattern in file_patterns:
            matches = re.findall(pattern, source_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    referenced_names.add(match[0].lower())
                else:
                    referenced_names.add(match.lower())

        relations = []
        now = datetime.datetime.utcnow().isoformat()

        for name in referenced_names:
            rows = self.db.fetchall(
                "SELECT doc_id FROM documents WHERE LOWER(title) LIKE ? AND doc_id != ?",
                (f"%{name}%", doc_id)
            )
            for row in rows:
                relations.append(Relation(
                    relation_id=str(uuid.uuid4()),
                    source_doc_id=doc_id,
                    target_doc_id=row['doc_id'],
                    relation_type='references',
                    confidence=0.7,
                    evidence=f"File reference: {name}",
                    created_at=now,
                    auto_detected=True,
                ))

        return relations

    def _stopwords(self) -> set:
        return {
            'this', 'that', 'with', 'from', 'have', 'been', 'will', 'would',
            'could', 'should', 'their', 'there', 'they', 'what', 'when', 'where',
            'which', 'while', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'each', 'more', 'also', 'than',
            'then', 'some', 'such', 'only', 'other', 'same', 'both', 'very',
        }

    def store_relations(self, relations: List[Relation]):
        """Store relations in database."""
        for rel in relations:
            try:
                self.db.execute(
                    """INSERT OR IGNORE INTO relations
                       (relation_id, source_doc_id, target_doc_id, relation_type,
                        confidence, evidence, created_at, auto_detected)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (rel.relation_id, rel.source_doc_id, rel.target_doc_id,
                     rel.relation_type, rel.confidence, rel.evidence,
                     rel.created_at, int(rel.auto_detected))
                )
            except Exception as e:
                logger.warning(f"Error storing relation: {e}")
        self.db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# LLM Client
# ─────────────────────────────────────────────────────────────────────────────

class LLMClient:
    """Abstraction over different LLM providers."""

    def __init__(self, provider: str = "anthropic", model: Optional[str] = None):
        self.provider = provider
        self.model = model or self._default_model(provider)
        self._client = None

    def _default_model(self, provider: str) -> str:
        defaults = {
            'anthropic': 'claude-3-5-sonnet-20241022',
            'openai': 'gpt-4o',
        }
        return defaults.get(provider, 'claude-3-5-sonnet-20241022')

    def _get_client(self):
        if self._client is None:
            if self.provider == 'anthropic':
                if not HAS_ANTHROPIC:
                    raise ImportError("anthropic package not installed")
                self._client = anthropic.Anthropic()
            elif self.provider == 'openai':
                if not HAS_OPENAI:
                    raise ImportError("openai package not installed")
                self._client = openai.OpenAI()
        return self._client

    def complete(self, system: str, messages: List[Dict[str, str]], max_tokens: int = 4096) -> str:
        """Generate a completion."""
        try:
            client = self._get_client()

            if self.provider == 'anthropic':
                response = client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=messages,
                )
                return response.content[0].text

            elif self.provider == 'openai':
                all_messages = [{"role": "system", "content": system}] + messages
                response = client.chat.completions.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=all_messages,
                )
                return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM completion error: {e}")
            return f"[LLM Error: {e}]"

    def is_available(self) -> bool:
        """Check if LLM is available."""
        try:
            self._get_client()
            return True
        except Exception:
            return False


# ─────────────────────────────────────────────────────────────────────────────
# Research Agent
# ─────────────────────────────────────────────────────────────────────────────

class ResearchAgent:
    """The main research agent that answers queries with citations."""

    SYSTEM_PROMPT = """You are Marginalia, a research assistant for a personal knowledge base.
Your job is to answer questions by reading relevant documents and providing cited answers.

Guidelines:
1. Base your answers ONLY on the provided document excerpts
2. Cite every claim with [Doc: title, location]
3. Quote relevant passages directly when helpful
4. Acknowledge when information is incomplete or uncertain
5. Suggest follow-up questions when appropriate
6. Be concise but thorough

Format your response as:
## Answer
[Your answer with inline citations]

## Key Quotes
[Direct quotes from sources]

## Sources Used
[List of sources with locations]

## Follow-up Questions
[2-3 suggested follow-up questions]
"""

    def __init__(
        self,
        knowledge_base: 'KnowledgeBase',
        llm_client: LLMClient,
        reader: DocumentReader,
    ):
        self.kb = knowledge_base
        self.llm = llm_client
        self.reader = reader
        self.session_id = str(uuid.uuid4())

    def answer(
        self,
        query: str,
        max_sources: int = 5,
        use_semantic: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        source_quota: Optional[Dict[str, int]] = None,
        context_lines: int = 20,
    ) -> Tuple[str, List[Citation], List[SearchResult]]:
        """Answer a query with citations."""

        # Search for relevant chunks
        search_results = self.kb.search(
            query=query,
            limit=max_sources * 3,
            use_semantic=use_semantic,
            filters=filters,
            source_quota=source_quota,
        )

        if not search_results:
            return "No relevant documents found in the knowledge base.", [], []

        # Read original file windows
        source_windows = []
        used_results = search_results[:max_sources]

        for result in used_results:
            window_content = self.reader.read_chunk_window(result, context_lines)
            source_windows.append({
                'result': result,
                'content': window_content,
            })

        # Build context for LLM
        context = self._build_context(query, source_windows)

        # Generate answer
        if self.llm.is_available():
            messages = [{"role": "user", "content": context}]
            raw_answer = self.llm.complete(self.SYSTEM_PROMPT, messages)
        else:
            raw_answer = self._generate_fallback_answer(query, source_windows)

        # Extract citations
        citations = self._extract_citations(raw_answer, used_results)

        return raw_answer, citations, used_results

    def _build_context(self, query: str, source_windows: List[Dict]) -> str:
        """Build context string for LLM."""
        parts = [f"## Research Query\n{query}\n\n## Relevant Document Excerpts\n"]

        for i, sw in enumerate(source_windows, 1):
            result = sw['result']
            content = sw['content']

            location = ""
            if result.start_page:
                location = f"pages {result.start_page}-{result.end_page or result.start_page}"
            elif result.start_line:
                location = f"lines {result.start_line}-{result.end_line}"
            if result.section_title:
                location = f"{result.section_title}, {location}" if location else result.section_title

            parts.append(f"### Source {i}: {result.title}")
            parts.append(f"**File:** {result.file_path}")
            parts.append(f"**Location:** {location}")
            parts.append(f"**Relevance Score:** {result.score:.3f}")
            parts.append(f"\n```\n{content[:3000]}\n```\n")

        parts.append("\nPlease answer the query based on these sources, with citations.")
        return "\n".join(parts)

    def _generate_fallback_answer(self, query: str, source_windows: List[Dict]) -> str:
        """Generate a simple answer without LLM."""
        parts = [f"## Answer\nBased on the knowledge base (LLM not available):\n"]

        for sw in source_windows:
            result = sw['result']
            highlights = result.highlights
            if highlights:
                parts.append(f"\nFrom **{result.title}**:")
                for h in highlights[:2]:
                    parts.append(f"  > {h}")

        parts.append("\n## Sources Used")
        for sw in source_windows:
            result = sw['result']
            location = f"lines {result.start_line}-{result.end_line}"
            if result.start_page:
                location = f"page {result.start_page}"
            parts.append(f"- {result.title} ({location})")

        return "\n".join(parts)

    def _extract_citations(self, answer: str, results: List[SearchResult]) -> List[Citation]:
        """Extract citations from answer."""
        citations = []
        for result in results:
            location = ""
            if result.start_page:
                location = f"page {result.start_page}"
            elif result.start_line:
                location = f"lines {result.start_line}-{result.end_line}"
            if result.section_title:
                location = f"{result.section_title}" + (f", {location}" if location else "")

            quote = result.highlights[0] if result.highlights else result.content[:200]

            citations.append(Citation(
                citation_id=str(uuid.uuid4()),
                doc_id=result.doc_id,
                file_path=result.file_path,
                title=result.title,
                quote=quote,
                location=location,
                relevance_note=f"Score: {result.score:.3f}",
            ))

        return citations

    def investigate(
        self,
        query: str,
        save_note: bool = True,
        **kwargs
    ) -> InvestigationNote:
        """Run a full investigation and save a durable note."""
        answer, citations, results = self.answer(query, **kwargs)

        # Extract follow-up questions from answer
        follow_ups = self._extract_follow_ups(answer)

        note = InvestigationNote(
            note_id=str(uuid.uuid4()),
            session_id=self.session_id,
            query=query,
            answer=answer,
            citations=citations,
            created_at=datetime.datetime.utcnow().isoformat(),
            tags=[],
            metadata={
                'num_sources': len(results),
                'search_scores': [r.score for r in results],
            },
            follow_up_questions=follow_ups,
        )

        if save_note:
            self.kb.save_investigation_note(note)

        return note

    def _extract_follow_ups(self, answer: str) -> List[str]:
        """Extract follow-up questions from answer."""
        follow_ups = []
        in_section = False

        for line in answer.split('\n'):
            if 'follow-up' in line.lower() or 'follow up' in line.lower():
                in_section = True
                continue
            if in_section and line.startswith('#'):
                break
            if in_section and line.strip() and (line.strip().startswith('-') or line.strip()[0].isdigit()):
                q = re.sub(r'^[-\d\.\s]+', '', line.strip())
                if q:
                    follow_ups.append(q)

        return follow_ups[:5]

    def generate_report(
        self,
        topic: str,
        sections: Optional[List[str]] = None,
        max_sources_per_section: int = 3,
    ) -> str:
        """Generate a structured report on a topic."""
        if not sections:
            sections = ['Overview', 'Key Findings', 'Details', 'Conclusions']

        report_parts = [f"# Report: {topic}\n*Generated by Marginalia*\n"]

        for section in sections:
            section_query = f"{topic} {section}"
            answer, citations, _ = self.answer(
                section_query,
                max_sources=max_sources_per_section,
            )

            report_parts.append(f"\n## {section}\n")
            # Extract just the answer part
            answer_match = re.search(r'## Answer\n(.*?)(?=##|\Z)', answer, re.DOTALL)
            if answer_match:
                report_parts.append(answer_match.group(1).strip())
            else:
                report_parts.append(answer[:1000])

            if citations:
                report_parts.append("\n**Sources:**")
                for cit in citations[:3]:
                    report_parts.append(f"- {cit.title} ({cit.location})")

        return "\n".join(report_parts)


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge Base
# ─────────────────────────────────────────────────────────────────────────────

class KnowledgeBase:
    """The main knowledge base manager."""

    def __init__(self, base_path: str, db_path: Optional[str] = None):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        if db_path is None:
            db_path = str(self.base_path / '.marginalia' / 'marginalia.db')

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = Database(db_path)

        self.ingester = FileIngester(str(self.base_path))
        self.lexical = LexicalSearchEngine(self.db)
        self.semantic = SemanticSearchEngine(self.db)
        self.search_engine = HybridSearchEngine(self.db, self.lexical, self.semantic)
        self.reader = DocumentReader(self.ingester)
        self.relation_miner = RelationMiner(self.db)

    # ── Document Management ──────────────────────────────────────────────────

    def ingest(self, file_path: str, catalog_id: Optional[str] = None,
               tags: Optional[List[str]] = None, mine_relations: bool = True) -> DocumentRecord:
        """Ingest a file into the knowledge base."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check if already ingested
        existing = self.db.fetchone(
            "SELECT doc_id, content_hash FROM documents WHERE file_path = ?",
            (str(path.resolve()),)
        )

        new_hash = self.ingester._compute_hash(path)

        if existing and existing['content_hash'] == new_hash:
            logger.info(f"File unchanged, skipping: {file_path}")
            return self.get_document(existing['doc_id'])

        # Ingest
        doc, chunks = self.ingester.ingest_file(file_path)

        if catalog_id:
            doc.catalog_id = catalog_id

        if tags:
            doc.tags = tags

        # Store document
        if existing:
            # Update existing
            self._update_document(doc)
            # Remove old chunks
            self.db.execute("DELETE FROM chunks WHERE doc_id = ?", (doc.doc_id,))
        else:
            self._insert_document(doc)

        # Store chunks and index
        for chunk in chunks:
            self._insert_chunk(chunk)
            self.lexical.index_chunk(chunk)

        self.db.commit()

        # Mine relations
        if mine_relations:
            try:
                relations = self.relation_miner.mine_lexical_relations(doc.doc_id)
                relations += self.relation_miner.mine_citation_relations(doc.doc_id)
                self.relation_miner.store_relations(relations)
            except Exception as e:
                logger.warning(f"Relation mining error: {e}")

        logger.info(f"Ingested: {path.name} ({len(chunks)} chunks)")
        return doc

    def ingest_directory(self, dir_path: str, recursive: bool = True,
                         catalog_id: Optional[str] = None) -> List[DocumentRecord]:
        """Ingest all supported files in a directory."""
        path = Path(dir_path)
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")

        pattern = '**/*' if recursive else '*'
        docs = []

        for file_path in path.glob(pattern):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in self.ingester.SUPPORTED_EXTENSIONS:
                    try:
                        doc = self.ingest(str(file_path), catalog_id=catalog_id)
                        docs.append(doc)
                    except Exception as e:
                        logger.warning(f"Error ingesting {file_path}: {e}")

        return docs

    def _insert_document(self, doc: DocumentRecord):
        """Insert document into database."""
        self.db.execute(
            """INSERT INTO documents
               (doc_id, file_path, title, file_type, content_hash, size_bytes,
                created_at, modified_at, ingested_at, tags, metadata, catalog_id,
                folder_path, language, word_count, page_count, summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (doc.doc_id, doc.file_path, doc.title, doc.file_type, doc.content_hash,
             doc.size_bytes, doc.created_at, doc.modified_at, doc.ingested_at,
             json.dumps(doc.tags), json.dumps(doc.metadata), doc.catalog_id,
             doc.folder_path, doc.language, doc.word_count, doc.page_count, doc.summary)
        )

    def _update_document(self, doc: DocumentRecord):
        """Update existing document."""
        self.db.execute(
            """UPDATE documents SET
               title=?, file_type=?, content_hash=?, size_bytes=?,
               modified_at=?, ingested_at=?, tags=?, metadata=?,
               catalog_id=?, folder_path=?, word_count=?, page_count=?, summary=?
               WHERE doc_id=?""",
            (doc.title, doc.file_type, doc.content_hash, doc.size_bytes,
             doc.modified_at, doc.ingested_at, json.dumps(doc.tags),
             json.dumps(doc.metadata), doc.catalog_id, doc.folder_path,
             doc.word_count, doc.page_count, doc.summary, doc.doc_id)
        )

    def _insert_chunk(self, chunk: Chunk):
        """Insert chunk into database."""
        self.db.execute(
            """INSERT INTO chunks
               (chunk_id, doc_id, content, chunk_index, start_line, end_line,
                start_page, end_page, section_title, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (chunk.chunk_id, chunk.doc_id, chunk.content, chunk.chunk_index,
             chunk.start_line, chunk.end_line, chunk.start_page, chunk.end_page,
             chunk.section_title, json.dumps(chunk.metadata))
        )

    def get_document(self, doc_id: str) -> Optional[DocumentRecord]:
        """Get a document by ID."""
        row = self.db.fetchone("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        if not row:
            return None
        return self._row_to_document(row)

    def get_document_by_path(self, file_path: str) -> Optional[DocumentRecord]:
        """Get a document by file path."""
        row = self.db.fetchone("SELECT * FROM documents WHERE file_path = ?", (str(Path(file_path).resolve()),))
        if not row:
            return None
        return self._row_to_document(row)

    def _row_to_document(self, row: sqlite3.Row) -> DocumentRecord:
        """Convert database row to DocumentRecord."""
        return DocumentRecord(
            doc_id=row['doc_id'],
            file_path=row['file_path'],
            title=row['title'],
            file_type=row['file_type'],
            content_hash=row['content_hash'],
            size_bytes=row['size_bytes'],
            created_at=row['created_at'],
            modified_at=row['modified_at'],
            ingested_at=row['ingested_at'],
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}'),
            catalog_id=row['catalog_id'],
            folder_path=row['folder_path'],
            language=row['language'],
            word_count=row['word_count'],
            page_count=row['page_count'],
            summary=row['summary'],
        )

    def list_documents(
        self,
        catalog_id: Optional[str] = None,
        file_type: Optional[str] = None,
        folder_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DocumentRecord]:
        """List documents with optional filters."""
        conditions = []
        params = []

        if catalog_id:
            conditions.append("catalog_id = ?")
            params.append(catalog_id)
        if file_type:
            conditions.append("file_type = ?")
            params.append(file_type)
        if folder_path:
            conditions.append("folder_path LIKE ?")
            params.append(f"{folder_path}%")
        if tags:
            for tag in tags:
                conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.extend([limit, offset])

        rows = self.db.fetchall(
            f"SELECT * FROM documents {where} ORDER BY ingested_at DESC LIMIT ? OFFSET ?",
            tuple(params)
        )
        return [self._row_to_document(row) for row in rows]

    def delete_document(self, doc_id: str):
        """Delete a document and all its chunks."""
        self.db.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        self.db.commit()

    def update_document_tags(self, doc_id: str, tags: List[str]):
        """Update tags for a document."""
        self.db.execute(
            "UPDATE documents SET tags = ? WHERE doc_id = ?",
            (json.dumps(tags), doc_id)
        )
        self.db.commit()

    def update_document_summary(self, doc_id: str, summary: str):
        """Update summary for a document."""
        self.db.execute(
            "UPDATE documents SET summary = ? WHERE doc_id = ?",
            (summary, doc_id)
        )
        self.db.commit()

    # ── Search ───────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        limit: int = 10,
        use_semantic: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        source_quota: Optional[Dict[str, int]] = None,
    ) -> List[SearchResult]:
        """Search the knowledge base."""
        return self.search_engine.search(
            query=query,
            limit=limit,
            use_semantic=use_semantic,
            source_quota=source_quota,
            filters=filters,
        )

    # ── Catalogs ─────────────────────────────────────────────────────────────

    def create_catalog(self, name: str, description: str = "", tags: Optional[List[str]] = None) -> Catalog:
        """Create a new catalog."""
        catalog = Catalog(
            catalog_id=str(uuid.uuid4()),
            name=name,
            description=description,
            created_at=datetime.datetime.utcnow().isoformat(),
            tags=tags or [],
        )
        self.db.execute(
            "INSERT INTO catalogs (catalog_id, name, description, created_at, tags, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (catalog.catalog_id, catalog.name, catalog.description, catalog.created_at,
             json.dumps(catalog.tags), json.dumps(catalog.metadata))
        )
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
            description=row['description'],
            created_at=row['created_at'],
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}'),
        )

    def list_catalogs(self) -> List[Catalog]:
        """List all catalogs."""
        rows = self.db.fetchall("SELECT * FROM catalogs ORDER BY name")
        return [Catalog(
            catalog_id=row['catalog_id'],
            name=row['name'],
            description=row['description'],
            created_at=row['created_at'],
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}'),
        ) for row in rows]

    def delete_catalog(self, catalog_id: str):
        """Delete a catalog (documents remain)."""
        self.db.execute("UPDATE documents SET catalog_id = NULL WHERE catalog_id = ?", (catalog_id,))
        self.db.execute("DELETE FROM catalogs WHERE catalog_id = ?", (catalog_id,))
        self.db.commit()

    # ── Tags ─────────────────────────────────────────────────────────────────

    def create_tag(self, name: str, color: str = "#888888", description: str = "",
                   parent_tag_id: Optional[str] = None) -> Tag:
        """Create a new tag."""
        tag = Tag(
            tag_id=str(uuid.uuid4()),
            name=name,
            color=color,
            description=description,
            parent_tag_id=parent_tag_id,
        )
        self.db.execute(
            "INSERT INTO tags (tag_id, name, color, description, parent_tag_id) VALUES (?, ?, ?, ?, ?)",
            (tag.tag_id, tag.name, tag.color, tag.description, tag.parent_tag_id)
        )
        self.db.commit()
        return tag

    def list_tags(self) -> List[Tag]:
        """List all tags."""
        rows = self.db.fetchall("SELECT * FROM tags ORDER BY name")
        return [Tag(
            tag_id=row['tag_id'],
            name=row['name'],
            color=row['color'],
            description=row['description'],
            parent_tag_id=row['parent_tag_id'],
        ) for row in rows]

    def get_tag_by_name(self, name: str) -> Optional[Tag]:
        """Get a tag by name."""
        row = self.db.fetchone("SELECT * FROM tags WHERE name = ?", (name,))
        if not row:
            return None
        return Tag(
            tag_id=row['tag_id'],
            name=row['name'],
            color=row['color'],
            description=row['description'],
            parent_tag_id=row['parent_tag_id'],
        )

    # ── Views ────────────────────────────────────────────────────────────────

    def create_view(self, name: str, query: str, filters: Optional[Dict] = None,
                    description: str = "") -> View:
        """Create a saved view."""
        view = View(
            view_id=str(uuid.uuid4()),
            name=name,
            query=query,
            filters=filters or {},
            created_at=datetime.datetime.utcnow().isoformat(),
            description=description,
        )
        self.db.execute(
            "INSERT INTO views (view_id, name, query, filters, created_at, description) VALUES (?, ?, ?, ?, ?, ?)",
            (view.view_id, view.name, view.query, json.dumps(view.filters),
             view.created_at, view.description)
        )
        self.db.commit()
        return view

    def execute_view(self, view_id: str) -> List[SearchResult]:
        """Execute a saved view."""
        row = self.db.fetchone("SELECT * FROM views WHERE view_id = ?", (view_id,))
        if not row:
            return []
        filters = json.loads(row['filters'] or '{}')
        return self.search(query=row['query'], filters=filters)

    def list_views(self) -> List[View]:
        """List all views."""
        rows = self.db.fetchall("SELECT * FROM views ORDER BY name")
        return [View(
            view_id=row['view_id'],
            name=row['name'],
            query=row['query'],
            filters=json.loads(row['filters'] or '{}'),
            created_at=row['created_at'],
            description=row['description'],
        ) for row in rows]

    # ── Relations ────────────────────────────────────────────────────────────

    def get_relations(self, doc_id: str, relation_type: Optional[str] = None) -> List[Relation]:
        """Get relations for a document."""
        if relation_type:
            rows = self.db.fetchall(
                "SELECT * FROM relations WHERE (source_doc_id = ? OR target_doc_id = ?) AND relation_type = ?",
                (doc_id, doc_id, relation_type)
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM relations WHERE source_doc_id = ? OR target_doc_id = ?",
                (doc_id, doc_id)
            )

        return [Relation(
            relation_id=row['relation_id'],
            source_doc_id=row['source_doc_id'],
            target_doc_id=row['target_doc_id'],
            relation_type=row['relation_type'],
            confidence=row['confidence'],
            evidence=row['evidence'],
            created_at=row['created_at'],
            auto_detected=bool(row['auto_detected']),
        ) for row in rows]

    def add_relation(self, source_doc_id: str, target_doc_id: str,
                     relation_type: str, confidence: float = 1.0,
                     evidence: str = "") -> Relation:
        """Manually add a relation between documents."""
        relation = Relation(
            relation_id=str(uuid.uuid4()),
            source_doc_id=source_doc_id,
            target_doc_id=target_doc_id,
            relation_type=relation_type,
            confidence=confidence,
            evidence=evidence,
            created_at=datetime.datetime.utcnow().isoformat(),
            auto_detected=False,
        )
        self.relation_miner.store_relations([relation])
        return relation

    # ── Journal ──────────────────────────────────────────────────────────────

    def add_journal_entry(
        self,
        content: str,
        session_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        linked_doc_ids: Optional[List[str]] = None,
        entry_type: str = "note",
    ) -> JournalEntry:
        """Add a journal entry."""
        entry = JournalEntry(
            entry_id=str(uuid.uuid4()),
            session_id=session_id or str(uuid.uuid4()),
            content=content,
            created_at=datetime.datetime.utcnow().isoformat(),
            tags=tags or [],
            linked_doc_ids=linked_doc_ids or [],
            entry_type=entry_type,
        )
        self.db.execute(
            """INSERT INTO journal_entries
               (entry_id, session_id, content, created_at, tags, linked_doc_ids, entry_type)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (entry.entry_id, entry.session_id, entry.content, entry.created_at,
             json.dumps(entry.tags), json.dumps(entry.linked_doc_ids), entry.entry_type)
        )
        self.db.commit()
        return entry

    def get_journal_entries(
        self,
        session_id: Optional[str] = None,
        entry_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[JournalEntry]:
        """Get journal entries."""
        conditions = []
        params = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if entry_type:
            conditions.append("entry_type = ?")
            params.append(entry_type)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        rows = self.db.fetchall(
            f"SELECT * FROM journal_entries {where} ORDER BY created_at DESC LIMIT ?",
            tuple(params)
        )

        return [JournalEntry(
            entry_id=row['entry_id'],
            session_id=row['session_id'],
            content=row['content'],
            created_at=row['created_at'],
            tags=json.loads(row['tags'] or '[]'),
            linked_doc_ids=json.loads(row['linked_doc_ids'] or '[]'),
            entry_type=row['entry_type'],
        ) for row in rows]

    # ── Investigation Notes ──────────────────────────────────────────────────

    def save_investigation_note(self, note: InvestigationNote):
        """Save an investigation note."""
        citations_data = [asdict(c) for c in note.citations]
        self.db.execute(
            """INSERT INTO investigation_notes
               (note_id, session_id, query, answer, citations, created_at, tags, metadata, follow_up_questions)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (note.note_id, note.session_id, note.query, note.answer,
             json.dumps(citations_data), note.created_at,
             json.dumps(note.tags), json.dumps(note.metadata),
             json.dumps(note.follow_up_questions))
        )
        self.db.commit()

    def get_investigation_notes(
        self,
        session_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[InvestigationNote]:
        """Get investigation notes."""
        if session_id:
            rows = self.db.fetchall(
                "SELECT * FROM investigation_notes WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit)
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM investigation_notes ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )

        notes = []
        for row in rows:
            citations_data = json.loads(row['citations'] or '[]')
            citations = [Citation(**c) for c in citations_data]
            notes.append(InvestigationNote(
                note_id=row['note_id'],
                session_id=row['session_id'],
                query=row['query'],
                answer=row['answer'],
                citations=citations,
                created_at=row['created_at'],
                tags=json.loads(row['tags'] or '[]'),
                metadata=json.loads(row['metadata'] or '{}'),
                follow_up_questions=json.loads(row['follow_up_questions'] or '[]'),
            ))
        return notes

    def search_investigation_notes(self, query: str, limit: int = 20) -> List[InvestigationNote]:
        """Search investigation notes by query text."""
        rows = self.db.fetchall(
            """SELECT * FROM investigation_notes
               WHERE LOWER(query) LIKE ? OR LOWER(answer) LIKE ?
               ORDER BY created_at DESC LIMIT ?""",
            (f'%{query.lower()}%', f'%{query.lower()}%', limit)
        )

        notes = []
        for row in rows:
            citations_data = json.loads(row['citations'] or '[]')
            citations = [Citation(**c) for c in citations_data]
            notes.append(InvestigationNote(
                note_id=row['note_id'],
                session_id=row['session_id'],
                query=row['query'],
                answer=row['answer'],
                citations=citations,
                created_at=row['created_at'],
                tags=json.loads(row['tags'] or '[]'),
                metadata=json.loads(row['metadata'] or '{}'),
                follow_up_questions=json.loads(row['follow_up_questions'] or '[]'),
            ))
        return notes

    # ── Statistics ───────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        doc_count = self.db.fetchone("SELECT COUNT(*) as n FROM documents")['n']
        chunk_count = self.db.fetchone("SELECT COUNT(*) as n FROM chunks")['n']
        catalog_count = self.db.fetchone("SELECT COUNT(*) as n FROM catalogs")['n']
        tag_count = self.db.fetchone("SELECT COUNT(*) as n FROM tags")['n']
        relation_count = self.db.fetchone("SELECT COUNT(*) as n FROM relations")['n']
        note_count = self.db.fetchone("SELECT COUNT(*) as n FROM investigation_notes")['n']
        journal_count = self.db.fetchone("SELECT COUNT(*) as n FROM journal_entries")['n']

        type_rows = self.db.fetchall(
            "SELECT file_type, COUNT(*) as n FROM documents GROUP BY file_type ORDER BY n DESC"
        )
        by_type = {row['file_type']: row['n'] for row in type_rows}

        total_words = self.db.fetchone("SELECT SUM(word_count) as n FROM documents")['n'] or 0
        total_size = self.db.fetchone("SELECT SUM(size_bytes) as n FROM documents")['n'] or 0

        return {
            'documents': doc_count,
            'chunks': chunk_count,
            'catalogs': catalog_count,
            'tags': tag_count,
            'relations': relation_count,
            'investigation_notes': note_count,
            'journal_entries': journal_count,
            'by_file_type': by_type,
            'total_words': total_words,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
        }

    def rebuild_fts_index(self):
        """Rebuild the full-text search index."""
        logger.info("Rebuilding FTS index...")
        self.db.execute("DELETE FROM chunks_fts")
        chunks = self.db.fetchall("SELECT * FROM chunks")
        for row in chunks:
            chunk = Chunk(
                chunk_id=row['chunk_id'],
                doc_id=row['doc_id'],
                content=row['content'],
                chunk_index=row['chunk_index'],
                start_line=row['start_line'],
                end_line=row['end_line'],
                start_page=row['start_page'],
                end_page=row['end_page'],
                section_title=row['section_title'],
            )
            self.lexical.index_chunk(chunk)
        self.db.commit()
        logger.info(f"FTS index rebuilt with {len(chunks)} chunks")

    def sync_directory(self, dir_path: str) -> Dict[str, int]:
        """Sync a directory, ingesting new/modified files."""
        path = Path(dir_path)
        stats = {'new': 0, 'updated': 0, 'unchanged': 0, 'errors': 0}

        for file_path in path.rglob('*'):
            if not file_path.is_file():
                continue
            ext = file_path.suffix.lower()
            if ext not in self.ingester.SUPPORTED_EXTENSIONS:
                continue

            try:
                existing = self.db.fetchone(
                    "SELECT doc_id, content_hash FROM documents WHERE file_path = ?",
                    (str(file_path.resolve()),)
                )
                new_hash = self.ingester._compute_hash(file_path)

                if not existing:
                    self.ingest(str(file_path))
                    stats['new'] += 1
                elif existing['content_hash'] != new_hash:
                    self.ingest(str(file_path))
                    stats['updated'] += 1
                else:
                    stats['unchanged'] += 1
            except Exception as e:
                logger.warning(f"Sync error for {file_path}: {e}")
                stats['errors'] += 1

        return stats


# ─────────────────────────────────────────────────────────────────────────────
# Marginalia Application
# ─────────────────────────────────────────────────────────────────────────────

class Marginalia:
    """Main application class for Marginalia."""

    def __init__(
        self,
        base_path: str,
        llm_provider: str = "anthropic",
        llm_model: Optional[str] = None,
        db_path: Optional[str] = None,
    ):
        self.base_path = Path(base_path)
        self.kb = KnowledgeBase(str(self.base_path), db_path=db_path)
        self.llm = LLMClient(provider=llm_provider, model=llm_model)
        self.agent = ResearchAgent(
            knowledge_base=self.kb,
            llm_client=self.llm,
            reader=self.kb.reader,
        )

    # ── High-level API ───────────────────────────────────────────────────────

    def ingest(self, path: str, **kwargs) -> Union[DocumentRecord, List[DocumentRecord]]:
        """Ingest a file or directory."""
        p = Path(path)
        if p.is_dir():
            return self.kb.ingest_directory(str(p), **kwargs)
        else:
            return self.kb.ingest(str(p), **kwargs)

    def ask(
        self,
        query: str,
        save_note: bool = True,
        max_sources: int = 5,
        use_semantic: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ) -> InvestigationNote:
        """Ask a question and get a cited answer."""
        self.agent.session_id = str(uuid.uuid4())
        note = self.agent.investigate(
            query=query,
            save_note=save_note,
            max_sources=max_sources,
            use_semantic=use_semantic,
            filters=filters,
        )
        return note

    def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search the knowledge base."""
        return self.kb.search(query, **kwargs)

    def report(self, topic: str, sections: Optional[List[str]] = None) -> str:
        """Generate a report on a topic."""
        return self.agent.generate_report(topic, sections=sections)

    def stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        return self.kb.get_stats()

    def sync(self, dir_path: Optional[str] = None) -> Dict[str, int]:
        """Sync a directory with the knowledge base."""
        return self.kb.sync_directory(dir_path or str(self.base_path))

    # ── Catalog Management ───────────────────────────────────────────────────

    def create_catalog(self, name: str, description: str = "") -> Catalog:
        return self.kb.create_catalog(name, description)

    def list_catalogs(self) -> List[Catalog]:
        return self.kb.list_catalogs()

    # ── Tag Management ───────────────────────────────────────────────────────

    def create_tag(self, name: str, color: str = "#888888") -> Tag:
        return self.kb.create_tag(name, color)

    def list_tags(self) -> List[Tag]:
        return self.kb.list_tags()

    def tag_document(self, doc_id: str, tags: List[str]):
        """Add tags to a document."""
        doc = self.kb.get_document(doc_id)
        if doc:
            existing_tags = set(doc.tags)
            existing_tags.update(tags)
            self.kb.update_document_tags(doc_id, list(existing_tags))

    # ── View Management ──────────────────────────────────────────────────────

    def create_view(self, name: str, query: str, filters: Optional[Dict] = None) -> View:
        return self.kb.create_view(name, query, filters)

    def list_views(self) -> List[View]:
        return self.kb.list_views()

    def execute_view(self, view_name: str) -> List[SearchResult]:
        """Execute a view by name."""
        rows = self.kb.db.fetchall("SELECT view_id FROM views WHERE name = ?", (view_name,))
        if not rows:
            return []
        return self.kb.execute_view(rows[0]['view_id'])

    # ── Journal ──────────────────────────────────────────────────────────────

    def journal(self, content: str, tags: Optional[List[str]] = None,
                entry_type: str = "note") -> JournalEntry:
        """Add a journal entry."""
        return self.kb.add_journal_entry(
            content=content,
            session_id=self.agent.session_id,
            tags=tags,
            entry_type=entry_type,
        )

    def get_journal(self, limit: int = 20) -> List[JournalEntry]:
        """Get recent journal entries."""
        return self.kb.get_journal_entries(limit=limit)

    # ── Investigation Notes ──────────────────────────────────────────────────

    def get_notes(self, limit: int = 20) -> List[InvestigationNote]:
        """Get recent investigation notes."""
        return self.kb.get_investigation_notes(limit=limit)

    def search_notes(self, query: str) -> List[InvestigationNote]:
        """Search investigation notes."""
        return self.kb.search_investigation_notes(query)

    # ── Relations ────────────────────────────────────────────────────────────

    def get_relations(self, doc_id: str) -> List[Relation]:
        """Get relations for a document."""
        return self.kb.get_relations(doc_id)

    def add_relation(self, source_doc_id: str, target_doc_id: str,
                     relation_type: str, evidence: str = "") -> Relation:
        """Add a relation between documents."""
        return self.kb.add_relation(source_doc_id, target_doc_id, relation_type, evidence=evidence)

    # ── Document Access ──────────────────────────────────────────────────────

    def list_documents(self, **kwargs) -> List[DocumentRecord]:
        """List documents."""
        return self.kb.list_documents(**kwargs)

    def get_document(self, doc_id: str) -> Optional[DocumentRecord]:
        """Get a document by ID."""
        return self.kb.get_document(doc_id)

    def read_document(self, doc_id: str, start_line: Optional[int] = None,
                      end_line: Optional[int] = None) -> str:
        """Read a document's content."""
        doc = self.kb.get_document(doc_id)
        if not doc:
            return "[Document not found]"

        if start_line and end_line:
            return self.kb.reader.read_lines(doc.file_path, start_line, end_line)
        else:
            try:
                content, _, _ = self.kb.ingester._extract_content(
                    Path(doc.file_path),
                    doc.file_type
                )
                return content
            except Exception as e:
                return f"[Error reading document: {e}]"

    def rebuild_index(self):
        """Rebuild the search index."""
        self.kb.rebuild_fts_index()

    def export_notes(self, output_path: str, format: str = "markdown"):
        """Export investigation notes to a file."""
        notes = self.kb.get_investigation_notes(limit=10000)
        output = Path(output_path)

        if format == "markdown":
            lines = ["# Marginalia Investigation Notes\n"]
            for note in notes:
                lines.append(f"## {note.query}")
                lines.append(f"*{note.created_at}*\n")
                lines.append(note.answer)
                if note.citations:
                    lines.append("\n### Sources")
                    for cit in note.citations:
                        lines.append(f"- **{cit.title}** ({cit.location}): {cit.quote[:100]}...")
                if note.follow_up_questions:
                    lines.append("\n### Follow-up Questions")
                    for q in note.follow_up_questions:
                        lines.append(f"- {q}")
                lines.append("\n---\n")
            output.write_text("\n".join(lines), encoding='utf-8')

        elif format == "json":
            data = [note.to_dict() for note in notes]
            output.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

        logger.info(f"Exported {len(notes)} notes to {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI Interface
# ─────────────────────────────────────────────────────────────────────────────

class CLI:
    """Command-line interface for Marginalia."""

    def __init__(self, marginalia: Marginalia):
        self.m = marginalia

    def run_interactive(self):
        """Run interactive CLI session."""
        print("=" * 60)
        print("Marginalia - Personal Knowledge Management System")
        print("=" * 60)
        print(f"Knowledge base: {self.m.base_path}")

        stats = self.m.stats()
        print(f"Documents: {stats['documents']} | Chunks: {stats['chunks']} | Notes: {stats['investigation_notes']}")
        print("\nCommands: ask, search, ingest, stats, notes, journal, catalogs, tags, views, help, quit")
        print()

        while True:
            try:
                cmd = input("marginalia> ").strip()
                if not cmd:
                    continue

                parts = cmd.split(None, 1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""

                if command in ('quit', 'exit', 'q'):
                    print("Goodbye!")
                    break
                elif command == 'help':
                    self._show_help()
                elif command == 'ask':
                    self._cmd_ask(args)
                elif command == 'search':
                    self._cmd_search(args)
                elif command == 'ingest':
                    self._cmd_ingest(args)
                elif command == 'stats':
                    self._cmd_stats()
                elif command == 'notes':
                    self._cmd_notes(args)
                elif command == 'journal':
                    self._cmd_journal(args)
                elif command == 'catalogs':
                    self._cmd_catalogs(args)
                elif command == 'tags':
                    self._cmd_tags(args)
                elif command == 'views':
                    self._cmd_views(args)
                elif command == 'docs':
                    self._cmd_docs(args)
                elif command == 'sync':
                    self._cmd_sync(args)
                elif command == 'report':
                    self._cmd_report(args)
                else:
                    print(f"Unknown command: {command}. Type 'help' for help.")

            except KeyboardInterrupt:
                print("\nInterrupted. Type 'quit' to exit.")
            except EOFError:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
                logger.exception(e)

    def _show_help(self):
        help_text = """
Commands:
  ask <query>          - Ask a question and get a cited answer
  search <query>       - Search the knowledge base
  ingest <path>        - Ingest a file or directory
  sync [path]          - Sync directory with knowledge base
  stats                - Show knowledge base statistics
  docs [filter]        - List documents
  notes [query]        - List or search investigation notes
  journal <text>       - Add a journal entry
  catalogs             - List catalogs
  tags                 - List tags
  views                - List saved views
  report <topic>       - Generate a report on a topic
  help                 - Show this help
  quit                 - Exit
"""
        print(help_text)

    def _cmd_ask(self, query: str):
        if not query:
            query = input("Query: ").strip()
        if not query:
            return

        print(f"\nSearching for: {query}")
        note = self.m.ask(query)
        print("\n" + "=" * 60)
        print(note.answer)
        print("=" * 60)
        if note.citations:
            print(f"\nSources ({len(note.citations)}):")
            for cit in note.citations:
                print(f"  - {cit.title} ({cit.location})")
        if note.follow_up_questions:
            print("\nFollow-up questions:")
            for q in note.follow_up_questions:
                print(f"  ? {q}")
        print()

    def _cmd_search(self, query: str):
        if not query:
            query = input("Search query: ").strip()
        if not query:
            return

        results = self.m.search(query, limit=10)
        if not results:
            print("No results found.")
            return

        print(f"\nFound {len(results)} results:\n")
        for r in results:
            print(f"[{r.rank}] {r.title} (score: {r.score:.3f})")
            print(f"    File: {r.file_path}")
            if r.section_title:
                print(f"    Section: {r.section_title}")
            if r.start_page:
                print(f"    Page: {r.start_page}")
            elif r.start_line:
                print(f"    Lines: {r.start_line}-{r.end_line}")
            if r.highlights:
                print(f"    > {r.highlights[0][:100]}")
            print()

    def _cmd_ingest(self, path: str):
        if not path:
            path = input("Path to ingest: ").strip()
        if not path:
            return

        print(f"Ingesting: {path}")
        result = self.m.ingest(path)
        if isinstance(result, list):
            print(f"Ingested {len(result)} documents.")
        else:
            print(f"Ingested: {result.title} ({result.file_type}, {result.word_count} words)")

    def _cmd_stats(self):
        stats = self.m.stats()
        print("\nKnowledge Base Statistics:")
        print(f"  Documents:           {stats['documents']}")
        print(f"  Chunks:              {stats['chunks']}")
        print(f"  Catalogs:            {stats['catalogs']}")
        print(f"  Tags:                {stats['tags']}")
        print(f"  Relations:           {stats['relations']}")
        print(f"  Investigation Notes: {stats['investigation_notes']}")
        print(f"  Journal Entries:     {stats['journal_entries']}")
        print(f"  Total Words:         {stats['total_words']:,}")
        print(f"  Total Size:          {stats['total_size_mb']} MB")
        if stats['by_file_type']:
            print("\n  By File Type:")
            for ft, count in stats['by_file_type'].items():
                print(f"    {ft:15} {count}")
        print()

    def _cmd_notes(self, query: str):
        if query:
            notes = self.m.search_notes(query)
            print(f"\nNotes matching '{query}':")
        else:
            notes = self.m.get_notes(limit=10)
            print("\nRecent Investigation Notes:")

        if not notes:
            print("  No notes found.")
            return

        for note in notes:
            print(f"\n[{note.created_at[:10]}] {note.query[:80]}")
            answer_preview = note.answer[:200].replace('\n', ' ')
            print(f"  {answer_preview}...")
            if note.citations:
                print(f"  Sources: {', '.join(c.title for c in note.citations[:3])}")
        print()

    def _cmd_journal(self, content: str):
        if not content:
            content = input("Journal entry: ").strip()
        if not content:
            return

        entry = self.m.journal(content)
        print(f"Journal entry saved: {entry.entry_id[:8]}...")

    def _cmd_catalogs(self, args: str):
        catalogs = self.m.list_catalogs()
        if not catalogs:
            print("No catalogs found.")
            return
        print("\nCatalogs:")
        for cat in catalogs:
            print(f"  [{cat.catalog_id[:8]}] {cat.name}: {cat.description}")
        print()

    def _cmd_tags(self, args: str):
        tags = self.m.list_tags()
        if not tags:
            print("No tags found.")
            return
        print("\nTags:")
        for tag in tags:
            print(f"  {tag.name} ({tag.color}): {tag.description}")
        print()

    def _cmd_views(self, args: str):
        views = self.m.list_views()
        if not views:
            print("No views found.")
            return
        print("\nSaved Views:")
        for view in views:
            print(f"  [{view.view_id[:8]}] {view.name}: {view.query}")
        print()

    def _cmd_docs(self, args: str):
        docs = self.m.list_documents(limit=20)
        if not docs:
            print("No documents found.")
            return
        print(f"\nDocuments ({len(docs)}):")
        for doc in docs:
            print(f"  [{doc.doc_id[:8]}] {doc.title} ({doc.file_type}, {doc.word_count} words)")
            print(f"           {doc.file_path}")
        print()

    def _cmd_sync(self, path: str):
        sync_path = path or str(self.m.base_path)
        print(f"Syncing: {sync_path}")
        stats = self.m.sync(sync_path)
        print(f"Sync complete: {stats['new']} new, {stats['updated']} updated, "
              f"{stats['unchanged']} unchanged, {stats['errors']} errors")

    def _cmd_report(self, topic: str):
        if not topic:
            topic = input("Report topic: ").strip()
        if not topic:
            return

        print(f"\nGenerating report on: {topic}")
        report = self.m.report(topic)
        print("\n" + report)


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def create_marginalia(
    base_path: str = ".",
    llm_provider: str = "anthropic",
    llm_model: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Marginalia:
    """Create a Marginalia instance."""
    return Marginalia(
        base_path=base_path,
        llm_provider=llm_provider,
        llm_model=llm_model,
        db_path=db_path,
    )


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Marginalia - Personal Knowledge Management System"
    )
    parser.add_argument('--path', default='.', help='Knowledge base path')
    parser.add_argument('--db', default=None, help='Database path')
    parser.add_argument('--provider', default='anthropic', choices=['anthropic', 'openai'],
                        help='LLM provider')
    parser.add_argument('--model', default=None, help='LLM model name')
    parser.add_argument('--ingest', default=None, help='Ingest a file or directory')
    parser.add_argument('--ask', default=None, help='Ask a question')
    parser.add_argument('--search', default=None, help='Search the knowledge base')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--sync', action='store_true', help='Sync knowledge base')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')
    parser.add_argument('--report', default=None, help='Generate a report on a topic')

    args = parser.parse_args()

    m = create_marginalia(
        base_path=args.path,
        llm_provider=args.provider,
        llm_model=args.model,
        db_path=args.db,
    )

    if args.ingest:
        result = m.ingest(args.ingest)
        if isinstance(result, list):
            print(f"Ingested {len(result)} documents.")
        else:
            print(f"Ingested: {result.title}")

    elif args.ask:
        note = m.ask(args.ask)
        print(note.answer)

    elif args.search:
        results = m.search(args.search)
        for r in results:
            print(f"[{r.rank}] {r.title} (score: {r.score:.3f})")
            if r.highlights:
                print(f"    > {r.highlights[0][:100]}")

    elif args.stats:
        stats = m.stats()
        for k, v in stats.items():
            if not isinstance(v, dict):
                print(f"  {k}: {v}")

    elif args.sync:
        stats = m.sync()
        print(f"Sync: {stats}")

    elif args.report:
        report = m.report(args.report)
        print(report)

    else:
        # Default to interactive mode
        cli = CLI(m)
        cli.run_interactive()


if __name__ == '__main__':
    main()