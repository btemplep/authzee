"""Complete test suite for 100% coverage of reference.py"""
import pytest
import jmespath
import jsonschema
from src.reference import (
    validate_definitions,
    generate_schemas,
    validate_grants,
    validate_request,
    evaluate_one,
    audit,
    authorize,
    audit_workflow,
    authorize_workflow
)


@pytest.fixture
def identity_defs():
    return [
        {
            "identity_type": "User",
            "schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "role": {"type": "string"}
                },
                "required": ["id", "role"]
            }
        }
    ]


@pytest.fixture
def resource_defs():
    return [
        {
            "resource_type": "Document",
            "actions": ["read", "write"],
            "schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "owner": {"type": "string"}
                },
                "required": ["id"]
            },
            "parent_types": [],
            "child_types": []
        }
    ]


@pytest.fixture
def basic_request():
    return {
        "identities": {
            "User": [{"id": "user1", "role": "admin"}]
        },
        "resource_type": "Document",
        "action": "read",
        "resource": {"id": "doc1", "owner": "user1"},
        "parents": {},
        "children": {},
        "query_validation": "grant",
        "context": {},
        "context_validation": "grant"
    }


class TestValidateDefinitions:
    def test_valid_definitions(self, identity_defs, resource_defs):
        result = validate_definitions(identity_defs, resource_defs)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_invalid_identity_schema(self, resource_defs):
        invalid_identity = [{"identity_type": "User"}]  # Missing schema
        result = validate_definitions(invalid_identity, resource_defs)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert result["errors"][0]["definition_type"] == "identity"

    def test_duplicate_identity_types(self, resource_defs):
        duplicate_identities = [
            {"identity_type": "User", "schema": {"type": "object"}},
            {"identity_type": "User", "schema": {"type": "object"}}
        ]
        result = validate_definitions(duplicate_identities, resource_defs)
        assert result["valid"] is False
        assert any("unique" in error["message"] for error in result["errors"])

    def test_invalid_resource_schema(self, identity_defs):
        invalid_resource = [{"resource_type": "Doc"}]  # Missing required fields
        result = validate_definitions(identity_defs, invalid_resource)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert result["errors"][0]["definition_type"] == "resource"

    def test_duplicate_resource_types(self, identity_defs):
        duplicate_resources = [
            {
                "resource_type": "Document",
                "actions": ["read"],
                "schema": {"type": "object"},
                "parent_types": [],
                "child_types": []
            },
            {
                "resource_type": "Document",
                "actions": ["write"],
                "schema": {"type": "object"},
                "parent_types": [],
                "child_types": []
            }
        ]
        result = validate_definitions(identity_defs, duplicate_resources)
        assert result["valid"] is False
        assert any("unique" in error["message"] for error in result["errors"])

    def test_invalid_parent_type(self, identity_defs):
        resource_with_invalid_parent = [
            {
                "resource_type": "Document",
                "actions": ["read"],
                "schema": {"type": "object"},
                "parent_types": ["NonExistent"],
                "child_types": []
            }
        ]
        result = validate_definitions(identity_defs, resource_with_invalid_parent)
        assert result["valid"] is False
        assert any("Parent type" in error["message"] for error in result["errors"])

    def test_invalid_child_type(self, identity_defs):
        resource_with_invalid_child = [
            {
                "resource_type": "Document",
                "actions": ["read"],
                "schema": {"type": "object"},
                "parent_types": [],
                "child_types": ["NonExistent"]
            }
        ]
        result = validate_definitions(identity_defs, resource_with_invalid_child)
        assert result["valid"] is False
        assert any("Child type" in error["message"] for error in result["errors"])


