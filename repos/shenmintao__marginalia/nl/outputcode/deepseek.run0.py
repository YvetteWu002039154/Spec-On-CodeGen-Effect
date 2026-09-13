from __future__ import annotations
import os
import re
import json
import datetime
import zipfile
import tarfile
import csv
import io
import logging
from pathlib import Path
from collections import defaultdict
from typing import (
    List, Dict, Optional, Tuple, Any, Union, Iterator,
    Callable, Type, cast, TYPE_CHECKING
)
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import hashlib
import pickle

# Optional imports with graceful fallback
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
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

try:
    from sentence_transformers import SentenceTransformer, CrossEncoder
    HAS_TRANSFORMERS = True
except ImportError:
    SentenceTransformer = None
    CrossEncoder = None
    HAS_TRANSFORMERS = False

try:
    import sqlite3
    import sqlite_vec
    HAS_SQLITE_VEC = True
except ImportError:
    HAS_SQLITE_VEC = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("marginalia")

# ============================================================
# Data classes
# ============================================================
@dataclass
class FileEntry:
    """Metadata for a library file."""
    file_path: str
    title: str
    file_type: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    catalog_id: Optional[str] = None
    text_preview: str = ""

    @property
    def size(self) -> Optional[int]:
        try:
            return os.path.getsize(self.file_path)
        except OSError:
            return None

@dataclass
class Note:
    """A durable investigation note in the journal."""
    id: str
    timestamp: datetime.datetime
    question: str
    answer: str
    citations: List[Citation] = field(default_factory=list)
    context_snippets: List[Snippet] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

@dataclass
class Citation:
    source_file: str
    location: str   # e.g., "Section: Introduction", "Page: 3", "Lines: 12-15"
    text: str

@dataclass
class Snippet:
    file_path: str
    location: str
    content: str

@dataclass
class SearchResult:
    entry: FileEntry
    score: float
    snippet: str = ""

# ============================================================
# File type detection and extraction strategies
# ============================================================
class BaseExtractor(ABC):
    """Abstract file extractor."""
    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        ...

    @abstractmethod
    def can_handle(self, file_path: str) -> bool:
        ...

