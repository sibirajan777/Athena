# 🦉 Athena — AI-Powered Personal Knowledge Assistant

> **Final Year Project** · Retrieval-Augmented Generation (RAG) System with Confidence Scoring, Citation Click-Through, and Quantitative Evaluation Framework.

---

## ✨ Features

| Category | Feature |
|---|---|
| 🔍 **Retrieval** | Hybrid Vector + BM25 (RRF fusion) retrieval via ChromaDB |
| 🤖 **Generation** | Gemini API with multi-model circuit-breaker fallback |
| 🎯 **Confidence** | Calibrated confidence tiers (High / Medium / Low) per answer |
| 📎 **Citations** | Clickable citation chips linking answers back to source chunks |
| 📊 **Evaluation** | Full quantitative benchmark framework (Precision@k, Recall@k, MRR, Semantic Similarity) |
| 🔐 **Auth** | JWT-based sign-up / login with conversation history persistence |
| 💾 **Ingestion** | Upload PDF / Markdown / text files and index into ChromaDB |

---

## 🏗️ Architecture

```
┌─────────────────────────────┐
│          Frontend           │  Vanilla HTML + CSS + JS
│  Chat UI · Auth · Citations │  (no framework, fully responsive)
└──────────────┬──────────────┘
               │ REST API
┌──────────────▼──────────────┐
│       FastAPI Backend        │
│  /query · /ingest · /login  │
└──────┬───────────┬───────────┘
       │           │
┌──────▼──────┐ ┌──▼────────────┐
│  ChromaDB   │ │  Gemini API   │
│ Vector Store│ │ (Flash-Lite / │
│ + BM25 RRF  │ │  Flash / etc) │
└─────────────┘ └───────────────┘
```

### Retrieval Pipeline
1. **Dense Vector Retrieval** — `all-MiniLM-L6-v2` embeddings via ChromaDB L2 index.
2. **BM25 Sparse Retrieval** — `rank_bm25` with Okapi BM25 over all indexed chunks.
3. **Reciprocal Rank Fusion (RRF, k=60)** — merges both ranked lists for Hybrid retrieval.

### Confidence Scoring
Calibrated from ChromaDB L2 distances:
- 🟢 **High** — `avg_score ≥ 0.67` OR `max_score ≥ 0.74`
- 🟡 **Medium** — `avg_score ≥ 0.52` OR `max_score ≥ 0.62`
- 🔴 **Low** — below both thresholds

---

## 📈 Quantitative Evaluation Results ($N = 25$ labeled QA pairs)

### Retrieval
| Metric | Vector-Only | Hybrid (BM25 + Vector) | Gain |
|---|---|---|---|
| Precision@3 | 0.7600 | **0.8133** | +7.01% |
| Recall@3 | 0.9200 | **1.0000** | +8.70% |
| MRR | 0.8833 | **0.9267** | +4.91% |

### Generation Quality
| Metric | Value |
|---|---|
| Mean Semantic Cosine Similarity | **0.7805** |
| Mean Token F1 | 0.2270 |
| High-Confidence Tier Coverage | 36% (9/25) |

### Latency (after circuit-breaker fix)
| Stage | Mean | P95 | Max |
|---|---|---|---|
| Hybrid Retrieval | 18.7 ms | 27.2 ms | 31.4 ms |
| LLM Generation | 1838.7 ms | 2807.0 ms | 2991.4 ms |
| End-to-End | 1858.7 ms | 2827.7 ms | 3019.7 ms |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- `uv` package manager (recommended) or `pip`
- A [Gemini API key](https://aistudio.google.com/app/apikey)

### 1. Clone & Install
```bash
git clone https://github.com/sibirajan777/Athena.git
cd Athena

# Using uv (recommended)
uv sync

# Or pip
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

`.env` format:
```env
GEMINI_API_KEY=your_api_key_here
SECRET_KEY=any_random_secret_string
```

### 3. Run
```bash
# Using uv
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Or directly
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in your browser.

---

## 📁 Project Structure

```
Athena/
├── backend/
│   ├── main.py            # FastAPI app & route definitions
│   ├── services/
│   │   ├── generate.py    # Gemini generation + circuit breaker
│   │   ├── retrieve.py    # ChromaDB retrieval
│   │   └── ingest.py      # Document chunking & embedding
│   └── auth.py            # JWT authentication
├── frontend/
│   ├── index.html         # Main chat interface
│   ├── login.html         # Sign-in page
│   ├── signup.html        # Sign-up page
│   ├── app.js             # Chat UI, citations, animations
│   ├── auth.js            # Auth forms & token management
│   └── style.css          # Full application styles
├── evaluate.py            # Standalone quantitative benchmark script
├── eval_dataset.json      # 25 labeled QA pairs for evaluation
├── eval_results.json      # Latest benchmark results (JSON)
├── eval_report.md         # Latest benchmark report (Markdown)
├── eval_comparison.png    # Retrieval comparison chart (300 DPI)
└── pyproject.toml         # Project & dependency configuration
```

---

## 🧪 Running Tests

```bash
# Full system integration tests
python test_full_system.py

# Auth flow tests
python test_auth_flow.py

# Knowledge ingestion flow tests
python test_knowledge_flow.py

# Run the quantitative evaluation benchmark
python evaluate.py
```

---

## 🔑 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | Your Google Gemini API key |
| `SECRET_KEY` | ✅ | JWT signing secret (any long random string) |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built as a Final Year Project demonstrating production-quality RAG system design with quantitative evaluation.*
