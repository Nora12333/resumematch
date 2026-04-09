import { useState } from "react";
import axios from "axios";
import StepIndicator from "./components/StepIndicator";
import InputStep from "./components/InputStep";
import AnalysisStep from "./components/AnalysisStep";
import GenerateStep from "./components/GenerateStep";
import { useLanguage } from "./hooks/useLanguage";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function App() {
  const { t, toggleLanguage } = useLanguage();
  const [currentStep, setCurrentStep] = useState(1);
  const [resumeText, setResumeText] = useState("");
  const [jdText, setJdText] = useState("");
  const [analysisResult, setAnalysisResult] = useState(null);
  const [generatedResult, setGeneratedResult] = useState(null);
  const [mode, setMode] = useState("smart_fill");
  const [analyzing, setAnalyzing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  const handleAnalyze = async () => {
    if (!resumeText.trim() || !jdText.trim()) {
      setError(t.emptyInput);
      return;
    }
    try {
      setError("");
      // Always start a fresh analysis run.
      setAnalysisResult(null);
      setGeneratedResult(null);
      setCurrentStep(1);
      setAnalyzing(true);
      const { data } = await axios.post(`${API_BASE}/api/analyze`, {
        resume_text: resumeText,
        jd_text: jdText,
      });
      setAnalysisResult(data);
      setCurrentStep(2);
    } catch (_err) {
      setError(t.apiError);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleGenerate = async () => {
    if (!analysisResult) return;
    try {
      setError("");
      setGenerating(true);
      const { data } = await axios.post(`${API_BASE}/api/generate`, {
        resume_text: resumeText,
        jd_text: jdText,
        gaps: analysisResult.gaps,
        mode,
      });
      setGeneratedResult(data);
      setCurrentStep(3);
    } catch (_err) {
      setError(t.apiError);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-4 py-8">
      <header className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">{t.appTitle}</h1>
          <p className="mt-1 text-sm text-slate-600">{t.appSubtitle}</p>
        </div>
        <button
          type="button"
          onClick={toggleLanguage}
          className="rounded-lg bg-slate-200 px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-300"
        >
          {t.language}
        </button>
      </header>

      <StepIndicator steps={t.steps} currentStep={currentStep} />

      {error && <div className="mb-4 rounded-lg bg-rose-100 px-4 py-3 text-sm text-rose-700">{error}</div>}

      <InputStep
        t={t}
        resumeText={resumeText}
        jdText={jdText}
        setResumeText={setResumeText}
        setJdText={setJdText}
        onAnalyze={handleAnalyze}
        loading={analyzing}
        setError={setError}
      />

      {analysisResult && (
        <div className="mt-5">
          <AnalysisStep t={t} analysisResult={analysisResult} onGenerate={handleGenerate} loading={generating} />
        </div>
      )}

      {(currentStep >= 3 || generatedResult) && (
        <div className="mt-5">
          <GenerateStep
            t={t}
            mode={mode}
            setMode={setMode}
            generatedResult={generatedResult}
            onGenerate={handleGenerate}
            loading={generating}
          />
        </div>
      )}
    </main>
  );
}
