import { ObservatoryClock } from './clock'
import { TopologyEdge, TopologyNode } from './types'

export type IntroSceneState = {
  phase: string
  nodes: TopologyNode[]
  edges: TopologyEdge[]
}

export function createIntroSceneState(
  clock: ObservatoryClock,
  now?: number,
): IntroSceneState {
  const frame = clock.frame(now)

  const nodes: TopologyNode[] = [
    {
      id: 'origin',
      kind: 'prompt',
      x: 0,
      y: 0,
      z: 0,
      stabilization:
        frame.phase === 'identity' ? 'stabilized' : 'aligning',
    },
    {
      id: 'surface',
      kind: 'proposition',
      x: 140,
      y: 40,
      z: 12,
      stabilization:
        frame.phase === 'surface_reveal'
          ? 'synchronized'
          : 'emergent',
    },
    {
      id: 'replay',
      kind: 'replay_anchor',
      x: -120,
      y: -32,
      z: 8,
      stabilization:
        frame.phase === 'alignment' ? 'aligning' : 'emergent',
    },
  ]

  const edges: TopologyEdge[] = [
    {
      from: 'origin',
      to: 'surface',
      layer: 'surface',
      stabilization: 'synchronized',
    },
    {
      from: 'origin',
      to: 'replay',
      layer: 'replay',
      stabilization: 'aligning',
    },
  ]

  return {
    phase: frame.phase,
    nodes,
    edges,
  }
}
