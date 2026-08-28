import urllib.request
import urllib.error
import json
from pathlib import Path

def test_static_files():
    files = [
        "frontend/signup.html",
        "frontend/login.html",
        "frontend/index.html",
        "frontend/auth.js",
        "frontend/auth.css",
        "frontend/app.js",
        "frontend/style.css"
    ]
    for f in files:
        p = Path(f)
        assert p.exists(), f"File {f} does not exist"
        print(f"[PASS] Found {f} ({p.stat().st_size} bytes)")

def test_endpoints():
    base = "http://127.0.0.1:8000"
    
    # 1. Health
    with urllib.request.urlopen(f"{base}/health") as r:
        assert r.status == 200
        print("[PASS] Backend /health is OK")

    # 2. Signup validation - short password
    req = urllib.request.Request(
        f"{base}/signup",
        data=json.dumps({"email": "short@test.com", "password": "123"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Should have failed with short password"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        data = json.loads(e.read().decode())
        assert "Password must be at least 8 characters" in data["detail"]
        print("[PASS] Signup rejects short passwords (<8 characters)")

    # 3. Successful signup
    test_email = f"verified_user_{Path('athena.db').stat().st_mtime_ns}@athena.ai"
    test_pw = "ValidPassword123"
    req = urllib.request.Request(
        f"{base}/signup",
        data=json.dumps({"email": test_email, "password": test_pw}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        data = json.loads(r.read().decode())
        assert data["status"] == "success"
        assert data["user"]["email"] == test_email
        print(f"[PASS] Signup succeeds for new user ({test_email})")

    # 4. Duplicate signup rejected
    req = urllib.request.Request(
        f"{base}/signup",
        data=json.dumps({"email": test_email, "password": test_pw}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Should have rejected duplicate email"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        data = json.loads(e.read().decode())
        assert "Email already registered" in data["detail"]
        print("[PASS] Signup rejects duplicate email addresses")

    # 5. Login wrong password
    req = urllib.request.Request(
        f"{base}/login",
        data=json.dumps({"email": test_email, "password": "WrongPassword!"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Should have failed invalid login"
    except urllib.error.HTTPError as e:
        assert e.code == 401
        print("[PASS] Login rejects invalid password (401)")

    # 6. Login correct credentials
    req = urllib.request.Request(
        f"{base}/login",
        data=json.dumps({"email": test_email, "password": test_pw}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        data = json.loads(r.read().decode())
        assert data["status"] == "success"
        assert "token" in data
        assert data["user"]["email"] == test_email
        print(f"[PASS] Login succeeds with valid token generated for {test_email}")

    # 7. Static file serving check
    for route in ["/login.html", "/signup.html", "/auth.js", "/auth.css", "/index.html"]:
        with urllib.request.urlopen(f"{base}{route}") as r:
            assert r.status == 200
            print(f"[PASS] Static route {route} is accessible")

if __name__ == "__main__":
    test_static_files()
    test_endpoints()
    print("\nALL TESTS PASSED SUCCESSFULLY!")
