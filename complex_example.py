
import json

import jmespath
import jmespath.functions

from src.reference import authorize_workflow, audit_workflow

# Define the identities the calling entity has
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
            },
            "required": [
                "id",
                "color",
                "size",
                "material",
                "owner_department",
                "inflated"
            ]
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
            },
            "required": [
                "id",
                "length",
                "color",
                "material"
            ]
        }
    }
]

# 3. Define Contexts - extra data that is passed to the request
context_definitions = [
    { # no context
        "context_type": "NULL",
        "schema": {
            "type": "null"
        }
    },
    { # any context
        "context_type": "ANY",
        "schema": {}
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
    { # Allow users to read balloons in their department
        "effect": "allow",
        "actions": [
            "read"
        ],
        "query": "contains(request.identities.User[].department, request.resource.owner_department)", 
        # JMESPath query - Runs on {"request": <request obj>, "grant": <current grant>} 
        "query_validation": "error", # if the query has an error return it
        "equality": True,
        "data": {},
        "context_type": "NULL"
    },
    { # Allow users to read balloons on the context team
        "effect": "allow",
        "actions": [
            "read"
        ],
        "query": "contains(request.identities.User[].department, request.context.Team)",
        "query_validation": "error", # if the query has an error return it
        "equality": True,
        "data": {},
        "context_type": "MySpecialContext"
    },
    { # Allow users with admin role to perform any action
        "effect": "allow", 
        "actions": [
            "read",
            "inflate",
            "deflate",
            "pop",
            "tie"
        ],
        "query": "contains(request.identities.Role[].level, 'admin')",
        "query_validation": "error",
        "equality": True,
        "data": {},
        "context_type": "NULL"
    },
    { # Allow members of department groups to read balloons in that department
        "effect": "allow",
        "actions": [
            "read"
        ],
        "query": "contains(request.identities.Group[?type=='department'].department, request.resource.owner_department)",
        "query_validation": "error", 
        "equality": True,
        "data": {},
        "context_type": "NULL"
    },
    { # Allow inflate access if user has balloon permission in their role
        "effect": "allow",
        "actions": [
            "inflate"
        ],
        "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
        "query_validation": "error",
        "equality": True,
        "data": {},
        "context_type": "NULL"
    },
    { # Deny pop access for large balloons unless admin
        "effect": "deny",
        "actions": [
            "pop"
        ],
        "query": "request.resource.size == 'large' && !contains(request.identities.Role[*].level, 'admin')",
        "query_validation": "error",
        "equality": True,
        "data": {},
        "context_type": "NULL"
    },
    { # Deny if they don't have any user identities
        "effect": "deny",
        "actions": [],
        "query": "length(request.identities.User)",
        "query_validation": "error",
        "equality": 0,
        "data": {},
        "context_type": "NULL"
    }
]

# 5. Create an authorization request
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

# 6.a. Audit which grants are applicable (useful for auditing)
audit_result = audit_workflow(
    identity_definitions,
    resource_definitions,
    grants,
    request,
    jmespath.search # JMESPath search function or custom function
)
print(f"Audit Result:\n{json.dumps(audit_result, indent=4)}")
# Audit Result:
# {
#     "completed": true,
#     "grants": [
#         {
#             "effect": "allow",
#             "actions": [
#                 "inflate"
#             ],
#             "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#             "query_validation": "error",
#             "equality": true,
#             "data": {},
#             "context_schema": {
#                 "type": "object"
#             },
#             "context_validation": "none"
#         }
#     ],
#     "errors": {
#         "definition": [],
#         "grant": [],
#         "jmespath": [],
#         "request": []
#     }
# }

# 6.b. Make authorization decision
authorization_result = authorize_workflow(
    identity_definitions,
    resource_definitions, 
    grants,
    request,
    my_search # JMESPath search function or custom function
)
print(f"Authorization Result:\n{json.dumps(authorization_result, indent=4)}")
# Authorization Result:
# {
#     "authorized": true,
#     "completed": true,
#     "grant": {
#         "effect": "allow",
#         "actions": [
#             "inflate"
#         ],
#         "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#         "query_validation": "error",
#         "equality": true,
#         "data": {},
#         "context_schema": {
#             "type": "object"
#         },
#         "context_validation": "none"
#     },
#     "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
#     "errors": {
#         "definition": [],
#         "grant": [],
#         "jmespath": [],
#         "request": []
#     }
# }

# 7. Create a batch request. Requests can also be batched for the same identities, action, resource type, and context type.
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
    "resource_type": "Balloon",
    "action": "inflate",
    "context_type": "MySpecialContext",  # specify the context type, this will only be evaluated against grants that accept this context
    "resources": [
        {
            "resource": {
                "id": "balloon456",
                "color": "red",
                "size": "medium",
                "material": "latex",
                "owner_department": "party_planning",
                "inflated": False
            },
            "query_validation": "grant",  # Use grant-level validation settings
            "context": { # The context for the request
                "Team": "party_planning"
            }
        }
    ]  
}

# 6.a. Audit which grants are applicable (useful for auditing)
audit_batch_result = audit_batch_workflow(
    identity_definitions,
    resource_definitions,
    grants,
    batch_request,
    jmespath.search # JMESPath search function or custom function
)
print(f"Audit Batch Result:\n{json.dumps(audit_result, indent=4)}")
# Audit Result - An array of audit results that maps to the batch_request.resources array
# Each one is processed as if it was a separate request
# [
#     {
#         "completed": true,
#         "grants": [
#             {
#                 "effect": "allow",
#                 "actions": [
#                     "inflate"
#                 ],
#                 "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#                 "query_validation": "error",
#                 "equality": true,
#                 "data": {},
#                 "context_schema": {
#                     "type": "object"
#                 },
#                 "context_validation": "none"
#             }
#         ],
#         "errors": {
#             "definition": [],
#             "grant": [],
#             "jmespath": [],
#             "request": []
#         }
#     }
# ]

# 7.b. Make authorization decision
authorize_batch_result = authorize_batch_workflow(
    identity_definitions,
    resource_definitions, 
    grants,
    batch_request,
    my_search # JMESPath search function or custom function
)
print(f"Authorize Batch Result:\n{json.dumps(authorization_result, indent=4)}")
# Authorization Result - An array of authorization results that maps to the batch_request.resources array
# Each one is processed as if it was a separate request
# [
#     {
#         "authorized": true,
#         "completed": true,
#         "grant": {
#             "effect": "allow",
#             "actions": [
#                 "inflate"
#             ],
#             "query": "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
#             "query_validation": "error",
#             "equality": true,
#             "data": {},
#             "context_schema": {
#                 "type": "object"
#             },
#             "context_validation": "none"
#         },
#         "message": "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
#         "errors": {
#             "definition": [],
#             "grant": [],
#             "jmespath": [],
#             "request": []
#         }
#     }
# ]
