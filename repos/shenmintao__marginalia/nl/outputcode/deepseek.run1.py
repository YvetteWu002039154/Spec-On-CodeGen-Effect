import os
import re
import uuid
import json
import csv
import io
import datetime
import zipfile
import tarfile
import xml.etree.ElementTree as ET
import math
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Union
from collections import defaultdict
from enum import Enum
from dataclasses import dataclass, field


# ----------------------------------------------------------------------
# ENUMS AND DATA STRUCTURES
# ----------------------------------------------------------------------
class FileType(Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    IMAGE = "image"
    SPREADSHEET = "spreadsheet"
    LOG = "log"
    ARCHIVE = "archive"
    OTHER = "other"


@dataclass
class FileWindowSpec:
    """Specifies a window to read: lines, section, page, member, table_slice."""
    window_type: str   # 'lines', 'section', 'page', 'member', 'table_slice'
    start: Optional[Union[int, str]] = None
    end: Optional[Union[int, str]] = None
    section_title: Optional[str] = None
    member_name: Optional[str] = None
    sheet_name: Optional[str] = None   # for spreadsheet slices


@dataclass
class CatalogEntry:
    entry_id: str
    path: str          # relative to root
    title: str
    file_type: FileType
    size_bytes: int
    modified: datetime.datetime
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_hash: Optional[str] = None
    summary: Optional[str] = None
    # For archives, store sub-entries
    members: Optional[List[str]] = None   # list of member paths relative to archive


@dataclass
class SearchResult:
    entry_id: str
    score: float
    snippet: Optional[str] = None
    why: Optional[str] = None   # explanation of match (e.g., term found)


@dataclass
class Citation:
    entry_id: str
    title: str
    location: str   # human-readable window description
    content_snippet: Optional[str] = None


@dataclass
class InvestigationNote:
    note_id: str
    query: str
    answer: str
    citations: List[Citation]
    timestamp: datetime.datetime
    source_entry_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    raw_context: Optional[str] = None


# ----------------------------------------------------------------------
# TEXT PROCESSING
# ----------------------------------------------------------------------
class TokenProcessor:
    """Simple tokenizer: lowercase, split on non-alphanumeric, keep words of length>1"""
    @staticmethod
    def tokenize(text: str) -> List[str]:
        if not text:
            return []
        return re.findall(r'\b\w{2,}\b', text.lower())


# ----------------------------------------------------------------------
# INVERTED INDEX (lexical search)
# ----------------------------------------------------------------------
class InvertedIndex:
    def __init__(self):
        self.index: Dict[str, List[Tuple[str, List[int], float]]] = defaultdict(list)  # token -> [(doc_id, positions, tf)]
        self.doc_lengths: Dict[str, int] = {}   # doc_id -> term_count
        self.doc_count = 0
        self.avg_dl = 0.0

    def add_document(self, doc_id: str, tokens: List[str]):
        # Compute term frequencies
        tf_map = defaultdict(int)
        pos_map = defaultdict(list)
        for pos, token in enumerate(tokens):
            tf_map[token] += 1
            pos_map[token].append(pos)
        length = len(tokens)
        self.doc_lengths[doc_id] = length
        self.doc_count += 1
        total = sum(self.doc_lengths.values())
        self.avg_dl = total / self.doc_count if self.doc_count else 0
        for token, tf in tf_map.items():
            self.index[token].append((doc_id, pos_map[token], tf))

    def remove_document(self, doc_id: str):
        if doc_id not in self.doc_lengths:
            return
        # Rebuild index without this doc
        # For simplicity, we can reconstruct by iterating over all tokens, but
        # a direct removal is possible by filtering each token's postings list.
        for token in list(self.index.keys()):
            new_list = [(did, pos, tf) for did, pos, tf in self.index[token] if did != doc_id]
            if new_list:
                self.index[token] = new_list
            else:
                del self.index[token]
        del self.doc_lengths[doc_id]
        self.doc_count -= 1
        total = sum(self.doc_lengths.values())
        self.avg_dl = total / self.doc_count if self.doc_count else 0

    def search(self, query_tokens: List[str], top_k: int = 10) -> List[Tuple[str, float]]:
        """BM25-like scoring."""
        scores = defaultdict(float)
        k1 = 1.2
        b = 0.75
        N = self.doc_count
        avgdl = self.avg_dl

        for token in query_tokens:
            if token not in self.index:
                continue
            df = len(self.index[token])
            idf = math.log(1 + (N - df + 0.5) / (df + 0.5))
            for doc_id, positions, tf in self.index[token]:
                dl = self.doc_lengths[doc_id]
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * dl / avgdl)
                scores[doc_id] += idf * numerator / denominator

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:top_k]

    def get_snippet(self, doc_id: str, query_tokens: List[str], max_length: int = 200) -> Optional[str]:
        """Return a snippet containing one of the query tokens. Requires token positions."""
        token_positions = {}
        for token in query_tokens:
            if token in self.index:
                for did, pos, _ in self.index[token]:
                    if did == doc_id:
                        if doc_id not in token_positions:
                            token_positions[doc_id] = []
                        token_positions[doc_id].extend(pos)
        if doc_id not in token_positions:
            return None
        # We'll need original text. The index doesn't store raw text.
        # So we'll need to fetch the full document content. The snippet will be provided by calling the Reader.
        # Here we just return a placeholder; real implementation would use stored text or token sequences.
        return f"Snippet not available from index; use Reader for full context."


