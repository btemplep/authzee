"""Tests for python reference"""

import jmespath
import jsonschema
import pytest
from src.reference import *


def execute(expression, data):
    result = {
        "result": None,
        "failure": None
    }
    try:
        result['result'] = jmespath.search(expression, data)
    except Exception as exc:
        result['failure'] = str(exc)

    return result


def failing_execute(expression, data):
    return {
        "result": None,
        "failure": "forced failure"
    }


@pytest.fixture
def context_defs():
    return [
        {
            "context_type": "NULL",
            "schema": {
                "type": "object",
                "additionalProperties": False
            }
        }
    ]


@pytest.fixture
def identity_defs():
    return [
        {
            "identity_type": "User",
            "schema": {
                "type": "object",
                "required": [
                    "id",
                    "role"
                ],
                "properties": {
                    "id": {
                        "type": "string"
                    },
                    "role": {
                        "type": "string"
                    }
                }
            }
        }
    ]


@pytest.fixture
def resource_defs():
    return [
        {
            "resource_type": "Widget",
            "actions": [
                "Widget:Read",
                "Widget:Write"
            ],
            "schema": {
                "type": "object",
                "required": [
                    "id"
                ],
                "properties": {
                    "id": {
                        "type": "string"
                    }
                }
            }
        }
    ]


@pytest.fixture
def allow_grant():
    return {
        "effect": "allow",
        "actions": [
            "Widget:Read"
        ],
        "query": "request.identities.User[0].role == 'admin'",
        "equality": True,
        "applicable_on_failure": False,
        "data": {}
    }


@pytest.fixture
def deny_grant():
    return {
        "effect": "deny",
        "actions": [
            "Widget:Read"
        ],
        "query": "request.identities.User[0].role == 'banned'",
        "equality": True,
        "applicable_on_failure": False,
        "data": {}
    }


@pytest.fixture
def admin_request():
    return {
        "identities": {
            "User": [
                {
                    "id": "u1",
                    "role": "admin"
                }
            ]
        },
        "action": "Widget:Read",
        "resource_type": "Widget",
        "resource": {
            "id": "w1"
        },
        "context_type": "NULL",
        "context": {}
    }


@pytest.fixture
def banned_request(admin_request):
    return {
        **admin_request,
        "identities": {
            "User": [
                {
                    "id": "u2",
                    "role": "banned"
                }
            ]
        }
    }


@pytest.fixture
def guest_request(admin_request):
    return {
        **admin_request,
        "identities": {
            "User": [
                {
                    "id": "u3",
                    "role": "guest"
                }
            ]
        }
    }


@pytest.fixture
def base_batch():
    return {
        "identities": {
            "User": [
                {
                    "id": "u1",
                    "role": "admin"
                }
            ]
        },
        "action": "Widget:Read",
        "resource_type": "Widget",
        "resource": {
            "id": "w1"
        },
        "context_type": "NULL",
        "context": {},
        "batch": [
            {}
        ]
    }


def test_validate_context_defs_valid(context_defs):
    r = validate_context_defs(context_defs)
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is None


