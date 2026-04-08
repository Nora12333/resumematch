import * as pdfjsLib from "pdfjs-dist";
import pdfWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker;

async function extractPdfText(file) {
  const buffer = await file.arrayBuffer();
  const data = new Uint8Array(buffer);
  const loadingTask = pdfjsLib.getDocument({ data });
  const pdf = await loadingTask.promise;
  const pages = [];

  for (let i = 1; i <= pdf.numPages; i += 1) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    const text = content.items.map((item) => item.str).join(" ");
    pages.push(text);
  }
  return pages.join("\n");
}

export default function InputStep({
  t,
  resumeText,
  jdText,
  setResumeText,
  setJdText,
  onAnalyze,
  loading,
  setError,
}) {
  const handlePdfUpload = async (event, target) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const text = await extractPdfText(file);
      if (target === "resume") setResumeText(text);
      if (target === "jd") setJdText(text);
      setError("");
    } catch (_err) {
      setError(t.parseError);
    }
  };

  return (
    <div className="rounded-xl bg-white p-5 shadow-sm">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-700">{t.resumeLabel}</label>
          <textarea
            className="h-64 w-full rounded-lg border border-slate-300 p-3 text-sm outline-none focus:border-blue-500"
            value={resumeText}
            onChange={(e) => setResumeText(e.target.value)}
            placeholder={t.resumeLabel}
          />
          <label className="mt-2 inline-block cursor-pointer rounded-md bg-slate-100 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-200">
            {t.uploadResumePdf}
            <input type="file" accept="application/pdf" className="hidden" onChange={(e) => handlePdfUpload(e, "resume")} />
          </label>
        </div>
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-700">{t.jdLabel}</label>
          <textarea
            className="h-64 w-full rounded-lg border border-slate-300 p-3 text-sm outline-none focus:border-blue-500"
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            placeholder={t.jdLabel}
          />
          <label className="mt-2 inline-block cursor-pointer rounded-md bg-slate-100 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-200">
            {t.uploadJdPdf}
            <input type="file" accept="application/pdf" className="hidden" onChange={(e) => handlePdfUpload(e, "jd")} />
          </label>
        </div>
      </div>

      <button
        type="button"
        onClick={onAnalyze}
        disabled={loading}
        className="mt-5 inline-flex items-center rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
      >
        {loading ? t.analyzing : t.analyze}
      </button>
    </div>
  );
}
