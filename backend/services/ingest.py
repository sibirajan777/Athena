import re
import os
from pathlib import Path

# Only enforce offline mode locally when models are pre-cached, allowing Vercel to download on startup
if not os.environ.get("VERCEL"):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

import datetime
import chromadb
from pypdf import PdfReader
try:
    from docx import Document as DocxDocument
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
chroma_path = Path("/tmp/chroma_db") if os.environ.get("VERCEL") else (PROJECT_ROOT / "chroma_db")
DATA_DIR = Path("/tmp/data") if os.environ.get("VERCEL") else (PROJECT_ROOT / "data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ChromaDB client — persists to disk
chroma_client = chromadb.PersistentClient(path=str(chroma_path), settings=chromadb.config.Settings(anonymized_telemetry=False))
collection = chroma_client.get_or_create_collection(name="athena_knowledge")

# Resilient & Lightweight Embedding Adapter
class AthenaEmbedder:
    def __init__(self):
        self._local = None
        try:
            from sentence_transformers import SentenceTransformer
            self._local = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            self._local = None

    def encode(self, texts, show_progress_bar=False, *args, **kwargs):
        if isinstance(texts, str):
            texts = [texts]
        if self._local is not None:
            return self._local.encode(texts, show_progress_bar=show_progress_bar, *args, **kwargs)
        
        # Fast deterministic semantic feature hasher (384-dim, pure NumPy)
        import numpy as np
        import hashlib
        
        embeddings = []
        for text in texts:
            vec = np.zeros(384, dtype=np.float32)
            words = str(text).lower().split()
            for word in words:
                idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % 384
                vec[idx] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            embeddings.append(vec)
        return np.array(embeddings, dtype=np.float32)

embedder = AthenaEmbedder()

def extract_pdf_text(filepath: str) -> list[dict]:
    """
    Extract text from a PDF page-by-page.
    Returns a list of {text, page} dicts so callers can attach page numbers.
    """
    reader = PdfReader(filepath)
    pages = []
    for page_num, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text()
        if page_text and page_text.strip():
            pages.append({"text": page_text, "page": page_num})
    return pages


def extract_docx_text(filepath: str) -> list[dict]:
    """
    Extract text from a DOCX file preserving paragraph/heading structure.
    Returns a list of {text, page} dicts (DOCX has no real page concept;
    we use paragraph index as a surrogate location).
    """
    if not _DOCX_AVAILABLE:
        raise ImportError("python-docx is not installed. Run: pip install python-docx")

    doc = DocxDocument(filepath)
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)

    # Join paragraphs into a single text block; chunk_plain_text will slice it.
    full_text = "\n".join(paragraphs)
    return [{"text": full_text, "page": None}]

def chunk_plain_text(text: str, source: str, chunk_size: int = 800, overlap: int = 150, page: int = None) -> list[dict]:
    chunks = []
    start = 0
    text_length = len(text)
    chunk_index = 0

    while start < text_length:
        end = start + chunk_size
        chunk_text = text[start:end].strip()

        if len(chunk_text) >= 20:
            meta = {"text": chunk_text, "source": source}
            if page is not None:
                meta["page"] = page
            chunks.append(meta)

        start += chunk_size - overlap
        chunk_index += 1

    return chunks

def chunk_markdown(text: str, source: str) -> list[dict]:
    sections = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    chunks = []

    for section in sections:
        section = section.strip()
        if not section or (section.startswith("# ") and "##" not in section):
            continue
        if len(section) < 20:
            continue
        chunks.append({"text": section, "source": source})

    return chunks

def ingest_file(filepath: str) -> int:
    """
    Ingest a single file into ChromaDB.
    Supported formats: .pdf, .md, .txt, .docx
    Returns the number of chunks added.
    """
    path = Path(filepath)
    source = path.name
    suffix = path.suffix.lower()
    chunks = []

    try:
        if suffix == ".pdf":
            pages = extract_pdf_text(filepath)
            for page_data in pages:
                chunks.extend(chunk_plain_text(page_data["text"], source, page=page_data["page"]))

        elif suffix == ".docx":
            pages = extract_docx_text(filepath)
            for page_data in pages:
                chunks.extend(chunk_plain_text(page_data["text"], source))

        elif suffix == ".txt":
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            chunks = chunk_plain_text(text, source)

        else:
            # Default: treat as markdown / plain text
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            chunks = chunk_markdown(text, source)

    except Exception as e:
        print(f"[ingest_file] Error reading '{path.name}': {e}")
        return 0

    if not chunks:
        print(f"No chunks found in {filepath}")
        return 0

    batch_size = 150
    total_added = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]
        embeddings = embedder.encode(texts, batch_size=32, show_progress_bar=False).tolist()
        ids = [f"{source}_{i + j}" for j in range(len(batch))]
        # Include page number in metadata when available
        metadatas = [
            {
                "source": c["source"],
                **({"page": c["page"]} if c.get("page") is not None else {})
            }
            for c in batch
        ]

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        total_added += len(batch)

    print(f"Successfully ingested {total_added} chunks from {source}")
    return total_added

