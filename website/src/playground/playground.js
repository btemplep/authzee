/**
 * Authzee playground logic.
 *
 * All state lives in the browser, seeded from the basic example so the page is
 * immediately runnable. The JS reference engine (bundled to ./engine.js) does
 * the actual work; JMESPath is the query backend.
 */
import {
  QUERY_BACKENDS,
  authorizeWorkflow,
  auditWorkflow,
  batchAuthorizeWorkflow,
  batchAuditWorkflow,
  validateContextDefs,
  validateIdentityDefs,
  validateResourceDefs,
  validateGrants,
  validateRequest,
  validateBatchRequest
} from "./engine.js";

// ---------- Seed state (complex example) ----------
const SEED = {
  context_defs: [
    {
      context_type: "NULL",
      schema: { type: "object", additionalProperties: false }
    },
    {
      context_type: "ANY",
      schema: { type: "object" }
    },
    {
      context_type: "MySpecialContext",
      schema: {
        type: "object",
        additionalProperties: false,
        required: ["Team"],
        properties: { Team: { type: "string" } }
      }
    },
    {
      context_type: "BalloonRelationships",
      schema: {
        type: "object",
        additionalProperties: false,
        required: ["BalloonStore"],
        properties: {
          BalloonStore: {
            type: "array",
            items: {
              type: "object",
              properties: {
                id: { type: "string" },
                name: { type: "string" },
                owner_department: { type: "string" },
                location: { type: "string" }
              },
              required: ["id", "name", "owner_department", "location"]
            }
          }
        }
      }
    }
  ],
  identity_defs: [
    {
      identity_type: "User",
      schema: {
        type: "object",
        properties: {
          id: { type: "string" },
          department: { type: "string" },
          email: { type: "string" }
        },
        required: ["id", "department", "email"]
      }
    },
    {
      identity_type: "Group",
      schema: {
        type: "object",
        properties: {
          name: { type: "string" },
          department: { type: "string" },
          type: { type: "string", enum: ["team", "project", "department"] }
        },
        required: ["name", "department", "type"]
      }
    },
    {
      identity_type: "Role",
      schema: {
        type: "object",
        properties: {
          name: { type: "string" },
          permissions: { type: "array", items: { type: "string" } },
          level: { type: "string", enum: ["basic", "advanced", "admin"] }
        },
        required: ["name", "permissions", "level"]
      }
    },
    {
      identity_type: "OtherID",
      schema: {
        type: "object",
        required: [],
        properties: { dontCare: { type: "string" } }
      }
    }
  ],
  resource_defs: [
    {
      resource_type: "BalloonStore",
      actions: ["read", "manage", "create_balloon"],
      schema: {
        type: "object",
        required: ["id", "name", "owner_department", "location"],
        properties: {
          id: { type: "string" },
          name: { type: "string" },
          owner_department: { type: "string" },
          location: { type: "string" }
        }
      }
    },
    {
      resource_type: "Balloon",
      actions: ["read", "inflate", "deflate", "pop", "tie"],
      schema: {
        type: "object",
        required: ["id", "color", "size", "material", "owner_department", "inflated"],
        properties: {
          id: { type: "string" },
          color: { type: "string" },
          size: { type: "string", enum: ["small", "medium", "large"] },
          material: { type: "string" },
          owner_department: { type: "string" },
          inflated: { type: "boolean" }
        }
      }
    },
    {
      resource_type: "BalloonString",
      actions: ["read", "cut", "tie", "untie"],
      schema: {
        type: "object",
        required: ["id", "length", "color", "material"],
        properties: {
          id: { type: "string" },
          length: { type: "number" },
          color: { type: "string" },
          material: { type: "string" }
        }
      }
    }
  ],
  grants: [
    {
      effect: "allow",
      actions: ["read"],
      query: "contains(request.identities.User[].department, request.resource.owner_department)",
      equality: true,
      applicable_on_failure: false,
      data: {}
    },
    {
      effect: "allow",
      actions: ["read"],
      query:
        "request.context_type == 'MySpecialContext' && contains(request.identities.User[].department, request.context.Team)",
      equality: true,
      applicable_on_failure: false,
      data: {}
    },
    {
      effect: "allow",
      actions: ["read", "inflate", "deflate", "pop", "tie"],
      query: "request.context_type == 'NULL' && contains(request.identities.Role[].level, 'admin')",
      equality: true,
      applicable_on_failure: false,
      data: {}
    },
    {
      effect: "allow",
      actions: ["read"],
      query:
        "request.resource_type == 'BalloonStore' && contains(request.identities.Group[?type=='department'].department, request.resource.owner_department)",
      equality: true,
      applicable_on_failure: false,
      data: {}
    },
    {
      effect: "allow",
      actions: ["inflate"],
      query:
        "contains(request.identities.Role[*].permissions[], 'balloon:inflate') && request.identities.User[0].department == request.resource.owner_department",
      equality: true,
      applicable_on_failure: false,
      data: {}
    },
    {
      effect: "deny",
      actions: ["pop"],
      query:
        "request.context_type == 'NULL' && request.resource.size == 'large' && !contains(request.identities.Role[*].level, 'admin')",
      equality: true,
      applicable_on_failure: true,
      data: {}
    },
    {
      effect: "deny",
      actions: [],
      query: "request.context_type == 'NULL' && length(request.identities.User) == `0`",
      equality: true,
      applicable_on_failure: true,
      data: {}
    }
  ],
  request: {
    identities: {
      User: [
        { id: "user123", department: "party_planning", email: "john.doe@company.com" }
      ],
      Group: [
        { name: "event-team", department: "party_planning", type: "team" },
        { name: "party-planning-dept", department: "party_planning", type: "department" }
      ],
      Role: [
        {
          name: "party-coordinator",
          permissions: ["balloon:read", "balloon:inflate", "balloon:tie"],
          level: "advanced"
        }
      ]
    },
    resource_type: "Balloon",
    action: "inflate",
    resource: {
      id: "balloon456",
      color: "red",
      size: "medium",
      material: "latex",
      owner_department: "party_planning",
      inflated: false
    },
    context_type: "MySpecialContext",
    context: { Team: "party_planning" }
  },
  batch_request: {
    identities: {
      User: [
        { id: "user123", department: "party_planning", email: "john.doe@company.com" }
      ],
      Group: [
        { name: "event-team", department: "party_planning", type: "team" },
        { name: "party-planning-dept", department: "party_planning", type: "department" }
      ],
      Role: [
        {
          name: "party-coordinator",
          permissions: ["balloon:read", "balloon:inflate", "balloon:tie"],
          level: "advanced"
        }
      ]
    },
    action: "inflate",
    resource_type: "Balloon",
    resource: {
      id: "balloon123",
      color: "green",
      size: "medium",
      material: "latex",
      owner_department: "party_planning",
      inflated: false
    },
    context_type: "MySpecialContext",
    context: { Team: "ABC" },
    batch: [
      {
        resource: {
          id: "balloon456",
          color: "red",
          size: "medium",
          material: "latex",
          owner_department: "party_planning",
          inflated: false
        }
      },
      {
        identities: {
          User: [
            { id: "Store123", department: "Store 123", owner_department: "IDK", location: "Somewhere" }
          ],
          Group: [
            { name: "My Special group", department: "special_dept", type: "team" }
          ]
        },
        resource_type: "BalloonStore",
        resource: { id: "1234", name: "Special store", owner_department: "special_dept", location: "Somewhere" },
        context_type: "NULL",
        context: {}
      },
      {}
    ]
  }
};

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

