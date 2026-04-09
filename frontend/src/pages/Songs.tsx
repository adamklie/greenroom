import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Song } from "../api/client";
import { Search, X, Play, Music, Tag, ArrowUpRight } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  idea: "var(--text-muted)", learning: "var(--blue)", rehearsed: "var(--yellow)",
  polished: "var(--blue)", recorded: "var(--green)", released: "var(--accent)",
  captured: "var(--text-muted)", developing: "var(--yellow)", promoted: "var(--green)",
  draft: "var(--text-muted)", arranged: "var(--yellow)",
};

const STATUSES_BY_TYPE: Record<string, string[]> = {
  cover: ["idea", "learning", "rehearsed", "polished", "recorded", "released"],
  original: ["idea", "draft", "arranged", "rehearsed", "recorded", "released"],
  idea: ["captured", "developing", "promoted"],
};

const PROJECTS = ["all", "solo", "ozone_destructors", "sural", "joe", "ideas"];
const PROJECT_LABELS: Record<string, string> = {
  all: "All Projects", solo: "Solo", ozone_destructors: "Ozone Destructors",
  sural: "Sural", joe: "Joe", ideas: "Ideas",
};

function StatusBadge({ status, onClick }: { status: string; onClick?: (e: React.MouseEvent) => void }) {
  return (
    <button onClick={onClick}
      className="px-2 py-0.5 rounded-full text-xs font-medium capitalize border cursor-pointer hover:opacity-80"
      style={{ borderColor: STATUS_COLORS[status] || "var(--border)", color: STATUS_COLORS[status] || "var(--text)" }}>
      {status}
    </button>
  );
}

const TYPE_OPTIONS = ["cover", "original", "idea"];
const ALL_STATUSES = [...new Set([
  ...STATUSES_BY_TYPE.cover, ...STATUSES_BY_TYPE.original, ...STATUSES_BY_TYPE.idea,
])];
const TUNING_OPTIONS = ["standard", "drop_d", "open_g", "open_d", "half_step_down", "full_step_down", "dadgad", "other"];
const KEY_OPTIONS = ["", "C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B",
  "Am", "A#m", "Bbm", "Bm", "Cm", "C#m", "Dm", "D#m", "Ebm", "Em", "Fm", "F#m", "Gm", "G#m"];

