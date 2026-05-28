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
import { RunsRoute } from "./runs/RunsRoute";
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
            <Route path="trace" element={<TraceRoutePlaceholder />} />
            <Route path="replay" element={<ReplayRoute />} />
            <Route path="proposals" element={<ProposalsRoute />} />
            <Route path="evals" element={<EvalsRoute />} />
            <Route path="runs" element={<RunsRoute />} />
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
