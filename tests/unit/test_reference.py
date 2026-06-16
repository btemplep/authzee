import pytest
import jmespath
from src.reference import *


def execute(expression, data):
    result = {"result": None, "has_failed": False, "error_message": None}
    try:
        result['result'] = jmespath.search(expression, data)
    except Exception as exc:
        result['has_failed'] = True
        result['error_message'] = str(exc)
    return result


def failing_execute(expression, data):
    return {"result": None, "has_failed": True, "error_message": "forced failure"}


@pytest.fixture
def context_defs():
    return [{"context_type": "NULL", "schema": {"type": "object", "additionalProperties": False}}]


@pytest.fixture
def identity_defs():
    return [
        {
            "identity_type": "User",
            "schema": {
                "type": "object",
                "required": ["id", "role"],
                "properties": {"id": {"type": "string"}, "role": {"type": "string"}},
            },
        }
    ]


@pytest.fixture
def resource_defs():
    return [
        {
            "resource_type": "Widget",
            "actions": ["Widget:Read", "Widget:Write"],
            "schema": {
                "type": "object",
                "required": ["id"],
                "properties": {"id": {"type": "string"}},
            },
        }
    ]


@pytest.fixture
def allow_grant():
    return {
        "effect": "allow",
        "actions": ["Widget:Read"],
        "query": "request.identities.User[0].role == 'admin'",
        "evaluation_handler": "evaluate",
        "equality": True,
        "data": {},
    }


@pytest.fixture
def deny_grant():
    return {
        "effect": "deny",
        "actions": ["Widget:Read"],
        "query": "request.identities.User[0].role == 'banned'",
        "evaluation_handler": "evaluate",
        "equality": True,
        "data": {},
    }


@pytest.fixture
def admin_request():
    return {
        "identities": {"User": [{"id": "u1", "role": "admin"}]},
        "action": "Widget:Read",
        "resource_type": "Widget",
        "resource": {"id": "w1"},
        "context_type": "NULL",
        "context": {},
        "evaluation_handler": "grant",
    }


@pytest.fixture
def banned_request(admin_request):
    return {**admin_request, "identities": {"User": [{"id": "u2", "role": "banned"}]}}


@pytest.fixture
def guest_request(admin_request):
    return {**admin_request, "identities": {"User": [{"id": "u3", "role": "guest"}]}}


@pytest.fixture
def base_batch():
    return {
        "identities": {"User": [{"id": "u1", "role": "admin"}]},
        "action": "Widget:Read",
        "resource_type": "Widget",
        "resource": {"id": "w1"},
        "context_type": "NULL",
        "context": {},
        "evaluation_handler": "grant",
        "batch": [{}],
    }


def test_validate_context_defs_valid(context_defs):
    r = validate_context_defs(context_defs)
    assert r['is_valid'] is True
    assert r['errors'] == []


def test_validate_context_defs_invalid_schema():
    r = validate_context_defs([{"context_type": "X", "schema": "bad"}])
    assert r['is_valid'] is False


def test_validate_context_defs_duplicate_type(context_defs):
    r = validate_context_defs(context_defs + context_defs)
    assert r['is_valid'] is False
    assert any("more than once" in e['message'] for e in r['errors'])


def test_validate_context_defs_non_object_schema():
    r = validate_context_defs([{"context_type": "X", "schema": {"type": "array"}}])
    assert r['is_valid'] is False
    assert any("object" in e['message'] for e in r['errors'])


def test_validate_context_defs_missing_type_in_schema():
    r = validate_context_defs([{"context_type": "X", "schema": {}}])
    assert r['is_valid'] is False


def test_validate_context_defs_empty():
    assert validate_context_defs([])['is_valid'] is True


def test_validate_identity_defs_valid(identity_defs):
    assert validate_identity_defs(identity_defs)['is_valid'] is True


def test_validate_identity_defs_invalid_schema():
    r = validate_identity_defs([{"identity_type": "X", "schema": 123}])
    assert r['is_valid'] is False


def test_validate_identity_defs_duplicate_type(identity_defs):
    r = validate_identity_defs(identity_defs + identity_defs)
    assert r['is_valid'] is False
    assert any("more than once" in e['message'] for e in r['errors'])


