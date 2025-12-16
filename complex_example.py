
import json

import jmespath
import jmespath.functions

from src.reference import (
    audit_workflow,
    authorize_workflow,
    batch_audit_workflow,
    batch_authorize_workflow
) 

# Define the identities the calling entity may have
identity_definitions = [
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
resource_definitions = [
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
context_definitions = [ # note that context root types must be objects!
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
        "grant_uuid": "ab57355a-dc2a-4a6e-b642-727069e70a41",
        "name": "User Read Balloons",
        "description": "Allow users to read balloons in their department.",
        "effect": "allow",
        "actions": [
            "read"
        ],
        "query": "contains(request.identities.User[].department, request.resource.owner_department)", 
        # JMESPath query - Runs on {"request": <request obj>, "grant": <current grant>} 
        "query_validation": "error", # if the query has an error return it
        "equality": True,
        "data": {}
    },
    {
        "grant_uuid": "ad3448fc-8e78-48e4-bbae-c5e8d22b032f",
        "name": "User Read context team Balloons",
        "description": "Allow users to read balloons on the context team.",
        "effect": "allow",
        "actions": [
            "read"
        ],       # you can use the query to limit by context types
        "query": "request.context_type == 'MySpecialContext' && contains(request.identities.User[].department, request.context.Team)",
        "query_validation": "error", # if the query has an error return it
        "equality": True,
        "data": {}
    },
    {
        "grant_uuid": "74060ab5-7cd5-41f7-96d9-490ee120b411",
        "name": "Admin null context all",
        "description": "Allow users with admin role to perform any action if given a null context.",
        "effect": "allow", 
        "actions": [
            "read",
            "inflate",
            "deflate",
            "pop",
            "tie"
        ],
        "query": "request.context_type == 'NULL' && contains(request.identities.Role[].level, 'admin')",
        "query_validation": "error",
        "equality": True,
        "data": {}
    },
    { # 
        "grant_uuid": "66a1a821-f424-49b9-a435-9691a388ee74",
        "name": "Group read department balloon",
        "description": "Allow members of department groups to read balloons in that department.",
        "effect": "allow",
        "actions": [
            "read"
        ], # because the read action is for multiple resources we can check the resource type first. 
        "query": "request.resource_type == 'BalloonStore' && contains(request.identities.Group[?type=='department'].department, request.resource.owner_department)",
        "query_validation": "error", 
        "equality": True,
        "data": {}
    },
    { # 
        "grant_uuid": "edc82a71-1bad-4a40-9678-1da30e630ac4",
        "name": "Allow user balloon inflate with role permissions",
        "description": "Allow inflate access if user has balloon permission in their role, and the balloon is in the users department.",
        "effect": "allow",
        "actions": [
            "inflate"
        ],                                                                               # don't need to check resource type since only Balloon has the 'inflate' action
        "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
        "query_validation": "error",
        "equality": True,
        "data": {}
    },
    {
        "grant_uuid": "2ad2dc5f-2452-4bd0-8e5f-ef602e16d9e1",
        "name": "Deny pop for non-admin",
        "description": "Deny pop access for large balloons unless admin.",
        "effect": "deny",
        "actions": [
            "pop"
        ],       # don't need to check resource type since only Balloon has the 'inflate' action
        "query": "request.context_type == 'NULL' && request.resource.size == 'large' && !contains(request.identities.Role[*].level, 'admin')",
        "query_validation": "error",
        "equality": True,
        "data": {}
    },
    { # 
        "grant_uuid": "86d7fc42-9908-4391-b7b0-7bb5ae752ae5",
        "name": "Deny no identities",
        "description": "Deny if they don't have any user identities.",
        "effect": "deny",
        "actions": [],
        "query": "request.context_type == 'NULL' && length(request.identities.User) == `0`",
        "query_validation": "error",
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
    "query_validation": "grant",  # Use grant-level validation settings
    "context_type": "MySpecialContext",  # specify the context type, this will only be evaluated against grants that accept this context
    "context": { # The context for the request
        "Team": "party_planning"
    }
}

# 5.b. (Optional) Add custom JMESPath functions
class CustomFunctions(jmespath.functions.Functions):
    @jmespath.functions.signature({'types': ['number']}, {'types': ['number']})
    def _func_my_add(self, x, y):
        return x + y

options = jmespath.Options(custom_functions=CustomFunctions())

def my_search(expression: str, data):
    return jmespath.search(expression, data, options)

# 6.a. Audit - Find grants applicable to the request.  As the name says, this is good for auditing access
audit_result = audit_workflow(
    context_definitions,
    identity_definitions,
    resource_definitions,
    grants,
    request,
    jmespath.search # JMESPath search function or custom function
)
print(f"Audit Result:\n{json.dumps(audit_result, indent=4)}")
# Audit Result:
# {
#     "grants": [
#         {
#             "grant_uuid": "6a98d38a-2c47-4558-9156-a049a716760b",
#             "name": "Allow user balloon inflate with role permissions",
#             "description": "Allow inflate access if user has balloon permission in their role, and the balloon is in the users department.",
#             "effect": "allow",
#             "actions": [
#                 "inflate"
#             ],
#             "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#             "query_validation": "error",
#             "equality": true,
#             "data": {}
#         }
#     ],
#     "has_failed": false,
#     "errors": {}
# }


# 6.b. Authorized - Optimized to decide if the given request is authorized
# Requests are authorized if they have a matching allow grant and no matching deny grants. 
authorization_result = authorize_workflow(
    context_definitions,
    identity_definitions,
    resource_definitions, 
    grants,
    request,
    my_search # JMESPath search function or custom function
)
print(f"Authorization Result:\n{json.dumps(authorization_result, indent=4)}")
# Authorization Result:
# {
#     "is_authorized": true,
#     "grant": {
#         "grant_uuid": "6a98d38a-2c47-4558-9156-a049a716760b",
#         "name": "Allow user balloon inflate with role permissions",
#         "description": "Allow inflate access if user has balloon permission in their role, and the balloon is in the users department.",
#         "effect": "allow",
#         "actions": [
#             "inflate"
#         ],
#         "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#         "query_validation": "error",
#         "equality": true,
#         "data": {}
#     },
#     "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
#     "has_failed": false,
#     "critical_errors": {}
# }

# 7. Create a batch request. 
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
    "query_validation": "grant",
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
            "context":  {},
            "query_validation": "error"
        },
        {} # technically you don't have to override any
    ]  
}

