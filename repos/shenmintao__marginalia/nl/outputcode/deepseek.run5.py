import sqlite3
import json
import hashlib
import datetime
import re
import os
import shutil
import tempfile
import zipfile
import tarfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union, Generator
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
import warnings
import csv
import io
import sys

# Optional heavy libraries
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    from PIL import Image
    import PIL.ExifTags
except ImportError:
    Image = None

try:
    import numpy as np
except ImportError:
    np = None

# ------------------------------------------------------------------------------
# Database schema and manager
# ------------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    file_type TEXT NOT NULL,
    title TEXT,
    content TEXT,
    plain_text TEXT,
    metadata JSON,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_date TIMESTAMP,
    hash TEXT,
    archive_member TEXT,
    is_archive INTEGER DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    title, content, plain_text, content='documents', content_rowid='id'
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS document_tags (
    doc_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (doc_id, tag_id),
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    query_definition TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS investigation_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    answer TEXT,
    citations TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER,
    entry_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content TEXT NOT NULL,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE SET NULL
);
"""

class Database:
    def __init__(self, db_path: str = "marginalia.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.executescript(SCHEMA)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()

    def insert_document(self, file_path: str, file_type: str, title: str,
                        content: str, plain_text: str = None, metadata: Dict = None,
                        modified_date: float = None, hash: str = None,
                        archive_member: str = None, is_archive: bool = False) -> int:
        cursor = self.conn.execute("""
            INSERT OR REPLACE INTO documents (file_path, file_type, title, content, plain_text, metadata, modified_date, hash, archive_member, is_archive)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (file_path, file_type, title, content, plain_text,
              json.dumps(metadata) if metadata else None,
              modified_date, hash, archive_member, 1 if is_archive else 0))
        return cursor.lastrowid

    def delete_document(self, doc_id: int):
        self.conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self.conn.execute("DELETE FROM document_tags WHERE doc_id = ?", (doc_id,))

    def get_document(self, doc_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()

    def get_document_by_path(self, file_path: str) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM documents WHERE file_path = ?", (file_path,)).fetchone()

    def add_tag(self, name: str) -> int:
        cursor = self.conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
        tag_id = cursor.lastrowid or self.conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()[0]
        return tag_id

    def tag_document(self, doc_id: int, tag_id: int):
        self.conn.execute("INSERT OR IGNORE INTO document_tags (doc_id, tag_id) VALUES (?, ?)", (doc_id, tag_id))

    def remove_tag_from_document(self, doc_id: int, tag_id: int):
        self.conn.execute("DELETE FROM document_tags WHERE doc_id = ? AND tag_id = ?", (doc_id, tag_id))

    def get_document_tags(self, doc_id: int) -> List[str]:
        rows = self.conn.execute("""
            SELECT t.name FROM tags t JOIN document_tags dt ON t.id = dt.tag_id WHERE dt.doc_id = ?
        """, (doc_id,)).fetchall()
        return [row[0] for row in rows]

    def save_view(self, name: str, query_def: str):
        self.conn.execute("INSERT OR REPLACE INTO views (name, query_definition) VALUES (?, ?)", (name, query_def))

    def get_view(self, name: str) -> Optional[str]:
        row = self.conn.execute("SELECT query_definition FROM views WHERE name = ?", (name,)).fetchone()
        return row[0] if row else None

    def add_investigation_note(self, query: str, answer: str, citations: List[Dict] = None,
                               metadata: Dict = None):
        self.conn.execute("""
            INSERT INTO investigation_notes (query, answer, citations, metadata)
            VALUES (?, ?, ?, ?)
        """, (query, answer, json.dumps(citations) if citations else None,
              json.dumps(metadata) if metadata else None))

    def add_journal_entry(self, content: str, doc_id: Optional[int] = None):
        self.conn.execute("INSERT INTO journal_entries (doc_id, content) VALUES (?, ?)", (doc_id, content))

    def rebuild_fts(self):
        self.conn.execute("INSERT INTO documents_fts(documents_fts) VALUES('rebuild')")


# ------------------------------------------------------------------------------
# File parsers
# ------------------------------------------------------------------------------

class FileParser(ABC):
    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        pass

    @abstractmethod
    def parse(self, file_path: Path) -> Dict[str, Any]:
        """Return dict with keys: content (html/markdown), plain_text, metadata, title."""
        pass


class TextParser(FileParser):
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in ['.txt', '.log', '.csv', '.tsv']

    def parse(self, file_path: Path) -> Dict:
        try:
            text = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            text = file_path.read_text(errors='ignore')
        title = file_path.stem
        return {
            'content': f"<pre>{text}</pre>",
            'plain_text': text,
            'metadata': {'encoding': 'utf-8'},
            'title': title
        }

class MarkdownParser(FileParser):
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in ['.md', '.markdown']

    def parse(self, file_path: Path) -> Dict:
        text = file_path.read_text(encoding='utf-8', errors='ignore')
        # Simple extraction of title from first heading
        title = file_path.stem
        for line in text.splitlines():
            if line.startswith('# '):
                title = line[2:].strip()
                break
        return {
            'content': text,  # store raw markdown
            'plain_text': text,  # could convert to plain text, keep as is for now
            'metadata': {},
            'title': title
        }

class PDFParser(FileParser):
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.pdf'

    def parse(self, file_path: Path) -> Dict:
        if PyPDF2 is None:
            raise ImportError("PyPDF2 is required for PDF parsing")
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
            full_text = "\n".join(text_parts)
            metadata = {}
            if reader.metadata:
                for key, value in reader.metadata.items():
                    if key.startswith('/'):
                        metadata[key[1:]] = str(value)
            title = metadata.get('Title') or file_path.stem
        return {
            'content': full_text,
            'plain_text': full_text,
            'metadata': metadata,
            'title': title
        }

class DocxParser(FileParser):
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.docx'

    def parse(self, file_path: Path) -> Dict:
        if DocxDocument is None:
            raise ImportError("python-docx is required for DOCX parsing")
        doc = DocxDocument(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        text = "\n".join(full_text)
        metadata = {}
        if doc.core_properties:
            cp = doc.core_properties
            metadata['title'] = cp.title
            metadata['author'] = cp.author
            metadata['created'] = str(cp.created) if cp.created else None
        title = metadata.get('title') or file_path.stem
        return {
            'content': text,
            'plain_text': text,
            'metadata': metadata,
            'title': title
        }

class SpreadsheetParser(FileParser):
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in ['.xlsx', '.xls', '.ods']

    def parse(self, file_path: Path) -> Dict:
        if file_path.suffix.lower() == '.csv':
            return TextParser().parse(file_path)
        if openpyxl is None:
            raise ImportError("openpyxl required for spreadsheet parsing")
        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheets_data = {}
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = []
            for row in ws.iter_rows(values_only=True):
                rows.append([str(cell) if cell is not None else '' for cell in row])
            sheets_data[sheet_name] = rows
        # Represent as simple JSON for content; plain text summary
        plain = json.dumps({name: rows for name, rows in sheets_data.items()}, indent=2)
        title = file_path.stem
        return {
            'content': plain,
            'plain_text': plain,
            'metadata': {'sheets': list(sheets_data.keys())},
            'title': title
        }

class ImageParser(FileParser):
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']

    def parse(self, file_path: Path) -> Dict:
        if Image is None:
            raise ImportError("Pillow is required for image metadata parsing")
        metadata = {}
        plain_text = ""
        try:
            with Image.open(file_path) as img:
                exif = img._getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag = PIL.ExifTags.TAGS.get(tag_id, tag_id)
                        metadata[tag] = str(value)
                # Basic placeholder for OCR
                # In real implementation, run OCR here.
                plain_text = f"[Image: {file_path.name}]"
                # metadata['dimensions'] = img.size
        except Exception:
            plain_text = f"[Image load error: {file_path.name}]"
        return {
            'content': f'<img src="{file_path.name}"/>',
            'plain_text': plain_text,
            'metadata': metadata,
            'title': file_path.stem
        }

class ArchiveParser(FileParser):
    """Treats archive as container; returns member list as metadata, not content."""
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in ['.zip', '.tar', '.gz', '.bz2', '.7z']

    def parse(self, file_path: Path) -> Dict:
        members = []
        if zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path, 'r') as zf:
                members = zf.namelist()
        elif tarfile.is_tarfile(file_path):
            with tarfile.open(file_path, 'r:*') as tf:
                members = tf.getnames()
        else:
            members = []
        plain_text = f"Archive with {len(members)} members: " + ", ".join(members[:20])
        return {
            'content': plain_text,
            'plain_text': plain_text,
            'metadata': {'members': members},
            'title': file_path.stem,
            'is_archive': True
        }


# ------------------------------------------------------------------------------
# Ingestion
# ------------------------------------------------------------------------------

class IngestionPipeline:
    def __init__(self, db: Database, root_path: Path):
        self.db = db
        self.root_path = root_path.resolve()
        self.parsers: List[FileParser] = [
            MarkdownParser(),
            PDFParser(),
            DocxParser(),
            SpreadsheetParser(),
            ImageParser(),
            ArchiveParser(),
            TextParser()  # fallback
        ]

    def walk_and_ingest(self):
        for file_path in self.root_path.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                if self.should_process(file_path):
                    self.ingest_file(file_path)

    def should_process(self, file_path: Path) -> bool:
        # Skip database file and known temporary
        if file_path.name == 'marginalia.db':
            return False
        return True

    def ingest_file(self, file_path: Path):
        rel_path = file_path.relative_to(self.root_path)
        str_path = str(rel_path)
        parser = self.select_parser(file_path)
        if parser is None:
            return

        try:
            parsed = parser.parse(file_path)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}", file=sys.stderr)
            return

        is_archive = parsed.pop('is_archive', False)
        file_type = file_path.suffix.lower().lstrip('.')
        modified_date = file_path.stat().st_mtime
        hash_ = self.compute_hash(file_path)

        # If archive, also ingest each member as separate doc
        if is_archive:
            # Store the archive itself with minimal info
            self.db.insert_document(
                file_path=str_path,
                file_type=file_type,
                title=parsed['title'],
                content=parsed['plain_text'],
                plain_text=parsed['plain_text'],
                metadata=parsed['metadata'],
                modified_date=modified_date,
                hash=hash_,
                is_archive=True
            )
            # Ingest members from archive
            self.ingest_archive_members(file_path, parsed['metadata'].get('members', []))
        else:
            self.db.insert_document(
                file_path=str_path,
                file_type=file_type,
                title=parsed['title'],
                content=parsed['content'],
                plain_text=parsed.get('plain_text', parsed['content']),
                metadata=parsed['metadata'],
                modified_date=modified_date,
                hash=hash_
            )

    def ingest_archive_members(self, archive_path: Path, members: List[str]):
        arc_path = archive_path
        rel_arc_path = str(arc_path.relative_to(self.root_path))
        temp_dir = tempfile.mkdtemp()
        try:
            if zipfile.is_zipfile(arc_path):
                with zipfile.ZipFile(arc_path, 'r') as zf:
                    for member in members:
                        try:
                            extracted_path = zf.extract(member, temp_dir)
                            member_file = Path(extracted_path)
                            self._ingest_member_file(member_file, rel_arc_path, member)
                        except Exception:
                            pass
            elif tarfile.is_tarfile(arc_path):
                with tarfile.open(arc_path, 'r:*') as tf:
                    for member in members:
                        try:
                            tf.extract(member, temp_dir)
                            member_file = Path(temp_dir) / member
                            self._ingest_member_file(member_file, rel_arc_path, member)
                        except Exception:
                            pass
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _ingest_member_file(self, member_file: Path, archive_rel: str, member_name: str):
        if not member_file.is_file():
            return
        # Use same parsers but with path pointing to archive
        parser = self.select_parser(member_file)
        if parser is None:
            return
        try:
            parsed = parser.parse(member_file)
        except Exception:
            return
        # Store with special archive_member field, path is archive path
        self.db.insert_document(
            file_path=archive_rel,
            file_type=member_file.suffix.lower().lstrip('.'),
            title=f"{parsed['title']} (in {Path(archive_rel).name})",
            content=parsed['content'],
            plain_text=parsed.get('plain_text', parsed['content']),
            metadata=parsed.get('metadata', {}),
            modified_date=member_file.stat().st_mtime,
            hash=self.compute_hash(member_file),
            archive_member=member_name
        )

    def select_parser(self, file_path: Path) -> Optional[FileParser]:
        for parser in self.parsers:
            if parser.can_handle(file_path):
                return parser
        return None

    def compute_hash(self, file_path: Path) -> str:
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()


