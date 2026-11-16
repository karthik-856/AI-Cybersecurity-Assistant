"""Check staged publication files for local state, oversized files, and credential patterns."""
import re
import subprocess
from pathlib import Path


def main():
    files = subprocess.check_output(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]).decode().split("\0")
    patterns = [
        re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
        re.compile(rb"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}\b"),
        re.compile(rb"\bAIza[A-Za-z0-9_-]{35}\b"),
        re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    ]
    errors = []
    checked = 0
    for name in filter(None, files):
        path = Path(name)
        if path.name == ".env" or path.suffix.lower() in {".pem", ".key", ".db", ".sqlite", ".sqlite3"}:
            errors.append(f"Local state or credential file: {name}")
        content = subprocess.check_output(["git", "show", f":{name}"])
        if len(content) >= 95 * 1024 * 1024:
            errors.append(f"File exceeds publication size budget: {name}")
        if b"\0" not in content[:8192] and any(pattern.search(content) for pattern in patterns):
            errors.append(f"Possible credential content: {name}")
        checked += 1
    print(f"Checked {checked} staged files.")
    for error in errors:
        print(error)
    if errors:
        raise SystemExit(1)
    print("Publication size, local-state, and credential-pattern checks passed.")


if __name__ == "__main__":
    main()
