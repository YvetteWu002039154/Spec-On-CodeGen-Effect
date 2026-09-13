from __future__ import annotations
import abc
import datetime
import json
import os
import re
import shutil
import sqlite3
import tarfile
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

# ---------------------------------------------------------------------------
# Data classes and enums (library-science inspired metadata)
# ---------------------------------------------------------------------------

@dataclass
class DocumentMetadata:
    """Core metadata for a document (Dublin Core-ish plus file details)."""
    title: Optional[str] = None
    creator: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None
    contributor: Optional[str] = None
    date: Optional[datetime.date] = None
    type: Optional[str] = None
    format: Optional[str] = None
    identifier: Optional[str] = None
    source: Optional[str] = None
    language: Optional[str] = None
    relation: Optional[str] = None
    coverage: Optional[str] = None
    rights: Optional[str] = None
    file_path: Path = field(default_factory=Path)
    file_size: int = 0
    last_modified: float = 0.0
    custom: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Section:
    """A chunk of documented content with references to original location."""
    content: str
    start_line: int = 0
    end_line: int = 0
    page_number: Optional[int] = None
    archive_member: Optional[str] = None
    table_slice: Optional[Tuple[int, int, int, int]] = None  # (row_start, col_start, row_end, col_end) 1-indexed

@dataclass
class InvestigationNote:
    """Durable note written by the agent after an investigation."""
    query: str
    answer: str
    citations: List[Citation]
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    tags: Set[str] = field(default_factory=set)
    folder: str = "inbox"

@dataclass
class Citation:
    """A citation linking to a portion of a document."""
    document_id: str
    section: Optional[Section] = None
    text_snippet: str = ""

# ---------------------------------------------------------------------------
# Ingestors (abstract + concrete for each file type)
# ---------------------------------------------------------------------------

class Ingestor(abc.ABC):
    """Base ingestor. Subclasses parse different file types into a Document."""
    @abc.abstractmethod
    def ingest(self, file_path: Path) -> Document:
        """Return a Document object with full text and extracted sections."""
        ...

class TextIngestor(Ingestor):
    def ingest(self, file_path: Path) -> Document:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        meta = DocumentMetadata(file_path=file_path, file_size=os.path.getsize(file_path),
                                last_modified=os.path.getmtime(file_path))
        sections = [Section(content=content, start_line=1, end_line=content.count('\n')+1)]
        return Document(doc_id=self._make_id(file_path), content=content, metadata=meta,
                       sections=sections, file_path=file_path)

    def _make_id(self, path: Path) -> str:
        return f"file:{path.absolute().as_posix()}"

class MarkdownIngestor(TextIngestor):
    pass

class PDFIngestor(Ingestor):
    def ingest(self, file_path: Path) -> Document:
        # Stub: attempt simple PyPDF2 or similar - here just read raw text if possible
        # For a runnable demo, treat as text using a fallback.
        return TextIngestor().ingest(file_path)  # fallback; real impl would use pdf parsing

class DOCXIngestor(Ingestor):
    def ingest(self, file_path: Path) -> Document:
        return TextIngestor().ingest(file_path)  # fallback

class ImageIngestor(Ingestor):
    def ingest(self, file_path: Path) -> Document:
        # OCR would be required; for now return placeholder.
        content = f"[Image content not available for text search: {file_path.name}]"
        meta = DocumentMetadata(file_path=file_path)
        sections = [Section(content=content, start_line=1, end_line=1)]
        return Document(doc_id=f"img:{file_path}", content=content, metadata=meta,
                       sections=sections, file_path=file_path)

class SpreadsheetIngestor(Ingestor):
    def ingest(self, file_path: Path) -> Document:
        # Stub: try to read with openpyxl or csv; fallback text
        content = f"[Spreadsheet data from {file_path.name}]"
        meta = DocumentMetadata(file_path=file_path)
        # actual parsing would yield table slices; here just full content
        sections = [Section(content=content, start_line=1, end_line=1)]
        return Document(doc_id=f"sheet:{file_path}", content=content, metadata=meta,
                       sections=sections, file_path=file_path)

