import { Minus, Plus } from "lucide-react";
import { cn } from "@/core/utils/cn";

export interface StepperProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  label?: string;
  unit?: string;
  className?: string;
}

export function Stepper({
  value,
  onChange,
  min = 0,
  max = 180,
  step = 5,
  label,
  unit = "min",
  className,
}: StepperProps) {
  const handleDecrement = () => {
    if (value - step >= min) onChange(value - step);
  };

  const handleIncrement = () => {
    if (value + step <= max) onChange(value + step);
  };

  return (
    <div className={cn("space-y-1.5 text-left", className)}>
      {label && <label className="block text-xs font-semibold text-slate-300">{label}</label>}
      <div className="flex items-center justify-between p-1 bg-slate-900/60 border border-slate-800 rounded-xl">
        <button
          type="button"
          onClick={handleDecrement}
          disabled={value <= min}
          className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white disabled:opacity-30 disabled:pointer-events-none transition-all active:scale-95"
          aria-label="Decrease value"
        >
          <Minus size={16} />
        </button>
        <div className="flex items-baseline gap-1 select-none">
          <span className="text-base font-extrabold text-slate-100">{value}</span>
          <span className="text-xs text-slate-400 font-medium">{unit}</span>
        </div>
        <button
          type="button"
          onClick={handleIncrement}
          disabled={value >= max}
          className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white disabled:opacity-30 disabled:pointer-events-none transition-all active:scale-95"
          aria-label="Increase value"
        >
          <Plus size={16} />
        </button>
      </div>
    </div>
  );
}
