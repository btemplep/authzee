/**
 * A reference implementation for the Authzee specification, in JavaScript.
 *
 * This is a faithful port of the Python reference (`reference.py`). It is an ESM
 * module. JSON Schema validation (Draft 2020-12) is performed with Ajv. The
 * JSON query language is supplied by the caller through an `execute` function
 * (JMESPath is the reference query language, but it is not bundled here).
 *
 * Core workflow:
 *
 * 1. Context, identity, and resource definitions are created to limit inputs.
 * 2. Definitions are validated with `validateContextDefs`, `validateIdentityDefs`,
 *    and `validateResourceDefs`.
 * 3. Grants are created to allow or deny actions on resources.
 * 4. Grants are validated with `validateGrants`.
 * 5. Requests or batch requests are created to perform Authzee operations.
 * 6. Requests are validated with `validateRequest`, batch requests with
 *    `validateBatchRequest`.
 * 7. An operation is run on the request or batch request:
 *    - audit - List grants that evaluate to a match for the request.
 *    - authorize - Evaluate grants to determine if a request is authorized.
 *    - batchAudit / batchAuthorize - The batch equivalents.
 *
 * The public function names use camelCase (JS convention); the underlying
 * behavior, data shapes, and schema constants match the Python reference.
 */

import Ajv2020 from "ajv/dist/2020.js";

const DRAFT_2020_12_META_URI = "https://json-schema.org/draft/2020-12/schema";

const _type_regex = "^[A-Za-z0-9_]*$";
const _type_schema = {
  title: "Authzee Type",
  description: "A unique name to identity this type.",
  type: "string",
  pattern: _type_regex,
  minLength: 1,
  maxLength: 256
};
const _action_schema = {
  title: "Resource Action",
  description:
    "Unique name for a resource action. The 'ResourceType:ResourceAction' pattern is common, or more general 'Namespace:Action' pattern.",
  type: "string",
  pattern: "^[A-Za-z0-9_.:-]*$",
  minLength: 1,
  maxLength: 512
};

/**
 * In the Python reference `_schema_schema` is the Draft 2020-12 meta-schema, used
 * to validate that a definition's `schema` field is itself a valid JSON Schema.
 * With Ajv the meta-schema is built in and addressable by its canonical URI, so
 * definition schemas reference it with `$ref`.
 */
const _schema_schema = { $ref: DRAFT_2020_12_META_URI };

const _context_type_schema = {
  ..._type_schema,
  title: "Authzee Context Type",
  description: "A unique name to identity this context type."
};
const _identity_type_schema = {
  ..._type_schema,
  title: "Authzee Identity Type",
  description: "A unique name to identity this identity type."
};
const _resource_type_schema = {
  ..._type_schema,
  title: "Authzee Resource Type",
  description: "A unique name to identity this resource type."
};

export const context_definition_schema = {
  $schema: DRAFT_2020_12_META_URI,
  title: "Context Definition",
  description:
    "A request context definition.  Defines a type of context that can be passed with Authzee requests.",
  type: "object",
  additionalProperties: true,
  required: [
    "context_type",
    "schema"
  ],
  properties: {
    context_type: _context_type_schema,
    schema: _schema_schema
  }
};

export const identity_definition_schema = {
  $schema: DRAFT_2020_12_META_URI,
  title: "Identity Definition",
  description:
    "An identity definition.  Defines a type of identity to use with Authzee.",
  type: "object",
  additionalProperties: true,
  required: [
    "identity_type",
    "schema"
  ],
  properties: {
    identity_type: _identity_type_schema,
    schema: _schema_schema
  }
};

export const resource_definition_schema = {
  $schema: DRAFT_2020_12_META_URI,
  title: "Resource Definition",
  description:
    "A resource definition.  Defines a type of resource to use with Authzee.",
  type: "object",
  additionalProperties: true,
  required: [
    "resource_type",
    "actions",
    "schema"
  ],
  properties: {
    resource_type: _resource_type_schema,
    actions: {
      type: "array",
      uniqueItems: true,
      items: _action_schema
    },
    schema: _schema_schema
  }
};

