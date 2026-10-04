export type NotificationType =
  | 'ALARM_WAKE'
  | 'ALARM_DEPARTURE_REMINDER'
  | 'ALARM_SCHEDULE_CHANGED'
  | 'ALARM_URGENT_CHANGE'
  | 'ALARM_MISSED'
  | 'ALARM_COMPLETED'
  | 'ALARM_CANCELLED'
  | 'SYSTEM';

export type NotificationStatus =
  | 'PENDING'
  | 'SENT'
  | 'DELIVERED'
  | 'READ'
  | 'FAILED'
  | 'CANCELLED'
  | 'SUPERSEDED';

export type NotificationChannel = 'IN_APP' | 'WEB_PUSH' | 'ALL';

export interface AppNotification {
  id: string;
  userId: string;
  alarmId?: string;
  type: NotificationType;
  status: NotificationStatus;
  channel: NotificationChannel;
  title: string;
  body: string;
  scheduledFor: string;
  deliveredAt?: string;
  readAt?: string;
  scheduleVersion?: number;
  metadata?: Record<string, any>;
  createdAt: string;
}

export interface NotificationPreferences {
  wakeAlarmEnabled: boolean;
  departureReminderEnabled: boolean;
  departureReminderLeadMinutes: number;
  scheduleChangeEnabled: boolean;
  trafficChangeEnabled: boolean;
  soundEnabled: boolean;
  vibrationEnabled: boolean;
  inAppEnabled: boolean;
  webPushEnabled: boolean;
}

export interface NotificationListResponse {
  items: AppNotification[];
  total: number;
  unreadCount: number;
}
