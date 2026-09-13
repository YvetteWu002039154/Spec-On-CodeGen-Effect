from __future__ import annotations
import os
import re
import json
import sqlite3
import datetime
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    Iterator,
    Callable,
    TypeVar,
)
from abc import ABC, abstractmethod
from collections import defaultdict

# ---------------------------------------------------------------------------
# Attempt imports for document parsers. If missing, the stubs will be used
# and a warning is issued.
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import docx
except ImportError:
    docx = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import PIL.Image
except ImportError:
    PIL = None

T = TypeVar("T")
DocumentID = int

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("marginalia")

# ---------------------------------------------------------------------------
# Parser framework
class Parser(ABC):
    """Abstract parser for a file type."""

    @abstractmethod
    def can_parse(self, filepath: Path) -> bool:
        """Return True if this parser can handle the file."""

    @abstractmethod
    def parse(self, filepath: Path) -> Dict[str, Any]:
        """
        Extract text and metadata.
        Returns dict with at least:
            - 'text': str
            - 'metadata': dict (original source, title, author, etc.)
        """


class TextParser(Parser):
    """Plain text and Markdown."""

    def can_parse(self, filepath: Path) -> bool:
        return filepath.suffix.lower() in (".txt", ".md", ".markdown", ".rst", ".log")

    def parse(self, filepath: Path) -> Dict[str, Any]:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        return {"text": text, "metadata": {"type": "text", "encoding": "utf-8"}}


class PdfParser(Parser):
    def can_parse(self, filepath: Path) -> bool:
        return filepath.suffix.lower() == ".pdf"

    def parse(self, filepath: Path) -> Dict[str, Any]:
        if PyPDF2 is None:
            raise ImportError("PyPDF2 is required to parse PDF files.")
        text = ""
        pages: List[str] = []
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                    pages.append(page_text)
        metadata = {
            "type": "pdf",
            "num_pages": len(reader.pages),
        }
        return {"text": text, "metadata": metadata, "pages": pages}


class DocxParser(Parser):
    def can_parse(self, filepath: Path) -> bool:
        return filepath.suffix.lower() == ".docx"

    def parse(self, filepath: Path) -> Dict[str, Any]:
        if docx is None:
            raise ImportError("python-docx is required to parse DOCX files.")
        doc = docx.Document(filepath)
        text = "\n".join(p.text for p in doc.paragraphs)
        metadata = {"type": "docx", "paragraph_count": len(doc.paragraphs)}
        return {"text": text, "metadata": metadata}


class ImageParser(Parser):
    def can_parse(self, filepath: Path) -> bool:
        return filepath.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff")

    def parse(self, filepath: Path) -> Dict[str, Any]:
        if PIL is None:
            raise ImportError("Pillow is required to handle image files.")
        # Without OCR, we can only read basic metadata.
        img = PIL.Image.open(filepath)
        metadata = {"type": "image", "size": img.size, "mode": img.mode}
        # Optionally, we could use pytesseract for OCR, but for now text is empty.
        return {"text": "", "metadata": metadata}


class SpreadsheetParser(Parser):
    def can_parse(self, filepath: Path) -> bool:
        return filepath.suffix.lower() in (".xlsx", ".xls", ".csv", ".ods")

    def parse(self, filepath: Path) -> Dict[str, Any]:
        # CSV handled by simple reading; others via openpyxl.
        suffix = filepath.suffix.lower()
        if suffix == ".csv":
            text_lines = []
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    text_lines.append(line.strip())
            return {"text": "\n".join(text_lines), "metadata": {"type": "csv"}}
        if openpyxl is None:
            raise ImportError("openpyxl is required to parse Excel files.")
        wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
        all_text = []
        for sheet in wb.sheetnames:
            ws = wb[sheet]
            for row in ws.iter_rows(values_only=True):
                row_text = "\t".join(str(cell) if cell is not None else "" for cell in row)
                all_text.append(row_text)
        wb.close()
        return {"text": "\n".join(all_text), "metadata": {"type": "spreadsheet", "sheets": wb.sheetnames}}


