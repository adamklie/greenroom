import type { Link } from "../api/client";
import { kindLabel } from "../lib/links";

const KIND_COLORS: Record<string, string> = {
  tab: "var(--accent)",
  track: "#f59e0b",
  chart: "#60a5fa",
  listen: "#1db954",
  other: "var(--text-muted)",
};

/** Compact row of external links (tab / track / chart / listen). */
export default function LinkChips({ links }: { links: Link[] }) {
  if (links.length === 0) return <span className="text-xs" style={{ color: "var(--text-muted)" }}>—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {links.map((link, i) => (
        <a key={`${link.kind}-${i}`} href={link.url} target="_blank" rel="noreferrer"
          title={link.label || link.url}
          onClick={(e) => e.stopPropagation()}
          className="px-2 py-0.5 rounded-full text-xs border hover:opacity-80 whitespace-nowrap"
          style={{ borderColor: KIND_COLORS[link.kind], color: KIND_COLORS[link.kind] }}>
          {kindLabel(link.kind)}
        </a>
      ))}
    </div>
  );
}
