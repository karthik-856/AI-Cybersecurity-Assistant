"""
Generate a professional, publication-quality Microsoft Word (.docx) document
for the Capstone Project Phase-I (23AM4701) Review-2 submission at
Dayananda Sagar University (DSU), Department of CSE (AI & ML).
"""

import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn
from pathlib import Path

OUTPUT_PATH = Path(r"c:\Users\admin\Downloads\AI-Cybersecurity-Assistant\docs\presentation\Review_2_Capstone_Project_Documentation.docx")
ARCH_IMG_PATH = Path(r"c:\Users\admin\Downloads\AI-Cybersecurity-Assistant\docs\architecture\zuka_methodology_architecture.png")

doc = Document()

# Set standard 1-inch margins
for section in doc.sections:
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

# Colors
C_NAVY = RGBColor(10, 37, 64)       # #0A2540
C_BLUE = RGBColor(30, 64, 175)      # #1E40AF
C_SLATE = RGBColor(71, 85, 105)     # #475569
C_BLACK = RGBColor(15, 23, 42)      # #0F172A

# Helpers for styling
def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def add_header(title, level=1):
    h = doc.add_heading(level=level)
    run = h.add_run(title)
    run.font.name = 'Arial'
    run.font.color.rgb = C_NAVY if level == 1 else C_BLUE
    run.bold = True
    if level == 1:
        run.font.size = Pt(16)
        h.paragraph_format.space_before = Pt(18)
        h.paragraph_format.space_after = Pt(6)
    elif level == 2:
        run.font.size = Pt(13)
        h.paragraph_format.space_before = Pt(14)
        h.paragraph_format.space_after = Pt(4)
    return h

