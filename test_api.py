"""
API Test Script - runs the server and tests all endpoints.
Usage: python test_api.py
"""
import sys, os, time, subprocess, requests, json

BASE = "http://localhost:5000"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    print(f"  {status} {label}" + (f": {detail}" if detail else ""))
    return condition

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

# ── Start server ──────────────────────────────────────────────
section("Starting Flask server")
server = subprocess.Popen(
    [sys.executable, "app.py"],
    cwd=PROJECT_DIR,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)
print("  Server PID:", server.pid)
print("  Waiting for server to be ready...")

for i in range(20):
    try:
        requests.get(f"{BASE}/health", timeout=2)
        print(f"  Server ready (after {i+1}s)")
        break
    except Exception:
        time.sleep(1)
else:
    print("  Server did not start in 20s. Exiting.")
    server.terminate()
    sys.exit(1)

results = []

# ── A: GET /api/team_info ─────────────────────────────────────
section("A) GET /api/team_info")
try:
    r = requests.get(f"{BASE}/api/team_info", timeout=10)
    d = r.json()
    results.append(check("HTTP 200", r.status_code == 200, f"got {r.status_code}"))
    results.append(check("group_batch_order_number present", "group_batch_order_number" in d, d.get("group_batch_order_number")))
    results.append(check("team_name present", "team_name" in d, d.get("team_name")))
    students = d.get("students", [])
    results.append(check("students is list of 3", len(students) == 3, f"got {len(students)}"))
    results.append(check("each student has name+email", all("name" in s and "email" in s for s in students)))
    print("\n  Response:")
    print("  ", json.dumps(d, indent=2).replace("\n", "\n  "))
except Exception as e:
    print(f"  {FAIL} Request failed: {e}")
    results.append(False)

# ── B: GET /api/agent_info ────────────────────────────────────
section("B) GET /api/agent_info")
try:
    r = requests.get(f"{BASE}/api/agent_info", timeout=10)
    d = r.json()
    results.append(check("HTTP 200", r.status_code == 200))
    results.append(check("has 'description'", "description" in d))
    results.append(check("has 'purpose'", "purpose" in d))
    results.append(check("has 'prompt_template'", "prompt_template" in d))
    examples = d.get("prompt_examples", [])
    results.append(check("has 'prompt_examples' (>=1)", len(examples) >= 1, f"{len(examples)} examples"))
    for i, ex in enumerate(examples):
        steps = ex.get("steps", [])
        results.append(check(f"  example[{i}] has steps", len(steps) > 0, f"{len(steps)} steps"))
        results.append(check(f"  example[{i}] steps have module+prompt+response",
            all("module" in s and "prompt" in s and "response" in s for s in steps)))
        modules = [s.get("module") for s in steps]
        results.append(check(f"  example[{i}] no extra 'step' field", not any("step" in s for s in steps)))
        print(f"    example[{i}] modules: {modules}")
except Exception as e:
    print(f"  {FAIL} Request failed: {e}")
    results.append(False)

# ── C: GET /api/model_architecture ───────────────────────────
section("C) GET /api/model_architecture")
try:
    r = requests.get(f"{BASE}/api/model_architecture", timeout=10)
    results.append(check("HTTP 200", r.status_code == 200))
    results.append(check("Content-Type is image/png", "image/png" in r.headers.get("Content-Type", ""),
        r.headers.get("Content-Type")))
    results.append(check("Response body non-empty (>1KB)", len(r.content) > 1024, f"{len(r.content)} bytes"))
except Exception as e:
    print(f"  {FAIL} Request failed: {e}")
    results.append(False)

# ── D: POST /api/execute (mild case) ─────────────────────────
section("D) POST /api/execute - Mild case (sore throat)")
try:
    payload = {"prompt": "Patient: 28yo female, BP 118/76, HR 74, temp 37.8C, SpO2 99%, sore throat and mild cough for 2 days, no difficulty breathing"}
    r = requests.post(f"{BASE}/api/execute", json=payload, timeout=90)
    d = r.json()
    results.append(check("HTTP 200", r.status_code == 200))
    results.append(check("status == 'ok'", d.get("status") == "ok", d.get("status")))
    results.append(check("error is null", d.get("error") is None, str(d.get("error"))))
    results.append(check("response is non-empty string", isinstance(d.get("response"), str) and len(d.get("response","")) > 10))
    steps = d.get("steps", [])
    results.append(check("steps is list", isinstance(steps, list)))
    results.append(check("steps has 4 entries", len(steps) == 4, f"got {len(steps)}"))
    expected = ["Input Validator", "Clinical Rule Engine", "Knowledge Retriever (RAG)", "Decision Engine (LLM)"]
    actual_modules = [s.get("module") for s in steps]
    results.append(check("correct module names", actual_modules == expected, str(actual_modules)))
    results.append(check("each step has module+prompt+response",
        all("module" in s and "prompt" in s and "response" in s for s in steps)))
    resp_preview = d.get("response", "")[:200].encode("ascii", "replace").decode()
    print(f"\n  Response preview:\n  {resp_preview}")
except Exception as e:
    print(f"  {FAIL} Request failed: {e}")
    results.append(False)

# ── E: POST /api/execute (minor injury) ──────────────────────
section("E) POST /api/execute - Minor injury case")
try:
    payload = {"prompt": "Patient: 35yo male, BP 122/80, HR 78, temp 36.9C, SpO2 99%, twisted ankle while jogging, mild swelling, able to bear weight"}
    r = requests.post(f"{BASE}/api/execute", json=payload, timeout=90)
    d = r.json()
    results.append(check("status == 'ok'", d.get("status") == "ok"))
    steps = d.get("steps", [])
    results.append(check("4 steps", len(steps) == 4, f"got {len(steps)}"))
    resp_preview = d.get("response", "")[:200].encode("ascii", "replace").decode()
    print(f"\n  Response preview:\n  {resp_preview}")
except Exception as e:
    print(f"  {FAIL} Request failed: {e}")
    results.append(False)

# ── F: POST /api/execute (error case) ────────────────────────
section("F) POST /api/execute - Error case (empty body)")
try:
    r = requests.post(f"{BASE}/api/execute", json={}, timeout=10)
    d = r.json()
    results.append(check("status == 'error'", d.get("status") == "error", d.get("status")))
    results.append(check("error message present", bool(d.get("error")), d.get("error")))
    results.append(check("response is null", d.get("response") is None))
    results.append(check("steps is []", d.get("steps") == []))
    print(f"  error: {d.get('error')}")
except Exception as e:
    print(f"  {FAIL} Request failed: {e}")
    results.append(False)

# ── Summary ───────────────────────────────────────────────────
section("SUMMARY")
passed = sum(1 for r in results if r)
total = len(results)
print(f"  {passed}/{total} checks passed")
if passed == total:
    print(f"  {PASS} ALL CHECKS PASSED - ready to submit!")
else:
    print(f"  {FAIL} {total - passed} checks failed - review output above")

server.terminate()
print("\n  Server stopped.")