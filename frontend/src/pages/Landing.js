import { Link } from "react-router-dom";
import { ArrowRight, FileCheck2, GitCompareArrows, ScanLine, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LANDING } from "@/constants/testIds";

const DISCREPANCIES = [
  "Ghost orders",
  "Missing payments",
  "Duplicate payments",
  "Amount mismatch",
  "Refund mismatch",
  "Settlement difference",
  "Money at risk",
];

const Landing = () => (
  <div className="min-h-screen bg-white" data-testid={LANDING.root}>
    <header className="sticky top-0 z-20 border-b border-zinc-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-[1200px] items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2">
          <ScanLine className="h-5 w-5 text-[#0A0F2C]" aria-hidden="true" />
          <span className="font-display text-lg font-extrabold tracking-tight text-zinc-950">Ganaka</span>
        </div>
        <nav className="flex items-center gap-2">
          <Button asChild variant="ghost" size="sm">
            <Link to="/login" data-testid={LANDING.loginLink}>
              Sign in
            </Link>
          </Button>
          <Button asChild size="sm" className="bg-[#0A0F2C] hover:bg-[#1E293B]">
            <Link to="/register" data-testid={LANDING.registerLink}>
              Create account
            </Link>
          </Button>
        </nav>
      </div>
    </header>

    <section className="bg-[#0A0F2C] text-white">
      <div className="mx-auto grid max-w-[1200px] gap-14 px-6 py-24 md:py-32 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="reveal">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-400">
            Reconciliation for Indian D2C
          </p>
          <h1 className="mt-6 font-display text-5xl font-extrabold leading-[1.02] tracking-tighter sm:text-6xl">
            Shopify says one thing.
            <br />
            Razorpay says another.
          </h1>
          <p className="mt-6 max-w-xl text-base leading-relaxed text-zinc-300">
            Ganaka imports your orders, payments, refunds and settlements, applies deterministic business
            rules, and hands your finance team auditable evidence for every rupee — not a black-box guess.
          </p>
          <div className="mt-10 flex flex-wrap items-center gap-4">
            <Button asChild size="lg" className="bg-white text-[#0A0F2C] hover:bg-zinc-200">
              <Link to="/register" data-testid={LANDING.heroCta}>
                Start reconciling
                <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
              </Link>
            </Button>
            <span className="font-mono text-xs text-zinc-400">No card required · MVP access</span>
          </div>
        </div>
        <div className="reveal border border-white/15 bg-white/5 p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-400">What Ganaka detects</p>
          <ul className="mt-6 space-y-3">
            {DISCREPANCIES.map((item) => (
              <li key={item} className="flex items-center justify-between border-b border-white/10 pb-3 text-sm">
                <span>{item}</span>
                <span className="font-mono text-xs text-zinc-400">rule-backed</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>

    <section className="mx-auto max-w-[1200px] px-6 py-24">
      <div className="grid gap-10 md:grid-cols-3">
        {[
          {
            icon: GitCompareArrows,
            title: "Deterministic matching",
            body: "The same inputs always produce the same result. Every match cites the rule that produced it.",
          },
          {
            icon: ShieldCheck,
            title: "Immutable imports",
            body: "Imported financial records are never edited. Corrections are recorded as reconciliation entries.",
          },
          {
            icon: FileCheck2,
            title: "Evidence, not vibes",
            body: "Each discrepancy carries its evidence, calculation, explanation and recommended action.",
          },
        ].map(({ icon: Icon, title, body }) => (
          <article key={title} className="border border-zinc-200 bg-white p-8">
            <Icon className="h-5 w-5 text-[#0A0F2C]" aria-hidden="true" />
            <h2 className="mt-6 font-display text-xl font-bold tracking-tight text-zinc-900">{title}</h2>
            <p className="mt-3 text-sm leading-relaxed text-zinc-600">{body}</p>
          </article>
        ))}
      </div>
    </section>

    <footer className="border-t border-zinc-200 bg-zinc-50">
      <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-4 px-6 py-10 text-sm text-zinc-600">
        <span className="font-display font-bold text-zinc-900">Ganaka</span>
        <span className="font-mono text-xs">Financial reconciliation · MVP</span>
      </div>
    </footer>
  </div>
);

export default Landing;
