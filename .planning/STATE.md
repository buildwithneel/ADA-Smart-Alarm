# Project Memory & Current State

## Current Position
- **Active Milestone**: Milestone 1 (Foundation & Toolchain) transitioning to Milestone 2 (Domain Engine & Unit Tests).
- **Current Focus**: Verifying Gradle build pipeline for Android and implementing pure Kotlin domain calculations.

## Decision Log
- **D-01 (Architecture)**: Android app lives in `android/` directory in repository root, keeping backend and web frontend intact.
- **D-02 (SDK Targets)**: Android SDK Platform 35 and Build-Tools 35.0.0 installed via Google Android CLI; minSdk=26 (Android 8.0 Oreo), targetSdk=35 (Android 15).
- **D-03 (Alarm Engine)**: Uses `AlarmManager.setAlarmClock()` exclusively for reliable user-facing alarm execution.
- **D-04 (Offline First)**: Room local SQLite database owns the canonical device alarm schedule; backend network failures do not prevent local scheduling.
- **D-05 (Authentication)**: Firebase Authentication Android SDK for production; supports development test tokens matching backend `FirebaseAuthService` mock capabilities.
