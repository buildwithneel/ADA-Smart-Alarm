import React, { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Stepper } from "@/components/ui/stepper";
import { toast } from "@/core/toast/useToast";
import { assistantApiClient } from "@/core/api/assistantClient";
import { PersonalizationPreferences } from "@/core/types/assistant";
import { TransportMode } from "@/core/types/alarm";
import {
  Sparkles,
  ShieldCheck,
  RotateCcw,
  Car,
  Bus,
  Footprints,
  Bike,
  History,
  Lightbulb,
  Check,
} from "lucide-react";
import { cn } from "@/core/utils/cn";

export const PersonalizationControls: React.FC = () => {
  const [preferences, setPreferences] = useState<PersonalizationPreferences | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const fetchPrefs = async () => {
      try {
        const data = await assistantApiClient.getPersonalization();
        if (isMounted) setPreferences(data);
      } catch (err: any) {
        console.warn("Failed to load personalization settings:", err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };
    fetchPrefs();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleUpdate = async (field: keyof PersonalizationPreferences, value: any) => {
    if (!preferences) return;
    const updatedLocal = { ...preferences, [field]: value };
    setPreferences(updatedLocal);

    try {
      setIsSaving(true);
      const res = await assistantApiClient.updatePersonalization({ [field]: value });
      setPreferences(res);
      toast.success("Settings Saved", "Your personalization preferences were updated.");
    } catch (err: any) {
      const detail = err?.response?.data?.detail || "Failed to update preferences.";
      toast.error("Error", detail);
      // Revert on error
      const fresh = await assistantApiClient.getPersonalization();
      setPreferences(fresh);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm("Reset all personalization settings and defaults to initial values?")) {
      return;
    }

    try {
      setIsResetting(true);
      const res = await assistantApiClient.resetPersonalization();
      setPreferences(res);
      toast.info("Preferences Reset", "Personalization settings restored to default values.");
    } catch (err: any) {
      toast.error("Error", "Failed to reset personalization.");
    } finally {
      setIsResetting(false);
    }
  };

  if (isLoading) {
    return (
      <Card className="p-5 border-white/10 space-y-4 animate-pulse">
        <div className="h-5 bg-slate-800 rounded w-1/3" />
        <div className="h-20 bg-slate-850 rounded" />
      </Card>
    );
  }

  if (!preferences) {
    return null;
  }

  const transportModes: Array<{ id: TransportMode; label: string; icon: React.ReactNode }> = [
    { id: "driving", label: "Driving", icon: <Car size={14} /> },
    { id: "transit", label: "Transit", icon: <Bus size={14} /> },
    { id: "bicycling", label: "Bicycle", icon: <Bike size={14} /> },
    { id: "walking", label: "Walking", icon: <Footprints size={14} /> },
  ];

  const responseStyles: Array<{ id: "concise" | "detailed" | "friendly"; label: string; desc: string }> = [
    { id: "concise", label: "Concise", desc: "Short, direct schedule calculations" },
    { id: "detailed", label: "Detailed", desc: "Includes route factors & context" },
    { id: "friendly", label: "Friendly", desc: "Conversational & encouraging" },
  ];

  return (
    <Card className="p-4 sm:p-5 space-y-5 border-white/10 text-left">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg gradient-brand flex items-center justify-center text-white">
            <Sparkles size={14} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100">AI Assistant & Personalization</h3>
            <p className="text-[11px] text-slate-400">
              User-controlled defaults for schedule drafting and conversations
            </p>
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={handleReset}
          disabled={isResetting || isSaving}
          className="gap-1.5 text-xs text-slate-400 hover:text-rose-400 hover:border-rose-500/30 self-start sm:self-auto h-7 px-2.5"
        >
          <RotateCcw size={12} className={isResetting ? "animate-spin" : ""} />
          <span>Reset Defaults</span>
        </Button>
      </div>

      {/* Routine Steppers */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Stepper
          label="Default Preparation Routine"
          value={preferences.default_preparation_time}
          onChange={(val) => handleUpdate("default_preparation_time", val)}
          min={5}
          max={180}
        />
        <Stepper
          label="Default Safety Buffer"
          value={preferences.default_safety_buffer}
          onChange={(val) => handleUpdate("default_safety_buffer", val)}
          min={0}
          max={90}
        />
      </div>

      {/* Preferred Transport Mode */}
      <div className="space-y-2">
        <label className="text-xs font-semibold text-slate-300">
          Default Transportation Mode
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {transportModes.map((m) => {
            const isSelected =
              (preferences.default_transportation || preferences.default_transportation_mode) === m.id;
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => handleUpdate("default_transportation", m.id)}
                className={cn(
                  "flex items-center justify-center gap-2 p-2 rounded-xl border text-xs font-medium transition-all",
                  isSelected
                    ? "bg-brand-600/20 border-brand-500 text-brand-300 font-semibold shadow-sm"
                    : "border-slate-800 bg-slate-900/50 text-slate-400 hover:text-slate-200"
                )}
              >
                {m.icon}
                <span>{m.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Assistant Response Style */}
      <div className="space-y-2">
        <label className="text-xs font-semibold text-slate-300">
          Assistant Response Style
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {responseStyles.map((style) => {
            const isSelected = preferences.assistant_response_style === style.id;
            return (
              <button
                key={style.id}
                type="button"
                onClick={() => handleUpdate("assistant_response_style", style.id)}
                className={cn(
                  "p-2.5 rounded-xl border text-left transition-all space-y-0.5",
                  isSelected
                    ? "bg-brand-600/20 border-brand-500 text-brand-200 shadow-sm"
                    : "border-slate-800 bg-slate-900/40 text-slate-400 hover:text-slate-200"
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-200">{style.label}</span>
                  {isSelected && <Check size={12} className="text-brand-400" />}
                </div>
                <p className="text-[10px] text-slate-400 leading-tight">{style.desc}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Privacy and History Toggles */}
      <div className="space-y-3 pt-2 border-t border-slate-800">
        {/* Save Conversation History */}
        <div className="flex items-center justify-between gap-4 p-3 rounded-xl bg-slate-900/50 border border-slate-800/80">
          <div className="space-y-0.5">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
              <History size={14} className="text-brand-400" />
              <span>Save Assistant Conversation History</span>
            </div>
            <p className="text-[11px] text-slate-400">
              Allows you to resume recent scheduling chats and view past drafts.
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={preferences.save_conversation_history}
            onClick={() =>
              handleUpdate("save_conversation_history", !preferences.save_conversation_history)
            }
            className={cn(
              "w-11 h-6 rounded-full transition-colors relative shrink-0",
              preferences.save_conversation_history ? "bg-brand-600" : "bg-slate-800"
            )}
          >
            <span
              className={cn(
                "block w-4 h-4 rounded-full bg-white transition-transform absolute top-1 left-1",
                preferences.save_conversation_history ? "translate-x-5" : "translate-x-0"
              )}
            />
          </button>
        </div>

        {/* Use Alarm History Suggestions */}
        <div className="flex items-center justify-between gap-4 p-3 rounded-xl bg-slate-900/50 border border-slate-800/80">
          <div className="space-y-0.5">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
              <Lightbulb size={14} className="text-amber-400" />
              <span>Use Alarm History Suggestions</span>
            </div>
            <p className="text-[11px] text-slate-400">
              Pre-populates saved destination names and typical prep durations in quick pills.
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={preferences.use_alarm_history_suggestions}
            onClick={() =>
              handleUpdate(
                "use_alarm_history_suggestions",
                !preferences.use_alarm_history_suggestions
              )
            }
            className={cn(
              "w-11 h-6 rounded-full transition-colors relative shrink-0",
              preferences.use_alarm_history_suggestions ? "bg-brand-600" : "bg-slate-800"
            )}
          >
            <span
              className={cn(
                "block w-4 h-4 rounded-full bg-white transition-transform absolute top-1 left-1",
                preferences.use_alarm_history_suggestions ? "translate-x-5" : "translate-x-0"
              )}
            />
          </button>
        </div>
      </div>

      {/* Privacy Guarantees Footer */}
      <div className="flex items-start gap-2 p-2.5 rounded-xl bg-slate-900/30 border border-white/5 text-[11px] text-slate-400">
        <ShieldCheck size={14} className="text-emerald-400 shrink-0 mt-0.5" />
        <p>
          Personalization only suggests defaults and never overrides your explicit instructions.
          ADA does not track your location in the background or infer sensitive routines without consent.
        </p>
      </div>
    </Card>
  );
};
