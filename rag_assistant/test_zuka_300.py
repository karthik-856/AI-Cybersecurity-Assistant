import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Base paths
BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR.parent
QUESTIONS_FILE = BASE_DIR / "test_questions_300.json"
RESULTS_FILE = Path(os.environ.get("ZUKA_EVAL_RESULTS_FILE", str(BASE_DIR / "eval_results_300.json")))

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
FALLBACK_PHRASE = "I don't have that information. Please contact <chitlakarthik66@gmail.com>."
CONTACT_EMAIL = "chitlakarthik66@gmail.com"


def get_auth_token() -> str:
    """Create or retrieve a valid authenticated session token for testing."""
    sys.path.insert(0, str(WORKSPACE_DIR))
    from backend.app.database.session import SessionLocal
    from backend.app.models import AuthSession, User
    from backend.app.security.jwt import create_access_token, create_session_id

    db = SessionLocal()
    user = db.query(User).filter(User.username == "karthik").first()
    if not user:
        user = db.query(User).first()
    sid = create_session_id()
    now = datetime.now(timezone.utc)
    sess = AuthSession(
        session_id=sid,
        user_id=user.id,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(days=7),
        ip_address="127.0.0.1",
        user_agent="EvaluationRunner",
        is_current=True,
    )
    db.add(sess)
    db.commit()
    return create_access_token(subject=str(user.id), role="ADMIN", session_id=sid)


def evaluate_single(item: Dict[str, Any], reply: str) -> Dict[str, Any]:
    """Determine PASS/FAIL and Hallucination for each question."""
    is_ood = item.get("is_out_of_domain", False)
    key_facts = item.get("key_facts", [])
    lower_reply = reply.lower()

    # Check fallback signals
    has_fallback = (
        "don't have that information" in lower_reply
        or "do not have that information" in lower_reply
        or CONTACT_EMAIL.lower() in lower_reply
        or "cannot assist with" in lower_reply
        or "outside my" in lower_reply
        or "defensive policy restriction" in lower_reply
        or "security notice" in lower_reply
        or "architectural scope boundary" in lower_reply
    )

    if is_ood:
        # OUT-OF-DOMAIN:
        # PASS if model refused or returned fallback
        if has_fallback:
            return {
                "verdict": "PASS_REFUSAL",
                "accurate": True,
                "hallucination": False,
                "reason": "Correctly refused / provided contact fallback.",
            }
        else:
            return {
                "verdict": "FAIL_HALLUCINATION",
                "accurate": False,
                "hallucination": True,
                "reason": "Invented facts for out-of-domain question.",
            }
    else:
        # IN-DOMAIN:
        # Check if model gave a fallback erroneously
        if has_fallback and not any(k.lower() in lower_reply for k in key_facts):
            return {
                "verdict": "FAIL_REFUSAL",
                "accurate": False,
                "hallucination": False,
                "reason": "Erroneously refused question present in knowledge base.",
            }

        # Check if key facts are present in reply with flexible morphological matching
        matched_facts = []
        r_clean = lower_reply.replace("-", " ").replace("`", "")
        for k in key_facts:
            k_lower = k.lower()
            k_clean = k_lower.replace("-", " ").replace("`", "")
            if k_lower in lower_reply or k_clean in r_clean:
                matched_facts.append(k)
            else:
                # Root word / stem matching for plurals and derived forms (e.g. botnet/botnets, constraint/constrained)
                tokens = [t for t in k_clean.split() if len(t) > 3]
                if tokens and any(t.rstrip("s") in r_clean for t in tokens):
                    matched_facts.append(k)

        match_rate = len(matched_facts) / len(key_facts) if key_facts else 1.0

        if match_rate >= 0.33 or len(matched_facts) >= 1:
            return {
                "verdict": "PASS_ACCURATE",
                "accurate": True,
                "hallucination": False,
                "reason": f"Matched key facts ({len(matched_facts)}/{len(key_facts)}).",
            }
        else:
            return {
                "verdict": "FAIL_INACCURATE",
                "accurate": False,
                "hallucination": False,
                "reason": f"Missed key facts ({len(matched_facts)}/{len(key_facts)} matched).",
            }


