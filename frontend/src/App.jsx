import { useState, useEffect, useRef } from "react";
import axios from "axios";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ─── Animation Hook ───
function useInView() {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { setInView(true); observer.disconnect(); }
    }, { threshold: 0.15 });
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  return [ref, inView];
}

function AnimatedSection({ children, delay = 0 }) {
  const [ref, inView] = useInView();
  return (
    <div ref={ref} style={{
      opacity: inView ? 1 : 0,
      transform: inView ? "translateY(0)" : "translateY(40px)",
      transition: `opacity 0.7s ease ${delay}s, transform 0.7s ease ${delay}s`,
    }}>
      {children}
    </div>
  );
}

function PageWrapper({ children }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => { const t = setTimeout(() => setVisible(true), 20); return () => clearTimeout(t); }, []);
  return (
    <div style={{ opacity: visible ? 1 : 0, transform: visible ? "translateY(0)" : "translateY(16px)", transition: "opacity 0.35s ease, transform 0.35s ease" }}>
      {children}
    </div>
  );
}

function StepBar({ step }) {
  const steps = ["Upload", "Analyze", "Compare"];
  return (
    <div className="step-bar">
      {steps.map((label, i) => {
        const n = i + 1; const active = n === step; const done = n < step;
        return (
          <div key={n} className="step-item">
            <div className={`step-circle ${active ? "active" : done ? "done" : ""}`}>{n}</div>
            <span className={`step-label ${active ? "active" : ""}`}>{label}</span>
            {i < steps.length - 1 && <div className={`step-line ${done ? "done" : ""}`} />}
          </div>
        );
      })}
    </div>
  );
}

const ANALYZE_LINES = ["Reading your resume...", "Parsing job description...", "Identifying skill requirements...", "Analyzing experience alignment...", "Scoring keyword matches...", "Calculating match score...", "Finalizing analysis..."];
const GENERATE_LINES = ["Understanding your profile...", "Identifying improvement areas...", "Crafting targeted bullet points...", "Refining language and tone...", "Aligning with job requirements...", "Adding strategic keywords...", "Polishing your resume..."];

function TypewriterLoading({ isAnalyzing }) {
  const lines = isAnalyzing ? ANALYZE_LINES : GENERATE_LINES;
  const title = isAnalyzing ? "Analyzing Your Resume" : "Generating Optimized Resume";
  const [displayedLines, setDisplayedLines] = useState([]);
  const [currentLine, setCurrentLine] = useState(0);
  const [currentText, setCurrentText] = useState("");
  const [charIdx, setCharIdx] = useState(0);

  useEffect(() => {
    if (currentLine >= lines.length) return;
    const line = lines[currentLine];
    if (charIdx < line.length) {
      const t = setTimeout(() => { setCurrentText(prev => prev + line[charIdx]); setCharIdx(c => c + 1); }, 35);
      return () => clearTimeout(t);
    } else {
      const t = setTimeout(() => { setDisplayedLines(prev => [...prev, line]); setCurrentText(""); setCharIdx(0); setCurrentLine(c => c + 1); }, 400);
      return () => clearTimeout(t);
    }
  }, [currentLine, charIdx, lines]);

  return (
    <div className="loading-screen">
      <div className="loading-icon">
        <div className="resume-icon">
          <div className="ri-bar dark" /><div className="ri-bar mid" /><div className="ri-bar light" /><div className="ri-bar light short" />
          <div style={{ marginTop: 8 }}><div className="ri-bar light" /><div className="ri-bar light mid-w" /></div>
          <div className="ri-pulse" />
        </div>
      </div>
      <h2 className="loading-title">{title}</h2>
      <div className="typewriter-box">
        {displayedLines.map((line, i) => (
          <div key={i} className="tw-line done"><span className="tw-check">✓</span><span>{line}</span></div>
        ))}
        {currentLine < lines.length && (
          <div className="tw-line current"><span className="tw-dot">›</span><span>{currentText}<span className="tw-cursor">|</span></span></div>
        )}
      </div>
    </div>
  );
}

