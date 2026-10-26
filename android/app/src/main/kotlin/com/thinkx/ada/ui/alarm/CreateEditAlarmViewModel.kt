package com.thinkx.ada.ui.alarm

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.thinkx.ada.alarm.scheduler.AlarmScheduler
import com.thinkx.ada.alarm.scheduler.ScheduleResult
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.data.local.entity.DestinationEntity
import com.thinkx.ada.data.preferences.UserPreferencesRepository
import com.thinkx.ada.data.repository.AlarmRepository
import com.thinkx.ada.data.repository.DestinationRepository
import com.thinkx.ada.data.sync.AlarmSyncRepository
import com.thinkx.ada.domain.engine.AdaCalculationEngine
import com.thinkx.ada.domain.model.CalculationInput
import com.thinkx.ada.domain.model.CalculationResult
import com.thinkx.ada.util.DateTimeUtils
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.util.UUID

data class CreateEditAlarmUiState(
    val isEditMode: Boolean = false,
    val alarmId: String? = null,
    val title: String = "",
    val destinationName: String = "",
    val destinationAddress: String = "",
    val destinationLat: Double = 0.0,
    val destinationLng: Double = 0.0,
    val selectedDate: LocalDate = LocalDate.now().plusDays(1),
    val selectedTime: LocalTime = LocalTime.of(9, 0),
    val travelDurationMinutes: Int = 35,
    val preparationDurationMinutes: Int = 30,
    val safetyBufferMinutes: Int = 10,
    val calculationResult: CalculationResult? = null,
    val isWakeTimePast: Boolean = false,
    val isDeadlinePast: Boolean = false,
    val savedDestinations: List<DestinationEntity> = emptyList(),
    val recentDestinations: List<DestinationEntity> = emptyList(),
    val isLoading: Boolean = true,
    val isSaving: Boolean = false,
    val isSaveSuccess: Boolean = false,
    val validationError: String? = null,
    val permissionDenied: Boolean = false
)

