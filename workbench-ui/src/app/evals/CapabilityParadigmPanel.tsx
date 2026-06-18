import { InfoBadge } from "../../design/components/badges/Badge";
import { MetadataTable } from "../../design/components/MetadataTable/MetadataTable";
import { Panel } from "../../design/components/Panel/Panel";
import { TruncatedCell } from "../../design/components/TruncatedCell";
import {
  BLOCKED_FAMILIES,
  CLUSTER_CONTRACT_SPRINT11,
  DOCUMENTED_BASELINE_LABEL,
  DOCUMENTED_TRAIN_SAMPLE_BASELINE,
  GATE_LADDER_A2E_A2Q,
} from "./capabilityMasteryData";

function formatScore({ correct, refused, wrong }: { correct: number; refused: number; wrong: number }) {
  return `${correct} / ${refused} / ${wrong}`;
}

export function CapabilityParadigmPanel() {
  const baseline = DOCUMENTED_TRAIN_SAMPLE_BASELINE;

  return (
    <Panel
      title="Capability Paradigm"
      toolbar={
        <InfoBadge
          label="Documented"
          colorToken="--color-text-secondary"
          meaning="Milestone cards are sourced from committed lookback docs on main through PR 824 — not a live workbench API."
          adr="ADR-0160 / ADR-0162"
          evidence="No GET /capability endpoint exists; values mirror lookback analyses."
        />
      }
    >
      <div className="flex flex-col gap-4">
        <div>
          <p className="m-0 text-xs text-[var(--color-text-secondary)] [text-wrap:balance]">
            {DOCUMENTED_BASELINE_LABEL}
          </p>
          <MetadataTable
            rows={[
              {
                key: "train_sample (serving)",
                value: (
                  <span className="font-mono text-sm text-[var(--color-text-primary)]">
                    {formatScore(baseline)}
                  </span>
                ),
                mono: true,
              },
              {
                key: "wrong invariant",
                value: (
                  <span className="text-[var(--color-state-success-text)] font-medium">
                    wrong = 0 (documented)
                  </span>
                ),
              },
              {
                key: "evidence through",
                value: "PR 824 — Sprint 11 ClusterContract",
              },
            ]}
          />
        </div>

        <div>
          <h3 className="m-0 mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-secondary)]">
            Gate ladder (A2e → A2q)
          </h3>
          <div className="overflow-x-auto rounded border border-[var(--color-border-subtle)]">
            <table className="w-full min-w-[36rem] border-collapse text-left text-xs">
              <thead className="bg-[var(--color-surface-inset)] text-[var(--color-text-secondary)]">
                <tr>
                  <th className="px-2 py-1.5 font-medium">Gate</th>
                  <th className="px-2 py-1.5 font-medium">Organ</th>
                  <th className="px-2 py-1.5 font-medium">Sprint</th>
                  <th className="px-2 py-1.5 font-medium">Lifted</th>
                  <th className="px-2 py-1.5 font-medium">Score after</th>
                  <th className="px-2 py-1.5 font-medium">Lookback</th>
                </tr>
              </thead>
              <tbody>
                {GATE_LADDER_A2E_A2Q.map((row) => (
                  <tr
                    key={row.gate}
                    className="border-t border-[var(--color-border-subtle)]"
                    data-testid={`gate-row-${row.gate}`}
                  >
                    <td className="px-2 py-1.5 font-mono text-[var(--color-text-primary)]">{row.gate}</td>
                    <td className="px-2 py-1.5 text-[var(--color-text-primary)]">
                      <TruncatedCell value={row.organ} label="organ" />
                    </td>
                    <td className="px-2 py-1.5 text-[var(--color-text-secondary)]">{row.sprint}</td>
                    <td className="px-2 py-1.5 font-mono text-[var(--color-text-secondary)]">
                      {row.newlySolved.length > 0 ? row.newlySolved.join(", ") : "—"}
                    </td>
                    <td className="px-2 py-1.5 font-mono text-[var(--color-text-primary)]">
                      {formatScore(row.scoreAfter)}
                    </td>
                    <td className="px-2 py-1.5 font-mono text-[10px] text-[var(--color-text-tertiary)]">
                      <TruncatedCell value={row.lookbackDoc} label="lookback doc" mono />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div
          className="rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3"
          data-testid="cluster-contract-sprint11"
        >
          <h3 className="m-0 text-xs font-semibold text-[var(--color-text-primary)]">
            ClusterContract — Sprint 11 (PR 824)
          </h3>
          <p className="mt-1 mb-2 text-xs text-[var(--color-text-secondary)] [text-wrap:balance]">
            First ClusterContract sprint: typed chain + explicit{" "}
            <code className="font-mono">calendar_table</code> provenance for Gate A2q.
          </p>
          <MetadataTable
            rows={[
              { key: "family_id", value: CLUSTER_CONTRACT_SPRINT11.familyId, mono: true },
              { key: "organs", value: CLUSTER_CONTRACT_SPRINT11.organs.join(" + ") },
              { key: "included case", value: CLUSTER_CONTRACT_SPRINT11.includedCase, mono: true },
              { key: "provenance", value: CLUSTER_CONTRACT_SPRINT11.provenance, mono: true },
              { key: "lookback", value: CLUSTER_CONTRACT_SPRINT11.lookbackDoc, mono: true },
            ]}
          />
        </div>

        <div>
          <h3 className="m-0 mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-secondary)]">
            Blocked families (documented)
          </h3>
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {BLOCKED_FAMILIES.map((blocked) => (
              <li
                key={blocked.family}
                className="rounded border border-[var(--color-border-subtle)] p-2 text-xs"
                data-testid={`blocked-${blocked.family.split(" ")[0]}`}
              >
                <div className="font-medium text-[var(--color-text-primary)]">{blocked.family}</div>
                <div className="mt-0.5 font-mono text-[var(--color-text-secondary)]">
                  cases: {blocked.cases.join(", ")}
                </div>
                <div className="mt-1 text-[var(--color-text-tertiary)]">{blocked.reason}</div>
              </li>
            ))}
          </ul>
        </div>

        <p className="m-0 text-[10px] text-[var(--color-text-tertiary)] [text-wrap:balance]">
          Sprint 12 lookback doc is not on main yet. Re-run eval lanes or read lookback markdown in-repo
          for replay evidence; this panel does not fabricate live serving counts.
        </p>
      </div>
    </Panel>
  );
}