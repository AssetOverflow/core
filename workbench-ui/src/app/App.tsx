import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "../api/queries";
import { Shell } from "./Shell";
import { PreviewPage } from "../preview/PreviewPage";
import { ChatRoutePlaceholder } from "../routes/ChatRoutePlaceholder";
import { TraceRoutePlaceholder } from "../routes/TraceRoutePlaceholder";
import { ReplayRoutePlaceholder } from "../routes/ReplayRoutePlaceholder";
import { ProposalsRoutePlaceholder } from "../routes/ProposalsRoutePlaceholder";
import { EvalsRoutePlaceholder } from "../routes/EvalsRoutePlaceholder";
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
            <Route path="chat" element={<ChatRoutePlaceholder />} />
            <Route path="trace" element={<TraceRoutePlaceholder />} />
            <Route path="replay" element={<ReplayRoutePlaceholder />} />
            <Route path="proposals" element={<ProposalsRoutePlaceholder />} />
            <Route path="evals" element={<EvalsRoutePlaceholder />} />
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
