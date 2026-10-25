package com.thinkx.ada

import androidx.navigation3.runtime.NavKey
import kotlinx.serialization.Serializable

@Serializable data object Main : NavKey
@Serializable data class CreateEditAlarm(val alarmId: String? = null) : NavKey
@Serializable data object Destinations : NavKey
@Serializable data object Settings : NavKey

