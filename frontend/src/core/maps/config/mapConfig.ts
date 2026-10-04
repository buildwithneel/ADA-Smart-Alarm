import { env } from "@/core/config/env";
import { MapProviderName } from "../models/types";

export interface MapPlatformConfig {
  mapProvider: MapProviderName;
  routingProvider: MapProviderName;
  geocodingProvider: MapProviderName;
  trafficProvider: MapProviderName;
  enableFallback: boolean;
  credentials: {
    googleMapsApiKey?: string;
    mapboxAccessToken?: string;
  };
}

/**
 * Global Map Platform Configuration.
 * Providers can be selected completely independently via environment variables.
 *
 * Example:
 * MAP_PROVIDER=mapbox
 * ROUTING_PROVIDER=google
 * GEOCODING_PROVIDER=google
 * TRAFFIC_PROVIDER=google
 */
export const mapConfig: MapPlatformConfig = {
  mapProvider: (env.VITE_MAP_PROVIDER as MapProviderName) || "mapbox",
  routingProvider: (env.VITE_ROUTING_PROVIDER as MapProviderName) || "google",
  geocodingProvider: (env.VITE_GEOCODING_PROVIDER as MapProviderName) || "google",
  trafficProvider: (env.VITE_TRAFFIC_PROVIDER as MapProviderName) || "google",
  enableFallback: env.VITE_ENABLE_MAP_FALLBACK !== false,
  credentials: {
    googleMapsApiKey: env.VITE_GOOGLE_MAPS_API_KEY,
    mapboxAccessToken: env.VITE_MAPBOX_ACCESS_TOKEN,
  },
};