export const grant_schema = {
  $schema: DRAFT_2020_12_META_URI,
  title: "Grant",
  description:
    "A grant is an object representing enacted authorization rules.",
  type: "object",
  additionalProperties: true,
  required: [
    "effect",
    "actions",
    "data",
    "query",
    "equality",
    "applicable_on_failure"
  ],
  properties: {
    effect: {
      type: "string",
      enum: [
        "allow",
        "deny"
      ],
      description:
        "Any applicable deny grant will always cause the request to be unauthorized. If there are no applicable deny grants, and there is an applicable allow grant, the request is authorized. If there no applicable allow or deny grants, requests are implicitly denied and is not authorized."
    },
    actions: {
      type: "array",
      uniqueItems: true,
      items: _action_schema,
      description:
        "List of actions this grant applies to or null to match any resource action."
    },
    data: {
      type: "object",
      description:
        "Data that is made available at query time for the grant evaluation. Easy place to store data so it doesn't have to be embedded in the query."
    },
    query: {
      type: "string",
      description:
        'JSON query to run on the authorization data. {"grant": <grant>, "request": <request>}'
    },
    equality: {
      description:
        "Expected value for the query to return.  If the query result matches this value the grant is a considered applicable to the request."
    },
    applicable_on_failure: {
      type: "boolean",
      description:
        "If true, the grant is considered applicable when the query evaluation fails. Useful as a fail-safe for deny grants."
    }
  }
};

export const generic_error_schema = {
  title: "Operation Error",
  description: "Error from an Authzee operation, or null if no error.",
  type: [
    "object",
    "null"
  ],
  required: [
    "error_type",
    "message"
  ],
  properties: {
    error_type: {
      type: "string",
      description: "The type of error."
    },
    message: {
      type: "string",
      description: "Message describing the error."
    }
  }
};

export const general_result_schema = {
  $schema: DRAFT_2020_12_META_URI,
  title: "General Result",
  description:
    "General result, where no distinct return value is needed.  Only passes on if there was an error or not. ",
  type: "object",
  additionalProperties: false,
  required: [
    "error"
  ],
  properties: {
    error: generic_error_schema
  }
};

const _request_identities_schema = {
  description:
    "Object whose keys are the identity types, and values are an array of instances of that identity type.",
  type: "object",
  additionalProperties: false,
  required: [],
  patternProperties: {
    [_type_regex]: {
      type: "array",
      items: {
        type: "object"
      }
    }
  }
};
const _request_resource_schema = {
  type: "object",
  description:
    "Resource for the request that is an instance of the given resource_type."
};
const _request_context_schema = {
  type: "object",
  description:
    "Context for the request that is an instance of the given context_type."
};

export const request_schema = {
  $schema: DRAFT_2020_12_META_URI,
  title: "Authzee Operation Request",
  description: "Request for an Authzee Operation.",
  additionalProperties: false,
  required: [
    "identities",
    "action",
    "resource_type",
    "resource",
    "context_type",
    "context"
  ],
  properties: {
    identities: _request_identities_schema,
    action: _action_schema,
    resource_type: _resource_type_schema,
    resource: _request_resource_schema,
    context_type: _context_type_schema,
    context: _request_context_schema
  }
};

const _query_result_schema = {
  description: "Result from running the JSON query in the grant."
};

export const query_execute_result_schema = {
  $schema: DRAFT_2020_12_META_URI,
  title: "Result for a JSON query execute function",
  description:
    "Result from evaluating a JSON query against the given input data.",
  type: "object",
  additionalProperties: false,
  required: [
    "result",
    "failure"
  ],
  properties: {
    result: _query_result_schema,
    failure: {
      type: [
        "string",
        "null"
      ],
      description:
        "A message describing why the query execution failed, or null if no failure occurred."
    }
  }
};

const _is_applicable_schema = {
  type: "boolean",
  description: "If the grant is applicable to the request or not."
};

