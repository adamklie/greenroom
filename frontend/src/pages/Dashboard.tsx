import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "../api/client";
import { Music, Radio, Star, Inbox, Disc3, PenTool, Lightbulb, AlertTriangle, FolderInput, Check } from "lucide-react";

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

function FileHealthCard() {
  const [checked, setChecked] = useState(false);
  const { data: health, refetch } = useQuery({
    queryKey: ["file-health"],
    queryFn: api.files.healthCheck,
    enabled: checked,
  });

  const consolidateMut = useMutation({
    mutationFn: api.files.consolidateAll,
  });

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold flex items-center gap-2">
          <AlertTriangle size={18} style={{ color: "var(--yellow)" }} />
          File Health
        </h3>
        <div className="flex gap-2">
          {!checked ? (
            <button onClick={() => setChecked(true)}
              className="px-3 py-1.5 rounded text-sm border hover:opacity-80"
              style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
              Run Check
            </button>
          ) : (
            <button onClick={() => refetch()}
              className="px-3 py-1.5 rounded text-sm border hover:opacity-80"
              style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
              Recheck
            </button>
          )}
        </div>
      </div>

      {!checked && (
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Checks for files that have been moved or deleted since last scan.
        </p>
      )}

      {health && (
        <div>
          {health.total_broken === 0 ? (
            <div className="flex items-center gap-2 text-sm" style={{ color: "var(--green)" }}>
              <Check size={16} /> All {health.broken_links.length === 0 ? "file links are healthy" : "clear"}
            </div>
          ) : (
            <div>
              <p className="text-sm mb-2" style={{ color: "var(--red)" }}>
                {health.total_broken} broken link{health.total_broken > 1 ? "s" : ""} found
              </p>
              <div className="max-h-32 overflow-y-auto space-y-1 mb-3">
                {health.broken_links.slice(0, 10).map((b, i) => (
                  <div key={i} className="text-xs truncate" style={{ color: "var(--text-muted)" }}>
                    {b.song_title || "Unknown"}: {b.path.split("/").pop()}
                  </div>
                ))}
                {health.total_broken > 10 && (
                  <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                    ...and {health.total_broken - 10} more
                  </div>
                )}
              </div>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                Try "Rescan Files" to re-link, or check if files were moved/deleted.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Consolidate */}
      <div className="mt-4 pt-4 border-t" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-medium flex items-center gap-2">
              <FolderInput size={16} style={{ color: "var(--accent)" }} />
              Consolidate Files
            </h4>
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              Move scattered files (~/Music, ~/Desktop) into your organized music directory
            </p>
          </div>
          <button
            onClick={() => consolidateMut.mutate()}
            disabled={consolidateMut.isPending}
            className="px-3 py-1.5 rounded text-sm font-medium text-white disabled:opacity-50"
            style={{ background: "var(--accent)" }}>
            {consolidateMut.isPending ? "Moving..." : "Consolidate"}
          </button>
        </div>
        {consolidateMut.data && (
          <div className="mt-2 text-sm" style={{ color: "var(--green)" }}>
            Moved {consolidateMut.data.moved} files
            {consolidateMut.data.errors.length > 0 && (
              <span style={{ color: "var(--red)" }}> ({consolidateMut.data.errors.length} errors)</span>
            )}
          </div>
        )}
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
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>

      {/* Top stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Songs" value={stats.total_songs} icon={Music} color="var(--accent)" />
        <StatCard label="Practice Sessions" value={stats.total_sessions} icon={Radio} color="var(--blue)" />
        <StatCard label="Unrated Takes" value={stats.unrated_takes} icon={Star} color="var(--yellow)" />
        <StatCard label="Triage Queue" value={stats.triage_pending} icon={Inbox} color="var(--red)" />
      </div>

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

      {/* File Health + Consolidate */}
      <div className="mb-8">
        <FileHealthCard />
      </div>

      {/* Songs by status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
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
    </div>
  );
}
