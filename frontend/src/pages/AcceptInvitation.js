import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { MailPlus } from "lucide-react";
import AuthLayout from "@/components/AuthLayout";
import { Button } from "@/components/ui/button";
import { api, readError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { INVITATION } from "@/constants/testIds";

const AcceptInvitation = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const navigate = useNavigate();
  const { user, loadMe, switchWorkspace } = useAuth();
  const [state, setState] = useState({ status: "idle", message: "" });

  const handleAccept = async () => {
    setState({ status: "working", message: "" });
    try {
      const response = await api.post("/workspaces/invitations/accept", { token });
      await switchWorkspace(response.data.id);
      await loadMe();
      setState({ status: "success", message: `You joined ${response.data.name}.` });
      navigate("/app", { replace: true });
    } catch (caught) {
      setState({ status: "error", message: readError(caught).message });
    }
  };

  return (
    <AuthLayout
      title="Join a workspace"
      subtitle={`Invitations are bound to the invited email address${user ? ` (${user.email})` : ""}.`}
    >
      <div className="space-y-6" data-testid={INVITATION.root}>
        <MailPlus className="h-8 w-8 text-[#0A0F2C]" aria-hidden="true" />
        {state.message ? (
          <p
            className={`border p-4 text-sm ${
              state.status === "error"
                ? "border-destructive/30 bg-destructive/5"
                : "border-emerald-200 bg-emerald-50 text-emerald-900"
            }`}
            data-testid={INVITATION.message}
            role={state.status === "error" ? "alert" : undefined}
          >
            {state.message}
          </p>
        ) : null}
        <Button
          className="w-full bg-[#0A0F2C] hover:bg-[#1E293B]"
          onClick={handleAccept}
          disabled={!token || state.status === "working"}
          data-testid={INVITATION.acceptButton}
        >
          {state.status === "working" ? "Joining…" : "Accept invitation"}
        </Button>
        {!token ? <p className="text-xs text-destructive">This invitation link is missing its token.</p> : null}
        <Link to="/app" className="block text-sm text-zinc-600 underline">
          Skip for now
        </Link>
      </div>
    </AuthLayout>
  );
};

export default AcceptInvitation;
