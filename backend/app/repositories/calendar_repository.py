from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.calendar import CalendarConnection, CalendarEvent


class CalendarRepository:
    """
    SQLAlchemy repository for CalendarConnection and CalendarEvent entities.
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Connection Management
    # ------------------------------------------------------------------

    def get_connection(self, connection_id: uuid.UUID) -> Optional[CalendarConnection]:
        stmt = select(CalendarConnection).where(CalendarConnection.id == connection_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_connection_by_user(
        self, user_id: uuid.UUID, provider: str = "google"
    ) -> Optional[CalendarConnection]:
        stmt = select(CalendarConnection).where(
            and_(
                CalendarConnection.user_id == user_id,
                CalendarConnection.provider == provider,
                CalendarConnection.is_active == True,  # noqa: E712
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_user_connections(self, user_id: uuid.UUID) -> List[CalendarConnection]:
        stmt = select(CalendarConnection).where(CalendarConnection.user_id == user_id)
        return list(self.db.execute(stmt).scalars().all())

    def list_all_active_connections(self) -> List[CalendarConnection]:
        stmt = select(CalendarConnection).where(CalendarConnection.is_active == True)  # noqa: E712
        return list(self.db.execute(stmt).scalars().all())

    def create_connection(
        self,
        user_id: uuid.UUID,
        account_email: str,
        encrypted_access_token: str,
        encrypted_refresh_token: Optional[str],
        token_expires_at: Optional[datetime],
        provider: str = "google",
        scopes: str = "https://www.googleapis.com/auth/calendar.events.readonly",
    ) -> CalendarConnection:
        conn = CalendarConnection(
            user_id=user_id,
            provider=provider,
            account_email=account_email,
            encrypted_access_token=encrypted_access_token,
            encrypted_refresh_token=encrypted_refresh_token,
            token_expires_at=token_expires_at,
            scopes=scopes,
            is_active=True,
            sync_status="idle",
        )
        self.db.add(conn)
        self.db.commit()
        self.db.refresh(conn)
        return conn

    def update_connection(self, conn: CalendarConnection) -> CalendarConnection:
        self.db.commit()
        self.db.refresh(conn)
        return conn

    def delete_connection(self, connection_id: uuid.UUID) -> bool:
        conn = self.get_connection(connection_id)
        if not conn:
            return False
        self.db.delete(conn)
        self.db.commit()
        return True

    # ------------------------------------------------------------------
    # Event Management
    # ------------------------------------------------------------------

    def get_event(self, event_id: uuid.UUID) -> Optional[CalendarEvent]:
        stmt = select(CalendarEvent).where(CalendarEvent.id == event_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_event_by_external_id(
        self, connection_id: uuid.UUID, external_event_id: str
    ) -> Optional[CalendarEvent]:
        stmt = select(CalendarEvent).where(
            and_(
                CalendarEvent.connection_id == connection_id,
                CalendarEvent.external_event_id == external_event_id,
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_event_by_alarm(self, alarm_id: uuid.UUID) -> Optional[CalendarEvent]:
        stmt = select(CalendarEvent).where(CalendarEvent.alarm_id == alarm_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_upcoming_events(
        self, user_id: uuid.UUID, time_min: Optional[datetime] = None
    ) -> List[CalendarEvent]:
        cutoff = time_min or datetime.now(timezone.utc)
        stmt = (
            select(CalendarEvent)
            .where(
                and_(
                    CalendarEvent.user_id == user_id,
                    CalendarEvent.start_time >= cutoff,
                )
            )
            .order_by(CalendarEvent.start_time.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def upsert_event(
        self,
        connection_id: uuid.UUID,
        user_id: uuid.UUID,
        external_event_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        timezone_str: str,
        location: Optional[str] = None,
        resolved_latitude: Optional[float] = None,
        resolved_longitude: Optional[float] = None,
        all_day: bool = False,
        status: str = "confirmed",
        source_provider: str = "google",
        event_link: Optional[str] = None,
    ) -> tuple[CalendarEvent, bool]:
        """
        Upserts calendar event. Returns tuple: (event, was_created: bool).
        """
        existing = self.get_event_by_external_id(connection_id, external_event_id)
        now = datetime.now(timezone.utc)

        if existing:
            existing.title = title
            existing.start_time = start_time
            existing.end_time = end_time
            existing.timezone = timezone_str
            existing.location = location
            if resolved_latitude is not None:
                existing.resolved_latitude = resolved_latitude
            if resolved_longitude is not None:
                existing.resolved_longitude = resolved_longitude
            existing.all_day = all_day
            existing.status = status
            existing.event_link = event_link
            existing.last_synced_at = now
            self.db.commit()
            self.db.refresh(existing)
            return existing, False
        else:
            new_event = CalendarEvent(
                connection_id=connection_id,
                user_id=user_id,
                external_event_id=external_event_id,
                title=title,
                start_time=start_time,
                end_time=end_time,
                timezone=timezone_str,
                location=location,
                resolved_latitude=resolved_latitude,
                resolved_longitude=resolved_longitude,
                all_day=all_day,
                status=status,
                source_provider=source_provider,
                last_synced_at=now,
                event_link=event_link,
            )
            self.db.add(new_event)
            self.db.commit()
            self.db.refresh(new_event)
            return new_event, True

    def link_alarm_to_event(
        self, event_id: uuid.UUID, alarm_id: uuid.UUID
    ) -> Optional[CalendarEvent]:
        event = self.get_event(event_id)
        if event:
            event.alarm_id = alarm_id
            self.db.commit()
            self.db.refresh(event)
        return event
