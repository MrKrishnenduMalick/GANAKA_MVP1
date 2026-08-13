import { useCallback, useEffect, useState } from "react";
import { Check, Minus } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ErrorState, LoadingState } from "@/components/StateViews";
import { api, readError } from "@/lib/api";
import { ROLES } from "@/constants/testIds";

const ROLE_ORDER = ["OWNER", "ADMIN", "FINANCE", "ACCOUNTANT", "VIEWER"];

const Roles = () => {
  const [state, setState] = useState({ status: "loading", error: null });
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);

  const load = useCallback(async () => {
    setState({ status: "loading", error: null });
    try {
      const [roleResponse, permissionResponse] = await Promise.all([
        api.get("/roles", { params: { page: 1, size: 100, sort: "name,asc" } }),
        api.get("/permissions", { params: { page: 1, size: 100, sort: "code,asc" } }),
      ]);
      const ordered = [...roleResponse.data.items].sort((a, b) => {
        const indexA = ROLE_ORDER.indexOf(a.name);
        const indexB = ROLE_ORDER.indexOf(b.name);
        return (indexA === -1 ? 99 : indexA) - (indexB === -1 ? 99 : indexB);
      });
      setRoles(ordered);
      setPermissions(permissionResponse.data.items);
      setState({ status: "ready", error: null });
    } catch (caught) {
      setState({ status: "error", error: readError(caught).message });
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (state.status === "loading") return <LoadingState label="Loading roles" />;
  if (state.status === "error") return <ErrorState message={state.error} onRetry={load} />;

  return (
    <div className="space-y-8" data-testid={ROLES.root}>
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.15em] text-zinc-500">Settings</p>
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-zinc-950">Roles &amp; permissions</h1>
        <p className="max-w-3xl text-sm text-zinc-600">
          Permissions are resolved server-side on every request. The default roles below are read-only; custom
          roles are available on the PRO and ENTERPRISE plans.
        </p>
      </header>

      <div className="overflow-x-auto border border-zinc-200 bg-white">
        <Table data-testid={ROLES.matrix}>
          <TableHeader className="bg-zinc-50/60">
            <TableRow>
              <TableHead className="min-w-[240px]">Permission</TableHead>
              {roles.map((role) => (
                <TableHead key={role.id} className="text-center font-mono text-[11px]">
                  {role.name}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {permissions.map((permission) => (
              <TableRow key={permission.code} data-testid={`roles-permission-row-${permission.code}`}>
                <TableCell>
                  <span className="block font-mono text-xs text-zinc-900">{permission.code}</span>
                  <span className="block text-xs text-zinc-500">{permission.description}</span>
                </TableCell>
                {roles.map((role) => (
                  <TableCell key={`${role.id}-${permission.code}`} className="text-center">
                    {role.permissions.includes(permission.code) ? (
                      <Check className="mx-auto h-4 w-4 text-emerald-600" aria-label="granted" />
                    ) : (
                      <Minus className="mx-auto h-4 w-4 text-zinc-300" aria-label="not granted" />
                    )}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

export default Roles;
