
import json
from typing import Any

import jmespath
import jmespath.functions

from src.reference import (
    audit_workflow,
    authorize_workflow,
    batch_audit_workflow,
    batch_authorize_workflow
) 

# Define the identities the calling entity may have
identity_defs = [
    {
        "identity_type": "User",
        "schema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string"
                },
                "department": {
                    "type": "string"
                },
                "email": {
                    "type": "string"
                }
            },
            "required": [
                "id",
                "department",
                "email"
            ]
        }
    },
    {
        "identity_type": "Group", 
        "schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string"
                },
                "department": {
                    "type": "string"
                },
                "type": {
                    "type": "string",
                    "enum": [
                        "team",
                        "project",
                        "department"
                    ]
                }
            },
            "required": [
                "name",
                "department",
                "type"
            ]
        }
    },
    {
        "identity_type": "Role",
        "schema": {
            "type": "object", 
            "properties": {
                "name": {
                    "type": "string"
                },
                "permissions": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "level": {
                    "type": "string",
                    "enum": [
                        "basic",
                        "advanced",
                        "admin"
                    ]
                }
            },
            "required": [
                "name",
                "permissions",
                "level"
            ]
        }
    },
    {
        "identity_type": "OtherID",
        "schema": {
            "type": "object",
            "required": [],
            "properties": {
                "dontCare": {
                    "type": "string"
                }
            }
        }
    }
]

# 2. Define resources that can be accessed
resource_defs = [
    {
        "resource_type": "BalloonStore",
        "actions": [
            "read",
            "manage",
            "create_balloon"
        ],
        "schema": {
            "type": "object",
            "required": [
                "id",
                "name",
                "owner_department",
                "location"
            ],
            "properties": {
                "id": {
                    "type": "string"
                },
                "name": {
                    "type": "string"
                },
                "owner_department": {
                    "type": "string"
                },
                "location": {
                    "type": "string"
                }
            }
        }
    },
    {
        "resource_type": "Balloon",
        "actions": [
            "read",
            "inflate",
            "deflate",
            "pop",
            "tie"
        ],
        "schema": {
            "type": "object", 
            "required": [
                "id",
                "color",
                "size",
                "material",
                "owner_department",
                "inflated"
            ],
            "properties": {
                "id": {
                    "type": "string"
                },
                "color": {
                    "type": "string"
                },
                "size": {
                    "type": "string",
                    "enum": [
                        "small",
                        "medium",
                        "large"
                    ]
                },
                "material": {
                    "type": "string"
                },
                "owner_department": {
                    "type": "string"
                },
                "inflated": {
                    "type": "boolean"
                }
            }
        }
    },
    {
        "resource_type": "BalloonString",
        "actions": [
            "read",
            "cut",
            "tie",
            "untie"
        ],
        "schema": {
            "type": "object",
            "required": [
                "id",
                "length",
                "color",
                "material"
            ],
            "properties": {
                "id": {
                    "type": "string"
                },
                "length": {
                    "type": "number"
                },
                "color": {
                    "type": "string"
                },
                "material": {
                    "type": "string"
                }
            }
        }
    }
]

# 3. Define Contexts - extra data that is passed to the request
context_defs = [ # note that context root types must be objects!
    { # no context
        "context_type": "NULL",
        "schema": {
            "type": "object",
            "additionalProperties": False
        }
    },
    { # any context
        "context_type": "ANY",
        "schema": {
            "type": "object"
        }
    },
    { # Context for the Team
        "context_type": "MySpecialContext",
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
    }, 
    { # You can also do things like parent or child resources
        "context_type": "BalloonRelationships",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "BalloonStore"
            ],
            "properties": {
                "BalloonStore": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string"
                            },
                            "name": {
                                "type": "string"
                            },
                            "owner_department": {
                                "type": "string"
                            },
                            "location": {
                                "type": "string"
                            }
                        },
                        "required": [
                            "id",
                            "name",
                            "owner_department",
                            "location"
                        ]
                    }
                }
            }
        }
    }
]