class TestValidateGrants:
    def test_valid_grants(self, identity_defs, resource_defs):
        schemas = generate_schemas(identity_defs, resource_defs)
        grants = [
            {
                "effect": "allow",
                "actions": ["read"],
                "query": "`true`",
                "query_validation": "validate",
                "equality": True,
                "data": {},
                "context_schema": {"type": "object"},
                "context_validation": "none"
            }
        ]
        result = validate_grants(grants, schemas["grant"])
        assert result["valid"] is True
        assert result["errors"] == []
        # Validate grant against schema
        jsonschema.validate(grants[0], schemas["grant"])

    def test_invalid_grants(self, identity_defs, resource_defs):
        schemas = generate_schemas(identity_defs, resource_defs)
        invalid_grants = [{"effect": "allow"}]  # Missing required fields
        result = validate_grants(invalid_grants, schemas["grant"])
        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestGenerateSchemas:
    def test_generate_schemas_with_parent_and_child_types(self, identity_defs):
        resource_defs = [
            {
                "resource_type": "Parent",
                "actions": ["read"],
                "schema": {"type": "object", "properties": {"id": {"type": "string"}}},
                "parent_types": [],
                "child_types": ["Child"]
            },
            {
                "resource_type": "Child", 
                "actions": ["write"],
                "schema": {"type": "object", "properties": {"id": {"type": "string"}}},
                "parent_types": ["Parent"],
                "child_types": []
            }
        ]
        schemas = generate_schemas(identity_defs, resource_defs)
        # This covers lines 676-677 and 685-686
        assert "Parent" in schemas["request"]["$defs"]
        assert "Child" in schemas["request"]["$defs"]


