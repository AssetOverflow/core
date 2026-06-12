import { useState } from "react";
import { copyText } from "../../lib";
import { useManagedTimeout } from "../../hooks/useManagedTimeout";

export interface DigestBadgeProps {
  digest: string;
  algorithm?: string;
  verified?: boolean | null;
  truncate?: number;
}

function VerifiedDot({ verified }: { verified: boolean | null }) {
  const color =
    verified === true
      ? "var(--color-state-verified)"
      : verified === false
        ? "var(--color-state-contradicted)"
        : "var(--color-text-muted)";

  const label =
    verified === true
      ? "Verified"
      : verified === false
        ? "Not verified"
        : "Verification unknown";

  return (
    <span
      aria-label={label}
      className="inline-block h-2 w-2 shrink-0 rounded-full"
      style={{ background: color }}
    />
  );
}

export function DigestBadge({
  digest,
  algorithm = "sha256",
  verified,
  // Wave R hash display standard: 12 visible chars + copy, everywhere.
  truncate = 12,
}: DigestBadgeProps) {
  const [copied, setCopied] = useState(false);
  const scheduleReset = useManagedTimeout();

  const display = digest.length > truncate
    ? `${digest.slice(0, truncate)}...`
    : digest;

  const fullDisplay = `${algorithm}:${display}`;

  return (
    <button
      type="button"
      aria-label={`Digest ${algorithm}:${digest}. Click to copy.`}
      className="inline-flex items-center gap-1.5 rounded-md border px-2 py-1 font-mono text-xs transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
      style={{
        borderColor: "var(--color-border-subtle)",
        background: "var(--color-surface-inset)",
        color: "var(--color-text-mono)",
        cursor: "pointer",
        fontFamily: "var(--font-mono)",
        fontSize: "var(--text-xs)",
        transitionDuration: "var(--motion-duration-fast)",
        transitionTimingFunction: "var(--motion-ease-standard)",
      }}
      onClick={() => {
        void copyText(`${algorithm}:${digest}`).then(() => {
          setCopied(true);
          scheduleReset(() => setCopied(false), 1500);
        });
      }}
      data-testid="digest-badge"
    >
      {verified !== undefined && <VerifiedDot verified={verified} />}
      <span>{copied ? "Copied" : fullDisplay}</span>
    </button>
  );
}
