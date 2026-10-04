import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  Volume2,
  Navigation,
  AlertTriangle,
  Send,
  ShieldCheck,
  AlertOctagon,
  Clock,
  Info,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { toast } from "@/core/toast/useToast";
import { ApiNotificationRepository } from "@/core/repositories/api/ApiNotificationRepository";
import { playAlarmChime } from "@/core/utils/audioAlert";
import {
  isPushSupported,
  getNotificationPermission,
  requestNotificationPermission,
  subscribeToWebPush,
} from "@/core/utils/pushManager";

export function NotificationSettingsCard() {
  const queryClient = useQueryClient();
  const [permissionState, setPermissionState] = useState<NotificationPermission>("default");
  const [isSubscribing, setIsSubscribing] = useState(false);
  const [isSendingTest, setIsSendingTest] = useState(false);

  useEffect(() => {
    setPermissionState(getNotificationPermission());
  }, []);

  const { data: prefs, isLoading } = useQuery({
    queryKey: ["notification-preferences"],
    queryFn: () => ApiNotificationRepository.getPreferences(),
  });

  const updateMutation = useMutation({
    mutationFn: (newPrefs: Parameters<typeof ApiNotificationRepository.updatePreferences>[0]) =>
      ApiNotificationRepository.updatePreferences(newPrefs),
    onSuccess: (updated) => {
      queryClient.setQueryData(["notification-preferences"], updated);
      toast.success("Preferences Saved", "Notification preferences updated.");
    },
    onError: () => {
      toast.error("Save Failed", "Unable to update notification preferences.");
    },
  });

  const handleToggle = (key: string, val: boolean) => {
    updateMutation.mutate({ [key]: val } as any);
  };

  const handleEnablePush = async () => {
    if (!isPushSupported()) {
      toast.error("Not Supported", "Web Push is not supported in this browser.");
      return;
    }

    setIsSubscribing(true);
    try {
      const perm = await requestNotificationPermission();
      setPermissionState(perm);

      if (perm === "granted") {
        const vapidKey = await ApiNotificationRepository.getVapidPublicKey();
        const subData = await subscribeToWebPush(vapidKey);
        if (subData) {
          await ApiNotificationRepository.subscribePush(subData);
          toast.success("Push Enabled", "Web Push notifications successfully configured.");
        } else {
          toast.info("Permission Granted", "Push permissions enabled for browser.");
        }
      } else if (perm === "denied") {
        toast.error(
          "Permission Denied",
          "Notifications were blocked. Please enable them in your browser site settings."
        );
      }
    } catch (err) {
      console.error("Push subscription error:", err);
      toast.error("Push Setup Failed", "Failed to complete Web Push subscription.");
    } finally {
      setIsSubscribing(false);
    }
  };

  const handleSendTest = async () => {
    setIsSendingTest(true);
    try {
      playAlarmChime();
      await ApiNotificationRepository.sendTestNotification({
        title: "ADA Smart Alarm Test",
        body: "Test notification delivered successfully. In-app and browser channels operational.",
      });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["unread-notifications-count"] });
      toast.success("Test Dispatched", "Test alert delivered to your notification center.");
    } catch {
      toast.error("Test Failed", "Unable to send test notification.");
    } finally {
      setIsSendingTest(false);
    }
  };

  if (isLoading || !prefs) {
    return (
      <Card className="p-4 border-white/10 text-xs text-slate-400">
        Loading notification settings...
      </Card>
    );
  }

  return (
    <Card className="p-5 space-y-5 border-white/10 bg-slate-900/40">
      <div className="flex items-center justify-between pb-3 border-b border-white/5">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <Bell size={14} className="text-brand-400" />
            Notification & Alarm Delivery
          </h3>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Configure how ADA delivers wake events, departure reminders, and live traffic updates.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={handleSendTest}
          disabled={isSendingTest}
          className="text-xs gap-1.5 h-8 border-slate-700 hover:border-brand-500/50"
        >
          <Send size={12} className={isSendingTest ? "animate-pulse" : ""} />
          Send Test
        </Button>
      </div>

      {/* Push Permission Status Banner */}
      <div className="p-3.5 rounded-xl bg-slate-800/50 border border-white/5 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {permissionState === "granted" ? (
              <ShieldCheck size={16} className="text-emerald-400" />
            ) : permissionState === "denied" ? (
              <AlertOctagon size={16} className="text-rose-400" />
            ) : (
              <Bell size={16} className="text-amber-400" />
            )}
            <span className="text-xs font-semibold text-slate-200">
              Browser Web Push:{" "}
              {permissionState === "granted" ? (
                <span className="text-emerald-400">Active</span>
              ) : permissionState === "denied" ? (
                <span className="text-rose-400">Blocked</span>
              ) : (
                <span className="text-amber-400">Not Enabled</span>
              )}
            </span>
          </div>

          {permissionState !== "granted" && permissionState !== "denied" && (
            <Button
              size="sm"
              onClick={handleEnablePush}
              disabled={isSubscribing}
              className="text-xs h-7 px-3 bg-brand-600 hover:bg-brand-500 text-white"
            >
              {isSubscribing ? "Enabling..." : "Enable Push"}
            </Button>
          )}
        </div>

        {permissionState === "denied" && (
          <p className="text-[11px] text-rose-300/80 leading-relaxed">
            Notifications are blocked in your browser settings. To receive wake alarms, please click
            the lock/settings icon in your browser address bar and set Notifications to Allow.
          </p>
        )}
      </div>

      {/* Main Delivery Toggles */}
      <div className="space-y-4">
        {/* Wake Alarm */}
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-0.5">
            <label className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
              <Clock size={13} className="text-violet-400" />
              Wake Alarms
            </label>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Trigger alarm experience at the calculated wake time based on preparation and traffic.
            </p>
          </div>
          <Switch
            checked={prefs.wakeAlarmEnabled}
            onCheckedChange={(val) => handleToggle("wakeAlarmEnabled", val)}
          />
        </div>

        {/* Departure Reminder */}
        <div className="pt-3 border-t border-white/5 space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-0.5">
              <label className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <Navigation size={13} className="text-amber-400" />
                Departure Approaching Reminders
              </label>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Receive an alert before you need to leave the house.
              </p>
            </div>
            <Switch
              checked={prefs.departureReminderEnabled}
              onCheckedChange={(val) => handleToggle("departureReminderEnabled", val)}
            />
          </div>

          {prefs.departureReminderEnabled && (
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-white/5 text-xs">
              <span className="text-slate-400 text-[11px]">Reminder Lead Time:</span>
              <div className="flex items-center gap-1.5">
                {[5, 10, 15, 20].map((mins) => (
                  <button
                    key={mins}
                    onClick={() =>
                      updateMutation.mutate({ departureReminderLeadMinutes: mins })
                    }
                    className={`px-2 py-0.5 rounded text-[11px] font-mono transition-colors ${
                      prefs.departureReminderLeadMinutes === mins
                        ? "bg-brand-500/20 text-brand-300 border border-brand-500/40 font-bold"
                        : "text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800"
                    }`}
                  >
                    {mins}m
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Traffic Schedule Changes */}
        <div className="pt-3 border-t border-white/5 flex items-start justify-between gap-4">
          <div className="space-y-0.5">
            <label className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
              <AlertTriangle size={13} className="text-sky-400" />
              Traffic & Schedule Change Alerts
            </label>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Notify immediately when road congestion causes ADA to adjust your wake schedule.
            </p>
          </div>
          <Switch
            checked={prefs.scheduleChangeEnabled}
            onCheckedChange={(val) => handleToggle("scheduleChangeEnabled", val)}
          />
        </div>

        {/* Audio Alerts & Synth Chime */}
        <div className="pt-3 border-t border-white/5 flex items-start justify-between gap-4">
          <div className="space-y-0.5">
            <label className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
              <Volume2 size={13} className="text-violet-400" />
              Web Audio Wake Chimes
            </label>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Synthesize harmonic wake chords when alerts are delivered.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => playAlarmChime()}
              className="text-[11px] text-slate-400 hover:text-violet-300 px-2 py-1 rounded bg-slate-800 border border-slate-700 transition-colors"
            >
              Test
            </button>
            <Switch
              checked={prefs.soundEnabled}
              onCheckedChange={(val) => handleToggle("soundEnabled", val)}
            />
          </div>
        </div>
      </div>

      {/* Platform Limitations Notice (Section 10 & 22) */}
      <div className="p-3 rounded-xl bg-slate-950/60 border border-white/5 flex items-start gap-2 text-[11px] text-slate-400 leading-relaxed">
        <Info size={14} className="text-slate-500 mt-0.5 shrink-0" />
        <p>
          <strong className="text-slate-300">Device Note:</strong> Browser-based delivery relies
          on the Web Push API. If your device is shut down, in system Do Not Disturb mode, or
          browser suspended, audio playback may be restricted until the browser is reopened.
        </p>
      </div>
    </Card>
  );
}
