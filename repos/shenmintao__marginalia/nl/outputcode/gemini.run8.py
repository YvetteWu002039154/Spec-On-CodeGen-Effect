import os
import sqlite3
import uuid
import json
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import List, Dict, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field

class FileType(Enum):
    TEXT = auto()
    MARKDOWN = auto()
    PDF = auto()
    DOCX = auto()
    IMAGE = auto()
    SPREADSHEET = auto()
    LOG = auto()
    ARCHIVE = auto()

class WindowType(Enum):
    SECTION = auto()
    PAGE = auto()
    LINE = auto()
    ARCHIVE_MEMBER = auto()
    TABLE_SLICE = auto()

@dataclass
class Document:
    id: str
    path: Path
    file_type: FileType
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    
    @property
    def folder(self) -> str:
        return str(self.path.parent)

@dataclass
class View:
    name: str
    query: str
    filters: Dict[str, Any]

@dataclass
class Relation:
    source_id: str
    target_id: str
    relation_type: str
    weight: float

@dataclass
class FileWindow:
    doc_id: str
    window_type: WindowType
    location: str
    content: str

@dataclass
class Citation:
    window: FileWindow
    reference_text: str

@dataclass
class CitedAnswer:
    text: str
    citations: List[Citation]

@dataclass
class Report:
    title: str
    summary: str
    answers: List[CitedAnswer]
    generated_at: datetime = field(default_factory=datetime.now)

@dataclass
class InvestigationNote:
    id: str
    timestamp: datetime
    query: str
    findings: str
    referenced_doc_ids: List[str]

class Journal:
    def __init__(self):
        self.notes: List[InvestigationNote] = []

    def add_note(self, query: str, findings: str, referenced_doc_ids: List[str]) -> InvestigationNote:
        note = InvestigationNote(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            query=query,
            findings=findings,
            referenced_doc_ids=referenced_doc_ids
        )
        self.notes.append(note)
        return note

    def get_history(self) -> List[InvestigationNote]:
        return sorted(self.notes, key=lambda x: x.timestamp, reverse=True)

class RelationMiner:
    def __init__(self):
        self.relations: List[Relation] = []

    def mine_relations(self, documents: List[Document]) -> None:
        self.relations.clear()
        for i, doc_a in enumerate(documents):
            for doc_b in documents[i+1:]:
                shared_tags = doc_a.tags.intersection(doc_b.tags)
                if shared_tags:
                    self.relations.append(Relation(
                        source_id=doc_a.id,
                        target_id=doc_b.id,
                        relation_type="shared_tags",
                        weight=len(shared_tags)
                    ))
                if doc_a.folder == doc_b.folder:
                    self.relations.append(Relation(
                        source_id=doc_a.id,
                        target_id=doc_b.id,
                        relation_type="same_folder",
                        weight=1.0
                    ))

