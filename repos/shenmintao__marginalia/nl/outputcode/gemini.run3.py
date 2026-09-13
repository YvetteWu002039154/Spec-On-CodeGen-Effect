import os
import sqlite3
import json
import math
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any, Tuple, Union

@dataclass
class Metadata:
    author: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    custom_fields: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Document:
    filepath: str
    file_type: str
    content: str
    metadata: Metadata = field(default_factory=Metadata)
    tags: Set[str] = field(default_factory=set)
    folder: str = "/"
    
    def __hash__(self) -> int:
        return hash(self.filepath)

@dataclass
class InvestigationNote:
    query: str
    answer: str
    citations: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_document(self) -> Document:
        content = f"Query: {self.query}\nAnswer: {self.answer}\nCitations: {', '.join(self.citations)}"
        return Document(
            filepath=f"/notes/investigation_{self.timestamp.strftime('%Y%m%d%H%M%S')}.md",
            file_type="markdown",
            content=content,
            tags={"investigation_note", "durable_record"},
            folder="/notes"
        )

class FileIngester:
    def __init__(self):
        self.supported_extensions = {
            '.txt': 'text',
            '.md': 'markdown',
            '.pdf': 'pdf',
            '.docx': 'docx',
            '.jpg': 'image',
            '.png': 'image',
            '.csv': 'spreadsheet',
            '.xlsx': 'spreadsheet',
            '.log': 'log',
            '.zip': 'archive',
            '.tar': 'archive'
        }

    def ingest(self, filepath: str) -> Document:
        ext = os.path.splitext(filepath)[1].lower()
        file_type = self.supported_extensions.get(ext, 'unknown')
        
        content = self._extract_content(filepath, file_type)
        return Document(filepath=filepath, file_type=file_type, content=content)

    def _extract_content(self, filepath: str, file_type: str) -> str:
        return f"Simulated extracted content from {filepath} of type {file_type}."

class Catalog:
    def __init__(self):
        self._documents: Dict[str, Document] = {}
        self._folders: Dict[str, Set[str]] = {"/": set()}
        self._tags: Dict[str, Set[str]] = {}
        self._views: Dict[str, callable] = {}
        self._journals: List[Dict[str, Any]] = []
        self._relations: List[Tuple[str, str, str]] = []

    def add_document(self, doc: Document) -> None:
        self._documents[doc.filepath] = doc
        self.organize_in_folder(doc.filepath, doc.folder)
        for tag in doc.tags:
            self.add_tag(doc.filepath, tag)

    def organize_in_folder(self, filepath: str, folder: str) -> None:
        if folder not in self._folders:
            self._folders[folder] = set()
        self._folders[folder].add(filepath)
        if filepath in self._documents:
            self._documents[filepath].folder = folder

    def add_tag(self, filepath: str, tag: str) -> None:
        if tag not in self._tags:
            self._tags[tag] = set()
        self._tags[tag].add(filepath)
        if filepath in self._documents:
            self._documents[filepath].tags.add(tag)

    def create_view(self, view_name: str, filter_func: callable) -> None:
        self._views[view_name] = filter_func

    def get_view(self, view_name: str) -> List[Document]:
        if view_name not in self._views:
            return []
        return [doc for doc in self._documents.values() if self._views[view_name](doc)]

    def add_metadata(self, filepath: str, key: str, value: Any) -> None:
        if filepath in self._documents:
            self._documents[filepath].metadata.custom_fields[key] = value

    def add_journal_entry(self, entry: str) -> None:
        self._journals.append({
            "timestamp": datetime.now(),
            "entry": entry
        })

    def mine_relations(self) -> None:
        self._relations.clear()
        doc_list = list(self._documents.values())
        for i in range(len(doc_list)):
            for j in range(i + 1, len(doc_list)):
                doc_a = doc_list[i]
                doc_b = doc_list[j]
                shared_tags = doc_a.tags.intersection(doc_b.tags)
                if shared_tags:
                    self._relations.append((doc_a.filepath, doc_b.filepath, f"Shared tags: {shared_tags}"))

    def get_all_documents(self) -> List[Document]:
        return list(self._documents.values())

