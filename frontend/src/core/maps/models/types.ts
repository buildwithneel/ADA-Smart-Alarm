/**
 * Normalized Geographical and Mapping Types for ADA.
 * Decouples domain logic and UI from Google Maps and Mapbox vendor SDKs.
 */

export type MapProviderName = "google" | "mapbox";

export interface GeoPoint {
  latitude: number;
  longitude: number;
}

export interface BoundingBox {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface MapMarkerOptions {
  id: string;
  position: GeoPoint;
  title?: string;
  type: "origin" | "destination" | "waypoint" | "incident";
  color?: string;
}

export interface RoutePolylineOptions {
  color?: string;
  weight?: number;
  opacity?: number;
  dashArray?: string;
}

export interface RouteRequestOptions {
  origin: GeoPoint;
  destination: GeoPoint;
  transportMode: "driving" | "transit" | "bicycling" | "walking";
  departureTime?: Date;
  avoidTolls?: boolean;
  avoidHighways?: boolean;
}
