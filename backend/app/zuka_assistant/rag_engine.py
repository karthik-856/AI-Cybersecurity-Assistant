from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag_assistant.rag import RAGPipeline
from rag_assistant.config import FALLBACK_RESPONSE, CONTACT_EMAIL

logger = logging.getLogger(__name__)

# Singleton RAG Pipeline instance
_rag_pipeline_instance: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    """Retrieve or initialize the singleton RAG pipeline."""
    global _rag_pipeline_instance
    if _rag_pipeline_instance is None:
        from rag_assistant.rag import RAGPipeline
        logger.info("[ZUKA_RAG] Initializing RAG Pipeline with ChromaDB persistent store...")
        _rag_pipeline_instance = RAGPipeline()
        from rag_assistant.config import knowledge_base_fingerprint
        if _rag_pipeline_instance.collection.count() == 0 or _rag_pipeline_instance.collection.metadata.get("source_fingerprint") != knowledge_base_fingerprint():
            from rag_assistant.ingest import ingest_documents
            ingest_documents()
    return _rag_pipeline_instance


def query_rag(question: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes grounded RAG query using ChromaDB vectors and Ollama qwen2.5:3b.
    Adheres strictly to the 7 Critical Rules:
    1. Retrieve top 4 chunks.
    2. Answer ONLY from retrieved chunks.
    3. If answer not found, return: "I don't have that information. Please contact <chitlakarthik66@gmail.com>."
    4. Short, clear, friendly tone.
    5. Never invent facts.
    6. Show source section title under each answer.
    7. temperature=0.1, num_ctx=4096.
    """
    pipeline = get_rag_pipeline()
    return pipeline.query(question=question, model=model)
