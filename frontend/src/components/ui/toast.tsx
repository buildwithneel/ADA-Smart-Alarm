import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from "lucide-react";
import { useToastStore, ToastType } from "@/core/toast/useToast";
import { toastVariants } from "@/core/animations/variants";

const icons: Record<ToastType, typeof CheckCircle2> = {
  success: CheckCircle2,
  warning: AlertTriangle,
  error: AlertCircle,
  info: Info,
};

const borderStyles: Record<ToastType, string> = {
  success: "border-emerald-500/30 bg-slate-900/90 text-emerald-400",
  warning: "border-amber-500/30 bg-slate-900/90 text-amber-400",
  error: "border-rose-500/30 bg-slate-900/90 text-rose-400",
  info: "border-indigo-500/30 bg-slate-900/90 text-indigo-400",
};

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  return (
    <aside aria-label="Notifications" className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none px-4">
      <AnimatePresence>
        {toasts.map((t) => {
          const Icon = icons[t.type];
          return (
            <motion.div
              key={t.id}
              variants={toastVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              className={`pointer-events-auto p-3.5 rounded-xl border backdrop-blur-xl shadow-xl flex items-start gap-3 text-left ${borderStyles[t.type]}`}
            >
              <Icon size={18} className="shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-bold text-slate-100">{t.title}</p>
                {t.message && <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">{t.message}</p>}
              </div>
              <button
                onClick={() => removeToast(t.id)}
                className="text-slate-400 hover:text-slate-200 transition-colors p-1"
                aria-label="Dismiss toast"
              >
                <X size={14} />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </aside>
  );
}
