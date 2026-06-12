import { useEffect, useMemo, useState } from "react";
import { WorkbenchApiError } from "../../api/client";
import { useAuditEvents } from "../../api/queries";
import { Panel } from "../../design/components/Panel/Panel";
import { SearchInput } from "../../design/components/SearchInput/SearchInput";
import { Timeline, type TimelineEntry } from "../../design/components/Timeline";
import { Button } from "../../design/components/primitives/Button";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import type { AuditEvent } from "../../types/api";

const PAGE_SIZE = 50;

function errorMessage(error: unknown) {
  return error instanceof WorkbenchApiError ? error.message : "Audit event request failed.";
}

function toTimelineEntry(event: AuditEvent): TimelineEntry {
  return {
    id: event.event_id,
    timestamp: event.timestamp,
    source: event.source,
    summary: event.summary,
    mutationBoundary: event.mutation_boundary,
  };
}

function eventMatches(event: AuditEvent, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return event.source.toLowerCase().includes(q) || event.summary.toLowerCase().includes(q);
}

export function AuditRoute() {
  const [offset, setOffset] = useState(0);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [search, setSearch] = useState("");
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const eventsQuery = useAuditEvents(PAGE_SIZE, offset);

  useEffect(() => {
    const page = eventsQuery.data?.items;
    if (!page) return;
    setEvents((current) => {
      if (offset === 0) return page;
      const seen = new Set(current.map((event) => event.event_id));
      return [...current, ...page.filter((event) => !seen.has(event.event_id))];
    });
  }, [eventsQuery.data, offset]);

  const filteredEvents = useMemo(
    () => events.filter((event) => eventMatches(event, search)),
    [events, search],
  );

  const timelineEntries = useMemo(
    () => filteredEvents.map(toTimelineEntry),
    [filteredEvents],
  );

  const hasMore = (eventsQuery.data?.items.length ?? 0) === PAGE_SIZE;
  const isInitialLoading = events.length === 0 && eventsQuery.isLoading;

  if (isInitialLoading) {
    return <LoadingState label="Loading audit events..." />;
  }

  if (eventsQuery.isError) {
    return (
      <ErrorState
        whatFailed={errorMessage(eventsQuery.error)}
        mutationStatus="No audit mutation occurred."
        reproducer="curl /audit/events"
        retrySafety="Retry: safe"
      />
    );
  }

  if (events.length === 0) {
    return (
      <EmptyState
        statement="No audit events recorded."
        nextAction={{ kind: "cli", command: "core audit events" }}
      />
    );
  }

  return (
    <Panel
      title="Audit Timeline"
      toolbar={
        <span className="font-mono text-xs text-[var(--color-text-muted)]">
          {events.length} events
        </span>
      }
    >
      <div className="grid min-h-0 gap-3">
        <SearchInput
          placeholder="Filter by source or summary"
          value={search}
          onChange={setSearch}
        />
        {timelineEntries.length === 0 ? (
          <EmptyState
            statement="No audit events match this filter."
            nextAction={{ kind: "cli", command: "core audit events" }}
          />
        ) : (
          <Timeline
            ariaLabel="Audit events"
            entries={timelineEntries}
            height="calc(100vh - 14rem)"
            initialRect={{ width: 720, height: 560 }}
            selectedId={selectedEventId}
            onSelect={(entry) => setSelectedEventId(entry.id)}
          />
        )}
        {hasMore ? (
          <div className="flex justify-start">
            <Button
              type="button"
              variant="quiet"
              disabled={eventsQuery.isFetching}
              onClick={() => setOffset((current) => current + PAGE_SIZE)}
            >
              {eventsQuery.isFetching ? "Loading more..." : "Load more"}
            </Button>
          </div>
        ) : null}
      </div>
    </Panel>
  );
}
