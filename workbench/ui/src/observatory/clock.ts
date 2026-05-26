import { ObservatoryFrame } from './types'

const INTRO_DURATION_MS = 14000

export class ObservatoryClock {
  private readonly startedAt: number

  constructor(startedAt: number = performance.now()) {
    this.startedAt = startedAt
  }

  frame(now: number = performance.now()): ObservatoryFrame {
    const elapsedMs = Math.max(0, now - this.startedAt)
    const normalized = Math.min(1, elapsedMs / INTRO_DURATION_MS)

    let phase: ObservatoryFrame['phase'] = 'void'

    if (normalized >= 0.2) {
      phase = 'emergence'
    }
    if (normalized >= 0.45) {
      phase = 'alignment'
    }
    if (normalized >= 0.7) {
      phase = 'surface_reveal'
    }
    if (normalized >= 0.9) {
      phase = 'identity'
    }

    return {
      elapsedMs,
      normalized,
      phase,
    }
  }
}
