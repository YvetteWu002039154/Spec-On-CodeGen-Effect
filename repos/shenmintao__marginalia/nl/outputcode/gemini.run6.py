import os
import re
import json
import csv
import zipfile
import sqlite3
from enum import Enum, auto
from typing import List, Dict, Set, Optional, Any, Callable, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

class FileType(Enum):
    TEXT = auto()
    MARKDOWN = auto()
    PDF = auto()
    DOCX = auto()
    IMAGE = auto()
    SPREADSHEET = auto()
    LOG = auto()
    ARCHIVE = auto()
    UNKNOWN = auto()

class LocationType(Enum):
    LINE = auto()
    PAGE = auto()
    SECTION = auto()
    ARCHIVE_MEMBER = auto()
    TABLE_SLICE = auto()
    FULL = auto()

@dataclass
class Location:
    location_type: LocationType
    identifier: str
    start_index: Optional[int] = None
    end_index: Optional[int] = None

@dataclass
class Metadata:
    author: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None
    custom_attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Tag:
    name: str
    description: Optional[str] = None

    def __hash__(self):
        return hash(self.name)

@dataclass
class Relation:
    source_id: str
    target_id: str
    relation_type: str
    weight: float = 1.0

@dataclass
class Document:
    doc_id: str
    path: str
    file_type: FileType
    content: Any
    metadata: Metadata
    tags: Set[Tag] = field(default_factory=set)
    
    def get_text_content(self) -> str:
        if isinstance(self.content, str):
            return self.content
        elif isinstance(self.content, dict):
            return json.dumps(self.content)
        elif isinstance(self.content, list):
            return "\n".join(str(item) for item in self.content)
        return str(self.content)

@dataclass
class SearchResult:
    document: Document
    score: float
    matched_locations: List[Location] = field(default_factory=list)

@dataclass
class CitedAnswer:
    answer_text: str
    citations: List[Tuple[str, Location]]
    generated_at: datetime = field(default_factory=datetime.now)

@dataclass
class InvestigationNote:
    note_id: str
    query: str
    answer: CitedAnswer
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class JournalEntry:
    entry_id: str
    timestamp: datetime
    content: str
    associated_docs: List[str] = field(default_factory=list)

class BaseParser:
    def parse(self, path: str) -> Any:
        raise NotImplementedError

class TextParser(BaseParser):
    def parse(self, path: str) -> str:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        return f"Mocked text content for {path}"

class MarkdownParser(BaseParser):
    def parse(self, path: str) -> str:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        return f"# Mocked Markdown\nContent for {path}"

class PDFParser(BaseParser):
    def parse(self, path: str) -> Dict[int, str]:
        return {1: f"Mocked PDF Page 1 for {path}", 2: "Mocked PDF Page 2"}

class DocxParser(BaseParser):
    def parse(self, path: str) -> List[str]:
        return [f"Mocked DOCX Paragraph 1 for {path}", "Mocked DOCX Paragraph 2"]

class ImageParser(BaseParser):
    def parse(self, path: str) -> str:
        return f"[OCR Extracted Text from Image {path}]"

class SpreadsheetParser(BaseParser):
    def parse(self, path: str) -> List[List[str]]:
        if os.path.exists(path) and path.endswith('.csv'):
            with open(path, 'r', encoding='utf-8') as f:
                return list(csv.reader(f))
        return [["Header1", "Header2"], ["Row1Col1", "Row1Col2"]]

class LogParser(BaseParser):
    def parse(self, path: str) -> List[str]:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.readlines()
        return [f"INFO: Mocked log entry 1 for {path}", "ERROR: Mocked log entry 2"]

class ArchiveParser(BaseParser):
    def parse(self, path: str) -> Dict[str, str]:
        if os.path.exists(path) and zipfile.is_zipfile(path):
            contents = {}
            with zipfile.ZipFile(path, 'r') as z:
                for name in z.namelist():
                    if not name.endswith('/'):
                        with z.open(name) as f:
                            contents[name] = f.read().decode('utf-8', errors='ignore')
            return contents
        return {"file1.txt": "Mocked archive member 1", "file2.md": "Mocked archive member 2"}

class IngestionManager:
    def __init__(self):
        self.parsers = {
            FileType.TEXT: TextParser(),
            FileType.MARKDOWN: MarkdownParser(),
            FileType.PDF: PDFParser(),
            FileType.DOCX: DocxParser(),
            FileType.IMAGE: ImageParser(),
            FileType.SPREADSHEET: SpreadsheetParser(),
            FileType.LOG: LogParser(),
            FileType.ARCHIVE: ArchiveParser(),
        }

    def determine_file_type(self, path: str) -> FileType:
        ext = path.lower().split('.')[-1]
        mapping = {
            'txt': FileType.TEXT,
            'md': FileType.MARKDOWN,
            'pdf': FileType.PDF,
            'docx': FileType.DOCX,
            'png': FileType.IMAGE,
            'jpg': FileType.IMAGE,
            'jpeg': FileType.IMAGE,
            'csv': FileType.SPREADSHEET,
            'xlsx': FileType.SPREADSHEET,
            'log': FileType.LOG,
            'zip': FileType.ARCHIVE,
            'tar': FileType.ARCHIVE
        }
        return mapping.get(ext, FileType.UNKNOWN)

    def ingest(self, path: str, doc_id: str) -> Document:
        file_type = self.determine_file_type(path)
        if file_type == FileType.UNKNOWN:
            file_type = FileType.TEXT
        
        parser = self.parsers.get(file_type, TextParser())
        content = parser.parse(path)
        
        metadata = Metadata(source=path)
        return Document(doc_id=doc_id, path=path, file_type=file_type, content=content, metadata=metadata)

