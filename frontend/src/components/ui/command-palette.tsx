import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Plus, Compass, MapPin, Activity, Settings, Moon, Sun, ArrowRight, X } from "lucide-react";
import { commandPaletteVariants, searchResultStagger } from "@/core/animations/variants";
import { useTheme } from "@/core/theme/ThemeProvider";

export interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        if (isOpen) onClose();
        else setQuery("");
      }
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const actions = [
    { id: "create", label: "Create Adaptive Alarm", icon: Plus, category: "Actions", action: () => navigate("/alarms/new") },
    { id: "dashboard", label: "Go to Dashboard", icon: Compass, category: "Navigation", action: () => navigate("/") },
    { id: "alarms", label: "View All Alarms", icon: Compass, category: "Navigation", action: () => navigate("/alarms") },
    { id: "destinations", label: "Manage Destinations", icon: MapPin, category: "Navigation", action: () => navigate("/destinations") },
    { id: "activity", label: "View Recent Activity", icon: Activity, category: "Navigation", action: () => navigate("/activity") },
    { id: "settings", label: "Settings", icon: Settings, category: "Navigation", action: () => navigate("/settings") },
    { id: "theme", label: `Toggle Theme (Current: ${theme})`, icon: theme === "dark" ? Sun : Moon, category: "Preferences", action: toggleTheme },
  ];

  const filtered = actions.filter((a) =>
    a.label.toLowerCase().includes(query.toLowerCase()) ||
    a.category.toLowerCase().includes(query.toLowerCase())
  );

  const handleSelect = (act: typeof actions[0]) => {
    act.action();
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm"
          />

          <motion.div
            variants={commandPaletteVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            className="relative z-10 w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden text-left"
          >
            {/* Search Input Bar */}
            <div className="flex items-center gap-3 px-4 py-3.5 border-b border-slate-800">
              <Search size={18} className="text-slate-400 shrink-0" />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Type a command or search alarms, destinations..."
                className="w-full bg-transparent text-sm text-slate-100 placeholder:text-slate-500 outline-none"
              />
              <button
                onClick={onClose}
                className="p-1 rounded text-slate-400 hover:text-slate-200"
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>

            {/* Results List */}
            <motion.div
              variants={searchResultStagger}
              initial="initial"
              animate="animate"
              className="max-h-72 overflow-y-auto p-2 space-y-1"
            >
              {filtered.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-400">
                  No commands found matching "{query}"
                </div>
              ) : (
                filtered.map((item) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleSelect(item)}
                      className="w-full flex items-center justify-between p-2.5 rounded-xl hover:bg-slate-800/80 transition-colors text-left group"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-slate-800 text-slate-400 group-hover:text-brand-400 group-hover:bg-brand-500/10 transition-colors">
                          <Icon size={16} />
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-slate-200 group-hover:text-white">
                            {item.label}
                          </p>
                          <p className="text-[10px] text-slate-400">{item.category}</p>
                        </div>
                      </div>
                      <ArrowRight size={14} className="text-slate-600 group-hover:text-slate-300 transition-colors" />
                    </button>
                  );
                })
              )}
            </motion.div>

            {/* Footer shortcuts */}
            <div className="px-4 py-2 border-t border-slate-800/80 bg-slate-950/40 flex items-center justify-between text-[11px] text-slate-400">
              <span className="flex items-center gap-1.5">
                <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-[10px] font-mono">↑↓</kbd>
                to navigate
              </span>
              <span className="flex items-center gap-1.5">
                <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-[10px] font-mono">↵</kbd>
                to select
              </span>
              <span className="flex items-center gap-1.5">
                <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-[10px] font-mono">esc</kbd>
                to close
              </span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
