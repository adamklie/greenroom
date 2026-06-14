import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { api } from "../api/client";

const CARD = { background: "var(--bg-card)", borderColor: "var(--border)" } as const;

/**
 * Member list + add/role/remove controls for a project. No modal chrome — used
 * both inline (Settings) and inside the switcher's modal.
 */
export default function ProjectMembersEditor({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("viewer");
  const [error, setError] = useState<string | null>(null);

  const { data: members = [] } = useQuery({
    queryKey: ["projects", projectId, "members"],
    queryFn: () => api.projects.members(projectId),
  });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["projects", projectId, "members"] });

  const addMember = useMutation({
    mutationFn: () => api.projects.addMember(projectId, email.trim(), role),
    onSuccess: () => { setEmail(""); setError(null); invalidate(); },
    onError: () => setError("Couldn't add — check the email is a registered account."),
  });
  const updateRole = useMutation({
    mutationFn: ({ memberId, r }: { memberId: number; r: string }) => api.projects.updateMember(projectId, memberId, r),
    onSuccess: invalidate,
  });
  const removeMember = useMutation({
    mutationFn: (memberId: number) => api.projects.removeMember(projectId, memberId),
    onSuccess: invalidate,
  });

  return (
    <div>
      <div className="space-y-2 mb-3">
        {members.map((m) => (
          <div key={m.id} className="flex items-center gap-2 text-sm">
            <span className="flex-1 truncate" style={{ color: "var(--text)" }}>{m.email}</span>
            <select
              value={m.role}
              onChange={(e) => updateRole.mutate({ memberId: m.id, r: e.target.value })}
              className="px-2 py-1 rounded border text-xs"
              style={{ ...CARD, color: "var(--text)" }}
            >
              <option value="owner">owner</option>
              <option value="editor">editor</option>
              <option value="viewer">viewer</option>
            </select>
            <button onClick={() => removeMember.mutate(m.id)} title="Remove" style={{ color: "var(--text-muted)" }}>
              <X size={14} />
            </button>
          </div>
        ))}
        {members.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>No members yet.</p>}
      </div>

      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (email.trim()) addMember.mutate(); }}>
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="email@account"
          className="flex-1 min-w-0 px-2 py-1.5 rounded border text-sm"
          style={{ ...CARD, color: "var(--text)" }}
        />
        <select value={role} onChange={(e) => setRole(e.target.value)} className="px-2 py-1.5 rounded border text-sm" style={{ ...CARD, color: "var(--text)" }}>
          <option value="viewer">viewer</option>
          <option value="editor">editor</option>
          <option value="owner">owner</option>
        </select>
        <button type="submit" className="px-3 py-1.5 rounded text-sm" style={{ background: "var(--accent)", color: "var(--bg)" }}>
          Add
        </button>
      </form>
      {error && <p className="mt-2 text-xs" style={{ color: "var(--danger, #e57373)" }}>{error}</p>}
      <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
        Members must already have a Greenroom account — sharing is invite-only.
      </p>
    </div>
  );
}
