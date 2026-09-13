import os
import sys
import sqlite3
import json
import re
import hashlib
import mimetypes
import zipfile
import io
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Marginalia")

# Attempt imports for file parsers, graceful fallback
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import docx
except ImportError:
    docx = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import markdown
except ImportError:
    markdown = None

# ======================================================================
# Data models
# ======================================================================

@dataclass
class DocumentMetadata:
    path: str
    mime_type: str
    title: str = ""
    authors: List[str] = field(default_factory=list)
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    size: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass
class InvestigationNote:
    id: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    question: str = ""
    answer: str = ""
    citations: List[Dict[str, Any]] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SearchResult:
    document_id: int
    path: str
    title: str
    snippet: str
    score: float
    metadata: Dict[str, Any]

# ======================================================================
# Database schema and manager
# ======================================================================

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()
    
    def _init_schema(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                title TEXT,
                content TEXT,
                metadata_json TEXT,
                mime_type TEXT,
                created TEXT,
                modified TEXT,
                size INTEGER
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
                query_json TEXT,
                created TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                relation_type TEXT,
                weight REAL DEFAULT 1.0,
                FOREIGN KEY (source_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS investigation_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT (datetime('now')),
                question TEXT,
                answer TEXT,
                citations_json TEXT,
                references_json TEXT,
                metadata_json TEXT
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                title, content, content='documents', content_rowid='id'
            );
            CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
                INSERT INTO documents_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
            END;
            CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
            END;
            CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
                INSERT INTO documents_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
            END;
        """)
        self.conn.commit()
    
    def execute(self, sql, params=None):
        if params is None:
            return self.conn.execute(sql)
        return self.conn.execute(sql, params)
    
    def executemany(self, sql, seq):
        self.conn.executemany(sql, seq)
    
    def commit(self):
        self.conn.commit()
    
    def close(self):
        self.conn.close()

# ======================================================================
# File parsers / extractors
# ======================================================================

class FileParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> Tuple[str, DocumentMetadata]:
        """Return (content, metadata)"""
        pass

class PlainTextParser(FileParser):
    def parse(self, file_path: str) -> Tuple[str, DocumentMetadata]:
        p = Path(file_path)
        stat = p.stat()
        mime = mimetypes.guess_type(file_path)[0] or "text/plain"
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        meta = DocumentMetadata(
            path=str(p.resolve()),
            mime_type=mime,
            title=p.stem,
            modified=datetime.fromtimestamp(stat.st_mtime),
            created=datetime.fromtimestamp(stat.st_ctime) if hasattr(stat, 'st_ctime') else None,
            size=stat.st_size,
        )
        return content, meta

class MarkdownParser(PlainTextParser):
    def parse(self, file_path: str) -> Tuple[str, DocumentMetadata]:
        content, meta = super().parse(file_path)
        # Simple title extraction from first heading
        first_heading = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if first_heading:
            meta.title = first_heading.group(1).strip()
        return content, meta

class PDFParser(FileParser):
    def parse(self, file_path: str) -> Tuple[str, DocumentMetadata]:
        if PyPDF2 is None:
            raise ImportError("PyPDF2 is required for PDF parsing")
        content_parts = []
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            metadata = reader.metadata
            num_pages = len(reader.pages)
            for page_num in range(num_pages):
                page = reader.pages[page_num]
                text = page.extract_text()
                if text:
                    content_parts.append(text)
        content = "\n".join(content_parts)
        p = Path(file_path)
        stat = p.stat()
        mime = "application/pdf"
        title = ""
        if metadata and metadata.title:
            title = metadata.title
        else:
            title = p.stem
        meta = DocumentMetadata(
            path=str(p.resolve()),
            mime_type=mime,
            title=title,
            modified=datetime.fromtimestamp(stat.st_mtime),
            created=datetime.fromtimestamp(stat.st_ctime) if hasattr(stat, 'st_ctime') else None,
            size=stat.st_size,
            extra={"num_pages": num_pages}
        )
        return content, meta

class DOCXParser(FileParser):
    def parse(self, file_path: str) -> Tuple[str, DocumentMetadata]:
        if docx is None:
            raise ImportError("python-docx is required for DOCX parsing")
        p = Path(file_path)
        stat = p.stat()
        doc = docx.Document(file_path)
        content = "\n".join([para.text for para in doc.paragraphs])
        # Extract properties
        core_props = doc.core_properties
        title = core_props.title or p.stem
        meta = DocumentMetadata(
            path=str(p.resolve()),
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            title=title,
            modified=datetime.fromtimestamp(stat.st_mtime),
            created=core_props.created if core_props.created else None,
            size=stat.st_size,
            authors=[core_props.author] if core_props.author else [],
        )
        return content, meta

class ImageParser(FileParser):
    def parse(self, file_path: str) -> Tuple[str, DocumentMetadata]:
        if Image is None:
            raise ImportError("Pillow is required for image parsing")
        p = Path(file_path)
        stat = p.stat()
        img = Image.open(file_path)
        # Use basic metadata
        mime = "image/" + (img.format.lower() if img.format else "png")
        meta = DocumentMetadata(
            path=str(p.resolve()),
            mime_type=mime,
            title=p.stem,
            modified=datetime.fromtimestamp(stat.st_mtime),
            created=datetime.fromtimestamp(stat.st_ctime) if hasattr(stat, 'st_ctime') else None,
            size=stat.st_size,
            extra={"width": img.width, "height": img.height}
        )
        # Images have no textual content, return metadata as placeholder
        content = f"[Image: {p.name} ({img.width}x{img.height})]"
        return content, meta

class SpreadsheetParser(FileParser):
    def parse(self, file_path: str) -> Tuple[str, DocumentMetadata]:
        if openpyxl is None:
            raise ImportError("openpyxl is required for spreadsheet parsing")
        p = Path(file_path)
        stat = p.stat()
        wb = openpyxl.load_workbook(file_path, data_only=True)
        content_parts = []
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            content_parts.append(f"Sheet: {sheet_name}")
            for row in sheet.iter_rows(values_only=True):
                content_parts.append("\t".join([str(cell) if cell is not None else "" for cell in row]))
        content = "\n".join(content_parts)
        meta = DocumentMetadata(
            path=str(p.resolve()),
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            title=p.stem,
            modified=datetime.fromtimestamp(stat.st_mtime),
            size=stat.st_size,
            extra={"sheets": wb.sheetnames}
        )
        return content, meta

class LogParser(PlainTextParser):
    pass

class ArchiveParser(FileParser):
    def parse(self, file_path: str) -> Tuple[str, DocumentMetadata]:
        p = Path(file_path)
        stat = p.stat()
        content_parts = []
        members = []
        with zipfile.ZipFile(file_path, 'r') as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                members.append(info.filename)
                try:
                    with zf.open(info) as f:
                        # Try to read as text, limited size
                        raw = f.read(1024*1024).decode('utf-8', errors='ignore')
                        content_parts.append(f"--- Member: {info.filename} ---\n{raw}\n")
                except Exception:
                    content_parts.append(f"--- Member: {info.filename} (binary) ---\n")
        content = "\n".join(content_parts)
        meta = DocumentMetadata(
            path=str(p.resolve()),
            mime_type="application/zip",
            title=p.stem,
            modified=datetime.fromtimestamp(stat.st_mtime),
            size=stat.st_size,
            extra={"members": members, "count": len(members)}
        )
        return content, meta

PARSER_REGISTRY = {
    'text/plain': PlainTextParser,
    'text/markdown': MarkdownParser,
    'text/x-markdown': MarkdownParser,
    'application/pdf': PDFParser,
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': DOCXParser,
    'image/jpeg': ImageParser,
    'image/png': ImageParser,
    'image/gif': ImageParser,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': SpreadsheetParser,
    'application/zip': ArchiveParser,
    'application/x-zip-compressed': ArchiveParser,
}

def get_parser_for_mime(mime_type: str) -> FileParser:
    for mime, parser_cls in PARSER_REGISTRY.items():
        if mime_type.startswith(mime.split('/')[0]) and mime_type.split('/')[0] in ('text',):  # text/* fallback
            return MarkdownParser() if 'markdown' in mime_type else PlainTextParser()
    return PARSER_REGISTRY.get(mime_type, PlainTextParser)()

# ======================================================================
# Core library components
# ======================================================================

class DocumentStore:
    def __init__(self, db: Database):
        self.db = db
    
    def add_document(self, content: str, metadata: DocumentMetadata, tags: List[str] = None) -> int:
        cur = self.db.execute(
            "INSERT OR REPLACE INTO documents (path, title, content, metadata_json, mime_type, created, modified, size) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                metadata.path,
                metadata.title,
                content,
                json.dumps({"authors": metadata.authors, "extra": metadata.extra, "mime": metadata.mime_type}),
                metadata.mime_type,
                metadata.created.isoformat() if metadata.created else None,
                metadata.modified.isoformat() if metadata.modified else None,
                metadata.size
            )
        )
        doc_id = cur.lastrowid
        if tags:
            self.add_tags(doc_id, tags)
        self.db.commit()
        return doc_id
    
    def add_tags(self, doc_id: int, tags: List[str]):
        for tag_name in tags:
            tag_name = tag_name.strip().lower()
            if not tag_name:
                continue
            cur = self.db.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
            self.db.execute("INSERT OR IGNORE INTO document_tags (doc_id, tag_id) VALUES (?, (SELECT id FROM tags WHERE name=?))",
                            (doc_id, tag_name))
        self.db.commit()
    
    def get_document(self, doc_id: int) -> Optional[Dict]:
        row = self.db.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if row:
            return dict(row)
        return None
    
    def list_documents(self) -> List[Dict]:
        rows = self.db.execute("SELECT id, path, title, mime_type FROM documents ORDER BY title").fetchall()
        return [dict(r) for r in rows]
    
    def delete_document(self, doc_id: int):
        self.db.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        self.db.commit()

class Catalog:
    def __init__(self, db: Database):
        self.db = db
        self.store = DocumentStore(db)
    
    def index_file(self, file_path: str, tags: List[str] = None) -> Optional[int]:
        path = Path(file_path).resolve()
        mime_type, _ = mimetypes.guess_type(str(path))
        mime_type = mime_type or 'text/plain'
        parser = get_parser_for_mime(mime_type)
        try:
            content, metadata = parser.parse(str(path))
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return None
        return self.store.add_document(content, metadata, tags=tags)
    
    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        # Lexical search via FTS5
        rows = self.db.execute(
            """SELECT d.id, d.path, d.title, snippet(documents_fts, 1, '<b>', '</b>', '...', 32) as snippet,
                bm25(documents_fts) as score
            FROM documents_fts JOIN documents d ON d.id = documents_fts.rowid
            WHERE documents_fts MATCH ?
            ORDER BY score
            LIMIT ?""",
            (query, top_k)
        ).fetchall()
        results = []
        for r in rows:
            results.append(SearchResult(
                document_id=r['id'],
                path=r['path'],
                title=r['title'],
                snippet=r['snippet'],
                score=r['score'],
                metadata={}
            ))
        return results

class EmbeddingService(ABC):
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass
    
    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        pass

class DummyEmbeddingService(EmbeddingService):
    """Placeholder; replace with real sentence-transformers or API."""
    def __init__(self, dim: int = 128):
        self.dim = dim
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Returns zero vectors as placeholder
        return [[0.0]*self.dim for _ in texts]
    
    def embed_query(self, text: str) -> List[float]:
        return [0.0]*self.dim

class VectorSearch:
    def __init__(self, db: Database, embedder: EmbeddingService):
        self.db = db
        self.embedder = embedder
        self._ensure_embeddings_table()
    
    def _ensure_embeddings_table(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                doc_id INTEGER PRIMARY KEY,
                embedding BLOB,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)
        self.db.commit()
    
    def index_documents(self):
        rows = self.db.execute("SELECT id, content FROM documents WHERE id NOT IN (SELECT doc_id FROM embeddings)").fetchall()
        if not rows:
            return
        ids = [r['id'] for r in rows]
        texts = [r['content'] for r in rows]
        embeddings = self.embedder.embed_documents(texts)
        for doc_id, emb in zip(ids, embeddings):
            blob = struct.pack(f'{len(emb)}f', *emb)
            self.db.execute("INSERT OR REPLACE INTO embeddings (doc_id, embedding) VALUES (?, ?)", (doc_id, blob))
        self.db.commit()
    
    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        query_vec = self.embedder.embed_query(query)
        self.index_documents()  # ensure up-to-date
        # Load all embeddings and compute cosine similarity (simplistic)
        rows = self.db.execute("SELECT e.doc_id, e.embedding, d.path, d.title FROM embeddings e JOIN documents d ON d.id=e.doc_id").fetchall()
        import struct
        import math
        results = []
        for row in rows:
            emb_blob = row['embedding']
            n = len(emb_blob) // 4
            doc_vec = list(struct.unpack(f'{n}f', emb_blob))
            # cosine similarity
            dot = sum(a*b for a,b in zip(query_vec, doc_vec))
            norm_q = math.sqrt(sum(a*a for a in query_vec))
            norm_d = math.sqrt(sum(b*b for b in doc_vec))
            if norm_q == 0 or norm_d == 0:
                score = 0.0
            else:
                score = dot / (norm_q * norm_d)
            results.append(SearchResult(
                document_id=row['doc_id'],
                path=row['path'],
                title=row['title'],
                snippet="",
                score=score,
                metadata={}
            ))
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, candidates: List[SearchResult]) -> List[SearchResult]:
        pass

class IdentityReranker(Reranker):
    def rerank(self, query: str, candidates: List[SearchResult]) -> List[SearchResult]:
        return candidates

class CrossEncoderReranker(Reranker):
    """Placeholder for a cross-encoder model."""
    def rerank(self, query: str, candidates: List[SearchResult]) -> List[SearchResult]:
        # In practice would use model to score (query, document) pairs.
        # Kept as identity for now.
        return candidates

class SourceQuota:
    def __init__(self, max_per_source: int = 3):
        self.max_per_source = max_per_source
    
    def apply(self, results: List[SearchResult]) -> List[SearchResult]:
        source_counts = defaultdict(int)
        filtered = []
        for res in results:
            # Use top-level folder as source
            source = Path(res.path).parent.name if res.path else "unknown"
            if source_counts[source] < self.max_per_source:
                filtered.append(res)
                source_counts[source] += 1
        return filtered

class Reader:
    """Reads original sections, pages, lines, archive members, table slices."""
    @staticmethod
    def read_section(document: Dict, section_ref: str) -> str:
        """section_ref format: 'line 10-20', 'page 2', 'member:filename', 'sheet:Sales!A1:C10'"""
        content = document.get('content', '')
        mime = document.get('mime_type', 'text/plain')
        if section_ref.startswith('line '):
            # line range: 'line 5-10' or 'line 5'
            range_str = section_ref[5:].strip()
            lines = content.splitlines()
            if '-' in range_str:
                start, end = map(int, range_str.split('-'))
                return "\n".join(lines[start-1:end])
            else:
                start = int(range_str)
                return lines[start-1] if start-1 < len(lines) else ""
        elif section_ref.startswith('page '):
            if PyPDF2 is None:
                return "PDF reader not available"
            page_num = int(section_ref[5:].strip())
            path = document['path']
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                if page_num-1 < len(reader.pages):
                    return reader.pages[page_num-1].extract_text() or ""
        elif section_ref.startswith('member:'):
            member_name = section_ref[7:].strip()
            path = document['path']
            if not zipfile.is_zipfile(path):
                return "Not an archive"
            with zipfile.ZipFile(path, 'r') as zf:
                try:
                    with zf.open(member_name) as f:
                        return f.read().decode('utf-8', errors='ignore')
                except KeyError:
                    return f"Member '{member_name}' not found"
        elif section_ref.startswith('sheet:'):
            # sheet:SheetName!A1:C10 or sheet:SheetName
            if openpyxl is None:
                return "Spreadsheet reader not available"
            path = document['path']
            wb = openpyxl.load_workbook(path, data_only=True)
            part = section_ref[6:].strip()
            if '!' in part:
                sheet_name, cell_range = part.split('!', 1)
            else:
                sheet_name, cell_range = part, None
            if sheet_name not in wb.sheetnames:
                return f"Sheet '{sheet_name}' not found"
            ws = wb[sheet_name]
            if cell_range:
                # Simple range extraction
                rows_data = []
                try:
                    for row in ws[cell_range]:
                        rows_data.append(" | ".join([str(cell.value) if cell.value is not None else "" for cell in row]))
                    return "\n".join(rows_data)
                except Exception as e:
                    return f"Error reading range: {e}"
            else:
                return "\n".join([" | ".join([str(cell.value) if cell.value is not None else "" for cell in row]) for row in ws.iter_rows()])
        else:
            # default: return content
            return content

class Journal:
    def __init__(self, db: Database):
        self.db = db
    
    def add_note(self, note: InvestigationNote):
        self.db.execute(
            "INSERT INTO investigation_notes (question, answer, citations_json, references_json, metadata_json) VALUES (?, ?, ?, ?, ?)",
            (
                note.question,
                note.answer,
                json.dumps(note.citations),
                json.dumps(note.references),
                json.dumps(note.metadata)
            )
        )
        self.db.commit()
    
    def get_notes(self, limit: int = 10) -> List[InvestigationNote]:
        rows = self.db.execute("SELECT * FROM investigation_notes ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        return [InvestigationNote(
            id=r['id'],
            timestamp=datetime.fromisoformat(r['timestamp']),
            question=r['question'],
            answer=r['answer'],
            citations=json.loads(r['citations_json']),
            references=json.loads(r['references_json']),
            metadata=json.loads(r['metadata_json']),
        ) for r in rows]
    
    def search_notes(self, query: str) -> List[InvestigationNote]:
        # Simple LIKE search on question/answer
        rows = self.db.execute(
            "SELECT * FROM investigation_notes WHERE question LIKE ? OR answer LIKE ? ORDER BY timestamp DESC",
            (f'%{query}%', f'%{query}%')
        ).fetchall()
        return [InvestigationNote(
            id=r['id'],
            timestamp=datetime.fromisoformat(r['timestamp']),
            question=r['question'],
            answer=r['answer'],
            citations=json.loads(r['citations_json']),
            references=json.loads(r['references_json']),
            metadata=json.loads(r['metadata_json']),
        ) for r in rows]

class RelationMiner:
    def __init__(self, db: Database):
        self.db = db
    
    def mine_relations(self, doc_id: int):
        # Simple: co-tag relations
        tags = [r['tag_id'] for r in self.db.execute("SELECT tag_id FROM document_tags WHERE doc_id=?", (doc_id,)).fetchall()]
        if not tags:
            return
        placeholders = ','.join('?' for _ in tags)
        related = self.db.execute(
            f"SELECT DISTINCT doc_id FROM document_tags WHERE tag_id IN ({placeholders}) AND doc_id != ?",
            (*tags, doc_id)
        ).fetchall()
        for rel in related:
            self.db.execute(
                "INSERT OR IGNORE INTO relations (source_id, target_id, relation_type, weight) VALUES (?, ?, 'cotag', 0.8)",
                (doc_id, rel['doc_id'])
            )
        self.db.commit()
    
    def get_related(self, doc_id: int) -> List[int]:
        rows = self.db.execute("SELECT target_id FROM relations WHERE source_id=?", (doc_id,)).fetchall()
        return [r['target_id'] for r in rows]

# ======================================================================
# LLM Agent (simplified, replace with actual API)
# ======================================================================

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

class ConsoleLLM(LLMProvider):
    """A stub that asks the user (console) to simulate LLM; replace with API."""
    def generate(self, prompt: str) -> str:
        print("=== LLM Prompt ===")
        print(prompt[:500] + "...")
        print("=== Enter LLM response (type 'END' on a line by itself) ===")
        lines = []
        while True:
            line = sys.stdin.readline()
            if line.strip() == "END":
                break
            lines.append(line)
        return "".join(lines)

class Agent:
    def __init__(self, llm: LLMProvider, reader: Reader, catalog: Catalog, journal: Journal, reranker: Reranker = None, quota: SourceQuota = None):
        self.llm = llm
        self.reader = reader
        self.catalog = catalog
        self.journal = journal
        self.reranker = reranker or IdentityReranker()
        self.quota = quota or SourceQuota()
    
    def answer(self, question: str, max_sources: int = 5) -> InvestigationNote:
        # Step 1: lexical search
        search_results = self.catalog.search(question, top_k=max_sources*2)
        # Step 2: rerank
        ranked = self.reranker.rerank(question, search_results)
        # Step 3: apply source quota
        filtered = self.quota.apply(ranked)[:max_sources]
        # Step 4: read context windows
        contexts = []
        for res in filtered:
            doc = self.catalog.store.get_document(res.document_id)
            if not doc:
                continue
            snippet = res.snippet if res.snippet else "Full document not shown in snippet"
            # For answer, we could read a window based on snippet context, but for simplicity, we take snippet
            contexts.append({
                "title": doc['title'],
                "path": doc['path'],
                "content_snippet": snippet,
                "doc_id": doc['id']
            })
        # Step 5: construct prompt
        prompt = self._build_prompt(question, contexts)
        # Step 6: get LLM answer
        answer_text = self.llm.generate(prompt)
        # Step 7: extract citations (simple pattern: [ref: path or snippet])
        citations = self._extract_citations(answer_text, contexts)
        # Step 8: create investigation note
        note = InvestigationNote(
            question=question,
            answer=answer_text,
            citations=citations,
            references=[ctx['path'] for ctx in contexts],
            metadata={"source_count": len(contexts)}
        )
        self.journal.add_note(note)
        return note
    
    def _build_prompt(self, question: str, contexts: List[Dict]) -> str:
        ctx_str = "\n\n".join([f"Source: {c['title']} ({c['path']})\nContent: {c['content_snippet']}" for c in contexts])
        prompt = f"""You are a research assistant. Answer the question based on the provided sources. Cite the sources using [ref: path] or [ref: title] where applicable.

Sources:
{ctx_str}

Question: {question}

Answer with citations:"""
        return prompt
    
    def _extract_citations(self, text: str, contexts: List[Dict]) -> List[Dict]:
        # Simple regex
        refs = re.findall(r'\[ref:\s*(.*?)\]', text)
        citations = []
        for ref in refs:
            # try to match path or title
            for ctx in contexts:
                if ref in ctx['path'] or ref.lower() in ctx['title'].lower():
                    citations.append({"ref": ref, "path": ctx['path'], "title": ctx['title']})
                    break
            else:
                citations.append({"ref": ref})
        return citations

# ======================================================================
# Main application class
# ======================================================================

class Marginalia:
    def __init__(self, kb_path: str, llm: LLMProvider = None, use_embeddings: bool = False):
        self.kb_path = Path(kb_path).resolve()
        self.kb_path.mkdir(parents=True, exist_ok=True)
        db_path = self.kb_path / "marginalia.db"
        self.db = Database(str(db_path))
        self.catalog = Catalog(self.db)
        self.journal = Journal(self.db)
        self.relation_miner = RelationMiner(self.db)
        self.reader = Reader()
        self.llm = llm or ConsoleLLM()
        self.agent = Agent(self.llm, self.reader, self.catalog, self.journal)
        self.embedding_service = DummyEmbeddingService() if use_embeddings else None
        self.vector_search = VectorSearch(self.db, self.embedding_service) if use_embeddings else None
    
    def ingest(self, file_path: str, tags: List[str] = None) -> Optional[int]:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        # Check if already indexed (by resolved path)
        existing = self.db.execute("SELECT id FROM documents WHERE path=?", (str(path.resolve()),)).fetchone()
        if existing:
            logger.info(f"File already indexed: {path}")
            return existing['id']
        doc_id = self.catalog.index_file(str(path), tags=tags)
        if doc_id:
            # mine relations
            self.relation_miner.mine_relations(doc_id)
            # optionally embed
            if self.vector_search:
                self.vector_search.index_documents()
            logger.info(f"Ingested: {path} (id={doc_id})")
        return doc_id
    
    def query(self, question: str) -> InvestigationNote:
        return self.agent.answer(question)
    
    def list_documents(self):
        return self.catalog.store.list_documents()
    
    def get_notes(self, limit=10):
        return self.journal.get_notes(limit)
    
    def search_notes(self, query):
        return self.journal.search_notes(query)

# ======================================================================
# Example usage
# ======================================================================
if __name__ == "__main__":
    import tempfile
    import textwrap
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup Marginalia
        m = Marginalia(tmpdir)
        
        # Create some test files
        (Path(tmpdir) / "research").mkdir()
        (Path(tmpdir) / "research" / "python.md").write_text("# Python\nPython is a programming language.\n## Features\n- Easy to learn\n- Powerful")
        (Path(tmpdir) / "research" / "notes.txt").write_text("Meeting notes: Discussed ML project timeline.")
        
        # Ingest files
        m.ingest(str(Path(tmpdir) / "research" / "python.md"), tags=["programming", "python"])
        m.ingest(str(Path(tmpdir) / "research" / "notes.txt"), tags=["meeting", "ml"])
        
        # List documents
        print("Documents:")
        for doc in m.list_documents():
            print(f"  {doc['id']}: {doc['title']} ({doc['path']})")
        
        # Query (requires interactive input for LLM stub; provide mock answer)
        print("\nEnter a mock answer for the query:")
        # To automate, we'll manually inject a note instead of interactive LLM
        note = InvestigationNote(
            question="What is Python?",
            answer="Python is an easy-to-learn programming language [ref: python.md].",
            citations=[{"ref": "python.md", "path": str(Path(tmpdir)/"research"/"python.md"), "title": "Python"}],
            references=[str(Path(tmpdir)/"research"/"python.md")]
        )
        m.journal.add_note(note)
        
        # Retrieve notes
        print("\nInvestigation notes:")
        for n in m.get_notes():
            print(f"Q: {n.question}")
            print(f"A: {n.answer[:100]}...")
        
        # Durable recall
        past = m.search_notes("Python")
        print(f"\nFound {len(past)} notes about Python.")