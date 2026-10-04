import time
from typing import Any, Dict

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

security_scheme = HTTPBearer()

# Cache public keys to avoid fetching on every API request
_firebase_public_keys: Dict[str, str] = {}
_keys_expire_at: float = 0.0
FIREBASE_KEYS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"


async def _get_firebase_public_keys() -> Dict[str, str]:
    """
    Fetches the current Google public keys used to sign Firebase ID tokens.
    Uses in-memory caching with respect to Cache-Control HTTP headers.
    """
    global _firebase_public_keys, _keys_expire_at
    current_time = time.time()

    if _firebase_public_keys and current_time < _keys_expire_at:
        return _firebase_public_keys

    async with httpx.AsyncClient() as client:
        response = await client.get(FIREBASE_KEYS_URL)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve Firebase public certificates",
            )

        # Parse cache headers to determine lifetime
        cache_control = response.headers.get("cache-control", "")
        max_age = 3600  # Default fallback 1 hour
        for part in cache_control.split(","):
            if "max-age" in part:
                try:
                    max_age = int(part.split("=")[1])
                except (IndexError, ValueError):
                    pass

        _firebase_public_keys = response.json()
        _keys_expire_at = current_time + max_age
        return _firebase_public_keys


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> Dict[str, Any]:
    """
    FastAPI dependency injection provider that extracts, validates, and decodes
    the incoming Firebase Bearer Token. Returns decoded token claims (user context).
    """
    token = credentials.credentials
    project_id = settings.FIREBASE_PROJECT_ID

    if not project_id:
        # If project ID is unconfigured, fallback in dev mode or fail in prod
        if settings.ENVIRONMENT == "development":
            # Return dummy credentials for configuration purposes during local dev
            return {
                "uid": "dev-user-123",
                "email": "dev@example.com",
                "name": "Dev User",
            }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Firebase Project ID is not configured on the backend.",
        )

    try:
        # Get public certificates signature dictionary
        public_keys = await _get_firebase_public_keys()

        # Extract JWT header parameters to check kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid or kid not in public_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature credentials ID (kid).",
            )

        # Decrypt signature using matching Google public key certificate
        public_key = public_keys[kid]

        # Verify JWT payload signature, audience, and issuer
        # Firebase JWT claims spec: https://firebase.google.com/docs/auth/admin/verify-id-tokens
        decoded_claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=project_id,
            issuer=f"https://securetoken.google.com/{project_id}",
            options={"verify_signature": True},
        )
        return decoded_claims

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase access token has expired.",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase access token: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
        )
