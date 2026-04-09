import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "../api/client";
import { Music, Radio, Star, Inbox, Disc3, PenTool, Lightbulb, FolderInput, Zap, Shield, Download, Hash, Wrench } from "lucide-react";

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

function DataProtectionCard() {
  const [checked, setChecked] = useState(false);
  const { data: health, refetch } = useQuery({
    queryKey: ["file-health"],
    queryFn: api.files.healthCheck,
    enabled: checked,
  });

  const { data: backupList } = useQuery({
    queryKey: ["backups"],
    queryFn: api.backup.list,
  });

  const backupMut = useMutation({ mutationFn: api.backup.create });
  const hashMut = useMutation({ mutationFn: api.backup.hashFiles });
  const healMut = useMutation({ mutationFn: api.backup.autoHeal });
  const exportMut = useMutation({ mutationFn: api.backup.export });
  const consolidateMut = useMutation({ mutationFn: api.files.consolidateAll });

  const latestBackup = backupList?.backups?.[0];

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <h3 className="font-semibold mb-4 flex items-center gap-2">
        <Shield size={18} style={{ color: "var(--green)" }} />
        Data Protection
      </h3>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        {/* Backup */}
        <button onClick={() => backupMut.mutate()}
          disabled={backupMut.isPending}
          className="p-3 rounded-lg border text-left hover:opacity-80 transition-opacity"
          style={{ borderColor: "var(--border)", background: "var(--bg)" }}>
          <Download size={16} className="mb-1" style={{ color: "var(--accent)" }} />
          <div className="text-sm font-medium">{backupMut.isPending ? "Backing up..." : "Backup DB"}</div>
          <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            {latestBackup ? `Last: ${latestBackup.created.split("T")[0]}` : "No backups yet"}
          </div>
          {backupMut.data && <div className="text-xs mt-1" style={{ color: "var(--green)" }}>Saved!</div>}
        </button>

        {/* Hash files */}
        <button onClick={() => hashMut.mutate()}
          disabled={hashMut.isPending}
          className="p-3 rounded-lg border text-left hover:opacity-80 transition-opacity"
          style={{ borderColor: "var(--border)", background: "var(--bg)" }}>
          <Hash size={16} className="mb-1" style={{ color: "var(--blue)" }} />
          <div className="text-sm font-medium">{hashMut.isPending ? "Hashing..." : "Hash Files"}</div>
          <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Fingerprint files for auto-heal</div>
          {hashMut.data && (
            <div className="text-xs mt-1" style={{ color: "var(--green)" }}>
              {hashMut.data.newly_hashed} new, {hashMut.data.already_hashed} cached
            </div>
          )}
        </button>

        {/* Health check + auto-heal */}
        <button onClick={() => { if (!checked) setChecked(true); else { refetch(); healMut.mutate(); } }}
          disabled={healMut.isPending}
          className="p-3 rounded-lg border text-left hover:opacity-80 transition-opacity"
          style={{ borderColor: "var(--border)", background: "var(--bg)" }}>
          <Wrench size={16} className="mb-1" style={{ color: "var(--yellow)" }} />
          <div className="text-sm font-medium">{healMut.isPending ? "Healing..." : "Check & Heal"}</div>
          <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            {health ? `${health.total_broken} broken` : "Find & fix broken paths"}
          </div>
          {healMut.data && (
            <div className="text-xs mt-1" style={{ color: "var(--green)" }}>
              {healMut.data.healed} healed, {healMut.data.unresolvable} unresolvable
            </div>
          )}
        </button>

        {/* Export */}
        <button onClick={() => exportMut.mutate()}
          disabled={exportMut.isPending}
          className="p-3 rounded-lg border text-left hover:opacity-80 transition-opacity"
          style={{ borderColor: "var(--border)", background: "var(--bg)" }}>
          <FolderInput size={16} className="mb-1" style={{ color: "var(--accent)" }} />
          <div className="text-sm font-medium">{exportMut.isPending ? "Exporting..." : "Export JSON"}</div>
          <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Save all annotations</div>
          {exportMut.data && (
            <div className="text-xs mt-1" style={{ color: "var(--green)" }}>
              {exportMut.data.songs} songs, {exportMut.data.takes} takes
            </div>
          )}
        </button>
      </div>

      {/* Consolidate */}
      <div className="flex items-center justify-between p-3 rounded-lg" style={{ background: "var(--bg)" }}>
        <div>
          <div className="text-sm font-medium">Consolidate scattered files</div>
          <div className="text-xs" style={{ color: "var(--text-muted)" }}>Move files from ~/Music, ~/Desktop into your organized directory</div>
        </div>
        <button onClick={() => consolidateMut.mutate()} disabled={consolidateMut.isPending}
          className="px-3 py-1.5 rounded text-sm font-medium text-white disabled:opacity-50"
          style={{ background: "var(--accent)" }}>
          {consolidateMut.isPending ? "Moving..." : "Consolidate"}
        </button>
      </div>
      {consolidateMut.data && (
        <div className="mt-2 text-xs" style={{ color: "var(--green)" }}>
          Moved {consolidateMut.data.moved} files ({consolidateMut.data.errors.length} errors)
        </div>
      )}

      {/* How it works */}
      <div className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
        <strong>How protection works:</strong> DB is auto-backed up every time the app starts (last {backupList?.backups?.length || 0} backups kept).
        Hash Files fingerprints each audio file so if you move it, Check & Heal can find it again by content.
        Export JSON saves all your annotations (ratings, lyrics, tags) as a portable file.
      </div>
    </div>
  );
}

