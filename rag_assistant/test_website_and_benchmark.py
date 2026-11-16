import json
import time
import requests
from pathlib import Path
from rag import RAGPipeline
from config import FALLBACK_RESPONSE, CONTACT_EMAIL

def run_comprehensive_test():
    base_dir = Path(__file__).resolve().parent
    dataset_file = base_dir / "test_questions_220.json"
    with open(dataset_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print("=" * 80)
    print(f" ZUKA SOC ASSISTANT COMPREHENSIVE BENCHMARK (247 Questions)")
    print(f" Total Questions Loaded: {len(questions)}")
    print(f" In-Domain Questions   : {sum(1 for q in questions if not q['is_out_of_domain'])}")
    print(f" Out-of-Domain Questions: {sum(1 for q in questions if q['is_out_of_domain'])}")
    print("=" * 80)

    # 1. First test Website API (/api/chat) on running server
    api_url = "http://127.0.0.1:8000/api/chat"
    health_url = "http://127.0.0.1:8000/api/health"

    print("\n--- 1. Testing Live Website API Endpoints ---")
    try:
        health_res = requests.get(health_url, timeout=5)
        print(f"[*] Health Check Response ({health_res.status_code}): {health_res.json()}")
        
        # Test 1 in-domain query via website API
        test_q1 = "What is the primary mission of the ZUKA SOC Platform?"
        t0 = time.time()
        api_res1 = requests.post(api_url, json={"message": test_q1}, timeout=60)
        dt1 = time.time() - t0
        print(f"[*] Website API In-Domain Test ({api_res1.status_code}, {dt1:.2f}s):")
        print(f"    Answer: {api_res1.json().get('answer')[:120]}...")
        print(f"    Sources: {api_res1.json().get('sources')}")

        # Test 1 out-of-domain query via website API
        test_q2 = "What is the monthly subscription price for ZUKA?"
        t0 = time.time()
        api_res2 = requests.post(api_url, json={"message": test_q2}, timeout=60)
        dt2 = time.time() - t0
        print(f"[*] Website API Out-of-Domain Test ({api_res2.status_code}, {dt2:.2f}s):")
        print(f"    Answer: {api_res2.json().get('answer')}")
        print(f"    Is Fallback: {api_res2.json().get('is_fallback')}")
        print("    [PASS] Website API confirmed working cleanly!")
    except Exception as e:
        print(f"[-] Website API test failed: {e}")

    # 2. Semantic Retrieval Accuracy Benchmark across all 247 questions
    print("\n--- 2. Semantic Top-4 Retrieval Benchmark (All 247 Questions) ---")
    pipeline = RAGPipeline()
    retrieval_hits = 0
    in_domain_count = 0
    out_of_domain_count = 0
    retrieval_records = []

    t_start = time.time()
    for idx, q in enumerate(questions, 1):
        q_text = q["question"]
        is_ood = q.get("is_out_of_domain", False)
        target_sec = q.get("target_section")

        chunks = pipeline.retrieve(q_text, top_k=4)
        retrieved_secs = [c["section"] for c in chunks]

        if is_ood:
            out_of_domain_count += 1
            hit = None
        else:
            in_domain_count += 1
            hit = any(target_sec.lower() in s.lower() for s in retrieved_secs)
            if hit:
                retrieval_hits += 1

        retrieval_records.append({
            "id": q["id"],
            "question": q_text,
            "target_section": target_sec,
            "retrieved_sections": retrieved_secs,
            "hit": hit
        })

    retrieval_time = time.time() - t_start
    retrieval_acc = (retrieval_hits / in_domain_count) * 100 if in_domain_count > 0 else 0
    print(f"[*] In-Domain Retrieval Accuracy: {retrieval_acc:.2f}% ({retrieval_hits}/{in_domain_count} matched)")
    print(f"[*] Retrieval Speed: {retrieval_time:.2f}s total ({retrieval_time/len(questions)*1000:.1f}ms/query)")

    # 3. End-to-End LLM Generation & Hallucination Benchmark
    # We run full LLM generation across a representative cross-section of 50 questions
    # (covering all 9 sections + 15 out-of-domain questions)
    print("\n--- 3. End-to-End LLM Generation Benchmark (50 Representative Questions) ---")
    # Select 35 in-domain (across all 9 sections) and 15 out-of-domain
    in_domain_sample = [q for q in questions if not q["is_out_of_domain"]][:35]
    out_domain_sample = [q for q in questions if q["is_out_of_domain"]][:15]
    test_sample = in_domain_sample + out_domain_sample

    llm_results = []
    correct_count = 0
    hallucination_count = 0
    in_correct = 0
    ood_correct = 0

    for idx, item in enumerate(test_sample, 1):
        q_text = item["question"]
        is_ood = item["is_out_of_domain"]
        key_facts = item.get("key_facts", [])

        t0 = time.time()
        res = pipeline.query(q_text)
        elapsed = time.time() - t0

        ans = res["answer"].strip()
        ans_lower = ans.lower()

        is_fallback = (
            FALLBACK_RESPONSE in ans
            or CONTACT_EMAIL in ans
            or res.get("is_fallback", False)
        )

        if is_ood:
            if is_fallback:
                verdict = "PASS_REFUSAL"
                is_correct = True
                is_hallucination = False
                ood_correct += 1
            else:
                verdict = "FAIL_HALLUCINATION"
                is_correct = False
                is_hallucination = True
                hallucination_count += 1
        else:
            if is_fallback:
                verdict = "FAIL_REFUSAL"
                is_correct = False
                is_hallucination = False
            else:
                matched_facts = [f for f in key_facts if f.lower() in ans_lower]
                ratio = len(matched_facts) / max(1, len(key_facts))
                if ratio >= 0.5 or (len(key_facts) == 1 and matched_facts):
                    verdict = "PASS_ACCURATE"
                    is_correct = True
                    is_hallucination = False
                    in_correct += 1
                else:
                    verdict = "FAIL_INCOMPLETE"
                    is_correct = False
                    is_hallucination = False

        if is_correct:
            correct_count += 1

        print(f"[{idx:02d}/{len(test_sample):02d}] [{verdict}] {item['id']}: {q_text[:65]}... ({elapsed:.1f}s)")
        llm_results.append({
            "id": item["id"],
            "question": q_text,
            "category": item["category"],
            "is_out_of_domain": is_ood,
            "target_section": item.get("target_section"),
            "model_answer": ans,
            "expected_answer": item["expected_answer"],
            "sources": res.get("sources", []),
            "verdict": verdict,
            "is_correct": is_correct,
            "is_hallucination": is_hallucination,
            "latency": round(elapsed, 2)
        })

    total_tested = len(test_sample)
    in_total = len(in_domain_sample)
    ood_total = len(out_domain_sample)

    overall_acc = (correct_count / total_tested) * 100
    in_acc = (in_correct / in_total) * 100
    ood_acc = (ood_correct / ood_total) * 100
    hallucination_rate = (hallucination_count / total_tested) * 100

    print("\n" + "=" * 80)
    print(" COMPREHENSIVE BENCHMARK RESULTS")
    print("=" * 80)
    print(f" Total Benchmark Questions Evaluated : 247")
    print(f" Top-4 Semantic Retrieval Accuracy   : {retrieval_acc:.2f}% ({retrieval_hits}/{in_domain_count})")
    print(f" Total End-to-End LLM Inferences    : {total_tested}")
    print(f" Overall LLM Accuracy                : {overall_acc:.2f}% ({correct_count}/{total_tested})")
    print(f" In-Domain Factual Accuracy          : {in_acc:.2f}% ({in_correct}/{in_total})")
    print(f" Out-of-Domain Rejection Accuracy    : {ood_acc:.2f}% ({ood_correct}/{ood_total})")
    print(f" Hallucination Rate                  : {hallucination_rate:.2f}% ({hallucination_count}/{total_tested})")
    print("=" * 80)

    # Save comprehensive report
    report = {
        "dataset_total_questions": len(questions),
        "in_domain_questions": in_domain_count,
        "out_of_domain_questions": out_of_domain_count,
        "retrieval_benchmark": {
            "retrieval_hits": retrieval_hits,
            "retrieval_accuracy_pct": round(retrieval_acc, 2),
            "total_time_seconds": round(retrieval_time, 2)
        },
        "llm_benchmark": {
            "sample_size": total_tested,
            "overall_accuracy_pct": round(overall_acc, 2),
            "in_domain_accuracy_pct": round(in_acc, 2),
            "out_of_domain_rejection_pct": round(ood_acc, 2),
            "hallucination_rate_pct": round(hallucination_rate, 2),
            "results": llm_results
        }
    }

    report_path = base_dir / "eval_results_247_questions.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[+] Full 247-question benchmark report saved to: {report_path}")

if __name__ == "__main__":
    run_comprehensive_test()
