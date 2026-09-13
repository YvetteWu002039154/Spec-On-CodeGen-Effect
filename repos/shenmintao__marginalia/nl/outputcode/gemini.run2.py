import os
import re
import json
import sqlite3
import zipfile
import csv
import math
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Union, Tuple
from dataclasses import dataclass, field
from collections import Counter, defaultdict

@dataclass
class Metadata:
    author: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    source_type: str = "unknown"
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps({
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "source_type": self.source_type,
            "custom": self.custom
        })

    @classmethod
    def from_json(cls, data: str) -> 'Metadata':
        parsed = json.loads(data)
        return cls(
            author=parsed.get("author"),
            created_at=datetime.fromisoformat(parsed.get("created_at", datetime.now().isoformat())),
            source_type=parsed.get("source_type", "unknown"),
            custom=parsed.get("custom", {})
        )

@dataclass
class DocumentChunk:
    chunk_id: str
    doc_id: str
    content: str
    start_line: int
    end_line: int
    page_num: Optional[int] = None
    section_name: Optional[str] = None
    archive_member: Optional[str] = None
    is_table_slice: bool = False

@dataclass
class Document:
    doc_id: str
    filepath: str
    file_type: str
    content: str
    metadata: Metadata
    tags: Set[str] = field(default_factory=set)
    folder_path: str = "/"
    chunks: List[DocumentChunk] = field(default_factory=list)

@dataclass
class Relation:
    source_id: str
    target_id: str
    relation_type: str
    weight: float = 1.0

@dataclass
class CitedAnswer:
    query: str
    answer: str
    citations: List[DocumentChunk]
    generated_at: datetime = field(default_factory=datetime.now)

@dataclass
class Report:
    title: str
    summary: str
    detailed_answers: List[CitedAnswer]
    generated_at: datetime = field(default_factory=datetime.now)

class MarginaliaDB:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                filepath TEXT,
                file_type TEXT,
                content TEXT,
                metadata TEXT,
                folder_path TEXT
            );
            CREATE TABLE IF NOT EXISTS tags (
                doc_id TEXT,
                tag TEXT,
                PRIMARY KEY (doc_id, tag)
            );
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT,
                content TEXT,
                start_line INTEGER,
                end_line INTEGER,
                page_num INTEGER,
                section_name TEXT,
                archive_member TEXT,
                is_table_slice BOOLEAN
            );
            CREATE TABLE IF NOT EXISTS relations (
                source_id TEXT,
                target_id TEXT,
                relation_type TEXT,
                weight REAL,
                PRIMARY KEY (source_id, target_id, relation_type)
            );
            CREATE TABLE IF NOT EXISTS journal (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                answer TEXT,
                citations TEXT,
                timestamp TEXT
            );
        """)
        self.conn.commit()

class Journal:
    def __init__(self, db: MarginaliaDB):
        self.db = db

    def write_note(self, answer: CitedAnswer) -> None:
        cursor = self.db.conn.cursor()
        citations_json = json.dumps([c.chunk_id for c in answer.citations])
        cursor.execute(
            "INSERT INTO journal (query, answer, citations, timestamp) VALUES (?, ?, ?, ?)",
            (answer.query, answer.answer, citations_json, answer.generated_at.isoformat())
        )
        self.db.conn.commit()

    def get_history(self) -> List[Dict[str, Any]]:
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM journal ORDER BY timestamp DESC")
        return [dict(row) for row in cursor.fetchall()]

class Catalog:
    def __init__(self, db: MarginaliaDB):
        self.db = db

    def add_document(self, doc: Document) -> None:
        cursor = self.db.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO documents (doc_id, filepath, file_type, content, metadata, folder_path) VALUES (?, ?, ?, ?, ?, ?)",
            (doc.doc_id, doc.filepath, doc.file_type, doc.content, doc.metadata.to_json(), doc.folder_path)
        )
        cursor.execute("DELETE FROM tags WHERE doc_id = ?", (doc.doc_id,))
        for tag in doc.tags:
            cursor.execute("INSERT INTO tags (doc_id, tag) VALUES (?, ?)", (doc.doc_id, tag))
        
        cursor.execute("DELETE FROM chunks WHERE doc_id = ?", (doc.doc_id,))
        for chunk in doc.chunks:
            cursor.execute(
                """INSERT INTO chunks 
                   (chunk_id, doc_id, content, start_line, end_line, page_num, section_name, archive_member, is_table_slice) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (chunk.chunk_id, chunk.doc_id, chunk.content, chunk.start_line, chunk.end_line, 
                 chunk.page_num, chunk.section_name, chunk.archive_member, chunk.is_table_slice)
            )
        self.db.conn.commit()

    def get_document(self, doc_id: str) -> Optional[Document]:
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        cursor.execute("SELECT tag FROM tags WHERE doc_id = ?", (doc_id,))
        tags = {t["tag"] for t in cursor.fetchall()}
        
        cursor.execute("SELECT * FROM chunks WHERE doc_id = ?", (doc_id,))
        chunks = []
        for crow in cursor.fetchall():
            chunks.append(DocumentChunk(
                chunk_id=crow["chunk_id"],
                doc_id=crow["doc_id"],
                content=crow["content"],
                start_line=crow["start_line"],
                end_line=crow["end_line"],
                page_num=crow["page_num"],
                section_name=crow["section_name"],
                archive_member=crow["archive_member"],
                is_table_slice=bool(crow["is_table_slice"])
            ))
            
        return Document(
            doc_id=row["doc_id"],
            filepath=row["filepath"],
            file_type=row["file_type"],
            content=row["content"],
            metadata=Metadata.from_json(row["metadata"]),
            tags=tags,
            folder_path=row["folder_path"],
            chunks=chunks
        )

    def add_relation(self, relation: Relation) -> None:
        cursor = self.db.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO relations (source_id, target_id, relation_type, weight) VALUES (?, ?, ?, ?)",
            (relation.source_id, relation.target_id, relation.relation_type, relation.weight)
        )
        self.db.conn.commit()

