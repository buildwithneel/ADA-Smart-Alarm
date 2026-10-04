# ADA Security Policy & Architecture (Step 12)

This document details the security posture, defensive controls, and operational policies enforced across the ADA (Adaptive Dynamic Alarm) platform.

---

## 1. Authentication & Identity Management

### Firebase Authentication Integration
- ADA uses Firebase Authentication as the authoritative external identity provider.
- All protected backend API routes require a valid HTTP `Authorization: Bearer <ID_TOKEN>` header.
- The backend verifies the token using the official Firebase Admin SDK (`firebase_admin.auth.verify_id_token`), validating:
  - **Signature:** Cryptographically verified against Google's public key JWKS endpoints.
  - **Audience (`aud`):** Matches `FIREBASE_PROJECT_ID`.
  - **Issuer (`iss`):** `https://securetoken.google.com/<FIREBASE_PROJECT_ID>`.
  - **Expiration (`exp`):** Rejecting expired tokens.

### Production Mock Bypass Prevention
- In development/testing environments, simulated tokens (`test-token:<uid>`) may be used for automated tests.
- **Enforced Security Guard:** In `app/services/firebase_auth_service.py`, mock tokens are **strictly rejected** when `ENVIRONMENT == "production"`. Any attempt to present a test token in production immediately raises an HTTP 401 Unauthorized exception.

---

## 2. Authorization & Object-Level Access Control

ADA enforces strict object-level authorization on every user-owned entity to prevent **Insecure Direct Object Reference (IDOR)** vulnerabilities:

- **Alarms:** Users can only query, update, recalculate, or delete alarms where `alarm.user_id == current_user.id`.
- **Destinations:** Geocoded addresses and saved places are strictly scoped to `destination.user_id == current_user.id`.
- **Drafts & Conversations:** AI assistant sessions and alarm drafts are bounded to the creator's user ID.
- **Calendar Connections:** OAuth credentials and synchronized calendar events are scoped to the connection owner.
- **Notifications & Push Subscriptions:** Delivered alerts and browser endpoints are isolated per user.

*Note: The frontend user ID is never trusted as proof of ownership; the backend resolves ownership exclusively from the verified Firebase ID token.*

---

## 3. Network & Transport Security

- **Enforced HTTPS & HSTS:** In production, HTTP Strict Transport Security (`Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`) is enforced via `SecurityHeadersMiddleware`.
- **Anti-Clickjacking:** `X-Frame-Options: DENY` is sent on all HTTP responses.
- **MIME Sniffing Defense:** `X-Content-Type-Options: nosniff` prevents browser MIME confusion attacks.
- **Cross-Origin Resource Sharing (CORS):** Strict origin whitelisting configured via `CORS_ORIGINS`. Localhost origins are disabled in production.
- **Request Size DOS Defense:** `ContentLengthLimitMiddleware` enforces a maximum payload limit (`MAX_CONTENT_LENGTH_BYTES = 2MB`). Requests exceeding 2MB are rejected with HTTP 413 Payload Too Large before memory allocation.
- **User-Scoped Rate Limiting:** Rate limiting hashes the user's authentication token so users behind shared corporate NAT gateways are not throttled collectively.

---

## 4. Container & Infrastructure Hardening

- **Non-Root Execution:** The production container (`backend/Dockerfile`) creates and switches to a dedicated unprivileged user `ada` (UID 10001, GID 10001).
- **Network Isolation:** PostgreSQL and Redis containers do not expose public host ports in `docker-compose.prod.yml`. They communicate exclusively across the internal `ada-internal` Docker bridge network.
- **Resource Constraints:** CPU and memory limits are enforced in `docker-compose.prod.yml` to prevent rogue tasks from starving host resources.
- **Docker Log Rotation:** Container logging is bounded to `max-size: 20m` and `max-file: 5` to prevent disk exhaustion.

---

## 5. Secrets Management

- **Zero Hardcoded Secrets:** No production passwords, secret keys, or API tokens are checked into source control.
- **Startup Fail-Fast Validation:** `Settings.validate_production_configuration` halts application boot if default development secrets (`SECRET_KEY`, `POSTGRES_PASSWORD`) are detected when `ENVIRONMENT=production`.
- **Log Sanitization:** `StructuredJsonFormatter` automatically regex-redacts authorization tokens (`Bearer [REDACTED]`), API keys, and passwords before logs are emitted.

---

## 6. Privacy & GDPR Compliance

- **Right of Access & Portability (`GET /api/v1/users/me/data`):** Exports the user's complete profile, travel preferences, saved destinations, and alarm histories in a structured machine-readable JSON archive.
- **Right to be Forgotten (`DELETE /api/v1/users/me`):** Permanently deletes the user account and cascades deletion across all alarms, schedules, destinations, calendar credentials, notifications, and assistant conversations.
- **Data Minimization:** No continuous background GPS tracking is performed. Location coordinates are only processed upon explicit alarm creation or recalculation sweeps.