def add_p(text="", bold_prefix=None, space_after=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = 'Arial'
        r_pre.font.size = Pt(10.5)
        r_pre.font.bold = True
        r_pre.font.color.rgb = C_BLACK
    if text:
        r_txt = p.add_run(text)
        r_txt.font.name = 'Arial'
        r_txt.font.size = Pt(10.5)
        r_txt.font.color.rgb = C_BLACK
    return p

def add_bullet(text, bold_prefix=None):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = 'Arial'
        r_pre.font.size = Pt(10)
        r_pre.font.bold = True
        r_pre.font.color.rgb = C_BLACK
    if text:
        r_txt = p.add_run(text)
        r_txt.font.name = 'Arial'
        r_txt.font.size = Pt(10)
        r_txt.font.color.rgb = C_BLACK
    return p

# ==============================================================================
# COVER / TITLE BLOCK
# ==============================================================================
p_uni = doc.add_paragraph()
p_uni.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p_uni.add_run("DAYANANDA SAGAR UNIVERSITY (DSU) — SCHOOL OF ENGINEERING\n")
r.font.name = 'Arial'
r.font.size = Pt(13)
r.font.bold = True
r.font.color.rgb = C_NAVY

r2 = p_uni.add_run("DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING (AI & ML)\n")
r2.font.name = 'Arial'
r2.font.size = Pt(11)
r2.font.bold = True
r2.font.color.rgb = C_BLUE

r3 = p_uni.add_run("Capstone Project Phase-I (23AM4701) — Review-2 Report\nAcademic Year: 2026–2027")
r3.font.name = 'Arial'
r3.font.size = Pt(10)
r3.font.color.rgb = C_SLATE

# Title
p_title = doc.add_paragraph()
p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
p_title.paragraph_format.space_before = Pt(14)
p_title.paragraph_format.space_after = Pt(14)
r_t = p_title.add_run("AI-BASED CYBERSECURITY ASSISTANT TO DETECT AND DIAGNOSE NETWORK ATTACKS FOR SMART DEVICES")
r_t.font.name = 'Arial'
r_t.font.size = Pt(16)
r_t.font.bold = True
r_t.font.color.rgb = C_NAVY

# Team & Supervision Table
t_info = doc.add_table(rows=5, cols=2)
t_info.alignment = WD_TABLE_ALIGNMENT.CENTER
headers = ["Project Supervision", "Student Team (Batch)"]
for c_idx, h_text in enumerate(headers):
    cell = t_info.cell(0, c_idx)
    set_cell_background(cell, "E2E8F0")
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(h_text)
    r.font.name = 'Arial'
    r.font.size = Pt(10)
    r.font.bold = True
    r.font.color.rgb = C_NAVY

supervisors = [
    ("Supervisor / Guide:", "Dr. Sugandha Saxena, Associate Professor, Dept. of CSE (AI&ML)"),
    ("Co-Supervisor:", "Prof. Saurav Kumar, Assistant Professor, Dept. of CSE (AI&ML)"),
    ("Institution:", "Dayananda Sagar University, Harohalli Campus, Bengaluru"),
    ("Review Milestone:", "Review-2 Progress Submission (Completed & Operational Prototype)")
]
students = [
    ("Karthik Chitla", "ENG23AM0117"),
    ("Shaik Mohammed Arif", "ENG23AM0190"),
    ("Shaik Mohammed Danish", "ENG23AM0191"),
    ("T Vaishnavi", "ENG23AM0202")
]

for row_idx in range(1, 5):
    cell_sup = t_info.cell(row_idx, 0)
    cell_stu = t_info.cell(row_idx, 1)
    set_cell_background(cell_sup, "F8FAFC" if row_idx % 2 == 1 else "FFFFFF")
    set_cell_background(cell_stu, "F8FAFC" if row_idx % 2 == 1 else "FFFFFF")
    
    p_s = cell_sup.paragraphs[0]
    p_s.paragraph_format.space_after = Pt(2)
    r1 = p_s.add_run(f"{supervisors[row_idx-1][0]} ")
    r1.font.bold = True
    r1.font.size = Pt(9.5)
    r2 = p_s.add_run(supervisors[row_idx-1][1])
    r2.font.size = Pt(9.5)
    
    p_st = cell_stu.paragraphs[0]
    p_st.paragraph_format.space_after = Pt(2)
    r1_st = p_st.add_run(f"{students[row_idx-1][0]} ")
    r1_st.font.bold = True
    r1_st.font.size = Pt(9.5)
    r2_st = p_st.add_run(f"({students[row_idx-1][1]})")
    r2_st.font.size = Pt(9.5)

doc.add_page_break()

# ==============================================================================
# SECTION 1: INTRODUCTION
# ==============================================================================
add_header("1. Introduction", level=1)
add_bullet(" The rapid proliferation of smart devices, industrial IoT controllers, IP surveillance equipment, and connected consumer gadgets has significantly expanded the attack surface of modern networks. These edge devices communicate continuously over open internet protocols but possess constrained hardware architectures.", bold_prefix="Background: ")
add_bullet(" Smart peripherals lack the CPU cycles and memory capacity necessary to host traditional Endpoint Detection and Response (EDR) software or heavy local antivirus agents. Consequently, they often deploy with unhardened default credentials (e.g., Telnet/UPnP) and rarely receive vendor firmware updates, making them prime targets for botnet recruitment (e.g., Mirai) and volumetric attack staging.", bold_prefix="Motivation: ")
add_bullet(" Existing network security relies heavily on legacy signature-based Intrusion Detection Systems (IDS). These tools trigger overwhelming alert volumes (alert fatigue), miss slightly altered zero-day payloads, and output opaque binary warnings without contextualized root-cause explanations. Security analysts waste hours manually decoding packet dumps.", bold_prefix="The Operational Gap: ")
add_bullet(" This project introduces ZUKA SOC, an intelligent, out-of-band network intrusion detection and autonomous SOC assistance platform. ZUKA combines high-speed machine learning, Explainable AI (TreeSHAP), and an on-premises local language model to classify attacks, explain why an alert was triggered, correlate multi-stage incidents, and recommend tactical containment playbooks.", bold_prefix="Project Context: ")

# ==============================================================================
# SECTION 2: DOMAIN & SDG MAPPING
# ==============================================================================
add_header("2. Domain & Sustainable Development Goals (SDG) Mapping", level=1)
add_bullet(" Cybersecurity, Supervised Machine Learning (Gradient Boosted Trees), Deep Learning (MLP, 1D-CNN), Explainable Artificial Intelligence (XAI via TreeSHAP), and Security Orchestration, Automation, and Response (SOAR).", bold_prefix="AIML Domain: ")
add_bullet(" Ingest raw packet streams, transform network traffic into 14 statistical behavioral features, detect 13 distinct cyberattack classes, produce local Shapley attribution explanations, and provide natural language case investigations via a privacy-preserving local LLM.", bold_prefix="Technical Scope: ")
add_bullet(" By defending connected smart infrastructure, industrial IoT hubs, and cloud-edge networks against destructive volumetric attacks (DDoS/DoS) and botnet recruitment, ZUKA ensures reliable, resilient, and secure technological innovation.", bold_prefix="SDG 9 (Industry, Innovation, and Infrastructure): ")
add_bullet(" Fosters institutional data integrity, preserves immutable forensic audit records (via the PostgreSQL analyst_actions ledger), and ensures non-repudiation during cyber incident investigations.", bold_prefix="SDG 16 (Peace, Justice, and Strong Institutions): ")
add_bullet(" Strictly defensive and non-destructive. Focuses exclusively on passive network flow analysis and authorized containment; does not perform unauthorized penetration or network hacking.", bold_prefix="Ethical & Safety Boundary: ")

# ==============================================================================
# SECTION 3: PROBLEM STATEMENT & KEY CHALLENGES
# ==============================================================================
add_header("3. Problem Statement & Key Challenges", level=1)
add_p("Modern enterprise and IoT networks generate gigabytes of traffic per second containing both benign smart home telemetry and aggressive intrusions. Accurately detecting threats in real time while providing transparent forensic justifications to human operators remains a critical unresolved challenge.")
add_p("The project directly addresses five core industry challenges:")
add_bullet(" Real-time stream rates require sub-millisecond per-flow classification without introducing latency bottlenecks or dropping packets.", bold_prefix="1. High-Volume Network Traffic: ")
add_bullet(" In real-world networks, malicious flows comprise less than 0.002% of total packets (e.g., Infiltration = 0.0015%, Web Attacks = 0.0008%), causing naive classifiers to achieve deceptively high accuracy while failing to detect critical intrusions.", bold_prefix="2. Severe Class Imbalance: ")
add_bullet(" Normal high-throughput activities (e.g., HD IP camera video streaming or cloud backups) mimic volumetric floods, generating false alerts that overwhelm security analysts.", bold_prefix="3. False Positive Alert Fatigue: ")
add_bullet(" Deep neural networks produce classification scores without explaining which network attributes triggered the alert, creating trust barriers for operators.", bold_prefix="4. The Black-Box Dilemma: ")
add_bullet(" Detection tools operate in silos without linking prediction to explanation, incident dossiers, and verified mitigation.", bold_prefix="5. Operational Disconnect: ")

# ==============================================================================
# SECTION 4: PROJECT OBJECTIVES
# ==============================================================================
add_header("4. Project Objectives", level=1)
add_bullet(" Construct a high-throughput network flow ingestion and feature engineering pipeline that transforms raw packet captures into a unified 14-metric behavioral feature schema.", bold_prefix="Objective 1 (Data Ingestion & Flow Engineering): ")
add_bullet(" Implement, train, and empirically benchmark 10 distinct ML and DL architectures across 2,394,375 labeled flows, prioritizing Macro F1-score, minority recall, and inference latency.", bold_prefix="Objective 2 (Multi-Model Evaluation & Selection): ")
add_bullet(" Integrate a localized Explainable AI engine (TreeSHAP) to decompose individual attack predictions into exact feature attributions, eliminating black-box opacity for SOC analysts.", bold_prefix="Objective 3 (Explainable AI & Root-Cause Diagnosis): ")
add_bullet(" Build an end-to-end, production-grade SOC platform featuring a FastAPI backend, React 18 operations dashboard, PostgreSQL audit store, and a local privacy-preserving LLM assistant (Ollama qwen2.5:3b) with human-in-the-loop containment.", bold_prefix="Objective 4 (Full-Stack SOC Platform & Autonomous Co-Pilot): ")

# ==============================================================================
# SECTION 5: PROJECT SCOPE
# ==============================================================================
add_header("5. Project Scope & Operational Boundaries", level=1)
add_bullet(" Offline and live streaming traffic replay; unified 14-feature statistical schema; scratch training and comparative evaluation of 10 ML/DL models; deployment of TreeSHAP; development of full-stack prototype (FastAPI, React 18, PostgreSQL); local Ollama LLM assistant (Zuka); and human-in-the-loop containment directives.", bold_prefix="Covered in Phase-I: ")
add_bullet(" No unauthorized active penetration testing or external network hacking; no ASIC/FPGA hardware synthesis; containment directives remain advisory and gated by human analyst confirmation.", bold_prefix="Limitations & Boundaries: ")
add_bullet(" Smart Devices, IoT Gateways, Campus Networks, and Enterprise SOC Environments.", bold_prefix="Target Application Domain: ")

# ==============================================================================
# SECTION 6: LITERATURE REVIEW & BASE PAPER
# ==============================================================================
add_header("6. Literature Review & Base Paper Analysis", level=1)
add_p("A thorough literature review of 10 recent research papers (2023–2025) was conducted to identify limitations in contemporary NIDS solutions:")

# Table of Literature
t_lit = doc.add_table(rows=11, cols=5)
t_lit.alignment = WD_TABLE_ALIGNMENT.CENTER
lit_cols = ["SN", "Paper Title & Year", "Algorithm", "Dataset", "Identified Research Gap"]
for idx, col_name in enumerate(lit_cols):
    c = t_lit.cell(0, idx)
    set_cell_background(c, "0A2540")
    p = c.paragraphs[0]
    r = p.add_run(col_name)
    r.font.bold = True
    r.font.size = Pt(8.5)
    r.font.color.rgb = RGBColor(255, 255, 255)

lit_data = [
    ("1", "Cutting-Edge IDS in IoT Networks (2024)", "Ensemble ML (XGBoost, RF, Extra Trees)", "IoT Traffic", "Performance varies across IoT topologies; lacks real-time local XAI."),
    ("2", "ST-IAOA-XGBoost for WSN (2025)", "ST-IAOA-XGBoost + SMOTE-Tomek", "WSN-DS, KDD99", "Heavy optimization search space impedes streaming line-rate inference."),
    ("3", "Detecting Unbalanced Intrusions with DL (2024)", "XGBoost, LSTM, Mini-VGGNet, AlexNet", "Imbalanced Traffic", "High overall accuracy masks poor detection rates on extreme minority classes."),
    ("4", "E-XAI: Evaluating Black-Box XAI (2024)", "SHAP, LIME + Multiple AI Models", "3 NIDS Datasets", "Discrepancy between SHAP/LIME; lacks conversion into actionable SOC diagnosis."),
    ("5", "Dynamic Attack Detection with Q-Learning (2024)", "Ensemble ML + MFO + Q-Learning + XAI", "Dynamic IoT Flows", "Excessive computational overhead; heavy reliance on clean training data."),
    ("6", "A-NIDS: Adaptive NIDS with CTGAN (2025)", "Shallow NN + Clustering + CTGAN", "CIC-IDS2017/2018", "Complex generative retraining cycle; prone to mode collapse on rare flows."),
    ("7", "Addressing Class Imbalance via Resampling (2023)", "MLP, CNN, CNN-BLSTM + ADASYN", "NSL-KDD", "Tested on legacy synthetic benchmarks; requires validation on modern traffic."),
    ("8", "From Zero-Shot ML to Zero-Day Detection (2023)", "Random Forest + MLP + Zero-Shot", "UNSW-NB15", "Unseen low-footprint attacks (Fuzzers, Exploits) remain difficult to detect."),
    ("9", "Lightweight DL with Feature Selection & XAI (2025)", "DNN + Bi-LSTM + GA + LIME", "CIC-IDS2017, UNSW", "Multi-stage genetic feature selection too slow for streaming line-rate SOCs."),
    ("10", "Enhancing ML Models Using SMOTE (2024)", "RF, SVM, KNN, XGBoost + SMOTE", "NSL-KDD", "Over-sampling synthetic samples inflates latency; lacks full SOC integration.")
]

for row_i, data_row in enumerate(lit_data, start=1):
    for col_i, val in enumerate(data_row):
        c = t_lit.cell(row_i, col_i)
        set_cell_background(c, "F8FAFC" if row_i % 2 == 1 else "FFFFFF")
        p = c.paragraphs[0]
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(val)
        r.font.size = Pt(8.0)

# Base Paper Details
add_header("Base Paper Analysis & Novelty", level=2)
add_bullet(" 'Joint Rough Set Theory and XGBoost-Based Learning for Network Intrusion Detection System' — Published in IEEE Internet of Things Journal, vol. 12, no. 7, pp. 7930–7937, Apr. 2025.", bold_prefix="Base Paper: ")
add_bullet(" Combines Rough Set Theory (RST) attribute reduction with XGBoost. However, it lacks a comparative evaluation against deep learning architectures, provides no local explainability (SHAP/XAI) for forensic justification, and lacks an operational full-stack SOC assistant platform.", bold_prefix="Gaps in Base Paper: ")
add_bullet(" 1) Rigorous ML vs DL comparative benchmarking across 2.39M flows; 2) Multi-criteria model selection optimized for extreme class imbalance; 3) TreeSHAP local feature attribution per alert; 4) Closed-loop full-stack SOC platform integrating FastAPI, React 18, and an on-premises Ollama LLM co-pilot.", bold_prefix="Four Pillars of Novelty: ")

# ==============================================================================
# SECTION 7: METHODOLOGY & ARCHITECTURE
# ==============================================================================
add_header("7. Methodology / Approach & Architecture", level=1)
add_p("The ZUKA SOC methodology is structured across six sequential stages flowing from left to right:")

if ARCH_IMG_PATH.exists():
    doc.add_picture(str(ARCH_IMG_PATH), width=Inches(6.5))
    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_c = p_cap.add_run("Figure 1: End-to-end ZUKA SOC system architecture and operational pipeline.")
    r_c.font.size = Pt(8.5)
    r_c.font.italic = True
    r_c.font.color.rgb = C_SLATE

add_bullet(" Captures live packet streams and PCAP replays via an asynchronous socket listener, assembling bidirectional flow records without packet loss.", bold_prefix="1. Traffic Ingestion: ")
add_bullet(" Extracts 14 core statistical behavioral metrics per flow (packet rates, byte rates, IAT means, flow duration) aligned with standardized feature schemas.", bold_prefix="2. Feature Engineering Pipeline: ")
add_bullet(" Evaluates the flow vector using the unified multi-class XGBoost classifier trained on 2,561,658 network flows, delivering 99.87% accuracy with sub-0.05 ms inference latency.", bold_prefix="3. AI Threat Detection: ")
add_bullet(" Computes exact local Shapley feature attribution values (TreeSHAP) per prediction, isolating the decisive flow metrics triggering the detection.", bold_prefix="4. Explainable AI (TreeSHAP): ")
add_bullet(" Maps model confidence and impact into a standardized priority matrix (P1–P4, Critical/High/Medium/Low), automatically generating correlated forensic case dossiers (INV-...).", bold_prefix="5. Severity & Case Triage: ")
add_bullet(" Security analysts verify forensic evidence in the React dashboard with grounded guidance from the local Ollama LLM co-pilot.", bold_prefix="6. SOC Analyst & Cognitive Co-Pilot: ")
add_bullet(" Analyst-authorized defensive directives (Ingress IP Drop and VLAN Quarantine) are dispatched back to the network boundary, completing the defensive cycle.", bold_prefix="7. Closed-Loop Containment: ")

# ==============================================================================
# SECTION 8: DATA COLLECTION & PREPROCESSING
# ==============================================================================
add_header("8. Sample of Data Collection & Preprocessing", level=1)
add_p("The model training and evaluation pipeline utilizes 2,394,375 labeled network flow records sourced primarily from the Canadian Institute for Cybersecurity (CIC-IDS2017) benchmark, augmented by contemporary attack vectors from UNSW-NB15:")

# Class Imbalance Table
t_imb = doc.add_table(rows=15, cols=5)
t_imb.alignment = WD_TABLE_ALIGNMENT.CENTER
imb_cols = ["Class ID", "Attack Category", "Training Samples", "Testing Samples", "Percentage (%)"]
for idx, col_name in enumerate(imb_cols):
    c = t_imb.cell(0, idx)
    set_cell_background(c, "0A2540")
    p = c.paragraphs[0]
    r = p.add_run(col_name)
    r.font.bold = True
    r.font.size = Pt(8.5)
    r.font.color.rgb = RGBColor(255, 255, 255)

imb_data = [
    ("0", "BENIGN (Normal Traffic)", "1,582,247", "395,562", "82.60%"),
    ("1", "Bot (Mirai / Ares)", "1,558", "390", "0.081%"),
    ("2", "DDoS (Volumetric Flood)", "102,411", "25,603", "5.35%"),
    ("3", "DoS GoldenEye", "898", "224", "0.047%"),
    ("4", "DoS Hulk", "138,277", "34,569", "7.22%"),
    ("5", "DoS Slowhttptest", "4,182", "1,046", "0.218%"),
    ("6", "DoS Slowloris", "4,308", "1,077", "0.225%"),
    ("7", "FTP-Patator (Brute Force)", "4,745", "1,186", "0.248%"),
    ("8", "Infiltration (Lateral Pivoting)", "29", "7", "0.0015%"),
    ("9", "PortScan (Reconnaissance)", "72,555", "18,139", "3.79%"),
    ("10", "SSH-Patator (Brute Force)", "2,575", "644", "0.134%"),
    ("11", "Web Attack — Brute Force", "1,176", "294", "0.061%"),
    ("12", "Web Attack — SQL Injection", "17", "4", "0.0008%"),
    ("13", "Web Attack — XSS", "522", "130", "0.027%")
]

for row_i, data_row in enumerate(imb_data, start=1):
    for col_i, val in enumerate(data_row):
        c = t_imb.cell(row_i, col_i)
        set_cell_background(c, "F8FAFC" if row_i % 2 == 1 else "FFFFFF")
        p = c.paragraphs[0]
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(val)
        r.font.size = Pt(8.0)
        if col_i in (0, 4):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

add_p("Preprocessing Workflow:", bold_prefix=None)
add_bullet(" Infinite values (inf, -inf) were clipped to the maximum valid feature value; missing records were imputed using feature medians; exact duplicate flow timestamps were deduplicated.", bold_prefix="Data Cleaning: ")
add_bullet(" Flow duration, source/destination packet rates, byte transfer rates, mean packet sizes, and inter-arrival time (IAT) means.", bold_prefix="14 Unified Features: ")
add_bullet(" Scikit-Learn StandardScaler was fitted exclusively on training flows to prevent data leakage, generating standardized tensors for neural networks and tree ensembles.", bold_prefix="Feature Scaling: ")

# ==============================================================================
# SECTION 9: TOOLS & TECHNOLOGIES
# ==============================================================================
add_header("9. Tools & Technologies", level=1)
add_bullet(" Python 3.13 (Backend API, Data Engineering, ML/DL Training), TypeScript (Frontend).", bold_prefix="Programming Languages: ")
add_bullet(" XGBoost (xgboost), Scikit-Learn, CatBoost, LightGBM, Keras/TensorFlow.", bold_prefix="Machine Learning & DL: ")
add_bullet(" SHAP (shap.TreeExplainer for exact localized Shapley attribution).", bold_prefix="Explainable AI: ")
add_bullet(" FastAPI (Asynchronous ASGI REST API), SQLAlchemy 2.0 (ORM), Alembic, python-jose (JWT).", bold_prefix="Backend Stack: ")
add_bullet(" React 18, Vite, Lucide Icons, Axios, Tailwind CSS / Scoped CSS modules.", bold_prefix="Frontend Stack: ")
add_bullet(" Local Ollama runtime hosting qwen2.5:3b / llama3.2:1b (100% on-premises privacy).", bold_prefix="AI Assistant Co-Pilot: ")
add_bullet(" PostgreSQL (Relational schema for alerts, incidents, dossiers, and audit ledgers).", bold_prefix="Database & Storage: ")
add_bullet(" VS Code, Jupyter/Colab, PyTest, Matplotlib, ReportLab PDF generation.", bold_prefix="Testing & Tooling: ")

# ==============================================================================
# SECTION 10: EXPECTED OUTCOMES & EMPIRICAL RESULTS (REVIEW-2 MILESTONE)
# ==============================================================================
add_header("10. Expected Outcomes & Empirical Results (Review-2 Milestone)", level=1)
add_p("A critical technical breakthrough achieved between Review-1 and Review-2 was the resolution of the deep learning normalization defect:")
add_bullet(" In the preliminary Review-1 notebook, unscaled raw features were passed into deep neural networks that had been trained on standardized inputs, collapsing MLP accuracy to 27.75%.", bold_prefix="Identified Defect: ")
add_bullet(" Corrected feature scaling pipeline and serialized fitted StandardScaler instances, restoring Deep MLP accuracy to 93.11% (Weighted F1: 0.9441) and 1D-CNN accuracy to 86.88% (Weighted F1: 0.9014).", bold_prefix="Resolution: ")

add_p("Table 1: Deep Learning Models Evaluation (Test Set: 478,875 flows):", bold_prefix=None)
t_dl = doc.add_table(rows=4, cols=8)
t_dl.alignment = WD_TABLE_ALIGNMENT.CENTER
dl_cols = ["Model", "Accuracy", "Balanced Acc", "Macro F1", "Weighted Prec", "Weighted Rec", "Weighted F1", "Inference Time"]
for idx, col_name in enumerate(dl_cols):
    c = t_dl.cell(0, idx)
    set_cell_background(c, "0A2540")
    p = c.paragraphs[0]
    r = p.add_run(col_name)
    r.font.bold = True
    r.font.size = Pt(8.0)
    r.font.color.rgb = RGBColor(255, 255, 255)

dl_data = [
    ("Deep MLP", "93.11%", "82.09%", "0.5107", "96.55%", "93.11%", "0.9441", "2.08s"),
    ("Standard MLP", "91.16%", "78.80%", "0.4909", "96.27%", "91.16%", "0.9315", "1.82s"),
    ("1D-CNN", "86.88%", "75.61%", "0.4033", "95.37%", "86.88%", "0.9014", "22.51s")
]
for row_i, data_row in enumerate(dl_data, start=1):
    for col_i, val in enumerate(data_row):
        c = t_dl.cell(row_i, col_i)
        set_cell_background(c, "F8FAFC" if row_i % 2 == 1 else "FFFFFF")
        p = c.paragraphs[0]
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(val)
        r.font.size = Pt(8.0)

add_p("Table 2: Machine Learning Classifiers Benchmark (Test Set: 478,875 flows):", bold_prefix=None)
t_ml = doc.add_table(rows=8, cols=8)
t_ml.alignment = WD_TABLE_ALIGNMENT.CENTER
ml_cols = ["Rank", "Model", "Family", "Test Accuracy", "Balanced Acc", "Macro F1", "Weighted F1", "Status"]
for idx, col_name in enumerate(ml_cols):
    c = t_ml.cell(0, idx)
    set_cell_background(c, "0A2540")
    p = c.paragraphs[0]
    r = p.add_run(col_name)
    r.font.bold = True
    r.font.size = Pt(8.0)
    r.font.color.rgb = RGBColor(255, 255, 255)

ml_data = [
    ("1", "XGBoost", "Gradient Boosted Trees", "99.87%", "85.22%", "0.8753", "0.9986", "HIRED (Champion)"),
    ("2", "Random Forest", "Bagged Trees", "99.78%", "77.05%", "0.7920", "0.9978", "Secondary Verifier"),
    ("3", "Decision Tree", "Single Tree", "99.79%", "73.63%", "0.7456", "0.9978", "Baseline"),
    ("4", "CatBoost", "Gradient Boosted Trees", "99.73%", "71.21%", "0.7226", "0.9971", "Benchmark"),
    ("5", "Logistic Regression", "Linear Model", "97.48%", "57.78%", "0.5937", "0.9749", "Baseline"),
    ("6", "LightGBM", "Gradient Boosted Trees", "92.51%", "29.80%", "0.2922", "0.9250", "Rejected"),
    ("7", "Dummy Classifier", "Majority Baseline", "82.60%", "7.14%", "0.0646", "0.7473", "Null Reference")
]
for row_i, data_row in enumerate(ml_data, start=1):
    for col_i, val in enumerate(data_row):
        c = t_ml.cell(row_i, col_i)
        set_cell_background(c, "F8FAFC" if row_i % 2 == 1 else "FFFFFF")
        p = c.paragraphs[0]
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(val)
        r.font.size = Pt(8.0)

add_bullet(" 99.866% test accuracy and 0.8753 Macro F1 across all 14 categories, maintaining high detection on minority attack classes.", bold_prefix="1. Superior Accuracy & F1: ")
add_bullet(" Evaluated 478,875 flows in only 4.92 seconds (<0.010 ms per flow), qualifying for streaming line-rate defense.", bold_prefix="2. Sub-Millisecond Latency: ")
add_bullet(" Fully compatible with fast TreeExplainer SHAP attribution (<12 ms per alert).", bold_prefix="3. Native Explainability: ")

# ==============================================================================
# SECTION 11: TIMELINE (GANTT CHART)
# ==============================================================================
add_header("11. Timeline (Updated Gantt Chart)", level=1)
add_p("Current milestone progress for Capstone Phase-I Review-2:")

t_gantt = doc.add_table(rows=18, cols=3)
t_gantt.alignment = WD_TABLE_ALIGNMENT.CENTER
gantt_cols = ["Module / Activity", "Target Timeline", "Review-2 Progress Status"]
for idx, col_name in enumerate(gantt_cols):
    c = t_gantt.cell(0, idx)
    set_cell_background(c, "0A2540")
    p = c.paragraphs[0]
    r = p.add_run(col_name)
    r.font.bold = True
    r.font.size = Pt(8.5)
    r.font.color.rgb = RGBColor(255, 255, 255)

gantt_data = [
    ("1. Requirements & Problem Analysis", "Jul (W4)", "COMPLETED (✓)"),
    ("2. Literature Survey & Research Gap Identification", "Jul – Aug", "COMPLETED (✓)"),
    ("3. Dataset Collection & Exploratory Data Analysis", "Aug", "COMPLETED (✓)"),
    ("4. Feature Engineering & Preprocessing Pipeline", "Aug – Sep", "COMPLETED (✓)"),
    ("5. ML/DL Model Training & Comprehensive Benchmarking", "Aug – Sep", "COMPLETED (✓)"),
    ("6. TreeSHAP Explainable AI (XAI) Integration", "Sep", "COMPLETED (✓)"),
    ("7. Relational Database Schema & FastAPI Backend", "Sep – Oct", "COMPLETED (✓)"),
    ("8. Alert Center & Telemetry Stream Engine", "Sep", "COMPLETED (✓)"),
    ("9. Incident Management & Forensic Dossiers", "Sep – Oct", "COMPLETED (✓)"),
    ("10. Tactical Defense Containment Engine (SOAR)", "Oct", "COMPLETED (✓)"),
    ("11. ZUKA Cognitive Co-Pilot (Ollama RAG Engine)", "Oct", "COMPLETED (✓)"),
    ("12. React 18 Operations Dashboard UI Integration", "Oct", "COMPLETED (✓)"),
    ("13. Role-Based Access Control (RBAC) & Security", "Sep – Oct", "COMPLETED (✓)"),
    ("14. Immutable Audit Ledger & Compliance Logging", "Oct", "COMPLETED (✓)"),
    ("15. System End-to-End Testing & Verification", "Oct", "COMPLETED (✓)"),
    ("16. Performance Optimization & Latency Tuning", "Oct", "COMPLETED (✓)"),
    ("17. Capstone Phase-I Review-2 Documentation & Slides", "Oct", "COMPLETED (✓)")
]

for row_i, data_row in enumerate(gantt_data, start=1):
    for col_i, val in enumerate(data_row):
        c = t_gantt.cell(row_i, col_i)
        set_cell_background(c, "F8FAFC" if row_i % 2 == 1 else "FFFFFF")
        p = c.paragraphs[0]
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(val)
        r.font.size = Pt(8.0)
        if col_i == 2:
            r.font.bold = True
            r.font.color.rgb = RGBColor(16, 120, 50)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

# ==============================================================================
# SECTION 12: REFERENCES
# ==============================================================================
add_header("12. References (IEEE Format)", level=1)
refs = [
    "[1] N. U. Sama, S. Ullah, S. M. A. Kazmi, and M. Mazzara, 'Cutting-edge intrusion detection in IoT networks: A focus on ensemble models,' IEEE Access, vol. 13, pp. 8375–8392, Nov. 2024, doi: 10.1109/ACCESS.2024.3491831.",
    "[2] L. Jiang, H. Gu, L. Xie, H. Yang, and Z. Na, 'ST-IAOA-XGBoost: An efficient data-balanced intrusion detection method for WSN,' IEEE Sensors Journal, vol. 25, no. 1, pp. 1768–1783, Jan. 2025, doi: 10.1109/JSEN.2024.3489623.",
    "[3] S. Pavithra and K. V. Vikas, 'Detecting unbalanced network traffic intrusions with deep learning,' IEEE Access, vol. 12, pp. 74096–74107, May 2024, doi: 10.1109/ACCESS.2024.3405187.",
    "[4] O. Arreche, T. R. Guntur, J. W. Roberts, and M. Abdallah, 'E-XAI: Evaluating black-box explainable AI frameworks for network intrusion detection,' IEEE Access, vol. 12, pp. 23954–23988, Feb. 2024, doi: 10.1109/ACCESS.2024.3365140.",
    "[5] C. Zha, Z. Wang, Y. Fan, B. Bai, Y. Zhang, S. Shi, and R. Zhang, 'A-NIDS: Adaptive network intrusion detection system based on clustering and stacked CTGAN,' IEEE Transactions on Information Forensics and Security, vol. 20, pp. 3204–3219, Mar. 2025, doi: 10.1109/TIFS.2025.3551643.",
    "[6] A. Abdelkhalek and M. Mashaly, 'Addressing the class imbalance problem in network intrusion detection systems using data resampling and deep learning,' The Journal of Supercomputing, vol. 79, pp. 10611–10644, Feb. 2023, doi: 10.1007/s11227-023-05073-x.",
    "[7] M. Sarhan, S. Layeghy, M. Gallagher, and M. Portmann, 'From zero-shot machine learning to zero-day attack detection,' International Journal of Information Security, vol. 22, pp. 947–959, Mar. 2023, doi: 10.1007/s10207-023-00676-0.",
    "[8] A. Khan, M. A. Hussain, and F. Anwer, 'A hybrid lightweight deep learning-based intrusion detection approach in IoT utilizing feature selection & explainable artificial intelligence,' IEEE Access, vol. 13, pp. 192451–192466, Nov. 2025, doi: 10.1109/ACCESS.2025.3630753.",
    "[9] 'Enhancing machine learning models for attack detection using SMOTE,' in Proc. 2024 Int. Conf. Integrated Intelligence and Communication Systems (ICIICS), 2024, doi: 10.1109/ICIICS63763.2024.10859848.",
    "[10] S. Author(s), 'SHAP-guided feature selection for cross-dataset generalization in network intrusion detection systems,' IEEE Access, vol. 14, pp. 90926–90936, Jun. 2026, doi: 10.1109/ACCESS.2026.3703481.",
    "[11] N. Alsabilah and D. B. Rawat, 'Joint rough set theory and XGBoost-based learning for network intrusion detection system,' IEEE Internet of Things Journal, vol. 12, no. 7, pp. 7930–7937, Apr. 2025, doi: 10.1109/JIOT.2025.3528452."
]

for ref in refs:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(ref)
    r.font.name = 'Arial'
    r.font.size = Pt(8.5)
    r.font.color.rgb = C_BLACK

doc.save(str(OUTPUT_PATH))
print(f"Document successfully created at: {OUTPUT_PATH}")