class TestValidateRequest:
    def test_valid_request(self, identity_defs, resource_defs, basic_request):
        schemas = generate_schemas(identity_defs, resource_defs)
        result = validate_request(basic_request, schemas["request"])
        assert result["valid"] is True
        assert result["errors"] == []
        # Validate request against schema
        jsonschema.validate(basic_request, schemas["request"])

    def test_invalid_request(self, identity_defs, resource_defs):
        schemas = generate_schemas(identity_defs, resource_defs)
        invalid_request = {"action": "read"}  # Missing required fields
        result = validate_request(invalid_request, schemas["request"])
        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestEvaluateOne:
    def test_action_not_in_grant_actions_with_non_empty_actions(self, basic_request):
        grant = {
            "actions": ["write"],  # Different from request action "read"
            "context_validation": "none",
            "query": "`true`",
            "equality": True
        }
        result = evaluate_one(basic_request, grant, jmespath.search, False)
        assert result["applicable"] is False
        assert result["critical"] is False

    def test_action_not_in_grant_actions_with_empty_actions(self, basic_request):
        grant = {
            "actions": [],  # Empty actions should match all
            "context_validation": "none",
            "query": "`true`",
            "equality": True
        }
        result = evaluate_one(basic_request, grant, jmespath.search, False)
        assert result["applicable"] is True

    def test_context_validation_none(self, basic_request):
        grant = {
            "actions": ["read"],
            "context_validation": "none",
            "query": "`true`",
            "equality": True,
            "context_schema": {"type": "object", "required": ["missing"]}
        }
        result = evaluate_one(basic_request, grant, jmespath.search, False)
        assert result["applicable"] is True

    def test_context_validation_validate_with_valid_context(self, basic_request):
        grant = {
            "actions": ["read"],
            "context_validation": "validate",
            "query": "`true`",
            "equality": True,
            "context_schema": {"type": "object"}
        }
        result = evaluate_one(basic_request, grant, jmespath.search, False)
        assert result["applicable"] is True

    def test_context_validation_validate_with_invalid_context(self, basic_request):
        grant = {
            "actions": ["read"],
            "context_validation": "validate",
            "query": "`true`",
            "equality": True,
            "context_schema": {"type": "object", "required": ["missing"]}
        }
        result = evaluate_one(basic_request, grant, jmespath.search, False)
        assert result["applicable"] is False

    def test_context_validation_error_with_invalid_context_only_crits_false(self, basic_request):
        grant = {
            "actions": ["read"],
            "context_validation": "error",
            "query": "`true`",
            "equality": True,
            "context_schema": {"type": "object", "required": ["missing"]}
        }
        result = evaluate_one(basic_request, grant, jmespath.search, False)
        assert result["applicable"] is False
        assert result["critical"] is False
        assert len(result["errors"]["context"]) == 1
        assert result["errors"]["context"][0]["critical"] is False

    def test_context_validation_critical_with_invalid_context(self, basic_request):
        grant = {
            "actions": ["read"],
            "context_validation": "critical",
            "query": "`true`",
            "equality": True,
            "context_schema": {"type": "object", "required": ["missing"]}
        }
        result = evaluate_one(basic_request, grant, jmespath.search, False)
        assert result["applicable"] is False
        assert result["critical"] is True
        assert len(result["errors"]["context"]) == 1
        assert result["errors"]["context"][0]["critical"] is True

    def test_jmespath_error_with_error_validation_only_crits_false(self, basic_request):
        grant = {
            "actions": ["read"],
            "context_validation": "none",
            "query": "invalid_jmespath_query[",
            "query_validation": "error",
            "equality": True
        }
        result = evaluate_one(basic_request, grant, jmespath.search, False)
        assert result["applicable"] is False
        assert result["critical"] is False
        assert len(result["errors"]["jmespath"]) == 1
        assert result["errors"]["jmespath"][0]["critical"] is False

    def test_jmespath_error_with_critical_validation(self, basic_request):
        grant = {
            "actions": ["read"],
            "context_validation": "none",
            "query": "invalid_jmespath_query[",
            "query_validation": "critical",
            "equality": True
        }
        result = evaluate_one(basic_request, grant, jmespath.search, False)
        assert result["applicable"] is False
        assert result["critical"] is True
        assert len(result["errors"]["jmespath"]) == 1
        assert result["errors"]["jmespath"][0]["critical"] is True


    def test_context_validation_error_with_invalid_context_only_crits_true(self, basic_request):
        grant = {
            "actions": ["read"],
            "context_validation": "error",
            "query": "`true`",
            "equality": False,
            "context_schema": {"type": "object", "required": ["missing"]}
        }
        result = evaluate_one(basic_request, grant, jmespath.search, True)
        print(result)
        assert result["applicable"] is False
        assert len(result["errors"]["context"]) == 0  # Should not add errors when only_crits=True

    def test_context_validation_critical_with_invalid_context(self, basic_request):
        grant = {
            "actions": ["read"],
            "context_validation": "critical",
            "query": "`true`",
            "equality": True,
            "context_schema": {"type": "object", "required": ["missing"]}
        }
        result = evaluate_one(basic_request, grant, jmespath.search, True)
        assert result["applicable"] is False
        assert result["critical"] is True
        assert len(result["errors"]["context"]) > 0
        assert result["errors"]["context"][0]["critical"] is True

    def test_request_context_validation_override(self):
        request = {
            "action": "read",
            "context_validation": "error",  # Override grant setting
            "context": {}
        }
        grant = {
            "actions": ["read"],
            "context_validation": "validate",  # Will be overridden
            "query": "`true`",
            "equality": True,
            "context_schema": {"type": "object", "required": ["missing"]}
        }
        result = evaluate_one(request, grant, jmespath.search, False)
        assert result["applicable"] is False
        assert len(result["errors"]["context"]) > 0

    def test_query_success_with_matching_equality(self, basic_request):
        grant = {
            "actions": ["read"],
            "context_validation": "none",
            "query": "`true`",
            "equality": True
        }
        result = evaluate_one(basic_request, grant, jmespath.search, False)
        assert result["applicable"] is True

    def test_query_success_with_non_matching_equality(self, basic_request):
        grant = {
            "actions": ["read"],
            "context_validation": "none",
            "query": "`true`",
            "equality": False  # Query returns true, but equality expects false
        }
        result = evaluate_one(basic_request, grant, jmespath.search, False)
        assert result["applicable"] is False

    def test_jmespath_error_with_validate_query_validation(self, basic_request):
        grant = {
            "actions": ["read"],
            "context_validation": "none",
            "query": "invalid[syntax",
            "query_validation": "validate",
            "equality": True
        }
        result = evaluate_one(basic_request, grant, jmespath.search, False)
        assert result["applicable"] is False
        assert len(result["errors"]["jmespath"]) == 0  # validate doesn't add errors

    def test_jmespath_error_with_error_query_validation_only_crits_false(self, basic_request):
        grant = {
            "actions": ["read"],
            "context_validation": "none",
            "query": "invalid[syntax",
            "query_validation": "error",
            "equality": True
        }
        result = evaluate_one(basic_request, grant, jmespath.search, False)
        assert result["applicable"] is False
        assert len(result["errors"]["jmespath"]) > 0
        assert result["errors"]["jmespath"][0]["critical"] is False

    def test_jmespath_error_with_error_query_validation_only_crits_true(self, basic_request):
        grant = {
            "actions": ["read"],
            "context_validation": "none",
            "query": "invalid[syntax",
            "query_validation": "error",
            "equality": True
        }
        result = evaluate_one(basic_request, grant, jmespath.search, True)
        assert result["applicable"] is False
        assert len(result["errors"]["jmespath"]) == 0  # Should not add when only_crits=True

    def test_jmespath_error_with_critical_query_validation(self, basic_request):
        grant = {
            "actions": ["read"],
            "context_validation": "none",
            "query": "invalid[syntax",
            "query_validation": "critical",
            "equality": True
        }
        result = evaluate_one(basic_request, grant, jmespath.search, True)
        assert result["applicable"] is False
        assert result["critical"] is True
        assert len(result["errors"]["jmespath"]) > 0
        assert result["errors"]["jmespath"][0]["critical"] is True

    def test_request_query_validation_override(self):
        request = {
            "action": "read",
            "context_validation": "none",
            "query_validation": "error",  # Override grant setting
            "context": {}
        }
        grant = {
            "actions": ["read"],
            "context_validation": "none",
            "query": "invalid[syntax",
            "query_validation": "validate",  # Will be overridden
            "equality": True
        }
        result = evaluate_one(request, grant, jmespath.search, False)
        assert result["applicable"] is False
        assert len(result["errors"]["jmespath"]) > 0


