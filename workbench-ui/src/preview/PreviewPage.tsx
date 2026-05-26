import { useEffect, useState } from "react";
import { StableJsonViewer } from "../design/components/StableJsonViewer";
import {
  EpistemicState,
  EpistemicStateBadge,
  GroundingSource,
  GroundingSourceBadge,
  NormativeClearance,
  NormativeClearanceBadge,
  ReviewState,
  ReviewStateBadge,
  TraceHashBadge,
} from "../design/components/badges";
import { Button } from "../design/components/primitives/Button";
import { CommandPalette } from "../design/components/primitives/CommandPalette";
import { EmptyState } from "../design/components/states/EmptyState";
import { ErrorState } from "../design/components/states/ErrorState";
import { LoadingState } from "../design/components/states/LoadingState";

export function PreviewPage() {
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen(true);
      }
      if (event.key === "Escape") setPaletteOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <main className="mx-auto grid max-w-6xl gap-8 px-5 py-8">
      <header>
        <h1 className="m-0 text-xl font-semibold">CORE Workbench Design System v1</h1>
        <p className="mt-2 max-w-3xl text-sm text-[var(--color-text-secondary)]">
          Static Branch 1 substrate preview. No backend, no API client, no runtime mutation surface.
        </p>
      </header>

      <section aria-labelledby="primitive-heading" className="grid gap-3">
        <h2 id="primitive-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">Primitives</h2>
        <div className="flex flex-wrap gap-2">
          <Button type="button">Primary action</Button>
          <Button type="button" variant="quiet">Quiet action</Button>
        </div>
      </section>

      <section aria-labelledby="badge-heading" className="grid gap-3">
        <h2 id="badge-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">Badges</h2>
        <div className="flex flex-wrap gap-2">
          {Object.values(EpistemicState).map((value) => <EpistemicStateBadge key={value} value={value} />)}
          {Object.values(NormativeClearance).map((value) => <NormativeClearanceBadge key={value} value={value} />)}
          {Object.values(ReviewState).map((value) => <ReviewStateBadge key={value} value={value} />)}
          {Object.values(GroundingSource).map((value) => <GroundingSourceBadge key={value} value={value} />)}
          <TraceHashBadge value="4f80f7e12c7e8ca1f1a277f8ccecf2846f08bb9d8f22354e6d3f30eb7fb34c80" />
        </div>
      </section>

      <section aria-labelledby="state-heading" className="grid gap-3">
        <h2 id="state-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">States</h2>
        <div className="grid gap-3 md:grid-cols-3">
          <EmptyState statement="No artifact selected." nextAction="Select an artifact." />
          <ErrorState
            whatFailed="Preview artifact failed validation."
            mutationStatus="No mutation attempted."
            reproducer="cd workbench-ui && pnpm test"
            retrySafety="Retry reads static fixtures only."
          />
          <LoadingState label="Loading preview fixture." />
        </div>
      </section>

      <section aria-labelledby="json-heading" className="grid gap-3">
        <h2 id="json-heading" className="text-sm font-semibold text-[var(--color-text-secondary)]">Stable JSON Viewer</h2>
        <StableJsonViewer source='{"trace_hash":"4f80f7e12c7e","scenes":[{"detail":{"object":"lens","epsilon":1e-6}}],"state":"decoded"}' />
      </section>

      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </main>
  );
}
