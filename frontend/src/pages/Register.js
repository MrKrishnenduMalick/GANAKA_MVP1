import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Check, MailCheck, X } from "lucide-react";
import AuthLayout from "@/components/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, readError } from "@/lib/api";
import { REGISTER } from "@/constants/testIds";

const RULES = [
  { key: "length", label: "At least 12 characters", test: (value) => value.length >= 12 },
  { key: "upper", label: "One uppercase letter", test: (value) => /[A-Z]/.test(value) },
  { key: "lower", label: "One lowercase letter", test: (value) => /[a-z]/.test(value) },
  { key: "number", label: "One number", test: (value) => /[0-9]/.test(value) },
  { key: "special", label: "One special character", test: (value) => /[^A-Za-z0-9]/.test(value) },
];

const Register = () => {
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    workspace_name: "",
    password: "",
    confirm: "",
  });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  const checks = useMemo(() => RULES.map((rule) => ({ ...rule, ok: rule.test(form.password) })), [form.password]);
  const passwordOk = checks.every((check) => check.ok);
  const matches = form.password.length > 0 && form.password === form.confirm;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!passwordOk || !matches) {
      setError({ code: "VALIDATION-001", message: "Fix the highlighted password requirements first." });
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.post("/auth/register", {
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
        workspace_name: form.workspace_name.trim() || undefined,
      });
      setSent(true);
    } catch (caught) {
      setError(readError(caught));
    } finally {
      setSubmitting(false);
    }
  };

  if (sent) {
    return (
      <AuthLayout
        title="Check your email"
        subtitle="We sent a verification link. It expires in 24 hours and can be used once."
      >
        <div className="space-y-6" data-testid={REGISTER.successPanel}>
          <MailCheck className="h-8 w-8 text-emerald-600" aria-hidden="true" />
          <p className="text-sm leading-relaxed text-zinc-600">
            Once verified you can sign in and connect your Shopify store. If the email does not arrive,
            check spam or start a password reset — for security we respond the same way whether or not an
            account already exists.
          </p>
          <Button asChild className="w-full bg-[#0A0F2C] hover:bg-[#1E293B]">
            <Link to="/login" data-testid={REGISTER.loginLink}>
              Go to sign in
            </Link>
          </Button>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Create your Ganaka workspace"
      subtitle="You will own the workspace and can invite your finance team afterwards."
      footer={
        <span>
          Already have an account?{" "}
          <Link className="font-semibold text-[#0A0F2C] underline" to="/login" data-testid={REGISTER.loginLink}>
            Sign in
          </Link>
        </span>
      }
    >
      <form className="space-y-6" onSubmit={handleSubmit} noValidate>
        {error ? (
          <div
            className="flex items-start gap-3 border border-destructive/30 bg-destructive/5 p-4 text-sm text-zinc-800"
            role="alert"
            data-testid="register-error-message"
          >
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" aria-hidden="true" />
            <span>
              {error.message}
              {error.details?.length ? (
                <ul className="mt-2 list-disc space-y-1 pl-4 text-xs">
                  {error.details.map((detail) => (
                    <li key={`${detail.field}-${detail.issue}`}>{detail.issue}</li>
                  ))}
                </ul>
              ) : null}
            </span>
          </div>
        ) : null}

        <div className="space-y-2">
          <Label htmlFor="full_name">Full name</Label>
          <Input
            id="full_name"
            required
            value={form.full_name}
            onChange={(event) => setForm({ ...form, full_name: event.target.value })}
            data-testid={REGISTER.nameInput}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="email">Work email</Label>
          <Input
            id="email"
            type="email"
            required
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
            data-testid={REGISTER.emailInput}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="workspace_name">Workspace name</Label>
          <Input
            id="workspace_name"
            placeholder="Your brand"
            value={form.workspace_name}
            onChange={(event) => setForm({ ...form, workspace_name: event.target.value })}
            data-testid={REGISTER.workspaceNameInput}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            required
            value={form.password}
            onChange={(event) => setForm({ ...form, password: event.target.value })}
            data-testid={REGISTER.passwordInput}
          />
          <ul className="mt-3 grid gap-1.5" data-testid={REGISTER.passwordChecklist}>
            {checks.map((check) => (
              <li key={check.key} className="flex items-center gap-2 text-xs">
                {check.ok ? (
                  <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                ) : (
                  <X className="h-3.5 w-3.5 text-zinc-400" aria-hidden="true" />
                )}
                <span className={check.ok ? "text-zinc-700" : "text-zinc-500"}>{check.label}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-2">
          <Label htmlFor="confirm">Confirm password</Label>
          <Input
            id="confirm"
            type="password"
            required
            value={form.confirm}
            onChange={(event) => setForm({ ...form, confirm: event.target.value })}
            data-testid={REGISTER.passwordConfirmInput}
          />
          {form.confirm && !matches ? (
            <p className="text-xs text-destructive" data-testid={REGISTER.confirmError}>
              Passwords do not match.
            </p>
          ) : null}
        </div>

        <Button
          type="submit"
          className="w-full bg-[#0A0F2C] hover:bg-[#1E293B]"
          disabled={submitting}
          data-testid={REGISTER.submitButton}
        >
          {submitting ? "Creating account…" : "Create account"}
        </Button>
      </form>
    </AuthLayout>
  );
};

export default Register;
