import os
import hashlib
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_PERSIST_DIR = str(DATA_DIR / "chroma_db")

# Default Knowledge Base Document Paths
DEFAULT_KB_PATHS = [
    str(WORKSPACE_DIR / "docs" / "zuka_website_knowledge_base.md"),
]
DEFAULT_KB_PATH = DEFAULT_KB_PATHS[0]
KB_FILE_PATH = os.environ.get("KB_FILE_PATH", DEFAULT_KB_PATH)


def knowledge_base_fingerprint(file_paths=None) -> str:
    """Return a stable fingerprint for the current knowledge source files."""
    paths = file_paths or DEFAULT_KB_PATHS
    digest = hashlib.sha256()
    for file_path in sorted(str(Path(path).resolve()) for path in paths):
        path = Path(file_path)
        digest.update(b"local-text-index-v1")
        digest.update(path.name.encode("utf-8"))
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()

# Ollama Settings
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "qwen2.5:3b")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")

# Generation Hyperparameters (as required by prompt rules)
TEMPERATURE = 0.1
NUM_CTX = 4096
TOP_K_CHUNKS = 4

# Fallback string (Rule 3)
CONTACT_EMAIL = "chitlakarthik66@gmail.com"
FALLBACK_RESPONSE = "I don't have that information in the project guide. Ask about alerts, incidents, investigations, or reports."

# System Prompt (as required)
SYSTEM_PROMPT = (
    "You are Zuka, the official assistant for the ZUKA SOC website. Answer static factual questions "
    "using only the retrieved CONTEXT. Never use outside knowledge, infer missing details, or invent "
    "prices, dates, hours, policies, links, phone numbers, IDs, or live metrics. Keep answers concise "
    "and cite the retrieved section titles when available. If the context is missing or insufficient, "
    f"reply exactly: {FALLBACK_RESPONSE} "
    "Refuse requests for malware, exploit code, malicious payloads, or unauthorized access, and offer "
    "defensive guidance only when supported by the context."
)

# Vector Store Settings
COLLECTION_NAME = "zuka_soc_kb"

# Chunking Parameters (Rule: 200–400 word chunks with ~50 words overlap)
MIN_CHUNK_WORDS = 200
MAX_CHUNK_WORDS = 400
TARGET_CHUNK_WORDS = 320
CHUNK_OVERLAP_WORDS = 50

# Web Server Settings
SERVER_HOST = "127.0.0.1"
SERVER_PORT = int(os.environ.get("SERVER_PORT", 8005))
