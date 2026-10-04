import { motion } from "framer-motion";
import {
  Bell,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Navigation,
  XCircle,
  TrendingUp,
} from "lucide-react";
import { ActivityEvent, ActivityEventType } from "@/core/repositories/interfaces/ActivityRepository";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { activityItemVariants } from "@/core/animations/variants";

export interface ActivityTimelineProps {
  activities: ActivityEvent[];
}

export function ActivityTimeline({ activities }: ActivityTimelineProps) {
  const getEventIcon = (type: ActivityEventType) => {
    switch (type) {
      case "arrived":
        return <CheckCircle2 size={16} className="text-emerald-400" />;
      case "alarm_triggered":
        return <Bell size={16} className="text-brand-400" />;
      case "traffic_recalculated":
        return <TrendingUp size={16} className="text-amber-400" />;
      case "alarm_snoozed":
        return <Clock size={16} className="text-indigo-400" />;
      case "alarm_missed":
        return <AlertTriangle size={16} className="text-rose-400" />;
      case "alarm_cancelled":
        return <XCircle size={16} className="text-slate-400" />;
      default:
        return <Navigation size={16} className="text-brand-400" />;
    }
  };

  const getEventBadge = (type: ActivityEventType) => {
    switch (type) {
      case "arrived":
        return <Badge variant="success">Arrived</Badge>;
      case "traffic_recalculated":
        return <Badge variant="warning">Traffic Shift</Badge>;
      case "alarm_missed":
        return <Badge variant="danger">Missed</Badge>;
      default:
        return <Badge variant="neutral">Audit</Badge>;
    }
  };

  return (
    <div className="relative pl-6 space-y-4 text-left">
      {/* Continuous vertical timeline line */}
      <div className="absolute left-2.5 top-3 bottom-3 w-0.5 bg-slate-800" />

      {activities.map((act) => (
        <motion.div
          key={act.id}
          variants={activityItemVariants}
          initial="initial"
          animate="animate"
          className="relative group"
        >
          {/* Node Icon on Timeline Line */}
          <div className="absolute -left-6 top-3 w-6 h-6 rounded-full bg-slate-900 border-2 border-slate-700 flex items-center justify-center shadow-md">
            {getEventIcon(act.type)}
          </div>

          <Card className="p-4 border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-colors">
            <div className="flex items-start justify-between gap-3 mb-1.5">
              <h4 className="text-sm font-bold text-slate-100">{act.title}</h4>
              <div className="flex items-center gap-2">
                {getEventBadge(act.type)}
                <span className="text-[11px] text-slate-500 whitespace-nowrap">
                  {act.timestamp}
                </span>
              </div>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              {act.description}
            </p>

            {act.metadata?.destination && (
              <div className="mt-2.5 pt-2 border-t border-white/5 flex items-center gap-3 text-[11px] text-slate-400">
                <span>Destination: <strong>{act.metadata.destination}</strong></span>
                {act.metadata.delayMinutes && (
                  <span className="text-amber-400 font-semibold">
                    Traffic buffer: +{act.metadata.delayMinutes}m
                  </span>
                )}
              </div>
            )}
          </Card>
        </motion.div>
      ))}
    </div>
  );
}
