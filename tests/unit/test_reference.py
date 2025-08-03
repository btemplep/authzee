"""pytest -vvv --cov=src/ --cov-report=html --cov-report term tests/unit/ """
import pytest
import jmespath
import jsonschema
from src.reference import (
    audit_workflow,
    authorize_workflow,
    generate_schemas
)


@pytest.fixture
def basic_identity_defs():
    """Basic identity definitions for testing."""
    return [
        {
            "identity_type": "User",
            "schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"}
                },
                "required": ["id", "name"]
            }
        }
    ]


@pytest.fixture
def basic_resource_defs():
    """Basic resource definitions for testing."""
    return [
        {
            "resource_type": "Document",
            "actions": ["read", "write", "delete"],
            "schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "owner": {"type": "string"}
                },
                "required": ["id", "title"]
            },
            "parent_types": ["Folder"],
            "child_types": ["Comment"]
        },
        {
            "resource_type": "Folder",
            "actions": ["list", "create"],
            "schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"}
                },
                "required": ["id", "name"]
            },
            "parent_types": [],
            "child_types": []
        },
        {
            "resource_type": "Comment",
            "actions": ["reply", "edit"],
            "schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"}
                },
                "required": ["id", "text"]
            },
            "parent_types": [],
            "child_types": []
        }
    ]


@pytest.fixture
def basic_grants():
    """Basic grants for testing."""
    return [
        {
            "effect": "allow",
            "actions": ["read"],
            "query": "request.resource.owner == request.identities.User[0].id",
            "query_validation": "validate",
            "equality": True,
            "data": {"description": "Allow owner to read"},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        },
        {
            "effect": "deny",
            "actions": ["delete"],
            "query": "request.resource.title == 'protected'",
            "query_validation": "validate",
            "equality": True,
            "data": {"description": "Deny deletion of protected documents"},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        }
    ]


@pytest.fixture
def basic_request():
    """Basic request for testing."""
    return {
        "identities": {
            "User": [{"id": "user123", "name": "John Doe"}]
        },
        "resource_type": "Document",
        "action": "read",
        "resource": {
            "id": "doc1",
            "title": "Test Document",
            "owner": "user123"
        },
        "parents": {
            "Folder": [{"id": "folder1", "name": "Test Folder"}]
        },
        "children": {
            "Comment": [{"id": "comment1", "text": "Test comment"}]
        },
        "query_validation": "grant",
        "context": {},
        "context_validation": "grant"
    }


def test_successful_evaluation(basic_identity_defs, basic_resource_defs, basic_grants, basic_request):
    result = audit_workflow(
        basic_identity_defs,
        basic_resource_defs,
        basic_grants,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['audit'])  
    assert result['completed'] is True
    assert len(result['grants']) == 1  # Only the allow grant should match
    assert result['grants'][0]['effect'] == 'allow'
    assert all(len(errors) == 0 for errors in result['errors'].values())


