import React, { useEffect, useState } from 'react';
import {
  Calendar,
  RefreshCw,
  MapPin,
  Clock,
  AlertCircle,
  ExternalLink,
  PlusCircle,
  Unlink,
  Check,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';
import { calendarRepository } from '@/core/repositories';
import {
  CalendarConnection,
  CalendarEvent,
  ProposeAlarmResponse,
} from '@/core/types/calendar';

interface CalendarEventsViewProps {
  onAlarmCreated?: () => void;
}

export const CalendarEventsView: React.FC<CalendarEventsViewProps> = ({
  onAlarmCreated,
}) => {
  const [connections, setConnections] = useState<CalendarConnection[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Proposal modal state
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [proposal, setProposal] = useState<ProposeAlarmResponse | null>(null);
  const [isProposing, setIsProposing] = useState<boolean>(false);
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [prepTime, setPrepTime] = useState<number>(30);
  const [safetyBuffer, setSafetyBuffer] = useState<number>(15);
  const [travelMode, setTravelMode] = useState<string>('driving');

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const conns = await calendarRepository.listConnections();
      setConnections(conns);

      if (conns.some((c) => c.is_active)) {
        const evs = await calendarRepository.listEvents();
        setEvents(evs);
      } else {
        setEvents([]);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load calendar data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleConnect = async () => {
    try {
      const redirectUri = `${window.location.origin}/settings?tab=calendar`;
      const res = await calendarRepository.getAuthUrl(redirectUri);
      if (res?.authorization_url) {
        window.location.href = res.authorization_url;
      }
    } catch (err: any) {
      setError('Could not generate authorization URL.');
    }
  };

  const handleDisconnect = async (connId: string) => {
    if (!window.confirm('Are you sure you want to disconnect this calendar?')) return;
    try {
      await calendarRepository.disconnect(connId);
      await loadData();
    } catch (err: any) {
      setError('Failed to disconnect calendar.');
    }
  };

  const handleSync = async (connId: string) => {
    setIsSyncing(true);
    try {
      await calendarRepository.sync(connId);
      await loadData();
    } catch (err: any) {
      setError('Sync failed.');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleOpenProposal = async (event: CalendarEvent) => {
    setSelectedEvent(event);
    setIsProposing(true);
    try {
      const prop = await calendarRepository.proposeAlarm(event.id);
      setProposal(prop);
      setPrepTime(prop.preparation_time || 30);
      setSafetyBuffer(prop.safety_buffer || 15);
      setTravelMode(prop.transportation_mode || 'driving');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not evaluate event for alarm.');
      setSelectedEvent(null);
    } finally {
      setIsProposing(false);
    }
  };

  const handleConfirmAlarm = async () => {
    if (!selectedEvent) return;
    setIsCreating(true);
    try {
      await calendarRepository.createAlarmFromEvent(selectedEvent.id, {
        title: `Calendar: ${selectedEvent.title}`,
        preparation_time: prepTime,
        safety_buffer: safetyBuffer,
        transportation_mode: travelMode,
      });
      setSelectedEvent(null);
      setProposal(null);
      await loadData();
      onAlarmCreated?.();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create alarm from event.');
    } finally {
      setIsCreating(false);
    }
  };

  const activeConnection = connections.find((c) => c.is_active);

  const formatEventDate = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
    } catch {
      return '';
    }
  };

  const formatEventTime = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <div className="space-y-6">
      {/* Connection Header Card */}
      <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-5 backdrop-blur-xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-500/20 text-blue-400">
              <Calendar className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Google Calendar Integration</h3>
              <p className="text-xs text-slate-400">
                {activeConnection
                  ? `Connected as ${activeConnection.account_email}`
                  : 'Connect your calendar to turn scheduled events into smart arrival alarms.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {activeConnection ? (
              <>
                <button
                  type="button"
                  onClick={() => handleSync(activeConnection.id)}
                  disabled={isSyncing}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-white/10 transition-colors disabled:opacity-50"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
                  Sync
                </button>
                <button
                  type="button"
                  onClick={() => handleDisconnect(activeConnection.id)}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-rose-500/20 bg-rose-500/10 px-3 py-1.5 text-xs font-medium text-rose-300 hover:bg-rose-500/20 transition-colors"
                >
                  <Unlink className="h-3.5 w-3.5" />
                  Disconnect
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={handleConnect}
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-lg hover:from-blue-500 hover:to-indigo-500 transition-all"
              >
                <PlusCircle className="h-4 w-4" />
                Connect Google Calendar
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="mt-3 flex items-center gap-2 rounded-xl bg-rose-950/40 border border-rose-500/30 p-3 text-xs text-rose-300">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Events List */}
      {activeConnection && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold tracking-wide text-slate-300 uppercase">
              Upcoming Events ({events.length})
            </h4>
            {activeConnection.last_synced_at && (
              <span className="text-xs text-slate-500">
                Last synced {new Date(activeConnection.last_synced_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
              </span>
            )}
          </div>

          {isLoading ? (
            <div className="rounded-2xl border border-white/5 bg-slate-900/40 p-8 text-center text-sm text-slate-400">
              Loading calendar events...
            </div>
          ) : events.length === 0 ? (
            <div className="rounded-2xl border border-white/5 bg-slate-900/40 p-8 text-center">
              <Calendar className="mx-auto h-8 w-8 text-slate-500 mb-2 opacity-50" />
              <p className="text-sm font-medium text-slate-300">No upcoming calendar events found</p>
              <p className="text-xs text-slate-500 mt-1">
                Events with specified locations will appear here for 1-click alarm creation.
              </p>
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {events.map((event) => {
                const isLinked = Boolean(event.alarm_id);
                return (
                  <div
                    key={event.id}
                    className="flex flex-col justify-between rounded-2xl border border-white/10 bg-slate-900/50 p-4 transition-all hover:border-blue-500/30 hover:bg-slate-900/70"
                  >
                    <div className="space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <h5 className="font-semibold text-slate-100 text-sm line-clamp-1">
                          {event.title}
                        </h5>
                        {isLinked ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 shrink-0">
                            <Check className="h-3 w-3" /> Alarm Active
                          </span>
                        ) : (
                          <span className="text-[11px] font-medium text-slate-400 shrink-0">
                            {formatEventDate(event.start_time)}
                          </span>
                        )}
                      </div>

                      <div className="space-y-1 text-xs text-slate-400">
                        <div className="flex items-center gap-1.5">
                          <Clock className="h-3.5 w-3.5 text-slate-500" />
                          <span>
                            {formatEventTime(event.start_time)} – {formatEventTime(event.end_time)}
                          </span>
                        </div>

                        {event.location ? (
                          <div className="flex items-center gap-1.5 text-slate-300">
                            <MapPin className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
                            <span className="line-clamp-1">{event.location}</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5 text-slate-500 italic">
                            <MapPin className="h-3.5 w-3.5 opacity-40 shrink-0" />
                            <span>No location specified</span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between">
                      {event.event_link && (
                        <a
                          href={event.event_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200"
                        >
                          Google Calendar <ExternalLink className="h-3 w-3" />
                        </a>
                      )}

                      {!isLinked ? (
                        <button
                          type="button"
                          onClick={() => handleOpenProposal(event)}
                          className="inline-flex items-center gap-1 rounded-xl bg-blue-600/20 border border-blue-500/30 px-3 py-1.5 text-xs font-semibold text-blue-300 hover:bg-blue-600/30 hover:text-white transition-all ml-auto"
                        >
                          <span>Create ADA Alarm</span>
                          <ChevronRight className="h-3.5 w-3.5" />
                        </button>
                      ) : (
                        <span className="text-[11px] text-slate-500 ml-auto">
                          Synchronized
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Proposal & Confirmation Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-3xl border border-white/15 bg-slate-900 p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[11px] font-semibold tracking-wider text-blue-400 uppercase">
                  Create Smart Alarm
                </span>
                <h3 className="text-lg font-bold text-white mt-0.5">{selectedEvent.title}</h3>
              </div>
              <button
                type="button"
                onClick={() => {
                  setSelectedEvent(null);
                  setProposal(null);
                }}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {isProposing ? (
              <div className="py-8 text-center text-sm text-slate-400">
                Evaluating destination and journey schedule...
              </div>
            ) : proposal ? (
              <div className="space-y-4">
                {/* Destination inspection */}
                <div className="rounded-2xl bg-white/5 border border-white/10 p-3.5 space-y-1.5">
                  <div className="text-xs text-slate-400 flex items-center gap-1.5">
                    <MapPin className="h-3.5 w-3.5 text-indigo-400" />
                    <span>Arrival Destination</span>
                  </div>
                  <div className="text-sm font-semibold text-slate-100">
                    {selectedEvent.location || 'Selected Event Location'}
                  </div>
                  {!proposal.has_usable_location && (
                    <div className="flex items-center gap-1.5 text-xs text-amber-400 pt-1">
                      <ShieldAlert className="h-3.5 w-3.5" />
                      <span>Location will be geocoded upon creation.</span>
                    </div>
                  )}
                </div>

                {/* Arrival Time */}
                <div className="rounded-2xl bg-white/5 border border-white/10 p-3.5 flex justify-between items-center">
                  <div>
                    <span className="text-xs text-slate-400">Required Arrival Time</span>
                    <div className="text-base font-bold text-white">
                      {formatEventTime(selectedEvent.start_time)}
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-slate-400">Date</span>
                    <div className="text-sm font-medium text-slate-200">
                      {formatEventDate(selectedEvent.start_time)}
                    </div>
                  </div>
                </div>

                {/* Buffers configuration */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">
                      Preparation (mins)
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={180}
                      value={prepTime}
                      onChange={(e) => setPrepTime(Number(e.target.value))}
                      className="w-full rounded-xl bg-slate-800 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">
                      Safety Buffer (mins)
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={60}
                      value={safetyBuffer}
                      onChange={(e) => setSafetyBuffer(Number(e.target.value))}
                      className="w-full rounded-xl bg-slate-800 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>

                {/* Transportation Mode */}
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Transport Mode</label>
                  <select
                    value={travelMode}
                    onChange={(e) => setTravelMode(e.target.value)}
                    className="w-full rounded-xl bg-slate-800 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="driving">Driving</option>
                    <option value="transit">Transit</option>
                    <option value="bicycling">Bicycling</option>
                    <option value="walking">Walking</option>
                  </select>
                </div>

                {/* Confirm Button */}
                <div className="pt-2 flex items-center justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedEvent(null);
                      setProposal(null);
                    }}
                    className="rounded-xl px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirmAlarm}
                    disabled={isCreating}
                    className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-2 text-xs font-semibold text-white shadow-lg hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 transition-all"
                  >
                    {isCreating ? 'Creating Alarm...' : 'Confirm & Create Alarm'}
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
};