# ----------------------------------------------------------------------
# EMBEDDINGS INDEX (simple TF-IDF vector based for demonstration)
# ----------------------------------------------------------------------
class EmbeddingIndex:
    """Uses a bag-of-words TF-IDF model with cosine similarity."""
    def __init__(self):
        self.doc_vectors: Dict[str, Dict[str, float]] = {}   # doc_id -> {term: tfidf}
        self.idf: Dict[str, float] = {}
        self.vocab: set = set()

    def add_document(self, doc_id: str, tokens: List[str]):
        tf_map = defaultdict(int)
        for t in tokens:
            tf_map[t] += 1
        length = len(tokens)
        tf_norm = {t: cnt / length for t, cnt in tf_map.items()} if length > 0 else {}
        self.doc_vectors[doc_id] = tf_norm
        self.vocab.update(tf_norm.keys())
        # Update IDF later (batch)

    def finalize_vocab(self):
        N = len(self.doc_vectors)
        self.idf = {}
        for term in self.vocab:
            df = sum(1 for vec in self.doc_vectors.values() if term in vec)
            self.idf[term] = math.log((N + 1) / (df + 1)) + 1 if df > 0 else 0
        # Recalculate TF-IDF vectors
        for doc_id, tf_vec in self.doc_vectors.items():
            self.doc_vectors[doc_id] = {t: tf * self.idf[t] for t, tf in tf_vec.items()}

    def search(self, query_tokens: List[str], top_k: int = 10) -> List[Tuple[str, float]]:
        # Build query vector: TF (count) * IDF
        q_tf = defaultdict(int)
        for t in query_tokens:
            q_tf[t] += 1
        q_vec = {}
        length = len(query_tokens)
        for t, cnt in q_tf.items():
            if t in self.idf:
                q_vec[t] = (cnt / length) * self.idf[t]
        # Cosine similarity
        if not q_vec:
            return []
        scores = []
        for doc_id, d_vec in self.doc_vectors.items():
            dot = sum(q_vec.get(t, 0) * d_vec.get(t, 0) for t in q_vec)
            q_norm = math.sqrt(sum(v**2 for v in q_vec.values()))
            d_norm = math.sqrt(sum(v**2 for v in d_vec.values()))
            if q_norm == 0 or d_norm == 0:
                sim = 0.0
            else:
                sim = dot / (q_norm * d_norm)
            scores.append((doc_id, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


# ----------------------------------------------------------------------
# INGESTION ENGINE
# ----------------------------------------------------------------------
class IngestionEngine:
    """
    Walks the file tree, extracts text/metadata, and returns raw content
    plus tokens for indexing.
    Supported: .txt, .md, .docx (minimal), .csv, .log, .zip, .tar, .tar.gz, .tgz.
    PDF and images are cataloged but text extraction is not implemented (stub).
    """
    def __init__(self, root: Path):
        self.root = root

    def discover(self) -> List[Path]:
        """Return list of all file paths (absolute) in root tree."""
        files = []
        for p in self.root.rglob('*'):
            if p.is_file() and not p.name.startswith('.'):  # ignore hidden
                files.append(p)
        return files

    def get_file_type(self, path: Path) -> FileType:
        ext = path.suffix.lower()
        if ext in ('.txt', '.text'):
            return FileType.TEXT
        if ext in ('.md', '.markdown'):
            return FileType.MARKDOWN
        if ext == '.pdf':
            return FileType.PDF
        if ext == '.docx':
            return FileType.DOCX
        if ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'):
            return FileType.IMAGE
        if ext in ('.csv', '.tsv', '.xlsx', '.xls', '.ods'):
            return FileType.SPREADSHEET
        if ext in ('.log',):
            return FileType.LOG
        if ext in ('.zip', '.tar', '.gz', '.tgz', '.bz2', '.7z'):
            return FileType.ARCHIVE
        return FileType.OTHER

    def extract_text(self, path: Path, ftype: FileType) -> str:
        """Extract full text content. For unsupported types returns empty string."""
        try:
            if ftype in (FileType.TEXT, FileType.MARKDOWN, FileType.LOG):
                return path.read_text(encoding='utf-8', errors='ignore')
            elif ftype == FileType.CSV:
                # For CSV, extract as tabular string for indexing
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                # Flatten into text
                return ' '.join(' '.join(row) for row in rows)
            elif ftype == FileType.DOCX:
                # Minimal DOCX reader using zip + XML
                with zipfile.ZipFile(path, 'r') as z:
                    if 'word/document.xml' in z.namelist():
                        xml_content = z.read('word/document.xml')
                        root_el = ET.fromstring(xml_content)
                        # Extract all text from <w:t> elements
                        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                        texts = root_el.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
                        return ' '.join(t.text for t in texts if t.text)
                    else:
                        return ''
            elif ftype == FileType.ARCHIVE:
                # For archives we return a listing of member names (text)
                # The actual members are handled separately.
                return self._get_archive_listing(path)
            else:
                return ''  # PDF, images, unsupported
        except Exception as e:
            return ''

    def _get_archive_listing(self, path: Path) -> str:
        """Return newline-separated list of member names inside archive."""
        members = []
        try:
            if path.suffix.lower() == '.zip':
                with zipfile.ZipFile(path, 'r') as zf:
                    members = zf.namelist()
            elif path.suffix.lower() in ('.tar', '.gz', '.tgz', '.bz2'):
                with tarfile.open(path, 'r') as tf:
                    members = [m.name for m in tf.getmembers() if m.isfile()]
            else:
                return ''
        except Exception:
            pass
        return '\n'.join(members)

    def process_file(self, path: Path) -> Tuple[CatalogEntry, List[CatalogEntry], Optional[str], Optional[str]]:
        """
        Returns:
            - primary entry
            - list of sub-entries (e.g., archive members) - only for archives
            - full text (str)
            - content hash (optional)
        """
        rel_path = str(path.relative_to(self.root))
        ftype = self.get_file_type(path)
        stat = path.stat()
        size = stat.st_size
        mod = datetime.datetime.fromtimestamp(stat.st_mtime)
        title = path.name
        text = self.extract_text(path, ftype)
        # Generate entry ID from relative path
        entry_id = str(uuid.uuid5(uuid.NAMESPACE_OID, rel_path))
        entry = CatalogEntry(
            entry_id=entry_id,
            path=rel_path,
            title=title,
            file_type=ftype,
            size_bytes=size,
            modified=mod,
            tags=[],
            metadata={'extension': path.suffix},
            content_hash=None,   # could be added
            summary=None
        )
        sub_entries = []
        # For archives, create sub-entries for each member
        if ftype == FileType.ARCHIVE:
            members = []
            full_path = self.root / rel_path
            try:
                if path.suffix.lower() == '.zip':
                    with zipfile.ZipFile(full_path, 'r') as zf:
                        for name in zf.namelist():
                            if name.endswith('/'):
                                continue
                            member_id = str(uuid.uuid5(uuid.NAMESPACE_OID, rel_path + '::' + name))
                            sub = CatalogEntry(
                                entry_id=member_id,
                                path=rel_path + '::' + name,  # virtual path
                                title=name,
                                file_type=self.get_file_type(Path(name)),
                                size_bytes=0,  # unknown without extracting
                                modified=mod,
                                tags=[],
                                metadata={'archive_member': True, 'archive': rel_path},
                                content_hash=None,
                                summary=None
                            )
                            sub_entries.append(sub)
                            members.append(name)
                elif path.suffix.lower() in ('.tar', '.gz', '.tgz', '.bz2'):
                    with tarfile.open(full_path, 'r') as tf:
                        for m in tf.getmembers():
                            if not m.isfile():
                                continue
                            name = m.name
                            member_id = str(uuid.uuid5(uuid.NAMESPACE_OID, rel_path + '::' + name))
                            sub = CatalogEntry(
                                entry_id=member_id,
                                path=rel_path + '::' + name,
                                title=name,
                                file_type=self.get_file_type(Path(name)),
                                size_bytes=m.size,
                                modified=datetime.datetime.fromtimestamp(m.mtime),
                                tags=[],
                                metadata={'archive_member': True, 'archive': rel_path},
                                content_hash=None,
                                summary=None
                            )
                            sub_entries.append(sub)
                            members.append(name)
            except Exception:
                pass
            entry.members = members

        return entry, sub_entries, text, None


# ----------------------------------------------------------------------
# FILE READER FOR WINDOWS
# ----------------------------------------------------------------------
class Reader:
    """
    Reads specific file windows based on window specs.
    Returns the extracted window content as a string along with a human-readable location.
    """
    def __init__(self, root: Path, catalog: Dict[str, CatalogEntry]):
        self.root = root
        self.catalog = catalog

    def read_window(self, entry_id: str, spec: FileWindowSpec) -> Tuple[str, str]:
        """
        Returns (content, location_description).
        """
        entry = self.catalog.get(entry_id)
        if not entry:
            return "", "unknown"
        ftype = entry.file_type
        # Determine real file path
        if '::' in entry.path:   # archive member
            archive_rel, member_name = entry.path.split('::', 1)
            archive_path = self.root / archive_rel
            if not archive_path.exists():
                return "", f"archive {archive_rel} not found"
            # For archive members, the spec.window_type == 'member'
            content = self._read_archive_member(archive_path, member_name, entry.file_type)
            loc = f"archive {archive_rel} member {member_name}"
            if spec.window_type == 'member':
                return content, loc
            else:
                # If spec is something else, treat whole member as content
                return content, loc
        else:
            file_path = self.root / entry.path
            if not file_path.exists():
                return "", f"file {entry.path} not found"

            if spec.window_type == 'lines':
                return self._read_lines(file_path, ftype, spec.start, spec.end)
            elif spec.window_type == 'section' and ftype == FileType.MARKDOWN:
                return self._read_md_section(file_path, spec.section_title)
            elif spec.window_type == 'page' and ftype == FileType.PDF:
                # PDF reading not implemented
                return "[PDF reading not supported]", f"page {spec.start} of {entry.path}"
            elif spec.window_type == 'table_slice' and ftype == FileType.SPREADSHEET:
                return self._read_csv_slice(file_path, spec.start, spec.end, spec.sheet_name)
            else:
                # Fallback: return full file
                content = self._read_full(file_path, ftype)
                loc = f"full content of {entry.path}"
                return content, loc

    def _read_lines(self, path: Path, ftype: FileType, start: Optional[int], end: Optional[int]) -> Tuple[str, str]:
        if ftype in (FileType.TEXT, FileType.MARKDOWN, FileType.LOG):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            total = len(lines)
            s = max(0, start - 1) if start else 0
            e = min(total, end) if end else total
            selected = lines[s:e]
            content = ''.join(selected)
            loc = f"lines {s+1}-{e} of {path.name}"
            return content, loc
        else:
            return self._read_full(path, ftype), f"full content of {path.name}"

    def _read_md_section(self, path: Path, section_title: str) -> Tuple[str, str]:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        # Split by headings (lines starting with #). Simple regex.
        pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        sections = []
        last_pos = 0
        for m in pattern.finditer(content):
            level = len(m.group(1))
            heading = m.group(2).strip()
            start = m.start()
            if last_pos < start:
                sections.append(('', content[last_pos:start]))  # intro before first heading
            sections.append((heading, content[start:]))
            last_pos = m.end()
        if last_pos < len(content):
            sections.append(('', content[last_pos:]))
        # Now find section matching section_title (case-insensitive)
        found = None
        for i, (h, sec) in enumerate(sections):
            if h.lower() == section_title.lower():
                # Return from heading to next heading or end
                # sec starts with the heading line; we need to extract lines until next heading
                # Actually sec contains text from the heading line. We'll search for next heading within it.
                # Simpler: we have the entire section string.
                found = sec
                break
        if found:
            # Get lines of the section
            lines = found.splitlines(keepends=True)
            content_out = ''.join(lines)
            loc = f"section '{section_title}' of {path.name}"
            return content_out, loc
        else:
            return "", f"section '{section_title}' not found in {path.name}"

    def _read_archive_member(self, archive_path: Path, member_name: str, ftype: FileType) -> str:
        try:
            if archive_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    with zf.open(member_name) as mf:
                        return mf.read().decode('utf-8', errors='ignore')
            elif archive_path.suffix.lower() in ('.tar', '.gz', '.tgz', '.bz2'):
                with tarfile.open(archive_path, 'r') as tf:
                    f = tf.extractfile(member_name)
                    if f:
                        return f.read().decode('utf-8', errors='ignore')
                    else:
                        return f"[Could not read member {member_name}]"
            else:
                return f"[Unsupported archive format: {archive_path}]"
        except Exception as e:
            return f"[Error reading archive member: {e}]"

    def _read_csv_slice(self, path: Path, start_row: Optional[int], end_row: Optional[int], sheet_name: Optional[str] = None) -> Tuple[str, str]:
        # Assume CSV
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            rows = list(reader)
        total = len(rows)
        s = max(0, start_row - 1) if start_row else 0
        e = min(total, end_row) if end_row else total
        selected = rows[s:e]
        content = '\n'.join(','.join(row) for row in selected)
        loc = f"rows {s+1}-{e} of {path.name}"
        return content, loc

    def _read_full(self, path: Path, ftype: FileType) -> str:
        try:
            if ftype in (FileType.TEXT, FileType.MARKDOWN, FileType.LOG, FileType.CSV, FileType.DOCX):
                return path.read_text(encoding='utf-8', errors='ignore')
            else:
                return path.read_text(encoding='utf-8', errors='ignore')  # attempt anyway
        except Exception:
            return ''


# ----------------------------------------------------------------------
# MOCK LLM AGENT
# ----------------------------------------------------------------------
class MarginAgent:
    """
    Simulates an LLM that reads context windows and generates a cited answer.
    For demonstration, it constructs a summary mentioning the sources.
    """
    def answer(self, query: str, contexts: List[Tuple[str, str, str]]) -> Tuple[str, List[Citation]]:
        """
        Args:
            query: user's question
            contexts: list of (entry_id, window_content, location_description)
        Returns:
            answer text, list of citations
        """
        citations: List[Citation] = []
        used_ids = set()
        parts = []
        for i, (eid, content, loc) in enumerate(contexts):
            if eid in used_ids:
                continue
            used_ids.add(eid)
            snippet = content[:200] + ('...' if len(content) > 200 else '')
            # Generate a citation
            title = "source"  # we don't have title here; we'll get from catalog later
            citations.append(Citation(entry_id=eid, title=loc, location=loc, content_snippet=snippet))
            # Build answer part
            parts.append(f"From {loc}:\n{snippet}\n")
        answer = f"Based on the provided context, here is a synthesized answer to: '{query}'\n\n" + '\n'.join(parts)
        answer += "\n\nNote: This is a simulated answer. In a real system, an LLM would provide detailed reasoning."
        return answer, citations


# ----------------------------------------------------------------------
# NOTE MANAGER
# ----------------------------------------------------------------------
class NoteManager:
    def __init__(self, notes_file: Optional[Path] = None):
        self.notes: Dict[str, InvestigationNote] = {}
        self.notes_file = notes_file
        if notes_file and notes_file.exists():
            self._load()

    def save_note(self, note: InvestigationNote):
        self.notes[note.note_id] = note
        if self.notes_file:
            self._persist()

    def search_notes(self, query: str) -> List[InvestigationNote]:
        query_tokens = TokenProcessor.tokenize(query)
        results = []
        for note in self.notes.values():
            text = note.query + ' ' + note.answer
            tokens = set(TokenProcessor.tokenize(text))
            # simple Jaccard-like match
            overlap = sum(1 for t in query_tokens if t in tokens)
            if overlap > 0:
                results.append(note)
        return results

    def _persist(self):
        data = []
        for n in self.notes.values():
            data.append({
                'note_id': n.note_id,
                'query': n.query,
                'answer': n.answer,
                'citations': [{
                    'entry_id': c.entry_id,
                    'title': c.title,
                    'location': c.location,
                    'content_snippet': c.content_snippet
                } for c in n.citations],
                'timestamp': n.timestamp.isoformat(),
                'source_entry_ids': n.source_entry_ids,
                'tags': n.tags,
                'raw_context': n.raw_context
            })
        with open(self.notes_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _load(self):
        with open(self.notes_file, 'r') as f:
            data = json.load(f)
        for d in data:
            citations = [Citation(**c) for c in d['citations']]
            note = InvestigationNote(
                note_id=d['note_id'],
                query=d['query'],
                answer=d['answer'],
                citations=citations,
                timestamp=datetime.datetime.fromisoformat(d['timestamp']),
                source_entry_ids=d['source_entry_ids'],
                tags=d.get('tags', []),
                raw_context=d.get('raw_context')
            )
            self.notes[note.note_id] = note


# ----------------------------------------------------------------------
# MARGINALIA MAIN CLASS
# ----------------------------------------------------------------------
class Marginalia:
    """
    Personal knowledge management system with LLM agent.
    Maintains a folder tree, catalog, indexes, and supports recall, reading, and answering.
    """
    def __init__(self, root_path: str, use_embeddings: bool = False):
        self.root = Path(root_path).expanduser().resolve()
        if not self.root.exists():
            self.root.mkdir(parents=True)
        self.catalog: Dict[str, CatalogEntry] = {}
        self.ingestion = IngestionEngine(self.root)
        self.lex_index = InvertedIndex()
        self.embed_index = EmbeddingIndex() if use_embeddings else None
        self.use_embeddings = use_embeddings
        self.reader = Reader(self.root, self.catalog)
        self.agent = MarginAgent()
        self.notes_mgr = NoteManager(notes_file=self.root / '.marginalia_notes.json')
        self.journal: List[str] = []  # simple list of timestamped entries
        self.views: Dict[str, str] = {}  # name -> query expression
        self.tags_index: Dict[str, List[str]] = defaultdict(list)  # tag -> list of entry_ids
        self._ingested = False

    def ingest(self):
        """Scan the root directory and process all files, building catalog and index."""
        files = self.ingestion.discover()
        for fpath in files:
            entry, subs, text, _ = self.ingestion.process_file(fpath)
            # Add to catalog
            self.catalog[entry.entry_id] = entry
            # For sub-entries (archive members)
            for sub in subs:
                self.catalog[sub.entry_id] = sub
            # Index primary entry
            if text:
                tokens = TokenProcessor.tokenize(text)
                self.lex_index.add_document(entry.entry_id, tokens)
                if self.embed_index:
                    self.embed_index.add_document(entry.entry_id, tokens)
            # Index archive members (extract member content)
            if entry.file_type == FileType.ARCHIVE and entry.members:
                archive_idx = entry.path
                try:
                    if fpath.suffix.lower() == '.zip':
                        with zipfile.ZipFile(fpath, 'r') as zf:
                            for member_name in entry.members:
                                # member_name is just the name, resolve sub entry
                                sub_entry = next((s for s in subs if s.path.endswith(member_name)), None)
                                if sub_entry:
                                    try:
                                        with zf.open(member_name) as mf:
                                            member_text = mf.read().decode('utf-8', errors='ignore')
                                    except Exception:
                                        member_text = ''
                                    if member_text:
                                        tokens = TokenProcessor.tokenize(member_text)
                                        self.lex_index.add_document(sub_entry.entry_id, tokens)
                                        if self.embed_index:
                                            self.embed_index.add_document(sub_entry.entry_id, tokens)
                    elif fpath.suffix.lower() in ('.tar', '.gz', '.tgz', '.bz2'):
                        with tarfile.open(fpath, 'r') as tf:
                            for member_name in entry.members:
                                sub_entry = next((s for s in subs if s.path.endswith(member_name)), None)
                                if sub_entry:
                                    try:
                                        f = tf.extractfile(member_name)
                                        if f:
                                            member_text = f.read().decode('utf-8', errors='ignore')
                                        else:
                                            member_text = ''
                                    except Exception:
                                        member_text = ''
                                    if member_text:
                                        tokens = TokenProcessor.tokenize(member_text)
                                        self.lex_index.add_document(sub_entry.entry_id, tokens)
                                        if self.embed_index:
                                            self.embed_index.add_document(sub_entry.entry_id, tokens)
                except Exception:
                    pass

        if self.embed_index:
            self.embed_index.finalize_vocab()
        self.journal.append(f"{datetime.datetime.now()}: Ingest completed. {len(self.catalog)} entries indexed.")
        self._ingested = True

    def recall(self, query: str, top_k: int = 10, strategy: str = 'lexical',
               source_quota: Optional[Dict[str, int]] = None) -> List[SearchResult]:
        """
        Recall candidate entries based on query.
        strategy: 'lexical' (default), 'embedding', 'both' (rerank)
        source_quota: dict limiting number of results from certain folders, e.g., {'projects/':3}
        """
        if not self._ingested:
            self.ingest()
        tokens = TokenProcessor.tokenize(query)
        if strategy == 'lexical' or strategy == 'both':
            lex_scores = self.lex_index.search(tokens, top_k=top_k*2)  # get more for reranking
            results = [SearchResult(entry_id=eid, score=score, snippet=self.lex_index.get_snippet(eid, tokens)) for eid, score in lex_scores]
        else:
            results = []
        if strategy == 'embedding' or (strategy == 'both' and self.embed_index):
            if self.embed_index:
                emb_scores = self.embed_index.search(tokens, top_k=top_k*2)
                emb_map = dict(emb_scores)
                # Merge
                for res in results:
                    if res.entry_id in emb_map:
                        res.score = 0.5 * res.score + 0.5 * emb_map[res.entry_id]
                    else:
                        res.score *= 0.5
                # Add missing embedding-only results
                exist = {res.entry_id for res in results}
                for eid, escore in emb_scores:
                    if eid not in exist:
                        results.append(SearchResult(entry_id=eid, score=escore*0.5, snippet=None))
            elif strategy == 'embedding':
                # fallback to lexical if no embedding index
                results = self.recall(query, top_k, 'lexical', source_quota)
                return results
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        # Apply source quotas if any
        if source_quota:
            quota_results = []
            counts = defaultdict(int)
            for res in results:
                entry = self.catalog.get(res.entry_id)
                if not entry:
                    continue
                # Determine source folder (parent directory of entry.path)
                source = str(Path(entry.path).parent) + '/'   # relative
                matched_quota = None
                for prefix, max_count in source_quota.items():
                    if source.startswith(prefix):
                        matched_quota = prefix
                        break
                if matched_quota:
                    if counts[matched_quota] < source_quota[matched_quota]:
                        quota_results.append(res)
                        counts[matched_quota] += 1
                else:
                    quota_results.append(res)
            results = quota_results
        if len(results) > top_k:
            results = results[:top_k]
        return results

    def read_windows_for_results(self, results: List[SearchResult], window_size: int = 5) -> List[Tuple[str, str, str]]:
        """
        For each search result, generate a window spec based on file type and read the window.
        Returns list of (entry_id, content, location)
        """
        windows = []
        for res in results:
            entry = self.catalog.get(res.entry_id)
            if not entry:
                continue
            spec = self._auto_window_spec(entry, window_size)
            content, loc = self.reader.read_window(res.entry_id, spec)
            if content:
                windows.append((res.entry_id, content, loc))
        return windows

    def _auto_window_spec(self, entry: CatalogEntry, window_lines: int = 5) -> FileWindowSpec:
        """Create a sensible default window spec based on file type."""
        ftype = entry.file_type
        if ftype == FileType.MARKDOWN:
            # Try to get the first section title; we'll need content. Use lines instead.
            return FileWindowSpec(window_type='lines', start=1, end=window_lines*2)
        elif ftype in (FileType.TEXT, FileType.LOG):
            return FileWindowSpec(window_type='lines', start=1, end=window_lines*2)
        elif ftype == FileType.ARCHIVE:
            # Pick first member if exists
            if entry.members:
                return FileWindowSpec(window_type='member', member_name=entry.members[0])
            else:
                return FileWindowSpec(window_type='lines', start=1, end=10)
        elif ftype == FileType.SPREADSHEET:
            return FileWindowSpec(window_type='table_slice', start=1, end=window_lines)
        else:
            return FileWindowSpec(window_type='lines', start=1, end=10)

    def answer(self, query: str, window_size: int = 5) -> Tuple[str, List[Citation], InvestigationNote]:
        """
        Full pipeline: recall, read windows, generate answer, save note.
        """
        # Step 1: Recall
        results = self.recall(query, top_k=3)
        # Step 2: Read windows
        windows = self.read_windows_for_results(results, window_size)
        # Step 3: Answer with mock LLM
        answer_text, citations = self.agent.answer(query, windows)
        # Step 4: Create investigation note
        source_ids = [r.entry_id for r in results[:3]]
        context_text = '\n\n---\n'.join(w[1] for w in windows)
        note = InvestigationNote(
            note_id=str(uuid.uuid4()),
            query=query,
            answer=answer_text,
            citations=citations,
            timestamp=datetime.datetime.now(),
            source_entry_ids=source_ids,
            tags=[],
            raw_context=context_text
        )
        self.notes_mgr.save_note(note)
        self.journal.append(f"{datetime.datetime.now()}: Answered query '{query}' (note {note.note_id})")
        return answer_text, citations, note

    def add_tag(self, entry_id: str, tag: str):
        entry = self.catalog.get(entry_id)
        if entry and tag not in entry.tags:
            entry.tags.append(tag)
            self.tags_index[tag].append(entry_id)

    def remove_tag(self, entry_id: str, tag: str):
        entry = self.catalog.get(entry_id)
        if entry and tag in entry.tags:
            entry.tags.remove(tag)
            if entry_id in self.tags_index.get(tag, []):
                self.tags_index[tag].remove(entry_id)

    def create_view(self, name: str, query_expression: str):
        self.views[name] = query_expression

    def search_notes(self, query: str) -> List[InvestigationNote]:
        return self.notes_mgr.search_notes(query)

    # Optional relation mining: find files that share tags
    def find_related(self, entry_id: str) -> List[str]:
        entry = self.catalog.get(entry_id)
        if not entry or not entry.tags:
            return []
        related = set()
        for tag in entry.tags:
            for eid in self.tags_index.get(tag, []):
                if eid != entry_id:
                    related.add(eid)
        return list(related)


# ----------------------------------------------------------------------
# DEMO / MAIN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "my_library"
        root.mkdir()
        # Create some sample files
        (root / "notes.txt").write_text("This is a personal note about AI research. I am excited about LLMs.")
        (root / "project.md").write_text("# Introduction\nThis project uses retrieval-augmented generation.\n## Results\nResults are promising.")
        (root / "data.csv").write_text("name,value\nalice,10\nbob,20")
        (root / "archive.zip").write_bytes(b'PK\x03\x04')  # dummy, not valid zip; for demo we'll skip
        (root / "sub").mkdir()
        (root / "sub" / "log.txt").write_text("2023-10-01 INFO Starting agent\n2023-10-01 ERROR Connection failed")

        # Instantiate Marginalia
        m = Marginalia(str(root), use_embeddings=True)
        m.ingest()

        # Show catalog size
        print(f"Catalog entries: {len(m.catalog)}")
        for eid, entry in list(m.catalog.items())[:5]:
            print(f" - {entry.path} ({entry.file_type.value})")

        # Add tags
        if m.catalog:
            first = next(iter(m.catalog.values()))
            m.add_tag(first.entry_id, "demo")

        # Recall
        query = "LLM research"
        results = m.recall(query, top_k=3, strategy='lexical')
        print(f"\nRecall results for '{query}':")
        for r in results:
            print(f"  {r.entry_id}: {r.score:.3f}")

        # Answer
        answer_text, citations, note = m.answer(query, window_size=5)
        print(f"\nAnswer for '{query}':\n{answer_text}")
        print("Citations:")
        for cit in citations:
            print(f"  {cit.location}")

        # Search notes (just created)
        notes = m.search_notes("LLM")
        print(f"\nFound {len(notes)} investigation notes.")

        print("\nJournal entries:")
        for entry in m.journal:
            print(f"  {entry}")

        # Check tags
        related = m.find_related(first.entry_id)
        print(f"Related to {first.path}: {related}")