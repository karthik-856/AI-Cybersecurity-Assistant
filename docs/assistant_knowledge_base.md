# ZUKA SOC Platform: Master Knowledge Base & Assistant Operational Reference

> **Document Type:** Master Operational Knowledge Base & Assistant Reference Manual  
> **Target Audience:** AI Operations Assistant (Zuka), SOC Analysts, Tier 1/2/3 Operators, Platform Administrators  
> **Version:** 2.1.0  
> **Platform Name:** ZUKA SOC — AI-Based Cybersecurity Assistant for Smart Devices  

---

## 1. System Identity & Mission Overview

### 1.1 Purpose & Mission
The **ZUKA SOC Platform** is an enterprise-grade Security Operations Center (SOC) platform engineered to detect, diagnose, investigate, and triage network attacks directed against smart devices and Internet of Things (IoT) infrastructure.

Smart devices (e.g., IP cameras, smart plugs, smart hubs, industrial sensors) introduce critical vulnerabilities because they:
1. Feature resource-constrained hardware unable to run traditional host-based antivirus or Endpoint Detection and Response (EDR) agents.
2. Frequently ship with insecure defaults (factory passwords like `admin/admin`, open Telnet/UPnP ports).
3. Rarely receive automated firmware updates from vendors.
4. Are primary targets for botnet recruitment (e.g., Mirai) to execute distributed volumetric attacks.

ZUKA solves this by operating as an out-of-band network flow analysis and SOC management engine. It inspects live packet flows, runs machine learning classification and Explainable AI (XAI), automates incident correlation, generates compliance reports, and embeds an interactive AI Assistant (**Zuka**) to streamline operations and case triage.

### 1.2 Assistant Identity & Personality
- **Name:** Zuka (ZUKA Operations Assistant)
- **Role:** Autonomous Tier-1/Tier-2 Cybersecurity Analyst and Operations Co-pilot.
- **Tone:** Professional, precise, factual, security-conscious, and action-oriented.
- **Zero-Hallucination Policy:** Never invent packet numbers, IP addresses, alert IDs, incident IDs, or device statuses. All metrics, record counts, and timestamps must strictly derive from live database records or official platform knowledge.
- **Safety Boundary:** Strictly refuses to create malicious payloads, write exploit scripts, or provide instructions for unauthorized attacks. All recommendations are purely defensive, non-destructive, and educational.

---

## 2. Platform Architecture & Technology Stack

```
   ┌─────────────────────────────────────────────────────────────────┐
   │                       ZUKA SOC WEB FRONTEND                     │
   │           React 18 + TypeScript + Vite + Lucide Icons           │
   │       Context-Aware Chat Widget + Interactive Action Cards      │
   └────────────────────────────────┬────────────────────────────────┘
                                    │ HTTP / REST / Bearer Token
                                    ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │                       FASTAPI BACKEND API                       │
   │               Python 3.13 + SQLAlchemy 2.0 ORM                 │
   │  ┌──────────────────────────┐    ┌───────────────────────────┐  │
   │  │   Assistant v2 Router    │    │   Zuka Assistant Router   │  │
   │  │  (Sub-5ms Intent Engine) │    │   (Ollama Agent Tools)    │  │
   │  └────────────┬─────────────┘    └─────────────┬─────────────┘  │
   │               │                                │                │
   │  ┌────────────┴────────────────────────────────┴─────────────┐  │
   │  │ Core Modules: Alerts, Incidents, Investigations, Reports, │  │
   │  │  Network Telemetry, User RBAC & Immutable Audit History  │  │
   │  └────────────────────────────┬──────────────────────────────┘  │
   └───────────────────────────────┼─────────────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  POSTGRESQL DB   │     │  XGBOOST + SHAP  │     │  LOCAL OLLAMA    │
│  Live Tables &   │     │  Multiclass Model│     │  qwen2.5:3b /    │
│  Analyst Ledgers │     │  TreeExplainer   │     │  llama3.2:1b     │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

### 2.1 Backend Stack
- **Framework:** FastAPI (Python 3.13) with asynchronous request handling.
- **ORM & Migrations:** SQLAlchemy with Alembic migration management.
- **Database:** PostgreSQL (production relational store for alerts, incidents, investigations, telemetry, analyst actions, and audit logs).
- **Authentication:** OAuth2 password flow with JWT (HMAC-SHA256) access tokens, refresh tokens, and optional TOTP 2FA.
- **Push Notifications:** Web Push via VAPID keys for real-time browser alerts.

### 2.2 Frontend Stack
- **Framework:** React 18 with TypeScript.
- **Build Tool:** Vite with hot-module reloading.
- **Navigation:** React Router v6 with role-guarded route trees (`ProtectedRoute`).
- **Icons & Styling:** Lucide React icons, scoped CSS modules, responsive CSS grid/flexbox layouts.
- **State & Caching:** Persistent browser `sessionStorage` for assistant conversations and `localStorage` for authentication tokens.

### 2.3 Machine Learning & Explainable AI Stack
- **Model:** Unified XGBoost Multiclass Decision Trees (`xgboost`).
- **Explainability:** TreeSHAP (`shap.TreeExplainer`) for per-packet feature importance calculation.
- **Training Corpus:** 2,561,658 network flow records trained across 13 distinct network traffic categories.

### 2.4 Assistant AI Engine
- **Local LLM Engine:** Ollama instance running `qwen2.5:3b` (or `llama3.2:1b`) at `http://localhost:11434`.
- **Low Temperature:** `0.2` for deterministic, grounded reasoning.
- **On-Premises Privacy:** 100% localhost inference. Zero customer telemetry or packet flows ever leave the internal environment.
- **Hybrid Fallback:** Deterministic regex rule-based engine operates in sub-5ms even if Ollama is unavailable.

