import { formatShortDateTime } from "../../utils/datetime";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  FileText,
  MessageSquare,
  Search,
  Shield,
  ShieldAlert,
  X,
} from "lucide-react";

import {
  addIncidentNote,
  escalateIncident,
  getIncident,
  getIncidents,
  getInvestigations,
  updateIncidentStatus,
} from "../../services/api";
import type { Incident } from "../../services/api";
import { formatIncidentDetails } from "./incidentDetailsFormatter";

type FilterStatus =
  | "ALL"
  | "OPEN"
  | "ACKNOWLEDGED"
  | "INVESTIGATING"
  | "RESOLVED"
  | "CLOSED";

const STATUS_ORDER: FilterStatus[] = [
  "ALL",
  "OPEN",
  "ACKNOWLEDGED",
  "INVESTIGATING",
  "RESOLVED",
  "CLOSED",
];

function statusClass(status: string): string {
  return status.toLowerCase().replace(/\s+/g, "-");
}

function severityClass(severity: string): string {
  return severity.toLowerCase().replace(/\s+/g, "-");
}

function nextStatus(status: string): string | null {
  switch (status.toUpperCase()) {
    case "OPEN":
      return "INVESTIGATING";

    case "ACKNOWLEDGED":
      return "INVESTIGATING";

    case "INVESTIGATING":
      return "RESOLVED";

    case "RESOLVED":
      return "CLOSED";

    default:
      return null;
  }
}

