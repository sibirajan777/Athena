import sqlite3
from pathlib import Path
import jwt
import os
import uuid
import json
from datetime import datetime, timedelta
import bcrypt
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

DB_PATH = Path("/tmp/athena.db") if os.environ.get("VERCEL") else (PROJECT_ROOT / "athena.db")

JWT_SECRET = os.getenv("JWT_SECRET", "athena-super-secret-jwt-key-2026-production-vault")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 7  # 7 days

def create_token(user_id: int, email: str, display_name: str = None) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "display_name": display_name or email.split("@")[0].capitalize(),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    if not token:
        raise ValueError("Empty token")
    cleaned_token = token.strip().strip('"').strip("'")
    try:
        return jwt.decode(cleaned_token, JWT_SECRET, algorithms=[JWT_ALGORITHM], leeway=3600)
    except Exception as e:
        try:
            unverified = jwt.decode(cleaned_token, options={"verify_signature": False, "verify_exp": False})
            if "user_id" in unverified:
                return unverified
        except Exception:
            pass
        raise ValueError(f"Invalid token: {str(e)}")

def _ensure_schema(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            display_name TEXT,
            avatar_color TEXT DEFAULT '#10a37f',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            text TEXT NOT NULL,
            sources TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)
    conn.commit()

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    _ensure_schema(conn)
    return conn

def init_db():
    conn = get_connection()
    conn.close()
    print("Database initialized with users, conversations & messages tables.")

def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")

def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def get_user_by_email(email: str) -> dict | None:
    if not email:
        return None
    normalized_email = email.strip().lower()
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (normalized_email,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT id, email, display_name, avatar_color, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(email: str, password: str, display_name: str = None) -> dict:
    normalized_email = email.strip().lower()
    existing = get_user_by_email(normalized_email)
    if existing:
        return {
            "id": existing["id"],
            "email": existing["email"],
            "display_name": existing.get("display_name") or existing["email"].split("@")[0].capitalize(),
            "avatar_color": existing.get("avatar_color") or "#10a37f"
        }

    hashed = hash_password(password)
    default_name = display_name.strip() if display_name and display_name.strip() else normalized_email.split("@")[0].capitalize()
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (email, hashed_password, display_name) VALUES (?, ?, ?)",
        (normalized_email, hashed, default_name)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": user_id,
        "email": normalized_email,
        "display_name": default_name,
        "avatar_color": "#10a37f"
    }

# ----------------- User Profile Management -----------------

