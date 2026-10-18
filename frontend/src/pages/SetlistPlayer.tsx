import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link as RouterLink, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  ChevronLeft, ExternalLink, FileText, Maximize, Music, Pause, Play, SkipBack, SkipForward, Upload, X,
} from "lucide-react";
import { api, type SetlistItem } from "../api/client";
import ChartView from "../components/ChartView";
import LinkChips from "../components/LinkChips";
import LyricsView from "../components/LyricsView";
import { toDirectUrl } from "../lib/links";

type Mode = "practice" | "perform";
type View = "chart" | "lyrics";

const SPEEDS = [0.75, 0.9, 1];

const fmt = (s: number) =>
  Number.isFinite(s) ? `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}` : "0:00";

const linkOf = (item: SetlistItem, kind: string) => item.effective_links.find((l) => l.kind === kind);

const songPanelUrl = (item: SetlistItem) => `/${item.song_type || "cover"}s?song=${item.song_id}`;

/** Two-option switch (Chart | Lyrics, Fit | Scroll). */
function Segmented<T extends string>({ value, options, onChange, dark }: {
  value: T; options: { value: T; label: string }[]; onChange: (v: T) => void; dark?: boolean;
}) {
  return (
    <div className="flex rounded-lg border overflow-hidden text-xs" style={{ borderColor: dark ? "#333" : "var(--border)" }}>
      {options.map((o) => (
        <button key={o.value} onClick={(e) => { e.stopPropagation(); onChange(o.value); }}
          className="px-2.5 py-1"
          style={o.value === value
            ? { background: "var(--accent)", color: "#fff" }
            : { color: dark ? "#aaa" : "var(--text-muted)" }}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

const VIEW_OPTIONS: { value: View; label: string }[] = [{ value: "chart", label: "Chart" }, { value: "lyrics", label: "Lyrics" }];
const LAYOUT_OPTIONS: { value: "fit" | "scroll"; label: string }[] = [{ value: "fit", label: "Fit" }, { value: "scroll", label: "Scroll" }];

/** Keeps a tablet's screen on while performing. */
function useWakeLock(active: boolean) {
  useEffect(() => {
    if (!active || !("wakeLock" in navigator)) return;
    let lock: WakeLockSentinel | null = null;
    const acquire = () => {
      navigator.wakeLock.request("screen").then((l) => { lock = l; }).catch(() => {});
    };
    const onVisible = () => document.visibilityState === "visible" && acquire();
    acquire();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      document.removeEventListener("visibilitychange", onVisible);
      lock?.release().catch(() => {});
    };
  }, [active]);
}

function UploadChartButton({ songId, setlistId }: { songId: number; setlistId: number }) {
  const queryClient = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const upload = useMutation({
    mutationFn: (file: File) => api.charts.upload(songId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["setlist", setlistId] });
      queryClient.invalidateQueries({ queryKey: ["setlists"] });
    },
  });
  return (
    <>
      <input ref={input} type="file" accept=".pdf,.png,.jpg,.jpeg,.webp" className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate(f); e.target.value = ""; }} />
      <button onClick={() => input.current?.click()} disabled={upload.isPending}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm border"
        style={{ borderColor: "var(--border)", color: "var(--text)" }}>
        <Upload size={14} /> {upload.isPending ? "Uploading…" : "Upload chart"}
      </button>
      {upload.isError && <span className="text-xs" style={{ color: "var(--red)" }}>Upload failed</span>}
    </>
  );
}

/** Placeholder when a song has no uploaded chart. */
function NoChart({ item, setlistId, dark }: { item: SetlistItem; setlistId: number; dark?: boolean }) {
  const chartLink = linkOf(item, "chart");
  return (
    <div className="h-full flex flex-col items-center justify-center gap-3 text-center p-6"
      style={{ color: dark ? "#aaa" : "var(--text-muted)" }}>
      <FileText size={40} />
      <p className="text-sm">No chart uploaded for this song.</p>
      <div className="flex flex-wrap gap-2 justify-center">
        {chartLink && (
          <a href={chartLink.url} target="_blank" rel="noreferrer"
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm border"
            style={{ borderColor: "var(--border)", color: dark ? "#fff" : "var(--text)" }}>
            <ExternalLink size={14} /> Open linked chart
          </a>
        )}
        <UploadChartButton songId={item.song_id} setlistId={setlistId} />
      </div>
    </div>
  );
}

