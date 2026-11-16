import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

from backend.app.database.session import SessionLocal
from backend.app.models import User, AuthSession
from backend.app.security.jwt import create_access_token, create_session_id
from backend.app.core.config import settings
from sqlalchemy import select

BASE_URL = "http://127.0.0.1:8000"

def get_auth_token_for_user(username: str, role_override: str = None) -> tuple[str, str]:
    db = SessionLocal()
    user = db.scalar(select(User).where(User.username == username))
    if not user:
        user = db.scalar(select(User).order_by(User.id.asc()).limit(1))
    if not user:
        db.close()
        raise ValueError(f"No users found in database")
    
    user_id = user.id
    role_name = role_override or (user.role.name if hasattr(user.role, 'name') else str(user.role))
    session_id = create_session_id()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    auth_session = AuthSession(
        session_id=session_id,
        user_id=user_id,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(minutes=settings.access_token_expire_minutes),
        ip_address="127.0.0.1",
        user_agent="Automated Test Suite",
    )
    db.add(auth_session)
    db.commit()
    db.close()
    
    token = create_access_token(
        subject=str(user_id),
        role=role_name,
        session_id=session_id
    )
    return token, role_name

from backend.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def request(method: str, path: str, token: str = None, data: dict = None) -> tuple[int, any]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = client.request(method, path, headers=headers, json=data)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, resp.content

