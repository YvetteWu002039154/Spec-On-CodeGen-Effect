import os
import re
import uuid
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Optional, Callable, Tuple, Any
from dataclasses import dataclass, field

@dataclass
class Metadata:
    title: str = ""
    author: str = ""
    date_added: datetime = field(default_factory=datetime.now)
    source_type: str = ""
    custom_attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DocumentWindow:
    doc_id: str
    window_type: str  # 'section', 'page', 'line', 'archive_member', 'table_slice'
    content: str
    reference: str

@dataclass
class Document:
    id: str
    path: Path
    file_type: str
    content: str
    metadata: Metadata
    tags: Set[str] = field(default_factory=set)

@dataclass
class InvestigationNote:
    id: str
    timestamp: datetime
    query: str
    findings: str
    cited_sources: List[str]

@dataclass
class CitedAnswer:
    answer: str
    citations: List[str]

@dataclass
class Report:
    title: str
    summary: str
    detailed_answers: List[CitedAnswer]
    generated_at: datetime = field(default_factory=datetime.now)

class Journal:
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path
        self.notes: List[InvestigationNote] = []

    def add_note(self, note: InvestigationNote) -> None:
        self.notes.append(note)

    def get_history(self) -> List[InvestigationNote]:
        return sorted(self.notes, key=lambda n: n.timestamp)

class Catalog:
    def __init__(self, root_folder: Path):
        self.root_folder = root_folder
        self.documents: Dict[str, Document] = {}
        self.relations: List[Tuple[str, str, str]] = []
        self.views: Dict[str, Callable[[Document], bool]] = {}

    def add_document(self, document: Document) -> None:
        self.documents[document.id] = document

    def get_document(self, doc_id: str) -> Optional[Document]:
        return self.documents.get(doc_id)

    def add_relation(self, source_id: str, target_id: str, relation_type: str) -> None:
        if source_id in self.documents and target_id in self.documents:
            self.relations.append((source_id, target_id, relation_type))

    def create_view(self, name: str, filter_func: Callable[[Document], bool]) -> None:
        self.views[name] = filter_func

    def get_view(self, name: str) -> List[Document]:
        if name not in self.views:
            raise ValueError(f"View {name} does not exist.")
        return [doc for doc in self.documents.values() if self.views[name](doc)]

    def get_all_tags(self) -> Set[str]:
        tags = set()
        for doc in self.documents.values():
            tags.update(doc.tags)
        return tags

class Ingestor:
    SUPPORTED_EXTENSIONS = {
        '.txt': 'text',
        '.md': 'markdown',
        '.pdf': 'pdf',
        '.docx': 'docx',
        '.png': 'image',
        '.jpg': 'image',
        '.jpeg': 'image',
        '.csv': 'spreadsheet',
        '.xlsx': 'spreadsheet',
        '.log': 'log',
        '.zip': 'archive',
        '.tar': 'archive',
        '.gz': 'archive'
    }

    def __init__(self, catalog: Catalog):
        self.catalog = catalog

    def ingest_file(self, file_path: Path) -> Document:
        ext = file_path.suffix.lower()
        file_type = self.SUPPORTED_EXTENSIONS.get(ext, 'unknown')
        
        content = f"Simulated extracted content from {file_path.name} of type {file_type}"
        
        doc = Document(
            id=str(uuid.uuid4()),
            path=file_path,
            file_type=file_type,
            content=content,
            metadata=Metadata(title=file_path.stem, source_type=file_type),
            tags={file_type}
        )
        self.catalog.add_document(doc)
        return doc

    def ingest_folder_tree(self) -> None:
        for root, _, files in os.walk(self.catalog.root_folder):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    self.ingest_file(file_path)

class RelationMiner:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog

    def mine_relations(self) -> None:
        docs = list(self.catalog.documents.values())
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                doc_a = docs[i]
                doc_b = docs[j]
                shared_tags = doc_a.tags.intersection(doc_b.tags)
                if shared_tags:
                    self.catalog.add_relation(doc_a.id, doc_b.id, f"shared_tags:{','.join(shared_tags)}")
                
                if doc_a.path.parent == doc_b.path.parent:
                    self.catalog.add_relation(doc_a.id, doc_b.id, "same_folder")

class SearchEngine:
    def __init__(self, catalog: Catalog, use_embeddings: bool = False, use_sqlite_vec: bool = False):
        self.catalog = catalog
        self.use_embeddings = use_embeddings
        self.use_sqlite_vec = use_sqlite_vec
        
        if self.use_sqlite_vec:
            self._init_sqlite_vec()

    def _init_sqlite_vec(self) -> None:
        self.conn = sqlite3.connect(':memory:')
        self.conn.execute("CREATE TABLE vec_index (id TEXT, embedding BLOB)")

    def search(self, query: str, quota: int = 5, rerank: bool = False) -> List[Document]:
        results = self._lexical_search(query)
        
        if self.use_embeddings or self.use_sqlite_vec:
            results.extend(self._vector_search(query))
            
        results = list({doc.id: doc for doc in results}.values())
        
        if rerank:
            results = self._rerank_results(query, results)
            
        return results[:quota]

    def _lexical_search(self, query: str) -> List[Document]:
        query_terms = query.lower().split()
        results = []
        for doc in self.catalog.documents.values():
            content_lower = doc.content.lower()
            if any(term in content_lower for term in query_terms):
                results.append(doc)
        return results

    def _vector_search(self, query: str) -> List[Document]:
        return []

    def _rerank_results(self, query: str, results: List[Document]) -> List[Document]:
        query_terms = set(query.lower().split())
        def score(doc: Document) -> int:
            return sum(1 for term in query_terms if term in doc.content.lower())
        return sorted(results, key=score, reverse=True)

