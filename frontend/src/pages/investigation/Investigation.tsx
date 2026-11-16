import { sessionFetch } from "../../services/sessionFetch";
import { scheduleLoad } from "../../utils/scheduleLoad";
import { formatShortDateTime } from "../../utils/datetime";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Clock3,
  Copy,
  Download,
  FileSearch,
  FileText,
  Loader2,
  PauseCircle,
  PlayCircle,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";

import {
  getInvestigations,
  updateInvestigationConclusion,
  updateInvestigationNotes,
  updateInvestigationStatus,
  type Investigation as InvestigationRecord,
} from "../../services/api";

import "./Investigation.css";

const STATUS_OPTIONS = [
  "ALL",
  "NOT_STARTED",
  "IN_PROGRESS",
  "ON_HOLD",
  "COMPLETED",
];

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

function statusClass(status: string) {
  switch (status) {
    case "IN_PROGRESS":
      return "investigation-status in-progress";
    case "ON_HOLD":
      return "investigation-status on-hold";
    case "COMPLETED":
      return "investigation-status completed";
    default:
      return "investigation-status not-started";
  }
}

function Investigation() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [investigations, setInvestigations] = useState<InvestigationRecord[]>(
    [],
  );

  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 10;

  const [selected, setSelected] = useState<InvestigationRecord | null>(null);

  const [statusFilter, setStatusFilter] = useState("ALL");

  const [search, setSearch] = useState(() => searchParams.get("search") || "");
  const [copied, setCopied] = useState(false);

  const [notes, setNotes] = useState("");

  const [conclusion, setConclusion] = useState("");

  const [loading, setLoading] = useState(true);

  const [refreshing, setRefreshing] = useState(false);

  const [savingNotes, setSavingNotes] = useState(false);

  const [savingConclusion, setSavingConclusion] = useState(false);

  const [updatingStatus, setUpdatingStatus] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [downloadingReport, setDownloadingReport] = useState(false);

  const handleDownloadForensicReport = async () => {
    if (!selected) return;
    setDownloadingReport(true);
    try {
      const token = localStorage.getItem("zuka_access_token");
      const headers: HeadersInit = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await sessionFetch(
        `/api/reports/investigations/${encodeURIComponent(selected.investigation_id)}/pdf`,
        {
          headers,
        },
      );
      if (!res.ok) {
        let msg = `Export failed (${res.status})`;
        try {
          const body = await res.json();
          msg = body.detail || msg;
        } catch {
          /* The optional browser feature or response body is unavailable. */
        }
        throw new Error(msg);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `ZUKA-${selected.investigation_id}-Investigation-Report.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(
        err instanceof Error
          ? err.message
          : "Unable to export forensic report.",
      );
    } finally {
      setDownloadingReport(false);
    }
  };

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

    const q = searchParams.get("search") || searchParams.get("incident_id");
    if (q !== null && q !== undefined) {
      setSearch(q);
    }
  }

  const [previousInputs1, setpreviousInputs1] = useState<
    readonly unknown[] | null
  >(null);
  const currentInputs2 = [searchParams, investigations];
  if (
    previousInputs1 === null ||
    currentInputs2.some(
      (value, index) => !Object.is(value, previousInputs1?.[index]),
    )
  ) {
    setpreviousInputs1(currentInputs2);

    const invId = searchParams.get("investigation_id");
    const incId = searchParams.get("incident_id");
    if (investigations.length > 0) {
      if (invId) {
        const found = investigations.find(
          (item) => item.investigation_id === invId,
        );
        if (found) setSelected(found);
      } else if (incId) {
        const found = investigations.find((item) => item.incident_id === incId);
        if (found) setSelected(found);
      }
    }
  }

  const loadInvestigations = useCallback(async () => {
    try {
      const data = await getInvestigations({
        status: statusFilter === "ALL" ? undefined : statusFilter,
        search: search.trim() || undefined,
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      });

      setInvestigations(data.items);
      setTotal(data.total);

      // Do not replace the selected object during the 5-second refresh
      // while the analyst is editing notes/conclusion. That would reset
      // the controlled textareas and make typing appear broken.
      setSelected((current) => {
        if (!current) {
          return data.items[0] ?? null;
        }

        const refreshed = data.items.find(
          (item) => item.investigation_id === current.investigation_id,
        );

        // Preserve the current object when it is on this page so the
        // 5-second refresh never overwrites unsaved analyst text.
        if (refreshed) {
          return current;
        }

        // When pagination moves to another page, select its first case.
        return data.items[0] ?? null;
      });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load investigations.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [page, search, statusFilter]);

  const [previousInputs2, setpreviousInputs2] = useState<
    readonly unknown[] | null
  >(null);
  const currentInputs3 = [search, statusFilter];
  if (
    previousInputs2 === null ||
    currentInputs3.some(
      (value, index) => !Object.is(value, previousInputs2?.[index]),
    )
  ) {
    setpreviousInputs2(currentInputs3);

    setPage(1);
  }

  useEffect(() => {
    const cancelInitialLoad = scheduleLoad(loadInvestigations);

    const interval = window.setInterval(() => {
      void loadInvestigations();
    }, 5000);

    return () => {
      cancelInitialLoad();
      window.clearInterval(interval);
    };
  }, [loadInvestigations]);

  const [previousInputs3, setpreviousInputs3] = useState<
    readonly unknown[] | null
  >(null);
  // A refreshed copy of the same case must not replace an analyst's draft.
  const currentInputs4 = [selected?.investigation_id ?? null];
  if (
    previousInputs3 === null ||
    currentInputs4.some(
      (value, index) => !Object.is(value, previousInputs3?.[index]),
    )
  ) {
    setpreviousInputs3(currentInputs4);

    if (!selected) {
      setNotes("");
      setConclusion("");
    } else {
      setNotes(selected.analyst_notes ?? "");
      setConclusion(selected.conclusion ?? "");
    }
  }

  const statistics = useMemo(() => {
    return {
      total,
      notStarted: investigations.filter((item) => item.status === "NOT_STARTED")
        .length,
      inProgress: investigations.filter((item) => item.status === "IN_PROGRESS")
        .length,
      onHold: investigations.filter((item) => item.status === "ON_HOLD").length,
      completed: investigations.filter((item) => item.status === "COMPLETED")
        .length,
    };
  }, [investigations, total]);

  async function saveNotes() {
    if (!selected) {
      return;
    }

    try {
      setSavingNotes(true);
      setError(null);

      const updated = await updateInvestigationNotes(
        selected.investigation_id,
        {
          analyst_notes: notes,
        },
      );

      setSelected(updated);

      setInvestigations((current) =>
        current.map((item) =>
          item.investigation_id === updated.investigation_id ? updated : item,
        ),
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to save analyst notes.",
      );
    } finally {
      setSavingNotes(false);
    }
  }

  async function saveConclusion() {
    if (!selected) {
      return;
    }

    if (!conclusion.trim()) {
      setError("A conclusion is required before saving.");
      return;
    }

    try {
      setSavingConclusion(true);
      setError(null);

      const updated = await updateInvestigationConclusion(
        selected.investigation_id,
        {
          conclusion: conclusion.trim(),
        },
      );

      setSelected(updated);

      setInvestigations((current) =>
        current.map((item) =>
          item.investigation_id === updated.investigation_id ? updated : item,
        ),
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to save conclusion.",
      );
    } finally {
      setSavingConclusion(false);
    }
  }

  async function changeStatus(nextStatus: string) {
    if (!selected) {
      return;
    }

    if (selected.status === "COMPLETED") {
      return;
    }

    if (
      nextStatus === "COMPLETED" &&
      !selected.conclusion?.trim() &&
      !conclusion.trim()
    ) {
      setError(
        "Save an investigation conclusion before completing the investigation.",
      );
      return;
    }

    try {
      setUpdatingStatus(true);
      setError(null);

      let current = selected;

      if (
        nextStatus === "COMPLETED" &&
        conclusion.trim() &&
        conclusion.trim() !== (selected.conclusion ?? "").trim()
      ) {
        current = await updateInvestigationConclusion(
          selected.investigation_id,
          {
            conclusion: conclusion.trim(),
          },
        );

        setSelected(current);

        setInvestigations((items) =>
          items.map((item) =>
            item.investigation_id === current.investigation_id ? current : item,
          ),
        );
      }

      const updated = await updateInvestigationStatus(
        current.investigation_id,
        {
          status: nextStatus,
        },
      );

      setSelected(updated);

      setInvestigations((items) =>
        items.map((item) =>
          item.investigation_id === updated.investigation_id ? updated : item,
        ),
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to update investigation status.",
      );
    } finally {
      setUpdatingStatus(false);
    }
  }

  const isCompleted = selected?.status === "COMPLETED";

  return (
    <main className="investigation-page">
      <header className="investigation-header">
        <div>
          <div className="investigation-eyebrow">
            SOC OPERATIONS / INVESTIGATION
          </div>

          <div className="investigation-title-row">
            <div className="investigation-title-icon">
              <FileSearch size={22} />
            </div>

            <div>
              <h1>Investigation Center</h1>
              <p>
                Investigate detected security incidents using evidence, analyst
                notes, conclusions, and controlled investigation states.
              </p>
            </div>
          </div>
        </div>

        <button
          type="button"
          className="investigation-refresh"
          onClick={() => void loadInvestigations()}
          disabled={refreshing}
        >
          <RefreshCw
            size={15}
            className={refreshing ? "investigation-spin" : ""}
          />
          Refresh
        </button>
      </header>

      {error && (
        <div className="investigation-error">
          <ShieldAlert size={17} />
          <span>{error}</span>
        </div>
      )}

      <section className="investigation-stats">
        <div className="investigation-stat-card">
          <span>Total Investigations</span>
          <strong>{statistics.total}</strong>
        </div>

        <div className="investigation-stat-card">
          <span>Not Started</span>
          <strong>{statistics.notStarted}</strong>
        </div>

        <div className="investigation-stat-card active">
          <span>In Progress</span>
          <strong>{statistics.inProgress}</strong>
        </div>

        <div className="investigation-stat-card hold">
          <span>On Hold</span>
          <strong>{statistics.onHold}</strong>
        </div>

        <div className="investigation-stat-card complete">
          <span>Completed</span>
          <strong>{statistics.completed}</strong>
        </div>
      </section>

      <section className="investigation-workspace">
        <aside className="investigation-queue">
          <div className="queue-header">
            <div>
              <span className="queue-eyebrow">INVESTIGATION QUEUE</span>
              <h2>Cases</h2>
            </div>

            <span className="queue-count">{investigations.length}</span>
          </div>

          <div className="queue-controls">
            <div className="investigation-search">
              <Search size={15} />

              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search investigation..."
              />
            </div>

            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              {STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {status === "ALL" ? "All statuses" : statusLabel(status)}
                </option>
              ))}
            </select>
          </div>

          <div className="investigation-list">
            {loading ? (
              <div className="investigation-empty">
                <Loader2 size={22} className="investigation-spin" />
                <span>Loading investigations...</span>
              </div>
            ) : investigations.length === 0 ? (
              <div className="investigation-empty">
                <FileSearch size={25} />
                <strong>No investigations found</strong>
                <span>
                  Investigations created from SOC incidents will appear here.
                </span>
              </div>
            ) : (
              investigations.map((item) => (
                <button
                  type="button"
                  key={item.investigation_id}
                  className={`investigation-list-item ${
                    selected?.investigation_id === item.investigation_id
                      ? "selected"
                      : ""
                  }`}
                  onClick={() => setSelected(item)}
                >
                  <div className="case-top-row">
                    <span className="case-id">{item.investigation_id}</span>

                    <span className={statusClass(item.status)}>
                      {statusLabel(item.status)}
                    </span>
                  </div>

                  <div className="case-incident">
                    <ShieldAlert size={13} />
                    {item.incident_id}
                  </div>

                  <div className="case-time">
                    <Clock3 size={12} />
                    Created {formatShortDateTime(item.created_at)}
                  </div>
                </button>
              ))
            )}
          </div>

          {total > 0 && (
            <div className="investigation-pagination">
              <span>
                Page <strong>{page}</strong> of{" "}
                <strong>{Math.ceil(total / PAGE_SIZE)}</strong>
              </span>
              <div className="investigation-pagination-controls">
                <button
                  type="button"
                  className="prev-next"
                  onClick={() => setPage((value) => Math.max(1, value - 1))}
                  disabled={page === 1}
                  title="Previous Page"
                >
                  <ChevronLeft size={14} />
                  <span>Prev</span>
                </button>
                {Array.from(
                  { length: Math.min(5, Math.ceil(total / PAGE_SIZE)) },
                  (_, index) => {
                    const pageCount = Math.ceil(total / PAGE_SIZE);
                    const startPage = Math.max(
                      1,
                      Math.min(page - 2, pageCount - 4),
                    );
                    const pageNumber = startPage + index;
                    return (
                      <button
                        key={pageNumber}
                        type="button"
                        className={page === pageNumber ? "active" : ""}
                        onClick={() => setPage(pageNumber)}
                      >
                        {pageNumber}
                      </button>
                    );
                  },
                )}
                <button
                  type="button"
                  className="prev-next"
                  onClick={() =>
                    setPage((value) =>
                      Math.min(Math.ceil(total / PAGE_SIZE), value + 1),
                    )
                  }
                  disabled={page >= Math.ceil(total / PAGE_SIZE)}
                  title="Next Page"
                >
                  <span>Next</span>
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </aside>

        <section className="investigation-detail">
          {!selected ? (
            <div className="detail-empty">
              <FileSearch size={38} />
              <h2>Select an investigation</h2>
              <p>
                Choose a case from the investigation queue to begin the analyst
                workflow.
              </p>
            </div>
          ) : (
            <>
              <div className="detail-header">
                <div>
                  <div className="detail-eyebrow">INVESTIGATION CASE</div>

                  <h2>{selected.investigation_id}</h2>

                  <p>
                    Linked incident: <strong>{selected.incident_id}</strong>
                  </p>
                </div>

                <div className="detail-header-actions">
                  <button
                    type="button"
                    className="investigation-export-report-btn"
                    onClick={handleDownloadForensicReport}
                    disabled={downloadingReport}
                    title="Export forensic investigation report PDF"
                  >
                    {downloadingReport ? (
                      <Loader2 size={13} className="investigation-spin" />
                    ) : (
                      <Download size={13} />
                    )}
                    <span>Export Forensic Report (PDF)</span>
                  </button>

                  <button
                    type="button"
                    className="investigation-view-report-btn"
                    onClick={() => navigate("/reports")}
                    title="Open Reports center"
                  >
                    <FileText size={13} />
                    <span>Reports</span>
                  </button>

                  <span className={statusClass(selected.status)}>
                    {statusLabel(selected.status)}
                  </span>
                </div>
              </div>

              <div className="evidence-grid">
                <div className="evidence-card">
                  <div className="evidence-icon">
                    <ShieldAlert size={18} />
                  </div>

                  <div>
                    <span>Linked Incident</span>
                    <strong>{selected.incident_id}</strong>
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
                        padding: 0,
                      }}
                      onClick={() =>
                        navigate(
                          `/incidents?search=${encodeURIComponent(
                            selected.incident_id,
                          )}`,
                        )
                      }
                      title="Inspect linked incident in Incident Management"
                    >
                      View Incident ↗
                    </button>
                  </div>
                </div>

                <div className="evidence-card">
                  <div className="evidence-icon">
                    <Clock3 size={18} />
                  </div>

                  <div>
                    <span>Started</span>
                    <strong>{formatShortDateTime(selected.started_at)}</strong>
                  </div>
                </div>

                <div className="evidence-card">
                  <div className="evidence-icon">
                    <CheckCircle2 size={18} />
                  </div>

                  <div>
                    <span>Completed</span>
                    <strong>
                      {formatShortDateTime(selected.completed_at)}
                    </strong>
                  </div>
                </div>

                {selected.alert_id && (
                  <div className="evidence-card">
                    <div className="evidence-icon">
                      <ShieldCheck size={18} />
                    </div>
                    <div>
                      <span>Linked Alert</span>
                      <strong>{selected.alert_id}</strong>
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
                          padding: 0,
                        }}
                        onClick={() =>
                          navigate(
                            `/alerts?search=${encodeURIComponent(
                              selected.alert_id!,
                            )}`,
                          )
                        }
                      >
                        Inspect Alert ↗
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <div className="workflow-panel">
                <div className="panel-heading">
                  <div>
                    <span className="panel-eyebrow">ANALYST WORKFLOW</span>
                    <h3>Investigation Status</h3>
                  </div>
                </div>

                <div className="workflow-actions">
                  {selected.status === "NOT_STARTED" && (
                    <button
                      type="button"
                      onClick={() => void changeStatus("IN_PROGRESS")}
                      disabled={updatingStatus}
                    >
                      <PlayCircle size={16} />
                      Start Investigation
                    </button>
                  )}

                  {selected.status === "IN_PROGRESS" && (
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => void changeStatus("ON_HOLD")}
                      disabled={updatingStatus}
                    >
                      <PauseCircle size={16} />
                      Put On Hold
                    </button>
                  )}

                  {selected.status === "ON_HOLD" && (
                    <button
                      type="button"
                      onClick={() => void changeStatus("IN_PROGRESS")}
                      disabled={updatingStatus}
                    >
                      <PlayCircle size={16} />
                      Resume Investigation
                    </button>
                  )}

                  {selected.status !== "COMPLETED" && (
                    <button
                      type="button"
                      className="complete-button"
                      onClick={() => void changeStatus("COMPLETED")}
                      disabled={
                        updatingStatus ||
                        !(conclusion.trim() || selected.conclusion?.trim())
                      }
                    >
                      {updatingStatus ? (
                        <Loader2 size={16} className="investigation-spin" />
                      ) : (
                        <ClipboardCheck size={16} />
                      )}
                      Complete Investigation
                    </button>
                  )}

                  {isCompleted && (
                    <div className="completed-notice">
                      <CheckCircle2 size={17} />
                      Investigation completed. Notes and conclusion can still be
                      refined.
                    </div>
                  )}

                  <button
                    type="button"
                    className="secondary"
                    style={{ borderColor: "#3b82f6", color: "#60a5fa" }}
                    onClick={() => {
                      if (selected.incident_id) {
                        navigate(
                          `/incidents?incident_id=${encodeURIComponent(selected.incident_id)}`,
                        );
                      } else {
                        navigate("/incidents");
                      }
                    }}
                    title="Proceed to Incident Management to Resolve or Close case"
                  >
                    <span>Proceed to Incident Management ↗</span>
                  </button>

                  <button
                    type="button"
                    className="secondary"
                    style={{
                      borderColor: "rgba(239, 68, 68, 0.4)",
                      color: "#f87171",
                    }}
                    onClick={() => {
                      if (selected.incident_id) {
                        navigate(
                          `/defense?case_id=${encodeURIComponent(selected.incident_id)}`,
                        );
                      } else {
                        navigate("/defense");
                      }
                    }}
                    title="Review network detection telemetry and deploy defense countermeasures"
                  >
                    <span>Defense Department ↗</span>
                  </button>

                  <button
                    type="button"
                    className="secondary"
                    onClick={() => {
                      const alertTarget =
                        selected.alert_id || selected.incident_id;
                      navigate(
                        `/alerts?search=${encodeURIComponent(alertTarget)}`,
                      );
                    }}
                    title="Cross-reference incident alerts in Alert Center"
                  >
                    <ShieldAlert size={15} />
                    Inspect in Alert Center ↗
                  </button>

                  <button
                    type="button"
                    className="secondary"
                    onClick={async () => {
                      try {
                        await navigator.clipboard.writeText(
                          JSON.stringify(selected, null, 2),
                        );
                        setCopied(true);
                        setTimeout(() => setCopied(false), 2000);
                      } catch {
                        // ignore
                      }
                    }}
                  >
                    <Copy size={15} />
                    {copied ? "Copied Case JSON!" : "Copy Case Record"}
                  </button>
                </div>
              </div>

              <div className="investigation-editor-grid">
                <section className="editor-panel">
                  <div className="panel-heading">
                    <div>
                      <span className="panel-eyebrow">ANALYST RECORD</span>
                      <h3>Analyst Investigation Notes</h3>
                      <p className="editor-helper">
                        Record the evidence reviewed, observations,
                        correlations, and actions taken during the
                        investigation.
                      </p>
                    </div>
                  </div>

                  <textarea
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                    placeholder="Record evidence reviewed, observations, correlations, and analyst actions..."
                  />

                  <div className="editor-footer">
                    <span>
                      {isCompleted
                        ? "Saved in PostgreSQL (Editable post-completion)"
                        : "Notes are stored in PostgreSQL"}
                    </span>

                    <button
                      type="button"
                      onClick={() => void saveNotes()}
                      disabled={savingNotes}
                    >
                      {savingNotes ? (
                        <Loader2 size={15} className="investigation-spin" />
                      ) : null}
                      Save Notes
                    </button>
                  </div>
                </section>

                <section className="editor-panel">
                  <div className="panel-heading">
                    <div>
                      <span className="panel-eyebrow">ANALYST RECORD</span>
                      <h3>Analyst Conclusion</h3>
                      <p className="editor-helper">
                        Write the final evidence-based finding. This conclusion
                        becomes the Incident Resolution Summary when the
                        incident is resolved.
                      </p>
                    </div>
                  </div>

                  <textarea
                    value={conclusion}
                    onChange={(event) => setConclusion(event.target.value)}
                    placeholder="Document the evidence-based conclusion of the investigation..."
                  />

                  <div className="editor-footer">
                    <span>
                      {isCompleted
                        ? "Resolution summary updated in Incident"
                        : "Required before completion"}
                    </span>

                    <button
                      type="button"
                      onClick={() => void saveConclusion()}
                      disabled={savingConclusion || !conclusion.trim()}
                    >
                      {savingConclusion ? (
                        <Loader2 size={15} className="investigation-spin" />
                      ) : null}
                      Save Conclusion
                    </button>
                  </div>
                </section>
              </div>

              <div className="timeline-panel">
                <div className="panel-heading">
                  <div>
                    <span className="panel-eyebrow">CASE TIMELINE</span>
                    <h3>Investigation Record</h3>
                  </div>
                </div>

                <div className="timeline">
                  <div className="timeline-item">
                    <span className="timeline-dot" />

                    <div>
                      <strong>Investigation created</strong>
                      <span>{formatShortDateTime(selected.created_at)}</span>
                    </div>
                  </div>

                  {selected.started_at && (
                    <div className="timeline-item">
                      <span className="timeline-dot active" />

                      <div>
                        <strong>Investigation started</strong>
                        <span>{formatShortDateTime(selected.started_at)}</span>
                      </div>
                    </div>
                  )}

                  {selected.completed_at && (
                    <div className="timeline-item">
                      <span className="timeline-dot complete" />

                      <div>
                        <strong>Investigation completed</strong>
                        <span>
                          {formatShortDateTime(selected.completed_at)}
                        </span>
                      </div>
                    </div>
                  )}

                  <div className="timeline-item">
                    <span className="timeline-dot" />

                    <div>
                      <strong>Last record update</strong>
                      <span>{formatShortDateTime(selected.updated_at)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </section>
      </section>
    </main>
  );
}

export default Investigation;
