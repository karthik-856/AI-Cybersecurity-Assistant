"""
================================================================================
ZUKA — SOC ALERT STORE
================================================================================

Persistent SQLite storage for the ZUKA SOC application.

Purpose
-------
The previous dashboard used CSV files containing a fixed set of test events.

That approach is useful for model testing, but a real SOC application needs
persistent alert state.

This module provides:

    NEW
      ↓
    INVESTIGATING
      ↓
    ├── RESOLVED
    └── ESCALATED

The database stores alerts independently from the dashboard.

Architecture:

    Detection
        ↓
    SHAP
        ↓
    Alert Engine
        ↓
    Recommendation Engine
        ↓
    AlertStore
        ↓
    ZUKA Dashboard
        ↓
    SOC Analyst
        ↓
    Analyst Action
        ↓
    AlertStore

Database:
    SQLite

Default location:
    <project_root>/data/zuka_soc.db

================================================================================
"""

from __future__ import annotations

import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Iterable

import pandas as pd


# =============================================================================
# LOGGER
# =============================================================================

logger = logging.getLogger("zuka.storage")

if not logger.handlers:

    handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    handler.setFormatter(formatter)

    logger.addHandler(handler)

    logger.setLevel(logging.INFO)


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"

DEFAULT_DATABASE_PATH = DATA_DIR / "zuka_soc.db"


# =============================================================================
# ALERT STATUS
# =============================================================================

STATUS_NEW = "NEW"

STATUS_INVESTIGATING = "INVESTIGATING"

STATUS_RESOLVED = "RESOLVED"

STATUS_ESCALATED = "ESCALATED"

STATUS_CLOSED = "CLOSED"


VALID_STATUSES = {
    STATUS_NEW,
    STATUS_INVESTIGATING,
    STATUS_RESOLVED,
    STATUS_ESCALATED,
    STATUS_CLOSED,
}


# =============================================================================
# DATABASE SCHEMA
# =============================================================================

CREATE_ALERTS_TABLE = """
CREATE TABLE IF NOT EXISTS alerts (

    alert_id TEXT PRIMARY KEY,

    event_id TEXT,

    timestamp TEXT,

    source TEXT,

    predicted_class INTEGER,

    detection TEXT,

    confidence REAL,

    confidence_level TEXT,

    severity TEXT,

    soc_priority TEXT,

    soc_response_category TEXT,

    top_feature_1 TEXT,

    top_feature_1_value REAL,

    top_feature_1_shap REAL,

    top_feature_2 TEXT,

    top_feature_2_value REAL,

    top_feature_2_shap REAL,

    top_feature_3 TEXT,

    top_feature_3_value REAL,

    top_feature_3_shap REAL,

    top_feature_4 TEXT,

    top_feature_5 TEXT,

    xai_explanation TEXT,

    analyst_recommendation TEXT,

    status TEXT NOT NULL DEFAULT 'NEW',

    analyst TEXT,

    analyst_notes TEXT,

    created_at TEXT NOT NULL,

    updated_at TEXT NOT NULL,

    resolved_at TEXT,

    escalated_at TEXT

)
"""


CREATE_ACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS analyst_actions (

    action_id INTEGER PRIMARY KEY AUTOINCREMENT,

    alert_id TEXT NOT NULL,

    action TEXT NOT NULL,

    analyst TEXT,

    notes TEXT,

    timestamp TEXT NOT NULL,

    FOREIGN KEY(alert_id)
        REFERENCES alerts(alert_id)

)
"""


CREATE_ALERT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_alert_status
ON alerts(status)
"""


