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
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from docx import Document as DocxDocument
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
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

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
class FileRecord:
    """Represents a file in the knowledge base."""
    file_id: str
    path: str
    filename: str
    extension: str
    mime_type: str
    size_bytes: int
    checksum: str
    created_at: str
    modified_at: str
    ingested_at: str
    catalog_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_count: int = 0


@dataclass
class Chunk:
    """A text chunk extracted from a file."""
    chunk_id: str
    file_id: str
    content: str
    chunk_type: str  # text, page, line, table_row, archive_member, image_ocr
    position: int    # page number, line number, row index, etc.
    start_char: int
    end_char: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class Catalog:
    """A named collection of files (like a library catalog)."""
    catalog_id: str
    name: str
    description: str
    created_at: str
    parent_catalog_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Tag:
    """A tag for organizing files."""
    tag_id: str
    name: str
    color: str
    description: str
    created_at: str
    parent_tag_id: Optional[str] = None


@dataclass
class View:
    """A saved search/filter configuration."""
    view_id: str
    name: str
    description: str
    query: str
    filters: Dict[str, Any]
    sort_by: str
    created_at: str
    updated_at: str


@dataclass
class Relation:
    """A relationship between two files."""
    relation_id: str
    source_file_id: str
    target_file_id: str
    relation_type: str  # cites, references, similar_to, part_of, etc.
    confidence: float
    evidence: str
    created_at: str
    auto_detected: bool = False


@dataclass
class JournalEntry:
    """A research journal entry."""
    entry_id: str
    title: str
    content: str
    created_at: str
    updated_at: str
    tags: List[str] = field(default_factory=list)
    cited_files: List[str] = field(default_factory=list)
    investigation_id: Optional[str] = None


@dataclass
class Investigation:
    """A durable investigation note from an agent session."""
    investigation_id: str
    query: str
    answer: str
    citations: List[Dict[str, Any]]
    sources_used: List[str]
    created_at: str
    updated_at: str
    tags: List[str] = field(default_factory=list)
    follow_up_questions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """A search result with relevance scoring."""
    chunk: Chunk
    file_record: FileRecord
    score: float
    match_type: str  # lexical, semantic, reranked
    snippet: str
    highlights: List[str] = field(default_factory=list)


@dataclass
class Citation:
    """A citation in an agent answer."""
    file_id: str
    filename: str
    path: str
    chunk_id: str
    position: int
    chunk_type: str
    excerpt: str
    relevance_score: float


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
            CREATE TABLE IF NOT EXISTS files (
                file_id TEXT PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                extension TEXT,
                mime_type TEXT,
                size_bytes INTEGER,
                checksum TEXT,
                created_at TEXT,
                modified_at TEXT,
                ingested_at TEXT,
                catalog_id TEXT,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                chunk_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_type TEXT,
                position INTEGER,
                start_char INTEGER,
                end_char INTEGER,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                file_id UNINDEXED,
                content,
                content='chunks',
                content_rowid='rowid'
            );

            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id TEXT PRIMARY KEY,
                embedding BLOB,
                model TEXT,
                created_at TEXT,
                FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS catalogs (
                catalog_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT,
                parent_catalog_id TEXT,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS tags (
                tag_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                color TEXT DEFAULT '#808080',
                description TEXT,
                created_at TEXT,
                parent_tag_id TEXT
            );

            CREATE TABLE IF NOT EXISTS file_tags (
                file_id TEXT NOT NULL,
                tag_id TEXT NOT NULL,
                PRIMARY KEY (file_id, tag_id),
                FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS views (
                view_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                query TEXT,
                filters TEXT DEFAULT '{}',
                sort_by TEXT DEFAULT 'ingested_at',
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS relations (
                relation_id TEXT PRIMARY KEY,
                source_file_id TEXT NOT NULL,
                target_file_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                evidence TEXT,
                created_at TEXT,
                auto_detected INTEGER DEFAULT 0,
                FOREIGN KEY (source_file_id) REFERENCES files(file_id) ON DELETE CASCADE,
                FOREIGN KEY (target_file_id) REFERENCES files(file_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                entry_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                created_at TEXT,
                updated_at TEXT,
                tags TEXT DEFAULT '[]',
                cited_files TEXT DEFAULT '[]',
                investigation_id TEXT
            );

            CREATE TABLE IF NOT EXISTS investigations (
                investigation_id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                answer TEXT,
                citations TEXT DEFAULT '[]',
                sources_used TEXT DEFAULT '[]',
                created_at TEXT,
                updated_at TEXT,
                tags TEXT DEFAULT '[]',
                follow_up_questions TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_files_catalog ON files(catalog_id);
            CREATE INDEX IF NOT EXISTS idx_files_extension ON files(extension);
            CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_id);
            CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_file_id);
            CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_file_id);
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


# ─────────────────────────────────────────────────────────────────────────────
# File Ingestion
# ─────────────────────────────────────────────────────────────────────────────

class TextExtractor:
    """Extracts text content from various file types."""

    def extract(self, path: str) -> List[Chunk]:
        """Extract chunks from a file based on its type."""
        ext = Path(path).suffix.lower()
        mime, _ = mimetypes.guess_type(path)

        if ext in ('.txt', '.md', '.rst', '.log', '.csv', '.tsv'):
            return self._extract_text(path, ext)
        elif ext == '.pdf':
            return self._extract_pdf(path)
        elif ext in ('.docx', '.doc'):
            return self._extract_docx(path)
        elif ext in ('.xlsx', '.xls', '.ods'):
            return self._extract_spreadsheet(path)
        elif ext in ('.zip', '.tar', '.gz', '.bz2', '.7z'):
            return self._extract_archive(path)
        elif ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'):
            return self._extract_image(path)
        elif mime and mime.startswith('text/'):
            return self._extract_text(path, ext)
        else:
            return self._extract_text_fallback(path)

    def _extract_text(self, path: str, ext: str) -> List[Chunk]:
        chunks = []
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            if ext == '.md':
                chunks = self._chunk_markdown(content, path)
            elif ext in ('.log',):
                chunks = self._chunk_lines(content, path)
            elif ext in ('.csv', '.tsv'):
                chunks = self._chunk_csv(path)
            else:
                chunks = self._chunk_paragraphs(content, path)
        except Exception as e:
            logger.warning(f"Text extraction failed for {path}: {e}")
        return chunks

    def _chunk_paragraphs(self, content: str, path: str) -> List[Chunk]:
        chunks = []
        paragraphs = re.split(r'\n\s*\n', content)
        pos = 0
        for i, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                pos += len(para) + 2
                continue
            start = content.find(para, pos)
            end = start + len(para)
            chunk = Chunk(
                chunk_id=str(uuid.uuid4()),
                file_id='',
                content=para,
                chunk_type='paragraph',
                position=i,
                start_char=start,
                end_char=end,
                metadata={'paragraph_index': i}
            )
            chunks.append(chunk)
            pos = end
        return chunks if chunks else [Chunk(
            chunk_id=str(uuid.uuid4()),
            file_id='',
            content=content,
            chunk_type='text',
            position=0,
            start_char=0,
            end_char=len(content)
        )]

    def _chunk_markdown(self, content: str, path: str) -> List[Chunk]:
        chunks = []
        sections = re.split(r'(?m)^(#{1,6}\s+.+)$', content)
        pos = 0
        section_idx = 0
        current_heading = ''

        for part in sections:
            if re.match(r'^#{1,6}\s+', part):
                current_heading = part.strip()
            elif part.strip():
                start = content.find(part, pos)
                end = start + len(part)
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    file_id='',
                    content=part.strip(),
                    chunk_type='section',
                    position=section_idx,
                    start_char=start,
                    end_char=end,
                    metadata={'heading': current_heading}
                )
                chunks.append(chunk)
                section_idx += 1
                pos = end

        return chunks if chunks else self._chunk_paragraphs(content, path)

    def _chunk_lines(self, content: str, path: str) -> List[Chunk]:
        chunks = []
        lines = content.splitlines()
        pos = 0
        for i, line in enumerate(lines):
            if line.strip():
                start = content.find(line, pos)
                end = start + len(line)
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    file_id='',
                    content=line,
                    chunk_type='line',
                    position=i,
                    start_char=start,
                    end_char=end,
                    metadata={'line_number': i + 1}
                )
                chunks.append(chunk)
                pos = end
        return chunks

    def _chunk_csv(self, path: str) -> List[Chunk]:
        chunks = []
        if not HAS_CSV:
            return chunks
        try:
            import csv as csv_module
            ext = Path(path).suffix.lower()
            delimiter = '\t' if ext == '.tsv' else ','
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv_module.DictReader(f, delimiter=delimiter)
                headers = reader.fieldnames or []
                for i, row in enumerate(reader):
                    content = ' | '.join(f"{k}: {v}" for k, v in row.items() if v)
                    if content.strip():
                        chunk = Chunk(
                            chunk_id=str(uuid.uuid4()),
                            file_id='',
                            content=content,
                            chunk_type='table_row',
                            position=i,
                            start_char=0,
                            end_char=len(content),
                            metadata={'row_index': i, 'headers': headers, 'row_data': dict(row)}
                        )
                        chunks.append(chunk)
        except Exception as e:
            logger.warning(f"CSV extraction failed for {path}: {e}")
        return chunks

    def _extract_pdf(self, path: str) -> List[Chunk]:
        chunks = []
        if not HAS_PYMUPDF:
            logger.warning(f"PyMuPDF not available, skipping PDF: {path}")
            return chunks
        try:
            doc = fitz.open(path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    chunk = Chunk(
                        chunk_id=str(uuid.uuid4()),
                        file_id='',
                        content=text.strip(),
                        chunk_type='page',
                        position=page_num,
                        start_char=0,
                        end_char=len(text),
                        metadata={'page_number': page_num + 1, 'total_pages': len(doc)}
                    )
                    chunks.append(chunk)
            doc.close()
        except Exception as e:
            logger.warning(f"PDF extraction failed for {path}: {e}")
        return chunks

    def _extract_docx(self, path: str) -> List[Chunk]:
        chunks = []
        if not HAS_DOCX:
            logger.warning(f"python-docx not available, skipping DOCX: {path}")
            return chunks
        try:
            doc = DocxDocument(path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            pos = 0
            for i, para_text in enumerate(paragraphs):
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    file_id='',
                    content=para_text,
                    chunk_type='paragraph',
                    position=i,
                    start_char=pos,
                    end_char=pos + len(para_text),
                    metadata={'paragraph_index': i}
                )
                chunks.append(chunk)
                pos += len(para_text) + 1
        except Exception as e:
            logger.warning(f"DOCX extraction failed for {path}: {e}")
        return chunks

    def _extract_spreadsheet(self, path: str) -> List[Chunk]:
        chunks = []
        if not HAS_OPENPYXL:
            logger.warning(f"openpyxl not available, skipping spreadsheet: {path}")
            return chunks
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                headers = []
                for i, row in enumerate(ws.iter_rows(values_only=True)):
                    if i == 0:
                        headers = [str(c) if c is not None else '' for c in row]
                        continue
                    row_data = {headers[j]: str(v) if v is not None else '' for j, v in enumerate(row) if j < len(headers)}
                    content = ' | '.join(f"{k}: {v}" for k, v in row_data.items() if v)
                    if content.strip():
                        chunk = Chunk(
                            chunk_id=str(uuid.uuid4()),
                            file_id='',
                            content=content,
                            chunk_type='table_row',
                            position=i - 1,
                            start_char=0,
                            end_char=len(content),
                            metadata={'sheet': sheet_name, 'row_index': i, 'headers': headers, 'row_data': row_data}
                        )
                        chunks.append(chunk)
            wb.close()
        except Exception as e:
            logger.warning(f"Spreadsheet extraction failed for {path}: {e}")
        return chunks

    def _extract_archive(self, path: str) -> List[Chunk]:
        chunks = []
        ext = Path(path).suffix.lower()
        try:
            members = []
            if ext == '.zip':
                with zipfile.ZipFile(path, 'r') as zf:
                    for info in zf.infolist():
                        if not info.is_dir():
                            try:
                                with zf.open(info) as f:
                                    content = f.read(8192).decode('utf-8', errors='replace')
                                members.append((info.filename, content, info.file_size))
                            except Exception:
                                members.append((info.filename, '[binary content]', info.file_size))
            elif tarfile.is_tarfile(path):
                with tarfile.open(path, 'r:*') as tf:
                    for member in tf.getmembers():
                        if member.isfile():
                            try:
                                f = tf.extractfile(member)
                                if f:
                                    content = f.read(8192).decode('utf-8', errors='replace')
                                    members.append((member.name, content, member.size))
                            except Exception:
                                members.append((member.name, '[binary content]', member.size))

            for i, (name, content, size) in enumerate(members):
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    file_id='',
                    content=f"Archive member: {name}\n{content}",
                    chunk_type='archive_member',
                    position=i,
                    start_char=0,
                    end_char=len(content),
                    metadata={'member_name': name, 'member_size': size}
                )
                chunks.append(chunk)
        except Exception as e:
            logger.warning(f"Archive extraction failed for {path}: {e}")
        return chunks

    def _extract_image(self, path: str) -> List[Chunk]:
        chunks = []
        if not HAS_OCR:
            logger.warning(f"PIL/pytesseract not available, skipping image OCR: {path}")
            chunk = Chunk(
                chunk_id=str(uuid.uuid4()),
                file_id='',
                content=f"[Image file: {Path(path).name}]",
                chunk_type='image_ocr',
                position=0,
                start_char=0,
                end_char=0,
                metadata={'ocr_available': False}
            )
            return [chunk]
        try:
            img = Image.open(path)
            text = pytesseract.image_to_string(img)
            if text.strip():
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    file_id='',
                    content=text.strip(),
                    chunk_type='image_ocr',
                    position=0,
                    start_char=0,
                    end_char=len(text),
                    metadata={'image_size': img.size, 'image_mode': img.mode}
                )
                chunks.append(chunk)
        except Exception as e:
            logger.warning(f"Image OCR failed for {path}: {e}")
        return chunks

    def _extract_text_fallback(self, path: str) -> List[Chunk]:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(65536)
            if content.strip():
                return self._chunk_paragraphs(content, path)
        except Exception:
            pass
        return []


