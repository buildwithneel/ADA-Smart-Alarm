/**
 * Time and Schedule calculations for ADA.
 */

/**
 * Format minutes into human-readable duration (e.g., "45m" or "1h 15m")
 */
export function formatMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;
  return remaining > 0 ? `${hours}h ${remaining}m` : `${hours}h`;
}

/**
 * Converts 24h format "09:00" to 12h format "9:00 AM"
 */
export function formatTo12Hour(timeStr: string): string {
  if (!timeStr) return "--:--";
  const [hStr, mStr] = timeStr.split(":");
  let hours = parseInt(hStr, 10);
  const minutes = mStr ? mStr.slice(0, 2) : "00";
  const period = hours >= 12 ? "PM" : "AM";
  hours = hours % 12 || 12;
  return `${hours}:${minutes} ${period}`;
}

/**
 * Calculate countdown remaining time until the alarm fires in hours/minutes
 */
export function getTimeUntil(targetTimeStr: string): string {
  if (!targetTimeStr) return "";
  const now = new Date();
  const [hStr, mStr] = targetTimeStr.split(":");
  const target = new Date();
  target.setHours(parseInt(hStr, 10), parseInt(mStr, 10), 0, 0);

  if (target.getTime() <= now.getTime()) {
    target.setDate(target.getDate() + 1);
  }

  const diffMs = target.getTime() - now.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  return formatMinutes(diffMins);
}
