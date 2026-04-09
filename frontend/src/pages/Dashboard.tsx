import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Music, Radio, Star, Inbox, Disc3, PenTool, Lightbulb } from "lucide-react";

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
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>

      {/* Top stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Songs" value={stats.total_songs} icon={Music} color="var(--accent)" />
        <StatCard label="Practice Sessions" value={stats.total_sessions} icon={Radio} color="var(--blue)" />
        <StatCard label="Unrated Takes" value={stats.unrated_takes} icon={Star} color="var(--yellow)" />
        <StatCard label="Triage Queue" value={stats.triage_pending} icon={Inbox} color="var(--red)" />
      </div>

      {/* Songs by type */}
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

      {/* Songs by status */}
      <div className="rounded-xl p-5 border mb-8" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <h3 className="font-semibold mb-3">Songs by Status</h3>
        <div className="flex gap-6 flex-wrap">
          {Object.entries(stats.songs_by_status).map(([status, count]) => (
            <div key={status} className="text-center">
              <div className="text-2xl font-bold">{count}</div>
              <div className="text-xs capitalize" style={{ color: "var(--text-muted)" }}>{status}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Songs by project */}
      <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
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
