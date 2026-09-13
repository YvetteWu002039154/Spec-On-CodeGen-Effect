import os
import json
import sqlite3
import datetime
import zipfile
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union, Set, Callable
from pathlib import Path
from collections import Counter
import math

# --- Core Data Models ---

@dataclass
class Metadata:
    title: str
    author: Optional[str] = None
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    modified_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    custom_fields: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Tag:
    name: str
    description: Optional[str] = None

    def __hash__(self):
        return hash(self.name)

@dataclass
class Document:
    id: str
    file_path: Path
    content: str
    metadata: Metadata
    tags: Set[Tag] = field(default_factory=set)
    file_type: str = "text"

@dataclass
class Folder:
    name: str
    path: Path
    documents: List[Document] = field(default_factory=list)
    subfolders: List['Folder'] = field(default_factory=list)

@dataclass
class View:
    name: str
    query_filter: Callable[[Document], bool]

@dataclass
class InvestigationNote:
    id: str
    timestamp: datetime.datetime
    query: str
    summary: str
    cited_document_ids: List[str]

@dataclass
class CitedAnswer:
    answer: str
    citations: List[Dict[str, Any]]

@dataclass
class Report:
    title: str
    sections: List[CitedAnswer]
    generated_at: datetime.datetime = field(default_factory=datetime.datetime.now)

# --- Ingestion Engine ---

class IngestionEngine:
    def __init__(self):
        self.supported_extensions = {
            '.txt': self._ingest_text,
            '.md': self._ingest_markdown,
            '.pdf': self._ingest_pdf,
            '.docx': self._ingest_docx,
            '.png': self._ingest_image,
            '.jpg': self._ingest_image,
            '.xlsx': self._ingest_spreadsheet,
            '.csv': self._ingest_spreadsheet,
            '.log': self._ingest_log,
            '.zip': self._ingest_archive
        }

    def ingest(self, file_path: Union[str, Path]) -> Document:
        path = Path(file_path)
        ext = path.suffix.lower()
        
        doc_id = str(hash(path.absolute()))
        metadata = Metadata(title=path.stem)
        
        if not path.exists():
            return Document(id=doc_id, file_path=path, content=f"[Simulated content for {path.name}]", metadata=metadata, file_type=ext)

        if ext in self.supported_extensions:
            content, file_type = self.supported_extensions[ext](path)
        else:
            content, file_type = self._ingest_text(path)

        return Document(
            id=doc_id,
            file_path=path,
            content=content,
            metadata=metadata,
            file_type=file_type
        )

    def _ingest_text(self, path: Path) -> tuple[str, str]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read(), "text"
        except Exception:
            return "[Unreadable Text Content]", "text"

    def _ingest_markdown(self, path: Path) -> tuple[str, str]:
        content, _ = self._ingest_text(path)
        return content, "markdown"

    def _ingest_pdf(self, path: Path) -> tuple[str, str]:
        return f"[Extracted PDF Text from {path.name}]", "pdf"

    def _ingest_docx(self, path: Path) -> tuple[str, str]:
        return f"[Extracted DOCX Text from {path.name}]", "docx"

    def _ingest_image(self, path: Path) -> tuple[str, str]:
        return f"[OCR Extracted Text from Image {path.name}]", "image"

    def _ingest_spreadsheet(self, path: Path) -> tuple[str, str]:
        return f"[Extracted Spreadsheet Data from {path.name}]", "spreadsheet"

    def _ingest_log(self, path: Path) -> tuple[str, str]:
        content, _ = self._ingest_text(path)
        return content, "log"

    def _ingest_archive(self, path: Path) -> tuple[str, str]:
        content = []
        try:
            with zipfile.ZipFile(path, 'r') as z:
                for info in z.infolist():
                    content.append(f"Archive Member: {info.filename}")
        except zipfile.BadZipFile:
            content.append("[Invalid Archive]")
        return "\n".join(content), "archive"

# --- Organization & Storage ---

class Journal:
    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS investigation_notes (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                query TEXT,
                summary TEXT,
                cited_document_ids TEXT
            )
        ''')
        self.conn.commit()

    def add_note(self, note: InvestigationNote):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO investigation_notes (id, timestamp, query, summary, cited_document_ids)
            VALUES (?, ?, ?, ?, ?)
        ''', (note.id, note.timestamp.isoformat(), note.query, note.summary, json.dumps(note.cited_document_ids)))
        self.conn.commit()

    def get_history(self) -> List[InvestigationNote]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, timestamp, query, summary, cited_document_ids FROM investigation_notes ORDER BY timestamp DESC')
        rows = cursor.fetchall()
        return [
            InvestigationNote(
                id=row[0],
                timestamp=datetime.datetime.fromisoformat(row[1]),
                query=row[2],
                summary=row[3],
                cited_document_ids=json.loads(row[4])
            ) for row in rows
        ]

