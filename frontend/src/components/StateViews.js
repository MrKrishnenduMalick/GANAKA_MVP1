import { AlertTriangle, Inbox, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { STATE } from "@/constants/testIds";

export const LoadingState = ({ label = "Loading" }) => (
  <div className="flex items-center gap-3 py-16 text-sm text-muted-foreground" data-testid={STATE.loading}>
    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
    <span>{label}…</span>
  </div>
);

export const ErrorState = ({ message, onRetry }) => (
  <div
    className="flex flex-col items-start gap-3 border border-destructive/30 bg-destructive/5 p-6"
    data-testid={STATE.error}
    role="alert"
  >
    <div className="flex items-center gap-2 text-destructive">
      <AlertTriangle className="h-4 w-4" aria-hidden="true" />
      <span className="font-display text-sm font-bold uppercase tracking-[0.15em]">Something went wrong</span>
    </div>
    <p className="text-sm text-zinc-700">{message}</p>
    {onRetry ? (
      <Button variant="outline" size="sm" onClick={onRetry} data-testid="state-error-retry-button">
        Try again
      </Button>
    ) : null}
  </div>
);

export const EmptyState = ({ title, description, action, testId = STATE.empty }) => (
  <div className="flex flex-col items-start gap-3 border border-dashed border-zinc-300 bg-white p-10" data-testid={testId}>
    <Inbox className="h-5 w-5 text-zinc-400" aria-hidden="true" />
    <h3 className="font-display text-lg font-bold text-zinc-900">{title}</h3>
    <p className="max-w-lg text-sm text-zinc-600">{description}</p>
    {action}
  </div>
);
