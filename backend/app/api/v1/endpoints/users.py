from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_user_service
from app.models.user import User
from app.schemas.preference import UserPreferenceResponse, UserPreferenceUpdate
from app.schemas.user import UserResponse
from app.services.user_service import UserService

router = APIRouter()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User Profile",
    tags=["Users"],
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Returns the authenticated user's profile and default preferences.
    Uses development placeholder authentication during Step 3.
    """
    return user_service.get_user_profile(current_user.id)


@router.patch(
    "/me/preferences",
    response_model=UserPreferenceResponse,
    summary="Update User Preferences",
    tags=["Users"],
)
def update_user_preferences(
    preferences_in: UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserPreferenceResponse:
    """
    Updates the current user's default travel, timing, theme, and notification preferences.
    """
    return user_service.update_preferences(current_user.id, preferences_in)


@router.get(
    "/me/data",
    summary="Export All User Data (GDPR Portability)",
    tags=["Users"],
)
def export_user_data(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> dict:
    """
    Exports a comprehensive JSON archive containing the authenticated user's
    profile, preferences, saved destinations, and alarms.
    """
    return user_service.export_user_data(current_user.id)


@router.delete(
    "/me",
    summary="Delete User Account (Right to be Forgotten)",
    tags=["Users"],
)
def delete_user_account(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> dict:
    """
    Permanently deletes the authenticated user's account and all associated
    destinations, alarms, schedules, and notifications in accordance with privacy regulations.
    """
    user_service.delete_user_account(current_user.id)
    return {"status": "success", "message": "User account and all associated data have been permanently deleted."}