export const evaluate_one_result_schema = {
  $schema: DRAFT_2020_12_META_URI,
  title: "Evaluate One Result",
  description: "Result from evaluating one grant against a request.",
  type: "object",
  additionalProperties: false,
  required: [
    "is_applicable",
    "query_result",
    "failure"
  ],
  properties: {
    is_applicable: _is_applicable_schema,
    query_result: _query_result_schema,
    failure: {
      type: [
        "string",
        "null"
      ],
      description:
        "A message describing why the evaluation failed, or null if no failure occurred. Evaluation failures do not cause the operation to fail."
    }
  }
};

export const audit_result_schema = {
  $schema: DRAFT_2020_12_META_URI,
  title: "Audit Result",
  description: "Result for the audit operation.",
  type: "object",
  additionalProperties: true,
  required: [
    "results",
    "error"
  ],
  properties: {
    results: {
      type: "array",
      description: "List of grant evaluation results.",
      items: {
        type: "object",
        additionalProperties: true,
        required: [
          "grant",
          "is_applicable",
          "query_result",
          "failure"
        ],
        properties: {
          grant: grant_schema,
          is_applicable: _is_applicable_schema,
          query_result: _query_result_schema,
          failure: {
            type: [
              "string",
              "null"
            ],
            description:
              "A message describing why the evaluation failed, or null if no failure occurred."
          }
        }
      }
    },
    error: generic_error_schema
  }
};

export const authorize_result_schema = {
  $schema: DRAFT_2020_12_META_URI,
  title: "Authorize Result",
  description: "Result for the authorize operation.",
  type: "object",
  additionalProperties: true,
  required: [
    "is_authorized",
    "grant",
    "message",
    "error"
  ],
  properties: {
    is_authorized: {
      type: "boolean",
      description:
        "true if the request is authorized.  false if it is not authorized."
    },
    grant: {
      description:
        "Grant that was responsible for the authorization decision, if applicable.",
      anyOf: [
        {
          type: "null",
          description: "No grant was involved in the authorization decision."
        },
        grant_schema
      ]
    },
    message: {
      type: "string",
      description: "Details about why the request was authorized or not.",
      enum: [
        "An error has occurred. Therefore, the request is not authorized.",
        "A deny grant is applicable to the request. Therefore, the request is not authorized.",
        "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
        "No grants are applicable to the request. Therefore, the request is implicitly denied and is not authorized."
      ]
    },
    error: generic_error_schema
  }
};

const _request_level_description =
  " Applies to all items in the batch unless the batch item overwrites it by specifying a different, non-null value.";
const _batch_item_level_description =
  " Overrides the batch request level if the field exists and is not null.";

export const batch_request_schema = {
  $schema: DRAFT_2020_12_META_URI,
  title: "Batch Operation Request",
  description: "Request for an Authzee Batch Operation.",
  additionalProperties: true,
  required: [
    "identities",
    "action",
    "resource_type",
    "resource",
    "context_type",
    "context",
    "batch"
  ],
  properties: {
    identities: {
      ..._request_identities_schema,
      description: _request_identities_schema.description + _request_level_description
    },
    action: _action_schema,
    resource_type: {
      ..._resource_type_schema,
      description: _resource_type_schema.description + _request_level_description
    },
    resource: {
      ..._request_resource_schema,
      description: _request_resource_schema.description + _request_level_description
    },
    context_type: _context_type_schema,
    context: {
      ..._request_context_schema,
      description: _request_context_schema.description + _request_level_description
    },
    batch: {
      type: "array",
      description:
        "Batch of items to process with shared resource types. When evaluated, each item is merged with the root request, where the batch item fields take precedence.",
      minItems: 1,
      items: {
        type: "object",
        additionalProperties: false,
        required: [],
        properties: {
          identities: {
            ..._request_identities_schema,
            type: [
              "object",
              "null"
            ],
            description:
              _request_identities_schema.description + _batch_item_level_description
          },
          resource_type: {
            ..._resource_type_schema,
            type: [
              "string",
              "null"
            ],
            description: _resource_type_schema.description + _batch_item_level_description
          },
          resource: {
            ..._request_resource_schema,
            description:
              "Resource for this batch item, that is an instance of the given resource_type. Overrides the batch request level if the field exists and is not null."
          },
          context_type: {
            ..._context_type_schema,
            type: [
              "string",
              "null"
            ],
            description: _context_type_schema.description + _batch_item_level_description
          },
          context: {
            type: [
              "object",
              "null"
            ],
            description:
              "Context for the request that is an instance of context_type." +
              _batch_item_level_description
          }
        }
      }
    }
  }
};

