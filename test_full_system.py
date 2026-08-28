import json
import urllib.request
import urllib.error
import time

BASE_URL = "http://127.0.0.1:8000"

def request(method, path, data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {}
    body = None

    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")

    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            raw = resp.read()
            try:
                content = raw.decode("utf-8")
                try:
                    return status, json.loads(content)
                except Exception:
                    return status, content
            except Exception:
                return status, raw
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            content = raw.decode("utf-8")
            try:
                return e.code, json.loads(content)
            except Exception:
                return e.code, content
        except Exception:
            return e.code, raw

def run_tests():
    print("=== STARTING FULL SYSTEM & CONVERSATION TEST SUITE ===")

    # 1. Health check
    status, body = request("GET", "/health")
    assert status == 200 and body.get("status") == "ok"
    print("[PASS] 1. Backend /health is OK")

    # 2. Signup a test user
    ts = int(time.time() * 1000)
    email = f"test_claude_user_{ts}@athena.ai"
    password = "SecurePassword123!"

    status, body = request("POST", "/signup", {"email": email, "password": password})
    assert status == 200, f"Signup failed: {body}"
    print(f"[PASS] 2. User signup succeeded ({email})")

    # 3. Login
    status, body = request("POST", "/login", {"email": email, "password": password})
    assert status == 200 and "token" in body, f"Login failed: {body}"
    token = body["token"]
    print("[PASS] 3. User login succeeded, JWT token obtained")

    # 4. Knowledge base stats
    status, body = request("GET", "/knowledge/stats", token=token)
    assert status == 200, f"Knowledge stats failed: {body}"
    total_chunks = body.get("total_chunks", 0)
    print(f"[PASS] 4. Knowledge stats fetched: {total_chunks} chunks, {body.get('document_count')} documents")

    # 5. Query Athena RAG
    print("Sending RAG question: 'What is machine learning?'...")
    status, body = request("POST", "/query", {"question": "What is machine learning?"}, token=token)
    assert status == 200, f"Query failed: {body}"
    assert "answer" in body and len(body["answer"]) > 10, f"No answer: {body}"
    conv_id = body.get("conversation_id")
    assert conv_id is not None, "conversation_id must be returned"
    print(f"[PASS] 5. RAG query successful! Answer preview: '{body['answer'][:80]}...'")
    print(f"       Sources: {body.get('sources')}")
    print(f"       Generated conversation ID: {conv_id}")

    # 6. Multi-turn follow up in the same conversation
    print("Sending follow-up question: 'Give me 2 examples from the notes'...")
    status, body2 = request("POST", "/query", {"question": "Give me 2 examples from the notes", "conversation_id": conv_id}, token=token)
    assert status == 200, f"Follow-up query failed: {body2}"
    print(f"[PASS] 6. Follow-up query successful! Answer preview: '{body2['answer'][:80]}...'")

    # 7. List user conversations
    status, convs = request("GET", "/conversations", token=token)
    assert status == 200 and isinstance(convs, list) and len(convs) >= 1, f"List convs failed: {convs}"
    print(f"[PASS] 7. User conversations listed ({len(convs)} chats found)")

    # 8. Load specific conversation with messages
    status, conv_data = request("GET", f"/conversations/{conv_id}", token=token)
    assert status == 200 and "messages" in conv_data, f"Load conv failed: {conv_data}"
    msg_count = len(conv_data["messages"])
    assert msg_count >= 4, f"Expected at least 4 messages (2 user + 2 assistant), got {msg_count}"
    print(f"[PASS] 8. Conversation {conv_id} loaded with {msg_count} persisted messages")

    # 9. Rename conversation
    status, rename_resp = request("PATCH", f"/conversations/{conv_id}", {"title": "ML Fundamentals"}, token=token)
    assert status == 200, f"Rename failed: {rename_resp}"
    status, conv_data = request("GET", f"/conversations/{conv_id}", token=token)
    assert conv_data.get("title") == "ML Fundamentals", "Title was not updated"
    print(f"[PASS] 9. Conversation successfully renamed to '{conv_data['title']}'")

    # 10. Create new empty conversation
    status, new_conv = request("POST", "/conversations", {"title": "Deep Learning Chat"}, token=token)
    assert status == 200 and "id" in new_conv, f"New conv failed: {new_conv}"
    new_conv_id = new_conv["id"]
    print(f"[PASS] 10. Created new conversation: {new_conv_id}")

    # 11. Delete the new conversation
    status, del_resp = request("DELETE", f"/conversations/{new_conv_id}", token=token)
    assert status == 200, f"Delete failed: {del_resp}"
    status, check_deleted = request("GET", f"/conversations/{new_conv_id}", token=token)
    assert status == 404, "Deleted conversation should return 404"
    print("[PASS] 11. Deleted conversation verified (returns 404)")

    # 12. Check static and clean pages
    pages = ["/", "/login", "/signup", "/app.js", "/style.css", "/auth.js", "/auth.css", "/assets/logo-white.png", "/assets/favicon.png"]
    for p in pages:
        status, _ = request("GET", p)
        assert status == 200, f"Page {p} returned {status}"
        print(f"[PASS] 12. Route '{p}' accessible (200 OK)")

    print("\n=======================================================")
    print("ALL 12 TESTS IN FULL SYSTEM SUITE PASSED WITH 100% SUCCESS!")
    print("=======================================================")

if __name__ == "__main__":
    run_tests()