function LandingPage({ onBegin }) {
  return (
    <PageWrapper>
      <div className="landing">
        <nav className="landing-nav">
          <span className="logo">ResumeMatch</span>
          <button className="begin-btn" onClick={onBegin}>Begin</button>
        </nav>

        <section className="hero">
          <AnimatedSection delay={0.1}>
            <div className="hero-tag">INTELLIGENT OPTIMIZATION</div>
          </AnimatedSection>
          <div className="hero-grid">
            <div className="hero-left">
              <AnimatedSection delay={0.2}>
                <h1 className="hero-title">Your resume,<br />refined by<br />intelligence.</h1>
                <p className="hero-sub">A sophisticated approach to resume optimization.<br />Every word measured, every detail considered.</p>
                <button className="outline-btn" onClick={onBegin}>BEGIN NOW</button>
              </AnimatedSection>
            </div>
            <div className="hero-right">
              <AnimatedSection delay={0.4}>
                <div className="resume-card">
                  <div className="rc-bar dark" /><div className="rc-bar mid" style={{ width: "70%" }} />
                  <div className="rc-bar light" style={{ width: "85%" }} /><div className="rc-bar light" style={{ width: "60%" }} />
                  <div style={{ marginTop: 16 }}><div className="rc-bar light" style={{ width: "90%" }} /><div className="rc-bar light" style={{ width: "75%" }} /></div>
                  <div className="match-badge"><div className="mb-label">MATCH SCORE</div><div className="mb-score">68%</div></div>
                </div>
              </AnimatedSection>
            </div>
          </div>
        </section>

        <section className="process-section">
          <AnimatedSection delay={0}>
            <h2 className="process-title">Three steps to precision</h2>
          </AnimatedSection>
          <div className="process-steps">
            {[
              { n: "01", name: "Submit", desc: "Upload your current resume in any standard format" },
              { n: "02", name: "Analyze", desc: "Provide the job description you're targeting" },
              { n: "03", name: "Refine", desc: "Receive an optimized version, ready for submission" }
            ].map((s, i) => (
              <div key={i}>
                <AnimatedSection delay={i * 0.15}>
                  <div className="process-row">
                    <span className="process-num">{s.n}</span>
                    <span className="process-name">{s.name}</span>
                    <span className="process-desc">{s.desc}</span>
                  </div>
                </AnimatedSection>
                {i < 2 && <div className="process-divider" />}
              </div>
            ))}
          </div>
        </section>

        <section className="testimonials-section">
          <AnimatedSection delay={0}>
            <div className="section-tag">TRUSTED BY JOB SEEKERS</div>
            <h2 className="section-h2">Results that speak</h2>
          </AnimatedSection>
          <div className="t-grid">
            {[
              { q: "I went from zero callbacks to three interviews in one week. The resume transformation was remarkable.", name: "Sarah Chen", role: "Data Analyst · New York" },
              { q: "The semantic matching is extraordinary. It understands what recruiters actually look for, not just keywords.", name: "Marcus Rivera", role: "Software Engineer · San Francisco" },
              { q: "Every resume I've submitted since using this tool has gotten a response. The precision is unmatched.", name: "Priya Sharma", role: "Product Manager · London" }
            ].map((t, i) => (
              <AnimatedSection key={i} delay={i * 0.15}>
                <div className="t-card">
                  <p className="t-quote">"{t.q}"</p>
                  <div className="t-author">
                    <div className="t-avatar">{t.name.split(" ").map(n => n[0]).join("")}</div>
                    <div><div className="t-name">{t.name}</div><div className="t-role">{t.role}</div></div>
                  </div>
                </div>
              </AnimatedSection>
            ))}
          </div>
        </section>

        <AnimatedSection delay={0}>
          <section className="cta-section">
            <h2 className="cta-title">Begin with precision.</h2>
            <p className="cta-sub">Upload your resume and discover what intelligence reveals.</p>
            <button className="outline-btn large" onClick={onBegin}>UPLOAD RESUME</button>
            <p className="cta-note">No account required · Results in seconds · Completely private</p>
          </section>
        </AnimatedSection>

        <footer className="footer">
          <div className="logo">ResumeMatch</div>
          <p style={{ fontSize: 14, color: "#6b7280", marginTop: 8 }}>Intelligent optimization for the modern professional.</p>
        </footer>
      </div>
    </PageWrapper>
  );
}

