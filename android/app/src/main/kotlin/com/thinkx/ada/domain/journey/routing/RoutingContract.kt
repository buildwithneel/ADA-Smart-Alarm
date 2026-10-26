package com.thinkx.ada.domain.journey.routing

/**
 * Request parameters for routing queries.
 */
data class RouteRequest(
    val originLat: Double,
    val originLng: Double,
    val destinationLat: Double,
    val destinationLng: Double,
    val travelMode: String = "driving",
    val departureTimeEpochSec: Long? = null
)

/**
 * Normalized result from a routing calculation.
 */
data class RouteResult(
    val distanceMeters: Int,
    val baseDurationSeconds: Int,
    val trafficDurationSeconds: Int,
    val routeGeometry: String = "",
    val providerName: String,
    val isTrafficAware: Boolean,
    val congestionLevel: String? = null
)

/**
 * Typed routing exceptions.
 */
sealed class RoutingError(message: String, cause: Throwable? = null) : Exception(message, cause) {
    class NetworkError(message: String, cause: Throwable? = null) : RoutingError(message, cause)
    class RateLimited(message: String = "Routing provider rate limit exceeded") : RoutingError(message)
    class ProviderUnavailable(message: String = "Routing provider unavailable") : RoutingError(message)
    class InvalidCoordinates(message: String) : RoutingError(message)
}

/**
 * Pure Kotlin contract for routing providers.
 */
interface RoutingProvider {
    val name: String
    suspend fun calculateRoute(request: RouteRequest): Result<RouteResult>
}
