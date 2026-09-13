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


# ============================================================
# Data Models
# ============================================================

@dataclass
class DocumentRecord:
    """Represents a document in the knowledge base."""
    doc_id: str
    file_path: str
    title: str
    doc_type: str
    content_hash: str
    size_bytes: int
    created_at: str
    updated_at: str
    ingested_at: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    catalog_id: Optional[str] = None
    folder_path: str = ""
    language: str = "en"
    word_count: int = 0
    page_count: int = 0
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
    section: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """A search result with relevance scoring."""
    chunk: Chunk
    doc: DocumentRecord
    score: float
    match_type: str  # 'lexical', 'semantic', 'hybrid'
    snippet: str = ""
    highlights: List[str] = field(default_factory=list)


@dataclass
class Citation:
    """A citation reference."""
    doc_id: str
    file_path: str
    title: str
    chunk_id: str
    page_number: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    section: Optional[str] = None
    quote: str = ""


@dataclass
class InvestigationNote:
    """A durable investigation note for future recall."""
    note_id: str
    query: str
    answer: str
    citations: List[Citation]
    created_at: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    follow_up_questions: List[str] = field(default_factory=list)


@dataclass
class Catalog:
    """A catalog grouping related documents."""
    catalog_id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class View:
    """A saved search/filter view."""
    view_id: str
    name: str
    description: str
    query: str
    filters: Dict[str, Any]
    created_at: str
    updated_at: str


@dataclass
class Relation:
    """A relation between two documents."""
    relation_id: str
    source_doc_id: str
    target_doc_id: str
    relation_type: str  # 'cites', 'related', 'contradicts', 'extends', 'summarizes'
    confidence: float
    evidence: str
    created_at: str
    auto_detected: bool = True


