# Official Authzee SDKs

Authzee official SDKs offer the same general API's and architecture.
This makes it easier to switch languages by standardizing SDK patterns, and still leave room for language specific functionality and syntax. 

They offer a flexible and scalable general purpose interface, but they are opinionated in their APIs.  
If this doesn't fit your use case you are free to create your own as long as the core is compliant with the Authzee spec!

> **NOTE** - This document is not a specification but a list of recommendations.  It may change and will not effect the specification or specification version of Authzee.

### Table of Contents

- [Available SDKs](#available-sdks)
- [SDK Standards](#sdk-standards)
    - [Authzee Class](#authzee-class)
    - [Compute Modules](#compute-modules)
    - [Storage Modules](#storage-modules)
    - [Module Locality](#module-locality)
    - [Storage Latches](#storage-latches)
    - [Standard Types](#standard-types)
- [Standard JMESPath Extensions](#standard-jmespath-extensions)
    - [INNER JOIN](#inner-join)
    - [regex Find](#regex-find)
    - [regex Find All](#regex-find-all)
    - [regex Groups](#regex-groups)
    - [regex Groups All](#regex-groups-all)


## Available SDKs

SDKs are considered:
- **Authzee Compliant** - Follows the Authzee specification.
- **Maintained** - Actively maintained.
- **SDK Standard** - Follows the Authzee SDK standard.  It's not a bad thing if the library does not follow the standard.  You can expect a different interface than the official SDKs. 
- **Official** - Branded as the official Authzee SDK for a language. Again, not a bad thing if the library isn't official.

| Language | Code Repo | Package - Repo | Authzee Compliant | Maintained | SDK Standard | Official |
|---|---|---|:---:|:---:|:---:|:---:|
| python | [authzee-py](https://github.com/btemplep/authzee-py) | [authzee](https://pypi.org/project/authzee/) - pypi.org | ❌ | ✅ | ☑️ | ✅ |

<!-- 
Green checks for all that are compliant
Red X for if not compliant for "Authzee Complaint" and "Maintained"
Grey Check box if not compliant for "SDK Standard" and "Official"

| python | [authzee-py-bad](https://github.com/btemplep/authzee-py) | [authzee-bad](https://pypi.org/project/authzee/) - pypi.org | ❌ | ❌ | ☑️ | ☑️ |
| python | [authzee-py-compliant](https://github.com/btemplep/authzee-py) | [authzee-comliant](https://pypi.org/project/authzee/) - pypi.org | ✅  | ✅ | ☑️ | ☑️ |
-->


## SDK Standards

The following sections outline Authzee SDK standards.  All examples are given in python or JSON with python naming conventions, but the SDKs should change this based on the convention of the language. 

The suggested architecture of SDKs is to have a primary class, `Authzee`, and create instances from it.  This class provides the only public API to the Authzee SDKs. 

> **NOTE** - The docs will use class and method terminology, but for languages that don't, translate as so:
> - Classes -> struct definitions
> - Class instances or objects -> struct instances
> - Methods -> struct methods or functions that act on a struct 

Under this object, identity definitions, resource definitions, and the JMESPath search function are static.
The Authzee object is created with a compute module and a storage module. The compute module will be used to provide the compute resources for running workflows, and the storage module will be used to store and retrieve grants and other compute state objects. 

> **NOTE** - The Standard describes the minimum expectations of what an Authzee SDK should meet.  SDKs are welcome to have more functionality!!!

- [Authzee Class](#authzee-class)
- [Compute Modules](#compute-modules)
- [Storage Modules](#storage-modules)
- [Module Locality](#module-locality)
- [Standard Types](#standard-types)
- [Storage Latches](#storage-latches)


## Authzee Class

The `Authzee` class should take these arguments when created:
- Identity Definitions
- Resource Definitions
- JMESPath search function
- Compute Module type and arguments
- Storage Module type and arguments
- Default grants page size
- Default grant refs page size

If the language supports async, there should also be an async version, `AuthzeeAsync`. 

These are the methods for the Authzee class.  For the `AuthzeeAsync` class, they should all be async.

- `start() -> None`
    - start up Authzee app 
    - Initialize runtime resources
    - After this method is complete these public instance vars or getters must be available:
        - locality - Authzee [Module Locality](#module-locality) to tell the limit of where other Authzee instances can be created.
        - parallel_paging - if the instance of Authzee supports processing grant pages in parallel according to the compute and storage combination. 
- `shutdown() -> None`
    - shutdown authzee app
    - clean up runtime resources
- `setup() -> None` 
    - Construct backend resources for compute and storage
    - one time setup 
- `teardown() -> None` 
    - tear down backend resources 
    - destructive - may lose all storage and compute etc.
- `enact(new_grant: NewGrant) -> Grant` 
    - add a new grant.
- `repeal(grant_uuid: UUID) -> None` 
    - delete a grant.
- `get_grants_page(effect: str|None, action: str|None, page_ref: str|None, page_size: int|None, parallel_paging: bool, ref_page_size: int|None) -> GrantsPage` 
    - get a page of grants
- `get_grant_page_refs_page(effect: str|None, action: str|None, page_ref: str|None, page_size: int|None) -> GrantPageRefsPage` 
    - get a page of grant page references for parallel pagination
    - For some storage modules this may not be possible, check the `parallel_paging` value.
- `get_grant(grant_uuid: UUID) -> Grant`
    - Get a grant by UUID
- `audit_page(request: AuthzeeRequest, page_ref: str|None, page_size: int|None, parallel_paging: bool, ref_page_size: int|None) -> AuditPage` 
    - Run the Audit Workflow for a page of results.
    - Parallel pagination will send a whole page of grant page refs to be computed at a time which can help to cut down on latency between pages but may produce significantly more results.
- `authorize(request: AuthzeeRequest, page_size: int|None, parallel_paging: bool, ref_page_size: int|None) -> AuthorizeResult` 
    - Run the Authorize Workflow.


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

Compute modules objects or structs should implement these methods:

- `start() -> None`
    - start up compute module
    - run before use
    - After this method is complete these public instance vars or getters must be available:
        - locality - Compute [Module Locality](#module-locality) 
        - parallel_paging - if the compute module supports processing grants with parallel paging
- `shutdown() -> None`
    - shutdown compute module
    - clean up runtime resources
- `setup() -> None` 
    - Construct backend resources for compute 
    - one time setup 
- `teardown() -> None` 
    - tear down backend resources 
    - destructive - may lose all long lasting compute resources
- `audit_page(request: AuthzeeRequest, page_ref: str|None, parallel_paging: bool) -> AuditPage` 
    - Run the Audit Workflow for a page of results.
    - Parallel pagination will send a whole page of grant page refs to be computed at a time which can help to cut down on latency between pages but may produce significantly more results.
- `authorize(request: AuthzeeRequest) -> AuthorizeResult` 
    - Run the Authorize Workflow.


## Storage Modules

Storage modules provide a standard API for storing and retrieving grants and [Storage Latches](#storage-latches). 

> **NOTE** - If the language supports async, then the storage module functions are expected to be async. Even if the underlying functionality is not async, this is to simplify the API between the pieces. 

Storage Modules should take these arguments when created:
- Identity definitions
- Resource Definitions
- Other module specific arguments as needed


Storage modules should implement these methods:
 `start() -> None`
    - start up storage module
    - run before use
    - After this method is complete these public instance vars or getters must be available:
        - locality - Storage [Module Locality](#module-locality) 
        - parallel_paging - if the storage modules supports parallel paging (returning a page of grant page references). 
- `shutdown() -> None`
    - shutdown storage module
    - clean up runtime resources
- `setup() -> None` 
    - Construct backend resources for storage 
    - one time setup 
- `teardown() -> None` 
    - tear down backend resources 
    - destructive - may lose all long lasting compute resources
- `enact(new_grant: NewGrant) -> Grant` 
    - add a new grant.
- `repeal(grant_uuid: UUID) -> None` 
    - delete a grant.
- `get_grants_page(effect: str|None, action: str|None, page_ref: str|None) -> GrantsPage` 
    - get a page of grants
- `get_grant_page_refs_page(effect: str|None, action: str|None, page_ref: str|None) -> GrantPageRefsPage` 
    - get a page of grant page references for parallel pagination
    - For some storage modules this may not be possible, check the `parallel_paging` value.
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

> **NOTE** - When listing grants there are 2 filters: `effect` and `action`.  Storage modules should partition grants on these 2 fields. 


## Module Locality

Module Locality is a way to describe "where" a compute module, storage module, or Authzee instance could be located in relation to one another.  This will determine the compute localities that are compatible with specific storage localities.  It will also limit how Authzee instances can be created. 

- process - The module is localized to the same process as the Authzee app.
    - Compute resources are shared with the same process as the Authzee app.
    - Storage is localized to the same process and is not shared with any other instances of the Authzee app (other processes).
    - Authzee instances must exist within the same process.
- system - The module is localized to the same system as the Authzee app.
    - Compute resources are shared with the same system as the Authzee app.
    - Storage is localized to the same system and is shared with other Authzee app instances on the system.
    - Authzee instances must exist within the same system.
- network - The module is localized to the same network as the Authzee app.
    - Compute resources are shared with systems across the same network as the Authzee app.
    - Storage is localized to the same network and is shared with other Authzee app instances on systems, on the same network.
    - Authzee instances must exist within the same network.  More verbosely, the storage and compute is available over the network from all Authzee instances.

Compute localities are only compatible with storage localities that are the same or have a "larger" locality. 

The compute locality compatibility matrix with storage localities:

| _____________＼Storage Locality<br>Compute Locality＼ _______________ | Process | System | Network |
|---|:---:|:---:|:---:|
| Process | ✅ | ✅ | ✅ |
| System | ❌ | ✅ | ✅ |
| Network | ❌ | ❌ | ✅ |

Authzee Localities are usually the same as the storage locality.


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

Compute modules may call on the storage module to create latches to manage the state of workflows.  When compute is shared over the network this becomes a necessary piece to communicate different workflow statuses.


## Standard Types

The input and output objects (data class instances, struct instances) should take a standard form when dealing with the Authzee class. The Authzee class provides the only public API to the SDKs, but the compute and storage classes are expected to provide consistent APIs to make compute and storage classes interchangeable. 

Standard Types:
- [page_ref](#page_ref)
- [Grant](#grant)
- [NewGrant](#newgrant)
- [GrantsPage](#grantspage)
- [GrantPageRefsPage](#grantpagerefspage)
- [AuthzeeRequest](#authzeerequest)
- [AuditPage](#auditpage)
- [AuthorizeResult](#authorizeresult)

### page_ref

Authzee relies on pagination to make it's operations scalable. 
`page_ref` represents a string token to a specific page of resources.  To get the first page of a resource the `page_ref` should have a `null` value.  `next_ref` is present in responses to be passed on the next function call to retrieve the next page.  When `next_ref` is a `null` value, the current page is considered the last and should not be passed back to the function.


### Grant

Grants should offer more flexibility over the reference implementation, but be standard across the SDKs.

```json
{
    "grant_uuid": "6ce44005-8735-45ac-ae76-38e22e66f615",
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

They should provide these additional fields over the [Grant Specification](./specification.md#grants), and they should also be available to query during runtime. 

| Field | Type | Required | Description |
|---|---|---|---|
| `grant_uuid` | string(UUID) | ✅ | UUID for the grant. |
| `name` | string |  ✅ | People friendly name for the grant |
| `description` | string |  ✅ | People friendly long description for the grant. |
| `tags` | object[string, string] | ✅ | Additional people metadata for the grant. An object whose keys and values are strings. |

Generally speaking, grants should only be created or deleted, never updated. 
This simplifies many storage and compute structures and allows for more scalability. 


### NewGrant

Used when creating a new grant.  The same as [Grant](#grant) without the `grant_uuid` field as that is generated by Authzee.


### GrantsPage

A single page of [Grants](#grant).

```json
{
    "grants": [],
    "next_ref": "abc123"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `grants` | array[Grant]| ✅ | The array of grants. |
| `next_ref` | string|null |  ✅ | A token used to reference the next page of grants to retrieve from Authzee/the storage module. |


### GrantPageRefsPage

A page of grant page references.

```json
{
    "page_refs": [
        "abc123"
    ],
    "next_ref": "def456"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `page_refs` | array[strings] | ✅ | The array page references that can be used to retrieve several pages in parallel. |
| `next_ref` | string|null |  ✅ | A token used to reference the next page of page refs to retrieve from Authzee/the storage module. |


### AuthzeeRequest

The standard "Request" object used to initiate an Authzee workflow. Should match the [Authzee Request Specification](./specification.md#requests)


### AuditPage

A page of Audit Workflow results.  Conforms to the [Audit Workflow Results](./specification.md#audit-workflow-result) except it will also have a `next_ref` field for pagination. 


### AuthorizeResult

The [Authorize Workflow Results](./specification.md#authorize-workflow-response), which conforms to the Authzee specification.


## Standard JMESPath Extensions

JMESPath libraries offer the ability extend functionality by making new functions available in JMESPath queries. 
Authzee purposely takes a JMESPath search function as an argument so that custom functions can be used. Authzee SDKs should also offer a set of JMESPath functions out of the box the are helpful to Authzee grant queries.

- [INNER JOIN](#inner-join) - Join 2 arrays in a fashion similar to an SQL INNER JOIN. 
- [regex Find](#regex-find) - Run a regex pattern on a string or array of strings to find the first match.
- [regex Find All](#regex-find-all) - Run a regex pattern on a string or array of strings to find all matches.
- [regex Groups](#regex-groups) - Run a regex pattern on a string or array of strings to find the first match, and extract the groups.
- [regex Groups All](#regex-groups-all) - Run a regex pattern on a string or array of strings to find all matches, and extract the groups.


The sections are given in the same format as the [JMESPath Built-in Function Specification](https://jmespath.org/specification.html#built-in-functions)

### INNER JOIN

`array[object] inner_join(array[any] $lhs, array[any] $rhs, expression->boolean expr)`

Modeled after SQL INNER JOIN functionality.  Takes 2 arrays and an expression and returns all combinations of elements from the arrays where the expression evaluates to `true`.

Examples:

<table>
    <tr>
        <th>Expression</th>
        <th>Result</th>
    </tr>
    <tr>
        <td>
            <pre><code>inner_join(
    `[
        {
            "l_field": "hello",
            "other_field": "thing"
        }
    ]`,
    `[
        {
            "r_field": "goodbye",
            "r_other_field": "other thing"
        },
        {
            "r_field": "hello",
            "r_other_field": "other other thing"
        }
    ]`,
    lhs.l_field == rhs.r_field
) </code></pre>
        </td>
        <td>
            <pre><code>[
    {
        "lhs": {
            "l_field": "hello",
            "other_field": "thing"
        },
        "rhs": {
            "r_field": "hello",
            "r_other_field": "other other thing"
        }
    }
]           </code></pre>
        </td>
    </tr>
    <tr>
        <td>
            <pre><code>inner_join(
    `[
        {
            "l_field": "hello",
            "other_field": "thing"
        }
    ]`,
    `[
        {
            "r_field": "goodbye",
            "r_other_field": "other thing"
        }
    ]`,
    lhs.l_field == rhs.r_field
) </code></pre>
        </td>
        <td>
            <code>[]</code>
        </td>
    </tr>
</table>

Simple python function example:

```python
from typing import Any, Dict, List

import jmespath


def inner_join(lhs: List[Any], rhs: List[Any], expr: str) -> List[Dict[str, Any]]:
    result = []
    for l in lhs:
        for r in rhs:
            if jmespath.search( # Should use passed in jmespath search function.
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


### regex Find

`string|null|array[string|null] regex_find(string $pattern, string|array[string] $subject)`

> **WARNING!** - Regex evaluation differs based on the underlying language/library implementation. Regex evaluation is not standardized across programming languages, and it's not expected for the SDKs to create standard regex evaluation *at this point*. The general functionality of the JMESPath custom functions should match between languages though.

The return value depends on the subject type:
- `string` - Run a regex pattern against a string and return the first occurrence of the pattern or `null` if there are none.
- `array[string]` - Run a regex pattern on an array of strings and return an equal length array where each element is the first occurrence of the pattern or `null` if there are none.  

Examples:

<table>
    <tr>
        <th>Expression</th>
        <th>Result</th>
    </tr>
    <tr>
        <td>
           <code>regex_find('pattern.*', 'some string here')</code>
        </td>
        <td>
            <code>null</code>
        </td>
    </tr>
    <tr>
        <td>
           <code>regex_find('string.+', 'some string here')</code>
        </td>
        <td>
            <code>"string here"</code>
        </td>
    </tr>
    <tr>
        <td>
           <code>regex_find('string.+', `["something", "here"]`)</code>
        </td>
        <td>
            <code>[null, null]</code>
        </td>
    </tr>
    <tr>
        <td>
           <code>regex_find('string.+', `["something", "a string now", "here"]`)</code>
        </td>
        <td>
            <code>[null, "string now", null]</code>
        </td>
    </tr>
</table>

Simple Python Example:

```python
import re
from typing import List, Union


def regex_find(pattern: str, subject: Union[str, List[str]]) -> Union[None, str, List[Union[None, str]]]:
    if type(subject) is str:
        match = re.search(pattern, subject)
        if match is not None:
            return match.group()
        else:
            return None
    
    if type(subject) is list:
        result = []
        for sub in subject:
            match = re.search(pattern, sub)
            if match is not None:
                result.append(match.group())
            else:
                result.append(None)
    
    return result
```

### regex Find All

`array[string]|array[array[string]] regex_find_all(string $pattern, string|array[string] $subject)`

> **WARNING!** - Regex evaluation differs based on the underlying language/library implementation. Regex evaluation is not standardized across programming languages, and it's not expected for the SDKs to create standard regex evaluation *at this point*. The general functionality of the JMESPath custom functions should match between languages though.

The return value depends on the subject type:
- `string` - Run a regex pattern against a string and return an array of all occurrences of the pattern in the string.
- `array[string]` - Run a regex pattern on an array of strings and return an equal length array of results where each element is an array of all occurrences of the pattern in the string.

Examples:

<table>
    <tr>
        <th>Expression</th>
        <th>Result</th>
    </tr>
    <tr>
        <td>
           <code>regex_find_all('pattern', 'some string here')</code>
        </td>
        <td>
            <code>[]</code>
        </td>
    </tr>
    <tr>
        <td>
           <code>regex_find_all('string[0-9]', 'some string3 here string4')</code>
        </td>
        <td>
            <code>["string3", "string4"]</code>
        </td>
    </tr>
    <tr>
        <td>
           <code>regex_find_all('string.+', `["something", "here"]`)</code>
        </td>
        <td>
            <code>[[], []]</code>
        </td>
    </tr>
    <tr>
        <td>
           <pre><code>regex_find_all(
    'string[0-9]',
    `[
        "something",
        "a string2 now string7 too",
        "here", 
        "another string3 here"
    ]`
)</code></pre>
        </td>
        <td>
            <pre><code>[
    [], 
    [
        "string2", 
        "string7"
    ], 
    [], 
    [
        "string3"
    ]
]</code></pre>
        </td>
    </tr>
</table>

Simple Python Example:

```python
import re
from typing import List, Union


def regex_find_all(pattern: str, subject: Union[str, List[str]]) -> Union[List[str], List[List[str]]]:
    if type(subject) is str:
        return re.findall(pattern, subject)
        
    if type(subject) is list:
        result = []
        for sub in subject:
            result.append(re.findall(pattern, sub))
    
    return result
```


### regex Groups

`null|array[string|null]|array[array[string|null]|null] regex_groups(string|array[string] $subject, string $pattern)`

> **WARNING!** - Regex evaluation differs based on the underlying language/library implementation. Regex evaluation is not standardized across programming languages, and it's not expected for the SDKs to create standard regex evaluation *at this point*. The general functionality of the JMESPath custom functions should match between languages though.

The return value depends on the subject type:
- `string` - Run a regex pattern against a string and return an array of all groups from the first occurrence of the pattern, or `null` if there are no pattern matches. If a group has no value it will be `null`.
- `array[string]` - Run a regex pattern on an array of strings and return an equal length array where each element is an array of groups from the first occurrence of the pattern or `null` if there are no pattern matches. If a group has no value it will be `null`.

Examples:

<table>
    <tr>
        <th>Expression</th>
        <th>Result</th>
    </tr>
    <tr>
        <td>
           <code>regex_groups('pattern.*', 'some string here')</code>
        </td>
        <td>
            <code>null</code>
        </td>
    </tr>
    <tr>
        <td>
           <code>regex_groups('string.+', 'some string here')</code>
        </td>
        <td>
            <code>[]</code>
        </td>
    </tr>
    <tr>
        <td>
           <pre><code>regex_groups(
    'string (my_group[0-4])|string (my_other_group[5-9])', 
    'a string my_other_group9 another string my_group2'
)</code></pre>
        </td>
        <td>
            <code>[null, "my_group9"]</code>
        </td>
    </tr>
    <tr>
        <td>
           <code>regex_groups('string.+', `["something", "here"]`)</code>
        </td>
        <td>
            <code>[null, null]</code>
        </td>
    </tr>
    <tr>
        <td>
           <code>regex_groups('string.+', `["something", "a string now", "here"]`)</code>
        </td>
        <td>
            <code>[null, [], null]</code>
        </td>
    </tr>
    <tr>
        <td>
           <pre><code>regex_groups(
    'string (my_group[0-4])|string (my_other_group[5-9])', 
    `[
        "something", 
        "a string my_other_group9 another string my_group2", 
        "here"
    ]`
)</code></pre>
        </td>
        <td>
            <code>[null, [null, "my_group9"], null]</code>
        </td>
    </tr>
</table>



Simple Python Example:

```python
import re
from typing import List, Union


def regex_groups(
    pattern: str, 
    subject: Union[str, List[str]]
) -> Union[
    None, 
    List[Union[None, str]], 
    List[
        Union[
            None, 
            List[
                Union[None, str]
            ]
        ]
    ]
]:
    if type(subject) is str:
        match = re.search(pattern, subject)
        if match is not None:
            return list(match.groups())
        else:
            return None
    
    if type(subject) is list:
        result = []
        for sub in subject:
            match = re.search(pattern, sub)
            if match is not None:
                result.append(list(match.groups()))
            else:
                result.append(None)
    
    return result
```


### regex Groups All

`array[array[string|null]]|array[array[array[string|null]]] regex_groups_all(string|array[string] $subject, string $pattern)`

> **WARNING!** - Regex evaluation differs based on the underlying language/library implementation. Regex evaluation is not standardized across programming languages, and it's not expected for the SDKs to create standard regex evaluation *at this point*. The general functionality of the JMESPath custom functions should match between languages though.

The return value depends on the subject type:
- `string` - Run a regex pattern against a string and return an array where each item is an array of groups for each occurrence of the pattern. If a group has no value it will be `null`.
- `array[string]` - Run a regex pattern on an array of strings and return an equal length array where each element is an array of all occurrences of the pattern.  Each element in the array of occurrences is an array of the groups. If a group has no value it will be `null`.

Examples:

<table>
    <tr>
        <th>Expression</th>
        <th>Result</th>
    </tr>
    <tr>
        <td>
           <code>regex_groups_all('pattern.*', 'some string here')</code>
        </td>
        <td>
            <code>[]</code>
        </td>
    </tr>
    <tr>
        <td>
           <code>regex_groups_all('string.+', 'some string here')</code>
        </td>
        <td>
            <code>[[]]</code>
        </td>
    </tr>
    <tr>
        <td>
           <pre><code>regex_groups_all(
    'string (my_group[0-4])|string (my_other_group[5-9])', 
    'a string my_other_group9 another string my_group2'
)</pre></code>
        </td>
        <td>
            <pre><code>[
    [
        null, 
        "my_group9"
    ], 
    [
        "my_group2", 
        null
    ]
]</code></pre>
        </td>
    </tr>
    <tr>
        <td>
           <code>regex_groups_all('string.+', `["something", "here"]`)</code>
        </td>
        <td>
            <code>[[], []]</code>
        </td>
    </tr>
    <tr>
        <td>
           <code>regex_groups_all('string.+', `["something", "a string now", "here"]`)</code>
        </td>
        <td>
            <code>[[], [[]], []]</code>
        </td>
    </tr>
    <tr>
        <td>
           <pre><code>regex_groups_all(
    'string (my_group[0-4])|string (my_other_group[5-9])', 
    `[
        "something", 
        "a string my_other_group9 another string my_group2", 
        "here"
    ]`
)</code></pre>
        </td>
        <td>
            <pre><code>[
    [],
    [
        [
            null, 
            "my_group9"
        ],
        [
            "my_group2",
            null
        ]
    ], 
    []
]</code></pre>
        </td>
    </tr>
</table>



Simple Python Example

```python
import re
from typing import List, Union


def regex_groups_all(pattern: str, subject: Union[str, List[str]]) -> Union[List[str], List[List[str]]]:
    if type(subject) is str:
        return [list(m.groups()) if m is not None else None for m in re.finditer(pattern, subject)]
        
    if type(subject) is list:
        result = []
        for sub in subject:
            result.append(
                [list(m.groups()) if m is not None else None for m in re.finditer(pattern, sub)]
            )
    
    return result
```
