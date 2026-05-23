import { useState } from "react";
import { api } from "../api/client";

/**
 * Magic-link login page.
 *
 * Email → POST /api/auth/request → "check your email" message. The endpoint
 * always returns 200 (anti-enumeration), so the success state shown here
 * is the same whether or not the address is registered.
 */
export default function Login() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.auth.requestMagicLink(email.trim());
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send magic link");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex h-screen items-center justify-center"
      style={{ background: "var(--bg-base)" }}>
      <div className="w-full max-w-sm rounded-2xl border p-8"
        style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <h1 className="text-2xl font-bold mb-2" style={{ color: "var(--accent)" }}>
          Greenroom
        </h1>
        <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
          Sign in with a magic link.
        </p>

        {submitted ? (
          <div className="text-sm" style={{ color: "var(--text-muted)" }}>
            <p className="mb-2">If that email is registered, a magic link has been sent.</p>
            <p>Check your inbox (or the backend logs in dev) for the link.</p>
            <button
              className="mt-4 text-xs underline"
              onClick={() => { setSubmitted(false); setEmail(""); }}
              style={{ color: "var(--accent)" }}
            >
              Use a different email
            </button>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            <label className="block">
              <span className="text-xs uppercase tracking-wide"
                style={{ color: "var(--text-muted)" }}>
                Email
              </span>
              <input
                type="email"
                autoFocus
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
                style={{ background: "var(--bg-base)", borderColor: "var(--border)" }}
              />
            </label>
            {error && (
              <p className="text-xs" style={{ color: "tomato" }}>{error}</p>
            )}
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg px-3 py-2 text-sm font-medium disabled:opacity-50"
              style={{ background: "var(--accent)", color: "var(--bg-base)" }}
            >
              {submitting ? "Sending…" : "Send magic link"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
