import { API_BASE_URL } from "./config";

export interface ActionButton {
  label: string;
  action: "execute_command" | "navigate" | "prompt";
  payload: string;
  variant: "primary" | "secondary" | "danger" | "success";
}

export interface ActionCard {
  title: string;
  subtitle?: string | null;
  badge?: string | null;
  badge_variant?: "critical" | "high" | "medium" | "low" | "success" | "info" | null;
  fields: Array<{ label: string; value: string }>;
  actions: ActionButton[];
}

export interface ActionTable {
  headers: string[];
  rows: string[][];
  total_count: number;
  actions: ActionButton[];
}

export interface ConfirmationPrompt {
  confirmation_token: string;
  prompt: string;
  warning: string;
  confirm_command: string;
  cancel_command: string;
}

export interface ParsedIntent {
  intent: string;
  entity?: string | null;
  id?: number | string | null;
  params: Record<string, unknown>;
  confidence: number;
  source: "rule" | "llm_fallback" | "unknown";
}

export interface ChatResponse {
  reply: string;
  intent?: ParsedIntent | null;
  cards: ActionCard[];
  table?: ActionTable | null;
  quick_chips: string[];
  confirmation?: ConfirmationPrompt | null;
  execution_time_ms: number;
}

export interface CommandSuggestion {
  label: string;
  description: string;
  category: string;
}

export async function sendAssistantMessage(payload: {
  message: string;
  confirmed?: boolean;
  confirmation_token?: string | null;
}): Promise<ChatResponse> {
  const token = localStorage.getItem("zuka_access_token");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}/api/assistant-v2/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      message: payload.message,
      confirmed: !!payload.confirmed,
      confirmation_token: payload.confirmation_token || null,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Assistant request failed with status ${response.status}`,
    );
  }

  return response.json();
}

export async function fetchCommandSuggestions(): Promise<CommandSuggestion[]> {
  const token = localStorage.getItem("zuka_access_token");
  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/assistant-v2/suggestions`, {
      method: "GET",
      headers,
    });
    if (response.ok) {
      const data = await response.json();
      return data.suggestions || [];
    }
  } catch {
    // Return fallback list if network is down
  }

  return [
    { label: "show alert <id>", description: "Inspect alert flow & SHAP", category: "Alerts" },
    { label: "list alerts", description: "Display recent detections", category: "Alerts" },
    { label: "list critical alerts", description: "Filter by critical severity", category: "Alerts" },
    { label: "acknowledge alert <id>", description: "Acknowledge an alert", category: "Alerts" },
    { label: "show incident <id>", description: "View incident triage", category: "Incidents" },
    { label: "list incidents", description: "List active incidents", category: "Incidents" },
    { label: "list users", description: "List all user accounts", category: "Users" },
    { label: "system status", description: "Telemetry & system health", category: "System" },
    { label: "help", description: "Command catalog", category: "General" },
  ];
}
