from __future__ import annotations
from backend.app.core.time import utc_now

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models import User
from backend.app.security.dependencies import get_current_user


router = APIRouter(
    prefix="/api/database",
    tags=["Database Center"],
)


# ---------------------------------------------------------------------
# DATABASE TABLE MAP
# ---------------------------------------------------------------------

SUPPORTED_TABLES = {
    # Core SOC
    "alerts": "alerts",
    "incidents": "incidents",
    "investigations": "investigations",
    "analyst_actions": "analyst_actions",
    "analyst-actions": "analyst_actions",
    "analyst_action": "analyst_actions",
    "analyst-action": "analyst_actions",
    "audit_history": "audit_logs",
    "audit_logs": "audit_logs",
    # Telemetry & Reports
    "network_events": "network_events",
    "reports": "reports",
    # Access & Security
    "users": "users",
    "roles": "roles",
    "login_history": "login_audit_logs",
    "login_audit_logs": "login_audit_logs",
    "auth_sessions": "auth_sessions",
    "auth_otps": "auth_otps",
    "push_subscriptions": "push_subscriptions",
    # System
    "alembic_version": "alembic_version",
}

SENSITIVE_COLUMNS = {
    "hashed_password",
    "password",
    "password_hash",
    "hashed_otp",
    "otp_hash",
    "session_id",
    "auth",
    "p256dh",
    "secret",
}


# ---------------------------------------------------------------------
# ADMIN AUTHORIZATION
# ---------------------------------------------------------------------

