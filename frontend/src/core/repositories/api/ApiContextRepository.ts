import apiClient from "@/core/api/apiClient";
import { ContextSummary, WeatherData } from "@/core/types/context";
import { IContextRepository } from "../interfaces/ContextRepository";

export class ApiContextRepository implements IContextRepository {
  async getWeather(lat: number, lng: number, targetTime?: string): Promise<WeatherData> {
    const params: Record<string, any> = { lat, lng };
    if (targetTime) {
      params.target_time = targetTime;
    }
    const response = await apiClient.get<WeatherData>("/context/weather", { params });
    return response.data;
  }

  async getAlarmContext(alarmUuid: string): Promise<ContextSummary> {
    const response = await apiClient.get<ContextSummary>(`/context/alarm/${alarmUuid}`);
    return response.data;
  }

  async applyWeatherBuffer(
    alarmUuid: string,
    bufferMinutes?: number,
    expectedVersion?: number
  ): Promise<any> {
    const payload: Record<string, any> = {};
    if (bufferMinutes !== undefined) payload.buffer_minutes = bufferMinutes;
    if (expectedVersion !== undefined) payload.expected_version = expectedVersion;

    const response = await apiClient.post(`/context/alarm/${alarmUuid}/apply-weather-buffer`, payload);
    return response.data;
  }

  async getContextPreferences(): Promise<{
    weather_buffer_enabled: boolean;
    weather_buffer_mode: string;
    weather_buffer_minutes: number;
    weather_alerts_enabled: boolean;
    calendar_sync_enabled: boolean;
    calendar_auto_reschedule: boolean;
  }> {
    const response = await apiClient.get("/users/me");
    const pref = response.data.preference || {};
    return {
      weather_buffer_enabled: pref.weather_buffer_enabled ?? false,
      weather_buffer_mode: pref.weather_buffer_mode ?? "informational_only",
      weather_buffer_minutes: pref.weather_buffer_minutes ?? 10,
      weather_alerts_enabled: pref.weather_alerts_enabled ?? true,
      calendar_sync_enabled: pref.calendar_sync_enabled ?? true,
      calendar_auto_reschedule: pref.calendar_auto_reschedule ?? false,
    };
  }

  async updateContextPreferences(preferences: Partial<{
    weather_buffer_enabled: boolean;
    weather_buffer_mode: string;
    weather_buffer_minutes: number;
    weather_alerts_enabled: boolean;
    calendar_sync_enabled: boolean;
    calendar_auto_reschedule: boolean;
  }>): Promise<any> {
    const response = await apiClient.patch("/users/me/preferences", preferences);
    return response.data;
  }
}
