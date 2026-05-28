import { InfoBadge } from "../../design/components/badges/Badge";

export function EvalMetricGrid({
  metrics,
}: {
  metrics: Record<string, unknown>;
}) {
  const allKeys = Object.keys(metrics);

  function formatValue(value: unknown): string {
    if (typeof value === "boolean") {
      return value ? "true" : "false";
    }
    if (typeof value === "number") {
      return String(value);
    }
    if (typeof value === "object" && value !== null) {
      return JSON.stringify(value, null, 2);
    }
    return String(value ?? "");
  }

  function getUnit(key: string): string | undefined {
    const k = key.toLowerCase();
    if (k.endsWith("_ms") || k.includes("ms") || k.includes("latency")) {
      return "ms";
    }
    if (k.endsWith("_rate") || k.endsWith("_pct") || k.includes("percentage")) {
      return "%";
    }
    if (k.endsWith("_sec") || k.includes("seconds")) {
      return "s";
    }
    return undefined;
  }

  function isLowerIsBetter(key: string): boolean {
    const k = key.toLowerCase();
    return (
      k.includes("latency") ||
      k.includes("duration") ||
      k.includes("time") ||
      k.includes("error") ||
      k.includes("fail") ||
      k.includes("fabrication") ||
      k.includes("divergence") ||
      k.includes("cost")
    );
  }

  function renderPassFailBadge(key: string, value: unknown) {
    const isBool = typeof value === "boolean";
    const k = key.toLowerCase();
    const isPassKey = k.includes("pass") || k.includes("success") || k === "passed";

    if (isBool && isPassKey) {
      if (value === true) {
        return (
          <InfoBadge
            label="Passed"
            colorToken="--color-state-verified"
            meaning="Metric passed the verification criteria."
            adr="ADR-0160 / ADR-0162"
            evidence="Metric value indicates success."
          />
        );
      } else {
        return (
          <InfoBadge
            label="Failed"
            colorToken="--color-state-contradicted"
            meaning="Metric failed the verification criteria."
            adr="ADR-0160 / ADR-0162"
            evidence="Metric value indicates failure."
          />
        );
      }
    }
    return null;
  }

  // Find pairs
  const pairedKeys = new Set<string>();
  const pairs: Array<{
    key: string;
    actual: unknown;
    target: unknown;
  }> = [];

  // 1. Group "passed" and "total"
  if (allKeys.includes("passed") && allKeys.includes("total")) {
    pairs.push({
      key: "passed",
      actual: metrics["passed"],
      target: metrics["total"],
    });
    pairedKeys.add("passed");
    pairedKeys.add("total");
  }

  // 2. Group "X" and "X_target" or "target_X"
  allKeys.forEach((k) => {
    if (pairedKeys.has(k)) return;

    if (k.endsWith("_target")) {
      const baseKey = k.slice(0, -7);
      if (allKeys.includes(baseKey)) {
        pairs.push({
          key: baseKey,
          actual: metrics[baseKey],
          target: metrics[k],
        });
        pairedKeys.add(baseKey);
        pairedKeys.add(k);
      }
    } else if (k.startsWith("target_")) {
      const baseKey = k.slice(7);
      if (allKeys.includes(baseKey)) {
        pairs.push({
          key: baseKey,
          actual: metrics[baseKey],
          target: metrics[k],
        });
        pairedKeys.add(baseKey);
        pairedKeys.add(k);
      }
    }
  });

  // 3. Remaining singles
  const singles: Array<{ key: string; value: unknown }> = [];
  allKeys.forEach((k) => {
    if (!pairedKeys.has(k)) {
      singles.push({ key: k, value: metrics[k] });
    }
  });

  interface DisplayMetric {
    key: string;
    isPair: boolean;
    actual: unknown;
    target?: unknown;
    value?: unknown;
  }

  const list: DisplayMetric[] = [
    ...pairs.map((p) => ({ key: p.key, isPair: true, actual: p.actual, target: p.target })),
    ...singles.map((s) => ({ key: s.key, isPair: false, actual: s.value, value: s.value })),
  ];

  // Sort lexicographically
  list.sort((a, b) => a.key.localeCompare(b.key));

  return (
    <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3" data-testid="eval-metric-grid">
      {list.map((item) => {
        const key = item.key;
        const unit = getUnit(key);

        if (item.isPair) {
          const actualVal = item.actual;
          const targetVal = item.target;
          const badge = renderPassFailBadge(key, actualVal);

          const actualNum = Number(actualVal);
          const targetNum = Number(targetVal);
          const hasNumericValues = !isNaN(actualNum) && !isNaN(targetNum);
          const isFailing =
            hasNumericValues &&
            (isLowerIsBetter(key) ? actualNum > targetNum : actualNum < targetNum);

          const formattedActual = formatValue(actualVal);
          const formattedTarget = formatValue(targetVal);

          return (
            <div
              key={key}
              className="flex flex-col justify-between rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-3 shadow-sm"
              data-testid="metric-card"
            >
              <div>
                <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider truncate" title={key}>
                  {key.replaceAll("_", " ")}
                </div>
                <div className="mt-1 font-mono text-sm font-semibold text-right tabular-nums">
                  <span
                    className={
                      isFailing
                        ? "text-[var(--color-state-contradicted)] font-bold"
                        : "text-[var(--color-text-primary)]"
                    }
                  >
                    {formattedActual}
                  </span>
                  <span className="text-[var(--color-text-muted)] mx-1">/</span>
                  <span className="text-[var(--color-text-secondary)] font-normal">
                    {formattedTarget}
                  </span>
                  {unit && <span className="ml-1 text-xs text-[var(--color-text-muted)] font-sans font-normal">{unit}</span>}
                </div>
              </div>
              {badge && <div className="mt-2 flex justify-start">{badge}</div>}
            </div>
          );
        } else {
          const val = item.value;
          const badge = renderPassFailBadge(key, val);
          const formatted = formatValue(val);
          const isObj = typeof val === "object" && val !== null;
          const isNum = typeof val === "number";

          return (
            <div
              key={key}
              className="flex flex-col justify-between rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-3 shadow-sm"
              data-testid="metric-card"
            >
              <div>
                <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider truncate" title={key}>
                  {key.replaceAll("_", " ")}
                </div>
                <div
                  className={`mt-1 font-mono text-sm font-semibold text-[var(--color-text-primary)] ${
                    isNum ? "text-right tabular-nums" : ""
                  } ${isObj ? "whitespace-pre overflow-x-auto text-[10px] bg-[var(--color-surface-inset)] p-1.5 rounded" : ""}`}
                >
                  {formatted}
                  {unit && <span className="ml-1 text-xs text-[var(--color-text-muted)] font-sans font-normal">{unit}</span>}
                </div>
              </div>
              {badge && <div className="mt-2 flex justify-start">{badge}</div>}
            </div>
          );
        }
      })}
    </div>
  );
}
