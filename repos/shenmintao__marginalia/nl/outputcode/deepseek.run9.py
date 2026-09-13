import os
import json
import sqlite3
import hashlib
import datetime
from typing import List, Dict, Set, Optional, Union, Tuple, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from pathlib import Path
import re
import mimetypes
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("marginalia")


# ------------------------------------------------------------------------------
# Data Models
# ------------------------------------------------------------------------------
@dataclass
class FileItem:
    id: int
    path: str
    name: str
    is_dir: bool
    mime_type: str
    size: int
    modified: datetime.datetime
    catalog: str = "" 
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_text: Optional[str] = None


@dataclass
class JournalEntry:
    id: int
    timestamp: datetime.datetime
    content: str
    linked_file_ids: List[int] = field(default_factory=list)


@dataclass
class Relation:
    id: int
    from_id: int
    to_id: int
    relation_type: str
    weight: float = 1.0


# ------------------------------------------------------------------------------
# Database Manager
# ------------------------------------------------------------------------------
class LibraryDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._create_tables()
        self._enable_fts()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                is_dir INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                size INTEGER NOT NULL,
                modified TIMESTAMP NOT NULL,
                catalog TEXT DEFAULT '',
                content_text TEXT
            );

            CREATE TABLE IF NOT EXISTS tags (
                file_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
                PRIMARY KEY (file_id, tag)
            );

            CREATE TABLE IF NOT EXISTS metadata (
                file_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
                PRIMARY KEY (file_id, key)
            );

            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                content TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS journal_links (
                journal_id INTEGER NOT NULL,
                file_id INTEGER NOT NULL,
                FOREIGN KEY (journal_id) REFERENCES journal(id) ON DELETE CASCADE,
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
                PRIMARY KEY (journal_id, file_id)
            );

            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id INTEGER NOT NULL,
                to_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                FOREIGN KEY (from_id) REFERENCES files(id) ON DELETE CASCADE,
                FOREIGN KEY (to_id) REFERENCES files(id) ON DELETE CASCADE,
                UNIQUE(from_id, to_id, relation_type)
            );

            CREATE TABLE IF NOT EXISTS investigation_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                question TEXT,
                answer TEXT,
                citations TEXT
            );
        """)
        self.conn.commit()

    def _enable_fts(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM files_fts LIMIT 0")
        except sqlite3.OperationalError:
            cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(content_text, content='files', content_rowid='id')")
            # triggers to keep FTS in sync (simplified: we will update manually after insert/update)
            self.conn.commit()
        self.conn.execute("PRAGMA foreign_keys = ON")

    def add_file(self, item: FileItem) -> int:
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO files (path, name, is_dir, mime_type, size, modified, catalog, content_text) VALUES (?,?,?,?,?,?,?,?)",
                (item.path, item.name, int(item.is_dir), item.mime_type, item.size, item.modified.isoformat(), item.catalog, item.content_text)
            )
            file_id = cursor.lastrowid
            # tags
            for tag in item.tags:
                cursor.execute("INSERT OR IGNORE INTO tags (file_id, tag) VALUES (?,?)", (file_id, tag))
            # metadata
            for k, v in item.metadata.items():
                cursor.execute("INSERT OR REPLACE INTO metadata (file_id, key, value) VALUES (?,?,?)", (file_id, k, str(v)))
            # update FTS
            if item.content_text:
                cursor.execute("INSERT INTO files_fts (rowid, content_text) VALUES (?,?)", (file_id, item.content_text))
            self.conn.commit()
            return file_id
        except sqlite3.IntegrityError:
            # file already exists
            return self.update_file(item)

    def update_file(self, item: FileItem):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE files SET name=?, mime_type=?, size=?, modified=?, catalog=?, content_text=? WHERE path=?",
            (item.name, item.mime_type, item.size, item.modified.isoformat(), item.catalog, item.content_text, item.path)
        )
        # keep id
        cursor.execute("SELECT id FROM files WHERE path=?", (item.path,))
        row = cursor.fetchone()
        if not row:
            # insert instead
            return self.add_file(item)
        file_id = row[0]
        # replace tags/metadata (simple: delete then insert)
        cursor.execute("DELETE FROM tags WHERE file_id=?", (file_id,))
        cursor.execute("DELETE FROM metadata WHERE file_id=?", (file_id,))
        for tag in item.tags:
            cursor.execute("INSERT OR IGNORE INTO tags (file_id, tag) VALUES (?,?)", (file_id, tag))
        for k, v in item.metadata.items():
            cursor.execute("INSERT OR REPLACE INTO metadata (file_id, key, value) VALUES (?,?,?)", (file_id, k, str(v)))
        # update FTS
        cursor.execute("DELETE FROM files_fts WHERE rowid=?", (file_id,))
        if item.content_text:
            cursor.execute("INSERT INTO files_fts (rowid, content_text) VALUES (?,?)", (file_id, item.content_text))
        self.conn.commit()
        return file_id

    def remove_file(self, path: str):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM files WHERE path=?", (path,))
        self.conn.commit()

    def get_file_by_path(self, path: str) -> Optional[FileItem]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, path, name, is_dir, mime_type, size, modified, catalog, content_text FROM files WHERE path=?", (path,))
        row = cursor.fetchone()
        if row:
            return self._row_to_item(row)
        return None

    def get_file_by_id(self, file_id: int) -> Optional[FileItem]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, path, name, is_dir, mime_type, size, modified, catalog, content_text FROM files WHERE id=?", (file_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_item(row)
        return None

    def _row_to_item(self, row) -> FileItem:
        file_id, path, name, is_dir, mime_type, size, modified_str, catalog, content_text = row
        tags = self._get_tags(file_id)
        meta = self._get_metadata(file_id)
        modified = datetime.datetime.fromisoformat(modified_str)
        return FileItem(
            id=file_id, path=path, name=name, is_dir=bool(is_dir),
            mime_type=mime_type, size=size, modified=modified,
            catalog=catalog, tags=tags, metadata=meta, content_text=content_text
        )

    def _get_tags(self, file_id: int) -> Set[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT tag FROM tags WHERE file_id=?", (file_id,))
        return {row[0] for row in cursor.fetchall()}

    def _get_metadata(self, file_id: int) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM metadata WHERE file_id=?", (file_id,))
        return {row[0]: row[1] for row in cursor.fetchall()}

    def add_journal(self, entry: JournalEntry) -> int:
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO journal (timestamp, content) VALUES (?,?)", (entry.timestamp.isoformat(), entry.content))
        journal_id = cursor.lastrowid
        for fid in entry.linked_file_ids:
            cursor.execute("INSERT INTO journal_links (journal_id, file_id) VALUES (?,?)", (journal_id, fid))
        self.conn.commit()
        return journal_id

    def get_journals(self, limit=50) -> List[JournalEntry]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, timestamp, content FROM journal ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        entries = []
        for row in rows:
            jid, ts, content = row
            cursor.execute("SELECT file_id FROM journal_links WHERE journal_id=?", (jid,))
            links = [r[0] for r in cursor.fetchall()]
            entries.append(JournalEntry(id=jid, timestamp=datetime.datetime.fromisoformat(ts), content=content, linked_file_ids=links))
        return entries

    def add_relation(self, from_id: int, to_id: int, relation_type: str, weight: float = 1.0):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO relations (from_id, to_id, relation_type, weight) VALUES (?,?,?,?)",
                       (from_id, to_id, relation_type, weight))
        self.conn.commit()

    def get_relations(self, file_id: int, direction='both') -> List[Relation]:
        cursor = self.conn.cursor()
        if direction == 'from':
            cursor.execute("SELECT id, from_id, to_id, relation_type, weight FROM relations WHERE from_id=?", (file_id,))
        elif direction == 'to':
            cursor.execute("SELECT id, from_id, to_id, relation_type, weight FROM relations WHERE to_id=?", (file_id,))
        else:
            cursor.execute("SELECT id, from_id, to_id, relation_type, weight FROM relations WHERE from_id=? OR to_id=?", (file_id, file_id))
        return [Relation(id=r[0], from_id=r[1], to_id=r[2], relation_type=r[3], weight=r[4]) for r in cursor.fetchall()]

    def search_lexical(self, query: str, catalog: str = None, limit: int = 30, source_quotas: Dict[str, int] = None) -> List[Tuple[FileItem, float]]:
        # Use FTS5 for full text search
        cursor = self.conn.cursor()
        # Build FTS query, escaping special chars
        safe_query = re.sub(r'[^\w\s]', '', query)
        if not safe_query.strip():
            return []
        fts_query = ' OR '.join(safe_query.split())
        rows = []
        try:
            cursor.execute(
                "SELECT f.id, f.path, f.name, f.is_dir, f.mime_type, f.size, f.modified, f.catalog, f.content_text, rank FROM files_fts JOIN files f ON f.id = files_fts.rowid WHERE files_fts MATCH ? ORDER BY rank LIMIT ?",
                (fts_query, limit * 2)  # fetch more, then filter
            )
            rows = cursor.fetchall()
        except sqlite3.OperationalError as e:
            logger.warning(f"FTS5 query failed: {e}")
        if not rows:
            return []
        items = []
        for row in rows:
            item = self._row_to_item(row[:-1])  # last column rank
            score = row[-1]
            # apply catalog filter
            if catalog and item.catalog != catalog:
                continue
            items.append((item, score))
        if source_quotas:
            filtered = []
            counts = {}
            for item, score in items:
                mime_base = item.mime_type.split('/')[0] if '/' in item.mime_type else item.mime_type
                current = counts.get(mime_base, 0)
                quota = source_quotas.get(mime_base, None) or source_quotas.get(item.mime_type, None)
                if quota is None or current < quota:
                    filtered.append((item, score))
                    counts[mime_base] = current + 1
                if len(filtered) >= limit:
                    break
            items = filtered[:limit]
        else:
            items = items[:limit]
        return items

    def add_investigation_note(self, question: str, answer: str, citations: str):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO investigation_notes (timestamp, question, answer, citations) VALUES (?,?,?,?)",
                       (datetime.datetime.now().isoformat(), question, answer, citations))
        self.conn.commit()

    def get_investigation_notes(self, limit=10) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, timestamp, question, citations FROM investigation_notes ORDER BY timestamp DESC LIMIT ?", (limit,))
        return cursor.fetchall()


# ------------------------------------------------------------------------------
# File Extractors
# ------------------------------------------------------------------------------
class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Return (text_content, metadata)"""
        pass

