import { sessionFetch } from "./sessionFetch";
import { getErrorMessage } from "./errors";
import { API_BASE_URL } from "./config";

export interface LoginRequest {
  username_or_email: string;
  password: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface NetworkEvent {
  id: number;
  event_time: string;
  source_ip: string | null;
  destination_ip: string | null;
  source_port: number | null;
  destination_port: number | null;
  protocol: string | null;
  direction: string | null;
  packets: number | null;
  bytes_count: number | null;
  flow_duration_ms: number | null;
  interface_name: string | null;
  capture_source: string;
  event_type: string;
  description: string | null;
  extra_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface NetworkStats {
  total_events: number;
  unique_source_ips: number;
  unique_destination_ips: number;
  tcp_events: number;
  udp_events: number;
  other_protocol_events: number;
}

export interface CaptureStatus {
  running: boolean;
  interface: string;
  packet_count: number;
  flow_count: number;
  active_flows: number;
  started_at: string | null;
  last_error: string | null;
}

async function readResponse(response: Response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    try {
      return await response.json();
    } catch {
      return {};
    }
  }

  const text = await response.text();

  return {
    detail: text,
  };
}

function getToken(): string | null {
  return localStorage.getItem("zuka_access_token");
}

async function authenticatedFetch(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  const token = getToken();

  const headers = new Headers(options.headers || {});

  headers.set("Accept", "application/json");

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await sessionFetch(url, {
    ...options,
    headers,
  });

  return response;
}

export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  const controller = new AbortController();

  const timeout = window.setTimeout(() => {
    controller.abort();
  }, 8000);

