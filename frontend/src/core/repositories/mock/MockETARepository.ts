import { AlarmCalculationPreview } from "@/core/types/alarm";
import { ETARequest, IETARepository } from "../interfaces/ETARepository";
import { mapDomainService } from "@/core/maps";

/**
 * MockETARepository consuming the normalized MapDomainService.
 * Seamlessly consumes RouteResult without knowing if Google or Mapbox generated it.
 */
export class MockETARepository implements IETARepository {
  async calculateETA(request: ETARequest): Promise<AlarmCalculationPreview> {
    const route = await mapDomainService.calculateCommuteRoute({
      origin: { latitude: request.originLat, longitude: request.originLng },
      destination: { latitude: request.destinationLat, longitude: request.destinationLng },
      transportMode: request.transportMode,
    });

    const totalTravelMinutes = Math.round(route.trafficDurationSeconds / 60);
    const trafficDelayMinutes = Math.max(0, Math.round((route.trafficDurationSeconds - route.durationSeconds) / 60));

    const [h, m] = request.desiredArrival.split(":");
    const arrivalDate = new Date();
    arrivalDate.setHours(parseInt(h, 10), parseInt(m, 10), 0, 0);

    const leaveDate = new Date(arrivalDate.getTime() - (totalTravelMinutes + request.bufferMinutes) * 60000);
    const wakeDate = new Date(leaveDate.getTime() - request.routineMinutes * 60000);

    const formatTime = (d: Date) => {
      let hours = d.getHours();
      const minutes = d.getMinutes();
      const period = hours >= 12 ? "PM" : "AM";
      hours = hours % 12 || 12;
      return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")} ${period}`;
    };

    return {
      travel_minutes: totalTravelMinutes,
      traffic_delay_minutes: trafficDelayMinutes,
      recommended_leave_time: formatTime(leaveDate),
      recommended_wake_time: formatTime(wakeDate),
      weather_summary: `Route via ${route.provider.toUpperCase()} (${route.summary.formattedDistance})`,
      confidence_score: 0.95,
    };
  }
}