# ------------------------------------------------------------------------------
# Catalog & tags
# ------------------------------------------------------------------------------

class CatalogManager:
    def __init__(self, db: Database):
        self.db = db

    def tag_document(self, doc_id: int, tag_name: str):
        tag_id = self.db.add_tag(tag_name)
        self.db.tag_document(doc_id, tag_id)

    def untag_document(self, doc_id: int, tag_name: str):
        tag = self.db.conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,)).fetchone()
        if tag:
            self.db.remove_tag_from_document(doc_id, tag[0])

    def get_tags(self, doc_id: int) -> List[str]:
        return self.db.get_document_tags(doc_id)

    def search_by_tag(self, tag_name: str) -> List[int]:
        rows = self.db.conn.execute("""
            SELECT d.id FROM documents d
            JOIN document_tags dt ON d.id = dt.doc_id
            JOIN tags t ON dt.tag_id = t.id
            WHERE t.name = ?
        """, (tag_name,)).fetchall()
        return [row[0] for row in rows]

    def save_view(self, name: str, query_definition: str):
        self.db.save_view(name, query_definition)

    def get_view(self, name: str) -> Optional[str]:
        return self.db.get_view(name)

    def journal_entry(self, content: str, doc_id: Optional[int] = None):
        self.db.add_journal_entry(content, doc_id)

    # Relation mining: simple co-occurrence by tags
    def find_related_docs(self, doc_id: int, max_results: int = 10) -> List[int]:
        tags = set(self.get_tags(doc_id))
        if not tags:
            return []
        placeholders = ','.join('?' for _ in tags)
        query = f"""
            SELECT dt2.doc_id, COUNT(*) as common
            FROM document_tags dt1
            JOIN document_tags dt2 ON dt1.tag_id = dt2.tag_id AND dt1.doc_id != dt2.doc_id
            WHERE dt1.doc_id = ? AND dt2.tag_id IN (
                SELECT id FROM tags WHERE name IN ({placeholders})
            )
            GROUP BY dt2.doc_id
            ORDER BY common DESC
            LIMIT ?
        """
        rows = self.db.conn.execute(query, (doc_id, *tags, max_results)).fetchall()
        return [row[0] for row in rows]