  try {
    const response = await sessionFetch(`${API_BASE_URL}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(credentials),
      signal: controller.signal,
    });

    const data = await readResponse(response);

    if (!response.ok) {
      throw new Error(
        getErrorMessage(
          data,
          `Login failed. Server returned ${response.status}.`,
        ),
      );
    }

    if (!data?.access_token) {
      throw new Error(
        "The authentication server did not return an access token.",
      );
    }

    return data as LoginResponse;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(
        "The server is taking longer than expected. Please try again.",
        { cause: error },
      );
    }

    if (error instanceof TypeError) {
      throw new Error("Unable to connect. Please try again shortly.", {
        cause: error,
      });
    }

    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function getNetworkEvents(limit = 100): Promise<NetworkEvent[]> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/network/events?limit=${limit}`,
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to load network events. Server returned ${response.status}.`,
      ),
    );
  }

  return data as NetworkEvent[];
}

export async function getNetworkStats(): Promise<NetworkStats> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/network/stats`,
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to load network statistics. Server returned ${response.status}.`,
      ),
    );
  }

  return data as NetworkStats;
}

export async function getCaptureStatus(): Promise<CaptureStatus> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/network/capture/status`,
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to load capture status. Server returned ${response.status}.`,
      ),
    );
  }

  return data as CaptureStatus;
}

export async function startLiveCapture(): Promise<CaptureStatus> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/network/capture/start`,
    {
      method: "POST",
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to start live capture. Server returned ${response.status}.`,
      ),
    );
  }

  return data as CaptureStatus;
}

export async function stopLiveCapture(): Promise<CaptureStatus> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/network/capture/stop`,
    {
      method: "POST",
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to stop live capture. Server returned ${response.status}.`,
      ),
    );
  }

  return data as CaptureStatus;
}
// ============================================================
// INCIDENT MANAGEMENT
// ============================================================

export interface Incident {
  id: number;
  incident_id: string;
  alert_id: string;
  title: string;
  description: string | null;
  severity: string;
  priority: string;
  status: string;
  assigned_to_id: number | null;
  assigned_to_username?: string | null;
  assigned_analyst?: string | null;
  escalation_level: number;
  escalation_count: number;
  resolution_summary: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
  source_ip?: string | null;
  destination_ip?: string | null;
  source_port?: number | null;
  destination_port?: number | null;
  protocol?: string | null;
  attack_class?: string | null;
  confidence?: number | null;
  dataset_name?: string | null;
  investigation_id?: string | null;
  investigation_status?: string | null;
  investigation_conclusion?: string | null;
  affected_asset?: string | null;
  detection_result?: Record<string, unknown> | null;
  xai_explanation?: Record<string, unknown> | null;
}

export interface IncidentListResponse {
  items: Incident[];
  total: number;
}

export interface IncidentStatusUpdate {
  status: string;
  resolution_summary?: string;
}

export interface IncidentAssignmentUpdate {
  assigned_to_id: number | null;
}

export interface IncidentEscalationUpdate {
  reason?: string;
}

export async function getIncidents(params?: {
  status?: string;
  severity?: string;
  priority?: string;
  assigned_to_id?: number;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<IncidentListResponse> {
  const searchParams = new URLSearchParams();

  if (params?.status) {
    searchParams.set("status", params.status);
  }

  if (params?.severity) {
    searchParams.set("severity", params.severity);
  }

  if (params?.priority) {
    searchParams.set("priority", params.priority);
  }

  if (params?.assigned_to_id !== undefined) {
    searchParams.set("assigned_to_id", String(params.assigned_to_id));
  }

  if (params?.search) {
    searchParams.set("search", params.search);
  }

  searchParams.set("limit", String(params?.limit ?? 100));

  searchParams.set("offset", String(params?.offset ?? 0));

  const query = searchParams.toString();

  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/incidents?${query}`,
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to load incidents. Server returned ${response.status}.`,
      ),
    );
  }

  return data as IncidentListResponse;
}

export async function getIncident(incidentId: string): Promise<Incident> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/incidents/${encodeURIComponent(incidentId)}`,
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to load incident. Server returned ${response.status}.`,
      ),
    );
  }

  return data as Incident;
}

export async function updateIncidentStatus(
  incidentId: string,
  payload: IncidentStatusUpdate,
): Promise<Incident> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/incidents/${encodeURIComponent(incidentId)}/status`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to update incident status. Server returned ${response.status}.`,
      ),
    );
  }

  return data as Incident;
}

export async function updateIncidentAssignment(
  incidentId: string,
  payload: IncidentAssignmentUpdate,
): Promise<Incident> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/incidents/${encodeURIComponent(incidentId)}/assignment`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to update incident assignment. Server returned ${response.status}.`,
      ),
    );
  }

  return data as Incident;
}

export async function escalateIncident(
  incidentId: string,
  payload: IncidentEscalationUpdate = {},
): Promise<Incident> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/incidents/${encodeURIComponent(incidentId)}/escalate`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to escalate incident. Server returned ${response.status}.`,
      ),
    );
  }

  return data as Incident;
}

export async function addIncidentNote(
  incidentId: string,
  note: string,
): Promise<Incident> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/incidents/${encodeURIComponent(incidentId)}/notes`,
    {
      method: "POST",
      body: JSON.stringify({ note }),
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to add note to incident. Server returned ${response.status}.`,
      ),
    );
  }

  return data as Incident;
}

// ============================================================
// INVESTIGATION MANAGEMENT
// ============================================================

export interface Investigation {
  id: number;
  investigation_id: string;
  incident_id: string;
  status: string;
  conclusion: string | null;
  analyst_notes: string | null;
  findings?: string | null;
  evidence_reviewed?: string | null;
  investigation_steps?: string | null;
  impact_assessment?: string | null;
  remediation?: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  alert_id?: string;
  source_ip?: string;
  destination_ip?: string;
}

export interface InvestigationListResponse {
  items: Investigation[];
  total: number;
}

export interface InvestigationCreate {
  incident_id: string;
}

export interface InvestigationStatusUpdate {
  status: string;
}

export interface InvestigationNotesUpdate {
  analyst_notes: string | null;
}

export interface InvestigationConclusionUpdate {
  conclusion: string | null;
}

export async function getInvestigations(params?: {
  status?: string;
  incident_id?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<InvestigationListResponse> {
  const searchParams = new URLSearchParams();

  if (params?.status) {
    searchParams.set("status", params.status);
  }

  if (params?.incident_id) {
    searchParams.set("incident_id", params.incident_id);
  }

  if (params?.search) {
    searchParams.set("search", params.search);
  }

  searchParams.set("limit", String(params?.limit ?? 100));

  searchParams.set("offset", String(params?.offset ?? 0));

  const query = searchParams.toString();

  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/investigations?${query}`,
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to load investigations. Server returned ${response.status}.`,
      ),
    );
  }

  return data as InvestigationListResponse;
}

export async function getInvestigation(
  investigationId: string,
): Promise<Investigation> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/investigations/${encodeURIComponent(investigationId)}`,
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to load investigation. Server returned ${response.status}.`,
      ),
    );
  }

  return data as Investigation;
}

export async function createInvestigation(
  payload: InvestigationCreate,
): Promise<Investigation> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/investigations`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to create investigation. Server returned ${response.status}.`,
      ),
    );
  }

  return data as Investigation;
}

export async function updateInvestigationStatus(
  investigationId: string,
  payload: InvestigationStatusUpdate,
): Promise<Investigation> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/investigations/${encodeURIComponent(
      investigationId,
    )}/status`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to update investigation status. Server returned ${response.status}.`,
      ),
    );
  }

  return data as Investigation;
}

export async function updateInvestigationNotes(
  investigationId: string,
  payload: InvestigationNotesUpdate,
): Promise<Investigation> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/investigations/${encodeURIComponent(
      investigationId,
    )}/notes`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to update investigation notes. Server returned ${response.status}.`,
      ),
    );
  }

  return data as Investigation;
}

export async function updateInvestigationConclusion(
  investigationId: string,
  payload: InvestigationConclusionUpdate,
): Promise<Investigation> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/investigations/${encodeURIComponent(
      investigationId,
    )}/conclusion`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to update investigation conclusion. Server returned ${response.status}.`,
      ),
    );
  }

  return data as Investigation;
}

export async function updateInvestigationFindings(
  investigationId: string,
  findings: string,
): Promise<Investigation> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/investigations/${encodeURIComponent(
      investigationId,
    )}/findings`,
    {
      method: "PATCH",
      body: JSON.stringify({ findings }),
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to update investigation findings. Server returned ${response.status}.`,
      ),
    );
  }

  return data as Investigation;
}

export interface InvestigationWorkspaceData {
  analyst_notes?: string;
  findings?: string;
  conclusion?: string;
  evidence_reviewed?: string;
  investigation_steps?: string;
  impact_assessment?: string;
  remediation?: string;
}

export async function updateInvestigationWorkspace(
  investigationId: string,
  payload: InvestigationWorkspaceData,
): Promise<Investigation> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/investigations/${encodeURIComponent(
      investigationId,
    )}/workspace`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to save investigation workspace. Server returned ${response.status}.`,
      ),
    );
  }

  return data as Investigation;
}

export interface AnalystAction {
  id: number;
  action_id: string;
  analyst_id: number | null;
  incident_id: string | null;
  investigation_id: string | null;
  action_type: string;
  description: string;
  result: string | null;
  created_at: string;
}

export interface AnalystActionListResponse {
  items: AnalystAction[];
  total: number;
}

export async function getAnalystActions(params?: {
  incident_id?: string;
  investigation_id?: string;
  action_type?: string;
  limit?: number;
}): Promise<AnalystActionListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.incident_id) searchParams.set("incident_id", params.incident_id);
  if (params?.investigation_id)
    searchParams.set("investigation_id", params.investigation_id);
  if (params?.action_type) searchParams.set("action_type", params.action_type);
  if (params?.limit) searchParams.set("limit", String(params.limit));

  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/analyst-actions?${searchParams.toString()}`,
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to load audit actions. Server returned ${response.status}.`,
      ),
    );
  }

  return data as AnalystActionListResponse;
}
// ============================================================
// ALERT CENTER
// ============================================================

export type AlertStatus =
  "OPEN" | "ACKNOWLEDGED" | "INVESTIGATING" | "RESOLVED";

export type AlertSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";

export interface ShapFeature {
  feature: string;
  direction: string;
  shap_value: number;
  feature_value: number;
}

export interface Alert {
  id: number;
  alert_id: string;
  detected_at: string;
  predicted_class: string;
  confidence: number;
  severity: AlertSeverity;
  status: AlertStatus;

  source_ip: string | null;
  destination_ip: string | null;
  source_port: number | null;
  destination_port: number | null;
  protocol: string | null;

  dataset_name: string | null;
  capture_source: string | null;

  description: string | null;

  detection_result: Record<string, unknown> | null;

  xai_explanation: {
    method?: string;
    input_source?: string;
    predicted_class?: string;
    confidence?: number;
    top_contributions?: ShapFeature[];
    supporting_features?: ShapFeature[];
    opposing_features?: ShapFeature[];
  } | null;

  created_at: string;
  updated_at: string;
  incident_id?: string | null;
  investigation_id?: string | null;
}

export interface AlertListResponse {
  alerts: Alert[];
  total: number;
}

export interface AlertStatusUpdate {
  status: AlertStatus;
}

export async function getAlerts(params?: {
  status?: AlertStatus;
  severity?: AlertSeverity;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<AlertListResponse> {
  const searchParams = new URLSearchParams();

  if (params?.status) {
    searchParams.set("status", params.status);
  }

  if (params?.severity) {
    searchParams.set("severity", params.severity);
  }

  if (params?.search) {
    searchParams.set("search", params.search);
  }

  searchParams.set("limit", String(params?.limit ?? 100));

  searchParams.set("offset", String(params?.offset ?? 0));

  const query = searchParams.toString();

  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/alerts?${query}`,
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to load alerts. Server returned ${response.status}.`,
      ),
    );
  }

  return data as AlertListResponse;
}

export async function getAlert(alertId: string): Promise<Alert> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/alerts/${encodeURIComponent(alertId)}`,
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to load alert. Server returned ${response.status}.`,
      ),
    );
  }

  return data as Alert;
}

export async function generateAlertExplanation(
  alertId: string,
): Promise<Alert> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/alerts/${encodeURIComponent(alertId)}/explanation`,
    { method: "POST", signal: AbortSignal.timeout(120000) },
  );
  const data = await readResponse(response);
  if (!response.ok)
    throw new Error(
      getErrorMessage(data, "Unable to generate this explanation."),
    );
  return data as Alert;
}

export interface AlertStats {
  total: number;
  open: number;
  acknowledged: number;
  investigating: number;
  resolved: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
  active_critical?: number;
  active_high?: number;
}

export async function getAlertStats(): Promise<AlertStats> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/alerts/stats`);

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to load alert statistics. Server returned ${response.status}.`,
      ),
    );
  }

  return data as AlertStats;
}

export async function updateAlertStatus(
  alertId: string,
  payload: AlertStatusUpdate,
): Promise<Alert> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/alerts/${encodeURIComponent(alertId)}/status`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to update alert status. Server returned ${response.status}.`,
      ),
    );
  }

  return data as Alert;
}

