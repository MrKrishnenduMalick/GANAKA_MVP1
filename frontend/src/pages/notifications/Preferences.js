import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/StateViews";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

const NotificationsPreferences = () => {
  const { can } = useAuth();
  const queryClient = useQueryClient();

  const { data: preferences, isLoading } = useQuery({
    queryKey: ["notifications", "preferences"],
    queryFn: async () => {
      const response = await api.get("/notifications/preferences");
      return response.data;
    },
    enabled: can("workspace.read"),
  });

  const updateMutation = useMutation({
    mutationFn: async (data) => {
      const response = await api.patch("/notifications/preferences", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries(["notifications", "preferences"]);
      toast({
        title: "Preferences updated",
        description: "Notification preferences have been saved",
      });
    },
    onError: (error) => {
      toast({
        title: "Update failed",
        description: error.response?.data?.message || "Failed to update preferences",
        variant: "destructive",
      });
    },
  });

  if (!can("workspace.read")) {
    return (
      <div className="space-y-6">
        <EmptyState
          title="Permission required"
          description="You need workspace.read permission to view notifications."
        />
      </div>
    );
  }

  if (isLoading) {
    return <div className="text-sm text-zinc-500">Loading...</div>;
  }

  const handleToggle = (key) => {
    updateMutation.mutate({ [key]: !preferences[key] });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-zinc-950">Notifications</h1>
        <p className="mt-2 text-sm text-zinc-600">Manage your notification preferences.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Notification Preferences
          </CardTitle>
          <CardDescription>Choose what notifications you want to receive</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-zinc-900">Critical Reconciliation Failures</p>
                <p className="text-xs text-zinc-500">Get notified when reconciliation fails</p>
              </div>
              <Button
                variant={preferences?.critical_reconciliation_failures ? "default" : "outline"}
                size="sm"
                onClick={() => handleToggle("critical_reconciliation_failures")}
              >
                {preferences?.critical_reconciliation_failures ? "Enabled" : "Disabled"}
              </Button>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-zinc-900">Failed Shopify Sync</p>
                <p className="text-xs text-zinc-500">Get notified when Shopify sync fails</p>
              </div>
              <Button
                variant={preferences?.failed_shopify_sync ? "default" : "outline"}
                size="sm"
                onClick={() => handleToggle("failed_shopify_sync")}
              >
                {preferences?.failed_shopify_sync ? "Enabled" : "Disabled"}
              </Button>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-zinc-900">Failed Razorpay Sync</p>
                <p className="text-xs text-zinc-500">Get notified when Razorpay sync fails</p>
              </div>
              <Button
                variant={preferences?.failed_razorpay_sync ? "default" : "outline"}
                size="sm"
                onClick={() => handleToggle("failed_razorpay_sync")}
              >
                {preferences?.failed_razorpay_sync ? "Enabled" : "Disabled"}
              </Button>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-zinc-900">OAuth Expiration</p>
                <p className="text-xs text-zinc-500">Get notified before OAuth tokens expire</p>
              </div>
              <Button
                variant={preferences?.oauth_expiration ? "default" : "outline"}
                size="sm"
                onClick={() => handleToggle("oauth_expiration")}
              >
                {preferences?.oauth_expiration ? "Enabled" : "Disabled"}
              </Button>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-zinc-900">Webhook Failures</p>
                <p className="text-xs text-zinc-500">Get notified when webhooks fail</p>
              </div>
              <Button
                variant={preferences?.webhook_failures ? "default" : "outline"}
                size="sm"
                onClick={() => handleToggle("webhook_failures")}
              >
                {preferences?.webhook_failures ? "Enabled" : "Disabled"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default NotificationsPreferences;