---

## 3. Role-Based Access Control (RBAC) & User Management

ZUKA enforces strict tripartite role segmentation:

| Role | Permissions & Operational Access | Restricted Operations |
|---|---|---|
| **`ADMIN`** | Full platform access: All operational modules, system telemetry, database center, user approvals, user deactivation, user deletion, configuration. | Cannot delete or deactivate own active administrator account. |
| **`SOC_ANALYST`** | Operational access: Dashboard, Network Monitor, Alert Center, Incident Management, Investigations, PDF Reports, and Assistant. | Cannot access Database Center schema admin, cannot approve or delete user accounts. |
| **`VIEWER`** | Read-only access: Dashboard and Network Monitor. | Cannot acknowledge alerts, create/modify incidents, write notes, change settings, or manage users. |

### User Registration & Approval Workflow
1. A new operator submits the registration form at `/register`.
2. The user account is saved in the database with status `is_active = False` (Pending Approval).
3. The platform generates an administrative approval token and alerts the administrator.
4. An `ADMIN` navigates to **User Management** (`/users`) or uses the Assistant command `approve user <ID>` to authorize the account.
5. Once approved, `is_active` becomes `True`, enabling the user to authenticate at `/login`.

---

## 4. Platform Modules & Operations Guide

### 4.1 Dashboard (`/dashboard`)
- **Primary Function:** High-level executive overview of security posture and operational health.
- **Key Metrics Displayed:**
  - Total Alerts, Open Alerts, Critical Threats, Total Incidents, Active Investigations.
  - 24-hour attack trend charts, severity distributions (Critical, High, Medium, Low).
  - Protocol traffic breakdowns (TCP, UDP, ICMP).
  - Quick shortcuts to recent critical alerts and unassigned incidents.

### 4.2 Network Monitor (`/network-monitor`)
- **Primary Function:** Real-time packet telemetry visualization and traffic inspection.
- **Key Capabilities:**
  - Live packet stream visualizer displaying flows captured by ingestion workers.
  - Interactive protocol charts, port distribution graphs, and flow rate monitors.
  - Identifies traffic anomalies, bandwidth spikes, and potential reconnaissance probes.
  - Supports replay runner feeds for simulated attack verification.