export const validate_request_result_schema = {
  $schema: DRAFT_2020_12_META_URI,
  title: "Request Validation Result",
  description: "Request Validation Result schema.",
  type: "object",
  additionalProperties: false,
  required: [
    "error"
  ],
  properties: {
    error: generic_error_schema
  }
};

export const validate_batch_request_result_schema = {
  $schema: DRAFT_2020_12_META_URI,
  title: "Batch request Validation Result",
  description: "Batch request Validation Result schema.",
  type: "object",
  additionalProperties: false,
  required: [
    "error",
    "batch"
  ],
  properties: {
    error: generic_error_schema,
    batch: {
      type: "array",
      description: "Each result corresponds to the batch request item of the same index.",
      items: generic_error_schema
    }
  }
};

export const batch_audit_result_schema = {
  $schema: DRAFT_2020_12_META_URI,
  title: "Batch Audit Result",
  description: "Result for the Batch Audit Operation.",
  type: "object",
  additionalProperties: true,
  required: [
    "grants",
    "batch",
    "error"
  ],
  properties: {
    grants: {
      type: "array",
      description: "List of grants that have been processed for the request.",
      items: grant_schema
    },
    batch: {
      type: "array",
      description:
        "Array of results from a batch request. Each result corresponds to the batch request item of the same index.",
      items: {
        type: "object",
        description: "Audit batch item result.",
        additionalProperties: true,
        required: [
          "results",
          "error"
        ],
        properties: {
          results: {
            type: "array",
            description:
              "List of grant evaluation results for each respective grant index.",
            items: {
              type: "object",
              additionalProperties: true,
              required: [
                "is_applicable",
                "query_result",
                "failure"
              ],
              properties: {
                is_applicable: _is_applicable_schema,
                query_result: _query_result_schema,
                failure: {
                  type: [
                    "string",
                    "null"
                  ],
                  description:
                    "A message describing why the evaluation failed, or null if no failure occurred."
                }
              }
            }
          },
          error: generic_error_schema
        }
      }
    },
    error: generic_error_schema
  }
};

export const batch_authorize_result_schema = {
  $schema: DRAFT_2020_12_META_URI,
  title: "Batch Authorize Result",
  description: "Result for the Batch Authorize Operation.",
  type: "object",
  additionalProperties: true,
  required: [
    "batch",
    "error"
  ],
  properties: {
    batch: {
      type: "array",
      description:
        "Array of results from a batch request. Each result corresponds to the batch request item of the same index.",
      items: authorize_result_schema
    },
    error: generic_error_schema
  }
};

/**
 * Shared Ajv instance. `strict` is disabled so the spec schemas (which include
 * things like sibling `type` + `$ref`, unknown keywords in descriptions, etc.)
 * compile without strict-mode errors, matching the permissive behavior of the
 * Python `jsonschema` library.
 */
const _ajv = new Ajv2020({
  strict: false,
  allErrors: false,
  validateSchema: false,
  logger: false
});

const _validatorCache = new WeakMap();

/**
 * Validate `instance` against `schema`. Returns `null` when valid, or a message
 * string describing the first error when invalid. Mirrors the Python reference's
 * use of `jsonschema.validate` (which raises a `ValidationError` whose string
 * form is embedded in the returned error messages).
 */
function _schemaError(instance, schema) {
  let validate = _validatorCache.get(schema);
  if (validate === undefined) {
    validate = _ajv.compile(schema);
    _validatorCache.set(schema, validate);
  }

  const valid = validate(instance);
  if (valid) {
    return null;
  }

  return _ajv.errorsText(validate.errors);
}

