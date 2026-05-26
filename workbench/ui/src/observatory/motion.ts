export function converge(current: number, target: number, factor = 0.08): number {
  return current + (target - current) * factor
}

export function stabilize(value: number, threshold = 0.001): number {
  return Math.abs(value) < threshold ? 0 : value
}

export function synchronize(a: number, b: number, blend = 0.5): number {
  return a * (1 - blend) + b * blend
}

export function propagate(origin: number, velocity: number, deltaMs: number): number {
  return origin + velocity * (deltaMs / 1000)
}

export function damp(current: number, damping = 0.92): number {
  return current * damping
}

export function bind(a: number, b: number): number {
  return (a + b) / 2
}
