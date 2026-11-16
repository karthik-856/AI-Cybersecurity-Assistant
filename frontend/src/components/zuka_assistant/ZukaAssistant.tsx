import { sessionFetch } from "../../services/sessionFetch";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createPortal } from "react-dom";
import { Bot, Check, Minus, Send, Trash2, X } from "lucide-react";
import type {
  AssistantCard,
  AssistantResponse,
  ChatMessage,
  CurrentContext,
  PendingAction,
} from "./types";
import { API_BASE_URL } from "../../services/config";
import { SafeMarkdown } from "./SafeMarkdown";
import "./ZukaAssistant.css";

const PROMPTS = [
  "Show alerts",
  "Show incidents",
  "Show investigations",
  "Show reports",
];
const WELCOME: ChatMessage = {
  id: "welcome",
  sender: "assistant",
  text: "Hi, I'm Zuka. Ask about an alert, incident, investigation, or report.",
  timestamp: "",
};
const time = () =>
  new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const text = (value: unknown) =>
  typeof value === "string" || typeof value === "number" ? String(value) : "";
const record = (value: unknown): Record<string, unknown> =>
  value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};

function restoreHistory(): ChatMessage[] {
  try {
    const saved: unknown = JSON.parse(
      sessionStorage.getItem("zuka_chat_history") || "null",
    );
    if (Array.isArray(saved)) {
      const messages = saved
        .map(record)
        .filter(
          (m) =>
            (m.sender === "user" || m.sender === "assistant") &&
            typeof m.text === "string" &&
            !m.isStreaming,
        );
      if (messages.length)
        return messages.slice(-50).map((m) => ({
          id: text(m.id),
          sender: m.sender as "user" | "assistant",
          text: text(m.text),
          timestamp: text(m.timestamp),
        }));
    }
  } catch {
    /* History is optional when browser storage is unavailable. */
  }
  return [WELCOME];
}

function RecordCard({
  card,
  onSend,
}: {
  card: AssistantCard;
  onSend: (message: string) => void;
}) {
  const d = card.data;
  if (card.card_type === "confirmation_prompt" || card.card_type === "none")
    return null;
  const rows = Array.isArray(d.items) ? d.items.slice(0, 6) : [];
  const fields = [
    ["Severity", d.severity],
    ["Status", d.status],
    ["Owner", d.owner],
    ["Priority", d.priority],
    ["Source", d.source_ip],
    ["Destination", d.destination_ip],
    ["Finding", d.findings],
    ["Conclusion", d.conclusion],
  ].filter(([, v]) => text(v));
  const title =
    text(d.title || d.incident_id || d.alert_id || d.report_id) ||
    (card.card_type === "error_card"
      ? "Unable to complete action"
      : card.card_type === "action_success"
        ? "Action recorded"
        : "Details");
  return (
    <div
      className={`zuka-card ${card.card_type === "error_card" ? "error" : ""}`}
    >
      <div className="zuka-card-header">
        <strong>{title}</strong>
      </div>
      {text(d.error || d.message || d.summary) && (
        <p>{text(d.error || d.message || d.summary)}</p>
      )}
      {fields.length > 0 && (
        <dl className="zuka-card-grid">
          {fields.map(([label, value]) => (
            <div className="zuka-grid-item" key={text(label)}>
              <dt className="zuka-grid-label">{text(label)}</dt>
              <dd className="zuka-grid-value">{text(value)}</dd>
            </div>
          ))}
        </dl>
      )}
      {Object.entries(record(d.platform_metrics)).map(([key, value]) => (
        <div key={key}>
          {key.replaceAll("_", " ")}: {text(value)}
        </div>
      ))}
      {rows.map((value, index) => {
        if (typeof value === "string") return <div key={index}>{value}</div>;
        const item = record(value);
        const id = text(item.report_id || item.investigation_id || item.id);
        const type = item.report_id
          ? "report"
          : item.investigation_id
            ? "investigation"
            : text(item.type);
        return (
          <div key={id || index} className="zuka-list-item">
            <strong>{text(item.title || item.username || id)}</strong>
            {text(item.status) && <span> {text(item.status)}</span>}
            {id &&
              ["alert", "incident", "report", "investigation"].includes(
                type,
              ) && (
                <button
                  type="button"
                  className="zuka-quick-btn"
                  onClick={() => onSend(`summarize ${type} ${id}`)}
                >
                  View details
                </button>
              )}
          </div>
        );
      })}
      {Array.isArray(d.sources) && (
        <small>Sources: {d.sources.map(text).filter(Boolean).join(", ")}</small>
      )}
    </div>
  );
}

