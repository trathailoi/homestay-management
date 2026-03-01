// API client wrapper for all backend calls

export interface ApiSuccessResponse<T> {
  success: true;
  data: T;
  meta?: {
    total: number;
    page: number;
    per_page: number;
  };
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ApiErrorResponse {
  success: false;
  error: ApiErrorDetail;
}

export type ApiResponse<T> = ApiSuccessResponse<T>;

export class ApiError extends Error {
  code: string;
  details?: Record<string, unknown>;
  statusCode: number;

  constructor(
    message: string,
    code: string,
    statusCode: number,
    details?: Record<string, unknown>
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
  }
}

interface FetchOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
}

/**
 * Wrapper around fetch that handles JSON serialization, error handling,
 * and authentication cookies.
 *
 * @param path - API path (e.g., "/rooms", "/bookings/123")
 * @param options - Fetch options, body will be JSON.stringify'd if present
 * @returns Promise resolving to the response data
 * @throws ApiError on non-2xx responses
 */
export async function apiFetch<T>(
  path: string,
  options: FetchOptions = {}
): Promise<T> {
  const { body, headers: customHeaders, ...restOptions } = options;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...customHeaders,
  };

  const config: RequestInit = {
    ...restOptions,
    headers,
    credentials: "include", // Send cookies with every request
  };

  if (body !== undefined) {
    config.body = JSON.stringify(body);
  }

  const url = `/api/v1${path}`;
  const response = await fetch(url, config);

  if (!response.ok) {
    let errorData: { detail?: string | { msg?: string } };
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: response.statusText };
    }

    // Handle FastAPI error response format
    const message =
      typeof errorData.detail === "string"
        ? errorData.detail
        : errorData.detail?.msg || response.statusText;

    throw new ApiError(
      message,
      `HTTP_${response.status}`,
      response.status,
      typeof errorData.detail === "object" ? errorData.detail : undefined
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// Convenience methods
export const api = {
  get: <T>(path: string, options?: FetchOptions) =>
    apiFetch<T>(path, { ...options, method: "GET" }),

  post: <T>(path: string, body?: unknown, options?: FetchOptions) =>
    apiFetch<T>(path, { ...options, method: "POST", body }),

  patch: <T>(path: string, body?: unknown, options?: FetchOptions) =>
    apiFetch<T>(path, { ...options, method: "PATCH", body }),

  put: <T>(path: string, body?: unknown, options?: FetchOptions) =>
    apiFetch<T>(path, { ...options, method: "PUT", body }),

  delete: <T>(path: string, options?: FetchOptions) =>
    apiFetch<T>(path, { ...options, method: "DELETE" }),
};

export default api;
