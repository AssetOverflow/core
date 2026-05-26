import React from 'react'
import { readTrace, TraceDetail } from '../api'
import { TraceDrawer } from '../trace/TraceDrawer'

export function ChatSurface(): JSX.Element {
  const [trace, setTrace] = React.useState<TraceDetail | null>(null)
  const [traceId, setTraceId] = React.useState('bootstrap')
  const [error, setError] = React.useState<string | null>(null)

  async function loadTrace(turnId: string): Promise<void> {
    setError(null)
    try {
      setTrace(await readTrace(turnId))
    } catch (err) {
      setTrace(null)
      setError(err instanceof Error ? err.message : 'Unable to load trace.')
    }
  }

  React.useEffect(() => {
    void loadTrace(traceId)
  }, [])

  return (
    <div className="chat-observatory-grid">
      <div className="panel-card stack-gap">
        <h2>Chat Surface</h2>
        <p>
          Live runtime turn execution attaches here next. The trace drawer is
          already wired through the authenticated observability contract.
        </p>

        <label>
          Trace / turn id
          <input
            value={traceId}
            onChange={(event) => setTraceId(event.target.value)}
            placeholder="bootstrap"
          />
        </label>

        <button className="ghost-button" onClick={() => void loadTrace(traceId)}>
          Inspect Trace
        </button>

        {error ? <div className="error">{error}</div> : null}
        <div className="runtime-pill">TRACE CONTRACT ACTIVE</div>
      </div>

      <TraceDrawer trace={trace} />
    </div>
  )
}
