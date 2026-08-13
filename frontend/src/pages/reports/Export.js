import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/StateViews";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

const ReportsExport = () => {
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const [format, setFormat] = useState("csv");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const exportMutation = useMutation({
    mutationFn: async (type) => {
      const response = await api.post(`/exports/${type}`, {
        format,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      });
      return response.data;
    },
    onSuccess: async (data) => {
      // ARCH-AUDIT-002 fix: download_url now resolves to a real, generated
      // file, so actually fetch and download it instead of only naming it in
      // a toast. The endpoint requires the same bearer auth as every other
      // API call, so it's fetched as a blob through the authenticated `api`
      // client rather than a plain <a href>.
      try {
        const fileResponse = await api.get(`/exports/download/${data.filename}`, { responseType: "blob" });
        const blobUrl = window.URL.createObjectURL(fileResponse.data);
        const link = document.createElement("a");
        link.href = blobUrl;
        link.download = data.filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(blobUrl);
        toast({
          title: "Export ready",
          description: `Downloaded ${data.filename} (${data.record_count} record${data.record_count === 1 ? "" : "s"})`,
        });
      } catch (error) {
        toast({
          title: "Export generated, download failed",
          description: error.response?.data?.message || "The file was generated but could not be downloaded automatically.",
          variant: "destructive",
        });
      }
    },
    onError: (error) => {
      toast({
        title: "Export failed",
        description: error.response?.data?.message || "Failed to export",
        variant: "destructive",
      });
    },
  });

  if (!can("report.export")) {
    return (
      <div className="space-y-6">
        <EmptyState
          title="Permission required"
          description="You need report.export permission to export data."
        />
      </div>
    );
  }

  const exportTypes = [
    { key: "reconciliation-results", label: "Reconciliation Results", description: "Export all reconciliation results" },
    { key: "exceptions", label: "Exceptions", description: "Export reconciliation exceptions" },
    { key: "dashboard-summary", label: "Dashboard Summary", description: "Export dashboard summary" },
    { key: "payments", label: "Payments", description: "Export payment records" },
    { key: "refunds", label: "Refunds", description: "Export refund records" },
    { key: "settlements", label: "Settlements", description: "Export settlement records" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-zinc-950">Reports</h1>
        <p className="mt-2 text-sm text-zinc-600">Export data for analysis and record-keeping.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Export Options</CardTitle>
          <CardDescription>Select format and date range for your export</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-900">Format</label>
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value)}
                className="w-full rounded-md border border-zinc-200 px-3 py-2 text-sm focus:border-[#0A0F2C] focus:outline-none focus:ring-2 focus:ring-[#0A0F2C] focus:ring-offset-2"
              >
                <option value="csv">CSV</option>
                <option value="excel">Excel</option>
                <option value="pdf">PDF</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-900">Date From</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full rounded-md border border-zinc-200 px-3 py-2 text-sm focus:border-[#0A0F2C] focus:outline-none focus:ring-2 focus:ring-[#0A0F2C] focus:ring-offset-2"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-900">Date To</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full rounded-md border border-zinc-200 px-3 py-2 text-sm focus:border-[#0A0F2C] focus:outline-none focus:ring-2 focus:ring-[#0A0F2C] focus:ring-offset-2"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {exportTypes.map((type) => (
          <Card key={type.key}>
            <CardHeader>
              <CardTitle className="text-base">{type.label}</CardTitle>
              <CardDescription>{type.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                onClick={() => exportMutation.mutate(type.key)}
                disabled={exportMutation.isPending}
                className="w-full gap-2 bg-[#0A0F2C] hover:bg-[#1E293B]"
              >
                <Download className="h-4 w-4" />
                Export
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default ReportsExport;