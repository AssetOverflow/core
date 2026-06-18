import React, { useMemo, useState } from 'react';
import {
  Panel,
  EmptyState,
  ErrorState,
  LoadingState,
  SearchInput,
  StableJsonViewer,
  TruncatedCell,
  MetadataTable,
} from '../../design';
import type { ExperienceRecord } from '../../types/api'; // Will be extended in api.ts

/**
 * ExperienceFlywheelPanel
 *
 * Surfaces the bounded practice-memory flywheel (from GSM8K sealed scout runs).
 * Shows compacted ExperienceRecords with retention gates, hazard/family blocking,
 * provenance, and promotion candidates.
 *
 * Designed to be dropped into EvalsRoute (right pane) or used as a standalone
 * view. Fully compliant with ADR-0160 (read-only evidence) and ADR-0162
 * (design system, honest states, no cognitive theater).
 */

interface ExperienceFlywheelPanelProps {
  records?: ExperienceRecord[];
  isLoading?: boolean;
  error?: Error | null;
  onRecordSelect?: (record: ExperienceRecord) => void;
  className?: string;
}

// Temporary local type until backend types land in api.ts
// Matches description from PR #816 (compaction, retention, provenance)
export interface ExperienceRecord {
  id: string;
  case_id: string;
  candidate_family: string;
  arithmetic_chain_signature?: string;
  hazard_tags: string[];
  status: 'retained' | 'compacted' | 'promoted' | 'dropped';
  retention_reason?: string;
  count: number;
  source_report_hash?: string;
  source_run_id?: string;
  promotion_candidate?: boolean;
  created_at?: string;
  // Additional compacted metadata
  compacted_from_count?: number;
}

// Simple classification for tone
function getRecordTone(record: ExperienceRecord): 'success' | 'warning' | 'danger' | 'neutral' {
  if (record.promotion_candidate) return 'success';
  if (record.hazard_tags.length > 0) return 'danger';
  if (record.status === 'dropped') return 'warning';
  return 'neutral';
}

function RecordRow({
  record,
  onSelect,
}: {
  record: ExperienceRecord;
  onSelect: (r: ExperienceRecord) => void;
}) {
  const tone = getRecordTone(record);

  return (
    <div
      className="grid grid-cols-[1fr,auto,auto] items-center gap-3 rounded border border-[var(--color-border)] bg-[var(--color-surface-base)] p-3 text-sm hover:bg-[var(--color-surface-raised)] cursor-pointer"
      onClick={() => onSelect(record)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(record);
        }
      }}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <TruncatedCell className="font-mono text-xs text-[var(--color-text-secondary)]">
            {record.case_id}
          </TruncatedCell>
          <span className="font-semibold text-[var(--color-text-primary)]">
            {record.candidate_family}
          </span>
        </div>
        {record.arithmetic_chain_signature && (
          <TruncatedCell className="mt-0.5 text-xs text-[var(--color-text-tertiary)]">
            {record.arithmetic_chain_signature}
          </TruncatedCell>
        )}
      </div>

      <div className="flex flex-wrap gap-1.5">
        {record.hazard_tags.length > 0 && (
          <span className="inline-flex items-center rounded-full bg-[var(--color-state-danger-bg)] px-2 py-0.5 text-xs text-[var(--color-state-danger-text)]">
            {record.hazard_tags.length} hazard{record.hazard_tags.length > 1 ? 's' : ''}
          </span>
        )}
        {record.promotion_candidate && (
          <span className="inline-flex items-center rounded-full bg-[var(--color-state-success-bg)] px-2 py-0.5 text-xs text-[var(--color-state-success-text)]">
            promotion candidate
          </span>
        )}
      </div>

      <div className="flex items-center gap-2 text-right text-xs tabular-nums text-[var(--color-text-secondary)]">
        <span>{record.count}×</span>
        <span className="text-[var(--color-text-tertiary)]">{record.status}</span>
      </div>
    </div>
  );
}

