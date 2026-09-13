import os
import re
import sqlite3
import collections
from datetime import datetime
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Window:
    unit: str
    start: int
    end: int
    content: str

@dataclass
class Citation:
    document_id: str
    window: Window
    text_snippet: str

@dataclass
class Answer:
    text: str
    citations: List[Citation]
    report: str

@dataclass
class InvestigationNote:
    timestamp: datetime
    query: str
    answer: Answer
    durable_path: str

class Document:
    def __init__(self, path: Path, doc_id: str):
        self.path = path
        self.doc_id = doc_id
        self.ext = path.suffix.lower()
        self.metadata: Dict[str, Any] = {}
        self.tags: Set[str] = set()
        self.content: str = ""
        self.relations: List[str] = []

    def read_window(self, unit: str, start: int, end: int) -> Window:
        if unit == "lines":
            lines = self.content.split('\n')
            snippet = '\n'.join(lines[start:end])
        elif unit == "pages":
            lines = self.content.split('\n')
            snippet = '\n'.join(lines[start * 50:end * 50])
        elif unit == "sections":
            sections = re.split(r'\n##+ ', self.content)
            snippet = "\n\n".join(sections[start:end])
        elif unit == "archive_members":
            snippet = f"[Archive Member {start} to {end} from {self.path.name}]"
        elif unit == "table_slices":
            snippet = f"[Table Slice {start} to {end} from {self.path.name}]"
        else:
            snippet = self.content[:1000]
        return Window(unit=unit, start=start, end=end, content=snippet)

class Ingestor:
    SUPPORTED_TYPES = {
        'text': ['.txt'],
        'markdown': ['.md'],
        'pdf': ['.pdf'],
        'docx': ['.docx'],
        'image': ['.jpg', '.png', '.jpeg'],
        'spreadsheet': ['.csv', '.xlsx'],
        'log': ['.log'],
        'archive': ['.zip', '.tar', '.gz']
    }

    @staticmethod
    def ingest(path: Path, doc_id: str) -> Document:
        doc = Document(path, doc_id)
        ext = path.suffix.lower()
        
        if ext in Ingestor.SUPPORTED_TYPES['text'] or ext in Ingestor.SUPPORTED_TYPES['markdown'] or ext in Ingestor.SUPPORTED_TYPES['log']:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    doc.content = f.read()
            except Exception:
                doc.content = f"[Simulated text content for {path.name}]"
        else:
            doc.content = f"[Simulated extracted content for binary/complex format {ext}: {path.name}]"
        
        doc.metadata['ingested_at'] = datetime.now().isoformat()
        doc.metadata['size_bytes'] = os.path.getsize(path) if path.exists() else 0
        doc.metadata['format'] = ext
        
        return doc

class Catalog:
    def __init__(self, name: str):
        self.name = name
        self.document_ids: Set[str] = set()

    def add(self, doc_id: str):
        self.document_ids.add(doc_id)

class View:
    def __init__(self, name: str, query_tags: Set[str], query_ext: Optional[str] = None):
        self.name = name
        self.query_tags = query_tags
        self.query_ext = query_ext

    def filter(self, documents: Dict[str, Document]) -> List[Document]:
        results = []
        for doc in documents.values():
            if self.query_tags.issubset(doc.tags):
                if not self.query_ext or doc.ext == self.query_ext:
                    results.append(doc)
        return results

class Journal:
    def __init__(self, journal_dir: Path):
        self.journal_dir = journal_dir
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.entries: List[InvestigationNote] = []

    def add_entry(self, note: InvestigationNote):
        self.entries.append(note)
        file_path = self.journal_dir / f"note_{note.timestamp.strftime('%Y%m%d_%H%M%S')}.md"
        note.durable_path = str(file_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# Investigation Note: {note.timestamp}\n")
            f.write(f"## Query\n{note.query}\n")
            f.write(f"## Answer\n{note.answer.text}\n")
            f.write("## Citations\n")
            for c in note.answer.citations:
                f.write(f"- [{c.document_id}] ({c.window.unit} {c.window.start}-{c.window.end}): {c.text_snippet}\n")

class RelationMiner:
    @staticmethod
    def mine_relations(documents: Dict[str, Document]):
        doc_list = list(documents.values())
        for i in range(len(doc_list)):
            for j in range(i + 1, len(doc_list)):
                doc_a = doc_list[i]
                doc_b = doc_list[j]
                shared_tags = doc_a.tags.intersection(doc_b.tags)
                if len(shared_tags) > 0:
                    if doc_b.doc_id not in doc_a.relations:
                        doc_a.relations.append(doc_b.doc_id)
                    if doc_a.doc_id not in doc_b.relations:
                        doc_b.relations.append(doc_a.doc_id)

class SearchEngine:
    def __init__(self, db_path: Path, use_embeddings: bool = False, use_sqlite_vec: bool = False, use_reranking: bool = False):
        self.db_path = db_path
        self.use_embeddings = use_embeddings
        self.use_sqlite_vec = use_sqlite_vec
        self.use_reranking = use_reranking
        self.conn = sqlite3.connect(str(db_path))
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                content TEXT
            )
        ''')
        if self.use_sqlite_vec:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vec_documents (
                    doc_id TEXT PRIMARY KEY,
                    embedding BLOB
                )
            ''')
        self.conn.commit()

    def index_document(self, doc: Document):
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO documents (doc_id, content) VALUES (?, ?)', (doc.doc_id, doc.content))
        if self.use_sqlite_vec:
            dummy_embedding = b'\x00\x01\x02' 
            cursor.execute('INSERT OR REPLACE INTO vec_documents (doc_id, embedding) VALUES (?, ?)', (doc.doc_id, dummy_embedding))
        self.conn.commit()

    def lexical_search(self, query: str, documents: Dict[str, Document]) -> List[Document]:
        keywords = query.lower().split()
        results = []
        for doc in documents.values():
            score = sum(1 for kw in keywords if kw in doc.content.lower())
            if score > 0:
                results.append((score, doc))
        results.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in results]

    def vector_search(self, query: str, documents: Dict[str, Document]) -> List[Document]:
        return list(documents.values())[:5]

    def rerank(self, candidates: List[Document], query: str) -> List[Document]:
        if not self.use_reranking:
            return candidates
        return sorted(candidates, key=lambda d: len(d.tags), reverse=True)

    def apply_quotas(self, candidates: List[Document], source_quotas: Dict[str, int]) -> List[Document]:
        if not source_quotas:
            return candidates
        
        quota_counts = collections.defaultdict(int)
        filtered = []
        for doc in candidates:
            ext = doc.ext
            if ext in source_quotas:
                if quota_counts[ext] < source_quotas[ext]:
                    filtered.append(doc)
                    quota_counts[ext] += 1
            else:
                filtered.append(doc)
        return filtered

    def search(self, query: str, documents: Dict[str, Document], source_quotas: Optional[Dict[str, int]] = None) -> List[Document]:
        if self.use_embeddings or self.use_sqlite_vec:
            candidates = self.vector_search(query, documents)
        else:
            candidates = self.lexical_search(query, documents)
        
        candidates = self.rerank(candidates, query)
        if source_quotas:
            candidates = self.apply_quotas(candidates, source_quotas)
            
        return candidates

