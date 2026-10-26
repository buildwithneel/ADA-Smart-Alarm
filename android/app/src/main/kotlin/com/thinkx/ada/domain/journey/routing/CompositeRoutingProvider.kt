package com.thinkx.ada.domain.journey.routing

/**
 * Resilient routing provider that attempts [primary] first, and gracefully
 * falls back to [fallback] upon any network failure, timeout, or rate-limiting.
 */
class CompositeRoutingProvider(
    private val primary: RoutingProvider,
    private val fallback: RoutingProvider = FallbackRoutingProvider()
) : RoutingProvider {

    override val name: String
        get() = primary.name

    override suspend fun calculateRoute(request: RouteRequest): Result<RouteResult> {
        val primaryResult = primary.calculateRoute(request)
        if (primaryResult.isSuccess) {
            return primaryResult
        }

        // Primary failed; engage fallback
        val fallbackResult = fallback.calculateRoute(request)
        return if (fallbackResult.isSuccess) {
            val res = fallbackResult.getOrThrow()
            Result.success(
                res.copy(
                    providerName = "${fallback.name} (Primary unavailable: ${primaryResult.exceptionOrNull()?.message})"
                )
            )
        } else {
            primaryResult // Return original error if both somehow fail
        }
    }
}
