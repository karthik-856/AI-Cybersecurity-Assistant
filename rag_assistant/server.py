import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Header, Depends
import secrets
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from rag_assistant.config import (
    SERVER_HOST,
    SERVER_PORT,
    CHAT_MODEL,
    EMBEDDING_MODEL,
    DEFAULT_KB_PATHS,
    KB_FILE_PATH,
    CHROMA_PERSIST_DIR,
    COLLECTION_NAME,
    FALLBACK_RESPONSE,
)
from rag_assistant.rag import RAGPipeline
from rag_assistant.ingest import ingest_document, ingest_documents

app = FastAPI(
    title="ZUKA Operations RAG Assistant API",
    description="Grounded AI Customer & Operations Assistant for ZUKA SOC Platform",
    version="2.1.0"
)

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "ZUKA_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

# Keep browser access limited to explicitly configured website origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Initialize RAG Pipeline singleton
pipeline = RAGPipeline()

# Define Request and Response Schemas
class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None

class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: List[str]
    is_fallback: bool
    model: str

class IngestRequest(BaseModel):
    file_path: Optional[str] = None
    force_reload: bool = True


@app.get("/api/health")
def health_check():
    """Returns system status, active models, and collection statistics."""
    try:
        count = pipeline.collection.count()
    except Exception:
        count = 0
    return {
        "status": "healthy",
        "chat_model": pipeline.chat_model,
        "embedding_model": pipeline.embedding_model,
        "indexed_chunks": count,
        "kb_file": KB_FILE_PATH,
        "collection": COLLECTION_NAME
    }


@app.get("/api/config")
def get_config():
    """Returns runtime configuration."""
    return {
        "chat_model": pipeline.chat_model,
        "embedding_model": pipeline.embedding_model,
        "top_k": pipeline.top_k,
        "temperature": pipeline.temperature,
        "num_ctx": pipeline.num_ctx,
        "fallback_response": FALLBACK_RESPONSE
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    """Processes user message through the RAG pipeline."""
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    result = pipeline.query(question=req.message.strip(), model=req.model)
    return ChatResponse(
        question=result["question"],
        answer=result["answer"],
        sources=result["sources"],
        is_fallback=result["is_fallback"],
        model=result["model"]
    )


@app.post("/api/ingest")
def trigger_ingest(req: IngestRequest, authorization: str | None = Header(default=None)):
    """Re-ingest the canonical knowledge sources, or one explicitly selected file."""
    expected = os.environ.get("RAG_ADMIN_TOKEN", "")
    if not expected or not authorization or not secrets.compare_digest(authorization, "Bearer " + expected):
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    if req.file_path and Path(req.file_path).resolve() not in {Path(path).resolve() for path in DEFAULT_KB_PATHS}:
        raise HTTPException(status_code=400, detail="Select an approved knowledge source.")
    try:
        if req.file_path:
            ingest_res = ingest_document(
                file_path=req.file_path,
                force_reload=req.force_reload,
            )
        else:
            ingest_res = ingest_documents(
                file_paths=DEFAULT_KB_PATHS,
                force_reload=req.force_reload,
            )
        # Refresh pipeline collection handle
        from rag_assistant.vector_index import VectorIndex
        pipeline.collection = VectorIndex(CHROMA_PERSIST_DIR, COLLECTION_NAME)
        return ingest_res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve static web frontend
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    print(f"Starting ZUKA Operations Assistant server at http://{SERVER_HOST}:{SERVER_PORT}")
    uvicorn.run("server:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)
