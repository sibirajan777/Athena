import urllib.request
import urllib.parse
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("=== TESTING KNOWLEDGE BASE DOCUMENTS APIS ===")
    
    # 1. Register a test user
    email = f"kb_user_{int(time.time())}@athena.ai"
    signup_req = urllib.request.Request(
        f"{BASE_URL}/signup",
        data=json.dumps({"email": email, "password": "password123", "name": "Athena KB Explorer"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(signup_req) as resp:
        assert resp.status == 200
        print(f"[PASS] 1. User created: {email}")

    # 2. Login to get token
    login_req = urllib.request.Request(
        f"{BASE_URL}/login",
        data=json.dumps({"email": email, "password": "password123"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(login_req) as resp:
        assert resp.status == 200
        token = json.loads(resp.read().decode())["token"]
        print(f"[PASS] 2. JWT token acquired")

    auth_headers = {"Authorization": f"Bearer {token}"}

    # 3. Test /knowledge/documents
    docs_req = urllib.request.Request(f"{BASE_URL}/knowledge/documents", headers=auth_headers)
    with urllib.request.urlopen(docs_req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        print(f"[PASS] 3. Documents listed: Total chunks = {data['total_chunks']}, Total Docs = {data['document_count']}")
        for doc in data["documents"]:
            print(f"       * {doc['filename']} | {doc['size']} | {doc['chunks']} chunks | {doc['type']} | Modified: {doc['modified_at']}")

    # 4. Test Preview for first document
    if data["documents"]:
        doc_name = data["documents"][0]["filename"]
        enc_name = urllib.parse.quote(doc_name)
        prev_req = urllib.request.Request(f"{BASE_URL}/knowledge/documents/{enc_name}/preview", headers=auth_headers)
        with urllib.request.urlopen(prev_req) as resp:
            assert resp.status == 200
            prev_data = json.loads(resp.read().decode())
            print(f"[PASS] 4. Preview received for '{doc_name}' ({prev_data['total_chunks_found']} chunks found in preview)")
            if prev_data["chunks_preview"]:
                print(f"       Sample chunk snippet: {prev_data['chunks_preview'][0]['text'][:100]}...")

    print("\n=======================================================")
    print("ALL KNOWLEDGE BASE API TESTS PASSED!")
    print("=======================================================")

if __name__ == "__main__":
    run_tests()
