# iOS Release Readiness & Apple App Store Checklist
## Prerequisites, Configuration, Capabilities & Review Compliance

---

## 1. Apple Developer Account & Provisioning

- [ ] Active Apple Developer Program membership ($99/year enrollment).
- [ ] Registered App ID with bundle identifier: `com.thinkx.ada.mobile`.
- [ ] Distribution Certificate (Apple Distribution) generated and imported into Keychain.
- [ ] App Store Provisioning Profile configured for `com.thinkx.ada.mobile`.
- [ ] App record created in App Store Connect with metadata, primary category (Productivity or Navigation).

---

## 2. Capabilities & Entitlements Verification

- [ ] `UIBackgroundModes` configured in `Info.plist`:
  - `location`: For active destination journey tracking and arrival alerts.
  - `fetch`: For periodic background sync if enabled.
  - `remote-notification`: If APNs remote notifications are configured.
- [ ] Explicit justification documented for Apple App Review:
  - *Why does ADA require background location?* ADA is an arrival-deadline smart alarm that recalculates ETA while the user is traveling to their destination and sounds approaching and arrival alerts even when the device is locked in pocket or bag.

---

## 3. Privacy Strings & Disclosures (`Info.plist`)

- [ ] `NSLocationWhenInUseUsageDescription`: Clear explanation of in-app route planning and map preview.
- [ ] `NSLocationAlwaysAndWhenInUseUsageDescription`: Explicit explanation of locked-device journey tracking and arrival alerts.
- [ ] Privacy Nutrition Labels filled in App Store Connect:
  - Location -> Precise Location -> Linked to User / App Functionality.
  - User ID / Contact Info -> Linked to User (Authentication).

---

## 4. Build, Signing & TestFlight Distribution

- [ ] Build created via macOS / Xcode (`eas build --platform ios` or `npx expo run:ios --configuration Release`).
- [ ] Archive created in Xcode Organizer.
- [ ] Validated with Apple Transporter or Xcode Organizer without missing symbol or icon warnings.
- [ ] Uploaded to TestFlight internal test track.
- [ ] Tested on at least one physical iPhone (iOS 17 or 18) for:
  - Permission prompting sequence.
  - Background location indicator visibility.
  - Approaching and arrival notifications when screen is locked.
  - Battery consumption during active tracking.

---

## 5. Explicit Constraints & Non-Actions

- [ ] **NO AUTOMATIC APP STORE PUBLICATION**: Releases to production or App Store submission must never be automated without explicit user review and approval.
- [ ] **NO CREDENTIAL COMMITS**: Never commit `.p8` APNs keys, distribution `.p12` certificates, provisioning profiles, or production passwords to git.
