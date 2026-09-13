import os
import sqlite3
import json
import datetime
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Metadata:
    catalog: str = "default"
    tags: List[str] = field(default_factory=list)
    relations: List[str] = field(default_factory=list)
    custom: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Document:
    filepath: str
    content: str
    doc_type: str
    metadata: Metadata = field(default_factory=Metadata)

class Ingester:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)

    def ingest_file(self, filepath: Path) -> Document:
        ext = filepath.suffix.lower()
        doc_type = self._determine_type(ext)
        content = self._extract_content(filepath, doc_type)
        return Document(filepath=str(filepath), content=content, doc_type=doc_type)

    def _determine_type(self, ext: str) -> str:
        if ext in ['.txt']: return 'text'
        if ext in ['.md']: return 'markdown'
        if ext in ['.pdf']: return 'pdf'
        if ext in ['.docx']: return 'docx'
        if ext in ['.png', '.jpg', '.jpeg']: return 'image'
        if ext in ['.csv', '.xlsx']: return 'spreadsheet'
        if ext in ['.log']: return 'log'
        if ext in ['.zip', '.tar', '.gz']: return 'archive'
        return 'unknown'

    def _extract_content(self, filepath: Path, doc_type: str) -> str:
        if doc_type in ['text', 'markdown', 'log', 'spreadsheet']:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                return f"[Extracted content for {doc_type} at {filepath}]"
        else:
            return f"[Extracted binary/complex content for {doc_type} at {filepath}]"

class Organizer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._setup_db()

    def _setup_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS documents (
                            filepath TEXT PRIMARY KEY,
                            folder TEXT,
                            catalog TEXT,
                            content TEXT,
                            doc_type TEXT,
                            metadata JSON
                          )''')
        cursor.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                            filepath, content, content='documents', content_rowid='rowid'
                          )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS tags (
                            filepath TEXT,
                            tag TEXT,
                            UNIQUE(filepath, tag)
                          )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS journals (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT,
                            entry TEXT
                          )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS views (
                            name TEXT PRIMARY KEY,
                            query TEXT
                          )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS relations (
                            source TEXT,
                            target TEXT,
                            relation_type TEXT
                          )''')
        self.conn.commit()

    def add_document(self, doc: Document):
        cursor = self.conn.cursor()
        folder = str(Path(doc.filepath).parent)
        metadata_json = json.dumps(doc.metadata.custom)
        cursor.execute('''INSERT OR REPLACE INTO documents (filepath, folder, catalog, content, doc_type, metadata)
                          VALUES (?, ?, ?, ?, ?, ?)''',
                       (doc.filepath, folder, doc.metadata.catalog, doc.content, doc.doc_type, metadata_json))
        cursor.execute('''INSERT INTO documents_fts (rowid, filepath, content)
                          VALUES (last_insert_rowid(), ?, ?)''', (doc.filepath, doc.content))
        for tag in doc.metadata.tags:
            cursor.execute('INSERT OR IGNORE INTO tags (filepath, tag) VALUES (?, ?)', (doc.filepath, tag))
        self.conn.commit()

    def write_journal(self, entry: str):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO journals (timestamp, entry) VALUES (?, ?)',
                       (datetime.datetime.now().isoformat(), entry))
        self.conn.commit()

    def mine_relations(self):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM relations')
        cursor.execute('''INSERT INTO relations (source, target, relation_type)
                          SELECT a.filepath, b.filepath, 'shared_tag'
                          FROM tags a JOIN tags b ON a.tag = b.tag AND a.filepath != b.filepath''')
        self.conn.commit()

    def create_view(self, name: str, query: str):
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO views (name, query) VALUES (?, ?)', (name, query))
        self.conn.commit()