class TestAudit:
    def test_successful_audit(self, basic_request):
        grants = [
            {
                "actions": ["read"],
                "context_validation": "none",
                "query": "`true`",
                "equality": True
            }
        ]
        result = audit(basic_request, grants, jmespath.search)
        assert result["completed"] is True
        assert len(result["grants"]) == 1

    def test_audit_with_critical_error(self, basic_request):
        grants = [
            {
                "actions": ["read"],
                "context_validation": "critical",
                "query": "`true`",
                "equality": True,
                "context_schema": {"type": "object", "required": ["missing"]}
            }
        ]
        result = audit(basic_request, grants, jmespath.search)
        assert result["completed"] is False
        assert len(result["grants"]) == 0

    def test_audit_with_non_applicable_grant(self, basic_request):
        grants = [
            {
                "actions": ["write"],  # Different action
                "context_validation": "none",
                "query": "`true`",
                "equality": True
            }
        ]
        result = audit(basic_request, grants, jmespath.search)
        assert result["completed"] is True
        assert len(result["grants"]) == 0

    def test_audit_with_applicable_grant_after_critical(self, basic_request):
        grants = [
            {
                "actions": ["read"],
                "context_validation": "critical",
                "query": "`true`",
                "equality": True,
                "context_schema": {"type": "object", "required": ["missing"]}
            },
            {
                "actions": ["read"],
                "context_validation": "none",
                "query": "`true`",
                "equality": True
            }
        ]
        result = audit(basic_request, grants, jmespath.search)
        assert result["completed"] is False


