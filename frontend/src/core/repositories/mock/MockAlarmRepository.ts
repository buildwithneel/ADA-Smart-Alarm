import { Alarm, AlarmCreateInput } from "@/core/types/alarm";
import { IAlarmRepository } from "../interfaces/AlarmRepository";
import { INITIAL_ALARMS } from "./mockData";

export class MockAlarmRepository implements IAlarmRepository {
  private alarms: Alarm[] = [...INITIAL_ALARMS];

  async getAll(): Promise<Alarm[]> {
    return [...this.alarms];
  }

  async getById(id: number): Promise<Alarm | null> {
    const found = this.alarms.find((a) => a.id === id);
    return found ? { ...found } : null;
  }

  async create(input: AlarmCreateInput): Promise<Alarm> {
    const newId = this.alarms.length > 0 ? Math.max(...this.alarms.map((a) => a.id)) + 1 : 1;
    
    // Simulate dynamic time derivation
    const [h, m] = input.desired_arrival_time.split(":");
    const arrivalHour = parseInt(h, 10);
    const arrivalMinute = parseInt(m, 10);
    
    const commuteMinutes = 35; // Mock baseline
    const totalMinutesBefore = commuteMinutes + input.buffer_minutes;
    let leaveH = arrivalHour;
    let leaveM = arrivalMinute - totalMinutesBefore;
    while (leaveM < 0) {
      leaveM += 60;
      leaveH -= 1;
    }
    
    let wakeH = leaveH;
    let wakeM = leaveM - input.routine_minutes;
    while (wakeM < 0) {
      wakeM += 60;
      wakeH -= 1;
    }

    const fmt = (hr: number, min: number) => {
      const p = hr >= 12 ? "PM" : "AM";
      const h12 = hr % 12 || 12;
      return `${String(h12).padStart(2, "0")}:${String(min).padStart(2, "0")} ${p}`;
    };

    const newAlarm: Alarm = {
      id: newId,
      user_id: 1,
      title: input.title,
      destination_name: input.destination_name,
      destination_lat: input.destination_lat,
      destination_lng: input.destination_lng,
      origin_name: input.origin_name || "Current Location",
      origin_lat: input.origin_lat,
      origin_lng: input.origin_lng,
      use_live_gps: input.use_live_gps,
      desired_arrival_time: input.desired_arrival_time,
      repeat_days: input.repeat_days || "",
      transport_mode: input.transport_mode,
      routine_minutes: input.routine_minutes,
      buffer_minutes: input.buffer_minutes,
      current_travel_minutes: commuteMinutes,
      traffic_delay_minutes: 0,
      calculated_leave_time: fmt(leaveH, leaveM),
      calculated_wake_time: fmt(wakeH, wakeM),
      weather_condition: "Clear, 24°C",
      weather_temp_c: 24,
      last_evaluated_at: new Date().toISOString(),
      status: "scheduled",
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    this.alarms.unshift(newAlarm);
    return { ...newAlarm };
  }

  async update(id: number, input: Partial<Alarm>): Promise<Alarm> {
    const index = this.alarms.findIndex((a) => a.id === id);
    if (index === -1) throw new Error(`Alarm ${id} not found`);
    this.alarms[index] = { ...this.alarms[index], ...input, updated_at: new Date().toISOString() };
    return { ...this.alarms[index] };
  }

  async toggle(id: number): Promise<Alarm> {
    const alarm = await this.getById(id);
    if (!alarm) throw new Error(`Alarm ${id} not found`);
    return this.update(id, {
      is_active: !alarm.is_active,
      status: !alarm.is_active ? "scheduled" : "disabled",
    });
  }

  async delete(id: number): Promise<boolean> {
    const initialLen = this.alarms.length;
    this.alarms = this.alarms.filter((a) => a.id !== id);
    return this.alarms.length < initialLen;
  }

  async duplicate(id: number): Promise<Alarm> {
    const orig = await this.getById(id);
    if (!orig) throw new Error(`Alarm ${id} not found`);
    const newId = this.alarms.length > 0 ? Math.max(...this.alarms.map((a) => a.id)) + 1 : 1;
    const copy: Alarm = {
      ...orig,
      id: newId,
      title: `${orig.title} (Copy)`,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    this.alarms.unshift(copy);
    return { ...copy };
  }

  async refresh(id: number): Promise<Alarm> {
    const orig = await this.getById(id);
    if (!orig) throw new Error(`Alarm ${id} not found`);
    const updated: Alarm = {
      ...orig,
      last_calculated_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    const idx = this.alarms.findIndex((a) => a.id === id);
    if (idx !== -1) this.alarms[idx] = updated;
    return { ...updated };
  }
}
