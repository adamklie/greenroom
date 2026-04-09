import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { Music2, Download, Plus, TrendingUp, User, Disc3 } from "lucide-react";

export default function Discover() {
  const queryClient = useQueryClient();

  const { data: stats } = useQuery({
    queryKey: ["apple-music-stats"],
    queryFn: api.appleMusic.stats,
  });

  const importMut = useMutation({
    mutationFn: api.appleMusic.import,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["apple-music-stats"] });
      queryClient.invalidateQueries({ queryKey: ["apple-music-suggestions"] });
    },
  });

  const { data: suggestions = [] } = useQuery({
    queryKey: ["apple-music-suggestions"],
    queryFn: () => api.appleMusic.suggestions(30),
    enabled: stats?.imported === true,
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
      <h2 className="text-2xl font-bold mb-2">Discover</h2>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        Powered by your Apple Music listening history
      </p>

      {/* Import button */}
      {!stats?.imported && (
        <div className="rounded-xl p-8 border text-center mb-8" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <Music2 size={40} className="mx-auto mb-4" style={{ color: "var(--accent)" }} />
          <h3 className="text-lg font-semibold mb-2">Connect Apple Music</h3>
          <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
            Import your listening history to get personalized cover suggestions, artist insights, and genre analysis.
          </p>
          <button onClick={() => importMut.mutate()}
            disabled={importMut.isPending}
            className="px-6 py-3 rounded-lg text-sm font-medium text-white disabled:opacity-50"
            style={{ background: "var(--accent)" }}>
            <Download size={16} className="inline mr-2" />
            {importMut.isPending ? "Importing..." : "Import Listening History"}
          </button>
          {importMut.data && (
            <p className="text-sm mt-3" style={{ color: "var(--green)" }}>
              Imported {importMut.data.exported_from_music_app} tracks ({importMut.data.linked_to_songs} linked to your songs)
            </p>
          )}
        </div>
      )}

      {stats?.imported && (
        <>
          {/* Refresh button */}
          <div className="flex justify-end mb-4">
            <button onClick={() => importMut.mutate()}
              disabled={importMut.isPending}
              className="px-3 py-1.5 rounded text-sm border hover:opacity-80"
              style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
              {importMut.isPending ? "Syncing..." : "Refresh from Apple Music"}
            </button>
          </div>

          {/* Stats cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="rounded-xl p-4 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
              <div className="text-sm" style={{ color: "var(--text-muted)" }}>Tracks</div>
              <div className="text-2xl font-bold">{stats.total_tracks}</div>
            </div>
            <div className="rounded-xl p-4 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
              <div className="text-sm" style={{ color: "var(--text-muted)" }}>Total Plays</div>
              <div className="text-2xl font-bold">{stats.total_plays?.toLocaleString()}</div>
            </div>
            <div className="rounded-xl p-4 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
              <div className="text-sm" style={{ color: "var(--text-muted)" }}>Artists</div>
              <div className="text-2xl font-bold">{stats.top_artists?.length || 0}+</div>
            </div>
            <div className="rounded-xl p-4 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
              <div className="text-sm" style={{ color: "var(--text-muted)" }}>Genres</div>
              <div className="text-2xl font-bold">{stats.top_genres?.length || 0}</div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Top Artists */}
            <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <User size={18} style={{ color: "var(--accent)" }} />
                Top Artists
              </h3>
              <div className="space-y-2">
                {stats.top_artists?.map((a, i) => (
                  <div key={a.artist} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="w-5 text-right" style={{ color: "var(--text-muted)" }}>{i + 1}</span>
                      <span className="font-medium">{a.artist}</span>
                    </div>
                    <div className="flex items-center gap-3" style={{ color: "var(--text-muted)" }}>
                      <span>{a.tracks} tracks</span>
                      <span className="font-medium" style={{ color: "var(--accent)" }}>{a.plays} plays</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Top Genres */}
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
                        <span style={{ color: "var(--text-muted)" }}>{g.plays} plays</span>
                      </div>
                      <div className="h-2 rounded-full" style={{ background: "var(--bg-hover)" }}>
                        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: "var(--accent)" }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Cover Suggestions */}
          <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
            <h3 className="font-semibold mb-1 flex items-center gap-2">
              <TrendingUp size={18} style={{ color: "var(--green)" }} />
              Cover Suggestions
            </h3>
            <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
              Songs you listen to most that you haven't covered yet. Click + to add as a cover.
            </p>
            <div className="space-y-2">
              {suggestions.map((s) => (
                <div key={`${s.title}-${s.artist}`}
                  className="flex items-center justify-between p-3 rounded-lg"
                  style={{ background: "var(--bg)" }}>
                  <div>
                    <span className="font-medium text-sm">{s.title}</span>
                    <span className="text-sm ml-2" style={{ color: "var(--text-muted)" }}>— {s.artist}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>{s.genre}</span>
                    <span className="text-sm font-medium" style={{ color: "var(--accent)" }}>{s.play_count} plays</span>
                    <button onClick={() => addCoverMut.mutate({ title: s.title, artist: s.artist })}
                      className="p-1 rounded hover:bg-white/10" style={{ color: "var(--green)" }}>
                      <Plus size={16} />
                    </button>
                  </div>
                </div>
              ))}
              {suggestions.length === 0 && (
                <p className="text-sm text-center py-4" style={{ color: "var(--text-muted)" }}>
                  No suggestions — you've covered or cataloged most of your top-played songs!
                </p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
