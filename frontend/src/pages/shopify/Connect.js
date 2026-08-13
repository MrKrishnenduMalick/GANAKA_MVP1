import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Store, Unplug } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/StateViews";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

const ShopifyConnect = () => {
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const [shopDomain, setShopDomain] = useState("");

  const { data: status, isLoading } = useQuery({
    queryKey: ["shopify", "status"],
    queryFn: async () => {
      const response = await api.get("/shopify/status");
      return response.data;
    },
    enabled: can("shopify.connect"),
  });

  const connectMutation = useMutation({
    mutationFn: async (domain) => {
      const response = await api.post("/shopify/install", { shop_domain: domain });
      return response.data;
    },
    onSuccess: (data) => {
      window.location.href = data.install_url;
    },
    onError: (error) => {
      toast({
        title: "Connection failed",
        description: error.response?.data?.message || "Failed to initiate Shopify connection",
        variant: "destructive",
      });
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: async () => {
      const response = await api.delete("/shopify/disconnect");
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries(["shopify", "status"]);
      toast({
        title: "Disconnected",
        description: "Shopify store has been disconnected",
      });
    },
  });

  if (!can("shopify.connect")) {
    return (
      <div className="space-y-6">
        <EmptyState
          title="Permission required"
          description="You need shopify.connect permission to manage Shopify integration."
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
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-zinc-950">Shopify</h1>
        <p className="mt-2 text-sm text-zinc-600">Connect and manage your Shopify store integration.</p>
      </div>

      {isConnected ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Store className="h-5 w-5" />
              Connected Store
            </CardTitle>
            <CardDescription>Your Shopify store is currently connected</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-xs uppercase tracking-[0.15em] text-zinc-500">Shop Name</p>
                <p className="mt-1 font-mono text-sm text-zinc-900">{status.connection?.shop_name || "—"}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.15em] text-zinc-500">Shop Domain</p>
                <p className="mt-1 font-mono text-sm text-zinc-900">{status.connection?.shop_domain || "—"}</p>
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
              Disconnect Store
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Connect Shopify Store</CardTitle>
            <CardDescription>Connect your Shopify store to import orders, products, and customers</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-900">Shop Domain</label>
              <input
                type="text"
                value={shopDomain}
                onChange={(e) => setShopDomain(e.target.value)}
                placeholder="your-store.myshopify.com"
                className="w-full rounded-md border border-zinc-200 px-3 py-2 text-sm focus:border-[#0A0F2C] focus:outline-none focus:ring-2 focus:ring-[#0A0F2C] focus:ring-offset-2"
              />
            </div>
            <Button
              onClick={() => connectMutation.mutate(shopDomain)}
              disabled={!shopDomain || connectMutation.isPending}
              className="gap-2 bg-[#0A0F2C] hover:bg-[#1E293B]"
            >
              <Store className="h-4 w-4" />
              Connect Store
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ShopifyConnect;