export function validateContextDefs(context_defs) {
  const context_types = new Set();
  for (const c_def of context_defs) {
    const err = _schemaError(c_def, context_definition_schema);
    if (err !== null) {
      return {
        error: {
          error_type: "definition",
          message: `Context def is not valid. Schema Error: ${err}'`
        }
      };
    }

    if (!context_types.has(c_def.context_type)) {
      context_types.add(c_def.context_type);
    } else {
      return {
        error: {
          error_type: "definition",
          message: `Context types must be unique. '${c_def.context_type}' is present more than once.`
        }
      };
    }

    if (c_def.schema.type === undefined || c_def.schema.type !== "object") {
      return {
        error: {
          error_type: "definition",
          message: "Context schemas must declare the root type to be an object."
        }
      };
    }
  }

  return {
    error: null
  };
}

export function validateIdentityDefs(identity_defs) {
  const id_types = [];
  for (const id_def of identity_defs) {
    const err = _schemaError(id_def, identity_definition_schema);
    if (err !== null) {
      return {
        error: {
          error_type: "definition",
          message: `Identity definition is not valid. Schema Error: ${err}'`
        }
      };
    }

    if (!id_types.includes(id_def.identity_type)) {
      id_types.push(id_def.identity_type);
    } else {
      return {
        error: {
          error_type: "definition",
          message: `Identity types must be unique. '${id_def.identity_type}' is present more than once.`
        }
      };
    }

    if (id_def.schema.type === undefined || id_def.schema.type !== "object") {
      return {
        error: {
          error_type: "definition",
          message: "Identity schemas must declare the root type to be an object."
        }
      };
    }
  }

  return {
    error: null
  };
}

export function validateResourceDefs(resource_defs) {
  const r_types = new Set();
  for (const r_def of resource_defs) {
    const err = _schemaError(r_def, resource_definition_schema);
    if (err !== null) {
      return {
        error: {
          error_type: "definition",
          message: `Resource definition is not valid. Schema Error: ${err}`
        }
      };
    }

    if (!r_types.has(r_def.resource_type)) {
      r_types.add(r_def.resource_type);
    } else {
      return {
        error: {
          error_type: "definition",
          message: `Resource types must be unique. '${r_def.resource_type}' is present more than once.`
        }
      };
    }

    if (r_def.schema.type === undefined || r_def.schema.type !== "object") {
      return {
        error: {
          error_type: "definition",
          message: "Resource schemas must declare the root type to be an object."
        }
      };
    }
  }

  return {
    error: null
  };
}

export function validateGrants(grants) {
  for (const g of grants) {
    const err = _schemaError(g, grant_schema);
    if (err !== null) {
      return {
        error: {
          error_type: "grant",
          message: `The grant is not valid. Schema Error: ${err}`
        }
      };
    }
  }

  return {
    error: null
  };
}

function _validateRequestIdentities(identities, identity_lut) {
  for (const i_type of Object.keys(identities)) {
    if (!(i_type in identity_lut)) {
      return `Identity Type '${i_type}' is not valid.`;
    }

    const instances = identities[i_type];
    for (let i_num = 0; i_num < instances.length; i_num++) {
      const err = _schemaError(instances[i_num], identity_lut[i_type].schema);
      if (err !== null) {
        return `Identity '${i_type}[${i_num}]' is not valid. Schema Error: ${err}`;
      }
    }
  }

  return null;
}

function _validateRequestResource(resource_type, resource, action, resource_lut) {
  if (!(resource_type in resource_lut)) {
    return `Resource type '${resource_type}' is not valid.`;
  }

  const err = _schemaError(resource, resource_lut[resource_type].schema);
  if (err !== null) {
    return `The request resource is not valid for the '${resource_type}' resource type. Schema Error: ${err}`;
  }

  if (!resource_lut[resource_type].actions.includes(action)) {
    return `'${action}' is not a valid action for the '${resource_type}' resource type.`;
  }

  return null;
}

