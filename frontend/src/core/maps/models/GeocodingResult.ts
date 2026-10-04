import { MapProviderName } from "./types";

/**
 * Normalized Geocoding Result.
 * Standard contract across Google Geocoding/Places API and Mapbox Geocoding API.
 */
export interface GeocodingResult {
  latitude: number;
  longitude: number;
  formattedAddress: string;
  placeId: string;
  provider: MapProviderName;
  confidenceScore?: number;
  addressComponents?: {
    streetNumber?: string;
    route?: string;
    locality?: string;
    state?: string;
    country?: string;
    postalCode?: string;
  };
}

export interface PlaceAutocompletePrediction {
  placeId: string;
  primaryText: string;
  secondaryText: string;
  fullText: string;
  provider: MapProviderName;
}
