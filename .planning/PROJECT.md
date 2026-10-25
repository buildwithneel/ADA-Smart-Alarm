# ADA Smart Alarm — Native Android Application

## Vision & Role
Act as a senior Android architect, Kotlin engineer, mobile UI/UX designer, backend integration engineer, QA engineer and technical project manager to build **ADA Smart Alarm**, a production-oriented native Android application that helps users wake up at the right time to reach a destination by a specified deadline.

## Core Problem ADA Solves
The app helps a user answer five questions:
1. When must I reach my destination?
2. How long will the journey take?
3. When should I leave?
4. When should I wake up?
5. Is my planned arrival still achievable given current conditions?

## Calculation Contract
```
plannedArrivalTime = requiredArrivalTime - safetyBuffer
recommendedLeaveTime = plannedArrivalTime - travelDuration
recommendedWakeTime = recommendedLeaveTime - preparationDuration
```

## Architectural Tenets
1. **Phone Owns the Alarm Schedule:** Local-first architecture using Android `AlarmManager.setAlarmClock()`, Room local database, and BroadcastReceivers. Alarms ring even if offline, airplane mode is on, or the backend is unreachable.
2. **Native Modern Android:** Jetpack Compose, Material 3, Clean Architecture (Domain, Data, UI), ViewModels, Coroutines & Flow, Navigation.
3. **Resilient Backend Integration:** Communicates with existing FastAPI backend via Retrofit, authenticates with Firebase ID tokens, handles offline gracefully without discarding local alarms.
4. **Safety & Policy Conformance:** Safe handling of exact alarm permissions (`SCHEDULE_EXACT_ALARM` / `USE_EXACT_ALARM`), post-notifications permission, full-screen alarm activity, battery optimization awareness, and reboot persistence (`RECEIVE_BOOT_COMPLETED`).
