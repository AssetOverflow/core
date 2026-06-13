import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "../api/queries";
import { Shell } from "./Shell";
import { PreviewPage } from "../preview/PreviewPage";
import { ChatRoute } from "../routes/ChatRoute";
import { ProposalsRoute } from "./proposals/ProposalsRoute";
import { TraceRoute } from "./trace/TraceRoute";
import { AuditRoute } from "./audit/AuditRoute";
import { ReplayRoute } from "./replay/ReplayRoute";
import { EvalsRoute } from "./evals/EvalsRoute";
import { RunsRoute } from "./runs/RunsRoute";
import { PacksRoute } from "./packs/PacksRoute";
import { VaultRoutePlaceholder } from "../routes/VaultRoutePlaceholder";
import { SettingsRoutePlaceholder } from "../routes/SettingsRoutePlaceholder";

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Shell />}>
            <Route index element={<Navigate to="/chat" replace />} />
            <Route path="chat" element={<ChatRoute />} />
            <Route path="trace/:turnId?" element={<TraceRoute />} />
            <Route path="replay/:artifactId?" element={<ReplayRoute />} />
            <Route path="proposals/:proposalId?" element={<ProposalsRoute />} />
            <Route path="evals/:laneId?" element={<EvalsRoute />} />
            <Route path="runs/:sessionId?" element={<RunsRoute />} />
            <Route path="packs/:packId?" element={<PacksRoute />} />
            <Route path="vault" element={<VaultRoutePlaceholder />} />
            <Route path="audit" element={<AuditRoute />} />
            <Route path="settings" element={<SettingsRoutePlaceholder />} />
          </Route>
          <Route path="/preview" element={<PreviewPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