class TextExtractor(BaseExtractor):
    def extract(self, file_path: str) -> Tuple[Optional[str], Dict[str, Any]]:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
            return text, {}
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            return None, {}

class MarkdownExtractor(TextExtractor):
    pass

class LogExtractor(TextExtractor):
    pass

class PDFExtractor(BaseExtractor):
    def extract(self, file_path: str) -> Tuple[Optional[str], Dict[str, Any]]:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            logger.error("PyPDF2 not installed, cannot extract PDF")
            return None, {}
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            metadata = reader.metadata if reader.metadata else {}
            return text, metadata
        except Exception as e:
            logger.error(f"Failed to extract PDF {file_path}: {e}")
            return None, {}

class DOCXExtractor(BaseExtractor):
    def extract(self, file_path: str) -> Tuple[Optional[str], Dict[str, Any]]:
        try:
            from docx import Document
        except ImportError:
            logger.error("python-docx not installed, cannot extract DOCX")
            return None, {}
        try:
            doc = Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs])
            metadata = doc.core_properties.__dict__ if doc.core_properties else {}
            return text, metadata
        except Exception as e:
            logger.error(f"Failed to extract DOCX {file_path}: {e}")
            return None, {}

class ImageExtractor(BaseExtractor):
    def extract(self, file_path: str) -> Tuple[Optional[str], Dict[str, Any]]:
        # For now, no text extraction; could OCR with Tesseract later.
        metadata = {}
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            img = Image.open(file_path)
            info = img._getexif()
            if info:
                for tag, value in info.items():
                    decoded = TAGS.get(tag, tag)
                    metadata[decoded] = str(value)
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Failed to read image metadata {file_path}: {e}")
        return None, metadata

