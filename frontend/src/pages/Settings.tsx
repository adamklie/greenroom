import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Info, Palette, Download, FolderKanban, Trash2, GripVertical } from "lucide-react";
import { api, type Project } from "../api/client";
import { useTheme } from "../theme";
import { useProject } from "../project";
import ProjectMembersEditor from "../components/ProjectMembersEditor";

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between items-baseline py-1.5">
      <span className="text-sm" style={{ color: "var(--text-muted)" }}>{label}</span>
      <span className="text-sm font-mono">{value}</span>
    </div>
  );
}

function AppInfo() {
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: api.health.get,
  });
  const { data: dashboard } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.dashboard.get,
  });
  const { data: tags = [] } = useQuery({
    queryKey: ["tags-all"],
    queryFn: () => api.tags.list(),
  });
  const { data: backupList } = useQuery({
    queryKey: ["backups"],
    queryFn: api.backup.list,
  });

  const stats = dashboard?.stats;
  const latestBackup = backupList?.backups?.[0];

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <h3 className="font-semibold mb-3 flex items-center gap-2">
        <Info size={16} style={{ color: "var(--accent)" }} />
        App Info
      </h3>
      <div className="divide-y" style={{ borderColor: "var(--border)" }}>
        <StatRow label="Backend version" value={health?.version ?? "—"} />
        <StatRow label="Total songs" value={stats?.total_songs ?? "—"} />
        <StatRow label="Total recordings (audio files)" value={stats?.total_audio_files ?? "—"} />
        <StatRow label="Total sessions" value={stats?.total_sessions ?? "—"} />
        <StatRow label="Total tags" value={tags.length} />
        <StatRow
          label="Last backup"
          value={latestBackup ? new Date(latestBackup.created).toLocaleString() : "none"}
        />
      </div>
    </div>
  );
}

function Appearance() {
  const { theme, toggleTheme } = useTheme();
  const isLight = theme === "light";
  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <h3 className="font-semibold mb-3 flex items-center gap-2">
        <Palette size={16} style={{ color: "var(--accent)" }} />
        Appearance
      </h3>
      <div className="flex items-center justify-between py-1.5">
        <div>
          <div className="text-sm">Light mode</div>
          <div className="text-xs" style={{ color: "var(--text-muted)" }}>
            Switch the app to a light color theme
          </div>
        </div>
        <button
          onClick={toggleTheme}
          role="switch"
          aria-checked={isLight}
          aria-label="Toggle light mode"
          className="relative w-10 h-5 rounded-full border transition-colors"
          style={{ borderColor: "var(--border)", background: isLight ? "var(--accent)" : "var(--bg)" }}
        >
          <span
            className="absolute top-0.5 w-4 h-4 rounded-full transition-all"
            style={{ background: isLight ? "#fff" : "var(--text-muted)", left: isLight ? "1.375rem" : "0.125rem" }}
          />
        </button>
      </div>
    </div>
  );
}

