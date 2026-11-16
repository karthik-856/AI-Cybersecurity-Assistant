"""Deterministic local text retrieval; no downloaded model or paid API is needed."""
import hashlib
import math
import re
from collections import Counter

STOP_WORDS = {"a", "an", "the", "is", "are", "do", "does", "i", "my", "me", "how", "what", "to", "of", "in", "on", "and", "can", "for", "this", "with", "it"}


def encode_text(text: str, dimensions: int = 1024) -> list[float]:
    counts = Counter(token.rstrip("s") for token in re.findall(r"[a-z][a-z0-9_]+", text.lower()) if token not in STOP_WORDS)
    vector = [0.0] * dimensions
    for token, count in counts.items():
        position = int.from_bytes(hashlib.blake2b(token.encode(), digest_size=4).digest(), "little") % dimensions
        vector[position] += 1.0 + math.log(count)
    return vector