CREATE_PRIORITY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_alert_priority
ON alerts(soc_priority)
"""


CREATE_TIMESTAMP_INDEX = """
CREATE INDEX IF NOT EXISTS idx_alert_timestamp
ON alerts(created_at)
"""


# =============================================================================
# ALERT STORE
# =============================================================================

class AlertStore:
    """
    Persistent storage manager for ZUKA SOC alerts.
    """

    def __init__(
        self,
        database_path: str | Path = DEFAULT_DATABASE_PATH,
    ) -> None:

        self.database_path = Path(database_path)

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize_database()

        logger.info(
            "ZUKA AlertStore initialized | database=%s",
            self.database_path,
        )


    # =========================================================================
    # DATABASE CONNECTION
    # =========================================================================

    def _connect(self) -> sqlite3.Connection:

        connection = sqlite3.connect(
            self.database_path,
            timeout=30,
        )

        connection.row_factory = sqlite3.Row

        return connection


    # =========================================================================
    # DATABASE INITIALIZATION
    # =========================================================================

    def _initialize_database(self) -> None:

        with self._connect() as connection:

            connection.execute(
                CREATE_ALERTS_TABLE
            )

            connection.execute(
                CREATE_ACTIONS_TABLE
            )

            connection.execute(
                CREATE_ALERT_INDEX
            )

            connection.execute(
                CREATE_PRIORITY_INDEX
            )

            connection.execute(
                CREATE_TIMESTAMP_INDEX
            )

            connection.commit()


    # =========================================================================
    # TIME
    # =========================================================================

    @staticmethod
    def _now() -> str:

        return datetime.now(
            timezone.utc
        ).isoformat()


    # =========================================================================
    # VALUE NORMALIZATION
    # =========================================================================

    @staticmethod
    def _clean_value(value: Any) -> Any:

        if value is None:
            return None

        try:

            if pd.isna(value):
                return None

        except (TypeError, ValueError):

            pass

        if hasattr(value, "item"):

            try:
                return value.item()

            except Exception:
                pass

        return value


    # =========================================================================
    # INSERT ONE ALERT
    # =========================================================================

    def add_alert(
        self,
        alert: dict[str, Any],
    ) -> bool:
        """
        Add one SOC alert.

        Returns:
            True if inserted.
            False if the alert already exists.
        """

        alert_id = str(
            alert.get("Alert_ID")
            or alert.get("alert_id")
            or ""
        ).strip()

        if not alert_id:

            raise ValueError(
                "Alert must contain Alert_ID"
            )


        now = self._now()


        values = {

            "alert_id": alert_id,

            "event_id": self._clean_value(
                alert.get("Event_ID")
                or alert.get("event_id")
            ),

            "timestamp": self._clean_value(
                alert.get("Timestamp")
                or alert.get("timestamp")
            ),

            "source": self._clean_value(
                alert.get("Source")
                or alert.get("source")
            ),

            "predicted_class": self._clean_value(
                alert.get("Predicted_Class")
            ),

            "detection": self._clean_value(
                alert.get("Detection")
            ),

            "confidence": self._clean_value(
                alert.get("Confidence")
            ),

            "confidence_level": self._clean_value(
                alert.get("Confidence_Level")
            ),

            "severity": self._clean_value(
                alert.get("Severity")
            ),

            "soc_priority": self._clean_value(
                alert.get("SOC_Priority")
            ),

            "soc_response_category": self._clean_value(
                alert.get("SOC_Response_Category")
            ),

            "top_feature_1": self._clean_value(
                alert.get("Top_Feature_1")
            ),

            "top_feature_1_value": self._clean_value(
                alert.get("Top_Feature_1_Value")
            ),

            "top_feature_1_shap": self._clean_value(
                alert.get("Top_Feature_1_SHAP")
            ),

            "top_feature_2": self._clean_value(
                alert.get("Top_Feature_2")
            ),

            "top_feature_2_value": self._clean_value(
                alert.get("Top_Feature_2_Value")
            ),

            "top_feature_2_shap": self._clean_value(
                alert.get("Top_Feature_2_SHAP")
            ),

            "top_feature_3": self._clean_value(
                alert.get("Top_Feature_3")
            ),

            "top_feature_3_value": self._clean_value(
                alert.get("Top_Feature_3_Value")
            ),

            "top_feature_3_shap": self._clean_value(
                alert.get("Top_Feature_3_SHAP")
            ),

            "top_feature_4": self._clean_value(
                alert.get("Top_Feature_4")
            ),

            "top_feature_5": self._clean_value(
                alert.get("Top_Feature_5")
            ),

            "xai_explanation": self._clean_value(
                alert.get("XAI_Explanation")
            ),

            "analyst_recommendation": self._clean_value(
                alert.get("Analyst_Recommendation")
            ),

        }


        status = str(
            alert.get(
                "Status",
                STATUS_NEW,
            )
        ).upper()


        if status not in VALID_STATUSES:

            raise ValueError(
                f"Invalid alert status: {status}"
            )


        sql = """
        INSERT OR IGNORE INTO alerts (

            alert_id,
            event_id,
            timestamp,
            source,
            predicted_class,
            detection,
            confidence,
            confidence_level,
            severity,
            soc_priority,
            soc_response_category,
            top_feature_1,
            top_feature_1_value,
            top_feature_1_shap,
            top_feature_2,
            top_feature_2_value,
            top_feature_2_shap,
            top_feature_3,
            top_feature_3_value,
            top_feature_3_shap,
            top_feature_4,
            top_feature_5,
            xai_explanation,
            analyst_recommendation,
            status,
            created_at,
            updated_at

        )

        VALUES (

            :alert_id,
            :event_id,
            :timestamp,
            :source,
            :predicted_class,
            :detection,
            :confidence,
            :confidence_level,
            :severity,
            :soc_priority,
            :soc_response_category,
            :top_feature_1,
            :top_feature_1_value,
            :top_feature_1_shap,
            :top_feature_2,
            :top_feature_2_value,
            :top_feature_2_shap,
            :top_feature_3,
            :top_feature_3_value,
            :top_feature_3_shap,
            :top_feature_4,
            :top_feature_5,
            :xai_explanation,
            :analyst_recommendation,
            :status,
            :created_at,
            :updated_at

        )
        """


        values["status"] = status

        values["created_at"] = now

        values["updated_at"] = now


        with self._connect() as connection:

            cursor = connection.execute(
                sql,
                values,
            )

            connection.commit()

            inserted = cursor.rowcount > 0


        if inserted:

            logger.info(
                "Alert stored | alert_id=%s | status=%s",
                alert_id,
                status,
            )

        else:

            logger.info(
                "Alert already exists | alert_id=%s",
                alert_id,
            )


        return inserted


    # =========================================================================
    # INSERT MANY ALERTS
    # =========================================================================

    def add_alerts(
        self,
        alerts: Iterable[dict[str, Any]],
    ) -> int:
        """
        Store multiple alerts.

        Returns:
            Number of newly inserted alerts.
        """

        count = 0

        for alert in alerts:

            if self.add_alert(alert):

                count += 1

        logger.info(
            "Alert batch stored | inserted=%d",
            count,
        )

        return count


    # =========================================================================
    # GET ONE ALERT
    # =========================================================================

    def get_alert(
        self,
        alert_id: str,
    ) -> dict[str, Any] | None:

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT *
                FROM alerts
                WHERE alert_id = ?
                """,
                (alert_id,),
            ).fetchone()


        if row is None:

            return None


        return dict(row)


    # =========================================================================
    # GET ALERTS
    # =========================================================================

    def get_alerts(
        self,
        status: str | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """
        Retrieve alerts.

        Examples:

            store.get_alerts()

            store.get_alerts(
                status="NEW"
            )
        """

        query = """
        SELECT *
        FROM alerts
        """

        parameters: list[Any] = []


        if status is not None:

            normalized_status = str(
                status
            ).upper()


            if normalized_status not in VALID_STATUSES:

                raise ValueError(
                    f"Invalid status: {normalized_status}"
                )


            query += """
            WHERE status = ?
            """

            parameters.append(
                normalized_status
            )


        query += """
        ORDER BY created_at DESC
        """


        if limit is not None:

            if limit <= 0:

                raise ValueError(
                    "limit must be greater than zero"
                )


            query += """
            LIMIT ?
            """

            parameters.append(
                int(limit)
            )


        with self._connect() as connection:

            rows = connection.execute(
                query,
                parameters,
            ).fetchall()


        return pd.DataFrame(
            [dict(row) for row in rows]
        )


    # =========================================================================
    # GET ACTIVE ALERTS
    # =========================================================================

    def get_active_alerts(
        self,
    ) -> pd.DataFrame:

        query = """
        SELECT *
        FROM alerts
        WHERE status IN (?, ?)
        ORDER BY
            CASE
                WHEN soc_priority = 'P1' THEN 1
                WHEN soc_priority = 'P2' THEN 2
                WHEN soc_priority = 'P3' THEN 3
                ELSE 4
            END,
            created_at DESC
        """

        with self._connect() as connection:

            rows = connection.execute(
                query,
                (
                    STATUS_NEW,
                    STATUS_INVESTIGATING,
                ),
            ).fetchall()


        return pd.DataFrame(
            [dict(row) for row in rows]
        )


    # =========================================================================
    # UPDATE STATUS
    # =========================================================================

    def update_status(
        self,
        alert_id: str,
        status: str,
        analyst: str | None = None,
        notes: str | None = None,
    ) -> bool:
        """
        Update the lifecycle status of an alert.
        """

        normalized_status = str(
            status
        ).upper()


        if normalized_status not in VALID_STATUSES:

            raise ValueError(
                f"Invalid status: {normalized_status}"
            )


        existing = self.get_alert(
            alert_id
        )


        if existing is None:

            raise ValueError(
                f"Alert not found: {alert_id}"
            )


        now = self._now()


        resolved_at = (
            now
            if normalized_status == STATUS_RESOLVED
            else existing.get("resolved_at")
        )


        escalated_at = (
            now
            if normalized_status == STATUS_ESCALATED
            else existing.get("escalated_at")
        )


        with self._connect() as connection:

            connection.execute(
                """
                UPDATE alerts

                SET
                    status = ?,
                    analyst = COALESCE(?, analyst),
                    analyst_notes = COALESCE(?, analyst_notes),
                    updated_at = ?,
                    resolved_at = ?,
                    escalated_at = ?

                WHERE alert_id = ?
                """,

                (
                    normalized_status,
                    analyst,
                    notes,
                    now,
                    resolved_at,
                    escalated_at,
                    alert_id,
                ),
            )


            connection.execute(
                """
                INSERT INTO analyst_actions (

                    alert_id,
                    action,
                    analyst,
                    notes,
                    timestamp

                )

                VALUES (?, ?, ?, ?, ?)
                """,

                (
                    alert_id,
                    normalized_status,
                    analyst,
                    notes,
                    now,
                ),
            )


            connection.commit()


        logger.info(
            "Alert status updated | alert_id=%s | status=%s",
            alert_id,
            normalized_status,
        )


        return True


    # =========================================================================
    # ANALYST ACTION
    # =========================================================================

    def record_action(
        self,
        alert_id: str,
        action: str,
        analyst: str = "SOC_ANALYST",
        notes: str | None = None,
    ) -> None:

        if self.get_alert(alert_id) is None:

            raise ValueError(
                f"Alert not found: {alert_id}"
            )


        action = str(action).upper()

        now = self._now()


        with self._connect() as connection:

            connection.execute(
                """
                INSERT INTO analyst_actions (

                    alert_id,
                    action,
                    analyst,
                    notes,
                    timestamp

                )

                VALUES (?, ?, ?, ?, ?)
                """,

                (
                    alert_id,
                    action,
                    analyst,
                    notes,
                    now,
                ),
            )

            connection.commit()


    # =========================================================================
    # ALERT HISTORY
    # =========================================================================

    def get_action_history(
        self,
        alert_id: str,
    ) -> pd.DataFrame:

        with self._connect() as connection:

            rows = connection.execute(
                """
                SELECT
                    action_id,
                    alert_id,
                    action,
                    analyst,
                    notes,
                    timestamp

                FROM analyst_actions

                WHERE alert_id = ?

                ORDER BY timestamp DESC
                """,
                (alert_id,),
            ).fetchall()


        return pd.DataFrame(
            [dict(row) for row in rows]
        )


    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_statistics(
        self,
    ) -> dict[str, int]:

        with self._connect() as connection:

            total = connection.execute(
                """
                SELECT COUNT(*)
                FROM alerts
                """
            ).fetchone()[0]


            new = connection.execute(
                """
                SELECT COUNT(*)
                FROM alerts
                WHERE status = ?
                """,
                (STATUS_NEW,),
            ).fetchone()[0]


            investigating = connection.execute(
                """
                SELECT COUNT(*)
                FROM alerts
                WHERE status = ?
                """,
                (STATUS_INVESTIGATING,),
            ).fetchone()[0]


            resolved = connection.execute(
                """
                SELECT COUNT(*)
                FROM alerts
                WHERE status = ?
                """,
                (STATUS_RESOLVED,),
            ).fetchone()[0]


            escalated = connection.execute(
                """
                SELECT COUNT(*)
                FROM alerts
                WHERE status = ?
                """,
                (STATUS_ESCALATED,),
            ).fetchone()[0]


            p1 = connection.execute(
                """
                SELECT COUNT(*)
                FROM alerts
                WHERE soc_priority = 'P1'
                AND status NOT IN (?, ?)
                """,
                (
                    STATUS_RESOLVED,
                    STATUS_CLOSED,
                ),
            ).fetchone()[0]


        return {

            "total": int(total),

            "new": int(new),

            "investigating": int(
                investigating
            ),

            "resolved": int(
                resolved
            ),

            "escalated": int(
                escalated
            ),

            "active_p1": int(p1),

        }


# =============================================================================
# SELF TEST
# =============================================================================

def _run_self_test() -> None:

    print(
        "\n"
        + "=" * 80
    )

    print(
        "ZUKA — SOC ALERT STORE SELF TEST"
    )

    print(
        "=" * 80
    )


    # -------------------------------------------------------------------------
    # Temporary test database
    # -------------------------------------------------------------------------

    test_database = (
        DATA_DIR / "zuka_soc_self_test.db"
    )


    if test_database.exists():

        test_database.unlink()


    store = AlertStore(
        database_path=test_database
    )


    print(
        "\nDATABASE"
    )

    print(
        "-" * 80
    )

    print(
        f"Path: {test_database}"
    )

    print(
        "✓ Database initialized"
    )


    # -------------------------------------------------------------------------
    # Test alerts
    # -------------------------------------------------------------------------

    alerts = [

        {

            "Alert_ID":
                "ZUKA-TEST-0001",

            "Event_ID":
                "EVENT-0001",

            "Timestamp":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "Source":
                "SELF_TEST",

            "Predicted_Class":
                9,

            "Detection":
                "ATTACK",

            "Confidence":
                0.9998,

            "Confidence_Level":
                "HIGH_CONFIDENCE",

            "Severity":
                "HIGH",

            "SOC_Priority":
                "P1",

            "SOC_Response_Category":
                "INVESTIGATE_AND_CORRELATE",

            "Top_Feature_1":
                "Destination Port",

            "Top_Feature_1_Value":
                80.0,

            "Top_Feature_1_SHAP":
                1.23,

            "Top_Feature_2":
                "Flow Duration",

            "Top_Feature_2_Value":
                1000.0,

            "Top_Feature_2_SHAP":
                0.87,

            "Top_Feature_3":
                "Packet Length Mean",

            "Top_Feature_3_Value":
                500.0,

            "Top_Feature_3_SHAP":
                0.42,

            "XAI_Explanation":
                "Test SHAP explanation.",

            "Analyst_Recommendation":
                "Investigate and correlate.",

        },

        {

            "Alert_ID":
                "ZUKA-TEST-0002",

            "Event_ID":
                "EVENT-0002",

            "Timestamp":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "Source":
                "SELF_TEST",

            "Predicted_Class":
                13,

            "Detection":
                "ATTACK",

            "Confidence":
                0.50,

            "Confidence_Level":
                "LOW_CONFIDENCE",

            "Severity":
                "LOW",

            "SOC_Priority":
                "P3",

            "SOC_Response_Category":
                "VALIDATE_BEFORE_ESCALATION",

            "Top_Feature_1":
                "Flow Bytes/s",

            "Top_Feature_2":
                "Packet Length Mean",

            "Top_Feature_3":
                "Flow Duration",

            "XAI_Explanation":
                "Low-confidence test alert.",

            "Analyst_Recommendation":
                "Validate before escalation.",

        },

    ]


    # -------------------------------------------------------------------------
    # Insert
    # -------------------------------------------------------------------------

    print(
        "\nINSERTING ALERTS"
    )

    print(
        "-" * 80
    )


    inserted = store.add_alerts(
        alerts
    )


    print(
        f"Inserted alerts: {inserted}"
    )


    assert inserted == 2

    print(
        "✓ Alert insertion verified"
    )


    # -------------------------------------------------------------------------
    # Retrieve
    # -------------------------------------------------------------------------

    print(
        "\nRETRIEVING ALERTS"
    )

    print(
        "-" * 80
    )


    all_alerts = store.get_alerts()


    print(
        all_alerts[
            [
                "alert_id",
                "predicted_class",
                "confidence",
                "severity",
                "soc_priority",
                "status",
            ]
        ].to_string(
            index=False
        )
    )


    assert len(all_alerts) == 2

    print(
        "✓ Alert retrieval verified"
    )


    # -------------------------------------------------------------------------
    # Active queue
    # -------------------------------------------------------------------------

    print(
        "\nACTIVE ALERT QUEUE"
    )

    print(
        "-" * 80
    )


    active = store.get_active_alerts()


    print(
        f"Active alerts: {len(active)}"
    )


    assert len(active) == 2

    print(
        "✓ Active alert queue verified"
    )


    # -------------------------------------------------------------------------
    # Investigate
    # -------------------------------------------------------------------------

    print(
        "\nSTARTING INVESTIGATION"
    )

    print(
        "-" * 80
    )


    store.update_status(
        "ZUKA-TEST-0001",
        STATUS_INVESTIGATING,
        analyst="SOC_ANALYST",
        notes="Investigation started.",
    )


    alert = store.get_alert(
        "ZUKA-TEST-0001"
    )


    assert (
        alert["status"]
        == STATUS_INVESTIGATING
    )


    print(
        "✓ INVESTIGATING status verified"
    )


    # -------------------------------------------------------------------------
    # Resolve
    # -------------------------------------------------------------------------

    print(
        "\nRESOLVING ALERT"
    )

    print(
        "-" * 80
    )


    store.update_status(
        "ZUKA-TEST-0001",
        STATUS_RESOLVED,
        analyst="SOC_ANALYST",
        notes="Alert reviewed and resolved.",
    )


    alert = store.get_alert(
        "ZUKA-TEST-0001"
    )


    assert (
        alert["status"]
        == STATUS_RESOLVED
    )


    assert (
        alert["resolved_at"]
        is not None
    )


    print(
        "✓ RESOLVED status verified"
    )


    # -------------------------------------------------------------------------
    # Escalate
    # -------------------------------------------------------------------------

    print(
        "\nESCALATING ALERT"
    )

    print(
        "-" * 80
    )


    store.update_status(
        "ZUKA-TEST-0002",
        STATUS_ESCALATED,
        analyst="SOC_ANALYST",
        notes="Escalation required.",
    )


    alert = store.get_alert(
        "ZUKA-TEST-0002"
    )


    assert (
        alert["status"]
        == STATUS_ESCALATED
    )


    print(
        "✓ ESCALATED status verified"
    )


    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    print(
        "\nSOC STATISTICS"
    )

    print(
        "-" * 80
    )


    stats = store.get_statistics()


    for key, value in stats.items():

        print(
            f"{key:20}: {value}"
        )


    assert stats["total"] == 2

    assert stats["resolved"] == 1

    assert stats["escalated"] == 1


    # -------------------------------------------------------------------------
    # History
    # -------------------------------------------------------------------------

    print(
        "\nANALYST ACTION HISTORY"
    )

    print(
        "-" * 80
    )


    history = store.get_action_history(
        "ZUKA-TEST-0001"
    )


    print(
        history.to_string(
            index=False
        )
    )


    assert len(history) >= 2


    print(
        "\n✓ Analyst history verified"
    )


    # -------------------------------------------------------------------------
    # Final
    # -------------------------------------------------------------------------

    print(
        "\n"
        + "=" * 80
    )

    print(
        "✓ ZUKA AlertStore self-test completed"
    )

    print(
        "=" * 80
    )


    # Remove test database.

    try:

        test_database.unlink()

    except OSError:

        pass


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":

    _run_self_test()