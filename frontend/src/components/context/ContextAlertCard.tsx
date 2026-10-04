import React from 'react';
import {
  CloudRain,
  AlertTriangle,
  Calendar,
  Clock,
  ExternalLink,
  ShieldCheck,
} from 'lucide-react';
import { ContextResult } from '@/core/types/context';

interface ContextAlertCardProps {
  result: ContextResult;
  onApplyBuffer?: (bufferMinutes: number) => void;
  onDismiss?: () => void;
  isApplying?: boolean;
}

export const ContextAlertCard: React.FC<ContextAlertCardProps> = ({
  result,
  onApplyBuffer,
  onDismiss,
  isApplying = false,
}) => {
  const isWeather = result.context_type === 'weather';
  const isCalendar = result.context_type === 'calendar';
  const isSevere = result.finding === 'SEVERE_WEATHER_ALERT';
  const isRain = result.finding === 'RAIN_DURING_JOURNEY';
  const isCanApply = result.recommended_action === 'apply_buffer' && result.recommended_buffer_minutes > 0;

  const formatEvaluatedTime = (isoString: string) => {
    try {
      const dt = new Date(isoString);
      return dt.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    } catch {
      return 'recently';
    }
  };

  return (
    <div
      className={`rounded-2xl border p-4.5 transition-all duration-300 backdrop-blur-xl ${
        isSevere
          ? 'bg-rose-950/20 border-rose-500/40 text-rose-100 shadow-lg shadow-rose-950/30'
          : isRain
          ? 'bg-sky-950/25 border-sky-500/30 text-sky-100 shadow-lg shadow-sky-950/20'
          : isCalendar
          ? 'bg-amber-950/20 border-amber-500/30 text-amber-100'
          : 'bg-slate-900/60 border-white/10 text-slate-200'
      }`}
    >
      <div className="flex items-start gap-3.5">
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
            isSevere
              ? 'bg-rose-500/20 text-rose-400'
              : isRain
              ? 'bg-sky-500/20 text-sky-400'
              : isCalendar
              ? 'bg-amber-500/20 text-amber-400'
              : 'bg-white/10 text-slate-300'
          }`}
        >
          {isSevere ? (
            <AlertTriangle className="h-5 w-5 animate-pulse" />
          ) : isRain ? (
            <CloudRain className="h-5 w-5" />
          ) : isCalendar ? (
            <Calendar className="h-5 w-5" />
          ) : (
            <Clock className="h-5 w-5" />
          )}
        </div>

        <div className="flex-1 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold tracking-wider uppercase text-slate-400">
              {isWeather ? 'Weather Intelligence' : 'Calendar Intelligence'}
            </span>
            <span className="text-[11px] text-slate-400 flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Updated {formatEvaluatedTime(result.evaluated_at)}
            </span>
          </div>

          <p className="text-sm font-medium leading-relaxed text-slate-100">
            {result.explanation}
          </p>

          {/* Severe alerts official source link if provided */}
          {result.metadata?.alerts && result.metadata.alerts.length > 0 && (
            <div className="mt-2 space-y-1.5">
              {result.metadata.alerts.map((alert: any, idx: number) => (
                <div
                  key={idx}
                  className="rounded-lg bg-black/20 p-2 text-xs border border-white/5 space-y-0.5"
                >
                  <div className="font-semibold text-rose-300">{alert.title}</div>
                  <div className="text-slate-300 text-[11px]">{alert.description}</div>
                  {alert.url && (
                    <a
                      href={alert.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] text-rose-400 hover:underline pt-0.5"
                    >
                      Official advisory details <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Action buttons if policy allows adjustment */}
          {isCanApply && (
            <div className="mt-3 flex items-center gap-2.5 pt-1">
              <button
                type="button"
                onClick={() => onApplyBuffer?.(result.recommended_buffer_minutes)}
                disabled={isApplying}
                className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-md hover:from-sky-400 hover:to-blue-500 focus:outline-none focus:ring-2 focus:ring-sky-400/50 disabled:opacity-50 transition-all"
              >
                {isApplying ? (
                  <span className="animate-spin mr-1">⌛</span>
                ) : (
                  <ShieldCheck className="h-3.5 w-3.5" />
                )}
                Apply +{result.recommended_buffer_minutes}m Weather Buffer
              </button>

              {onDismiss && (
                <button
                  type="button"
                  onClick={onDismiss}
                  className="rounded-xl px-3 py-1.5 text-xs font-medium text-slate-400 hover:bg-white/5 hover:text-slate-200 transition-colors"
                >
                  Keep current schedule
                </button>
              )}
            </div>
          )}

          {/* Attribution footer */}
          {result.metadata?.attribution && (
            <div className="pt-1 text-[10px] text-slate-500">
              {result.metadata.attribution}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