class FolderTree:
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.structure: Dict[str, List[str]] = defaultdict(list)

    def scan(self) -> List[str]:
        files_found = []
        if os.path.exists(self.root_path):
            for root, _, files in os.walk(self.root_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    self.structure[root].append(full_path)
                    files_found.append(full_path)
        else:
            mock_path = os.path.join(self.root_path, "mock_file.txt")
            self.structure[self.root_path].append(mock_path)
            files_found.append(mock_path)
        return files_found

class View:
    def __init__(self, name: str, filter_func: Callable[[Document], bool]):
        self.name = name
        self.filter_func = filter_func

    def apply(self, documents: List[Document]) -> List[Document]:
        return [doc for doc in documents if self.filter_func(doc)]

class Catalog:
    def __init__(self):
        self.documents: Dict[str, Document] = {}
        self.relations: List[Relation] = []
        self.views: Dict[str, View] = {}

    def add_document(self, doc: Document):
        self.documents[doc.doc_id] = doc

    def get_document(self, doc_id: str) -> Optional[Document]:
        return self.documents.get(doc_id)

    def add_relation(self, relation: Relation):
        self.relations.append(relation)

    def add_view(self, view: View):
        self.views[view.name] = view

    def get_view_results(self, view_name: str) -> List[Document]:
        if view_name not in self.views:
            raise ValueError(f"View {view_name} not found.")
        return self.views[view_name].apply(list(self.documents.values()))

    def mine_relations(self):
        docs = list(self.documents.values())
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                shared_tags = docs[i].tags.intersection(docs[j].tags)
                if shared_tags:
                    self.add_relation(Relation(
                        source_id=docs[i].doc_id,
                        target_id=docs[j].doc_id,
                        relation_type="shared_tags",
                        weight=len(shared_tags)
                    ))

class Journal:
    def __init__(self):
        self.entries: List[JournalEntry] = []
        self.investigation_notes: List[InvestigationNote] = []

    def add_entry(self, entry: JournalEntry):
        self.entries.append(entry)

    def add_investigation_note(self, note: InvestigationNote):
        self.investigation_notes.append(note)

class SQLiteVecManager:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self._setup_db()

    def _setup_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vec_embeddings (
                doc_id TEXT PRIMARY KEY,
                embedding TEXT
            )
        """)
        self.conn.commit()

    def store_embedding(self, doc_id: str, text: str):
        cursor = self.conn.cursor()
        mock_embedding = f"[{len(text)}, 0.1, 0.2]"
        cursor.execute("INSERT OR REPLACE INTO vec_embeddings (doc_id, embedding) VALUES (?, ?)", (doc_id, mock_embedding))
        self.conn.commit()

    def search(self, query: str, limit: int = 5) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT doc_id FROM vec_embeddings LIMIT ?", (limit,))
        return [row[0] for row in cursor.fetchall()]

class SearchEngine:
    def __init__(self, vec_manager: SQLiteVecManager):
        self.vec_manager = vec_manager

    def lexical_search(self, query: str, catalog: Catalog) -> List[SearchResult]:
        results = []
        query_terms = set(query.lower().split())
        for doc in catalog.documents.values():
            text = doc.get_text_content().lower()
            score = sum(1 for term in query_terms if term in text)
            if score > 0:
                results.append(SearchResult(document=doc, score=float(score)))
        return sorted(results, key=lambda x: x.score, reverse=True)

    def vector_search(self, query: str, catalog: Catalog) -> List[SearchResult]:
        doc_ids = self.vec_manager.search(query)
        results = []
        for doc_id in doc_ids:
            doc = catalog.get_document(doc_id)
            if doc:
                results.append(SearchResult(document=doc, score=1.0))
        return results

    def rerank(self, results: List[SearchResult], query: str) -> List[SearchResult]:
        for res in results:
            if query.lower() in res.document.get_text_content().lower():
                res.score += 2.0
        return sorted(results, key=lambda x: x.score, reverse=True)

    def search(self, query: str, catalog: Catalog, use_embeddings: bool = False, use_reranking: bool = False, source_quota: int = 5) -> List[SearchResult]:
        if use_embeddings:
            results = self.vector_search(query, catalog)
            if not results:
                results = self.lexical_search(query, catalog)
        else:
            results = self.lexical_search(query, catalog)

        if use_reranking:
            results = self.rerank(results, query)

        return results[:source_quota]

class Reader:
    def read_window(self, document: Document, location: Location) -> str:
        if location.location_type == LocationType.FULL:
            return document.get_text_content()
            
        if document.file_type == FileType.TEXT or document.file_type == FileType.MARKDOWN:
            lines = document.get_text_content().split('\n')
            if location.location_type == LocationType.LINE:
                start = location.start_index or 0
                end = location.end_index or (start + 1)
                return '\n'.join(lines[start:end])
            elif location.location_type == LocationType.SECTION:
                return f"Section {location.identifier} content from {document.path}"

        elif document.file_type == FileType.PDF:
            if location.location_type == LocationType.PAGE and isinstance(document.content, dict):
                page_num = int(location.identifier)
                return document.content.get(page_num, "")

        elif document.file_type == FileType.ARCHIVE:
            if location.location_type == LocationType.ARCHIVE_MEMBER and isinstance(document.content, dict):
                return document.content.get(location.identifier, "")

        elif document.file_type == FileType.SPREADSHEET:
            if location.location_type == LocationType.TABLE_SLICE and isinstance(document.content, list):
                start = location.start_index or 0
                end = location.end_index or len(document.content)
                slice_rows = document.content[start:end]
                return "\n".join([",".join(row) for row in slice_rows])

        return document.get_text_content()[:500]

class LLMClient:
    def generate(self, prompt: str, context: List[Tuple[str, str]]) -> str:
        response = f"Based on the provided context, here is the answer to your query.\n\n"
        for i, (doc_id, text) in enumerate(context):
            response += f"According to {doc_id}, the information states: '{text[:50]}...'\n"
        return response

class MarginaliaAgent:
    def __init__(self, kb: 'KnowledgeBase'):
        self.kb = kb
        self.llm = LLMClient()

    def ask(self, query: str, use_embeddings: bool = False, use_reranking: bool = True, quota: int = 3) -> CitedAnswer:
        search_results = self.kb.search_engine.search(
            query=query, 
            catalog=self.kb.catalog, 
            use_embeddings=use_embeddings, 
            use_reranking=use_reranking, 
            source_quota=quota
        )

        context = []
        citations = []
        for res in search_results:
            loc = Location(location_type=LocationType.FULL, identifier="full")
            if res.document.file_type == FileType.PDF:
                loc = Location(location_type=LocationType.PAGE, identifier="1")
            elif res.document.file_type == FileType.SPREADSHEET:
                loc = Location(location_type=LocationType.TABLE_SLICE, identifier="slice", start_index=0, end_index=5)
            
            window_text = self.kb.reader.read_window(res.document, loc)
            context.append((res.document.doc_id, window_text))
            citations.append((res.document.doc_id, loc))

        answer_text = self.llm.generate(query, context)
        cited_answer = CitedAnswer(answer_text=answer_text, citations=citations)
        
        note_id = f"note_{int(datetime.now().timestamp())}"
        note = InvestigationNote(note_id=note_id, query=query, answer=cited_answer)
        self.kb.journal.add_investigation_note(note)
        
        note_doc = Document(
            doc_id=note_id,
            path=f"journal/{note_id}.md",
            file_type=FileType.MARKDOWN,
            content=f"# Query: {query}\n\n{answer_text}",
            metadata=Metadata(source="agent_investigation")
        )
        note_doc.tags.add(Tag("investigation"))
        self.kb.catalog.add_document(note_doc)
        
        return cited_answer

    def generate_report(self, topic: str) -> str:
        answer = self.ask(topic, quota=10)
        report = f"=== MARGINALIA REPORT: {topic.upper()} ===\n"
        report += f"Generated at: {answer.generated_at}\n\n"
        report += answer.answer_text + "\n\n"
        report += "Citations:\n"
        for doc_id, loc in answer.citations:
            report += f"- {doc_id} ({loc.location_type.name}: {loc.identifier})\n"
        return report

class KnowledgeBase:
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.folder_tree = FolderTree(root_path)
        self.catalog = Catalog()
        self.journal = Journal()
        self.ingestor = IngestionManager()
        self.vec_manager = SQLiteVecManager()
        self.search_engine = SearchEngine(self.vec_manager)
        self.reader = Reader()
        self.agent = MarginaliaAgent(self)

    def build(self):
        files = self.folder_tree.scan()
        for i, file_path in enumerate(files):
            doc_id = f"doc_{i}"
            doc = self.ingestor.ingest(file_path, doc_id)
            self.catalog.add_document(doc)
            self.vec_manager.store_embedding(doc_id, doc.get_text_content())
        
        self.catalog.mine_relations()

        recent_view = View("recent", lambda d: (datetime.now() - d.metadata.created_at).days < 7)
        self.catalog.add_view(recent_view)

if __name__ == "__main__":
    kb = KnowledgeBase("./my_messy_knowledge_base")
    kb.build()
    
    answer = kb.agent.ask("What is the main topic of my documents?", use_embeddings=True)
    
    report = kb.agent.generate_report("Summary of recent findings")