class TestAuthorize:
    def test_successful_allow_authorization(self, basic_request):
        grants = [
            {
                "effect": "allow",
                "actions": ["read"],
                "context_validation": "none",
                "query": "`true`",
                "equality": True
            }
        ]
        result = authorize(basic_request, grants, jmespath.search)
        assert result["authorized"] is True
        assert result["completed"] is True
        assert result["grant"]["effect"] == "allow"

    def test_deny_grant_applicable(self, basic_request):
        grants = [
            {
                "effect": "deny",
                "actions": ["read"],
                "context_validation": "none",
                "query": "`true`",
                "equality": True
            }
        ]
        result = authorize(basic_request, grants, jmespath.search)
        assert result["authorized"] is False
        assert result["completed"] is True
        assert result["grant"]["effect"] == "deny"
        assert "deny grant is applicable" in result["message"]

    def test_critical_error_in_deny_grant(self, basic_request):
        grants = [
            {
                "effect": "deny",
                "actions": ["read"],
                "context_validation": "critical",
                "query": "`true`",
                "equality": True,
                "context_schema": {"type": "object", "required": ["missing"]}
            }
        ]
        result = authorize(basic_request, grants, jmespath.search)
        assert result["authorized"] is False
        assert result["completed"] is False
        assert "critical error has occurred" in result["message"]

    def test_critical_error_in_allow_grant(self, basic_request):
        grants = [
            {
                "effect": "allow",
                "actions": ["read"],
                "context_validation": "critical",
                "query": "`true`",
                "equality": True,
                "context_schema": {"type": "object", "required": ["missing"]}
            }
        ]
        result = authorize(basic_request, grants, jmespath.search)
        assert result["authorized"] is False
        assert result["completed"] is False
        assert "critical error has occurred" in result["message"]

    def test_implicit_deny_no_grants(self, basic_request):
        grants = []
        result = authorize(basic_request, grants, jmespath.search)
        assert result["authorized"] is False
        assert result["completed"] is True
        assert result["grant"] is None
        assert "implicitly denied" in result["message"]

    def test_implicit_deny_no_applicable_grants(self, basic_request):
        grants = [
            {
                "effect": "allow",
                "actions": ["write"],  # Different action
                "context_validation": "none",
                "query": "`true`",
                "equality": True
            }
        ]
        result = authorize(basic_request, grants, jmespath.search)
        assert result["authorized"] is False
        assert result["completed"] is True
        assert result["grant"] is None
        assert "implicitly denied" in result["message"]

    def test_authorize_with_mixed_grants(self, basic_request):
        grants = [
            {
                "effect": "deny",
                "actions": ["write"],  # Different action, not applicable
                "context_validation": "none",
                "query": "`true`",
                "equality": True
            },
            {
                "effect": "allow",
                "actions": ["read"],
                "context_validation": "none",
                "query": "`true`",
                "equality": True
            }
        ]
        result = authorize(basic_request, grants, jmespath.search)
        assert result["authorized"] is True
        assert result["completed"] is True
        assert result["grant"]["effect"] == "allow"


class TestWorkflows:
    def test_audit_workflow_invalid_definitions(self, resource_defs, basic_request):
        invalid_identity_defs = [{"identity_type": "User"}]  # Missing schema
        result = audit_workflow(invalid_identity_defs, resource_defs, [], basic_request, jmespath.search)
        assert result["completed"] is False
        assert len(result["errors"]["definition"]) > 0

    def test_audit_workflow_invalid_grants(self, identity_defs, resource_defs, basic_request):
        invalid_grants = [{"effect": "allow"}]  # Missing required fields
        result = audit_workflow(identity_defs, resource_defs, invalid_grants, basic_request, jmespath.search)
        assert result["completed"] is False
        assert len(result["errors"]["grant"]) > 0

    def test_audit_workflow_invalid_request(self, identity_defs, resource_defs):
        invalid_request = {"action": "read"}  # Missing required fields
        result = audit_workflow(identity_defs, resource_defs, [], invalid_request, jmespath.search)
        assert result["completed"] is False
        assert len(result["errors"]["request"]) > 0

    def test_authorize_workflow_invalid_definitions(self, resource_defs, basic_request):
        invalid_identity_defs = [{"identity_type": "User"}]  # Missing schema
        result = authorize_workflow(invalid_identity_defs, resource_defs, [], basic_request, jmespath.search)
        assert result["authorized"] is False
        assert result["completed"] is False
        assert "definitions are not valid" in result["message"]

    def test_authorize_workflow_invalid_grants(self, identity_defs, resource_defs, basic_request):
        invalid_grants = [{"effect": "allow"}]  # Missing required fields
        result = authorize_workflow(identity_defs, resource_defs, invalid_grants, basic_request, jmespath.search)
        assert result["authorized"] is False
        assert result["completed"] is False
        assert "grants are not valid" in result["message"]

    def test_authorize_workflow_invalid_request(self, identity_defs, resource_defs):
        invalid_request = {"action": "read"}  # Missing required fields
        result = authorize_workflow(identity_defs, resource_defs, [], invalid_request, jmespath.search)
        assert result["authorized"] is False
        assert result["completed"] is False
        assert "request is not valid" in result["message"]

    def test_authorize_workflow_success(self, identity_defs, resource_defs, basic_request):
        grants = [
            {
                "effect": "allow",
                "actions": ["read"],
                "query": "`true`",
                "query_validation": "validate",
                "equality": True,
                "data": {},
                "context_schema": {"type": "object"},
                "context_validation": "none"
            }
        ]
        result = authorize_workflow(identity_defs, resource_defs, grants, basic_request, jmespath.search)
        assert result["authorized"] is True
        assert result["completed"] is True

    def test_audit_workflow_success(self, identity_defs, resource_defs, basic_request):
        grants = [
            {
                "effect": "allow",
                "actions": ["read"],
                "query": "`true`",
                "query_validation": "validate",
                "equality": True,
                "data": {},
                "context_schema": {"type": "object"},
                "context_validation": "none"
            }
        ]
        result = audit_workflow(identity_defs, resource_defs, grants, basic_request, jmespath.search)
        assert result["completed"] is True
        assert len(result["grants"]) == 1

    def test_audit_workflow_calls_audit(self, identity_defs, resource_defs, basic_request):
        grants = [
            {
                "effect": "allow",
                "actions": ["read"],
                "query": "`true`",
                "query_validation": "validate",
                "equality": True,
                "data": {},
                "context_schema": {"type": "object"},
                "context_validation": "none"
            }
        ]
        result = audit_workflow(identity_defs, resource_defs, grants, basic_request, jmespath.search)
        # This should call the audit function and return its result
        direct_audit = audit(basic_request, grants, jmespath.search)
        assert result["completed"] == direct_audit["completed"]
        assert len(result["grants"]) == len(direct_audit["grants"])

    def test_authorize_workflow_calls_authorize(self, identity_defs, resource_defs, basic_request):
        grants = [
            {
                "effect": "allow",
                "actions": ["read"],
                "query": "`true`",
                "query_validation": "validate",
                "equality": True,
                "data": {},
                "context_schema": {"type": "object"},
                "context_validation": "none"
            }
        ]
        result = authorize_workflow(identity_defs, resource_defs, grants, basic_request, jmespath.search)
        # This should call the authorize function and return its result
        direct_authorize = authorize(basic_request, grants, jmespath.search)
        assert result["authorized"] == direct_authorize["authorized"]
        assert result["completed"] == direct_authorize["completed"]


