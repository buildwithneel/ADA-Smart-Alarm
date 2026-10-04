import React from "react";
import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";
import { AssistantStatus } from "@/core/types/assistant";
import { cn } from "@/core/utils/cn";

export interface AIStatusIndicatorProps {
  status: AssistantStatus | null;
  isLoading?: boolean;
}

export const AIStatusIndicator: React.FC<AIStatusIndicatorProps> = ({ status, isLoading }) => {
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/80 border border-slate-800 text-xs text-slate-400 animate-pulse">
        <span className="w-2 h-2 rounded-full bg-brand-400" />
        <span>Connecting to ADA Assistant...</span>
      </div>
    );
  }

  const isOnline = status?.status === "online";

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 p-2 sm:px-3 sm:py-2 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm text-xs">
      <div className="flex items-center gap-2">
        <div className="relative flex items-center justify-center">
          <span
            className={cn(
              "w-2.5 h-2.5 rounded-full",
              isOnline ? "bg-emerald-400" : "bg-amber-400"
            )}
          />
          {isOnline && (
            <span className="absolute w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping opacity-75" />
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="font-semibold text-slate-200">
            {isOnline ? "AI Assistant Ready" : "Deterministic Engine Active"}
          </span>
          <span className="text-[10px] text-slate-500 font-mono px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700">
            {status?.provider || "deterministic"}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3 text-[11px] text-slate-400">
        <span>Grounded schedule math</span>
        <Link
          to="/alarms/new"
          className="inline-flex items-center gap-0.5 text-brand-400 hover:text-brand-300 font-medium transition-colors"
          title="Manual alarm creation form"
        >
          <span>Standard Form</span>
          <ArrowUpRight size={12} />
        </Link>
      </div>
    </div>
  );
};