class RelationMiner:
    def mine_relations(self, documents: List[Document]) -> Dict[str, List[str]]:
        relations = {}
        for doc in documents:
            related = []
            for other in documents:
                if doc.id == other.id:
                    continue
                if doc.tags & other.tags:
                    related.append(other.id)
            relations[doc.id] = related
        return relations

class Catalog:
    def __init__(self):
        self.root_folder = Folder(name="root", path=Path("/"))
        self.documents: Dict[str, Document] = {}
        self.views: Dict[str, View] = {}
        self.journal = Journal()
        self.relation_miner = RelationMiner()
        self.relations: Dict[str, List[str]] = {}

    def add_document(self, document: Document, folder_path: str = "/"):
        self.documents[document.id] = document
        target_folder = self._get_or_create_folder(folder_path)
        target_folder.documents.append(document)
        self.relations = self.relation_miner.mine_relations(list(self.documents.values()))

    def _get_or_create_folder(self, path_str: str) -> Folder:
        if path_str == "/":
            return self.root_folder
        
        parts = [p for p in path_str.split("/") if p]
        current = self.root_folder
        
        for part in parts:
            found = next((f for f in current.subfolders if f.name == part), None)
            if not found:
                new_folder = Folder(name=part, path=current.path / part)
                current.subfolders.append(new_folder)
                current = new_folder
            else:
                current = found
        return current

    def add_view(self, view: View):
        self.views[view.name] = view

    def get_view_results(self, view_name: str) -> List[Document]:
        if view_name not in self.views:
            return []
        view = self.views[view_name]
        return [doc for doc in self.documents.values() if view.query_filter(doc)]

# --- Recall & Search ---

@dataclass
class SearchResult:
    document: Document
    score: float
    snippet: str

