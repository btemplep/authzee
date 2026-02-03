# Official Authzee SDKs

Authzee official SDKs offer the same general API's and architecture.
This makes it easier to switch languages by standardizing SDK patterns, and still leave room for language specific functionality and syntax. 

They offer a flexible and scalable general purpose interface, but they are opinionated in their APIs.  
If this doesn't fit your use case you are free to create your own! Try to stay compliant with the Authzee spec for the sake of portability.

> **NOTE** - This document is not a specification but a list of recommendations.  It may change and will not effect the specification or specification version of Authzee.


## Example


```python

from authzee import Authzee, InProcessCompute, InProcessStorage

storage = {}
authz = Authzee(
    compute_type=InProcessCompute,
    compute_kwargs={},
    storage_type=InProcessStorage,
    storage_kwargs={
        storage_ptr=storage
    },
    grants_page_size=100,
    grant_refs_page_size=10,
    parallel_paging=True, # default true
    raise_crits=True # Default true
)
authz.start()
authz.setup() # one time setup
context_def = {
    "context_type": "Team",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "Team"
        ],
        "properties": {
            "Team": {
                "type": "string"
            }
        }
    }
}
authz.put_context_def(identity_def) # register a new context definition or update an existing by context_type
get_context_defs_page() # manually paginate registered context definitions
list_context_defs() # Auto paginate context definitions - if the language allows
# authz.delete_context_def(context_def['context_type']) # delete a context def by type

identity_def = {
    "identity_type": "User",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "username",
            "email",
            "department"
        ],
        "properties": {
            "username": {
                "type": "string
            },
            "email": {
                "type": "string",
                "department": "Balloon Sales"
            }
        }
    }
}
authz.put_identity_def(identity_def) # register a new identity definition or update an existing by identity_type
get_identity_defs_page() # manually paginate registered identity definitions
list_identity_defs() # Auto paginate identity definitions - if the language allows
# authz.delete_identity_def(identity_def['identity_type']) # delete a identity def by type

authz.put_resource_def( # register a new resource definition or update an existing by resource_type
    {
        "resource_type": "Balloon",
        "actions": [
            "Balloon:Inflate",
            "Balloon:Deflate",
            "Balloon:ListBalloons"
        ],
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "color",
                "size",
                "psi",
                "is_inflated"
            ],
            "properties": {
                "color": {
                    "type": "string",
                    "enum": [
                        "green",
                        "purple"
                    ]
                },
                "size": {
                    "type": "number",
                    "minimum": 0
                },
                "psi": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Pounds per square inch of inflated air."
                },
                "is_inflated": {
                    "type": "boolean"
                }
            }
        }
    }
)
get_resource_defs_page() # manually paginate registered resource definitions
list_resource_defs() # Auto paginate resource definitions - if the language allows
# authz.delete_resource_def(resource['resource_type']) # delete a resource definition by resource type

grant = authz.enact( # Enact a grant and it will now be used when making authorization decisions. 
    {
        "name": "Balloon Sales and maintenance Inflate",
        "description": "Allow people in the Balloon Sales and Maintenance departments to inflate balloons.",
        "tags": {
            "SomeKey": "SomeVal"
        }
        "effect": "allow",
        "actions": [
            "Balloon:Inflate"
        ],
        "query": "contains(request.identities, 'User') && length(request.identities.User) > `0` && contains(grant.data.allowed_departments, request.identities.User[0].department)",
        "evaluation_handler": "evaluate", 
        "equality": True,
        "data": {
            "allowed_departments": [
                "Maintenance",
                "Balloon Sales"
            ]
        }
    }
)
get_grants_page() # get a page of grants
get_page_refs_page() # get a page of references to grant pages.  Used for parallel pagination
list_grants() # Auto paginate grants - if the language allows
# authz.repeal(grant['grant_uuid']) # Repeal to delete a grant and it does not effect authorization any more. 

request = {
    "identities": {
        "User": [
            {
                "username": "tester",
                "email": "tester@example.com",
                "department": "Balloon Sales"
            }
        ]
    },
    "action": "Balloon:Inflate",
    "resource_type": "Balloon",
    "resource": {
        "color": "green",
        "size": 2.7,
        "psi": 7.2,
        "is_inflated": True
    },
    "context_type": "Team",
    "context": {
        "Team": "My Team"
    },
    "evaluation_handler": "grant"
}
authorize_result = authz.authorize(request)
print(authorize_result)
# {
#     "is_authorized": True,
#     "grant": {
#         "grant_uuid": "8df01e31-819e-45e4-a06b-95d25b89e927"
#         "name": "Balloon Sales and maintenance Inflate",
#         "description": "Allow people in the Balloon Sales and Maintenance departments to inflate balloons.",
#         "effect": "allow",
#         "actions": [
#             "Balloon:Inflate"
#         ],
#         "query": "contains(request.identities, 'User') && length(request.identities.User) > `0` && contains(grant.data.allowed_departments, request.identities.User[0].department)",
#         "evaluation_handler": "evaluate", 
#         "equality": True,
#         "data": {
#             "allowed_departments": [
#                 "Maintenance",
#                 "Balloon Sales"
#             ]
#         }
#     },
#     "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
#     "has_failed": False,
#     "critical_errors": {}
# }

audit_page_result = authz.audit_page(request)
print(audit_page_result)
# {
#     "results": [
#         {
#             "is_applicable": True,
#             "query_result": True,
#             "grant": {
#                 "grant_uuid": "8df01e31-819e-45e4-a06b-95d25b89e927"
#                 "name": "Balloon Sales and maintenance Inflate",
#                 "description": "Allow people in the Balloon Sales and Maintenance departments to inflate balloons.",
#                 "effect": "allow",
#                 "actions": [
#                     "Balloon:Inflate"
#                 ],
#                 "query": "contains(request.identities, 'User') && length(request.identities.User) > `0` && contains(grant.data.allowed_departments, request.identities.User[0].department)",
#                 "evaluation_handler": "evaluate", 
#                 "equality": True,
#                 "data": {
#                     "allowed_departments": [
#                         "Maintenance",
#                         "Balloon Sales"
#                     ]
#                 }
#             },
#             "errors": {}
#         }
#     ],
#     "has_failed": False,
#     "errors": {},
#     "next_ref": None
# }

batch_request = {
    "identities": {
        "User": [
            {
                "username": "tester",
                "email": "tester@example.com",
                "department": "Balloon Sales"
            }
        ]
    },
    "action": "Balloon:Inflate",
    "resource_type": "Balloon",
    "resource": {
        "color": "green",
        "size": 2.7,
        "psi": 7.2,
        "is_inflated": True
    },
    "context_type": "Team",
    "context": {
        "Team": "My Team"
    },
    "evaluation_handler": "grant"
    "batch": [
        {}, # run the request with all the defaults from the root request
        {
            "identities": { # A batch item can override any field besides the action
                "User": [
                    {
                        "username": "tester2",
                        "email": "tester2@example.com",
                        "department": "Balloon Popper"
                    }
                ]
            }
        }
    ]
}
batch_authorize_result = authz.batch_authorize(batch_request)
print(patch_authorize_result)
# {
#     "batch_results": [
#         {
#             "is_authorized": True,
#             "grant": {
#                 "grant_uuid": "8df01e31-819e-45e4-a06b-95d25b89e927"
#                 "name": "Balloon Sales and maintenance Inflate",
#                 "description": "Allow people in the Balloon Sales and Maintenance departments to inflate balloons.",
#                 "effect": "allow",
#                 "actions": [
#                     "Balloon:Inflate"
#                 ],
#                 "query": "contains(request.identities, 'User') && length(request.identities.User) > `0` && contains(grant.data.allowed_departments, request.identities.User[0].department)",
#                 "evaluation_handler": "evaluate", 
#                 "equality": True,
#                 "data": {
#                     "allowed_departments": [
#                         "Maintenance",
#                         "Balloon Sales"
#                     ]
#                 }
#             },
#             "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
#             "has_failed": False,
#             "critical_errors": {}
#         },
#         {
#             "is_authorized": False,
#             "grant": None,
#             "message": "No grants are applicable to the request. Therefore, the request is implicitly denied and is not authorized.",
#             "has_failed": False,
#             "critical_errors": {}s
#         }
#     ],
#     "has_failed": False,
#     "errors": {}
# }

batch_audit_result = authz.batch_audit_page(batch_request)
print(batch_audit_result)
# {
#     "results": [
#         {
#             "grant": {
#                 "grant_uuid": "8df01e31-819e-45e4-a06b-95d25b89e927"
#                 "name": "Balloon Sales and maintenance Inflate",
#                 "description": "Allow people in the Balloon Sales and Maintenance departments to inflate balloons.",
#                 "effect": "allow",
#                 "actions": [
#                     "Balloon:Inflate"
#                 ],
#                 "query": "contains(request.identities, 'User') && length(request.identities.User) > `0` && contains(grant.data.allowed_departments, request.identities.User[0].department)",
#                 "evaluation_handler": "evaluate", 
#                 "equality": True,
#                 "data": {
#                     "allowed_departments": [
#                         "Maintenance",
#                         "Balloon Sales"
#                     ]
#                 }
#             },
#             "batch_results": [
#                 {
#                     "is_applicable": True,
#                     "query_result": True,
#                     "errors": {}
#                 },
#                 {
#                     "is_applicable": False,
#                     "query_result": False,
#                     "errors": {}
#                 }
#             ]
#         }
#     ],
#     "has_failed": False,
#     "errors": {},
#     "next_ref": None
# }
```