# ------------------------------------------------------------------------------
# Search Engine with FTS5 + optional embeddings
# ------------------------------------------------------------------------------

class SearchEngine:
    def __init__(self, db: Database, config: Dict[str, Any] = None):
        self.db = db
        self.config = config or {}
        self.use_embeddings = self.config.get('use_embeddings', False)
        self.embedding_model = None
        if self.use_embeddings:
            self._init_embeddings()

    def _init_embeddings(self):
        try:
            from sentence_transformers import SentenceTransformer
            model_name = self.config.get('embedding_model', 'all-MiniLM-L6-v2')
            self.embedding_model = SentenceTransformer(model_name)
            self._build_vector_index()
        except ImportError:
            warnings.warn("sentence-transformers not available; embedding search disabled.")
            self.use_embeddings = False
        except Exception as e:
            warnings.warn(f"Failed to load embedding model: {e}")
            self.use_embeddings = False

    def _build_vector_index(self):
        # Store embeddings in a separate table or in memory
        # For simplicity, create a table if not exists
        self.db.conn.execute("CREATE TABLE IF NOT EXISTS doc_vectors (doc_id INTEGER PRIMARY KEY, vector BLOB)")
        docs = self.db.conn.execute("SELECT id, plain_text FROM documents WHERE plain_text IS NOT NULL").fetchall()
        for row in docs:
            if self.db.conn.execute("SELECT 1 FROM doc_vectors WHERE doc_id=?", (row['id'],)).fetchone():
                continue
            vec = self._encode_text(row['plain_text'])
            if vec is not None:
                self.db.conn.execute("INSERT OR REPLACE INTO doc_vectors (doc_id, vector) VALUES (?, ?)",
                                     (row['id'], vec.tobytes()))

    def _encode_text(self, text: str) -> Optional[np.ndarray]:
        if not self.embedding_model:
            return None
        return self.embedding_model.encode(text[:2000])  # limit length

    def _cosine_similarity(self, a, b):
        if np is None:
            return 0.0
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def lexical_search(self, query: str, limit: int = 10, offset: int = 0) -> List[Tuple[int, float]]:
        # FTS5 BM25 similarity
        cursor = self.db.conn.execute("""
            SELECT docid as doc_id, rank as score
            FROM documents_fts
            WHERE documents_fts MATCH ?
            ORDER BY rank
            LIMIT ? OFFSET ?
        """, (query, limit, offset))
        return [(row['doc_id'], -row['score']) for row in cursor]

    def vector_search(self, query: str, limit: int = 10) -> List[Tuple[int, float]]:
        if not self.use_embeddings or self.embedding_model is None:
            return []
        query_vec = self._encode_text(query)
        if query_vec is None:
            return []
        # Retrieve all vectors and compute similarity (brute force)
        results = []
        rows = self.db.conn.execute("SELECT doc_id, vector FROM doc_vectors").fetchall()
        for row in rows:
            if row['vector'] is None:
                continue
            doc_vec = np.frombuffer(row['vector'])
            sim = self._cosine_similarity(query_vec, doc_vec)
            results.append((row['doc_id'], sim))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def combined_search(self, query: str, limit: int = 10, rerank: bool = False):
        lexical = self.lexical_search(query, limit=limit * 2)
        if not self.use_embeddings:
            return lexical[:limit]
        vector = self.vector_search(query, limit=limit * 2)
        # Reciprocal rank fusion or simple score merging
        lex_scores = {doc_id: score for doc_id, score in lexical}
        vec_scores = {doc_id: score for doc_id, score in vector}
        all_ids = set(lex_scores) | set(vec_scores)
        combined = []
        for doc_id in all_ids:
            l = lex_scores.get(doc_id, 0.0)
            v = vec_scores.get(doc_id, 0.0)
            combined_score = 0.7 * l + 0.3 * v  # weight lexical more
            combined.append((doc_id, combined_score))
        combined.sort(key=lambda x: x[1], reverse=True)
        return combined[:limit]

    def search_with_quota(self, query: str, limit: int = 10, source_quota: Dict[str, int] = None) -> List[int]:
        """source_quota: e.g. {'pdf': 3, 'docx': 2}, limits results per file type."""
        results = self.lexical_search(query, limit=limit * 2)  # get more to apply quota
        if not source_quota:
            return [doc_id for doc_id, _ in results[:limit]]
        counted = {}
        final = []
        for doc_id, score in results:
            doc = self.db.get_document(doc_id)
            if not doc:
                continue
            ftype = doc['file_type']
            if ftype in source_quota and counted.get(ftype, 0) >= source_quota[ftype]:
                continue
            final.append(doc_id)
            counted[ftype] = counted.get(ftype, 0) + 1
            if len(final) >= limit:
                break
        return final