@dataclass
class JournalEntry:
    """A journal entry for tracking research activity."""
    entry_id: str
    content: str
    created_at: str
    tags: List[str] = field(default_factory=list)
    linked_docs: List[str] = field(default_factory=list)
    linked_notes: List[str] = field(default_factory=list)


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
                doc_type TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                catalog_id TEXT,
                folder_path TEXT DEFAULT '',
                language TEXT DEFAULT 'en',
                word_count INTEGER DEFAULT 0,
                page_count INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                start_offset INTEGER NOT NULL,
                end_offset INTEGER NOT NULL,
                page_number INTEGER,
                line_start INTEGER,
                line_end INTEGER,
                section TEXT,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                doc_id UNINDEXED,
                content,
                section,
                tokenize='porter unicode61'
            );

            CREATE TABLE IF NOT EXISTS catalogs (
                catalog_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS views (
                view_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                query TEXT NOT NULL,
                filters TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
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
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                linked_docs TEXT DEFAULT '[]',
                linked_notes TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS investigation_notes (
                note_id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                answer TEXT NOT NULL,
                citations TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                follow_up_questions TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,
                model TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tags (
                tag_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                color TEXT DEFAULT '#888888',
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
            CREATE INDEX IF NOT EXISTS idx_documents_catalog ON documents(catalog_id);
            CREATE INDEX IF NOT EXISTS idx_documents_folder ON documents(folder_path);
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

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()


# ============================================================
# Document Ingestion
# ============================================================

class TextExtractor:
    """Extracts text content from various file types."""

    def extract(self, file_path: str) -> Dict[str, Any]:
        """Extract text and metadata from a file."""
        path = Path(file_path)
        suffix = path.suffix.lower()
        mime_type, _ = mimetypes.guess_type(file_path)

        extractors = {
            '.txt': self._extract_text,
            '.md': self._extract_markdown,
            '.markdown': self._extract_markdown,
            '.pdf': self._extract_pdf,
            '.docx': self._extract_docx,
            '.doc': self._extract_docx,
            '.xlsx': self._extract_spreadsheet,
            '.xls': self._extract_spreadsheet,
            '.csv': self._extract_csv,
            '.log': self._extract_log,
            '.zip': self._extract_zip,
            '.tar': self._extract_tar,
            '.gz': self._extract_tar,
            '.bz2': self._extract_tar,
            '.png': self._extract_image,
            '.jpg': self._extract_image,
            '.jpeg': self._extract_image,
            '.gif': self._extract_image,
            '.bmp': self._extract_image,
            '.tiff': self._extract_image,
            '.json': self._extract_json,
            '.xml': self._extract_xml,
            '.html': self._extract_html,
            '.htm': self._extract_html,
            '.rst': self._extract_text,
            '.py': self._extract_code,
            '.js': self._extract_code,
            '.ts': self._extract_code,
            '.java': self._extract_code,
            '.c': self._extract_code,
            '.cpp': self._extract_code,
            '.h': self._extract_code,
            '.go': self._extract_code,
            '.rs': self._extract_code,
            '.rb': self._extract_code,
            '.sh': self._extract_code,
            '.yaml': self._extract_text,
            '.yml': self._extract_text,
            '.toml': self._extract_text,
            '.ini': self._extract_text,
            '.cfg': self._extract_text,
        }

        extractor = extractors.get(suffix, self._extract_text)
        try:
            result = extractor(file_path)
            result['doc_type'] = self._determine_doc_type(suffix, mime_type)
            return result
        except Exception as e:
            logger.warning(f"Extraction failed for {file_path}: {e}")
            return {
                'text': '',
                'pages': [],
                'metadata': {'error': str(e)},
                'doc_type': 'unknown',
                'word_count': 0,
                'page_count': 0,
            }

    def _determine_doc_type(self, suffix: str, mime_type: Optional[str]) -> str:
        type_map = {
            '.txt': 'text', '.md': 'markdown', '.markdown': 'markdown',
            '.pdf': 'pdf', '.docx': 'docx', '.doc': 'docx',
            '.xlsx': 'spreadsheet', '.xls': 'spreadsheet', '.csv': 'spreadsheet',
            '.log': 'log', '.zip': 'archive', '.tar': 'archive',
            '.gz': 'archive', '.bz2': 'archive',
            '.png': 'image', '.jpg': 'image', '.jpeg': 'image',
            '.gif': 'image', '.bmp': 'image', '.tiff': 'image',
            '.json': 'json', '.xml': 'xml', '.html': 'html', '.htm': 'html',
            '.py': 'code', '.js': 'code', '.ts': 'code', '.java': 'code',
            '.c': 'code', '.cpp': 'code', '.go': 'code', '.rs': 'code',
            '.rb': 'code', '.sh': 'code',
        }
        return type_map.get(suffix, 'text')

    def _extract_text(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
        except Exception:
            text = ''
        lines = text.splitlines()
        return {
            'text': text,
            'pages': [{'page': 1, 'text': text}],
            'lines': lines,
            'metadata': {},
            'word_count': len(text.split()),
            'page_count': 1,
        }

    def _extract_markdown(self, file_path: str) -> Dict[str, Any]:
        result = self._extract_text(file_path)
        text = result['text']
        # Extract sections from markdown headers
        sections = []
        current_section = None
        current_lines = []
        for line in text.splitlines():
            if line.startswith('#'):
                if current_section is not None:
                    sections.append({'title': current_section, 'content': '\n'.join(current_lines)})
                current_section = line.lstrip('#').strip()
                current_lines = []
            else:
                current_lines.append(line)
        if current_section is not None:
            sections.append({'title': current_section, 'content': '\n'.join(current_lines)})
        result['sections'] = sections
        result['metadata']['sections'] = [s['title'] for s in sections]
        return result

    def _extract_pdf(self, file_path: str) -> Dict[str, Any]:
        if not HAS_PYPDF:
            return self._extract_text(file_path)
        pages = []
        full_text = []
        metadata = {}
        try:
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                if reader.metadata:
                    metadata = {
                        'title': str(reader.metadata.get('/Title', '')),
                        'author': str(reader.metadata.get('/Author', '')),
                        'subject': str(reader.metadata.get('/Subject', '')),
                        'creator': str(reader.metadata.get('/Creator', '')),
                    }
                for i, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text() or ''
                    except Exception:
                        text = ''
                    pages.append({'page': i + 1, 'text': text})
                    full_text.append(text)
        except Exception as e:
            logger.warning(f"PDF extraction error for {file_path}: {e}")
        combined = '\n\n'.join(full_text)
        return {
            'text': combined,
            'pages': pages,
            'metadata': metadata,
            'word_count': len(combined.split()),
            'page_count': len(pages),
        }

    def _extract_docx(self, file_path: str) -> Dict[str, Any]:
        if not HAS_DOCX:
            return self._extract_text(file_path)
        try:
            doc = docx.Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs]
            text = '\n'.join(paragraphs)
            metadata = {}
            try:
                props = doc.core_properties
                metadata = {
                    'title': props.title or '',
                    'author': props.author or '',
                    'subject': props.subject or '',
                    'created': str(props.created) if props.created else '',
                }
            except Exception:
                pass
            return {
                'text': text,
                'pages': [{'page': 1, 'text': text}],
                'paragraphs': paragraphs,
                'metadata': metadata,
                'word_count': len(text.split()),
                'page_count': 1,
            }
        except Exception as e:
            logger.warning(f"DOCX extraction error: {e}")
            return self._extract_text(file_path)

    def _extract_spreadsheet(self, file_path: str) -> Dict[str, Any]:
        if not HAS_OPENPYXL:
            return self._extract_csv(file_path) if file_path.endswith('.csv') else self._extract_text(file_path)
        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheets_text = []
            sheets_data = []
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = []
                for row in ws.iter_rows(values_only=True):
                    row_data = [str(cell) if cell is not None else '' for cell in row]
                    rows.append(row_data)
                sheet_text = f"Sheet: {sheet_name}\n"
                sheet_text += '\n'.join('\t'.join(row) for row in rows)
                sheets_text.append(sheet_text)
                sheets_data.append({'name': sheet_name, 'rows': rows})
            text = '\n\n'.join(sheets_text)
            return {
                'text': text,
                'pages': [{'page': i + 1, 'text': s} for i, s in enumerate(sheets_text)],
                'sheets': sheets_data,
                'metadata': {'sheet_names': wb.sheetnames},
                'word_count': len(text.split()),
                'page_count': len(sheets_text),
            }
        except Exception as e:
            logger.warning(f"Spreadsheet extraction error: {e}")
            return self._extract_text(file_path)

    def _extract_csv(self, file_path: str) -> Dict[str, Any]:
        import csv as csv_module
        try:
            rows = []
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv_module.reader(f)
                for row in reader:
                    rows.append(row)
            text = '\n'.join('\t'.join(row) for row in rows)
            return {
                'text': text,
                'pages': [{'page': 1, 'text': text}],
                'rows': rows,
                'metadata': {'row_count': len(rows), 'col_count': len(rows[0]) if rows else 0},
                'word_count': len(text.split()),
                'page_count': 1,
            }
        except Exception as e:
            logger.warning(f"CSV extraction error: {e}")
            return self._extract_text(file_path)

    def _extract_log(self, file_path: str) -> Dict[str, Any]:
        result = self._extract_text(file_path)
        lines = result.get('lines', [])
        # Try to detect log format
        log_entries = []
        for i, line in enumerate(lines):
            log_entries.append({'line': i + 1, 'content': line})
        result['log_entries'] = log_entries
        result['metadata']['line_count'] = len(lines)
        return result

    def _extract_zip(self, file_path: str) -> Dict[str, Any]:
        members_text = []
        member_list = []
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                for info in zf.infolist():
                    member_list.append(info.filename)
                    if not info.is_dir() and info.file_size < 10 * 1024 * 1024:  # 10MB limit
                        try:
                            with zf.open(info) as mf:
                                content = mf.read().decode('utf-8', errors='replace')
                                members_text.append(f"[{info.filename}]\n{content}")
                        except Exception:
                            members_text.append(f"[{info.filename}] (binary)")
        except Exception as e:
            logger.warning(f"ZIP extraction error: {e}")
        text = '\n\n'.join(members_text)
        return {
            'text': text,
            'pages': [{'page': i + 1, 'text': t} for i, t in enumerate(members_text)],
            'members': member_list,
            'metadata': {'member_count': len(member_list), 'members': member_list},
            'word_count': len(text.split()),
            'page_count': len(members_text),
        }

    def _extract_tar(self, file_path: str) -> Dict[str, Any]:
        members_text = []
        member_list = []
        try:
            with tarfile.open(file_path, 'r:*') as tf:
                for member in tf.getmembers():
                    member_list.append(member.name)
                    if member.isfile() and member.size < 10 * 1024 * 1024:
                        try:
                            f = tf.extractfile(member)
                            if f:
                                content = f.read().decode('utf-8', errors='replace')
                                members_text.append(f"[{member.name}]\n{content}")
                        except Exception:
                            members_text.append(f"[{member.name}] (binary)")
        except Exception as e:
            logger.warning(f"TAR extraction error: {e}")
        text = '\n\n'.join(members_text)
        return {
            'text': text,
            'pages': [{'page': i + 1, 'text': t} for i, t in enumerate(members_text)],
            'members': member_list,
            'metadata': {'member_count': len(member_list), 'members': member_list},
            'word_count': len(text.split()),
            'page_count': len(members_text),
        }

    def _extract_image(self, file_path: str) -> Dict[str, Any]:
        metadata = {}
        if HAS_PIL:
            try:
                with Image.open(file_path) as img:
                    metadata = {
                        'width': img.width,
                        'height': img.height,
                        'mode': img.mode,
                        'format': img.format,
                    }
                    # Try to get EXIF data
                    try:
                        exif = img._getexif()
                        if exif:
                            metadata['exif'] = {str(k): str(v) for k, v in list(exif.items())[:20]}
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Image extraction error: {e}")
        text = f"[Image: {Path(file_path).name}] {metadata}"
        return {
            'text': text,
            'pages': [{'page': 1, 'text': text}],
            'metadata': metadata,
            'word_count': 0,
            'page_count': 1,
        }

    def _extract_json(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                data = json.load(f)
            text = json.dumps(data, indent=2)
            return {
                'text': text,
                'pages': [{'page': 1, 'text': text}],
                'metadata': {'keys': list(data.keys()) if isinstance(data, dict) else []},
                'word_count': len(text.split()),
                'page_count': 1,
            }
        except Exception:
            return self._extract_text(file_path)

    def _extract_xml(self, file_path: str) -> Dict[str, Any]:
        result = self._extract_text(file_path)
        # Strip XML tags for plain text
        text = result['text']
        plain = re.sub(r'<[^>]+>', ' ', text)
        plain = re.sub(r'\s+', ' ', plain).strip()
        result['plain_text'] = plain
        return result

    def _extract_html(self, file_path: str) -> Dict[str, Any]:
        result = self._extract_text(file_path)
        text = result['text']
        # Strip HTML tags
        plain = re.sub(r'<[^>]+>', ' ', text)
        plain = re.sub(r'&[a-zA-Z]+;', ' ', plain)
        plain = re.sub(r'\s+', ' ', plain).strip()
        result['text'] = plain
        result['pages'] = [{'page': 1, 'text': plain}]
        result['word_count'] = len(plain.split())
        return result

    def _extract_code(self, file_path: str) -> Dict[str, Any]:
        result = self._extract_text(file_path)
        text = result['text']
        lines = text.splitlines()
        # Extract function/class definitions
        definitions = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if re.match(r'^(def |class |function |func |fn |pub fn |async fn )', stripped):
                definitions.append({'line': i + 1, 'definition': stripped})
        result['metadata']['definitions'] = definitions
        result['metadata']['line_count'] = len(lines)
        return result


class Chunker:
    """Splits document text into chunks for indexing."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, doc_id: str, extraction: Dict[str, Any]) -> List[Chunk]:
        """Create chunks from extracted document content."""
        doc_type = extraction.get('doc_type', 'text')

        if doc_type == 'pdf' and extraction.get('pages'):
            return self._chunk_by_pages(doc_id, extraction['pages'])
        elif doc_type in ('log',) and extraction.get('lines'):
            return self._chunk_by_lines(doc_id, extraction['lines'])
        elif doc_type == 'spreadsheet' and extraction.get('sheets'):
            return self._chunk_spreadsheet(doc_id, extraction['sheets'])
        elif doc_type in ('archive', 'zip', 'tar') and extraction.get('members'):
            return self._chunk_archive(doc_id, extraction.get('pages', []))
        elif doc_type == 'markdown' and extraction.get('sections'):
            return self._chunk_by_sections(doc_id, extraction['sections'], extraction.get('text', ''))
        else:
            return self._chunk_text(doc_id, extraction.get('text', ''))

    def _chunk_text(self, doc_id: str, text: str) -> List[Chunk]:
        """Split text into overlapping chunks."""
        if not text.strip():
            return []
        words = text.split()
        chunks = []
        i = 0
        chunk_index = 0
        while i < len(words):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)
            start_offset = len(' '.join(words[:i]))
            end_offset = start_offset + len(chunk_text)
            chunks.append(Chunk(
                chunk_id=str(uuid.uuid4()),
                doc_id=doc_id,
                content=chunk_text,
                chunk_index=chunk_index,
                start_offset=start_offset,
                end_offset=end_offset,
            ))
            chunk_index += 1
            i += self.chunk_size - self.chunk_overlap
        return chunks

    def _chunk_by_pages(self, doc_id: str, pages: List[Dict]) -> List[Chunk]:
        """Create chunks from PDF pages."""
        chunks = []
        for page_data in pages:
            page_num = page_data.get('page', 1)
            text = page_data.get('text', '')
            if not text.strip():
                continue
            # Split large pages further
            page_chunks = self._chunk_text(doc_id, text)
            for chunk in page_chunks:
                chunk.page_number = page_num
            chunks.extend(page_chunks)
        # Re-index
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i
        return chunks

    def _chunk_by_lines(self, doc_id: str, lines: List[str]) -> List[Chunk]:
        """Create chunks from log lines."""
        chunks = []
        chunk_size_lines = 50
        for i in range(0, len(lines), chunk_size_lines):
            batch = lines[i:i + chunk_size_lines]
            text = '\n'.join(batch)
            chunks.append(Chunk(
                chunk_id=str(uuid.uuid4()),
                doc_id=doc_id,
                content=text,
                chunk_index=len(chunks),
                start_offset=i,
                end_offset=i + len(batch),
                line_start=i + 1,
                line_end=i + len(batch),
            ))
        return chunks

    def _chunk_spreadsheet(self, doc_id: str, sheets: List[Dict]) -> List[Chunk]:
        """Create chunks from spreadsheet sheets."""
        chunks = []
        for sheet_idx, sheet in enumerate(sheets):
            rows = sheet.get('rows', [])
            sheet_name = sheet.get('name', f'Sheet{sheet_idx + 1}')
            # Chunk rows in batches
            batch_size = 100
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                text = f"Sheet: {sheet_name}\n" + '\n'.join('\t'.join(row) for row in batch)
                chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=text,
                    chunk_index=len(chunks),
                    start_offset=i,
                    end_offset=i + len(batch),
                    page_number=sheet_idx + 1,
                    section=sheet_name,
                    metadata={'sheet': sheet_name, 'row_start': i, 'row_end': i + len(batch)},
                ))
        return chunks

    def _chunk_archive(self, doc_id: str, pages: List[Dict]) -> List[Chunk]:
        """Create chunks from archive members."""
        chunks = []
        for page_data in pages:
            page_num = page_data.get('page', 1)
            text = page_data.get('text', '')
            if not text.strip():
                continue
            # Extract member name from text
            member_name = ''
            if text.startswith('['):
                end = text.find(']')
                if end > 0:
                    member_name = text[1:end]
            page_chunks = self._chunk_text(doc_id, text)
            for chunk in page_chunks:
                chunk.page_number = page_num
                chunk.section = member_name
            chunks.extend(page_chunks)
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i
        return chunks

    def _chunk_by_sections(self, doc_id: str, sections: List[Dict], full_text: str) -> List[Chunk]:
        """Create chunks from markdown sections."""
        chunks = []
        if not sections:
            return self._chunk_text(doc_id, full_text)
        for section in sections:
            title = section.get('title', '')
            content = section.get('content', '')
            if not content.strip():
                continue
            section_chunks = self._chunk_text(doc_id, content)
            for chunk in section_chunks:
                chunk.section = title
            chunks.extend(section_chunks)
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i
        return chunks


# ============================================================
# Ingestion Pipeline
# ============================================================

class IngestionPipeline:
    """Manages the ingestion of documents into the knowledge base."""

    def __init__(self, db: Database, vault_path: str):
        self.db = db
        self.vault_path = vault_path
        self.extractor = TextExtractor()
        self.chunker = Chunker()

    def ingest_file(self, file_path: str, catalog_id: Optional[str] = None,
                    tags: Optional[List[str]] = None, force: bool = False) -> Optional[DocumentRecord]:
        """Ingest a single file into the knowledge base."""
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        # Compute content hash
        content_hash = self._compute_hash(file_path)

        # Check if already ingested
        existing = self.db.fetchone(
            "SELECT doc_id, content_hash FROM documents WHERE file_path = ?",
            (str(path.resolve()),)
        )
        if existing and not force:
            if existing['content_hash'] == content_hash:
                logger.info(f"File unchanged, skipping: {file_path}")
                return self._load_doc(existing['doc_id'])
            else:
                logger.info(f"File changed, re-ingesting: {file_path}")
                self._delete_doc(existing['doc_id'])

        # Extract content
        extraction = self.extractor.extract(file_path)

        # Build document record
        stat = path.stat()
        now = datetime.datetime.utcnow().isoformat()
        doc_id = str(uuid.uuid4())
        title = self._extract_title(path, extraction)
        folder_path = str(path.parent.resolve())

        doc = DocumentRecord(
            doc_id=doc_id,
            file_path=str(path.resolve()),
            title=title,
            doc_type=extraction.get('doc_type', 'text'),
            content_hash=content_hash,
            size_bytes=stat.st_size,
            created_at=datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            updated_at=datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            ingested_at=now,
            tags=tags or [],
            metadata=extraction.get('metadata', {}),
            catalog_id=catalog_id,
            folder_path=folder_path,
            word_count=extraction.get('word_count', 0),
            page_count=extraction.get('page_count', 0),
        )

        # Create chunks
        chunks = self.chunker.chunk_document(doc_id, extraction)
        doc.chunk_count = len(chunks)

        # Store in database
        self._store_document(doc)
        self._store_chunks(chunks)

        logger.info(f"Ingested: {file_path} ({len(chunks)} chunks)")
        return doc

    def ingest_directory(self, dir_path: str, recursive: bool = True,
                         catalog_id: Optional[str] = None,
                         tags: Optional[List[str]] = None,
                         extensions: Optional[List[str]] = None) -> List[DocumentRecord]:
        """Ingest all files in a directory."""
        path = Path(dir_path)
        if not path.exists():
            logger.error(f"Directory not found: {dir_path}")
            return []

        docs = []
        pattern = '**/*' if recursive else '*'
        for file_path in path.glob(pattern):
            if not file_path.is_file():
                continue
            if extensions and file_path.suffix.lower() not in extensions:
                continue
            # Skip hidden files and system files
            if file_path.name.startswith('.'):
                continue
            doc = self.ingest_file(str(file_path), catalog_id=catalog_id, tags=tags)
            if doc:
                docs.append(doc)
        return docs

    def _compute_hash(self, file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()

    def _extract_title(self, path: Path, extraction: Dict[str, Any]) -> str:
        # Try metadata title first
        meta = extraction.get('metadata', {})
        if meta.get('title'):
            return str(meta['title'])
        # Use filename without extension
        return path.stem.replace('_', ' ').replace('-', ' ').title()

    def _store_document(self, doc: DocumentRecord):
        self.db.execute("""
            INSERT OR REPLACE INTO documents
            (doc_id, file_path, title, doc_type, content_hash, size_bytes,
             created_at, updated_at, ingested_at, tags, metadata, catalog_id,
             folder_path, language, word_count, page_count, chunk_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc.doc_id, doc.file_path, doc.title, doc.doc_type, doc.content_hash,
            doc.size_bytes, doc.created_at, doc.updated_at, doc.ingested_at,
            json.dumps(doc.tags), json.dumps(doc.metadata), doc.catalog_id,
            doc.folder_path, doc.language, doc.word_count, doc.page_count, doc.chunk_count
        ))
        self.db.commit()

    def _store_chunks(self, chunks: List[Chunk]):
        if not chunks:
            return
        # Store in chunks table
        self.db.executemany("""
            INSERT OR REPLACE INTO chunks
            (chunk_id, doc_id, content, chunk_index, start_offset, end_offset,
             page_number, line_start, line_end, section, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (c.chunk_id, c.doc_id, c.content, c.chunk_index, c.start_offset,
             c.end_offset, c.page_number, c.line_start, c.line_end, c.section,
             json.dumps(c.metadata))
            for c in chunks
        ])
        # Store in FTS table
        self.db.executemany("""
            INSERT INTO chunks_fts (chunk_id, doc_id, content, section)
            VALUES (?, ?, ?, ?)
        """, [
            (c.chunk_id, c.doc_id, c.content, c.section or '')
            for c in chunks
        ])
        self.db.commit()

    def _delete_doc(self, doc_id: str):
        self.db.execute("DELETE FROM chunks_fts WHERE doc_id = ?", (doc_id,))
        self.db.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        self.db.commit()

    def _load_doc(self, doc_id: str) -> Optional[DocumentRecord]:
        row = self.db.fetchone("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        if row:
            return self._row_to_doc(row)
        return None

    def _row_to_doc(self, row: sqlite3.Row) -> DocumentRecord:
        return DocumentRecord(
            doc_id=row['doc_id'],
            file_path=row['file_path'],
            title=row['title'],
            doc_type=row['doc_type'],
            content_hash=row['content_hash'],
            size_bytes=row['size_bytes'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            ingested_at=row['ingested_at'],
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}'),
            catalog_id=row['catalog_id'],
            folder_path=row['folder_path'] or '',
            language=row['language'] or 'en',
            word_count=row['word_count'] or 0,
            page_count=row['page_count'] or 0,
            chunk_count=row['chunk_count'] or 0,
        )


# ============================================================
# Search Engine
# ============================================================

class LexicalSearchEngine:
    """FTS5-based lexical search engine."""

    def __init__(self, db: Database):
        self.db = db

    def search(self, query: str, limit: int = 20,
               doc_ids: Optional[List[str]] = None,
               doc_types: Optional[List[str]] = None,
               catalog_id: Optional[str] = None,
               tags: Optional[List[str]] = None) -> List[SearchResult]:
        """Perform lexical search using FTS5."""
        # Sanitize query for FTS5
        fts_query = self._sanitize_fts_query(query)
        if not fts_query:
            return []

        # Build filter conditions
        filters = []
        params = [fts_query]

        if doc_ids:
            placeholders = ','.join('?' * len(doc_ids))
            filters.append(f"d.doc_id IN ({placeholders})")
            params.extend(doc_ids)

        if doc_types:
            placeholders = ','.join('?' * len(doc_types))
            filters.append(f"d.doc_type IN ({placeholders})")
            params.extend(doc_types)

        if catalog_id:
            filters.append("d.catalog_id = ?")
            params.append(catalog_id)

        filter_clause = ""
        if filters:
            filter_clause = "AND " + " AND ".join(filters)

        params.append(limit)

        sql = f"""
            SELECT
                c.chunk_id, c.doc_id, c.content, c.chunk_index,
                c.start_offset, c.end_offset, c.page_number,
                c.line_start, c.line_end, c.section, c.metadata,
                d.doc_id as d_doc_id, d.file_path, d.title, d.doc_type,
                d.content_hash, d.size_bytes, d.created_at, d.updated_at,
                d.ingested_at, d.tags, d.metadata as d_metadata,
                d.catalog_id, d.folder_path, d.language, d.word_count,
                d.page_count, d.chunk_count,
                bm25(chunks_fts) as score
            FROM chunks_fts
            JOIN chunks c ON chunks_fts.chunk_id = c.chunk_id
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE chunks_fts MATCH ?
            {filter_clause}
            ORDER BY score
            LIMIT ?
        """

        try:
            rows = self.db.fetchall(sql, tuple(params))
        except Exception as e:
            logger.warning(f"FTS search error: {e}")
            return []

        results = []
        for row in rows:
            chunk = Chunk(
                chunk_id=row['chunk_id'],
                doc_id=row['doc_id'],
                content=row['content'],
                chunk_index=row['chunk_index'],
                start_offset=row['start_offset'],
                end_offset=row['end_offset'],
                page_number=row['page_number'],
                line_start=row['line_start'],
                line_end=row['line_end'],
                section=row['section'],
                metadata=json.loads(row['metadata'] or '{}'),
            )
            doc = DocumentRecord(
                doc_id=row['d_doc_id'],
                file_path=row['file_path'],
                title=row['title'],
                doc_type=row['doc_type'],
                content_hash=row['content_hash'],
                size_bytes=row['size_bytes'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                ingested_at=row['ingested_at'],
                tags=json.loads(row['tags'] or '[]'),
                metadata=json.loads(row['d_metadata'] or '{}'),
                catalog_id=row['catalog_id'],
                folder_path=row['folder_path'] or '',
                language=row['language'] or 'en',
                word_count=row['word_count'] or 0,
                page_count=row['page_count'] or 0,
                chunk_count=row['chunk_count'] or 0,
            )
            score = abs(float(row['score'])) if row['score'] else 0.0
            snippet = self._make_snippet(chunk.content, query)
            results.append(SearchResult(
                chunk=chunk,
                doc=doc,
                score=score,
                match_type='lexical',
                snippet=snippet,
                highlights=self._find_highlights(chunk.content, query),
            ))

        # Filter by tags if needed
        if tags:
            results = [r for r in results if any(t in r.doc.tags for t in tags)]

        return results

    def _sanitize_fts_query(self, query: str) -> str:
        """Sanitize query for FTS5."""
        # Remove special FTS5 characters that could cause errors
        query = query.strip()
        if not query:
            return ''
        # Escape quotes
        query = query.replace('"', '""')
        # For simple queries, just use the words
        words = re.findall(r'\w+', query)
        if not words:
            return ''
        return ' '.join(words)

    def _make_snippet(self, content: str, query: str, max_len: int = 200) -> str:
        """Create a snippet highlighting the query terms."""
        words = re.findall(r'\w+', query.lower())
        content_lower = content.lower()
        best_pos = 0
        best_score = 0
        for i in range(0, len(content), 50):
            window = content_lower[i:i + max_len]
            score = sum(1 for w in words if w in window)
            if score > best_score:
                best_score = score
                best_pos = i
        snippet = content[best_pos:best_pos + max_len]
        if best_pos > 0:
            snippet = '...' + snippet
        if best_pos + max_len < len(content):
            snippet = snippet + '...'
        return snippet

    def _find_highlights(self, content: str, query: str) -> List[str]:
        """Find highlighted phrases in content."""
        words = re.findall(r'\w+', query.lower())
        highlights = []
        for word in words:
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(content):
                start = max(0, match.start() - 30)
                end = min(len(content), match.end() + 30)
                highlights.append(content[start:end])
        return highlights[:5]


class EmbeddingEngine:
    """Manages document embeddings for semantic search."""

    def __init__(self, db: Database, model_name: str = "text-embedding-3-small"):
        self.db = db
        self.model_name = model_name
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
            response = client.embeddings.create(
                model=self.model_name,
                input=text[:8000],  # Truncate to avoid token limits
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Embedding error: {e}")
            return None

    def embed_chunks(self, chunks: List[Chunk]) -> int:
        """Embed a list of chunks and store in database."""
        count = 0
        for chunk in chunks:
            embedding = self.embed_text(chunk.content)
            if embedding is None:
                continue
            embedding_bytes = self._serialize_embedding(embedding)
            now = datetime.datetime.utcnow().isoformat()
            self.db.execute("""
                INSERT OR REPLACE INTO embeddings (chunk_id, embedding, model, created_at)
                VALUES (?, ?, ?, ?)
            """, (chunk.chunk_id, embedding_bytes, self.model_name, now))
            count += 1
        self.db.commit()
        return count

    def semantic_search(self, query: str, limit: int = 20,
                        doc_ids: Optional[List[str]] = None) -> List[Tuple[str, float]]:
        """Search by semantic similarity. Returns (chunk_id, score) pairs."""
        query_embedding = self.embed_text(query)
        if query_embedding is None:
            return []

        # Load all embeddings and compute cosine similarity
        if doc_ids:
            placeholders = ','.join('?' * len(doc_ids))
            rows = self.db.fetchall(f"""
                SELECT e.chunk_id, e.embedding
                FROM embeddings e
                JOIN chunks c ON e.chunk_id = c.chunk_id
                WHERE c.doc_id IN ({placeholders})
            """, tuple(doc_ids))
        else:
            rows = self.db.fetchall("SELECT chunk_id, embedding FROM embeddings")

        if not rows:
            return []

        results = []
        query_vec = query_embedding
        for row in rows:
            try:
                stored_vec = self._deserialize_embedding(row['embedding'])
                score = self._cosine_similarity(query_vec, stored_vec)
                results.append((row['chunk_id'], score))
            except Exception:
                continue

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def _serialize_embedding(self, embedding: List[float]) -> bytes:
        import struct
        return struct.pack(f'{len(embedding)}f', *embedding)

    def _deserialize_embedding(self, data: bytes) -> List[float]:
        import struct
        n = len(data) // 4
        return list(struct.unpack(f'{n}f', data))

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
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


class Reranker:
    """Reranks search results for better relevance."""

    def rerank(self, query: str, results: List[SearchResult], top_k: int = 10) -> List[SearchResult]:
        """Rerank results using a simple scoring heuristic."""
        query_words = set(re.findall(r'\w+', query.lower()))
        for result in results:
            content_words = set(re.findall(r'\w+', result.chunk.content.lower()))
            # Jaccard similarity
            if query_words and content_words:
                intersection = len(query_words & content_words)
                union = len(query_words | content_words)
                jaccard = intersection / union if union > 0 else 0
                # Boost by exact phrase matches
                phrase_boost = 1.0
                for word in query_words:
                    if word in result.chunk.content.lower():
                        phrase_boost += 0.1
                result.score = result.score * 0.5 + jaccard * phrase_boost * 0.5
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]


class SearchEngine:
    """Main search engine combining lexical and semantic search."""

    def __init__(self, db: Database, use_embeddings: bool = False,
                 use_reranking: bool = True):
        self.db = db
        self.use_embeddings = use_embeddings
        self.use_reranking = use_reranking
        self.lexical = LexicalSearchEngine(db)
        self.embedding_engine = EmbeddingEngine(db) if use_embeddings else None
        self.reranker = Reranker() if use_reranking else None

    def search(self, query: str, limit: int = 20,
               filters: Optional[Dict[str, Any]] = None,
               source_quota: Optional[Dict[str, int]] = None) -> List[SearchResult]:
        """Search the knowledge base."""
        filters = filters or {}
        doc_ids = filters.get('doc_ids')
        doc_types = filters.get('doc_types')
        catalog_id = filters.get('catalog_id')
        tags = filters.get('tags')

        # Lexical search
        results = self.lexical.search(
            query, limit=limit * 2,
            doc_ids=doc_ids, doc_types=doc_types,
            catalog_id=catalog_id, tags=tags
        )

        # Semantic search (if enabled)
        if self.use_embeddings and self.embedding_engine:
            semantic_pairs = self.embedding_engine.semantic_search(query, limit=limit, doc_ids=doc_ids)
            if semantic_pairs:
                semantic_chunk_ids = {cid: score for cid, score in semantic_pairs}
                # Merge with lexical results
                existing_ids = {r.chunk.chunk_id for r in results}
                for chunk_id, sem_score in semantic_pairs:
                    if chunk_id not in existing_ids:
                        chunk_row = self.db.fetchone("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,))
                        if chunk_row:
                            doc_row = self.db.fetchone("SELECT * FROM documents WHERE doc_id = ?", (chunk_row['doc_id'],))
                            if doc_row:
                                chunk = Chunk(
                                    chunk_id=chunk_row['chunk_id'],
                                    doc_id=chunk_row['doc_id'],
                                    content=chunk_row['content'],
                                    chunk_index=chunk_row['chunk_index'],
                                    start_offset=chunk_row['start_offset'],
                                    end_offset=chunk_row['end_offset'],
                                    page_number=chunk_row['page_number'],
                                    line_start=chunk_row['line_start'],
                                    line_end=chunk_row['line_end'],
                                    section=chunk_row['section'],
                                    metadata=json.loads(chunk_row['metadata'] or '{}'),
                                )
                                doc = self._row_to_doc(doc_row)
                                results.append(SearchResult(
                                    chunk=chunk, doc=doc,
                                    score=sem_score,
                                    match_type='semantic',
                                    snippet=self.lexical._make_snippet(chunk.content, query),
                                ))
                # Update scores for hybrid results
                for r in results:
                    if r.chunk.chunk_id in semantic_chunk_ids:
                        r.score = (r.score + semantic_chunk_ids[r.chunk.chunk_id]) / 2
                        r.match_type = 'hybrid'

        # Apply source quotas
        if source_quota:
            results = self._apply_source_quota(results, source_quota)

        # Rerank
        if self.reranker and results:
            results = self.reranker.rerank(query, results, top_k=limit)

        return results[:limit]

    def _apply_source_quota(self, results: List[SearchResult],
                             quota: Dict[str, int]) -> List[SearchResult]:
        """Apply per-source quotas to results."""
        doc_counts: Dict[str, int] = defaultdict(int)
        filtered = []
        for r in results:
            doc_id = r.doc.doc_id
            max_per_doc = quota.get(doc_id, quota.get('default', 999))
            if doc_counts[doc_id] < max_per_doc:
                filtered.append(r)
                doc_counts[doc_id] += 1
        return filtered

    def _row_to_doc(self, row: sqlite3.Row) -> DocumentRecord:
        return DocumentRecord(
            doc_id=row['doc_id'],
            file_path=row['file_path'],
            title=row['title'],
            doc_type=row['doc_type'],
            content_hash=row['content_hash'],
            size_bytes=row['size_bytes'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            ingested_at=row['ingested_at'],
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}'),
            catalog_id=row['catalog_id'],
            folder_path=row['folder_path'] or '',
            language=row['language'] or 'en',
            word_count=row['word_count'] or 0,
            page_count=row['page_count'] or 0,
            chunk_count=row['chunk_count'] or 0,
        )


# ============================================================
# Library Organization
# ============================================================

class CatalogManager:
    """Manages catalogs for organizing documents."""

    def __init__(self, db: Database):
        self.db = db

    def create_catalog(self, name: str, description: str = '',
                       tags: Optional[List[str]] = None,
                       metadata: Optional[Dict] = None) -> Catalog:
        """Create a new catalog."""
        now = datetime.datetime.utcnow().isoformat()
        catalog = Catalog(
            catalog_id=str(uuid.uuid4()),
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
            tags=tags or [],
            metadata=metadata or {},
        )
        self.db.execute("""
            INSERT INTO catalogs (catalog_id, name, description, created_at, updated_at, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (catalog.catalog_id, catalog.name, catalog.description,
              catalog.created_at, catalog.updated_at,
              json.dumps(catalog.tags), json.dumps(catalog.metadata)))
        self.db.commit()
        return catalog

    def get_catalog(self, catalog_id: str) -> Optional[Catalog]:
        row = self.db.fetchone("SELECT * FROM catalogs WHERE catalog_id = ?", (catalog_id,))
        if row:
            return self._row_to_catalog(row)
        return None

    def get_catalog_by_name(self, name: str) -> Optional[Catalog]:
        row = self.db.fetchone("SELECT * FROM catalogs WHERE name = ?", (name,))
        if row:
            return self._row_to_catalog(row)
        return None

    def list_catalogs(self) -> List[Catalog]:
        rows = self.db.fetchall("SELECT * FROM catalogs ORDER BY name")
        return [self._row_to_catalog(r) for r in rows]

    def update_catalog(self, catalog_id: str, **kwargs) -> Optional[Catalog]:
        catalog = self.get_catalog(catalog_id)
        if not catalog:
            return None
        now = datetime.datetime.utcnow().isoformat()
        for key, value in kwargs.items():
            if hasattr(catalog, key):
                setattr(catalog, key, value)
        catalog.updated_at = now
        self.db.execute("""
            UPDATE catalogs SET name=?, description=?, updated_at=?, tags=?, metadata=?
            WHERE catalog_id=?
        """, (catalog.name, catalog.description, catalog.updated_at,
              json.dumps(catalog.tags), json.dumps(catalog.metadata), catalog_id))
        self.db.commit()
        return catalog

    def delete_catalog(self, catalog_id: str):
        self.db.execute("UPDATE documents SET catalog_id=NULL WHERE catalog_id=?", (catalog_id,))
        self.db.execute("DELETE FROM catalogs WHERE catalog_id=?", (catalog_id,))
        self.db.commit()

    def add_document_to_catalog(self, doc_id: str, catalog_id: str):
        self.db.execute("UPDATE documents SET catalog_id=? WHERE doc_id=?", (catalog_id, doc_id))
        self.db.commit()

    def get_catalog_documents(self, catalog_id: str) -> List[str]:
        rows = self.db.fetchall("SELECT doc_id FROM documents WHERE catalog_id=?", (catalog_id,))
        return [r['doc_id'] for r in rows]

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


class TagManager:
    """Manages tags for documents."""

    def __init__(self, db: Database):
        self.db = db

    def create_tag(self, name: str, color: str = '#888888', description: str = '') -> str:
        """Create a new tag, return tag_id."""
        existing = self.db.fetchone("SELECT tag_id FROM tags WHERE name=?", (name,))
        if existing:
            return existing['tag_id']
        tag_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()
        self.db.execute("""
            INSERT INTO tags (tag_id, name, color, description, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (tag_id, name, color, description, now))
        self.db.commit()
        return tag_id

    def add_tag_to_document(self, doc_id: str, tag: str):
        """Add a tag to a document."""
        self.create_tag(tag)
        row = self.db.fetchone("SELECT tags FROM documents WHERE doc_id=?", (doc_id,))
        if row:
            tags = json.loads(row['tags'] or '[]')
            if tag not in tags:
                tags.append(tag)
                self.db.execute("UPDATE documents SET tags=? WHERE doc_id=?",
                                (json.dumps(tags), doc_id))
                self.db.commit()

    def remove_tag_from_document(self, doc_id: str, tag: str):
        """Remove a tag from a document."""
        row = self.db.fetchone("SELECT tags FROM documents WHERE doc_id=?", (doc_id,))
        if row:
            tags = json.loads(row['tags'] or '[]')
            if tag in tags:
                tags.remove(tag)
                self.db.execute("UPDATE documents SET tags=? WHERE doc_id=?",
                                (json.dumps(tags), doc_id))
                self.db.commit()

    def get_documents_by_tag(self, tag: str) -> List[str]:
        """Get all document IDs with a given tag."""
        rows = self.db.fetchall("SELECT doc_id, tags FROM documents")
        result = []
        for row in rows:
            tags = json.loads(row['tags'] or '[]')
            if tag in tags:
                result.append(row['doc_id'])
        return result

    def list_all_tags(self) -> List[Dict[str, Any]]:
        """List all tags with usage counts."""
        rows = self.db.fetchall("SELECT * FROM tags ORDER BY name")
        tags = []
        for row in rows:
            count = len(self.get_documents_by_tag(row['name']))
            tags.append({
                'tag_id': row['tag_id'],
                'name': row['name'],
                'color': row['color'],
                'description': row['description'],
                'count': count,
            })
        return tags


class ViewManager:
    """Manages saved search views."""

    def __init__(self, db: Database):
        self.db = db

    def create_view(self, name: str, query: str, description: str = '',
                    filters: Optional[Dict] = None) -> View:
        """Create a new saved view."""
        now = datetime.datetime.utcnow().isoformat()
        view = View(
            view_id=str(uuid.uuid4()),
            name=name,
            description=description,
            query=query,
            filters=filters or {},
            created_at=now,
            updated_at=now,
        )
        self.db.execute("""
            INSERT INTO views (view_id, name, description, query, filters, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (view.view_id, view.name, view.description, view.query,
              json.dumps(view.filters), view.created_at, view.updated_at))
        self.db.commit()
        return view

    def get_view(self, view_id: str) -> Optional[View]:
        row = self.db.fetchone("SELECT * FROM views WHERE view_id=?", (view_id,))
        if row:
            return self._row_to_view(row)
        return None

    def get_view_by_name(self, name: str) -> Optional[View]:
        row = self.db.fetchone("SELECT * FROM views WHERE name=?", (name,))
        if row:
            return self._row_to_view(row)
        return None

    def list_views(self) -> List[View]:
        rows = self.db.fetchall("SELECT * FROM views ORDER BY name")
        return [self._row_to_view(r) for r in rows]

    def delete_view(self, view_id: str):
        self.db.execute("DELETE FROM views WHERE view_id=?", (view_id,))
        self.db.commit()

    def _row_to_view(self, row: sqlite3.Row) -> View:
        return View(
            view_id=row['view_id'],
            name=row['name'],
            description=row['description'] or '',
            query=row['query'],
            filters=json.loads(row['filters'] or '{}'),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )


class RelationMiner:
    """Mines relations between documents."""

    def __init__(self, db: Database):
        self.db = db

    def mine_relations(self, doc_id: str, all_doc_ids: Optional[List[str]] = None) -> List[Relation]:
        """Mine relations for a document."""
        relations = []

        # Get document content
        chunks = self.db.fetchall("SELECT content FROM chunks WHERE doc_id=?", (doc_id,))
        if not chunks:
            return []
        doc_text = ' '.join(c['content'] for c in chunks).lower()

        # Get all other documents
        if all_doc_ids is None:
            rows = self.db.fetchall("SELECT doc_id, title, file_path FROM documents WHERE doc_id != ?", (doc_id,))
        else:
            placeholders = ','.join('?' * len(all_doc_ids))
            rows = self.db.fetchall(
                f"SELECT doc_id, title, file_path FROM documents WHERE doc_id IN ({placeholders}) AND doc_id != ?",
                tuple(all_doc_ids) + (doc_id,)
            )

        for row in rows:
            target_id = row['doc_id']
            target_title = row['title'].lower()
            target_path = Path(row['file_path']).stem.lower()

            # Check if document references target by title or filename
            confidence = 0.0
            evidence = ''

            if target_title in doc_text:
                confidence = 0.8
                evidence = f"Document mentions '{row['title']}'"
            elif target_path in doc_text:
                confidence = 0.6
                evidence = f"Document mentions filename '{target_path}'"

            if confidence > 0:
                relation = Relation(
                    relation_id=str(uuid.uuid4()),
                    source_doc_id=doc_id,
                    target_doc_id=target_id,
                    relation_type='related',
                    confidence=confidence,
                    evidence=evidence,
                    created_at=datetime.datetime.utcnow().isoformat(),
                    auto_detected=True,
                )
                relations.append(relation)

        # Store relations
        for relation in relations:
            self._store_relation(relation)

        return relations

    def add_relation(self, source_doc_id: str, target_doc_id: str,
                     relation_type: str, evidence: str = '',
                     confidence: float = 1.0) -> Relation:
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
        self._store_relation(relation)
        return relation

    def get_relations(self, doc_id: str) -> List[Relation]:
        """Get all relations for a document."""
        rows = self.db.fetchall("""
            SELECT * FROM relations
            WHERE source_doc_id=? OR target_doc_id=?
        """, (doc_id, doc_id))
        return [self._row_to_relation(r) for r in rows]

    def _store_relation(self, relation: Relation):
        # Check for existing relation
        existing = self.db.fetchone("""
            SELECT relation_id FROM relations
            WHERE source_doc_id=? AND target_doc_id=? AND relation_type=?
        """, (relation.source_doc_id, relation.target_doc_id, relation.relation_type))
        if existing:
            return
        self.db.execute("""
            INSERT INTO relations
            (relation_id, source_doc_id, target_doc_id, relation_type,
             confidence, evidence, created_at, auto_detected)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (relation.relation_id, relation.source_doc_id, relation.target_doc_id,
              relation.relation_type, relation.confidence, relation.evidence,
              relation.created_at, 1 if relation.auto_detected else 0))
        self.db.commit()

    def _row_to_relation(self, row: sqlite3.Row) -> Relation:
        return Relation(
            relation_id=row['relation_id'],
            source_doc_id=row['source_doc_id'],
            target_doc_id=row['target_doc_id'],
            relation_type=row['relation_type'],
            confidence=row['confidence'],
            evidence=row['evidence'] or '',
            created_at=row['created_at'],
            auto_detected=bool(row['auto_detected']),
        )


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
        """, (entry.entry_id, entry.content, entry.created_at,
              json.dumps(entry.tags), json.dumps(entry.linked_docs),
              json.dumps(entry.linked_notes)))
        self.db.commit()
        return entry

    def get_entry(self, entry_id: str) -> Optional[JournalEntry]:
        row = self.db.fetchone("SELECT * FROM journal_entries WHERE entry_id=?", (entry_id,))
        if row:
            return self._row_to_entry(row)
        return None

    def list_entries(self, limit: int = 50, offset: int = 0) -> List[JournalEntry]:
        rows = self.db.fetchall("""
            SELECT * FROM journal_entries ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, (limit, offset))
        return [self._row_to_entry(r) for r in rows]

    def search_entries(self, query: str) -> List[JournalEntry]:
        query_lower = query.lower()
        rows = self.db.fetchall("SELECT * FROM journal_entries ORDER BY created_at DESC")
        results = []
        for row in rows:
            if query_lower in row['content'].lower():
                results.append(self._row_to_entry(row))
        return results

    def _row_to_entry(self, row: sqlite3.Row) -> JournalEntry:
        return JournalEntry(
            entry_id=row['entry_id'],
            content=row['content'],
            created_at=row['created_at'],
            tags=json.loads(row['tags'] or '[]'),
            linked_docs=json.loads(row['linked_docs'] or '[]'),
            linked_notes=json.loads(row['linked_notes'] or '[]'),
        )


# ============================================================
# Document Reader (reads original file sections)
# ============================================================

class DocumentReader:
    """Reads specific sections/pages/lines from original files."""

    def __init__(self, extractor: TextExtractor):
        self.extractor = extractor

    def read_page(self, file_path: str, page_number: int) -> str:
        """Read a specific page from a document."""
        extraction = self.extractor.extract(file_path)
        pages = extraction.get('pages', [])
        for page in pages:
            if page.get('page') == page_number:
                return page.get('text', '')
        return ''

    def read_lines(self, file_path: str, line_start: int, line_end: int) -> str:
        """Read specific lines from a document."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            selected = lines[line_start - 1:line_end]
            return ''.join(selected)
        except Exception as e:
            logger.warning(f"Error reading lines from {file_path}: {e}")
            return ''

    def read_section(self, file_path: str, section_name: str) -> str:
        """Read a named section from a document."""
        extraction = self.extractor.extract(file_path)
        sections = extraction.get('sections', [])
        for section in sections:
            if section.get('title', '').lower() == section_name.lower():
                return section.get('content', '')
        # Fallback: search in text
        text = extraction.get('text', '')
        pattern = re.compile(
            r'(?:^|\n)#+\s*' + re.escape(section_name) + r'\s*\n(.*?)(?=\n#+\s|\Z)',
            re.IGNORECASE | re.DOTALL
        )
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
        return ''

    def read_archive_member(self, archive_path: str, member_name: str) -> str:
        """Read a specific member from an archive."""
        path = Path(archive_path)
        try:
            if path.suffix.lower() == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    with zf.open(member_name) as f:
                        return f.read().decode('utf-8', errors='replace')
            elif path.suffix.lower() in ('.tar', '.gz', '.bz2'):
                with tarfile.open(archive_path, 'r:*') as tf:
                    f = tf.extractfile(member_name)
                    if f:
                        return f.read().decode('utf-8', errors='replace')
        except Exception as e:
            logger.warning(f"Error reading archive member {member_name}: {e}")
        return ''

    def read_table_slice(self, file_path: str, sheet_name: Optional[str] = None,
                         row_start: int = 0, row_end: Optional[int] = None,
                         col_start: int = 0, col_end: Optional[int] = None) -> str:
        """Read a slice of a spreadsheet."""
        extraction = self.extractor.extract(file_path)
        sheets = extraction.get('sheets', [])
        if not sheets:
            return ''
        # Find the right sheet
        sheet = None
        if sheet_name:
            for s in sheets:
                if s.get('name', '').lower() == sheet_name.lower():
                    sheet = s
                    break
        if sheet is None and sheets:
            sheet = sheets[0]
        if sheet is None:
            return ''
        rows = sheet.get('rows', [])
        if row_end is None:
            row_end = len(rows)
        sliced_rows = rows[row_start:row_end]
        if col_end is not None:
            sliced_rows = [row[col_start:col_end] for row in sliced_rows]
        elif col_start > 0:
            sliced_rows = [row[col_start:] for row in sliced_rows]
        return '\n'.join('\t'.join(row) for row in sliced_rows)

    def read_chunk_context(self, file_path: str, chunk: Chunk, context_size: int = 200) -> str:
        """Read the original context around a chunk."""
        if chunk.page_number is not None:
            return self.read_page(file_path, chunk.page_number)
        elif chunk.line_start is not None and chunk.line_end is not None:
            return self.read_lines(file_path, chunk.line_start, chunk.line_end)
        elif chunk.section:
            return self.read_section(file_path, chunk.section)
        else:
            # Read by offset
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    text = f.read()
                start = max(0, chunk.start_offset - context_size)
                end = min(len(text), chunk.end_offset + context_size)
                return text[start:end]
            except Exception:
                return chunk.content


# ============================================================
# LLM Agent
# ============================================================

class LLMClient:
    """Abstraction over different LLM providers."""

    def __init__(self, provider: str = 'anthropic', model: Optional[str] = None):
        self.provider = provider
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            if self.provider == 'anthropic' and HAS_ANTHROPIC:
                self._client = anthropic.Anthropic()
            elif self.provider == 'openai' and HAS_OPENAI:
                self._client = openai.OpenAI()
        return self._client

    def complete(self, system_prompt: str, user_message: str,
                 max_tokens: int = 4096) -> str:
        """Get a completion from the LLM."""
        client = self._get_client()
        if client is None:
            return self._mock_completion(system_prompt, user_message)

        try:
            if self.provider == 'anthropic':
                model = self.model or 'claude-3-5-sonnet-20241022'
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{'role': 'user', 'content': user_message}]
                )
                return response.content[0].text
            elif self.provider == 'openai':
                model = self.model or 'gpt-4o'
                response = client.chat.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_message}
                    ]
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM completion error: {e}")
            return f"[LLM Error: {e}]"

        return self._mock_completion(system_prompt, user_message)

    def _mock_completion(self, system_prompt: str, user_message: str) -> str:
        """Mock completion when no LLM is available."""
        return (
            f"[Mock LLM Response]\n"
            f"Query: {user_message[:100]}...\n"
            f"Note: No LLM provider configured. Install anthropic or openai package."
        )


class CitationFormatter:
    """Formats citations for answers."""

    def format_citation(self, citation: Citation, index: int) -> str:
        """Format a single citation."""
        parts = [f"[{index}] {citation.title}"]
        if citation.page_number:
            parts.append(f"p.{citation.page_number}")
        if citation.line_start and citation.line_end:
            parts.append(f"lines {citation.line_start}-{citation.line_end}")
        if citation.section:
            parts.append(f"§{citation.section}")
        parts.append(f"({Path(citation.file_path).name})")
        return ' '.join(parts)

    def format_citations_block(self, citations: List[Citation]) -> str:
        """Format a block of citations."""
        if not citations:
            return ''
        lines = ['\n\n---\n**Sources:**']
        for i, citation in enumerate(citations, 1):
            lines.append(self.format_citation(citation, i))
            if citation.quote:
                lines.append(f'  > "{citation.quote[:150]}..."')
        return '\n'.join(lines)

    def inline_citation(self, index: int) -> str:
        return f"[{index}]"


class ResearchAgent:
    """The main research agent that answers queries using the knowledge base."""

    def __init__(self, db: Database, search_engine: SearchEngine,
                 document_reader: DocumentReader, llm_client: LLMClient,
                 vault_path: str):
        self.db = db
        self.search_engine = search_engine
        self.document_reader = document_reader
        self.llm_client = llm_client
        self.vault_path = vault_path
        self.citation_formatter = CitationFormatter()
        self.note_manager = InvestigationNoteManager(db)

    def answer(self, query: str, filters: Optional[Dict[str, Any]] = None,
               max_sources: int = 5, source_quota: Optional[Dict[str, int]] = None,
               save_note: bool = True) -> Dict[str, Any]:
        """Answer a query using the knowledge base."""
        # Search for relevant chunks
        results = self.search_engine.search(
            query,
            limit=max_sources * 3,
            filters=filters,
            source_quota=source_quota,
        )

        if not results:
            return {
                'answer': "I couldn't find any relevant information in the knowledge base for your query.",
                'citations': [],
                'note_id': None,
                'sources_consulted': 0,
            }

        # Read original context for top results
        contexts = []
        citations = []
        seen_docs = set()

        for result in results[:max_sources]:
            doc = result.doc
            chunk = result.chunk

            # Read original context
            original_context = self.document_reader.read_chunk_context(
                doc.file_path, chunk
            )

            context_entry = {
                'title': doc.title,
                'file_path': doc.file_path,
                'doc_type': doc.doc_type,
                'content': original_context or chunk.content,
                'page': chunk.page_number,
                'lines': (chunk.line_start, chunk.line_end) if chunk.line_start else None,
                'section': chunk.section,
                'score': result.score,
            }
            contexts.append(context_entry)

            # Build citation
            citation = Citation(
                doc_id=doc.doc_id,
                file_path=doc.file_path,
                title=doc.title,
                chunk_id=chunk.chunk_id,
                page_number=chunk.page_number,
                line_start=chunk.line_start,
                line_end=chunk.line_end,
                section=chunk.section,
                quote=chunk.content[:200],
            )
            citations.append(citation)
            seen_docs.add(doc.doc_id)

        # Build context for LLM
        context_text = self._build_context_text(contexts)

        # Generate answer
        system_prompt = self._build_system_prompt()
        user_message = self._build_user_message(query, context_text, len(citations))

        answer_text = self.llm_client.complete(system_prompt, user_message)

        # Append citations
        citations_block = self.citation_formatter.format_citations_block(citations)
        full_answer = answer_text + citations_block

        # Save investigation note
        note_id = None
        if save_note:
            note = self.note_manager.create_note(
                query=query,
                answer=full_answer,
                citations=citations,
                tags=['auto-generated'],
            )
            note_id = note.note_id

        return {
            'answer': full_answer,
            'citations': [asdict(c) for c in citations],
            'note_id': note_id,
            'sources_consulted': len(seen_docs),
            'chunks_retrieved': len(results),
        }

    def generate_report(self, topic: str, filters: Optional[Dict[str, Any]] = None,
                        max_sources: int = 10) -> Dict[str, Any]:
        """Generate a comprehensive report on a topic."""
        # Gather information from multiple angles
        sub_queries = self._generate_sub_queries(topic)
        all_results = []
        all_citations = []
        seen_chunk_ids = set()

        for sub_query in sub_queries:
            results = self.search_engine.search(sub_query, limit=5, filters=filters)
            for r in results:
                if r.chunk.chunk_id not in seen_chunk_ids:
                    all_results.append(r)
                    seen_chunk_ids.add(r.chunk.chunk_id)

        # Limit total sources
        all_results = all_results[:max_sources]

        # Read contexts
        contexts = []
        for result in all_results:
            doc = result.doc
            chunk = result.chunk
            original_context = self.document_reader.read_chunk_context(doc.file_path, chunk)
            contexts.append({
                'title': doc.title,
                'file_path': doc.file_path,
                'doc_type': doc.doc_type,
                'content': original_context or chunk.content,
                'page': chunk.page_number,
                'section': chunk.section,
                'score': result.score,
            })
            citation = Citation(
                doc_id=doc.doc_id,
                file_path=doc.file_path,
                title=doc.title,
                chunk_id=chunk.chunk_id,
                page_number=chunk.page_number,
                line_start=chunk.line_start,
                line_end=chunk.line_end,
                section=chunk.section,
                quote=chunk.content[:200],
            )
            all_citations.append(citation)

        context_text = self._build_context_text(contexts)
        system_prompt = self._build_report_system_prompt()
        user_message = f"Generate a comprehensive research report on: {topic}\n\n{context_text}"

        report_text = self.llm_client.complete(system_prompt, user_message, max_tokens=8192)
        citations_block = self.citation_formatter.format_citations_block(all_citations)
        full_report = report_text + citations_block

        # Save as investigation note
        note = self.note_manager.create_note(
            query=f"Report: {topic}",
            answer=full_report,
            citations=all_citations,
            tags=['report', 'auto-generated'],
        )

        return {
            'report': full_report,
            'citations': [asdict(c) for c in all_citations],
            'note_id': note.note_id,
            'sources_consulted': len(set(r.doc.doc_id for r in all_results)),
        }

    def _generate_sub_queries(self, topic: str) -> List[str]:
        """Generate sub-queries for comprehensive coverage."""
        words = topic.split()
        queries = [topic]
        if len(words) > 2:
            queries.append(' '.join(words[:3]))
            queries.append(' '.join(words[-3:]))
        queries.append(f"overview {topic}")
        queries.append(f"{topic} examples")
        return queries[:5]

    def _build_context_text(self, contexts: List[Dict]) -> str:
        """Build context text for LLM."""
        parts = []
        for i, ctx in enumerate(contexts, 1):
            header = f"[Source {i}] {ctx['title']}"
            if ctx.get('page'):
                header += f" (page {ctx['page']})"
            if ctx.get('section'):
                header += f" §{ctx['section']}"
            parts.append(f"{header}\n{ctx['content']}")
        return '\n\n---\n\n'.join(parts)

    def _build_system_prompt(self) -> str:
        return """You are Marginalia, a research assistant for a personal knowledge base.
Your task is to answer questions based ONLY on the provided source documents.

Guidelines:
- Answer based strictly on the provided sources
- Cite sources using [1], [2], etc. inline when referencing specific information
- If the sources don't contain enough information, say so clearly
- Be precise and scholarly in your responses
- Quote relevant passages when helpful
- Identify any contradictions between sources
- Note the document type and location when relevant (page numbers, sections, etc.)"""

    def _build_report_system_prompt(self) -> str:
        return """You are Marginalia, a research assistant generating comprehensive reports.
Your task is to synthesize information from multiple sources into a well-structured report.

Report structure:
1. Executive Summary
2. Key Findings (with inline citations)
3. Detailed Analysis
4. Contradictions or Gaps
5. Conclusions

Guidelines:
- Use inline citations [1], [2], etc.
- Organize information logically
- Highlight important patterns and connections
- Note the provenance of key claims"""

    def _build_user_message(self, query: str, context: str, num_sources: int) -> str:
        return f"""Query: {query}

I have retrieved {num_sources} relevant source(s) from the knowledge base. Please answer the query based on these sources:

{context}

Please provide a thorough answer with inline citations [1], [2], etc."""


# ============================================================
# Investigation Notes
# ============================================================

class InvestigationNoteManager:
    """Manages durable investigation notes."""

    def __init__(self, db: Database):
        self.db = db

    def create_note(self, query: str, answer: str, citations: List[Citation],
                    tags: Optional[List[str]] = None,
                    metadata: Optional[Dict] = None,
                    follow_up_questions: Optional[List[str]] = None) -> InvestigationNote:
        """Create a new investigation note."""
        note = InvestigationNote(
            note_id=str(uuid.uuid4()),
            query=query,
            answer=answer,
            citations=citations,
            created_at=datetime.datetime.utcnow().isoformat(),
            tags=tags or [],
            metadata=metadata or {},
            follow_up_questions=follow_up_questions or [],
        )
        self.db.execute("""
            INSERT INTO investigation_notes
            (note_id, query, answer, citations, created_at, tags, metadata, follow_up_questions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            note.note_id, note.query, note.answer,
            json.dumps([asdict(c) for c in note.citations]),
            note.created_at,
            json.dumps(note.tags),
            json.dumps(note.metadata),
            json.dumps(note.follow_up_questions),
        ))
        self.db.commit()
        return note

    def get_note(self, note_id: str) -> Optional[InvestigationNote]:
        row = self.db.fetchone("SELECT * FROM investigation_notes WHERE note_id=?", (note_id,))
        if row:
            return self._row_to_note(row)
        return None

    def list_notes(self, limit: int = 50, offset: int = 0) -> List[InvestigationNote]:
        rows = self.db.fetchall("""
            SELECT * FROM investigation_notes ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, (limit, offset))
        return [self._row_to_note(r) for r in rows]

    def search_notes(self, query: str) -> List[InvestigationNote]:
        """Search investigation notes by query text."""
        query_lower = query.lower()
        rows = self.db.fetchall("SELECT * FROM investigation_notes ORDER BY created_at DESC")
        results = []
        for row in rows:
            if query_lower in row['query'].lower() or query_lower in row['answer'].lower():
                results.append(self._row_to_note(row))
        return results

    def delete_note(self, note_id: str):
        self.db.execute("DELETE FROM investigation_notes WHERE note_id=?", (note_id,))
        self.db.commit()

    def export_note(self, note_id: str, output_path: str, format: str = 'markdown'):
        """Export a note to a file."""
        note = self.get_note(note_id)
        if not note:
            raise ValueError(f"Note not found: {note_id}")

        if format == 'markdown':
            content = self._note_to_markdown(note)
        elif format == 'json':
            content = json.dumps(asdict(note), indent=2, default=str)
        else:
            content = self._note_to_markdown(note)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _note_to_markdown(self, note: InvestigationNote) -> str:
        lines = [
            f"# Investigation Note",
            f"",
            f"**Query:** {note.query}",
            f"**Created:** {note.created_at}",
            f"**Tags:** {', '.join(note.tags) if note.tags else 'none'}",
            f"",
            f"## Answer",
            f"",
            note.answer,
        ]
        if note.follow_up_questions:
            lines.extend([
                f"",
                f"## Follow-up Questions",
                f"",
            ])
            for q in note.follow_up_questions:
                lines.append(f"- {q}")
        return '\n'.join(lines)

    def _row_to_note(self, row: sqlite3.Row) -> InvestigationNote:
        citations_data = json.loads(row['citations'] or '[]')
        citations = []
        for c in citations_data:
            try:
                citations.append(Citation(**c))
            except Exception:
                pass
        return InvestigationNote(
            note_id=row['note_id'],
            query=row['query'],
            answer=row['answer'],
            citations=citations,
            created_at=row['created_at'],
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}'),
            follow_up_questions=json.loads(row['follow_up_questions'] or '[]'),
        )


# ============================================================
# Document Manager (high-level document operations)
# ============================================================

class DocumentManager:
    """High-level document management operations."""

    def __init__(self, db: Database):
        self.db = db

    def get_document(self, doc_id: str) -> Optional[DocumentRecord]:
        row = self.db.fetchone("SELECT * FROM documents WHERE doc_id=?", (doc_id,))
        if row:
            return self._row_to_doc(row)
        return None

    def get_document_by_path(self, file_path: str) -> Optional[DocumentRecord]:
        row = self.db.fetchone("SELECT * FROM documents WHERE file_path=?",
                               (str(Path(file_path).resolve()),))
        if row:
            return self._row_to_doc(row)
        return None

    def list_documents(self, limit: int = 100, offset: int = 0,
                       doc_type: Optional[str] = None,
                       catalog_id: Optional[str] = None,
                       folder_path: Optional[str] = None) -> List[DocumentRecord]:
        conditions = []
        params = []
        if doc_type:
            conditions.append("doc_type=?")
            params.append(doc_type)
        if catalog_id:
            conditions.append("catalog_id=?")
            params.append(catalog_id)
        if folder_path:
            conditions.append("folder_path LIKE ?")
            params.append(f"{folder_path}%")
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.extend([limit, offset])
        rows = self.db.fetchall(
            f"SELECT * FROM documents {where} ORDER BY title LIMIT ? OFFSET ?",
            tuple(params)
        )
        return [self._row_to_doc(r) for r in rows]

    def update_document_metadata(self, doc_id: str, metadata: Dict[str, Any]):
        """Update document metadata."""
        existing = self.db.fetchone("SELECT metadata FROM documents WHERE doc_id=?", (doc_id,))
        if existing:
            current = json.loads(existing['metadata'] or '{}')
            current.update(metadata)
            self.db.execute("UPDATE documents SET metadata=? WHERE doc_id=?",
                            (json.dumps(current), doc_id))
            self.db.commit()

    def delete_document(self, doc_id: str):
        """Delete a document and all its chunks."""
        self.db.execute("DELETE FROM chunks_fts WHERE doc_id=?", (doc_id,))
        self.db.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
        self.db.commit()

    def get_document_chunks(self, doc_id: str) -> List[Chunk]:
        """Get all chunks for a document."""
        rows = self.db.fetchall(
            "SELECT * FROM chunks WHERE doc_id=? ORDER BY chunk_index",
            (doc_id,)
        )
        return [self._row_to_chunk(r) for r in rows]

    def get_document_stats(self) -> Dict[str, Any]:
        """Get statistics about the document collection."""
        total = self.db.fetchone("SELECT COUNT(*) as count FROM documents")['count']
        by_type = self.db.fetchall(
            "SELECT doc_type, COUNT(*) as count FROM documents GROUP BY doc_type"
        )
        total_chunks = self.db.fetchone("SELECT COUNT(*) as count FROM chunks")['count']
        total_words = self.db.fetchone("SELECT SUM(word_count) as total FROM documents")['total'] or 0
        return {
            'total_documents': total,
            'total_chunks': total_chunks,
            'total_words': total_words,
            'by_type': {r['doc_type']: r['count'] for r in by_type},
        }

    def _row_to_doc(self, row: sqlite3.Row) -> DocumentRecord:
        return DocumentRecord(
            doc_id=row['doc_id'],
            file_path=row['file_path'],
            title=row['title'],
            doc_type=row['doc_type'],
            content_hash=row['content_hash'],
            size_bytes=row['size_bytes'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            ingested_at=row['ingested_at'],
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}'),
            catalog_id=row['catalog_id'],
            folder_path=row['folder_path'] or '',
            language=row['language'] or 'en',
            word_count=row['word_count'] or 0,
            page_count=row['page_count'] or 0,
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
            section=row['section'],
            metadata=json.loads(row['metadata'] or '{}'),
        )


# ============================================================
# Main Marginalia System
# ============================================================

class Marginalia:
    """
    Main entry point for the Marginalia knowledge management system.
    
    Provides a unified interface to all subsystems:
    - Document ingestion
    - Library organization (catalogs, tags, views, relations, journals)
    - Search (lexical, semantic, hybrid)
    - Research agent (Q&A, reports)
    - Investigation notes
    """

    def __init__(self, vault_path: str, db_path: Optional[str] = None,
                 llm_provider: str = 'anthropic', llm_model: Optional[str] = None,
                 use_embeddings: bool = False, use_reranking: bool = True):
        """
        Initialize Marginalia.

        Args:
            vault_path: Path to the root folder of the knowledge base
            db_path: Path to SQLite database (defaults to vault_path/.marginalia/db.sqlite)
            llm_provider: LLM provider ('anthropic' or 'openai')
            llm_model: Specific model to use
            use_embeddings: Enable semantic search with embeddings
            use_reranking: Enable result reranking
        """
        self.vault_path = str(Path(vault_path).resolve())
        Path(self.vault_path).mkdir(parents=True, exist_ok=True)

        # Set up database
        if db_path is None:
            meta_dir = Path(self.vault_path) / '.marginalia'
            meta_dir.mkdir(exist_ok=True)
            db_path = str(meta_dir / 'db.sqlite')
        self.db_path = db_path
        self.db = Database(db_path)

        # Initialize subsystems
        self.extractor = TextExtractor()
        self.chunker = Chunker()
        self.ingestion = IngestionPipeline(self.db, self.vault_path)
        self.documents = DocumentManager(self.db)
        self.catalogs = CatalogManager(self.db)
        self.tags = TagManager(self.db)
        self.views = ViewManager(self.db)
        self.relations = RelationMiner(self.db)
        self.journal = JournalManager(self.db)
        self.notes = InvestigationNoteManager(self.db)
        self.reader = DocumentReader(self.extractor)
        self.search_engine = SearchEngine(
            self.db,
            use_embeddings=use_embeddings,
            use_reranking=use_reranking,
        )
        self.llm = LLMClient(provider=llm_provider, model=llm_model)
        self.agent = ResearchAgent(
            db=self.db,
            search_engine=self.search_engine,
            document_reader=self.reader,
            llm_client=self.llm,
            vault_path=self.vault_path,
        )

        logger.info(f"Marginalia initialized at {self.vault_path}")

    # ---- Ingestion ----

    def ingest(self, path: str, catalog: Optional[str] = None,
               tags: Optional[List[str]] = None,
               recursive: bool = True,
               force: bool = False) -> Union[Optional[DocumentRecord], List[DocumentRecord]]:
        """
        Ingest a file or directory.

        Args:
            path: File or directory path
            catalog: Catalog name to assign documents to
            tags: Tags to apply to documents
            recursive: If path is a directory, recurse into subdirectories
            force: Re-ingest even if file hasn't changed

        Returns:
            DocumentRecord for a file, list of DocumentRecords for a directory
        """
        catalog_id = None
        if catalog:
            cat = self.catalogs.get_catalog_by_name(catalog)
            if cat is None:
                cat = self.catalogs.create_catalog(catalog)
            catalog_id = cat.catalog_id

        p = Path(path)
        if p.is_file():
            return self.ingestion.ingest_file(str(p), catalog_id=catalog_id, tags=tags, force=force)
        elif p.is_dir():
            return self.ingestion.ingest_directory(
                str(p), recursive=recursive, catalog_id=catalog_id, tags=tags
            )
        else:
            logger.error(f"Path not found: {path}")
            return None

    def sync(self, path: Optional[str] = None) -> Dict[str, int]:
        """
        Sync the vault, re-ingesting changed files and removing deleted ones.

        Args:
            path: Directory to sync (defaults to vault_path)

        Returns:
            Dict with counts of added, updated, removed documents
        """
        sync_path = path or self.vault_path
        counts = {'added': 0, 'updated': 0, 'removed': 0}

        # Get all existing documents
        existing_docs = self.documents.list_documents(limit=100000)
        existing_paths = {doc.file_path: doc for doc in existing_docs}

        # Scan directory
        scan_path = Path(sync_path)
        found_paths = set()
        for file_path in scan_path.rglob('*'):
            if not file_path.is_file():
                continue
            if file_path.name.startswith('.'):
                continue
            abs_path = str(file_path.resolve())
            found_paths.add(abs_path)

            if abs_path in existing_paths:
                # Check if changed
                doc = existing_paths[abs_path]
                new_hash = self.ingestion._compute_hash(abs_path)
                if new_hash != doc.content_hash:
                    self.ingestion.ingest_file(abs_path, force=True)
                    counts['updated'] += 1
            else:
                result = self.ingestion.ingest_file(abs_path)
                if result:
                    counts['added'] += 1

        # Remove deleted files
        for abs_path, doc in existing_paths.items():
            if abs_path not in found_paths:
                self.documents.delete_document(doc.doc_id)
                counts['removed'] += 1

        return counts

    # ---- Search ----

    def search(self, query: str, limit: int = 10,
               doc_type: Optional[str] = None,
               catalog: Optional[str] = None,
               tags: Optional[List[str]] = None,
               source_quota: Optional[Dict[str, int]] = None) -> List[SearchResult]:
        """
        Search the knowledge base.

        Args:
            query: Search query
            limit: Maximum number of results
            doc_type: Filter by document type
            catalog: Filter by catalog name
            tags: Filter by tags
            source_quota: Max results per source document

        Returns:
            List of SearchResult objects
        """
        filters = {}
        if doc_type:
            filters['doc_types'] = [doc_type]
        if catalog:
            cat = self.catalogs.get_catalog_by_name(catalog)
            if cat:
                filters['catalog_id'] = cat.catalog_id
        if tags:
            filters['tags'] = tags

        return self.search_engine.search(
            query, limit=limit, filters=filters, source_quota=source_quota
        )

    # ---- Agent ----

    def ask(self, question: str, catalog: Optional[str] = None,
            tags: Optional[List[str]] = None,
            max_sources: int = 5,
            save_note: bool = True) -> Dict[str, Any]:
        """
        Ask a question and get a cited answer.

        Args:
            question: The research question
            catalog: Limit search to a catalog
            tags: Limit search to tagged documents
            max_sources: Maximum number of sources to consult
            save_note: Whether to save the answer as an investigation note

        Returns:
            Dict with 'answer', 'citations', 'note_id', 'sources_consulted'
        """
        filters = {}
        if catalog:
            cat = self.catalogs.get_catalog_by_name(catalog)
            if cat:
                filters['catalog_id'] = cat.catalog_id
        if tags:
            filters['tags'] = tags

        return self.agent.answer(
            question, filters=filters,
            max_sources=max_sources,
            save_note=save_note,
        )

    def report(self, topic: str, catalog: Optional[str] = None,
               max_sources: int = 10) -> Dict[str, Any]:
        """
        Generate a comprehensive research report.

        Args:
            topic: The report topic
            catalog: Limit to a catalog
            max_sources: Maximum sources to use

        Returns:
            Dict with 'report', 'citations', 'note_id', 'sources_consulted'
        """
        filters = {}
        if catalog:
            cat = self.catalogs.get_catalog_by_name(catalog)
            if cat:
                filters['catalog_id'] = cat.catalog_id

        return self.agent.generate_report(topic, filters=filters, max_sources=max_sources)

    # ---- Organization ----

    def create_catalog(self, name: str, description: str = '') -> Catalog:
        """Create a new catalog."""
        return self.catalogs.create_catalog(name, description)

    def add_to_catalog(self, doc_path_or_id: str, catalog_name: str):
        """Add a document to a catalog."""
        cat = self.catalogs.get_catalog_by_name(catalog_name)
        if cat is None:
            cat = self.catalogs.create_catalog(catalog_name)

        # Try as doc_id first, then as path
        doc = self.documents.get_document(doc_path_or_id)
        if doc is None:
            doc = self.documents.get_document_by_path(doc_path_or_id)
        if doc:
            self.catalogs.add_document_to_catalog(doc.doc_id, cat.catalog_id)

    def tag_document(self, doc_path_or_id: str, *tag_names: str):
        """Add tags to a document."""
        doc = self.documents.get_document(doc_path_or_id)
        if doc is None:
            doc = self.documents.get_document_by_path(doc_path_or_id)
        if doc:
            for tag in tag_names:
                self.tags.add_tag_to_document(doc.doc_id, tag)

    def create_view(self, name: str, query: str, description: str = '',
                    filters: Optional[Dict] = None) -> View:
        """Create a saved search view."""
        return self.views.create_view(name, query, description, filters)

    def execute_view(self, view_name: str, limit: int = 20) -> List[SearchResult]:
        """Execute a saved view."""
        view = self.views.get_view_by_name(view_name)
        if view is None:
            return []
        return self.search_engine.search(view.query, limit=limit, filters=view.filters)

    def mine_relations(self, doc_path_or_id: str) -> List[Relation]:
        """Mine relations for a document."""
        doc = self.documents.get_document(doc_path_or_id)
        if doc is None:
            doc = self.documents.get_document_by_path(doc_path_or_id)
        if doc:
            return self.relations.mine_relations(doc.doc_id)
        return []

    def add_journal_entry(self, content: str, tags: Optional[List[str]] = None,
                          linked_docs: Optional[List[str]] = None) -> JournalEntry:
        """Add a journal entry."""
        return self.journal.create_entry(content, tags=tags, linked_docs=linked_docs)

    # ---- Notes ----

    def get_note(self, note_id: str) -> Optional[InvestigationNote]:
        """Get an investigation note by ID."""
        return self.notes.get_note(note_id)

    def list_notes(self, limit: int = 20) -> List[InvestigationNote]:
        """List recent investigation notes."""
        return self.notes.list_notes(limit=limit)

    def search_notes(self, query: str) -> List[InvestigationNote]:
        """Search investigation notes."""
        return self.notes.search_notes(query)

    def export_note(self, note_id: str, output_path: str, format: str = 'markdown'):
        """Export an investigation note."""
        self.notes.export_note(note_id, output_path, format)

    # ---- Stats & Info ----

    def stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        doc_stats = self.documents.get_document_stats()
        catalog_count = len(self.catalogs.list_catalogs())
        tag_count = len(self.tags.list_all_tags())
        note_count = len(self.notes.list_notes(limit=100000))
        journal_count = len(self.journal.list_entries(limit=100000))
        return {
            **doc_stats,
            'catalogs': catalog_count,
            'tags': tag_count,
            'investigation_notes': note_count,
            'journal_entries': journal_count,
            'vault_path': self.vault_path,
            'db_path': self.db_path,
        }

    def list_documents(self, limit: int = 50, **kwargs) -> List[DocumentRecord]:
        """List documents in the knowledge base."""
        return self.documents.list_documents(limit=limit, **kwargs)

    def get_document(self, doc_path_or_id: str) -> Optional[DocumentRecord]:
        """Get a document by path or ID."""
        doc = self.documents.get_document(doc_path_or_id)
        if doc is None:
            doc = self.documents.get_document_by_path(doc_path_or_id)
        return doc

    def read_document(self, doc_path_or_id: str,
                      page: Optional[int] = None,
                      lines: Optional[Tuple[int, int]] = None,
                      section: Optional[str] = None) -> str:
        """
        Read content from a document.

        Args:
            doc_path_or_id: Document path or ID
            page: Page number to read
            lines: (start, end) line numbers to read
            section: Section name to read

        Returns:
            Document content as string
        """
        doc = self.get_document(doc_path_or_id)
        if doc is None:
            return ''

        if page is not None:
            return self.reader.read_page(doc.file_path, page)
        elif lines is not None:
            return self.reader.read_lines(doc.file_path, lines[0], lines[1])
        elif section is not None:
            return self.reader.read_section(doc.file_path, section)
        else:
            # Read full document
            extraction = self.extractor.extract(doc.file_path)
            return extraction.get('text', '')

    def __repr__(self) -> str:
        stats = self.stats()
        return (
            f"Marginalia(vault='{self.vault_path}', "
            f"docs={stats['total_documents']}, "
            f"chunks={stats['total_chunks']})"
        )


# ============================================================
# CLI Interface
# ============================================================

class CLI:
    """Command-line interface for Marginalia."""

    def __init__(self, vault_path: str = '.', **kwargs):
        self.marginalia = Marginalia(vault_path, **kwargs)

    def run(self, args: Optional[List[str]] = None):
        """Run the CLI."""
        import sys
        if args is None:
            args = sys.argv[1:]

        if not args:
            self._print_help()
            return

        command = args[0]
        rest = args[1:]

        commands = {
            'ingest': self._cmd_ingest,
            'search': self._cmd_search,
            'ask': self._cmd_ask,
            'report': self._cmd_report,
            'stats': self._cmd_stats,
            'list': self._cmd_list,
            'sync': self._cmd_sync,
            'catalog': self._cmd_catalog,
            'tag': self._cmd_tag,
            'note': self._cmd_note,
            'journal': self._cmd_journal,
            'read': self._cmd_read,
            'help': lambda _: self._print_help(),
        }

        handler = commands.get(command)
        if handler:
            handler(rest)
        else:
            print(f"Unknown command: {command}")
            self._print_help()

    def _cmd_ingest(self, args: List[str]):
        if not args:
            print("Usage: ingest <path> [--catalog <name>] [--tags <tag1,tag2>]")
            return
        path = args[0]
        catalog = None
        tags = None
        i = 1
        while i < len(args):
            if args[i] == '--catalog' and i + 1 < len(args):
                catalog = args[i + 1]
                i += 2
            elif args[i] == '--tags' and i + 1 < len(args):
                tags = args[i + 1].split(',')
                i += 2
            else:
                i += 1
        result = self.marginalia.ingest(path, catalog=catalog, tags=tags)
        if isinstance(result, list):
            print(f"Ingested {len(result)} documents")
        elif result:
            print(f"Ingested: {result.title} ({result.doc_type})")
        else:
            print("Ingestion failed")

    def _cmd_search(self, args: List[str]):
        if not args:
            print("Usage: search <query> [--limit <n>] [--type <doc_type>]")
            return
        query = args[0]
        limit = 10
        doc_type = None
        i = 1
        while i < len(args):
            if args[i] == '--limit' and i + 1 < len(args):
                limit = int(args[i + 1])
                i += 2
            elif args[i] == '--type' and i + 1 < len(args):
                doc_type = args[i + 1]
                i += 2
            else:
                i += 1
        results = self.marginalia.search(query, limit=limit, doc_type=doc_type)
        print(f"\nSearch results for: '{query}' ({len(results)} found)\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. [{r.match_type}] {r.doc.title} (score: {r.score:.3f})")
            if r.doc.page_count > 1 and r.chunk.page_number:
                print(f"   Page {r.chunk.page_number}")
            if r.chunk.section:
                print(f"   Section: {r.chunk.section}")
            print(f"   {r.snippet[:100]}...")
            print()

    def _cmd_ask(self, args: List[str]):
        if not args:
            print("Usage: ask <question> [--catalog <name>] [--sources <n>]")
            return
        question = args[0]
        catalog = None
        max_sources = 5
        i = 1
        while i < len(args):
            if args[i] == '--catalog' and i + 1 < len(args):
                catalog = args[i + 1]
                i += 2
            elif args[i] == '--sources' and i + 1 < len(args):
                max_sources = int(args[i + 1])
                i += 2
            else:
                i += 1
        print(f"\nResearching: {question}\n")
        result = self.marginalia.ask(question, catalog=catalog, max_sources=max_sources)
        print(result['answer'])
        print(f"\n[Consulted {result['sources_consulted']} sources, note saved: {result['note_id']}]")

    def _cmd_report(self, args: List[str]):
        if not args:
            print("Usage: report <topic> [--catalog <name>]")
            return
        topic = args[0]
        catalog = None
        i = 1
        while i < len(args):
            if args[i] == '--catalog' and i + 1 < len(args):
                catalog = args[i + 1]
                i += 2
            else:
                i += 1
        print(f"\nGenerating report on: {topic}\n")
        result = self.marginalia.report(topic, catalog=catalog)
        print(result['report'])

    def _cmd_stats(self, args: List[str]):
        stats = self.marginalia.stats()
        print("\n=== Marginalia Knowledge Base Statistics ===")
        print(f"Vault: {stats['vault_path']}")
        print(f"Documents: {stats['total_documents']}")
        print(f"Chunks: {stats['total_chunks']}")
        print(f"Words: {stats['total_words']:,}")
        print(f"Catalogs: {stats['catalogs']}")
        print(f"Tags: {stats['tags']}")
        print(f"Investigation Notes: {stats['investigation_notes']}")
        print(f"Journal Entries: {stats['journal_entries']}")
        if stats.get('by_type'):
            print("\nBy Type:")
            for doc_type, count in sorted(stats['by_type'].items()):
                print(f"  {doc_type}: {count}")

    def _cmd_list(self, args: List[str]):
        limit = 20
        if args and args[0].isdigit():
            limit = int(args[0])
        docs = self.marginalia.list_documents(limit=limit)
        print(f"\n=== Documents ({len(docs)} shown) ===")
        for doc in docs:
            print(f"  [{doc.doc_type}] {doc.title}")
            print(f"    {doc.file_path}")
            if doc.tags:
                print(f"    Tags: {', '.join(doc.tags)}")

    def _cmd_sync(self, args: List[str]):
        path = args[0] if args else None
        print("Syncing vault...")
        counts = self.marginalia.sync(path)
        print(f"Sync complete: {counts['added']} added, {counts['updated']} updated, {counts['removed']} removed")

    def _cmd_catalog(self, args: List[str]):
        if not args:
            catalogs = self.marginalia.catalogs.list_catalogs()
            print(f"\n=== Catalogs ({len(catalogs)}) ===")
            for cat in catalogs:
                docs = self.marginalia.catalogs.get_catalog_documents(cat.catalog_id)
                print(f"  {cat.name}: {len(docs)} documents")
                if cat.description:
                    print(f"    {cat.description}")
        elif args[0] == 'create' and len(args) > 1:
            cat = self.marginalia.create_catalog(args[1], ' '.join(args[2:]))
            print(f"Created catalog: {cat.name}")

    def _cmd_tag(self, args: List[str]):
        if not args:
            tags = self.marginalia.tags.list_all_tags()
            print(f"\n=== Tags ({len(tags)}) ===")
            for tag in tags:
                print(f"  {tag['name']}: {tag['count']} documents")
        elif len(args) >= 2:
            doc_path = args[0]
            tag_names = args[1:]
            self.marginalia.tag_document(doc_path, *tag_names)
            print(f"Tagged {doc_path} with: {', '.join(tag_names)}")

    def _cmd_note(self, args: List[str]):
        if not args or args[0] == 'list':
            notes = self.marginalia.list_notes(limit=10)
            print(f"\n=== Recent Investigation Notes ({len(notes)}) ===")
            for note in notes:
                print(f"  [{note.note_id[:8]}] {note.query[:60]}")
                print(f"    {note.created_at}")
        elif args[0] == 'show' and len(args) > 1:
            note = self.marginalia.get_note(args[1])
            if note:
                print(f"\nQuery: {note.query}")
                print(f"Created: {note.created_at}")
                print(f"\n{note.answer}")
            else:
                print(f"Note not found: {args[1]}")
        elif args[0] == 'search' and len(args) > 1:
            query = ' '.join(args[1:])
            notes = self.marginalia.search_notes(query)
            print(f"\nFound {len(notes)} notes matching '{query}'")
            for note in notes:
                print(f"  [{note.note_id[:8]}] {note.query[:60]}")

    def _cmd_journal(self, args: List[str]):
        if not args or args[0] == 'list':
            entries = self.marginalia.journal.list_entries(limit=10)
            print(f"\n=== Recent Journal Entries ({len(entries)}) ===")
            for entry in entries:
                print(f"  [{entry.entry_id[:8]}] {entry.created_at}")
                print(f"    {entry.content[:80]}...")
        elif args[0] == 'add' and len(args) > 1:
            content = ' '.join(args[1:])
            entry = self.marginalia.add_journal_entry(content)
            print(f"Journal entry created: {entry.entry_id[:8]}")

    def _cmd_read(self, args: List[str]):
        if not args:
            print("Usage: read <path_or_id> [--page <n>] [--lines <start>-<end>] [--section <name>]")
            return
        doc_ref = args[0]
        page = None
        lines = None
        section = None
        i = 1
        while i < len(args):
            if args[i] == '--page' and i + 1 < len(args):
                page = int(args[i + 1])
                i += 2
            elif args[i] == '--lines' and i + 1 < len(args):
                parts = args[i + 1].split('-')
                lines = (int(parts[0]), int(parts[1]))
                i += 2
            elif args[i] == '--section' and i + 1 < len(args):
                section = args[i + 1]
                i += 2
            else:
                i += 1
        content = self.marginalia.read_document(doc_ref, page=page, lines=lines, section=section)
        print(content)

    def _print_help(self):
        print("""
Marginalia - Personal Knowledge Management System

Commands:
  ingest <path>           Ingest a file or directory
  search <query>          Search the knowledge base
  ask <question>          Ask a question (cited answer)
  report <topic>          Generate a research report
  stats                   Show knowledge base statistics
  list [n]                List documents
  sync [path]             Sync vault with filesystem
  catalog [create <name>] Manage catalogs
  tag <doc> <tags...>     Tag a document
  note [list|show|search] Manage investigation notes
  journal [list|add]      Manage journal entries
  read <doc>              Read document content
  help                    Show this help

Options:
  --catalog <name>        Filter by catalog
  --tags <t1,t2>          Filter by tags
  --limit <n>             Limit results
  --type <type>           Filter by document type
  --sources <n>           Max sources for agent
  --page <n>              Read specific page
  --lines <s>-<e>         Read specific lines
  --section <name>        Read specific section
""")


# ============================================================
# Entry Point
# ============================================================

def main():
    """Main entry point."""
    import sys
    import os

    vault_path = os.environ.get('MARGINALIA_VAULT', '.')
    llm_provider = os.environ.get('MARGINALIA_LLM', 'anthropic')
    llm_model = os.environ.get('MARGINALIA_MODEL', None)

    cli = CLI(
        vault_path=vault_path,
        llm_provider=llm_provider,
        llm_model=llm_model,
    )
    cli.run()


if __name__ == '__main__':
    main()