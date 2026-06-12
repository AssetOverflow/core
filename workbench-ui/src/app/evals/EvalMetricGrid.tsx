import { InfoBadge } from "../../design/components/badges/Badge";

export function EvalMetricGrid({
  metrics,
}: {
  metrics: Record<string, unknown>;
}) {
  const sortedKeys = Object.keys(metrics).sort();

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

  return (
    <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3" data-testid="eval-metric-grid">
      {sortedKeys.map((key) => {
        const val = metrics[key];
        const unit = getUnit(key);
        const badge = renderPassFailBadge(key, val);
        const formatted = formatValue(val);
        const isObj = typeof val === "object" && val !== null;

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
              <div className={`mt-1 font-mono tabular-nums text-sm font-semibold text-[var(--color-text-primary)] ${isObj ? "whitespace-pre overflow-x-auto text-[10px] bg-[var(--color-surface-inset)] p-1.5 rounded" : ""}`}>
                {formatted}
                {unit && <span className="ml-1 text-xs text-[var(--color-text-muted)] font-sans font-normal">{unit}</span>}
              </div>
            </div>
            {badge && <div className="mt-2 flex justify-start">{badge}</div>}
          </div>
        );
      })}
    </div>
  );
}
