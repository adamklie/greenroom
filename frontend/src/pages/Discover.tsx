import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { Music2, Plus, TrendingUp, User, Disc3, Link2 } from "lucide-react";

export default function Discover() {
  const queryClient = useQueryClient();
  const [includeAllGenres, setIncludeAllGenres] = useState(false);

  const { data: stats } = useQuery({
    queryKey: ["apple-music-stats", includeAllGenres],
    queryFn: () => api.appleMusic.stats(includeAllGenres),
  });

  const { data: suggestions = [] } = useQuery({
    queryKey: ["apple-music-suggestions", includeAllGenres],
    queryFn: () => api.appleMusic.suggestions(50, includeAllGenres),
    enabled: stats?.imported === true,
  });

  const linkMut = useMutation({
    mutationFn: api.appleMusic.linkSongs,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["apple-music-stats"] });
      queryClient.invalidateQueries({ queryKey: ["apple-music-suggestions"] });
      queryClient.invalidateQueries({ queryKey: ["songs"] });
    },
  });

  const addCoverMut = useMutation({
    mutationFn: (data: { title: string; artist: string }) =>
      api.songs.create({ title: data.title, artist: data.artist, type: "cover", project: "solo", status: "idea" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["apple-music-suggestions"] });
      queryClient.invalidateQueries({ queryKey: ["songs"] });
    },
  });

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold mb-1">Discover</h2>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Powered by your Apple Music listening history
          </p>
        </div>
        <div className="flex gap-2 items-center">
          <label className="flex items-center gap-2 text-sm" style={{ color: "var(--text-muted)" }}>
            <input type="checkbox" checked={includeAllGenres}
              onChange={(e) => setIncludeAllGenres(e.target.checked)} />
            Include classical/scores
          </label>
          <button onClick={() => linkMut.mutate()} disabled={linkMut.isPending}
            className="px-3 py-1.5 rounded text-sm border hover:opacity-80 disabled:opacity-50 flex items-center gap-1"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
            <Link2 size={14} />
            {linkMut.isPending ? "Linking…" : "Re-link Songs"}
          </button>
        </div>
      </div>

      {!stats?.imported && (
        <div className="rounded-xl p-8 border text-center mb-8" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <Music2 size={40} className="mx-auto mb-4" style={{ color: "var(--accent)" }} />
          <h3 className="text-lg font-semibold mb-2">No listening history yet</h3>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Request an Apple Media Services data export from privacy.apple.com, then run:
          </p>
          <code className="block text-xs mt-3 p-2 rounded" style={{ background: "var(--bg)" }}>
            python -m scripts.ingest_apple_dump /path/to/Apple_Media_Services.zip --wipe
          </code>
        </div>
      )}

      {stats?.imported && (
        <>
          {linkMut.data && (
            <div className="mb-4 text-sm p-3 rounded" style={{ background: "var(--bg-hover)" }}>
              Linked {linkMut.data.total_listening_rows_linked} listening rows to{" "}
              {stats.total_tracks ? stats.total_tracks - (linkMut.data.catalog_songs_with_no_link || 0) : "?"} catalog songs.{" "}
              {linkMut.data.catalog_songs_with_no_link} songs still unlinked.
            </div>
          )}

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard label="Unique Tracks" value={stats.total_tracks?.toLocaleString() ?? "0"} />
            <StatCard label="Total Plays" value={stats.total_plays?.toLocaleString() ?? "0"} />
            <StatCard label="Listen Hours" value={stats.total_listen_hours?.toLocaleString() ?? "0"} />
            <StatCard label="Artists" value={`${stats.top_artists?.length ?? 0}+`} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <User size={18} style={{ color: "var(--accent)" }} />
                Top Artists
              </h3>
              <div className="space-y-2">
                {stats.top_artists?.filter((a) => a.artist).map((a, i) => (
                  <div key={a.artist} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="w-5 text-right" style={{ color: "var(--text-muted)" }}>{i + 1}</span>
                      <span className="font-medium">{a.artist}</span>
                    </div>
                    <div className="flex items-center gap-3" style={{ color: "var(--text-muted)" }}>
                      <span>{a.tracks} tracks</span>
                      <span className="font-medium" style={{ color: "var(--accent)" }}>
                        {a.plays.toLocaleString()} plays
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <Disc3 size={18} style={{ color: "var(--blue)" }} />
                Top Genres
              </h3>
              <div className="space-y-2">
                {stats.top_genres?.map((g) => {
                  const maxPlays = stats.top_genres?.[0]?.plays || 1;
                  const pct = Math.round((g.plays / maxPlays) * 100);
                  return (
                    <div key={g.genre}>
                      <div className="flex justify-between text-sm mb-1">
                        <span>{g.genre}</span>
                        <span style={{ color: "var(--text-muted)" }}>{g.plays.toLocaleString()} plays</span>
                      </div>
                      <div className="h-2 rounded-full" style={{ background: "var(--bg-hover)" }}>
                        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: "var(--accent)" }} />
                      </div>
                    </div>
                  );
                })}
              </div>
              {stats.excluded_genres && stats.excluded_genres.length > 0 && (
                <p className="text-xs mt-3" style={{ color: "var(--text-muted)" }}>
                  Excluded: {stats.excluded_genres.join(", ")}
                </p>
              )}
            </div>
          </div>

          <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
            <h3 className="font-semibold mb-1 flex items-center gap-2">
              <TrendingUp size={18} style={{ color: "var(--green)" }} />
              Cover Suggestions
            </h3>
            <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
              Top-played tracks not yet linked to a song in your catalog. Click + to add as a cover.
            </p>
            <div className="space-y-2">
              {suggestions.map((s) => (
                <div key={`${s.title}-${s.artist}-${s.album ?? ""}`}
                  className="flex items-center justify-between p-3 rounded-lg"
                  style={{ background: "var(--bg)" }}>
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-sm truncate">{s.title}</div>
                    <div className="text-xs truncate" style={{ color: "var(--text-muted)" }}>
                      {s.artist || "—"}{s.album ? ` · ${s.album}` : ""}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 ml-4 flex-shrink-0">
                    {s.genre && <span className="text-xs" style={{ color: "var(--text-muted)" }}>{s.genre}</span>}
                    <span className="text-sm font-medium" style={{ color: "var(--accent)" }}>
                      {s.play_count.toLocaleString()} plays
                    </span>
                    <button onClick={() => addCoverMut.mutate({ title: s.title, artist: s.artist })}
                      disabled={!s.artist}
                      className="p-1 rounded hover:bg-white/10 disabled:opacity-30"
                      style={{ color: "var(--green)" }}
                      title={s.artist ? "Add as cover" : "Can't add (no artist)"}>
                      <Plus size={16} />
                    </button>
                  </div>
                </div>
              ))}
              {suggestions.length === 0 && (
                <p className="text-sm text-center py-4" style={{ color: "var(--text-muted)" }}>
                  No suggestions.
                </p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl p-4 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
      <div className="text-sm" style={{ color: "var(--text-muted)" }}>{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}
