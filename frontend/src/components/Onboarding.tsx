import { useState } from "react";

const slides = [
  { title: "Observation ≠ Interpretation", body: "发生了什么，和你认为它为什么这样，是两件不同的事。" },
  { title: "理解变化，而不是替它说话", body: "从日常基线、生活事件与持续观察中，看见真正发生的变化。" },
  { title: "Medical Safety > Behavior Interpretation", body: "Relapaw 不进行疾病诊断，也不替代兽医；安全始终优先。" },
];

export function Onboarding({ onComplete }: { onComplete: () => void }) {
  const [index, setIndex] = useState(0);
  const slide = slides[index];
  return (
    <main className="onboarding">
      <div className="onboarding-progress" aria-label={`第 ${index + 1} 页，共 ${slides.length} 页`}>
        {slides.map((_, step) => <span key={step} className={step === index ? "active" : ""} />)}
      </div>
      <section aria-live="polite">
        <p className="eyebrow">RELAPAW PRINCIPLE</p>
        <h1>{slide.title}</h1>
        <p>{slide.body}</p>
      </section>
      <div className="onboarding-actions">
        <button type="button" className="text-button" onClick={onComplete}>跳过</button>
        {index > 0 && <button type="button" onClick={() => setIndex(index - 1)}>返回</button>}
        <button type="button" className="primary" onClick={() => index === slides.length - 1 ? onComplete() : setIndex(index + 1)}>
          {index === slides.length - 1 ? "开始建立它的档案" : "继续"}
        </button>
      </div>
    </main>
  );
}
