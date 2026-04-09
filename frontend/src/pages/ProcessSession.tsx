import { useState, useRef } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { FolderOpen, Scan, Scissors, Play, Plus, Trash2, Check, Video } from "lucide-react";

interface Clip {
  start_seconds: number;
  end_seconds: number;
  clip_name: string;
  song_id: number | null;
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

export default function ProcessSession() {
  const [directory, setDirectory] = useState("/Users/adamklie/Desktop");
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null);
  const [clips, setClips] = useState<Clip[]>([]);
  const [duration, setDuration] = useState(0);
  const [sessionDate, setSessionDate] = useState(new Date().toISOString().split("T")[0]);
  const [marking, setMarking] = useState<{ start: number } | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const { data: songs = [] } = useQuery({
    queryKey: ["songs-all"],
    queryFn: () => api.songs.list(),
  });

  const listMut = useMutation({
    mutationFn: () => api.gopro.listVideos(directory),
  });

  const analyzeMut = useMutation({
    mutationFn: (path: string) => api.gopro.analyze(path),
    onSuccess: (data) => {
      setDuration(data.duration_seconds);
      setClips(data.proposed_clips.map((c) => ({
        start_seconds: c.start_seconds,
        end_seconds: c.end_seconds,
        clip_name: c.suggested_name,
        song_id: null,
      })));
    },
  });

  const processMut = useMutation({
    mutationFn: () => api.gopro.process({
      source_path: selectedVideo!,
      session_date: sessionDate,
      clips: clips.map((c) => ({
        start_seconds: c.start_seconds,
        end_seconds: c.end_seconds,
        clip_name: c.clip_name,
        song_id: c.song_id,
      })),
    }),
  });

