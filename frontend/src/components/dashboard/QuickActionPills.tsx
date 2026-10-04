import { useNavigate } from "react-router-dom";
import { GraduationCap, Briefcase, Dumbbell, Plane, Plus } from "lucide-react";
import { Destination } from "@/core/repositories/interfaces/DestinationRepository";

export interface QuickActionPillsProps {
  destinations: Destination[];
  onSelect?: (dest: Destination) => void;
}

export function QuickActionPills({ destinations }: QuickActionPillsProps) {
  const navigate = useNavigate();

  const getCategoryIcon = (cat: string) => {
    switch (cat) {
      case "college":
        return <GraduationCap size={14} />;
      case "office":
        return <Briefcase size={14} />;
      case "gym":
        return <Dumbbell size={14} />;
      case "airport":
        return <Plane size={14} />;
      default:
        return <GraduationCap size={14} />;
    }
  };

  return (
    <div className="space-y-2 text-left">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Quick Trip Alarms
        </span>
        <button
          onClick={() => navigate("/destinations")}
          className="text-xs text-brand-400 hover:text-brand-300 font-medium"
        >
          Manage All
        </button>
      </div>

      <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
        {destinations.map((dest) => (
          <button
            key={dest.id}
            onClick={() => navigate(`/alarms/new?destId=${dest.id}`)}
            className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-brand-500/40 hover:bg-slate-800/60 text-slate-200 transition-all select-none shrink-0 text-xs font-semibold group"
          >
            <span className="text-brand-400 group-hover:scale-110 transition-transform">
              {getCategoryIcon(dest.category)}
            </span>
            <span>{dest.name}</span>
          </button>
        ))}

        <button
          onClick={() => navigate("/alarms/new")}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-dashed border-slate-700 hover:border-slate-500 text-slate-400 hover:text-slate-200 transition-all select-none shrink-0 text-xs font-medium"
        >
          <Plus size={14} />
          <span>Custom</span>
        </button>
      </div>
    </div>
  );
}
