import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Session, type AudioFile } from "../api/client";
import { ChevronDown, ChevronRight, Star, Video, FileAudio, FolderInput } from "lucide-react";
import MoveToProjectMenu from "../components/MoveToProjectMenu";
import MoveRecordingModal from "../components/MoveRecordingModal";
import { useProject } from "../project";

const RATING_DIMENSIONS = [
  { key: "rating_overall", label: "Overall" },
  { key: "rating_vocals", label: "Vocals" },
  { key: "rating_guitar", label: "Guitar" },
  { key: "rating_drums", label: "Drums" },
  { key: "rating_tone", label: "Tone" },
  { key: "rating_timing", label: "Timing" },
  { key: "rating_energy", label: "Energy" },
] as const;

function StarRating({ value, onChange, size = 14 }: { value: number | null; onChange: (r: number) => void; size?: number }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} onClick={() => onChange(n)} className="p-0">
          <Star size={size}
            fill={value && n <= value ? "var(--yellow)" : "none"}
            style={{ color: value && n <= value ? "var(--yellow)" : "var(--text-muted)" }} />
        </button>
      ))}
    </div>
  );
}

function AudioFileRating({ af }: { af: AudioFile }) {
  const [expanded, setExpanded] = useState(false);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.audioFiles.update(af.id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["session"] }),
  });

  return (
    <div>
      <div className="flex items-center gap-2">
        <span className="text-xs w-12" style={{ color: "var(--text-muted)" }}>Overall</span>
        <StarRating value={af.rating_overall} onChange={(r) => mutation.mutate({ rating_overall: r })} />
        <button onClick={() => setExpanded(!expanded)} className="text-xs ml-2" style={{ color: "var(--accent)" }}>
          {expanded ? "Less" : "More"}
        </button>
      </div>
      {expanded && (
        <div className="mt-2 space-y-1 pl-0">
          {RATING_DIMENSIONS.slice(1).map(({ key, label }) => (
            <div key={key} className="flex items-center gap-2">
              <span className="text-xs w-12" style={{ color: "var(--text-muted)" }}>{label}</span>
              <StarRating value={(af as unknown as Record<string, unknown>)[key] as number | null}
                onChange={(r) => mutation.mutate({ [key]: r })} size={12} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RecordingCard({ af }: { af: AudioFile }) {
  const { multiProject } = useProject();
  const [moving, setMoving] = useState(false);
  const isVideo = af.file_type && ["mp4", "mov", "m4v"].includes(af.file_type);
  return (
    <div className="rounded-lg p-4 border" style={{ background: "var(--bg)", borderColor: "var(--border)" }}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{af.song_title || af.clip_name || af.file_path.split("/").pop()}</span>
          {isVideo ? <Video size={14} style={{ color: "var(--text-muted)" }} /> : <FileAudio size={14} style={{ color: "var(--text-muted)" }} />}
          <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "var(--bg-hover)", color: "var(--text-muted)" }}>
            {af.file_type}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {multiProject && (
            <button onClick={() => setMoving(true)} title="Move to another project"
              className="p-0.5 rounded hover:bg-white/10" style={{ color: "var(--text-muted)" }}>
              <FolderInput size={14} />
            </button>
          )}
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            {af.start_time && af.end_time ? `${af.start_time} - ${af.end_time}` : ""}
          </span>
        </div>
      </div>
      {moving && <MoveRecordingModal afs={[af]} onClose={() => setMoving(false)} />}
      {isVideo ? (
        <video controls className="w-full rounded mb-2" style={{ maxHeight: 200 }}>
          <source src={api.media.audioFileUrl(af.id)} />
        </video>
      ) : (
        <audio controls className="w-full h-8 mb-2" style={{ filter: "invert(1) hue-rotate(180deg)" }}>
          <source src={api.media.audioFileUrl(af.id)} />
        </audio>
      )}
      <AudioFileRating af={af} />
    </div>
  );
}

function SessionCard({ session }: { session: Session }) {
  const [expanded, setExpanded] = useState(false);
  const { data: detail } = useQuery({
    queryKey: ["session", session.id],
    queryFn: () => api.sessions.get(session.id),
    enabled: expanded,
  });

  return (
    <div className="rounded-xl border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <div className="flex items-center pr-4">
        <button onClick={() => setExpanded(!expanded)} className="flex-1 flex items-center justify-between p-5 text-left">
          <div className="flex items-center gap-3">
            {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            <div>
              <div className="font-semibold">{session.name || session.date}</div>
              <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                {session.name ? `${session.date} · ` : ""}{session.track_count} recordings
              </div>
            </div>
          </div>
        </button>
        <MoveToProjectMenu kind="session" ids={[session.id]} compact />
      </div>
      {expanded && detail && (
        <div className="px-5 pb-5 space-y-3">
          {detail.audio_files.map((af) => <RecordingCard key={af.id} af={af} />)}
        </div>
      )}
    </div>
  );
}

export default function Sessions() {
  const { data: sessions = [], isLoading } = useQuery({
    queryKey: ["sessions"],
    queryFn: api.sessions.list,
  });

  if (isLoading) return <div style={{ color: "var(--text-muted)" }}>Loading...</div>;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Sessions</h2>
      <div className="space-y-3">
        {sessions.map((s) => <SessionCard key={s.id} session={s} />)}
      </div>
    </div>
  );
}
