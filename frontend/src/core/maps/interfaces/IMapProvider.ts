import { GeoPoint, MapMarkerOptions, RoutePolylineOptions, BoundingBox } from "../models/types";

/**
 * Common Map Display Provider Contract.
 * Abstracts interactive map rendering across Google Maps JavaScript SDK and Mapbox GL JS.
 */
export interface IMapProvider {
  readonly name: "google" | "mapbox";

  /**
   * Mounts the map onto the target DOM container.
   */
  mount(container: HTMLElement, center: GeoPoint, zoom: number): Promise<void>;

  /**
   * Sets map camera position.
   */
  setCenter(center: GeoPoint, zoom?: number): void;

  /**
   * Adds or updates a map marker.
   */
  addMarker(options: MapMarkerOptions): void;

  /**
   * Removes a marker by ID.
   */
  removeMarker(id: string): void;

  /**
   * Draws a route polyline path on the map.
   */
  drawRoute(geometry: string, options?: RoutePolylineOptions): void;

  /**
   * Clears route lines from map.
   */
  clearRoute(): void;

  /**
   * Fits map camera to enclose bounding coordinates.
   */
  fitBounds(bounds: BoundingBox): void;

  /**
   * Cleanly unmounts and cleans up memory resources.
   */
  destroy(): void;
}
