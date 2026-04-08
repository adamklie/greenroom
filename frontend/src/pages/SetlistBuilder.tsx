import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Song, type Setlist } from "../api/client";
import { Plus, Trash2, Clock, GripVertical, X, ListMusic } from "lucide-react";

interface DraftItem {
  song_id: number;
  duration_minutes: number;
  song_title: string;
  song_artist: string | null;
}

const CONFIG_LABELS: Record<string, string> = {
  solo: "Solo (Guitar + Vocals)",
  duo: "Duo",
  full_band: "Full Band (Trio)",
};

function SetlistCard({ setlist, onSelect }: { setlist: Setlist; onSelect: () => void }) {
  const queryClient = useQueryClient();
  const deleteMut = useMutation({
    mutationFn: () => api.setlists.delete(setlist.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["setlists"] }),
  });

  return (
    <div
      className="rounded-xl p-5 border cursor-pointer transition-colors"
      style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
      onClick={onSelect}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
    >
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-semibold">{setlist.name}</h3>
        <button
          onClick={(e) => { e.stopPropagation(); deleteMut.mutate(); }}
          className="p-1 rounded hover:bg-white/10"
          style={{ color: "var(--text-muted)" }}
        >
          <Trash2 size={14} />
        </button>
      </div>
      <div className="flex gap-4 text-sm" style={{ color: "var(--text-muted)" }}>
        <span>{setlist.song_count} songs</span>
        <span className="flex items-center gap-1"><Clock size={14} /> {setlist.total_minutes} min</span>
        <span>{CONFIG_LABELS[setlist.config] || setlist.config}</span>
      </div>
      {setlist.items.length > 0 && (
        <div className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
          {setlist.items.slice(0, 5).map((item, i) => (
            <span key={item.id}>{i > 0 ? " → " : ""}{item.song_title}</span>
          ))}
          {setlist.items.length > 5 && <span> +{setlist.items.length - 5} more</span>}
        </div>
      )}
    </div>
  );
}

