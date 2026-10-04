import { IMapProvider } from "../../interfaces/IMapProvider";
import { GeoPoint, MapMarkerOptions, RoutePolylineOptions, BoundingBox } from "../../models/types";

/**
 * Mapbox GL JS implementation of IMapProvider.
 *
 * [INTEGRATION HOOK - STEP 3/4]:
 * In production integration, this mounts an instance of `mapboxgl.Map`:
 * ```ts
 * new mapboxgl.Map({
 *   container,
 *   style: 'mapbox://styles/mapbox/dark-v11',
 *   center: [center.longitude, center.latitude],
 *   zoom,
 *   accessToken: this.accessToken
 * });
 * ```
 */
export class MapboxMapProvider implements IMapProvider {
  readonly name = "mapbox" as const;
  private container: HTMLElement | null = null;
  private markers = new Map<string, MapMarkerOptions>();

  constructor(public readonly accessToken?: string) {}

  async mount(container: HTMLElement, center: GeoPoint, zoom: number): Promise<void> {
    this.container = container;
    container.setAttribute("data-map-provider", "mapbox");
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
    // In real implementation: adds GeoJSON source and line layer to Mapbox GL map
  }

  clearRoute(): void {
    // In real implementation: removes GeoJSON layer from map
  }

  fitBounds(_bounds: BoundingBox): void {
    // In real implementation: map.fitBounds([[bounds.west, bounds.south], [bounds.east, bounds.north]])
  }

  destroy(): void {
    this.markers.clear();
    this.container = null;
  }
}
