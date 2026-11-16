import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    from config import CHAT_MODEL, FALLBACK_RESPONSE, CONTACT_EMAIL
    from rag import RAGPipeline
except ImportError:
    from rag_assistant.config import CHAT_MODEL, FALLBACK_RESPONSE, CONTACT_EMAIL
    from rag_assistant.rag import RAGPipeline


def evaluate_response(item: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates whether the RAG response is accurate or a hallucination.

    Out-of-domain questions:
    - PASS: Model correctly states it does not have the information / provides the contact email.
    - FAIL / HALLUCINATION: Model invents facts (prices, phone numbers, policies, addresses).

    In-domain questions:
    - PASS: Model accurately states the facts matching the expected answer and key facts.
    - FAIL / FALSE NEGATIVE: Model erroneously states it does not have the info when it is in context.
    - FAIL / HALLUCINATION: Model introduces fabricated metrics or false claims.
    """
    answer = result.get("answer", "").strip()
    is_out_of_domain = item.get("is_out_of_domain", False)
    key_facts = item.get("key_facts", [])

    is_fallback = (
        FALLBACK_RESPONSE in answer
        or CONTACT_EMAIL in answer
        or result.get("is_fallback", False)
    )

    if is_out_of_domain:
        if is_fallback:
            return {
                "verdict": "PASS",
                "is_correct": True,
                "is_hallucination": False,
                "reason": "Correctly rejected out-of-domain question with designated contact fallback."
            }
        else:
            return {
                "verdict": "FAIL_HALLUCINATION",
                "is_correct": False,
                "is_hallucination": True,
                "reason": "Failed to refuse out-of-domain query; fabricated information."
            }
    else:
        # In-domain evaluation
        if is_fallback:
            return {
                "verdict": "FAIL_REFUSAL",
                "is_correct": False,
                "is_hallucination": False,
                "reason": "False negative: Refused to answer when context contained the answer."
            }

        # Check key factual terms
        answer_lower = answer.lower()
        matched_facts = [fact for fact in key_facts if fact.lower() in answer_lower]
        match_ratio = len(matched_facts) / max(1, len(key_facts))

        # Check retrieval success
        target_sec = item.get("target_section", "")
        retrieved_sources = result.get("sources", [])
        retrieval_hit = any(target_sec.lower() in s.lower() for s in retrieved_sources)

        if match_ratio >= 0.5:
            return {
                "verdict": "PASS",
                "is_correct": True,
                "is_hallucination": False,
                "retrieval_hit": retrieval_hit,
                "match_ratio": match_ratio,
                "reason": f"Accurately answered with {len(matched_facts)}/{len(key_facts)} key facts."
            }
        else:
            return {
                "verdict": "FAIL_INACCURATE",
                "is_correct": False,
                "is_hallucination": True if match_ratio == 0 else False,
                "retrieval_hit": retrieval_hit,
                "match_ratio": match_ratio,
                "reason": f"Incomplete or inaccurate answer: matched only {matched_facts}."
            }


def run_evaluation(
    model_name: str = CHAT_MODEL,
    questions_path: str = "test_questions.json",
    output_path: Optional[str] = None,
    limit: Optional[int] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """Runs evaluation over the benchmark questions."""
    q_path = Path(questions_path)
    if not q_path.is_absolute():
        q_path = Path(__file__).resolve().parent / questions_path

    with open(q_path, "r", encoding="utf-8") as f:
        questions: List[Dict[str, Any]] = json.load(f)

    if limit:
        questions = questions[:limit]

    print("=" * 78)
    print(f" ZUKA RAG BENCHMARK EVALUATION")
    print(f" Model Under Test : {model_name}")
    print(f" Total Questions  : {len(questions)}")
    print(f" Questions File   : {q_path.name}")
    print("=" * 78)

    pipeline = RAGPipeline(chat_model=model_name)

    results = []
    latencies = []
    in_domain_total = 0
    in_domain_correct = 0
    out_of_domain_total = 0
    out_of_domain_correct = 0
    hallucination_count = 0

    for idx, item in enumerate(questions, 1):
        qid = item["id"]
        q_text = item["question"]
        is_ood = item.get("is_out_of_domain", False)

        if is_ood:
            out_of_domain_total += 1
        else:
            in_domain_total += 1

        t0 = time.time()
        res = pipeline.query(q_text, model=model_name)
        elapsed = time.time() - t0
        latencies.append(elapsed)

        eval_metric = evaluate_response(item, res)
        is_correct = eval_metric["is_correct"]
        is_hallucination = eval_metric["is_hallucination"]

        if is_ood and is_correct:
            out_of_domain_correct += 1
        elif not is_ood and is_correct:
            in_domain_correct += 1

        if is_hallucination:
            hallucination_count += 1

        res_record = {
            "id": qid,
            "question": q_text,
            "category": item["category"],
            "target_section": item.get("target_section"),
            "expected_answer": item["expected_answer"],
            "model_answer": res["answer"],
            "sources": res.get("sources", []),
            "latency_sec": round(elapsed, 2),
            "verdict": eval_metric["verdict"],
            "is_correct": is_correct,
            "is_hallucination": is_hallucination,
            "evaluation_note": eval_metric["reason"]
        }
        results.append(res_record)

        # Print progress
        status_tag = "[PASS]" if is_correct else f"[{eval_metric['verdict']}]"
        print(f"\n[{idx:02d}/{len(questions):02d}] {status_tag} {qid}: {q_text}")
        if verbose:
            print(f"  Target Section  : {item.get('target_section') or 'None (Out of Domain)'}")
            print(f"  Retrieved Secs  : {', '.join(res.get('sources', [])) or 'None'}")
            print(f"  Model Answer    : {res['answer'][:160]}{'...' if len(res['answer']) > 160 else ''}")
            print(f"  Expected Answer : {item['expected_answer'][:120]}...")
            print(f"  Latency         : {elapsed:.2f}s | Note: {eval_metric['reason']}")

    total_q = len(questions)
    total_correct = in_domain_correct + out_of_domain_correct
    overall_accuracy = (total_correct / total_q) * 100 if total_q > 0 else 0
    in_domain_acc = (in_domain_correct / in_domain_total) * 100 if in_domain_total > 0 else 0
    ood_rejection_acc = (out_of_domain_correct / out_of_domain_total) * 100 if out_of_domain_total > 0 else 0
    hallucination_rate = (hallucination_count / total_q) * 100 if total_q > 0 else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    summary = {
        "model": model_name,
        "total_questions": total_q,
        "overall_accuracy_pct": round(overall_accuracy, 2),
        "in_domain_total": in_domain_total,
        "in_domain_correct": in_domain_correct,
        "in_domain_accuracy_pct": round(in_domain_acc, 2),
        "out_of_domain_total": out_of_domain_total,
        "out_of_domain_correct": out_of_domain_correct,
        "out_of_domain_rejection_pct": round(ood_rejection_acc, 2),
        "hallucination_count": hallucination_count,
        "hallucination_rate_pct": round(hallucination_rate, 2),
        "avg_latency_seconds": round(avg_latency, 2),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    print("\n" + "=" * 78)
    print(" EVALUATION SUMMARY REPORT")
    print("=" * 78)
    print(f" Model Tested              : {summary['model']}")
    print(f" Total Questions           : {summary['total_questions']}")
    print(f" Overall Accuracy          : {summary['overall_accuracy_pct']}% ({total_correct}/{total_q})")
    print(f" In-Domain Accuracy        : {summary['in_domain_accuracy_pct']}% ({in_domain_correct}/{in_domain_total})")
    print(f" Out-of-Domain Rejection   : {summary['out_of_domain_rejection_pct']}% ({out_of_domain_correct}/{out_of_domain_total})")
    print(f" Hallucination Rate        : {summary['hallucination_rate_pct']}% ({hallucination_count}/{total_q})")
    print(f" Average Latency           : {summary['avg_latency_seconds']}s / question")
    print("=" * 78)

    # Save to disk
    safe_model_name = re.sub(r"[^a-zA-Z0-9]+", "_", model_name)
    out_file = output_path or f"eval_results_{safe_model_name}.json"
    out_path = Path(__file__).resolve().parent / out_file

    full_output = {
        "summary": summary,
        "results": results
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)

    print(f"\n[Eval] Full detailed benchmark saved to: {out_path}")
    return full_output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate ZUKA RAG Assistant")
    parser.add_argument("--model", "-m", default=CHAT_MODEL, help="Model name (e.g. qwen2.5:3b, qwen2.5:7b)")
    parser.add_argument("--questions", "-q", default="test_questions.json", help="Path to test_questions.json")
    parser.add_argument("--output", "-o", default=None, help="Output JSON path")
    parser.add_argument("--limit", "-l", type=int, default=None, help="Limit number of questions tested")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")

    args = parser.parse_args()
    run_evaluation(
        model_name=args.model,
        questions_path=args.questions,
        output_path=args.output,
        limit=args.limit,
        verbose=not args.quiet
    )
