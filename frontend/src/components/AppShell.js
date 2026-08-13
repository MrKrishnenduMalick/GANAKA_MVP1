import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  ChevronsUpDown,
  Check,
  CreditCard,
  KeyRound,
  LayoutDashboard,
  LogOut,
  MonitorSmartphone,
  Play,
  RefreshCw,
  ScanLine,
  Settings,
  Store,
  Users,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { LOGOUT, SHELL } from "@/constants/testIds";

const NAV_ITEMS = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, testId: SHELL.navDashboard, end: true },
  { to: "/app/shopify", label: "Shopify", icon: Store, testId: "nav-shopify" },
  { to: "/app/razorpay", label: "Razorpay", icon: CreditCard, testId: "nav-razorpay" },
  { to: "/app/reconciliation/run", label: "Reconciliation", icon: Play, testId: "nav-reconciliation" },
  { to: "/app/reports", label: "Reports", icon: RefreshCw, testId: "nav-reports" },
  { to: "/app/settings/general", label: "Workspace", icon: Settings, testId: SHELL.navGeneral },
  { to: "/app/settings/members", label: "Members", icon: Users, testId: SHELL.navMembers },
  { to: "/app/settings/roles", label: "Roles & permissions", icon: KeyRound, testId: SHELL.navRoles },
  { to: "/app/settings/sessions", label: "Active sessions", icon: MonitorSmartphone, testId: SHELL.navSessions },
];

const AppShell = () => {
  const { user, workspace, workspaces, role, logout, switchWorkspace } = useAuth();
  const navigate = useNavigate();
  const [switching, setSwitching] = useState(false);

  const handleSwitch = async (workspaceId) => {
    if (workspaceId === workspace?.id) return;
    setSwitching(true);
    try {
      await switchWorkspace(workspaceId);
    } finally {
      setSwitching(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[260px_1fr]" data-testid={SHELL.root}>
      <aside className="flex flex-col border-r border-zinc-200 bg-white">
        <Link to="/app" className="flex items-center gap-2 border-b border-zinc-200 px-6 py-5">
          <ScanLine className="h-5 w-5 text-[#0A0F2C]" aria-hidden="true" />
          <span className="font-display text-lg font-extrabold tracking-tight text-zinc-950">Ganaka</span>
        </Link>

        <div className="border-b border-zinc-200 p-4">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="flex w-full items-center justify-between gap-2 border border-zinc-200 bg-zinc-50 px-3 py-2.5 text-left transition-colors hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0A0F2C] focus-visible:ring-offset-2"
                data-testid={SHELL.workspaceSwitcher}
                disabled={switching}
              >
                <span className="min-w-0">
                  <span className="block text-[10px] uppercase tracking-[0.15em] text-zinc-500">Workspace</span>
                  <span className="block truncate text-sm font-semibold text-zinc-900">
                    {workspace?.name || "No workspace"}
                  </span>
                </span>
                <ChevronsUpDown className="h-4 w-4 shrink-0 text-zinc-500" aria-hidden="true" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-60">
              <DropdownMenuLabel className="text-[10px] uppercase tracking-[0.15em]">Your workspaces</DropdownMenuLabel>
              {workspaces.map((item) => (
                <DropdownMenuItem
                  key={item.id}
                  onClick={() => handleSwitch(item.id)}
                  data-testid={`workspace-option-${item.slug}`}
                  className="flex items-center justify-between gap-2"
                >
                  <span className="truncate">{item.name}</span>
                  {item.id === workspace?.id ? <Check className="h-4 w-4" aria-hidden="true" /> : null}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          {NAV_ITEMS.map(({ to, label, icon: Icon, testId, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              data-testid={testId}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 text-sm transition-colors ${
                  isActive
                    ? "bg-[#0A0F2C] font-semibold text-white"
                    : "text-zinc-700 hover:bg-zinc-100"
                }`
              }
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-zinc-200 p-4">
          <p className="truncate text-sm font-medium text-zinc-900" data-testid={SHELL.userEmail}>
            {user?.email}
          </p>
          <div className="mt-2 flex items-center justify-between gap-2">
            <Badge variant="secondary" className="rounded-sm font-mono text-[10px]" data-testid={SHELL.roleBadge}>
              {role || "NO ROLE"}
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              data-testid={LOGOUT.button}
              className="gap-2 text-zinc-600"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              Sign out
            </Button>
          </div>
        </div>
      </aside>

      <main className="bg-zinc-50">
        <div className="mx-auto max-w-6xl px-6 py-10 lg:px-10 lg:py-14">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default AppShell;
