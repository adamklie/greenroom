import { useEffect } from "react";
import { api, type SongChart } from "../api/client";
import PdfView from "./PdfView";

/** An uploaded chart (PDF or image). With `page`, fits one page to the box
 * (Perform mode); without, shows the whole chart at full width (Practice). */
export default function ChartView({ chart, page, onPageCount }: {
  chart: SongChart; page?: number; onPageCount?: (n: number) => void;
}) {
  const url = api.charts.fileUrl(chart.id);
  const isPdf = chart.file_type === "pdf";

  useEffect(() => {
    if (!isPdf) onPageCount?.(1);
  }, [chart.id, isPdf, onPageCount]);

  if (isPdf) return <PdfView key={chart.id} url={url} page={page} onPageCount={onPageCount} />;
  return (
    <div data-scroll className="w-full h-full overflow-auto flex justify-center items-start">
      <img src={url} alt={chart.label || chart.original_filename || "Chart"}
        className={page != null ? "max-w-full max-h-full object-contain" : "max-w-full"} />
    </div>
  );
}