# 6.a. Audit which grants are applicable (useful for auditing)
batch_audit_results = batch_audit_workflow(
    context_definitions,
    identity_definitions,
    resource_definitions,
    grants,
    batch_request,
    jmespath.search # JMESPath search function or custom function
)
print(f"Batch Audit Result:\n{json.dumps(batch_audit_results, indent=4)}")
# Audit Result - An array of audit results that maps to the batch_request.resources array
# Each one is processed as if it was a separate request
# {
#     "results": [
#         {
#             "grants": [
#                 {
#                     "grant_uuid": "6a98d38a-2c47-4558-9156-a049a716760b",
#                     "name": "Allow user balloon inflate with role permissions",
#                     "description": "Allow inflate access if user has balloon permission in their role, and the balloon is in the users department.",
#                     "effect": "allow",
#                     "actions": [
#                         "inflate"
#                     ],
#                     "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#                     "query_validation": "error",
#                     "equality": true,
#                     "data": {}
#                 }
#             ],
#             "has_failed": false,
#             "errors": {}
#         },
#         {
#             "grants": [],
#             "has_failed": false,
#             "errors": {
#                 "jmespath": [
#                     {
#                         "is_critical": false,
#                         "message": "A JMESPath error has occurred: In function contains(), invalid type for value: None, expected one of: ['array', 'string'], received: \"null\".",
#                         "grant": {
#                             "grant_uuid": "8f8c4ee7-eea3-4d81-a736-abe6c3c4c3c3",
#                             "name": "Admin null context all",
#                             "description": "Allow users with admin role to perform any action if given a null context.",
#                             "effect": "allow",
#                             "actions": [
#                                 "read",
#                                 "inflate",
#                                 "deflate",
#                                 "pop",
#                                 "tie"
#                             ],
#                             "query": "request.context_type == 'NULL' && contains(request.identities.Role[].level, 'admin')",
#                             "query_validation": "error",
#                             "equality": true,
#                             "data": {}
#                         }
#                     },
#                     {
#                         "is_critical": false,
#                         "message": "A JMESPath error has occurred: In function contains(), invalid type for value: None, expected one of: ['array', 'string'], received: \"null\".",
#                         "grant": {
#                             "grant_uuid": "6a98d38a-2c47-4558-9156-a049a716760b",
#                             "name": "Allow user balloon inflate with role permissions",
#                             "description": "Allow inflate access if user has balloon permission in their role, and the balloon is in the users department.",
#                             "effect": "allow",
#                             "actions": [
#                                 "inflate"
#                             ],
#                             "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#                             "query_validation": "error",
#                             "equality": true,
#                             "data": {}
#                         }
#                     }
#                 ]
#             }
#         },
#         {
#             "grants": [
#                 {
#                     "grant_uuid": "6a98d38a-2c47-4558-9156-a049a716760b",
#                     "name": "Allow user balloon inflate with role permissions",
#                     "description": "Allow inflate access if user has balloon permission in their role, and the balloon is in the users department.",
#                     "effect": "allow",
#                     "actions": [
#                         "inflate"
#                     ],
#                     "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#                     "query_validation": "error",
#                     "equality": true,
#                     "data": {}
#                 }
#             ],
#             "has_failed": false,
#             "errors": {}
#         }
#     ],
#     "has_failed": false,
#     "errors": {}
# }

