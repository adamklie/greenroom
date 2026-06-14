/**
 * Greenroom icon set
 * ------------------
 * Drop-in, lucide-compatible icons in the Greenroom house style: emerald
 * linework drawn with `currentColor` (so each glyph follows your nav's
 * active/muted color, exactly like the lucide icons it replaces) plus a
 * single `--yellow` accent for the Greenroom pop.
 *
 * Colors come straight from your tokens in index.css:
 *   currentColor -> --accent (active) / --text-muted (inactive), set by NavLink
 *   accent       -> --yellow (#eab308 dark / #ca8a04 light)
 *
 * Usage (App.tsx navItems) — same `size` API as lucide:
 *   import { LibraryIcon } from "./components/GreenroomIcons";
 *   { to: "/library", icon: LibraryIcon, label: "Library" }
 *
 * See BRANDING.md for the full navItems swap and header replacement.
 */
import type { SVGProps, HTMLAttributes } from "react";

type IconProps = { size?: number } & SVGProps<SVGSVGElement>;

const Y = "var(--yellow, #eab308)";

const base = (size: number): SVGProps<SVGSVGElement> => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round",
  strokeLinejoin: "round",
});

/* ---- Content tabs ---------------------------------------------------- */

export function DashboardIcon({ size = 20, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <rect x="3.5" y="3.5" width="17" height="17" rx="3" />
      <line x1="11.25" y1="3.5" x2="11.25" y2="20.5" strokeWidth="1.4" />
      <line x1="11.25" y1="12" x2="20.5" y2="12" strokeWidth="1.4" />
      <rect x="6" y="6" width="3.6" height="3.6" rx="0.9" fill={Y} stroke="none" />
    </svg>
  );
}

export function ImportIcon({ size = 20, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M4.5 12.5 V18.5 A2 2 0 0 0 6.5 20.5 H17.5 A2 2 0 0 0 19.5 18.5 V12.5" />
      <line x1="12" y1="3.6" x2="12" y2="14.4" stroke={Y} strokeWidth="1.8" />
      <path d="M8 7.6 L12 3.6 L16 7.6" stroke={Y} strokeWidth="1.8" fill="none" />
    </svg>
  );
}

export function LibraryIcon({ size = 20, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M3 7.5 Q3 6 4.5 6 H9 L10.5 4.5 H19.5 Q21 4.5 21 6 V18 Q21 19.5 19.5 19.5 H4.5 Q3 19.5 3 18 Z" />
      <rect x="9" y="12" width="1.5" height="4.5" rx="0.7" fill={Y} stroke="none" />
      <rect x="11.75" y="10" width="1.5" height="6.5" rx="0.7" fill={Y} stroke="none" />
      <rect x="14.5" y="11.5" width="1.5" height="5" rx="0.7" fill={Y} stroke="none" />
    </svg>
  );
}

export function CoversIcon({ size = 20, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="3.6" strokeWidth="1.3" />
      <circle cx="12" cy="12" r="1.5" fill={Y} stroke="none" />
    </svg>
  );
}

export function OriginalsIcon({ size = 20, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M8.5 5 H15.5 L13 16 L12 19 L11 16 Z" />
      <line x1="12" y1="8" x2="12" y2="15" strokeWidth="1.3" />
      <circle cx="12" cy="10.5" r="1.1" fill={Y} stroke="none" />
    </svg>
  );
}

export function IdeasIcon({ size = 20, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M12 3.5 A6 6 0 0 1 15.4 14.4 C14.8 14.8 14.5 15.4 14.4 16.2 H9.6 C9.5 15.4 9.2 14.8 8.6 14.4 A6 6 0 0 1 12 3.5 Z" />
      <line x1="9.8" y1="18.2" x2="14.2" y2="18.2" />
      <line x1="10.6" y1="20.3" x2="13.4" y2="20.3" />
      <path d="M10.3 10.8 L12 8.3 L13.7 10.8" stroke={Y} strokeWidth="1.5" fill="none" />
    </svg>
  );
}

