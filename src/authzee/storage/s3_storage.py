
import asyncio
from contextlib import AsyncExitStack
import datetime
import json
from typing import Dict, List, Optional, Set, Type, Union
from typing_extensions import Any
import uuid

import aioboto3
import botocore.exceptions
from pydantic import BaseModel

from authzee import exceptions
from authzee.backend_locality import BackendLocality
from authzee.grant import Grant
from authzee.grant_effect import GrantEffect
from authzee.grants_page import GrantsPage
from authzee.page_refs_page import PageRefsPage
from authzee.raw_grants_page import RawGrantsPage
from authzee.resource_action import ResourceAction
from authzee.resource_authz import ResourceAuthz
from authzee.storage.storage_backend import StorageBackend
from authzee.storage_flag import StorageFlag


class S3Storage(StorageBackend):
    """

    Stores all data in S3. allows parallel pagination

    bucket-name/prefix/path/
    - /grants/{ALLOW or DENY}/by_uuid/{grant UUID}.json
        - holds actual object data

    - /grants/{ALLOW or DENY}/by_resource_type/{resource type}/{ACTION1}-{ACTION2}-{ACTIONn}/pages/{page num}/{grant UUID}
        - holds empty object but is good for filters
    
    - /grants/{ALLOW or DENY}/by_resource_type/{resource type}/{ACTION1}-{ACTION2}-{ACTIONn}/page_counts/{page num}
        - page nums have a tag that has the approximate count of objects
        - don't need to delete these. Just add when if you need a new page

    - /flags/{flag UUID}.json
        - holds flags


    catches:
    
    - Must call shutdown!

    - aioboto3 session must auto refresh
    """

    def __init__(
        self, 
        *, 
        bucket: str,
        prefix: str,
        aioboto3_session: Optional[aioboto3.Session] = None,
        s3_client_kwargs: Optional[Dict[str, Any]] = None,
        list_objects_kwargs: Optional[Dict[str, Any]] = None,
        get_object_kwargs: Optional[Dict[str, Any]] = None,
        put_object_kwargs: Optional[Dict[str, Any]] = None,
        delete_object_kwargs: Optional[Dict[str, Any]] = None
    ):
        self._bucket = bucket
        self._prefix = prefix
        self._aioboto3_session = aioboto3_session if aioboto3_session is not None else aioboto3.Session()
        self._s3_client_kwargs = s3_client_kwargs if s3_client_kwargs is not None else {}
        self._list_objects_kwargs = list_objects_kwargs if list_objects_kwargs is not None else {}
        self._get_object_kwargs = get_object_kwargs if get_object_kwargs is not None else {}
        self._put_object_kwargs = put_object_kwargs if put_object_kwargs is not None else {}
        self._delete_object_kwargs = delete_object_kwargs if delete_object_kwargs is not None else {}
        super().__init__(
            backend_locality=BackendLocality.NETWORK,
            default_page_size=1000,
            parallel_pagination=True,
            bucket=bucket,
            prefix=prefix,
            aioboto3_session=aioboto3_session,
            s3_client_kwargs=s3_client_kwargs,
            get_object_kwargs=get_object_kwargs,
            put_object_kwargs=put_object_kwargs
        )
        self._aes = AsyncExitStack()


    async def initialize(
        self, 
        identity_types: Set[Type[BaseModel]],
        resource_authzs: List[ResourceAuthz]
    ) -> None:
        """Initialize the storage backend. 

        All creation of connections to external storage should take place here,
        but not creation of resources in the storage.  ie don't create tables.

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
        self._s3_client = await self._aes.enter_async_context(
            self._aioboto3_session.client("s3", **self._s3_client_kwargs)
        )
        
    

    async def shutdown(self) -> None:
        """Clean up of storage backend resources.

        Must be called for the ``S3Storage`` backend!
        """
        await self._aes.aclose()


    async def setup(self) -> None:
        """One time setup for storage backend resources.
        """
        pass

    
    async def teardown(self) -> None:
        """Teardown and delete the results of ``setup()`` .
        """
        pass

    
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

        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            ``StorageBackend`` sub-classes must implement this method.

        bucket-name/prefix/path/

        - /grants/{ALLOW or DENY}/by_uuid/{grant UUID}.json
            - holds actual object data

        - /grants/{ALLOW or DENY}/by_resource_type/{resource type}/{ACTION1}-{ACTION2}-{ACTIONn}/pages/{page num}/{grant UUID}
            - holds empty object but is good for filters
        
        - /grants/{ALLOW or DENY}/deleted/{resource type}/{ACTION1}-{ACTION2}-{ACTIONn}/pages/{page num}/{grant UUID}
            - delete markers where "holes" need to be filled
            - downsides: "holes" exist until a new grant is added
                - If the deletes out way the adds, then there will be a lot of pages that are very short or empty
        
            
        or when we delete one we copy another one from the last page to the first
        Then we put a delete marker on the one in the last page
        then after a certain amount of time we delete the one on the last page?
        That way we always correctly back fill deletes
        downsides: 
            - there are duplicates that can come out when getting a page of matching grants.
            - There is chance that if a task runs longer than the delete time it could skip a grant
                - While this can be made to be statistically very low, it's possible

        another prefix that acts as delete markers for each page
        when deleted put a delete in the other prefix so the hole can be filled
        check if the latest page is less then just add to the latest page and delete the older delete markers

        OBV there are still race conditions here but it's pretty minimal
        check if there are any holes, delete hole obj then start your add
        PLUS race conditions just lead to extra objects in the page, which is better than less in the long run. 
        Where as in the separate tagging structure race conditions to lead to less or more than page size. 

        list objects are ordered by utf-8 binary order
        When listing grants it doesn't matter the order
        Delete doesn't matter the order
        Adding order matters if there are no holes, we would like to only check the first page
        If we do like 8 digits for page num and start backwards, we should always get the "latest" page first when listing objects
        start at page  9999 9999 or 16 digits if that's not enough. 

        Add something to the class for max_pages, default is 16
        """
        grant = self._check_uuid(grant=grant, generate_uuid=True)
        actions = [a.value for a in grant.actions]
        actions.sort()
        filter_key = f"grants/{effect}/by_resource_type/{grant.resource_type}/{"-".join(actions)}/"
        store_task = asyncio.create_task(
            self._s3_client.put_object(
                **{
                    **self._put_object_kwargs,
                    "Body": grant.model_dump_json(),
                    "Bucket": self._bucket,
                    "Key": f"grants/{effect.value}/by_uuid/{grant.uuid}.json"
                }
            )
        )
        # First find the highest page num
        highest_page = 0
        pagey = self._s3_client.get_paginator("list_objects_v2")
        async for page in pagey.paginate(
            **{
                **self._list_objects_kwargs,
                "Bucket": self._bucket, 
                "Delimiter": "/",
                "Prefix": filter_key + "pages/"
            }
        ):
            for o in page['Contents']:
                page_num = int(o['Key'].split("/")[-1])
                if page_num > highest_page:
                    highest_page = page_num
            
        # Then see if there needs to be another page
        # but this is not going to work indefinitely
        # if things are deleted there is no way to go back and fill them
        # you have to just insert new objects in the less than full pages
        # keep tags on the dirs? then we need to maintain page objects. 
        # I don't think that will matter, we don't need to delete
        # them.....
        
        # separate the page "dirs" from the page counts with tags
        filter_key += f"{highest_page}/"
        async for page in pagey.paginate(
            **{
                **self._list_objects_kwargs,
                "Bucket": self._bucket, 
                "Delimiter": "/",
                "Prefix": filter_key
            }
        ):  
            pass



        ref_task = asyncio.create_task(
            self._s3_client.put_object(
                **{
                    **self._put_object_kwargs,
                    "Body": "",
                    "Bucket": self._bucket,
                    "Key": filter_key
                }
            )
        )



    async def delete_grant(self, effect: GrantEffect, uuid: str) -> None:
        """Delete a grant.

        Parameters
        ----------
        effect : GrantEffect
            The effect of the grant.
        uuid : str
            UUID of grant to delete.

        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            ``StorageBackend`` sub-classes *may* implement this method if ``async`` is supported.
        """
        raise exceptions.MethodNotImplementedError()
        

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
            The reference to the next page that is returned in ``RawGrantsPage``, 
            or one of the page references from ``StorageBackend.get_page_ref_page()`` (if parallel pagination is supported.) .
            By default this will return the first page.

        Returns
        -------
        RawGrantsPage
            The page of raw grants.

        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            ``StorageBackend`` sub-classes must implement this method.
        """
        raise exceptions.MethodNotImplementedError()
    

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
        
        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            ``StorageBackend`` sub-classes must implement this method.
        """
        raise exceptions.MethodNotImplementedError()
    

    async def get_page_ref_page(self, page_ref: str) -> PageRefsPage:
        """Get a page of page references for parallel pagination. 

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
        page_ref : str
            Page reference for the next page of page references.

        Returns
        -------
        PageRefsPage
            Page of page references.
        """
        if self.parallel_pagination is True:
            raise exceptions.MethodNotImplementedError(
                (
                    "There is an error in the storage backend!"
                    "This storage backend has marked parallel_pagination as true "
                    "but it has not implemented the required methods!"
                )
            )
        else:
            raise exceptions.ParallelPaginationNotSupported(
                "This storage backend does not support parallel pagination."
            )
    
    
    async def create_flag(self) -> StorageFlag:
        """Create a new shared flag in the storage backend.

        Returns
        -------
        StorageFlag
            New storage flag. 
        """
        new_flag = StorageFlag()
        await self._s3_client.put_object(
            **{
                **self._put_object_kwargs, 
                "Bucket": self._bucket, 
                "Key": f"{self._prefix}/flags/{new_flag.uuid}.json",
                "Body": new_flag.model_dump_json()
            }
        )

        return new_flag


    async def get_flag(self, uuid: str) -> StorageFlag:
        """Retrieve flag by UUID.

        Parameters
        ----------
        uuid : str
            Storage flag UUID.

        Returns
        -------
        StorageFlag
            The storage flag with the given UUID.
        
        Raises
        ------
        authzee.exceptions.StorageFlagNotFoundError
            The storage flag with the given UUID was not found.
        """
        try:
            response = await self._s3_client.get_object(
                **{
                    **self._get_object_kwargs,
                    "Bucket": self._bucket,
                    "Key": f"{self._prefix}/flags/{uuid}.json",
                }
            )
        except botocore.exceptions.ClientError as exc:
            if exc.response[''][''] == "":
                raise exceptions.StorageFlagNotFoundError(
                    f"Could not find storage flag with UUID: {uuid}. {exc}"
                ) from exc
            
            raise
        
        return StorageFlag(**json.loads(await response['Body']))


    async def set_flag(self, uuid: str) -> StorageFlag:
        """Set a flag for a given UUID. 

        Parameters
        ----------
        uuid : str
            Storage flag UUID.

        Returns
        -------
        StorageFlag
            The storage flag with the given UUID and the flag set.
        
        Raises
        ------
        authzee.exceptions.StorageFlagNotFoundError
            The storage flag with the given UUID was not found.
        """
        flag = await self.get_flag(uuid=uuid)
        flag.is_set = True
        await self._s3_client.put_object(
            **{
                **self._put_object_kwargs, 
                "Bucket": self._bucket, 
                "Key": f"{self._prefix}/flags/{uuid}.json",
                "Body": flag.model_dump_json()
            }
        )

        return flag


    async def delete_flag(self, uuid: str) -> None:
        """Delete a storage flag by UUID.

        Parameters
        ----------
        uuid : str
            Storage flag UUID.
        
        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            ``StorageBackend`` sub-classes must implement this method.
        """
        try:
            await self._s3_client.delete_object(
                {
                    **self._delete_object_kwargs,
                    "Bucket": self._bucket,
                    "Key": "{self._prefix}/flags/{uuid}.json"
                }
            )
        except botocore.exceptions.ClientError as exc:
            if exc.response[''][''] == "":
                pass
            
            raise


    async def cleanup_flags(self, earlier_than: datetime.datetime) -> None:
        """Delete zombie storage flags from before a certain point in time.

        Parameters
        ----------
        earlier_than : datetime.datetime
            Delete flags created earlier than this date.
        """
        pagey = self._s3_client.get_paginator("list_objects_v2")
        delete_keys = []
        delete_tasks = []
        async for page in pagey.paginate(Bucket=self._bucket, Prefix=self._prefix + "/"):
            for obj in page['Contents']:
                if obj['LastModified'] <= earlier_than:
                    delete_keys.append(obj['Key'])
            
            if len(delete_keys) >= 1000:
                delete_tasks.append(
                    asyncio.create_task(
                        self._s3_client.delete_objects(
                            {
                                **self._delete_object_kwargs,
                                "Bucket": self._bucket,
                                "Objects": [{"Key": k} for k in delete_keys[:1000]]
                            }
                        )
                    )
                )
                delete_keys = delete_keys[1000:]
        
        if len(delete_keys) > 0:
            delete_tasks.append(
                asyncio.create_task(
                    self._s3_client.delete_objects(
                        {
                            **self._delete_object_kwargs,
                            "Bucket": self._bucket,
                            "Objects": [{"Key": k} for k in delete_keys]
                        }
                    )
                )
            )
        
        await asyncio.gather(*delete_tasks)
