import { useMemo, useState } from "react";

function formatResumeHTML(text) {
  const sections = ["EDUCATION", "EXPERIENCE", "PROJECTS", "SKILLS", "SUMMARY"];
  const lines = text.split("\n");
  const result = [];

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) { result.push(<div key={idx} style={{height:'8px'}} />); return; }

    const isSection = sections.some(s => trimmed.toUpperCase() === s || trimmed.toUpperCase().startsWith(s + " "));
    const isBullet = trimmed.startsWith("•") || trimmed.startsWith("-");

    const renderWithHighlight = (text) => {
      const parts = text.split(/(\[NEW\][\s\S]*?\[NEW\])/g);
      return parts.map((part, i) => {
        if (/^\[NEW\][\s\S]*\[NEW\]$/.test(part)) {
          const cleaned = part.replace(/^\[NEW\]/, "").replace(/\[NEW\]$/, "");
          return <mark key={i} className="resume-highlight">{cleaned}</mark>;
        }
        return <span key={i}>{part}</span>;
      });
    };

    if (isSection) {
      result.push(
        <div key={idx} className="resume-section-header">
          {renderWithHighlight(trimmed)}
        </div>
      );
    } else if (isBullet) {
      result.push(
        <div key={idx} className="resume-bullet">
          {renderWithHighlight(trimmed)}
        </div>
      );
    } else {
      // Check if it looks like a name (first line, short)
      const isName = idx < 3 && trimmed.split(' ').length <= 4 && !trimmed.includes('|') && !trimmed.includes('@');
      if (isName && idx === 0) {
        result.push(<div key={idx} className="resume-name">{renderWithHighlight(trimmed)}</div>);
      } else if (trimmed.includes('@') || trimmed.includes('|') || trimmed.match(/\d{3}/)) {
        result.push(<div key={idx} className="resume-contact">{renderWithHighlight(trimmed)}</div>);
      } else {
        result.push(<div key={idx} className="resume-line">{renderWithHighlight(trimmed)}</div>);
      }
    }
  });

  return result;
}

export default function GenerateStep({
  t, mode, setMode, generatedResult, onGenerate, loading,
  resumeText, jdText, gaps, apiBase, analysisResult, onBack, toggleLanguage
}) {
  const [copied, setCopied] = useState(false);
  const [pages, setPages] = useState(2);
  const [downloading, setDownloading] = useState(false);
  const outputText = generatedResult?.optimized_resume || "";
  const formattedResume = useMemo(() => formatResumeHTML(outputText), [outputText]);

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
      a.download = "optimized_resume.docx";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Download failed", e);
    } finally {
      setDownloading(false);
    }
  };

  const overallBefore = analysisResult?.overall_score ?? "—";
  const skillBefore = analysisResult?.skill_score ?? "—";
  const expBefore = analysisResult?.experience_score ?? "—";

  return (
    <div className="result-page">
      {/* Top nav */}
      <nav className="result-nav">
        <span className="landing-logo">ResumeMatch</span>
        <div style={{display:'flex', gap:'12px', alignItems:'center'}}>
          {toggleLanguage && (
            <button className="lang-btn" onClick={toggleLanguage}>{t.language}</button>
          )}
          <button className="back-btn" onClick={onBack}>← Back</button>
        </div>
      </nav>

      <div className="result-body">
        {/* Left: scores + controls */}
        <div className="result-sidebar">
          <h2 className="sidebar-title">Your Results</h2>

          {/* Score cards */}
          <div className="score-section">
            <div className="score-label">MATCH SCORES</div>
            {[
              { label: "Overall", value: overallBefore },
              { label: "Skills", value: skillBefore },
              { label: "Experience", value: expBefore },
            ].map(s => (
              <div key={s.label} className="score-row">
                <span className="score-name">{s.label}</span>
                <div className="score-bar-wrap">
                  <div className="score-bar-fill" style={{width: `${s.value}%`}} />
                </div>
                <span className="score-value">{s.value}</span>
              </div>
            ))}
          </div>

          {/* Mode */}
          <div className="sidebar-section">
            <div className="score-label">{t.modeLabel}</div>
            <select value={mode} onChange={e => setMode(e.target.value)} className="mode-select">
              <option value="smart_fill">{t.smartFill}</option>
              <option value="full_rewrite">{t.fullRewrite}</option>
            </select>
          </div>

          {/* Pages */}
          <div className="sidebar-section">
            <div className="score-label">PAGES</div>
            <div className="pages-selector">
              {[1, 2, 3].map(n => (
                <button key={n} className={`page-btn ${pages === n ? 'active' : ''}`} onClick={() => setPages(n)}>{n}</button>
              ))}
            </div>
          </div>

          {/* Disclaimer */}
          <div className="disclaimer">{t.disclaimer}</div>

          {/* Actions */}
          <div className="action-buttons">
            <button className="action-btn secondary" onClick={handleCopy}>
              {copied ? "✓ Copied" : "Copy Text"}
            </button>
            <button className="action-btn secondary" onClick={handleDownloadDocx} disabled={!outputText || downloading}>
              {downloading ? "Generating..." : "⬇ Download Word"}
            </button>
            <button className="action-btn primary" onClick={onGenerate} disabled={loading}>
              {loading ? t.generating : t.regenerate}
            </button>
          </div>
        </div>

        {/* Right: formatted resume */}
        <div className="result-main">
          <div className="resume-header-row">
            <h2 className="sidebar-title">Optimized Resume</h2>
            <div className="highlight-legend">
              <mark className="resume-highlight" style={{padding:'2px 8px', borderRadius:'4px'}}>New content</mark>
            </div>
          </div>
          <div className="resume-document">
            {outputText ? formattedResume : <p style={{color:'#94a3b8', fontStyle:'italic'}}>Your optimized resume will appear here.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
