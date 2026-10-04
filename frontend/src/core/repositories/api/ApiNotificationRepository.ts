import apiClient from "@/core/api/apiClient";
import {
  AppNotification,
  NotificationListResponse,
  NotificationPreferences,
} from "@/core/types/notification";

interface BackendNotification {
  id: string;
  user_id: string;
  alarm_id?: string;
  type: string;
  status: string;
  channel: string;
  title: string;
  body: string;
  scheduled_for: string;
  delivered_at?: string;
  read_at?: string;
  schedule_version?: number;
  metadata_json?: Record<string, any>;
  created_at: string;
}

interface BackendPreferences {
  wake_alarm_enabled: boolean;
  departure_reminder_enabled: boolean;
  departure_reminder_lead_minutes: number;
  schedule_change_enabled: boolean;
  traffic_change_enabled: boolean;
  sound_enabled: boolean;
  vibration_enabled: boolean;
  in_app_enabled: boolean;
  web_push_enabled: boolean;
}

function mapFromBackend(item: BackendNotification): AppNotification {
  return {
    id: item.id,
    userId: item.user_id,
    alarmId: item.alarm_id,
    type: item.type as any,
    status: item.status as any,
    channel: item.channel as any,
    title: item.title,
    body: item.body,
    scheduledFor: item.scheduled_for,
    deliveredAt: item.delivered_at,
    readAt: item.read_at,
    scheduleVersion: item.schedule_version,
    metadata: item.metadata_json || {},
    createdAt: item.created_at,
  };
}

function mapPreferencesFromBackend(b: BackendPreferences): NotificationPreferences {
  return {
    wakeAlarmEnabled: b.wake_alarm_enabled,
    departureReminderEnabled: b.departure_reminder_enabled,
    departureReminderLeadMinutes: b.departure_reminder_lead_minutes,
    scheduleChangeEnabled: b.schedule_change_enabled,
    trafficChangeEnabled: b.traffic_change_enabled,
    soundEnabled: b.sound_enabled,
    vibrationEnabled: b.vibration_enabled,
    inAppEnabled: b.in_app_enabled,
    webPushEnabled: b.web_push_enabled,
  };
}

export const ApiNotificationRepository = {
  async getNotifications(
    unreadOnly = false,
    limit = 50,
    offset = 0
  ): Promise<NotificationListResponse> {
    const res = await apiClient.get<{
      items: BackendNotification[];
      total: number;
      unread_count: number;
    }>("/notifications", {
      params: { unread_only: unreadOnly, limit, offset },
    });
    return {
      items: (res.data.items || []).map(mapFromBackend),
      total: res.data.total,
      unreadCount: res.data.unread_count,
    };
  },

  async getUnreadCount(): Promise<number> {
    const res = await apiClient.get<{ unread_count: number }>("/notifications/unread-count");
    return res.data.unread_count || 0;
  },

  async markAsRead(id: string): Promise<AppNotification> {
    const res = await apiClient.post<BackendNotification>(`/notifications/${id}/read`);
    return mapFromBackend(res.data);
  },

  async markAllAsRead(): Promise<number> {
    const res = await apiClient.post<{ marked_read: number }>("/notifications/read-all");
    return res.data.marked_read || 0;
  },

  async getPreferences(): Promise<NotificationPreferences> {
    const res = await apiClient.get<BackendPreferences>("/notifications/preferences");
    return mapPreferencesFromBackend(res.data);
  },

  async updatePreferences(
    prefs: Partial<NotificationPreferences>
  ): Promise<NotificationPreferences> {
    const payload: Partial<BackendPreferences> = {};
    if (prefs.wakeAlarmEnabled !== undefined) payload.wake_alarm_enabled = prefs.wakeAlarmEnabled;
    if (prefs.departureReminderEnabled !== undefined)
      payload.departure_reminder_enabled = prefs.departureReminderEnabled;
    if (prefs.departureReminderLeadMinutes !== undefined)
      payload.departure_reminder_lead_minutes = prefs.departureReminderLeadMinutes;
    if (prefs.scheduleChangeEnabled !== undefined)
      payload.schedule_change_enabled = prefs.scheduleChangeEnabled;
    if (prefs.trafficChangeEnabled !== undefined)
      payload.traffic_change_enabled = prefs.trafficChangeEnabled;
    if (prefs.soundEnabled !== undefined) payload.sound_enabled = prefs.soundEnabled;
    if (prefs.vibrationEnabled !== undefined) payload.vibration_enabled = prefs.vibrationEnabled;
    if (prefs.inAppEnabled !== undefined) payload.in_app_enabled = prefs.inAppEnabled;
    if (prefs.webPushEnabled !== undefined) payload.web_push_enabled = prefs.webPushEnabled;

    const res = await apiClient.patch<BackendPreferences>("/notifications/preferences", payload);
    return mapPreferencesFromBackend(res.data);
  },

  async getVapidPublicKey(): Promise<string> {
    const res = await apiClient.get<{ public_key: string }>("/notifications/push/vapid-key");
    return res.data.public_key;
  },

  async subscribePush(sub: {
    endpoint: string;
    p256dh: string;
    auth: string;
    userAgent?: string;
  }): Promise<{ id: string; endpoint: string }> {
    const res = await apiClient.post("/notifications/push/subscribe", {
      endpoint: sub.endpoint,
      p256dh: sub.p256dh,
      auth: sub.auth,
      user_agent: sub.userAgent,
    });
    return res.data;
  },

  async unsubscribePush(endpoint: string): Promise<boolean> {
    const res = await apiClient.delete("/notifications/push/subscribe", {
      params: { endpoint },
    });
    return res.data.status === "unsubscribed";
  },

  async sendTestNotification(req?: {
    type?: string;
    title?: string;
    body?: string;
  }): Promise<AppNotification> {
    const res = await apiClient.post<BackendNotification>("/notifications/test", req || {});
    return mapFromBackend(res.data);
  },
};
