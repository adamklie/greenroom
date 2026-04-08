import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type ContentPost, type Song } from "../api/client";
import { Plus, Music2, Check } from "lucide-react";

const PLATFORM_ICONS: Record<string, React.ElementType> = {
  instagram: Music2,
  youtube: Music2,
  tiktok: Music2,
};

const STATUS_STYLES: Record<string, { bg: string; color: string }> = {
  planned: { bg: "var(--bg-hover)", color: "var(--text-muted)" },
  ready: { bg: "rgba(234, 179, 8, 0.15)", color: "var(--yellow)" },
  posted: { bg: "rgba(34, 197, 94, 0.15)", color: "var(--green)" },
};

function PostCard({ post }: { post: ContentPost }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.content.update(post.id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["content"] }),
  });

  const PlatformIcon = PLATFORM_ICONS[post.platform || ""] || Music2;
  const statusStyle = STATUS_STYLES[post.status] || STATUS_STYLES.planned;

  const cycleStatus = () => {
    const order = ["planned", "ready", "posted"];
    const next = order[(order.indexOf(post.status) + 1) % order.length];
    mutation.mutate({ status: next });
  };

  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <PlatformIcon size={18} style={{ color: "var(--accent)" }} />
          <h4 className="font-medium">{post.title}</h4>
        </div>
        <button
          onClick={cycleStatus}
          className="px-2 py-0.5 rounded-full text-xs font-medium capitalize cursor-pointer"
          style={{ background: statusStyle.bg, color: statusStyle.color }}
        >
          {post.status === "posted" && <Check size={12} className="inline mr-1" />}
          {post.status}
        </button>
      </div>
      {post.song_title && (
        <p className="text-sm mb-1" style={{ color: "var(--text-muted)" }}>
          Song: {post.song_title}
        </p>
      )}
      {post.scheduled_date && (
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Scheduled: {post.scheduled_date}
        </p>
      )}
      {post.caption && (
        <p className="text-sm mt-2 italic" style={{ color: "var(--text-muted)" }}>
          "{post.caption}"
        </p>
      )}
    </div>
  );
}

function CreatePostForm({ songs, onClose }: { songs: Song[]; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [songId, setSongId] = useState<number | "">("");
  const [platform, setPlatform] = useState("instagram");
  const [scheduledDate, setScheduledDate] = useState("");
  const [caption, setCaption] = useState("");

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.content.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["content"] });
      onClose();
    },
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      title,
      song_id: songId || null,
      platform,
      scheduled_date: scheduledDate || null,
      caption: caption || null,
      post_type: "reel",
    });
  };

  const inputStyle = {
    borderColor: "var(--border)",
    color: "var(--text)",
    background: "var(--bg)",
  };

  return (
    <form onSubmit={submit} className="rounded-xl p-5 border mb-4" style={{ background: "var(--bg-card)", borderColor: "var(--accent)" }}>
      <h3 className="font-semibold mb-4">New Post</h3>
      <div className="space-y-3">
        <input
          placeholder="Post title..."
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
          style={inputStyle}
        />
        <div className="flex gap-3">
          <select value={platform} onChange={(e) => setPlatform(e.target.value)}
            className="px-3 py-2 rounded-lg border text-sm outline-none flex-1" style={inputStyle}>
            <option value="instagram">Instagram</option>
            <option value="tiktok">TikTok</option>
            <option value="youtube">YouTube</option>
          </select>
          <input type="date" value={scheduledDate} onChange={(e) => setScheduledDate(e.target.value)}
            className="px-3 py-2 rounded-lg border text-sm outline-none flex-1" style={inputStyle} />
        </div>
        <select value={songId} onChange={(e) => setSongId(e.target.value ? Number(e.target.value) : "")}
          className="w-full px-3 py-2 rounded-lg border text-sm outline-none" style={inputStyle}>
          <option value="">No song linked</option>
          {songs.map((s) => (
            <option key={s.id} value={s.id}>{s.title}{s.artist ? ` — ${s.artist}` : ""}</option>
          ))}
        </select>
        <textarea
          placeholder="Caption..."
          value={caption}
          onChange={(e) => setCaption(e.target.value)}
          rows={2}
          className="w-full px-3 py-2 rounded-lg border text-sm outline-none resize-none"
          style={inputStyle}
        />
        <div className="flex gap-2">
          <button type="submit"
            className="px-4 py-2 rounded-lg text-sm font-medium text-white"
            style={{ background: "var(--accent)" }}>
            Create
          </button>
          <button type="button" onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm border"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
            Cancel
          </button>
        </div>
      </div>
    </form>
  );
}

export default function ContentPlanner() {
  const [showCreate, setShowCreate] = useState(false);

  const { data: posts = [], isLoading } = useQuery({
    queryKey: ["content"],
    queryFn: api.content.list,
  });

  const { data: songs = [] } = useQuery({
    queryKey: ["repertoire"],
    queryFn: () => api.repertoire.list(),
  });

  if (isLoading) return <div style={{ color: "var(--text-muted)" }}>Loading...</div>;

  const planned = posts.filter((p) => p.status === "planned");
  const ready = posts.filter((p) => p.status === "ready");
  const posted = posts.filter((p) => p.status === "posted");

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Content Planner</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white"
          style={{ background: "var(--accent)" }}
        >
          <Plus size={16} /> New Post
        </button>
      </div>

      {showCreate && <CreatePostForm songs={songs} onClose={() => setShowCreate(false)} />}

      {posts.length === 0 && !showCreate && (
        <div className="text-center py-16 rounded-xl border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <Share2Icon />
          <p className="mt-4 font-medium">No posts planned yet</p>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Click "New Post" to plan your first social media content
          </p>
        </div>
      )}

      {posts.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Column title="Planned" count={planned.length} posts={planned} />
          <Column title="Ready" count={ready.length} posts={ready} />
          <Column title="Posted" count={posted.length} posts={posted} />
        </div>
      )}
    </div>
  );
}

function Column({ title, count, posts }: { title: string; count: number; posts: ContentPost[] }) {
  return (
    <div>
      <h3 className="font-semibold mb-3 flex items-center gap-2">
        {title}
        <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "var(--bg-hover)", color: "var(--text-muted)" }}>
          {count}
        </span>
      </h3>
      <div className="space-y-3">
        {posts.map((p) => <PostCard key={p.id} post={p} />)}
      </div>
    </div>
  );
}

function Share2Icon() {
  return (
    <div className="mx-auto w-12 h-12 rounded-full flex items-center justify-center" style={{ background: "var(--bg-hover)" }}>
      <Music2 size={24} style={{ color: "var(--text-muted)" }} />
    </div>
  );
}