function _validateRequestContext(context_type, context, context_lut) {
  if (!(context_type in context_lut)) {
    return `Context type '${context_type}' is not valid.`;
  }

  const err = _schemaError(context, context_lut[context_type].schema);
  if (err !== null) {
    return `The request context is not valid for the '${context_type}' context type. Schema Error: ${err}`;
  }

  return null;
}

function _lut(defs, key) {
  const lut = {};
  for (const d of defs) {
    lut[d[key]] = d;
  }

  return lut;
}

export function validateRequest(request, context_defs, identity_defs, resource_defs) {
  const err = _schemaError(request, request_schema);
  if (err !== null) {
    return {
      error: {
        error_type: "request",
        message: `The request is not valid. Schema Error: ${err}`
      }
    };
  }

  let msg = _validateRequestIdentities(
    request.identities,
    _lut(identity_defs, "identity_type")
  );
  if (msg !== null) {
    return {
      error: {
        error_type: "request",
        message: msg
      }
    };
  }

  msg = _validateRequestResource(
    request.resource_type,
    request.resource,
    request.action,
    _lut(resource_defs, "resource_type")
  );
  if (msg !== null) {
    return {
      error: {
        error_type: "request",
        message: msg
      }
    };
  }

  msg = _validateRequestContext(
    request.context_type,
    request.context,
    _lut(context_defs, "context_type")
  );
  if (msg !== null) {
    return {
      error: {
        error_type: "request",
        message: msg
      }
    };
  }

  return {
    error: null
  };
}

export function validateBatchRequest(batch_request, context_defs, identity_defs, resource_defs) {
  const schemaErr = _schemaError(batch_request, batch_request_schema);
  if (schemaErr !== null) {
    return {
      error: {
        error_type: "request",
        message: `The batch request is not valid. Schema Error: ${schemaErr}`
      },
      batch: []
    };
  }

  const identity_lut = _lut(identity_defs, "identity_type");
  const resource_lut = _lut(resource_defs, "resource_type");
  const context_lut = _lut(context_defs, "context_type");

  let msg = _validateRequestIdentities(batch_request.identities, identity_lut);
  if (msg !== null) {
    return {
      error: {
        error_type: "request",
        message: msg
      },
      batch: []
    };
  }

  msg = _validateRequestResource(
    batch_request.resource_type,
    batch_request.resource,
    batch_request.action,
    resource_lut
  );
  if (msg !== null) {
    return {
      error: {
        error_type: "request",
        message: msg
      },
      batch: []
    };
  }

  msg = _validateRequestContext(
    batch_request.context_type,
    batch_request.context,
    context_lut
  );
  if (msg !== null) {
    return {
      error: {
        error_type: "request",
        message: msg
      },
      batch: []
    };
  }

  const batch = [];
  for (const item of batch_request.batch) {
    let item_err = null;
    if (item_err === null && item.identities !== undefined && item.identities !== null) {
      item_err = _validateRequestIdentities(item.identities, identity_lut);
    }

    if (
      item_err === null &&
      (
        (item.resource_type !== undefined && item.resource_type !== null) ||
        (item.resource !== undefined && item.resource !== null)
      )
    ) {
      item_err = _validateRequestResource(
        item.resource_type !== undefined ? item.resource_type : batch_request.resource_type,
        item.resource !== undefined ? item.resource : batch_request.resource,
        batch_request.action,
        resource_lut
      );
    }

    if (
      item_err === null &&
      (
        (item.context_type !== undefined && item.context_type !== null) ||
        (item.context !== undefined && item.context !== null)
      )
    ) {
      item_err = _validateRequestContext(
        item.context_type !== undefined ? item.context_type : batch_request.context_type,
        item.context !== undefined ? item.context : batch_request.context,
        context_lut
      );
    }

    if (item_err !== null) {
      batch.push({
        error_type: "request",
        message: item_err
      });
    } else {
      batch.push(null);
    }
  }

  return {
    error: null,
    batch
  };
}

