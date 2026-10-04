import { useNavigate } from "react-router-dom";
import { Clock, CheckCircle2, ChevronRight, Activity } from "lucide-react";
import { ActivityEvent } from "@/core/repositories/interfaces/ActivityRepository";
import { Card } from "@/components/ui/card";

export interface RecentActivityWidgetProps {
  activities: ActivityEvent[];
}

export function RecentActivityWidget({ activities }: RecentActivityWidgetProps) {
  const navigate = useNavigate();

  return (
    <Card className="p-4 text-left border-white/10 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
          <Activity size={13} className="text-brand-400" />
          Recent Dynamic Audits
        </span>
        <button
          onClick={() => navigate("/activity")}
          className="text-xs text-brand-400 hover:text-brand-300 font-medium flex items-center gap-0.5"
        >
          History
          <ChevronRight size={13} />
        </button>
      </div>

      <div className="space-y-2.5">
        {activities.slice(0, 3).map((act) => (
          <div
            key={act.id}
            className="p-2.5 rounded-xl bg-slate-900/50 border border-slate-800/80 hover:border-slate-700 transition-colors flex items-start gap-2.5"
          >
            <div className="p-1 rounded-lg bg-brand-500/10 text-brand-400 shrink-0 mt-0.5">
              {act.type === "arrived" ? <CheckCircle2 size={14} /> : <Clock size={14} />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-slate-200 truncate">{act.title}</p>
              <p className="text-[11px] text-slate-400 line-clamp-1">{act.description}</p>
            </div>
            <span className="text-[10px] text-slate-500 whitespace-nowrap">{act.timestamp}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
