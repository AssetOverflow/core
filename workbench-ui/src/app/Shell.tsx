import { useEffect, useState, useCallback } from "react";
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
import { useCommandRegistry } from "./commandRegistry";
import { useWorkbenchPrefs } from "./workbenchPrefs";
import { SplitPane } from "../design/components/SplitPane/SplitPane";

function ShellInner() {
  const { subject, inspectorOpen, toggleInspector, notifyAddressCopied } =
    useEvidenceSubject();
  const prefs = useWorkbenchPrefs();
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

  // Action verbs in the palette (Wave R brief R0d): registered by the
  // component that owns the behavior, unregistered on unmount.
  const { register, unregister } = useCommandRegistry();
  useEffect(() => {
    register([
      {
        id: "action-toggle-inspector",
        label: "Toggle inspector",
        section: "Actions",
        kind: "action",
        shortcut: "\u2318I",
        action: toggleInspector,
      },
      {
        id: "action-copy-evidence-link",
        label: "Copy evidence link",
        section: "Actions",
        kind: "action",
        shortcut: "\u2318\u21E7C",
        action: onCopyEvidenceLink,
      },
    ]);
    return () => unregister(["action-toggle-inspector", "action-copy-evidence-link"]);
  }, [register, unregister, toggleInspector, onCopyEvidenceLink]);

  const mainSurface = (
    <main
      data-region="main"
      className="h-full overflow-y-auto bg-[var(--color-surface-base)] p-[var(--density-main-padding)]"
    >
      <ApiErrorBoundary>
        <Outlet />
      </ApiErrorBoundary>
    </main>
  );

  return (
    <div
      className="grid h-screen"
      data-density={prefs.densityMode}
      style={{
        gridTemplateAreas:
          '"topbar topbar" "leftnav center" "footer footer"',
        gridTemplateRows: "auto 1fr auto",
        gridTemplateColumns: "12rem 1fr",
      }}
    >
      <div style={{ gridArea: "topbar" }}>
        <TopBar paletteOpen={paletteOpen} onPaletteOpenChange={setPaletteOpen} />
      </div>

      <div style={{ gridArea: "leftnav" }}>
        <LeftNav />
      </div>

      <div style={{ gridArea: "center" }} className="min-h-0">
        {inspectorOpen ? (
          // Resizable main/inspector split; width persists via the
          // SplitPane id (guarded storage access inside SplitPane).
          <SplitPane direction="horizontal" id="inspector" defaultSplit={72} minSize={240}>
            {mainSurface}
            <RightInspector />
          </SplitPane>
        ) : (
          mainSurface
        )}
      </div>

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