class LogIngestor(TextIngestor):
    pass

class ArchiveIngestor(Ingestor):
    def ingest(self, file_path: Path) -> Document:
        # Extract member list and maybe concatenate text from text files inside.
        # For simplicity, we treat the archive as a container and list members.
        members = self._list_members(file_path)
        content = f"Archive: {file_path.name}\nMembers:\n" + "\n".join(members)
        meta = DocumentMetadata(file_path=file_path, file_size=os.path.getsize(file_path))
        sections = []
        # Attempt to read each text member as sub-sections
        for member in members:
            text = self._read_text_member(file_path, member)
            if text is not None:
                sec = Section(content=text, archive_member=member, start_line=1, end_line=text.count('\n')+1)
                sections.append(sec)
        # If no text members, include the listing as a section
        if not sections:
            sections.append(Section(content=content, start_line=1, end_line=1))
        return Document(doc_id=f"archive:{file_path}", content=content, metadata=meta,
                       sections=sections, file_path=file_path)

    def _list_members(self, file_path: Path) -> List[str]:
        if file_path.suffix.lower() in ('.zip', '.jar', '.epub'):
            with zipfile.ZipFile(file_path, 'r') as zf:
                return zf.namelist()
        elif file_path.suffix.lower() in ('.tar', '.gz', '.bz2', '.xz'):
            with tarfile.open(file_path, 'r:*') as tf:
                return [m.name for m in tf.getmembers()]
        else:
            return []

    def _read_text_member(self, file_path: Path, member: str) -> Optional[str]:
        try:
            if file_path.suffix.lower() in ('.zip',):
                with zipfile.ZipFile(file_path, 'r') as zf:
                    with zf.open(member) as f:
                        return f.read().decode('utf-8', errors='ignore')
            elif file_path.suffix.lower() in ('.tar', '.gz', '.bz2', '.xz'):
                with tarfile.open(file_path, 'r:*') as tf:
                    f = tf.extractfile(member)
                    if f:
                        return f.read().decode('utf-8', errors='ignore')
        except Exception:
            pass
        return None

# ---------------------------------------------------------------------------
# Document and Knowledge Base
# ---------------------------------------------------------------------------

class Document:
    """Represents a single ingested item with full text and segmented sections."""
    def __init__(self, doc_id: str, content: str, metadata: DocumentMetadata,
                 sections: List[Section], file_path: Path):
        self.id = doc_id
        self.content = content
        self.metadata = metadata
        self.sections = sections          # list of Section objects
        self.file_path = file_path
        self.tags: Set[str] = set()
        self.folders: Set[str] = set([str(file_path.parent)])
        self.custom_metadata: Dict[str, Any] = {}

    def add_tag(self, tag: str):
        self.tags.add(tag)

    def remove_tag(self, tag: str):
        self.tags.discard(tag)

    def add_to_folder(self, folder: str):
        self.folders.add(folder)

    def remove_from_folder(self, folder: str):
        self.folders.discard(folder)

