import { useState, type FormEvent } from "react";
import { createPet } from "../api";
import { useCurrentPet } from "../state/CurrentPetContext";

const PET_SETUP_DRAFT_KEY = "relapaw.petSetup.draft";

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
      <p className="eyebrow">PET PROFILE</p>
      <h1>先认识它</h1>
      <p>先填写最必要的信息，日常基线可以以后慢慢补充。</p>
      <form onSubmit={submit} onChange={(event) => {
        const form = event.currentTarget;
        const values = Object.fromEntries(new FormData(form).entries());
        localStorage.setItem(PET_SETUP_DRAFT_KEY, JSON.stringify(values));
      }}>
        <label>名字<input name="name" required maxLength={100} defaultValue={draft.name} /></label>
        <label>物种<input name="species" required maxLength={50} placeholder="例如：cat / dog" defaultValue={draft.species} /></label>
        <label>品种（可选）<input name="breed" defaultValue={draft.breed} /></label>
        <label>年龄填写方式
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
        {ageMode === "birth_date" && <label>出生日期<input name="birth_date" type="date" defaultValue={draft.birth_date} /></label>}
        {ageMode === "approximate_age" && <label>大约年龄<input name="approximate_age" placeholder="例如：约 1 岁" defaultValue={draft.approximate_age} /></label>}
        <label>性别（可选）<input name="sex" defaultValue={draft.sex} /></label>
        <label>是否绝育<select name="neutered" defaultValue={draft.neutered ?? ""}><option value="">暂不填写</option><option value="yes">是</option><option value="no">否</option></select></label>
        <div className="photo-placeholder" aria-label="宠物照片功能尚未开放">照片上传将在后续阶段开放</div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary" type="submit" disabled={saving}>{saving ? "正在保存…" : "完成建档"}</button>
        <button className="text-button" type="button" onClick={onSkip}>稍后添加</button>
      </form>
    </main>
  );
}
