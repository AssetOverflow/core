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
import { WORKBENCH_ROUTES, type RouteElementMap } from "./routes";

// The one place route id → element is bound (App owns the route-component
// imports). Every WORKBENCH_ROUTES id must have an entry here; routes.test
// asserts it, so a registry route without an element fails the suite instead
// of rendering `undefined`.
export const ROUTE_ELEMENTS: RouteElementMap = {
  chat: <ChatRoute />,
  trace: <TraceRoute />,
  replay: <ReplayRoute />,
  demos: <DemoTheaterRoute />,
  proposals: <ProposalsRoute />,
  runs: <RunsRoute />,
  vault: <VaultRoute />,
  audit: <AuditRoute />,
  evals: <EvalsRoute />,
  calibration: <CalibrationRoute />,
  packs: <PacksRoute />,
  settings: <SettingsRoute />,
};

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Shell />}>
            <Route index element={<Navigate to={`/${getWorkbenchPrefs().landingRoute}`} replace />} />
            {WORKBENCH_ROUTES.map((route) => (
              <Route
                key={route.id}
                path={route.routePattern}
                element={ROUTE_ELEMENTS[route.id]}
              />
            ))}
          </Route>
          <Route path="/preview" element={<PreviewPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
