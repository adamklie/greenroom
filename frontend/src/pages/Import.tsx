import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { SongSelect } from "../components/InlineSongPicker";
import { Upload, FileAudio, Check, Plus, X, Scissors, FolderUp, Layers } from "lucide-react";
import { useProject } from "../project";

const inputStyle = { borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" };

const MEDIA_EXTS = /\.(m4a|mp3|wav|aac|flac|ogg|aiff?|mp4|mov|avi|mkv|m4v)$/i;

const SOURCE_OPTIONS = [
  { value: "phone", label: "Phone Recording" },
  { value: "logic_pro", label: "Logic Pro" },
  { value: "garageband", label: "GarageBand" },
  { value: "suno_ai", label: "Suno AI" },
  { value: "collaborator", label: "Collaborator" },
  { value: "download", label: "Download" },
  { value: "unknown", label: "Other" },
];

const ROLE_OPTIONS = [
  { value: "recording", label: "Recording" },
  { value: "demo", label: "Demo" },
  { value: "reference", label: "Reference (Original)" },
  { value: "backing_track", label: "Backing Track" },
  { value: "final_mix", label: "Final Mix" },
];

interface PendingFile {
  file: File;
  songId: number | null;
  createTitle: string;
  songType: string;
  project: string;
  source: string;
  role: string;
  notes: string;
  recordedAt: string;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
  resultId?: number;
}

function TrimControls({ audioFileId }: { audioFileId: number }) {
  const [trimStart, setTrimStart] = useState("");
  const [trimEnd, setTrimEnd] = useState("");
  const [showTrim, setShowTrim] = useState(false);
  const trimMut = useMutation({
    mutationFn: () => api.audioFiles.trim(audioFileId, parseFloat(trimStart), parseFloat(trimEnd)),
    onSuccess: () => { setTrimStart(""); setTrimEnd(""); },
  });
  const iStyle = { borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" };
  return (
    <div className="mt-2">
      <button onClick={() => setShowTrim(!showTrim)}
        className="flex items-center gap-1 text-xs mb-1" style={{ color: "var(--accent)" }}>
        <Scissors size={11} /> {showTrim ? "Cancel Trim" : "Trim Audio"}
      </button>
      {showTrim && (
        <div className="flex items-end gap-2">
          <div>
            <label className="text-xs block mb-0.5" style={{ color: "var(--text-muted)" }}>Start (sec)</label>
            <input type="number" step="0.1" min="0" value={trimStart}
              onChange={(e) => setTrimStart(e.target.value)}
              className="w-20 px-2 py-1 rounded border text-xs outline-none" style={iStyle} placeholder="0.0" />
          </div>
          <div>
            <label className="text-xs block mb-0.5" style={{ color: "var(--text-muted)" }}>End (sec)</label>
            <input type="number" step="0.1" min="0" value={trimEnd}
              onChange={(e) => setTrimEnd(e.target.value)}
              className="w-20 px-2 py-1 rounded border text-xs outline-none" style={iStyle} placeholder="30.0" />
          </div>
          <button onClick={() => trimMut.mutate()}
            disabled={!trimStart || !trimEnd || trimMut.isPending}
            className="px-3 py-1 rounded text-xs text-white disabled:opacity-50"
            style={{ background: "var(--accent)" }}>
            {trimMut.isPending ? "Trimming..." : "Create Trim"}
          </button>
          {trimMut.isError && <span className="text-xs" style={{ color: "var(--red, #f44)" }}>Failed</span>}
          {trimMut.isSuccess && <span className="text-xs" style={{ color: "var(--green)" }}>Trimmed!</span>}
        </div>
      )}
    </div>
  );
}

function FileCard({ pending, songs, grouped, onChange, onRemove, onUpload }: {
  pending: PendingFile;
  songs: { id: number; title: string; artist: string | null; type: string }[];
  grouped: boolean;
  onChange: (updates: Partial<PendingFile>) => void;
  onRemove: () => void;
  onUpload: () => void;
}) {
  const { multiProject } = useProject();
  const sizeMb = (pending.file.size / (1024 * 1024)).toFixed(1);
  const isDone = pending.status === "done";
  const isUploading = pending.status === "uploading";

  return (
    <div className="rounded-xl p-4 border" style={{
      background: "var(--bg-card)", borderColor: isDone ? "var(--green)" : "var(--border)",
      opacity: isDone ? 0.7 : 1,
    }}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          {isDone ? <Check size={18} style={{ color: "var(--green)" }} /> : <FileAudio size={18} style={{ color: "var(--accent)" }} />}
          <div>
            <div className="font-medium text-sm">{pending.file.name}</div>
            <div className="text-xs" style={{ color: "var(--text-muted)" }}>
              {sizeMb} MB{isUploading ? " · importing…" : ""}
            </div>
          </div>
        </div>
        {!isDone && (
          <button onClick={onRemove} className="p-1 rounded hover:bg-white/10" style={{ color: "var(--text-muted)" }}>
            <X size={14} />
          </button>
        )}
      </div>

      {/* Grouped (session) mode: compact — just an optional existing-song link.
          The session import button lives in the toolbar above. */}
      {!isDone && grouped && (
        <div>
          <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Link to song (optional)</label>
          <SongSelect
            songs={songs}
            value={pending.songId}
            onChange={(songId) => onChange({ songId })}
            allowCreate={false}
            placeholder="Leave blank to assign later…"
            className="w-full px-2 py-1.5 rounded border text-sm text-left outline-none"
          />
          {pending.error && <p className="text-xs mt-2" style={{ color: "var(--red)" }}>{pending.error}</p>}
        </div>
      )}

      {!isDone && !grouped && (
        <>
          <div className="grid grid-cols-2 gap-2 mb-3">
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Type</label>
              <select value={pending.songType} onChange={(e) => onChange({ songType: e.target.value })}
                className="w-full px-2 py-1.5 rounded border text-sm outline-none" style={inputStyle}>
                <option value="cover">Cover</option>
                <option value="original">Original</option>
                <option value="idea">Idea</option>
              </select>
            </div>
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Source</label>
              <select value={pending.source} onChange={(e) => onChange({ source: e.target.value })}
                className="w-full px-2 py-1.5 rounded border text-sm outline-none" style={inputStyle}>
                {SOURCE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            {/* Legacy project picker — under multi-project the active project
                (sidebar switcher) determines placement, so hide it. */}
            {!multiProject && (
              <div>
                <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Project</label>
                <select value={pending.project} onChange={(e) => onChange({ project: e.target.value })}
                  className="w-full px-2 py-1.5 rounded border text-sm outline-none" style={inputStyle}>
                  <option value="solo">Solo</option>
                  <option value="ozone_destructors">Ozone Destructors</option>
                  <option value="sural">Sural</option>
                  <option value="joe">Joe</option>
                  <option value="ideas">Ideas</option>
                </select>
              </div>
            )}
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Role</label>
              <select value={pending.role} onChange={(e) => onChange({ role: e.target.value })}
                className="w-full px-2 py-1.5 rounded border text-sm outline-none" style={inputStyle}>
                {ROLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </div>

          <div className="mb-3">
            <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Link to song</label>
            <SongSelect
              songs={songs}
              value={pending.songId}
              onChange={(songId) => onChange({ songId, createTitle: songId ? "" : pending.createTitle })}
              allowCreate={false}
              placeholder="Search to link an existing song…"
              className="w-full px-2 py-1.5 rounded border text-sm text-left outline-none"
            />
            {!pending.songId && (
              <input value={pending.createTitle} onChange={(e) => onChange({ createTitle: e.target.value })}
                placeholder="New song title..."
                className="w-full mt-2 px-2 py-1.5 rounded border text-sm outline-none" style={inputStyle} />
            )}
          </div>

          <div className="mb-3">
            <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Recorded date (optional)</label>
            <input type="date" value={pending.recordedAt} onChange={(e) => onChange({ recordedAt: e.target.value })}
              className="w-full px-2 py-1.5 rounded border text-sm outline-none" style={inputStyle} />
          </div>

          <input value={pending.notes} onChange={(e) => onChange({ notes: e.target.value })}
            placeholder="Notes (optional)..."
            className="w-full px-2 py-1.5 rounded border text-sm outline-none mb-3" style={inputStyle} />

          <button onClick={onUpload} disabled={isUploading || (!pending.songId && !pending.createTitle)}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50"
            style={{ background: "var(--accent)" }}>
            <Upload size={14} /> {isUploading ? "Importing..." : "Import"}
          </button>

          {pending.error && <p className="text-xs mt-2" style={{ color: "var(--red)" }}>{pending.error}</p>}
        </>
      )}

      {isDone && (
        <div>
          <p className="text-xs" style={{ color: "var(--green)" }}>Imported successfully</p>
          {pending.resultId && <TrimControls audioFileId={pending.resultId} />}
        </div>
      )}
    </div>
  );
}

export default function Import() {
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [grouped, setGrouped] = useState(false);
  const [sessionName, setSessionName] = useState("");
  const [sessionDate, setSessionDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [groupBusy, setGroupBusy] = useState(false);
  const [groupError, setGroupError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: songs = [] } = useQuery({
    queryKey: ["songs-all"],
    queryFn: () => api.songs.list(),
  });

  const addFiles = useCallback((files: FileList | File[]) => {
    const media = Array.from(files).filter((f) => MEDIA_EXTS.test(f.name));
    const newPending: PendingFile[] = media.map((file) => {
      const name = file.name.replace(/\.[^.]+$/, "").replace(/[_-]/g, " ");
      return {
        file,
        songId: null,
        createTitle: name,
        songType: "idea",
        project: "solo",
        source: "unknown",
        role: "recording",
        notes: "",
        recordedAt: "",
        status: "pending" as const,
      };
    });
    setPendingFiles((prev) => [...prev, ...newPending]);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) addFiles(e.dataTransfer.files);
  }, [addFiles]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => setIsDragging(false), []);

  const updateFile = (idx: number, updates: Partial<PendingFile>) => {
    setPendingFiles((prev) => prev.map((f, i) => i === idx ? { ...f, ...updates } : f));
  };

  const removeFile = (idx: number) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const uploadFile = async (idx: number, sessionId?: number) => {
    const pending = pendingFiles[idx];
    updateFile(idx, { status: "uploading", error: undefined });

    const formData = new FormData();
    formData.append("file", pending.file);
    if (pending.songId) formData.append("song_id", String(pending.songId));
    // Only auto-create a song for ungrouped imports — session clips stay
    // unlinked unless you pick an existing song.
    if (!sessionId && !pending.songId && pending.createTitle) {
      formData.append("create_song_title", pending.createTitle);
    }
    formData.append("song_type", pending.songType);
    formData.append("project", pending.project);
    formData.append("source", pending.source);
    formData.append("role", sessionId ? "practice_clip" : pending.role);
    if (pending.notes) formData.append("notes", pending.notes);
    if (sessionId) formData.append("session_id", String(sessionId));
    // Optional recorded date (ungrouped imports). Session clips inherit the
    // session date server-side, so only send this when it's explicitly set.
    if (!sessionId && pending.recordedAt) formData.append("recorded_at", pending.recordedAt);

    try {
      const res = await fetch("/api/upload", { method: "POST", body: formData });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      updateFile(idx, { status: "done", resultId: data.audio_file_id });
      queryClient.invalidateQueries({ queryKey: ["songs"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    } catch (e) {
      updateFile(idx, { status: "error", error: String(e) });
      throw e;
    }
  };

  const uploadAll = async () => {
    for (let i = 0; i < pendingFiles.length; i++) {
      if (pendingFiles[i].status === "pending") {
        try { await uploadFile(i); } catch { /* per-file error already shown */ }
      }
    }
  };

  const importIntoSession = async () => {
    setGroupError(null);
    if (!sessionName.trim()) { setGroupError("Session name is required"); return; }
    setGroupBusy(true);
    try {
      const session = await api.sessions.create({ name: sessionName.trim(), date: sessionDate });
      for (let i = 0; i < pendingFiles.length; i++) {
        const st = pendingFiles[i].status;
        if (st === "pending" || st === "error") {
          try { await uploadFile(i, session.id); } catch { /* shown on the card */ }
        }
      }
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    } catch (e) {
      setGroupError(String(e));
    } finally {
      setGroupBusy(false);
    }
  };

  const pendingCount = pendingFiles.filter((f) => f.status === "pending").length;
  const remainingCount = pendingFiles.filter((f) => f.status === "pending" || f.status === "error").length;
  const doneCount = pendingFiles.filter((f) => f.status === "done").length;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-2">Import</h2>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        Drag and drop files (or a folder) to import them into your music library
      </p>

      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className="rounded-xl border-2 border-dashed p-12 text-center mb-6 transition-colors"
        style={{
          borderColor: isDragging ? "var(--accent)" : "var(--border)",
          background: isDragging ? "rgba(16, 185, 129, 0.05)" : "transparent",
        }}
      >
        <Upload size={40} className="mx-auto mb-4" style={{ color: isDragging ? "var(--accent)" : "var(--text-muted)" }} />
        <p className="font-medium mb-1">{isDragging ? "Drop files here" : "Drag & drop audio or video files"}</p>
        <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
          m4a, mp3, wav — or mp4, mov (video kept)
        </p>
        <div className="flex items-center justify-center gap-2">
          <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white cursor-pointer"
            style={{ background: "var(--accent)" }}>
            <Plus size={16} /> Browse files
            <input type="file" multiple accept="audio/*,video/*" className="hidden"
              onChange={(e) => { if (e.target.files) addFiles(e.target.files); e.target.value = ""; }} />
          </label>
          <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium cursor-pointer border"
            style={{ borderColor: "var(--border)", color: "var(--text)" }}>
            <FolderUp size={16} /> Upload folder
            <input type="file" className="hidden"
              {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
              onChange={(e) => { if (e.target.files) addFiles(e.target.files); e.target.value = ""; }} />
          </label>
        </div>
      </div>

      {/* Pending files */}
      {pendingFiles.length > 0 && (
        <>
          {/* Session grouping panel */}
          <div className="rounded-xl border p-4 mb-4" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" checked={grouped} onChange={(e) => setGrouped(e.target.checked)} />
              <Layers size={16} style={{ color: "var(--accent)" }} />
              <span className="text-sm font-medium">Group these files into a session</span>
            </label>
            {grouped && (
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Session name</label>
                  <input value={sessionName} onChange={(e) => setSessionName(e.target.value)}
                    placeholder="e.g. Tuesday Rehearsal"
                    className="w-full px-2 py-1.5 rounded border text-sm outline-none" style={inputStyle} />
                </div>
                <div>
                  <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Date</label>
                  <input type="date" value={sessionDate} onChange={(e) => setSessionDate(e.target.value)}
                    className="w-full px-2 py-1.5 rounded border text-sm outline-none" style={inputStyle} />
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between mb-4">
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>
              {pendingFiles.length} file{pendingFiles.length > 1 ? "s" : ""} ({doneCount} imported)
            </span>
            {grouped ? (
              <button onClick={importIntoSession} disabled={groupBusy || remainingCount === 0 || !sessionName.trim()}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50"
                style={{ background: "var(--accent)" }}>
                <Layers size={14} /> {groupBusy ? "Importing…" : `Create session & import (${remainingCount})`}
              </button>
            ) : (
              pendingCount > 1 && (
                <button onClick={uploadAll}
                  className="px-4 py-2 rounded-lg text-sm font-medium text-white"
                  style={{ background: "var(--accent)" }}>
                  Import All ({pendingCount})
                </button>
              )
            )}
          </div>

          {groupError && <p className="text-sm mb-3" style={{ color: "var(--red)" }}>{groupError}</p>}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {pendingFiles.map((pending, idx) => (
              <FileCard
                key={`${pending.file.name}-${idx}`}
                pending={pending}
                songs={songs}
                grouped={grouped}
                onChange={(updates) => updateFile(idx, updates)}
                onRemove={() => removeFile(idx)}
                onUpload={() => { uploadFile(idx).catch(() => {}); }}
              />
            ))}
          </div>
        </>
      )}

    </div>
  );
}