const state = clone(SEED);

const $ = (id) => document.getElementById(id);

// ---------- Editor helpers ----------

/**
 * Parse JSON from a textarea, reporting status. Returns the parsed value, or
 * undefined on error (and marks the status element).
 */
function parseEditor(textareaId, statusId) {
  const status = $(statusId);
  try {
    const value = JSON.parse($(textareaId).value);
    if (status) {
      status.textContent = "valid JSON";
      status.className = "pg-status ok";
    }

    return value;
  } catch (err) {
    if (status) {
      status.textContent = "invalid JSON: " + err.message;
      status.className = "pg-status bad";
    }

    return undefined;
  }
}

function pretty(value) {
  return JSON.stringify(value, null, 4);
}

/**
 * Highlight a JSON string into HTML (self-contained, no dependency). Wraps
 * tokens in `.jk` (key), `.js` (string), `.jn` (number), `.jb` (boolean),
 * `.jz` (null), `.jp` (punctuation) spans. Input must already be escaped-safe;
 * this escapes HTML itself.
 */
function highlightJson(text) {
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Match strings (with a following colon => key), numbers, booleans, null,
  // and punctuation.
  const tokenRe =
    /("(?:\\.|[^"\\])*")(\s*:)?|\b(true|false)\b|\b(null)\b|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|([{}\[\],])/g;

  return escaped.replace(
    tokenRe,
    (match, str, colon, bool, nul, num, punct) => {
      if (str !== undefined) {
        if (colon !== undefined) {
          return '<span class="jk">' + str + "</span>" + '<span class="jp">' + colon + "</span>";
        }

        return '<span class="js">' + str + "</span>";
      }

      if (bool !== undefined) {
        return '<span class="jb">' + bool + "</span>";
      }

      if (nul !== undefined) {
        return '<span class="jz">' + nul + "</span>";
      }

      if (num !== undefined) {
        return '<span class="jn">' + num + "</span>";
      }

      if (punct !== undefined) {
        return '<span class="jp">' + punct + "</span>";
      }

      return match;
    }
  );
}