### 4.3 Alert Center (`/alerts`)
- **Primary Function:** Ingests, categorizes, and provides deep forensic inspection for automated ML detections.
- **Alert Attributes:**
  - `alert_id` (e.g., `ALT-1082` / database primary key `id`).
  - `predicted_class`: Attack category detected by the XGBoost classifier.
  - `confidence`: Confidence score (0.0% to 100.0%).
  - `severity`: Automatically computed as `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, or `INFO`.
  - `status`: `OPEN`, `ACKNOWLEDGED`, `RESOLVED`, or `FALSE_POSITIVE`.
  - `source_ip` & `destination_ip`: Attacker and target IP endpoints.
  - `source_port` & `destination_port`: Service communication ports.
  - `protocol`: Network layer protocol (TCP, UDP, ICMP).
  - `detected_at`: ISO UTC timestamp.
- **Explainable AI (TreeSHAP) Drawer:**
  - Clicking any alert row opens the forensic inspection drawer.
  - Displays localized SHAP values showing exactly which flow metrics (e.g., extreme `flow_packet_rate` or zero `dst_bytes`) influenced the model's classification.
- **Acknowledgement Action:**
  - Analysts review the alert and click **Acknowledge** (or ask Zuka: `acknowledge alert <ID>`).
  - *Crucial Rule:* An alert **must be acknowledged** before its linked incident can be investigated.

### 4.4 Incident Management (`/incidents`)
- **Primary Function:** Central case management for verified security threats requiring human intervention.
- **Incident Lifecycle Statuses:**
  1. `OPEN`: Newly triggered case awaiting analyst triage.
  2. `ACKNOWLEDGED`: Linked alert has been verified and confirmed.
  3. `INVESTIGATING`: Active forensic dossier created; analyst assigned.
  4. `RESOLVED`: Threat mitigated, root cause identified, resolution summary logged (pre-filled by the analyst conclusion by default, which can be overridden by the analyst).
  5. `CLOSED`: Post-mortem complete, archived permanently.
- **Escalation Levels:**
  - `Level 0`: Normal triage.
  - `Level 1`: Priority analysis by Senior SOC Analyst.
  - `Level 2`: Team Lead & Network Engineering escalation.
  - `Level 3`: Critical Management Escalation & Incident Response Team mobilization.
- **Priority Ratings:** `P1` (Urgent / Business Critical), `P2` (High), `P3` (Medium), `P4` (Low).
- **Prerequisite Enforcement:** "Resolve Incident" cannot be executed until the linked forensic investigation is marked `COMPLETED` with an analyst conclusion.

### 4.5 Defense Department (`/defense`)
- **Primary Function:** Dedicated threat triage, network detection telemetry identification, and tactical containment countermeasures.
- **Scope:** Exclusively displays active **open investigations** (`status: IN_PROGRESS`, `NOT_STARTED`, `ON_HOLD`).
- **Network Detection Identification:** Correlates the linked alert and incident to identify:
  - Attack Classification (with AI confidence percentage).
  - Attacker Host (Source IP, Port, Protocol).
  - Targeted Asset (Destination IP, Destination Port).
  - Automated Threat Diagnosis explaining the exact attack mechanism (volumetric flood, port sweep, brute force, Mirai C2 beaconing, etc.).
- **Containment Countermeasures:**
  - `VLAN_QUARANTINE`: Quarantine targeted endpoint or VLAN to isolate lateral pivoting while preserving forensic link.
  - `BLOCK_IP`: Deploy ingress firewall drop rules against the hostile attacker IP address.
  - `CREDENTIAL_ROTATION`: Invalidate active sessions, terminate tokens, and queue administrative credential rotation.
  - `RATE_LIMIT`: Apply packet filtering and traffic shaping on the affected port to prevent service exhaustion.
  - `FIRMWARE_PATCH`: Schedule vulnerability remediation and disable exposed daemon service.
  - `CUSTOM`: Bespoke analyst containment strategy.
- **Automatic Dossier Synchronization:** Applying a defense action automatically formats and appends the containment directive into the **Investigation Department** dossier's analyst notes and logs an immutable audit event in `analyst_actions` (`DEFEND_INCIDENT`).

### 4.6 Investigation Department (`/investigation`)
- **Primary Function:** Dedicated digital forensic workspace for packet evidence analysis and case documentation.
- **Dossier Properties:** Unique identifier (`INV-...`), status (`NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`), start timestamp, completion timestamp, analyst notes, manual conclusion.
- **Analyst Notes:**
  - Displays all investigation notes, including defense directives synchronized from the Defense Department.
  - Analysts document additional forensic steps and telemetry findings.
  - Every note is immutably stamped with the analyst username, timestamp, and an Action Ledger ID.
- **Manual Case Conclusion:**
  - The SOC analyst manually authors the final evidence-based finding and verdict.
  - Saving the conclusion and clicking "Complete Investigation" transitions status to `COMPLETED` (guaranteed clean completion without legacy field blocking popups).
  - Marking the investigation `COMPLETED` unlocks the "Resolve Incident" action in Incident Management.

### 4.7 Reports & PDF Export (`/reports`)
- **Primary Function:** Generates executive and compliance-ready PDF documentation.
- **Print Optimization:** Supports 1-click clean paper sheet printing (`window.print()`). Uses isolated `@media print` CSS so only the white document sheet prints across multi-page paper without website sidebars, top headers, or assistant artifacts.
- **Supported Report Types:**
  - **Incident Report:** Multi-page summary containing incident timeline, linked alerts, forensic notes, escalation history, and analyst sign-offs.
  - **Alert Report:** Detailed packet telemetry and feature attribution report for a single alert.
  - **Executive Summary:** Platform-wide metrics, attack distributions, and SOC response time KPIs.
  - **Detection XAI Report:** TreeSHAP visualizations and algorithmic breakdown of model classifications.

### 4.8 Database Center (`/databases`)
- **Primary Function:** Live system health, relational database monitoring, and immutable compliance audit tracking (Admin only).
- **Pure Observation Ledger:** Manual "+ Log Analyst Action" button removed so all analyst actions across the platform (Alert acknowledge, Incident status updates, Defense actions, Investigation completion, Incident resolution, Incident closure) are automatically and authentically recorded.
- **Core Tables & Ledgers:**
  - `alerts`: Raw threat detection records and ML predictions.
  - `incidents`: Case files, severities, priority ratings, and resolution records.
  - `investigations`: Forensic dossiers and analyst notes.
  - `analyst_actions`: Immutable ledger storing human-authorized operational actions (`action_id`, `action_type`, `user_id`, `result`, `timestamp`).
  - `audit_logs`: Security audit log recording logins, session revocations, password changes, and permission adjustments.

### 4.9 User Management (`/users`)
- **Primary Function:** Administrative console for managing operators and access permissions (Admin only).
- **Capabilities:**
  - List all registered users and filter by role or approval state.
  - Approve pending analyst registrations (`approve user <ID>`).
  - Activate or deactivate analyst accounts (`activate user <ID>` / `deactivate user <ID>`).
  - Delete user accounts with two-step safety confirmation (`delete user <ID>`).

### 4.10 Settings & Two-Factor Authentication (`/settings`)
- **Primary Function:** Profile management, session controls, and security hardening.
- **Capabilities:**
  - Update user email and change account password.
  - View active browser sessions and remotely revoke unauthorized devices.
  - Configure Time-based One-Time Password (TOTP) Two-Factor Authentication (2FA) for heightened login protection.

---

## 5. Machine Learning, IoT Detection & Explainable AI (XAI)

### 5.1 Unified XGBoost Model Architecture
- **Model File:** `models/zuka_unified_xgboost/model.json`
- **Algorithm:** Multiclass Gradient Boosted Decision Trees (XGBoost).
- **Training Corpus:** 2,561,658 network flow records with balanced class weighting.
- **Performance Benchmarks:**
  - **Overall Multiclass Accuracy:** ~93.0%
  - **DDoS Detection F1-Score:** 99.2%
  - **DoS Detection F1-Score:** 92.6%
  - **Benign Traffic F1-Score:** 96.3%

### 5.2 The 13 Supported Traffic Classes
1. `BENIGN`: Normal, legitimate smart device operations (e.g., periodic cloud telemetry, NTP time sync, standard HTTP queries).
2. `DOS` (Denial of Service): Volumetric or resource-exhaustion traffic originating from a single source host aiming to crash the device.
3. `DDOS` (Distributed Denial of Service): Coordinated multi-source flood targeting smart hubs or IoT gateways.
4. `PORT_SCAN`: Systematic probing of TCP/UDP ports on a target IP (e.g., scanning ports 21, 22, 23, 80, 443, 554, 8080) to discover open listeners.
5. `BRUTE_FORCE`: Automated credential guessing against IoT management protocols (Telnet port 23, SSH port 22, HTTP admin forms).
6. `BOTNET`: Mirai-style recruitment, command execution, or Command & Control (C2) beaconing.
7. `BACKDOOR`: Unauthorized reverse shell or covert listener established on a compromised device.
8. `RECONNAISSANCE`: Active host discovery and subnet mapping.
9. `EXPLOIT`: Known vulnerability payload directed against smart device firmware or exposed daemons.
10. `FUZZING`: Malformed, high-entropy packet payloads engineered to trigger buffer overflows in embedded network stacks.
11. `INFILTRATION`: Lateral movement from a compromised smart peripheral into the internal enterprise network.
12. `MALWARE`: Malicious binary download or communication payload targeting smart device architectures (ARM, MIPS).
13. `OTHER_ATTACK`: Anomalous malicious traffic patterns that deviate from baseline but do not fit a classic single category.

### 5.3 The 14 Common Network Flow Features
The ZUKA feature extraction pipeline transforms raw packet streams into 14 statistical indicators:
1. `duration_sec`: Flow duration in seconds.
2. `src_packets`: Total packets transmitted by source.
3. `dst_packets`: Total packets transmitted by destination.
4. `src_bytes`: Total payload and header bytes sent by source.
5. `dst_bytes`: Total payload and header bytes sent by destination.
6. `flow_packet_rate`: Total packets per second in the flow.
7. `src_packet_rate`: Source transmission rate in packets per second.
8. `dst_packet_rate`: Destination transmission rate in packets per second.
9. `src_byte_rate`: Source data transfer rate in bytes per second.
10. `dst_byte_rate`: Destination data transfer rate in bytes per second.
11. `src_packet_size_mean`: Average size of packets sent by source.
12. `dst_packet_size_mean`: Average size of packets sent by destination.
13. `src_iat_mean_sec`: Mean inter-arrival time between source packets in seconds.
14. `dst_iat_mean_sec`: Mean inter-arrival time between destination packets in seconds.

### 5.4 Explainable AI (TreeSHAP)
- **Engine:** `shap.TreeExplainer` applied directly to the trained XGBoost decision trees.
- **Function:** Solves the black-box problem by calculating exact Shapley attribution values for each of the 14 features on any individual prediction.
- **Interpretation:**
  - Positive SHAP value: Pushes the prediction toward the attack class (e.g., abnormally small `src_iat_mean_sec` indicating flood pacing).
  - Negative SHAP value: Pushes the prediction toward benign (e.g., normal balanced `dst_bytes` with valid ACK pacing).
- **Analyst Benefit:** Allows analysts to verify whether a detection is a true positive or a benign burst (such as high-definition IP camera video streaming).

---

## 6. Standard Operating Procedures (SOPs) & Unified SOC Workflow

### The Unified 6-Stage SOC Incident Response Pipeline
```
[1. Alert Center]       ──> Acknowledge Alert (Alert & Incident marked ACKNOWLEDGED)
       │
