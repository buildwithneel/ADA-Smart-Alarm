import { mapConfig, MapPlatformConfig } from "../config/mapConfig";
import { IMapProvider } from "../interfaces/IMapProvider";
import { IRoutingProvider } from "../interfaces/IRoutingProvider";
import { IGeocodingProvider } from "../interfaces/IGeocodingProvider";
import { ITrafficProvider } from "../interfaces/ITrafficProvider";
import { GoogleMapsProvider } from "../providers/google/GoogleMapsProvider";
import { GoogleRoutingProvider } from "../providers/google/GoogleRoutingProvider";
import { GoogleGeocodingProvider } from "../providers/google/GoogleGeocodingProvider";
import { GoogleTrafficProvider } from "../providers/google/GoogleTrafficProvider";
import { MapboxMapProvider } from "../providers/mapbox/MapboxMapProvider";
import { MapboxRoutingProvider } from "../providers/mapbox/MapboxRoutingProvider";
import { MapboxGeocodingProvider } from "../providers/mapbox/MapboxGeocodingProvider";
import { MapboxTrafficProvider } from "../providers/mapbox/MapboxTrafficProvider";
import { ResilientRoutingProvider } from "../fallback/ResilientRoutingProvider";
import { ResilientGeocodingProvider } from "../fallback/ResilientGeocodingProvider";
import { ResilientTrafficProvider } from "../fallback/ResilientTrafficProvider";

/**
 * MapProviderRegistry.
 * Single source of truth for constructing and wiring map, geocoding,
 * routing, and traffic providers based on runtime configuration.
 */
export class MapProviderRegistry {
  private static instance: MapProviderRegistry | null = null;

  private constructor(private readonly config: MapPlatformConfig) {}

  public static getInstance(config: MapPlatformConfig = mapConfig): MapProviderRegistry {
    if (!this.instance) {
      this.instance = new MapProviderRegistry(config);
    }
    return this.instance;
  }

  /**
   * Resolves the configured visual MapProvider (Google or Mapbox).
   */
  public getMapProvider(): IMapProvider {
    return this.config.mapProvider === "google"
      ? new GoogleMapsProvider(this.config.credentials.googleMapsApiKey)
      : new MapboxMapProvider(this.config.credentials.mapboxAccessToken);
  }

  /**
   * Resolves the RoutingProvider with resilient fallback.
   * If primary is Google, fallback is Mapbox, and vice-versa.
   */
  public getRoutingProvider(): IRoutingProvider {
    const google = new GoogleRoutingProvider(this.config.credentials.googleMapsApiKey);
    const mapbox = new MapboxRoutingProvider(this.config.credentials.mapboxAccessToken);

    const primary = this.config.routingProvider === "google" ? google : mapbox;
    const fallback = this.config.routingProvider === "google" ? mapbox : google;

    return new ResilientRoutingProvider(primary, fallback, this.config.enableFallback);
  }

  /**
   * Resolves the GeocodingProvider with resilient fallback.
   */
  public getGeocodingProvider(): IGeocodingProvider {
    const google = new GoogleGeocodingProvider(this.config.credentials.googleMapsApiKey);
    const mapbox = new MapboxGeocodingProvider(this.config.credentials.mapboxAccessToken);

    const primary = this.config.geocodingProvider === "google" ? google : mapbox;
    const fallback = this.config.geocodingProvider === "google" ? mapbox : google;

    return new ResilientGeocodingProvider(primary, fallback, this.config.enableFallback);
  }

  /**
   * Resolves the TrafficProvider with resilient fallback.
   */
  public getTrafficProvider(): ITrafficProvider {
    const google = new GoogleTrafficProvider(this.config.credentials.googleMapsApiKey);
    const mapbox = new MapboxTrafficProvider(this.config.credentials.mapboxAccessToken);

    const primary = this.config.trafficProvider === "google" ? google : mapbox;
    const fallback = this.config.trafficProvider === "google" ? mapbox : google;

    return new ResilientTrafficProvider(primary, fallback, this.config.enableFallback);
  }
}