/** Render a value as highlighted JSON HTML into a target <pre>/<code> element. */
function renderJson(el, value) {
  el.innerHTML = highlightJson(pretty(value));
}

/** Render an already-stringified JSON text as highlighted HTML. */
function renderJsonText(el, text) {
  el.innerHTML = highlightJson(text);
}

/**
 * Turn a plain <textarea> editor into a syntax-highlighted editor by placing a
 * highlight layer (<pre><code>) behind a transparent-text textarea and keeping
 * them in sync on input and scroll. Returns a function to re-sync the layer
 * (call after programmatically setting the textarea value).
 */
const _highlightLayers = {};

function enhanceEditor(textareaId) {
  const ta = $(textareaId);
  const wrap = document.createElement("div");
  wrap.className = "pg-code-edit";
  ta.parentNode.insertBefore(wrap, ta);

  const layer = document.createElement("pre");
  layer.className = "pg-hl";
  layer.setAttribute("aria-hidden", "true");
  const code = document.createElement("code");
  layer.appendChild(code);

  wrap.appendChild(layer);
  wrap.appendChild(ta);

  function sync() {
    renderJsonText(code, ta.value);
    layer.scrollTop = ta.scrollTop;
    layer.scrollLeft = ta.scrollLeft;
  }

  ta.addEventListener("input", sync);
  ta.addEventListener("scroll", () => {
    layer.scrollTop = ta.scrollTop;
    layer.scrollLeft = ta.scrollLeft;
  });

  // Editing niceties: Enter carries indentation (and adds a level after an
  // opening bracket/brace); Tab inserts spaces instead of moving focus.
  ta.addEventListener("keydown", (e) => {
    const fireInput = () => ta.dispatchEvent(new Event("input", { bubbles: true }));
    if (e.key === "Enter") {
      e.preventDefault();
      const start = ta.selectionStart;
      const end = ta.selectionEnd;
      const value = ta.value;
      const lineStart = value.lastIndexOf("\n", start - 1) + 1;
      const currentLine = value.slice(lineStart, start);
      const indentMatch = currentLine.match(/^[ \t]*/);
      let indent = indentMatch ? indentMatch[0] : "";
      const prevChar = value.slice(0, start).trimEnd().slice(-1);
      const nextChar = value.slice(end).trimStart().slice(0, 1);

      let insert = "\n" + indent;
      if (prevChar === "{" || prevChar === "[") {
        const inner = indent + "    ";
        if (
          (prevChar === "{" && nextChar === "}") ||
          (prevChar === "[" && nextChar === "]")
        ) {
          // Opening/closing pair: put the caret on an indented middle line.
          insert = "\n" + inner + "\n" + indent;
          ta.value = value.slice(0, start) + insert + value.slice(end);
          ta.selectionStart = ta.selectionEnd = start + 1 + inner.length;
          fireInput();
          return;
        }

        insert = "\n" + inner;
      }

      ta.value = value.slice(0, start) + insert + value.slice(end);
      ta.selectionStart = ta.selectionEnd = start + insert.length;
      fireInput();
    } else if (e.key === "Tab") {
      e.preventDefault();
      const start = ta.selectionStart;
      const end = ta.selectionEnd;
      ta.value = ta.value.slice(0, start) + "    " + ta.value.slice(end);
      ta.selectionStart = ta.selectionEnd = start + 4;
      fireInput();
    }
  });

  _highlightLayers[textareaId] = sync;
  sync();

  return sync;
}

