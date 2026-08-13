import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import AuthLayout from "@/components/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { readError } from "@/lib/api";
import { LOGIN } from "@/constants/testIds";

const Login = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(form.email.trim(), form.password);
      navigate(searchParams.get("next") || "/app", { replace: true });
    } catch (caught) {
      setError(readError(caught));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Sign in to Ganaka"
      subtitle="Use the email address your workspace was created with."
      footer={
        <span>
          New to Ganaka?{" "}
          <Link className="font-semibold text-[#0A0F2C] underline" to="/register" data-testid={LOGIN.registerLink}>
            Create an account
          </Link>
        </span>
      }
    >
      <form className="space-y-6" onSubmit={handleSubmit} noValidate>
        {error ? (
          <div
            className="flex items-start gap-3 border border-destructive/30 bg-destructive/5 p-4 text-sm text-zinc-800"
            role="alert"
            data-testid={LOGIN.errorMessage}
          >
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" aria-hidden="true" />
            <span>
              {error.message}
              <span className="mt-1 block font-mono text-[11px] text-zinc-500">{error.code}</span>
            </span>
          </div>
        ) : null}

        <div className="space-y-2">
          <Label htmlFor="email">Email address</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
            data-testid={LOGIN.emailInput}
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="password">Password</Label>
            <Link
              to="/forgot-password"
              className="text-xs text-zinc-600 underline"
              data-testid={LOGIN.forgotPasswordLink}
            >
              Forgot password?
            </Link>
          </div>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={form.password}
            onChange={(event) => setForm({ ...form, password: event.target.value })}
            data-testid={LOGIN.passwordInput}
          />
        </div>

        <Button
          type="submit"
          className="w-full bg-[#0A0F2C] hover:bg-[#1E293B]"
          disabled={submitting}
          data-testid={LOGIN.submitButton}
        >
          {submitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </AuthLayout>
  );
};

export default Login;
