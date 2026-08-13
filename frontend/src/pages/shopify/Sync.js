import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/StateViews";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

const ShopifySync = () => {
  const { can } = useAuth();
  const queryClient = useQueryClient();

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ["shopify", "status"],
    queryFn: async () => {
      const response = await api.get("/shopify/status");
      return response.data;
    },
    enabled: can("shopify.connect"),
  });

  const syncMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post("/shopify/sync", { resources: ["orders", "products", "customers"] });
      return response.data;
    },
    onSuccess: (data) => {
      toast({
        title: "Sync started",
        description: `Job ID: ${data.job_id}`,
      });
      queryClient.invalidateQueries(["shopify"]);
    },
    onError: (error) => {
      toast({
        title: "Sync failed",
        description: error.response?.data?.message || "Failed to start sync",
        variant: "destructive",
      });
    },
  });

  if (!can("shopify.connect")) {
    return (
      <div className="space-y-6">
        <EmptyState
          title="Permission required"
          description="You need shopify.connect permission to sync data."
        />
      </div>
    );
  }

  if (statusLoading) {
    return <div className="text-sm text-zinc-500">Loading...</div>;
  }

  const isConnected = status?.connected;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-zinc-950">Sync Data</h1>
        <p className="mt-2 text-sm text-zinc-600">Import orders, products, and customers from Shopify.</p>
      </div>

      {!isConnected ? (
        <Card>
          <CardContent className="pt-6">
            <EmptyState
              title="No Shopify connection"
              description="Connect your Shopify store first to sync data."
            />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Manual Sync</CardTitle>
            <CardDescription>Trigger a full sync of your Shopify data</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <p className="text-xs uppercase tracking-[0.15em] text-zinc-500">Shop</p>
                <p className="mt-1 font-mono text-sm text-zinc-900">{status.connection?.shop_name || "—"}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.15em] text-zinc-500">Domain</p>
                <p className="mt-1 font-mono text-sm text-zinc-900">{status.connection?.shop_domain || "—"}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.15em] text-zinc-500">Status</p>
                <p className="mt-1 font-mono text-sm text-zinc-900">{status.connection?.status || "—"}</p>
              </div>
            </div>
            <Button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="gap-2 bg-[#0A0F2C] hover:bg-[#1E293B]"
            >
              <RefreshCw className="h-4 w-4" />
              {syncMutation.isPending ? "Syncing..." : "Start Sync"}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ShopifySync;