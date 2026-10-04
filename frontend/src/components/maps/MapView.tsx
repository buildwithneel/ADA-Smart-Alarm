import React, { useRef, useState, useEffect, useCallback } from "react";
import {
  Navigation,
  MapPin,
  Plus,
  Minus,
  Maximize2,
  Crosshair,
  Loader2,
  AlertTriangle,
  RotateCcw,
} from "lucide-react";
import { GeoPoint, MapProviderName } from "@/core/maps/models/types";
import { MapController } from "@/core/maps/services/MapController";
import { cn } from "@/core/utils/cn";

export interface MapViewProps {
  center?: GeoPoint;
  zoom?: number;
  origin?: GeoPoint | null;
  destination?: GeoPoint | null;
  originTitle?: string;
  destinationTitle?: string;
  routeGeometry?: string | null;
  provider?: MapProviderName | string;
  interactive?: boolean;
  isLoading?: boolean;
  error?: string | null;
  className?: string;
  onSelectLocation?: (point: GeoPoint) => void;
  onCenterLocation?: () => void;
  onRetry?: () => void;
}

export const MapView: React.FC<MapViewProps> = ({
  center = { latitude: 22.5996, longitude: 72.8205 },
  zoom = 13,
  origin = null,
  destination = null,
  originTitle = "Starting Point",
  destinationTitle = "Destination",
  routeGeometry = null,
  provider = "google",
  interactive = true,
  isLoading = false,
  error = null,
  className,
  onSelectLocation,
  onCenterLocation,
  onRetry,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [viewport, setViewport] = useState({ center, zoom });
  const [controller] = useState(
    () => new MapController(center, zoom, (next) => setViewport(next))
  );

  // Synchronize incoming center changes
  useEffect(() => {
    controller.setCenter(center, zoom);
  }, [center.latitude, center.longitude, zoom, controller]);

  // Auto-fit bounds if both origin and destination are present
  const handleFitRoute = useCallback(() => {
    if (origin && destination) {
      controller.fitRoute(origin, destination);
    }
  }, [origin, destination, controller]);

  // Convert GPS coordinates to container SVG coordinate space (normalized projection)
  const projectPoint = useCallback(
    (point: GeoPoint) => {
      const scale = Math.pow(2, viewport.zoom - 10) * 120;
      const x = 200 + (point.longitude - viewport.center.longitude) * scale * 1.5;
      const y = 140 - (point.latitude - viewport.center.latitude) * scale * 1.5;
      return { x, y };
    },
    [viewport]
  );

  // Handle click on map to choose / update destination
  const handleMapClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!interactive || !onSelectLocation || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const scale = Math.pow(2, viewport.zoom - 10) * 120;
    const normX = (clickX / rect.width) * 400;
    const normY = (clickY / rect.height) * 280;

    const deltaLng = (normX - 200) / (scale * 1.5);
    const deltaLat = (140 - normY) / (scale * 1.5);

    const selected: GeoPoint = {
      latitude: parseFloat((viewport.center.latitude + deltaLat).toFixed(6)),
      longitude: parseFloat((viewport.center.longitude + deltaLng).toFixed(6)),
    };

    onSelectLocation(selected);
  };

  const originProj = origin ? projectPoint(origin) : null;
  const destProj = destination ? projectPoint(destination) : null;

  return (
    <div
      ref={containerRef}
      onClick={handleMapClick}
      className={cn(
        "relative w-full h-64 md:h-72 rounded-2xl overflow-hidden bg-slate-950 border border-slate-800 shadow-xl select-none group",
        interactive && "cursor-crosshair",
        className
      )}
      role="region"
      aria-label="Interactive map visualizer"
    >
      {/* Background Cartographic Vector Grid with Dark Aesthetic */}
      <svg
        className="absolute inset-0 w-full h-full stroke-slate-800/40 pointer-events-none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern id="ada-map-grid" width="32" height="32" patternUnits="userSpaceOnUse">
            <path d="M 32 0 L 0 0 0 32" fill="none" strokeWidth="0.8" />
          </pattern>
          <linearGradient id="route-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="100%" stopColor="#a855f7" />
          </linearGradient>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>
        <rect width="100%" height="100%" fill="url(#ada-map-grid)" />

        {/* Ambient Arterial Road Vector Lines */}
        <g className="stroke-slate-800/70" strokeWidth="2" strokeLinecap="round">
          <path d="M -20 180 Q 150 160 250 80 T 450 60" fill="none" />
          <path d="M 60 -20 Q 120 120 220 220 T 380 320" fill="none" />
          <path d="M 220 30 Q 240 140 280 280" fill="none" strokeDasharray="3 3" />
        </g>

        {/* Route Polyline Connecting Origin and Destination */}
        {originProj && destProj && (
          <g>
            {/* Background Glow */}
            <path
              d={`M ${originProj.x} ${originProj.y} Q ${(originProj.x + destProj.x) / 2 + 25} ${(originProj.y + destProj.y) / 2 - 25} ${destProj.x} ${destProj.y}`}
              fill="none"
              stroke="#818cf8"
              strokeWidth="6"
              strokeOpacity="0.3"
              filter="url(#glow)"
            />
            {/* Main Polyline Path */}
            <path
              d={`M ${originProj.x} ${originProj.y} Q ${(originProj.x + destProj.x) / 2 + 25} ${(originProj.y + destProj.y) / 2 - 25} ${destProj.x} ${destProj.y}`}
              fill="none"
              stroke="url(#route-gradient)"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeDasharray={routeGeometry ? undefined : "6 4"}
              className="animate-pulse"
            />
          </g>
        )}
      </svg>

      {/* Origin Marker (Current Location / GPS Pin) */}
      {originProj && (
        <div
          style={{ left: `${originProj.x}px`, top: `${originProj.y}px` }}
          className="absolute -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none transition-all duration-300"
        >
          <div className="relative flex items-center justify-center">
            <span className="animate-ping absolute h-7 w-7 rounded-full bg-brand-400 opacity-60" />
            <span className="h-5 w-5 rounded-full bg-brand-500 border-2 border-white ring-2 ring-brand-400/40 shadow-lg flex items-center justify-center">
              <span className="h-1.5 w-1.5 rounded-full bg-white" />
            </span>
          </div>
          {originTitle && (
            <div className="absolute top-6 left-1/2 -translate-x-1/2 whitespace-nowrap px-2 py-0.5 rounded-md bg-slate-950/80 border border-white/10 text-[10px] font-bold text-brand-300 backdrop-blur-md shadow-md">
              {originTitle}
            </div>
          )}
        </div>
      )}

      {/* Destination Marker (Selected Target Pin) */}
      {destProj && (
        <div
          style={{ left: `${destProj.x}px`, top: `${destProj.y}px` }}
          className="absolute -translate-x-1/2 -translate-y-full z-20 pointer-events-none transition-all duration-300"
        >
          <div className="flex flex-col items-center">
            <div className="p-1.5 rounded-full bg-rose-500 text-white shadow-xl shadow-rose-500/40 ring-2 ring-white/20 animate-bounce">
              <MapPin size={15} />
            </div>
            <div className="w-1.5 h-1.5 bg-rose-500 rotate-45 -mt-1 shadow-sm" />
          </div>
          {destinationTitle && (
            <div className="mt-1 whitespace-nowrap px-2 py-0.5 rounded-md bg-slate-950/85 border border-rose-500/30 text-[10px] font-bold text-rose-300 backdrop-blur-md shadow-md">
              {destinationTitle}
            </div>
          )}
        </div>
      )}

      {/* Map Interactive HUD Controls (Zoom, Pan, Center) */}
      <div className="absolute right-3 top-3 z-30 flex flex-col gap-1.5">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            controller.zoomIn();
          }}
          className="p-2 rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-slate-700/60 text-slate-200 transition-all shadow-md active:scale-95"
          aria-label="Zoom In"
        >
          <Plus size={14} />
        </button>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            controller.zoomOut();
          }}
          className="p-2 rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-slate-700/60 text-slate-200 transition-all shadow-md active:scale-95"
          aria-label="Zoom Out"
        >
          <Minus size={14} />
        </button>
        {onCenterLocation && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onCenterLocation();
            }}
            className="p-2 rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-slate-700/60 text-brand-400 hover:text-brand-300 transition-all shadow-md active:scale-95"
            aria-label="Center on user location"
          >
            <Crosshair size={14} />
          </button>
        )}
        {origin && destination && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              handleFitRoute();
            }}
            className="p-2 rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-slate-700/60 text-slate-300 hover:text-white transition-all shadow-md active:scale-95"
            aria-label="Fit route within view"
          >
            <Maximize2 size={14} />
          </button>
        )}
      </div>

      {/* Top Left Floating Provider & Instructions Badge */}
      <div className="absolute left-3 top-3 z-30 flex items-center gap-2">
        <div className="px-2.5 py-1 rounded-lg bg-slate-950/80 border border-white/10 backdrop-blur-md text-[10px] font-semibold text-slate-300 flex items-center gap-1.5 shadow-md">
          <Navigation size={11} className="text-brand-400" />
          <span className="capitalize">{provider} Maps Engine</span>
        </div>
        {interactive && (
          <span className="hidden sm:inline-block text-[10px] text-slate-400 bg-slate-950/60 px-2 py-0.5 rounded-md border border-white/5 backdrop-blur-sm">
            Click map to pick destination
          </span>
        )}
      </div>

      {/* Loading Overlay State */}
      {isLoading && (
        <div className="absolute inset-0 z-40 bg-slate-950/70 backdrop-blur-[2px] flex items-center justify-center gap-2 text-xs font-semibold text-brand-300">
          <Loader2 size={18} className="animate-spin text-brand-400" />
          <span>Calculating Route & Traffic...</span>
        </div>
      )}

      {/* Error State Banner */}
      {error && (
        <div className="absolute inset-0 z-40 bg-slate-950/85 backdrop-blur-sm flex flex-col items-center justify-center p-4 text-center">
          <AlertTriangle size={24} className="text-rose-400 mb-2" />
          <p className="text-xs font-semibold text-slate-200 mb-1">Map & Routing Error</p>
          <p className="text-[11px] text-slate-400 max-w-xs mb-3">{error}</p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-bold text-white transition-all"
            >
              <RotateCcw size={12} />
              Retry Calculation
            </button>
          )}
        </div>
      )}
    </div>
  );
};
