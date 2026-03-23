"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { submitFeedback, type FeedbackPayload } from "@/lib/api";

interface Props {
  trigger: "forecast" | "chat";
  company?: string;
  lastQuery?: string;
  onClose: () => void;
}

const ISSUES: Record<string, string[]> = {
  accuracy: ["Output seems wrong", "Too generic / vague", "Data seems outdated", "Hard to interpret", "Missed key info"],
  speed:    ["Took too long", "App was lagging", "Request timed out", "Slow to load"],
  ease:     ["Confusing interface", "Didn't understand output", "Too many steps", "Didn't know what to do next", "Missing guidance"],
};

function Stars({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex gap-2">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          onClick={() => onChange(n)}
          className={`w-9 h-9 rounded-lg border text-sm font-semibold transition-colors ${
            n <= value
              ? "bg-primary border-primary text-white"
              : "border-border text-muted-foreground hover:border-primary/50"
          }`}
        >
          {n}
        </button>
      ))}
    </div>
  );
}

export default function FeedbackModal({ trigger, company, lastQuery, onClose }: Props) {
  const [step, setStep] = useState(1);
  const [feature] = useState<"forecast" | "chat" | "both">(trigger);
  const [succeeded, setSucceeded] = useState<"yes" | "partially" | "no" | null>(null);
  const [accuracy, setAccuracy] = useState(0);
  const [speed, setSpeed] = useState(0);
  const [ease, setEase] = useState(0);
  const [selectedIssues, setSelectedIssues] = useState<string[]>([]);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const lowRatings = [
    ...(accuracy > 0 && accuracy <= 3 ? ISSUES.accuracy : []),
    ...(speed > 0 && speed <= 3 ? ISSUES.speed : []),
    ...(ease > 0 && ease <= 3 ? ISSUES.ease : []),
  ];
  const showIssuesStep = lowRatings.length > 0;
  const totalSteps = showIssuesStep ? 4 : 3;

  function toggleIssue(issue: string) {
    setSelectedIssues((prev) =>
      prev.includes(issue) ? prev.filter((i) => i !== issue) : [...prev, issue]
    );
  }

  async function handleSubmit() {
    setSubmitting(true);
    const payload: FeedbackPayload = {
      feature,
      succeeded: succeeded!,
      accuracy: accuracy || undefined,
      speed: speed || undefined,
      ease: ease || undefined,
      issues: selectedIssues.length ? selectedIssues : undefined,
      comment: comment.trim() || undefined,
      company,
      query: lastQuery,
    };
    try {
      await submitFeedback(payload);
    } catch {
      // best-effort — don't block user
    }
    setDone(true);
    setSubmitting(false);
    setTimeout(onClose, 1800);
  }

  const canNext =
    (step === 1 && succeeded !== null) ||
    (step === 2 && accuracy > 0 && speed > 0 && ease > 0) ||
    (step === 3 && showIssuesStep);

  if (done) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
        <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-green-500/10">
            <span className="text-2xl">✓</span>
          </div>
          <p className="font-semibold text-foreground">Thanks for the feedback!</p>
          <p className="mt-1 text-sm text-muted-foreground">It helps us improve.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <p className="text-xs text-muted-foreground">
              Step {step} of {totalSteps}
            </p>
            <div className="mt-1 flex gap-1">
              {Array.from({ length: totalSteps }).map((_, i) => (
                <div
                  key={i}
                  className={`h-1 w-6 rounded-full transition-colors ${
                    i < step ? "bg-primary" : "bg-border"
                  }`}
                />
              ))}
            </div>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-5 py-5 space-y-4">
          {/* Step 1 — Did it work? */}
          {step === 1 && (
            <>
              <p className="font-semibold text-foreground">
                Did the {trigger} work for you?
              </p>
              <div className="grid grid-cols-3 gap-2">
                {(["yes", "partially", "no"] as const).map((opt) => (
                  <button
                    key={opt}
                    onClick={() => setSucceeded(opt)}
                    className={`rounded-lg border py-3 text-sm font-medium capitalize transition-colors ${
                      succeeded === opt
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border text-muted-foreground hover:border-primary/40"
                    }`}
                  >
                    {opt === "yes" ? "Yes" : opt === "partially" ? "Partially" : "No"}
                  </button>
                ))}
              </div>
            </>
          )}

          {/* Step 2 — Ratings */}
          {step === 2 && (
            <>
              <p className="font-semibold text-foreground">Rate your experience</p>
              <div className="space-y-4">
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Accuracy</p>
                  <Stars value={accuracy} onChange={setAccuracy} />
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Speed</p>
                  <Stars value={speed} onChange={setSpeed} />
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Ease of understanding</p>
                  <Stars value={ease} onChange={setEase} />
                </div>
              </div>
            </>
          )}

          {/* Step 3 — Issues (conditional) */}
          {step === 3 && showIssuesStep && (
            <>
              <p className="font-semibold text-foreground">What went wrong?</p>
              <p className="text-xs text-muted-foreground">Select all that apply</p>
              <div className="flex flex-wrap gap-2">
                {lowRatings.map((issue) => (
                  <button
                    key={issue}
                    onClick={() => toggleIssue(issue)}
                    className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                      selectedIssues.includes(issue)
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border text-muted-foreground hover:border-primary/40"
                    }`}
                  >
                    {issue}
                  </button>
                ))}
              </div>
            </>
          )}

          {/* Last step — Comment */}
          {((step === 3 && !showIssuesStep) || (step === 4 && showIssuesStep)) && (
            <>
              <p className="font-semibold text-foreground">Anything else? <span className="text-muted-foreground font-normal text-sm">(optional)</span></p>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="What could be better?"
                rows={3}
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none"
              />
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-between border-t border-border px-5 py-4">
          {step > 1 ? (
            <button
              onClick={() => setStep((s) => s - 1)}
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Back
            </button>
          ) : (
            <div />
          )}

          {step < totalSteps ? (
            <button
              onClick={() => setStep((s) => s + 1)}
              disabled={!canNext}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-40 hover:bg-primary/90 transition-colors"
            >
              Next
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={submitting || succeeded === null}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-40 hover:bg-primary/90 transition-colors"
            >
              {submitting ? "Sending..." : "Submit"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
