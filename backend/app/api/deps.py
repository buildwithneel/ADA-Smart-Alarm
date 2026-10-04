from typing import Generator, Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.errors import ForbiddenException, UnauthorizedException
from app.models.user import User
from app.repositories.alarm_repository import AlarmRepository
from app.repositories.destination_repository import DestinationRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.preference_repository import PreferenceRepository
from app.repositories.push_subscription_repository import PushSubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.services.alarm_recalculation_service import AlarmRecalculationService
from app.services.alarm_service import AlarmService
from app.services.destination_service import DestinationService
from app.services.eta_calculation_service import ETACalculationService
from app.services.firebase_auth_service import FirebaseAuthService
from app.services.geocoding_service import GeocodingService
from app.services.notification_service import NotificationService
from app.services.routing_service import RoutingService
from app.services.user_service import UserService


# Bearer token security scheme with graceful error handling
bearer_scheme = HTTPBearer(auto_error=False)
_firebase_auth_service = FirebaseAuthService()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency injection provider yielding a scoped database session.
    Guarantees the session is closed upon request finalization.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_destination_repository(db: Session = Depends(get_db)) -> DestinationRepository:
    return DestinationRepository(db)


def get_alarm_repository(db: Session = Depends(get_db)) -> AlarmRepository:
    return AlarmRepository(db)


def get_preference_repository(db: Session = Depends(get_db)) -> PreferenceRepository:
    return PreferenceRepository(db)


def get_firebase_auth_service() -> FirebaseAuthService:
    return _firebase_auth_service


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    user_repo: UserRepository = Depends(get_user_repository),
    auth_service: FirebaseAuthService = Depends(get_firebase_auth_service),
) -> User:
    """
    Authoritative server-side Firebase Authentication dependency.
    1. Reads Authorization header and validates Bearer schema.
    2. Verifies cryptographic signature and claims via Firebase Admin SDK.
    3. Extracts verified Firebase UID.
    4. Synchronizes and retrieves the corresponding ADA User entity from PostgreSQL.
    """
    if credentials is None:
        raise UnauthorizedException("Authentication required: Missing Authorization header.")

    if credentials.scheme.lower() != "bearer" or not credentials.credentials.strip():
        raise UnauthorizedException("Malformed Authorization header. Format: 'Bearer <token>'.")

    # Cryptographically verify token
    token = credentials.credentials
    claims = auth_service.verify_id_token(token)

    uid = claims.get("uid")
    if not uid:
        raise UnauthorizedException("Invalid token: Firebase UID is missing.")

    email = claims.get("email") or f"{uid}@ada-dynamic-alarm.com"
    name = claims.get("name")
    profile_image = claims.get("picture")

    # Synchronize or find ADA user in PostgreSQL
    user = user_repo.get_or_create_by_firebase_uid(
        firebase_uid=uid,
        email=email,
        name=name,
        profile_image=profile_image,
    )

    if not user.is_active:
        raise ForbiddenException("User account has been deactivated.")

    return user


def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
    preference_repo: PreferenceRepository = Depends(get_preference_repository),
) -> UserService:
    return UserService(user_repo, preference_repo)


def get_destination_service(
    destination_repo: DestinationRepository = Depends(get_destination_repository),
) -> DestinationService:
    return DestinationService(destination_repo)


_geocoding_service: Optional[GeocodingService] = None
_routing_service: Optional[RoutingService] = None


def get_geocoding_service() -> GeocodingService:
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service


def get_routing_service() -> RoutingService:
    global _routing_service
    if _routing_service is None:
        _routing_service = RoutingService()
    return _routing_service


def get_alarm_service(
    alarm_repo: AlarmRepository = Depends(get_alarm_repository),
    destination_repo: DestinationRepository = Depends(get_destination_repository),
    routing_service: RoutingService = Depends(get_routing_service),
) -> AlarmService:
    return AlarmService(alarm_repo, destination_repo, routing_service)


_eta_calculation_service: Optional[ETACalculationService] = None


def get_eta_calculation_service(
    alarm_repo: AlarmRepository = Depends(get_alarm_repository),
    routing_service: RoutingService = Depends(get_routing_service),
) -> ETACalculationService:
    """Constructs ETACalculationService with a request-scoped AlarmRepository."""
    return ETACalculationService(
        routing_service=routing_service,
        alarm_repo=alarm_repo,
    )


def get_alarm_recalculation_service(
    alarm_repo: AlarmRepository = Depends(get_alarm_repository),
    destination_repo: DestinationRepository = Depends(get_destination_repository),
    routing_service: RoutingService = Depends(get_routing_service),
) -> AlarmRecalculationService:
    """Step 8 dynamic traffic recalculation service dependency."""
    return AlarmRecalculationService(
        alarm_repo=alarm_repo,
        destination_repo=destination_repo,
        routing_service=routing_service,
    )


def get_notification_repository(
    db: Session = Depends(get_db),
) -> NotificationRepository:
    return NotificationRepository(db)


def get_push_subscription_repository(
    db: Session = Depends(get_db),
) -> PushSubscriptionRepository:
    return PushSubscriptionRepository(db)


def get_notification_service(
    notification_repo: NotificationRepository = Depends(get_notification_repository),
    push_repo: PushSubscriptionRepository = Depends(get_push_subscription_repository),
    alarm_repo: AlarmRepository = Depends(get_alarm_repository),
    preference_repo: PreferenceRepository = Depends(get_preference_repository),
) -> NotificationService:
    """Step 9 notification delivery service dependency."""
    return NotificationService(
        notification_repo=notification_repo,
        push_repo=push_repo,
        alarm_repo=alarm_repo,
        preference_repo=preference_repo,
    )


# ----------------------------------------------------------------------
# Step 11: AI Assistant & Personalization Dependencies
# ----------------------------------------------------------------------

from app.repositories.assistant_repository import AssistantRepository
from app.services.alarm_draft_service import AlarmDraftService
from app.services.assistant_conversation_service import AssistantConversationService
from app.services.intent_parser import IntentParser
from app.services.personalization_service import PersonalizationService


def get_assistant_repository(db: Session = Depends(get_db)) -> AssistantRepository:
    return AssistantRepository(db)


def get_intent_parser(
    preference_repo: PreferenceRepository = Depends(get_preference_repository),
    destination_repo: DestinationRepository = Depends(get_destination_repository),
) -> IntentParser:
    return IntentParser(pref_repo=preference_repo, dest_repo=destination_repo)


def get_assistant_conversation_service(
    assistant_repo: AssistantRepository = Depends(get_assistant_repository),
    preference_repo: PreferenceRepository = Depends(get_preference_repository),
) -> AssistantConversationService:
    return AssistantConversationService(assistant_repo, preference_repo)


def get_personalization_service(
    preference_repo: PreferenceRepository = Depends(get_preference_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> PersonalizationService:
    return PersonalizationService(preference_repo, user_repo)


def get_alarm_draft_service(
    assistant_repo: AssistantRepository = Depends(get_assistant_repository),
    destination_repo: DestinationRepository = Depends(get_destination_repository),
    alarm_repo: AlarmRepository = Depends(get_alarm_repository),
    alarm_service: AlarmService = Depends(get_alarm_service),
    geocoding_service: GeocodingService = Depends(get_geocoding_service),
    routing_service: RoutingService = Depends(get_routing_service),
) -> AlarmDraftService:
    return AlarmDraftService(
        assistant_repo=assistant_repo,
        destination_repo=destination_repo,
        alarm_repo=alarm_repo,
        alarm_service=alarm_service,
        geocoding_service=geocoding_service,
        routing_service=routing_service,
    )