  const seekTo = (seconds: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = seconds;
    }
  };

  const getCurrentTime = () => videoRef.current?.currentTime || 0;

  const markStart = () => {
    setMarking({ start: getCurrentTime() });
  };

  const markEnd = () => {
    if (!marking) return;
    const end = getCurrentTime();
    if (end > marking.start) {
      setClips([...clips, {
        start_seconds: Math.round(marking.start),
        end_seconds: Math.round(end),
        clip_name: `clip_${clips.length + 1}`,
        song_id: null,
      }]);
    }
    setMarking(null);
  };

  const updateClip = (idx: number, field: keyof Clip, value: string | number | null) => {
    const copy = [...clips];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (copy[idx] as any)[field] = value;
    setClips(copy);
  };

  const removeClip = (idx: number) => setClips(clips.filter((_, i) => i !== idx));

  const addEmptyClip = () => {
    setClips([...clips, {
      start_seconds: 0,
      end_seconds: 60,
      clip_name: `clip_${clips.length + 1}`,
      song_id: null,
    }]);
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Process GoPro Session</h2>

      {/* Step 1: Select video source */}
      <div className="rounded-xl p-5 border mb-6" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <h3 className="font-semibold mb-3 flex items-center gap-2">
          <FolderOpen size={18} style={{ color: "var(--accent)" }} />
          Step 1: Select Video
        </h3>
        <div className="flex gap-2 mb-4">
          <input value={directory} onChange={(e) => setDirectory(e.target.value)}
            placeholder="/Volumes/GOPRO/DCIM/100GOPRO"
            className="flex-1 px-3 py-2 rounded-lg border text-sm outline-none" style={inputStyle} />
          <button onClick={() => listMut.mutate()}
            disabled={listMut.isPending}
            className="px-4 py-2 rounded-lg text-sm font-medium text-white"
            style={{ background: "var(--accent)" }}>
            {listMut.isPending ? "Scanning..." : "Scan"}
          </button>
        </div>

        {listMut.data?.files && listMut.data.files.length > 0 && (
          <div className="space-y-2">
            {listMut.data.files.map((f) => (
              <div key={f.path}
                className="flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors"
                style={{
                  background: selectedVideo === f.path ? "var(--bg-hover)" : "var(--bg)",
                  borderColor: selectedVideo === f.path ? "var(--accent)" : "var(--border)",
                }}
                onClick={() => { setSelectedVideo(f.path); setClips([]); setDuration(0); }}>
                <div className="flex items-center gap-2">
                  <Video size={16} style={{ color: "var(--text-muted)" }} />
                  <span className="font-medium text-sm">{f.filename}</span>
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>{f.size_mb} MB</span>
                </div>
                {selectedVideo === f.path && (
                  <button onClick={(e) => { e.stopPropagation(); analyzeMut.mutate(f.path); }}
                    disabled={analyzeMut.isPending}
                    className="flex items-center gap-1 px-3 py-1 rounded text-sm font-medium text-white"
                    style={{ background: "var(--green)" }}>
                    <Scan size={14} />
                    {analyzeMut.isPending ? "Analyzing..." : "Auto-Detect Clips"}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {listMut.data?.files?.length === 0 && (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>No video files found in that directory.</p>
        )}
      </div>

      {/* Step 2: Video player + clip marking */}
      {selectedVideo && (
        <div className="rounded-xl p-5 border mb-6" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <Scissors size={18} style={{ color: "var(--blue)" }} />
            Step 2: Review & Mark Clips
          </h3>

          {/* Video player */}
          <video ref={videoRef} controls className="w-full rounded-lg mb-4" style={{ maxHeight: 400 }}>
            <source src={`/api/media/file/${encodeURIComponent(selectedVideo)}`} />
          </video>

          {/* Clip timeline visualization */}
          {duration > 0 && (
            <div className="relative h-8 rounded-full mb-4" style={{ background: "var(--bg-hover)" }}>
              {clips.map((clip, i) => {
                const left = (clip.start_seconds / duration) * 100;
                const width = ((clip.end_seconds - clip.start_seconds) / duration) * 100;
                return (
                  <div key={i} className="absolute h-full rounded-full cursor-pointer opacity-70 hover:opacity-100"
                    style={{ left: `${left}%`, width: `${Math.max(width, 0.5)}%`, background: "var(--accent)", top: 0 }}
                    onClick={() => seekTo(clip.start_seconds)}
                    title={`${clip.clip_name}: ${formatTime(clip.start_seconds)} - ${formatTime(clip.end_seconds)}`}
                  />
                );
              })}
            </div>
          )}

          {/* Manual marking controls */}
          <div className="flex gap-2 mb-4">
            {!marking ? (
              <button onClick={markStart}
                className="flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-medium text-white"
                style={{ background: "var(--green)" }}>
                <Play size={14} /> Mark Start
              </button>
            ) : (
              <button onClick={markEnd}
                className="flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-medium text-white animate-pulse"
                style={{ background: "var(--red)" }}>
                <Scissors size={14} /> Mark End (started at {formatTime(marking.start)})
              </button>
            )}
            <button onClick={addEmptyClip}
              className="flex items-center gap-1 px-3 py-2 rounded-lg text-sm border"
              style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
              <Plus size={14} /> Add Clip Manually
            </button>
            {analyzeMut.data && (
              <span className="self-center text-xs" style={{ color: "var(--text-muted)" }}>
                {analyzeMut.data.silence_gaps.length} silence gaps detected
              </span>
            )}
          </div>

          {/* Clip list */}
          <div className="space-y-2">
            {clips.map((clip, i) => (
              <div key={i} className="flex items-center gap-2 p-3 rounded-lg border"
                style={{ background: "var(--bg)", borderColor: "var(--border)" }}>
                <span className="text-xs w-6 text-center" style={{ color: "var(--text-muted)" }}>{i + 1}</span>
                <button onClick={() => seekTo(clip.start_seconds)} className="text-xs px-1" style={{ color: "var(--accent)" }}>▶</button>
                <input value={formatTime(clip.start_seconds)}
                  onChange={(e) => updateClip(i, "start_seconds", parseTime(e.target.value))}
                  className="w-20 px-2 py-1 rounded border text-sm text-center outline-none" style={inputStyle} />
                <span style={{ color: "var(--text-muted)" }}>→</span>
                <input value={formatTime(clip.end_seconds)}
                  onChange={(e) => updateClip(i, "end_seconds", parseTime(e.target.value))}
                  className="w-20 px-2 py-1 rounded border text-sm text-center outline-none" style={inputStyle} />
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                  ({formatTime(clip.end_seconds - clip.start_seconds)})
                </span>
                <input value={clip.clip_name} onChange={(e) => updateClip(i, "clip_name", e.target.value)}
                  placeholder="clip name..."
                  className="flex-1 px-2 py-1 rounded border text-sm outline-none" style={inputStyle} />
                <select value={clip.song_id || ""} onChange={(e) => updateClip(i, "song_id", e.target.value ? Number(e.target.value) : null)}
                  className="w-40 px-2 py-1 rounded border text-sm outline-none" style={inputStyle}>
                  <option value="">Link to song...</option>
                  {songs.map((s) => (
                    <option key={s.id} value={s.id}>{s.title}</option>
                  ))}
                </select>
                <button onClick={() => removeClip(i)} className="p-1 rounded hover:bg-white/10" style={{ color: "var(--red)" }}>
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Step 3: Process */}
      {clips.length > 0 && (
        <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <Check size={18} style={{ color: "var(--green)" }} />
            Step 3: Process
          </h3>
          <div className="flex gap-3 items-center mb-4">
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--text-muted)" }}>Session Date</label>
              <input type="date" value={sessionDate} onChange={(e) => setSessionDate(e.target.value)}
                className="px-3 py-2 rounded-lg border text-sm outline-none" style={inputStyle} />
            </div>
            <div className="flex-1" />
            <button onClick={() => processMut.mutate()}
              disabled={processMut.isPending || clips.length === 0}
              className="px-6 py-3 rounded-lg text-sm font-medium text-white disabled:opacity-50"
              style={{ background: "var(--accent)" }}>
              {processMut.isPending ? "Processing..." : `Process ${clips.length} Clips`}
            </button>
          </div>

          {processMut.data && (
            <div className="rounded-lg p-4" style={{ background: "var(--bg)" }}>
              <p className="text-sm font-medium" style={{ color: "var(--green)" }}>
                Processing complete!
              </p>
              <p className="text-sm mt-1">
                {processMut.data.clips_processed} clips cut, {processMut.data.audio_extracted} audio extracted
              </p>
              {processMut.data.errors.length > 0 && (
                <div className="mt-2">
                  <p className="text-sm" style={{ color: "var(--red)" }}>{processMut.data.errors.length} errors:</p>
                  {processMut.data.errors.map((e, i) => (
                    <p key={i} className="text-xs" style={{ color: "var(--text-muted)" }}>{e}</p>
                  ))}
                </div>
              )}
              <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
                Session ID: {processMut.data.session_id} | cuts.txt saved to {processMut.data.cuts_txt_path}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
