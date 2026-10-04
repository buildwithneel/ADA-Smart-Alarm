import { ContextSummary, WeatherData } from "@/core/types/context";

export interface IContextRepository {
  getWeather(lat: number, lng: number, targetTime?: string): Promise<WeatherData>;
  getAlarmContext(alarmUuid: string): Promise<ContextSummary>;
  applyWeatherBuffer(
    alarmUuid: string,
    bufferMinutes?: number,
    expectedVersion?: number
  ): Promise<any>;
  getContextPreferences(): Promise<{
    weather_buffer_enabled: boolean;
    weather_buffer_mode: string;
    weather_buffer_minutes: number;
    weather_alerts_enabled: boolean;
    calendar_sync_enabled: boolean;
    calendar_auto_reschedule: boolean;
  }>;
  updateContextPreferences(preferences: Partial<{
    weather_buffer_enabled: boolean;
    weather_buffer_mode: string;
    weather_buffer_minutes: number;
    weather_alerts_enabled: boolean;
    calendar_sync_enabled: boolean;
    calendar_auto_reschedule: boolean;
  }>): Promise<any>;
}
