import os
import re
import csv
import json
import sqlite3
import zipfile
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable, Set, Tuple


@dataclass
class Document:
    filepath: str
    file_type: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)

    @property
    def doc_id(self) -> str:
        return self.filepath


@dataclass
class Window:
    doc_id: str
    window_type: str
    content: str
    citation: str


@dataclass
class InvestigationNote:
    timestamp: str
    query: str
    cited_answer: str
    sources: List[str]
    
    def to_document(self, notes_dir: Path) -> Document:
        filename = f"investigation_{self.timestamp.replace(':', '-')}.md"
        filepath = str(notes_dir / filename)
        content = f"# Query: {self.query}\n\n## Answer\n{self.cited_answer}\n\n## Sources\n" + "\n".join(self.sources)
        return Document(
            filepath=filepath,
            file_type="markdown",
            content=content,
            metadata={"type": "investigation_note", "timestamp": self.timestamp},
            tags={"journal", "investigation"}
        )


class Ingestor:
    SUPPORTED_EXTENSIONS = {
        "text": [".txt"],
        "markdown": [".md"],
        "pdf": [".pdf"],
        "docx": [".docx"],
        "image": [".png", ".jpg", ".jpeg"],
        "spreadsheet": [".csv", ".xlsx"],
        "log": [".log"],
        "archive": [".zip", ".tar"]
    }

    def ingest(self, filepath: str) -> Document:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        ext = path.suffix.lower()
        file_type = "unknown"
        for ftype, exts in self.SUPPORTED_EXTENSIONS.items():
            if ext in exts:
                file_type = ftype
                break

        content = self._extract_content(path, file_type)
        
        return Document(
            filepath=str(path),
            file_type=file_type,
            content=content,
            metadata={"ingested_at": datetime.now().isoformat(), "size": path.stat().st_size}
        )

    def _extract_content(self, path: Path, file_type: str) -> str:
        try:
            if file_type in ("text", "markdown", "log"):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            elif file_type == "spreadsheet" and path.suffix.lower() == ".csv":
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.reader(f)
                    return "\n".join([",".join(row) for row in reader])
            elif file_type == "archive" and path.suffix.lower() == ".zip":
                with zipfile.ZipFile(path, "r") as z:
                    return "\n".join(z.namelist())
            else:
                return f"[{file_type.upper()} content extracted via OCR/Parsing stub for {path.name}]"
        except Exception as e:
            return f"[Error extracting content: {str(e)}]"


