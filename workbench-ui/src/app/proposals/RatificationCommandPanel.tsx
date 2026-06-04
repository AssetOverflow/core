import React, { useState, useEffect } from "react";
import { Check, X, Clock, Terminal, AlertTriangle } from "lucide-react";
import { useMathRatify, useMathReject, useMathDefer } from "../../api/queries";
import type { MathProposalDetail } from "../../types/api";
import { Button } from "../../design/components/primitives/Button";
import { copyText } from "../../design/lib";

interface RatificationCommandPanelProps {
  proposal: MathProposalDetail;
  state: string;
  replayEquivalent: boolean | null;
  onSuccess?: () => void;
  onDefer?: () => void;
}

const CATEGORY_ALLOWLISTS: Record<string, string[]> = {
  LexicalClaim: ["drain_token"],
  FrameClaim: ["increment_frame", "decrement_frame", "transfer_frame", "remainder_frame"],
  CompositionClaim: ["multiplicative_composition", "additive_composition", "subtractive_composition"],
};

export function RatificationCommandPanel({
  proposal,
  state,
  replayEquivalent,
  onSuccess,
  onDefer,
}: RatificationCommandPanelProps) {
  const handlerName = proposal.handler_name ?? "";
  const isPending = state === "pending";
  const isReplayEquivalent = replayEquivalent === true;
  const isSupportedHandler = ["LexicalClaim", "FrameClaim", "CompositionClaim"].includes(handlerName);
  
  const isEnabled = isPending && isReplayEquivalent && isSupportedHandler;

  const allowedCategories = CATEGORY_ALLOWLISTS[handlerName] || [];
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedPolarity, setSelectedPolarity] = useState("affirms");
  const [showNoteInput, setShowNoteInput] = useState(false);
  const [note, setNote] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusType, setStatusType] = useState<"success" | "error" | "info" | null>(null);

  const ratifyMutation = useMathRatify();
  const rejectMutation = useMathReject();
  const deferMutation = useMathDefer();

  // Reset states when proposal changes
  useEffect(() => {
    if (allowedCategories.length > 0) {
      setSelectedCategory(allowedCategories[0]);
    } else {
      setSelectedCategory("");
    }
    setSelectedPolarity("affirms");
    setShowNoteInput(false);
    setNote("");
    setStatusMessage(null);
    setStatusType(null);
  }, [proposal.proposal_id, handlerName]);

  const handleRatify = async () => {
    if (!isEnabled) {
      if (!isPending) {
        setStatusMessage(`Cannot ratify: proposal state is ${state}`);
        setStatusType("error");
      } else if (!isReplayEquivalent) {
        setStatusMessage("Cannot ratify: proposal is not replay equivalent");
        setStatusType("error");
      } else {
        setStatusMessage("Cannot ratify: unsupported handler name");
        setStatusType("error");
      }
      return;
    }

    setStatusMessage("Executing ratification...");
    setStatusType("info");

    ratifyMutation.mutate(
      {
        proposalId: proposal.proposal_id,
        category: selectedCategory || undefined,
        polarity: handlerName !== "LexicalClaim" ? selectedPolarity : undefined,
        dryRun: false,
      },
      {
        onSuccess: (result) => {
          if (result.applied) {
            setStatusMessage(`Ratification succeeded: ${result.message}`);
            setStatusType("success");
            setTimeout(() => {
              if (onSuccess) onSuccess();
            }, 800);
          } else {
            setStatusMessage(`Dry run validation routed but not applied: ${result.message}`);
            setStatusType("info");
          }
        },
        onError: (err) => {
          setStatusMessage(err.message);
          setStatusType("error");
        },
      }
    );
  };

  const handleReject = async () => {
    setStatusMessage("Recording rejection...");
    setStatusType("info");

    rejectMutation.mutate(
      {
        proposalId: proposal.proposal_id,
        note: note || undefined,
      },
      {
        onSuccess: () => {
          setStatusMessage("Proposal rejected successfully");
          setStatusType("success");
          setShowNoteInput(false);
          setNote("");
          setTimeout(() => {
            if (onSuccess) onSuccess();
          }, 800);
        },
        onError: (err) => {
          setStatusMessage(err.message);
          setStatusType("error");
        },
      }
    );
  };

  const handleDefer = async () => {
    setStatusMessage("Recording deferral...");
    setStatusType("info");

    deferMutation.mutate(
      {
        proposalId: proposal.proposal_id,
      },
      {
        onSuccess: () => {
          setStatusMessage("Proposal deferred successfully");
          setStatusType("success");
          setTimeout(() => {
            if (onDefer) onDefer();
          }, 800);
        },
        onError: (err) => {
          setStatusMessage(err.message);
          setStatusType("error");
        },
      }
    );
  };

  const handleCopyCli = async () => {
    if (proposal.suggested_ratify_cli) {
      await copyText(proposal.suggested_ratify_cli);
      setStatusMessage("Suggested CLI command copied to clipboard");
      setStatusType("success");
      setTimeout(() => {
        setStatusMessage(null);
        setStatusType(null);
      }, 3000);
    } else {
      setStatusMessage("No suggested CLI command available");
      setStatusType("error");
    }
  };

  // Keyboard shortcut listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // If typing in input, don't trigger global shortcuts
      if (document.activeElement?.tagName === "INPUT" || document.activeElement?.tagName === "TEXTAREA") {
        if (e.key === "Escape") {
          e.preventDefault();
          setShowNoteInput(false);
        }
        return;
      }

      if (e.key === "r") {
        e.preventDefault();
        handleRatify();
      } else if (e.key === "x") {
        e.preventDefault();
        setShowNoteInput(true);
      } else if (e.key === "d") {
        e.preventDefault();
        handleDefer();
      } else if (e.key === "y") {
        e.preventDefault();
        handleCopyCli();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [proposal.proposal_id, isEnabled, selectedCategory, selectedPolarity, note, state, replayEquivalent]);

  const handleNoteKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleReject();
    }
  };

  return (
    <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4 shadow-panel mt-4 transition-all">
      <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] pb-2 mb-3">
        <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
          <Terminal size={16} className="text-[var(--color-text-secondary)]" />
          Ratification Corridor
        </h3>
        <span className="text-xs font-mono text-[var(--color-text-muted)] bg-[var(--color-surface-inset)] px-2 py-0.5 rounded">
          {handlerName || "No handler"}
        </span>
      </div>

      {!isEnabled ? (
        <div className="flex items-center gap-2 text-xs text-[var(--color-state-warning-text)] bg-[var(--color-state-warning-bg)] border border-[var(--color-state-warning-border)] p-3 rounded-md mb-2">
          <AlertTriangle size={16} className="shrink-0" />
          <div>
            <strong>Corridor Gated:</strong>{" "}
            {!isPending
              ? `This proposal is already ${state}.`
              : !isReplayEquivalent
              ? "Replay verification failed or is not equivalent. Ratification disabled."
              : !isSupportedHandler
              ? `Ratification handler '${handlerName}' not admitted.`
              : "Preconditions failed."}
          </div>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 mb-4">
          <div>
            <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1">
              Allowlisted Category
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full bg-[var(--color-surface-inset)] border border-[var(--color-border-subtle)] rounded-md px-3 py-1.5 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-focus-ring)] focus:outline-none"
            >
              {allowedCategories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {handlerName !== "LexicalClaim" && (
            <div>
              <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1">
                Polarity Mapping
              </label>
              <select
                value={selectedPolarity}
                onChange={(e) => setSelectedPolarity(e.target.value)}
                className="w-full bg-[var(--color-surface-inset)] border border-[var(--color-border-subtle)] rounded-md px-3 py-1.5 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-focus-ring)] focus:outline-none"
              >
                <option value="affirms">affirms</option>
                <option value="falsifies">falsifies</option>
              </select>
            </div>
          )}
        </div>
      )}

      {showNoteInput && isEnabled && (
        <div className="bg-[var(--color-surface-inset)] p-3 border border-[var(--color-border-subtle)] rounded-md mb-3 transition-all">
          <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-1">
            Rejection Note (Enter to commit, Esc to cancel)
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              autoFocus
              value={note}
              onChange={(e) => setNote(e.target.value)}
              onKeyDown={handleNoteKeyDown}
              placeholder="e.g. unexpected slot constraints, wrong zero hazard"
              className="flex-1 bg-[var(--color-surface-base)] border border-[var(--color-border-subtle)] rounded-md px-3 py-1 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-focus-ring)] focus:outline-none"
            />
            <Button onClick={handleReject} variant="quiet" className="text-[var(--color-review-rejected)]">
              Reject
            </Button>
            <Button onClick={() => setShowNoteInput(false)} variant="quiet">
              Cancel
            </Button>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={handleRatify}
            disabled={!isEnabled || ratifyMutation.isPending}
            variant={isEnabled ? "primary" : "quiet"}
            title="Ratify (r)"
          >
            <Check size={14} className="mr-1" />
            Ratify <span className="text-xs opacity-60 ml-1">(r)</span>
          </Button>

          <Button
            onClick={() => setShowNoteInput(true)}
            disabled={!isEnabled || rejectMutation.isPending}
            variant="quiet"
            title="Reject (x)"
          >
            <X size={14} className="mr-1" />
            Reject <span className="text-xs opacity-60 ml-1">(x)</span>
          </Button>

          <Button
            onClick={handleDefer}
            disabled={!isEnabled || deferMutation.isPending}
            variant="quiet"
            title="Defer (d)"
          >
            <Clock size={14} className="mr-1" />
            Defer <span className="text-xs opacity-60 ml-1">(d)</span>
          </Button>
        </div>

        <Button onClick={handleCopyCli} variant="quiet" title="Copy Suggested CLI (y)">
          Copy CLI <span className="text-xs opacity-60 ml-1">(y)</span>
        </Button>
      </div>

      {statusMessage && (
        <div
          className={`mt-3 p-2.5 rounded-md text-xs font-mono border ${
            statusType === "success"
              ? "bg-[var(--color-state-success-bg)] border-[var(--color-state-success-border)] text-[var(--color-state-success-text)]"
              : statusType === "error"
              ? "bg-[var(--color-state-danger-bg)] border-[var(--color-state-danger-border)] text-[var(--color-state-danger-text)]"
              : "bg-[var(--color-state-info-bg)] border-[var(--color-state-info-border)] text-[var(--color-state-info-text)]"
          }`}
        >
          {statusMessage}
        </div>
      )}
    </section>
  );
}
