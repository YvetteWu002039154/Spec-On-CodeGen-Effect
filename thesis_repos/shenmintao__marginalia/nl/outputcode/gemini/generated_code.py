import os
import json
import sqlite3
import uuid
import zipfile
import csv
import re
import math
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, Counter

@dataclass
class Metadata:
    catalog: str = "default"
    tags: Set[str] = field(default_factory=set)
    views: Set[str] = field(default_factory=set)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DocumentWindow:
    window_id: str
    doc_id: str
    window_type: str  # 'section', 'page', 'line', 'archive_member', 'table_slice'
    location_identifier: str
    content: str

@dataclass
class Document:
    doc_id: str
    filepath: str
    file_type: str
    content: str
    metadata: Metadata
    windows: List[DocumentWindow] = field(default_factory=list)

@dataclass
class InvestigationNote:
    note_id: str
    timestamp: datetime
    query: str
    content: str
    citations: List[str]

@dataclass
class CitedAnswer:
    answer_text: str
    report: str
    citations: List[str]
    investigation_note_id: str

class Ingestor:
    def __init__(self):
        self.supported_extensions = {
            '.txt': 'text', '.md': 'markdown', '.pdf': 'pdf', 
            '.docx': 'docx', '.png': 'image', '.jpg': 'image', 
            '.csv': 'spreadsheet', '.log': 'log', '.zip': 'archive'
        }

    def ingest(self, filepath: str, metadata: Optional[Metadata] = None) -> Document:
        path = Path(filepath)
        ext = path.suffix.lower()
        file_type = self.supported_extensions.get(ext, 'unknown')
        doc_id = str(uuid.uuid4())
        metadata = metadata or Metadata()
        
        content = ""
        windows = []

        if not path.exists():
            content = f"[Simulated content for missing file: {path.name}]"
            windows = [DocumentWindow(str(uuid.uuid4()), doc_id, "section", "1", content)]
        elif file_type in ['text', 'markdown', 'log']:
            content, windows = self._ingest_text_based(path, doc_id, file_type)
        elif file_type == 'spreadsheet':
            content, windows = self._ingest_spreadsheet(path, doc_id)
        elif file_type == 'archive':
            content, windows = self._ingest_archive(path, doc_id)
        else:
            content = f"[Extracted text from {file_type} file: {path.name}]"
            windows = [DocumentWindow(str(uuid.uuid4()), doc_id, "page", "1", content)]

        return Document(doc_id, str(path), file_type, content, metadata, windows)

    def _ingest_text_based(self, path: Path, doc_id: str, file_type: str) -> Tuple[str, List[DocumentWindow]]:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        content = "".join(lines)
        windows = []
        
        if file_type == 'log':
            for i, line in enumerate(lines):
                if line.strip():
                    windows.append(DocumentWindow(str(uuid.uuid4()), doc_id, "line", str(i+1), line.strip()))
        elif file_type == 'markdown':
            sections = re.split(r'(^#+\s+.*)', content, flags=re.MULTILINE)
            current_section = "Intro"
            current_content = []
            for part in sections:
                if re.match(r'^#+\s+', part):
                    if current_content:
                        windows.append(DocumentWindow(str(uuid.uuid4()), doc_id, "section", current_section, "".join(current_content).strip()))
                    current_section = part.strip()
                    current_content = [part]
                else:
                    current_content.append(part)
            if current_content:
                windows.append(DocumentWindow(str(uuid.uuid4()), doc_id, "section", current_section, "".join(current_content).strip()))
        else:
            chunk_size = 50
            for i in range(0, len(lines), chunk_size):
                chunk = "".join(lines[i:i+chunk_size])
                windows.append(DocumentWindow(str(uuid.uuid4()), doc_id, "page", f"{i//chunk_size + 1}", chunk.strip()))
                
        return content, windows

    def _ingest_spreadsheet(self, path: Path, doc_id: str) -> Tuple[str, List[DocumentWindow]]:
        windows = []
        content_parts = []
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                row_str = ", ".join(row)
                content_parts.append(row_str)
                windows.append(DocumentWindow(str(uuid.uuid4()), doc_id, "table_slice", f"row_{i+1}", row_str))
        return "\n".join(content_parts), windows

    def _ingest_archive(self, path: Path, doc_id: str) -> Tuple[str, List[DocumentWindow]]:
        windows = []
        content_parts = []
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path, 'r') as z:
                for member in z.namelist():
                    content_parts.append(member)
                    windows.append(DocumentWindow(str(uuid.uuid4()), doc_id, "archive_member", member, f"File inside archive: {member}"))
        return "\n".join(content_parts), windows