def test_validate_identity_defs_non_object_schema():
    r = validate_identity_defs([{"identity_type": "X", "schema": {"type": "string"}}])
    assert r['is_valid'] is False


def test_validate_identity_defs_empty():
    assert validate_identity_defs([])['is_valid'] is True


def test_validate_resource_defs_valid(resource_defs):
    assert validate_resource_defs(resource_defs)['is_valid'] is True


def test_validate_resource_defs_invalid_schema():
    r = validate_resource_defs([{"resource_type": "X", "actions": [], "schema": "bad"}])
    assert r['is_valid'] is False


def test_validate_resource_defs_duplicate_type(resource_defs):
    r = validate_resource_defs(resource_defs + resource_defs)
    assert r['is_valid'] is False
    assert any("more than once" in e['message'] for e in r['errors'])


def test_validate_resource_defs_non_object_schema():
    r = validate_resource_defs([{"resource_type": "X", "actions": [], "schema": {"type": "array"}}])
    assert r['is_valid'] is False


def test_validate_resource_defs_empty():
    assert validate_resource_defs([])['is_valid'] is True


def test_validate_grants_valid(allow_grant, deny_grant):
    assert validate_grants([allow_grant, deny_grant])['is_valid'] is True


def test_validate_grants_invalid():
    assert validate_grants([{"effect": "bad"}])['is_valid'] is False


def test_validate_grants_empty():
    assert validate_grants([])['is_valid'] is True


def test_validate_request_valid(admin_request, context_defs, identity_defs, resource_defs):
    assert validate_request(
        admin_request, context_defs, identity_defs, resource_defs
    )['is_valid'] is True


def test_validate_request_invalid_schema(context_defs, identity_defs, resource_defs):
    assert validate_request(
        {}, context_defs, identity_defs, resource_defs
    )['is_valid'] is False


def test_validate_request_unknown_identity_type(admin_request, context_defs, identity_defs, resource_defs):
    req = {**admin_request, "identities": {"Ghost": [{"id": "g1"}]}}
    r = validate_request(req, context_defs, identity_defs, resource_defs)
    assert r['is_valid'] is False
    assert any("Ghost" in e['message'] for e in r['errors'])


def test_validate_request_invalid_identity_instance(admin_request, context_defs, identity_defs, resource_defs):
    req = {**admin_request, "identities": {"User": [{"id": 123}]}}
    assert validate_request(
        req, context_defs, identity_defs, resource_defs
    )['is_valid'] is False


def test_validate_request_unknown_resource_type(admin_request, context_defs, identity_defs, resource_defs):
    req = {**admin_request, "resource_type": "Unknown"}
    r = validate_request(req, context_defs, identity_defs, resource_defs)
    assert r['is_valid'] is False
    assert any("Unknown" in e['message'] for e in r['errors'])


def test_validate_request_invalid_resource_instance(admin_request, context_defs, identity_defs, resource_defs):
    req = {**admin_request, "resource": {"id": 999}}
    assert validate_request(
        req, context_defs, identity_defs, resource_defs
    )['is_valid'] is False


def test_validate_request_invalid_action(admin_request, context_defs, identity_defs, resource_defs):
    req = {**admin_request, "action": "Widget:Delete"}
    r = validate_request(req, context_defs, identity_defs, resource_defs)
    assert r['is_valid'] is False
    assert any("Widget:Delete" in e['message'] for e in r['errors'])


def test_validate_request_unknown_context_type(admin_request, context_defs, identity_defs, resource_defs):
    req = {**admin_request, "context_type": "Unknown"}
    r = validate_request(req, context_defs, identity_defs, resource_defs)
    assert r['is_valid'] is False
    assert any("Unknown" in e['message'] for e in r['errors'])


def test_validate_request_invalid_context_instance(admin_request, context_defs, identity_defs, resource_defs):
    req = {**admin_request, "context": {"extra": "not_allowed"}}
    assert validate_request(
        req, context_defs, identity_defs, resource_defs
    )['is_valid'] is False


def test_validate_batch_request_valid(base_batch, context_defs, identity_defs, resource_defs):
    assert validate_batch_request(
        base_batch, context_defs, identity_defs, resource_defs
    )['is_valid'] is True


