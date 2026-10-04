import { create } from "zustand";
import { Alarm, AlarmCalculationPreview } from "@/core/types/alarm";

interface AlarmState {
  alarms: Alarm[];
  activeAlarm: Alarm | null;
  livePreview: AlarmCalculationPreview | null;
  isLoading: boolean;
  error: string | null;
  setAlarms: (alarms: Alarm[]) => void;
  setActiveAlarm: (alarm: Alarm | null) => void;
  setLivePreview: (preview: AlarmCalculationPreview | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useAlarmStore = create<AlarmState>((set) => ({
  alarms: [],
  activeAlarm: null,
  livePreview: null,
  isLoading: false,
  error: null,
  setAlarms: (alarms) => set({ alarms }),
  setActiveAlarm: (alarm) => set({ activeAlarm: alarm }),
  setLivePreview: (preview) => set({ livePreview: preview }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
}));