function SetlistEditor({ setlist, songs, onBack }: { setlist: Setlist; songs: Song[]; onBack: () => void }) {
  const queryClient = useQueryClient();
  const [items, setItems] = useState<DraftItem[]>(
    setlist.items.map((i) => ({
      song_id: i.song_id,
      duration_minutes: i.duration_minutes,
      song_title: i.song_title || "Unknown",
      song_artist: i.song_artist,
    }))
  );
  const [name, setName] = useState(setlist.name);
  const [config, setConfig] = useState(setlist.config);
  const [addingSong, setAddingSong] = useState(false);
  const [searchText, setSearchText] = useState("");

  const saveMut = useMutation({
    mutationFn: () =>
      api.setlists.update(setlist.id, {
        name,
        config,
        items: items.map((item, i) => ({
          song_id: item.song_id,
          position: i,
          duration_minutes: item.duration_minutes,
        })),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["setlists"] }),
  });

  const totalMinutes = items.reduce((sum, i) => sum + i.duration_minutes, 0);

  const addSong = (song: Song) => {
    setItems([...items, {
      song_id: song.id,
      duration_minutes: 4,
      song_title: song.title,
      song_artist: song.artist,
    }]);
    setAddingSong(false);
    setSearchText("");
  };

  const removeSong = (idx: number) => {
    setItems(items.filter((_, i) => i !== idx));
  };

  const moveSong = (idx: number, dir: -1 | 1) => {
    const newIdx = idx + dir;
    if (newIdx < 0 || newIdx >= items.length) return;
    const copy = [...items];
    [copy[idx], copy[newIdx]] = [copy[newIdx], copy[idx]];
    setItems(copy);
  };

  const updateDuration = (idx: number, mins: number) => {
    const copy = [...items];
    copy[idx] = { ...copy[idx], duration_minutes: Math.max(1, mins) };
    setItems(copy);
  };

  const filteredSongs = songs.filter((s) => {
    if (!searchText) return true;
    const q = searchText.toLowerCase();
    return s.title.toLowerCase().includes(q) || (s.artist && s.artist.toLowerCase().includes(q));
  });

  const inputStyle = { borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" };

  return (
    <div>
      <button onClick={onBack} className="text-sm mb-4 flex items-center gap-1" style={{ color: "var(--text-muted)" }}>
        ← Back to setlists
      </button>

      {/* Header */}
      <div className="flex gap-3 mb-6">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="text-xl font-bold bg-transparent border-b outline-none flex-1 pb-1"
          style={{ borderColor: "var(--border)", color: "var(--text)" }}
        />
        <select value={config} onChange={(e) => setConfig(e.target.value)}
          className="px-3 py-1 rounded-lg border text-sm outline-none" style={inputStyle}>
          {Object.entries(CONFIG_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <button
          onClick={() => saveMut.mutate()}
          className="px-4 py-2 rounded-lg text-sm font-medium text-white"
          style={{ background: "var(--accent)" }}
        >
          {saveMut.isPending ? "Saving..." : "Save"}
        </button>
      </div>

      {/* Stats bar */}
      <div className="flex gap-6 mb-6 text-sm" style={{ color: "var(--text-muted)" }}>
        <span>{items.length} songs</span>
        <span className="flex items-center gap-1"><Clock size={14} /> {totalMinutes} min ({Math.floor(totalMinutes / 60)}h {totalMinutes % 60}m)</span>
      </div>

      {/* Song list */}
      <div className="space-y-2 mb-4">
        {items.map((item, idx) => (
          <div key={`${item.song_id}-${idx}`} className="flex items-center gap-3 rounded-lg p-3 border group"
            style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
            <div className="flex flex-col gap-0.5">
              <button onClick={() => moveSong(idx, -1)} className="text-xs px-1 hover:opacity-80" style={{ color: "var(--text-muted)" }}>▲</button>
              <button onClick={() => moveSong(idx, 1)} className="text-xs px-1 hover:opacity-80" style={{ color: "var(--text-muted)" }}>▼</button>
            </div>
            <GripVertical size={16} style={{ color: "var(--text-muted)" }} />
            <span className="w-6 text-sm text-center" style={{ color: "var(--text-muted)" }}>{idx + 1}</span>
            <div className="flex-1">
              <span className="font-medium text-sm">{item.song_title}</span>
              {item.song_artist && <span className="text-sm ml-2" style={{ color: "var(--text-muted)" }}>— {item.song_artist}</span>}
            </div>
            <div className="flex items-center gap-1">
              <input
                type="number"
                value={item.duration_minutes}
                onChange={(e) => updateDuration(idx, parseInt(e.target.value) || 1)}
                className="w-12 text-center text-sm rounded border bg-transparent outline-none"
                style={inputStyle}
                min={1}
              />
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>min</span>
            </div>
            <button onClick={() => removeSong(idx)} className="p-1 rounded hover:bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity"
              style={{ color: "var(--red)" }}>
              <X size={16} />
            </button>
          </div>
        ))}
      </div>

      {/* Add song */}
      {!addingSong ? (
        <button onClick={() => setAddingSong(true)}
          className="w-full flex items-center justify-center gap-2 p-3 rounded-lg border border-dashed text-sm transition-colors hover:opacity-80"
          style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
          <Plus size={16} /> Add Song
        </button>
      ) : (
        <div className="rounded-lg border p-4" style={{ background: "var(--bg-card)", borderColor: "var(--accent)" }}>
          <input
            autoFocus
            placeholder="Search songs to add..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border text-sm bg-transparent outline-none mb-3"
            style={inputStyle}
          />
          <div className="max-h-48 overflow-y-auto space-y-1">
            {filteredSongs.slice(0, 20).map((song) => (
              <button key={song.id} onClick={() => addSong(song)}
                className="w-full text-left px-3 py-2 rounded text-sm flex justify-between hover:opacity-80 transition-opacity"
                style={{ color: "var(--text)" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <span>{song.title}{song.artist ? ` — ${song.artist}` : ""}</span>
                <span className="text-xs capitalize" style={{ color: "var(--text-muted)" }}>{song.status}</span>
              </button>
            ))}
          </div>
          <button onClick={() => { setAddingSong(false); setSearchText(""); }}
            className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>Cancel</button>
        </div>
      )}
    </div>
  );
}

export default function SetlistBuilder() {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const queryClient = useQueryClient();

  const { data: setlists = [], isLoading } = useQuery({
    queryKey: ["setlists"],
    queryFn: api.setlists.list,
  });

  const { data: songs = [] } = useQuery({
    queryKey: ["repertoire"],
    queryFn: () => api.repertoire.list(),
  });

  const createMut = useMutation({
    mutationFn: () => api.setlists.create({ name: newName || "New Setlist" }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["setlists"] });
      setSelectedId(data.id);
      setCreating(false);
      setNewName("");
    },
  });

  const selectedSetlist = setlists.find((s) => s.id === selectedId);

  if (isLoading) return <div style={{ color: "var(--text-muted)" }}>Loading...</div>;

  if (selectedSetlist) {
    return <SetlistEditor setlist={selectedSetlist} songs={songs} onBack={() => setSelectedId(null)} />;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Setlists</h2>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white"
          style={{ background: "var(--accent)" }}
        >
          <Plus size={16} /> New Setlist
        </button>
      </div>

      {creating && (
        <div className="rounded-xl p-4 border mb-4 flex gap-3" style={{ background: "var(--bg-card)", borderColor: "var(--accent)" }}>
          <input
            autoFocus
            placeholder="Setlist name..."
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && createMut.mutate()}
            className="flex-1 px-3 py-2 rounded-lg border text-sm bg-transparent outline-none"
            style={{ borderColor: "var(--border)", color: "var(--text)" }}
          />
          <button onClick={() => createMut.mutate()}
            className="px-4 py-2 rounded-lg text-sm font-medium text-white" style={{ background: "var(--accent)" }}>
            Create
          </button>
          <button onClick={() => { setCreating(false); setNewName(""); }}
            className="px-4 py-2 rounded-lg text-sm border" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
            Cancel
          </button>
        </div>
      )}

      {setlists.length === 0 && !creating && (
        <div className="text-center py-16 rounded-xl border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <div className="mx-auto w-12 h-12 rounded-full flex items-center justify-center mb-3" style={{ background: "var(--bg-hover)" }}>
            <ListMusic size={24} style={{ color: "var(--text-muted)" }} />
          </div>
          <p className="font-medium">No setlists yet</p>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Create a setlist to plan your gigs and open mic performances
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {setlists.map((s) => (
          <SetlistCard key={s.id} setlist={s} onSelect={() => setSelectedId(s.id)} />
        ))}
      </div>
    </div>
  );
}
