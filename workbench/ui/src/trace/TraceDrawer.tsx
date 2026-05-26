import React from 'react'
import './trace.css'

export type TraceDetail = {
  turn_id: string
  surface: string
  articulation_surface: string | null
  walk_surface: string | null
  trace_hash: string | null
  replay_digest: string | null
  grounding_source: string | null
  proposal_refs: string[]
  candidate_refs: string[]
  admissibility: {
    rejected_attempts: number | null
    exhausted: boolean | null
  }
  raw: unknown | null
}

type Props = {
  trace: TraceDetail | null
}

function value(value: string | number | boolean | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}

export function TraceDrawer({ trace }: Props): JSX.Element {
  return (
    <aside className="trace-drawer">
      <div className="trace-header">
        <div>
          <div className="trace-eyebrow">Live Trace Observatory</div>
          <h3>Layered Cognition Surface</h3>
        </div>
        <div className="trace-badge">READ ONLY</div>
      </div>

      {!trace ? (
        <div className="trace-empty">No trace selected.</div>
      ) : (
        <div className="trace-stack">
          <section className="trace-card trace-card-primary">
            <div className="trace-card-title">Proposition Surface</div>
            <p>{trace.surface || 'Trace storage not yet wired to a live turn.'}</p>
          </section>

          <section className="trace-card-grid">
            <div className="trace-card">
              <div className="trace-card-title">Replay</div>
              <dl>
                <dt>Trace Hash</dt><dd>{value(trace.trace_hash)}</dd>
                <dt>Replay Digest</dt><dd>{value(trace.replay_digest)}</dd>
              </dl>
            </div>
            <div className="trace-card">
              <div className="trace-card-title">Grounding</div>
              <dl>
                <dt>Source</dt><dd>{value(trace.grounding_source)}</dd>
                <dt>Turn</dt><dd>{trace.turn_id}</dd>
              </dl>
            </div>
          </section>

          <section className="trace-card-grid">
            <div className="trace-card">
              <div className="trace-card-title">Admissibility</div>
              <dl>
                <dt>Rejected</dt><dd>{value(trace.admissibility.rejected_attempts)}</dd>
                <dt>Exhausted</dt><dd>{value(trace.admissibility.exhausted)}</dd>
              </dl>
            </div>
            <div className="trace-card">
              <div className="trace-card-title">References</div>
              <dl>
                <dt>Proposals</dt><dd>{trace.proposal_refs.length}</dd>
                <dt>Candidates</dt><dd>{trace.candidate_refs.length}</dd>
              </dl>
            </div>
          </section>

          <section className="trace-card">
            <div className="trace-card-title">Layered Surfaces</div>
            <dl>
              <dt>Articulation</dt><dd>{value(trace.articulation_surface)}</dd>
              <dt>Walk</dt><dd>{value(trace.walk_surface)}</dd>
            </dl>
          </section>
        </div>
      )}
    </aside>
  )
}
