"""Build a 300-question website benchmark from the existing suite and canonical KB."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAG_DIR = Path(__file__).resolve().parent
SOURCE_QUESTIONS = RAG_DIR / "test_questions_220.json"
KNOWLEDGE_BASE = ROOT / "docs" / "zuka_website_knowledge_base.md"
OUTPUT = RAG_DIR / "test_questions_300.json"
TARGET_COUNT = 300


def read_canonical_qas(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    section = "Website Knowledge Base"
    entries: list[dict[str, str]] = []
    current_question: str | None = None
    answer_lines: list[str] = []

    def flush() -> None:
        if current_question:
            answer = "\n".join(answer_lines).strip()
            if answer:
                entries.append({
                    "question": current_question,
                    "expected_answer": answer,
                    "target_section": section,
                })

    for line in text.splitlines():
        if line.startswith("## "):
            flush()
            current_question = None
            answer_lines = []
            section = line[3:].strip()
        elif line.startswith("### "):
            flush()
            current_question = line[4:].strip()
            answer_lines = []
        elif current_question:
            answer_lines.append(line)

    flush()
    return entries


def main() -> None:
    base: list[dict[str, Any]] = json.loads(SOURCE_QUESTIONS.read_text(encoding="utf-8"))
    canonical = read_canonical_qas(KNOWLEDGE_BASE)

    if len(base) > TARGET_COUNT:
        raise ValueError(f"Existing suite already exceeds {TARGET_COUNT} questions")
    needed = TARGET_COUNT - len(base)
    additions: list[dict[str, Any]] = []

    for entry in canonical:
        if len(additions) >= needed:
            break
        additions.append({
            "id": f"Q{len(base) + len(additions) + 1:03d}",
            "category": "website_knowledge",
            "target_section": entry["target_section"],
            "question": entry["question"],
            "expected_answer": entry["expected_answer"],
            "is_out_of_domain": False,
        })

    # Add paraphrases from canonical Q&As to reach exactly 300. These exercise
    # the natural-question routing used by Ask Zuka without introducing writes.
    paraphrase_prefixes = [
        "For the ZUKA website, can you answer this: ",
        "Please explain this ZUKA question: ",
        "I need to know about the website: ",
    ]
    variant_index = 0
    while len(additions) < needed:
        source = canonical[variant_index % len(canonical)]
        prefix = paraphrase_prefixes[(variant_index // len(canonical)) % len(paraphrase_prefixes)]
        question = prefix + source["question"].rstrip("?") + "?"
        additions.append({
            "id": f"Q{len(base) + len(additions) + 1:03d}",
            "category": "website_knowledge_paraphrase",
            "target_section": source["target_section"],
            "question": question,
            "expected_answer": source["expected_answer"],
            "is_out_of_domain": False,
        })
        variant_index += 1

    suite = base + additions
    if len(suite) != TARGET_COUNT:
        raise ValueError(f"Generated {len(suite)} questions; expected {TARGET_COUNT}")
    if len({item["question"].casefold() for item in suite}) != TARGET_COUNT:
        raise ValueError("Question suite contains duplicate prompts")

    OUTPUT.write_text(json.dumps(suite, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_of_domain = sum(bool(item.get("is_out_of_domain")) for item in suite)
    print(f"Wrote {len(suite)} questions ({len(suite) - out_of_domain} in-scope, {out_of_domain} out-of-scope) to {OUTPUT}")


if __name__ == "__main__":
    main()
