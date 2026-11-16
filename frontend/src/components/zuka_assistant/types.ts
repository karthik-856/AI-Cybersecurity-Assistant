export type CardType =
  | "incident_summary"
  | "alert_card"
  | "investigation_card"
  | "confirmation_prompt"
  | "action_success"
  | "error_card"
  | "help_card"
  | "list_card"
  | "info_card"
  | "none";

export interface AssistantCard {
  card_type: CardType;
  data: Record<string, any>;
}

export interface PendingAction {
  action: string;
  target_entity: string;
  target_id: string;
  params: Record<string, any>;
  preview_changes: Record<string, any>;
  summary: string;
}

export interface CurrentContext {
  incident_id?: string | null;
  alert_id?: string | null;
  page_route?: string | null;
}

export interface ChatMessageRequest {
  message: string;
  conversation_id?: string | null;
  current_context?: CurrentContext | null;
  confirmed_action?: PendingAction | null;
}

export interface ActionConfirmationRequest {
  action: string;
  target_entity: string;
  target_id: string;
  params?: Record<string, any>;
  conversation_id?: string | null;
}

export interface AssistantResponse {
  reply: string;
  intent: string;
  entity_type: string;
  entity_id?: string | null;
  page_route?: string | null;
  card?: AssistantCard | null;
  confirmation_required: boolean;
  pending_action?: PendingAction | null;
  suggested_prompts: string[];
  context: {
    incident_id?: string | null;
    alert_id?: string | null;
  };
  timestamp: string;
  engine?: string;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
  card?: AssistantCard | null;
  confirmationRequired?: boolean;
  pendingAction?: PendingAction | null;
  suggestedPrompts?: string[];
  isStreaming?: boolean;
}
