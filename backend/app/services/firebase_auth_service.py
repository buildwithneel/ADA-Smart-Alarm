import json
import logging
import os
from typing import Any, Dict

import firebase_admin
from firebase_admin import auth, credentials

from app.core.config import settings
from app.core.errors import UnauthorizedException
from app.services.base import BaseService

logger = logging.getLogger("ada.auth")


class FirebaseAuthService(BaseService):
    """
    Server-side Firebase Authentication service utilizing the official Firebase Admin SDK.
    Responsible for cryptographically verifying ID tokens, extracting UIDs, and parsing claims.
    """

    def __init__(self) -> None:
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        """Initializes Firebase Admin SDK application singleton if not already initialized."""
        if not firebase_admin._apps:
            cred_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", None)
            project_id = getattr(settings, "FIREBASE_PROJECT_ID", None)

            # Check if emulator is configured
            emulator_host = os.environ.get("FIREBASE_AUTH_EMULATOR_HOST")
            if emulator_host:
                logger.info(f"Connecting to Firebase Auth Emulator at {emulator_host}")

            try:
                if cred_path and os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred, {"projectId": project_id} if project_id else None)
                    logger.info("Firebase Admin initialized using service account certificate file.")
                elif project_id:
                    firebase_admin.initialize_app(options={"projectId": project_id})
                    logger.info("Firebase Admin initialized using Google Default Credentials.")
                else:
                    # Initialize default app (supports local emulator and gcloud defaults)
                    firebase_admin.initialize_app()
                    logger.info("Firebase Admin initialized with default configuration.")
            except Exception as e:
                logger.warning(
                    f"Firebase Admin SDK initialization deferred or running in test mode: {e}"
                )

    def verify_id_token(self, token: str) -> Dict[str, Any]:
        """
        Cryptographically verifies the Firebase ID token and extracts claims.
        Guarantees server-side verification and returns UID, email, and profile claims.
        """
        if not token or not token.strip():
            raise UnauthorizedException("Authentication token is required.")

        # Support test tokens during isolated unit testing and local emulator testing
        # CRITICAL SECURITY: Never honor mock/test tokens in production mode
        if settings.ENVIRONMENT != "production":
            if os.environ.get("ENVIRONMENT") == "testing" or token.startswith("test-token:"):
                return self._verify_mock_test_token(token)

        try:
            # Official Firebase Admin SDK verification
            decoded_token = auth.verify_id_token(token, check_revoked=False)
            uid = decoded_token.get("uid")
            if not uid:
                raise UnauthorizedException("Invalid token: Missing UID claim.")
            return decoded_token
        except auth.ExpiredIdTokenError:
            raise UnauthorizedException("Authentication token has expired.")
        except (auth.InvalidIdTokenError, auth.RevokedIdTokenError, ValueError) as e:
            logger.warning(f"Firebase token rejected: {e}")
            raise UnauthorizedException("Invalid authentication token.")
        except Exception as e:
            logger.error(f"Unexpected token verification error: {e}")
            raise UnauthorizedException("Unable to verify authentication token.")

    def _verify_mock_test_token(self, token: str) -> Dict[str, Any]:
        """
        Parses deterministic test tokens for automated test isolation without
        requiring production Firebase cloud credentials.
        Format: 'test-token:<uid>[:<email>[:<name>]]' or JSON payload.
        """
        if token == "expired-token":
            raise UnauthorizedException("Authentication token has expired.")
        if token == "invalid-token" or token == "malformed":
            raise UnauthorizedException("Invalid authentication token.")

        if token.startswith("test-token:"):
            parts = token.split(":")
            uid = parts[1] if len(parts) > 1 else "test-uid-default"
            email = parts[2] if len(parts) > 2 else f"{uid}@example.com"
            name = parts[3] if len(parts) > 3 else "Test User"
            return {
                "uid": uid,
                "email": email,
                "name": name,
                "picture": None,
                "auth_time": 1700000000,
            }

        try:
            claims = json.loads(token)
            if "uid" in claims:
                return claims
        except Exception:
            pass

        return {
            "uid": "test-user-firebase-uid-001",
            "email": "dev@ada-alarm.com",
            "name": "ADA Developer",
            "picture": None,
        }
