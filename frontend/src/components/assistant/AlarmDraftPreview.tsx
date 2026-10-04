import React, { useState } from "react";
import {
  AlarmDraft,
  AlarmDraftUpdateRequest,
} from "@/core/types/assistant";
import { TransportMode } from "@/core/types/alarm";
import {
  Clock,
  MapPin,
  Car,
  Bus,
  Footprints,
  Bike,
  CheckCircle2,
  Trash2,
  Edit3,
  Info,
  Calendar,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/core/utils/cn";

export interface AlarmDraftPreviewProps {
  draft: AlarmDraft;
  onConfirm: (draftId: string, idempotencyKey: string) => Promise<void>;
  onUpdate: (draftId: string, data: AlarmDraftUpdateRequest) => Promise<void>;
  onDiscard: (draftId: string) => Promise<void>;
  isConfirming?: boolean;
}

export const AlarmDraftPreview: React.FC<AlarmDraftPreviewProps> = ({
  draft,
  onConfirm,
  onUpdate,
  onDiscard,
  isConfirming = false,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(draft.title);
  const [editDest, setEditDest] = useState(draft.destination_text);
  const [editTime, setEditTime] = useState(draft.arrival_time?.slice(0, 5) || "09:00");
  const [editDate, setEditDate] = useState(draft.arrival_date || "");
  const [editPrep, setEditPrep] = useState(draft.preparation_time);
  const [editBuffer, setEditBuffer] = useState(draft.safety_buffer);
  const [editMode, setEditMode] = useState<TransportMode>(draft.transportation_mode);
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [hasConfirmed, setHasConfirmed] = useState(draft.status === "confirmed");

  const handleSaveEdit = async () => {
    try {
      setIsSavingEdit(true);
      await onUpdate(draft.id, {
        title: editTitle,
        destination_text: editDest,
        arrival_time: `${editTime}:00`,
        arrival_date: editDate || undefined,
        preparation_time: editPrep,
        safety_buffer: editBuffer,
        transportation_mode: editMode,
      });
      setIsEditing(false);
    } finally {
      setIsSavingEdit(false);
    }
  };

  const handleConfirmClick = async () => {
    if (hasConfirmed || isConfirming) return;
    const idempotencyKey = `idem-${draft.id}-${Date.now()}`;
    await onConfirm(draft.id, idempotencyKey);
    setHasConfirmed(true);
  };

  const formatDateTime = (val?: string) => {
    if (!val) return "--:--";
    if (/^\d{2}:\d{2}(:\d{2})?$/.test(val)) {
      return val.slice(0, 5);
    }
    try {
      const dt = new Date(val);
      if (isNaN(dt.getTime())) {
        return val.slice(0, 5);
      }
      return dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
    } catch {
      return val.slice(0, 5) || "--:--";
    }
  };

  const getPlannedTarget = () => {
    if (draft.planned_arrival_time) return formatDateTime(draft.planned_arrival_time);
    if (draft.arrival_time) {
      const [h, m] = draft.arrival_time.split(":").map(Number);
      const totalMinutes = h * 60 + m - (draft.safety_buffer || 0);
      const targetH = Math.floor(((totalMinutes + 1440) % 1440) / 60);
      const targetM = (totalMinutes + 1440) % 60;
      return `${String(targetH).padStart(2, "0")}:${String(targetM).padStart(2, "0")}`;
    }
    return "--:--";
  };

  const transportIcons: Record<TransportMode, React.ReactNode> = {
    driving: <Car size={14} />,
    transit: <Bus size={14} />,
    bicycling: <Bike size={14} />,
    walking: <Footprints size={14} />,
  };

  return (
    <div
      className={cn(
        "rounded-2xl border transition-all text-left shadow-lg overflow-hidden",
        hasConfirmed
          ? "bg-emerald-950/20 border-emerald-500/40"
          : "bg-slate-900/90 border-slate-800 backdrop-blur-xl"
      )}
    >
      {/* Top Banner / Header */}
      <div className="p-4 sm:p-5 border-b border-white/5 flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full border",
                hasConfirmed
                  ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-300"
                  : "bg-brand-500/20 border-brand-500/40 text-brand-300"
              )}
            >
              {hasConfirmed ? "Confirmed & Scheduled" : "Editable Alarm Draft"}
            </span>
            <span className="text-[11px] text-slate-500 font-mono">
              v-deterministic
            </span>
          </div>
          <h3 className="text-base sm:text-lg font-bold text-slate-100 truncate">
            {draft.title}
          </h3>
        </div>

        <div className="flex items-center gap-2">
          {!hasConfirmed && (
            <>
              <button
                onClick={() => setIsEditing(!isEditing)}
                className="px-2.5 py-1.5 rounded-xl border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-xs font-semibold text-slate-300 flex items-center gap-1.5 transition-colors"
                title="Edit draft parameters"
              >
                <Edit3 size={13} />
                <span>{isEditing ? "Close Edit" : "Edit Details"}</span>
              </button>
              <button
                onClick={() => onDiscard(draft.id)}
                className="p-1.5 rounded-xl border border-rose-500/20 hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 transition-colors"
                title="Discard draft"
                aria-label="Discard draft"
              >
                <Trash2 size={15} />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Inline Editing Drawer */}
      {isEditing && (
        <div className="p-4 bg-slate-950/60 border-b border-white/5 space-y-3 animate-in fade-in duration-200">
          <p className="text-xs font-semibold text-brand-300 flex items-center gap-1.5">
            <Edit3 size={13} />
            Modify Extracted Parameters:
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="space-y-1">
              <label className="text-[11px] text-slate-400">Alarm Title</label>
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-brand-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-slate-400">Destination</label>
              <input
                type="text"
                value={editDest}
                onChange={(e) => setEditDest(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-brand-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-slate-400">Arrival Time</label>
              <input
                type="time"
                value={editTime}
                onChange={(e) => setEditTime(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-brand-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-slate-400">Arrival Date</label>
              <input
                type="date"
                value={editDate}
                onChange={(e) => setEditDate(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-brand-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-slate-400">Prep Routine (minutes)</label>
              <input
                type="number"
                min={0}
                max={360}
                value={editPrep}
                onChange={(e) => setEditPrep(parseInt(e.target.value) || 0)}
                className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-brand-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-slate-400">Safety Buffer (minutes)</label>
              <input
                type="number"
                min={0}
                max={180}
                value={editBuffer}
                onChange={(e) => setEditBuffer(parseInt(e.target.value) || 0)}
                className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 focus:outline-none focus:border-brand-500"
              />
            </div>

            <div className="sm:col-span-2 space-y-1">
              <label className="text-[11px] text-slate-400">Transport Mode</label>
              <div className="flex gap-2">
                {(["driving", "transit", "bicycling", "walking"] as TransportMode[]).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setEditMode(m)}
                    className={cn(
                      "px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 capitalize transition-all",
                      editMode === m
                        ? "bg-brand-500/20 border-brand-500 text-brand-300"
                        : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
                    )}
                  >
                    {transportIcons[m]}
                    <span>{m}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsEditing(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleSaveEdit}
              disabled={isSavingEdit}
            >
              {isSavingEdit ? "Recalculating..." : "Apply & Recalculate"}
            </Button>
          </div>
        </div>
      )}

      {/* Main Schedule Timeline Grid */}
      <div className="p-4 sm:p-5 space-y-5">
        {/* Core Schedule Math Progression */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* 1. Wake-up */}
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1 relative overflow-hidden">
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span className="font-semibold text-amber-400 flex items-center gap-1">
                <Clock size={12} />
                Wake-up Time
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 font-mono">
                -{draft.preparation_time}m prep
              </span>
            </div>
            <div className="text-xl sm:text-2xl font-black text-white font-mono tracking-tight">
              {formatDateTime(draft.recommended_wake_time || (draft as any).calculated_wake_time)}
            </div>
            <p className="text-[11px] text-slate-500">
              Allows {draft.preparation_time} min for morning routine
            </p>
          </div>

          {/* 2. Leave Time */}
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1 relative overflow-hidden">
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span className="font-semibold text-brand-400 flex items-center gap-1">
                <Car size={12} />
                Departure Time
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-brand-500/10 text-brand-300 font-mono">
                {draft.travel_duration_minutes || draft.estimated_travel_duration || 0}m travel
              </span>
            </div>
            <div className="text-xl sm:text-2xl font-black text-white font-mono tracking-tight">
              {formatDateTime(draft.recommended_leave_time || (draft as any).calculated_leave_time)}
            </div>
            <p className="text-[11px] text-slate-500">
              {draft.traffic_delay_minutes > 0
                ? `Includes ${draft.traffic_delay_minutes} min traffic delay`
                : "Optimal routing conditions"}
            </p>
          </div>

          {/* 3. Arrival */}
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1 relative overflow-hidden">
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span className="font-semibold text-emerald-400 flex items-center gap-1">
                <CheckCircle2 size={12} />
                Required Arrival
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 font-mono">
                +{draft.safety_buffer}m buffer
              </span>
            </div>
            <div className="text-xl sm:text-2xl font-black text-white font-mono tracking-tight">
              {draft.arrival_time?.slice(0, 5) || "09:00"}
            </div>
            <p className="text-[11px] text-slate-500">
              Planned target: {getPlannedTarget()}
            </p>
          </div>
        </div>

        {/* Location & Trip Breakdown */}
        <div className="p-3 rounded-xl bg-slate-950/40 border border-white/5 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 rounded-lg bg-brand-500/20 text-brand-300 flex items-center justify-center shrink-0">
              <MapPin size={15} />
            </div>
            <div className="min-w-0">
              <p className="font-semibold text-slate-200 truncate">{draft.destination_text}</p>
              <p className="text-[11px] text-slate-400 truncate">
                {draft.destination_address || "GPS Coordinates verified"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-800 text-[11px] text-slate-300 font-medium capitalize">
              {transportIcons[draft.transportation_mode]}
              <span>{draft.transportation_mode}</span>
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-800 text-[11px] text-slate-300 font-medium font-mono">
              <Calendar size={11} />
              <span>{draft.arrival_date || "Tomorrow"}</span>
            </span>
          </div>
        </div>

        {/* Grounded Explanation Box */}
        {(draft.grounded_explanation || draft.explanation) && (
          <div className="p-3.5 rounded-xl bg-brand-500/5 border border-brand-500/20 text-slate-300 text-xs leading-relaxed space-y-1.5">
            <div className="flex items-center gap-1.5 font-semibold text-brand-300 text-[11px]">
              <Info size={13} />
              <span>Schedule Rationale (ADA Deterministic Engine)</span>
            </div>
            <p className="whitespace-pre-line text-slate-300 text-[11px] sm:text-xs">
              {draft.grounded_explanation || draft.explanation}
            </p>
          </div>
        )}

        {/* Confirmation CTA Footer */}
        {!hasConfirmed ? (
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3">
            <p className="text-[11px] text-slate-400 text-center sm:text-left">
              🔒 No alarm will be created without your explicit confirmation.
            </p>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Button
                variant="secondary"
                size="sm"
                className="w-full sm:w-auto text-xs"
                onClick={() => onDiscard(draft.id)}
              >
                Discard
              </Button>
              <Button
                variant="primary"
                size="sm"
                className="w-full sm:w-auto gap-2 font-bold text-xs shadow-md shadow-brand-500/20"
                onClick={handleConfirmClick}
                disabled={isConfirming}
              >
                {isConfirming ? (
                  <span>Scheduling Alarm...</span>
                ) : (
                  <>
                    <CheckCircle2 size={15} />
                    <span>Confirm & Schedule Alarm</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        ) : (
          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between text-xs text-emerald-200">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
              <span>
                <strong>Smart Alarm Confirmed!</strong> ADA is now actively monitoring traffic and will wake you up on time.
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