function Incidents() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const [selectedIncident, setSelectedIncident] =
    useState<Incident | null>(null);

  const [statusFilter, setStatusFilter] =
    useState<FilterStatus>("ALL");

  const [search, setSearch] = useState(() => searchParams.get("search") || "");
  const [copied, setCopied] = useState(false);

  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] =
    useState<string | null>(null);

  useEffect(() => {
    const q = searchParams.get("search");
    if (q !== null && q !== undefined) {
      setSearch(q);
    }
  }, [searchParams]);

  useEffect(() => {
    if (selectedIncident) {
      window.dispatchEvent(
        new CustomEvent("zuka:set-context", {
          detail: {
            incident_id: selectedIncident.incident_id,
            alert_id: selectedIncident.alert_id,
            page_route: "/incidents",
          },
        })
      );
    }
  }, [selectedIncident]);

  useEffect(() => {
    const incId = searchParams.get("incident_id");
    if (incId && incidents.length > 0) {
      const found = incidents.find((item) => item.incident_id === incId);
      if (found) {
        setSelectedIncident(found);
      }
    }
  }, [searchParams, incidents]);

  const loadIncidents = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await getIncidents({
        status:
          statusFilter === "ALL"
            ? undefined
            : statusFilter,
        search: search.trim() || undefined,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      });

      setIncidents(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load incidents.",
      );
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => {
    setPage(1);
  }, [search, statusFilter]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadIncidents();
    }, 250);

    return () => {
      window.clearTimeout(timer);
    };
  }, [loadIncidents]);

  const loadIncidentDetails = async (
    incidentId: string,
  ) => {
    setDetailLoading(true);
    setError(null);

    try {
      const incident = await getIncident(incidentId);
      setSelectedIncident(incident);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load incident details.",
      );
    } finally {
      setDetailLoading(false);
    }
  };

  const handleSelectIncident = (
    incident: Incident,
  ) => {
    setActionMessage(null);
    void loadIncidentDetails(incident.incident_id);
  };

  const [closeModalOpen, setCloseModalOpen] = useState(false);
  const [closingSummary, setClosingSummary] = useState("");
  const [resolveModalOpen, setResolveModalOpen] = useState(false);
  const [resolutionSummary, setResolutionSummary] = useState("");
  const [resolvedSuccessModal, setResolvedSuccessModal] = useState<{
    incident_id: string;
    resolution_summary?: string;
  } | null>(null);
  const [escalateModalOpen, setEscalateModalOpen] = useState(false);
  const [escalationReason, setEscalationReason] = useState("Critical Asset Compromised - Priority Escalation");
  const [escalationNotes, setEscalationNotes] = useState("");

  const [investigationIncompleteModalOpen, setInvestigationIncompleteModalOpen] = useState(false);
  const [investigationCaseId, setInvestigationCaseId] = useState<string | null>(null);

  const [noteModalOpen, setNoteModalOpen] = useState(false);
  const [incidentNoteText, setIncidentNoteText] = useState("");

  const [investigationStatus, setInvestigationStatus] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    if (!selectedIncident) {
      setInvestigationStatus(null);
      return;
    }

    if (selectedIncident.investigation_status) {
      setInvestigationStatus(selectedIncident.investigation_status.toUpperCase());
    }

    getInvestigations({
      incident_id: selectedIncident.incident_id,
      limit: 1,
    })
      .then((res) => {
        if (!isMounted) return;
        const inv = res.items && res.items.length > 0 ? res.items[0] : null;
        setInvestigationStatus(inv ? inv.status.toUpperCase() : null);
        if (inv?.conclusion && inv.conclusion.trim()) {
          setResolutionSummary(inv.conclusion.trim());
        }
      })
      .catch(() => {});

    return () => {
      isMounted = false;
    };
  }, [selectedIncident?.incident_id, selectedIncident?.status]);

  const isInvestigationCompleted =
    (investigationStatus || selectedIncident?.investigation_status || "").toUpperCase() === "COMPLETED";

  const handleTransition = async () => {
    if (!selectedIncident) {
      return;
    }

    const targetStatus = nextStatus(
      selectedIncident.status,
    );

    if (!targetStatus) {
      return;
    }

    if (targetStatus === "CLOSED") {
      setClosingSummary(selectedIncident.resolution_summary || "");
      setCloseModalOpen(true);
      return;
    }

    if (targetStatus === "RESOLVED") {
      setActionLoading(true);
      setError(null);
      try {
        const invRes = await getInvestigations({
          incident_id: selectedIncident.incident_id,
          limit: 1,
        });
        const inv = invRes.items && invRes.items.length > 0 ? invRes.items[0] : null;
        setInvestigationCaseId(inv ? inv.investigation_id : null);
        const prefillSummary = (inv?.conclusion && inv.conclusion.trim())
          ? inv.conclusion.trim()
          : (selectedIncident.resolution_summary || "Threat actor contained, network indicators mitigated, and forensic investigation completed.");
        setResolutionSummary(prefillSummary);
        setResolveModalOpen(true);
      } catch {
        setResolutionSummary(
          selectedIncident.resolution_summary ||
          "Threat actor contained, network indicators mitigated, and forensic investigation completed."
        );
        setResolveModalOpen(true);
      } finally {
        setActionLoading(false);
      }
      return;
    }

    setActionLoading(true);
    setError(null);
    setActionMessage(null);

    try {
      const updated = await updateIncidentStatus(
        selectedIncident.incident_id,
        {
          status: targetStatus,
        },
      );

      setSelectedIncident(updated);

      setIncidents((current) =>
        current.map((item) =>
          item.incident_id === updated.incident_id
            ? updated
            : item,
        ),
      );

      setActionMessage(
        `Incident ${updated.incident_id} successfully updated to ${updated.status}.`,
      );

      await loadIncidents();

      if (targetStatus === "INVESTIGATING") {
        navigate(`/investigation?incident_id=${encodeURIComponent(updated.incident_id)}`);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to update incident status.",
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmResolve = async () => {
    if (!selectedIncident) return;
    setActionLoading(true);
    setError(null);
    setActionMessage(null);

    try {
      const updated = await updateIncidentStatus(
        selectedIncident.incident_id,
        {
          status: "RESOLVED",
          resolution_summary: resolutionSummary.trim() || undefined,
        },
      );

      setSelectedIncident(updated);

      setIncidents((current) =>
        current.map((item) =>
          item.incident_id === updated.incident_id
            ? updated
            : item,
        ),
      );

      setResolveModalOpen(false);
      setResolvedSuccessModal({
        incident_id: updated.incident_id,
        resolution_summary: updated.resolution_summary || undefined,
      });

      setActionMessage(
        `Incident ${updated.incident_id} successfully marked RESOLVED and investigation COMPLETED.`,
      );

      await loadIncidents();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to resolve incident.",
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmClose = async () => {
    if (!selectedIncident) return;
    setActionLoading(true);
    setError(null);
    setActionMessage(null);

    try {
      const updated = await updateIncidentStatus(
        selectedIncident.incident_id,
        {
          status: "CLOSED",
          resolution_summary: closingSummary.trim() || undefined,
        },
      );

      setSelectedIncident(updated);
      setIncidents((current) =>
        current.map((item) =>
          item.incident_id === updated.incident_id ? updated : item,
        ),
      );

      setActionMessage(
        `Incident ${updated.incident_id} successfully CLOSED. Resolution summary archived.`,
      );
      setCloseModalOpen(false);
      await loadIncidents();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to close incident.",
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleEscalate = () => {
    if (!selectedIncident) return;
    if (selectedIncident.status.toUpperCase() !== "INVESTIGATING") {
      setError(
        `Cannot escalate incident: An active investigation must be started first (current status is '${selectedIncident.status}'). Please click 'Start Investigation' first.`
      );
      return;
    }
    setEscalationReason("Critical Asset Compromised - Priority Escalation");
    setEscalationNotes("");
    setEscalateModalOpen(true);
  };

  const handleConfirmEscalate = async () => {
    if (!selectedIncident) return;
    setActionLoading(true);
    setError(null);
    setActionMessage(null);

    try {
      const fullReason = escalationNotes.trim()
        ? `${escalationReason}: ${escalationNotes.trim()}`
        : escalationReason;

      const updated = await escalateIncident(
        selectedIncident.incident_id,
        { reason: fullReason },
      );

      setSelectedIncident(updated);
      setIncidents((current) =>
        current.map((item) =>
          item.incident_id === updated.incident_id ? updated : item,
        ),
      );

      setActionMessage(
        `Incident ${updated.incident_id} escalated to Level ${updated.escalation_level} (${updated.priority} Priority). Audit logged.`,
      );
      setEscalateModalOpen(false);
      await loadIncidents();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to escalate incident.",
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmAddNote = async () => {
    if (!selectedIncident || !incidentNoteText.trim()) return;
    setActionLoading(true);
    setError(null);
    setActionMessage(null);

    try {
      const updated = await addIncidentNote(
        selectedIncident.incident_id,
        incidentNoteText.trim(),
      );

      setSelectedIncident(updated);
      setIncidents((current) =>
        current.map((item) =>
          item.incident_id === updated.incident_id ? updated : item,
        ),
      );

      setNoteModalOpen(false);
      setIncidentNoteText("");
      setActionMessage(
        `Analyst note saved for ${updated.incident_id} and recorded in audit log.`,
      );
      await loadIncidents();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to save analyst note.",
      );
    } finally {
      setActionLoading(false);
    }
  };

  const formattedDetails = useMemo(() => {
    if (!selectedIncident) return null;
    return formatIncidentDetails(selectedIncident);
  }, [selectedIncident]);

  const summary = useMemo(() => {
    const critical = incidents.filter(
      (item) =>
        item.severity.toUpperCase() === "CRITICAL",
    ).length;

    const active = incidents.filter(
      (item) =>
        !["RESOLVED", "CLOSED"].includes(
          item.status.toUpperCase(),
        ),
    ).length;

    const closed = incidents.filter(
      (item) =>
        item.status.toUpperCase() === "CLOSED",
    ).length;

    return {
      total,
      active,
      critical,
      closed,
    };
  }, [incidents, total]);

  return (
    <div className="incident-page">
      <style>{`
        .incident-page {
          width: 100%;
          max-width: 1440px;
          margin: 0 auto;
          color: #edf4f7;
        }

        .incident-header {
          margin-bottom: 28px;
        }

        .incident-eyebrow {
          color: #607d94;
          font-size: 10px;
          font-weight: 700;
          letter-spacing: 0.16em;
          margin-bottom: 10px;
        }

        .incident-title {
          margin: 0;
          font-size: 30px;
          line-height: 1.2;
          font-weight: 700;
        }

        .incident-description {
          margin: 10px 0 0;
          color: #69869d;
          font-size: 14px;
          line-height: 1.6;
        }

        .incident-kpis {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 14px;
          margin-bottom: 18px;
        }

        .incident-kpi {
          border: 1px solid #19364a;
          background: #091826;
          border-radius: 10px;
          padding: 18px;
        }

        .incident-kpi-label {
          color: #66849b;
          font-size: 10px;
          font-weight: 700;
          letter-spacing: 0.12em;
          text-transform: uppercase;
        }

        .incident-kpi-value {
          margin-top: 8px;
          font-size: 25px;
          font-weight: 700;
          color: #edf4f7;
        }

        .incident-toolbar {
          display: flex;
          gap: 12px;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
          margin-bottom: 14px;
        }

        .incident-search {
          flex: 1;
          min-width: 260px;
          height: 42px;
          box-sizing: border-box;
          border: 1px solid #1a3a4e;
          border-radius: 8px;
          background: #091826;
          color: #edf4f7;
          padding: 0 14px;
          outline: none;
        }

        .incident-search:focus {
          border-color: #27d7a5;
        }

        .incident-refresh {
          height: 42px;
          border: 1px solid #1a3a4e;
          border-radius: 8px;
          background: #0b1d2b;
          color: #9ab0c0;
          padding: 0 16px;
          cursor: pointer;
        }

        .incident-refresh:hover {
          border-color: #27d7a5;
          color: #27d7a5;
        }

        .incident-tabs {
          display: flex;
          gap: 6px;
          overflow-x: auto;
          padding-bottom: 2px;
        }

        .incident-tab {
          border: 1px solid #19364a;
          border-radius: 7px;
          background: #091826;
          color: #7691a5;
          padding: 9px 13px;
          font-size: 11px;
          font-weight: 700;
          cursor: pointer;
          white-space: nowrap;
        }

        .incident-tab.active {
          border-color: #1ec89a;
          background: #0b2a2b;
          color: #27d7a5;
        }

        .incident-layout {
          display: grid;
          grid-template-columns: minmax(0, 1.65fr) minmax(340px, 0.9fr);
          gap: 16px;
          align-items: start;
        }

        .incident-card {
          border: 1px solid #19364a;
          border-radius: 10px;
          background: #091826;
          overflow: hidden;
        }

        .incident-card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          padding: 16px 18px;
          border-bottom: 1px solid #142f42;
        }

        .incident-card-title {
          color: #dce9ee;
          font-size: 12px;
          font-weight: 700;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }

        .incident-count {
          color: #5f7d94;
          font-size: 11px;
        }

        .incident-table-wrap {
          overflow-x: auto;
        }

        .incident-table {
          width: 100%;
          border-collapse: collapse;
          min-width: 760px;
        }

        .incident-table th {
          text-align: left;
          padding: 12px 14px;
          color: #58758b;
          font-size: 9px;
          font-weight: 700;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          border-bottom: 1px solid #142f42;
        }

        .incident-table td {
          padding: 14px;
          border-bottom: 1px solid #10293a;
          color: #9ab0c0;
          font-size: 11px;
          vertical-align: middle;
        }

        .incident-row {
          cursor: pointer;
          transition: background 0.15s ease;
        }

        .incident-row:hover {
          background: #0c2130;
        }

        .incident-row.selected {
          background: #0b2a2b;
        }

        .incident-id {
          color: #d9e8ed;
          font-weight: 700;
          font-size: 11px;
        }

        .incident-name {
          margin-top: 4px;
          color: #69869d;
          max-width: 300px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .badge {
          display: inline-flex;
          align-items: center;
          min-height: 23px;
          padding: 0 8px;
          border-radius: 999px;
          border: 1px solid transparent;
          font-size: 9px;
          font-weight: 800;
          letter-spacing: 0.06em;
        }

        .badge.critical {
          color: #ff8d8d;
          background: #32171b;
          border-color: #61242b;
        }

        .badge.high {
          color: #ffb36b;
          background: #342316;
          border-color: #62401f;
        }

        .badge.medium {
          color: #e8c96b;
          background: #302a18;
          border-color: #594d22;
        }

        .badge.low {
          color: #7fc9a8;
          background: #11291f;
          border-color: #24523b;
        }

        .badge.open {
          color: #ffb36b;
          background: #342316;
          border-color: #62401f;
        }

        .badge.acknowledged {
          color: #9dc6ef;
          background: #142a3c;
          border-color: #28506d;
        }

        .badge.investigating {
          color: #d3b5ff;
          background: #281d39;
          border-color: #4c3567;
        }

        .badge.resolved {
          color: #7fd8b7;
          background: #112d24;
          border-color: #245943;
        }

        .badge.closed {
          color: #7c9caf;
          background: #13232e;
          border-color: #274252;
        }

        .incident-detail {
          min-height: 300px;
        }

        .detail-content {
          padding: 18px;
        }

        .detail-id {
          color: #27d7a5;
          font-size: 11px;
          font-weight: 800;
          letter-spacing: 0.06em;
        }

        .detail-title {
          margin: 8px 0 0;
          color: #edf4f7;
          font-size: 19px;
          line-height: 1.35;
        }

        .detail-badges {
          display: flex;
          flex-wrap: wrap;
          gap: 7px;
          margin-top: 13px;
        }

        .detail-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          margin-top: 20px;
        }

        .detail-field {
          padding: 11px;
          border: 1px solid #142f42;
          border-radius: 7px;
          background: #081521;
        }

        .detail-label {
          color: #56748a;
          font-size: 8px;
          font-weight: 700;
          letter-spacing: 0.1em;
          text-transform: uppercase;
        }

        .detail-value {
          margin-top: 5px;
          color: #c9d8df;
          font-size: 11px;
          word-break: break-word;
        }

        .detail-section {
          margin-top: 18px;
        }

        .detail-section-title {
          color: #6f8ba0;
          font-size: 9px;
          font-weight: 700;
          letter-spacing: 0.11em;
          text-transform: uppercase;
          margin-bottom: 8px;
        }

        .detail-text {
          color: #94aaba;
          font-size: 11px;
          line-height: 1.65;
          white-space: pre-wrap;
        }

        .detail-actions {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          margin-top: 20px;
          padding-top: 16px;
          border-top: 1px solid #142f42;
        }

        .action-button {
          border: 1px solid #1a4650;
          border-radius: 7px;
          background: #0b2b2c;
          color: #27d7a5;
          padding: 10px 13px;
          font-size: 10px;
          font-weight: 800;
          cursor: pointer;
        }

        .action-button:hover:not(:disabled) {
          background: #0e3937;
          border-color: #27d7a5;
        }

        .action-button.secondary {
          background: #0b1d2b;
          color: #9ab0c0;
          border-color: #1a3a4e;
        }

        .action-button.secondary:hover:not(:disabled) {
          color: #edf4f7;
          border-color: #58758b;
        }

        .action-button:disabled {
          opacity: 0.45;
          cursor: not-allowed;
        }

        .message {
          margin-bottom: 14px;
          padding: 11px 13px;
          border-radius: 7px;
          font-size: 11px;
        }

        .message.error {
          border: 1px solid #61242b;
          background: #32171b;
          color: #ff9a9a;
        }

        .message.success {
          border: 1px solid #245943;
          background: #112d24;
          color: #7fd8b7;
        }

        .empty-state {
          padding: 55px 20px;
          text-align: center;
          color: #607d94;
          font-size: 12px;
        }

        .empty-title {
          color: #27d7a5;
          font-size: 11px;
          font-weight: 800;
          letter-spacing: 0.12em;
          margin-bottom: 8px;
        }

        .loading {
          padding: 40px;
          text-align: center;
          color: #6e8ba0;
          font-size: 11px;
        }

        .incident-pagination {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 13px 14px;
          border-top: 1px solid #142f42;
          background: #081521;
          flex-wrap: wrap;
        }

        .incident-pagination-info {
          color: #607d94;
          font-size: 10px;
        }

        .incident-pagination-controls {
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .incident-page-button {
          min-width: 32px;
          height: 32px;
          border: 1px solid #19364a;
          border-radius: 7px;
          background: #091826;
          color: #8da5b5;
          font-size: 10px;
          font-weight: 700;
          cursor: pointer;
        }

        .incident-page-button:hover:not(:disabled),
        .incident-page-button.active {
          border-color: #27d7a5;
          background: #0b2a2b;
          color: #27d7a5;
        }

        .incident-page-button:disabled {
          opacity: 0.35;
          cursor: not-allowed;
        }

        .incident-page-button.prev-next {
          padding: 0 10px;
          display: inline-flex;
          align-items: center;
          gap: 4px;
        }

        .soc-modal-backdrop {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(4, 10, 18, 0.78);
          backdrop-filter: blur(6px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
          padding: 20px;
        }

        .soc-modal-box {
          background: #091826;
          border: 1px solid #1c3c54;
          border-radius: 12px;
          max-width: 520px;
          width: 100%;
          box-shadow: 0 20px 45px rgba(0, 0, 0, 0.6), 0 0 25px rgba(14, 165, 233, 0.1);
          overflow: hidden;
          animation: modalFadeIn 0.15s ease-out;
        }

        @keyframes modalFadeIn {
          from { opacity: 0; transform: scale(0.97); }
          to { opacity: 1; transform: scale(1); }
        }

        .soc-modal-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 18px 22px;
          border-bottom: 1px solid #142f42;
          background: #0b1f30;
        }

        .soc-modal-title {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 15px;
          font-weight: 800;
          color: #edf4f7;
          letter-spacing: 0.02em;
        }

        .soc-modal-close-btn {
          background: transparent;
          border: none;
          color: #628198;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 4px;
          border-radius: 6px;
        }

        .soc-modal-close-btn:hover {
          color: #edf4f7;
          background: #142f42;
        }

        .soc-modal-body {
          padding: 22px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .soc-modal-label {
          font-size: 10px;
          font-weight: 800;
          letter-spacing: 0.08em;
          color: #7291a7;
          text-transform: uppercase;
        }

        .soc-modal-select,
        .soc-modal-textarea {
          width: 100%;
          background: #06111b;
          border: 1px solid #16374e;
          border-radius: 8px;
          color: #edf4f7;
          font-size: 12px;
          padding: 10px 12px;
          outline: none;
          box-sizing: border-box;
          transition: border-color 0.15s;
        }

        .soc-modal-select:focus,
        .soc-modal-textarea:focus {
          border-color: #38bdf8;
        }

        .soc-modal-textarea {
          resize: vertical;
          min-height: 90px;
          line-height: 1.5;
        }

        .soc-modal-footer {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
          padding: 16px 22px;
          border-top: 1px solid #142f42;
          background: #071522;
        }

        /* SOC FRIENDLY INCIDENT DETAIL STYLES */
        .soc-detail-content {
          padding: 18px 20px 24px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .soc-detail-header {
          border-bottom: 1px solid #142f42;
          padding-bottom: 14px;
        }

        .soc-summary-card {
          background: linear-gradient(135deg, rgba(8, 28, 48, 0.75), rgba(7, 21, 34, 0.9));
          border: 1px solid #1e4663;
          border-left: 3px solid #38bdf8;
          border-radius: 8px;
          padding: 12px 14px;
        }

        .soc-summary-header {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 10px;
          font-weight: 800;
          letter-spacing: 0.08em;
          color: #38bdf8;
          text-transform: uppercase;
          margin-bottom: 6px;
        }

        .soc-summary-body {
          font-size: 13px;
          line-height: 1.5;
          color: #edf4f7;
          font-weight: 600;
        }

        .soc-risk-card {
          background: #081521;
          border: 1px solid #19364a;
          border-radius: 8px;
          padding: 12px 14px;
        }

        .soc-card-label {
          font-size: 9px;
          font-weight: 800;
          letter-spacing: 0.1em;
          color: #7291a7;
          text-transform: uppercase;
          margin-bottom: 4px;
        }

        .soc-card-text {
          font-size: 12px;
          color: #cbd5e1;
          line-height: 1.5;
        }

        .soc-section-card {
          background: #081521;
          border: 1px solid #142f42;
          border-radius: 8px;
          padding: 12px 14px;
        }

        .soc-section-header {
          display: flex;
          align-items: center;
          gap: 7px;
          font-size: 10px;
          font-weight: 800;
          letter-spacing: 0.08em;
          color: #8da6b9;
          text-transform: uppercase;
          margin-bottom: 10px;
          border-bottom: 1px solid #0f2738;
          padding-bottom: 6px;
        }

        .soc-assets-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }

        .soc-asset-item {
          display: flex;
          flex-direction: column;
          gap: 3px;
          background: #061019;
          padding: 8px 10px;
          border-radius: 6px;
          border: 1px solid #102638;
        }

        .asset-label {
          font-size: 9px;
          font-weight: 700;
          color: #5d7c92;
          text-transform: uppercase;
        }

        .asset-value {
          font-size: 11px;
          color: #edf4f7;
          word-break: break-all;
        }

        .soc-evidence-list {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .soc-evidence-item {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          font-size: 11.5px;
          color: #d1e2eb;
          line-height: 1.45;
        }

        .evidence-bullet {
          color: #facc15;
          font-size: 11px;
          margin-top: 1px;
        }

        .soc-grid-dual {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }

        .soc-small-card {
          background: #081521;
          border: 1px solid #142f42;
          border-radius: 8px;
          padding: 10px 12px;
        }

        .small-card-label {
          font-size: 9px;
          font-weight: 800;
          letter-spacing: 0.08em;
          color: #628198;
          text-transform: uppercase;
          display: block;
          margin-bottom: 5px;
        }

        .small-card-value {
          font-size: 12px;
          font-weight: 600;
          color: #edf4f7;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .mitre-tag {
          display: inline-block;
          font-size: 10px;
          font-weight: 800;
          font-family: monospace;
          background: rgba(56, 189, 248, 0.15);
          color: #38bdf8;
          border: 1px solid rgba(56, 189, 248, 0.3);
          border-radius: 4px;
          padding: 1px 6px;
          width: fit-content;
        }

        .soc-steps-list {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 7px;
        }

        .soc-step-item {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          font-size: 11.5px;
          color: #c9dce6;
          line-height: 1.45;
          background: #07131e;
          padding: 7px 10px;
          border-radius: 6px;
          border-left: 2px solid #27d7a5;
        }

        .step-num {
          font-weight: 800;
          color: #27d7a5;
          font-size: 11px;
        }

        .soc-action-toolbar {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          padding-top: 14px;
          border-top: 1px solid #142f42;
        }

        .soc-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 8px 12px;
          border-radius: 6px;
          font-size: 11px;
          font-weight: 700;
          cursor: pointer;
          border: 1px solid transparent;
          transition: all 0.15s ease;
        }

        .soc-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .soc-btn-primary {
          background: #0e3b56;
          border-color: #38bdf8;
          color: #38bdf8;
        }

        .soc-btn-primary:hover:not(:disabled) {
          background: #154c6d;
          color: #ffffff;
        }

        .soc-btn-ack {
          background: #0c3328;
          border-color: #27d7a5;
          color: #27d7a5;
        }

        .soc-btn-ack:hover:not(:disabled) {
          background: #124939;
          color: #ffffff;
        }

        .soc-btn-secondary {
          background: #0b1d2b;
          border-color: #1a3a4e;
          color: #9ab0c0;
        }

        .soc-btn-secondary:hover:not(:disabled) {
          background: #11283a;
          color: #edf4f7;
          border-color: #58758b;
        }

        .soc-btn-resolve {
          background: #112d24;
          border-color: #245943;
          color: #7fd8b7;
        }

        .soc-btn-resolve:hover:not(:disabled) {
          background: #174235;
          color: #ffffff;
        }

        .soc-btn-close {
          background: #251618;
          border-color: #5c272c;
          color: #ff9a9a;
        }

        .soc-btn-close:hover:not(:disabled) {
          background: #3a1f22;
          color: #ffffff;
        }

        .soc-raw-trace-details {
          background: #050c14;
          border: 1px solid #122838;
          border-radius: 8px;
          overflow: hidden;
          margin-top: 4px;
        }

        .soc-trace-summary {
          padding: 10px 14px;
          font-size: 11px;
          font-weight: 700;
          color: #7291a7;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: space-between;
          background: #081521;
          user-select: none;
        }

        .soc-trace-summary:hover {
          color: #38bdf8;
        }

        .soc-trace-hint {
          font-size: 10px;
          color: #4a677d;
          font-weight: normal;
        }

        .soc-raw-trace-body {
          padding: 12px 14px;
          border-top: 1px solid #102636;
        }

        .soc-trace-toolbar {
          display: flex;
          justify-content: flex-end;
          margin-bottom: 8px;
        }

        .soc-copy-btn {
          background: #0e2233;
          border: 1px solid #1f3e58;
          color: #7dd3fc;
          font-size: 10px;
          font-weight: 700;
          padding: 4px 10px;
          border-radius: 4px;
          cursor: pointer;
        }

        .soc-copy-btn:hover {
          background: #14354f;
          color: #ffffff;
        }

        .soc-raw-json-block {
          background: #03080d;
          border: 1px solid #0d1e2b;
          border-radius: 6px;
          padding: 10px;
          color: #94a3b8;
          font-family: monospace;
          font-size: 10.5px;
          line-height: 1.45;
          max-height: 260px;
          overflow: auto;
          white-space: pre;
          margin: 0;
        }

        .soc-raw-description {
          margin-top: 10px;
          padding: 8px 10px;
          background: #07131e;
          border-radius: 6px;
          border: 1px solid #0f2738;
          font-size: 11px;
          color: #8fa5b5;
        }

        .soc-raw-description p {
          margin: 4px 0 0;
          color: #cbd5e1;
          line-height: 1.45;
        }

        @media (max-width: 1050px) {
          .incident-layout {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 760px) {
          .incident-kpis {
            grid-template-columns: 1fr 1fr;
          }

          .detail-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>

      <div className="incident-header">
        <div className="incident-eyebrow">
          SOC PLATFORM / RESPONSE
        </div>

        <h1 className="incident-title">
          Security Incidents
        </h1>

        <p className="incident-description">
          Manage active incidents, escalation status,
          investigation history, and resolution.
        </p>
      </div>

      <div className="incident-kpis">
        <div className="incident-kpi">
          <div className="incident-kpi-label">
            Total Incidents
          </div>
          <div className="incident-kpi-value">
            {summary.total}
          </div>
        </div>

        <div className="incident-kpi">
          <div className="incident-kpi-label">
            Active
          </div>
          <div className="incident-kpi-value">
            {summary.active}
          </div>
        </div>

        <div className="incident-kpi">
          <div className="incident-kpi-label">
            Critical
          </div>
          <div className="incident-kpi-value">
            {summary.critical}
          </div>
        </div>

        <div className="incident-kpi">
          <div className="incident-kpi-label">
            Closed
          </div>
          <div className="incident-kpi-value">
            {summary.closed}
          </div>
        </div>
      </div>

      {error && (
        <div className="message error">
          {error}
        </div>
      )}

      {actionMessage && (
        <div className="message success">
          {actionMessage}
        </div>
      )}

      <div className="incident-toolbar">
        <input
          className="incident-search"
          value={search}
          onChange={(event) =>
            setSearch(event.target.value)
          }
          placeholder="Search incident ID, alert ID, title, or description..."
        />

        <button
          className="incident-refresh"
          type="button"
          onClick={() => void loadIncidents()}
          disabled={loading}
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>

        <div className="incident-tabs">
          {STATUS_ORDER.map((status) => (
            <button
              key={status}
              type="button"
              className={`incident-tab ${
                statusFilter === status
                  ? "active"
                  : ""
              }`}
              onClick={() =>
                setStatusFilter(status)
              }
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      <div className="incident-layout">
        <div className="incident-card">
          <div className="incident-card-header">
            <div className="incident-card-title">
              Incident Queue
            </div>

            <div className="incident-count">
              {total} record{total === 1 ? "" : "s"}
            </div>
          </div>

          {loading ? (
            <div className="loading">
              Loading incidents from ZUKA backend...
            </div>
          ) : incidents.length === 0 ? (
            <div className="empty-state">
              <div className="empty-title">
                NO INCIDENTS FOUND
              </div>
              No incidents match the current filters.
            </div>
          ) : (
            <div className="incident-table-wrap">
              <table className="incident-table">
                <thead>
                  <tr>
                    <th>Incident</th>
                    <th>Severity</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Assigned Analyst</th>
                    <th>Escalation</th>
                    <th>Created</th>
                  </tr>
                </thead>

                <tbody>
                  {incidents.map((incident) => (
                    <tr
                      key={incident.incident_id}
                      className={`incident-row ${
                        selectedIncident?.incident_id ===
                        incident.incident_id
                          ? "selected"
                          : ""
                      }`}
                      onClick={() =>
                        handleSelectIncident(
                          incident,
                        )
                      }
                    >
                      <td>
                        <div className="incident-id">
                          {incident.incident_id}
                        </div>

                        <div className="incident-name">
                          {incident.title}
                        </div>
                      </td>

                      <td>
                        <span
                          className={`badge ${severityClass(
                            incident.severity,
                          )}`}
                        >
                          {incident.severity}
                        </span>
                      </td>

                      <td>
                        <span
                          className={`badge ${severityClass(
                            incident.priority,
                          )}`}
                        >
                          {incident.priority}
                        </span>
                      </td>

                      <td>
                        <span
                          className={`badge ${statusClass(
                            incident.status,
                          )}`}
                        >
                          {incident.status}
                        </span>
                      </td>

                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span
                            style={{
                              fontSize: "11px",
                              fontWeight: 700,
                              color:
                                incident.status.toUpperCase() !== "OPEN" || incident.assigned_to_id
                                  ? "#27d7a5"
                                  : "#64748b",
                            }}
                          >
                            {incident.assigned_analyst ||
                              (incident.assigned_to_username
                                ? `${incident.assigned_to_username} (Assigned)`
                                : incident.status.toUpperCase() !== "OPEN"
                                ? "karthik admin (Assigned)"
                                : "Unassigned")}
                          </span>
                        </div>
                      </td>

                      <td>
                        L{incident.escalation_level}
                      </td>

                      <td>
                        {formatShortDateTime(
                          incident.created_at,
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {!loading && total > 0 && (
            <div className="incident-pagination">
              <div className="incident-pagination-info">
                Showing <strong style={{ color: "#d9e8ed" }}>{(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)}</strong> of <strong style={{ color: "#d9e8ed" }}>{total}</strong> incidents
              </div>
              <div className="incident-pagination-controls">
                <button
                  type="button"
                  className="incident-page-button prev-next"
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                  disabled={page <= 1 || loading}
                  title="Previous Page"
                >
                  <ChevronLeft size={14} />
                  <span>Prev</span>
                </button>
                {Array.from({ length: Math.min(Math.ceil(total / pageSize), 5) }, (_, index) => {
                  const totalPages = Math.ceil(total / pageSize);
                  const startPage = Math.min(Math.max(1, page - 2), Math.max(1, totalPages - 4));
                  const pageNumber = startPage + index;
                  if (pageNumber > totalPages) return null;
                  return (
                    <button
                      key={pageNumber}
                      type="button"
                      className={`incident-page-button ${page === pageNumber ? "active" : ""}`}
                      onClick={() => setPage(pageNumber)}
                    >
                      {pageNumber}
                    </button>
                  );
                })}
                <button
                  type="button"
                  className="incident-page-button prev-next"
                  onClick={() => setPage((current) => Math.min(Math.ceil(total / pageSize), current + 1))}
                  disabled={page >= Math.ceil(total / pageSize) || loading}
                  title="Next Page"
                >
                  <span>Next</span>
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="incident-card incident-detail">
          <div className="incident-card-header" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div className="incident-card-title">
              Incident Detail
            </div>
            {selectedIncident && (
              <button
                type="button"
                className="incident-detail-close-btn"
                onClick={() => setSelectedIncident(null)}
                title="Close Incident Inspection"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                  padding: "5px 10px",
                  borderRadius: 6,
                  border: "1px solid #1f3b52",
                  background: "rgba(15, 23, 42, 0.75)",
                  color: "#94a3b8",
                  cursor: "pointer",
                  fontSize: 11,
                  fontWeight: 600,
                  transition: "all 0.15s ease",
                }}
              >
                <X size={14} />
                <span>Close</span>
              </button>
            )}
          </div>

          {detailLoading ? (
            <div className="loading">
              Loading incident details...
            </div>
          ) : !selectedIncident ? (
            <div className="empty-state">
              <div className="empty-title">
                SELECT AN INCIDENT
              </div>
              Select an incident from the queue
              to inspect its details and available
              SOC actions.
            </div>
          ) : (
            <div className="soc-detail-content">
              {/* HEADER: ID, Title, Badges, Timestamp */}
              <div className="soc-detail-header">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                  <div className="detail-id" style={{ fontSize: 13, fontWeight: 800, color: "#38bdf8", letterSpacing: "0.04em" }}>
                    {selectedIncident.incident_id}
                  </div>
                  <span style={{ fontSize: 11, color: "#64748b" }}>
                    {formatShortDateTime(selectedIncident.created_at)}
                  </span>
                </div>

                <h2 className="detail-title" style={{ margin: "8px 0 10px", fontSize: 18, color: "#edf4f7" }}>
                  {selectedIncident.title}
                </h2>

                <div className="detail-badges">
                  <span className={`badge ${severityClass(selectedIncident.severity)}`}>
                    {selectedIncident.severity}
                  </span>
                  <span className={`badge ${severityClass(selectedIncident.priority)}`}>
                    PRIORITY {selectedIncident.priority}
                  </span>
                  <span className={`badge ${statusClass(selectedIncident.status)}`}>
                    {selectedIncident.status}
                  </span>
                  <span className="badge" style={{ background: "#0f2334", borderColor: "#1e3d54", color: "#7dd3fc" }}>
                    L{selectedIncident.escalation_level} (Escalations: {selectedIncident.escalation_count})
                  </span>
                </div>
              </div>

              {formattedDetails && (
                <>
                  {/* ONE-LINE EXECUTIVE SUMMARY (MAX 25 WORDS) */}
                  <div className="soc-summary-card">
                    <div className="soc-summary-header">
                      <Activity size={14} />
                      <span>One-Line Summary</span>
                    </div>
                    <div className="soc-summary-body">
                      {formattedDetails.summary}
                    </div>
                  </div>

                  {/* WHY IT MATTERS (1-2 LINES) */}
                  <div className="soc-risk-card">
                    <div className="soc-card-label">Why It Matters</div>
                    <div className="soc-card-text">
                      {formattedDetails.whyItMatters}
                    </div>
                  </div>

                  {/* AFFECTED ASSETS */}
                  <div className="soc-section-card">
                    <div className="soc-section-header">
                      <Shield size={14} style={{ color: "#27d7a5" }} />
                      <span>Affected Assets</span>
                    </div>
                    <div className="soc-assets-grid">
                      <div className="soc-asset-item">
                        <span className="asset-label">Source Host / IP</span>
                        <span className="asset-value" style={{ fontFamily: "monospace", color: "#38bdf8" }}>
                          {formattedDetails.affectedAssets.source}
                        </span>
                      </div>
                      <div className="soc-asset-item">
                        <span className="asset-label">Target Host / IP</span>
                        <span className="asset-value" style={{ fontFamily: "monospace", color: "#f87171" }}>
                          {formattedDetails.affectedAssets.target}
                        </span>
                      </div>
                      <div className="soc-asset-item">
                        <span className="asset-label">Protocol / Service</span>
                        <span className="asset-value" style={{ fontWeight: 600 }}>
                          {formattedDetails.affectedAssets.service}
                        </span>
                      </div>
                      <div className="soc-asset-item">
                        <span className="asset-label">Assigned Analyst</span>
                        <span className="asset-value" style={{ color: "#27d7a5", fontWeight: 600 }}>
                          {formattedDetails.affectedAssets.assignedAnalyst}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* KEY EVIDENCE (3-5 BULLET POINTS DERIVED STRICTLY FROM REAL DB FIELDS) */}
                  <div className="soc-section-card">
                    <div className="soc-section-header">
                      <FileText size={14} style={{ color: "#facc15" }} />
                      <span>Key Evidence (Verified DB Telemetry)</span>
                    </div>
                    <ul className="soc-evidence-list">
                      {formattedDetails.keyEvidence.map((bullet, idx) => (
                        <li key={idx} className="soc-evidence-item">
                          <span className="evidence-bullet">▸</span>
                          <span>{bullet}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* DETECTION SOURCE & MITRE ATT&CK */}
                  <div className="soc-grid-dual">
                    <div className="soc-small-card">
                      <span className="small-card-label">Detection Source</span>
                      <div className="small-card-value">{formattedDetails.detectionSource}</div>
                    </div>

                    <div className="soc-small-card">
                      <span className="small-card-label">MITRE ATT&CK</span>
                      <div className="small-card-value">
                        <span className="mitre-tag">{formattedDetails.mitreAttack.code}</span>
                        <span style={{ fontSize: "11px", color: "#cbd5e1" }}>
                          {formattedDetails.mitreAttack.tactic} - {formattedDetails.mitreAttack.technique}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* RECOMMENDED NEXT STEPS (3-4 CONCISE SOC ACTIONS) */}
                  <div className="soc-section-card">
                    <div className="soc-section-header">
                      <CheckCircle2 size={14} style={{ color: "#34d399" }} />
                      <span>Recommended Next Steps</span>
                    </div>
                    <ol className="soc-steps-list">
                      {formattedDetails.recommendedNextSteps.map((step, idx) => (
                        <li key={idx} className="soc-step-item">
                          <span className="step-num">{idx + 1}.</span>
                          <span>{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                </>
              )}

              {/* TOP ACTION TOOLBAR */}
              <div className="soc-action-toolbar">
                {/* 1. START INVESTIGATION / INVESTIGATE */}
                {selectedIncident.status.toUpperCase() === "OPEN" && (
                  <>
                    <button
                      type="button"
                      className="soc-btn soc-btn-disabled"
                      style={{ opacity: 0.6, cursor: "not-allowed", border: "1px dashed #64748b" }}
                      disabled={true}
                      title="Alert must be acknowledged in Alert Center before starting investigation"
                    >
                      <Search size={13} style={{ color: "#94a3b8" }} />
                      <span>Start Investigation (Awaiting Alert Ack)</span>
                    </button>
                    {selectedIncident.alert_id && (
                      <button
                        type="button"
                        className="soc-btn soc-btn-secondary"
                        style={{ borderColor: "#19d39d", color: "#19d39d" }}
                        onClick={() =>
                          navigate(`/alerts?search=${encodeURIComponent(selectedIncident.alert_id!)}`)
                        }
                        title="Go to Alert Center to inspect and acknowledge this alert"
                      >
                        <AlertTriangle size={13} />
                        <span>Acknowledge in Alert Center ↗</span>
                      </button>
                    )}
                  </>
                )}

                {selectedIncident.status.toUpperCase() === "ACKNOWLEDGED" && (
                  <button
                    type="button"
                    className="soc-btn soc-btn-primary"
                    onClick={async () => {
                      try {
                        setActionLoading(true);
                        setError(null);
                        const updated = await updateIncidentStatus(
                          selectedIncident.incident_id,
                          { status: "INVESTIGATING" },
                        );
                        setSelectedIncident(updated);
                        setIncidents((current) =>
                          current.map((item) =>
                            item.incident_id === updated.incident_id ? updated : item,
                          ),
                        );
                        navigate(
                          `/investigation?incident_id=${encodeURIComponent(
                            updated.incident_id,
                          )}`,
                        );
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "Failed to start investigation");
                      } finally {
                        setActionLoading(false);
                      }
                    }}
                    disabled={actionLoading}
                    title="Start forensic investigation for this incident"
                  >
                    <Search size={13} />
                    <span>Start Investigation</span>
                  </button>
                )}

                {selectedIncident.status.toUpperCase() === "INVESTIGATING" && (
                  <>
                    <button
                      type="button"
                      className="soc-btn soc-btn-primary"
                      onClick={() =>
                        navigate(
                          `/investigation?incident_id=${encodeURIComponent(
                            selectedIncident.incident_id,
                          )}`,
                        )
                      }
                      title="Open investigation department to conduct forensic analysis"
                    >
                      <Search size={13} />
                      <span>Investigate</span>
                    </button>

                    {!isInvestigationCompleted && (
                      <button
                        type="button"
                        className="soc-btn soc-btn-secondary"
                        style={{ borderColor: "rgba(239, 68, 68, 0.4)", color: "#f87171" }}
                        onClick={() =>
                          navigate(
                            `/defense?case_id=${encodeURIComponent(
                              selectedIncident.incident_id,
                            )}`,
                          )
                        }
                        title="Triage threat telemetry and apply containment in Defense Department"
                      >
                        <ShieldAlert size={13} />
                        <span>Defense Department</span>
                      </button>
                    )}
                  </>
                )}

                {["RESOLVED", "CLOSED"].includes(selectedIncident.status.toUpperCase()) && (
                  <button
                    type="button"
                    className="soc-btn soc-btn-secondary"
                    onClick={() =>
                      navigate(
                        `/investigation?incident_id=${encodeURIComponent(
                          selectedIncident.incident_id,
                        )}`,
                      )
                    }
                    title="Review completed forensic investigation report"
                  >
                    <Search size={13} />
                    <span>Investigate Findings</span>
                  </button>
                )}

                {/* 2. RESOLVE INCIDENT (ENABLED WHEN INVESTIGATION IS COMPLETED) */}
                {selectedIncident.status.toUpperCase() === "INVESTIGATING" && (
                  isInvestigationCompleted ? (
                    <button
                      type="button"
                      className="soc-btn soc-btn-resolve"
                      onClick={handleTransition}
                      disabled={actionLoading}
                      title="Resolve incident with completed investigation findings"
                    >
                      <CheckCircle2 size={13} />
                      <span>Resolve Incident</span>
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="soc-btn soc-btn-disabled"
                      onClick={() => setInvestigationIncompleteModalOpen(true)}
                      style={{ opacity: 0.65, cursor: "pointer", border: "1px dashed #64748b" }}
                      title="Forensic investigation must be completed with analyst conclusion before resolution"
                    >
                      <CheckCircle2 size={13} style={{ color: "#94a3b8" }} />
                      <span>Resolve Incident (Awaiting Investigation)</span>
                    </button>
                  )
                )}

                {/* 3. CLOSE INCIDENT */}
                {selectedIncident.status.toUpperCase() === "RESOLVED" && (
                  <button
                    type="button"
                    className="soc-btn soc-btn-close"
                    onClick={() => {
                      setClosingSummary(selectedIncident.resolution_summary || "");
                      setCloseModalOpen(true);
                    }}
                    disabled={actionLoading}
                    title="Close incident"
                  >
                    <X size={13} />
                    <span>Close Incident</span>
                  </button>
                )}

                {/* 4. ADD NOTE */}
                <button
                  type="button"
                  className="soc-btn soc-btn-secondary"
                  onClick={() => {
                    setIncidentNoteText("");
                    setNoteModalOpen(true);
                  }}
                  title="Add analyst note with audit logging"
                >
                  <MessageSquare size={13} />
                  <span>Add Note</span>
                </button>

                {/* 5. ESCALATE (ONLY AVAILABLE WHEN INVESTIGATION IS IN PROGRESS) */}
                {!["CLOSED"].includes(selectedIncident.status.toUpperCase()) && (
                  selectedIncident.status.toUpperCase() === "INVESTIGATING" ? (
                    <button
                      type="button"
                      className="soc-btn soc-btn-secondary"
                      onClick={handleEscalate}
                      disabled={actionLoading}
                      title="Escalate incident priority and level"
                    >
                      <AlertTriangle size={13} />
                      <span>Escalate</span>
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="soc-btn soc-btn-disabled"
                      style={{ opacity: 0.5, cursor: "not-allowed", border: "1px dashed #475569" }}
                      disabled={true}
                      title="Investigation must be started before escalating this incident"
                    >
                      <AlertTriangle size={13} style={{ color: "#64748b" }} />
                      <span>Escalate (Investigation Required)</span>
                    </button>
                  )
                )}
              </div>

              {/* COLLAPSIBLE RAW LOG & JSON TRACE */}
              <details className="soc-raw-trace-details">
                <summary className="soc-trace-summary">
                  <span>Raw Incident Telemetry & JSON Trace</span>
                  <span className="soc-trace-hint">(Click to inspect full payload)</span>
                </summary>
                <div className="soc-raw-trace-body">
                  <div className="soc-trace-toolbar">
                    <button
                      type="button"
                      className="soc-copy-btn"
                      onClick={async () => {
                        try {
                          await navigator.clipboard.writeText(
                            JSON.stringify(selectedIncident, null, 2),
                          );
                          setCopied(true);
                          setTimeout(() => setCopied(false), 2000);
                        } catch {}
                      }}
                    >
                      {copied ? "Copied!" : "Copy Raw JSON"}
                    </button>
                  </div>
                  <pre className="soc-raw-json-block">
                    {JSON.stringify(selectedIncident, null, 2)}
                  </pre>
                  {selectedIncident.description && (
                    <div className="soc-raw-description">
                      <strong>Raw Sensor Description:</strong>
                      <p>{selectedIncident.description}</p>
                    </div>
                  )}
                  {selectedIncident.resolution_summary && (
                    <div className="soc-raw-description" style={{ marginTop: 8 }}>
                      <strong>Resolution Summary:</strong>
                      <p>{selectedIncident.resolution_summary}</p>
                    </div>
                  )}
                </div>
              </details>
            </div>
          )}
        </div>
      </div>

      {/* INVESTIGATION INCOMPLETE WARNING MODAL */}
      {investigationIncompleteModalOpen && selectedIncident && (
        <div
          className="soc-modal-backdrop"
          onClick={() => setInvestigationIncompleteModalOpen(false)}
        >
          <div
            className="soc-modal-box"
            style={{ maxWidth: 540 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              className="soc-modal-header"
              style={{ borderBottomColor: "rgba(234, 179, 8, 0.3)" }}
            >
              <div className="soc-modal-title">
                <AlertTriangle size={20} color="#eab308" />
                <span style={{ color: "#eab308", fontWeight: 700 }}>
                  Forensic Investigation Incomplete
                </span>
              </div>
              <button
                type="button"
                className="soc-modal-close-btn"
                onClick={() => setInvestigationIncompleteModalOpen(false)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="soc-modal-body">
              <div
                style={{
                  background: "rgba(234, 179, 8, 0.08)",
                  border: "1px solid rgba(234, 179, 8, 0.25)",
                  borderRadius: 8,
                  padding: "14px",
                  fontSize: 13,
                  color: "#fde047",
                  lineHeight: 1.5,
                }}
              >
                <strong>The investigation is not yet over.</strong> In accordance with standard SOC operating procedures, you must first complete the forensic investigation in the <strong>Investigation Department</strong> (including analyst notes and conclusion) and mark it as <strong>COMPLETED</strong> before this incident can be resolved.
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 10 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    background: "#0c1524",
                    padding: "10px 14px",
                    borderRadius: 8,
                    border: "1px solid #1e293b",
                  }}
                >
                  <span style={{ fontSize: 12, color: "#94a3b8" }}>Target Incident ID:</span>
                  <code style={{ fontSize: 12, color: "#38bdf8", fontWeight: 700 }}>
                    {selectedIncident.incident_id}
                  </code>
                </div>

                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    background: "#0c1524",
                    padding: "10px 14px",
                    borderRadius: 8,
                    border: "1px solid #1e293b",
                  }}
                >
                  <span style={{ fontSize: 12, color: "#94a3b8" }}>Investigation Status:</span>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: "#fb923c",
                      background: "rgba(251, 146, 60, 0.15)",
                      padding: "2px 8px",
                      borderRadius: 4,
                    }}
                  >
                    INCOMPLETE / NOT OVER
                  </span>
                </div>

                {investigationCaseId && (
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      background: "#0c1524",
                      padding: "10px 14px",
                      borderRadius: 8,
                      border: "1px solid #1e293b",
                    }}
                  >
                    <span style={{ fontSize: 12, color: "#94a3b8" }}>Investigation Case ID:</span>
                    <code style={{ fontSize: 12, color: "#a78bfa", fontWeight: 700 }}>
                      {investigationCaseId}
                    </code>
                  </div>
                )}
              </div>
            </div>
            <div className="soc-modal-footer">
              <button
                type="button"
                className="action-button secondary"
                onClick={() => setInvestigationIncompleteModalOpen(false)}
              >
                Dismiss
              </button>
              <button
                type="button"
                className="action-button"
                style={{
                  background: "rgba(239, 68, 68, 0.15)",
                  color: "#ef4444",
                  borderColor: "rgba(239, 68, 68, 0.4)",
                }}
                onClick={() => {
                  setInvestigationIncompleteModalOpen(false);
                  navigate(
                    `/defense?case_id=${encodeURIComponent(
                      selectedIncident.incident_id,
                    )}`,
                  );
                }}
              >
                Go to Defense Department ↗
              </button>
              <button
                type="button"
                className="action-button"
                style={{
                  background: "#0c3b5e",
                  color: "#38bdf8",
                  borderColor: "#38bdf8",
                }}
                onClick={() => {
                  setInvestigationIncompleteModalOpen(false);
                  navigate(
                    `/investigation?search=${encodeURIComponent(
                      selectedIncident.incident_id,
                    )}`,
                  );
                }}
              >
                Go to Investigation Department ↗
              </button>
            </div>
          </div>
        </div>
      )}

      {/* RESOLVE INCIDENT MODAL */}
      {resolveModalOpen && selectedIncident && (
        <div className="soc-modal-backdrop" onClick={() => setResolveModalOpen(false)}>
          <div className="soc-modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="soc-modal-header">
              <div className="soc-modal-title">
                <CheckCircle2 size={18} color="#38bdf8" />
                <span>Resolve Incident {selectedIncident.incident_id}</span>
              </div>
              <button
                type="button"
                className="soc-modal-close-btn"
                onClick={() => setResolveModalOpen(false)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="soc-modal-body">
              <div
                style={{
                  background: "rgba(56, 189, 248, 0.08)",
                  border: "1px solid rgba(56, 189, 248, 0.2)",
                  borderRadius: 8,
                  padding: "12px",
                  fontSize: 12,
                  color: "#93c5fd",
                }}
              >
                <strong>SOC Resolution Protocol:</strong> Forensic investigation has been verified as <strong>COMPLETED</strong> in the Investigation Department. Submitting will mark this incident as <strong>RESOLVED</strong> and synchronize the correlated detection alert.
              </div>

              <div>
                <div className="soc-modal-label" style={{ marginBottom: 6 }}>
                  Resolution Summary / Analyst Conclusion
                </div>
                <p style={{ fontSize: 11, color: "#7493a8", margin: "0 0 10px", lineHeight: 1.5 }}>
                  Document the containment actions, root cause findings, and conclusion of this forensic investigation.
                </p>
                <textarea
                  className="soc-modal-textarea"
                  value={resolutionSummary}
                  onChange={(e) => setResolutionSummary(e.target.value)}
                  placeholder="e.g., Threat actor traffic blocked at perimeter firewall. Affected endpoint isolated and cleaned. Forensic investigation completed."
                  rows={4}
                />
              </div>
            </div>
            <div className="soc-modal-footer">
              <button
                type="button"
                className="action-button secondary"
                onClick={() => setResolveModalOpen(false)}
                disabled={actionLoading}
              >
                Cancel
              </button>
              <button
                type="button"
                className="action-button"
                style={{ background: "#0c3b5e", color: "#38bdf8", borderColor: "#38bdf8" }}
                onClick={() => void handleConfirmResolve()}
                disabled={actionLoading}
              >
                {actionLoading ? "Resolving..." : "Submit & Resolve Incident"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* RESOLUTION SUCCESS POP-UP MESSAGE MODAL */}
      {resolvedSuccessModal && (
        <div className="soc-modal-backdrop" onClick={() => setResolvedSuccessModal(null)}>
          <div className="soc-modal-box" style={{ maxWidth: 540 }} onClick={(e) => e.stopPropagation()}>
            <div className="soc-modal-header" style={{ borderBottomColor: "rgba(39, 215, 165, 0.3)" }}>
              <div className="soc-modal-title">
                <CheckCircle2 size={20} color="#27d7a5" />
                <span style={{ color: "#27d7a5", fontWeight: 700 }}>Incident Resolved & Investigation Completed</span>
              </div>
              <button
                type="button"
                className="soc-modal-close-btn"
                onClick={() => setResolvedSuccessModal(null)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="soc-modal-body">
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#0c1524", padding: "10px 14px", borderRadius: 8, border: "1px solid #1e293b" }}>
                  <span style={{ fontSize: 12, color: "#94a3b8" }}>Target Incident ID:</span>
                  <code style={{ fontSize: 12, color: "#38bdf8", fontWeight: 700 }}>{resolvedSuccessModal.incident_id}</code>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#0c1524", padding: "10px 14px", borderRadius: 8, border: "1px solid #1e293b" }}>
                  <span style={{ fontSize: 12, color: "#94a3b8" }}>Incident Lifecycle Status:</span>
                  <span style={{ fontSize: 11, fontWeight: 700, color: "#27d7a5", background: "rgba(39, 215, 165, 0.15)", padding: "2px 8px", borderRadius: 4 }}>RESOLVED</span>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#0c1524", padding: "10px 14px", borderRadius: 8, border: "1px solid #1e293b" }}>
                  <span style={{ fontSize: 12, color: "#94a3b8" }}>Investigation Department:</span>
                  <span style={{ fontSize: 11, fontWeight: 700, color: "#a78bfa", background: "rgba(167, 139, 250, 0.15)", padding: "2px 8px", borderRadius: 4 }}>COMPLETED</span>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#0c1524", padding: "10px 14px", borderRadius: 8, border: "1px solid #1e293b" }}>
                  <span style={{ fontSize: 12, color: "#94a3b8" }}>Correlated Detection Alert:</span>
                  <span style={{ fontSize: 11, fontWeight: 700, color: "#27d7a5", background: "rgba(39, 215, 165, 0.15)", padding: "2px 8px", borderRadius: 4 }}>RESOLVED</span>
                </div>

                {resolvedSuccessModal.resolution_summary && (
                  <div style={{ background: "#0c1524", padding: "12px", borderRadius: 8, border: "1px solid #1e293b", marginTop: 4 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "#7493a8", marginBottom: 4 }}>RESOLUTION SUMMARY</div>
                    <p style={{ margin: 0, fontSize: 12, color: "#cbd5e1", lineHeight: 1.5 }}>{resolvedSuccessModal.resolution_summary}</p>
                  </div>
                )}
              </div>
            </div>
            <div className="soc-modal-footer">
              <button
                type="button"
                className="action-button secondary"
                onClick={() => {
                  const incId = resolvedSuccessModal.incident_id;
                  setResolvedSuccessModal(null);
                  navigate(`/investigation?search=${encodeURIComponent(incId)}`);
                }}
              >
                View in Investigation Department ↗
              </button>
              <button
                type="button"
                className="action-button"
                style={{ background: "#11382f", color: "#27d7a5", borderColor: "#27d7a5" }}
                onClick={() => setResolvedSuccessModal(null)}
              >
                Close & Return
              </button>
            </div>
          </div>
        </div>
      )}

      {closeModalOpen && selectedIncident && (
        <div className="soc-modal-backdrop" onClick={() => setCloseModalOpen(false)}>
          <div className="soc-modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="soc-modal-header">
              <div className="soc-modal-title">
                <CheckCircle2 size={18} color="#27d7a5" />
                <span>Close Incident {selectedIncident.incident_id}</span>
              </div>
              <button
                type="button"
                className="soc-modal-close-btn"
                onClick={() => setCloseModalOpen(false)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="soc-modal-body">
              <div>
                <div className="soc-modal-label" style={{ marginBottom: 6 }}>
                  Resolution Summary
                </div>
                <p style={{ fontSize: 11, color: "#7493a8", margin: "0 0 10px", lineHeight: 1.5 }}>
                  This resolution summary will be permanently archived with the incident case. It is pre-filled with the Analyst Conclusion from the SOC investigation.
                </p>
                <textarea
                  className="soc-modal-textarea"
                  value={closingSummary}
                  onChange={(e) => setClosingSummary(e.target.value)}
                  placeholder="Enter or refine the closing resolution summary..."
                  rows={4}
                />
              </div>
            </div>
            <div className="soc-modal-footer">
              <button
                type="button"
                className="action-button secondary"
                onClick={() => setCloseModalOpen(false)}
                disabled={actionLoading}
              >
                Cancel
              </button>
              <button
                type="button"
                className="action-button"
                style={{ background: "#11382f", color: "#27d7a5", borderColor: "#27d7a5" }}
                onClick={() => void handleConfirmClose()}
                disabled={actionLoading}
              >
                {actionLoading ? "Closing..." : "Confirm & Close Incident"}
              </button>
            </div>
          </div>
        </div>
      )}

      {escalateModalOpen && selectedIncident && (
        <div className="soc-modal-backdrop" onClick={() => setEscalateModalOpen(false)}>
          <div className="soc-modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="soc-modal-header">
              <div className="soc-modal-title">
                <AlertTriangle size={18} color="#ff8d8d" />
                <span>Escalate Incident {selectedIncident.incident_id}</span>
              </div>
              <button
                type="button"
                className="soc-modal-close-btn"
                onClick={() => setEscalateModalOpen(false)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="soc-modal-body">
              <div>
                <div className="soc-modal-label" style={{ marginBottom: 6 }}>
                  Escalation Reason
                </div>
                <select
                  className="soc-modal-select"
                  value={escalationReason}
                  onChange={(e) => setEscalationReason(e.target.value)}
                >
                  <option value="Critical Asset Compromised - Priority Escalation">Critical Asset Compromised - Priority Escalation</option>
                  <option value="Active Malicious Infiltration / Data Exfiltration">Active Malicious Infiltration / Data Exfiltration</option>
                  <option value="Senior Tier-3 / SOC Lead Intervention Required">Senior Tier-3 / SOC Lead Intervention Required</option>
                  <option value="SLA Breach - Uncontained Threat Actor">SLA Breach - Uncontained Threat Actor</option>
                  <option value="Suspected APT / Lateral Movement Activity">Suspected APT / Lateral Movement Activity</option>
                  <option value="Custom Analyst Rationale">Custom Analyst Rationale</option>
                </select>
              </div>

              <div>
                <div className="soc-modal-label" style={{ marginBottom: 6 }}>
                  Operational Notes & Justification (Optional)
                </div>
                <textarea
                  className="soc-modal-textarea"
                  value={escalationNotes}
                  onChange={(e) => setEscalationNotes(e.target.value)}
                  placeholder="Describe operational reasons, indicators of compromise, or specific escalation requirements..."
                  rows={3}
                />
              </div>

              <div style={{ background: "#141c28", padding: "10px 14px", borderRadius: 8, border: "1px solid #1f334a", fontSize: 11, color: "#8aa5b9" }}>
                <span>Escalation will set Priority to <strong style={{ color: "#ff8d8d" }}>CRITICAL</strong>, increment the escalation level, and log an audit event to PostgreSQL.</span>
              </div>
            </div>
            <div className="soc-modal-footer">
              <button
                type="button"
                className="action-button secondary"
                onClick={() => setEscalateModalOpen(false)}
                disabled={actionLoading}
              >
                Cancel
              </button>
              <button
                type="button"
                className="action-button"
                style={{ background: "#3d1419", color: "#ff8d8d", borderColor: "#7a2a33" }}
                onClick={() => void handleConfirmEscalate()}
                disabled={actionLoading}
              >
                {actionLoading ? "Escalating..." : "Confirm Escalation"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ADD ANALYST NOTE MODAL */}
      {noteModalOpen && selectedIncident && (
        <div
          className="soc-modal-backdrop"
          onClick={() => setNoteModalOpen(false)}
        >
          <div
            className="soc-modal-box"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: 520 }}
          >
            <div className="soc-modal-header">
              <div className="soc-modal-title">
                <MessageSquare size={18} color="#38bdf8" />
                <span>Add Analyst Note: {selectedIncident.incident_id}</span>
              </div>
              <button
                type="button"
                className="soc-modal-close-btn"
                onClick={() => setNoteModalOpen(false)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="soc-modal-body">
              <p style={{ margin: "0 0 10px", fontSize: "12px", color: "#94a3b8" }}>
                Document triage observations or containment actions. This note will be recorded in the audit trail and attached to this incident.
              </p>
              <textarea
                className="soc-modal-textarea"
                style={{
                  minHeight: "110px",
                  lineHeight: "1.5",
                }}
                placeholder="Enter analyst observation, containment note, or triage notes..."
                value={incidentNoteText}
                onChange={(e) => setIncidentNoteText(e.target.value)}
              />
            </div>
            <div className="soc-modal-footer">
              <button
                type="button"
                className="action-button secondary"
                onClick={() => setNoteModalOpen(false)}
                disabled={actionLoading}
              >
                Cancel
              </button>
              <button
                type="button"
                className="action-button"
                style={{ background: "#0e3b56", color: "#38bdf8", borderColor: "#38bdf8" }}
                onClick={() => void handleConfirmAddNote()}
                disabled={actionLoading || !incidentNoteText.trim()}
              >
                {actionLoading ? "Saving..." : "Save Note"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Incidents;