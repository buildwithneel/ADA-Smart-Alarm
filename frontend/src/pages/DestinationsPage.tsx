import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Search } from "lucide-react";
import { DestinationCard } from "@/components/destinations/DestinationCard";
import { AddDestinationModal } from "@/components/destinations/AddDestinationModal";
import { Button } from "@/components/ui/button";
import { destinationRepository } from "@/core/repositories";
import { Destination } from "@/core/repositories/interfaces/DestinationRepository";
import { toast } from "@/core/toast/useToast";

export function DestinationsPage() {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [search, setSearch] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    async function load() {
      const data = await destinationRepository.getAll();
      setDestinations(data);
    }
    load();
  }, []);

  const handleToggleFavorite = async (id: string) => {
    const updated = await destinationRepository.toggleFavorite(id);
    setDestinations((prev) => prev.map((d) => (d.id === id ? updated : d)));
    toast.info("Favorite Updated", `${updated.name} favorite status changed.`);
  };

  const handleDelete = async (id: string) => {
    await destinationRepository.delete(id);
    setDestinations((prev) => prev.filter((d) => d.id !== id));
    toast.success("Destination Removed", "Destination was deleted.");
  };

  const handleSave = async (newDest: Omit<Destination, "id">) => {
    const created = await destinationRepository.create(newDest);
    setDestinations((prev) => [created, ...prev]);
    toast.success("Destination Saved", `${created.name} is ready for smart alarms.`);
  };

  const filtered = destinations.filter(
    (d) =>
      d.name.toLowerCase().includes(search.toLowerCase()) ||
      d.category.toLowerCase().includes(search.toLowerCase()) ||
      d.address.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 text-left">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black text-slate-100 tracking-tight">Saved Destinations</h1>
          <p className="text-xs text-slate-400">Quick-route targets for your dynamic alarms</p>
        </div>
        <Button onClick={() => setIsModalOpen(true)} className="gap-1.5 self-start sm:self-auto">
          <Plus size={16} />
          Add Destination
        </Button>
      </div>

      {/* Search Input */}
      <div className="relative">
        <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter destinations by name or category (e.g. college, office)..."
          className="w-full bg-slate-900/60 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-100 placeholder:text-slate-500 outline-none focus:border-brand-500 transition-colors"
        />
      </div>

      {/* Destinations Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filtered.map((dest) => (
          <DestinationCard
            key={dest.id}
            destination={dest}
            onToggleFavorite={handleToggleFavorite}
            onDelete={handleDelete}
            onSelect={(d) => navigate(`/alarms/new?destId=${d.id}`)}
          />
        ))}
      </div>

      <AddDestinationModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSave}
      />
    </div>
  );
}