[2. Incident Center]    ──> Start Investigation (Incident -> INVESTIGATING, Dossier created)
       │
[3. Defense Dept]       ──> Identify Threat Telemetry & Apply Containment (Note appended)
       │
[4. Investigation Dept] ──> Review Telemetry/Directives, Write Conclusion & Complete (COMPLETED)
       │
[5. Resolve Incident]   ──> Enabled only after Investigation COMPLETED (adopts Analyst Conclusion)
       │
[6. Close Incident]     ──> Final Review & Case Archival (CLOSED)
```

### SOP-01: Acknowledging an Alert (Alert Center `/alerts`)
1. Navigate to **Alert Center** (`/alerts`).
2. Click on the target alert row to open the forensic inspection drawer.
3. Review the attack classification, model confidence, source/destination IPs, and SHAP feature contributions.
4. Click **Acknowledge Alert** (or send command: `acknowledge alert <ID>`).
5. Status changes from `OPEN` to `ACKNOWLEDGED`. The correlated incident status is synchronized to `ACKNOWLEDGED` and unlocked for investigation.

### SOP-02: Initiating Case Investigation (Incident Management `/incidents`)
1. Navigate to **Incident Management** (`/incidents`) and select the acknowledged incident.
2. Click **Start Investigation** (or send command: `investigate incident <ID>`).
3. The platform transitions the incident to `INVESTIGATING` and automatically provisions an active forensic dossier in `IN_PROGRESS`.
4. The open case immediately becomes visible in both the **Investigation Department** and **Defense Department**.

### SOP-03: Triaging & Defending the Incident (Defense Department `/defense`)
1. Navigate to **Defense Department** (`/defense`). The department displays only active open investigations.
2. Select the case to view the **Network Detection Telemetry**:
   - Attack class and ML confidence score.
   - Hostile origin IP & source port.
   - Targeted device IP & target port.
   - Automated rule-based Threat Diagnosis explaining what occurred in network traffic.
3. Select an authoritative containment countermeasure (`VLAN_QUARANTINE`, `BLOCK_IP`, `CREDENTIAL_ROTATION`, `RATE_LIMIT`, `FIRMWARE_PATCH`, or `CUSTOM`).
4. Enter the containment rationale and formulate the defense directive note.
5. Click **Apply Defense & Append Note to Investigation**:
   - The platform applies the containment directive.
   - The note is automatically appended into the linked investigation dossier's analyst notes.
   - An immutable record is created in the `analyst_actions` ledger (`DEFEND_INCIDENT`).

### SOP-04: Authoring Conclusion & Completing Investigation (Investigation Department `/investigation`)
1. Navigate to **Investigation Department** (`/investigation`) and select the case.
2. Review the consolidated evidence timeline, raw flow telemetry, and the defense directives appended from the Defense Department.
3. In the **Analyst Record** section, the SOC analyst manually types the authoritative **Analyst Conclusion**.
4. Click **Save Conclusion** and then click **Complete Investigation**.
5. Investigation status transitions to `COMPLETED` cleanly without any blocking popup errors.

### SOP-05: Resolving the Incident (Incident Management `/incidents`)
1. Return to **Incident Management** (`/incidents`).
2. **Prerequisite Enforcement:** The "Resolve Incident" action is strictly gated. If the investigation is incomplete, clicking the button displays an informative notice directing the analyst to complete the investigation.
3. Once the investigation is marked `COMPLETED`, click **Resolve Incident**.
4. The resolution modal opens with the resolution summary automatically pre-filled from the analyst's manual conclusion.
5. Confirm resolution: incident status transitions to `RESOLVED` and `resolved_at` is stamped.

### SOP-06: Closing an Incident (Incident Management `/incidents`)
1. In Incident Management, select the `RESOLVED` incident.
2. Review the final resolution summary and post-incident verification.
3. Click **Close Incident** (or send command: `close incident <ID>`).
4. Status transitions to `CLOSED` and the case is archived permanently.

### SOP-07: Generating & Printing Reports (Reports `/reports`)
1. Navigate to **Reports** (`/reports`).
2. Generate compliance documentation or select a stored report.
3. Click **Print**: uses isolated print CSS to print directly to clean A4/letter document sheets without any website dark shell, sidebar, or button artifacts.

---

## 7. Assistant Architecture, Command Palette & Natural Language Reference

### 7.1 Dual-Engine Architecture
The Zuka Assistant operates via a two-tier pipeline:
1. **Primary Engine (Deterministic Rule Parser):** Evaluates user input against precompiled regular expressions in sub-5ms with zero token cost.
2. **Secondary Engine (Local Ollama LLM):** If the rule parser does not find a match and LLM mode is active, the query is dispatched to Ollama (`qwen2.5:3b`) using function calling against grounded database tools.

### 7.2 Safety Confirmation System (Human-in-the-Loop)
- Destructive actions (such as `delete user <id>`) **require explicit human confirmation**.
- When triggered, the backend generates a cryptographically random confirmation token (`secrets.token_hex(16)`) with a strict **60-second time-to-live (TTL)**.
- The assistant presents a red warning confirmation card with two buttons: **Confirm** and **Cancel**.
- The deletion is executed *only* when the user clicks Confirm or types `confirm delete user <id>`.

### 7.3 Assistant UI Response Primitives
The assistant delivers structured, interactive responses:
- **ActionCard:** Rich card with titles, badges (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `SUCCESS`, `INFO`), labeled attribute fields, and action buttons.
- **ActionTable:** Formatted data table with sortable columns and pagination.
- **ActionButton:** Interactive buttons that trigger actions:
  - `execute_command`: Sends a command back to the assistant automatically.
  - `navigate`: Routes the analyst directly to the relevant platform page (e.g., `/alerts`, `/incidents`).
  - `prompt`: Pre-fills the chat input for the analyst.
- **Quick Chips:** One-click recommendation chips beneath each message for rapid follow-ups.

### 7.4 Complete Command Reference

#### Alert Commands
| Command Syntax | Alternative Phrasings | Description |
|---|---|---|
| `show alert <id>` | `alert <id>`, `inspect alert <id>`, `view alert #12` | Inspect detailed alert telemetry, ports, confidence, and status. |
| `list alerts` | `show alerts`, `recent alerts`, `all alerts` | Display the 8 most recent threat detections in a table. |
| `list critical alerts` | `critical alerts`, `show critical alerts` | Filter alerts where severity is `CRITICAL`. |
| `list pending alerts` | `open alerts`, `unresolved alerts` | Filter alerts where status is `OPEN`. |
| `acknowledge alert <id>` | `ack alert <id>`, `acknowledge alert #5` | Mark alert status as `ACKNOWLEDGED`. Unlocks incident investigation. |
| `resolve alert <id>` | `close alert <id>`, `fix alert <id>` | Mark alert status as `RESOLVED`. |
| `dismiss alert <id>` | `mark false positive <id>`, `fp alert <id>` | Flag alert as `FALSE_POSITIVE`. |
| `escalate alert <id>` | `promote alert <id>`, `convert alert <id> to incident` | Automatically generate a security incident from an alert. |

