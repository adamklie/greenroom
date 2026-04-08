import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Session, type Take } from "../api/client";
import { ChevronDown, ChevronRight, Star, Video } from "lucide-react";

function StarRating({ rating, onChange }: { rating: number | null; onChange: (r: number) => void }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} onClick={() => onChange(n)} className="p-0">
          <Star
            size={16}
            fill={rating && n <= rating ? "var(--yellow)" : "none"}
            style={{ color: rating && n <= rating ? "var(--yellow)" : "var(--text-muted)" }}
          />
        </button>
      ))}
    </div>
  );
}

function TakeCard({ take }: { take: Take }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ id, rating }: { id: number; rating: number }) =>
      api.takes.update(id, { rating }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["session"] }),
  });

  return (
    <div className="rounded-lg p-4 border" style={{ background: "var(--bg)", borderColor: "var(--border)" }}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{take.song_title || take.clip_name}</span>
          {take.video_path && <Video size={14} style={{ color: "var(--text-muted)" }} />}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            {take.start_time} - {take.end_time}
          </span>
          <StarRating
            rating={take.rating}
            onChange={(r) => mutation.mutate({ id: take.id, rating: r })}
          />
        </div>
      </div>
      {take.audio_path && (
        <audio controls className="w-full h-8" style={{ filter: "invert(1) hue-rotate(180deg)" }}>
          <source src={api.media.takeAudioUrl(take.id)} />
        </audio>
      )}
      {!take.audio_path && (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          No audio export — video only
        </p>
      )}
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
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-5 text-left"
      >
        <div className="flex items-center gap-3">
          {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
          <div>
            <div className="font-semibold">{session.date}</div>
            <div className="text-xs" style={{ color: "var(--text-muted)" }}>
              {session.take_count} takes
            </div>
          </div>
        </div>
        <span className="text-xs px-2 py-1 rounded-full" style={{ background: "var(--bg-hover)", color: "var(--text-muted)" }}>
          {session.project === "ozone_destructors" ? "Ozone Destructors" : session.project}
        </span>
      </button>

      {expanded && detail && (
        <div className="px-5 pb-5 space-y-3">
          {detail.takes.map((take) => (
            <TakeCard key={take.id} take={take} />
          ))}
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
      <h2 className="text-2xl font-bold mb-6">Practice Sessions</h2>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        {sessions.length} sessions &middot; Click to expand and listen to takes
      </p>
      <div className="space-y-3">
        {sessions.map((s) => (
          <SessionCard key={s.id} session={s} />
        ))}
      </div>
    </div>
  );
}
