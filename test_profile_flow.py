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
            content = resp.read().decode("utf-8")
            try:
                return status, json.loads(content)
            except Exception:
                return status, content
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            return e.code, json.loads(content)
        except Exception:
            return e.code, content

def run_tests():
    print("=== STARTING USER PROFILE & SETTINGS TEST SUITE ===")

    # 1. Signup a user
    ts = int(time.time() * 1000)
    email = f"profile_user_{ts}@athena.ai"
    password = "InitialPassword123!"

    status, body = request("POST", "/signup", {"email": email, "password": password, "display_name": "Barath Test"})
    assert status == 200, f"Signup failed: {body}"
    print(f"[PASS] 1. User signup succeeded ({email})")

    # 2. Login
    status, body = request("POST", "/login", {"email": email, "password": password})
    assert status == 200 and "token" in body, f"Login failed: {body}"
    token = body["token"]
    print("[PASS] 2. User login succeeded, JWT token obtained")

    # 3. Fetch User Profile
    status, profile = request("GET", "/user/profile", token=token)
    assert status == 200, f"Get profile failed: {profile}"
    assert profile["email"] == email
    assert "stats" in profile
    print(f"[PASS] 3. Profile fetched: Name='{profile.get('display_name')}', Stats={profile['stats']}")

    # 4. Edit Profile (Display Name and Avatar Color)
    status, edit_res = request("PATCH", "/user/profile", {"display_name": "Barath Prodigy", "avatar_color": "#7c3aed"}, token=token)
    assert status == 200, f"Edit profile failed: {edit_res}"
    status, updated_prof = request("GET", "/user/profile", token=token)
    assert updated_prof["display_name"] == "Barath Prodigy"
    assert updated_prof["avatar_color"] == "#7c3aed"
    print(f"[PASS] 4. Profile updated: Name='{updated_prof['display_name']}', Color='{updated_prof['avatar_color']}'")

    # 5. Create a conversation and message
    status, conv = request("POST", "/conversations", {"title": "Profile Test Chat"}, token=token)
    assert status == 200 and "id" in conv
    conv_id = conv["id"]

    status, q_res = request("POST", "/query", {"question": "Hello Athena", "conversation_id": conv_id}, token=token)
    assert status == 200

    # Verify profile stats updated
    status, profile_after_msg = request("GET", "/user/profile", token=token)
    assert profile_after_msg["stats"]["total_conversations"] >= 1
    assert profile_after_msg["stats"]["total_messages"] >= 2
    print(f"[PASS] 5. Profile stats dynamically updated: {profile_after_msg['stats']}")

    # 6. Export Chat Data
    status, export_data = request("GET", "/user/export", token=token)
    assert status == 200 and "conversations" in export_data
    assert len(export_data["conversations"]) >= 1
    print(f"[PASS] 6. Export chat history data generated with {len(export_data['conversations'])} conversations")

    # 7. Change Password
    new_password = "UpdatedNewPassword456!"
    status, change_res = request("POST", "/user/change-password", {"old_password": password, "new_password": new_password}, token=token)
    assert status == 200, f"Change password failed: {change_res}"
    print("[PASS] 7. Password changed successfully")

    # 8. Verify login with old password fails (401)
    status, fail_login = request("POST", "/login", {"email": email, "password": password})
    assert status == 401
    print("[PASS] 8. Old password correctly rejected (401)")

    # 9. Verify login with new password succeeds (200)
    status, new_login = request("POST", "/login", {"email": email, "password": new_password})
    assert status == 200 and "token" in new_login
    new_token = new_login["token"]
    print("[PASS] 9. New password successfully authenticated")

    # 10. Clear All User Conversations
    status, clear_res = request("DELETE", "/user/conversations", token=new_token)
    assert status == 200 and clear_res.get("status") == "success"
    status, check_convs = request("GET", "/conversations", token=new_token)
    assert len(check_convs) == 0
    print("[PASS] 10. All conversations cleared successfully")

    print("\n=======================================================")
    print("ALL 10 TESTS IN PROFILE TEST SUITE PASSED WITH 100% SUCCESS!")
    print("=======================================================")

if __name__ == "__main__":
    run_tests()
