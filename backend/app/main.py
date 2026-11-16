from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request
from backend.app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes.admin import router as admin_router
from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.network import router as network_router
from backend.app.api.routes.database_center import (
    router as database_center_router,
)
from backend.app.api.routes.detection import (
    router as detection_router,
)
from backend.app.api.routes.alerts import router as alerts_router
from backend.app.api.routes.incidents import router as incidents_router
from backend.app.api.routes.investigations import router as investigations_router
from backend.app.api.routes.analyst_actions import (
    router as analyst_actions_router,
)
from backend.app.api.routes.audit_history import (
    router as audit_history_router,
)
from backend.app.api.routes.replay import router as replay_router
from backend.app.replay.replay_worker import replay_worker
from backend.app.api.routes.dashboard import (
    router as dashboard_router,
)
from backend.app.api.routes.reports import router as reports_router
from backend.app.api.routes.push import router as push_router
from backend.app.assistant_v2.router import router as assistant_v2_router
from backend.app.zuka_assistant.router import router as zuka_assistant_router
from backend.app.api.routes.defense import router as defense_router
from backend.app.models import User
from backend.app.security.dependencies import get_current_user



# ============================================================================
# APPLICATION
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    if getattr(settings, "enable_in_process_replay", True):
        replay_worker.start()
    try:
        yield
    finally:
        if getattr(settings, "enable_in_process_replay", True):
            replay_worker.stop()


app = FastAPI(
    title="ZUKA SOC API",
    description="ZUKA Security Operations Center Backend",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# SECURITY HEADERS MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ============================================================================
# CORS
# ============================================================================

allowed_origins = [
    origin.strip()
    for origin in getattr(settings, "cors_origins", "").split(",")
    if origin.strip()
] or ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ROUTERS
# ============================================================================

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(dashboard_router)
app.include_router(network_router)
app.include_router(database_center_router)
app.include_router(detection_router)
app.include_router(alerts_router) 
app.include_router(incidents_router)
app.include_router(investigations_router)
app.include_router(analyst_actions_router)
app.include_router(audit_history_router)
app.include_router(replay_router)
app.include_router(assistant_v2_router)
app.include_router(zuka_assistant_router)
app.include_router(reports_router)
app.include_router(push_router)
app.include_router(defense_router)

# ============================================================================
# SYSTEM HEALTH
# ============================================================================

@app.get(
    "/api/health",
    tags=["System"],
)
def health_check():
    return {
        "status": "ok",
        "service": "ZUKA SOC API",
        "version": "1.0.0",
    }


# ============================================================================
# CURRENT USER
# ============================================================================

@app.get(
    "/api/auth/me",
    tags=["Authentication"],
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    role = current_user.role

    if hasattr(role, "name"):
        role_name = role.name
    else:
        role_name = str(role)

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": role_name,
        "is_active": current_user.is_active,
    }
