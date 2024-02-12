
import asyncio
import json
from typing import Any, Dict, List, Optional, Set, Type, Union

from pydantic import BaseModel
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine

from authzee import exceptions
from authzee.backend_locality import BackendLocality
from authzee.grant import Grant
from authzee.grant_effect import GrantEffect
from authzee.grants_page import GrantsPage
from authzee.raw_grants_page import RawGrantsPage
from authzee.resource_action import ResourceAction
from authzee.resource_authz import ResourceAuthz
from authzee.storage.sql_storage_models import (
    AllowGrantDB, 
    Base, 
    DenyGrantDB, 
    ResourceActionDB, 
    ResourceTypeDB
)
from authzee.storage.storage_backend import StorageBackend


class SQLNextPageRef(BaseModel):

    next_token: int


class SQLStorage(StorageBackend):
    """Store Grants in SQL RDBMS. 

    Parameters
    ----------
    sqlalchemy_async_engine_kwargs : Dict[str, Any]
        SQLAlchemy Async Engine keyword args. 
        https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.create_async_engine

    default_page_size : int, default: 1000
        The default page size when for calls when page size is not specified.
    """


    def __init__(
        self,
        *,
        sqlalchemy_async_engine_kwargs: Dict[str, Any],
        default_page_size: int = 1000
    ):
        locality = BackendLocality.NETWORK
        url = sqlalchemy_async_engine_kwargs['url']
        if url.endswith("://:memory:") is True:
            locality = BackendLocality.MAIN_PROCESS
        
        if (
            url.startswith("sqlite") is True
            or "://localhost" in url
            or "://127.0.0.1" in url
        ):
            locality = BackendLocality.SYSTEM

        super().__init__(
            backend_locality=locality,
            default_page_size=default_page_size,
            parallel_pagination=False,
            sqlalchemy_async_engine_kwargs=sqlalchemy_async_engine_kwargs
        )
        self._sqlalchemy_async_engine_kwargs = sqlalchemy_async_engine_kwargs


    async def initialize(
        self, 
        identity_types: Set[Type[BaseModel]],
        resource_authzs: List[ResourceAuthz]
    ) -> None:
        """Initialize the SQL storage backend. 

        Should only be called by the ``Authzee`` app.

        Parameters
        ----------
        identity_types : Set[Type[BaseModel]]
            Identity types that have been registered with ``Authzee``.
        resource_authzs : List[ResourceAuthz]
            ``ResourceAuthz`` instances that have been registered with ``Authzee``.
        """
        await super().initialize(
            identity_types=identity_types,
            resource_authzs=resource_authzs
        )
        self._resource_type_lookup: Dict[str, Type[BaseModel]] = {
            authz.resource_type.__name__: authz.resource_type for authz in resource_authzs
        }
        self._resource_action_type_lookup: Dict[str, Type[ResourceAction]] = {
            authz.resource_action_type.__name__: authz.resource_action_type.__name__ for authz in resource_authzs
        }
        self._resource_action_lookup: Dict[str, ResourceAction] = {}
        for authz in resource_authzs:
            for action in authz.resource_action_type:
                self._resource_action_lookup[str(action)] = action
        
        self._engine = create_async_engine(**self._sqlalchemy_async_engine_kwargs)
        self._async_sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self._engine, 
            expire_on_commit=False
        )

        # For SQLite, foreign key constraints must be turned on for each connection
        if self._engine.dialect.name == "sqlite":
            @event.listens_for(self._engine.sync_engine, "connect")
            def set_sqlite_fk_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
    

    async def shutdown(self) -> None:
        """Early clean up of storage backend resources.

        Disposes of SQLAlchemy engine.
        """
        await self._engine.dispose()
    

    async def setup(self) -> None:
        """Create the necessary tables for Authzee SQL storage.

        Only run this once per configuration.
        """
        await self.create_tables()

    
    async def create_tables(self) -> None:
        """Create the necessary tables for Authzee SQL storage.
        """
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
 
        async with self._async_sessionmaker() as session:
            for rt_str in self._resource_type_lookup:
                session.add(ResourceTypeDB(resource_type=rt_str))
            
            for ra_str in self._resource_action_lookup:
                session.add(ResourceActionDB(resource_action=ra_str))
            
            await session.commit()
    

    async def add_grant(self, effect: GrantEffect, grant: Grant) -> Grant:
        """Add a grant. 

        Parameters
        ----------
        effect : GrantEffect
            The effect of the grant.
        grant : Grant
            The grant.

        Returns
        -------
        Grant
            The grant that has been added with additional information for the specific backend.
        """
        grant = self._check_uuid(grant=grant, generate_uuid=True)
        async with self._async_sessionmaker() as session:
            resource_action_strs = {str(action) for action in grant.resource_actions}
            result = await session.execute(
                select(ResourceActionDB).where(
                    ResourceActionDB.resource_action.in_(resource_action_strs)
                )
            )
            re_actions = set(result.scalars().fetchall())
            grant_kwargs = {
                "uuid": grant.uuid,
                "name": grant.name,
                "description": grant.description,
                "resource_type": grant.resource_type.__name__,
                "resource_actions": re_actions,
                "jmespath_expression": grant.jmespath_expression,
                "result_match": json.dumps(grant.result_match)
            }
            if effect is GrantEffect.ALLOW:
                db_grant = AllowGrantDB(**grant_kwargs)
            else:
                db_grant = DenyGrantDB(**grant_kwargs)

            session.add(db_grant)
            await session.commit()
            grant.storage_id = db_grant.storage_id
        
        return grant


    async def delete_grant(self, effect: GrantEffect, uuid: str) -> None:
        """Delete a grant.

        Parameters
        ----------
        effect : GrantEffect
            The effect of the grant.
        uuid : str
            UUID of grant to delete.
        """
        async with self._async_sessionmaker() as session:
            if effect is GrantEffect.ALLOW:
                grant_table = AllowGrantDB
            else:
                grant_table = DenyGrantDB
            
            result = await session.execute(
                select(grant_table).where(grant_table.uuid == uuid)
            )
            db_grant = result.scalars().unique().one_or_none()
            if db_grant is None:
                raise exceptions.GrantDoesNotExistError(
                    "{} Grant with UUID: '{}' does not exist.".format(
                        effect.value,
                        uuid
                    )
                )

            await session.delete(db_grant)
            await session.commit()
    

    async def get_raw_grants_page(
        self,
        effect: GrantEffect,
        resource_type: Optional[Type[BaseModel]] = None,
        resource_action: Optional[ResourceAction] = None,
        page_size: Optional[int] = None,
        page_ref: Optional[str] = None
    ) -> RawGrantsPage:
        """Retrieve a page of raw grants matching the filters.

        If ``RawGrantsPage.next_page_ref`` is not ``None`` , there are more grants to retrieve.
        To get the next page, pass ``page_ref=RawGrantsPage.next_page_ref`` .

        Use ``normalize_raw_grants_page`` to convert the ``RawGrantsPage`` to a ``GrantsPage`` model.

        **NOTE** - There is no guarantee of how many grants will be returned if any.

        Parameters
        ----------
        effect : GrantEffect
            The effect of the grant.
        resource_type : Optional[Type[BaseModel]], optional
            Filter by resource type.
            By default no filter is applied.
        resource_action : Optional[ResourceAction], optional
            Filter by `ResourceAction``. 
            By default no filter is applied.
        page_size : Optional[int], optional
            The suggested page size to return. 
            There is no guarantee of how much data will be returned if any.
            The default is set on the storage backend. 
        page_ref : Optional[str], optional
            The reference to the next page that is returned in ``RawGrantsPage``.
            By default this will return the first page.

        Returns
        -------
        RawGrantsPage
            The page of raw grants.
        """
        page_size = self._real_page_size(page_size=page_size)
        async with self._async_sessionmaker() as session:
            if effect is GrantEffect.ALLOW:
                grant_table = AllowGrantDB
            else:
                grant_table = DenyGrantDB

            query = select(grant_table)
            filters = []
            if resource_type is not None:
                filters.append(
                    grant_table.resource_type == resource_type.__name__
                )
            
            if resource_action is not None:
                filters.append(
                    grant_table.resource_actions.any(
                        ResourceActionDB.resource_action == str(resource_action)
                    )
                )

            if page_ref is not None:
                sql_next_page = SQLNextPageRef(**json.loads(page_ref))
                filters.append(
                    grant_table.storage_id > sql_next_page.next_token
                )
            
            query = query.where(*filters)
            query = query.limit(page_size)

            result = await session.execute(query)
            db_grants = result.scalars().unique().all()
            next_page_ref = None
            if len(db_grants) >= page_size:
                next_page_ref = SQLNextPageRef(next_token=db_grants[-1].storage_id).model_dump_json()

        return RawGrantsPage(
            raw_grants=db_grants,
            next_page_ref=next_page_ref
        )


    async def normalize_raw_grants_page(
        self,
        raw_grants_page: RawGrantsPage
    ) -> GrantsPage:
        """Convert a ``RawGrantsPage`` to a ``GrantsPage``.

        Parameters
        ----------
        raw_grants_page : RawGrantsPage
            Raw grants page to convert.

        Returns
        -------
        GrantsPage
            Normalized grants page.
        """
        grants = []
        db_grants: List[Union[AllowGrantDB, DenyGrantDB]] = raw_grants_page.raw_grants
        for db_grant in db_grants:
            grants.append(
                Grant(
                    name=db_grant.name,
                    description=db_grant.description,
                    resource_type=self._resource_type_lookup[db_grant.resource_type],
                    resource_actions={
                        self._resource_action_lookup[action.resource_action] for action in db_grant.resource_actions
                    },
                    jmespath_expression=db_grant.jmespath_expression,
                    result_match=json.loads(db_grant.result_match),
                    storage_id=str(db_grant.storage_id),
                    uuid=db_grant.uuid
                )
            )

        return GrantsPage(
            grants=grants,
            next_page_ref=raw_grants_page.next_page_ref
        )