/** Re-sync a highlighted editor after setting its value programmatically. */
function syncEditor(textareaId) {
  const sync = _highlightLayers[textareaId];
  if (sync) {
    sync();
  }
}

/**
 * Reformat an editor's JSON with 4-space indentation if it currently parses.
 * No-op (leaves the text as-is) when the content isn't valid JSON, so it never
 * destroys in-progress edits. Re-syncs the highlight layer after formatting.
 */
function formatEditor(textareaId) {
  const ta = $(textareaId);
  try {
    const value = JSON.parse(ta.value);
    const formatted = pretty(value);
    if (formatted !== ta.value) {
      ta.value = formatted;
    }
  } catch (err) {
    // Not valid JSON yet — leave the text untouched.
  }

  syncEditor(textareaId);
}

// ---------- Overview ----------
function renderOverview() {
  const groups = [
    ["context", "context_defs", "context_type"],
    ["identity", "identity_defs", "identity_type"],
    ["resource", "resource_defs", "resource_type"]
  ];

  for (const [key, listName, typeKey] of groups) {
    const defs = Array.isArray(state[listName]) ? state[listName] : [];
    $("ov-" + key + "-count").textContent = String(defs.length);
    const list = $("ov-" + key + "-list");
    list.innerHTML = "";
    for (const d of defs) {
      const li = document.createElement("li");
      li.textContent = d && d[typeKey] !== undefined ? String(d[typeKey]) : "(unnamed)";
      list.appendChild(li);
    }
  }

  const grants = Array.isArray(state.grants) ? state.grants : [];
  $("ov-grant-count").textContent = String(grants.length);
  const allow = grants.filter((g) => g && g.effect === "allow").length;
  const deny = grants.filter((g) => g && g.effect === "deny").length;
  $("ov-allow-count").textContent = String(allow);
  $("ov-deny-count").textContent = String(deny);
}

// ---------- Tabs ----------
function initTabs() {
  const tabs = document.querySelectorAll(".pg-tab");
  const panels = document.querySelectorAll(".pg-panel");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      panels.forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      const name = tab.getAttribute("data-tab");
      document.querySelector('.pg-panel[data-panel="' + name + '"]').classList.add("active");
    });
  });
}

// ---------- Definitions tab ----------
const DEF_MAP = {
  context: {
    list: "context_defs",
    label: "Context Definitions",
    validate: validateContextDefs,
    hint: "Context is extra structured data passed with a request."
  },
  identity: {
    list: "identity_defs",
    label: "Identity Definitions",
    validate: validateIdentityDefs,
    hint: "Identities describe the calling entity (users, groups, roles, etc.)."
  },
  resource: {
    list: "resource_defs",
    label: "Resource Definitions",
    validate: validateResourceDefs,
    hint: "Resources are things that actions are performed on. "
  }
};
let activeDef = "context";

function loadDefEditor() {
  const info = DEF_MAP[activeDef];
  $("def-editor-label").textContent = info.label;
  $("def-editor").value = pretty(state[info.list]);
  syncEditor("def-editor");
  $("def-hint").textContent = info.hint;
  $("def-status").textContent = "";
  $("def-status").className = "pg-status";
  validateDefs();
}

