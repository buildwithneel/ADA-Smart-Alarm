import apiClient from "@/core/api/apiClient";
import { Alarm, AlarmCreateInput, TransportMode } from "@/core/types/alarm";
import { IAlarmRepository } from "../interfaces/AlarmRepository";

interface BackendAlarm {
  id: string;
  user_id: string;
  destination_id: string;
  title: string;
  arrival_time: string;
  preparation_time: number;
  safety_buffer: number;
  transportation_mode: string;
  enabled: boolean;
  destination?: {
    id: string;
    name: string;
    latitude: number;
    longitude: number;
    address: string;
  } | null;
  schedule?: {
    schedule_type: string;
    repeat_days?: string | null;
  } | null;
  calculated_wake_time?: string | null;
  calculated_leave_time?: string | null;
  planned_arrival_time?: string | null;
  current_travel_minutes?: number | null;
  traffic_delay_minutes?: number | null;
  status?: string;
  last_calculated_at?: string | null;
  calculation_version?: string | null;
  timezone?: string | null;
  schedule_version?: number;
  last_route_refresh_at?: string | null;
  last_schedule_change_at?: string | null;
  schedule_change_reason?: string | null;
  route_freshness_state?: string;
  schedule_changes?: any[];
  // Step 10: Weather + Calendar Context
  weather_buffer_minutes?: number | null;
  weather_condition_snapshot?: string | null;
  calendar_event_id?: string | null;
  created_at: string;
  updated_at: string;
}

export class ApiAlarmRepository implements IAlarmRepository {
  private idToUuid = new Map<number, string>();
  private uuidToId = new Map<string, number>();
  private nextId = 1;

  private getNumericId(uuid: string): number {
    if (!this.uuidToId.has(uuid)) {
      const numId = this.nextId++;
      this.uuidToId.set(uuid, numId);
      this.idToUuid.set(numId, uuid);
    }
    return this.uuidToId.get(uuid)!;
  }

  private mapFromBackend(item: BackendAlarm): Alarm {
    const numId = this.getNumericId(item.id);
    return {
      id: numId,
      user_id: 1,
      title: item.title,
      destination_name: item.destination?.name || "Destination",
      destination_lat: item.destination?.latitude || 0,
      destination_lng: item.destination?.longitude || 0,
      origin_name: "Current Location",
      origin_lat: null,
      origin_lng: null,
      use_live_gps: true,
      desired_arrival_time: item.arrival_time,
      planned_arrival_time: item.planned_arrival_time || null,
      repeat_days: item.schedule?.repeat_days || "",
      transport_mode: (item.transportation_mode.toLowerCase() as TransportMode) || "driving",
      routine_minutes: item.preparation_time,
      buffer_minutes: item.safety_buffer,
      current_travel_minutes: item.current_travel_minutes || 0,
      traffic_delay_minutes: item.traffic_delay_minutes || 0,
      calculated_leave_time: item.calculated_leave_time || null,
      calculated_wake_time: item.calculated_wake_time || null,
      last_calculated_at: item.last_calculated_at || null,
      calculation_version: item.calculation_version || "eta-v1",
      timezone: item.timezone || "Asia/Kolkata",
      status: (item.status?.toLowerCase() as any) || (item.enabled ? "scheduled" : "disabled"),
      is_active: item.enabled,
      schedule_version: item.schedule_version || 1,
      last_route_refresh_at: item.last_route_refresh_at || null,
      last_schedule_change_at: item.last_schedule_change_at || null,
      schedule_change_reason: item.schedule_change_reason || null,
      route_freshness_state: item.route_freshness_state || "fresh",
      schedule_changes: item.schedule_changes || [],
      weather_buffer_minutes: item.weather_buffer_minutes || 0,
      weather_condition_snapshot: item.weather_condition_snapshot || null,
      calendar_event_id: item.calendar_event_id || null,
      created_at: item.created_at,
      updated_at: item.updated_at,
    };
  }

  getUuid(numericId: number): string | undefined {
    return this.idToUuid.get(numericId);
  }

  async getAll(): Promise<Alarm[]> {
    const response = await apiClient.get<BackendAlarm[]>("/alarms");
    return response.data.map((item) => this.mapFromBackend(item));
  }