class Library:
    def __init__(self, root_folder: Path):
        self.root_folder = root_folder
        self.root_folder.mkdir(parents=True, exist_ok=True)
        self.documents: Dict[str, Document] = {}
        self.catalogs: Dict[str, Catalog] = {}
        self.views: Dict[str, View] = {}
        self.tags: Set[str] = set()
        
        self.db_path = self.root_folder / "marginalia.db"
        self.search_engine = SearchEngine(self.db_path, use_reranking=True)
        self.journal = Journal(self.root_folder / "journals")

    def add_document(self, path: Path, tags: Optional[List[str]] = None, catalog_name: str = "default") -> Document:
        doc_id = f"doc_{len(self.documents) + 1}"
        doc = Ingestor.ingest(path, doc_id)
        if tags:
            doc.tags.update(tags)
            self.tags.update(tags)
        
        self.documents[doc_id] = doc
        self.search_engine.index_document(doc)
        
        if catalog_name not in self.catalogs:
            self.catalogs[catalog_name] = Catalog(catalog_name)
        self.catalogs[catalog_name].add(doc_id)
        
        return doc

    def organize(self):
        RelationMiner.mine_relations(self.documents)

    def create_view(self, name: str, query_tags: Set[str], query_ext: Optional[str] = None):
        self.views[name] = View(name, query_tags, query_ext)

class Agent:
    def __init__(self, library: Library):
        self.library = library

    def read_sources(self, candidates: List[Document], query: str) -> List[Citation]:
        citations = []
        for doc in candidates:
            unit = "lines"
            if doc.ext in ['.zip', '.tar', '.gz']:
                unit = "archive_members"
            elif doc.ext in ['.csv', '.xlsx']:
                unit = "table_slices"
            elif doc.ext in ['.pdf', '.docx']:
                unit = "pages"
            elif doc.ext in ['.md']:
                unit = "sections"

            window = doc.read_window(unit, 0, 5)
            snippet = window.content[:200] + "..." if len(window.content) > 200 else window.content
            citations.append(Citation(document_id=doc.doc_id, window=window, text_snippet=snippet))
        return citations

    def generate_cited_answer(self, query: str, citations: List[Citation]) -> Answer:
        answer_text = f"Based on the provided sources, here is the investigation result for: '{query}'.\n\n"
        for i, cit in enumerate(citations):
            answer_text += f"According to {cit.document_id}, we observe relevant information [{i+1}]. "
        
        report = f"Report generated on {datetime.now().isoformat()}. Analyzed {len(citations)} sources."
        return Answer(text=answer_text, citations=citations, report=report)

    def investigate(self, query: str, source_quotas: Optional[Dict[str, int]] = None) -> Answer:
        candidates = self.library.search_engine.search(query, self.library.documents, source_quotas)
        citations = self.read_sources(candidates, query)
        answer = self.generate_cited_answer(query, citations)
        
        note = InvestigationNote(
            timestamp=datetime.now(),
            query=query,
            answer=answer,
            durable_path=""
        )
        self.library.journal.add_entry(note)
        
        return answer

if __name__ == "__main__":
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "my_knowledge_base"
        lib = Library(root)
        
        doc1_path = root / "notes.md"
        doc1_path.parent.mkdir(parents=True, exist_ok=True)
        with open(doc1_path, "w") as f:
            f.write("# Project Alpha\n\nThis is a secret project about AI agents.\n\n## Goals\n\nBuild a local-first system.")
            
        doc2_path = root / "data.csv"
        with open(doc2_path, "w") as f:
            f.write("id,value\n1,100\n2,200")
            
        doc3_path = root / "manual.pdf"
        with open(doc3_path, "w") as f:
            f.write("dummy pdf content")
            
        lib.add_document(doc1_path, tags=["ai", "project"], catalog_name="work")
        lib.add_document(doc2_path, tags=["data"], catalog_name="work")
        lib.add_document(doc3_path, tags=["reference"], catalog_name="personal")
        
        lib.organize()
        lib.create_view("work_ai", query_tags={"ai"}, query_ext=".md")
        
        agent = Agent(lib)
        
        quotas = {".md": 1, ".csv": 1}
        answer = agent.investigate("What is Project Alpha about AI?", source_quotas=quotas)