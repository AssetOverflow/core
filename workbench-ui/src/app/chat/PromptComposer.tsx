import { Send, X } from "lucide-react";
import { FormEvent, KeyboardEvent, useState } from "react";
import { Button } from "../../design/components/primitives/Button";

const MAX_PROMPT_CHARS = 4096;

export function PromptComposer({
  disabled,
  onSubmit,
}: {
  disabled: boolean;
  onSubmit: (prompt: string) => void;
}) {
  const [prompt, setPrompt] = useState("");
  const overSoftCap = prompt.length >= MAX_PROMPT_CHARS * 0.8;
  const invalid = prompt.trim().length === 0 || prompt.length > MAX_PROMPT_CHARS;

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!disabled && !invalid) onSubmit(prompt);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      submit();
    }
    if (event.key === "Escape") {
      setPrompt("");
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-2" aria-label="Chat prompt composer">
      <textarea
        value={prompt}
        disabled={disabled}
        maxLength={MAX_PROMPT_CHARS + 1}
        onChange={(event) => setPrompt(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask CORE a question..."
        className="min-h-28 resize-y rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3 text-sm text-[var(--color-text-primary)] outline-none focus-visible:border-[var(--color-border-strong)] focus-visible:ring-2 focus-visible:ring-[var(--color-focus-ring)] disabled:opacity-60"
      />
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs text-[var(--color-text-secondary)]">
          {overSoftCap ? <span>{prompt.length}/{MAX_PROMPT_CHARS}</span> : null}
        </div>
        <div className="flex items-center gap-2">
          <Button type="button" variant="quiet" disabled={disabled || prompt.length === 0} onClick={() => setPrompt("")}>
            <X size={14} aria-hidden />
            Clear
          </Button>
          <Button type="submit" disabled={disabled || invalid}>
            <Send size={14} aria-hidden />
            Submit
          </Button>
        </div>
      </div>
    </form>
  );
}
