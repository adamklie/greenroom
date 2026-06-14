import { useState, useEffect, useMemo, useCallback, useRef, memo } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type AudioFile } from "../api/client";
import { Search, FileAudio, FileVideo, Columns3, Trash2, RotateCcw, Download, FolderInput } from "lucide-react";
import { InlineSongPicker, type SongOption } from "../components/InlineSongPicker";
import MoveToProjectMenu from "../components/MoveToProjectMenu";
import MoveRecordingModal from "../components/MoveRecordingModal";
import { useProject } from "../project";

const SOURCE_OPTIONS = ["", "phone", "logic_pro", "garageband", "suno_ai", "collaborator", "download", "gopro", "unknown"];
const ROLE_OPTIONS = ["", "recording", "demo", "reference", "backing_track", "final_mix", "stem"];

const inputStyle = { borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" };

type SessionOption = { id: number; date: string };

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

const RATING_COLUMN_KEYS = [
  "rating_overall", "rating_vocals", "rating_guitar", "rating_drums",
  "rating_keys", "rating_bass", "rating_tone", "rating_timing",
  "rating_energy", "rating_mix", "rating_other",
];

type SortDir = "asc" | "desc";

const displayName = (af: { identifier: string | null; file_path: string }) =>
  af.identifier || af.file_path.split("/").pop() || af.file_path;

// Does an audio file still belong in a list fetched with these query params?
// Mirrors the backend filter so optimistic updates can drop rows that no
// longer match (e.g. a file that just got a song while viewing "Unassigned").
function rowMatchesParams(af: AudioFile, params: Record<string, string>): boolean {
  if (af.role === "deleted" && params.include_deleted !== "true" && params.role !== "deleted") return false;
  if (params.has_song === "true" && af.song_id == null) return false;
  if (params.has_song === "false" && af.song_id != null) return false;
  if (params.source && af.source !== params.source) return false;
  if (params.role && af.role !== params.role) return false;
  return true;
}

interface RowProps {
  af: AudioFile;
  cols: Column[];
  songs: SongOption[];
  sessions: SessionOption[];
  isExpanded: boolean;
  isSelected: boolean;
  isEditingSong: boolean;
  isExtracting: boolean;
  onToggleExpand: (id: number) => void;
  onToggleSelect: (id: number, shiftKey: boolean) => void;
  onStartEditSong: (id: number) => void;
  onStopEditSong: () => void;
  onSave: (id: number, field: string, value: unknown) => void;
  onSaveSong: (songId: number, field: string, value: unknown) => void;
  onExtract: (id: number) => void;
  onDelete: (id: number) => void;
  onRestore: (id: number) => void;
  onSongCreated: () => void;
  onMove?: (af: AudioFile) => void;
}

const LibraryRow = memo(function LibraryRow({
  af, cols, songs, sessions, isExpanded, isSelected, isEditingSong, isExtracting,
  onToggleExpand, onToggleSelect, onStartEditSong, onStopEditSong,
  onSave, onSaveSong, onExtract, onDelete, onRestore, onSongCreated, onMove,
}: RowProps) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const afAny = af as Record<string, any>;
  const isDeleted = af.role === "deleted";

  return (
    <tr className="border-t cursor-pointer"
      style={{ borderColor: "var(--border)", opacity: isDeleted ? 0.55 : 1, background: isSelected ? "var(--bg-hover)" : "transparent" }}
      onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = "var(--bg-hover)"; }}
      onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = "transparent"; }}
      onClick={(e) => {
        // Clicking empty/read-only areas of the row toggles selection; clicks
        // on actual editable controls keep doing their own thing.
        if ((e.target as HTMLElement).closest("input, select, button, a, textarea, label")) return;
        onToggleSelect(af.id, e.shiftKey);
      }}>

      <td className="px-2 py-2 w-8">
        <input type="checkbox" checked={isSelected} onChange={() => {}}
          onClick={(e) => onToggleSelect(af.id, e.shiftKey)} title="Shift-click to select a range" />
      </td>

      {cols.map(col => {
        const k = col.key;

        if (k === "file") return (
          <td key={k} className="px-3 py-2">
            <div className="flex items-center gap-2">
              <button onClick={() => onToggleExpand(af.id)}>
                {af.file_type && ["mp4", "mov"].includes(af.file_type) ? (
                  <FileVideo size={14} style={{ color: af.song_id ? "var(--accent)" : "var(--text-muted)" }} />
                ) : (
                  <FileAudio size={14} style={{ color: af.song_id ? "var(--accent)" : "var(--text-muted)" }} />
                )}
              </button>
              <div>
                <div className="font-medium flex items-center gap-1">
                  {displayName(af)}
                  {isDeleted && (
                    <span className="px-1 rounded text-[10px] uppercase tracking-wide"
                      style={{ background: "var(--danger, #ef4444)", color: "#fff" }}>deleted</span>
                  )}
                  {af.file_exists === false && (
                    <span title="File missing on disk" style={{ color: "var(--danger, #ef4444)" }}>⚠</span>
                  )}
                </div>
                <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {af.file_path.split("/").pop() || af.file_path}
                </div>
                {isExpanded && af.file_type && (
                  af.file_type && ["mp4", "mov"].includes(af.file_type) ? (
                    <div>
                      <video controls className="mt-1 rounded" style={{ width: 800, maxHeight: 540 }}>
                        <source src={api.media.audioFileUrl(af.id)} />
                      </video>
                      <button
                        onClick={() => onExtract(af.id)}
                        disabled={isExtracting}
                        className="mt-1 px-2 py-1 rounded border text-xs"
                        style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
                        title="Create an audio-only sibling (m4a)"
                      >
                        {isExtracting ? "Extracting…" : "Extract audio"}
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

        if (k === "submitted_file_name") return (
          <td key={k} className="px-3 py-2" style={{ color: "var(--text-muted)" }}>
            {af.submitted_file_name || "—"}
          </td>
        );

        // Song — lightweight text by default; heavy picker only mounts when editing this row.
        if (k === "song") return (
          <td key={k} className="px-3 py-2">
            {isEditingSong ? (
              <InlineSongPicker
                songs={songs}
                onSave={(songId) => { onSave(af.id, "song_id", songId); onStopEditSong(); }}
                onSongCreated={onSongCreated}
                onCancel={onStopEditSong}
              />
            ) : (
              <button onClick={() => onStartEditSong(af.id)}
                className="text-left w-full px-1 py-0.5 rounded hover:bg-white/10 truncate"
                style={{ color: af.song_title ? "var(--text)" : "var(--text-muted)" }}>
                {af.song_title ? `${af.song_title}${af.song_artist ? ` — ${af.song_artist}` : ""}` : "— link song"}
              </button>
            )}
          </td>
        );

        if (k === "song_type") return (
          <td key={k} className="px-3 py-2">
            {af.song_id ? (
              <InlineSelect value={af.song_type || ""} options={["", "cover", "original", "idea"]}
                onChange={(v) => onSaveSong(af.song_id!, "type", v)} />
            ) : (
              <span style={{ color: "var(--text-muted)" }}>—</span>
            )}
          </td>
        );

        if (k === "source") return (
          <td key={k} className="px-3 py-2">
            <InlineSelect value={af.source || ""} options={SOURCE_OPTIONS}
              onChange={(v) => onSave(af.id, "source", v)} />
          </td>
        );

        if (k === "role") return (
          <td key={k} className="px-3 py-2">
            <InlineSelect value={af.role || ""} options={ROLE_OPTIONS}
              onChange={(v) => onSave(af.id, "role", v)} />
          </td>
        );

        if (RATING_COLUMN_KEYS.includes(k)) return (
          <td key={k} className="px-3 py-2 text-center">
            <StarRating value={afAny[k] as number | null}
              onChange={(v) => onSave(af.id, k, v)} />
          </td>
        );

        if (k === "notes") return (
          <td key={k} className="px-3 py-2">
            <input defaultValue={af.notes || ""} placeholder="—"
              onBlur={(e) => onSave(af.id, "notes", e.target.value)}
              className="w-full px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}
              key={`notes-${af.id}-${af.notes}`} />
          </td>
        );

        if (k === "version") return (
          <td key={k} className="px-3 py-2">
            <input defaultValue={af.version || ""} placeholder="—"
              onBlur={(e) => onSave(af.id, "version", e.target.value)}
              className="w-full px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}
              key={`ver-${af.id}-${af.version}`} />
          </td>
        );

        if (k === "clip_name") return (
          <td key={k} className="px-3 py-2">
            <input defaultValue={af.clip_name || ""} placeholder="—"
              onBlur={(e) => onSave(af.id, "clip_name", e.target.value)}
              className="w-full px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}
              key={`clip-${af.id}-${af.clip_name}`} />
          </td>
        );

        if (k === "session_date") return (
          <td key={k} className="px-3 py-2">
            <select value={af.session_id || ""} onChange={(e) => onSave(af.id, "session_id", e.target.value ? Number(e.target.value) : null)}
              className="w-full px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}>
              <option value="">—</option>
              {sessions.map(s => (
                <option key={s.id} value={s.id}>{s.date}</option>
              ))}
            </select>
          </td>
        );

        if (k === "file_type") return (
          <td key={k} className="px-3 py-2" style={{ color: "var(--text-muted)" }}>
            {af.file_type || "—"}
          </td>
        );

        if (k === "recorded_at") return (
          <td key={k} className="px-3 py-2">
            <input type="date" defaultValue={af.recorded_at?.split("T")[0] || ""}
              onBlur={(e) => onSave(af.id, "recorded_at", e.target.value || null)}
              className="px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}
              key={`rec-${af.id}-${af.recorded_at}`} />
          </td>
        );

        if (k === "uploaded_at") return (
          <td key={k} className="px-3 py-2">
            <input type="date" defaultValue={af.uploaded_at?.split("T")[0] || ""}
              onBlur={(e) => onSave(af.id, "uploaded_at", e.target.value || null)}
              className="px-1 py-0.5 rounded border text-xs outline-none bg-transparent" style={inputStyle}
              key={`upl-${af.id}-${af.uploaded_at}`} />
          </td>
        );

        if (k === "created_at") return (
          <td key={k} className="px-3 py-2" style={{ color: "var(--text-muted)" }}>
            {af.created_at ? new Date(af.created_at).toLocaleDateString() : "—"}
          </td>
        );

        return null;
      })}

      <td className="px-1 py-2">
        <div className="flex items-center gap-1">
          {onMove && (
            <button onClick={(e) => { e.stopPropagation(); onMove(af); }}
              className="p-1 rounded hover:bg-white/10" title="Move to another project"
              style={{ color: "var(--text-muted)" }}>
              <FolderInput size={12} />
            </button>
          )}
          <a href={api.media.audioFileDownloadUrl(af.id)} download
            className="p-1 rounded hover:bg-white/10" title="Download"
            style={{ color: "var(--text-muted)" }} onClick={(e) => e.stopPropagation()}>
            <Download size={12} />
          </a>
          {isDeleted ? (
            <button onClick={() => onRestore(af.id)}
              className="p-1 rounded hover:bg-white/10" title="Restore"
              style={{ color: "var(--green, #22c55e)" }}>
              <RotateCcw size={12} />
            </button>
          ) : (
            <button onClick={() => { if (confirm("Delete this file?")) onDelete(af.id); }}
              className="p-1 rounded hover:bg-white/10" title="Delete"
              style={{ color: "var(--text-muted)" }}>
              <Trash2 size={12} />
            </button>
          )}
        </div>
      </td>
    </tr>
  );
});

export default function Library() {
  const { multiProject } = useProject();
  const [movingAf, setMovingAf] = useState<AudioFile | null>(null);
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
  const [editingSongId, setEditingSongId] = useState<number | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [bulkSongOpen, setBulkSongOpen] = useState(false);
  const [showColumnPicker, setShowColumnPicker] = useState(false);
  const [visibleCols, setVisibleCols] = useState<Set<string>>(
    new Set(ALL_COLUMNS.filter(c => c.defaultVisible).map(c => c.key))
  );
  const [sortKey, setSortKey] = useState<string>("file");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  // Refs for shift-click range selection — read inside a stable callback so it
  // doesn't depend on (and get recreated by) the changing sorted list.
  const sortedRef = useRef<AudioFile[]>([]);
  const anchorRef = useRef<number | null>(null);

  // Row virtualization against the PAGE scroll (no inner scrollbar — the page
  // scrolls normally). Only rows in/near the viewport render; without this,
  // toggling a column or first load re-renders all ~700 rows (the lag).
  const scrollRef = useRef<HTMLDivElement>(null);
  const [range, setRange] = useState({ start: 0, end: 60 });
  const ROW_H = 42; // px estimate per (collapsed) row
  const OVERSCAN = 8;

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

  // Optimistic cache update that respects the active filter: replace the row
  // in every cached list, and DROP it from any list whose params it no longer
  // matches (e.g. it just got a song while you're viewing "Unassigned"). This
  // avoids both a full refetch and stale rows lingering in the wrong filter.
  const reconcileRow = useCallback((updated: AudioFile) => {
    queryClient.getQueriesData<AudioFile[]>({ queryKey: ["audio-files"] }).forEach(([key, data]) => {
      if (!Array.isArray(data)) return;
      const params = (Array.isArray(key) && key[1] ? key[1] : {}) as Record<string, string>;
      const replaced = data.map(f => (f.id === updated.id ? updated : f));
      const next = rowMatchesParams(updated, params) ? replaced : replaced.filter(f => f.id !== updated.id);
      queryClient.setQueryData(key, next);
    });
  }, [queryClient]);

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      api.audioFiles.update(id, data),
    onSuccess: (updated) => reconcileRow(updated),
  });

  const bulkMut = useMutation({
    mutationFn: ({ ids, data }: { ids: number[]; data: Record<string, unknown> }) =>
      api.audioFiles.bulkUpdate(ids, data),
    onSuccess: (rows) => rows.forEach(reconcileRow),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.audioFiles.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["audio-files"] }),
  });

  const restoreMut = useMutation({
    mutationFn: (id: number) => api.audioFiles.restore(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["audio-files"] }),
  });

  const extractAudioMut = useMutation({
    mutationFn: (id: number) => api.audioFiles.extractAudio(id),
    // Creates a NEW sibling file — refetch so it appears in the list.
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

  // React Query's `.mutate` is a referentially-stable function; the mutation
  // OBJECT is recreated every render. Depend on the stable mutate fns so these
  // row callbacks keep stable identity — otherwise LibraryRow's React.memo
  // never bails and all ~700 rows re-render on every sort/select (the lag).
  const updateMutate = updateMut.mutate;
  const updateSongMutate = updateSongMut.mutate;
  const deleteMutate = deleteMut.mutate;
  const restoreMutate = restoreMut.mutate;
  const extractMutate = extractAudioMut.mutate;

  const save = useCallback((id: number, field: string, value: unknown) => {
    updateMutate({ id, data: { [field]: value === "" ? null : value } });
  }, [updateMutate]);

  const saveSong = useCallback((songId: number, field: string, value: unknown) => {
    updateSongMutate({ id: songId, data: { [field]: value === "" ? null : value } });
  }, [updateSongMutate]);

  const onToggleExpand = useCallback((id: number) => setExpandedId(e => (e === id ? null : id)), []);
  // Shift-click selects the contiguous range between the last-clicked row
  // (anchor) and this one, in current sorted order. Refs keep this callback
  // stable so LibraryRow's memo isn't defeated.
  const onToggleSelect = useCallback((id: number, shiftKey: boolean) => {
    setSelected(prev => {
      const next = new Set(prev);
      const rows = sortedRef.current;
      if (shiftKey && anchorRef.current != null) {
        const a = rows.findIndex(r => r.id === anchorRef.current);
        const b = rows.findIndex(r => r.id === id);
        if (a !== -1 && b !== -1) {
          const [lo, hi] = a < b ? [a, b] : [b, a];
          for (let i = lo; i <= hi; i++) next.add(rows[i].id);
          anchorRef.current = id;
          return next;
        }
      }
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
    anchorRef.current = id;
  }, []);
  const onStartEditSong = useCallback((id: number) => setEditingSongId(id), []);
  const onStopEditSong = useCallback(() => setEditingSongId(null), []);
  const onDelete = useCallback((id: number) => deleteMutate(id), [deleteMutate]);
  const onRestore = useCallback((id: number) => restoreMutate(id), [restoreMutate]);
  const onExtract = useCallback((id: number) => extractMutate(id), [extractMutate]);
  // No-op: the InlineSongPicker already refreshes the song list (songs-all),
  // and the link PATCH's reconcileRow updates the row. Invalidating audio-files
  // here caused a race — a refetch issued before the link committed could land
  // afterward and re-add the file to "Unassigned".
  const onSongCreated = useCallback(() => {}, []);

  const toggleCol = (key: string) => {
    setVisibleCols(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("asc"); }
  };

  const sorted = useMemo(() => {
    return [...files].sort((a, b) => {
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
  }, [files, sortKey, sortDir]);
  sortedRef.current = sorted;

  const cols = useMemo(() => ALL_COLUMNS.filter(c => visibleCols.has(c.key)), [visibleCols]);
  const colCount = cols.length + 2; // checkbox + columns + actions

  // Visible window, clamped to the current list length.
  const total = sorted.length;
  const startIdx = Math.min(Math.max(0, range.start), Math.max(0, total - 1));
  const endIdx = Math.min(total, range.end);
  const topPad = startIdx * ROW_H;
  const botPad = Math.max(0, (total - endIdx) * ROW_H);
  const windowRows = sorted.slice(startIdx, endIdx);

  // Recompute the visible window from the PAGE scroll position. Re-binds when
  // the list size changes (filter/show-deleted); the listener handles scroll.
  useEffect(() => {
    const compute = () => {
      const el = scrollRef.current;
      if (!el) return;
      const top = el.getBoundingClientRect().top; // table top relative to viewport
      const rowsAbove = top < 0 ? Math.floor(-top / ROW_H) : 0;
      const start = Math.max(0, rowsAbove - OVERSCAN);
      const count = Math.ceil(window.innerHeight / ROW_H) + OVERSCAN * 2;
      setRange(prev => (prev.start === start && prev.end === start + count) ? prev : { start, end: start + count });
    };
    compute();
    // Capture phase so scroll from the inner <main className="overflow-y-auto">
    // container is caught (scroll doesn't bubble to window).
    window.addEventListener("scroll", compute, { capture: true, passive: true });
    window.addEventListener("resize", compute);
    return () => {
      window.removeEventListener("scroll", compute, { capture: true });
      window.removeEventListener("resize", compute);
    };
  }, [total]);

  const allVisibleSelected = sorted.length > 0 && sorted.every(af => selected.has(af.id));
  const toggleSelectAll = () => {
    setSelected(prev => {
      if (sorted.every(af => prev.has(af.id)) && sorted.length > 0) return new Set();
      return new Set(sorted.map(af => af.id));
    });
  };

  const selectedIds = useMemo(() => [...selected], [selected]);
  const applyBulk = (field: string, value: unknown) => {
    if (selectedIds.length === 0) return;
    bulkMut.mutate({ ids: selectedIds, data: { [field]: value === "" ? null : value } });
  };
  const bulkDelete = () => {
    if (selectedIds.length === 0) return;
    if (!confirm(`Delete ${selectedIds.length} file(s)?`)) return;
    Promise.all(selectedIds.map(id => api.audioFiles.delete(id)))
      .then(() => { setSelected(new Set()); queryClient.invalidateQueries({ queryKey: ["audio-files"] }); });
  };

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

      {/* Bulk-edit toolbar */}
      {selected.size > 0 && (
        <div className="flex gap-3 mb-3 flex-wrap items-center rounded-lg border px-3 py-2 sticky top-0 z-40"
          style={{ borderColor: "var(--accent)", background: "var(--bg-card)" }}>
          <span className="text-sm font-medium">{selected.size} selected</span>
          <div className="relative flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
            Song:
            <button onClick={() => setBulkSongOpen(o => !o)}
              className="px-2 py-1 rounded border text-xs bg-transparent" style={inputStyle}>
              — set —
            </button>
            {bulkSongOpen && (
              <div className="absolute top-full left-0 mt-1 z-50 p-2 rounded-lg border shadow-xl"
                style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
                <InlineSongPicker
                  songs={songs}
                  onSave={(songId) => { applyBulk("song_id", songId); setBulkSongOpen(false); }}
                  onSongCreated={onSongCreated}
                  onCancel={() => setBulkSongOpen(false)}
                />
              </div>
            )}
          </div>
          <div className="flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
            Source:
            <select defaultValue="" onChange={(e) => { if (e.target.value) applyBulk("source", e.target.value); e.target.value = ""; }}
              className="px-1 py-1 rounded border text-xs outline-none bg-transparent" style={inputStyle}>
              <option value="">— set —</option>
              {SOURCE_OPTIONS.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
            Role:
            <select defaultValue="" onChange={(e) => { if (e.target.value) applyBulk("role", e.target.value); e.target.value = ""; }}
              className="px-1 py-1 rounded border text-xs outline-none bg-transparent" style={inputStyle}>
              <option value="">— set —</option>
              {ROLE_OPTIONS.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
            Session:
            <select defaultValue="" onChange={(e) => { applyBulk("session_id", e.target.value ? Number(e.target.value) : null); e.target.value = ""; }}
              className="px-1 py-1 rounded border text-xs outline-none bg-transparent" style={inputStyle}>
              <option value="">— set —</option>
              {sessions.map(s => <option key={s.id} value={s.id}>{s.date}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
            Overall:
            <StarRating value={null} onChange={(v) => applyBulk("rating_overall", v)} />
          </div>
          <input type="date" title="Set recorded date"
            onChange={(e) => { if (e.target.value) applyBulk("recorded_at", e.target.value); }}
            className="px-1 py-1 rounded border text-xs outline-none bg-transparent" style={inputStyle} />
          <button onClick={bulkDelete}
            className="flex items-center gap-1 px-2 py-1 rounded border text-xs"
            style={{ borderColor: "var(--danger, #ef4444)", color: "var(--danger, #ef4444)" }}>
            <Trash2 size={12} /> Delete
          </button>
          <div className="ml-auto flex items-center gap-2">
            <MoveToProjectMenu kind="audio_file" ids={selectedIds} onMoved={() => setSelected(new Set())} compact />
            <button onClick={() => setSelected(new Set())}
              className="px-2 py-1 rounded text-xs" style={{ color: "var(--text-muted)" }}>
              Clear
            </button>
          </div>
        </div>
      )}

      {isLoading ? <div style={{ color: "var(--text-muted)" }}>Loading...</div> : (
        <div ref={scrollRef} className="rounded-xl border overflow-x-auto" style={{ borderColor: "var(--border)" }}>
          <table className="w-full text-xs">
            <thead>
              <tr style={{ background: "var(--bg-card)" }}>
                <th className="w-8 px-2 py-2.5">
                  <input type="checkbox" checked={allVisibleSelected} onChange={toggleSelectAll} />
                </th>
                {cols.map(col => (
                  <th key={col.key}
                    className={`text-left px-3 py-2.5 font-medium ${col.width || ""} ${col.sortable ? "cursor-pointer select-none" : ""}`}
                    style={{ color: sortKey === col.key ? "var(--accent)" : "var(--text-muted)" }}
                    onClick={() => col.sortable && toggleSort(col.key)}>
                    {col.label}
                    {sortKey === col.key && <span className="ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>}
                  </th>
                ))}
                <th className="w-16" />
              </tr>
            </thead>
            <tbody>
              {topPad > 0 && <tr style={{ height: topPad }}><td colSpan={colCount} style={{ padding: 0 }} /></tr>}
              {windowRows.map((af) => (
                <LibraryRow
                  key={af.id}
                  af={af}
                  cols={cols}
                  songs={songs}
                  sessions={sessions}
                  isExpanded={expandedId === af.id}
                  isSelected={selected.has(af.id)}
                  isEditingSong={editingSongId === af.id}
                  isExtracting={extractAudioMut.isPending && expandedId === af.id}
                  onToggleExpand={onToggleExpand}
                  onToggleSelect={onToggleSelect}
                  onStartEditSong={onStartEditSong}
                  onStopEditSong={onStopEditSong}
                  onSave={save}
                  onSaveSong={saveSong}
                  onExtract={onExtract}
                  onDelete={onDelete}
                  onRestore={onRestore}
                  onSongCreated={onSongCreated}
                  onMove={multiProject ? setMovingAf : undefined}
                />
              ))}
              {botPad > 0 && <tr style={{ height: botPad }}><td colSpan={colCount} style={{ padding: 0 }} /></tr>}
            </tbody>
          </table>
        </div>
      )}
      {movingAf && <MoveRecordingModal af={movingAf} onClose={() => setMovingAf(null)} />}
    </div>
  );
}
