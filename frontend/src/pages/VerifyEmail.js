import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, XCircle } from "lucide-react";
import AuthLayout from "@/components/AuthLayout";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/StateViews";
import { api, readError } from "@/lib/api";
import { VERIFY_EMAIL } from "@/constants/testIds";

const VerifyEmail = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const [state, setState] = useState({ status: "loading", message: "" });
  const requested = useRef(false);

  useEffect(() => {
    if (requested.current) return;
    requested.current = true;
    if (!token) {
      setState({ status: "error", message: "This verification link is missing its token." });
      return;
    }
    api
      .get("/auth/verify-email", { params: { token } })
      .then((response) => setState({ status: "success", message: response.data.message }))
      .catch((caught) => setState({ status: "error", message: readError(caught).message }));
  }, [token]);

  return (
    <AuthLayout title="Email verification" subtitle="Confirming your email address.">
      <div className="space-y-6" data-testid={VERIFY_EMAIL.root}>
        {state.status === "loading" ? <LoadingState label="Verifying your link" /> : null}
        {state.status === "success" ? (
          <div className="flex items-start gap-3" data-testid={VERIFY_EMAIL.status}>
            <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-600" aria-hidden="true" />
            <p className="text-sm text-zinc-700">{state.message}</p>
          </div>
        ) : null}
        {state.status === "error" ? (
          <div className="flex items-start gap-3" data-testid={VERIFY_EMAIL.status} role="alert">
            <XCircle className="mt-0.5 h-5 w-5 text-destructive" aria-hidden="true" />
            <p className="text-sm text-zinc-700">{state.message}</p>
          </div>
        ) : null}

        <Button asChild className="w-full bg-[#0A0F2C] hover:bg-[#1E293B]">
          <Link to="/login" data-testid={VERIFY_EMAIL.loginLink}>
            Continue to sign in
          </Link>
        </Button>
      </div>
    </AuthLayout>
  );
};

export default VerifyEmail;
