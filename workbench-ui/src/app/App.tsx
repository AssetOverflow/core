import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "../api/queries";
import { Shell } from "./Shell";
import { PreviewPage } from "../preview/PreviewPage";
import { ChatRoute } from "../routes/ChatRoute";
import { ProposalsRoute } from "./proposals/ProposalsRoute";
import { TraceRoutePlaceholder } from "../routes/TraceRoutePlaceholder";
import { ReplayRoute } from "./replay/ReplayRoute";
import { EvalsRoute } from "./evals/EvalsRoute";
import { RunsRoutePlaceholder } from "../routes/RunsRoutePlaceholder";
import { PacksRoutePlaceholder } from "../routes/PacksRoutePlaceholder";
import { VaultRoutePlaceholder } from "../routes/VaultRoutePlaceholder";
import { AuditRoutePlaceholder } from "../routes/AuditRoutePlaceholder";
import { SettingsRoutePlaceholder } from "../routes/SettingsRoutePlaceholder";

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Shell />}>
            <Route index element={<Navigate to="/chat" replace />} />
            <Route path="chat" element={<ChatRoute />} />
            <Route path="trace/:turnId?" element={<TraceRoutePlaceholder />} />
            <Route path="replay/:artifactId?" element={<ReplayRoute />} />
            <Route path="proposals/:proposalId?" element={<ProposalsRoute />} />
            <Route path="evals/:laneId?" element={<EvalsRoute />} />
            <Route path="runs" element={<RunsRoutePlaceholder />} />
            <Route path="packs" element={<PacksRoutePlaceholder />} />
            <Route path="vault" element={<VaultRoutePlaceholder />} />
            <Route path="audit" element={<AuditRoutePlaceholder />} />
            <Route path="settings" element={<SettingsRoutePlaceholder />} />
          </Route>
          <Route path="/preview" element={<PreviewPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
