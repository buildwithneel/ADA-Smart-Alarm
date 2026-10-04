import { Link } from "react-router-dom";
import {
  Car,
  Train,
  Bike,
  Footprints,
  MapPin,
  Trash2,
  Calendar,
  ChevronRight,
  Copy,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Clock,
} from "lucide-react";
import { Alarm } from "@/core/types/alarm";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { WeatherBadge } from "@/components/context/WeatherBadge";

export interface AlarmCardProps {
  alarm: Alarm;
  onToggle: (id: number) => void;
  onDelete: (id: number) => void;
  onDuplicate?: (id: number) => void;
}

export function AlarmCard({ alarm, onToggle, onDelete, onDuplicate }: AlarmCardProps) {
  const getTransportIcon = (mode: string) => {
    switch (mode) {
      case "transit":
        return <Train size={15} />;
      case "bicycling":
        return <Bike size={15} />;
      case "walking":
        return <Footprints size={15} />;
      default:
        return <Car size={15} />;
    }
  };

  const getStatusBadge = () => {
    const rawStatus = alarm.status?.toLowerCase() || (alarm.is_active ? "scheduled" : "disabled");

    if (rawStatus === "urgent_schedule_change") {
      return (
        <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded border bg-rose-500/20 text-rose-300 border-rose-500/40 flex items-center gap-1 animate-pulse">
          <AlertTriangle size={10} />
          URGENT UPDATE
        </span>
      );
    }

    if (rawStatus === "missed_recalculation") {
      return (
        <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded border bg-amber-500/20 text-amber-300 border-amber-500/40">
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
      <span className={`text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded border ${color}`}>
        {st}
      </span>
    );
  };

  const renderAdaptiveNotice = () => {
    const reason = alarm.schedule_change_reason;
    if (!reason || !alarm.is_active) return null;

    if (reason === "TRAFFIC_INCREASE") {
      return (
        <div className="mt-3 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-between text-xs text-amber-300">
          <span className="flex items-center gap-1.5">
            <TrendingUp size={13} className="text-amber-400 shrink-0" />
            <span>Heavy traffic • Travel increased by {alarm.traffic_delay_minutes || 0}m</span>
          </span>
          <span className="text-[10px] text-amber-400/80 font-mono">
            {alarm.schedule_version ? `v${alarm.schedule_version}` : ""}
          </span>
        </div>
      );
    }

    if (reason === "TRAFFIC_DECREASE") {
      return (
        <div className="mt-3 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-between text-xs text-emerald-300">
          <span className="flex items-center gap-1.5">
            <TrendingDown size={13} className="text-emerald-400 shrink-0" />
            <span>Traffic eased • Schedule optimized</span>
          </span>
          <span className="text-[10px] text-emerald-400/80 font-mono">
            {alarm.schedule_version ? `v${alarm.schedule_version}` : ""}
          </span>
        </div>
      );
    }

    if (reason === "URGENT_SCHEDULE_CHANGE" || alarm.status === "urgent_schedule_change") {
      return (
        <div className="mt-3 px-3 py-1.5 rounded-lg bg-rose-500/15 border border-rose-500/30 flex items-center justify-between text-xs text-rose-300">
          <span className="flex items-center gap-1.5">
            <AlertTriangle size={13} className="text-rose-400 shrink-0" />
            <span>Traffic surged close to departure • Wake time adjusted to now!</span>
          </span>
        </div>
      );
    }

    return null;
  };

  return (
    <Card
      className={`p-5 text-left border transition-all ${
        alarm.is_active
          ? alarm.status === "urgent_schedule_change"
            ? "border-rose-500/40 bg-rose-950/20"
            : "border-white/10 hover:border-brand-500/40 bg-slate-900/60"
          : "border-slate-800/60 bg-slate-950/40 opacity-60"
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className="p-2.5 rounded-xl bg-slate-800 text-slate-300 border border-white/5 shrink-0 mt-0.5">
            {getTransportIcon(alarm.transport_mode)}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-base font-bold text-slate-100">
                {alarm.title}
              </h3>
              {getStatusBadge()}
              {alarm.schedule_version && alarm.schedule_version > 1 && (
                <span className="text-[9px] font-mono text-slate-400 px-1.5 py-0.2 rounded bg-slate-800 border border-slate-700">
                  v{alarm.schedule_version}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 flex-wrap mt-0.5">
              <p className="text-xs text-slate-400 flex items-center gap-1.5">
                <MapPin size={12} className="text-brand-400 shrink-0" />
                <span className="truncate max-w-[180px]">{alarm.destination_name}</span>
              </p>
              {alarm.weather_condition_snapshot && (
                <WeatherBadge conditionText={alarm.weather_condition_snapshot} size="sm" />
              )}
              {alarm.weather_buffer_minutes && alarm.weather_buffer_minutes > 0 ? (
                <span className="text-[9px] font-semibold text-sky-300 bg-sky-950/40 border border-sky-500/30 px-1.5 py-0.5 rounded">
                  +{alarm.weather_buffer_minutes}m Weather
                </span>
              ) : null}
              {alarm.calendar_event_id && (
                <span className="text-[9px] font-semibold text-blue-300 bg-blue-950/40 border border-blue-500/30 px-1.5 py-0.5 rounded flex items-center gap-1">
                  <Calendar size={9} /> Calendar
                </span>
              )}
            </div>
          </div>
        </div>

        <Switch
          checked={alarm.is_active}
          onCheckedChange={() => onToggle(alarm.id)}
          aria-label={`Toggle ${alarm.title}`}
        />
      </div>

      {/* Dynamic Adaptive Notice Badge */}
      {renderAdaptiveNotice()}

      {/* Dynamic Times: Wake & Leave & Arrive */}
      <div className="grid grid-cols-3 gap-2 mt-4 p-3 rounded-xl bg-slate-950/60 border border-white/5 text-center">
        <div>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Wake Up
          </span>
          <span className="text-lg font-black text-brand-300">
            {alarm.calculated_wake_time || "--:--"}
          </span>
        </div>
        <div>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Leave Home
          </span>
          <span className="text-lg font-black text-slate-200">
            {alarm.calculated_leave_time || "--:--"}
          </span>
        </div>
        <div>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Target
          </span>
          <span className="text-lg font-black text-emerald-400">
            {alarm.desired_arrival_time}
          </span>
        </div>
      </div>

      {/* Meta tags and actions */}
      <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1">
            <Calendar size={12} className="text-slate-500" />
            {alarm.repeat_days ? alarm.repeat_days.split(",").join(" ") : "Once"}
          </span>
          <span className="text-slate-600">•</span>
          <span>Commute: {alarm.current_travel_minutes}m</span>
          {alarm.route_freshness_state === "stale" && (
            <>
              <span className="text-slate-600">•</span>
              <span className="text-amber-400 text-[11px] flex items-center gap-0.5">
                <Clock size={10} /> Outdated
              </span>
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          {onDuplicate && (
            <button
              onClick={() => onDuplicate(alarm.id)}
              className="p-1 text-slate-400 hover:text-brand-300 transition-colors"
              title="Duplicate alarm"
              aria-label="Duplicate alarm"
            >
              <Copy size={13} />
            </button>
          )}
          <Link
            to={`/alarms/${alarm.id}`}
            className="text-slate-300 hover:text-brand-400 font-semibold flex items-center gap-0.5 transition-colors"
          >
            Details
            <ChevronRight size={14} />
          </Link>
          <button
            onClick={() => onDelete(alarm.id)}
            className="p-1 text-slate-500 hover:text-rose-400 transition-colors"
            title="Delete alarm"
            aria-label="Delete alarm"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </Card>
  );
}
