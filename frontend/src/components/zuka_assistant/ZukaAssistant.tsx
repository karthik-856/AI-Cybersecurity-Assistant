import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createPortal } from "react-dom";
import {
  AlertTriangle,
  Bot,
  Check,
  CheckCircle,
  Minus,
  Send,
  Shield,
  Trash2,
  X,
} from "lucide-react";
import type {
  AssistantCard,
  ChatMessage,
  CurrentContext,
  PendingAction,
} from "./types";
import { SafeMarkdown } from "./SafeMarkdown";
import "./ZukaAssistant.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const WEBSITE_OPERATION_PROMPTS = [
  "Explain flow event #22750",
  "Show me reports",
  "Connect to the Database Center and show its status",
  "Show dashboard status",
  "Show me users",
  "Show alerts",
  "Show defense actions",
  "What can I do in Settings?",
  "Summarize a report by ID",
  "Summarize an alert by ID",
  "Summarize an incident by ID",
  "Summarize an investigation by ID",
  "How many alerts, incidents, investigations, reports, and users are there?",
  "What operations can you do?",
  "Open Incident Management",
  "Open Investigation",
  "Open Defense Department",
];

const DEFAULT_WELCOME_MESSAGE: ChatMessage = {
  id: "initial-welcome",
  sender: "assistant",
  text: "Hi, I'm Zuka. I can look up live website operations and summarize records from the database. Try one of the Website Operations questions below. For a specific record, ask me to summarize its ID, such as `REP-...`, `ALT-...`, `INC-...`, or `INV-...`.",
  timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  suggestedPrompts: WEBSITE_OPERATION_PROMPTS,
};