# ------------------------------------------------------------------------------
# Reader: extracts specific windows
# ------------------------------------------------------------------------------

class Reader:
    def __init__(self, db: Database, root_path: Path):
        self.db = db
        self.root_path = root_path

    def get_document_fulltext(self, doc_id: int) -> str:
        doc = self.db.get_document(doc_id)
        if not doc:
            return ""
        if doc['is_archive']:
            return self._archive_summary(doc)
        if doc['archive_member']:
            return self._read_archive_member(doc)
        # normal file, read the plain_text from db or file
        if doc['plain_text']:
            return doc['plain_text']
        return self._read_file_text(doc['file_path'])

    def read_section(self, doc_id: int, section_title: str) -> str:
        """For markdown, find heading and return until next heading."""
        full = self.get_document_fulltext(doc_id)
        pattern = re.compile(r'^#+\s+' + re.escape(section_title) + r'\s*$', re.MULTILINE)
        match = pattern.search(full)
        if not match:
            return ""
        start = match.end()
        next_heading = re.search(r'^#+\s', full[start:], re.MULTILINE)
        if next_heading:
            return full[start:start + next_heading.start()]
        else:
            return full[start:]

    def read_lines(self, doc_id: int, start_line: int, end_line: int) -> str:
        full = self.get_document_fulltext(doc_id)
        lines = full.splitlines()
        return "\n".join(lines[start_line:end_line])

    def read_pages(self, doc_id: int, start_page: int, end_page: int) -> str:
        doc = self.db.get_document(doc_id)
        if not doc or doc['file_type'] != 'pdf':
            return ""
        file_path = self.root_path / doc['file_path']
        if file_path.exists():
            return self._extract_pdf_pages(file_path, start_page, end_page)
        return ""

    def _extract_pdf_pages(self, file_path: Path, start: int, end: int) -> str:
        if PyPDF2 is None:
            return ""
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            pages = []
            for i in range(start - 1, min(end, len(reader.pages))):
                pages.append(reader.pages[i].extract_text() or "")
        return "\n".join(pages)

    def read_archive_member(self, doc_id: int) -> str:
        doc = self.db.get_document(doc_id)
        if not doc or not doc['archive_member']:
            return ""
        archive_path = self.root_path / doc['file_path']
        if not archive_path.exists():
            return ""
        member = doc['archive_member']
        return self._extract_member_text(archive_path, member)

    def _read_archive_member(self, doc_record) -> str:
        return self.read_archive_member(doc_record['id'])

    def _extract_member_text(self, archive_path: Path, member: str) -> str:
        temp_dir = tempfile.mkdtemp()
        try:
            if zipfile.is_zipfile(archive_path):
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extract(member, temp_dir)
                    member_file = Path(temp_dir) / member
                    return self._read_file_text(str(member_file))
            elif tarfile.is_tarfile(archive_path):
                with tarfile.open(archive_path, 'r:*') as tf:
                    tf.extract(member, temp_dir)
                    member_file = Path(temp_dir) / member
                    return self._read_file_text(str(member_file))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return ""

    def read_table_slice(self, doc_id: int, sheet: str = None, rows: Tuple[int, int] = None,
                         columns: Tuple[int, int] = None) -> str:
        doc = self.db.get_document(doc_id)
        if not doc or doc['file_type'] not in ['xlsx', 'xls', 'ods']:
            return ""
        file_path = self.root_path / doc['file_path']
        if not file_path.exists():
            return ""
        if openpyxl is None:
            return ""
        wb = openpyxl.load_workbook(file_path, data_only=True)
        if sheet:
            ws = wb[sheet]
        else:
            ws = wb.active
        data = []
        for row in ws.iter_rows(min_row=rows[0] if rows else 1,
                                max_row=rows[1] if rows else ws.max_row,
                                min_col=columns[0] if columns else 1,
                                max_col=columns[1] if columns else ws.max_column,
                                values_only=True):
            data.append([str(cell) if cell is not None else '' for cell in row])
        return json.dumps(data, indent=2)

    def _read_file_text(self, file_path: str) -> str:
        try:
            return Path(file_path).read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return ""

    def _archive_summary(self, doc) -> str:
        return doc.get('plain_text') or "[Archive summary]"


