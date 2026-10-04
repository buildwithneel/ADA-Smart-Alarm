import { useState, useEffect } from "react";
import { ActivityTimeline } from "@/components/activity/ActivityTimeline";
import { ActivityEvent } from "@/core/repositories/interfaces/ActivityRepository";
import { activityRepository } from "@/core/repositories";
import { Tabs } from "@/components/ui/tabs";

export function ActivityPage() {
  const [activities, setActivities] = useState<ActivityEvent[]>([]);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    async function load() {
      const data = await activityRepository.getAll();
      setActivities(data);
    }
    load();
  }, []);

  const tabs = [
    { id: "all", label: "All Events" },
    { id: "traffic", label: "Traffic Adjustments" },
    { id: "alarms", label: "Alarms & Arrivals" },
  ];

  const filtered = activities.filter((act) => {
    if (filter === "traffic") return act.type === "traffic_recalculated";
    if (filter === "alarms") return act.type === "alarm_triggered" || act.type === "arrived";
    return true;
  });

  return (
    <div className="space-y-6 text-left max-w-2xl mx-auto">
      <div>
        <h1 className="text-2xl font-black text-slate-100 tracking-tight">Activity Log</h1>
        <p className="text-xs text-slate-400">
          Full audit trail of dynamic alarm adjustments, triggers, and commutes
        </p>
      </div>

      <Tabs tabs={tabs} activeTab={filter} onChange={setFilter} />

      <ActivityTimeline activities={filtered} />
    </div>
  );
}
