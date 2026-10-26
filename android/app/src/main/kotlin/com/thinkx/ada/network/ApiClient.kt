package com.thinkx.ada.network

import com.thinkx.ada.BuildConfig
import com.thinkx.ada.auth.repository.AuthRepository
import com.thinkx.ada.network.api.AdaApiService
import com.thinkx.ada.network.interceptor.AuthInterceptor
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Factory and provider for AdaApiService and underlying HTTP stack.
 */
object ApiClient {

    private val json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
        isLenient = true
        encodeDefaults = true
    }

    /**
     * Builds a configured OkHttpClient with token authorization and defensive security.
     */
    fun createOkHttpClient(
        authRepository: AuthRepository,
        enableLogging: Boolean = BuildConfig.DEBUG
    ): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .writeTimeout(20, TimeUnit.SECONDS)
            .addInterceptor(AuthInterceptor(authRepository))

        if (enableLogging) {
            val loggingInterceptor = HttpLoggingInterceptor { message ->
                // Ensure auth tokens and sensitive payloads are never dumped
                if (!message.contains("Authorization", ignoreCase = true)) {
                    android.util.Log.d("ADA_HTTP", message)
                }
            }.apply {
                level = HttpLoggingInterceptor.Level.BASIC
            }
            builder.addInterceptor(loggingInterceptor)
        }

        return builder.build()
    }

    /**
     * Creates an instance of [AdaApiService] with the given baseUrl.
     * In Android emulator, baseUrl is typically "http://10.0.2.2:8000/api/v1/".
     * In production, baseUrl is HTTPS (e.g., "https://api.ada-alarm.app/api/v1/").
     */
    fun createApiService(
        authRepository: AuthRepository,
        baseUrl: String = BuildConfig.API_BASE_URL
    ): AdaApiService {
        val client = createOkHttpClient(authRepository)
        val contentType = "application/json".toMediaType()

        val normalizedBaseUrl = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"

        val retrofit = Retrofit.Builder()
            .baseUrl(normalizedBaseUrl)
            .client(client)
            .addConverterFactory(json.asConverterFactory(contentType))
            .build()

        return retrofit.create(AdaApiService::class.java)
    }
}
