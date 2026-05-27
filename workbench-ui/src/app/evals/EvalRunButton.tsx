import { useState, useEffect } from "react";
    import { useEvalRun } from "../../api/queries";
    import { Button } from "../../design/components/primitives/Button";
    import type { EvalLaneSummary, EvalRunResult } from "../../types/api";
    import type { WorkbenchApiError } from "../../api/client";

    export function EvalRunButton({
      lane,
      onRunStart,
      onRunSuccess,
      onRunError,
    }: {
      lane: EvalLaneSummary | null;
      onRunStart: () => void;
      onRunSuccess: (result: EvalRunResult) => void;
      onRunError: (error: WorkbenchApiError) => void;
    }) {
      const evalRun = useEvalRun();
      const [version, setVersion] = useState("");
      const [split, setSplit] = useState<"dev" | "public" | "holdout">("public");

      // Reset selection when lane changes
      useEffect(() => {
        if (lane) {
          setVersion(lane.versions[0] || "v1");
          setSplit("public");
        }
      }, [lane]);

      if (!lane || !lane.read_only) {
        return null;
      }

      const handleRun = () => {
        onRunStart();
        evalRun.mutate(
          { lane: lane.lane, version, split },
          {
            onSuccess: (data) => {
              onRunSuccess(data);
            },
            onError: (err) => {
              onRunError(err);
            },
          }
        );
      };

      const isPending = evalRun.isPending;

      return (
        <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4 shadow-sm" data-testid="eval-run-form">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">Run Configuration</h3>
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="version-select" className="text-xs text-[var(--color-text-secondary)] font-medium">
                Version
              </label>
              <select
                id="version-select"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                disabled={isPending}
                className="bg-[var(--color-surface-base)] border border-[var(--color-border-subtle)] rounded px-2.5 py-1.5 text-xs text-[var(--color-text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--color-focus-ring)] disabled:opacity-50"
              >
                {lane.versions.map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="split-select" className="text-xs text-[var(--color-text-secondary)] font-medium">
                Split
              </label>
              <select
                id="split-select"
                value={split}
                onChange={(e) => setSplit(e.target.value as any)}
                disabled={isPending}
                className="bg-[var(--color-surface-base)] border border-[var(--color-border-subtle)] rounded px-2.5 py-1.5 text-xs text-[var(--color-text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--color-focus-ring)] disabled:opacity-50"
              >
                <option value="public">Public</option>
                <option value="dev">Dev</option>
                <option value="holdout" title="Holdout runs require sealed-eval config — use CLI" disabled>
                  Holdout
                </option>
              </select>
            </div>

            <Button
              onClick={handleRun}
              disabled={isPending}
              className="h-8.5"
              data-testid="run-button"
            >
              {isPending ? "Running..." : "Run Eval"}
            </Button>
          </div>
        </div>
      );
    }
