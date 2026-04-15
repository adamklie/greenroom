import { useEffect, useRef, useState } from "react";
import * as alphaTab from "@coderline/alphatab";
import { Play, Pause, Square, Minus, Plus } from "lucide-react";

// One-time AlphaTab Environment setup
let envInitialized = false;
function ensureAlphaTabEnv() {
  if (envInitialized) return;
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const Env = (alphaTab as any).Environment;
    if (Env?.initializeMain) {
      Env.initializeMain(
        (_settings: unknown, nameHint: string) => {
          console.log("[TabViewer] creating worker:", nameHint);
          return new Worker("/alphatab/alphaTab.worker.min.mjs", { type: "module", name: nameHint });
        },
        async (context: AudioContext) => {
          console.log("[TabViewer] loading audio worklet");
          await context.audioWorklet.addModule("/alphatab/alphaTab.worklet.min.mjs");
        },
      );
    }
    envInitialized = true;
    console.log("[TabViewer] AlphaTab environment initialized");
  } catch (e) {
    console.warn("[TabViewer] env init failed (non-fatal):", e);
  }
}

interface TabViewerProps {
  fileUrl: string;
  fullscreen?: boolean;
}

export function TabViewer({ fileUrl, fullscreen = false }: TabViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const apiRef = useRef<alphaTab.AlphaTabApi | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [tempo, setTempo] = useState(100);
  const [zoom, setZoom] = useState(1.0);
  const [status, setStatus] = useState<string>("initializing...");
  const [tracks, setTracks] = useState<{ name: string; index: number }[]>([]);
  const [currentTrack, setCurrentTrack] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    ensureAlphaTabEnv();
    const el = containerRef.current;
    // Clear any leftover content from a previous mount (StrictMode double-mount safety)
    el.innerHTML = "";
    console.log("[TabViewer] init with fileUrl:", fileUrl);

    let api: alphaTab.AlphaTabApi;
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      api = new alphaTab.AlphaTabApi(el, {
        core: {
          file: fileUrl,
          fontDirectory: "/alphatab/",
        },
        player: {
          enablePlayer: true,
          enableCursor: true,
          soundFont: "/alphatab/sonivox.sf2",
        },
      } as any);
      apiRef.current = api;
      console.log("[TabViewer] api created, has loadSoundFontFromUrl:",
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        typeof (api as any).loadSoundFontFromUrl,
        "has loadSoundFont:",
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        typeof (api as any).loadSoundFont);
      setStatus("api created, loading file...");
    } catch (e) {
      console.error("[TabViewer] construction failed:", e);
      setError(`Construction failed: ${e}`);
      return;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    api.scoreLoaded.on((score: any) => {
      console.log("[TabViewer] scoreLoaded", score);
      const trackList = score.tracks.map((t: { name: string }, i: number) => ({
        name: t.name || `Track ${i + 1}`,
        index: i,
      }));
      setTracks(trackList);
      setStatus(`loaded: ${score.title || "untitled"} (${trackList.length} tracks)`);

      // Load soundfont after score is loaded (player is initialized by then)
      fetch("/alphatab/sonivox.sf2")
        .then(r => {
          console.log("[TabViewer] soundfont fetch response:", r.status, r.headers.get("content-type"));
          return r.arrayBuffer();
        })
        .then(buf => {
          console.log("[TabViewer] soundfont bytes:", buf.byteLength);
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const result = (api as any).loadSoundFont(new Uint8Array(buf), false);
          console.log("[TabViewer] loadSoundFont returned:", result);
          // Generate MIDI from score so player can play
          try {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (api as any).loadMidiForScore?.();
            console.log("[TabViewer] loadMidiForScore called");
          } catch (e) {
            console.warn("[TabViewer] loadMidiForScore failed:", e);
          }
        })
        .catch(e => console.error("[TabViewer] soundfont fetch/load failed:", e));
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    api.renderStarted.on((isResize: any) => {
      console.log("[TabViewer] renderStarted", isResize);
      setStatus("rendering...");
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    api.renderFinished.on((arg: any) => {
      console.log("[TabViewer] renderFinished", arg);
      setStatus("rendered");
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (api as any).soundFontLoaded?.on?.(() => {
      console.log("[TabViewer] soundFontLoaded");
      setStatus(s => s + " + sound ready");
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (api as any).soundFontLoad?.on?.((args: any) => {
      const pct = args?.loaded && args?.total ? Math.round((args.loaded / args.total) * 100) : 0;
      console.log("[TabViewer] soundFontLoad progress", pct, "%");
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (api as any).playerReady?.on?.(() => {
      console.log("[TabViewer] playerReady");
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (api as any).error?.on?.((err: unknown) => {
      console.error("[TabViewer] error event:", err);
      setError(String(err));
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    api.playerStateChanged.on((args: any) => {
      setIsPlaying(args.state === 1); // 1 = Playing
    });

    return () => {
      try {
        api.destroy();
      } catch (e) {
        console.warn("[TabViewer] destroy error (non-fatal):", e);
      }
      // Clear container so next mount starts clean
      try { if (el) el.innerHTML = ""; } catch { /* noop */ }
      apiRef.current = null;
    };
  }, [fileUrl]);

  // Apply zoom
  useEffect(() => {
    if (apiRef.current) {
      apiRef.current.settings.display.scale = zoom;
      apiRef.current.updateSettings();
      apiRef.current.render();
    }
  }, [zoom]);

  // Apply tempo
  useEffect(() => {
    if (apiRef.current) apiRef.current.playbackSpeed = tempo / 100;
  }, [tempo]);

  // Render specific track
  useEffect(() => {
    if (apiRef.current && apiRef.current.score) {
      const track = apiRef.current.score.tracks[currentTrack];
      if (track) apiRef.current.renderTracks([track]);
    }
  }, [currentTrack]);

  const togglePlay = async () => {
    const api = apiRef.current;
    if (!api) { console.warn("[TabViewer] togglePlay: no api"); return; }
    // Resume AudioContext on user gesture (browser requirement)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const player = (api as any).player;
    const ctx = player?.output?.context || player?.context;
    if (ctx && ctx.state === "suspended") {
      try {
        await ctx.resume();
        console.log("[TabViewer] AudioContext resumed");
      } catch (e) { console.warn("[TabViewer] resume failed:", e); }
    }
    console.log("[TabViewer] togglePlay, state:", api.playerState, "isReady:", api.isReadyForPlayback);
    api.playPause();
  };
  const stop = () => apiRef.current?.stop();

  return (
    <div className="rounded-lg border overflow-hidden" style={{ borderColor: "var(--border)" }}>
      {/* Toolbar */}
      <div className="flex items-center gap-2 p-2 flex-wrap" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--border)" }}>
        <button onClick={togglePlay}
          className="p-1.5 rounded hover:bg-white/10"
          style={{ color: "var(--accent)" }}>
          {isPlaying ? <Pause size={14} /> : <Play size={14} />}
        </button>
        <button onClick={stop}
          className="p-1.5 rounded hover:bg-white/10"
          style={{ color: "var(--text-muted)" }}>
          <Square size={14} />
        </button>

        <div className="h-4 border-l" style={{ borderColor: "var(--border)" }} />

        <span className="text-xs" style={{ color: "var(--text-muted)" }}>Tempo: {tempo}%</span>
        <button onClick={() => setTempo(t => Math.max(25, t - 10))}
          className="p-1 rounded hover:bg-white/10" style={{ color: "var(--text-muted)" }}>
          <Minus size={12} />
        </button>
        <button onClick={() => setTempo(t => Math.min(200, t + 10))}
          className="p-1 rounded hover:bg-white/10" style={{ color: "var(--text-muted)" }}>
          <Plus size={12} />
        </button>

        <div className="h-4 border-l" style={{ borderColor: "var(--border)" }} />

        <span className="text-xs" style={{ color: "var(--text-muted)" }}>Zoom: {Math.round(zoom * 100)}%</span>
        <button onClick={() => setZoom(z => Math.max(0.5, z - 0.1))}
          className="p-1 rounded hover:bg-white/10" style={{ color: "var(--text-muted)" }}>
          <Minus size={12} />
        </button>
        <button onClick={() => setZoom(z => Math.min(2.0, z + 0.1))}
          className="p-1 rounded hover:bg-white/10" style={{ color: "var(--text-muted)" }}>
          <Plus size={12} />
        </button>

        {tracks.length > 1 && (
          <>
            <div className="h-4 border-l" style={{ borderColor: "var(--border)" }} />
            <select value={currentTrack} onChange={(e) => setCurrentTrack(Number(e.target.value))}
              className="px-2 py-0.5 rounded text-xs outline-none"
              style={{ background: "var(--bg)", color: "var(--text)", border: "1px solid var(--border)" }}>
              {tracks.map(t => (
                <option key={t.index} value={t.index}>{t.name}</option>
              ))}
            </select>
          </>
        )}

        <span className="text-xs ml-auto" style={{ color: "var(--text-muted)" }}>{status}</span>
      </div>

      {error && (
        <div className="p-3 text-xs" style={{ color: "var(--red, #f44)", background: "var(--bg)" }}>
          {error}
        </div>
      )}

      <div ref={containerRef}
        className="overflow-auto bg-white text-black"
        style={{ maxHeight: fullscreen ? "calc(100vh - 120px)" : 600, minHeight: 300 }}
      />
    </div>
  );
}
