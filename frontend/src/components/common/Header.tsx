import { Bell, Moon, Sun } from "lucide-react";
import { useTheme } from "@/core/theme/ThemeProvider";
import { useAuthStore } from "@/stores/useAuthStore";

export function Header() {
  const { theme, toggleTheme } = useTheme();
  const user = useAuthStore((state) => state.user);

  return (
    <header className="sticky top-0 z-40 w-full border-b border-white/10 glass-panel bg-opacity-70">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between max-w-5xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl gradient-brand flex items-center justify-center text-white font-extrabold shadow-lg shadow-brand-500/25">
            A
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-brand-400 via-indigo-300 to-violet-400 bg-clip-text text-transparent">
                ADA
              </span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-brand-500/20 text-brand-400 border border-brand-500/30">
                PROD
              </span>
            </div>
            <span className="text-[11px] block text-slate-400 font-medium">
              Adaptive Dynamic Alarm
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={toggleTheme}
            className="p-2.5 rounded-xl border border-white/10 hover:bg-white/5 text-slate-400 hover:text-slate-100 transition-colors"
            aria-label="Toggle Theme"
          >
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          <button
            className="p-2.5 rounded-xl border border-white/10 hover:bg-white/5 text-slate-400 hover:text-slate-100 transition-colors relative"
            aria-label="Notifications"
          >
            <Bell size={18} />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500 ring-2 ring-slate-950" />
          </button>

          <div className="h-6 w-px bg-white/10 mx-1 hidden sm:block" />

          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-brand-600 border border-brand-400/40 flex items-center justify-center text-xs font-bold text-white shadow-md">
              {user?.display_name?.slice(0, 2).toUpperCase() || "AD"}
            </div>
            <span className="text-xs font-semibold text-slate-200 hidden sm:inline">
              {user?.display_name || "User"}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
