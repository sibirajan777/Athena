import os
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from backend.services.retrieve import retrieve

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

_client = None

def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        # attempts=1 disables internal SDK tenacity retries so circuit breaker fails over instantly (<100ms)
        _client = genai.Client(
            api_key=api_key,
            http_options=genai.types.HttpOptions(
                retry_options=genai.types.HttpRetryOptions(attempts=1)
            ),
        )
    return _client


# ---------------------------------------------------------------------------
# Model Circuit Breaker & Cooldown Manager
# ---------------------------------------------------------------------------

_MODEL_COOLDOWNS: dict[str, float] = {}

CANDIDATE_MODELS = [
    "gemini-3.5-flash-lite",  # High throughput, fast latency (700ms - 1.5s)
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
]

def get_active_models() -> list[str]:
    now = time.time()
    active = [m for m in CANDIDATE_MODELS if _MODEL_COOLDOWNS.get(m, 0) <= now]
    if not active:
        # If all models are in cooldown, reset to allow a fresh attempt
        _MODEL_COOLDOWNS.clear()
        return CANDIDATE_MODELS
    return active

def mark_model_cooldown(model_name: str, duration_sec: float = 60.0):
    _MODEL_COOLDOWNS[model_name] = time.time() + duration_sec
    print(f"[CircuitBreaker] Model '{model_name}' hit rate-limit/quota -> Cooldown for {duration_sec}s")


# ---------------------------------------------------------------------------
# Feature 1: Calibrated Confidence / Grounding Indicator
# ---------------------------------------------------------------------------

def compute_confidence(chunks: list[dict]) -> dict:
    """
    Derive a calibrated confidence tier from ChromaDB L2 distances.

    ChromaDB returns L2 distances; we convert to a pseudo-cosine score:
        score_i = max(0, 1 - distance_i / 2)   (range 0..1, higher = better)

    Calibrated Tiers:
        high   — avg score >= 0.67 OR top chunk max score >= 0.74
        medium — avg score >= 0.52 OR top chunk max score >= 0.62
        low    — weak grounding / low relevance
    """
    if not chunks:
        return {"level": "low", "score": 0.0, "max_score": 0.0, "num_sources": 0}

    scores = [max(0.0, 1.0 - c.get("distance", 2.0) / 2.0) for c in chunks]
    avg_score = sum(scores) / len(scores)
    max_score = max(scores)
    distinct_sources = len(set(c.get("source", "") for c in chunks))

    if avg_score >= 0.67 or max_score >= 0.74:
        level = "high"
    elif avg_score >= 0.52 or max_score >= 0.62:
        level = "medium"
    else:
        level = "low"

    return {
        "level": level,
        "score": round(avg_score, 3),
        "max_score": round(max_score, 3),
        "num_sources": distinct_sources,
    }


# ---------------------------------------------------------------------------
# Feature 2: Citation-aware prompt builder
# ---------------------------------------------------------------------------

def build_prompt(question: str, chunks: list[dict], history: list[dict] = None) -> tuple[str, list[dict]]:
    """
    Build the Gemini prompt with numbered citation markers [1], [2], … prepended
    to each context chunk so the model can reference them inline.

    Returns:
        (prompt_str, citations_list)

    citations_list is a list of dicts:
        {id, source, text, location}
    where location is "chunk N of M" (page-level info unavailable for plain text;
    PDF page extraction is a stretch goal).
    """
    citations = []
    context_parts = []

    for idx, c in enumerate(chunks, start=1):
        src = c.get("source", "Knowledge Base")
        text = c.get("text", "").strip()

        # Build citation record returned to the frontend
        citations.append({
            "id": idx,
            "source": src,
            "text": text,
            "location": f"chunk {idx} of {len(chunks)}",
        })

        context_parts.append(f"[{idx}] [Document: {src}]\n{text}")

    context_str = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant documents found."

    history_str = ""
    if history:
        recent_history = history[-6:]  # last 3 turns
        formatted_history = []
        for msg in recent_history:
            sender_name = "User" if msg.get("sender") == "user" else "Athena"
            formatted_history.append(f"{sender_name}: {msg.get('text', '')}")
        history_str = "\n".join(formatted_history)

    prompt = f"""You are Athena, an intelligent, helpful, and concise personal knowledge assistant.
You have access to the user's uploaded documents and notes in the context section below.

Instructions:
1. When context from documents is provided, base your answer primarily on that context and explain concepts clearly.
2. Cite the relevant context chunks inline using their reference numbers, e.g. [1] or [2], placed immediately after the sentence they support — exactly as in academic writing.
3. If the user asks a conversational question, greeting, or follow-up regarding past messages in the conversation, respond naturally and politely (no forced citations needed).
4. If the user asks about a specific topic not covered in the context at all, provide a helpful answer if appropriate or let them know you don't have specific notes on that topic and suggest they upload a document.
5. Format your answer with clean Markdown (use bullet points, bold key terms, and code blocks where helpful).

=== Knowledge Base Context ===
{context_str}

"""
    if history_str:
        prompt += f"""=== Conversation History ===
{history_str}

"""

    prompt += f"""=== Current User Question ===
User: {question}

Athena:"""

    return prompt, citations


def generate_answer(question: str, top_k: int = 4, history: list[dict] = None) -> dict:
    question = question.strip()

    if not question:
        return {
            "answer": "Please ask a question.",
            "sources": [],
            "distances": [],
            "citations": [],
            "confidence": {"level": "low", "score": 0.0, "num_sources": 0},
        }

    chunks = retrieve(question, top_k=top_k)

    # Compute confidence from retrieved chunk distances
    confidence = compute_confidence(chunks)

    api_client = get_client()
    if not api_client:
        return {
            "answer": "⚠️ `GEMINI_API_KEY` is not configured in `.env`. Please provide a valid Gemini API key.",
            "sources": [c["source"] for c in chunks],
            "distances": [c["distance"] for c in chunks],
            "citations": [],
            "confidence": confidence,
        }

    prompt, citations = build_prompt(question, chunks, history=history)

    models_to_try = get_active_models()
    answer_text = None
    last_error = None

    for model_name in models_to_try:
        try:
            response = api_client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if response and response.text:
                answer_text = response.text.strip()
                break
        except Exception as e:
            last_error = e
            err_str = str(e)
            print(f"Gemini API error with {model_name}: {e}")
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                mark_model_cooldown(model_name, duration_sec=60.0)
            continue

    if not answer_text:
        if last_error:
            err_str = str(last_error)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                answer_text = "⚠️ Gemini API rate limit reached. Please wait a moment and try asking again."
            else:
                answer_text = f"Sorry, I encountered an issue processing your request with the AI service. Please try again."
        else:
            answer_text = "I couldn't generate a response for that."

    return {
        "answer": answer_text,
        "sources": [c["source"] for c in chunks],
        "distances": [c["distance"] for c in chunks],
        "citations": citations,
        "confidence": confidence,
    }


if __name__ == "__main__":
    q = "what is machine learning"
    res = generate_answer(q)
    print("Answer:", res["answer"])
    print("Sources:", res["sources"])
    print("Confidence:", res["confidence"])
    print("Citations:")
    for cit in res["citations"]:
        print(f"  [{cit['id']}] {cit['source']} — {cit['text'][:80]}…")