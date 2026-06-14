import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { api, type AudioFile } from "../api/client";
import { useProject } from "../project";

const CARD = { background: "var(--bg-card)", borderColor: "var(--border)" } as const;

/**
 * Split a single recording into another project. Pick the destination, then
 * attach the recording to an existing song there or create a new one (copying
 * the source song's metadata by default). Only this recording moves; the source
 * song and its other recordings are untouched.
 */
export default function MoveRecordingModal({
  af,
  onClose,
  onMoved,
}: {
  af: AudioFile;
  onClose: () => void;
  onMoved?: () => void;
}) {
  const { projects, activeProjectId } = useProject();
  const queryClient = useQueryClient();
  const targets = projects.filter((p) => p.id !== activeProjectId);
  const [targetId, setTargetId] = useState<number | null>(targets[0]?.id ?? null);
  // "new" = create a copy of the source song; otherwise an existing song id.
  const [choice, setChoice] = useState<number | "new">("new");
  const [copyMetadata, setCopyMetadata] = useState(true);

  const { data: songs = [] } = useQuery({
    queryKey: ["projects", targetId, "songs"],
    queryFn: () => api.projects.songs(targetId as number),
    enabled: targetId != null,
  });

  const move = useMutation({
    mutationFn: () =>
      api.projects.moveRecording(
        af.id,
        targetId as number,
        choice === "new" ? null : choice,
        copyMetadata,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        predicate: (q) => q.queryKey[0] !== "projects" && q.queryKey[0] !== "health",
      });
      onMoved?.();
      onClose();
    },
  });

  const label = af.song_title ? `${af.song_title}${af.song_artist ? ` — ${af.song_artist}` : ""}` : (af.submitted_file_name || af.clip_name || af.identifier || `recording ${af.id}`);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.5)" }} onClick={onClose}>
      <div className="w-full max-w-md rounded-xl border p-5" style={CARD} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>Move recording</h2>
          <button onClick={onClose} style={{ color: "var(--text-muted)" }}><X size={18} /></button>
        </div>
        <p className="text-xs mb-4 truncate" style={{ color: "var(--text-muted)" }}>{label}</p>

        <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Destination project</label>
        <select
          value={targetId ?? ""}
          onChange={(e) => { setTargetId(Number(e.target.value)); setChoice("new"); }}
          className="w-full mb-4 px-2 py-1.5 rounded border text-sm outline-none"
          style={{ ...CARD, color: "var(--text)" }}
        >
          {targets.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>

        <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Attach to a song</label>
        <div className="rounded-lg border max-h-56 overflow-y-auto" style={CARD}>
          <label className="flex items-start gap-2 px-3 py-2 text-sm cursor-pointer border-b" style={{ borderColor: "var(--border)" }}>
            <input type="radio" name="song" checked={choice === "new"} onChange={() => setChoice("new")} className="mt-0.5" />
            <span>
              <span style={{ color: "var(--text)" }}>Create new song</span>
              <span style={{ color: "var(--text-muted)" }}> — “{af.song_title || "Untitled"}”</span>
            </span>
          </label>
          {songs.map((s) => (
            <label key={s.id} className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer" style={{ color: "var(--text)" }}>
              <input type="radio" name="song" checked={choice === s.id} onChange={() => setChoice(s.id)} />
              <span className="truncate">{s.title}{s.artist ? <span style={{ color: "var(--text-muted)" }}> — {s.artist}</span> : null}</span>
            </label>
          ))}
        </div>

        {choice === "new" && (
          <label className="flex items-center gap-2 mt-3 text-sm cursor-pointer" style={{ color: "var(--text-muted)" }}>
            <input type="checkbox" checked={copyMetadata} onChange={(e) => setCopyMetadata(e.target.checked)} />
            Copy metadata (key, tempo, tuning, lyrics, notes) from the current song
          </label>
        )}

        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="px-3 py-1.5 rounded text-sm border" style={{ ...CARD, color: "var(--text-muted)" }}>Cancel</button>
          <button
            onClick={() => move.mutate()}
            disabled={targetId == null || move.isPending}
            className="px-3 py-1.5 rounded text-sm"
            style={{ background: "var(--accent)", color: "var(--bg)", opacity: targetId == null || move.isPending ? 0.6 : 1 }}
          >
            {move.isPending ? "Moving…" : "Move recording"}
          </button>
        </div>
      </div>
    </div>
  );
}
