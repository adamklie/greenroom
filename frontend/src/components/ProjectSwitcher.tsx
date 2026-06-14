import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, FolderKanban, Plus, Users, X } from "lucide-react";
import { api, type Project } from "../api/client";
import { useProject } from "../project";
import ProjectMembersEditor from "./ProjectMembersEditor";

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
        {activeProject?.color
          ? <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: activeProject.color }} />
          : <FolderKanban size={16} style={{ color: "var(--accent)" }} />}
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
                <span className="flex items-center gap-2 truncate">
                  <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: p.color || "var(--border)" }} />
                  <span className="truncate">{p.name}</span>
                </span>
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
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.5)" }} onClick={onClose}>
      <div className="w-full max-w-md rounded-xl border p-5" style={CARD} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
            Members · {project.name}
          </h2>
          <button onClick={onClose} style={{ color: "var(--text-muted)" }}><X size={18} /></button>
        </div>
        <ProjectMembersEditor projectId={project.id} />
      </div>
    </div>
  );
}