class ArchiveParser(Parser):
    """Zip and tar archives. Extract member list and optionally text from files inside."""

    def can_parse(self, filepath: Path) -> bool:
        return filepath.suffix.lower() in (".zip", ".tar", ".gz", ".bz2", ".7z")

    def parse(self, filepath: Path) -> Dict[str, Any]:
        import zipfile

        members: List[Dict[str, Any]] = []
        # We try zip first, then fallback to tar if applicable.
        if filepath.suffix.lower() == ".zip":
            with zipfile.ZipFile(filepath, "r") as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    member = {
                        "name": info.filename,
                        "size": info.file_size,
                        "date": datetime.datetime(*info.date_time),
                    }
                    # Optionally read text from text-like files
                    try:
                        with zf.open(info) as member_file:
                            raw = member_file.read()
                            try:
                                member["text"] = raw.decode("utf-8")
                            except UnicodeDecodeError:
                                member["text"] = ""  # binary file
                    except Exception:
                        member["text"] = ""
                    members.append(member)
            return {"text": "", "members": members, "metadata": {"type": "archive"}}
        else:
            # For tar, we would need tarfile module; simplified here.
            return {"text": "", "members": [], "metadata": {"type": "archive"}}


ALL_PARSERS: List[Parser] = [
    TextParser(),
    PdfParser(),
    DocxParser(),
    ImageParser(),
    SpreadsheetParser(),
    ArchiveParser(),
]


def find_parser(filepath: Path) -> Parser:
    for parser in ALL_PARSERS:
        if parser.can_parse(filepath):
            return parser
    raise ValueError(f"No parser found for {filepath}")


# ---------------------------------------------------------------------------
# Core data model
class Document:
    """Represents an ingested file with metadata, cached content, and views."""

    def __init__(
        self,
        doc_id: DocumentID,
        filepath: Path,
        metadata: Dict[str, Any],
        content: Optional[str] = None,
        pages: Optional[List[str]] = None,
        members: Optional[List[Dict[str, Any]]] = None,
    ):
        self.id = doc_id
        self.filepath = filepath  # relative to KB root or absolute
        self.title = filepath.stem
        self.metadata = metadata
        self.content = content or ""  # full plain text
        self.pages = pages or []  # for paged documents
        self.members = members or []  # for archives
        self.tags: Set[str] = set()
        self.added_date = datetime.datetime.now()
        self.modified_date = datetime.datetime.now()

    def read_lines(self, start: int, end: Optional[int] = None) -> str:
        """Return lines of the content (0-based)."""
        lines = self.content.splitlines()
        if end is None:
            end = len(lines)
        return "\n".join(lines[start:end])

    def read_pages(self, page_range: Union[int, Tuple[int, int]]) -> str:
        """Return text from pages (1-indexed)."""
        if not self.pages:
            raise ValueError("Document has no page data.")
        if isinstance(page_range, int):
            page = page_range - 1
            if 0 <= page < len(self.pages):
                return self.pages[page]
            raise IndexError("Page out of range")
        start, end = page_range
        start -= 1  # convert to 0-index
        if start < 0 or end > len(self.pages) or start >= end:
            raise ValueError("Invalid page range")
        return "\n".join(self.pages[start:end])

    def read_member(self, name: str) -> str:
        """Return text content of an archive member."""
        for m in self.members:
            if m["name"] == name:
                return m.get("text", "")
        raise ValueError(f"Member '{name}' not found in {self.filepath}")

    def read_table_slice(
        self, sheet_name: Optional[str] = None, cell_range: Optional[str] = None
    ) -> str:
        """Return textual representation of a spreadsheet slice. Simplified."""
        # This would require keeping structured spreadsheet data. For now,
        # we fall back to full text search. In a real implementation, we store sheets.
        return self.content

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "filepath": str(self.filepath),
            "metadata": self.metadata,
            "tags": list(self.tags),
            "added_date": self.added_date.isoformat(),
            "modified_date": self.modified_date.isoformat(),
        }


