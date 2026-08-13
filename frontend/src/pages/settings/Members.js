import { useCallback, useEffect, useState } from "react";
import { Trash2, UserPlus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { api, readError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { MEMBERS } from "@/constants/testIds";

const ASSIGNABLE_ROLES = ["ADMIN", "FINANCE", "ACCOUNTANT", "VIEWER"];

const ROLE_TONE = {
  OWNER: "bg-[#0A0F2C] text-white",
  ADMIN: "bg-zinc-900 text-white",
  FINANCE: "bg-emerald-100 text-emerald-800",
  ACCOUNTANT: "bg-amber-100 text-amber-900",
  VIEWER: "bg-zinc-100 text-zinc-700",
};

const Members = () => {
  const { can } = useAuth();
  const [state, setState] = useState({ status: "loading", error: null });
  const [page, setPage] = useState({ items: [], total: 0, page: 1, total_pages: 1 });
  const [inviteOpen, setInviteOpen] = useState(false);
  const [invite, setInvite] = useState({ email: "", role: "VIEWER" });
  const [inviteState, setInviteState] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const canManage = can("workspace.members");

  const load = useCallback(async () => {
    setState({ status: "loading", error: null });
    try {
      const response = await api.get("/workspaces/members", { params: { page: 1, size: 50, sort: "created_at,asc" } });
      setPage(response.data);
      setState({ status: "ready", error: null });
    } catch (caught) {
      setState({ status: "error", error: readError(caught).message });
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleInvite = async (event) => {
    event.preventDefault();
    setInviteState(null);
    try {
      const response = await api.post("/workspaces/invitations", {
        email: invite.email.trim(),
        role: invite.role,
      });
      setInviteState({
        tone: "success",
        text: `Invitation sent to ${response.data.email} as ${response.data.role}.`,
      });
      setInvite({ email: "", role: "VIEWER" });
      await load();
    } catch (caught) {
      setInviteState({ tone: "error", text: readError(caught).message });
    }
  };

  const handleRoleChange = async (memberId, role) => {
    setBusyId(memberId);
    try {
      await api.patch(`/workspaces/members/${memberId}`, { roles: [role] });
      await load();
    } catch (caught) {
      setState((current) => ({ ...current, error: readError(caught).message }));
    } finally {
      setBusyId(null);
    }
  };

  const handleRemove = async (memberId) => {
    setBusyId(memberId);
    try {
      await api.delete(`/workspaces/members/${memberId}`);
      await load();
    } catch (caught) {
      setState((current) => ({ ...current, error: readError(caught).message }));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-8" data-testid={MEMBERS.root}>
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-zinc-500">Settings</p>
          <h1 className="font-display text-3xl font-extrabold tracking-tight text-zinc-950">Members</h1>
          <p className="text-sm text-zinc-600">
            Invitations expire after 7 days, are single use, and are bound to the invited email address.
          </p>
        </div>
        {canManage ? (
          <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2 bg-[#0A0F2C] hover:bg-[#1E293B]" data-testid={MEMBERS.inviteButton}>
                <UserPlus className="h-4 w-4" aria-hidden="true" />
                Invite member
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle className="font-display">Invite a team member</DialogTitle>
                <DialogDescription>
                  They will receive an email invitation and join with the role you pick.
                </DialogDescription>
              </DialogHeader>
              <form className="space-y-5" onSubmit={handleInvite}>
                {inviteState ? (
                  <p
                    className={`border p-3 text-sm ${
                      inviteState.tone === "error"
                        ? "border-destructive/30 bg-destructive/5"
                        : "border-emerald-200 bg-emerald-50 text-emerald-900"
                    }`}
                    data-testid={MEMBERS.inviteMessage}
                    role={inviteState.tone === "error" ? "alert" : undefined}
                  >
                    {inviteState.text}
                  </p>
                ) : null}
                <div className="space-y-2">
                  <Label htmlFor="invite-email">Email address</Label>
                  <Input
                    id="invite-email"
                    type="email"
                    required
                    value={invite.email}
                    onChange={(event) => setInvite({ ...invite, email: event.target.value })}
                    data-testid={MEMBERS.inviteEmailInput}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="invite-role">Role</Label>
                  <select
                    id="invite-role"
                    value={invite.role}
                    onChange={(event) => setInvite({ ...invite, role: event.target.value })}
                    data-testid={MEMBERS.inviteRoleSelect}
                    className="h-10 w-full border border-zinc-200 bg-white px-3 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0A0F2C] focus-visible:ring-offset-2"
                  >
                    {ASSIGNABLE_ROLES.map((role) => (
                      <option key={role} value={role}>
                        {role}
                      </option>
                    ))}
                  </select>
                </div>
                <DialogFooter>
                  <Button
                    type="submit"
                    className="bg-[#0A0F2C] hover:bg-[#1E293B]"
                    data-testid={MEMBERS.inviteSubmitButton}
                  >
                    Send invitation
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        ) : null}
      </header>

      {state.status === "loading" ? <LoadingState label="Loading members" /> : null}
      {state.status === "error" ? <ErrorState message={state.error} onRetry={load} /> : null}

      {state.status === "ready" ? (
        page.items.length === 0 ? (
          <EmptyState
            testId={MEMBERS.emptyState}
            title="No members yet"
            description="Invite your finance team so they can review reconciliation results with you."
          />
        ) : (
          <div className="border border-zinc-200 bg-white">
            <Table data-testid={MEMBERS.table}>
              <TableHeader className="bg-zinc-50/60">
                <TableRow>
                  <TableHead>Member</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {page.items.map((member) => (
                  <TableRow key={member.id} data-testid={`${MEMBERS.row}-${member.email}`}>
                    <TableCell>
                      <span className="block font-medium text-zinc-900">{member.full_name || "—"}</span>
                      <span className="block font-mono text-xs text-zinc-500">{member.email}</span>
                    </TableCell>
                    <TableCell>
                      {member.is_owner || !canManage ? (
                        <Badge className={`rounded-sm font-mono text-[10px] ${ROLE_TONE[member.roles[0]] || ""}`}>
                          {member.roles[0] || "—"}
                        </Badge>
                      ) : (
                        <select
                          value={member.roles[0] || "VIEWER"}
                          disabled={busyId === member.id}
                          onChange={(event) => handleRoleChange(member.id, event.target.value)}
                          data-testid={`${MEMBERS.roleSelect}-${member.email}`}
                          className="h-9 border border-zinc-200 bg-white px-2 text-xs font-mono transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0A0F2C]"
                        >
                          {ASSIGNABLE_ROLES.map((role) => (
                            <option key={role} value={role}>
                              {role}
                            </option>
                          ))}
                        </select>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-xs text-zinc-600">{member.status}</span>
                    </TableCell>
                    <TableCell className="text-right">
                      {canManage && !member.is_owner ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="gap-2 text-destructive hover:text-destructive"
                          disabled={busyId === member.id}
                          onClick={() => handleRemove(member.id)}
                          data-testid={`${MEMBERS.removeButton}-${member.email}`}
                        >
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                          Remove
                        </Button>
                      ) : (
                        <span className="font-mono text-xs text-zinc-400">protected</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <p className="border-t border-zinc-200 px-4 py-3 font-mono text-xs text-zinc-500">
              {page.total} member{page.total === 1 ? "" : "s"} · page {page.page} of {page.total_pages}
            </p>
          </div>
        )
      ) : null}
    </div>
  );
};

export default Members;
