import { useState, useRef } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { FolderOpen, Scan, Scissors, Play, Plus, Trash2, Check, Video, Folder, ChevronUp, X } from "lucide-react";

interface Clip {
  start_seconds: number;
  end_seconds: number;
  clip_name: string;
  song_id: number | null;
  notes: string;
  tags: string[];
}

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
}

function parseTime(str: string): number {
  const parts = str.split(":").map(Number);
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return parts[0] || 0;
}

const inputStyle = { borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" };
const QUICK_TAGS = ["good-take", "needs-work", "false-start", "best-take", "demo"];

function FileBrowserModal({ onSelect, onClose }: { onSelect: (path: string) => void; onClose: () => void }) {
  const [currentPath, setCurrentPath] = useState("/Users/adamklie");
  const { data } = useQuery({
    queryKey: ["browse", currentPath],
    queryFn: () => api.browse.list(currentPath),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.6)" }}>
      <div className="w-[560px] max-h-[70vh] rounded-xl border flex flex-col"
        style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: "var(--border)" }}>
          <h3 className="font-semibold text-sm">Select Video File</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-white/10"><X size={16} /></button>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 border-b text-xs" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
          {data?.parent && data.parent !== data.path && (
            <button onClick={() => setCurrentPath(data.parent)} className="p-1 rounded hover:bg-white/10"><ChevronUp size={14} /></button>
          )}
          <span className="truncate">{data?.path || currentPath}</span>
        </div>
        <div className="flex-1 overflow-y-auto px-2 py-2">
          {data?.error && <p className="text-sm px-2 py-4" style={{ color: "var(--red)" }}>{data.error}</p>}
          {data?.entries.map((entry) => (
            <button key={entry.path}
              onClick={() => entry.type === "directory" ? setCurrentPath(entry.path) : onSelect(entry.path)}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-left hover:opacity-80"
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
              {entry.type === "directory" ? <Folder size={16} style={{ color: "var(--yellow)" }} /> : <Video size={16} style={{ color: "var(--accent)" }} />}
              <span className="flex-1 truncate">{entry.name}</span>
              {entry.size_mb && <span className="text-xs" style={{ color: "var(--text-muted)" }}>{entry.size_mb} MB</span>}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function EnergyWaveform({ profile, clips, duration, threshold, onSeek }: {
  profile: { time: number; db: number }[];
  clips: Clip[];
  duration: number;
  threshold: number;
  onSeek: (t: number) => void;
}) {
  if (!profile.length) return null;
  const minDb = -60;
  const maxDb = 0;
  const h = 80;
  const w = 800;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full rounded-lg mb-4" style={{ background: "var(--bg)" }}
      onClick={(e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const t = (x / rect.width) * duration;
        onSeek(t);
      }}>
      {/* Threshold line */}
      <line x1={0} y1={h - ((threshold - minDb) / (maxDb - minDb)) * h}
        x2={w} y2={h - ((threshold - minDb) / (maxDb - minDb)) * h}
        stroke="var(--red)" strokeWidth={0.5} strokeDasharray="4 2" opacity={0.5} />

      {/* Clip regions */}
      {clips.map((clip, i) => (
        <rect key={i}
          x={(clip.start_seconds / duration) * w}
          width={((clip.end_seconds - clip.start_seconds) / duration) * w}
          y={0} height={h}
          fill="var(--accent)" opacity={0.15} />
      ))}

      {/* Energy bars */}
      {profile.map((p, i) => {
        const x = (p.time / duration) * w;
        const barH = Math.max(1, ((p.db - minDb) / (maxDb - minDb)) * h);
        const isGap = p.db < threshold;
        return (
          <rect key={i} x={x} y={h - barH} width={Math.max(1, w / profile.length - 0.5)} height={barH}
            fill={isGap ? "var(--text-muted)" : "var(--accent)"} opacity={isGap ? 0.3 : 0.6} />
        );
      })}
    </svg>
  );
}

export default function ProcessSession() {
  const [directory, setDirectory] = useState("/Users/adamklie/Desktop");
  const [directFile, setDirectFile] = useState("");
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null);
  const [showBrowser, setShowBrowser] = useState(false);
  const [clips, setClips] = useState<Clip[]>([]);
  const [duration, setDuration] = useState(0);
  const [sessionDate, setSessionDate] = useState(new Date().toISOString().split("T")[0]);
  const [existingSessionId, setExistingSessionId] = useState<number | null>(null);
  const [marking, setMarking] = useState<{ start: number } | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Energy-based detection tuning
  const [dropDb, setDropDb] = useState(6);
  const [minGapDuration, setMinGapDuration] = useState(2);
  const [minClipDuration, setMinClipDuration] = useState(30);
  const [showHelp, setShowHelp] = useState(false);

  const { data: songs = [] } = useQuery({ queryKey: ["songs-all"], queryFn: () => api.songs.list() });
  const { data: allSessions = [] } = useQuery({ queryKey: ["sessions-all"], queryFn: () => api.sessions.list() });
  const recentSessions = [...allSessions].sort((a, b) => (b.date ?? "").localeCompare(a.date ?? "")).slice(0, 30);
  useQuery({ queryKey: ["tags"], queryFn: () => api.tags.list() });

  const listMut = useMutation({ mutationFn: () => api.gopro.listVideos(directory) });

  const analyzeMut = useMutation({
    mutationFn: (path: string) => api.gopro.analyze(path, { dropDb, minGap: minGapDuration, minClip: minClipDuration }),
    onSuccess: (data) => {
      setDuration(data.duration_seconds);
      setClips(data.proposed_clips.map((c) => ({
        start_seconds: c.start_seconds, end_seconds: c.end_seconds,
        clip_name: c.suggested_name, song_id: null, notes: "", tags: [],
      })));
    },
  });

  const processMut = useMutation({
    mutationFn: () => api.gopro.process({
      source_path: selectedVideo!,
      session_date: sessionDate,
      clips: clips.map((c) => ({
        start_seconds: c.start_seconds, end_seconds: c.end_seconds,
        clip_name: c.clip_name, song_id: c.song_id,
      })),
      existing_session_id: existingSessionId,
    }),
  });

  const seekTo = (seconds: number) => { if (videoRef.current) videoRef.current.currentTime = seconds; };
  const getCurrentTime = () => videoRef.current?.currentTime || 0;
  const markStart = () => setMarking({ start: getCurrentTime() });
  const markEnd = () => {
    if (!marking) return;
    const end = getCurrentTime();
    if (end > marking.start) {
      setClips([...clips, {
        start_seconds: Math.round(marking.start), end_seconds: Math.round(end),
        clip_name: `clip_${clips.length + 1}`, song_id: null, notes: "", tags: [],
      }]);
    }
    setMarking(null);
  };

  const updateClip = (idx: number, field: string, value: unknown) => {
    const copy = [...clips];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (copy[idx] as any)[field] = value;
    setClips(copy);
  };

  const toggleClipTag = (idx: number, tag: string) => {
    const copy = [...clips];
    const tags = copy[idx].tags;
    copy[idx] = { ...copy[idx], tags: tags.includes(tag) ? tags.filter(t => t !== tag) : [...tags, tag] };
    setClips(copy);
  };

  const removeClip = (idx: number) => setClips(clips.filter((_, i) => i !== idx));
  const addEmptyClip = () => setClips([...clips, {
    start_seconds: Math.round(getCurrentTime()), end_seconds: Math.round(getCurrentTime()) + 60,
    clip_name: `clip_${clips.length + 1}`, song_id: null, notes: "", tags: [],
  }]);

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Process GoPro Session</h2>

      {/* Step 1: Select video */}
      <div className="rounded-xl p-5 border mb-6" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <h3 className="font-semibold mb-3 flex items-center gap-2">
          <FolderOpen size={18} style={{ color: "var(--accent)" }} /> Step 1: Select Video
        </h3>

        <div className="flex gap-2 mb-3">
          <input value={directFile} onChange={(e) => setDirectFile(e.target.value)}
            placeholder="Paste file path or click Browse..."
            className="flex-1 px-3 py-2 rounded-lg border text-sm outline-none" style={inputStyle}
            onKeyDown={(e) => { if (e.key === "Enter" && directFile.trim()) { setSelectedVideo(directFile.trim()); setClips([]); setDuration(0); } }} />
          <button onClick={() => setShowBrowser(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white"
            style={{ background: "var(--accent)" }}>
            <FolderOpen size={16} /> Browse
          </button>
          {directFile.trim() && (
            <button onClick={() => { setSelectedVideo(directFile.trim()); setClips([]); setDuration(0); }}
              className="px-4 py-2 rounded-lg text-sm border hover:opacity-80"
              style={{ borderColor: "var(--border)", color: "var(--text)" }}>Load</button>
          )}
        </div>

        {showBrowser && (
          <FileBrowserModal
            onSelect={(path) => { setDirectFile(path); setSelectedVideo(path); setClips([]); setDuration(0); setShowBrowser(false); }}
            onClose={() => setShowBrowser(false)} />
        )}

        <div className="flex items-center gap-3 mb-3">
          <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>or scan a directory</span>
          <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
        </div>

        <div className="flex gap-2 mb-4">
          <input value={directory} onChange={(e) => setDirectory(e.target.value)}
            placeholder="/Volumes/GOPRO/DCIM/100GOPRO"
            className="flex-1 px-3 py-2 rounded-lg border text-sm outline-none" style={inputStyle} />
          <button onClick={() => listMut.mutate()} disabled={listMut.isPending}
            className="px-4 py-2 rounded-lg text-sm font-medium border hover:opacity-80"
            style={{ borderColor: "var(--border)", color: "var(--text)" }}>
            {listMut.isPending ? "Scanning..." : "Scan Folder"}
          </button>
        </div>

        {listMut.data?.files && listMut.data.files.length > 0 && (
          <div className="space-y-2">
            {listMut.data.files.map((f) => (
              <div key={f.path}
                className="flex items-center justify-between p-3 rounded-lg border cursor-pointer"
                style={{ background: selectedVideo === f.path ? "var(--bg-hover)" : "var(--bg)", borderColor: selectedVideo === f.path ? "var(--accent)" : "var(--border)" }}
                onClick={() => { setSelectedVideo(f.path); setDirectFile(f.path); setClips([]); setDuration(0); }}>
                <div className="flex items-center gap-2">
                  <Video size={16} style={{ color: "var(--text-muted)" }} />
                  <span className="font-medium text-sm">{f.filename}</span>
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>{f.size_mb} MB</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {selectedVideo && (
          <div className="flex items-center justify-between p-3 rounded-lg border mt-3"
            style={{ background: "var(--bg-hover)", borderColor: "var(--accent)" }}>
            <div className="flex items-center gap-2">
              <Video size={16} style={{ color: "var(--accent)" }} />
              <span className="font-medium text-sm">{selectedVideo.split("/").pop()}</span>
            </div>
            <button onClick={() => analyzeMut.mutate(selectedVideo)} disabled={analyzeMut.isPending}
              className="flex items-center gap-1 px-3 py-1 rounded text-sm font-medium text-white"
              style={{ background: "var(--green)" }}>
              <Scan size={14} /> {analyzeMut.isPending ? "Analyzing..." : "Auto-Detect Clips"}
            </button>
          </div>
        )}
      </div>

      {/* Step 2: Review */}
      {selectedVideo && (
        <div className="rounded-xl p-5 border mb-6" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <Scissors size={18} style={{ color: "var(--blue)" }} /> Step 2: Review & Mark Clips
          </h3>

          {/* Detection tuning */}
          <div className="mb-4 p-4 rounded-lg" style={{ background: "var(--bg)" }}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium">Detection Settings</span>
              <div className="flex items-center gap-3">
                {analyzeMut.data && (
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                    Room level: {analyzeMut.data.median_db}dB | Threshold: {analyzeMut.data.threshold_db}dB | {clips.length} clips found
                  </span>
                )}
                <button onClick={() => setShowHelp(!showHelp)} className="text-xs underline" style={{ color: "var(--accent)" }}>
                  {showHelp ? "Hide tips" : "How to tune"}
                </button>
              </div>
            </div>

            {showHelp && (
              <div className="mb-4 p-3 rounded-lg text-xs space-y-2" style={{ background: "var(--bg-card)", color: "var(--text-muted)" }}>
                <p><strong style={{ color: "var(--text)" }}>How it works:</strong> The analyzer measures volume across the whole video, finds the typical "playing" level (median), then looks for moments where volume drops below that level. Those drops are the gaps between songs.</p>
                <p><strong style={{ color: "var(--text)" }}>Volume drop:</strong> How much quieter than the median a section needs to be to count as a "gap." <strong>Start at 4-6 dB.</strong> If you get one big clip, lower it (3-4). If you get too many clips, raise it (8-10). The waveform shows gray bars where gaps were detected.</p>
                <p><strong style={{ color: "var(--text)" }}>Min gap:</strong> How many seconds of quiet before it counts as a real gap (vs. a brief pause within a song). <strong>2-3s works for most practice sessions.</strong> Raise to 5-8s if short pauses between song sections are being detected as gaps.</p>
                <p><strong style={{ color: "var(--text)" }}>Min clip:</strong> Ignore detected clips shorter than this. <strong>30s filters out tuning and noodling.</strong> Lower to 15s if you play short songs. Raise to 60s if you're getting lots of small false clips.</p>
                <p><strong style={{ color: "var(--text)" }}>Tip:</strong> Click the waveform to seek the video to that point. Purple regions are detected clips, gray regions are gaps. The red dashed line is the threshold. Adjust sliders and hit Re-Analyze to iterate quickly.</p>
              </div>
            )}

            <div className="flex gap-4 items-end flex-wrap">
              <div>
                <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>
                  Volume drop: <strong>{dropDb} dB</strong> below median
                </label>
                <input type="range" min={2} max={20} value={dropDb}
                  onChange={(e) => setDropDb(Number(e.target.value))} className="w-36" />
                <div className="flex justify-between text-xs" style={{ color: "var(--text-muted)" }}>
                  <span>More clips</span><span>Fewer clips</span>
                </div>
              </div>
              <div>
                <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>
                  Min gap: <strong>{minGapDuration}s</strong>
                </label>
                <input type="range" min={1} max={15} step={0.5} value={minGapDuration}
                  onChange={(e) => setMinGapDuration(Number(e.target.value))} className="w-28" />
                <div className="flex justify-between text-xs" style={{ color: "var(--text-muted)" }}>
                  <span>Short</span><span>Long</span>
                </div>
              </div>
              <div>
                <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>
                  Min clip: <strong>{minClipDuration}s</strong>
                </label>
                <input type="range" min={5} max={180} step={5} value={minClipDuration}
                  onChange={(e) => setMinClipDuration(Number(e.target.value))} className="w-28" />
                <div className="flex justify-between text-xs" style={{ color: "var(--text-muted)" }}>
                  <span>Short</span><span>Long</span>
                </div>
              </div>
              <button onClick={() => analyzeMut.mutate(selectedVideo!)} disabled={analyzeMut.isPending}
                className="flex items-center gap-1 px-4 py-2 rounded text-sm font-medium text-white"
                style={{ background: "var(--green)" }}>
                <Scan size={14} /> {analyzeMut.isPending ? "Analyzing..." : "Re-Analyze"}
              </button>
            </div>
          </div>

          {/* Energy waveform */}
          {analyzeMut.data?.energy_profile && (
            <EnergyWaveform
              profile={analyzeMut.data.energy_profile}
              clips={clips}
              duration={duration}
              threshold={analyzeMut.data.threshold_db}
              onSeek={seekTo}
            />
          )}

          {/* Video player */}
          <video ref={videoRef} controls className="w-full rounded-lg mb-4" style={{ maxHeight: 400 }}>
            <source src={`/api/media/file/${encodeURIComponent(selectedVideo)}`} />
          </video>

          {/* Marking controls */}
          <div className="flex gap-2 mb-4">
            {!marking ? (
              <button onClick={markStart} className="flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-medium text-white"
                style={{ background: "var(--green)" }}><Play size={14} /> Mark Start</button>
            ) : (
              <button onClick={markEnd} className="flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-medium text-white animate-pulse"
                style={{ background: "var(--red)" }}><Scissors size={14} /> Mark End ({formatTime(marking.start)})</button>
            )}
            <button onClick={addEmptyClip} className="flex items-center gap-1 px-3 py-2 rounded-lg text-sm border"
              style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}><Plus size={14} /> Add Clip at Current Position</button>
          </div>

          {/* Clip list with metadata */}
          <div className="space-y-3">
            {clips.map((clip, i) => (
              <div key={i} className="p-3 rounded-lg border" style={{ background: "var(--bg)", borderColor: "var(--border)" }}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs w-6 text-center font-bold" style={{ color: "var(--accent)" }}>{i + 1}</span>
                  <button onClick={() => seekTo(clip.start_seconds)} title="Jump to start" className="text-xs" style={{ color: "var(--accent)" }}>▶</button>
                  <input value={formatTime(clip.start_seconds)}
                    onChange={(e) => updateClip(i, "start_seconds", parseTime(e.target.value))}
                    onFocus={() => seekTo(clip.start_seconds)}
                    title="Click to seek; type to edit"
                    className="w-20 px-2 py-1 rounded border text-sm text-center outline-none cursor-pointer" style={inputStyle} />
                  <span style={{ color: "var(--text-muted)" }}>→</span>
                  <button onClick={() => seekTo(clip.end_seconds)} title="Jump to end" className="text-xs" style={{ color: "var(--accent)" }}>▶</button>
                  <input value={formatTime(clip.end_seconds)}
                    onChange={(e) => updateClip(i, "end_seconds", parseTime(e.target.value))}
                    onFocus={() => seekTo(clip.end_seconds)}
                    title="Click to seek; type to edit"
                    className="w-20 px-2 py-1 rounded border text-sm text-center outline-none cursor-pointer" style={inputStyle} />
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>({formatTime(clip.end_seconds - clip.start_seconds)})</span>
                  <input value={clip.clip_name} onChange={(e) => updateClip(i, "clip_name", e.target.value)}
                    placeholder="clip name..." className="flex-1 px-2 py-1 rounded border text-sm outline-none" style={inputStyle} />
                  <button onClick={() => removeClip(i)} className="p-1 rounded hover:bg-white/10" style={{ color: "var(--red)" }}>
                    <Trash2 size={14} /></button>
                </div>
                {/* Metadata row */}
                <div className="flex items-center gap-2 ml-8">
                  <select value={clip.song_id || ""} onChange={(e) => updateClip(i, "song_id", e.target.value ? Number(e.target.value) : null)}
                    className="px-2 py-1 rounded border text-xs outline-none" style={inputStyle}>
                    <option value="">Link to song...</option>
                    {songs.map((s) => <option key={s.id} value={s.id}>{s.title}{s.artist ? ` — ${s.artist}` : ""}</option>)}
                  </select>
                  <div className="flex gap-1">
                    {QUICK_TAGS.map((tag) => (
                      <button key={tag} onClick={() => toggleClipTag(i, tag)}
                        className="px-1.5 py-0.5 rounded text-xs"
                        style={{
                          background: clip.tags.includes(tag) ? "var(--accent)" : "var(--bg-hover)",
                          color: clip.tags.includes(tag) ? "#fff" : "var(--text-muted)",
                        }}>
                        {tag}
                      </button>
                    ))}
                  </div>
                  <input value={clip.notes} onChange={(e) => updateClip(i, "notes", e.target.value)}
                    placeholder="Notes..." className="flex-1 px-2 py-1 rounded border text-xs outline-none" style={inputStyle} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Step 3: Process */}
      {clips.length > 0 && (
        <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <Check size={18} style={{ color: "var(--green)" }} /> Step 3: Process
          </h3>
          <div className="flex gap-3 items-center mb-4">
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Session Date</label>
              <input type="date" value={sessionDate} onChange={(e) => { setSessionDate(e.target.value); setExistingSessionId(null); }}
                className="px-3 py-2 rounded-lg border text-sm outline-none" style={inputStyle} />
            </div>
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Target Session</label>
              <select value={existingSessionId ?? ""} onChange={(e) => setExistingSessionId(e.target.value ? Number(e.target.value) : null)}
                className="px-3 py-2 rounded-lg border text-sm outline-none" style={inputStyle}>
                <option value="">New session</option>
                {recentSessions.map((s) => (
                  <option key={s.id} value={s.id}>#{s.id} · {s.date} · {s.folder_path.split("/").pop()} ({s.take_count ?? 0})</option>
                ))}
              </select>
            </div>
            <div className="flex-1" />
            <button onClick={() => processMut.mutate()} disabled={processMut.isPending || clips.length === 0}
              className="px-6 py-3 rounded-lg text-sm font-medium text-white disabled:opacity-50"
              style={{ background: "var(--accent)" }}>
              {processMut.isPending ? "Processing..." : `Process ${clips.length} Clips`}
            </button>
          </div>
          {processMut.data && (
            <div className="rounded-lg p-4" style={{ background: "var(--bg)" }}>
              <p className="text-sm font-medium" style={{ color: "var(--green)" }}>Processing complete!</p>
              <p className="text-sm mt-1">{processMut.data.clips_processed} clips cut, {processMut.data.audio_extracted} audio extracted</p>
              {processMut.data.errors.length > 0 && (
                <div className="mt-2">
                  <p className="text-sm" style={{ color: "var(--red)" }}>{processMut.data.errors.length} errors:</p>
                  {processMut.data.errors.map((e, i) => <p key={i} className="text-xs" style={{ color: "var(--text-muted)" }}>{e}</p>)}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
