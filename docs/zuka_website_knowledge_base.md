# ZUKA SOC Website Assistant Knowledge Base

**Purpose:** The single approved reference for the ZUKA website assistant and its retrieval index. This document consolidates the existing assistant references, RAG guidance, and verified website workflows. Keep each topic current here, then rebuild the RAG index as described in `rag_assistant/README.md`.

## Assistant scope and answer policy

### What can Zuka answer?
Zuka answers questions about the ZUKA SOC website, its documented security monitoring and case-management features, user roles, platform procedures, and the cybersecurity concepts explicitly described in this knowledge base. It can also retrieve live alerts, incidents, investigations, and other authorized SOC records through the authenticated website assistant tools. Live records are answered from the connected database, not from this static document.

### What should Zuka refuse or hand off?
Zuka must refuse requests to create malware, exploit code, malicious packet payloads, or instructions for unauthorized access. It may offer defensive detection, triage, and remediation guidance covered by this knowledge base.

For ordinary questions outside the documented ZUKA scope, or when retrieved information does not support an answer, Zuka must reply exactly: `I don't have that information. Please contact <chitlakarthik66@gmail.com>.` It must not guess or fill gaps with general model knowledge. This configured email is the documented fallback contact; no public contact page URL, support form, response-time promise, or office hours are specified here.

### How should answers be written?
Use only the supplied knowledge-base context for static factual answers. Keep replies concise, use the question's language where possible, and cite the retrieved section titles when available. Never invent prices, dates, hours, URLs, phone numbers, policies, service commitments, record IDs, or live metrics. Treat live database facts as authoritative only when returned by an authorized SOC tool.

### What is Zuka's policy for hallucinations and live database questions?
Zuka must not invent packet numbers, IP addresses, alert IDs, incident IDs, device statuses, record counts, or timestamps. Live counts, statuses, identifiers, and timestamps must come from an authorized database operation. If the required record or count is not returned, Zuka must use the configured contact fallback.

### How does Zuka handle website operations before general questions?
Zuka first checks whether a request asks for a live website operation or current SOC data. Requests such as **"Show me alerts"**, **"How many incidents are there?"**, and **"List investigations"** must use the authenticated live database tools. Only when a request is not a recognized operation should Zuka answer a general website or cybersecurity question from this knowledge base. Never use this static document to invent current alert or incident records, counts, or statuses.

## Platform overview

### What is ZUKA SOC?
ZUKA SOC is a web-based security operations platform for monitoring network traffic, detecting suspicious activity affecting smart devices and IoT infrastructure, reviewing alerts, managing incidents and investigations, and producing reports. Its assistant is named Zuka.

### Why do smart devices need dedicated SOC monitoring instead of traditional antivirus or EDR?
Smart devices often have resource-constrained hardware that cannot run traditional host-based antivirus or Endpoint Detection and Response (EDR) agents. ZUKA monitors their network flows out of band.

### What insecure defaults may smart devices have?
The platform reference identifies factory credentials such as `admin/admin` and exposed Telnet or UPnP services as examples of insecure defaults. These are general examples; Zuka must not claim they are present on a particular device without live evidence.

### How can compromised IoT devices be used in botnets?
Compromised IoT devices can be recruited into botnets such as Mirai and used in distributed volumetric attacks. Zuka may explain this at a defensive, high level but must not provide instructions for compromising devices.

### What are the platform's documented capabilities?
- Dashboard summaries of alert and incident activity.
- Network telemetry monitoring and traffic visualizations.
- Machine-learning alert classification with per-alert explainability information when available.
- Alert review, incident triage, investigation notes and conclusions, and defensive containment workflows.
- Executive, incident, alert, and detection explanation reports.
- Role-based user access, administration, and audit history.
- An authenticated assistant that combines knowledge-base answers with authorized live SOC operations.

### What technologies are documented for the website?
The project uses a React and TypeScript frontend, a FastAPI backend, PostgreSQL for operational records, and a local ChromaDB plus Ollama RAG pipeline for knowledge questions. The RAG configuration names `qwen2.5:3b` for generation and `nomic-embed-text` for embeddings. Other assistant model providers may be configured in a deployment; the assistant must not claim the whole product always runs locally unless that deployment is verified.

### Does ZUKA offer public services, subscription plans, or prices?
Pricing, subscription plans, public service packages, and sales terms are not documented. Zuka must use the configured contact fallback rather than state or estimate a price.

### What are ZUKA's opening hours or support response times?
Opening hours, staffed support hours, and response-time commitments are not documented. Zuka must not infer them.

## Website navigation and access

