# iOS Background Location Tracking & Lifecycle Architecture
## Apple Core Location Requirements, Permissions, Capabilities & State Handling

---

## 1. Core Principles & Truthful Expectations

### The Fundamental Rule:
**iOS does not guarantee arbitrary timer-based background execution.**  
Unlike Android foreground services (which run with a persistent system notification and continuous CPU wake lock), iOS aggressively suspends and terminates background applications to conserve battery life. 

Any claim that an iOS app can execute a JavaScript timer every 60 seconds while backgrounded or locked is false and will fail in production. Continuous, reliable journey tracking on iOS requires adhering strictly to Apple's supported location paradigms.

---

## 2. Required iOS Capabilities & Info.plist Configurations

To qualify for background location updates on iOS, the following entitlements, modes, and privacy keys must be configured:

### 2.1 Background Modes (`UIBackgroundModes`)
In the Xcode project or Expo config plugin (`app.json`):
```json
{
  "expo": {
    "ios": {
      "infoPlist": {
        "UIBackgroundModes": [
          "location",
          "fetch",
          "remote-notification"
        ]
      }
    }
  }
}
```

### 2.2 Location Permission Strings (Privacy Disclosures)
Apple requires clear, specific, user-benefit justifications in `Info.plist`. Vague descriptions result in immediate App Store rejection:

```xml
<!-- Foreground authorization -->
<key>NSLocationWhenInUseUsageDescription</key>
<string>ADA requires your location while using the app to calculate dynamic travel times, detect route progress, and preview upcoming journeys.</string>

<!-- Background authorization (iOS 11+) -->
<key>NSLocationAlwaysAndWhenInUseUsageDescription</key>
<string>ADA uses your background location during an active journey to continuously update your arrival time, detect route delays, and alert you when you are approaching your destination even when the screen is locked.</string>

<!-- Legacy fallback (iOS 10 and earlier) -->
<key>NSLocationAlwaysUsageDescription</key>
<string>ADA uses your location in the background during active journey tracking to deliver timely departure and arrival alerts.</string>
```

---

## 3. Two-Step Permission Strategy (Apple Best Practice)

Apple guidelines mandate requesting location authorization in context rather than blasting the user with permission prompts upon first launch:

```
Step 1: Contextual Education
       │
       ▼
Step 2: Request WhenInUse ("While Using the App")
       │ User can plan journeys and see live map
       ▼
Step 3: When User Arms/Activates Journey Tracking
       │ Display prompt: "Enable background tracking to receive arrival alerts while locked"
       ▼
Step 4: Request Always Authorization ("Change to Always Allow")
```

### Handling Reduced Accuracy / Location Services Disabled:
- If `accuracyAuthorization == CLAccuracyAuthorizationReducedAccuracy`, the system supplies coordinates with a ~1-5 km fuzziness.
- ADA detects this state and displays a **Degraded Tracking** banner:  
  *"Precise location is turned off. ADA cannot detect approaching or arrival status accurately without precise location."*
- Prompts user with a direct deep-link to app settings (`Linking.openSettings()`).

---

## 4. Active Journey Tracking Execution Model

### 4.1 Native Core Location Configuration
When active journey tracking starts:
```swift
// Swift / CoreLocation configuration applied by native layer or expo-location
locationManager.desiredAccuracy = kCLLocationAccuracyBestForNavigation
locationManager.distanceFilter = 25.0 // Update every 25 meters of displacement
locationManager.activityType = .automotiveNavigation
locationManager.allowsBackgroundLocationUpdates = true
locationManager.showsBackgroundLocationIndicator = true // Required blue pill / status bar indicator
locationManager.pausesLocationUpdatesAutomatically = false
locationManager.startUpdatingLocation()
```

### 4.2 In Expo Development Build (`expo-location` + `expo-task-manager`)
The task is registered at root scope before React Native component mount:
```typescript
import * as TaskManager from 'expo-task-manager';
import * as Location from 'expo-location';

export const JOURNEY_TRACKING_TASK = 'ADA_BACKGROUND_JOURNEY_TRACKING';

TaskManager.defineTask(JOURNEY_TRACKING_TASK, async ({ data, error }) => {
  if (error) {
    console.error('Background location task error:', error);
    return;
  }
  if (data) {
    const { locations } = data as { locations: Location.LocationObject[] };
    const latestFix = locations[locations.length - 1];
    
    // Process fix using shared DynamicEtaEngine
    await handleBackgroundLocationFix(latestFix);
  }
});
```

Starting the session:
```typescript
await Location.startLocationUpdatesAsync(JOURNEY_TRACKING_TASK, {
  accuracy: Location.Accuracy.Highest,
  timeInterval: 30000, // Hint to OS (not guaranteed)
  distanceInterval: 25, // Meters
  showsBackgroundLocationIndicator: true,
  pausesUpdatesAutomatically: false,
  foregroundService: { // Ignored on iOS; used if run on RN Android
    notificationTitle: "ADA Journey Active",
    notificationBody: "Tracking your progress to destination"
  }
});
```

---

## 5. Lifecycle, App Suspension & Termination Scenarios

| Scenario | OS Behavior | ADA Handling & Truthful Impact |
| :--- | :--- | :--- |
| **App in Background, Device Locked** | CoreLocation delivers batch location fixes to the background task while tracking is active. | ✅ System wakes app execution briefly to process fix, calculate ETA, and fire local notifications if thresholds met. |
| **App Suspended (Resource Conservation)** | OS suspends app memory. When GPS update occurs matching `distanceFilter`, OS briefly resumes process. | ✅ High-accuracy GPS updates wake the app; ETA is re-evaluated. |
| **User Force-Quits App from App Switcher** | Apple policy treats swipe-to-kill as an **explicit user intent to terminate all activity**. The OS will **NOT** deliver standard location updates. | ⚠️ **Cannot restart standard tracking.** User education banner explains that force-closing the app halts active alarm tracking. |
| **Device Reboot** | App is not running after reboot. | ⚠️ Standard location tracking cannot auto-restart without significant location changes or geofences registered before reboot. |
| **Significant Location Changes (`startMonitoringSignificantLocationChanges`)** | Cell tower / Wi-Fi based coarse location (~500m). Survives device reboot and can relaunch app in background. | 💡 Used as a secondary wake-up safety net if user travels significantly before scheduled departure. |
| **Region Monitoring (`CLCircularRegion`)** | Native geofencing for destination (1,000m approaching boundary, 100m arrival boundary). | 💡 Registered natively as a backup trigger for alerts even if continuous updates are throttled by iOS. |

---

## 6. Battery Optimization & Teardown

- High-accuracy continuous GPS (`kCLLocationAccuracyBestForNavigation`) consumes significant battery power.
- **Teardown Rule**:
  - The moment `isArrivalConfirmed` becomes `true` or the user clicks `Stop Tracking` / `Cancel Journey`, `Location.stopLocationUpdatesAsync(JOURNEY_TRACKING_TASK)` is called immediately.
  - Geofences and active location listeners are torn down.
  - `showsBackgroundLocationIndicator` turns off immediately.
