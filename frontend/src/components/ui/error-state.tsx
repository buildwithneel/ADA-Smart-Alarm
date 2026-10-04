import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "./button";

export interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="p-6 rounded-2xl border border-rose-500/20 bg-rose-500/5 text-center flex flex-col items-center justify-center space-y-3">
      <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
        <AlertTriangle size={20} />
      </div>
      <div>
        <h4 className="text-sm font-bold text-slate-100">{title}</h4>
        <p className="text-xs text-slate-400 max-w-sm mt-1">{message}</p>
      </div>
      {onRetry && (
        <Button size="sm" variant="outline" onClick={onRetry} className="gap-1.5 mt-2 border-rose-500/30 text-rose-300">
          <RefreshCw size={13} />
          Try Again
        </Button>
      )}
    </div>
  );
}
