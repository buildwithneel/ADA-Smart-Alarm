export interface CalendarConnection {
  id: string;
  user_id: string;
  provider: string;
  account_email: string;
  is_active: boolean;
  last_synced_at?: string | null;
  sync_status: 'idle' | 'syncing' | 'success' | 'error';
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CalendarEvent {
  id: string;
  connection_id: string;
  user_id: string;
  alarm_id?: string | null;
  external_event_id: string;
  title: string;
  start_time: string;
  end_time: string;
  timezone: string;
  location?: string | null;
  resolved_latitude?: number | null;
  resolved_longitude?: number | null;
  all_day: boolean;
  status: 'confirmed' | 'tentative' | 'cancelled';
  source_provider: string;
  last_synced_at: string;
  event_link?: string | null;
}

export interface ProposeAlarmResponse {
  already_linked: boolean;
  alarm_id?: string | null;
  alarm_title?: string | null;
  event_id?: string | null;
  event_title?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  timezone?: string | null;
  location?: string | null;
  has_usable_location: boolean;
  resolved_latitude?: number | null;
  resolved_longitude?: number | null;
  proposed_arrival_time?: string | null;
  proposed_arrival_date?: string | null;
  preparation_time: number;
  safety_buffer: number;
  transportation_mode: string;
}

export interface CreateAlarmFromEventRequest {
  title?: string;
  destination_id?: string;
  preparation_time?: number;
  safety_buffer?: number;
  transportation_mode?: string;
}
