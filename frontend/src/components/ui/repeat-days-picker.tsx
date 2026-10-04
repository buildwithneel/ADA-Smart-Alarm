import { cn } from "@/core/utils/cn";

export interface RepeatDaysPickerProps {
  value: string; // e.g. "MON,TUE,WED"
  onChange: (value: string) => void;
  className?: string;
}

const DAYS = [
  { id: "MON", label: "M", full: "Mon" },
  { id: "TUE", label: "T", full: "Tue" },
  { id: "WED", label: "W", full: "Wed" },
  { id: "THU", label: "T", full: "Thu" },
  { id: "FRI", label: "F", full: "Fri" },
  { id: "SAT", label: "S", full: "Sat" },
  { id: "SUN", label: "S", full: "Sun" },
];

export function RepeatDaysPicker({ value, onChange, className }: RepeatDaysPickerProps) {
  const selectedDays = value ? value.split(",").filter(Boolean) : [];

  const toggleDay = (dayId: string) => {
    let next: string[];
    if (selectedDays.includes(dayId)) {
      next = selectedDays.filter((d) => d !== dayId);
    } else {
      next = [...selectedDays, dayId];
    }
    onChange(next.join(","));
  };

  const setPreset = (preset: "weekdays" | "weekends" | "everyday" | "once") => {
    if (preset === "weekdays") onChange("MON,TUE,WED,THU,FRI");
    else if (preset === "weekends") onChange("SAT,SUN");
    else if (preset === "everyday") onChange("MON,TUE,WED,THU,FRI,SAT,SUN");
    else onChange("");
  };

  return (
    <div className={cn("space-y-2 text-left", className)}>
      <div className="flex items-center justify-between">
        <label className="block text-xs font-semibold text-slate-300">Repeat Schedule</label>
        <div className="flex items-center gap-1.5 text-[10px]">
          <button
            type="button"
            onClick={() => setPreset("weekdays")}
            className="text-brand-400 hover:underline font-medium"
          >
            Weekdays
          </button>
          <span className="text-slate-600">•</span>
          <button
            type="button"
            onClick={() => setPreset("everyday")}
            className="text-brand-400 hover:underline font-medium"
          >
            Daily
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between gap-1.5">
        {DAYS.map((d) => {
          const isSelected = selectedDays.includes(d.id);
          return (
            <button
              key={d.id}
              type="button"
              onClick={() => toggleDay(d.id)}
              className={cn(
                "w-9 h-9 rounded-xl text-xs font-bold transition-all select-none outline-none border",
                isSelected
                  ? "bg-brand-600 border-brand-500 text-white shadow-md shadow-brand-500/20 scale-105"
                  : "bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200"
              )}
              title={d.full}
            >
              {d.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
