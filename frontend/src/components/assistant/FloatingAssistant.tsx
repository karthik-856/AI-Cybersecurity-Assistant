import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  Bot,
  Send,
  Sparkles,
  Trash2,
  User,
  X,
} from "lucide-react";
import type {
  ActionButton,
  ActionCard,
  ActionTable,
  CommandSuggestion,
  ConfirmationPrompt,
} from "../../services/assistantV2";
import {
  fetchCommandSuggestions,
  sendAssistantMessage,
} from "../../services/assistantV2";
import "./FloatingAssistant.css";

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
  cards?: ActionCard[];
  table?: ActionTable | null;
  quick_chips?: string[];
  confirmation?: ConfirmationPrompt | null;
  execution_time_ms?: number;
  engine_source?: string;
}

export const FloatingAssistant: React.FC = () => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<CommandSuggestion[]>([]);
  const [filteredSuggestions, setFilteredSuggestions] = useState<CommandSuggestion[]>([]);
  const [activeSuggestionIdx, setActiveSuggestionIdx] = useState(-1);
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load suggestions on mount
  useEffect(() => {
    fetchCommandSuggestions().then(setSuggestions).catch(() => {});
  }, []);

  // Auto-scroll on new message
  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading, isOpen]);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  // Filter autocomplete suggestions
  useEffect(() => {
    const trimmed = input.trim().toLowerCase();
    if (trimmed.length >= 1) {
      const matches = suggestions.filter(
        (s) =>
          s.label.toLowerCase().includes(trimmed) ||
          s.description.toLowerCase().includes(trimmed),
      );
      setFilteredSuggestions(matches.slice(0, 5));
    } else {
      setFilteredSuggestions([]);
    }
    setActiveSuggestionIdx(-1);
  }, [input, suggestions]);

  function getFormattedTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  async function handleSend(
    messageText: string,
    confirmed = false,
    confirmationToken?: string | null,
  ) {
    const text = messageText.trim();
    if (!text || loading) return;

    // Save to history
    setCommandHistory((prev) => [text, ...prev.filter((c) => c !== text)]);
    setHistoryIdx(-1);

    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      sender: "user",
      text,
      timestamp: getFormattedTime(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setFilteredSuggestions([]);
    setLoading(true);

    try {
      const response = await sendAssistantMessage({
        message: text,
        confirmed,
        confirmation_token: confirmationToken,
      });

      const assistantMsg: ChatMessage = {
        id: `ast-${Date.now()}`,
        sender: "assistant",
        text: response.reply,
        timestamp: getFormattedTime(),
        cards: response.cards,
        table: response.table,
        quick_chips: response.quick_chips,
        confirmation: response.confirmation,
        execution_time_ms: response.execution_time_ms,
        engine_source: response.intent?.source,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: "assistant",
        text:
          err instanceof Error
            ? `⚠️ Error: ${err.message}`
            : "⚠️ Unable to execute command. Please verify your connection to ZUKA SOC backend.",
        timestamp: getFormattedTime(),
        quick_chips: ["Help", "System status", "List alerts"],
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    // Autocomplete navigation
    if (filteredSuggestions.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveSuggestionIdx((prev) =>
          prev < filteredSuggestions.length - 1 ? prev + 1 : 0,
        );
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveSuggestionIdx((prev) =>
          prev > 0 ? prev - 1 : filteredSuggestions.length - 1,
        );
        return;
      }
      if (e.key === "Enter" && activeSuggestionIdx >= 0) {
        e.preventDefault();
        const selected = filteredSuggestions[activeSuggestionIdx];
        setInput(selected.label);
        setFilteredSuggestions([]);
        return;
      }
      if (e.key === "Escape") {
        setFilteredSuggestions([]);
        return;
      }
    }

    // Command History navigation (Up/Down arrow)
    if (commandHistory.length > 0) {
      if (e.key === "ArrowUp" && filteredSuggestions.length === 0) {
        e.preventDefault();
        const nextIdx = historyIdx + 1;
        if (nextIdx < commandHistory.length) {
          setHistoryIdx(nextIdx);
          setInput(commandHistory[nextIdx]);
        }
        return;
      }
      if (e.key === "ArrowDown" && filteredSuggestions.length === 0) {
        e.preventDefault();
        const nextIdx = historyIdx - 1;
        if (nextIdx >= 0) {
          setHistoryIdx(nextIdx);
          setInput(commandHistory[nextIdx]);
        } else {
          setHistoryIdx(-1);
          setInput("");
        }
        return;
      }
    }
  }

  function handleActionButtonClick(button: ActionButton) {
    if (button.action === "execute_command") {
      handleSend(button.payload);
    } else if (button.action === "navigate") {
      navigate(button.payload);
      // On mobile, close widget upon navigation
      if (window.innerWidth < 640) {
        setIsOpen(false);
      }
    }
  }

  function handleClearChat() {
    setMessages([]);
  }

  return (
    <>
      {/* Floating Launcher Button */}
      <button
        className="zuka-floating-btn"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label="Open ZUKA Instant Assistant"
        title="Open ZUKA AI Assistant (Sub-10ms Engine)"
      >
        <span className="zuka-floating-pulse" />
        {isOpen ? <X size={26} /> : <Bot size={28} />}
      </button>

      {/* Floating Panel */}
      {isOpen && (
        <aside className="zuka-assistant-panel" aria-label="ZUKA AI Assistant Window">
          {/* Header */}
          <header className="zuka-panel-header">
            <div className="zuka-header-left">
              <div className="zuka-header-avatar">
                <Sparkles size={20} />
              </div>
              <div className="zuka-header-titles">
                <div className="zuka-header-title">
                  ZUKA Assistant
                  <span className="zuka-engine-pill">⚡ Instant</span>
                </div>
                <div className="zuka-header-sub">
                  Rule-based SOC Copilot
                </div>
              </div>
            </div>

            <div className="zuka-header-actions">
              <button
                type="button"
                className="zuka-header-btn"
                onClick={handleClearChat}
                title="Clear Chat History"
                aria-label="Clear chat"
              >
                <Trash2 size={16} />
              </button>
              <button
                type="button"
                className="zuka-header-btn"
                onClick={() => setIsOpen(false)}
                title="Close Assistant"
                aria-label="Close assistant"
              >
                <X size={18} />
              </button>
            </div>
          </header>

          {/* Body */}
          <div className="zuka-panel-body">
            {messages.length === 0 ? (
              <div className="zuka-empty-state">
                <div className="zuka-empty-icon">
                  <Bot size={28} />
                </div>
                <h3>Welcome to ZUKA Assistant</h3>
                <p>
                  Execute fast SOC actions, inspect alerts, triage incidents, and check live
                  telemetry without leaving this page.
                </p>
                <div className="zuka-chips-container" style={{ justifyContent: "center" }}>
                  <button
                    type="button"
                    className="zuka-chip"
                    onClick={() => handleSend("list critical alerts")}
                  >
                    🚨 Critical alerts
                  </button>
                  <button
                    type="button"
                    className="zuka-chip"
                    onClick={() => handleSend("list open incidents")}
                  >
                    🛡️ Open incidents
                  </button>
                  <button
                    type="button"
                    className="zuka-chip"
                    onClick={() => handleSend("system status")}
                  >
                    📊 System status
                  </button>
                  <button
                    type="button"
                    className="zuka-chip"
                    onClick={() => handleSend("help")}
                  >
                    ❓ Help & commands
                  </button>
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div key={msg.id} className={`zuka-message ${msg.sender}`}>
                  <div className="zuka-message-avatar">
                    {msg.sender === "user" ? <User size={15} /> : <Bot size={15} />}
                  </div>

                  <div className="zuka-message-content">
                    {/* Text Bubble */}
                    <div className="zuka-bubble">{msg.text}</div>

                    {/* Result Cards */}
                    {msg.cards && msg.cards.length > 0 && (
                      <div style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%" }}>
                        {msg.cards.map((card, idx) => (
                          <div key={idx} className="zuka-card">
                            <div className="zuka-card-header">
                              <div>
                                <div className="zuka-card-title">{card.title}</div>
                                {card.subtitle && (
                                  <div className="zuka-card-subtitle">{card.subtitle}</div>
                                )}
                              </div>
                              {card.badge && (
                                <span className={`zuka-card-badge ${card.badge_variant || "info"}`}>
                                  {card.badge}
                                </span>
                              )}
                            </div>

                            {card.fields && card.fields.length > 0 && (
                              <div className="zuka-fields-grid">
                                {card.fields.map((f, fIdx) => (
                                  <div key={fIdx} className="zuka-field-item">
                                    <span className="zuka-field-label">{f.label}</span>
                                    <span className="zuka-field-value">{f.value}</span>
                                  </div>
                                ))}
                              </div>
                            )}

                            {card.actions && card.actions.length > 0 && (
                              <div className="zuka-card-actions">
                                {card.actions.map((act, aIdx) => (
                                  <button
                                    key={aIdx}
                                    type="button"
                                    className={`zuka-action-btn ${act.variant}`}
                                    onClick={() => handleActionButtonClick(act)}
                                  >
                                    {act.label}
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Result Table */}
                    {msg.table && (
                      <div className="zuka-table-wrapper">
                        <table className="zuka-chat-table">
                          <thead>
                            <tr>
                              {msg.table.headers.map((h, hIdx) => (
                                <th key={hIdx}>{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {msg.table.rows.map((row, rIdx) => (
                              <tr key={rIdx}>
                                {row.map((cell, cIdx) => (
                                  <td key={cIdx}>{cell}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {msg.table.actions && msg.table.actions.length > 0 && (
                          <div style={{ padding: "6px 10px", background: "#0a1320", borderTop: "1px solid #162337" }}>
                            {msg.table.actions.map((act, aIdx) => (
                              <button
                                key={aIdx}
                                type="button"
                                className={`zuka-action-btn ${act.variant}`}
                                onClick={() => handleActionButtonClick(act)}
                              >
                                {act.label}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Safety Confirmation Box */}
                    {msg.confirmation && (
                      <div className="zuka-confirmation-card">
                        <div className="zuka-conf-header">
                          <AlertTriangle size={17} />
                          <span>Safety Confirmation Required</span>
                        </div>
                        <div className="zuka-conf-prompt">{msg.confirmation.prompt}</div>
                        <div className="zuka-conf-warning">{msg.confirmation.warning}</div>
                        <div className="zuka-conf-buttons">
                          <button
                            type="button"
                            className="zuka-action-btn danger"
                            onClick={() =>
                              handleSend(
                                msg.confirmation!.confirm_command,
                                true,
                                msg.confirmation!.confirmation_token,
                              )
                            }
                          >
                            Yes, Confirm & Delete
                          </button>
                          <button
                            type="button"
                            className="zuka-action-btn secondary"
                            onClick={() => handleSend("cancel")}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Quick Chips */}
                    {msg.quick_chips && msg.quick_chips.length > 0 && (
                      <div className="zuka-chips-container">
                        {msg.quick_chips.map((chip, cIdx) => (
                          <button
                            key={cIdx}
                            type="button"
                            className="zuka-chip"
                            onClick={() => handleSend(chip)}
                          >
                            {chip}
                          </button>
                        ))}
                      </div>
                    )}

                    {/* Meta info */}
                    <div className="zuka-message-meta">
                      <span>{msg.timestamp}</span>
                      {msg.execution_time_ms !== undefined && (
                        <span className="zuka-time-badge">
                          ⚡ {msg.execution_time_ms}ms ({msg.engine_source || "rule"})
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}

            {/* Typing indicator */}
            {loading && (
              <div className="zuka-message assistant">
                <div className="zuka-message-avatar">
                  <Bot size={15} />
                </div>
                <div className="zuka-bubble">
                  <div className="zuka-typing-indicator">
                    <span className="zuka-typing-dot" />
                    <span className="zuka-typing-dot" />
                    <span className="zuka-typing-dot" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Autocomplete Suggestions Popover */}
          {filteredSuggestions.length > 0 && (
            <div className="zuka-autocomplete-list">
              {filteredSuggestions.map((item, idx) => (
                <div
                  key={idx}
                  className={`zuka-autocomplete-item ${idx === activeSuggestionIdx ? "active" : ""}`}
                  onClick={() => {
                    setInput(item.label);
                    setFilteredSuggestions([]);
                    inputRef.current?.focus();
                  }}
                >
                  <span className="zuka-autocomplete-label">{item.label}</span>
                  <span className="zuka-autocomplete-desc">{item.description}</span>
                </div>
              ))}
            </div>
          )}

          {/* Footer Input */}
          <footer className="zuka-panel-footer">
            <form
              className="zuka-input-form"
              onSubmit={(e) => {
                e.preventDefault();
                handleSend(input);
              }}
            >
              <input
                ref={inputRef}
                type="text"
                className="zuka-input"
                placeholder="Type a command (e.g. 'show alert 12', 'help')..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
                autoComplete="off"
              />
              <button
                type="submit"
                className="zuka-send-btn"
                disabled={loading || !input.trim()}
                aria-label="Send command"
              >
                <Send size={15} />
              </button>
            </form>
          </footer>
        </aside>
      )}
    </>
  );
};

export default FloatingAssistant;
