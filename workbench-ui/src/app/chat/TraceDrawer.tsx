import * as Dialog from "@radix-ui/react-dialog";
import { Download, X } from "lucide-react";
import { useEffect, useMemo, useRef, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Button } from "../../design/components/primitives/Button";
import { StableJsonViewer } from "../../design/components/StableJsonViewer";
import { copyText } from "../../design/lib";
import type { ChatTurnResult, TurnVerdict } from "../../types/api";
import { CopyableHash } from "./CopyableHash";
import type { TraceFocus } from "./EvidenceStrip";

function Panel({
  id,
  title,
  children,
}: {
  id: TraceFocus | "json" | "raw" | "refusal";
  title: string;
  children: ReactNode;
}) {
  return (
    <section id={`trace-${id}`} className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-3">
      <h3 className="m-0 mb-2 text-sm font-semibold text-[var(--color-text-primary)]">{title}</h3>
      {children}
    </section>
  );
}

function VerdictRow({ label, verdict }: { label: string; verdict: TurnVerdict | null }) {
  return (
    <div className="grid grid-cols-[7rem_1fr] gap-2 text-sm">
      <dt className="text-[var(--color-text-secondary)]">{label}</dt>
      <dd className="m-0">
        {verdict ? (
          <span>
            {verdict.outcome}
            {verdict.runtime_detail ? <span className="ml-2 font-mono text-xs">{verdict.runtime_detail}</span> : null}
          </span>
        ) : (
          "not emitted"
        )}
      </dd>
    </div>
  );
}

export function TraceDrawer({
  result,
  open,
  focus,
  onOpenChange,
}: {
  result: ChatTurnResult | null;
  open: boolean;
  focus?: TraceFocus;
  onOpenChange: (open: boolean) => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);
  const json = useMemo(() => JSON.stringify(result, null, 2), [result]);
  const rawUrl = useMemo(() => {
    if (!result) return "";
    return URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }));
  }, [result]);

  useEffect(() => {
    if (open) {
      restoreFocusRef.current = document.activeElement as HTMLElement;
    } else {
      restoreFocusRef.current?.focus();
    }
  }, [open]);

  useEffect(() => {
    if (!open || !focus) return;
    document.getElementById(`trace-${focus}`)?.scrollIntoView({ block: "start" });
  }, [focus, open]);

  if (!result) return null;

  const replayCommand = `core trace ${JSON.stringify(result.prompt)}`;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40" />
        <Dialog.Content
          aria-label="Trace drawer"
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            closeRef.current?.focus();
          }}
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            restoreFocusRef.current?.focus();
          }}
          className="fixed right-0 top-0 flex h-screen w-[min(42rem,92vw)] flex-col border-l border-[var(--color-border-strong)] bg-[var(--color-surface-base)] shadow-[var(--shadow-floating)] motion-standard"
        >
          <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] p-4">
            <Dialog.Title className="m-0 text-base font-semibold">Turn trace</Dialog.Title>
            <Dialog.Description className="sr-only">Full evidence envelope for the latest chat turn.</Dialog.Description>
            <Dialog.Close asChild>
              <Button ref={closeRef} type="button" variant="quiet" aria-label="Close trace drawer">
                <X size={16} aria-hidden />
                Close
              </Button>
            </Dialog.Close>
          </div>

          <div className="grid gap-3 overflow-y-auto p-4">
            {result.refusal_emitted ? (
              <Panel id="refusal" title="Refusal">
                <p className="m-0 text-sm text-[var(--color-text-secondary)]">
                  Refusal emitted. Boundary detail: <span className="font-mono">{result.normative_detail || "not specified"}</span>
                </p>
              </Panel>
            ) : null}
            <Panel id="metadata" title="Turn metadata">
              <dl className="m-0 grid gap-1 text-sm">
                <div>turn_cost_ms: {result.turn_cost_ms}</div>
                <div>mutation_mode: {result.mutation_mode}</div>
                <div>checkpoint_emitted: {String(result.checkpoint_emitted)}</div>
              </dl>
            </Panel>
            <Panel id="surfaces" title="Surfaces">
              <dl className="m-0 grid gap-3 text-sm">
                <div>
                  <dt className="font-semibold">surface <span className="font-normal text-[var(--color-text-secondary)]">(user-facing response)</span></dt>
                  <dd className="m-0">{result.surface}</dd>
                </div>
                <div>
                  <dt className="font-semibold">articulation_surface <span className="font-normal text-[var(--color-text-secondary)]">(realizer output)</span></dt>
                  <dd className="m-0">{result.articulation_surface ?? "not emitted"}</dd>
                </div>
                <div>
                  <dt className="font-semibold">walk_surface <span className="font-normal text-[var(--color-text-secondary)]">(manifold evidence)</span></dt>
                  <dd className="m-0 font-mono text-xs">{result.walk_surface ?? "not emitted"}</dd>
                </div>
              </dl>
            </Panel>
            <Panel id="grounding" title="Grounding">
              <p className="m-0 text-sm">grounding_source: {result.grounding_source}</p>
              <p className="m-0 mt-1 text-sm text-[var(--color-text-secondary)]">epistemic_state: {result.epistemic_state}</p>
            </Panel>
            <Panel id="verdicts" title="Verdicts">
              <dl className="m-0 grid gap-2">
                <VerdictRow label="identity" verdict={result.identity_verdict} />
                <VerdictRow label="safety" verdict={result.safety_verdict} />
                <VerdictRow label="ethics" verdict={result.ethics_verdict} />
              </dl>
            </Panel>
            <Panel id="proposals" title="Proposal candidates">
              {result.proposal_candidates.length ? (
                <div className="grid gap-2">
                  {result.proposal_candidates.map((candidate) => (
                    <div key={candidate.candidate_id} className="flex items-center justify-between gap-3 text-sm">
                      <span><span className="font-mono">{candidate.candidate_id}</span> {candidate.source_kind}</span>
                      <Link className="text-[var(--color-text-secondary)] underline" to={`/proposals/${candidate.candidate_id}`}>
                        /proposals/{candidate.candidate_id}
                      </Link>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="m-0 text-sm text-[var(--color-text-secondary)]">No proposal candidates.</p>
              )}
            </Panel>
            <Panel id="trace" title="Trace hash + replay">
              {result.trace_hash ? <CopyableHash value={result.trace_hash} /> : <p className="m-0 text-sm">No trace hash recorded.</p>}
              <button
                type="button"
                className="mt-2 rounded border border-[var(--color-border-subtle)] px-2 py-1 font-mono text-xs text-[var(--color-text-secondary)]"
                onClick={() => void copyText(replayCommand)}
              >
                Run: {replayCommand}
              </button>
            </Panel>
            <Panel id="json" title="Stable JSON viewer">
              <StableJsonViewer source={json} />
            </Panel>
            <Panel id="raw" title="Raw payload">
              <details>
                <summary className="cursor-pointer text-sm">Operator raw JSON</summary>
                <a className="mt-2 inline-flex items-center gap-2 text-sm underline" href={rawUrl} download="chat-turn-result.json">
                  <Download size={14} aria-hidden />
                  Download .json
                </a>
                <pre className="mt-2 max-h-72 overflow-auto rounded bg-[var(--color-surface-inset)] p-2 text-xs">{json}</pre>
              </details>
            </Panel>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
