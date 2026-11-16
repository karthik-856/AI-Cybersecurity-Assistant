from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic running header and footer with total page count."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, total_pages: int) -> None:
        self.saveState()
        width, height = A4
        margin_x = 14 * mm

        # Running Header (pages 2+)
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.6)
            self.line(margin_x, height - 12 * mm, width - margin_x, height - 12 * mm)

            self.setFont("Helvetica-Bold", 7.5)
            self.setFillColor(colors.HexColor("#0284C7"))
            self.drawString(margin_x, height - 9 * mm, "ZUKA SOC PLATFORM  //  OPERATIONAL KNOWLEDGE BASE")

            self.setFont("Helvetica", 7.5)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawRightString(
                width - margin_x,
                height - 9 * mm,
                "CLASSIFICATION: INTERNAL RESTRICTED  •  VERSION 2.1.0",
            )

        # Running Footer (all pages)
        footer_y = 10 * mm
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.6)
        self.line(margin_x, footer_y + 4 * mm, width - margin_x, footer_y + 4 * mm)

        self.setFont("Helvetica-Bold", 7.0)
        self.setFillColor(colors.HexColor("#0F172A"))
        self.drawString(margin_x, footer_y, "ZUKA SECURITY OPERATIONS CENTER")

        self.setFont("Helvetica", 7.0)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(
            margin_x + 55 * mm,
            footer_y,
            "• AI-ASSISTED SMART DEVICE THREAT MONITORING REFERENCE",
        )

        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor("#0F172A"))
        self.drawRightString(
            width - margin_x,
            footer_y,
            f"Page {self._pageNumber} of {total_pages}",
        )

        self.restoreState()


def get_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()

    c_primary = colors.HexColor("#0F172A")
    c_accent = colors.HexColor("#0284C7")
    c_text = colors.HexColor("#334155")
    c_subtle = colors.HexColor("#64748B")

    return {
        "doc_title": ParagraphStyle(
            "DocTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=c_primary,
            alignment=0,
            spaceAfter=6,
        ),
        "doc_subtitle": ParagraphStyle(
            "DocSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=c_accent,
            spaceAfter=14,
        ),
        "meta_label": ParagraphStyle(
            "MetaLabel",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=c_subtle,
        ),
        "meta_value": ParagraphStyle(
            "MetaValue",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=c_primary,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=c_primary,
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=c_accent,
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13,
            textColor=c_primary,
            spaceBefore=8,
            spaceAfter=3,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12.5,
            textColor=c_text,
            spaceAfter=5,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12.5,
            textColor=c_text,
            leftIndent=12,
            firstLineIndent=-8,
            spaceAfter=3,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10.5,
            textColor=c_text,
        ),
        "table_cell_bold": ParagraphStyle(
            "TableCellBold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.8,
            leading=10.5,
            textColor=c_primary,
        ),
        "callout_text": ParagraphStyle(
            "CalloutText",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.2,
            leading=11.5,
            textColor=colors.HexColor("#1E293B"),
        ),
        "code_block": ParagraphStyle(
            "CodeBlock",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#0F172A"),
        ),
        "faq_q": ParagraphStyle(
            "FAQQ",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12.5,
            textColor=colors.HexColor("#0369A1"),
            spaceBefore=6,
            spaceAfter=2,
            keepWithNext=True,
        ),
        "faq_a": ParagraphStyle(
            "FAQA",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=c_text,
            spaceAfter=6,
        ),
    }


def make_callout(text: str, styles: dict[str, ParagraphStyle], title: str = "OPERATIONAL NOTE", border_color: str = "#0284C7", bg_color: str = "#F0F9FF") -> Table:
    p_title = Paragraph(f"<b>{title}</b>", ParagraphStyle("CTitle", parent=styles["meta_label"], textColor=colors.HexColor(border_color), fontSize=8))
    p_body = Paragraph(text, styles["callout_text"])
    t = Table([[p_title], [p_body]], colWidths=[182 * mm])
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg_color)),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor(border_color)),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    return t