export async function acknowledgeAndInvestigateAlert(
  alertId: string,
  analystNotes?: string,
): Promise<{
  success: boolean;
  message: string;
  alert_id: string;
  incident_id: string;
  investigation_id: string;
  status: string;
  investigation_status: string;
}> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/assistant/alerts/acknowledge-and-investigate`,
    {
      method: "POST",
      body: JSON.stringify({
        alert_id: alertId,
        analyst_notes: analystNotes || undefined,
      }),
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to acknowledge and escalate alert. Server returned ${response.status}.`,
      ),
    );
  }

  return data as Awaited<ReturnType<typeof acknowledgeAndInvestigateAlert>>;
}
// ============================================================
// DATASET REPLAY
// ============================================================

export interface ReplayResult {
  row_index: number;
  unified_row_id: string | number | null;
  dataset_name: string | null;
  predicted_class: string | null;
  confidence: number | null;
  severity: string | null;
  is_attack: boolean;
  network_event_id: number;
  alert_id: string | null;
}

export interface ReplayResponse {
  status: string;
  message: string;
  row_index: number;
  next_row_index: number;
  processed: boolean;
  result: ReplayResult | null;
  incident: {
    id: number;
    incident_id: string;
    alert_id: string;
    severity: string;
    priority: string;
    status: string;
  } | null;
}

