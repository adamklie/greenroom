import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { Search, Star, FileAudio, FileVideo, Columns3, Trash2, Plus, X } from "lucide-react";

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
  { key: "file", label: "Accession", defaultVisible: true, sortable: true, width: "w-32" },
  { key: "submitted_file_name", label: "Submitted Name", defaultVisible: false, sortable: true, width: "w-40" },
  { key: "song", label: "Song", defaultVisible: true, sortable: true, width: "w-48" },
  { key: "song_type", label: "Type", defaultVisible: false, sortable: true, width: "w-20" },
  { key: "source", label: "Source", defaultVisible: true, sortable: true, width: "w-24" },
  { key: "role", label: "Role", defaultVisible: true, sortable: true, width: "w-24" },
  { key: "rating_overall", label: "Overall", defaultVisible: true, sortable: true, width: "w-24" },
  { key: "rating_vocals", label: "Vocals", defaultVisible: false, sortable: true, width: "w-24" },
  { key: "rating_guitar", label: "Guitar", defaultVisible: false, sortable: true, width: "w-24" },
  { key: "rating_drums", label: "Drums", defaultVisible: false, sortable: true, width: "w-24" },
  { key: "rating_keys", label: "Keys", defaultVisible: false, sortable: true, width: "w-24" },
  { key: "rating_bass", label: "Bass", defaultVisible: false, sortable: true, width: "w-24" },
  { key: "rating_tone", label: "Tone", defaultVisible: false, sortable: true, width: "w-24" },
  { key: "rating_timing", label: "Timing", defaultVisible: false, sortable: true, width: "w-24" },
  { key: "rating_energy", label: "Energy", defaultVisible: false, sortable: true, width: "w-24" },
  { key: "rating_mix", label: "Mix", defaultVisible: false, sortable: true, width: "w-24" },
  { key: "rating_other", label: "Other", defaultVisible: false, sortable: true, width: "w-24" },
  { key: "notes", label: "Notes", defaultVisible: true, sortable: false, width: "w-32" },
  { key: "version", label: "Version", defaultVisible: false, sortable: true, width: "w-20" },
  { key: "session_date", label: "Session", defaultVisible: false, sortable: true, width: "w-24" },
  { key: "clip_name", label: "Clip", defaultVisible: false, sortable: true, width: "w-24" },
  { key: "file_type", label: "Format", defaultVisible: false, sortable: true, width: "w-16" },
  { key: "recorded_at", label: "Recorded", defaultVisible: true, sortable: true, width: "w-28" },
  { key: "uploaded_at", label: "Uploaded", defaultVisible: false, sortable: true, width: "w-28" },
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

