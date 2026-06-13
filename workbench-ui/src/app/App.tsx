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
import { DemoTheaterRoute } from "./demos/DemoTheaterRoute";
import { EvalsRoute } from "./evals/EvalsRoute";
import { RunsRoute } from "./runs/RunsRoute";
import { PacksRoute } from "./packs/PacksRoute";
import { VaultRoute } from "./vault/VaultRoute";
import { CalibrationRoute } from "./calibration/CalibrationRoute";
import { SettingsRoute } from "./settings/SettingsRoute";
import { getWorkbenchPrefs } from "./workbenchPrefs";

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Shell />}>
            <Route index element={<Navigate to={`/${getWorkbenchPrefs().landingRoute}`} replace />} />
            <Route path="chat" element={<ChatRoute />} />
            <Route path="trace/:turnId?" element={<TraceRoute />} />
            <Route path="replay/:turnId?" element={<ReplayRoute />} />
            <Route path="demos/:demoId?" element={<DemoTheaterRoute />} />
            <Route path="proposals/:proposalId?" element={<ProposalsRoute />} />
            <Route path="evals/:laneId?" element={<EvalsRoute />} />
            <Route path="runs/:sessionId?" element={<RunsRoute />} />
            <Route path="packs/:packId?" element={<PacksRoute />} />
            <Route path="vault" element={<VaultRoute />} />
            <Route path="calibration" element={<CalibrationRoute />} />
            <Route path="audit" element={<AuditRoute />} />
            <Route path="settings" element={<SettingsRoute />} />
          </Route>
          <Route path="/preview" element={<PreviewPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
