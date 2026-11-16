from pathlib import Path
import sys
import joblib
import xgboost

MODEL_PATH = (
    Path(__file__).resolve().parents[1]
    / "models"
    / "multiclass"
    / "xgb_model.joblib"
)

print("=" * 80)
print("ZUKA — DIRECT MODEL LOAD TEST")
print("=" * 80)

print(f"Python   : {sys.version}")
print(f"XGBoost  : {xgboost.__version__}")
print(f"Model    : {MODEL_PATH}")
print(f"Exists   : {MODEL_PATH.exists()}")
print(f"Size     : {MODEL_PATH.stat().st_size:,} bytes")

print()
print("Loading model...")
print("-" * 80)

try:
    model = joblib.load(MODEL_PATH)

    print("[OK] MODEL LOADED SUCCESSFULLY")
    print(f"Type      : {type(model).__name__}")

    if hasattr(model, "n_features_in_"):
        print(f"Features  : {model.n_features_in_}")

    if hasattr(model, "classes_"):
        print(f"Classes   : {model.classes_}")

except Exception as exc:
    print("[FAIL] MODEL LOAD FAILED")
    print()
    print(f"Error type : {type(exc).__name__}")
    print(f"Error      : {exc}")

print()
print("=" * 80)