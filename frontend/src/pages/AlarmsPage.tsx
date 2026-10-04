import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Plus, Clock } from "lucide-react";
import { AlarmCard } from "@/components/alarms/AlarmCard";
import { Tabs } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { alarmRepository } from "@/core/repositories";
import { Alarm } from "@/core/types/alarm";
import { toast } from "@/core/toast/useToast";

export function AlarmsPage() {
  const [alarms, setAlarms] = useState<Alarm[]>([]);
  const [activeTab, setActiveTab] = useState("all");

  useEffect(() => {
    async function load() {
      const data = await alarmRepository.getAll();
      setAlarms(data);
    }
    load();
  }, []);

  const handleToggle = async (id: number) => {
    const updated = await alarmRepository.toggle(id);
    setAlarms((prev) => prev.map((a) => (a.id === id ? updated : a)));
    toast.info(
      updated.is_active ? "Alarm Activated" : "Alarm Deactivated",
      `${updated.title} is now ${updated.is_active ? "active" : "disabled"}.`
    );
  };

  const handleDelete = async (id: number) => {
    await alarmRepository.delete(id);
    setAlarms((prev) => prev.filter((a) => a.id !== id));
    toast.success("Alarm Removed", "The alarm was deleted.");
  };

  const handleDuplicate = async (id: number) => {
    try {
      const copy = await alarmRepository.duplicate(id);
      setAlarms((prev) => [copy, ...prev]);
      toast.success("Alarm Duplicated", `Created copy: ${copy.title}`);
    } catch {
      toast.error("Duplicate Failed", "Could not duplicate alarm.");
    }
  };

  const counts = {
    all: alarms.length,
    active: alarms.filter((a) => a.is_active && a.status !== "expired").length,
    disabled: alarms.filter((a) => !a.is_active && a.status !== "expired").length,
    expired: alarms.filter((a) => a.status === "expired").length,
  };

  const tabs = [
    { id: "all", label: "All Alarms", count: counts.all },
    { id: "active", label: "Active", count: counts.active },
    { id: "disabled", label: "Disabled", count: counts.disabled },
    { id: "expired", label: "Expired", count: counts.expired },
  ];

  const filteredAlarms = alarms.filter((a) => {
    if (activeTab === "active") return a.is_active && a.status !== "expired";
    if (activeTab === "disabled") return !a.is_active && a.status !== "expired";
    if (activeTab === "expired") return a.status === "expired";
    return true;
  });

  return (
    <div className="space-y-6 text-left">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black text-slate-100 tracking-tight">Adaptive Alarms</h1>
          <p className="text-xs text-slate-400">Arrival-based dynamic scheduled smart alarms</p>
        </div>
        <Link to="/alarms/new" className="self-start sm:self-auto">
          <Button className="gap-1.5 font-bold shadow-lg shadow-brand-500/20">
            <Plus size={16} />
            Create Smart Alarm
          </Button>
        </Link>
      </div>

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {filteredAlarms.length === 0 ? (
        <EmptyState
          icon={<Clock size={24} />}
          title={alarms.length === 0 ? "No smart alarms yet." : "No alarms in this category"}
          description={
            alarms.length === 0
              ? "Set your required arrival time, travel mode, and morning routine. ADA calculates your optimal wake and leave times."
              : "No alarms currently match the selected filter."
          }
          actionLabel="Create your first arrival alarm"
          onAction={() => (window.location.href = "/alarms/new")}
        />
      ) : (
        <div className="space-y-3">
          {filteredAlarms.map((alarm) => (
            <AlarmCard
              key={alarm.id}
              alarm={alarm}
              onToggle={handleToggle}
              onDelete={handleDelete}
              onDuplicate={handleDuplicate}
            />
          ))}
        </div>
      )}
    </div>
  );
}
