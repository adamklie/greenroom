import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, type RecentSong, type RecentAudioFile, type RecentSession } from "../api/client";
import { Music, Radio, Disc3, PenTool, Lightbulb, Target, ArrowRight, Clock, FileAudio, CalendarDays, Upload } from "lucide-react";

function StatCard({ label, value, icon: Icon, color }: {
  label: string; value: number | string; icon: React.ElementType; color: string;
}) {
  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm" style={{ color: "var(--text-muted)" }}>{label}</span>
        <Icon size={18} style={{ color }} />
      </div>
      <div className="text-3xl font-bold">{value}</div>
    </div>
  );
}

const STATUS_COLORS: Record<string, string> = {
  idea: "var(--text-muted)", learning: "var(--blue)", rehearsed: "var(--yellow)",
  polished: "var(--blue)", recorded: "var(--green)", released: "var(--accent)",
  captured: "var(--text-muted)", developing: "var(--yellow)", promoted: "var(--green)",
  draft: "var(--text-muted)", arranged: "var(--yellow)",
};

const TYPE_ROUTES: Record<string, string> = {
  cover: "/covers", original: "/originals", idea: "/ideas",
};

function FocusSongs() {
  const { data: focusSongs = [] } = useQuery({
    queryKey: ["songs", { tag: "focus" }],
    queryFn: () => api.songs.list({ tag: "focus" }),
  });

  if (focusSongs.length === 0) {
    return (
      <div className="rounded-xl p-5 border mb-8" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <h3 className="font-semibold flex items-center gap-2 mb-2">
          <Target size={18} style={{ color: "var(--accent)" }} />
          Focus Songs
        </h3>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Tag up to 3 songs with <strong>"focus"</strong> to pin them here. Open any song and add the tag from the detail panel.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl p-5 border mb-8" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <h3 className="font-semibold flex items-center gap-2 mb-4">
        <Target size={18} style={{ color: "var(--accent)" }} />
        Focus Songs
      </h3>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {focusSongs.slice(0, 3).map((song) => (
          <a key={song.id} href={`${TYPE_ROUTES[song.type] || "/covers"}?song=${song.id}`}
            className="block rounded-lg p-4 border hover:opacity-80 transition-opacity"
            style={{ borderColor: "var(--border)", background: "var(--bg)" }}>
            <div className="flex items-start justify-between mb-2">
              <div>
                <div className="font-semibold text-sm">{song.title}</div>
                {song.artist && <div className="text-xs" style={{ color: "var(--text-muted)" }}>{song.artist}</div>}
              </div>
              <ArrowRight size={14} style={{ color: "var(--accent)" }} />
            </div>
            <div className="flex flex-wrap gap-2 mb-2">
              <span className="px-2 py-0.5 rounded-full text-xs capitalize border"
                style={{ borderColor: STATUS_COLORS[song.status] || "var(--border)", color: STATUS_COLORS[song.status] || "var(--text)" }}>
                {song.status}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full capitalize"
                style={{ background: "var(--bg-hover)", color: "var(--text-muted)" }}>
                {song.type}
              </span>
            </div>
            <div className="flex gap-4 text-xs" style={{ color: "var(--text-muted)" }}>
              {song.key && <span>Key: {song.key}</span>}
              {song.tempo_bpm && <span>{song.tempo_bpm} BPM</span>}
              <span>{song.take_count} takes</span>
              {song.has_audio && <span style={{ color: "var(--green)" }}>Has audio</span>}
            </div>
            {song.notes && (
              <p className="text-xs mt-2 line-clamp-2" style={{ color: "var(--text-muted)" }}>
                {song.notes}
              </p>
            )}
          </a>
        ))}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.dashboard.get,
  });

  if (isLoading) return <div style={{ color: "var(--text-muted)" }}>Loading...</div>;
  if (error || !data) return <div style={{ color: "var(--red)" }}>Error loading dashboard</div>;

  const { stats } = data;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <Link to="/import"
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white"
          style={{ background: "var(--accent)" }}>
          <Upload size={16} /> Import
        </Link>
      </div>

      {/* Focus Songs */}
      <FocusSongs />

      {/* Top stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
        <StatCard label="Total Songs" value={stats.total_songs} icon={Music} color="var(--accent)" />
        <StatCard label="Practice Sessions" value={stats.total_sessions} icon={Radio} color="var(--blue)" />
      </div>

      {/* Recent additions */}
      <RecentAdditions
        songs={data.recent_songs}
        audioFiles={data.recent_audio_files}
        sessions={data.recent_sessions}
      />

      {/* Three pillars */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <div className="flex items-center gap-2 mb-2">
            <Disc3 size={18} style={{ color: "var(--blue)" }} />
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>Covers</span>
          </div>
          <div className="text-3xl font-bold">{stats.songs_by_type["cover"] || 0}</div>
        </div>
        <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <div className="flex items-center gap-2 mb-2">
            <PenTool size={18} style={{ color: "var(--green)" }} />
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>Originals</span>
          </div>
          <div className="text-3xl font-bold">{stats.songs_by_type["original"] || 0}</div>
        </div>
        <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <div className="flex items-center gap-2 mb-2">
            <Lightbulb size={18} style={{ color: "var(--yellow)" }} />
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>Ideas</span>
          </div>
          <div className="text-3xl font-bold">{stats.songs_by_type["idea"] || 0}</div>
        </div>
      </div>

      {/* Songs by project */}
      <div className="rounded-xl p-5 border mt-8" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <h3 className="font-semibold mb-3">Songs by Project</h3>
        <div className="flex gap-6 flex-wrap">
          {Object.entries(stats.songs_by_project).map(([project, count]) => (
            <div key={project} className="text-center">
              <div className="text-2xl font-bold">{count}</div>
              <div className="text-xs capitalize" style={{ color: "var(--text-muted)" }}>
                {project.replace("_", " ")}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function RecentAdditions({
  songs, audioFiles, sessions,
}: {
  songs: RecentSong[];
  audioFiles: RecentAudioFile[];
  sessions: RecentSession[];
}) {
  const fmt = (ts: string | null) => {
    if (!ts) return "";
    const d = new Date(ts);
    if (isNaN(d.valueOf())) return "";
    return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };
  const songTypePath = (t: string) => t === "cover" ? "covers" : t === "original" ? "originals" : "ideas";
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
      <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 font-semibold">
            <Music size={16} style={{ color: "var(--accent)" }} />
            <span>Recent Songs</span>
          </div>
          <Link to="/library" className="text-xs" style={{ color: "var(--text-muted)" }}>all →</Link>
        </div>
        <div className="space-y-2">
          {songs.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>None</p>}
          {songs.map((s) => (
            <Link key={s.id} to={`/${songTypePath(s.type)}?song=${s.id}`}
              className="flex items-center justify-between text-sm hover:opacity-80">
              <div className="min-w-0 flex-1 truncate">
                <span className="font-medium">{s.title}</span>
                {s.artist && <span style={{ color: "var(--text-muted)" }}> — {s.artist}</span>}
              </div>
              <span className="text-xs ml-2 flex-shrink-0" style={{ color: "var(--text-muted)" }}>{fmt(s.created_at)}</span>
            </Link>
          ))}
        </div>
      </div>

      <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 font-semibold">
            <FileAudio size={16} style={{ color: "var(--blue)" }} />
            <span>Recent Audio Files</span>
          </div>
          <Link to="/library" className="text-xs" style={{ color: "var(--text-muted)" }}>all →</Link>
        </div>
        <div className="space-y-2">
          {audioFiles.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>None</p>}
          {audioFiles.map((a) => (
            <Link key={a.id} to={`/library?search=${encodeURIComponent(a.identifier || a.file_path.split("/").pop() || "")}`}
              className="flex items-center justify-between text-sm hover:opacity-80">
              <div className="min-w-0 flex-1 truncate">
                <span className="font-medium">{a.song_title || a.file_path.split("/").pop()}</span>
                <span className="text-xs ml-2" style={{ color: "var(--text-muted)" }}>{a.file_type}</span>
              </div>
              <span className="text-xs ml-2 flex-shrink-0" style={{ color: "var(--text-muted)" }}>{fmt(a.created_at)}</span>
            </Link>
          ))}
        </div>
      </div>

      <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 font-semibold">
            <CalendarDays size={16} style={{ color: "var(--green)" }} />
            <span>Recent Sessions</span>
          </div>
          <Link to="/sessions" className="text-xs" style={{ color: "var(--text-muted)" }}>all →</Link>
        </div>
        <div className="space-y-2">
          {sessions.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>None</p>}
          {sessions.map((s) => (
            <Link key={s.id} to="/sessions" className="flex items-center justify-between text-sm hover:opacity-80">
              <div className="flex items-center gap-2 min-w-0 flex-1 truncate">
                <Clock size={12} style={{ color: "var(--text-muted)" }} />
                <span className="font-medium">{s.date}</span>
                <span className="text-xs truncate" style={{ color: "var(--text-muted)" }}>
                  {s.folder_path.split("/").pop()}
                </span>
              </div>
              <span className="text-xs ml-2 flex-shrink-0" style={{ color: "var(--text-muted)" }}>{s.clip_count} clips</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
