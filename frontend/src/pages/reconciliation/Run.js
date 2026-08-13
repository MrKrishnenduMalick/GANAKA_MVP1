import { useMutation } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/StateViews";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

const ReconciliationRun = () => {
  const { can } = useAuth();

  const runMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post("/reconciliation/run");
      return response.data;
    },
    onSuccess: (data) => {
      toast({
        title: "Reconciliation started",
        description: `Job ID: ${data.job_id}`,
      });
    },
    onError: (error) => {
      toast({
        title: "Reconciliation failed",
        description: error.response?.data?.message || "Failed to run reconciliation",
        variant: "destructive",
      });
    },
  });

  if (!can("reconciliation.run")) {
    return (
      <div className="space-y-6">
        <EmptyState
          title="Permission required"
          description="You need reconciliation.run permission to run reconciliation."
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-zinc-950">Run Reconciliation</h1>
        <p className="mt-2 text-sm text-zinc-600">Run the reconciliation engine to match orders with payments.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Reconciliation Engine</CardTitle>
          <CardDescription>
            This will match Shopify orders with Razorpay payments, detect discrepancies, and generate exceptions.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <p className="text-sm text-zinc-600">
              The reconciliation engine will:
            </p>
            <ul className="list-disc list-inside text-sm text-zinc-600 space-y-1">
              <li>Match orders with payments</li>
              <li>Detect ghost orders and missing payments</li>
              <li>Identify duplicate payments</li>
              <li>Find settlement mismatches</li>
              <li>Detect refund mismatches</li>
            </ul>
          </div>
          <Button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="gap-2 bg-[#0A0F2C] hover:bg-[#1E293B]"
          >
            <Play className="h-4 w-4" />
            {runMutation.isPending ? "Running..." : "Run Reconciliation"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

export default ReconciliationRun;