function DataBackup() {
  const [state, setState] = useState<"idle" | "downloading" | "done" | "error">("idle");
  const [error, setError] = useState<string>("");

  const handleExport = async () => {
    setState("downloading");
    setError("");
    try {
      const r = await fetch("/api/backup/export-download", { credentials: "include" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `greenroom-export-${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setState("done");
    } catch (err) {
      setState("error");
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <h3 className="font-semibold mb-3 flex items-center gap-2">
        <Download size={16} style={{ color: "var(--accent)" }} />
        Data Backup
      </h3>
      <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
        Save every song, recording, rating, and lyric annotation as a single
        portable JSON file. Useful for offline backup or migrating elsewhere.
        Database itself is continuously replicated to cloud storage in the
        background; this is a human-readable extra.
      </p>
      <button
        onClick={handleExport}
        disabled={state === "downloading"}
        className="px-4 py-2 rounded text-sm font-medium text-white disabled:opacity-50"
        style={{ background: "var(--accent)" }}>
        {state === "downloading" ? "Preparing…" : "Export JSON"}
      </button>
      {state === "done" && (
        <span className="ml-3 text-xs" style={{ color: "var(--green)" }}>Downloaded</span>
      )}
      {state === "error" && (
        <span className="ml-3 text-xs" style={{ color: "var(--red)" }}>Failed: {error}</span>
      )}
    </div>
  );
}

const PROJECT_COLORS = [
  "#10b981", "#3b82f6", "#eab308", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#6b7280",
];

function ProjectEditor({ project }: { project: Project }) {
  const queryClient = useQueryClient();
  const { setActiveProjectId, projects } = useProject();
  const canEdit = project.role === "owner" || project.role === "admin";
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description ?? "");
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["projects"] });

  const save = useMutation({
    mutationFn: (data: { name?: string; description?: string | null; color?: string | null }) =>
      api.projects.update(project.id, data),
    onSuccess: invalidate,
  });
  const del = useMutation({
    mutationFn: () => api.projects.remove(project.id),
    onSuccess: () => {
      const next = projects.find((p) => p.id !== project.id);
      if (next) setActiveProjectId(next.id);
      invalidate();
    },
    onError: () => alert("Couldn't delete — the project still has content. Move or delete it first."),
  });

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Name</label>
        <div className="flex gap-2">
          <input value={name} onChange={(e) => setName(e.target.value)} disabled={!canEdit}
            className="flex-1 px-2 py-1.5 rounded border text-sm bg-transparent outline-none"
            style={{ borderColor: "var(--border)", color: "var(--text)" }} />
          {canEdit && name.trim() && name.trim() !== project.name && (
            <button onClick={() => save.mutate({ name: name.trim() })}
              className="px-3 py-1.5 rounded text-sm" style={{ background: "var(--accent)", color: "var(--bg)" }}>Save</button>
          )}
        </div>
      </div>

      <div>
        <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Description</label>
        <textarea value={description} onChange={(e) => setDescription(e.target.value)} disabled={!canEdit}
          rows={2} placeholder="What is this project?"
          className="w-full px-2 py-1.5 rounded border text-sm bg-transparent outline-none resize-y"
          style={{ borderColor: "var(--border)", color: "var(--text)" }} />
        {canEdit && (description ?? "") !== (project.description ?? "") && (
          <button onClick={() => save.mutate({ description })}
            className="mt-1 px-3 py-1 rounded text-xs" style={{ background: "var(--accent)", color: "var(--bg)" }}>Save description</button>
        )}
      </div>

      <div>
        <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Color</label>
        <div className="flex items-center gap-2 flex-wrap">
          {PROJECT_COLORS.map((c) => (
            <button key={c} disabled={!canEdit} onClick={() => save.mutate({ color: c })}
              className="w-6 h-6 rounded-full border-2" title={c}
              style={{ background: c, borderColor: project.color === c ? "var(--text)" : "transparent" }} />
          ))}
          {project.color && canEdit && (
            <button onClick={() => save.mutate({ color: null })} className="text-xs ml-1" style={{ color: "var(--text-muted)" }}>clear</button>
          )}
        </div>
      </div>

      {canEdit && (
        <div>
          <label className="text-xs block mb-2" style={{ color: "var(--text-muted)" }}>Members</label>
          <ProjectMembersEditor projectId={project.id} />
        </div>
      )}

      {canEdit && (
        <div className="pt-3 border-t" style={{ borderColor: "var(--border)" }}>
          <button onClick={() => { if (confirm(`Delete project "${project.name}"? It must be empty.`)) del.mutate(); }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded border text-sm"
            style={{ borderColor: "var(--danger, #ef4444)", color: "var(--danger, #ef4444)" }}>
            <Trash2 size={14} /> Delete project
          </button>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Only works when the project has no songs, recordings, sessions, or setlists.</p>
        </div>
      )}
    </div>
  );
}

function ProjectSettings() {
  const { multiProject, projects, activeProjectId } = useProject();
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(activeProjectId);
  const [dragId, setDragId] = useState<number | null>(null);
  const reorder = useMutation({
    mutationFn: (ids: number[]) => api.projects.reorder(ids),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });
  if (!multiProject) return null;
  const selected = projects.find((p) => p.id === (selectedId ?? activeProjectId)) ?? projects[0];

  const onDrop = (targetId: number) => {
    if (dragId == null || dragId === targetId) { setDragId(null); return; }
    const ids = projects.map((p) => p.id);
    const from = ids.indexOf(dragId);
    const to = ids.indexOf(targetId);
    ids.splice(to, 0, ids.splice(from, 1)[0]);
    reorder.mutate(ids);
    setDragId(null);
  };

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <h3 className="font-semibold mb-1 flex items-center gap-2">
        <FolderKanban size={18} style={{ color: "var(--accent)" }} />
        Project settings
      </h3>
      <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>
        Drag to reorder; click to edit.
      </p>
      {projects.length === 0 ? (
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>No projects yet.</p>
      ) : (
        <>
          <div className="rounded-lg border mb-4 divide-y" style={{ borderColor: "var(--border)" }}>
            {projects.map((p) => (
              <div
                key={p.id}
                draggable
                onDragStart={() => setDragId(p.id)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => onDrop(p.id)}
                onClick={() => setSelectedId(p.id)}
                className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer"
                style={{ background: p.id === selected?.id ? "var(--bg-hover)" : "transparent", opacity: dragId === p.id ? 0.4 : 1 }}
              >
                <GripVertical size={14} style={{ color: "var(--text-muted)", cursor: "grab" }} />
                <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: p.color || "var(--border)" }} />
                <span className="flex-1 truncate" style={{ color: "var(--text)" }}>{p.name}</span>
                <span className="text-xs uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{p.role}</span>
              </div>
            ))}
          </div>
          {selected && <ProjectEditor key={selected.id} project={selected} />}
        </>
      )}
    </div>
  );
}

export default function Settings() {
  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold mb-2">Settings</h2>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        App-level configuration and status
      </p>

      <div className="space-y-6">
        <ProjectSettings />
        <AppInfo />
        <DataBackup />
        <Appearance />
      </div>

      <p className="text-xs mt-6" style={{ color: "var(--text-muted)" }}>
        More settings will live here as the app evolves (vault location, rating dimensions, etc.).
      </p>
    </div>
  );
}