class Library:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.root_path.mkdir(parents=True, exist_ok=True)
        
        self.notes_dir = self.root_path / ".marginalia_notes"
        self.notes_dir.mkdir(exist_ok=True)

        self.documents: Dict[str, Document] = {}
        self.catalogs: Dict[str, List[str]] = {}
        self.views: Dict[str, Callable[[Document], bool]] = {}
        self.journals: List[InvestigationNote] = []
        self.relations: Dict[str, List[str]] = {}
        
        self.db_path = self.root_path / "marginalia.db"
        self._init_db()

    def _init_db(self) -> None:
        self.conn = sqlite3.connect(str(self.db_path))
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_index (
                doc_id TEXT PRIMARY KEY,
                content TEXT,
                tags TEXT
            )
        """)
        self.conn.commit()

    def add_document(self, doc: Document) -> None:
        self.documents[doc.doc_id] = doc
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO search_index (doc_id, content, tags) VALUES (?, ?, ?)",
            (doc.doc_id, doc.content, ",".join(doc.tags))
        )
        self.conn.commit()
        self.mine_relations()

    def organize_in_catalog(self, catalog_name: str, doc_id: str) -> None:
        if doc_id not in self.documents:
            raise ValueError("Document not found in library.")
        if catalog_name not in self.catalogs:
            self.catalogs[catalog_name] = []
        if doc_id not in self.catalogs[catalog_name]:
            self.catalogs[catalog_name].append(doc_id)

    def add_tag(self, doc_id: str, tag: str) -> None:
        if doc_id in self.documents:
            self.documents[doc_id].tags.add(tag)
            self.add_document(self.documents[doc_id]) 

    def update_metadata(self, doc_id: str, metadata: Dict[str, Any]) -> None:
        if doc_id in self.documents:
            self.documents[doc_id].metadata.update(metadata)

    def create_view(self, view_name: str, filter_func: Callable[[Document], bool]) -> None:
        self.views[view_name] = filter_func

    def get_view(self, view_name: str) -> List[Document]:
        if view_name not in self.views:
            raise ValueError(f"View {view_name} does not exist.")
        return [doc for doc in self.documents.values() if self.views[view_name](doc)]

    def add_journal_entry(self, note: InvestigationNote) -> None:
        self.journals.append(note)
        doc = note.to_document(self.notes_dir)
        with open(doc.filepath, "w", encoding="utf-8") as f:
            f.write(doc.content)
        self.add_document(doc)

    def mine_relations(self) -> Dict[str, List[str]]:
        self.relations.clear()
        doc_list = list(self.documents.values())
        for i, doc_a in enumerate(doc_list):
            self.relations[doc_a.doc_id] = []
            for doc_b in doc_list[i+1:]:
                if doc_a.tags & doc_b.tags: 
                    self.relations[doc_a.doc_id].append(doc_b.doc_id)
                    if doc_b.doc_id not in self.relations:
                        self.relations[doc_b.doc_id] = []
                    self.relations[doc_b.doc_id].append(doc_a.doc_id)
        return self.relations


class SearchEngine:
    def __init__(self, library: Library):
        self.library = library

    def recall(
        self, 
        query: str, 
        method: str = "lexical", 
        use_embeddings: bool = False, 
        use_sqlite_vec: bool = False, 
        rerank: bool = False, 
        source_quota: int = 5
    ) -> List[Document]:
        
        candidates: List[Document] = []
        
        if method == "lexical" or not (use_embeddings or use_sqlite_vec):
            cursor = self.library.conn.cursor()
            search_term = f"%{query}%"
            cursor.execute(
                "SELECT doc_id FROM search_index WHERE content LIKE ? OR tags LIKE ?",
                (search_term, search_term)
            )
            results = cursor.fetchall()
            for row in results:
                doc_id = row[0]
                if doc_id in self.library.documents:
                    candidates.append(self.library.documents[doc_id])
        else:
            candidates = list(self.library.documents.values())

        if rerank:
            candidates.sort(key=lambda d: d.content.lower().count(query.lower()), reverse=True)

        return candidates[:source_quota]


class Reader:
    def read_window(self, doc: Document, window_type: str, target: str = "") -> Window:
        content_window = ""
        citation = f"{doc.filepath} [{window_type}: {target}]"

        if window_type == "section":
            sections = re.split(r'\n##+ ', doc.content)
            content_window = sections[0] 
            for sec in sections:
                if target.lower() in sec.lower():
                    content_window = sec
                    break
        elif window_type == "page":
            pages = doc.content.split("\n\x0c") 
            try:
                page_num = int(target)
                content_window = pages[page_num] if page_num < len(pages) else pages[-1]
            except ValueError:
                content_window = pages[0]
        elif window_type == "line":
            lines = doc.content.split("\n")
            try:
                start, end = map(int, target.split("-"))
                content_window = "\n".join(lines[start:end])
            except ValueError:
                content_window = "\n".join(lines[:10])
        elif window_type == "archive_member":
            if target in doc.content:
                content_window = f"Archive member {target} found in {doc.filepath}"
            else:
                content_window = f"Archive member {target} not found."
        elif window_type == "table_slice":
            rows = doc.content.split("\n")
            try:
                start, end = map(int, target.split("-"))
                content_window = "\n".join(rows[start:end])
            except ValueError:
                content_window = "\n".join(rows[:5])
        else:
            content_window = doc.content[:1000] 

        return Window(
            doc_id=doc.doc_id,
            window_type=window_type,
            content=content_window,
            citation=citation
        )


class Agent:
    def __init__(self, library: Library, search_engine: SearchEngine, reader: Reader):
        self.library = library
        self.search_engine = search_engine
        self.reader = reader

    def investigate(self, query: str, source_quota: int = 5) -> str:
        candidates = self.search_engine.recall(
            query=query, 
            method="lexical", 
            rerank=True, 
            source_quota=source_quota
        )

        if not candidates:
            return "No relevant documents found in the library to answer the query."

        windows: List[Window] = []
        for doc in candidates:
            if doc.file_type == "spreadsheet":
                win = self.reader.read_window(doc, "table_slice", "0-5")
            elif doc.file_type == "archive":
                win = self.reader.read_window(doc, "archive_member", query)
            else:
                win = self.reader.read_window(doc, "line", "0-20")
            windows.append(win)

        cited_answer = f"Based on the investigation for '{query}':\n\n"
        sources_used = []
        
        for i, win in enumerate(windows, 1):
            cited_answer += f"According to [{i}], the relevant information is: {win.content.strip()[:200]}...\n"
            sources_used.append(f"[{i}] {win.citation}")

        cited_answer += "\nConclusion: The agent has synthesized the above windows into this report."

        note = InvestigationNote(
            timestamp=datetime.now().isoformat(),
            query=query,
            cited_answer=cited_answer,
            sources=sources_used
        )
        
        self.library.add_journal_entry(note)

        report = f"{cited_answer}\n\nSources:\n" + "\n".join(sources_used)
        return report