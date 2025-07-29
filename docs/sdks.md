# Official Authzee SDKs

Authzee official SDKs offer the same general API's and architecture.
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

> **NOTE** - The docs will use class and method terminology, but for languages that don't, translate as so:
> - Classes -> struct definitions
> - Class instances or objects -> struct instances
> - Methods -> struct methods or functions that act on a struct 

Under this object, identity definitions, resource definitions, and the JMESPath search function are static.
The Authzee object is created with a compute module and a storage module. The compute module will be used to provide the compute resources for running workflows, 
and the storage module will be used to store and retrieve grants and other compute state objects. 


## Authzee Class

The `Authzee` class should take these arguments when created:
- Identity Definitions
- Resource Definitions
- JMESPath search function
- Compute Module type and arguments
- Storage Module type and arguments

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
- `list_grants(effect: str, action: str) -> GrantsIterator` 
    - auto paginate list grants
    - Maybe also by tags?
- `get_grants_page(effect: str, action: str, page_token: str) -> GrantsPage` 
    - get a page of grants
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

Compute modules objects or structs should implement these methods:

- `start() -> null`
    - start up compute module
    - run before use
    - After this method is complete these public instance vars or getters must be available:
        - locality - Compute [Module Locality](#module-locality) 
        - parallel_paging - if the compute module supports processing grants with parallel paging
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


Storage modules should implement these methods:
 `start() -> null`
    - start up storage module
    - run before use
    - After this method is complete these public instance vars or getters must be available:
        - locality - Storage [Module Locality](#module-locality) 
        - parallel_paging - if the storage modules supports parallel paging (returning a page of grant page references). 
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

| _______________Storage Locality<br>Compute Locality＼| Process | System | Network |
|---|:---:|:---:|:---:|
| Process | ✅ | ✅ | ✅ |
| System | ❌ | ✅ | ✅ |
| Network | ❌ | ❌ | ✅ |


Authzee Localities are usually the same as the storage locality.


## Grants

Grants should offer more flexibility over the reference implementation, but be standard across the SDKs.

They should provide these additional fields:

- uuid - Grant UUID.
- name - People friendly name.
- description - Longer description for the grant.
- tags - Key/value pairs that can be used to as grant metadata.


These additional fields should also be available to the query at runtime. 

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

Compute modules may call on the storage module to create latches to manage the state of workflows.  When compute is shared over the network this because a necessary piece when syncing up on workflows.


## Standard JMESPath Extensions

JMESPath libraries offer the ability extend functionality by making new functions available in JMESPath queries. 
Authzee purposely takes a JMESPath search function as an argument so that custom functions can be used. Authzee SDKs should also offer a set of JMESPath functions out of the box the are helpful to Authzee grant queries.

- [INNER JOIN](#inner-join) - Join 2 arrays in a fashion similar to an SQL INNER JOIN. 
- [regex Find](#regex-find) - Run a regex pattern on a string or array of strings to find the first match.
- [regex Find All](#regex-find-all) - Run a regex pattern on a string or array of strings to find all matches.
- [regex Find Groups](#regex-group-find) - Run a regex pattern on a string or array of strings to find the first match, and extract the groups.


The sections are given in the same format as the [JMESPath Built-in Function Specification](https://jmespath.org/specification.html#built-in-functions)

### INNER JOIN

`array[object] inner_join(array[any] $lhs, array[any] $rhs, expression->number expr)`

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

def inner_join(lhs: List[Any], rhs: List[Any], expr: str) -> List[Dict[str, Any]]:
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


### regex Find

`string|null|array[string|null] regex_find(string $pattern, string|array[string] $subject, boolean $all)`

> **WARNING** - Regex evaluation differs based on the underlying language/library implementation. Regex evaluation is not standardized across programming languages, and it's not expected for the SDKs to create standard regex evaluation *at this point*. The general functionality should match between languages though, besides difference in the syntax and implementation of the regex notation evaluation.

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


`string|null|array[string|null] regex_find(string $pattern, string|array[string] $subject)`
Simple Python Example

```python
import re
from typing import List, Union


def regex_find(pattern: str, subject: Union[str, List[str]]) -> Union[None, str, List[Union[None, str]]]:
    if type(subject) is str:
        

```

### regex Find All

`array[string]|array[array[string]] regex_find_all(string $pattern, string|array[string] $subject)`

> **WARNING** - Regex evaluation differs based on the underlying language/library implementation. Regex evaluation is not standardized across programming languages, and it's not expected for the SDKs to create standard regex evaluation *at this point*. The general functionality should match between languages though, besides difference in the syntax and implementation of the regex notation evaluation.

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
           <code>regex_find('pattern', 'some string here')</code>
        </td>
        <td>
            <code>[]</code>
        </td>
    </tr>
    <tr>
        <td>
           <code>regex_find('string[0-9]', 'some string3 here string4')</code>
        </td>
        <td>
            <code>["string3", "string4"]</code>
        </td>
    </tr>
    <tr>
        <td>
           <code>regex_find('string.+', `["something", "here"]`)</code>
        </td>
        <td>
            <code>[[], []]</code>
        </td>
    </tr>
    <tr>
        <td>
           <pre><code>regex_find(
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
    ["string2", "string7"], 
    [], 
    ["string3"]
]</code></pre>
        </td>
    </tr>
</table>



### regex Groups

`null|array[string|null]|array[array[string|null]|null] regex_groups(string|array[string] $subject, string $pattern)`

> **WARNING** - Regex evaluation differs based on the underlying language/library implementation. Regex evaluation is not standardized across programming languages, and it's not expected for the SDKs to create standard regex evaluation *at this point*. The general functionality should match between languages though, besides difference in the syntax and implementation of the regex notation evaluation.

The return value depends on the subject type:
- `string` - Run a regex pattern against a string and return an array of all groups from the first occurrence of the pattern, or `null` if there are no pattern matches. If the group has no value it will be `null`.
- `array[string]` - Run a regex pattern on an array of strings and return an equal length array where each element is an array of groups from the first occurrence of the pattern or `null` if there are no pattern matches. If the group has no value it will be `null`.

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
    'string.+(my_group[0-4])|string.+(my_group[5-9])', 
    'a string now my_group9 another string my_group2'
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
    'string.+(my_group[0-4])|string.+(my_group[5-9])', 
    `[
        "something", 
        "a string now my_group9 another string my_group2", 
        "here"
    ]`
)</code></pre>
        </td>
        <td>
            <code>[null, [null, "my_group9"], null]</code>
        </td>
    </tr>
</table>



Simple Python Example

```python
import re

# Use re.search() to find first

```


### regex Groups All

`null|array[array[string|null]]|array[null|array[array[string|null]]] regex_groups_all(string|array[string] $subject, string $pattern)`

> **WARNING** - Regex evaluation differs based on the underlying language/library implementation. Regex evaluation is not standardized across programming languages, and it's not expected for the SDKs to create standard regex evaluation *at this point*. The general functionality should match between languages though, besides difference in the syntax and implementation of the regex notation evaluation.

The return value depends on the subject type:
- `string` - Run a regex pattern against a string and return an array where each item is an array of groups for each occurrence of the pattern, or `null` if there are no pattern matches. If the group has no value it will be `null`.
- `array[string]` - Run a regex pattern on an array of strings and return an equal length array where each element is an array of all occurrences of the pattern or `null` if there are no pattern matches.  Each element in that array is an array of the groups. If the group has no value it will be `null`.

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
            <code>null</code>
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
    'string.+(my_group[0-4])|string.+(my_group[5-9])', 
    'a string now my_group9 another string my_group2'
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
            <code>[null, null]</code>
        </td>
    </tr>
    <tr>
        <td>
           <code>regex_groups_all('string.+', `["something", "a string now", "here"]`)</code>
        </td>
        <td>
            <code>[null, [[]], null]</code>
        </td>
    </tr>
    <tr>
        <td>
           <pre><code>regex_groups_all(
    'string.+(my_group[0-4])|string.+(my_group[5-9])', 
    `[
        "something", 
        "a string now my_group9 another string my_group2", 
        "here"
    ]`
)</code></pre>
        </td>
        <td>
            <pre><code>[
    null,
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
    null
]</code></pre>
        </td>
    </tr>
</table>



Simple Python Example

```python
import re

# Use re.search() to find first

```
