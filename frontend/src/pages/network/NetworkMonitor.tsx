import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  Check,
  Copy,
  Database,
  ExternalLink,
  Filter,
  Network,
  RefreshCw,
  Search,
  Server,
  ShieldAlert,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { formatShortDateTime, formatTime as formatUtcTime, isToday } from "../../utils/datetime";

import "./NetworkMonitor.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const PAGE_SIZE = 10;

interface NetworkEvent {
  id: number;
  event_time: string;
  source_ip?: string | null;
  destination_ip?: string | null;
  source_port?: number | null;
  destination_port?: number | null;
  protocol?: string | null;
  direction?: string | null;
  packets?: number | null;
  bytes_count?: number | null;
  flow_duration_ms?: number | null;
  interface_name?: string | null;
  capture_source?: string | null;
  event_type?: string | null;
  description?: string | null;
}

interface NetworkStats {
  total_events: number;
  unique_source_ips: number;
  unique_destination_ips: number;
  tcp_events: number;
  udp_events: number;
  other_protocol_events: number;
}

function formatNumber(value?: number | null) {
  return new Intl.NumberFormat().format(value ?? 0);
}

function formatBytes(value?: number | null) {
  if (!value) return "0 B";

  if (value < 1024) {
    return `${value} B`;
  }

  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }

  if (value < 1024 * 1024 * 1024) {
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  }

  return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

function formatDuration(value?: number | null) {
  if (value === null || value === undefined) {
    return "—";
  }

  if (value < 1000) {
    return `${value} ms`;
  }

  return `${(value / 1000).toFixed(2)} s`;
}

function formatTime(value?: string | null) {
  if (!value) {
    return "—";
  }
  return formatShortDateTime(value);
}

function protocolClass(protocol?: string | null) {
  switch ((protocol || "OTHER").toUpperCase()) {
    case "TCP":
      return "network-protocol-tcp";

    case "UDP":
      return "network-protocol-udp";

    default:
      return "";
  }
}

function datasetLabel(_value?: string | null) {
  return "Unknown";
}

