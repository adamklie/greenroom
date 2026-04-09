import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type TriageItem, type Song } from "../api/client";
import { FileAudio, Check, SkipForward, Plus } from "lucide-react";

function TriageCard({ item, songs, onDone }: { item: TriageItem; songs: Song[]; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [songId, setSongId] = useState<number | "">(item.suggested_song_id || "");
  const [newTitle, setNewTitle] = useState("");
  const [songType, setSongType] = useState(item.suggested_type || "cover");
  const [source, setSource] = useState(item.suggested_source || "unknown");
  const [creating, setCreating] = useState(false);

  const classifyMut = useMutation({
    mutationFn: () => api.triage.classify(item.id, {
      song_id: songId || null,
      create_song_title: creating ? newTitle : null,
      song_type: songType,
      source,
    }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["triage"] }); onDone(); },
  });

  const skipMut = useMutation({
    mutationFn: () => api.triage.skip(item.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["triage"] }),
  });

  const fileName = item.file_path.split("/").pop() || item.file_path;
  const inputStyle = { borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" };

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <FileAudio size={18} style={{ color: "var(--accent)" }} />
          <div>
            <div className="font-medium text-sm">{fileName}</div>
            <div className="text-xs truncate max-w-md" style={{ color: "var(--text-muted)" }}>{item.file_path}</div>
          </div>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "var(--bg-hover)", color: "var(--text-muted)" }}>
          {item.file_type}
        </span>
      </div>

      {/* Audio preview */}
      {item.file_type && ["m4a", "mp3", "wav"].includes(item.file_type) && (
        <audio controls className="w-full h-8 mb-3" style={{ filter: "invert(1) hue-rotate(180deg)" }}>
          <source src={`/api/media/file/${encodeURIComponent(item.file_path)}`} />
        </audio>
      )}

      <div className="flex gap-3 flex-wrap mb-3">
        <select value={songType} onChange={(e) => setSongType(e.target.value)}
          className="px-2 py-1 rounded border text-sm outline-none" style={inputStyle}>
          <option value="cover">Cover</option>
          <option value="original">Original</option>
          <option value="idea">Idea</option>
        </select>
        <select value={source} onChange={(e) => setSource(e.target.value)}
          className="px-2 py-1 rounded border text-sm outline-none" style={inputStyle}>
          <option value="unknown">Unknown</option>
          <option value="phone">Phone</option>
          <option value="logic_pro">Logic Pro</option>
          <option value="garageband">GarageBand</option>
          <option value="suno_ai">Suno AI</option>
          <option value="collaborator">Collaborator</option>
          <option value="download">Download</option>
        </select>
      </div>

      {!creating ? (
        <div className="flex gap-2 mb-3">
          <select value={songId} onChange={(e) => setSongId(e.target.value ? Number(e.target.value) : "")}
            className="flex-1 px-2 py-1 rounded border text-sm outline-none" style={inputStyle}>
            <option value="">Assign to existing song...</option>
            {songs.map((s) => (
              <option key={s.id} value={s.id}>{s.title}{s.artist ? ` — ${s.artist}` : ""} ({s.type})</option>
            ))}
          </select>
          <button onClick={() => setCreating(true)}
            className="flex items-center gap-1 px-2 py-1 rounded border text-sm"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
            <Plus size={14} /> New
          </button>
        </div>
      ) : (
        <div className="flex gap-2 mb-3">
          <input placeholder="New song title..." value={newTitle} onChange={(e) => setNewTitle(e.target.value)}
            className="flex-1 px-2 py-1 rounded border text-sm outline-none" style={inputStyle} />
          <button onClick={() => setCreating(false)} className="text-xs" style={{ color: "var(--text-muted)" }}>Cancel</button>
        </div>
      )}

      <div className="flex gap-2">
        <button onClick={() => classifyMut.mutate()}
          disabled={!songId && !newTitle}
          className="flex items-center gap-1 px-3 py-1.5 rounded text-sm font-medium text-white disabled:opacity-50"
          style={{ background: "var(--green)" }}>
          <Check size={14} /> Classify
        </button>
        <button onClick={() => skipMut.mutate()}
          className="flex items-center gap-1 px-3 py-1.5 rounded text-sm border"
          style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
          <SkipForward size={14} /> Skip
        </button>
      </div>
    </div>
  );
}

export default function Triage() {
  const { data: items = [], isLoading } = useQuery({
    queryKey: ["triage"],
    queryFn: () => api.triage.list("pending"),
  });

  const { data: songs = [] } = useQuery({
    queryKey: ["songs-all"],
    queryFn: () => api.songs.list(),
  });

  if (isLoading) return <div style={{ color: "var(--text-muted)" }}>Loading...</div>;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-2">Triage Queue</h2>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        {items.length} unclassified files found on disk. Assign them to songs or skip.
      </p>

      {items.length === 0 && (
        <div className="text-center py-16 rounded-xl border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <Check size={32} className="mx-auto mb-3" style={{ color: "var(--green)" }} />
          <p className="font-medium">All caught up!</p>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            No unclassified files. Hit "Rescan Files" after adding new recordings.
          </p>
        </div>
      )}

      <div className="space-y-4">
        {items.map((item) => (
          <TriageCard key={item.id} item={item} songs={songs} onDone={() => {}} />
        ))}
      </div>
    </div>
  );
}