#### Incident Commands
| Command Syntax | Alternative Phrasings | Description |
|---|---|---|
| `show incident <id>` | `incident <id>`, `view incident #3` | Inspect incident details, severity, priority, owner, and notes. |
| `list incidents` | `show incidents`, `all incidents`, `active incidents` | List all active security incidents in an action table. |
| `list open incidents` | `open incidents`, `unresolved incidents` | Filter incidents currently in `OPEN` status. |
| `investigate incident <id>`| `start investigation on incident <id>` | Transition incident to `INVESTIGATING` and open dossier. |
| `resolve incident <id>` | `close incident <id>`, `fix incident <id>` | Transition incident to `RESOLVED` (requires summary). |
| `create incident` | `new incident`, `open incident titled "..."` | Create a new incident ticket directly from the assistant. |
| `summarize incident <id>` | `give summary for incident <id>` | Generates a complete forensic summary of the case and linked alert. |

#### User Management Commands (Admin Only)
| Command Syntax | Alternative Phrasings | Description |
|---|---|---|
| `list users` | `show users`, `all users`, `accounts` | Display all registered user accounts. |
| `list analysts` | `show analysts`, `soc analysts` | Filter accounts by `SOC_ANALYST` role. |
| `list pending users` | `pending analysts`, `pending approvals` | List accounts awaiting administrative approval. |
| `show user <id>` | `user <id>`, `view user admin` | Inspect user profile, email, role, and last login date. |
| `approve user <id>` | `authorize user <id>`, `approve analyst <id>` | Authorize a newly registered account and set `is_active=True`. |
| `deactivate user <id>` | `disable user <id>`, `suspend user <id>` | Revoke user login access immediately. |
| `activate user <id>` | `enable user <id>`, `unblock user <id>` | Re-enable login access for a user. |
| `delete user <id>` | `remove user <id>`, `drop user <id>` | Triggers safety confirmation prompt to permanently delete user. |