class View:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog

    def filter(self, tags: Optional[Set[str]] = None, folder_prefix: Optional[str] = None) -> List[str]:
        cursor = self.catalog.db.conn.cursor()
        query = "SELECT DISTINCT d.doc_id FROM documents d"
        params = []
        
        if tags:
            query += " JOIN tags t ON d.doc_id = t.doc_id WHERE t.tag IN ({})".format(
                ",".join("?" * len(tags))
            )
            params.extend(list(tags))
            if folder_prefix:
                query += " AND d.folder_path LIKE ?"
                params.append(f"{folder_prefix}%")
        elif folder_prefix:
            query += " WHERE d.folder_path LIKE ?"
            params.append(f"{folder_prefix}%")
            
        cursor.execute(query, params)
        return [row["doc_id"] for row in cursor.fetchall()]

class RelationMiner:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog

    def mine_lexical_relations(self, threshold: float = 0.2) -> None:
        cursor = self.catalog.db.conn.cursor()
        cursor.execute("SELECT doc_id, content FROM documents")
        docs = cursor.fetchall()
        
        doc_words = {}
        for doc in docs:
            words = set(re.findall(r'\w+', doc["content"].lower()))
            doc_words[doc["doc_id"]] = words
            
        doc_ids = list(doc_words.keys())
        for i in range(len(doc_ids)):
            for j in range(i + 1, len(doc_ids)):
                id1, id2 = doc_ids[i], doc_ids[j]
                w1, w2 = doc_words[id1], doc_words[id2]
                if not w1 or not w2:
                    continue
                jaccard = len(w1.intersection(w2)) / len(w1.union(w2))
                if jaccard >= threshold:
                    self.catalog.add_relation(Relation(id1, id2, "lexical_similarity", jaccard))
                    self.catalog.add_relation(Relation(id2, id1, "lexical_similarity", jaccard))

