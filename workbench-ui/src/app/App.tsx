import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { Suspense, lazy, type ReactElement } from "react";
import { queryClient } from "../api/queries";
import { Shell } from "./Shell";
import { LoadingState } from "../design/components/states/LoadingState";
import { getWorkbenchPrefs } from "./workbenchPrefs";
import { WORKBENCH_ROUTES, type RouteElementMap } from "./routes";

const ChatRoute = lazy(() =>
  import("../routes/ChatRoute").then((module) => ({ default: module.ChatRoute })),
);
const TraceRoute = lazy(() =>
  import("./trace/TraceRoute").then((module) => ({ default: module.TraceRoute })),
);
const ContemplationRoute = lazy(() =>
  import("./contemplation/ContemplationRoute").then((module) => ({
    default: module.ContemplationRoute,
  })),
);
const ReplayRoute = lazy(() =>
  import("./replay/ReplayRoute").then((module) => ({ default: module.ReplayRoute })),
);
const TourRoute = lazy(() =>
  import("./tour/TourRoute").then((module) => ({ default: module.TourRoute })),
);
const DemoTheaterRoute = lazy(() =>
  import("./demos/DemoTheaterRoute").then((module) => ({
    default: module.DemoTheaterRoute,
  })),
);
const ProposalsRoute = lazy(() =>
  import("./proposals/ProposalsRoute").then((module) => ({
    default: module.ProposalsRoute,
  })),
);
const RunsRoute = lazy(() =>
  import("./runs/RunsRoute").then((module) => ({ default: module.RunsRoute })),
);
const LivedLifeRoute = lazy(() =>
  import("./lived-life/LivedLifeRoute").then((module) => ({
    default: module.LivedLifeRoute,
  })),
);
const VaultRoute = lazy(() =>
  import("./vault/VaultRoute").then((module) => ({ default: module.VaultRoute })),
);
const AuditRoute = lazy(() =>
  import("./audit/AuditRoute").then((module) => ({ default: module.AuditRoute })),
);
const EvalsRoute = lazy(() =>
  import("./evals/EvalsRoute").then((module) => ({ default: module.EvalsRoute })),
);
const CalibrationRoute = lazy(() =>
  import("./calibration/CalibrationRoute").then((module) => ({
    default: module.CalibrationRoute,
  })),
);
const PacksRoute = lazy(() =>
  import("./packs/PacksRoute").then((module) => ({ default: module.PacksRoute })),
);
const LogosRoute = lazy(() =>
  import("./logos/LogosRoute").then((module) => ({ default: module.LogosRoute })),
);
const AppleUmaReportRoute = lazy(() =>
  import("./apple-uma/AppleUmaReportRoute").then((module) => ({
    default: module.AppleUmaReportRoute,
  })),
);
const SettingsRoute = lazy(() =>
  import("./settings/SettingsRoute").then((module) => ({
    default: module.SettingsRoute,
  })),
);
const PreviewPage = lazy(() =>
  import("../preview/PreviewPage").then((module) => ({ default: module.PreviewPage })),
);

function lazyRoute(element: ReactElement): ReactElement {
  return (
    <Suspense fallback={<LoadingState label="Loading route..." />}>
      {element}
    </Suspense>
  );
}

// The one place route id → element is bound (App owns the route-component
// imports). Every WORKBENCH_ROUTES id must have an entry here; routes.test
// asserts it, so a registry route without an element fails the suite instead
// of rendering `undefined`.
export const ROUTE_ELEMENTS: RouteElementMap = {
  chat: lazyRoute(<ChatRoute />),
  trace: lazyRoute(<TraceRoute />),
  contemplation: lazyRoute(<ContemplationRoute />),
  tour: lazyRoute(<TourRoute />),
  replay: lazyRoute(<ReplayRoute />),
  demos: lazyRoute(<DemoTheaterRoute />),
  proposals: lazyRoute(<ProposalsRoute />),
  runs: lazyRoute(<RunsRoute />),
  "lived-life": lazyRoute(<LivedLifeRoute />),
  vault: lazyRoute(<VaultRoute />),
  audit: lazyRoute(<AuditRoute />),
  evals: lazyRoute(<EvalsRoute />),
  calibration: lazyRoute(<CalibrationRoute />),
  packs: lazyRoute(<PacksRoute />),
  logos: lazyRoute(<LogosRoute />),
  "apple-uma": lazyRoute(<AppleUmaReportRoute />),
  settings: lazyRoute(<SettingsRoute />),
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
            <Route path="apple-uma" element={ROUTE_ELEMENTS["apple-uma"]} />
          </Route>
          <Route path="/preview" element={lazyRoute(<PreviewPage />)} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
