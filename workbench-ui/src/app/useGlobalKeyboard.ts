import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useRegisterShortcuts, type ShortcutEntry } from "./shortcutRegistry";

const ROUTE_KEYS: Record<string, string> = {
  "1": "/chat",
  "2": "/trace",
  "3": "/replay",
  "4": "/proposals",
  "5": "/evals",
  "6": "/runs",
  "7": "/packs",
  "8": "/vault",
  "9": "/audit",
  "0": "/settings",
};

interface GlobalKeyboardOptions {
  onTogglePalette: () => void;
  onToggleInspector: () => void;
  onShowHelp: () => void;
  onCopyEvidenceLink: () => void;
}

// The binder registers exactly what it binds: KeyboardHelp renders from the
// shortcut registry, so an overlay row exists iff a handler exists.
const GLOBAL_SHORTCUTS: readonly ShortcutEntry[] = [
  { id: "global-palette", keys: "\u2318K", action: "Command palette", order: 10 },
  { id: "global-inspector", keys: "\u2318I", action: "Toggle inspector", order: 11 },
  { id: "global-routes", keys: "\u23181\u20130", action: "Navigate to route 1\u201310", order: 12 },
  { id: "global-copy-link", keys: "\u2318\u21E7C", action: "Copy evidence link", order: 13 },
  // Esc is bound by every Radix overlay (palette, help, drawers).
  { id: "global-escape", keys: "Esc", action: "Close overlay", order: 50 },
  { id: "global-help", keys: "?", action: "This help", order: 60 },
];

function isInputFocused(): boolean {
  const el = document.activeElement;
  if (!el) return false;
  const tag = el.tagName?.toLowerCase();
  return tag === "input" || tag === "textarea" || (el as HTMLElement).isContentEditable === true;
}

export function useGlobalKeyboard({
  onTogglePalette,
  onToggleInspector,
  onShowHelp,
  onCopyEvidenceLink,
}: GlobalKeyboardOptions) {
  const navigate = useNavigate();

  useRegisterShortcuts(GLOBAL_SHORTCUTS);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const meta = e.metaKey || e.ctrlKey;

      if (meta && e.shiftKey && e.key.toLowerCase() === "c") {
        if (isInputFocused()) return;
        e.preventDefault();
        onCopyEvidenceLink();
        return;
      }

      if (meta && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onTogglePalette();
        return;
      }

      if (meta && e.key.toLowerCase() === "i") {
        e.preventDefault();
        onToggleInspector();
        return;
      }

      if (meta && ROUTE_KEYS[e.key]) {
        e.preventDefault();
        navigate(ROUTE_KEYS[e.key]);
        return;
      }

      if (isInputFocused()) return;

      if (e.key === "?" && !meta) {
        e.preventDefault();
        onShowHelp();
        return;
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [navigate, onTogglePalette, onToggleInspector, onShowHelp, onCopyEvidenceLink]);
}