function UploadPage({ resumeText, setResumeText, jdText, setJdText, onAnalyze, loading, error, onLogoClick }) {
  const [pdfSuccess, setPdfSuccess] = useState(false);
  const resumeWords = resumeText.trim() ? resumeText.trim().split(/\s+/).length : 0;
  const jdWords = jdText.trim() ? jdText.trim().split(/\s+/).length : 0;

  return (
    <PageWrapper>
      <div className="page">
        <nav className="app-nav">
          <span className="logo" onClick={onLogoClick} style={{ cursor: "pointer" }}>ResumeMatch</span>
        </nav>
        <StepBar step={1} />
        <div className="page-body">
          <div className="page-heading">
            <h1 className="page-title">Upload Your Information</h1>
            <p className="page-sub">Paste your resume and the job description to begin analysis</p>
          </div>
          {error && <div className="error-box">{error}</div>}
          <div className="two-col">
            <div className="input-group">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <label className="input-label">Your Resume</label>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  {pdfSuccess && <span style={{ fontSize: 12, color: "#16a34a" }}>✓ PDF uploaded</span>}
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>{resumeWords} words</span>
                  {resumeText && <button onClick={() => { setResumeText(""); setPdfSuccess(false); }} style={{ fontSize: 12, color: "var(--muted)", background: "none", border: "none", cursor: "pointer" }}>Clear</button>}
                </div>
              </div>
              <textarea className="big-textarea" placeholder="Paste your resume text here..."
                value={resumeText} onChange={e => setResumeText(e.target.value)} />
              <label className="upload-file-btn">
                📄 Upload PDF
                <input type="file" accept=".pdf" style={{ display: "none" }}
                  onChange={async (e) => {
                    const file = e.target.files[0];
                    if (!file) return;
                    const formData = new FormData();
                    formData.append("file", file);
                    try {
                      const res = await fetch(`${API_BASE}/api/parse-pdf`, { method: "POST", body: formData });
                      const data = await res.json();
                      if (data.text) { setResumeText(data.text); setPdfSuccess(true); }
                      else alert("Could not extract text from PDF. Please paste manually.");
                    } catch { alert("Failed to parse PDF. Please paste text manually."); }
                  }}
                />
              </label>
            </div>
            <div className="input-group">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <label className="input-label">Job Description</label>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>{jdWords} words</span>
                  {jdText && <button onClick={() => setJdText("")} style={{ fontSize: 12, color: "var(--muted)", background: "none", border: "none", cursor: "pointer" }}>Clear</button>}
                </div>
              </div>
              <textarea className="big-textarea" placeholder="Paste the job description here..."
                value={jdText} onChange={e => setJdText(e.target.value)} />
            </div>
          </div>
          <div style={{ display: "flex", justifyContent: "center", marginTop: 32 }}>
            <button className="navy-btn large" onClick={onAnalyze} disabled={loading}>
              {loading ? "Analyzing..." : "Analyze Resume →"}
            </button>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}

function AnalyzePage({ analysisResult, onGenerate, loading, onLogoClick, selectedKeywords, setSelectedKeywords }) {
  const overall = analysisResult?.overall_score ?? 0;
  const skill = analysisResult?.skill_score ?? 0;
  const exp = analysisResult?.experience_score ?? 0;
  const gaps = analysisResult?.gaps ?? [];
  const keywords = analysisResult?.keywords ?? [];
  const ungappedGaps = gaps.filter(g => g.importance !== "covered");

  const toggleKeyword = (word) => {
    setSelectedKeywords(prev => prev.includes(word) ? prev.filter(w => w !== word) : [...prev, word]);
  };

  const selectedGapsData = gaps.filter(g => selectedKeywords.includes(g.skill));

  const scoreGradient = (v) => v >= 75
    ? "linear-gradient(135deg, #16a34a, #4ade80)"
    : v >= 50
    ? "linear-gradient(135deg, #d97706, #fbbf24)"
    : "linear-gradient(135deg, #dc2626, #f87171)";

  return (
    <PageWrapper>
      <div className="page">
        <nav className="app-nav">
          <span className="logo" onClick={onLogoClick} style={{ cursor: "pointer" }}>ResumeMatch</span>
        </nav>
        <StepBar step={2} />
        <div className="page-body">
          <AnimatedSection delay={0}>
            <div className="page-heading">
              <h1 className="page-title">Analysis Results</h1>
              <p className="page-sub">Here's how your resume matches the job description</p>
            </div>
          </AnimatedSection>

          {/* Score Cards */}
          <AnimatedSection delay={0.1}>
            <div className="score-cards">
              {[
                { label: "OVERALL SCORE", value: overall },
                { label: "SKILL SCORE", value: skill },
                { label: "EXPERIENCE SCORE", value: exp }
              ].map((s, i) => (
                <div key={s.label} className="score-card" style={{
                  background: "white",
                  border: "1px solid #e5e7eb",
                  borderRadius: 16,
                  padding: 24,
                  position: "relative",
                  overflow: "hidden",
                }}>
                  <div style={{
                    position: "absolute", top: -20, right: -20,
                    width: 100, height: 100, borderRadius: "50%",
                    background: scoreGradient(s.value),
                    opacity: 0.08,
                  }} />
                  <div className="sc-label" style={{ fontSize: 11, letterSpacing: 1, color: "#9ca3af", marginBottom: 8 }}>{s.label}</div>
                  <div style={{
                    fontSize: 48, fontWeight: 800,
                    fontFamily: "'Playfair Display', serif",
                    background: scoreGradient(s.value),
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    lineHeight: 1,
                    marginBottom: 16,
                  }}>
                    {s.value}%
                  </div>
                  <div style={{ height: 6, background: "#f3f4f6", borderRadius: 3, overflow: "hidden" }}>
                    <div style={{
                      height: 6, borderRadius: 3,
                      width: `${s.value}%`,
                      background: scoreGradient(s.value),
                      transition: "width 1s cubic-bezier(0.22, 1, 0.36, 1)",
                    }} />
                  </div>
                </div>
              ))}
            </div>
          </AnimatedSection>

          {/* Radar Chart */}
          <AnimatedSection delay={0.15}>
            <div style={{
              marginTop: 40, padding: 32,
              background: "linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%)",
              borderRadius: 20, border: "1px solid #e0e7ff",
            }}>
              <div style={{ fontSize: 11, color: "#6366f1", letterSpacing: 2, marginBottom: 4, fontWeight: 600 }}>VISUAL INSIGHTS</div>
              <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--navy)", marginBottom: 24 }}>Performance Comparison</h2>
              <ResponsiveContainer width="100%" height={260}>
                <RadarChart data={[
                  { subject: "Skills", before: skill, after: Math.min(100, skill + 15) },
                  { subject: "Experience", before: exp, after: Math.min(100, exp + 10) },
                  { subject: "Keywords", before: Math.round(overall * 0.8), after: overall },
                  { subject: "Education", before: 80, after: 85 },
                  { subject: "Overall", before: overall, after: Math.min(100, overall + 12) },
                ]}>
                  <PolarGrid stroke="#e0e7ff" />
                  <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: "#6b7280" }} />
                  <Radar name={`Before (${overall}%)`} dataKey="before" stroke="#9ca3af" fill="#9ca3af" fillOpacity={0.25} strokeWidth={2} />
                  <Radar name="After (projected)" dataKey="after" stroke="#6366f1" fill="#6366f1" fillOpacity={0.3} strokeWidth={2} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </AnimatedSection>

          {/* Skill Coverage */}
          <AnimatedSection delay={0.2}>
            <div style={{
              marginTop: 32, padding: 28,
              background: "white", borderRadius: 20,
              border: "1px solid #e5e7eb",
            }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--navy)", marginBottom: 20 }}>Skill Coverage</h3>
              {ungappedGaps.slice(0, 6).map((g, i) => (
                <div key={i} style={{ marginBottom: 16 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 6 }}>
                    <span style={{ fontWeight: 500 }}>{g.skill}</span>
                    <span style={{
                      fontSize: 11, fontWeight: 600, padding: "2px 10px", borderRadius: 20,
                      background: g.importance === "covered" ? "#dcfce7" : g.importance === "partial" ? "#fef3c7" : "#fee2e2",
                      color: g.importance === "covered" ? "#16a34a" : g.importance === "partial" ? "#d97706" : "#dc2626",
                    }}>
                      {g.importance === "covered" ? "✓ Covered" : g.importance === "partial" ? "~ Partial" : "✗ Missing"}
                    </span>
                  </div>
                  <div style={{ height: 6, background: "#f3f4f6", borderRadius: 3, overflow: "hidden" }}>
                    <div style={{
                      height: 6, borderRadius: 3,
                      width: g.importance === "covered" ? "100%" : g.importance === "partial" ? "55%" : "8%",
                      background: g.importance === "covered"
                        ? "linear-gradient(90deg, #16a34a, #4ade80)"
                        : g.importance === "partial"
                        ? "linear-gradient(90deg, #d97706, #fbbf24)"
                        : "linear-gradient(90deg, #dc2626, #f87171)",
                      transition: `width 0.8s cubic-bezier(0.22, 1, 0.36, 1) ${i * 0.1}s`,
                    }} />
                  </div>
                </div>
              ))}
              {ungappedGaps.length > 0 && (
                <div style={{ marginTop: 16, fontSize: 12, color: "#6b7280" }}>
                  Coverage: {Math.round((gaps.filter(g => g.importance === "covered").length / Math.max(gaps.length, 1)) * 100)}%
                </div>
              )}
            </div>
          </AnimatedSection>

          {/* Skill Gaps + Keywords */}
          <AnimatedSection delay={0.25}>
            <div className="two-col" style={{ marginTop: 32 }}>
              <div style={{ padding: 28, background: "white", borderRadius: 20, border: "1px solid #e5e7eb" }}>
                <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--navy)", marginBottom: 6 }}>Skill Gaps</h2>
                <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 16 }}>Missing or underrepresented in your resume.</p>
                <div className="gaps-list">
                  {ungappedGaps.map((g, i) => (
                    <div key={i} className="gap-row" style={{ flexDirection: "column", alignItems: "flex-start", gap: 4 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", width: "100%", alignItems: "center" }}>
                        <span className="gap-name">{g.skill}</span>
                        <span style={{
                          fontSize: 11, fontWeight: 600, padding: "2px 10px", borderRadius: 20,
                          background: g.importance === "required" ? "#fee2e2" : "#fef3c7",
                          color: g.importance === "required" ? "#dc2626" : "#d97706",
                        }}>
                          {g.importance === "required" ? "High" : "Medium"}
                        </span>
                      </div>
                      {g.suggestion_en && (
                        <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.6, paddingBottom: 4 }}>{g.suggestion_en}</p>
                      )}
                    </div>
                  ))}
                  {ungappedGaps.length === 0 && (
                    <div style={{ padding: 20, textAlign: "center" }}>
                      <div style={{ fontSize: 32, marginBottom: 8 }}>🎉</div>
                      <p style={{ color: "#16a34a", fontWeight: 600 }}>No major gaps found!</p>
                    </div>
                  )}
                </div>
              </div>

              <div style={{ padding: 28, background: "white", borderRadius: 20, border: "1px solid #e5e7eb" }}>
                <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--navy)", marginBottom: 6 }}>Keywords</h2>
                <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 16 }}>Click unmatched keywords to add them.</p>
                <div className="keywords-wrap">
                  {keywords.map((k, i) => {
                    const isSelected = selectedKeywords.includes(k.word);
                    return (
                      <div key={i}
                        onClick={() => !k.matched && toggleKeyword(k.word)}
                        style={{
                          padding: "6px 14px", borderRadius: 20, fontSize: 12,
                          cursor: k.matched ? "default" : "pointer",
                          userSelect: "none",
                          border: k.matched ? "1px solid #bbf7d0" : isSelected ? "1px solid #1e3a5f" : "1px solid #e5e7eb",
                          background: k.matched
                            ? "linear-gradient(135deg, #f0fdf4, #dcfce7)"
                            : isSelected
                            ? "linear-gradient(135deg, #1e3a5f, #2d5a8e)"
                            : "#f9fafb",
                          color: k.matched ? "#16a34a" : isSelected ? "white" : "#6b7280",
                          fontWeight: k.matched || isSelected ? 600 : 400,
                          transition: "all 0.15s ease",
                          marginBottom: 6,
                        }}
                      >
                        {k.word}{k.matched ? " ✓" : isSelected ? " ✓" : ""}
                      </div>
                    );
                  })}
                </div>
                {selectedKeywords.length > 0 && (
                  <p style={{ fontSize: 13, color: "var(--navy)", marginTop: 16, fontWeight: 600 }}>
                    {selectedKeywords.length} keyword{selectedKeywords.length > 1 ? "s" : ""} selected
                  </p>
                )}
              </div>
            </div>
          </AnimatedSection>

          <AnimatedSection delay={0.3}>
            <div style={{ display: "flex", justifyContent: "center", marginTop: 40, marginBottom: 40 }}>
              <button className="navy-btn large" onClick={() => onGenerate(selectedGapsData)} disabled={loading}
                style={{
                  background: "linear-gradient(135deg, #1e3a5f, #2d5a8e)",
                  boxShadow: "0 4px 20px rgba(30, 58, 95, 0.3)",
                  transition: "all 0.2s ease",
                }}
              >
                {loading ? "Generating..." : "Generate Optimized Resume →"}
              </button>
            </div>
          </AnimatedSection>
        </div>
      </div>
    </PageWrapper>
  );
}


