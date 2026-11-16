from __future__ import annotations
from backend.app.core.time import utc_now

from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_, select

from backend.app.database.session import get_db
from backend.app.security.dependencies import get_current_user, require_role
from backend.app.models import User
from backend.app.models.report import Report
from backend.app.reports.pdf_generator import generate_pdf
from backend.app.reports.report_service import (
    build_alert_report,
    build_detection_xai_report,
    build_incident_report,
    build_investigation_report,
    build_soc_summary,
)
from backend.app.schemas.report import ReportCreate, ReportListResponse, ReportResponse

router = APIRouter(
    prefix="/api/reports",
    tags=["Reports"],
)


def _record_generated_report(
    db: Session,
    title: str,
    report_type: str,
    entity_id: str | None,
    filename: str,
    size_bytes: int,
    username: str = "soc_operator",
) -> Report | None:
    try:
        now = utc_now()
        report_id = f"REP-{now.strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:4].upper()}"
        report_record = Report(
            report_id=report_id,
            title=title,
            report_type=report_type,
            entity_id=entity_id,
            status="READY",
            format="PDF",
            summary=f"Automated {report_type.replace('-', ' ').title()} document generated for {entity_id or 'SOC Platform'}.",
            file_path=f"reports/{filename}",
            file_size_bytes=size_bytes,
            generated_by_username=username,
            created_at=now,
            updated_at=now,
        )
        db.add(report_record)
        db.commit()
        db.refresh(report_record)
        return report_record
    except Exception:
        db.rollback()
        return None


def _pdf_response(
    report: dict,
    filename: str,
    db: Session | None = None,
    title: str = "SOC Security Report",
    report_type: str = "summary",
    entity_id: str | None = None,
    username: str = "soc_operator",
) -> Response:
    pdf_bytes = generate_pdf(report)
    if db is not None:
        _record_generated_report(
            db=db,
            title=title,
            report_type=report_type,
            entity_id=entity_id,
            filename=filename,
            size_bytes=len(pdf_bytes),
            username=username,
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("", response_model=ReportListResponse)
@router.get("/", response_model=ReportListResponse)
def list_reports(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    report_type: str | None = Query(None),
    search: str | None = Query(None),
):

    query = select(Report)

    if report_type:
        query = query.where(Report.report_type == report_type)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Report.report_id.ilike(term),
                Report.title.ilike(term),
                Report.entity_id.ilike(term),
                Report.summary.ilike(term),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(desc(Report.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": limit,
    }


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN", "SOC_ANALYST")),
):
    report_id = f"REP-{utc_now().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"
    new_report = Report(
        report_id=report_id,
        title=payload.title,
        report_type=payload.report_type,
        entity_id=payload.entity_id,
        status="READY",
        format=payload.format or "PDF",
        summary=payload.summary,
        parameters_json=payload.parameters_json or {},
        generated_by_id=current_user.id,
        generated_by_username=current_user.username,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    return new_report


@router.delete("/{report_id}")
def delete_report(
    report_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("ADMIN", "SOC_ANALYST")),
):
    report = db.execute(
        select(Report).where(Report.report_id == report_id)
    ).scalar_one_or_none()

    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found.")

    db.delete(report)
    db.commit()
    return {"success": True, "report_id": report_id}


@router.get("/summary")
def get_soc_summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return build_soc_summary(db)


@router.get("/alerts/{alert_id}")
def get_alert_report(
    alert_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    report = build_alert_report(db, alert_id)
    if report is None:
        raise HTTPException(404, "Alert not found.")
    return report


@router.get("/incidents/{incident_id}")
def get_incident_report(
    incident_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    report = build_incident_report(db, incident_id)
    if report is None:
        raise HTTPException(404, "Incident not found.")
    return report


@router.get("/investigations/{investigation_id}")
def get_investigation_report(
    investigation_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    report = build_investigation_report(db, investigation_id)
    if report is None:
        raise HTTPException(404, "Investigation not found.")
    return report


@router.get("/detection-xai/{alert_id}")
def get_detection_xai_report(
    alert_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    report = build_detection_xai_report(db, alert_id)
    if report is None:
        raise HTTPException(404, "Alert not found.")
    return report


@router.get("/alerts/{alert_id}/pdf")
def download_alert_pdf(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = build_alert_report(db, alert_id)
    if report is None:
        raise HTTPException(404, "Alert not found.")

    filename = f"ZUKA-{alert_id}-Alert-Report.pdf"
    return _pdf_response(
        report,
        filename,
        db=db,
        title=f"Alert Triage Report: {alert_id}",
        report_type="alert",
        entity_id=alert_id,
        username=current_user.username,
    )


@router.get("/incidents/{incident_id}/pdf")
def download_incident_pdf(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = build_incident_report(db, incident_id)
    if report is None:
        raise HTTPException(404, "Incident not found.")

    filename = f"ZUKA-{incident_id}-Incident-Report.pdf"
    return _pdf_response(
        report,
        filename,
        db=db,
        title=f"Security Incident Forensic Report: {incident_id}",
        report_type="incident",
        entity_id=incident_id,
        username=current_user.username,
    )


@router.get("/investigations/{investigation_id}/pdf")
def download_investigation_pdf(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = build_investigation_report(db, investigation_id)
    if report is None:
        raise HTTPException(404, "Investigation not found.")

    filename = f"ZUKA-{investigation_id}-Investigation-Report.pdf"
    return _pdf_response(
        report,
        filename,
        db=db,
        title=f"Investigation Department Casefile: {investigation_id}",
        report_type="investigation",
        entity_id=investigation_id,
        username=current_user.username,
    )


@router.get("/detection-xai/{alert_id}/pdf")
def download_detection_xai_pdf(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = build_detection_xai_report(db, alert_id)
    if report is None:
        raise HTTPException(404, "Alert not found.")

    filename = f"ZUKA-{alert_id}-Detection-XAI-Report.pdf"
    return _pdf_response(
        report,
        filename,
        db=db,
        title=f"Detection & XAI Evidence Report: {alert_id}",
        report_type="detection-xai",
        entity_id=alert_id,
        username=current_user.username,
    )


@router.get("/summary/pdf")
def download_soc_summary_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = build_soc_summary(db)
    filename = "ZUKA-SOC-Summary-Report.pdf"
    return _pdf_response(
        report,
        filename,
        db=db,
        title="ZUKA Executive SOC Summary Report",
        report_type="summary",
        entity_id="SOC-SYSTEM",
        username=current_user.username,
    )


@router.get("/{report_id}")
def get_stored_report_data(
    report_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    report = db.execute(
        select(Report).where(Report.report_id == report_id)
    ).scalar_one_or_none()

    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found.")

    details: dict[str, Any] = {}
    if report.report_type == "summary":
        details = build_soc_summary(db)
    elif report.report_type == "incident" and report.entity_id:
        details = build_incident_report(db, report.entity_id) or {}
    elif report.report_type == "investigation" and report.entity_id:
        details = build_investigation_report(db, report.entity_id) or {}
    elif report.report_type in ("alert", "detection-xai") and report.entity_id:
        details = build_detection_xai_report(db, report.entity_id) or build_alert_report(db, report.entity_id) or {}

    return {
        "report_id": report.report_id,
        "title": report.title,
        "report_type": report.report_type,
        "entity_id": report.entity_id,
        "status": report.status,
        "format": report.format,
        "summary": report.summary,
        "file_size_bytes": report.file_size_bytes,
        "generated_by_username": report.generated_by_username,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "content": details,
    }