def test_invalid_identity_definitions(basic_resource_defs, basic_grants, basic_request):
    invalid_identity_defs = [
        {
            "identity_type": "User",
            # Missing required 'schema' field
        }
    ]
    result = audit_workflow(
        invalid_identity_defs,
        basic_resource_defs,
        basic_grants,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas([{"identity_type": "User", "schema": {"type": "object"}}], basic_resource_defs)
    jsonschema.validate(result, schemas['audit'])
    assert result['completed'] is False
    assert len(result['grants']) == 0
    assert len(result['errors']['definition']) > 0
    assert result['errors']['definition'][0]['critical'] is True


def test_duplicate_identity_types(basic_resource_defs, basic_grants, basic_request):
    duplicate_identity_defs = [
        {
            "identity_type": "User",
            "schema": {"type": "object"}
        },
        {
            "identity_type": "User",  # Duplicate
            "schema": {"type": "object"}
        }
    ]
    result = audit_workflow(
        duplicate_identity_defs,
        basic_resource_defs,
        basic_grants,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas([{"identity_type": "User", "schema": {"type": "object"}}], basic_resource_defs)
    jsonschema.validate(result, schemas['audit'])
    assert result['completed'] is False
    assert len(result['errors']['definition']) > 0


def test_invalid_resource_definitions(basic_identity_defs, basic_grants, basic_request):
    invalid_resource_defs = [
        {
            "resource_type": "Document",
            # Missing required fields
        }
    ]
    result = audit_workflow(
        basic_identity_defs,
        invalid_resource_defs,
        basic_grants,
        basic_request,
        jmespath.search
    )
    assert result['completed'] is False
    assert len(result['errors']['definition']) > 0


def test_invalid_parent_type_resource_definitions(basic_identity_defs, basic_grants, basic_request):
    invalid_resource_defs = [
        {
            "resource_type": "Document",
            "actions": ["read"],
            "schema": {"type": "object"},
            "parent_types": ["unknown"],
            "child_types": []
        }
    ]
    result = audit_workflow(
        basic_identity_defs,
        invalid_resource_defs,
        basic_grants,
        basic_request,
        jmespath.search
    )
    assert result['completed'] is False
    assert len(result['errors']['definition']) > 0


def test_invalid_child_type_resource_definitions(basic_identity_defs, basic_grants, basic_request):
    invalid_resource_defs = [
        {
            "resource_type": "Document",
            "actions": ["read"],
            "schema": {"type": "object"},
            "parent_types": [],
            "child_types": ["unknown"]
        }
    ]
    result = audit_workflow(
        basic_identity_defs,
        invalid_resource_defs,
        basic_grants,
        basic_request,
        jmespath.search
    )
    assert result['completed'] is False
    assert len(result['errors']['definition']) > 0


def test_duplicate_resource_types(basic_identity_defs, basic_grants, basic_request):
    duplicate_resource_defs = [
        {
            "resource_type": "Document",
            "actions": ["read"],
            "schema": {"type": "object"},
            "parent_types": [],
            "child_types": []
        },
        {
            "resource_type": "Document",  # Duplicate
            "actions": ["write"],
            "schema": {"type": "object"},
            "parent_types": [],
            "child_types": []
        }
    ]
    result = audit_workflow(
        basic_identity_defs,
        duplicate_resource_defs,
        basic_grants,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, [duplicate_resource_defs[0]])
    jsonschema.validate(result, schemas['audit'])
    assert result['completed'] is False
    assert len(result['errors']['definition']) > 0


def test_invalid_grants(basic_identity_defs, basic_resource_defs, basic_request):
    invalid_grants = [
        {
            "effect": "allow",
            # Missing required fields
        }
    ]
    result = audit_workflow(
        basic_identity_defs,
        basic_resource_defs,
        invalid_grants,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['audit'])
    assert result['completed'] is False
    assert len(result['errors']['grant']) > 0


def test_invalid_request(basic_identity_defs, basic_resource_defs, basic_grants):
    invalid_request = {
        "identities": {},  # Missing required User identity
        "resource_type": "Document",
        "action": "read"
        # Missing other required fields
    }
    result = audit_workflow(
        basic_identity_defs,
        basic_resource_defs,
        basic_grants,
        invalid_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['audit'])
    assert result['completed'] is False
    assert len(result['errors']['request']) > 0


def test_context_validation_error(basic_identity_defs, basic_resource_defs, basic_request):
    grants_with_context = [
        {
            "effect": "allow",
            "actions": ["read"],
            "query": "`true`",
            "query_validation": "validate",
            "equality": True,
            "data": {},
            "context_schema": {
                "type": "object",
                "required": ["required_field"],
                "properties": {
                    "required_field": {"type": "string"}
                }
            },
            "context_validation": "error"
        }
    ]
    result = audit_workflow(
        basic_identity_defs,
        basic_resource_defs,
        grants_with_context,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['audit'])
    assert result['completed'] is True
    assert len(result['errors']['context']) > 0


def test_context_validation_critical(basic_identity_defs, basic_resource_defs, basic_request):
    grants_with_critical_context = [
        {
            "effect": "allow",
            "actions": ["read"],
            "query": "`true`",
            "query_validation": "validate",
            "equality": True,
            "data": {},
            "context_schema": {
                "type": "object",
                "required": ["required_field"],
                "properties": {
                    "required_field": {"type": "string"}
                }
            },
            "context_validation": "critical"
        }
    ]
    result = audit_workflow(
        basic_identity_defs,
        basic_resource_defs,
        grants_with_critical_context,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['audit'])
    assert result['completed'] is False
    assert len(result['errors']['context']) > 0
    assert result['errors']['context'][0]['critical'] is True


def test_jmespath_error(basic_identity_defs, basic_resource_defs, basic_request):
    grants_with_bad_query = [
        {
            "effect": "allow",
            "actions": ["read"],
            "query": "invalid[query",  # Invalid JMESPath syntax
            "query_validation": "error",
            "equality": True,
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        }
    ]
    result = audit_workflow(
        basic_identity_defs,
        basic_resource_defs,
        grants_with_bad_query,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['audit'])
    assert result['completed'] is True
    assert len(result['errors']['jmespath']) > 0


def test_jmespath_error_critical(basic_identity_defs, basic_resource_defs, basic_request):
    grants_with_critical_query = [
        {
            "effect": "allow",
            "actions": ["read"],
            "query": "invalid[query",  # Invalid JMESPath syntax
            "query_validation": "critical",
            "equality": True,
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        }
    ]
    result = audit_workflow(
        basic_identity_defs,
        basic_resource_defs,
        grants_with_critical_query,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['audit'])
    assert result['completed'] is False
    assert len(result['errors']['jmespath']) > 0
    assert result['errors']['jmespath'][0]['critical'] is True


def test_request_level_query_validation_override(basic_identity_defs, basic_resource_defs):
    grants_with_bad_query = [
        {
            "effect": "allow",
            "actions": ["read"],
            "query": "invalid[query",
            "query_validation": "validate",  # Grant level is validate
            "equality": True,
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        }
    ]
    request_with_override = {
        "identities": {
            "User": [{"id": "user123", "name": "John Doe"}]
        },
        "resource_type": "Document",
        "action": "read",
        "resource": {"id": "doc1", "title": "Test Document"},
        "parents": {"Folder": []},
        "children": {"Comment": []},
        "query_validation": "error",  # Override to error
        "context": {},
        "context_validation": "grant"
    }
    result = audit_workflow(
        basic_identity_defs,
        basic_resource_defs,
        grants_with_bad_query,
        request_with_override,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['audit'])
    assert result['completed'] is True
    assert len(result['errors']['jmespath']) > 0


def test_request_level_context_validation_override(basic_identity_defs, basic_resource_defs):
    grants_with_context = [
        {
            "effect": "allow",
            "actions": ["read"],
            "query": "`true`",
            "query_validation": "validate",
            "equality": True,
            "data": {},
            "context_schema": {
                "type": "object",
                "required": ["required_field"]
            },
            "context_validation": "validate"  # Grant level is validate
        }
    ]
    request_with_override = {
        "identities": {
            "User": [{"id": "user123", "name": "John Doe"}]
        },
        "resource_type": "Document",
        "action": "read",
        "resource": {"id": "doc1", "title": "Test Document"},
        "parents": {"Folder": []},
        "children": {"Comment": []},
        "query_validation": "grant",
        "context": {},  # Invalid context
        "context_validation": "error"  # Override to error
    }
    result = audit_workflow(
        basic_identity_defs,
        basic_resource_defs,
        grants_with_context,
        request_with_override,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['audit'])
    assert result['completed'] is True
    assert len(result['errors']['context']) > 0


def test_empty_actions_grant(basic_identity_defs, basic_resource_defs, basic_request):
    universal_grant = [
        {
            "effect": "allow",
            "actions": [],  # Empty actions matches all
            "query": "`true`",
            "query_validation": "validate",
            "equality": True,
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        }
    ]
    result = audit_workflow(
        basic_identity_defs,
        basic_resource_defs,
        universal_grant,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['audit'])
    assert result['completed'] is True
    assert len(result['grants']) == 1


def test_no_matching_grants(basic_identity_defs, basic_resource_defs, basic_request):
    non_matching_grants = [
        {
            "effect": "allow",
            "actions": ["write"],  # Different action
            "query": "`true`",
            "query_validation": "validate",
            "equality": True,
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        }
    ]
    result = audit_workflow(
        basic_identity_defs,
        basic_resource_defs,
        non_matching_grants,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['audit'])
    assert result['completed'] is True
    assert len(result['grants']) == 0


def test_successful_authorization(basic_identity_defs, basic_resource_defs, basic_grants, basic_request):
    result = authorize_workflow(
        basic_identity_defs,
        basic_resource_defs,
        basic_grants,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['authorize'])
    assert result['authorized'] is True
    assert result['completed'] is True
    assert result['grant'] is not None
    assert "allow grant is applicable" in result['message']
    assert all(len(errors) == 0 for errors in result['errors'].values())


def test_deny_authorization(basic_identity_defs, basic_resource_defs, basic_grants):
    delete_request = {
        "identities": {
            "User": [{"id": "user123", "name": "John Doe"}]
        },
        "resource_type": "Document",
        "action": "delete",
        "resource": {
            "id": "doc1",
            "title": "protected",  # This will trigger deny grant
            "owner": "user123"
        },
        "parents": {"Folder": []},
        "children": {"Comment": []},
        "query_validation": "grant",
        "context": {},
        "context_validation": "grant"
    }
    result = authorize_workflow(
        basic_identity_defs,
        basic_resource_defs,
        basic_grants,
        delete_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['authorize'])
    assert result['authorized'] is False
    assert result['completed'] is True
    assert result['grant'] is not None
    assert result['grant']['effect'] == 'deny'
    assert "deny grant is applicable" in result['message']


def test_implicit_deny(basic_identity_defs, basic_resource_defs):
    no_grants = []
    request = {
        "identities": {
            "User": [{"id": "user123", "name": "John Doe"}]
        },
        "resource_type": "Document",
        "action": "read",
        "resource": {"id": "doc1", "title": "Test Document"},
        "parents": {"Folder": []},
        "children": {"Comment": []},
        "query_validation": "grant",
        "context": {},
        "context_validation": "grant"
    }  
    result = authorize_workflow(
        basic_identity_defs,
        basic_resource_defs,
        no_grants,
        request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['authorize'])
    assert result['authorized'] is False
    assert result['completed'] is True
    assert result['grant'] is None
    assert "implicitly denied" in result['message']


def test_invalid_definitions_authorization(basic_resource_defs, basic_grants, basic_request):
    invalid_identity_defs = [{"identity_type": "User"}]  # Missing schema
    result = authorize_workflow(
        invalid_identity_defs,
        basic_resource_defs,
        basic_grants,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas([{"identity_type": "User", "schema": {"type": "object"}}], basic_resource_defs)
    jsonschema.validate(result, schemas['authorize'])
    assert result['authorized'] is False
    assert result['completed'] is False
    assert result['grant'] is None
    assert "definitions are not valid" in result['message']
    assert len(result['errors']['definition']) > 0


def test_invalid_grants_authorization(basic_identity_defs, basic_resource_defs, basic_request):
    invalid_grants = [{"effect": "allow"}]  # Missing required fields
    result = authorize_workflow(
        basic_identity_defs,
        basic_resource_defs,
        invalid_grants,
        basic_request,
        jmespath.search
    )
    # Validate against schema
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['authorize'])
    assert result['authorized'] is False
    assert result['completed'] is False
    assert result['grant'] is None
    assert "grants are not valid" in result['message']
    assert len(result['errors']['grant']) > 0


def test_invalid_request_authorization(basic_identity_defs, basic_resource_defs, basic_grants):
    invalid_request = {"action": "read"}  # Missing required fields
    result = authorize_workflow(
        basic_identity_defs,
        basic_resource_defs,
        basic_grants,
        invalid_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['authorize'])
    assert result['authorized'] is False
    assert result['completed'] is False
    assert result['grant'] is None
    assert "request is not valid" in result['message']
    assert len(result['errors']['request']) > 0


def test_critical_error_in_deny_grant(basic_identity_defs, basic_resource_defs, basic_request):
    critical_deny_grant = [
        {
            "effect": "deny",
            "actions": ["read"],
            "query": "invalid[query",
            "query_validation": "critical",
            "equality": True,
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        }
    ]
    result = authorize_workflow(
        basic_identity_defs,
        basic_resource_defs,
        critical_deny_grant,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['authorize'])
    assert result['authorized'] is False
    assert result['completed'] is False
    assert "critical error has occurred" in result['message']
    assert len(result['errors']['jmespath']) > 0


def test_critical_error_in_allow_grant(basic_identity_defs, basic_resource_defs, basic_request):
    critical_allow_grant = [
        {
            "effect": "allow",
            "actions": ["read"],
            "query": "invalid[query",
            "query_validation": "critical",
            "equality": True,
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        }
    ]
    result = authorize_workflow(
        basic_identity_defs,
        basic_resource_defs,
        critical_allow_grant,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['authorize'])
    assert result['authorized'] is False
    assert result['completed'] is False
    assert "critical error has occurred" in result['message']
    assert len(result['errors']['jmespath']) > 0


def test_grants_with_different_actions(basic_identity_defs, basic_resource_defs, basic_request):
    different_action_grants = [
        {
            "effect": "allow",
            "actions": ["write", "delete"],  # Different from 'read' in request
            "query": "`true`",
            "query_validation": "validate",
            "equality": True,
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        }
    ]
    result = authorize_workflow(
        basic_identity_defs,
        basic_resource_defs,
        different_action_grants,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['authorize'])
    assert result['authorized'] is False
    assert result['completed'] is True
    assert result['grant'] is None
    assert "implicitly denied" in result['message']


def test_context_validation_settings(basic_identity_defs, basic_resource_defs):
    grants_with_context = [
        {
            "effect": "allow",
            "actions": ["read"],
            "query": "`true`",
            "query_validation": "validate",
            "equality": True,
            "data": {},
            "context_schema": {
                "type": "object",
                "required": ["missing_field"]
            },
            "context_validation": "validate"  # Will make grant non-applicable
        }
    ]
    request = {
        "identities": {
            "User": [{"id": "user123", "name": "John Doe"}]
        },
        "resource_type": "Document",
        "action": "read",
        "resource": {"id": "doc1", "title": "Test Document"},
        "parents": {"Folder": []},
        "children": {"Comment": []},
        "query_validation": "grant",
        "context": {},  # Missing required field
        "context_validation": "grant"
    }
    result = authorize_workflow(
        basic_identity_defs,
        basic_resource_defs,
        grants_with_context,
        request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['authorize'])
    assert result['authorized'] is False
    assert result['completed'] is True
    assert "implicitly denied" in result['message']


def test_both_allow_and_deny_grants_non_applicable(basic_identity_defs, basic_resource_defs, basic_request):
    non_applicable_grants = [
        {
            "effect": "deny",
            "actions": ["read"],
            "query": "request.resource.title == 'never_matches'",
            "query_validation": "validate",
            "equality": True,
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        },
        {
            "effect": "allow",
            "actions": ["read"],
            "query": "request.resource.owner == 'never_matches'",
            "query_validation": "validate",
            "equality": True,
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        }
    ]
    result = authorize_workflow(
        basic_identity_defs,
        basic_resource_defs,
        non_applicable_grants,
        basic_request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['authorize'])
    assert result['authorized'] is False
    assert result['completed'] is True
    assert result['grant'] is None
    assert "implicitly denied" in result['message']


# def test_empty_lists():
#     empty_identity_defs = []
#     empty_resource_defs = []
#     empty_grants = []
#     result = audit_workflow(
#         empty_identity_defs,
#         empty_resource_defs,
#         empty_grants,
#         {},
#         jmespath.search
#     )
#     assert result['completed'] is False


def test_malformed_json_schemas_in_definitions():
    malformed_identity_defs = [
        {
            "identity_type": "User",
            "schema": "not_a_schema"  # Should be object
        }
    ]
    basic_resource_defs = [
        {
            "resource_type": "Document",
            "actions": ["read"],
            "schema": {"type": "object"},
            "parent_types": [],
            "child_types": []
        }
    ]
    result = audit_workflow(
        malformed_identity_defs,
        basic_resource_defs,
        [],
        {},
        jmespath.search
    )
    assert result['completed'] is False
    assert len(result['errors']['definition']) > 0


def test_context_validation_none_setting(basic_identity_defs, basic_resource_defs):
    grants_with_context_none = [
        {
            "effect": "allow",
            "actions": ["read"],
            "query": "`true`",
            "query_validation": "validate",
            "equality": True,
            "data": {},
            "context_schema": {
                "type": "object",
                "required": ["required_field"]
            },
            "context_validation": "none"  # Should not validate context
        }
    ] 
    request = {
        "identities": {
            "User": [{"id": "user123", "name": "John Doe"}]
        },
        "resource_type": "Document",
        "action": "read",
        "resource": {"id": "doc1", "title": "Test Document"},
        "parents": {"Folder": []},
        "children": {"Comment": []},
        "query_validation": "grant",
        "context": {},  # Invalid context but should be ignored
        "context_validation": "grant"
    }
    result = authorize_workflow(
        basic_identity_defs,
        basic_resource_defs,
        grants_with_context_none,
        request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['authorize'])
    assert result['authorized'] is True  # Should succeed despite invalid context
    assert result['completed'] is True


def test_query_equality_with_various_types(basic_identity_defs, basic_resource_defs):
    grants_with_different_equalities = [
        {
            "effect": "allow",
            "actions": ["read"],
            "query": "`false`",  # Returns boolean false
            "query_validation": "validate",
            "equality": False,  # Should match
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        },
        {
            "effect": "allow",
            "actions": ["read"],
            "query": "`42`",  # Returns number 42
            "query_validation": "validate",
            "equality": 42,  # Should match
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        },
        {
            "effect": "allow",
            "actions": ["read"],
            "query": "`\"hello\"`",  # Returns string "hello"
            "query_validation": "validate",
            "equality": "hello",  # Should match
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        }
    ]
    request = {
        "identities": {
            "User": [{"id": "user123", "name": "John Doe"}]
        },
        "resource_type": "Document",
        "action": "read",
        "resource": {"id": "doc1", "title": "Test Document"},
        "parents": {"Folder": []},
        "children": {"Comment": []},
        "query_validation": "grant",
        "context": {},
        "context_validation": "grant"
    }
    result = audit_workflow(
        basic_identity_defs,
        basic_resource_defs,
        grants_with_different_equalities,
        request,
        jmespath.search
    )
    schemas = generate_schemas(basic_identity_defs, basic_resource_defs)
    jsonschema.validate(result, schemas['audit'])
    assert result['completed'] is True
    assert len(result['grants']) == 3  
