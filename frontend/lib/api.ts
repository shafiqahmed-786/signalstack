const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiClientError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

interface ApiErrorResponse {
  error?: {
    code?: string;
    message?: string;
  };
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { token?: string } = {}
): Promise<T> {
  const { token, ...fetchOptions } = options;

  const isFormData =
    typeof FormData !== "undefined" &&
    fetchOptions.body instanceof FormData;

  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((fetchOptions.headers as Record<string, string>) ?? {}),
  };

  const response = await fetch(`${API_BASE}${path}`, {
    ...fetchOptions,
    headers,
  });

  if (!response.ok) {
    let errorBody: ApiErrorResponse = {};

    try {
      errorBody = await response.json();
    } catch {
      // Response body may be empty or non-JSON
    }

    throw new ApiClientError(
      errorBody.error?.code ?? "UNKNOWN_ERROR",
      errorBody.error?.message ?? `HTTP ${response.status}`,
      response.status
    );
  }

  // Handle empty responses safely
  if (response.status === 204) {
    return undefined as T;
  }

  // Handle non-JSON responses safely
  const contentType = response.headers.get("content-type");

  if (!contentType?.includes("application/json")) {
    return (await response.text()) as T;
  }

  return response.json() as Promise<T>;
}

export function getApiBase(): string {
  return API_BASE;
}