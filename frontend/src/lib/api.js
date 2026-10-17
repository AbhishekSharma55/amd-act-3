import factory from "../../../shared/mocks/factory.json" with { type: "json" };
import extract from "../../../shared/mocks/extract.json" with { type: "json" };
import solve from "../../../shared/mocks/solve.json" with { type: "json" };
import replay from "../../../shared/mocks/replay.json" with { type: "json" };

const mocks = {
  "/api/factory": factory,
  "/api/extract": extract,
  "/api/solve": solve,
  "/api/replay": replay,
};

export class ApiError extends Error {
  constructor(
    message,
    { code = "request_failed", status = 0, retryable = false } = {},
  ) {
    super(message);
    this.name = "ApiError";
    Object.assign(this, { code, status, retryable });
  }
}

/** Shared transport for future feature modules. No silent fallback to samples. */
export function createApi({
  useMocks = true,
  baseUrl = "",
  fetchImpl = globalThis.fetch,
} = {}) {
  return async function api(path, body, { signal } = {}) {
    if (useMocks) {
      if (path === "/api/approve")
        throw new ApiError(
          "Approval needs the service to recheck the stored plan. A recorded response cannot approve it.",
          { code: "approval_requires_service" },
        );
      if (!mocks[path])
        throw new ApiError(`No recorded sample is available for ${path}.`, {
          code: "mock_unavailable",
        });
      return structuredClone(mocks[path]);
    }

    let response;
    try {
      response = await fetchImpl(`${baseUrl.replace(/\/$/, "")}${path}`, {
        method: body === undefined ? "GET" : "POST",
        ...(body === undefined
          ? {}
          : {
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(body),
            }),
        signal,
      });
    } catch (error) {
      if (error.name === "AbortError") throw error;
      throw new ApiError(
        "Could not reach the service. Check the connection, then retry.",
        { code: "network_error", retryable: true },
      );
    }

    let data;
    try {
      data = await response.json();
    } catch {
      throw new ApiError(
        `The API returned an unreadable response (${response.status}).`,
        { code: "invalid_response", status: response.status, retryable: true },
      );
    }
    if (!response.ok) {
      throw new ApiError(
        data?.error?.message || `Request failed (${response.status}).`,
        {
          code: data?.error?.code,
          status: response.status,
          retryable: data?.error?.retryable ?? response.status >= 500,
        },
      );
    }
    return data;
  };
}

export const api = createApi({
  useMocks: import.meta.env?.VITE_USE_MOCKS !== "0",
  baseUrl: import.meta.env?.VITE_API_BASE_URL || "",
});