class SearchEngine:
    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path)
        self._init_vec_db()

    def _init_vec_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_embeddings (
                id TEXT PRIMARY KEY,
                embedding BLOB
            )
        ''')
        self.conn.commit()

    def _lexical_search(self, query: str, documents: List[Document]) -> List[SearchResult]:
        query_terms = set(re.findall(r'\w+', query.lower()))
        results = []
        for doc in documents:
            content_lower = doc.content.lower()
            doc_terms = re.findall(r'\w+', content_lower)
            term_counts = Counter(doc_terms)
            
            score = sum(term_counts[term] for term in query_terms)
            if score > 0:
                snippet_start = max(0, content_lower.find(list(query_terms)[0]) - 30)
                snippet = doc.content[snippet_start:snippet_start+100] + "..."
                results.append(SearchResult(document=doc, score=float(score), snippet=snippet))
        return results

    def _embedding_search(self, query: str, documents: List[Document]) -> List[SearchResult]:
        results = []
        for doc in documents:
            score = len(set(query.lower().split()) & set(doc.content.lower().split())) * 1.5 
            if score > 0:
                results.append(SearchResult(document=doc, score=score, snippet=doc.content[:100]))
        return results

    def _rerank(self, results: List[SearchResult], query: str) -> List[SearchResult]:
        for res in results:
            if query.lower() in res.document.metadata.title.lower():
                res.score += 10.0
        return sorted(results, key=lambda x: x.score, reverse=True)

    def search(self, 
               query: str, 
               catalog: Catalog, 
               use_embeddings: bool = False, 
               rerank: bool = True, 
               quota: int = 5) -> List[SearchResult]:
        
        docs = list(catalog.documents.values())
        
        if use_embeddings:
            results = self._embedding_search(query, docs)
        else:
            results = self._lexical_search(query, docs)
            
        if rerank:
            results = self._rerank(results, query)
            
        return results[:quota]

# --- Reading ---

class DocumentReader:
    @staticmethod
    def read_lines(document: Document, start_line: int, end_line: int) -> str:
        lines = document.content.splitlines()
        return "\n".join(lines[start_line:end_line])

    @staticmethod
    def read_section(document: Document, section_header: str) -> str:
        pattern = re.compile(rf"(?i)^{re.escape(section_header)}.*?(?=^#|\Z)", re.MULTILINE | re.DOTALL)
        match = pattern.search(document.content)
        return match.group(0) if match else ""

    @staticmethod
    def read_page(document: Document, page_number: int, chars_per_page: int = 3000) -> str:
        start = (page_number - 1) * chars_per_page
        end = start + chars_per_page
        return document.content[start:end]

    @staticmethod
    def read_archive_member(document: Document, member_name: str) -> str:
        if document.file_type != "archive":
            return ""
        if member_name in document.content:
            return f"[Content of {member_name} from archive]"
        return ""

    @staticmethod
    def read_table_slice(document: Document, row_start: int, row_end: int) -> str:
        if document.file_type not in ["spreadsheet", "csv"]:
            return ""
        lines = document.content.splitlines()
        return "\n".join(lines[row_start:row_end])

    @staticmethod
    def extract_best_window(document: Document, query: str) -> str:
        query_terms = query.lower().split()
        lines = document.content.splitlines()
        best_window = ""
        max_score = -1
        
        window_size = 20
        for i in range(max(1, len(lines) - window_size + 1)):
            window = "\n".join(lines[i:i+window_size])
            score = sum(1 for term in query_terms if term in window.lower())
            if score > max_score:
                max_score = score
                best_window = window
                
        return best_window if max_score > 0 else document.content[:500]

# --- Production (LLM Agent) ---

class Agent:
    def __init__(self, catalog: Catalog, search_engine: SearchEngine):
        self.catalog = catalog
        self.search_engine = search_engine
        self.reader = DocumentReader()

    def _simulate_llm_generation(self, prompt: str, context: List[Dict[str, Any]]) -> str:
        citations_text = "\n".join([f"[{i+1}] {c['title']}: {c['window'][:50]}..." for i, c in enumerate(context)])
        return f"Based on the provided documents, here is the synthesized answer to your query.\n\nCitations used:\n{citations_text}"

    def answer_query(self, query: str, use_embeddings: bool = False, quota: int = 3) -> CitedAnswer:
        search_results = self.search_engine.search(
            query=query, 
            catalog=self.catalog, 
            use_embeddings=use_embeddings, 
            quota=quota
        )

        context = []
        cited_ids = []
        for res in search_results:
            window = self.reader.extract_best_window(res.document, query)
            context.append({
                "id": res.document.id,
                "title": res.document.metadata.title,
                "window": window
            })
            cited_ids.append(res.document.id)

        prompt = f"Query: {query}\nContext: {json.dumps(context)}"
        answer_text = self._simulate_llm_generation(prompt, context)

        cited_answer = CitedAnswer(answer=answer_text, citations=context)

        note = InvestigationNote(
            id=f"inv_{int(datetime.datetime.now().timestamp())}",
            timestamp=datetime.datetime.now(),
            query=query,
            summary=answer_text[:100] + "...",
            cited_document_ids=cited_ids
        )
        self.catalog.journal.add_note(note)

        return cited_answer

    def generate_report(self, title: str, queries: List[str]) -> Report:
        sections = []
        for query in queries:
            sections.append(self.answer_query(query))
        
        return Report(title=title, sections=sections)

# --- Example Usage / System Initialization ---

if __name__ == "__main__":
    # 1. Initialize System Components
    ingestion_engine = IngestionEngine()
    catalog = Catalog()
    search_engine = SearchEngine()
    agent = Agent(catalog=catalog, search_engine=search_engine)

    # 2. Ingest Documents
    doc1 = ingestion_engine.ingest("research_notes.md")
    doc1.content = "The library science approach emphasizes metadata and cataloging. Lexical search is fast but embeddings capture semantics."
    doc1.tags.add(Tag("research"))
    
    doc2 = ingestion_engine.ingest("financials.xlsx")
    doc2.content = "Q1 Revenue: $5000\nQ2 Revenue: $7000\nQ3 Revenue: $8000"
    doc2.tags.add(Tag("finance"))

    doc3 = ingestion_engine.ingest("archive.zip")
    
    catalog.add_document(doc1, folder_path="/projects/marginalia")
    catalog.add_document(doc2, folder_path="/finance/2023")
    catalog.add_document(doc3, folder_path="/backups")

    # 3. Create a View
    research_view = View(name="Research Docs", query_filter=lambda d: Tag("research") in d.tags)
    catalog.add_view(research_view)

    # 4. Agent answers a query
    print("--- Agent Answering Query ---")
    answer = agent.answer_query("What is the library science approach?", use_embeddings=False, quota=2)
    print(answer.answer)
    print("\nCitations:")
    for c in answer.citations:
        print(f"- {c['title']}: {c['window']}")

    # 5. Agent generates a report
    print("\n--- Agent Generating Report ---")
    report = agent.generate_report("Marginalia Overview", ["library science", "Q1 Revenue"])
    print(f"Report Title: {report.title}")
    print(f"Generated at: {report.generated_at}")
    print(f"Sections generated: {len(report.sections)}")

    # 6. Check Journal History
    print("\n--- Journal History ---")
    history = catalog.journal.get_history()
    for note in history:
        print(f"[{note.timestamp}] Query: '{note.query}' -> Cited Docs: {note.cited_document_ids}")

    # 7. Test Document Reader specific windows
    print("\n--- Document Reader Tests ---")
    table_slice = DocumentReader.read_table_slice(doc2, row_start=0, row_end=2)
    print(f"Table Slice (Rows 0-2):\n{table_slice}")