const CATEGORY_ICONS: Record<string, string> = {
  practice: "🎸", improve: "📈", gig: "🎤", repertoire: "📋", learn: "📚",
};
const PRIORITY_COLORS: Record<string, string> = {
  high: "var(--red)", medium: "var(--yellow)", low: "var(--green)",
};
const CATEGORY_ORDER = ["improve", "gig", "practice", "repertoire", "learn"];

function RecommendationsCard() {
  const [filter, setFilter] = useState("all");
  const { data: recs = [] } = useQuery({
    queryKey: ["recommendations"],
    queryFn: api.recommendations.list,
  });

  // Group by category, limit practice to top 5
  const categories = [...new Set(recs.map(r => r.category))];
  const filtered = filter === "all" ? recs : recs.filter(r => r.category === filter);

  // For "all" view, show top recommendations per category
  const displayed = filter === "all"
    ? CATEGORY_ORDER.flatMap(cat => {
        const catRecs = recs.filter(r => r.category === cat);
        return cat === "practice" ? catRecs.slice(0, 5) : catRecs.slice(0, 3);
      })
    : filtered;

  return (
    <div className="rounded-xl p-5 border mb-8" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold flex items-center gap-2">
          <Zap size={18} style={{ color: "var(--accent)" }} />
          Recommendations ({recs.length})
        </h3>
        <div className="flex gap-1">
          <button onClick={() => setFilter("all")}
            className="px-2 py-1 rounded text-xs"
            style={{ background: filter === "all" ? "var(--accent)" : "var(--bg-hover)", color: filter === "all" ? "#fff" : "var(--text-muted)" }}>
            All
          </button>
          {categories.sort((a, b) => CATEGORY_ORDER.indexOf(a) - CATEGORY_ORDER.indexOf(b)).map(cat => (
            <button key={cat} onClick={() => setFilter(cat)}
              className="px-2 py-1 rounded text-xs capitalize"
              style={{ background: filter === cat ? "var(--accent)" : "var(--bg-hover)", color: filter === cat ? "#fff" : "var(--text-muted)" }}>
              {CATEGORY_ICONS[cat] || "•"} {cat}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2 max-h-80 overflow-y-auto">
        {displayed.map((rec, i) => (
          <div key={i} className="flex items-start gap-3 p-3 rounded-lg" style={{ background: "var(--bg)" }}>
            <div className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0" style={{ background: PRIORITY_COLORS[rec.priority] }} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{rec.title}</span>
                <span className="text-xs px-1.5 py-0.5 rounded capitalize" style={{ background: "var(--bg-hover)", color: "var(--text-muted)" }}>
                  {rec.category}
                </span>
              </div>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{rec.detail}</p>
            </div>
          </div>
        ))}
      </div>

      {filter === "all" && recs.length > displayed.length && (
        <p className="text-xs mt-3 text-center" style={{ color: "var(--text-muted)" }}>
          Showing top recommendations. Filter by category to see all {recs.length}.
        </p>
      )}
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

      {/* Data Protection */}
      <div className="mb-8">
        <DataProtectionCard />
      </div>

      {/* Recommendations */}
      <RecommendationsCard />

      {/* Songs by status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-8">
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