class SpreadsheetExtractor(BaseExtractor):
    def extract(self, file_path: str) -> Tuple[Optional[str], Dict[str, Any]]:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True)
            text = ""
            for sheet in wb.sheetnames:
                ws = wb[sheet]
                text += f"Sheet: {sheet}\n"
                for row in ws.iter_rows(values_only=True):
                    text += "\t".join([str(cell) if cell else "" for cell in row]) + "\n"
            return text, {"sheets": wb.sheetnames}
        except ImportError:
            logger.error("openpyxl not installed, cannot extract spreadsheet")
            return None, {}
        except Exception as e:
            logger.error(f"Failed to extract spreadsheet {file_path}: {e}")
            return None, {}

class ArchiveExtractor(BaseExtractor):
    def extract(self, file_path: str) -> Tuple[Optional[str], Dict[str, Any]]:
        # Extract text from archive members, maybe from readme, or list of files.
        import tarfile, zipfile
        members = []
        if file_path.endswith('.zip'):
            try:
                with zipfile.ZipFile(file_path, 'r') as zf:
                    members = zf.namelist()
            except:
                pass
        elif tarfile.is_tarfile(file_path):
            try:
                with tarfile.open(file_path, 'r') as tf:
                    members = tf.getnames()
            except:
                pass
        text = "Archive members:\n" + "\n".join(members)
        return text, {"members": members}


