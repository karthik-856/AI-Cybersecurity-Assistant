import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import requests
import chromadb
from chromadb.config import Settings
import pypdf

try:
    from config import (
        CHROMA_PERSIST_DIR,
        COLLECTION_NAME,
        KB_FILE_PATH,
        DEFAULT_KB_PATHS,
        OLLAMA_BASE_URL,
        EMBEDDING_MODEL,
        TARGET_CHUNK_WORDS,
        MAX_CHUNK_WORDS,
        CHUNK_OVERLAP_WORDS,
        knowledge_base_fingerprint,
    )
except ImportError:
    from rag_assistant.config import (
        CHROMA_PERSIST_DIR,
        COLLECTION_NAME,
        KB_FILE_PATH,
        DEFAULT_KB_PATHS,
        OLLAMA_BASE_URL,
        EMBEDDING_MODEL,
        TARGET_CHUNK_WORDS,
        MAX_CHUNK_WORDS,
        CHUNK_OVERLAP_WORDS,
        knowledge_base_fingerprint,
    )


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from a PDF document using pypdf."""
    reader = pypdf.PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n\n".join(pages)


def clean_pdf_artifacts(raw_text: str) -> str:
    """Remove repeating page headers, footers, and classification banners."""
    lines = raw_text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Filter pagination and known repeating footer markers
        if re.search(r"Page \d+ of \d+", stripped, re.IGNORECASE):
            continue
        if "ZUKA SECURITY OPERATIONS CENTER" in stripped:
            continue
        if "AI-ASSISTED SMART DEVICE THREAT MONITORING REFERENCE" in stripped:
            continue
        if "ZUKA SOC PLATFORM  //" in stripped or "ZUKA SOC PLATFORM //" in stripped:
            continue
        if "CLASSIFICATION: INTERNAL RESTRICTED" in stripped:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def split_document_by_headings(cleaned_text: str) -> List[Tuple[str, str]]:
    """
    Split the document into sections based on headings.
    Supports markdown headings (#, ##), numbered major headings (1. System...),
    and document metadata headers.
    """
    # Regex to identify major top-level headings:
    # 1. Numbered major headings (e.g. '1. System Identity & Mission Overview')
    # 2. Markdown headings ('# Title', '## Section')
    heading_pattern = re.compile(
        r"(?m)^(?P<heading>(?:#{1,6}\s+[^\n]+|[1-9]\.\s+[A-Z][A-Za-z0-9\s&()/:,-]{3,70}))\s*$"
    )

    matches = list(heading_pattern.finditer(cleaned_text))

    # Filter out numbered lists that look like procedural steps (e.g., '1. Navigate to...', '1. Zero Hallucination:...')
    # Major section headings in this document have specific titles or are followed by section content
    valid_headings = []
    for m in matches:
        title = m.group("heading").strip()
        # Remove markdown hashes if present and take only the first line of the heading
        clean_title = re.sub(r"^#+\s*", "", title).strip()
        clean_title = clean_title.splitlines()[0].strip()

        # Reject procedural steps starting with action verbs
        if re.match(r"^[1-9]\.\s+(Navigate|Click|Verify|In Incident|Review|Select|Formulate|Open|Return|Once|Confirm)", clean_title):
            continue
        # Reject numbered directives inside Section 9 (1. Zero Hallucination:, 2. SOP Enforcement:)
        if re.match(r"^[1-9]\.\s+(Zero Hallucination|SOP Enforcement|Safety Confirmation|Defensive Boundary|Concise Professionalism):", clean_title):
            continue

        valid_headings.append((m.start(), clean_title))

    sections: List[Tuple[str, str]] = []

    # Handle prelude text before the first section heading
    if valid_headings and valid_headings[0][0] > 0:
        prelude = cleaned_text[:valid_headings[0][0]].strip()
        if prelude:
            sections.append(("Platform Overview & Document Metadata", prelude))

    # Slice between heading markers
    for i, (start_idx, title) in enumerate(valid_headings):
        end_idx = valid_headings[i + 1][0] if i + 1 < len(valid_headings) else len(cleaned_text)
        content = cleaned_text[start_idx:end_idx].strip()
        sections.append((title, content))

    # Fallback if no headings matched
    if not sections:
        sections.append(("General Knowledge Base", cleaned_text.strip()))

    return sections


def chunk_section_text(
    text: str,
    target_words: int = TARGET_CHUNK_WORDS,
    overlap_words: int = CHUNK_OVERLAP_WORDS,
    max_words: int = MAX_CHUNK_WORDS,
) -> List[str]:
    """
    Split text into 200–400 word chunks with ~50 words overlap.
    If the text has <= max_words, returns the entire text as a single coherent chunk.
    """
    words = text.split()
    if len(words) <= max_words:
        return [text]

    chunks = []
    start = 0
    step = max(1, target_words - overlap_words)

    while start < len(words):
        end = min(start + target_words, len(words))
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end >= len(words):
            break
        start += step

    return chunks


def get_embedding(text: str, base_url: str = OLLAMA_BASE_URL, model: str = EMBEDDING_MODEL) -> List[float]:
    """Fetch 768-dim text embedding vector from Ollama nomic-embed-text."""
    return get_embeddings_batch([text], base_url, model)[0]


def get_embeddings_batch(texts: List[str], base_url: str = OLLAMA_BASE_URL, model: str = EMBEDDING_MODEL) -> List[List[float]]:
    """Fetch 768-dim text embedding vectors in batches from Ollama nomic-embed-text."""
    url = f"{base_url.rstrip('/')}/api/embed"
    all_embeddings = []
    batch_size = 16

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            response = requests.post(
                url,
                json={"model": model, "input": batch},
                timeout=120
            )
            if response.status_code == 200:
                data = response.json()
                all_embeddings.extend(data["embeddings"])
                continue
        except Exception:
            pass

        # Fallback to single item legacy calls
        for item in batch:
            legacy_url = f"{base_url.rstrip('/')}/api/embeddings"
            response = requests.post(
                legacy_url,
                json={"model": model, "prompt": item},
                timeout=60
            )
            response.raise_for_status()
            all_embeddings.append(response.json()["embedding"])

    return all_embeddings


def ingest_documents(
    file_paths: List[str] = DEFAULT_KB_PATHS,
    persist_dir: str = CHROMA_PERSIST_DIR,
    collection_name: str = COLLECTION_NAME,
    force_reload: bool = True
) -> Dict[str, Any]:
    """
    Ingests multiple documents (PDF, Markdown, Text) into a single unified Chroma collection.
    """
    prepared_chunks: List[Dict[str, Any]] = []
    chunk_counter = 0

    for file_path in file_paths:
        path = Path(file_path).resolve()
        if not path.exists():
            print(f"[Ingest] Warning: File not found: {path}, skipping.")
            continue

        print(f"[Ingest] Loading document from: {path}")
        if path.suffix.lower() == ".pdf":
            raw_text = extract_text_from_pdf(str(path))
        else:
            with open(path, "r", encoding="utf-8") as f:
                raw_text = f.read()

        cleaned_text = clean_pdf_artifacts(raw_text)
        sections = split_document_by_headings(cleaned_text)
        print(f"[Ingest] Identified {len(sections)} distinct sections in '{path.name}'.")

        for sec_title, sec_content in sections:
            chunks = chunk_section_text(sec_content)
            for sub_idx, chunk_text in enumerate(chunks):
                chunk_counter += 1
                words_count = len(chunk_text.split())
                slug = re.sub(r'[^a-zA-Z0-9]+', '_', sec_title)[:30]
                chunk_id = f"chunk_{chunk_counter:03d}_{slug}"
                full_chunk_text = f"[{sec_title}]\n{chunk_text}" if not chunk_text.startswith(sec_title) else chunk_text
                prepared_chunks.append({
                    "id": chunk_id,
                    "text": full_chunk_text,
                    "metadata": {
                        "section": sec_title,
                        "chunk_index": sub_idx,
                        "total_section_chunks": len(chunks),
                        "word_count": words_count,
                        "source": path.name
                    }
                })

    print(f"[Ingest] Generated {len(prepared_chunks)} total chunks across all documents.")

    # Connect to persistent ChromaDB
    os.makedirs(persist_dir, exist_ok=True)
    client = chromadb.PersistentClient(path=persist_dir)

    if force_reload:
        try:
            client.delete_collection(name=collection_name)
            print(f"[Ingest] Deleted existing Chroma collection: '{collection_name}' for clean reload.")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "ZUKA SOC Master Knowledge Base Chunks"}
    )

    print(f"[Ingest] Batch embedding {len(prepared_chunks)} chunks with model '{EMBEDDING_MODEL}' via Ollama...")
    chunk_texts = [item["text"] for item in prepared_chunks]
    embeddings = get_embeddings_batch(chunk_texts)

    ids = [item["id"] for item in prepared_chunks]
    documents = chunk_texts
    metadatas = [item["metadata"] for item in prepared_chunks]

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings
    )

    collection.modify(metadata={
        **(collection.metadata or {}),
        "description": "ZUKA SOC canonical website knowledge base",
        "source_fingerprint": knowledge_base_fingerprint(file_paths),
    })

    print(f"[Ingest] Ingestion complete! Stored {collection.count()} chunks in persistent ChromaDB.")
    return {
        "status": "success",
        "chunks_indexed": collection.count(),
        "sources": [str(Path(p).resolve()) for p in file_paths],
        "collection": collection_name,
        "persist_dir": persist_dir
    }


def ingest_document(
    file_path: str = KB_FILE_PATH,
    persist_dir: str = CHROMA_PERSIST_DIR,
    collection_name: str = COLLECTION_NAME,
    force_reload: bool = True
) -> Dict[str, Any]:
    return ingest_documents(
        file_paths=[file_path],
        persist_dir=persist_dir,
        collection_name=collection_name,
        force_reload=force_reload
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Knowledge Base into ChromaDB")
    parser.add_argument("--file", "-f", default=None, help="Path to specific knowledge base document (defaults to all knowledge files)")
    parser.add_argument("--no-force", action="store_true", help="Do not wipe existing collection")
    args = parser.parse_args()

    files_to_ingest = [args.file] if args.file else DEFAULT_KB_PATHS
    result = ingest_documents(
        file_paths=files_to_ingest,
        force_reload=not args.no_force
    )
    print(result)
