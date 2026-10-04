import apiClient from "./apiClient";
import {
  AlarmDraft,
  AlarmDraftUpdateRequest,
  AssistantChatRequest,
  AssistantChatResponse,
  AssistantConversation,
  AssistantStatus,
  PersonalizationPreferences,
  PersonalizationUpdateRequest,
} from "../types/assistant";
import { Alarm } from "../types/alarm";

export class AssistantApiClient {
  async sendMessage(request: AssistantChatRequest): Promise<AssistantChatResponse> {
    const response = await apiClient.post<AssistantChatResponse>("/assistant/chat", request);
    return response.data;
  }

  async getDraft(draftId: string): Promise<AlarmDraft> {
    const response = await apiClient.get<AlarmDraft>(`/assistant/drafts/${draftId}`);
    return response.data;
  }

  async updateDraft(draftId: string, data: AlarmDraftUpdateRequest): Promise<AlarmDraft> {
    const response = await apiClient.patch<AlarmDraft>(`/assistant/drafts/${draftId}`, data);
    return response.data;
  }

  async confirmDraft(draftId: string, idempotencyKey?: string): Promise<Alarm> {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers["X-Idempotency-Key"] = idempotencyKey;
    }
    const response = await apiClient.post<Alarm>(
      `/assistant/drafts/${draftId}/confirm`,
      { idempotency_key: idempotencyKey },
      { headers }
    );
    return response.data;
  }

  async discardDraft(draftId: string): Promise<AlarmDraft> {
    const response = await apiClient.post<AlarmDraft>(`/assistant/drafts/${draftId}/discard`);
    return response.data;
  }

  async listConversations(skip = 0, limit = 50): Promise<AssistantConversation[]> {
    const response = await apiClient.get<AssistantConversation[]>("/assistant/conversations", {
      params: { skip, limit },
    });
    return response.data;
  }

  async getConversation(id: string): Promise<AssistantConversation> {
    const response = await apiClient.get<AssistantConversation>(`/assistant/conversations/${id}`);
    return response.data;
  }

  async deleteConversation(id: string): Promise<void> {
    await apiClient.delete(`/assistant/conversations/${id}`);
  }

  async deleteAllConversations(): Promise<{ message: string; count: number }> {
    const response = await apiClient.delete<{ message: string; count: number }>("/assistant/conversations");
    return response.data;
  }

  async getStatus(): Promise<AssistantStatus> {
    const response = await apiClient.get<AssistantStatus>("/assistant/status");
    return response.data;
  }

  async getPersonalization(): Promise<PersonalizationPreferences> {
    const response = await apiClient.get<PersonalizationPreferences>("/personalization");
    return response.data;
  }

  async updatePersonalization(data: PersonalizationUpdateRequest): Promise<PersonalizationPreferences> {
    const response = await apiClient.patch<PersonalizationPreferences>("/personalization", data);
    return response.data;
  }

  async resetPersonalization(): Promise<PersonalizationPreferences> {
    const response = await apiClient.post<PersonalizationPreferences>("/personalization/reset");
    return response.data;
  }
}

export const assistantApiClient = new AssistantApiClient();
