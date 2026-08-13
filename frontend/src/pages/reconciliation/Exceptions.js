import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/StateViews";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

const ReconciliationExceptions = () => {
  const { can } = useAuth();

  const { data: exceptions, isLoading } = useQuery({
    queryKey: ["reconciliation", "exceptions"],
    queryFn: async () => {
      const response = await api.get("/reconciliation/exceptions");
      return response.data;
    },
    enabled: can("reconciliation.run"),
  });

  if (!can("reconciliation.run")) {
    return (
      <div className="space-y-6">
        <EmptyState
          title="Permission required"
          description="You need reconciliation.run permission to view exceptions."
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
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-zinc-950">Exceptions</h1>
        <p className="mt-2 text-sm text-zinc-600">Reconciliation exceptions requiring attention.</p>
      </div>

      {!exceptions?.items?.length ? (
        <Card>
          <CardContent className="pt-6">
            <EmptyState
              title="No exceptions"
              description="All reconciliations are clean. Exceptions will appear here when discrepancies are found."
            />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Exceptions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {exceptions.items.map((exception) => (
                <div key={exception.id} className="border-b border-zinc-100 pb-4 last:border-0">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-red-600" />
                        <p className="font-mono text-sm font-medium text-zinc-900">
                          {exception.exception_type}
                        </p>
                      </div>
                      <p className="text-xs text-zinc-500">
                        Severity: <span className="font-medium">{exception.severity}</span>
                      </p>
                      <p className="text-xs text-zinc-500">
                        Status: <span className="font-medium">{exception.status}</span>
                      </p>
                      {exception.root_cause && (
                        <p className="text-xs text-zinc-600">{exception.root_cause}</p>
                      )}
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-sm text-zinc-900">
                        ₹{exception.amount?.toLocaleString() || "0"}
                      </p>
                      <p className="text-xs text-zinc-500">
                        Order #{exception.shopify_order_id || "—"}
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

export default ReconciliationExceptions;