import apiClient from "@/core/api/apiClient";
import {
  CalendarConnection,
  CalendarEvent,
  CreateAlarmFromEventRequest,
  ProposeAlarmResponse,
} from "@/core/types/calendar";
import { ICalendarRepository } from "../interfaces/CalendarRepository";

export class ApiCalendarRepository implements ICalendarRepository {
  async listConnections(): Promise<CalendarConnection[]> {
    const response = await apiClient.get<CalendarConnection[]>("/calendar/connections");
    return response.data;
  }

  async getAuthUrl(redirectUri?: string): Promise<{ authorization_url: string; provider: string }> {
    const params: Record<string, any> = {};
    if (redirectUri) params.redirect_uri = redirectUri;
    const response = await apiClient.post<{ authorization_url: string; provider: string }>(
      "/calendar/connections/auth-url",
      null,
      { params }
    );
    return response.data;
  }

  async callback(code: string, state: string, redirectUri?: string): Promise<CalendarConnection> {
    const response = await apiClient.post<CalendarConnection>("/calendar/connections/callback", {
      code,
      state,
      redirect_uri: redirectUri,
    });
    return response.data;
  }

  async disconnect(connectionId: string): Promise<void> {
    await apiClient.delete(`/calendar/connections/${connectionId}`);
  }

  async sync(connectionId: string): Promise<any> {
    const response = await apiClient.post(`/calendar/connections/${connectionId}/sync`);
    return response.data;
  }

  async listEvents(): Promise<CalendarEvent[]> {
    const response = await apiClient.get<CalendarEvent[]>("/calendar/events");
    return response.data;
  }

  async proposeAlarm(eventId: string): Promise<ProposeAlarmResponse> {
    const response = await apiClient.get<ProposeAlarmResponse>(
      `/calendar/events/${eventId}/propose-alarm`
    );
    return response.data;
  }

  async createAlarmFromEvent(
    eventId: string,
    payload: CreateAlarmFromEventRequest
  ): Promise<any> {
    const response = await apiClient.post(
      `/calendar/events/${eventId}/create-alarm`,
      payload
    );
    return response.data;
  }
}