export default function SetlistPlayer() {
  const { id } = useParams();
  const setlistId = Number(id);
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const mode: Mode = params.get("mode") === "perform" ? "perform" : "practice";
  const index = Math.max(0, parseInt(params.get("i") || "0") || 0);
  // Chart vs lyrics, and (on stage) fit-to-screen vs scroll, persist across songs.
  const view: View = params.get("view") === "lyrics" ? "lyrics" : "chart";
  const scrollMode = params.get("layout") === "scroll";
  const setParam = useCallback((key: string, value: string) => {
    setParams((p) => { p.set(key, value); return p; }, { replace: true });
  }, [setParams]);
  const mainRef = useRef<HTMLDivElement>(null);

  const { data: setlist, isLoading } = useQuery({
    queryKey: ["setlist", setlistId],
    queryFn: () => api.setlists.get(setlistId),
  });
  const items = setlist?.items ?? [];
  const item: SetlistItem | undefined = items[Math.min(index, items.length - 1)];

  const [chartIdx, setChartIdx] = useState(0);
  const [page, setPage] = useState(1);
  const [pageCount, setPageCount] = useState(1);

  // --- backing track ---
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [rate, setRate] = useState(1);
  const [autoAdvance, setAutoAdvance] = useState(true);
  const playOnLoad = useRef(false);
  const track = item ? linkOf(item, "track") : undefined;
  const trackUrl = track ? toDirectUrl(track.url) : null;

  const goTo = useCallback((n: number, nextMode: Mode = mode) => {
    if (n < 0 || n >= items.length) return;
    if (n !== index) {
      playOnLoad.current = playOnLoad.current || (!!audioRef.current && !audioRef.current.paused);
    }
    setParams((p) => { p.set("i", String(n)); p.set("mode", nextMode); return p; }, { replace: true });
    setChartIdx(0);
    setPage(1);
  }, [items.length, index, mode, setParams]);

  // On stage, "next" first scrolls down a screen if there's more below, then
  // turns the chart's page, and only then moves to the next song.
  const scroller = () => mainRef.current?.querySelector<HTMLElement>("[data-scroll]") ?? null;
  const pagedChart = view === "chart" && !scrollMode;

  const next = useCallback(() => {
    if (mode === "perform") {
      const el = scroller();
      if (el && el.scrollTop + el.clientHeight < el.scrollHeight - 4) {
        el.scrollBy({ top: el.clientHeight * 0.85, behavior: "smooth" });
        return;
      }
      if (pagedChart && page < pageCount) { setPage(page + 1); return; }
    }
    goTo(index + 1);
  }, [mode, pagedChart, page, pageCount, goTo, index]);

  const prev = useCallback(() => {
    if (mode === "perform") {
      const el = scroller();
      if (el && el.scrollTop > 4) {
        el.scrollBy({ top: -el.clientHeight * 0.85, behavior: "smooth" });
        return;
      }
      if (pagedChart && page > 1) { setPage(page - 1); return; }
    }
    goTo(index - 1);
  }, [mode, pagedChart, page, goTo, index]);

  const togglePlay = useCallback(() => {
    const a = audioRef.current;
    if (!a || !trackUrl) return;
    if (a.paused) a.play().catch(() => {});
    else a.pause();
  }, [trackUrl]);

  // New song: load its track, keep the chosen speed, keep playing if we were.
  useEffect(() => {
    const a = audioRef.current;
    if (!a) return;
    setTime(0);
    setDuration(0);
    if (!trackUrl) {
      a.removeAttribute("src");
      a.load();
      playOnLoad.current = false;
      return;
    }
    a.src = trackUrl;
    a.defaultPlaybackRate = rate;
    a.playbackRate = rate;
    if (playOnLoad.current) a.play().catch(() => {});
    playOnLoad.current = false;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trackUrl]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.defaultPlaybackRate = rate;
      audioRef.current.playbackRate = rate;
    }
  }, [rate]);

  // Keyboard: arrows / PageUp / PageDown move (page-turner pedals send these);
  // Space plays/pauses in Practice and turns the page in Perform.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
      if (e.key === "ArrowRight" || e.key === "PageDown") { e.preventDefault(); next(); }
      else if (e.key === "ArrowLeft" || e.key === "PageUp") { e.preventDefault(); prev(); }
      else if (e.key === " ") { e.preventDefault(); if (mode === "perform") next(); else togglePlay(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [next, prev, togglePlay, mode]);

  useWakeLock(mode === "perform");

  // Swipe left/right on touch screens.
  const touchX = useRef<number | null>(null);
  const onTouchStart = (e: React.TouchEvent) => { touchX.current = e.touches[0].clientX; };
  const onTouchEnd = (e: React.TouchEvent) => {
    if (touchX.current == null) return;
    const dx = e.changedTouches[0].clientX - touchX.current;
    touchX.current = null;
    if (dx < -50) next();
    else if (dx > 50) prev();
  };

  const exit = () => {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    navigate(`/setlists/${setlistId}`);
  };

  if (isLoading) return <div style={{ color: "var(--text-muted)" }}>Loading…</div>;
  if (!setlist || !item) return <div style={{ color: "var(--text-muted)" }}>This setlist has no songs yet.</div>;

  const chart = item.charts[Math.min(chartIdx, item.charts.length - 1)];
  const upNext = items[index + 1];
  const meta = [item.song_artist, item.song_key && `Key ${item.song_key}`, item.song_tempo_bpm && `${item.song_tempo_bpm} BPM`]
    .filter(Boolean).join(" · ");

  const audio = (
    <audio ref={audioRef} preload="metadata"
      onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)}
      onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
      onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
      onEnded={() => { setPlaying(false); if (autoAdvance && index + 1 < items.length) { playOnLoad.current = true; goTo(index + 1); } }} />
  );

  // ---------------------------------------------------------------- Perform
  if (mode === "perform") {
    return (
      <div className="fixed inset-0 z-50 flex flex-col select-none" style={{ background: "#000", color: "#fff" }}>
        {audio}
        <div className="flex items-center gap-4 px-4 py-2 text-sm border-b" style={{ borderColor: "#222" }}>
          <span style={{ color: "#888" }}>{index + 1} / {items.length}{item.section ? ` · ${item.section}` : ""}</span>
          <span className="font-semibold text-base truncate">{item.song_title}</span>
          {item.notes && <span className="truncate" style={{ color: "#f59e0b" }}>{item.notes}</span>}
          <span className="ml-auto" />
          {pagedChart && chart && pageCount > 1 && <span style={{ color: "#888" }}>Page {page}/{pageCount}</span>}
          <Segmented dark value={view} options={VIEW_OPTIONS} onChange={(v) => setParam("view", v)} />
          <Segmented dark value={scrollMode ? "scroll" : "fit"} options={LAYOUT_OPTIONS} onChange={(v) => setParam("layout", v)} />
          {upNext && <span className="truncate hidden md:inline" style={{ color: "#888" }}>Next: {upNext.song_title}</span>}
          {trackUrl && (
            <button onClick={togglePlay} title="Backing track" className="p-1.5 rounded hover:bg-white/10">
              {playing ? <Pause size={16} /> : <Play size={16} />}
            </button>
          )}
          <button onClick={() => document.documentElement.requestFullscreen?.().catch(() => {})}
            title="Full screen" className="p-1.5 rounded hover:bg-white/10"><Maximize size={16} /></button>
          <button onClick={() => goTo(index, "practice")} className="px-2 py-1 rounded border text-xs"
            style={{ borderColor: "#333" }}>Practice</button>
          <button onClick={exit} title="Close" className="p-1.5 rounded hover:bg-white/10"><X size={16} /></button>
        </div>
        {/* Tap the left third to go back, the right third to go forward. */}
        <div ref={mainRef} className="flex-1 min-h-0 p-2" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}
          onClick={(e) => {
            const r = e.currentTarget.getBoundingClientRect();
            const x = (e.clientX - r.left) / r.width;
            if (x < 1 / 3) prev();
            else if (x > 2 / 3) next();
          }}>
          {view === "lyrics" && item.song_lyrics
            ? <LyricsView lyrics={item.song_lyrics} fit={!scrollMode} fontSize={32} />
            : view === "chart" && chart
              ? <ChartView chart={chart} page={scrollMode ? undefined : page} onPageCount={setPageCount} />
              : (
                <div className="h-full flex flex-col items-center justify-center text-center gap-2">
                  <p className="text-5xl font-bold">{item.song_title}</p>
                  <p className="text-xl" style={{ color: "#888" }}>{meta}</p>
                  {item.notes && <p className="text-2xl mt-4" style={{ color: "#f59e0b" }}>{item.notes}</p>}
                  <p className="text-sm mt-6" style={{ color: "#666" }}>No {view === "lyrics" ? "lyrics" : "chart"} for this song</p>
                </div>
              )}
        </div>
      </div>
    );
  }

  // --------------------------------------------------------------- Practice
  let n = 0;
  let lastSection: string | null | undefined;
  return (
    <div className="fixed inset-0 z-50 flex flex-col" style={{ background: "var(--bg)", color: "var(--text)" }}>
      {audio}
      {/* Top bar */}
      <div className="flex items-center gap-3 px-4 py-2 border-b" style={{ borderColor: "var(--border)" }}>
        <button onClick={exit} className="flex items-center gap-1 text-sm" style={{ color: "var(--text-muted)" }}>
          <ChevronLeft size={16} /> {setlist.name}
        </button>
        <span className="ml-auto" />
        <button onClick={() => goTo(index, "perform")}
          className="px-3 py-1.5 rounded-lg text-sm font-medium text-white" style={{ background: "var(--accent)" }}>
          Perform
        </button>
      </div>

      <div className="flex-1 min-h-0 flex">
        {/* Now playing: song header + chart */}
        <div className="flex-1 min-w-0 flex flex-col" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
          <div className="px-6 pt-5 pb-3">
            <div className="text-xs uppercase tracking-wide mb-1" style={{ color: "var(--accent)" }}>
              {index + 1} of {items.length}{item.section ? ` · ${item.section}` : ""}
            </div>
            <h2 className="text-3xl font-bold">{item.song_title}</h2>
            {meta && <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>{meta}</p>}
            {item.notes && (
              <p className="text-sm mt-2 px-3 py-1.5 rounded-lg inline-block" style={{ background: "#f59e0b22", color: "#f59e0b" }}>
                {item.notes}
              </p>
            )}
            <div className="flex items-center gap-3 mt-3 flex-wrap">
              <Segmented value={view} options={VIEW_OPTIONS} onChange={(v) => setParam("view", v)} />
              <LinkChips links={item.effective_links} />
              {view === "chart" && item.charts.length > 1 && item.charts.map((c, ci) => (
                <button key={c.id} onClick={() => setChartIdx(ci)}
                  className="px-2 py-0.5 rounded text-xs border"
                  style={{ borderColor: ci === chartIdx ? "var(--accent)" : "var(--border)", color: ci === chartIdx ? "var(--accent)" : "var(--text-muted)" }}>
                  {c.label || c.original_filename || `Chart ${ci + 1}`}
                </button>
              ))}
            </div>
          </div>
          <div className="flex-1 min-h-0 px-6 pb-4">
            <div className="h-full rounded-xl border overflow-hidden" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
              {view === "lyrics"
                ? item.song_lyrics
                  ? <LyricsView lyrics={item.song_lyrics} fit={false} />
                  : (
                    <div className="h-full flex flex-col items-center justify-center gap-2 text-sm" style={{ color: "var(--text-muted)" }}>
                      <p>No lyrics for this song yet.</p>
                      <RouterLink to={songPanelUrl(item)} style={{ color: "var(--accent)" }}>Add them in the song panel →</RouterLink>
                    </div>
                  )
                : chart ? <ChartView chart={chart} /> : <NoChart item={item} setlistId={setlistId} />}
            </div>
          </div>
        </div>

        {/* Queue */}
        <div className="w-80 flex-shrink-0 border-l overflow-y-auto hidden md:block" style={{ borderColor: "var(--border)" }}>
          <div className="px-4 py-3 text-xs font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Queue</div>
          {items.map((it, i) => {
            n += 1;
            const header = it.section !== lastSection && it.section;
            lastSection = it.section;
            const current = i === index;
            return (
              <div key={it.id}>
                {header && (
                  <div className="px-4 pt-3 pb-1 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--accent)" }}>
                    {it.section}
                  </div>
                )}
                <button onClick={() => goTo(i)}
                  className="w-full text-left px-4 py-2 flex items-center gap-3 text-sm"
                  style={{ background: current ? "var(--bg-hover)" : "transparent" }}>
                  <span className="w-5 text-right text-xs" style={{ color: current ? "var(--accent)" : "var(--text-muted)" }}>
                    {current && playing ? "♪" : n}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="block truncate" style={{ color: current ? "var(--accent)" : "var(--text)", fontWeight: current ? 600 : 400 }}>
                      {it.song_title}
                    </span>
                    <span className="block truncate text-xs" style={{ color: "var(--text-muted)" }}>{it.song_artist}</span>
                  </span>
                  <span className="flex gap-1" style={{ color: "var(--text-muted)" }}>
                    {it.charts.length > 0 && <span title="Chart uploaded"><FileText size={12} /></span>}
                    {linkOf(it, "track") && <span title="Backing track"><Music size={12} /></span>}
                  </span>
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Now-playing bar */}
      <div className="border-t px-4 py-3 flex items-center gap-4" style={{ borderColor: "var(--border)", background: "var(--bg-card)" }}>
        <div className="w-56 min-w-0 hidden sm:block">
          <div className="text-sm font-medium truncate">{item.song_title}</div>
          <div className="text-xs truncate" style={{ color: "var(--text-muted)" }}>
            {upNext ? `Up next: ${upNext.song_title}` : "Last song"}
          </div>
        </div>
        <div className="flex-1 flex flex-col items-center gap-1">
          <div className="flex items-center gap-4">
            <button onClick={prev} disabled={index === 0} className="p-1 disabled:opacity-30"><SkipBack size={18} /></button>
            <button onClick={togglePlay} disabled={!trackUrl}
              className="w-10 h-10 rounded-full flex items-center justify-center text-white disabled:opacity-30"
              style={{ background: "var(--accent)" }}>
              {playing ? <Pause size={18} /> : <Play size={18} className="ml-0.5" />}
            </button>
            <button onClick={next} disabled={index === items.length - 1} className="p-1 disabled:opacity-30"><SkipForward size={18} /></button>
          </div>
          {trackUrl ? (
            <div className="w-full max-w-xl flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
              <span className="w-10 text-right">{fmt(time)}</span>
              <input type="range" min={0} max={duration || 0} step={0.1} value={time}
                onChange={(e) => { if (audioRef.current) audioRef.current.currentTime = Number(e.target.value); }}
                className="flex-1" style={{ accentColor: "var(--accent)" }} />
              <span className="w-10">{fmt(duration)}</span>
            </div>
          ) : (
            <div className="text-xs" style={{ color: "var(--text-muted)" }}>No backing track for this song</div>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs" style={{ color: "var(--text-muted)" }}>
          <select value={rate} onChange={(e) => setRate(Number(e.target.value))} title="Playback speed"
            className="px-1.5 py-1 rounded border outline-none"
            style={{ borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" }}>
            {SPEEDS.map((s) => <option key={s} value={s}>{s}×</option>)}
          </select>
          <label className="flex items-center gap-1.5 cursor-pointer" title="Start the next song's track when this one ends">
            <input type="checkbox" checked={autoAdvance} onChange={(e) => setAutoAdvance(e.target.checked)}
              style={{ accentColor: "var(--accent)" }} />
            Auto-advance
          </label>
        </div>
      </div>
    </div>
  );
}
