import { useRef, useState, type FormEvent } from "react";
import { createPet } from "../api";
import { useCurrentPet } from "../state/CurrentPetContext";
import { CroppedSticker, type FirstMeetingSticker } from "./Onboarding";

const PET_SETUP_DRAFT_KEY = "relapaw.petSetup.draft";

function SetupSticker({ name }: { name: FirstMeetingSticker }) {
  return <span className="setup-sticker" aria-hidden="true"><CroppedSticker name={name} /></span>;
}

interface PetSetupDraft {
  name?: string;
  species?: string;
  breed?: string;
  birth_date?: string;
  approximate_age?: string;
  age_mode?: "none" | "birth_date" | "approximate_age";
  sex?: string;
  neutered?: string;
}

function readDraft(): PetSetupDraft {
  try {
    return JSON.parse(localStorage.getItem(PET_SETUP_DRAFT_KEY) ?? "{}") as PetSetupDraft;
  } catch {
    localStorage.removeItem(PET_SETUP_DRAFT_KEY);
    return {};
  }
}

export function PetSetup({ onDone, onSkip }: { onDone: () => void; onSkip: () => void }) {
  const { setCurrentPet } = useCurrentPet();
  const [draft] = useState(readDraft);
  const [ageMode, setAgeMode] = useState<"none" | "birth_date" | "approximate_age">(
    draft.age_mode ?? (draft.birth_date ? "birth_date" : draft.approximate_age ? "approximate_age" : "none"),
  );
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [step, setStep] = useState<1 | 2>(1);
  const [stepMotion, setStepMotion] = useState<"forward" | "back" | "idle">("idle");
  const formRef = useRef<HTMLFormElement>(null);

  function showStep(nextStep: 1 | 2, direction: "forward" | "back") {
    setStep(nextStep);
    setStepMotion(direction);
    window.setTimeout(() => setStepMotion("idle"), 620);
  }

  function continueToDetails() {
    if (formRef.current?.reportValidity()) showStep(2, "forward");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const birthDate = String(data.get("birth_date") || "");
    const approximateAge = String(data.get("approximate_age") || "");
    if (birthDate && approximateAge) {
      setError("出生日期和大约年龄请只填写一项。")
      setSaving(false);
      return;
    }
    try {
      const pet = await createPet({
        name: String(data.get("name")),
        species: String(data.get("species")),
        breed: String(data.get("breed") || "") || undefined,
        birth_date: birthDate || undefined,
        approximate_age: approximateAge || undefined,
        sex: String(data.get("sex") || "") || undefined,
        neutered: data.get("neutered") === "yes" ? true : data.get("neutered") === "no" ? false : undefined,
      });
      localStorage.removeItem(PET_SETUP_DRAFT_KEY);
      setCurrentPet(pet);
      onDone();
    } catch {
      setError("暂时无法创建宠物档案，请稍后重试。")
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="setup-page">
      <header className="setup-intro">
        <p className="eyebrow">OUR FIRST LITTLE PROFILE</p>
        <h1>先认识它</h1>
        <p>不用一次写完。先留下称呼和它是谁，其他小事以后慢慢补。</p>
        <div className="setup-steps" aria-label={`建档第 ${step} 步，共 2 步`}>
          <button type="button" className={step === 1 ? "active" : "complete"} aria-current={step === 1 ? "step" : undefined} onClick={() => step === 2 && showStep(1, "back")}>{step === 2 ? "✓ " : ""}01 相识</button>
          <button type="button" className={step === 2 ? "active" : ""} aria-current={step === 2 ? "step" : undefined} onClick={continueToDetails}>02 小档案</button>
        </div>
      </header>
      <form ref={formRef} onSubmit={submit} onChange={(event) => {
        const form = event.currentTarget;
        const values = Object.fromEntries(new FormData(form).entries());
        localStorage.setItem(PET_SETUP_DRAFT_KEY, JSON.stringify(values));
      }}>
        <section className={`setup-sheet setup-sheet--identity ${step === 1 ? "is-current" : ""} ${stepMotion === "back" ? "setup-sheet--turn-in-back" : ""}`} hidden={step !== 1}>
          <span className="setup-sheet__tape" aria-hidden="true" />
          <div className="setup-sticker-group setup-sticker-group--identity"><SetupSticker name="magnifier"/><SetupSticker name="bowl"/><SetupSticker name="bone"/></div>
          <p className="setup-sheet__number">01 · FIRST MEETING</p>
          <h2>今天怎么称呼它？</h2>
          <label>名字 <span className="field-status">必填</span><input aria-label="名字" name="name" required maxLength={100} defaultValue={draft.name} placeholder="它最熟悉的名字" /></label>
          <label>它是什么小伙伴？ <span className="field-status">必填</span><input aria-label="物种" name="species" required maxLength={50} placeholder="例如：猫、狗、兔子" defaultValue={draft.species} /></label>
          {step === 1 && <button aria-label="继续补充一点" className="primary setup-next" type="button" onClick={continueToDetails}>继续补充一点 <span>→</span></button>}
        </section>
        <section className={`setup-sheet setup-sheet--details ${step === 2 ? "is-current" : ""} ${stepMotion === "forward" ? "setup-sheet--turn-in-forward" : ""}`} hidden={step !== 2}>
        <div className="setup-sticker-group setup-sticker-group--details"><SetupSticker name="flowers"/><SetupSticker name="sparkles"/><SetupSticker name="house"/></div>
        <p className="setup-sheet__number">02 · LITTLE DETAILS</p>
        <h2>还有一些小事</h2>
        <label className="setup-field setup-field--breed">品种（可选）<input name="breed" defaultValue={draft.breed} /></label>
        <label className="setup-field setup-field--age-mode">年龄填写方式
          <select
            name="age_mode"
            value={ageMode}
            onChange={(event) => setAgeMode(event.target.value as typeof ageMode)}
          >
            <option value="none">暂不填写</option>
            <option value="birth_date">填写出生日期</option>
            <option value="approximate_age">填写大约年龄</option>
          </select>
        </label>
        {ageMode === "birth_date" && <label className="setup-field setup-field--age-value">出生日期<input name="birth_date" type="date" defaultValue={draft.birth_date} /></label>}
        {ageMode === "approximate_age" && <label className="setup-field setup-field--age-value">大约年龄<input name="approximate_age" placeholder="例如：约 1 岁" defaultValue={draft.approximate_age} /></label>}
        <label className="setup-field setup-field--sex">性别（可选）<input name="sex" defaultValue={draft.sex} /></label>
        <label className="setup-field setup-field--neutered">是否绝育<select name="neutered" defaultValue={draft.neutered ?? ""}><option value="">暂不填写</option><option value="yes">是</option><option value="no">否</option></select></label>
        <div className="photo-placeholder" aria-label="宠物照片功能尚未开放">照片的位置先空着，之后再一起贴上</div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="setup-form-actions"><button type="button" onClick={() => showStep(1, "back")}>返回</button><button className="primary" type="submit" disabled={saving}>{saving ? "正在保存…" : "完成建档"}</button></div>
        </section>
        <button className="text-button setup-skip" type="button" onClick={onSkip}>稍后添加</button>
      </form>
    </main>
  );
}