export async function processDemoEvent(
  rowIndex: number,
): Promise<ReplayResponse> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/replay/demo`, {
    method: "POST",
    body: JSON.stringify({ row_index: rowIndex }),
    signal: AbortSignal.timeout(120000),
  });
  const data = await readResponse(response);
  if (!response.ok)
    throw new Error(
      getErrorMessage(data, "Unable to process the demonstration sample."),
    );
  return data as ReplayResponse;
}

export interface ServerReplayStatus {
  enabled: boolean;
  running: boolean;
  interval_seconds: number;
  dataset_rows: number | null;
  processed_events: number;
  generated_alerts: number;
  last_processed_at: string | null;
  error: string | null;
}

export async function getServerReplayStatus(): Promise<ServerReplayStatus> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/replay/status`,
    {
      signal: AbortSignal.timeout(10000),
    },
  );
  if (!response.ok)
    throw new Error("Unable to check backend detection status.");
  return response.json();
}

export async function replayNext(
  rowIndex: number,
  includeXai = true,
): Promise<ReplayResponse> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/replay/next`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      row_index: rowIndex,
      include_xai: includeXai,
    }),
  });

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Dataset replay failed. Server returned ${response.status}.`,
      ),
    );
  }

  return data as ReplayResponse;
}

// ============================================================
// PERSISTENT WEB PUSH
// ============================================================