function StarRating({ value, onChange }: { value: number | null; onChange: (v: number | null) => void }) {
  const handleClick = (starIndex: number, isLeftHalf: boolean) => {
    const newVal = isLeftHalf ? starIndex - 0.5 : starIndex;
    if (value === newVal) onChange(null);
    else onChange(newVal);
  };
  return (
    <div className="flex">
      {[1,2,3,4,5].map(n => {
        const full = value !== null && value >= n;
        const half = value !== null && value >= n - 0.5 && value < n;
        return (
          <div key={n} className="relative" style={{ width: 13, height: 12 }}>
            <button className="absolute inset-y-0 left-0 w-1/2 z-10 p-0" style={{ background: "transparent" }}
              onClick={() => handleClick(n, true)} />
            <button className="absolute inset-y-0 right-0 w-1/2 z-10 p-0" style={{ background: "transparent" }}
              onClick={() => handleClick(n, false)} />
            <svg width={12} height={12} viewBox="0 0 24 24" className="absolute inset-0 pointer-events-none">
              <defs>
                <clipPath id={`lib-half-${n}`}>
                  <rect x="0" y="0" width="12" height="24" />
                </clipPath>
              </defs>
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
                fill="none" stroke={full || half ? "var(--yellow)" : "var(--text-muted)"} strokeWidth="1.5" />
              {full && <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" fill="var(--yellow)" />}
              {half && <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" fill="var(--yellow)" clipPath={`url(#lib-half-${n})`} />}
            </svg>
          </div>
        );
      })}
    </div>
  );
}

function InlineSongPicker({ audioFileId, currentSongId, songs, onSave, onSongCreated }: {
  audioFileId: number;
  currentSongId: number | null;
  songs: { id: number; title: string; artist: string | null; type: string }[];
  onSave: (songId: number | null) => void;
  onSongCreated: () => void;
}) {
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [artist, setArtist] = useState("");
  const [type, setType] = useState("cover");

  const queryClient = useQueryClient();
  const createMut = useMutation({
    mutationFn: () => api.songs.create({ title, artist: artist || null, type, status: type === "idea" ? "captured" : "idea" }),
    onSuccess: (newSong) => {
      onSave(newSong.id);
      setCreating(false);
      setTitle("");
      setArtist("");
      queryClient.invalidateQueries({ queryKey: ["songs-all"] });
      onSongCreated();
    },
  });

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
    <div className="flex items-center gap-1">
      <select value={currentSongId || ""} onChange={(e) => onSave(e.target.value ? Number(e.target.value) : null)}
        className="flex-1 px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}>
        <option value="">—</option>
        {songs.map(s => (
          <option key={s.id} value={s.id}>
            {s.title}{s.artist ? ` — ${s.artist}` : ""}{s.type ? ` (${s.type})` : ""}
          </option>
        ))}
      </select>
      <button onClick={() => setCreating(true)} className="p-0.5 rounded hover:bg-white/10 flex-shrink-0"
        title="Create new song" style={{ color: "var(--accent)" }}>
        <Plus size={12} />
      </button>
    </div>
  );
}

const RATING_COLUMN_KEYS = [
  "rating_overall", "rating_vocals", "rating_guitar", "rating_drums",
  "rating_keys", "rating_bass", "rating_tone", "rating_timing",
  "rating_energy", "rating_mix", "rating_other",
];

type SortDir = "asc" | "desc";

export default function Library() {
  const [searchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  useEffect(() => {
    const s = searchParams.get("search");
    if (s !== null) setSearch(s);
  }, [searchParams]);
  const [filterHasSong, setFilterHasSong] = useState<string>("");
  const [filterSource, setFilterSource] = useState("");
  const [filterRole, setFilterRole] = useState("");
  const [showDeleted, setShowDeleted] = useState(false);
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
  if (showDeleted) params.include_deleted = "true";

  const { data: files = [], isLoading } = useQuery({
    queryKey: ["audio-files", params],
    queryFn: () => api.audioFiles.list(params),
  });

  const { data: songs = [] } = useQuery({
    queryKey: ["songs-all"],
    queryFn: () => api.songs.list(),
  });

  const { data: sessions = [] } = useQuery({
    queryKey: ["sessions-all"],
    queryFn: () => api.sessions.list(),
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
    mutationFn: (id: number) => api.audioFiles.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["audio-files"] }),
  });

  const extractAudioMut = useMutation({
    mutationFn: (id: number) => api.audioFiles.extractAudio(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["audio-files"] }),
  });

  const updateSongMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      api.songs.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audio-files"] });
      queryClient.invalidateQueries({ queryKey: ["songs"] });
    },
  });

  const save = (id: number, field: string, value: unknown) => {
    updateMut.mutate({ id, data: { [field]: value === "" ? null : value } });
  };

  const saveSong = (songId: number, field: string, value: unknown) => {
    updateSongMut.mutate({ id: songId, data: { [field]: value === "" ? null : value } });
  };

  const displayName = (af: { identifier: string | null; file_path: string }) =>
    af.identifier || af.file_path.split("/").pop() || af.file_path;

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
    if (sortKey === "file") cmp = displayName(a).localeCompare(displayName(b));
    else if (sortKey === "song") cmp = (a.song_title || "").localeCompare(b.song_title || "");
    else if (RATING_COLUMN_KEYS.includes(sortKey)) cmp = (av[sortKey] || 0) - (bv[sortKey] || 0);
    else if (sortKey === "created_at" || sortKey === "uploaded_at") cmp = (av[sortKey] || "").localeCompare(bv[sortKey] || "");
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
        <label className="flex items-center gap-1 text-sm" style={{ color: "var(--text-muted)" }}>
          <input type="checkbox" checked={showDeleted} onChange={(e) => setShowDeleted(e.target.checked)} />
          Show deleted
        </label>
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
              {sorted.map((af) => {
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                const afAny = af as Record<string, any>;
                return (
                <tr key={af.id} className="border-t"
                  style={{ borderColor: "var(--border)" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>

                  {/* Render cells in ALL_COLUMNS order to match headers */}
                  {cols.map(col => {
                    const k = col.key;

                    // Accession (file) — read-only display name + audio player
                    if (k === "file") return (
                      <td key={k} className="px-3 py-2">
                        <div className="flex items-center gap-2">
                          <button onClick={() => setExpandedId(expandedId === af.id ? null : af.id)}>
                            {af.file_type && ["mp4", "mov"].includes(af.file_type) ? (
                              <FileVideo size={14} style={{ color: af.song_id ? "var(--accent)" : "var(--text-muted)" }} />
                            ) : (
                              <FileAudio size={14} style={{ color: af.song_id ? "var(--accent)" : "var(--text-muted)" }} />
                            )}
                          </button>
                          <div>
                            <div className="font-medium flex items-center gap-1">
                              {af.identifier || af.file_path.split("/").pop() || af.file_path}
                              {af.file_exists === false && (
                                <span title="File missing on disk" style={{ color: "var(--danger, #ef4444)" }}>⚠</span>
                              )}
                            </div>
                            <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                              {af.file_path.split("/").pop() || af.file_path}
                            </div>
                            {expandedId === af.id && af.file_type && (
                              af.file_type && ["mp4", "mov"].includes(af.file_type) ? (
                                <div>
                                  <video controls className="mt-1 rounded" style={{ width: 800, maxHeight: 540 }}>
                                    <source src={api.media.audioFileUrl(af.id)} />
                                  </video>
                                  <button
                                    onClick={() => extractAudioMut.mutate(af.id)}
                                    disabled={extractAudioMut.isPending}
                                    className="mt-1 px-2 py-1 rounded border text-xs"
                                    style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
                                    title="Create an audio-only sibling (m4a)"
                                  >
                                    {extractAudioMut.isPending ? "Extracting…" : "Extract audio"}
                                  </button>
                                </div>
                              ) : (
                                <audio controls className="h-8 mt-1" style={{ filter: "invert(1) hue-rotate(180deg)", width: 520 }}>
                                  <source src={api.media.audioFileUrl(af.id)} />
                                </audio>
                              )
                            )}
                          </div>
                        </div>
                      </td>
                    );

                    // Submitted file name — read-only
                    if (k === "submitted_file_name") return (
                      <td key={k} className="px-3 py-2" style={{ color: "var(--text-muted)" }}>
                        {af.submitted_file_name || "—"}
                      </td>
                    );

                    // Song — editable dropdown with inline create
                    if (k === "song") return (
                      <td key={k} className="px-3 py-2">
                        <InlineSongPicker
                          audioFileId={af.id}
                          currentSongId={af.song_id}
                          songs={songs}
                          onSave={(songId) => save(af.id, "song_id", songId)}
                          onSongCreated={() => queryClient.invalidateQueries({ queryKey: ["audio-files"] })}
                        />
                      </td>
                    );

                    // Song type — editable dropdown (updates the linked Song)
                    if (k === "song_type") return (
                      <td key={k} className="px-3 py-2">
                        {af.song_id ? (
                          <InlineSelect value={af.song_type || ""} options={["", "cover", "original", "idea"]}
                            onChange={(v) => saveSong(af.song_id!, "type", v)} />
                        ) : (
                          <span style={{ color: "var(--text-muted)" }}>—</span>
                        )}
                      </td>
                    );

                    // Source — editable dropdown
                    if (k === "source") return (
                      <td key={k} className="px-3 py-2">
                        <InlineSelect value={af.source || ""} options={SOURCE_OPTIONS}
                          onChange={(v) => save(af.id, "source", v)} />
                      </td>
                    );

                    // Role — editable dropdown
                    if (k === "role") return (
                      <td key={k} className="px-3 py-2">
                        <InlineSelect value={af.role || ""} options={ROLE_OPTIONS}
                          onChange={(v) => save(af.id, "role", v)} />
                      </td>
                    );

                    // Ratings — editable star pickers
                    if (RATING_COLUMN_KEYS.includes(k)) return (
                      <td key={k} className="px-3 py-2 text-center">
                        <StarRating value={afAny[k] as number | null}
                          onChange={(v) => save(af.id, k, v)} />
                      </td>
                    );

                    // Notes — editable text
                    if (k === "notes") return (
                      <td key={k} className="px-3 py-2">
                        <input defaultValue={af.notes || ""} placeholder="—"
                          onBlur={(e) => save(af.id, "notes", e.target.value)}
                          className="w-full px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}
                          key={`notes-${af.id}-${af.notes}`} />
                      </td>
                    );

                    // Version — editable text
                    if (k === "version") return (
                      <td key={k} className="px-3 py-2">
                        <input defaultValue={af.version || ""} placeholder="—"
                          onBlur={(e) => save(af.id, "version", e.target.value)}
                          className="w-full px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}
                          key={`ver-${af.id}-${af.version}`} />
                      </td>
                    );

                    // Clip name — editable text
                    if (k === "clip_name") return (
                      <td key={k} className="px-3 py-2">
                        <input defaultValue={af.clip_name || ""} placeholder="—"
                          onBlur={(e) => save(af.id, "clip_name", e.target.value)}
                          className="w-full px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}
                          key={`clip-${af.id}-${af.clip_name}`} />
                      </td>
                    );

                    // Session — editable dropdown
                    if (k === "session_date") return (
                      <td key={k} className="px-3 py-2">
                        <select value={af.session_id || ""} onChange={(e) => save(af.id, "session_id", e.target.value ? Number(e.target.value) : null)}
                          className="w-full px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}>
                          <option value="">—</option>
                          {sessions.map(s => (
                            <option key={s.id} value={s.id}>{s.date}</option>
                          ))}
                        </select>
                      </td>
                    );

                    // Format — read-only
                    if (k === "file_type") return (
                      <td key={k} className="px-3 py-2" style={{ color: "var(--text-muted)" }}>
                        {af.file_type || "—"}
                      </td>
                    );

                    // Recorded at — editable date
                    if (k === "recorded_at") return (
                      <td key={k} className="px-3 py-2">
                        <input type="date" defaultValue={af.recorded_at?.split("T")[0] || ""}
                          onBlur={(e) => save(af.id, "recorded_at", e.target.value || null)}
                          className="px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}
                          key={`rec-${af.id}-${af.recorded_at}`} />
                      </td>
                    );

                    // Uploaded at — editable date
                    if (k === "uploaded_at") return (
                      <td key={k} className="px-3 py-2">
                        <input type="date" defaultValue={af.uploaded_at?.split("T")[0] || ""}
                          onBlur={(e) => save(af.id, "uploaded_at", e.target.value || null)}
                          className="px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}
                          key={`upl-${af.id}-${af.uploaded_at}`} />
                      </td>
                    );

                    // Created at — read-only
                    if (k === "created_at") return (
                      <td key={k} className="px-3 py-2" style={{ color: "var(--text-muted)" }}>
                        {af.created_at ? new Date(af.created_at).toLocaleDateString() : "—"}
                      </td>
                    );

                    return null;
                  })}

                  <td className="px-1 py-2">
                    <button onClick={() => { if (confirm("Delete this file?")) deleteMut.mutate(af.id); }}
                      className="p-1 rounded hover:bg-white/10"
                      style={{ color: "var(--text-muted)" }}>
                      <Trash2 size={12} />
                    </button>
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
