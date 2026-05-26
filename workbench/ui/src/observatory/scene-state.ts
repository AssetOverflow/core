import { ObservatoryClock } from './clock'
import { ObservatoryFrame, TopologyEdge, TopologyNode } from './types'

export type IntroSceneState = {
  frame: ObservatoryFrame
  phase: string
  nodes: TopologyNode[]
  edges: TopologyEdge[]
  convergence: number
  synchronization: number
  reveal: number
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value))
}

function ramp(value: number, start: number, end: number): number {
  if (end <= start) return value >= end ? 1 : 0
  return clamp01((value - start) / (end - start))
}

export function createIntroSceneState(
  clock: ObservatoryClock,
  now?: number,
): IntroSceneState {
  const frame = clock.frame(now)
  const convergence = ramp(frame.normalized, 0.28, 0.72)
  const synchronization = ramp(frame.normalized, 0.42, 0.86)
  const reveal = ramp(frame.normalized, 0.68, 0.95)

  const nodes: TopologyNode[] = [
    {
      id: 'origin',
      kind: 'prompt',
      x: 0,
      y: 0,
      z: 0,
      stabilization:
        synchronization > 0.88 ? 'stabilized' : convergence > 0.48 ? 'aligning' : 'emergent',
    },
    {
      id: 'surface',
      kind: 'proposition',
      x: 140 - convergence * 18,
      y: 40 - convergence * 8,
      z: 12 + reveal * 26,
      stabilization:
        reveal > 0.72 ? 'synchronized' : convergence > 0.3 ? 'aligning' : 'emergent',
    },
    {
      id: 'replay',
      kind: 'replay_anchor',
      x: -120 + synchronization * 16,
      y: -32 + synchronization * 10,
      z: 8 + synchronization * 20,
      stabilization:
        synchronization > 0.65 ? 'synchronized' : convergence > 0.2 ? 'aligning' : 'emergent',
    },
    {
      id: 'trace',
      kind: 'trace',
      x: -16,
      y: 92 - reveal * 20,
      z: 16 + reveal * 18,
      stabilization:
        reveal > 0.58 ? 'synchronized' : 'emergent',
    },
  ]

  const edges: TopologyEdge[] = [
    {
      from: 'origin',
      to: 'surface',
      layer: 'surface',
      stabilization: convergence > 0.45 ? 'synchronized' : 'aligning',
    },
    {
      from: 'origin',
      to: 'replay',
      layer: 'replay',
      stabilization: synchronization > 0.55 ? 'synchronized' : 'aligning',
    },
    {
      from: 'origin',
      to: 'trace',
      layer: 'trace',
      stabilization: reveal > 0.5 ? 'synchronized' : 'emergent',
    },
  ]

  return {
    frame,
    phase: frame.phase,
    nodes,
    edges,
    convergence,
    synchronization,
    reveal,
  }
}