# 4. Define Grants - access rules 
grants = [
    { 
        "effect": "allow",
        "actions": [
            "read"
        ],
        "query": "contains(request.identities.User[].department, request.resource.owner_department)", 
        # JMESPath query - Runs on {"request": <request obj>, "grant": <current grant>} 
        "equality": True,
        "data": {}
    },
    {
        "effect": "allow",
        "actions": [
            "read"
        ],       # you can use the query to limit by context types
        "query": "request.context_type == 'MySpecialContext' && contains(request.identities.User[].department, request.context.Team)",
        "equality": True,
        "data": {}
    },
    {
        "effect": "allow", 
        "actions": [
            "read",
            "inflate",
            "deflate",
            "pop",
            "tie"
        ],
        "query": "request.context_type == 'NULL' && contains(request.identities.Role[].level, 'admin')",
        "equality": True,
        "data": {}
    },
    { 
        "effect": "allow",
        "actions": [
            "read"
        ], # because the read action is for multiple resources we can check the resource type first. 
        "query": "request.resource_type == 'BalloonStore' && contains(request.identities.Group[?type=='department'].department, request.resource.owner_department)",
        "equality": True,
        "data": {}
    },
    { 
        "effect": "allow",
        "actions": [
            "inflate"
        ],                                                                               # don't need to check resource type since only Balloon has the 'inflate' action
        "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
        "equality": True,
        "data": {}
    },
    {
        "effect": "deny",
        "actions": [
            "pop"
        ],       # don't need to check resource type since only Balloon has the 'inflate' action
        "query": "request.context_type == 'NULL' && request.resource.size == 'large' && !contains(request.identities.Role[*].level, 'admin')",
        "equality": True,
        "data": {}
    },
    {
        "effect": "deny",
        "actions": [],
        "query": "request.context_type == 'NULL' && length(request.identities.User) == `0`",
        "equality": True,
        "data": {}
    }
]

# 5. Create an Authzee request
request = {
    "identities": {
        "User": [
            {
                "id": "user123",
                "department": "party_planning",
                "email": "john.doe@company.com"
            }
        ],
        "Group": [
            {
                "name": "event-team",
                "department": "party_planning", 
                "type": "team"
            },
            {
                "name": "party-planning-dept",
                "department": "party_planning",
                "type": "department"
            }
        ],
        "Role": [
            {
                "name": "party-coordinator",
                "permissions": [
                    "balloon:read",
                    "balloon:inflate",
                    "balloon:tie"
                ],
                "level": "advanced"
            }
        ]
        #"OtherID": [] # Can be added if none or any exist for the calling entity
    },
    "resource_type": "Balloon",
    "action": "inflate",
    "resource": {
        "id": "balloon456",
        "color": "red",
        "size": "medium",
        "material": "latex",
        "owner_department": "party_planning",
        "inflated": False
    },
    "context_type": "MySpecialContext",  # specify the context type, this will only be evaluated against grants that accept this context
    "context": { # The context for the request
        "Team": "party_planning"
    }
}

# 6.a. Define a function wrapping your preferred JSON query language to return the expected schema.
def execute(expression: str, data: Any) -> Any:
    result = {
        "result": None,
        "error": None
    }
    try:
        result['result'] = jmespath.search(expression, data)
    except Exception as exc:
        result['error'] = {
            "error_type": "evaluation",
            "message": f"A JMESPath Query error has occurred: {exc}"
        }
    
    return result

# 6.b. (Optional) Add custom JMESPath functions
class CustomFunctions(jmespath.functions.Functions):
    @jmespath.functions.signature({'types': ['number']}, {'types': ['number']})
    def _func_my_add(self, x, y):
        return x + y

options = jmespath.Options(custom_functions=CustomFunctions())

def my_execute(expression: str, data: Any) -> Any:
    result = {
        "result": None,
        "error": None
    }
    try:
        result['result'] = jmespath.search(expression, data, options)
    except Exception as exc:
        result['error'] = {
            "error_type": "evaluation",
            "message": f"A JMESPath Query error has occurred: {exc}"
        }
    
    return result


# 7.a. Audit - Evaluate grants against the request.  As the name says, this is good for auditing access
audit_result = audit_workflow(
    context_defs,
    identity_defs,
    resource_defs,
    grants,
    request,
    my_execute
)
print(f"Audit Result:\n{json.dumps(audit_result, indent=4)}")
# Audit Result:
# {
#     "results": [
#         {
#             "grant": {
#                 "effect": "allow",
#                 "actions": [
#                     "inflate"
#                 ],
#                 "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#                 "equality": true,
#                 "data": {}
#             },
#             "is_applicable": true,
#             "query_result": true,
#             "error": null
#         }
#     ],
#     "error": null
# }


# 7.b. Authorized - Optimized to decide if the given request is authorized
# Requests are authorized if they have a matching allow grant and no matching deny grants. 
authorization_result = authorize_workflow(
    context_defs,
    identity_defs,
    resource_defs, 
    grants,
    request,
    my_execute 
)
print(f"Authorization Result:\n{json.dumps(authorization_result, indent=4)}")
# Authorization Result:
# {
#     "is_authorized": true,
#     "grant": {
#         "effect": "allow",
#         "actions": [
#             "inflate"
#         ],
#         "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#         "equality": true,
#         "data": {}
#     },
#     "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
#     "error": null
# }

