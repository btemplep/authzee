
import datetime
from typing_extensions import Annotated
import uuid

from pydantic import BaseModel, field_validator, Field


class StorageFlag(BaseModel):
    uuid: Annotated[str, Field(default_factory=lambda: str(uuid.uuid4()))]
    is_set: bool = False
    created_at: Annotated[
        datetime.datetime, 
        Field(
            default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc)
        )
    ]


    @field_validator("created_at")
    @classmethod
    def aware_dt(cls, dt: datetime.datetime) -> datetime.datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        
        return dt

