import { MapPin, Navigation, Car, AlertCircle } from "lucide-react";
import { cn } from "@/core/utils/cn";

export interface MapPlaceholderProps {
  originName?: string;
  destinationName: string;
  travelMinutes: number;
  trafficDelayMinutes?: number;
  className?: string;
}

export function MapPlaceholder({
  originName = "Current Location",
  destinationName,
  travelMinutes,
  trafficDelayMinutes = 0,
  className,
}: MapPlaceholderProps) {
  return (
    <div
      className={cn(
        "relative w-full h-44 rounded-2xl overflow-hidden bg-slate-900 border border-slate-800 shadow-inner flex flex-col justify-between p-3 select-none",
        className
      )}
    >
      {/* Subtle Map Grid Lines */}
      <svg
        className="absolute inset-0 w-full h-full stroke-slate-800/40 [mask-image:radial-gradient(ellipse_at_center,white,transparent)]"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern id="map-grid" width="24" height="24" patternUnits="userSpaceOnUse">
            <path d="M 24 0 L 0 0 0 24" fill="none" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#map-grid)" />
      </svg>

      {/* Simulated Route Path */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 400 180">
        {/* Normal Route Path (Blue) */}
        <path
          d="M 60 130 C 120 130, 140 70, 200 70 C 260 70, 300 45, 340 45"
          fill="none"
          stroke="#4f46e5"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray="4 2"
        />
        {/* Traffic Delay Segment (Amber) */}
        {trafficDelayMinutes > 0 && (
          <path
            d="M 170 85 C 200 70, 240 70, 270 55"
            fill="none"
            stroke="#f59e0b"
            strokeWidth="5"
            strokeLinecap="round"
          />
        )}
      </svg>

      {/* Top Floating Badge */}
      <div className="relative z-10 flex items-center justify-between">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-950/80 border border-white/10 backdrop-blur-md text-[11px] font-semibold text-slate-200">
          <Navigation size={12} className="text-brand-400" />
          <span>{originName}</span>
        </div>
        <div className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-brand-600/90 text-white text-[11px] font-bold shadow-md shadow-brand-500/20">
          <Car size={12} />
          <span>{travelMinutes} min</span>
        </div>
      </div>

      {/* Origin Pin */}
      <div className="absolute left-12 bottom-8 z-10 flex items-center gap-1">
        <div className="w-4 h-4 rounded-full bg-brand-500 border-2 border-white ring-4 ring-brand-500/20 shadow-md" />
      </div>

      {/* Destination Pin */}
      <div className="absolute right-12 top-6 z-10 flex items-center gap-1">
        <div className="p-1 rounded-full bg-rose-500 text-white shadow-lg shadow-rose-500/30">
          <MapPin size={14} />
        </div>
      </div>

      {/* Bottom Floating Bar */}
      <div className="relative z-10 flex items-center justify-between px-3 py-1.5 rounded-xl bg-slate-950/85 border border-white/10 backdrop-blur-md text-xs">
        <span className="font-semibold text-slate-200 truncate max-w-[200px]">
          {destinationName}
        </span>
        {trafficDelayMinutes > 0 ? (
          <span className="flex items-center gap-1 text-[11px] font-bold text-amber-400">
            <AlertCircle size={12} />
            +{trafficDelayMinutes}m traffic
          </span>
        ) : (
          <span className="text-[11px] font-semibold text-emerald-400">
            Route Clear
          </span>
        )}
      </div>
    </div>
  );
}
