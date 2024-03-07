
import datetime

from pydantic import BaseModel,  field_validator


class StorageFlag(BaseModel):
    uuid: str
    is_set: bool
    created_at: datetime.datetime


    @field_validator("created_at")
    @classmethod
    def aware_dt(cls, dt: datetime.datetime) -> datetime.datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        
        return dt

