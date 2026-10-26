package com.thinkx.ada.network

import com.thinkx.ada.auth.FakeAuthRepository
import com.thinkx.ada.network.interceptor.AuthInterceptor
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Protocol
import okhttp3.Request
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class AuthInterceptorTest {

    private lateinit var authRepository: FakeAuthRepository
    private lateinit var interceptor: AuthInterceptor

    @Before
    fun setup() {
        authRepository = FakeAuthRepository(mockToken = "valid-test-token-xyz")
        interceptor = AuthInterceptor(authRepository)
    }

    @Test
    fun interceptor_attachesBearerTokenHeader_whenTokenAvailable() {
        val originalRequest = Request.Builder()
            .url("https://api.ada-alarm.app/api/v1/alarms")
            .build()

        var executedRequest: Request? = null

        val fakeChain = object : Interceptor.Chain {
            override fun request(): Request = originalRequest
            override fun proceed(request: Request): Response {
                executedRequest = request
                return Response.Builder()
                    .request(request)
                    .protocol(Protocol.HTTP_1_1)
                    .code(200)
                    .message("OK")
                    .body("{}".toResponseBody("application/json".toMediaType()))
                    .build()
            }
            override fun connection() = null
            override fun call() = throw UnsupportedOperationException()
            override fun connectTimeoutMillis() = 1000
            override fun readTimeoutMillis() = 1000
            override fun writeTimeoutMillis() = 1000
            override fun withConnectTimeout(timeout: Int, unit: java.util.concurrent.TimeUnit) = this
            override fun withReadTimeout(timeout: Int, unit: java.util.concurrent.TimeUnit) = this
            override fun withWriteTimeout(timeout: Int, unit: java.util.concurrent.TimeUnit) = this
        }

        interceptor.intercept(fakeChain)

        assertNotNull(executedRequest)
        assertEquals("Bearer valid-test-token-xyz", executedRequest!!.header("Authorization"))
    }

    @Test
    fun interceptor_omitsAuthHeader_whenUnauthenticated() {
        authRepository.mockToken = null

        val originalRequest = Request.Builder()
            .url("https://api.ada-alarm.app/api/v1/health")
            .build()

        var executedRequest: Request? = null

        val fakeChain = object : Interceptor.Chain {
            override fun request(): Request = originalRequest
            override fun proceed(request: Request): Response {
                executedRequest = request
                return Response.Builder()
                    .request(request)
                    .protocol(Protocol.HTTP_1_1)
                    .code(200)
                    .message("OK")
                    .body("{}".toResponseBody("application/json".toMediaType()))
                    .build()
            }
            override fun connection() = null
            override fun call() = throw UnsupportedOperationException()
            override fun connectTimeoutMillis() = 1000
            override fun readTimeoutMillis() = 1000
            override fun writeTimeoutMillis() = 1000
            override fun withConnectTimeout(timeout: Int, unit: java.util.concurrent.TimeUnit) = this
            override fun withReadTimeout(timeout: Int, unit: java.util.concurrent.TimeUnit) = this
            override fun withWriteTimeout(timeout: Int, unit: java.util.concurrent.TimeUnit) = this
        }

        interceptor.intercept(fakeChain)

        assertNotNull(executedRequest)
        assertNull(executedRequest!!.header("Authorization"))
    }

    @Test
    fun interceptor_retriesWithFreshToken_on401Unauthorized() {
        authRepository.mockToken = "expired-token"

        val originalRequest = Request.Builder()
            .url("https://api.ada-alarm.app/api/v1/alarms")
            .build()

        var callCount = 0
        val capturedTokens = mutableListOf<String?>()

        val fakeChain = object : Interceptor.Chain {
            override fun request(): Request = originalRequest
            override fun proceed(request: Request): Response {
                callCount++
                capturedTokens.add(request.header("Authorization"))
                if (callCount == 1) {
                    // Update auth repository with fresh token upon 401
                    authRepository.mockToken = "refreshed-fresh-token-abc"
                    return Response.Builder()
                        .request(request)
                        .protocol(Protocol.HTTP_1_1)
                        .code(401)
                        .message("Unauthorized")
                        .body("{}".toResponseBody("application/json".toMediaType()))
                        .build()
                }
                return Response.Builder()
                    .request(request)
                    .protocol(Protocol.HTTP_1_1)
                    .code(200)
                    .message("OK")
                    .body("{}".toResponseBody("application/json".toMediaType()))
                    .build()
            }
            override fun connection() = null
            override fun call() = throw UnsupportedOperationException()
            override fun connectTimeoutMillis() = 1000
            override fun readTimeoutMillis() = 1000
            override fun writeTimeoutMillis() = 1000
            override fun withConnectTimeout(timeout: Int, unit: java.util.concurrent.TimeUnit) = this
            override fun withReadTimeout(timeout: Int, unit: java.util.concurrent.TimeUnit) = this
            override fun withWriteTimeout(timeout: Int, unit: java.util.concurrent.TimeUnit) = this
        }

        val response = interceptor.intercept(fakeChain)

        assertEquals(200, response.code)
        assertEquals(2, callCount)
        assertEquals("Bearer expired-token", capturedTokens[0])
        assertEquals("Bearer refreshed-fresh-token-abc", capturedTokens[1])
        assertTrue(authRepository.lastForceRefresh == true)
    }
}
