import os
import re
import json
import logging
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Union, Callable, Iterator, Set
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from collections import defaultdict
from dataclasses import dataclass, field
import sqlite3

# Optional imports with fallback
try:
    import PyPDF2
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
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import yaml
except ImportError:
    yaml = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("marginalia")


# ----------------------------------------------------------------
# Exception classes
# ----------------------------------------------------------------
class MarginaliaError(Exception):
    pass

class IngestionError(MarginaliaError):
    pass

class SearchError(MarginaliaError):
    pass

class ReadError(MarginaliaError):
    pass


# ----------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------
@dataclass
class SystemConfig:
    """Global configuration for Marginalia system."""
    root_path: str = os.path.expanduser("~/marginalia_kb")
    enable_embeddings: bool = False
    vector_db_path: Optional[str] = None  # SQLite path for sqlite-vec
    enable_reranking: bool = False
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    source_quotas: Dict[str, int] = field(default_factory=lambda: {
        "pdf": 5,
        "md": 10,
        "txt": 10,
        "docx": 5,
        "xlsx": 5,
        "image": 3,
        "archive": 3,
    })
    default_max_results: int = 20
    lexical_search_field: str = "content"  # which field to search

    def __post_init__(self):
        os.makedirs(self.root_path, exist_ok=True)
        if self.vector_db_path is None:
            self.vector_db_path = os.path.join(self.root_path, "vectors.db")


# ----------------------------------------------------------------
# Document and Metadata
# ----------------------------------------------------------------
@dataclass
class DocumentMetadata:
    tags: Set[str] = field(default_factory=set)
    custom: Dict[str, Any] = field(default_factory=dict)
    created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    modified: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_type: str = "unknown"


@dataclass
class Relation:
    source_doc_id: str
    target_doc_id: str
    relation_type: str  # e.g., "references", "similar", "parent"
    weight: float = 1.0


@dataclass
class JournalEntry:
    doc_id: str
    note: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    citations: List[str] = field(default_factory=list)  # list of doc_ids


class Document:
    """
    Represents an ingested file with extracted text and metadata.
    """
    def __init__(self, doc_id: str, path: str, content: str = "", metadata: Optional[DocumentMetadata] = None):
        self.id = doc_id
        self.path = path  # relative path within root, or absolute
        self.content = content  # full extracted text
        self.metadata = metadata if metadata else DocumentMetadata()
        self.relations: List[Relation] = []
        self.journal: List[JournalEntry] = []

    def add_tag(self, tag: str):
        self.metadata.tags.add(tag)

    def remove_tag(self, tag: str):
        self.metadata.tags.discard(tag)

    def add_relation(self, target_id: str, rel_type: str, weight: float = 1.0):
        self.relations.append(Relation(self.id, target_id, rel_type, weight))

    def add_journal_entry(self, note: str, citations: List[str]):
        entry = JournalEntry(self.id, note, citations=citations)
        self.journal.append(entry)
        return entry

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "path": self.path,
            "content": self.content,
            "tags": list(self.metadata.tags),
            "custom": self.metadata.custom,
            "created": self.metadata.created.isoformat(),
            "modified": self.metadata.modified.isoformat(),
            "source_type": self.metadata.source_type,
        }


