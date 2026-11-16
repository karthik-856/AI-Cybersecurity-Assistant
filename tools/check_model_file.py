from pathlib import Path
import hashlib

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "multiclass"
    / "xgb_model.joblib"
)

print("=" * 80)
print("ZUKA — MODEL FILE DIAGNOSTIC")
print("=" * 80)

print()
print("MODEL PATH")
print("-" * 80)
print(MODEL_PATH)

if not MODEL_PATH.exists():
    print("[FAIL] Model file does not exist.")
    raise SystemExit(1)

size_bytes = MODEL_PATH.stat().st_size
size_mb = size_bytes / (1024 * 1024)

print(f"[OK] File exists")
print(f"Size      : {size_bytes:,} bytes")
print(f"Size      : {size_mb:.2f} MB")

print()
print("FILE HASH")
print("-" * 80)

sha256 = hashlib.sha256()

with open(MODEL_PATH, "rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        sha256.update(chunk)

print("SHA256:")
print(sha256.hexdigest())

print()
print("=" * 80)
print("NEXT STEP")
print("=" * 80)
print()
print("If the file is unexpectedly small or was copied/downloaded")
print("incompletely, replace it with a verified model artifact.")
print()
print("Do NOT modify xgboost_detector.py yet.")
print()