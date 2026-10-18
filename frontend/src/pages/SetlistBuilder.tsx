import { useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { api, type Link, type Song, type Setlist, type SetlistItem } from "../api/client";
import { Plus, Trash2, Clock, GripVertical, X, ListMusic, Upload, Pencil, Link2, Play, FileText, MonitorPlay } from "lucide-react";
import MoveToProjectMenu from "../components/MoveToProjectMenu";
import LinkChips from "../components/LinkChips";
import LinksEditor from "../components/LinksEditor";
import BulkChartUpload from "../components/BulkChartUpload";

interface DraftSong {
  kind: "song";
  song_id: number;
  duration_minutes: number;
  notes: string;
  links: Link[];
  song_title: string;
  song_artist: string | null;
}

// A divider row in the editor; every song below it (until the next divider)
// is saved with this section label.
interface DraftSection {
  kind: "section";
  name: string;
}

type DraftEntry = DraftSong | DraftSection;

function toEntries(items: SetlistItem[]): DraftEntry[] {
  const entries: DraftEntry[] = [];
  let current: string | null = null;
  for (const i of items) {
    if (i.section !== current) {
      entries.push({ kind: "section", name: i.section || "" });
      current = i.section;
    }
    entries.push({
      kind: "song",
      song_id: i.song_id,
      duration_minutes: i.duration_minutes,
      notes: i.notes || "",
      links: i.links,
      song_title: i.song_title || "Unknown",
      song_artist: i.song_artist,
    });
  }
  return entries;
}

/** Consecutive items sharing a section label form one group. */
function groupBySection(items: SetlistItem[]) {
  const groups: { section: string | null; items: SetlistItem[] }[] = [];
  for (const item of items) {
    const last = groups[groups.length - 1];
    if (last && last.section === item.section) last.items.push(item);
    else groups.push({ section: item.section, items: [item] });
  }
  return groups;
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
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <MoveToProjectMenu kind="setlist" ids={[setlist.id]} compact />
          <button
            onClick={(e) => { e.stopPropagation(); deleteMut.mutate(); }}
            className="p-1 rounded hover:bg-white/10"
            style={{ color: "var(--text-muted)" }}
          >
            <Trash2 size={14} />
          </button>
        </div>
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

function SetlistEditor({ setlist, songs, onDone }: { setlist: Setlist; songs: Song[]; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [entries, setEntries] = useState<DraftEntry[]>(() => toEntries(setlist.items));
  const [name, setName] = useState(setlist.name);
  const [config, setConfig] = useState(setlist.config);
  const [addingSong, setAddingSong] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [linksOpen, setLinksOpen] = useState<number | null>(null);

  const items = entries.filter((e): e is DraftSong => e.kind === "song");

  const saveMut = useMutation({
    mutationFn: () => {
      let section: string | null = null;
      const payload = [];
      for (const e of entries) {
        if (e.kind === "section") {
          section = e.name.trim() || null;
          continue;
        }
        payload.push({
          song_id: e.song_id,
          position: payload.length,
          duration_minutes: e.duration_minutes,
          notes: e.notes.trim() || null,
          section,
          links: e.links.filter((l) => l.url.trim()),
        });
      }
      return api.setlists.update(setlist.id, { name, config, items: payload });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["setlists"] });
      onDone();
    },
  });

  const totalMinutes = items.reduce((sum, i) => sum + i.duration_minutes, 0);

  const addSong = (song: Song) => {
    setEntries([...entries, {
      kind: "song",
      song_id: song.id,
      duration_minutes: 4,
      notes: "",
      links: [],
      song_title: song.title,
      song_artist: song.artist,
    }]);
    setAddingSong(false);
    setSearchText("");
  };

  const removeEntry = (idx: number) => {
    setEntries(entries.filter((_, i) => i !== idx));
  };

  const moveEntry = (idx: number, dir: -1 | 1) => {
    const newIdx = idx + dir;
    if (newIdx < 0 || newIdx >= entries.length) return;
    const copy = [...entries];
    [copy[idx], copy[newIdx]] = [copy[newIdx], copy[idx]];
    setEntries(copy);
  };

  const updateEntry = (idx: number, patch: Partial<DraftSong> | Partial<DraftSection>) => {
    const copy = [...entries];
    copy[idx] = { ...copy[idx], ...patch } as DraftEntry;
    setEntries(copy);
  };

  const filteredSongs = songs.filter((s) => {
    if (!searchText) return true;
    const q = searchText.toLowerCase();
    return s.title.toLowerCase().includes(q) || (s.artist && s.artist.toLowerCase().includes(q));
  });

  const inputStyle = { borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" };

  return (
    <div>
      <button onClick={onDone} className="text-sm mb-4 flex items-center gap-1" style={{ color: "var(--text-muted)" }}>
        ← Cancel editing
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

      {/* Song list, with section dividers */}
      <div className="space-y-2 mb-4">
        {entries.map((entry, idx) => entry.kind === "section" ? (
          <div key={`section-${idx}`} className="flex items-center gap-3 pt-3">
            <div className="flex flex-col gap-0.5">
              <button onClick={() => moveEntry(idx, -1)} className="text-xs px-1 hover:opacity-80" style={{ color: "var(--text-muted)" }}>▲</button>
              <button onClick={() => moveEntry(idx, 1)} className="text-xs px-1 hover:opacity-80" style={{ color: "var(--text-muted)" }}>▼</button>
            </div>
            <input value={entry.name} placeholder="Section name (e.g. Set 1)"
              onChange={(e) => updateEntry(idx, { name: e.target.value })}
              className="flex-1 bg-transparent border-b outline-none text-sm font-semibold uppercase tracking-wide pb-1"
              style={{ borderColor: "var(--accent)", color: "var(--accent)" }} />
            <button onClick={() => removeEntry(idx)} className="p-1 rounded hover:bg-white/10" style={{ color: "var(--red)" }}>
              <X size={16} />
            </button>
          </div>
        ) : (
          <div key={`${entry.song_id}-${idx}`} className="rounded-lg p-3 border group"
            style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
            <div className="flex items-center gap-3">
              <div className="flex flex-col gap-0.5">
                <button onClick={() => moveEntry(idx, -1)} className="text-xs px-1 hover:opacity-80" style={{ color: "var(--text-muted)" }}>▲</button>
                <button onClick={() => moveEntry(idx, 1)} className="text-xs px-1 hover:opacity-80" style={{ color: "var(--text-muted)" }}>▼</button>
              </div>
              <GripVertical size={16} style={{ color: "var(--text-muted)" }} />
              <span className="w-6 text-sm text-center" style={{ color: "var(--text-muted)" }}>{items.indexOf(entry) + 1}</span>
              <div className="flex-1 min-w-0">
                <span className="font-medium text-sm">{entry.song_title}</span>
                {entry.song_artist && <span className="text-sm ml-2" style={{ color: "var(--text-muted)" }}>— {entry.song_artist}</span>}
              </div>
              <input value={entry.notes} placeholder="Gig notes"
                onChange={(e) => updateEntry(idx, { notes: e.target.value })}
                className="w-48 px-2 py-0.5 text-sm rounded border bg-transparent outline-none" style={inputStyle} />
              <button onClick={() => setLinksOpen(linksOpen === idx ? null : idx)}
                title="Links for this gig (override the song's own links of the same kind)"
                className="flex items-center gap-1 text-xs px-2 py-0.5 rounded border"
                style={{ borderColor: "var(--border)", color: entry.links.length ? "var(--accent)" : "var(--text-muted)" }}>
                <Link2 size={12} /> {entry.links.length}
              </button>
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  value={entry.duration_minutes}
                  onChange={(e) => updateEntry(idx, { duration_minutes: Math.max(1, parseInt(e.target.value) || 1) })}
                  className="w-12 text-center text-sm rounded border bg-transparent outline-none"
                  style={inputStyle}
                  min={1}
                />
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>min</span>
              </div>
              <button onClick={() => removeEntry(idx)} className="p-1 rounded hover:bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ color: "var(--red)" }}>
                <X size={16} />
              </button>
            </div>
            {linksOpen === idx && (
              <div className="mt-3 pl-16">
                <p className="text-xs mb-1.5" style={{ color: "var(--text-muted)" }}>
                  Links for this gig only. A link here replaces the song's own links of the same kind.
                </p>
                <LinksEditor value={entry.links} onChange={(links) => updateEntry(idx, { links })} />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Add song */}
      {!addingSong ? (
        <div className="flex gap-2">
          <button onClick={() => setAddingSong(true)}
            className="flex-1 flex items-center justify-center gap-2 p-3 rounded-lg border border-dashed text-sm transition-colors hover:opacity-80"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
            <Plus size={16} /> Add Song
          </button>
          <button onClick={() => setEntries([...entries, { kind: "section", name: "" }])}
            className="flex items-center justify-center gap-2 px-4 p-3 rounded-lg border border-dashed text-sm transition-colors hover:opacity-80"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
            <Plus size={16} /> Add Section
          </button>
        </div>
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

interface ImportSummary { songs_matched: number; songs_created: number }

function SetlistView({ setlist, onEdit, onBack, imported }: {
  setlist: Setlist; onEdit: () => void; onBack: () => void; imported: ImportSummary | null;
}) {
  const navigate = useNavigate();
  const [uploadingCharts, setUploadingCharts] = useState(false);
  const play = (i: number, mode: "practice" | "perform") => navigate(`/setlists/${setlist.id}/play?i=${i}&mode=${mode}`);
  const groups = groupBySection(setlist.items);
  const withCharts = setlist.items.filter((i) => i.charts.length > 0).length;
  let n = 0;
  const th = "text-left text-xs font-medium uppercase tracking-wide px-3 py-2";
  return (
    <div>
      <button onClick={onBack} className="text-sm mb-4 flex items-center gap-1" style={{ color: "var(--text-muted)" }}>
        ← Back to setlists
      </button>

      {imported && (
        <div className="mb-4 rounded-lg border px-4 py-2 text-sm" style={{ borderColor: "var(--accent)", color: "var(--text)" }}>
          Imported {setlist.song_count} songs: {imported.songs_matched} matched existing songs, {imported.songs_created} new.
        </div>
      )}

      <div className="flex items-start justify-between gap-4 mb-2">
        <div>
          <h2 className="text-2xl font-bold">{setlist.name}</h2>
          {setlist.description && <p className="text-sm" style={{ color: "var(--text-muted)" }}>{setlist.description}</p>}
        </div>
        <div className="flex flex-wrap gap-2 justify-end">
          <button onClick={() => setUploadingCharts(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm border"
            style={{ borderColor: "var(--border)", color: "var(--text)" }}>
            <FileText size={14} /> Upload charts
          </button>
          <button onClick={onEdit}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm border"
            style={{ borderColor: "var(--border)", color: "var(--text)" }}>
            <Pencil size={14} /> Edit
          </button>
          <button onClick={() => play(0, "perform")} disabled={!setlist.items.length}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm border disabled:opacity-40"
            style={{ borderColor: "var(--accent)", color: "var(--accent)" }}>
            <MonitorPlay size={14} /> Perform
          </button>
          <button onClick={() => play(0, "practice")} disabled={!setlist.items.length}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-40"
            style={{ background: "var(--accent)" }}>
            <Play size={14} /> Practice
          </button>
        </div>
      </div>
      {uploadingCharts && <BulkChartUpload setlist={setlist} onClose={() => setUploadingCharts(false)} />}
      <div className="flex gap-6 mb-6 text-sm" style={{ color: "var(--text-muted)" }}>
        <span>{setlist.song_count} songs</span>
        <span className="flex items-center gap-1"><Clock size={14} /> {setlist.total_minutes} min</span>
        <span className="flex items-center gap-1"><FileText size={14} /> {withCharts}/{setlist.song_count} with charts</span>
      </div>

      {setlist.items.length === 0 && (
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>No songs yet. Use Edit to add some.</p>
      )}

      {groups.map((group, gi) => (
        <div key={gi} className="mb-6 rounded-xl border overflow-hidden" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          {group.section && (
            <div className="px-3 py-2 text-sm font-semibold uppercase tracking-wide border-b"
              style={{ color: "var(--accent)", borderColor: "var(--border)" }}>
              {group.section}
            </div>
          )}
          <table className="w-full text-sm">
            <thead style={{ color: "var(--text-muted)" }}>
              <tr>
                <th className={`${th} w-10`} />
                <th className={`${th} w-10`}>#</th>
                <th className={th}>Song</th>
                <th className={th}>Artist</th>
                <th className={th}>Notes</th>
                <th className={th}>Links</th>
                <th className={`${th} w-16`}>Chart</th>
              </tr>
            </thead>
            <tbody>
              {group.items.map((item) => {
                n += 1;
                const idx = n - 1;
                return (
                  <tr key={item.id} className="border-t group" style={{ borderColor: "var(--border)" }}>
                    <td className="pl-3 py-2">
                      <button onClick={() => play(idx, "practice")} title="Practice from here"
                        className="p-1 rounded opacity-40 group-hover:opacity-100" style={{ color: "var(--accent)" }}>
                        <Play size={14} />
                      </button>
                    </td>
                    <td className="px-3 py-2" style={{ color: "var(--text-muted)" }}>{n}</td>
                    <td className="px-3 py-2 font-medium">{item.song_title}</td>
                    <td className="px-3 py-2" style={{ color: "var(--text-muted)" }}>{item.song_artist}</td>
                    <td className="px-3 py-2" style={{ color: "var(--text-muted)" }}>{item.notes}</td>
                    <td className="px-3 py-2"><LinkChips links={item.effective_links} /></td>
                    <td className="px-3 py-2" style={{ color: item.charts.length ? "var(--accent)" : "var(--text-muted)" }}>
                      {item.charts.length ? <FileText size={14} /> : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

export default function SetlistBuilder() {
  const { id } = useParams();
  const selectedId = id ? Number(id) : null;
  const navigate = useNavigate();
  const location = useLocation();
  const imported = (location.state as { imported?: ImportSummary } | null)?.imported ?? null;
  const [editing, setEditing] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const queryClient = useQueryClient();

  const { data: setlists = [], isLoading } = useQuery({
    queryKey: ["setlists"],
    queryFn: api.setlists.list,
  });

  const { data: songs = [] } = useQuery({
    queryKey: ["repertoire"],
    queryFn: () => api.songs.list(),
  });

  const createMut = useMutation({
    mutationFn: () => api.setlists.create({ name: newName || "New Setlist" }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["setlists"] });
      navigate(`/setlists/${data.id}`);
      setEditing(true);
      setCreating(false);
      setNewName("");
    },
  });

  const importMut = useMutation({
    mutationFn: (file: File) => api.setlists.import(file),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["setlists"] });
      queryClient.invalidateQueries({ queryKey: ["repertoire"] });
      queryClient.invalidateQueries({ queryKey: ["songs"] });
      navigate(`/setlists/${res.setlist.id}`, {
        state: { imported: { songs_matched: res.songs_matched, songs_created: res.songs_created } },
      });
    },
  });

  const selectedSetlist = setlists.find((s) => s.id === selectedId);

  if (isLoading) return <div style={{ color: "var(--text-muted)" }}>Loading...</div>;

  if (selectedId != null && !selectedSetlist) {
    return <div style={{ color: "var(--text-muted)" }}>Setlist not found.</div>;
  }

  if (selectedSetlist) {
    return editing
      ? <SetlistEditor key={selectedSetlist.id} setlist={selectedSetlist} songs={songs} onDone={() => setEditing(false)} />
      : <SetlistView setlist={selectedSetlist} imported={imported}
          onEdit={() => setEditing(true)} onBack={() => navigate("/setlists")} />;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Setlists</h2>
        <div className="flex gap-2">
          <input ref={fileInput} type="file" accept=".xlsx" className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) importMut.mutate(file);
              e.target.value = "";
            }} />
          <button
            onClick={() => fileInput.current?.click()}
            disabled={importMut.isPending}
            title="Import a set-list spreadsheet (# / Song / Artist / Notes + link columns)"
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm border"
            style={{ borderColor: "var(--border)", color: "var(--text)" }}
          >
            <Upload size={16} /> {importMut.isPending ? "Importing..." : "Import .xlsx"}
          </button>
          <button
            onClick={() => setCreating(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white"
            style={{ background: "var(--accent)" }}
          >
            <Plus size={16} /> New Setlist
          </button>
        </div>
      </div>

      {importMut.isError && (
        <div className="mb-4 rounded-lg border px-4 py-2 text-sm" style={{ borderColor: "var(--red)", color: "var(--red)" }}>
          Import failed: {(importMut.error as Error).message}
        </div>
      )}

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
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {setlists.map((s) => (
          <SetlistCard key={s.id} setlist={s} onSelect={() => { setEditing(false); navigate(`/setlists/${s.id}`); }} />
        ))}
      </div>
    </div>
  );
}
