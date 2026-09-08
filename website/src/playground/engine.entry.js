/**
 * Playground engine entry point.
 *
 * Bundled by the site build (esbuild) into dist/playground/engine.js as a
 * browser ESM module. Re-exports the JS reference implementation and provides
 * the JMESPath-backed `execute` adapter that the reference's operations use.
 *
 * Note the JS `jmespath` package signature is `search(data, expression)` — the
 * reverse of the Python `jmespath.search(expression, data)`.
 */
import jmespath from "jmespath";

export * from "../../../src/reference.js";

/**
 * The JMESPath query backend. Matches the reference `execute` contract:
 * returns `{ result, failure }` where `failure` is null on success or a message
 * string on error.
 */
export function jmespathExecute(expression, data) {
  const out = {
    result: null,
    failure: null
  };
  try {
    out.result = jmespath.search(data, expression);
  } catch (exc) {
    out.failure = `A JMESPath Query error has occurred: ${exc}`;
  }

  return out;
}

/** Available query backends, keyed by the value used in the UI select. */
export const QUERY_BACKENDS = {
  jmespath: jmespathExecute
};
