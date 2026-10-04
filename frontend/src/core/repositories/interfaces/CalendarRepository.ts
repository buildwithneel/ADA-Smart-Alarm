import {
  CalendarConnection,
  CalendarEvent,
  CreateAlarmFromEventRequest,
  ProposeAlarmResponse,
} from "@/core/types/calendar";

export interface ICalendarRepository {
  listConnections(): Promise<CalendarConnection[]>;
  getAuthUrl(redirectUri?: string): Promise<{ authorization_url: string; provider: string }>;
  callback(code: string, state: string, redirectUri?: string): Promise<CalendarConnection>;
  disconnect(connectionId: string): Promise<void>;
  sync(connectionId: string): Promise<any>;
  listEvents(): Promise<CalendarEvent[]>;
  proposeAlarm(eventId: string): Promise<ProposeAlarmResponse>;
  createAlarmFromEvent(eventId: string, payload: CreateAlarmFromEventRequest): Promise<any>;
}