def test_validate_context_defs_invalid_schema():
    r = validate_context_defs(
        [
            {
                "context_type": "X",
                "schema": "bad"
            }
        ]
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None


def test_validate_context_defs_duplicate_type(context_defs):
    r = validate_context_defs(context_defs + context_defs)
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None
    assert "more than once" in r['error']['message']


def test_validate_context_defs_non_object_schema():
    r = validate_context_defs(
        [
            {
                "context_type": "X",
                "schema": {
                    "type": "array"
                }
            }
        ]
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None
    assert "object" in r['error']['message']


def test_validate_context_defs_missing_type_in_schema():
    r = validate_context_defs(
        [
            {
                "context_type": "X",
                "schema": {}
            }
        ]
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None


def test_validate_context_defs_empty():
    r = validate_context_defs([])
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is None


def test_validate_identity_defs_valid(identity_defs):
    r = validate_identity_defs(identity_defs)
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is None


def test_validate_identity_defs_invalid_schema():
    r = validate_identity_defs(
        [
            {
                "identity_type": "X",
                "schema": 123
            }
        ]
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None


def test_validate_identity_defs_duplicate_type(identity_defs):
    r = validate_identity_defs(identity_defs + identity_defs)
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None
    assert "more than once" in r['error']['message']


def test_validate_identity_defs_non_object_schema():
    r = validate_identity_defs(
        [
            {
                "identity_type": "X",
                "schema": {
                    "type": "string"
                }
            }
        ]
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None


def test_validate_identity_defs_empty():
    r = validate_identity_defs([])
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is None


def test_validate_resource_defs_valid(resource_defs):
    r = validate_resource_defs(resource_defs)
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is None


def test_validate_resource_defs_invalid_schema():
    r = validate_resource_defs(
        [
            {
                "resource_type": "X",
                "actions": [],
                "schema": "bad"
            }
        ]
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None


def test_validate_resource_defs_duplicate_type(resource_defs):
    r = validate_resource_defs(resource_defs + resource_defs)
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None
    assert "more than once" in r['error']['message']


def test_validate_resource_defs_non_object_schema():
    r = validate_resource_defs(
        [
            {
                "resource_type": "X",
                "actions": [],
                "schema": {
                    "type": "array"
                }
            }
        ]
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None


def test_validate_resource_defs_empty():
    r = validate_resource_defs([])
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is None


def test_validate_grants_valid(allow_grant, deny_grant):
    r = validate_grants([allow_grant, deny_grant])
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is None


def test_validate_grants_invalid():
    r = validate_grants(
        [
            {
                "effect": "bad"
            }
        ]
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None


def test_validate_grants_empty():
    r = validate_grants([])
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is None


def test_validate_request_valid(
    admin_request,
    context_defs,
    identity_defs,
    resource_defs
):
    r = validate_request(
        admin_request,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is None


def test_validate_request_invalid_schema(
    context_defs,
    identity_defs,
    resource_defs
):
    r = validate_request(
        {},
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None


def test_validate_request_unknown_identity_type(
    admin_request,
    context_defs,
    identity_defs,
    resource_defs
):
    req = {
        **admin_request,
        "identities": {
            "Ghost": [
                {
                    "id": "g1"
                }
            ]
        }
    }
    r = validate_request(
        req,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None
    assert "Ghost" in r['error']['message']


def test_validate_request_invalid_identity_instance(
    admin_request,
    context_defs,
    identity_defs,
    resource_defs
):
    req = {
        **admin_request,
        "identities": {
            "User": [
                {
                    "id": 123
                }
            ]
        }
    }
    r = validate_request(
        req,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None


def test_validate_request_unknown_resource_type(
    admin_request,
    context_defs,
    identity_defs,
    resource_defs
):
    req = {
        **admin_request,
        "resource_type": "Unknown"
    }
    r = validate_request(
        req,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None
    assert "Unknown" in r['error']['message']


def test_validate_request_invalid_resource_instance(
    admin_request,
    context_defs,
    identity_defs,
    resource_defs
):
    req = {
        **admin_request,
        "resource": {
            "id": 999
        }
    }
    r = validate_request(
        req,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None


def test_validate_request_invalid_action(
    admin_request,
    context_defs,
    identity_defs,
    resource_defs
):
    req = {
        **admin_request,
        "action": "Widget:Delete"
    }
    r = validate_request(
        req,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None
    assert "Widget:Delete" in r['error']['message']


def test_validate_request_unknown_context_type(
    admin_request,
    context_defs,
    identity_defs,
    resource_defs
):
    req = {
        **admin_request,
        "context_type": "Unknown"
    }
    r = validate_request(
        req,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None
    assert "Unknown" in r['error']['message']


def test_validate_request_invalid_context_instance(
    admin_request,
    context_defs,
    identity_defs,
    resource_defs
):
    req = {
        **admin_request,
        "context": {
            "extra": "not_allowed"
        }
    }
    r = validate_request(
        req,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, general_result_schema)
    assert r['error'] is not None


def test_validate_batch_request_valid(
    base_batch,
    context_defs,
    identity_defs,
    resource_defs
):
    r = validate_batch_request(
        base_batch,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, validate_batch_request_result_schema)
    assert r['error'] is None


def test_validate_batch_request_invalid_schema(
    context_defs,
    identity_defs,
    resource_defs
):
    r = validate_batch_request(
        {},
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, validate_batch_request_result_schema)
    assert r['error'] is not None


def test_validate_batch_request_item_overrides_identities(
    base_batch,
    context_defs,
    identity_defs,
    resource_defs
):
    batch = {
        **base_batch,
        "batch": [
            {
                "identities": {
                    "User": [
                        {
                            "id": "u2",
                            "role": "guest"
                        }
                    ]
                }
            }
        ]
    }
    r = validate_batch_request(
        batch,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, validate_batch_request_result_schema)
    assert r['error'] is None


def test_validate_batch_request_item_invalid_identity(
    base_batch,
    context_defs,
    identity_defs,
    resource_defs
):
    batch = {
        **base_batch,
        "batch": [
            {
                "identities": {
                    "Ghost": [
                        {}
                    ]
                }
            }
        ]
    }
    r = validate_batch_request(
        batch,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, validate_batch_request_result_schema)
    assert r['batch_errors'][0] is not None


def test_validate_batch_request_item_overrides_resource(
    base_batch,
    context_defs,
    identity_defs,
    resource_defs
):
    batch = {
        **base_batch,
        "batch": [
            {
                "resource": {
                    "id": "w2"
                }
            }
        ]
    }
    r = validate_batch_request(
        batch,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, validate_batch_request_result_schema)
    assert r['error'] is None


def test_validate_batch_request_item_overrides_resource_type(
    base_batch,
    context_defs,
    identity_defs,
    resource_defs
):
    batch = {
        **base_batch,
        "batch": [
            {
                "resource_type": "Widget",
                "resource": {
                    "id": "w2"
                }
            }
        ]
    }
    r = validate_batch_request(
        batch,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, validate_batch_request_result_schema)
    assert r['error'] is None


def test_validate_batch_request_item_overrides_context(
    base_batch,
    context_defs,
    identity_defs,
    resource_defs
):
    batch = {
        **base_batch,
        "batch": [
            {
                "context": {},
                "context_type": "NULL"
            }
        ]
    }
    r = validate_batch_request(
        batch,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, validate_batch_request_result_schema)
    assert r['error'] is None


def test_validate_batch_request_item_context_only(
    base_batch,
    context_defs,
    identity_defs,
    resource_defs
):
    batch = {
        **base_batch,
        "batch": [
            {
                "context": {}
            }
        ]
    }
    r = validate_batch_request(
        batch,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, validate_batch_request_result_schema)
    assert r['error'] is None


def test_validate_batch_request_top_level_invalid_identity(
    base_batch,
    context_defs,
    identity_defs,
    resource_defs
):
    batch = {
        **base_batch,
        "identities": {
            "Ghost": [
                {}
            ]
        }
    }
    r = validate_batch_request(
        batch,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, validate_batch_request_result_schema)
    assert r['error'] is not None


def test_validate_batch_request_top_level_invalid_resource(
    base_batch,
    context_defs,
    identity_defs,
    resource_defs
):
    batch = {
        **base_batch,
        "resource": {
            "id": 999
        }
    }
    r = validate_batch_request(
        batch,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, validate_batch_request_result_schema)
    assert r['error'] is not None


def test_validate_batch_request_top_level_invalid_context(
    base_batch,
    context_defs,
    identity_defs,
    resource_defs
):
    batch = {
        **base_batch,
        "context": {
            "not_allowed": True
        }
    }
    r = validate_batch_request(
        batch,
        context_defs,
        identity_defs,
        resource_defs
    )
    jsonschema.validate(r, validate_batch_request_result_schema)
    assert r['error'] is not None


def test_evaluate_one_action_not_in_grant(admin_request, allow_grant):
    grant = {
        **allow_grant,
        "actions": [
            "Widget:Write"
        ]
    }
    r = evaluate_one(admin_request, grant, execute)
    jsonschema.validate(r, evaluate_one_result_schema)
    assert r['is_applicable'] is False
    assert r['query_result'] is None


def test_evaluate_one_empty_actions_matches_any(admin_request, allow_grant):
    grant = {
        **allow_grant,
        "actions": [],
        "query": "`true`",
        "equality": True
    }
    r = evaluate_one(admin_request, grant, execute)
    jsonschema.validate(r, evaluate_one_result_schema)
    assert r['is_applicable'] is True


def test_evaluate_one_applicable(admin_request, allow_grant):
    r = evaluate_one(admin_request, allow_grant, execute)
    jsonschema.validate(r, evaluate_one_result_schema)
    assert r['is_applicable'] is True


def test_evaluate_one_wrong_equality(admin_request, allow_grant):
    grant = {
        **allow_grant,
        "equality": False
    }
    r = evaluate_one(admin_request, grant, execute)
    jsonschema.validate(r, evaluate_one_result_schema)
    assert r['is_applicable'] is False


def test_evaluate_one_query_failure(admin_request, allow_grant):
    r = evaluate_one(
        admin_request,
        allow_grant,
        failing_execute
    )
    jsonschema.validate(r, evaluate_one_result_schema)
    assert r['is_applicable'] is False
    assert r['failure'] is not None


def test_evaluate_one_applicable_on_failure_true(admin_request, allow_grant):
    grant = {
        **allow_grant,
        "applicable_on_failure": True
    }
    r = evaluate_one(
        admin_request,
        grant,
        failing_execute
    )
    jsonschema.validate(r, evaluate_one_result_schema)
    assert r['is_applicable'] is True
    assert r['failure'] is not None


def test_evaluate_one_applicable_on_failure_false(admin_request, allow_grant):
    grant = {
        **allow_grant,
        "applicable_on_failure": False
    }
    r = evaluate_one(
        admin_request,
        grant,
        failing_execute
    )
    jsonschema.validate(r, evaluate_one_result_schema)
    assert r['is_applicable'] is False
    assert r['failure'] is not None


def test_audit_applicable_grant(admin_request, allow_grant):
    r = audit(
        admin_request,
        [allow_grant],
        execute
    )
    jsonschema.validate(r, audit_result_schema)
    assert r['error'] is None
    assert r['results'][0]['is_applicable'] is True
    assert r['results'][0]['grant'] == allow_grant


def test_audit_no_applicable_grant(guest_request, allow_grant):
    r = audit(
        guest_request,
        [allow_grant],
        execute
    )
    jsonschema.validate(r, audit_result_schema)
    assert r['results'][0]['is_applicable'] is False
    assert r['results'][0]['grant'] == allow_grant


def test_audit_evaluation_error(admin_request, allow_grant):
    r = audit(
        admin_request,
        [allow_grant],
        failing_execute
    )
    jsonschema.validate(r, audit_result_schema)
    assert r['error'] is None
    assert len(r['results']) == 1
    assert r['results'][0]['failure'] is not None


def test_audit_empty_grants(admin_request):
    r = audit(admin_request, [], execute)
    jsonschema.validate(r, audit_result_schema)
    assert r['results'] == []
    assert r['error'] is None


def test_authorize_allow_grant(admin_request, allow_grant):
    r = authorize(
        admin_request,
        [allow_grant],
        execute
    )
    jsonschema.validate(r, authorize_result_schema)
    assert r['is_authorized'] is True
    assert r['grant'] == allow_grant


def test_authorize_deny_grant(banned_request, allow_grant, deny_grant):
    r = authorize(
        banned_request,
        [allow_grant, deny_grant],
        execute
    )
    jsonschema.validate(r, authorize_result_schema)
    assert r['is_authorized'] is False
    assert "deny" in r['message']


def test_authorize_no_applicable_grant(guest_request, allow_grant):
    r = authorize(
        guest_request,
        [allow_grant],
        execute
    )
    jsonschema.validate(r, authorize_result_schema)
    assert r['is_authorized'] is False
    assert r['grant'] is None
    assert "implicitly denied" in r['message']


def test_authorize_query_failure_in_deny(admin_request, deny_grant):
    r = authorize(
        admin_request,
        [deny_grant],
        failing_execute
    )
    jsonschema.validate(r, authorize_result_schema)
    assert r['is_authorized'] is False
    assert r['error'] is None
    assert "implicitly denied" in r['message']


def test_authorize_query_failure_in_allow(admin_request, allow_grant):
    r = authorize(
        admin_request,
        [allow_grant],
        failing_execute
    )
    jsonschema.validate(r, authorize_result_schema)
    assert r['is_authorized'] is False
    assert r['error'] is None
    assert "implicitly denied" in r['message']


def test_authorize_deny_checked_before_allow(
    admin_request,
    allow_grant,
    deny_grant
):
    deny = {
        **deny_grant,
        "query": "request.identities.User[0].role == 'admin'"
    }
    r = authorize(
        admin_request,
        [allow_grant, deny],
        execute
    )
    jsonschema.validate(r, authorize_result_schema)
    assert r['is_authorized'] is False
    assert r['grant']['effect'] == "deny"


def test_batch_audit_basic(base_batch, allow_grant):
    r = batch_audit(
        base_batch,
        [allow_grant],
        execute
    )
    jsonschema.validate(r, batch_audit_result_schema)
    assert len(r['batch']) == 1
    assert r['batch'][0]['results'][0]['is_applicable'] is True


def test_batch_audit_item_overrides(base_batch, allow_grant):
    batch = {
        **base_batch,
        "batch": [
            {
                "identities": {
                    "User": [
                        {
                            "id": "u2",
                            "role": "guest"
                        }
                    ]
                }
            }
        ]
    }
    r = batch_audit(
        batch,
        [allow_grant],
        execute
    )
    jsonschema.validate(r, batch_audit_result_schema)
    assert r['batch'][0]['results'][0]['is_applicable'] is False


def test_batch_audit_multiple_items(base_batch, allow_grant):
    batch = {
        **base_batch,
        "batch": [
            {},
            {}
        ]
    }
    r = batch_audit(
        batch,
        [allow_grant],
        execute
    )
    jsonschema.validate(r, batch_audit_result_schema)
    assert len(r['batch']) == 2


def test_batch_authorize_basic(base_batch, allow_grant):
    r = batch_authorize(
        base_batch,
        [allow_grant],
        execute
    )
    jsonschema.validate(r, batch_authorize_result_schema)
    assert r['batch'][0]['is_authorized'] is True


def test_batch_authorize_item_overrides(base_batch, allow_grant):
    batch = {
        **base_batch,
        "batch": [
            {
                "identities": {
                    "User": [
                        {
                            "id": "u2",
                            "role": "guest"
                        }
                    ]
                }
            }
        ]
    }
    r = batch_authorize(
        batch,
        [allow_grant],
        execute
    )
    jsonschema.validate(r, batch_authorize_result_schema)
    assert r['batch'][0]['is_authorized'] is False


def test_batch_authorize_multiple_items(base_batch, allow_grant):
    batch = {
        **base_batch,
        "batch": [
            {},
            {}
        ]
    }
    r = batch_authorize(
        batch,
        [allow_grant],
        execute
    )
    jsonschema.validate(r, batch_authorize_result_schema)
    assert len(r['batch']) == 2


def test_audit_workflow_valid(
    context_defs,
    identity_defs,
    resource_defs,
    allow_grant,
    admin_request
):
    r = audit_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        admin_request,
        execute
    )
    jsonschema.validate(r, audit_result_schema)
    assert "results" in r


def test_audit_workflow_invalid_context_defs(
    identity_defs,
    resource_defs,
    allow_grant,
    admin_request
):
    bad_ctx = [
        {
            "context_type": "X",
            "schema": {
                "type": "array"
            }
        }
    ]
    r = audit_workflow(
        bad_ctx,
        identity_defs,
        resource_defs,
        [allow_grant],
        admin_request,
        execute
    )
    jsonschema.validate(r, audit_result_schema)
    assert r['error'] is not None


def test_audit_workflow_invalid_identity_defs(
    context_defs,
    resource_defs,
    allow_grant,
    admin_request
):
    bad_id = [
        {
            "identity_type": "X",
            "schema": {
                "type": "string"
            }
        }
    ]
    r = audit_workflow(
        context_defs,
        bad_id,
        resource_defs,
        [allow_grant],
        admin_request,
        execute
    )
    jsonschema.validate(r, audit_result_schema)
    assert r['error'] is not None


def test_audit_workflow_invalid_resource_defs(
    context_defs,
    identity_defs,
    allow_grant,
    admin_request
):
    bad_res = [
        {
            "resource_type": "X",
            "actions": [],
            "schema": {
                "type": "array"
            }
        }
    ]
    r = audit_workflow(
        context_defs,
        identity_defs,
        bad_res,
        [allow_grant],
        admin_request,
        execute
    )
    jsonschema.validate(r, audit_result_schema)
    assert r['error'] is not None


def test_audit_workflow_invalid_grants(
    context_defs,
    identity_defs,
    resource_defs,
    admin_request
):
    r = audit_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [
            {
                "effect": "bad"
            }
        ],
        admin_request,
        execute
    )
    jsonschema.validate(r, audit_result_schema)
    assert r['error'] is not None


def test_audit_workflow_invalid_request(
    context_defs,
    identity_defs,
    resource_defs,
    allow_grant
):
    r = audit_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        {},
        execute
    )
    jsonschema.validate(r, audit_result_schema)
    assert r['error'] is not None
    assert r['results'] == []


def test_authorize_workflow_authorized(
    context_defs,
    identity_defs,
    resource_defs,
    allow_grant,
    admin_request
):
    r = authorize_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        admin_request,
        execute
    )
    jsonschema.validate(r, authorize_result_schema)
    assert r['is_authorized'] is True


def test_authorize_workflow_not_authorized(
    context_defs,
    identity_defs,
    resource_defs,
    allow_grant,
    guest_request
):
    r = authorize_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        guest_request,
        execute
    )
    jsonschema.validate(r, authorize_result_schema)
    assert r['is_authorized'] is False


def test_authorize_workflow_invalid_request(
    context_defs,
    identity_defs,
    resource_defs,
    allow_grant
):
    r = authorize_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        {},
        execute
    )
    jsonschema.validate(r, authorize_result_schema)
    assert r['is_authorized'] is False
    assert r['error'] is not None


def test_batch_audit_workflow_valid(
    context_defs,
    identity_defs,
    resource_defs,
    allow_grant,
    base_batch
):
    r = batch_audit_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        base_batch,
        execute
    )
    jsonschema.validate(r, batch_audit_result_schema)
    assert "batch" in r


def test_batch_audit_workflow_invalid_batch(
    context_defs,
    identity_defs,
    resource_defs,
    allow_grant
):
    r = batch_audit_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        {},
        execute
    )
    jsonschema.validate(r, batch_audit_result_schema)
    assert r['error'] is not None
    assert r['grants'] == []
    assert r['batch'] == []


def test_batch_audit_workflow_invalid_context_defs(
    identity_defs,
    resource_defs,
    allow_grant,
    base_batch
):
    bad_ctx = [
        {
            "context_type": "X",
            "schema": {
                "type": "array"
            }
        }
    ]
    r = batch_audit_workflow(
        bad_ctx,
        identity_defs,
        resource_defs,
        [allow_grant],
        base_batch,
        execute
    )
    jsonschema.validate(r, batch_audit_result_schema)
    assert r['error'] is not None


def test_batch_authorize_workflow_valid(
    context_defs,
    identity_defs,
    resource_defs,
    allow_grant,
    base_batch
):
    r = batch_authorize_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        base_batch,
        execute
    )
    jsonschema.validate(r, batch_authorize_result_schema)
    assert "batch" in r


def test_batch_authorize_workflow_invalid_batch(
    context_defs,
    identity_defs,
    resource_defs,
    allow_grant
):
    r = batch_authorize_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        {},
        execute
    )
    jsonschema.validate(r, batch_authorize_result_schema)
    assert r['error'] is not None
    assert r['batch'] == []


def test_batch_audit_workflow_item_with_error(
    context_defs,
    identity_defs,
    resource_defs,
    allow_grant,
    base_batch
):
    batch = {
        **base_batch,
        "batch": [
            {},
            {
                "identities": {
                    "Ghost": [
                        {}
                    ]
                }
            }
        ]
    }
    r = batch_audit_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        batch,
        execute
    )
    jsonschema.validate(r, batch_audit_result_schema)
    assert r['error'] is None
    assert len(r['batch']) == 2
    assert r['batch'][0]['error'] is None
    assert r['batch'][1]['error'] is not None
    assert r['batch'][1]['results'] == []


def test_batch_authorize_workflow_item_with_error(
    context_defs,
    identity_defs,
    resource_defs,
    allow_grant,
    base_batch
):
    batch = {
        **base_batch,
        "batch": [
            {},
            {
                "identities": {
                    "Ghost": [
                        {}
                    ]
                }
            }
        ]
    }
    r = batch_authorize_workflow(
        context_defs,
        identity_defs,
        resource_defs,
        [allow_grant],
        batch,
        execute
    )
    jsonschema.validate(r, batch_authorize_result_schema)
    assert r['error'] is None
    assert len(r['batch']) == 2
    assert r['batch'][0]['is_authorized'] is True
    assert r['batch'][1]['is_authorized'] is False
    assert r['batch'][1]['error'] is not None
