import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Upload, X } from "lucide-react";
import { api, type Setlist } from "../api/client";

interface Row {
  file: File;
  songId: number | null; // null = skip
  status: "pending" | "uploading" | "done" | "error";
}

const compact = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, "");

/** Strip gig prefixes like "GICC1018-02-" or "02 - " from a chart filename. */
function filenameTitle(name: string) {
  return name
    .replace(/\.[^.]+$/, "")
    .replace(/^[a-z]*\d+[-_ ]+\d+[-_ ]+/i, "")
    .replace(/^\d+[\s._-]+/, "");
}

/** Exact match on the compacted title, else the longest title the filename contains. */
function matchSong(fileName: string, songs: { id: number; title: string }[]): number | null {
  const stem = compact(filenameTitle(fileName));
  const exact = songs.find((s) => compact(s.title) === stem);
  if (exact) return exact.id;
  const contained = songs
    .filter((s) => compact(s.title).length >= 3 && compact(fileName).includes(compact(s.title)))
    .sort((a, b) => b.title.length - a.title.length);
  return contained[0]?.id ?? null;
}

/** Pick a folder's worth of chart files, match them to the setlist's songs by
 * filename, confirm, then upload each to its song. */
export default function BulkChartUpload({ setlist, onClose }: { setlist: Setlist; onClose: () => void }) {
  const queryClient = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [running, setRunning] = useState(false);

  const songs = Array.from(
    new Map(setlist.items.map((i) => [i.song_id, { id: i.song_id, title: i.song_title || "", charts: i.charts.length }])).values(),
  );

  const pick = (files: FileList | null) => {
    if (!files) return;
    setRows(Array.from(files)
      .filter((f) => /\.(pdf|png|jpe?g|webp)$/i.test(f.name))
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((file) => ({ file, songId: matchSong(file.name, songs), status: "pending" })));
  };

  const uploadAll = async () => {
    setRunning(true);
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      if (row.songId == null || row.status === "done") continue;
      setRows((r) => r.map((x, j) => (j === i ? { ...x, status: "uploading" } : x)));
      try {
        await api.charts.upload(row.songId, row.file);
        setRows((r) => r.map((x, j) => (j === i ? { ...x, status: "done" } : x)));
      } catch {
        setRows((r) => r.map((x, j) => (j === i ? { ...x, status: "error" } : x)));
      }
    }
    setRunning(false);
    queryClient.invalidateQueries({ queryKey: ["setlists"] });
    queryClient.invalidateQueries({ queryKey: ["setlist", setlist.id] });
  };

  const toUpload = rows.filter((r) => r.songId != null && r.status !== "done").length;
  const inputStyle = { borderColor: "var(--border)", color: "var(--text)", background: "var(--bg)" };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.6)" }}>
      <div className="w-full max-w-3xl max-h-[85vh] flex flex-col rounded-xl border"
        style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <div className="flex items-center justify-between px-5 py-3 border-b" style={{ borderColor: "var(--border)" }}>
          <h3 className="font-semibold">Upload charts</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-white/10"><X size={18} /></button>
        </div>

        <div className="p-5 overflow-y-auto flex-1">
          <p className="text-sm mb-3" style={{ color: "var(--text-muted)" }}>
            Pick chart files (PDF or image). Each is matched to a song in this setlist by filename; check the
            matches, then upload. Charts attach to the song, so later setlists reuse them.
          </p>
          <input ref={input} type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.webp" className="hidden"
            onChange={(e) => { pick(e.target.files); e.target.value = ""; }} />
          <button onClick={() => input.current?.click()} disabled={running}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm border mb-4"
            style={{ borderColor: "var(--border)", color: "var(--text)" }}>
            <Upload size={16} /> Choose files
          </button>

          {rows.length > 0 && (
            <table className="w-full text-sm">
              <thead style={{ color: "var(--text-muted)" }}>
                <tr>
                  <th className="text-left text-xs font-medium uppercase tracking-wide py-2">File</th>
                  <th className="text-left text-xs font-medium uppercase tracking-wide py-2">Song</th>
                  <th className="w-20" />
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => {
                  const existing = songs.find((s) => s.id === row.songId)?.charts ?? 0;
                  return (
                    <tr key={row.file.name + i} className="border-t" style={{ borderColor: "var(--border)" }}>
                      <td className="py-2 pr-3 truncate max-w-xs">{row.file.name}</td>
                      <td className="py-2 pr-3">
                        <select value={row.songId ?? ""} disabled={running || row.status === "done"}
                          onChange={(e) => {
                            const v = e.target.value ? Number(e.target.value) : null;
                            setRows((r) => r.map((x, j) => (j === i ? { ...x, songId: v } : x)));
                          }}
                          className="w-full px-2 py-1 rounded border text-sm outline-none" style={inputStyle}>
                          <option value="">— skip —</option>
                          {songs.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
                        </select>
                        {existing > 0 && row.status === "pending" && (
                          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                            already has {existing} chart{existing > 1 ? "s" : ""}
                          </span>
                        )}
                      </td>
                      <td className="py-2 text-xs" style={{
                        color: row.status === "error" ? "var(--red)" : row.status === "done" ? "var(--accent)" : "var(--text-muted)",
                      }}>
                        {row.status === "uploading" ? "Uploading…" : row.status === "done" ? "Done" : row.status === "error" ? "Failed" : ""}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 px-5 py-3 border-t" style={{ borderColor: "var(--border)" }}>
          <span className="text-xs mr-auto" style={{ color: "var(--text-muted)" }}>
            {rows.length > 0 && `${rows.filter((r) => r.songId != null).length} of ${rows.length} files matched`}
          </span>
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-sm border"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
            {rows.length > 0 && toUpload === 0 ? "Close" : "Cancel"}
          </button>
          <button onClick={uploadAll} disabled={running || toUpload === 0}
            className="px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-40"
            style={{ background: "var(--accent)" }}>
            {running ? "Uploading…" : `Upload ${toUpload} chart${toUpload === 1 ? "" : "s"}`}
          </button>
        </div>
      </div>
    </div>
  );
}
