import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, CreditCard, ShoppingBag } from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/StateViews";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { DASHBOARD } from "@/constants/testIds";

const CHART_COLORS = {
  primary: "#0A0F2C",
  secondary: "#71717A",
  success: "#059669",
  warning: "#D97706",
  danger: "#E11D48",
  muted: "#E4E4E7",
};

const Dashboard = () => {
  const { can } = useAuth();

  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ["dashboard", "overview"],
    queryFn: async () => {
      const response = await api.get("/dashboard/overview");
      return response.data;
    },
    enabled: can("dashboard.read"),
  });

  const { data: revenue, isLoading: revenueLoading } = useQuery({
    queryKey: ["dashboard", "revenue"],
    queryFn: async () => {
      const response = await api.get("/dashboard/revenue");
      return response.data;
    },
    enabled: can("dashboard.read"),
  });

  const { data: orders, isLoading: ordersLoading } = useQuery({
    queryKey: ["dashboard", "orders"],
    queryFn: async () => {
      const response = await api.get("/dashboard/orders");
      return response.data;
    },
    enabled: can("dashboard.read"),
  });

  const { data: payments, isLoading: paymentsLoading } = useQuery({
    queryKey: ["dashboard", "payments"],
    queryFn: async () => {
      const response = await api.get("/dashboard/payments");
      return response.data;
    },
    enabled: can("dashboard.read"),
  });

  const { data: refunds, isLoading: refundsLoading } = useQuery({
    queryKey: ["dashboard", "refunds"],
    queryFn: async () => {
      const response = await api.get("/dashboard/refunds");
      return response.data;
    },
    enabled: can("dashboard.read"),
  });

  const { data: settlements, isLoading: settlementsLoading } = useQuery({
    queryKey: ["dashboard", "settlements"],
    queryFn: async () => {
      const response = await api.get("/dashboard/settlements");
      return response.data;
    },
    enabled: can("dashboard.read"),
  });

  const { data: exceptions, isLoading: exceptionsLoading } = useQuery({
    queryKey: ["dashboard", "exceptions"],
    queryFn: async () => {
      const response = await api.get("/dashboard/exceptions");
      return response.data;
    },
    enabled: can("dashboard.read"),
  });

  const { data: matchRate, isLoading: matchRateLoading } = useQuery({
    queryKey: ["dashboard", "match-rate"],
    queryFn: async () => {
      const response = await api.get("/dashboard/match-rate");
      return response.data;
    },
    enabled: can("dashboard.read"),
  });

  const isLoading = overviewLoading || revenueLoading || ordersLoading || paymentsLoading || refundsLoading || settlementsLoading || exceptionsLoading || matchRateLoading;

  if (!can("dashboard.read")) {
    return (
      <div className="space-y-10" data-testid={DASHBOARD.root}>
        <header className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-zinc-500">Dashboard</p>
          <h1 className="font-display text-3xl font-extrabold tracking-tight text-zinc-950">Dashboard</h1>
        </header>
        <EmptyState
          testId={DASHBOARD.emptyState}
          title="Permission required"
          description="You need dashboard.read permission to view this page."
        />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-10" data-testid={DASHBOARD.root}>
        <header className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-zinc-500">Dashboard</p>
          <h1 className="font-display text-3xl font-extrabold tracking-tight text-zinc-950">Loading...</h1>
        </header>
      </div>
    );
  }

  const hasData = overview && (overview.total_orders > 0 || overview.total_payments > 0);

  return (
    <div className="space-y-10" data-testid={DASHBOARD.root}>
      <header className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.15em] text-zinc-500">Dashboard</p>
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-zinc-950">Dashboard</h1>
        <p className="max-w-2xl text-sm leading-relaxed text-zinc-600">
          Financial overview and reconciliation metrics for your workspace.
        </p>
      </header>

      {!hasData ? (
        <EmptyState
          testId={DASHBOARD.emptyState}
          title="No financial data yet"
          description="Ganaka never estimates figures. Once your Shopify store and Razorpay account are connected, imported orders, payments, refunds and settlements will be reconciled here with the rule and evidence behind every discrepancy."
          action={
            <div className="flex flex-wrap gap-3 pt-2">
              <Button className="gap-2 bg-[#0A0F2C] hover:bg-[#1E293B]" disabled data-testid={DASHBOARD.connectShopifyButton}>
                <ShoppingBag className="h-4 w-4" aria-hidden="true" />
                Connect Shopify
              </Button>
              <Button variant="outline" className="gap-2" disabled data-testid="dashboard-connect-razorpay-button">
                <CreditCard className="h-4 w-4" aria-hidden="true" />
                Connect Razorpay
              </Button>
            </div>
          }
        />
      ) : (
        <>
          <section className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium uppercase tracking-[0.15em] text-zinc-500">Revenue</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-mono text-2xl font-medium tracking-tight text-zinc-900">
                  ₹{overview?.revenue?.toLocaleString() || "0"}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium uppercase tracking-[0.15em] text-zinc-500">Orders</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-mono text-2xl font-medium tracking-tight text-zinc-900">
                  {overview?.total_orders?.toLocaleString() || "0"}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium uppercase tracking-[0.15em] text-zinc-500">Payments</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-mono text-2xl font-medium tracking-tight text-zinc-900">
                  ₹{overview?.total_payments?.toLocaleString() || "0"}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium uppercase tracking-[0.15em] text-zinc-500">Refunds</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-mono text-2xl font-medium tracking-tight text-zinc-900">
                  ₹{overview?.total_refunds?.toLocaleString() || "0"}
                </p>
              </CardContent>
            </Card>
          </section>

          <section className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium uppercase tracking-[0.15em] text-zinc-500">Settlements</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-mono text-2xl font-medium tracking-tight text-zinc-900">
                  ₹{overview?.total_settlements?.toLocaleString() || "0"}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium uppercase tracking-[0.15em] text-zinc-500">Match Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-mono text-2xl font-medium tracking-tight text-zinc-900">
                  {overview?.reconciliation_match_rate ? `${(overview.reconciliation_match_rate * 100).toFixed(1)}%` : "—"}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium uppercase tracking-[0.15em] text-zinc-500">Critical Exceptions</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-mono text-2xl font-medium tracking-tight text-zinc-900">
                  {overview?.critical_exceptions?.toLocaleString() || "0"}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium uppercase tracking-[0.15em] text-zinc-500">Connected</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-mono text-2xl font-medium tracking-tight text-zinc-900">
                  {overview?.connected_integrations || "0"}
                </p>
              </CardContent>
            </Card>
          </section>

          <section className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="font-display text-lg font-bold tracking-tight text-zinc-900">Revenue Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={revenue?.daily || []}>
                    <defs>
                      <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.muted} />
                    <XAxis dataKey="date" stroke={CHART_COLORS.secondary} fontSize={12} />
                    <YAxis stroke={CHART_COLORS.secondary} fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "white",
                        border: `1px solid ${CHART_COLORS.muted}`,
                        borderRadius: "6px",
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="total"
                      stroke={CHART_COLORS.primary}
                      fillOpacity={1}
                      fill="url(#colorRevenue)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="font-display text-lg font-bold tracking-tight text-zinc-900">Orders Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={orders?.trend || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.muted} />
                    <XAxis dataKey="date" stroke={CHART_COLORS.secondary} fontSize={12} />
                    <YAxis stroke={CHART_COLORS.secondary} fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "white",
                        border: `1px solid ${CHART_COLORS.muted}`,
                        borderRadius: "6px",
                      }}
                    />
                    <Bar dataKey="count" fill={CHART_COLORS.primary} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="font-display text-lg font-bold tracking-tight text-zinc-900">Payments vs Refunds</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={payments?.trend || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.muted} />
                    <XAxis dataKey="date" stroke={CHART_COLORS.secondary} fontSize={12} />
                    <YAxis stroke={CHART_COLORS.secondary} fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "white",
                        border: `1px solid ${CHART_COLORS.muted}`,
                        borderRadius: "6px",
                      }}
                    />
                    <Line type="monotone" dataKey="total" stroke={CHART_COLORS.primary} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="font-display text-lg font-bold tracking-tight text-zinc-900">Match Rate Trend</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={matchRate?.trend || []}>
                    <defs>
                      <linearGradient id="colorMatch" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={CHART_COLORS.success} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={CHART_COLORS.success} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.muted} />
                    <XAxis dataKey="date" stroke={CHART_COLORS.secondary} fontSize={12} />
                    <YAxis stroke={CHART_COLORS.secondary} fontSize={12} domain={[0, 1]} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "white",
                        border: `1px solid ${CHART_COLORS.muted}`,
                        borderRadius: "6px",
                      }}
                      formatter={(value) => `${(value * 100).toFixed(1)}%`}
                    />
                    <Area
                      type="monotone"
                      dataKey="rate"
                      stroke={CHART_COLORS.success}
                      fillOpacity={1}
                      fill="url(#colorMatch)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </section>
        </>
      )}
    </div>
  );
};

export default Dashboard;