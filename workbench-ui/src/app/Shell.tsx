import { useState, useCallback } from "react";
import { Outlet } from "react-router-dom";
import { TopBar } from "./TopBar";
import { LeftNav } from "./LeftNav";
import { StatusFooter } from "./StatusFooter";
import { RightInspector } from "./RightInspector";
import { ApiErrorBoundary } from "./ApiErrorBoundary";
import { EvidenceProvider, useEvidenceSubject } from "./evidenceContext";
import { EvidenceUrlSync } from "./evidenceUrlSync";
import { isAddressable, subjectToUrl } from "./evidenceAddress";
import { KeyboardHelp } from "./KeyboardHelp";
import { useGlobalKeyboard } from "./useGlobalKeyboard";

function ShellInner() {
  const { subject, inspectorOpen, toggleInspector, notifyAddressCopied } =
    useEvidenceSubject();
  const [helpOpen, setHelpOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  const onTogglePalette = useCallback(() => {
    setPaletteOpen((v) => !v);
  }, []);

  const onShowHelp = useCallback(() => {
    setHelpOpen(true);
  }, []);

  const onCopyEvidenceLink = useCallback(() => {
    if (!isAddressable(subject)) return;
    if (!navigator.clipboard?.writeText) return;
    const url = window.location.origin + subjectToUrl(subject);
    navigator.clipboard.writeText(url).then(
      () => notifyAddressCopied(),
      (err) => console.error("Evidence link copy failed:", err),
    );
  }, [subject, notifyAddressCopied]);

  useGlobalKeyboard({
    onTogglePalette,
    onToggleInspector: toggleInspector,
    onShowHelp,
    onCopyEvidenceLink,
  });

  return (
    <div
      className="grid h-screen"
      style={{
        gridTemplateAreas: inspectorOpen
          ? '"topbar topbar topbar" "leftnav main inspector" "footer footer footer"'
          : '"topbar topbar" "leftnav main" "footer footer"',
        gridTemplateRows: "auto 1fr auto",
        gridTemplateColumns: inspectorOpen ? "12rem 1fr 20rem" : "12rem 1fr",
      }}
    >
      <div style={{ gridArea: "topbar" }}>
        <TopBar paletteOpen={paletteOpen} onPaletteOpenChange={setPaletteOpen} />
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

      {inspectorOpen && (
        <div style={{ gridArea: "inspector" }}>
          <RightInspector />
        </div>
      )}

      <div style={{ gridArea: "footer" }}>
        <StatusFooter />
      </div>

      <KeyboardHelp open={helpOpen} onOpenChange={setHelpOpen} />
    </div>
  );
}

export function Shell() {
  return (
    <EvidenceProvider>
      <EvidenceUrlSync />
      <ShellInner />
    </EvidenceProvider>
  );
}
