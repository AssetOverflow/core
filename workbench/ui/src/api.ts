export const API_BASE = 'http://127.0.0.1:8765'

export type WorkbenchResponse<T> =
  | { ok: true; generated_at: string; data: T }
  | { ok: false; generated_at: string; error: { code: string; message: string; detail?: unknown } }

export type RuntimeStatus = {
  backend: string
  git_revision: string
  engine_state_present: boolean
  checkpoint_revision: string
  revision_warning: boolean
  active_session_id: string | null
  mutation_mode: 'read_only' | 'runtime_turn'
}

export type ProposalSummary = {
  proposal_id: string
  state: string
  source_kind: string
  replay_equivalent: boolean | null
  created_at: string | null
  downstream_effect: 'unknown' | 'none' | 'observed'
}

export type EvalLaneSummary = {
  lane: string
  versions: string[]
  read_only: boolean
  description: string | null
}

export type ArtifactRef = {
  artifact_id: string
  kind: string
  path: string
  digest: string | null
  created_at: string | null
}

export type ReplayComparison = {
  artifact_id: string
  original_hash: string | null
  replay_hash: string | null
  equivalent: boolean
  divergences: Array<{ path: string; original: unknown; replay: unknown; severity: 'info' | 'warning' | 'failure' }>
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as WorkbenchResponse<T>
  if (!payload.ok) {
    throw new Error(payload.error.message)
  }
  return payload.data
}

export async function login(email: string, password: string): Promise<{ email: string }> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  return parseResponse<{ email: string }>(response)
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE}/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  })
}

export async function me(): Promise<{ email: string }> {
  const response = await fetch(`${API_BASE}/auth/me`, { credentials: 'include' })
  return parseResponse<{ email: string }>(response)
}

export async function getRuntimeStatus(): Promise<RuntimeStatus> {
  const response = await fetch(`${API_BASE}/runtime/status`, { credentials: 'include' })
  return parseResponse<RuntimeStatus>(response)
}

export async function listProposals(): Promise<ProposalSummary[]> {
  const response = await fetch(`${API_BASE}/proposals`, { credentials: 'include' })
  const data = await parseResponse<{ items: ProposalSummary[] }>(response)
  return data.items
}

export async function listEvalLanes(): Promise<EvalLaneSummary[]> {
  const response = await fetch(`${API_BASE}/evals`, { credentials: 'include' })
  const data = await parseResponse<{ lanes: EvalLaneSummary[] }>(response)
  return data.lanes
}

export async function listArtifacts(): Promise<ArtifactRef[]> {
  const response = await fetch(`${API_BASE}/artifacts?limit=50`, { credentials: 'include' })
  const data = await parseResponse<{ items: ArtifactRef[] }>(response)
  return data.items
}

export async function replayArtifact(artifactId: string): Promise<ReplayComparison> {
  const response = await fetch(`${API_BASE}/replay/${encodeURIComponent(artifactId)}`, { credentials: 'include' })
  return parseResponse<ReplayComparison>(response)
}
