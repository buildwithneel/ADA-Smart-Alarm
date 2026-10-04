/**
 * ETABreakdownCard — Rich visual breakdown of ADA's ETA calculation.
 *
 * Displays:
 * - Wake Time, Leave Time, Arrival Time (hero row)
 * - Animated confidence meter
 * - Travel time breakdown (base + traffic delay + safety buffer + weather buffer)
 * - Preparation time
 * - Provider badge and engine version
 * - Live refresh trigger
 */

import { useState } from "react";
import {
  Clock,
  Navigation,
  Zap,
  Shield,
  CloudRain,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Car,
  Activity,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import type { ETALivePreview } from "@/core/types/eta";

interface ETABreakdownCardProps {
  preview: ETALivePreview;
  desiredArrivalTime: string;
  onRefresh?: () => void;
  compact?: boolean;
}

function ConfidenceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 90
      ? "bg-emerald-500"
      : pct >= 75
      ? "bg-amber-500"
      : "bg-rose-500";

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[11px] font-mono text-slate-400">{pct}%</span>
    </div>
  );
}

function TimeBlock({
  label,
  value,
  accent = false,
  isLoading = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
  isLoading?: boolean;
}) {
  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500">
        {label}
      </span>
      {isLoading ? (
        <div className="h-8 w-20 bg-slate-800 rounded animate-pulse" />
      ) : (
        <span
          className={`text-xl font-black tracking-tight ${
            accent ? "text-brand-300" : "text-slate-100"
          }`}
        >
          {value}
        </span>
      )}
    </div>
  );
}

function BreakdownRow({
  icon,
  label,
  value,
  subLabel,
  highlight = false,
  dimmed = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  subLabel?: string;
  highlight?: boolean;
  dimmed?: boolean;
}) {
  return (
    <div
      className={`flex items-center justify-between py-2 border-b border-white/5 last:border-0 ${
        dimmed ? "opacity-50" : ""
      }`}
    >
      <div className="flex items-center gap-2.5">
        <span
          className={`w-7 h-7 rounded-lg flex items-center justify-center ${
            highlight ? "bg-brand-500/20 text-brand-400" : "bg-slate-800 text-slate-400"
          }`}
        >
          {icon}
        </span>
        <div>
          <span className="text-sm font-medium text-slate-300">{label}</span>
          {subLabel && (
            <span className="block text-[11px] text-slate-500">{subLabel}</span>
          )}
        </div>
      </div>
      <span
        className={`text-sm font-bold tabular-nums ${
          highlight ? "text-brand-300" : "text-slate-200"
        }`}
      >
        {value}
      </span>
    </div>
  );
}

