import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FolderInput, ChevronDown } from "lucide-react";
import { api } from "../api/client";
import { useProject } from "../project";

type Kind = "song" | "session" | "take" | "setlist";

const CARD = { background: "var(--bg-card)", borderColor: "var(--border)" } as const;

/**
 * Reassign project-scoped items to another project (v2). Renders nothing unless
 * the multi_project flag is on and there's somewhere to move to. Lists the
 * caller's other projects; moving a song/session cascades to its recordings.
 */
export default function MoveToProjectMenu({
  kind,
  ids,
  onMoved,
  compact = false,
  align = "right",
}: {
  kind: Kind;
  ids: number[];
  onMoved?: (moved: number) => void;
  compact?: boolean;
  align?: "left" | "right";
}) {
  const { multiProject, projects, activeProjectId } = useProject();
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();

  const targets = projects.filter((p) => p.id !== activeProjectId);

  const move = useMutation({
    mutationFn: (targetId: number) => api.projects.move(kind, ids, targetId),

    onSuccess: (r) => {
      // Moved items leave the active project, so refresh the scoped data views.
      queryClient.invalidateQueries({
        predicate: (q) => q.queryKey[0] !== "projects" && q.queryKey[0] !== "health",
      });
      setOpen(false);
      onMoved?.(r.moved);
    },
  });

  if (!multiProject || ids.length === 0 || targets.length === 0) return null;

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-1.5 rounded-lg border hover:opacity-80 ${compact ? "px-2 py-1 text-xs" : "px-3 py-2 text-sm"}`}
        style={{ ...CARD, color: "var(--text)" }}
        title="Move to another project"
      >
        <FolderInput size={compact ? 13 : 15} />
        {compact ? "Move" : `Move${ids.length > 1 ? ` ${ids.length}` : ""} to…`}
        <ChevronDown size={12} style={{ color: "var(--text-muted)" }} />
      </button>
      {open && (
        <div className={`absolute ${align === "left" ? "left-0" : "right-0"} mt-1 z-50 rounded-lg border shadow-lg py-1 min-w-44 max-w-64`} style={CARD}>
          {targets.map((p) => (
            <button
              key={p.id}
              disabled={move.isPending}
              onClick={() => move.mutate(p.id)}
              className="w-full text-left px-3 py-2 text-sm hover:opacity-80 truncate"
              style={{ color: "var(--text)" }}
            >
              {p.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
