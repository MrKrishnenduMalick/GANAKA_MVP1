import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorState, LoadingState } from "@/components/StateViews";
import { api, readError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { WORKSPACE_SETTINGS } from "@/constants/testIds";

const WorkspaceSettings = () => {
  const { workspace, can, loadMe } = useAuth();
  const workspaceId = workspace?.id;
  const [state, setState] = useState({ status: "loading", error: null });
  const [form, setForm] = useState({
    name: "",
    timezone: "",
    currency: "",
    reconciliation_amount_tolerance: 0,
    settlement_match_window_days: 15,
  });
  const [message, setMessage] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!workspaceId) return;
    setState({ status: "loading", error: null });
    try {
      const [detail, settings] = await Promise.all([
        api.get(`/workspaces/${workspaceId}`),
        api.get(`/workspaces/${workspaceId}/settings`),
      ]);
      setForm({
        name: detail.data.name,
        timezone: detail.data.timezone,
        currency: detail.data.currency,
        reconciliation_amount_tolerance: settings.data.reconciliation_amount_tolerance,
        settlement_match_window_days: settings.data.settlement_match_window_days,
      });
      setState({ status: "ready", error: null });
    } catch (caught) {
      setState({ status: "error", error: readError(caught).message });
    }
  }, [workspaceId]);

  useEffect(() => {
    load();
  }, [load]);

  const canUpdate = can("workspace.update");
  const canSettings = can("workspace.settings");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      if (canUpdate) {
        await api.patch(`/workspaces/${workspaceId}`, {
          name: form.name,
          timezone: form.timezone,
          currency: form.currency.toUpperCase(),
        });
      }
      if (canSettings) {
        await api.patch(`/workspaces/${workspaceId}/settings`, {
          reconciliation_amount_tolerance: Number(form.reconciliation_amount_tolerance),
          settlement_match_window_days: Number(form.settlement_match_window_days),
        });
      }
      await loadMe();
      setMessage({ tone: "success", text: "Workspace settings saved." });
    } catch (caught) {
      setMessage({ tone: "error", text: readError(caught).message });
    } finally {
      setSaving(false);
    }
  };

  if (state.status === "loading") return <LoadingState label="Loading workspace" />;
  if (state.status === "error") return <ErrorState message={state.error} onRetry={load} />;

  return (
    <div className="space-y-8" data-testid={WORKSPACE_SETTINGS.root}>
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.15em] text-zinc-500">Settings</p>
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-zinc-950">Workspace</h1>
        <p className="text-sm text-zinc-600">
          Reconciliation tolerances are applied deterministically to every future reconciliation run.
        </p>
      </header>

      {message ? (
        <p
          className={`border p-4 text-sm ${
            message.tone === "error"
              ? "border-destructive/30 bg-destructive/5"
              : "border-emerald-200 bg-emerald-50 text-emerald-900"
          }`}
          data-testid={WORKSPACE_SETTINGS.message}
          role={message.tone === "error" ? "alert" : undefined}
        >
          {message.text}
        </p>
      ) : null}

      <form className="space-y-8" onSubmit={handleSubmit}>
        <section className="border border-zinc-200 bg-white p-6">
          <h2 className="font-display text-lg font-bold tracking-tight text-zinc-900">General</h2>
          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="name">Workspace name</Label>
              <Input
                id="name"
                value={form.name}
                disabled={!canUpdate}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                data-testid={WORKSPACE_SETTINGS.nameInput}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="timezone">Timezone</Label>
              <Input
                id="timezone"
                value={form.timezone}
                disabled={!canUpdate}
                onChange={(event) => setForm({ ...form, timezone: event.target.value })}
                data-testid={WORKSPACE_SETTINGS.timezoneInput}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="currency">Currency</Label>
              <Input
                id="currency"
                maxLength={3}
                value={form.currency}
                disabled={!canUpdate}
                onChange={(event) => setForm({ ...form, currency: event.target.value })}
                data-testid={WORKSPACE_SETTINGS.currencyInput}
              />
            </div>
          </div>
        </section>

        <section className="border border-zinc-200 bg-white p-6">
          <h2 className="font-display text-lg font-bold tracking-tight text-zinc-900">Reconciliation tolerances</h2>
          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="tolerance">Amount tolerance (max 5.00)</Label>
              <Input
                id="tolerance"
                type="number"
                step="0.01"
                min="0"
                max="5"
                value={form.reconciliation_amount_tolerance}
                disabled={!canSettings}
                onChange={(event) => setForm({ ...form, reconciliation_amount_tolerance: event.target.value })}
                data-testid={WORKSPACE_SETTINGS.toleranceInput}
                className="font-mono"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="window">Settlement match window (days, max 45)</Label>
              <Input
                id="window"
                type="number"
                min="1"
                max="45"
                value={form.settlement_match_window_days}
                disabled={!canSettings}
                onChange={(event) => setForm({ ...form, settlement_match_window_days: event.target.value })}
                data-testid={WORKSPACE_SETTINGS.settlementWindowInput}
                className="font-mono"
              />
            </div>
          </div>
        </section>

        <Button
          type="submit"
          className="bg-[#0A0F2C] hover:bg-[#1E293B]"
          disabled={saving || (!canUpdate && !canSettings)}
          data-testid={WORKSPACE_SETTINGS.saveButton}
        >
          {saving ? "Saving…" : "Save changes"}
        </Button>
        {!canUpdate && !canSettings ? (
          <p className="text-xs text-zinc-500">Your role does not permit changing workspace settings.</p>
        ) : null}
      </form>
    </div>
  );
};

export default WorkspaceSettings;