def ingest_folder(folder_path: str = "data"):
    folder = Path(folder_path)
    if not folder.is_absolute():
        folder = PROJECT_ROOT / folder_path

    # Supported extensions (order matters for glob performance)
    SUPPORTED_EXTS = ["*.pdf", "*.md", "*.txt", "*.docx"]
    files = []
    for pattern in SUPPORTED_EXTS:
        files.extend(folder.glob(pattern))

    if not files:
        print(f"No supported files found in {folder}")
        return

    for file in files:
        ingest_file(str(file))

    print(f"\nDone. Total chunks in collection: {collection.count()}")

def get_collection_stats() -> dict:
    try:
        count = collection.count()
        files = []
        if DATA_DIR.exists():
            files = [f.name for f in DATA_DIR.iterdir() if f.is_file()]
        return {
            "total_chunks": count,
            "document_count": len(files),
            "documents": files
        }
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return {
            "total_chunks": 0,
            "document_count": 0,
            "documents": []
        }

def get_detailed_documents_list() -> dict:
    """Returns rich metadata for all documents in the Athena Knowledge Base."""
    try:
        total_chunks = collection.count()
        
        # Calculate chunks per document source from ChromaDB
        source_counts = {}
        try:
            all_meta = collection.get(include=["metadatas"])
            if all_meta and "metadatas" in all_meta and all_meta["metadatas"]:
                for m in all_meta["metadatas"]:
                    if m and "source" in m:
                        src = m["source"]
                        source_counts[src] = source_counts.get(src, 0) + 1
        except Exception as e:
            print(f"Error getting metadatas: {e}")

        docs_list = []
        found_names = set()

        if DATA_DIR.exists():
            for f in sorted(DATA_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if f.is_file():
                    found_names.add(f.name)
                    stat = f.stat()
                    size_bytes = stat.st_size
                    if size_bytes < 1024:
                        size_str = f"{size_bytes} B"
                    elif size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes / 1024:.1f} KB"
                    else:
                        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

                    mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y %I:%M %p")
                    doc_type = f.suffix.upper().replace(".", "") or "FILE"
                    chunks = source_counts.get(f.name, 0)

                    docs_list.append({
                        "filename": f.name,
                        "size": size_str,
                        "size_bytes": size_bytes,
                        "type": doc_type,
                        "modified_at": mtime,
                        "chunks": chunks,
                        "indexed": chunks > 0
                    })

        # Add any sources indexed in ChromaDB that may not be on local container disk
        for src, chunks in source_counts.items():
            if src not in found_names:
                ext = Path(src).suffix.upper().replace(".", "") or "PDF"
                docs_list.append({
                    "filename": src,
                    "size": "Indexed",
                    "size_bytes": 0,
                    "type": ext,
                    "modified_at": "Indexed in Athena",
                    "chunks": chunks,
                    "indexed": True
                })

        return {
            "total_chunks": total_chunks,
            "document_count": len(docs_list),
            "documents": docs_list
        }
    except Exception as e:
        print(f"Error getting detailed documents: {e}")
        return {
            "total_chunks": 0,
            "document_count": 0,
            "documents": []
        }

def get_document_preview(filename: str, max_chunks: int = 6) -> dict:
    """Returns sample indexed chunks and text snippets for a given document."""
    try:
        # Query ChromaDB for chunks belonging to this document
        results = collection.get(
            where={"source": filename},
            limit=max_chunks,
            include=["documents", "metadatas"]
        )

        chunks_preview = []
        if results and "documents" in results and results["documents"]:
            for i, doc_text in enumerate(results["documents"]):
                chunks_preview.append({
                    "chunk_id": results["ids"][i] if "ids" in results else f"chunk_{i}",
                    "text": doc_text[:400] + ("..." if len(doc_text) > 400 else "")
                })

        file_path = DATA_DIR / filename
        size_bytes = file_path.stat().st_size if file_path.exists() else 0
        return {
            "filename": filename,
            "size_bytes": size_bytes,
            "total_chunks_found": len(results.get("documents", [])),
            "chunks_preview": chunks_preview
        }
    except Exception as e:
        print(f"Error previewing document {filename}: {e}")
        return {"error": str(e)}

def delete_document(filename: str) -> bool:
    """Deletes a document from the data directory and deletes its chunks from ChromaDB."""
    try:
        # 1. Delete chunks from ChromaDB
        collection.delete(where={"source": filename})
        
        # 2. Delete file from data directory
        file_path = DATA_DIR / filename
        if file_path.exists():
            os.remove(file_path)
            
        print(f"Successfully deleted {filename} and its chunks")
        return True
    except Exception as e:
        print(f"Error deleting document {filename}: {e}")
        return False

def reindex_document(filename: str) -> int:
    """Re-indexes an existing document in the data directory."""
    file_path = DATA_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"File {filename} does not exist")
    
    # Delete old chunks
    try:
        collection.delete(where={"source": filename})
    except Exception:
        pass
    
    # Re-ingest
    return ingest_file(str(file_path))

if __name__ == "__main__":
    ingest_folder("data")
    print(f"Total chunks in collection: {collection.count()}")