# ---------------------------------------------------------------------------
# Catalog, Tags, Views, Journals
class Catalog:
    """A named, persistent collection of documents (a view)."""

    def __init__(self, name: str, query: Optional[str] = None):
        self.name = name
        self.query = query  # saved search string, if any
        self.doc_ids: Set[DocumentID] = set()

    def add(self, doc: Document):
        self.doc_ids.add(doc.id)

    def remove(self, doc: Document):
        self.doc_ids.discard(doc.id)

    def contains(self, doc_id: DocumentID) -> bool:
        return doc_id in self.doc_ids


class Journal:
    """A chronological log of investigation notes or observations."""

    def __init__(self):
        self.entries: List[Dict[str, Any]] = []

    def add_entry(self, note: str, related_docs: List[DocumentID] = None):
        self.entries.append(
            {
                "timestamp": datetime.datetime.now().isoformat(),
                "note": note,
                "related_docs": related_docs or [],
            }
        )


# ---------------------------------------------------------------------------
# Indexing and Search
class Indexer:
    """Manages lexical and optional embedding indexes using SQLite."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                filepath TEXT UNIQUE,
                title TEXT,
                content TEXT,
                metadata TEXT,
                tags TEXT,
                added_date TEXT,
                modified_date TEXT
            )"""
        )
        cursor.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS doc_fts USING fts5(title, content, content='documents')"
        )
        # Additional tables for embeddings and relation mining can be added here.
        self.conn.commit()

    def add_document(self, doc: Document):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO documents (id, filepath, title, content, metadata, tags, added_date, modified_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                doc.id,
                str(doc.filepath),
                doc.title,
                doc.content,
                json.dumps(doc.metadata),
                json.dumps(list(doc.tags)),
                doc.added_date.isoformat(),
                doc.modified_date.isoformat(),
            ),
        )
        self.conn.commit()
        # Update FTS; it's auto from content sync if configured, but for safety:
        self.rebuild_fts()

    def rebuild_fts(self):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO doc_fts(doc_fts) VALUES('rebuild')")
        self.conn.commit()

    def search_lexical(self, query: str, limit: int = 10) -> List[Tuple[DocumentID, float]]:
        """FTS5 lexical search returning (doc_id, rank)."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "SELECT id, rank FROM doc_fts, documents WHERE doc_fts MATCH ? AND documents.id = doc_fts.rowid ORDER BY rank LIMIT ?",
                (query, limit),
            )
            results = [(row[0], row[1]) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            # If no matches, FTS may raise error; fallback to LIKE search.
            results = self._fallback_search(query, limit)
        return results

    def _fallback_search(self, query: str, limit: int) -> List[Tuple[DocumentID, float]]:
        cursor = self.conn.cursor()
        pattern = f"%{query}%"
        cursor.execute(
            "SELECT id FROM documents WHERE content LIKE ? OR title LIKE ? LIMIT ?",
            (pattern, pattern, limit),
        )
        return [(row[0], 1.0) for row in cursor.fetchall()]

    def search_embeddings(self, query_embedding: List[float], limit: int = 10) -> List[Tuple[DocumentID, float]]:
        """Stub: would use sqlite-vec or other vector store."""
        logger.warning("Embedding search is not implemented; falling back to lexical.")
        return []

    def load_document(self, doc_id: DocumentID) -> Optional[Document]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT filepath, title, content, metadata, tags, added_date, modified_date FROM documents WHERE id=?",
            (doc_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        filepath = Path(row[0])
        metadata = json.loads(row[3])
        tags = set(json.loads(row[4]))
        doc = Document(
            doc_id=doc_id,
            filepath=filepath,
            metadata=metadata,
            content=row[2],
        )
        doc.title = row[1]
        doc.tags = tags
        doc.added_date = datetime.datetime.fromisoformat(row[5])
        doc.modified_date = datetime.datetime.fromisoformat(row[6])
        return doc

    def close(self):
        self.conn.close()


# ---------------------------------------------------------------------------
# Relation Mining
class RelationMiner:
    """Mines relations between documents based on shared tags or content similarity."""

    def __init__(self, indexer: Indexer):
        self.indexer = indexer

    def find_related(self, doc: Document, top_k: int = 5) -> List[DocumentID]:
        """Return IDs of documents related by tags or content overlap."""
        cursor = self.indexer.conn.cursor()
        # Tags
        tag_condition = " OR ".join(
            f"tags LIKE '%\"{tag}\"%'" for tag in doc.tags
        )
        if tag_condition:
            cursor.execute(
                f"SELECT id FROM documents WHERE ({tag_condition}) AND id != ? LIMIT ?",
                (doc.id, top_k),
            )
            results = [row[0] for row in cursor.fetchall()]
            if results:
                return results[:top_k]
        # Fallback: content overlap via quick FTS (use first 50 chars)
        snippet = doc.content[:200] if doc.content else ""
        if snippet:
            # Use a simple query: first 20 words
            words = snippet.split()[:20]
            if words:
                query = " ".join(words)
                try:
                    cursor.execute(
                        "SELECT id, rank FROM doc_fts WHERE doc_fts MATCH ? AND id != ? ORDER BY rank LIMIT ?",
                        (query, doc.id, top_k),
                    )
                    return [row[0] for row in cursor.fetchall()]
                except Exception:
                    pass
        return []


# ---------------------------------------------------------------------------
# LLM Agent Abstraction
class LLMProvider(ABC):
    """Abstract for accessing an LLM (local or remote)."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return completion text."""


