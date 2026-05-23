import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { Plus, Trash2 } from "lucide-react";

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

export default function Settings() {
  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold mb-2">Settings</h2>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        Manage dropdown options and categories used across the app
      </p>

      <div className="space-y-6">
        {CATEGORIES.map(({ key, label, description }) => (
          <CategorySection key={key} category={key} label={label} description={description} />
        ))}
      </div>
    </div>
  );
}
