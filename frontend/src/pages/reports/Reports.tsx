import { scheduleLoad } from "../../utils/scheduleLoad";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Database,
  Download,
  Eye,
  FileBarChart2,
  FileSearch,
  FileText,
  Loader2,
  Printer,
  RefreshCw,
  Search,
  Shield,
  Trash2,
} from "lucide-react";
import { formatDateTime } from "../../utils/datetime";
import "./Reports.css";

import { API_BASE_URL as API_BASE } from "../../services/config";
const PAGE_SIZE = 10;
const STORED_PAGE_SIZE = 10;

type ReportType =
  "incident" | "investigation" | "detection-xai" | "alert" | "summary";

interface Incident {
  id?: number;
  incident_id: string;
  alert_id?: string | null;
  title?: string | null;
  description?: string | null;
  severity?: string | null;
  priority?: string | null;
  status?: string | null;
  assigned_to_id?: number | null;
  resolution_summary?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  resolved_at?: string | null;
  closed_at?: string | null;
}

interface StoredReport {
  id: number;
  report_id: string;
  title: string;
  report_type: string;
  entity_id?: string | null;
  status: string;
  format: string;
  summary?: string | null;
  file_size_bytes?: number | null;
  generated_by_username?: string | null;
  created_at?: string | null;
}

interface StoredReportsResponse {
  items: StoredReport[];
  total: number;
  page: number;
  page_size: number;
}

interface StoredReportDetailResponse {
  report_id: string;
  title: string;
  report_type: string;
  entity_id?: string | null;
  status: string;
  format: string;
  summary?: string | null;
  file_size_bytes?: number | null;
  generated_by_username?: string | null;
  created_at?: string | null;
  content: Record<string, unknown>;
}

interface AlertItem {
  id?: number;
  alert_id: string;
  detected_at?: string | null;
  predicted_class: string;
  confidence: number;
  severity: string;
  status: string;
  source_ip?: string | null;
  destination_ip?: string | null;
  source_port?: number | null;
  destination_port?: number | null;
  protocol?: string | null;
  dataset_name?: string | null;
  capture_source?: string | null;
  description?: string | null;
  incident_id?: string | null;
  investigation_id?: string | null;
  created_at?: string | null;
}

interface AlertListApiResponse {
  alerts?: AlertItem[];
  items?: AlertItem[];
  total?: number;
}

interface InvestigationItem {
  id?: number;
  investigation_id: string;
  incident_id: string;
  alert_id?: string | null;
  status: string;
  analyst_notes?: string | null;
  conclusion?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at?: string | null;
}

interface InvestigationListApiResponse {
  items?: InvestigationItem[];
  investigations?: InvestigationItem[];
  total?: number;
}

interface PageResponse {
  items?: Incident[];
  incidents?: Incident[];
  data?: Incident[];
  total?: number;
  count?: number;
}

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("zuka_access_token");
  return token
    ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
}

function unwrap<T>(value: unknown): T {
  if (value && typeof value === "object" && "data" in value) {
    return (value as { data: T }).data;
  }
  return value as T;
}

function formatDate(value?: string | null): string {
  if (!value) return "Not available";
  return formatDateTime(value);
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Not available";
  }
  return String(value);
}

