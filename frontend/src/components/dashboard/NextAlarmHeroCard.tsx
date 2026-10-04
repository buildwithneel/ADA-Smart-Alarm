import { useState } from "react";
import { motion } from "framer-motion";
import {
  Clock,
  MapPin,
  Car,
  Bell,
  CheckCircle2,
  Calendar,
  Sparkles,
} from "lucide-react";
import { Alarm } from "@/core/types/alarm";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusIndicator } from "@/components/ui/status-indicator";
import { MapPlaceholder } from "@/components/ui/map-placeholder";
import {
  nextAlarmCardEntrance,
  timelineStagger,
} from "@/core/animations/variants";

export interface NextAlarmHeroCardProps {
  alarm: Alarm;
  onToggle?: (id: number) => void;
}

export function NextAlarmHeroCard({ alarm }: NextAlarmHeroCardProps) {
  const [showMap, setShowMap] = useState(false);

  // Progressive Timeline Steps: WAKE -> PREPARE -> LEAVE -> TRAVEL -> ARRIVE
  const timelineSteps = [
    {
      id: "wake",
      label: "WAKE UP",
      time: alarm.calculated_wake_time || "07:42 AM",
      description: "Gentle ascending audio & smart light trigger",
      status: "current",
      icon: Bell,
    },
    {
      id: "prepare",
      label: "PREPARATION",
      time: `${alarm.routine_minutes} min`,
      description: "Morning routine cushion",
      status: "upcoming",
      icon: Clock,
    },
    {
      id: "leave",
      label: "LEAVE HOME",
      time: alarm.calculated_leave_time || "08:15 AM",
      description: "Optimal departure window",
      status: "upcoming",
      icon: Car,
    },
    {
      id: "travel",
      label: "LIVE TRAVEL",
      time: `${alarm.current_travel_minutes} min`,
      description: alarm.traffic_delay_minutes > 0 ? `+${alarm.traffic_delay_minutes}m dynamic traffic buffer` : "Optimal traffic flow",
      status: "upcoming",
      icon: Sparkles,
    },
    {
      id: "arrive",
      label: "ARRIVE TARGET",
      time: "09:00 AM",
      description: "CHARUSAT campus arrival guarantee",
      status: "upcoming",
      icon: CheckCircle2,
    },
  ];

  return (
    <motion.div
      variants={nextAlarmCardEntrance}
      initial="initial"
      animate="animate"
      className="space-y-4"
    >
      <Card className="p-6 relative overflow-hidden border-brand-500/25 bg-gradient-to-b from-slate-900/90 to-slate-950/90 text-left">
        {/* Subtle background ambient pulse */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-brand-500/10 blur-[90px] rounded-full pointer-events-none -z-0" />

        {/* Header Bar */}
        <div className="relative z-10 flex items-center justify-between mb-5">
          <StatusIndicator status="active" label="Live Adaptive Radar" pulse />
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowMap(!showMap)}
              className="text-xs px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition-colors border border-white/5"
            >
              {showMap ? "Hide Route Map" : "Preview Route"}
            </button>
            <Badge variant="brand">Next Trip</Badge>
          </div>
        </div>

        {/* Map Preview Toggle */}
        {showMap && (
          <div className="relative z-10 mb-6">
            <MapPlaceholder
              originName={alarm.origin_name || "Current GPS"}
              destinationName={alarm.destination_name}
              travelMinutes={alarm.current_travel_minutes}
              trafficDelayMinutes={alarm.traffic_delay_minutes}
            />
          </div>
        )}

        {/* Primary Destination & Dynamic Alarm Calculation Display */}
        <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
          <div>
            <div className="flex items-center gap-2 text-xs text-brand-400 font-semibold uppercase tracking-wider mb-1">
              <MapPin size={13} />
              <span>Target Destination</span>
            </div>
            <h2 className="text-2xl font-black text-slate-100 tracking-tight">
              {alarm.destination_name}
            </h2>
            <p className="text-xs text-slate-400 mt-1 flex items-center gap-2">
              <Calendar size={13} />
              Weekdays • Mon, Tue, Wed, Thu, Fri
            </p>

            <div className="mt-4 flex flex-wrap gap-2 text-xs">
              <span className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 border border-white/5">
                Arrival: <strong>9:00 AM</strong>
              </span>
              <span className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 border border-white/5">
                Travel: <strong>{alarm.current_travel_minutes}m</strong>
              </span>
              <span className="px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
                Traffic Normal
              </span>
            </div>
          </div>

          {/* Huge Calculated Wake-up Hero Time */}
          <div className="text-center md:text-right p-5 rounded-2xl bg-slate-950/60 border border-white/5 backdrop-blur-md">
            <span className="text-[11px] font-bold uppercase tracking-widest text-slate-400 block mb-1">
              Recommended Wake Time
            </span>
            <div className="text-5xl md:text-6xl font-black tracking-tight text-white">
              {alarm.calculated_wake_time || "07:42 AM"}
            </div>
            <p className="text-xs text-brand-400 font-medium mt-2 flex items-center justify-center md:justify-end gap-1.5">
              <Clock size={13} />
              Departure in 45 min • Routine 33 min
            </p>
          </div>
        </div>

        {/* Progressive Timeline: WAKE -> PREPARE -> LEAVE -> TRAVEL -> ARRIVE */}
        <div className="relative z-10 mt-8 pt-6 border-t border-white/10">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Trip Execution Pipeline
            </span>
            <span className="text-[11px] text-slate-400">
              Auto-recalculates every 60s
            </span>
          </div>

          <motion.div
            variants={timelineStagger}
            initial="initial"
            animate="animate"
            className="grid grid-cols-1 sm:grid-cols-5 gap-3"
          >
            {timelineSteps.map((step, idx) => {
              const Icon = step.icon;
              return (
                <div
                  key={step.id}
                  className="relative p-3 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">
                      0{idx + 1}. {step.label}
                    </span>
                    <Icon size={13} className="text-brand-400" />
                  </div>
                  <div className="text-sm font-extrabold text-slate-100">
                    {step.time}
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1 leading-snug">
                    {step.description}
                  </p>
                </div>
              );
            })}
          </motion.div>
        </div>
      </Card>
    </motion.div>
  );
}
