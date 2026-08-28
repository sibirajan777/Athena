"""
Athena RAG Evaluation Framework
================================
Standalone benchmarking script for final year project reporting.

Evaluates:
1. Vector Retrieval vs. Hybrid (Vector + BM25) Retrieval
   - Precision@3, Precision@5, Recall@3, Recall@5, MRR (Mean Reciprocal Rank)
2. Generation Quality
   - Semantic Similarity (Cosine similarity via SentenceTransformer)
   - Lexical Token F1 / Overlap
   - Confidence Calibration
3. Latency Profiling
   - Min, Max, Mean, Median, P95 for Retrieval, Generation, and End-to-End
4. Output
   - Console summary tables
   - eval_results.json
   - eval_report.md (formatted for project documentation)
   - eval_comparison.png (visual comparative chart)

Usage:
    python evaluate.py                  # Full evaluation (all 25 questions)
    python evaluate.py --limit 5        # Quick test with 5 questions
    python evaluate.py --no-generation  # Benchmark retrieval & latency only
"""

import os
import sys
import json
import time
import re
import string
import argparse
from pathlib import Path
import numpy as np

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.ingest import collection, embedder
from backend.services.generate import generate_answer

try:
    from rank_bm25 import BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25_AVAILABLE = False
    print("Warning: rank_bm25 not installed. Install with: pip install rank_bm25")

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    _MATPLOTLIB_AVAILABLE = True
except ImportError:
    _MATPLOTLIB_AVAILABLE = False


