# ZUKA RAG Operations & Customer Assistant

A local, zero-hallucination Retrieval-Augmented Generation (RAG) assistant for the **ZUKA SOC Cyber Platform**, built with Python, Ollama, ChromaDB, and FastAPI.

---

## Architecture & Tech Stack

- **LLM Runtime**: [Ollama](https://ollama.ai) (100% on-premises localhost execution).
- **Default Chat Model**: `qwen2.5:3b` (configurable to `qwen2.5:7b`).
- **Embedding Model**: `nomic-embed-text` (768-dimensional embeddings).
- **Vector Store**: [ChromaDB](https://www.trychroma.com) (persistent local storage).
- **Backend API**: [FastAPI](https://fastapi.tiangolo.com) + Uvicorn (Python 3.13).
- **Frontend UI**: Responsive Cybersecurity SOC Operations Chat console (HTML5 / Vanilla CSS / Modern JS).
- **Canonical Knowledge Base**: `docs/zuka_website_knowledge_base.md`.
- **Website Integration**: The signed-in React widget calls the main FastAPI backend at `/api/zuka-assistant/chat`; that route uses this RAG pipeline for documented knowledge questions and database tools for live SOC records.

```
+-------------------------------------------------------------------------+
|                              ZUKA Web UI                                |
|           (FastAPI /api/chat, HTML/CSS/JS with Source Badges)           |
+------------------------------------+------------------------------------+
                                     | (User Question)
                                     v
                        +---------------------------+
                        |  Ollama Embeddings API    |
                        |   ('nomic-embed-text')    |
                        +-------------+-------------+
                                      | (Query Vector)
                                      v
                        +---------------------------+
                        | Persistent ChromaDB Index |
                        | (Top-4 Semantic Chunks)   |
                        +-------------+-------------+
                                      | (Top 4 Chunks + Section Metadata)
                                      v
                        +---------------------------+
                        | Grounded Prompt Assembly  |
                        |  (System Guardrail Rules) |
                        +-------------+-------------+
                                      | (Context + Prompt)
                                      v
                        +---------------------------+
                        |  Local Ollama Generation  |
                        |  (qwen2.5:3b @ temp 0.1)  |
                        +-------------+-------------+
                                      |
                                      v
+-------------------------------------------------------------------------+
| Verified Output: Factual Answer + Source Section Titles                 |
| Fallback: "I don't have that information. Please contact <chitlakarthik66@gmail.com>."
+-------------------------------------------------------------------------+
```

---

## 1. Prerequisites & Model Setup

Ensure Ollama is installed and running on your local machine (`http://localhost:11434`).

Pull the required models:
```bash
# Pull the default 3B chat model
ollama pull qwen2.5:3b

# Pull the text embedding model
ollama pull nomic-embed-text

# (Optional) Pull the 7B model for comparison
ollama pull qwen2.5:7b
```

Verify the models are active:
```bash
ollama list
```

---

## 2. Environment Setup

From the `rag_assistant` directory (or workspace root), install dependencies:

```bash
pip install -r requirements.txt
```

Core dependencies:
- `chromadb>=0.5.0`
- `fastapi>=0.110.0`
- `uvicorn>=0.28.0`
- `requests>=2.31.0`
- `pypdf>=4.0.0`

---

## 3. Knowledge Base Ingestion

The ingestion script extracts document text, cleans repeating headers/footers, segments content by major headings into 200–400 word chunks with ~50 words overlap, embeds each chunk with `nomic-embed-text`, and stores persistent vectors and section metadata in ChromaDB.

The canonical source is `docs/zuka_website_knowledge_base.md`. The PDF and older assistant documents remain reference materials and are not added to the default index, which prevents duplicated or conflicting answers. After changing the canonical file, rebuild the index from the repository root:
```bash
# From repository root
python -m rag_assistant.ingest

# Or specify a custom document path:
python -m rag_assistant.ingest --file "C:/path/to/your/knowledge_base.md"
```

The script is **completely re-runnable**: it replaces the existing RAG collection and indexes the selected source. Ollama must be running with `nomic-embed-text` available. The collection stores a fingerprint of its source; the website assistant returns the configured fallback instead of using an empty or outdated index until the canonical knowledge file has been ingested.

The website assistant uses the main API on port `8000` (configured by the backend launch setup), not the standalone demo server below. Its CORS allowlist is restricted to the local Vite origins, and authenticated assistant requests are rate-limited to 30 per user per minute.

---

## 4. Launching the Chat Web Application

Start the FastAPI web server:

```bash
python server.py
```

The standalone demonstration server binds to `http://127.0.0.1:8005` by default (or `SERVER_PORT`).

- Open your browser to `http://127.0.0.1:8000` to interact with the responsive SOC Operations Assistant.
- Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

---

## 5. Running the Evaluation Benchmark

We provide a comprehensive evaluation suite with 40 questions in `test_questions.json`:
- **32 In-Domain Questions**: Spanning all 9 sections of the authoritative manual.
- **8 Out-of-Domain Questions**: Testing refusal behavior for unmentioned prices, phone numbers, external platforms, and policies.

To run the evaluation:
```bash
# Run benchmark on default model (qwen2.5:3b)
python eval.py

# Run benchmark on 7B model for comparison
python eval.py --model qwen2.5:7b
```

The evaluation script reports:
- **In-Domain Accuracy (%)**: Factual alignment with verified database facts.
- **Out-of-Domain Rejection (%)**: Correctly returning the designated contact fallback without inventing facts.
- **Hallucination Rate (%)**: Percentage of fabricated answers.
- **Average Query Latency (s)**.
- Saves detailed JSON results to `eval_results_<model>.json`.

---

## 6. Model Configuration & Swapping

The model name is configured via `config.py` and can be overridden dynamically:

1. **Environment Variable**:
   ```bash
   # Windows PowerShell
   $env:CHAT_MODEL="qwen2.5:7b"
   python server.py

   # Linux/macOS
   export CHAT_MODEL="qwen2.5:7b"
   python server.py
   ```

2. **Evaluation CLI Flag**:
   ```bash
   python eval.py --model qwen2.5:7b
   ```

3. **In `config.py`**:
   Change `CHAT_MODEL = "qwen2.5:7b"`.

---

## 7. Answering Rules & Safety Policy

1. **Top-4 Retrieval**: Exactly 4 chunks retrieved per query.
2. **Context-Only Grounding**: Answers are derived strictly from retrieved chunks. No outside knowledge or speculation.
3. **Exact Fallback**: If information is absent or insufficient, reply exactly:
   ```
   I don't have that information. Please contact <chitlakarthik66@gmail.com>.
   ```
4. **Tone & Style**: Short, clear, friendly, and matches the language of the prompt.
5. **Zero Fabrication**: Never invents prices, dates, links, phone numbers, or policies.
6. **Source Attribution**: The source section title is displayed under each answer.
7. **Generation Hyperparameters**: `temperature = 0.1`, `num_ctx = 4096`.