class TestAuditSchemas:
    def test_audit_response_schema(self, identity_defs, resource_defs, basic_request):
        schemas = generate_schemas(identity_defs, resource_defs)
        grants = [{
            "effect": "allow",
            "actions": ["read"],
            "query": "`true`",
            "query_validation": "validate",
            "equality": True,
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        }]
        result = audit(basic_request, grants, jmespath.search)
        # Validate audit response against schema
        jsonschema.validate(result, schemas["audit"])


class TestAuthorizeSchemas:
    def test_authorize_response_schema(self, identity_defs, resource_defs, basic_request):
        schemas = generate_schemas(identity_defs, resource_defs)
        grants = [{
            "effect": "allow",
            "actions": ["read"],
            "query": "`true`",
            "query_validation": "validate",
            "equality": True,
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        }]
        result = authorize(basic_request, grants, jmespath.search)
        # Validate authorize response against schema
        jsonschema.validate(result, schemas["authorize"])


class TestWorkflowSchemas:
    def test_audit_workflow_response_schema(self, identity_defs, resource_defs, basic_request):
        schemas = generate_schemas(identity_defs, resource_defs)
        grants = [{
            "effect": "allow",
            "actions": ["read"],
            "query": "`true`",
            "query_validation": "validate",
            "equality": True,
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        }]
        result = audit_workflow(identity_defs, resource_defs, grants, basic_request, jmespath.search)
        # Validate workflow response against schema
        jsonschema.validate(result, schemas["audit"])

    def test_authorize_workflow_response_schema(self, identity_defs, resource_defs, basic_request):
        schemas = generate_schemas(identity_defs, resource_defs)
        grants = [{
            "effect": "allow",
            "actions": ["read"],
            "query": "`true`",
            "query_validation": "validate",
            "equality": True,
            "data": {},
            "context_schema": {"type": "object"},
            "context_validation": "none"
        }]
        result = authorize_workflow(identity_defs, resource_defs, grants, basic_request, jmespath.search)
        # Validate workflow response against schema
        jsonschema.validate(result, schemas["authorize"])