/** Validate the current definition editor and show a result message. */
function validateDefs() {
  const info = DEF_MAP[activeDef];
  const out = $("def-validate-result");
  const parsed = parseEditor("def-editor", "def-status");
  if (parsed === undefined) {
    out.textContent = "✗ Fix the JSON before validating.";
    out.className = "pg-validate-result bad";
    return;
  }

  if (!Array.isArray(parsed)) {
    out.textContent = "✗ Definitions must be a JSON array.";
    out.className = "pg-validate-result bad";
    return;
  }

  const result = info.validate(parsed);
  if (result.error === null) {
    out.textContent = "✓ Valid — " + parsed.length + " " + activeDef + " definition(s).";
    out.className = "pg-validate-result ok";
  } else {
    out.textContent = "✗ " + result.error.error_type + ": " + result.error.message;
    out.className = "pg-validate-result bad";
  }
}

function initDefinitions() {
  enhanceEditor("def-editor");
  loadDefEditor();
  $("def-type-select").querySelectorAll(".pg-side-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      // Persist current editor content before switching, if valid.
      commitDefEditor();
      $("def-type-select").querySelectorAll(".pg-side-item").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeDef = btn.getAttribute("data-def");
      loadDefEditor();
    });
  });

  $("def-editor").addEventListener("input", () => {
    const parsed = parseEditor("def-editor", "def-status");
    if (parsed !== undefined) {
      state[DEF_MAP[activeDef].list] = parsed;
      renderOverview();
    }
  });

  // Auto-format and validate when focus leaves the editor.
  $("def-editor").addEventListener("blur", () => {
    formatEditor("def-editor");
    validateDefs();
  });
}

function commitDefEditor() {
  const parsed = parseEditor("def-editor", "def-status");
  if (parsed !== undefined) {
    state[DEF_MAP[activeDef].list] = parsed;
  }
}

// ---------- Grants tab ----------
/** Validate the grants editor and show a result message. */
function validateGrantsEditor() {
  const out = $("grant-validate-result");
  const parsed = parseEditor("grant-editor", "grant-status");
  if (parsed === undefined) {
    out.textContent = "✗ Fix the JSON before validating.";
    out.className = "pg-validate-result bad";
    return;
  }

  if (!Array.isArray(parsed)) {
    out.textContent = "✗ Grants must be a JSON array.";
    out.className = "pg-validate-result bad";
    return;
  }

  const result = validateGrants(parsed);
  if (result.error === null) {
    out.textContent = "✓ Valid — " + parsed.length + " grant(s).";
    out.className = "pg-validate-result ok";
  } else {
    out.textContent = "✗ " + result.error.error_type + ": " + result.error.message;
    out.className = "pg-validate-result bad";
  }
}

function initGrants() {
  enhanceEditor("grant-editor");
  $("grant-editor").value = pretty(state.grants);
  syncEditor("grant-editor");
  $("grant-editor").addEventListener("input", () => {
    const parsed = parseEditor("grant-editor", "grant-status");
    if (parsed !== undefined) {
      state.grants = parsed;
      renderOverview();
      renderGrantBreakdown();
    }
  });

  // Auto-format and validate when focus leaves the editor.
  $("grant-editor").addEventListener("blur", () => {
    formatEditor("grant-editor");
    validateGrantsEditor();
  });

  renderGrantBreakdown();
  validateGrantsEditor();
}

/**
 * Render the grant breakdown: total, allow/deny counts, and per-action counts
 * (further split into allow/deny). Grants with no actions apply to all actions
 * and are tallied under "(any action)".
 */
