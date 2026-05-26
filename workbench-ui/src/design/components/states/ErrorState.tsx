export function ErrorState({
  whatFailed,
  mutationStatus,
  reproducer,
  retrySafety,
}: {
  whatFailed: string;
  mutationStatus: string;
  reproducer: string;
  retrySafety: string;
}) {
  return (
    <section className="rounded-lg border border-[var(--color-state-danger-border)] bg-[var(--color-state-danger-bg)] p-4 text-sm text-[var(--color-state-danger-text)]">
      <dl className="m-0 grid gap-2">
        <div>
          <dt className="font-semibold">What failed</dt>
          <dd className="m-0">{whatFailed}</dd>
        </div>
        <div>
          <dt className="font-semibold">Mutation status</dt>
          <dd className="m-0">{mutationStatus}</dd>
        </div>
        <div>
          <dt className="font-semibold">Reproducer</dt>
          <dd className="m-0 font-mono text-xs">{reproducer}</dd>
        </div>
        <div>
          <dt className="font-semibold">Retry safety</dt>
          <dd className="m-0">{retrySafety}</dd>
        </div>
      </dl>
    </section>
  );
}
