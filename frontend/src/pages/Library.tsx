import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { Search, Star, FileAudio, Columns3, Trash2 } from "lucide-react";

const SOURCE_OPTIONS = ["", "phone", "logic_pro", "garageband", "suno_ai", "collaborator", "download", "gopro", "unknown"];
const ROLE_OPTIONS = ["", "recording", "demo", "reference", "backing_track", "final_mix", "stem"];

const inputStyle = { borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" };

interface Column {
  key: string;
  label: string;
  defaultVisible: boolean;
  sortable: boolean;
  width?: string;
}

const ALL_COLUMNS: Column[] = [
  { key: "file", label: "File", defaultVisible: true, sortable: true },
  { key: "song", label: "Song", defaultVisible: true, sortable: true, width: "w-48" },
  { key: "song_type", label: "Type", defaultVisible: false, sortable: true, width: "w-20" },
  { key: "source", label: "Source", defaultVisible: true, sortable: true, width: "w-24" },
  { key: "role", label: "Role", defaultVisible: true, sortable: true, width: "w-24" },
  { key: "rating", label: "Rating", defaultVisible: true, sortable: true, width: "w-24" },
  { key: "notes", label: "Notes", defaultVisible: true, sortable: false, width: "w-32" },
  { key: "version", label: "Version", defaultVisible: false, sortable: true, width: "w-20" },
  { key: "session_date", label: "Session", defaultVisible: false, sortable: true, width: "w-24" },
  { key: "clip_name", label: "Clip", defaultVisible: false, sortable: true, width: "w-24" },
  { key: "file_type", label: "Format", defaultVisible: false, sortable: true, width: "w-16" },
  { key: "created_at", label: "Added", defaultVisible: false, sortable: true, width: "w-24" },
];

function InlineSelect({ value, options, onChange }: { value: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <select value={value || ""} onChange={(e) => onChange(e.target.value)}
      className="px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}>
      {options.map(o => <option key={o} value={o}>{o || "—"}</option>)}
    </select>
  );
}

function StarRating({ value, onChange }: { value: number | null; onChange: (v: number) => void }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map(n => (
        <button key={n} onClick={() => onChange(n)} className="p-0">
          <Star size={12} fill={value && n <= value ? "var(--yellow)" : "none"}
            style={{ color: value && n <= value ? "var(--yellow)" : "var(--text-muted)" }} />
        </button>
      ))}
    </div>
  );
}

type SortDir = "asc" | "desc";

