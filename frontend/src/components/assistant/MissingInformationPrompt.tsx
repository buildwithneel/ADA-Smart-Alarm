import React from "react";
import { HelpCircle, MapPin, Clock } from "lucide-react";

export interface MissingInformationPromptProps {
  missingFields: string[];
  clarificationQuestions: string[];
  onSelectSuggestion: (text: string) => void;
}

export const MissingInformationPrompt: React.FC<MissingInformationPromptProps> = ({
  missingFields,
  clarificationQuestions,
  onSelectSuggestion,
}) => {
  if (missingFields.length === 0 && clarificationQuestions.length === 0) {
    return null;
  }

  // Pre-configured fast suggestion pills based on missing field type
  const suggestions: Array<{ label: string; text: string; icon: React.ReactNode }> = [];

  if (missingFields.includes("destination")) {
    suggestions.push(
      { label: "CHARUSAT University", text: "Destination is CHARUSAT University", icon: <MapPin size={12} /> },
      { label: "My Office", text: "Destination is my office", icon: <MapPin size={12} /> },
      { label: "College Campus", text: "Destination is College", icon: <MapPin size={12} /> }
    );
  }

  if (missingFields.includes("arrival_time") || missingFields.includes("arrival_time_clarification")) {
    suggestions.push(
      { label: "9:00 AM (Morning)", text: "I need to arrive by 9:00 AM", icon: <Clock size={12} /> },
      { label: "2:00 PM (Afternoon)", text: "I need to arrive by 2:00 PM", icon: <Clock size={12} /> },
      { label: "10:30 AM", text: "Arrival time is 10:30 AM", icon: <Clock size={12} /> }
    );
  }

  return (
    <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-left space-y-3 shadow-sm">
      <div className="flex items-center gap-2 font-semibold text-xs sm:text-sm text-amber-300">
        <HelpCircle size={16} className="shrink-0 text-amber-400" />
        <span>A few details are missing or ambiguous:</span>
      </div>

      <ul className="space-y-1 text-xs text-amber-200/90 pl-5 list-disc">
        {clarificationQuestions.map((q, idx) => (
          <li key={idx}>{q}</li>
        ))}
      </ul>

      {suggestions.length > 0 && (
        <div className="pt-2 border-t border-amber-500/20 space-y-1.5">
          <p className="text-[11px] font-medium text-amber-300/80">Quick suggestions:</p>
          <div className="flex flex-wrap gap-1.5">
            {suggestions.map((s, idx) => (
              <button
                key={idx}
                onClick={() => onSelectSuggestion(s.text)}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-[11px] font-medium text-amber-100 hover:text-white transition-all transform active:scale-95"
              >
                {s.icon}
                <span>{s.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
