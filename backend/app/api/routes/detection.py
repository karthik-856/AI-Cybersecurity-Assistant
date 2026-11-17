from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.detection.detection_service import detect_flow
from backend.app.detection.workload import model_task_lock
from backend.app.security.dependencies import get_current_user, require_role
from backend.app.database.session import get_db
from backend.app.soc.alert_service import create_alert_from_detection


router = APIRouter(prefix="/api/detection", tags=["Detection"])


class DetectFlowRequest(BaseModel):
    features: dict[str, float] = Field(..., description="The 14 ZUKA common ML features.")
    network_metadata: dict[str, Any] | None = None
    include_xai: bool = True


@router.get("/health")
def detection_health(
    _current_user=Depends(get_current_user),
):
    from backend.app.detection.model_service import zuka_model_service

    try:
        zuka_model_service.load()
        return {
            "status": "ok",
            "model_loaded": True,
            "feature_count": len(zuka_model_service.features),
            "class_count": len(zuka_model_service.labels),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Detection model unavailable: {exc}",
        )


@router.post("/predict")
def predict_flow(
    payload: DetectFlowRequest,
    _current_user=Depends(require_role("ADMIN", "SOC_ANALYST")),
    db=Depends(get_db),
):
    if not model_task_lock.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="The model is processing another request. Try again shortly.", headers={"Retry-After": "2"})
    try:
        result = detect_flow(
            features=payload.features,
            network_metadata=payload.network_metadata,
            include_xai=payload.include_xai,
        )

        alert = create_alert_from_detection(
            db=db,
            detection_result=result,
        )

        if alert is not None:
            result["alert"] = {
                "id": alert.id,
                "alert_id": alert.alert_id,
                "status": alert.status,
                "severity": alert.severity,
            }
        else:
            result["alert"] = None

        return result
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    finally:
        model_task_lock.release()
