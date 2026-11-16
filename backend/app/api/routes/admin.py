from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.database.session import get_db
from backend.app.models import LoginAuditLog, Role, User
from backend.app.schemas.admin import (
    AdminUserResponse,
    CreateUserRequest,
    LoginAuditResponse,
    UpdateUserRoleRequest,
    UpdateUserStatusRequest,
)
from backend.app.security.dependencies import require_role
from backend.app.security.password import hash_password, validate_password_complexity
from backend.app.services.email_service import send_analyst_approval_email
from backend.app.audit.audit_service import record_audit_event


router = APIRouter(
    prefix="/api/admin",
    tags=["Administration"],
)

@router.post(
    "/users",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(
        require_role("ADMIN")
    ),
    db: Session = Depends(get_db),
):
    allowed_roles = {
        "ADMIN",
        "SOC_ANALYST",
        "VIEWER",
    }

    if request.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid role. Allowed roles: "
                "ADMIN, SOC_ANALYST, VIEWER."
            ),
        )

    existing_username = db.scalar(
        select(User).where(
            User.username == request.username
        )
    )

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists.",
        )

    existing_email = db.scalar(
        select(User).where(
            User.email == request.email
        )
    )

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists.",
        )

    is_valid, pwd_err = validate_password_complexity(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=pwd_err or "Password does not meet enterprise complexity requirements.",
        )

    role = db.scalar(
        select(Role).where(
            Role.name == request.role
        )
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Requested role does not exist.",
        )

    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(
            request.password
        ),
        is_active=True,
        role_id=role.id,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    record_audit_event(
        db,
        user_id=current_user.id,
        action="USER_CREATED",
        resource_type="USER",
        resource_id=str(user.id),
        description=f"User '{user.username}' created with role '{user.role.name}'.",
        commit=True,
    )

    return AdminUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.name,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        last_login_ip=user.last_login_ip,
    )


