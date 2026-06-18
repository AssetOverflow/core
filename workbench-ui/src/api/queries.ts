import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';
import type { ExperienceRecord } from '../types/api';

// === Experience Flywheel Queries ===

export function useExperienceFlywheelRecords() {
  return useQuery<ExperienceRecord[]>({
    queryKey: ['experience-flywheel', 'records'],
    queryFn: async () => {
      // Real endpoint expected: GET /evals/flywheel/records
      // Returns compacted ExperienceRecord[] from the bounded practice memory
      const response = await apiClient.get('/evals/flywheel/records');
      return response.data;
    },
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

// === Capability Paradigm Queries ===

export interface CapabilityParadigmState {
  recent_lifts: Array<{
    id: string;
    description: string;
    cases_lifted: string[];
    wrong_preserved: boolean;
    gate_context?: string;
    evidence_hash?: string;
  }>;
  gate_statuses: Array<{
    gate: string;
    status: 'active' | 'completed' | 'blocked';
    injections: number;
  }>;
  overall_wrong_zero: boolean;
}

export function useCapabilityParadigmState() {
  return useQuery<CapabilityParadigmState>({
    queryKey: ['capability-paradigm', 'state'],
    queryFn: async () => {
      // Real endpoint expected: GET /capabilities/paradigm/state
      // Aggregates current lifts, gate progress, and invariant status
      const response = await apiClient.get('/capabilities/paradigm/state');
      return response.data;
    },
    staleTime: 60_000,
  });
}
