import { GraduationCap, Briefcase, Dumbbell, Plane, MapPin, Star, Clock, Trash2, Edit } from "lucide-react";
import { Destination } from "@/core/repositories/interfaces/DestinationRepository";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface DestinationCardProps {
  destination: Destination;
  onSelect?: (dest: Destination) => void;
  onToggleFavorite?: (id: string) => void;
  onDelete?: (id: string) => void;
  onEdit?: (dest: Destination) => void;
}

export function DestinationCard({
  destination,
  onSelect,
  onToggleFavorite,
  onDelete,
  onEdit,
}: DestinationCardProps) {
  const getCategoryIcon = (cat: string) => {
    switch (cat) {
      case "college":
        return <GraduationCap size={16} />;
      case "office":
        return <Briefcase size={16} />;
      case "gym":
        return <Dumbbell size={16} />;
      case "airport":
        return <Plane size={16} />;
      default:
        return <MapPin size={16} />;
    }
  };

  return (
    <Card className="p-4 text-left border-white/10 hover:border-brand-500/40 transition-all flex flex-col justify-between group">
      <div>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400">
              {getCategoryIcon(destination.category)}
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <h3 className="text-sm font-bold text-slate-100">{destination.name}</h3>
                {destination.isFavorite && (
                  <Star size={13} className="text-amber-400 fill-amber-400" />
                )}
              </div>
              <Badge variant="neutral" className="mt-1 text-[10px] lowercase">
                {destination.category}
              </Badge>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => onToggleFavorite?.(destination.id)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-amber-400 transition-colors"
              aria-label="Favorite destination"
            >
              <Star
                size={15}
                className={destination.isFavorite ? "text-amber-400 fill-amber-400" : ""}
              />
            </button>
            {onEdit && (
              <button
                onClick={() => onEdit(destination)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 transition-colors"
                aria-label="Edit destination"
              >
                <Edit size={14} />
              </button>
            )}
            {onDelete && (
              <button
                onClick={() => onDelete(destination.id)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 transition-colors"
                aria-label="Delete destination"
              >
                <Trash2 size={14} />
              </button>
            )}
          </div>
        </div>

        <p className="text-xs text-slate-400 flex items-start gap-1.5 mt-3 line-clamp-2">
          <MapPin size={13} className="text-slate-500 shrink-0 mt-0.5" />
          <span>{destination.address}</span>
        </p>
      </div>

      <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-[11px] text-slate-400">
        <span className="flex items-center gap-1">
          <Clock size={12} className="text-brand-400" />
          Routine: {destination.defaultRoutineMinutes}m • Buffer: {destination.defaultBufferMinutes}m
        </span>
        {onSelect && (
          <button
            onClick={() => onSelect(destination)}
            className="text-xs font-bold text-brand-400 hover:text-brand-300"
          >
            Create Alarm →
          </button>
        )}
      </div>
    </Card>
  );
}