class CreateEditAlarmViewModel(
    private val alarmId: String?,
    private val alarmRepository: AlarmRepository,
    private val destinationRepository: DestinationRepository,
    private val userPreferencesRepository: UserPreferencesRepository,
    private val alarmScheduler: AlarmScheduler,
    private val syncRepository: AlarmSyncRepository? = null,
    private val journeyScheduler: com.thinkx.ada.journey.scheduler.JourneyScheduler? = null
) : ViewModel() {

    private val _uiState = MutableStateFlow(CreateEditAlarmUiState(alarmId = alarmId, isEditMode = alarmId != null))
    val uiState: StateFlow<CreateEditAlarmUiState> = _uiState.asStateFlow()

    init {
        loadInitialData()
    }

    private fun loadInitialData() {
        viewModelScope.launch {
            // Load saved and recent destinations
            launch {
                destinationRepository.getSavedDestinations().collect { saved ->
                    _uiState.update { it.copy(savedDestinations = saved) }
                }
            }
            launch {
                destinationRepository.getRecentDestinations(5).collect { recent ->
                    _uiState.update { it.copy(recentDestinations = recent) }
                }
            }

            if (alarmId != null) {
                // Edit mode: fetch existing alarm
                val existingAlarm = alarmRepository.getAlarmById(alarmId)
                if (existingAlarm != null) {
                    val arrivalDateTime = DateTimeUtils.epochMsToLocalDateTime(existingAlarm.requiredArrivalEpochMs)
                    _uiState.update {
                        it.copy(
                            isEditMode = true,
                            title = existingAlarm.title,
                            destinationName = existingAlarm.destinationName,
                            destinationAddress = existingAlarm.destinationAddress,
                            destinationLat = existingAlarm.destinationLat,
                            destinationLng = existingAlarm.destinationLng,
                            selectedDate = arrivalDateTime.toLocalDate(),
                            selectedTime = arrivalDateTime.toLocalTime(),
                            travelDurationMinutes = existingAlarm.travelDurationMinutes,
                            preparationDurationMinutes = existingAlarm.preparationDurationMinutes,
                            safetyBufferMinutes = existingAlarm.safetyBufferMinutes,
                            isLoading = false
                        )
                    }
                    recalculate()
                } else {
                    _uiState.update { it.copy(isLoading = false, validationError = "Alarm not found.") }
                }
            } else {
                // Create mode: load user defaults from DataStore
                val prefs = userPreferencesRepository.userPreferencesFlow.first()
                _uiState.update {
                    it.copy(
                        preparationDurationMinutes = prefs.defaultPreparationMinutes,
                        safetyBufferMinutes = prefs.defaultSafetyBufferMinutes,
                        selectedDate = LocalDate.now().plusDays(1),
                        selectedTime = LocalTime.of(9, 0),
                        isLoading = false
                    )
                }
                recalculate()
            }
        }
    }

    fun onTitleChange(newTitle: String) {
        _uiState.update { it.copy(title = newTitle, validationError = null) }
    }

    fun onDestinationChange(name: String, address: String = "", lat: Double = 0.0, lng: Double = 0.0) {
        _uiState.update {
            it.copy(
                destinationName = name,
                destinationAddress = address,
                destinationLat = lat,
                destinationLng = lng,
                validationError = null
            )
        }
    }

    fun selectDestination(destination: DestinationEntity) {
        _uiState.update {
            it.copy(
                destinationName = destination.name,
                destinationAddress = destination.address,
                destinationLat = destination.latitude,
                destinationLng = destination.longitude,
                validationError = null
            )
        }
    }

    fun onDateChange(newDate: LocalDate) {
        _uiState.update { it.copy(selectedDate = newDate, validationError = null) }
        recalculate()
    }

    fun onTimeChange(newTime: LocalTime) {
        _uiState.update { it.copy(selectedTime = newTime, validationError = null) }
        recalculate()
    }

    fun onTravelDurationChange(minutes: Int) {
        val safeMinutes = minutes.coerceAtLeast(0)
        _uiState.update { it.copy(travelDurationMinutes = safeMinutes, validationError = null) }
        recalculate()
    }

    fun onPreparationDurationChange(minutes: Int) {
        val safeMinutes = minutes.coerceAtLeast(0)
        _uiState.update { it.copy(preparationDurationMinutes = safeMinutes, validationError = null) }
        recalculate()
    }

    fun onSafetyBufferChange(minutes: Int) {
        val safeMinutes = minutes.coerceAtLeast(0)
        _uiState.update { it.copy(safetyBufferMinutes = safeMinutes, validationError = null) }
        recalculate()
    }

    private fun recalculate() {
        val state = _uiState.value
        val requiredArrival = LocalDateTime.of(state.selectedDate, state.selectedTime)

        try {
            val input = CalculationInput(
                requiredArrival = requiredArrival,
                travelDurationMinutes = state.travelDurationMinutes,
                preparationDurationMinutes = state.preparationDurationMinutes,
                safetyBufferMinutes = state.safetyBufferMinutes
            )
            val result = AdaCalculationEngine.calculate(input)
            val isWakePast = AdaCalculationEngine.isWakeTimePast(result.recommendedWakeTime)
            val isDeadlinePast = AdaCalculationEngine.isDeadlinePast(result.requiredArrival)

            _uiState.update {
                it.copy(
                    calculationResult = result,
                    isWakeTimePast = isWakePast,
                    isDeadlinePast = isDeadlinePast
                )
            }
        } catch (e: Exception) {
            _uiState.update { it.copy(calculationResult = null, validationError = e.message) }
        }
    }

    fun saveAlarm() {
        val state = _uiState.value

        if (state.destinationName.isBlank()) {
            _uiState.update { it.copy(validationError = "Please specify a destination.") }
            return
        }

        val calculation = state.calculationResult
        if (calculation == null) {
            _uiState.update { it.copy(validationError = "Unable to compute alarm schedule.") }
            return
        }

        if (state.isDeadlinePast) {
            _uiState.update { it.copy(validationError = "Required arrival deadline is in the past. Choose a future time.") }
            return
        }

        if (state.isWakeTimePast) {
            _uiState.update { it.copy(validationError = "Recommended wake-up time has already passed. Please choose a later arrival time.") }
            return
        }

        _uiState.update { it.copy(isSaving = true, validationError = null) }

        viewModelScope.launch {
            val requiredArrivalEpochMs = DateTimeUtils.localDateTimeToEpochMs(calculation.requiredArrival)
            val plannedArrivalEpochMs = DateTimeUtils.localDateTimeToEpochMs(calculation.plannedArrival)
            val recommendedLeaveEpochMs = DateTimeUtils.localDateTimeToEpochMs(calculation.recommendedLeaveTime)
            val recommendedWakeEpochMs = DateTimeUtils.localDateTimeToEpochMs(calculation.recommendedWakeTime)
            val scheduledAlarmEpochMs = recommendedWakeEpochMs

            val alarmIdToUse = state.alarmId ?: UUID.randomUUID().toString()
            val alarmTitle = if (state.title.isNotBlank()) state.title else "Trip to ${state.destinationName}"

            val alarmEntity = AlarmEntity(
                id = alarmIdToUse,
                title = alarmTitle,
                destinationName = state.destinationName,
                destinationAddress = state.destinationAddress,
                destinationLat = state.destinationLat,
                destinationLng = state.destinationLng,
                requiredArrivalEpochMs = requiredArrivalEpochMs,
                plannedArrivalEpochMs = plannedArrivalEpochMs,
                recommendedLeaveEpochMs = recommendedLeaveEpochMs,
                recommendedWakeEpochMs = recommendedWakeEpochMs,
                scheduledAlarmEpochMs = scheduledAlarmEpochMs,
                scheduledDepartureEpochMs = recommendedLeaveEpochMs,
                trackingLeadMinutes = 15,
                approachingThresholdMeters = 1000,
                arrivalThresholdMeters = 100,
                travelDurationMinutes = state.travelDurationMinutes,
                preparationDurationMinutes = state.preparationDurationMinutes,
                safetyBufferMinutes = state.safetyBufferMinutes,
                isEnabled = true,
                status = AlarmEntity.STATUS_SCHEDULED,
                updatedAtEpochMs = System.currentTimeMillis()
            )

            // Check exact alarm permission
            if (!alarmScheduler.canScheduleExactAlarms()) {
                // Do not silently save as scheduled when permission is missing
                val disabledAlarm = alarmEntity.copy(isEnabled = false, status = AlarmEntity.STATUS_CANCELLED)
                if (state.isEditMode) {
                    alarmRepository.updateAlarm(disabledAlarm)
                } else {
                    alarmRepository.saveAlarm(disabledAlarm)
                }
                _uiState.update {
                    it.copy(
                        isSaving = false,
                        permissionDenied = true,
                        validationError = "Exact alarm permission is missing. Alarm saved as disabled."
                    )
                }
                return@launch
            }

            // Schedule with AlarmManager
            when (val scheduleResult = alarmScheduler.schedule(alarmEntity)) {
                is ScheduleResult.Success -> {
                    // Schedule journey tracking start attempt (e.g. 15 min prior)
                    journeyScheduler?.scheduleTrackingStart(alarmEntity)

                    // Persist to Room
                    if (state.isEditMode) {
                        alarmRepository.updateAlarm(alarmEntity)
                    } else {
                        alarmRepository.saveAlarm(alarmEntity)
                    }

                    // Trigger asynchronous background push (non-blocking)
                    syncRepository?.let { sync ->
                        launch {
                            try {
                                sync.pushLocalAlarm(alarmEntity)
                            } catch (_: Exception) {
                                // Room and native AlarmManager own the schedule
                            }
                        }
                    }

                    // Save destination as recent
                    val recentDest = DestinationEntity(
                        name = state.destinationName,
                        address = state.destinationAddress,
                        latitude = state.destinationLat,
                        longitude = state.destinationLng,
                        isSaved = false,
                        isRecent = true,
                        lastUsedAtEpochMs = System.currentTimeMillis()
                    )
                    destinationRepository.saveDestination(recentDest)

                    _uiState.update { it.copy(isSaving = false, isSaveSuccess = true) }
                }
                is ScheduleResult.PermissionDenied -> {
                    val disabledAlarm = alarmEntity.copy(isEnabled = false, status = AlarmEntity.STATUS_CANCELLED)
                    if (state.isEditMode) {
                        alarmRepository.updateAlarm(disabledAlarm)
                    } else {
                        alarmRepository.saveAlarm(disabledAlarm)
                    }
                    _uiState.update {
                        it.copy(
                            isSaving = false,
                            permissionDenied = true,
                            validationError = "Exact alarm permission denied. Alarm saved as disabled."
                        )
                    }
                }
                is ScheduleResult.PastTime -> {
                    _uiState.update {
                        it.copy(
                            isSaving = false,
                            validationError = "Calculated wake time is in the past ($scheduledAlarmEpochMs <= ${scheduleResult.currentEpochMs})."
                        )
                    }
                }
                is ScheduleResult.Error -> {
                    val disabledAlarm = alarmEntity.copy(isEnabled = false, status = AlarmEntity.STATUS_CANCELLED)
                    if (state.isEditMode) {
                        alarmRepository.updateAlarm(disabledAlarm)
                    } else {
                        alarmRepository.saveAlarm(disabledAlarm)
                    }
                    _uiState.update {
                        it.copy(
                            isSaving = false,
                            validationError = "Scheduling failed: ${scheduleResult.message}"
                        )
                    }
                }
            }
        }
    }

    fun clearValidationError() {
        _uiState.update { it.copy(validationError = null) }
    }

    class Factory(
        private val alarmId: String?,
        private val alarmRepository: AlarmRepository,
        private val destinationRepository: DestinationRepository,
        private val userPreferencesRepository: UserPreferencesRepository,
        private val alarmScheduler: AlarmScheduler,
        private val syncRepository: AlarmSyncRepository? = null,
        private val journeyScheduler: com.thinkx.ada.journey.scheduler.JourneyScheduler? = null
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return CreateEditAlarmViewModel(
                alarmId = alarmId,
                alarmRepository = alarmRepository,
                destinationRepository = destinationRepository,
                userPreferencesRepository = userPreferencesRepository,
                alarmScheduler = alarmScheduler,
                syncRepository = syncRepository,
                journeyScheduler = journeyScheduler
            ) as T
        }
    }
}
