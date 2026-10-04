import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Clock, ShieldCheck } from "lucide-react";
import { NextAlarmHeroCard } from "@/components/dashboard/NextAlarmHeroCard";
import { TrafficCard } from "@/components/dashboard/TrafficCard";
import { WeatherCard } from "@/components/dashboard/WeatherCard";
import { QuickActionPills } from "@/components/dashboard/QuickActionPills";
import { RecentActivityWidget } from "@/components/dashboard/RecentActivityWidget";
import { AlarmCard } from "@/components/alarms/AlarmCard";
import {
  alarmRepository,
  destinationRepository,
  activityRepository,
} from "@/core/repositories";
import { Alarm } from "@/core/types/alarm";
import { Destination } from "@/core/repositories/interfaces/DestinationRepository";
import { ActivityEvent } from "@/core/repositories/interfaces/ActivityRepository";
import { toast } from "@/core/toast/useToast";

export function DashboardPage() {
  const [alarms, setAlarms] = useState<Alarm[]>([]);
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [activities, setActivities] = useState<ActivityEvent[]>([]);

  useEffect(() => {
    async function loadData() {
      try {
        const [loadedAlarms, loadedDestinations, loadedActivities] = await Promise.all([
          alarmRepository.getAll(),
          destinationRepository.getAll(),
          activityRepository.getAll(),
        ]);
        setAlarms(loadedAlarms);
        setDestinations(loadedDestinations);
        setActivities(loadedActivities);
      } catch (err) {
        console.error("Failed to load dashboard data", err);
      }
    }
    loadData();
  }, []);

  const handleToggleAlarm = async (id: number) => {
    const updated = await alarmRepository.toggle(id);
    setAlarms((prev) => prev.map((a) => (a.id === id ? updated : a)));
    toast.info(
      updated.is_active ? "Alarm Activated" : "Alarm Deactivated",
      `${updated.title} is now ${updated.is_active ? "active and dynamically tracking traffic" : "disabled"}.`
    );
  };

  const handleDeleteAlarm = async (id: number) => {
    await alarmRepository.delete(id);
    setAlarms((prev) => prev.filter((a) => a.id !== id));
    toast.success("Alarm Removed", "The dynamic alarm was deleted.");
  };

  const nextAlarm = alarms.find((a) => a.is_active) || alarms[0];

  return (
    <div className="space-y-6">
      {/* Quick Action Destination Pills */}
      {destinations.length > 0 && (
        <QuickActionPills destinations={destinations} />
      )}

      {/* Hero: Next Adaptive Alarm Card */}
      {nextAlarm && (
        <NextAlarmHeroCard alarm={nextAlarm} onToggle={handleToggleAlarm} />
      )}

      {/* Two-Column Grid: Traffic Status & Micro-Weather */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <TrafficCard
          congestionLevel="clear"
          delayMinutes={nextAlarm?.traffic_delay_minutes || 0}
          routeSummary="Ahmedabad-Vadodara Expressway • US-101 Corridor"
          onRefresh={() => toast.info("Traffic Re-evaluated", "No major delays detected. Travel time remains 38 mins.")}
        />
        <WeatherCard
          temperatureC={23}
          condition="Clear Sky"
          bufferImpactMinutes={0}
        />
      </div>

      {/* Upcoming Secondary Alarms */}
      <div className="space-y-3 text-left">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Clock size={13} className="text-brand-400" />
            Configured Dynamic Alarms
          </span>
          <Link to="/alarms" className="text-xs text-brand-400 hover:text-brand-300 font-medium">
            View All ({alarms.length})
          </Link>
        </div>

        <div className="space-y-3">
          {alarms.slice(1, 3).map((alarm) => (
            <AlarmCard
              key={alarm.id}
              alarm={alarm}
              onToggle={handleToggleAlarm}
              onDelete={handleDeleteAlarm}
            />
          ))}
        </div>
      </div>

      {/* Recent Activity Timeline Widget */}
      {activities.length > 0 && (
        <RecentActivityWidget activities={activities} />
      )}

      {/* Autonomous System Status Footer */}
      <div className="flex items-center justify-between px-3 py-2 text-xs text-slate-500 border-t border-white/5">
        <span className="flex items-center gap-1.5">
          <ShieldCheck size={14} className="text-emerald-500" />
          Autonomous Sync Active (1m interval)
        </span>
        <span className="font-mono text-[11px]">GPS Accuracy: 4m</span>
      </div>
    </div>
  );
}
