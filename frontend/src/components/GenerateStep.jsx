import { useMemo, useState } from "react";

function renderNewMarkers(text) {
  const parts = text.split(/(\[NEW\][\s\S]*?\[\/NEW\])/g);
  return parts.map((part, idx) => {
    const marked = /^\[NEW\][\s\S]*\[\/NEW\]$/.test(part);
    if (!marked) return <span key={idx}>{part}</span>;
    const cleaned = part.replace(/^\[NEW\]/, "").replace(/\[\/NEW\]$/, "");
    return (
      <span key={idx} className="rounded bg-emerald-200 px-1">
        {cleaned}
      </span>
    );
  });
}

export default function GenerateStep({
  t, mode, setMode, generatedResult, onGenerate, loading,
  resumeText, jdText, gaps, apiBase,
}) {
  const [copied, setCopied] = useState(false);
  const [pages, setPages] = useState(2);
  const [downloading, setDownloading] = useState(false);
  const outputText = generatedResult?.optimized_resume || "";
  const renderedOutput = useMemo(() => renderNewMarkers(outputText), [outputText]);

  const handleCopy = async () => {
    if (!outputText) return;
    await navigator.clipboard.writeText(outputText);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  const handleDownloadDocx = async () => {
    if (!outputText) return;
    setDownloading(true);
    try {
      const res = await fetch(`${apiBase}/api/generate-docx?pages=${pages}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume_text: resumeText, jd_text: jdText, gaps, mode }),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `optimized_resume_${pages}page.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Download failed", e);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-white p-4 shadow-sm">
        <label className="mb-2 block text-sm font-medium text-slate-700">{t.modeLabel}</label>
        <select value={mode} onChange={(e) => setMode(e.target.value)}
          className="w-full rounded-lg border border-slate-300 p-2 text-sm outline-none focus:border-blue-500 md:w-72">
          <option value="smart_fill">{t.smartFill}</option>
          <option value="full_rewrite">{t.fullRewrite}</option>
        </select>
      </div>
      <div className="rounded-xl bg-amber-100 p-3 text-sm text-amber-900">{t.disclaimer}</div>
      <div className="rounded-xl bg-white p-4 shadow-sm">
        <h3 className="mb-3 text-base font-semibold text-slate-900">{t.outputTitle}</h3>
        <div className="min-h-56 whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800">
          {outputText ? renderedOutput : ""}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={handleCopy}
          className="rounded-lg bg-slate-200 px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-300">
          {copied ? t.copied : t.copy}
        </button>
        <div className="flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2 py-1">
          <span className="text-xs text-slate-500 mr-1">页数:</span>
          <button type="button" onClick={() => setPages(1)}
            className={`px-2 py-1 rounded text-xs font-medium ${pages === 1 ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}>
            1页
          </button>
          <button type="button" onClick={() => setPages(2)}
            className={`px-2 py-1 rounded text-xs font-medium ${pages === 2 ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}>
            2页
          </button>
        </div>
        <button type="button" onClick={handleDownloadDocx}
          disabled={!outputText || downloading}
          className="rounded-lg bg-slate-200 px-4 py-2 text-sm font-medium text-slate-800 hovere-300 disabled:opacity-50">
          {downloading ? "生成中..." : "⬇ 下载 Word"}
        </button>
        <button type="button" onClick={onGenerate} disabled={loading}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60">
          {loading ? t.generating : t.regenerate}
        </button>
      </div>
    </div>
  );
}
