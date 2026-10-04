import React, { useEffect, useState } from 'react';
import { CloudRain, Calendar } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Stepper } from '@/components/ui/stepper';
import { contextRepository } from '@/core/repositories';
import { toast } from '@/core/toast/useToast';

export const ContextSettingsCard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [weatherBufferEnabled, setWeatherBufferEnabled] = useState(false);
  const [weatherBufferMode, setWeatherBufferMode] = useState('informational_only');
  const [weatherBufferMinutes, setWeatherBufferMinutes] = useState(10);
  const [weatherAlertsEnabled, setWeatherAlertsEnabled] = useState(true);
  const [calendarSyncEnabled, setCalendarSyncEnabled] = useState(true);
  const [calendarAutoReschedule, setCalendarAutoReschedule] = useState(false);

  useEffect(() => {
    contextRepository
      .getContextPreferences()
      .then((prefs) => {
        setWeatherBufferEnabled(prefs.weather_buffer_enabled);
        setWeatherBufferMode(prefs.weather_buffer_mode || 'informational_only');
        setWeatherBufferMinutes(prefs.weather_buffer_minutes || 10);
        setWeatherAlertsEnabled(prefs.weather_alerts_enabled);
        setCalendarSyncEnabled(prefs.calendar_sync_enabled);
        setCalendarAutoReschedule(prefs.calendar_auto_reschedule);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const savePreferences = async (patch: Record<string, any>) => {
    try {
      await contextRepository.updateContextPreferences(patch);
      toast.success('Context Policy Updated', 'Your contextual adjustments have been saved.');
    } catch {
      toast.error('Update Failed', 'Could not save context preferences.');
    }
  };

  if (loading) {
    return (
      <Card className="p-4 border-white/10 text-xs text-slate-400">
        Loading context intelligence settings...
      </Card>
    );
  }

  return (
    <Card className="p-4.5 space-y-5 border-white/10 text-left">
      <div className="flex items-center justify-between pb-3 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500/20 text-sky-400">
            <CloudRain size={16} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100">Weather & Journey Buffer Policy</h3>
            <p className="text-[11px] text-slate-400">
              Governs whether rain or travel conditions may affect arrival schedules.
            </p>
          </div>
        </div>
      </div>

      {/* Weather Buffer Toggle & Policy */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5 pr-4">
            <span className="text-xs font-semibold text-slate-200">
              Weather Buffer Adjustments
            </span>
            <p className="text-[11px] text-slate-400">
              Allow ADA to evaluate forecasts and suggest travel adjustments for rain.
            </p>
          </div>
          <Switch
            checked={weatherBufferEnabled}
            onCheckedChange={(val) => {
              setWeatherBufferEnabled(val);
              savePreferences({ weather_buffer_enabled: val });
            }}
          />
        </div>

        {weatherBufferEnabled && (
          <div className="space-y-3 pl-3 border-l-2 border-sky-500/30">
            {/* Policy Mode Selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300">Adjustment Policy Mode</label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {[
                  {
                    id: 'informational_only',
                    label: 'Informational Only',
                    desc: 'Warn in UI, no schedule changes',
                  },
                  {
                    id: 'user_confirmed',
                    label: 'User Confirmed',
                    desc: 'Recommend buffer; requires approval',
                  },
                  {
                    id: 'automatic',
                    label: 'Automatic',
                    desc: 'Apply buffer directly upon rain',
                  },
                ].map((mode) => {
                  const isSelected = weatherBufferMode === mode.id;
                  return (
                    <button
                      key={mode.id}
                      type="button"
                      onClick={() => {
                        setWeatherBufferMode(mode.id);
                        savePreferences({ weather_buffer_mode: mode.id });
                      }}
                      className={`p-2.5 rounded-xl border text-left transition-all ${
                        isSelected
                          ? 'border-sky-500 bg-sky-500/10 text-sky-200 font-semibold'
                          : 'border-white/5 bg-slate-900/40 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <div className="text-xs">{mode.label}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">{mode.desc}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Weather Buffer Duration */}
            <div className="pt-1">
              <Stepper
                label="Maximum Weather Buffer"
                value={weatherBufferMinutes}
                onChange={(val) => {
                  setWeatherBufferMinutes(val);
                  savePreferences({ weather_buffer_minutes: val });
                }}
                min={5}
                max={30}
              />
              <span className="text-[10px] text-slate-500 block mt-1">
                Cap additional weather buffer at 30 minutes to protect sleep schedules.
              </span>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between pt-2 border-t border-white/5">
          <div className="space-y-0.5 pr-4">
            <span className="text-xs font-semibold text-slate-200">Severe Weather Alerts</span>
            <p className="text-[11px] text-slate-400">
              Display official weather warnings and safety advisories.
            </p>
          </div>
          <Switch
            checked={weatherAlertsEnabled}
            onCheckedChange={(val) => {
              setWeatherAlertsEnabled(val);
              savePreferences({ weather_alerts_enabled: val });
            }}
          />
        </div>
      </div>

      {/* Calendar Automation Section */}
      <div className="pt-3 border-t border-white/5 space-y-3">
        <div className="flex items-center gap-2">
          <Calendar size={14} className="text-amber-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Calendar Automation Policy
          </span>
        </div>

        <div className="flex items-center justify-between">
          <div className="space-y-0.5 pr-4">
            <span className="text-xs font-semibold text-slate-200">
              Synchronize Connected Calendars
            </span>
            <p className="text-[11px] text-slate-400">
              Check for upcoming event times and locations every 15 minutes.
            </p>
          </div>
          <Switch
            checked={calendarSyncEnabled}
            onCheckedChange={(val) => {
              setCalendarSyncEnabled(val);
              savePreferences({ calendar_sync_enabled: val });
            }}
          />
        </div>

        <div className="flex items-center justify-between">
          <div className="space-y-0.5 pr-4">
            <span className="text-xs font-semibold text-slate-200">
              Automatic Rescheduling on Calendar Change
            </span>
            <p className="text-[11px] text-slate-400">
              When an event moves, recalculate wake and leave times automatically.
            </p>
          </div>
          <Switch
            checked={calendarAutoReschedule}
            onCheckedChange={(val) => {
              setCalendarAutoReschedule(val);
              savePreferences({ calendar_auto_reschedule: val });
            }}
          />
        </div>
      </div>
    </Card>
  );
};
