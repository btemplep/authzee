__all__ = [
    "S3Storage"
]
import asyncio
import base64
from contextlib import AsyncExitStack
import datetime
import json
from typing import Dict, List, Optional, Set, Type, Union
from typing_extensions import Any

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


class S3PageRef(BaseModel):
        prefix: str
        s3_next_token: Union[str, None]


class S3Storage(StorageBackend):
    """AWS S3 storage backend.

    Store grants and flags as objects in an S3 bucket.

    **NOTE** - Must call ``shutdown()`` on exit.

    Parameters
    ----------
    bucket : str
        Bucket for storage.
    prefix : str
        Prefix for objects in the bucket.
    aioboto3_session : Optional[aioboto3.Session], optional
        aioboto3 ``Session`` object to create clients with.
        By default one will be created with no arguments.
    s3_client_kwargs : Optional[Dict[str, Any]], optional
        Additional kwargs for when creating the S3 client, by default None
    list_objects_kwargs : Optional[Dict[str, Any]], optional
        Additional kwargs for calling ``list_objects_v2`` , by default None
    get_object_kwargs : Optional[Dict[str, Any]], optional
        Additional kwargs for calling ``get_object`` , by default None
    put_object_kwargs : Optional[Dict[str, Any]], optional
        Additional kwargs for calling ``put_object`` , by default None
    delete_object_kwargs : Optional[Dict[str, Any]], optional
        Additional kwargs for calling ``delete_object``, by default None
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
        self._prefix = prefix if prefix[-1] != "/" else prefix[:-1]
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
        self._action_to_rt: Dict[ResourceAction, BaseModel] = {}
        self._name_to_rt: Dict[str, BaseModel] = {}
        self._rt_to_action: Dict[BaseModel, ResourceAction] = {}


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
        for authz in self._resource_authzs:
            for action in authz.resource_action_type:
                self._action_to_rt[action] = authz.resource_type
                self._name_to_rt[authz.resource_type.__name__] = authz.resource_type
                self._rt_to_action[authz.resource_type] = authz.resource_action_type
        
    
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
        """
        grant = self._check_uuid(grant=grant, generate_uuid=True)
        actions = [a.value for a in grant.actions]
        actions.sort()
        acts = "-".join(actions)
        filter_key = f"{self._prefix}/grants/{effect}/by_resource_type/{grant.resource_type.__name__}/{acts}"
        # first put the seed object before filters to avoid race conditions
        # where a filter list is ran but the actual seed object doesn't exist yet.
        await self._s3_client.put_object(
            **{
                **self._put_object_kwargs,
                "Body": grant.model_dump_json(),
                "Bucket": self._bucket,
                "Key": f"{self._prefix}/grants/{effect}/by_uuid/{grant.uuid}.json"
            }
        )
         # Then put filter object
        await self._s3_client.put_object(
            **{
                **self._put_object_kwargs,
                "Body": "",
                "Bucket": self._bucket,
                "Key": f"{filter_key}/{grant.uuid}"
            }
        )

        return grant


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
        key = f"{self._prefix}/grants/{effect}/by_uuid/{uuid}.json"
        grant = await self._get_grant(effect=effect, uuid=uuid)
        actions = [a.value for a in grant.actions]
        actions.sort()
        acts = "-".join(actions)
        filter_key = f"{self._prefix}/grants/{effect}/by_resource_type/{grant.resource_type.__name__}/{acts}"
        # When deleting a grant there is a race condition either way that is handled when normalized
        store_task = asyncio.create_task(
            self._s3_client.delete_object(
                **{
                    **self._delete_object_kwargs,
                    "Bucket": self._bucket,
                    "Key": key
                }
            )
        )
        lookup_task = asyncio.create_task(
            self._s3_client.delete_object(
                **{
                    **self._delete_object_kwargs,
                    "Bucket": self._bucket,
                    "Key": f"{filter_key}/{uuid}"
                }
            )
        )
        await asyncio.gather(store_task, lookup_task)

        return grant


    def _ref_to_model(self, page_ref: str) -> S3PageRef:
        return S3PageRef.model_validate_json(
            base64.b64decode(
                page_ref
            ).decode("ascii")
        )


    def _model_to_ref(self, s3_ref: S3PageRef) -> str:
        return base64.b64encode(
            s3_ref.model_dump_json().encode("ascii")
        ).decode("ascii")
    

    async def _get_grant(self, effect: GrantEffect, uuid: str) -> Grant:
        grant_ob = await self._s3_client.get_object(
            **self._get_object_kwargs,
            Bucket=self._bucket,
            Key=f"{self._prefix}/grants/{effect}/by_uuid/{uuid}.json"
        )
        body = await grant_ob['Body'].read()
        body = json.loads(body)
        body['resource_type'] = self._name_to_rt[body['resource_type']]
        action_type = self._rt_to_action[body['resource_type']]
        body['actions'] = set([action_type[a] for a in body['actions']])

        return Grant(**body)


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
        prefix = f"{self._prefix}/grants/{effect}/"
        s3_ref = None
        list_kwargs = {**self._list_objects_kwargs}
        if page_size is not None:
            list_kwargs['MaxKeys'] = page_size

        if page_ref is not None:
            s3_ref = self._ref_to_model(page_ref=page_ref)

        if resource_action is None:
            # if no filters list from the lookup table
            if resource_type is None:
                prefix += "by_uuid/"
            # filter by resource type only
            else:
                prefix += f"by_resource_type/{resource_type.__name__}/"

            list_kwargs = {
                **list_kwargs,
                "Bucket": self._bucket,
                "Prefix": prefix
            }
            if s3_ref is not None:
                list_kwargs['ContinuationToken'] = s3_ref.s3_next_token

            obj_page = await self._s3_client.list_objects_v2(
                **list_kwargs
            )
            obj_page['authzee_effect'] = effect.value
            cont_token = obj_page.get("NextContinuationToken", None)
            if cont_token is None:
                next_page_ref = None
            else:
                next_page_ref = self._model_to_ref(
                    S3PageRef(
                        prefix=prefix,
                        s3_next_token=cont_token
                    )
                )

            return RawGrantsPage(
                raw_grants=obj_page,
                next_page_ref=next_page_ref
            )

        # else resource action is not None, therefore resource type is not None
        # since actions only map to one resource type
        else:
            if resource_type is None:
                resource_type = self._action_to_rt[resource_action]

            prefix += f"by_resource_type/{resource_type.__name__}/"
            # if we have another page on the current prefix then get that
            if s3_ref is not None and s3_ref.s3_next_token is not None:
                obj_page = await self._s3_client.list_objects_v2(
                    **{
                        **list_kwargs,
                        "Bucket": self._bucket,
                        "Prefix": s3_ref.prefix,
                        "ContinuationToken": s3_ref.s3_next_token
                    }
                )
                obj_page['authzee_effect'] = effect.value
                next_s3_ref = S3PageRef(
                    prefix=s3_ref.prefix,
                    s3_next_token=obj_page.get("NextContinuationToken", None)
                )

                return RawGrantsPage(
                    raw_grants=obj_page,
                    next_page_ref=self._model_to_ref(s3_ref=next_s3_ref)
                )
            # else no ref was passed or we need a new prefix/token
            else:
                prefix_list_kwargs = {
                    **self._list_objects_kwargs,
                    "Bucket": self._bucket,
                    "Prefix": prefix,
                    "Delimiter": "/"
                }
                # need a new prefix
                if s3_ref is not None and s3_ref.s3_next_token is None:
                    prefix_list_kwargs['StartAfter'] = s3_ref.prefix 

                ap_pager = self._s3_client.get_paginator("list_objects_v2")
                async for page in ap_pager.paginate(**prefix_list_kwargs):
                    if "CommonPrefixes" not in page:
                        continue

                    for p in page['CommonPrefixes']:
                        cp: str = p['Prefix']
                        action_strs = cp.split("/")[-2].split("-")
                        if resource_action.value in action_strs:
                            obj_page = await self._s3_client.list_objects_v2(
                                **{
                                    **list_kwargs,
                                    "Bucket": self._bucket,
                                    "Prefix": cp
                                }
                            )
                            obj_page['authzee_effect'] = effect.value
                            next_s3_ref = S3PageRef(
                                prefix=cp,
                                s3_next_token=obj_page.get("NextContinuationToken", None)
                            )

                            return RawGrantsPage(
                                raw_grants=obj_page,
                                next_page_ref=self._model_to_ref(s3_ref=next_s3_ref)
                            )
            
        # If any case is not caught we have nothing left to return
        return RawGrantsPage(
            raw_grants=None,
            next_page_ref=None
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
        
        Raises
        ------
        authzee.exceptions.MethodNotImplementedError
            ``StorageBackend`` sub-classes must implement this method.
        """
        if (
            raw_grants_page.raw_grants is None
            or "Contents" not in raw_grants_page.raw_grants
        ):
            return GrantsPage(grants=[], next_page_ref=raw_grants_page.next_page_ref)
        
        effect = GrantEffect[raw_grants_page.raw_grants['authzee_effect']]
        tasks = []
        for ob in raw_grants_page.raw_grants['Contents']:
            tasks.append(
                self._get_grant(
                    effect=effect,
                    # split key to get the UUID, split again to remove file extension if present.
                    uuid=ob['Key'].split("/")[-1].split(".")[0] 
                )
            )

        grants: List[Grant] = await asyncio.gather(*tasks, return_exceptions=True)
        # There is a race condition when deleting grants.
        # If the grant is listed and then deleted before normalizing we need to handle that
        # by just removing it from the list and re-raise any other exception
        keep_grants: List[Grant] = []
        for grant in grants:
            if type(grant) is Grant:
                keep_grants.append(grant)

            elif type(grant) is botocore.exceptions.ClientError:
                # if error is about the object not existing we pass or else re-raise
                if grant.response["Error"]["Code"] != "NoSuchKey":
                    raise grant

            else:
                raise grant

        return GrantsPage(
            grants=keep_grants,
            next_page_ref=raw_grants_page.next_page_ref
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
                    "Key": f"{self._prefix}/flags/{uuid}.json"
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