export function SetlistsIcon({ size = 20, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <path d="M9 4 Q12 2 15 4" />
      <rect x="4" y="6" width="16" height="13" rx="2.5" />
      <rect x="8.5" y="11.5" width="1.5" height="4.5" rx="0.7" fill={Y} stroke="none" />
      <rect x="11.25" y="9.5" width="1.5" height="6.5" rx="0.7" fill={Y} stroke="none" />
      <rect x="14" y="11" width="1.5" height="5" rx="0.7" fill={Y} stroke="none" />
    </svg>
  );
}

export function SessionsIcon({ size = 20, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <rect x="4" y="6" width="16" height="14" rx="2.5" />
      <line x1="8" y1="4" x2="8" y2="7.5" />
      <line x1="16" y1="4" x2="16" y2="7.5" />
      <line x1="4.5" y1="10.5" x2="19.5" y2="10.5" strokeWidth="1.3" />
      <rect x="7" y="13" width="3" height="3" rx="0.7" fill={Y} stroke="none" />
    </svg>
  );
}

export function ProcessIcon({ size = 20, ...p }: IconProps) {
  return (
    <svg {...base(size)} {...p}>
      <g fill="currentColor" stroke="none">
        <rect x="4.5" y="9" width="1.6" height="6" rx="0.8" />
        <rect x="7" y="5.5" width="1.6" height="13" rx="0.8" />
        <rect x="9.5" y="8" width="1.6" height="8" rx="0.8" />
        <rect x="14.5" y="6.5" width="1.6" height="11" rx="0.8" />
        <rect x="17" y="8.5" width="1.6" height="7" rx="0.8" />
        <rect x="19.5" y="10" width="1.6" height="4" rx="0.8" />
      </g>
      <line x1="12.5" y1="3.5" x2="12.5" y2="20.5" stroke={Y} strokeWidth="1.7" />
    </svg>
  );
}

/* ---- Brand mark + wordmark ------------------------------------------- */

/** Standalone waveform G — app icon, sidebar header, anywhere the mark stands alone. */
export function GreenroomMark({ size = 28, ...p }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" {...p}>
      <path d="M45 22 A17 17 0 1 0 45 42" stroke="currentColor" strokeWidth="4.8" strokeLinecap="round" />
      <path d="M45 42 L38 42" stroke="currentColor" strokeWidth="4.8" strokeLinecap="round" />
      <rect x="24" y="29" width="2.6" height="6.4" rx="1.3" fill={Y} />
      <rect x="29" y="25" width="2.6" height="14" rx="1.3" fill={Y} />
      <rect x="34" y="27" width="2.6" height="10" rx="1.3" fill={Y} />
    </svg>
  );
}

/**
 * Full logo lockup: the G doubles as the capital, so the wordmark reads
 * "G + reenroom" = Greenroom. Green parts inherit `color`; set it on the
 * wrapper. For your current all-green header use color: var(--accent);
 * for a two-tone treatment use color: var(--text).
 */
export function GreenroomLogo({
  size = 22,
  ...p
}: { size?: number } & HTMLAttributes<HTMLDivElement>) {
  return (
    <div style={{ display: "inline-flex", alignItems: "center", lineHeight: 1, color: "var(--accent)" }} {...p}>
      <svg
        width={Math.round(size * 0.92)}
        height={Math.round(size * 1.0)}
        viewBox="14 12 37 40"
        fill="none"
        style={{ display: "block" }}
        aria-hidden="true"
      >
        <path d="M45 22 A17 17 0 1 0 45 42" stroke="currentColor" strokeWidth="4.8" strokeLinecap="round" />
        <path d="M45 42 L38 42" stroke="currentColor" strokeWidth="4.8" strokeLinecap="round" />
        <rect x="24" y="29" width="2.6" height="6.4" rx="1.3" fill={Y} />
        <rect x="29" y="25" width="2.6" height="14" rx="1.3" fill={Y} />
        <rect x="34" y="27" width="2.6" height="10" rx="1.3" fill={Y} />
      </svg>
      <span style={{ marginLeft: 1, fontSize: size, fontWeight: 600, letterSpacing: "-0.02em" }}>
        reenroom
      </span>
    </div>
  );
}
