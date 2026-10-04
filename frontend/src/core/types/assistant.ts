import { TransportMode } from "./alarm";

export type IntentType =
  | "create_alarm"
  | "update_draft"
  | "explain_schedule"
  | "ask_clarification"
  | "general_query";

export type DraftStatus = "draft" | "confirmed" | "discarded";

export interface ParsedIntent {
  intent_type: IntentType;
  title?: string;
  destination_text?: string;
  destination_place_id?: string;
  required_arrival_time?: string;
  arrival_date?: string;
  timezone?: string;
  preparation_duration_minutes?: number;
  safety_buffer_minutes?: number;
  transport_mode?: TransportMode;
  missing_fields: string[];
  ambiguities: string[];
  confidence: number;
  explanation?: string;
}

export interface AlarmDraft {
  id: string;
  user_id: string | number;
  conversation_id?: string;
  title: string;
  destination_text: string;
  destination_id?: string;
  destination_address?: string;
  destination_lat?: number;
  destination_lng?: number;
  destination_place_id?: string;
  destination_latitude?: number;
  destination_longitude?: number;
  arrival_time: string;
  arrival_date?: string;
  preparation_time: number;
  safety_buffer: number;
  transportation_mode: TransportMode;
  timezone: string;
  calculated_wake_time?: string;
  calculated_leave_time?: string;
  recommended_wake_time?: string;
  recommended_leave_time?: string;
  planned_arrival_time?: string;
  travel_duration_minutes: number;
  estimated_travel_duration?: number;
  estimated_distance_meters?: number;
  traffic_delay_minutes: number;
  status: DraftStatus;
  explanation?: string;
  grounded_explanation?: string;
  idempotency_key?: string;
  created_at: string;
  updated_at: string;
}

export interface AssistantMessage {
  id: string;
  conversation_id?: string;
  role: "user" | "assistant" | "system";
  content: string;
  metadata_json?: string;
  created_at?: string;
}

export interface AssistantConversation {
  id: string;
  user_id: string;
  title: string;
  messages: AssistantMessage[];
  created_at: string;
  updated_at: string;
}

export interface AssistantChatRequest {
  message: string;
  conversation_id?: string;
  draft_id?: string;
  client_timezone?: string;
  origin_lat?: number;
  origin_lng?: number;
}

export interface AssistantChatResponse {
  conversation_id: string;
  message?: AssistantMessage;
  reply?: string;
  parsed_intent: ParsedIntent;
  draft?: AlarmDraft | null;
  requires_clarification: boolean;
  missing_fields: string[];
  clarification_questions: string[];
  provider: string;
}

export interface AlarmDraftUpdateRequest {
  title?: string;
  destination_text?: string;
  arrival_time?: string;
  arrival_date?: string;
  preparation_time?: number;
  safety_buffer?: number;
  transportation_mode?: TransportMode;
  timezone?: string;
}

export interface PersonalizationPreferences {
  user_id: string | number;
  default_transportation: TransportMode;
  default_transportation_mode?: TransportMode;
  default_preparation_time: number;
  default_safety_buffer: number;
  assistant_response_style: "concise" | "detailed" | "direct" | "casual" | "friendly";
  save_conversation_history: boolean;
  use_alarm_history_suggestions: boolean;
  weather_buffer_enabled: boolean;
  calendar_sync_enabled: boolean;
}

export interface PersonalizationUpdateRequest {
  default_transportation?: TransportMode;
  default_transportation_mode?: TransportMode;
  default_preparation_time?: number;
  default_safety_buffer?: number;
  assistant_response_style?: string;
  save_conversation_history?: boolean;
  use_alarm_history_suggestions?: boolean;
  weather_buffer_enabled?: boolean;
  calendar_sync_enabled?: boolean;
}

export interface AssistantStatus {
  status: "online" | "degraded" | "offline" | "fallback";
  provider: string;
  model: string;
  fallback_available?: boolean;
  features?: string[];
}
