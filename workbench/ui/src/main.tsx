import React from 'react'
import ReactDOM from 'react-dom/client'
import './styles.css'

const API_BASE = 'http://127.0.0.1:8765'

async function login(email: string, password: string): Promise<boolean> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  })
  return response.ok
}

function App(): JSX.Element {
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [authenticated, setAuthenticated] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  async function submit(event: React.FormEvent): Promise<void> {
    event.preventDefault()
    setError(null)
    const ok = await login(email, password)
    if (!ok) {
      setAuthenticated(false)
      setError('Authentication failed.')
      return
    }
    setAuthenticated(true)
  }

  if (!authenticated) {
    return (
      <div className="login-shell">
        <div className="login-card">
          <h1>CORE Workbench</h1>
          <p className="subtle">
            Deterministic cognition observability and replay workstation.
          </p>
          <form onSubmit={submit}>
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </label>
            {error ? <div className="error">{error}</div> : null}
            <button type="submit">Enter Workbench</button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">CORE Workbench</div>
        <div className="runtime-pill">READ ONLY</div>
      </header>

      <div className="body-shell">
        <nav className="sidebar">
          <button>Chat</button>
          <button>Replay</button>
          <button>Proposals</button>
          <button>Evals</button>
          <button>Artifacts</button>
          <button>Runtime</button>
        </nav>

        <main className="main-panel">
          <div className="panel-card">
            <h2>Workbench Initialized</h2>
            <p>
              The operator shell is active. Replay, proposal, eval, and runtime
              surfaces will be connected incrementally.
            </p>
          </div>
        </main>
      </div>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