class Catalog:
    def __init__(self, db_path: str = ":memory:"):
        self.documents: Dict[str, Document] = {}
        self.views: Dict[str, View] = {}
        self.conn = sqlite3.connect(db_path)
        self._init_db()
        self.relation_miner = RelationMiner()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS lexical_index 
            USING fts5(id, content, tokenize='porter')
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vector_index (
                id TEXT PRIMARY KEY,
                embedding BLOB
            )
        """)
        self.conn.commit()

    def determine_file_type(self, path: Path) -> FileType:
        ext = path.suffix.lower()
        mapping = {
            '.txt': FileType.TEXT,
            '.md': FileType.MARKDOWN,
            '.pdf': FileType.PDF,
            '.docx': FileType.DOCX,
            '.jpg': FileType.IMAGE,
            '.png': FileType.IMAGE,
            '.csv': FileType.SPREADSHEET,
            '.xlsx': FileType.SPREADSHEET,
            '.log': FileType.LOG,
            '.zip': FileType.ARCHIVE,
            '.tar': FileType.ARCHIVE
        }
        return mapping.get(ext, FileType.TEXT)

    def ingest(self, root_path: Union[str, Path]) -> None:
        root = Path(root_path)
        if not root.exists():
            return

        for file_path in root.rglob('*'):
            if file_path.is_file():
                doc_id = str(uuid.uuid4())
                doc = Document(
                    id=doc_id,
                    path=file_path,
                    file_type=self.determine_file_type(file_path),
                    metadata={"size": file_path.stat().st_size, "ingested_at": datetime.now().isoformat()},
                    tags=set()
                )
                self.documents[doc_id] = doc
                
                content = f"Simulated content for {file_path.name}"
                self.conn.execute(
                    "INSERT INTO lexical_index (id, content) VALUES (?, ?)",
                    (doc_id, content)
                )
        self.conn.commit()
        self.relation_miner.mine_relations(list(self.documents.values()))

    def add_tag(self, doc_id: str, tag: str) -> None:
        if doc_id in self.documents:
            self.documents[doc_id].tags.add(tag)
            self.relation_miner.mine_relations(list(self.documents.values()))

    def update_metadata(self, doc_id: str, key: str, value: Any) -> None:
        if doc_id in self.documents:
            self.documents[doc_id].metadata[key] = value

    def create_view(self, name: str, query: str, filters: Dict[str, Any]) -> View:
        view = View(name=name, query=query, filters=filters)
        self.views[name] = view
        return view

class RecallSystem:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog

    def lexical_search(self, query: str) -> List[Document]:
        cursor = self.catalog.conn.cursor()
        cursor.execute(
            "SELECT id FROM lexical_index WHERE content MATCH ? ORDER BY rank",
            (query,)
        )
        results = cursor.fetchall()
        return [self.catalog.documents[row[0]] for row in results if row[0] in self.catalog.documents]

    def vector_search(self, query_embedding: List[float]) -> List[Document]:
        return []

    def sqlite_vec_search(self, query: str) -> List[Document]:
        return []

    def rerank(self, documents: List[Document], query: str) -> List[Document]:
        return sorted(documents, key=lambda d: d.path.name)

    def apply_source_quotas(self, documents: List[Document], max_per_type: int = 3) -> List[Document]:
        type_counts: Dict[FileType, int] = {}
        filtered = []
        for doc in documents:
            count = type_counts.get(doc.file_type, 0)
            if count < max_per_type:
                filtered.append(doc)
                type_counts[doc.file_type] = count + 1
        return filtered

    def recall_candidates(self, query: str, use_embeddings: bool = False, use_sqlite_vec: bool = False) -> List[Document]:
        candidates = self.lexical_search(query)
        
        if use_embeddings:
            candidates.extend(self.vector_search([0.0]))
            
        if use_sqlite_vec:
            candidates.extend(self.sqlite_vec_search(query))
            
        unique_candidates = {doc.id: doc for doc in candidates}.values()
        reranked = self.rerank(list(unique_candidates), query)
        return self.apply_source_quotas(reranked)

class WindowReader:
    def read_original_window(self, document: Document) -> List[FileWindow]:
        windows = []
        if document.file_type == FileType.TEXT or document.file_type == FileType.LOG:
            windows.append(FileWindow(document.id, WindowType.LINE, "lines 1-50", f"Content lines from {document.path.name}"))
        elif document.file_type == FileType.MARKDOWN:
            windows.append(FileWindow(document.id, WindowType.SECTION, "Header 1", f"Section content from {document.path.name}"))
        elif document.file_type in (FileType.PDF, FileType.DOCX):
            windows.append(FileWindow(document.id, WindowType.PAGE, "page 1", f"Page text from {document.path.name}"))
        elif document.file_type == FileType.ARCHIVE:
            windows.append(FileWindow(document.id, WindowType.ARCHIVE_MEMBER, "file1.txt", f"Extracted member from {document.path.name}"))
        elif document.file_type == FileType.SPREADSHEET:
            windows.append(FileWindow(document.id, WindowType.TABLE_SLICE, "A1:D10", f"Table slice from {document.path.name}"))
        else:
            windows.append(FileWindow(document.id, WindowType.SECTION, "metadata", f"Metadata for {document.path.name}"))
        return windows

class MarginaliaAgent:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.catalog = Catalog()
        self.journal = Journal()
        self.recall = RecallSystem(self.catalog)
        self.reader = WindowReader()
        
        self.catalog.ingest(self.base_dir)

    def _generate_llm_response(self, query: str, windows: List[FileWindow]) -> CitedAnswer:
        citations = []
        for i, window in enumerate(windows):
            citations.append(Citation(
                window=window,
                reference_text=f"[{i+1}]"
            ))
            
        answer_text = f"Based on the provided documents, here is the answer to '{query}'. "
        answer_text += " ".join([c.reference_text for c in citations])
        
        return CitedAnswer(text=answer_text, citations=citations)

    def research(self, query: str, use_embeddings: bool = False) -> CitedAnswer:
        candidates = self.recall.recall_candidates(query, use_embeddings=use_embeddings)
        
        windows = []
        for doc in candidates:
            windows.extend(self.reader.read_original_window(doc))
            
        answer = self._generate_llm_response(query, windows)
        
        referenced_ids = list(set([w.doc_id for w in windows]))
        self.journal.add_note(
            query=query,
            findings=answer.text,
            referenced_doc_ids=referenced_ids
        )
        
        return answer

    def generate_report(self, title: str, queries: List[str]) -> Report:
        answers = []
        for query in queries:
            answers.append(self.research(query))
            
        return Report(
            title=title,
            summary=f"Report generated for {len(queries)} queries.",
            answers=answers
        )

    def get_investigation_history(self) -> List[InvestigationNote]:
        return self.journal.get_history()