function renderGrantBreakdown() {
  const grants = Array.isArray(state.grants) ? state.grants.filter((g) => g && typeof g === "object") : [];
  const allow = grants.filter((g) => g.effect === "allow").length;
  const deny = grants.filter((g) => g.effect === "deny").length;

  $("grant-count-label").textContent = grants.length + " total";
  $("bd-total").textContent = String(grants.length);
  $("bd-allow").textContent = String(allow);
  $("bd-deny").textContent = String(deny);

  // Tally per action.
  const byAction = new Map();
  const bump = (action, effect) => {
    if (!byAction.has(action)) {
      byAction.set(action, { allow: 0, deny: 0 });
    }

    const entry = byAction.get(action);
    if (effect === "deny") {
      entry.deny += 1;
    } else {
      entry.allow += 1;
    }
  };

  for (const g of grants) {
    const acts = Array.isArray(g.actions) ? g.actions : [];
    if (acts.length === 0) {
      bump("(any action)", g.effect);
    } else {
      for (const a of acts) {
        bump(a, g.effect);
      }
    }
  }

  const list = $("bd-actions");
  list.innerHTML = "";
  const actions = Array.from(byAction.keys()).sort((a, b) => {
    // Keep "(any action)" first, then alphabetical.
    if (a === "(any action)") {
      return -1;
    }

    if (b === "(any action)") {
      return 1;
    }

    return a.localeCompare(b);
  });

  if (actions.length === 0) {
    const li = document.createElement("li");
    li.className = "pg-bd-empty";
    li.textContent = "No grants.";
    list.appendChild(li);
    return;
  }

  for (const action of actions) {
    const entry = byAction.get(action);
    const li = document.createElement("li");
    li.className = "pg-bd-action";

    const name = document.createElement("span");
    name.className = "pg-bd-action-name";
    name.textContent = action;
    name.title = action;

    const counts = document.createElement("span");
    counts.className = "pg-bd-action-counts";
    counts.innerHTML =
      '<span class="pg-bd-allow">' + entry.allow + " allow</span>" +
      '<span class="pg-bd-deny">' + entry.deny + " deny</span>";

    li.appendChild(name);
    li.appendChild(counts);
    list.appendChild(li);
  }
}

// ---------- Operations tab ----------
let activeOp = "authorize";

/** Validate the request editor against the current defs; show a result message. */
function validateRequestEditor() {
  const out = $("req-validate-result");
  const parsed = parseEditor("req-editor", "req-status");
  if (parsed === undefined) {
    out.textContent = "✗ Fix the JSON before validating.";
    out.className = "pg-validate-result bad";
    return;
  }

  const result = validateRequest(
    parsed,
    state.context_defs,
    state.identity_defs,
    state.resource_defs
  );
  if (result.error === null) {
    out.textContent = "✓ Valid request.";
    out.className = "pg-validate-result ok";
  } else {
    out.textContent = "✗ " + result.error.error_type + ": " + result.error.message;
    out.className = "pg-validate-result bad";
  }
}

function initOperations() {
  enhanceEditor("req-editor");
  $("req-editor").value = pretty(state.request);
  syncEditor("req-editor");
  $("req-editor").addEventListener("input", () => {
    const parsed = parseEditor("req-editor", "req-status");
    if (parsed !== undefined) {
      state.request = parsed;
    }
  });

  // Auto-format and validate when focus leaves the editor.
  $("req-editor").addEventListener("blur", () => {
    formatEditor("req-editor");
    validateRequestEditor();
  });

  $("op-select").querySelectorAll(".pg-side-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      $("op-select").querySelectorAll(".pg-side-item").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeOp = btn.getAttribute("data-op");
    });
  });

  $("run-op").addEventListener("click", runOperation);
  validateRequestEditor();
}

function runOperation() {
  const request = parseEditor("req-editor", "req-status");
  const responseEl = $("op-response");
  if (request === undefined) {
    responseEl.textContent = "Fix the request JSON before running.";
    responseEl.className = "pg-response error";
    return;
  }

  const execute = QUERY_BACKENDS[$("query-backend").value] || QUERY_BACKENDS.jmespath;
  const fn = activeOp === "audit" ? auditWorkflow : authorizeWorkflow;
  try {
    const result = fn(
      state.context_defs,
      state.identity_defs,
      state.resource_defs,
      state.grants,
      request,
      execute
    );
    $("op-response-label").textContent = "Response — " + activeOp;
    renderJson(responseEl, result);
    responseEl.className = "pg-response";
  } catch (err) {
    responseEl.textContent = "Engine error: " + (err && err.message ? err.message : String(err));
    responseEl.className = "pg-response error";
  }
}

// ---------- Batch Operations tab ----------
let activeBatchOp = "batchAuthorize";

