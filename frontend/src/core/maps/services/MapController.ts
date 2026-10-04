import { GeoPoint } from "../models/types";


export interface MapViewportState {
  center: GeoPoint;
  zoom: number;
}

export class MapController {
  private center: GeoPoint;
  private zoom: number;
  private onViewportChange?: (state: MapViewportState) => void;

  constructor(
    initialCenter: GeoPoint = { latitude: 22.5996, longitude: 72.8205 },
    initialZoom = 13,
    onViewportChange?: (state: MapViewportState) => void
  ) {
    this.center = initialCenter;
    this.zoom = initialZoom;
    this.onViewportChange = onViewportChange;
  }

  public getCenter(): GeoPoint {
    return this.center;
  }

  public getZoom(): number {
    return this.zoom;
  }

  public setCenter(center: GeoPoint, zoom?: number): void {
    this.center = center;
    if (typeof zoom === "number") {
      this.zoom = Math.max(3, Math.min(zoom, 19));
    }
    this.notify();
  }

  public zoomIn(): void {
    if (this.zoom < 19) {
      this.zoom += 1;
      this.notify();
    }
  }

  public zoomOut(): void {
    if (this.zoom > 3) {
      this.zoom -= 1;
      this.notify();
    }
  }

  public fitRoute(origin: GeoPoint, destination: GeoPoint): void {
    const midLat = (origin.latitude + destination.latitude) / 2;
    const midLng = (origin.longitude + destination.longitude) / 2;
    this.center = { latitude: midLat, longitude: midLng };

    // Calculate approximate zoom based on distance
    const latDiff = Math.abs(origin.latitude - destination.latitude);
    const lngDiff = Math.abs(origin.longitude - destination.longitude);
    const maxDiff = Math.max(latDiff, lngDiff);

    if (maxDiff > 2.0) this.zoom = 8;
    else if (maxDiff > 0.8) this.zoom = 10;
    else if (maxDiff > 0.3) this.zoom = 11;
    else if (maxDiff > 0.08) this.zoom = 13;
    else this.zoom = 14;

    this.notify();
  }

  private notify(): void {
    this.onViewportChange?.({
      center: this.center,
      zoom: this.zoom,
    });
  }
}