export function ZukaAssistant() {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>(restoreHistory);
  const [isLoading, setIsLoading] = useState(false);
  const [context, setContext] = useState<CurrentContext>({});
  const [prompts, setPrompts] = useState(PROMPTS);
  const endRef = useRef<HTMLDivElement>(null);
  const busyRef = useRef(false);
  const requestRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => () => requestRef.current?.abort(), []);
  useEffect(() => {
    try {
      sessionStorage.setItem(
        "zuka_chat_history",
        JSON.stringify(messages.filter((m) => !m.isStreaming).slice(-50)),
      );
    } catch {
      /* Private browsing or a full quota must not interrupt a conversation. */
    }
  }, [messages]);
  useEffect(() => {
    if (isOpen && !isMinimized)
      endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading, isOpen, isMinimized]);
  useEffect(() => {
    if (isOpen && !isMinimized) inputRef.current?.focus();
  }, [isOpen, isMinimized]);

  const send = useCallback(
    async (
      message: string,
      pending?: PendingAction,
      explicitContext?: CurrentContext,
    ) => {
      const value = message.trim();
      if (busyRef.current || (!value && !pending)) return;
      busyRef.current = true;
      setIsLoading(true);
      setInput("");
      if (!pending)
        setMessages((previous) => [
          ...previous,
          {
            id: crypto.randomUUID(),
            sender: "user",
            text: value,
            timestamp: time(),
          },
        ]);
      const controller = new AbortController();
      requestRef.current = controller;
      const timeout = window.setTimeout(() => controller.abort(), 120000);
      const messageId = crypto.randomUUID();
      let streamedText = "";
      try {
        const token = localStorage.getItem("zuka_access_token");
        const response = await sessionFetch(
          `${API_BASE_URL}/api/zuka-assistant/chat/stream`,
          {
            method: "POST",
            signal: controller.signal,
            headers: {
              "Content-Type": "application/json",
              Accept: "text/event-stream",
              Authorization: token ? `Bearer ${token}` : "",
            },
            body: JSON.stringify({
              message: value || "Confirm action",
              current_context: explicitContext || context,
              confirmed_action: pending || null,
            }),
          },
        );
        if (response.status === 401)
          throw new Error("Your session expired. Please sign in again.");
        if (!response.ok)
          throw new Error(
            "The request could not be completed. Please try again.",
          );
        let answer: AssistantResponse | undefined;
        if (
          response.headers.get("content-type")?.includes("text/event-stream")
        ) {
          const reader = response.body?.getReader();
          if (!reader)
            throw new Error("The response is unavailable. Please try again.");
          const decoder = new TextDecoder();
          let buffer = "";
          const processEvent = (block: string) => {
            const line = block
              .split(/\r?\n/)
              .find((value) => value.startsWith("data:"));
            if (!line) return;
            const event = record(JSON.parse(line.slice(5)));
            if (event.type === "token" && typeof event.text === "string") {
              streamedText += event.text;
              setMessages((previous) => {
                const next: ChatMessage = {
                  id: messageId,
                  sender: "assistant",
                  text: streamedText,
                  timestamp: time(),
                  isStreaming: true,
                };
                return previous.some((m) => m.id === messageId)
                  ? previous.map((m) => (m.id === messageId ? next : m))
                  : [...previous, next];
              });
            } else if (event.type === "done")
              answer = event.response as AssistantResponse;
            else if (event.type === "error")
              throw new Error(
                "Zuka could not finish the answer. Please try again.",
              );
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
        } else answer = (await response.json()) as AssistantResponse;
        if (!answer || typeof answer.reply !== "string")
          throw new Error("The response was incomplete. Please try again.");
        const finalMessage: ChatMessage = {
          id: messageId,
          sender: "assistant",
          text: answer.reply,
          timestamp: time(),
          card: answer.card,
          pendingAction: answer.pending_action,
          confirmationRequired: answer.confirmation_required,
        };
        setMessages((previous) => [
          ...previous.filter((m) => m.id !== messageId),
          finalMessage,
        ]);
        const returnedContext = answer.context;
        if (returnedContext)
          setContext((previous) => ({ ...previous, ...returnedContext }));
        if (
          Array.isArray(answer.suggested_prompts) &&
          answer.suggested_prompts.length
        )
          setPrompts(answer.suggested_prompts.slice(0, 4));
        if (
          answer.page_route?.startsWith("/") &&
          !answer.page_route.startsWith("//")
        )
          navigate(answer.page_route);
      } catch (error) {
        if (controller.signal.aborted) return;
        setMessages((previous) => [
          ...previous.filter((m) => m.id !== messageId),
          {
            id: messageId,
            sender: "assistant",
            text:
              error instanceof Error
                ? error.message
                : "Unable to complete your request. Please try again.",
            timestamp: time(),
          },
        ]);
      } finally {
        window.clearTimeout(timeout);
        if (requestRef.current === controller) requestRef.current = null;
        busyRef.current = false;
        setIsLoading(false);
      }
    },
    [context, navigate],
  );

  useEffect(() => {
    function update(event: Event) {
      const detail = record((event as CustomEvent<unknown>).detail);
      setContext((previous) => ({
        ...previous,
        ...(typeof detail.incident_id === "string" ||
        detail.incident_id === null
          ? { incident_id: detail.incident_id }
          : {}),
        ...(typeof detail.alert_id === "string" || detail.alert_id === null
          ? { alert_id: detail.alert_id }
          : {}),
      }));
    }
    function open(event: Event) {
      update(event);
      setIsOpen(true);
      setIsMinimized(false);
      const detail = record((event as CustomEvent<unknown>).detail);
      if (typeof detail.prompt === "string")
        void send(detail.prompt, undefined, {
          incident_id: text(detail.incident_id) || null,
          alert_id: text(detail.alert_id) || null,
          page_route: window.location.pathname,
        });
    }
    window.addEventListener("zuka:open", open);
    window.addEventListener("zuka:set-context", update);
    return () => {
      window.removeEventListener("zuka:open", open);
      window.removeEventListener("zuka:set-context", update);
    };
  }, [send]);

  function clear() {
    requestRef.current?.abort();
    setMessages([WELCOME]);
    setContext({});
    setPrompts(PROMPTS);
  }

  return createPortal(
    <div className="zuka-widget-container">
      {!isOpen && (
        <button
          type="button"
          className="zuka-fab-button"
          onClick={() => setIsOpen(true)}
          aria-label="Open Zuka assistant"
        >
          <Bot size={17} />
          Ask Zuka
        </button>
      )}
      {isOpen && (
        <section
          className="zuka-panel"
          aria-label="Zuka assistant"
          style={isMinimized ? { height: 60 } : undefined}
        >
          <header className="zuka-header">
            <div className="zuka-header-brand">
              <Bot size={20} />
              <div className="zuka-header-title">
                <span className="zuka-title-main">Ask Zuka</span>
                <span className="zuka-title-sub">Your SOC assistant</span>
              </div>
            </div>
            <div className="zuka-header-actions">
              <button
                type="button"
                className="zuka-icon-btn"
                onClick={clear}
                aria-label="Clear conversation"
              >
                <Trash2 size={16} />
              </button>
              <button
                type="button"
                className="zuka-icon-btn"
                onClick={() => setIsMinimized((previous) => !previous)}
                aria-label={
                  isMinimized ? "Expand assistant" : "Minimize assistant"
                }
              >
                <Minus size={16} />
              </button>
              <button
                type="button"
                className="zuka-icon-btn"
                onClick={() => setIsOpen(false)}
                aria-label="Close assistant"
              >
                <X size={16} />
              </button>
            </div>
          </header>
          {!isMinimized && (
            <>
              {(context.incident_id || context.alert_id) && (
                <div className="zuka-context-bar">
                  <span>{context.incident_id || context.alert_id}</span>
                  <button
                    type="button"
                    className="zuka-clear-context-btn"
                    onClick={() => setContext({})}
                  >
                    Clear focus
                  </button>
                </div>
              )}
              <div
                className="zuka-messages-feed"
                role="log"
                aria-live="polite"
                aria-busy={isLoading}
              >
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`zuka-message ${message.sender}`}
                  >
                    <div className="zuka-bubble">
                      <SafeMarkdown content={message.text} />
                    </div>
                    {message.card && (
                      <RecordCard
                        card={message.card}
                        onSend={(value) => void send(value)}
                      />
                    )}
                    {message.confirmationRequired && message.pendingAction && (
                      <div className="zuka-card">
                        <p>{message.pendingAction.summary}</p>
                        <div className="zuka-confirm-actions">
                          <button
                            type="button"
                            className="zuka-btn-confirm"
                            disabled={isLoading}
                            onClick={() => {
                              const pending = message.pendingAction;
                              setMessages((previous) =>
                                previous.map((m) =>
                                  m.id === message.id
                                    ? { ...m, confirmationRequired: false }
                                    : m,
                                ),
                              );
                              void send("", pending || undefined);
                            }}
                          >
                            <Check size={14} />
                            Confirm action
                          </button>
                          <button
                            type="button"
                            className="zuka-btn-cancel"
                            onClick={() =>
                              setMessages((previous) =>
                                previous.map((m) =>
                                  m.id === message.id
                                    ? { ...m, confirmationRequired: false }
                                    : m,
                                ),
                              )
                            }
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                    {message.timestamp && (
                      <div className="zuka-message-time">
                        {message.timestamp}
                      </div>
                    )}
                  </div>
                ))}
                {isLoading && (
                  <div
                    className="zuka-typing-indicator"
                    aria-label="Zuka is responding"
                  >
                    <span className="zuka-typing-dot" />
                    <span className="zuka-typing-dot" />
                    <span className="zuka-typing-dot" />
                  </div>
                )}
                <div ref={endRef} />
              </div>
              <div className="zuka-suggestions-panel">
                <div className="zuka-suggestions-row">
                  {prompts.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      className="zuka-suggestion-chip"
                      disabled={isLoading}
                      onClick={() => void send(prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
              <form
                className="zuka-input-bar"
                onSubmit={(event) => {
                  event.preventDefault();
                  void send(input);
                }}
              >
                <textarea
                  ref={inputRef}
                  className="zuka-input-field"
                  aria-label="Message Zuka"
                  placeholder="Ask a question or request an action"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      void send(input);
                    }
                  }}
                  rows={1}
                  maxLength={4000}
                />
                <button
                  type="submit"
                  className="zuka-send-button"
                  disabled={isLoading || !input.trim()}
                  aria-label="Send message"
                >
                  <Send size={16} />
                </button>
              </form>
            </>
          )}
        </section>
      )}
    </div>,
    document.body,
  );
}

export default ZukaAssistant;