#### System Telemetry & Workflow Commands
| Command Syntax | Alternative Phrasings | Description |
|---|---|---|
| `system status` | `health`, `server status`, `ping`, `soc health` | Displays live database health, open alerts, critical count, and server status. |
| `dashboard stats` | `overview`, `summary`, `metrics`, `kpi` | High-level summary of active platform KPIs. |
| `network monitor` | `show network`, `traffic summary` | Summarizes current packet telemetry and flow rates. |
| `help` | `commands`, `?`, `usage`, `what can you do` | Displays categorized command cards and quick examples. |

---

## 8. Comprehensive Frequently Asked Questions (FAQs)

### 8.1 General & Platform FAQs

#### Q1: What is the ZUKA SOC Platform?
**A:** ZUKA is an AI-driven Security Operations Center platform designed specifically to detect, diagnose, investigate, and triage network attacks targeting smart devices and IoT environments. It integrates machine learning packet classification, Explainable AI (XAI), SOC case workflows, and an AI copilot.

#### Q2: Who is Zuka the Assistant?
**A:** Zuka is the platform's AI operations co-pilot. Zuka can run real-time database queries, inspect alerts, triage incidents, add analyst notes, check system health, and guide operators through standard operating procedures using sub-5ms deterministic rules or local Ollama LLM inference.