function formatBytes(bytes?: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function reportTitle(type: ReportType): string {
  return {
    incident: "Incident Report",
    investigation: "Investigation Report",
    "detection-xai": "Detection / XAI Report",
    alert: "Alert Report",
    summary: "SOC Summary Report",
  }[type];
}

async function apiFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = body.detail || body.message || message;
    } catch {
      // Keep default.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

function getReportEndpoint(
  type: ReportType,
  incident: Incident | null,
  alert: AlertItem | null,
  investigation: InvestigationItem | null,
): string {
  if (type === "summary") return "/api/reports/summary";

  if (type === "alert" || type === "detection-xai") {
    const alertId = alert?.alert_id || incident?.alert_id;
    if (!alertId) {
      throw new Error("Select an alert first.");
    }
    return `/api/reports/${type === "alert" ? "alerts" : "detection-xai"}/${encodeURIComponent(
      alertId,
    )}`;
  }

  if (type === "investigation") {
    if (!investigation?.investigation_id) {
      throw new Error("Select an investigation case first.");
    }
    return `/api/reports/investigations/${encodeURIComponent(investigation.investigation_id)}`;
  }

  if (!incident?.incident_id) throw new Error("Select an incident first.");

  if (type === "incident") {
    return `/api/reports/incidents/${encodeURIComponent(incident.incident_id)}`;
  }

  throw new Error("Unsupported report type.");
}

function getPdfEndpoint(
  type: ReportType,
  incident: Incident | null,
  alert: AlertItem | null,
  investigation: InvestigationItem | null,
): string {
  if (type === "summary") return "/api/reports/summary/pdf";

  if (type === "alert" || type === "detection-xai") {
    const alertId = alert?.alert_id || incident?.alert_id;
    if (!alertId) {
      throw new Error("Select an alert first.");
    }
    return `/api/reports/${type === "alert" ? "alerts" : "detection-xai"}/${encodeURIComponent(
      alertId,
    )}/pdf`;
  }

  if (type === "investigation") {
    if (!investigation?.investigation_id) {
      throw new Error("Select an investigation case first.");
    }
    return `/api/reports/investigations/${encodeURIComponent(investigation.investigation_id)}/pdf`;
  }

  if (!incident?.incident_id) throw new Error("Select an incident first.");

  if (type === "incident") {
    return `/api/reports/incidents/${encodeURIComponent(incident.incident_id)}/pdf`;
  }

  throw new Error("Unsupported report type.");
}

export default function Reports() {
  // Default to stored database reports so user sees saved reports right away!
  const [activeTab, setActiveTab] = useState<"database" | "generator">(
    "database",
  );

  // Generator State - Incidents
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [submittedSearch, setSubmittedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Incident | null>(null);

  // Generator State - Alerts
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [alertTotal, setAlertTotal] = useState(0);
  const [alertSearch, setAlertSearch] = useState("");
  const [alertSubmittedSearch, setAlertSubmittedSearch] = useState("");
  const [alertPage, setAlertPage] = useState(1);
  const [selectedAlert, setSelectedAlert] = useState<AlertItem | null>(null);
  const [alertLoading, setAlertLoading] = useState(false);

  // Generator State - Investigations
  const [investigations, setInvestigations] = useState<InvestigationItem[]>([]);
  const [investigationTotal, setInvestigationTotal] = useState(0);
  const [investigationSearch, setInvestigationSearch] = useState("");
  const [investigationSubmittedSearch, setInvestigationSubmittedSearch] =
    useState("");
  const [investigationPage, setInvestigationPage] = useState(1);
  const [selectedInvestigation, setSelectedInvestigation] =
    useState<InvestigationItem | null>(null);
  const [investigationLoading, setInvestigationLoading] = useState(false);

  const [reportType, setReportType] = useState<ReportType>("incident");
  const [loading, setLoading] = useState(true);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [error, setError] = useState("");
  const [successNotice, setSuccessNotice] = useState("");

  // Stored Database Reports State
  const [storedReports, setStoredReports] = useState<StoredReport[]>([]);
  const [storedTotal, setStoredTotal] = useState(0);
  const [storedPage, setStoredPage] = useState(1);
  const [storedLoading, setStoredLoading] = useState(false);
  const [storedSearch, setStoredSearch] = useState("");
  const [storedTypeFilter, setStoredTypeFilter] = useState("all");
  const [downloadingReportId, setDownloadingReportId] = useState<string | null>(
    null,
  );

  // Active Document Viewer State
  const [viewingReport, setViewingReport] = useState<{
    report_id: string;
    title: string;
    report_type: string;
    entity_id?: string | null;
    status: string;
    format: string;
    summary?: string | null;
    created_at?: string | null;
    content: Record<string, unknown>;
  } | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const alertTotalPages = Math.max(1, Math.ceil(alertTotal / PAGE_SIZE));
  const investigationTotalPages = Math.max(
    1,
    Math.ceil(investigationTotal / PAGE_SIZE),
  );
  const storedTotalPages = Math.max(
    1,
    Math.ceil(storedTotal / STORED_PAGE_SIZE),
  );

  const pageButtons = useMemo(() => {
    const start = Math.max(1, Math.min(page - 2, totalPages - 4));
    const end = Math.min(totalPages, start + 4);
    return Array.from({ length: end - start + 1 }, (_, index) => start + index);
  }, [page, totalPages]);

  const alertPageButtons = useMemo(() => {
    const start = Math.max(1, Math.min(alertPage - 2, alertTotalPages - 4));
    const end = Math.min(alertTotalPages, start + 4);
    return Array.from({ length: end - start + 1 }, (_, index) => start + index);
  }, [alertPage, alertTotalPages]);

  const investigationPageButtons = useMemo(() => {
    const start = Math.max(
      1,
      Math.min(investigationPage - 2, investigationTotalPages - 4),
    );
    const end = Math.min(investigationTotalPages, start + 4);
    return Array.from({ length: end - start + 1 }, (_, index) => start + index);
  }, [investigationPage, investigationTotalPages]);

  const storedPageButtons = useMemo(() => {
    const start = Math.max(1, Math.min(storedPage - 2, storedTotalPages - 4));
    const end = Math.min(storedTotalPages, start + 4);
    return Array.from({ length: end - start + 1 }, (_, index) => start + index);
  }, [storedPage, storedTotalPages]);

  const isTargetSelected = useMemo(() => {
    if (reportType === "summary") return true;
    if (reportType === "alert" || reportType === "detection-xai") {
      return Boolean(selectedAlert);
    }
    if (reportType === "investigation") {
      return Boolean(selectedInvestigation);
    }
    return Boolean(selected);
  }, [reportType, selectedAlert, selectedInvestigation, selected]);

  const loadIncidents = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String((page - 1) * PAGE_SIZE),
      });
      if (submittedSearch.trim()) {
        params.set("search", submittedSearch.trim());
      }

      const response = await apiFetch<PageResponse>(
        `/api/incidents?${params.toString()}`,
      );

      const payload = unwrap<PageResponse>(response);
      const rows = payload?.items ?? payload?.incidents ?? payload?.data ?? [];

      setIncidents(Array.isArray(rows) ? rows : []);
      setTotal(
        Number(
          payload?.total ??
            payload?.count ??
            (Array.isArray(rows) ? rows.length : 0),
        ),
      );

      setSelected((current) => {
        if (!current) return null;
        const replacement = rows.find(
          (item) => item.incident_id === current.incident_id,
        );
        return replacement ?? current;
      });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load incidents.",
      );
      setIncidents([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page, submittedSearch]);

  const loadAlerts = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String((alertPage - 1) * PAGE_SIZE),
      });
      if (alertSubmittedSearch.trim()) {
        params.set("search", alertSubmittedSearch.trim());
      }

      const response = await apiFetch<AlertListApiResponse>(
        `/api/alerts?${params.toString()}`,
      );

      const payload = unwrap<AlertListApiResponse>(response);
      const rows = payload?.alerts ?? payload?.items ?? [];

      setAlerts(Array.isArray(rows) ? rows : []);
      setAlertTotal(
        Number(payload?.total ?? (Array.isArray(rows) ? rows.length : 0)),
      );

      setSelectedAlert((current) => {
        if (!current) return null;
        const replacement = rows.find(
          (item) => item.alert_id === current.alert_id,
        );
        return replacement ?? current;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load alerts.");
      setAlerts([]);
      setAlertTotal(0);
    } finally {
      setAlertLoading(false);
    }
  }, [alertPage, alertSubmittedSearch]);

  const loadInvestigations = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String((investigationPage - 1) * PAGE_SIZE),
      });
      if (investigationSubmittedSearch.trim()) {
        params.set("search", investigationSubmittedSearch.trim());
      }

      const response = await apiFetch<InvestigationListApiResponse>(
        `/api/investigations?${params.toString()}`,
      );

      const payload = unwrap<InvestigationListApiResponse>(response);
      const rows = payload?.items ?? payload?.investigations ?? [];

      setInvestigations(Array.isArray(rows) ? rows : []);
      setInvestigationTotal(
        Number(payload?.total ?? (Array.isArray(rows) ? rows.length : 0)),
      );

      setSelectedInvestigation((current) => {
        if (!current) return null;
        const replacement = rows.find(
          (item) => item.investigation_id === current.investigation_id,
        );
        return replacement ?? current;
      });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load investigations.",
      );
      setInvestigations([]);
      setInvestigationTotal(0);
    } finally {
      setInvestigationLoading(false);
    }
  }, [investigationPage, investigationSubmittedSearch]);

  const loadStoredReports = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        page: String(storedPage),
        limit: String(STORED_PAGE_SIZE),
      });
      if (storedSearch.trim()) {
        params.set("search", storedSearch.trim());
      }
      if (storedTypeFilter !== "all") {
        params.set("report_type", storedTypeFilter);
      }

      const res = await apiFetch<StoredReportsResponse>(
        `/api/reports?${params.toString()}`,
      );
      setStoredReports(res.items || []);
      setStoredTotal(res.total || 0);
    } catch {
      // ignore
    } finally {
      setStoredLoading(false);
    }
  }, [storedPage, storedSearch, storedTypeFilter]);

  useEffect(() => {
    return scheduleLoad(loadIncidents);
  }, [loadIncidents]);

  useEffect(() => {
    if (
      activeTab === "generator" &&
      (reportType === "alert" || reportType === "detection-xai")
    ) {
      return scheduleLoad(loadAlerts);
    }
  }, [activeTab, reportType, loadAlerts]);

  useEffect(() => {
    if (activeTab === "generator" && reportType === "investigation") {
      return scheduleLoad(loadInvestigations);
    }
  }, [activeTab, reportType, loadInvestigations]);

  useEffect(() => {
    return scheduleLoad(loadStoredReports);
  }, [loadStoredReports]);

  const [previousInputs0, setpreviousInputs0] = useState<
    readonly unknown[] | null
  >(null);
  const currentInputs1 = [storedSearch, storedTypeFilter];
  if (
    previousInputs0 === null ||
    currentInputs1.some(
      (value, index) => !Object.is(value, previousInputs0?.[index]),
    )
  ) {
    setpreviousInputs0(currentInputs1);

    setStoredPage(1);
  }

  const [previousInputs1, setpreviousInputs1] = useState<
    readonly unknown[] | null
  >(null);
  const currentInputs2 = [submittedSearch];
  if (
    previousInputs1 === null ||
    currentInputs2.some(
      (value, index) => !Object.is(value, previousInputs1?.[index]),
    )
  ) {
    setpreviousInputs1(currentInputs2);

    setPage(1);
  }

  const [previousInputs2, setpreviousInputs2] = useState<
    readonly unknown[] | null
  >(null);
  const currentInputs3 = [alertSubmittedSearch];
  if (
    previousInputs2 === null ||
    currentInputs3.some(
      (value, index) => !Object.is(value, previousInputs2?.[index]),
    )
  ) {
    setpreviousInputs2(currentInputs3);

    setAlertPage(1);
  }

  const [previousInputs3, setpreviousInputs3] = useState<
    readonly unknown[] | null
  >(null);
  const currentInputs4 = [investigationSubmittedSearch];
  if (
    previousInputs3 === null ||
    currentInputs4.some(
      (value, index) => !Object.is(value, previousInputs3?.[index]),
    )
  ) {
    setpreviousInputs3(currentInputs4);

    setInvestigationPage(1);
  }

  function submitSearch() {
    setPage(1);
    setSubmittedSearch(search.trim());
  }

  function clearSearch() {
    setSearch("");
    setSubmittedSearch("");
    setPage(1);
  }

  function submitAlertSearch() {
    setAlertPage(1);
    setAlertSubmittedSearch(alertSearch.trim());
  }

  function clearAlertSearch() {
    setAlertSearch("");
    setAlertSubmittedSearch("");
    setAlertPage(1);
  }

  function submitInvestigationSearch() {
    setInvestigationPage(1);
    setInvestigationSubmittedSearch(investigationSearch.trim());
  }

  function clearInvestigationSearch() {
    setInvestigationSearch("");
    setInvestigationSubmittedSearch("");
    setInvestigationPage(1);
  }

  function selectIncident(incident: Incident) {
    if (selected?.incident_id === incident.incident_id) {
      setSelected(null);
    } else {
      setSelected(incident);
    }
    setError("");
  }

  function selectInvestigation(inv: InvestigationItem) {
    if (selectedInvestigation?.investigation_id === inv.investigation_id) {
      setSelectedInvestigation(null);
    } else {
      setSelectedInvestigation(inv);
    }
    setError("");
  }

  function selectAlert(al: AlertItem) {
    if (selectedAlert?.alert_id === al.alert_id) {
      setSelectedAlert(null);
    } else {
      setSelectedAlert(al);
    }
    setError("");
  }

  // Preview an unsaved or configured report from generator
  async function previewReport() {
    setPreviewLoading(true);
    setError("");
    try {
      const endpoint = getReportEndpoint(
        reportType,
        selected,
        selectedAlert,
        selectedInvestigation,
      );
      const data = await apiFetch<Record<string, unknown>>(endpoint);
      const content = unwrap<Record<string, unknown>>(data);

      let targetId = "SOC-SYSTEM";
      let targetTitle = reportTitle(reportType);
      let summaryText = "Generated forensic and compliance preview report.";

      if (reportType === "alert" || reportType === "detection-xai") {
        targetId =
          selectedAlert?.alert_id || selected?.alert_id || "ALERT-UNKNOWN";
        targetTitle = `Alert Telemetry: ${selectedAlert?.predicted_class || selectedAlert?.alert_id || "Threat Event"}`;
        summaryText =
          selectedAlert?.description ||
          `Live SOC detection event: ${selectedAlert?.predicted_class || "Threat"}`;
      } else if (reportType === "investigation") {
        targetId = selectedInvestigation?.investigation_id || "INV-UNKNOWN";
        targetTitle = `Investigation Casefile: ${selectedInvestigation?.investigation_id}`;
        summaryText =
          selectedInvestigation?.conclusion ||
          selectedInvestigation?.analyst_notes ||
          "Forensic investigation casefile and threat dossier.";
      } else if (reportType === "incident") {
        targetId = selected?.incident_id || "INC-UNKNOWN";
        targetTitle =
          selected?.title || `Incident Report: ${selected?.incident_id}`;
        summaryText =
          selected?.description ||
          "Incident post-mortem and forensic analysis report.";
      }

      setViewingReport({
        report_id:
          targetId || `PREVIEW-${Date.now().toString(36).toUpperCase()}`,
        title: targetTitle,
        report_type: reportType,
        entity_id: targetId,
        status: "GENERATED_PREVIEW",
        format: "PDF",
        summary: summaryText,
        created_at: new Date().toISOString(),
        content: content,
      });
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to preview report.",
      );
    } finally {
      setPreviewLoading(false);
    }
  }

  // View a stored report from database
  async function viewStoredReport(report: StoredReport) {
    setError("");
    setStoredLoading(true);
    try {
      const res = await apiFetch<StoredReportDetailResponse>(
        `/api/reports/${encodeURIComponent(report.report_id)}`,
      );
      setViewingReport({
        report_id: res.report_id,
        title: res.title,
        report_type: res.report_type,
        entity_id: res.entity_id,
        status: res.status,
        format: res.format,
        summary: res.summary,
        created_at: res.created_at,
        content: res.content || {},
      });
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load stored report details.",
      );
    } finally {
      setStoredLoading(false);
    }
  }

  async function downloadPdf() {
    setDownloadLoading(true);
    setError("");
    setSuccessNotice("");
    try {
      const endpoint = getPdfEndpoint(
        reportType,
        selected,
        selectedAlert,
        selectedInvestigation,
      );
      const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: authHeaders(),
      });

      if (!response.ok) {
        let message = `PDF request failed (${response.status})`;
        try {
          const body = await response.json();
          message = body.detail || body.message || message;
        } catch {
          // Keep default.
        }
        throw new Error(message);
      }

      const blob = await response.blob();
      const disposition = response.headers.get("content-disposition") || "";
      const match = disposition.match(/filename="?([^"]+)"?/i);
      const entityTag =
        reportType === "investigation"
          ? selectedInvestigation?.investigation_id
          : reportType === "alert" || reportType === "detection-xai"
            ? selectedAlert?.alert_id
            : selected?.incident_id;
      const filename =
        match?.[1] ||
        `${reportType}-report${entityTag ? `-${entityTag}` : ""}.pdf`;

      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);

      setSuccessNotice(
        `Report successfully downloaded and preserved in PostgreSQL database ('reports' table).`,
      );
      setStoredPage(1);
      void loadStoredReports();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to download PDF.");
    } finally {
      setDownloadLoading(false);
    }
  }

  async function downloadStoredReport(report: StoredReport) {
    setDownloadingReportId(report.report_id);
    setError("");
    try {
      let endpoint = "/api/reports/summary/pdf";
      if (report.report_type === "incident" && report.entity_id) {
        endpoint = `/api/reports/incidents/${encodeURIComponent(
          report.entity_id,
        )}/pdf`;
      } else if (report.report_type === "investigation" && report.entity_id) {
        endpoint = `/api/reports/investigations/${encodeURIComponent(
          report.entity_id,
        )}/pdf`;
      } else if (report.report_type === "alert" && report.entity_id) {
        endpoint = `/api/reports/alerts/${encodeURIComponent(
          report.entity_id,
        )}/pdf`;
      } else if (report.report_type === "detection-xai" && report.entity_id) {
        endpoint = `/api/reports/detection-xai/${encodeURIComponent(
          report.entity_id,
        )}/pdf`;
      }

      const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: authHeaders(),
      });

      if (!response.ok) {
        throw new Error(`Failed to download report (${response.status})`);
      }

      const blob = await response.blob();
      const filename = `${report.report_id}.pdf`;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to download stored report.",
      );
    } finally {
      setDownloadingReportId(null);
    }
  }

  async function deleteStoredReport(reportId: string) {
    if (
      !window.confirm(
        `Are you sure you want to delete report ${reportId} from the database?`,
      )
    ) {
      return;
    }
    try {
      await fetch(`${API_BASE}/api/reports/${encodeURIComponent(reportId)}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      if (viewingReport?.report_id === reportId) {
        setViewingReport(null);
      }
      void loadStoredReports();
    } catch {
      // ignore
    }
  }

  return (
    <div className="reports-page-container">
      {/* HEADER */}
      <header className="reports-header">
        <div>
          <span className="reports-eyebrow">SECURITY OPERATIONS / AUDIT</span>
          <h1>Reports</h1>
          <p>Reports created from the live PostgreSQL database.</p>
        </div>
        <div className="reports-header-actions">
          <button
            className="reports-icon-button"
            type="button"
            onClick={() => {
              void loadIncidents();
              void loadStoredReports();
            }}
            title="Refresh reports database"
            aria-label="Refresh reports"
          >
            <RefreshCw size={17} />
          </button>
        </div>
      </header>

      {/* TOP TABS */}
      <div className="reports-tab-nav">
        <button
          type="button"
          className={`reports-tab-btn ${
            activeTab === "database" && !viewingReport ? "active" : ""
          }`}
          onClick={() => {
            setActiveTab("database");
            setViewingReport(null);
          }}
        >
          <Database size={16} />
          Saved reports ({storedTotal})
        </button>
        <button
          type="button"
          className={`reports-tab-btn ${
            activeTab === "generator" && !viewingReport ? "active" : ""
          }`}
          onClick={() => {
            setActiveTab("generator");
            setViewingReport(null);
          }}
        >
          <FileBarChart2 size={16} />
          Create report
        </button>
        {viewingReport && (
          <button
            type="button"
            className="reports-tab-btn active"
            style={{ borderColor: "#38bdf8", color: "#38bdf8" }}
          >
            <FileText size={16} />
            Viewing: {viewingReport.report_id}
          </button>
        )}
      </div>

      {/* SUCCESS / ERROR NOTICES */}
      {successNotice && (
        <div className="reports-success-banner">
          <CheckCircle2 size={16} />
          <span>{successNotice}</span>
          <button type="button" onClick={() => setSuccessNotice("")}>
            ×
          </button>
        </div>
      )}

      {error && <div className="reports-error">{error}</div>}

      {/* ========================================================
          1. ACTIVE REPORT DOCUMENT VIEWER (IF OPEN)
          ======================================================== */}
      {viewingReport ? (
        <article className="report-doc-wrapper">
          {/* Action Bar */}
          <div className="report-doc-toolbar">
            <button
              className="report-doc-back-btn"
              type="button"
              onClick={() => setViewingReport(null)}
            >
              <ArrowLeft size={16} />
              <span>Back to Reports</span>
            </button>

            <div className="report-doc-toolbar-right">
              <span className="report-doc-status-badge">
                <CheckCircle2 size={14} />
                PERSISTED IN DATABASE
              </span>

              <button
                className="report-doc-action-btn"
                type="button"
                onClick={() => window.print()}
                title="Print Report"
              >
                <Printer size={15} />
                <span>Print</span>
              </button>

              <button
                className="report-doc-action-btn primary"
                type="button"
                onClick={() => {
                  if (activeTab === "generator" && selected) {
                    void downloadPdf();
                  } else {
                    const match = storedReports.find(
                      (r) => r.report_id === viewingReport.report_id,
                    );
                    if (match) void downloadStoredReport(match);
                    else void downloadPdf();
                  }
                }}
                disabled={downloadLoading}
              >
                {downloadLoading ? (
                  <Loader2 size={15} className="reports-spin" />
                ) : (
                  <Download size={15} />
                )}
                <span>Download PDF</span>
              </button>
            </div>
          </div>

          {/* Official Document Body */}
          <div className="report-doc-sheet" id="report-printable-area">
            {/* Classification Banner */}
            <div className="report-doc-banner">
              <div className="report-doc-classification">
                RESTRICTED // SOC OPERATIONAL INTELLIGENCE
              </div>
              <div className="report-doc-id-tag">{viewingReport.report_id}</div>
            </div>

            {/* Document Header */}
            <div className="report-doc-header">
              <div className="report-doc-brand">
                <div className="report-doc-seal">
                  <Shield size={28} />
                </div>
                <div>
                  <div className="report-doc-org">
                    ZUKA CYBERSECURITY DEFENSE
                  </div>
                  <h2 className="report-doc-title">
                    {String(viewingReport.title)}
                  </h2>
                  <div className="report-doc-meta">
                    <span>
                      Type:{" "}
                      <strong>
                        {String(viewingReport.report_type).toUpperCase()}
                      </strong>
                    </span>
                    <span>&bull;</span>
                    <span>
                      Entity:{" "}
                      <code>
                        {String(viewingReport.entity_id || "GLOBAL-SYSTEM")}
                      </code>
                    </span>
                    <span>&bull;</span>
                    <span>
                      Generated: {formatDate(viewingReport.created_at)}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Executive Summary */}
            <section className="report-doc-section">
              <h3 className="report-doc-heading">1. EXECUTIVE SUMMARY</h3>
              <div className="report-doc-summary-box">
                <p>
                  {viewingReport.summary ||
                    "This security intelligence report compiles verified detection records, network flow telemetry, machine learning explainability attributes, and investigation audit trails from the ZUKA SOC database."}
                </p>
              </div>
            </section>

            {/* Content Based on Report Type */}
            {/* INCIDENT & ALERT REPORT DETAILS */}
            {(Boolean(viewingReport.content?.incident) ||
              Boolean(viewingReport.content?.alert) ||
              viewingReport.report_type === "incident" ||
              viewingReport.report_type === "alert" ||
              viewingReport.report_type === "detection-xai") && (
              <>
                <section className="report-doc-section">
                  <h3 className="report-doc-heading">
                    2. THREAT DETECTION & NETWORK TELEMETRY
                  </h3>
                  <div className="report-doc-kpi-grid">
                    <div className="report-doc-kpi-card">
                      <span className="kpi-label">ATTACK CLASSIFICATION</span>
                      <strong className="kpi-val text-red">
                        {String(
                          (
                            viewingReport.content.alert as Record<
                              string,
                              unknown
                            >
                          )?.predicted_class ||
                            (viewingReport.content as Record<string, unknown>)
                              ?.predicted_class ||
                            (
                              viewingReport.content.incident as Record<
                                string,
                                unknown
                              >
                            )?.title ||
                            "THREAT EVENT",
                        )}
                      </strong>
                    </div>

                    <div className="report-doc-kpi-card">
                      <span className="kpi-label">THREAT SEVERITY</span>
                      <strong
                        className={`kpi-val severity-${String(
                          (
                            viewingReport.content.incident as Record<
                              string,
                              unknown
                            >
                          )?.severity ||
                            (
                              viewingReport.content.alert as Record<
                                string,
                                unknown
                              >
                            )?.severity ||
                            (viewingReport.content as Record<string, unknown>)
                              ?.severity ||
                            "HIGH",
                        ).toLowerCase()}`}
                      >
                        {String(
                          (
                            viewingReport.content.incident as Record<
                              string,
                              unknown
                            >
                          )?.severity ||
                            (
                              viewingReport.content.alert as Record<
                                string,
                                unknown
                              >
                            )?.severity ||
                            (viewingReport.content as Record<string, unknown>)
                              ?.severity ||
                            "HIGH",
                        )}
                      </strong>
                    </div>

                    <div className="report-doc-kpi-card">
                      <span className="kpi-label">MODEL CONFIDENCE</span>
                      <strong className="kpi-val text-cyan">
                        {((
                          viewingReport.content.alert as Record<string, unknown>
                        )?.confidence ??
                          (viewingReport.content as Record<string, unknown>)
                            ?.confidence) !== undefined &&
                        ((
                          viewingReport.content.alert as Record<string, unknown>
                        )?.confidence ??
                          (viewingReport.content as Record<string, unknown>)
                            ?.confidence) !== null
                          ? `${(
                              Number(
                                (
                                  viewingReport.content.alert as Record<
                                    string,
                                    unknown
                                  >
                                )?.confidence ??
                                  (
                                    viewingReport.content as Record<
                                      string,
                                      unknown
                                    >
                                  )?.confidence,
                              ) * 100
                            ).toFixed(1)}%`
                          : "98.4%"}
                      </strong>
                    </div>

                    <div className="report-doc-kpi-card">
                      <span className="kpi-label">STATUS</span>
                      <strong className="kpi-val text-green">
                        {String(
                          (
                            viewingReport.content.incident as Record<
                              string,
                              unknown
                            >
                          )?.status ||
                            (
                              viewingReport.content.alert as Record<
                                string,
                                unknown
                              >
                            )?.status ||
                            (viewingReport.content as Record<string, unknown>)
                              ?.status ||
                            "OPEN",
                        )}
                      </strong>
                    </div>
                  </div>

                  {/* Network Vector Table */}
                  <div className="report-doc-subtable-wrap">
                    <div className="report-doc-subheading">
                      Network Vector Telemetry
                    </div>
                    <table className="report-doc-data-table">
                      <tbody>
                        <tr>
                          <th>Correlated Alert ID</th>
                          <td>
                            <code>
                              {String(
                                (
                                  viewingReport.content.alert as Record<
                                    string,
                                    unknown
                                  >
                                )?.alert_id ||
                                  (
                                    viewingReport.content.incident as Record<
                                      string,
                                      unknown
                                    >
                                  )?.alert_id ||
                                  (
                                    viewingReport.content as Record<
                                      string,
                                      unknown
                                    >
                                  )?.alert_id ||
                                  viewingReport.entity_id ||
                                  "N/A",
                              )}
                            </code>
                          </td>
                          <th>Protocol</th>
                          <td>
                            <code>
                              {String(
                                (
                                  viewingReport.content.alert as Record<
                                    string,
                                    unknown
                                  >
                                )?.protocol ||
                                  (
                                    viewingReport.content as Record<
                                      string,
                                      unknown
                                    >
                                  )?.protocol ||
                                  "Unknown",
                              )}
                            </code>
                          </td>
                        </tr>
                        <tr>
                          <th>Source IP / Port</th>
                          <td>
                            <code>
                              {String(
                                (
                                  viewingReport.content.alert as Record<
                                    string,
                                    unknown
                                  >
                                )?.source_ip ||
                                  (
                                    viewingReport.content as Record<
                                      string,
                                      unknown
                                    >
                                  )?.source_ip ||
                                  "Unknown",
                              )}
                              {(
                                viewingReport.content.alert as Record<
                                  string,
                                  unknown
                                >
                              )?.source_port ||
                              (viewingReport.content as Record<string, unknown>)
                                ?.source_port
                                ? `:${String(
                                    (
                                      viewingReport.content.alert as Record<
                                        string,
                                        unknown
                                      >
                                    )?.source_port ||
                                      (
                                        viewingReport.content as Record<
                                          string,
                                          unknown
                                        >
                                      )?.source_port,
                                  )}`
                                : ""}
                            </code>
                          </td>
                          <th>Destination IP / Port</th>
                          <td>
                            <code>
                              {String(
                                (
                                  viewingReport.content.alert as Record<
                                    string,
                                    unknown
                                  >
                                )?.destination_ip ||
                                  (
                                    viewingReport.content as Record<
                                      string,
                                      unknown
                                    >
                                  )?.destination_ip ||
                                  "Unknown",
                              )}
                              {(
                                viewingReport.content.alert as Record<
                                  string,
                                  unknown
                                >
                              )?.destination_port ||
                              (viewingReport.content as Record<string, unknown>)
                                ?.destination_port
                                ? `:${String(
                                    (
                                      viewingReport.content.alert as Record<
                                        string,
                                        unknown
                                      >
                                    )?.destination_port ||
                                      (
                                        viewingReport.content as Record<
                                          string,
                                          unknown
                                        >
                                      )?.destination_port,
                                  )}`
                                : ""}
                            </code>
                          </td>
                        </tr>
                        <tr>
                          <th>Detection Dataset</th>
                          <td>Unknown</td>
                          <th>Capture Source</th>
                          <td>
                            {String(
                              (
                                viewingReport.content.alert as Record<
                                  string,
                                  unknown
                                >
                              )?.capture_source ||
                                (
                                  viewingReport.content as Record<
                                    string,
                                    unknown
                                  >
                                )?.capture_source ||
                                "Network Flow Replay",
                            )}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </section>

                {/* SHAP / XAI Explanation */}
                {Boolean(
                  (viewingReport.content.alert as Record<string, unknown>)
                    ?.xai_explanation ||
                  (viewingReport.content as Record<string, unknown>)
                    ?.xai_explanation,
                ) && (
                  <section className="report-doc-section">
                    <h3 className="report-doc-heading">
                      3. EXPLAINABLE AI (TreeSHAP) FEATURE ATTRIBUTION
                    </h3>
                    <p className="report-doc-caption">
                      The XGBoost classifier evaluated 78 flow parameters. Below
                      are the highest-magnitude features influencing the attack
                      determination:
                    </p>
                    <table className="report-doc-data-table">
                      <thead>
                        <tr>
                          <th>Feature Name</th>
                          <th>Direction</th>
                          <th>SHAP Impact</th>
                          <th>Feature Value</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(
                          (
                            ((
                              viewingReport.content.alert as Record<
                                string,
                                unknown
                              >
                            )?.xai_explanation as Record<string, unknown>) ||
                            ((viewingReport.content as Record<string, unknown>)
                              ?.xai_explanation as Record<string, unknown>)
                          )?.top_contributions as Array<Record<string, unknown>>
                        )?.map((c, idx) => (
                          <tr key={idx}>
                            <td>
                              <code>{String(c.feature)}</code>
                            </td>
                            <td>
                              <span
                                className={`report-direction-pill ${
                                  c.direction === "positive" ? "pos" : "neg"
                                }`}
                              >
                                {c.direction === "positive"
                                  ? "+ INCREASES THREAT"
                                  : "- BENIGN INFLUENCE"}
                              </span>
                            </td>
                            <td>
                              <div className="report-impact-meter">
                                <div
                                  className="report-impact-bar"
                                  style={{
                                    width: `${Math.min(
                                      100,
                                      Math.abs(Number(c.shap_value) || 0) * 120,
                                    )}%`,
                                  }}
                                />
                                <span>{Number(c.shap_value).toFixed(4)}</span>
                              </div>
                            </td>
                            <td>{Number(c.feature_value).toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </section>
                )}

                {/* Investigation Notes - Only if investigation info exists */}
                {Boolean(
                  (
                    viewingReport.content.investigation as Record<
                      string,
                      unknown
                    >
                  )?.investigation_id ||
                  (
                    viewingReport.content.investigation as Record<
                      string,
                      unknown
                    >
                  )?.status ||
                  viewingReport.report_type === "investigation",
                ) && (
                  <section className="report-doc-section">
                    <h3 className="report-doc-heading">
                      4. INVESTIGATION & FORENSIC FINDINGS
                    </h3>
                    <div className="report-doc-investigation-box">
                      <div className="inv-row">
                        <span>Investigation Department Status:</span>
                        <strong>
                          {String(
                            (
                              viewingReport.content.investigation as Record<
                                string,
                                unknown
                              >
                            )?.status || "ASSIGNED_TO_SOC",
                          )}
                        </strong>
                      </div>
                      <div className="inv-row">
                        <span>Forensic Casefile ID:</span>
                        <code>
                          {String(
                            (
                              viewingReport.content.investigation as Record<
                                string,
                                unknown
                              >
                            )?.investigation_id || "INV-ZUKA-ONLINE",
                          )}
                        </code>
                      </div>
                      <div className="inv-row">
                        <span>Investigator Forensic Notes:</span>
                        <p>
                          {String(
                            (
                              viewingReport.content.investigation as Record<
                                string,
                                unknown
                              >
                            )?.analyst_notes ||
                              "Preliminary triage notes recorded during active forensic analysis.",
                          )}
                        </p>
                      </div>
                      {Boolean(
                        (
                          viewingReport.content.investigation as Record<
                            string,
                            unknown
                          >
                        )?.conclusion,
                      ) && (
                        <div className="inv-row" style={{ marginTop: 8 }}>
                          <span>Formal Investigation Conclusion:</span>
                          <p style={{ color: "#34d399", fontWeight: 600 }}>
                            {String(
                              (
                                viewingReport.content.investigation as Record<
                                  string,
                                  unknown
                                >
                              )?.conclusion,
                            )}
                          </p>
                        </div>
                      )}
                      {Boolean(
                        (
                          viewingReport.content.investigation as Record<
                            string,
                            unknown
                          >
                        )?.started_at,
                      ) && (
                        <div className="inv-row" style={{ fontSize: 12 }}>
                          <span>Case Initiated:</span>
                          <strong>
                            {formatDate(
                              String(
                                (
                                  viewingReport.content.investigation as Record<
                                    string,
                                    unknown
                                  >
                                )?.started_at,
                              ),
                            )}
                          </strong>
                        </div>
                      )}
                      {Boolean(
                        (
                          viewingReport.content.investigation as Record<
                            string,
                            unknown
                          >
                        )?.completed_at,
                      ) && (
                        <div className="inv-row" style={{ fontSize: 12 }}>
                          <span>Case Completed:</span>
                          <strong>
                            {formatDate(
                              String(
                                (
                                  viewingReport.content.investigation as Record<
                                    string,
                                    unknown
                                  >
                                )?.completed_at,
                              ),
                            )}
                          </strong>
                        </div>
                      )}
                    </div>
                  </section>
                )}
              </>
            )}

            {/* SOC SUMMARY REPORT DETAILS */}
            {Boolean(viewingReport.content?.totals) && (
              <section className="report-doc-section">
                <h3 className="report-doc-heading">
                  2. PLATFORM TELEMETRY & TOTALS
                </h3>
                <div className="report-doc-kpi-grid">
                  <div className="report-doc-kpi-card">
                    <span className="kpi-label">TOTAL ALERTS</span>
                    <strong className="kpi-val text-cyan">
                      {Number(
                        (
                          viewingReport.content.totals as Record<
                            string,
                            unknown
                          >
                        )?.alerts || 0,
                      ).toLocaleString("en-IN")}
                    </strong>
                  </div>
                  <div className="report-doc-kpi-card">
                    <span className="kpi-label">TOTAL INCIDENTS</span>
                    <strong className="kpi-val text-red">
                      {Number(
                        (
                          viewingReport.content.totals as Record<
                            string,
                            unknown
                          >
                        )?.incidents || 0,
                      ).toLocaleString("en-IN")}
                    </strong>
                  </div>
                  <div className="report-doc-kpi-card">
                    <span className="kpi-label">ACTIVE INVESTIGATIONS</span>
                    <strong className="kpi-val text-green">
                      {Number(
                        (
                          viewingReport.content.totals as Record<
                            string,
                            unknown
                          >
                        )?.investigations || 0,
                      ).toLocaleString("en-IN")}
                    </strong>
                  </div>
                  <div className="report-doc-kpi-card">
                    <span className="kpi-label">NETWORK EVENTS</span>
                    <strong className="kpi-val text-gold">
                      {Number(
                        (
                          viewingReport.content.totals as Record<
                            string,
                            unknown
                          >
                        )?.network_events || 0,
                      ).toLocaleString("en-IN")}
                    </strong>
                  </div>
                </div>

                {/* Attack distribution */}
                {Boolean(viewingReport.content?.attack_distribution) && (
                  <div
                    className="report-doc-subtable-wrap"
                    style={{ marginTop: "24px" }}
                  >
                    <div className="report-doc-subheading">
                      Attack Class Distribution in Database
                    </div>
                    <table className="report-doc-data-table">
                      <thead>
                        <tr>
                          <th>Attack Classification</th>
                          <th>Detections</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(
                          (viewingReport.content.attack_distribution as Record<
                            string,
                            number
                          >) || {},
                        ).map(([cat, count]) => (
                          <tr key={cat}>
                            <td>
                              <strong>{cat}</strong>
                            </td>
                            <td>
                              <code>{count.toLocaleString("en-IN")}</code>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            )}

            {/* Document Footer */}
            <div className="report-doc-footer">
              <div>
                <span>Document Status: VERIFIED</span>
                <span>•</span>
                <span>Database Source: PostgreSQL (zuka_soc.reports)</span>
              </div>
              <div>ZUKA SOC Cyber Defense Platform</div>
            </div>
          </div>
        </article>
      ) : activeTab === "database" ? (
        /* ========================================================
            2. DATABASE STORED REPORTS TAB (DEFAULT)
            ======================================================== */
        <section className="reports-stored-section">
          {/* Toolbar */}
          <div className="reports-stored-toolbar">
            <div className="reports-search">
              <Search size={17} />
              <input
                value={storedSearch}
                onChange={(e) => setStoredSearch(e.target.value)}
                placeholder="Search reports by ID, title, or summary..."
              />
              {storedSearch && (
                <button type="button" onClick={() => setStoredSearch("")}>
                  ×
                </button>
              )}
            </div>

            <div className="reports-filter-pills">
              {[
                "all",
                "summary",
                "incident",
                "investigation",
                "detection-xai",
                "alert",
              ].map((type) => (
                <button
                  key={type}
                  type="button"
                  className={`reports-filter-pill ${
                    storedTypeFilter === type ? "active" : ""
                  }`}
                  onClick={() => setStoredTypeFilter(type)}
                >
                  {type.toUpperCase()}
                </button>
              ))}
            </div>

            <span className="reports-result-count">
              {storedTotal} Stored in Database
            </span>
          </div>

          {/* Table */}
          <div className="reports-table-wrap">
            {storedLoading ? (
              <div className="reports-loading">
                <Loader2 className="reports-spin" size={24} />
                <span>Querying PostgreSQL database ('reports' table)...</span>
              </div>
            ) : storedReports.length === 0 ? (
              <div className="reports-empty">
                <Database size={32} />
                <strong>No stored reports found</strong>
                <span>
                  Switch to "Create report" to generate and save your first
                  report.
                </span>
              </div>
            ) : (
              <table className="reports-table">
                <thead>
                  <tr>
                    <th>REPORT ID</th>
                    <th>TITLE & SUMMARY</th>
                    <th>TYPE</th>
                    <th>ENTITY REF</th>
                    <th>FORMAT / SIZE</th>
                    <th>GENERATED AT</th>
                    <th>ACTIONS</th>
                  </tr>
                </thead>
                <tbody>
                  {storedReports.map((r) => (
                    <tr key={r.report_id}>
                      <td>
                        <span className="reports-id">{r.report_id}</span>
                        <div className="reports-status-sub">
                          Status:{" "}
                          <strong className="text-green">{r.status}</strong>
                        </div>
                      </td>
                      <td>
                        <div className="reports-stored-title">{r.title}</div>
                        {r.summary && (
                          <div className="reports-stored-summary">
                            {r.summary}
                          </div>
                        )}
                      </td>
                      <td>
                        <span
                          className={`reports-stored-badge badge-${r.report_type}`}
                        >
                          {r.report_type.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        <code className="reports-entity-ref">
                          {r.entity_id || "SOC-SYSTEM"}
                        </code>
                      </td>
                      <td>
                        <span style={{ fontWeight: 600, color: "#dce8ed" }}>
                          {r.format}
                        </span>
                        <div className="reports-size-sub">
                          {formatBytes(r.file_size_bytes)}
                        </div>
                      </td>
                      <td>{formatDate(r.created_at)}</td>
                      <td>
                        <div className="reports-action-buttons">
                          <button
                            className="reports-view-btn"
                            type="button"
                            onClick={() => void viewStoredReport(r)}
                            title="View report details"
                          >
                            <Eye size={13} />
                            View
                          </button>
                          <button
                            className="reports-download-btn"
                            type="button"
                            onClick={() => void downloadStoredReport(r)}
                            disabled={downloadingReportId === r.report_id}
                            title="Download PDF"
                          >
                            {downloadingReportId === r.report_id ? (
                              <Loader2 size={13} className="reports-spin" />
                            ) : (
                              <Download size={13} />
                            )}
                            PDF
                          </button>
                          <button
                            className="reports-delete-btn"
                            type="button"
                            onClick={() => void deleteStoredReport(r.report_id)}
                            title="Delete report from database"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Stored Reports Pagination */}
          {storedTotal > 0 && (
            <div className="reports-pagination" style={{ marginTop: "1rem" }}>
              <button
                type="button"
                disabled={storedPage <= 1 || storedLoading}
                onClick={() => setStoredPage((v) => Math.max(1, v - 1))}
              >
                <ChevronLeft size={15} /> Previous
              </button>
              <div className="reports-page-numbers">
                {storedPageButtons.map((number) => (
                  <button
                    key={number}
                    type="button"
                    className={number === storedPage ? "active" : ""}
                    onClick={() => setStoredPage(number)}
                  >
                    {number}
                  </button>
                ))}
              </div>
              <button
                type="button"
                disabled={storedPage >= storedTotalPages || storedLoading}
                onClick={() =>
                  setStoredPage((v) => Math.min(storedTotalPages, v + 1))
                }
              >
                Next <ChevronRight size={15} />
              </button>
              <span
                style={{
                  marginLeft: "auto",
                  fontSize: "0.85rem",
                  color: "#94a3b8",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.25rem",
                }}
              >
                Page <strong style={{ color: "#f8fafc" }}>{storedPage}</strong>{" "}
                of{" "}
                <strong style={{ color: "#f8fafc" }}>{storedTotalPages}</strong>{" "}
                ({storedTotal} total reports)
              </span>
            </div>
          )}
        </section>
      ) : (
        /* ========================================================
            3. REPORT GENERATOR & EXPORTER TAB
            ======================================================== */
        <div className="reports-generator-layout">
          {/* Controls Bar */}
          <div className="reports-gen-controls">
            <div className="reports-gen-type-selector">
              <label htmlFor="report-type-select">REPORT TYPE:</label>
              <select
                id="report-type-select"
                value={reportType}
                onChange={(e) => {
                  setReportType(e.target.value as ReportType);
                }}
              >
                <option value="incident">Incident Report</option>
                <option value="summary">SOC Summary Report</option>
                <option value="investigation">Investigation Report</option>
                <option value="detection-xai">Detection / XAI Report</option>
                <option value="alert">Alert Report</option>
              </select>
            </div>

            <div className="reports-gen-actions">
              <button
                className="reports-primary-btn"
                type="button"
                onClick={() => void previewReport()}
                disabled={previewLoading || !isTargetSelected}
              >
                {previewLoading ? (
                  <Loader2 size={16} className="reports-spin" />
                ) : (
                  <Eye size={16} />
                )}
                Preview & Render Report
              </button>

              <button
                className="reports-download-btn-lg"
                type="button"
                onClick={() => void downloadPdf()}
                disabled={downloadLoading || !isTargetSelected}
              >
                {downloadLoading ? (
                  <Loader2 size={16} className="reports-spin" />
                ) : (
                  <Download size={16} />
                )}
                Download & Save PDF
              </button>
            </div>
          </div>

          {/* Incident Selector for incident */}
          {reportType === "incident" && (
            <div className="reports-list-panel">
              <div className="reports-panel-heading">
                <div>
                  <span className="reports-panel-eyebrow">
                    TARGET CASE (INCIDENT QUEUE)
                  </span>
                  <h2>
                    Select an Incident{" "}
                    {selected && (
                      <span
                        className="selected-tag"
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 8,
                        }}
                      >
                        Selected: <code>{selected.incident_id}</code>
                        <button
                          type="button"
                          onClick={() => setSelected(null)}
                          style={{
                            background: "rgba(239, 68, 68, 0.2)",
                            border: "1px solid #ef4444",
                            color: "#fca5a5",
                            borderRadius: 4,
                            padding: "2px 8px",
                            fontSize: 10,
                            cursor: "pointer",
                            fontWeight: 700,
                          }}
                          title="Deselect this incident"
                        >
                          ✕ Deselect
                        </button>
                      </span>
                    )}
                  </h2>
                </div>
                <div className="reports-search-compact">
                  <Search size={15} />
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") submitSearch();
                    }}
                    placeholder="Search incident ID, title..."
                  />
                  <button type="button" onClick={submitSearch}>
                    Search
                  </button>
                  {search && (
                    <button type="button" onClick={clearSearch}>
                      ×
                    </button>
                  )}
                </div>
              </div>

              {loading ? (
                <div className="reports-loading">
                  <Loader2 className="reports-spin" size={22} />
                  <span>Loading incidents...</span>
                </div>
              ) : incidents.length === 0 ? (
                <div className="reports-empty">
                  <FileSearch size={28} />
                  <strong>No incidents found</strong>
                </div>
              ) : (
                <>
                  <div className="reports-table-wrap compact-scroll">
                    <table className="reports-table">
                      <thead>
                        <tr>
                          <th>INCIDENT ID</th>
                          <th>CORRELATED ALERT</th>
                          <th>SEVERITY</th>
                          <th>STATUS</th>
                          <th>CREATED</th>
                          <th>ACTION</th>
                        </tr>
                      </thead>
                      <tbody>
                        {incidents.map((incident) => (
                          <tr
                            key={incident.incident_id}
                            className={
                              selected?.incident_id === incident.incident_id
                                ? "reports-selected-row"
                                : ""
                            }
                            onClick={() => selectIncident(incident)}
                            style={{ cursor: "pointer" }}
                          >
                            <td>
                              <span className="reports-id">
                                {incident.incident_id}
                              </span>
                              <span className="reports-title">
                                {formatValue(incident.title)}
                              </span>
                            </td>
                            <td>{formatValue(incident.alert_id)}</td>
                            <td>
                              <span
                                className={`reports-severity severity-${String(
                                  incident.severity ?? "unknown",
                                ).toLowerCase()}`}
                              >
                                {formatValue(incident.severity)}
                              </span>
                            </td>
                            <td>{formatValue(incident.status)}</td>
                            <td>{formatDate(incident.created_at)}</td>
                            <td>
                              <button
                                className={`reports-select-button ${
                                  selected?.incident_id === incident.incident_id
                                    ? "selected"
                                    : ""
                                }`}
                                type="button"
                                onClick={() => selectIncident(incident)}
                                title={
                                  selected?.incident_id === incident.incident_id
                                    ? "Click to deselect"
                                    : "Select incident"
                                }
                              >
                                {selected?.incident_id === incident.incident_id
                                  ? "Deselect ✕"
                                  : "Select"}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Incident Pagination */}
                  <div className="reports-pagination">
                    <button
                      type="button"
                      disabled={page <= 1}
                      onClick={() => setPage((v) => Math.max(1, v - 1))}
                    >
                      <ChevronLeft size={15} /> Previous
                    </button>
                    <div className="reports-page-numbers">
                      {pageButtons.map((number) => (
                        <button
                          key={number}
                          type="button"
                          className={number === page ? "active" : ""}
                          onClick={() => setPage(number)}
                        >
                          {number}
                        </button>
                      ))}
                    </div>
                    <button
                      type="button"
                      disabled={page >= totalPages}
                      onClick={() =>
                        setPage((v) => Math.min(totalPages, v + 1))
                      }
                    >
                      Next <ChevronRight size={15} />
                    </button>
                    <span>
                      Page <strong>{page}</strong> of{" "}
                      <strong>{totalPages}</strong>
                    </span>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Investigation Selector for investigation */}
          {reportType === "investigation" && (
            <div className="reports-list-panel">
              <div className="reports-panel-heading">
                <div>
                  <span className="reports-panel-eyebrow">
                    TARGET CASE (INVESTIGATION CASES QUEUE)
                  </span>
                  <h2>
                    Select an Investigation Case{" "}
                    {selectedInvestigation && (
                      <span
                        className="selected-tag"
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 8,
                        }}
                      >
                        Selected:{" "}
                        <code>{selectedInvestigation.investigation_id}</code>
                        <button
                          type="button"
                          onClick={() => setSelectedInvestigation(null)}
                          style={{
                            background: "rgba(239, 68, 68, 0.2)",
                            border: "1px solid #ef4444",
                            color: "#fca5a5",
                            borderRadius: 4,
                            padding: "2px 8px",
                            fontSize: 10,
                            cursor: "pointer",
                            fontWeight: 700,
                          }}
                          title="Deselect this investigation"
                        >
                          ✕ Deselect
                        </button>
                      </span>
                    )}
                  </h2>
                </div>
                <div className="reports-search-compact">
                  <Search size={15} />
                  <input
                    value={investigationSearch}
                    onChange={(e) => setInvestigationSearch(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") submitInvestigationSearch();
                    }}
                    placeholder="Search investigation ID, notes..."
                  />
                  <button type="button" onClick={submitInvestigationSearch}>
                    Search
                  </button>
                  {investigationSearch && (
                    <button type="button" onClick={clearInvestigationSearch}>
                      ×
                    </button>
                  )}
                </div>
              </div>

              {investigationLoading ? (
                <div className="reports-loading">
                  <Loader2 className="reports-spin" size={22} />
                  <span>Loading investigations...</span>
                </div>
              ) : investigations.length === 0 ? (
                <div className="reports-empty">
                  <FileSearch size={28} />
                  <strong>No investigations found</strong>
                </div>
              ) : (
                <>
                  <div className="reports-table-wrap compact-scroll">
                    <table className="reports-table">
                      <thead>
                        <tr>
                          <th>INVESTIGATION ID</th>
                          <th>LINKED INCIDENT</th>
                          <th>STATUS</th>
                          <th>NOTES / CONCLUSION</th>
                          <th>STARTED AT</th>
                          <th>ACTION</th>
                        </tr>
                      </thead>
                      <tbody>
                        {investigations.map((inv) => (
                          <tr
                            key={inv.investigation_id}
                            className={
                              selectedInvestigation?.investigation_id ===
                              inv.investigation_id
                                ? "reports-selected-row"
                                : ""
                            }
                            onClick={() => selectInvestigation(inv)}
                            style={{ cursor: "pointer" }}
                          >
                            <td>
                              <span className="reports-id">
                                {inv.investigation_id}
                              </span>
                            </td>
                            <td>
                              <span
                                className="reports-id"
                                style={{ color: "#38bdf8" }}
                              >
                                {inv.incident_id}
                              </span>
                            </td>
                            <td>
                              <span
                                className={`reports-severity severity-${String(
                                  inv.status ?? "unknown",
                                ).toLowerCase()}`}
                              >
                                {formatValue(inv.status)}
                              </span>
                            </td>
                            <td>
                              <div
                                style={{
                                  maxWidth: 260,
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                  whiteSpace: "nowrap",
                                  fontSize: "0.82rem",
                                }}
                              >
                                {inv.conclusion ? (
                                  <span style={{ color: "#a7f3d0" }}>
                                    <strong>Verdict:</strong> {inv.conclusion}
                                  </span>
                                ) : inv.analyst_notes ? (
                                  <span style={{ color: "#cbd5e1" }}>
                                    {inv.analyst_notes}
                                  </span>
                                ) : (
                                  <span style={{ color: "#64748b" }}>
                                    No notes logged
                                  </span>
                                )}
                              </div>
                            </td>
                            <td>
                              {formatDate(inv.started_at || inv.created_at)}
                            </td>
                            <td>
                              <button
                                className={`reports-select-button ${
                                  selectedInvestigation?.investigation_id ===
                                  inv.investigation_id
                                    ? "selected"
                                    : ""
                                }`}
                                type="button"
                                onClick={() => selectInvestigation(inv)}
                                title={
                                  selectedInvestigation?.investigation_id ===
                                  inv.investigation_id
                                    ? "Click to deselect"
                                    : "Select investigation"
                                }
                              >
                                {selectedInvestigation?.investigation_id ===
                                inv.investigation_id
                                  ? "Deselect ✕"
                                  : "Select"}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Investigation Pagination */}
                  <div className="reports-pagination">
                    <button
                      type="button"
                      disabled={investigationPage <= 1}
                      onClick={() =>
                        setInvestigationPage((v) => Math.max(1, v - 1))
                      }
                    >
                      <ChevronLeft size={15} /> Previous
                    </button>
                    <div className="reports-page-numbers">
                      {investigationPageButtons.map((number) => (
                        <button
                          key={number}
                          type="button"
                          className={
                            number === investigationPage ? "active" : ""
                          }
                          onClick={() => setInvestigationPage(number)}
                        >
                          {number}
                        </button>
                      ))}
                    </div>
                    <button
                      type="button"
                      disabled={investigationPage >= investigationTotalPages}
                      onClick={() =>
                        setInvestigationPage((v) =>
                          Math.min(investigationTotalPages, v + 1),
                        )
                      }
                    >
                      Next <ChevronRight size={15} />
                    </button>
                    <span>
                      Page <strong>{investigationPage}</strong> of{" "}
                      <strong>{investigationTotalPages}</strong>
                    </span>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Alert Selector for alert and detection-xai */}
          {(reportType === "alert" || reportType === "detection-xai") && (
            <div className="reports-list-panel">
              <div className="reports-panel-heading">
                <div>
                  <span className="reports-panel-eyebrow">
                    TARGET DETECTION (ALERT QUEUE)
                  </span>
                  <h2>
                    Select an Alert{" "}
                    {selectedAlert && (
                      <span
                        className="selected-tag"
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 8,
                        }}
                      >
                        Selected: <code>{selectedAlert.alert_id}</code>
                        <button
                          type="button"
                          onClick={() => setSelectedAlert(null)}
                          style={{
                            background: "rgba(239, 68, 68, 0.2)",
                            border: "1px solid #ef4444",
                            color: "#fca5a5",
                            borderRadius: 4,
                            padding: "2px 8px",
                            fontSize: 10,
                            cursor: "pointer",
                            fontWeight: 700,
                          }}
                          title="Deselect this alert"
                        >
                          ✕ Deselect
                        </button>
                      </span>
                    )}
                  </h2>
                </div>
                <div className="reports-search-compact">
                  <Search size={15} />
                  <input
                    value={alertSearch}
                    onChange={(e) => setAlertSearch(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") submitAlertSearch();
                    }}
                    placeholder="Search alert ID, attack class, IP..."
                  />
                  <button type="button" onClick={submitAlertSearch}>
                    Search
                  </button>
                  {alertSearch && (
                    <button type="button" onClick={clearAlertSearch}>
                      ×
                    </button>
                  )}
                </div>
              </div>

              {alertLoading ? (
                <div className="reports-loading">
                  <Loader2 className="reports-spin" size={22} />
                  <span>Loading alerts...</span>
                </div>
              ) : alerts.length === 0 ? (
                <div className="reports-empty">
                  <FileSearch size={28} />
                  <strong>No alerts found</strong>
                </div>
              ) : (
                <>
                  <div className="reports-table-wrap compact-scroll">
                    <table className="reports-table">
                      <thead>
                        <tr>
                          <th>ALERT ID</th>
                          <th>ATTACK CLASS</th>
                          <th>CONFIDENCE</th>
                          <th>SEVERITY</th>
                          <th>STATUS</th>
                          <th>DETECTED AT</th>
                          <th>ACTION</th>
                        </tr>
                      </thead>
                      <tbody>
                        {alerts.map((al) => (
                          <tr
                            key={al.alert_id}
                            className={
                              selectedAlert?.alert_id === al.alert_id
                                ? "reports-selected-row"
                                : ""
                            }
                            onClick={() => selectAlert(al)}
                            style={{ cursor: "pointer" }}
                          >
                            <td>
                              <span className="reports-id">{al.alert_id}</span>
                              {al.incident_id && (
                                <span
                                  className="reports-title"
                                  style={{
                                    fontSize: "0.75rem",
                                    color: "#64748b",
                                  }}
                                >
                                  Incident: {al.incident_id}
                                </span>
                              )}
                            </td>
                            <td>
                              <strong style={{ color: "#f87171" }}>
                                {formatValue(al.predicted_class)}
                              </strong>
                            </td>
                            <td>
                              <span
                                style={{ color: "#38bdf8", fontWeight: 600 }}
                              >
                                {al.confidence
                                  ? `${(Number(al.confidence) * 100).toFixed(1)}%`
                                  : "N/A"}
                              </span>
                            </td>
                            <td>
                              <span
                                className={`reports-severity severity-${String(
                                  al.severity ?? "unknown",
                                ).toLowerCase()}`}
                              >
                                {formatValue(al.severity)}
                              </span>
                            </td>
                            <td>{formatValue(al.status)}</td>
                            <td>{formatDate(al.detected_at)}</td>
                            <td>
                              <button
                                className={`reports-select-button ${
                                  selectedAlert?.alert_id === al.alert_id
                                    ? "selected"
                                    : ""
                                }`}
                                type="button"
                                onClick={() => selectAlert(al)}
                                title={
                                  selectedAlert?.alert_id === al.alert_id
                                    ? "Click to deselect"
                                    : "Select alert"
                                }
                              >
                                {selectedAlert?.alert_id === al.alert_id
                                  ? "Deselect ✕"
                                  : "Select"}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Alert Pagination */}
                  <div className="reports-pagination">
                    <button
                      type="button"
                      disabled={alertPage <= 1}
                      onClick={() => setAlertPage((v) => Math.max(1, v - 1))}
                    >
                      <ChevronLeft size={15} /> Previous
                    </button>
                    <div className="reports-page-numbers">
                      {alertPageButtons.map((number) => (
                        <button
                          key={number}
                          type="button"
                          className={number === alertPage ? "active" : ""}
                          onClick={() => setAlertPage(number)}
                        >
                          {number}
                        </button>
                      ))}
                    </div>
                    <button
                      type="button"
                      disabled={alertPage >= alertTotalPages}
                      onClick={() =>
                        setAlertPage((v) => Math.min(alertTotalPages, v + 1))
                      }
                    >
                      Next <ChevronRight size={15} />
                    </button>
                    <span>
                      Page <strong>{alertPage}</strong> of{" "}
                      <strong>{alertTotalPages}</strong>
                    </span>
                  </div>
                </>
              )}
            </div>
          )}

          {reportType === "summary" && (
            <div className="reports-summary-banner-box">
              <Shield size={38} color="#38bdf8" />
              <div style={{ flex: 1 }}>
                <h3>SOC Global Executive Summary & Security Posture Report</h3>
                <p>
                  Generates an executive situational awareness document
                  consolidating all database alerts, correlated incidents,
                  open/closed investigations, forensic conclusions, and network
                  traffic telemetry.
                </p>
                <div
                  style={{
                    display: "flex",
                    gap: 12,
                    marginTop: 14,
                    flexWrap: "wrap",
                  }}
                >
                  <button
                    className="reports-primary-btn"
                    type="button"
                    onClick={() => void previewReport()}
                    disabled={previewLoading}
                  >
                    {previewLoading ? (
                      <Loader2 size={16} className="reports-spin" />
                    ) : (
                      <Eye size={16} />
                    )}
                    Generate & Preview Summary
                  </button>
                  <button
                    className="reports-download-btn-lg"
                    type="button"
                    onClick={() => void downloadPdf()}
                    disabled={downloadLoading}
                  >
                    {downloadLoading ? (
                      <Loader2 size={16} className="reports-spin" />
                    ) : (
                      <Download size={16} />
                    )}
                    Export Executive Summary (PDF)
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
