from __future__ import annotations

import numpy as np
import xgboost as xgb

from backend.app.detection.model_service import zuka_model_service


class ZukaXAIService:
    """Generate real TreeSHAP explanations for ZUKA predictions."""

    def __init__(self):
        self._explainer = None

    def _get_explainer(self):
        zuka_model_service.load()

        if self._explainer is None:
            self._explainer = zuka_model_service._model

        return self._explainer

    def explain(
        self,
        values: dict,
        prediction: dict,
        top_n: int = 5,
    ) -> dict:

        zuka_model_service.load()

        features = zuka_model_service.features
        labels = zuka_model_service.labels

        row = {
            feature: float(values[feature])
            for feature in features
        }

        dataframe = np.asarray([[row[name] for name in features]], dtype=np.float32)

        explainer = self._get_explainer()

        # XGBoost's native TreeSHAP reuses the loaded trees instead of creating
        # a second full model in memory. The final column is the bias term.
        shap_values = explainer.predict(
            xgb.DMatrix(dataframe, feature_names=features), pred_contribs=True, strict_shape=True,
            iteration_range=zuka_model_service.iteration_range,
        )[:, :, :-1].transpose(0, 2, 1)

        class_id = int(
            prediction["predicted_class_id"]
        )

        number_of_features = len(features)
        number_of_classes = len(labels)

        if isinstance(shap_values, np.ndarray):

            if shap_values.ndim == 3:

                if shap_values.shape == (
                    1,
                    number_of_features,
                    number_of_classes,
                ):
                    class_values = shap_values[
                        0, :, class_id
                    ]

                elif shap_values.shape == (
                    1,
                    number_of_classes,
                    number_of_features,
                ):
                    class_values = shap_values[
                        0, class_id, :
                    ]

                else:
                    raise RuntimeError(
                        f"Unexpected SHAP shape: "
                        f"{shap_values.shape}"
                    )

            elif shap_values.ndim == 2:
                class_values = shap_values[0]

            else:
                raise RuntimeError(
                    f"Unexpected SHAP dimensions: "
                    f"{shap_values.ndim}"
                )

        elif isinstance(shap_values, list):

            if len(shap_values) == number_of_classes:
                class_values = np.asarray(
                    shap_values[class_id]
                )[0]

            elif len(shap_values) == 1:
                class_values = np.asarray(
                    shap_values[0]
                )[0]

            else:
                raise RuntimeError(
                    "Unexpected SHAP class output."
                )

        else:
            raise RuntimeError(
                "Unsupported SHAP output type."
            )

        ranking = np.argsort(
            np.abs(class_values)
        )[::-1]

        top_contributions = []

        for index in ranking[:top_n]:

            index = int(index)
            shap_value = float(
                class_values[index]
            )

            top_contributions.append(
                {
                    "feature": features[index],
                    "feature_value": float(
                        dataframe[0, index]
                    ),
                    "shap_value": shap_value,
                    "direction": (
                        "supports_prediction"
                        if shap_value >= 0
                        else "opposes_prediction"
                    ),
                }
            )

        supporting = [
            item
            for item in top_contributions
            if item["shap_value"] > 0
        ]

        opposing = [
            item
            for item in top_contributions
            if item["shap_value"] < 0
        ]

        return {
            "method": "TreeSHAP",
            "predicted_class": prediction[
                "predicted_class"
            ],
            "confidence": prediction[
                "confidence"
            ],
            "top_contributions": top_contributions,
            "supporting_features": supporting,
            "opposing_features": opposing,
        }


zuka_xai_service = ZukaXAIService()