class Searcher:
    def __init__(self, organizer: Organizer):
        self.organizer = organizer

    def search(self, query: str, use_embeddings: bool = False, use_sqlite_vec: bool = False,
               rerank: bool = False, quota: int = 5) -> List[Document]:
        cursor = self.organizer.conn.cursor()
        
        if use_embeddings or use_sqlite_vec:
            cursor.execute('''SELECT filepath, content, doc_type, catalog, metadata 
                              FROM documents LIMIT ?''', (quota,))
        else:
            cursor.execute('''SELECT d.filepath, d.content, d.doc_type, d.catalog, d.metadata
                              FROM documents d
                              JOIN documents_fts fts ON d.filepath = fts.filepath
                              WHERE documents_fts MATCH ?
                              LIMIT ?''', (query, quota))
        
        results = cursor.fetchall()
        docs = []
        for row in results:
            filepath, content, doc_type, catalog, metadata_json = row
            meta = Metadata(catalog=catalog, custom=json.loads(metadata_json))
            cursor.execute('SELECT tag FROM tags WHERE filepath = ?', (filepath,))
            meta.tags = [t[0] for t in cursor.fetchall()]
            docs.append(Document(filepath=filepath, content=content, doc_type=doc_type, metadata=meta))
        
        if rerank:
            docs.sort(key=lambda d: len(d.content), reverse=True)
            
        return docs[:quota]

class Reader:
    def read_window(self, doc: Document, window_type: str, target: str = "") -> str:
        if window_type == "lines":
            lines = doc.content.split('\n')
            try:
                start, end = map(int, target.split('-'))
                return '\n'.join(lines[start:end])
            except ValueError:
                return doc.content[:500]
        elif window_type == "pages":
            pages = doc.content.split('\f')
            if not pages or len(pages) == 1:
                pages = [doc.content[i:i+1000] for i in range(0, len(doc.content), 1000)]
            try:
                page_num = int(target)
                return pages[page_num] if page_num < len(pages) else pages[-1]
            except ValueError:
                return pages[0]
        elif window_type == "sections":
            sections = re.split(r'\n##+ ', doc.content)
            for sec in sections:
                if target.lower() in sec.lower():
                    return sec
            return sections[0]
        elif window_type == "archive_member":
            return f"[Extracted archive member {target} from {doc.filepath}]"
        elif window_type == "table_slice":
            return f"[Extracted table slice {target} from {doc.filepath}]"
        return doc.content

class Agent:
    def __init__(self, searcher: Searcher, reader: Reader, organizer: Organizer):
        self.searcher = searcher
        self.reader = reader
        self.organizer = organizer

    def generate_cited_answer(self, query: str, use_embeddings: bool = False, quota: int = 3) -> str:
        candidates = self.searcher.search(query, use_embeddings=use_embeddings, quota=quota)
        
        read_contents = []
        citations = []
        
        for i, doc in enumerate(candidates):
            window_type = "lines"
            target = "0-10"
            if doc.doc_type == "markdown":
                window_type = "sections"
                target = query.split()[0] if query else ""
            elif doc.doc_type == "pdf":
                window_type = "pages"
                target = "0"
            elif doc.doc_type == "archive":
                window_type = "archive_member"
                target = "readme.txt"
            elif doc.doc_type == "spreadsheet":
                window_type = "table_slice"
                target = "A1:C10"
                
            window_content = self.reader.read_window(doc, window_type, target)
            read_contents.append(f"Source [{i+1}] ({doc.filepath}): {window_content}")
            citations.append(f"[{i+1}] {doc.filepath}")

        answer = f"Report for query: '{query}'\n\n"
        if not candidates:
            answer += "No relevant information found in the knowledge base."
        else:
            answer += f"Based on the recalled windows, the documents contain relevant information regarding '{query}'. "
            answer += f"Specifically, Source [1] provides foundational context.\n\nCitations:\n" + "\n".join(citations)

        note = f"Durable Investigation Note for query '{query}':\n{answer}"
        self.organizer.write_journal(note)
        
        return answer

class Marginalia:
    def __init__(self, root_dir: str, db_path: str = "marginalia.db"):
        self.root_dir = root_dir
        self.organizer = Organizer(db_path)
        self.ingester = Ingester(root_dir)
        self.searcher = Searcher(self.organizer)
        self.reader = Reader()
        self.agent = Agent(self.searcher, self.reader, self.organizer)

    def ingest_directory(self):
        root_path = Path(self.root_dir)
        if not root_path.exists():
            root_path.mkdir(parents=True, exist_ok=True)
            
        for filepath in root_path.rglob('*'):
            if filepath.is_file():
                doc = self.ingester.ingest_file(filepath)
                self.organizer.add_document(doc)
        
        self.organizer.mine_relations()

    def ask(self, query: str, use_embeddings: bool = False, quota: int = 5) -> str:
        return self.agent.generate_cited_answer(query, use_embeddings=use_embeddings, quota=quota)