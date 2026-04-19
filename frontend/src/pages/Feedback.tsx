import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { MessageSquare, Bug, Lightbulb, HelpCircle, ExternalLink, Check, AlertCircle } from "lucide-react";

const CATEGORIES = [
  { value: "feedback", label: "Feedback", icon: MessageSquare, color: "var(--accent)" },
  { value: "bug", label: "Bug Report", icon: Bug, color: "var(--red)" },
  { value: "feature", label: "Feature Request", icon: Lightbulb, color: "var(--yellow)" },
  { value: "question", label: "Question", icon: HelpCircle, color: "var(--blue)" },
];

const inputStyle = { borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" };

export default function Feedback() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("feedback");
  const [priority, setPriority] = useState("normal");
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submitMut = useMutation({
    mutationFn: async () => {
      const r = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description, category, priority }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    },
    onMutate: () => { setError(null); setSubmitted(null); },
    onSuccess: (data) => {
      if (data.ok) {
        setSubmitted(data.url);
        setTitle("");
        setDescription("");
      } else {
        setError(data.error || "Failed to create issue");
      }
    },
    onError: (e: Error) => setError(e.message),
  });

  const { data: issuesData } = useQuery({
    queryKey: ["github-issues"],
    queryFn: () => fetch("/api/feedback/issues").then(r => r.json()),
  });

  const issues = issuesData?.issues || [];

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold mb-2">Feedback</h2>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        Submit feedback, bug reports, and feature requests — creates a GitHub issue automatically
      </p>

      {/* Submit form */}
      <div className="rounded-xl p-5 border mb-6" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        {/* Category picker */}
        <div className="flex gap-2 mb-4">
          {CATEGORIES.map(({ value, label, icon: Icon, color }) => (
            <button key={value} onClick={() => setCategory(value)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm border transition-colors"
              style={{
                borderColor: category === value ? color : "var(--border)",
                color: category === value ? color : "var(--text-muted)",
                background: category === value ? `${color}15` : "transparent",
              }}>
              <Icon size={16} /> {label}
            </button>
          ))}
        </div>

        <input value={title} onChange={(e) => setTitle(e.target.value)}
          placeholder="Title — brief summary of your feedback..."
          className="w-full px-3 py-2 rounded-lg border text-sm outline-none mb-3" style={inputStyle} />

        <textarea value={description} onChange={(e) => setDescription(e.target.value)}
          placeholder="Description — what happened, what you expected, steps to reproduce..."
          rows={5} className="w-full px-3 py-2 rounded-lg border text-sm outline-none resize-y mb-3" style={inputStyle} />

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>Priority:</span>
            {["low", "normal", "high"].map(p => (
              <button key={p} onClick={() => setPriority(p)}
                className="px-2 py-1 rounded text-xs capitalize"
                style={{
                  background: priority === p ? "var(--bg-hover)" : "transparent",
                  color: priority === p ? "var(--text)" : "var(--text-muted)",
                }}>
                {p}
              </button>
            ))}
          </div>
          <button onClick={() => submitMut.mutate()}
            disabled={!title.trim() || !description.trim() || submitMut.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50"
            style={{ background: "var(--accent)" }}>
            {submitMut.isPending ? "Submitting..." : "Submit to GitHub"}
          </button>
        </div>

        {submitted && (
          <div className="mt-3 flex items-center gap-2 text-sm" style={{ color: "var(--green)" }}>
            <Check size={16} />
            Issue created!
            <a href={submitted} target="_blank" rel="noopener noreferrer"
              className="underline flex items-center gap-1" style={{ color: "var(--accent)" }}>
              View on GitHub <ExternalLink size={12} />
            </a>
          </div>
        )}

        {error && (
          <div className="mt-3 flex items-start gap-2 text-sm" style={{ color: "var(--red)" }}>
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <span className="break-all">{error}</span>
          </div>
        )}
      </div>

      {/* Existing issues */}
      {issues.length > 0 && (
        <div className="rounded-xl p-5 border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <h3 className="font-semibold mb-3">Open Issues ({issues.length})</h3>
          <div className="space-y-2">
            {issues.map((issue: { number: number; title: string; url: string; labels: { name: string }[]; createdAt: string }) => (
              <a key={issue.number} href={issue.url} target="_blank" rel="noopener noreferrer"
                className="flex items-center justify-between p-3 rounded-lg text-sm hover:opacity-80"
                style={{ background: "var(--bg)" }}>
                <div className="flex items-center gap-2">
                  <span style={{ color: "var(--text-muted)" }}>#{issue.number}</span>
                  <span className="font-medium">{issue.title}</span>
                  {issue.labels?.map((l: { name: string }) => (
                    <span key={l.name} className="px-1.5 py-0.5 rounded text-xs"
                      style={{ background: "var(--bg-hover)", color: "var(--text-muted)" }}>
                      {l.name}
                    </span>
                  ))}
                </div>
                <ExternalLink size={12} style={{ color: "var(--text-muted)" }} />
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
