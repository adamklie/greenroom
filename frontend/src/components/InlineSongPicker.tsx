import { useState, useMemo } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { api } from "../api/client";

export type SongOption = { id: number; title: string; artist: string | null; type: string };

const inputStyle = { borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" };

/**
 * Searchable song combobox with inline "create new song". Rendered inline (not
 * absolutely positioned) so it can't get clipped by a parent's overflow. Lifted
 * out of the Library page so Import, Process, and Library all share one picker.
 *
 * `createExtra` is merged into the create payload — e.g. Import passes the
 * chosen project so a song created here lands in the right project.
 */
export function InlineSongPicker({ songs, onSave, onSongCreated, onCancel, createExtra, allowCreate = true }: {
  songs: SongOption[];
  onSave: (songId: number | null) => void;
  onSongCreated: () => void;
  onCancel?: () => void;
  createExtra?: Record<string, unknown>;
  allowCreate?: boolean;
}) {
  const [creating, setCreating] = useState(false);
  const [query, setQuery] = useState("");
  const [title, setTitle] = useState("");
  const [artist, setArtist] = useState("");
  const [type, setType] = useState("cover");

  const queryClient = useQueryClient();
  const createMut = useMutation({
    mutationFn: () => api.songs.create({ title, artist: artist || null, type, status: type === "idea" ? "captured" : "idea", ...createExtra }),
    onSuccess: (newSong) => {
      onSave(newSong.id);
      setCreating(false);
      setTitle("");
      setArtist("");
      queryClient.invalidateQueries({ queryKey: ["songs-all"] });
      onSongCreated();
    },
  });

  // Alphabetical by title, then filtered by the search query (title or artist).
  const filtered = useMemo(() => {
    const sorted = [...songs].sort((a, b) => a.title.localeCompare(b.title));
    const q = query.trim().toLowerCase();
    if (!q) return sorted;
    return sorted.filter(s =>
      s.title.toLowerCase().includes(q) || (s.artist || "").toLowerCase().includes(q)
    );
  }, [songs, query]);

  if (creating) {
    return (
      <div className="flex flex-col gap-1">
        <input autoFocus value={title} onChange={(e) => setTitle(e.target.value)}
          placeholder="Song title..."
          onKeyDown={(e) => { if (e.key === "Enter" && title.trim()) createMut.mutate(); if (e.key === "Escape") setCreating(false); }}
          className="w-full px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle} />
        <div className="flex gap-1">
          <select value={type} onChange={(e) => setType(e.target.value)}
            className="px-1 py-0.5 rounded border text-xs outline-none bg-transparent flex-1" style={inputStyle}>
            <option value="cover">Cover</option>
            <option value="original">Original</option>
            <option value="idea">Idea</option>
          </select>
          <input value={artist} onChange={(e) => setArtist(e.target.value)}
            placeholder="Artist..."
            onKeyDown={(e) => { if (e.key === "Enter" && title.trim()) createMut.mutate(); }}
            className="px-1 py-0.5 rounded border text-xs outline-none bg-transparent flex-1" style={inputStyle} />
        </div>
        <div className="flex gap-1">
          <button onClick={() => createMut.mutate()} disabled={!title.trim()}
            className="px-2 py-0.5 rounded text-xs text-white disabled:opacity-50" style={{ background: "var(--accent)" }}>
            Create & Link
          </button>
          <button onClick={() => setCreating(false)} className="px-2 py-0.5 rounded text-xs" style={{ color: "var(--text-muted)" }}>
            <X size={10} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1" style={{ minWidth: 200 }}>
      <input autoFocus value={query} onChange={(e) => setQuery(e.target.value)}
        placeholder="Search songs…"
        onKeyDown={(e) => {
          if (e.key === "Enter" && filtered.length) onSave(filtered[0].id);
          if (e.key === "Escape") onCancel?.();
        }}
        onBlur={() => { if (onCancel) setTimeout(onCancel, 150); }}
        className="w-full px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle} />
      <div className="max-h-48 overflow-y-auto rounded border" style={{ borderColor: "var(--border)", background: "var(--bg-card)" }}>
        <button onMouseDown={(e) => e.preventDefault()} onClick={() => onSave(null)}
          className="block w-full text-left px-2 py-1 text-xs hover:bg-white/10" style={{ color: "var(--text-muted)" }}>
          — Unlink
        </button>
        {filtered.slice(0, 50).map(s => (
          <button key={s.id} onMouseDown={(e) => e.preventDefault()} onClick={() => onSave(s.id)}
            className="block w-full text-left px-2 py-1 text-xs hover:bg-white/10 truncate">
            {s.title}{s.artist ? <span style={{ color: "var(--text-muted)" }}> — {s.artist}</span> : null}
            {s.type ? <span style={{ color: "var(--text-muted)" }}> ({s.type})</span> : null}
          </button>
        ))}
        {allowCreate && (
          <button onMouseDown={(e) => e.preventDefault()}
            onClick={() => { setTitle(query); setCreating(true); }}
            className="flex items-center gap-1 w-full text-left px-2 py-1 text-xs hover:bg-white/10 border-t"
            style={{ color: "var(--accent)", borderColor: "var(--border)" }}>
            <Plus size={11} /> Create{query.trim() ? ` "${query.trim()}"` : " new song"}
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Drop-in song selector: shows the linked song as a button; clicking opens the
 * searchable InlineSongPicker. Use anywhere a song needs to be picked.
 */
export function SongSelect({ songs, value, onChange, onSongCreated, createExtra, allowCreate = true, placeholder = "Link to song…", className }: {
  songs: SongOption[];
  value: number | null;
  onChange: (songId: number | null) => void;
  onSongCreated?: () => void;
  createExtra?: Record<string, unknown>;
  allowCreate?: boolean;
  placeholder?: string;
  className?: string;
}) {
  const [editing, setEditing] = useState(false);
  const selected = songs.find((s) => s.id === value) || null;

  if (editing) {
    return (
      <InlineSongPicker
        songs={songs}
        createExtra={createExtra}
        allowCreate={allowCreate}
        onSave={(id) => { onChange(id); setEditing(false); }}
        onSongCreated={() => onSongCreated?.()}
        onCancel={() => setEditing(false)}
      />
    );
  }

  return (
    <button type="button" onClick={() => setEditing(true)}
      className={className ?? "px-2 py-1 rounded border text-xs text-left outline-none"}
      style={inputStyle}>
      {selected ? (
        <span>{selected.title}{selected.artist ? <span style={{ color: "var(--text-muted)" }}> — {selected.artist}</span> : null}</span>
      ) : (
        <span style={{ color: "var(--text-muted)" }}>{placeholder}</span>
      )}
    </button>
  );
}
