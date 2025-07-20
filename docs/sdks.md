# Official Authzee SDKs

Authzee SDKs come in many languages, and the official ones offer the same general API's and architecture.
This makes it easier to switch languages by standardizing SDK patterns, and still leave room for language specific functionality and syntax. 

They offer a flexible and scalable general purpose interface, but they are opinionated in their APIs.  
If this doesn't fit your use case you are free to create your own as long as the core is compliant with the Authzee spec!

> **NOTE** - This document is not a specification but a list of recommendations.  It may change and will not effect the specification or specification version of Authzee.

## SDKs

SDKs are considered:
- **Authzee Compliant** - Follows the Authzee specification.
- **Maintained** - Actively maintained.
- **SDK Standard** - Follows the Authzee SDK standard.  It's not a bad thing if the library isn't does not follow the standard.  You can expect a different interface than the official SDKs. 
- **Official** - Branded as the official Authzee SDK for a language. Again, not a bad thing, the other options could be better!

| Language | Code Repo | Package - Repo | Authzee Compliant | Maintained | SDK Standard | Official |
|---|---|---|:---:|:---:|:---:|:---:|
| python | [authzee-py](https://github.com/btemplep/authzee-py) | [authzee](https://pypi.org/project/authzee/) - pypi.org | ✅ | ✅ | ✅ | ✅ |

<!-- 
Green checks for all that are compliant
Red X for if not compliant for "Authzee Complaint" and "Maintained"
Grey Check box if not compliant for "SDK Standard" and "Official"

| python | [authzee-py-bad](https://github.com/btemplep/authzee-py) | [authzee-bad](https://pypi.org/project/authzee/) - pypi.org | ❌ | ❌ | ☑️ | ☑️ |
| python | [authzee-py-compliant](https://github.com/btemplep/authzee-py) | [authzee-comliant](https://pypi.org/project/authzee/) - pypi.org | ✅  | ✅ | ☑️ | ☑️ |
-->


## SDK Standard

The following sections outline Authzee SDK standards.  All examples are given in python or JSON with python naming conventions, but the SDKs should change this based on the convention of the language. 

The suggested architecture of SDKs is to have a primary class, `Authzee`, and create instances from it. 

> **NOTE** - The docs will use class and method terminology, but for languages that don't, translate:
> - Classes -> struct definitions
> - Class instances or objects -> struct instances
> - Methods -> struct methods or functions that act on a struct 

Under this object, identity definitions, resource definitions, and the JMESPath search function are static.
The Authzee object is created with a compute module and a storage module. The compute module will be used to provide the compute resources for running workflows, 
and the storage module will be used to store and retrieve grants and other compute state objects. 


## Authzee Object or Struct

The `Authzee` object should take these arguments when created:
- Identity defs
- Resource defs
- JMESPath search function
- Compute Module type and arguments
- Storage Module type and arguments

If the language supports async, there should also be an async version, `AuthzeeAsync`. 

These are the methods of functions for the Authzee object.  For the `AuthzeeAsync` class, they should all be async functions.

- `start() -> None`
    - start up Authzee app 
    - Initialize runtime resources
- `shutdown() -> None`
    - shutdown authzee app
    - clean up runtime resources
- `setup() -> None` 
    - Construct backend resources for compute and storage
    - one time setup 
- `teardown() -> None` 
    - tear down backend resources 
    - destructive - may lose all storage and compute etc.
- `list_grants(effect: str, action: str) -> GrantsIterator` 
    - auto paginate list grants
    - Maybe also by tags?
- `get_grants_page(effect: str, action: str, page_token: str) -> GrantsPage` 
    - get a page of grants
    - Maybe also by tags?
- `get_grant_page_refs_page(effect: str, action: str, page_token: str) -> GrantPageRefsPage` 
    - get a page of grant page references for parallel pagination
    - For some storage modules this may not be possible
    - Maybe also by tags?
- `get_grant(grant_uuid: UUID) -> Grant`
    - Get a grant by UUID
- `add_grant(new_grant: NewGrant) -> Grant` 
    - add a new grant
- `delete_grant(grant_uuid: UUID) -> None` 
    - delete a grant
- `evaluate(request: obj, parallel_paging: bool) -> EvaluateIterator` 
    - Run evaluate workflow with auto pagination
    - parallel pagination will send a whole page of grant page refs to be computed at a time which can help to cut down on latency between pages.
- `evaluate_page(request: obj, page_token) -> EvaluatePage` 
    - Run evaluate workflow for a single page of results
- `authorize(request: obj) -> AuthorizeResult` 
    - run authorize workflow


## Compute Modules

Compute modules provide a standard API for running workflows on compute.
They have direct access to the storage module and use it to retrieve grants. 
They may also use the storage module to create and retrieve latches that help with compute state.  Especially for compute that is spread across multiple systems.

> **NOTE** - If the language supports async, then the compute module functions are expected to be async. Even if the underlying functionality is not async, this is to simplify the API between the `Authzee` app and the compute modules.  As well as avoid having to create a sync and async version of each compute module. 

Compute Modules should take these arguments when created:
- Identity definitions
- Resource Definitions
- JMESPath function pointer
- Storage module type and arguments
- Other module specific arguments as needed

Compute modules need to declare these public constant class vars when they are created, or have getters:
- locality - Compute [Module Locality](#module-locality) 
- parallel_paging_supported - if the compute module supports processing grants with parallel paging

Compute modules objects or structs should implement these methods:

- `start() -> null`
    - start up compute module
    - run before use
- `shutdown() -> null`
    - shutdown compute module
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


## Storage Modules
Storage modules provide a standard API for storing and retrieving grants and [Storage Latches](#storage-latches). 

> **NOTE** - If the language supports async, then the storage module functions are expected to be async. Even if the underlying functionality is not async, this is to simplify the API between the pieces. 

Storage Modules should take these arguments when created:
- Identity definitions
- Resource Definitions
- Other module specific arguments as needed


Storage modules need to declare these public constant class vars when they are created, or have getters:
- locality - Storage [Module Locality](#module-locality) 
- parallel_paging_supported - if the storage modules supports parallel paging (returning a page of grant page references). 

Storage module objects or structs should implement these methods:
 `start() -> null`
    - start up storage module
    - run before use
- `shutdown() -> null`
    - shutdown storage module
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
    - **OPTIONAL** - For some storage modules this may not be possible.  Set `parallel_paging_supported` accordingly.
- `get_grant(grant_uuid: UUID) -> Grant`
    - Get a grant by UUID
- `create_latch() -> StorageLatch`
    - Create a new [storage latch](#storage-latches) by UUID
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

- uuid - Grant UUID.
- name - People friendly name.
- description - Longer description for the grant.
- tags - Key/value pairs that can be used to as grant metadata.


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


## Module Locality

Module Locality is a way to describe "where" a compute or storage module is or could be located in relation to where the Authzee app is created. 
This will determine the compute localities that are compatible with specific storage localities.

- process - The module is localized to the same process as the Authzee app.
    - Compute resources are shared with the same process as the Authzee app.
    - Storage is localized to the same process and is not shared with any other instances of the Authzee app (other processes).
- system - The module is localized to the same system as the Authzee app.
    - Compute resources are shared with the same system as the Authzee app.
    - Storage is localized to the same system and is shared with other Authzee app instances on the system.
- network - The module is localized to the same network as the Authzee app.
    - Compute resources are shared with systems across the same network as the Authzee app.
    - Storage is localized to the same network and is shared with other Authzee app instances on systems, on the same network.

Compute localities are only compatible with storage localities that are the same or have a "larger" locality. 

The compute locality compatibility matrix with storage localities:

| Storage Locality<br>Compute Locality＼| Process | System | Network |
|---|:---:|:---:|:---:|
| Process | ✅ | ✅ | ✅ |
| System | ❌ | ✅ | ✅ |
| Network | ❌ | ❌ | ✅ |


## Storage Latches

Storage latches are flag like objects kept in the storage module. 

```json
{
    "storage_latch_uuid": "7fa89195-d455-444c-ad53-9f1c66a0fc85",
    "set": false,
    "created_at": "2025-07-20T04:13:17.292144Z"
}
```

Storage latches can only be created, set, or deleted. 
They cannot be unset. 

Compute modules may call on the storage module to create latches to manage the state of workflows. 


## Standard JMESPath Extensions

JMESPath libraries offer the ability extend functionality by making new functions available in JMESPath queries. 

Custom functions are needed in Authzee SDKs to enabled some query techniques. 

- [Inner Join](#inner-join) - Join 2 arrays 
- [regex](#regex) - Run regex patterns
- [regex_group](#regex-Group) - Extract a regex group


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


### regex

> **WARNING** - Regex evaluation differs based on the on the underlying language/library implementation. Regex evaluation is not standardized across programming languages, and it's not expected for the SDKs to create standard regex evaluation at this point. 


Run regex patterns against a string or array of strings.


### regex Group

> **WARNING** - Regex evaluation differs based on the on the underlying language/library implementation. Regex evaluation is not standardized across programming languages, and it's not expected for the SDKs to create standard regex evaluation at this point. 

Extract a regex group from a string or array of strings. 

