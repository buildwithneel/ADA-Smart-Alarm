import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Bell,
  Clock,
  Navigation,
  AlertOctagon,
  Volume2,
  CheckCheck,
  ArrowRight,
} from "lucide-react";
import { Sheet } from "@/components/ui/sheet";
import { ApiNotificationRepository } from "@/core/repositories/api/ApiNotificationRepository";
import { AppNotification, NotificationType } from "@/core/types/notification";
import { playAlarmChime } from "@/core/utils/audioAlert";

export interface NotificationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function NotificationDrawer({ isOpen, onClose }: NotificationDrawerProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [unreadOnly, setUnreadOnly] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["notifications", unreadOnly],
    queryFn: () => ApiNotificationRepository.getNotifications(unreadOnly, 30),
    enabled: isOpen,
    refetchInterval: 15000,
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => ApiNotificationRepository.markAsRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["unread-notifications-count"] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => ApiNotificationRepository.markAllAsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["unread-notifications-count"] });
    },
  });

  const notifications = data?.items || [];
  const unreadCount = data?.unreadCount || 0;

  const getNotificationIcon = (type: NotificationType) => {
    switch (type) {
      case "ALARM_WAKE":
        return <Clock size={16} className="text-violet-400" />;
      case "ALARM_DEPARTURE_REMINDER":
        return <Navigation size={16} className="text-amber-400" />;
      case "ALARM_SCHEDULE_CHANGED":
        return <AlertTriangle size={16} className="text-sky-400" />;
      case "ALARM_URGENT_CHANGE":
      case "ALARM_MISSED":
        return <AlertOctagon size={16} className="text-rose-400" />;
      case "ALARM_COMPLETED":
        return <CheckCircle2 size={16} className="text-emerald-400" />;
      default:
        return <Bell size={16} className="text-brand-400" />;
    }
  };

  const formatRelativeTime = (isoString: string) => {
    const diffMs = Date.now() - new Date(isoString).getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return new Date(isoString).toLocaleDateString([], { month: "short", day: "numeric" });
  };

  const handleNotificationClick = (n: AppNotification) => {
    if (!n.readAt) {
      markReadMutation.mutate(n.id);
    }
    if (n.alarmId) {
      onClose();
      navigate(`/alarms/${n.alarmId}`);
    }
  };

  return (
    <Sheet isOpen={isOpen} onClose={onClose} title="Notification Center">
      <div className="space-y-4">
        {/* Controls Header */}
        <div className="flex items-center justify-between pb-3 border-b border-white/5">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setUnreadOnly(false)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                !unreadOnly
                  ? "bg-brand-500/20 text-brand-300 border border-brand-500/30"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              All
            </button>
            <button
              onClick={() => setUnreadOnly(true)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                unreadOnly
                  ? "bg-brand-500/20 text-brand-300 border border-brand-500/30"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Unread {unreadCount > 0 && `(${unreadCount})`}
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => playAlarmChime()}
              className="text-[11px] text-slate-400 hover:text-violet-300 flex items-center gap-1 transition-colors px-2 py-1 rounded bg-slate-800/40 border border-slate-700/40"
              title="Test Web Audio wake chime"
            >
              <Volume2 size={12} />
              Chime
            </button>

            {unreadCount > 0 && (
              <button
                onClick={() => markAllReadMutation.mutate()}
                disabled={markAllReadMutation.isPending}
                className="text-[11px] text-slate-400 hover:text-brand-300 flex items-center gap-1 transition-colors"
              >
                <CheckCheck size={12} />
                Mark all read
              </button>
            )}
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="py-12 text-center text-slate-400 text-xs animate-pulse">
            Loading notifications...
          </div>
        )}

        {/* Empty State */}
        {!isLoading && notifications.length === 0 && (
          <div className="py-12 text-center text-slate-400 space-y-2">
            <div className="w-10 h-10 rounded-full bg-slate-800/60 border border-white/5 mx-auto flex items-center justify-center text-slate-500">
              <Bell size={18} />
            </div>
            <p className="text-xs font-medium text-slate-300">All caught up</p>
            <p className="text-[11px] text-slate-500 max-w-[200px] mx-auto">
              No new alerts. ADA will notify you when departure or traffic conditions change.
            </p>
          </div>
        )}

        {/* Notification Feed */}
        <div className="space-y-2.5">
          {notifications.map((n) => {
            const isUnread = !n.readAt && n.status !== "READ";
            return (
              <div
                key={n.id}
                onClick={() => handleNotificationClick(n)}
                className={`p-3.5 rounded-xl border transition-all text-left cursor-pointer group ${
                  isUnread
                    ? "bg-slate-800/80 border-brand-500/30 shadow-sm shadow-brand-500/5 hover:border-brand-500/50"
                    : "bg-slate-900/40 border-slate-800/60 hover:border-slate-700 hover:bg-slate-850/50"
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-slate-800/90 border border-white/5 shrink-0 mt-0.5">
                    {getNotificationIcon(n.type)}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <h5
                        className={`text-xs font-semibold truncate ${
                          isUnread ? "text-slate-100 font-bold" : "text-slate-300"
                        }`}
                      >
                        {n.title}
                      </h5>
                      <span className="text-[10px] text-slate-500 shrink-0">
                        {formatRelativeTime(n.createdAt)}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-400 leading-relaxed mb-2 line-clamp-2">
                      {n.body}
                    </p>

                    <div className="flex items-center justify-between text-[10px]">
                      {n.scheduleVersion && (
                        <span className="text-slate-500 font-mono">
                          Schedule v{n.scheduleVersion}
                        </span>
                      )}

                      {n.alarmId && (
                        <span className="text-brand-400 group-hover:text-brand-300 font-medium flex items-center gap-1 transition-colors ml-auto">
                          View Alarm <ArrowRight size={10} />
                        </span>
                      )}
                    </div>
                  </div>

                  {isUnread && (
                    <div className="w-2 h-2 rounded-full bg-brand-500 shrink-0 mt-1.5" />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Sheet>
  );
}
