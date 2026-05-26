import React from 'react'
import ReactDOM from 'react-dom/client'
import './styles.css'
import {
  ArtifactRef,
  EvalLaneSummary,
  ProposalSummary,
  ReplayComparison,
  RuntimeStatus,
  getRuntimeStatus,
  listArtifacts,
  listEvalLanes,
  listProposals,
  login,
  logout,
  me,
  replayArtifact,
} from './api'
import { ChatSurface } from './chat/ChatSurface'
import { ObservatoryIntro } from './observatory/ObservatoryIntro'

type Section = 'Chat' | 'Replay' | 'Proposals' | 'Evals' | 'Artifacts' | 'Runtime'

function RuntimePanel({ runtime }: { runtime: RuntimeStatus | null }): JSX.Element {
  if (!runtime) return <div className="panel-card">Loading runtime status...</div>
  return (
    <div className="panel-card stack-gap">
      <h2>Runtime Status</h2>
      <div className="kv-grid">
        <div>Backend</div><div>{runtime.backend}</div>
        <div>Git Revision</div><div>{runtime.git_revision}</div>
        <div>Checkpoint Revision</div><div>{runtime.checkpoint_revision}</div>
        <div>Engine State</div><div>{runtime.engine_state_present ? 'Present' : 'Missing'}</div>
        <div>Mutation Mode</div><div>{runtime.mutation_mode}</div>
      </div>
    </div>
  )
}

function ProposalPanel({ proposals }: { proposals: ProposalSummary[] }): JSX.Element {
  return (
    <div className="panel-card stack-gap">
      <h2>Proposal Queue</h2>
      <table className="data-table">
        <thead><tr><th>ID</th><th>State</th><th>Source</th><th>Replay</th></tr></thead>
        <tbody>{proposals.map((p) => <tr key={p.proposal_id}><td>{p.proposal_id}</td><td>{p.state}</td><td>{p.source_kind}</td><td>{p.replay_equivalent === true ? 'Equivalent' : 'Unknown'}</td></tr>)}</tbody>
      </table>
    </div>
  )
}

function EvalPanel({ lanes }: { lanes: EvalLaneSummary[] }): JSX.Element {
  return (
    <div className="panel-card stack-gap">
      <h2>Eval Lanes</h2>
      <table className="data-table">
        <thead><tr><th>Lane</th><th>Versions</th><th>Read Only</th></tr></thead>
        <tbody>{lanes.map((lane) => <tr key={lane.lane}><td>{lane.lane}</td><td>{lane.versions.join(', ')}</td><td>{lane.read_only ? 'Yes' : 'No'}</td></tr>)}</tbody>
      </table>
    </div>
  )
}

function ArtifactPanel({ artifacts }: { artifacts: ArtifactRef[] }): JSX.Element {
  return (
    <div className="panel-card stack-gap">
      <h2>Artifacts</h2>
      <table className="data-table">
        <thead><tr><th>Kind</th><th>Path</th></tr></thead>
        <tbody>{artifacts.map((a) => <tr key={a.artifact_id}><td>{a.kind}</td><td>{a.path}</td></tr>)}</tbody>
      </table>
    </div>
  )
}

function ReplayPanel({ replay }: { replay: ReplayComparison | null }): JSX.Element {
  return (
    <div className="panel-card stack-gap">
      <h2>Replay Theater</h2>
      {replay ? <div className="kv-grid"><div>Artifact</div><div>{replay.artifact_id}</div><div>Equivalent</div><div>{replay.equivalent ? 'Yes' : 'No'}</div><div>Original Hash</div><div>{replay.original_hash}</div><div>Replay Hash</div><div>{replay.replay_hash}</div></div> : <div>No replay selected.</div>}
    </div>
  )
}

function App(): JSX.Element {
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [authenticated, setAuthenticated] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [runtime, setRuntime] = React.useState<RuntimeStatus | null>(null)
  const [proposals, setProposals] = React.useState<ProposalSummary[]>([])
  const [lanes, setLanes] = React.useState<EvalLaneSummary[]>([])
  const [artifacts, setArtifacts] = React.useState<ArtifactRef[]>([])
  const [replay, setReplay] = React.useState<ReplayComparison | null>(null)
  const [section, setSection] = React.useState<Section>('Runtime')

  React.useEffect(() => { me().then(() => setAuthenticated(true)).catch(() => undefined) }, [])

  React.useEffect(() => {
    if (!authenticated) return
    void getRuntimeStatus().then(setRuntime)
    void listProposals().then(setProposals)
    void listEvalLanes().then(setLanes)
    void listArtifacts().then(async (items) => {
      setArtifacts(items)
      if (items.length > 0) {
        try { setReplay(await replayArtifact(items[0].artifact_id)) } catch {}
      }
    })
  }, [authenticated])

  async function submit(event: React.FormEvent): Promise<void> {
    event.preventDefault()
    setError(null)
    try { await login(email, password); setAuthenticated(true) } catch (err) {
      setAuthenticated(false)
      setError(err instanceof Error ? err.message : 'Authentication failed.')
    }
  }

  async function handleLogout(): Promise<void> { await logout(); setAuthenticated(false) }

  if (!authenticated) {
    return (
      <div className="login-shell">
        <ObservatoryIntro />
        <div className="login-card">
          <div className="eyebrow">Deterministic Cognition Observatory</div>
          <h1>CORE Workbench</h1>
          <p className="subtle">Replay-native cognition instrumentation environment.</p>
          <form onSubmit={submit}>
            <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" /></label>
            <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></label>
            {error ? <div className="error">{error}</div> : null}
            <button type="submit">Enter Workbench</button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <header className="topbar"><div className="brand">CORE Workbench</div><div className="topbar-right"><div className="runtime-pill">READ ONLY</div><button className="ghost-button" onClick={() => void handleLogout()}>Logout</button></div></header>
      <div className="body-shell">
        <nav className="sidebar">{(['Chat', 'Replay', 'Proposals', 'Evals', 'Artifacts', 'Runtime'] as Section[]).map((item) => <button key={item} onClick={() => setSection(item)}>{item}</button>)}</nav>
        <main className="main-panel">
          {section === 'Runtime' ? <RuntimePanel runtime={runtime} /> : null}
          {section === 'Proposals' ? <ProposalPanel proposals={proposals} /> : null}
          {section === 'Evals' ? <EvalPanel lanes={lanes} /> : null}
          {section === 'Artifacts' ? <ArtifactPanel artifacts={artifacts} /> : null}
          {section === 'Replay' ? <ReplayPanel replay={replay} /> : null}
          {section === 'Chat' ? <ChatSurface /> : null}
        </main>
      </div>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(<React.StrictMode><App /></React.StrictMode>)