export interface PushPublicKeyResponse {
  public_key: string;
}

export async function getPushStatus(): Promise<{ configured: boolean }> {
  const response = await fetch(`${API_BASE_URL}/api/push/status`, {
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok)
    throw new Error("Unable to check background notification setup.");
  return response.json();
}

export async function sendPushTest(endpoint: string): Promise<void> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/push/test`, {
    method: "POST",
    body: JSON.stringify({ endpoint }),
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok)
    throw new Error(
      getErrorMessage(
        await readResponse(response),
        "The test notification could not be delivered.",
      ),
    );
}

export interface PushSubscriptionPayload {
  endpoint: string;
  critical_alerts?: boolean;
  high_alerts?: boolean;
  notification_preview?: boolean;
  keys?: {
    p256dh?: string;
    auth?: string;
  };
}

export async function getPushPublicKey(): Promise<PushPublicKeyResponse> {
  const response = await sessionFetch(`${API_BASE_URL}/api/push/public-key`, {
    headers: {
      Accept: "application/json",
    },
    signal: AbortSignal.timeout(10000),
  });

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to load Web Push configuration. Server returned ${response.status}.`,
      ),
    );
  }

  return data as PushPublicKeyResponse;
}

export async function savePushSubscription(
  subscription: PushSubscriptionPayload,
): Promise<{ status: string; subscription_id: number }> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/push/subscribe`,
    {
      method: "POST",
      body: JSON.stringify(subscription),
      signal: AbortSignal.timeout(10000),
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to save Web Push subscription. Server returned ${response.status}.`,
      ),
    );
  }

  return data as {
    status: string;
    subscription_id: number;
  };
}

export async function deletePushSubscription(
  subscription: PushSubscriptionPayload,
): Promise<{ status: string }> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/push/subscribe`,
    {
      method: "DELETE",
      body: JSON.stringify(subscription),
      signal: AbortSignal.timeout(5000),
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to remove Web Push subscription. Server returned ${response.status}.`,
      ),
    );
  }

  return data as { status: string };
}

// ============================================================
// DEFENSE DEPARTMENT
// ============================================================

export interface DefenseInvestigation {
  investigation_id: string;
  incident_id: string;
  incident_title: string;
  incident_severity: string;
  incident_priority: string;
  investigation_status: string;
  started_at: string | null;
  analyst_notes: string;
  conclusion: string;
  alert_id: string | null;
  predicted_class: string;
  confidence_pct: number;
  source_ip: string;
  destination_ip: string;
  source_port: string | number;
  destination_port: string | number;
  protocol: string;
  detection_time: string | null;
  diagnosis: string;
  defense_actions_count: number;
  has_real_ips?: boolean;
  telemetry_source?: string;
}

export interface ApplyDefensePayload {
  investigation_id: string;
  incident_id: string;
  action_type: string;
  action_label: string;
  rationale: string;
  defense_note: string;
}

export interface ApplyDefenseResponse {
  status: string;
  message: string;
  investigation_id: string;
  incident_id: string;
  analyst_action_id: number;
  updated_notes: string;
}

export async function getOpenDefenseInvestigations(): Promise<
  DefenseInvestigation[]
> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/defense/open-investigations`,
    {
      headers: {
        Accept: "application/json",
      },
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to load open investigations for defense. Server returned ${response.status}.`,
      ),
    );
  }

  return data as DefenseInvestigation[];
}

export async function applyDefenseAction(
  payload: ApplyDefensePayload,
): Promise<ApplyDefenseResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/defense/apply-action`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );

  const data = await readResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        `Unable to apply defense action. Server returned ${response.status}.`,
      ),
    );
  }

  return data as ApplyDefenseResponse;
}
