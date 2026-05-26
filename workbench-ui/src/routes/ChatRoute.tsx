import { useState } from "react";
import { WorkbenchApiError } from "../api/client";
import { useChatTurn } from "../api/queries";
import { EmptyState } from "../design/components/states/EmptyState";
import { ErrorState } from "../design/components/states/ErrorState";
import { LoadingState } from "../design/components/states/LoadingState";
import { PromptComposer } from "../app/chat/PromptComposer";
import { ResponseCard } from "../app/chat/ResponseCard";
import { TraceDrawer } from "../app/chat/TraceDrawer";
import type { TraceFocus } from "../app/chat/EvidenceStrip";

export function ChatRoute() {
  const chatTurn = useChatTurn();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerFocus, setDrawerFocus] = useState<TraceFocus>("metadata");

  function openTrace(focus: TraceFocus) {
    setDrawerFocus(focus);
    setDrawerOpen(true);
  }

  const error = chatTurn.error;

  return (
    <div className="mx-auto grid max-w-5xl gap-4">
      <PromptComposer disabled={chatTurn.isPending} onSubmit={(prompt) => chatTurn.mutate({ prompt })} />

      {chatTurn.isPending ? <LoadingState label="Awaiting turn..." /> : null}

      {chatTurn.isError ? (
        <ErrorState
          whatFailed={error instanceof WorkbenchApiError ? error.message : "Chat turn failed."}
          mutationStatus="No corpus mutation occurred."
          reproducer={`curl -X POST /chat/turn -d '{"prompt":"${chatTurn.variables?.prompt ?? ""}"}'`}
          retrySafety={error instanceof WorkbenchApiError && error.code === "read_error" ? "Retry after reducing request size." : "Retry: safe"}
        />
      ) : null}

      {!chatTurn.data && !chatTurn.isPending && !chatTurn.isError ? (
        <EmptyState
          statement="Ask CORE a question."
          nextAction={{ kind: "cli", command: "core chat" }}
        />
      ) : null}

      {chatTurn.data ? <ResponseCard result={chatTurn.data} onOpenTrace={openTrace} /> : null}
      <TraceDrawer
        result={chatTurn.data ?? null}
        open={drawerOpen}
        focus={drawerFocus}
        onOpenChange={setDrawerOpen}
      />
    </div>
  );
}