class DummyLLM(LLMProvider):
    """A placeholder that echoes the prompt for testing."""

    def generate(self, prompt: str) -> str:
        return f"[LLM reply to: {prompt[:100]}...]"


# ---------------------------------------------------------------------------
# Investigation Note
class InvestigationNote:
    """Record of a research turn, storable and searchable."""

    def __init__(
        self,
        query: str,
        answer: str,
        sources: List[Tuple[DocumentID, str]],  # (doc_id, cited_snippet)
        timestamp: Optional[datetime.datetime] = None,
    ):
        self.query = query
        self.answer = answer
        self.sources = sources
        self.timestamp = timestamp or datetime.datetime.now()

    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "answer": self.answer,
            "sources": [(doc_id, snippet) for doc_id, snippet in self.sources],
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Main Marginalia System
class Marginalia:
    """
    The knowledge management system.
    - Manages a folder tree for original files.
    - Builds library metadata.
    - Provides ingestion, organization, recall, reading, and agent capabilities.
    """

    def __init__(
        self,
        root_folder: Union[str, Path],
        db_path: Optional[Union[str, Path]] = None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        self.root = Path(root_folder).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        if db_path is None:
            db_path = self.root / ".marginalia.db"
        else:
            db_path = Path(db_path)
        self.db_path = Path(db_path)
        self.indexer = Indexer(self.db_path)
        self.relation_miner = RelationMiner(self.indexer)
        self.catalogs: Dict[str, Catalog] = {}
        self.journal = Journal()
        self.llm = llm_provider or DummyLLM()
        self._doc_counter = 0  # simple ID generator; in production use DB sequence
        self._init_counters()

    def _init_counters(self):
        cursor = self.indexer.conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM documents")
        self._doc_counter = cursor.fetchone()[0]

    def _next_doc_id(self) -> int:
        self._doc_counter += 1
        return self._doc_counter

    def ingest(self, filepath: Union[str, Path]) -> Document:
        """Ingest a single file: parse, store, index, and return Document."""
        filepath = Path(filepath)
        if not filepath.is_absolute():
            raise ValueError("Provide absolute path or relative to root; use ingest_file_for_kb.")
        # Actually, we can automatically store a copy inside KB? The spec says "keeps your files in a normal folder tree".
        # We'll assume the file is already inside root or we move it. For simplicity, we accept any absolute path and store
        # its location. We should ensure it's within root or copy. For now, we just link.
        # Here we copy file into KB root preserving relative structure? The user wants "normal folder tree". 
        # A real implementation would allow linking. For simplicity, we'll just ingest by path and store the path.
        parser = find_parser(filepath)
        try:
            parsed = parser.parse(filepath)
        except ImportError as e:
            logger.warning(f"Skipping {filepath}: {e}")
            raise
        doc_id = self._next_doc_id()
        doc = Document(
            doc_id=doc_id,
            filepath=filepath,
            metadata=parsed.get("metadata", {}),
            content=parsed.get("text", ""),
            pages=parsed.get("pages", []),
            members=parsed.get("members", []),
        )
        self.indexer.add_document(doc)
        logger.info(f"Ingested {filepath.name} as document {doc.id}")
        return doc

    def ingest_directory(self, directory: Union[str, Path], recursive: bool = True) -> List[Document]:
        """Walk directory and ingest all files."""
        directory = Path(directory)
        docs = []
        for path in directory.rglob("*") if recursive else directory.iterdir():
            if path.is_file():
                try:
                    docs.append(self.ingest(path))
                except Exception as e:
                    logger.warning(f"Failed to ingest {path}: {e}")
        return docs

    def organize(self) -> None:
        """Scan and update metadata; could rebuild catalogs, tags, etc."""
        # In a real system, we'd scan for new files, update modified times, etc.
        logger.info("Organizing knowledge base (no-op stub).")

    def create_catalog(self, name: str, query: Optional[str] = None) -> Catalog:
        catalog = Catalog(name, query)
        self.catalogs[name] = catalog
        return catalog

    def add_to_catalog(self, catalog_name: str, doc: Document):
        if catalog_name not in self.catalogs:
            raise KeyError(f"Catalog {catalog_name} does not exist")
        self.catalogs[catalog_name].add(doc)

    def add_tag(self, doc: Document, tag: str):
        doc.tags.add(tag)
        self._update_document_tags(doc)

    def remove_tag(self, doc: Document, tag: str):
        doc.tags.discard(tag)
        self._update_document_tags(doc)

    def _update_document_tags(self, doc: Document):
        cursor = self.indexer.conn.cursor()
        cursor.execute(
            "UPDATE documents SET tags=?, modified_date=? WHERE id=?",
            (json.dumps(list(doc.tags)), datetime.datetime.now().isoformat(), doc.id),
        )
        self.indexer.conn.commit()

    def search(
        self,
        query: str,
        use_embeddings: bool = False,
        rerank: bool = False,
        source_quota: Optional[int] = None,
        limit: int = 10,
    ) -> List[Tuple[Document, float]]:
        """
        Recall candidates with lexical search by default.
        If use_embeddings is True, attempts vector search.
        Reranking and source quotas are placeholders.
        """
        if use_embeddings:
            # Generate embedding from query (stub)
            # In practice, call embedding model.
            embedding = []  # dummy
            results = self.indexer.search_embeddings(embedding, limit)
            if not results:
                # fallback
                results = self.indexer.search_lexical(query, limit)
        else:
            results = self.indexer.search_lexical(query, limit)

        if rerank:
            # Placeholder: reorder by a cross-encoder
            logger.info("Reranking (stub).")

        if source_quota is not None:
            results = results[:source_quota]

        # Load full documents
        out: List[Tuple[Document, float]] = []
        for doc_id, score in results:
            doc = self.indexer.load_document(doc_id)
            if doc is not None:
                out.append((doc, score))
        return out

    def relate(self, doc: Document) -> List[Document]:
        """Find related documents."""
        related_ids = self.relation_miner.find_related(doc)
        return [self.indexer.load_document(did) for did in related_ids if self.indexer.load_document(did) is not None]

    # -------------------------------------------------------------------
    # Reading windows
    def read_section(self, doc: Document, section_type: str = "any", **kwargs) -> str:
        """
        Read specific part of a document.
        section_type: 'lines', 'pages', 'member', 'table_slice'
        """
        if section_type == "lines":
            start = kwargs.get("start", 0)
            end = kwargs.get("end", None)
            return doc.read_lines(start, end)
        elif section_type == "pages":
            page_range = kwargs.get("page_range")
            if page_range is None:
                raise ValueError("page_range required")
            return doc.read_pages(page_range)
        elif section_type == "member":
            name = kwargs.get("name")
            if not name:
                raise ValueError("name required for archive member")
            return doc.read_member(name)
        elif section_type == "table_slice":
            sheet = kwargs.get("sheet")
            cell_range = kwargs.get("cell_range")
            return doc.read_table_slice(sheet, cell_range)
        else:
            # Default: return a snippet of content
            return doc.content[:2000]

    # -------------------------------------------------------------------
    # Agent research
    def investigate(self, query: str, top_k: int = 5) -> InvestigationNote:
        """
        Research agent:
        1. Recall candidates.
        2. Read relevant sections from top documents.
        3. Produce a cited answer using LLM.
        4. Write durable investigation note.
        """
        # 1. Retrieve
        candidates = self.search(query, limit=top_k)
        if not candidates:
            return InvestigationNote(
                query=query,
                answer="No relevant documents found.",
                sources=[],
            )
        # 2. Prepare context: for each candidate, get a snippet and maybe full text.
        # For brevity, we include a chunk from each.
        context_parts = []
        sources: List[Tuple[DocumentID, str]] = []
        for doc, score in candidates:
            # Choose a reading window: if the doc has pages, read first page; else first 500 chars.
            window = doc.content[:1000]
            context_parts.append(f"Document '{doc.title}' (id={doc.id}):\n{window}\n")
            sources.append((doc.id, window))
        context = "\n---\n".join(context_parts)
        # 3. Build prompt and generate answer
        prompt = (
            f"You are a research assistant. Using the provided sources, answer the question concisely "
            f"and cite sources by document id.\n\n"
            f"Sources:\n{context}\n\n"
            f"Question: {query}\n"
            f"Answer: "
        )
        answer = self.llm.generate(prompt)
        # 4. Create note and add to journal
        note = InvestigationNote(query=query, answer=answer, sources=sources)
        self.journal.add_entry(note.answer, related_docs=[doc_id for doc_id, _ in sources])
        # Also store the note in DB? We can keep a separate table for notes.
        # For now, journal is in-memory and can be saved.
        return note

    def get_journal_entries(self) -> List[Dict]:
        return self.journal.entries

    def close(self):
        self.indexer.close()


# ---------------------------------------------------------------------------
# Example usage (optional)
if __name__ == "__main__":
    # Create a temporary knowledge base
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        kb_root = Path(tmpdir) / "kb"
        kb_root.mkdir()
        mar = Marginalia(root_folder=kb_root)

        # Create a sample file
        sample_file = kb_root / "notes.txt"
        sample_file.write_text("Marginalia is a knowledge management system with LLM agents.\nIt supports many file types.", encoding="utf-8")

        doc = mar.ingest(sample_file)
        mar.add_tag(doc, "concept")
        print("Ingested:", doc.title)

        # Search
        results = mar.search("knowledge management")
        for d, score in results:
            print(f"Found: {d.title} (score {score})")

        # Investigate
        note = mar.investigate("What is Marginalia?")
        print("Answer:", note.answer)

        mar.close()