@router.get("/users/{user_id}/approve-via-mail", response_class=HTMLResponse)
def approve_user_via_mail(
    user_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """Email action callback to approve and activate a pending SOC Analyst account."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("action") != "approve_analyst" or int(payload.get("sub")) != user_id:
            raise HTTPException(status_code=400, detail="Invalid approval token.")
    except Exception:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head><title>ZUKA SOC — Token Expired</title></head>
            <body style="margin:0;padding:50px;background:#0b1220;color:#f87171;font-family:sans-serif;text-align:center;">
              <div style="max-width:500px;margin:auto;background:#111827;border:1px solid #1e293b;border-radius:12px;padding:36px;">
                <h2 style="margin-top:0;">Authorization Token Invalid or Expired</h2>
                <p style="color:#94a3b8;font-size:14px;">This security token could not be verified. You can still approve this analyst directly from the ZUKA User Management console.</p>
                <a href="http://127.0.0.1:5173/users" style="display:inline-block;margin-top:16px;background:#0284c7;color:#fff;text-decoration:none;padding:10px 22px;border-radius:6px;font-weight:600;">Open User Management</a>
              </div>
            </body>
            </html>
            """,
            status_code=400,
        )

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User account not found.")

    user.is_active = True
    db.commit()

    record_audit_event(
        db,
        user_id=user.id,
        action="ANALYST_APPROVED_VIA_EMAIL",
        resource_type="USER",
        resource_id=str(user.id),
        description=f"SOC Analyst account '{user.username}' was authorized and activated via administrative email link.",
        commit=True,
    )

    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          <title>ZUKA SOC — Account Approved</title>
          <style>
            body {{ margin:0; padding:40px; background:#0b1220; color:#f8fafc; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; display:flex; justify-content:center; align-items:center; min-height:80vh; }}
            .card {{ max-width:540px; background:#111827; border:1px solid #263244; border-radius:14px; padding:38px; text-align:center; box-shadow:0 12px 30px rgba(0,0,0,0.5); }}
            .icon {{ font-size:46px; margin-bottom:12px; color:#10b981; }}
            h1 {{ font-size:22px; margin:0 0 12px; color:#f8fafc; font-weight:700; }}
            p {{ color:#94a3b8; font-size:14px; line-height:1.6; margin:0 0 24px; }}
            .badge {{ display:inline-block; padding:5px 14px; background:#064e3b; color:#34d399; border-radius:6px; font-weight:700; font-size:12px; margin-bottom:18px; }}
            .btn {{ display:inline-block; background:#0284c7; color:#ffffff; text-decoration:none; padding:12px 28px; border-radius:8px; font-weight:700; font-size:14px; }}
          </style>
        </head>
        <body>
          <div class="card">
            <div class="icon">✔</div>
            <div class="badge">ACCOUNT AUTHORIZED & ACTIVATED</div>
            <h1>SOC Analyst Approved Successfully</h1>
            <p>The SOC Analyst account for <strong>{user.username}</strong> (<code style="color:#38bdf8;">{user.email}</code>) has been approved and activated. The analyst is now authorized to sign in and perform triage investigations.</p>
            <a href="http://127.0.0.1:5173/login" class="btn">Return to ZUKA SOC Console</a>
          </div>
        </body>
        </html>
        """
    )


@router.post("/users/{user_id}/approve", response_model=AdminUserResponse)
def approve_user_in_console(
    user_id: int,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """Directly approve and activate an account from the User Management console."""
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = True
    db.commit()
    db.refresh(user)

    record_audit_event(
        db,
        user_id=current_user.id,
        action="ANALYST_APPROVED_IN_CONSOLE",
        resource_type="USER",
        resource_id=str(user.id),
        description=f"SOC Analyst account '{user.username}' was authorized and activated in the User Management console by admin '{current_user.username}'.",
        commit=True,
    )

    return AdminUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.name,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        last_login_ip=user.last_login_ip,
    )

@router.get(
    "/users",
    response_model=list[AdminUserResponse],
)
def list_users(
    current_user: User = Depends(
        require_role("ADMIN")
    ),
    db: Session = Depends(get_db),
):
    users = db.scalars(
        select(User)
        .order_by(User.id)
    ).all()

    return [
        AdminUserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.name,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            last_login_ip=user.last_login_ip,
        )
        for user in users
    ]


@router.patch(
    "/users/{user_id}/role",
    response_model=AdminUserResponse,
)
def update_user_role(
    user_id: int,
    request: UpdateUserRoleRequest,
    current_user: User = Depends(
        require_role("ADMIN")
    ),
    db: Session = Depends(get_db),
):
    allowed_roles = {
        "ADMIN",
        "SOC_ANALYST",
        "VIEWER",
    }

    if request.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid role. Allowed roles: "
                "ADMIN, SOC_ANALYST, VIEWER."
            ),
        )

    user = db.scalar(
        select(User).where(User.id == user_id)
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # Prevent an administrator from accidentally
    # removing their own ADMIN role.
    if (
        user.id == current_user.id
        and request.role != "ADMIN"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "You cannot remove your own ADMIN role."
            ),
        )

    role = db.scalar(
        select(Role).where(
            Role.name == request.role
        )
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Requested role does not exist.",
        )

    user.role_id = role.id

    db.commit()
    db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.name,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        last_login_ip=user.last_login_ip,
    )


@router.patch(
    "/users/{user_id}/status",
    response_model=AdminUserResponse,
)
def update_user_status(
    user_id: int,
    request: UpdateUserStatusRequest,
    current_user: User = Depends(
        require_role("ADMIN")
    ),
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(User.id == user_id)
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # Prevent an administrator from disabling
    # their own account.
    if (
        user.id == current_user.id
        and not request.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "You cannot deactivate your own account."
            ),
        )

    user.is_active = request.is_active

    db.commit()
    db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.name,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        last_login_ip=user.last_login_ip,
    )


@router.get(
    "/login-audit",
    response_model=list[LoginAuditResponse],
)
def login_audit(
    current_user: User = Depends(
        require_role("ADMIN")
    ),
    db: Session = Depends(get_db),
):
    logs = db.scalars(
        select(LoginAuditLog)
        .order_by(LoginAuditLog.login_at.desc())
        .limit(200)
    ).all()

    results = []

    for log in logs:
        username = None

        if log.user_id is not None:
            user = db.scalar(
                select(User).where(
                    User.id == log.user_id
                )
            )

            if user is not None:
                username = user.username

        results.append(
            LoginAuditResponse(
                id=log.id,
                user_id=log.user_id,
                username=username,
                login_at=log.login_at,
                ip_address=log.ip_address,
                success=log.success,
                user_agent=log.user_agent,
            )
        )

    return results


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_200_OK,
)
def delete_user(
    user_id: int,
    current_user: User = Depends(
        require_role("ADMIN")
    ),
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(User.id == user_id)
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account.",
        )

    from backend.app.models.login_audit import LoginAuditLog

    db.query(LoginAuditLog).filter(LoginAuditLog.user_id == user.id).update({LoginAuditLog.user_id: None})
    db.delete(user)
    db.commit()

    return {
        "message": f"User {user.username} deleted successfully.",
        "user_id": user_id,
    }
