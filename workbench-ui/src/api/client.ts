import type {
  ApiResponse,
  ErrorCode,
  EvalLaneSummary,
  EvalRunRequest,
  EvalRunResult,
  ArtifactRef,
  ArtifactDetail,
  ReplayComparison,
} from "../types/api";

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

export async function fetchEvalLanes(): Promise<EvalLaneSummary[]> {
  return apiFetch<EvalLaneSummary[]>("/evals");
}

export async function runEvalLane(req: EvalRunRequest): Promise<EvalRunResult> {
  if (req.split === "holdout") {
    const hasConfig = typeof window !== "undefined" && (window as any).sealedEvalConfig === true;
    if (!hasConfig) {
      throw new WorkbenchApiError(
        "client_refused_sealed_holdout",
        "Holdout runs require sealed-eval config — use CLI"
      );
    }
  }

  const lanes = await fetchEvalLanes();
  const lane = lanes.find((l) => l.lane === req.lane);
  if (!lane) {
    throw new WorkbenchApiError("not_found", `Eval lane not found: ${req.lane}`);
  }
  if (!lane.read_only) {
    throw new WorkbenchApiError("client_refused_unsafe_lane", "API run disabled — use CLI");
  }

  return apiFetch<EvalRunResult>("/evals/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function fetchArtifacts(): Promise<ArtifactRef[]> {
  const data = await apiFetch<{ items: ArtifactRef[] }>("/artifacts");
  return data.items;
}

export async function fetchArtifactDetail(artifactId: string): Promise<ArtifactDetail> {
  return apiFetch<ArtifactDetail>(`/artifacts/${artifactId}`);
}

export async function fetchReplayComparison(artifactId: string): Promise<ReplayComparison> {
  return apiFetch<ReplayComparison>(`/replay/${artifactId}`);
}
