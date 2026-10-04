import { Moon, Sun, Monitor, LogOut, Info } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/core/theme/ThemeProvider";
import { useAuth } from "@/core/auth/AuthContext";
import { toast } from "@/core/toast/useToast";
import { NotificationSettingsCard } from "@/components/settings/NotificationSettingsCard";
import { ContextSettingsCard } from "@/components/settings/ContextSettingsCard";
import { CalendarEventsView } from "@/components/calendar/CalendarEventsView";
import { PersonalizationControls } from "@/components/settings/PersonalizationControls";

export function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { currentUser, signOut } = useAuth();

  const handleSignOut = async () => {
    try {
      await signOut();
      toast.info("Signed Out", "You have signed out of ADA.");
    } catch {
      toast.error("Sign Out Failed", "Unable to sign out. Please try again.");
    }
  };

  const displayName = currentUser?.name || currentUser?.email?.split("@")[0] || "User";
  const initials = (currentUser?.name
    ? currentUser.name.split(" ").map((n) => n[0]).join("")
    : currentUser?.email?.slice(0, 2) || "AD"
  ).toUpperCase();

  return (
    <div className="space-y-6 text-left max-w-2xl mx-auto">
      <div>
        <h1 className="text-2xl font-black text-slate-100 tracking-tight">Settings</h1>
        <p className="text-xs text-slate-400">Manage routines, devices, and profile preferences</p>
      </div>

      {/* Profile Card */}
      <Card className="flex items-center gap-4 p-4 border-white/10">
        {currentUser?.profileImage ? (
          <img
            src={currentUser.profileImage}
            alt={displayName}
            className="w-12 h-12 rounded-2xl border border-brand-400/40 object-cover shadow-md shadow-brand-500/20"
          />
        ) : (
          <div className="w-12 h-12 rounded-2xl bg-brand-600 flex items-center justify-center text-white font-bold text-lg shadow-md shadow-brand-500/20">
            {initials}
          </div>
        )}
        <div className="flex-1">
          <h3 className="font-bold text-sm text-slate-100">{displayName}</h3>
          <p className="text-xs text-slate-400">{currentUser?.email || "No email"}</p>
          <p className="text-[10px] text-slate-500 font-mono mt-0.5">UID: {currentUser?.firebaseUid}</p>
        </div>
      </Card>

      {/* Appearance Section */}
      <Card className="p-4 space-y-3 border-white/10">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Appearance</h3>
        <div className="grid grid-cols-3 gap-2">
          {(
            [
              { id: "dark", label: "Dark", icon: Moon },
              { id: "light", label: "Light", icon: Sun },
              { id: "system", label: "System", icon: Monitor },
            ] as const
          ).map((t) => {
            const Icon = t.icon;
            const isSelected = theme === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => {
                  setTheme(t.id);
                  toast.success("Theme Updated", `Switched to ${t.label} mode.`);
                }}
                className={`p-3 rounded-xl border flex flex-col items-center gap-1.5 transition-all ${
                  isSelected
                    ? "bg-brand-600/20 border-brand-500 text-brand-300 font-semibold shadow-sm"
                    : "border-slate-800 bg-slate-900/50 text-slate-400 hover:text-slate-200"
                }`}
              >
                <Icon size={18} />
                <span className="text-xs">{t.label}</span>
              </button>
            );
          })}
        </div>
      </Card>

      {/* Alarm Triggers & Notifications */}
      <NotificationSettingsCard />

      {/* Step 10: Weather & Journey Buffer Policy */}
      <ContextSettingsCard />

      {/* Step 10: Google Calendar Integration & Events */}
      <CalendarEventsView />

      {/* Step 11: Personalization Controls & Dynamic Schedule Defaults */}
      <PersonalizationControls />

      {/* About Section */}
      <Card className="p-4 space-y-2 border-white/10 text-xs text-slate-400">
        <div className="flex items-center gap-2 text-slate-200 font-bold">
          <Info size={14} className="text-brand-400" />
          <span>ADA (Adaptive Dynamic Alarm) v0.2.0</span>
        </div>
        <p>
          Architected for location-based dynamic alarms. Google Directions, Distance Matrix,
          and Firebase FCM push engine integration ready for production.
        </p>
      </Card>

      <Button
        variant="ghost"
        className="w-full text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 gap-2 font-bold"
        onClick={handleSignOut}
      >
        <LogOut size={16} />
        Sign Out of Account
      </Button>
    </div>
  );
}