def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Database Center is restricted to administrators.
    """
    role_name = current_user.role.name if hasattr(current_user.role, "name") else str(current_user.role)
    if role_name != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Database Center is available only to administrators.",
        )

    return current_user


# ---------------------------------------------------------------------
# DATABASE HELPERS
# ---------------------------------------------------------------------

def get_available_tables(
    db: Session,
) -> set[str]:
    """
    Return actual PostgreSQL tables.
    """
    inspector = inspect(db.bind)
    return {
        table.lower()
        for table in inspector.get_table_names()
    }


def normalize_table_name(
    table_name: str,
) -> str:
    """
    Normalize table names so Users, USERS and users resolve consistently.
    """
    return table_name.strip().lower()


def resolve_supported_table(
    table_name: str,
    db: Session | None = None,
) -> str:
    """
    Resolve a public table name or alias to a real PostgreSQL table.
    """
    normalized = normalize_table_name(table_name)

    if normalized in SUPPORTED_TABLES:
        return SUPPORTED_TABLES[normalized]

    if normalized in SUPPORTED_TABLES.values():
        return normalized

    if db is not None:
        avail = get_available_tables(db)
        if normalized in avail:
            return normalized

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Table '{table_name}' is not recognized or available.",
    )


def get_table_columns_meta(
    db: Session,
    table_name: str,
) -> list[dict[str, Any]]:
    inspector = inspect(db.bind)
    pk_constraint = inspector.get_pk_constraint(table_name) or {}
    pk_cols = set(pk_constraint.get("constrained_columns", []))

    columns_meta = []
    for col in inspector.get_columns(table_name):
        columns_meta.append({
            "name": col["name"],
            "type": str(col["type"]),
            "nullable": col.get("nullable", True),
            "default": str(col.get("default", "")) if col.get("default") is not None else None,
            "primary_key": col["name"] in pk_cols,
        })
    return columns_meta


def serialize_value(
    key: str,
    value: Any,
) -> Any:
    if key.lower() in SENSITIVE_COLUMNS:
        return "[REDACTED - HASHED]" if value else None

    if value is None:
        return None

    if isinstance(value, datetime):
        return f"{value.isoformat()}Z" if value.tzinfo is None else value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    if isinstance(value, (dict, list)):
        return value

    return value


def serialize_row(
    row: Any,
    columns: list[str],
) -> dict[str, Any]:
    mapping = row._mapping

    return {
        column: serialize_value(column, mapping.get(column))
        for column in columns
    }


# ---------------------------------------------------------------------
# GENERIC TABLE QUERY
# ---------------------------------------------------------------------

def get_table_rows(
    db: Session,
    table_name: str,
    limit: int = 25,
    offset: int = 0,
    search: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
) -> dict[str, Any]:
    actual_table = resolve_supported_table(table_name, db)
    available_tables = get_available_tables(db)

    if actual_table.lower() not in available_tables:
        return {
            "table": actual_table,
            "available": False,
            "columns": [],
            "records": [],
            "total": 0,
            "page": 1,
            "page_size": limit,
            "total_pages": 0,
        }

    inspector = inspect(db.bind)
    raw_columns = inspector.get_columns(actual_table)
    columns = [col["name"] for col in raw_columns]

    safe_limit = max(1, min(limit, 500))
    safe_offset = max(offset, 0)

    if not columns:
        return {
            "table": actual_table,
            "available": True,
            "columns": [],
            "records": [],
            "total": 0,
            "page": 1,
            "page_size": safe_limit,
            "total_pages": 0,
        }

    column_sql = ", ".join(f'"{col}"' for col in columns)
    query = f'SELECT {column_sql} FROM "{actual_table}"'
    params: dict[str, Any] = {}
    conditions = []

    if search and search.strip():
        search_term = f"%{search.strip()}%"
        for index, col in enumerate(columns):
            if col.lower() in SENSITIVE_COLUMNS:
                continue
            param_key = f"p_search_{index}"
            conditions.append(f'CAST("{col}" AS TEXT) ILIKE :{param_key}')
            params[param_key] = search_term

        if conditions:
            query += " WHERE (" + " OR ".join(conditions) + ")"

    # Count matching records
    count_query = f'SELECT COUNT(*) FROM "{actual_table}"'
    if conditions:
        count_query += " WHERE (" + " OR ".join(conditions) + ")"

    total_result = db.execute(text(count_query), params)
    total = int(total_result.scalar() or 0)

    # Determine order column
    order_clause = "1"
    valid_col_names = {c.lower(): c for c in columns}
    if sort_by and sort_by.lower() in valid_col_names:
        order_clause = f'"{valid_col_names[sort_by.lower()]}"'
    else:
        for candidate in ["id", "created_at", "detected_at", "event_time", "timestamp"]:
            if candidate in valid_col_names:
                order_clause = f'"{valid_col_names[candidate]}"'
                break

    direction = "ASC" if sort_order.strip().lower() == "asc" else "DESC"
    query += f" ORDER BY {order_clause} {direction} LIMIT {safe_limit} OFFSET {safe_offset}"

    result = db.execute(text(query), params)
    rows = result.fetchall()

    records = [serialize_row(row, columns) for row in rows]
    total_pages = max(1, (total + safe_limit - 1) // safe_limit) if total > 0 else 1
    current_page = (safe_offset // safe_limit) + 1

    return {
        "table": actual_table,
        "available": True,
        "columns": columns,
        "records": records,
        "total": total,
        "page": current_page,
        "page_size": safe_limit,
        "total_pages": total_pages,
        "sort_by": sort_by or order_clause.strip('"'),
        "sort_order": direction.lower(),
    }


# ---------------------------------------------------------------------
# HEALTH
# ---------------------------------------------------------------------

@router.get("/health")
def database_health(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Verify PostgreSQL connectivity and query response time.
    """
    start = utc_now()
    db.execute(text("SELECT 1"))
    latency_ms = (utc_now() - start).total_seconds() * 1000

    return {
        "status": "healthy",
        "database": "PostgreSQL",
        "latency_ms": round(latency_ms, 2),
    }


# ---------------------------------------------------------------------
# OVERVIEW & ENGINE CATALOG
# ---------------------------------------------------------------------

