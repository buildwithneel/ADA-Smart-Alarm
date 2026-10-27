/**
 * ADA Mobile Location & Journey Tracking Coordinator.
 * Platform-independent coordinator utilizing @ada/shared DynamicEtaEngine.
 */

import {
  decodePolyline,
  DynamicEtaEngine,
  DynamicEtaResult,
  haversineMeters,
  JourneyAlertEvent,
  JourneyLocationFix,
  JourneyState,
  RouteRequestDto,
  RouteResultDto,
} from "@ada/shared";

export interface TrackingSessionUpdate {
  journeyId: string;
  state: JourneyState;
  etaResult: DynamicEtaResult | null;
  remainingDistanceMeters: number;
  alertEvent?: JourneyAlertEvent;
  isDeviation: boolean;
  message?: string;
}

export interface JourneySessionConfig {
  journeyId: string;
  destinationLat: number;
  destinationLng: number;
  approachingThresholdMeters?: number;
  arrivalThresholdMeters?: number;
}

export class LocationManager {
  private config: JourneySessionConfig | null = null;
  private previousFix: JourneyLocationFix | null = null;
  private lastRequestEpochMs = 0;
  private cachedPolylinePoints: Array<[number, number]> = [];
  private consecutiveArrivalHits = 0;
  private hasAlertedApproaching = false;
  private hasConfirmedArrival = false;
  private isTrackingActive = false;

  constructor(
    private routeProvider: (req: RouteRequestDto) => Promise<RouteResultDto>,
    private nowProvider: () => number = () => Date.now()
  ) {}

  startTracking(config: JourneySessionConfig): void {
    this.config = config;
    this.previousFix = null;
    this.lastRequestEpochMs = 0;
    this.cachedPolylinePoints = [];
    this.consecutiveArrivalHits = 0;
    this.hasAlertedApproaching = false;
    this.hasConfirmedArrival = false;
    this.isTrackingActive = true;
  }

  stopTracking(): void {
    this.isTrackingActive = false;
    this.config = null;
  }

  isActive(): boolean {
    return this.isTrackingActive;
  }

  async processLocationFix(currentFix: JourneyLocationFix): Promise<TrackingSessionUpdate> {
    if (!this.config || !this.isTrackingActive) {
      return {
        journeyId: this.config?.journeyId ?? "",
        state: JourneyState.CANCELLED,
        etaResult: null,
        remainingDistanceMeters: 0,
        isDeviation: false,
      };
    }

    const now = this.nowProvider();
    const { journeyId, destinationLat, destinationLng } = this.config;
    const approachingThreshold = this.config.approachingThresholdMeters ?? 1000;
    const arrivalThreshold = this.config.arrivalThresholdMeters ?? 100;

    // 1. Validate fix accuracy and freshness
    if (!DynamicEtaEngine.isLocationFixValid(currentFix, 50, 60000, now)) {
      return {
        journeyId,
        state: JourneyState.TRACKING_DEGRADED,
        etaResult: null,
        remainingDistanceMeters: 0,
        isDeviation: false,
        alertEvent: JourneyAlertEvent.TRACKING_DEGRADED,
        message: "Discarded inaccurate or stale GPS fix",
      };
    }

    // 2. Protect against unrealistic GPS velocity jumps
    if (this.previousFix && DynamicEtaEngine.isGpsJump(this.previousFix, currentFix)) {
      return {
        journeyId,
        state: JourneyState.ACTIVE_TRACKING,
        etaResult: null,
        remainingDistanceMeters: 0,
        isDeviation: false,
        message: "Discarded unrealistic GPS velocity jump",
      };
    }
    this.previousFix = currentFix;

    // 3. Route deviation check
    const isDeviated =
      this.cachedPolylinePoints.length > 0
        ? DynamicEtaEngine.isRouteDeviation(currentFix, this.cachedPolylinePoints)
        : false;

    // 4. Determine if we should query routing provider
    const shouldRecalculate = DynamicEtaEngine.shouldRecalculateRoute(
      isDeviated,
      this.lastRequestEpochMs,
      this.previousFix,
      currentFix,
      now
    );

    let etaResult: DynamicEtaResult;

    if (shouldRecalculate || this.cachedPolylinePoints.length === 0) {
      this.lastRequestEpochMs = now;
      try {
        const route = await this.routeProvider({
          origin: { latitude: currentFix.latitude, longitude: currentFix.longitude },
          destination: { latitude: destinationLat, longitude: destinationLng },
          travel_mode: "driving",
        });

        etaResult = DynamicEtaEngine.calculateEtaFromProvider(currentFix, route, now);
        if (route.route_geometry) {
          this.cachedPolylinePoints = decodePolyline(route.route_geometry);
        }
      } catch (err) {
        // Fallback to Great-Circle heuristic if provider fails
        etaResult = DynamicEtaEngine.calculateFallbackEta(
          currentFix,
          destinationLat,
          destinationLng,
          11.11,
          now
        );
      }
    } else {
      // Re-compute remaining distance to destination with existing ETA
      const remainingDist = Math.round(
        haversineMeters(currentFix.latitude, currentFix.longitude, destinationLat, destinationLng)
      );
      etaResult = DynamicEtaEngine.calculateFallbackEta(
        currentFix,
        destinationLat,
        destinationLng,
        11.11,
        now
      );
      etaResult.remainingDistanceMeters = remainingDist;
    }

    const remainingDistance = etaResult.remainingDistanceMeters;

    // 5. Evaluate Arrival Confirmation
    if (remainingDistance <= arrivalThreshold && currentFix.accuracyMeters <= 50) {
      this.consecutiveArrivalHits++;
    } else {
      this.consecutiveArrivalHits = 0;
    }

    const isArrived = DynamicEtaEngine.checkArrivalConfirmation(
      remainingDistance,
      currentFix.accuracyMeters,
      arrivalThreshold,
      this.consecutiveArrivalHits,
      2
    );

    let alertEvent: JourneyAlertEvent | undefined;
    let nextState = JourneyState.ACTIVE_TRACKING;

    if (isArrived && !this.hasConfirmedArrival) {
      this.hasConfirmedArrival = true;
      nextState = JourneyState.ARRIVED;
      alertEvent = JourneyAlertEvent.ARRIVAL_CONFIRMED;
      this.stopTracking(); // Stop tracking upon arrival confirmation
    } else if (
      DynamicEtaEngine.checkApproachingAlert(
        remainingDistance,
        approachingThreshold,
        this.hasAlertedApproaching
      )
    ) {
      this.hasAlertedApproaching = true;
      nextState = JourneyState.APPROACHING;
      alertEvent = JourneyAlertEvent.APPROACHING_ALERT;
    } else if (this.hasAlertedApproaching && remainingDistance <= approachingThreshold) {
      nextState = JourneyState.APPROACHING;
    } else if (isDeviated) {
      nextState = JourneyState.RECALCULATING;
      alertEvent = JourneyAlertEvent.ROUTE_DEVIATED;
    }

    return {
      journeyId,
      state: nextState,
      etaResult,
      remainingDistanceMeters: remainingDistance,
      alertEvent,
      isDeviation: isDeviated,
    };
  }
}
