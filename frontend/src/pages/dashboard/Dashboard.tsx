import { sessionFetch } from "../../services/sessionFetch";
import { scheduleLoad } from "../../utils/scheduleLoad";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  Radio,
  RefreshCw,
  Shield,
  TrendingUp,
  Wifi,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { formatShortDateTime, formatTime } from "../../utils/datetime";
import "./Dashboard.css";

interface DashboardSummaryData {
  status: string;
  alerts: {
    total: number;
    active: number;
    resolved: number;
    critical_active: number;
    high_active: number;
    medium_active: number;
    low_active: number;
    open: number;
    acknowledged: number;
    investigating: number;
  };
  incidents: {
    total: number;
    active: number;
    closed: number;
    open: number;
    acknowledged: number;
    investigating: number;
    resolved: number;
  };
  network: {
    total_events: number;
    unique_source_ips: number;
    unique_destination_ips: number;
    tcp_events: number;
    udp_events: number;
    other_protocol_events: number;
  };
  attack_distribution: Array<{
    name: string;
    count: number;
  }>;
  recent_alerts: Array<{
    id: number;
    alert_id: string;
    predicted_class: string;
    confidence: number;
    severity: string;
    status: string;
    source_ip: string | null;
    destination_ip: string | null;
    source_port: number | null;
    destination_port: number | null;
    dataset_name: string | null;
    detected_at: string | null;
  }>;
}

import { API_BASE_URL } from "../../services/config";

