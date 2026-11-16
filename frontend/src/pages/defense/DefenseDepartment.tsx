import { scheduleLoad } from "../../utils/scheduleLoad";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Copy,
  ExternalLink,
  Flame,
  Globe,
  HelpCircle,
  Info,
  Layers,
  Loader2,
  Lock,
  Network,
  RefreshCw,
  Search,
  Server,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Zap,
} from "lucide-react";
import {
  applyDefenseAction,
  getOpenDefenseInvestigations,
  type ApplyDefensePayload,
  type DefenseInvestigation,
} from "../../services/api";
import { formatShortDateTime } from "../../utils/datetime";
import "./DefenseDepartment.css";

export interface DefenseStrategyDef {
  type: string;
  label: string;
  icon: typeof ShieldAlert;
  color: string;
  category: string;
  targetNetwork: string;
  summary: string;
  recommendedFor: string[];
}

const DEFENSE_STRATEGIES: DefenseStrategyDef[] = [
  {
    type: "VLAN_QUARANTINE",
    label: "Record device isolation",
    icon: Lock,
    color: "#f59e0b",
    category: "Network Isolation (L2/L3)",
    targetNetwork: "IoT Subnets, Sensor Rings, Smart Hub VLANs",
    summary:
      "Isolate the targeted device or local VLAN to a dedicated quarantine network. Cuts off lateral movement to internal assets while preserving packet monitoring.",
    recommendedFor: ["BOTNET", "INFILTRATION", "DDOS", "DOS"],
  },
  {
    type: "BLOCK_IP",
    label: "Record an IP block",
    icon: ShieldAlert,
    color: "#ef4444",
    category: "Perimeter Security (L3/L4 ACL)",
    targetNetwork: "WAN Gateway, Border Routers, Edge Firewalls",
    summary:
      "Document an intended IP block and its verification. Configure the firewall separately.",
    recommendedFor: [
      "PORT_SCAN",
      "BRUTE_FORCE",
      "DOS",
      "DDOS",
      "RECONNAISSANCE",
    ],
  },
  {
    type: "CREDENTIAL_ROTATION",
    label: "Record credential rotation",
    icon: ShieldCheck,
    color: "#8b5cf6",
    category: "Identity & Access Control (IAM)",
    targetNetwork: "API Gateways, Active Directory, IoT Management Plane",
    summary: "Document credential changes made in the affected system.",
    recommendedFor: ["BRUTE_FORCE", "BACKDOOR", "INFILTRATION"],
  },
  {
    type: "RATE_LIMIT",
    label: "Record rate limiting",
    icon: Flame,
    color: "#3b82f6",
    category: "Transport QoS & Flow Control (L4)",
    targetNetwork: "Ingress Interfaces, Public Switch Ports, API Endpoints",
    summary: "Document rate limits applied in the affected system.",
    recommendedFor: ["DOS", "DDOS", "FUZZING"],
  },
  {
    type: "FIRMWARE_PATCH",
    label: "Record a firmware update",
    icon: Server,
    color: "#10b981",
    category: "Endpoint & Application Shield (L7)",
    targetNetwork: "Embedded Microcontrollers, Firmware Services, RTSP/UPnP",
    summary:
      "Temporarily deactivate vulnerable exposed daemons (e.g. UPnP, Telnet port 23) and queue an urgent hotfix firmware update across the fleet.",
    recommendedFor: ["EXPLOIT", "FUZZING", "MALWARE"],
  },
  {
    type: "CUSTOM",
    label: "Other response",
    icon: Zap,
    color: "#06b6d4",
    category: "Bespoke Countermeasure Policy",
    targetNetwork: "Custom Segment / Hybrid Network",
    summary:
      "Formulate an analyst-specified containment directive tailored to complex, multi-stage, or novel attack scenarios.",
    recommendedFor: ["OTHER_ATTACK", "ALL"],
  },
];

type FilterTab = "ALL" | "CRITICAL_HIGH" | "NEEDS_DEFENSE" | "DEFENDED";
type DetailTab = "CONTAINMENT" | "TELEMETRY" | "DOSSIER";

