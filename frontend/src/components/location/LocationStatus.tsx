import React from "react";
import { Navigation, AlertCircle, RefreshCw, ShieldAlert } from "lucide-react";
import { LocationPermissionState } from "@/core/location/LocationService";

import { cn } from "@/core/utils/cn";

export interface LocationStatusProps {
  state: LocationPermissionState;
  accuracyMeters?: number | null;
  onRequestPermission?: () => void;
  onRetry?: () => void;
  className?: string;
  compact?: boolean;
}

export const LocationStatus: React.FC<LocationStatusProps> = ({
  state,
  accuracyMeters,
  onRequestPermission,
  onRetry,
  className,
  compact = false,
}) => {
  const renderContent = () => {
    switch (state) {
      case "granted":
        return (
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-xs font-semibold text-emerald-400">
                Live GPS Active
              </span>
              {accuracyMeters && (
                <span className="text-[10px] text-slate-400 font-mono">
                  (±{Math.round(accuracyMeters)}m)
                </span>
              )}
            </div>
            {!compact && (
              <span className="text-[10px] text-slate-500">Private • In-Memory</span>
            )}
          </div>
        );

      case "denied_permanently":
        return (
          <div className="flex items-center justify-between w-full gap-2">
            <div className="flex items-center gap-2 text-rose-400">
              <ShieldAlert size={14} />
              <span className="text-xs font-semibold">Location Blocked in Browser</span>
            </div>
            {onRequestPermission && (
              <button
                type="button"
                onClick={onRequestPermission}
                className="text-[11px] font-bold text-rose-400 hover:text-rose-300 underline"
              >
                Help
              </button>
            )}
          </div>
        );

      case "unavailable":
      case "timeout":
      case "gps_disabled":
        return (
          <div className="flex items-center justify-between w-full gap-2">
            <div className="flex items-center gap-2 text-amber-400">
              <AlertCircle size={14} />
              <span className="text-xs font-semibold">Unable to Acquire Location</span>
            </div>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="flex items-center gap-1 text-[11px] font-bold text-amber-400 hover:text-amber-300 transition-colors"
              >
                <RefreshCw size={11} />
                Retry
              </button>
            )}
          </div>
        );

      case "prompt":
      default:
        return (
          <div className="flex items-center justify-between w-full gap-2">
            <div className="flex items-center gap-2 text-brand-400">
              <Navigation size={14} />
              <span className="text-xs font-medium text-slate-300">
                Location access needed for dynamic ETA
              </span>
            </div>
            {onRequestPermission && (
              <button
                type="button"
                onClick={onRequestPermission}
                className="px-2.5 py-1 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-[11px] font-bold transition-all shadow-sm"
              >
                Enable
              </button>
            )}
          </div>
        );
    }
  };

  return (
    <div
      className={cn(
        "px-3 py-2 rounded-xl bg-slate-900/80 border border-slate-800 backdrop-blur-sm transition-all",
        state === "granted" && "border-emerald-500/20 bg-emerald-950/10",
        state === "denied_permanently" && "border-rose-500/20 bg-rose-950/10",
        state === "unavailable" && "border-amber-500/20 bg-amber-950/10",
        className
      )}
    >
      {renderContent()}
    </div>
  );
};
