import asyncio
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.services.generate import generate_answer
from backend.services.ingest import (
    ingest_file,
    get_collection_stats,
    get_detailed_documents_list,
    get_document_preview,
    delete_document,
    reindex_document,
)
from backend.services.db import (
    init_db,
    create_user,
    get_user_by_email,
    verify_password,
    create_token,
    decode_token,
    get_user_profile,
    update_user_profile,
    change_user_password,
    clear_all_user_conversations,
    get_user_export_data,
    create_conversation,
    get_user_conversations,
    get_conversation,
    update_conversation_title,
    delete_conversation,
    add_message,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_PATH = PROJECT_ROOT / "frontend"
DATA_DIR = Path("/tmp/data") if os.environ.get("VERCEL") else (PROJECT_ROOT / "data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Athena API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

# --- Auth Helper ---
def get_current_user_id(authorization: Optional[str] = Header(None)) -> int:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication token required")
    
    parts = authorization.split(" ")
    token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else authorization
    
    try:
        payload = decode_token(token)
        return int(payload["user_id"])
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired session: {str(e)}")

# --- Request / Response Models ---
class SignupRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    avatar_color: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Chat"

class UpdateConversationRequest(BaseModel):
    title: str

class QueryRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None

class CitationItem(BaseModel):
    id: int
    source: str
    text: str
    location: str

class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    distances: list[float]
    conversation_id: str
    message_id: int
    # Feature 1 — Confidence indicator
    confidence_level: str = "low"   # "high" | "medium" | "low"
    confidence_score: float = 0.0
    num_sources: int = 0
    # Feature 2 — Citations
    citations: list[CitationItem] = []

# --- HTML Page Routes for Browser Navigation ---
@app.get("/login", include_in_schema=False)
def get_login_page():
    return FileResponse(FRONTEND_PATH / "login.html")

@app.get("/signup", include_in_schema=False)
def get_signup_page():
    return FileResponse(FRONTEND_PATH / "signup.html")

@app.get("/", include_in_schema=False)
def get_index_page():
    return FileResponse(FRONTEND_PATH / "index.html")

# --- Authentication Endpoints ---
@app.post("/signup")
def signup(request: SignupRequest):
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    try:
        user = create_user(request.email, request.password, request.display_name)
        return {"status": "success", "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/login")
def login(request: LoginRequest):
    user = get_user_by_email(request.email)

    if not user or not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user["id"], user["email"])
    return {
        "status": "success", 
        "token": token,
        "user": {
            "id": user["id"], 
            "email": user["email"],
            "display_name": user.get("display_name") or user["email"].split("@")[0].capitalize(),
            "avatar_color": user.get("avatar_color") or "#10a37f"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Athena backend is running"}

@app.get("/settings/status")
def settings_status():
    api_key = os.getenv("GEMINI_API_KEY")
    return {
        "configured": bool(api_key),
        "model": "gemini-3.6-flash"
    }

# --- User Profile Endpoints ---
@app.get("/user/profile")
def get_profile(user_id: int = Depends(get_current_user_id)):
    profile = get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Attach knowledge base global stats
    kb_stats = get_collection_stats()
    profile["stats"]["total_documents"] = kb_stats["document_count"]
    profile["stats"]["total_chunks"] = kb_stats["total_chunks"]
    profile["ai_model"] = "gemini-3.6-flash"
    
    return profile

@app.patch("/user/profile")
def edit_profile(
    req: UpdateProfileRequest,
    user_id: int = Depends(get_current_user_id)
):
    updated = update_user_profile(user_id, display_name=req.display_name, avatar_color=req.avatar_color)
    return {"status": "success", "profile": updated}

@app.post("/user/change-password")
def change_password(
    req: ChangePasswordRequest,
    user_id: int = Depends(get_current_user_id)
):
    try:
        change_user_password(user_id, req.old_password, req.new_password)
        return {"status": "success", "message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/user/export")
def export_chats(user_id: int = Depends(get_current_user_id)):
    data = get_user_export_data(user_id)
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": "attachment; filename=athena_conversations.json"}
    )

@app.delete("/user/conversations")
def clear_all_chats(user_id: int = Depends(get_current_user_id)):
    deleted_count = clear_all_user_conversations(user_id)
    return {"status": "success", "deleted_conversations": deleted_count}

# --- Knowledge Base Stats & Ingestion ---
@app.get("/knowledge/stats")
def knowledge_stats(user_id: int = Depends(get_current_user_id)):
    stats = get_collection_stats()
    return stats

@app.get("/knowledge/documents")
def list_knowledge_documents(user_id: int = Depends(get_current_user_id)):
    """Returns detailed metadata and chunk counts for all uploaded documents."""
    return get_detailed_documents_list()

@app.get("/knowledge/documents/{filename}/preview")
def preview_knowledge_document(filename: str, user_id: int = Depends(get_current_user_id)):
    """Returns sample chunks and preview text for a specific document."""
    res = get_document_preview(filename)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@app.delete("/knowledge/documents/{filename}")
def delete_knowledge_document(filename: str, user_id: int = Depends(get_current_user_id)):
    """Removes a document from disk and deletes all its vector embeddings from ChromaDB."""
    success = delete_document(filename)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to delete document '{filename}'")
    return {"status": "success", "message": f"Document '{filename}' removed from knowledge base."}

@app.post("/knowledge/documents/{filename}/reindex")
async def reindex_knowledge_document(filename: str, user_id: int = Depends(get_current_user_id)):
    """Re-chunks and re-embeds an existing document."""
    try:
        chunks_added = await run_in_threadpool(reindex_document, filename)
        return {"status": "success", "filename": filename, "chunks_added": chunks_added}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id)
):
    save_path = DATA_DIR / file.filename
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    # Ingest in threadpool to keep async loop unblocked
    total_added = await run_in_threadpool(ingest_file, str(save_path))
    stats = get_collection_stats()

    return {
        "status": "success",
        "filename": file.filename,
        "chunks_added": total_added,
        "total_chunks": stats["total_chunks"]
    }

