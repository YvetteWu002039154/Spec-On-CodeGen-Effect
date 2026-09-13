import os
import re
import json
import uuid
import shutil
import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set, Tuple, Any, Union
from collections import defaultdict
from pathlib import Path

# -------------------------------------------------------------------
# Minimal placeholder for external dependencies (not actually used)
# -------------------------------------------------------------------
class FakeSqliteVec:
    """Simulated sqlite-vec for optional embeddings."""
    pass

class FakeEmbedder:
    """Simulated embedding model."""
    def encode(self, text: str) -> List[float]:
        return [0.0] * 128

# -------------------------------------------------------------------
# Document & Metadata
# -------------------------------------------------------------------
@dataclass
class Metadata:
    author: str = ""
    created: str = ""          # ISO format
    modified: str = ""
    size: int = 0
    title: str = ""
    description: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def update(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                self.extra[k] = v

    def to_dict(self) -> Dict:
        d = asdict(self)
        del d["extra"]
        d.update(self.extra)
        return d

class Document:
    """Represents an ingested file or logical unit."""
    def __init__(self, path: str, title: str = "", content: str = "",
                 metadata: Optional[Metadata] = None,
                 tags: Optional[List[str]] = None,
                 journal_entries: Optional[List[str]] = None):
        self.id: str = str(uuid.uuid4())
        self.path: str = os.path.abspath(path)
        self.title: str = title or os.path.basename(path)
        self.content: str = content
        self.metadata: Metadata = metadata or Metadata()
        self.tags: List[str] = tags or []
        self.folder: str = os.path.dirname(self.path)
        self.journal: List[str] = journal_entries or []   # investigation note ids

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        if tag in self.tags:
            self.tags.remove(tag)

    def update_metadata(self, **kwargs) -> None:
        self.metadata.update(**kwargs)

    def get_section(self, section_id: int) -> str:
        """Return content of a section if available (simulated by splitting on ## headings)."""
        sections = re.split(r'(^## .*$)', self.content, flags=re.MULTILINE)
        # Naive: return full if no sections, else try to get by index
        if len(sections) == 1:
            return self.content
        try:
            # Join section header with its content
            if 0 <= section_id < len(sections):
                return sections[section_id]
        except IndexError:
            return ""
        return ""

    def get_page(self, page_num: int, page_size: int = 50) -> str:
        """Simulate page extraction by splitting content into lines and grouping."""
        lines = self.content.splitlines()
        start = (page_num - 1) * page_size
        end = start + page_size
        return "\n".join(lines[start:end])

    def get_lines(self, start_line: int, end_line: int) -> str:
        """Return lines [start_line, end_line) 1-indexed."""
        lines = self.content.splitlines()
        start = max(0, start_line - 1)
        end = min(len(lines), end_line)
        return "\n".join(lines[start:end])

    def get_archive_member(self, member_name: str) -> str:
        """For archive documents (simulated), return member content if stored."""
        # Not implemented in this stub; assumes archives are expanded during ingestion.
        return ""

    def get_table_slice(self, rows: Optional[Tuple[int, int]] = None,
                        cols: Optional[Tuple[int, int]] = None) -> str:
        """Simulate spreadsheet table slice (CSV-like)."""
        # Assumes content stored as CSV text
        lines = self.content.splitlines()
        if not lines:
            return ""
        header = lines[0]
        rows_data = lines[1:]
        if rows:
            r_start, r_end = rows
            rows_data = rows_data[r_start-1:r_end]  # 1-indexed
        if cols:
            c_start, c_end = cols
            result_lines = []
            for line in rows_data:
                fields = line.split(',')
                trimmed = fields[c_start-1:c_end]
                result_lines.append(','.join(trimmed))
            result = header + "\n" + "\n".join(result_lines) if cols else "\n".join(rows_data)
        else:
            result = self.content
        return result

# -------------------------------------------------------------------
# Index & Search
# -------------------------------------------------------------------
class LexicalIndex:
    """Simple in-memory inverted index for lexical search."""
    def __init__(self):
        self._index: Dict[str, Set[str]] = defaultdict(set)   # token -> doc ids
        self._documents: Dict[str, Document] = {}

    def add_document(self, doc: Document) -> None:
        self._documents[doc.id] = doc
        tokens = self._tokenize(doc.content)
        for token in tokens:
            self._index[token].add(doc.id)

    def remove_document(self, doc_id: str) -> None:
        if doc_id in self._documents:
            doc = self._documents[doc_id]
            tokens = self._tokenize(doc.content)
            for token in tokens:
                if doc_id in self._index[token]:
                    self._index[token].remove(doc_id)
                    if not self._index[token]:
                        del self._index[token]
            del self._documents[doc_id]

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\b\w+\b', text.lower())

    def search(self, query: str) -> List[Tuple[Document, float]]:
        """Return documents sorted by TF-IDF-like score (simplified)."""
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        scores: Dict[str, float] = defaultdict(float)
        for token in set(query_tokens):
            if token in self._index:
                for doc_id in self._index[token]:
                    scores[doc_id] += 1.0 / (1 + len(self._documents[doc_id].content))  # dummy score
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = [(self._documents[doc_id], score) for doc_id, score in sorted_docs]
        return results

class EmbeddingIndex:
    """Optional embeddings index (simulated)."""
    def __init__(self, embedder: Optional[FakeEmbedder] = None):
        self.embedder = embedder or FakeEmbedder()
        self._doc_embeddings: Dict[str, List[float]] = {}
        self._documents: Dict[str, Document] = {}

    def add_document(self, doc: Document) -> None:
        self._documents[doc.id] = doc
        self._doc_embeddings[doc.id] = self.embedder.encode(doc.content)

    def remove_document(self, doc_id: str) -> None:
        self._doc_embeddings.pop(doc_id, None)
        self._documents.pop(doc_id, None)

    def search(self, query: str, top_k: int = 10) -> List[Tuple[Document, float]]:
        query_emb = self.embedder.encode(query)
        scores = []
        for doc_id, emb in self._doc_embeddings.items():
            # cosine similarity (simplified: dot product assuming unit vectors)
            sim = sum(a * b for a, b in zip(query_emb, emb))
            scores.append((self._documents[doc_id], sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

class Reranker:
    """Simple re-ranker that adjusts scores based on document recency or length (placeholder)."""
    def rerank(self, candidates: List[Tuple[Document, float]], query: str) -> List[Tuple[Document, float]]:
        # Just return unchanged; in real life could use cross-encoder.
        return candidates

class Searcher:
    """Unifies lexical, embedding, and reranking search with source quotas."""
    def __init__(self, lexical_index: LexicalIndex, embedding_index: Optional[EmbeddingIndex] = None,
                 reranker: Optional[Reranker] = None):
        self.lexical = lexical_index
        self.embedding = embedding_index
        self.reranker = reranker or Reranker()

    def search(self, query: str, mode: str = "lexical", top_k: int = 10,
               use_rerank: bool = False, source_quotas: Optional[Dict[str, int]] = None) -> List[Tuple[Document, float]]:
        """Main search interface. mode can be 'lexical', 'embedding', 'hybrid'."""
        if mode == "embedding" and self.embedding:
            candidates = self.embedding.search(query, top_k=top_k*2)
        elif mode == "hybrid" and self.embedding:
            lex_results = self.lexical.search(query)
            emb_results = self.embedding.search(query, top_k=top_k*2)
            # simplistic fuse: combine scores (normalized)
            combined = {}
            for doc, score in lex_results:
                combined[doc.id] = (doc, score * 0.5)  # weight
            for doc, score in emb_results:
                if doc.id in combined:
                    combined[doc.id] = (doc, combined[doc.id][1] + score * 0.5)
                else:
                    combined[doc.id] = (doc, score * 0.5)
            candidates = sorted(combined.values(), key=lambda x: x[1], reverse=True)
        else:  # lexical
            candidates = self.lexical.search(query)

        if use_rerank:
            candidates = self.reranker.rerank(candidates, query)

        # Apply source quotas: limit number of results per source type (folder/tag/format) if provided.
        if source_quotas:
            quota_results = []
            counts: Dict[str, int] = defaultdict(int)
            for doc, score in candidates:
                # Determine source type from e.g., file extension or folder
                ext = os.path.splitext(doc.path)[1]
                if ext:
                    source_type = ext.lstrip('.')
                else:
                    source_type = "other"
                quota = source_quotas.get(source_type, source_quotas.get("*", top_k))
                if counts[source_type] < quota:
                    quota_results.append((doc, score))
                    counts[source_type] += 1
            candidates = quota_results

        return candidates[:top_k]

# -------------------------------------------------------------------
# Reader (intelligent extraction based on context)
# -------------------------------------------------------------------
class Reader:
    """Given a document and a request, extracts the specific portion."""
    @staticmethod
    def read_section(doc: Document, section_id: int) -> str:
        return doc.get_section(section_id)

    @staticmethod
    def read_page(doc: Document, page_num: int) -> str:
        return doc.get_page(page_num)

    @staticmethod
    def read_lines(doc: Document, start: int, end: int) -> str:
        return doc.get_lines(start, end)

    @staticmethod
    def read_archive_member(doc: Document, member: str) -> str:
        return doc.get_archive_member(member)

    @staticmethod
    def read_table_slice(doc: Document, rows: Optional[Tuple[int, int]] = None,
                         cols: Optional[Tuple[int, int]] = None) -> str:
        return doc.get_table_slice(rows, cols)

    @staticmethod
    def read_automatic(doc: Document, query: str) -> str:
        """Placeholder: returns a simulated most relevant snippet using simple keyword overlap."""
        # Actually, the agent would orchestrate this; for now return first 2000 chars.
        return doc.content[:2000]

# -------------------------------------------------------------------
# Investigation Notes
# -------------------------------------------------------------------
@dataclass
class InvestigationNote:
    note_id: str
    timestamp: str
    query: str
    answer: str
    citations: List[Dict[str, str]]   # e.g., {"doc_id": ..., "passage": ..., "section": ...}
    raw_context: str
    tags: List[str] = field(default_factory=list)

    def to_document(self) -> Document:
        """Convert to a Document so it can be indexed and recalled."""
        content = f"Query: {self.query}\nAnswer: {self.answer}\nCitations:\n" + \
                  "\n".join(json.dumps(c) for c in self.citations)
        doc = Document(path=f"notes/{self.note_id}.md", title=f"Investigation {self.note_id[:8]}",
                       content=content)
        doc.metadata.created = self.timestamp
        doc.tags = self.tags
        doc.id = self.note_id
        return doc

# -------------------------------------------------------------------
# Agent (LLM-based)
# -------------------------------------------------------------------
class Agent:
    """LLM agent that answers questions using retrieval-augmented reading."""
    def __init__(self, knowledge_base: 'KnowledgeBase', llm_function: Optional[callable] = None):
        self.kb = knowledge_base
        self.llm = llm_function or self._mock_llm   # can be replaced by actual GPT/Claude call

    def _mock_llm(self, prompt: str) -> str:
        """Simulated LLM: returns a generic answer with invented citations."""
        return f"Based on the provided context, the answer is that X relates to Y. [source: doc_1]"

    def answer(self, user_query: str, search_mode: str = "lexical", top_k: int = 5,
               source_quotas: Optional[Dict[str, int]] = None) -> Tuple[str, InvestigationNote]:
        """Full pipeline: retrieve, read, generate, save note."""
        # 1. Search for candidate documents
        searcher = self.kb.searcher
        candidates = searcher.search(user_query, mode=search_mode, top_k=top_k,
                                     source_quotas=source_quotas)

        if not candidates:
            answer = "No relevant documents found."
            note = InvestigationNote(
                note_id=str(uuid.uuid4()),
                timestamp=datetime.datetime.now().isoformat(),
                query=user_query,
                answer=answer,
                citations=[],
                raw_context=""
            )
            self._save_note(note)
            return answer, note

        # 2. For each candidate, decide what to read (simulated logic: read first section)
        context_parts = []
        citations = []
        for doc, score in candidates[:top_k]:
            # In a real system, the LLM would request specific parts.
            # Here we auto-read a portion.
            snippet = Reader.read_automatic(doc, user_query)
            context_parts.append(f"--- Document: {doc.title} (ID: {doc.id}) ---\n{snippet}")
            citations.append({"doc_id": doc.id, "title": doc.title, "passage": snippet[:200] + "..."})

        context_text = "\n\n".join(context_parts)

        # 3. Generate answer using LLM with context
        prompt = f"""You are a research librarian. Answer the user's question using ONLY the provided document excerpts.
If the answer cannot be found, say so.

Context:
{context_text}

Question: {user_query}

Answer with citations:"""
        answer = self.llm(prompt)

        # 4. Create investigation note
        note = InvestigationNote(
            note_id=str(uuid.uuid4()),
            timestamp=datetime.datetime.now().isoformat(),
            query=user_query,
            answer=answer,
            citations=citations,
            raw_context=context_text,
            tags=["investigation"]
        )
        self._save_note(note)

        return answer, note

    def _save_note(self, note: InvestigationNote) -> None:
        """Persist investigation note as a document and add to knowledge base."""
        doc = note.to_document()
        # Ensure notes folder exists
        notes_dir = os.path.join(self.kb.base_path, "notes")
        os.makedirs(notes_dir, exist_ok=True)
        file_path = os.path.join(notes_dir, f"{note.note_id}.md")
        with open(file_path, 'w') as f:
            f.write(doc.content)
        self.kb.index_document(doc, file_path)  # So it becomes searchable
        # Also record in original document journals if applicable
        for cit in note.citations:
            cited_doc = self.kb.get_document(cit["doc_id"])
            if cited_doc:
                cited_doc.journal.append(note.note_id)

# -------------------------------------------------------------------
# KnowledgeBase: central orchestrator
# -------------------------------------------------------------------
class KnowledgeBase:
    def __init__(self, base_path: str, config: Optional[Dict] = None):
        self.base_path = os.path.abspath(base_path)
        self.config = config or {}
        self._documents: Dict[str, Document] = {}   # id -> Document
        # Indexes
        self.lexical_index = LexicalIndex()
        self.embedding_index: Optional[EmbeddingIndex] = None
        if self.config.get("use_embeddings"):
            self.embedding_index = EmbeddingIndex()
        self.searcher = Searcher(self.lexical_index, self.embedding_index)
        self.agent = Agent(self)
        # Optional sqlite-vec placeholder
        self._vec_db = None
        if self.config.get("use_sqlite_vec"):
            self._vec_db = FakeSqliteVec()

        # Ensure base path exists
        os.makedirs(self.base_path, exist_ok=True)
        # Scan existing files? Not implemented.

    def ingest_file(self, file_path: str) -> Optional[Document]:
        """Ingest a single file from outside base path into knowledge base (copy to base)."""
        src = Path(file_path)
        if not src.is_file():
            return None
        # Determine destination inside base_path preserving relative structure or flat?
        # For safety, copy into a 'files' subdirectory.
        target_dir = os.path.join(self.base_path, "files")
        os.makedirs(target_dir, exist_ok=True)
        dest = os.path.join(target_dir, src.name)
        shutil.copy2(file_path, dest)
        return self._ingest_from_path(dest)

    def _ingest_from_path(self, path: str, content: Optional[str] = None) -> Document:
        """Create Document object from a file path, extracting content."""
        if content is None:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        # Derive metadata
        stat = os.stat(path)
        metadata = Metadata(
            size=stat.st_size,
            created=datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified=datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            title=os.path.basename(path)
        )
        doc = Document(path=path, content=content, metadata=metadata)
        self.add_document(doc)
        return doc

    def add_document(self, doc: Document) -> None:
        """Add document to internal stores and indexes."""
        self._documents[doc.id] = doc
        self.lexical_index.add_document(doc)
        if self.embedding_index:
            self.embedding_index.add_document(doc)
        # Also could update relation miner etc.

    def index_document(self, doc: Document, file_path: str) -> None:
        """Index a document that may already have a path (used for notes)."""
        doc.path = file_path
        self.add_document(doc)

    def get_document(self, doc_id: str) -> Optional[Document]:
        return self._documents.get(doc_id)

    def search(self, query: str, mode: str = "lexical", **kwargs) -> List[Tuple[Document, float]]:
        return self.searcher.search(query, mode=mode, **kwargs)

    def ask_agent(self, question: str) -> Tuple[str, InvestigationNote]:
        return self.agent.answer(question)

    def add_tag(self, doc_id: str, tag: str) -> None:
        doc = self.get_document(doc_id)
        if doc:
            doc.add_tag(tag)

    def update_metadata(self, doc_id: str, **kwargs) -> None:
        doc = self.get_document(doc_id)
        if doc:
            doc.update_metadata(**kwargs)

    def organize_folder(self, doc_id: str, new_folder: str) -> None:
        """Logical folder assignment (does not move file unless physical)."""
        doc = self.get_document(doc_id)
        if doc:
            doc.folder = new_folder

    def list_documents(self, folder: Optional[str] = None, tag: Optional[str] = None) -> List[Document]:
        """List documents filtered by folder or tag."""
        result = list(self._documents.values())
        if folder:
            result = [d for d in result if d.folder == folder]
        if tag:
            result = [d for d in result if tag in d.tags]
        return result

    # Relation mining (placeholder)
    def discover_relations(self) -> List[Tuple[str, str, str]]:
        """Find simple co-occurrence relations (same tokens) between documents."""
        relations = []
        for i, (id1, doc1) in enumerate(self._documents.items()):
            tokens1 = set(re.findall(r'\b\w+\b', doc1.content.lower()))
            for id2, doc2 in list(self._documents.items())[i+1:]:
                tokens2 = set(re.findall(r'\b\w+\b', doc2.content.lower()))
                common = tokens1 & tokens2
                if len(common) > 20:   # arbitrary threshold
                    relations.append((doc1.id, doc2.id, ", ".join(list(common)[:5])))
        return relations

# -------------------------------------------------------------------
# Example usage (if script run directly)
# -------------------------------------------------------------------
if __name__ == "__main__":
    # Initialize knowledge base in a temp directory
    test_dir = os.path.join(os.getcwd(), "test_kb")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    kb = KnowledgeBase(test_dir)

    # Ingest a sample file
    sample_file = os.path.join(test_dir, "sample.md")
    with open(sample_file, 'w') as f:
        f.write("# Project Marginalia\n\nThis is a local-first research agent.\n")
    doc = kb._ingest_from_path(sample_file)

    # Add some tags
    kb.add_tag(doc.id, "tech")
    kb.add_tag(doc.id, "AI")

    # Perform a search
    results = kb.search("local-first", mode="lexical")
    for d, score in results:
        print(f"Found: {d.title} with score {score}")

    # Ask agent
    answer, note = kb.ask_agent("What is Marginalia?")
    print("Answer:", answer)
    print("Note ID:", note.note_id)

    # Retrieve investigation notes via search
    note_docs = kb.search("investigation", mode="lexical")
    print("Investigation notes found:", len(note_docs))