import json
import os

questions = [
    # =========================================================================
    # PART 1: WEBSITE & UI FEATURES (Questions 1 - 100)
    # =========================================================================
    {
        "id": "WEB-001",
        "category": "Website - Architecture",
        "question": "What frontend framework and library stack is used in the ZUKA platform?",
        "expected_answer": "React 18 with TypeScript, Vite build tool, and Lucide React icons.",
        "key_facts": ["React", "TypeScript", "Vite"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-002",
        "category": "Website - Navigation",
        "question": "What routing library and navigation structure does the ZUKA frontend use?",
        "expected_answer": "React Router v6 with role-guarded route trees using ProtectedRoute.",
        "key_facts": ["React Router", "ProtectedRoute"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-003",
        "category": "Website - Dashboard",
        "question": "What is the primary route and function of the Dashboard page?",
        "expected_answer": "The Dashboard at /dashboard provides a high-level executive overview of security posture and operational health.",
        "key_facts": ["/dashboard", "executive overview", "security posture"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-004",
        "category": "Website - Dashboard",
        "question": "What key metric cards are displayed on the Dashboard?",
        "expected_answer": "Total Alerts, Open Alerts, Critical Threats, Total Incidents, and Active Investigations.",
        "key_facts": ["Total Alerts", "Open Alerts", "Critical Threats", "Incidents", "Investigations"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-005",
        "category": "Website - Dashboard",
        "question": "Which network protocols are broken down in the Dashboard protocol traffic charts?",
        "expected_answer": "TCP, UDP, and ICMP protocols.",
        "key_facts": ["TCP", "UDP", "ICMP"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-006",
        "category": "Website - Network Monitor",
        "question": "What is the URL route of the Network Monitor page and what does it display?",
        "expected_answer": "The Network Monitor at /network-monitor displays live packet telemetry streams, protocol breakdowns, port distribution graphs, and traffic anomalies.",
        "key_facts": ["/network-monitor", "packet telemetry", "protocol"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-007",
        "category": "Website - Network Monitor",
        "question": "Can the Network Monitor display simulated attack traffic from a replay worker?",
        "expected_answer": "Yes, it supports replay runner feeds for simulated attack verification.",
        "key_facts": ["replay runner", "simulated attack"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-008",
        "category": "Website - Alert Center",
        "question": "What is the URL route for the Alert Center?",
        "expected_answer": "The Alert Center is located at /alerts.",
        "key_facts": ["/alerts"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-009",
        "category": "Website - Alert Center",
        "question": "What happens when an analyst clicks on an alert row in the Alert Center?",
        "expected_answer": "Clicking an alert row opens the forensic inspection drawer displaying localized TreeSHAP feature importance values and telemetry details.",
        "key_facts": ["inspection drawer", "TreeSHAP", "telemetry"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-010",
        "category": "Website - Alert Center",
        "question": "What information does the TreeSHAP drawer in Alert Center show?",
        "expected_answer": "It shows localized Shapley attribution values explaining which flow features influenced the model classification.",
        "key_facts": ["Shapley", "flow features", "classification"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-011",
        "category": "Website - Alert Center",
        "question": "What are the possible status values of an alert in ZUKA?",
        "expected_answer": "OPEN, ACKNOWLEDGED, RESOLVED, and FALSE_POSITIVE.",
        "key_facts": ["OPEN", "ACKNOWLEDGED", "RESOLVED", "FALSE_POSITIVE"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-012",
        "category": "Website - Alert Center",
        "question": "Why is acknowledging an alert necessary in ZUKA?",
        "expected_answer": "Acknowledging an alert confirms analyst triage and is a prerequisite that unlocks the linked incident for active investigation.",
        "key_facts": ["prerequisite", "unlocks", "investigation"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-013",
        "category": "Website - Incident Center",
        "question": "What is the URL route for Incident Management?",
        "expected_answer": "The Incident Management interface is at /incidents.",
        "key_facts": ["/incidents"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-014",
        "category": "Website - Incident Center",
        "question": "What are the 5 sequential lifecycle statuses of an incident?",
        "expected_answer": "OPEN, ACKNOWLEDGED, INVESTIGATING, RESOLVED, and CLOSED.",
        "key_facts": ["OPEN", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED", "CLOSED"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-015",
        "category": "Website - Incident Center",
        "question": "What prerequisite must be satisfied before an analyst can click 'Resolve Incident'?",
        "expected_answer": "The linked forensic investigation must be marked COMPLETED with an analyst conclusion.",
        "key_facts": ["investigation", "COMPLETED", "conclusion"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-016",
        "category": "Website - Incident Center",
        "question": "What are the priority ratings for incidents in ZUKA?",
        "expected_answer": "P1 (Urgent / Business Critical), P2 (High), P3 (Medium), and P4 (Low).",
        "key_facts": ["P1", "P2", "P3", "P4"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-017",
        "category": "Website - Incident Center",
        "question": "What are the four escalation levels available for incidents?",
        "expected_answer": "Level 0 (normal triage), Level 1 (senior analyst), Level 2 (team lead / network engineering), and Level 3 (critical management / IR team).",
        "key_facts": ["Level 0", "Level 1", "Level 2", "Level 3"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-018",
        "category": "Website - Defense Department",
        "question": "What is the route and function of the Defense Department page?",
        "expected_answer": "The Defense Department at /defense performs threat triage, network telemetry identification, and tactical containment countermeasures.",
        "key_facts": ["/defense", "containment countermeasures", "telemetry"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-019",
        "category": "Website - Defense Department",
        "question": "Which incidents are displayed in the Defense Department?",
        "expected_answer": "Exclusively active open investigations with status IN_PROGRESS, NOT_STARTED, or ON_HOLD.",
        "key_facts": ["open investigations", "IN_PROGRESS"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-020",
        "category": "Website - Defense Department",
        "question": "What are the six containment countermeasures available in Defense Department?",
        "expected_answer": "VLAN_QUARANTINE, BLOCK_IP, CREDENTIAL_ROTATION, RATE_LIMIT, FIRMWARE_PATCH, and CUSTOM.",
        "key_facts": ["VLAN_QUARANTINE", "BLOCK_IP", "CREDENTIAL_ROTATION", "RATE_LIMIT", "FIRMWARE_PATCH"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-021",
        "category": "Website - Defense Department",
        "question": "What happens when an analyst applies a defense countermeasure in Defense Department?",
        "expected_answer": "The defense directive is automatically formatted and appended into the linked investigation dossier notes and logged in analyst_actions.",
        "key_facts": ["appended", "investigation", "analyst_actions"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-022",
        "category": "Website - Investigation Department",
        "question": "What is the URL route of the Investigation Department?",
        "expected_answer": "The Investigation Department is located at /investigation.",
        "key_facts": ["/investigation"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-023",
        "category": "Website - Investigation Department",
        "question": "What prefix identifier is used for investigation dossiers?",
        "expected_answer": "Dossiers use the prefix INV- (e.g. INV-1042).",
        "key_facts": ["INV-"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-024",
        "category": "Website - Investigation Department",
        "question": "What statuses can an investigation have?",
        "expected_answer": "NOT_STARTED, IN_PROGRESS, and COMPLETED.",
        "key_facts": ["NOT_STARTED", "IN_PROGRESS", "COMPLETED"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-025",
        "category": "Website - Investigation Department",
        "question": "How are analyst notes tracked and logged in the Investigation Department?",
        "expected_answer": "Every note is permanently logged in the analyst_actions ledger with an Action ID, timestamp, and analyst username.",
        "key_facts": ["analyst_actions", "Action ID", "timestamp"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-026",
        "category": "Website - Investigation Department",
        "question": "What must an analyst author before completing an investigation?",
        "expected_answer": "The analyst must author the manual Analyst Conclusion finding.",
        "key_facts": ["Analyst Conclusion"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-027",
        "category": "Website - Reports",
        "question": "What is the route for generating reports?",
        "expected_answer": "Reports are located at /reports.",
        "key_facts": ["/reports"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-028",
        "category": "Website - Reports",
        "question": "What report types can be generated in the Reports module?",
        "expected_answer": "Incident Report, Alert Report, Executive Summary, and Detection XAI Report.",
        "key_facts": ["Incident Report", "Alert Report", "Executive Summary", "Detection XAI Report"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-029",
        "category": "Website - Reports",
        "question": "How does the print feature work on the Reports page?",
        "expected_answer": "It uses isolated @media print CSS to print clean white A4/letter document sheets without website sidebars, headers, or assistant artifacts.",
        "key_facts": ["@media print", "clean", "sidebar"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-030",
        "category": "Website - Database Center",
        "question": "What is the route and access permission for the Database Center?",
        "expected_answer": "Database Center is at /databases and is restricted to ADMIN users only.",
        "key_facts": ["/databases", "ADMIN"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-031",
        "category": "Website - Database Center",
        "question": "Why was the manual '+ Log Analyst Action' button removed from the Database Center?",
        "expected_answer": "To preserve a pure observation ledger where all analyst actions are automatically and authentically recorded by system events.",
        "key_facts": ["pure observation", "authentic", "automatically"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-032",
        "category": "Website - Database Center",
        "question": "What core tables are monitored in the Database Center?",
        "expected_answer": "alerts, incidents, investigations, analyst_actions, and audit_logs.",
        "key_facts": ["alerts", "incidents", "investigations", "analyst_actions", "audit_logs"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-033",
        "category": "Website - User Management",
        "question": "What is the route for User Management and what permissions are required?",
        "expected_answer": "User Management is at /users and requires the ADMIN role.",
        "key_facts": ["/users", "ADMIN"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-034",
        "category": "Website - User Management",
        "question": "Why are newly registered users unable to log in immediately?",
        "expected_answer": "Newly registered accounts have is_active=False by default and require explicit administrative approval.",
        "key_facts": ["is_active=False", "approval", "ADMIN"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-035",
        "category": "Website - User Management",
        "question": "Can an administrator delete or deactivate their own account?",
        "expected_answer": "No, administrators are strictly prohibited from deleting or deactivating their own active account to prevent lockout.",
        "key_facts": ["prohibited", "own account", "lockout"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-036",
        "category": "Website - User Management",
        "question": "What safety mechanism is enforced when an admin deletes a user via the assistant?",
        "expected_answer": "A cryptographically random confirmation token is issued with a strict 60-second time-to-live requiring explicit confirmation.",
        "key_facts": ["confirmation token", "60-second", "TTL"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-037",
        "category": "Website - Settings",
        "question": "What capabilities are available on the Settings page at /settings?",
        "expected_answer": "Updating email, changing password, inspecting active browser sessions, revoking sessions, and configuring TOTP 2FA.",
        "key_facts": ["/settings", "password", "sessions", "2FA"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-038",
        "category": "Website - Settings",
        "question": "How does Two-Factor Authentication (2FA) work in ZUKA Settings?",
        "expected_answer": "It uses Time-based One-Time Password (TOTP) requiring a 6-digit authenticator code upon login.",
        "key_facts": ["TOTP", "6-digit", "authenticator"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-039",
        "category": "Website - Roles",
        "question": "What are the three RBAC roles in ZUKA?",
        "expected_answer": "ADMIN, SOC_ANALYST, and VIEWER.",
        "key_facts": ["ADMIN", "SOC_ANALYST", "VIEWER"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-040",
        "category": "Website - Roles",
        "question": "What can a VIEWER role access on the ZUKA website?",
        "expected_answer": "Read-only access to the Dashboard and Network Monitor.",
        "key_facts": ["read-only", "Dashboard", "Network Monitor"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-041",
        "category": "Website - Roles",
        "question": "What operations are restricted from a SOC_ANALYST role?",
        "expected_answer": "SOC_ANALYSTs cannot access Database Center schema admin and cannot approve or delete user accounts.",
        "key_facts": ["Database Center", "approve", "delete users"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-042",
        "category": "Website - Assistant UI",
        "question": "Where is the Ask Zuka assistant button located on the website?",
        "expected_answer": "It is a floating button located at the bottom-right corner of the layout labeled 'Ask Zuka' with a green indicator.",
        "key_facts": ["bottom-right", "Ask Zuka", "floating"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-043",
        "category": "Website - Assistant UI",
        "question": "Where does the assistant store conversation history in the browser?",
        "expected_answer": "In browser sessionStorage under the key 'zuka_chat_history'.",
        "key_facts": ["sessionStorage", "zuka_chat_history"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-044",
        "category": "Website - Assistant UI",
        "question": "What cards can the assistant render in chat?",
        "expected_answer": "Action cards, Info cards, Confirmation cards, and Error cards.",
        "key_facts": ["Action", "Info", "Confirmation", "Error"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-045",
        "category": "Website - Backend API",
        "question": "What web framework and Python version power the backend API?",
        "expected_answer": "FastAPI powered by Python 3.13.",
        "key_facts": ["FastAPI", "Python 3.13"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-046",
        "category": "Website - Backend API",
        "question": "What ASGI server runs the FastAPI backend application?",
        "expected_answer": "Uvicorn running on http://127.0.0.1:8000.",
        "key_facts": ["Uvicorn", "8000"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-047",
        "category": "Website - Backend API",
        "question": "What endpoint does the frontend assistant call for sending chat messages?",
        "expected_answer": "POST /api/zuka-assistant/chat.",
        "key_facts": ["POST /api/zuka-assistant/chat"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-048",
        "category": "Website - Backend API",
        "question": "What endpoint checks the backend system health?",
        "expected_answer": "GET /api/health.",
        "key_facts": ["GET /api/health"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-049",
        "category": "Website - Backend API",
        "question": "What database ORM and migration tool are used in the backend?",
        "expected_answer": "SQLAlchemy 2.0 ORM with Alembic migration management.",
        "key_facts": ["SQLAlchemy", "Alembic"],
        "is_out_of_domain": False
    },
    {
        "id": "WEB-050",
        "category": "Website - Backend API",
        "question": "How are user passwords protected in the backend database?",
        "expected_answer": "Hashed using passlib with bcrypt or Argon2 hashing and cryptographic salts.",
        "key_facts": ["passlib", "bcrypt", "Argon2"],
        "is_out_of_domain": False
    },
]

# Generate more in-domain questions (Web, Operations, Project Architecture) up to 250 in-domain, and 50 out-of-domain
print(f"Base questions defined: {len(questions)}")