class LibraryCatalog:
    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS documents (doc_id TEXT PRIMARY KEY, filepath TEXT, file_type TEXT, content TEXT);
            CREATE TABLE IF NOT EXISTS metadata (doc_id TEXT, catalog TEXT, custom_attributes TEXT);
            CREATE TABLE IF NOT EXISTS tags (doc_id TEXT, tag TEXT);
            CREATE TABLE IF NOT EXISTS views (doc_id TEXT, view_name TEXT);
            CREATE TABLE IF NOT EXISTS windows (window_id TEXT PRIMARY KEY, doc_id TEXT, window_type TEXT, location TEXT, content TEXT);
            CREATE TABLE IF NOT EXISTS journals (note_id TEXT PRIMARY KEY, timestamp TEXT, query TEXT, content TEXT, citations TEXT);
            CREATE TABLE IF NOT EXISTS relations (doc_id_1 TEXT, doc_id_2 TEXT, relation_type TEXT, weight REAL);
        """)
        self.conn.commit()

    def add_document(self, doc: Document):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO documents VALUES (?, ?, ?, ?)", 
                       (doc.doc_id, doc.filepath, doc.file_type, doc.content))
        cursor.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?, ?)", 
                       (doc.doc_id, doc.metadata.catalog, json.dumps(doc.metadata.custom_attributes)))
        
        cursor.execute("DELETE FROM tags WHERE doc_id = ?", (doc.doc_id,))
        for tag in doc.metadata.tags:
            cursor.execute("INSERT INTO tags VALUES (?, ?)", (doc.doc_id, tag))
            
        cursor.execute("DELETE FROM views WHERE doc_id = ?", (doc.doc_id,))
        for view in doc.metadata.views:
            cursor.execute("INSERT INTO views VALUES (?, ?)", (doc.doc_id, view))
            
        cursor.execute("DELETE FROM windows WHERE doc_id = ?", (doc.doc_id,))
        for w in doc.windows:
            cursor.execute("INSERT INTO windows VALUES (?, ?, ?, ?, ?)", 
                           (w.window_id, w.doc_id, w.window_type, w.location_identifier, w.content))
        self.conn.commit()

    def add_journal_note(self, note: InvestigationNote):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO journals VALUES (?, ?, ?, ?, ?)", 
                       (note.note_id, note.timestamp.isoformat(), note.query, note.content, json.dumps(note.citations)))
        self.conn.commit()

    def get_all_windows(self) -> List[DocumentWindow]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT window_id, doc_id, window_type, location, content FROM windows")
        return [DocumentWindow(*row) for row in cursor.fetchall()]

    def get_all_documents(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT doc_id, filepath, content FROM documents")
        return [{"doc_id": r[0], "filepath": r[1], "content": r[2]} for r in cursor.fetchall()]

    def add_relation(self, doc_id_1: str, doc_id_2: str, relation_type: str, weight: float):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO relations VALUES (?, ?, ?, ?)", (doc_id_1, doc_id_2, relation_type, weight))
        self.conn.commit()

class RelationMiner:
    def __init__(self, catalog: LibraryCatalog):
        self.catalog = catalog

    def mine_relations(self):
        docs = self.catalog.get_all_documents()
        for i, doc1 in enumerate(docs):
            for doc2 in docs[i+1:]:
                words1 = set(doc1['content'].lower().split())
                words2 = set(doc2['content'].lower().split())
                intersection = words1.intersection(words2)
                if len(intersection) > 10:
                    weight = len(intersection) / min(len(words1), len(words2))
                    self.catalog.add_relation(doc1['doc_id'], doc2['doc_id'], 'lexical_overlap', weight)

class SearchEngine:
    def __init__(self, catalog: LibraryCatalog, use_embeddings: bool = False, use_sqlite_vec: bool = False):
        self.catalog = catalog
        self.use_embeddings = use_embeddings
        self.use_sqlite_vec = use_sqlite_vec

    def recall(self, query: str, source_quota: int = 5, rerank: bool = False) -> List[DocumentWindow]:
        windows = self.catalog.get_all_windows()
        
        if self.use_sqlite_vec or self.use_embeddings:
            candidates = self._vector_search(query, windows)
        else:
            candidates = self._lexical_search(query, windows)
            
        if rerank:
            candidates = self._rerank(query, candidates)
            
        return candidates[:source_quota]

    def _lexical_search(self, query: str, windows: List[DocumentWindow]) -> List[DocumentWindow]:
        query_terms = set(re.findall(r'\w+', query.lower()))
        scored_windows = []
        for w in windows:
            content_terms = re.findall(r'\w+', w.content.lower())
            term_counts = Counter(content_terms)
            score = sum(term_counts[term] for term in query_terms)
            if score > 0:
                scored_windows.append((score, w))
        
        scored_windows.sort(key=lambda x: x[0], reverse=True)
        return [w for score, w in scored_windows]

    def _vector_search(self, query: str, windows: List[DocumentWindow]) -> List[DocumentWindow]:
        return self._lexical_search(query, windows)

    def _rerank(self, query: str, windows: List[DocumentWindow]) -> List[DocumentWindow]:
        return windows

class LLMClient:
    def generate(self, prompt: str) -> str:
        return f"Based on the provided context, here is the synthesized answer to your query.\n\n[Simulated LLM Response generated from context]"

class ResearchAgent:
    def __init__(self, catalog: LibraryCatalog, search_engine: SearchEngine, llm_client: LLMClient):
        self.catalog = catalog
        self.search_engine = search_engine
        self.llm_client = llm_client

    def investigate(self, query: str, source_quota: int = 5) -> CitedAnswer:
        windows = self.search_engine.recall(query, source_quota=source_quota, rerank=True)
        
        context_blocks = []
        citations = []
        for w in windows:
            context_blocks.append(f"--- Source: {w.doc_id} | Type: {w.window_type} | Location: {w.location_identifier} ---\n{w.content}")
            if w.doc_id not in citations:
                citations.append(w.doc_id)
                
        context_str = "\n\n".join(context_blocks)
        prompt = f"System: You are Marginalia, a research agent. Read the following original file windows and answer the query with citations.\n\nContext:\n{context_str}\n\nQuery: {query}\n\nAnswer:"
        
        answer_text = self.llm_client.generate(prompt)
        report = f"Investigation Report:\nQuery: {query}\nSources Read: {len(windows)} windows from {len(citations)} documents.\n"
        
        note_id = str(uuid.uuid4())
        note_content = f"Report:\n{report}\nAnswer:\n{answer_text}"
        note = InvestigationNote(
            note_id=note_id,
            timestamp=datetime.now(),
            query=query,
            content=note_content,
            citations=citations
        )
        
        self.catalog.add_journal_note(note)
        
        return CitedAnswer(
            answer_text=answer_text,
            report=report,
            citations=citations,
            investigation_note_id=note_id
        )

class FileSystemManager:
    def __init__(self, root_dir: str, ingestor: Ingestor, catalog: LibraryCatalog):
        self.root_dir = Path(root_dir)
        self.ingestor = ingestor
        self.catalog = catalog

    def scan_and_ingest(self):
        if not self.root_dir.exists():
            self.root_dir.mkdir(parents=True, exist_ok=True)
            
        for filepath in self.root_dir.rglob('*'):
            if filepath.is_file():
                rel_path = filepath.relative_to(self.root_dir)
                folder_tags = set(rel_path.parts[:-1])
                
                metadata = Metadata(
                    catalog="local_files",
                    tags=folder_tags,
                    custom_attributes={"filename": filepath.name}
                )
                
                doc = self.ingestor.ingest(str(filepath), metadata)
                self.catalog.add_document(doc)

class MarginaliaSystem:
    def __init__(self, root_dir: str, db_path: str = ":memory:"):
        self.catalog = LibraryCatalog(db_path)
        self.ingestor = Ingestor()
        self.fs_manager = FileSystemManager(root_dir, self.ingestor, self.catalog)
        self.relation_miner = RelationMiner(self.catalog)
        self.search_engine = SearchEngine(self.catalog, use_embeddings=False, use_sqlite_vec=False)
        self.llm_client = LLMClient()
        self.agent = ResearchAgent(self.catalog, self.search_engine, self.llm_client)

    def sync(self):
        self.fs_manager.scan_and_ingest()
        self.relation_miner.mine_relations()

    def ask(self, query: str, source_quota: int = 5) -> CitedAnswer:
        return self.agent.investigate(query, source_quota)