/** Deep structural equality mirroring Python `==` for JSON values. */
function _jsonEqual(a, b) {
  if (a === b) {
    return true;
  }

  if (a === null || b === null || typeof a !== typeof b) {
    return false;
  }

  if (Array.isArray(a) || Array.isArray(b)) {
    if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) {
      return false;
    }

    for (let i = 0; i < a.length; i++) {
      if (!_jsonEqual(a[i], b[i])) {
        return false;
      }
    }

    return true;
  }

  if (typeof a === "object") {
    const aKeys = Object.keys(a);
    const bKeys = Object.keys(b);
    if (aKeys.length !== bKeys.length) {
      return false;
    }

    for (const k of aKeys) {
      if (!Object.prototype.hasOwnProperty.call(b, k) || !_jsonEqual(a[k], b[k])) {
        return false;
      }
    }

    return true;
  }

  return false;
}

export function evaluateOne(request, grant, execute) {
  const result = {
    is_applicable: false,
    query_result: null,
    failure: null
  };
  if (grant.actions.length > 0 && !grant.actions.includes(request.action)) {
    return result;
  }

  const query_result = execute(
    grant.query,
    {
      request,
      grant
    }
  );
  if (query_result.failure === null || query_result.failure === undefined) {
    result.query_result = query_result.result;
    if (_jsonEqual(query_result.result, grant.equality)) {
      result.is_applicable = true;
    }
  } else {
    result.failure = query_result.failure;
    if (grant.applicable_on_failure === true) {
      result.is_applicable = true;
    }
  }

  return result;
}

export function audit(request, grants, execute) {
  const result = {
    results: [],
    error: null
  };
  for (const g of grants) {
    const g_eval = evaluateOne(request, g, execute);
    result.results.push({
      grant: g,
      is_applicable: g_eval.is_applicable,
      query_result: g_eval.query_result,
      failure: g_eval.failure
    });
  }

  return result;
}

export function authorize(request, grants, execute) {
  const allow_grants = [];
  const deny_grants = [];
  for (const g of grants) {
    if (g.effect === "allow") {
      allow_grants.push(g);
    } else {
      deny_grants.push(g);
    }
  }

  for (const g of deny_grants) {
    const g_eval = evaluateOne(request, g, execute);
    if (g_eval.is_applicable === true) {
      return {
        is_authorized: false,
        grant: g,
        message:
          "A deny grant is applicable to the request. Therefore, the request is not authorized.",
        error: null
      };
    }
  }

  for (const g of allow_grants) {
    const g_eval = evaluateOne(request, g, execute);
    if (g_eval.is_applicable === true) {
      return {
        is_authorized: true,
        grant: g,
        message:
          "An allow grant is applicable to the request, and there are no deny grants that are applicable to the request. Therefore, the request is authorized.",
        error: null
      };
    }
  }

  return {
    is_authorized: false,
    grant: null,
    message:
      "No grants are applicable to the request. Therefore, the request is implicitly denied and is not authorized.",
    error: null
  };
}

function _validate(context_defs, identity_defs, resource_defs, grants, request, is_batch) {
  const c_val = validateContextDefs(context_defs);
  if (c_val.error !== null) {
    return c_val;
  }

  const i_val = validateIdentityDefs(identity_defs);
  if (i_val.error !== null) {
    return i_val;
  }

  const r_val = validateResourceDefs(resource_defs);
  if (r_val.error !== null) {
    return r_val;
  }

  const g_val = validateGrants(grants);
  if (g_val.error !== null) {
    return g_val;
  }

  if (is_batch === true) {
    const req_val = validateBatchRequest(
      request,
      context_defs,
      identity_defs,
      resource_defs
    );
    if (req_val.error !== null) {
      return req_val;
    }

    return {
      error: null,
      batch: req_val.batch
    };
  }

  const req_val = validateRequest(
    request,
    context_defs,
    identity_defs,
    resource_defs
  );
  if (req_val.error !== null) {
    return req_val;
  }

  return {
    error: null
  };
}

