const badgeStyles = {
  required: "bg-rose-100 text-rose-700",
  nice_to_have: "bg-amber-100 text-amber-700",
  covered: "bg-emerald-100 text-emerald-700",
};

function ScoreCard({ label, score, color }) {
  return (
    <div className="rounded-xl bg-white p-4 shadow-sm">
      <p className="mb-2 text-sm text-slate-600">{label}</p>
      <p className="text-2xl font-bold text-slate-900">{score}</p>
      <div className="mt-3 h-2 rounded-full bg-slate-100">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${score}%`, transition: "width 500ms ease" }} />
      </div>
    </div>
  );
}

export default function AnalysisStep({ lang, t, analysisResult, onGenerate, loading }) {
  if (!analysisResult) return null;

  const gapSuggestion = (gap) =>
    lang === "en"
      ? gap.suggestion_en || gap.suggestion_zh || ""
      : gap.suggestion_zh || gap.suggestion_en || "";

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <ScoreCard label={t.overallScore} score={analysisResult.overall_score} color="bg-blue-600" />
        <ScoreCard label={t.skillScore} score={analysisResult.skill_score} color="bg-indigo-600" />
        <ScoreCard label={t.experienceScore} score={analysisResult.experience_score} color="bg-cyan-600" />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-xl bg-white p-4 shadow-sm">
          <h3 className="mb-3 text-base font-semibold text-slate-900">{t.gapsTitle}</h3>
          <div className="space-y-2">
            {analysisResult.gaps.map((gap) => (
              <div key={gap.skill} className="rounded-lg border border-slate-200 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-800">{gap.skill}</span>
                  <span className={`rounded-full px-2 py-1 text-xs ${badgeStyles[gap.importance]}`}>{t[gap.importance]}</span>
                </div>
                <p className="mt-2 text-sm text-slate-600">{gapSuggestion(gap)}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl bg-white p-4 shadow-sm">
          <h3 className="mb-3 text-base font-semibold text-slate-900">{t.keywordsTitle}</h3>
          <div className="flex flex-wrap gap-2">
            {analysisResult.keywords.map((item) => (
              <span
                key={item.word}
                className={`rounded-full px-3 py-1 text-sm ${
                  item.matched ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"
                }`}
              >
                {item.word}
              </span>
            ))}
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={onGenerate}
        disabled={loading}
        className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
      >
        {loading ? t.generating : t.generateResume}
      </button>
    </div>
  );
}