### Which pages are available?
The authenticated website includes Dashboard and Network Monitor. Operational pages include Alert Center, Incident Management, Defense Department, Investigation, Reports, and Settings. Administrators also have Database Center and User Management.

### How do I open Settings?
Open Settings. The page documents profile email and password changes, active-session review and revocation, and optional TOTP two-factor authentication.

### Where can I open Database Center?
Database Center is available to administrators. It displays database status, table record counts, and schema definitions.

### What user roles exist?
- `ADMIN`: Full platform and administration access, including user management and Database Center.
- `SOC_ANALYST`: Operational access for reviewing alerts, managing incidents and investigations, using defense workflows and reports, changing personal settings, and using the assistant.
- `VIEWER`: Read-only access to the dashboard and network monitor.

The website enforces role access. Zuka must not imply that a user can access or change records beyond their permissions.

### What can an administrator manage?
The User Management page supports reviewing users and pending registrations, approving accounts, and managing account access. Database Center is documented as administrator-only and provides database health and operational audit views. A user cannot deactivate or delete their own active administrator account.

### What account settings are available?
The Settings page documents profile email and password changes, active-session review and revocation, and optional time-based one-time password (TOTP) two-factor authentication. Zuka must not claim a setting was changed unless the live operation confirms it.

### How does account approval work?
New registrations are pending administrator approval before they can sign in. An administrator can review pending accounts in User Management (`/users`). Exact registration policies beyond this approval step are not documented.

## Security operations

### What is an alert?
An alert is a suspicious network event recorded by the platform's detection pipeline. Alert records may include an identifier, predicted class, confidence, severity, status, source and destination addresses and ports, protocol, and detection time. Documented statuses are `OPEN`, `ACKNOWLEDGED`, `RESOLVED`, and `FALSE_POSITIVE`. For a specific alert, Zuka must retrieve the live record rather than make up values.

### How do I review or acknowledge an alert?
Open Alert Center, select an alert, review its available detection and traffic details, then choose **Acknowledge Alert**. The assistant can also process an `acknowledge alert <ID>` request when the signed-in user is authorized. An alert must be acknowledged before the linked incident investigation can proceed.

### What is an incident?
An incident is a case used to coordinate triage and response to a security issue. The documented lifecycle includes `OPEN`, `ACKNOWLEDGED`, `INVESTIGATING`, `RESOLVED`, and `CLOSED`. Current state and identifiers must come from live records.

### What priority and escalation levels are documented?
Incident priorities are `P1` (urgent/business critical), `P2` (high), `P3` (medium), and `P4` (low). Escalation runs from Level 0 (normal triage) through Level 3 (critical management escalation and incident response team mobilization). The current priority and escalation of any case must come from its live record.

### How do I start an investigation?
First acknowledge the incident's linked alert. Then start the investigation from Incident Management or ask Zuka to investigate the incident. The platform creates or opens a forensic dossier for the case. If the linked alert is not acknowledged, the workflow is locked until it is.

### How do I add an investigation note?
Open the case's investigation dossier and add a note, or ask Zuka to `add analyst note to <ID>: <note>`. Notes are associated with the analyst and recorded in the platform's action history. Do not claim a note was saved unless the live operation confirms it.

### How do I complete an investigation?
Record an evidence-based conclusion in the investigation dossier, save it, then mark the investigation `COMPLETED`. Completing the investigation unlocks incident resolution.

### How do I resolve or close an incident?
An investigation must be `COMPLETED` with an analyst conclusion before the incident can be resolved. Resolve the incident from Incident Management or ask Zuka to resolve it with a summary. A resolved incident can then be closed after its post-incident review. Zuka must use the confirmation flow required by the live assistant for any operation that requests confirmation.

### What defensive actions are available?
The Defense Department documents `VLAN_QUARANTINE`, `BLOCK_IP`, `CREDENTIAL_ROTATION`, `RATE_LIMIT`, `FIRMWARE_PATCH`, and `CUSTOM` containment actions. These are defensive response options, not proof that a network control has been deployed. Applying a defense action is documented to add a directive to the investigation notes and record an analyst action. Zuka must report an action as completed only after the live operation confirms it.

### How many defense action types are documented?
There are six documented defense action types: `VLAN_QUARANTINE`, `BLOCK_IP`, `CREDENTIAL_ROTATION`, `RATE_LIMIT`, `FIRMWARE_PATCH`, and `CUSTOM`. This is the number of available action types, not a live count of defenses currently deployed.

