import { NavLink } from "react-router-dom";
import {
  Compass,
  Clock,
  MapPin,
  Activity,
  Settings,
  Plus,
  Search,
  LogOut,
  Sparkles,
} from "lucide-react";
import { cn } from "@/core/utils/cn";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/core/auth/AuthContext";
import { toast } from "@/core/toast/useToast";

export interface DesktopSidebarProps {
  onOpenCommandPalette: () => void;
}

export function DesktopSidebar({ onOpenCommandPalette }: DesktopSidebarProps) {
  const { currentUser, signOut } = useAuth();

  const handleSignOut = async () => {
    try {
      await signOut();
      toast.info("Signed Out", "You have signed out of ADA.");
    } catch {
      toast.error("Sign Out Failed", "Unable to sign out.");
    }
  };

  const displayName = currentUser?.name || currentUser?.email?.split("@")[0] || "User";
  const initials = (currentUser?.name
    ? currentUser.name.split(" ").map((n) => n[0]).join("")
    : currentUser?.email?.slice(0, 2) || "AD"
  ).toUpperCase();

  const navLinks = [
    { to: "/", label: "Dashboard", icon: Compass },
    { to: "/alarms", label: "My Alarms", icon: Clock },
    { to: "/assistant", label: "AI Assistant", icon: Sparkles },
    { to: "/destinations", label: "Destinations", icon: MapPin },
    { to: "/activity", label: "Activity Log", icon: Activity },
    { to: "/settings", label: "Settings", icon: Settings },
  ];

  return (
    <aside className="hidden lg:flex flex-col w-64 border-r border-slate-800 bg-slate-950/80 backdrop-blur-xl p-5 select-none h-screen sticky top-0 justify-between text-left">
      <div className="space-y-6">
        {/* Brand Logo */}
        <div className="flex items-center gap-3 px-2">
          <div className="w-9 h-9 rounded-xl gradient-brand flex items-center justify-center text-white font-extrabold shadow-md shadow-brand-500/20">
            A
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-base tracking-tight text-white">
                ADA
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-brand-500/20 text-brand-300 font-bold">
                ETA
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Adaptive Dynamic Alarm</p>
          </div>
        </div>

        {/* Quick Action Button */}
        <NavLink to="/alarms/new">
          <Button variant="primary" className="w-full gap-2 shadow-sm font-semibold text-xs">
            <Plus size={16} />
            New Adaptive Alarm
          </Button>
        </NavLink>

        {/* Command Palette Trigger */}
        <button
          onClick={onOpenCommandPalette}
          className="w-full flex items-center justify-between px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200 transition-colors text-xs"
        >
          <span className="flex items-center gap-2">
            <Search size={14} />
            Quick search...
          </span>
          <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-[10px] font-mono text-slate-400">
            ⌘K
          </kbd>
        </button>

        {/* Nav Links */}
        <nav className="space-y-1">
          {navLinks.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all",
                    isActive
                      ? "bg-brand-600/15 text-brand-300 border border-brand-500/30"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                  )
                }
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer System Status & User Profile */}
      <div className="pt-4 border-t border-slate-800/80 px-1 space-y-3">
        <div className="flex items-center justify-between text-[11px] text-slate-500 px-1">
          <span>Autonomous Sync</span>
          <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-sm" />
        </div>

        {/* Compact User Bar with Sign Out */}
        <div className="flex items-center justify-between gap-2 p-2 rounded-xl bg-slate-900/60 border border-white/5">
          <div className="flex items-center gap-2 min-w-0">
            {currentUser?.profileImage ? (
              <img
                src={currentUser.profileImage}
                alt={displayName}
                className="w-7 h-7 rounded-lg border border-brand-400/40 object-cover shrink-0"
              />
            ) : (
              <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center text-[10px] font-bold text-white shrink-0">
                {initials}
              </div>
            )}
            <div className="min-w-0 flex-1 text-left">
              <p className="text-xs font-semibold text-slate-200 truncate">{displayName}</p>
              <p className="text-[10px] text-slate-400 truncate">{currentUser?.email || "Signed in"}</p>
            </div>
          </div>
          <button
            onClick={handleSignOut}
            title="Sign out"
            aria-label="Sign out"
            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors shrink-0"
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  );
}
