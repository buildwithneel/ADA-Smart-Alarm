import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "@/core/auth/AuthContext";
import { toast } from "@/core/toast/useToast";
import { assistantApiClient } from "@/core/api/assistantClient";
import {
  AlarmDraft,
  AlarmDraftUpdateRequest,
  AssistantMessage as IAssistantMessage,
  AssistantStatus,
} from "@/core/types/assistant";
import { AIStatusIndicator } from "./AIStatusIndicator";
import { AssistantMessage } from "./AssistantMessage";
import { AssistantInput } from "./AssistantInput";
import { AlarmDraftPreview } from "./AlarmDraftPreview";
import { MissingInformationPrompt } from "./MissingInformationPrompt";
import {
  Sparkles,
  Trash2,
  AlertTriangle,
  ArrowRight,
  Shield,
  Layers,
  Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

export interface AssistantPanelProps {
  className?: string;
  initialPrompt?: string;
}

export const AssistantPanel: React.FC<AssistantPanelProps> = ({
  className,
  initialPrompt = "",
}) => {
  const { currentUser } = useAuth();

  // Assistant State
  const [messages, setMessages] = useState<IAssistantMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [activeDraft, setActiveDraft] = useState<AlarmDraft | null>(null);
  const [missingFields, setMissingFields] = useState<string[]>([]);
  const [clarifications, setClarifications] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [status, setStatus] = useState<AssistantStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load Assistant status on mount
  useEffect(() => {
    let isMounted = true;
    const fetchStatus = async () => {
      try {
        const res = await assistantApiClient.getStatus();
        if (isMounted) setStatus(res);
      } catch (err) {
        console.warn("Failed to load assistant status:", err);
      } finally {
        if (isMounted) setStatusLoading(false);
      }
    };
    fetchStatus();
    return () => {
      isMounted = false;
    };
  }, []);

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, activeDraft, missingFields, isLoading]);

  // Handle sending a user message
  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    setErrorMsg(null);
    const userMsg: IAssistantMessage = {
      id: `usr_${Date.now()}`,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };

    // Optimistically update conversation
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await assistantApiClient.sendMessage({
        message: text,
        conversation_id: conversationId,
        draft_id: activeDraft?.id,
      });

      // Update conversation state
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      // Append assistant reply message
      const assistantMsg: IAssistantMessage = {
        id: `asst_${Date.now()}`,
        role: "assistant",
        content: response.reply || response.message?.content || "",
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // Update draft if returned
      if (response.draft) {
        setActiveDraft(response.draft);
      }

      // Update missing fields & clarifications
      setMissingFields(response.missing_fields || []);
      setClarifications(response.clarification_questions || []);
    } catch (err: any) {
      console.error("Assistant chat error:", err);
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        "Could not connect to ADA Assistant. Please check your connection.";
      setErrorMsg(detail);
      toast.error("Assistant Error", detail);

      const errorReply: IAssistantMessage = {
        id: `err_${Date.now()}`,
        role: "assistant",
        content: `I encountered an issue processing your request: ${detail}. You can create an alarm using our standard form below if needed.`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorReply]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle draft update (user modifies time, date, prep duration, etc.)
  const handleUpdateDraft = async (draftId: string, data: AlarmDraftUpdateRequest) => {
    try {
      const updated = await assistantApiClient.updateDraft(draftId, data);
      setActiveDraft(updated);
      toast.success("Draft Updated", "Alarm draft schedule recalculated.");

      // Add a brief system notice in chat
      const wakeTime = (updated.recommended_wake_time || updated.calculated_wake_time)?.slice(0, 5) || "--:--";
      const leaveTime = (updated.recommended_leave_time || updated.calculated_leave_time)?.slice(0, 5) || "--:--";
      setMessages((prev) => [
        ...prev,
        {
          id: `sys_${Date.now()}`,
          role: "assistant",
          content: `Updated schedule: Wake up at ${wakeTime}, leave at ${leaveTime}.`,
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || "Failed to update draft.";
      toast.error("Update Error", detail);
      throw err;
    }
  };

  // Handle draft confirmation -> creates actual alarm in database
  const handleConfirmDraft = async (draftId: string, idempotencyKey: string) => {
    try {
      setIsConfirming(true);
      const createdAlarm = await assistantApiClient.confirmDraft(draftId, idempotencyKey);
      const wakeStr = (createdAlarm.calculated_wake_time || (createdAlarm as any).wake_up_time)?.slice(0, 5) || "--:--";
      toast.success("Alarm Created!", `"${createdAlarm.title}" scheduled for ${wakeStr}.`);

      // Update local draft status to confirmed
      if (activeDraft) {
        setActiveDraft({ ...activeDraft, status: "confirmed" });
      }

      setMessages((prev) => [
        ...prev,
        {
          id: `confirmed_${Date.now()}`,
          role: "assistant",
          content: `🎉 Confirmed! Your alarm "${createdAlarm.title}" has been successfully scheduled. ADA will monitor traffic and weather to keep you on schedule.`,
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || "Failed to confirm alarm.";
      toast.error("Confirmation Error", detail);
      throw err;
    } finally {
      setIsConfirming(false);
    }
  };

  // Handle discard draft
  const handleDiscardDraft = async (draftId: string) => {
    try {
      await assistantApiClient.discardDraft(draftId);
      setActiveDraft(null);
      setMissingFields([]);
      setClarifications([]);
      toast.info("Draft Discarded", "Alarm draft has been cancelled.");

      setMessages((prev) => [
        ...prev,
        {
          id: `disc_${Date.now()}`,
          role: "assistant",
          content: "Draft discarded. What else would you like to schedule?",
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || "Failed to discard draft.";
      toast.error("Error", detail);
    }
  };

  // Reset conversation
  const handleClearConversation = async () => {
    if (messages.length === 0) return;
    try {
      if (conversationId) {
        await assistantApiClient.deleteConversation(conversationId);
      }
      setMessages([]);
      setActiveDraft(null);
      setMissingFields([]);
      setClarifications([]);
      setConversationId(undefined);
      setErrorMsg(null);
      toast.info("Conversation Cleared", "Started a fresh assistant session.");
    } catch (err: any) {
      // Even if API fails, clear local state
      setMessages([]);
      setActiveDraft(null);
      setConversationId(undefined);
    }
  };

  const displayName = currentUser?.name || currentUser?.email?.split("@")[0] || "You";

  return (
    <div className={`flex flex-col h-[calc(100vh-8rem)] max-w-4xl mx-auto ${className || ""}`}>
      {/* Top Bar: Status and Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-black text-slate-100 tracking-tight flex items-center gap-2">
              <Sparkles className="text-brand-400" size={24} />
              <span>ADA AI Assistant</span>
            </h1>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-500/30">
              Grounded
            </span>
          </div>
          <p className="text-xs text-slate-400 text-left mt-0.5">
            Natural language dynamic alarm scheduling with deterministic route calculation
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          {messages.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleClearConversation}
              className="gap-1.5 text-xs text-slate-400 hover:text-rose-400 hover:border-rose-500/30 h-8"
              title="Clear conversation history"
            >
              <Trash2 size={13} />
              <span>Clear Chat</span>
            </Button>
          )}

          <Link to="/alarms/new">
            <Button
              variant="ghost"
              size="sm"
              className="gap-1 text-xs text-slate-400 hover:text-slate-200 h-8"
            >
              <span>Standard Form</span>
              <ArrowRight size={13} />
            </Button>
          </Link>
        </div>
      </div>

      {/* AI System Health / Indicator */}
      <div className="py-2.5">
        <AIStatusIndicator status={status} isLoading={statusLoading} />
      </div>

      {/* Scrollable Conversation Container */}
      <div className="flex-1 overflow-y-auto space-y-4 p-2 sm:p-4 rounded-2xl bg-slate-950/60 border border-slate-800/80 scrollbar-thin">
        {messages.length === 0 ? (
          /* Empty State / Welcome Screen */
          <div className="h-full flex flex-col items-center justify-center text-center p-6 sm:p-10 space-y-6">
            <div className="w-16 h-16 rounded-3xl gradient-brand flex items-center justify-center text-white shadow-xl shadow-brand-500/30">
              <Sparkles size={32} />
            </div>

            <div className="space-y-2 max-w-md">
              <h2 className="text-lg font-bold text-slate-100">
                How can ADA help you wake up on time?
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed">
                Describe your journey in natural language. ADA parses your destination, calculates deterministic ETAs with Google/Mapbox, and creates an editable schedule draft.
              </p>
            </div>

            {/* Feature Pillars */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-lg text-left">
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                <div className="flex items-center gap-1.5 text-brand-300 text-xs font-semibold">
                  <Shield size={14} />
                  <span>Deterministic</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  AI extracts intent; real routing engines compute final travel ETAs.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                <div className="flex items-center gap-1.5 text-brand-300 text-xs font-semibold">
                  <Clock size={14} />
                  <span>Safe Confirmation</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Review and edit drafts before any alarm is scheduled.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                <div className="flex items-center gap-1.5 text-brand-300 text-xs font-semibold">
                  <Layers size={14} />
                  <span>Personalized</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Respects your preferred morning prep duration and safety cushions.
                </p>
              </div>
            </div>
          </div>
        ) : (
          /* Render Messages */
          <>
            {messages.map((msg) => (
              <AssistantMessage
                key={msg.id}
                message={msg}
                userAvatar={currentUser?.profileImage || undefined}
                userName={displayName}
              />
            ))}

            {/* Loading Indicator */}
            {isLoading && (
              <div className="flex items-center gap-3 text-left w-full">
                <div className="w-8 h-8 rounded-xl gradient-brand flex items-center justify-center text-white shrink-0 shadow-sm animate-pulse">
                  <Sparkles size={16} />
                </div>
                <div className="p-3 rounded-2xl bg-slate-900/90 border border-slate-800 text-slate-400 text-xs flex items-center gap-2">
                  <div className="flex space-x-1">
                    <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" />
                    <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:0.2s]" />
                    <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:0.4s]" />
                  </div>
                  <span>Analyzing request and calculating deterministic schedule...</span>
                </div>
              </div>
            )}

            {/* Missing Information / Clarification Follow-up Prompt */}
            {!isLoading && (missingFields.length > 0 || clarifications.length > 0) && (
              <MissingInformationPrompt
                missingFields={missingFields}
                clarificationQuestions={clarifications}
                onSelectSuggestion={(sug) => handleSendMessage(sug)}
              />
            )}

            {/* Active Alarm Draft Preview Card */}
            {!isLoading && activeDraft && (
              <div className="pt-2">
                <AlarmDraftPreview
                  draft={activeDraft}
                  onConfirm={handleConfirmDraft}
                  onUpdate={handleUpdateDraft}
                  onDiscard={handleDiscardDraft}
                  isConfirming={isConfirming}
                />
              </div>
            )}
          </>
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Error Message Notice */}
      {errorMsg && (
        <div className="flex items-center justify-between p-2.5 my-2 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-200 text-xs">
          <div className="flex items-center gap-2">
            <AlertTriangle size={14} className="text-rose-400 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <Link
            to="/alarms/new"
            className="text-rose-300 underline font-medium hover:text-white shrink-0 ml-2"
          >
            Create Alarm Manually
          </Link>
        </div>
      )}

      {/* Bottom Input Area */}
      <div className="pt-3">
        <AssistantInput
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          initialPrompt={initialPrompt}
        />
      </div>
    </div>
  );
};
