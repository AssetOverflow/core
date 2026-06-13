import { Link } from "react-router-dom";
import { useServingMetrics } from "../api/queries";

// The project's thesis, made a constant presence: the live serving outcome
// with the wrong count load-bearing. It is a MIRROR of /serving/metrics —
// it shows whatever the committed reports say, never a hard-coded zero, and
// says so honestly when the metrics can't be read.
export function WrongZeroFrame() {
  const { data, isLoading, isError } = useServingMetrics();

  const base =
    "shrink-0 rounded-full border px-3 py-1 text-xs tabular-nums focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]";

  if (isLoading) {
    return (
      <span
        className={`${base} border-[var(--color-border-subtle)] text-[var(--color-text-secondary)]`}
        aria-live="polite"
      >
        wrong=0 …
      </span>
    );
  }

  if (isError || !data || data.length === 0) {
    return (
      <span
        className={`${base} border-[var(--color-border-subtle)] text-[var(--color-text-muted)]`}
        aria-live="polite"
        title="serving metrics could not be read"
      >
        wrong=0: metrics unavailable
      </span>
    );
  }

  const correct = data.reduce((sum, m) => sum + m.correct, 0);
  const refused = data.reduce((sum, m) => sum + m.refused, 0);
  const wrong = data.reduce((sum, m) => sum + m.wrong, 0);

  return (
    <Link
      to="/calibration"
      className={`${base} border-[var(--color-border-subtle)] bg-[var(--color-surface-sunken)] no-underline text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]`}
      aria-label={`Serving outcome: ${correct} correct, ${refused} refused, ${wrong} wrong. View calibration.`}
    >
      <span>{correct} correct · {refused} refused · </span>
      <span
        className={
          wrong > 0
            ? "font-semibold text-[var(--color-state-contradicted)]"
            : "font-semibold text-[var(--color-state-verified)]"
        }
      >
        {wrong} wrong
      </span>
    </Link>
  );
}
