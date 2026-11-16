from backend.app.core.time import utc_now
from datetime import datetime, timedelta
import hashlib
import hmac
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
import jwt
from jwt import PyJWTError as JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models import AuthSession, LoginAuditLog, Role, User
from backend.app.models.auth_otp import AuthOtp
from backend.app.schemas.auth import (
    ChangePasswordRequest,
    EmailOtpRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    ResendVerificationRequest,
    TokenResponse,
    TwoFactorLoginRequest,
    TwoFactorRequest,
    TwoFactorVerifyRequest,
    UserResponse,
    VerifyResetOtpRequest,
)
from backend.app.security.jwt import create_access_token, create_session_id
from backend.app.security.password import (
    hash_password,
    verify_password,
    validate_password_complexity,
)
from backend.app.core.config import settings
from backend.app.services.email_service import (
    send_email_verification_otp,
    send_password_reset_otp,
    send_two_factor_otp,
    send_analyst_approval_email,
)
from backend.app.security.dependencies import get_current_user


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
PASSWORD_RESET = "PASSWORD_RESET"
TWO_FACTOR_SETUP = "TWO_FACTOR_SETUP"
TWO_FACTOR_LOGIN = "TWO_FACTOR_LOGIN"
TWO_FACTOR_CHALLENGE = "2FA_LOGIN_CHALLENGE"


def _utcnow() -> datetime:
    return utc_now()


def _create_auth_session(
    db: Session,
    user_id: int,
    client_ip: str | None,
    user_agent: str | None,
) -> AuthSession:
    """Create a server-side authentication session bound to the issued JWT."""

    now = _utcnow()
    session_expiry_minutes = settings.access_token_expire_minutes

    session = AuthSession(
        session_id=create_session_id(),
        user_id=user_id,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(minutes=session_expiry_minutes),
        ip_address=client_ip,
        user_agent=user_agent,
        revoked_at=None,
        is_current=True,
    )

    db.add(session)
    db.flush()

    return session


def _otp_hash(otp: str) -> str:
    secret = getattr(
        settings,
        "otp_secret",
        None,
    ) or settings.jwt_secret_key

    return hmac.new(
        secret.encode("utf-8"),
        otp.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _create_otp(
    db: Session,
    user_id: int,
    purpose: str,
) -> tuple[AuthOtp, str]:

    now = _utcnow()

    otp_expiry_minutes = getattr(
        settings,
        "otp_expiry_minutes",
        10,
    )

    otp = _generate_otp()

    record = AuthOtp(
        user_id=user_id,
        purpose=purpose,
        otp_hash=_otp_hash(otp),
        expires_at=now + timedelta(
            minutes=otp_expiry_minutes
        ),
        attempts=0,
        verified_at=None,
        used_at=None,
        created_at=now,
    )

    db.add(record)
    db.flush()

    return record, otp


def _invalidate_unused_otps(
    db: Session,
    user_id: int,
    purpose: str,
) -> None:

    records = db.scalars(
        select(AuthOtp).where(
            AuthOtp.user_id == user_id,
            AuthOtp.purpose == purpose,
            AuthOtp.used_at.is_(None),
        )
    ).all()

    now = _utcnow()

    for record in records:
        record.used_at = now


def _latest_otp(
    db: Session,
    user_id: int,
    purpose: str,
) -> AuthOtp | None:

    return db.scalar(
        select(AuthOtp)
        .where(
            AuthOtp.user_id == user_id,
            AuthOtp.purpose == purpose,
            AuthOtp.used_at.is_(None),
        )
        .order_by(AuthOtp.created_at.desc())
    )


def _verify_otp(
    db: Session,
    user_id: int,
    purpose: str,
    otp: str,
    require_verified: bool = False,
) -> AuthOtp:

    record = _latest_otp(
        db=db,
        user_id=user_id,
        purpose=purpose,
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP not found or has already been used.",
        )

    now = _utcnow()

    if record.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new OTP.",
        )

    max_attempts = getattr(
        settings,
        "otp_max_attempts",
        5,
    )

    if record.attempts >= max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum OTP verification attempts exceeded. Please request a new OTP.",
        )

    if (
        require_verified
        and record.verified_at is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has not been verified.",
        )

    if not hmac.compare_digest(
        record.otp_hash,
        _otp_hash(otp),
    ):
        record.attempts += 1
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP.",
        )

    return record