EXTRACTORS = {
    'text/plain': TextExtractor(),
    'text/markdown': MarkdownExtractor(),
    'text/x-markdown': MarkdownExtractor(),
    'text/x-log': LogExtractor(),
    'application/pdf': PDFExtractor(),
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': DOCXExtractor(),
    'application/msword': DOCXExtractor(),
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': SpreadsheetExtractor(),
    'application/vnd.ms-excel': SpreadsheetExtractor(),
    'image/jpeg': ImageExtractor(),
    'image/png': ImageExtractor(),
    'image/gif': ImageExtractor(),
    'image/webp': ImageExtractor(),
    'application/zip': ArchiveExtractor(),
    'application/x-tar': ArchiveExtractor(),
    'application/gzip': ArchiveExtractor(),
}


# ------------------------------------------------------------------------------
# Library Core
# ------------------------------------------------------------------------------
class Library:
    def __init__(self, library_path: str):
        self.root = Path(library_path)
        self.db_path = self.root / ".marginalia" / "library.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = LibraryDB(str(self.db_path))
        self.view_dir = self.root / ".marginalia" / "views"
        self.view_dir.mkdir(exist_ok=True)

    def scan_directory(self, directory: str = None, recursive: bool = True, catalog: str = None):
        if directory is None:
            directory = self.root
        dir_path = Path(directory).resolve()
        if not dir_path.is_dir():
            raise ValueError(f"Not a directory: {directory}")
        files = dir_path.iterdir() if not recursive else dir_path.rglob('*')
        for f in files:
            if f.is_symlink():
                continue
            if '.marginalia' in f.parts:
                continue
            if f.is_dir():
                # optionally process directory
                pass
            else:
                try:
                    self.ingest_file(str(f), catalog=catalog)
                except Exception as e:
                    logger.error(f"Could not ingest {f}: {e}")

    def ingest_file(self, file_path: str, catalog: str = None) -> Optional[FileItem]:
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"File not found: {file_path}")
            return None
        stat = path.stat()
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'
        extractor = EXTRACTORS.get(mime_type, TextExtractor())  # fallback to text
        text, meta = extractor.extract(file_path)
        item = FileItem(
            id=-1,  # placeholder
            path=str(path.absolute()),
            name=path.name,
            is_dir=False,
            mime_type=mime_type,
            size=stat.st_size,
            modified=datetime.datetime.fromtimestamp(stat.st_mtime),
            catalog=catalog if catalog else str(path.parent),
            tags=set(),
            metadata=meta,
            content_text=text
        )
        file_id = self.db.add_file(item)
        item.id = file_id
        return item

    def tag_file(self, file_id: int, tags: List[str]):
        item = self.db.get_file_by_id(file_id)
        if item:
            item.tags.update(tags)
            self.db.update_file(item)

    def add_metadata(self, file_id: int, key: str, value: Any):
        item = self.db.get_file_by_id(file_id)
        if item:
            item.metadata[key] = value
            self.db.update_file(item)

    def add_journal_entry(self, content: str, linked_file_ids: List[int] = None):
        entry = JournalEntry(
            id=-1,
            timestamp=datetime.datetime.now(),
            content=content,
            linked_file_ids=linked_file_ids or []
        )
        self.db.add_journal(entry)

    def mine_relations(self, threshold: float = 0.5):
        # simplistic relation mining based on common tags or keyword overlap
        # using text similarity via Jaccard on tokens
        files = self._get_all_file_ids()
        import itertools
        for f1, f2 in itertools.combinations(files, 2):
            item1 = self.db.get_file_by_id(f1)
            item2 = self.db.get_file_by_id(f2)
            if not item1 or not item2:
                continue
            if item1.mime_type.startswith('image') or item2.mime_type.startswith('image'):
                continue  # skip images for now
            # tokenize
            tokens1 = set(re.findall(r'\w+', item1.content_text.lower())) if item1.content_text else set()
            tokens2 = set(re.findall(r'\w+', item2.content_text.lower())) if item2.content_text else set()
            union = tokens1.union(tokens2)
            if not union:
                continue
            jaccard = len(tokens1.intersection(tokens2)) / len(union)
            if jaccard > threshold:
                self.db.add_relation(f1, f2, "similar", weight=jaccard)

    def _get_all_file_ids(self) -> List[int]:
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id FROM files WHERE is_dir=0")
        return [row[0] for row in cursor.fetchall()]

    def search(self, query: str, **kwargs) -> List[Tuple[FileItem, float]]:
        return self.db.search_lexical(query, **kwargs)

    def save_view(self, name: str, query_params: dict):
        view_file = self.view_dir / f"{name}.json"
        with open(view_file, 'w') as f:
            json.dump(query_params, f)

    def load_view(self, name: str) -> dict:
        view_file = self.view_dir / f"{name}.json"
        if view_file.exists():
            with open(view_file, 'r') as f:
                return json.load(f)
        return {}

    # File window reading
    def read_file_window(self, file_id: int, window_type: str, **kwargs) -> str:
        item = self.db.get_file_by_id(file_id)
        if not item:
            return ""
        path = item.path
        if window_type == 'lines':
            start = kwargs.get('start', 0)
            end = kwargs.get('end', None)
            return self._read_lines(path, start, end)
        elif window_type == 'page':
            page_num = kwargs.get('page_num', 0)
            return self._read_page(path, page_num)
        elif window_type == 'archive_member':
            member_name = kwargs.get('member', '')
            return self._read_archive_member(path, member_name)
        elif window_type == 'table_slice':
            sheet_name = kwargs.get('sheet_name', None)
            cell_range = kwargs.get('cell_range', None)  # e.g., "A1:D10"
            return self._read_table_slice(path, sheet_name, cell_range)
        return ""

    def _read_lines(self, path, start, end):
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            if end is None:
                end = len(lines)
            selected = lines[start:end]
            return ''.join(selected)
        except Exception:
            return ""

    def _read_page(self, path, page_num):
        mime_type, _ = mimetypes.guess_type(path)
        if 'pdf' in mime_type:
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(path)
                if 0 <= page_num < len(reader.pages):
                    return reader.pages[page_num].extract_text()
            except:
                pass
        return ""

    def _read_archive_member(self, path, member_name):
        import tarfile, zipfile
        if path.endswith('.zip'):
            import zipfile
            with zipfile.ZipFile(path, 'r') as zf:
                try:
                    with zf.open(member_name) as f:
                        return f.read().decode('utf-8', errors='replace')
                except:
                    return ""
        elif tarfile.is_tarfile(path):
            with tarfile.open(path, 'r') as tf:
                try:
                    f = tf.extractfile(member_name)
                    if f:
                        return f.read().decode('utf-8', errors='replace')
                except:
                    return ""
        return ""

    def _read_table_slice(self, path, sheet_name=None, cell_range=None):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, data_only=True)
            ws = wb[sheet_name] if sheet_name else wb.active
            if cell_range:
                # e.g., "A1:D5"
                rows = ws[cell_range]
            else:
                rows = ws.iter_rows(values_only=True)
            text = ""
            for row in rows:
                text += "\t".join([str(cell if cell is not None else "") for cell in row]) + "\n"
            return text
        except:
            return ""