#### Q3: Does ZUKA send our telemetry or packet data to external cloud APIs?
**A:** **No.** ZUKA is engineered with strict local privacy. The backend, database, XGBoost inference engine, and Ollama LLM (`qwen2.5:3b`) all execute on premises (localhost). No network packets, alert logs, or user credentials are ever transmitted to third-party cloud services.

#### Q4: What roles exist in ZUKA and how do permissions differ?
**A:** There are three roles:
1. `ADMIN`: Full control over operations, telemetry, database management, and user approvals/deletions.
2. `SOC_ANALYST`: Operational control over alerts, incidents, investigations, and PDF reporting.
3. `VIEWER`: Read-only access to dashboards and network monitor.

#### Q5: Why can't newly registered users log in immediately?
**A:** For operational security, all newly registered accounts have status `is_active = False` by default. An `ADMIN` must log in and approve the user via the User Management interface (`/users`) or via the Assistant command `approve user <ID>` before login is permitted.

---

### 8.2 Alerts & Threat Detection FAQs

#### Q6: How does ZUKA classify incoming network traffic?
**A:** Ingested network flows are transformed into 14 statistical indicators (e.g., packet rates, byte volumes, inter-arrival times). These indicators are evaluated by a Unified XGBoost multiclass model trained on 2.56 million flows, categorizing traffic into one of 13 attack or benign classes.

#### Q7: How is alert severity calculated?
**A:** Severity is calculated directly from model confidence and threat class severity:
- `CRITICAL`: Model confidence >= 90%, or severe volumetric DoS/DDoS attacks.
- `HIGH`: Model confidence between 75% and 89%.
- `MEDIUM`: Model confidence between 55% and 74%.
- `LOW`: Model confidence < 55%.
- `INFO`: Assigned to verified benign baseline flows.

#### Q8: What does Explainable AI (XAI / SHAP) show me in an alert?
**A:** TreeSHAP computes the mathematical contribution of each flow feature toward the model's prediction. For example, if an alert is flagged as `DOS`, the SHAP chart shows whether extreme `flow_packet_rate`, miniature `src_iat_mean_sec`, or deficient `dst_bytes` drove the decision. This transparency allows analysts to rapidly rule out false positives.

#### Q9: How do I distinguish legitimate high-bandwidth video streaming from a DoS flood?
**A:** Legitimate video streaming (e.g., from an HD IP camera) features high payload byte volume (`dst_bytes`), steady inter-packet pacing, and balanced TCP acknowledgments. In contrast, a Denial of Service flood features abnormal packet counts with minimal or zero payload bytes, incomplete handshakes, and tiny inter-arrival times. The XGBoost model evaluates combinations of `flow_packet_rate`, `dst_bytes`, and `src_iat_mean_sec` to prevent false alarms.

#### Q10: How do I acknowledge an alert and why is it necessary?
**A:** Open the alert in Alert Center (`/alerts`) and click **Acknowledge**, or tell Zuka: `acknowledge alert <ID>`. Acknowledging acknowledges that a human analyst has triaged the alert. It is an operational prerequisite that unlocks the linked incident for active investigation.

---

### 8.3 Incident Management & Investigation FAQs

#### Q11: What is the difference between an Alert and an Incident?
**A:** An **Alert** is an automated detection event triggered by ML or signature rules for a specific flow. An **Incident** is an aggregated operational security case that tracks the full investigation, response, and resolution lifecycle handled by human analysts.

#### Q12: Why is the "Start Investigation" button disabled on an incident?
**A:** The linked alert has not been acknowledged yet. ZUKA enforces the rule that an alert must be in `ACKNOWLEDGED` status before an investigation dossier can be opened. Acknowledge the alert first to unlock the investigation.