  async getById(id: number): Promise<Alarm | null> {
    const uuid = this.idToUuid.get(id);
    if (!uuid) return null;
    try {
      const response = await apiClient.get<BackendAlarm>(`/alarms/${uuid}`);
      return this.mapFromBackend(response.data);
    } catch {
      return null;
    }
  }

  async create(input: AlarmCreateInput): Promise<Alarm> {
    // 1. Ensure target destination exists on backend
    const destRes = await apiClient.post<{ id: string }>("/destinations", {
      name: input.destination_name,
      type: "custom",
      latitude: input.destination_lat,
      longitude: input.destination_lng,
      address: input.destination_name,
    });

    const payload = {
      title: input.title,
      destination_id: destRes.data.id,
      arrival_time: input.desired_arrival_time.length === 5 ? `${input.desired_arrival_time}:00` : input.desired_arrival_time,
      preparation_time: input.routine_minutes,
      safety_buffer: input.buffer_minutes,
      transportation_mode: input.transport_mode,
      enabled: true,
      schedule: {
        schedule_type: input.repeat_days ? "custom" : "daily",
        repeat_days: input.repeat_days || null,
      },
    };

    const response = await apiClient.post<BackendAlarm>("/alarms", payload);
    return this.mapFromBackend(response.data);
  }

  async update(id: number, input: Partial<Alarm>): Promise<Alarm> {
    const uuid = this.idToUuid.get(id);
    if (!uuid) throw new Error(`Alarm ${id} not found.`);

    const payload: Record<string, unknown> = {};
    if (input.title !== undefined) payload.title = input.title;
    if (input.desired_arrival_time !== undefined) {
      payload.arrival_time = input.desired_arrival_time.length === 5 
        ? `${input.desired_arrival_time}:00` 
        : input.desired_arrival_time;
    }
    if (input.routine_minutes !== undefined) payload.preparation_time = input.routine_minutes;
    if (input.buffer_minutes !== undefined) payload.safety_buffer = input.buffer_minutes;
    if (input.transport_mode !== undefined) payload.transportation_mode = input.transport_mode;
    if (input.is_active !== undefined) payload.enabled = input.is_active;

    const response = await apiClient.patch<BackendAlarm>(`/alarms/${uuid}`, payload);
    return this.mapFromBackend(response.data);
  }

  async toggle(id: number): Promise<Alarm> {
    const current = await this.getById(id);
    if (!current) throw new Error(`Alarm ${id} not found.`);
    if (current.is_active) {
      return this.disable(id);
    } else {
      return this.enable(id);
    }
  }

  async duplicate(id: number): Promise<Alarm> {
    const uuid = this.idToUuid.get(id);
    if (!uuid) throw new Error(`Alarm ${id} not found.`);
    const response = await apiClient.post<BackendAlarm>(`/alarms/${uuid}/duplicate`);
    return this.mapFromBackend(response.data);
  }

  async refresh(id: number): Promise<Alarm> {
    const uuid = this.idToUuid.get(id);
    if (!uuid) throw new Error(`Alarm ${id} not found.`);
    const response = await apiClient.post<BackendAlarm>(`/alarms/${uuid}/refresh`);
    return this.mapFromBackend(response.data);
  }

  async enable(id: number): Promise<Alarm> {
    const uuid = this.idToUuid.get(id);
    if (!uuid) throw new Error(`Alarm ${id} not found.`);
    const response = await apiClient.post<BackendAlarm>(`/alarms/${uuid}/enable`);
    return this.mapFromBackend(response.data);
  }

  async disable(id: number): Promise<Alarm> {
    const uuid = this.idToUuid.get(id);
    if (!uuid) throw new Error(`Alarm ${id} not found.`);
    const response = await apiClient.post<BackendAlarm>(`/alarms/${uuid}/disable`);
    return this.mapFromBackend(response.data);
  }

  async delete(id: number): Promise<boolean> {
    const uuid = this.idToUuid.get(id);
    if (!uuid) return false;
    try {
      await apiClient.delete(`/alarms/${uuid}`);
      return true;
    } catch {
      return false;
    }
  }

  async getHistory(id: number): Promise<import("@/core/types/alarm").AlarmScheduleChange[]> {
    const uuid = this.idToUuid.get(id);
    if (!uuid) return [];
    try {
      const response = await apiClient.get<import("@/core/types/alarm").AlarmScheduleChange[]>(`/alarms/${uuid}/history`);
      return response.data;
    } catch {
      return [];
    }
  }
}