class FileIngester:
    """Ingests files into the knowledge base."""

    def __init__(self, db: Database, vault_path: str):
        self.db = db
        self.vault_path = vault_path
        self.extractor = TextExtractor()

    def _compute_checksum(self, path: str) -> str:
        h = hashlib.sha256()
        try:
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    h.update(chunk)
        except Exception:
            pass
        return h.hexdigest()

    def _get_file_times(self, path: str) -> Tuple[str, str]:
        stat = os.stat(path)
        created = datetime.datetime.fromtimestamp(stat.st_ctime).isoformat()
        modified = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
        return created, modified

    def ingest_file(self, path: str, catalog_id: Optional[str] = None,
                    tags: Optional[List[str]] = None) -> Optional[FileRecord]:
        """Ingest a single file into the knowledge base."""
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            logger.error(f"File not found: {path}")
            return None

        # Check if already ingested
        existing = self.db.fetchone("SELECT file_id, checksum FROM files WHERE path = ?", (path,))
        checksum = self._compute_checksum(path)

        if existing and existing['checksum'] == checksum:
            logger.info(f"File unchanged, skipping: {path}")
            return self._load_file_record(existing['file_id'])

        file_id = str(uuid.uuid4()) if not existing else existing['file_id']
        filename = os.path.basename(path)
        ext = Path(path).suffix.lower()
        mime, _ = mimetypes.guess_type(path)
        size = os.path.getsize(path)
        created_at, modified_at = self._get_file_times(path)
        ingested_at = datetime.datetime.now().isoformat()

        # Extract chunks
        chunks = self.extractor.extract(path)
        for chunk in chunks:
            chunk.file_id = file_id

        # Store file record
        self.db.execute("""
            INSERT OR REPLACE INTO files
            (file_id, path, filename, extension, mime_type, size_bytes, checksum,
             created_at, modified_at, ingested_at, catalog_id, tags, metadata, chunk_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (file_id, path, filename, ext, mime or 'application/octet-stream',
              size, checksum, created_at, modified_at, ingested_at,
              catalog_id, json.dumps(tags or []), json.dumps({}), len(chunks)))

        # Delete old chunks if re-ingesting
        if existing:
            self.db.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))

        # Store chunks
        for chunk in chunks:
            self.db.execute("""
                INSERT INTO chunks (chunk_id, file_id, content, chunk_type, position, start_char, end_char, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (chunk.chunk_id, chunk.file_id, chunk.content, chunk.chunk_type,
                  chunk.position, chunk.start_char, chunk.end_char, json.dumps(chunk.metadata)))

        # Update FTS index
        self.db.execute("DELETE FROM chunks_fts WHERE file_id = ?", (file_id,))
        for chunk in chunks:
            self.db.execute("""
                INSERT INTO chunks_fts (chunk_id, file_id, content)
                VALUES (?, ?, ?)
            """, (chunk.chunk_id, chunk.file_id, chunk.content))

        self.db.commit()

        record = FileRecord(
            file_id=file_id,
            path=path,
            filename=filename,
            extension=ext,
            mime_type=mime or 'application/octet-stream',
            size_bytes=size,
            checksum=checksum,
            created_at=created_at,
            modified_at=modified_at,
            ingested_at=ingested_at,
            catalog_id=catalog_id,
            tags=tags or [],
            metadata={},
            chunk_count=len(chunks)
        )

        logger.info(f"Ingested: {filename} ({len(chunks)} chunks)")
        return record

    def ingest_directory(self, directory: str, recursive: bool = True,
                         catalog_id: Optional[str] = None,
                         extensions: Optional[List[str]] = None) -> List[FileRecord]:
        """Ingest all files in a directory."""
        records = []
        directory = os.path.abspath(directory)

        if recursive:
            walker = os.walk(directory)
        else:
            walker = [(directory, [], os.listdir(directory))]

        for root, dirs, files in walker:
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for filename in files:
                if filename.startswith('.'):
                    continue
                filepath = os.path.join(root, filename)
                ext = Path(filepath).suffix.lower()
                if extensions and ext not in extensions:
                    continue
                record = self.ingest_file(filepath, catalog_id=catalog_id)
                if record:
                    records.append(record)

        return records

    def _load_file_record(self, file_id: str) -> Optional[FileRecord]:
        row = self.db.fetchone("SELECT * FROM files WHERE file_id = ?", (file_id,))
        if not row:
            return None
        return FileRecord(
            file_id=row['file_id'],
            path=row['path'],
            filename=row['filename'],
            extension=row['extension'],
            mime_type=row['mime_type'],
            size_bytes=row['size_bytes'],
            checksum=row['checksum'],
            created_at=row['created_at'],
            modified_at=row['modified_at'],
            ingested_at=row['ingested_at'],
            catalog_id=row['catalog_id'],
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}'),
            chunk_count=row['chunk_count']
        )


# ─────────────────────────────────────────────────────────────────────────────
# Catalog & Organization
# ─────────────────────────────────────────────────────────────────────────────

