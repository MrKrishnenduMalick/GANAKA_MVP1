import { useState } from "react";
import { Link } from "react-router-dom";
import AuthLayout from "@/components/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, readError } from "@/lib/api";
import { FORGOT_PASSWORD, LOGIN } from "@/constants/testIds";

const ForgotPassword = () => {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const response = await api.post("/auth/forgot-password", { email: email.trim() });
      setMessage(response.data.message);
    } catch (caught) {
      setError(readError(caught).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Reset your password"
      subtitle="We will email a single-use link that expires in 15 minutes."
      footer={
        <Link className="font-semibold text-[#0A0F2C] underline" to="/login" data-testid={LOGIN.submitButton + "-back"}>
          Back to sign in
        </Link>
      }
    >
      <form className="space-y-6" onSubmit={handleSubmit} noValidate>
        {message ? (
          <p
            className="border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900"
            data-testid={FORGOT_PASSWORD.message}
          >
            {message}
          </p>
        ) : null}
        {error ? (
          <p className="border border-destructive/30 bg-destructive/5 p-4 text-sm" role="alert">
            {error}
          </p>
        ) : null}

        <div className="space-y-2">
          <Label htmlFor="email">Email address</Label>
          <Input
            id="email"
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            data-testid={FORGOT_PASSWORD.emailInput}
          />
        </div>

        <Button
          type="submit"
          className="w-full bg-[#0A0F2C] hover:bg-[#1E293B]"
          disabled={submitting}
          data-testid={FORGOT_PASSWORD.submitButton}
        >
          {submitting ? "Sending…" : "Send reset link"}
        </Button>
      </form>
    </AuthLayout>
  );
};

export default ForgotPassword;
