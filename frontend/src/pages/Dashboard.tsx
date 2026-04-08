import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type RoadmapPhase } from "../api/client";
import { CheckCircle2, Circle, Music, Radio, Star, Mic } from "lucide-react";

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

function PhaseCard({ phase }: { phase: RoadmapPhase }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ id, completed }: { id: number; completed: boolean }) =>
      api.roadmap.toggleTask(id, completed),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
  });

  const pct = phase.total > 0 ? Math.round((phase.completed / phase.total) * 100) : 0;

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold">Phase {phase.phase}: {phase.phase_title}</h3>
        <span className="text-sm px-2 py-0.5 rounded-full" style={{
          background: pct === 100 ? "var(--green)" : "var(--bg-hover)",
          color: pct === 100 ? "#000" : "var(--text-muted)",
        }}>
          {phase.completed}/{phase.total}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 rounded-full mb-4" style={{ background: "var(--bg-hover)" }}>
        <div className="h-full rounded-full transition-all" style={{
          width: `${pct}%`,
          background: `var(--accent)`,
        }} />
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto">
        {phase.tasks.map((t) => (
          <button
            key={t.id}
            onClick={() => mutation.mutate({ id: t.id, completed: !t.completed })}
            className="flex items-start gap-2 text-sm w-full text-left hover:opacity-80 transition-opacity"
          >
            {t.completed
              ? <CheckCircle2 size={16} className="mt-0.5 flex-shrink-0" style={{ color: "var(--green)" }} />
              : <Circle size={16} className="mt-0.5 flex-shrink-0" style={{ color: "var(--text-muted)" }} />
            }
            <span style={{ color: t.completed ? "var(--text-muted)" : "var(--text)", textDecoration: t.completed ? "line-through" : "none" }}>
              {t.task_text}
            </span>
          </button>
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

  const { stats, roadmap } = data;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Songs" value={stats.total_songs} icon={Music} color="var(--accent)" />
        <StatCard label="Practice Sessions" value={stats.total_sessions} icon={Radio} color="var(--blue)" />
        <StatCard label="Gig-Ready Songs" value={stats.gig_ready_songs} icon={Mic} color="var(--green)" />
        <StatCard label="Unrated Takes" value={stats.unrated_takes} icon={Star} color="var(--yellow)" />
      </div>

      {/* Songs by status */}
      <div className="rounded-xl p-5 border mb-8" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <h3 className="font-semibold mb-3">Songs by Status</h3>
        <div className="flex gap-6">
          {Object.entries(stats.songs_by_status).map(([status, count]) => (
            <div key={status} className="text-center">
              <div className="text-2xl font-bold">{count}</div>
              <div className="text-xs capitalize" style={{ color: "var(--text-muted)" }}>{status}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Roadmap */}
      <h3 className="text-xl font-semibold mb-4">Roadmap</h3>
      <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
        Click any task to toggle its completion
      </p>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {roadmap.map((phase) => (
          <PhaseCard key={phase.phase} phase={phase} />
        ))}
      </div>
    </div>
  );
}