# 8. Create a batch request. 
# Requests can be batched for the same action. They can share all other fields in a normal request. 
# if the batch item does not specify a request field then it uses the default that is specified in the top level of the batch request. 
batch_request = {
    "identities": {
        "User": [
            {
                "id": "user123",
                "department": "party_planning",
                "email": "john.doe@company.com"
            }
        ],
        "Group": [
            {
                "name": "event-team",
                "department": "party_planning", 
                "type": "team"
            },
            {
                "name": "party-planning-dept",
                "department": "party_planning",
                "type": "department"
            }
        ],
        "Role": [
            {
                "name": "party-coordinator",
                "permissions": [
                    "balloon:read",
                    "balloon:inflate",
                    "balloon:tie"
                ],
                "level": "advanced"
            }
        ]
        #"OtherID": [] # Can be added if none or any exist for the calling entity
    },
    "action": "inflate",
    "resource_type": "Balloon",
    "resource": { 
        "id": "balloon123",
        "color": "green",
        "size": "medium",
        "material": "latex",
        "owner_department": "party_planning",
        "inflated": False
    },
    "context_type": "MySpecialContext",  # specify the context type, this will only be evaluated against grants that accept this context
    "context": {
        "Team": "ABC"
    },
    "batch": [
        {
            "resource": { # A common use case is to simply specify different resources for the same request
                "id": "balloon456",
                "color": "red",
                "size": "medium",
                "material": "latex",
                "owner_department": "party_planning",
                "inflated": False
            }
        },
        { # Can also override any root fields in the batch request besides the action.
            "identities": {
                "User": [
                    {
                        "id": "Store123",
                        "department": "Store 123",
                        "owner_department": "IDK",
                        "location": "Somewhere"
                    }
                ],
                "Group": [
                    {
                        "name": "My Special group",
                        "department": "special_dept", 
                        "type": "team"
                    }
                ]
            },
            "resource_type": "BalloonStore",
            "resource": {
                "id": "1234",
                "name": "Special store",
                "owner_department": "special_dept",
                "location": "Somewhere"
            },
            "context_type": "NULL",  # specify the context type, this will only be evaluated against grants that accept this context
            "context":  {}
        },
        {} # technically you don't have to override any
    ]  
}

# 9.a. Evaluate several requests with the same action against grants
batch_audit_results = batch_audit_workflow(
    context_defs,
    identity_defs,
    resource_defs,
    grants,
    batch_request,
    my_execute 
)
print(f"Batch Audit Result:\n{json.dumps(batch_audit_results, indent=4)}")
# Audit Result - An array of audit results that maps to the batch_request.resources array
# Each one is processed as if it was a separate request
# {
#     "grants": [...],
#     "batch_results": [
#         {
#             "results": [
#                 {
#                     "is_applicable": true,
#                     "query_result": true,
#                     "error": null
#                 }
#             ],
#             "error": null
#         },
#         {
#             "results": [
#                 {
#                     "is_applicable": false,
#                     "query_result": null,
#                     "error": {
#                         "error_type": "evaluation",
#                         "message": "A JSON Query error has occurred: ..."
#                     }
#                 }
#             ],
#             "error": null
#         },
#         {
#             "results": [
#                 {
#                     "is_applicable": true,
#                     "query_result": true,
#                     "error": null
#                 }
#             ],
#             "error": null
#         }
#     ],
#     "error": null
# }

# 9.b. Check if several requests with the same action are authorized.
batch_authorize_result = batch_authorize_workflow(
    context_defs,
    identity_defs,
    resource_defs, 
    grants,
    batch_request,
    my_execute 
)
print(f"Authorize Batch Result:\n{json.dumps(batch_authorize_result, indent=4)}")
# Authorization Result - An array of authorization results that maps to the batch_request.resources array
# Each one is processed as if it was a separate request
# {
#     "batch_results": [
#         {
#             "is_authorized": true,
#             "grant": {
#                 "effect": "allow",
#                 "actions": [
#                     "inflate"
#                 ],
#                 "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#                 "equality": true,
#                 "data": {}
#             },
#             "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
#             "error": null
#         },
#         {
#             "is_authorized": false,
#             "grant": null,
#             "message": "No grants are applicable to the request. Therefore, the request is implicitly denied and is not authorized.",
#             "error": null
#         },
#         {
#             "is_authorized": true,
#             "grant": {
#                 "effect": "allow",
#                 "actions": [
#                     "inflate"
#                 ],
#                 "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#                 "equality": true,
#                 "data": {}
#             },
#             "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
#             "error": null
#         }
#     ],
#     "error": null
# }