function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatConfidence(value: number): string {
  const normalized = value <= 1 ? value * 100 : value;
  return `${normalized.toFixed(1)}%`;
}

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem("zuka_access_token");
  return {
    Accept: "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardSummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadDashboard = useCallback(async () => {
    try {
      const response = await sessionFetch(
        `${API_BASE_URL}/api/dashboard/summary`,
        {
          headers: getAuthHeaders(),
        },
      );

      if (!response.ok) {
        throw new Error(
          `Unable to retrieve dashboard metrics (${response.status}).`,
        );
      }

      const summary: DashboardSummaryData = await response.json();
      setData(summary);
      setLastUpdated(new Date());
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to connect to SOC dashboard backend.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const cancelInitialLoad = scheduleLoad(loadDashboard);

    const interval = window.setInterval(() => {
      void loadDashboard();
    }, 6000);

    return () => {
      cancelInitialLoad();
      window.clearInterval(interval);
    };
  }, [loadDashboard]);

  const maxAttackCount =
    data && data.attack_distribution.length > 0
      ? Math.max(...data.attack_distribution.map((item) => item.count))
      : 1;

  const totalResolved = data
    ? (data.alerts.resolved || 0) + (data.incidents.closed || 0)
    : 0;

  return (
    <div className="dashboard-page">
      {/* =====================================================
          HEADER SECTION
      ===================================================== */}
      <section className="dashboard-header">
        <div className="dashboard-header-text">
          <div className="dashboard-eyebrow">SECURITY WORKSPACE</div>
          <h1>Overview</h1>
          <p>Review alerts, investigate incidents, and track response work.</p>
        </div>

        <div className="dashboard-status-row">
          <div className="dashboard-engine-status">
            <span className="dashboard-engine-dot" />
            <span>
              {error
                ? "Connection unavailable"
                : data
                  ? "Workspace connected"
                  : "Connecting..."}
            </span>
          </div>

          <div className="dashboard-live-card">
            <div className="dashboard-live-card-top">
              <span className="dashboard-live-title">RECENT ACTIVITY</span>
              <div className="dashboard-live-indicator">
                <Radio size={14} className="dashboard-pulse-icon" />
                <span>DATASET REPLAY</span>
              </div>
            </div>
            <div className="dashboard-live-status">
              <Wifi size={14} />
              <span>
                {data?.network.total_events
                  ? `${formatNumber(data.network.total_events)} recorded events`
                  : "No events yet"}
              </span>
            </div>
            <div className="dashboard-live-meta">
              <Clock size={12} />
              <span>
                {lastUpdated
                  ? `Updated at ${formatTime(lastUpdated)}`
                  : "Loading activity..."}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* =====================================================
          ERROR BANNER
      ===================================================== */}
      {error && (
        <div className="dashboard-error-banner">
          <AlertTriangle size={18} />
          <span>{error}</span>
          <button
            type="button"
            className="dashboard-retry-btn"
            onClick={() => void loadDashboard()}
          >
            Retry
          </button>
        </div>
      )}

      {/* =====================================================
          PRIMARY KPI CARDS (Calculated across ALL DB Records)
      ===================================================== */}
      <div className="dashboard-section-heading">
        <span>PLATFORM HEALTH & METRICS</span>
        <button
          type="button"
          className="dashboard-quick-refresh"
          onClick={() => void loadDashboard()}
          disabled={refreshing}
          title="Refresh All Metrics"
        >
          <RefreshCw size={14} className={refreshing ? "dashboard-spin" : ""} />
          <span>{refreshing ? "Syncing..." : "Refresh"}</span>
        </button>
      </div>

      <section className="dashboard-kpis">
        {/* KPI 1: Active Alerts */}
        <div className="dashboard-kpi-card alert-card">
          <div className="dashboard-kpi-header">
            <div className="dashboard-kpi-icon alert">
              <AlertTriangle size={22} />
            </div>
            <Link
              to="/alerts"
              className="dashboard-kpi-link"
              title="Open Alert Center"
            >
              <ArrowUpRight size={16} />
            </Link>
          </div>
          <div className="dashboard-kpi-content">
            <span className="dashboard-kpi-label">Active Alerts</span>
            <strong className="dashboard-kpi-value">
              {loading || !data ? "—" : formatNumber(data.alerts.active)}
            </strong>
            <div className="dashboard-kpi-sub">
              {loading || !data ? (
                "Calculating..."
              ) : (
                <>
                  <span className="badge-critical">
                    {formatNumber(data.alerts.critical_active)} Critical
                  </span>
                  <span className="badge-sep">•</span>
                  <span className="badge-high">
                    {formatNumber(data.alerts.high_active)} High
                  </span>
                  <span className="badge-sep">•</span>
                  <span className="badge-sub-info">
                    {formatNumber(data.alerts.open)} Open
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* KPI 2: Events Processed */}
        <div className="dashboard-kpi-card network-card">
          <div className="dashboard-kpi-header">
            <div className="dashboard-kpi-icon network">
              <Activity size={22} />
            </div>
            <Link
              to="/network-monitor"
              className="dashboard-kpi-link"
              title="Open Network Monitor"
            >
              <ArrowUpRight size={16} />
            </Link>
          </div>
          <div className="dashboard-kpi-content">
            <span className="dashboard-kpi-label">Events Processed</span>
            <strong className="dashboard-kpi-value">
              {loading || !data ? "—" : formatNumber(data.network.total_events)}
            </strong>
            <div className="dashboard-kpi-sub">
              {loading || !data ? (
                "Counting telemetry..."
              ) : (
                <span>
                  {formatNumber(data.network.tcp_events)} TCP ·{" "}
                  {formatNumber(data.network.udp_events)} UDP ·{" "}
                  {formatNumber(data.network.other_protocol_events)} Other
                </span>
              )}
            </div>
          </div>
        </div>

        {/* KPI 3: Active Incidents */}
        <div className="dashboard-kpi-card incident-card">
          <div className="dashboard-kpi-header">
            <div className="dashboard-kpi-icon incident">
              <Shield size={22} />
            </div>
            <Link
              to="/incidents"
              className="dashboard-kpi-link"
              title="Open Incidents"
            >
              <ArrowUpRight size={16} />
            </Link>
          </div>
          <div className="dashboard-kpi-content">
            <span className="dashboard-kpi-label">Active Incidents</span>
            <strong className="dashboard-kpi-value">
              {loading || !data ? "—" : formatNumber(data.incidents.active)}
            </strong>
            <div className="dashboard-kpi-sub">
              {loading || !data ? (
                "Gathering cases..."
              ) : (
                <span>
                  {formatNumber(data.incidents.open)} Open ·{" "}
                  {formatNumber(data.incidents.investigating)} Investigating
                </span>
              )}
            </div>
          </div>
        </div>

        {/* KPI 4: Resolved History */}
        <div
          className="dashboard-kpi-card resolved-card dashboard-stat-clickable"
          onClick={() => navigate("/alerts?history=true")}
          title="Inspect Resolved Alert History in Alert Center"
        >
          <div className="dashboard-kpi-header">
            <div className="dashboard-kpi-icon resolved">
              <CheckCircle2 size={22} />
            </div>
            <Link
              to="/alerts?history=true"
              className="dashboard-kpi-link"
              title="Open Alert History"
              onClick={(e) => e.stopPropagation()}
            >
              <ArrowUpRight size={16} />
            </Link>
          </div>
          <div className="dashboard-kpi-content">
            <span className="dashboard-kpi-label">Resolved / Retained</span>
            <strong className="dashboard-kpi-value">
              {loading || !data ? "—" : formatNumber(totalResolved)}
            </strong>
            <div className="dashboard-kpi-sub">
              {loading || !data ? (
                "Preserved history..."
              ) : (
                <span>
                  {formatNumber(data.alerts.resolved)} Alerts ·{" "}
                  {formatNumber(data.incidents.closed)} Closed Tickets
                </span>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* =====================================================
          MIDDLE PANELS: TELEMETRY + ATTACK DISTRIBUTION
      ===================================================== */}
      <section className="dashboard-panels">
        {/* NETWORK ACTIVITY PANEL */}
        <div className="dashboard-panel">
          <div className="dashboard-panel-header">
            <div>
              <div className="dashboard-panel-eyebrow">NETWORK TELEMETRY</div>
              <h2>Traffic Breakdown & Endpoints</h2>
            </div>
            <Activity size={20} className="dashboard-header-accent" />
          </div>

          <div className="dashboard-panel-body">
            <div className="dashboard-telemetry-grid">
              <div className="dashboard-data-box">
                <span className="data-box-label">Total Flow Events</span>
                <strong className="data-box-val">
                  {data ? formatNumber(data.network.total_events) : "—"}
                </strong>
                <small className="data-box-meta">Recorded events</small>
              </div>

              <div className="dashboard-data-box">
                <span className="data-box-label">Unique Source IPs</span>
                <strong className="data-box-val">
                  {data ? formatNumber(data.network.unique_source_ips) : "—"}
                </strong>
                <small className="data-box-meta">Origin nodes</small>
              </div>

              <div className="dashboard-data-box">
                <span className="data-box-label">Unique Dest IPs</span>
                <strong className="data-box-val">
                  {data
                    ? formatNumber(data.network.unique_destination_ips)
                    : "—"}
                </strong>
                <small className="data-box-meta">Target servers</small>
              </div>

              <div className="dashboard-data-box">
                <span className="data-box-label">TCP Packets</span>
                <strong className="data-box-val">
                  {data ? formatNumber(data.network.tcp_events) : "—"}
                </strong>
                <small className="data-box-meta">Connection-oriented</small>
              </div>

              <div className="dashboard-data-box">
                <span className="data-box-label">UDP Packets</span>
                <strong className="data-box-val">
                  {data ? formatNumber(data.network.udp_events) : "—"}
                </strong>
                <small className="data-box-meta">Datagram flows</small>
              </div>

              <div className="dashboard-data-box">
                <span className="data-box-label">Raw Protocols</span>
                <strong className="data-box-val">
                  {data
                    ? formatNumber(data.network.other_protocol_events)
                    : "—"}
                </strong>
                <small className="data-box-meta">ICMP / Custom</small>
              </div>
            </div>
          </div>
        </div>

        {/* THREAT DETECTION: ATTACK DISTRIBUTION */}
        <div className="dashboard-panel">
          <div className="dashboard-panel-header">
            <div>
              <div className="dashboard-panel-eyebrow">MACHINE LEARNING</div>
              <h2>Attack Class Distribution</h2>
            </div>
            <TrendingUp size={20} className="dashboard-header-accent" />
          </div>

          <div className="dashboard-panel-body">
            {!data || data.attack_distribution.length === 0 ? (
              <div className="dashboard-empty-panel">
                <div className="dashboard-empty-icon">
                  <Shield size={24} />
                </div>
                <h3>No attack detections</h3>
                <p>
                  ML detection records will populate distribution bars as replay
                  feeds are processed.
                </p>
              </div>
            ) : (
              <div className="dashboard-attack-list">
                {data.attack_distribution.map((item) => {
                  const percentage =
                    maxAttackCount > 0
                      ? Math.round((item.count / maxAttackCount) * 100)
                      : 0;

                  return (
                    <div key={item.name} className="dashboard-attack-item">
                      <div className="dashboard-attack-meta">
                        <span className="attack-name">{item.name}</span>
                        <div className="attack-stats">
                          <strong className="attack-count">
                            {formatNumber(item.count)}
                          </strong>
                          <span className="attack-share">({percentage}%)</span>
                        </div>
                      </div>

                      <div className="dashboard-attack-track">
                        <div
                          className="dashboard-attack-fill"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* =====================================================
          LOWER PANEL: RECENT SOC ACTIVITY
      ===================================================== */}
      <section className="dashboard-panel recent-panel">
        <div className="dashboard-panel-header">
          <div>
            <div className="dashboard-panel-eyebrow">RECENT DETECTIONS</div>
            <h2>Recent Detection Records</h2>
          </div>
          <div className="dashboard-header-right">
            <Link to="/alerts" className="dashboard-view-all-link">
              View All Alerts →
            </Link>
          </div>
        </div>

        <div className="dashboard-table-container">
          {!data || data.recent_alerts.length === 0 ? (
            <div className="dashboard-empty-panel">
              <CheckCircle2 size={24} />
              <h3>No detections recorded</h3>
              <p>Security detections will appear here automatically.</p>
            </div>
          ) : (
            <table className="dashboard-table">
              <thead>
                <tr>
                  <th>ALERT ID</th>
                  <th>PREDICTED ATTACK</th>
                  <th>CONFIDENCE</th>
                  <th>SEVERITY</th>
                  <th>STATUS</th>
                  <th>DATASET</th>
                  <th>TIMESTAMP</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_alerts.map((alert) => (
                  <tr key={alert.alert_id}>
                    <td>
                      <Link to={`/alerts`} className="dashboard-cell-id">
                        {alert.alert_id}
                      </Link>
                    </td>
                    <td>
                      <span className="dashboard-cell-class">
                        {alert.predicted_class}
                      </span>
                    </td>
                    <td>
                      <span className="dashboard-cell-confidence">
                        {formatConfidence(alert.confidence)}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`sev-badge sev-${alert.severity.toLowerCase()}`}
                      >
                        {alert.severity}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`stat-badge stat-${alert.status.toLowerCase()}`}
                      >
                        {alert.status}
                      </span>
                    </td>
                    <td>
                      <span className="dashboard-cell-dataset">Unknown</span>
                    </td>
                    <td>
                      <span className="dashboard-cell-time">
                        {alert.detected_at
                          ? formatShortDateTime(alert.detected_at)
                          : "—"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}

export default Dashboard;
