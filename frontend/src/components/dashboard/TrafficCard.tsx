import { AlertTriangle, TrendingUp, CheckCircle2, RefreshCw } from "lucide-react";
import { Card } from "@/components/ui/card";
import { StatusIndicator } from "@/components/ui/status-indicator";

export interface TrafficCardProps {
  congestionLevel: "clear" | "moderate" | "heavy";
  delayMinutes: number;
  routeSummary: string;
  onRefresh?: () => void;
}

export function TrafficCard({
  congestionLevel = "clear",
  delayMinutes = 0,
  routeSummary = "Ahmedabad-Vadodara Expressway",
  onRefresh,
}: TrafficCardProps) {
  const isDelay = delayMinutes > 0 || congestionLevel !== "clear";

  return (
    <Card className="p-4 text-left border-white/10 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Live Traffic Intelligence
        </span>
        <div className="flex items-center gap-2">
          <StatusIndicator
            status={isDelay ? "warning" : "active"}
            label={isDelay ? "Congested" : "Flowing"}
          />
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="p-1 rounded text-slate-400 hover:text-slate-200 transition-colors"
              aria-label="Refresh traffic"
            >
              <RefreshCw size={12} />
            </button>
          )}
        </div>
      </div>

      <div className="flex items-start gap-3">
        <div
          className={`p-2 rounded-xl border ${
            isDelay
              ? "bg-amber-500/10 border-amber-500/20 text-amber-400"
              : "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
          }`}
        >
          {isDelay ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-bold text-slate-100">
            {isDelay ? `+${delayMinutes} min Traffic Delay` : "Optimal Traffic Flow"}
          </p>
          <p className="text-xs text-slate-400 mt-0.5 truncate">
            {routeSummary}
          </p>
        </div>
      </div>

      <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[11px] text-slate-500">
        <span className="flex items-center gap-1 text-slate-400">
          <TrendingUp size={12} className="text-brand-400" />
          Predictive trend: Stable
        </span>
        <span>Updated 1m ago</span>
      </div>
    </Card>
  );
}