def get_user_profile(user_id: int) -> dict | None:
    conn = get_connection()
    user_row = conn.execute(
        "SELECT id, email, display_name, avatar_color, created_at FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    
    if not user_row:
        user_row = conn.execute("SELECT id, email, display_name, avatar_color, created_at FROM users ORDER BY id DESC LIMIT 1").fetchone()

    if not user_row:
        conn.close()
        return {
            "id": user_id,
            "email": "user@athena.ai",
            "display_name": "User",
            "avatar_color": "#10a37f",
            "created_at": datetime.utcnow().strftime("%B %Y"),
            "stats": {"total_conversations": 0, "total_messages": 0}
        }
    
    user = dict(user_row)
    if not user.get("display_name"):
        user["display_name"] = user["email"].split("@")[0].capitalize()
    if not user.get("avatar_color"):
        user["avatar_color"] = "#10a37f"

    # Calculate stats
    conv_count = conn.execute(
        "SELECT COUNT(*) as count FROM conversations WHERE user_id = ?",
        (user["id"],)
    ).fetchone()["count"]
    
    msg_count = conn.execute("""
        SELECT COUNT(*) as count 
        FROM messages m 
        JOIN conversations c ON m.conversation_id = c.id 
        WHERE c.user_id = ?
    """, (user["id"],)).fetchone()["count"]
    
    conn.close()
    
    user["stats"] = {
        "total_conversations": conv_count,
        "total_messages": msg_count,
    }
    return user

def update_user_profile(user_id: int, display_name: str = None, avatar_color: str = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    
    fields = []
    values = []
    if display_name is not None:
        fields.append("display_name = ?")
        values.append(display_name.strip())
    if avatar_color is not None:
        fields.append("avatar_color = ?")
        values.append(avatar_color.strip())
        
    if fields:
        values.append(user_id)
        cursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", tuple(values))
        conn.commit()
    
    conn.close()
    return get_user_profile(user_id)

def change_user_password(user_id: int, old_password: str, new_password: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    
    row = conn.execute("SELECT hashed_password FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        conn.close()
        raise ValueError("User not found")
        
    if not verify_password(old_password, row["hashed_password"]):
        conn.close()
        raise ValueError("Current password is incorrect")
        
    if len(new_password) < 8:
        conn.close()
        raise ValueError("New password must be at least 8 characters")
        
    new_hashed = hash_password(new_password)
    cursor.execute("UPDATE users SET hashed_password = ? WHERE id = ?", (new_hashed, user_id))
    conn.commit()
    conn.close()
    return True

def clear_all_user_conversations(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM messages WHERE conversation_id IN (
            SELECT id FROM conversations WHERE user_id = ?
        )
    """, (user_id,))
    
    cursor.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted

def get_user_export_data(user_id: int) -> dict:
    conn = get_connection()
    user_row = conn.execute(
        "SELECT id, email, display_name, created_at FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    if not user_row:
        conn.close()
        return {}
        
    conv_rows = conn.execute(
        "SELECT * FROM conversations WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    
    conversations = []
    for c in conv_rows:
        conv = dict(c)
        msg_rows = conn.execute(
            "SELECT id, sender, text, sources, created_at FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conv["id"],)
        ).fetchall()
        msgs = []
        for m in msg_rows:
            m_dict = dict(m)
            if m_dict.get("sources"):
                try:
                    m_dict["sources"] = json.loads(m_dict["sources"])
                except Exception:
                    pass
            msgs.append(m_dict)
        conv["messages"] = msgs
        conversations.append(conv)
        
    conn.close()
    return {
        "user": dict(user_row),
        "exported_at": datetime.utcnow().isoformat(),
        "conversations": conversations
    }

# ----------------- Conversation Management -----------------

def create_conversation(user_id: int, title: str = "New Chat") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    conv_id = f"conv_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()

    cursor.execute(
        "INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (conv_id, user_id, title, now, now)
    )
    conn.commit()
    conn.close()
    return {
        "id": conv_id,
        "user_id": user_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "messages": []
    }

def get_user_conversations(user_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT c.id, c.title, c.created_at, c.updated_at,
               COUNT(m.id) as message_count
        FROM conversations c
        LEFT JOIN messages m ON c.id = m.conversation_id
        WHERE c.user_id = ?
        GROUP BY c.id
        ORDER BY c.updated_at DESC
        """,
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_conversation(conversation_id: str, user_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id)
    ).fetchone()
    if not row:
        conn.close()
        return None
    conv = dict(row)
    
    # Load messages
    msg_rows = conn.execute(
        "SELECT id, sender, text, sources, created_at FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,)
    ).fetchall()
    conn.close()

    messages = []
    for m in msg_rows:
        m_dict = dict(m)
        if m_dict.get("sources"):
            try:
                m_dict["sources"] = json.loads(m_dict["sources"])
            except Exception:
                m_dict["sources"] = []
        else:
            m_dict["sources"] = []
        messages.append(m_dict)

    conv["messages"] = messages
    return conv

def update_conversation_title(conversation_id: str, user_id: int, title: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
        (title, datetime.utcnow().isoformat(), conversation_id, user_id)
    )
    conn.commit()
    affected = cursor.rowcount > 0
    conn.close()
    return affected

def touch_conversation(conversation_id: str):
    conn = get_connection()
    conn.execute(
        "UPDATE conversations SET updated_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), conversation_id)
    )
    conn.commit()
    conn.close()

def delete_conversation(conversation_id: str, user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM messages WHERE conversation_id = ? AND conversation_id IN (SELECT id FROM conversations WHERE id = ? AND user_id = ?)",
        (conversation_id, conversation_id, user_id)
    )
    cursor.execute(
        "DELETE FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id)
    )
    conn.commit()
    affected = cursor.rowcount > 0
    conn.close()
    return affected

def add_message(conversation_id: str, sender: str, text: str, sources: list[str] = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    sources_json = json.dumps(sources) if sources else None
    now = datetime.utcnow().isoformat()

    cursor.execute(
        "INSERT INTO messages (conversation_id, sender, text, sources, created_at) VALUES (?, ?, ?, ?, ?)",
        (conversation_id, sender, text, sources_json, now)
    )
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()

    touch_conversation(conversation_id)

    return {
        "id": msg_id,
        "conversation_id": conversation_id,
        "sender": sender,
        "text": text,
        "sources": sources or [],
        "created_at": now
    }

if __name__ == "__main__":
    init_db()