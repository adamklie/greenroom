import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Song } from "../api/client";
import { Search, X, Play, Music } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  idea: "var(--text-muted)",
  rehearsed: "var(--yellow)",
  polished: "var(--blue)",
  recorded: "var(--green)",
  released: "var(--accent)",
};

const STATUSES = ["idea", "rehearsed", "polished", "recorded", "released"];
const PROJECTS = ["all", "solo", "ozone_destructors", "sural", "joe", "ideas"];
const PROJECT_LABELS: Record<string, string> = {
  all: "All Projects",
  solo: "Solo",
  ozone_destructors: "Ozone Destructors",
  sural: "Sural",
  joe: "Joe",
  ideas: "Ideas",
};

function StatusBadge({ status, onClick }: { status: string; onClick?: (e?: React.MouseEvent) => void }) {
  return (
    <button
      onClick={(e) => { if (onClick) onClick(e); }}
      className="px-2 py-0.5 rounded-full text-xs font-medium capitalize border cursor-pointer transition-opacity hover:opacity-80"
      style={{ borderColor: STATUS_COLORS[status] || "var(--border)", color: STATUS_COLORS[status] || "var(--text)" }}
    >
      {status}
    </button>
  );
}

function SongDetailPanel({ songId, onClose }: { songId: number; onClose: () => void }) {
  const { data: song } = useQuery({
    queryKey: ["song", songId],
    queryFn: () => api.repertoire.get(songId),
  });

  if (!song) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-96 border-l shadow-2xl z-50 overflow-y-auto p-6"
      style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-bold">{song.title}</h3>
          {song.artist && <p className="text-sm" style={{ color: "var(--text-muted)" }}>{song.artist}</p>}
        </div>
        <button onClick={onClose} className="p-1 rounded hover:bg-white/10">
          <X size={18} />
        </button>
      </div>

      <div className="space-y-4">
        <div className="flex gap-2">
          <StatusBadge status={song.status} />
          <span className="text-xs px-2 py-0.5 rounded-full border" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
            {song.is_original ? "Original" : "Cover"}
          </span>
        </div>

        {song.notes && <p className="text-sm" style={{ color: "var(--text-muted)" }}>{song.notes}</p>}

        {/* Audio files */}
        {song.audio_files.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-2">Recordings</h4>
            {song.audio_files.map((af) => (
              <div key={af.id} className="flex items-center gap-2 mb-2">
                <audio controls className="h-8 flex-1" style={{ filter: "invert(1) hue-rotate(180deg)" }}>
                  <source src={api.media.audioFileUrl(af.id)} />
                </audio>
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>
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
                  <span style={{ color: "var(--text-muted)" }}>{t.start_time} - {t.end_time}</span>
                </div>
                {t.audio_path && (
                  <audio controls className="w-full h-8" style={{ filter: "invert(1) hue-rotate(180deg)" }}>
                    <source src={api.media.takeAudioUrl(t.id)} />
                  </audio>
                )}
                {!t.audio_path && <span className="text-xs" style={{ color: "var(--text-muted)" }}>No audio export</span>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function Repertoire() {
  const [project, setProject] = useState("all");
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const queryClient = useQueryClient();

  const params: Record<string, string> = {};
  if (project !== "all") params.project = project;
  if (statusFilter) params.status = statusFilter;
  if (search) params.search = search;

  const { data: songs = [], isLoading } = useQuery({
    queryKey: ["repertoire", params],
    queryFn: () => api.repertoire.list(params),
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      api.repertoire.update(id, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["repertoire"] }),
  });

  const cycleStatus = (song: Song) => {
    const idx = STATUSES.indexOf(song.status);
    const next = STATUSES[(idx + 1) % STATUSES.length];
    updateStatus.mutate({ id: song.id, status: next });
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Repertoire</h2>

      {/* Filters */}
      <div className="flex gap-3 mb-6 flex-wrap">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
          <input
            type="text"
            placeholder="Search songs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-2 rounded-lg border text-sm bg-transparent outline-none focus:border-purple-500"
            style={{ borderColor: "var(--border)", color: "var(--text)" }}
          />
        </div>
        <select
          value={project}
          onChange={(e) => setProject(e.target.value)}
          className="px-3 py-2 rounded-lg border text-sm bg-transparent outline-none"
          style={{ borderColor: "var(--border)", color: "var(--text)", background: "var(--bg-card)" }}
        >
          {PROJECTS.map((p) => (
            <option key={p} value={p}>{PROJECT_LABELS[p]}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 rounded-lg border text-sm bg-transparent outline-none"
          style={{ borderColor: "var(--border)", color: "var(--text)", background: "var(--bg-card)" }}
        >
          <option value="">All Statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>
        <span className="self-center text-sm" style={{ color: "var(--text-muted)" }}>
          {songs.length} songs
        </span>
      </div>

      {/* Table */}
      {isLoading ? (
        <div style={{ color: "var(--text-muted)" }}>Loading...</div>
      ) : (
        <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--border)" }}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: "var(--bg-card)" }}>
                <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--text-muted)" }}>Song</th>
                <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--text-muted)" }}>Artist</th>
                <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--text-muted)" }}>Project</th>
                <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--text-muted)" }}>Status</th>
                <th className="text-center px-4 py-3 font-medium" style={{ color: "var(--text-muted)" }}>Practiced</th>
                <th className="text-center px-4 py-3 font-medium" style={{ color: "var(--text-muted)" }}>Takes</th>
              </tr>
            </thead>
            <tbody>
              {songs.map((song) => (
                <tr
                  key={song.id}
                  className="border-t cursor-pointer transition-colors"
                  style={{ borderColor: "var(--border)" }}
                  onClick={() => setSelectedId(song.id)}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <td className="px-4 py-3 font-medium flex items-center gap-2">
                    {song.has_audio ? <Play size={14} style={{ color: "var(--green)" }} /> : <Music size={14} style={{ color: "var(--text-muted)" }} />}
                    {song.title}
                  </td>
                  <td className="px-4 py-3" style={{ color: song.artist ? "var(--text)" : "var(--text-muted)" }}>
                    {song.artist || (song.is_original ? "Original" : "—")}
                  </td>
                  <td className="px-4 py-3" style={{ color: "var(--text-muted)" }}>
                    {PROJECT_LABELS[song.project] || song.project}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge
                      status={song.status}
                      onClick={(e) => { e?.stopPropagation(); cycleStatus(song); }}
                    />
                  </td>
                  <td className="px-4 py-3 text-center">{song.times_practiced || "—"}</td>
                  <td className="px-4 py-3 text-center">{song.take_count || "—"}</td>
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