def _check_resend_cooldown(
    record: AuthOtp | None,
) -> None:

    if record is None:
        return

    resend_seconds = getattr(
        settings,
        "otp_resend_seconds",
        60,
    )

    elapsed = (
        _utcnow() - record.created_at
    ).total_seconds()

    if elapsed < resend_seconds:
        remaining = max(
            1,
            int(resend_seconds - elapsed),
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Please wait {remaining} seconds "
                "before requesting another OTP."
            ),
        )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    """Create a new account and send an email verification OTP."""

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

    # Public sign-up never grants operational privileges. An administrator
    # can promote a verified account through the user management API.
    requested_role_name = "VIEWER"

    assigned_role = db.scalar(
        select(Role).where(
            Role.name == requested_role_name
        )
    )

    if assigned_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Requested role '{requested_role_name}' has not been initialized."
            ),
        )

    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(
            request.password
        ),
        is_active=False,
        role_id=assigned_role.id,
    )

    db.add(user)
    db.flush()

    otp_record, otp = _create_otp(
        db=db,
        user_id=user.id,
        purpose=EMAIL_VERIFICATION,
    )

    try:
        send_email_verification_otp(
            recipient=user.email,
            username=user.username,
            otp=otp,
        )
    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Account could not be created because "
                "the verification email could not be sent."
            ),
        )

    db.commit()

    return RegisterResponse(
        message="Account created successfully. A 6-digit verification OTP has been sent to your email.",
        email=user.email,
        verification_required=True,
    )


