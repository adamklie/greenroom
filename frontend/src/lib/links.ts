import type { LinkKind } from "../api/client";

export const LINK_KINDS: { kind: LinkKind; label: string }[] = [
  { kind: "tab", label: "Tab" },
  { kind: "track", label: "Track" },
  { kind: "chart", label: "Chart" },
  { kind: "listen", label: "Listen" },
  { kind: "other", label: "Link" },
];

export const kindLabel = (kind: LinkKind) =>
  LINK_KINDS.find((k) => k.kind === kind)?.label ?? "Link";

/** Best guess at a link's kind from its URL (used when adding links by hand). */
export function guessKind(url: string): LinkKind {
  let host = "";
  let path = "";
  try {
    const u = new URL(url);
    host = u.hostname;
    path = decodeURIComponent(u.pathname).toLowerCase();
  } catch {
    return "other";
  }
  if (host.includes("ultimate-guitar") || host.includes("songsterr")) return "tab";
  if (host.includes("spotify") || host.includes("youtube") || host.includes("youtu.be")) return "listen";
  if (/\.(mp3|m4a|wav|aac|ogg)$/.test(path)) return "track";
  if (/\.(pdf|png|jpe?g)$/.test(path)) return "chart";
  return "other";
}

/** Dropbox share links (dl=0) open a preview page; raw=1 serves the file
 * itself so <audio>/<iframe> can use it. Other URLs pass through. */
export function toDirectUrl(url: string): string {
  try {
    const u = new URL(url);
    if (!u.hostname.endsWith("dropbox.com")) return url;
    u.searchParams.delete("dl");
    u.searchParams.set("raw", "1");
    return u.toString();
  } catch {
    return url;
  }
}
