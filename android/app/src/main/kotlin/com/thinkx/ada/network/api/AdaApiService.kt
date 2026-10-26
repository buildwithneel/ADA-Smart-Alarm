package com.thinkx.ada.network.api

import com.thinkx.ada.network.dto.AlarmCreateDto
import com.thinkx.ada.network.dto.AlarmDto
import com.thinkx.ada.network.dto.AlarmUpdateDto
import com.thinkx.ada.network.dto.DestinationCreateDto
import com.thinkx.ada.network.dto.DestinationDto
import com.thinkx.ada.network.dto.UserDto
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Retrofit contract for ADA FastAPI backend services (/api/v1).
 */
interface AdaApiService {

    // --- Users ---
    @GET("users/me")
    suspend fun getCurrentUser(): UserDto

    // --- Destinations ---
    @GET("destinations")
    suspend fun getDestinations(
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 100
    ): List<DestinationDto>

    @POST("destinations")
    suspend fun createDestination(
        @Body body: DestinationCreateDto
    ): DestinationDto

    @GET("destinations/{id}")
    suspend fun getDestination(
        @Path("id") id: String
    ): DestinationDto

    @DELETE("destinations/{id}")
    suspend fun deleteDestination(
        @Path("id") id: String
    ): Response<Unit>

    // --- Alarms ---
    @GET("alarms")
    suspend fun getAlarms(
        @Query("status") status: String? = null,
        @Query("filter") filter: String? = null,
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 100
    ): List<AlarmDto>

    @POST("alarms")
    suspend fun createAlarm(
        @Body body: AlarmCreateDto,
        @Header("X-Idempotency-Key") idempotencyKey: String? = null
    ): AlarmDto

    @GET("alarms/{id}")
    suspend fun getAlarm(
        @Path("id") id: String
    ): AlarmDto

    @PATCH("alarms/{id}")
    suspend fun updateAlarm(
        @Path("id") id: String,
        @Body body: AlarmUpdateDto
    ): AlarmDto

    @DELETE("alarms/{id}")
    suspend fun deleteAlarm(
        @Path("id") id: String
    ): Response<Unit>

    @POST("alarms/{id}/enable")
    suspend fun enableAlarm(
        @Path("id") id: String
    ): AlarmDto

    @POST("alarms/{id}/disable")
    suspend fun disableAlarm(
        @Path("id") id: String
    ): AlarmDto

    @POST("alarms/{id}/refresh")
    suspend fun refreshAlarm(
        @Path("id") id: String
    ): AlarmDto

    // --- Routing & Live Traffic ---
    @POST("routes")
    suspend fun calculateRoute(
        @Body body: com.thinkx.ada.network.dto.RouteRequestDto
    ): com.thinkx.ada.network.dto.RouteResultDto
}
