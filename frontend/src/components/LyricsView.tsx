import { useCallback, useLayoutEffect, useRef, useState } from "react";

const CHORD = /^\(?[A-G][#b♯♭]?(m|maj|min|dim|aug|sus|add|M)?\d*((sus|add|maj|b|#)\d+)*(\/[A-G][#b♯♭]?)?\)?$/;
const CHORD_EXTRAS = /^(\||x\d+|n\.?c\.?|%|-+|\/)$/i;
const SECTION = /^\s*(\[.+\]|(intro|verse|pre-?chorus|chorus|bridge|solo|interlude|outro|tag|coda)\b[^a-z]*\d*:?)\s*$/i;

function isChordLine(line: string) {
  const tokens = line.trim().split(/\s+/).filter(Boolean);
  return tokens.some((t) => CHORD.test(t)) && tokens.every((t) => CHORD.test(t) || CHORD_EXTRAS.test(t));
}

const MIN_FONT = 10;
const MAX_FONT = 64;
const GAP = 40;

/** Song lyrics for the player.
 *
 * - `fit`: shrink the text and flow it into up to 3 columns so the whole song
 *   fits the box without scrolling (falls back to scrolling if it can't).
 * - otherwise: one readable column at `fontSize`, scrollable.
 *
 * Pasted chord sheets (chord lines above lyric lines) switch to a monospaced,
 * non-wrapping layout so the chords stay over the right words. */
export default function LyricsView({ lyrics, fit, fontSize = 20 }: { lyrics: string; fit: boolean; fontSize?: number }) {
  const boxRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLDivElement>(null);
  const [layout, setLayout] = useState<{ cols: number; size: number; fits: boolean } | null>(null);

  const lines = lyrics.replace(/\r\n/g, "\n").split("\n");
  const chordSheet = lines.filter((l) => l.trim() && isChordLine(l)).length >= 2;

  const measure = useCallback(() => {
    const box = boxRef.current;
    const text = textRef.current;
    if (!fit || !box || !text || !box.clientHeight) return;
    const pad = getComputedStyle(box);
    const available = box.clientHeight - parseFloat(pad.paddingTop) - parseFloat(pad.paddingBottom);
    // Columns are balanced, so the text's height is the tallest column.
    const fitsAt = (cols: number, size: number) => {
      text.style.columnCount = String(cols);
      text.style.fontSize = `${size}px`;
      return text.scrollWidth <= text.clientWidth + 1 && text.scrollHeight <= available + 1;
    };
    // Largest font that fits for 1, 2 and 3 columns.
    const sizes: (number | null)[] = [1, 2, 3].map((cols) => {
      if (!fitsAt(cols, MIN_FONT)) return null;
      let lo = MIN_FONT;
      let hi = MAX_FONT + 1;
      while (hi - lo > 1) {
        const mid = Math.floor((lo + hi) / 2);
        if (fitsAt(cols, mid)) lo = mid;
        else hi = mid;
      }
      return lo;
    });
    const biggest = Math.max(...sizes.map((sz) => sz ?? 0));
    // Fewer columns read more naturally; only add one if the text gets clearly bigger.
    const cols = sizes.findIndex((sz) => sz != null && sz >= biggest * 0.85) + 1;
    const chosen = cols > 0 ? { cols, size: sizes[cols - 1]!, fits: true } : { cols: 1, size: 16, fits: false };
    // The probing above wrote styles straight to the DOM; put the chosen ones
    // back, since React won't rewrite a style whose value it thinks is unchanged.
    text.style.columnCount = String(chosen.cols);
    text.style.fontSize = `${chosen.size}px`;
    setLayout(chosen);
  }, [fit]);

  useLayoutEffect(() => {
    measure();
    const box = boxRef.current;
    if (!box) return;
    const ro = new ResizeObserver(() => measure());
    ro.observe(box);
    return () => ro.disconnect();
  }, [measure, lyrics, chordSheet]);

  // New song: start at the top.
  useLayoutEffect(() => {
    if (boxRef.current) boxRef.current.scrollTop = 0;
  }, [lyrics]);

  const fitted = fit && layout?.fits;
  const textStyle: React.CSSProperties = fit
    ? {
        columnCount: fitted ? layout!.cols : 1,
        columnGap: GAP,
        fontSize: fitted ? layout!.size : 16,
      }
    : { fontSize, maxWidth: chordSheet ? undefined : "48rem", margin: "0 auto" };

  const tooSmall = fit && (!layout?.fits || layout.size < 16);

  return (
    <div ref={boxRef} data-scroll className={`w-full h-full ${fitted ? "overflow-hidden" : "overflow-auto"} px-6 py-4`}>
      <div ref={textRef} style={{
        ...textStyle,
        lineHeight: 1.35,
        fontFamily: chordSheet ? "ui-monospace, SFMono-Regular, Menlo, monospace" : undefined,
        // When fitting, lines never wrap mid-phrase: the longest line sets the size.
        whiteSpace: chordSheet || fit ? "pre" : "pre-wrap",
      }}>
        {lines.map((line, i) => {
          if (!line.trim()) return <div key={i} style={{ height: "0.6em" }} />;
          if (SECTION.test(line)) {
            return (
              <div key={i} className="font-bold uppercase tracking-wide"
                style={{ color: "var(--accent)", fontSize: "0.8em", marginTop: i ? "0.4em" : 0, breakAfter: "avoid" }}>
                {line.trim().replace(/^\[|\]$/g, "")}
              </div>
            );
          }
          if (chordSheet && isChordLine(line)) {
            return <div key={i} className="font-bold" style={{ color: "#f59e0b", breakAfter: "avoid" }}>{line}</div>;
          }
          return <div key={i} style={{ breakInside: "avoid" }}>{line}</div>;
        })}
      </div>
      {tooSmall && (
        <div className="fixed bottom-3 right-3 text-xs px-2 py-1 rounded" style={{ background: "#333", color: "#ccc" }}>
          Long song: try Scroll for bigger text
        </div>
      )}
    </div>
  );
}
