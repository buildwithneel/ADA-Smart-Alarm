package com.thinkx.ada.domain.journey.routing

import com.thinkx.ada.network.api.AdaApiService
import com.thinkx.ada.network.dto.LocationDto
import com.thinkx.ada.network.dto.RouteRequestDto

/**
 * RoutingProvider backed by the ADA FastAPI server, which securely proxies
 * Google Maps and Mapbox APIs with live road traffic and Redis caching.
 */
class BackendRoutingProvider(
    private val apiService: AdaApiService
) : RoutingProvider {

    override val name: String = "ADA Backend Proxy (Live Traffic)"

    override suspend fun calculateRoute(request: RouteRequest): Result<RouteResult> {
        return try {
            val dto = apiService.calculateRoute(
                RouteRequestDto(
                    origin = LocationDto(request.originLat, request.originLng),
                    destination = LocationDto(request.destinationLat, request.destinationLng),
                    travelMode = request.travelMode
                )
            )

            val isTraffic = dto.isTrafficAware && dto.trafficDurationSeconds > 0
            val providerName = when {
                !isTraffic -> "Fallback Simulation (No API key)"
                dto.provider.equals("google", ignoreCase = true) -> "Google Maps (Live Traffic)"
                dto.provider.equals("mapbox", ignoreCase = true) -> "Mapbox (Live Traffic)"
                else -> "${dto.provider} (Live Traffic)"
            }

            Result.success(
                RouteResult(
                    distanceMeters = dto.distanceMeters,
                    baseDurationSeconds = dto.durationSeconds,
                    trafficDurationSeconds = dto.trafficDurationSeconds,
                    routeGeometry = dto.routeGeometry,
                    providerName = providerName,
                    isTrafficAware = isTraffic,
                    congestionLevel = dto.summary?.congestionLevel
                )
            )
        } catch (e: Exception) {
            Result.failure(RoutingError.NetworkError("Failed to reach routing proxy: ${e.message}", e))
        }
    }
}
