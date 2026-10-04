import { IGeocodingProvider } from "../../interfaces/IGeocodingProvider";
import { GeoPoint } from "../../models/types";
import { GeocodingResult, PlaceAutocompletePrediction } from "../../models/GeocodingResult";

/**
 * Google Maps Geocoding & Places implementation.
 *
 * [INTEGRATION HOOK - STEP 3/4]:
 * In real implementation: calls Google Geocoding API:
 * `GET https://maps.googleapis.com/maps/api/geocode/json?address=${query}&key=${apiKey}`
 * and Google Places Autocomplete:
 * `GET https://maps.googleapis.com/maps/api/place/autocomplete/json?input=${input}&key=${apiKey}`
 */
export class GoogleGeocodingProvider implements IGeocodingProvider {
  readonly name = "google" as const;

  constructor(public readonly apiKey?: string) {}

  async geocode(addressQuery: string): Promise<GeocodingResult[]> {
    // Normalized mock result simulating Google Geocoding response
    return [
      {
        latitude: 22.5996,
        longitude: 72.8205,
        formattedAddress: `${addressQuery}, Gujarat, India`,
        placeId: `google-place-${Date.now()}`,
        provider: "google",
        confidenceScore: 0.98,
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
      formattedAddress: `Location near (${point.latitude.toFixed(4)}, ${point.longitude.toFixed(4)})`,
      placeId: `google-rev-${Date.now()}`,
      provider: "google",
      confidenceScore: 0.95,
    };
  }

  async autocomplete(input: string): Promise<PlaceAutocompletePrediction[]> {
    if (!input.trim()) return [];
    return [
      {
        placeId: "google-charusat-1",
        primaryText: "CHARUSAT University",
        secondaryText: "Highway, Changa, Gujarat 388421",
        fullText: "CHARUSAT University, Highway, Changa, Gujarat 388421",
        provider: "google",
      },
      {
        placeId: "google-thinkx-2",
        primaryText: "ThinkX Tech Labs",
        secondaryText: "Infocity, Gandhinagar, Gujarat",
        fullText: "ThinkX Tech Labs, Infocity, Gandhinagar, Gujarat",
        provider: "google",
      },
    ];
  }
}
