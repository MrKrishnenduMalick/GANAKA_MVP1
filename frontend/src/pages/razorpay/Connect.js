import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CreditCard, Unplug } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState } from "@/components/StateViews";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

const RazorpayConnect = () => {
  const { can } = useAuth();
  const queryClient = useQueryClient();
  // ARCH-AUDIT-001 fix: each workspace connects its OWN Razorpay account now
  // instead of the platform sharing a single deployment-wide credential, so
  // the form collects that workspace's key_id/key_secret (and optional
  // webhook_secret) instead of a single no-input "Connect" button.
  const [form, setForm] = useState({ key_id: "", key_secret: "", webhook_secret: "" });

  const { data: status, isLoading } = useQuery({
    queryKey: ["razorpay", "status"],
    queryFn: async () => {
      const response = await api.get("/razorpay/status");
      return response.data;
    },
    enabled: can("razorpay.connect"),
  });

  const connectMutation = useMutation({
    mutationFn: async () => {
      const payload = { key_id: form.key_id, key_secret: form.key_secret };
      if (form.webhook_secret) payload.webhook_secret = form.webhook_secret;
      const response = await api.post("/razorpay/connect", payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries(["razorpay", "status"]);
      setForm({ key_id: "", key_secret: "", webhook_secret: "" });
      toast({
        title: "Connected",
        description: "Razorpay account has been connected",
      });
    },
    onError: (error) => {
      toast({
        title: "Connection failed",
        description: error.response?.data?.message || "Failed to connect Razorpay",
        variant: "destructive",
      });
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: async () => {
      const response = await api.delete("/razorpay/disconnect");
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries(["razorpay", "status"]);
      toast({
        title: "Disconnected",
        description: "Razorpay account has been disconnected",
      });
    },
  });

  if (!can("razorpay.connect")) {
    return (
      <div className="space-y-6">
        <EmptyState
          title="Permission required"
          description="You need razorpay.connect permission to manage Razorpay integration."
        />
      </div>
    );
  }

  if (isLoading) {
    return <div className="text-sm text-zinc-500">Loading...</div>;
  }

  const isConnected = status?.connected;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-zinc-950">Razorpay</h1>
        <p className="mt-2 text-sm text-zinc-600">Connect and manage your Razorpay account integration.</p>
      </div>

      {isConnected ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Connected Account
            </CardTitle>
            <CardDescription>Your Razorpay account is currently connected</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-xs uppercase tracking-[0.15em] text-zinc-500">Key ID</p>
                <p className="mt-1 font-mono text-sm text-zinc-900">{status.connection?.key_id || "—"}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.15em] text-zinc-500">Account Name</p>
                <p className="mt-1 font-mono text-sm text-zinc-900">{status.connection?.account_name || "—"}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.15em] text-zinc-500">Status</p>
                <p className="mt-1 font-mono text-sm text-zinc-900">{status.connection?.status || "—"}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.15em] text-zinc-500">Connected At</p>
                <p className="mt-1 font-mono text-sm text-zinc-900">
                  {status.connection?.installed_at ? new Date(status.connection.installed_at).toLocaleString() : "—"}
                </p>
              </div>
            </div>
            <Button
              variant="destructive"
              onClick={() => disconnectMutation.mutate()}
              disabled={disconnectMutation.isPending}
              className="gap-2"
            >
              <Unplug className="h-4 w-4" />
              Disconnect Account
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Connect Razorpay</CardTitle>
            <CardDescription>
              Connect your own Razorpay account (from your Razorpay Dashboard → Settings → API Keys) to
              import payments, refunds, and settlements. Your key secret is encrypted at rest and never
              shown again after connecting.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="razorpay-key-id">Key ID</Label>
                <Input
                  id="razorpay-key-id"
                  placeholder="rzp_live_xxxxxxxxxxxx"
                  value={form.key_id}
                  onChange={(event) => setForm((prev) => ({ ...prev, key_id: event.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="razorpay-key-secret">Key Secret</Label>
                <Input
                  id="razorpay-key-secret"
                  type="password"
                  placeholder="Your Razorpay key secret"
                  value={form.key_secret}
                  onChange={(event) => setForm((prev) => ({ ...prev, key_secret: event.target.value }))}
                />
              </div>
              <div className="space-y-1.5 md:col-span-2">
                <Label htmlFor="razorpay-webhook-secret">Webhook Secret (optional, needed for real-time updates)</Label>
                <Input
                  id="razorpay-webhook-secret"
                  type="password"
                  placeholder="Your Razorpay webhook secret"
                  value={form.webhook_secret}
                  onChange={(event) => setForm((prev) => ({ ...prev, webhook_secret: event.target.value }))}
                />
              </div>
            </div>
            <Button
              onClick={() => connectMutation.mutate()}
              disabled={connectMutation.isPending || !form.key_id || !form.key_secret}
              className="gap-2 bg-[#0A0F2C] hover:bg-[#1E293B]"
            >
              <CreditCard className="h-4 w-4" />
              Connect Razorpay
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default RazorpayConnect;