# --- Conversation History Endpoints (Claude AI-Style) ---
@app.get("/conversations")
def list_conversations(user_id: int = Depends(get_current_user_id)):
    return get_user_conversations(user_id)

@app.post("/conversations")
def new_conversation(
    req: CreateConversationRequest = CreateConversationRequest(),
    user_id: int = Depends(get_current_user_id)
):
    conv = create_conversation(user_id=user_id, title=req.title or "New Chat")
    return conv

@app.get("/conversations/{conversation_id}")
def load_conversation(conversation_id: str, user_id: int = Depends(get_current_user_id)):
    conv = get_conversation(conversation_id, user_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

@app.patch("/conversations/{conversation_id}")
def rename_conversation(
    conversation_id: str,
    req: UpdateConversationRequest,
    user_id: int = Depends(get_current_user_id)
):
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    ok = update_conversation_title(conversation_id, user_id, req.title.strip())
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "title": req.title.strip()}

@app.delete("/conversations/{conversation_id}")
def remove_conversation(conversation_id: str, user_id: int = Depends(get_current_user_id)):
    ok = delete_conversation(conversation_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success"}

# --- Query with Conversation History Integration ---
@app.post("/query")
async def query_athena(
    request: QueryRequest,
    user_id: int = Depends(get_current_user_id)
):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # 1. Resolve or create conversation
    conv_id = request.conversation_id
    conv = None
    if conv_id:
        conv = get_conversation(conv_id, user_id)
    
    if not conv:
        # Create a new conversation with auto-generated title
        auto_title = question[:35] + ("..." if len(question) > 35 else "")
        conv = create_conversation(user_id=user_id, title=auto_title)
        conv_id = conv["id"]
    elif conv.get("title") == "New Chat":
        # Auto-update placeholder title from first question
        auto_title = question[:35] + ("..." if len(question) > 35 else "")
        update_conversation_title(conv_id, user_id, auto_title)

    # 2. Record user message
    user_msg = add_message(conv_id, sender="user", text=question)

    # 3. Retrieve and generate answer in threadpool
    history = conv.get("messages", [])
    result = await run_in_threadpool(generate_answer, question, 4, history)

    # 4. Record assistant message
    asst_msg = add_message(
        conv_id,
        sender="athena",
        text=result["answer"],
        sources=result["sources"]
    )

    confidence = result.get("confidence", {"level": "low", "score": 0.0, "num_sources": 0})
    raw_citations = result.get("citations", [])
    citation_items = [
        CitationItem(
            id=c["id"],
            source=c["source"],
            text=c["text"],
            location=c.get("location", ""),
        )
        for c in raw_citations
    ]

    return QueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        distances=result.get("distances", []),
        conversation_id=conv_id,
        message_id=asst_msg["id"],
        confidence_level=confidence.get("level", "low"),
        confidence_score=confidence.get("score", 0.0),
        num_sources=confidence.get("num_sources", 0),
        citations=citation_items,
    )

# Serve frontend static assets
if FRONTEND_PATH.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_PATH), html=True), name="frontend")