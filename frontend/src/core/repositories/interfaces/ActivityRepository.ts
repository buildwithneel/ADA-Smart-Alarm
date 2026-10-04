export type ActivityEventType =
  | "alarm_created"
  | "alarm_triggered"
  | "alarm_snoozed"
  | "alarm_missed"
  | "arrived"
  | "alarm_cancelled"
  | "traffic_recalculated";

export interface ActivityEvent {
  id: string;
  type: ActivityEventType;
  title: string;
  description: string;
  timestamp: string;
  metadata?: {
    alarmId?: number;
    destination?: string;
    originalWakeTime?: string;
    shiftedWakeTime?: string;
    delayMinutes?: number;
    onTime?: boolean;
  };
}

export interface IActivityRepository {
  getAll(): Promise<ActivityEvent[]>;
  logEvent(event: Omit<ActivityEvent, "id" | "timestamp">): Promise<ActivityEvent>;
}
