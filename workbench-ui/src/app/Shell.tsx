import { Outlet } from "react-router-dom";
import { TopBar } from "./TopBar";
import { LeftNav } from "./LeftNav";
import { StatusFooter } from "./StatusFooter";
import { RightInspector } from "./RightInspector";
import { ApiErrorBoundary } from "./ApiErrorBoundary";

export function Shell() {
  // RightInspector defaults to collapsed in W-027
  const inspectorCollapsed = true;

  return (
    <div
      className="grid h-screen"
      style={{
        gridTemplateAreas: inspectorCollapsed
          ? '"topbar topbar" "leftnav main" "footer footer"'
          : '"topbar topbar topbar" "leftnav main inspector" "footer footer footer"',
        gridTemplateRows: "auto 1fr auto",
        gridTemplateColumns: inspectorCollapsed ? "12rem 1fr" : "12rem 1fr 20rem",
      }}
    >
      <div style={{ gridArea: "topbar" }}>
        <TopBar />
      </div>

      <div style={{ gridArea: "leftnav" }}>
        <LeftNav />
      </div>

      <main
        data-region="main"
        style={{ gridArea: "main" }}
        className="overflow-y-auto bg-[var(--color-surface-base)] p-4"
      >
        <ApiErrorBoundary>
          <Outlet />
        </ApiErrorBoundary>
      </main>

      {!inspectorCollapsed && (
        <div style={{ gridArea: "inspector" }}>
          <RightInspector collapsed={false} />
        </div>
      )}

      <div style={{ gridArea: "footer" }}>
        <StatusFooter />
      </div>
    </div>
  );
}
