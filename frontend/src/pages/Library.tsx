import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type AudioFile, type Song } from "../api/client";
import { Search, Play, Star, FileAudio } from "lucide-react";

const SOURCE_OPTIONS = ["", "phone", "logic_pro", "garageband", "suno_ai", "collaborator", "download", "gopro", "unknown"];
const ROLE_OPTIONS = ["", "recording", "demo", "reference", "backing_track", "final_mix", "stem"];

const inputStyle = { borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" };

function InlineSelect({ value, options, onChange }: { value: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <select value={value || ""} onChange={(e) => onChange(e.target.value)}
      className="px-1 py-0.5 rounded border text-xs outline-none bg-transparent"
      style={inputStyle}>
      {options.map(o => <option key={o} value={o}>{o || "—"}</option>)}
    </select>
  );
}

function StarRating({ value, onChange }: { value: number | null; onChange: (v: number) => void }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map(n => (
        <button key={n} onClick={() => onChange(n)} className="p-0">
          <Star size={12}
            fill={value && n <= value ? "var(--yellow)" : "none"}
            style={{ color: value && n <= value ? "var(--yellow)" : "var(--text-muted)" }} />
        </button>
      ))}
    </div>
  );
}

export default function Library() {
  const [search, setSearch] = useState("");
  const [filterHasSong, setFilterHasSong] = useState<string>("");
  const [filterSource, setFilterSource] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const queryClient = useQueryClient();

  const params: Record<string, string> = {};
  if (search) params.search = search;
  if (filterHasSong === "yes") params.has_song = "true";
  if (filterHasSong === "no") params.has_song = "false";
  if (filterSource) params.source = filterSource;

  const { data: files = [], isLoading } = useQuery({
    queryKey: ["audio-files", params],
    queryFn: () => api.audioFiles.list(params),
  });

  const { data: songs = [] } = useQuery({
    queryKey: ["songs-all"],
    queryFn: () => api.songs.list(),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      api.audioFiles.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audio-files"] });
      queryClient.invalidateQueries({ queryKey: ["songs"] });
    },
  });

  const save = (id: number, field: string, value: unknown) => {
    updateMut.mutate({ id, data: { [field]: value === "" ? null : value } });
  };

  const filename = (path: string) => path.split("/").pop() || path;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-2">Library</h2>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        {files.length} audio files — the source of truth for all your recordings
      </p>

      {/* Filters */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
          <input type="text" placeholder="Search files..." value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-2 rounded-lg border text-sm bg-transparent outline-none"
            style={{ borderColor: "var(--border)", color: "var(--text)" }} />
        </div>
        <select value={filterHasSong} onChange={(e) => setFilterHasSong(e.target.value)}
          className="px-3 py-2 rounded-lg border text-sm outline-none"
          style={{ ...inputStyle, background: "var(--bg-card)" }}>
          <option value="">All files</option>
          <option value="yes">Linked to a song</option>
          <option value="no">Unassigned</option>
        </select>
        <select value={filterSource} onChange={(e) => setFilterSource(e.target.value)}
          className="px-3 py-2 rounded-lg border text-sm outline-none"
          style={{ ...inputStyle, background: "var(--bg-card)" }}>
          <option value="">All sources</option>
          {SOURCE_OPTIONS.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {isLoading ? <div style={{ color: "var(--text-muted)" }}>Loading...</div> : (
        <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--border)" }}>
          <table className="w-full text-xs">
            <thead>
              <tr style={{ background: "var(--bg-card)" }}>
                <th className="text-left px-3 py-2.5 font-medium" style={{ color: "var(--text-muted)" }}>File</th>
                <th className="text-left px-3 py-2.5 font-medium w-48" style={{ color: "var(--text-muted)" }}>Song</th>
                <th className="text-left px-3 py-2.5 font-medium w-24" style={{ color: "var(--text-muted)" }}>Source</th>
                <th className="text-left px-3 py-2.5 font-medium w-24" style={{ color: "var(--text-muted)" }}>Role</th>
                <th className="text-center px-3 py-2.5 font-medium w-24" style={{ color: "var(--text-muted)" }}>Rating</th>
                <th className="text-left px-3 py-2.5 font-medium w-32" style={{ color: "var(--text-muted)" }}>Notes</th>
              </tr>
            </thead>
            <tbody>
              {files.map((af) => (
                <tr key={af.id} className="border-t"
                  style={{ borderColor: "var(--border)" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <button onClick={() => setExpandedId(expandedId === af.id ? null : af.id)}>
                        <FileAudio size={14} style={{ color: af.song_id ? "var(--accent)" : "var(--text-muted)" }} />
                      </button>
                      <div>
                        <div className="font-medium">{filename(af.file_path)}</div>
                        {expandedId === af.id && af.file_type && ["m4a", "mp3", "wav"].includes(af.file_type) && (
                          <audio controls className="h-7 mt-1" style={{ filter: "invert(1) hue-rotate(180deg)", width: 200 }}>
                            <source src={api.media.audioFileUrl(af.id)} />
                          </audio>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <select value={af.song_id || ""} onChange={(e) => save(af.id, "song_id", e.target.value ? Number(e.target.value) : null)}
                      className="w-full px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}>
                      <option value="">—</option>
                      {songs.map(s => (
                        <option key={s.id} value={s.id}>
                          {s.title}{s.artist ? ` — ${s.artist}` : ""}{s.type ? ` (${s.type})` : ""}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <InlineSelect value={af.source || ""} options={SOURCE_OPTIONS}
                      onChange={(v) => save(af.id, "source", v)} />
                  </td>
                  <td className="px-3 py-2">
                    <InlineSelect value={af.role || ""} options={ROLE_OPTIONS}
                      onChange={(v) => save(af.id, "role", v)} />
                  </td>
                  <td className="px-3 py-2 text-center">
                    <StarRating value={af.rating_overall} onChange={(v) => save(af.id, "rating_overall", v)} />
                  </td>
                  <td className="px-3 py-2">
                    <input defaultValue={af.notes || ""} placeholder="—"
                      onBlur={(e) => save(af.id, "notes", e.target.value)}
                      className="w-full px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}
                      key={`notes-${af.id}-${af.notes}`} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
