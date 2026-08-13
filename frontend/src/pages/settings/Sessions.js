import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Monitor, Smartphone } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorState, LoadingState } from "@/components/StateViews";
import { api, readError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { SESSIONS } from "@/constants/testIds";

const formatWhen = (value) => new Date(value).toLocaleString();

const Sessions = () => {
  const { signOutLocal } = useAuth();
  const navigate = useNavigate();
  const [state, setState] = useState({ status: "loading", error: null });
  const [sessions, setSessions] = useState([]);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setState({ status: "loading", error: null });
    try {
      const response = await api.get("/auth/sessions");
      setSessions(response.data);
      setState({ status: "ready", error: null });
    } catch (caught) {
      setState({ status: "error", error: readError(caught).message });
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const revoke = async (sessionId, isCurrent) => {
    setBusyId(sessionId);
    try {
      await api.delete(`/auth/sessions/${sessionId}`);
      if (isCurrent) {
        signOutLocal();
        navigate("/login", { replace: true });
        return;
      }
      await load();
    } catch (caught) {
      setState((current) => ({ ...current, error: readError(caught).message }));
    } finally {
      setBusyId(null);
    }
  };

  const revokeAll = async () => {
    setBusyId("all");
    try {
      await api.post("/auth/logout-all");
      signOutLocal();
      navigate("/login", { replace: true });
    } catch (caught) {
      setState((current) => ({ ...current, error: readError(caught).message }));
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-8" data-testid={SESSIONS.root}>
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-zinc-500">Settings</p>
          <h1 className="font-display text-3xl font-extrabold tracking-tight text-zinc-950">Active sessions</h1>
          <p className="text-sm text-zinc-600">
            Maximum 5 concurrent sessions. Sessions idle for 30 minutes expire automatically.
          </p>
        </div>
        <Button
          variant="outline"
          onClick={revokeAll}
          disabled={busyId === "all"}
          data-testid={SESSIONS.revokeAllButton}
        >
          Sign out everywhere
        </Button>
      </header>

      {state.status === "loading" ? <LoadingState label="Loading sessions" /> : null}
      {state.status === "error" ? <ErrorState message={state.error} onRetry={load} /> : null}

      {state.status === "ready" ? (
        <ul className="divide-y divide-zinc-200 border border-zinc-200 bg-white" data-testid={SESSIONS.list}>
          {sessions.map((session) => (
            <li
              key={session.id}
              className="flex flex-wrap items-center justify-between gap-4 p-5"
              data-testid={`${SESSIONS.row}-${session.id}`}
            >
              <div className="flex items-start gap-4">
                {session.device === "Mobile" ? (
                  <Smartphone className="mt-1 h-4 w-4 text-zinc-500" aria-hidden="true" />
                ) : (
                  <Monitor className="mt-1 h-4 w-4 text-zinc-500" aria-hidden="true" />
                )}
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-sm font-medium text-zinc-900">
                    <span>
                      {session.browser} on {session.device}
                    </span>
                    {session.current ? (
                      <Badge className="rounded-sm bg-emerald-100 font-mono text-[10px] text-emerald-800">
                        this device
                      </Badge>
                    ) : null}
                  </div>
                  <p className="font-mono text-xs text-zinc-500">
                    {session.ip} · last active {formatWhen(session.last_activity)}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive hover:text-destructive"
                disabled={busyId === session.id}
                onClick={() => revoke(session.id, session.current)}
                data-testid={`${SESSIONS.revokeButton}-${session.id}`}
              >
                Revoke
              </Button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
};

export default Sessions;
