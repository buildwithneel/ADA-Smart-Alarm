import { IGeocodingProvider } from "../../interfaces/IGeocodingProvider";
import { GeoPoint } from "../../models/types";
import { GeocodingResult, PlaceAutocompletePrediction } from "../../models/GeocodingResult";

/**
 * Mapbox Geocoding v6 implementation.
 *
 * [INTEGRATION HOOK - STEP 3/4]:
 * In real implementation: calls Mapbox Geocoding API:
 * `GET https://api.mapbox.com/search/geocode/v6/forward?q=${encodeURIComponent(query)}&access_token=${token}`
 */
export class MapboxGeocodingProvider implements IGeocodingProvider {
  readonly name = "mapbox" as const;

  constructor(public readonly accessToken?: string) {}

  async geocode(addressQuery: string): Promise<GeocodingResult[]> {
    return [
      {
        latitude: 22.5996,
        longitude: 72.8205,
        formattedAddress: `${addressQuery}, Gujarat, India`,
        placeId: `mapbox-feat-${Date.now()}`,
        provider: "mapbox",
        confidenceScore: 0.96,
        addressComponents: {
          locality: "Changa",
          state: "Gujarat",
          country: "India",
          postalCode: "388421",
        },
      },
    ];
  }

  async reverseGeocode(point: GeoPoint): Promise<GeocodingResult | null> {
    return {
      latitude: point.latitude,
      longitude: point.longitude,
      formattedAddress: `Near (${point.latitude.toFixed(4)}, ${point.longitude.toFixed(4)})`,
      placeId: `mapbox-rev-${Date.now()}`,
      provider: "mapbox",
      confidenceScore: 0.94,
    };
  }

  async autocomplete(input: string): Promise<PlaceAutocompletePrediction[]> {
    if (!input.trim()) return [];
    return [
      {
        placeId: "mapbox-charusat-1",
        primaryText: "CHARUSAT University",
        secondaryText: "Highway, Changa, Anand, Gujarat",
        fullText: "CHARUSAT University, Highway, Changa, Anand, Gujarat",
        provider: "mapbox",
      },
      {
        placeId: "mapbox-thinkx-2",
        primaryText: "ThinkX Tech Labs",
        secondaryText: "Airport Road, Gandhinagar, Gujarat",
        fullText: "ThinkX Tech Labs, Airport Road, Gandhinagar, Gujarat",
        provider: "mapbox",
      },
    ];
  }
}
