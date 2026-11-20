from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
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
from backend.app.services.email_service import send_analyst_approved_notice
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
        email_verified=user.email_verified,
        approval_pending=user.approval_pending,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        last_login_ip=user.last_login_ip,
    )


@router.get("/users/{user_id}/approve-via-mail", include_in_schema=False)
def approve_user_via_mail(user_id: int):
    # Email scanners, forwarded links and GET requests cannot grant access.
    return RedirectResponse(settings.frontend_base_url.rstrip("/") + "/users", status_code=303,
                            headers={"Referrer-Policy": "no-referrer"})


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

    if user.role.name != "SOC_ANALYST":
        raise HTTPException(status_code=409, detail="This account is not a SOC Analyst request.")
    if not user.email_verified:
        raise HTTPException(status_code=409, detail="Email verification is required before approval.")
    if not user.approval_pending:
        if not user.is_active:
            raise HTTPException(status_code=409, detail="This account has no pending analyst request.")
        return AdminUserResponse(id=user.id, username=user.username, email=user.email,
            role=user.role.name, is_active=user.is_active, email_verified=user.email_verified,
            approval_pending=False, created_at=user.created_at,
            last_login_at=user.last_login_at, last_login_ip=user.last_login_ip)
    user.approval_pending = False
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
    try:
        send_analyst_approved_notice(user.email, user.username)
    except Exception:
        import logging
        logging.getLogger("zuka.mail").warning("Analyst approval confirmation could not be sent.")

    return AdminUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.name,
        is_active=user.is_active,
        email_verified=user.email_verified,
        approval_pending=user.approval_pending,
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
            email_verified=user.email_verified,
            approval_pending=user.approval_pending,
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

    if request.role in {"SOC_ANALYST", "ADMIN"} and (not user.email_verified or user.approval_pending):
        raise HTTPException(status_code=409, detail="Verify email and approve the analyst request before granting operational access.")
    if request.role == "VIEWER":
        user.approval_pending = False

    user.role_id = role.id

    db.commit()
    db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.name,
        is_active=user.is_active,
        email_verified=user.email_verified,
        approval_pending=user.approval_pending,
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

    if request.is_active and (not user.email_verified or user.approval_pending):
        raise HTTPException(status_code=409, detail="Email verification and analyst approval are required before activation.")

    user.is_active = request.is_active

    db.commit()
    db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.name,
        is_active=user.is_active,
        email_verified=user.email_verified,
        approval_pending=user.approval_pending,
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
