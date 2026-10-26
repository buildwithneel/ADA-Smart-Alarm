package com.thinkx.ada.network.interceptor

import com.thinkx.ada.auth.repository.AuthRepository
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response

/**
 * Interceptor that attaches the current Firebase ID token in the Authorization Bearer header.
 *
 * Security considerations:
 * - Never logs or dumps the Bearer token.
 * - If no session exists or token retrieval fails, request continues unauthenticated
 *   (server-side authorization will return 401 Unauthorized appropriately).
 */
class AuthInterceptor(
    private val authRepository: AuthRepository
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()

        // If request already has Authorization header, don't overwrite
        if (originalRequest.header("Authorization") != null) {
            return chain.proceed(originalRequest)
        }

        val tokenResult = runBlocking {
            authRepository.getIdToken(forceRefresh = false)
        }

        val token = tokenResult.getOrNull()
        val authenticatedRequest = if (!token.isNullOrBlank()) {
            originalRequest.newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
        } else {
            originalRequest
        }

        val response = chain.proceed(authenticatedRequest)

        // If server returns 401 Unauthorized, attempt a single forced token refresh retry
        if (response.code == 401 && !token.isNullOrBlank()) {
            response.close()
            val freshTokenResult = runBlocking {
                authRepository.getIdToken(forceRefresh = true)
            }
            val freshToken = freshTokenResult.getOrNull()
            if (!freshToken.isNullOrBlank() && freshToken != token) {
                val retryRequest = originalRequest.newBuilder()
                    .header("Authorization", "Bearer $freshToken")
                    .build()
                return chain.proceed(retryRequest)
            }
        }

        return response
    }
}