# 7.b. Make authorization decision
batch_authorize_result = batch_authorize_workflow(
    context_definitions,
    identity_definitions,
    resource_definitions, 
    grants,
    batch_request,
    my_search # JMESPath search function or custom function
)
print(f"Authorize Batch Result:\n{json.dumps(batch_authorize_result, indent=4)}")
# Authorization Result - An array of authorization results that maps to the batch_request.resources array
# Each one is processed as if it was a separate request
# {
#     "results": [
#         {
#             "is_authorized": true,
#             "grant": {
#                 "grant_uuid": "edc82a71-1bad-4a40-9678-1da30e630ac4",
#                 "name": "Allow user balloon inflate with role permissions",
#                 "description": "Allow inflate access if user has balloon permission in their role, and the balloon is in the users department.",
#                 "effect": "allow",
#                 "actions": [
#                     "inflate"
#                 ],
#                 "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#                 "query_validation": "error",
#                 "equality": true,
#                 "data": {}
#             },
#             "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
#             "has_failed": false,
#             "critical_errors": {}
#         },
#         {
#             "is_authorized": false,
#             "grant": null,
#             "message": "No allow or deny grants are applicable to the request. Therefore, the request is implicitly denied and is not authorized.",
#             "has_failed": false,
#             "critical_errors": {}
#         },
#         {
#             "is_authorized": true,
#             "grant": {
#                 "grant_uuid": "edc82a71-1bad-4a40-9678-1da30e630ac4",
#                 "name": "Allow user balloon inflate with role permissions",
#                 "description": "Allow inflate access if user has balloon permission in their role, and the balloon is in the users department.",
#                 "effect": "allow",
#                 "actions": [
#                     "inflate"
#                 ],
#                 "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#                 "query_validation": "error",
#                 "equality": true,
#                 "data": {}
#             },
#             "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
#             "has_failed": false,
#             "critical_errors": {}
#         }
#     ],
#     "has_failed": false,
#     "errors": {}
# }
