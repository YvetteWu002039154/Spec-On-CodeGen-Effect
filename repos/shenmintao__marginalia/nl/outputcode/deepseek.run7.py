import os
import sqlite3
import json
import logging
import pickle
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union, Generator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

import numpy as np

# Optional dependencies - will fail gracefully if not installed
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
try:
    from docx import Document
except ImportError:
    Document = None
try:
    import openpyxl
except ImportError:
    openpyxl = None
try:
    from PIL import Image
except ImportError:
    Image = None
try:
    from sentence_transformers import SentenceTransformer, CrossEncoder
except ImportError:
    SentenceTransformer = None
    CrossEncoder = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("marginalia")

# --------------------- Data structures ---------------------
class FileType(Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    IMAGE = "image"
    SPREADSHEET = "spreadsheet"
    LOG = "log"
    ARCHIVE = "archive"
    UNKNOWN = "unknown"

@dataclass
class ChunkLocation:
    file_path: str
    file_type: FileType
    # For text/log/markdown
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    # For PDF
    page: Optional[int] = None
    # For DOCX
    start_para: Optional[int] = None
    end_para: Optional[int] = None
    # For spreadsheet
    sheet: Optional[str] = None
    start_row: Optional[int] = None
    end_row: Optional[int] = None
    start_col: Optional[int] = None
    end_col: Optional[int] = None
    # For archive
    member: Optional[str] = None

    def to_dict(self) -> Dict:
        d = self.__dict__.copy()
        d['file_type'] = self.file_type.value
        return d

    @staticmethod
    def from_dict(data: Dict) -> 'ChunkLocation':
        data['file_type'] = FileType(data['file_type'])
        return ChunkLocation(**data)

@dataclass
class Chunk:
    id: int
    file_id: int
    text: str
    location: ChunkLocation
    parent_chunk_id: Optional[int] = None

@dataclass
class SearchResult:
    chunk: Chunk
    score: float
    source: str  # file path or identifier

@dataclass
class DocumentMeta:
    file_path: str
    title: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    custom: Dict[str, Any] = field(default_factory=dict)

# --------------------- Database & Content Store ---------------------
class ContentStore:
    """SQLite-based store for file metadata, chunks, and full-text index."""

    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                file_type TEXT NOT NULL,
                title TEXT,
                created TEXT,
                modified TEXT,
                author TEXT,
                description TEXT,
                metadata_json TEXT
            );
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS file_tags (
                file_id INTEGER,
                tag_id INTEGER,
                FOREIGN KEY (file_id) REFERENCES files(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id),
                PRIMARY KEY (file_id, tag_id)
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                text,
                content='chunks',
                content_rowid='id'
            );
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY,
                file_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                location_json TEXT NOT NULL,
                parent_chunk_id INTEGER,
                FOREIGN KEY (file_id) REFERENCES files(id)
            );

            -- Vector store for embeddings (base table)
            CREATE TABLE IF NOT EXISTS vectors (
                chunk_id INTEGER PRIMARY KEY,
                vector BLOB NOT NULL,
                FOREIGN KEY (chunk_id) REFERENCES chunks(id)
            );

            -- Triggers to keep FTS in sync
            CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
            END;
            CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.id, old.text);
            END;
            CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.id, old.text);
                INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
            END;
        """)
        self.conn.commit()

    def add_file(self, path: str, file_type: FileType, meta: DocumentMeta = None) -> int:
        """Insert or update a file record. Returns file id."""
        cur = self.conn.cursor()
        meta_json = json.dumps(meta.custom) if meta else "{}"
        cur.execute("""
            INSERT INTO files (path, file_type, title, created, modified, author, description, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                file_type=excluded.file_type,
                title=excluded.title,
                created=excluded.created,
                modified=excluded.modified,
                author=excluded.author,
                description=excluded.description,
                metadata_json=excluded.metadata_json
        """, (path, file_type.value, meta.title if meta else None,
              meta.created_date if meta else None, meta.modified_date if meta else None,
              meta.author if meta else None, meta.description if meta else None,
              meta_json))
        file_id = cur.lastrowid
        # Handle tags if meta provided
        if meta and meta.tags:
            file_id = cur.execute("SELECT id FROM files WHERE path=?", (path,)).fetchone()['id']
            self._set_file_tags(file_id, meta.tags)
        self.conn.commit()
        return file_id

    def _set_file_tags(self, file_id: int, tags: List[str]):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM file_tags WHERE file_id=?", (file_id,))
        for tag in tags:
            cur.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (tag,))
            tag_id = cur.execute("SELECT id FROM tags WHERE name=?", (tag,)).fetchone()['id']
            cur.execute("INSERT OR IGNORE INTO file_tags(file_id, tag_id) VALUES (?,?)", (file_id, tag_id))
        self.conn.commit()

    def get_file_meta(self, file_path: str) -> Optional[DocumentMeta]:
        cur = self.conn.cursor()
        row = cur.execute("SELECT * FROM files WHERE path=?", (file_path,)).fetchone()
        if not row:
            return None
        tags = self._get_file_tags(row['id'])
        return DocumentMeta(
            file_path=row['path'],
            title=row['title'],
            tags=tags,
            created_date=row['created'],
            modified_date=row['modified'],
            author=row['author'],
            description=row['description'],
            custom=json.loads(row['metadata_json'] or '{}')
        )

    def _get_file_tags(self, file_id: int) -> List[str]:
        cur = self.conn.cursor()
        rows = cur.execute("""
            SELECT t.name FROM tags t
            JOIN file_tags ft ON t.id = ft.tag_id
            WHERE ft.file_id = ?
        """, (file_id,)).fetchall()
        return [r['name'] for r in rows]

    def add_chunk(self, file_id: int, text: str, location: ChunkLocation, parent_chunk_id: Optional[int] = None) -> int:
        cur = self.conn.cursor()
        location_json = json.dumps(location.to_dict())
        cur.execute("INSERT INTO chunks (file_id, text, location_json, parent_chunk_id) VALUES (?,?,?,?)",
                   (file_id, text, location_json, parent_chunk_id))
        self.conn.commit()
        return cur.lastrowid

    def add_vector(self, chunk_id: int, vector: np.ndarray):
        cur = self.conn.cursor()
        vector_blob = vector.astype(np.float32).tobytes()
        cur.execute("INSERT OR REPLACE INTO vectors (chunk_id, vector) VALUES (?,?)", (chunk_id, vector_blob))
        self.conn.commit()

    def delete_file_chunks(self, file_id: int):
        self.conn.execute("DELETE FROM vectors WHERE chunk_id IN (SELECT id FROM chunks WHERE file_id=?)", (file_id,))
        self.conn.execute("DELETE FROM chunks WHERE file_id=?", (file_id,))
        self.conn.commit()

    def get_chunks_for_file(self, file_id: int) -> List[Chunk]:
        return [self._row_to_chunk(row) for row in
                self.conn.execute("SELECT * FROM chunks WHERE file_id=? ORDER BY id", (file_id,)).fetchall()]

    def get_all_files(self) -> List[str]:
        rows = self.conn.execute("SELECT path FROM files").fetchall()
        return [r['path'] for r in rows]

    def get_file_by_id(self, file_id: int) -> Optional[Dict]:
        return self.conn.execute("SELECT * FROM files WHERE id=?", (file_id,)).fetchone()

    def _row_to_chunk(self, row) -> Chunk:
        loc = ChunkLocation.from_dict(json.loads(row['location_json']))
        return Chunk(id=row['id'], file_id=row['file_id'], text=row['text'],
                     location=loc, parent_chunk_id=row['parent_chunk_id'])

    def close(self):
        self.conn.close()

# --------------------- Ingestor ---------------------
class FileIngestor:
    """Processes files into chunks and stores them with metadata."""

    def __init__(self, store: ContentStore):
        self.store = store

    def ingest(self, file_path: str) -> int:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        file_type = self._detect_type(path)
        meta = self._extract_metadata(path, file_type)
        file_id = self.store.add_file(str(path.resolve()), file_type, meta)
        # Remove old chunks and reprocess
        self.store.delete_file_chunks(file_id)
        text = self._extract_full_text(path, file_type)
        chunks = self._chunk_text(text, file_type, path)
        for i, chunk_text in enumerate(chunks):
            loc = self._make_location(path, file_type, i, chunk_text, chunks, text)
            self.store.add_chunk(file_id, chunk_text, loc)
        return file_id

    def _detect_type(self, path: Path) -> FileType:
        suffix = path.suffix.lower()
        if suffix in ('.txt',):
            return FileType.TEXT
        if suffix in ('.md', '.markdown'):
            return FileType.MARKDOWN
        if suffix == '.pdf':
            return FileType.PDF
        if suffix == '.docx':
            return FileType.DOCX
        if suffix in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'):
            return FileType.IMAGE
        if suffix in ('.xlsx', '.xls', '.ods', '.csv'):
            return FileType.SPREADSHEET
        if suffix in ('.log',):
            return FileType.LOG
        if suffix in ('.zip', '.tar', '.gz', '.bz2'):
            return FileType.ARCHIVE
        # Default to text if small, else unknown
        try:
            with open(path, 'r', encoding='utf-8') as f:
                f.read(1024)
            return FileType.TEXT
        except:
            return FileType.UNKNOWN

    def _extract_metadata(self, path: Path, file_type: FileType) -> Optional[DocumentMeta]:
        stat = path.stat()
        meta = DocumentMeta(
            file_path=str(path.resolve()),
            title=path.stem,
            created_date=datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified_date=datetime.fromtimestamp(stat.st_mtime).isoformat()
        )
        # Try to read frontmatter from markdown
        if file_type in (FileType.MARKDOWN,):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line == '---':
                        lines = []
                        for line in f:
                            if line.strip() == '---':
                                break
                            lines.append(line)
                        front = {}
                        for line in lines:
                            if ':' in line:
                                k, v = line.split(':', 1)
                                front[k.strip()] = v.strip()
                        meta.title = front.get('title', meta.title)
                        meta.tags = [t.strip() for t in front.get('tags', '').split(',') if t.strip()]
                        meta.author = front.get('author', meta.author)
                        meta.description = front.get('description', meta.description)
                        meta.custom.update({k: v for k, v in front.items() if k not in ('title', 'tags', 'author', 'description')})
            except Exception:
                pass
        return meta

    def _extract_full_text(self, path: Path, file_type: FileType) -> str:
        if file_type == FileType.TEXT or file_type == FileType.MARKDOWN or file_type == FileType.LOG:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        elif file_type == FileType.PDF:
            if PyPDF2 is None:
                raise ImportError("PyPDF2 required for PDF ingestion")
            reader = PyPDF2.PdfReader(str(path))
            return "\n".join([page.extract_text() or "" for page in reader.pages])
        elif file_type == FileType.DOCX:
            if Document is None:
                raise ImportError("python-docx required for DOCX ingestion")
            doc = Document(str(path))
            return "\n".join([para.text for para in doc.paragraphs])
        elif file_type == FileType.SPREADSHEET:
            if openpyxl is None:
                raise ImportError("openpyxl required for spreadsheet ingestion")
            wb = openpyxl.load_workbook(str(path), data_only=True)
            text = []
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                text.append(f"--- Sheet: {sheet_name} ---")
                for row in ws.iter_rows(values_only=True):
                    row_text = "\t".join([str(cell) if cell is not None else "" for cell in row])
                    text.append(row_text)
            return "\n".join(text)
        elif file_type == FileType.IMAGE:
            # No textual content extraction by default
            return ""
        elif file_type == FileType.ARCHIVE:
            # For archives, we would need extraction; return placeholder
            return f"[Archive: {path.name}]"
        elif file_type == FileType.UNKNOWN:
            # Try as binary, base64 encode? Not useful.
            return ""
        else:
            return ""

    def _chunk_text(self, text: str, file_type: FileType, path: Path) -> List[str]:
        """Simple chunking by paragraphs or fixed size."""
        if not text.strip():
            return []
        if file_type == FileType.SPREADSHEET:
            # Keep sheets as separate chunks
            return [text]  # already includes sheet markers
        # Default: split by double newline for paragraph chunks, then merge small ones
        raw = [p.strip() for p in text.split('\n\n') if p.strip()]
        chunks = []
        buffer = ""
        for para in raw:
            if len(buffer) + len(para) > 1000:
                if buffer:
                    chunks.append(buffer)
                buffer = para
            else:
                if buffer:
                    buffer += "\n\n" + para
                else:
                    buffer = para
        if buffer:
            chunks.append(buffer)
        # Ensure no empty chunks
        return [c for c in chunks if c.strip()]

    def _make_location(self, path: Path, file_type: FileType, chunk_idx: int,
                       chunk_text: str, chunks: List[str], full_text: str) -> ChunkLocation:
        """Generate location based on chunk position for later window retrieval."""
        if file_type in (FileType.TEXT, FileType.MARKDOWN, FileType.LOG):
            # Use line numbers
            lines = full_text.splitlines()
            start_line = 0
            if chunk_idx > 0:
                prev_text = '\n\n'.join(chunks[:chunk_idx])
                start_line = prev_text.count('\n') + 1 if prev_text else 0
            end_line = start_line + chunk_text.count('\n')
            # Ensure within bounds
            return ChunkLocation(
                file_path=str(path),
                file_type=file_type,
                start_line=start_line,
                end_line=min(end_line, len(lines)-1)
            )
        elif file_type == FileType.PDF:
            # Assign page based on chunk index; simplified: chunk_idx corresponds to page
            return ChunkLocation(
                file_path=str(path),
                file_type=file_type,
                page=chunk_idx  # assuming each chunk is a page
            )
        elif file_type == FileType.DOCX:
            # map paragraph ranges based on chunk index; we'll use chunk index as start
            return ChunkLocation(
                file_path=str(path),
                file_type=file_type,
                start_para=chunk_idx,
                end_para=chunk_idx
            )
        elif file_type == FileType.SPREADSHEET:
            return ChunkLocation(
                file_path=str(path),
                file_type=file_type,
                sheet="all"  # since we concatenated all sheets
            )
        else:
            return ChunkLocation(file_path=str(path), file_type=file_type)

# --------------------- Search Engine ---------------------
class SearchEngine:
    """Handles lexical search, optional embeddings, reranking, and source quotas."""

    def __init__(self, store: ContentStore,
                 use_embeddings: bool = False,
                 embedding_model_name: str = 'all-MiniLM-L6-v2',
                 reranker_model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        self.store = store
        self.use_embeddings = use_embeddings
        self.embedding_model = None
        self.reranker = None
        if use_embeddings:
            if SentenceTransformer is None:
                raise ImportError("sentence-transformers required for embeddings")
            self.embedding_model = SentenceTransformer(embedding_model_name)
        if reranker_model_name and CrossEncoder is not None:
            self.reranker = CrossEncoder(reranker_model_name)
        # Initialize vector similarity threshold
        self.vector_cache = {}  # chunk_id -> vector stored lazily

    def search(self,
               query: str,
               top_k: int = 10,
               lexical_weight: float = 0.5,
               source_quota: Optional[Dict[str, int]] = None,
               use_rerank: bool = True) -> List[SearchResult]:
        """Main search: combine lexical and optional embeddings, enforce quotas, rerank."""
        # Lexical via FTS5
        lexical_results = self._lexical_search(query, top_k)
        # Embedding search
        embedding_results = []
        if self.use_embeddings:
            embedding_results = self._embedding_search(query, top_k)
        # Merge scores
        combined = self._merge_results(lexical_results, embedding_results, lexical_weight)
        # Apply source quota
        if source_quota:
            combined = self._apply_source_quota(combined, source_quota)
        # Rerank top candidates
        if use_rerank and self.reranker and combined:
            combined = self._rerank(query, combined[:top_k*2])  # rerank larger pool
        # Return top-k
        return combined[:top_k]

    def _lexical_search(self, query: str, top_k: int) -> List[Tuple[Chunk, float]]:
        # FTS5 query; use MATCH and return scores based on rank
        # SQLite FTS5 doesn't give a score directly in basic mode; we'll use bm25() extension if available.
        # Simpler: we'll use MATCH with bm25 or rank, but for simplicity, we'll use rowid ordering.
        # Actual implementation: we can use 'WHERE chunks_fts MATCH ? ORDER BY rank' after enabling rank.
        # We'll create a scoring: use `bm25()` function if built.
        # For portability, we'll implement a simplistic: fetch all match and score by length of match? Not great.
        # Better: use `rank` column with INSERT rank. We'll just try ORDER BY rank; if fails, fallback.
        try:
            # Attempt to use rank built-in (requires enabling rank during FTS5 creation)
            cur = self.store.conn.execute(
                "SELECT c.*, rank FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid "
                "WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?",
                (query, top_k))
            results = []
            for row in cur.fetchall():
                chunk = self.store._row_to_chunk(row)
                rank = row['rank']
                # Convert rank to score (higher is better, but rank is usually negative? We'll invert)
                score = -rank if rank is not None else 0.0
                results.append((chunk, score))
            return results
        except sqlite3.OperationalError:
            # Fallback to no ordering; just use limit
            cur = self.store.conn.execute(
                "SELECT c.* FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid "
                "WHERE chunks_fts MATCH ? LIMIT ?",
                (query, top_k))
            return [(self.store._row_to_chunk(row), 1.0) for row in cur.fetchall()]

    def _embedding_search(self, query: str, top_k: int) -> List[Tuple[Chunk, float]]:
        if not self.embedding_model:
            return []
        query_vec = self.embedding_model.encode(query).astype(np.float32)
        # Load all vectors (simplistic for local scale; real implementation would index)
        all_vectors = {}
        rows = self.store.conn.execute("SELECT v.chunk_id, v.vector FROM vectors v").fetchall()
        for row in rows:
            vec = np.frombuffer(row['vector'], dtype=np.float32)
            all_vectors[row['chunk_id']] = vec
        # Compute cosine similarities
        similarities = {}
        for chunk_id, vec in all_vectors.items():
            sim = np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec) + 1e-9)
            similarities[chunk_id] = sim
        # Get top-k chunks
        sorted_ids = sorted(similarities, key=similarities.get, reverse=True)[:top_k]
        results = []
        for cid in sorted_ids:
            row = self.store.conn.execute("SELECT * FROM chunks WHERE id=?", (cid,)).fetchone()
            if row:
                chunk = self.store._row_to_chunk(row)
                results.append((chunk, similarities[cid]))
        return results

    def _merge_results(self, lexical: List[Tuple[Chunk, float]], embedding: List[Tuple[Chunk, float]],
                       lexical_weight: float) -> List[SearchResult]:
        # Normalize both sets of scores to 0-1 (min-max)
        def normalize(scores):
            if not scores:
                return {}
            max_s = max(scores)
            min_s = min(scores)
            if max_s == min_s:
                return {id_: 0.5 for id_ in scores}
            return {id_: (s - min_s) / (max_s - min_s) for id_, s in scores.items()}
        lex_scores = {c.id: s for c, s in lexical}
        emb_scores = {c.id: s for c, s in embedding}
        all_ids = set(lex_scores.keys()) | set(emb_scores.keys())
        norm_lex = normalize(lex_scores)
        norm_emb = normalize(emb_scores)
        combined = {}
        for id_ in all_ids:
            l = norm_lex.get(id_, 0.0)
            e = norm_emb.get(id_, 0.0)
            combined[id_] = lexical_weight * l + (1 - lexical_weight) * e
        # Build SearchResult list
        chunk_map = {}
        for c, _ in lexical:
            chunk_map[c.id] = c
        for c, _ in embedding:
            chunk_map[c.id] = c
        results = []
        for id_, score in combined.items():
            c = chunk_map[id_]
            # source is file path
            source = c.location.file_path
            results.append(SearchResult(chunk=c, score=score, source=source))
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _apply_source_quota(self, results: List[SearchResult], quota: Dict[str, int]) -> List[SearchResult]:
        # quota: max number per source (file path or parent folder). We'll implement per file.
        counts = defaultdict(int)
        filtered = []
        for res in results:
            src = res.source
            if src in quota and counts[src] >= quota[src]:
                continue
            counts[src] += 1
            filtered.append(res)
        return filtered

    def _rerank(self, query: str, candidates: List[SearchResult]) -> List[SearchResult]:
        if not candidates:
            return candidates
        pairs = [(query, c.chunk.text) for c in candidates]
        scores = self.reranker.predict(pairs)
        for res, score in zip(candidates, scores):
            res.score = float(score)
        candidates.sort(key=lambda r: r.score, reverse=True)
        return candidates

    def generate_embeddings_for_chunks(self, chunk_ids: List[int]):
        """Encode chunks and store vectors."""
        if not self.embedding_model:
            return
        for cid in chunk_ids:
            row = self.store.conn.execute("SELECT text FROM chunks WHERE id=?", (cid,)).fetchone()
            if row:
                vec = self.embedding_model.encode(row['text'])
                self.store.add_vector(cid, vec)

    def index_all_vectors(self):
        """Generate embeddings for all chunks."""
        all_ids = [r['id'] for r in self.store.conn.execute("SELECT id FROM chunks").fetchall()]
        self.generate_embeddings_for_chunks(all_ids)

# --------------------- File Reader ---------------------
class FileReader:
    """Reads original files and extracts text windows based on chunk location."""

    def read_window(self, chunk: Chunk, context_lines: int = 2) -> str:
        """Read the original file and return context around chunk."""
        loc = chunk.location
        path = Path(loc.file_path)
        if not path.exists():
            return "[File not found]"
        try:
            if loc.file_type in (FileType.TEXT, FileType.MARKDOWN, FileType.LOG):
                return self._read_text_window(path, loc, context_lines)
            elif loc.file_type == FileType.PDF:
                return self._read_pdf_page(path, loc)
            elif loc.file_type == FileType.DOCX:
                return self._read_docx_window(path, loc, context_lines)
            elif loc.file_type == FileType.SPREADSHEET:
                return self._read_spreadsheet_window(path, loc)
            elif loc.file_type == FileType.ARCHIVE:
                return self._read_archive_member(path, loc)
            else:
                return self._read_full_text(path)
        except Exception as e:
            return f"[Error reading window: {e}]"

    def _read_text_window(self, path: Path, loc: ChunkLocation, context: int) -> str:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        start = max(0, (loc.start_line or 0) - context)
        end = min(len(lines), (loc.end_line or 0) + context + 1)
        return ''.join(lines[start:end])

    def _read_pdf_page(self, path: Path, loc: ChunkLocation) -> str:
        if PyPDF2 is None:
            return "[PDF reader not available]"
        reader = PyPDF2.PdfReader(str(path))
        page_num = loc.page if loc.page is not None and 0 <= loc.page < len(reader.pages) else 0
        return reader.pages[page_num].extract_text() or ""

    def _read_docx_window(self, path: Path, loc: ChunkLocation, context: int) -> str:
        if Document is None:
            return "[DOCX reader not available]"
        doc = Document(str(path))
        paras = doc.paragraphs
        start = max(0, (loc.start_para or 0) - context)
        end = min(len(paras), (loc.end_para or 0) + context + 1)
        return "\n".join(p.text for p in paras[start:end])

    def _read_spreadsheet_window(self, path: Path, loc: ChunkLocation) -> str:
        """Read the sheet and possibly a range; simplified to full sheet if specified."""
        # Since we stored 'all' sheet, just return full text.
        return self._extract_full_spreadsheet(path)

    def _extract_full_spreadsheet(self, path: Path) -> str:
        if openpyxl is None:
            return "[Spreadsheet reader not available]"
        wb = openpyxl.load_workbook(str(path), data_only=True)
        parts = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            parts.append(f"--- Sheet: {sheet_name} ---")
            for row in ws.iter_rows(values_only=True):
                parts.append("\t".join([str(cell) if cell is not None else "" for cell in row]))
        return "\n".join(parts)

    def _read_archive_member(self, path: Path, loc: ChunkLocation) -> str:
        # Could use zipfile/tarfile to extract member. Simplified.
        return f"[Archive content for member {loc.member}]"

    def _read_full_text(self, path: Path) -> str:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

# --------------------- Agent ---------------------
class MarginaliaAgent:
    """LLM-powered agent that answers questions with citations."""

    def __init__(self, search_engine: SearchEngine, reader: FileReader,
                 notes_manager, llm_client=None):
        self.search = search_engine
        self.reader = reader
        self.notes = notes_manager
        self.llm = llm_client or self._default_llm

    def _default_llm(self, prompt: str) -> str:
        """Fallback LLM interface - override with actual API."""
        # Placeholder: use some local model or print prompt
        print("LLM prompt:\n" + prompt)
        return "This is a placeholder answer with no real citations."

    def answer(self,
               question: str,
               max_sources: int = 5,
               context_window: int = 4,
               write_note: bool = True) -> str:
        """Answer question with citations."""
        # 1. Retrieve candidates
        results = self.search.search(question, top_k=max_sources)
        if not results:
            return "No relevant sources found."
        # 2. Read windows
        windows = []
        sources = []
        for i, res in enumerate(results):
            window_text = self.reader.read_window(res.chunk, context_lines=context_window)
            source_ref = f"[{i+1}] {res.source}"
            windows.append(f"{source_ref}\n{window_text}")
            sources.append(source_ref)
        # 3. Build prompt
        context = "\n\n".join(windows)
        prompt = f"""You are a research assistant. Answer the question using ONLY the provided sources. Cite sources inline using numbers in brackets (e.g., [1]).

Sources:
{context}

Question: {question}
Answer (with citations):"""
        response = self.llm(prompt)
        # 4. Optionally write investigation note
        if write_note:
            self.notes.add_note(question=question, answer=response, sources=[r.source for r in results])
        return response

    def generate_report(self, topic: str, max_sources: int = 10) -> str:
        """Generate a structured report with citations."""
        results = self.search.search(topic, top_k=max_sources)
        windows = []
        sources = []
        for i, res in enumerate(results):
            window_text = self.reader.read_window(res.chunk, context_lines=5)
            source_ref = f"[{i+1}] {res.source}"
            windows.append(f"{source_ref}\n{window_text}")
            sources.append(source_ref)
        context = "\n\n".join(windows)
        prompt = f"""You are a research assistant. Write a comprehensive report on the topic using ONLY the provided sources. Use inline citations ([1], [2], etc.) and produce a structured report with sections.

Sources:
{context}

Topic: {topic}
Report:"""
        response = self.llm(prompt)
        self.notes.add_report(topic=topic, content=response, sources=[r.source for r in results])
        return response

# --------------------- Notes Manager ---------------------
class NotesManager:
    """Stores durable investigation notes that can be recalled later."""

    def __init__(self, notes_dir: str, store: ContentStore):
        self.notes_dir = Path(notes_dir)
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.store = store
        # We'll also index notes as files for future search
        # Notes are stored as markdown files
        self.note_db_file = self.notes_dir / "_notes_index.json"
        self._load_index()

    def _load_index(self):
        if self.note_db_file.exists():
            with open(self.note_db_file, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = []

    def _save_index(self):
        with open(self.note_db_file, 'w') as f:
            json.dump(self.index, f, indent=2)

    def add_note(self, question: str, answer: str, sources: List[str]):
        note_id = len(self.index)
        timestamp = datetime.now().isoformat()
        note_data = {
            'id': note_id,
            'timestamp': timestamp,
            'type': 'question',
            'question': question,
            'answer': answer,
            'sources': sources
        }
        self.index.append(note_data)
        # Write markdown file
        filename = f"note_{note_id:04d}.md"
        content = f"# Investigation Note {note_id}\n\n"
        content += f"**Question:** {question}\n\n**Date:** {timestamp}\n\n"
        content += f"**Answer:**\n{answer}\n\n"
        content += "**Sources:**\n" + "\n".join(f"- {s}" for s in sources)
        (self.notes_dir / filename).write_text(content)
        self._save_index()

    def add_report(self, topic: str, content: str, sources: List[str]):
        note_id = len(self.index)
        timestamp = datetime.now().isoformat()
        note_data = {
            'id': note_id,
            'timestamp': timestamp,
            'type': 'report',
            'topic': topic,
            'content': content,
            'sources': sources
        }
        self.index.append(note_data)
        filename = f"report_{note_id:04d}.md"
        md = f"# Report: {topic}\n\n**Date:** {timestamp}\n\n{content}\n\n**Sources:**\n"
        md += "\n".join(f"- {s}" for s in sources)
        (self.notes_dir / filename).write_text(md)
        self._save_index()

    def get_recent_notes(self, limit=10):
        return self.index[-limit:]

# --------------------- Journals ---------------------
class JournalManager:
    """Manages daily journal entries as markdown files."""

    def __init__(self, journal_dir: str):
        self.dir = Path(journal_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def create_entry(self, content: str, date: Optional[str] = None):
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date}.md"
        filepath = self.dir / filename
        header = f"# Journal - {date}\n\n"
        with open(filepath, 'a') as f:
            f.write(header + content + "\n\n")
        return str(filepath)

    def get_entry(self, date: str) -> Optional[str]:
        filepath = self.dir / f"{date}.md"
        if filepath.exists():
            return filepath.read_text()
        return None

# --------------------- Catalog & Views ---------------------
class CatalogManager:
    """Manages saved search/tag queries as catalogs and views."""

    def __init__(self, store: ContentStore):
        self.store = store
        self.catalogs: Dict[str, Dict] = {}  # could persist to db

    def create_catalog(self, name: str, query: str, tags: List[str] = None):
        self.catalogs[name] = {'query': query, 'tags': tags or []}

    def get_catalog_items(self, name: str) -> List[str]:
        cat = self.catalogs.get(name)
        if not cat:
            return []
        # Search files by tags and query (simple)
        files = self.store.get_all_files()
        if cat['tags']:
            # filter by tags
            filtered = []
            for f in files:
                meta = self.store.get_file_meta(f)
                if meta and any(tag in meta.tags for tag in cat['tags']):
                    filtered.append(f)
            files = filtered
        if cat['query']:
            # rudimentary filename match
            files = [f for f in files if cat['query'].lower() in Path(f).name.lower()]
        return files

# --------------------- Relationship Mining ---------------------
class RelationMiner:
    """Finds connections between files based on shared tags, content similarity."""

    def __init__(self, store: ContentStore):
        self.store = store

    def find_related(self, file_path: str, max_relations: int = 5) -> List[str]:
        meta = self.store.get_file_meta(file_path)
        if not meta:
            return []
        # Simple relation by shared tags
        all_files = self.store.get_all_files()
        scores = defaultdict(float)
        for other in all_files:
            if other == file_path:
                continue
            other_meta = self.store.get_file_meta(other)
            if not other_meta:
                continue
            common = set(meta.tags).intersection(set(other_meta.tags))
            if common:
                scores[other] = len(common)
        sorted_files = sorted(scores, key=scores.get, reverse=True)[:max_relations]
        return sorted_files

# --------------------- Main Marginalia Library ---------------------
class MarginaliaLibrary:
    """Central library manager."""

    def __init__(self, root_path: str, use_embeddings: bool = False):
        self.root = Path(root_path).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        # Subdirectories
        self.data_dir = self.root / ".marginalia"
        self.data_dir.mkdir(exist_ok=True)
        db_path = str(self.data_dir / "library.db")
        self.store = ContentStore(db_path)
        self.ingestor = FileIngestor(self.store)
        self.search_engine = SearchEngine(self.store, use_embeddings=use_embeddings)
        self.reader = FileReader()
        self.notes = NotesManager(str(self.root / "notes"), self.store)
        self.journal = JournalManager(str(self.root / "journal"))
        self.catalog = CatalogManager(self.store)
        self.relation_miner = RelationMiner(self.store)

        # Agent initialization (LLM client could be passed externally)
        self.agent = MarginaliaAgent(self.search_engine, self.reader, self.notes)

    def ingest_file(self, file_path: str):
        abs_path = str(Path(file_path).resolve())
        file_id = self.ingestor.ingest(abs_path)
        # Optionally generate embeddings for new file's chunks
        if self.search_engine.use_embeddings:
            chunks = self.store.get_chunks_for_file(file_id)
            self.search_engine.generate_embeddings_for_chunks([c.id for c in chunks])
        logger.info(f"Ingested {file_path} with id {file_id}")

    def search(self, query: str, top_k=10, **kwargs):
        return self.search_engine.search(query, top_k=top_k, **kwargs)

    def answer(self, question: str, **kwargs):
        return self.agent.answer(question, **kwargs)

    def generate_report(self, topic: str):
        return self.agent.generate_report(topic)

    def add_journal_entry(self, content: str, date=None):
        return self.journal.create_entry(content, date)

    def list_files(self):
        return self.store.get_all_files()

    def close(self):
        self.store.close()

# --------------------- Example usage ---------------------
if __name__ == "__main__":
    # Initialize with a test directory
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        lib = MarginaliaLibrary(tmpdir)
        # Create some test files
        test_file = Path(tmpdir) / "test_note.txt"
        test_file.write_text("This is the first line.\nThis is the second line.\nThird line of note.")
        lib.ingest_file(str(test_file))
        # Search
        results = lib.search("first line")
        for r in results:
            print(f"Score: {r.score:.2f}, Source: {r.source}, Snippet: {r.chunk.text[:50]}...")
        # Answer
        answer = lib.answer("What is the first line?")
        print("Answer:", answer)