import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  ArrowLeft,
  MapPin,
  Trash2,
  ShieldCheck,
  RefreshCw,
  Copy,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  History,
  Clock,
  Radio,
  Volume2,
} from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { MapView } from "@/components/maps/MapView";
import { ETABreakdownCard } from "@/components/eta/ETABreakdownCard";
import { Card } from "@/components/ui/card";
import { alarmRepository } from "@/core/repositories";
import { useETAEngine } from "@/core/eta/useETAEngine";
import { Alarm, AlarmScheduleChange } from "@/core/types/alarm";
import { toast } from "@/core/toast/useToast";
import { playAlarmChime } from "@/core/utils/audioAlert";
import { contextRepository } from "@/core/repositories";
import { ContextSummary } from "@/core/types/context";
import { ContextAlertCard } from "@/components/context/ContextAlertCard";
import { WeatherBadge } from "@/components/context/WeatherBadge";

export function AlarmDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [alarm, setAlarm] = useState<Alarm | null>(null);
  const [history, setHistory] = useState<AlarmScheduleChange[]>([]);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [contextSummary, setContextSummary] = useState<ContextSummary | null>(null);
  const [isApplyingBuffer, setIsApplyingBuffer] = useState(false);

  useEffect(() => {
    if (id) {
      const numId = parseInt(id, 10);
      alarmRepository.getById(numId).then((res) => {
        setAlarm(res);
        if (alarmRepository.getHistory) {
          alarmRepository.getHistory(numId).then((hist) => setHistory(hist || []));
        }

        const uuid = (alarmRepository as any).getUuid?.(numId) || id;
        if (uuid) {
          contextRepository.getAlarmContext(uuid).then(setContextSummary).catch(() => {});
        }
      });
    }
  }, [id]);

  // ETA Engine — compute live ETA preview for the alarm
  const origin = {
    latitude: alarm?.origin_lat ?? 23.2156,
    longitude: alarm?.origin_lng ?? 72.6369,
  };
  const destination = {
    latitude: alarm?.destination_lat ?? 22.5996,
    longitude: alarm?.destination_lng ?? 72.8205,
  };

  const { preview, recalculate } = useETAEngine({
    origin,
    destination,
    desiredArrivalTime: alarm?.desired_arrival_time?.slice(0, 5) ?? "09:00",
    preparationMinutes: alarm?.routine_minutes ?? 30,
    safetyBufferMinutes: alarm?.buffer_minutes ?? 15,
    transportMode: (alarm?.transport_mode ?? "driving") as "driving" | "transit" | "bicycling" | "walking",
    enabled: !!alarm,
  });

  if (!alarm) {
    return (
      <div className="py-20 text-center text-slate-400">
        <p>Loading alarm details...</p>
      </div>
    );
  }

  const handleToggle = async () => {
    const updated = await alarmRepository.toggle(alarm.id);
    setAlarm(updated);
    toast.info("Status Updated", `Alarm is now ${updated.is_active ? "active" : "disabled"}.`);
  };

  const handleDelete = async () => {
    await alarmRepository.delete(alarm.id);
    toast.success("Alarm Removed", "The dynamic alarm was deleted.");
    navigate("/alarms");
  };

  const handleDuplicate = async () => {
    try {
      const copy = await alarmRepository.duplicate(alarm.id);
      toast.success("Alarm Duplicated", `Created copy: ${copy.title}`);
      navigate(`/alarms/${copy.id}`);
    } catch {
      toast.error("Duplicate Failed", "Could not duplicate alarm.");
    }
  };

  const handleEvaluate = async () => {
    setIsEvaluating(true);
    try {
      const refreshed = await alarmRepository.refresh(alarm.id);
      setAlarm(refreshed);
      if (alarmRepository.getHistory) {
        const hist = await alarmRepository.getHistory(alarm.id);
        setHistory(hist || []);
      }
    } catch {
      // Fallback to local recalculation if network/endpoint unavailable
    }
    recalculate();
    await new Promise((r) => setTimeout(r, 600)); // Visual feedback
    setIsEvaluating(false);
    toast.success("Schedule Refreshed", `Wake at ${preview.wakeTime} · Leave at ${preview.leaveTime}`);
  };

  const handleApplyBuffer = async (bufferMinutes: number) => {
    const uuid = (alarmRepository as any).getUuid?.(alarm.id) || id || String(alarm.id);
    setIsApplyingBuffer(true);
    try {
      await contextRepository.applyWeatherBuffer(uuid, bufferMinutes, alarm.schedule_version);
      toast.success("Weather Buffer Applied", `Added ${bufferMinutes}m to your safety buffer.`);
      const refreshed = await alarmRepository.getById(alarm.id);
      if (refreshed) setAlarm(refreshed);
      const updatedCtx = await contextRepository.getAlarmContext(uuid);
      setContextSummary(updatedCtx);
      recalculate();
    } catch (err: any) {
      toast.error("Failed to Apply Buffer", err?.response?.data?.detail || "Could not apply buffer.");
    } finally {
      setIsApplyingBuffer(false);
    }
  };

  const getStatusBadge = () => {
    const rawStatus = alarm.status?.toLowerCase() || (alarm.is_active ? "scheduled" : "disabled");

    if (rawStatus === "urgent_schedule_change") {
      return (
        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full border bg-rose-500/20 text-rose-300 border-rose-500/40 flex items-center gap-1 animate-pulse">
          <AlertTriangle size={11} />
          URGENT UPDATE
        </span>
      );
    }

    if (rawStatus === "missed_recalculation") {
      return (
        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full border bg-amber-500/20 text-amber-300 border-amber-500/40">
          MISSED RECALC
        </span>
      );
    }

    const st = rawStatus.toUpperCase();
    const color =
      st === "SCHEDULED" || st === "ACTIVE"
        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
        : st === "DISABLED"
        ? "bg-slate-800 text-slate-400 border-slate-700"
        : st === "EXPIRED"
        ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
        : "bg-brand-500/10 text-brand-400 border-brand-500/30";

    return (
      <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full border ${color}`}>
        {st}
      </span>
    );
  };

  const getReasonExplanation = (reason?: string | null) => {
    if (!reason) return null;
    switch (reason) {
      case "TRAFFIC_INCREASE":
        return `Traffic increased your travel time by ${alarm.traffic_delay_minutes || 0} minutes, so ADA adjusted your schedule.`;
      case "TRAFFIC_DECREASE":
        return "Traffic conditions improved. ADA optimized your schedule to give you more rest.";
      case "URGENT_SCHEDULE_CHANGE":
        return "Traffic surged close to departure. Wake time has been adjusted immediately to prevent missing arrival.";
      case "ROUTE_CHANGED":
        return "A more optimal traffic-aware route was detected and your schedule was refreshed.";
      case "ROUTE_REFRESHED":
        return "Schedule verified against live traffic conditions.";
      default:
        return `Schedule updated: ${reason}`;
    }
  };

  const formatDateTime = (isoStr?: string | null) => {
    if (!isoStr) return "--:--";
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="space-y-6 text-left max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            to="/alarms"
            className="p-2 rounded-xl border border-slate-800 hover:bg-slate-900 text-slate-300"
            aria-label="Back to alarms"
          >
            <ArrowLeft size={18} />
          </Link>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-bold text-slate-100">{alarm.title}</h1>
              {getStatusBadge()}
              {alarm.schedule_version && (
                <span className="text-[10px] font-mono font-bold text-slate-400 px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700">
                  Version {alarm.schedule_version}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <p className="text-xs text-slate-400 flex items-center gap-1.5">
                <MapPin size={12} className="text-brand-400" />
                {alarm.destination_name}
              </p>
              {alarm.weather_condition_snapshot && (
                <WeatherBadge conditionText={alarm.weather_condition_snapshot} />
              )}
              {alarm.weather_buffer_minutes && alarm.weather_buffer_minutes > 0 ? (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full border bg-sky-500/20 text-sky-300 border-sky-500/30">
                  +{alarm.weather_buffer_minutes}m Weather Buffer
                </span>
              ) : null}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleDuplicate}
            className="p-2 text-slate-400 hover:text-brand-300 hover:bg-slate-900 rounded-lg transition-colors"
            title="Duplicate alarm"
            aria-label="Duplicate alarm"
          >
            <Copy size={16} />
          </button>
          <Switch checked={alarm.is_active} onCheckedChange={handleToggle} />
          <button
            onClick={handleDelete}
            className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-900 rounded-lg transition-colors"
            title="Delete alarm"
            aria-label="Delete alarm"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      {/* Context Intelligence Alerts (Weather & Calendar) */}
      {contextSummary?.results && contextSummary.results.length > 0 && (
        <div className="space-y-3">
          {contextSummary.results
            .filter((r) => r.finding !== 'CLEAR_CONDITIONS')
            .map((result, idx) => (
              <ContextAlertCard
                key={idx}
                result={result}
                onApplyBuffer={handleApplyBuffer}
                isApplying={isApplyingBuffer}
              />
            ))}
        </div>
      )}

      {/* Adaptive Schedule Live Status Section (Section 29) */}
      <Card className="p-5 border border-brand-500/20 bg-gradient-to-br from-slate-900/90 via-slate-900/60 to-slate-950/80 shadow-xl space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Radio size={14} className="text-emerald-400 animate-pulse" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Current Adaptive Schedule
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <button
              onClick={() => {
                playAlarmChime();
                toast.info("Chime Preview", "Playing harmonic wake chime audio.");
              }}
              className="flex items-center gap-1 text-[11px] text-slate-300 hover:text-violet-300 px-2 py-0.5 rounded-lg bg-slate-800 border border-slate-700 transition-colors"
              title="Test wake audio chime"
            >
              <Volume2 size={12} className="text-violet-400" />
              Test Chime
            </button>
            {alarm.route_freshness_state === "stale" ? (
              <span className="text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full text-[10px]">
                Traffic data may be outdated
              </span>
            ) : (
              <span className="text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full text-[10px]">
                Live Traffic-Aware
              </span>
            )}
          </div>
        </div>

        {/* 3-Column Schedule Display */}
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="p-3 rounded-xl bg-slate-950/70 border border-white/5">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
              Wake Up
            </span>
            <span className="text-xl font-black text-brand-300">
              {alarm.calculated_wake_time || "--:--"}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/70 border border-white/5">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
              Leave Home
            </span>
            <span className="text-xl font-black text-slate-200">
              {alarm.calculated_leave_time || "--:--"}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/70 border border-white/5">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
              Planned Arrival
            </span>
            <span className="text-xl font-black text-emerald-400">
              {formatDateTime(alarm.planned_arrival_time) || alarm.desired_arrival_time}
            </span>
          </div>
        </div>

        {/* Visual Adaptive Delivery Timeline (Section 25) */}
        <div className="pt-3 border-t border-white/5 space-y-3">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Delivery Schedule Timeline
          </span>
          <div className="relative pl-6 space-y-3.5 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-gradient-to-b before:from-violet-500 before:via-sky-500 before:to-emerald-500">
            {/* Step 1: Wake Up */}
            <div className="relative">
              <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-violet-400 ring-2 ring-slate-950" />
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-violet-300">WAKE UP ALARM</span>
                <span className="font-mono font-bold text-slate-100">{alarm.calculated_wake_time || "--:--"}</span>
              </div>
              <p className="text-[11px] text-slate-400">Preparation routine ({alarm.routine_minutes || 30} min)</p>
            </div>

            {/* Step 2: Leave Home */}
            <div className="relative">
              <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-sky-400 ring-2 ring-slate-950" />
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-sky-300">DEPARTURE REMINDER</span>
                <span className="font-mono font-bold text-slate-100">{alarm.calculated_leave_time || "--:--"}</span>
              </div>
              <p className="text-[11px] text-slate-400">
                Commute with live traffic ({preview.travelMinutes || alarm.current_travel_minutes || 0} min)
              </p>
            </div>

            {/* Step 3: Planned Arrival & Safety Buffer */}
            <div className="relative">
              <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-emerald-400 ring-2 ring-slate-950" />
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-emerald-300">PLANNED ARRIVAL</span>
                <span className="font-mono font-bold text-slate-100">{formatDateTime(alarm.planned_arrival_time) || alarm.desired_arrival_time}</span>
              </div>
              <p className="text-[11px] text-slate-400">
                Safety cushion ({alarm.buffer_minutes || 15} min) before required arrival at {alarm.desired_arrival_time}
              </p>
            </div>
          </div>
        </div>

        {/* Adaptive Explanation Card */}
        {alarm.schedule_change_reason && (
          <div className="p-3 rounded-xl bg-slate-800/50 border border-white/5 flex items-start gap-2.5 text-xs">
            {alarm.schedule_change_reason === "TRAFFIC_INCREASE" ? (
              <TrendingUp size={15} className="text-amber-400 mt-0.5 shrink-0" />
            ) : alarm.schedule_change_reason === "TRAFFIC_DECREASE" ? (
              <TrendingDown size={15} className="text-emerald-400 mt-0.5 shrink-0" />
            ) : (
              <Clock size={15} className="text-brand-400 mt-0.5 shrink-0" />
            )}
            <div className="space-y-0.5 text-left">
              <span className="font-semibold text-slate-200 block">
                {getReasonExplanation(alarm.schedule_change_reason)}
              </span>
              {alarm.last_route_refresh_at && (
                <span className="text-[11px] text-slate-400 block">
                  Last traffic update: {formatDateTime(alarm.last_route_refresh_at)}
                </span>
              )}
            </div>
          </div>
        )}
      </Card>

      {/* Interactive Map Visualizer */}
      <MapView
        origin={origin}
        destination={destination}
        originTitle={alarm.origin_name || "Current GPS"}
        destinationTitle={alarm.destination_name}
        provider="google"
        className="h-56"
      />

      {/* ETA Breakdown Card */}
      <ETABreakdownCard
        preview={preview}
        desiredArrivalTime={
          alarm.desired_arrival_time
            ? (() => {
                const parts = alarm.desired_arrival_time.slice(0, 5).split(":");
                const h = parseInt(parts[0]);
                const m = parseInt(parts[1]);
                const period = h < 12 ? "AM" : "PM";
                const h12 = h % 12 || 12;
                return `${String(h12).padStart(2, "0")}:${String(m).padStart(2, "0")} ${period}`;
              })()
            : "09:00 AM"
        }
        onRefresh={handleEvaluate}
      />

      {/* Schedule Audit History (Section 18) */}
      {history.length > 0 && (
        <Card className="p-4 border border-white/10 bg-slate-900/60 text-left space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <History size={13} className="text-brand-400" />
              Schedule Adjustments ({history.length})
            </span>
            <button
              onClick={() => setShowHistory((prev) => !prev)}
              className="text-xs text-brand-400 hover:text-brand-300 font-medium"
            >
              {showHistory ? "Hide History" : "View History"}
            </button>
          </div>

          {showHistory && (
            <div className="space-y-2 pt-2 border-t border-white/5">
              {history.map((item) => (
                <div
                  key={item.id}
                  className="p-2.5 rounded-lg bg-slate-950/60 border border-white/5 text-xs flex items-center justify-between"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-slate-400 text-[10px]">v{item.schedule_version}</span>
                      <span className="font-semibold text-slate-200">{item.reason}</span>
                    </div>
                    <p className="text-slate-400 text-[11px]">
                      Wake: {formatDateTime(item.previous_wake_time)} → {formatDateTime(item.new_wake_time)} • Travel: {item.new_travel_minutes}m
                    </p>
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Dynamic Recalculation Status Footer */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between text-xs text-slate-400">
        <span className="flex items-center gap-2">
          <ShieldCheck size={16} className="text-emerald-400" />
          Autonomous traffic polling active (evaluates periodically)
        </span>
        <button
          id="alarm-details-refresh-btn"
          onClick={handleEvaluate}
          disabled={isEvaluating || preview.isLoading}
          className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-slate-400 hover:text-brand-300 hover:bg-slate-800 transition-colors disabled:opacity-40"
          aria-label="Re-evaluate ETA"
        >
          <RefreshCw size={13} className={isEvaluating ? "animate-spin" : ""} />
          Re-evaluate
        </button>
      </div>
    </div>
  );
}
