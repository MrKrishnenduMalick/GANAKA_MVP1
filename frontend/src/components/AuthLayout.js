import { Link } from "react-router-dom";
import { ScanLine } from "lucide-react";

const AuthLayout = ({ title, subtitle, children, footer }) => (
  <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[1.05fr_1fr]">
    <aside className="hidden flex-col justify-between bg-[#0A0F2C] p-12 text-white lg:flex">
      <Link to="/" className="flex items-center gap-2" data-testid="auth-layout-home-link">
        <ScanLine className="h-5 w-5" aria-hidden="true" />
        <span className="font-display text-lg font-extrabold tracking-tight">Ganaka</span>
      </Link>
      <div className="max-w-md space-y-6">
        <p className="font-display text-4xl font-extrabold leading-[1.05] tracking-tight">
          Every rupee accounted for, with the evidence attached.
        </p>
        <p className="text-sm leading-relaxed text-zinc-300">
          Ganaka reconciles Shopify orders against Razorpay payments, refunds and settlements — then shows
          you the rule, the calculation and the source record behind every discrepancy.
        </p>
      </div>
      <dl className="grid grid-cols-3 gap-6 border-t border-white/15 pt-6 text-xs uppercase tracking-[0.15em] text-zinc-400">
        <div>
          <dt>Deterministic</dt>
          <dd className="mt-1 font-mono text-base text-white">Rules</dd>
        </div>
        <div>
          <dt>Immutable</dt>
          <dd className="mt-1 font-mono text-base text-white">Imports</dd>
        </div>
        <div>
          <dt>Full</dt>
          <dd className="mt-1 font-mono text-base text-white">Audit</dd>
        </div>
      </dl>
    </aside>
    <main className="grid-paper flex items-center justify-center bg-zinc-50 px-6 py-16">
      <div className="w-full max-w-md">
        <div className="border border-zinc-200 bg-white p-8">
          <div className="rule-heavy -mx-8 -mt-8 mb-8" />
          <h1 className="font-display text-2xl font-extrabold tracking-tight text-zinc-950">{title}</h1>
          {subtitle ? <p className="mt-2 text-sm leading-relaxed text-zinc-600">{subtitle}</p> : null}
          <div className="mt-8">{children}</div>
        </div>
        {footer ? <div className="mt-6 text-sm text-zinc-600">{footer}</div> : null}
      </div>
    </main>
  </div>
);

export default AuthLayout;