# ---------------------------------------------------------------------------
# 1. BM25 & Hybrid Index Builder
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    """Tokenize and lowercase text for BM25 keyword matching."""
    text = text.lower()
    text = re.sub(r'[%s]' % re.escape(string.punctuation), ' ', text)
    tokens = text.split()
    # Remove common short stopwords
    stopwords = {"a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "is", "it", "with", "as", "by", "that", "this"}
    return [t for t in tokens if t not in stopwords and len(t) > 1]


class HybridRetriever:
    """Combines ChromaDB vector search with BM25 keyword retrieval using RRF."""
    def __init__(self, collection, embedder):
        self.collection = collection
        self.embedder = embedder
        self.all_docs = []
        self.all_metas = []
        self.all_ids = []
        self.bm25 = None
        self._build_bm25_index()

    def _build_bm25_index(self):
        data = self.collection.get()
        self.all_docs = data.get("documents", [])
        self.all_metas = data.get("metadatas", [])
        self.all_ids = data.get("ids", [])

        if not self.all_docs or not _BM25_AVAILABLE:
            return

        corpus_tokens = [tokenize(doc) for doc in self.all_docs]
        self.bm25 = BM25Okapi(corpus_tokens)
        print(f"[HybridRetriever] Indexed {len(self.all_docs)} chunks for BM25.")

    def retrieve_vector_only(self, query: str, top_k: int = 5) -> list[dict]:
        """Vector semantic search via ChromaDB."""
        t0 = time.perf_counter()
        q_emb = self.embedder.encode([query.strip()], show_progress_bar=False).tolist()
        results = self.collection.query(
            query_embeddings=q_emb,
            n_results=top_k
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        chunks = []
        if results and results.get("documents") and results["documents"][0]:
            for doc, meta, dist, cid in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
                results["ids"][0]
            ):
                chunks.append({
                    "id": cid,
                    "text": doc,
                    "source": meta.get("source", "Document"),
                    "score": float(1.0 - dist / 2.0),  # converted similarity
                    "distance": float(dist),
                    "rank": len(chunks) + 1
                })
        return chunks, elapsed_ms

    def retrieve_bm25_only(self, query: str, top_k: int = 5) -> list[dict]:
        """BM25 keyword search."""
        if not self.bm25:
            return [], 0.0

        t0 = time.perf_counter()
        query_tokens = tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]
        elapsed_ms = (time.perf_counter() - t0) * 1000

        chunks = []
        for rank, idx in enumerate(top_indices, 1):
            if scores[idx] > 0:
                chunks.append({
                    "id": self.all_ids[idx],
                    "text": self.all_docs[idx],
                    "source": self.all_metas[idx].get("source", "Document"),
                    "score": float(scores[idx]),
                    "rank": rank
                })
        return chunks, elapsed_ms

    def retrieve_hybrid(self, query: str, top_k: int = 5, rrf_k: int = 60) -> list[dict]:
        """
        Hybrid retrieval combining Dense Vector + Sparse BM25 using
        Reciprocal Rank Fusion (RRF):
            RRF_score(d) = sum(1 / (rrf_k + rank_i(d)))
        """
        t0 = time.perf_counter()

        # Fetch candidate pool (top 20 from each)
        pool_size = max(top_k * 4, 20)
        vec_chunks, _ = self.retrieve_vector_only(query, top_k=pool_size)
        bm25_chunks, _ = self.retrieve_bm25_only(query, top_k=pool_size)

        rrf_scores = {}
        chunk_map = {}

        # Vector RRF contribution
        for rank, c in enumerate(vec_chunks, 1):
            cid = c["id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))
            chunk_map[cid] = c

        # BM25 RRF contribution
        for rank, c in enumerate(bm25_chunks, 1):
            cid = c["id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))
            if cid not in chunk_map:
                chunk_map[cid] = c

        # Sort by combined RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:top_k]
        elapsed_ms = (time.perf_counter() - t0) * 1000

        hybrid_chunks = []
        for rank, cid in enumerate(sorted_ids, 1):
            c = chunk_map[cid].copy()
            c["rrf_score"] = round(float(rrf_scores[cid]), 5)
            c["rank"] = rank
            hybrid_chunks.append(c)

        return hybrid_chunks, elapsed_ms


# ---------------------------------------------------------------------------
# 2. Metric Computation Functions
# ---------------------------------------------------------------------------

def is_chunk_relevant(chunk: dict, expected_sources: list[str], key_concepts: list[str] = None) -> bool:
    """
    Check if a retrieved chunk is relevant.
    Criteria:
    1. The chunk source matches one of expected_sources.
    2. If key_concepts are provided, checks for concept phrases or significant keyword co-occurrence.
    """
    source_match = any(exp.lower() in chunk["source"].lower() for exp in expected_sources)
    if not source_match:
        return False

    if not key_concepts:
        return True

    text_lower = chunk["text"].lower()

    # 1. Direct phrase match
    for k in key_concepts:
        if k.lower() in text_lower:
            return True

    # 2. Significant keyword co-occurrence for multi-word concepts
    for k in key_concepts:
        words = [w.lower().strip(string.punctuation) for w in k.split() if len(w) > 3]
        if words and sum(1 for w in words if w in text_lower) >= max(1, len(words) - 1):
            return True

    return False


def compute_retrieval_metrics(retrieved_chunks: list[dict], expected_sources: list[str], key_concepts: list[str] = None, k_list: list[int] = [3, 5]) -> dict:
    """
    Calculate Precision@k, Recall@k, and Reciprocal Rank (RR).
    """
    metrics = {}

    for k in k_list:
        top_k_chunks = retrieved_chunks[:k]
        if not top_k_chunks:
            metrics[f"P@{k}"] = 0.0
            metrics[f"R@{k}"] = 0.0
            continue

        relevant_count = sum(1 for c in top_k_chunks if is_chunk_relevant(c, expected_sources, key_concepts))
        precision_k = relevant_count / k
        # Recall@k (binary hit indicator: did we find at least 1 relevant chunk in top-k)
        recall_k = 1.0 if relevant_count > 0 else 0.0

        metrics[f"P@{k}"] = round(precision_k, 4)
        metrics[f"R@{k}"] = round(recall_k, 4)

    # Reciprocal Rank (RR): 1 / rank of first relevant chunk
    rr = 0.0
    for idx, c in enumerate(retrieved_chunks, 1):
        if is_chunk_relevant(c, expected_sources, key_concepts):
            rr = 1.0 / idx
            break
    metrics["RR"] = round(rr, 4)

    return metrics


def compute_semantic_similarity(generated: str, reference: str, embedder) -> float:
    """Calculate cosine similarity between generated and ground-truth answer embeddings."""
    if not generated or not reference:
        return 0.0
    e_gen = embedder.encode([generated.strip()], show_progress_bar=False)[0]
    e_ref = embedder.encode([reference.strip()], show_progress_bar=False)[0]
    cos_sim = np.dot(e_gen, e_ref) / (np.linalg.norm(e_gen) * np.linalg.norm(e_ref) + 1e-9)
    return round(float(np.clip(cos_sim, 0.0, 1.0)), 4)


def compute_token_f1(generated: str, reference: str) -> float:
    """Calculate token-level F1 overlap score."""
    gen_tokens = tokenize(generated)
    ref_tokens = tokenize(reference)

    if not gen_tokens or not ref_tokens:
        return 0.0

    common = set(gen_tokens) & set(ref_tokens)
    if not common:
        return 0.0

    precision = len(common) / len(gen_tokens)
    recall = len(common) / len(ref_tokens)
    f1 = 2 * (precision * recall) / (precision + recall)
    return round(float(f1), 4)


def compute_percentiles(values: list[float]) -> dict:
    """Calculate summary statistics (mean, median, min, max, p95)."""
    if not values:
        return {"mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "p95": 0.0}
    arr = np.array(values)
    return {
        "mean": round(float(np.mean(arr)), 2),
        "median": round(float(np.median(arr)), 2),
        "min": round(float(np.min(arr)), 2),
        "max": round(float(np.max(arr)), 2),
        "p95": round(float(np.percentile(arr, 95)), 2),
    }


# ---------------------------------------------------------------------------
# 3. Chart Generation
# ---------------------------------------------------------------------------

def generate_comparison_chart(vector_metrics: dict, hybrid_metrics: dict, output_path: str = "eval_comparison.png"):
    """Generate professional comparative bar chart for project report."""
    if not _MATPLOTLIB_AVAILABLE:
        print("[Chart] Matplotlib not available, skipping chart generation.")
        return

    metrics_keys = ["P@3", "P@5", "R@3", "R@5", "MRR"]
    vec_vals = [vector_metrics.get(k, 0.0) for k in metrics_keys]
    hyb_vals = [hybrid_metrics.get(k, 0.0) for k in metrics_keys]

    x = np.arange(len(metrics_keys))
    width = 0.35

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)

    rects1 = ax.bar(x - width/2, vec_vals, width, label="Dense Vector Only", color="#4f46e5", alpha=0.9, edgecolor="none")
    rects2 = ax.bar(x + width/2, hyb_vals, width, label="Hybrid (Vector + BM25)", color="#059669", alpha=0.9, edgecolor="none")

    ax.set_ylabel("Score (0.0 – 1.0)", fontsize=11, fontweight="600")
    ax.set_title("Athena Retrieval Performance: Dense Vector vs. Hybrid Retrieval", fontsize=13, fontweight="700", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics_keys, fontsize=11, fontweight="600")
    ax.set_ylim(0, 1.15)
    ax.legend(frameon=True, facecolor="white", edgecolor="#e5e7eb", fontsize=10)

    # Attach value labels on bars
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f"{height:.2f}",
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center", va="bottom", fontsize=9, fontweight="600")

    autolabel(rects1)
    autolabel(rects2)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"[Chart] Saved comparison chart to {output_path}")


# ---------------------------------------------------------------------------
# 4. Main Evaluation Runner
# ---------------------------------------------------------------------------

def run_evaluation(dataset_path: str = "eval_dataset.json", limit: int = None, run_generation: bool = True):
    print("=" * 70)
    print("  ATHENA FINAL YEAR PROJECT: RAG SYSTEM QUANTITATIVE BENCHMARK")
    print("=" * 70)

    dataset_file = Path(dataset_path)
    if not dataset_file.is_absolute():
        dataset_file = PROJECT_ROOT / dataset_path

    if not dataset_file.exists():
        print(f"Error: Dataset file not found at {dataset_file}")
        return

    with open(dataset_file, "r", encoding="utf-8") as f:
        test_set = json.load(f)

    if limit and limit > 0:
        test_set = test_set[:limit]

    print(f"Loaded {len(test_set)} evaluation test cases from {dataset_file.name}\n")

    retriever = HybridRetriever(collection, embedder)

    vec_results_all = []
    hyb_results_all = []
    gen_results_all = []

    vec_latencies = []
    hyb_latencies = []
    gen_latencies = []
    e2e_latencies = []

    print(f"{'ID':<5} | {'Category':<22} | {'Vec P@3':<8} | {'Hyb P@3':<8} | {'Vec MRR':<8} | {'Hyb MRR':<8} | {'Sim':<6} | {'Conf':<6}")
    print("-" * 96)

    for item in test_set:
        qid = item["id"]
        category = item.get("category", "General")
        question = item["question"]
        ref_answer = item["reference_answer"]
        expected_sources = item.get("expected_sources", [])
        key_concepts = item.get("key_concepts", [])

        # 1. Vector Retrieval
        vec_chunks, v_lat = retriever.retrieve_vector_only(question, top_k=5)
        vec_m = compute_retrieval_metrics(vec_chunks, expected_sources, key_concepts, k_list=[3, 5])
        vec_latencies.append(v_lat)
        vec_results_all.append(vec_m)

        # 2. Hybrid Retrieval
        hyb_chunks, h_lat = retriever.retrieve_hybrid(question, top_k=5)
        hyb_m = compute_retrieval_metrics(hyb_chunks, expected_sources, key_concepts, k_list=[3, 5])
        hyb_latencies.append(h_lat)
        hyb_results_all.append(hyb_m)

        # 3. Answer Generation (if enabled)
        gen_answer = ""
        sem_sim = 0.0
        tok_f1 = 0.0
        conf_level = "low"
        conf_score = 0.0
        g_lat = 0.0

        if run_generation:
            t0 = time.perf_counter()
            gen_res = generate_answer(question, top_k=4)
            g_lat = (time.perf_counter() - t0) * 1000
            gen_latencies.append(g_lat)
            e2e_latencies.append(v_lat + g_lat)

            gen_answer = gen_res.get("answer", "")
            confidence = gen_res.get("confidence", {})
            conf_level = confidence.get("level", "low")
            conf_score = confidence.get("score", 0.0)

            sem_sim = compute_semantic_similarity(gen_answer, ref_answer, embedder)
            tok_f1 = compute_token_f1(gen_answer, ref_answer)

            gen_results_all.append({
                "id": qid,
                "question": question,
                "semantic_similarity": sem_sim,
                "token_f1": tok_f1,
                "confidence_level": conf_level,
                "confidence_score": conf_score,
                "generated_answer": gen_answer,
                "reference_answer": ref_answer
            })
            # Small delay to respect rate limits
            time.sleep(0.6)

        sim_str = f"{sem_sim:.2f}" if run_generation else "N/A"
        conf_str = conf_level[:4] if run_generation else "N/A"

        print(f"{qid:<5} | {category[:22]:<22} | {vec_m['P@3']:<8.2f} | {hyb_m['P@3']:<8.2f} | {vec_m['RR']:<8.2f} | {hyb_m['RR']:<8.2f} | {sim_str:<6} | {conf_str:<6}", flush=True)

    # ---------------------------------------------------------------------------
    # Aggregate Metrics Computation
    # ---------------------------------------------------------------------------
    avg_vec = {
        "P@3": round(float(np.mean([m["P@3"] for m in vec_results_all])), 4),
        "P@5": round(float(np.mean([m["P@5"] for m in vec_results_all])), 4),
        "R@3": round(float(np.mean([m["R@3"] for m in vec_results_all])), 4),
        "R@5": round(float(np.mean([m["R@5"] for m in vec_results_all])), 4),
        "MRR": round(float(np.mean([m["RR"] for m in vec_results_all])), 4),
    }

    avg_hyb = {
        "P@3": round(float(np.mean([m["P@3"] for m in hyb_results_all])), 4),
        "P@5": round(float(np.mean([m["P@5"] for m in hyb_results_all])), 4),
        "R@3": round(float(np.mean([m["R@3"] for m in hyb_results_all])), 4),
        "R@5": round(float(np.mean([m["R@5"] for m in hyb_results_all])), 4),
        "MRR": round(float(np.mean([m["RR"] for m in hyb_results_all])), 4),
    }

    gen_summary = {}
    if run_generation and gen_results_all:
        sims = [g["semantic_similarity"] for g in gen_results_all]
        f1s = [g["token_f1"] for g in gen_results_all]
        high_sims = [g["semantic_similarity"] for g in gen_results_all if g["confidence_level"] == "high"]
        med_sims = [g["semantic_similarity"] for g in gen_results_all if g["confidence_level"] == "medium"]
        low_sims = [g["semantic_similarity"] for g in gen_results_all if g["confidence_level"] == "low"]

        gen_summary = {
            "mean_semantic_similarity": round(float(np.mean(sims)), 4) if sims else 0.0,
            "median_semantic_similarity": round(float(np.median(sims)), 4) if sims else 0.0,
            "mean_token_f1": round(float(np.mean(f1s)), 4) if f1s else 0.0,
            "high_conf_avg_similarity": round(float(np.mean(high_sims)), 4) if high_sims else None,
            "medium_conf_avg_similarity": round(float(np.mean(med_sims)), 4) if med_sims else None,
            "low_conf_avg_similarity": round(float(np.mean(low_sims)), 4) if low_sims else None,
            "tier_distribution": {
                "high": len(high_sims),
                "medium": len(med_sims),
                "low": len(low_sims),
                "total": len(gen_results_all)
            }
        }

    latency_summary = {
        "vector_retrieval_ms": compute_percentiles(vec_latencies),
        "hybrid_retrieval_ms": compute_percentiles(hyb_latencies),
        "generation_ms": compute_percentiles(gen_latencies) if run_generation else {},
        "end_to_end_ms": compute_percentiles(e2e_latencies) if run_generation else {},
    }

    # ---------------------------------------------------------------------------
    # Print Executive Summary
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 70, flush=True)
    print("  EXECUTIVE SUMMARY: RETRIEVAL & GENERATION BENCHMARKS", flush=True)
    print("=" * 70, flush=True)
    print(f"\n1. RETRIEVAL PERFORMANCE COMPARISON (N = {len(test_set)}):", flush=True)
    print(f"{'Metric':<15} | {'Vector-Only':<15} | {'Hybrid (Vector+BM25)':<22} | {'Relative Gain':<12}", flush=True)
    print("-" * 70, flush=True)
    for m_key in ["P@3", "P@5", "R@3", "R@5", "MRR"]:
        v_val = avg_vec[m_key]
        h_val = avg_hyb[m_key]
        gain = ((h_val - v_val) / v_val * 100) if v_val > 0 else 0.0
        print(f"{m_key:<15} | {v_val:<15.4f} | {h_val:<22.4f} | {gain:+6.2f}%", flush=True)

    if run_generation and gen_summary:
        td = gen_summary["tier_distribution"]
        def fmt_cli_tier(val, count):
            return f"{val:.4f} ({count} samples)" if (count > 0 and val is not None) else "N/A (0 samples)"

        print(f"\n2. GENERATION ACCURACY & CONFIDENCE CALIBRATION:", flush=True)
        print(f"  • Mean Semantic Similarity (Cosine): {gen_summary['mean_semantic_similarity']:.4f}", flush=True)
        print(f"  • Mean Token F1 Overlap:             {gen_summary['mean_token_f1']:.4f}", flush=True)
        print(f"  • High-Confidence Tier Avg Sim:      {fmt_cli_tier(gen_summary['high_conf_avg_similarity'], td['high'])}", flush=True)
        print(f"  • Medium-Confidence Tier Avg Sim:    {fmt_cli_tier(gen_summary['medium_conf_avg_similarity'], td['medium'])}", flush=True)
        print(f"  • Low-Confidence Tier Avg Sim:       {fmt_cli_tier(gen_summary['low_conf_avg_similarity'], td['low'])}", flush=True)
        print(f"  • Confidence Tier Distribution:      High: {td['high']} ({td['high']/td['total']*100:.0f}%), Med: {td['medium']} ({td['medium']/td['total']*100:.0f}%), Low: {td['low']} ({td['low']/td['total']*100:.0f}%)", flush=True)

    print(f"\n3. LATENCY BENCHMARKS (milliseconds):", flush=True)
    print(f"{'Pipeline Stage':<25} | {'Mean (ms)':<10} | {'Median':<10} | {'Min':<8} | {'Max':<8} | {'P95 (ms)':<8}", flush=True)
    print("-" * 75, flush=True)
    for stage, stats in latency_summary.items():
        if stats:
            print(f"{stage:<25} | {stats['mean']:<10.1f} | {stats['median']:<10.1f} | {stats['min']:<8.1f} | {stats['max']:<8.1f} | {stats['p95']:<8.1f}", flush=True)

    # ---------------------------------------------------------------------------
    # Save Outputs: JSON, Markdown Report, Chart
    # ---------------------------------------------------------------------------
    final_output = {
        "metadata": {
            "total_test_cases": len(test_set),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "embedding_model": "all-MiniLM-L6-v2",
            "generator_model": "gemini-3.5-flash-lite / fallback tier"
        },
        "retrieval_comparison": {
            "vector_only": avg_vec,
            "hybrid_vector_bm25": avg_hyb
        },
        "generation_quality": gen_summary,
        "latency_benchmarks": latency_summary,
        "individual_results": gen_results_all
    }

    results_file = PROJECT_ROOT / "eval_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)
    print(f"\n[Saved] Machine-readable metrics: {results_file}", flush=True)

    # Generate Markdown Report
    report_file = PROJECT_ROOT / "eval_report.md"
    generate_markdown_report(final_output, report_file)
    print(f"[Saved] Final Year Project Markdown Report: {report_file}", flush=True)

    # Generate Chart
    chart_file = PROJECT_ROOT / "eval_comparison.png"
    generate_comparison_chart(avg_vec, avg_hyb, str(chart_file))


