export type StabilizationState =
  | 'emergent'
  | 'unstable'
  | 'aligning'
  | 'synchronized'
  | 'stabilized'
  | 'divergent'
  | 'collapsed'

export type ObservatoryLayer =
  | 'surface'
  | 'trace'
  | 'topology'
  | 'telemetry'
  | 'replay'

export type TopologyNodeKind =
  | 'prompt'
  | 'proposition'
  | 'trace'
  | 'replay_anchor'
  | 'proposal'
  | 'eval'

export type TopologyNode = {
  id: string
  kind: TopologyNodeKind
  x: number
  y: number
  z: number
  stabilization: StabilizationState
}

export type TopologyEdge = {
  from: string
  to: string
  layer: ObservatoryLayer
  stabilization: StabilizationState
}

export type ObservatoryFrame = {
  elapsedMs: number
  normalized: number
  phase: 'void' | 'emergence' | 'alignment' | 'surface_reveal' | 'identity'
}
