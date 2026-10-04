import uuid
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.models.destination import DestinationType
from app.schemas.base import BaseSchema


class DestinationBase(BaseSchema):
    name: str = Field(
        ..., min_length=1, max_length=150, description="Destination label"
    )
    type: DestinationType = Field(
        default=DestinationType.CUSTOM, description="Category of destination"
    )
    latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Latitude between -90 and 90"
    )
    longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitude between -180 and 180"
    )
    address: str = Field(
        ..., min_length=1, max_length=500, description="Full formatted address"
    )
    place_id: Optional[str] = Field(
        None, max_length=255, description="Provider place identifier"
    )
    provider: Optional[str] = Field(
        None, max_length=50, description="Map provider name (e.g. google, mapbox)"
    )
    is_favorite: bool = Field(default=False, description="Favorite flag")


class DestinationCreate(DestinationBase):
    pass


class DestinationUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    type: Optional[DestinationType] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    address: Optional[str] = Field(None, min_length=1, max_length=500)
    place_id: Optional[str] = Field(None, max_length=255)
    provider: Optional[str] = Field(None, max_length=50)
    is_favorite: Optional[bool] = None


class DestinationResponse(DestinationBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
