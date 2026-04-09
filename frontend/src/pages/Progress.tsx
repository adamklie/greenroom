import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  AreaChart, Area, CartesianGrid,
} from "recharts";
import { TrendingUp, Calendar, Target, BarChart3 } from "lucide-react";

const CHART_COLORS = {
  accent: "#8b5cf6",
  green: "#22c55e",
  blue: "#3b82f6",
  yellow: "#eab308",
  text: "#71717a",
  grid: "#2a2e3f",
};

function PracticeHeatmap() {
  const { data = [] } = useQuery({
    queryKey: ["practice-frequency"],
    queryFn: api.analytics.practiceFrequency,
  });

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <h3 className="font-semibold mb-4 flex items-center gap-2">
        <Calendar size={18} style={{ color: CHART_COLORS.blue }} />
        Practice Sessions Over Time
      </h3>
      {data.length === 0 ? (
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>No session data yet</p>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
            <XAxis dataKey="date" tick={{ fill: CHART_COLORS.text, fontSize: 11 }}
              tickFormatter={(d) => { const p = d.split("-"); return `${p[1]}/${p[2]}`; }} />
            <YAxis tick={{ fill: CHART_COLORS.text, fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: "#1a1d27", border: "1px solid #2a2e3f", borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: "#e4e4e7" }}
            />
            <Bar dataKey="takes" fill={CHART_COLORS.accent} radius={[4, 4, 0, 0]} name="Takes" />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function SkillRadar() {
  const { data } = useQuery({
    queryKey: ["skill-radar"],
    queryFn: api.analytics.skillRadar,
  });

  if (!data) return null;

  const hasData = Object.values(data).some(d => d.average !== null);

  const radarData = Object.entries(data).map(([dim, { average, count }]) => ({
    dimension: dim.charAt(0).toUpperCase() + dim.slice(1),
    value: average || 0,
    count,
  }));

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <h3 className="font-semibold mb-4 flex items-center gap-2">
        <Target size={18} style={{ color: CHART_COLORS.green }} />
        Skill Radar
      </h3>
      {!hasData ? (
        <div className="text-center py-8">
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Rate your takes in Sessions to populate this chart.
          </p>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Each dimension needs at least one rated take.
          </p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <RadarChart data={radarData}>
            <PolarGrid stroke={CHART_COLORS.grid} />
            <PolarAngleAxis dataKey="dimension" tick={{ fill: CHART_COLORS.text, fontSize: 11 }} />
            <PolarRadiusAxis domain={[0, 5]} tick={{ fill: CHART_COLORS.text, fontSize: 10 }} />
            <Radar dataKey="value" stroke={CHART_COLORS.accent} fill={CHART_COLORS.accent} fillOpacity={0.3} name="Avg Rating" />
          </RadarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function SongProgressTable() {
  const { data = [] } = useQuery({
    queryKey: ["song-progress"],
    queryFn: api.analytics.songProgress,
  });

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <h3 className="font-semibold mb-4 flex items-center gap-2">
        <TrendingUp size={18} style={{ color: CHART_COLORS.yellow }} />
        Most Practiced Songs
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th className="text-left px-3 py-2 font-medium" style={{ color: "var(--text-muted)" }}>Song</th>
              <th className="text-center px-3 py-2 font-medium" style={{ color: "var(--text-muted)" }}>Takes</th>
              <th className="text-center px-3 py-2 font-medium" style={{ color: "var(--text-muted)" }}>Avg Rating</th>
              <th className="text-center px-3 py-2 font-medium" style={{ color: "var(--text-muted)" }}>Status</th>
              <th className="text-right px-3 py-2 font-medium" style={{ color: "var(--text-muted)" }}>Last Practiced</th>
            </tr>
          </thead>
          <tbody>
            {data.slice(0, 20).map((s) => (
              <tr key={s.song_id} className="border-t" style={{ borderColor: "var(--border)" }}>
                <td className="px-3 py-2 font-medium">{s.title}</td>
                <td className="px-3 py-2 text-center">{s.take_count}</td>
                <td className="px-3 py-2 text-center">
                  {s.avg_rating ? (
                    <span style={{ color: CHART_COLORS.yellow }}>
                      {s.avg_rating.toFixed(1)} {"★".repeat(Math.round(s.avg_rating))}
                    </span>
                  ) : (
                    <span style={{ color: "var(--text-muted)" }}>—</span>
                  )}
                </td>
                <td className="px-3 py-2 text-center">
                  <span className="px-2 py-0.5 rounded-full text-xs capitalize border"
                    style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
                    {s.status}
                  </span>
                </td>
                <td className="px-3 py-2 text-right" style={{ color: "var(--text-muted)" }}>
                  {s.last_practiced || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatusFunnel() {
  const { data = [] } = useQuery({
    queryKey: ["status-funnel"],
    queryFn: api.analytics.statusFunnel,
  });

  const maxCount = Math.max(...data.map(d => d.count), 1);

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <h3 className="font-semibold mb-4 flex items-center gap-2">
        <BarChart3 size={18} style={{ color: CHART_COLORS.accent }} />
        Status Pipeline
      </h3>
      <div className="space-y-2">
        {data.map((d) => (
          <div key={d.status}>
            <div className="flex justify-between text-sm mb-1">
              <span className="capitalize">{d.status}</span>
              <span style={{ color: "var(--text-muted)" }}>{d.count} songs</span>
            </div>
            <div className="h-3 rounded-full" style={{ background: "var(--bg-hover)" }}>
              <div className="h-full rounded-full transition-all"
                style={{ width: `${(d.count / maxCount) * 100}%`, background: CHART_COLORS.accent }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SessionTimeline() {
  const { data = [] } = useQuery({
    queryKey: ["session-summary"],
    queryFn: api.analytics.sessionSummary,
  });

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <h3 className="font-semibold mb-4">Session Intensity Over Time</h3>
      {data.length === 0 ? (
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>No sessions yet</p>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
            <XAxis dataKey="date" tick={{ fill: CHART_COLORS.text, fontSize: 11 }}
              tickFormatter={(d) => { const p = d.split("-"); return `${p[1]}/${p[2]}`; }} />
            <YAxis tick={{ fill: CHART_COLORS.text, fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: "#1a1d27", border: "1px solid #2a2e3f", borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: "#e4e4e7" }}
            />
            <Area type="monotone" dataKey="take_count" stroke={CHART_COLORS.blue} fill={CHART_COLORS.blue}
              fillOpacity={0.2} name="Takes per session" />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export default function Progress() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Practice Progress</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <PracticeHeatmap />
        <SkillRadar />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <SessionTimeline />
        <StatusFunnel />
      </div>

      <SongProgressTable />
    </div>
  );
}
