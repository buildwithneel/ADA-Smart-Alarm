import { cn } from "@/core/utils/cn";

export interface ProgressBarProps {
  value: number; // 0 to 100
  max?: number;
  label?: string;
  sublabel?: string;
  variant?: "brand" | "success" | "warning" | "danger";
  className?: string;
}

export function ProgressBar({
  value,
  max = 100,
  label,
  sublabel,
  variant = "brand",
  className,
}: ProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  const barVariants = {
    brand: "bg-brand-500",
    success: "bg-emerald-500",
    warning: "bg-amber-500",
    danger: "bg-rose-500",
  };

  return (
    <div className={cn("w-full space-y-1.5 text-left", className)}>
      {(label || sublabel) && (
        <div className="flex items-center justify-between text-xs">
          {label && <span className="font-semibold text-slate-300">{label}</span>}
          {sublabel && <span className="text-slate-400">{sublabel}</span>}
        </div>
      )}
      <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden p-0.5 border border-white/5">
        <div
          className={cn("h-full rounded-full transition-all duration-500", barVariants[variant])}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
