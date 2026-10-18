import { useState } from "react";
import { Plus, X } from "lucide-react";
import type { Link, LinkKind } from "../api/client";
import { LINK_KINDS, guessKind } from "../lib/links";

const inputStyle = { borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" };

/** Controlled editor for a list of {kind, label, url} links. */
export default function LinksEditor({ value, onChange }: { value: Link[]; onChange: (links: Link[]) => void }) {
  const [newUrl, setNewUrl] = useState("");

  const update = (idx: number, patch: Partial<Link>) =>
    onChange(value.map((l, i) => (i === idx ? { ...l, ...patch } : l)));

  const add = () => {
    const url = newUrl.trim();
    if (!url) return;
    onChange([...value, { kind: guessKind(url), label: null, url }]);
    setNewUrl("");
  };

  return (
    <div className="space-y-1.5">
      {value.map((link, idx) => (
        <div key={idx} className="flex gap-1.5 items-center">
          <select value={link.kind} onChange={(e) => update(idx, { kind: e.target.value as LinkKind })}
            className="px-1.5 py-1 rounded border text-xs outline-none" style={inputStyle}>
            {LINK_KINDS.map((k) => <option key={k.kind} value={k.kind}>{k.label}</option>)}
          </select>
          <input value={link.url} onChange={(e) => update(idx, { url: e.target.value })}
            className="flex-1 min-w-0 px-2 py-1 rounded border text-xs outline-none" style={inputStyle} />
          <button onClick={() => onChange(value.filter((_, i) => i !== idx))}
            className="p-1 rounded hover:bg-white/10" style={{ color: "var(--text-muted)" }}>
            <X size={12} />
          </button>
        </div>
      ))}
      <form onSubmit={(e) => { e.preventDefault(); add(); }} className="flex gap-1.5">
        <input value={newUrl} onChange={(e) => setNewUrl(e.target.value)} placeholder="Paste a tab, track, chart or Spotify URL"
          className="flex-1 min-w-0 px-2 py-1 rounded border text-xs outline-none" style={inputStyle} />
        <button type="submit" className="p-1 rounded border" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
          <Plus size={12} />
        </button>
      </form>
    </div>
  );
}