def run_benchmark(sample_size: int = 300):
    print("=" * 70)
    print(" ZUKA UNIFIED ASSISTANT: 300-QUESTION COMPREHENSIVE BENCHMARK")
    print("=" * 70)

    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    endpoint = f"{API_BASE_URL.rstrip('/')}/api/zuka-assistant/chat"

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        all_questions = json.load(f)

    questions = all_questions[:sample_size]
    print(f"Total questions to evaluate: {len(questions)}")
    print(f"Backend API endpoint: {endpoint}")
    print("-" * 70)

    results = []
    total_eval = 0
    passed = 0
    hallucinations = 0
    in_domain_total = 0
    in_domain_passed = 0
    ood_total = 0
    ood_passed = 0

    t_start = time.time()

    for idx, item in enumerate(questions, 1):
        q_id = item["id"]
        q_text = item["question"]
        is_ood = item.get("is_out_of_domain", False)
        category = item.get("category", "General")

        payload = {
            "message": q_text,
            "current_context": {"incident_id": None, "alert_id": None, "page_route": "/dashboard"},
        }

        q_t0 = time.time()
        try:
            while True:
                res = requests.post(endpoint, headers=headers, json=payload, timeout=90)
                if res.status_code != 429:
                    break
                retry_after = max(1, int(res.headers.get("Retry-After", "60")))
                print(f"[WAIT] Rate limit reached; retrying {q_id} in {retry_after}s", flush=True)
                time.sleep(retry_after)
            q_latency = time.time() - q_t0
            if res.status_code == 200:
                data = res.json()
                reply = data.get("reply", "")
                engine = data.get("engine", "Unknown")
            else:
                reply = f"Error: Status {res.status_code}"
                engine = "Error"
        except Exception as e:
            q_latency = time.time() - q_t0
            reply = f"Error: {e}"
            engine = "Exception"

        eval_res = evaluate_single(item, reply)
        verdict = eval_res["verdict"]

        total_eval += 1
        if eval_res["accurate"]:
            passed += 1
        if eval_res["hallucination"]:
            hallucinations += 1

        if is_ood:
            ood_total += 1
            if eval_res["accurate"]:
                ood_passed += 1
        else:
            in_domain_total += 1
            if eval_res["accurate"]:
                in_domain_passed += 1

        record = {
            "id": q_id,
            "category": category,
            "question": q_text,
            "is_out_of_domain": is_ood,
            "reply": reply,
            "engine": engine,
            "verdict": verdict,
            "accurate": eval_res["accurate"],
            "hallucination": eval_res["hallucination"],
            "reason": eval_res["reason"],
            "latency_sec": round(q_latency, 2),
        }
        results.append(record)

        # Print progress
        status_symbol = "[+]" if eval_res["accurate"] else "[-]"
        print(f"[{idx:03d}/{len(questions):03d}] {status_symbol} [{verdict}] {q_id}: {q_text[:50]}... ({q_latency:.1f}s)", flush=True)

        # Periodically dump results
        if idx % 5 == 0 or idx == len(questions):
            with open(RESULTS_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "evaluated_count": total_eval,
                        "overall_accuracy": round((passed / total_eval) * 100, 2),
                        "hallucination_rate": round((hallucinations / total_eval) * 100, 2),
                        "in_domain_accuracy": round((in_domain_passed / in_domain_total) * 100, 2) if in_domain_total else 0,
                        "ood_refusal_rate": round((ood_passed / ood_total) * 100, 2) if ood_total else 0,
                        "timestamp": datetime.utcnow().isoformat(),
                        "results": results,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

    total_time = time.time() - t_start
    overall_acc = (passed / total_eval) * 100 if total_eval else 0
    hallucination_pct = (hallucinations / total_eval) * 100 if total_eval else 0
    in_domain_acc = (in_domain_passed / in_domain_total) * 100 if in_domain_total else 0
    ood_refusal = (ood_passed / ood_total) * 100 if ood_total else 0

    print("=" * 70)
    print(" BENCHMARK COMPLETED")
    print(f" Total Questions:       {total_eval}")
    print(f" Total Duration:        {total_time:.1f}s (avg {total_time/total_eval:.2f}s/q)")
    print(f" In-Domain Accuracy:    {in_domain_acc:.1f}% ({in_domain_passed}/{in_domain_total})")
    print(f" Out-of-Domain Refusal: {ood_refusal:.1f}% ({ood_passed}/{ood_total})")
    print(f" Overall Accuracy:      {overall_acc:.1f}% ({passed}/{total_eval})")
    print(f" Hallucination Rate:    {hallucination_pct:.1f}% ({hallucinations}/{total_eval})")
    print(f" Full Results:          {RESULTS_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    sample = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    run_benchmark(sample)