export function auditWorkflow(context_defs, identity_defs, resource_defs, grants, request, execute) {
  const val = _validate(
    context_defs,
    identity_defs,
    resource_defs,
    grants,
    request,
    false
  );
  if (val.error !== null) {
    return {
      results: [],
      error: val.error
    };
  }

  return audit(request, grants, execute);
}

export function authorizeWorkflow(context_defs, identity_defs, resource_defs, grants, request, execute) {
  const val = _validate(
    context_defs,
    identity_defs,
    resource_defs,
    grants,
    request,
    false
  );
  if (val.error !== null) {
    return {
      is_authorized: false,
      grant: null,
      message: "An error has occurred. Therefore, the request is not authorized.",
      error: val.error
    };
  }

  return authorize(request, grants, execute);
}

/** Merge a batch item over the root batch_request into a full request. */
function _mergeBatchItem(item, batch_request) {
  return {
    identities: item.identities || batch_request.identities,
    action: batch_request.action,
    resource_type: item.resource_type || batch_request.resource_type,
    resource: item.resource || batch_request.resource,
    context_type: item.context_type || batch_request.context_type,
    context:
      item.context !== undefined && item.context !== null
        ? item.context
        : batch_request.context
  };
}

export function batchAudit(batch_request, grants, execute) {
  const batch_results = [];
  for (const item of batch_request.batch) {
    const request = _mergeBatchItem(item, batch_request);
    const results = [];
    for (const g of grants) {
      const g_eval = evaluateOne(request, g, execute);
      results.push({
        is_applicable: g_eval.is_applicable,
        query_result: g_eval.query_result,
        failure: g_eval.failure
      });
    }

    batch_results.push({
      results,
      error: null
    });
  }

  return {
    grants,
    batch: batch_results,
    error: null
  };
}

export function batchAuthorize(batch_request, grants, execute) {
  const results = [];
  for (const item of batch_request.batch) {
    results.push(authorize(_mergeBatchItem(item, batch_request), grants, execute));
  }

  return {
    batch: results,
    error: null
  };
}

export function batchAuditWorkflow(context_defs, identity_defs, resource_defs, grants, batch_request, execute) {
  const val = _validate(
    context_defs,
    identity_defs,
    resource_defs,
    grants,
    batch_request,
    true
  );
  if (val.error !== null) {
    return {
      grants: [],
      batch: [],
      error: val.error
    };
  }

  const batch_results = [];
  const batch_results_indexes = [];
  for (let i = 0; i < val.batch.length; i++) {
    const error = val.batch[i];
    if (error === null) {
      batch_results.push(null);
      batch_results_indexes.push(i);
    } else {
      batch_results.push({
        results: [],
        error
      });
    }
  }

  const result = batchAudit(batch_request, grants, execute);
  const n = Math.min(result.batch.length, batch_results_indexes.length);
  for (let j = 0; j < n; j++) {
    batch_results[batch_results_indexes[j]] = result.batch[j];
  }

  result.batch = batch_results;

  return result;
}

export function batchAuthorizeWorkflow(context_defs, identity_defs, resource_defs, grants, batch_request, execute) {
  const val = _validate(
    context_defs,
    identity_defs,
    resource_defs,
    grants,
    batch_request,
    true
  );
  if (val.error !== null) {
    return {
      batch: [],
      error: val.error
    };
  }

  const batch_results = [];
  const batch_results_indexes = [];
  for (let i = 0; i < val.batch.length; i++) {
    const error = val.batch[i];
    if (error === null) {
      batch_results.push(null);
      batch_results_indexes.push(i);
    } else {
      batch_results.push({
        is_authorized: false,
        grant: null,
        message: "An error has occurred. Therefore, the request is not authorized.",
        error
      });
    }
  }

  const result = batchAuthorize(batch_request, grants, execute);
  const n = Math.min(result.batch.length, batch_results_indexes.length);
  for (let j = 0; j < n; j++) {
    batch_results[batch_results_indexes[j]] = result.batch[j];
  }

  result.batch = batch_results;

  return result;
}
