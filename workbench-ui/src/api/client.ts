import type { ApiResponse, ErrorCode } from "../types/api";

export class WorkbenchApiError extends Error {
  constructor(
    public readonly code: ErrorCode,
    message: string,
  ) {
    super(message);
    this.name = "WorkbenchApiError";
  }
}

export const API_URL: string =
  import.meta.env.VITE_WORKBENCH_API_URL ?? "http://127.0.0.1:8765";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const res = await fetch(`${API_URL}${path}`, { ...init, signal: controller.signal });
    const json: ApiResponse<T> = await res.json();
    if (!json.ok) {
      throw new WorkbenchApiError(json.error.code, json.error.message);
    }
    return json.data;
  } finally {
    clearTimeout(timeout);
  }
}