def test_validate_batch_request_invalid_schema(context_defs, identity_defs, resource_defs):
    assert validate_batch_request(
        {}, context_defs, identity_defs, resource_defs
    )['is_valid'] is False


def test_validate_batch_request_item_overrides_identities(base_batch, context_defs, identity_defs, resource_defs):
    batch = {**base_batch, "batch": [{"identities": {"User": [{"id": "u2", "role": "guest"}]}}]}
    assert validate_batch_request(
        batch, context_defs, identity_defs, resource_defs
    )['is_valid'] is True


def test_validate_batch_request_item_invalid_identity(base_batch, context_defs, identity_defs, resource_defs):
    batch = {**base_batch, "batch": [{"identities": {"Ghost": [{}]}}]}
    r = validate_batch_request(batch, context_defs, identity_defs, resource_defs)
    assert r['batch_errors'][0]['request'] != []


def test_validate_batch_request_item_overrides_resource(base_batch, context_defs, identity_defs, resource_defs):
    batch = {**base_batch, "batch": [{"resource": {"id": "w2"}}]}
    assert validate_batch_request(
        batch, context_defs, identity_defs, resource_defs
    )['is_valid'] is True


def test_validate_batch_request_item_overrides_resource_type(base_batch, context_defs, identity_defs, resource_defs):
    batch = {**base_batch, "batch": [{"resource_type": "Widget", "resource": {"id": "w2"}}]}
    assert validate_batch_request(
        batch, context_defs, identity_defs, resource_defs
    )['is_valid'] is True


def test_validate_batch_request_item_overrides_context(base_batch, context_defs, identity_defs, resource_defs):
    batch = {**base_batch, "batch": [{"context": {}, "context_type": "NULL"}]}
    assert validate_batch_request(
        batch, context_defs, identity_defs, resource_defs
    )['is_valid'] is True


def test_validate_batch_request_item_context_only(base_batch, context_defs, identity_defs, resource_defs):
    batch = {**base_batch, "batch": [{"context": {}}]}
    assert validate_batch_request(
        batch, context_defs, identity_defs, resource_defs
    )['is_valid'] is True


def test_validate_batch_request_top_level_invalid_identity(base_batch, context_defs, identity_defs, resource_defs):
    batch = {**base_batch, "identities": {"Ghost": [{}]}}
    assert validate_batch_request(
        batch, context_defs, identity_defs, resource_defs
    )['is_valid'] is False


def test_evaluate_one_action_not_in_grant(admin_request, allow_grant):
    grant = {**allow_grant, "actions": ["Widget:Write"]}
    r = evaluate_one(admin_request, grant, execute, False)
    assert r['is_applicable'] is False
    assert r['query_result'] is None


def test_evaluate_one_empty_actions_matches_any(admin_request, allow_grant):
    grant = {**allow_grant, "actions": [], "query": "`true`", "equality": True}
    assert evaluate_one(admin_request, grant, execute, False)['is_applicable'] is True


def test_evaluate_one_applicable(admin_request, allow_grant):
    assert evaluate_one(admin_request, allow_grant, execute, False)['is_applicable'] is True


def test_evaluate_one_wrong_equality(admin_request, allow_grant):
    grant = {**allow_grant, "equality": False}
    assert evaluate_one(admin_request, grant, execute, False)['is_applicable'] is False


def test_evaluate_one_query_failure_evaluate_no_error(admin_request, allow_grant):
    r = evaluate_one(admin_request, allow_grant, failing_execute, False)
    assert r['is_applicable'] is False
    assert r['has_failed'] is False
    assert "evaluation" not in r['errors']


def test_evaluate_one_query_failure_error_handler(admin_request, allow_grant):
    grant = {**allow_grant, "evaluation_handler": "error"}
    r = evaluate_one(admin_request, grant, failing_execute, False)
    assert r['has_failed'] is False
    assert r['errors']['evaluation'][0]['is_critical'] is False


def test_evaluate_one_query_failure_critical_handler(admin_request, allow_grant):
    grant = {**allow_grant, "evaluation_handler": "critical"}
    r = evaluate_one(admin_request, grant, failing_execute, False)
    assert r['has_failed'] is True
    assert r['errors']['evaluation'][0]['is_critical'] is True


