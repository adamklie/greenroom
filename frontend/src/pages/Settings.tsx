import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { Plus, Trash2, GitMerge, Check, Zap } from "lucide-react";

const CATEGORIES = [
  { key: "source", label: "Sources", description: "Where audio files come from" },
  { key: "role", label: "Roles", description: "What role a recording plays" },
  { key: "project", label: "Projects", description: "Bands, collabs, contexts" },
  { key: "tuning", label: "Tunings", description: "Guitar tuning options" },
];

const inputStyle = { borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" };

function CategorySection({ category, label, description }: { category: string; label: string; description: string }) {
  const queryClient = useQueryClient();
  const [newValue, setNewValue] = useState("");
  const [newLabel, setNewLabel] = useState("");

  const { data: options = [] } = useQuery({
    queryKey: ["options", category],
    queryFn: () => api.options.list(category),
  });

  const createMut = useMutation({
    mutationFn: () => api.options.create(category, newValue.trim().toLowerCase().replace(/\s+/g, "_"), newLabel.trim() || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["options"] });
      setNewValue("");
      setNewLabel("");
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.options.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["options"] }),
  });

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <h3 className="font-semibold mb-1">{label}</h3>
      <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>{description}</p>

      <div className="space-y-1 mb-3">
        {options.map((opt) => (
          <div key={opt.id} className="flex items-center justify-between py-1.5 px-2 rounded text-sm"
            onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
            <div>
              <span className="font-mono text-xs" style={{ color: "var(--accent)" }}>{opt.value}</span>
              {opt.label && opt.label !== opt.value && (
                <span className="ml-2 text-xs" style={{ color: "var(--text-muted)" }}>{opt.label}</span>
              )}
              {opt.is_default && (
                <span className="ml-2 text-xs px-1 py-0.5 rounded" style={{ background: "var(--bg-hover)", color: "var(--text-muted)" }}>default</span>
              )}
            </div>
            {!opt.is_default && (
              <button onClick={() => deleteMut.mutate(opt.id)}
                className="p-1 rounded hover:bg-white/10 opacity-50 hover:opacity-100"
                style={{ color: "var(--red)" }}>
                <Trash2 size={12} />
              </button>
            )}
          </div>
        ))}
      </div>

      <form onSubmit={(e) => { e.preventDefault(); if (newValue.trim()) createMut.mutate(); }}
        className="flex gap-2">
        <input value={newValue} onChange={(e) => setNewValue(e.target.value)}
          placeholder="value_name"
          className="flex-1 px-2 py-1.5 rounded border text-sm font-mono outline-none" style={inputStyle} />
        <input value={newLabel} onChange={(e) => setNewLabel(e.target.value)}
          placeholder="Display Label (optional)"
          className="flex-1 px-2 py-1.5 rounded border text-sm outline-none" style={inputStyle} />
        <button type="submit" disabled={!newValue.trim()}
          className="flex items-center gap-1 px-3 py-1.5 rounded text-sm font-medium text-white disabled:opacity-50"
          style={{ background: "var(--accent)" }}>
          <Plus size={14} /> Add
        </button>
      </form>
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
    if (!confirm(`Auto-merge ${groups.length} duplicate groups? The entry with the most audio+takes will be kept in each group.`)) return;
    for (const group of groups) {
      // Pick the one with most content
      const best = [...group.entries].sort((a, b) =>
        (b.audio_count + b.take_count) - (a.audio_count + a.take_count)
      )[0];
      mergeGroup(group, best.id);
    }
  };

  if (isLoading) return <div style={{ color: "var(--text-muted)" }}>Scanning for duplicates...</div>;

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <div className="flex items-center justify-between mb-1">
        <h3 className="font-semibold flex items-center gap-2">
          <GitMerge size={16} /> Song Deduplication
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
          Songs with matching title + artist. Pick which to keep — audio files, takes, and metadata merge into it.
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
                    <th className="text-center py-1">Takes</th>
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

export default function Settings() {
  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold mb-2">Settings</h2>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        Manage dropdown options and categories used across the app
      </p>

      <div className="space-y-6">
        <DedupSection />
        {CATEGORIES.map(({ key, label, description }) => (
          <CategorySection key={key} category={key} label={label} description={description} />
        ))}
      </div>
    </div>
  );
}
