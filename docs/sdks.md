# Authzee SDKs

Authzee aims to offer SDKs in many languages with similar interfaces. 
Making it easier to switch languages by standardizing SDK patterns, while leaving room for language specific functionality and syntax. 

they aim to offer a flexible and scalable general purpose interface, but they are opinionated in their APIs.  
if this doesn't fit your use case you are free to create your own and 

## Languages

| Language | Code Repo | Package - Repo | Maintained | SDK Standard | Official |
|---|---|---|---|---|---|
| python | [authzee-py](https://github.com/btemplep/authzee-py) | [authzee](https://pypi.org/project/authzee/) - pypi.org | ✅ | ✅ | ✅ |


## SDK API Standard

The following sections outline Authzee SDK standards.  Note that python naming conventions are used but the actual SDKs should change this based on the convention of the language. 

The suggested architecture of SDKs is to have one main object or struct `Authzee`.  
Under this object, identity definitions, resource definitions, and the jmespath search function are static.
The Authzee object will accept a compute engine and a storage engine.  
The compute engine will be used to provide the compute resources for running workflows, 
and the storage engine will be used to store and retrieve grants and other compute state objects. 



## Authzee Object or Struct

The `Authzee` object or struct should take these arguments when created:
- Identity defs
- Resource defs
- JMESPath search function
- Compute Engine type and arguments
- Storage Engine type and arguments

If the language supports async, there should also be an async version, `AuthzeeAsync`. 

These are the methods of functions for the Authzee object.  For AuthzeeAsync, they should all be async functions.

- `start() -> null`
    - start up Authzee app 
    -Initialize runtime resources
- `shutdown() -> null`
    - shutdown authzee app
    - clean up runtime resources
- `setup() -> null` 
    - Construct backend resources for compute and storage
    - one time setup 
- `teardown() -> null` 
    - tear down backend resources 
    - destructive - may lose all storage and compute etc.
- `list_grants(effect: str, action: str) -> <Grants Iterator>` 
    - auto paginate list grants
    - Maybe also by tags?
- `get_grants_page(effect: str, action: str, page_token: str) -> <Grants Page>` 
    - get a page of grants
    - Maybe also by tags?
- `get_grant_page_refs_page(effect: str, action: str, page_token: str) -> Grant Page Refs Page` 
    - get a page of grant page references for parallel pagination
    - For some storage backends this may not be possible
    - Maybe also by tags?
- `get_grant(grant_uuid: UUID) -> Grant`
    - Get a grant by UUID
- `add_grant(new_grant: NewGrant) -> Grant` 
    - add a new grant
- `delete_grant(grant_uuid: UUID) -> null` 
    - delete a grant
- `evaluate(request: obj, parallel_paging: bool) -> <Evaluate Iterator>` 
    - Run evaluate workflow with auto pagination
    - parallel pagination will send a whole page of grant page refs to be computed at a time which can help to cut down on latency between pages.
- `evaluate_page(request: obj, page_token) -> <Evaluate Page>` 
    - Run evaluate workflow for a single page of results
- `authorize(request: obj) -> <Authorization Result>` 
    - run authorize workflow


## Compute Engine Objects or Structs

Compute engines provide a standard API for running workflows on compute.
They have direct access to the storage engine and use it to retrieve grants. 
They may also use the storage engine ato create and retrieve latches that help with compute state.  Especially for compute that is spread across multiple systems.

Compute Engines should take these arguments when created:
- Identity definitions
- Resource Definitions
- JMESPath function pointer
- Storage engine type and arguments
- Other engine specific arguments as needed

Compute engines need to declare these public constant class vars when they are created, or have getters:
- locality - Compute [Engine Locality](#engine-locality) 
- parallel_paging_supported - if the compute engines supports processing grants with parallel paging

Compute engines objects or structs should implement these methods:

- `start() -> null`
    - start up compute engine
    - run before use
- `shutdown() -> null`
    - shutdown compute engine
    - clean up runtime resources
- `setup() -> null` 
    - Construct backend resources for compute 
    - one time setup 
- `teardown() -> null` 
    - tear down backend resources 
    - destructive - may lose all long lasting compute resources
- `evaluate_page(request: obj, page_token) -> <Evaluate Page>`
    - Run evaluate workflow on a page of grants
- `evaluate(request: obj, parallel_paging: bool) -> <Evaluate Iterator>` 
    - Run evaluate workflow with auto pagination
    - parallel pagination will send a whole page of grant page refs to be computed at a time which can help to cut down on latency between pages.
- `authorize(request: obj) -> <Authorization Result>` 
    - run authorize workflow


## Storage Engine Objects or Structs

Storage engine provide a standard API for storing and retrieving grants and compute latches. 

Storage Engines should take these arguments when created:
- Identity definitions
- Resource Definitions
- Other engine specific arguments as needed


Storage engines need to declare these public constant class vars when they are created, or have getters:
- locality - Storage [Engine Locality](#engine-locality) 
- parallel_paging_supported - if the storage engines supports parallel paging (returning a page of grant page references). 

Storage engine objects or structs should implement these methods:
 `start() -> null`
    - start up storage engine
    - run before use
- `shutdown() -> null`
    - shutdown storage engine
    - clean up runtime resources
- `setup() -> null` 
    - Construct backend resources for storage 
    - one time setup 
- `teardown() -> null` 
    - tear down backend resources 
    - destructive - may lose all long lasting compute resources
- `list_grants(effect: str, action: str) -> <Grants Iterator>` 
    - auto paginate list grants
- `get_grants_page(effect: str, action: str, page_token: str) -> <Grants Page>` 
    - get a page of grants
- `get_grant_page_refs_page(effect: str, action: str, page_token: str) -> Grant Page Refs Page` 
    - get a page of grant page references for parallel pagination
    - **OPTIONAL** - For some storage backends this may not be possible.  Set `parallel_paging_supported` accordingly.
- `get_grant(grant_uuid: UUID) -> Grant`
    - Get a grant by UUID
- `create_latch() -> StorageLatch`
    - Create a new 
- `get_latch(storage_latch_uuid) -> StorageLatch`
    - Get a [storage latch](#storage-latches) by UUID
- `set_latch(storage_latch_uuid) -> StorageLatch`
    - Set a [storage latch](#storage-latches) by UUID
- `delete_storage_latch(storage_latch_uuid) -> null`
    - Delete a [storage latch](#storage-latches) by UUID
- `cleanup_latches(oldest: Datetime) -> null`
    - Delete all latches older than the specified oldest datetime



## Grants

Grants should offer more flexibility over the reference implementation, but be standard across the SDKs.

They should provide these additional fields:

- uuid - Grant UUID
- name - friendly name
- description - describe what the grant is for
- tags - General key values that can be used to categorize grants.


```json
{
    "uuid": "6ce44005-8735-45ac-ae76-38e22e66f615",
    "name": "My grant name",
    "description": "Longer description here to explain what the grant is for.",
    "tags": {
        "some_key": "some_val"
    },
    "effect": "allow",
    "actions": [
        "Balloon:Pop",
        "Balloon:Inflate"
    ],
    "query": "contains(request.identities.Group[? contains(grant.data.allowed_groups, cn)]",
    "query_validation": "validate",
    "equality": true,
    "data": {
        "allowed_groups": "MyGroup"
    },
    "context_schema": {
        "type": "object",
        "required": [
            "some_context_field"
        ]
    },
    "context_validation": "none"
}
```

Generally speaking, grants should only every be created or destroyed, never updated. 
This simplifies many storage and compute structures and allows for more scalability. 


## Engine Locality

Engine Locality is a way to describe "where" a compute or storage engine is or could be located in relation to where the Authzee app is created. 
This will determine the compute localities that are compatible with specific storage localities.

- process - The engine is localized to the same process as the Authzee app
    - Compute resources are shared with the same process as the Authzee app
    - Storage is localized to the same process and is not shared with any other instances of the Authzee app (other processes)
- system - The engine is localized to the same system as the Authzee app
    - Compute resources are shared with the same system as the Authzee app
    - Storage is localized to the same system and is shared with other Authzee app instances on the system
- network - The engine is localized to the same network as the Authzee app
    - Compute resources are shared with systems across the same network as the Authzee app
    - Storage is localized to the same network and is shared with other Authzee app instances on systems, on the same network

Compute localities are only compatible with storage localities that are the same or have a "wider" locality. 
The compatibility matrix:

| Compute Locality | Process Storage Locality | System Storage Locality | Network Storage Locality |
|---|---|---|---|
| Process | ✅ | ✅ | ✅ |
| System | ❌ | ✅ | ✅ |
| Network | ❌ | ❌ | ✅ |


## Storage Latches

Storage latches are flag like objects kept in the storage engine. 

```json
{
    "storage_latch_uuid": "7fa89195-d455-444c-ad53-9f1c66a0fc85",
    "set": false,
    "created_at": "2025-07-20T04:13:17.292144Z"
}
```

Storage latches can only be created, set, or deleted. 
They cannot be unset. 

Compute engines may call on the storage engine to create latches to manage the state of workflows. 


## Standard JMESPath Extensions

JMESPath libraries offer the ability extend functionality by making new functions available in JMESPath queries. 

There are some custom functions that are needed in Authzee SDKs to enabled some query techniques. 

- [Inner Join](#inner-join) - Join 2 arrays 


### Inner Join

`inner_join(lhs: array, rhs: array, expr: str) -> array`

- Takes 2 arrays and a jmespath expression

```python


def inner_join(lhs, rhs, expr):
    result = []
    for l in lhs:
        for r in rhs:
            if jmespath.search( # how to pass the pointer from earlier?
                expr,
                {
                    "lhs": l,
                    "rhs": r
                }
            ) is True:
                result.append(
                    {
                        "lhs": l,
                        "rhs": r
                    }
                )
    
    return result

```

