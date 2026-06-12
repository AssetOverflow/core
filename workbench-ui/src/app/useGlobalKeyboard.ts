import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

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
}

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
}: GlobalKeyboardOptions) {
  const navigate = useNavigate();

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const meta = e.metaKey || e.ctrlKey;

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
  }, [navigate, onTogglePalette, onToggleInspector, onShowHelp]);
}