#### Q13: What happens when an investigation is started?
**A:** The system generates a dedicated forensic dossier (`INV-...`), stamps `started_at`, assigns the incident to the current analyst, and updates the incident status to `INVESTIGATING`.

#### Q14: How are analyst notes stored and tracked?
**A:** Analyst notes are recorded in the investigation record and simultaneously logged in the immutable `analyst_actions` ledger with a unique Action ID (`ACT-XXXXXXXX`), timestamp, analyst ID, and description.

#### Q15: What is required before an incident can be marked RESOLVED?
**A:** The incident's investigation dossier must be completed with analyst findings and a conclusion summary. Once recorded, the analyst can resolve the incident by providing a resolution summary explaining the mitigation steps.

#### Q16: How do Escalation Levels work?
**A:** Escalation levels range from Level 0 (standard triage) to Level 3 (critical management escalation). Incidents involving verified breaches, compromised credentials, or active C2 botnets are escalated to engage senior engineers and emergency response protocols.

---

### 8.4 Security, Authentication & Session FAQs

#### Q17: How are passwords protected?
**A:** Passwords are never stored in plaintext. They are hashed using `passlib` with industry-standard bcrypt or Argon2 hashing algorithms with unique cryptographic salts.

#### Q18: How do session revocations and 2FA work?
**A:** Users can view active sessions in **Settings** (`/settings`) and revoke individual device tokens or revoke all active sessions. In addition, users can configure Time-based One-Time Password (TOTP) two-factor authentication, requiring a 6-digit authenticator code upon login.

#### Q19: What happens if an administrator tries to delete their own account?
**A:** The platform includes an explicit safety restriction: administrators cannot delete or deactivate their own active administrator account, preventing administrative lockout.

#### Q20: Why does deleting a user require a confirmation token?
**A:** User deletion is irreversible and immediately terminates all active sessions. To prevent accidental clicks, the assistant issues a 60-second confirmation token requiring the administrator to confirm the action.

---

### 8.5 Troubleshooting & Error State FAQs

#### Q21: What should I do if the Assistant displays "Unable to reach backend"?
**A:**
1. Check if the FastAPI backend service is running (`http://127.0.0.1:8000`).
2. Verify network connectivity and check browser console errors.
3. Ensure your JWT session token has not expired; if expired, log out and log back in.

#### Q22: What happens if Ollama is not running on localhost:11434?
**A:** The ZUKA Assistant will automatically fall back to its internal deterministic rule parser and database tools. Essential operations (showing alerts, listing incidents, updating statuses, checking health) will continue to function seamlessly in sub-5ms without interruption.

#### Q23: How do I verify live system and database health?
**A:** Ask Zuka: `system status` or navigate to `/api/health`. The system verifies the database connection, table row counts, open alerts, and active incidents.

---

## 9. Assistant System Prompt & Operating Boundaries

When building or fine-tuning an AI Assistant instance for this website, use the following system prompt and guardrail specifications:

### 9.1 System Prompt Definition
```text
You are Zuka, the dedicated AI Cybersecurity Operations Assistant for the ZUKA SOC Platform.
Your purpose is to assist SOC analysts in monitoring, triaging, investigating, and documenting
network attacks against smart devices and IoT infrastructure.

Operational Directives:
1. Grounding & Zero Hallucination: Derive all metrics, record counts, alert IDs, incident IDs,
   and timestamps exclusively from verified database records. Never fabricate identifiers.
2. Step-by-Step SOP Adherence: Strictly follow standard operating procedures:
   - Alerts must be ACKNOWLEDGED before an incident investigation can begin.
   - An investigation must be COMPLETED with notes and a conclusion before an incident can be RESOLVED.
3. Safety & Confirmation: Destructive actions (deleting users, deactivating accounts) require explicit
   human confirmation via confirmation tokens. Never bypass confirmation workflows.
4. Defensive Boundary: Strictly refuse any request to generate exploit code, craft malicious packets,
   or participate in unauthorized attacks. All recommendations must be strictly defensive and educational.
5. Tone & Format: Maintain a concise, professional, and authoritative tone. Use markdown formatting,
   bullet points, and action cards to make operational information rapidly actionable for analysts.
```

### 9.2 Refusal Template for Malicious Prompts
If a user requests exploit payloads or attack scripts:
> *"I cannot generate exploit scripts, malicious packet payloads, or facilitate unauthorized attacks. Zuka is strictly designed for defensive smart-device security monitoring, threat triage, and SOC operational workflows. I can assist you with identifying attack signatures, evaluating security posture, or analyzing network flow telemetry."*

### 9.3 Fallback Template for Missing Information
If a user asks about a topic outside the platform's knowledge:
> *"I don't have that information in my knowledge base. You can ask about: alert management, incident triage, forensic investigations, network telemetry monitoring, or compliance reports."*

---

*End of Knowledge Base — ZUKA SOC Platform Reference Manual v2.1.0*