class CatalogManager:
    """Manages catalogs (collections) of files."""

    def __init__(self, db: Database):
        self.db = db

    def create_catalog(self, name: str, description: str = '',
                       parent_catalog_id: Optional[str] = None,
                       tags: Optional[List[str]] = None) -> Catalog:
        catalog_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()
        self.db.execute("""
            INSERT INTO catalogs (catalog_id, name, description, created_at, parent_catalog_id, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (catalog_id, name, description, created_at, parent_catalog_id,
              json.dumps(tags or []), json.dumps({})))
        self.db.commit()
        return Catalog(catalog_id=catalog_id, name=name, description=description,
                       created_at=created_at, parent_catalog_id=parent_catalog_id,
                       tags=tags or [])

    def get_catalog(self, catalog_id: str) -> Optional[Catalog]:
        row = self.db.fetchone("SELECT * FROM catalogs WHERE catalog_id = ?", (catalog_id,))
        if not row:
            return None
        return Catalog(
            catalog_id=row['catalog_id'],
            name=row['name'],
            description=row['description'],
            created_at=row['created_at'],
            parent_catalog_id=row['parent_catalog_id'],
            tags=json.loads(row['tags'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}')
        )

    def list_catalogs(self) -> List[Catalog]:
        rows = self.db.fetchall("SELECT * FROM catalogs ORDER BY name")
        return [Catalog(
            catalog_id=r['catalog_id'],
            name=r['name'],
            description=r['description'],
            created_at=r['created_at'],
            parent_catalog_id=r['parent_catalog_id'],
            tags=json.loads(r['tags'] or '[]'),
            metadata=json.loads(r['metadata'] or '{}')
        ) for r in rows]

    def assign_file_to_catalog(self, file_id: str, catalog_id: str):
        self.db.execute("UPDATE files SET catalog_id = ? WHERE file_id = ?", (catalog_id, file_id))
        self.db.commit()

    def get_catalog_files(self, catalog_id: str) -> List[str]:
        rows = self.db.fetchall("SELECT file_id FROM files WHERE catalog_id = ?", (catalog_id,))
        return [r['file_id'] for r in rows]

    def delete_catalog(self, catalog_id: str):
        self.db.execute("UPDATE files SET catalog_id = NULL WHERE catalog_id = ?", (catalog_id,))
        self.db.execute("DELETE FROM catalogs WHERE catalog_id = ?", (catalog_id,))
        self.db.commit()


class TagManager:
    """Manages tags for organizing files."""

    def __init__(self, db: Database):
        self.db = db

    def create_tag(self, name: str, color: str = '#808080',
                   description: str = '', parent_tag_id: Optional[str] = None) -> Tag:
        tag_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()
        self.db.execute("""
            INSERT OR IGNORE INTO tags (tag_id, name, color, description, created_at, parent_tag_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (tag_id, name, color, description, created_at, parent_tag_id))
        self.db.commit()
        # Return existing if name collision
        row = self.db.fetchone("SELECT * FROM tags WHERE name = ?", (name,))
        return Tag(tag_id=row['tag_id'], name=row['name'], color=row['color'],
                   description=row['description'], created_at=row['created_at'],
                   parent_tag_id=row['parent_tag_id'])

    def get_or_create_tag(self, name: str) -> Tag:
        row = self.db.fetchone("SELECT * FROM tags WHERE name = ?", (name,))
        if row:
            return Tag(tag_id=row['tag_id'], name=row['name'], color=row['color'],
                       description=row['description'], created_at=row['created_at'],
                       parent_tag_id=row['parent_tag_id'])
        return self.create_tag(name)

    def tag_file(self, file_id: str, tag_name: str):
        tag = self.get_or_create_tag(tag_name)
        self.db.execute("INSERT OR IGNORE INTO file_tags (file_id, tag_id) VALUES (?, ?)",
                        (file_id, tag.tag_id))
        # Update tags JSON in files table
        row = self.db.fetchone("SELECT tags FROM files WHERE file_id = ?", (file_id,))
        if row:
            tags = json.loads(row['tags'] or '[]')
            if tag_name not in tags:
                tags.append(tag_name)
            self.db.execute("UPDATE files SET tags = ? WHERE file_id = ?",
                            (json.dumps(tags), file_id))
        self.db.commit()

    def untag_file(self, file_id: str, tag_name: str):
        row = self.db.fetchone("SELECT tag_id FROM tags WHERE name = ?", (tag_name,))
        if row:
            self.db.execute("DELETE FROM file_tags WHERE file_id = ? AND tag_id = ?",
                            (file_id, row['tag_id']))
        file_row = self.db.fetchone("SELECT tags FROM files WHERE file_id = ?", (file_id,))
        if file_row:
            tags = json.loads(file_row['tags'] or '[]')
            tags = [t for t in tags if t != tag_name]
            self.db.execute("UPDATE files SET tags = ? WHERE file_id = ?",
                            (json.dumps(tags), file_id))
        self.db.commit()

    def get_file_tags(self, file_id: str) -> List[Tag]:
        rows = self.db.fetchall("""
            SELECT t.* FROM tags t
            JOIN file_tags ft ON t.tag_id = ft.tag_id
            WHERE ft.file_id = ?
        """, (file_id,))
        return [Tag(tag_id=r['tag_id'], name=r['name'], color=r['color'],
                    description=r['description'], created_at=r['created_at'],
                    parent_tag_id=r['parent_tag_id']) for r in rows]

    def get_files_by_tag(self, tag_name: str) -> List[str]:
        rows = self.db.fetchall("""
            SELECT ft.file_id FROM file_tags ft
            JOIN tags t ON ft.tag_id = t.tag_id
            WHERE t.name = ?
        """, (tag_name,))
        return [r['file_id'] for r in rows]

    def list_tags(self) -> List[Tag]:
        rows = self.db.fetchall("SELECT * FROM tags ORDER BY name")
        return [Tag(tag_id=r['tag_id'], name=r['name'], color=r['color'],
                    description=r['description'], created_at=r['created_at'],
                    parent_tag_id=r['parent_tag_id']) for r in rows]


class ViewManager:
    """Manages saved views (search configurations)."""

    def __init__(self, db: Database):
        self.db = db

    def create_view(self, name: str, query: str = '', description: str = '',
                    filters: Optional[Dict] = None, sort_by: str = 'ingested_at') -> View:
        view_id = str(uuid.uuid4())
        now = datetime.datetime.now().isoformat()
        self.db.execute("""
            INSERT INTO views (view_id, name, description, query, filters, sort_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (view_id, name, description, query, json.dumps(filters or {}), sort_by, now, now))
        self.db.commit()
        return View(view_id=view_id, name=name, description=description,
                    query=query, filters=filters or {}, sort_by=sort_by,
                    created_at=now, updated_at=now)

    def get_view(self, view_id: str) -> Optional[View]:
        row = self.db.fetchone("SELECT * FROM views WHERE view_id = ?", (view_id,))
        if not row:
            return None
        return View(view_id=row['view_id'], name=row['name'], description=row['description'],
                    query=row['query'], filters=json.loads(row['filters'] or '{}'),
                    sort_by=row['sort_by'], created_at=row['created_at'], updated_at=row['updated_at'])

    def list_views(self) -> List[View]:
        rows = self.db.fetchall("SELECT * FROM views ORDER BY name")
        return [View(view_id=r['view_id'], name=r['name'], description=r['description'],
                     query=r['query'], filters=json.loads(r['filters'] or '{}'),
                     sort_by=r['sort_by'], created_at=r['created_at'], updated_at=r['updated_at'])
                for r in rows]

    def update_view(self, view_id: str, **kwargs):
        allowed = {'name', 'description', 'query', 'filters', 'sort_by'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if 'filters' in updates:
            updates['filters'] = json.dumps(updates['filters'])
        updates['updated_at'] = datetime.datetime.now().isoformat()
        set_clause = ', '.join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [view_id]
        self.db.execute(f"UPDATE views SET {set_clause} WHERE view_id = ?", tuple(values))
        self.db.commit()

    def delete_view(self, view_id: str):
        self.db.execute("DELETE FROM views WHERE view_id = ?", (view_id,))
        self.db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Metadata Management
# ─────────────────────────────────────────────────────────────────────────────

class MetadataManager:
    """Manages file metadata."""

    def __init__(self, db: Database):
        self.db = db

    def set_metadata(self, file_id: str, key: str, value: Any):
        row = self.db.fetchone("SELECT metadata FROM files WHERE file_id = ?", (file_id,))
        if row:
            meta = json.loads(row['metadata'] or '{}')
            meta[key] = value
            self.db.execute("UPDATE files SET metadata = ? WHERE file_id = ?",
                            (json.dumps(meta), file_id))
            self.db.commit()

    def get_metadata(self, file_id: str) -> Dict[str, Any]:
        row = self.db.fetchone("SELECT metadata FROM files WHERE file_id = ?", (file_id,))
        if row:
            return json.loads(row['metadata'] or '{}')
        return {}

    def update_metadata(self, file_id: str, metadata: Dict[str, Any]):
        row = self.db.fetchone("SELECT metadata FROM files WHERE file_id = ?", (file_id,))
        if row:
            existing = json.loads(row['metadata'] or '{}')
            existing.update(metadata)
            self.db.execute("UPDATE files SET metadata = ? WHERE file_id = ?",
                            (json.dumps(existing), file_id))
            self.db.commit()

    def search_by_metadata(self, key: str, value: Any) -> List[str]:
        rows = self.db.fetchall("SELECT file_id, metadata FROM files")
        results = []
        for row in rows:
            meta = json.loads(row['metadata'] or '{}')
            if meta.get(key) == value:
                results.append(row['file_id'])
        return results


# ─────────────────────────────────────────────────────────────────────────────
# Relation Mining
# ─────────────────────────────────────────────────────────────────────────────

class RelationMiner:
    """Mines relationships between files."""

    def __init__(self, db: Database):
        self.db = db

    def add_relation(self, source_file_id: str, target_file_id: str,
                     relation_type: str, confidence: float = 1.0,
                     evidence: str = '', auto_detected: bool = False) -> Relation:
        relation_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()
        self.db.execute("""
            INSERT OR REPLACE INTO relations
            (relation_id, source_file_id, target_file_id, relation_type, confidence, evidence, created_at, auto_detected)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (relation_id, source_file_id, target_file_id, relation_type,
              confidence, evidence, created_at, int(auto_detected)))
        self.db.commit()
        return Relation(relation_id=relation_id, source_file_id=source_file_id,
                        target_file_id=target_file_id, relation_type=relation_type,
                        confidence=confidence, evidence=evidence, created_at=created_at,
                        auto_detected=auto_detected)

    def get_relations(self, file_id: str, direction: str = 'both') -> List[Relation]:
        if direction == 'outgoing':
            rows = self.db.fetchall("SELECT * FROM relations WHERE source_file_id = ?", (file_id,))
        elif direction == 'incoming':
            rows = self.db.fetchall("SELECT * FROM relations WHERE target_file_id = ?", (file_id,))
        else:
            rows = self.db.fetchall(
                "SELECT * FROM relations WHERE source_file_id = ? OR target_file_id = ?",
                (file_id, file_id))
        return [Relation(
            relation_id=r['relation_id'],
            source_file_id=r['source_file_id'],
            target_file_id=r['target_file_id'],
            relation_type=r['relation_type'],
            confidence=r['confidence'],
            evidence=r['evidence'],
            created_at=r['created_at'],
            auto_detected=bool(r['auto_detected'])
        ) for r in rows]

    def mine_filename_relations(self) -> List[Relation]:
        """Auto-detect relations based on filename references in content."""
        relations = []
        files = self.db.fetchall("SELECT file_id, filename FROM files")
        file_map = {r['filename']: r['file_id'] for r in files}

        for file_id, filename in [(r['file_id'], r['filename']) for r in files]:
            chunks = self.db.fetchall("SELECT content FROM chunks WHERE file_id = ?", (file_id,))
            for chunk in chunks:
                content = chunk['content']
                for other_filename, other_file_id in file_map.items():
                    if other_file_id != file_id and other_filename in content:
                        rel = self.add_relation(
                            source_file_id=file_id,
                            target_file_id=other_file_id,
                            relation_type='references',
                            confidence=0.7,
                            evidence=f"Filename '{other_filename}' found in content",
                            auto_detected=True
                        )
                        relations.append(rel)
        return relations

    def mine_url_relations(self) -> List[Relation]:
        """Auto-detect relations based on shared URLs."""
        url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')
        file_urls: Dict[str, set] = defaultdict(set)

        files = self.db.fetchall("SELECT file_id FROM files")
        for row in files:
            file_id = row['file_id']
            chunks = self.db.fetchall("SELECT content FROM chunks WHERE file_id = ?", (file_id,))
            for chunk in chunks:
                urls = url_pattern.findall(chunk['content'])
                file_urls[file_id].update(urls)

        relations = []
        file_ids = list(file_urls.keys())
        for i, fid1 in enumerate(file_ids):
            for fid2 in file_ids[i+1:]:
                shared = file_urls[fid1] & file_urls[fid2]
                if shared:
                    rel = self.add_relation(
                        source_file_id=fid1,
                        target_file_id=fid2,
                        relation_type='shares_urls',
                        confidence=0.8,
                        evidence=f"Shared URLs: {', '.join(list(shared)[:3])}",
                        auto_detected=True
                    )
                    relations.append(rel)
        return relations

    def delete_relation(self, relation_id: str):
        self.db.execute("DELETE FROM relations WHERE relation_id = ?", (relation_id,))
        self.db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Search Engine
# ─────────────────────────────────────────────────────────────────────────────

class LexicalSearchEngine:
    """BM25-style lexical search using SQLite FTS5."""

    def __init__(self, db: Database):
        self.db = db

    def search(self, query: str, limit: int = 20,
               file_ids: Optional[List[str]] = None,
               extensions: Optional[List[str]] = None,
               catalog_id: Optional[str] = None) -> List[SearchResult]:
        """Perform lexical search using FTS5."""
        results = []

        # Build FTS query
        fts_query = self._build_fts_query(query)

        try:
            if file_ids:
                placeholders = ','.join('?' * len(file_ids))
                rows = self.db.fetchall(f"""
                    SELECT c.chunk_id, c.file_id, c.content, c.chunk_type, c.position,
                           c.start_char, c.end_char, c.metadata,
                           bm25(chunks_fts) as score
                    FROM chunks_fts
                    JOIN chunks c ON chunks_fts.chunk_id = c.chunk_id
                    WHERE chunks_fts MATCH ? AND c.file_id IN ({placeholders})
                    ORDER BY score
                    LIMIT ?
                """, (fts_query, *file_ids, limit))
            else:
                rows = self.db.fetchall("""
                    SELECT c.chunk_id, c.file_id, c.content, c.chunk_type, c.position,
                           c.start_char, c.end_char, c.metadata,
                           bm25(chunks_fts) as score
                    FROM chunks_fts
                    JOIN chunks c ON chunks_fts.chunk_id = c.chunk_id
                    WHERE chunks_fts MATCH ?
                    ORDER BY score
                    LIMIT ?
                """, (fts_query, limit))

            for row in rows:
                file_row = self.db.fetchone("SELECT * FROM files WHERE file_id = ?", (row['file_id'],))
                if not file_row:
                    continue

                # Apply filters
                if extensions and file_row['extension'] not in extensions:
                    continue
                if catalog_id and file_row['catalog_id'] != catalog_id:
                    continue

                chunk = Chunk(
                    chunk_id=row['chunk_id'],
                    file_id=row['file_id'],
                    content=row['content'],
                    chunk_type=row['chunk_type'],
                    position=row['position'],
                    start_char=row['start_char'],
                    end_char=row['end_char'],
                    metadata=json.loads(row['metadata'] or '{}')
                )

                file_record = FileRecord(
                    file_id=file_row['file_id'],
                    path=file_row['path'],
                    filename=file_row['filename'],
                    extension=file_row['extension'],
                    mime_type=file_row['mime_type'],
                    size_bytes=file_row['size_bytes'],
                    checksum=file_row['checksum'],
                    created_at=file_row['created_at'],
                    modified_at=file_row['modified_at'],
                    ingested_at=file_row['ingested_at'],
                    catalog_id=file_row['catalog_id'],
                    tags=json.loads(file_row['tags'] or '[]'),
                    metadata=json.loads(file_row['metadata'] or '{}'),
                    chunk_count=file_row['chunk_count']
                )

                score = abs(row['score']) if row['score'] else 0.0
                snippet = self._make_snippet(row['content'], query)
                highlights = self._find_highlights(row['content'], query)

                results.append(SearchResult(
                    chunk=chunk,
                    file_record=file_record,
                    score=score,
                    match_type='lexical',
                    snippet=snippet,
                    highlights=highlights
                ))

        except Exception as e:
            logger.warning(f"FTS search failed: {e}, falling back to LIKE search")
            results = self._fallback_search(query, limit, file_ids, extensions, catalog_id)

        return results

    def _build_fts_query(self, query: str) -> str:
        """Build an FTS5 query from a natural language query."""
        # Escape special FTS5 characters
        query = query.replace('"', '""')
        words = query.split()
        if not words:
            return '""'
        # Use phrase search for multi-word, OR for individual terms
        if len(words) == 1:
            return f'"{words[0]}"'
        phrase = f'"{query}"'
        individual = ' OR '.join(f'"{w}"' for w in words if len(w) > 2)
        return f'{phrase} OR {individual}' if individual else phrase

    def _fallback_search(self, query: str, limit: int,
                         file_ids: Optional[List[str]],
                         extensions: Optional[List[str]],
                         catalog_id: Optional[str]) -> List[SearchResult]:
        """LIKE-based fallback search."""
        results = []
        terms = query.lower().split()
        rows = self.db.fetchall("SELECT * FROM chunks LIMIT 10000")

        scored = []
        for row in rows:
            content_lower = row['content'].lower()
            score = sum(content_lower.count(term) for term in terms)
            if score > 0:
                scored.append((score, row))

        scored.sort(key=lambda x: x[0], reverse=True)

        for score, row in scored[:limit]:
            file_row = self.db.fetchone("SELECT * FROM files WHERE file_id = ?", (row['file_id'],))
            if not file_row:
                continue
            if file_ids and row['file_id'] not in file_ids:
                continue
            if extensions and file_row['extension'] not in extensions:
                continue
            if catalog_id and file_row['catalog_id'] != catalog_id:
                continue

            chunk = Chunk(
                chunk_id=row['chunk_id'],
                file_id=row['file_id'],
                content=row['content'],
                chunk_type=row['chunk_type'],
                position=row['position'],
                start_char=row['start_char'],
                end_char=row['end_char'],
                metadata=json.loads(row['metadata'] or '{}')
            )
            file_record = FileRecord(
                file_id=file_row['file_id'],
                path=file_row['path'],
                filename=file_row['filename'],
                extension=file_row['extension'],
                mime_type=file_row['mime_type'],
                size_bytes=file_row['size_bytes'],
                checksum=file_row['checksum'],
                created_at=file_row['created_at'],
                modified_at=file_row['modified_at'],
                ingested_at=file_row['ingested_at'],
                catalog_id=file_row['catalog_id'],
                tags=json.loads(file_row['tags'] or '[]'),
                metadata=json.loads(file_row['metadata'] or '{}'),
                chunk_count=file_row['chunk_count']
            )
            snippet = self._make_snippet(row['content'], query)
            results.append(SearchResult(
                chunk=chunk,
                file_record=file_record,
                score=float(score),
                match_type='lexical',
                snippet=snippet
            ))

        return results

    def _make_snippet(self, content: str, query: str, window: int = 200) -> str:
        """Extract a relevant snippet from content."""
        terms = query.lower().split()
        content_lower = content.lower()
        best_pos = 0
        best_score = 0

        for i in range(0, len(content), 50):
            window_text = content_lower[i:i+window]
            score = sum(window_text.count(term) for term in terms)
            if score > best_score:
                best_score = score
                best_pos = i

        snippet = content[best_pos:best_pos+window]
        if best_pos > 0:
            snippet = '...' + snippet
        if best_pos + window < len(content):
            snippet = snippet + '...'
        return snippet.strip()

    def _find_highlights(self, content: str, query: str) -> List[str]:
        """Find highlighted terms in content."""
        terms = query.lower().split()
        highlights = []
        for term in terms:
            if len(term) > 2:
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                matches = pattern.findall(content)
                highlights.extend(matches[:3])
        return list(set(highlights))


class EmbeddingEngine:
    """Manages text embeddings for semantic search."""

    def __init__(self, db: Database, model: str = 'text-embedding-3-small'):
        self.db = db
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None and HAS_OPENAI:
            self._client = openai.OpenAI()
        return self._client

    def embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text."""
        client = self._get_client()
        if not client:
            return None
        try:
            response = client.embeddings.create(input=text, model=self.model)
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")
            return None

    def embed_chunk(self, chunk_id: str, content: str) -> bool:
        """Embed a chunk and store it."""
        embedding = self.embed_text(content)
        if embedding is None:
            return False
        embedding_bytes = json.dumps(embedding).encode()
        now = datetime.datetime.now().isoformat()
        self.db.execute("""
            INSERT OR REPLACE INTO embeddings (chunk_id, embedding, model, created_at)
            VALUES (?, ?, ?, ?)
        """, (chunk_id, embedding_bytes, self.model, now))
        self.db.commit()
        return True

    def embed_all_chunks(self, file_id: Optional[str] = None) -> int:
        """Embed all chunks that don't have embeddings yet."""
        if file_id:
            rows = self.db.fetchall("""
                SELECT c.chunk_id, c.content FROM chunks c
                LEFT JOIN embeddings e ON c.chunk_id = e.chunk_id
                WHERE c.file_id = ? AND e.chunk_id IS NULL
            """, (file_id,))
        else:
            rows = self.db.fetchall("""
                SELECT c.chunk_id, c.content FROM chunks c
                LEFT JOIN embeddings e ON c.chunk_id = e.chunk_id
                WHERE e.chunk_id IS NULL
            """)

        count = 0
        for row in rows:
            if self.embed_chunk(row['chunk_id'], row['content']):
                count += 1
        return count

    def semantic_search(self, query: str, limit: int = 20,
                        file_ids: Optional[List[str]] = None) -> List[Tuple[str, float]]:
        """Search by semantic similarity. Returns (chunk_id, score) pairs."""
        query_embedding = self.embed_text(query)
        if query_embedding is None:
            return []

        if not HAS_NUMPY:
            return []

        # Load all embeddings and compute cosine similarity
        if file_ids:
            placeholders = ','.join('?' * len(file_ids))
            rows = self.db.fetchall(f"""
                SELECT e.chunk_id, e.embedding FROM embeddings e
                JOIN chunks c ON e.chunk_id = c.chunk_id
                WHERE c.file_id IN ({placeholders})
            """, tuple(file_ids))
        else:
            rows = self.db.fetchall("SELECT chunk_id, embedding FROM embeddings")

        query_vec = np.array(query_embedding)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []

        scored = []
        for row in rows:
            try:
                emb = np.array(json.loads(row['embedding'].decode()))
                emb_norm = np.linalg.norm(emb)
                if emb_norm == 0:
                    continue
                similarity = float(np.dot(query_vec, emb) / (query_norm * emb_norm))
                scored.append((row['chunk_id'], similarity))
            except Exception:
                continue

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]