class Reader:
    def extract_windows(self, document: Document, query: str) -> List[DocumentWindow]:
        windows = []
        
        if document.file_type == 'text' or document.file_type == 'markdown':
            lines = document.content.split('\n')
            for i, line in enumerate(lines):
                if any(term in line.lower() for term in query.lower().split()):
                    windows.append(DocumentWindow(
                        doc_id=document.id,
                        window_type='line',
                        content=line,
                        reference=f"Line {i+1}"
                    ))
                    
        elif document.file_type == 'pdf' or document.file_type == 'docx':
            windows.append(DocumentWindow(
                doc_id=document.id,
                window_type='page',
                content=document.content[:500], 
                reference="Page 1"
            ))
            
        elif document.file_type == 'spreadsheet':
            windows.append(DocumentWindow(
                doc_id=document.id,
                window_type='table_slice',
                content="Row 1-5, Cols A-C", 
                reference="Rows 1-5"
            ))
            
        elif document.file_type == 'archive':
            windows.append(DocumentWindow(
                doc_id=document.id,
                window_type='archive_member',
                content="Extracted file.txt from archive",
                reference="file.txt"
            ))
            
        else:
            windows.append(DocumentWindow(
                doc_id=document.id,
                window_type='section',
                content=document.content,
                reference="Main Section"
            ))
            
        return windows

class ResearchAgent:
    def __init__(self, catalog: Catalog, journal: Journal, search_engine: SearchEngine, reader: Reader):
        self.catalog = catalog
        self.journal = journal
        self.search_engine = search_engine
        self.reader = reader

    def _generate_llm_response(self, query: str, windows: List[DocumentWindow]) -> str:
        if not windows:
            return "I could not find any relevant information in the knowledge base."
        
        context = "\n".join([f"[{w.reference}]: {w.content}" for w in windows])
        return f"Based on the provided context, here is the answer to '{query}'. Context used: {context}"

    def investigate(self, query: str, source_quota: int = 5, use_reranking: bool = True) -> CitedAnswer:
        past_notes = self.journal.get_history()
        enriched_query = query
        if past_notes:
            enriched_query += " " + " ".join([note.findings for note in past_notes[-2:]])

        candidate_docs = self.search_engine.search(enriched_query, quota=source_quota, rerank=use_reranking)
        
        relevant_windows: List[DocumentWindow] = []
        for doc in candidate_docs:
            windows = self.reader.extract_windows(doc, query)
            relevant_windows.extend(windows)

        answer_text = self._generate_llm_response(query, relevant_windows)
        
        citations = []
        for w in relevant_windows:
            doc = self.catalog.get_document(w.doc_id)
            if doc:
                citations.append(f"{doc.metadata.title} ({w.window_type}: {w.reference})")
        
        citations = list(set(citations))

        cited_answer = CitedAnswer(answer=answer_text, citations=citations)

        note = InvestigationNote(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            query=query,
            findings=cited_answer.answer,
            cited_sources=cited_answer.citations
        )
        self.journal.add_note(note)

        return cited_answer

    def generate_report(self, topic: str, queries: List[str]) -> Report:
        answers = []
        for q in queries:
            answers.append(self.investigate(q))
            
        summary = f"Report generated for topic: {topic}. Investigated {len(queries)} sub-queries."
        
        return Report(
            title=f"Investigation Report: {topic}",
            summary=summary,
            detailed_answers=answers
        )

class MarginaliaSystem:
    def __init__(self, root_folder_path: str, use_embeddings: bool = False, use_sqlite_vec: bool = False):
        self.root_path = Path(root_folder_path)
        self.catalog = Catalog(self.root_path)
        self.journal = Journal()
        self.ingestor = Ingestor(self.catalog)
        self.relation_miner = RelationMiner(self.catalog)
        self.search_engine = SearchEngine(
            self.catalog, 
            use_embeddings=use_embeddings, 
            use_sqlite_vec=use_sqlite_vec
        )
        self.reader = Reader()
        self.agent = ResearchAgent(self.catalog, self.journal, self.search_engine, self.reader)

    def initialize(self) -> None:
        if not self.root_path.exists():
            self.root_path.mkdir(parents=True, exist_ok=True)
            
        self.ingestor.ingest_folder_tree()
        self.relation_miner.mine_relations()
        
        self.catalog.create_view("recent_documents", lambda d: (datetime.now() - d.metadata.date_added).days < 7)
        self.catalog.create_view("pdfs_only", lambda d: d.file_type == 'pdf')

    def ask(self, query: str) -> CitedAnswer:
        return self.agent.investigate(query)

    def create_report(self, topic: str, sub_queries: List[str]) -> Report:
        return self.agent.generate_report(topic, sub_queries)