export default function Library() {
  const [search, setSearch] = useState("");
  const [filterHasSong, setFilterHasSong] = useState<string>("");
  const [filterSource, setFilterSource] = useState("");
  const [filterRole, setFilterRole] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [showColumnPicker, setShowColumnPicker] = useState(false);
  const [visibleCols, setVisibleCols] = useState<Set<string>>(
    new Set(ALL_COLUMNS.filter(c => c.defaultVisible).map(c => c.key))
  );
  const [sortKey, setSortKey] = useState<string>("file");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const queryClient = useQueryClient();

  const params: Record<string, string> = {};
  if (search) params.search = search;
  if (filterHasSong === "yes") params.has_song = "true";
  if (filterHasSong === "no") params.has_song = "false";
  if (filterSource) params.source = filterSource;
  if (filterRole) params.role = filterRole;

  const { data: files = [], isLoading } = useQuery({
    queryKey: ["audio-files", params],
    queryFn: () => api.audioFiles.list(params),
  });

  const { data: songs = [] } = useQuery({
    queryKey: ["songs-all"],
    queryFn: () => api.songs.list(),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      api.audioFiles.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audio-files"] });
      queryClient.invalidateQueries({ queryKey: ["songs"] });
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.audioFiles.update(id, { role: "deleted" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["audio-files"] }),
  });

  const save = (id: number, field: string, value: unknown) => {
    updateMut.mutate({ id, data: { [field]: value === "" ? null : value } });
  };

  const filename = (path: string) => path.split("/").pop() || path;

  const toggleCol = (key: string) => {
    const next = new Set(visibleCols);
    if (next.has(key)) next.delete(key); else next.add(key);
    setVisibleCols(next);
  };

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("asc"); }
  };

  // Sort files
  const sorted = [...files].sort((a, b) => {
    let cmp = 0;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const av = a as any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const bv = b as any;
    if (sortKey === "file") cmp = filename(a.file_path).localeCompare(filename(b.file_path));
    else if (sortKey === "song") cmp = (a.song_title || "").localeCompare(b.song_title || "");
    else if (sortKey === "rating") cmp = (a.rating_overall || 0) - (b.rating_overall || 0);
    else if (sortKey === "created_at") cmp = (a.created_at || "").localeCompare(b.created_at || "");
    else {
      const aVal = String(av[sortKey] || "");
      const bVal = String(bv[sortKey] || "");
      cmp = aVal.localeCompare(bVal);
    }
    return sortDir === "asc" ? cmp : -cmp;
  });

  const cols = ALL_COLUMNS.filter(c => visibleCols.has(c.key));

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-2xl font-bold">Library</h2>
        <span className="text-sm" style={{ color: "var(--text-muted)" }}>{files.length} files</span>
      </div>

      {/* Filters + column picker */}
      <div className="flex gap-3 mb-4 flex-wrap items-center">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
          <input type="text" placeholder="Search files..." value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-2 rounded-lg border text-sm bg-transparent outline-none"
            style={{ borderColor: "var(--border)", color: "var(--text)" }} />
        </div>
        <select value={filterHasSong} onChange={(e) => setFilterHasSong(e.target.value)}
          className="px-3 py-2 rounded-lg border text-sm outline-none"
          style={{ ...inputStyle, background: "var(--bg-card)" }}>
          <option value="">All files</option>
          <option value="yes">Linked to a song</option>
          <option value="no">Unassigned</option>
        </select>
        <select value={filterSource} onChange={(e) => setFilterSource(e.target.value)}
          className="px-3 py-2 rounded-lg border text-sm outline-none"
          style={{ ...inputStyle, background: "var(--bg-card)" }}>
          <option value="">All sources</option>
          {SOURCE_OPTIONS.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={filterRole} onChange={(e) => setFilterRole(e.target.value)}
          className="px-3 py-2 rounded-lg border text-sm outline-none"
          style={{ ...inputStyle, background: "var(--bg-card)" }}>
          <option value="">All roles</option>
          {ROLE_OPTIONS.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <div className="relative ml-auto">
          <button onClick={() => setShowColumnPicker(!showColumnPicker)}
            className="flex items-center gap-1 px-3 py-2 rounded-lg border text-sm"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
            <Columns3 size={14} /> Columns
          </button>
          {showColumnPicker && (
            <div className="absolute right-0 top-full mt-1 rounded-lg border p-3 z-50 w-48 shadow-xl"
              style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
              {ALL_COLUMNS.map(col => (
                <label key={col.key} className="flex items-center gap-2 py-1 text-xs cursor-pointer">
                  <input type="checkbox" checked={visibleCols.has(col.key)}
                    onChange={() => toggleCol(col.key)} />
                  {col.label}
                </label>
              ))}
            </div>
          )}
        </div>
      </div>

      {isLoading ? <div style={{ color: "var(--text-muted)" }}>Loading...</div> : (
        <div className="rounded-xl border overflow-x-auto" style={{ borderColor: "var(--border)" }}>
          <table className="w-full text-xs">
            <thead>
              <tr style={{ background: "var(--bg-card)" }}>
                {cols.map(col => (
                  <th key={col.key}
                    className={`text-left px-3 py-2.5 font-medium ${col.width || ""} ${col.sortable ? "cursor-pointer select-none" : ""}`}
                    style={{ color: sortKey === col.key ? "var(--accent)" : "var(--text-muted)" }}
                    onClick={() => col.sortable && toggleSort(col.key)}>
                    {col.label}
                    {sortKey === col.key && <span className="ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>}
                  </th>
                ))}
                <th className="w-8" />
              </tr>
            </thead>
            <tbody>
              {sorted.map((af) => (
                <tr key={af.id} className="border-t"
                  style={{ borderColor: "var(--border)" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>

                  {visibleCols.has("file") && (
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <button onClick={() => setExpandedId(expandedId === af.id ? null : af.id)}>
                          <FileAudio size={14} style={{ color: af.song_id ? "var(--accent)" : "var(--text-muted)" }} />
                        </button>
                        <div>
                          <div className="font-medium">{filename(af.file_path)}</div>
                          {expandedId === af.id && af.file_type && ["m4a", "mp3", "wav"].includes(af.file_type) && (
                            <audio controls className="h-7 mt-1" style={{ filter: "invert(1) hue-rotate(180deg)", width: 200 }}>
                              <source src={api.media.audioFileUrl(af.id)} />
                            </audio>
                          )}
                        </div>
                      </div>
                    </td>
                  )}

                  {visibleCols.has("song") && (
                    <td className="px-3 py-2">
                      <select value={af.song_id || ""} onChange={(e) => save(af.id, "song_id", e.target.value ? Number(e.target.value) : null)}
                        className="w-full px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}>
                        <option value="">—</option>
                        {songs.map(s => (
                          <option key={s.id} value={s.id}>
                            {s.title}{s.artist ? ` — ${s.artist}` : ""}{s.type ? ` (${s.type})` : ""}
                          </option>
                        ))}
                      </select>
                    </td>
                  )}

                  {visibleCols.has("song_type") && (
                    <td className="px-3 py-2" style={{ color: "var(--text-muted)" }}>
                      {af.song_type || "—"}
                    </td>
                  )}

                  {visibleCols.has("source") && (
                    <td className="px-3 py-2">
                      <InlineSelect value={af.source || ""} options={SOURCE_OPTIONS}
                        onChange={(v) => save(af.id, "source", v)} />
                    </td>
                  )}

                  {visibleCols.has("role") && (
                    <td className="px-3 py-2">
                      <InlineSelect value={af.role || ""} options={ROLE_OPTIONS}
                        onChange={(v) => save(af.id, "role", v)} />
                    </td>
                  )}

                  {visibleCols.has("rating") && (
                    <td className="px-3 py-2 text-center">
                      <StarRating value={af.rating_overall} onChange={(v) => save(af.id, "rating_overall", v)} />
                    </td>
                  )}

                  {visibleCols.has("notes") && (
                    <td className="px-3 py-2">
                      <input defaultValue={af.notes || ""} placeholder="—"
                        onBlur={(e) => save(af.id, "notes", e.target.value)}
                        className="w-full px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}
                        key={`notes-${af.id}-${af.notes}`} />
                    </td>
                  )}

                  {visibleCols.has("version") && (
                    <td className="px-3 py-2">
                      <input defaultValue={af.version || ""} placeholder="—"
                        onBlur={(e) => save(af.id, "version", e.target.value)}
                        className="w-full px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}
                        key={`ver-${af.id}-${af.version}`} />
                    </td>
                  )}

                  {visibleCols.has("session_date") && (
                    <td className="px-3 py-2" style={{ color: "var(--text-muted)" }}>
                      {af.session_date || "—"}
                    </td>
                  )}

                  {visibleCols.has("clip_name") && (
                    <td className="px-3 py-2" style={{ color: "var(--text-muted)" }}>
                      {af.clip_name || "—"}
                    </td>
                  )}

                  {visibleCols.has("file_type") && (
                    <td className="px-3 py-2" style={{ color: "var(--text-muted)" }}>
                      {af.file_type || "—"}
                    </td>
                  )}

                  {visibleCols.has("created_at") && (
                    <td className="px-3 py-2" style={{ color: "var(--text-muted)" }}>
                      {af.created_at ? new Date(af.created_at).toLocaleDateString() : "—"}
                    </td>
                  )}

                  <td className="px-1 py-2">
                    <button onClick={() => deleteMut.mutate(af.id)}
                      className="p-1 rounded hover:bg-white/10 opacity-0 group-hover:opacity-100"
                      style={{ color: "var(--red)" }}>
                      <Trash2 size={12} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
