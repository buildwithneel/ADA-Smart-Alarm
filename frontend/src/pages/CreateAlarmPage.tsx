import { useState, useEffect, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  ArrowLeft,
  Sparkles,
  CheckCircle2,
  Navigation,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Stepper } from "@/components/ui/stepper";
import { TransportSelector } from "@/components/ui/transport-selector";
import { RepeatDaysPicker } from "@/components/ui/repeat-days-picker";
import { MapView } from "@/components/maps/MapView";
import { DestinationSearchInput } from "@/components/destinations/DestinationSearchInput";
import { LocationStatus } from "@/components/location/LocationStatus";
import { LocationPermissionDialog } from "@/components/location/LocationPermissionDialog";
import { CurrentLocationIndicator } from "@/components/location/CurrentLocationIndicator";
import { TransportMode } from "@/core/types/alarm";
import { GeoPoint, RouteResult, GeocodingResult } from "@/core/maps";
import { locationService, LocationPermissionState } from "@/core/location/LocationService";
import { useETAEngine } from "@/core/eta/useETAEngine";
import { locationApiClient } from "@/core/api/locationClient";
import { alarmRepository, destinationRepository } from "@/core/repositories";
import { toast } from "@/core/toast/useToast";

const alarmFormSchema = z.object({
  title: z.string().min(2, "Title must be at least 2 characters"),
  destination_name: z.string().min(3, "Please enter a destination"),
  desired_arrival_time: z.string().regex(/^([01]\d|2[0-3]):?([0-5]\d)$/, "Valid time required (HH:MM)"),
  routine_minutes: z.number().min(5).max(180),
  buffer_minutes: z.number().min(0).max(120),
  transport_mode: z.enum(["driving", "transit", "bicycling", "walking"]),
  repeat_days: z.string(),
});

type AlarmFormData = z.infer<typeof alarmFormSchema>;