class Retriever:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog
        self.db_conn = sqlite3.connect(":memory:")
        self._setup_sqlite_vec_mock()

    def _setup_sqlite_vec_mock(self) -> None:
        cursor = self.db_conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vec_mock (
                filepath TEXT PRIMARY KEY,
                content TEXT
            )
        """)
        self.db_conn.commit()

    def _sync_db(self) -> None:
        cursor = self.db_conn.cursor()
        cursor.execute("DELETE FROM vec_mock")
        for doc in self.catalog.get_all_documents():
            cursor.execute("INSERT INTO vec_mock (filepath, content) VALUES (?, ?)", (doc.filepath, doc.content))
        self.db_conn.commit()

    def recall(self, 
               query: str, 
               method: str = "lexical", 
               use_embeddings: bool = False, 
               use_sqlite_vec: bool = False, 
               use_reranking: bool = False, 
               source_quota: int = 5) -> List[Document]:
        
        candidates: List[Document] = []
        
        if use_sqlite_vec or method == "sqlite-vec":
            self._sync_db()
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT filepath FROM vec_mock WHERE content LIKE ?", (f"%{query}%",))
            rows = cursor.fetchall()
            candidates = [doc for doc in self.catalog.get_all_documents() if doc.filepath in [r[0] for r in rows]]
        elif use_embeddings:
            candidates = self._mock_embedding_search(query)
        else:
            candidates = self._lexical_search(query)

        if use_reranking:
            candidates = self._rerank(query, candidates)

        return candidates[:source_quota]

    def _lexical_search(self, query: str) -> List[Document]:
        query_terms = query.lower().split()
        results = []
        for doc in self.catalog.get_all_documents():
            content_lower = doc.content.lower()
            if any(term in content_lower for term in query_terms):
                results.append(doc)
        return results

    def _mock_embedding_search(self, query: str) -> List[Document]:
        return self.catalog.get_all_documents()

    def _rerank(self, query: str, documents: List[Document]) -> List[Document]:
        def score(doc: Document) -> int:
            return doc.content.lower().count(query.lower())
        return sorted(documents, key=score, reverse=True)

class Reader:
    def read_section(self, doc: Document, section_name: str) -> str:
        return f"[Section: {section_name}] from {doc.filepath}: {doc.content[:100]}..."

    def read_page(self, doc: Document, page_number: int) -> str:
        return f"[Page: {page_number}] from {doc.filepath}: {doc.content[:100]}..."

    def read_line(self, doc: Document, line_number: int) -> str:
        return f"[Line: {line_number}] from {doc.filepath}: {doc.content[:50]}..."

    def read_archive_member(self, doc: Document, member_name: str) -> str:
        if doc.file_type != 'archive':
            raise ValueError("Document is not an archive.")
        return f"[Archive Member: {member_name}] from {doc.filepath}"

    def read_table_slice(self, doc: Document, row_start: int, row_end: int) -> str:
        if doc.file_type not in ['spreadsheet', 'csv']:
            raise ValueError("Document is not a spreadsheet.")
        return f"[Table Slice: rows {row_start}-{row_end}] from {doc.filepath}"

class Agent:
    def __init__(self, catalog: Catalog, retriever: Retriever, reader: Reader):
        self.catalog = catalog
        self.retriever = retriever
        self.reader = reader

    def produce_cited_answer(self, query: str) -> str:
        documents = self.retriever.recall(
            query=query, 
            method="lexical", 
            use_reranking=True, 
            source_quota=3
        )
        
        citations = []
        synthesized_context = []
        
        for i, doc in enumerate(documents):
            snippet = self.reader.read_section(doc, "Introduction")
            synthesized_context.append(f"Source [{i+1}]: {snippet}")
            citations.append(doc.filepath)
            
        answer = f"Based on the retrieved documents, here is the answer to '{query}'.\n"
        answer += "\n".join(synthesized_context)
        
        self.write_investigation_note(query, answer, citations)
        return answer

    def produce_report(self, topic: str) -> str:
        documents = self.retriever.recall(topic, source_quota=10)
        report = f"--- Comprehensive Report on {topic} ---\n"
        report += f"Analyzed {len(documents)} sources.\n"
        for doc in documents:
            report += f"- {doc.filepath} (Type: {doc.file_type})\n"
        return report

    def write_investigation_note(self, query: str, answer: str, citations: List[str]) -> None:
        note = InvestigationNote(query=query, answer=answer, citations=citations)
        doc_note = note.to_document()
        self.catalog.add_document(doc_note)
        self.catalog.add_journal_entry(f"Generated investigation note for query: {query}")

class Marginalia:
    def __init__(self):
        self.catalog = Catalog()
        self.ingester = FileIngester()
        self.retriever = Retriever(self.catalog)
        self.reader = Reader()
        self.agent = Agent(self.catalog, self.retriever, self.reader)

    def ingest_file(self, filepath: str, tags: Optional[Set[str]] = None, folder: str = "/") -> None:
        doc = self.ingester.ingest(filepath)
        doc.folder = folder
        if tags:
            doc.tags = tags
        self.catalog.add_document(doc)

    def ask(self, query: str) -> str:
        return self.agent.produce_cited_answer(query)

    def generate_report(self, topic: str) -> str:
        return self.agent.produce_report(topic)

    def organize(self) -> None:
        self.catalog.mine_relations()