function ComparePage({ resumeText, jdText, generatedResult, analysisResult, afterScore, onRegenerate, loading, mode, setMode, apiBase, selectedGapsData, onLogoClick }) {
  const optimized = generatedResult?.optimized_resume || "";
  const [downloading, setDownloading] = useState(false);
  const [pages, setPages] = useState(2);
  const [copied, setCopied] = useState(false);
  const overallBefore = analysisResult?.overall_score ?? 0;
  const overallAfter = afterScore?.overall_score ?? null;
  const improvement = overallAfter !== null ? overallAfter - overallBefore : null;
  const originalLines = resumeText.split("\n");

  const renderLine = (text) => {
    const parts = text.split(/(\[NEW\][\s\S]*?\[NEW\])/g);
    return parts.map((part, i) => {
      if (/^\[NEW\][\s\S]*\[NEW\]$/.test(part)) {
        const cleaned = part.replace(/^\[NEW\]/, "").replace(/\[NEW\]$/, "");
        return <mark key={i} className="new-mark">{cleaned}</mark>;
      }
      return <span key={i}>{part}</span>;
    });
  };

  const handleCopy = async () => {
    const cleanText = optimized.replace(/\[NEW\]/g, "");
    await navigator.clipboard.writeText(cleanText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const res = await fetch(`${apiBase}/api/generate-docx?pages=${pages}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          optimized_text: optimized.replace(/\[NEW\]/g, ""),
          resume_text: resumeText,
          jd_text: jdText,
          gaps: selectedGapsData || [],
          mode: mode
        }),
      });
      if (!res.ok) throw new Error("failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "optimized_resume.docx"; a.click();
      URL.revokeObjectURL(url);
    } catch { alert("Download failed. Please try again."); }
    finally { setDownloading(false); }
  };

  const scoreColor = (v) => v >= 75 ? "#16a34a" : v >= 50 ? "#d97706" : "#dc2626";

  return (
    <PageWrapper>
      <div className="page">
        <nav className="app-nav">
          <span className="logo" onClick={onLogoClick} style={{ cursor: "pointer" }}>ResumeMatch</span>
        </nav>
        <StepBar step={3} />
        <div className="compare-header">
          <h1 className="page-title">Compare Results</h1>
          <p className="page-sub">See the improvements made to your resume</p>
        </div>
        <div className="compare-layout">
          <div className="compare-content">
            <div className="compare-cols">
              <div className="compare-col">
                <div className="compare-col-header"><h2 className="col-title">Original Resume</h2></div>
                <div className="resume-doc" style={{whiteSpace:"pre-wrap", fontFamily:"'Courier New', monospace", fontSize:"12.5px", lineHeight:"1.8"}}>{resumeText}</div>
              </div>
              <div className="compare-col highlight-col">
                <div className="compare-col-header">
                  <h2 className="col-title">Optimized Resume</h2>
                  <span className="improved-badge">↗ Improved</span>
                </div>
                <div className="resume-doc" style={{ whiteSpace: "pre-wrap", fontFamily: "'Courier New', monospace", fontSize: "12.5px", lineHeight: "1.8" }}>{renderLine(optimized)}</div>
              </div>
            </div>
          </div>
          <div className="compare-sidebar">
            <h2 className="col-title">Score Comparison</h2>
            <div className="score-compare">
              <div className="sc-block">
                <div className="sc-tag">BEFORE</div>
                <div className="sc-num gray">{overallBefore}%</div>
              </div>
              <div className="sc-block">
                <div className="sc-tag">AFTER</div>
                <div className="sc-num" style={{ color: overallAfter !== null ? scoreColor(overallAfter) : "var(--muted)", fontFamily: "'Playfair Display', serif", fontSize: 44, fontWeight: 700, letterSpacing: -2 }}>
                  {overallAfter !== null ? `${overallAfter}%` : <span style={{ fontSize: 16 }}>Scoring...</span>}
                </div>
              </div>
              {improvement !== null && (
                <div className="sc-imp-block">
                  <span className="sc-arrow">{improvement >= 0 ? "↗" : "↘"}</span>
                  <span className="sc-plus" style={{ color: improvement >= 0 ? "#16a34a" : "#dc2626" }}>{improvement >= 0 ? "+" : ""}{improvement}%</span>
                  <div className="sc-imp-label">Improvement</div>
                </div>
              )}
            </div>

            {/* Radar Chart */}
            <div style={{ marginTop: 24 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: "var(--navy)", marginBottom: 12 }}>Score Breakdown</h3>
              <ResponsiveContainer width="100%" height={200}>
                <RadarChart
                  data={[
                    { subject: "Skills", before: overallBefore * 0.4, after: (overallAfter || 0) * 0.4 },
                    { subject: "Experience", before: analysisResult?.experience_score || 0, after: afterScore?.experience_score || 0 },
                    { subject: "Keywords", before: analysisResult?.skill_score || 0, after: afterScore?.skill_score || 0 },
                    { subject: "Overall", before: overallBefore, after: overallAfter || 0 },
                  ]}
                >
                  <PolarGrid />
                  <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
                  <Radar name="Before" dataKey="before" stroke="#9ca3af" fill="#9ca3af" fillOpacity={0.3} />
                  <Radar name="After" dataKey="after" stroke="#1e3a5f" fill="#1e3a5f" fillOpacity={0.4} />
                  <Legend />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            {/* Skill Gap Bars */}
            <div style={{ marginTop: 24 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: "var(--navy)", marginBottom: 12 }}>Skill Coverage</h3>
              {(analysisResult?.gaps || []).slice(0, 6).map((g, i) => (
                <div key={i} style={{ marginBottom: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 3 }}>
                    <span>{g.skill}</span>
                    <span
                      style={{
                        color: g.importance === "covered" ? "#16a34a" : g.importance === "partial" ? "#d97706" : "#dc2626",
                      }}
                    >
                      {g.importance === "covered" ? "✓" : g.importance === "partial" ? "~" : "✗"}
                    </span>
                  </div>
                  <div style={{ height: 6, background: "#f3f4f6", borderRadius: 3 }}>
                    <div
                      style={{
                        height: 6,
                        borderRadius: 3,
                        width: g.importance === "covered" ? "100%" : g.importance === "partial" ? "50%" : "10%",
                        background: g.importance === "covered" ? "#16a34a" : g.importance === "partial" ? "#d97706" : "#dc2626",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Before / After metric bars */}
            <div style={{ marginTop: 24 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: "var(--navy)", marginBottom: 12 }}>Metrics</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart
                  data={[
                    { name: "Overall", before: overallBefore, after: overallAfter ?? 0 },
                    { name: "Skills", before: analysisResult?.skill_score ?? 0, after: afterScore?.skill_score ?? 0 },
                    { name: "Experience", before: analysisResult?.experience_score ?? 0, after: afterScore?.experience_score ?? 0 },
                  ]}
                  margin={{ top: 8, right: 8, left: -18, bottom: 0 }}
                >
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Legend />
                  <Bar name="Before" dataKey="before" fill="#9ca3af" radius={[4, 4, 0, 0]} />
                  <Bar name="After" dataKey="after" fill="#1e3a5f" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="sidebar-controls">
              <div className="ctrl-row">
                <span className="ctrl-label">Mode</span>
                <select className="ctrl-select" value={mode} onChange={e => setMode(e.target.value)}>
                  <option value="smart_fill">Smart Fill</option>
                  <option value="full_rewrite">Full Rewrite</option>
                </select>
              </div>
              <div className="ctrl-row">
                <span className="ctrl-label">Pages</span>
                <div className="pages-btns">
                  {[1, 2, 3].map(n => (
                    <button key={n} className={`pg-btn ${pages === n ? "active" : ""}`} onClick={() => setPages(n)}>{n}</button>
                  ))}
                </div>
              </div>
              <button className="navy-btn full" onClick={handleDownload} disabled={!optimized || downloading}>
                {downloading ? "Generating..." : "⬇ Download Word"}
              </button>
              <button className="outline-btn-navy full" onClick={handleCopy} disabled={!optimized}>
                {copied ? "✓ Copied!" : "Copy Text"}
              </button>
              <button className="outline-btn-navy full" onClick={() => onRegenerate(selectedGapsData)} disabled={loading}>
                {loading ? "Regenerating..." : "Regenerate"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}

export default function App() {
  const [page, setPage] = useState("landing");
  const [resumeText, setResumeText] = useState("");
  const [jdText, setJdText] = useState("");
  const [analysisResult, setAnalysisResult] = useState(null);
  const [generatedResult, setGeneratedResult] = useState(null);
  const [afterScore, setAfterScore] = useState(null);
  const [selectedKeywords, setSelectedKeywords] = useState([]);
  const [selectedGapsData, setSelectedGapsData] = useState([]);
  const [mode, setMode] = useState("smart_fill");
  const [analyzing, setAnalyzing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    window.history.replaceState({ page: "landing" }, "", window.location.pathname);
    const handlePopState = (e) => { setPage(e.state?.page || "landing"); };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigateTo = (newPage) => {
    window.history.pushState({ page: newPage }, "", window.location.pathname);
    setPage(newPage);
  };

  const goHome = () => {
    window.history.pushState({ page: "landing" }, "", window.location.pathname);
    setPage("landing");
  };

  useEffect(() => {
    const handleKey = (e) => { if (e.key === "Escape" && page !== "landing") window.history.back(); };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [page]);

  const handleAnalyze = async () => {
    if (!resumeText.trim() || !jdText.trim()) { setError("Please fill in both fields."); return; }
    try {
      setError(""); setAnalyzing(true);
      const { data } = await axios.post(`${API_BASE}/api/analyze`, { resume_text: resumeText, jd_text: jdText });
      setAnalysisResult(data);
      setSelectedKeywords([]);
      navigateTo("analyze");
    } catch { setError("Request failed. Please check backend and try again."); }
    finally { setAnalyzing(false); }
  };

  const handleGenerate = async (gapsData) => {
    if (!analysisResult) return;
    const gaps = gapsData?.length > 0 ? gapsData : analysisResult.gaps;
    setSelectedGapsData(gaps);
    try {
      setError(""); setGenerating(true); setAfterScore(null);
      const { data } = await axios.post(`${API_BASE}/api/generate`, { resume_text: resumeText, jd_text: jdText, gaps, mode });
      setGeneratedResult(data);
      navigateTo("compare");
      try {
        const cleanedText = data.optimized_resume.replace(/\[NEW\]/g, "");
        const { data: newScore } = await axios.post(`${API_BASE}/api/analyze`, { resume_text: cleanedText, jd_text: jdText });
        setAfterScore(newScore);
      } catch (e) {
        console.error("Re-scoring failed", e);
        setAfterScore({ overall_score: null });
      }
    } catch { setError("Request failed."); }
    finally { setGenerating(false); }
  };

  if (analyzing) return <TypewriterLoading isAnalyzing={true} />;
  if (generating) return <TypewriterLoading isAnalyzing={false} />;

  if (page === "landing") return <LandingPage onBegin={() => {
    setResumeText(""); setJdText(""); setAnalysisResult(null);
    setGeneratedResult(null); setAfterScore(null); setSelectedKeywords([]);
    navigateTo("upload");
  }} />;
  if (page === "upload") return <UploadPage resumeText={resumeText} setResumeText={setResumeText} jdText={jdText} setJdText={setJdText} onAnalyze={handleAnalyze} loading={analyzing} error={error} onLogoClick={goHome} />;
  if (page === "analyze") return <AnalyzePage analysisResult={analysisResult} onGenerate={handleGenerate} loading={generating} onLogoClick={goHome} selectedKeywords={selectedKeywords} setSelectedKeywords={setSelectedKeywords} />;
  if (page === "compare") return <ComparePage resumeText={resumeText} jdText={jdText} generatedResult={generatedResult} analysisResult={analysisResult} afterScore={afterScore} onRegenerate={handleGenerate} loading={generating} mode={mode} setMode={setMode} apiBase={API_BASE} selectedGapsData={selectedGapsData} onLogoClick={goHome} />;
}