@router.get("/overview")
def database_overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Return comprehensive, real-time PostgreSQL database metrics,
    including disk size, active connections, and exact per-table statistics.
    """
    available_tables = get_available_tables(db)

    # 1. Database-level metrics
    db_size_pretty = "—"
    active_connections = 1
    pg_version = "PostgreSQL"
    try:
        db_stats = db.execute(
            text("""
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as db_size,
                    (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()) as active_conns,
                    version() as ver
            """)
        ).fetchone()
        if db_stats:
            db_size_pretty = db_stats[0]
            active_connections = int(db_stats[1] or 1)
            pg_version = db_stats[2].split(" on ")[0] if db_stats[2] else "PostgreSQL"
    except Exception:
        pass

    # 2. Table counts and catalog
    table_counts: dict[str, int] = {}
    tables_catalog: list[dict[str, Any]] = []
    total_records = 0

    filtered_tables = [
        t for t in sorted(available_tables)
        if not t.startswith("zuka_assistant") and t != "push_subscriptions"
    ]

    for table_name in filtered_tables:
        count = 0
        pretty_size = "—"
        try:
            cnt_res = db.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            count = int(cnt_res.scalar() or 0)
        except Exception:
            count = 0

        try:
            sz_res = db.execute(text(f"SELECT pg_size_pretty(pg_total_relation_size('\"{table_name}\"'))"))
            pretty_size = sz_res.scalar() or "—"
        except Exception:
            pretty_size = "—"

        table_counts[table_name] = count
        total_records += count

        # Friendly title
        title = table_name.replace("_", " ").title()

        tables_catalog.append({
            "name": table_name,
            "title": title,
            "records": count,
            "size": pretty_size,
        })

    # Legacy mapping for backwards compatibility with tests and callers
    users_count = table_counts.get("users", 0)
    login_history_count = table_counts.get("login_audit_logs", 0)
    network_events_count = table_counts.get("network_events", 0)
    alerts_count = table_counts.get("alerts", 0)
    incidents_count = table_counts.get("incidents", 0)
    investigations_count = table_counts.get("investigations", 0)
    analyst_actions_count = table_counts.get("analyst_actions", 0)
    audit_events_count = table_counts.get("audit_logs", 0)

    # Also map friendly keys into table_counts for compatibility
    table_counts["login_history"] = login_history_count
    table_counts["audit_history"] = audit_events_count

    return {
        "database": "PostgreSQL",
        "version": pg_version,
        "status": "CONNECTED",
        "historical_retention": True,
        "total_records": total_records,
        "db_size": db_size_pretty,
        "active_connections": active_connections,
        "users": users_count,
        "login_history": login_history_count,
        "network_events": network_events_count,
        "alerts": alerts_count,
        "incidents": incidents_count,
        "investigations": investigations_count,
        "analyst_actions": analyst_actions_count,
        "audit_events": audit_events_count,
        "available_tables": filtered_tables,
        "table_counts": table_counts,
        "tables_catalog": tables_catalog,
    }


# ---------------------------------------------------------------------
# LIST TABLES
# ---------------------------------------------------------------------

@router.get("/tables")
def list_database_tables(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Return the actual PostgreSQL tables.
    """
    tables = sorted(get_available_tables(db))
    return {
        "tables": tables,
        "count": len(tables),
    }


# ---------------------------------------------------------------------
# TABLE SCHEMA
# ---------------------------------------------------------------------

@router.get("/table/{table_name}/schema")
def database_table_schema(
    table_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Return column data types, nullability, default values, and primary key status.
    """
    actual_table = resolve_supported_table(table_name, db)
    columns_meta = get_table_columns_meta(db, actual_table)
    return {
        "table": actual_table,
        "columns": columns_meta,
        "column_count": len(columns_meta),
    }


# ---------------------------------------------------------------------
# SPECIFIC TABLE
# ---------------------------------------------------------------------

@router.get("/table/{table_name}")
def database_table(
    table_name: str,
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    sort_by: str | None = Query(default=None),
    sort_order: str = Query(default="desc"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Return records from a supported PostgreSQL table with sorting,
    search, and pagination.
    """
    actual_table = resolve_supported_table(table_name, db)
    return get_table_rows(
        db=db,
        table_name=actual_table,
        limit=limit,
        offset=offset,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


# ---------------------------------------------------------------------
# SECTION (For backwards compatibility)
# ---------------------------------------------------------------------

@router.get("/section/{section_name}")
def database_section(
    section_name: str,
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    sort_by: str | None = Query(default=None),
    sort_order: str = Query(default="desc"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Read one logical Database Center section.
    """
    actual_table = resolve_supported_table(section_name, db)
    result = get_table_rows(
        db=db,
        table_name=actual_table,
        limit=limit,
        offset=offset,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return {
        "section": section_name,
        **result,
    }
