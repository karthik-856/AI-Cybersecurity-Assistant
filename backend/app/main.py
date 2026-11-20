from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from starlette.concurrency import run_in_threadpool
from sqlalchemy import text
from backend.app.database.session import engine
from backend.app.security.auth_rate_limit import PUBLIC_AUTH_LIMITS, allow_auth_request
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
    docs_url=None if settings.app_env == "production" else "/docs",
    redoc_url=None if settings.app_env == "production" else "/redoc",
    openapi_url=None if settings.app_env == "production" else "/openapi.json",
)


# ============================================================================
# SECURITY HEADERS MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    if request.method == "POST" and settings.auth_rate_limit_enabled and request.url.path in PUBLIC_AUTH_LIMITS:
        try:
            allowed, retry = await run_in_threadpool(allow_auth_request, request.client.host if request.client else "unknown", request.url.path)
        except Exception:
            return JSONResponse({"detail": "Sign-in is temporarily unavailable. Please try again shortly."}, status_code=503)
        if not allowed:
            return JSONResponse({"detail": "Too many attempts. Please wait before trying again."}, status_code=429, headers={"Retry-After": str(retry)})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
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


@app.get("/api/ready", tags=["System"])
def readiness_check():
    root = Path(__file__).resolve().parents[2]
    model_dir = root / "models" / "zuka_unified_xgboost"
    if not any((model_dir / name).exists() for name in ("model.ubj", "model.json", "model.json.gz")):
        raise HTTPException(status_code=503, detail="Detection is temporarily unavailable.")
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="The service is temporarily unavailable.")
    return {"status": "ready"}


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


# Serve the built dashboard from the same origin as its API. Unknown API URLs
# remain JSON 404s; deep links to application screens receive the SPA entry.
frontend_root = Path(settings.frontend_dist_dir).resolve()
if (frontend_root / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_root / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def serve_dashboard(path: str):
    if path == "api" or path.startswith("api/") or path in ("docs", "redoc", "openapi.json"):
        raise HTTPException(status_code=404, detail="Not found.")
    target = (frontend_root / path).resolve()
    if not target.is_relative_to(frontend_root):
        raise HTTPException(status_code=404, detail="Not found.")
    if target.is_file():
        return FileResponse(target, headers={"Cache-Control": "no-store"} if target.name == "index.html" else None)
    entry = frontend_root / "index.html"
    if not entry.exists():
        raise HTTPException(status_code=404, detail="Not found.")
    return FileResponse(entry, headers={"Cache-Control": "no-store"})
