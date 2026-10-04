import React from "react";
import { Navigation, Loader2 } from "lucide-react";
import { cn } from "@/core/utils/cn";

export interface CurrentLocationIndicatorProps {
  onUseCurrentLocation: () => void;
  isLoading?: boolean;
  hasLocation?: boolean;
  accuracyMeters?: number | null;
  className?: string;
}

export const CurrentLocationIndicator: React.FC<CurrentLocationIndicatorProps> = ({
  onUseCurrentLocation,
  isLoading = false,
  hasLocation = false,
  accuracyMeters,
  className,
}) => {
  return (
    <button
      type="button"
      onClick={onUseCurrentLocation}
      disabled={isLoading}
      className={cn(
        "group flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all",
        hasLocation
          ? "bg-slate-900 border-emerald-500/30 text-emerald-400 hover:bg-slate-800"
          : "bg-slate-900/80 border-slate-800 text-slate-300 hover:border-brand-500/40 hover:text-white",
        className
      )}
      title="Set starting point to current GPS location"
    >
      {isLoading ? (
        <Loader2 size={13} className="animate-spin text-brand-400" />
      ) : (
        <span className="relative flex h-3 w-3 items-center justify-center">
          {hasLocation && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          )}
          <Navigation
            size={12}
            className={cn(
              "transition-transform group-hover:scale-110",
              hasLocation ? "text-emerald-400 fill-emerald-400/20" : "text-brand-400"
            )}
          />
        </span>
      )}
      <span>{hasLocation ? "Using Current GPS" : "Use My Current Location"}</span>
      {hasLocation && accuracyMeters && (
        <span className="text-[10px] text-slate-500 font-mono">
          ±{Math.round(accuracyMeters)}m
        </span>
      )}
    </button>
  );
};