function severityBadgeClass(severity: string) {
  switch (severity?.toUpperCase()) {
    case "CRITICAL":
      return "severity-badge badge-critical";
    case "HIGH":
      return "severity-badge badge-high";
    case "MEDIUM":
      return "severity-badge badge-medium";
    case "LOW":
      return "severity-badge badge-low";
    default:
      return "severity-badge badge-info";
  }
}

export default function DefenseDepartment() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [investigations, setInvestigations] = useState<DefenseInvestigation[]>(
    [],
  );
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters & Pagination
  const [filterTab, setFilterTab] = useState<FilterTab>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const PAGE_SIZE = 6;

  // Selected case & view tabs
  const [selectedCase, setSelectedCase] = useState<DefenseInvestigation | null>(
    null,
  );
  const [detailTab, setDetailTab] = useState<DetailTab>("CONTAINMENT");

  // Defense form state
  const [selectedStrategy, setSelectedStrategy] = useState<DefenseStrategyDef>(
    DEFENSE_STRATEGIES[0],
  );
  const [rationale, setRationale] = useState("");
  const [defenseNote, setDefenseNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [copiedIp, setCopiedIp] = useState(false);
  const [successBanner, setSuccessBanner] = useState<{
    message: string;
    investigation_id: string;
    incident_id: string;
  } | null>(null);

  const loadData = useCallback(async () => {
    try {
      const data = await getOpenDefenseInvestigations();
      setInvestigations(data);

      // Keep selection or auto-select first or matching search param
      setSelectedCase((prev) => {
        const targetId =
          searchParams.get("investigation_id") ||
          searchParams.get("case_id") ||
          searchParams.get("incident_id") ||
          searchParams.get("search") ||
          prev?.investigation_id;

        if (targetId) {
          const found = data.find(
            (item) =>
              item.investigation_id.toLowerCase() === targetId.toLowerCase() ||
              item.incident_id.toLowerCase() === targetId.toLowerCase(),
          );
          if (found) return found;
        }
        return data.length > 0 ? data[0] : null;
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load open defense investigations.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [searchParams]);

  useEffect(() => {
    return scheduleLoad(loadData);
  }, [loadData]);

  // Auto-generate defense note template when case or strategy changes
  const [previousInputs0, setpreviousInputs0] = useState<
    readonly unknown[] | null
  >(null);
  const currentInputs1 = [selectedCase, selectedStrategy];
  if (
    previousInputs0 === null ||
    currentInputs1.some(
      (value, index) => !Object.is(value, previousInputs0?.[index]),
    )
  ) {
    setpreviousInputs0(currentInputs1);

    if (!selectedCase) {
      setDefenseNote("");
      setRationale("");
    } else {
      const defaultRationale = `Review ${selectedCase.predicted_class} and record the planned response.`;
      setRationale(defaultRationale);
      const generatedNote = `Planned action: ${selectedStrategy.label}\nTarget: ${selectedCase.destination_ip}\nRecord the evidence and outcome here. This action does not configure a real device.`;

      setDefenseNote(generatedNote);
      setSuccessBanner(null);
    }
  }

  // Filtered investigations
  const filteredCases = useMemo(() => {
    let result = investigations;

    if (filterTab === "CRITICAL_HIGH") {
      result = result.filter(
        (c) =>
          c.incident_severity.toUpperCase() === "CRITICAL" ||
          c.incident_severity.toUpperCase() === "HIGH",
      );
    } else if (filterTab === "NEEDS_DEFENSE") {
      result = result.filter((c) => c.defense_actions_count === 0);
    } else if (filterTab === "DEFENDED") {
      result = result.filter((c) => c.defense_actions_count > 0);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (c) =>
          c.investigation_id.toLowerCase().includes(q) ||
          c.incident_id.toLowerCase().includes(q) ||
          c.incident_title.toLowerCase().includes(q) ||
          c.predicted_class.toLowerCase().includes(q) ||
          c.source_ip.toLowerCase().includes(q) ||
          c.destination_ip.toLowerCase().includes(q),
      );
    }

    return result;
  }, [investigations, filterTab, searchQuery]);

  // Metric counts
  const criticalCount = useMemo(
    () =>
      investigations.filter(
        (c) =>
          c.incident_severity.toUpperCase() === "CRITICAL" ||
          c.incident_severity.toUpperCase() === "HIGH",
      ).length,
    [investigations],
  );

  const needsActionCount = useMemo(
    () => investigations.filter((c) => c.defense_actions_count === 0).length,
    [investigations],
  );

  const containedCount = useMemo(
    () => investigations.filter((c) => c.defense_actions_count > 0).length,
    [investigations],
  );

  // Reset page when filter changes
  const [previousInputs1, setpreviousInputs1] = useState<
    readonly unknown[] | null
  >(null);
  const currentInputs2 = [searchQuery, filterTab];
  if (
    previousInputs1 === null ||
    currentInputs2.some(
      (value, index) => !Object.is(value, previousInputs1?.[index]),
    )
  ) {
    setpreviousInputs1(currentInputs2);

    setCurrentPage(1);
  }

  // Pagination slice
  const totalPages = Math.ceil(filteredCases.length / PAGE_SIZE) || 1;
  const paginatedCases = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredCases.slice(start, start + PAGE_SIZE);
  }, [filteredCases, currentPage]);

  async function handleApplyDefense() {
    if (!selectedCase) return;
    if (!defenseNote.trim()) {
      setError("Please supply a defense note before applying action.");
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const payload: ApplyDefensePayload = {
        investigation_id: selectedCase.investigation_id,
        incident_id: selectedCase.incident_id,
        action_type: selectedStrategy.type,
        action_label: selectedStrategy.label,
        rationale: rationale.trim() || selectedStrategy.summary,
        defense_note: defenseNote.trim(),
      };

      const res = await applyDefenseAction(payload);

      setSuccessBanner({
        message: `Defense action successfully applied! Containment note has been appended to the Investigation Department dossier for Case ${res.investigation_id}.`,
        investigation_id: res.investigation_id,
        incident_id: res.incident_id,
      });

      setSelectedCase((prev) =>
        prev
          ? {
              ...prev,
              analyst_notes: res.updated_notes,
              defense_actions_count: prev.defense_actions_count + 1,
            }
          : null,
      );

      void loadData();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to apply defense action.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  function handleCopyIp(text: string) {
    void navigator.clipboard.writeText(text);
    setCopiedIp(true);
    setTimeout(() => setCopiedIp(false), 1600);
  }

  return (
    <div className="defense-dashboard">
      {/* =====================================================================
          1. HEADER SECTION
          ===================================================================== */}
      <header className="defense-header-bar">
        <div className="defense-header-brand">
          <div className="defense-brand-icon">
            <ShieldAlert size={24} />
          </div>
          <div className="defense-brand-titles">
            <h1>Defense Department</h1>
            <div className="defense-brand-meta">
              <span className="defense-brand-subtitle">
                Threat Containment Console
              </span>
            </div>
          </div>
        </div>

        {/* METRIC CARDS */}
        <div className="defense-header-metrics">
          <div
            className="header-metric-card"
            title="Total active cases in containment queue"
          >
            <span className="header-metric-label">Queue</span>
            <span className="header-metric-value cyan">
              {investigations.length}
            </span>
          </div>

          <div
            className="header-metric-card"
            title="Incidents requiring immediate defensive containment"
          >
            <span className="header-metric-label">Needs Action</span>
            <span className="header-metric-value amber">
              {needsActionCount}
            </span>
          </div>

          <div
            className="header-metric-card"
            title="Incidents with containment countermeasures enforced"
          >
            <span className="header-metric-label">Contained</span>
            <span className="header-metric-value emerald">
              {containedCount}
            </span>
          </div>
        </div>

        {/* ACTION BUTTONS */}
        <div className="defense-header-actions">
          <button
            type="button"
            className="btn-header secondary"
            onClick={() => void loadData()}
            disabled={loading || refreshing}
            title="Refresh open defense cases"
          >
            <RefreshCw
              size={13}
              className={refreshing ? "spin-animation" : ""}
            />
            <span>Refresh</span>
          </button>

          <button
            type="button"
            className="btn-header primary"
            onClick={() => navigate("/investigation")}
            title="Switch to Investigation Department"
          >
            <Search size={13} />
            <span>Investigation Department</span>
          </button>
        </div>
      </header>

      {/* NOTIFICATION BANNERS */}
      {error && (
        <div className="defense-banner error">
          <div className="banner-left">
            <AlertTriangle size={16} />
            <span>{error}</span>
          </div>
          <button
            type="button"
            className="banner-dismiss"
            onClick={() => setError(null)}
            title="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}

      {successBanner && (
        <div className="defense-banner success">
          <div className="banner-left">
            <CheckCircle2 size={16} />
            <span>{successBanner.message}</span>
          </div>
          <div className="banner-links">
            <button
              type="button"
              className="banner-link"
              onClick={() =>
                navigate(
                  `/investigation?search=${encodeURIComponent(
                    successBanner.investigation_id,
                  )}`,
                )
              }
            >
              Open in Investigation ↗
            </button>
            <button
              type="button"
              className="banner-link"
              onClick={() =>
                navigate(
                  `/incidents?incident_id=${encodeURIComponent(
                    successBanner.incident_id,
                  )}`,
                )
              }
            >
              View in Incident Management ↗
            </button>
            <button
              type="button"
              className="banner-dismiss"
              onClick={() => setSuccessBanner(null)}
              title="Dismiss notification"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* =====================================================================
          MAIN TWO-COLUMN WORKSPACE
          ===================================================================== */}
      <div className="defense-workspace-layout">
        {/* ===================================================================
            2. INCIDENT QUEUE SECTION (LEFT PANEL)
            =================================================================== */}
        <aside className="incident-queue-panel">
          <div className="queue-panel-head">
            <div className="queue-head-title-row">
              <h2>Incident Queue</h2>
              <span className="queue-count-badge">
                {filteredCases.length} Cases
              </span>
            </div>
          </div>

          {/* QUEUE FILTERS */}
          <div className="queue-filter-tabs">
            <button
              type="button"
              className={`queue-tab-btn ${filterTab === "ALL" ? "active" : ""}`}
              onClick={() => setFilterTab("ALL")}
              title="All open defense cases"
            >
              All ({investigations.length})
            </button>
            <button
              type="button"
              className={`queue-tab-btn ${filterTab === "CRITICAL_HIGH" ? "active" : ""}`}
              onClick={() => setFilterTab("CRITICAL_HIGH")}
              title="Critical and High severity cases"
            >
              High/Critical ({criticalCount})
            </button>
            <button
              type="button"
              className={`queue-tab-btn ${filterTab === "NEEDS_DEFENSE" ? "active" : ""}`}
              onClick={() => setFilterTab("NEEDS_DEFENSE")}
              title="Cases requiring containment action"
            >
              Action ({needsActionCount})
            </button>
            <button
              type="button"
              className={`queue-tab-btn ${filterTab === "DEFENDED" ? "active" : ""}`}
              onClick={() => setFilterTab("DEFENDED")}
              title="Cases with containment enforced"
            >
              Contained ({containedCount})
            </button>
          </div>

          {/* QUEUE SEARCH BAR */}
          <div className="queue-search-container">
            <Search size={14} />
            <input
              type="text"
              placeholder="Search by ID, threat, host..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* QUEUE INCIDENT CARDS LIST */}
          {loading && investigations.length === 0 ? (
            <div className="investigation-empty-state">
              <Loader2 size={24} className="spin-animation" />
              <p>Loading incident queue...</p>
            </div>
          ) : paginatedCases.length === 0 ? (
            <div className="investigation-empty-state">
              <ShieldCheck size={32} style={{ color: "#10b981" }} />
              <h3>No Incidents Found</h3>
              <p>No active cases match the selected filter criteria.</p>
            </div>
          ) : (
            <div className="queue-cards-list">
              {paginatedCases.map((incident) => {
                const isSelected =
                  selectedCase?.investigation_id === incident.investigation_id;
                return (
                  <div
                    key={incident.investigation_id}
                    className={`incident-card ${isSelected ? "selected" : ""}`}
                    onClick={() => setSelectedCase(incident)}
                  >
                    <div className="incident-card-row-top">
                      <span className="incident-card-id">
                        {incident.investigation_id}
                      </span>
                      <span
                        className={severityBadgeClass(
                          incident.incident_severity,
                        )}
                      >
                        {incident.incident_severity}
                      </span>
                    </div>

                    <div
                      className="incident-card-title"
                      title={incident.incident_title}
                    >
                      {incident.incident_title}
                    </div>

                    <div className="incident-card-meta-row">
                      <span className="threat-classification-badge">
                        {incident.predicted_class}
                      </span>
                      <span
                        className="incident-card-ip"
                        title={incident.source_ip}
                      >
                        {incident.source_ip}
                      </span>
                    </div>

                    <div className="incident-card-footer">
                      <span className="incident-card-time">
                        <Clock3 size={11} />
                        {incident.started_at
                          ? formatShortDateTime(incident.started_at)
                          : "Active"}
                      </span>
                      {incident.defense_actions_count > 0 ? (
                        <span className="status-badge-contained">
                          <Shield size={11} />
                          {incident.defense_actions_count} Contained
                        </span>
                      ) : (
                        <span className="status-badge-action">
                          Action Required
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* QUEUE PAGINATION CONTROLS */}
          {filteredCases.length > PAGE_SIZE && (
            <div className="queue-pagination-bar">
              <span className="pagination-text">
                Page {currentPage} of {totalPages} ({filteredCases.length}{" "}
                Total)
              </span>
              <div className="pagination-controls">
                <button
                  type="button"
                  className="pagination-button"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  title="Previous page"
                >
                  <ChevronLeft size={13} />
                  <span>Prev</span>
                </button>
                <button
                  type="button"
                  className="pagination-button"
                  onClick={() =>
                    setCurrentPage((p) => Math.min(totalPages, p + 1))
                  }
                  disabled={currentPage === totalPages}
                  title="Next page"
                >
                  <span>Next</span>
                  <ChevronRight size={13} />
                </button>
              </div>
            </div>
          )}
        </aside>

        {/* ===================================================================
            3. INCIDENT INVESTIGATION PANEL (RIGHT PANEL)
            =================================================================== */}
        <main className="investigation-panel">
          {!selectedCase ? (
            <div className="investigation-empty-state">
              <ShieldAlert size={48} style={{ color: "#334155" }} />
              <h3>Select an Incident to Inspect</h3>
              <p>
                Choose an active incident from the queue on the left to review
                correlated threat telemetry, evaluate AI detection confidence,
                and deploy containment strategies.
              </p>
            </div>
          ) : (
            <>
              {/* INVESTIGATION PANEL TOP HEADER */}
              <div className="investigation-header-top">
                <div className="investigation-header-meta">
                  <span className="investigation-selected-id">
                    {selectedCase.investigation_id}
                  </span>
                  <span
                    className={severityBadgeClass(
                      selectedCase.incident_severity,
                    )}
                  >
                    {selectedCase.incident_severity}
                  </span>
                  <span className="threat-classification-badge">
                    {selectedCase.predicted_class}
                  </span>

                  {selectedCase.has_real_ips ? (
                    <span className="packet-ip-badge verified">
                      <span className="stage-dot" />
                      Verified Packet IP
                    </span>
                  ) : (
                    <span className="packet-ip-badge flow-vector">
                      <span
                        className="stage-dot"
                        style={{
                          background: "#38bdf8",
                          boxShadow: "0 0 6px #38bdf8",
                        }}
                      />
                      Flow Vector Telemetry
                    </span>
                  )}

                  <span className="linked-incident-ref">
                    Incident:{" "}
                    <button
                      type="button"
                      className="linked-incident-link"
                      onClick={() =>
                        navigate(
                          `/incidents?incident_id=${encodeURIComponent(
                            selectedCase.incident_id,
                          )}`,
                        )
                      }
                      title="Open correlated incident"
                    >
                      {selectedCase.incident_id}
                      <ExternalLink size={11} />
                    </button>
                  </span>
                </div>

                {/* VIEW TABS */}
                <div className="investigation-tabs-group">
                  <button
                    type="button"
                    className={`tab-nav-btn ${detailTab === "CONTAINMENT" ? "active" : ""}`}
                    onClick={() => setDetailTab("CONTAINMENT")}
                  >
                    <Shield size={13} />
                    <span>Containment</span>
                  </button>
                  <button
                    type="button"
                    className={`tab-nav-btn ${detailTab === "TELEMETRY" ? "active" : ""}`}
                    onClick={() => setDetailTab("TELEMETRY")}
                  >
                    <Globe size={13} />
                    <span>Telemetry</span>
                  </button>
                  <button
                    type="button"
                    className={`tab-nav-btn ${detailTab === "DOSSIER" ? "active" : ""}`}
                    onClick={() => setDetailTab("DOSSIER")}
                  >
                    <Layers size={13} />
                    <span>Dossier ({selectedCase.defense_actions_count})</span>
                  </button>
                </div>
              </div>

              {/* INVESTIGATION BODY CONTENT */}
              <div className="investigation-body-content">
                {/* ===========================================================
                    4. INCIDENT DETAILS SUMMARY (4 HORIZONTAL CARDS)
                    =========================================================== */}
                <section className="incident-summary-grid">
                  {/* CARD 1: THREAT CLASS */}
                  <div className="summary-card">
                    <span className="summary-card-label">Threat Class</span>
                    <div className="summary-card-value-row">
                      <span className="summary-card-value text-critical">
                        {selectedCase.predicted_class}
                      </span>
                    </div>
                    <span className="summary-card-sub">
                      AI Confidence: {selectedCase.confidence_pct}%
                    </span>
                  </div>

                  {/* CARD 2: ATTACKER ORIGIN */}
                  <div className="summary-card">
                    <span className="summary-card-label">Attacker Origin</span>
                    <div className="summary-card-value-row">
                      <span className="summary-card-value text-high">
                        {selectedCase.source_ip}
                      </span>
                      {selectedCase.has_real_ips && (
                        <button
                          type="button"
                          className="summary-copy-btn"
                          onClick={() => handleCopyIp(selectedCase.source_ip)}
                          title="Copy Attacker IP"
                        >
                          {copiedIp ? (
                            <CheckCircle2
                              size={12}
                              style={{ color: "#10b981" }}
                            />
                          ) : (
                            <Copy size={12} />
                          )}
                        </button>
                      )}
                    </div>
                    <span className="summary-card-sub">
                      Port: {selectedCase.source_port} | Proto:{" "}
                      {selectedCase.protocol}
                    </span>
                  </div>

                  {/* CARD 3: TARGET ASSET */}
                  <div className="summary-card">
                    <span className="summary-card-label">Target Asset</span>
                    <div className="summary-card-value-row">
                      <span className="summary-card-value text-target">
                        {selectedCase.destination_ip}
                      </span>
                      {selectedCase.has_real_ips && (
                        <button
                          type="button"
                          className="summary-copy-btn"
                          onClick={() =>
                            handleCopyIp(selectedCase.destination_ip)
                          }
                          title="Copy Target IP"
                        >
                          {copiedIp ? (
                            <CheckCircle2
                              size={12}
                              style={{ color: "#10b981" }}
                            />
                          ) : (
                            <Copy size={12} />
                          )}
                        </button>
                      )}
                    </div>
                    <span className="summary-card-sub">
                      Target Port: {selectedCase.destination_port}
                    </span>
                  </div>

                  {/* CARD 4: CONTAINMENT STATUS */}
                  <div className="summary-card">
                    <span className="summary-card-label">
                      Containment Status
                    </span>
                    <div className="summary-card-value-row">
                      <span
                        className={`summary-card-value ${
                          selectedCase.defense_actions_count > 0
                            ? "text-emerald"
                            : "text-amber"
                        }`}
                        style={{
                          color:
                            selectedCase.defense_actions_count > 0
                              ? "#10b981"
                              : "#f59e0b",
                        }}
                      >
                        {selectedCase.defense_actions_count > 0
                          ? `${selectedCase.defense_actions_count} Actions recorded`
                          : "Awaiting Action"}
                      </span>
                    </div>
                    <span className="summary-card-sub">
                      {selectedCase.has_real_ips
                        ? "Verified Packet Capture"
                        : "Statistical Flow Vector"}
                    </span>
                  </div>
                </section>

                {/* ===========================================================
                    TAB 1: CONTAINMENT CONSOLE
                    =========================================================== */}
                {detailTab === "CONTAINMENT" && (
                  <>
                    {/* 5. CONTAINMENT STRATEGY CARDS (3-COLUMN GRID) */}
                    <section className="strategy-section-wrapper">
                      <div className="strategy-section-header">
                        <h3>Response options</h3>
                        <span>Select targeted defense countermeasure</span>
                      </div>

                      <div className="strategy-cards-grid">
                        {DEFENSE_STRATEGIES.map((strategy) => {
                          const isSelected =
                            selectedStrategy.type === strategy.type;
                          const IconComponent = strategy.icon;
                          const isRecommended =
                            strategy.recommendedFor.includes(
                              selectedCase.predicted_class?.toUpperCase() || "",
                            ) || strategy.recommendedFor.includes("ALL");

                          return (
                            <div
                              key={strategy.type}
                              className={`strategy-card ${isSelected ? "selected" : ""}`}
                              onClick={() => setSelectedStrategy(strategy)}
                            >
                              <div>
                                <div className="strategy-card-top-row">
                                  <div
                                    className="strategy-icon-box"
                                    style={{
                                      color: strategy.color,
                                      background: strategy.color + "18",
                                      border: `1px solid ${strategy.color}40`,
                                    }}
                                  >
                                    <IconComponent size={16} />
                                  </div>
                                  <span className="strategy-category-label">
                                    {strategy.category}
                                  </span>
                                </div>

                                <div className="strategy-content-body">
                                  <div className="strategy-card-title">
                                    {strategy.label}
                                  </div>
                                  <div className="strategy-card-desc">
                                    {strategy.summary}
                                  </div>
                                </div>
                              </div>

                              <div className="strategy-card-foot">
                                <span
                                  className="strategy-target-network"
                                  title={strategy.targetNetwork}
                                >
                                  <Network size={11} />
                                  {strategy.targetNetwork}
                                </span>
                                {isRecommended && (
                                  <span className="strategy-recommended-tag">
                                    RECOMMENDED
                                  </span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </section>

                    {/* 6. CONTAINMENT DIRECTIVE FORM */}
                    <section className="containment-form-section">
                      <div className="form-field-group">
                        <label className="form-field-label">
                          <span>Tactical Rationale</span>
                          <small>
                            Audit justification and operational rationale
                          </small>
                        </label>
                        <input
                          type="text"
                          className="form-text-input"
                          value={rationale}
                          onChange={(e) => setRationale(e.target.value)}
                          placeholder="e.g. Hostile volumetric pattern threatening switch port. Immediate VLAN containment applied."
                        />
                      </div>

                      <div className="form-field-group">
                        <label className="form-field-label">
                          <span>Defense Directive Note</span>
                          <small>
                            Synchronizes automatically into Investigation
                            Department dossier
                          </small>
                        </label>
                        <textarea
                          className="form-textarea"
                          rows={5}
                          value={defenseNote}
                          onChange={(e) => setDefenseNote(e.target.value)}
                          placeholder="Formulate defensive directives and containment verification..."
                        />
                      </div>

                      <div className="containment-form-actions">
                        <div className="target-investigation-badge">
                          Target Incident Dossier:{" "}
                          <strong>{selectedCase.investigation_id}</strong>
                        </div>

                        <button
                          type="button"
                          className="btn-enforce-containment"
                          onClick={() => void handleApplyDefense()}
                          disabled={submitting || !defenseNote.trim()}
                        >
                          {submitting ? (
                            <>
                              <Loader2 size={15} className="spin-animation" />
                              <span>Saving action...</span>
                            </>
                          ) : (
                            <>
                              <ShieldCheck size={16} />
                              <span>Record defense action</span>
                            </>
                          )}
                        </button>
                      </div>
                    </section>
                  </>
                )}

                {/* ===========================================================
                    TAB 2: TELEMETRY & FLOW DIAGNOSIS
                    =========================================================== */}
                {detailTab === "TELEMETRY" && (
                  <div className="telemetry-tab-container">
                    <div className="telemetry-card">
                      <div className="telemetry-card-title">
                        <Globe size={16} style={{ color: "#38bdf8" }} />
                        <span>Network Detection Telemetry Specification</span>
                      </div>

                      <div className="telemetry-specs-grid">
                        <div className="telemetry-spec-tile">
                          <span className="spec-tile-label">
                            Attacker Origin Host
                          </span>
                          <div className="summary-card-value-row">
                            <span className="spec-tile-value text-high">
                              {selectedCase.source_ip}
                            </span>
                            {selectedCase.has_real_ips && (
                              <button
                                type="button"
                                className="summary-copy-btn"
                                onClick={() =>
                                  handleCopyIp(selectedCase.source_ip)
                                }
                                title="Copy Source IP"
                              >
                                {copiedIp ? (
                                  <CheckCircle2
                                    size={12}
                                    style={{ color: "#10b981" }}
                                  />
                                ) : (
                                  <Copy size={12} />
                                )}
                              </button>
                            )}
                          </div>
                          <span className="spec-tile-sub">
                            Source Port: {selectedCase.source_port} | Protocol:{" "}
                            {selectedCase.protocol}
                          </span>
                        </div>

                        <div className="telemetry-spec-tile">
                          <span className="spec-tile-label">
                            Target Asset Endpoint
                          </span>
                          <div className="summary-card-value-row">
                            <span className="spec-tile-value text-target">
                              {selectedCase.destination_ip}
                            </span>
                            {selectedCase.has_real_ips && (
                              <button
                                type="button"
                                className="summary-copy-btn"
                                onClick={() =>
                                  handleCopyIp(selectedCase.destination_ip)
                                }
                                title="Copy Destination IP"
                              >
                                {copiedIp ? (
                                  <CheckCircle2
                                    size={12}
                                    style={{ color: "#10b981" }}
                                  />
                                ) : (
                                  <Copy size={12} />
                                )}
                              </button>
                            )}
                          </div>
                          <span className="spec-tile-sub">
                            Target Port: {selectedCase.destination_port}
                          </span>
                        </div>
                      </div>

                      <div className="telemetry-diagnosis-box">
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 8,
                            marginBottom: 6,
                            color: "#38bdf8",
                            fontWeight: 700,
                          }}
                        >
                          <Info size={15} />
                          <span>Telemetry Threat Diagnosis:</span>
                        </div>
                        <p style={{ margin: 0 }}>{selectedCase.diagnosis}</p>
                      </div>

                      {!selectedCase.has_real_ips && (
                        <div className="flow-vector-banner">
                          <HelpCircle
                            size={18}
                            style={{ flexShrink: 0, color: "#38bdf8" }}
                          />
                          <div>
                            <strong>
                              Why is this case showing Flow Telemetry instead of
                              raw IP headers?
                            </strong>
                            <p>
                              This detection was captured from statistical
                              network flow vectors (packet counts, byte rates,
                              flow duration, and inter-arrival time metrics).
                              Raw IP headers were omitted at ingestion to
                              preserve bandwidth and IoT privacy, but behavioral
                              flow anomalies clearly indicated hostile activity.
                              Containment strategies apply to the affected
                              subnet segment.
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* ===========================================================
                    TAB 3: INVESTIGATION DOSSIER & NOTES
                    =========================================================== */}
                {detailTab === "DOSSIER" && (
                  <div className="dossier-tab-container">
                    <div className="dossier-card">
                      <div
                        className="telemetry-card-title"
                        style={{ marginBottom: 12 }}
                      >
                        <Layers size={16} style={{ color: "#c084fc" }} />
                        <span>Synchronized Investigation Dossier Notes</span>
                      </div>

                      <div className="dossier-notes-container">
                        {selectedCase.analyst_notes ? (
                          selectedCase.analyst_notes
                        ) : (
                          <div className="dossier-empty-message">
                            No analyst notes recorded yet. Apply a defense
                            action from the Containment tab to append the first
                            containment directive.
                          </div>
                        )}
                      </div>

                      <div className="dossier-footer-actions">
                        <button
                          type="button"
                          className="btn-header secondary"
                          onClick={() =>
                            navigate(
                              `/investigation?search=${encodeURIComponent(
                                selectedCase.investigation_id,
                              )}`,
                            )
                          }
                        >
                          <span>Open in Investigation Department</span>
                          <ExternalLink size={13} />
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