export function ETABreakdownCard({
  preview,
  desiredArrivalTime,
  onRefresh,
  compact = false,
}: ETABreakdownCardProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await onRefresh?.();
    setTimeout(() => setIsRefreshing(false), 1200);
  };

  const congestionColors: Record<string, string> = {
    clear: "text-emerald-400 bg-emerald-500/10",
    low: "text-emerald-400 bg-emerald-500/10",
    moderate: "text-amber-400 bg-amber-500/10",
    heavy: "text-orange-400 bg-orange-500/10",
    severe: "text-rose-400 bg-rose-500/10",
    unknown: "text-slate-400 bg-slate-700/40",
  };

  const congestionBadge = congestionColors[preview.congestionLevel] ?? congestionColors.unknown;

  return (
    <Card className="border-brand-500/20 bg-gradient-to-br from-slate-900 via-indigo-950/10 to-slate-900 shadow-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-white/5">
        <div className="flex items-center gap-2">
          <span className="w-7 h-7 rounded-lg bg-brand-500/20 flex items-center justify-center">
            <Zap size={14} className="text-brand-400" />
          </span>
          <span className="text-xs font-bold uppercase tracking-widest text-brand-400">
            ADA ETA Engine
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Provider badge */}
          <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-white/5">
            {preview.provider || "—"}
          </span>

          {/* Congestion badge */}
          <span
            className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-md ${congestionBadge}`}
          >
            {preview.congestionLevel}
          </span>

          {/* Refresh */}
          {onRefresh && (
            <button
              id="eta-refresh-btn"
              onClick={handleRefresh}
              disabled={preview.isLoading || isRefreshing}
              className="w-6 h-6 flex items-center justify-center text-slate-400 hover:text-brand-300 transition-colors disabled:opacity-40"
              aria-label="Refresh ETA"
            >
              <RefreshCw
                size={13}
                className={preview.isLoading || isRefreshing ? "animate-spin" : ""}
              />
            </button>
          )}
        </div>
      </div>

      {/* Hero Time Row */}
      <div className="flex items-center justify-around px-5 py-5">
        <TimeBlock
          label="⏰ Wake Up"
          value={preview.wakeTime}
          accent
          isLoading={preview.isLoading}
        />

        <div className="flex flex-col items-center gap-1">
          <div className="w-px h-8 bg-gradient-to-b from-transparent via-slate-700 to-transparent" />
          <Navigation size={12} className="text-brand-500" />
          <div className="w-px h-8 bg-gradient-to-b from-transparent via-slate-700 to-transparent" />
        </div>

        <TimeBlock
          label="🚗 Leave Home"
          value={preview.leaveTime}
          isLoading={preview.isLoading}
        />

        <div className="flex flex-col items-center gap-1">
          <div className="w-px h-8 bg-gradient-to-b from-transparent via-slate-700 to-transparent" />
          <CheckCircle2 size={12} className="text-emerald-500" />
          <div className="w-px h-8 bg-gradient-to-b from-transparent via-slate-700 to-transparent" />
        </div>

        <TimeBlock
          label="🎯 Arrive By"
          value={desiredArrivalTime}
          isLoading={false}
        />
      </div>

      {/* Error or Loading state */}
      {preview.error && (
        <div className="mx-5 mb-3 flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
          <AlertTriangle size={13} className="text-amber-400 flex-shrink-0" />
          <span className="text-[11px] text-amber-300">{preview.error}</span>
        </div>
      )}

      {!compact && (
        <>
          {/* Breakdown Rows */}
          <div className="px-5 pb-3">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block mb-2">
              Time Budget Breakdown
            </span>

            <BreakdownRow
              icon={<Car size={13} />}
              label="Base Travel Time"
              value={`${preview.baseMinutes} min`}
              subLabel={`Without traffic · ${preview.distanceText}`}
            />

            <BreakdownRow
              icon={<Activity size={13} />}
              label="Traffic Delay"
              value={
                preview.trafficDelayMinutes > 0
                  ? `+${preview.trafficDelayMinutes} min`
                  : "None"
              }
              subLabel={`Congestion: ${preview.congestionLevel}`}
              highlight={preview.trafficDelayMinutes > 0}
              dimmed={preview.trafficDelayMinutes === 0}
            />

            <BreakdownRow
              icon={<Shield size={13} />}
              label="Safety Buffer"
              value={`+${preview.safetyBufferMinutes} min`}
              subLabel="Your explicit traffic cushion"
              highlight={false}
            />

            {preview.weatherBufferMinutes > 0 && (
              <BreakdownRow
                icon={<CloudRain size={13} />}
                label="Weather Buffer"
                value={`+${preview.weatherBufferMinutes} min`}
                subLabel="Adverse weather modifier"
                highlight
              />
            )}

            <BreakdownRow
              icon={<Clock size={13} />}
              label="Preparation Time"
              value={`${preview.safetyBufferMinutes > 0 ? preview.totalBudgetMinutes - preview.travelMinutes - preview.safetyBufferMinutes - preview.weatherBufferMinutes : "—"} min`}
              subLabel="Morning routine"
            />

            {/* Total */}
            <div className="mt-3 pt-3 border-t border-white/5 flex items-center justify-between">
              <span className="text-sm font-bold text-slate-300">
                Total Time Budget
              </span>
              <span className="text-base font-black text-brand-300">
                {preview.totalBudgetMinutes} min
              </span>
            </div>
          </div>

          {/* Confidence */}
          <div className="px-5 pb-5">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500">
                Calculation Confidence
              </span>
              <span className="text-[11px] text-slate-400">
                {preview.lastUpdated
                  ? `Updated ${preview.lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
                  : "Pending..."}
              </span>
            </div>
            <ConfidenceBar score={preview.confidenceScore} />
          </div>
        </>
      )}
    </Card>
  );
}
