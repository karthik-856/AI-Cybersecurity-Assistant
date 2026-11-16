"""
================================================================================
ZUKA — AI CYBERSECURITY SOC ASSISTANT
================================================================================

Persistent Streamlit SOC dashboard.

Architecture:

    Network Flow
        ↓
    TrafficCollector
        ↓
    FeaturePipeline
        ↓
    XGBoost Detection
        ↓
    SHAP Explainability
        ↓
    SOC Alert Engine
        ↓
    Recommendation Engine
        ↓
    SQLite AlertStore
        ↓
    ZUKA SOC Dashboard
        ↓
    Human Analyst

Run from project root:

    python -m streamlit run src/dashboard/app.py

Important:
    - Dashboard reads persistent SQLite SOC data.
    - Active alerts are NEW and INVESTIGATING.
    - RESOLVED alerts remain in history.
    - No manual 78-feature entry is required.
    - Automated containment is disabled.
    - Human analyst approval is required.
================================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st


# =============================================================================
# PROJECT PATH
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# =============================================================================
# ZUKA IMPORTS
# =============================================================================

from storage.alert_store import AlertStore


# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="ZUKA — SOC Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# CUSTOM CSS
# =============================================================================

st.markdown(
    """
    <style>

    .zuka-title {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 0;
    }

    .zuka-subtitle {
        font-size: 17px;
        color: #6b7280;
        margin-bottom: 25px;
    }

    .status-critical {
        padding: 18px;
        border-radius: 10px;
        border-left: 6px solid #dc2626;
        background-color: #fee2e2;
        margin-bottom: 15px;
    }

    .status-warning {
        padding: 18px;
        border-radius: 10px;
        border-left: 6px solid #f59e0b;
        background-color: #fef3c7;
        margin-bottom: 15px;
    }

    .status-safe {
        padding: 18px;
        border-radius: 10px;
        border-left: 6px solid #16a34a;
        background-color: #dcfce7;
        margin-bottom: 15px;
    }

    .status-info {
        padding: 18px;
        border-radius: 10px;
        border-left: 6px solid #2563eb;
        background-color: #dbeafe;
        margin-bottom: 15px;
    }

    .alert-card {
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #d1d5db;
        margin-bottom: 10px;
    }

    .small-text {
        font-size: 13px;
        color: #6b7280;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# LOGGING
# =============================================================================

def log(message: str) -> None:
    print(
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"ZUKA DASHBOARD | {message}"
    )


# =============================================================================
# DATABASE
# =============================================================================

DEFAULT_DATABASE = PROJECT_ROOT / "data" / "zuka_soc.db"


@st.cache_resource
def get_alert_store() -> AlertStore:
    """
    Create one persistent AlertStore instance for the Streamlit application.
    """

    store = AlertStore(database_path=DEFAULT_DATABASE)

    log(f"Connected to SQLite database: {DEFAULT_DATABASE}")

    return store


store = get_alert_store()


# =============================================================================
# DATA HELPERS
# =============================================================================

def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize database data for dashboard display.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()

    # Normalize common database column names.
    rename_map = {
        "alert_id": "Alert_ID",
        "event_id": "Event_ID",
        "timestamp": "Timestamp",
        "source": "Source",
        "predicted_class": "Predicted_Class",
        "confidence": "Confidence",
        "detection": "Detection",
        "confidence_level": "Confidence_Level",
        "severity": "Severity",
        "soc_priority": "SOC_Priority",
        "soc_response_category": "SOC_Response_Category",
        "top_feature_1": "Top_Feature_1",
        "top_feature_1_value": "Top_Feature_1_Value",
        "top_feature_1_shap": "Top_Feature_1_SHAP",
        "top_feature_2": "Top_Feature_2",
        "top_feature_2_value": "Top_Feature_2_Value",
        "top_feature_2_shap": "Top_Feature_2_SHAP",
        "top_feature_3": "Top_Feature_3",
        "top_feature_3_value": "Top_Feature_3_Value",
        "top_feature_3_shap": "Top_Feature_3_SHAP",
        "xai_explanation": "XAI_Explanation",
        "analyst_recommendation": "Analyst_Recommendation",
        "status": "Status",
        "analyst": "Analyst",
        "notes": "Notes",
        "created_at": "Created_At",
        "updated_at": "Updated_At",
    }

    for old, new in rename_map.items():
        if old in result.columns and new not in result.columns:
            result.rename(columns={old: new}, inplace=True)

    # Ensure important columns exist.
    defaults = {
        "Alert_ID": "",
        "Event_ID": "",
        "Timestamp": "",
        "Source": "",
        "Predicted_Class": "",
        "Confidence": 0.0,
        "Detection": "",
        "Severity": "NONE",
        "SOC_Priority": "NONE",
        "SOC_Response_Category": "",
        "XAI_Explanation": "",
        "Analyst_Recommendation": "",
        "Status": "",
    }

    for column, default in defaults.items():
        if column not in result.columns:
            result[column] = default

    result["Confidence"] = pd.to_numeric(
        result["Confidence"],
        errors="coerce",
    ).fillna(0.0)

    result["Detection"] = (
        result["Detection"]
        .astype(str)
        .str.upper()
    )

    result["Severity"] = (
        result["Severity"]
        .astype(str)
        .str.upper()
    )

    result["SOC_Priority"] = (
        result["SOC_Priority"]
        .astype(str)
        .str.upper()
    )

    result["Status"] = (
        result["Status"]
        .astype(str)
        .str.upper()
    )

    return result


def get_active_alerts() -> pd.DataFrame:
    """
    Retrieve NEW and INVESTIGATING alerts.
    """

    try:
        alerts = store.get_active_alerts()

        if alerts is None or alerts.empty:
            return pd.DataFrame()

        return normalize_dataframe(alerts)

    except Exception as exc:
        log(f"Failed loading active alerts: {exc}")
        st.error(f"Unable to load active alerts: {exc}")
        return pd.DataFrame()


def get_history() -> pd.DataFrame:
    """
    Retrieve historical alerts.
    """

    try:
        alerts = store.get_alerts()

        if alerts is None or alerts.empty:
            return pd.DataFrame()

        return normalize_dataframe(alerts)

    except Exception as exc:
        log(f"Failed loading alert history: {exc}")
        st.error(f"Unable to load alert history: {exc}")
        return pd.DataFrame()


# =============================================================================
# HEADER
# =============================================================================

st.markdown(
    '<div class="zuka-title">🛡️ ZUKA — AI Cybersecurity SOC</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="zuka-subtitle">'
    "Persistent SOC Monitoring • XGBoost • SHAP • Alert Intelligence"
    "</div>",
    unsafe_allow_html=True,
)


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:

    st.header("🛡️ ZUKA")

    st.caption("AI Cybersecurity SOC Assistant")

    st.divider()

    st.subheader("Pipeline")

    st.success("Traffic Ingestion")
    st.success("Feature Processing")
    st.success("XGBoost Detection")
    st.success("SHAP Explainability")
    st.success("SOC Alert Engine")
    st.success("Recommendation Engine")
    st.success("SQLite Persistence")
    st.success("SOC Dashboard")

    st.divider()

    st.subheader("System")

    st.write(
        f"**Python:** {sys.version.split()[0]}"
    )

    st.write(
        f"**Project:** `{PROJECT_ROOT.name}`"
    )

    st.write(
        f"**Database:** `{DEFAULT_DATABASE.name}`"
    )

    st.divider()

    if st.button(
        "🔄 Refresh Dashboard",
        use_container_width=True,
    ):
        st.rerun()

    st.divider()

    st.caption(
        "Human analyst approval is required before "
        "escalation or containment."
    )

    st.caption(
        "Automated containment: DISABLED"
    )


# =============================================================================
# LOAD DATA
# =============================================================================

active_df = get_active_alerts()
history_df = get_history()


# =============================================================================
# DATABASE STATISTICS
# =============================================================================

try:
    statistics = store.get_statistics()
except Exception as exc:
    log(f"Failed loading statistics: {exc}")
    statistics = {
        "total": len(history_df),
        "new": 0,
        "investigating": 0,
        "resolved": 0,
        "escalated": 0,
        "active_p1": 0,
    }


total_alerts = int(statistics.get("total", 0))
new_count = int(statistics.get("new", 0))
investigating_count = int(statistics.get("investigating", 0))
resolved_count = int(statistics.get("resolved", 0))
escalated_count = int(statistics.get("escalated", 0))
active_p1 = int(statistics.get("active_p1", 0))


# =============================================================================
# SECURITY STATUS
# =============================================================================

if active_p1 > 0:

    st.markdown(
        """
        <div class="status-critical">
        <strong>🚨 SECURITY STATUS: P1 ALERTS REQUIRE ATTENTION</strong><br>
        One or more active P1 alerts require human analyst investigation.
        </div>
        """,
        unsafe_allow_html=True,
    )

elif investigating_count > 0:

    st.markdown(
        """
        <div class="status-warning">
        <strong>⚠️ SECURITY STATUS: ACTIVE INVESTIGATION</strong><br>
        One or more alerts are currently being investigated by the SOC.
        </div>
        """,
        unsafe_allow_html=True,
    )

elif new_count > 0:

    st.markdown(
        """
        <div class="status-warning">
        <strong>⚠️ SECURITY STATUS: NEW ALERTS AVAILABLE</strong><br>
        New alerts are waiting for analyst review.
        </div>
        """,
        unsafe_allow_html=True,
    )

else:

    st.markdown(
        """
        <div class="status-safe">
        <strong>🟢 SECURITY STATUS: NO ACTIVE ALERTS</strong><br>
        There are currently no NEW or INVESTIGATING alerts.
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# KPI CARDS
# =============================================================================

st.subheader("SOC Overview")

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(
        "TOTAL ALERTS",
        f"{total_alerts:,}",
    )

with col2:
    st.metric(
        "NEW",
        f"{new_count:,}",
    )

with col3:
    st.metric(
        "INVESTIGATING",
        f"{investigating_count:,}",
    )

with col4:
    st.metric(
        "RESOLVED",
        f"{resolved_count:,}",
    )

with col5:
    st.metric(
        "ESCALATED",
        f"{escalated_count:,}",
    )

with col6:
    st.metric(
        "ACTIVE P1",
        f"{active_p1:,}",
    )


# =============================================================================
# ACTIVE ALERT QUEUE
# =============================================================================

st.divider()

st.subheader("🚨 Active SOC Alert Queue")

st.caption(
    "Active alerts include NEW and INVESTIGATING alerts only."
)

if active_df.empty:

    st.success(
        "No active alerts. The SOC queue is currently clear."
    )

else:

    active_display_columns = [
        "Alert_ID",
        "Timestamp",
        "Predicted_Class",
        "Confidence",
        "Detection",
        "Severity",
        "SOC_Priority",
        "Status",
        "SOC_Response_Category",
    ]

    active_display_columns = [
        column
        for column in active_display_columns
        if column in active_df.columns
    ]

    display_active = active_df[active_display_columns].copy()

    if "Confidence" in display_active.columns:
        display_active["Confidence"] = (
            display_active["Confidence"] * 100
        ).round(2)

    st.dataframe(
        display_active,
        use_container_width=True,
        hide_index=True,
    )


# =============================================================================
# ALERT INVESTIGATION
# =============================================================================

st.divider()

st.subheader("🔎 Alert Investigation")

if active_df.empty:

    st.info(
        "There are no active alerts available for investigation."
    )

else:

    alert_ids = (
        active_df["Alert_ID"]
        .astype(str)
        .tolist()
    )

    selected_alert_id = st.selectbox(
        "Select an active alert",
        alert_ids,
    )

    selected_rows = active_df[
        active_df["Alert_ID"].astype(str)
        == str(selected_alert_id)
    ]

    if selected_rows.empty:

        st.warning("Selected alert could not be loaded.")

    else:

        alert = selected_rows.iloc[0]

        # ---------------------------------------------------------------------
        # DETECTION INFORMATION
        # ---------------------------------------------------------------------

        left, right = st.columns(2)

        with left:

            st.markdown("### Detection")

            st.write(
                f"**Alert ID:** {alert.get('Alert_ID', 'N/A')}"
            )

            st.write(
                f"**Event ID:** {alert.get('Event_ID', 'N/A')}"
            )

            st.write(
                f"**Predicted Class:** "
                f"{alert.get('Predicted_Class', 'N/A')}"
            )

            confidence = float(
                alert.get("Confidence", 0.0)
            )

            st.write(
                f"**Confidence:** "
                f"{confidence * 100:.2f}%"
            )

            st.write(
                f"**Detection:** "
                f"{alert.get('Detection', 'N/A')}"
            )

            st.write(
                f"**Severity:** "
                f"{alert.get('Severity', 'N/A')}"
            )

            st.write(
                f"**SOC Priority:** "
                f"{alert.get('SOC_Priority', 'N/A')}"
            )

            st.write(
                f"**Status:** "
                f"{alert.get('Status', 'N/A')}"
            )

            st.write(
                f"**Source:** "
                f"{alert.get('Source', 'N/A')}"
            )

        # ---------------------------------------------------------------------
        # SHAP EVIDENCE
        # ---------------------------------------------------------------------

        with right:

            st.markdown("### 🧠 SHAP Evidence")

            shap_found = False

            for number in range(1, 4):

                feature = alert.get(
                    f"Top_Feature_{number}",
                    None,
                )

                value = alert.get(
                    f"Top_Feature_{number}_Value",
                    None,
                )

                shap_value = alert.get(
                    f"Top_Feature_{number}_SHAP",
                    None,
                )

                if pd.notna(feature) and str(feature).strip():

                    shap_found = True

                    st.write(
                        f"**{number}. {feature}**"
                    )

                    if pd.notna(value):
                        st.caption(
                            f"Feature value: {value}"
                        )

                    if pd.notna(shap_value):
                        st.caption(
                            f"SHAP contribution: {shap_value}"
                        )

            if not shap_found:

                st.info(
                    "No SHAP feature evidence is available."
                )

        # ---------------------------------------------------------------------
        # XAI EXPLANATION
        # ---------------------------------------------------------------------

        st.markdown("### 🧠 XAI Explanation")

        explanation = alert.get(
            "XAI_Explanation",
            "",
        )

        if pd.notna(explanation) and str(explanation).strip():

            st.info(str(explanation))

        else:

            st.info(
                "No XAI explanation is available for this alert."
            )

        # ---------------------------------------------------------------------
        # RECOMMENDATION
        # ---------------------------------------------------------------------

        st.markdown("### 👨‍💻 Analyst Recommendation")

        recommendation = alert.get(
            "Analyst_Recommendation",
            "",
        )

        if (
            pd.notna(recommendation)
            and str(recommendation).strip()
        ):

            st.warning(str(recommendation))

        else:

            st.warning(
                "No analyst recommendation is available."
            )

        # ---------------------------------------------------------------------
        # ANALYST WORKFLOW
        # ---------------------------------------------------------------------

        st.markdown("### 👤 Analyst Workflow")

        current_status = str(
            alert.get("Status", "")
        ).upper()

        analyst_name = st.text_input(
            "Analyst name",
            value="SOC_ANALYST",
            key=f"analyst_{selected_alert_id}",
        )

        notes = st.text_area(
            "Investigation notes",
            key=f"notes_{selected_alert_id}",
            placeholder=(
                "Enter analyst observations, evidence, "
                "correlation results, or resolution notes."
            ),
        )

        action_col1, action_col2 = st.columns(2)

        # ---------------------------------------------------------------------
        # NEW → INVESTIGATING
        # ---------------------------------------------------------------------

        with action_col1:

            if current_status == "NEW":

                if st.button(
                    "🔍 Start Investigation",
                    use_container_width=True,
                ):

                    success = store.update_status(
                        alert_id=str(selected_alert_id),
                        status="INVESTIGATING",
                        analyst=analyst_name,
                        notes=notes,
                    )

                    if success:

                        st.success(
                            "Alert moved to INVESTIGATING."
                        )

                        st.rerun()

                    else:

                        st.error(
                            "Unable to update alert status."
                        )

            elif current_status == "INVESTIGATING":

                st.info(
                    "Alert is currently under investigation."
                )

        # ---------------------------------------------------------------------
        # INVESTIGATING → RESOLVED
        # ---------------------------------------------------------------------

        with action_col2:

            if current_status == "INVESTIGATING":

                if st.button(
                    "✅ Resolve Alert",
                    use_container_width=True,
                ):

                    success = store.update_status(
                        alert_id=str(selected_alert_id),
                        status="RESOLVED",
                        analyst=analyst_name,
                        notes=notes,
                    )

                    if success:

                        st.success(
                            "Alert resolved and removed from active queue."
                        )

                        st.rerun()

                    else:

                        st.error(
                            "Unable to resolve alert."
                        )


# =============================================================================
# ANALYST ACTION HISTORY
# =============================================================================

if not active_df.empty and "selected_alert_id" in locals():

    st.divider()

    st.subheader("📜 Analyst Action History")

    try:

        action_history = store.get_action_history(
            str(selected_alert_id)
        )

        if action_history is not None and not action_history.empty:

            st.dataframe(
                action_history,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No analyst actions recorded for this alert."
            )

    except Exception as exc:

        st.warning(
            f"Unable to load analyst action history: {exc}"
        )


# =============================================================================
# ALERT HISTORY
# =============================================================================

st.divider()

st.subheader("📚 SOC Alert History")

st.caption(
    "Historical records include resolved alerts and other previously stored alerts."
)

if history_df.empty:

    st.info(
        "No historical alerts are currently stored."
    )

else:

    history_display_columns = [
        "Alert_ID",
        "Timestamp",
        "Predicted_Class",
        "Confidence",
        "Detection",
        "Severity",
        "SOC_Priority",
        "Status",
        "Source",
    ]

    history_display_columns = [
        column
        for column in history_display_columns
        if column in history_df.columns
    ]

    history_display = history_df[
        history_display_columns
    ].copy()

    if "Confidence" in history_display.columns:

        history_display["Confidence"] = (
            history_display["Confidence"] * 100
        ).round(2)

    st.dataframe(
        history_display,
        use_container_width=True,
        hide_index=True,
    )


# =============================================================================
# STATUS DISTRIBUTION
# =============================================================================

st.divider()

st.subheader("📊 Alert Status Distribution")

if history_df.empty:

    st.info(
        "No alert status data available."
    )

else:

    status_counts = (
        history_df["Status"]
        .astype(str)
        .str.upper()
        .value_counts()
    )

    st.bar_chart(status_counts)


# =============================================================================
# SEVERITY DISTRIBUTION
# =============================================================================

st.subheader("📊 Severity Distribution")

if history_df.empty:

    st.info(
        "No severity data available."
    )

else:

    severity_counts = (
        history_df["Severity"]
        .astype(str)
        .str.upper()
        .value_counts()
    )

    st.bar_chart(severity_counts)


# =============================================================================
# PRIORITY DISTRIBUTION
# =============================================================================

st.subheader("📊 SOC Priority Distribution")

if history_df.empty:

    st.info(
        "No priority data available."
    )

else:

    priority_counts = (
        history_df["SOC_Priority"]
        .astype(str)
        .str.upper()
        .value_counts()
    )

    st.bar_chart(priority_counts)


# =============================================================================
# SYSTEM CAPABILITIES
# =============================================================================

st.divider()

st.subheader("⚙️ ZUKA Capabilities")

capabilities = [
    ("Automatic network-flow ingestion", True),
    ("78-feature model schema", True),
    ("Multiclass XGBoost detection", True),
    ("Prediction confidence", True),
    ("SHAP explainability", True),
    ("SOC alert generation", True),
    ("Persistent SQLite alert storage", True),
    ("Active alert queue", True),
    ("Analyst investigation workflow", True),
    ("Alert resolution workflow", True),
    ("Historical alert retention", True),
    ("Analyst action history", True),
    ("Human approval requirement", True),
    ("Automated containment", False),
]

cap_col1, cap_col2 = st.columns(2)

half = (len(capabilities) + 1) // 2

for index, (name, enabled) in enumerate(capabilities):

    target = (
        cap_col1
        if index < half
        else cap_col2
    )

    with target:

        if enabled:
            st.write(f"✅ {name}")
        else:
            st.write(f"⛔ {name}")


# =============================================================================
# FOOTER
# =============================================================================

st.divider()

st.caption(
    "ZUKA — AI Cybersecurity SOC Assistant"
)

st.caption(
    "XGBoost + SHAP + SOC Alert Intelligence + Persistent Analyst Workflow"
)

st.caption(
    "Human analyst approval is required before escalation or containment. "
    "Automated containment is disabled."
)

log(
    f"Dashboard rendered | "
    f"total={total_alerts} | "
    f"new={new_count} | "
    f"investigating={investigating_count} | "
    f"resolved={resolved_count}"
)