export function ExperienceFlywheelPanel({
  records = [],
  isLoading = false,
  error = null,
  onRecordSelect,
  className,
}: ExperienceFlywheelPanelProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRecord, setSelectedRecord] = useState<ExperienceRecord | null>(null);

  const filteredRecords = useMemo(() => {
    if (!searchTerm) return records;
    const term = searchTerm.toLowerCase();
    return records.filter(
      (r) =>
        r.case_id.toLowerCase().includes(term) ||
        r.candidate_family.toLowerCase().includes(term) ||
        r.hazard_tags.some((t) => t.toLowerCase().includes(term)) ||
        (r.retention_reason && r.retention_reason.toLowerCase().includes(term))
    );
  }, [records, searchTerm]);

  const summary = useMemo(() => {
    const total = records.length;
    const retained = records.filter((r) => r.status === 'retained' || r.status === 'compacted').length;
    const promotionCandidates = records.filter((r) => r.promotion_candidate).length;
    const withHazards = records.filter((r) => r.hazard_tags.length > 0).length;
    return { total, retained, promotionCandidates, withHazards };
  }, [records]);

  const handleSelect = (record: ExperienceRecord) => {
    setSelectedRecord(record);
    onRecordSelect?.(record);
  };

  if (isLoading) {
    return (
      <Panel title="Experience Flywheel" className={className}>
        <LoadingState label="Loading practice memory records..." />
      </Panel>
    );
  }

  if (error) {
    return (
      <Panel title="Experience Flywheel" className={className}>
        <ErrorState
          title="Failed to load flywheel"
          message={error.message}
          reproducer="Run the sealed scout + flywheel compaction script again"
          onRetry={() => window.location.reload()}
        />
      </Panel>
    );
  }

  if (records.length === 0) {
    return (
      <Panel title="Experience Flywheel" className={className}>
        <EmptyState
          title="No practice records yet"
          description="The bounded experience flywheel is empty. High-signal GSM8K sealed scout cases will appear here after compaction."
          actionLabel="Run flywheel"
          onAction={() => {
            // Placeholder — in real integration this could trigger a command palette action
            alert('Run: scripts/gsm8k_experience_flywheel.py --out ...');
          }}
        />
      </Panel>
    );
  }

  return (
    <Panel
      title="Experience Flywheel"
      subtitle={`${summary.total} records • ${summary.retained} retained • ${summary.promotionCandidates} promotion candidates`}
      className={className}
      actions={[
        {
          label: 'Refresh',
          onClick: () => window.location.reload(),
        },
      ]}
    >
      <div className="space-y-4">
        {/* Summary metrics */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded border border-[var(--color-border)] bg-[var(--color-surface-base)] p-3">
            <div className="text-xs text-[var(--color-text-secondary)]">Total Records</div>
            <div className="text-2xl font-semibold tabular-nums text-[var(--color-text-primary)]">
              {summary.total}
            </div>
          </div>
          <div className="rounded border border-[var(--color-border)] bg-[var(--color-surface-base)] p-3">
            <div className="text-xs text-[var(--color-text-secondary)]">Retained / Compacted</div>
            <div className="text-2xl font-semibold tabular-nums text-[var(--color-state-success-text)]">
              {summary.retained}
            </div>
          </div>
          <div className="rounded border border-[var(--color-border)] bg-[var(--color-surface-base)] p-3">
            <div className="text-xs text-[var(--color-text-secondary)]">Promotion Candidates</div>
            <div className="text-2xl font-semibold tabular-nums text-[var(--color-state-success-text)]">
              {summary.promotionCandidates}
            </div>
          </div>
          <div className="rounded border border-[var(--color-border)] bg-[var(--color-surface-base)] p-3">
            <div className="text-xs text-[var(--color-text-secondary)]">With Hazards</div>
            <div className="text-2xl font-semibold tabular-nums text-[var(--color-state-danger-text)]">
              {summary.withHazards}
            </div>
          </div>
        </div>

        {/* Search */}
        <SearchInput
          value={searchTerm}
          onChange={setSearchTerm}
          placeholder="Search case ID, family, hazard, or retention reason..."
          className="w-full"
        />

        {/* Record list */}
        <div className="space-y-2">
          {filteredRecords.length === 0 ? (
            <div className="py-8 text-center text-sm text-[var(--color-text-secondary)]">
              No records match your search.
            </div>
          ) : (
            filteredRecords.map((record) => (
              <RecordRow key={record.id} record={record} onSelect={handleSelect} />
            ))
          )}
        </div>

        {/* Detail inspector (inline for now; can move to RightInspector later) */}
        {selectedRecord && (
          <div className="mt-6 rounded border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-4">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <div className="font-mono text-sm text-[var(--color-text-secondary)]">
                  {selectedRecord.case_id}
                </div>
                <div className="text-lg font-semibold text-[var(--color-text-primary)]">
                  {selectedRecord.candidate_family}
                </div>
              </div>
              <button
                onClick={() => setSelectedRecord(null)}
                className="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
              >
                Close detail
              </button>
            </div>

            <MetadataTable
              rows={[
                { label: 'Status', value: selectedRecord.status },
                { label: 'Count', value: String(selectedRecord.count) },
                { label: 'Promotion Candidate', value: selectedRecord.promotion_candidate ? 'Yes' : 'No' },
                { label: 'Hazards', value: selectedRecord.hazard_tags.join(', ') || 'None' },
                { label: 'Retention Reason', value: selectedRecord.retention_reason || '—' },
                { label: 'Source Report Hash', value: selectedRecord.source_report_hash || '—' },
                { label: 'Source Run ID', value: selectedRecord.source_run_id || '—' },
              ]}
            />

            <div className="mt-4">
              <div className="mb-1.5 text-xs font-medium text-[var(--color-text-secondary)]">
                Full Record (Stable JSON)
              </div>
              <StableJsonViewer data={selectedRecord} />
            </div>
          </div>
        )}

        <div className="pt-2 text-[10px] text-[var(--color-text-tertiary)]">
          Bounded experience flywheel • retention gates enforce high-signal cases only • family wrong-risk blocking active
        </div>
      </div>
    </Panel>
  );
}
