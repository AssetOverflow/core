import React from 'react'
import { ObservatoryClock } from './clock'
import { createIntroSceneState } from './scene-state'
import './observatory.css'

export function ObservatoryIntro(): JSX.Element {
  const clockRef = React.useRef(new ObservatoryClock())
  const [now, setNow] = React.useState(() => performance.now())

  React.useEffect(() => {
    let raf = 0

    const tick = (time: number): void => {
      setNow(time)
      raf = requestAnimationFrame(tick)
    }

    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [])

  const state = createIntroSceneState(clockRef.current, now)

  return (
    <div className="observatory-intro" aria-hidden="true">
      <div className="observatory-depth" />
      <svg className="observatory-graph" viewBox="-220 -160 440 320" role="presentation">
        <defs>
          <radialGradient id="nodeGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(196, 220, 255, 0.95)" />
            <stop offset="65%" stopColor="rgba(102, 154, 255, 0.26)" />
            <stop offset="100%" stopColor="rgba(102, 154, 255, 0)" />
          </radialGradient>
        </defs>

        {state.edges.map((edge) => {
          const from = state.nodes.find((node) => node.id === edge.from)
          const to = state.nodes.find((node) => node.id === edge.to)
          if (!from || !to) return null
          return (
            <line
              key={`${edge.from}-${edge.to}`}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              className={`observatory-edge observatory-edge-${edge.layer}`}
            />
          )
        })}

        {state.nodes.map((node) => (
          <g key={node.id} className={`observatory-node observatory-node-${node.stabilization}`}>
            <circle cx={node.x} cy={node.y} r="22" fill="url(#nodeGlow)" />
            <circle cx={node.x} cy={node.y} r="3.5" />
          </g>
        ))}
      </svg>

      <div className={`observatory-phase observatory-phase-${state.phase}`}>
        <span>{state.phase.replace('_', ' ')}</span>
      </div>
    </div>
  )
}
