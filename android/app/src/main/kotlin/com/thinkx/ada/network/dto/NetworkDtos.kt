package com.thinkx.ada.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class UserDto(
    val id: String,
    val firebaseUid: String? = null,
    val email: String,
    val name: String? = null,
    val profileImage: String? = null,
    val timezone: String = "UTC"
)

@Serializable
data class DestinationDto(
    val id: String,
    val name: String,
    val address: String,
    val latitude: Double,
    val longitude: Double,
    val type: String? = "saved",
    @SerialName("is_favorite")
    val isFavorite: Boolean? = false
)

@Serializable
data class DestinationCreateDto(
    val name: String,
    val address: String,
    val latitude: Double,
    val longitude: Double,
    val type: String = "saved",
    @SerialName("is_favorite")
    val isFavorite: Boolean = false
)

@Serializable
data class AlarmDto(
    val id: String,
    @SerialName("user_id")
    val userId: String? = null,
    @SerialName("destination_id")
    val destinationId: String,
    val title: String,
    @SerialName("arrival_time")
    val arrivalTime: String,
    @SerialName("preparation_time")
    val preparationTime: Int = 30,
    @SerialName("safety_buffer")
    val safetyBuffer: Int = 15,
    @SerialName("transportation_mode")
    val transportationMode: String = "driving",
    val enabled: Boolean = true,
    val status: String = "scheduled",
    val timezone: String = "Asia/Kolkata",
    @SerialName("calculated_wake_time")
    val calculatedWakeTime: String? = null,
    @SerialName("calculated_leave_time")
    val calculatedLeaveTime: String? = null,
    @SerialName("planned_arrival_time")
    val plannedArrivalTime: String? = null,
    @SerialName("current_travel_minutes")
    val currentTravelMinutes: Int? = 0,
    @SerialName("traffic_delay_minutes")
    val trafficDelayMinutes: Int? = 0,
    @SerialName("schedule_version")
    val scheduleVersion: Int = 1,
    @SerialName("origin_lat")
    val originLat: Double? = null,
    @SerialName("origin_lng")
    val originLng: Double? = null,
    @SerialName("created_at")
    val createdAt: String? = null,
    @SerialName("updated_at")
    val updatedAt: String? = null
)

@Serializable
data class AlarmCreateDto(
    val title: String,
    @SerialName("destination_id")
    val destinationId: String,
    @SerialName("arrival_time")
    val arrivalTime: String,
    @SerialName("arrival_date")
    val arrivalDate: String? = null,
    @SerialName("preparation_time")
    val preparationTime: Int = 30,
    @SerialName("safety_buffer")
    val safetyBuffer: Int = 15,
    @SerialName("transportation_mode")
    val transportationMode: String = "driving",
    val enabled: Boolean = true,
    val timezone: String = "Asia/Kolkata",
    @SerialName("origin_lat")
    val originLat: Double? = null,
    @SerialName("origin_lng")
    val originLng: Double? = null
)

@Serializable
data class AlarmUpdateDto(
    val title: String? = null,
    @SerialName("destination_id")
    val destinationId: String? = null,
    @SerialName("arrival_time")
    val arrivalTime: String? = null,
    @SerialName("arrival_date")
    val arrivalDate: String? = null,
    @SerialName("preparation_time")
    val preparationTime: Int? = null,
    @SerialName("safety_buffer")
    val safetyBuffer: Int? = null,
    @SerialName("transportation_mode")
    val transportationMode: String? = null,
    val enabled: Boolean? = null,
    val status: String? = null,
    val timezone: String? = null
)

@Serializable
data class ApiProblemDetails(
    val title: String? = null,
    val status: Int? = null,
    val detail: String? = null,
    val instance: String? = null
)

@Serializable
data class LocationDto(
    val latitude: Double,
    val longitude: Double
)

@Serializable
data class RouteRequestDto(
    val origin: LocationDto,
    val destination: LocationDto,
    @SerialName("travel_mode")
    val travelMode: String = "driving"
)

@Serializable
data class RouteSummaryDto(
    @SerialName("formatted_distance")
    val formattedDistance: String? = null,
    @SerialName("formatted_duration")
    val formattedDuration: String? = null,
    @SerialName("formatted_traffic_delay")
    val formattedTrafficDelay: String? = null,
    @SerialName("congestion_level")
    val congestionLevel: String? = null
)

@Serializable
data class RouteResultDto(
    val origin: Map<String, Double> = emptyMap(),
    val destination: Map<String, Double> = emptyMap(),
    @SerialName("distance_meters")
    val distanceMeters: Int,
    @SerialName("duration_seconds")
    val durationSeconds: Int,
    @SerialName("traffic_duration_seconds")
    val trafficDurationSeconds: Int,
    @SerialName("route_geometry")
    val routeGeometry: String = "",
    val provider: String = "google",
    val summary: RouteSummaryDto? = null
)