export const ZukaAssistant: React.FC = () => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [currentContext, setCurrentContext] = useState<CurrentContext>({
    incident_id: null,
    alert_id: null,
    page_route: window.location.pathname,
  });

  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    try {
      const saved = sessionStorage.getItem("zuka_chat_history");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          const completedOnly = parsed.filter((m: ChatMessage) => !m.isStreaming);
          if (completedOnly.length > 0) return completedOnly;
        }
      }
    } catch {}
    return [DEFAULT_WELCOME_MESSAGE];
  });

  const [suggestedPrompts, setSuggestedPrompts] = useState<string[]>(WEBSITE_OPERATION_PROMPTS);

  // Persist conversation to sessionStorage (excluding interim streaming messages)
  useEffect(() => {
    try {
      const completedMessages = messages.filter((m) => !m.isStreaming);
      if (completedMessages.length > 0) {
        sessionStorage.setItem("zuka_chat_history", JSON.stringify(completedMessages));
      }
    } catch {}
  }, [messages]);

  const handleClearConversation = () => {
    try {
      sessionStorage.removeItem("zuka_chat_history");
    } catch {}
    setCurrentContext({ incident_id: null, alert_id: null, page_route: window.location.pathname });
    setMessages([
      {
        id: `cleared-${Date.now()}`,
        sender: "assistant",
        text: "Hi, I'm Zuka. I can look up live website operations and summarize records from the database. Try one of the Website Operations questions below. For a specific record, ask me to summarize its ID, such as `REP-...`, `ALT-...`, `INC-...`, or `INV-...`.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        suggestedPrompts: WEBSITE_OPERATION_PROMPTS,
      },
    ]);
    setSuggestedPrompts(WEBSITE_OPERATION_PROMPTS);
  };

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    if (isOpen && !isMinimized) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading, isOpen, isMinimized]);

  // Context event listener (so incident/alert pages can communicate)
  useEffect(() => {
    function handleOpenEvent(event: any) {
      setIsOpen(true);
      setIsMinimized(false);
      const detail = event.detail || {};
      const newCtx: CurrentContext = {
        incident_id: detail.incident_id || null,
        alert_id: detail.alert_id || null,
        page_route: window.location.pathname,
      };
      setCurrentContext(newCtx);
      if (detail.prompt) {
        handleSend(detail.prompt, undefined, newCtx);
      }
    }

    function handleContextEvent(event: any) {
      const detail = event.detail || {};
      setCurrentContext((prev) => ({
        ...prev,
        incident_id: detail.incident_id !== undefined ? detail.incident_id : prev.incident_id,
        alert_id: detail.alert_id !== undefined ? detail.alert_id : prev.alert_id,
      }));
    }

    window.addEventListener("zuka:open", handleOpenEvent);
    window.addEventListener("zuka:set-context", handleContextEvent);

    return () => {
      window.removeEventListener("zuka:open", handleOpenEvent);
      window.removeEventListener("zuka:set-context", handleContextEvent);
    };
  }, []);

  const getAuthToken = () => {
    return localStorage.getItem("zuka_access_token") || "";
  };

  const handleSend = async (
    textToSend?: string,
    confirmedActionPayload?: PendingAction,
    explicitContext?: CurrentContext
  ) => {
    const rawText = textToSend !== undefined ? textToSend : inputMessage;
    const trimmed = rawText.trim();

    if (!trimmed && !confirmedActionPayload) return;

    if (!confirmedActionPayload) {
      setInputMessage("");
      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        sender: "user",
        text: trimmed,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, userMsg]);
    }

    setIsLoading(true);
    let streamedMessageId: string | null = null;

    try {
      const token = getAuthToken();
      const activeCtx = explicitContext || currentContext;
      const payload = {
        message: trimmed || "Confirmed action execution",
        current_context: activeCtx,
        confirmed_action: confirmedActionPayload || null,
      };

      const res = await fetch(`${API_BASE}/api/zuka-assistant/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          Authorization: token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }

      let data: any;
      if (res.headers.get("content-type")?.includes("text/event-stream")) {
        const reader = res.body?.getReader();
        if (!reader) throw new Error("The response stream is unavailable.");
        const decoder = new TextDecoder();
        let buffer = "";
        let streamedText = "";

        const processEvent = (block: string) => {
          const dataLine = block.split(/\r?\n/).find((line) => line.startsWith("data:"));
          if (!dataLine) return;
          const event = JSON.parse(dataLine.slice(5).trim());
          if (event.type === "token" && typeof event.text === "string") {
            streamedText += event.text;
            if (!streamedMessageId) {
              streamedMessageId = `asst-${Date.now()}`;
              setMessages((prev) => [
                ...prev,
                {
                  id: streamedMessageId!,
                  sender: "assistant",
                  text: streamedText,
                  timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                  isStreaming: true,
                },
              ]);
            } else {
              setMessages((prev) => prev.map((item) =>
                item.id === streamedMessageId ? { ...item, text: streamedText, isStreaming: true } : item
              ));
            }
          } else if (event.type === "error") {
            throw new Error(event.message || "The assistant stream encountered an error.");
          } else if (event.type === "done") {
            data = event.response;
          }
        };

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const blocks = buffer.split(/\r?\n\r?\n/);
          buffer = blocks.pop() || "";
          blocks.forEach(processEvent);
        }
        buffer += decoder.decode();
        if (buffer.trim()) processEvent(buffer);
        if (!data) throw new Error("The assistant stream ended before the answer was complete.");
      } else {
        data = await res.json();
      }

      if (typeof data.page_route === "string" && data.page_route.startsWith("/")) {
        navigate(data.page_route);
      }

      // Update contextual focus if returned
      if (data.context) {
        setCurrentContext((prev) => ({
          ...prev,
          incident_id: data.context.incident_id || prev.incident_id,
          alert_id: data.context.alert_id || prev.alert_id,
        }));
      }

      const assistantMsg: ChatMessage = {
        id: streamedMessageId || `asst-${Date.now()}`,
        sender: "assistant",
        text: data.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        card: data.card,
        confirmationRequired: data.confirmation_required,
        pendingAction: data.pending_action,
        suggestedPrompts: data.suggested_prompts || [],
        isStreaming: false,
      };

      setMessages((prev) => streamedMessageId
        ? prev.map((item) => item.id === streamedMessageId ? assistantMsg : item)
        : [...prev, assistantMsg]);
      if (data.suggested_prompts && data.suggested_prompts.length > 0) {
        setSuggestedPrompts(data.suggested_prompts);
      }
    } catch (err: any) {
      if (streamedMessageId) {
        setMessages((prev) => prev.filter((item) => item.id !== streamedMessageId));
      }
      const errMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: "assistant",
        text: `⚠️ **Operation Error**: Unable to reach backend. ${err.message || ""}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        card: {
          card_type: "error_card",
          data: { error: err.message || "Network error" },
        },
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCancelAction = () => {
    const cancelMsg: ChatMessage = {
      id: `cancel-${Date.now()}`,
      sender: "assistant",
      text: "Action cancelled. No database changes were executed.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, cancelMsg]);
  };

  const renderCard = (card: AssistantCard, pending?: PendingAction | null) => {
    if (!card || card.card_type === "none") return null;

    if (card.card_type === "confirmation_prompt" && pending) {
      const prev = pending.preview_changes || {};
      return (
        <div className="zuka-card confirmation">
          <div className="zuka-conf-title">
            <AlertTriangle size={15} />
            <span>{card.data.title || "Confirmation Required"}</span>
          </div>
          <div className="zuka-conf-summary">{pending.summary}</div>
          <div className="zuka-conf-diff">
            {Object.entries(prev).map(([k, v]) => (
              <div key={k} className="zuka-diff-row">
                <span className="zuka-diff-label">{k.replace(/_/g, " ")}:</span>
                <span className="zuka-diff-val">{typeof v === "object" ? JSON.stringify(v) : String(v)}</span>
              </div>
            ))}
          </div>
          <div className="zuka-card-actions">
            <button
              type="button"
              className="zuka-btn-confirm"
              onClick={() => handleSend(undefined, pending)}
            >
              <Check size={14} style={{ marginRight: 4, display: "inline" }} />
              Confirm & Execute
            </button>
            <button
              type="button"
              className="zuka-btn-cancel"
              onClick={handleCancelAction}
            >
              Cancel
            </button>
          </div>
        </div>
      );
    }

    if (card.card_type === "incident_summary") {
      const d = card.data;
      if (d.platform_metrics) {
        const m = d.platform_metrics;
        return (
          <div className="zuka-card">
            <div className="zuka-card-header">
              <span>Platform Metrics</span>
              <span className="zuka-badge resolved">Live</span>
            </div>
            <div className="zuka-card-grid">
              <div className="zuka-grid-item">
                <span className="zuka-grid-label">Total Alerts</span>
                <span className="zuka-grid-value">{Number(m.total_alerts || 0).toLocaleString()} ({Number(m.open_alerts || 0).toLocaleString()} Open)</span>
              </div>
              <div className="zuka-grid-item">
                <span className="zuka-grid-label">Total Incidents</span>
                <span className="zuka-grid-value">{Number(m.total_incidents || 0).toLocaleString()} ({Number(m.open_incidents || 0).toLocaleString()} Open)</span>
              </div>
              <div className="zuka-grid-item">
                <span className="zuka-grid-label">Active Investigations</span>
                <span className="zuka-grid-value">{Number(m.active_investigations || 0).toLocaleString()}</span>
              </div>
              <div className="zuka-grid-item">
                <span className="zuka-grid-label">Resolved / Closed</span>
                <span className="zuka-grid-value">{Number(m.resolved_incidents || 0).toLocaleString()} / {Number(m.closed_incidents || 0).toLocaleString()}</span>
              </div>
            </div>
          </div>
        );
      }

      return (
        <div className="zuka-card">
          <div className="zuka-card-header">
            <span>{d.incident_id}</span>
            <div style={{ display: "flex", gap: 4 }}>
              <span className={`zuka-badge ${String(d.severity).toLowerCase()}`}>{d.severity}</span>
              <span className={`zuka-badge ${String(d.status).toLowerCase()}`}>{d.status}</span>
            </div>
          </div>
          <div className="zuka-card-grid">
            <div className="zuka-grid-item">
              <span className="zuka-grid-label">Owner</span>
              <span className="zuka-grid-value">{d.owner}</span>
            </div>
            <div className="zuka-grid-item">
              <span className="zuka-grid-label">Linked Alert</span>
              <span className="zuka-grid-value">{d.linked_alert?.alert_id || "None"}</span>
            </div>
            <div className="zuka-grid-item">
              <span className="zuka-grid-label">Priority</span>
              <span className="zuka-grid-value">{d.priority}</span>
            </div>
            <div className="zuka-grid-item">
              <span className="zuka-grid-label">Investigation</span>
              <span className="zuka-grid-value">{d.investigation?.status || "NOT_STARTED"}</span>
            </div>
          </div>

          {/* Quick Buttons on card */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
            {d.linked_alert?.alert_id && d.linked_alert.status !== "ACKNOWLEDGED" && (
              <button
                type="button"
                className="zuka-quick-btn"
                onClick={() => handleSend(`acknowledge alert ${d.linked_alert.alert_id}`)}
              >
                Ack Alert {d.linked_alert.alert_id}
              </button>
            )}
            <button
              type="button"
              className="zuka-quick-btn"
              onClick={() => handleSend(`investigate incident ${d.incident_id}`)}
            >
              Investigate
            </button>
            <button
              type="button"
              className="zuka-quick-btn"
              onClick={() => handleSend(`escalate incident ${d.incident_id}`)}
            >
              Escalate
            </button>
          </div>
        </div>
      );
    }

    if (card.card_type === "alert_card") {
      const d = card.data;
      return (
        <div className="zuka-card">
          <div className="zuka-card-header">
            <span>Alert {d.alert_id}</span>
            <span className={`zuka-badge ${String(d.status).toLowerCase()}`}>{d.status}</span>
          </div>
          <div className="zuka-card-grid">
            <div className="zuka-grid-item">
              <span className="zuka-grid-label">Threat Class</span>
              <span className="zuka-grid-value">{d.predicted_class}</span>
            </div>
            <div className="zuka-grid-item">
              <span className="zuka-grid-label">Severity</span>
              <span className={`zuka-badge ${String(d.severity).toLowerCase()}`}>{d.severity}</span>
            </div>
            {d.source_ip && (
              <div className="zuka-grid-item" style={{ gridColumn: "span 2" }}>
                <span className="zuka-grid-label">Traffic Path</span>
                <span className="zuka-grid-value">{d.source_ip} → {d.destination_ip}</span>
              </div>
            )}
          </div>
          {d.status !== "ACKNOWLEDGED" && (
            <button
              type="button"
              className="zuka-quick-btn"
              onClick={() => handleSend(`acknowledge alert ${d.alert_id}`)}
            >
              Acknowledge Alert
            </button>
          )}
        </div>
      );
    }

    if (card.card_type === "action_success") {
      const d = card.data;
      return (
        <div className="zuka-card success">
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 600 }}>
            <CheckCircle size={15} />
            <span>Operation Verified & Committed</span>
          </div>
          <div style={{ fontSize: 11, marginTop: 4, fontFamily: "monospace" }}>
            Action Ledger ID: {d.action_id}
          </div>
        </div>
      );
    }

    if (card.card_type === "error_card") {
      const d = card.data;
      return (
        <div className="zuka-card error">
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 600 }}>
            <AlertTriangle size={15} />
            <span>SOC Constraint / Error</span>
          </div>
          <div style={{ fontSize: 11.5, marginTop: 4 }}>
            {d.error || "Operation could not be completed."}
          </div>
        </div>
      );
    }

    if (card.card_type === "list_card") {
      const d = card.data;
      const items = d.items || [];
      return (
        <div className="zuka-card">
          <div className="zuka-card-header">
            <span>{d.title || "Items"}</span>
            <span className="zuka-badge high">{d.total ?? items.length} Records</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {items.map((item: any, idx: number) => (
              <div
                key={idx}
                style={{
                  padding: "8px 10px",
                  backgroundColor: "rgba(30, 41, 59, 0.4)",
                  border: "1px solid rgba(51, 65, 85, 0.5)",
                  borderRadius: 8,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                <span style={{ fontWeight: 600, color: "#f8fafc" }}>{item.username || item.id || item.report_id || item.investigation_id || (item.user_id ? `User ${item.user_id}` : "")}</span>
                  <div style={{ display: "flex", gap: 4 }}>
                    {item.severity && (
                      <span className={`zuka-badge ${String(item.severity).toLowerCase()}`}>{item.severity}</span>
                    )}
                    {item.status && (
                      <span className={`zuka-badge ${String(item.status).toLowerCase()}`}>{item.status}</span>
                    )}
                  </div>
                </div>
                <div style={{ fontSize: 11.5, color: "#94a3b8", marginBottom: 6 }}>
                  <div>{item.title}</div>
                  {(item.report_id || item.investigation_id || item.role || item.type || item.meta) && (
                    <div style={{ fontSize: 10.5, color: "#64748b" }}>
                      {[item.report_id, item.investigation_id, item.role, item.type, item.meta].filter(Boolean).join(" · ")}
                    </div>
                  )}
                  {item.created_at && <div style={{ fontSize: 10.5, color: "#64748b" }}>{item.created_at}</div>}
                </div>
                <div style={{ display: "flex", gap: 6 }}>
                  {item.type === "alert" && item.status !== "ACKNOWLEDGED" && (
                    <button
                      type="button"
                      className="zuka-quick-btn"
                      onClick={() => handleSend(`acknowledge alert ${item.id}`)}
                    >
                      Acknowledge
                    </button>
                  )}
                  {item.type === "alert" && (
                    <button
                      type="button"
                      className="zuka-quick-btn"
                      onClick={() => handleSend(`summarize alert ${item.id}`)}
                    >
                      Inspect
                    </button>
                  )}
                  {item.type === "incident" && (
                    <button
                      type="button"
                      className="zuka-quick-btn"
                      onClick={() => handleSend(`summarize incident ${item.id}`)}
                    >
                      Summarize
                    </button>
                  )}
                  {item.type === "incident" && (
                    <button
                      type="button"
                      className="zuka-quick-btn"
                      onClick={() => handleSend(`investigate incident ${item.id}`)}
                    >
                      Investigate
                    </button>
                  )}
                  {item.type === "investigation" && (
                    <button
                      type="button"
                      className="zuka-quick-btn"
                      onClick={() => {
                        const target = item.investigation_id || item.id;
                        handleSend(`summarize investigation ${target}`);
                      }}
                    >
                      Inspect Dossier
                    </button>
                  )}
                  {item.report_id && (
                    <button
                      type="button"
                      className="zuka-quick-btn"
                      onClick={() => handleSend(`summarize report ${item.report_id}`)}
                    >
                      Summarize
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }

    if (card.card_type === "info_card") {
      const d = card.data;
      const recordCounts = [
        ["Alerts", d.alerts],
        ["Incidents", d.incidents],
        ["Investigations", d.investigations],
        ["Reports", d.reports],
        ["Users", d.users],
        ["Network events", d.network_events],
      ].filter(([, count]) => typeof count === "number");
      const detailFields = [
        ["Flow event", d.event_id], ["Time", d.event_time], ["Source", d.source_ip && `${d.source_ip}${d.source_port ? `:${d.source_port}` : ""}`],
        ["Destination", d.destination_ip && `${d.destination_ip}${d.destination_port ? `:${d.destination_port}` : ""}`],
        ["Protocol", d.protocol], ["Event type", d.event_type], ["Packets", d.packets], ["Bytes", d.bytes],
        ["Duration", typeof d.flow_duration_ms === "number" ? `${d.flow_duration_ms.toLocaleString()} ms` : null],
        ["Direction", d.direction], ["Capture source", d.capture_source], ["Findings", d.findings],
        ["Conclusion", d.conclusion], ["Impact", d.impact_assessment], ["Remediation", d.remediation],
        ["Related incident", d.incident_id], ["Report ID", d.report_id], ["Type", d.type], ["Format", d.format],
      ].filter(([, value]) => value !== undefined && value !== null && value !== "");
      return (
        <div className="zuka-card" style={{ borderColor: "#38bdf8" }}>
          <div className="zuka-card-header" style={{ color: "#38bdf8" }}>
            <span>{d.title || "Information"}</span>
            {d.status && <span className="zuka-badge">{d.status}</span>}
          </div>
          {d.message && <div style={{ fontSize: 12, color: "#cbd5e1" }}>{d.message}</div>}
          {d.summary && <div style={{ fontSize: 12, color: "#cbd5e1", whiteSpace: "pre-wrap" }}>{d.summary}</div>}
          {detailFields.length > 0 && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginTop: 6 }}>
              {detailFields.map(([label, value]) => (
                <div key={String(label)} style={{ padding: "6px 8px", background: "rgba(30, 41, 59, 0.55)", borderRadius: 6, color: "#94a3b8", fontSize: 10.5, minWidth: 0 }}>
                  <div>{label}</div><strong style={{ display: "block", color: "#e2e8f0", fontSize: 11, overflowWrap: "anywhere" }}>{String(value)}</strong>
                </div>
              ))}
            </div>
          )}
          {recordCounts.length > 0 && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginTop: 6 }}>
              {recordCounts.map(([label, count]) => (
                <div key={String(label)} style={{ padding: "6px 8px", background: "rgba(30, 41, 59, 0.55)", borderRadius: 6, color: "#cbd5e1", fontSize: 11.5 }}>
                  {label}: <strong style={{ color: "#f8fafc" }}>{Number(count).toLocaleString()}</strong>
                </div>
              ))}
            </div>
          )}
          {d.recommendations && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 4 }}>
              {d.recommendations.map((rec: string, i: number) => (
                <div key={i} style={{ fontSize: 11.5, color: "#e2e8f0" }}>
                  {rec}
                </div>
              ))}
            </div>
          )}
          {Array.isArray(d.items) && d.items.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 6 }}>
              {d.items.map((item: string, index: number) => (
                <span key={`${item}-${index}`} className="zuka-badge">{String(item).replace(/_/g, " ")}</span>
              ))}
            </div>
          )}
        </div>
      );
    }

    return null;
  };

  return createPortal(
    <div className="zuka-widget-container">
      {/* Floating launcher button when closed */}
      {!isOpen && (
        <button
          type="button"
          className="zuka-fab-button"
          onClick={() => {
            setIsOpen(true);
            setIsMinimized(false);
          }}
          aria-label="Open Zuka Operations Assistant"
          title="Open Zuka Operations Assistant"
        >
          <span className="zuka-fab-pulse" />
          <Bot size={17} />
          <span>Ask Zuka</span>
        </button>
      )}

      {/* Main Assistant Chat Panel */}
      {isOpen && (
        <div
          className="zuka-panel"
          style={isMinimized ? { height: 60, overflow: "hidden" } : {}}
        >
          {/* Header */}
          <div className="zuka-header">
            <div className="zuka-header-brand">
              <div className="zuka-avatar-badge">
                <Bot size={18} />
              </div>
              <div className="zuka-header-title">
                <span className="zuka-title-main">Zuka Assistant</span>
                <span className="zuka-title-sub">
                  <span className="zuka-fab-pulse" style={{ width: 6, height: 6 }} />
                  SOC Online
                </span>
              </div>
            </div>

            <div className="zuka-header-actions">
              <button
                type="button"
                className="zuka-icon-btn zuka-clear-btn"
                onClick={handleClearConversation}
                title="Clear / Delete Present Conversation"
              >
                <Trash2 size={15} />
              </button>
              <button
                type="button"
                className="zuka-icon-btn"
                onClick={() => setIsMinimized(!isMinimized)}
                title={isMinimized ? "Expand" : "Minimize"}
              >
                <Minus size={15} />
              </button>
              <button
                type="button"
                className="zuka-icon-btn"
                onClick={() => setIsOpen(false)}
                title="Close"
              >
                <X size={15} />
              </button>
            </div>
          </div>

          {!isMinimized && (
            <>
              {/* Context Active Bar */}
              {(currentContext.incident_id || currentContext.alert_id) && (
                <div className="zuka-context-bar">
                  <div className="zuka-context-tag">
                    <Shield size={13} />
                    <span>
                      Focus:{" "}
                      {currentContext.incident_id ? `Incident ${currentContext.incident_id}` : `Alert ${currentContext.alert_id}`}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="zuka-clear-context-btn"
                    onClick={() => setCurrentContext({ incident_id: null, alert_id: null })}
                    title="Clear current focus context"
                  >
                    Clear Focus
                  </button>
                </div>
              )}

              {/* Message Feed */}
              <div className="zuka-messages-feed">
                {messages.map((m) => (
                  <div key={m.id} className={`zuka-message ${m.sender}`}>
                    <div className="zuka-bubble">
                      <SafeMarkdown content={m.text} />
                    </div>
                    {m.card && renderCard(m.card, m.pendingAction)}
                    <div className="zuka-message-time">{m.timestamp}</div>
                  </div>
                ))}

                {isLoading && (
                  <div className="zuka-message assistant">
                    <div className="zuka-typing-indicator">
                      <span className="zuka-typing-dot" />
                      <span className="zuka-typing-dot" />
                      <span className="zuka-typing-dot" />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Suggested Chips */}
              {suggestedPrompts.length > 0 && (
                <div className="zuka-suggestions-panel">
                  <div className="zuka-suggestions-title">Website Operations</div>
                  <div className="zuka-suggestions-row">
                    {suggestedPrompts.map((p, idx) => (
                      <button
                        key={idx}
                        type="button"
                        className="zuka-suggestion-chip"
                        onClick={() => handleSend(p)}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Input Area */}
              <div className="zuka-input-bar">
                <textarea
                  className="zuka-input-field"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    currentContext.incident_id
                      ? `Ask Zuka about ${currentContext.incident_id}...`
                      : "Ask about the website or request an operation (e.g. show me alerts)..."
                  }
                  rows={1}
                />
                <button
                  type="button"
                  className="zuka-send-button"
                  disabled={!inputMessage.trim() || isLoading}
                  onClick={() => handleSend()}
                  title="Send message"
                >
                  <Send size={15} />
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>,
    document.body,
  );
};

export default ZukaAssistant;
