# Quantitative Evaluation Report: Athena RAG System
*Generated: 2026-08-27T16:12:36Z*  
*Total Evaluation Samples: 25 questions*  
*Embedding Model: all-MiniLM-L6-v2*  

---

## 1. Retrieval Performance: Vector vs. Hybrid (Vector + BM25)

| Metric | Vector-Only (Dense) | Hybrid (Dense + BM25 RRF) | Relative Improvement |
|---|---|---|---|
| **Precision@3** | 0.7600 | 0.8133 | +7.01% |
| **Precision@5** | 0.7120 | 0.7600 | +6.74% |
| **Recall@3** | 0.9200 | 1.0000 | +8.70% |
| **Recall@5** | 0.9600 | 1.0000 | +4.17% |
| **MRR (Mean Reciprocal Rank)** | 0.8833 | 0.9267 | +4.91% |

---

## 2. Answer Quality & Confidence Score Calibration

| Metric | Measured Value | Description |
|---|---|---|
| **Mean Semantic Similarity** | `0.7805` | Cosine similarity between generated and ground-truth answer embeddings |
| **Mean Token F1 Score** | `0.2270` | Token-level lexical harmonic mean |
| **High Confidence Tier Avg Sim** | `0.7840` (9 samples, 36%) | Quality of answers tagged as High Confidence |
| **Medium Confidence Tier Avg Sim** | `0.7838` (13 samples, 52%) | Quality of answers tagged as Medium Confidence |
| **Low Confidence Tier Avg Sim** | `0.7554` (3 samples, 12%) | Quality of answers tagged as Low Confidence |

---

## 3. Latency Benchmarks (in milliseconds)

| Pipeline Stage | Mean | Median | Min | Max | P95 |
|---|---|---|---|---|---|
| **Vector Retrieval** | `20.0 ms` | `19.2 ms` | `13.2 ms` | `29.6 ms` | `27.5 ms` |
| **Hybrid Retrieval** | `18.7 ms` | `17.4 ms` | `13.0 ms` | `31.4 ms` | `27.2 ms` |
| **LLM Generation** | `1838.7 ms` | `1924.1 ms` | `1083.1 ms` | `2991.4 ms` | `2807.0 ms` |
| **Total End-to-End** | `1858.7 ms` | `1948.3 ms` | `1101.2 ms` | `3019.7 ms` | `2827.7 ms` |
