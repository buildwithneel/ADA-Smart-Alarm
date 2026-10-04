import { IMapProvider } from "../../interfaces/IMapProvider";
import { GeoPoint, MapMarkerOptions, RoutePolylineOptions, BoundingBox } from "../../models/types";

/**
 * Google Maps Platform implementation of IMapProvider.
 *
 * [INTEGRATION HOOK - STEP 3/4]:
 * In production integration, this class dynamically injects Google Maps JavaScript API:
 * `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places,routes`
 * and mounts an instance of `google.maps.Map`.
 */
export class GoogleMapsProvider implements IMapProvider {
  readonly name = "google" as const;
  private container: HTMLElement | null = null;
  private markers = new Map<string, MapMarkerOptions>();

  constructor(public readonly apiKey?: string) {}

  async mount(container: HTMLElement, center: GeoPoint, zoom: number): Promise<void> {
    this.container = container;
    // Mock container initial setup
    container.setAttribute("data-map-provider", "google");
    container.setAttribute("data-center", `${center.latitude},${center.longitude}`);
    container.setAttribute("data-zoom", zoom.toString());
  }

  setCenter(center: GeoPoint, zoom?: number): void {
    if (this.container) {
      this.container.setAttribute("data-center", `${center.latitude},${center.longitude}`);
      if (zoom) this.container.setAttribute("data-zoom", zoom.toString());
    }
  }

  addMarker(options: MapMarkerOptions): void {
    this.markers.set(options.id, options);
  }

  removeMarker(id: string): void {
    this.markers.delete(id);
  }

  drawRoute(_geometry: string, _options?: RoutePolylineOptions): void {
    // In real implementation: renders google.maps.Polyline with decoded path
  }

  clearRoute(): void {
    // In real implementation: polyline.setMap(null)
  }

  fitBounds(_bounds: BoundingBox): void {
    // In real implementation: map.fitBounds(new google.maps.LatLngBounds(...))
  }

  destroy(): void {
    this.markers.clear();
    this.container = null;
  }
}
