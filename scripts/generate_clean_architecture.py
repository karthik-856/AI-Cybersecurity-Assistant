"""
Generate clean, professional, publication-grade software architecture diagrams
strictly following all user style requirements:
- White background, flat modern design, no 3D effects, no shadows
- Rounded rectangle boxes of equal size, evenly spaced and aligned on a grid
- One consistent sans-serif font (Segoe UI / Arial / Inter) for all text,
  same size for all box labels, bold only for the title
- All text spelled correctly, centered inside boxes, fully readable
- Neat, straight arrows with arrowheads, no crossing or overlapping lines
- A clear loop arrow from final output back to start to show feedback cycle
- Small arrow labels in dark gray ("query", "context", "response", etc.)
- Color palette: blue, teal, and gray only, with soft pastel fills and dark text
- Strictly NO red text, NO red lines, NO red highlights, NO handwritten annotations
- No extra decorative icons, watermarks, or clutter
- High resolution, landscape orientation, balanced spacing and margins
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

OUTPUT_DIR = Path(r"c:\Users\admin\Downloads\AI-Cybersecurity-Assistant\docs\architecture")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Select best available sans-serif font
FONT_FAMILY = 'Segoe UI'

# ==============================================================================
# OPTION A: LINEAR LANDSCAPE ARCHITECTURE (1 ROW OF 6 BOXES + RETURN LOOP)
# ==============================================================================
def generate_linear_diagram():
    # 16:9 Landscape Canvas
    fig, ax = plt.subplots(figsize=(16, 8.5), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    ax.set_xlim(0, 160)
    ax.set_ylim(0, 85)
    ax.axis('off')

    # Title (Bold only, sans-serif, centered)
    ax.text(80, 75, 'ZUKA SOC: AI CYBERSECURITY ASSISTANT ARCHITECTURE',
            fontsize=16, fontweight='bold', fontfamily=FONT_FAMILY, color='#0F172A',
            ha='center', va='center')

    # Subtitle / Caption description
    ax.text(80, 70.5, 'End-to-End Grounded Retrieval-Augmented Generation & Human-in-the-Loop Workflow',
            fontsize=10.5, fontfamily=FONT_FAMILY, color='#475569',
            ha='center', va='center')

    # 6 Components (Equal Size, Rounded Rectangle, Soft Pastel Fills)
    box_w = 20.0
    box_h = 18.0
    y_pos = 38.0
    gap = 4.8
    x_start = 8.0

    # Color Palette: Blue, Teal, Gray only
    # Box structure: (Main Label, Secondary Description, Fill Color, Border Color)
    components = [
        ("User", "SOC Analyst", "#F1F5F9", "#94A3B8"),            # Soft Gray
        ("Frontend / Website", "React 18 Dashboard", "#E0F2FE", "#0284C7"), # Soft Blue
        ("Backend API", "FastAPI Service", "#CCFBF1", "#0D9488"),   # Soft Teal
        ("Knowledge Base", "RAG & Telemetry Store", "#E0F2FE", "#0284C7"), # Soft Blue
        ("LLM Model", "Local Ollama Engine", "#CCFBF1", "#0D9488"), # Soft Teal
        ("Response to User", "Triage & Actions", "#F1F5F9", "#94A3B8")     # Soft Gray
    ]

    # Draw Boxes
    for i, (main_text, sub_text, bg_col, border_col) in enumerate(components):
        x = x_start + i * (box_w + gap)
        box = patches.FancyBboxPatch((x, y_pos), box_w, box_h,
                                     boxstyle='round,pad=0.2,rounding_size=1.2',
                                     facecolor=bg_col, edgecolor=border_col,
                                     linewidth=1.8)
        ax.add_patch(box)

        # Centered text, exactly same font size for all box labels
        ax.text(x + box_w/2, y_pos + box_h/2 + 2.2, main_text,
                fontsize=11.5, fontfamily=FONT_FAMILY, color='#0F172A',
                ha='center', va='center')
        ax.text(x + box_w/2, y_pos + box_h/2 - 2.8, sub_text,
                fontsize=9.5, fontfamily=FONT_FAMILY, color='#475569',
                ha='center', va='center')

    # Straight Horizontal Arrows & Small Dark Gray Labels
    arrow_labels = ["query", "request", "context", "prompt", "response"]
    for i in range(5):
        x_from = x_start + i * (box_w + gap) + box_w
        x_to = x_start + (i + 1) * (box_w + gap)
        y = y_pos + box_h/2

        ax.annotate('', xy=(x_to, y), xytext=(x_from, y),
                    arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.6',
                                    color='#334155', lw=1.8))
        ax.text((x_from + x_to)/2, y + 2.5, arrow_labels[i],
                fontsize=9.0, fontfamily=FONT_FAMILY, color='#475569',
                ha='center', va='center')

    # Clear Feedback Loop Arrow (Down from Box 6, Left along bottom, Up into Box 1)
    x_box1_center = x_start + box_w/2
    x_box6_center = x_start + 5 * (box_w + gap) + box_w/2
    y_loop_bottom = 15.0

    # Down from Box 6
    ax.plot([x_box6_center, x_box6_center], [y_pos, y_loop_bottom], color='#334155', lw=1.8)
    # Left horizontally across all components
    ax.plot([x_box6_center, x_box1_center], [y_loop_bottom, y_loop_bottom], color='#334155', lw=1.8)
    # Up into Box 1 with arrowhead
    ax.annotate('', xy=(x_box1_center, y_pos), xytext=(x_box1_center, y_loop_bottom),
                arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.6',
                                color='#334155', lw=1.8))

    # Loop Label (Centered, small dark gray)
    ax.text((x_box1_center + x_box6_center)/2, y_loop_bottom + 2.5,
            'feedback cycle & continuous incident triage loop',
            fontsize=9.5, fontfamily=FONT_FAMILY, color='#475569',
            ha='center', va='center')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'zuka_architecture_clean_linear.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'zuka_architecture_clean_linear.pdf', bbox_inches='tight')
    plt.close()
    print("Linear architecture diagram generated successfully.")

# ==============================================================================
# OPTION B: BALANCED GRID ARCHITECTURE (2 ROWS OF 3 BOXES + RETURN LOOP)
# ==============================================================================
def generate_grid_diagram():
    # 16:10 Landscape Canvas
    fig, ax = plt.subplots(figsize=(15, 9.5), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    ax.set_xlim(0, 150)
    ax.set_ylim(0, 95)
    ax.axis('off')

    # Title
    ax.text(75, 87, 'ZUKA SOC: SOFTWARE ARCHITECTURE DIAGRAM',
            fontsize=16, fontweight='bold', fontfamily=FONT_FAMILY, color='#0F172A',
            ha='center', va='center')
    ax.text(75, 82.5, 'Components Pipeline with Closed Feedback Cycle (IEEE Publication Style)',
            fontsize=10.5, fontfamily=FONT_FAMILY, color='#475569',
            ha='center', va='center')

    # Grid Dimensions (Equal Size, Even Spacing)
    box_w = 32.0
    box_h = 18.0
    gap_x = 13.0
    x1 = 15.0
    x2 = x1 + box_w + gap_x
    x3 = x2 + box_w + gap_x

    y_row1 = 54.0
    y_row2 = 22.0

    # Row 1 Components (Left to Right)
    row1 = [
        ("User", "Security Analyst", "#F1F5F9", "#94A3B8", x1),             # Box 1 (Gray)
        ("Frontend / Website", "React Operations UI", "#E0F2FE", "#0284C7", x2), # Box 2 (Blue)
        ("Backend API", "FastAPI Core Services", "#CCFBF1", "#0D9488", x3)     # Box 3 (Teal)
    ]

    # Row 2 Components (Right to Left to form a natural rectangular circuit)
    row2 = [
        ("Knowledge Base", "RAG & Telemetry Center", "#E0F2FE", "#0284C7", x3),# Box 4 (Blue)
        ("LLM Model", "Local Ollama Engine", "#CCFBF1", "#0D9488", x2),       # Box 5 (Teal)
        ("Response back to User", "Triage & Actions", "#F1F5F9", "#94A3B8", x1)# Box 6 (Gray)
    ]

    # Draw Row 1 Boxes
    for main_text, sub_text, bg_col, border_col, x in row1:
        box = patches.FancyBboxPatch((x, y_row1), box_w, box_h,
                                     boxstyle='round,pad=0.2,rounding_size=1.2',
                                     facecolor=bg_col, edgecolor=border_col,
                                     linewidth=1.8)
        ax.add_patch(box)
        ax.text(x + box_w/2, y_row1 + box_h/2 + 2.2, main_text,
                fontsize=12.0, fontfamily=FONT_FAMILY, color='#0F172A',
                ha='center', va='center')
        ax.text(x + box_w/2, y_row1 + box_h/2 - 2.8, sub_text,
                fontsize=10.0, fontfamily=FONT_FAMILY, color='#475569',
                ha='center', va='center')

    # Draw Row 2 Boxes
    for main_text, sub_text, bg_col, border_col, x in row2:
        box = patches.FancyBboxPatch((x, y_row2), box_w, box_h,
                                     boxstyle='round,pad=0.2,rounding_size=1.2',
                                     facecolor=bg_col, edgecolor=border_col,
                                     linewidth=1.8)
        ax.add_patch(box)
        ax.text(x + box_w/2, y_row2 + box_h/2 + 2.2, main_text,
                fontsize=12.0, fontfamily=FONT_FAMILY, color='#0F172A',
                ha='center', va='center')
        ax.text(x + box_w/2, y_row2 + box_h/2 - 2.8, sub_text,
                fontsize=10.0, fontfamily=FONT_FAMILY, color='#475569',
                ha='center', va='center')

    # Straight Arrows Row 1 (1 -> 2 -> 3)
    # 1 -> 2
    ax.annotate('', xy=(x2, y_row1 + box_h/2), xytext=(x1 + box_w, y_row1 + box_h/2),
                arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.6', color='#334155', lw=1.8))
    ax.text((x1 + box_w + x2)/2, y_row1 + box_h/2 + 2.5, 'query',
            fontsize=9.5, fontfamily=FONT_FAMILY, color='#475569', ha='center', va='center')

    # 2 -> 3
    ax.annotate('', xy=(x3, y_row1 + box_h/2), xytext=(x2 + box_w, y_row1 + box_h/2),
                arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.6', color='#334155', lw=1.8))
    ax.text((x2 + box_w + x3)/2, y_row1 + box_h/2 + 2.5, 'request',
            fontsize=9.5, fontfamily=FONT_FAMILY, color='#475569', ha='center', va='center')

    # Down from Box 3 to Box 4
    ax.annotate('', xy=(x3 + box_w/2, y_row2 + box_h), xytext=(x3 + box_w/2, y_row1),
                arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.6', color='#334155', lw=1.8))
    ax.text(x3 + box_w/2 + 6.8, (y_row1 + y_row2 + box_h)/2, 'context',
            fontsize=9.5, fontfamily=FONT_FAMILY, color='#475569', ha='center', va='center')

    # Straight Arrows Row 2 (4 -> 5 -> 6, going left)
    # 4 -> 5
    ax.annotate('', xy=(x2 + box_w, y_row2 + box_h/2), xytext=(x3, y_row2 + box_h/2),
                arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.6', color='#334155', lw=1.8))
    ax.text((x3 + x2 + box_w)/2, y_row2 + box_h/2 + 2.5, 'prompt',
            fontsize=9.5, fontfamily=FONT_FAMILY, color='#475569', ha='center', va='center')

    # 5 -> 6
    ax.annotate('', xy=(x1 + box_w, y_row2 + box_h/2), xytext=(x2, y_row2 + box_h/2),
                arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.6', color='#334155', lw=1.8))
    ax.text((x2 + x1 + box_w)/2, y_row2 + box_h/2 + 2.5, 'response',
            fontsize=9.5, fontfamily=FONT_FAMILY, color='#475569', ha='center', va='center')

    # Up from Box 6 back to Box 1 (Closing the cycle)
    ax.annotate('', xy=(x1 + box_w/2, y_row1), xytext=(x1 + box_w/2, y_row2 + box_h),
                arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.6', color='#334155', lw=1.8))
    ax.text(x1 + box_w/2 - 7.5, (y_row1 + y_row2 + box_h)/2, 'feedback cycle',
            fontsize=9.5, fontfamily=FONT_FAMILY, color='#475569', ha='center', va='center')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'zuka_architecture_clean_grid.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'zuka_architecture_clean_grid.pdf', bbox_inches='tight')
    plt.close()
    print("Grid architecture diagram generated successfully.")

if __name__ == '__main__':
    generate_linear_diagram()
    generate_grid_diagram()
    print("Both clean diagrams generated successfully!")