# ------------------------------------------------------------------------------
# LLM Interface (simple abstraction)
# ------------------------------------------------------------------------------
class LLMInterface(ABC):
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        pass

class MockLLM(LLMInterface):
    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        # Simple mock that returns citations from context
        if "citations" in prompt.lower():
            return "Based on the provided sources, the answer is: [Sample answer with citation to file1]"
        return "Mock response"


# ------------------------------------------------------------------------------
# Agent
# ------------------------------------------------------------------------------
class ResearchAgent:
    def __init__(self, library: Library, llm: LLMInterface = None):
        self.library = library
        self.llm = llm or MockLLM()

    def ask(self, question: str, use_embeddings: bool = False, rerank: bool = False, source_quotas: Dict[str, int] = None) -> str:
        # 1. Search
        logger.info(f"Question: {question}")
        results = self.library.search(question, source_quotas=source_quotas)
        if not results:
            return "No relevant files found."

        # 2. For each result, read a window of text (default lines 0-50)
        contexts = []
        for item, score in results[:5]:  # top 5
            window_text = self.library.read_file_window(item.id, 'lines', start=0, end=50)
            if window_text:
                contexts.append(f"--- Source: {item.path} (score {score:.2f}) ---\n{window_text}")
        if not contexts:
            return "Could not extract readable windows."

        combined = "\n\n".join(contexts)
        prompt = (
            f"Question: {question}\n\n"
            f"Please answer using ONLY the following sources. If the answer cannot be found, say so. "
            f"Include citations to source paths.\n\n"
            f"{combined}"
        )
        response = self.llm.generate(prompt)
        self._save_investigation(question, response, [item.path for item, _ in results[:5]])
        return response

    def _save_investigation(self, question: str, answer: str, source_paths: List[str]):
        citations_str = json.dumps(source_paths)
        self.library.db.add_investigation_note(question, answer, citations_str)

    def recall_investigations(self, limit=5):
        return self.library.db.get_investigation_notes(limit)


# ------------------------------------------------------------------------------
# Example Usage
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import tempfile, shutil

    # Create a temporary library directory
    with tempfile.TemporaryDirectory() as tmpdir:
        lib = Library(tmpdir)
        # Create sample files
        sample_dir = Path(tmpdir) / "docs"
        sample_dir.mkdir()
        (sample_dir / "readme.txt").write_text("Marginalia is a personal knowledge management system.\nIt uses LLMs to answer questions.")
        (sample_dir / "notes.md").write_text("# Notes\n\nThis is a markdown note about machine learning.")
        (sample_dir / "data.csv").write_text("name,value\nAlice,10\nBob,20")
        
        lib.scan_directory(str(sample_dir), catalog="default")
        lib.tag_file(1, ["knowledge", "system"])
        lib.add_journal_entry("Started using Marginalia today", [1])

        agent = ResearchAgent(lib)
        answer = agent.ask("What is Marginalia?")
        print("Answer:", answer)

        # Recall past investigations
        print("Past investigations:", agent.recall_investigations())