class Chunker:
    @staticmethod
    def chunk_text(doc_id: str, text: str, lines_per_chunk: int = 50) -> List[DocumentChunk]:
        lines = text.split('\n')
        chunks = []
        for i in range(0, len(lines), lines_per_chunk):
            chunk_lines = lines[i:i+lines_per_chunk]
            chunk_content = '\n'.join(chunk_lines)
            chunks.append(DocumentChunk(
                chunk_id=f"{doc_id}_chunk_{i//lines_per_chunk}",
                doc_id=doc_id,
                content=chunk_content,
                start_line=i,
                end_line=i + len(chunk_lines) - 1
            ))
        return chunks

    @staticmethod
    def chunk_csv(doc_id: str, content: str, rows_per_slice: int = 20) -> List[DocumentChunk]:
        lines = content.split('\n')
        chunks = []
        header = lines[0] if lines else ""
        for i in range(1, len(lines), rows_per_slice):
            slice_lines = [header] + lines[i:i+rows_per_slice]
            chunks.append(DocumentChunk(
                chunk_id=f"{doc_id}_table_{i//rows_per_slice}",
                doc_id=doc_id,
                content='\n'.join(slice_lines),
                start_line=i,
                end_line=i + len(slice_lines) - 1,
                is_table_slice=True
            ))
        return chunks

class Ingestor:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog

    def ingest(self, filepath: str, folder_path: str = "/", tags: Optional[Set[str]] = None) -> Document:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Cannot ingest missing file: {filepath}")
            
        ext = os.path.splitext(filepath)[1].lower()
        doc_id = f"doc_{os.path.basename(filepath)}_{int(datetime.now().timestamp())}"
        
        content = ""
        chunks = []
        file_type = ext[1:] if ext else "unknown"
        
        if ext in ['.txt', '.md', '.log']:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            chunks = Chunker.chunk_text(doc_id, content)
            
        elif ext == '.csv':
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            chunks = Chunker.chunk_csv(doc_id, content)
            
        elif ext == '.zip':
            with zipfile.ZipFile(filepath, 'r') as z:
                for member in z.namelist():
                    if not member.endswith('/'):
                        with z.open(member) as mf:
                            member_content = mf.read().decode('utf-8', errors='ignore')
                            content += f"\n--- Archive Member: {member} ---\n{member_content}"
                            member_chunks = Chunker.chunk_text(doc_id, member_content)
                            for mc in member_chunks:
                                mc.archive_member = member
                                mc.chunk_id = f"{doc_id}_{member}_{mc.chunk_id}"
                            chunks.extend(member_chunks)
                            
        elif ext in ['.pdf', '.docx', '.jpg', '.png']:
            content = f"[{ext.upper()} Binary Content Placeholder for {filepath}]"
            chunks = [DocumentChunk(
                chunk_id=f"{doc_id}_meta",
                doc_id=doc_id,
                content=content,
                start_line=0,
                end_line=0
            )]
        else:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            chunks = Chunker.chunk_text(doc_id, content)

        doc = Document(
            doc_id=doc_id,
            filepath=filepath,
            file_type=file_type,
            content=content,
            metadata=Metadata(source_type=file_type),
            tags=tags or set(),
            folder_path=folder_path,
            chunks=chunks
        )
        self.catalog.add_document(doc)
        return doc

class SearchEngine:
    def __init__(self, catalog: Catalog, use_embeddings: bool = False):
        self.catalog = catalog
        self.use_embeddings = use_embeddings

    def _lexical_score(self, query: str, text: str) -> float:
        query_terms = set(re.findall(r'\w+', query.lower()))
        text_terms = re.findall(r'\w+', text.lower())
        if not query_terms or not text_terms:
            return 0.0
        
        term_counts = Counter(text_terms)
        score = sum(term_counts.get(q, 0) for q in query_terms)
        return score / (1 + math.log(len(text_terms)))

    def _mock_sqlite_vec_search(self, query: str) -> List[Tuple[float, DocumentChunk]]:
        cursor = self.catalog.db.conn.cursor()
        cursor.execute("SELECT * FROM chunks")
        results = []
        for row in cursor.fetchall():
            chunk = DocumentChunk(
                chunk_id=row["chunk_id"],
                doc_id=row["doc_id"],
                content=row["content"],
                start_line=row["start_line"],
                end_line=row["end_line"],
                page_num=row["page_num"],
                section_name=row["section_name"],
                archive_member=row["archive_member"],
                is_table_slice=bool(row["is_table_slice"])
            )
            score = self._lexical_score(query, chunk.content)
            if score > 0:
                results.append((score, chunk))
        return results

    def search(self, query: str, top_k: int = 10, max_per_source: int = 2) -> List[DocumentChunk]:
        if self.use_embeddings:
            scored_chunks = self._mock_sqlite_vec_search(query)
        else:
            scored_chunks = self._mock_sqlite_vec_search(query)
            
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        reranked = self._rerank(query, scored_chunks)
        return self._enforce_quotas(reranked, top_k, max_per_source)

    def _rerank(self, query: str, scored_chunks: List[Tuple[float, DocumentChunk]]) -> List[DocumentChunk]:
        return [chunk for score, chunk in scored_chunks]

    def _enforce_quotas(self, chunks: List[DocumentChunk], top_k: int, max_per_source: int) -> List[DocumentChunk]:
        source_counts = defaultdict(int)
        final_results = []
        
        for chunk in chunks:
            if len(final_results) >= top_k:
                break
            if source_counts[chunk.doc_id] < max_per_source:
                final_results.append(chunk)
                source_counts[chunk.doc_id] += 1
                
        return final_results

