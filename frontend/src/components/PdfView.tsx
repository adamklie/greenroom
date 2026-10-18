import { useEffect, useRef, useState } from "react";
import type { PDFDocumentProxy, RenderTask } from "pdfjs-dist";

// pdf.js is large; load it (and its worker) only when a PDF chart is opened.
let pdfjsPromise: Promise<typeof import("pdfjs-dist")> | null = null;
function loadPdfjs() {
  if (!pdfjsPromise) {
    pdfjsPromise = Promise.all([
      import("pdfjs-dist"),
      import("pdfjs-dist/build/pdf.worker.min.mjs?url"),
    ]).then(([pdfjs, worker]) => {
      pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
      return pdfjs;
    });
  }
  return pdfjsPromise;
}

function PdfPage({ doc, pageNumber, width, height }: {
  doc: PDFDocumentProxy; pageNumber: number; width: number; height?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!width) return;
    let cancelled = false;
    let task: RenderTask | null = null;
    doc.getPage(pageNumber).then((page) => {
      const canvas = canvasRef.current;
      if (cancelled || !canvas) return;
      const base = page.getViewport({ scale: 1 });
      let scale = width / base.width;
      if (height) scale = Math.min(scale, height / base.height);
      const dpr = window.devicePixelRatio || 1;
      const viewport = page.getViewport({ scale: scale * dpr });
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      canvas.style.width = `${viewport.width / dpr}px`;
      canvas.style.height = `${viewport.height / dpr}px`;
      task = page.render({ canvasContext: canvas.getContext("2d")!, viewport });
      task.promise.catch(() => {}); // cancelled by a re-render
    });
    return () => {
      cancelled = true;
      task?.cancel();
    };
  }, [doc, pageNumber, width, height]);

  return <canvas ref={canvasRef} className="block mx-auto mb-3 bg-white" />;
}

/** Renders a PDF with pdf.js (works on iPad, unlike an <iframe>).
 * With `page`, shows that one page scaled to fit the box; otherwise every
 * page stacked at full width. */
export default function PdfView({ url, page, onPageCount }: {
  url: string; page?: number; onPageCount?: (n: number) => void;
}) {
  const boxRef = useRef<HTMLDivElement>(null);
  const [doc, setDoc] = useState<PDFDocumentProxy | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const onPageCountRef = useRef(onPageCount);
  onPageCountRef.current = onPageCount;

  useEffect(() => {
    let cancelled = false;
    let loaded: PDFDocumentProxy | null = null;
    setDoc(null);
    setError(null);
    loadPdfjs()
      .then((pdfjs) => pdfjs.getDocument({ url, withCredentials: true }).promise)
      .then((d) => {
        if (cancelled) {
          d.destroy();
          return;
        }
        loaded = d;
        setDoc(d);
        onPageCountRef.current?.(d.numPages);
      })
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
      loaded?.destroy();
    };
  }, [url]);

  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) =>
      setSize({ w: entry.contentRect.width, h: entry.contentRect.height }),
    );
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const pages = doc
    ? page != null ? [Math.min(Math.max(page, 1), doc.numPages)] : Array.from({ length: doc.numPages }, (_, i) => i + 1)
    : [];

  return (
    <div ref={boxRef} data-scroll className="w-full h-full overflow-auto">
      {error && <p className="text-sm p-4" style={{ color: "var(--red)" }}>Couldn't load chart: {error}</p>}
      {!doc && !error && <p className="text-sm p-4" style={{ color: "var(--text-muted)" }}>Loading chart…</p>}
      {doc && pages.map((p) => (
        <PdfPage key={p} doc={doc} pageNumber={p} width={size.w} height={page != null ? size.h : undefined} />
      ))}
    </div>
  );
}
