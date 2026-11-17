from __future__ import annotations

import csv

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.database.session import get_db
from backend.app.models import User, Incident
from backend.app.replay.replay_service import replay_dataset, PROJECT_ROOT
from backend.app.detection.workload import model_task_lock
from backend.app.security.dependencies import get_current_user, require_role
from backend.app.soc.incident_service import create_incident_from_alert


router = APIRouter(
    prefix="/api/replay",
    tags=["Dataset Replay"],
)


class ReplayNextRequest(BaseModel):
    row_index: int = Field(
        default=0,
        ge=0,
        description="Zero-based row index in the unified test dataset.",
    )
    include_xai: bool = True


class DemoReplayRequest(BaseModel):
    row_index: int = Field(default=0, ge=0, le=1000000)


@router.post("/demo")
def process_demo_event(
    payload: DemoReplayRequest,
    current_user: User = Depends(require_role("ADMIN", "SOC_ANALYST")),
    db=Depends(get_db),
):
    path = PROJECT_ROOT / "data" / "sample_replay.csv"
    try:
        with path.open(encoding="utf-8") as source:
            row_count = sum(1 for _ in csv.DictReader(source))
    except OSError as exc:
        raise HTTPException(
            status_code=503, detail="The demonstration sample is unavailable."
        ) from exc
    if not row_count:
        raise HTTPException(status_code=503, detail="The demonstration sample is unavailable.")
    if not model_task_lock.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="The model is processing another request. Try again shortly.", headers={"Retry-After": "2"})
    try:
        index = payload.row_index % row_count
        result = replay_dataset(
            csv_path=path, start_row=index, max_rows=1, include_xai=True, db=db
        )
        row_result = result["results"][0]
        incident = db.query(Incident).filter_by(incident_id=row_result["incident_id"]).first() if row_result["incident_id"] else None
        return {
            "status": "processed",
            "message": "Included demonstration sample processed.",
            "row_index": index,
            "next_row_index": (index + 1) % row_count,
            "processed": True,
            "result": row_result,
            "incident": ({
                "id": incident.id,
                "incident_id": incident.incident_id,
                "alert_id": incident.alert_id,
                "severity": incident.severity,
                "priority": incident.priority,
                "status": incident.status,
            } if incident else None),
        }
    finally:
        model_task_lock.release()


@router.post("/next")
def replay_next(
    payload: ReplayNextRequest,
    current_user: User = Depends(require_role("ADMIN", "SOC_ANALYST")),
    db=Depends(get_db),
):
    """
    Process exactly one dataset row through the ZUKA detection pipeline.

    This endpoint is intentionally dataset replay only. It does not
    capture packets from a network interface.
    """

    if not model_task_lock.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="The model is processing another request. Try again shortly.", headers={"Retry-After": "2"})
    try:
        result = replay_dataset(
            start_row=payload.row_index,
            max_rows=1,
            include_xai=payload.include_xai,
            db=db,
        )

        if result["processed_rows"] == 0:
            # Wrap around to start of dataset for continuous loop replay
            result = replay_dataset(
                start_row=0,
                max_rows=1,
                include_xai=payload.include_xai,
                db=db,
            )
            if result["processed_rows"] == 0:
                return {
                    "status": "completed",
                    "message": "Replay dataset is empty or unreadable.",
                    "row_index": payload.row_index,
                    "next_row_index": 0,
                    "processed": False,
                    "result": None,
                }
            looped = True
        else:
            looped = False

        row_result = result["results"][0]


        incident = None

        # Automatically create an incident for attack alerts.
        alert_id = row_result.get("alert_id")

        if alert_id:
            incident = create_incident_from_alert(
                db=db,
                alert_id=alert_id,
            )

        return {
            "status": "processed",
            "message": "Dataset finished. Automatically looped back to start for continuous replay." if looped else "Dataset row processed successfully.",
            "row_index": 0 if looped else payload.row_index,
            "next_row_index": 1 if looped else payload.row_index + 1,
            "processed": True,
            "looped": looped,
            "result": row_result,

            "incident": (
                {
                    "id": incident.id,
                    "incident_id": incident.incident_id,
                    "alert_id": incident.alert_id,
                    "severity": incident.severity,
                    "priority": incident.priority,
                    "status": incident.status,
                }
                if incident is not None
                else None
            ),
        }

    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Dataset replay failed: {exc}",
        ) from exc
    finally:
        model_task_lock.release()
