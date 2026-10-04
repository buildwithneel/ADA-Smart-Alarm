import { motion } from "framer-motion";
import { cn } from "@/core/utils/cn";
import { trafficRadarVariants } from "@/core/animations/variants";

export interface StatusIndicatorProps {
  status: "active" | "warning" | "error" | "neutral";
  label?: string;
  pulse?: boolean;
}

export function StatusIndicator({ status, label, pulse = true }: StatusIndicatorProps) {
  const dotColors = {
    active: "bg-emerald-400 shadow-emerald-400/50",
    warning: "bg-amber-400 shadow-amber-400/50",
    error: "bg-rose-400 shadow-rose-400/50",
    neutral: "bg-slate-400 shadow-slate-400/30",
  };

  const textColors = {
    active: "text-emerald-400",
    warning: "text-amber-400",
    error: "text-rose-400",
    neutral: "text-slate-400",
  };

  return (
    <div className="inline-flex items-center gap-2">
      <div className="relative flex items-center justify-center">
        {pulse && (
          <motion.span
            variants={trafficRadarVariants}
            animate="pulse"
            className={cn("absolute w-3.5 h-3.5 rounded-full opacity-75", dotColors[status])}
          />
        )}
        <span className={cn("relative w-2 h-2 rounded-full shadow-sm", dotColors[status])} />
      </div>
      {label && <span className={cn("text-xs font-semibold uppercase tracking-wider", textColors[status])}>{label}</span>}
    </div>
  );
}