@router.post(
    "/verify-email",
    response_model=MessageResponse,
)
def verify_email(
    request: EmailOtpRequest,
    db: Session = Depends(get_db),
):
    """Verify a newly registered user's email address."""

    user = db.scalar(
        select(User).where(
            User.email == request.email
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    # Check if user already verified their email
    already_verified = db.scalar(
        select(AuthOtp).where(
            AuthOtp.user_id == user.id,
            AuthOtp.purpose == EMAIL_VERIFICATION,
            AuthOtp.verified_at.is_not(None),
        )
    )
    if already_verified is not None:
        return MessageResponse(
            message="Email is already verified. You can now sign in.",
        )

    record = _verify_otp(
        db=db,
        user_id=user.id,
        purpose=EMAIL_VERIFICATION,
        otp=request.otp,
    )

    now = _utcnow()

    record.verified_at = now
    record.used_at = now

    user.is_active = True
    db.commit()

    return MessageResponse(
        message=(
            "Email verified successfully. "
            "You can now sign in."
        ),
    )


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
)
def resend_verification(
    request: ResendVerificationRequest,
    db: Session = Depends(get_db),
):
    """Resend the email verification OTP."""

    user = db.scalar(
        select(User).where(
            User.email == request.email
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    if user.is_active:
        return MessageResponse(
            message="Email is already verified.",
        )

    previous = _latest_otp(
        db=db,
        user_id=user.id,
        purpose=EMAIL_VERIFICATION,
    )

    _check_resend_cooldown(previous)

    _invalidate_unused_otps(
        db=db,
        user_id=user.id,
        purpose=EMAIL_VERIFICATION,
    )

    _, otp = _create_otp(
        db=db,
        user_id=user.id,
        purpose=EMAIL_VERIFICATION,
    )

    try:
        send_email_verification_otp(
            recipient_email=user.email,
            otp=otp,
        )

        db.commit()

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification email could not be sent.",
        )

    return MessageResponse(
        message=(
            "A new verification OTP has been "
            "sent to your email."
        ),
    )


@router.post(
    "/login",
    response_model=LoginResponse,
)
def login(
    request: Request,
    credentials: LoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticate a user; require email OTP when 2FA is enabled."""
    client_ip = (
        request.client.host
        if request.client
        else None
    )

    user_agent = request.headers.get("user-agent")

    user = db.scalar(
        select(User).where(
            (User.username == credentials.username_or_email)
            | (User.email == credentials.username_or_email)
        )
    )

    if user is None:
        audit = LoginAuditLog(
            user_id=None,
            ip_address=client_ip,
            success=False,
            user_agent=user_agent,
        )
        db.add(audit)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password.",
        )

    if not verify_password(
        credentials.password,
        user.hashed_password,
    ):
        audit = LoginAuditLog(
            user_id=user.id,
            ip_address=client_ip,
            success=False,
            user_agent=user_agent,
        )
        db.add(audit)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password.",
        )

    if not user.is_active:
        pending_verification = _latest_otp(
            db=db,
            user_id=user.id,
            purpose=EMAIL_VERIFICATION,
        )

        audit = LoginAuditLog(
            user_id=user.id,
            ip_address=client_ip,
            success=False,
            user_agent=user_agent,
        )
        db.add(audit)
        db.commit()

        if pending_verification is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email with the 6-digit OTP before signing in.",
            )

        if user.role.name == "SOC_ANALYST":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your SOC Analyst account is pending administrator approval. Please wait for an administrator to authorize your account.",
            )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Please contact an administrator.",
        )

    # Password is valid. If 2FA is enabled, do not issue an access token yet.
    if user.two_factor_enabled:
        previous = _latest_otp(
            db=db,
            user_id=user.id,
            purpose=TWO_FACTOR_LOGIN,
        )
        _check_resend_cooldown(previous)

        _invalidate_unused_otps(
            db=db,
            user_id=user.id,
            purpose=TWO_FACTOR_LOGIN,
        )

        _, otp = _create_otp(
            db=db,
            user_id=user.id,
            purpose=TWO_FACTOR_LOGIN,
        )

        challenge_payload = {
            "sub": str(user.id),
            "purpose": TWO_FACTOR_CHALLENGE,
            "exp": utc_now() + timedelta(
                minutes=getattr(settings, "otp_expiry_minutes", 10)
            ),
        }

        challenge_token = jwt.encode(
            challenge_payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        try:
            send_two_factor_otp(
                recipient=user.email,
                username=user.username,
                otp=otp,
                purpose="Login",
            )
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login verification email could not be sent.",
            )

        return LoginResponse(
            requires_two_factor=True,
            otp_sent=True,
            challenge_token=challenge_token,
            message="A verification code has been sent to your registered email address.",
        )

    login_time = _utcnow()

    user.last_login_at = login_time
    user.last_login_ip = client_ip

    audit = LoginAuditLog(
        user_id=user.id,
        login_at=login_time,
        ip_address=client_ip,
        success=True,
        user_agent=user_agent,
    )

    db.add(audit)

    session = _create_auth_session(
        db=db,
        user_id=user.id,
        client_ip=client_ip,
        user_agent=user_agent,
    )

    db.commit()
    db.refresh(user)

    role = user.role.name

    access_token = create_access_token(
        subject=str(user.id),
        role=role,
        session_id=session.session_id,
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=role,
            is_active=user.is_active,
        ),
        requires_two_factor=False,
        otp_sent=False,
    )



def _get_current_session_id(request: Request) -> str:
    """Extract the session ID from the currently authenticated JWT."""

    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_id = payload.get("sid")

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication session.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return str(session_id)


@router.get("/sessions")
def get_active_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return active authentication sessions for the current user."""

    current_session_id = _get_current_session_id(request)
    now = _utcnow()

    sessions = db.scalars(
        select(AuthSession)
        .where(
            AuthSession.user_id == current_user.id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .order_by(AuthSession.last_seen_at.desc())
    ).all()

    return [
        {
            "session_id": session.session_id,
            "created_at": session.created_at,
            "last_seen_at": session.last_seen_at,
            "expires_at": session.expires_at,
            "ip_address": session.ip_address,
            "user_agent": session.user_agent,
            "is_current": session.session_id == current_session_id,
        }
        for session in sessions
    ]


@router.post("/sessions/{session_id}/revoke")
def revoke_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke one other active authentication session."""

    current_session_id = _get_current_session_id(request)

    if session_id == current_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke the current session. Use sign out instead.",
        )

    session = db.scalar(
        select(AuthSession).where(
            AuthSession.session_id == session_id,
            AuthSession.user_id == current_user.id,
        )
    )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authentication session not found.",
        )

    if session.revoked_at is not None:
        return {
            "message": "Session has already been signed out.",
            "session_id": session.session_id,
        }

    session.revoked_at = _utcnow()
    db.commit()

    return {
        "message": "Session signed out successfully.",
        "session_id": session.session_id,
    }


@router.post("/sessions/revoke-all")
def revoke_all_other_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke all other active sessions while keeping the current one active."""

    current_session_id = _get_current_session_id(request)
    now = _utcnow()

    sessions = db.scalars(
        select(AuthSession).where(
            AuthSession.user_id == current_user.id,
            AuthSession.session_id != current_session_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
    ).all()

    revoked_count = 0

    for session in sessions:
        session.revoked_at = now
        revoked_count += 1

    db.commit()

    return {
        "message": "All other sessions have been signed out.",
        "revoked_count": revoked_count,
    }

@router.get("/login-activity")
def get_login_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
):
    """Return recent successful and failed sign-in activity for the current user."""
    records = db.scalars(
        select(LoginAuditLog)
        .where(LoginAuditLog.user_id == current_user.id)
        .order_by(LoginAuditLog.login_at.desc())
        .limit(limit)
    ).all()

    return [
        {
            "id": record.id,
            "login_at": record.login_at,
            "ip_address": record.ip_address,
            "success": bool(record.success),
            "user_agent": record.user_agent,
        }
        for record in records
    ]


@router.get("/2fa/status")
def get_two_factor_status(
    current_user: User = Depends(get_current_user),
):
    """Return the current two-step verification state for the signed-in user."""
    email = current_user.email
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        masked_local = (local[:1] or "*") + "***"
    else:
        masked_local = local[0] + "***" + local[-1]
    return {
        "enabled": bool(current_user.two_factor_enabled),
        "email": f"{masked_local}@{domain}" if domain else email,
    }


@router.post(
    "/2fa/request",
    response_model=MessageResponse,
)
def request_two_factor_otp(
    request: TwoFactorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Request an email OTP to enable or disable two-step verification."""
    action = request.action.lower()

    if action == "enable" and current_user.two_factor_enabled:
        return MessageResponse(message="Two-step verification is already enabled.")

    if action == "disable" and not current_user.two_factor_enabled:
        return MessageResponse(message="Two-step verification is already disabled.")

    previous = _latest_otp(
        db=db,
        user_id=current_user.id,
        purpose=TWO_FACTOR_SETUP,
    )
    _check_resend_cooldown(previous)

    _invalidate_unused_otps(
        db=db,
        user_id=current_user.id,
        purpose=TWO_FACTOR_SETUP,
    )

    _, otp = _create_otp(
        db=db,
        user_id=current_user.id,
        purpose=TWO_FACTOR_SETUP,
    )

    try:
        send_two_factor_otp(
            recipient=current_user.email,
            username=current_user.username,
            otp=otp,
            purpose="Two-step verification",
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Two-step verification email could not be sent.",
        )

    action_text = "enable" if action == "enable" else "disable"

    return MessageResponse(
        message=(
            f"A verification code has been sent to your registered email "
            f"to {action_text} two-step verification."
        )
    )


@router.post(
    "/2fa/verify",
    response_model=MessageResponse,
)
def verify_two_factor_setup(
    request: TwoFactorVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify the setup OTP and change the user's 2FA setting."""
    action = request.action.lower()

    if action == "enable" and current_user.two_factor_enabled:
        return MessageResponse(message="Two-step verification is already enabled.")

    if action == "disable" and not current_user.two_factor_enabled:
        return MessageResponse(message="Two-step verification is already disabled.")

    record = _verify_otp(
        db=db,
        user_id=current_user.id,
        purpose=TWO_FACTOR_SETUP,
        otp=request.otp,
    )

    now = _utcnow()
    record.verified_at = now
    record.used_at = now

    current_user.two_factor_enabled = action == "enable"

    db.commit()

    state = "enabled" if current_user.two_factor_enabled else "disabled"

    return MessageResponse(
        message=f"Two-step verification {state} successfully."
    )


@router.post(
    "/2fa/login",
    response_model=TokenResponse,
)
def verify_two_factor_login(
    request: Request,
    credentials: TwoFactorLoginRequest,
    db: Session = Depends(get_db),
):
    """Verify a login OTP and issue the normal access token."""
    try:
        payload = jwt.decode(
            credentials.challenge_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired two-step verification challenge.",
        )

    if payload.get("purpose") != TWO_FACTOR_CHALLENGE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid two-step verification challenge.",
        )

    user_id = payload.get("sub")

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid two-step verification challenge.",
        )

    user = db.scalar(
        select(User).where(User.id == user_id)
    )

    if user is None or not user.is_active or not user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Two-step verification is unavailable for this account.",
        )

    record = _verify_otp(
        db=db,
        user_id=user.id,
        purpose=TWO_FACTOR_LOGIN,
        otp=credentials.otp,
    )

    now = _utcnow()
    record.verified_at = now
    record.used_at = now

    client_ip = (
        request.client.host
        if request.client
        else None
    )
    user_agent = request.headers.get("user-agent")

    login_time = now
    user.last_login_at = login_time
    user.last_login_ip = client_ip

    audit = LoginAuditLog(
        user_id=user.id,
        login_at=login_time,
        ip_address=client_ip,
        success=True,
        user_agent=user_agent,
    )

    db.add(audit)

    _invalidate_unused_otps(
        db=db,
        user_id=user.id,
        purpose=TWO_FACTOR_LOGIN,
    )

    session = _create_auth_session(
        db=db,
        user_id=user.id,
        client_ip=client_ip,
        user_agent=user_agent,
    )

    db.commit()
    db.refresh(user)

    role = user.role.name

    access_token = create_access_token(
        subject=str(user.id),
        role=role,
        session_id=session.session_id,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=role,
            is_active=user.is_active,
        ),
    )


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
)
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Request a password reset OTP.

    The response is intentionally generic so the endpoint
    does not reveal whether an email address exists.
    """

    user = db.scalar(
        select(User).where(
            User.email == request.email
        )
    )

    generic_message = (
        "If an active account exists for this email, "
        "a password reset OTP has been sent."
    )

    if user is None or not user.is_active:
        return MessageResponse(
            message=generic_message,
        )

    previous = _latest_otp(
        db=db,
        user_id=user.id,
        purpose=PASSWORD_RESET,
    )

    _check_resend_cooldown(previous)

    _invalidate_unused_otps(
        db=db,
        user_id=user.id,
        purpose=PASSWORD_RESET,
    )

    _, otp = _create_otp(
        db=db,
        user_id=user.id,
        purpose=PASSWORD_RESET,
    )

    try:
        send_password_reset_otp(
            recipient=user.email,
            username=user.username,
            otp=otp,
        )

        db.commit()

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset email could not be sent.",
        )

    return MessageResponse(
        message=generic_message,
    )


@router.post(
    "/verify-reset-otp",
    response_model=MessageResponse,
)
def verify_reset_otp(
    request: VerifyResetOtpRequest,
    db: Session = Depends(get_db),
):
    """Verify a password-reset OTP without consuming it."""

    user = db.scalar(
        select(User).where(
            User.email == request.email
        )
    )

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset OTP.",
        )

    record = _verify_otp(
        db=db,
        user_id=user.id,
        purpose=PASSWORD_RESET,
        otp=request.otp,
    )

    record.verified_at = _utcnow()

    db.commit()

    return MessageResponse(
        message=(
            "OTP verified successfully. "
            "You can now create a new password."
        ),
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
)
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Reset the user's password using a verified OTP."""

    user = db.scalar(
        select(User).where(
            User.email == request.email
        )
    )

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset OTP.",
        )

    record = _verify_otp(
        db=db,
        user_id=user.id,
        purpose=PASSWORD_RESET,
        otp=request.otp,
        require_verified=True,
    )

    user.hashed_password = hash_password(
        request.new_password
    )

    for session in db.scalars(select(AuthSession).where(
        AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)
    )):
        session.revoked_at = _utcnow()

    record.used_at = _utcnow()

    _invalidate_unused_otps(
        db=db,
        user_id=user.id,
        purpose=PASSWORD_RESET,
    )

    db.commit()

    return MessageResponse(
        message=(
            "Password reset successfully. "
            "You can now sign in with your new password."
        ),
    )


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change the authenticated user's password with strict complexity enforcement."""
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match.",
        )

    if request.current_password == request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from your current password.",
        )

    is_valid, error = validate_password_complexity(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error or "Password does not meet complexity requirements.",
        )

    current_user.hashed_password = hash_password(request.new_password)
    for session in db.scalars(select(AuthSession).where(
        AuthSession.user_id == current_user.id, AuthSession.revoked_at.is_(None)
    )):
        session.revoked_at = _utcnow()
    db.commit()

    return MessageResponse(
        message="Password changed successfully.",
    )

@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session_id = _get_current_session_id(request)
    session = db.scalar(select(AuthSession).where(AuthSession.session_id == session_id, AuthSession.user_id == current_user.id))
    if session:
        session.revoked_at = _utcnow()
        db.commit()
    return MessageResponse(message="Signed out successfully.")


@router.get("/features")
def authentication_features():
    email_available = bool(settings.smtp_host and settings.smtp_username and settings.smtp_password and settings.smtp_from_email)
    return {"registration": email_available, "password_recovery": email_available, "two_factor": email_available}
