import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { RefreshCw, Check, AlertTriangle, CloudUpload, Music, Shield, HardDrive, FolderTree, ArrowRight } from "lucide-react";

const STATUS_ICON: Record<string, React.ReactNode> = {
  ok: <Check size={14} style={{ color: "var(--green)" }} />,
  warning: <AlertTriangle size={14} style={{ color: "var(--yellow)" }} />,
  error: <AlertTriangle size={14} style={{ color: "var(--red)" }} />,
  skipped: <span className="text-xs" style={{ color: "var(--text-muted)" }}>—</span>,
};

const STEP_LABELS: Record<string, string> = {
  rescan: "Scan for new files",
  hash: "Fingerprint files",
  health: "Check file links",
  export: "Export annotations",
  backup: "Backup database",
  git_commit: "Save to version history",
  git_push: "Push to cloud",
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

const TYPE_COLORS: Record<string, string> = { cover: "var(--blue)", original: "var(--green)", idea: "var(--yellow)" };

function ReorganizeSection() {
  const [showPreview, setShowPreview] = useState(false);

  const { data: preview, refetch } = useQuery({
    queryKey: ["reorganize-preview"],
    queryFn: api.reorganize.preview,
    enabled: showPreview,
  });

  const executeMut = useMutation({
    mutationFn: () => api.reorganize.execute(),
    onSuccess: () => refetch(),
  });

  return (
    <div className="rounded-xl p-5 border mb-6" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold flex items-center gap-2">
          <FolderTree size={18} style={{ color: "var(--accent)" }} />
          Organize Files
        </h3>
        {!showPreview ? (
          <button onClick={() => setShowPreview(true)}
            className="px-3 py-1.5 rounded text-sm border hover:opacity-80"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
            Preview Changes
          </button>
        ) : (
          <button onClick={() => refetch()}
            className="px-3 py-1.5 rounded text-sm border hover:opacity-80"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
            Refresh
          </button>
        )}
      </div>

      <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
        Reorganize your files to match the database structure:
        <strong> Covers/</strong> (by artist), <strong>Originals/</strong> (by title), <strong>Ideas/</strong>
      </p>

      {!showPreview && (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          Click "Preview Changes" to see what would move. Nothing happens until you approve.
        </p>
      )}

      {preview && (
        <div>
          {/* Summary */}
          <div className="flex gap-4 mb-4 text-sm">
            <span style={{ color: "var(--accent)" }}><strong>{preview.total_moves}</strong> files to move</span>
            <span style={{ color: "var(--green)" }}><strong>{preview.already_organized}</strong> already organized</span>
            {preview.unlinked_files > 0 && (
              <span style={{ color: "var(--yellow)" }}><strong>{preview.unlinked_files}</strong> unlinked (classify in Triage first)</span>
            )}
            {preview.missing_files > 0 && (
              <span style={{ color: "var(--red)" }}><strong>{preview.missing_files}</strong> missing</span>
            )}
          </div>

          {/* Move list */}
          {preview.moves.length > 0 && (
            <>
              <div className="max-h-64 overflow-y-auto space-y-1 mb-4 rounded-lg p-2" style={{ background: "var(--bg)" }}>
                {preview.moves.map((m) => (
                  <div key={m.audio_file_id} className="flex items-center gap-2 text-xs py-1">
                    <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: TYPE_COLORS[m.song_type || ""] || "var(--text-muted)" }} />
                    <span className="truncate flex-1" style={{ color: "var(--text-muted)" }}>
                      {m.current_path.split("/").pop()}
                    </span>
                    <ArrowRight size={12} style={{ color: "var(--text-muted)" }} />
                    <span className="truncate flex-1 font-medium">
                      {m.proposed_path}
                    </span>
                  </div>
                ))}
              </div>

              <button onClick={() => executeMut.mutate()}
                disabled={executeMut.isPending}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-sm font-medium text-white disabled:opacity-50"
                style={{ background: "var(--accent)" }}>
                <FolderTree size={16} />
                {executeMut.isPending ? "Organizing..." : `Organize ${preview.total_moves} Files`}
              </button>
            </>
          )}

          {preview.moves.length === 0 && (
            <div className="flex items-center gap-2 text-sm" style={{ color: "var(--green)" }}>
              <Check size={16} /> All files are already organized!
            </div>
          )}

          {executeMut.data && (
            <div className="mt-3 p-3 rounded-lg" style={{ background: "var(--bg)" }}>
              <p className="text-sm" style={{ color: "var(--green)" }}>
                Moved {executeMut.data.moved} files
              </p>
              {executeMut.data.errors.length > 0 && (
                <div className="mt-1">
                  {executeMut.data.errors.map((e, i) => (
                    <p key={i} className="text-xs" style={{ color: "var(--red)" }}>{e}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
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

  const pushMut = useMutation({
    mutationFn: api.sync.gitPush,
  });

  const isRunning = afterPracticeMut.isPending || weeklyMut.isPending;
  const results = afterPracticeMut.data?.steps || weeklyMut.data?.steps || [];
  const hasUnpushed = results.some(s => s.step === "git_push" && s.status === "warning");

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold mb-2">Sync & Backup</h2>
      <p className="text-sm mb-8" style={{ color: "var(--text-muted)" }}>
        Keep your music library safe and in sync
      </p>

      {/* How it works */}
      <div className="rounded-xl p-5 border mb-6" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <h3 className="font-semibold mb-3">How your data is protected</h3>
        <div className="space-y-3 text-sm">
          <div className="flex items-start gap-3">
            <HardDrive size={18} className="mt-0.5 flex-shrink-0" style={{ color: "var(--blue)" }} />
            <div>
              <strong>Your audio & video files</strong> are in iCloud Drive. Apple syncs them automatically.
              <span style={{ color: "var(--text-muted)" }}> You don't need to do anything for this.</span>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <Shield size={18} className="mt-0.5 flex-shrink-0" style={{ color: "var(--green)" }} />
            <div>
              <strong>Your annotations</strong> (ratings, lyrics, tags, notes) are in the local database.
              <span style={{ color: "var(--text-muted)" }}> These need to be backed up — that's what the buttons below do.</span>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <CloudUpload size={18} className="mt-0.5 flex-shrink-0" style={{ color: "var(--accent)" }} />
            <div>
              <strong>Git push</strong> sends your annotation backup to GitHub for safekeeping.
              <span style={{ color: "var(--text-muted)" }}> This is your off-site backup.</span>
            </div>
          </div>
        </div>
      </div>

      {/* Action buttons */}
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
                  Scan new files, fingerprint, export annotations, backup database
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
                  Everything above + check for broken links, portfolio summary
                </div>
              </div>
            </div>
            {weeklyMut.isPending && <RefreshCw size={18} className="animate-spin" style={{ color: "var(--blue)" }} />}
            {lastAction === "weekly" && !isRunning && <Check size={18} style={{ color: "var(--green)" }} />}
          </div>
        </button>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="rounded-xl p-5 border mb-6" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <h3 className="font-semibold mb-3">Results</h3>
          <div className="divide-y" style={{ borderColor: "var(--border)" }}>
            {results.map((step, i) => <StepResult key={i} step={step} />)}
          </div>

          {/* Git push button */}
          {hasUnpushed && (
            <div className="mt-4 pt-4 border-t" style={{ borderColor: "var(--border)" }}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">Unpushed changes</div>
                  <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                    Push to GitHub to complete your off-site backup
                  </div>
                </div>
                <button onClick={() => pushMut.mutate()}
                  disabled={pushMut.isPending}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white"
                  style={{ background: "var(--accent)" }}>
                  <CloudUpload size={14} />
                  {pushMut.isPending ? "Pushing..." : "Push to GitHub"}
                </button>
              </div>
              {pushMut.data && (
                <p className="text-xs mt-2" style={{ color: pushMut.data.ok ? "var(--green)" : "var(--red)" }}>
                  {pushMut.data.detail}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Reorganize files */}
      <ReorganizeSection />

      {/* Storage tips */}
      <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <h3 className="font-semibold mb-3">Free up disk space</h3>
        <div className="text-sm space-y-2" style={{ color: "var(--text-muted)" }}>
          <p>Your music files are now synced to iCloud. To free up local disk space:</p>
          <ol className="list-decimal list-inside space-y-1">
            <li><strong>System Settings → Apple Account → iCloud → Optimize Mac Storage</strong> — Apple will automatically remove local copies of files you haven't opened recently, keeping them in the cloud</li>
            <li><strong>Right-click any file in Finder → "Remove Download"</strong> — manually offload specific large files (GoPro videos you've already processed are good candidates)</li>
            <li>Files show a cloud icon (☁️) in Finder when they're offloaded — they download again instantly when you open them</li>
          </ol>
          <p className="mt-2"><strong>Safe to offload:</strong> Old GoPro raw files you've already cut into clips, backing tracks you rarely play, old session recordings.</p>
          <p><strong>Keep local:</strong> Files you're actively working with, anything you need offline.</p>
        </div>
      </div>
    </div>
  );
}
