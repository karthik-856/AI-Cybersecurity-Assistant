"""
Script to generate publication-grade, crisp, neat, and highly readable architecture
diagrams for an IEEE paper with medium-big legible typography.
Generates:
1. fig1_ieee_full_architecture.png & .pdf (Wide 2-Column System Architecture)
2. fig2_ieee_single_column_pipeline.png & .pdf (Vertical 1-Column Sequential Pipeline)
3. fig3_ieee_xai_decision_loop.png & .pdf (Explainability & Human-in-the-Loop Engine)
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

# IEEE Publication Typography & Styling
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.weight'] = 'normal'

OUTPUT_DIR = Path(r"c:\Users\admin\Downloads\AI-Cybersecurity-Assistant\docs\architecture")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# FIGURE 1: FULL SYSTEM ARCHITECTURE (WIDE 2-COLUMN FORMAT)
# Medium-Big readable typography, clean modern boxes, uncluttered layout
# ==============================================================================
def generate_fig1():
    fig, ax = plt.subplots(figsize=(15, 10.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Color Palette - Academic IEEE Clean
    c_bg = '#F8FAFC'
    c_blue = '#1E40AF'
    c_emerald = '#047857'
    c_amber = '#B45309'
    c_purple = '#6D28D9'
    c_slate = '#334155'
    c_red = '#B91C1C'

    def draw_card(x, y, w, h, title, subtitle, points, border_col, header_bg, title_col):
        # Card shadow/base
        shadow = patches.FancyBboxPatch((x+0.3, y-0.4), w, h, boxstyle='round,pad=0.2,rounding_size=1.2',
                                        facecolor='#E2E8F0', edgecolor='none')
        ax.add_patch(shadow)

        # Card container
        card = patches.FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.2,rounding_size=1.2',
                                     facecolor='#FFFFFF', edgecolor=border_col, linewidth=2.0)
        ax.add_patch(card)

        # Card Header Banner
        header = patches.FancyBboxPatch((x, y + h - 4.2), w, 4.2, boxstyle='round,pad=0.1,rounding_size=1.0',
                                        facecolor=header_bg, edgecolor=border_col, linewidth=1.2)
        ax.add_patch(header)

        # Header Title (Medium-Big & Bold)
        ax.text(x + w/2, y + h - 2.1, title, fontsize=12.5, fontweight='bold',
                color=title_col, ha='center', va='center')

        # Subtitle / Tag
        ax.text(x + w/2, y + h - 6.2, subtitle, fontsize=10.5, fontweight='bold',
                color='#1E293B', ha='center', va='center')

        # Bullet points / descriptions (Clean, readable 10pt)
        curr_y = y + h - 9.5
        for pt in points:
            ax.text(x + 2.0, curr_y, pt, fontsize=10.0, color='#475569', va='center')
            curr_y -= 3.0

    # --------------------------------------------------------------------------
    # LAYER LABELS & CONTAINERS
    # --------------------------------------------------------------------------
    def draw_tier_bg(y_b, h, label, color):
        tier = patches.FancyBboxPatch((1.5, y_b), 97, h, boxstyle='round,pad=0.3,rounding_size=1.5',
                                     facecolor=color, edgecolor='#CBD5E1', linewidth=1.5, linestyle='--')
        ax.add_patch(tier)
        lbl_box = patches.FancyBboxPatch((1.5, y_b + h - 3.8), 38, 3.8, boxstyle='round,pad=0.1,rounding_size=0.8',
                                        facecolor='#1E293B', edgecolor='none')
        ax.add_patch(lbl_box)
        ax.text(3.0, y_b + h - 1.9, label, fontsize=10.5, fontweight='bold', color='#FFFFFF', va='center')

    # TIER 1: INGESTION
    draw_tier_bg(80.5, 18, 'TIER 1: TELEMETRY INGESTION & FLOW EXTRACTION', '#F8FAFC')
    draw_card(4, 82, 28, 14, 'Traffic Ingestion Engine', 'High-Speed Stream Listener',
              ['• Live Interface Capture & PCAP Replay', '• Socket Buffer & Packet Normalizer'], '#64748B', '#F1F5F9', c_slate)
    draw_card(36, 82, 28, 14, 'Statistical Feature Pipeline', '14 Behavioral Flow Metrics',
              ['• Packet & Byte Transfer Rates', '• Inter-Arrival Time (IAT) Statistics'], '#64748B', '#F1F5F9', c_slate)
    draw_card(68, 82, 28, 14, 'Feature Schema Alignment', 'Normalized Feature Matrix',
              ['• Standardization & Z-Score Scaling', '• Zero-Copy Tensor Vectorization'], '#64748B', '#F1F5F9', c_slate)

    # Ingestion Arrows
    ax.annotate('', xy=(36, 89), xytext=(32, 89), arrowprops=dict(arrowstyle='->', color=c_blue, lw=2.2))
    ax.text(34, 91, 'Packets', fontsize=9.5, fontweight='bold', color=c_blue, ha='center')
    ax.annotate('', xy=(68, 89), xytext=(64, 89), arrowprops=dict(arrowstyle='->', color=c_blue, lw=2.2))
    ax.text(66, 91, 'Flows', fontsize=9.5, fontweight='bold', color=c_blue, ha='center')

    # Tier 1 to Tier 2 Downward Connector
    ax.annotate('', xy=(82, 77), xytext=(82, 82), arrowprops=dict(arrowstyle='->', color=c_blue, lw=2.5))
    ax.text(83, 79.5, '14-Feature Input Vector', fontsize=10, fontweight='bold', color=c_blue)

    # TIER 2: AI DETECTION & EXPLAINABILITY (XAI)
    draw_tier_bg(58.5, 18.5, 'TIER 2: AI THREAT DETECTION & EXPLAINABILITY (XAI)', '#EFF6FF')
    draw_card(4, 60, 28, 14.5, 'Unified XGBoost Classifier', 'Accuracy: 99.87% | Latency: <0.05ms',
              ['• 13 Attack Classes (DoS, DDoS, Scan,', '  Mirai Botnet, Brute Force, Infil.)', '• Weighted F1-Score: 0.9986'], c_blue, '#DBEAFE', c_blue)
    draw_card(36, 60, 28, 14.5, 'TreeSHAP Attribution Engine', 'Faithful Local Feature Attributions',
              ['• Exact Shapley Values per Prediction', '• Isolates Decisive Flow Anomalies', '• Eliminates Black-Box Opacity'], c_blue, '#DBEAFE', c_blue)
    draw_card(68, 60, 28, 14.5, 'Severity & Risk Scoring', 'SOC Operational Priority Rating',
              ['• Confidence-Gated Risk Matrix', '• Dynamic Triage: CRITICAL / HIGH', '• Suppresses Low-Confidence Noise'], c_blue, '#DBEAFE', c_blue)

    # Tier 2 Arrows
    ax.annotate('', xy=(36, 67), xytext=(32, 67), arrowprops=dict(arrowstyle='->', color=c_blue, lw=2.2))
    ax.text(34, 69, 'Class + Prob', fontsize=9.5, fontweight='bold', color=c_blue, ha='center')
    ax.annotate('', xy=(68, 67), xytext=(64, 67), arrowprops=dict(arrowstyle='->', color=c_blue, lw=2.2))
    ax.text(66, 69, 'SHAP Values', fontsize=9.5, fontweight='bold', color=c_blue, ha='center')

    # Tier 2 to Tier 3 Downward Connector
    ax.annotate('', xy=(82, 54.5), xytext=(82, 60), arrowprops=dict(arrowstyle='->', color=c_blue, lw=2.5))
    ax.text(83, 57.2, 'Enriched Threat Alert', fontsize=10, fontweight='bold', color=c_blue)

    # TIER 3: INCIDENT ORCHESTRATION & STORAGE (SOAR)
    draw_tier_bg(36.5, 18, 'TIER 3: INCIDENT MANAGEMENT & TAMPER-EVIDENT STORAGE', '#F0FDF4')
    draw_card(4, 38, 28, 14, 'Case Management Engine', 'Alert -> Incident -> Dossier',
              ['• Multi-Stage Verification Gating', '• Correlated Threat Dossiers (INV-...)', '• Lifecycle: ACK -> INV -> RESOLVE'], c_emerald, '#DCFCE7', c_emerald)
    draw_card(36, 38, 28, 14, 'Tactical Containment Engine', 'Automated Defense Playbooks',
              ['• Targeted Ingress IP Drop Rules', '• VLAN Quarantine & Rate Limiting', '• Human-Supervised Gated Actions'], c_emerald, '#DCFCE7', c_emerald)
    draw_card(68, 38, 28, 14, 'PostgreSQL & Audit Ledger', 'Tamper-Evident History',
              ['• Live Alerts, Incidents & Telemetry', '• Immutable Analyst Action Log', '• Complete Chain-of-Custody Proof'], c_emerald, '#DCFCE7', c_emerald)

    # Tier 3 Arrows
    ax.annotate('', xy=(36, 45), xytext=(32, 45), arrowprops=dict(arrowstyle='->', color=c_blue, lw=2.2))
    ax.text(34, 47, 'Threat Context', fontsize=9.5, fontweight='bold', color=c_blue, ha='center')
    ax.annotate('', xy=(68, 45), xytext=(64, 45), arrowprops=dict(arrowstyle='->', color=c_blue, lw=2.2))
    ax.text(66, 47, 'Audit Trail', fontsize=9.5, fontweight='bold', color=c_blue, ha='center')

    # TIER 4 & 5: ASSISTANT & OPERATOR WORKSPACE
    # Tier 4: Assistant (Left)
    tier4 = patches.FancyBboxPatch((1.5, 14.5), 47, 18.5, boxstyle='round,pad=0.3,rounding_size=1.5',
                                  facecolor='#FFFBEB', edgecolor='#CBD5E1', linewidth=1.5, linestyle='--')
    ax.add_patch(tier4)
    lbl4 = patches.FancyBboxPatch((1.5, 14.5 + 18.5 - 3.8), 35, 3.8, boxstyle='round,pad=0.1,rounding_size=0.8',
                                  facecolor='#B45309', edgecolor='none')
    ax.add_patch(lbl4)
    ax.text(3.0, 14.5 + 18.5 - 1.9, 'TIER 4: COGNITIVE AI CO-PILOT (ZUKA)', fontsize=10.0, fontweight='bold', color='#FFFFFF', va='center')

    draw_card(4, 16, 20.5, 14, 'Dual NLP Router', 'Sub-5ms Intent Engine',
              ['• Fast Regex Engine (<5ms)', '• Local Ollama LLM Fallback', '• 100% On-Premises Privacy'], c_amber, '#FEF3C7', c_amber)
    draw_card(26.5, 16, 20.5, 14, 'Grounded Tool Guards', 'Safe Tool Execution',
              ['• Grounded Database Tools', '• 60s Time-To-Live Tokens', '• Strict Anti-Hallucination Gate'], c_amber, '#FEF3C7', c_amber)
    ax.annotate('', xy=(26.5, 23), xytext=(24.5, 23), arrowprops=dict(arrowstyle='<->', color=c_amber, lw=2.0))

    # Tier 5: Human-in-the-Loop & UI (Right)
    tier5 = patches.FancyBboxPatch((51.5, 14.5), 47, 18.5, boxstyle='round,pad=0.3,rounding_size=1.5',
                                  facecolor='#FAF5FF', edgecolor='#CBD5E1', linewidth=1.5, linestyle='--')
    ax.add_patch(tier5)
    lbl5 = patches.FancyBboxPatch((51.5, 14.5 + 18.5 - 3.8), 36, 3.8, boxstyle='round,pad=0.1,rounding_size=0.8',
                                  facecolor='#6D28D9', edgecolor='none')
    ax.add_patch(lbl5)
    ax.text(53.0, 14.5 + 18.5 - 1.9, 'TIER 5: HUMAN-IN-THE-LOOP INTERFACE', fontsize=10.0, fontweight='bold', color='#FFFFFF', va='center')

    draw_card(53.5, 16, 21, 14, 'React 18 Operations UI', 'SOC Analyst Dashboard',
              ['• Live Telemetry & Threat Feeds', '• TreeSHAP Attribution Drawer', '• Context-Aware Action Cards'], c_purple, '#F3E8FF', c_purple)
    draw_card(76.5, 16, 20.5, 14, 'SOC Security Analyst', 'Human Authority in the Loop',
              ['• Validates Incident Telemetry', '• Reviews Root Cause Evidence', '• Authorizes Containment Orders'], c_purple, '#F3E8FF', c_purple)
    ax.annotate('', xy=(76.5, 23), xytext=(74.5, 23), arrowprops=dict(arrowstyle='<->', color=c_purple, lw=2.0))

    # Connection between Tier 4 & Tier 5
    ax.annotate('', xy=(53.5, 24), xytext=(47, 24), arrowprops=dict(arrowstyle='<->', color=c_blue, lw=2.2, linestyle=':'))
    ax.text(50.2, 26, 'Natural Language\nOperations', fontsize=9.0, fontweight='bold', color=c_blue, ha='center')

    # Tier 3 down to Tier 4 & Tier 5
    ax.annotate('', xy=(14, 32), xytext=(14, 38), arrowprops=dict(arrowstyle='->', color=c_blue, lw=2.2))
    ax.text(15, 35, 'State Sync', fontsize=9.5, fontweight='bold', color=c_blue)
    ax.annotate('', xy=(86, 32), xytext=(86, 38), arrowprops=dict(arrowstyle='->', color=c_blue, lw=2.2))
    ax.text(87, 35, 'Telemetry Feeds', fontsize=9.5, fontweight='bold', color=c_blue)

    # CLOSED-LOOP CONTAINMENT FEEDBACK (Prominent Red Dashed Lines)
    ax.annotate('', xy=(36, 42), xytext=(86.5, 30),
                arrowprops=dict(arrowstyle='->', color=c_red, lw=2.5, linestyle='--',
                                connectionstyle='arc3,rad=0.3'))
    ax.text(62, 34.5, 'Analyst-Authorized Containment Directive', fontsize=10, fontweight='bold', color=c_red)

    ax.annotate('', xy=(4, 85), xytext=(36, 48),
                arrowprops=dict(arrowstyle='->', color=c_red, lw=2.5, linestyle='--',
                                connectionstyle='arc3,rad=-0.32'))
    ax.text(10, 62, 'Policy Enforcement (Drop Host IP / VLAN Isolation)', fontsize=10, fontweight='bold', color=c_red, rotation=90)

    # BOTTOM LEGEND (Clear & Bold)
    leg = patches.FancyBboxPatch((1.5, 2.5), 97, 8.5, boxstyle='round,pad=0.2,rounding_size=1.0',
                                facecolor='#F1F5F9', edgecolor='#94A3B8', linewidth=1.5)
    ax.add_patch(leg)
    ax.text(4, 7.8, 'LEGEND & ARCHITECTURAL STANDARDS:', fontsize=10.5, fontweight='bold', color='#0F172A')

    # Legend Item 1
    ax.plot([4, 8], [4.8, 4.8], color=c_blue, lw=2.8)
    ax.text(9.2, 4.8, 'Feed-Forward Telemetry & Threat Analysis Pipeline', fontsize=9.5, fontweight='bold', color='#334155', va='center')

    # Legend Item 2
    ax.plot([46, 50], [4.8, 4.8], color=c_red, lw=2.8, linestyle='--')
    ax.text(51.2, 4.8, 'Human-Authorized Closed-Loop Containment Feedback', fontsize=9.5, fontweight='bold', color=c_red, va='center')

    # Legend Item 3
    ax.plot([83, 86], [4.8, 4.8], color=c_purple, lw=2.8, linestyle=':')
    ax.text(87.2, 4.8, 'Interactive Assistant Loop', fontsize=9.5, fontweight='bold', color=c_purple, va='center')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig1_ieee_full_architecture.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'fig1_ieee_full_architecture.pdf', bbox_inches='tight')
    plt.close()
    print("Fig 1 generated successfully.")

# ==============================================================================
# FIGURE 2: END-TO-END PIPELINE (SINGLE-COLUMN IEEE FORMAT)
# Fits in a standard 3.5 in / 88 mm IEEE column with large, legible fonts!
# ==============================================================================
def generate_fig2():
    fig, ax = plt.subplots(figsize=(8, 12), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    stages = [
        ("STAGE 1: NETWORK TELEMETRY INGESTION",
         "Packet Ingestion & Traffic Normalizer",
         "Captures live packet flows and historical PCAP replays;\nassembles bidirectional network flow metadata.",
         "#475569", "#F8FAFC", "#64748B"),

        ("STAGE 2: STATISTICAL FEATURE PIPELINE",
         "14-Metric Behavioral Feature Extractor",
         "Calculates packet transfer rates, inter-arrival times (IAT),\nbyte ratios, and flow duration vectors in real time.",
         "#1E40AF", "#EFF6FF", "#2563EB"),

        ("STAGE 3: MULTICLASS THREAT DETECTION",
         "Unified XGBoost Classifier (13 Classes)",
         "99.87% accuracy across DoS, DDoS, Botnets, Scans, Brute Force;\nsub-0.05 ms inference latency for streaming SOC deployment.",
         "#1E40AF", "#DBEAFE", "#1D4ED8"),

        ("STAGE 4: EXPLAINABLE AI ATTRIBUTION",
         "TreeSHAP Attribution & Root Cause Engine",
         "Decomposes prediction into local Shapley feature contributions;\neliminates black-box opacity for forensic justification.",
         "#4338CA", "#EEF2FF", "#4F46E5"),

        ("STAGE 5: INCIDENT ORCHESTRATION (SOAR)",
         "Confidence-Gated Triage & Case Dossier",
         "Correlates alerts into structured incidents (P1-P4);\npre-populates tactical containment playbooks (VLAN/IP block).",
         "#047857", "#ECFDF5", "#059669"),

        ("STAGE 6: COGNITIVE CO-PILOT & ANALYST",
         "Human-in-the-Loop & Zuka Assistant",
         "Senior SOC analyst verifies evidence with AI co-pilot;\nauthorizes containment and signs off on incident closure.",
         "#7E22CE", "#FAF5FF", "#9333EA"),
    ]

    box_h = 11.5
    spacing = 4.0
    start_y = 86.0

    for i, (stage_title, main_title, desc, stroke_col, bg_col, text_col) in enumerate(stages):
        y = start_y - i * (box_h + spacing)

        # Drop shadow
        sh = patches.FancyBboxPatch((9.5, y - 0.4), 81, box_h, boxstyle='round,pad=0.2,rounding_size=1.2',
                                    facecolor='#E2E8F0', edgecolor='none')
        ax.add_patch(sh)

        # Card
        card = patches.FancyBboxPatch((9, y), 81, box_h, boxstyle='round,pad=0.2,rounding_size=1.2',
                                     facecolor='#FFFFFF', edgecolor=stroke_col, linewidth=2.0)
        ax.add_patch(card)

        # Stage Number Badge
        badge = patches.Circle((16, y + box_h/2), 3.8, facecolor=stroke_col, edgecolor='none')
        ax.add_patch(badge)
        ax.text(16, y + box_h/2, str(i + 1), fontsize=13, fontweight='bold', color='#FFFFFF',
                ha='center', va='center')

        # Header tag
        ax.text(23, y + box_h - 2.8, stage_title, fontsize=10.0, fontweight='bold',
                color=stroke_col, va='center')

        # Main Title (Medium-Big & Bold)
        ax.text(23, y + box_h - 5.8, main_title, fontsize=12.0, fontweight='bold',
                color='#0F172A', va='center')

        # Description (Readable, 9.8pt)
        ax.text(23, y + box_h - 9.0, desc, fontsize=9.6, color='#475569', va='center')

        # Arrow down
        if i < len(stages) - 1:
            arrow_y_start = y
            arrow_y_end = y - spacing + 0.5
            ax.annotate('', xy=(49.5, arrow_y_end), xytext=(49.5, arrow_y_start),
                        arrowprops=dict(arrowstyle='->', color='#2563EB', lw=2.4))

    # Outer border / frame
    outer = patches.Rectangle((2, 2), 96, 96, fill=False, edgecolor='#CBD5E1', linewidth=1.5, linestyle=':')
    ax.add_patch(outer)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig2_ieee_single_column_pipeline.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'fig2_ieee_single_column_pipeline.pdf', bbox_inches='tight')
    plt.close()
    print("Fig 2 generated successfully.")

# ==============================================================================
# FIGURE 3: XAI & HUMAN-IN-THE-LOOP DECISION LOOP
# Highlights the interaction: Model -> TreeSHAP -> Copilot -> Analyst
# ==============================================================================
def generate_fig3():
    fig, ax = plt.subplots(figsize=(13, 8.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    c_blue = '#1E40AF'
    c_purple = '#6D28D9'
    c_amber = '#B45309'
    c_green = '#047857'
    c_red = '#B91C1C'

    def draw_component_box(x, y, w, h, header, subtitle, bullets, col_border, col_bg, col_title):
        sh = patches.FancyBboxPatch((x+0.3, y-0.4), w, h, boxstyle='round,pad=0.2,rounding_size=1.0',
                                    facecolor='#E2E8F0', edgecolor='none')
        ax.add_patch(sh)
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.2,rounding_size=1.0',
                                     facecolor='#FFFFFF', edgecolor=col_border, linewidth=2.0)
        ax.add_patch(box)
        hdr = patches.FancyBboxPatch((x, y + h - 3.8), w, 3.8, boxstyle='round,pad=0.1,rounding_size=0.8',
                                     facecolor=col_bg, edgecolor=col_border, linewidth=1.2)
        ax.add_patch(hdr)
        ax.text(x + w/2, y + h - 1.9, header, fontsize=12.0, fontweight='bold',
                color=col_title, ha='center', va='center')
        ax.text(x + w/2, y + h - 5.8, subtitle, fontsize=10.5, fontweight='bold',
                color='#0F172A', ha='center', va='center')
        curr_y = y + h - 9.0
        for b in bullets:
            ax.text(x + 2.0, curr_y, b, fontsize=9.8, color='#475569', va='center')
            curr_y -= 2.8

    # Left: ML Engine
    draw_component_box(4, 52, 28, 22, 'ML DETECTION CORE', 'Unified XGBoost Model',
                       ['• 13 Attack Classes + Benign', '• Accuracy: 99.87% | F1: 0.9986', '• Inference Time: <0.05 ms/flow', '• 2.56 Million Training Flows'],
                       c_blue, '#DBEAFE', c_blue)

    # Middle: XAI Engine
    draw_component_box(36, 52, 28, 22, 'EXPLAINABLE AI CORE', 'TreeSHAP Attribution',
                       ['• Local Feature Contribution Decomposition', '• Identifies Exact Anomaly Drivers', '• Solves Black-Box Opacity', '• Transparent Forensic Evidence'],
                       '#4338CA', '#EEF2FF', '#4338CA')

    # Right: Case Management & Triage
    draw_component_box(68, 52, 28, 22, 'SOAR INCIDENT ENGINE', 'Confidence-Gated Triage',
                       ['• P1-P4 Severity Classification', '• Correlated Forensic Dossier', '• Automated Playbook Directives', '• Tamper-Evident PostgreSQL Ledger'],
                       c_green, '#DCFCE7', c_green)

    # Connectors between Top Three
    ax.annotate('', xy=(36, 63), xytext=(32, 63), arrowprops=dict(arrowstyle='->', color=c_blue, lw=2.4))
    ax.text(34, 65.5, 'Class & Prob', fontsize=9.5, fontweight='bold', color=c_blue, ha='center')

    ax.annotate('', xy=(68, 63), xytext=(64, 63), arrowprops=dict(arrowstyle='->', color=c_blue, lw=2.4))
    ax.text(66, 65.5, 'Attributions', fontsize=9.5, fontweight='bold', color=c_blue, ha='center')

    # Bottom Left: Zuka Cognitive Co-Pilot
    draw_component_box(16, 12, 30, 24, 'COGNITIVE AI CO-PILOT', 'Dual-Engine Assistant (Zuka)',
                       ['• Sub-5ms Regex Intent Dispatcher', '• Local Ollama LLM (Qwen 2.5 3B)', '• Zero Data Leaves On-Premises', '• Grounded Tools & 60s Safety Tokens', '• Eliminates False Hallucinations'],
                       c_amber, '#FEF3C7', c_amber)

    # Bottom Right: Human SOC Analyst
    draw_component_box(54, 12, 30, 24, 'HUMAN-IN-THE-LOOP AUTHORITY', 'Senior SOC Security Analyst',
                       ['• Inspects SHAP Explanations in UI', '• Queries Zuka Assistant for Evidence', '• Verifies Attack Classification', '• Final Sign-Off & Case Resolution', '• Authorizes Containment Enforcement'],
                       c_purple, '#F3E8FF', c_purple)

    # Diagonal Connectors
    # XAI down to Assistant
    ax.annotate('', xy=(31, 36), xytext=(45, 52), arrowprops=dict(arrowstyle='->', color=c_blue, lw=2.2))
    ax.text(34, 44, 'Feature Insights', fontsize=9.5, fontweight='bold', color=c_blue)

    # Case down to Analyst
    ax.annotate('', xy=(69, 36), xytext=(78, 52), arrowprops=dict(arrowstyle='->', color=c_blue, lw=2.2))
    ax.text(76, 44, 'Incident Dossier', fontsize=9.5, fontweight='bold', color=c_blue)

    # Horizontal Interactive loop between Assistant & Analyst
    ax.annotate('', xy=(54, 25), xytext=(46, 25), arrowprops=dict(arrowstyle='<->', color=c_blue, lw=2.4, linestyle=':'))
    ax.text(50, 27.5, 'Natural Language\nTriage & Queries', fontsize=9.5, fontweight='bold', color=c_blue, ha='center')

    # Red Feedback loop from Analyst back to Network / Containment
    ax.annotate('', xy=(18, 74), xytext=(69, 36),
                arrowprops=dict(arrowstyle='->', color=c_red, lw=2.6, linestyle='--',
                                connectionstyle='arc3,rad=0.38'))
    ax.text(38, 83, 'Human-Authorized Containment (Block Host IP / VLAN Quarantine)',
            fontsize=10.5, fontweight='bold', color=c_red, ha='center')

    # Legend / Title banner at top
    banner = patches.FancyBboxPatch((4, 88), 92, 8.5, boxstyle='round,pad=0.2,rounding_size=1.0',
                                    facecolor='#F8FAFC', edgecolor='#94A3B8', linewidth=1.5)
    ax.add_patch(banner)
    ax.text(50, 93.5, 'EXPLAINABLE AI (XAI) & HUMAN-IN-THE-LOOP DECISION FRAMEWORK',
            fontsize=13, fontweight='bold', color='#0F172A', ha='center', va='center')
    ax.text(50, 90.2, 'Transparent, tamper-evident threat triage combining XGBoost, TreeSHAP, and on-premises cognitive AI guidance.',
            fontsize=10.0, color='#475569', ha='center', va='center')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig3_ieee_xai_decision_loop.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'fig3_ieee_xai_decision_loop.pdf', bbox_inches='tight')
    plt.close()
    print("Fig 3 generated successfully.")

if __name__ == '__main__':
    generate_fig1()
    generate_fig2()
    generate_fig3()
    print("All 3 IEEE publication figures generated successfully!")
