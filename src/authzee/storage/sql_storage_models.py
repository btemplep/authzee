
import datetime
from typing import Any, Dict, Set

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.types import JSON
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    type_annotation_map = {
        Dict[str, Any]: JSON,
        Any: JSON
    }


class ResourceTypeDB(Base):
    __tablename__ = "resource_type"

    resource_type: Mapped[str] = mapped_column(primary_key=True)


class ResourceActionDB(Base):
    __tablename__ = "resource_action"

    resource_action: Mapped[str] = mapped_column(primary_key=True) # should be a string of the form ResourceAction.MyAction


allow_grant_action_association = Table(
    "allow_grant_action_association",
    Base.metadata,
    Column("allow_grant_storage_id", ForeignKey("allow_grant.storage_id"), primary_key=True),
    Column("resource_action", ForeignKey("resource_action.resource_action"), primary_key=True),
)


class AllowGrantDB(Base):
    __tablename__ = "allow_grant"

    storage_id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    uuid: Mapped[str] = mapped_column(unique=True, nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    resource_type: Mapped[str] = mapped_column(ForeignKey("resource_type.resource_type"), nullable=False)
    actions: Mapped[Set[ResourceActionDB]] = relationship(
        "ResourceActionDB", 
        secondary=allow_grant_action_association, 
        lazy="joined",
        cascade=""
    )
    expression: Mapped[str] = mapped_column(nullable=False)
    context: Mapped[Dict[str, Any]] = mapped_column(nullable=False)
    equality: Mapped[Any] = mapped_column(nullable=False)


deny_grant_action_association = Table(
    "deny_grant_action_association",
    Base.metadata,
    Column("deny_grant_storage_id", ForeignKey("deny_grant.storage_id"), primary_key=True),
    Column("resource_action", ForeignKey("resource_action.resource_action"), primary_key=True),
)


class DenyGrantDB(Base):
    __tablename__ = "deny_grant"

    storage_id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    uuid: Mapped[str] = mapped_column(unique=True, nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    resource_type: Mapped[str] = mapped_column(ForeignKey("resource_type.resource_type"), nullable=False)
    actions: Mapped[Set[ResourceActionDB]] = relationship(
        "ResourceActionDB", 
        secondary=deny_grant_action_association, 
        lazy="joined",
        cascade=""
    )
    expression: Mapped[str] = mapped_column(nullable=False)
    context: Mapped[Dict[str, Any]] = mapped_column(nullable=False)
    equality: Mapped[Any] = mapped_column(nullable=False)


class StorageFlagDB(Base):
    __tablename__ = "storage_flag"

    storage_id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    uuid: Mapped[str] = mapped_column(unique=True, nullable=True)
    is_set: Mapped[bool] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(nullable=False)