### How do I generate a report?
Open Reports, select a supported report type and the relevant record where required, then generate the report. Documented types include incident reports, alert reports, executive summaries, and detection explainability reports. The interface also supports printing report documents.

### What records appear in the audit history?
The platform reference describes alert, incident, and investigation records, network events, analyst actions, and security audit logs. Analyst actions record human-authorized operational changes, while audit history covers security events such as sign-ins, session revocations, password changes, and permission changes. Specific counts and timestamps must be obtained from the live system.

## Detection and explainability

### How does the documented detection model work?
The platform knowledge reference describes a multiclass XGBoost model that classifies network-flow records, with TreeSHAP used to explain feature contributions for supported alert views. A model prediction is an automated classification and should not be presented as independently confirmed malicious activity.

### Which traffic classes are documented?
The reference lists: `BENIGN`, `DOS`, `DDOS`, `PORT_SCAN`, `BRUTE_FORCE`, `BOTNET`, `BACKDOOR`, `RECONNAISSANCE`, `EXPLOIT`, `FUZZING`, `INFILTRATION`, `MALWARE`, and `OTHER_ATTACK`.

### What model results are documented?
The project knowledge reference reports a training corpus of 2,561,658 network flows, approximately 93.0% overall multiclass accuracy, and F1 scores of 99.2% for DDoS, 92.6% for DoS, and 96.3% for benign traffic. These are reported model-evaluation results, not guarantees for every deployment or prediction. Do not claim a current production score without a current evaluation source.

### What does explainability show?
The alert inspection view can show feature contributions that help explain why the classifier produced a prediction. These contributions describe model behavior; they do not by themselves establish attacker identity, intent, or a confirmed compromise.

### Which tool provides explainable AI for detection alerts?
TreeSHAP, implemented with `shap.TreeExplainer`, calculates feature contributions for the XGBoost detection model. Ollama is used for assistant language generation; it does not calculate the detection model's explanations.

### What network-flow features are documented?
The reference names 14 features: `duration_sec`, `src_packets`, `dst_packets`, `src_bytes`, `dst_bytes`, `flow_packet_rate`, `src_packet_rate`, `dst_packet_rate`, `src_byte_rate`, `dst_byte_rate`, `src_packet_size_mean`, `dst_packet_size_mean`, `src_iat_mean_sec`, and `dst_iat_mean_sec`. Actual values for a specific event must be read from its live record.

### What cybersecurity guidance may Zuka provide?
Zuka may explain defensive concepts documented in the knowledge base, such as isolating IoT devices, limiting exposed management services, rotating credentials, applying vendor firmware updates, and using network rate limits. It must avoid exploit instructions and must not imply that a suggested control is already active.

### Why are unpatched smart-device firmware versions a risk?
Smart devices may rarely receive automatic firmware updates from vendors. An unpatched device can remain exposed to known vulnerabilities in its firmware or services. Zuka may recommend applying vendor-provided firmware updates as defensive guidance; it must not claim a specific device is vulnerable without evidence from its live record.

## Privacy and assistant behavior

### How does the website assistant connect to the knowledge base?
The signed-in website widget sends chat requests to the FastAPI `/api/zuka-assistant/chat` endpoint with the user's authentication token. The backend handles live SOC operations and routes informational questions through the RAG knowledge engine. Retrieved answers include their source section titles when available.

### What happens when Zuka cannot find an answer?
It returns the configured fallback exactly: `I don't have that information. Please contact <chitlakarthik66@gmail.com>.` The assistant must not invent a contact page, email form, business hours, pricing, or policy.

### Does ZUKA process data in the cloud?
The assistant reference describes Ollama as a local model runtime and the intended setup as local inference. Deployment-specific privacy guarantees are not documented here; Zuka must not claim that every environment is completely offline or that no data ever leaves a host unless the deployment configuration verifies that claim.

### How does Zuka avoid inventing live metrics?
Alert, incident, investigation, user, and network-event counts, statuses, identifiers, and timestamps must come from an authorized live database tool. If the tool does not return the requested fact, Zuka must say it does not have that information and use the configured contact fallback. It must never substitute one record type's count for another or make up a live result.

### What can a VIEWER do?
The `VIEWER` role has read-only access to the Dashboard and Network Monitor. It cannot acknowledge alerts, create or modify incidents, write investigation notes, change settings, or manage users. Access to other pages depends on the signed-in role.

## Knowledge gaps

The following public-facing business details are not specified in the available assistant materials: prices, subscription plans, opening hours, support service levels, a public contact-page URL, and a contact form. For questions about these or any unsupported fact, use the exact configured fallback contact. Do not infer answers from unrelated technical documentation.
