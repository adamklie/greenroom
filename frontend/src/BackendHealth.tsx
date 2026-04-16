import { useEffect, useState } from "react";

/** A tiny banner that appears only when the backend is unreachable or slow. */
export function BackendHealthBanner() {
  const [state, setState] = useState<"ok" | "slow" | "down">("ok");
  const [lastError, setLastError] = useState<string>("");

  useEffect(() => {
    let cancelled = false;

    const probe = async () => {
      const ctrl = new AbortController();
      const slowTimer = setTimeout(() => !cancelled && setState("slow"), 3000);
      const hardTimer = setTimeout(() => ctrl.abort(), 8000);
      try {
        const r = await fetch("/api/dashboard", { signal: ctrl.signal });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        if (!cancelled) { setState("ok"); setLastError(""); }
      } catch (err) {
        if (!cancelled) {
          setState("down");
          setLastError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        clearTimeout(slowTimer);
        clearTimeout(hardTimer);
      }
    };

    probe();
    const id = setInterval(probe, 15_000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  if (state === "ok") return null;
  const color = state === "slow" ? "#b77" : "#c33";
  const label = state === "slow" ? "Backend is slow to respond…" : "Backend unreachable";
  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0, zIndex: 9999,
      padding: "6px 14px", background: color, color: "#fff", fontSize: 13,
      fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
    }}>
      {label}
      {lastError && <span style={{ opacity: 0.85 }}> — {lastError}</span>}
    </div>
  );
}
