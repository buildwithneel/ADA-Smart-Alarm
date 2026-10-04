import React from "react";
import { Sparkles, User as UserIcon, Clock } from "lucide-react";
import { AssistantMessage as IAssistantMessage } from "@/core/types/assistant";
import { cn } from "@/core/utils/cn";

export interface AssistantMessageProps {
  message: IAssistantMessage;
  userAvatar?: string;
  userName?: string;
}

export const AssistantMessage: React.FC<AssistantMessageProps> = ({
  message,
  userAvatar,
  userName = "You",
}) => {
  const isUser = message.role === "user";

  const formattedTime = new Date(message.created_at || Date.now()).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div
      className={cn(
        "flex gap-3 text-left w-full transition-opacity duration-300",
        isUser ? "justify-end" : "justify-start"
      )}
      role="article"
      aria-label={`${isUser ? "User" : "ADA Assistant"} message`}
    >
      {/* Assistant Avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-xl gradient-brand flex items-center justify-center text-white shrink-0 shadow-sm shadow-brand-500/20 mt-0.5">
          <Sparkles size={16} />
        </div>
      )}

      {/* Message Bubble Container */}
      <div className={cn("max-w-[85%] sm:max-w-[75%] space-y-1", isUser && "items-end")}>
        <div className={cn("flex items-center gap-2 text-[10px] text-slate-500", isUser && "justify-end")}>
          <span className="font-semibold text-slate-400">{isUser ? userName : "ADA Assistant"}</span>
          <span>•</span>
          <span className="flex items-center gap-1 font-mono">
            <Clock size={10} />
            {formattedTime}
          </span>
        </div>

        <div
          className={cn(
            "p-3.5 sm:p-4 rounded-2xl text-xs sm:text-sm leading-relaxed shadow-sm",
            isUser
              ? "gradient-brand text-white rounded-tr-sm"
              : "bg-slate-900/90 border border-slate-800 text-slate-200 rounded-tl-sm backdrop-blur-md"
          )}
        >
          {/* Formatted multi-line text */}
          <div className="whitespace-pre-wrap space-y-2">
            {message.content.split("\n").map((line, idx) => {
              if (line.startsWith("• ") || line.startsWith("- ")) {
                return (
                  <div key={idx} className="flex items-start gap-2 pl-1">
                    <span className="text-brand-400 font-bold shrink-0">•</span>
                    <span>{line.replace(/^[•\-]\s*/, "")}</span>
                  </div>
                );
              }
              return <p key={idx}>{line}</p>;
            })}
          </div>
        </div>
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0 mt-0.5 shadow-sm overflow-hidden">
          {userAvatar ? (
            <img src={userAvatar} alt={userName} className="w-full h-full object-cover" />
          ) : (
            <UserIcon size={16} />
          )}
        </div>
      )}
    </div>
  );
};