class Reader:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog

    def read_window(self, chunk: DocumentChunk, context_lines: int = 5) -> str:
        doc = self.catalog.get_document(chunk.doc_id)
        if not doc:
            return chunk.content
            
        if chunk.is_table_slice or chunk.archive_member:
            return chunk.content
            
        lines = doc.content.split('\n')
        start = max(0, chunk.start_line - context_lines)
        end = min(len(lines), chunk.end_line + context_lines + 1)
        
        window_content = '\n'.join(lines[start:end])
        return f"--- Source: {doc.filepath} (Lines {start}-{end}) ---\n{window_content}"

class Agent:
    def __init__(self, search_engine: SearchEngine, reader: Reader, journal: Journal):
        self.search_engine = search_engine
        self.reader = reader
        self.journal = journal

    def _generate_llm_response(self, query: str, context: str) -> str:
        return f"Based on the provided context, here is the synthesized answer for: '{query}'.\n\nContext Summary:\n{context[:500]}..."

    def investigate(self, query: str) -> CitedAnswer:
        candidates = self.search_engine.search(query, top_k=5, max_per_source=2)
        
        windows = []
        for chunk in candidates:
            windows.append(self.reader.read_window(chunk))
            
        full_context = "\n\n".join(windows)
        
        answer_text = self._generate_llm_response(query, full_context)
        
        cited_answer = CitedAnswer(
            query=query,
            answer=answer_text,
            citations=candidates
        )
        
        self.journal.write_note(cited_answer)
        return cited_answer

    def generate_report(self, title: str, queries: List[str]) -> Report:
        answers = []
        for q in queries:
            answers.append(self.investigate(q))
            
        summary = f"Report covering {len(queries)} investigation topics."
        return Report(
            title=title,
            summary=summary,
            detailed_answers=answers
        )

if __name__ == "__main__":
    db = MarginaliaDB(":memory:")
    catalog = Catalog(db)
    journal = Journal(db)
    ingestor = Ingestor(catalog)
    search_engine = SearchEngine(catalog, use_embeddings=False)
    reader = Reader(catalog)
    agent = Agent(search_engine, reader, journal)
    miner = RelationMiner(catalog)
    view = View(catalog)

    with open("sample_research.txt", "w") as f:
        f.write("The library science approach to personal knowledge management emphasizes metadata.\n" * 10)
        f.write("LLM agents can utilize this metadata to provide better cited answers.\n" * 10)
        
    with open("sample_data.csv", "w") as f:
        f.write("id,name,value\n1,test,100\n2,demo,200\n")

    ingestor.ingest("sample_research.txt", folder_path="/research", tags={"pkm", "llm"})
    ingestor.ingest("sample_data.csv", folder_path="/data", tags={"csv"})

    miner.mine_lexical_relations()

    answer = agent.investigate("How do LLM agents use library science metadata?")
    
    report = agent.generate_report("PKM and LLMs", [
        "What is the library science approach?",
        "What data is in the CSV?"
    ])

    os.remove("sample_research.txt")
    os.remove("sample_data.csv")