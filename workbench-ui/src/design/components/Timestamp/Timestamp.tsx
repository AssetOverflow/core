import { useEffect, useState } from "react";

export interface TimestampProps {
  iso: string;
  format?: "relative" | "absolute" | "both";
}

const LA_TZ = "America/Los_Angeles";
const MINUTE = 60_000;
const HOUR = 3_600_000;
const DAY = 86_400_000;

function formatAbsolute(date: Date): string {
  return date.toLocaleString("en-US", {
    timeZone: LA_TZ,
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatRelative(date: Date, now: Date): string {
  const diff = now.getTime() - date.getTime();
  if (diff < 0) return "just now";
  if (diff < MINUTE) return "just now";
  if (diff < HOUR) {
    const mins = Math.floor(diff / MINUTE);
    return `${mins}m ago`;
  }
  if (diff < DAY) {
    const hours = Math.floor(diff / HOUR);
    return `${hours}h ago`;
  }
  if (diff < 2 * DAY) return "yesterday";
  const days = Math.floor(diff / DAY);
  if (days < 30) return `${days}d ago`;
  return formatAbsolute(date);
}

export function Timestamp({ iso, format = "both" }: TimestampProps) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    if (format === "absolute") return;
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, [format]);

  const date = new Date(iso);
  const abs = formatAbsolute(date);
  const rel = formatRelative(date, now);

  const displayed = format === "absolute" ? abs : format === "relative" ? rel : rel;
  const tooltip = format === "absolute" ? rel : abs;

  return (
    <time
      dateTime={iso}
      title={tooltip}
      className="whitespace-nowrap text-xs text-[var(--color-text-secondary)]"
      style={{ fontSize: "var(--text-xs)" }}
      data-testid="timestamp"
    >
      {displayed}
      {format === "both" && (
        <span className="ml-1.5 text-[var(--color-text-muted)]">{abs}</span>
      )}
    </time>
  );
}
