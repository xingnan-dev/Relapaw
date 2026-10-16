import { useEffect, useState } from "react";
import { useCurrentPet } from "../state/CurrentPetContext";
import { MemoryBaselinePanel } from "../components/MemoryBaselinePanel";
import { JournalSticker, PetBotanicalSketch } from "../components/brand";

type UsPanel = "profile" | "principles" | "privacy" | null;

export function Us({ onAddPet, initialSection = null, onInitialSectionOpened = () => undefined }: { onAddPet: () => void; initialSection?: "memory" | null; onInitialSectionOpened?: () => void }) {
  const { pet } = useCurrentPet();
  const [panel, setPanel] = useState<UsPanel>(null);
  useEffect(() => {
    if (initialSection !== "memory") return;
    requestAnimationFrame(() => document.getElementById("memory-title")?.scrollIntoView?.({ behavior: "smooth", block: "start" }));
    onInitialSectionOpened();
  }, [initialSection, onInitialSectionOpened]);
  const togglePanel = (next: Exclude<UsPanel, null>) => setPanel((current) => current === next ? null : next);
  return (
    <section className="us-page" aria-labelledby="us-title">
      <header className="us-hero"><div><p className="eyebrow">US · 我们的关系档案</p><h2 id="us-title">我们</h2><p>不是一份冷冰冰的数据档案，而是你们共同生活留下的纹理。</p><span className="pet-handnote">这些是我们一起留下的</span></div><PetBotanicalSketch scene="us" /></header>
      {pet ? <div className="pet-identity"><div className="pet-avatar">{pet.name.slice(0, 1).toUpperCase()}</div><div><p className="eyebrow">MY COMPANION</p><h3>{pet.name}</h3><p>{[pet.species, pet.breed].filter(Boolean).join(" · ")}</p></div><span className="pet-identity__caption">从相识开始，慢慢记录</span></div> : <div className="card"><h3>还没有宠物档案</h3><button onClick={onAddPet}>添加宠物</button></div>}
      {pet && <MemoryBaselinePanel petId={pet.id} />}
      <div className="us-info-grid supporting-models">
        <section className={`card us-disclosure-card us-profile-entry${panel === "profile" ? " is-expanded" : ""}`}>
          <button type="button" className="us-disclosure-trigger" aria-expanded={panel === "profile"} aria-controls="us-profile-detail" onClick={() => togglePanel("profile")}><span><span className="eyebrow">01 · 它的资料页</span><strong>查看它的档案</strong><small>查看当前保存的身份与基本资料</small></span><b aria-hidden="true">⌄</b></button>
          {panel === "profile" && <div id="us-profile-detail" className="us-disclosure-content" aria-live="polite"><JournalSticker name="cat" />{pet ? <><dl><dt>名字</dt><dd>{pet.name}</dd><dt>物种</dt><dd>{pet.species || "尚未填写"}</dd><dt>品种</dt><dd>{pet.breed || "尚未填写"}</dd></dl><p className="us-disclosure-note">当前仅支持查看；资料编辑将在后续能力中开放。</p></> : <p>还没有建立宠物档案。</p>}</div>}
        </section>
        <section className={`card us-disclosure-card us-principle-card${panel === "principles" ? " is-expanded" : ""}`}>
          <button type="button" className="us-disclosure-trigger" aria-expanded={panel === "principles"} aria-controls="us-principles-detail" onClick={() => togglePanel("principles")}><span><span className="eyebrow">02 · 我们怎样记录</span><strong>记录原则</strong><small>事实与理解分开呈现，不替宠物下心理诊断</small></span><b aria-hidden="true">⌄</b></button>
          {panel === "principles" && <div id="us-principles-detail" className="us-disclosure-content"><JournalSticker name="bow" /><ul><li>先保留亲眼观察到的事实、原话与来源。</li><li>你的理解单独记录，不会被包装成客观结论。</li><li>AI 只提出带证据和不确定性的候选理解。</li></ul></div>}
        </section>
        <section className={`card us-disclosure-card us-principle-card privacy-card${panel === "privacy" ? " is-expanded" : ""}`}>
          <button type="button" className="us-disclosure-trigger" aria-expanded={panel === "privacy"} aria-controls="us-privacy-detail" onClick={() => togglePanel("privacy")}><span><span className="eyebrow">03 · 由你决定保留</span><strong>数据与隐私</strong><small>长期记忆由你决定纳入，也可以随时撤回</small></span><b aria-hidden="true">⌄</b></button>
          {panel === "privacy" && <div id="us-privacy-detail" className="us-disclosure-content"><JournalSticker name="star" /><ul><li>普通记录不会自动成为长期记忆。</li><li>候选内容只有在你确认后才会纳入。</li><li>撤回长期记忆不会改写原始记录与事实来源。</li></ul></div>}
        </section>
      </div>
    </section>
  );
}
