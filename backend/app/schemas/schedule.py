from datetime import date
from typing import Optional

from pydantic import Field, field_validator

from app.models.schedule import ScheduleType
from app.schemas.base import BaseSchema

VALID_DAYS = {"MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"}


class AlarmScheduleSchema(BaseSchema):
    schedule_type: ScheduleType = Field(
        default=ScheduleType.DAILY, description="Recurrence type"
    )
    repeat_days: Optional[str] = Field(
        None,
        description="Comma-separated repeat days for custom schedule (e.g. MON,TUE,WED)",
    )
    specific_date: Optional[date] = Field(
        None,
        description="Target calendar date for one-time alarms",
    )

    @field_validator("repeat_days")
    @classmethod
    def validate_repeat_days(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None
        days = [d.strip().upper() for d in v.split(",") if d.strip()]
        for day in days:
            if day not in VALID_DAYS:
                raise ValueError(
                    f"Invalid day '{day}'. Allowed days are: {', '.join(sorted(VALID_DAYS))}"
                )
        return ",".join(days)