### Table of Contents

- [Available SDKs](#available-sdks)
- [SDK Standards](#sdk-standards)
    - [Low Level API](#low-level-api)
    - [Authzee Class](#authzee-class)
    - [Compute Modules](#compute-modules)
    - [Storage Modules](#storage-modules)
    - [Module Locality](#module-locality)
    - [Storage Latches](#storage-latches)
    - [Standard Types](#standard-types)
- [SDK Full Example](#sdk-full-example)
- [Standard JMESPath Extensions](#standard-jmespath-extensions)
    - [INNER JOIN](#inner-join) TODO - Add other joins: left and outer
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

| Language | Code Repo | Package - Repo | Authzee Compliant | Maintained | SDK Standard | Official | Notes |
|---|---|---|:---:|:---:|:---:|:---:|:---:|
| python | [btemplep/authzee-py](https://github.com/btemplep/authzee-py) | [authzee](https://pypi.org/project/authzee/) - pypi.org | ✅ | ✅ | ✅ | ✅ | In progress for updating to the new standard |

<!-- 
Green checks for all that are compliant
Red X for if not compliant for "Authzee Complaint" and "Maintained"
Grey Check box if not compliant for "SDK Standard" and "Official"

| python | [authzee-py-bad](https://github.com/btemplep/authzee-py) | [authzee-bad](https://pypi.org/project/authzee/) - pypi.org | ❌ | ❌ | ☑️ | ☑️ |
| python | [authzee-py-compliant](https://github.com/btemplep/authzee-py) | [authzee-comliant](https://pypi.org/project/authzee/) - pypi.org | ✅  | ✅ | ✅ | ✅ |
-->


## SDK Standards

The following sections outline Authzee SDK standards.  All examples are given in python or JSON with python naming conventions, but the SDKs should change this based on the convention of the language. 

The suggested architecture for the high level API of SDKs is to have a primary class, `Authzee`, and create instances from it.  This class provides the only public API to the Authzee SDKs. 

> **NOTE** - The docs will use class and method terminology, but for languages that don't, translate as so:
> - Classes -> struct definitions
> - Class instances or objects -> struct instances
> - Methods -> struct methods or functions that act on a struct 

Under this object, the JSON query search function is static.
The Authzee object is created with a compute module and a storage module. The compute module will be used to provide the compute resources for running operations, and the storage module will be used to store and retrieve grants and other compute state objects. 

> **NOTE** - The Standard describes the minimum expectations of what an Authzee SDK should meet.  SDKs are welcome to have more functionality!!!

- [Low Level API](#low-level-api)
- [Authzee Class](#authzee-class)
- [Compute Modules](#compute-modules)
- [Storage Modules](#storage-modules)
- [Module Locality](#module-locality)
- [Standard Types](#standard-types)
- [Storage Latches](#storage-latches)


## Low Level API

Authzee SDKs should offer both a high and low level APIs.  
The majority of this document will focus on the high level APIs that are more easily consumed. 

The low level APIs should also exist, and directly follow the specification/reference for Authzee. 
This is to give a core point of logic for the higher level APIs, and the ability to use a Authzee specification-like interface directly.  

It should include these variables to import:

- `authzee_version` - The current version of the Authzee specification supported.
- `context_definition_schema` - Context Definition Schema
- `identity_definition_schema` - Identity Definition Schema
- `resource_definition_schema` - Resource Definition Schema
- `grant_schema` - Grant Schema
- `definition_error_schema` - Definition Type Error Schema
- `grant_error_schema` - Grant Type Error Schema
- `query_error_schema` - Query Type Error Schema
- `request_error_schema` - Request Type Error Schema
- `validate_defs_result_schema` - Return value schema for `validate_defs` function
- `validate_grants_result_schema` - Return value schema for `validate_grants` function
- `request_schema` - Authzee Request Schema
- `validate_request_result_schema` - Return value schema for `validate_request` function
- `evaluate_one_result_schema` - Return value schema for the `evaluate_one` function
- `audit_result_schema` - Return value schema for the `audit` operation/function
- `authorize_result_schema` - Return value schema for the `authorization` operation/function
- `batch_request_schema` - Authzee Batch Request Schema
- `validate_batch_request_result_schema` - Return value schema for the `validate_batch_request` function
- `batch_audit_result_schema` - Return value schema for the `batch_audit` operation/function
- `batch_authorize_result_schema` - Return value schema for the `batch_authorize` operation/function

It should include these functions from the authzee reference:


```python
def validate_context_defs(context_defs: List[Dict[str, AnyJSON]]) -> Dict[str, AnyJSON]:
```

```python
def validate_identity_defs(identity_defs: List[Dict[str, AnyJSON]]) -> Dict[str, AnyJSON]:
```

```python
def validate_resource_defs(resource_defs: List[Dict[str, AnyJSON]]) -> Dict[str, AnyJSON]:
```

```python
def validate_grants(
    grants: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]]
) -> Dict[str, AnyJSON]:
```

```python
def validate_request(
    request: Dict[str, AnyJSON],
    context_defs: List[Dict[str, AnyJSON]],
    identity_defs:List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]]
) -> Dict[str, AnyJSON]:
```

```python
def validate_batch_request(
    batch_request: Dict[str, AnyJSON],
    context_defs: List[Dict[str, AnyJSON]],
    identity_defs:List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]]
) -> Dict[str, AnyJSON]:
```

The `evaluate_one` function is for evaluating a request against one grant.

```python
def evaluate_one(
    request: Dict[str, AnyJSON], 
    grant: Dict[str, AnyJSON],
    execute: Callable[[str, AnyJSON], AnyJSON],
    only_crits: bool
) -> Dict[str, AnyJSON]:
```

```python
def audit(
    request: Dict[str, AnyJSON], 
    grants: List[Dict[str, AnyJSON]],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, List[Dict[str, AnyJSON]]]: 
```


```python
def authorize(
    request: Dict[str, AnyJSON], 
    grants: List[Dict[str, AnyJSON]],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, AnyJSON]:
```

> **NOTE** - Workflow functions perform all steps that need to be done for an operation.  They will return different result depending on if there are failures.  The are included as a way to easily test low level functionality and are just a simplification of the spec. 

```python
def audit_workflow(
    context_defs: List[Dict[str, AnyJSON]],
    identity_defs: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    request: Dict[str, AnyJSON],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, AnyJSON]:
```

```python
def authorize_workflow(
    context_defs: List[Dict[str, AnyJSON]],
    identity_defs: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    request: Dict[str, AnyJSON],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, AnyJSON]:
```

```python
def batch_audit(
    batch_request: Dict[str, AnyJSON], 
    grants: List[Dict[str, AnyJSON]],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, List[Dict[str, AnyJSON]]]: 
```

```python
def batch_authorize(
    batch_request: Dict[str, AnyJSON], 
    grants: List[Dict[str, AnyJSON]],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, List[Dict[str, AnyJSON]]]: 
```

```python
def batch_audit_workflow(
    context_defs: List[Dict[str, AnyJSON]],
    identity_defs: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    batch_request: Dict[str, AnyJSON],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, AnyJSON]:
```

```python
def batch_authorize_workflow(
    context_defs: List[Dict[str, AnyJSON]],
    identity_defs: List[Dict[str, AnyJSON]],
    resource_defs: List[Dict[str, AnyJSON]],
    grants: List[Dict[str, AnyJSON]],
    batch_request: Dict[str, AnyJSON],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, AnyJSON]:
```


## Authzee Class

The `Authzee` class should take these arguments when created:
- JSON execute function
- Compute Module type and arguments
- Storage Module type and arguments

If the language supports async, there should also be an async version, `AuthzeeAsync`. 

These are the methods for the Authzee class.  For the `AuthzeeAsync` class, they should all be async.

```python
def start() -> None:
```
- Start up Authzee app.  
- Initialize runtime resources
- Needs to run before any methods or vars are accessed.
- Run the same method for compute and storage modules.
- After this method is complete these public instance vars or getters must be available:
    - locality - Authzee [Module Locality](#module-locality) to tell the limit of where other Authzee instances can be created.
    - parallel_paging_supported - if the instance of Authzee supports processing grant pages in parallel according to the compute and storage combination. 

```python
def shutdown() -> None:
```
- shutdown authzee app
- clean up runtime resources

```python
def setup() -> None:
```
- Construct backend resources for compute and storage
- one time setup 

```python
def teardown() -> None:
```
- tear down backend resources 
- destructive - may lose all storage and compute etc.


```python
def get_context_defs_page(
    page_ref: str | None, 
    page_size: int
) -> ContextDefinitionsPage:
```

```python
def get_context_def(context_type: str) -> ContextDefinition:
```

```python
def register_context_def(context_def: ContextDefinition) -> ContextDefinition:
```
- Add a new Context Definition

```python 
def update_context_def(context_def: ContextDefinition) -> ContextDefinition:
```
- Update a context def

```python
def delete_context_def(context_type: str) -> None:
```

```python
def get_identity_defs_page(
    page_ref: str | None, 
    page_size: int
) -> IdentityDefinitionsPage:
```

```python
def get_identity_def(identity_type: str) -> IdentityDefinition:
```

```python
def register_identity_def(identity_def: IdentityDefinition) -> IdentityDefinition:
```
- Add a new Identity Definition

```python 
def update_identity_def(identity_def: IdentityDefinition) -> IdentityDefinition:
```
- Update a identity def

```python
def delete_identity_def(identity_type: str) -> None:
```

```python
def get_resource_defs_page(
    page_ref: str | None, 
    page_size: int
) -> ResourceDefinitionsPage:
```

```python
def get_resource_def(resource_type: str) -> ResourceDefinition:
```

```python
def register_resource_def(resource_def: ResourceDefinition) -> ResourceDefinition:
```
- Add a new Resource Definition

```python 
def update_resource_def(resource_def: ResourceDefinition) -> ResourceDefinition:
```
- Update a resource def

```python
def delete_resource_def(resource_type: str) -> None:
```

```python
def enact(new_grant: NewGrant) -> Grant:
```
- add a new grant.

```python
def amend(grant: Grant) -> Grant:
```
- update a grant

```python
def repeal(grant_uuid: UUID) -> None:
```
- delete a grant.

```python
def get_grant(grant_uuid: UUID) -> Grant:
```
- Get a grant by UUID

```python
def get_grants_page(
    effect: str | None, 
    action: str | None, 
    page_ref: str | None, 
    grants_page_size: int
) -> GrantsPage:
```
- Retrieve a page of grants

```python
def get_grant_page_refs_page(
    effect: str | None, 
    action: str | None, 
    page_ref: str | None, 
    grants_page_size: int,
    refs_page_size: int
) -> PageRefsPage:
```
- Retrieve a page of grant page references for parallel pagination
- For some storage modules this may not be possible, check the `parallel_paging` value.

```python
def audit_page(
    request: AuthzeeRequest, 
    page_ref: str | None, 
    page_size: int, 
    parallel_paging: bool, 
    refs_page_size: int
) -> AuditPage:
```
- Run the Audit Operation for a page of results.
- Parallel pagination will send a whole page of grant page refs to be computed at a time which can help to cut down on latency between pages but may produce significantly more results.

```python
def authorize(
    request: AuthzeeRequest, 
    page_size: int, 
    grants_page_size: int, 
    refs_page_size: int
) -> AuthorizeResult:
```
- Run the Authorize Operation.

```python
def batch_audit_page(
    batch_request: AuthzeeBatchRequest, 
    page_ref: str | None, 
    page_size: int, 
    parallel_paging: bool, 
    refs_page_size: int
) -> BatchAuditPage:
```
- Run the Batch Audit Operation for a page of results.
- Parallel pagination will send a whole page of grant page refs to be computed at a time which can help to cut down on latency between pages but may produce significantly more results.

```python
def batch_authorize(
    batch_request: AuthzeeBatchRequest, 
    page_size: int, 
    grants_page_size: int, 
    refs_page_size: int
) -> BatchAuthorizeResult:
```
- Run the Batch Authorize Operation.


## Compute Modules

Compute modules provide a standard API for running operation on compute.  Compute Modules should not be used directly but through the Authzee class.
They have direct access to the storage module and use it to retrieve grants. 
They may also use the storage module to create and retrieve latches that help with compute state.  Especially for compute that is spread across multiple systems.
The compute modules are 

> **NOTE** - If the language supports async, then the compute module functions are expected to be async. Even if the underlying functionality is not async, this is to simplify the API between the `Authzee` app and the compute modules.  As well as avoid having to create a sync and async version of each compute module. 

Compute Modules should take any module specific arguments when created.

Compute modules objects should implement these methods:

```python
def start(
    execute: Callable[[str, Any], Any], 
    storage_type: Type[StorageModule], 
    storage_kwargs: Dict[str, Any]
) -> None:
```
- start up compute module
- run before use
- After this method is complete these public instance vars or getters must be available and stable:
    - locality - Compute [Module Locality](#module-locality) 
    - parallel_paging_supported - if the compute module supports processing grants with parallel paging

```python
def shutdown() -> None:
```
- shutdown compute module
- clean up runtime resources

```python
def setup() -> None:
```
- Construct backend resources for compute 
- one time setup 

```python
def teardown() -> None:
```
- tear down backend resources 
- destructive - may lose all long lasting compute resources


```python
def audit_page(
    request: AuthzeeRequest, 
    page_ref: str | None, 
    grants_page_size: int, 
    parallel_paging: bool, 
    refs_page_size: int
) -> AuditPage:
```
- Run the Audit operation for a page of results.
- Parallel pagination will send a whole page of grant page refs to be computed at a time which can help to cut down on latency between pages but may produce significantly more results.

```python
def authorize(
    request: AuthzeeRequest, 
    page_size: int, 
    grants_page_size: int, 
    refs_page_size: int
) -> AuthorizeResult:
```
- Run the Authorize operation.

```python
def batch_audit_page(
    batch_request: AuthzeeBatchRequest, 
    page_ref: str | None, 
    page_size: int, 
    parallel_paging: bool, 
    refs_page_size: int
) -> BatchAuditPage:
```
- Run the Batch Audit Operation for a page of results.
- Parallel pagination will send a whole page of grant page refs to be computed at a time which can help to cut down on latency between pages but may produce significantly more results.

```python
def batch_authorize(
    batch_request: AuthzeeBatchRequest, 
    page_size: int, 
    grants_page_size: int, 
    refs_page_size: int
) -> BatchAuthorizeResult:
```
- Run the Batch Authorize Operation.


## Storage Modules

Storage modules provide a standard API for storing and retrieving grants and [Storage Latches](#storage-latches). 

> **NOTE** - If the language supports async, then the storage module functions are expected to be async. Even if the underlying functionality is not async, this is to simplify the API between the pieces. 

Storage Modules should take any module specific arguments when created.

Storage modules should implement these methods:

```python
def start(
    identity_defs: List[IdentityDef], 
    resource_defs: List[ResourceDef]
) -> None:
```
- start up storage module
- run before use
- After this method is complete these public instance vars or getters must be available:
    - locality - Storage [Module Locality](#module-locality) 
    - parallel_paging_supported - if the storage modules supports parallel paging (returning a page of grant page references). 

```python
def shutdown() -> None:
```
- shutdown storage module
- clean up runtime resources

```python
def setup() -> None:
```
- Construct backend resources for storage 
- one time setup 

```python
def teardown() -> None:
```
- tear down backend resources 
- destructive - may lose all long lasting compute resources

```python
def get_identity_defs_page(
    page_ref: str | None, 
    page_size: int
) -> IdentityDefinitionsPage:
```

```python
def get_identity_def(identity_type: str) -> IdentityDefinition:
```

```python
def register_identity_def(identity_def: IdentityDefinition) -> IdentityDefinition:
```
- Add a new Identity Definition

```python 
def update_identity_def(identity_def: IdentityDefinition) -> IdentityDefinition:
```
- Update a identity def

```python
def delete_identity_def(identity_type: str) -> None:
```

```python
def get_resource_defs_page(
    page_ref: str | None, 
    page_size: int
) -> ResourceDefinitionsPage:
```

```python
def get_resource_def(resource_type: str) -> ResourceDefinition:
```

```python
def register_resource_def(resource_def: ResourceDefinition) -> ResourceDefinition:
```
- Add a new Resource Definition

```python 
def update_resource_def(resource_def: ResourceDefinition) -> ResourceDefinition:
```
- Update a resource def

```python
def delete_resource_def(resource_type: str) -> None:
```

```python
def enact(new_grant: NewGrant) -> Grant:
```
- add a new grant.

```python
def amend(grant: Grant) -> Grant:
```
- update a grant

```python
def repeal(grant_uuid: UUID) -> None:
```
- delete a grant.

```python
def get_grant(grant_uuid: UUID) -> Grant:
```
- Get a grant by UUID

```python
def get_grants_page(
    effect: str | None, 
    action: str | None, 
    page_ref: str | None,
    grants_page_size: int
) -> GrantsPage:
```
- get a page of grants

```python
def get_grant_page_refs_page(
    effect: str | None, 
    action: str | None, 
    page_ref: str | None, 
    grants_page_size: int,
    refs_page_size: int
) -> PageRefsPage:
```
- get a page of grant page references for parallel pagination
- For some storage modules this may not be possible, check the `parallel_paging` value.

```python
def create_latch() -> StorageLatch:
```
- Create a new [storage latch](#storage-latches) by UUID

```python
def get_latch(storage_latch_uuid) -> StorageLatch:
```
- Get a [storage latch](#storage-latches) by UUID

```python
def set_latch(storage_latch_uuid) -> StorageLatch:
```
- Set a [storage latch](#storage-latches) by UUID

```python
def delete_latch(storage_latch_uuid) -> None:
```
- Delete a [storage latch](#storage-latches) by UUID

```python
def cleanup_latches(before: Datetime) -> None:
```
- Delete all latches before the specified datetime.
- operations should clean up their own latches, but in case of a failure this can be used to clean up zombie latches.

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
- network - The module is localized to network connectivity with the Authzee app.
    - Compute resources are shared with systems that are reachable across the same network as the Authzee app.
    - Storage is shared with systems that are reachable across the same network as the Authzee app.
    - More precisely, the storage and compute is available over the network from all Authzee instances.

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

Compute modules may call on the storage module to create latches to manage the state of operations.  When compute is shared over the network this becomes a necessary piece to communicate different operation statuses.


## Standard Types

The input and output objects (data class instances, struct instances) should take a standard form when dealing with the Authzee class. The Authzee class provides the only public API to the SDKs, but the compute and storage classes are expected to provide consistent APIs to make compute and storage classes interchangeable. 

The SDKs build on some existing data structures from the spec and use some totally new.

Standard Types:
- [page_ref](#page_ref)
- [ContextDef](#context-def)
- [Grant](#grant)
- [NewGrant](#newgrant)
- [GrantsPage](#grantspage)
- [PageRefsPage](#pagerefspage)
- [AuthzeeRequest](#authzeerequest)
- [AuditPage](#auditpage)
- [AuthorizeResult](#authorizeresult)
- [AuthzeeBatchRequest](#authzeebatchrequest)
- [BatchAuditPage](#batchauditpage)
- [BatchAuthorizeResult](#batchauthorizeresult)

### page_ref

Authzee relies on pagination to make it's operations scalable. 
`page_ref` represents a string token to a specific page of resources.  To get the first page of a resource the `page_ref` should have a `null` value.  `next_ref` is present in results to be passed on the next function call to retrieve the next page.  When `next_ref` is a `null` value, the current page is considered the last and should not be passed back to the function.


### Grant

Grants should offer more flexibility over the reference implementation, and should be standard across the SDKs.

#### Grant Example

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
    "evaluation_handler": "evaluate",
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

#### Grant Schema


They should provide these additional fields over the [Grant Specification](./specification.md#grants), and they should also be available to query during runtime. 

| Field | Type | Required | Description |
|---|---|---|---|
| `grant_uuid` | string(UUID) | ✅ | UUID for the grant. |
| `name` | string |  ✅ | People friendly name for the grant |
| `description` | string |  ✅ | People friendly long description for the grant. |
| `tags` | object[string, string] | ✅ | Additional people metadata for the grant. An object whose keys and values are strings. |



### NewGrant

Used when creating a new grant.  The same as [Grant](#grant) without the `grant_uuid` field as that is generated by Authzee.

#### NewGrant Example


#### NewGrant Schema


### GrantsPage

A single page of [Grants](#grant).

#### GrantsPage Example

```json
{
    "grants": [],
    "next_ref": "abc123"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `grants` | array[Grant]| ✅ | The array of grants. |
| `next_ref` | string OR null |  ✅ | A token used to reference the next page of grants to retrieve from Authzee/the storage module. |

#### GrantsPage Schema

### PageRefsPage

A page of page references.

#### PageRefsPage Example

```json
{
    "page_refs": [
        "abc123"
    ],
    "next_ref": "def456"
}
```

#### PageRefsPage Schema

| Field | Type | Required | Description |
|---|---|---|---|
| `page_refs` | array[strings] | ✅ | An array of page references that can be used to retrieve several pages of a resource in parallel. |
| `next_ref` | string OR null |  ✅ | A token used to reference the next page of page refs to retrieve from Authzee/the storage module. |


### AuthzeeRequest

The standard "Request" object used to initiate an Authzee operation. Should match the [Authzee Request Specification](./specification.md#requests), where some fields are updated depending on the identity and resource defs.

#### AuthzeeRequest Example

#### AuthzeeRequest Schema




### AuditPage

A page of Audit operation results.  Conforms to the [Audit Operation Results](./specification.md#audit-operation-result), where some fields are updated depending on the identity and resource defs. It will also have a `next_ref` field for pagination. 

#### AuditPage Example

#### AuditPage Schema


### AuthorizeResult

The [Authorize operation Results](./specification.md#authorize-operation-result), which conforms to the Authzee specification, where some fields are updated depending on the identity and resource defs.

#### AuthorizeResult Example

#### AuthorizeResult Schema


### AuthzeeBatchRequest

The standard "Batch Request" object used to initiate an Authzee operation. Should match the [Authzee Request Specification](./specification.md#requests), where some fields are updated depending on the identity and resource defs.

#### AuthzeeBatchRequest Example

#### AuthzeeAuthzeeBatchRequestRequest Schema




### BatchAuditPage

A page of Audit operation results.  Conforms to the [Audit operation Results](./specification.md#audit-operation-result), where some fields are updated depending on the identity and resource defs. It will also have a `next_ref` field for pagination. 

#### BatchAuditPage Example

#### BatchAuditPage Schema


### BatchAuthorizeResult

The [Authorize operation Results](./specification.md#authorize-operation-result), which conforms to the Authzee specification, where some fields are updated depending on the identity and resource defs.

#### BatchAuthorizeResult Example

#### BatchAuthorizeResult Schema


## Standard JMESPath Extensions

JMESPath libraries offer the ability extend functionality by making new functions available in JMESPath queries. JMESPath is also the preferred JSON query language for Authzee.
Because of this, Authzee SDKs should also offer a set of out of the box JMESPath functions the are helpful to Authzee grant queries.

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
