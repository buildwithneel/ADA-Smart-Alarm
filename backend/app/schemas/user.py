import uuid
from datetime import datetime
from typing import Optional

from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema
from app.schemas.preference import UserPreferenceResponse


class UserBase(BaseSchema):
    email: EmailStr
    name: Optional[str] = Field(None, max_length=100)
    profile_image: Optional[str] = Field(None, max_length=500)
    timezone: str = Field(default="UTC", max_length=50)


class UserUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=100)
    profile_image: Optional[str] = Field(None, max_length=500)
    timezone: Optional[str] = Field(None, max_length=50)


class UserResponse(UserBase):
    id: uuid.UUID
    firebase_uid: str = Field(..., serialization_alias="firebaseUid")
    is_active: bool
    preference: Optional[UserPreferenceResponse] = None
    created_at: datetime
    updated_at: datetime
