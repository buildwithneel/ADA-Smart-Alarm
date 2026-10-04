import React, { useState, useRef, useEffect } from "react";
import { Send, CornerDownLeft, Sparkles, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/core/utils/cn";

export interface AssistantInputProps {
  onSendMessage: (message: string) => Promise<void>;
  isLoading?: boolean;
  placeholder?: string;
  className?: string;
  initialPrompt?: string;
}

const STARTER_PROMPTS = [
  "I need to reach CHARUSAT by 9 AM tomorrow. 30m prep, 10m buffer.",
  "Wake me up early enough to reach my office by 8:30 AM.",
  "Meeting at 2:00 PM tomorrow. I need 25 minutes to get ready.",
  "Add a 15-minute safety buffer because parking is difficult.",
];

export const AssistantInput: React.FC<AssistantInputProps> = ({
  onSendMessage,
  isLoading = false,
  placeholder = "e.g., Reach CHARUSAT by 9 AM tomorrow, 30m prep, 10m buffer...",
  className,
  initialPrompt = "",
}) => {
  const [input, setInput] = useState(initialPrompt);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const maxLength = 1000;

  useEffect(() => {
    if (initialPrompt) {
      setInput(initialPrompt);
    }
  }, [initialPrompt]);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        140
      )}px`;
    }
  }, [input]);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    await onSendMessage(trimmed);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSelectStarter = (promptText: string) => {
    setInput(promptText);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const charsRemaining = maxLength - input.length;
  const isNearLimit = charsRemaining < 100;

  return (
    <div className={cn("space-y-3", className)}>
      {/* Starter Prompts (Pills) */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1.5 scrollbar-none text-[11px] select-none">
        <span className="flex items-center gap-1 text-slate-500 font-medium shrink-0 pl-1">
          <Sparkles size={11} className="text-brand-400" />
          <span>Try:</span>
        </span>
        {STARTER_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleSelectStarter(prompt)}
            disabled={isLoading}
            className="shrink-0 px-2.5 py-1 rounded-full bg-slate-900/80 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input Box Card */}
      <form
        onSubmit={handleSubmit}
        className={cn(
          "relative flex flex-col rounded-2xl bg-slate-900/90 border transition-all p-3 shadow-lg backdrop-blur-xl",
          isLoading
            ? "border-brand-500/40 ring-1 ring-brand-500/20"
            : "border-slate-800 hover:border-slate-700 focus-within:border-brand-500/50 focus-within:ring-1 focus-within:ring-brand-500/30"
        )}
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value.slice(0, maxLength))}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isLoading}
          rows={2}
          aria-label="Natural language alarm prompt"
          className="w-full bg-transparent resize-none border-0 text-slate-100 placeholder:text-slate-500 text-xs sm:text-sm focus:outline-none focus:ring-0 leading-relaxed max-h-36 scrollbar-thin"
        />

        <div className="flex items-center justify-between pt-2 mt-1 border-t border-slate-800/80 text-[11px]">
          <div className="flex items-center gap-2 text-slate-500">
            <span
              className={cn(
                "font-mono",
                isNearLimit ? "text-amber-400 font-bold" : "text-slate-500"
              )}
            >
              {input.length}/{maxLength}
            </span>
            <span className="hidden sm:inline text-slate-600">•</span>
            <span className="hidden sm:inline-flex items-center gap-1 text-slate-500">
              <CornerDownLeft size={10} /> Enter to send, Shift+Enter for newline
            </span>
          </div>

          <div className="flex items-center gap-2">
            {input.length > 0 && !isLoading && (
              <button
                type="button"
                onClick={() => setInput("")}
                className="p-1 text-slate-500 hover:text-slate-300 transition-colors"
                title="Clear input"
                aria-label="Clear input"
              >
                <XCircle size={14} />
              </button>
            )}

            <Button
              type="submit"
              size="sm"
              variant="primary"
              disabled={!input.trim() || isLoading}
              className="gap-1.5 h-8 px-3 rounded-xl text-xs font-semibold shadow-md shadow-brand-500/20 disabled:shadow-none"
            >
              <span>{isLoading ? "Thinking..." : "Send"}</span>
              <Send size={12} className={isLoading ? "animate-pulse" : ""} />
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
};
