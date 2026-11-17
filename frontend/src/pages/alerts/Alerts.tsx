import { scheduleLoad } from "../../utils/scheduleLoad";
import { formatShortDateTime } from "../../utils/datetime";
import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Copy,
  Database,
  ExternalLink,
  Eye,
  Info,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  X,
  Zap,
} from "lucide-react";

import {
  getAlerts,
  getAlert,
  generateAlertExplanation,
  getAlertStats,
  updateAlertStatus,
} from "../../services/api";

import type { Alert, AlertStatus, AlertStats } from "../../services/api";

import "./Alerts.css";

/* =========================================================
   TYPES
   ========================================================= */

type AlertRecord = Alert;

type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";

interface ShapFeature {
  feature: string;
  direction: string;
  shap_value: number;
  feature_value: number;
}

/* =========================================================
   HELPERS
   ========================================================= */

function formatPercent(value: number): string {
  if (!Number.isFinite(value)) {
    return "—";
  }

  return `${(value * 100).toFixed(2)}%`;
}

function formatFeatureValue(value: number): string {
  if (!Number.isFinite(value)) {
    return "—";
  }

  if (Math.abs(value) >= 100000) {
    return value.toExponential(3);
  }

  return value.toFixed(6).replace(/\.?0+$/, "");
}

function severityClass(severity: Severity): string {
  return `alert-severity alert-severity-${severity.toLowerCase()}`;
}

function statusClass(status: AlertStatus): string {
  return `alert-status alert-status-${status.toLowerCase()}`;
}

function statusLabel(status: AlertStatus): string {
  switch (status) {
    case "OPEN":
      return "Open";

    case "ACKNOWLEDGED":
      return "Acknowledged";

    case "INVESTIGATING":
      return "Investigating";

    case "RESOLVED":
      return "Resolved";

    default:
      return status;
  }
}

function severityIcon(severity: Severity) {
  switch (severity) {
    case "CRITICAL":
      return <ShieldAlert size={13} />;

    case "HIGH":
      return <AlertTriangle size={13} />;

    case "MEDIUM":
      return <Info size={13} />;

    default:
      return <Info size={13} />;
  }
}

/* =========================================================
   INVESTIGATION DRAWER
   ========================================================= */

