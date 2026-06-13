import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2, RotateCcw, GitMerge, Check, Zap } from "lucide-react";
import { api } from "../api/client";

function TrashSection() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["trash"],
    queryFn: api.trash.list,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["trash"] });
    queryClient.invalidateQueries({ queryKey: ["songs"] });
    queryClient.invalidateQueries({ queryKey: ["audio-files"] });
  };

  const restoreSongMut = useMutation({
    mutationFn: (id: number) => api.trash.restoreSong(id),
    onSuccess: invalidate,
  });
  const purgeMut = useMutation({
    mutationFn: () => api.trash.purge(30),
    onSuccess: invalidate,
  });

  const songs = data?.deleted_songs ?? [];
  const files = data?.files ?? [];

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <div className="flex items-center justify-between mb-1">
        <h3 className="font-semibold flex items-center gap-2">
          <Trash2 size={16} style={{ color: "var(--accent)" }} /> Trash
        </h3>
        <button onClick={() => { if (confirm("Permanently delete everything trashed 30+ days ago?")) purgeMut.mutate(); }}
          disabled={purgeMut.isPending}
          className="px-3 py-1.5 rounded text-xs border disabled:opacity-50"
          style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
          {purgeMut.isPending ? "Purging…" : "Purge now (30d+)"}
        </button>
      </div>
      <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
        Soft-deleted songs and audio files. Items are permanently removed 30 days after deletion.
      </p>

      {isLoading ? <div style={{ color: "var(--text-muted)" }}>Loading…</div> : (
        <>
          <div className="mb-4">
            <div className="text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>Deleted songs ({songs.length})</div>
            {songs.length === 0 ? (
              <div className="text-xs" style={{ color: "var(--text-muted)" }}>None</div>
            ) : (
              <div className="space-y-1">
                {songs.map((s) => (
                  <div key={s.id} className="flex items-center justify-between text-sm py-1 border-t" style={{ borderColor: "var(--border)" }}>
                    <span>{s.title}{s.type ? <span style={{ color: "var(--text-muted)" }}> ({s.type})</span> : null}</span>
                    <button onClick={() => restoreSongMut.mutate(s.id)}
                      className="flex items-center gap-1 px-2 py-0.5 rounded text-xs"
                      style={{ color: "var(--green, #22c55e)" }}>
                      <RotateCcw size={12} /> Restore
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <div className="text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>Trashed files ({files.length})</div>
            {files.length === 0 ? (
              <div className="text-xs" style={{ color: "var(--text-muted)" }}>None</div>
            ) : (
              <div className="space-y-1">
                {files.map((f) => (
                  <div key={f.filename} className="flex items-center justify-between text-xs py-1 border-t" style={{ borderColor: "var(--border)" }}>
                    <span className="font-mono truncate max-w-xs">{f.filename}</span>
                    <span style={{ color: "var(--text-muted)" }}>{f.size_mb} MB · purges in {f.days_until_purge}d</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function DedupSection() {
  const queryClient = useQueryClient();
  const [fuzzy, setFuzzy] = useState(false);
  const { data: groups = [], isLoading } = useQuery({
    queryKey: ["dedup", fuzzy],
    queryFn: () => api.dedup.duplicates(fuzzy),
  });

  const [selections, setSelections] = useState<Record<string, number>>({});

  const mergeMut = useMutation({
    mutationFn: ({ keepId, mergeIds }: { keepId: number; mergeIds: number[] }) =>
      api.dedup.merge(keepId, mergeIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dedup"] });
      queryClient.invalidateQueries({ queryKey: ["songs"] });
      queryClient.invalidateQueries({ queryKey: ["audio-files"] });
    },
  });

  const mergeGroup = (group: typeof groups[0], keepId: number) => {
    const mergeIds = group.entries.filter(e => e.id !== keepId).map(e => e.id);
    mergeMut.mutate({ keepId, mergeIds });
  };

  const autoMergeAll = () => {
    if (!confirm(`Auto-merge ${groups.length} duplicate groups? The entry with the most audio+tracks will be kept in each group.`)) return;
    for (const group of groups) {
      const best = [...group.entries].sort((a, b) =>
        (b.audio_count + b.take_count) - (a.audio_count + a.take_count)
      )[0];
      mergeGroup(group, best.id);
    }
  };

  if (isLoading) return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <div style={{ color: "var(--text-muted)" }}>Scanning for duplicates...</div>
    </div>
  );

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <div className="flex items-center justify-between mb-1">
        <h3 className="font-semibold flex items-center gap-2">
          <GitMerge size={16} style={{ color: "var(--accent)" }} /> Song Deduplication
        </h3>
        {groups.length > 0 && (
          <button onClick={autoMergeAll}
            className="flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium text-white"
            style={{ background: "var(--accent)" }}>
            <Zap size={12} /> Auto-Merge All ({groups.length})
          </button>
        )}
      </div>
      <div className="flex items-center gap-3 mb-4">
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          Songs with matching title + artist. Pick which to keep — audio files, tracks, and metadata merge into it. Merged-away songs go to Trash (restorable for 30 days).
        </p>
        <label className="flex items-center gap-1.5 text-xs cursor-pointer whitespace-nowrap">
          <input type="checkbox" checked={fuzzy} onChange={(e) => setFuzzy(e.target.checked)} />
          Fuzzy matching
        </label>
      </div>

      {groups.length === 0 && (
        <div className="text-center py-6">
          <Check size={24} className="mx-auto mb-2" style={{ color: "var(--green)" }} />
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>No duplicates found</p>
        </div>
      )}

      <div className="space-y-4">
        {groups.map((group) => {
          const selected = selections[group.key] || group.entries[0]?.id;
          return (
            <div key={group.key} className="rounded-lg border p-3" style={{ borderColor: "var(--border)" }}>
              <div className="text-sm font-medium mb-2">
                {group.entries[0].title}
                {group.entries[0].artist && <span style={{ color: "var(--text-muted)" }}> — {group.entries[0].artist}</span>}
                <span className="text-xs ml-2 px-1.5 py-0.5 rounded" style={{ background: "var(--bg-hover)", color: "var(--text-muted)" }}>
                  {group.entries.length} entries
                </span>
              </div>

              <table className="w-full text-xs mb-2">
                <thead>
                  <tr style={{ color: "var(--text-muted)" }}>
                    <th className="text-left py-1 w-8">Keep</th>
                    <th className="text-left py-1">ID</th>
                    <th className="text-left py-1">Type</th>
                    <th className="text-left py-1">Status</th>
                    <th className="text-left py-1">Project</th>
                    <th className="text-center py-1">Audio</th>
                    <th className="text-center py-1">Tracks</th>
                    <th className="text-left py-1">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {group.entries.map((entry) => (
                    <tr key={entry.id} className="border-t" style={{ borderColor: "var(--border)",
                      background: selected === entry.id ? "rgba(139,92,246,0.08)" : "transparent" }}>
                      <td className="py-1.5">
                        <input type="radio" name={`keep-${group.key}`}
                          checked={selected === entry.id}
                          onChange={() => setSelections(s => ({ ...s, [group.key]: entry.id }))} />
                      </td>
                      <td className="py-1.5" style={{ color: "var(--accent)" }}>{entry.id}</td>
                      <td className="py-1.5">{entry.type || "—"}</td>
                      <td className="py-1.5">{entry.status || "—"}</td>
                      <td className="py-1.5">{entry.project || "—"}</td>
                      <td className="py-1.5 text-center">{entry.audio_count}</td>
                      <td className="py-1.5 text-center">{entry.take_count}</td>
                      <td className="py-1.5 truncate max-w-32" style={{ color: "var(--text-muted)" }}>
                        {entry.notes || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <button onClick={() => mergeGroup(group, selected)}
                disabled={mergeMut.isPending}
                className="flex items-center gap-1 px-3 py-1 rounded text-xs font-medium text-white disabled:opacity-50"
                style={{ background: "var(--green)" }}>
                <GitMerge size={11} /> Merge into #{selected}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function Trash() {
  return (
    <div className="max-w-3xl">
      <h2 className="text-2xl font-bold mb-2">Trash & Cleanup</h2>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        Restore or purge deleted items, and merge duplicate songs.
      </p>
      <div className="space-y-6">
        <TrashSection />
        <DedupSection />
      </div>
    </div>
  );
}
