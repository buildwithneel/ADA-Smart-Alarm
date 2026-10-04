import { useState } from "react";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Stepper } from "@/components/ui/stepper";
import { MapView } from "@/components/maps/MapView";
import { DestinationSearchInput } from "@/components/destinations/DestinationSearchInput";
import { CurrentLocationIndicator } from "@/components/location/CurrentLocationIndicator";
import { Destination, DestinationCategory } from "@/core/repositories/interfaces/DestinationRepository";
import { GeoPoint, GeocodingResult } from "@/core/maps";
import { locationService } from "@/core/location/LocationService";
import { locationApiClient } from "@/core/api/locationClient";
import { toast } from "@/core/toast/useToast";

export interface AddDestinationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (dest: Omit<Destination, "id">) => void;
}

export function AddDestinationModal({ isOpen, onClose, onSave }: AddDestinationModalProps) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState<DestinationCategory>("college");
  const [address, setAddress] = useState("");
  const [coords, setCoords] = useState<GeoPoint>({ latitude: 22.5996, longitude: 72.8205 });
  const [routine, setRoutine] = useState(30);
  const [buffer, setBuffer] = useState(15);
  const [isLocating, setIsLocating] = useState(false);

  const handleSelectSearchResult = (result: GeocodingResult) => {
    setAddress(result.formattedAddress);
    setCoords({ latitude: result.latitude, longitude: result.longitude });
    if (!name) {
      setName(result.formattedAddress.split(",")[0]);
    }
  };

  const handleMapClick = async (point: GeoPoint) => {
    setCoords(point);
    try {
      const rev = await locationApiClient.reverseGeocode(point.latitude, point.longitude);
      setAddress(rev.formattedAddress);
      if (!name) {
        setName(rev.formattedAddress.split(",")[0]);
      }
    } catch {
      setAddress(`${point.latitude.toFixed(4)}°, ${point.longitude.toFixed(4)}°`);
    }
  };

  const handleUseCurrentLocation = async () => {
    setIsLocating(true);
    try {
      const pos = await locationService.getCurrentPosition();
      const point = { latitude: pos.latitude, longitude: pos.longitude };
      setCoords(point);
      const rev = await locationApiClient.reverseGeocode(point.latitude, point.longitude);
      setAddress(rev.formattedAddress);
      setName("My Current Location");
      toast.success("Location Set", "Loaded your current GPS position.");
    } catch (err: any) {
      toast.error("Location Error", err.message || "Failed to get current location.");
    } finally {
      setIsLocating(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !address) return;

    onSave({
      name,
      category,
      address,
      latitude: coords.latitude,
      longitude: coords.longitude,
      isFavorite: false,
      defaultTransportMode: "driving",
      defaultRoutineMinutes: routine,
      defaultBufferMinutes: buffer,
    });

    setName("");
    setAddress("");
    setCoords({ latitude: 22.5996, longitude: 72.8205 });
    onClose();
  };

  const categories: DestinationCategory[] = ["college", "office", "home", "gym", "airport", "custom"];

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Save New Destination"
      description="Quickly route dynamic alarms to this destination"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          id="name"
          label="Destination Name"
          placeholder="e.g. CHARUSAT Academic Block"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />

        <div className="space-y-1.5 text-left">
          <label className="block text-xs font-semibold text-slate-300">Category</label>
          <div className="grid grid-cols-3 gap-1.5">
            {categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setCategory(cat)}
                className={`py-2 px-3 rounded-xl border text-xs font-semibold capitalize transition-all ${
                  category === cat
                    ? "bg-brand-600 border-brand-500 text-white"
                    : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Address Search with Autocomplete */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-semibold text-slate-300">Address / Location</label>
            <CurrentLocationIndicator
              onUseCurrentLocation={handleUseCurrentLocation}
              isLoading={isLocating}
              className="py-1 px-2 text-[10px]"
            />
          </div>
          <DestinationSearchInput
            initialValue={address}
            placeholder="Search address or landmark..."
            onSelect={handleSelectSearchResult}
          />
        </div>

        {/* Interactive Mini Map to pin location */}
        <div className="space-y-1">
          <span className="text-[11px] text-slate-400 block text-left">
            Tap map to adjust destination coordinates ({coords.latitude.toFixed(4)}°, {coords.longitude.toFixed(4)}°)
          </span>
          <MapView
            center={coords}
            zoom={14}
            destination={coords}
            destinationTitle={name || "Selected Destination"}
            onSelectLocation={handleMapClick}
            className="h-44 rounded-xl"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Stepper
            label="Default Routine"
            value={routine}
            onChange={setRoutine}
            min={10}
            max={120}
          />
          <Stepper
            label="Default Buffer"
            value={buffer}
            onChange={setBuffer}
            min={5}
            max={60}
          />
        </div>

        <div className="flex items-center justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary">
            Save Destination
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