function AlertDetails({
  alert,
  onClose,
  onStatusChange,
  updating,
  onExplain,
}: {
  alert: AlertRecord;
  onClose: () => void;
  onStatusChange: (alertId: string, nextStatus: AlertStatus) => Promise<void>;
  updating: boolean;
  onExplain: (alertId: string) => Promise<void>;
}) {
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [explanationError, setExplanationError] = useState("");
  const [canGenerateExplanation] = useState(() => {
    try {
      return ["ADMIN", "SOC_ANALYST"].includes(
        JSON.parse(localStorage.getItem("zuka_user") || "{}").role,
      );
    } catch {
      return false;
    }
  });

  async function explain() {
    setExplaining(true);
    setExplanationError("");
    try {
      await onExplain(alert.alert_id);
    } catch (error) {
      setExplanationError(
        error instanceof Error
          ? error.message
          : "Unable to generate explanation.",
      );
    } finally {
      setExplaining(false);
    }
  }

  const features: ShapFeature[] = (alert.xai_explanation?.top_contributions ||
    alert.xai_explanation?.supporting_features ||
    []) as ShapFeature[];

  const supportingFeatures: ShapFeature[] = (alert.xai_explanation
    ?.supporting_features || []) as ShapFeature[];

  const opposingFeatures: ShapFeature[] = (alert.xai_explanation
    ?.opposing_features || []) as ShapFeature[];

  return (
    <>
      <div className="alert-drawer-backdrop" onClick={onClose} />

      <aside className="alert-drawer" aria-label="Alert investigation">
        {/* DRAWER HEADER */}

        <div className="alert-drawer-header">
          <div className="alert-drawer-title">
            <span className="alert-drawer-title-kicker">
              ALERT INVESTIGATION
            </span>

            <h2>{alert.alert_id}</h2>

            <p>
              {alert.predicted_class} • {formatPercent(alert.confidence)}
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button
              type="button"
              style={{
                background:
                  "linear-gradient(135deg, rgba(37, 99, 235, 0.25), rgba(59, 130, 246, 0.15))",
                border: "1px solid #3b82f6",
                color: "#60a5fa",
                padding: "6px 12px",
                fontSize: 12,
                fontWeight: 600,
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                borderRadius: 8,
                cursor: "pointer",
              }}
              onClick={() => {
                window.dispatchEvent(
                  new CustomEvent("zuka:open", {
                    detail: {
                      alert_id: alert.alert_id,
                      incident_id: alert.incident_id || undefined,
                      prompt: `summarize alert ${alert.alert_id}`,
                    },
                  }),
                );
              }}
              title="Open Zuka Assistant with this alert"
            >
              <Bot size={14} />
              <span>Ask Zuka</span>
            </button>

            <button
              type="button"
              className="alert-drawer-close"
              onClick={onClose}
              aria-label="Close investigation"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        <div className="alert-drawer-body">
          {/* SUMMARY */}

          <div className="alert-drawer-summary">
            <div className="alert-detail-card">
              <div className="alert-detail-label">Detection</div>

              <div className="alert-detail-value strong">
                {alert.predicted_class}
              </div>
            </div>

            <div className="alert-detail-card">
              <div className="alert-detail-label">Confidence</div>

              <div className="alert-detail-value">
                {formatPercent(alert.confidence)}
              </div>
            </div>

            <div className="alert-detail-card">
              <div className="alert-detail-label">Severity</div>

              <div>
                <span className={severityClass(alert.severity as Severity)}>
                  {severityIcon(alert.severity as Severity)}

                  {alert.severity}
                </span>
              </div>
            </div>

            <div className="alert-detail-card">
              <div className="alert-detail-label">Status</div>

              <div>
                <span className={statusClass(alert.status)}>
                  {statusLabel(alert.status)}
                </span>
              </div>
            </div>
          </div>

          {/* NETWORK EVIDENCE */}

          <section className="alert-drawer-section">
            <div className="alert-drawer-section-header">
              <h3>Network Evidence</h3>

              <span>Threat Detection</span>
            </div>

            <div className="alert-drawer-summary">
              <div className="alert-detail-card">
                <div className="alert-detail-label">Source</div>

                <div className="alert-detail-value">
                  {alert.source_ip ?? "Not available"}

                  {alert.source_port !== null && alert.source_port !== undefined
                    ? `:${alert.source_port}`
                    : ""}
                </div>
              </div>

              <div className="alert-detail-card">
                <div className="alert-detail-label">Destination</div>

                <div className="alert-detail-value">
                  {alert.destination_ip ?? "Not available"}

                  {alert.destination_port !== null &&
                  alert.destination_port !== undefined
                    ? `:${alert.destination_port}`
                    : ""}
                </div>
              </div>

              <div className="alert-detail-card">
                <div className="alert-detail-label">Protocol</div>

                <div className="alert-detail-value">
                  {alert.protocol ?? "Not available"}
                </div>
              </div>

              <div className="alert-detail-card">
                <div className="alert-detail-label">Dataset</div>

                <div className="alert-detail-value">Unknown</div>
              </div>

              <div className="alert-detail-card">
                <div className="alert-detail-label">Source Type</div>

                <div className="alert-detail-value">
                  {alert.capture_source ?? "Live Sensor"}
                </div>
              </div>

              <div className="alert-detail-card">
                <div className="alert-detail-label">Detected</div>

                <div className="alert-detail-value">
                  {formatShortDateTime(alert.detected_at)}
                </div>
              </div>
            </div>
          </section>

          {/* CORRELATED INCIDENT & INVESTIGATION */}
          <section className="alert-drawer-section">
            <div className="alert-drawer-section-header">
              <div>
                <h3>SOC Correlation & Department</h3>
                <span>Correlated incident and investigation case</span>
              </div>
            </div>

            <div className="alert-drawer-summary">
              <div className="alert-detail-card">
                <div className="alert-detail-label">Correlated Incident</div>
                <div
                  className="alert-detail-value strong"
                  style={{
                    fontFamily: "monospace",
                    color: alert.incident_id ? "#34d399" : "#8da4b5",
                  }}
                >
                  {alert.incident_id || "No Incident Linked"}
                </div>
                {alert.incident_id && (
                  <button
                    type="button"
                    style={{
                      marginTop: 6,
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 4,
                      background: "transparent",
                      border: "none",
                      color: "#38bdf8",
                      cursor: "pointer",
                      fontSize: 11,
                      fontWeight: 700,
                    }}
                    onClick={() =>
                      navigate(
                        `/incidents?search=${encodeURIComponent(alert.incident_id || "")}`,
                      )
                    }
                  >
                    View Incident ↗
                  </button>
                )}
              </div>

              <div className="alert-detail-card">
                <div className="alert-detail-label">
                  Investigation Department
                </div>
                <div
                  className="alert-detail-value strong"
                  style={{
                    fontFamily: "monospace",
                    color: alert.investigation_id ? "#38bdf8" : "#8da4b5",
                  }}
                >
                  {alert.investigation_id
                    ? `Case ${alert.investigation_id}`
                    : alert.incident_id
                      ? `Case for ${alert.incident_id}`
                      : "Triage Phase"}
                </div>
                {(alert.investigation_id || alert.incident_id) && (
                  <button
                    type="button"
                    style={{
                      marginTop: 6,
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 4,
                      background: "transparent",
                      border: "none",
                      color: "#19d39d",
                      cursor: "pointer",
                      fontSize: 11,
                      fontWeight: 700,
                    }}
                    onClick={() =>
                      navigate(
                        `/investigation?search=${encodeURIComponent(alert.incident_id || alert.investigation_id || "")}`,
                      )
                    }
                  >
                    Open investigation ↗
                  </button>
                )}
              </div>

              {alert.source_ip && (
                <div className="alert-detail-card">
                  <div className="alert-detail-label">Network Flow Origin</div>
                  <div
                    className="alert-detail-value strong"
                    style={{ fontFamily: "monospace", color: "#38bdf8" }}
                  >
                    {alert.source_ip}
                    {alert.source_port ? `:${alert.source_port}` : ""}
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* DESCRIPTION */}

          {alert.description && (
            <section className="alert-drawer-section">
              <div className="alert-drawer-section-header">
                <h3>Detection Summary</h3>
              </div>

              <div className="alert-detail-card">
                <div className="alert-detail-value strong">
                  {alert.description}
                </div>
              </div>
            </section>
          )}

          {/* SHAP */}

          <section className="alert-drawer-section">
            <div className="alert-drawer-section-header">
              <div>
                <h3>Explainability — TreeSHAP</h3>

                <span>Model feature contribution evidence</span>
              </div>

              <span>{alert.xai_explanation?.method ?? "TreeSHAP"}</span>
            </div>

            {features.length === 0 ? (
              <div className="alerts-empty">
                <Info size={18} />

                <div className="alerts-empty-title">
                  Explanation not generated
                </div>

                <div className="alerts-empty-text">
                  Generate an explanation from saved model inputs or a matching
                  demonstration sample.
                </div>
                <button
                  type="button"
                  className="alert-action-button"
                  disabled={explaining || !canGenerateExplanation}
                  onClick={() => void explain()}
                >
                  {explaining
                    ? "Generating explanation..."
                    : "Generate explanation"}
                </button>
                {!canGenerateExplanation && (
                  <p>
                    Ask an administrator or analyst to generate this
                    explanation.
                  </p>
                )}
                {explanationError && <p role="alert">{explanationError}</p>}
              </div>
            ) : (
              <div className="alert-explanation-list">
                {features.map((feature, index) => {
                  const positive = feature.shap_value >= 0;

                  return (
                    <div
                      key={`${feature.feature}-${index}`}
                      className={`alert-explanation-row ${
                        positive
                          ? "alert-explanation-supporting"
                          : "alert-explanation-opposing"
                      }`}
                    >
                      <div>
                        <div className="alert-explanation-name">
                          {feature.feature}
                        </div>

                        <div
                          className="alert-explanation-name"
                          style={{
                            marginTop: "4px",
                            color: "#536a75",
                          }}
                        >
                          Value: {formatFeatureValue(feature.feature_value)}
                        </div>
                      </div>

                      <div className="alert-explanation-value">
                        {feature.shap_value >= 0 ? "+" : ""}

                        {feature.shap_value.toFixed(4)}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* SUPPORTING / OPPOSING */}
          {alert.xai_explanation?.input_source ===
            "reconstructed_demo_sample" && (
            <p className="alert-detail-value">
              Explanation reconstructed from a matching included sample and
              stored replay evidence.
            </p>
          )}

          {(supportingFeatures.length > 0 || opposingFeatures.length > 0) && (
            <section className="alert-drawer-section">
              <div className="alert-drawer-section-header">
                <h3>Evidence Direction</h3>
              </div>

              <div className="alert-detail-card">
                <div
                  className="alert-detail-label"
                  style={{
                    color: "#67a996",
                  }}
                >
                  Supporting Features
                </div>

                <div className="alert-detail-value">
                  {supportingFeatures.length}
                </div>
              </div>

              <div
                className="alert-detail-card"
                style={{
                  marginTop: "7px",
                }}
              >
                <div
                  className="alert-detail-label"
                  style={{
                    color: "#bb747d",
                  }}
                >
                  Opposing Features
                </div>

                <div className="alert-detail-value">
                  {opposingFeatures.length}
                </div>
              </div>
            </section>
          )}

          {/* WORKFLOW */}

          <section className="alert-drawer-section">
            <div className="alert-drawer-section-header">
              <h3>Analyst Workflow</h3>

              <span>Response actions</span>
            </div>

            <div className="alert-workflow">
              {alert.status !== "ACKNOWLEDGED" &&
                alert.status !== "INVESTIGATING" &&
                alert.status !== "RESOLVED" && (
                  <button
                    type="button"
                    className="alert-workflow-button"
                    style={{
                      background:
                        "linear-gradient(135deg, rgba(25, 211, 157, 0.22), rgba(16, 185, 129, 0.16))",
                      borderColor: "#19d39d",
                      color: "#2bd7a5",
                      fontWeight: 700,
                    }}
                    disabled={updating}
                    onClick={async () => {
                      await onStatusChange(alert.alert_id, "ACKNOWLEDGED");
                    }}
                  >
                    {updating ? "Acknowledging..." : "Acknowledge Alert"}
                    {!updating && <ShieldCheck size={14} />}
                  </button>
                )}

              {(alert.status === "ACKNOWLEDGED" ||
                alert.status === "INVESTIGATING") && (
                <div
                  className="alert-detail-card"
                  style={{
                    padding: "12px",
                    background: "rgba(16, 185, 129, 0.08)",
                    borderColor: "rgba(16, 185, 129, 0.3)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      color: "#34d399",
                      fontWeight: 700,
                      fontSize: "13px",
                    }}
                  >
                    <ShieldCheck size={16} />
                    <span>{statusLabel(alert.status)}</span>
                  </div>
                  <p
                    style={{
                      margin: "6px 0 10px",
                      fontSize: "12px",
                      color: "#94a3b8",
                      lineHeight: 1.4,
                    }}
                  >
                    Open the linked incident to review its current status.
                  </p>
                  <button
                    type="button"
                    className="alert-workflow-button"
                    style={{
                      background: "rgba(56, 189, 248, 0.15)",
                      borderColor: "#38bdf8",
                      color: "#38bdf8",
                      fontWeight: 700,
                      fontSize: "12px",
                    }}
                    onClick={() =>
                      navigate(
                        `/incidents?search=${encodeURIComponent(
                          alert.incident_id || alert.alert_id,
                        )}`,
                      )
                    }
                  >
                    View incident ↗
                    <ExternalLink size={14} />
                  </button>
                </div>
              )}

              {alert.status === "RESOLVED" && (
                <div
                  className="alert-detail-card"
                  style={{
                    textAlign: "center",
                    color: "#64748b",
                    padding: "10px",
                  }}
                >
                  Alert resolved and preserved in SOC audit history.
                </div>
              )}
            </div>
          </section>

          {/* RESOLVED MESSAGE */}

          {alert.status === "RESOLVED" && (
            <div
              className="alert-detail-card"
              style={{
                marginTop: "16px",
                borderColor: "rgba(64, 133, 111, 0.25)",
              }}
            >
              <div
                className="alert-detail-value"
                style={{
                  color: "#70aa99",
                }}
              >
                Alert resolved. The detection record, model result, and XAI
                evidence remain preserved in alert history.
              </div>
            </div>
          )}

          {/* COPY ALERT DATA */}
          <div style={{ marginTop: "14px" }}>
            <button
              type="button"
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                padding: "10px 14px",
                borderRadius: "8px",
                background: "rgba(12, 26, 39, 0.9)",
                border: "1px solid #1a364e",
                color: "#9db3c5",
                fontSize: "11px",
                fontWeight: 700,
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(
                    JSON.stringify(alert, null, 2),
                  );
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                } catch {
                  // ignore
                }
              }}
            >
              {copied ? (
                <CheckCircle2 size={14} color="#19d39d" />
              ) : (
                <Copy size={14} />
              )}
              {copied ? "Copied" : "Copy alert data"}
            </button>
          </div>

          {/* BOTTOM CLOSE DRAWER BUTTON */}
          <div style={{ marginTop: "10px", paddingBottom: "16px" }}>
            <button
              type="button"
              className="alert-drawer-bottom-close-btn"
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                padding: "11px 16px",
                borderRadius: "8px",
                background:
                  "linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95))",
                border: "1px solid #334155",
                color: "#e2e8f0",
                fontSize: "12px",
                fontWeight: 700,
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              onClick={onClose}
            >
              <X size={15} />
              <span>Close Alert Inspection</span>
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}

/* =========================================================
   ALERT CENTER
   ========================================================= */

function Alerts() {
  const [searchParams] = useSearchParams();

  const [alerts, setAlerts] = useState<AlertRecord[]>([]);

  const [total, setTotal] = useState(0);

  const [history, setHistory] = useState<AlertRecord[]>([]);

  const [historyTotal, setHistoryTotal] = useState(0);
  const [search, setSearch] = useState(() => searchParams.get("search") || "");
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 10;

  const [showHistory, setShowHistory] = useState<boolean>(() => {
    return (
      searchParams.get("history") === "true" ||
      searchParams.get("tab") === "history"
    );
  });

  const [selectedAlert, setSelectedAlert] = useState<AlertRecord | null>(null);

  const [loading, setLoading] = useState(true);

  const [historyLoading, setHistoryLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [stats, setStats] = useState<AlertStats | null>(null);

  const loadStats = useCallback(async () => {
    try {
      const data = await getAlertStats();
      setStats(data);
    } catch {
      // ignore
    }
  }, []);

  const [previousInputs0, setpreviousInputs0] = useState<
    readonly unknown[] | null
  >(null);
  const currentInputs1 = [searchParams];
  if (
    previousInputs0 === null ||
    currentInputs1.some(
      (value, index) => !Object.is(value, previousInputs0?.[index]),
    )
  ) {
    setpreviousInputs0(currentInputs1);

    const q = searchParams.get("search");
    if (q !== null && q !== undefined) {
      setSearch(q);
    }
    if (
      searchParams.get("history") === "true" ||
      searchParams.get("tab") === "history"
    ) {
      setShowHistory(true);
      setPage(1);
    }
  }

  const [previousInputs1, setpreviousInputs1] = useState<
    readonly unknown[] | null
  >(null);
  const currentInputs2 = [searchParams, alerts];
  if (
    previousInputs1 === null ||
    currentInputs2.some(
      (value, index) => !Object.is(value, previousInputs1?.[index]),
    )
  ) {
    setpreviousInputs1(currentInputs2);

    const aid = searchParams.get("alert_id");
    if (aid && alerts.length > 0) {
      const found = alerts.find((a) => a.alert_id === aid);
      if (found) setSelectedAlert(found);
    }
  }

  const [previousInputs2, setpreviousInputs2] = useState<
    readonly unknown[] | null
  >(null);
  const currentInputs3 = [alerts, search, selectedAlert];
  if (
    previousInputs2 === null ||
    currentInputs3.some(
      (value, index) => !Object.is(value, previousInputs2?.[index]),
    )
  ) {
    setpreviousInputs2(currentInputs3);

    if (search.trim() && alerts.length === 1 && !selectedAlert) {
      setSelectedAlert(alerts[0]);
    }
  }

  const [updating, setUpdating] = useState(false);

  /* =======================================================
     LOAD ACTIVE ALERTS
     ======================================================= */

  const loadActiveAlerts = useCallback(async () => {
    try {
      const data = await getAlerts({
        search: search.trim() || undefined,
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      });

      setAlerts(data.alerts);

      setTotal(data.total);

      void loadStats();

      setSelectedAlert((current) => {
        if (!current) {
          return current;
        }

        return (
          data.alerts.find((alert) => alert.alert_id === current.alert_id) ??
          current
        );
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load alerts.");
    } finally {
      setLoading(false);
    }
  }, [search, page, loadStats]);

  /* =======================================================
     LOAD HISTORY
     ======================================================= */

  const loadHistory = useCallback(async () => {
    try {
      const data = await getAlerts({
        status: "RESOLVED",
        search: search.trim() || undefined,
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      });

      setHistory(data.alerts);
      setHistoryTotal(data.total);

      void loadStats();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load alert history.",
      );
    } finally {
      setHistoryLoading(false);
    }
  }, [search, page, loadStats]);

  /* =======================================================
     INITIAL ACTIVE QUEUE POLLING
     ======================================================= */

  useEffect(() => {
    const cancelInitialLoad = scheduleLoad(loadActiveAlerts);

    const interval = window.setInterval(() => {
      void loadActiveAlerts();
    }, 5000);

    return () => {
      cancelInitialLoad();
      window.clearInterval(interval);
    };
  }, [loadActiveAlerts]);

  /* =======================================================
     HISTORY LOADING
     ======================================================= */

  useEffect(() => {
    if (showHistory) {
      return scheduleLoad(loadHistory);
    }
  }, [showHistory, loadHistory]);

  /* =======================================================
     STATUS UPDATE
     ======================================================= */

  const updateStatus = async (alertId: string, nextStatus: AlertStatus) => {
    try {
      setUpdating(true);

      setError(null);

      const updatedAlert = await updateAlertStatus(alertId, {
        status: nextStatus,
      });

      if (updatedAlert.status === "RESOLVED") {
        setAlerts((current) =>
          current.filter((alert) => alert.alert_id !== alertId),
        );

        setTotal((current) => Math.max(0, current - 1));

        setSelectedAlert(null);

        await loadHistory();
      } else {
        setAlerts((current) =>
          current.map((alert) =>
            alert.alert_id === alertId ? updatedAlert : alert,
          ),
        );

        setSelectedAlert(updatedAlert);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to update alert status.",
      );
    } finally {
      setUpdating(false);
    }
  };

  /* =======================================================
     OPEN ALERT DETAILS
     ======================================================= */

  const openAlertDetails = async (alertId: string) => {
    try {
      setError(null);

      const latestAlert = await getAlert(alertId);

      setSelectedAlert(latestAlert);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load alert details.",
      );
    }
  };

  /* =======================================================
     DERIVED METRICS
     ======================================================= */

  const displayedAlerts = showHistory ? history : alerts;

  const criticalCount = stats
    ? (stats.active_critical ?? stats.critical)
    : alerts.filter((alert) => alert.severity === "CRITICAL").length;

  const highCount = stats
    ? (stats.active_high ?? stats.high)
    : alerts.filter((alert) => alert.severity === "HIGH").length;

  const investigatingCount = stats
    ? stats.investigating
    : alerts.filter((alert) => alert.status === "INVESTIGATING").length;

  const resolvedCount = stats ? stats.resolved : historyTotal;

  const activeAlertsCount = stats
    ? stats.open + stats.acknowledged + stats.investigating
    : total;

  const paginationTotal = showHistory ? historyTotal : total;
  const totalPages = Math.ceil(paginationTotal / PAGE_SIZE);
  const firstVisiblePage = Math.max(1, Math.min(page - 2, totalPages - 4));
  const visiblePages = Array.from(
    { length: Math.min(5, totalPages) },
    (_, index) => firstVisiblePage + index,
  );

  /* =======================================================
     RENDER
     ======================================================= */

  return (
    <div className="alerts-page">
      {/* =================================================
          PAGE HEADER
      ================================================= */}

      <section className="alerts-header">
        <div className="alerts-header-copy">
          <div className="alerts-kicker">
            <Zap size={12} />
            SOC OPERATIONS / DETECTION
          </div>

          <h1>Alert Center</h1>

          <p>
            Review ZUKA model detections, investigate evidence, track analyst
            workflow, and preserve resolved alerts for audit history.
          </p>
        </div>

        <div className="alerts-header-meta">
          <div className="alerts-live-indicator">
            <span className="alerts-live-dot" />
            DATASET REPLAY
          </div>

          <button
            type="button"
            className="alert-investigate-button"
            onClick={
              showHistory
                ? () => void loadHistory()
                : () => void loadActiveAlerts()
            }
          >
            <RefreshCw size={12} />
            Refresh
          </button>
        </div>
      </section>

      {/* =================================================
          ERROR
      ================================================= */}

      {error && <div className="alerts-error">{error}</div>}

      {/* =================================================
          KPI GRID
      ================================================= */}

      <section className="alerts-kpi-grid">
        <div className="alerts-kpi-card">
          <div className="alerts-kpi-label">Active Alerts</div>

          <div className="alerts-kpi-value alerts-kpi-open">
            {search.trim() ? total : activeAlertsCount}
          </div>

          <div className="alerts-kpi-subtitle">
            {search.trim() ? "Matching search query" : "Current SOC queue"}
          </div>
        </div>

        <div className="alerts-kpi-card">
          <div className="alerts-kpi-label">Critical</div>

          <div className="alerts-kpi-value alerts-kpi-critical">
            {criticalCount}
          </div>

          <div className="alerts-kpi-subtitle">Immediate analyst attention</div>
        </div>

        <div className="alerts-kpi-card">
          <div className="alerts-kpi-label">High</div>

          <div className="alerts-kpi-value alerts-kpi-high">{highCount}</div>

          <div className="alerts-kpi-subtitle">Elevated security priority</div>
        </div>

        <div className="alerts-kpi-card">
          <div className="alerts-kpi-label">Investigating</div>

          <div className="alerts-kpi-value">{investigatingCount}</div>

          <div className="alerts-kpi-subtitle">
            Analyst investigation in progress
          </div>
        </div>

        <div className="alerts-kpi-card">
          <div className="alerts-kpi-label">Resolved History</div>

          <div className="alerts-kpi-value alerts-kpi-resolved">
            {resolvedCount}
          </div>

          <div className="alerts-kpi-subtitle">Preserved SOC records</div>
        </div>
      </section>

      {/* =================================================
          ALERT PANEL
      ================================================= */}

      <section className="alerts-panel">
        <div className="alerts-panel-header">
          <div className="alerts-panel-title">
            <span className="alerts-panel-kicker">SECURITY OPERATIONS</span>

            <h2>
              {showHistory ? "Resolved Alert History" : "Active Alert Queue"}
            </h2>

            <p>
              {showHistory
                ? "Historical detection records preserved after SOC resolution."
                : "Alerts requiring analyst review and workflow progression."}
            </p>
          </div>

          <div className="alerts-status-item">
            <Clock3 size={11} />

            {showHistory
              ? `${history.length} historical records`
              : `${total} active records`}
          </div>
        </div>

        {/* =================================================
            TABS
        ================================================= */}

        <div className="alerts-tabs">
          <button
            type="button"
            className={`alerts-tab ${!showHistory ? "active" : ""}`}
            onClick={() => {
              setShowHistory(false);
              setPage(1);
            }}
          >
            Active Queue
            <span className="alerts-tab-count">{total}</span>
          </button>

          <button
            type="button"
            className={`alerts-tab ${showHistory ? "active" : ""}`}
            onClick={() => {
              setShowHistory(true);
              setPage(1);
            }}
          >
            Alert History
            <span className="alerts-tab-count">{resolvedCount}</span>
          </button>
        </div>

        {/* =================================================
            TOOLBAR
        ================================================= */}

        <div className="alerts-toolbar">
          <div className="alerts-search-box">
            <Search size={14} />
            <input
              type="search"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
              placeholder="Search alerts, attack type, IP..."
              aria-label="Search alerts"
            />
            {search && (
              <button
                type="button"
                className="alerts-search-clear"
                onClick={() => {
                  setSearch("");
                  setPage(1);
                }}
                aria-label="Clear alert search"
              >
                <X size={13} />
              </button>
            )}
          </div>

          <div className="alerts-filter-group">
            <div className="alerts-status-item">
              <Search size={11} />

              {showHistory ? "Resolved detections" : "Unresolved detections"}
            </div>
          </div>

          <div className="alerts-result-count">
            {(showHistory ? historyTotal : total).toLocaleString()} records
          </div>
        </div>

        {/* =================================================
            TABLE / EMPTY STATE
        ================================================= */}

        {loading && !showHistory ? (
          <div className="alerts-loading">Loading active alerts...</div>
        ) : historyLoading && showHistory ? (
          <div className="alerts-loading">Loading alert history...</div>
        ) : displayedAlerts.length === 0 ? (
          <div className="alerts-empty">
            <CheckCircle2 size={23} />

            <div className="alerts-empty-title">
              {showHistory ? "No resolved alerts" : "No active alerts"}
            </div>

            <div className="alerts-empty-text">
              {showHistory
                ? "Resolved ZUKA detections will remain available here as preserved SOC history."
                : "The active SOC queue is currently clear. Threat events will appear here when detections are generated."}
            </div>
          </div>
        ) : (
          <div className="alerts-table-wrap">
            <table className="alerts-table">
              <thead>
                <tr>
                  <th style={{ width: "19%" }}>Alert</th>

                  <th style={{ width: "13%" }}>Detection</th>

                  <th style={{ width: "11%" }}>Severity</th>

                  <th style={{ width: "10%" }}>Confidence</th>

                  <th style={{ width: "12%" }}>Status</th>

                  <th style={{ width: "12%" }}>Dataset</th>

                  <th style={{ width: "13%" }}>Detected</th>

                  <th style={{ width: "10%" }}>Action</th>
                </tr>
              </thead>

              <tbody>
                {displayedAlerts.map((alert) => (
                  <tr key={alert.id}>
                    {/* ALERT */}

                    <td>
                      <button
                        type="button"
                        className="alert-investigate-button"
                        style={{
                          border: 0,
                          background: "transparent",
                          padding: 0,
                          height: "auto",
                        }}
                        onClick={() => void openAlertDetails(alert.alert_id)}
                      >
                        <div className="alert-cell-id">{alert.alert_id}</div>
                      </button>

                      <div
                        className="alert-cell-time"
                        style={{
                          marginTop: "5px",
                        }}
                      >
                        ID #{alert.id}
                      </div>
                    </td>

                    {/* DETECTION */}

                    <td>
                      <div className="alert-cell-class">
                        {alert.predicted_class}
                      </div>
                    </td>

                    {/* SEVERITY */}

                    <td>
                      <span
                        className={severityClass(alert.severity as Severity)}
                      >
                        {severityIcon(alert.severity as Severity)}

                        {alert.severity}
                      </span>
                    </td>

                    {/* CONFIDENCE */}

                    <td>
                      <div className="alert-cell-confidence">
                        {formatPercent(alert.confidence)}
                      </div>
                    </td>

                    {/* STATUS */}

                    <td>
                      <span className={statusClass(alert.status)}>
                        {statusLabel(alert.status)}
                      </span>
                    </td>

                    {/* DATASET */}

                    <td>
                      <div className="alert-cell-dataset">Unknown</div>
                    </td>

                    {/* TIME */}

                    <td>
                      <div className="alert-cell-time">
                        {formatShortDateTime(alert.detected_at)}
                      </div>
                    </td>

                    {/* ACTION */}

                    <td>
                      <button
                        type="button"
                        className="alert-investigate-button"
                        onClick={() => void openAlertDetails(alert.alert_id)}
                      >
                        <Eye size={11} />
                        Investigate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {paginationTotal > PAGE_SIZE && (
        <div className="alerts-pagination">
          <span>
            Page <strong>{page}</strong> of <strong>{totalPages}</strong>
          </span>
          <div className="alerts-pagination-controls">
            <button
              type="button"
              className="prev-next"
              disabled={page === 1}
              onClick={() => setPage((v) => Math.max(1, v - 1))}
              title="Previous Page"
            >
              <ChevronLeft size={14} />
              <span>Prev</span>
            </button>
            {visiblePages.map((n) => (
              <button
                key={n}
                type="button"
                className={page === n ? "active" : ""}
                onClick={() => setPage(n)}
              >
                {n}
              </button>
            ))}
            <button
              type="button"
              className="prev-next"
              disabled={page >= totalPages}
              onClick={() => setPage((v) => Math.min(totalPages, v + 1))}
              title="Next Page"
            >
              <span>Next</span>
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* =================================================
          FOOTER
      ================================================= */}

      <div
        className="alerts-status-bar"
        style={{
          marginTop: "12px",
          marginBottom: 0,
        }}
      >
        <div className="alerts-status-left">
          <div className="alerts-status-item">
            <Database size={11} />
            Dataset-derived detection data
          </div>

          <span className="alerts-status-divider" />

          <div className="alerts-status-item">No live packet capture</div>
        </div>

        <div className="alerts-status-right">
          <div className="alerts-refresh-text">
            Active queue refreshes every 5 seconds
          </div>
        </div>
      </div>

      {/* =================================================
          INVESTIGATION DRAWER
      ================================================= */}

      {selectedAlert && (
        <AlertDetails
          key={selectedAlert.alert_id}
          alert={selectedAlert}
          onClose={() => setSelectedAlert(null)}
          onStatusChange={updateStatus}
          updating={updating}
          onExplain={async (alertId) => {
            const updated = await generateAlertExplanation(alertId);
            setSelectedAlert((current) =>
              current?.alert_id === alertId ? updated : current,
            );
          }}
        />
      )}
    </div>
  );
}

export default Alerts;