class Reranker:
    """Reranks search results using cross-encoder or LLM scoring."""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def rerank(self, query: str, results: List[SearchResult],
               top_k: int = 10) -> List[SearchResult]:
        """Rerank results by relevance to query."""
        if not results:
            return results

        # Simple TF-IDF-like reranking without external model
        query_terms = set(query.lower().split())
        reranked = []

        for result in results:
            content_lower = result.chunk.content.lower()
            content_terms = set(content_lower.split())

            # Term overlap score
            overlap = len(query_terms & content_terms) / max(len(query_terms), 1)

            # Exact phrase bonus
            phrase_bonus = 1.5 if query.lower() in content_lower else 1.0

            # Position bonus (earlier chunks may be more relevant)
            position_penalty = 1.0 / (1 + result.chunk.position * 0.01)

            new_score = result.score * overlap * phrase_bonus * position_penalty
            reranked.append(SearchResult(
                chunk=result.chunk,
                file_record=result.file_record,
                score=new_score,
                match_type='reranked',
                snippet=result.snippet,
                highlights=result.highlights
            ))

        reranked.sort(key=lambda x: x.score, reverse=True)
        return reranked[:top_k]


class SearchEngine:
    """Main search engine combining lexical, semantic, and reranking."""

    def __init__(self, db: Database, embedding_engine: Optional[EmbeddingEngine] = None,
                 reranker: Optional[Reranker] = None):
        self.db = db
        self.lexical = LexicalSearchEngine(db)
        self.embedding_engine = embedding_engine
        self.reranker = reranker

    def search(self, query: str, limit: int = 20,
               use_semantic: bool = False,
               use_reranking: bool = False,
               source_quota: Optional[Dict[str, int]] = None,
               file_ids: Optional[List[str]] = None,
               extensions: Optional[List[str]] = None,
               catalog_id: Optional[str] = None,
               tags: Optional[List[str]] = None) -> List[SearchResult]:
        """
        Unified search with optional semantic and reranking.
        source_quota: max results per file extension, e.g. {'.pdf': 5, '.md': 10}
        """
        # Apply tag filter
        if tags:
            tag_file_ids = set()
            for tag in tags:
                rows = self.db.fetchall("""
                    SELECT ft.file_id FROM file_tags ft
                    JOIN tags t ON ft.tag_id = t.tag_id
                    WHERE t.name = ?
                """, (tag,))
                tag_file_ids.update(r['file_id'] for r in rows)
            if file_ids:
                file_ids = list(set(file_ids) & tag_file_ids)
            else:
                file_ids = list(tag_file_ids)

        # Lexical search
        results = self.lexical.search(query, limit=limit * 2,
                                      file_ids=file_ids,
                                      extensions=extensions,
                                      catalog_id=catalog_id)

        # Semantic search
        if use_semantic and self.embedding_engine:
            semantic_pairs = self.embedding_engine.semantic_search(query, limit=limit, file_ids=file_ids)
            semantic_chunk_ids = {cid: score for cid, score in semantic_pairs}

            # Merge results
            existing_chunk_ids = {r.chunk.chunk_id for r in results}
            for chunk_id, sem_score in semantic_pairs:
                if chunk_id not in existing_chunk_ids:
                    row = self.db.fetchone("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,))
                    if row:
                        file_row = self.db.fetchone("SELECT * FROM files WHERE file_id = ?", (row['file_id'],))
                        if file_row:
                            chunk = Chunk(
                                chunk_id=row['chunk_id'],
                                file_id=row['file_id'],
                                content=row['content'],
                                chunk_type=row['chunk_type'],
                                position=row['position'],
                                start_char=row['start_char'],
                                end_char=row['end_char'],
                                metadata=json.loads(row['metadata'] or '{}')
                            )
                            file_record = FileRecord(
                                file_id=file_row['file_id'],
                                path=file_row['path'],
                                filename=file_row['filename'],
                                extension=file_row['extension'],
                                mime_type=file_row['mime_type'],
                                size_bytes=file_row['size_bytes'],
                                checksum=file_row['checksum'],
                                created_at=file_row['created_at'],
                                modified_at=file_row['modified_at'],
                                ingested_at=file_row['ingested_at'],
                                catalog_id=file_row['catalog_id'],
                                tags=json.loads(file_row['tags'] or '[]'),
                                metadata=json.loads(file_row['metadata'] or '{}'),
                                chunk_count=file_row['chunk_count']
                            )
                            snippet = self.lexical._make_snippet(row['content'], query)
                            results.append(SearchResult(
                                chunk=chunk,
                                file_record=file_record,
                                score=sem_score,
                                match_type='semantic',
                                snippet=snippet
                            ))

            # Boost scores for chunks found by both methods
            for result in results:
                if result.chunk.chunk_id in semantic_chunk_ids:
                    result.score = result.score * 0.5 + semantic_chunk_ids[result.chunk.chunk_id] * 0.5

        # Reranking
        if use_reranking and self.reranker:
            results = self.reranker.rerank(query, results, top_k=limit)
        else:
            results.sort(key=lambda x: x.score, reverse=True)
            results = results[:limit]

        # Apply source quota
        if source_quota:
            quota_counts: Dict[str, int] = defaultdict(int)
            filtered = []
            for result in results:
                ext = result.file_record.extension
                max_count = source_quota.get(ext, source_quota.get('*', limit))
                if quota_counts[ext] < max_count:
                    filtered.append(result)
                    quota_counts[ext] += 1
            results = filtered

        return results[:limit]


# ─────────────────────────────────────────────────────────────────────────────
# Journal
# ─────────────────────────────────────────────────────────────────────────────

class JournalManager:
    """Manages research journal entries."""

    def __init__(self, db: Database):
        self.db = db

    def create_entry(self, title: str, content: str,
                     tags: Optional[List[str]] = None,
                     cited_files: Optional[List[str]] = None,
                     investigation_id: Optional[str] = None) -> JournalEntry:
        entry_id = str(uuid.uuid4())
        now = datetime.datetime.now().isoformat()
        self.db.execute("""
            INSERT INTO journal_entries
            (entry_id, title, content, created_at, updated_at, tags, cited_files, investigation_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (entry_id, title, content, now, now,
              json.dumps(tags or []), json.dumps(cited_files or []), investigation_id))
        self.db.commit()
        return JournalEntry(entry_id=entry_id, title=title, content=content,
                            created_at=now, updated_at=now,
                            tags=tags or [], cited_files=cited_files or [],
                            investigation_id=investigation_id)

    def get_entry(self, entry_id: str) -> Optional[JournalEntry]:
        row = self.db.fetchone("SELECT * FROM journal_entries WHERE entry_id = ?", (entry_id,))
        if not row:
            return None
        return JournalEntry(
            entry_id=row['entry_id'],
            title=row['title'],
            content=row['content'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            tags=json.loads(row['tags'] or '[]'),
            cited_files=json.loads(row['cited_files'] or '[]'),
            investigation_id=row['investigation_id']
        )

    def update_entry(self, entry_id: str, title: Optional[str] = None,
                     content: Optional[str] = None, tags: Optional[List[str]] = None):
        updates = {}
        if title is not None:
            updates['title'] = title
        if content is not None:
            updates['content'] = content
        if tags is not None:
            updates['tags'] = json.dumps(tags)
        updates['updated_at'] = datetime.datetime.now().isoformat()
        set_clause = ', '.join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [entry_id]
        self.db.execute(f"UPDATE journal_entries SET {set_clause} WHERE entry_id = ?", tuple(values))
        self.db.commit()

    def list_entries(self, limit: int = 50, offset: int = 0) -> List[JournalEntry]:
        rows = self.db.fetchall(
            "SELECT * FROM journal_entries ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset))
        return [JournalEntry(
            entry_id=r['entry_id'],
            title=r['title'],
            content=r['content'],
            created_at=r['created_at'],
            updated_at=r['updated_at'],
            tags=json.loads(r['tags'] or '[]'),
            cited_files=json.loads(r['cited_files'] or '[]'),
            investigation_id=r['investigation_id']
        ) for r in rows]

    def search_entries(self, query: str) -> List[JournalEntry]:
        query_lower = query.lower()
        rows = self.db.fetchall("SELECT * FROM journal_entries")
        results = []
        for row in rows:
            if (query_lower in row['title'].lower() or
                    query_lower in (row['content'] or '').lower()):
                results.append(JournalEntry(
                    entry_id=row['entry_id'],
                    title=row['title'],
                    content=row['content'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    tags=json.loads(row['tags'] or '[]'),
                    cited_files=json.loads(row['cited_files'] or '[]'),
                    investigation_id=row['investigation_id']
                ))
        return results

    def delete_entry(self, entry_id: str):
        self.db.execute("DELETE FROM journal_entries WHERE entry_id = ?", (entry_id,))
        self.db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Investigation Store
# ─────────────────────────────────────────────────────────────────────────────

class InvestigationStore:
    """Stores and retrieves durable investigation notes."""

    def __init__(self, db: Database):
        self.db = db

    def save_investigation(self, query: str, answer: str,
                           citations: List[Citation],
                           sources_used: List[str],
                           tags: Optional[List[str]] = None,
                           follow_up_questions: Optional[List[str]] = None,
                           metadata: Optional[Dict] = None) -> Investigation:
        investigation_id = str(uuid.uuid4())
        now = datetime.datetime.now().isoformat()
        citations_data = [asdict(c) for c in citations]
        self.db.execute("""
            INSERT INTO investigations
            (investigation_id, query, answer, citations, sources_used, created_at, updated_at,
             tags, follow_up_questions, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (investigation_id, query, answer,
              json.dumps(citations_data),
              json.dumps(sources_used),
              now, now,
              json.dumps(tags or []),
              json.dumps(follow_up_questions or []),
              json.dumps(metadata or {})))
        self.db.commit()
        return Investigation(
            investigation_id=investigation_id,
            query=query,
            answer=answer,
            citations=citations_data,
            sources_used=sources_used,
            created_at=now,
            updated_at=now,
            tags=tags or [],
            follow_up_questions=follow_up_questions or [],
            metadata=metadata or {}
        )

    def get_investigation(self, investigation_id: str) -> Optional[Investigation]:
        row = self.db.fetchone("SELECT * FROM investigations WHERE investigation_id = ?",
                               (investigation_id,))
        if not row:
            return None
        return Investigation(
            investigation_id=row['investigation_id'],
            query=row['query'],
            answer=row['answer'],
            citations=json.loads(row['citations'] or '[]'),
            sources_used=json.loads(row['sources_used'] or '[]'),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            tags=json.loads(row['tags'] or '[]'),
            follow_up_questions=json.loads(row['follow_up_questions'] or '[]'),
            metadata=json.loads(row['metadata'] or '{}')
        )

    def list_investigations(self, limit: int = 50, offset: int = 0) -> List[Investigation]:
        rows = self.db.fetchall(
            "SELECT * FROM investigations ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset))
        return [Investigation(
            investigation_id=r['investigation_id'],
            query=r['query'],
            answer=r['answer'],
            citations=json.loads(r['citations'] or '[]'),
            sources_used=json.loads(r['sources_used'] or '[]'),
            created_at=r['created_at'],
            updated_at=r['updated_at'],
            tags=json.loads(r['tags'] or '[]'),
            follow_up_questions=json.loads(r['follow_up_questions'] or '[]'),
            metadata=json.loads(r['metadata'] or '{}')
        ) for r in rows]

    def search_investigations(self, query: str) -> List[Investigation]:
        query_lower = query.lower()
        rows = self.db.fetchall("SELECT * FROM investigations")
        results = []
        for row in rows:
            if (query_lower in row['query'].lower() or
                    query_lower in (row['answer'] or '').lower()):
                results.append(Investigation(
                    investigation_id=row['investigation_id'],
                    query=row['query'],
                    answer=row['answer'],
                    citations=json.loads(row['citations'] or '[]'),
                    sources_used=json.loads(row['sources_used'] or '[]'),
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    tags=json.loads(row['tags'] or '[]'),
                    follow_up_questions=json.loads(row['follow_up_questions'] or '[]'),
                    metadata=json.loads(row['metadata'] or '{}')
                ))
        return results

    def recall_relevant_investigations(self, query: str, limit: int = 5) -> List[Investigation]:
        """Recall past investigations relevant to current query."""
        all_investigations = self.list_investigations(limit=200)
        query_terms = set(query.lower().split())

        scored = []
        for inv in all_investigations:
            inv_terms = set(inv.query.lower().split())
            overlap = len(query_terms & inv_terms) / max(len(query_terms), 1)
            if overlap > 0:
                scored.append((overlap, inv))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [inv for _, inv in scored[:limit]]


# ─────────────────────────────────────────────────────────────────────────────
# LLM Clients
# ─────────────────────────────────────────────────────────────────────────────

class LLMClient:
    """Abstract LLM client interface."""

    def complete(self, messages: List[Dict[str, str]],
                 system: Optional[str] = None,
                 max_tokens: int = 4096,
                 temperature: float = 0.3) -> str:
        raise NotImplementedError


class AnthropicClient(LLMClient):
    """Anthropic Claude client."""

    def __init__(self, model: str = 'claude-3-5-sonnet-20241022',
                 api_key: Optional[str] = None):
        if not HAS_ANTHROPIC:
            raise ImportError("anthropic package not installed")
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get('ANTHROPIC_API_KEY'))

    def complete(self, messages: List[Dict[str, str]],
                 system: Optional[str] = None,
                 max_tokens: int = 4096,
                 temperature: float = 0.3) -> str:
        kwargs = {
            'model': self.model,
            'max_tokens': max_tokens,
            'messages': messages,
            'temperature': temperature
        }
        if system:
            kwargs['system'] = system
        response = self.client.messages.create(**kwargs)
        return response.content[0].text


class OpenAIClient(LLMClient):
    """OpenAI GPT client."""

    def __init__(self, model: str = 'gpt-4o',
                 api_key: Optional[str] = None):
        if not HAS_OPENAI:
            raise ImportError("openai package not installed")
        self.model = model
        self.client = openai.OpenAI(api_key=api_key or os.environ.get('OPENAI_API_KEY'))

    def complete(self, messages: List[Dict[str, str]],
                 system: Optional[str] = None,
                 max_tokens: int = 4096,
                 temperature: float = 0.3) -> str:
        all_messages = []
        if system:
            all_messages.append({'role': 'system', 'content': system})
        all_messages.extend(messages)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=all_messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content


class MockLLMClient(LLMClient):
    """Mock LLM client for testing without API keys."""

    def complete(self, messages: List[Dict[str, str]],
                 system: Optional[str] = None,
                 max_tokens: int = 4096,
                 temperature: float = 0.3) -> str:
        last_message = messages[-1]['content'] if messages else ''
        return f"[Mock LLM Response]\n\nQuery: {last_message[:100]}...\n\nThis is a mock response for testing purposes."


# ─────────────────────────────────────────────────────────────────────────────
# Source Reader
# ─────────────────────────────────────────────────────────────────────────────

class SourceReader:
    """Reads specific sections of original files for agent context."""

    def __init__(self):
        self.extractor = TextExtractor()

    def read_window(self, file_path: str, chunk: Chunk,
                    context_lines: int = 5) -> str:
        """Read a window of content around a chunk from the original file."""
        chunk_type = chunk.chunk_type
        position = chunk.position

        if chunk_type == 'page':
            return self._read_pdf_page(file_path, position)
        elif chunk_type == 'line':
            return self._read_lines(file_path, position, context_lines)
        elif chunk_type == 'table_row':
            return self._read_table_rows(file_path, position, context_lines)
        elif chunk_type == 'archive_member':
            return self._read_archive_member(file_path, chunk.metadata.get('member_name', ''))
        elif chunk_type == 'section':
            return self._read_section(file_path, chunk)
        else:
            return self._read_text_window(file_path, chunk.start_char, chunk.end_char, context_lines)

    def _read_pdf_page(self, path: str, page_num: int) -> str:
        if not HAS_PYMUPDF:
            return chunk_content_fallback(path, page_num)
        try:
            doc = fitz.open(path)
            if page_num < len(doc):
                page = doc[page_num]
                text = page.get_text()
                doc.close()
                return f"[Page {page_num + 1}]\n{text}"
        except Exception as e:
            logger.warning(f"PDF page read failed: {e}")
        return ''

    def _read_lines(self, path: str, line_num: int, context: int) -> str:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            start = max(0, line_num - context)
            end = min(len(lines), line_num + context + 1)
            return ''.join(lines[start:end])
        except Exception as e:
            logger.warning(f"Line read failed: {e}")
        return ''

    def _read_table_rows(self, path: str, row_idx: int, context: int) -> str:
        ext = Path(path).suffix.lower()
        try:
            if ext in ('.csv', '.tsv'):
                import csv as csv_module
                delimiter = '\t' if ext == '.tsv' else ','
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    reader = list(csv_module.reader(f, delimiter=delimiter))
                start = max(0, row_idx)
                end = min(len(reader), row_idx + context + 2)
                rows = reader[start:end]
                return '\n'.join(','.join(row) for row in rows)
        except Exception as e:
            logger.warning(f"Table row read failed: {e}")
        return ''

    def _read_archive_member(self, path: str, member_name: str) -> str:
        ext = Path(path).suffix.lower()
        try:
            if ext == '.zip':
                with zipfile.ZipFile(path, 'r') as zf:
                    with zf.open(member_name) as f:
                        return f.read(16384).decode('utf-8', errors='replace')
            elif tarfile.is_tarfile(path):
                with tarfile.open(path, 'r:*') as tf:
                    member = tf.getmember(member_name)
                    f = tf.extractfile(member)
                    if f:
                        return f.read(16384).decode('utf-8', errors='replace')
        except Exception as e:
            logger.warning(f"Archive member read failed: {e}")
        return ''

    def _read_section(self, path: str, chunk: Chunk) -> str:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            start = max(0, chunk.start_char - 100)
            end = min(len(content), chunk.end_char + 100)
            return content[start:end]
        except Exception as e:
            logger.warning(f"Section read failed: {e}")
        return chunk.content

    def _read_text_window(self, path: str, start_char: int, end_char: int,
                          context_chars: int = 500) -> str:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            start = max(0, start_char - context_chars)
            end = min(len(content), end_char + context_chars)
            return content[start:end]
        except Exception as e:
            logger.warning(f"Text window read failed: {e}")
        return ''


def chunk_content_fallback(path: str, position: int) -> str:
    """Fallback content reader."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        return content[:2000]
    except Exception:
        return ''


# ─────────────────────────────────────────────────────────────────────────────
# Research Agent
# ─────────────────────────────────────────────────────────────────────────────

class ResearchAgent:
    """
    The main LLM-powered research agent that reads original file windows
    before writing cited answers.
    """

    SYSTEM_PROMPT = """You are Marginalia, a research assistant for a personal knowledge base.
You have access to the user's private files and notes. Your job is to:
1. Answer questions by reading the relevant sections of original files
2. Always cite your sources with specific file names and locations
3. Be precise about what the sources actually say vs. your interpretation
4. Note when information is incomplete or when you're uncertain
5. Suggest follow-up questions when appropriate

When citing sources, use the format: [Source: filename, position/page/line]
"""

    def __init__(self, knowledge_base: 'KnowledgeBase', llm_client: LLMClient):
        self.kb = knowledge_base
        self.llm = llm_client
        self.source_reader = SourceReader()
        self.conversation_history: List[Dict[str, str]] = []

    def ask(self, query: str,
            use_semantic: bool = False,
            use_reranking: bool = True,
            max_sources: int = 10,
            source_quota: Optional[Dict[str, int]] = None,
            recall_investigations: bool = True,
            save_investigation: bool = True,
            tags: Optional[List[str]] = None,
            catalog_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Ask a question and get a cited answer.
        Returns dict with answer, citations, and investigation_id.
        """
        # Recall relevant past investigations
        past_investigations = []
        if recall_investigations:
            past_investigations = self.kb.investigation_store.recall_relevant_investigations(
                query, limit=3)

        # Search for relevant chunks
        search_results = self.kb.search_engine.search(
            query=query,
            limit=max_sources * 2,
            use_semantic=use_semantic,
            use_reranking=use_reranking,
            source_quota=source_quota,
            tags=tags,
            catalog_id=catalog_id
        )

        if not search_results:
            answer = "I couldn't find any relevant information in your knowledge base for this query."
            investigation = None
            if save_investigation:
                investigation = self.kb.investigation_store.save_investigation(
                    query=query,
                    answer=answer,
                    citations=[],
                    sources_used=[],
                    tags=tags or []
                )
            return {
                'answer': answer,
                'citations': [],
                'investigation_id': investigation.investigation_id if investigation else None,
                'sources_searched': 0
            }

        # Read original file windows for top results
        source_windows = []
        citations = []
        sources_used = []

        for i, result in enumerate(search_results[:max_sources]):
            try:
                window = self.source_reader.read_window(
                    result.file_record.path,
                    result.chunk
                )
                if not window:
                    window = result.chunk.content

                source_windows.append({
                    'index': i + 1,
                    'filename': result.file_record.filename,
                    'path': result.file_record.path,
                    'chunk_type': result.chunk.chunk_type,
                    'position': result.chunk.position,
                    'content': window[:2000],  # Limit window size
                    'score': result.score
                })

                citation = Citation(
                    file_id=result.file_record.file_id,
                    filename=result.file_record.filename,
                    path=result.file_record.path,
                    chunk_id=result.chunk.chunk_id,
                    position=result.chunk.position,
                    chunk_type=result.chunk.chunk_type,
                    excerpt=result.snippet[:500],
                    relevance_score=result.score
                )
                citations.append(citation)
                sources_used.append(result.file_record.file_id)

            except Exception as e:
                logger.warning(f"Failed to read source window: {e}")
                source_windows.append({
                    'index': i + 1,
                    'filename': result.file_record.filename,
                    'path': result.file_record.path,
                    'chunk_type': result.chunk.chunk_type,
                    'position': result.chunk.position,
                    'content': result.chunk.content[:2000],
                    'score': result.score
                })

        # Build context for LLM
        context_parts = []

        if past_investigations:
            context_parts.append("## Relevant Past Investigations\n")
            for inv in past_investigations:
                context_parts.append(
                    f"**Previous Query**: {inv.query}\n"
                    f"**Summary**: {inv.answer[:500]}...\n\n"
                )

        context_parts.append("## Source Documents\n")
        for sw in source_windows:
            context_parts.append(
                f"### Source {sw['index']}: {sw['filename']}\n"
                f"**Type**: {sw['chunk_type']} | **Position**: {sw['position']} | "
                f"**Relevance**: {sw['score']:.3f}\n\n"
                f"```\n{sw['content']}\n```\n\n"
            )

        context = '\n'.join(context_parts)

        # Build messages for LLM
        messages = list(self.conversation_history)
        messages.append({
            'role': 'user',
            'content': f"## Context from Knowledge Base\n\n{context}\n\n## Question\n\n{query}"
        })

        # Get LLM response
        try:
            answer = self.llm.complete(
                messages=messages,
                system=self.SYSTEM_PROMPT,
                max_tokens=4096,
                temperature=0.3
            )
        except Exception as e:
            logger.error(f"LLM completion failed: {e}")
            answer = f"Error generating answer: {e}"

        # Update conversation history
        self.conversation_history.append({
            'role': 'user',
            'content': query
        })
        self.conversation_history.append({
            'role': 'assistant',
            'content': answer
        })

        # Keep conversation history manageable
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        # Extract follow-up questions
        follow_up_questions = self._extract_follow_up_questions(answer)

        # Save investigation
        investigation = None
        if save_investigation:
            investigation = self.kb.investigation_store.save_investigation(
                query=query,
                answer=answer,
                citations=citations,
                sources_used=list(set(sources_used)),
                tags=tags or [],
                follow_up_questions=follow_up_questions,
                metadata={
                    'use_semantic': use_semantic,
                    'use_reranking': use_reranking,
                    'sources_found': len(search_results)
                }
            )

            # Create journal entry for this investigation
            self.kb.journal_manager.create_entry(
                title=f"Investigation: {query[:80]}",
                content=f"**Query**: {query}\n\n**Answer**:\n{answer}",
                tags=tags or [],
                cited_files=list(set(sources_used)),
                investigation_id=investigation.investigation_id
            )

        return {
            'answer': answer,
            'citations': [asdict(c) for c in citations],
            'investigation_id': investigation.investigation_id if investigation else None,
            'sources_searched': len(search_results),
            'follow_up_questions': follow_up_questions
        }

    def _extract_follow_up_questions(self, answer: str) -> List[str]:
        """Extract follow-up questions from the answer."""
        questions = []
        lines = answer.split('\n')
        for line in lines:
            line = line.strip()
            if line.endswith('?') and len(line) > 20:
                # Clean up bullet points etc.
                line = re.sub(r'^[-*•\d.]+\s*', '', line)
                if line:
                    questions.append(line)
        return questions[:5]

    def generate_report(self, topic: str, max_sources: int = 20,
                        report_format: str = 'markdown') -> str:
        """Generate a comprehensive report on a topic."""
        result = self.ask(
            query=f"Write a comprehensive report on: {topic}",
            max_sources=max_sources,
            use_reranking=True,
            save_investigation=True
        )

        report = result['answer']

        if report_format == 'markdown':
            # Add citation appendix
            if result['citations']:
                report += "\n\n---\n\n## Sources\n\n"
                for i, citation in enumerate(result['citations'], 1):
                    report += (f"{i}. **{citation['filename']}** "
                               f"({citation['chunk_type']}, position {citation['position']})\n"
                               f"   > {citation['excerpt'][:200]}...\n\n")

        return report

    def reset_conversation(self):
        """Reset the conversation history."""
        self.conversation_history = []


# ─────────────────────────────────────────────────────────────────────────────
# Knowledge Base (Main Facade)
# ─────────────────────────────────────────────────────────────────────────────

class KnowledgeBase:
    """
    Main facade for the Marginalia knowledge management system.
    Coordinates all subsystems.
    """

    def __init__(self, vault_path: str, db_path: Optional[str] = None):
        self.vault_path = os.path.abspath(vault_path)
        os.makedirs(self.vault_path, exist_ok=True)

        if db_path is None:
            db_path = os.path.join(self.vault_path, '.marginalia', 'marginalia.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.db = Database(db_path)
        self.ingester = FileIngester(self.db, self.vault_path)
        self.catalog_manager = CatalogManager(self.db)
        self.tag_manager = TagManager(self.db)
        self.view_manager = ViewManager(self.db)
        self.metadata_manager = MetadataManager(self.db)
        self.relation_miner = RelationMiner(self.db)
        self.journal_manager = JournalManager(self.db)
        self.investigation_store = InvestigationStore(self.db)
        self.embedding_engine = EmbeddingEngine(self.db)
        self.reranker = Reranker()
        self.search_engine = SearchEngine(
            self.db,
            embedding_engine=self.embedding_engine,
            reranker=self.reranker
        )

        logger.info(f"Marginalia knowledge base initialized at: {self.vault_path}")

    def create_agent(self, llm_client: Optional[LLMClient] = None) -> ResearchAgent:
        """Create a research agent for this knowledge base."""
        if llm_client is None:
            # Try to auto-detect available LLM
            if HAS_ANTHROPIC and os.environ.get('ANTHROPIC_API_KEY'):
                llm_client = AnthropicClient()
            elif HAS_OPENAI and os.environ.get('OPENAI_API_KEY'):
                llm_client = OpenAIClient()
            else:
                logger.warning("No LLM API key found, using mock client")
                llm_client = MockLLMClient()
        return ResearchAgent(self, llm_client)

    def ingest(self, path: str, catalog_id: Optional[str] = None,
               tags: Optional[List[str]] = None) -> Optional[FileRecord]:
        """Ingest a file or directory."""
        if os.path.isdir(path):
            records = self.ingester.ingest_directory(path, catalog_id=catalog_id)
            return records[0] if records else None
        return self.ingester.ingest_file(path, catalog_id=catalog_id, tags=tags)

    def ingest_directory(self, directory: str, recursive: bool = True,
                         catalog_id: Optional[str] = None,
                         extensions: Optional[List[str]] = None) -> List[FileRecord]:
        """Ingest all files in a directory."""
        return self.ingester.ingest_directory(directory, recursive=recursive,
                                              catalog_id=catalog_id, extensions=extensions)

    def search(self, query: str, limit: int = 20, **kwargs) -> List[SearchResult]:
        """Search the knowledge base."""
        return self.search_engine.search(query, limit=limit, **kwargs)

    def get_file(self, file_id: str) -> Optional[FileRecord]:
        """Get a file record by ID."""
        return self.ingester._load_file_record(file_id)

    def get_file_by_path(self, path: str) -> Optional[FileRecord]:
        """Get a file record by path."""
        path = os.path.abspath(path)
        row = self.db.fetchone("SELECT file_id FROM files WHERE path = ?", (path,))
        if row:
            return self.ingester._load_file_record(row['file_id'])
        return None

    def list_files(self, catalog_id: Optional[str] = None,
                   extension: Optional[str] = None,
                   limit: int = 100, offset: int = 0) -> List[FileRecord]:
        """List files in the knowledge base."""
        conditions = []
        params = []

        if catalog_id:
            conditions.append("catalog_id = ?")
            params.append(catalog_id)
        if extension:
            conditions.append("extension = ?")
            params.append(extension)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.extend([limit, offset])

        rows = self.db.fetchall(
            f"SELECT * FROM files {where} ORDER BY ingested_at DESC LIMIT ? OFFSET ?",
            tuple(params))

        return [FileRecord(
            file_id=r['file_id'],
            path=r['path'],
            filename=r['filename'],
            extension=r['extension'],
            mime_type=r['mime_type'],
            size_bytes=r['size_bytes'],
            checksum=r['checksum'],
            created_at=r['created_at'],
            modified_at=r['modified_at'],
            ingested_at=r['ingested_at'],
            catalog_id=r['catalog_id'],
            tags=json.loads(r['tags'] or '[]'),
            metadata=json.loads(r['metadata'] or '{}'),
            chunk_count=r['chunk_count']
        ) for r in rows]

    def delete_file(self, file_id: str):
        """Remove a file from the knowledge base (does not delete the actual file)."""
        self.db.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
        self.db.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        stats = {}
        stats['total_files'] = self.db.fetchone("SELECT COUNT(*) as c FROM files")['c']
        stats['total_chunks'] = self.db.fetchone("SELECT COUNT(*) as c FROM chunks")['c']
        stats['total_catalogs'] = self.db.fetchone("SELECT COUNT(*) as c FROM catalogs")['c']
        stats['total_tags'] = self.db.fetchone("SELECT COUNT(*) as c FROM tags")['c']
        stats['total_relations'] = self.db.fetchone("SELECT COUNT(*) as c FROM relations")['c']
        stats['total_investigations'] = self.db.fetchone("SELECT COUNT(*) as c FROM investigations")['c']
        stats['total_journal_entries'] = self.db.fetchone("SELECT COUNT(*) as c FROM journal_entries")['c']
        stats['total_embeddings'] = self.db.fetchone("SELECT COUNT(*) as c FROM embeddings")['c']

        # File type breakdown
        rows = self.db.fetchall("SELECT extension, COUNT(*) as c FROM files GROUP BY extension ORDER BY c DESC")
        stats['files_by_type'] = {r['extension']: r['c'] for r in rows}

        # Total size
        row = self.db.fetchone("SELECT SUM(size_bytes) as total FROM files")
        stats['total_size_bytes'] = row['total'] or 0

        return stats

    def export_catalog(self, catalog_id: str, output_path: str):
        """Export a catalog's metadata to JSON."""
        catalog = self.catalog_manager.get_catalog(catalog_id)
        if not catalog:
            raise ValueError(f"Catalog not found: {catalog_id}")

        files = self.list_files(catalog_id=catalog_id, limit=10000)
        export_data = {
            'catalog': asdict(catalog),
            'files': [asdict(f) for f in files],
            'exported_at': datetime.datetime.now().isoformat()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Exported catalog '{catalog.name}' to {output_path}")

    def mine_relations(self) -> Dict[str, int]:
        """Run all relation mining algorithms."""
        filename_relations = self.relation_miner.mine_filename_relations()
        url_relations = self.relation_miner.mine_url_relations()
        return {
            'filename_relations': len(filename_relations),
            'url_relations': len(url_relations)
        }

    def rebuild_fts_index(self):
        """Rebuild the full-text search index."""
        self.db.execute("DELETE FROM chunks_fts")
        rows = self.db.fetchall("SELECT chunk_id, file_id, content FROM chunks")
        for row in rows:
            self.db.execute(
                "INSERT INTO chunks_fts (chunk_id, file_id, content) VALUES (?, ?, ?)",
                (row['chunk_id'], row['file_id'], row['content'])
            )
        self.db.commit()
        logger.info(f"Rebuilt FTS index with {len(rows)} chunks")

    def watch_directory(self, directory: str, interval: int = 30,
                        catalog_id: Optional[str] = None):
        """Watch a directory for new/changed files and auto-ingest them."""
        def _watch():
            logger.info(f"Watching directory: {directory}")
            while True:
                try:
                    self.ingest_directory(directory, catalog_id=catalog_id)
                except Exception as e:
                    logger.error(f"Watch error: {e}")
                time.sleep(interval)

        thread = threading.Thread(target=_watch, daemon=True)
        thread.start()
        return thread


# ─────────────────────────────────────────────────────────────────────────────
# CLI Interface
# ─────────────────────────────────────────────────────────────────────────────

class MarginaliaCLI:
    """Command-line interface for Marginalia."""

    def __init__(self, vault_path: str = '.'):
        self.kb = KnowledgeBase(vault_path)
        self.agent = None

    def _get_agent(self) -> ResearchAgent:
        if self.agent is None:
            self.agent = self.kb.create_agent()
        return self.agent

    def cmd_ingest(self, path: str, catalog: Optional[str] = None,
                   tags: Optional[str] = None):
        """Ingest a file or directory."""
        tag_list = tags.split(',') if tags else None
        catalog_id = None

        if catalog:
            # Find or create catalog
            catalogs = self.kb.catalog_manager.list_catalogs()
            for c in catalogs:
                if c.name == catalog:
                    catalog_id = c.catalog_id
                    break
            if not catalog_id:
                cat = self.kb.catalog_manager.create_catalog(catalog)
                catalog_id = cat.catalog_id

        if os.path.isdir(path):
            records = self.kb.ingest_directory(path, catalog_id=catalog_id)
            print(f"Ingested {len(records)} files from {path}")
        else:
            record = self.kb.ingest(path, catalog_id=catalog_id, tags=tag_list)
            if record:
                print(f"Ingested: {record.filename} ({record.chunk_count} chunks)")
            else:
                print(f"Failed to ingest: {path}")

    def cmd_search(self, query: str, limit: int = 10,
                   semantic: bool = False, rerank: bool = True):
        """Search the knowledge base."""
        results = self.kb.search(query, limit=limit,
                                 use_semantic=semantic,
                                 use_reranking=rerank)
        if not results:
            print("No results found.")
            return

        print(f"\nFound {len(results)} results for: '{query}'\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. [{result.match_type}] {result.file_record.filename} "
                  f"(score: {result.score:.3f})")
            print(f"   Type: {result.chunk.chunk_type}, Position: {result.chunk.position}")
            print(f"   {result.snippet[:200]}")
            print()

    def cmd_ask(self, query: str, save: bool = True):
        """Ask the research agent a question."""
        agent = self._get_agent()
        print(f"\nSearching knowledge base for: '{query}'\n")
        result = agent.ask(query, save_investigation=save)

        print("=" * 60)
        print("ANSWER:")
        print("=" * 60)
        print(result['answer'])
        print()

        if result['citations']:
            print("=" * 60)
            print("CITATIONS:")
            print("=" * 60)
            for i, citation in enumerate(result['citations'], 1):
                print(f"{i}. {citation['filename']} "
                      f"({citation['chunk_type']}, pos {citation['position']})")
                print(f"   Score: {citation['relevance_score']:.3f}")
                print(f"   Excerpt: {citation['excerpt'][:150]}...")
                print()

        if result['follow_up_questions']:
            print("Follow-up questions:")
            for q in result['follow_up_questions']:
                print(f"  - {q}")

        if result['investigation_id']:
            print(f"\nInvestigation saved: {result['investigation_id']}")

    def cmd_report(self, topic: str):
        """Generate a report on a topic."""
        agent = self._get_agent()
        print(f"\nGenerating report on: '{topic}'\n")
        report = agent.generate_report(topic)
        print(report)

    def cmd_stats(self):
        """Show knowledge base statistics."""
        stats = self.kb.get_stats()
        print("\nKnowledge Base Statistics:")
        print("=" * 40)
        print(f"Files: {stats['total_files']}")
        print(f"Chunks: {stats['total_chunks']}")
        print(f"Catalogs: {stats['total_catalogs']}")
        print(f"Tags: {stats['total_tags']}")
        print(f"Relations: {stats['total_relations']}")
        print(f"Investigations: {stats['total_investigations']}")
        print(f"Journal Entries: {stats['total_journal_entries']}")
        print(f"Embeddings: {stats['total_embeddings']}")
        print(f"Total Size: {stats['total_size_bytes'] / 1024 / 1024:.2f} MB")

        if stats['files_by_type']:
            print("\nFiles by Type:")
            for ext, count in stats['files_by_type'].items():
                print(f"  {ext or 'no ext'}: {count}")

    def cmd_list(self, catalog: Optional[str] = None, limit: int = 20):
        """List files in the knowledge base."""
        catalog_id = None
        if catalog:
            catalogs = self.kb.catalog_manager.list_catalogs()
            for c in catalogs:
                if c.name == catalog:
                    catalog_id = c.catalog_id
                    break

        files = self.kb.list_files(catalog_id=catalog_id, limit=limit)
        if not files:
            print("No files found.")
            return

        print(f"\nFiles ({len(files)}):")
        print("-" * 60)
        for f in files:
            print(f"{f.filename:<40} {f.extension:<8} {f.chunk_count:>5} chunks  "
                  f"{f.size_bytes/1024:.1f}KB")

    def cmd_catalogs(self):
        """List all catalogs."""
        catalogs = self.kb.catalog_manager.list_catalogs()
        if not catalogs:
            print("No catalogs found.")
            return
        print("\nCatalogs:")
        for c in catalogs:
            file_count = len(self.kb.catalog_manager.get_catalog_files(c.catalog_id))
            print(f"  {c.name}: {c.description} ({file_count} files)")

    def cmd_tags(self):
        """List all tags."""
        tags = self.kb.tag_manager.list_tags()
        if not tags:
            print("No tags found.")
            return
        print("\nTags:")
        for t in tags:
            files = self.kb.tag_manager.get_files_by_tag(t.name)
            print(f"  {t.name}: {len(files)} files")

    def cmd_journal(self, action: str = 'list', title: Optional[str] = None,
                    content: Optional[str] = None):
        """Manage journal entries."""
        if action == 'list':
            entries = self.kb.journal_manager.list_entries(limit=20)
            if not entries:
                print("No journal entries.")
                return
            print("\nJournal Entries:")
            for e in entries:
                print(f"  [{e.created_at[:10]}] {e.title}")
        elif action == 'add' and title and content:
            entry = self.kb.journal_manager.create_entry(title=title, content=content)
            print(f"Created journal entry: {entry.entry_id}")

    def cmd_investigations(self, limit: int = 10):
        """List past investigations."""
        investigations = self.kb.investigation_store.list_investigations(limit=limit)
        if not investigations:
            print("No investigations found.")
            return
        print(f"\nPast Investigations ({len(investigations)}):")
        print("-" * 60)
        for inv in investigations:
            print(f"[{inv.created_at[:10]}] {inv.query[:70]}")
            print(f"  Sources: {len(inv.sources_used)}, Citations: {len(inv.citations)}")
            print()

    def cmd_mine_relations(self):
        """Mine relations between files."""
        print("Mining relations...")
        result = self.kb.mine_relations()
        print(f"Found {result['filename_relations']} filename relations")
        print(f"Found {result['url_relations']} URL relations")

    def cmd_rebuild_index(self):
        """Rebuild the full-text search index."""
        print("Rebuilding FTS index...")
        self.kb.rebuild_fts_index()
        print("Done.")

    def interactive(self):
        """Start an interactive session."""
        print("\nMarginalia - Personal Knowledge Management System")
        print("=" * 50)
        print("Commands: ingest, search, ask, report, stats, list,")
        print("          catalogs, tags, journal, investigations,")
        print("          mine, rebuild, quit")
        print()

        agent = self._get_agent()

        while True:
            try:
                user_input = input("marginalia> ").strip()
                if not user_input:
                    continue

                parts = user_input.split(None, 1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ''

                if cmd in ('quit', 'exit', 'q'):
                    print("Goodbye!")
                    break
                elif cmd == 'ingest':
                    self.cmd_ingest(args)
                elif cmd == 'search':
                    self.cmd_search(args)
                elif cmd == 'ask':
                    self.cmd_ask(args)
                elif cmd == 'report':
                    self.cmd_report(args)
                elif cmd == 'stats':
                    self.cmd_stats()
                elif cmd == 'list':
                    self.cmd_list()
                elif cmd == 'catalogs':
                    self.cmd_catalogs()
                elif cmd == 'tags':
                    self.cmd_tags()
                elif cmd == 'journal':
                    self.cmd_journal()
                elif cmd == 'investigations':
                    self.cmd_investigations()
                elif cmd == 'mine':
                    self.cmd_mine_relations()
                elif cmd == 'rebuild':
                    self.cmd_rebuild_index()
                elif cmd == 'reset':
                    agent.reset_conversation()
                    print("Conversation history cleared.")
                elif cmd == 'help':
                    print("Commands: ingest <path>, search <query>, ask <question>,")
                    print("          report <topic>, stats, list, catalogs, tags,")
                    print("          journal, investigations, mine, rebuild, reset, quit")
                else:
                    # Treat as a question to the agent
                    self.cmd_ask(user_input)

            except KeyboardInterrupt:
                print("\nUse 'quit' to exit.")
            except EOFError:
                break
            except Exception as e:
                logger.error(f"Command error: {e}")
                print(f"Error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def create_knowledge_base(vault_path: str = '.',
                          db_path: Optional[str] = None) -> KnowledgeBase:
    """Create a new KnowledgeBase instance."""
    return KnowledgeBase(vault_path=vault_path, db_path=db_path)


def main():
    """Main entry point for the Marginalia CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Marginalia - Personal Knowledge Management System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  marginalia ingest ~/Documents/research
  marginalia search "machine learning papers"
  marginalia ask "What are the main themes in my notes?"
  marginalia report "Summary of my research on climate change"
  marginalia stats
  marginalia interactive
        """
    )

    parser.add_argument('--vault', default='.', help='Path to vault directory')
    parser.add_argument('--db', default=None, help='Path to database file')

    subparsers = parser.add_subparsers(dest='command')

    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Ingest files')
    ingest_parser.add_argument('path', help='File or directory to ingest')
    ingest_parser.add_argument('--catalog', help='Catalog name')
    ingest_parser.add_argument('--tags', help='Comma-separated tags')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search knowledge base')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=10)
    search_parser.add_argument('--semantic', action='store_true')
    search_parser.add_argument('--rerank', action='store_true', default=True)

    # Ask command
    ask_parser = subparsers.add_parser('ask', help='Ask the research agent')
    ask_parser.add_argument('query', help='Question to ask')
    ask_parser.add_argument('--no-save', action='store_true')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate a report')
    report_parser.add_argument('topic', help='Report topic')

    # Stats command
    subparsers.add_parser('stats', help='Show statistics')

    # List command
    list_parser = subparsers.add_parser('list', help='List files')
    list_parser.add_argument('--catalog', help='Filter by catalog')
    list_parser.add_argument('--limit', type=int, default=20)

    # Interactive command
    subparsers.add_parser('interactive', help='Start interactive session')

    # Mine command
    subparsers.add_parser('mine', help='Mine relations between files')

    # Rebuild command
    subparsers.add_parser('rebuild', help='Rebuild search index')

    args = parser.parse_args()

    cli = MarginaliaCLI(vault_path=args.vault)

    if args.command == 'ingest':
        cli.cmd_ingest(args.path, catalog=args.catalog, tags=args.tags)
    elif args.command == 'search':
        cli.cmd_search(args.query, limit=args.limit,
                       semantic=args.semantic, rerank=args.rerank)
    elif args.command == 'ask':
        cli.cmd_ask(args.query, save=not args.no_save)
    elif args.command == 'report':
        cli.cmd_report(args.topic)
    elif args.command == 'stats':
        cli.cmd_stats()
    elif args.command == 'list':
        cli.cmd_list(catalog=args.catalog, limit=args.limit)
    elif args.command == 'interactive':
        cli.interactive()
    elif args.command == 'mine':
        cli.cmd_mine_relations()
    elif args.command == 'rebuild':
        cli.cmd_rebuild_index()
    else:
        # Default to interactive
        cli.interactive()


if __name__ == '__main__':
    main()