export function CreateAlarmPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Location & Geolocation state
  const [currentLocation, setCurrentLocation] = useState<GeoPoint>({
    latitude: 23.2156,
    longitude: 72.6369,
  });
  const [locationAccuracy, setLocationAccuracy] = useState<number | null>(null);
  const [permissionState, setPermissionState] = useState<LocationPermissionState>("prompt");
  const [isPermissionDialogOpen, setIsPermissionDialogOpen] = useState(false);
  const [isLocating, setIsLocating] = useState(false);

  // Destination coordinates
  const [destinationCoords, setDestinationCoords] = useState<GeoPoint>({
    latitude: 22.5996,
    longitude: 72.8205,
  });

  // Routing and Route Visualization
  const [routeResult, setRouteResult] = useState<RouteResult | null>(null);
  const [isRouting, setIsRouting] = useState(false);
  const [routingError, setRoutingError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<AlarmFormData>({
    resolver: zodResolver(alarmFormSchema),
    defaultValues: {
      title: "Morning Lecture at CHARUSAT",
      destination_name: "CHARUSAT University, Highway 188, Changa",
      desired_arrival_time: "09:00",
      routine_minutes: 33,
      buffer_minutes: 10,
      transport_mode: "driving",
      repeat_days: "MON,TUE,WED,THU,FRI",
    },
  });

  const watchedValues = watch();

  // ETA Engine — instant optimistic preview + accurate debounced API result
  const { preview } = useETAEngine({
    origin: currentLocation,
    destination: destinationCoords,
    desiredArrivalTime: watchedValues.desired_arrival_time || "09:00",
    preparationMinutes: watchedValues.routine_minutes || 30,
    safetyBufferMinutes: watchedValues.buffer_minutes || 10,
    transportMode: (watchedValues.transport_mode as "driving" | "transit" | "bicycling" | "walking") || "driving",
    routeResult,
  });

  // Check initial location permission
  useEffect(() => {
    locationService.getPermissionStatus().then((status) => {
      setPermissionState(status);
      if (status === "granted") {
        acquireLocation();
      }
    });
  }, []);

  const acquireLocation = async () => {
    setIsLocating(true);
    try {
      const pos = await locationService.getCurrentPosition();
      setCurrentLocation({ latitude: pos.latitude, longitude: pos.longitude });
      setLocationAccuracy(pos.accuracyMeters);
      setPermissionState("granted");
      toast.success("Location Acquired", "Using real-time GPS coordinates for route estimation.");
    } catch (err: any) {
      setPermissionState(err.state || "unavailable");
      if (err.state === "denied_permanently") {
        setIsPermissionDialogOpen(true);
      }
    } finally {
      setIsLocating(false);
    }
  };

  // Prefill if destId is passed in query string
  useEffect(() => {
    const destId = searchParams.get("destId");
    if (destId) {
      destinationRepository.getById(destId).then((dest) => {
        if (dest) {
          setValue("title", `Trip to ${dest.name}`);
          setValue("destination_name", dest.address);
          setValue("routine_minutes", dest.defaultRoutineMinutes);
          setValue("buffer_minutes", dest.defaultBufferMinutes);
          setValue("transport_mode", dest.defaultTransportMode);
          setDestinationCoords({
            latitude: dest.latitude,
            longitude: dest.longitude,
          });
        }
      });
    }
  }, [searchParams, setValue]);

  // Recalculate route on coordinate or transport mode changes
  const calculateRouteAndSchedule = useCallback(async () => {
    setIsRouting(true);
    setRoutingError(null);

    try {
      const route = await locationApiClient.calculateRoute({
        origin: currentLocation,
        destination: destinationCoords,
        transportMode: watchedValues.transport_mode || "driving",
      });
      setRouteResult(route);
      // ETA engine will auto-recalculate via routeResult dependency
    } catch (err: any) {
      console.error("Route calculation error:", err);
      setRoutingError("Failed to calculate live route. Using estimated travel times.");
      // ETA engine still works via Haversine fallback
    } finally {
      setIsRouting(false);
    }
  }, [
    currentLocation,
    destinationCoords,
    watchedValues.transport_mode,
  ]);

  useEffect(() => {
    calculateRouteAndSchedule();
  }, [calculateRouteAndSchedule]);

  // Destination autocomplete selection handler
  const handleDestinationSelect = (item: GeocodingResult) => {
    setValue("destination_name", item.formattedAddress);
    setDestinationCoords({
      latitude: item.latitude,
      longitude: item.longitude,
    });
    toast.info("Destination Selected", item.formattedAddress);
  };

  // Map tap/click destination selection with reverse geocoding
  const handleMapSelectLocation = async (point: GeoPoint) => {
    setDestinationCoords(point);
    toast.info("Pin Placed", "Resolving address...");
    try {
      const rev = await locationApiClient.reverseGeocode(point.latitude, point.longitude);
      setValue("destination_name", rev.formattedAddress);
    } catch {
      setValue("destination_name", `${point.latitude.toFixed(4)}°, ${point.longitude.toFixed(4)}°`);
    }
  };

  const onSubmit = async (data: AlarmFormData) => {
    setIsSubmitting(true);
    try {
      await alarmRepository.create({
        title: data.title,
        destination_name: data.destination_name,
        destination_lat: destinationCoords.latitude,
        destination_lng: destinationCoords.longitude,
        desired_arrival_time: data.desired_arrival_time,
        routine_minutes: data.routine_minutes,
        buffer_minutes: data.buffer_minutes,
        transport_mode: data.transport_mode,
        repeat_days: data.repeat_days,
        use_live_gps: permissionState === "granted",
      });
      toast.success("Adaptive Alarm Created", `Wakes you dynamically at ${preview.wakeTime}.`);
      navigate("/alarms");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 text-left max-w-3xl mx-auto pb-12">
      {/* Header with Navigation */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="p-2 rounded-xl border border-slate-800 hover:bg-slate-900 text-slate-300 transition-colors"
            aria-label="Back"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="text-2xl font-black text-slate-100 tracking-tight">
              Create Adaptive Alarm
            </h1>
            <p className="text-xs text-slate-400">
              Live traffic routing and departure calculation
            </p>
          </div>
        </div>

        {/* Location Status Trigger */}
        <CurrentLocationIndicator
          onUseCurrentLocation={acquireLocation}
          isLoading={isLocating}
          hasLocation={permissionState === "granted"}
          accuracyMeters={locationAccuracy}
        />
      </div>

      {/* Permission Status Notification Bar */}
      <LocationStatus
        state={permissionState}
        accuracyMeters={locationAccuracy}
        onRequestPermission={() => setIsPermissionDialogOpen(true)}
        onRetry={acquireLocation}
      />

      {/* AI Assistant Quick Create Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-2xl bg-gradient-to-r from-brand-600/15 via-indigo-600/10 to-slate-900 border border-brand-500/30">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl gradient-brand flex items-center justify-center text-white shrink-0 shadow-md shadow-brand-500/20">
            <Sparkles size={16} />
          </div>
          <div>
            <p className="text-xs font-bold text-slate-100">Prefer natural language?</p>
            <p className="text-[11px] text-slate-400">
              Describe your journey: &quot;Reach CHARUSAT by 9 AM tomorrow, 30m prep, 10m buffer&quot;
            </p>
          </div>
        </div>
        <Button
          type="button"
          variant="primary"
          size="sm"
          onClick={() => navigate("/assistant")}
          className="gap-1.5 text-xs font-semibold shrink-0 shadow-sm"
        >
          <Sparkles size={13} />
          <span>Create with AI Assistant</span>
        </Button>
      </div>

      {/* Dynamic Schedule Preview Hero Banner */}
      <Card className="p-5 border-brand-500/30 bg-gradient-to-r from-slate-900 via-indigo-950/20 to-slate-900 relative overflow-hidden shadow-2xl">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-brand-400 flex items-center gap-1.5">
            <Sparkles size={14} />
            Live Route & Trigger Preview
          </span>
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-white/5">
              Provider: {preview.provider}
            </span>
            <span className="text-xs font-semibold text-emerald-400">
              On-Time Guarantee
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
          <div className="p-3 rounded-xl bg-slate-950/70 border border-brand-500/20">
            <span className="text-[10px] uppercase font-bold text-brand-400 block mb-1">
              Wake Up
            </span>
            <span className="text-xl font-black text-brand-300">
              {preview.wakeTime}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/70 border border-white/5">
            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
              Leave Home
            </span>
            <span className="text-xl font-black text-slate-100">
              {preview.leaveTime}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/70 border border-emerald-500/20">
            <span className="text-[10px] uppercase font-bold text-emerald-400 block mb-1">
              Planned Arrival
            </span>
            <span className="text-xl font-black text-emerald-300">
              {preview.plannedArrivalTime || "--:-- --"}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/70 border border-white/5">
            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
              Required Target
            </span>
            <span className="text-xl font-black text-slate-100">
              {preview.arrivalTime}
            </span>
          </div>
        </div>

        {/* Calculation Summary Breakdown Strip */}
        <div className="mt-3 pt-3 border-t border-white/5 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-300">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400">Schedule Budget:</span>
            <span className="font-semibold text-slate-200">{watchedValues.routine_minutes || 30}m prep</span>
            <span className="text-slate-500">+</span>
            <span className="font-semibold text-slate-200">{preview.travelMinutes}m travel</span>
            <span className="text-slate-500">+</span>
            <span className="font-semibold text-slate-200">{watchedValues.buffer_minutes || 10}m buffer</span>
            <span className="text-slate-500">=</span>
            <span className="font-bold text-brand-300">
              {Math.floor((preview.totalBudgetMinutes || 0) / 60) > 0 ? `${Math.floor((preview.totalBudgetMinutes || 0) / 60)}h ` : ""}
              {(preview.totalBudgetMinutes || 0) % 60}m total
            </span>
          </div>
          {preview.trafficDelayMinutes > 0 && (
            <span className="text-[11px] text-amber-400 font-medium">
              +{preview.trafficDelayMinutes}m live congestion factored
            </span>
          )}
        </div>
      </Card>

      {/* Interactive Map Visualizer */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="font-semibold flex items-center gap-1 text-slate-300">
            <Navigation size={12} className="text-brand-400" />
            Route Corridor Preview ({preview.distanceText})
          </span>
          <span className="text-[11px] text-slate-400">
            Click map to reposition destination pin
          </span>
        </div>

        <MapView
          center={destinationCoords}
          zoom={12}
          origin={currentLocation}
          destination={destinationCoords}
          originTitle="Starting Point"
          destinationTitle={watchedValues.destination_name?.split(",")[0] || "Destination"}
          routeGeometry={routeResult?.routeGeometry}
          provider={preview.provider}
          isLoading={isRouting}
          error={routingError}
          onSelectLocation={handleMapSelectLocation}
          onCenterLocation={acquireLocation}
          onRetry={calculateRouteAndSchedule}
        />
      </div>

      {/* Main Form */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Card className="p-5 space-y-4 border-white/10 shadow-xl">
          <Input
            id="title"
            label="Alarm Title"
            placeholder="e.g. Morning Lecture at CHARUSAT"
            error={errors.title?.message}
            {...register("title")}
          />

          {/* Debounced Destination Autocomplete Search Input */}
          <DestinationSearchInput
            id="destination_name"
            label="Destination Address or Landmark"
            placeholder="Search address or tap map above..."
            initialValue={watchedValues.destination_name}
            onSelect={handleDestinationSelect}
            error={errors.destination_name?.message}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              id="desired_arrival_time"
              label="Desired Arrival Time"
              type="time"
              error={errors.desired_arrival_time?.message}
              {...register("desired_arrival_time")}
            />

            <TransportSelector
              value={watchedValues.transport_mode}
              onChange={(mode: TransportMode) => setValue("transport_mode", mode)}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <Stepper
              label="Preparation / Routine Cushion"
              value={watchedValues.routine_minutes}
              onChange={(val) => setValue("routine_minutes", val)}
              min={5}
              max={180}
              unit="min"
            />
            <Stepper
              label="Traffic Safety Buffer"
              value={watchedValues.buffer_minutes}
              onChange={(val) => setValue("buffer_minutes", val)}
              min={0}
              max={120}
              unit="min"
            />
          </div>

          <RepeatDaysPicker
            value={watchedValues.repeat_days}
            onChange={(days) => setValue("repeat_days", days)}
          />
        </Card>

        <Button
          type="submit"
          className="w-full text-sm font-bold gap-2 py-3 shadow-xl shadow-brand-500/20"
          isLoading={isSubmitting}
        >
          <CheckCircle2 size={16} />
          Save & Enable Adaptive Alarm
        </Button>
      </form>

      {/* Informative Location Permission Dialog */}
      <LocationPermissionDialog
        isOpen={isPermissionDialogOpen}
        isPermanentlyDenied={permissionState === "denied_permanently"}
        onClose={() => setIsPermissionDialogOpen(false)}
        onAllow={() => {
          setIsPermissionDialogOpen(false);
          locationService.resetPermissionStatus();
          acquireLocation();
        }}
      />
    </div>
  );
}
