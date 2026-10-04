/**
 * LocationService.
 * Single source of truth for browser geolocation acquisition, permission tracking,
 * coordinate validation, and location normalization.
 *
 * Privacy by Design:
 * - Does not stream location continuously in background
 * - Normalizes coordinates and strips non-essential telemetry
 * - Tracks permanent permission denial to avoid repeatedly prompting the user
 * - No location history is recorded on the device or server
 */

export interface NormalizedLocation {
  latitude: number;
  longitude: number;
  accuracyMeters: number;
  altitude: number | null;
  heading: number | null;
  speed: number | null;
  timestamp: number;
}

export type LocationPermissionState =
  | "granted"
  | "denied"
  | "denied_permanently"
  | "prompt"
  | "unavailable"
  | "timeout"
  | "gps_disabled";

export interface LocationErrorDetails {
  state: LocationPermissionState;
  message: string;
  code?: number;
}

const PERMISSION_DENIED_KEY = "ada_location_permanently_denied";

export class LocationService {
  private static instance: LocationService | null = null;
  private activeWatchId: number | null = null;

  public static getInstance(): LocationService {
    if (!this.instance) {
      this.instance = new LocationService();
    }
    return this.instance;
  }

  /**
   * Validates if geographical coordinates lie within legitimate spherical boundaries.
   */
  public isValidCoordinates(lat: number, lng: number): boolean {
    return (
      typeof lat === "number" &&
      typeof lng === "number" &&
      !isNaN(lat) &&
      !isNaN(lng) &&
      lat >= -90.0 &&
      lat <= 90.0 &&
      lng >= -180.0 &&
      lng <= 180.0
    );
  }

  /**
   * Normalizes a raw GeolocationPosition object into ADA's strict domain model.
   * Explicitly sets optional telemetry to null when absent.
   */
  public normalizePosition(pos: GeolocationPosition): NormalizedLocation {
    const { coords, timestamp } = pos;
    return {
      latitude: coords.latitude,
      longitude: coords.longitude,
      accuracyMeters: coords.accuracy || 10,
      altitude: typeof coords.altitude === "number" && !isNaN(coords.altitude) ? coords.altitude : null,
      heading: typeof coords.heading === "number" && !isNaN(coords.heading) ? coords.heading : null,
      speed: typeof coords.speed === "number" && !isNaN(coords.speed) ? coords.speed : null,
      timestamp: timestamp || Date.now(),
    };
  }

  /**
   * Inspects browser permission query API if available.
   */
  public async getPermissionStatus(): Promise<LocationPermissionState> {
    if (typeof window !== "undefined" && window.localStorage?.getItem(PERMISSION_DENIED_KEY) === "true") {
      return "denied_permanently";
    }

    if (typeof window === "undefined" || !("geolocation" in navigator)) {
      return "unavailable";
    }


    if ("permissions" in navigator && navigator.permissions?.query) {
      try {
        const status = await navigator.permissions.query({ name: "geolocation" });
        if (status.state === "granted") return "granted";
        if (status.state === "denied") return "denied_permanently";
        return "prompt";
      } catch {
        // Fallback for browsers that don't support geolocation permission query
        return "prompt";
      }
    }

    return "prompt";
  }

  /**
   * Obtains instantaneous position. Returns normalized location.
   */
  public async getCurrentPosition(options?: PositionOptions): Promise<NormalizedLocation> {
    if (typeof window === "undefined" || !("geolocation" in navigator)) {
      throw {
        state: "unavailable",
        message: "Geolocation is not supported by your browser or device.",
      } as LocationErrorDetails;
    }

    const defaultOptions: PositionOptions = {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 30000, // Reuse cached position up to 30s to conserve battery
      ...options,
    };

    return new Promise<NormalizedLocation>((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          localStorage.removeItem(PERMISSION_DENIED_KEY);
          resolve(this.normalizePosition(pos));
        },
        (err) => {
          const mapped = this.mapGeolocationError(err);
          if (mapped.state === "denied_permanently" || mapped.state === "denied") {
            localStorage.setItem(PERMISSION_DENIED_KEY, "true");
          }
          reject(mapped);
        },
        defaultOptions
      );
    });
  }

  /**
   * Initiates continuous watch only when actively required by an open map.
   */
  public watchPosition(
    onLocation: (loc: NormalizedLocation) => void,
    onError?: (err: LocationErrorDetails) => void,
    options?: PositionOptions
  ): number {
    this.stopWatching();

    if (typeof window === "undefined" || !("geolocation" in navigator)) {
      onError?.({
        state: "unavailable",
        message: "Geolocation is not supported on this device.",
      });
      return -1;
    }

    this.activeWatchId = navigator.geolocation.watchPosition(
      (pos) => onLocation(this.normalizePosition(pos)),
      (err) => onError?.(this.mapGeolocationError(err)),
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 5000,
        ...options,
      }
    );

    return this.activeWatchId;
  }

  /**
   * Halts active position watcher immediately to conserve battery and protect privacy.
   */
  public stopWatching(watchId?: number): void {
    const id = watchId ?? this.activeWatchId;
    if (id !== null && typeof window !== "undefined" && "geolocation" in navigator) {
      navigator.geolocation.clearWatch(id);
      if (this.activeWatchId === id) {
        this.activeWatchId = null;
      }
    }
  }

  /**
   * Resets permanent denial flag when the user explicitly requests to retry permission.
   */
  public resetPermissionStatus(): void {
    if (typeof window !== "undefined") {
      localStorage.removeItem(PERMISSION_DENIED_KEY);
    }
  }

  private mapGeolocationError(err: GeolocationPositionError): LocationErrorDetails {
    switch (err.code) {
      case err.PERMISSION_DENIED:
        return {
          state: "denied_permanently",
          message:
            "Location permission is disabled. Enable it in your browser or device site settings to calculate real commute times.",
          code: err.code,
        };
      case err.POSITION_UNAVAILABLE:
        return {
          state: "unavailable",
          message: "Unable to determine your current location. Ensure GPS is enabled.",
          code: err.code,
        };
      case err.TIMEOUT:
        return {
          state: "timeout",
          message: "Location request timed out. Please try again.",
          code: err.code,
        };
      default:
        return {
          state: "gps_disabled",
          message: "Failed to acquire location. Check device GPS settings.",
          code: err.code,
        };
    }
  }
}

export const locationService = LocationService.getInstance();