function NetworkMonitor() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [events, setEvents] = useState<NetworkEvent[]>([]);

  const [stats, setStats] = useState<NetworkStats>({
    total_events: 0,
    unique_source_ips: 0,
    unique_destination_ips: 0,
    tcp_events: 0,
    udp_events: 0,
    other_protocol_events: 0,
  });

  const [search, setSearch] = useState(() => searchParams.get("search") || "");
  const [protocol, setProtocol] = useState("ALL");
  const [direction, setDirection] = useState("ALL");
  const [source, setSource] = useState("ALL");

  const [selectedEvent, setSelectedEvent] = useState<NetworkEvent | null>(null);
  const [copied, setCopied] = useState(false);

  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Sync search query param if changes in URL
  useEffect(() => {
    const q = searchParams.get("search");
    if (q !== null && q !== undefined) {
      setSearch(q);
    }
  }, [searchParams]);

  async function loadNetworkData(manual = false) {
    if (manual) {
      setRefreshing(true);
    }

    try {
      setError("");

      const token = localStorage.getItem("zuka_access_token");

      const headers: HeadersInit = {
        Accept: "application/json",
      };

      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }

      const [eventsResponse, statsResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/api/network/events?limit=1000`, {
          headers,
        }),

        fetch(`${API_BASE_URL}/api/network/stats`, {
          headers,
        }),
      ]);

      if (!eventsResponse.ok) {
        throw new Error(
          `Unable to load network events (${eventsResponse.status}).`,
        );
      }

      if (!statsResponse.ok) {
        throw new Error(
          `Unable to load network statistics (${statsResponse.status}).`,
        );
      }

      const eventsData = await eventsResponse.json();
      const statsData = await statsResponse.json();

      const rawEvents: NetworkEvent[] = Array.isArray(eventsData) ? eventsData : [];
      // Filter strictly to today's records based on user's laptop local time
      const todayEvents = rawEvents.filter((ev) => isToday(ev.event_time));

      setEvents(todayEvents);
      if (todayEvents.length > 0) {
        setStats({
          total_events: todayEvents.length,
          unique_source_ips: new Set(
            todayEvents.map((e) => e.source_ip).filter(Boolean),
          ).size,
          unique_destination_ips: new Set(
            todayEvents.map((e) => e.destination_ip).filter(Boolean),
          ).size,
          tcp_events: todayEvents.filter(
            (e) => (e.protocol || "").toUpperCase() === "TCP",
          ).length,
          udp_events: todayEvents.filter(
            (e) => (e.protocol || "").toUpperCase() === "UDP",
          ).length,
          other_protocol_events: todayEvents.filter(
            (e) => !["TCP", "UDP"].includes((e.protocol || "").toUpperCase()),
          ).length,
        });
      } else {
        setStats(statsData);
      }
      setLastUpdated(new Date());
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load network monitoring data.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadNetworkData();

    const timer = window.setInterval(() => {
      loadNetworkData();
    }, 3000);

    return () => {
      window.clearInterval(timer);
    };
  }, []);

  const sourceOptions = useMemo(() => {
    const values = new Set<string>();

    events.forEach((event) => {
      if (event.capture_source) {
        values.add(event.capture_source);
      }
    });

    return Array.from(values).sort();
  }, [events]);

  const filteredEvents = useMemo(() => {
    const query = search.trim().toLowerCase();

    return events.filter((event) => {
      const searchable = [
        event.source_ip,
        event.destination_ip,
        event.source_port,
        event.destination_port,
        event.protocol,
        event.direction,
        event.capture_source,
        event.event_type,
        event.description,
      ]
        .filter(
          (value) =>
            value !== null &&
            value !== undefined &&
            value !== "",
        )
        .join(" ")
        .toLowerCase();

      const matchesSearch =
        !query || searchable.includes(query);

      const matchesProtocol =
        protocol === "ALL" ||
        (event.protocol || "OTHER").toUpperCase() === protocol;

      const matchesDirection =
        direction === "ALL" ||
        (event.direction || "UNKNOWN").toUpperCase() === direction;

      const matchesSource =
        source === "ALL" ||
        event.capture_source === source;

      return (
        matchesSearch &&
        matchesProtocol &&
        matchesDirection &&
        matchesSource
      );
    });
  }, [events, search, protocol, direction, source]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredEvents.length / PAGE_SIZE),
  );

  const paginatedEvents = filteredEvents.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE,
  );

  useEffect(() => {
    setPage(1);
  }, [search, protocol, direction, source]);

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  function sourceLabel(event: NetworkEvent) {
    if (!event.source_ip) {
      return "Unknown";
    }

    return event.source_port
      ? `${event.source_ip}:${event.source_port}`
      : event.source_ip;
  }

  function destinationLabel(event: NetworkEvent) {
    if (!event.destination_ip) {
      return "Unknown";
    }

    return event.destination_port
      ? `${event.destination_ip}:${event.destination_port}`
      : event.destination_ip;
  }

  function clearFilters() {
    setSearch("");
    setProtocol("ALL");
    setDirection("ALL");
    setSource("ALL");
  }

  return (
    <main className="network-monitor-page">
      <header className="network-page-header">
        <div>
          <div className="network-breadcrumb">
            MONITORING
            <span>/</span>
            NETWORK MONITOR
          </div>

          <div className="network-heading">
            <div className="network-heading-icon">
              <Network size={22} />
            </div>

            <div>
              <h1>Network Monitor</h1>

              <p>
                Inspect real-time telemetry flows and correlate with SOC intelligence.
              </p>
            </div>
          </div>
        </div>

        <button
          type="button"
          className="network-refresh-button"
          onClick={() => loadNetworkData(true)}
          disabled={refreshing}
        >
          <RefreshCw
            size={15}
            className={
              refreshing ? "network-spin" : ""
            }
          />

          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </header>

      {error && (
        <div className="network-alert">
          <Activity size={16} />

          <span>{error}</span>
        </div>
      )}

      <div className="network-overview">
        <div className="network-stat-card">
          <div className="network-stat-icon">
            <Activity size={18} />
          </div>

          <div>
            <span>Total Events</span>

            <strong>
              {loading
                ? "—"
                : formatNumber(stats.total_events)}
            </strong>

            <small>Dataset-derived records</small>
          </div>
        </div>

        <div className="network-stat-card">
          <div className="network-stat-icon">
            <Server size={18} />
          </div>

          <div>
            <span>Source Addresses</span>

            <strong>
              {loading
                ? "—"
                : formatNumber(
                    stats.unique_source_ips,
                  )}
            </strong>

            <small>Unique observed origins</small>
          </div>
        </div>

        <div className="network-stat-card">
          <div className="network-stat-icon">
            <ArrowDownToLine size={18} />
          </div>

          <div>
            <span>Destinations</span>

            <strong>
              {loading
                ? "—"
                : formatNumber(
                    stats.unique_destination_ips,
                  )}
            </strong>

            <small>Unique observed targets</small>
          </div>
        </div>

        <div className="network-stat-card">
          <div className="network-stat-icon">
            <ArrowUpRight size={18} />
          </div>

          <div>
            <span>TCP / UDP</span>

            <strong>
              {loading
                ? "—"
                : `${formatNumber(
                    stats.tcp_events,
                  )} / ${formatNumber(
                    stats.udp_events,
                  )}`}
            </strong>

            <small>Protocol events</small>
          </div>
        </div>
      </div>

      <section className="network-content-card">
        <div className="network-card-header">
          <div>
            <div className="network-card-kicker">
              NETWORK ACTIVITY
            </div>

            <h2>Flow Records</h2>

            <p>
              Click any row to inspect deep flow telemetry, filter indicators, or correlate in Alert Center.
            </p>
          </div>

          <div className="network-last-updated">
            <span className="network-status-dot" />

            <div>
              <span>LAST UPDATED</span>

              <strong>
                {lastUpdated ? formatUtcTime(lastUpdated) : "—"}
              </strong>
            </div>
          </div>
        </div>

        <div className="network-filter-bar">
          <div className="network-search">
            <Search size={16} />

            <input
              type="text"
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search IP address, port, protocol..."
            />
          </div>

          <div className="network-select">
            <Filter size={14} />

            <select
              value={protocol}
              onChange={(event) =>
                setProtocol(event.target.value)
              }
            >
              <option value="ALL">All protocols</option>
              <option value="TCP">TCP</option>
              <option value="UDP">UDP</option>
              <option value="OTHER">Other</option>
            </select>
          </div>

          <div className="network-select">
            <SlidersHorizontal size={14} />

            <select
              value={direction}
              onChange={(event) =>
                setDirection(event.target.value)
              }
            >
              <option value="ALL">All directions</option>
              <option value="INBOUND">Inbound</option>
              <option value="OUTBOUND">Outbound</option>
              <option value="INTERNAL">Internal</option>
              <option value="EXTERNAL">External</option>
              <option value="UNKNOWN">Unknown</option>
            </select>
          </div>

          <div className="network-select">
            <Database size={14} />

            <select
              value={source}
              onChange={(event) =>
                setSource(event.target.value)
              }
            >
              <option value="ALL">All sources</option>

              {sourceOptions.map((item) => (
                <option key={item} value={item}>
                  {datasetLabel(item)}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="network-clear-button"
            onClick={clearFilters}
          >
            Clear
          </button>
        </div>

        <div className="network-table-meta">
          <span>
            Showing{" "}
            <strong>
              {filteredEvents.length === 0
                ? 0
                : (page - 1) * PAGE_SIZE + 1}
              –
              {Math.min(
                page * PAGE_SIZE,
                filteredEvents.length,
              )}
            </strong>{" "}
            of{" "}
            <strong>{filteredEvents.length}</strong>{" "}
            records
          </span>

          <span className="network-table-source">
            <Database size={13} />
            Dataset-derived telemetry
          </span>
        </div>

        <div className="network-table-wrap">
          <table className="network-table">
            <thead>
              <tr>
                <th>TIME</th>
                <th>SOURCE</th>
                <th>DESTINATION</th>
                <th>PROTOCOL</th>
                <th>DIRECTION</th>
                <th>PACKETS</th>
                <th>BYTES</th>
                <th>DURATION</th>
                <th>DATA SOURCE</th>
              </tr>
            </thead>

            <tbody>
              {loading && events.length === 0 ? (
                <tr>
                  <td colSpan={9}>
                    <div className="network-empty">
                      <div className="network-empty-icon">
                        <RefreshCw
                          size={19}
                          className="network-spin"
                        />
                      </div>

                      <strong>
                        Loading network records
                      </strong>

                      <span>
                        Reading dataset-derived network
                        events from PostgreSQL.
                      </span>
                    </div>
                  </td>
                </tr>
              ) : paginatedEvents.length === 0 ? (
                <tr>
                  <td colSpan={9}>
                    <div className="network-empty">
                      <div className="network-empty-icon">
                        <Network size={20} />
                      </div>

                      <strong>
                        No network records found
                      </strong>

                      <span>
                        {events.length === 0
                          ? "No network records recorded today. Telemetry flows will stream in here as dataset replay processes events."
                          : "Try changing the search or filters."}
                      </span>
                    </div>
                  </td>
                </tr>
              ) : (
                paginatedEvents.map((event) => (
                  <tr
                    key={event.id}
                    className={`network-row-clickable ${
                      selectedEvent?.id === event.id ? "network-row-active" : ""
                    }`}
                    onClick={() => setSelectedEvent(event)}
                    title="Click to inspect flow details & actions"
                  >
                    <td className="network-time">
                      {formatTime(event.event_time)}
                    </td>

                    <td>
                      <span className="network-endpoint">
                        {sourceLabel(event)}
                      </span>
                    </td>

                    <td>
                      <span className="network-endpoint">
                        {destinationLabel(event)}
                      </span>
                    </td>

                    <td>
                      <span
                        className={`network-protocol ${protocolClass(
                          event.protocol,
                        )}`}
                      >
                        {event.protocol || "OTHER"}
                      </span>
                    </td>

                    <td>
                      <span className="network-direction">
                        {event.direction || "UNKNOWN"}
                      </span>
                    </td>

                    <td>
                      {formatNumber(event.packets)}
                    </td>

                    <td>
                      {formatBytes(event.bytes_count)}
                    </td>

                    <td>
                      {formatDuration(
                        event.flow_duration_ms,
                      )}
                    </td>

                    <td>
                      <span className="network-dataset">
                        <Database size={12} />

                        {datasetLabel(
                          event.capture_source,
                        )}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="network-pagination">
          <span>
            Page {page} of {totalPages}
          </span>

          <div className="network-page-buttons">
            <button
              type="button"
              onClick={() =>
                setPage((current) =>
                  Math.max(1, current - 1),
                )
              }
              disabled={page === 1}
            >
              Previous
            </button>

            {Array.from(
              {
                length: Math.min(totalPages, 5),
              },
              (_, index) => {
                const pageNumber = index + 1;

                return (
                  <button
                    type="button"
                    key={pageNumber}
                    className={
                      pageNumber === page
                        ? "active"
                        : ""
                    }
                    onClick={() =>
                      setPage(pageNumber)
                    }
                  >
                    {pageNumber}
                  </button>
                );
              },
            )}

            <button
              type="button"
              onClick={() =>
                setPage((current) =>
                  Math.min(
                    totalPages,
                    current + 1,
                  ),
                )
              }
              disabled={page === totalPages}
            >
              Next
            </button>
          </div>
        </div>
      </section>

      {/* FLOW EVENT INSPECTOR DRAWER */}
      {selectedEvent && (
        <>
          <div
            className="network-drawer-backdrop"
            onClick={() => setSelectedEvent(null)}
          />

          <aside className="network-drawer" aria-label="Network Flow Details">
            <div className="network-drawer-header">
              <div className="network-drawer-title-group">
                <span className="network-drawer-kicker">
                  FLOW TELEMETRY INSPECTOR
                </span>
                <h3>Flow Event #{selectedEvent.id}</h3>
                <p>{formatTime(selectedEvent.event_time)}</p>
              </div>

              <button
                type="button"
                className="network-drawer-close"
                onClick={() => setSelectedEvent(null)}
                aria-label="Close Inspector"
                title="Close Inspector"
              >
                <X size={18} />
              </button>
            </div>

            <div className="network-drawer-body">
              {/* 5-Tuple summary banner */}
              <div className="network-flow-card">
                <div className="network-flow-endpoint">
                  <span className="network-flow-role">SOURCE</span>
                  <strong>{selectedEvent.source_ip || "Unknown IP"}</strong>
                  <span className="network-flow-port">
                    Port {selectedEvent.source_port ?? "—"}
                  </span>
                </div>

                <div className="network-flow-arrow">
                  <span
                    className={`network-protocol ${protocolClass(
                      selectedEvent.protocol,
                    )}`}
                  >
                    {selectedEvent.protocol || "OTHER"}
                  </span>
                  <ArrowRight size={18} />
                  <span className="network-direction-badge">
                    {selectedEvent.direction || "UNKNOWN"}
                  </span>
                </div>

                <div className="network-flow-endpoint">
                  <span className="network-flow-role">DESTINATION</span>
                  <strong>{selectedEvent.destination_ip || "Unknown IP"}</strong>
                  <span className="network-flow-port">
                    Port {selectedEvent.destination_port ?? "—"}
                  </span>
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="network-drawer-section">
                <h4>Flow Metrics & Telemetry</h4>
                <div className="network-details-grid">
                  <div className="network-detail-item">
                    <span>Packets</span>
                    <strong>{formatNumber(selectedEvent.packets)} pkts</strong>
                  </div>

                  <div className="network-detail-item">
                    <span>Total Bytes</span>
                    <strong>{formatBytes(selectedEvent.bytes_count)}</strong>
                  </div>

                  <div className="network-detail-item">
                    <span>Flow Duration</span>
                    <strong>
                      {formatDuration(selectedEvent.flow_duration_ms)}
                    </strong>
                  </div>

                  <div className="network-detail-item">
                    <span>Capture Interface</span>
                    <strong>
                      {selectedEvent.interface_name || "eth0 (virtual)"}
                    </strong>
                  </div>

                  <div className="network-detail-item">
                    <span>Data Origin</span>
                    <strong className="network-dataset-val">
                      <Database size={13} />
                      {datasetLabel(selectedEvent.capture_source)}
                    </strong>
                  </div>

                  <div className="network-detail-item">
                    <span>Classification</span>
                    <strong>
                      {selectedEvent.event_type || "Network Flow"}
                    </strong>
                  </div>
                </div>
              </div>

              {selectedEvent.description && (
                <div className="network-drawer-section">
                  <h4>Telemetry Description</h4>
                  <p className="network-drawer-desc">
                    {selectedEvent.description}
                  </p>
                </div>
              )}

              {/* SOC Actions */}
              <div className="network-drawer-section">
                <h4>SOC Workflow Actions</h4>
                <div className="network-drawer-actions">
                  {selectedEvent.source_ip && (
                    <button
                      type="button"
                      className="network-action-btn primary"
                      onClick={() => {
                        navigate(
                          `/alerts?search=${encodeURIComponent(
                            selectedEvent.source_ip || "",
                          )}`,
                        );
                      }}
                    >
                      <ShieldAlert size={15} />
                      Cross-reference in Alert Center
                    </button>
                  )}

                  {selectedEvent.source_ip && (
                    <button
                      type="button"
                      className="network-action-btn secondary"
                      onClick={() => {
                        navigate(
                          `/investigation?search=${encodeURIComponent(
                            selectedEvent.source_ip || "",
                          )}`,
                        );
                      }}
                    >
                      <ExternalLink size={15} />
                      Open in Investigation Center
                    </button>
                  )}

                  {selectedEvent.source_ip && (
                    <button
                      type="button"
                      className="network-action-btn filter-btn"
                      onClick={() => {
                        setSearch(selectedEvent.source_ip || "");
                        setSelectedEvent(null);
                      }}
                    >
                      <Filter size={14} />
                      Filter Table by Source IP ({selectedEvent.source_ip})
                    </button>
                  )}

                  {selectedEvent.destination_ip && (
                    <button
                      type="button"
                      className="network-action-btn filter-btn"
                      onClick={() => {
                        setSearch(selectedEvent.destination_ip || "");
                        setSelectedEvent(null);
                      }}
                    >
                      <Filter size={14} />
                      Filter Table by Dest IP ({selectedEvent.destination_ip})
                    </button>
                  )}

                  <button
                    type="button"
                    className="network-action-btn copy-btn"
                    onClick={async () => {
                      try {
                        await navigator.clipboard.writeText(
                          JSON.stringify(selectedEvent, null, 2),
                        );
                        setCopied(true);
                        setTimeout(() => setCopied(false), 2000);
                      } catch {
                        // ignore
                      }
                    }}
                  >
                    {copied ? (
                      <Check size={15} color="#19d39d" />
                    ) : (
                      <Copy size={15} />
                    )}
                    {copied
                      ? "Copied Flow JSON to Clipboard!"
                      : "Copy Flow JSON"}
                  </button>
                </div>
              </div>
            </div>
          </aside>
        </>
      )}

      <div className="network-page-footer">
        <span>ZUKA SOC · Network Intelligence</span>

        <span>Dataset-driven monitoring · PostgreSQL</span>
      </div>
    </main>
  );
}

export default NetworkMonitor;