function EditableField({ label, value, onChange, type = "text", options, placeholder }: {
  label: string; value: string; onChange: (v: string) => void; type?: string; options?: string[]; placeholder?: string;
}) {
  const style = { borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" };
  return (
    <div>
      <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>{label}</label>
      {options ? (
        <select value={value} onChange={(e) => onChange(e.target.value)}
          className="w-full px-2 py-1.5 rounded border text-sm outline-none" style={style}>
          {options.map((o) => <option key={o} value={o}>{o || "—"}</option>)}
        </select>
      ) : (
        <input type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
          className="w-full px-2 py-1.5 rounded border text-sm outline-none" style={style} />
      )}
    </div>
  );
}

function SongDetailPanel({ songId, onClose }: { songId: number; onClose: () => void }) {
  const { data: song } = useQuery({
    queryKey: ["song", songId],
    queryFn: () => api.songs.get(songId),
  });
  const queryClient = useQueryClient();
  const [editingLyrics, setEditingLyrics] = useState(false);
  const [lyricsText, setLyricsText] = useState("");
  const [newTag, setNewTag] = useState("");

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["song", songId] });
    queryClient.invalidateQueries({ queryKey: ["songs"] });
  };

  const updateSong = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.songs.update(songId, data),
    onSuccess: invalidate,
  });

  const saveLyrics = useMutation({
    mutationFn: () => api.songs.updateLyrics(songId, lyricsText),
    onSuccess: () => { invalidate(); setEditingLyrics(false); },
  });

  const addTag = useMutation({
    mutationFn: (name: string) => api.songs.addTag(songId, name),
    onSuccess: invalidate,
  });

  const removeTag = useMutation({
    mutationFn: (name: string) => api.songs.removeTag(songId, name),
    onSuccess: invalidate,
  });

  if (!song) return null;

  const save = (field: string, value: string | number | null) => {
    updateSong.mutate({ [field]: value === "" ? null : value });
  };

  return (
    <div className="fixed inset-y-0 right-0 w-[480px] border-l shadow-2xl z-50 overflow-y-auto p-6"
      style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <div className="flex justify-between items-start mb-4">
        <button onClick={onClose} className="p-1 rounded hover:bg-white/10 ml-auto"><X size={18} /></button>
      </div>

      {/* Editable title + artist */}
      <div className="mb-4">
        <input onBlur={(e) => save("title", e.target.value)}
          defaultValue={song.title}
          className="text-lg font-bold bg-transparent border-b outline-none w-full pb-1 mb-1"
          style={{ borderColor: "var(--border)", color: "var(--text)" }}
          key={`title-${song.id}-${song.title}`} />
        <input defaultValue={song.artist || ""} placeholder="Artist (for covers)"
          onBlur={(e) => save("artist", e.target.value)}
          className="text-sm bg-transparent border-b outline-none w-full pb-1"
          style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
          key={`artist-${song.id}-${song.artist}`} />
      </div>

      {/* Type + Status + Project (editable dropdowns) */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <EditableField label="Type" value={song.type} options={TYPE_OPTIONS}
          onChange={(v) => save("type", v)} />
        <EditableField label="Status" value={song.status}
          options={STATUSES_BY_TYPE[song.type] || ALL_STATUSES}
          onChange={(v) => save("status", v)} />
        <EditableField label="Project" value={song.project}
          options={PROJECTS.filter(p => p !== "all")}
          onChange={(v) => save("project", v)} />
      </div>

      {/* Structured music fields (editable) */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <EditableField label="Key" value={song.key || ""} options={KEY_OPTIONS}
          onChange={(v) => save("key", v)} />
        <EditableField label="Tempo (BPM)" value={song.tempo_bpm?.toString() || ""} type="number"
          placeholder="120"
          onChange={(v) => save("tempo_bpm", v ? parseInt(v) : null)} />
        <EditableField label="Tuning" value={song.tuning || "standard"} options={TUNING_OPTIONS}
          onChange={(v) => save("tuning", v)} />
        <EditableField label="Vibe" value={song.vibe || ""} placeholder="upbeat, melancholy..."
          onChange={(v) => save("vibe", v)} />
      </div>

      {/* Tags (add/remove) */}
      <div className="mb-4">
        <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Tags</label>
        <div className="flex flex-wrap gap-1 mb-2">
          {song.tags.map((t) => (
            <span key={t} className="px-2 py-0.5 rounded-full text-xs flex items-center gap-1 cursor-pointer hover:opacity-70"
              style={{ background: "var(--bg-hover)", color: "var(--accent)" }}
              onClick={() => removeTag.mutate(t)}>
              <Tag size={10} />{t} <X size={10} />
            </span>
          ))}
          <form onSubmit={(e) => { e.preventDefault(); if (newTag.trim()) { addTag.mutate(newTag.trim()); setNewTag(""); } }}
            className="inline-flex">
            <input value={newTag} onChange={(e) => setNewTag(e.target.value)} placeholder="+ tag"
              className="px-2 py-0.5 rounded text-xs bg-transparent border outline-none w-20"
              style={{ borderColor: "var(--border)", color: "var(--text)" }} />
          </form>
        </div>
      </div>

      {/* Notes (editable) */}
      <div className="mb-4">
        <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Notes</label>
        <textarea defaultValue={song.notes || ""} placeholder="Add notes..."
          onBlur={(e) => save("notes", e.target.value)}
          rows={2} className="w-full px-2 py-1.5 rounded border text-sm outline-none resize-y"
          style={{ borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" }}
          key={`notes-${song.id}-${song.notes}`} />
      </div>

      {/* Reference recording (covers) */}
      {song.type === "cover" && song.reference_audio_file_id && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold mb-2">Reference (Original)</h4>
          <audio controls className="w-full h-8" style={{ filter: "invert(1) hue-rotate(180deg)" }}>
            <source src={api.media.audioFileUrl(song.reference_audio_file_id)} />
          </audio>
        </div>
      )}

      {/* Lyrics */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-semibold">Lyrics</h4>
          {!editingLyrics && (
            <button onClick={() => { setLyricsText(song.lyrics || ""); setEditingLyrics(true); }}
              className="text-xs" style={{ color: "var(--accent)" }}>
              {song.lyrics ? "Edit" : "Add lyrics"}
            </button>
          )}
        </div>
        {editingLyrics ? (
          <div>
            <textarea value={lyricsText} onChange={(e) => setLyricsText(e.target.value)}
              rows={10} className="w-full px-3 py-2 rounded-lg border text-sm outline-none resize-y font-mono"
              style={{ borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" }} />
            <div className="flex gap-2 mt-2">
              <button onClick={() => saveLyrics.mutate()}
                className="px-3 py-1 rounded text-sm text-white" style={{ background: "var(--accent)" }}>Save</button>
              <button onClick={() => setEditingLyrics(false)}
                className="px-3 py-1 rounded text-sm" style={{ color: "var(--text-muted)" }}>Cancel</button>
            </div>
          </div>
        ) : song.lyrics ? (
          <pre className="text-sm whitespace-pre-wrap font-mono p-3 rounded-lg max-h-48 overflow-y-auto"
            style={{ background: "var(--bg)", color: "var(--text-muted)" }}>
            {song.lyrics}
          </pre>
        ) : (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>No lyrics yet</p>
        )}
        {song.lyrics_versions.length > 0 && (
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            {song.lyrics_versions.length} previous version{song.lyrics_versions.length > 1 ? "s" : ""}
          </p>
        )}
      </div>

      {/* Audio files */}
      {song.audio_files.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold mb-2">Recordings ({song.audio_files.length})</h4>
          {song.audio_files.map((af) => (
            <div key={af.id} className="flex items-center gap-2 mb-2">
              <audio controls className="h-8 flex-1" style={{ filter: "invert(1) hue-rotate(180deg)" }}>
                <source src={api.media.audioFileUrl(af.id)} />
              </audio>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                {af.role !== "recording" && <span className="capitalize">{af.role} · </span>}
                {af.version || af.file_type}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Takes */}
      {song.takes.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold mb-2">Practice Takes ({song.takes.length})</h4>
          {song.takes.map((t) => (
            <div key={t.id} className="rounded-lg p-3 mb-2 border" style={{ background: "var(--bg)", borderColor: "var(--border)" }}>
              <div className="flex justify-between items-center text-sm mb-1">
                <span>{t.session_date}</span>
                {t.rating_overall && <span style={{ color: "var(--yellow)" }}>{"★".repeat(t.rating_overall)}</span>}
              </div>
              {t.audio_path && (
                <audio controls className="w-full h-8" style={{ filter: "invert(1) hue-rotate(180deg)" }}>
                  <source src={api.media.takeAudioUrl(t.id)} />
                </audio>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Songs({ songType, title }: { songType: string; title: string }) {
  const [project, setProject] = useState("all");
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const queryClient = useQueryClient();
  const params: Record<string, string> = { type: songType };
  if (project !== "all") params.project = project;
  if (statusFilter) params.status = statusFilter;
  if (search) params.search = search;

  const { data: songs = [], isLoading } = useQuery({
    queryKey: ["songs", params],
    queryFn: () => api.songs.list(params),
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      api.songs.update(id, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["songs"] }),
  });

  const promoteMut = useMutation({
    mutationFn: (id: number) => api.songs.promote(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["songs"] }),
  });

  const cycleStatus = (song: Song) => {
    const statuses = STATUSES_BY_TYPE[songType] || STATUSES_BY_TYPE.cover;
    const idx = statuses.indexOf(song.status);
    const next = statuses[(idx + 1) % statuses.length];
    updateStatus.mutate({ id: song.id, status: next });
  };

  const statuses = STATUSES_BY_TYPE[songType] || STATUSES_BY_TYPE.cover;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">{title}</h2>

      <div className="flex gap-3 mb-6 flex-wrap">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
          <input type="text" placeholder="Search..." value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-2 rounded-lg border text-sm bg-transparent outline-none"
            style={{ borderColor: "var(--border)", color: "var(--text)" }} />
        </div>
        <select value={project} onChange={(e) => setProject(e.target.value)}
          className="px-3 py-2 rounded-lg border text-sm outline-none"
          style={{ borderColor: "var(--border)", color: "var(--text)", background: "var(--bg-card)" }}>
          {PROJECTS.map((p) => <option key={p} value={p}>{PROJECT_LABELS[p]}</option>)}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 rounded-lg border text-sm outline-none"
          style={{ borderColor: "var(--border)", color: "var(--text)", background: "var(--bg-card)" }}>
          <option value="">All Statuses</option>
          {statuses.map((s) => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
        </select>
        <span className="self-center text-sm" style={{ color: "var(--text-muted)" }}>{songs.length} songs</span>
      </div>

      {isLoading ? <div style={{ color: "var(--text-muted)" }}>Loading...</div> : (
        <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--border)" }}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: "var(--bg-card)" }}>
                <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--text-muted)" }}>Song</th>
                {songType === "cover" && <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--text-muted)" }}>Artist</th>}
                <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--text-muted)" }}>Project</th>
                <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--text-muted)" }}>Status</th>
                <th className="text-center px-4 py-3 font-medium" style={{ color: "var(--text-muted)" }}>Key</th>
                <th className="text-center px-4 py-3 font-medium" style={{ color: "var(--text-muted)" }}>Takes</th>
                {songType === "idea" && <th className="text-center px-4 py-3 font-medium" style={{ color: "var(--text-muted)" }}>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {songs.map((song) => (
                <tr key={song.id} className="border-t cursor-pointer transition-colors"
                  style={{ borderColor: "var(--border)" }}
                  onClick={() => setSelectedId(song.id)}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                  <td className="px-4 py-3 font-medium flex items-center gap-2">
                    {song.has_audio ? <Play size={14} style={{ color: "var(--green)" }} /> : <Music size={14} style={{ color: "var(--text-muted)" }} />}
                    {song.title}
                    {song.tags.length > 0 && <span className="text-xs" style={{ color: "var(--accent)" }}>+{song.tags.length}</span>}
                  </td>
                  {songType === "cover" && (
                    <td className="px-4 py-3" style={{ color: "var(--text-muted)" }}>{song.artist || "—"}</td>
                  )}
                  <td className="px-4 py-3" style={{ color: "var(--text-muted)" }}>{PROJECT_LABELS[song.project] || song.project}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={song.status} onClick={(e) => { e.stopPropagation(); cycleStatus(song); }} />
                  </td>
                  <td className="px-4 py-3 text-center" style={{ color: "var(--text-muted)" }}>{song.key || "—"}</td>
                  <td className="px-4 py-3 text-center">{song.take_count || "—"}</td>
                  {songType === "idea" && (
                    <td className="px-4 py-3 text-center">
                      {song.status !== "promoted" && (
                        <button onClick={(e) => { e.stopPropagation(); promoteMut.mutate(song.id); }}
                          className="text-xs flex items-center gap-1 mx-auto" style={{ color: "var(--accent)" }}>
                          <ArrowUpRight size={14} /> Promote
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedId && <SongDetailPanel songId={selectedId} onClose={() => setSelectedId(null)} />}
    </div>
  );
}