def generate_markdown_report(data: dict, output_file: Path):
    """Format quantitative results as clean markdown tables for academic report inclusion."""
    ret_vec = data["retrieval_comparison"]["vector_only"]
    ret_hyb = data["retrieval_comparison"]["hybrid_vector_bm25"]
    gen = data.get("generation_quality", {})
    lat = data.get("latency_benchmarks", {})
    td = gen.get("tier_distribution", {"high": 0, "medium": 0, "low": 0, "total": data["metadata"]["total_test_cases"]})

    def fmt_md_tier(val, count):
        if count == 0 or val is None:
            return "N/A (0 samples)"
        total = td.get("total", 1)
        pct = (count / total * 100) if total > 0 else 0
        return f"`{val:.4f}` ({count} samples, {pct:.0f}%)"

    content = f"""# Quantitative Evaluation Report: Athena RAG System
*Generated: {data['metadata']['timestamp']}*  
*Total Evaluation Samples: {data['metadata']['total_test_cases']} questions*  
*Embedding Model: {data['metadata']['embedding_model']}*  

---

## 1. Retrieval Performance: Vector vs. Hybrid (Vector + BM25)

| Metric | Vector-Only (Dense) | Hybrid (Dense + BM25 RRF) | Relative Improvement |
|---|---|---|---|
| **Precision@3** | {ret_vec['P@3']:.4f} | {ret_hyb['P@3']:.4f} | {((ret_hyb['P@3']-ret_vec['P@3'])/ret_vec['P@3']*100) if ret_vec['P@3']>0 else 0:+.2f}% |
| **Precision@5** | {ret_vec['P@5']:.4f} | {ret_hyb['P@5']:.4f} | {((ret_hyb['P@5']-ret_vec['P@5'])/ret_vec['P@5']*100) if ret_vec['P@5']>0 else 0:+.2f}% |
| **Recall@3** | {ret_vec['R@3']:.4f} | {ret_hyb['R@3']:.4f} | {((ret_hyb['R@3']-ret_vec['R@3'])/ret_vec['R@3']*100) if ret_vec['R@3']>0 else 0:+.2f}% |
| **Recall@5** | {ret_vec['R@5']:.4f} | {ret_hyb['R@5']:.4f} | {((ret_hyb['R@5']-ret_vec['R@5'])/ret_vec['R@5']*100) if ret_vec['R@5']>0 else 0:+.2f}% |
| **MRR (Mean Reciprocal Rank)** | {ret_vec['MRR']:.4f} | {ret_hyb['MRR']:.4f} | {((ret_hyb['MRR']-ret_vec['MRR'])/ret_vec['MRR']*100) if ret_vec['MRR']>0 else 0:+.2f}% |

---

## 2. Answer Quality & Confidence Score Calibration

| Metric | Measured Value | Description |
|---|---|---|
| **Mean Semantic Similarity** | `{gen.get('mean_semantic_similarity', 0.0):.4f}` | Cosine similarity between generated and ground-truth answer embeddings |
| **Mean Token F1 Score** | `{gen.get('mean_token_f1', 0.0):.4f}` | Token-level lexical harmonic mean |
| **High Confidence Tier Avg Sim** | {fmt_md_tier(gen.get('high_conf_avg_similarity'), td['high'])} | Quality of answers tagged as High Confidence |
| **Medium Confidence Tier Avg Sim** | {fmt_md_tier(gen.get('medium_conf_avg_similarity'), td['medium'])} | Quality of answers tagged as Medium Confidence |
| **Low Confidence Tier Avg Sim** | {fmt_md_tier(gen.get('low_conf_avg_similarity'), td['low'])} | Quality of answers tagged as Low Confidence |

---

## 3. Latency Benchmarks (in milliseconds)

| Pipeline Stage | Mean | Median | Min | Max | P95 |
|---|---|---|---|---|---|
| **Vector Retrieval** | `{lat.get('vector_retrieval_ms', {}).get('mean', 0.0):.1f} ms` | `{lat.get('vector_retrieval_ms', {}).get('median', 0.0):.1f} ms` | `{lat.get('vector_retrieval_ms', {}).get('min', 0.0):.1f} ms` | `{lat.get('vector_retrieval_ms', {}).get('max', 0.0):.1f} ms` | `{lat.get('vector_retrieval_ms', {}).get('p95', 0.0):.1f} ms` |
| **Hybrid Retrieval** | `{lat.get('hybrid_retrieval_ms', {}).get('mean', 0.0):.1f} ms` | `{lat.get('hybrid_retrieval_ms', {}).get('median', 0.0):.1f} ms` | `{lat.get('hybrid_retrieval_ms', {}).get('min', 0.0):.1f} ms` | `{lat.get('hybrid_retrieval_ms', {}).get('max', 0.0):.1f} ms` | `{lat.get('hybrid_retrieval_ms', {}).get('p95', 0.0):.1f} ms` |
| **LLM Generation** | `{lat.get('generation_ms', {}).get('mean', 0.0):.1f} ms` | `{lat.get('generation_ms', {}).get('median', 0.0):.1f} ms` | `{lat.get('generation_ms', {}).get('min', 0.0):.1f} ms` | `{lat.get('generation_ms', {}).get('max', 0.0):.1f} ms` | `{lat.get('generation_ms', {}).get('p95', 0.0):.1f} ms` |
| **Total End-to-End** | `{lat.get('end_to_end_ms', {}).get('mean', 0.0):.1f} ms` | `{lat.get('end_to_end_ms', {}).get('median', 0.0):.1f} ms` | `{lat.get('end_to_end_ms', {}).get('min', 0.0):.1f} ms` | `{lat.get('end_to_end_ms', {}).get('max', 0.0):.1f} ms` | `{lat.get('end_to_end_ms', {}).get('p95', 0.0):.1f} ms` |
"""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Athena RAG Quantitative Evaluation Framework")
    parser.add_argument("--dataset", type=str, default="eval_dataset.json", help="Path to evaluation dataset JSON")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of evaluation questions")
    parser.add_argument("--no-generation", action="store_true", help="Skip LLM generation, only benchmark retrieval")
    args = parser.parse_args()

    run_evaluation(
        dataset_path=args.dataset,
        limit=args.limit,
        run_generation=not args.no_generation
    )