def build_knowledge_base_pdf(output_path: str) -> None:
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    styles = get_styles()
    story: list[Any] = []

    # =========================================================================
    # HEADER / COVER TITLE
    # =========================================================================
    story.append(Paragraph("ZUKA SOC PLATFORM", styles["doc_subtitle"]))
    story.append(Paragraph("Master Knowledge Base & Assistant Operational Reference", styles["doc_title"]))
    story.append(
        Paragraph(
            "Authoritative operational manual, system architecture, standard operating procedures, and comprehensive reference guide for the Zuka AI Cybersecurity Operations Assistant.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 4 * mm))

    # Metadata Grid
    meta_data = [
        [
            Paragraph("PLATFORM", styles["meta_label"]),
            Paragraph("ZUKA SOC Cyber Platform", styles["meta_value"]),
            Paragraph("DOCUMENT VERSION", styles["meta_label"]),
            Paragraph("2.1.0 (Production)", styles["meta_value"]),
        ],
        [
            Paragraph("SYSTEM TARGET", styles["meta_label"]),
            Paragraph("Smart Device & IoT Security", styles["meta_value"]),
            Paragraph("DATE GENERATED", styles["meta_label"]),
            Paragraph(datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), styles["meta_value"]),
        ],
        [
            Paragraph("ASSISTANT ENGINE", styles["meta_label"]),
            Paragraph("Dual: Rule Parser + Ollama qwen2.5:3b", styles["meta_value"]),
            Paragraph("SECURITY CLASSIFICATION", styles["meta_label"]),
            Paragraph("INTERNAL SOC RESTRICTED", ParagraphStyle("RedB", parent=styles["meta_value"], textColor=colors.HexColor("#DC2626"))),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[36 * mm, 55 * mm, 45 * mm, 46 * mm])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 6 * mm))

    # =========================================================================
    # SECTION 1: SYSTEM IDENTITY & MISSION OVERVIEW
    # =========================================================================
    story.append(Paragraph("1. System Identity & Mission Overview", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceAfter=5))
    story.append(
        Paragraph(
            "The <b>ZUKA SOC Platform</b> is an enterprise-grade Security Operations Center platform specifically engineered "
            "to detect, diagnose, investigate, and triage network attacks directed against smart devices and Internet of Things (IoT) infrastructure.",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            "<b>Why Smart Devices Require Dedicated SOC Operations:</b><br/>"
            "• <b>Resource Constraints:</b> Microcontroller CPU and RAM cannot support traditional antivirus or host-based EDR agents.<br/>"
            "• <b>Insecure Defaults:</b> Devices frequently ship with default credentials (e.g. <code>admin/admin</code>) and unencrypted management daemons (Telnet port 23, UPnP).<br/>"
            "• <b>Unpatched Firmware:</b> Vendors rarely push automated security updates, leaving known vulnerabilities active indefinitely.<br/>"
            "• <b>Volumetric Weaponization:</b> Compromised devices are rapidly recruited into Mirai-style botnets to conduct volumetric DDoS attacks.",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            "<b>Assistant Identity & Personality:</b><br/>"
            "The integrated assistant (<b>Zuka</b>) acts as an autonomous Tier-1/Tier-2 SOC co-pilot. Zuka adheres strictly to a "
            "<b>Zero-Hallucination Policy</b> (all IDs, counts, and metrics are derived directly from verified database queries) and a "
            "<b>Strict Defensive Boundary</b> (refusing any request to generate exploit payloads or facilitate attacks).",
            styles["body"],
        )
    )
    story.append(Spacer(1, 4 * mm))

    # =========================================================================
    # SECTION 2: PLATFORM ARCHITECTURE & TECHNOLOGY STACK
    # =========================================================================
    story.append(Paragraph("2. Platform Architecture & Technology Stack", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceAfter=5))

    arch_rows = [
        [
            Paragraph("COMPONENT", styles["table_header"]),
            Paragraph("TECHNOLOGY", styles["table_header"]),
            Paragraph("OPERATIONAL RESPONSIBILITY", styles["table_header"]),
        ],
        [
            Paragraph("Frontend UI", styles["table_cell_bold"]),
            Paragraph("React 18, TypeScript, Vite, Lucide Icons", styles["table_cell"]),
            Paragraph("Responsive SOC dashboard, interactive ActionCards, alert drawers, and telemetry charts.", styles["table_cell"]),
        ],
        [
            Paragraph("Backend API", styles["table_cell_bold"]),
            Paragraph("FastAPI (Python 3.13), Uvicorn", styles["table_cell"]),
            Paragraph("Asynchronous REST API, JWT authentication, RBAC authorization, and router dispatching.", styles["table_cell"]),
        ],
        [
            Paragraph("Database", styles["table_cell_bold"]),
            Paragraph("PostgreSQL, SQLAlchemy 2.0, Alembic", styles["table_cell"]),
            Paragraph("Relational persistence for alerts, incidents, investigations, analyst action ledgers, and audit logs.", styles["table_cell"]),
        ],
        [
            Paragraph("ML Detection", styles["table_cell_bold"]),
            Paragraph("Unified XGBoost Multiclass Decision Trees", styles["table_cell"]),
            Paragraph("Real-time classification across 13 traffic categories trained on 2,561,658 network flows.", styles["table_cell"]),
        ],
        [
            Paragraph("Explainable AI", styles["table_cell_bold"]),
            Paragraph("TreeSHAP (shap.TreeExplainer)", styles["table_cell"]),
            Paragraph("Computes Shapley feature importance attributions per packet flow to explain algorithmic decisions.", styles["table_cell"]),
        ],
        [
            Paragraph("Local AI Assistant", styles["table_cell_bold"]),
            Paragraph("Ollama (qwen2.5:3b) + Sub-5ms Regex Engine", styles["table_cell"]),
            Paragraph("Grounded natural language interface with human-in-the-loop safety confirmation tokens.", styles["table_cell"]),
        ],
    ]
    t_arch = Table(arch_rows, colWidths=[32 * mm, 50 * mm, 100 * mm])
    t_arch.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    story.append(t_arch)
    story.append(Spacer(1, 4 * mm))

    # =========================================================================
    # SECTION 3: ROLE-BASED ACCESS CONTROL (RBAC)
    # =========================================================================
    story.append(Paragraph("3. Role-Based Access Control (RBAC) & User Management", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceAfter=5))

    rbac_rows = [
        [
            Paragraph("ROLE", styles["table_header"]),
            Paragraph("PERMITTED OPERATIONS", styles["table_header"]),
            Paragraph("OPERATIONAL CONSTRAINTS", styles["table_header"]),
        ],
        [
            Paragraph("ADMIN", styles["table_cell_bold"]),
            Paragraph("Full access: All operational modules, system telemetry, database center, user account approval, deactivation, and safety-confirmed deletion.", styles["table_cell"]),
            Paragraph("Safety safeguard: Cannot delete or deactivate own active administrator account.", styles["table_cell"]),
        ],
        [
            Paragraph("SOC_ANALYST", styles["table_cell_bold"]),
            Paragraph("Operational access: Dashboard, Network Monitor, Alert Center, Incident Management, Forensic Investigations, and PDF Reports.", styles["table_cell"]),
            Paragraph("Cannot approve new users, delete user accounts, or modify core database schema definitions.", styles["table_cell"]),
        ],
        [
            Paragraph("VIEWER", styles["table_cell_bold"]),
            Paragraph("Read-only access: Operational overview on Dashboard and live packet inspection in Network Monitor.", styles["table_cell"]),
            Paragraph("Cannot acknowledge alerts, open investigations, edit incident statuses, add notes, or export reports.", styles["table_cell"]),
        ],
    ]
    t_rbac = Table(rbac_rows, colWidths=[28 * mm, 80 * mm, 74 * mm])
    t_rbac.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    story.append(t_rbac)
    story.append(Spacer(1, 3 * mm))
    story.append(
        make_callout(
            "<b>Registration Security:</b> All newly registered accounts default to <code>is_active = False</code> (Pending Approval). "
            "An administrator must authorize the analyst via the User Management panel (<code>/users</code>) or via the assistant command "
            "<code>approve user &lt;ID&gt;</code> before login credentials become active.",
            styles,
            title="SECURITY GATEWAY",
            border_color="#F59E0B",
            bg_color="#FFFBEB",
        )
    )
    story.append(Spacer(1, 5 * mm))

    # =========================================================================
    # SECTION 4: PLATFORM MODULES & OPERATIONS GUIDE
    # =========================================================================
    story.append(Paragraph("4. Platform Modules & Operational Guide", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceAfter=5))

    modules = [
        ("Dashboard (/dashboard)", "Central situational awareness console. Displays live threat indicators, 24h attack distributions, protocol breakdowns (TCP/UDP/ICMP), active incident queues, and system operational health."),
        ("Network Monitor (/network-monitor)", "Real-time packet telemetry visualizer. Inspects live bidirectional packet streams, bandwidth consumption curves, port scans, and packet burst frequencies feeding detection workers."),
        ("Alert Center (/alerts)", "Ingestion engine for automated ML threat detections. Evaluates confidence scores, severity ratings, port mappings, and hosts the Explainable AI (TreeSHAP) drawer for root-cause feature attribution. Analysts must click 'Acknowledge' to unlock investigation."),
        ("Incident Management (/incidents)", "Structured lifecycle case management: OPEN -> ACKNOWLEDGED -> INVESTIGATING -> RESOLVED -> CLOSED. Supports analyst assignment, priority ratings (P1 to P4), escalation tiers (Level 0 to Level 3), and strict investigation completion gating."),
        ("Defense Department (/defense)", "Dedicated incident response and containment console. Filters exclusively for open investigations. Identifies network detection telemetry (attacker IP, destination IP, ports, protocol, attack class, and automated threat diagnosis). Analysts apply defensive containment countermeasures (VLAN quarantine, IP block, credential rotation, rate limiting, firmware lockdown) which automatically append formatted directives into the Investigation Department dossier and log audit events in analyst_actions."),
        ("Investigation Department (/investigation)", "Digital forensic workspace housing case dossiers (INV-...). Consolidates chronological analyst notes, defense directives, and packet findings. The SOC analyst manually writes the final conclusion, and marking the investigation COMPLETED unlocks incident resolution."),
        ("Reports & PDF Export (/reports)", "Publication-grade document generator producing multi-page PDF records for Incidents, Alerts, Detection XAI analyses, and Executive SOC Summaries. Features isolated CSS print styling for clean white paper printing without website artifacts."),
        ("Database Center (/databases)", "Administrator-only system registry displaying live PostgreSQL table record counts, schema layouts, and the permanent immutable Analyst Action Ledger (automatically recording all operational actions across the platform)."),
        ("User Management (/users)", "Administrator console for controlling operator credentials, authorizing pending registrations, toggling active states, and permanently removing departed staff."),
        ("Settings & Security (/settings)", "Profile management, password updates, active browser session revocation, and Time-based One-Time Password (TOTP) 2FA authentication controls."),
    ]

    for title, desc in modules:
        story.append(Paragraph(f"• <b>{title}:</b> {desc}", styles["body"]))

    story.append(Spacer(1, 5 * mm))

    # =========================================================================
    # SECTION 5: MACHINE LEARNING & EXPLAINABLE AI (XAI)
    # =========================================================================
    story.append(Paragraph("5. Machine Learning, IoT Detection & Explainable AI (XAI)", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceAfter=5))
    story.append(
        Paragraph(
            "<b>Model Architecture & Training Corpus:</b><br/>"
            "ZUKA utilizes a Unified XGBoost Multiclass Decision Tree model trained on <b>2,561,658 network flows</b> with balanced class weighting. "
            "Validation achieves <b>~93.0% multiclass accuracy</b>, <b>99.2% F1 on DDoS</b>, <b>92.6% on DoS</b>, and <b>96.3% on Benign traffic</b>.",
            styles["body"],
        )
    )

    # 13 Classes Table
    classes_data = [
        [Paragraph("CLASS", styles["table_header"]), Paragraph("NETWORK SIGNATURE & BEHAVIOR", styles["table_header"]), Paragraph("TYPICAL SEVERITY", styles["table_header"])],
        [Paragraph("BENIGN", styles["table_cell_bold"]), Paragraph("Normal smart device telemetry, cloud polling, NTP synchronization.", styles["table_cell"]), Paragraph("INFO", styles["table_cell"])],
        [Paragraph("DOS", styles["table_cell_bold"]), Paragraph("Single-source packet flooding exhausting microcontroller memory or network buffers.", styles["table_cell"]), Paragraph("HIGH / CRITICAL", styles["table_cell"])],
        [Paragraph("DDOS", styles["table_cell_bold"]), Paragraph("Distributed coordinated volumetric flood overwhelming gateways and hubs.", styles["table_cell"]), Paragraph("CRITICAL", styles["table_cell"])],
        [Paragraph("PORT_SCAN", styles["table_cell_bold"]), Paragraph("Systematic probing of TCP/UDP ports to discover open daemons (RTSP, Telnet, HTTP).", styles["table_cell"]), Paragraph("MEDIUM", styles["table_cell"])],
        [Paragraph("BRUTE_FORCE", styles["table_cell_bold"]), Paragraph("Automated dictionary credential attacks against Telnet (port 23) or SSH (port 22).", styles["table_cell"]), Paragraph("HIGH", styles["table_cell"])],
        [Paragraph("BOTNET", styles["table_cell_bold"]), Paragraph("Mirai-style recruitment, malware download, and periodic C2 beaconing heartbeats.", styles["table_cell"]), Paragraph("CRITICAL", styles["table_cell"])],
        [Paragraph("BACKDOOR", styles["table_cell_bold"]), Paragraph("Unauthorized persistent reverse listener or shell on compromised IoT hardware.", styles["table_cell"]), Paragraph("CRITICAL", styles["table_cell"])],
        [Paragraph("RECONNAISSANCE", styles["table_cell_bold"]), Paragraph("Active host discovery and network topology mapping across subnets.", styles["table_cell"]), Paragraph("MEDIUM", styles["table_cell"])],
        [Paragraph("EXPLOIT", styles["table_cell_bold"]), Paragraph("Known vulnerability payloads directed against smart device web daemons or firmware.", styles["table_cell"]), Paragraph("HIGH", styles["table_cell"])],
        [Paragraph("FUZZING", styles["table_cell_bold"]), Paragraph("Malformed high-entropy payloads designed to crash embedded network parsers.", styles["table_cell"]), Paragraph("MEDIUM", styles["table_cell"])],
        [Paragraph("INFILTRATION", styles["table_cell_bold"]), Paragraph("Lateral movement from compromised peripheral devices deeper into internal LAN.", styles["table_cell"]), Paragraph("HIGH", styles["table_cell"])],
        [Paragraph("MALWARE", styles["table_cell_bold"]), Paragraph("Binary payload distribution targeting embedded ARM/MIPS IoT architectures.", styles["table_cell"]), Paragraph("HIGH", styles["table_cell"])],
        [Paragraph("OTHER_ATTACK", styles["table_cell_bold"]), Paragraph("Anomalous malicious deviation not conforming to standard single attack definitions.", styles["table_cell"]), Paragraph("MEDIUM", styles["table_cell"])],
    ]
    t_classes = Table(classes_data, colWidths=[32 * mm, 120 * mm, 30 * mm])
    t_classes.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_classes)
    story.append(Spacer(1, 4 * mm))

    story.append(
        Paragraph(
            "<b>The 14 Network Flow Features:</b><br/>"
            "<code>duration_sec</code>, <code>src_packets</code>, <code>dst_packets</code>, <code>src_bytes</code>, <code>dst_bytes</code>, "
            "<code>flow_packet_rate</code>, <code>src_packet_rate</code>, <code>dst_packet_rate</code>, <code>src_byte_rate</code>, <code>dst_byte_rate</code>, "
            "<code>src_packet_size_mean</code>, <code>dst_packet_size_mean</code>, <code>src_iat_mean_sec</code>, <code>dst_iat_mean_sec</code>.",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            "<b>TreeSHAP Explainability:</b><br/>"
            "TreeSHAP calculates exact additive Shapley values for each of the 14 features on every prediction. "
            "This demystifies model inference: analysts can confirm whether an alert was triggered by an abnormal <code>flow_packet_rate</code> "
            "or low <code>src_iat_mean_sec</code>, directly eliminating false alarms on legitimate high-bandwidth video streaming.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 5 * mm))

    # =========================================================================
    # SECTION 6: STANDARD OPERATING PROCEDURES (SOPS)
    # =========================================================================
    story.append(Paragraph("6. Standard Operating Procedures (SOPs) & Workflows", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceAfter=5))

    sops = [
        ("SOP-01: Acknowledging an Alert (Alert Center)", "1. Navigate to Alert Center (/alerts).<br/>2. Click alert row to open inspection drawer.<br/>3. Review threat classification, confidence, and TreeSHAP contributions.<br/>4. Click 'Acknowledge Alert' (or tell Zuka: <code>acknowledge alert &lt;ID&gt;</code>).<br/><i>*Mandatory rule: Acknowledging the alert sets both alert and correlated incident to ACKNOWLEDGED.</i>"),
        ("SOP-02: Initiating Case Investigation (Incident Management)", "1. Verify correlated incident is in ACKNOWLEDGED status.<br/>2. In Incident Management (/incidents), select the incident.<br/>3. Click 'Start Investigation' (or tell Zuka: <code>investigate incident &lt;ID&gt;</code>).<br/>4. System transitions incident to INVESTIGATING and auto-provisions an active forensic dossier (INV-...) in IN_PROGRESS, immediately visible in both Investigation and Defense Departments."),
        ("SOP-03: Triaging & Defending the Incident (Defense Department)", "1. Navigate to Defense Department (/defense), which exclusively displays open investigations.<br/>2. Review live network detection telemetry (attacker IP, target IP, ports, protocol, AI confidence, and automated threat diagnosis).<br/>3. Select a tactical defense containment strategy (VLAN quarantine, IP block, credential rotation, rate limiting, firmware lockdown).<br/>4. Formulate the containment note and click 'Apply Defense & Append Note to Investigation'.<br/>5. Directive note is automatically appended to the investigation dossier and logged in the immutable analyst_actions ledger."),
        ("SOP-04: Authoring Conclusion & Completing Investigation (Investigation Department)", "1. Open Investigation Department (/investigation) and review consolidated findings and defense directives.<br/>2. The SOC analyst manually authors the final evidence-based Analyst Conclusion.<br/>3. Click 'Save Conclusion' and then click 'Complete Investigation'. Status transitions to COMPLETED without any blocking popup errors.<br/><i>*Prerequisite rule: Completed investigation with analyst conclusion unlocks incident resolution.</i>"),
        ("SOP-05: Resolving the Incident (Incident Management)", "1. Return to Incident Management (/incidents).<br/>2. Once investigation is COMPLETED, click 'Resolve Incident'.<br/>3. The resolution summary automatically adopts the analyst's manual conclusion from the completed investigation.<br/>4. Confirm resolution: incident status updates to RESOLVED and resolved_at is stamped."),
        ("SOP-06: Closing an Incident (Incident Management)", "1. Select the RESOLVED incident in Incident Management.<br/>2. Review final post-mortem and verify device health.<br/>3. Click 'Close Incident' (or tell Zuka: <code>close incident &lt;ID&gt;</code>).<br/>4. Status updates to CLOSED and the incident is archived permanently."),
        ("SOP-07: Generating & Printing Reports (Reports)", "1. Navigate to Reports (/reports).<br/>2. Select report type (Incident Report, Alert Report, Executive Summary, Detection XAI) or pick a stored report.<br/>3. Click 'Print': uses isolated print CSS to print directly to clean white paper sheets without any website dark headers or sidebars."),
    ]

    for title, steps in sops:
        story.append(Paragraph(f"<b>{title}</b>", styles["h3"]))
        story.append(Paragraph(steps, styles["body"]))
        story.append(Spacer(1, 2 * mm))

    story.append(Spacer(1, 4 * mm))

    # =========================================================================
    # SECTION 7: ASSISTANT ARCHITECTURE & COMMAND PALETTE
    # =========================================================================
    story.append(Paragraph("7. Assistant Architecture, Command Palette & UI Primitives", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceAfter=5))
    story.append(
        Paragraph(
            "<b>Dual-Engine Architecture:</b> Queries pass through a sub-5ms deterministic rule-based parser. "
            "If no pattern matches, the query safely falls back to local Ollama (<code>qwen2.5:3b</code>) using grounded database tool calling. "
            "Destructive actions (e.g. user deletion) generate a <b>60-second cryptographic confirmation token</b> requiring explicit human confirmation.",
            styles["body"],
        )
    )

    cmd_rows = [
        [Paragraph("COMMAND", styles["table_header"]), Paragraph("CATEGORY", styles["table_header"]), Paragraph("DESCRIPTION & BEHAVIOR", styles["table_header"])],
        [Paragraph("show alert &lt;id&gt;", styles["code_block"]), Paragraph("Alerts", styles["table_cell"]), Paragraph("Inspects detailed alert flow, ports, confidence, and status.", styles["table_cell"])],
        [Paragraph("list alerts", styles["code_block"]), Paragraph("Alerts", styles["table_cell"]), Paragraph("Displays table of 8 most recent threat detections.", styles["table_cell"])],
        [Paragraph("list critical alerts", styles["code_block"]), Paragraph("Alerts", styles["table_cell"]), Paragraph("Filters alerts where severity is CRITICAL.", styles["table_cell"])],
        [Paragraph("acknowledge alert &lt;id&gt;", styles["code_block"]), Paragraph("Alerts", styles["table_cell"]), Paragraph("Marks alert ACKNOWLEDGED; unlocks investigation dossier.", styles["table_cell"])],
        [Paragraph("resolve alert &lt;id&gt;", styles["code_block"]), Paragraph("Alerts", styles["table_cell"]), Paragraph("Marks alert status as RESOLVED.", styles["table_cell"])],
        [Paragraph("dismiss alert &lt;id&gt;", styles["code_block"]), Paragraph("Alerts", styles["table_cell"]), Paragraph("Flags alert as FALSE_POSITIVE.", styles["table_cell"])],
        [Paragraph("escalate alert &lt;id&gt;", styles["code_block"]), Paragraph("Alerts", styles["table_cell"]), Paragraph("Promotes alert into a formal security incident.", styles["table_cell"])],
        [Paragraph("show incident &lt;id&gt;", styles["code_block"]), Paragraph("Incidents", styles["table_cell"]), Paragraph("Displays incident triage record, severity, owner, and notes.", styles["table_cell"])],
        [Paragraph("list incidents", styles["code_block"]), Paragraph("Incidents", styles["table_cell"]), Paragraph("Lists all active security cases in an ActionTable.", styles["table_cell"])],
        [Paragraph("list open incidents", styles["code_block"]), Paragraph("Incidents", styles["table_cell"]), Paragraph("Filters incidents currently in OPEN status.", styles["table_cell"])],
        [Paragraph("investigate incident &lt;id&gt;", styles["code_block"]), Paragraph("Incidents", styles["table_cell"]), Paragraph("Transitions incident to INVESTIGATING and assigns analyst.", styles["table_cell"])],
        [Paragraph("resolve incident &lt;id&gt;", styles["code_block"]), Paragraph("Incidents", styles["table_cell"]), Paragraph("Transitions incident to RESOLVED (requires summary).", styles["table_cell"])],
        [Paragraph("list users", styles["code_block"]), Paragraph("Admin", styles["table_cell"]), Paragraph("Lists registered user accounts and authorization status.", styles["table_cell"])],
        [Paragraph("approve user &lt;id&gt;", styles["code_block"]), Paragraph("Admin", styles["table_cell"]), Paragraph("Authorizes pending analyst account (is_active=True).", styles["table_cell"])],
        [Paragraph("deactivate user &lt;id&gt;", styles["code_block"]), Paragraph("Admin", styles["table_cell"]), Paragraph("Immediately suspends user login access.", styles["table_cell"])],
        [Paragraph("delete user &lt;id&gt;", styles["code_block"]), Paragraph("Admin", styles["table_cell"]), Paragraph("Prompts for safety confirmation before permanent removal.", styles["table_cell"])],
        [Paragraph("system status", styles["code_block"]), Paragraph("System", styles["table_cell"]), Paragraph("Checks live PostgreSQL health, table counts, and telemetry.", styles["table_cell"])],
        [Paragraph("dashboard stats", styles["code_block"]), Paragraph("System", styles["table_cell"]), Paragraph("Summary of active KPI metrics overview.", styles["table_cell"])],
        [Paragraph("help", styles["code_block"]), Paragraph("General", styles["table_cell"]), Paragraph("Displays categorized interactive command cards.", styles["table_cell"])],
    ]
    t_cmd = Table(cmd_rows, colWidths=[42 * mm, 24 * mm, 116 * mm])
    t_cmd.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_cmd)
    story.append(Spacer(1, 5 * mm))

    # =========================================================================
    # SECTION 8: COMPREHENSIVE FREQUENTLY ASKED QUESTIONS (FAQS)
    # =========================================================================
    story.append(Paragraph("8. Comprehensive Frequently Asked Questions (FAQs)", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceAfter=5))

    faqs = [
        ("Q1: What is the ZUKA SOC Platform?", "ZUKA is an enterprise AI-driven Security Operations Center platform designed specifically to detect, diagnose, investigate, and triage network attacks targeting smart devices and IoT environments."),
        ("Q2: Who is Zuka the Assistant?", "Zuka is the platform's AI operations co-pilot. Zuka executes database queries, inspects alerts, triages incidents, logs analyst notes, checks health, and guides analysts through SOPs."),
        ("Q3: Does ZUKA send our telemetry or packet data to external cloud APIs?", "No. ZUKA is engineered for 100% on-premises local privacy. The backend, database, XGBoost inference engine, and Ollama LLM execute strictly on localhost. No packet data or logs are ever transmitted to third-party clouds."),
        ("Q4: Why can't newly registered users log in immediately?", "All newly registered accounts default to is_active = False. An administrator must approve the account via the User Management panel (/users) or via the assistant command 'approve user <ID>' before login is permitted."),
        ("Q5: How is alert severity calculated?", "Severity is determined directly from model prediction confidence: CRITICAL (>=90% or severe volumetric attack), HIGH (75-89%), MEDIUM (55-74%), LOW (<55%), and INFO (verified benign flows)."),
        ("Q6: What does Explainable AI (TreeSHAP) show me in an alert?", "TreeSHAP computes the exact mathematical contribution of each network flow feature toward the model's classification, demonstrating why traffic was flagged and allowing analysts to confirm true positives."),
        ("Q7: How do I distinguish legitimate high-definition video streaming from a DoS flood?", "Legitimate video streaming features high payload bytes (dst_bytes), balanced TCP ACKs, and steady packet pacing. A DoS flood features abnormal packet rates with minimal or zero payload bytes and tiny inter-arrival times. The XGBoost model evaluates combinations of flow_packet_rate, dst_bytes, and src_iat_mean_sec to eliminate false positives."),
        ("Q8: Why is the 'Start Investigation' button locked on an incident?", "The linked alert has not been acknowledged yet. ZUKA enforces the operational rule that an alert must be in ACKNOWLEDGED status before an investigation dossier can be created."),
        ("Q9: What happens when an investigation is started?", "The system creates an investigation dossier (INV-...), stamps started_at, assigns the current analyst, and updates incident status to INVESTIGATING."),
        ("Q10: What is required before an incident can be marked RESOLVED?", "The incident's investigation dossier must be completed with forensic notes and a final conclusion. The analyst must then provide a resolution summary explaining containment."),
        ("Q11: How do Escalation Levels work?", "Levels range from Level 0 (normal triage) to Level 3 (critical management escalation). Incidents involving confirmed breaches, root-level compromises, or active botnets escalate to engage senior engineers."),
        ("Q12: How are user passwords protected?", "Passwords are never stored in plaintext. They are cryptographically hashed using passlib with industry-standard bcrypt or Argon2 hashing algorithms with unique salts."),
        ("Q13: How do session revocations and 2FA work?", "Operators can view active sessions in Settings (/settings) and remotely revoke unauthorized device tokens. Operators can also enable Time-based One-Time Password (TOTP) 2FA."),
        ("Q14: What happens if an administrator tries to delete their own account?", "The platform includes an explicit safety restriction preventing administrators from deleting or deactivating their own active account, preventing administrative lockout."),
        ("Q15: Why does deleting a user require a confirmation token?", "User deletion is permanent and revokes all active sessions. To prevent accidental clicks, the assistant issues a 60-second confirmation token requiring explicit confirmation."),
        ("Q16: What happens if Ollama is not running on localhost:11434?", "The assistant automatically falls back to its deterministic rule-based parser and direct database tools. Core operations continue functioning seamlessly in sub-5ms."),
        ("Q17: How do I verify live system and database health?", "Tell Zuka: 'system status' or navigate to /api/health. The system verifies PostgreSQL connectivity, table record counts, and active telemetry feeds."),
    ]

    for q, a in faqs:
        story.append(Paragraph(q, styles["faq_q"]))
        story.append(Paragraph(a, styles["faq_a"]))

    story.append(Spacer(1, 5 * mm))

    # =========================================================================
    # SECTION 9: ASSISTANT SYSTEM PROMPT & BOUNDARIES
    # =========================================================================
    story.append(Paragraph("9. Assistant System Prompt & Operating Boundaries", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceAfter=5))
    story.append(
        Paragraph(
            "When integrating or fine-tuning an AI Assistant instance for the ZUKA SOC platform, "
            "apply the following operational directives and guardrails:",
            styles["body"],
        )
    )

    prompt_text = (
        "<b>SYSTEM PROMPT DIRECTIVES:</b><br/>"
        "1. <b>Zero Hallucination:</b> Derive all counts, timestamps, alert IDs, and incident statuses exclusively from verified database queries.<br/>"
        "2. <b>SOP Enforcement:</b> Require alerts to be ACKNOWLEDGED before investigations begin; require investigations to be COMPLETED before incident resolution.<br/>"
        "3. <b>Safety Confirmation:</b> Destructive actions (deleting users, revoking accounts) require explicit human confirmation tokens.<br/>"
        "4. <b>Defensive Boundary:</b> Strictly refuse any request to generate exploit code, craft malicious packets, or participate in attacks.<br/>"
        "5. <b>Concise Professionalism:</b> Maintain an authoritative SOC analyst tone formatted in clean markdown tables and cards."
    )
    story.append(make_callout(prompt_text, styles, title="CORE ASSISTANT GUARDRAILS", border_color="#0F172A", bg_color="#F8FAFC"))

    # Build the PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully built at: {output_path}")


if __name__ == "__main__":
    import shutil
    out_dir = os.path.join(os.getcwd(), "docs")
    os.makedirs(out_dir, exist_ok=True)
    target_pdf = os.path.join(out_dir, "ZUKA_SOC_Master_Knowledge_Base.pdf")
    build_knowledge_base_pdf(target_pdf)
    root_pdf = os.path.join(os.getcwd(), "ZUKA_SOC_Master_Knowledge_Base.pdf")
    shutil.copyfile(target_pdf, root_pdf)
    print(f"Master Knowledge Base copied to: {root_pdf}")