/** Validate the batch request editor against the current defs; show a result. */
function validateBatchRequestEditor() {
  const out = $("batch-req-validate-result");
  const parsed = parseEditor("batch-req-editor", "batch-req-status");
  if (parsed === undefined) {
    out.textContent = "✗ Fix the JSON before validating.";
    out.className = "pg-validate-result bad";
    return;
  }

  const result = validateBatchRequest(
    parsed,
    state.context_defs,
    state.identity_defs,
    state.resource_defs
  );
  if (result.error === null) {
    const itemErrors = (result.batch || []).filter((b) => b !== null).length;
    if (itemErrors === 0) {
      out.textContent = "✓ Valid batch request (" + (result.batch || []).length + " item(s)).";
      out.className = "pg-validate-result ok";
    } else {
      out.textContent = "⚠ Root valid, but " + itemErrors + " batch item(s) have errors (see item results on Run).";
      out.className = "pg-validate-result warn";
    }
  } else {
    out.textContent = "✗ " + result.error.error_type + ": " + result.error.message;
    out.className = "pg-validate-result bad";
  }
}

function initBatch() {
  enhanceEditor("batch-req-editor");
  $("batch-req-editor").value = pretty(state.batch_request);
  syncEditor("batch-req-editor");
  $("batch-req-editor").addEventListener("input", () => {
    const parsed = parseEditor("batch-req-editor", "batch-req-status");
    if (parsed !== undefined) {
      state.batch_request = parsed;
    }
  });

  // Auto-format and validate when focus leaves the editor.
  $("batch-req-editor").addEventListener("blur", () => {
    formatEditor("batch-req-editor");
    validateBatchRequestEditor();
  });

  $("batch-op-select").querySelectorAll(".pg-side-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      $("batch-op-select").querySelectorAll(".pg-side-item").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeBatchOp = btn.getAttribute("data-op");
    });
  });

  $("run-batch").addEventListener("click", runBatch);
  validateBatchRequestEditor();
}

function runBatch() {
  const batchRequest = parseEditor("batch-req-editor", "batch-req-status");
  const responseEl = $("batch-response");
  if (batchRequest === undefined) {
    responseEl.textContent = "Fix the batch request JSON before running.";
    responseEl.className = "pg-response error";
    return;
  }

  const execute = QUERY_BACKENDS[$("query-backend").value] || QUERY_BACKENDS.jmespath;
  const fn = activeBatchOp === "batchAudit" ? batchAuditWorkflow : batchAuthorizeWorkflow;
  try {
    const result = fn(
      state.context_defs,
      state.identity_defs,
      state.resource_defs,
      state.grants,
      batchRequest,
      execute
    );
    $("batch-response-label").textContent = "Response — " + activeBatchOp;
    renderJson(responseEl, result);
    responseEl.className = "pg-response";
  } catch (err) {
    responseEl.textContent = "Engine error: " + (err && err.message ? err.message : String(err));
    responseEl.className = "pg-response error";
  }
}

// ---------- Reset ----------
function initReset() {
  $("pg-reset").addEventListener("click", () => {
    Object.assign(state, clone(SEED));
    activeDef = "context";
    $("def-type-select").querySelectorAll(".pg-side-item").forEach((b, i) => {
      b.classList.toggle("active", i === 0);
    });
    loadDefEditor();
    $("grant-editor").value = pretty(state.grants);
    syncEditor("grant-editor");
    $("req-editor").value = pretty(state.request);
    syncEditor("req-editor");
    $("batch-req-editor").value = pretty(state.batch_request);
    syncEditor("batch-req-editor");
    $("grant-status").textContent = "";
    $("req-status").textContent = "";
    $("batch-req-status").textContent = "";
    $("op-response").textContent = "";
    $("op-response").className = "pg-response";
    $("batch-response").textContent = "";
    $("batch-response").className = "pg-response";
    renderOverview();
    renderGrantBreakdown();
    validateDefs();
    validateGrantsEditor();
    validateRequestEditor();
    validateBatchRequestEditor();
  });
}

// ---------- Sidebar collapse ----------
function initSidebarToggle() {
  const layout = document.querySelector(".pg-layout");
  const collapse = $("pg-sidebar-collapse");
  const expand = $("pg-sidebar-expand");

  function setCollapsed(collapsed) {
    layout.classList.toggle("sidebar-collapsed", collapsed);
  }

  collapse.addEventListener("click", () => setCollapsed(true));
  expand.addEventListener("click", () => setCollapsed(false));
}

// ---------- Init ----------
initTabs();
initDefinitions();
initGrants();
initOperations();
initBatch();
initReset();
initSidebarToggle();
renderOverview();
