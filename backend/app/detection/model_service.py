from __future__ import annotations

import gzip
import json
from pathlib import Path
from threading import Lock

import numpy as np
import pandas as pd
import xgboost as xgb  # type: ignore[reportMissingImports]


class ZukaModelService:
    """Loads and serves predictions from the trained ZUKA unified XGBoost model."""

    def __init__(self, root_dir: str | Path | None = None) -> None:
        self.root = (
            Path(root_dir)
            if root_dir
            else Path(__file__).resolve().parents[3]
        )

        self.model_dir = self.root / "models" / "zuka_unified_xgboost"

        self.model_path = self.model_dir / "model.json"
        self.labels_path = self.model_dir / "label_encoder.json"
        self.schema_path = self.model_dir / "feature_schema.json"

        self._model = None
        self._features = None
        self._labels = None

        self._lock = Lock()

    @staticmethod
    def _load_json(path: Path) -> dict:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _load_features(schema: dict) -> list[str]:
        if isinstance(schema, list):
            return [str(value) for value in schema]

        for key in (
            "features",
            "feature_names",
            "ml_features",
            "columns",
        ):
            value = schema.get(key)

            if isinstance(value, list):
                return [str(item) for item in value]

        raise RuntimeError(
            "feature_schema.json does not contain a valid feature list."
        )

    @staticmethod
    def _load_labels(mapping: dict) -> dict[int, str]:
        if isinstance(mapping.get("classes"), list):
            return {
                index: str(label)
                for index, label in enumerate(mapping["classes"])
            }

        result = {}

        for key, value in mapping.items():
            try:
                result[int(key)] = str(value)
            except (TypeError, ValueError):
                continue

        if not result:
            raise RuntimeError(
                "label_encoder.json does not contain a valid class mapping."
            )

        return result

    def load(self) -> None:
        """Load model artifacts once."""

        if self._model is not None:
            return

        with self._lock:

            if self._model is not None:
                return

            required_files = (
                self.labels_path,
                self.schema_path,
            )

            for path in required_files:
                if not path.exists():
                    raise FileNotFoundError(
                        f"ZUKA model artifact not found: {path}"
                    )

            print("Loading ZUKA unified XGBoost model...")

            model = xgb.XGBClassifier()

            if self.model_path.exists():
                model.load_model(str(self.model_path))
            else:
                compressed = self.model_path.with_suffix(".json.gz")
                with gzip.open(compressed, "rb") as model_file:
                    model.load_model(bytearray(model_file.read()))

            schema = self._load_json(self.schema_path)
            label_mapping = self._load_json(self.labels_path)

            features = self._load_features(schema)
            labels = self._load_labels(label_mapping)

            if len(features) != 14:
                raise RuntimeError(
                    f"Expected 14 ZUKA common features, "
                    f"found {len(features)}."
                )

            if len(labels) != 13:
                raise RuntimeError(
                    f"Expected 13 ZUKA attack classes, "
                    f"found {len(labels)}."
                )

            self._model = model
            self._features = features
            self._labels = labels

            print("ZUKA model loaded successfully.")
            print(f"  Features: {len(features)}")
            print(f"  Classes : {len(labels)}")

    @property
    def features(self) -> list[str]:
        self.load()

        return list(self._features)

    @property
    def labels(self) -> dict[int, str]:
        self.load()

        return dict(self._labels)

    def predict(self, values: dict) -> dict:
        """Run one prediction using the 14 ZUKA ML features."""

        self.load()

        missing = [
            feature
            for feature in self._features
            if feature not in values
        ]

        if missing:
            raise ValueError(
                f"Missing required ZUKA features: {missing}"
            )

        row = {}

        for feature in self._features:

            try:
                row[feature] = float(values[feature])

            except (TypeError, ValueError):

                raise ValueError(
                    f"Feature '{feature}' must be numeric."
                )

        dataframe = pd.DataFrame(
            [row],
            columns=self._features,
        )

        numeric_values = dataframe.to_numpy(dtype=float)

        if not np.isfinite(numeric_values).all():
            raise ValueError(
                "ZUKA features must contain only finite values."
            )

        if (numeric_values < 0).any():
            raise ValueError(
                "ZUKA physical-domain features cannot be negative."
            )

        probabilities = self._model.predict_proba(dataframe)[0]

        predicted_id = int(np.argmax(probabilities))

        confidence = float(probabilities[predicted_id])

        predicted_class = self._labels.get(
            predicted_id,
            f"CLASS_{predicted_id}",
        )

        ranked_indices = np.argsort(probabilities)[::-1]

        top_predictions = []

        for index in ranked_indices[:3]:

            index = int(index)

            top_predictions.append(
                {
                    "class_id": index,
                    "class": self._labels.get(
                        index,
                        f"CLASS_{index}",
                    ),
                    "confidence": float(
                        probabilities[index]
                    ),
                }
            )

        return {
            "predicted_class_id": predicted_id,
            "predicted_class": predicted_class,
            "confidence": confidence,
            "top_predictions": top_predictions,
            "features_used": list(self._features),
        }


zuka_model_service = ZukaModelService()
