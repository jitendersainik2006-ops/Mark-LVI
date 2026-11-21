"""
core/knowledge_manager.py — J.A.R.V.I.S. Human-Provided Knowledge Base & Local RAG Subsystem

Provides an organized, searchable local knowledge store distinct from personal memory:
- Ingests direct text notes, instructions, FAQs, and files (PDF, DOCX, TXT, Markdown, JSON, Code).
- Local semantic chunking with section/page tracking, versioning, and credential scrubbing.
- Local TF-IDF & keyword retrieval engine (using scikit-learn).
- Source attribution, conflict detection, and document version precedence.
- Enable/disable toggles per source and globally.
- Security isolation: imported documents are treated strictly as untrusted DATA to prevent prompt injection.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
SOURCES_FILE = KNOWLEDGE_DIR / "sources.json"
CHUNKS_FILE = KNOWLEDGE_DIR / "chunks.json"
DOCS_DIR = KNOWLEDGE_DIR / "documents"

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into",
    "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our",
    "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's",
    "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs",
    "them", "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't",
    "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's",
    "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't",
    "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
    "yourselves"
}

# Credential filtering patterns (same strict safety as memory manager)
CREDENTIAL_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE),
    re.compile(r"AIza[0-9A-Za-z\-_]{30,45}", re.IGNORECASE),
    re.compile(r"ghp_[a-zA-Z0-9]{36}", re.IGNORECASE),
    re.compile(r"(?:bearer\s+|token\s*[:=]\s*)[a-zA-Z0-9_\-\.]{16,}", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|secret|password|passwd|pwd)\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
]


def redact_credentials(text: str) -> str:
    clean = str(text)
    for p in CREDENTIAL_PATTERNS:
        clean = p.sub("[REDACTED_CREDENTIAL]", clean)
    return clean


@dataclass
class KnowledgeSource:
    id: str
    title: str
    source_type: str  # text, note, file, folder
    file_path: Optional[str] = None
    version: int = 1
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    chunk_count: int = 0
    content_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class KnowledgeChunk:
    id: str
    source_id: str
    source_title: str
    section: str
    text: str
    version: int
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class KnowledgeManager:
    """Singleton Knowledge Base Manager for human-provided documents and reference material."""

    def __init__(self):
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._sources: Dict[str, KnowledgeSource] = {}
        self._chunks: List[KnowledgeChunk] = []
        self._global_enabled: bool = True
        self._vectorizer = None
        self._tfidf_matrix = None
        self._last_disk_mtime: float = 0.0
        self._load()
        self._build_index()

    def _check_reload(self):
        """Auto-reloads sources and chunks from disk if modified by another process/request."""
        try:
            mtime1 = SOURCES_FILE.stat().st_mtime if SOURCES_FILE.exists() else 0
            mtime2 = CHUNKS_FILE.stat().st_mtime if CHUNKS_FILE.exists() else 0
            latest = max(mtime1, mtime2)
            if latest > getattr(self, "_last_disk_mtime", 0.0):
                self._load()
                self._build_index()
                self._last_disk_mtime = latest
        except Exception:
            pass

    def _load(self):
        with self._lock:
            if SOURCES_FILE.exists():
                try:
                    data = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
                    self._global_enabled = data.get("global_enabled", True)
                    self._sources = {}
                    for sid, sdata in data.get("sources", {}).items():
                        self._sources[sid] = KnowledgeSource(**sdata)
                except Exception as e:
                    print(f"[KnowledgeManager] Failed loading sources: {e}")

            if CHUNKS_FILE.exists():
                try:
                    data = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
                    self._chunks = [KnowledgeChunk(**c) for c in data]
                except Exception as e:
                    print(f"[KnowledgeManager] Failed loading chunks: {e}")

            mtime1 = SOURCES_FILE.stat().st_mtime if SOURCES_FILE.exists() else 0
            mtime2 = CHUNKS_FILE.stat().st_mtime if CHUNKS_FILE.exists() else 0
            self._last_disk_mtime = max(mtime1, mtime2)

    def _save(self):
        with self._lock:
            sources_data = {
                "global_enabled": self._global_enabled,
                "sources": {sid: asdict(s) for sid, s in self._sources.items()},
            }
            SOURCES_FILE.write_text(json.dumps(sources_data, indent=2), encoding="utf-8")
            chunks_data = [asdict(c) for c in self._chunks]
            CHUNKS_FILE.write_text(json.dumps(chunks_data, indent=2), encoding="utf-8")
            mtime1 = SOURCES_FILE.stat().st_mtime if SOURCES_FILE.exists() else 0
            mtime2 = CHUNKS_FILE.stat().st_mtime if CHUNKS_FILE.exists() else 0
            self._last_disk_mtime = max(mtime1, mtime2)

    def _build_index(self):
        """Builds local TF-IDF search index across active knowledge chunks."""
        with self._lock:
            active_chunks = [c for c in self._chunks if self._sources.get(c.source_id, KnowledgeSource("", "", "")).enabled]
            if not active_chunks:
                self._vectorizer = None
                self._tfidf_matrix = None
                return

            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                corpus = [c.text for c in active_chunks]
                self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
                self._tfidf_matrix = self._vectorizer.fit_transform(corpus)
            except Exception as e:
                print(f"[KnowledgeManager] Index build note (using keyword fallback): {e}")
                self._vectorizer = None
                self._tfidf_matrix = None

    # ── Document Extraction ──────────────────────────────────────────────────

    def _extract_text_from_file(self, file_path: Path) -> List[Tuple[str, str]]:
        """Extracts text sections from supported document formats.
        Returns a list of (section_name, text_content).
        """
        ext = file_path.suffix.lower()
        sections: List[Tuple[str, str]] = []

        if ext in (".txt", ".md", ".json", ".py", ".yaml", ".yml", ".csv"):
            raw = file_path.read_text(encoding="utf-8", errors="ignore")
            # Split markdown by headings if present
            if ext == ".md":
                parts = re.split(r"(^#+\s+.*$)", raw, flags=re.MULTILINE)
                current_sec = "Introduction"
                current_text = ""
                for part in parts:
                    if part.startswith("#"):
                        if current_text.strip():
                            sections.append((current_sec, current_text.strip()))
                        current_sec = part.strip().lstrip("#").strip()
                        current_text = ""
                    else:
                        current_text += part
                if current_text.strip():
                    sections.append((current_sec, current_text.strip()))
            else:
                sections.append(("Main Content", raw))

        elif ext == ".pdf":
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    for i, page in enumerate(pdf.pages):
                        ptext = page.extract_text() or ""
                        if ptext.strip():
                            sections.append((f"Page {i + 1}", ptext.strip()))
            except Exception:
                try:
                    import pypdfium2
                    pdf = pypdfium2.PdfDocument(file_path)
                    for i, page in enumerate(pdf):
                        textpage = page.get_textpage()
                        ptext = textpage.get_text_range()
                        if ptext.strip():
                            sections.append((f"Page {i + 1}", ptext.strip()))
                except Exception as e:
                    sections.append(("Error", f"Failed reading PDF: {e}"))

        elif ext in (".docx", ".doc"):
            try:
                import docx
                doc = docx.Document(file_path)
                current_sec = "Document"
                current_text = []
                for p in doc.paragraphs:
                    txt = p.text.strip()
                    if not txt:
                        continue
                    if p.style.name.startswith("Heading"):
                        if current_text:
                            sections.append((current_sec, "\n".join(current_text)))
                            current_text = []
                        current_sec = txt
                    else:
                        current_text.append(txt)
                if current_text:
                    sections.append((current_sec, "\n".join(current_text)))
            except Exception as e:
                sections.append(("Error", f"Failed reading DOCX: {e}"))

        elif ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"):
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    w, h = img.size
                    mode = img.mode
                    fmt = img.format or ext.lstrip(".").upper()
                    img_info = f"Format: {fmt}, Dimensions: {w}x{h}, Color Mode: {mode}"

                    # Local OCR attempt if pytesseract is available
                    ocr_text = ""
                    try:
                        import pytesseract
                        ocr_text = pytesseract.image_to_string(img).strip()
                    except Exception:
                        pass

                    if ocr_text:
                        sections.append(("OCR Extracted Text", ocr_text))
                    else:
                        sections.append(("Visual Image Summary", f"Local image file '{file_path.name}'. {img_info}."))
            except Exception as e:
                sections.append(("Error", f"Failed reading Image: {e}"))

        else:
            raw = file_path.read_text(encoding="utf-8", errors="ignore")
            sections.append(("File Content", raw))

        return sections

    def _chunk_text(self, section: str, text: str, chunk_size: int = 600, overlap: int = 80) -> List[Tuple[str, str]]:
        """Splits section text into manageable passages with overlap."""
        clean = redact_credentials(text).strip()
        if not clean:
            return []
        if len(clean) <= chunk_size:
            return [(section, clean)]

        chunks = []
        paras = [p.strip() for p in clean.split("\n\n") if p.strip()]
        cur = ""
        part_idx = 1
        for p in paras:
            if len(cur) + len(p) <= chunk_size:
                cur += ("\n\n" if cur else "") + p
            else:
                if cur:
                    chunks.append((f"{section} (Part {part_idx})", cur))
                    part_idx += 1
                    # Retain overlap from end of cur
                    cur = cur[-overlap:] + "\n\n" + p if overlap < len(cur) else p
                else:
                    # Single paragraph exceeds chunk_size, split by sentences
                    for i in range(0, len(p), chunk_size - overlap):
                        sub = p[i:i + chunk_size]
                        if sub.strip():
                            chunks.append((f"{section} (Part {part_idx})", sub.strip()))
                            part_idx += 1
                    cur = ""
        if cur.strip():
            chunks.append((f"{section} (Part {part_idx})", cur.strip()))

        return chunks

    # ── Source Management ────────────────────────────────────────────────────

    def add_text_knowledge(self, title: str, text: str, metadata: Optional[dict] = None) -> KnowledgeSource:
        """Adds direct text, note, tutorial, or instruction into the knowledge base."""
        clean_text = redact_credentials(text).strip()
        if not clean_text:
            raise ValueError("Knowledge text cannot be empty.")

        source_id = f"src_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        content_hash = hashlib.sha256(clean_text.encode()).hexdigest()[:16]

        # Save copy locally in documents folder
        doc_path = DOCS_DIR / f"{source_id}.txt"
        doc_path.write_text(clean_text, encoding="utf-8")

        # Create chunks
        chunk_tuples = self._chunk_text("Overview", clean_text)
        new_chunks = [
            KnowledgeChunk(
                id=f"{source_id}_c{i+1}",
                source_id=source_id,
                source_title=title,
                section=sec,
                text=txt,
                version=1,
            )
            for i, (sec, txt) in enumerate(chunk_tuples)
        ]

        source = KnowledgeSource(
            id=source_id,
            title=title,
            source_type="text",
            file_path=str(doc_path),
            version=1,
            enabled=True,
            chunk_count=len(new_chunks),
            content_hash=content_hash,
            metadata=metadata or {},
        )

        with self._lock:
            self._sources[source_id] = source
            self._chunks.extend(new_chunks)

        self._save()
        self._build_index()
        return source

    def ingest_text(self, title: str, text: str, section: str = "General", metadata: Optional[dict] = None) -> str:
        """Convenience method to ingest raw text and return the source ID."""
        src = self.add_text_knowledge(title=title, text=text, metadata=metadata)
        return src.id

    def import_file(self, file_path_str: str, title: Optional[str] = None) -> KnowledgeSource:
        """Imports and indexes a single document (PDF, DOCX, TXT, MD, etc.)."""
        p = Path(file_path_str).resolve()
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path_str}")

        doc_title = title or p.stem.replace("_", " ").title()
        sections = self._extract_text_from_file(p)
        if not sections:
            raise ValueError(f"No readable text extracted from {p.name}")

        full_raw = "\n\n".join(t for _, t in sections)
        content_hash = hashlib.sha256(full_raw.encode()).hexdigest()[:16]
        source_id = f"src_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        all_chunk_tuples: List[Tuple[str, str]] = []
        for sec_name, sec_text in sections:
            all_chunk_tuples.extend(self._chunk_text(sec_name, sec_text))

        new_chunks = [
            KnowledgeChunk(
                id=f"{source_id}_c{i+1}",
                source_id=source_id,
                source_title=doc_title,
                section=sec,
                text=txt,
                version=1,
            )
            for i, (sec, txt) in enumerate(all_chunk_tuples)
        ]

        source = KnowledgeSource(
            id=source_id,
            title=doc_title,
            source_type="file",
            file_path=str(p),
            version=1,
            enabled=True,
            chunk_count=len(new_chunks),
            content_hash=content_hash,
            metadata={"filename": p.name, "filesize": p.stat().st_size, "extension": p.suffix.lower()},
        )

        with self._lock:
            self._sources[source_id] = source
            self._chunks.extend(new_chunks)

        self._save()
        self._build_index()
        return source

    def update_source(self, source_id: str, new_text: Optional[str] = None, new_file_path: Optional[str] = None) -> KnowledgeSource:
        """Updates an existing source with a new version, preserving history and reindexing."""
        with self._lock:
            if source_id not in self._sources:
                raise KeyError(f"Source '{source_id}' not found.")
            source = self._sources[source_id]

        new_version = source.version + 1
        all_chunk_tuples: List[Tuple[str, str]] = []

        if new_file_path:
            p = Path(new_file_path).resolve()
            sections = self._extract_text_from_file(p)
            for sec_name, sec_text in sections:
                all_chunk_tuples.extend(self._chunk_text(sec_name, sec_text))
            content_hash = hashlib.sha256(("\n\n".join(t for _, t in sections)).encode()).hexdigest()[:16]
            source.file_path = str(p)
        elif new_text:
            clean = redact_credentials(new_text).strip()
            all_chunk_tuples = self._chunk_text("Overview", clean)
            content_hash = hashlib.sha256(clean.encode()).hexdigest()[:16]
            if source.file_path and Path(source.file_path).exists():
                Path(source.file_path).write_text(clean, encoding="utf-8")
        else:
            # Re-read existing file path
            if source.file_path and Path(source.file_path).exists():
                sections = self._extract_text_from_file(Path(source.file_path))
                for sec_name, sec_text in sections:
                    all_chunk_tuples.extend(self._chunk_text(sec_name, sec_text))
                content_hash = hashlib.sha256(("\n\n".join(t for _, t in sections)).encode()).hexdigest()[:16]
            else:
                raise ValueError("No content or file provided for update.")

        new_chunks = [
            KnowledgeChunk(
                id=f"{source_id}_v{new_version}_c{i+1}",
                source_id=source_id,
                source_title=source.title,
                section=sec,
                text=txt,
                version=new_version,
            )
            for i, (sec, txt) in enumerate(all_chunk_tuples)
        ]

        with self._lock:
            # Remove old chunks for this source
            self._chunks = [c for c in self._chunks if c.source_id != source_id]
            self._chunks.extend(new_chunks)
            source.version = new_version
            source.updated_at = datetime.now().isoformat()
            source.chunk_count = len(new_chunks)
            source.content_hash = content_hash

        self._save()
        self._build_index()
        return source

    def delete_source(self, source_id: str) -> bool:
        """Removes a source and all its indexed chunks. Does NOT touch unrelated user files."""
        with self._lock:
            if source_id not in self._sources:
                return False
            del self._sources[source_id]
            self._chunks = [c for c in self._chunks if c.source_id != source_id]

        self._save()
        self._build_index()
        return True

    def toggle_source(self, source_id: str, enabled: Optional[bool] = None) -> bool:
        """Enables or disables a specific knowledge source."""
        with self._lock:
            if source_id not in self._sources:
                return False
            src = self._sources[source_id]
            src.enabled = not src.enabled if enabled is None else bool(enabled)
            state = src.enabled

        self._save()
        self._build_index()
        return state

    def toggle_knowledge_base(self, enabled: Optional[bool] = None) -> bool:
        """Globally enables or disables the entire knowledge system."""
        with self._lock:
            self._global_enabled = not self._global_enabled if enabled is None else bool(enabled)
            state = self._global_enabled

        self._save()
        self._build_index()
        return state

    def list_sources(self) -> List[dict]:
        """Lists all registered knowledge sources with metadata."""
        self._check_reload()
        with self._lock:
            return [s.to_dict() for s in sorted(self._sources.values(), key=lambda x: x.updated_at, reverse=True)]

    @property
    def sources(self) -> List[dict]:
        """Property returning all registered knowledge sources."""
        return self.list_sources()

    def get_stats(self) -> dict:
        """Returns statistics on active sources, total chunks, and indexing state."""
        self._check_reload()
        with self._lock:
            active_src = sum(1 for s in self._sources.values() if s.enabled)
            total_chunks = len(self._chunks)
            active_chunks = sum(1 for c in self._chunks if self._sources.get(c.source_id, KnowledgeSource("", "", "")).enabled)
            return {
                "total_sources": len(self._sources),
                "active_sources": active_src,
                "total_chunks": total_chunks,
                "active_chunks": active_chunks,
                "global_enabled": self._global_enabled,
                "indexed": self._vectorizer is not None,
            }

    def get_source(self, source_id: str) -> Optional[dict]:
        self._check_reload()
        with self._lock:
            s = self._sources.get(source_id)
            return s.to_dict() if s else None

    def is_enabled(self) -> bool:
        self._check_reload()
        return self._global_enabled


    # ── Search & Context Injection ───────────────────────────────────────────

    def search(self, query: str, top_k: int = 4, min_score: float = 0.6) -> List[dict]:
        """Searches active knowledge chunks using hybrid TF-IDF + Keyword density scoring."""
        self._check_reload()
        if not self._global_enabled:
            return []
        q = query.strip()
        if not q:
            return []

        with self._lock:
            active_chunks = [c for c in self._chunks if self._sources.get(c.source_id, KnowledgeSource("", "", "")).enabled]

        if not active_chunks:
            return []

        scores = np.zeros(len(active_chunks))

        # 1. TF-IDF scoring if vectorizer available
        if self._vectorizer and self._tfidf_matrix is not None:
            try:
                q_vec = self._vectorizer.transform([q])
                from sklearn.metrics.pairwise import cosine_similarity
                sims = cosine_similarity(q_vec, self._tfidf_matrix).flatten()
                if len(sims) == len(active_chunks):
                    # Only give TF-IDF weight if there is real semantic similarity
                    for idx, sim in enumerate(sims):
                        if sim >= 0.20:
                            scores[idx] += sim * 3.0
            except Exception:
                pass

        # 2. Filter out stop words to avoid common English word false positives
        q_tokens = {w for w in re.findall(r"\w+", q.lower()) if w not in STOP_WORDS and len(w) > 1}

        for idx, chunk in enumerate(active_chunks):
            c_text_lower = chunk.text.lower()
            matches = sum(1 for tok in q_tokens if tok in c_text_lower) if q_tokens else 0
            has_phrase = (len(q) >= 4 and q.lower() in c_text_lower)

            # Incidental single-word match on a multi-concept query is rejected as irrelevant
            if len(q_tokens) >= 3 and matches < 2 and not has_phrase:
                scores[idx] = 0.0
                continue

            if q_tokens:
                if (matches >= 2 and (matches / len(q_tokens)) >= 0.25) or (len(q_tokens) <= 2 and matches == len(q_tokens)):
                    scores[idx] += (matches / len(q_tokens)) * 3.5

            # Exact phrase match boost
            if has_phrase:
                scores[idx] += 4.0

            # Title match boost (excluding generic doc words)
            c_title_lower = chunk.source_title.lower()
            if any(tok in c_title_lower for tok in q_tokens if tok not in {"manual", "notes", "guide", "document", "system"}):
                scores[idx] += 1.5

            # Version precedence boost ONLY if chunk actually matched
            if scores[idx] > 0:
                scores[idx] += chunk.version * 0.1

        top_indices = np.argsort(scores)[::-1]
        results = []
        for idx in top_indices:
            if scores[idx] < min_score:
                break
            c = active_chunks[idx]
            results.append({
                "chunk_id": c.id,
                "source_id": c.source_id,
                "source_title": c.source_title,
                "section": c.section,
                "version": c.version,
                "text": c.text,
                "score": float(scores[idx]),
            })
            if len(results) >= top_k:
                break

        return results

    def format_knowledge_context(self, query: str, top_k: int = 3, min_score: float = 0.8) -> str:
        """Retrieves and formats knowledge passages for injection into the Qwen prompt."""
        matches = self.search(query, top_k=top_k, min_score=min_score)
        if not matches:
            return ""

        lines = [
            "\n[HUMAN_PROVIDED_KNOWLEDGE_BASE]",
            "The following verified factual passages were provided by the user. "
            "Use them to answer the user's inquiry accurately. "
            "Always cite the source document name and section. "
            "If the information is not supported by these passages or your general tools, state so honestly.",
        ]

        # Conflict detection check
        sources_used = set(m["source_title"] for m in matches)
        if len(sources_used) > 1:
            lines.append("NOTE: Passages from multiple user sources are retrieved below. If they conflict, highlight the discrepancy.")

        for m in matches:
            lines.append(
                f"\n<<<HUMAN_PROVIDED_KNOWLEDGE source=\"{m['source_title']}\" section=\"{m['section']}\" version=\"v{m['version']}\">>>\n"
                f"{m['text']}\n"
                f"<<<END HUMAN_PROVIDED_KNOWLEDGE>>>"
            )

        return "\n".join(lines)

    def summarize_document(self, source_id: str) -> Dict[str, Any]:
        """Provides a structured summary of an ingested document with section overview and citations."""
        self._check_reload()
        src = self._sources.get(source_id)
        if not src:
            return {"error": f"Source '{source_id}' not found."}

        chunks = [c for c in self._chunks if c.source_id == source_id]
        total_words = sum(len(c.text.split()) for c in chunks)
        sections = list(dict.fromkeys(c.section for c in chunks))

        summary_preview = (chunks[0].text[:300] + "…") if chunks else "No content available."

        return {
            "source_id": src.id,
            "title": src.title,
            "source_type": src.source_type,
            "file_path": src.file_path,
            "version": src.version,
            "chunk_count": len(chunks),
            "total_words": total_words,
            "sections": sections,
            "summary_preview": summary_preview,
            "citation": f"{src.title} (v{src.version})",
        }

    def create_task_from_knowledge(self, source_id: str, task_title: str) -> Dict[str, Any]:
        """Creates an actionable task linked to an ingested knowledge document."""
        summary = self.summarize_document(source_id)
        if "error" in summary:
            return summary
        try:
            # Attempt to register with global TaskManager if writable, otherwise return structured task
            task_dict = {
                "title": task_title,
                "description": f"Task derived from knowledge source '{summary['title']}': {summary['summary_preview'][:150]}",
                "source": f"knowledge:{source_id}",
                "created_at": datetime.now().isoformat(),
                "status": "QUEUED",
            }
            try:
                from core.task_manager import task_manager
                t = task_manager.create_task(
                    title=task_title,
                    description=task_dict["description"],
                    source=task_dict["source"],
                )
                task_dict["id"] = t.id
            except Exception:
                pass
            return {"status": "SUCCESS", "task": task_dict, "source": summary}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}


# Singleton instance
knowledge_manager = KnowledgeManager()

