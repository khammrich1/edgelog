const API_BASE = "/api";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  skipAuthRetry?: boolean;
};

let accessToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function onSessionExpired(callback: () => void): void {
  onUnauthorized = callback;
}

async function rawRequest(path: string, options: RequestOptions = {}): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
}

/**
 * Performs a request; on a 401 it attempts one silent refresh (the refresh token
 * lives in an HttpOnly cookie) before retrying, so callers never see transient
 * access-token expiry as an error.
 */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response = await rawRequest(path, options);

  if (response.status === 401 && !options.skipAuthRetry) {
    const refreshed = await refreshSession();
    if (refreshed) {
      response = await rawRequest(path, options);
    } else {
      onUnauthorized?.();
    }
  }

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new ApiError(response.status, detail?.detail ?? response.statusText);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function refreshSession(): Promise<boolean> {
  const response = await rawRequest("/auth/refresh", { method: "POST", skipAuthRetry: true });
  if (!response.ok) {
    setAccessToken(null);
    return false;
  }
  const data = await response.json();
  setAccessToken(data.access_token);
  return true;
}

export { refreshSession };