# ----------------------------------------------------------------
# Document Store (Catalog)
# ----------------------------------------------------------------
class DocumentStore:
    """In-memory store for documents, also backed by SQLite for persistence."""
    def __init__(self, db_path: str = ":memory:"):
        self.documents: Dict[str, Document] = {}
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                path TEXT UNIQUE,
                content TEXT,
                tags TEXT,
                custom TEXT,
                created TEXT,
                modified TEXT,
                source_type TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                source_id TEXT,
                target_id TEXT,
                rel_type TEXT,
                weight REAL,
                FOREIGN KEY(source_id) REFERENCES documents(id),
                FOREIGN KEY(target_id) REFERENCES documents(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                note TEXT,
                timestamp TEXT,
                citations TEXT,
                FOREIGN KEY(doc_id) REFERENCES documents(id)
            )
        """)
        self.conn.commit()

    def add_document(self, doc: Document):
        if doc.id in self.documents:
            raise MarginaliaError(f"Document {doc.id} already exists")
        self.documents[doc.id] = doc
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO documents (id, path, content, tags, custom, created, modified, source_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc.id,
                doc.path,
                doc.content,
                json.dumps(list(doc.metadata.tags)),
                json.dumps(doc.metadata.custom),
                doc.metadata.created.isoformat(),
                doc.metadata.modified.isoformat(),
                doc.metadata.source_type,
            ))
            # Insert relations
            for rel in doc.relations:
                self.conn.execute("""
                    INSERT INTO relations (source_id, target_id, rel_type, weight)
                    VALUES (?, ?, ?, ?)
                """, (rel.source_doc_id, rel.target_doc_id, rel.relation_type, rel.weight))
            self.conn.commit()
        except Exception as e:
            raise MarginaliaError(f"Database error: {e}")

    def get_document(self, doc_id: str) -> Optional[Document]:
        return self.documents.get(doc_id)

    def get_document_by_path(self, path: str) -> Optional[Document]:
        for doc in self.documents.values():
            if doc.path == path:
                return doc
        return None

    def remove_document(self, doc_id: str):
        if doc_id not in self.documents:
            return
        del self.documents[doc_id]
        self.conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self.conn.execute("DELETE FROM relations WHERE source_id = ? OR target_id = ?", (doc_id, doc_id))
        self.conn.execute("DELETE FROM journal WHERE doc_id = ?", (doc_id,))
        self.conn.commit()

    def all_documents(self) -> List[Document]:
        return list(self.documents.values())

    def get_relations(self, doc_id: str) -> List[Relation]:
        cur = self.conn.cursor()
        cur.execute("SELECT source_id, target_id, rel_type, weight FROM relations WHERE source_id = ? OR target_id = ?", (doc_id, doc_id))
        rows = cur.fetchall()
        return [Relation(s, t, r, w) for s, t, r, w in rows]

    def search_by_tags(self, tags: List[str]) -> List[Document]:
        result = []
        for doc in self.documents.values():
            if any(tag in doc.metadata.tags for tag in tags):
                result.append(doc)
        return result


# ----------------------------------------------------------------
# Ingestion: Parsers for various file types
# ----------------------------------------------------------------
class BaseParser(ABC):
    """Abstract parser for a file type."""
    @abstractmethod
    def parse(self, file_path: str) -> str:
        """Return extracted text content."""
        pass

    @property
    @abstractmethod
    def source_type(self) -> str:
        pass


class TextParser(BaseParser):
    source_type = "txt"
    def parse(self, file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()


class MarkdownParser(BaseParser):
    source_type = "md"
    def parse(self, file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()


class PDFParser(BaseParser):
    source_type = "pdf"
    def parse(self, file_path: str) -> str:
        if not HAS_PYPDF:
            raise ImportError("PyPDF2 required for PDF parsing")
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
        return text


class DocxParser(BaseParser):
    source_type = "docx"
    def parse(self, file_path: str) -> str:
        if not HAS_DOCX:
            raise ImportError("python-docx required for DOCX parsing")
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])


class SpreadsheetParser(BaseParser):
    source_type = "xlsx"
    def parse(self, file_path: str) -> str:
        if not HAS_OPENPYXL:
            raise ImportError("openpyxl required for XLSX parsing")
        wb = openpyxl.load_workbook(file_path, data_only=True)
        text = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for row in ws.iter_rows(values_only=True):
                text.append(" | ".join([str(cell) if cell is not None else "" for cell in row]))
        return "\n".join(text)


class ImageParser(BaseParser):
    source_type = "image"
    def parse(self, file_path: str) -> str:
        # For now, we return metadata only; full OCR would require tesseract etc.
        if not HAS_PIL:
            raise ImportError("PIL required for image metadata")
        img = Image.open(file_path)
        return f"[Image: {os.path.basename(file_path)}, size={img.size}, format={img.format}]"


class LogParser(BaseParser):
    source_type = "log"
    def parse(self, file_path: str) -> str:
        # Treat as text
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()


class ArchiveParser(BaseParser):
    source_type = "archive"
    def parse(self, file_path: str) -> str:
        import zipfile
        import tarfile
        text = []
        if zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path, 'r') as zf:
                for name in zf.namelist():
                    text.append(f"Member: {name}")
        elif tarfile.is_tarfile(file_path):
            with tarfile.open(file_path, 'r:*') as tar:
                for member in tar.getmembers():
                    text.append(f"Member: {member.name}")
        else:
            text.append("Unsupported archive format")
        return "\n".join(text)


class ParserFactory:
    """Determine parser based on file extension."""
    @staticmethod
    def get_parser(file_path: str) -> BaseParser:
        ext = os.path.splitext(file_path)[1].lower()
        mapping = {
            ".txt": TextParser,
            ".md": MarkdownParser,
            ".markdown": MarkdownParser,
            ".pdf": PDFParser,
            ".docx": DocxParser,
            ".xlsx": SpreadsheetParser,
            ".xls": SpreadsheetParser,
            ".png": ImageParser,
            ".jpg": ImageParser,
            ".jpeg": ImageParser,
            ".gif": ImageParser,
            ".bmp": ImageParser,
            ".log": LogParser,
            ".zip": ArchiveParser,
            ".tar": ArchiveParser,
            ".gz": ArchiveParser,
            ".bz2": ArchiveParser,
        }
        parser_class = mapping.get(ext)
        if parser_class is None:
            # fallback to text
            return TextParser()
        return parser_class()


class IngestionManager:
    """
    Handles ingestion of files into the document store.
    Walks the folder tree, parses files, creates Document objects, assigns metadata.
    """
    def __init__(self, store: DocumentStore, root_path: str):
        self.store = store
        self.root_path = root_path

    def ingest_file(self, file_path: str, add_tags: Optional[List[str]] = None,
                    custom_meta: Optional[Dict] = None) -> Document:
        abs_path = os.path.abspath(file_path)
        if not abs_path.startswith(self.root_path):
            raise IngestionError(f"File {file_path} is outside the root path")
        rel_path = os.path.relpath(abs_path, self.root_path)
        # Generate stable doc_id from relative path
        doc_id = hashlib.md5(rel_path.encode()).hexdigest()

        # Check if already exists
        existing = self.store.get_document(doc_id)
        if existing and existing.metadata.modified >= datetime.fromtimestamp(os.path.getmtime(abs_path), tz=timezone.utc):
            # already up to date
            logger.info(f"Document {rel_path} already up to date")
            return existing

        parser = ParserFactory.get_parser(abs_path)
        try:
            content = parser.parse(abs_path)
        except Exception as e:
            raise IngestionError(f"Parsing failed for {abs_path}: {e}")

        metadata = DocumentMetadata(source_type=parser.source_type)
        if add_tags:
            metadata.tags.update(add_tags)
        if custom_meta:
            metadata.custom.update(custom_meta)
        metadata.created = datetime.fromtimestamp(os.path.getctime(abs_path), tz=timezone.utc) if os.path.exists(abs_path) else datetime.now(timezone.utc)
        metadata.modified = datetime.fromtimestamp(os.path.getmtime(abs_path), tz=timezone.utc) if os.path.exists(abs_path) else datetime.now(timezone.utc)

        doc = Document(doc_id, rel_path, content, metadata)
        self.store.add_document(doc)
        logger.info(f"Ingested {rel_path} as {doc_id}")
        return doc

    def ingest_folder(self, folder_path: Optional[str] = None, recursive: bool = True, add_tags: Optional[List[str]] = None):
        if folder_path is None:
            folder_path = self.root_path
        abs_folder = os.path.abspath(folder_path)
        if not abs_folder.startswith(self.root_path):
            raise IngestionError(f"Folder {folder_path} outside root")
        for root, dirs, files in os.walk(abs_folder):
            for file in files:
                fpath = os.path.join(root, file)
                try:
                    self.ingest_file(fpath, add_tags=add_tags)
                except IngestionError as e:
                    logger.error(f"Skipping {fpath}: {e}")
            if not recursive:
                break


# ----------------------------------------------------------------
# Search (Recall) subsystem
# ----------------------------------------------------------------
class SearchResult:
    """Represents a search hit with score and document id."""
    def __init__(self, doc_id: str, score: float, snippet: str = ""):
        self.doc_id = doc_id
        self.score = score
        self.snippet = snippet


class BaseSearchEngine(ABC):
    """Abstract search engine."""
    def __init__(self, store: DocumentStore):
        self.store = store

    @abstractmethod
    def search(self, query: str, max_results: int = 20) -> List[SearchResult]:
        pass


class LexicalSearchEngine(BaseSearchEngine):
    """
    Lexical search using simple TF-IDF-like word matching over document content.
    (In practice, you'd integrate Whoosh or similar.)
    """
    def __init__(self, store: DocumentStore, field: str = "content"):
        super().__init__(store)
        self.field = field
        self._index = None

    def _build_index(self):
        # Simple in-memory index: word -> set of doc_ids
        self._word_index: Dict[str, Set[str]] = defaultdict(set)
        for doc in self.store.all_documents():
            text = doc.content if self.field == "content" else doc.metadata.custom.get(self.field, "")
            words = re.findall(r'\w+', text.lower())
            for w in words:
                self._word_index[w].add(doc.id)
        self._index = True

    def search(self, query: str, max_results: int = 20) -> List[SearchResult]:
        if not self._index:
            self._build_index()
        query_words = re.findall(r'\w+', query.lower())
        if not query_words:
            return []
        # Score by term frequency across all docs (simple)
        scores: Dict[str, float] = defaultdict(float)
        for word in query_words:
            docs = self._word_index.get(word, set())
            for doc_id in docs:
                # Count occurrences in that doc? We'll just give raw term count
                doc = self.store.get_document(doc_id)
                if doc:
                    text = doc.content if self.field == "content" else doc.metadata.custom.get(self.field, "")
                    count = text.lower().count(word)
                    scores[doc_id] += count
        # Sort by score descending
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for doc_id, score in sorted_docs[:max_results]:
            doc = self.store.get_document(doc_id)
            snippet = doc.content[:200] + "..." if doc else ""
            results.append(SearchResult(doc_id, score, snippet))
        return results


# Placeholder for vector/embedding search
class VectorSearchEngine(BaseSearchEngine):
    """
    Uses embeddings and sqlite-vec for similarity search.
    This implementation mocks the embedding process.
    """
    def __init__(self, store: DocumentStore, db_path: str, embedding_model_name: str = "all-MiniLM-L6-v2"):
        super().__init__(store)
        self.db_path = db_path
        self._setup_db()
        self.embedding_model = None  # Mock, would load sentence-transformers

    def _setup_db(self):
        # Initialize sqlite-vec (mock)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS vecs (doc_id TEXT PRIMARY KEY, vector BLOB)")
        self.conn.commit()

    def _embed(self, text: str) -> List[float]:
        # Mock: return zero vector of length 384
        return [0.0] * 384

    def index_documents(self, batch_size: int = 100):
        for doc in self.store.all_documents():
            vec = self._embed(doc.content)
            self.conn.execute("INSERT OR REPLACE INTO vecs (doc_id, vector) VALUES (?, ?)",
                              (doc.id, sqlite3.Binary(bytes(vec))))  # Not real, just placeholder
        self.conn.commit()

    def search(self, query: str, max_results: int = 20) -> List[SearchResult]:
        # Mock: return random
        return []


class Reranker(ABC):
    """Re-ranks search results."""
    @abstractmethod
    def rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        pass


class NoOpReranker(Reranker):
    def rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        return results


class CrossEncoderReranker(Reranker):
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        # Would load model
        self.model = None

    def rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        # Mock: just keep original order
        return results


class SourceQuota:
    """Applies per-source-type result limits."""
    def __init__(self, quotas: Dict[str, int]):
        self.quotas = quotas

    def apply(self, results: List[SearchResult], store: DocumentStore) -> List[SearchResult]:
        used: Dict[str, int] = defaultdict(int)
        filtered = []
        for res in results:
            doc = store.get_document(res.doc_id)
            if not doc:
                continue
            stype = doc.metadata.source_type
            if stype in self.quotas:
                if used[stype] >= self.quotas[stype]:
                    continue
                used[stype] += 1
            filtered.append(res)
        return filtered


class SearchOrchestrator:
    """
    Combines base search, optional reranking, and source quotas.
    """
    def __init__(self, store: DocumentStore, config: SystemConfig):
        self.store = store
        self.config = config
        self.lexical = LexicalSearchEngine(store, field=config.lexical_search_field)
        self.vector: Optional[VectorSearchEngine] = None
        if config.enable_embeddings:
            self.vector = VectorSearchEngine(store, db_path=config.vector_db_path)
            # Optionally index all documents
            self.vector.index_documents()
        self.reranker: Reranker = CrossEncoderReranker(config.reranker_model_name) if config.enable_reranking else NoOpReranker()
        self.quota = SourceQuota(config.source_quotas)

    def search(self, query: str, max_results: int = None) -> List[SearchResult]:
        if max_results is None:
            max_results = self.config.default_max_results
        # Lexical first (default)
        results = self.lexical.search(query, max_results)
        # If embeddings enabled, optionally merge
        if self.vector:
            vec_results = self.vector.search(query, max_results)
            # Simple merge by dedup and interleave
            lex_ids = {r.doc_id for r in results}
            for vr in vec_results:
                if vr.doc_id not in lex_ids:
                    results.append(vr)
        # Rerank
        results = self.reranker.rerank(query, results)
        # Apply quotas
        results = self.quota.apply(results, self.store)
        return results[:max_results]


# ----------------------------------------------------------------
# Reader: Extract windows from documents
# ----------------------------------------------------------------
class Reader:
    """
    Reads original sections, pages, lines, archive members, table slices based on document type.
    """
    def __init__(self, store: DocumentStore, root_path: str):
        self.store = store
        self.root_path = root_path

    def _resolve_abs_path(self, doc: Document) -> str:
        return os.path.join(self.root_path, doc.path)

    def read_section(self, doc: Document, section_id: str) -> str:
        """Read a named section (e.g., Markdown heading)."""
        if doc.metadata.source_type in ("md", "txt", "log"):
            # Simple section extraction via regex for markdown headings or by line range.
            # In a real implementation, parse AST for markdown.
            lines = doc.content.splitlines()
            heading_pattern = re.compile(r'^#+\s*' + re.escape(section_id) + r'\s*$', re.IGNORECASE)
            in_section = False
            collected = []
            next_heading = re.compile(r'^#+\s')
            for line in lines:
                if heading_pattern.match(line):
                    in_section = True
                    continue
                if in_section:
                    if next_heading.match(line):
                        break
                    collected.append(line)
            if collected:
                return "\n".join(collected)
            return ""
        else:
            raise ReadError(f"Section reading not supported for {doc.metadata.source_type}")

    def read_page(self, doc: Document, page_num: int) -> str:
        """Extract page content from a PDF."""
        if doc.metadata.source_type == "pdf":
            if not HAS_PYPDF:
                raise ImportError("PyPDF2 required")
            abs_path = self._resolve_abs_path(doc)
            with open(abs_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                if 0 <= page_num < len(reader.pages):
                    return reader.pages[page_num].extract_text() or ""
                else:
                    raise ReadError(f"Page {page_num} out of range")
        else:
            raise ReadError("Page reading only for PDFs")

    def read_lines(self, doc: Document, start: int, end: int) -> str:
        """Read lines numbers inclusive (1-indexed)."""
        lines = doc.content.splitlines()
        if start < 1 or end > len(lines):
            raise ReadError(f"Line range {start}-{end} out of bounds (1-{len(lines)})")
        return "\n".join(lines[start-1:end])

    def read_archive_member(self, doc: Document, member_name: str) -> str:
        """Extract content of a single archive member."""
        if doc.metadata.source_type != "archive":
            raise ReadError("Not an archive")
        abs_path = self._resolve_abs_path(doc)
        import zipfile, tarfile
        if zipfile.is_zipfile(abs_path):
            with zipfile.ZipFile(abs_path, 'r') as zf:
                try:
                    with zf.open(member_name) as mf:
                        return mf.read().decode('utf-8', errors='replace')
                except KeyError:
                    raise ReadError(f"Member {member_name} not found")
        elif tarfile.is_tarfile(abs_path):
            with tarfile.open(abs_path, 'r:*') as tar:
                try:
                    f = tar.extractfile(member_name)
                    if f:
                        return f.read().decode('utf-8', errors='replace')
                    raise ReadError(f"Member {member_name} not found")
                except KeyError:
                    raise ReadError(f"Member {member_name} not found")
        return ""

    def read_table_slice(self, doc: Document, sheet: str, start_row: int, end_row: int, columns: Optional[List[str]] = None) -> str:
        """Read slice of a spreadsheet."""
        if doc.metadata.source_type not in ("xlsx", "csv"):
            raise ReadError("Not a spreadsheet")
        if not HAS_OPENPYXL:
            raise ImportError("openpyxl required")
        abs_path = self._resolve_abs_path(doc)
        wb = openpyxl.load_workbook(abs_path, data_only=True)
        if sheet not in wb.sheetnames:
            raise ReadError(f"Sheet {sheet} not found")
        ws = wb[sheet]
        rows = []
        for row in ws.iter_rows(min_row=start_row, max_row=end_row, values_only=True):
            if columns:
                # columns are column letters like A,B
                col_indices = [openpyxl.utils.column_index_from_string(c) - 1 for c in columns]
                rows.append(" | ".join([str(row[i]) if i < len(row) and row[i] is not None else "" for i in col_indices]))
            else:
                rows.append(" | ".join([str(cell) if cell is not None else "" for cell in row]))
        return "\n".join(rows)

    def read_window(self, doc: Document, spec: Dict) -> str:
        """
        Dispatcher based on spec keys.
        Spec may contain: "type": "section"|"page"|"lines"|"archive_member"|"table_slice"
        and appropriate parameters.
        """
        stype = spec.get("type")
        if stype == "section":
            return self.read_section(doc, spec.get("name", ""))
        elif stype == "page":
            return self.read_page(doc, int(spec.get("number", 0)))
        elif stype == "lines":
            return self.read_lines(doc, int(spec.get("start", 1)), int(spec.get("end", 1)))
        elif stype == "archive_member":
            return self.read_archive_member(doc, spec.get("member", ""))
        elif stype == "table_slice":
            return self.read_table_slice(
                doc,
                spec.get("sheet", ""),
                int(spec.get("start_row", 1)),
                int(spec.get("end_row", 1)),
                spec.get("columns")
            )
        else:
            # default: return full content
            return doc.content


# ----------------------------------------------------------------
# Agent: LLM interface (mocked)
# ----------------------------------------------------------------
class LLMInterface(ABC):
    """Abstract LLM call."""
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass


class MockLLM(LLMInterface):
    def generate(self, prompt: str) -> str:
        return f"Mock answer based on query. Citations: [doc1], [doc2]."


# ----------------------------------------------------------------
# Marginalia Agent
# ----------------------------------------------------------------
class InvestigationNote:
    """Durable note from a research session."""
    def __init__(self, question: str, answer: str, sources: List[str], timestamp: Optional[datetime] = None):
        self.question = question
        self.answer = answer
        self.sources = sources
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_markdown(self) -> str:
        lines = [
            f"# Investigation: {self.question}",
            f"*{self.timestamp.isoformat()}*",
            "",
            "## Answer",
            self.answer,
            "",
            "## Sources",
        ]
        for s in self.sources:
            lines.append(f"- [{s}]")
        return "\n".join(lines)


class MarginaliaAgent:
    """
    Core agent that handles query → recall → read → answer → note.
    """
    def __init__(self, store: DocumentStore, search: SearchOrchestrator, reader: Reader,
                 llm: Optional[LLMInterface] = None, journal_dir: str = "journal"):
        self.store = store
        self.search = search
        self.reader = reader
        self.llm = llm or MockLLM()
        self.journal_dir = os.path.join(search.config.root_path, journal_dir)
        os.makedirs(self.journal_dir, exist_ok=True)

    def _generate_cited_answer(self, question: str, sources: List[SearchResult], windows: List[str]) -> Tuple[str, List[str]]:
        # In real system, build prompt with windows and question, call LLM.
        # For mock, we'll produce a simple answer.
        answer = f"Answer to '{question}' using {len(sources)} sources."
        # Source documents ids
        source_ids = [s.doc_id for s in sources]
        return answer, source_ids

    def _write_investigation_note(self, note: InvestigationNote):
        # Save as markdown in journal directory
        safe_question = re.sub(r'[^\w\s-]', '', note.question)[:50].strip().replace(' ', '_')
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_question}.md"
        filepath = os.path.join(self.journal_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(note.to_markdown())
        logger.info(f"Investigation note saved to {filepath}")

    def ask(self, question: str, read_specs: Optional[Dict[str, Dict]] = None) -> InvestigationNote:
        """
        Main method: given a question, search, optionally read windows, produce answer, save note.
        read_specs: dict mapping doc_id to window spec dict (e.g., {"type": "section", "name": "Introduction"}).
        If None, we read first 500 chars of each retrieved document as fallback.
        """
        # 1. Recall
        results = self.search.search(question)
        if not results:
            # Return note with no sources
            return InvestigationNote(question, "No sources found.", [], datetime.now(timezone.utc))

        # 2. Read windows from source documents
        windows = []
        source_docs: List[Document] = []
        for res in results:
            doc = self.store.get_document(res.doc_id)
            if not doc:
                continue
            source_docs.append(doc)
            if read_specs and res.doc_id in read_specs:
                window_content = self.reader.read_window(doc, read_specs[res.doc_id])
            else:
                # Default: first 500 characters
                window_content = doc.content[:500]
            windows.append(window_content)

        # 3. Generate answer with citations (mock)
        answer, source_ids = self._generate_cited_answer(question, results, windows)

        # 4. Create investigation note
        note = InvestigationNote(question, answer, source_ids, datetime.now(timezone.utc))

        # 5. Save durable note
        self._write_investigation_note(note)

        # 6. Also optionally attach note to source documents' journal
        for doc in source_docs:
            doc.add_journal_entry(f"Used for question: {question}", citations=[d.id for d in source_docs if d.id != doc.id])

        return note


# ----------------------------------------------------------------
# Views and Catalogs (Organization)
# ----------------------------------------------------------------
class View:
    """A saved search/filter criteria."""
    def __init__(self, name: str, query: str, tags: Optional[List[str]] = None, source_types: Optional[List[str]] = None):
        self.name = name
        self.query = query
        self.tags = tags or []
        self.source_types = source_types or []

    def matches(self, doc: Document) -> bool:
        # Simple match: text query in content or tags
        if self.query.lower() not in doc.content.lower():
            return False
        if self.tags and not any(t in doc.metadata.tags for t in self.tags):
            return False
        if self.source_types and doc.metadata.source_type not in self.source_types:
            return False
        return True


class Catalog:
    """A named collection of documents."""
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.doc_ids: Set[str] = set()

    def add(self, doc_id: str):
        self.doc_ids.add(doc_id)

    def remove(self, doc_id: str):
        self.doc_ids.discard(doc_id)

    def list_documents(self, store: DocumentStore) -> List[Document]:
        return [store.get_document(did) for did in self.doc_ids if store.get_document(did)]


# ----------------------------------------------------------------
# Marginalia System: top-level orchestrator
# ----------------------------------------------------------------
class MarginaliaSystem:
    """
    The main entry point for the personal knowledge management system.
    """
    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config or SystemConfig()
        self.store = DocumentStore(db_path=os.path.join(self.config.root_path, "marginalia.db"))
        self.ingestion = IngestionManager(self.store, self.config.root_path)
        self.search_orchestrator = SearchOrchestrator(self.store, self.config)
        self.reader = Reader(self.store, self.config.root_path)
        self.agent = MarginaliaAgent(self.store, self.search_orchestrator, self.reader,
                                     journal_dir=os.path.join(self.config.root_path, "journal"))
        self.catalogs: Dict[str, Catalog] = {}
        self.views: Dict[str, View] = {}
        self._loaded = False

    def load_or_ingest(self):
        """Initial ingestion of the folder tree if not already done."""
        # Simple: check if store has documents
        if len(self.store.all_documents()) == 0:
            logger.info("No documents found. Performing initial ingestion...")
            self.ingestion.ingest_folder()
        else:
            logger.info(f"Loaded {len(self.store.all_documents())} existing documents")
        self._loaded = True

    def refresh(self):
        """Re-ingest for changes."""
        self.ingestion.ingest_folder()

    def search(self, query: str, max_results: int = None) -> List[SearchResult]:
        return self.search_orchestrator.search(query, max_results)

    def ask(self, question: str, read_specs: Optional[Dict[str, Dict]] = None) -> InvestigationNote:
        return self.agent.ask(question, read_specs)

    def add_catalog(self, name: str, description: str = "") -> Catalog:
        catalog = Catalog(name, description)
        self.catalogs[name] = catalog
        return catalog

    def add_view(self, name: str, query: str, tags: Optional[List[str]] = None,
                 source_types: Optional[List[str]] = None) -> View:
        view = View(name, query, tags, source_types)
        self.views[name] = view
        return view

    def get_documents_by_view(self, view_name: str) -> List[Document]:
        view = self.views.get(view_name)
        if not view:
            return []
        return [doc for doc in self.store.all_documents() if view.matches(doc)]

    def relation_mining(self, doc_id: str, threshold: float = 0.5):
        """
        Simple relation mining: find docs with similar content based on word overlap.
        Adds relations.
        """
        source = self.store.get_document(doc_id)
        if not source:
            return
        source_words = set(re.findall(r'\w+', source.content.lower()))
        for candidate in self.store.all_documents():
            if candidate.id == doc_id:
                continue
            cand_words = set(re.findall(r'\w+', candidate.content.lower()))
            if not source_words or not cand_words:
                continue
            jaccard = len(source_words & cand_words) / len(source_words | cand_words)
            if jaccard >= threshold:
                source.add_relation(candidate.id, "similar", jaccard)
        logger.info(f"Relation mining completed for {doc_id}")

    def export_journal(self) -> List[InvestigationNote]:
        """Collect all saved investigation notes from disk."""
        journal_dir = self.agent.journal_dir
        notes = []
        for fname in os.listdir(journal_dir):
            if fname.endswith('.md'):
                with open(os.path.join(journal_dir, fname), 'r') as f:
                    content = f.read()
                    # Simple parse
                    question = ""
                    answer = ""
                    sources = []
                    # Extract using simple heuristics
                    for line in content.splitlines():
                        if line.startswith("# Investigation:"):
                            question = line.replace("# Investigation:", "").strip()
                        elif line.startswith("## Answer"):
                            answer = ""
                        elif line.startswith("## Sources"):
                            break
                        elif line.startswith("- ["):
                            sources.append(line.strip("- []"))
                    notes.append(InvestigationNote(question, answer, sources))
        return notes


# ----------------------------------------------------------------
# Utility: Journal recall
# ----------------------------------------------------------------
class JournalSearch:
    """Search past investigation notes."""
    def __init__(self, journal_dir: str):
        self.journal_dir = journal_dir

    def search(self, query: str, max_results: int = 10) -> List[InvestigationNote]:
        # Lexical search over markdown files
        notes = []
        for fname in os.listdir(self.journal_dir):
            fpath = os.path.join(self.journal_dir, fname)
            if not fname.endswith('.md'):
                continue
            with open(fpath, 'r') as f:
                content = f.read()
                if query.lower() in content.lower():
                    # Parse note (simplified)
                    question = ""
                    answer = ""
                    sources = []
                    lines = content.splitlines()
                    i = 0
                    while i < len(lines):
                        line = lines[i]
                        if line.startswith("# Investigation:"):
                            question = line.replace("# Investigation:", "").strip()
                        elif line.startswith("## Answer"):
                            answer_start = i+1
                            # Find next ## heading
                            j = answer_start
                            while j < len(lines) and not lines[j].startswith("## "):
                                j += 1
                            answer = "\n".join(lines[answer_start:j])
                            i = j
                            continue
                        elif line.startswith("- ["):
                            sources.append(line.replace("- [", "").replace("]", "").strip())
                        i += 1
                    notes.append(InvestigationNote(question, answer, sources, datetime.fromtimestamp(os.path.getmtime(fpath), tz=timezone.utc)))
        # Sort by recency
        notes.sort(key=lambda n: n.timestamp, reverse=True)
        return notes[:max_results]


# ----------------------------------------------------------------
# Example usage
# ----------------------------------------------------------------
if __name__ == "__main__":
    # Sample usage
    sys_config = SystemConfig(root_path=os.path.join(os.path.expanduser("~"), "marginalia_demo"),
                              enable_embeddings=False,
                              enable_reranking=False)
    # Create system
    ms = MarginaliaSystem(sys_config)
    ms.load_or_ingest()
    # Ingest a test markdown file
    test_dir = os.path.join(ms.config.root_path, "test")
    os.makedirs(test_dir, exist_ok=True)
    md_file = os.path.join(test_dir, "note.md")
    with open(md_file, 'w') as f:
        f.write("# My Note\n\nContent of my note.\n\n## Section 1\n\nSome information.\n")
    ms.ingestion.ingest_file(md_file, add_tags=["test", "note"])
    # Search
    results = ms.search("information")
    print("Search results:")
    for r in results:
        print(r.doc_id, r.score)
    # Ask a question
    note = ms.ask("What is in the note?", read_specs=None)
    print("\nInvestigation note:")
    print(note.to_markdown())
    # Relation mining
    ms.relation_mining(results[0].doc_id)
    # View creation
    ms.add_view("my_notes", "note", tags=["note"])
    view_docs = ms.get_documents_by_view("my_notes")
    print("\nView 'my_notes' documents:", [d.path for d in view_docs])
    # Journal search
    js = JournalSearch(ms.agent.journal_dir)
    past_notes = js.search("note")
    print("\nPast notes found:", len(past_notes))