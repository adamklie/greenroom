import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Info, Palette, Download } from "lucide-react";
import { api } from "../api/client";

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between items-baseline py-1.5">
      <span className="text-sm" style={{ color: "var(--text-muted)" }}>{label}</span>
      <span className="text-sm font-mono">{value}</span>
    </div>
  );
}

function AppInfo() {
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: api.health.get,
  });
  const { data: dashboard } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.dashboard.get,
  });
  const { data: tags = [] } = useQuery({
    queryKey: ["tags-all"],
    queryFn: () => api.tags.list(),
  });
  const { data: backupList } = useQuery({
    queryKey: ["backups"],
    queryFn: api.backup.list,
  });

  const stats = dashboard?.stats;
  const latestBackup = backupList?.backups?.[0];

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <h3 className="font-semibold mb-3 flex items-center gap-2">
        <Info size={16} style={{ color: "var(--accent)" }} />
        App Info
      </h3>
      <div className="divide-y" style={{ borderColor: "var(--border)" }}>
        <StatRow label="Backend version" value={health?.version ?? "—"} />
        <StatRow label="Total songs" value={stats?.total_songs ?? "—"} />
        <StatRow label="Total recordings (audio files)" value={stats?.total_audio_files ?? "—"} />
        <StatRow label="Total sessions" value={stats?.total_sessions ?? "—"} />
        <StatRow label="Total tags" value={tags.length} />
        <StatRow
          label="Last backup"
          value={latestBackup ? new Date(latestBackup.created).toLocaleString() : "none"}
        />
      </div>
    </div>
  );
}

function Appearance() {
  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <h3 className="font-semibold mb-3 flex items-center gap-2">
        <Palette size={16} style={{ color: "var(--accent)" }} />
        Appearance
      </h3>
      <div className="flex items-center justify-between py-1.5 opacity-60">
        <div>
          <div className="text-sm">Light mode</div>
          <div className="text-xs" style={{ color: "var(--text-muted)" }}>
            Switch the app to a light color theme
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="text-xs px-2 py-0.5 rounded-full"
            style={{ background: "var(--bg-hover)", color: "var(--text-muted)" }}
          >
            Coming soon
          </span>
          <button
            disabled
            aria-label="Toggle light mode"
            className="relative w-10 h-5 rounded-full border cursor-not-allowed"
            style={{ borderColor: "var(--border)", background: "var(--bg)" }}
          >
            <span
              className="absolute top-0.5 left-0.5 w-4 h-4 rounded-full"
              style={{ background: "var(--text-muted)" }}
            />
          </button>
        </div>
      </div>
    </div>
  );
}

function DataBackup() {
  const [state, setState] = useState<"idle" | "downloading" | "done" | "error">("idle");
  const [error, setError] = useState<string>("");

  const handleExport = async () => {
    setState("downloading");
    setError("");
    try {
      const r = await fetch("/api/backup/export-download", { credentials: "include" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `greenroom-export-${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setState("done");
    } catch (err) {
      setState("error");
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <h3 className="font-semibold mb-3 flex items-center gap-2">
        <Download size={16} style={{ color: "var(--accent)" }} />
        Data Backup
      </h3>
      <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
        Save every song, recording, rating, and lyric annotation as a single
        portable JSON file. Useful for offline backup or migrating elsewhere.
        Database itself is continuously replicated to cloud storage in the
        background; this is a human-readable extra.
      </p>
      <button
        onClick={handleExport}
        disabled={state === "downloading"}
        className="px-4 py-2 rounded text-sm font-medium text-white disabled:opacity-50"
        style={{ background: "var(--accent)" }}>
        {state === "downloading" ? "Preparing…" : "Export JSON"}
      </button>
      {state === "done" && (
        <span className="ml-3 text-xs" style={{ color: "var(--green)" }}>Downloaded</span>
      )}
      {state === "error" && (
        <span className="ml-3 text-xs" style={{ color: "var(--red)" }}>Failed: {error}</span>
      )}
    </div>
  );
}

export default function Settings() {
  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold mb-2">Settings</h2>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        App-level configuration and status
      </p>

      <div className="space-y-6">
        <AppInfo />
        <DataBackup />
        <Appearance />
      </div>

      <p className="text-xs mt-6" style={{ color: "var(--text-muted)" }}>
        More settings will live here as the app evolves (vault location, rating dimensions, etc.).
      </p>
    </div>
  );
}