def test_evaluate_one_only_crits_suppresses_error(admin_request, allow_grant):
    grant = {**allow_grant, "evaluation_handler": "error"}
    assert "evaluation" not in evaluate_one(
        admin_request,
        grant,
        failing_execute,
        True
    )['errors']


def test_evaluate_one_request_override_critical(admin_request, allow_grant):
    req = {**admin_request, "evaluation_handler": "critical"}
    grant = {**allow_grant, "evaluation_handler": "evaluate"}
    assert evaluate_one(
        req,
        grant,
        failing_execute,
        False
    )['has_failed'] is True


def test_evaluate_one_request_override_error(admin_request, allow_grant):
    req = {**admin_request, "evaluation_handler": "error"}
    grant = {**allow_grant, "evaluation_handler": "evaluate"}
    r = evaluate_one(
        req,
        grant,
        failing_execute,
        False
    )
    assert "evaluation" in r['errors']
    assert r['has_failed'] is False


def test_audit_applicable_grant(admin_request, allow_grant):
    r = audit(admin_request, [allow_grant], execute)
    assert r['has_failed'] is False
    assert r['results'][0]['is_applicable'] is True


def test_audit_no_applicable_grant(guest_request, allow_grant):
    assert audit(
        guest_request,
        [allow_grant],
        execute
    )['results'][0]['is_applicable'] is False


def test_audit_critical_error_stops_early(admin_request, allow_grant):
    grant = {**allow_grant, "evaluation_handler": "critical"}
    r = audit(
        admin_request,
        [grant, allow_grant],
        failing_execute
    )
    assert r['has_failed'] is True
    assert len(r['results']) == 1


def test_audit_empty_grants(admin_request):
    r = audit(
        admin_request,
        [],
        execute
    )
    assert r['results'] == []
    assert r['has_failed'] is False


def test_authorize_allow_grant(admin_request, allow_grant):
    r = authorize(
        admin_request,
        [allow_grant],
        execute
    )
    assert r['is_authorized'] is True
    assert r['grant'] == allow_grant


def test_authorize_deny_grant(banned_request, allow_grant, deny_grant):
    r = authorize(
        banned_request,
        [allow_grant, deny_grant],
        execute
    )
    assert r['is_authorized'] is False
    assert "deny" in r['message']


def test_authorize_no_applicable_grant(guest_request, allow_grant):
    r = authorize(
        guest_request,
        [allow_grant],
        execute
    )
    assert r['is_authorized'] is False
    assert r['grant'] is None
    assert "implicitly denied" in r['message']


def test_authorize_critical_error_in_deny(admin_request, deny_grant):
    grant = {**deny_grant, "evaluation_handler": "critical"}
    r = authorize(
        admin_request,
        [grant],
        failing_execute
    )
    assert r['is_authorized'] is False
    assert r['has_failed'] is True
    assert "critical error" in r['message']


def test_authorize_critical_error_in_allow(admin_request, allow_grant):
    grant = {**allow_grant, "evaluation_handler": "critical"}
    r = authorize(
        admin_request,
        [grant],
        failing_execute
    )
    assert r['is_authorized'] is False
    assert r['has_failed'] is True


def test_authorize_deny_checked_before_allow(admin_request, allow_grant, deny_grant):
    deny = {**deny_grant, "query": "request.identities.User[0].role == 'admin'"}
    r = authorize(
        admin_request,
        [allow_grant, deny],
        execute
    )
    assert r['is_authorized'] is False
    assert r['grant']['effect'] == "deny"


def test_batch_audit_basic(base_batch, allow_grant):
    r = batch_audit(
        base_batch,
        [allow_grant],
        execute
    )
    assert len(r['batch_results']) == 1
    assert r['batch_results'][0]['results'][0]['is_applicable'] is True


def test_batch_audit_item_overrides(base_batch, allow_grant):
    batch = {**base_batch, "batch": [{"identities": {"User": [{"id": "u2", "role": "guest"}]}}]}
    assert batch_audit(
        batch,
        [allow_grant],
        execute
    )['batch_results'][0]['results'][0]['is_applicable'] is False


