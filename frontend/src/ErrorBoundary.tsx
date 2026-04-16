import { Component, type ReactNode } from "react";

type Props = { children: ReactNode };
type State = { error: Error | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack?: string }) {
    // Surface to console for quick copy; persist for the in-page panel
    // eslint-disable-next-line no-console
    console.error("Greenroom crashed:", error, info);
    try {
      sessionStorage.setItem(
        "greenroom:last-error",
        JSON.stringify({ message: error.message, stack: error.stack, componentStack: info.componentStack }),
      );
    } catch { /* ignore */ }
  }

  render() {
    if (!this.state.error) return this.props.children;
    const e = this.state.error;
    return (
      <div style={{
        maxWidth: 780, margin: "40px auto", fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
        padding: 20, border: "1px solid #d33", borderRadius: 8, background: "#fff7f7", color: "#222",
      }}>
        <h2 style={{ marginTop: 0, color: "#c00" }}>Greenroom hit an error</h2>
        <p><strong>{e.name}:</strong> {e.message}</p>
        <details style={{ marginTop: 12 }}>
          <summary style={{ cursor: "pointer" }}>Stack trace</summary>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: 12 }}>{e.stack}</pre>
        </details>
        <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
          <button onClick={() => location.reload()}
            style={{ padding: "6px 14px", border: "1px solid #888", borderRadius: 4, background: "#fff", cursor: "pointer" }}>
            Reload
          </button>
          <button onClick={() => this.setState({ error: null })}
            style={{ padding: "6px 14px", border: "1px solid #888", borderRadius: 4, background: "#fff", cursor: "pointer" }}>
            Dismiss and try to continue
          </button>
        </div>
        <p style={{ fontSize: 12, marginTop: 16, color: "#555" }}>
          Check DevTools → Console for the full stack. If this keeps happening on startup, the dev server cache
          may be stale: stop the frontend and run <code>rm -rf node_modules/.vite</code>, then restart vite.
        </p>
      </div>
    );
  }
}
