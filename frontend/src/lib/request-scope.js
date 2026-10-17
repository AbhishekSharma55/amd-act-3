/** One workflow request at a time; cancelled or superseded work cannot commit. */
export function createRequestScope() {
  let current = null;
  let revision = 0;
  return {
    begin() {
      if (current) return null;
      current = { revision, controller: new AbortController() };
      return current;
    },
    matches(token) { return current === token && token.revision === revision; },
    finish(token) { if (current === token) current = null; },
    cancel() {
      revision += 1;
      current?.controller.abort();
      current = null;
    },
    get revision() { return revision; },
  };
}
