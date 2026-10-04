import { Alarm, AlarmCreateInput } from "@/core/types/alarm";

export interface IAlarmRepository {
  getAll(): Promise<Alarm[]>;
  getById(id: number): Promise<Alarm | null>;
  create(input: AlarmCreateInput): Promise<Alarm>;
  update(id: number, input: Partial<Alarm>): Promise<Alarm>;
  toggle(id: number): Promise<Alarm>;
  delete(id: number): Promise<boolean>;
  duplicate(id: number): Promise<Alarm>;
  refresh(id: number): Promise<Alarm>;
  enable?(id: number): Promise<Alarm>;
  disable?(id: number): Promise<Alarm>;
  getHistory?(id: number): Promise<import("@/core/types/alarm").AlarmScheduleChange[]>;
}