class KnowledgeBase:
    """Central repository of all documents, providing CRUD, indexing, and search."""
    def __init__(self, db_path: Optional[Path] = None):
        self.documents: Dict[str, Document] = {}
        self.index: Dict[str, Set[str]] = defaultdict(set)  # term -> doc_ids (simple inverted index)
        self.embeddings_enabled = False
        self.vector_store: Any = None  # placeholder for sqlite-vec
        self.db_path = db_path
        self._init_db()

    # --------------------- CRUD ---------------------
    def add_document(self, doc: Document):
        self.documents[doc.id] = doc
        self._index_document(doc)

    def remove_document(self, doc_id: str):
        if doc_id in self.documents:
            doc = self.documents.pop(doc_id)
            self._remove_from_index(doc)

    def get_document(self, doc_id: str) -> Optional[Document]:
        return self.documents.get(doc_id)

    def list_all(self) -> List[Document]:
        return list(self.documents.values())

    # --------------------- Indexing ---------------------
    def _index_document(self, doc: Document):
        tokens = self._tokenize(doc.content)
        for token in tokens:
            self.index[token].add(doc.id)
        if self.embeddings_enabled and self.vector_store:
            self.vector_store.add(doc.id, self._compute_embedding(doc.content))

    def _remove_from_index(self, doc: Document):
        tokens = self._tokenize(doc.content)
        for token in tokens:
            if token in self.index:
                self.index[token].discard(doc.id)
                if not self.index[token]:
                    del self.index[token]
        if self.embeddings_enabled and self.vector_store:
            self.vector_store.remove(doc.id)

    def rebuild_index(self):
        self.index.clear()
        for doc in self.documents.values():
            self._index_document(doc)

    # --------------------- Search ---------------------
    def lexical_search(self, query: str, top_k: int = 10, source_quota: Optional[int] = None) -> List[Tuple[Document, float]]:
        query_tokens = self._tokenize(query)
        scores: Dict[str, float] = defaultdict(float)
        for token in query_tokens:
            for doc_id in self.index.get(token, set()):
                scores[doc_id] += 1.0
        # rank by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        docs = []
        for doc_id, score in ranked[:top_k]:
            doc = self.documents.get(doc_id)
            if doc:
                docs.append((doc, score))
        if source_quota:
            # apply per-folder or per-type quotas (demo: keep max source_quota from same parent folder)
            seen_folders: Dict[str, int] = defaultdict(int)
            quota_docs = []
            for d, s in docs:
                parent = str(d.file_path.parent)
                if seen_folders[parent] < source_quota:
                    quota_docs.append((d, s))
                    seen_folders[parent] += 1
            docs = quota_docs
        return docs

    def embedding_search(self, query: str, top_k: int = 10, rerank: bool = False) -> List[Tuple[Document, float]]:
        if not self.embeddings_enabled or not self.vector_store:
            return self.lexical_search(query, top_k)
        q_emb = self._compute_embedding(query)
        candidates = self.vector_store.search(q_emb, top_k * 2)
        if rerank:
            candidates = self._rerank(candidates, query)
        docs = [(self.documents[did], score) for did, score in candidates[:top_k] if did in self.documents]
        return docs

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\w+', text.lower())

    def _compute_embedding(self, text: str) -> List[float]:
        # placeholder: return random vector of 128 dimensions (use deterministic based on hash for reproducibility)
        import hashlib
        h = hashlib.md5(text.encode()).digest()
        vec = [float(b) / 255.0 for b in h[:128]]  # up to 128 dimensions
        return vec

    def _rerank(self, candidates: List[Tuple[str, float]], query: str) -> List[Tuple[str, float]]:
        # stub: reorder based on lexical boost
        lexical_hits = self.lexical_search(query, top_k=len(candidates))
        lexical_map = {doc.id: score for doc, score in lexical_hits}
        reranked = []
        for did, vec_score in candidates:
            lex_score = lexical_map.get(did, 0)
            final_score = vec_score * 0.7 + lex_score * 0.3
            reranked.append((did, final_score))
        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked

    # --------------------- Database persistence ---------------------
    def _init_db(self):
        if self.db_path:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''CREATE TABLE IF NOT EXISTS documents
                            (id TEXT PRIMARY KEY, path TEXT, content TEXT, metadata_json TEXT)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS tags (doc_id TEXT, tag TEXT)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS folders (doc_id TEXT, folder TEXT)''')
            conn.commit()
            conn.close()

    def save_to_db(self):
        if not self.db_path:
            return
        conn = sqlite3.connect(self.db_path)
        for doc in self.documents.values():
            meta_json = json.dumps(self._serialize_metadata(doc.metadata))
            conn.execute('INSERT OR REPLACE INTO documents VALUES (?,?,?,?)',
                         (doc.id, str(doc.file_path), doc.content, meta_json))
            for tag in doc.tags:
                conn.execute('INSERT OR REPLACE INTO tags VALUES (?,?)', (doc.id, tag))
            for folder in doc.folders:
                conn.execute('INSERT OR REPLACE INTO folders VALUES (?,?)', (doc.id, folder))
        conn.commit()
        conn.close()

    def load_from_db(self):
        if not self.db_path:
            return
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute('SELECT id, path, content, metadata_json FROM documents').fetchall()
        for row in rows:
            doc_id, path, content, meta_json = row
            meta = self._deserialize_metadata(json.loads(meta_json))
            doc = Document(doc_id=doc_id, content=content, metadata=meta,
                           sections=[], file_path=Path(path))  # sections not persisted in demo
            self.documents[doc_id] = doc
        tag_rows = conn.execute('SELECT doc_id, tag FROM tags').fetchall()
        for doc_id, tag in tag_rows:
            if doc_id in self.documents:
                self.documents[doc_id].tags.add(tag)
        folder_rows = conn.execute('SELECT doc_id, folder FROM folders').fetchall()
        for doc_id, folder in folder_rows:
            if doc_id in self.documents:
                self.documents[doc_id].folders.add(folder)
        conn.close()
        self.rebuild_index()

    def _serialize_metadata(self, meta: DocumentMetadata) -> Dict:
        return {
            'title': meta.title,
            'creator': meta.creator,
            'subject': meta.subject,
            'description': meta.description,
            'date': meta.date.isoformat() if meta.date else None,
            'type': meta.type,
            'format': meta.format,
            'identifier': meta.identifier,
            'source': meta.source,
            'language': meta.language,
            'file_path': str(meta.file_path),
            'file_size': meta.file_size,
            'last_modified': meta.last_modified,
            'custom': meta.custom
        }

    def _deserialize_metadata(self, data: Dict) -> DocumentMetadata:
        return DocumentMetadata(
            title=data.get('title'),
            creator=data.get('creator'),
            subject=data.get('subject'),
            description=data.get('description'),
            date=datetime.date.fromisoformat(data['date']) if data.get('date') else None,
            type=data.get('type'),
            format=data.get('format'),
            identifier=data.get('identifier'),
            source=data.get('source'),
            language=data.get('language'),
            file_path=Path(data['file_path']),
            file_size=data['file_size'],
            last_modified=data['last_modified'],
            custom=data.get('custom', {})
        )

# ---------------------------------------------------------------------------
# Reader: extracts chosen windows from documents
# ---------------------------------------------------------------------------

class Reader:
    """Knows how to read specific sections, lines, pages, archive members, table slices."""
    def read_section(self, doc: Document, section_index: int) -> Optional[Section]:
        if 0 <= section_index < len(doc.sections):
            return doc.sections[section_index]
        return None

    def read_lines(self, doc: Document, start_line: int, end_line: int, section_index: int = 0) -> Optional[str]:
        if section_index >= len(doc.sections):
            return None
        sec = doc.sections[section_index]
        lines = sec.content.split('\n')
        if start_line < 1: start_line = 1
        if end_line > len(lines): end_line = len(lines)
        if start_line > end_line:
            return None
        return '\n'.join(lines[start_line-1:end_line])

    def read_page(self, doc: Document, page_number: int) -> Optional[str]:
        # For simplicity, we treat each section as a "page" if page_number is set
        for sec in doc.sections:
            if sec.page_number == page_number:
                return sec.content
        return None

    def read_archive_member(self, doc: Document, member_name: str) -> Optional[Section]:
        for sec in doc.sections:
            if sec.archive_member == member_name:
                return sec
        return None

    def read_table_slice(self, doc: Document, section_index: int,
                         row_start: int, col_start: int, row_end: int, col_end: int) -> Optional[str]:
        if section_index >= len(doc.sections):
            return None
        sec = doc.sections[section_index]
        lines = sec.content.split('\n')
        # assume CSV-like format in the section; simple slice
        if row_start < 1: row_start = 1
        if col_start < 1: col_start = 1
        sliced_lines = []
        for i in range(row_start-1, min(row_end, len(lines))):
            cols = lines[i].split(',')
            sliced_cols = cols[col_start-1:col_end]
            sliced_lines.append(','.join(sliced_cols))
        return '\n'.join(sliced_lines)

# ---------------------------------------------------------------------------
# Organizer: folders, tags, views, journals, relation mining
# ---------------------------------------------------------------------------

class Organizer:
    """Manages folders, tags, journals, views, and relation mining."""
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.views: Dict[str, List[str]] = defaultdict(list)  # view name -> list of doc_ids
        self.journals: Dict[str, Document] = {}  # journal name -> journal document
        self.relations: List[Tuple[str, str, str]] = []  # (source_id, target_id, relation_type)

    def assign_to_folder(self, doc_id: str, folder: str):
        doc = self.kb.get_document(doc_id)
        if doc:
            doc.add_to_folder(folder)

    def tag_document(self, doc_id: str, tag: str):
        doc = self.kb.get_document(doc_id)
        if doc:
            doc.add_tag(tag)

    def create_view(self, name: str, criteria: Dict[str, Any]):
        docs = self._filter_documents(criteria)
        self.views[name] = [doc.id for doc in docs]

    def query_view(self, name: str) -> List[Document]:
        ids = self.views.get(name, [])
        return [self.kb.get_document(did) for did in ids if self.kb.get_document(did)]

    def create_journal(self, name: str, initial_content: str = "") -> Document:
        jour = Document(doc_id=f"journal:{name}", content=initial_content,
                        metadata=DocumentMetadata(title=name), sections=[], file_path=Path("journals") / name)
        self.kb.add_document(jour)
        self.journals[name] = jour
        return jour

    def add_journal_entry(self, journal_name: str, entry: str, date: Optional[datetime.date] = None):
        if journal_name not in self.journals:
            self.create_journal(journal_name)
        jour = self.journals[journal_name]
        timestamp = datetime.datetime.now().isoformat()
        jour.content += f"\n\n[{timestamp}] {entry}"
        jour.sections = [Section(content=jour.content, start_line=1, end_line=jour.content.count('\n')+1)]

    def mine_relations(self):
        """Simple relation mining based on shared tags and folder proximity."""
        docs = self.kb.list_all()
        for i, doc_a in enumerate(docs):
            for doc_b in docs[i+1:]:
                if doc_a.tags & doc_b.tags:
                    self.relations.append((doc_a.id, doc_b.id, "shared_tags"))
                if doc_a.folders & doc_b.folders:
                    self.relations.append((doc_a.id, doc_b.id, "same_folder"))

    def get_related(self, doc_id: str, relation_type: Optional[str] = None) -> List[str]:
        result = set()
        for src, tgt, rtype in self.relations:
            if src == doc_id and (relation_type is None or rtype == relation_type):
                result.add(tgt)
            if tgt == doc_id and (relation_type is None or rtype == relation_type):
                result.add(src)
        return list(result)

    def _filter_documents(self, criteria: Dict[str, Any]) -> List[Document]:
        docs = self.kb.list_all()
        for key, value in criteria.items():
            if key == 'tag':
                docs = [d for d in docs if value in d.tags]
            elif key == 'folder':
                docs = [d for d in docs if value in d.folders]
            elif key == 'type':
                docs = [d for d in docs if d.metadata.type == value]
            elif key == 'title_contains':
                docs = [d for d in docs if value.lower() in (d.metadata.title or '')]
        return docs

# ---------------------------------------------------------------------------
# LLM Agent: uses reader, search, generates answers, writes notes
# ---------------------------------------------------------------------------

class LLMClient(abc.ABC):
    """Abstract LLM client. Implementations can call local or remote models."""
    @abc.abstractmethod
    def generate(self, prompt: str, context: str = "") -> str:
        ...

class MockLLMClient(LLMClient):
    """Simulates LLM responses for demonstration."""
    def generate(self, prompt: str, context: str = "") -> str:
        # Return a simple response citing the context length.
        return (f"Based on the provided context ({len(context)} chars), "
                f"I believe the answer is: [simulated answer]. Citations: ...")

class Agent:
    """The personal research agent that retrieves, reads, and answers."""
    def __init__(self, kb: KnowledgeBase, organizer: Organizer, reader: Reader,
                 llm: LLMClient, note_folder: Path = Path("notes")):
        self.kb = kb
        self.organizer = organizer
        self.reader = reader
        self.llm = llm
        self.note_folder = note_folder
        self.note_folder.mkdir(exist_ok=True)

    def search(self, query: str, use_embedding: bool = False, rerank: bool = False,
               source_quota: Optional[int] = None, top_k: int = 10) -> List[Tuple[Document, float]]:
        if use_embedding:
            return self.kb.embedding_search(query, top_k, rerank)
        return self.kb.lexical_search(query, top_k, source_quota)

    def read_windows(self, query: str, docs_scores: List[Tuple[Document, float]],
                     sections: bool = True, lines: Optional[Tuple[int,int]] = None,
                     pages: bool = False, archive_members: bool = False,
                     table_slices: bool = False) -> List[Section]:
        """Read relevant windows from top matching docs based on query hints.
        This is a simplified window retrieval: it tries to locate where query terms appear
        and returns that section or line range."""
        windows = []
        for doc, _ in docs_scores[:5]:  # read top 5 documents
            # For simplicity, find first section that contains query terms
            for sec in doc.sections:
                if any(term.lower() in sec.content.lower() for term in query.split()):
                    if lines:
                        line_start, line_end = lines
                        snippet = self.reader.read_lines(doc, line_start, line_end, doc.sections.index(sec))
                        windows.append(Section(content=snippet or "", start_line=line_start,
                                               end_line=line_end, archive_member=sec.archive_member,
                                               page_number=sec.page_number))
                    else:
                        windows.append(sec)
                    break  # one window per doc
        return windows

    def answer_query(self, query: str, use_embedding: bool = False, rerank: bool = False,
                     source_quota: Optional[int] = None, top_k: int = 10,
                     lines: Optional[Tuple[int,int]] = None,
                     pages: bool = False, archive_members: bool = False,
                     table_slices: bool = False) -> Tuple[str, List[Citation], List[Section]]:
        # 1. Search
        docs_scores = self.search(query, use_embedding, rerank, source_quota, top_k)
        # 2. Read windows
        windows = self.read_windows(query, docs_scores, sections=True, lines=lines,
                                    pages=pages, archive_members=archive_members, table_slices=table_slices)
        # 3. Build context
        context_parts = []
        citations = []
        for i, (doc, score) in enumerate(docs_scores[:5]):
            if i < len(windows):
                win = windows[i]
                context_parts.append(f"Source {doc.id} (score {score:.2f}): {win.content[:500]}")
                citations.append(Citation(document_id=doc.id, section=win, text_snippet=win.content[:200]))
        context = "\n\n".join(context_parts)
        # 4. Generate answer
        prompt = f"Query: {query}\n\nBased on the following context, provide a concise answer with citations.\n\n{context}"
        answer = self.llm.generate(prompt, context)
        # 5. Save investigation note
        note = InvestigationNote(query=query, answer=answer, citations=citations,
                                 tags=set(), folder="inbox")
        self.save_note(note)
        return answer, citations, windows

    def save_note(self, note: InvestigationNote):
        note_path = self.note_folder / f"note_{note.timestamp.strftime('%Y%m%d%H%M%S')}.json"
        data = {
            'query': note.query,
            'answer': note.answer,
            'citations': [{'doc_id': c.document_id, 'snippet': c.text_snippet} for c in note.citations],
            'timestamp': note.timestamp.isoformat(),
            'tags': list(note.tags),
            'folder': note.folder
        }
        with open(note_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load_notes(self, folder: str = "inbox") -> List[InvestigationNote]:
        notes = []
        for f in self.note_folder.glob("*.json"):
            with open(f, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            if data.get('folder') == folder:
                note = InvestigationNote(
                    query=data['query'],
                    answer=data['answer'],
                    citations=[Citation(d['doc_id'], text_snippet=d['snippet']) for d in data['citations']],
                    timestamp=datetime.datetime.fromisoformat(data['timestamp']),
                    tags=set(data['tags']),
                    folder=data['folder']
                )
                notes.append(note)
        return notes

# ---------------------------------------------------------------------------
# Ingestion pipeline
# ---------------------------------------------------------------------------

class IngestionPipeline:
    """Coordinates ingestion from a directory recursively using appropriate ingestors."""
    ingestors: Dict[str, Ingestor] = {
        '.txt': TextIngestor(),
        '.md': MarkdownIngestor(),
        '.pdf': PDFIngestor(),
        '.docx': DOCXIngestor(),
        '.jpg': ImageIngestor(), '.jpeg': ImageIngestor(), '.png': ImageIngestor(),
        '.gif': ImageIngestor(), '.bmp': ImageIngestor(), '.tiff': ImageIngestor(),
        '.csv': SpreadsheetIngestor(), '.xlsx': SpreadsheetIngestor(),
        '.xls': SpreadsheetIngestor(), '.ods': SpreadsheetIngestor(),
        '.log': LogIngestor(),
        '.zip': ArchiveIngestor(), '.tar': ArchiveIngestor(),
        '.gz': ArchiveIngestor(), '.bz2': ArchiveIngestor(),
        '.xz': ArchiveIngestor(),
    }

    def __init__(self, kb: KnowledgeBase, organizer: Organizer):
        self.kb = kb
        self.organizer = organizer

    def ingest_path(self, path: Path, recursive: bool = True):
        if path.is_file():
            self.ingest_file(path)
        elif path.is_dir():
            for item in path.iterdir():
                if item.is_file():
                    self.ingest_file(item)
                elif item.is_dir() and recursive:
                    self.ingest_path(item, recursive=True)

    def ingest_file(self, file_path: Path):
        ext = file_path.suffix.lower()
        ingestor = self.ingestors.get(ext)
        if ingestor is None:
            print(f"Skipping unsupported file type: {file_path}")
            return
        doc = ingestor.ingest(file_path)
        # Auto-tag based on extension and parent folder name
        doc.add_tag(f"ext:{ext[1:]}")
        doc.add_tag(f"folder:{file_path.parent.name}")
        self.kb.add_document(doc)
        self.organizer.assign_to_folder(doc.id, str(file_path.parent))
        print(f"Ingested: {doc.id}")

# ---------------------------------------------------------------------------
# Main application entry point (example usage)
# ---------------------------------------------------------------------------

def main():
    # Setup
    kb = KnowledgeBase(db_path=Path("marginalia.db"))
    organizer = Organizer(kb)
    reader = Reader()
    llm = MockLLMClient()
    agent = Agent(kb, organizer, reader, llm, note_folder=Path("investigation_notes"))

    # Ingest some sample files/directory
    pipeline = IngestionPipeline(kb, organizer)
    # For demonstration, create a dummy folder with a file
    demo_dir = Path("demo_docs")
    demo_dir.mkdir(exist_ok=True)
    sample_file = demo_dir / "readme.txt"
    sample_file.write_text("Marginalia is a personal knowledge management system.\nIt searches and cites sources.", encoding='utf-8')

    pipeline.ingest_path(demo_dir)

    # Perform a query
    answer, citations, windows = agent.answer_query(
        query="What is Marginalia?",
        use_embedding=False,
        source_quota=5
    )
    print("Answer:", answer)
    print("Citations:")
    for cite in citations:
        print(f"  - {cite.document_id}: {cite.text_snippet[:80]}...")

    # Mine relations
    organizer.mine_relations()
    print("Relations:", organizer.relations)

    # Save KB to disk
    kb.save_to_db()

if __name__ == "__main__":
    main()