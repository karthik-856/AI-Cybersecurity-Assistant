"""Convert the shipped JSON model to XGBoost's efficient UBJ format at build time."""
from pathlib import Path
import gzip
import shutil
import tempfile

import xgboost as xgb


def main():
    directory = Path(__file__).resolve().parents[1] / "models" / "zuka_unified_xgboost"
    target = directory / "model.ubj"
    if target.exists():
        return
    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp) / "model.json"
        with gzip.open(directory / "model.json.gz", "rb") as compressed, source.open("wb") as output:
            shutil.copyfileobj(compressed, output)
        model = xgb.Booster(params={"nthread": 1})
        model.load_model(source)
        model.save_model(target)
    print("Prepared binary model:", target.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
