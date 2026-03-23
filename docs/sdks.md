# Official Authzee SDKs

Authzee official SDKs offer the same general API's and architecture.
This makes it easier to switch languages by standardizing SDK patterns, and still leave room for language specific functionality and syntax. 

They offer a flexible and scalable general purpose interface, but they are opinionated in their APIs.  
If this doesn't fit your use case you are free to create your own! Try to stay compliant with the Authzee spec for the sake of portability.

> **NOTE** - This document is not a specification but a list of recommendations.  It may change and will not effect the specification or specification version of Authzee.


### Table of Contents

- [Example](#example)
- [Available SDKs](#available-sdks)
- [SDK Standards](#sdk-standards)
    - [Language Translations](#language-translations)
    - [Low Level API](#low-level-api)
    - [Authzee Class](#authzee-class)
    - [Compute Modules](#compute-modules)
    - [Storage Modules](#storage-modules)
    - [Module Locality](#module-locality)
    - [Storage Latches](#storage-latches)
    - [Handling Errors](#handling-errors)
    - [Standard Types](#standard-types)
- [SDK Full Example](#sdk-full-example)
- [Standard JMESPath Extensions](#standard-jmespath-extensions)
    - [INNER JOIN](#inner-join) TODO - Add other joins: left and outer
    - [regex Find](#regex-find)
    - [regex Find All](#regex-find-all)
    - [regex Groups](#regex-groups)
    - [regex Groups All](#regex-groups-all)

## Example


```python

from authzee import Authzee, InProcessCompute, InProcessStorage, jmespath_execute

storage = {}
authz = Authzee(
    execute=jmespath_execute,
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
authz.construct() # one time creation and setup of resources
# authz.destroy() # tear down all resources including runtime and non-volatile resources.  Destroys all grants and definitions.
authz.start() # initialization and creation of runtime resources.  Run for each Authzee instance
# authz.shutdown() # shutdown runtime resources for this Authzee instance
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

grant = authz.enact( # Create or update a grant and it will now be used when making authorization decisions. 
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
get_grant_refs_page() # get a page of references to grant pages.  Used for parallel pagination.  Only supported as available for storage backends
list_grants() # Auto paginate grants - if the language allows
# authz.repeal(grant['grant_uuid'], run_scan=False) # Repeal to delete a grant and it does not effect authorization any more. 

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
#     "next_page_ref": None
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
#     "next_page_ref": None
# }
```


## Available SDKs

SDKs are considered:
- **Authzee Compliant** - Follows the Authzee specification.
- **Maintained** - Actively maintained.
- **SDK Standard** - Follows the Authzee SDK standard.  It's not a bad thing if the library does not follow the standard.  You can expect a different interface than the official SDKs. 
- **Official** - Branded as the official Authzee SDK for a language. Again, not a bad thing if the library isn't official.

| Language | Code Repo | Package Repo | Authzee Compliant | Maintained | SDK Standard | Official | Notes |
|---|---|---|:---:|:---:|:---:|:---:|:---:|
| python | [btemplep/authzee-py](https://github.com/btemplep/authzee-py) | [authzee](https://pypi.org/project/authzee/) - pypi.org | ❌ | ✅ | ❌ | ✅ | In progress for updating to the new standard |

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

Under this object, the JSON query search function is static.
The Authzee object is created with a compute module and a storage module. The compute module will be used to provide the compute resources for running operations, and the storage module will be used to store and retrieve grants and other compute state objects. 

> **NOTE** - The Standard describes the minimum expectations of what an Authzee SDK should meet.  SDKs are welcome to have more functionality!!!

- [Language Translations](#language-translations)
- [Low Level API](#low-level-api)
- [Authzee Class](#authzee-class)
- [Compute Modules](#compute-modules)
- [Storage Modules](#storage-modules)
- [Module Locality](#module-locality)
- [Standard Types](#standard-types)
- [Storage Latches](#storage-latches)

### Language Translations

These docs will use python as the example language. For languages that don't support Classes and methods, translate as well as you can:
- Classes -> opaque struct definitions
- Class instances or objects -> struct instances
- Methods -> struct methods or functions that act on a struct 
 
Function/method parameter are expected to be able to grow for all methods/functions and for class/struct instantiation.  For languages that don't support all of these features like C and Rust:
- Authzee structs should be opaque and only created with a function
- All methods should accept the Authzee struct pointer, required params, and an opaque struct for optional and future arguments. 

In the examples, the most simple python types and data structures are given for clarity.  SDKs are free to change simple types like str to UUID.  They can also change complex types like dicts to structs, classes, data classes etc.  As long as they support adding fields without breaking the existing API. 


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
    grants: List[Dict[str, AnyJSON]]
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

```python
def evaluate_one(
    request: Dict[str, AnyJSON], 
    grant: Dict[str, AnyJSON],
    execute: Callable[[str, AnyJSON], AnyJSON],
    only_crits: bool
) -> Dict[str, AnyJSON]:
```

The `evaluate_one` function is for evaluating a request against one grant.
`only_crits` is a flag to only return critical errors.

```python
def audit(
    request: Dict[str, AnyJSON], 
    grants: List[Dict[str, AnyJSON]],
    execute: Callable[[str, AnyJSON], AnyJSON]
) -> Dict[str, List[Dict[str, AnyJSON]]]: 
```

> **NOTE** - `audit` and `authorize` functions do not run the validation steps before the core operation.

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

> **NOTE** - `batch_audit` and `batch_authorize` functions do not run the validation steps before the core operation.

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
- Compute Module type and arguments
    - keyword args where available, or else ordered arguments
- Storage Module type and arguments
    - keyword args where available, or else ordered arguments
- JSON query execute function
- [Authzee Config](#authzee-config) object or null to take defaults.

If the language supports async, there should also be an async version, `AuthzeeAsync`. 

These are the methods for the Authzee class.  For the `AuthzeeAsync` class, they should all be async.

```python
def start(self, config: AuthzeeConfig | None = None) -> GenericResult:
```
- Start up Authzee app.  
- Initialize runtime resources
- Needs to run before any methods or vars are accessed.
- Run the same method for compute and storage modules.
- After this method is complete these public instance vars or getters must be available:
    - locality - Authzee [Module Locality](#module-locality) to tell the limit of where other Authzee instances can be created.
    - parallel_paging_supported - if the instance of Authzee supports processing grant pages in parallel according to the compute and storage combination. 

```python
class Authzee:

    def __init__(
        self,
        execute: Callable[[str, Any], Any],
        compute_type: Type[ComputeModule],
        compute_kwargs: Dict[str, Any],
        storage_type: Type[StorageModule],
        storage_kwargs: Dict[str, Any]
    ):
        pass
```

```python
def shutdown(self, config: AuthzeeConfig | None = None) -> GenericResult:
```
- shutdown authzee app
- clean up runtime resources

```python
def construct(self, config: AuthzeeConfig | None = None) -> GenericResult:
```
- Construct backend resources for compute and storage
- one time setup 

```python
def destroy(self, config: AuthzeeConfig | None = None) -> GenericResult:
```
- tear down backend resources 
- destructive - may lose all storage and compute etc.


```python
def get_context_defs_page(self, config: AuthzeeConfig | None = None) -> ContextDefsPage:
```

```python
def get_context_def(
    self, 
    context_type: str, 
    config: AuthzeeConfig | None = None
) -> ContextDefResult:
```

```python
def list_context_defs(self, config: AuthzeeConfig | None = None) -> Iterable[ContextDef]:
```
- Auto-paginate context definitions - only included if the language supports it

```python
def put_context_def(
    self, 
    context_def: ContextDef, 
    config: AuthzeeConfig | None = None
) -> GenericResult:
```
- Add a new Context Definition or update an existing one

```python
def delete_context_def(
    self, 
    context_type: str, 
    config: AuthzeeConfig | None = None
) -> GenericResult:
```

```python
def get_identity_defs_page(self, config: AuthzeeConfig | None = None) -> IdentityDefsPage:
```

```python
def get_identity_def(
    self, 
    identity_type: str,
    config: AuthzeeConfig | None = None
) -> IdentityDefResult:
```

```python
def list_identity_defs(self, config: AuthzeeConfig | None = None) -> Iterable[IdentityDef]:
```
- Auto-paginate identity definitions - only included if the language supports it

```python
def put_identity_def(
    self, 
    identity_def: IdentityDef, 
    config: AuthzeeConfig | None = None
) -> GenericResult:
```
- Add a new Identity Definition or update an existing one

```python
def delete_identity_def(
    self, 
    identity_type: str,
    config: AuthzeeConfig | None = None
) -> GenericResult:
```

```python
def get_resource_defs_page(self, config: AuthzeeConfig | None = None) -> ResourceDefsPage:
```

```python
def get_resource_def(
    self, 
    resource_type: str,
    config: AuthzeeConfig | None = None
) -> ResourceDefResult:
```

```python
def list_resource_defs(self, config: AuthzeeConfig | None = None) -> Iterable[ResourceDef]:
```
- Auto-paginate resource definitions - only included if the language supports it

```python
def put_resource_def(
    self, 
    resource_def: ResourceDef,
    config: AuthzeeConfig | None = None
) -> GenericResult:
```
- Add a new Resource Definition or update an existing one

```python
def delete_resource_def(
    self, 
    resource_type: str,
    config: AuthzeeConfig | None = None
) -> GenericResult:
```

```python
def enact(
    self, 
    grant: Grant,
    config: AuthzeeConfig | None = None
) -> GenericResult:
```
- add a new grant. 

> **NOTE** - For scalability, grants should only be created and destroyed.  Storage modules may do their best to check if a grant UUID exists, but may not always be correct.  Only ever put in new UUIDs, not ones known to exist.

```python
def repeal(
    self, 
    grant_uuid: str, 
    run_scan: bool,
    config: AuthzeeConfig | None = None
) -> GenericResult:
```

- delete a grant. 
- `run_scan` will scan all grant partitions.  Slower but can be used to clean up corrupted grants.

```python
def get_grant(
    self, 
    grant_uuid: str,
    config: AuthzeeConfig | None = None
) -> GrantResult:
```
- Get a grant by UUID

```python
def get_grants_page(
    self,
    effect: str | None, 
    action: str | None, 
    page_ref: str | None, 
    config: AuthzeeConfig | None = None
) -> GrantsPage:
```
- Retrieve a page of grants

```python
def get_grant_refs_page(
    self,
    effect: str | None, 
    action: str | None, 
    page_ref: str | None, 
    config: AuthzeeConfig | None = None
) -> PageRefsPage:
```
- Retrieve a page of grant page references for parallel pagination
- For some storage modules this may not be possible, check the `parallel_paging` value.

```python
def audit_page(
    self,
    request: AuthzeeRequest, 
    page_ref: str | None, 
    config: AuthzeeConfig | None = None
) -> AuditPage:
```
- Run the Audit Operation for a page of results.

```python
def authorize(
    self, 
    request: AuthzeeRequest,
    config: AuthzeeConfig | None = None
) -> AuthorizeResult:
```
- Run the Authorize Operation.

```python
def batch_audit_page(
    self,
    batch_request: AuthzeeBatchRequest, 
    page_ref: str | None, 
    config: AuthzeeConfig | None = None
) -> BatchAuditPage:
```
- Run the Batch Audit Operation for a page of results.
- Parallel pagination will send a whole page of grant page refs to be computed at a time which can help to cut down on latency between pages but may produce significantly more results.

```python
def batch_authorize(
    self, 
    batch_request: AuthzeeBatchRequest,
    config: AuthzeeConfig | None = None
) -> BatchAuthorizeResult:
```
- Run the Batch Authorize Operation.


## Compute Modules

Compute modules provide a standard API for running operation on compute.  Compute Modules should not be used directly but through the Authzee class.
They have direct access to the storage module and use it to retrieve grants. 
They may also use the storage module to create and retrieve latches that help with compute state.  Especially for compute that is spread across multiple systems.

> **NOTE** - If the language supports async, then the compute module functions are expected to be async. Even if the underlying functionality is not async, this is to simplify the API between the `Authzee` app and the compute modules.  As well as avoid having to create a sync and async version of each compute module. 

Compute Modules should take any module specific arguments when created.

Compute modules objects should implement these methods:

```python
def start(
    self,
    execute: Callable[[str, Any], Any], 
    storage_type: Type[StorageModule], 
    storage_kwargs: Dict[str, Any]
) -> GenericResult:
```
- start up compute module
- run before use
- After this method is complete these public instance vars or getters must be available and stable:
    - locality - Compute [Module Locality](#module-locality) 
    - parallel_paging_supported - if the compute module supports processing grants with parallel paging

```python
def shutdown(self) -> GenericResult:
```
- shutdown compute module
- clean up runtime resources

```python
def construct(self) -> GenericResult:
```
- Construct backend resources for compute 
- one time setup 

```python
def destroy(self) -> GenericResult:
```
- tear down backend resources 
- destructive - may lose all long lasting compute resources


```python
def validate_context_def(
    self,
    context_def: ContextDef,
    page_size: int
) -> GenericResult:
```

```python
def validate_identity_def(
    self,
    identity_def: IdentityDef,
    page_size: int) -> GenericResult:
```

```python
def validate_resource_def(
    self,
    resource_def: ResourceDef,
    page_size: int
) -> GenericResult:
```

```python
def validate_request(
    self,
    request: AuthzeeRequest,
    page_size: int
) -> GenericResult:
```

```python
def validate_batch_request(
    self,
    batch_request: AuthzeeBatchRequest,
    page_size: int
) -> GenericResult
```

```python
def audit_page(
    self,
    request: AuthzeeRequest, 
    page_ref: str | None, 
    page_size: int
) -> AuditPage:
```

```python
def authorize(
    self,
    request: AuthzeeRequest, 
    page_size: int, 
    parallel_pagination: bool,
    refs_page_size: int
) -> AuthorizeResult:
```

```python
def batch_audit_page(
    self,
    batch_request: AuthzeeBatchRequest, 
    page_ref: str | None, 
    page_size: int
) -> BatchAuditPage:
```

```python
def batch_authorize(
    self,
    batch_request: AuthzeeBatchRequest,
    page_size: int, 
    parallel_pagination: bool,
    refs_page_size: int
) -> BatchAuthorizeResult:
```


## Storage Modules

Storage modules provide a standard API for storing and retrieving grants and [Storage Latches](#storage-latches). 

> **NOTE** - If the language supports async, then the storage module functions are expected to be async. Even if the underlying functionality is not async, this is to simplify the API between the pieces. 

Storage Modules should take any module specific arguments when created.

Storage modules should implement these methods:

```python
def start(self) -> GenericResult:
```
- start up storage module
- run before use
- After this method is complete these public instance vars or getters must be available:
    - locality - Storage [Module Locality](#module-locality) 
    - parallel_paging_supported - if the storage modules supports parallel paging (returning a page of grant page references). 

```python
def shutdown(self) -> GenericResult:
```
- shutdown storage module
- clean up runtime resources

```python
def construct(self) -> GenericResult:
```
- Construct backend resources for storage 
- one time setup 

```python
def destroy(self) -> GenericResult:
```
- tear down backend resources 
- destructive - may lose all long lasting compute resources


```python
def get_context_defs_page(
    self,
    page_ref: str | None, 
    page_size: int
) -> ContextDefsPage:
```

```python
def get_context_def(self, context_type: str) -> ContextDefResult:
```

```python
def put_context_def(self, context_def: ContextDef) -> GenericResult:
```
- Add a new Context Definition or update an existing one

```python
def delete_context_def(self, context_type: str) -> GenericResult:
```

```python
def get_identity_defs_page(
    self,
    page_ref: str | None, 
    page_size: int
) -> IdentityDefsPage:
```

```python
def get_identity_def(self, identity_type: str) -> IdentityDefResult:
```

```python
def put_identity_def(self, identity_def: IdentityDef) -> GenericResult:
```
- Add a new Identity Definition or update an existing one

```python
def delete_identity_def(self, identity_type: str) -> GenericResult:
```

```python
def get_resource_defs_page(
    self,
    page_ref: str | None, 
    page_size: int
) -> ResourceDefsPage:
```

```python
def get_resource_def(self, resource_type: str) -> ResourceDef:
```

```python
def list_resource_defs(self, page_size: int) -> Iterable[ResourceDef]:
```
- Auto-paginate resource definitions - only included if the language supports it

```python
def put_resource_def(self, resource_def: ResourceDef) -> ResourceDef:
```
- Add a new Resource Definition or update an existing one

```python
def delete_resource_def(self, resource_type: str) -> None:
```

```python
def enact(self, grant: Grant) -> GenericResult:
```
- add a new grant.


```python
def repeal(self, grant_uuid: str) -> GenericResult:
```
- delete a grant.

```python
def get_grant(self, grant_uuid: str) -> GrantResult:
```
- Get a grant by UUID

```python
def get_grants_page(
    self,
    effect: str | None, 
    action: str | None, 
    page_ref: str | None, 
    grants_page_size: int
) -> GrantsPage:
```
- Retrieve a page of grants

```python
def get_grant_refs_page(
    self,
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
def create_latch(self) -> StorageLatchResult:
```
- Create a new [storage latch](#storage-latches) by UUID

```python
def get_latch(self, storage_latch_uuid: str) -> StorageLatchResult:
```
- Get a [storage latch](#storage-latches) by UUID

```python
def set_latch(self, storage_latch_uuid: str) -> StorageLatchResult:
```
- Set a [storage latch](#storage-latches) by UUID

```python
def delete_latch(self, storage_latch_uuid: str) -> GenericResult:
```
- Delete a [storage latch](#storage-latches) by UUID

```python
def cleanup_latches(self, before: Datetime) -> GenericResult:
```
- Delete all latches before the specified datetime.
- operations should clean up their own latches, but in case of a failure this can be used to clean up zombie latches.

> **NOTE** - When listing grants there are 2 filters: `effect` and `action`.  Storage modules should partition grants on these 2 fields if they can.

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


## Handling Errors

The SDK should return normalized results for all operations that include any errors in the results. 

If the Language supports exceptions, then the Authzee Class should support the ability to raise critical errors as exceptions. 

Exceptions should provide a general message and the result of the function with all errors. 


### Exception Hierarchy

If the language support exception hierarchies it should be as follows:

- root exception for Authzee.  
    - Authzee Specification Exception
        - Definition Specification Error
        - Grant Specification Error
        - Request Specification Error
        - Evaluation Specification Error
    - Authzee SDK Exception
        - SDKs are free to implement any other exceptions as needed.  Try to denote that they are SDK exceptions if it makes sense.


## Standard Types

The input and output objects (data class instances, struct instances) should take a standard form when dealing with the Authzee class. The Authzee class provides the only public API to the SDKs, but the compute and storage classes are expected to provide consistent APIs to make compute and storage classes interchangeable. 

The SDKs build on some existing data structures from the spec and use some totally new.

Standard Types:
- [AuthzeeConfig](#authzeeconfig)
- [page_ref](#page_ref)
- [GenericResult and *Results](#genericresult-and-results)
- [Page Results](#page-results)
- [Grant](#grant)
- [AuthzeeRequest](#authzeerequest)
- [AuditPage](#auditpage)
- [AuthorizeResult](#authorizeresult)
- [AuthzeeBatchRequest](#authzeebatchrequest)
- [BatchAuditPage](#batchauditpage)
- [BatchAuthorizeResult](#batchauthorizeresult)


### AuthzeeConfig

The authzee config object is used to configure default settings at the class instantiation level and to override settings at the function level. 

These settings should be universal for all compute and storage and should not contain specific settings for the compute and storage.  


#### AuthzeeConfig Example

```json
{
    "definitions_page_size": 100,
    "grants_page_size": 100,
    "grant_refs_page_size": 10,
    "authorize_parallel_paging": true,
    "batch_authorize_parallel_paging": true,
    "raise_crits": true
}
```


#### AuthzeeConfig Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "AuthzeeConfig",
    "description": "An object representing the default configs for an Authzee instance, or override parameters for Authzee functions.",
    "type": "object",
    "additionalProperties": true,
    "required": [
        "definitions_page_size",
        "grants_page_size",
        "grant_refs_page_size",
        "authorize_parallel_paging",
        "batch_authorize_parallel_paging",
        "raise_crits"
    ],
    "properties": {
        "definitions_page_size": {
            "type": "integer",
            "description": "Max number of definitions to return when retrieving a page of context, identity, or resource definitions."
        },
        "grants_page_size": {
            "type": "integer",
            "description": "Max number of grants to return when retrieving a page of grants"
        },
        "grant_refs_page_size": {
            "type": "integer",
            "description": "Max number of references to grant pages to return when retrieving a page of grant references."
        },
        "authorize_parallel_paging": {
            "type": "boolean",
            "description": "Use parallel pagination if it is available for the authorize operation."
        },
        "batch_authorize_parallel_paging": {
            "type": "boolean",
            "description": "Use parallel pagination if it is available for the batch authorize operation."
        },
        "raise_crits": {
            "type": "boolean",
            "description": "Raise critical errors as an exception if available in the language."
        }
    }
}
```

### page_ref

Authzee relies on pagination to make its operations scalable. 
`page_ref` represents a string token to a specific page of resources. This string should be Base 64 encoded and ideally opaque to the backend resources.  To get the first page of a resource the `page_ref` should have a `null` value.  `next_page_ref` is present in results to be passed in the following function call to retrieve the next page.  When `next_page_ref` is a `null` value, the current page is considered the last and should not be passed back to the function.


### GenericResult and *Results

`GenericResult` simply returns if the function has failed and any associated errors.  
Types from Authzee that are prefixed with `Result` are simply that type nested in an object with fields in `GenericResult` as well.

Example structure for Grant:

```json
{
    "grant": {}, // grant or null
    "has_failed": false,
    "errors": {}
}
```

The results should use these field names:

- `Grant` -> `grant`
- `ContextDef` -> `context_def`
- `IdentityDef` -> `identity_def`
- `ResourceDef` -> `resource_def`

#### GenericResult Example

```json
{
    "has_failed": false,
    "errors": {}
}
```

#### GenericResult Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "GenericResult",
    "description": "An object representing the a result from an authzee function.",
    "type": "object",
    "additionalProperties": true,
    "required": [
        "has_failed",
        "errors"
    ],
    "properties": {
        "has_failed": {
            "type": "boolean",
            "description": "If the request has failed from a critical error or not."
        },
        "errors": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "generic results errors",
            "description": "Errors returned running and Authzee function. SDK errors should be prefixed with 'sdk_' and only have one field 'message' that is a string describing the error.",
            "type": "object",
            "additionalProperties": true,
            "required": [],
            "properties": {}
        }
    }
}
```

### Page Results

Authzee supplies several resources that are paginated including: grants, context definitions, identity definitions, resource definitions, and page references. 

Each of these has generalized paged results that will contain a field for the list of items, as well `next_page_ref` and the fields from [GenericResult](#genericresult-and-results). 

GrantsPage Example:

```json
{
    "grants": [], // list of grants" or null if error
    "next_page_ref": "asdfds", // token or null
    "has_failed": false,
    "errors": {}
}
```

Mapping of resource pages to field containing items: 
- `GrantsPage` -> `grants`
- `ContextDefsPage` -> `context_defs`    
- `IdentityDefsPage` -> `identity_defs`  
- `ResourceDefsPage` -> `resource_defs`
- `PageRefsPage` -> `page_refs`


### Grant

Grants should offer more flexibility over the reference implementation, and should be standard across the SDKs.

In the SDK standard, grants are an immutable resource.  They can only be enacted(created) or repealed(destroyed).
This is a purposeful limitation to enable better scaling of grants. 


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
    }
}
```

#### Grant Schema


They should provide these additional fields over the [Grant Specification](./specification.md#grants), and they should also be available to query during runtime. 

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Grant",
    "description": "A grant is an object representing enacted authorization rules.",
    "type": "object",
    "additionalProperties": true,
    "required": [
        "grant_uuid",
        "name",
        "description",
        "tags",
        "effect",
        "actions",
        "data",
        "query",
        "evaluation_handler",
        "equality"
    ],
    "properties": {
        "grant_uuid": {
            "type": "string",
            "format": "uuid"
        },
        "name": {
            "type": "string",
            "description": "Short name for the grant"
        },
        "description": {
            "type": "string",
            "description": "Longer description for the grant "
        },
        "tags": {
            "type": "object",
            "description": "General purpose Key/Value pairs for categorization.",
            "patternProperties": {
                "^[A-Za-z0-9_]*$": {
                    "type": "string"
                }
            }
        },
        "effect": {
            "type": "string",
            "enum": [
                "allow",
                "deny"
            ],
            "description": "Any applicable deny grant will always cause the request to be unauthorized. If there are no applicable deny grants, and there is an applicable allow grant, the request is authorized. If there no applicable allow or deny grants, requests are implicitly denied and is not authorized."
        },
        "actions": {
            "type": "array",
            "uniqueItems": true,
            "items": {
                "title": "Resource Action",
                "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common, or more general 'Namespace:Action' pattern.",
                "type": "string",
                "pattern": "^[A-Za-z0-9_.:-]*$",
                "minLength": 1,
                "maxLength": 512
            },
            "description": "List of actions this grant applies to or null to match any resource action."
        },
        "data": {
            "type": "object",
            "description": "Data that is made available at query time for the grant evaluation. Easy place to store data so it doesn't have to be embedded in the query."
        },
        "query": {
            "type": "string",
            "description": "JSON query to run on the authorization data. {\"grant\": <grant>, \"request\": <request>}"
        },
        "evaluation_handler": {
            "title": "Grant-Level Evaluation Handler Setting",
            "description": "Set how evaluation errors are handled.'evaluate' - Evaluation is run and any errors cause the grant to be inapplicable to the request, but are not included in the result.'error' - Includes the 'validate' setting checks, and also includes errors in the result. 'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the Authzee Operation early.",
            "type": "string",
            "enum": [
                "evaluate",
                "error",
                "critical"
            ]
        },
        "equality": {
            "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
        }
    }
}
```


### Storage Latches

Storage latches are flag like objects kept in the storage module. 
Storage latches can only be created, set, or deleted. 
They cannot be unset or otherwise mutated.

Compute modules may call on the storage module to create latches to manage the state of operations.  When compute is shared over the network this becomes a necessary piece to communicate different operation statuses.


#### Storage Latch Example

```json
{
    "storage_latch_uuid": "7fa89195-d455-444c-ad53-9f1c66a0fc85",
    "is_set": false,
    "created_at": "2025-07-20T04:13:17.292144Z"
}
```


#### Storage Latch Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "StorageLatch",
    "description": "An object representing a latch held in the storage module.",
    "type": "object",
    "additionalProperties": true,
    "required": [
        "storage_latch_uuid",
        "is_set",
        "created_at"
    ],
    "properties": {
        "storage_latch_uuid": {
            "type": "string",
            "format": "uuid"
        },
        "is_set": {
            "type": "boolean",
            "description": "Is the latch set or not"
        },
        "created_at": {
            "type": "string",
            "format": "date-time"
        }
    }
}
```


### AuthzeeRequest

The standard "Request" object used to initiate an Authzee operation. Should match the [Authzee Request Specification](./specification.md#requests).


### AuditPage

A page of Audit operation results.  Conforms to the [Audit Operation Results](./specification.md#audit). It will also have a `next_page_ref` field for pagination, and updated fields for grants. 


#### AuditPage Example

```json
{
    "grants": [
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
            }
        }
    ],
    "results": [
        {
            "is_applicable": true,
            "query_result": true,
            "errors": {}
        }
    ],
    "next_page_ref": "abc123",
    "has_failed": false,
    "errors": {}
}
```

#### AuditPage Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Audit Result",
    "description": "Result for the audit operation.",
    "type": "object",
    "additionalProperties": true,
    "required": [
        "grants",
        "results",
        "next_page_ref",
        "has_failed",
        "errors"
    ],
    "properties": {
        "grants": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "grant_uuid",
                    "name",
                    "description",
                    "tags",
                    "effect",
                    "actions",
                    "data",
                    "query",
                    "evaluation_handler",
                    "equality"
                ],
                "properties": {
                    "grant_uuid": {
                        "type": "string",
                        "format": "uuid"
                    },
                    "name": {
                        "type": "string",
                        "description": "Short name for the grant"
                    },
                    "description": {
                        "type": "string",
                        "description": "Longer description for the grant "
                    },
                    "tags": {
                        "type": "object",
                        "description": "General purpose Key/Value pairs for categorization.",
                        "patternProperties": {
                            "^[A-Za-z0-9_]*$": {
                                "type": "string"
                            }
                        }
                    },
                    "effect": {
                        "type": "string",
                        "enum": [
                            "allow",
                            "deny"
                        ],
                        "description": "Any applicable deny grant will always cause the request to be unauthorized. If there are no applicable deny grants, and there is an applicable allow grant, the request is authorized. If there no applicable allow or deny grants, requests are implicitly denied and is not authorized."
                    },
                    "actions": {
                        "type": "array",
                        "uniqueItems": true,
                        "items": {
                            "title": "Resource Action",
                            "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common, or more general 'Namespace:Action' pattern.",
                            "type": "string",
                            "pattern": "^[A-Za-z0-9_.:-]*$",
                            "minLength": 1,
                            "maxLength": 512
                        },
                        "description": "List of actions this grant applies to or null to match any resource action."
                    },
                    "data": {
                        "type": "object",
                        "description": "Data that is made available at query time for the grant evaluation. Easy place to store data so it doesn't have to be embedded in the query."
                    },
                    "query": {
                        "type": "string",
                        "description": "JSON query to run on the authorization data. {\"grant\": <grant>, \"request\": <request>}"
                    },
                    "evaluation_handler": {
                        "title": "Grant-Level Evaluation Handler Setting",
                        "description": "Set how evaluation errors are handled.'evaluate' - Evaluation is run and any errors cause the grant to be inapplicable to the request, but are not included in the result.'error' - Includes the 'validate' setting checks, and also includes errors in the result. 'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the Authzee Operation early.",
                        "type": "string",
                        "enum": [
                            "evaluate",
                            "error",
                            "critical"
                        ]
                    },
                    "equality": {
                        "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
                    }
                }

            }
        },
        "results": {
            "type": "array",
            "description": "List of grant evaluation results for each respective grant index.",
            "items": {
                "type": "object",
                "additionalProperties": true,
                "required": [
                    "is_applicable",
                    "query_result",
                    "errors"
                ],
                "properties": {
                    "is_applicable": {
                        "type": "boolean",
                        "description": "If the grant is applicable to the request or not."
                    },
                    "query_result": {
                        "description": "Result from running the JSON query."
                    },
                    "errors": {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "title": "Operation Result Errors",
                        "description": "Errors returned from Authzee Operations.",
                        "type": "object",
                        "additionalProperties": false,
                        "required": [],
                        "properties": {
                            "query": {
                                "type": "array",
                                "items": {
                                    "title": "Query Error",
                                    "description": "Error when a JSON query fails.",
                                    "type": "object",
                                    "additionalProperties": true,
                                    "required": [
                                        "is_critical",
                                        "message"
                                    ],
                                    "properties": {
                                        "is_critical": {
                                            "type": "boolean",
                                            "description": "If this error is critical. Critical errors generally halt further operations."
                                        },
                                        "message": {
                                            "type": "string",
                                            "description": "Detailed message about what caused the error."
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "next_page_ref": {
            "type": "string", 
            "description": "Used to retrieve the next page of audit results",
            "contentEncoding": "base64"

        },
        "has_failed": {
            "type": "boolean",
            "description": "If the request has failed from a critical error or not."
        },
        "errors": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Operation Result Errors",
            "description": "Errors returned from Authzee Operations. SDK errors should be prefixed with 'sdk_' and only have one field 'message' that is a string describing the error",
            "type": "object",
            "additionalProperties": true,
            "required": [],
            "properties": {
                "query": {
                    "type": "array",
                    "items": {
                        "title": "Query Error",
                        "description": "Error when a JSON query fails.",
                        "type": "object",
                        "additionalProperties": true,
                        "required": [
                            "is_critical",
                            "message"
                        ],
                        "properties": {
                            "is_critical": {
                                "type": "boolean",
                                "description": "If this error is critical. Critical errors generally halt further operations."
                            },
                            "message": {
                                "type": "string",
                                "description": "Detailed message about what caused the error."
                            }
                        }
                    }
                }
            }
        }
    }
}
```


### AuthorizeResult

The standard [Authorize operation Results](./specification.md#authorize) are returned with updated fields for grants.


#### AuthorizeResult Example

```json
{
    "grant_uuid": "6ce44005-8735-45ac-ae76-38e22e66f615",
    "name": "My grant name",
    "description": "Longer description here to explain what the grant is for.",
    "tags": {
        "some_key": "some_val"
    },
    "is_authorized": true,
    "grant": {
        "effect": "allow",
        "actions": [
            "Balloon:Read",
            "pop"
        ],
        "query": "contains(request.identities.User[0].role, 'admin')",
        "evaluation_handler": "evaluate",
        "equality": true,
        "data": {}
    },
    "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
    "has_failed": false,
    "critical_errors": {}
}
```

#### Authorize Result Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Authorize Result",
    "description": "Result for the authorize operation.",
    "type": "object",
    "additionalProperties": true,
    "required": [
        "is_authorized",
        "grant",
        "message",
        "has_failed",
        "critical_errors"
    ],
    "properties": {
        "is_authorized": {
            "type": "boolean",
            "description": "true if the request is authorized.  false if it is not authorized."
        },
        "grant": {
            "description": "Grant that was responsible for the authorization decision, if applicable.",
            "anyOf": [
                {
                    "type": "null",
                    "description": "No grant was involved in the authorization decision."
                },
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "title": "Grant",
                    "description": "A grant is an object representing enacted authorization rules.",
                    "type": "object",
                    "additionalProperties": true,
                    "required": [
                        "grant_uuid",
                        "name",
                        "description",
                        "tags",
                        "effect",
                        "actions",
                        "data",
                        "query",
                        "evaluation_handler",
                        "equality"
                    ],
                    "properties": {
                        "grant_uuid": {
                            "type": "string",
                            "format": "uuid"
                        },
                        "name": {
                            "type": "string",
                            "description": "Short name for the grant"
                        },
                        "description": {
                            "type": "string",
                            "description": "Longer description for the grant "
                        },
                        "tags": {
                            "type": "object",
                            "description": "General purpose Key/Value pairs for categorization.",
                            "patternProperties": {
                                "^[A-Za-z0-9_]*$": {
                                    "type": "string"
                                }
                            }
                        },
                        "effect": {
                            "type": "string",
                            "enum": [
                                "allow",
                                "deny"
                            ],
                            "description": "Any applicable deny grant will always cause the request to be unauthorized. If there are no applicable deny grants, and there is an applicable allow grant, the request is authorized. If there no applicable allow or deny grants, requests are implicitly denied and is not authorized."
                        },
                        "actions": {
                            "type": "array",
                            "uniqueItems": true,
                            "items": {
                                "title": "Resource Action",
                                "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common, or more general 'Namespace:Action' pattern.",
                                "type": "string",
                                "pattern": "^[A-Za-z0-9_.:-]*$",
                                "minLength": 1,
                                "maxLength": 512
                            },
                            "description": "List of actions this grant applies to or null to match any resource action."
                        },
                        "data": {
                            "type": "object",
                            "description": "Data that is made available at query time for the grant evaluation. Easy place to store data so it doesn't have to be embedded in the query."
                        },
                        "query": {
                            "type": "string",
                            "description": "JSON query to run on the authorization data. {\"grant\": <grant>, \"request\": <request>}"
                        },
                        "evaluation_handler": {
                            "title": "Grant-Level Evaluation Handler Setting",
                            "description": "Set how evaluation errors are handled.'evaluate' - Evaluation is run and any errors cause the grant to be inapplicable to the request, but are not included in the result.'error' - Includes the 'validate' setting checks, and also includes errors in the result. 'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the Authzee Operation early.",
                            "type": "string",
                            "enum": [
                                "evaluate",
                                "error",
                                "critical"
                            ]
                        },
                        "equality": {
                            "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
                        }
                    }
                }
            ]
        },
        "message": {
            "type": "string",
            "description": "Details about why the request was authorized or not.",
            "enum": [
                "A critical error has occurred. Therefore, the request is not authorized.",
                "A deny grant is applicable to the request. Therefore, the request is not authorized.",
                "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
                "No grants are applicable to the request. Therefore, the request is implicitly denied and is not authorized."
            ]
        },
        "has_failed": {
            "type": "boolean",
            "description": "If the request has failed from a critical error or not."
        },
        "critical_errors": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Operation Result Errors",
            "description": "Errors returned from Authzee Operations. SDK errors should be prefixed with 'sdk_' and only have one field 'message' that is a string describing the error",
            "type": "object",
            "additionalProperties": true,
            "required": [],
            "properties": {
                "query": {
                    "type": "array",
                    "items": {
                        "title": "Query Error",
                        "description": "Error when a JSON query fails.",
                        "type": "object",
                        "additionalProperties": true,
                        "required": [
                            "is_critical",
                            "message"
                        ],
                        "properties": {
                            "is_critical": {
                                "type": "boolean",
                                "description": "If this error is critical. Critical errors generally halt further operations."
                            },
                            "message": {
                                "type": "string",
                                "description": "Detailed message about what caused the error."
                            }
                        }
                    }
                }
            }
        }
    }
}
```

### AuthzeeBatchRequest

The standard "Batch Request" object used to initiate an Authzee operation. Should match the [Authzee Request Specification](./specification.md#requests).


### BatchAuditPage

A page of Audit operation results.  Conforms to the [Audit operation Results](./specification.md#audit-operation-result), where some fields are updated depending on the identity and resource defs. It will also have a `next_page_ref` field for pagination. 

#### BatchAuditPage Example


```json
{
    "grants": [
        {
            "grant_uuid": "6ce44005-8735-45ac-ae76-38e22e66f615",
            "name": "My grant name",
            "description": "Longer description here to explain what the grant is for.",
            "tags": {
                "some_key": "some_val"
            },
            "effect": "allow",
            "actions": [
                "inflate"
            ],
            "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
            "evaluation_handler": "error",
            "equality": true,
            "data": {}
        }
    ],
    "batch_results": [
        {
            "results": [
                {
                    "is_applicable": true,
                    "query_result": true,
                    "errors": {}
                }
            ],
            "has_failed": false,
            "errors": {}
        }
    ],
    "next_page_ref": "def456", 
    "has_failed": false,
    "errors": {}
}
```

#### BatchAuditPage Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Batch Audit Result",
    "description": "Result for the Batch Audit Operation.",
    "type": "object",
    "additionalProperties": true,
    "required": [
        "grants",
        "batch_results",
        "next_page_ref",
        "has_failed",
        "errors"
    ],
    "properties": {
        "grants": {
            "type": "array",
            "description": "List of grants that have been processed for the request.",
            "items": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "Grant",
                "description": "A grant is an object representing enacted authorization rules.",
                "type": "object",
                "additionalProperties": true,
                "required": [
                    "grant_uuid",
                    "name",
                    "description",
                    "tags",
                    "effect",
                    "actions",
                    "data",
                    "query",
                    "evaluation_handler",
                    "equality"
                ],
                "properties": {
                    "grant_uuid": {
                        "type": "string",
                        "format": "uuid"
                    },
                    "name": {
                        "type": "string",
                        "description": "Short name for the grant"
                    },
                    "description": {
                        "type": "string",
                        "description": "Longer description for the grant "
                    },
                    "tags": {
                        "type": "object",
                        "description": "General purpose Key/Value pairs for categorization.",
                        "patternProperties": {
                            "^[A-Za-z0-9_]*$": {
                                "type": "string"
                            }
                        }
                    },
                    "effect": {
                        "type": "string",
                        "enum": [
                            "allow",
                            "deny"
                        ],
                        "description": "Any applicable deny grant will always cause the request to be unauthorized. If there are no applicable deny grants, and there is an applicable allow grant, the request is authorized. If there no applicable allow or deny grants, requests are implicitly denied and is not authorized."
                    },
                    "actions": {
                        "type": "array",
                        "uniqueItems": true,
                        "items": {
                            "title": "Resource Action",
                            "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common, or more general 'Namespace:Action' pattern.",
                            "type": "string",
                            "pattern": "^[A-Za-z0-9_.:-]*$",
                            "minLength": 1,
                            "maxLength": 512
                        },
                        "description": "List of actions this grant applies to or null to match any resource action."
                    },
                    "data": {
                        "type": "object",
                        "description": "Data that is made available at query time for the grant evaluation. Easy place to store data so it doesn't have to be embedded in the query."
                    },
                    "query": {
                        "type": "string",
                        "description": "JSON query to run on the authorization data. {\"grant\": <grant>, \"request\": <request>}"
                    },
                    "evaluation_handler": {
                        "title": "Grant-Level Evaluation Handler Setting",
                        "description": "Set how evaluation errors are handled.'evaluate' - Evaluation is run and any errors cause the grant to be inapplicable to the request, but are not included in the result.'error' - Includes the 'validate' setting checks, and also includes errors in the result. 'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the Authzee Operation early.",
                        "type": "string",
                        "enum": [
                            "evaluate",
                            "error",
                            "critical"
                        ]
                    },
                    "equality": {
                        "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
                    }
                }
            }
        },
        "batch_results": {
            "type": "array",
            "description": "Array of results from a batch request. Each result corresponds to the batch request item of the same index.",
            "items": {
                "type": "object",
                "description": "Audit batch item result.",
                "additionalProperties": true,
                "required": [
                    "results",
                    "has_failed",
                    "errors"
                ],
                "properties": {
                    "results": {
                        "type": "array",
                        "description": "List of grant evaluation results for each respective grant index.",
                        "items": {
                            "type": "object",
                            "additionalProperties": true,
                            "required": [
                                "is_applicable",
                                "query_result",
                                "errors"
                            ],
                            "properties": {
                                "is_applicable": {
                                    "type": "boolean",
                                    "description": "If the grant is applicable to the request or not."
                                },
                                "query_result": {
                                    "description": "Result from running the JSON query."
                                },
                                "errors": {
                                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                                    "title": "Operation Result Errors",
                                    "description": "Errors returned from Authzee Operations.",
                                    "type": "object",
                                    "additionalProperties": false,
                                    "required": [],
                                    "properties": {
                                        "query": {
                                            "type": "array",
                                            "items": {
                                                "title": "Query Error",
                                                "description": "Error when a JSON query fails.",
                                                "type": "object",
                                                "additionalProperties": true,
                                                "required": [
                                                    "is_critical",
                                                    "message"
                                                ],
                                                "properties": {
                                                    "is_critical": {
                                                        "type": "boolean",
                                                        "description": "If this error is critical. Critical errors generally halt further operations."
                                                    },
                                                    "message": {
                                                        "type": "string",
                                                        "description": "Detailed message about what caused the error."
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "has_failed": {
                        "type": "boolean",
                        "description": "If the request has failed from a critical error or not."
                    },
                    "errors": {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "title": "Operation Result Errors",
                        "description": "Errors returned from Authzee Operations. SDK errors should be prefixed with 'sdk_' and only have one field 'message' that is a string describing the error",
                        "type": "object",
                        "additionalProperties": true,
                        "required": [],
                        "properties": {
                            "query": {
                                "type": "array",
                                "items": {
                                    "title": "Query Error",
                                    "description": "Error when a JSON query fails.",
                                    "type": "object",
                                    "additionalProperties": true,
                                    "required": [
                                        "is_critical",
                                        "message"
                                    ],
                                    "properties": {
                                        "is_critical": {
                                            "type": "boolean",
                                            "description": "If this error is critical. Critical errors generally halt further operations."
                                        },
                                        "message": {
                                            "type": "string",
                                            "description": "Detailed message about what caused the error."
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "has_failed": {
            "type": "boolean",
            "description": "If the batch request could not be validated and failed or not. SDK errors should be prefixed with 'sdk_' and only have one field 'message' that is a string describing the error"
        },
        "errors": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Batch Result Errors",
            "description": "Errors returned from Authzee Batch requests.",
            "type": "object",
            "additionalProperties": true,
            "required": [],
            "properties": {}
        }
    }
}
```

### BatchAuthorizeResult

The [Authorize operation Results](./specification.md#authorize-operation-result), which conforms to the Authzee specification, where some fields are updated depending on the identity and resource defs.

#### BatchAuthorizeResult Example


```json
{
    "batch_results": [
        {
            "is_authorized": true,
            "grant": {
                "grant_uuid": "6ce44005-8735-45ac-ae76-38e22e66f615",
                "name": "My grant name",
                "description": "Longer description here to explain what the grant is for.",
                "tags": {
                    "some_key": "some_val"
                },
                "effect": "allow",
                "actions": [
                    "Balloon:Read",
                    "pop"
                ],
                "query": "contains(request.identities.User[0].role, 'admin')",
                "evaluation_handler": "evaluate",
                "equality": true,
                "data": {}
            },
            "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
            "has_failed": false,
            "critical_errors": {}
        },
        {
            "is_authorized": false,
            "grant": null,
            "message": "No grants are applicable to the request. Therefore, the request is implicitly denied and is not authorized.",
            "has_failed": false,
            "critical_errors": {}
        },

    ],
    "has_failed": false,
    "errors": {}
}
```


#### BatchAuthorizeResult Schema

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Batch Authorize Result",
    "description": "Result for the Batch Authorize Operation.",
    "type": "object",
    "additionalProperties": true,
    "required": [
        "batch_results",
        "has_failed",
        "errors"
    ],
    "properties": {
        "batch_results": {
            "type": "array",
            "description": "Array of results from a batch request. Each result corresponds to the batch request item of the same index.",
            "items": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "Authorize Result",
                "description": "Result for the authorize operation.",
                "type": "object",
                "additionalProperties": true,
                "required": [
                    "is_authorized",
                    "grant",
                    "message",
                    "has_failed",
                    "critical_errors"
                ],
                "properties": {
                    "is_authorized": {
                        "type": "boolean",
                        "description": "true if the request is authorized.  false if it is not authorized."
                    },
                    "grant": {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "title": "Grant",
                        "description": "A grant is an object representing enacted authorization rules.",
                        "type": "object",
                        "additionalProperties": true,
                        "required": [
                            "grant_uuid",
                            "name",
                            "description",
                            "tags",
                            "effect",
                            "actions",
                            "data",
                            "query",
                            "evaluation_handler",
                            "equality"
                        ],
                        "properties": {
                            "grant_uuid": {
                                "type": "string",
                                "format": "uuid"
                            },
                            "name": {
                                "type": "string",
                                "description": "Short name for the grant"
                            },
                            "description": {
                                "type": "string",
                                "description": "Longer description for the grant "
                            },
                            "tags": {
                                "type": "object",
                                "description": "General purpose Key/Value pairs for categorization.",
                                "patternProperties": {
                                    "^[A-Za-z0-9_]*$": {
                                        "type": "string"
                                    }
                                }
                            },
                            "effect": {
                                "type": "string",
                                "enum": [
                                    "allow",
                                    "deny"
                                ],
                                "description": "Any applicable deny grant will always cause the request to be unauthorized. If there are no applicable deny grants, and there is an applicable allow grant, the request is authorized. If there no applicable allow or deny grants, requests are implicitly denied and is not authorized."
                            },
                            "actions": {
                                "type": "array",
                                "uniqueItems": true,
                                "items": {
                                    "title": "Resource Action",
                                    "description": "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common, or more general 'Namespace:Action' pattern.",
                                    "type": "string",
                                    "pattern": "^[A-Za-z0-9_.:-]*$",
                                    "minLength": 1,
                                    "maxLength": 512
                                },
                                "description": "List of actions this grant applies to or null to match any resource action."
                            },
                            "data": {
                                "type": "object",
                                "description": "Data that is made available at query time for the grant evaluation. Easy place to store data so it doesn't have to be embedded in the query."
                            },
                            "query": {
                                "type": "string",
                                "description": "JSON query to run on the authorization data. {\"grant\": <grant>, \"request\": <request>}"
                            },
                            "evaluation_handler": {
                                "title": "Grant-Level Evaluation Handler Setting",
                                "description": "Set how evaluation errors are handled.'evaluate' - Evaluation is run and any errors cause the grant to be inapplicable to the request, but are not included in the result.'error' - Includes the 'validate' setting checks, and also includes errors in the result. 'critical' - Includes the 'error' setting checks, and will flag the error as critical, thus exiting the Authzee Operation early.",
                                "type": "string",
                                "enum": [
                                    "evaluate",
                                    "error",
                                    "critical"
                                ]
                            },
                            "equality": {
                                "description": "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
                            }
                        }
                    },
                    "message": {
                        "type": "string",
                        "description": "Details about why the request was authorized or not.",
                        "enum": [
                            "A critical error has occurred. Therefore, the request is not authorized.",
                            "A deny grant is applicable to the request. Therefore, the request is not authorized.",
                            "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
                            "No grants are applicable to the request. Therefore, the request is implicitly denied and is not authorized."
                        ]
                    },
                    "has_failed": {
                        "type": "boolean",
                        "description": "If the request has failed from a critical error or not. SDK errors should be prefixed with 'sdk_' and only have one field 'message' that is a string describing the error"
                    },
                    "critical_errors": {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "title": "Operation Result Errors",
                        "description": "Errors returned from Authzee Operations.",
                        "type": "object",
                        "additionalProperties": true,
                        "required": [],
                        "properties": {
                            "query": {
                                "type": "array",
                                "items": {
                                    "title": "Query Error",
                                    "description": "Error when a JSON query fails.",
                                    "type": "object",
                                    "additionalProperties": true,
                                    "required": [
                                        "is_critical",
                                        "message"
                                    ],
                                    "properties": {
                                        "is_critical": {
                                            "type": "boolean",
                                            "description": "If this error is critical. Critical errors generally halt further operations."
                                        },
                                        "message": {
                                            "type": "string",
                                            "description": "Detailed message about what caused the error."
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "has_failed": {
            "type": "boolean",
            "description": "If the batch request could not be validated and failed or not. "
        },
        "errors": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Batch Result Errors",
            "description": "Errors returned from Authzee Batch requests. SDK errors should be prefixed with 'sdk_' and only have one field 'message' that is a string describing the error",
            "type": "object",
            "additionalProperties": true,
            "required": [],
            "properties": {}
        }
    }
}
```


## Standard JMESPath Extensions

JMESPath is also the preferred JSON query language for Authzee as it has a specification and JMESPath SDKs generally offer the ability extend functionality by making new functions available in JMESPath queries. 
Because of this, Authzee SDKs should also offer a set of out of the box JMESPath functions the are helpful to Authzee grant queries.

- [INNER JOIN](#inner-join) - Join 2 arrays in a fashion similar to an SQL INNER JOIN. 
- [LEFT JOIN](#left-join) - Join 2 arrays in a fashion similar to an SQL LEFT JOIN.
- [OUTER JOIN](#outer-join) - Join 2 arrays in a fashion similar to an SQL OUTER JOIN.
- [Is Identity Present](#is-identity-present) - Check if the given identity type is in the request and at least one instance was given.
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
        },
        {
            "r_field": "hello",
            "r_other_field": "other other other thing"
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
    },
    {
        "lhs": {
            "l_field": "hello",
            "other_field": "thing"
        },
        "rhs": {
            "r_field": "hello",
            "r_other_field": "other other other thing"
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
            if jmespath.search( # Should use jmespath search function set in Authzee.
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


### LEFT JOIN

`array[object] left_join(array[any] $lhs, array[any] $rhs, expression->boolean expr)`

Modeled after SQL LEFT JOIN functionality.  Takes 2 arrays and an expression and returns all combinations of elements from the arrays where the expression evaluates to `true`. If an element from the left hand side does match any elements from the right hand side, then the left hand side element is returned with null for the right hand side. 

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
        },
        {
            "r_field": "hello",
            "r_other_field": "other other other thing"
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
    },
    {
        "lhs": {
            "l_field": "hello",
            "other_field": "thing"
        },
        "rhs": {
            "r_field": "hello",
            "r_other_field": "other other other thing"
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
            <pre><code>[
    {
        "lhs": {
            "l_field": "hello",
            "other_field": "thing"
        },
        "rhs": null
    }
]           </code></pre>
        </td>
    </tr>
</table>

Simple python function example:

```python
from typing import Any, Dict, List

import jmespath


def left_join(lhs: List[Any], rhs: List[Any], expr: str) -> List[Dict[str, Any]]:
    result = []
    for l in lhs:
        lhs_match = False
        for r in rhs:
            if jmespath.search( # Should use jmespath search function set in Authzee.
                expr,
                {
                    "lhs": l,
                    "rhs": r
                }
            ) is True:
                lhs_match = True
                result.append(
                    {
                        "lhs": l,
                        "rhs": r
                    }
                )
        
        if lhs_match is False:
            result.append(
                {
                    "lhs": l,
                    "rhs": None
                }
            )
    
    return result
```


### OUTER JOIN

`array[object] outer_join(array[any] $lhs, array[any] $rhs, expression->boolean expr)`

Modeled after SQL FULL OUTER JOIN functionality.  Takes 2 arrays and an expression and returns all combinations of elements from the arrays where the expression evaluates to `true`. If an element from the left hand side does match any elements from the right hand side, then the left hand side element is returned with null for the right hand side. If an element from the right hand side does match any elements from the left hand side, then the right hand side element is returned with null for the left hand side. 

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
        },
        {
            "r_field": "hello",
            "r_other_field": "other other other thing"
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
    },
    {
        "lhs": {
            "l_field": "hello",
            "other_field": "thing"
        },
        "rhs": {
            "r_field": "hello",
            "r_other_field": "other other other thing"
        }
    },
    {
        "lhs": null,
        "rhs": {
            "r_field": "goodbye",
            "r_other_field": "other thing"
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
        },
        {
            "l_field": "goodbye",
            "other_field": "another thing"
        },
        {
            "l_field": "goodbye",
            "other_field": "another another thing"
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
            <pre><code>[
    {
        "lhs": {
            "l_field": "hello",
            "other_field": "thing"
        },
        "rhs": null
    },
    {
        "lhs": {
            "l_field": "goodbye",
            "other_field": "another thing"
        },
        "rhs": {
            "r_field": "goodbye",
            "r_other_field": "other thing"
        }
    },
    {
        "lhs": {
            "l_field": "goodbye",
            "other_field": "another another thing"
        },
        "rhs": {
            "r_field": "goodbye",
            "r_other_field": "other thing"
        }
    }
]           </code></pre>
        </td>
    </tr>
</table>

Simple python function example:

```python
from typing import Any, Dict, List

import jmespath


def outer_join(lhs: List[Any], rhs: List[Any], expr: str) -> List[Dict[str, Any]]:
    result = []
    unmatched_rhs = set(rhs)
    for l in lhs:
        lhs_match = False
        for r in rhs:
            if jmespath.search( # Should use jmespath search function set in Authzee.
                expr,
                {
                    "lhs": l,
                    "rhs": r
                }
            ) is True:
                unmatched_rhs.discard(r)
                lhs_match = True
                result.append(
                    {
                        "lhs": l,
                        "rhs": r
                    }
                )
        
        if lhs_match is False:
            result.append(
                {
                    "lhs": l,
                    "rhs": None
                }
            )
    
    for r in unmatched_rhs:
        result.append(
            {
                "lhs": None,
                "rhs": r
            }
        )
    
    return result
```

### Is Identity Present

`boolean is_identity_present(string $itype, object $request)`

Return true if the given identity type exists in the request and it has one or more instances present, or else return false.

Examples:

<table>
    <tr>
        <th>Expression</th>
        <th>Result</th>
    </tr>
    <tr>
        <td>
           <code>is_identity_present("ADGroup", `{"identities": {"ADUser": []}}`)</code>
        </td>
        <td>
            <code>false</code>
        </td>
    </tr>
    <tr>
        <td>
           <code>is_identity_present("ADGroup", `{"identities": {"ADGroup": []}}`)</code>
        </td>
        <td>
            <code>false</code>
        </td>
    </tr>
     <tr>
        <td>
           <code>is_identity_present("ADGroup", `{"identities": {"ADGroup": [{"name": "thing"}]}}`)</code>
        </td>
        <td>
            <code>true</code>
        </td>
    </tr>
</table>

Simple Python Example:

```python
def is_identity_present(itype: str, request: dict) -> bool:
    if itype in request['identities'] and len(request['identities'][itype]) > 0:
        return True
    
    return False
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
