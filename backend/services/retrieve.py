from backend.services.ingest import embedder, collection

def retrieve(query: str, top_k: int = 4, max_distance: float = 1.85) -> list[dict]:
    if not query or not query.strip():
        return []

    try:
        count = collection.count()
        if count == 0:
            return []

        actual_k = min(top_k, count)
        query_embedding = embedder.encode([query.strip()], show_progress_bar=False).tolist()

        results = collection.query(
            query_embeddings=query_embedding,
            n_results=actual_k,
        )

        if not results or not results["documents"] or not results["documents"][0]:
            return []

        chunks = []
        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            if distance <= max_distance:
                chunks.append({
                    "text": doc,
                    "source": meta["source"] if meta and "source" in meta else "Document",
                    "distance": float(distance)
                })

        # If strict threshold filtered everything but we have results with reasonable distance,
        # return top 2 to ensure broad questions still get context
        if not chunks and len(results["documents"][0]) > 0:
            for doc, meta, distance in zip(
                results["documents"][0][:2],
                results["metadatas"][0][:2],
                results["distances"][0][:2]
            ):
                chunks.append({
                    "text": doc,
                    "source": meta["source"] if meta and "source" in meta else "Document",
                    "distance": float(distance)
                })

        return chunks
    except Exception as e:
        print(f"Retrieval error: {e}")
        return []

if __name__ == "__main__":
    query = "what is machine learning"
    results = retrieve(query, top_k=3)

    for i, r in enumerate(results):
        print(f"\n--- Match {i+1} (distance: {r['distance']:.4f}, source: {r['source']}) ---")
        print(r["text"][:150], "...")