from __future__ import annotations

import hashlib
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically stamp running header, footer, and accurate total page count."""

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
            self.line(margin_x, height - 10 * mm, width - margin_x, height - 10 * mm)

            self.setFont("Helvetica-Bold", 7.2)
            self.setFillColor(colors.HexColor("#0284C7"))
            self.drawString(margin_x, height - 8 * mm, "ZUKA SOC INTELLIGENCE REPORT")

            self.setFont("Helvetica", 7.2)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawRightString(
                width - margin_x,
                height - 8 * mm,
                "CLASSIFICATION: TLP:AMBER // SOC LEVEL-3 CONFIDENTIAL",
            )

        # Running Footer (all pages)
        footer_y = 8 * mm
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.6)
        self.line(margin_x, footer_y + 4 * mm, width - margin_x, footer_y + 4 * mm)

        self.setFont("Helvetica-Bold", 6.8)
        self.setFillColor(colors.HexColor("#0F2744"))
        self.drawString(margin_x, footer_y, "ZUKA SECURITY OPERATIONS CENTER")

        self.setFont("Helvetica", 6.8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(
            margin_x + 55 * mm,
            footer_y,
            "• FORENSIC DOSSIER & AI THREAT GOVERNANCE RECORD",
        )

        self.setFont("Helvetica-Bold", 7.2)
        self.setFillColor(colors.HexColor("#0F2744"))
        self.drawRightString(
            width - margin_x,
            footer_y,
            f"Page {self._pageNumber} of {total_pages}",
        )

        self.restoreState()


def _text(value: Any) -> str:
    if value is None or value == "":
        return "Not available"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (dict, list)):
        return str(value)
    return str(value)


def _paragraph(value: Any, style: ParagraphStyle) -> Paragraph:
    safe = _text(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe = safe.replace("\n", "<br/>")
    return Paragraph(safe, style)


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "ZukaTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=colors.HexColor("#0F172A"),
            alignment=0,
        ),
        "header_brand": ParagraphStyle(
            "ZukaHeaderBrand",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0284C7"),
        ),
        "header_subtitle": ParagraphStyle(
            "ZukaHeaderSub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8.5,
            textColor=colors.HexColor("#64748B"),
        ),
        "header_meta": ParagraphStyle(
            "ZukaHeaderMeta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=6.8,
            leading=9.5,
            textColor=colors.HexColor("#1E293B"),
            alignment=2,
        ),
        "section_title": ParagraphStyle(
            "ZukaSectionTitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#0F172A"),
        ),
        "kpi_val": ParagraphStyle(
            "ZukaKPIVal",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#0F2744"),
            alignment=1,
        ),
        "kpi_lbl": ParagraphStyle(
            "ZukaKPILbl",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.5,
            leading=8.5,
            textColor=colors.HexColor("#64748B"),
            alignment=1,
        ),
        "callout": ParagraphStyle(
            "ZukaCallout",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.2,
            leading=10.5,
            textColor=colors.HexColor("#1E293B"),
        ),
        "tbl_hdr": ParagraphStyle(
            "ZukaTblHdr",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=colors.white,
        ),
        "tbl_hdr_r": ParagraphStyle(
            "ZukaTblHdrR",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=colors.white,
            alignment=2,
        ),
        "label": ParagraphStyle(
            "ZukaLabel",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9.5,
            textColor=colors.HexColor("#0F2744"),
        ),
        "body": ParagraphStyle(
            "ZukaBody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9.5,
            textColor=colors.HexColor("#1E293B"),
        ),
        "body_bold": ParagraphStyle(
            "ZukaBodyBold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9.5,
            textColor=colors.HexColor("#0F172A"),
        ),
        "body_mono": ParagraphStyle(
            "ZukaBodyMono",
            parent=base["Normal"],
            fontName="Courier-Bold",
            fontSize=6.8,
            leading=9,
            textColor=colors.HexColor("#0284C7"),
        ),
        "body_r": ParagraphStyle(
            "ZukaBodyR",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9.5,
            textColor=colors.HexColor("#1E293B"),
            alignment=2,
        ),
        "small": ParagraphStyle(
            "ZukaSmall",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8.5,
            textColor=colors.HexColor("#64748B"),
        ),
    }


def _severity_html(severity: Any) -> str:
    sev = str(severity or "").upper()
    if "CRIT" in sev:
        return '<font color="#DC2626"><b>● CRITICAL</b></font>'
    if "HIGH" in sev:
        return '<font color="#EA580C"><b>● HIGH</b></font>'
    if "MED" in sev:
        return '<font color="#D97706"><b>● MEDIUM</b></font>'
    if "LOW" in sev:
        return '<font color="#2563EB"><b>● LOW</b></font>'
    if "INFO" in sev or "BENIGN" in sev:
        return '<font color="#059669"><b>● INFO / BENIGN</b></font>'
    return f"<b>{sev}</b>" if sev else "Not available"


def _status_html(status: Any) -> str:
    st = str(status or "").upper()
    if "CLOSE" in st or "RESOLV" in st or "COMPLET" in st:
        return '<font color="#059669"><b>✔ RESOLVED / CLOSED</b></font>'
    if "ACTIVE" in st or "OPEN" in st:
        return '<font color="#DC2626"><b>⚡ ACTIVE / OPEN</b></font>'
    if "PROGRESS" in st or "INVESTIGAT" in st:
        return '<font color="#D97706"><b>⏳ IN PROGRESS</b></font>'
    return f"<b>{st}</b>" if st else "Not available"


def _section(title: str, styles: dict[str, ParagraphStyle], tag: str = "■") -> list[Any]:
    content = f"<font color='#0284C7'><b>{tag}</b></font> <font color='#0F172A'><b>{title.upper()}</b></font>"
    table = Table(
        [[Paragraph(content, styles["section_title"])]],
        colWidths=[182 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor("#0284C7")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [
        Spacer(1, 2 * mm),
        table,
        Spacer(1, 1.5 * mm),
    ]


def _build_header_banner(
    title: str,
    ref_id: str,
    gen_time: str,
    classification: str = "TLP:AMBER // SOC LEVEL-3",
    styles: dict[str, ParagraphStyle] | None = None,
) -> list[Any]:
    styles = styles or _build_styles()
    left_cell = [
        Paragraph("◆ ZUKA SECURITY OPERATIONS CENTER", styles["header_brand"]),
        Paragraph("ENTERPRISE CYBERSECURITY & AUTONOMOUS FORENSIC INTELLIGENCE PLATFORM", styles["header_subtitle"]),
        Spacer(1, 1 * mm),
        Paragraph(title, styles["title"]),
    ]

    right_cell = [
        Paragraph(f'<font color="#DC2626"><b>{classification}</b></font>', styles["header_meta"]),
        Paragraph(f'CASE REF: <b>{ref_id}</b>', styles["header_meta"]),
        Paragraph(f'GENERATED: <b>{gen_time}</b>', styles["header_meta"]),
        Paragraph('<font color="#059669">● AUDIT STATUS: <b>AUTHENTICATED</b></font>', styles["header_meta"]),
    ]

    header_table = Table([[left_cell, right_cell]], colWidths=[122 * mm, 60 * mm])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    bar_data = [["", ""]]
    bar_table = Table(bar_data, colWidths=[124 * mm, 58 * mm], rowHeights=[1.8 * mm])
    bar_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#0284C7")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#10B981")),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    return [
        header_table,
        Spacer(1, 1 * mm),
        bar_table,
        Spacer(1, 2 * mm),
    ]


def _two_column_matrix(
    left_title: str,
    left_rows: list[tuple[str, Any]],
    right_title: str,
    right_rows: list[tuple[str, Any]],
    styles: dict[str, ParagraphStyle],
) -> Table:
    def _make_subtable(title: str, rows: list[tuple[str, Any]]) -> Table:
        data = [[Paragraph(f"<b>{title.upper()}</b>", styles["tbl_hdr"]), ""]]
        for key, val in rows:
            k_lower = key.lower()
            val_str = _text(val)
            if "severity" in k_lower:
                val_p = Paragraph(_severity_html(val), styles["body"])
            elif "status" in k_lower:
                val_p = Paragraph(_status_html(val), styles["body"])
            elif "confidence" in k_lower:
                val_p = Paragraph(f"<b>{val_str}</b>", styles["body_bold"])
            elif "ip" in k_lower or "port" in k_lower or "id" in k_lower:
                val_p = Paragraph(f"<b>{val_str}</b>", styles["body_mono"] if ("ip" in k_lower or "id" in k_lower) else styles["body"])
            else:
                val_p = _paragraph(val, styles["body"])
            data.append([_paragraph(key, styles["label"]), val_p])

        tbl = Table(data, colWidths=[32 * mm, 58 * mm])
        t_styles = [
            ("SPAN", (0, 0), (1, 0)),
            ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#0F2744")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]
        for r in range(1, len(data)):
            bg = colors.HexColor("#FFFFFF") if r % 2 == 1 else colors.HexColor("#F8FAFC")
            t_styles.append(("BACKGROUND", (1, r), (1, r), bg))
            t_styles.append(("BACKGROUND", (0, r), (0, r), colors.HexColor("#F1F5F9")))
        tbl.setStyle(TableStyle(t_styles))
        return tbl

    left_tbl = _make_subtable(left_title, left_rows)
    right_tbl = _make_subtable(right_title, right_rows)

    wrapper = Table([[left_tbl, "", right_tbl]], colWidths=[90 * mm, 2 * mm, 90 * mm])
    wrapper.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return wrapper


def _executive_briefing_card(
    summary_text: str,
    status_val: str,
    severity_val: str,
    priority_val: str,
    styles: dict[str, ParagraphStyle],
) -> Table:
    briefing_p = Paragraph(f"<b>EXECUTIVE ASSESSMENT & BRIEFING:</b><br/>{summary_text}", styles["callout"])

    status_badge_data = [
        [Paragraph("CASE STATUS", styles["kpi_lbl"]), Paragraph(_status_html(status_val), styles["body"])],
        [Paragraph("SEVERITY", styles["kpi_lbl"]), Paragraph(_severity_html(severity_val), styles["body"])],
        [Paragraph("PRIORITY", styles["kpi_lbl"]), Paragraph(f"<b>{priority_val}</b>", styles["body_bold"])],
    ]
    badge_tbl = Table(status_badge_data, colWidths=[22 * mm, 34 * mm])
    badge_tbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
                ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#FFFFFF")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    card = Table([[briefing_p, badge_tbl]], colWidths=[124 * mm, 58 * mm])
    card.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#F8FAFC")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#EFF6FF")),
                ("LINELEFT", (0, 0), (0, 0), 3, colors.HexColor("#0284C7")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return card


def _compact_shap_table(explanation: Any, styles: dict[str, ParagraphStyle]) -> Table | None:
    if not isinstance(explanation, dict):
        return None
    contributions = explanation.get("top_contributions") or []
    if not isinstance(contributions, list) or len(contributions) == 0:
        return None

    rows = [[
        Paragraph("FEATURE ATTRIBUTION", styles["tbl_hdr"]),
        Paragraph("IMPACT DIRECTION", styles["tbl_hdr"]),
        Paragraph("SHAP VALUE", styles["tbl_hdr_r"]),
        Paragraph("OBSERVED VALUE", styles["tbl_hdr_r"]),
    ]]

    for item in contributions[:4]:
        if not isinstance(item, dict):
            continue
        raw_dir = str(item.get("direction") or item.get("impact") or "Not available")
        if any(w in raw_dir.lower() for w in ["attack", "increase", "positive", "+"]):
            dir_html = f'<font color="#DC2626"><b>▲ {raw_dir}</b></font>'
        elif any(w in raw_dir.lower() for w in ["benign", "decrease", "negative", "-"]):
            dir_html = f'<font color="#059669"><b>▼ {raw_dir}</b></font>'
        else:
            dir_html = f"<b>{raw_dir}</b>"

        rows.append(
            [
                _paragraph(item.get("feature"), styles["body_mono"]),
                Paragraph(dir_html, styles["body"]),
                _paragraph(item.get("shap_value"), styles["body_r"]),
                _paragraph(item.get("feature_value"), styles["body_r"]),
            ]
        )

    tbl = Table(rows, colWidths=[65 * mm, 37 * mm, 35 * mm, 45 * mm])
    t_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2744")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]
    for r in range(1, len(rows)):
        bg = colors.HexColor("#FFFFFF") if r % 2 == 1 else colors.HexColor("#F8FAFC")
        t_styles.append(("BACKGROUND", (0, r), (-1, r), bg))
    tbl.setStyle(TableStyle(t_styles))
    return tbl


def _compact_actions_table(actions: list[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> Table | None:
    if not actions:
        return None

    rows = [[
        Paragraph("TIMESTAMP", styles["tbl_hdr"]),
        Paragraph("ACTION TYPE", styles["tbl_hdr"]),
        Paragraph("OPERATIONAL DESCRIPTION", styles["tbl_hdr"]),
        Paragraph("STATUS / RESULT", styles["tbl_hdr"]),
    ]]

    for act in actions[:4]:
        act_type = str(act.get("action_type") or "ACTION").upper()
        act_p = Paragraph(f'<font color="#0284C7"><b>{act_type}</b></font>', styles["body"])
        rows.append([
            _paragraph(act.get("created_at"), styles["body"]),
            act_p,
            _paragraph(act.get("description"), styles["body"]),
            _paragraph(act.get("result"), styles["body_bold"]),
        ])

    tbl = Table(rows, colWidths=[38 * mm, 38 * mm, 74 * mm, 32 * mm])
    t_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2744")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]
    for r in range(1, len(rows)):
        bg = colors.HexColor("#FFFFFF") if r % 2 == 1 else colors.HexColor("#F8FAFC")
        t_styles.append(("BACKGROUND", (0, r), (-1, r), bg))
    tbl.setStyle(TableStyle(t_styles))
    return tbl


def _forensic_footer_seal(styles: dict[str, ParagraphStyle], ref_id: str = "SOC-REF") -> list[Any]:
    checksum = hashlib.sha256(ref_id.encode("utf-8")).hexdigest()[:16].upper()
    notice = Paragraph(
        "<b>REPORT INTEGRITY & MACHINE LEARNING GOVERNANCE RECORD:</b><br/>"
        "This official forensic document is compiled from immutable PostgreSQL records "
        "and real-time ML inference logs within ZUKA SOC. Model predictions and SHAP feature "
        "attributions represent probabilistic machine learning decisions corroborated by active "
        "human security analyst oversight under ISO/IEC 27001 & NIST SP 800-61 Rev. 2 standards.",
        styles["small"],
    )

    seal_box = [
        Paragraph('<font color="#0F2744"><b>DIGITAL FORENSIC SEAL</b></font>', styles["kpi_lbl"]),
        Paragraph('<font color="#059669"><b>✔ CERTIFIED SOC-3 RECORD</b></font>', styles["kpi_lbl"]),
        Paragraph(f'<font color="#0284C7">HMAC: <b>{checksum}</b></font>', styles["kpi_lbl"]),
    ]

    box_table = Table([[notice, seal_box]], colWidths=[126 * mm, 56 * mm])
    box_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#F8FAFC")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#EFF6FF")),
                ("LINELEFT", (1, 0), (1, 0), 1, colors.HexColor("#0284C7")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    return [
        Spacer(1, 2 * mm),
        box_table,
    ]


def generate_pdf(report: dict[str, Any]) -> bytes:
    report_type = str(report.get("report_type") or "REPORT").upper()
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"ZUKA SOC — {report_type.replace('_', ' ')}",
        author="ZUKA Security Operations Center",
    )

    styles = _build_styles()
    story: list[Any] = []

    entity_id = (
        report.get("investigation", {}).get("investigation_id")
        or report.get("incident", {}).get("incident_id")
        or report.get("alert", {}).get("alert_id")
        or report.get("alert_id")
        or report.get("report_id")
        or "SOC-TELEMETRY"
    )
    gen_time = _text(report.get("generated_at"))
    if len(gen_time) > 19:
        gen_time = gen_time[:19].replace("T", " ")

    clean_type_title = report_type.replace("_", " ").title()
    if clean_type_title.startswith("Soc"):
        clean_type_title = "SOC Executive Security Summary"
    elif "Incident" in clean_type_title:
        clean_type_title = "Incident Forensic Dossier"
    elif "Alert" in clean_type_title:
        clean_type_title = "Threat Detection Alert Report"
    elif "Investigation" in clean_type_title:
        clean_type_title = "SOC Investigation Case Dossier"
    elif "Detection Xai" in clean_type_title:
        clean_type_title = "XAI Machine Learning Attribution Audit"

    story.extend(
        _build_header_banner(
            title=clean_type_title,
            ref_id=str(entity_id),
            gen_time=gen_time,
            classification="TLP:AMBER // SOC LEVEL-3",
            styles=styles,
        )
    )

    if report_type == "SOC_SUMMARY":
        totals = report.get("totals") or {}

        # Executive KPI Cards Grid
        story.extend(_section("High-Level Operational Metrics", styles, "1"))
        kpi_cells = [
            [
                Paragraph(f"{totals.get('alerts', 0):,}", styles["kpi_val"]),
                Paragraph("TOTAL ALERTS", styles["kpi_lbl"]),
            ],
            [
                Paragraph(f"{totals.get('incidents', 0):,}", styles["kpi_val"]),
                Paragraph("SECURITY INCIDENTS", styles["kpi_lbl"]),
            ],
            [
                Paragraph(f"{totals.get('investigations', 0):,}", styles["kpi_val"]),
                Paragraph("INVESTIGATIONS", styles["kpi_lbl"]),
            ],
            [
                Paragraph(f"{totals.get('network_events', 0):,}", styles["kpi_val"]),
                Paragraph("NETWORK EVENTS", styles["kpi_lbl"]),
            ],
        ]
        kpi_table = Table([[kpi_cells[0], kpi_cells[1], kpi_cells[2], kpi_cells[3]]], colWidths=[45.5 * mm] * 4)
        kpi_table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("LINEBEFORE", (0, 0), (-1, -1), 2.5, colors.HexColor("#0284C7")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(kpi_table)

        summary_text = (
            report.get("summary")
            or "Automated high-level situational awareness telemetry indicating current detection pipeline health, "
            "attack categorization metrics, and human analyst triage velocity across the enterprise network."
        )
        callout_tbl = Table(
            [[Paragraph(f"<b>EXECUTIVE ASSESSMENT:</b> {summary_text}", styles["callout"])]],
            colWidths=[182 * mm],
        )
        callout_tbl.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
                    ("LINELEFT", (0, 0), (0, -1), 3, colors.HexColor("#10B981")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(Spacer(1, 2.5 * mm))
        story.append(callout_tbl)

        distributions = [
            ("Threat / Attack Classification", "attack_distribution", "2"),
            ("Severity Stratification", "severity_distribution", "3"),
            ("Alert Triage Status", "alert_status_distribution", "4"),
            ("Incident Lifecycle Status", "incident_status_distribution", "5"),
            ("Investigation Triage Status", "investigation_status_distribution", "6"),
        ]

        for title, key, sec_num in distributions:
            values = report.get(key) or {}
            if not values:
                continue

            story.extend(_section(title, styles, sec_num))
            total_items = sum(values.values()) if values else 1
            rows = [
                [
                    Paragraph("CATEGORY / CLASSIFICATION", styles["tbl_hdr"]),
                    Paragraph("VOLUME COUNT", styles["tbl_hdr_r"]),
                    Paragraph("DISTRIBUTION SHARE", styles["tbl_hdr_r"]),
                ]
            ]
            for cat, count in values.items():
                pct = (count / total_items * 100) if total_items > 0 else 0
                cat_formatted = _severity_html(cat) if "severity" in key else (
                    _status_html(cat) if "status" in key else f"<b>{cat}</b>"
                )
                rows.append(
                    [
                        Paragraph(cat_formatted, styles["body"]),
                        Paragraph(f"{count:,}", styles["body_r"]),
                        Paragraph(f"{pct:.1f}%", styles["body_r"]),
                    ]
                )

            dist_table = Table(rows, colWidths=[102 * mm, 40 * mm, 40 * mm])
            t_styles = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2744")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]
            for r in range(1, len(rows)):
                bg = colors.HexColor("#FFFFFF") if r % 2 == 1 else colors.HexColor("#F8FAFC")
                t_styles.append(("BACKGROUND", (0, r), (-1, r), bg))

            dist_table.setStyle(TableStyle(t_styles))
            story.append(dist_table)

    elif report_type == "DETECTION_XAI_REPORT":
        conf_val = report.get("confidence")
        conf_str = f"{float(conf_val) * 100:.2f}% (High Confidence Inference)" if conf_val is not None else "Not available"

        story.append(
            _executive_briefing_card(
                summary_text="Deep Learning and TreeSHAP attribution verification confirming primary packet indicators governing the detection model classification.",
                status_val=str(report.get("status") or "ACTIVE"),
                severity_val=str(report.get("severity") or "HIGH"),
                priority_val="HIGH FIDELITY",
                styles=styles,
            )
        )

        story.extend(_section("ML Detection Assessment & Metadata", styles, "1"))
        story.append(
            _two_column_matrix(
                left_title="Detection Attributes",
                left_rows=[
                    ("Alert Identifier", report.get("alert_id")),
                    ("Attack Class", report.get("predicted_class")),
                    ("Inference Confidence", conf_str),
                    ("Assessed Severity", report.get("severity")),
                ],
                right_title="Model Governance",
                right_rows=[
                    ("Alert Status", report.get("status")),
                    ("Network Sensor", report.get("capture_source")),
                    ("Explainer Engine", "TreeSHAP Local Attribution"),
                    ("Dataset Reference", "CIC-IDS2017 Flow Benchmark"),
                ],
                styles=styles,
            )
        )

        explanation = report.get("xai_explanation")
        shap_tbl = _compact_shap_table(explanation, styles)
        if shap_tbl:
            story.extend(_section("Explainable AI (TreeSHAP) Feature Drivers", styles, "2"))
            story.append(shap_tbl)

    elif report_type == "ALERT_REPORT":
        alert = report.get("alert") or {}
        conf_val = alert.get("confidence")
        conf_str = f"{float(conf_val) * 100:.2f}% (Deep Learning Classifier)" if conf_val is not None else "Not available"

        briefing_text = (
            f"Autonomous network sensor '{_text(alert.get('capture_source'))}' identified a high-confidence "
            f"threat signature matching '{_text(alert.get('predicted_class'))}' traffic from source IP "
            f"'{_text(alert.get('source_ip'))}' to internal target '{_text(alert.get('destination_ip'))}'."
        )

        story.append(
            _executive_briefing_card(
                summary_text=briefing_text,
                status_val=str(alert.get("status") or "ACTIVE"),
                severity_val=str(alert.get("severity") or "HIGH"),
                priority_val="P1 - IMMEDIATE",
                styles=styles,
            )
        )

        story.extend(_section("Threat Detection Telemetry & Vector Analysis", styles, "1"))
        story.append(
            _two_column_matrix(
                left_title="Detection Metadata",
                left_rows=[
                    ("Alert ID", alert.get("alert_id")),
                    ("Attack Class", alert.get("predicted_class")),
                    ("Model Confidence", conf_str),
                    ("Calculated Severity", alert.get("severity")),
                    ("Triage Status", alert.get("status")),
                    ("Detected At", alert.get("detected_at")),
                ],
                right_title="Network Vector",
                right_rows=[
                    ("Source IP / Port", f"{alert.get('source_ip')} : {alert.get('source_port')}"),
                    ("Target IP / Port", f"{alert.get('destination_ip')} : {alert.get('destination_port')}"),
                    ("Transport Protocol", alert.get("protocol")),
                    ("Capture Sensor", alert.get("capture_source")),
                    ("Dataset Benchmark", alert.get("dataset_name") or "CIC-IDS2017 Flow"),
                ],
                styles=styles,
            )
        )

        shap_tbl = _compact_shap_table(alert.get("xai_explanation"), styles)
        if shap_tbl:
            story.extend(_section("Explainable AI (TreeSHAP) Feature Attribution", styles, "2"))
            story.append(shap_tbl)

    elif report_type == "INVESTIGATION_REPORT":
        investigation = report.get("investigation") or {}
        incident = report.get("incident") or {}
        alert = report.get("alert") or {}

        summary_text = (
            incident.get("description")
            or investigation.get("analyst_notes")
            or "Comprehensive multi-layered forensic investigation correlating live network telemetry, deep packet inspection, and audited containment actions."
        )

        story.append(
            _executive_briefing_card(
                summary_text=summary_text,
                status_val=str(investigation.get("status") or incident.get("status") or "INVESTIGATING"),
                severity_val=str(incident.get("severity") or alert.get("severity") or "CRITICAL"),
                priority_val=str(incident.get("priority") or "P1 - CRITICAL"),
                styles=styles,
            )
        )

        story.extend(_section("Forensic Case Profile & Correlated Threat Vector", styles, "1"))
        conf_val = alert.get("confidence")
        conf_str = f"{float(conf_val) * 100:.2f}% (TreeSHAP Corroborated)" if conf_val is not None else "Not available"

        story.append(
            _two_column_matrix(
                left_title="Case Profile & Governance",
                left_rows=[
                    ("Investigation ID", investigation.get("investigation_id")),
                    ("Correlated Incident", investigation.get("incident_id") or incident.get("incident_id")),
                    ("Incident Title", incident.get("title")),
                    ("Lifecycle Status", investigation.get("status")),
                    ("Assigned Lead", "Tier-2 SOC Forensic Investigator"),
                    ("Initiated Timestamp", investigation.get("started_at")),
                    ("Concluded Timestamp", investigation.get("completed_at")),
                ],
                right_title="Threat Telemetry & Attack Signature",
                right_rows=[
                    ("Correlated Alert", incident.get("alert_id") or alert.get("alert_id")),
                    ("Attack Class", alert.get("predicted_class")),
                    ("ML Confidence", conf_str),
                    ("Threat Severity", alert.get("severity") or incident.get("severity")),
                    ("Attacker IP / Port", f"{alert.get('source_ip')} : {alert.get('source_port')}"),
                    ("Target IP / Port", f"{alert.get('destination_ip')} : {alert.get('destination_port')}"),
                    ("Protocol & Sensor", f"{alert.get('protocol')} ({alert.get('capture_source')})"),
                ],
                styles=styles,
            )
        )

        story.extend(_section("Lead Investigator Findings & Remediation Verdict", styles, "2"))
        notes_text = (
            investigation.get("analyst_notes")
            or "Active forensic inspection in progress. Packet telemetry and anomaly indicators analyzed."
        )
        notes_callout = Table(
            [[Paragraph(f"<b>LEAD INVESTIGATOR FORENSIC NOTES:</b><br/>{notes_text}", styles["callout"])]],
            colWidths=[182 * mm],
        )
        notes_callout.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("LINELEFT", (0, 0), (0, -1), 3, colors.HexColor("#0284C7")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(notes_callout)
        story.append(Spacer(1, 2 * mm))

        conclusion_text = (
            investigation.get("conclusion")
            or incident.get("resolution_summary")
            or "Formal forensic conclusion pending final remediation verification."
        )
        is_completed = str(investigation.get("status") or incident.get("status") or "").upper() in ["COMPLETED", "RESOLVED", "CLOSED"]
        conc_border = colors.HexColor("#10B981") if is_completed else colors.HexColor("#D97706")
        conc_bg = colors.HexColor("#F0FDF4") if is_completed else colors.HexColor("#FFFBEB")
        conc_badge = "VERIFIED CASE CONCLUSION & REMEDIATION VERDICT" if is_completed else "INTERIM TRIAGE FINDING"

        conc_callout = Table(
            [[Paragraph(f"<b>{conc_badge}:</b><br/>{conclusion_text}", styles["callout"])]],
            colWidths=[182 * mm],
        )
        conc_callout.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("BACKGROUND", (0, 0), (-1, -1), conc_bg),
                    ("LINELEFT", (0, 0), (0, -1), 3, conc_border),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(conc_callout)

        # TreeSHAP Attribution
        shap_tbl = _compact_shap_table(alert.get("xai_explanation"), styles)
        if shap_tbl:
            story.extend(_section("Explainable AI (TreeSHAP) Feature Drivers", styles, "3"))
            story.append(shap_tbl)

        # Audited Actions
        act_tbl = _compact_actions_table(report.get("analyst_actions") or [], styles)
        if act_tbl:
            story.extend(_section("Audited Human Analyst Actions Timeline", styles, "4"))
            story.append(act_tbl)

    else:
        # INCIDENT_REPORT
        incident = report.get("incident") or {}
        alert = report.get("alert") or {}
        investigation = report.get("investigation") or {}

        summary_text = (
            incident.get("description")
            or "Post-incident technical dossier detailing correlated detection indicators, risk severity ratings, and lifecycle status."
        )

        story.append(
            _executive_briefing_card(
                summary_text=summary_text,
                status_val=str(incident.get("status") or "RESOLVED"),
                severity_val=str(incident.get("severity") or "CRITICAL"),
                priority_val=str(incident.get("priority") or "P1 - CRITICAL"),
                styles=styles,
            )
        )

        story.extend(_section("Incident Case Profile & Correlated Threat Vector", styles, "1"))
        conf_val = alert.get("confidence")
        conf_str = f"{float(conf_val) * 100:.2f}% (TreeSHAP Corroborated)" if conf_val is not None else "Not available"

        story.append(
            _two_column_matrix(
                left_title="Incident Profile & Governance",
                left_rows=[
                    ("Incident ID", incident.get("incident_id")),
                    ("Correlated Alert", incident.get("alert_id")),
                    ("Incident Title", incident.get("title")),
                    ("Assigned Priority", incident.get("priority")),
                    ("Assessed Severity", incident.get("severity")),
                    ("Lifecycle Status", incident.get("status")),
                    ("Opened Timestamp", incident.get("created_at")),
                    ("Resolved Timestamp", incident.get("resolved_at") or incident.get("closed_at")),
                ],
                right_title="Network Vector & Threat Telemetry",
                right_rows=[
                    ("Attack Signature", alert.get("predicted_class")),
                    ("Detection Confidence", conf_str),
                    ("Attacker IP / Port", f"{alert.get('source_ip')} : {alert.get('source_port')}"),
                    ("Target IP / Port", f"{alert.get('destination_ip')} : {alert.get('destination_port')}"),
                    ("Transport Protocol", alert.get("protocol")),
                    ("Detection Sensor", alert.get("capture_source")),
                    ("Dataset Reference", alert.get("dataset_name") or "CIC-IDS2017 Flow"),
                ],
                styles=styles,
            )
        )

        # Resolution / Notes
        res_summary = incident.get("resolution_summary") or investigation.get("conclusion")
        if res_summary or investigation.get("analyst_notes"):
            story.extend(_section("Remediation & Forensic Conclusion Summary", styles, "2"))
            if investigation.get("analyst_notes"):
                notes_callout = Table(
                    [[Paragraph(f"<b>LEAD INVESTIGATOR NOTES:</b><br/>{investigation.get('analyst_notes')}", styles["callout"])]],
                    colWidths=[182 * mm],
                )
                notes_callout.setStyle(
                    TableStyle(
                        [
                            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                            ("LINELEFT", (0, 0), (0, -1), 3, colors.HexColor("#0284C7")),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
                story.append(notes_callout)
                story.append(Spacer(1, 2 * mm))

            if res_summary:
                res_box = Table(
                    [[Paragraph(f"<b>FINAL POST-MORTEM RESOLUTION:</b><br/>{res_summary}", styles["callout"])]],
                    colWidths=[182 * mm],
                )
                res_box.setStyle(
                    TableStyle(
                        [
                            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
                            ("LINELEFT", (0, 0), (0, -1), 3, colors.HexColor("#10B981")),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
                story.append(res_box)

        # TreeSHAP Attribution
        shap_tbl = _compact_shap_table(alert.get("xai_explanation"), styles)
        if shap_tbl:
            story.extend(_section("Explainable AI (TreeSHAP) Feature Drivers", styles, "3"))
            story.append(shap_tbl)

        # Audited Actions
        act_tbl = _compact_actions_table(report.get("analyst_actions") or [], styles)
        if act_tbl:
            story.extend(_section("Audited Human Analyst Actions Timeline", styles, "4"))
            story.append(act_tbl)

    story.extend(_forensic_footer_seal(styles, ref_id=str(entity_id)))

    document.build(
        story,
        canvasmaker=NumberedCanvas,
    )

    return buffer.getvalue()
