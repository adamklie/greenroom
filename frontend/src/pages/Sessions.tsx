import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Session, type AudioFile } from "../api/client";
import { ChevronDown, ChevronRight, Star, Video, FileAudio } from "lucide-react";

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
              <StarRating value={(af as Record<string, unknown>)[key] as number | null}
                onChange={(r) => mutation.mutate({ [key]: r })} size={12} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RecordingCard({ af }: { af: AudioFile }) {
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
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {af.start_time && af.end_time ? `${af.start_time} - ${af.end_time}` : ""}
        </span>
      </div>
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
      <button onClick={() => setExpanded(!expanded)} className="w-full flex items-center justify-between p-5 text-left">
        <div className="flex items-center gap-3">
          {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
          <div>
            <div className="font-semibold">{session.date}</div>
            <div className="text-xs" style={{ color: "var(--text-muted)" }}>{session.take_count} recordings</div>
          </div>
        </div>
      </button>
      {expanded && detail && (
        <div className="px-5 pb-5 space-y-3">
          {detail.audio_files.map((af) => <RecordingCard key={af.id} af={af} />)}
        </div>
      )}
    </div>
  );
}

function BestTakes() {
  const [dimension, setDimension] = useState("overall");
  const { data: takes = [], isLoading } = useQuery({
    queryKey: ["best-takes", dimension],
    queryFn: () => api.takes.best(1, dimension),
  });

  return (
    <div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {RATING_DIMENSIONS.map(({ key, label }) => {
          const dim = key.replace("rating_", "");
          return (
            <button key={dim} onClick={() => setDimension(dim)}
              className="px-3 py-1 rounded-full text-sm"
              style={{
                background: dimension === dim ? "var(--accent)" : "var(--bg-card)",
                color: dimension === dim ? "#fff" : "var(--text-muted)",
              }}>
              {label}
            </button>
          );
        })}
      </div>
      {isLoading && <div style={{ color: "var(--text-muted)" }}>Loading...</div>}
      {!isLoading && takes.length === 0 && (
        <div className="text-center py-12 rounded-xl border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <Star size={32} className="mx-auto mb-3" style={{ color: "var(--text-muted)" }} />
          <p className="font-medium">No rated takes yet</p>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Rate takes in a session to see them here</p>
        </div>
      )}
      <div className="space-y-3">
        {takes.map((t) => (
          <div key={t.id} className="flex items-center gap-4">
            <span className="text-sm w-24 flex-shrink-0" style={{ color: "var(--text-muted)" }}>{t.session_date}</span>
            <div className="flex-1"><TakeCard take={t} /></div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Sessions() {
  const [tab, setTab] = useState<"sessions" | "best">("sessions");
  const { data: sessions = [], isLoading } = useQuery({
    queryKey: ["sessions"],
    queryFn: api.sessions.list,
  });

  if (isLoading) return <div style={{ color: "var(--text-muted)" }}>Loading...</div>;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Practice Sessions</h2>
      <div className="flex gap-1 mb-6 p-1 rounded-lg w-fit" style={{ background: "var(--bg-card)" }}>
        <button onClick={() => setTab("sessions")}
          className="px-4 py-2 rounded-md text-sm font-medium"
          style={{ background: tab === "sessions" ? "var(--bg-hover)" : "transparent", color: tab === "sessions" ? "var(--text)" : "var(--text-muted)" }}>
          All Sessions ({sessions.length})
        </button>
        <button onClick={() => setTab("best")}
          className="px-4 py-2 rounded-md text-sm font-medium"
          style={{ background: tab === "best" ? "var(--bg-hover)" : "transparent", color: tab === "best" ? "var(--text)" : "var(--text-muted)" }}>
          Best Takes
        </button>
      </div>
      {tab === "sessions" && (
        <div className="space-y-3">
          {sessions.map((s) => <SessionCard key={s.id} session={s} />)}
        </div>
      )}
      {tab === "best" && <BestTakes />}
    </div>
  );
}
