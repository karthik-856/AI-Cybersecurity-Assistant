import os
import re
from typing import List, Dict, Any, Optional
import requests
from rag_assistant.vector_index import VectorIndex
from rag_assistant.text_encoder import encode_text

try:
    from config import (
        CHROMA_PERSIST_DIR,
        COLLECTION_NAME,
        OLLAMA_BASE_URL,
        CHAT_MODEL,
        EMBEDDING_MODEL,
        TEMPERATURE,
        NUM_CTX,
        TOP_K_CHUNKS,
        SYSTEM_PROMPT,
        FALLBACK_RESPONSE,
        knowledge_base_fingerprint,
    )
except ImportError:
    from rag_assistant.config import (
        CHROMA_PERSIST_DIR,
        COLLECTION_NAME,
        OLLAMA_BASE_URL,
        CHAT_MODEL,
        EMBEDDING_MODEL,
        TEMPERATURE,
        NUM_CTX,
        TOP_K_CHUNKS,
        SYSTEM_PROMPT,
        FALLBACK_RESPONSE,
        knowledge_base_fingerprint,
    )


class RAGPipeline:
    def __init__(
        self,
        persist_dir: str = CHROMA_PERSIST_DIR,
        collection_name: str = COLLECTION_NAME,
        ollama_url: str = OLLAMA_BASE_URL,
        chat_model: str = CHAT_MODEL,
        embedding_model: str = EMBEDDING_MODEL,
        temperature: float = TEMPERATURE,
        num_ctx: int = NUM_CTX,
        top_k: int = TOP_K_CHUNKS,
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.ollama_url = ollama_url.rstrip("/")
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.top_k = top_k

        self.collection = VectorIndex(self.persist_dir, self.collection_name)

    def embed_query(self, query: str) -> List[float]:
        """Fetch query embedding from Ollama using nomic-embed-text."""
        return encode_text(query)

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Rule 1: Retrieve the top 4 chunks for every question.
        Returns chunk documents and their associated section metadata.
        """
        k = top_k or self.top_k
        query_embedding = self.embed_query(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )

        chunks = []
        if results and results.get("documents") and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            dists = results["distances"][0] if results.get("distances") else [0.0] * len(docs)
            ids = results["ids"][0] if results.get("ids") else [f"c_{i}" for i in range(len(docs))]

            for doc, meta, dist, cid in zip(docs, metas, dists, ids):
                chunks.append({
                    "id": cid,
                    "text": doc,
                    "section": meta.get("section", "Unknown Section"),
                    "distance": dist,
                    "metadata": meta
                })

        return chunks

    def format_prompt(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        """
        Construct prompt enforcing rules:
        - Answer ONLY from retrieved chunks.
        - If answer is not in chunks, output fallback message.
        - Keep answers short, clear, friendly.
        - Never invent facts.
        """
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            section = chunk.get("section", f"Section {i}")
            context_parts.append(
                f"[CONTEXT CHUNK {i} | SECTION: {section}]\n{chunk['text'].strip()}"
            )

        context_str = "\n\n".join(context_parts)

        prompt = f"""CONTEXT:
{context_str}

QUESTION:
{query}

CRITICAL RULES:
1. Answer ONLY using the facts stated in the CONTEXT above. Do not assume or extrapolate.
2. If the context does not contain the answer, you MUST reply exactly:
"{FALLBACK_RESPONSE}"
3. Keep your answer short, clear, friendly, and factual. Use the same language the question is asked in.
4. Never invent prices, dates, links, phone numbers, or operational policies.

ANSWER:"""
        return prompt

    @staticmethod
    def _direct_faq_answer(question: str, chunk: Dict[str, Any]) -> Optional[str]:
        """Return a concise FAQ section directly when retrieval is highly confident."""
        section = str(chunk.get("section", "")).strip()
        if not section.endswith("?") or not re.match(
            r"^(what|why|how|which|where|who|when|does|do|can|is|are)\b",
            section,
            re.IGNORECASE,
        ):
            return None

        # Require both a close semantic match and a shared topic term. This
        # admits common paraphrases while avoiding answers to unrelated queries.
        if float(chunk.get("distance", 1.0)) > 0.90:
            return None
        stop_words = {
            "what", "why", "how", "which", "where", "who", "when", "does", "did", "do", "can",
            "is", "are", "the", "a", "an", "to", "of", "for", "in", "on", "me", "my", "there",
            "show", "tell", "about", "please", "could", "would", "should", "your", "you", "i",
        }
        question_terms = set(re.findall(r"[a-z0-9]+", question.lower())) - stop_words
        chunk_terms = set(re.findall(r"[a-z0-9]+", str(chunk.get("text", "")).lower())) - stop_words
        if not question_terms.intersection(chunk_terms):
            return None

        lines = str(chunk.get("text", "")).splitlines()
        if lines and lines[0].strip().startswith("[") and lines[0].strip().endswith("]"):
            lines = lines[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
        if lines and re.match(r"^#{1,6}\s+", lines[0].strip()):
            lines = lines[1:]

        answer = "\n".join(lines).strip()
        if not answer or len(answer.split()) > 110:
            return None
        return answer

    def query(self, question: str, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes end-to-end RAG:
        1. Retrieve top 4 chunks.
        2. Prompt model.
        3. Enforce exact fallback if information is missing.
        4. Include source section titles.
        """
        active_model = model or self.chat_model

        # Check collection validity
        if self.collection.count() == 0:
            return {
                "question": question,
                "answer": FALLBACK_RESPONSE,
                "formatted_answer": FALLBACK_RESPONSE,
                "sources": [],
                "is_fallback": True,
                "chunks": [],
                "model": active_model,
            }

        # Never generate an answer from an index that does not match the current
        # approved knowledge sources. Old PDF-only chunks can contradict newer
        # website guidance and cause plausible but incorrect answers.
        indexed_fingerprint = (self.collection.metadata or {}).get("source_fingerprint")
        if indexed_fingerprint != knowledge_base_fingerprint():
            return {
                "question": question,
                "answer": FALLBACK_RESPONSE,
                "formatted_answer": FALLBACK_RESPONSE,
                "sources": [],
                "is_fallback": True,
                "chunks": [],
                "model": active_model,
                "index_stale": True,
            }

        # 1. Retrieve top 4 chunks
        chunks = self.retrieve(question, top_k=self.top_k)

        # An empty or not-yet-ingested collection must never be sent to the model
        # as if it were usable context.
        if not chunks:
            return {
                "question": question,
                "answer": FALLBACK_RESPONSE,
                "formatted_answer": FALLBACK_RESPONSE,
                "sources": [],
                "is_fallback": True,
                "chunks": [],
                "model": model or self.chat_model,
            }

        # Extract unique source section titles (preserving order of relevance)
        seen_sections = set()
        sources = []
        for c in chunks:
            sec = c.get("section")
            if sec and sec not in seen_sections:
                seen_sections.add(sec)
                sources.append(sec)

        # Many website questions match a short, reviewed FAQ almost exactly.
        # Return that approved answer directly instead of waiting for a local
        # language model to paraphrase it. Complex or uncertain questions keep
        # using the grounded generation path below.
        direct_answer = self._direct_faq_answer(question, chunks[0])
        if direct_answer:
            source = chunks[0].get("section", "Knowledge Base")
            return {
                "question": question,
                "answer": direct_answer,
                "formatted_answer": f"{direct_answer}\n\nSources:\n- {source}",
                "sources": [source],
                "is_fallback": False,
                "chunks": chunks,
                "model": active_model,
                "fast_path": "matched_faq",
            }

        if os.environ.get("RAG_GENERATION_ENABLED", "false").lower() != "true":
            return {"question": question, "answer": FALLBACK_RESPONSE, "formatted_answer": FALLBACK_RESPONSE,
                    "sources": [], "is_fallback": True, "chunks": chunks, "model": "reviewed-knowledge"}

        # 2. Build prompt
        prompt = self.format_prompt(question, chunks)

        # 3. Call Ollama model with specified temperature and num_ctx
        payload = {
            "model": active_model,
            "system": SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.num_ctx
            }
        }

        try:
            res = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=120
            )
            res.raise_for_status()
            raw_answer = res.json().get("response", "").strip()
        except Exception:
            raw_answer = FALLBACK_RESPONSE

        # 4. Standardize fallback response if model indicated lack of information
        answer = raw_answer
        normalized_lower = raw_answer.lower()
        negative_signals = [
            "don't have that information",
            "do not have that information",
            "doesn't have that information",
            "not mentioned in the context",
            "not provided in the context",
            "context does not contain",
            "no information about",
            "chitlakarthik66@gmail.com",
            "not available in the provided context",
        ]

        if any(signal in normalized_lower for signal in negative_signals):
            answer = FALLBACK_RESPONSE
            # If information was missing, sources were uninformative for this query
            is_fallback = True
        else:
            is_fallback = False

        # Format answer with source section title(s) as required by Rule 6
        if is_fallback:
            formatted_answer = answer
        else:
            source_badge = "\n\nSources:\n" + "\n".join(f"- {s}" for s in sources)
            formatted_answer = f"{answer}{source_badge}"

        return {
            "question": question,
            "answer": answer,
            "formatted_answer": formatted_answer,
            "sources": sources,
            "is_fallback": is_fallback,
            "chunks": chunks,
            "model": active_model
        }


# Quick CLI test
if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "What is the ML detection architecture in ZUKA?"
    rag = RAGPipeline()
    out = rag.query(q)
    print("=" * 60)
    print(f"QUESTION: {out['question']}")
    print("-" * 60)
    print(f"ANSWER:\n{out['formatted_answer']}")
    print("=" * 60)