def run_tests():
    print("=" * 70)
    print(" ZUKA SOC COMPREHENSIVE OPERATIONS & INTEGRITY TEST SUITE")
    print("=" * 70)
    
    results = []
    def log_test(module: str, test_name: str, passed: bool, details: str = ""):
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str:4}] {module:18} | {test_name:35} | {details}")
        results.append({"module": module, "name": test_name, "passed": passed, "details": details})

    # 0. SERVER HEALTH
    c, _ = request("GET", "/api/health")
    log_test("System", "FastAPI Server Health", c == 200, "FastAPI application is responsive and healthy")

    # 1. SETUP SESSIONS
    try:
        db_init = SessionLocal()
        for uname, rid, email in [("arif", 2, "arif@zuka.ai"), ("arif123", 3, "viewer@zuka.ai")]:
            u = db_init.scalar(select(User).where(User.username == uname))
            if not u:
                u = User(username=uname, email=email, hashed_password="pw", is_active=True, role_id=rid)
                db_init.add(u)
        db_init.commit()
        db_init.close()

        admin_token, admin_role = get_auth_token_for_user("karthik")
        analyst_token, analyst_role = get_auth_token_for_user("arif")
        viewer_token, viewer_role = get_auth_token_for_user("arif123")
        log_test("Auth", "Generate Sessions (Admin/Analyst/Viewer)", True, f"Admin: {admin_role}, Analyst: {analyst_role}, Viewer: {viewer_role}")
    except Exception as e:
        log_test("Auth", "Generate Sessions", False, str(e))
        return

    # 2. DASHBOARD / SUMMARY & NETWORK STATS
    code, dash_data = request("GET", "/api/dashboard/summary", admin_token)
    log_test("Dashboard", "GET /api/dashboard/summary", code == 200, f"Active alerts: {dash_data.get('alerts', {}).get('active') if isinstance(dash_data, dict) else 'N/A'}")

    code, data = request("GET", "/api/network/stats", admin_token)
    log_test("Dashboard", "GET /api/network/stats", code == 200, f"Status: {code}")

    # 3. ALERTS CENTER
    code, data = request("GET", "/api/alerts?limit=5", admin_token)
    sample_alert_id = None
    if code == 200 and isinstance(data, dict):
        items = data.get("alerts") or data.get("items") or []
        if items:
            sample_alert_id = items[0].get("alert_id")
        log_test("Alert Center", "GET /api/alerts (List)", True, f"Found {len(items)} alerts, sample: {sample_alert_id}")
    else:
        log_test("Alert Center", "GET /api/alerts (List)", False, f"Status: {code}")

    if sample_alert_id:
        code, data = request("GET", f"/api/alerts/{sample_alert_id}", admin_token)
        log_test("Alert Center", f"GET /api/alerts/{sample_alert_id}", code == 200, f"Class: {data.get('predicted_class') if isinstance(data, dict) else 'N/A'}")

    # 4. INCIDENT MANAGEMENT
    code, data = request("GET", "/api/incidents?limit=5", admin_token)
    sample_inc_id = None
    if code == 200 and isinstance(data, dict):
        items = data.get("items") or data.get("incidents") or []
        if items:
            sample_inc_id = items[0].get("incident_id")
        log_test("Incidents", "GET /api/incidents (List)", True, f"Found {len(items)} incidents, sample: {sample_inc_id}")
    else:
        log_test("Incidents", "GET /api/incidents (List)", False, f"Status: {code}")

    if sample_inc_id:
        code, data = request("GET", f"/api/incidents/{sample_inc_id}", admin_token)
        log_test("Incidents", f"GET /api/incidents/{sample_inc_id}", code == 200, f"Title: {data.get('title') if isinstance(data, dict) else 'N/A'}")

    # 5. INVESTIGATION DEPARTMENT
    code, data = request("GET", "/api/investigations?limit=5", admin_token)
    sample_inv_id = None
    if code == 200 and isinstance(data, dict):
        items = data.get("items") or data.get("investigations") or []
        if items:
            sample_inv_id = items[0].get("investigation_id")
        log_test("Investigation", "GET /api/investigations (List)", True, f"Found {len(items)} investigations, sample: {sample_inv_id}")
    else:
        log_test("Investigation", "GET /api/investigations (List)", False, f"Status: {code}")

    # 6. REPORTS CENTER & DATABASE PERSISTENCE
    code, data = request("GET", "/api/reports", admin_token)
    report_items = []
    if code == 200 and isinstance(data, dict):
        report_items = data.get("items", [])
        log_test("Reports Center", "GET /api/reports (Stored DB Reports)", True, f"Found {len(report_items)} stored reports in DB")
    else:
        log_test("Reports Center", "GET /api/reports (Stored DB Reports)", False, f"Status: {code}")

    # Check each stored report's data endpoint
    for rep in report_items:
        r_id = rep.get("report_id")
        code, r_data = request("GET", f"/api/reports/{r_id}", admin_token)
        log_test("Reports Center", f"GET /api/reports/{r_id}", code == 200, f"Content keys: {list(r_data.get('content', {}).keys()) if isinstance(r_data, dict) else 'N/A'}")

    # PDF Download test
    code, pdf_bytes = request("GET", "/api/reports/summary/pdf", admin_token)
    log_test("Reports Center", "GET /api/reports/summary/pdf", code == 200 and len(pdf_bytes) > 1000, f"PDF bytes: {len(pdf_bytes) if isinstance(pdf_bytes, bytes) else 0}")

    if sample_inc_id:
        code, pdf_bytes = request("GET", f"/api/reports/incidents/{sample_inc_id}/pdf", admin_token)
        log_test("Reports Center", f"GET /api/reports/incidents/{sample_inc_id}/pdf", code == 200 and len(pdf_bytes) > 1000, f"PDF bytes: {len(pdf_bytes) if isinstance(pdf_bytes, bytes) else 0}")

    # 7. DEFENSE DEPARTMENT
    code, def_data = request("GET", "/api/defense/open-investigations", admin_token)
    def_items = def_data.get("investigations", []) if isinstance(def_data, dict) else []
    log_test("Defense", "GET /api/defense/open-investigations", code == 200, f"Found {len(def_items)} investigations for defense")

    # 8. AI COPILOT & ZUKA OPERATIONS ASSISTANT
    # Q1: Reports count question
    code, data = request("POST", "/api/zuka-assistant/chat", admin_token, {
        "message": "how many reports are in the database?"
    })
    ans = data.get("reply", "") if isinstance(data, dict) else ""
    log_test("AI Copilot", "Question: Report Count in Database", code == 200 and "report" in ans.lower(), f"Answer: {ans[:65]}...")

    # Q2: Show reports
    code, data = request("POST", "/api/zuka-assistant/chat", admin_token, {
        "message": "show me reports"
    })
    ans = data.get("reply", "") if isinstance(data, dict) else ""
    log_test("AI Copilot", "Question: Show Me Reports", code == 200 and ("REP-" in ans or "report" in ans.lower()), f"Contains reports: {'Yes' if ('REP-' in ans or 'report' in ans.lower()) else 'No'}")

    # Q3: Show alerts
    code, data = request("POST", "/api/zuka-assistant/chat", admin_token, {
        "message": "show alerts"
    })
    ans = data.get("reply", "") if isinstance(data, dict) else ""
    log_test("AI Copilot", "Question: Show Alerts", code == 200 and ("alert" in ans.lower() or "zuka" in ans.lower()), f"Contains alert info: {'Yes' if ('alert' in ans.lower() or 'zuka' in ans.lower()) else 'No'}")

    # Q4: Context suggestions
    code, sugg_data = request("GET", "/api/zuka-assistant/suggestions", admin_token)
    suggs = sugg_data if isinstance(sugg_data, list) else (sugg_data.get("suggestions", []) if isinstance(sugg_data, dict) else [])
    log_test("AI Copilot", "GET /api/zuka-assistant/suggestions", code == 200 and len(suggs) > 0, f"Found {len(suggs)} suggestions: {suggs}")

    # Q5: Assistant V2 CLI dispatch
    code, v2_data = request("POST", "/api/assistant-v2/chat", admin_token, {"message": "dashboard stats"})
    v2_type = v2_data.get("type") if isinstance(v2_data, dict) else "N/A"
    log_test("AI Copilot", "POST /api/assistant-v2/chat", code == 200, f"Status: {code}, V2 Type: {v2_type}")

    # 8. DATASET REPLAY (Continuous Loop)
    code, data = request("POST", "/api/replay/next", admin_token, {"row_index": 0, "include_xai": True})
    processed = isinstance(data, dict) and data.get("processed") == True
    pred_cls = data.get("result", {}).get("predicted_class") if isinstance(data, dict) else "N/A"
    log_test("Replay Loop", "POST /api/replay/next (Row 0)", code == 200 and processed, f"Predicted: {pred_cls}")

    # 9. INCIDENT STATS
    code, inc_stats = request("GET", "/api/incidents/stats", admin_token)
    log_test("Incidents", "GET /api/incidents/stats", code == 200, f"Active: {inc_stats.get('active') if isinstance(inc_stats, dict) else 'N/A'}")

    # 10. DATABASE CENTER (Overview, Schema & RBAC Verification)
    code_admin_ov, ov_data = request("GET", "/api/database/overview", admin_token)
    code_admin_tb, tb_data = request("GET", "/api/database/tables", admin_token)
    code_schema, schema_data = request("GET", "/api/database/table/alerts/schema", admin_token)
    code_viewer, _ = request("GET", "/api/database/overview", viewer_token)
    code_analyst, _ = request("GET", "/api/database/overview", analyst_token)
    log_test("Database Center", "GET /api/database/overview (Admin)", code_admin_ov == 200, f"Total records: {ov_data.get('total_records') if isinstance(ov_data, dict) else 'N/A'}")
    log_test("Database Center", "GET /api/database/tables (Admin)", code_admin_tb == 200, f"Tables count: {tb_data.get('count') if isinstance(tb_data, dict) else 'N/A'}")
    log_test("Database Center", "GET /api/database/table/alerts/schema", code_schema == 200, f"Columns: {schema_data.get('column_count') if isinstance(schema_data, dict) else 'N/A'}")
    log_test("Database Center", "Viewer Access Blocked (RBAC)", code_viewer == 403, f"Viewer status: {code_viewer} (Expected 403)")
    log_test("Database Center", "Analyst Access Blocked (RBAC)", code_analyst == 403, f"Analyst status: {code_analyst} (Expected 403)")

    # 11. USER MANAGEMENT (RBAC Verification)
    code_admin, _ = request("GET", "/api/admin/users", admin_token)
    code_viewer, _ = request("GET", "/api/admin/users", viewer_token)
    log_test("User Management", "Admin Access Granted", code_admin == 200, f"Admin status: {code_admin}")
    log_test("User Management", "Viewer Access Blocked (RBAC)", code_viewer == 403, f"Viewer status: {code_viewer} (Expected 403)")

    print("=" * 70)
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = sum(1 for r in results if not r["passed"])
    print(f" TEST RUN COMPLETE: {passed_count} PASSED, {failed_count} FAILED (TOTAL {len(results)})")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