def test_batch_audit_multiple_items(base_batch, allow_grant):
    batch = {**base_batch, "batch": [{}, {}]}
    assert len(batch_audit(
        batch,
        [allow_grant],
        execute
    )['batch_results']) == 2


def test_batch_authorize_basic(base_batch, allow_grant):
    r = batch_authorize(
        base_batch,
        [allow_grant],
        execute
    )
    assert r['results'][0]['is_authorized'] is True


def test_batch_authorize_item_overrides(base_batch, allow_grant):
    batch = {**base_batch, "batch": [{"identities": {"User": [{"id": "u2", "role": "guest"}]}}]}
    assert batch_authorize(
        batch,
        [allow_grant],
        execute
    )['results'][0]['is_authorized'] is False


def test_batch_authorize_multiple_items(base_batch, allow_grant):
    batch = {**base_batch, "batch": [{}, {}]}
    assert len(batch_authorize(
        batch,
        [allow_grant],
        execute
    )['results']) == 2


def test_audit_workflow_valid(context_defs, identity_defs, resource_defs, allow_grant, admin_request):
    assert "results" in audit_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        admin_request,
        execute
    )


def test_audit_workflow_invalid_context_defs(identity_defs, resource_defs, allow_grant, admin_request):
    bad_ctx = [{"context_type": "X", "schema": {"type": "array"}}]
    assert audit_workflow(
        bad_ctx,
        identity_defs,
        resource_defs,
        [allow_grant],
        admin_request,
        execute
    )['is_valid'] is False


def test_audit_workflow_invalid_identity_defs(context_defs, resource_defs, allow_grant, admin_request):
    bad_id = [{"identity_type": "X", "schema": {"type": "string"}}]
    assert audit_workflow(
        context_defs,
        bad_id,
        resource_defs,
        [allow_grant],
        admin_request,
        execute
    )['is_valid'] is False


def test_audit_workflow_invalid_resource_defs(context_defs, identity_defs, allow_grant, admin_request):
    bad_res = [{"resource_type": "X", "actions": [], "schema": {"type": "array"}}]
    assert audit_workflow(
        context_defs,
        identity_defs,
        bad_res,
        [allow_grant],
        admin_request,
        execute
    )['is_valid'] is False


def test_audit_workflow_invalid_grants(context_defs, identity_defs, resource_defs, admin_request):
    assert audit_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [{"effect": "bad"}],
        admin_request,
        execute
    )['is_valid'] is False


def test_audit_workflow_invalid_request(context_defs, identity_defs, resource_defs, allow_grant):
    assert audit_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        {},
        execute
    )['is_valid'] is False


def test_authorize_workflow_authorized(context_defs, identity_defs, resource_defs, allow_grant, admin_request):
    assert authorize_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        admin_request,
        execute
    )['is_authorized'] is True


def test_authorize_workflow_not_authorized(context_defs, identity_defs, resource_defs, allow_grant, guest_request):
    assert authorize_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        guest_request,
        execute
    )['is_authorized'] is False


def test_authorize_workflow_invalid_request(context_defs, identity_defs, resource_defs, allow_grant):
    assert authorize_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        {},
        execute
    )['is_valid'] is False


def test_batch_audit_workflow_valid(context_defs, identity_defs, resource_defs, allow_grant, base_batch):
    assert "batch_results" in batch_audit_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        base_batch,
        execute
    )


def test_batch_audit_workflow_invalid_batch(context_defs, identity_defs, resource_defs, allow_grant):
    assert batch_audit_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        {},
        execute
    )['is_valid'] is False


def test_batch_audit_workflow_invalid_context_defs(identity_defs, resource_defs, allow_grant, base_batch):
    bad_ctx = [{"context_type": "X", "schema": {"type": "array"}}]
    assert batch_audit_workflow(
        bad_ctx,
        identity_defs,
        resource_defs,
        [allow_grant],
        base_batch,
        execute
    )['is_valid'] is False


def test_batch_authorize_workflow_valid(context_defs, identity_defs, resource_defs, allow_grant, base_batch):
    assert "results" in batch_authorize_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        base_batch,
        execute
    )


def test_batch_authorize_workflow_invalid_batch(context_defs, identity_defs, resource_defs, allow_grant):
    assert batch_authorize_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        {},
        execute
    )['is_valid'] is False
