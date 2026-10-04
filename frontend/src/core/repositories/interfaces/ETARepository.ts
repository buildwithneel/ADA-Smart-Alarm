import { TransportMode, AlarmCalculationPreview } from "@/core/types/alarm";

export interface ETARequest {
  originLat: number;
  originLng: number;
  destinationLat: number;
  destinationLng: number;
  desiredArrival: string;
  routineMinutes: number;
  bufferMinutes: number;
  transportMode: TransportMode;
}

export interface IETARepository {
  calculateETA(request: ETARequest): Promise<AlarmCalculationPreview>;
}
