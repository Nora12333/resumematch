export default function StepIndicator({ steps, currentStep }) {
  return (
    <div className="mb-6 flex items-center gap-3">
      {steps.map((step, idx) => {
        const stepNo = idx + 1;
        const active = stepNo === currentStep;
        const completed = stepNo < currentStep;
        return (
          <div key={step} className="flex items-center gap-3">
            <div
              className={`flex h-8 w-8 items-center justify-center rounded-full border text-sm font-semibold ${
                active || completed
                  ? "border-blue-600 bg-blue-600 text-white"
                  : "border-slate-300 bg-white text-slate-500"
              }`}
            >
              {stepNo}
            </div>
            <span className={`${active ? "text-slate-900" : "text-slate-500"} text-sm`}>{step}</span>
            {idx < steps.length - 1 && <div className="h-px w-8 bg-slate-300" />}
          </div>
        );
      })}
    </div>
  );
}
