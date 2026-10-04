import { ReactNode } from "react";
import { motion } from "framer-motion";
import { emptyStateVariants } from "@/core/animations/variants";
import { Button } from "./button";

export interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <motion.div
      variants={emptyStateVariants}
      initial="initial"
      animate="animate"
      className="p-8 rounded-2xl border border-dashed border-slate-800 bg-slate-900/30 text-center flex flex-col items-center justify-center space-y-3"
    >
      <div className="w-12 h-12 rounded-2xl bg-slate-800/80 border border-white/5 flex items-center justify-center text-slate-400">
        {icon}
      </div>
      <div>
        <h4 className="text-sm font-bold text-slate-200">{title}</h4>
        <p className="text-xs text-slate-400 max-w-xs mt-1">{description}</p>
      </div>
      {actionLabel && onAction && (
        <Button size="sm" variant="secondary" onClick={onAction} className="mt-2">
          {actionLabel}
        </Button>
      )}
    </motion.div>
  );
}
