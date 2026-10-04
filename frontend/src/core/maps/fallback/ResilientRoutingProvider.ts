import { IRoutingProvider } from "../interfaces/IRoutingProvider";
import { RouteRequestOptions } from "../models/types";
import { RouteResult } from "../models/RouteResult";

/**
 * Resilient Fallback Routing Decorator.
 * Transparently catches network errors, HTTP 429 quota exhaustion, or unexpected outages
 * from the primary routing provider and executes the fallback provider seamlessly.
 */
export class ResilientRoutingProvider implements IRoutingProvider {
  readonly name: "google" | "mapbox";

  constructor(
    private readonly primary: IRoutingProvider,
    private readonly fallback: IRoutingProvider,
    private readonly enableFallback: boolean = true
  ) {
    this.name = primary.name;
  }

  async calculateRoute(options: RouteRequestOptions): Promise<RouteResult> {
    try {
      return await this.primary.calculateRoute(options);
    } catch (primaryError) {
      if (!this.enableFallback) {
        throw primaryError;
      }

      console.warn(
        `⚠️ [ADA Routing Fallback] Primary routing provider '${this.primary.name}' failed. ` +
        `Falling back to '${this.fallback.name}' immediately.`,
        primaryError
      );

      try {
        const fallbackResult = await this.fallback.calculateRoute(options);
        return {
          ...fallbackResult,
          summary: {
            ...fallbackResult.summary,
            formattedTrafficDelay: `${fallbackResult.summary.formattedTrafficDelay} (via ${this.fallback.name} fallback)`,
          },
        };
      } catch (fallbackError) {
        console.error(
          `❌ [ADA Routing Fallback] Both primary ('${this.primary.name}') and fallback ('${this.fallback.name}') providers failed.`,
          { primaryError, fallbackError }
        );
        throw new Error(
          `All routing providers failed. Primary: ${(primaryError as Error).message}. ` +
          `Fallback: ${(fallbackError as Error).message}`
        );
      }
    }
  }

  async estimateDurationSeconds(options: RouteRequestOptions): Promise<{
    durationSeconds: number;
    trafficDurationSeconds: number;
    distanceMeters: number;
  }> {
    try {
      return await this.primary.estimateDurationSeconds(options);
    } catch (primaryError) {
      if (!this.enableFallback) throw primaryError;
      console.warn(`[ADA Fallback] Primary duration estimation failed, invoking fallback.`);
      return await this.fallback.estimateDurationSeconds(options);
    }
  }
}
