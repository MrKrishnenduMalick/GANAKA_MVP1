import { useQuery } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/StateViews";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

const ReconciliationResults = () => {
  const { can } = useAuth();

  const { data: results, isLoading } = useQuery({
    queryKey: ["reconciliation", "results"],
    queryFn: async () => {
      const response = await api.get("/reconciliation/results");
      return response.data;
    },
    enabled: can("reconciliation.run"),
  });

  if (!can("reconciliation.run")) {
    return (
      <div className="space-y-6">
        <EmptyState
          title="Permission required"
          description="You need reconciliation.run permission to view results."
        />
      </div>
    );
  }

  if (isLoading) {
    return <div className="text-sm text-zinc-500">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-zinc-950">Reconciliation Results</h1>
        <p className="mt-2 text-sm text-zinc-600">View reconciliation results for your workspace.</p>
      </div>

      {!results?.items?.length ? (
        <Card>
          <CardContent className="pt-6">
            <EmptyState
              title="No results yet"
              description="Run reconciliation to see results here."
            />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {results.items.map((result) => (
                <div key={result.id} className="border-b border-zinc-100 pb-4 last:border-0">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <p className="font-mono text-sm font-medium text-zinc-900">
                        Order #{result.shopify_order_id || "—"}
                      </p>
                      <p className="text-xs text-zinc-500">
                        Status: <span className="font-medium">{result.match_status}</span>
                      </p>
                      <p className="text-xs text-zinc-500">
                        Confidence: <span className="font-medium">{(result.confidence * 100).toFixed(0)}%</span>
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-sm text-zinc-900">
                        ₹{result.amount_shopify?.toLocaleString() || "0"}
                      </p>
                      <p className="text-xs text-zinc-500">
                        Diff: ₹{result.amount_difference?.toLocaleString() || "0"}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ReconciliationResults;