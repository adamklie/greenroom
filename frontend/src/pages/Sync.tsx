import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../api/client";
import { RefreshCw, Check, AlertTriangle, Music, Shield, HardDrive } from "lucide-react";

const STATUS_ICON: Record<string, React.ReactNode> = {
  ok: <Check size={14} style={{ color: "var(--green)" }} />,
  warning: <AlertTriangle size={14} style={{ color: "var(--yellow)" }} />,
  error: <AlertTriangle size={14} style={{ color: "var(--red)" }} />,
  skipped: <span className="text-xs" style={{ color: "var(--text-muted)" }}>—</span>,
};

const STEP_LABELS: Record<string, string> = {
  export: "Export annotations",
  backup: "Backup database",
  summary: "Portfolio summary",
};

interface Step {
  step: string;
  status: string;
  detail: string | Record<string, number>;
}

function StepResult({ step }: { step: Step }) {
  const detail = typeof step.detail === "object"
    ? Object.entries(step.detail).map(([k, v]) => `${k}: ${v}`).join(", ")
    : step.detail;

  return (
    <div className="flex items-center gap-3 py-2">
      {STATUS_ICON[step.status] || STATUS_ICON.ok}
      <span className="text-sm font-medium w-48">{STEP_LABELS[step.step] || step.step}</span>
      <span className="text-sm" style={{ color: "var(--text-muted)" }}>{detail}</span>
    </div>
  );
}

export default function Sync() {
  const [lastAction, setLastAction] = useState<string | null>(null);

  const afterPracticeMut = useMutation({
    mutationFn: api.sync.afterPractice,
    onSuccess: () => setLastAction("after-practice"),
  });

  const weeklyMut = useMutation({
    mutationFn: api.sync.weekly,
    onSuccess: () => setLastAction("weekly"),
  });

  const isRunning = afterPracticeMut.isPending || weeklyMut.isPending;
  const results = afterPracticeMut.data?.steps || weeklyMut.data?.steps || [];

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold mb-2">Sync & Backup</h2>
      <p className="text-sm mb-8" style={{ color: "var(--text-muted)" }}>
        Export annotations and snapshot the database to iCloud
      </p>

      <div className="rounded-xl p-5 border mb-6" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <h3 className="font-semibold mb-3">How your data is protected</h3>
        <div className="space-y-3 text-sm">
          <div className="flex items-start gap-3">
            <HardDrive size={18} className="mt-0.5 flex-shrink-0" style={{ color: "var(--blue)" }} />
            <div>
              <strong>Audio &amp; video files</strong> live in the iCloud vault. Apple syncs them automatically across devices.
            </div>
          </div>
          <div className="flex items-start gap-3">
            <Shield size={18} className="mt-0.5 flex-shrink-0" style={{ color: "var(--green)" }} />
            <div>
              <strong>Annotations</strong> (ratings, lyrics, tags, notes) live in the local database. The buttons below snapshot them into iCloud so a fresh machine can restore everything.
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 mb-6">
        <button onClick={() => afterPracticeMut.mutate()}
          disabled={isRunning}
          className="rounded-xl p-5 border text-left transition-colors hover:opacity-90 disabled:opacity-50"
          style={{ background: "var(--bg-card)", borderColor: lastAction === "after-practice" ? "var(--green)" : "var(--border)" }}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: "rgba(139, 92, 246, 0.15)" }}>
                <Music size={20} style={{ color: "var(--accent)" }} />
              </div>
              <div>
                <div className="font-semibold">After Practice</div>
                <div className="text-sm" style={{ color: "var(--text-muted)" }}>
                  Export annotations + backup DB
                </div>
              </div>
            </div>
            {afterPracticeMut.isPending && <RefreshCw size={18} className="animate-spin" style={{ color: "var(--accent)" }} />}
            {lastAction === "after-practice" && !isRunning && <Check size={18} style={{ color: "var(--green)" }} />}
          </div>
        </button>

        <button onClick={() => weeklyMut.mutate()}
          disabled={isRunning}
          className="rounded-xl p-5 border text-left transition-colors hover:opacity-90 disabled:opacity-50"
          style={{ background: "var(--bg-card)", borderColor: lastAction === "weekly" ? "var(--green)" : "var(--border)" }}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: "rgba(59, 130, 246, 0.15)" }}>
                <Shield size={20} style={{ color: "var(--blue)" }} />
              </div>
              <div>
                <div className="font-semibold">Weekly Check</div>
                <div className="text-sm" style={{ color: "var(--text-muted)" }}>
                  Snapshot + portfolio summary
                </div>
              </div>
            </div>
            {weeklyMut.isPending && <RefreshCw size={18} className="animate-spin" style={{ color: "var(--blue)" }} />}
            {lastAction === "weekly" && !isRunning && <Check size={18} style={{ color: "var(--green)" }} />}
          </div>
        </button>
      </div>

      {results.length > 0 && (
        <div className="rounded-xl p-5 border mb-6" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <h3 className="font-semibold mb-3">Results</h3>
          <div className="divide-y" style={{ borderColor: "var(--border)" }}>
            {results.map((step, i) => <StepResult key={i} step={step} />)}
          </div>
        </div>
      )}

      <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <h3 className="font-semibold mb-3">Free up disk space</h3>
        <div className="text-sm space-y-2" style={{ color: "var(--text-muted)" }}>
          <p>Vault files live in iCloud Drive. To free up local disk:</p>
          <ol className="list-decimal list-inside space-y-1">
            <li><strong>System Settings → Apple Account → iCloud → Optimize Mac Storage</strong> — Apple evicts local copies of files you haven't opened recently</li>
            <li><strong>Right-click any file in Finder → "Remove Download"</strong> — manually offload large items (old GoPro raws, rarely-played backing tracks)</li>
            <li>Offloaded files show a cloud icon in Finder; they download on demand when the app asks for them</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
