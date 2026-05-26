import { Button } from "../primitives/Button";

export function EmptyState({
  statement,
  nextAction,
}: {
  statement: string;
  nextAction: string;
}) {
  return (
    <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
      <p className="m-0 text-sm text-[var(--color-text-primary)]">{statement}</p>
      <Button className="mt-3" variant="quiet" type="button">
        {nextAction}
      </Button>
    </section>
  );
}
