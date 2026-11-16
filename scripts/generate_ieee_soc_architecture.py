"""
Generate publication-quality software architecture diagram titled:
'ZUKA SOC: AI-Assisted Security Operations Architecture' in IEEE paper style.

Strict adherence to user specifications:
- Title: 'ZUKA SOC: AI-Assisted Security Operations Architecture'
- Layout: landscape, white background, flat design, no shadows or 3D.
- Five horizontal layered bands, each with a small label on the left, with equal spacing and a strict grid.
- Layers and components (rounded rectangles, equal size within each layer, short name plus one-line gray subtitle):
  1. Presentation Layer: Security Analyst; React Operations UI
  2. Application Layer: FastAPI Gateway; Query Orchestrator
  3. Knowledge Layer: Embedding Model; Vector Database; Telemetry and Logs Store; Knowledge Base Documents
  4. AI Layer: Prompt Builder; Local Ollama LLM
  5. Output Layer: Triage and Actions; Feedback Store
- Data flow with small gray arrow labels:
  Analyst -> React UI ('query') -> FastAPI Gateway ('request') -> Query Orchestrator ('parse') ->
  Vector Database ('search') -> Prompt Builder ('context') -> Ollama LLM ('prompt') ->
  Triage and Actions ('response') -> back to Analyst.
  Also: Knowledge Base Documents and Telemetry Store -> Embedding Model -> Vector Database ('indexing'), drawn as separate dashed arrow.
  Feedback Store -> Knowledge Layer ('learning loop'), drawn as a smooth dashed loop arrow.
- Style rules:
  - One font only (Segoe UI / Arial / Inter); all labels the same size; bold only for the title.
  - All text spelled exactly as given, centered, fully readable.
  - Straight or right-angle arrows with clean arrowheads, no crossing or overlapping lines.
  - Palette: soft blue, teal, and light gray fills, dark navy text, dark gray arrows.
  - Absolutely NO red text, NO red lines, NO handwritten notes, NO watermarks, NO decorative clutter.
  - Legend at bottom: solid arrow = main data flow, dashed arrow = indexing and feedback.
  - High resolution, generous margins.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

OUTPUT_DIR = Path(r"c:\Users\admin\Downloads\AI-Cybersecurity-Assistant\docs\architecture")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_FAMILY = 'Segoe UI'

def generate_diagram():
    # Landscape Canvas (16:10 ratio, 300 DPI publication quality)
    fig, ax = plt.subplots(figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    ax.set_xlim(0, 160)
    ax.set_ylim(0, 110)
    ax.axis('off')

    # Color Palette: Soft blue, teal, light gray fills; dark navy text; dark gray arrows
    c_blue_bg = '#E0F2FE'
    c_blue_border = '#38BDF8'
    c_teal_bg = '#CCFBF1'
    c_teal_border = '#2DD4BF'
    c_gray_bg = '#F1F5F9'
    c_gray_border = '#94A3B8'
    
    c_text_navy = '#0A2540'
    c_text_gray = '#64748B'
    c_arrow = '#334155'
    c_arrow_lbl = '#475569'

    # Title (Bold ONLY for title, exactly as requested)
    ax.text(80, 103.5, 'ZUKA SOC: AI-Assisted Security Operations Architecture',
            fontsize=17, fontweight='bold', fontfamily=FONT_FAMILY, color=c_text_navy,
            ha='center', va='center')

    # 5 Horizontal Layered Bands (Equal spacing and strict grid)
    # Band coordinates: y_bottom, height
    layer_h = 13.5
    layer_gap = 3.2
    start_y = 17.5  # Layer 5 bottom
    # Layer 5: 17.5 to 31.0
    # Layer 4: 34.2 to 47.7
    # Layer 3: 50.9 to 64.4
    # Layer 2: 67.6 to 81.1
    # Layer 1: 84.3 to 97.8

    layer_configs = [
        ("Presentation Layer", 84.3),
        ("Application Layer", 67.6),
        ("Knowledge Layer", 50.9),
        ("AI Layer", 34.2),
        ("Output Layer", 17.5),
    ]

    for label, y_b in layer_configs:
        # Subtle horizontal layered band background
        band = patches.FancyBboxPatch((6, y_b), 148, layer_h,
                                     boxstyle='round,pad=0.2,rounding_size=0.8',
                                     facecolor='#F8FAFC', edgecolor='#E2E8F0',
                                     linewidth=1.2)
        ax.add_patch(band)

        # Layer tab on the left
        tab = patches.FancyBboxPatch((7, y_b + 2.0), 22, layer_h - 4.0,
                                     boxstyle='round,pad=0.2,rounding_size=0.6',
                                     facecolor='#E2E8F0', edgecolor='#CBD5E1',
                                     linewidth=1.0)
        ax.add_patch(tab)
        ax.text(18, y_b + layer_h/2, label,
                fontsize=9.5, fontfamily=FONT_FAMILY, color=c_text_navy,
                fontweight='normal', ha='center', va='center')

    # Component Box Dimensions:
    # In layers 1, 2, 4, 5: components can be larger / wider
    # In layer 3: 4 components of equal size
    # All box labels have the SAME font size (10.5pt), normal weight
    def draw_box(x, y, w, h, main_title, subtitle, bg_col, border_col):
        box = patches.FancyBboxPatch((x, y), w, h,
                                     boxstyle='round,pad=0.2,rounding_size=1.0',
                                     facecolor=bg_col, edgecolor=border_col,
                                     linewidth=1.6)
        ax.add_patch(box)
        # Main label (Centered, same font size across all boxes)
        ax.text(x + w/2, y + h/2 + 1.8, main_title,
                fontsize=10.5, fontfamily=FONT_FAMILY, color=c_text_navy,
                fontweight='normal', ha='center', va='center')
        # Subtitle (Centered, gray, normal)
        ax.text(x + w/2, y + h/2 - 2.2, subtitle,
                fontsize=8.5, fontfamily=FONT_FAMILY, color=c_text_gray,
                fontweight='normal', ha='center', va='center')

    # ==========================================================================
    # LAYER 1: PRESENTATION LAYER (y = 84.3 to 97.8)
    # Security Analyst; React Operations UI
    # ==========================================================================
    y1 = 86.0
    h1 = 10.0
    w_std = 25.0
    
    # Security Analyst at x = 36
    draw_box(36, y1, w_std, h1, "Security Analyst", "Operations Specialist", c_gray_bg, c_gray_border)
    # React Operations UI at x = 70
    draw_box(70, y1, w_std, h1, "React Operations UI", "Dashboard Interface", c_blue_bg, c_blue_border)

    # Arrow 1: Analyst -> React UI ("query")
    ax.annotate('', xy=(70, y1 + h1/2), xytext=(61, y1 + h1/2),
                arrowprops=dict(arrowstyle='->,head_width=0.3,head_length=0.5', color=c_arrow, lw=1.6))
    ax.text(65.5, y1 + h1/2 + 2.0, 'query', fontsize=8.5, fontfamily=FONT_FAMILY, color=c_arrow_lbl, ha='center', va='center')

    # ==========================================================================
    # LAYER 2: APPLICATION LAYER (y = 67.6 to 81.1)
    # FastAPI Gateway (authentication, routing); Query Orchestrator (request handling)
    # ==========================================================================
    y2 = 69.3
    h2 = 10.0
    # FastAPI Gateway directly below React Operations UI (x = 70)
    draw_box(70, y2, w_std, h2, "FastAPI Gateway", "Authentication, Routing", c_teal_bg, c_teal_border)
    # Query Orchestrator at x = 104
    draw_box(104, y2, w_std, h2, "Query Orchestrator", "Request Handling", c_blue_bg, c_blue_border)

    # Arrow 2: React UI -> FastAPI Gateway ("request")
    ax.annotate('', xy=(82.5, y2 + h2), xytext=(82.5, y1),
                arrowprops=dict(arrowstyle='->,head_width=0.3,head_length=0.5', color=c_arrow, lw=1.6))
    ax.text(87.5, (y1 + y2 + h2)/2, 'request', fontsize=8.5, fontfamily=FONT_FAMILY, color=c_arrow_lbl, ha='center', va='center')

    # Arrow 3: FastAPI Gateway -> Query Orchestrator ("parse")
    ax.annotate('', xy=(104, y2 + h2/2), xytext=(95, y2 + h2/2),
                arrowprops=dict(arrowstyle='->,head_width=0.3,head_length=0.5', color=c_arrow, lw=1.6))
    ax.text(99.5, y2 + h2/2 + 2.0, 'parse', fontsize=8.5, fontfamily=FONT_FAMILY, color=c_arrow_lbl, ha='center', va='center')

    # ==========================================================================
    # LAYER 3: KNOWLEDGE LAYER (y = 50.9 to 64.4)
    # 4 Components: Embedding Model; Vector Database; Telemetry and Logs Store; Knowledge Base Documents
    # ==========================================================================
    y3 = 52.6
    h3 = 10.0
    w_k = 24.5
    gap_k = 3.5

    # Grid columns for Layer 3:
    # x3_kb (leftmost doc store): 34
    # x3_tel (telemetry store): 62
    # x3_emb (embedding model): 90
    # x3_vdb (vector database): 118 (aligned under Query Orchestrator!)
    x3_kb = 34.0
    x3_tel = 62.0
    x3_emb = 90.0
    x3_vdb = 118.0

    draw_box(x3_kb, y3, w_k, h3, "Knowledge Base Documents", "Security SOPs & Manuals", c_gray_bg, c_gray_border)
    draw_box(x3_tel, y3, w_k, h3, "Telemetry and Logs Store", "Network Telemetry & Logs", c_gray_bg, c_gray_border)
    draw_box(x3_emb, y3, w_k, h3, "Embedding Model", "Text & Log Vectorizer", c_teal_bg, c_teal_border)
    draw_box(x3_vdb, y3, w_k, h3, "Vector Database", "RAG Retrieval", c_blue_bg, c_blue_border)

    # Arrow 4: Query Orchestrator -> Vector Database ("search")
    # From bottom of Query Orchestrator (center x = 116.5) down to top of Vector Database (center x = 130.25)
    # Using clean right-angle orthogonal path:
    ax.plot([116.5, 116.5], [y2, y3 + h3 + 1.8], color=c_arrow, lw=1.6)
    ax.plot([116.5, 130.25], [y3 + h3 + 1.8, y3 + h3 + 1.8], color=c_arrow, lw=1.6)
    ax.annotate('', xy=(130.25, y3 + h3), xytext=(130.25, y3 + h3 + 1.8),
                arrowprops=dict(arrowstyle='->,head_width=0.3,head_length=0.5', color=c_arrow, lw=1.6))
    ax.text(123.0, y3 + h3 + 3.2, 'search', fontsize=8.5, fontfamily=FONT_FAMILY, color=c_arrow_lbl, ha='center', va='center')

    # Indexing Flow (Dashed Arrow):
    # Knowledge Base Documents & Telemetry Store -> Embedding Model -> Vector Database ("indexing")
    # KB Doc -> Embedding Model (dashed arrow right, passing under Telemetry store or through top channel)
    # Clean orthogonal path:
    ax.plot([x3_kb + w_k, x3_tel], [y3 + 3.0, y3 + 3.0], color=c_arrow, lw=1.4, linestyle='--')
    ax.annotate('', xy=(x3_emb, y3 + 3.0), xytext=(x3_tel + w_k, y3 + 3.0),
                arrowprops=dict(arrowstyle='->,head_width=0.3,head_length=0.5', color=c_arrow, lw=1.4, linestyle='--'))
    ax.text((x3_tel + w_k + x3_emb)/2, y3 + 4.8, 'raw docs', fontsize=7.5, fontfamily=FONT_FAMILY, color=c_arrow_lbl, ha='center', va='center')

    # Embedding Model -> Vector Database ("indexing")
    ax.annotate('', xy=(x3_vdb, y3 + 3.0), xytext=(x3_emb + w_k, y3 + 3.0),
                arrowprops=dict(arrowstyle='->,head_width=0.3,head_length=0.5', color=c_arrow, lw=1.4, linestyle='--'))
    ax.text((x3_emb + w_k + x3_vdb)/2, y3 + 4.8, 'indexing', fontsize=8.5, fontfamily=FONT_FAMILY, color=c_arrow_lbl, ha='center', va='center')

    # ==========================================================================
    # LAYER 4: AI LAYER (y = 34.2 to 47.7)
    # Prompt Builder (question + retrieved context); Local Ollama LLM (qwen2.5:3b, runs on-premise)
    # ==========================================================================
    y4 = 35.9
    h4 = 10.0
    w4 = 28.0

    # Prompt Builder at x = 102
    draw_box(102, y4, w4, h4, "Prompt Builder", "Question + Retrieved Context", c_teal_bg, c_teal_border)
    # Local Ollama LLM at x = 62
    draw_box(62, y4, w4, h4, "Local Ollama LLM", "qwen2.5:3b (On-Premise)", c_blue_bg, c_blue_border)

    # Arrow 5: Vector Database -> Prompt Builder ("context")
    # From bottom of Vector Database (center x = 130.25) down to top of Prompt Builder (center x = 116.0)
    ax.plot([130.25, 130.25], [y3, y4 + h4 + 1.8], color=c_arrow, lw=1.6)
    ax.plot([130.25, 116.0], [y4 + h4 + 1.8, y4 + h4 + 1.8], color=c_arrow, lw=1.6)
    ax.annotate('', xy=(116.0, y4 + h4), xytext=(116.0, y4 + h4 + 1.8),
                arrowprops=dict(arrowstyle='->,head_width=0.3,head_length=0.5', color=c_arrow, lw=1.6))
    ax.text(123.0, y4 + h4 + 3.2, 'context', fontsize=8.5, fontfamily=FONT_FAMILY, color=c_arrow_lbl, ha='center', va='center')

    # Arrow 6: Prompt Builder -> Local Ollama LLM ("prompt")
    ax.annotate('', xy=(90, y4 + h4/2), xytext=(102, y4 + h4/2),
                arrowprops=dict(arrowstyle='->,head_width=0.3,head_length=0.5', color=c_arrow, lw=1.6))
    ax.text(96.0, y4 + h4/2 + 2.0, 'prompt', fontsize=8.5, fontfamily=FONT_FAMILY, color=c_arrow_lbl, ha='center', va='center')

    # ==========================================================================
    # LAYER 5: OUTPUT LAYER (y = 17.5 to 31.0)
    # Triage and Actions (severity, explanation, next steps); Feedback Store
    # ==========================================================================
    y5 = 19.2
    h5 = 10.0
    w5 = 32.0

    # Triage and Actions directly below Local Ollama LLM (center x = 76.0)
    draw_box(60, y5, w5, h5, "Triage and Actions", "Severity, Explanation, Next Steps", c_teal_bg, c_teal_border)
    # Feedback Store to the right (x = 102)
    draw_box(102, y5, 28, h5, "Feedback Store", "Continuous Learning Ledger", c_gray_bg, c_gray_border)

    # Arrow 7: Ollama LLM -> Triage and Actions ("response")
    ax.annotate('', xy=(76.0, y5 + h5), xytext=(76.0, y4),
                arrowprops=dict(arrowstyle='->,head_width=0.3,head_length=0.5', color=c_arrow, lw=1.6))
    ax.text(82.0, (y4 + y5 + h5)/2, 'response', fontsize=8.5, fontfamily=FONT_FAMILY, color=c_arrow_lbl, ha='center', va='center')

    # Arrow 8: Triage and Actions -> Feedback Store (record)
    ax.annotate('', xy=(102, y5 + h5/2), xytext=(92, y5 + h5/2),
                arrowprops=dict(arrowstyle='->,head_width=0.3,head_length=0.5', color=c_arrow, lw=1.4, linestyle='--'))
    ax.text(97.0, y5 + h5/2 + 2.0, 'record', fontsize=8.0, fontfamily=FONT_FAMILY, color=c_arrow_lbl, ha='center', va='center')

    # Arrow 9: Triage and Actions -> back to Analyst (Clean left margin loop)
    # From bottom-left of Triage and Actions (x = 60, y = y5 + h5/2), go left to x = 20, up to Layer 1, into Analyst
    ax.plot([60, 20], [y5 + h5/2, y5 + h5/2], color=c_arrow, lw=1.6)
    ax.plot([20, 20], [y5 + h5/2, y1 + h1/2], color=c_arrow, lw=1.6)
    ax.annotate('', xy=(36, y1 + h1/2), xytext=(20, y1 + h1/2),
                arrowprops=dict(arrowstyle='->,head_width=0.3,head_length=0.5', color=c_arrow, lw=1.6))
    ax.text(28.0, y1 + h1/2 + 2.0, 'response', fontsize=8.5, fontfamily=FONT_FAMILY, color=c_arrow_lbl, ha='center', va='center')
    ax.text(17.5, (y1 + y5)/2, 'incident notification & triage return', fontsize=8.0, fontfamily=FONT_FAMILY,
            color=c_arrow_lbl, rotation=90, ha='center', va='center')

    # Arrow 10: Feedback Store -> Knowledge Layer ("learning loop", smooth dashed loop arrow)
    # From right of Feedback Store (x = 130, y = y5 + h5/2) -> right margin x = 148 -> up to Layer 3 (y3 + h3/2) -> left into Vector DB
    ax.plot([130, 148], [y5 + h5/2, y5 + h5/2], color=c_arrow, lw=1.4, linestyle='--')
    ax.plot([148, 148], [y5 + h5/2, y3 + h3/2], color=c_arrow, lw=1.4, linestyle='--')
    ax.annotate('', xy=(x3_vdb + w_k, y3 + h3/2), xytext=(148, y3 + h3/2),
                arrowprops=dict(arrowstyle='->,head_width=0.3,head_length=0.5', color=c_arrow, lw=1.4, linestyle='--'))
    ax.text(151.0, (y3 + y5)/2, 'learning loop', fontsize=8.5, fontfamily=FONT_FAMILY,
            color=c_arrow_lbl, rotation=270, ha='center', va='center')

    # ==========================================================================
    # LEGEND AT BOTTOM
    # solid arrow = main data flow, dashed arrow = indexing and feedback
    # ==========================================================================
    y_leg = 6.5
    leg_box = patches.FancyBboxPatch((40, y_leg), 80, 6.0,
                                     boxstyle='round,pad=0.2,rounding_size=0.6',
                                     facecolor='#F8FAFC', edgecolor='#CBD5E1',
                                     linewidth=1.0)
    ax.add_patch(leg_box)

    # Legend Item 1: Solid arrow = main data flow
    ax.plot([46, 54], [y_leg + 3.0, y_leg + 3.0], color=c_arrow, lw=1.8)
    ax.annotate('', xy=(54, y_leg + 3.0), xytext=(52, y_leg + 3.0),
                arrowprops=dict(arrowstyle='->,head_width=0.3,head_length=0.5', color=c_arrow, lw=1.8))
    ax.text(56.5, y_leg + 3.0, 'Main Data Flow', fontsize=9.0, fontfamily=FONT_FAMILY, color=c_text_navy, va='center')

    # Legend Item 2: Dashed arrow = indexing and feedback
    ax.plot([86, 94], [y_leg + 3.0, y_leg + 3.0], color=c_arrow, lw=1.5, linestyle='--')
    ax.annotate('', xy=(94, y_leg + 3.0), xytext=(92, y_leg + 3.0),
                arrowprops=dict(arrowstyle='->,head_width=0.3,head_length=0.5', color=c_arrow, lw=1.5, linestyle='--'))
    ax.text(96.5, y_leg + 3.0, 'Indexing and Feedback Loop', fontsize=9.0, fontfamily=FONT_FAMILY, color=c_text_navy, va='center')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'zuka_soc_architecture_ieee.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'zuka_soc_architecture_ieee.pdf', bbox_inches='tight')
    plt.close()
    print("ZUKA SOC IEEE architecture generated successfully!")

if __name__ == '__main__':
    generate_diagram()