# ------------------------------------------------------------------------------
# LLM Handler (placehoder)
# ------------------------------------------------------------------------------

class LLMHandler:
    def __init__(self, model_name: str = "gpt-3.5-turbo", api_key: str = None):
        self.model = model_name
        self.api_key = api_key
        # In real implementation, use openai or llama.cpp.

    def generate_answer(self, query: str, context_docs: List[Tuple[int, str]]) -> Dict:
        """Returns answer text and list of citations (doc_id, snippet)."""
        # Simulate: combine contexts into a prompt and return mock answer.
        prompt = f"Query: {query}\n\nContext:\n"
        citations = []
        for doc_id, text in context_docs:
            snippet = text[:200] + ("..." if len(text) > 200 else "")
            prompt += f"[{doc_id}] {snippet}\n"
            citations.append({"doc_id": doc_id, "snippet": snippet})
        prompt += "\nProvide a cited answer."
        # Mock answer
        answer = f"Based on the provided context, the answer is simulated from {len(context_docs)} documents."
        # In real system, call API
        return {"answer": answer, "citations": citations}


# ------------------------------------------------------------------------------
# Investigation Notes
# ------------------------------------------------------------------------------

class InvestigationNotes:
    def __init__(self, db: Database):
        self.db = db

    def save_note(self, query: str, answer: str, citations: List[Dict]):
        self.db.add_investigation_note(query, answer, citations)

    def get_notes(self, limit: int = 10) -> List[sqlite3.Row]:
        return self.db.conn.execute(
            "SELECT * FROM investigation_notes ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()


# ------------------------------------------------------------------------------
# Relation Mining (simple)
# ------------------------------------------------------------------------------

class RelationMiner:
    def __init__(self, db: Database, catalog: CatalogManager):
        self.db = db
        self.catalog = catalog

    def find_similar(self, doc_id: int, max_results: int = 10) -> List[int]:
        # Based on shared tags
        return self.catalog.find_related_docs(doc_id, max_results)


# ------------------------------------------------------------------------------
# Marginalia Main System
# ------------------------------------------------------------------------------

class Marginalia:
    def __init__(self, root_path: str = ".", db_path: str = "marginalia.db",
                 config: Dict = None):
        self.root_path = Path(root_path).resolve()
        self.db_path = db_path
        self.config = config or {}
        self.db = Database(db_path)
        self.catalog = CatalogManager(self.db)
        self.search_engine = SearchEngine(self.db, config)
        self.reader = Reader(self.db, self.root_path)
        self.llm = LLMHandler(model_name=config.get('model', 'gpt-3.5-turbo'))
        self.investigation_notes = InvestigationNotes(self.db)
        self.relation_miner = RelationMiner(self.db, self.catalog)
        self.pipeline = IngestionPipeline(self.db, self.root_path)

    def ingest(self):
        print("Running ingestion...")
        self.pipeline.walk_and_ingest()
        self.db.rebuild_fts()
        if self.config.get('use_embeddings', False):
            self.search_engine._build_vector_index()

    def search(self, query: str, limit: int = 10, source_quota: Dict = None) -> List[Dict]:
        doc_ids = self.search_engine.search_with_quota(query, limit, source_quota)
        results = []
        for doc_id in doc_ids:
            doc = self.db.get_document(doc_id)
            if doc:
                results.append(dict(doc))
        return results

    def answer_question(self, query: str, context_limit: int = 5) -> Dict:
        # Retrieve relevant documents
        results = self.search(query, limit=context_limit)
        contexts = []
        for doc in results:
            text = self.reader.get_document_fulltext(doc['id'])
            contexts.append((doc['id'], text))
        # Optionally refine windows: if question mentions specific section, etc.
        response = self.llm.generate_answer(query, contexts)
        # Save investigation note
        self.investigation_notes.save_note(query, response['answer'], response['citations'])
        return response

    def write_report(self, query: str, output_path: str = None):
        """Generate a cited report."""
        response = self.answer_question(query, context_limit=10)
        report = f"# Report: {query}\n\n{response['answer']}\n\n## Citations\n"
        for cite in response['citations']:
            report += f"- Doc {cite['doc_id']}: {cite['snippet']}\n"
        if output_path:
            Path(output_path).write_text(report)
        return report

    def add_journal_entry(self, content: str):
        self.catalog.journal_entry(content)


# ------------------------------------------------------------------------------
# Command Line Interface
# ------------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Marginalia: Personal Knowledge Management with LLM agents")
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Ingest
    ingest_parser = subparsers.add_parser('ingest', help='Index the knowledge base')

    # Search
    search_parser = subparsers.add_parser('search', help='Search documents')
    search_parser.add_argument('query', type=str)
    search_parser.add_argument('--limit', type=int, default=10)
    search_parser.add_argument('--quota', type=str, help='Source quotas, e.g. pdf:2,docx:1')

    # Answer
    answer_parser = subparsers.add_parser('answer', help='Generate a cited answer')
    answer_parser.add_argument('query', type=str)
    answer_parser.add_argument('--context-limit', type=int, default=5)

    # Report
    report_parser = subparsers.add_parser('report', help='Generate a report')
    report_parser.add_argument('query', type=str)
    report_parser.add_argument('--output', type=str, default='report.md')

    # Journal
    journal_parser = subparsers.add_parser('journal', help='Add a journal entry')
    journal_parser.add_argument('content', type=str)

    # Global options
    parser.add_argument('--root', type=str, default=os.getcwd(), help='Root directory of knowledge base')
    parser.add_argument('--db', type=str, default='marginalia.db', help='Database path')
    parser.add_argument('--use-embeddings', action='store_true', help='Enable vector search')

    args = parser.parse_args()

    config = {
        'use_embeddings': args.use_embeddings,
        'embedding_model': 'all-MiniLM-L6-v2',
        'model': 'gpt-3.5-turbo'  # placeholder
    }

    app = Marginalia(root_path=args.root, db_path=args.db, config=config)

    if args.command == 'ingest':
        app.ingest()
        print("Ingestion complete.")
    elif args.command == 'search':
        quota = None
        if args.quota:
            quota = {}
            for pair in args.quota.split(','):
                k, v = pair.split(':')
                quota[k] = int(v)
        results = app.search(args.query, limit=args.limit, source_quota=quota)
        for r in results:
            print(f"ID:{r['id']} [{r['file_type']}] {r['title']} - {r['file_path']}")
    elif args.command == 'answer':
        response = app.answer_question(args.query, context_limit=args.context_limit)
        print("Answer:", response['answer'])
        print("Citations:", json.dumps(response['citations'], indent=2))
    elif args.command == 'report':
        report = app.write_report(args.query, args.output)
        print(f"Report written to {args.output}")
    elif args.command == 'journal':
        app.add_journal_entry(args.content)
        print("Journal entry added.")
    else:
        parser.print_help()

if __name__ == '__main__':
    main()