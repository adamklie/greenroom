import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, FolderKanban, Plus, Users, X } from "lucide-react";
import { api, type Project } from "../api/client";
import { useProject } from "../project";

const CARD = { background: "var(--bg-card)", borderColor: "var(--border)" } as const;

/**
 * Sidebar project switcher (v2). Rendered only when the multi_project flag is
 * on. Lists the caller's projects, switches the active one, and opens a basic
 * members/sharing panel for owners (and admins).
 */
export default function ProjectSwitcher() {
  const { projects, activeProject, activeProjectId, setActiveProjectId } = useProject();
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [managing, setManaging] = useState<Project | null>(null);
  const queryClient = useQueryClient();

  const createProject = useMutation({
    mutationFn: (name: string) => api.projects.create(name),
    onSuccess: (p) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setActiveProjectId(p.id);
      setCreating(false);
      setNewName("");
      setOpen(false);
    },
  });

  const canManage = activeProject && (activeProject.role === "owner" || activeProject.role === "admin");

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm border hover:opacity-80"
        style={{ ...CARD, color: "var(--text)" }}
        title="Switch project"
      >
        <FolderKanban size={16} style={{ color: "var(--accent)" }} />
        <span className="flex-1 truncate text-left">
          {activeProject?.name ?? "No project"}
        </span>
        <ChevronDown size={14} style={{ color: "var(--text-muted)" }} />
      </button>

      {open && (
        <div
          className="absolute left-0 right-0 mt-1 z-40 rounded-lg border shadow-lg py-1"
          style={CARD}
        >
          <div className="max-h-64 overflow-y-auto">
            {projects.map((p) => (
              <button
                key={p.id}
                onClick={() => { setActiveProjectId(p.id); setOpen(false); }}
                className="w-full flex items-center justify-between px-3 py-2 text-sm hover:opacity-80"
                style={{
                  background: p.id === activeProjectId ? "var(--bg-hover)" : "transparent",
                  color: p.id === activeProjectId ? "var(--accent)" : "var(--text)",
                }}
              >
                <span className="truncate">{p.name}</span>
                <span className="text-xs uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
                  {p.role}
                </span>
              </button>
            ))}
            {projects.length === 0 && (
              <div className="px-3 py-2 text-sm" style={{ color: "var(--text-muted)" }}>
                No projects yet
              </div>
            )}
          </div>

          <div className="border-t mt-1 pt-1" style={{ borderColor: "var(--border)" }}>
            {creating ? (
              <form
                className="px-2 py-1 flex gap-1"
                onSubmit={(e) => { e.preventDefault(); if (newName.trim()) createProject.mutate(newName.trim()); }}
              >
                <input
                  autoFocus
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Project name"
                  className="flex-1 min-w-0 px-2 py-1 rounded text-sm border"
                  style={{ ...CARD, color: "var(--text)" }}
                />
                <button type="submit" className="px-2 py-1 rounded text-sm" style={{ background: "var(--accent)", color: "var(--bg)" }}>
                  Add
                </button>
              </form>
            ) : (
              <button
                onClick={() => setCreating(true)}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:opacity-80"
                style={{ color: "var(--text-muted)" }}
              >
                <Plus size={14} /> New project
              </button>
            )}
            {canManage && (
              <button
                onClick={() => { setManaging(activeProject); setOpen(false); }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:opacity-80"
                style={{ color: "var(--text-muted)" }}
              >
                <Users size={14} /> Manage members
              </button>
            )}
          </div>
        </div>
      )}

      {managing && <MembersPanel project={managing} onClose={() => setManaging(null)} />}
    </div>
  );
}

function MembersPanel({ project, onClose }: { project: Project; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("viewer");
  const [error, setError] = useState<string | null>(null);

  const { data: members = [] } = useQuery({
    queryKey: ["projects", project.id, "members"],
    queryFn: () => api.projects.members(project.id),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["projects", project.id, "members"] });

  const addMember = useMutation({
    mutationFn: () => api.projects.addMember(project.id, email.trim(), role),
    onSuccess: () => { setEmail(""); setError(null); invalidate(); },
    onError: () => setError("Couldn't add — check the email is a registered account."),
  });
  const updateRole = useMutation({
    mutationFn: ({ memberId, r }: { memberId: number; r: string }) => api.projects.updateMember(project.id, memberId, r),
    onSuccess: invalidate,
  });
  const removeMember = useMutation({
    mutationFn: (memberId: number) => api.projects.removeMember(project.id, memberId),
    onSuccess: invalidate,
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.5)" }} onClick={onClose}>
      <div className="w-full max-w-md rounded-xl border p-5" style={CARD} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
            Members · {project.name}
          </h2>
          <button onClick={onClose} style={{ color: "var(--text-muted)" }}><X size={18} /></button>
        </div>

        <div className="space-y-2 mb-4">
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
        </div>

        <form
          className="flex gap-2"
          onSubmit={(e) => { e.preventDefault(); if (email.trim()) addMember.mutate(); }}
        >
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
        <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
          Members must already have a Greenroom account — sharing is invite-only.
        </p>
      </div>
    </div>
  );
}
