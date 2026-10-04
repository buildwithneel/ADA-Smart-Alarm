import { Moon, Sun, Bell, Search, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { useTheme } from "@/core/theme/ThemeProvider";
import { useAuth } from "@/core/auth/AuthContext";

export interface TopNavbarProps {
  onOpenCommandPalette: () => void;
  onOpenNotifications: () => void;
  unreadCount?: number;
}

export function TopNavbar({
  onOpenCommandPalette,
  onOpenNotifications,
  unreadCount = 0,
}: TopNavbarProps) {
  const { theme, toggleTheme } = useTheme();
  const { currentUser } = useAuth();

  // Dynamic Time Greeting
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  const displayName = currentUser?.name || currentUser?.email?.split("@")[0] || "User";
  const initials = (currentUser?.name
    ? currentUser.name.split(" ").map((n) => n[0]).join("")
    : currentUser?.email?.slice(0, 2) || "AD"
  ).toUpperCase();

  return (
    <header className="sticky top-0 z-30 w-full border-b border-white/5 bg-slate-950/80 backdrop-blur-xl h-16">
      <div className="h-full px-4 sm:px-6 flex items-center justify-between">
        {/* Left: Greeting */}
        <div className="text-left">
          <p className="text-xs text-slate-400 font-medium">{getGreeting()},</p>
          <h2 className="text-sm font-bold text-slate-100">
            {displayName}
          </h2>
        </div>

        {/* Right Action Icons */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* AI Assistant Quick Link */}
          <Link
            to="/assistant"
            className="p-2 sm:px-3 sm:py-1.5 rounded-xl border border-brand-500/30 hover:border-brand-500/50 bg-brand-500/10 hover:bg-brand-500/15 text-brand-300 hover:text-brand-200 transition-colors flex items-center gap-1.5 text-xs font-semibold"
            title="ADA AI Assistant"
          >
            <Sparkles size={14} className="text-brand-400" />
            <span className="hidden sm:inline">AI Assistant</span>
          </Link>

          {/* Quick Search */}
          <button
            onClick={onOpenCommandPalette}
            className="p-2 sm:px-3 sm:py-1.5 rounded-xl border border-white/5 hover:border-white/15 bg-slate-900/50 text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-2 text-xs"
            aria-label="Search or command palette"
          >
            <Search size={15} />
            <span className="hidden sm:inline">Search</span>
            <kbd className="hidden sm:inline px-1 rounded bg-slate-800 border border-slate-700 text-[10px] font-mono">
              ⌘K
            </kbd>
          </button>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-xl border border-white/5 hover:border-white/15 bg-slate-900/50 text-slate-400 hover:text-slate-100 transition-colors"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          {/* Notifications Drawer Toggle */}
          <button
            onClick={onOpenNotifications}
            className="p-2 rounded-xl border border-white/5 hover:border-white/15 bg-slate-900/50 text-slate-400 hover:text-slate-100 transition-colors relative"
            aria-label="Open notifications"
          >
            <Bell size={16} />
            {unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500 ring-2 ring-slate-950" />
            )}
          </button>

          {/* User Avatar */}
          {currentUser?.profileImage ? (
            <img
              src={currentUser.profileImage}
              alt={displayName}
              className="w-8 h-8 rounded-full border border-brand-400/40 object-cover shadow-sm select-none"
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-brand-600 border border-brand-400/40 flex items-center justify-center text-xs font-bold text-white shadow-sm select-none">
              {initials}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
