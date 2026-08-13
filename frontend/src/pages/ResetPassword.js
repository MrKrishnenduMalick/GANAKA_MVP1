import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import AuthLayout from "@/components/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, readError } from "@/lib/api";
import { RESET_PASSWORD } from "@/constants/testIds";

const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const [form, setForm] = useState({ password: "", confirm: "" });
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (form.password !== form.confirm) {
      setError({ message: "Passwords do not match.", details: [] });
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const response = await api.post("/auth/reset-password", { token, password: form.password });
      setMessage(response.data.message);
    } catch (caught) {
      setError(readError(caught));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout title="Set a new password" subtitle="All active sessions are signed out once your password changes.">
      {message ? (
        <div className="space-y-6">
          <p
            className="border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900"
            data-testid={RESET_PASSWORD.message}
          >
            {message}
          </p>
          <Button asChild className="w-full bg-[#0A0F2C] hover:bg-[#1E293B]">
            <Link to="/login" data-testid="reset-password-login-link">
              Go to sign in
            </Link>
          </Button>
        </div>
      ) : (
        <form className="space-y-6" onSubmit={handleSubmit} noValidate>
          {error ? (
            <div className="border border-destructive/30 bg-destructive/5 p-4 text-sm" role="alert" data-testid="reset-password-error">
              {error.message}
              {error.details?.length ? (
                <ul className="mt-2 list-disc space-y-1 pl-4 text-xs">
                  {error.details.map((detail) => (
                    <li key={detail.issue}>{detail.issue}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}

          <div className="space-y-2">
            <Label htmlFor="password">New password</Label>
            <Input
              id="password"
              type="password"
              required
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
              data-testid={RESET_PASSWORD.passwordInput}
            />
            <p className="text-xs text-zinc-500">
              Minimum 12 characters with upper, lower, number and a special character.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirm">Confirm new password</Label>
            <Input
              id="confirm"
              type="password"
              required
              value={form.confirm}
              onChange={(event) => setForm({ ...form, confirm: event.target.value })}
              data-testid={RESET_PASSWORD.confirmInput}
            />
          </div>

          <Button
            type="submit"
            className="w-full bg-[#0A0F2C] hover:bg-[#1E293B]"
            disabled={submitting || !token}
            data-testid={RESET_PASSWORD.submitButton}
          >
            {submitting ? "Updating…" : "Update password"}
          </Button>
          {!token ? <p className="text-xs text-destructive">This reset link is missing its token.</p> : null}
        </form>
      )}
    </AuthLayout>
  );
};

export default ResetPassword;
