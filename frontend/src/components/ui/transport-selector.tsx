import { Car, Train, Bike, Footprints } from "lucide-react";
import { TransportMode } from "@/core/types/alarm";
import { cn } from "@/core/utils/cn";

export interface TransportSelectorProps {
  value: TransportMode | "motorcycle";
  onChange: (mode: TransportMode) => void;
  className?: string;
}

export function TransportSelector({ value, onChange, className }: TransportSelectorProps) {
  const options = [
    { id: "walking" as TransportMode, label: "Walk", icon: Footprints, speed: "~4 km/h" },
    { id: "bicycling" as TransportMode, label: "Bicycle", icon: Bike, speed: "~15 km/h" },
    { id: "driving" as TransportMode, label: "Car", icon: Car, speed: "Live Traffic" },
    { id: "transit" as TransportMode, label: "Transit", icon: Train, speed: "Schedules" },
  ];

  return (
    <div className={cn("space-y-1.5 text-left", className)}>
      <label className="block text-xs font-semibold text-slate-300">Transportation Mode</label>
      <div className="grid grid-cols-4 gap-2">
        {options.map((opt) => {
          const Icon = opt.icon;
          const isSelected = value === opt.id;
          return (
            <button
              key={opt.id}
              type="button"
              onClick={() => onChange(opt.id)}
              className={cn(
                "p-3 rounded-xl border flex flex-col items-center justify-center gap-1.5 transition-all text-center select-none outline-none",
                isSelected
                  ? "bg-brand-600/20 border-brand-500 text-brand-300 shadow-md shadow-brand-500/10"
                  : "bg-slate-900/50 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700"
              )}
            >
              <Icon size={18} className={isSelected ? "text-brand-400" : "text-slate-400"} />
              <span className="text-xs font-bold leading-none">{opt.label}</span>
              <span className="text-[10px] text-slate-400 leading-none">{opt.speed}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
