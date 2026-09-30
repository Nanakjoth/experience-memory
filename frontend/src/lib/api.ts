/**
 * Origin the API is called on.
 *
 * Empty (the default) means same-origin: requests go to relative `/api/*` paths.
 * That is correct for `npm run dev`, where the Vite proxy forwards /api to the
 * backend, and for production when the API is served from the same host behind
 * a reverse proxy.
 *
 * Set `VITE_API_BASE_URL` at build time to call a different origin:
 *   VITE_API_BASE_URL=https://api.example.com npm run build
 *
 * Vite inlines env vars at build time, so changing it requires a rebuild.
 */
const BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(status: number, message: string, payload: unknown) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

type Query = Record<string, string | number | boolean | undefined | null>;

function qs(params?: Query): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }
  if (!response.ok) {
    const detail = (payload as { detail?: unknown })?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail
              .map((d) => (d as { msg?: string }).msg ?? JSON.stringify(d))
              .join("; ")
          : detail && typeof detail === "object"
            ? ((detail as { message?: string }).message ?? JSON.stringify(detail))
            : `Request failed (${response.status})`;
    throw new ApiError(response.status, message, payload);
  }
  return payload as T;
}

export const api = {
  get: <T>(path: string, params?: Query) => request<T>(`${path}${qs(params)}`),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),
};
