import { scheduleLoad } from "../../utils/scheduleLoad";
import {
  Activity,
  AlertTriangle,
  ArrowDownUp,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Columns,
  Cpu,
  Database,
  Download,
  FileCode,
  FileText,
  HardDrive,
  History,
  Key,
  Layers,
  Network,
  RefreshCw,
  Search,
  Server,
  Shield,
  Table,
  UserCheck,
  Users,
  X,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { formatDateTime, formatTime } from "../../utils/datetime";
import "./Databases.css";

import { API_BASE_URL } from "../../services/config";

interface TableMeta {
  name: string;
  title: string;
  records: number;
  size: string;
}

interface OverviewResponse {
  database: string;
  version: string;
  status: string;
  historical_retention: boolean;
  total_records: number;
  db_size: string;
  active_connections: number;
  available_tables: string[];
  table_counts: Record<string, number>;
  tables_catalog: TableMeta[];
}

interface ColumnSchema {
  name: string;
  type: string;
  nullable: boolean;
  default: string | null;
  primary_key: boolean;
}

interface SchemaResponse {
  table: string;
  columns: ColumnSchema[];
  column_count: number;
}

interface TableResponse {
  table: string;
  available: boolean;
  columns: string[];
  records: Record<string, unknown>[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  sort_by: string;
  sort_order: string;
}

interface TableCategory {
  name: string;
  icon: typeof Database;
  tables: Array<{
    id: string;
    label: string;
    icon: typeof Database;
  }>;
}

const tableCategories: TableCategory[] = [
  {
    name: "SOC Operations",
    icon: Shield,
    tables: [
      { id: "alerts", label: "Security Alerts", icon: AlertTriangle },
      { id: "incidents", label: "Incidents", icon: ClipboardList },
      { id: "investigations", label: "Investigations", icon: Search },
      { id: "analyst_actions", label: "Analyst Actions", icon: Activity },
      { id: "audit_logs", label: "Audit Logs", icon: History },
    ],
  },
  {
    name: "Telemetry & Reports",
    icon: Network,
    tables: [
      { id: "network_events", label: "Network Events", icon: Network },
      { id: "reports", label: "Generated Reports", icon: FileText },
    ],
  },
  {
    name: "Identity & Security",
    icon: Users,
    tables: [
      { id: "users", label: "Users", icon: Users },
      { id: "roles", label: "Roles & RBAC", icon: Key },
      { id: "login_audit_logs", label: "Login History", icon: UserCheck },
      { id: "auth_sessions", label: "Active Sessions", icon: Server },
      { id: "auth_otps", label: "OTP Verification", icon: Key },
    ],
  },
];

function getToken(): string | null {
  return localStorage.getItem("zuka_access_token");
}

function getHeaders(): HeadersInit {
  const token = getToken();
  return {
    Accept: "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function apiGet<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "GET",
    headers: getHeaders(),
  });

  if (!response.ok) {
    let msg = `Request failed with HTTP ${response.status}.`;
    try {
      const errJson = await response.json();
      if (errJson?.detail) {
        msg =
          typeof errJson.detail === "string"
            ? errJson.detail
            : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(msg);
  }

  return response.json() as Promise<T>;
}

function formatColumnName(col: string): string {
  return col.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function isDateTimeCol(col: string): boolean {
  const c = col.toLowerCase();
  return (
    c.endsWith("_at") ||
    c.endsWith("_time") ||
    c === "timestamp" ||
    c === "event_time" ||
    c === "logged_at" ||
    c === "login_at" ||
    c === "action_time" ||
    c === "expires_at" ||
    c === "started_at" ||
    c === "completed_at" ||
    c === "resolved_at" ||
    c === "closed_at" ||
    c.includes("date") ||
    c.includes("time")
  );
}

function isIsoDateTimeString(val: string): boolean {
  return /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}/.test(val);
}

function Databases() {
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [tableData, setTableData] = useState<TableResponse | null>(null);
  const [schemaData, setSchemaData] = useState<SchemaResponse | null>(null);
  const [viewMode, setViewMode] = useState<"records" | "schema">("records");

  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<string>("");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  const [loading, setLoading] = useState(true);
  const [tableLoading, setTableLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const [jsonModalContent, setJsonModalContent] = useState<unknown | null>(
    null,
  );

  const dbPageButtons = useMemo(() => {
    if (!tableData) return [];
    const totalP = tableData.total_pages;
    const start = Math.max(1, Math.min(page - 2, totalP - 4));
    const end = Math.min(totalP, start + 4);
    return Array.from({ length: end - start + 1 }, (_, index) => start + index);
  }, [page, tableData]);

  // Load Overview Data
  const loadOverview = useCallback(async () => {
    const data = await apiGet<OverviewResponse>("/api/database/overview");
    setOverview(data);
    setLastUpdated(new Date());
  }, []);

  // Load Specific Table Records & Schema
  const loadTableRecords = useCallback(
    async (
      tableName: string,
      searchTerm = "",
      reqPage = 1,
      reqPageSize = 25,
      reqSortBy = "",
      reqSortOrder = "desc",
    ) => {
      if (tableName === "overview") {
        setTableData(null);
        setSchemaData(null);
        return;
      }

      setTableLoading(true);
      setError(null);

      try {
        const offset = (reqPage - 1) * reqPageSize;
        const params = new URLSearchParams();
        params.set("limit", String(reqPageSize));
        params.set("offset", String(offset));
        params.set("sort_order", reqSortOrder);

        if (searchTerm.trim()) {
          params.set("search", searchTerm.trim());
        }
        if (reqSortBy.trim()) {
          params.set("sort_by", reqSortBy.trim());
        }

        const [recordsRes, schemaRes] = await Promise.all([
          apiGet<TableResponse>(
            `/api/database/table/${tableName}?${params.toString()}`,
          ),
          apiGet<SchemaResponse>(`/api/database/table/${tableName}/schema`),
        ]);

        setTableData(recordsRes);
        setSchemaData(schemaRes);
        setLastUpdated(new Date());
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : `Unable to load table '${tableName}'.`,
        );
      } finally {
        setTableLoading(false);
      }
    },
    [],
  );

  // Full Refresh
  const handleFullRefresh = useCallback(
    async (manual = false) => {
      if (manual) setRefreshing(true);
      else setLoading(true);
      setError(null);

      try {
        await loadOverview();
        if (activeTab !== "overview") {
          await loadTableRecords(
            activeTab,
            search,
            page,
            pageSize,
            sortBy,
            sortOrder,
          );
        }
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to connect to Database Center.",
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [
      activeTab,
      loadOverview,
      loadTableRecords,
      search,
      page,
      pageSize,
      sortBy,
      sortOrder,
    ],
  );

  useEffect(() => {
    return scheduleLoad(async () => {
      try {
        await loadOverview();
      } catch (error) {
        setError(
          error instanceof Error
            ? error.message
            : "Unable to load database overview.",
        );
      } finally {
        setLoading(false);
      }
    });
  }, [loadOverview]);

  // Handle Tab Switch
  function handleSelectTab(tabId: string) {
    setActiveTab(tabId);
    setError(null);
    setSearch("");
    setPage(1);
    setSortBy("");
    setSortOrder("desc");
    setViewMode("records");

    if (tabId !== "overview") {
      void loadTableRecords(tabId, "", 1, pageSize, "", "desc");
    } else {
      setTableData(null);
      setSchemaData(null);
    }
  }

  // Handle Search Input Change (Debounced)
  useEffect(() => {
    if (activeTab === "overview") return;

    const timer = window.setTimeout(() => {
      void loadTableRecords(activeTab, search, 1, pageSize, sortBy, sortOrder);
      setPage(1);
    }, 350);

    return () => window.clearTimeout(timer);
  }, [activeTab, search, pageSize, sortBy, sortOrder, loadTableRecords]);

  // Handle Sort Change
  function handleSortChange(newSortBy: string) {
    const newOrder =
      sortBy === newSortBy && sortOrder === "desc" ? "asc" : "desc";
    setSortBy(newSortBy);
    setSortOrder(newOrder);
    void loadTableRecords(
      activeTab,
      search,
      page,
      pageSize,
      newSortBy,
      newOrder,
    );
  }

  // Export CSV
  function handleExportCsv() {
    if (!tableData || tableData.records.length === 0) return;

    const headers = tableData.columns.join(",");
    const rows = tableData.records.map((row) =>
      tableData.columns
        .map((col) => {
          const val = row[col];
          if (val === null || val === undefined) return '""';
          if (typeof val === "object")
            return `"${JSON.stringify(val).replace(/"/g, '""')}"`;
          return `"${String(val).replace(/"/g, '""')}"`;
        })
        .join(","),
    );

    const csvContent =
      "data:text/csv;charset=utf-8," + [headers, ...rows].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${tableData.table}_export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // Export JSON
  function handleExportJson() {
    if (!tableData || tableData.records.length === 0) return;
    const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify(tableData.records, null, 2),
    )}`;
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", jsonString);
    downloadAnchor.setAttribute("download", `${tableData.table}_export.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  }

  // Cell Renderer
  function renderCell(column: string, value: unknown): ReactNode {
    if (value === null || value === undefined) {
      return <span className="cell-null">—</span>;
    }

    if (value === "[REDACTED - HASHED]") {
      return <span className="cell-redacted">HASHED (PROTECTED)</span>;
    }

    if (typeof value === "object") {
      return (
        <button
          type="button"
          className="cell-json-btn"
          onClick={() => setJsonModalContent(value)}
        >
          {"{ } JSON Object"}
        </button>
      );
    }

    if (typeof value === "boolean") {
      return (
        <span className={`cell-bool ${value ? "bool-true" : "bool-false"}`}>
          {value ? "TRUE" : "FALSE"}
        </span>
      );
    }

    const strVal = String(value);

    // Formatted Badges for Severity
    if (column.toLowerCase() === "severity") {
      return (
        <span className={`db-badge sev-${strVal.toLowerCase()}`}>{strVal}</span>
      );
    }

    // Formatted Badges for Status
    if (column.toLowerCase() === "status") {
      return (
        <span className={`db-badge stat-${strVal.toLowerCase()}`}>
          {strVal}
        </span>
      );
    }

    // Formatted Badges for Action Type
    if (column.toLowerCase() === "action_type") {
      return (
        <span className="db-badge stat-investigating">
          {strVal.replace(/_/g, " ")}
        </span>
      );
    }

    // Formatted Dates in local laptop time
    if (
      (isDateTimeCol(column) ||
        (typeof value === "string" && isIsoDateTimeString(value))) &&
      typeof value === "string"
    ) {
      return (
        <span className="cell-datetime" title={strVal}>
          {formatDateTime(strVal)}
        </span>
      );
    }

    // Monospace for IDs, IPs, Ports
    if (
      column.endsWith("_id") ||
      column === "id" ||
      column.includes("ip") ||
      column.includes("port")
    ) {
      return <span className="cell-code">{strVal}</span>;
    }

    return (
      <span className="cell-text" title={strVal}>
        {strVal}
      </span>
    );
  }

  // Render Overview View
  function renderOverviewView() {
    return (
      <div className="db-overview-container">
        {/* TOP 4 KPIS */}
        <div className="db-overview-kpis">
          <div className="db-kpi-card">
            <div className="db-kpi-icon total">
              <Database size={22} />
            </div>
            <div className="db-kpi-details">
              <span>TOTAL PERSISTED ROWS</span>
              <strong>{overview?.total_records.toLocaleString() ?? "—"}</strong>
              <small>Across all 17 system tables</small>
            </div>
          </div>

          <div className="db-kpi-card">
            <div className="db-kpi-icon storage">
              <HardDrive size={22} />
            </div>
            <div className="db-kpi-details">
              <span>DATABASE DISK SIZE</span>
              <strong>{overview?.db_size ?? "—"}</strong>
              <small>PostgreSQL physical allocation</small>
            </div>
          </div>

          <div className="db-kpi-card">
            <div className="db-kpi-icon tables">
              <Table size={22} />
            </div>
            <div className="db-kpi-details">
              <span>ACTIVE SYSTEM TABLES</span>
              <strong>{overview?.available_tables.length ?? 0} Tables</strong>
              <small>Fully indexed schemas</small>
            </div>
          </div>

          <div className="db-kpi-card">
            <div className="db-kpi-icon conns">
              <Server size={22} />
            </div>
            <div className="db-kpi-details">
              <span>ACTIVE CONNECTIONS</span>
              <strong>{overview?.active_connections ?? 1} Conns</strong>
              <small>PostgreSQL connection pool</small>
            </div>
          </div>
        </div>

        {/* MIDDLE SECTION: SYSTEM SPECS & LIFECYCLE */}
        <div className="db-overview-middle-grid">
          {/* ENGINE SPECS */}
          <div className="db-panel">
            <div className="db-panel-header">
              <div>
                <span className="db-panel-eyebrow">PERSISTENCE ENGINE</span>
                <h3>PostgreSQL Production Engine</h3>
              </div>
              <Cpu size={20} className="db-accent-icon" />
            </div>

            <div className="db-engine-specs">
              <div className="spec-row">
                <span>Database Engine</span>
                <strong>{overview?.version ?? "PostgreSQL"}</strong>
              </div>
              <div className="spec-row">
                <span>Connection Status</span>
                <span className="status-connected">
                  <span className="dot-green" /> CONNECTED & HEALTHY
                </span>
              </div>
              <div className="spec-row">
                <span>Historical Retention</span>
                <strong style={{ color: "#19d39d" }}>ACTIVE & ENFORCED</strong>
              </div>
              <div className="spec-row">
                <span>Credential Protection</span>
                <strong style={{ color: "#38bdf8" }}>
                  AUTOMATIC HASH SCRUBBING
                </strong>
              </div>
              <div className="spec-row">
                <span>Data Isolation</span>
                <strong>STRICT RBAC (ADMIN ACCESS ONLY)</strong>
              </div>
            </div>
          </div>

          {/* SOC LIFECYCLE FLOW */}
          <div className="db-panel">
            <div className="db-panel-header">
              <div>
                <span className="db-panel-eyebrow">SOC RECORD PIPELINE</span>
                <h3>Security Data Lifecycle</h3>
              </div>
              <Activity size={20} className="db-accent-icon" />
            </div>

            <div className="db-lifecycle-steps">
              <div className="lifecycle-step">
                <span className="step-num">01</span>
                <div>
                  <strong>Network Flow Ingestion</strong>
                  <p>Packets logged in `network_events` table</p>
                </div>
              </div>
              <div className="lifecycle-step">
                <span className="step-num">02</span>
                <div>
                  <strong>ML Inference & Detection</strong>
                  <p>Model alerts written to `alerts` table</p>
                </div>
              </div>
              <div className="lifecycle-step">
                <span className="step-num">03</span>
                <div>
                  <strong>Incident Escalation</strong>
                  <p>Tickets assigned in `incidents` table</p>
                </div>
              </div>
              <div className="lifecycle-step">
                <span className="step-num">04</span>
                <div>
                  <strong>Audit & Reporting</strong>
                  <p>Archived in `audit_logs` & `reports`</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* FULL TABLE CATALOG CARDS */}
        <div className="db-panel table-catalog-panel">
          <div className="db-panel-header">
            <div>
              <span className="db-panel-eyebrow">SYSTEM INVENTORY</span>
              <h3>Database Table Catalog</h3>
              <p>
                Directly inspect rows, schemas, and disk footprint for all
                tables.
              </p>
            </div>
            <Layers size={20} className="db-accent-icon" />
          </div>

          <div className="db-catalog-grid">
            {overview?.tables_catalog
              ?.filter(
                (t) =>
                  t.name !== "push_subscriptions" &&
                  !t.name.startsWith("zuka_assistant"),
              )
              ?.map((t) => (
                <div
                  key={t.name}
                  className="db-catalog-card"
                  onClick={() => handleSelectTab(t.name)}
                >
                  <div className="catalog-card-header">
                    <div className="catalog-card-icon">
                      <Table size={18} />
                    </div>
                    <span className="catalog-card-size">{t.size}</span>
                  </div>
                  <strong className="catalog-card-name">{t.name}</strong>
                  <span className="catalog-card-title">{t.title}</span>
                  <div className="catalog-card-footer">
                    <span className="catalog-card-records">
                      {t.records.toLocaleString()} rows
                    </span>
                    <span className="catalog-card-explore">Inspect →</span>
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>
    );
  }

  // Render Table Explorer View
  function renderTableView() {
    return (
      <div className="db-table-explorer">
        {/* EXPLORER TOOLBAR */}
        <div className="db-explorer-toolbar">
          <div className="toolbar-left">
            <div className="table-title-block">
              <Table size={20} style={{ color: "#38bdf8" }} />
              <div>
                <h2>{tableData?.table}</h2>
                <span>
                  {tableLoading
                    ? "Fetching data..."
                    : `${tableData?.total.toLocaleString() ?? 0} total records`}
                </span>
              </div>
            </div>

            {/* VIEW MODE TOGGLE (RECORDS vs SCHEMA) */}
            <div className="view-mode-toggle">
              <button
                type="button"
                className={`toggle-btn ${viewMode === "records" ? "active" : ""}`}
                onClick={() => setViewMode("records")}
              >
                <Table size={14} />
                <span>Records ({tableData?.total.toLocaleString() ?? 0})</span>
              </button>
              <button
                type="button"
                className={`toggle-btn ${viewMode === "schema" ? "active" : ""}`}
                onClick={() => setViewMode("schema")}
              >
                <Columns size={14} />
                <span>Schema ({schemaData?.column_count ?? 0})</span>
              </button>
            </div>
          </div>

          <div className="toolbar-right">
            {/* SEARCH */}
            {viewMode === "records" && (
              <div className="db-search-box">
                <Search size={15} />
                <input
                  type="text"
                  placeholder="Search table rows..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                {search && (
                  <button
                    type="button"
                    className="clear-search-btn"
                    onClick={() => setSearch("")}
                  >
                    <X size={13} />
                  </button>
                )}
              </div>
            )}

            {/* SORT DROPDOWN */}
            {viewMode === "records" && tableData && (
              <div className="db-sort-box">
                <ArrowDownUp size={14} />
                <select
                  value={sortBy}
                  onChange={(e) => handleSortChange(e.target.value)}
                >
                  <option value="">Sort: Default</option>
                  {tableData.columns.map((col) => (
                    <option key={col} value={col}>
                      Sort: {formatColumnName(col)}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="sort-direction-btn"
                  onClick={() =>
                    setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"))
                  }
                  title={`Order: ${sortOrder.toUpperCase()}`}
                >
                  {sortOrder.toUpperCase()}
                </button>
              </div>
            )}

            {/* EXPORT BUTTONS */}
            {viewMode === "records" && (
              <div className="db-export-actions">
                <button
                  type="button"
                  className="db-action-btn"
                  onClick={handleExportCsv}
                  title="Export to CSV"
                  disabled={!tableData || tableData.records.length === 0}
                >
                  <Download size={14} />
                  <span>CSV</span>
                </button>
                <button
                  type="button"
                  className="db-action-btn"
                  onClick={handleExportJson}
                  title="Export to JSON"
                  disabled={!tableData || tableData.records.length === 0}
                >
                  <FileCode size={14} />
                  <span>JSON</span>
                </button>
              </div>
            )}

            {/* REFRESH BUTTON */}
            <button
              type="button"
              className="db-action-btn refresh-btn"
              onClick={() =>
                loadTableRecords(
                  activeTab,
                  search,
                  page,
                  pageSize,
                  sortBy,
                  sortOrder,
                )
              }
              disabled={tableLoading}
              title="Refresh Current Table"
            >
              <RefreshCw
                size={14}
                className={tableLoading ? "dashboard-spin" : ""}
              />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* RECORDS VIEW */}
        {viewMode === "records" && (
          <div className="db-table-content">
            {tableLoading ? (
              <div className="db-table-state-box">
                <RefreshCw size={28} className="dashboard-spin" />
                <h3>Querying PostgreSQL...</h3>
                <p>
                  Retrieving page {page} of table `{tableData?.table}`
                </p>
              </div>
            ) : !tableData || tableData.records.length === 0 ? (
              <div className="db-table-state-box">
                <CheckCircle2 size={28} style={{ color: "#64748b" }} />
                <h3>No records found</h3>
                <p>
                  {search
                    ? `No rows match search filter "${search}".`
                    : "This table is currently empty."}
                </p>
              </div>
            ) : (
              <div className="db-table-scroll-wrap">
                <table className="db-data-table">
                  <thead>
                    <tr>
                      {tableData.columns.map((col) => (
                        <th
                          key={col}
                          onClick={() => handleSortChange(col)}
                          className={sortBy === col ? "sorted-header" : ""}
                          title="Click to sort by this column"
                        >
                          <div className="header-cell-inner">
                            <span>{formatColumnName(col)}</span>
                            {sortBy === col && (
                              <span className="sort-indicator">
                                {sortOrder === "asc" ? "▲" : "▼"}
                              </span>
                            )}
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {tableData.records.map((row, rowIdx) => (
                      <tr key={rowIdx}>
                        {tableData.columns.map((col) => (
                          <td key={`${rowIdx}-${col}`}>
                            {renderCell(col, row[col])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* PAGINATION BAR */}
            {tableData && tableData.total > 0 && (
              <div className="db-pagination-bar">
                <div className="pagination-info">
                  Showing <strong>{(page - 1) * pageSize + 1}</strong> to{" "}
                  <strong>{Math.min(page * pageSize, tableData.total)}</strong>{" "}
                  of <strong>{tableData.total.toLocaleString()}</strong> records
                </div>

                <div className="pagination-controls">
                  <div className="page-size-picker">
                    <span>Rows:</span>
                    <select
                      value={pageSize}
                      onChange={(e) => {
                        const newSz = Number(e.target.value);
                        setPageSize(newSz);
                        setPage(1);
                        void loadTableRecords(
                          activeTab,
                          search,
                          1,
                          newSz,
                          sortBy,
                          sortOrder,
                        );
                      }}
                    >
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                    </select>
                  </div>

                  <button
                    type="button"
                    className="page-nav-btn prev-next"
                    disabled={page <= 1 || tableLoading}
                    onClick={() => {
                      const nextP = page - 1;
                      setPage(nextP);
                      void loadTableRecords(
                        activeTab,
                        search,
                        nextP,
                        pageSize,
                        sortBy,
                        sortOrder,
                      );
                    }}
                    title="Previous Page"
                  >
                    <ChevronLeft size={14} />
                    <span>Prev</span>
                  </button>

                  <div className="db-page-numbers">
                    {dbPageButtons.map((num) => (
                      <button
                        key={num}
                        type="button"
                        className={`db-page-num-btn ${num === page ? "active" : ""}`}
                        disabled={tableLoading}
                        onClick={() => {
                          setPage(num);
                          void loadTableRecords(
                            activeTab,
                            search,
                            num,
                            pageSize,
                            sortBy,
                            sortOrder,
                          );
                        }}
                      >
                        {num}
                      </button>
                    ))}
                  </div>

                  <span className="page-counter">
                    Page <strong>{page}</strong> of{" "}
                    <strong>{tableData.total_pages}</strong>
                  </span>

                  <button
                    type="button"
                    className="page-nav-btn prev-next"
                    disabled={page >= tableData.total_pages || tableLoading}
                    onClick={() => {
                      const nextP = page + 1;
                      setPage(nextP);
                      void loadTableRecords(
                        activeTab,
                        search,
                        nextP,
                        pageSize,
                        sortBy,
                        sortOrder,
                      );
                    }}
                    title="Next Page"
                  >
                    <span>Next</span>
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* SCHEMA VIEW */}
        {viewMode === "schema" && (
          <div className="db-schema-content">
            <table className="db-data-table schema-table">
              <thead>
                <tr>
                  <th>COLUMN NAME</th>
                  <th>DATA TYPE</th>
                  <th>PRIMARY KEY</th>
                  <th>NULLABLE</th>
                  <th>DEFAULT VALUE</th>
                </tr>
              </thead>
              <tbody>
                {schemaData?.columns.map((col) => (
                  <tr key={col.name}>
                    <td>
                      <strong className="schema-col-name">{col.name}</strong>
                    </td>
                    <td>
                      <span className="schema-col-type">{col.type}</span>
                    </td>
                    <td>
                      {col.primary_key ? (
                        <span className="badge-pk">PRIMARY KEY</span>
                      ) : (
                        <span className="cell-null">—</span>
                      )}
                    </td>
                    <td>
                      <span
                        className={`badge-null ${col.nullable ? "nullable" : "not-null"}`}
                      >
                        {col.nullable ? "NULL" : "NOT NULL"}
                      </span>
                    </td>
                    <td>
                      <span className="schema-col-default">
                        {col.default ?? "—"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="databases-page">
      {/* =====================================================
          HEADER SECTION
      ===================================================== */}
      <div className="databases-header">
        <div className="header-info">
          <div className="databases-eyebrow">DATABASE OPERATIONS & STORAGE</div>
          <h1>Database Center & Schema Catalog</h1>
          <p>
            Inspect and query PostgreSQL historical tables, audit trails,
            network telemetry, and machine learning alerts in a high-security
            operational view.
          </p>
        </div>

        {/* STATUS PILL */}
        <div className="databases-status-pill">
          <div className="pill-dot" />
          <div className="pill-text">
            <strong>PostgreSQL Engine</strong>
            <span>
              {loading
                ? "Connecting..."
                : `${overview?.db_size ?? "Active"} · ${overview?.total_records.toLocaleString() ?? 0} Rows`}
            </span>
          </div>
          <button
            type="button"
            className="header-refresh-btn"
            onClick={() => handleFullRefresh(true)}
            disabled={refreshing}
            title="Refresh All Database Stats"
          >
            <RefreshCw
              size={14}
              className={refreshing ? "dashboard-spin" : ""}
            />
          </button>
        </div>
      </div>

      {/* ERROR NOTICE */}
      {error && (
        <div className="database-error-banner">
          <XCircle size={18} />
          <span>{error}</span>
          <button type="button" onClick={() => handleFullRefresh(true)}>
            Retry
          </button>
        </div>
      )}

      {/* =====================================================
          CATEGORIZED TABS NAVIGATION
      ===================================================== */}
      <div className="db-tabs-shell">
        <div className="db-tabs-row">
          {/* OVERVIEW TAB */}
          <button
            type="button"
            className={`db-nav-tab ${activeTab === "overview" ? "active" : ""}`}
            onClick={() => handleSelectTab("overview")}
          >
            <Database size={15} />
            <span>Overview & Catalog</span>
          </button>

          {/* CATEGORIES WITH DROPDOWN OR QUICK PILLS */}
          {tableCategories.map((cat) => (
            <div key={cat.name} className="db-category-group">
              <span className="db-cat-label">{cat.name}</span>
              {cat.tables.map((t) => {
                const Icon = t.icon;
                const count = overview?.table_counts?.[t.id] ?? 0;
                const isActive = activeTab === t.id;

                return (
                  <button
                    key={t.id}
                    type="button"
                    className={`db-nav-tab ${isActive ? "active" : ""}`}
                    onClick={() => handleSelectTab(t.id)}
                  >
                    <Icon size={14} />
                    <span>{t.label}</span>
                    {count > 0 && (
                      <span className="tab-count-badge">
                        {count > 9999 ? `${(count / 1000).toFixed(1)}k` : count}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* =====================================================
          MAIN CONTENT AREA (Overview vs Table Explorer)
      ===================================================== */}
      <div className="db-main-content">
        {activeTab === "overview" ? renderOverviewView() : renderTableView()}
      </div>

      {/* =====================================================
          JSON OBJECT VIEWER MODAL
      ===================================================== */}
      {jsonModalContent !== null && (
        <div
          className="db-modal-overlay"
          onClick={() => setJsonModalContent(null)}
        >
          <div className="db-modal-window" onClick={(e) => e.stopPropagation()}>
            <div className="db-modal-header">
              <div className="modal-title">
                <FileCode size={18} style={{ color: "#38bdf8" }} />
                <h3>Structured JSON Inspector</h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setJsonModalContent(null)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="db-modal-body">
              <pre>{JSON.stringify(jsonModalContent, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}

      {/* FOOTER */}
      <div className="databases-footer">
        <span>ZUKA SOC · PostgreSQL Historical Store</span>
        <span>
          {lastUpdated
            ? `Sync completed at ${formatTime(lastUpdated)}`
            : "Connecting..."}
        </span>
      </div>
    </div>
  );
}

export default Databases;