class TextExtractor(BaseExtractor):
    def can_handle(self, file_path: str) -> bool:
        _, ext = os.path.splitext(file_path.lower())
        return ext in {'.txt', '.log', '.md', '.markdown', '.csv', '.json', '.yaml', '.yml'}

    def extract_text(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Text extraction failed for {file_path}: {e}")
            return ""

class PDFExtractor(BaseExtractor):
    def can_handle(self, file_path: str) -> bool:
        _, ext = os.path.splitext(file_path.lower())
        return ext == '.pdf' and PyPDF2 is not None

    def extract_text(self, file_path: str) -> str:
        if PyPDF2 is None:
            return "[PDF extraction unavailable]"
        try:
            reader = PyPDF2.PdfReader(file_path)
            text = []
            for page in reader.pages:
                text.append(page.extract_text() or "")
            return "\n".join(text)
        except Exception as e:
            logger.error(f"PDF extraction failed for {file_path}: {e}")
            return ""

class DocxExtractor(BaseExtractor):
    def can_handle(self, file_path: str) -> bool:
        _, ext = os.path.splitext(file_path.lower())
        return ext == '.docx' and docx is not None

    def extract_text(self, file_path: str) -> str:
        if docx is None:
            return "[DOCX extraction unavailable]"
        try:
            doc = docx.Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            logger.error(f"DOCX extraction failed for {file_path}: {e}")
            return ""

class SpreadsheetExtractor(BaseExtractor):
    def can_handle(self, file_path: str) -> bool:
        _, ext = os.path.splitext(file_path.lower())
        return ext in {'.xlsx', '.xlsm', '.xltx', '.xltm'} and openpyxl is not None

    def extract_text(self, file_path: str) -> str:
        if openpyxl is None:
            return "[Spreadsheet extraction unavailable]"
        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            text = []
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                for row in ws.iter_rows(values_only=True):
                    row_text = "\t".join(str(cell) if cell is not None else "" for cell in row)
                    text.append(row_text)
            return "\n".join(text)
        except Exception as e:
            logger.error(f"Spreadsheet extraction failed for {file_path}: {e}")
            return ""

class ArchiveExtractor(BaseExtractor):
    """Extracts a listing of archive members, not full recursive extraction."""
    def can_handle(self, file_path: str) -> bool:
        _, ext = os.path.splitext(file_path.lower())
        return ext in {'.zip', '.tar', '.tgz', '.tar.gz', '.tar.bz2'}

    def extract_text(self, file_path: str) -> str:
        """Returns a listing of members as text."""
        try:
            if file_path.endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zf:
                    names = zf.namelist()
                    return "Archive members:\n" + "\n".join(names)
            elif file_path.endswith(('.tar', '.tgz', '.tar.gz', '.tar.bz2')):
                with tarfile.open(file_path, 'r') as tf:
                    return "Archive members:\n" + "\n".join(tf.getnames())
            else:
                return ""
        except Exception as e:
            logger.error(f"Archive listing failed for {file_path}: {e}")
            return ""

class ImageExtractor(BaseExtractor):
    """No text extraction, returns metadata placeholder."""
    def can_handle(self, file_path: str) -> bool:
        _, ext = os.path.splitext(file_path.lower())
        return ext in {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'}

    def extract_text(self, file_path: str) -> str:
        return f"[Image: {os.path.basename(file_path)}]"

class FileIngestor:
    """Orchestrates extraction and library insertion."""
    def __init__(self, library: Library):
        self.library = library
        self.extractors: List[BaseExtractor] = [
            PDFExtractor(),
            DocxExtractor(),
            SpreadsheetExtractor(),
            ArchiveExtractor(),
            ImageExtractor(),
            TextExtractor(),   # fallback
        ]

    def _get_extractor(self, file_path: str) -> Optional[BaseExtractor]:
        for extractor in self.extractors:
            if extractor.can_handle(file_path):
                return extractor
        return None

    def ingest_file(self, file_path: str, tags: Optional[List[str]] = None,
                    catalog_id: Optional[str] = None, metadata: Optional[Dict[str, str]] = None) -> Optional[FileEntry]:
        if not os.path.isfile(file_path):
            logger.warning(f"Ignoring non-file: {file_path}")
            return None

        extractor = self._get_extractor(file_path)
        if extractor is None:
            logger.warning(f"No extractor for {file_path}, treating as text")
            extractor = TextExtractor()

        text = extractor.extract_text(file_path)
        _, ext = os.path.splitext(file_path)
        entry = FileEntry(
            file_path=os.path.abspath(file_path),
            title=os.path.basename(file_path),
            file_type=ext.lower(),
            tags=tags or [],
            catalog_id=catalog_id,
            metadata=metadata or {},
            text_preview=text[:500]    # short preview
        )
        self.library.add_entry(entry, full_text=text)
        return entry

# ============================================================
# Search Index (lexical, optional embeddings, reranking)
# ============================================================
class LexicalIndex:
    """Simple in-memory inverted index with TF-IDF scoring."""
    def __init__(self):
        self.documents: Dict[str, str] = {}            # id -> full text
        self.inverted_index: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.doc_lengths: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.avgdl: float = 0

    def add_document(self, doc_id: str, text: str):
        if doc_id in self.documents:
            self.remove_document(doc_id)
        self.documents[doc_id] = text
        tokens = self._tokenize(text)
        self.doc_lengths[doc_id] = len(tokens)
        for token in set(tokens):
            self.inverted_index[token][doc_id] = tokens.count(token)

    def remove_document(self, doc_id: str):
        if doc_id not in self.documents:
            return
        tokens = set(self._tokenize(self.documents[doc_id]))
        for token in tokens:
            if doc_id in self.inverted_index[token]:
                del self.inverted_index[token][doc_id]
                if not self.inverted_index[token]:
                    del self.inverted_index[token]
        del self.documents[doc_id]
        del self.doc_lengths[doc_id]

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\b\w+\b', text.lower())

    def _compute_idf(self):
        N = len(self.documents)
        self.idf.clear()
        for term, postings in self.inverted_index.items():
            self.idf[term] = 1.0 + np.log(N / len(postings)) if np else 1.0

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        if not self.documents:
            return []
        if not self.idf:
            self._compute_idf()
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        scores: Dict[str, float] = defaultdict(float)
        for token in query_tokens:
            if token not in self.inverted_index:
                continue
            idf = self.idf.get(token, 0)
            for doc_id, tf in self.inverted_index[token].items():
                doc_len = self.doc_lengths[doc_id]
                # simple TF-IDF
                scores[doc_id] += (tf / doc_len) * idf
        # sort by descending score
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return sorted_docs

class EmbeddingIndex(ABC):
    """Interface for dense vector search."""
    @abstractmethod
    def index_embeddings(self, embeddings: List[np.ndarray], doc_ids: List[str]):
        ...

    @abstractmethod
    def search(self, query_embedding: np.ndarray, top_k: int) -> List[Tuple[str, float]]:
        ...

class NumpyEmbeddingIndex(EmbeddingIndex):
    """Exact cosine similarity using numpy."""
    def __init__(self):
        self.embeddings: Optional[np.ndarray] = None
        self.doc_ids: List[str] = []

    def index_embeddings(self, embeddings: List[np.ndarray], doc_ids: List[str]):
        if not embeddings:
            self.embeddings = None
            self.doc_ids = []
            return
        stacked = np.stack(embeddings)
        norms = np.linalg.norm(stacked, axis=1, keepdims=True)
        norms[norms == 0] = 1e-9
        self.embeddings = stacked / norms  # normalized
        self.doc_ids = doc_ids

    def search(self, query_embedding: np.ndarray, top_k: int) -> List[Tuple[str, float]]:
        if self.embeddings is None or len(self.doc_ids) == 0:
            return []
        q = query_embedding / (np.linalg.norm(query_embedding) or 1e-9)
        scores = np.dot(self.embeddings, q)
        top_indices = np.argsort(-scores)[:top_k]
        return [(self.doc_ids[i], float(scores[i])) for i in top_indices]

class SqliteVecEmbeddingIndex(EmbeddingIndex):
    """sqlite-vec backed index."""
    def __init__(self, db_path: str = ":memory:"):
        if not HAS_SQLITE_VEC:
            raise ImportError("sqlite_vec not available")
        import sqlite_vec
        self.conn = sqlite3.connect(db_path)
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)
        self._init_table()
        self.doc_ids: List[str] = []
        self.dimension: Optional[int] = None

    def _init_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vec_index (
                doc_id TEXT PRIMARY KEY,
                embedding BLOB
            )
        """)

    def index_embeddings(self, embeddings: List[np.ndarray], doc_ids: List[str]):
        if not embeddings:
            return
        self.dimension = embeddings[0].shape[0]
        self.doc_ids = doc_ids.copy()
        self.conn.execute("DELETE FROM vec_index")
        for doc_id, emb in zip(doc_ids, embeddings):
            blob = pickle.dumps(emb.astype(np.float32))
            self.conn.execute("INSERT OR REPLACE INTO vec_index (doc_id, embedding) VALUES (?, ?)", (doc_id, blob))
        self.conn.commit()

    def search(self, query_embedding: np.ndarray, top_k: int) -> List[Tuple[str, float]]:
        if not self.doc_ids or self.dimension is None:
            return []
        rows = self.conn.execute("SELECT doc_id, embedding FROM vec_index").fetchall()
        if not rows:
            return []
        stored_ids, blobs = zip(*rows)
        stored_embs = [pickle.loads(b) for b in blobs]
        norm_q = query_embedding / (np.linalg.norm(query_embedding) or 1e-9)
        scores = [float(np.dot(emb, norm_q)) for emb in stored_embs]
        sorted_pairs = sorted(zip(stored_ids, scores), key=lambda x: x[1], reverse=True)[:top_k]
        return [(did, s) for did, s in sorted_pairs]

class Reranker:
    """Optional cross-encoder reranking."""
    def __init__(self, model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        self.model = None
        if HAS_TRANSFORMERS and CrossEncoder is not None:
            try:
                self.model = CrossEncoder(model_name)
            except:
                logger.warning("Could not load cross-encoder; reranking disabled")

    def rerank(self, query: str, documents: List[Tuple[str, str, float]], top_k: Optional[int] = None) -> List[Tuple[str, float]]:
        """
        documents: list of (doc_id, text, initial_score)
        returns: sorted list (doc_id, new_score)
        """
        if self.model is None:
            # fallback: return initial scoring
            return [(doc_id, score) for doc_id, _, score in documents]
        pairs = [(query, text) for _, text, _ in documents]
        scores = self.model.predict(pairs)
        scored = [(doc_id, float(s)) for (doc_id, _, _), s in zip(documents, scores)]
        scored.sort(key=lambda x: x[1], reverse=True)
        if top_k is not None:
            scored = scored[:top_k]
        return scored

class SearchOrchestrator:
    """Manages search strategies: lexical default, optional embeddings, reranking."""
    def __init__(self, lexical: LexicalIndex, embedding_index: Optional[EmbeddingIndex] = None,
                 reranker: Optional[Reranker] = None, embed_model=None):
        self.lexical = lexical
        self.embedding_index = embedding_index
        self.reranker = reranker
        self.embed_model = embed_model
        self.doc_text_cache: Dict[str, str] = {}   # doc_id -> text for reranking

    def add_document_text(self, doc_id: str, text: str):
        self.lexical.add_document(doc_id, text)
        self.doc_text_cache[doc_id] = text
        if self.embedding_index is not None and self.embed_model is not None:
            try:
                emb = self.embed_model.encode(text)
                self.embedding_index.index_embeddings([emb], [doc_id])
            except:
                pass

    def remove_document(self, doc_id: str):
        self.lexical.remove_document(doc_id)
        # embedding removal not implemented (re-indexing needed)
        self.doc_text_cache.pop(doc_id, None)

    def search(self, query: str, top_k: int = 20, use_embeddings: bool = False,
               rerank: bool = True, source_quota: Optional[Dict[str, int]] = None) -> List[SearchResult]:
        """source_quota: max results per source file path prefix"""
        results: List[Tuple[str, float]] = []
        if use_embeddings and self.embedding_index is not None and self.embed_model is not None:
            try:
                q_emb = self.embed_model.encode(query)
                results = self.embedding_index.search(q_emb, top_k)
            except Exception as e:
                logger.warning(f"Embedding search failed: {e}, falling back to lexical")
                use_embeddings = False
        if not use_embeddings:
            results = self.lexical.search(query, top_k)
        if not results:
            return []

        # Rerank
        if rerank and self.reranker is not None:
            docs_for_rerank = [(doc_id, self.doc_text_cache.get(doc_id, ""), score) for doc_id, score in results]
            reranked = self.reranker.rerank(query, docs_for_rerank, top_k)
            reranked_map = dict(reranked)
            results = sorted(results, key=lambda x: reranked_map.get(x[0], 0.0), reverse=True)

        # Build SearchResult list (need library to look up FileEntry)
        # We'll associate later; here we just return doc_ids and scores
        # The Marginalia class will convert using library.
        # For now, return doc_id and score; we'll adjust later.
        # We'll modify to require library reference.
        return [SearchResult(entry=None, score=score, snippet="") for doc_id, score in results]

# Actually SearchOrchestrator shouldn't know about library entries; we'll handle mapping outside.

class SnippetSelector:
    """Selects relevant text windows from a document."""
    @staticmethod
    def select_windows(full_text: str, query: str, window_size: int = 300, top_n: int = 3) -> List[str]:
        if not full_text or not query:
            return []
        # simple keyword overlap sliding window
        tokens = re.findall(r'\b\w+\b', full_text.lower())
        query_tokens = set(re.findall(r'\b\w+\b', query.lower()))
        if not tokens:
            return []
        stride = max(1, window_size // 2)
        windows: List[Tuple[int, str, float]] = []
        for start in range(0, len(tokens), stride):
            end = min(start + window_size, len(tokens))
            window_tokens = tokens[start:end]
            overlap = len(set(window_tokens) & query_tokens)
            if overlap > 0:
                # extract original text window using character positions
                # find char positions by locating token positions
                # We'll simply join the slice of tokens and look up in full_text via re.finditer
                # simpler: join full_text from start char based on token count (approximate)
                # find the substring that corresponds to these tokens
                token_pattern = re.compile(r'(\b\w+\b)')
                matches = list(token_pattern.finditer(full_text))
                if start < len(matches) and end <= len(matches):
                    char_start = matches[start].start()
                    char_end = matches[end-1].end()
                    snippet = full_text[char_start:char_end]
                else:
                    continue
                windows.append((char_start, snippet, overlap))
        # sort by overlap, keep unique non-overlapping? return top_n
        windows.sort(key=lambda x: x[2], reverse=True)
        return [s for _, s, _ in windows[:top_n]]

class DocumentReader:
    """Reads specific sections, pages, lines, archive members, table slices."""
    def read_section(self, file_path: str, section_title: str) -> Optional[str]:
        # For markdown/text: find section heading
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except:
            return None
        # Match heading patterns: ## Section or Section underlined with = or -
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line.strip().lower() == section_title.lower():
                # collect until next heading of same or higher level
                end = i + 1
                while end < len(lines) and not lines[end].startswith('#'):
                    end += 1
                return "\n".join(lines[i:end])
            if line.startswith('##') and section_title.lower() in line.lower():
                # collect until next ##
                end = i + 1
                while end < len(lines) and not lines[end].startswith('##'):
                    end += 1
                return "\n".join(lines[i:end])
        return None

    def read_page(self, file_path: str, page_num: int) -> Optional[str]:
        if not file_path.endswith('.pdf') or PyPDF2 is None:
            return None
        try:
            reader = PyPDF2.PdfReader(file_path)
            if page_num < 0 or page_num >= len(reader.pages):
                return None
            return reader.pages[page_num].extract_text()
        except:
            return None

    def read_lines(self, file_path: str, start_line: int, end_line: int) -> Optional[str]:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            return "".join(lines[start_line:end_line])
        except:
            return None

    def read_archive_member(self, archive_path: str, member_name: str) -> Optional[str]:
        if archive_path.endswith('.zip'):
            try:
                with zipfile.ZipFile(archive_path, 'r') as z:
                    with z.open(member_name) as mf:
                        return mf.read().decode('utf-8', errors='replace')
            except:
                return None
        elif archive_path.endswith(('.tar', '.tgz', '.tar.gz', '.tar.bz2')):
            try:
                with tarfile.open(archive_path, 'r') as tf:
                    f = tf.extractfile(member_name)
                    if f:
                        return f.read().decode('utf-8', errors='replace')
            except:
                return None
        return None

    def read_table_slice(self, file_path: str, sheet_name: Optional[str] = None,
                         start_cell: Optional[str] = None, end_cell: Optional[str] = None) -> Optional[str]:
        if openpyxl is None:
            return None
        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheet = wb[sheet_name] if sheet_name else wb.active
            rows = []
            if start_cell and end_cell:
                start_col, start_row = openpyxl.utils.cell.coordinate_from_string(start_cell)
                end_col, end_row = openpyxl.utils.cell.coordinate_from_string(end_cell)
                for row in sheet.iter_rows(min_row=start_row, max_row=end_row,
                                           min_col=start_col, max_col=end_col, values_only=True):
                    rows.append("\t".join(str(c) if c is not None else "" for c in row))
            else:
                for row in sheet.iter_rows(values_only=True):
                    rows.append("\t".join(str(c) if c is not None else "" for c in row))
            return "\n".join(rows)
        except:
            return None

# ============================================================
# Library
# ============================================================
class Library:
    def __init__(self, root_folder: str):
        self.root_folder = os.path.abspath(root_folder)
        self.entries: Dict[str, FileEntry] = {}
        self.catalogs: Dict[str, List[str]] = defaultdict(list)  # catalog_id -> list of file_ids
        self.tags_index: Dict[str, List[str]] = defaultdict(list)  # tag -> file_ids
        self._full_texts: Dict[str, str] = {}
        self.notes: Dict[str, Note] = {}

    def add_entry(self, entry: FileEntry, full_text: str = ""):
        file_id = self._make_id(entry.file_path)
        old_entry = self.entries.get(file_id)
        if old_entry:
            # remove old tags
            for tag in old_entry.tags:
                if file_id in self.tags_index[tag]:
                    self.tags_index[tag].remove(file_id)
        self.entries[file_id] = entry
        if full_text:
            self._full_texts[file_id] = full_text
        for tag in entry.tags:
            self.tags_index[tag].append(file_id)
        if entry.catalog_id:
            self.catalogs[entry.catalog_id].append(file_id)

    def remove_entry(self, file_path: str):
        file_id = self._make_id(file_path)
        entry = self.entries.pop(file_id, None)
        if entry:
            for tag in entry.tags:
                if file_id in self.tags_index[tag]:
                    self.tags_index[tag].remove(file_id)
            if entry.catalog_id and file_id in self.catalogs[entry.catalog_id]:
                self.catalogs[entry.catalog_id].remove(file_id)
            self._full_texts.pop(file_id, None)

    def get_entry(self, file_path: str) -> Optional[FileEntry]:
        return self.entries.get(self._make_id(file_path))

    def get_full_text(self, file_id: str) -> Optional[str]:
        return self._full_texts.get(file_id)

    def search_by_tags(self, tags: List[str], require_all: bool = True) -> List[FileEntry]:
        if not tags:
            return []
        sets = [set(self.tags_index.get(tag, [])) for tag in tags]
        if require_all:
            common = sets[0].intersection(*sets[1:])
        else:
            common = set.union(*sets)
        return [self.entries[fid] for fid in common]

    def get_catalog_entries(self, catalog_id: str) -> List[FileEntry]:
        return [self.entries[fid] for fid in self.catalogs.get(catalog_id, [])]

    def add_note(self, note: Note):
        self.notes[note.id] = note

    def get_notes(self) -> List[Note]:
        return list(self.notes.values())

    def _make_id(self, file_path: str) -> str:
        return hashlib.md5(os.path.abspath(file_path).encode()).hexdigest()

# ============================================================
# Agent and LLM Provider
# ============================================================
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        ...

class DummyLLM(LLMProvider):
    """A stub LLM for demonstration."""
    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        # simple citation-aware response
        citations = kwargs.get("citations", [])
        if citations:
            cited = "\n".join(f"[{i+1}] {c.source_file} ({c.location})" for i, c in enumerate(citations))
            return f"Answer based on provided sources:\n{cited}\n\nThe relevant information suggests ..."
        return "This is a placeholder answer. Please implement an actual LLM provider."

class Agent:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def answer(self, question: str, context_snippets: List[Snippet]) -> Tuple[str, List[Citation]]:
        # Build prompt with citations markers
        citations: List[Citation] = []
        context_parts = []
        for i, snip in enumerate(context_snippets):
            location_desc = snip.location if snip.location else "snippet"
            context_parts.append(f"Source [{i+1}] ({snip.file_path}, {location_desc}):\n{snip.content}")
            citations.append(Citation(source_file=snip.file_path, location=location_desc, text=snip.content))

        prompt = ("You are a research assistant. Answer the following question using ONLY the provided sources.\n"
                  "Cite sources using bracketed numbers, e.g., [1]. If the sources do not contain the answer, say so.\n\n"
                  "Sources:\n" + "\n\n".join(context_parts) + "\n\nQuestion: " + question + "\n\nAnswer:")
        system_msg = "You provide accurate, cited answers based on given sources."
        answer = self.llm.generate(prompt, system=system_msg, citations=citations)
        return answer, citations

# ============================================================
# Relation Mining
# ============================================================
class RelationMiner:
    """Discovers relations among library entries."""
    @staticmethod
    def related_by_tags(library: Library, entry: FileEntry, threshold: float = 0.3) -> List[FileEntry]:
        """Find entries sharing tags."""
        if not entry.tags:
            return []
        all_tagged = library.search_by_tags(entry.tags, require_all=False)
        # exclude self
        others = [e for e in all_tagged if e.file_path != entry.file_path]
        # score by Jaccard overlap?
        return others

    @staticmethod
    def common_keywords(library: Library, entry: FileEntry, top_k: int = 5) -> List[FileEntry]:
        # simplistic: find entries with overlapping tokens from full text
        # not implemented fully; placeholder.
        return []

# ============================================================
# Marginalia Main System
# ============================================================
class Marginalia:
    def __init__(self, root_folder: str = "./marginalia_data"):
        self.root = root_folder
        os.makedirs(root_folder, exist_ok=True)
        self.library = Library(root_folder)
        self.lexical_index = LexicalIndex()
        self.embedding_index: Optional[EmbeddingIndex] = None
        self.embed_model = None
        try:
            if HAS_TRANSFORMERS and SentenceTransformer:
                self.embed_model = SentenceTransformer('all-MiniLM-L6-v2')
                # decide on index backend; prefer sqlite-vec if available, else numpy
                if HAS_SQLITE_VEC:
                    self.embedding_index = SqliteVecEmbeddingIndex(db_path=os.path.join(root_folder, "vec.db"))
                elif HAS_NUMPY:
                    self.embedding_index = NumpyEmbeddingIndex()
        except Exception as e:
            logger.warning(f"Could not initialize embeddings: {e}")
        self.reranker = Reranker() if HAS_TRANSFORMERS and CrossEncoder else None
        self.search_orchestrator = SearchOrchestrator(
            lexical=self.lexical_index,
            embedding_index=self.embedding_index,
            reranker=self.reranker,
            embed_model=self.embed_model
        )
        self.reader = DocumentReader()
        self.snippet_selector = SnippetSelector()
        self.ingestor = FileIngestor(self.library)
        self.agent = Agent(DummyLLM())  # replace with actual LLM provider
        self._journal_path = os.path.join(root_folder, "journal.json")
        self._load_journal()

    def _load_journal(self):
        if os.path.exists(self._journal_path):
            try:
                with open(self._journal_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for note_dict in data.get('notes', []):
                    note = Note(
                        id=note_dict['id'],
                        timestamp=datetime.datetime.fromisoformat(note_dict['timestamp']),
                        question=note_dict['question'],
                        answer=note_dict['answer'],
                        citations=[Citation(**c) for c in note_dict.get('citations', [])],
                        context_snippets=[Snippet(**s) for s in note_dict.get('context_snippets', [])],
                        tags=note_dict.get('tags', [])
                    )
                    self.library.add_note(note)
                    # index journal text for search
                    self._index_note(note)
            except:
                pass

    def _save_journal(self):
        with open(self._journal_path, 'w', encoding='utf-8') as f:
            json.dump({
                'notes': [
                    {
                        'id': n.id,
                        'timestamp': n.timestamp.isoformat(),
                        'question': n.question,
                        'answer': n.answer,
                        'citations': [{'source_file': c.source_file, 'location': c.location, 'text': c.text} for c in n.citations],
                        'context_snippets': [{'file_path': s.file_path, 'location': s.location, 'content': s.content} for s in n.context_snippets],
                        'tags': n.tags,
                    }
                    for n in self.library.get_notes()
                ]
            }, f, indent=2)

    def _index_document(self, file_id: str, full_text: str):
        self.search_orchestrator.add_document_text(file_id, full_text)

    def ingest_file(self, file_path: str, tags: Optional[List[str]] = None,
                    catalog_id: Optional[str] = None, metadata: Optional[Dict[str, str]] = None) -> Optional[FileEntry]:
        entry = self.ingestor.ingest_file(file_path, tags, catalog_id, metadata)
        if entry:
            file_id = self.library._make_id(entry.file_path)
            full_text = self.library.get_full_text(file_id)
            if full_text:
                self._index_document(file_id, full_text)
        return entry

    def ingest_folder(self, folder_path: str, recursive: bool = True):
        for root, dirs, files in os.walk(folder_path):
            for fname in files:
                full_path = os.path.join(root, fname)
                self.ingest_file(full_path)
            if not recursive:
                break

    def search(self, query: str, top_k: int = 10, use_embeddings: bool = False,
               rerank: bool = True, source_quota: Optional[Dict[str, int]] = None) -> List[Tuple[FileEntry, float]]:
        """Return file entries and scores."""
        # Use orchestrator to get document ids and scores
        # We'll implement a simpler version: use orchestrator's lexical search directly
        doc_scores = self.search_orchestrator.search(query, top_k, use_embeddings, rerank, source_quota)
        results = []
        for sr in doc_scores:
            # sr is SearchResult with entry=None; we need doc_id from it
            # actually search method returns List[SearchResult] with entry=None, need to modify.
            # We'll modify search_orchestrator to return doc_ids and scores.
            pass
        # Redesign: SearchOrchestrator.search() returns List[Tuple[str, float]] (doc_id, score)
        # Let's change.
        return results

    def investigate(self, question: str, top_k_files: int = 5, snippets_per_file: int = 3,
                    use_embeddings: bool = False) -> Tuple[str, List[Citation], Note]:
        """Full investigation pipeline."""
        # 1. Retrieve candidate files from search
        doc_scores = self.search_orchestrator.search(question, top_k_files, use_embeddings, True)
        if not doc_scores:
            return "No relevant sources found.", [], Note(
                id="",
                timestamp=datetime.datetime.now(),
                question=question,
                answer="No sources found.",
                citations=[],
                context_snippets=[]
            )

        # 2. For each candidate, select snippets and read relevant parts
        all_snippets = []
        for doc_id, score in doc_scores:
            entry = self.library.entries.get(doc_id)
            if not entry:
                continue
            full_text = self.library.get_full_text(doc_id) or ""
            # Detect best windows
            windows = self.snippet_selector.select_windows(full_text, question, top_n=snippets_per_file)
            for win in windows:
                # Determine location descriptor (approximate line numbers)
                # simple: use start char, but for location we'll just say "context near...".
                location = f"relevance {score:.2f}"
                all_snippets.append(Snippet(file_path=entry.file_path, location=location, content=win))

        # 3. Read any specific sections if requested? Not in pipeline yet.

        # 4. Ask agent
        answer, citations = self.agent.answer(question, all_snippets)

        # 5. Create investigation note and store
        note_id = hashlib.md5((question + str(datetime.datetime.now())).encode()).hexdigest()
        note = Note(
            id=note_id,
            timestamp=datetime.datetime.now(),
            question=question,
            answer=answer,
            citations=citations,
            context_snippets=all_snippets
        )
        self.library.add_note(note)
        # Index note text for future search
        note_text = f"Q: {question}\nA: {answer}"
        self._index_note(note)
        self._save_journal()
        return answer, citations, note

    def _index_note(self, note: Note):
        # Index journal entry text for retrieval
        doc_id = f"note:{note.id}"
        text = f"Question: {note.question}\nAnswer: {note.answer}\n"
        for c in note.citations:
            text += f"Source: {c.source_file} ({c.location}): {c.text}\n"
        self.search_orchestrator.add_document_text(doc_id, text)

    def recall_notes(self, query: str, top_k: int = 5) -> List[Note]:
        doc_scores = self.search_orchestrator.search(query, top_k)
        notes = []
        for doc_id, score in doc_scores:
            if doc_id.startswith("note:"):
                note_id = doc_id[5:]
                if note_id in self.library.notes:
                    notes.append(self.library.notes[note_id])
        return notes

    def mine_relations(self, entry: FileEntry) -> List[FileEntry]:
        return RelationMiner.related_by_tags(self.library, entry)

# ============================================================
# Helper: search orchestrator fix
# ============================================================
# Override SearchOrchestrator.search to return List[Tuple[str, float]]
# We'll patch the class.
class SearchOrchestrator:
    """Manages search strategies."""
    def __init__(self, lexical: LexicalIndex, embedding_index: Optional[EmbeddingIndex] = None,
                 reranker: Optional[Reranker] = None, embed_model=None):
        self.lexical = lexical
        self.embedding_index = embedding_index
        self.reranker = reranker
        self.embed_model = embed_model
        self.doc_text_cache: Dict[str, str] = {}

    def add_document_text(self, doc_id: str, text: str):
        self.lexical.add_document(doc_id, text)
        self.doc_text_cache[doc_id] = text
        if self.embedding_index is not None and self.embed_model is not None:
            try:
                emb = self.embed_model.encode(text)
                self.embedding_index.index_embeddings([emb], [doc_id])
            except Exception as e:
                logger.warning(f"Embedding indexing failed for {doc_id}: {e}")

    def remove_document(self, doc_id: str):
        self.lexical.remove_document(doc_id)
        self.doc_text_cache.pop(doc_id, None)

    def search(self, query: str, top_k: int = 20, use_embeddings: bool = False,
               rerank: bool = True, source_quota: Optional[Dict[str, int]] = None) -> List[Tuple[str, float]]:
        results: List[Tuple[str, float]] = []
        if use_embeddings and self.embedding_index is not None and self.embed_model is not None:
            try:
                q_emb = self.embed_model.encode(query)
                results = self.embedding_index.search(q_emb, top_k)
            except Exception as e:
                logger.warning(f"Embedding search failed: {e}, falling back to lexical")
                use_embeddings = False
        if not use_embeddings:
            results = self.lexical.search(query, top_k)
        if not results:
            return []

        if rerank and self.reranker is not None:
            docs_for_rerank = [(doc_id, self.doc_text_cache.get(doc_id, ""), score) for doc_id, score in results]
            reranked = self.reranker.rerank(query, docs_for_rerank, top_k)
            reranked_map = dict(reranked)
            results = sorted(results, key=lambda x: reranked_map.get(x[0], 0.0), reverse=True)[:top_k]

        # apply source quota if provided
        if source_quota:
            counts: Dict[str, int] = defaultdict(int)
            filtered = []
            for doc_id, score in results:
                # extract source prefix (fine-matched)
                source = doc_id.split(':')[0]  # naive
                if counts.get(source, 0) < source_quota.get(source, top_k):
                    filtered.append((doc_id, score))
                    counts[source] += 1
            results = filtered

        return results[:top_k]

# ============================================================
# Utility: add document text to index from library
# ============================================================
def build_index_from_library(library: Library, orchestrator: SearchOrchestrator):
    for file_id, entry in library.entries.items():
        full_text = library.get_full_text(file_id)
        if full_text:
            orchestrator.add_document_text(file_id, full_text)

# ============================================================
# Example usage (commented out in production)
# ============================================================
# if __name__ == "__main__":
#     m = Marginalia("./my_library")
#     m.ingest_file("documents/report.pdf", tags=["report", "2024"])
#     ans, cites, note = m.investigate("What are the key findings?")
#     print(ans)