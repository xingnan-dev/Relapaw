import { useEffect, useState, type FormEvent } from "react";
import { useCurrentPet } from "../state/CurrentPetContext";
import { useAuth } from "../state/AuthContext";
import { MemoryBaselinePanel } from "../components/MemoryBaselinePanel";
import { RelationshipTimeline } from "../components/RelationshipTimeline";
import { JournalSticker, PetBotanicalSketch } from "../components/brand";
import { downloadAccountExport, listPets, requestAccountDeletion, updatePet } from "../api";
import type { Pet } from "../types";

type UsPanel = "profile" | "principles" | "privacy" | null;

export function Us({ onAddPet, initialSection = null, onInitialSectionOpened = () => undefined }: { onAddPet: () => void; initialSection?: "memory" | null; onInitialSectionOpened?: () => void }) {
  const { pet, pets, setCurrentPet, clearCurrentPet, retry } = useCurrentPet();
  const { session } = useAuth();
  const [panel, setPanel] = useState<UsPanel>(null);
  const [privacyStatus, setPrivacyStatus] = useState<string | null>(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [profileMode, setProfileMode] = useState<"view" | "edit" | "archive">("view");
  const [profileBusy, setProfileBusy] = useState(false);
  const [profileStatus, setProfileStatus] = useState("");
  const [archivedPets, setArchivedPets] = useState<Pet[]>([]);
  const [archiveListState, setArchiveListState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [ageMode, setAgeMode] = useState<"birth_date" | "approximate_age" | "none">("none");
  useEffect(() => {
    if (initialSection !== "memory") return;
    requestAnimationFrame(() => document.getElementById("memory-title")?.scrollIntoView?.({ behavior: "smooth", block: "start" }));
    onInitialSectionOpened();
  }, [initialSection, onInitialSectionOpened]);
  const togglePanel = (next: Exclude<UsPanel, null>) => setPanel((current) => current === next ? null : next);
  async function loadArchivedPets() {
    setArchiveListState("loading");
    try {
      setArchivedPets((await listPets(true)).filter((item) => item.archived_at));
      setArchiveListState("ready");
    } catch { setArchiveListState("error"); }
  }
  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!pet) return;
    setProfileBusy(true); setProfileStatus("");
    const data = new FormData(event.currentTarget);
    try {
      const updated = await updatePet(pet.id, {
        name: String(data.get("name") || "").trim(),
        species: String(data.get("species") || "").trim(),
        breed: String(data.get("breed") || "").trim() || null,
        birth_date: ageMode === "birth_date" ? String(data.get("birth_date") || "") || null : null,
        approximate_age: ageMode === "approximate_age" ? String(data.get("approximate_age") || "").trim() || null : null,
        sex: String(data.get("sex") || "").trim() || null,
        neutered: data.get("neutered") === "yes" ? true : data.get("neutered") === "no" ? false : null,
      });
      setCurrentPet(updated); setProfileMode("view"); setProfileStatus("资料已保存。");
    } catch { setProfileStatus("保存失败，原资料没有改变。请重试。"); }
    finally { setProfileBusy(false); }
  }
  async function archivePet() {
    if (!pet) return;
    setProfileBusy(true); setProfileStatus("");
    try {
      await updatePet(pet.id, { archived: true });
      clearCurrentPet(); retry(); setProfileMode("view");
    } catch { setProfileStatus("归档失败，宠物档案仍然保留。请重试。"); }
    finally { setProfileBusy(false); }
  }
  async function restorePet(item: Pet) {
    setProfileBusy(true); setProfileStatus("");
    try {
      const restored = await updatePet(item.id, { archived: false });
      setArchivedPets((current) => current.filter((candidate) => candidate.id !== item.id));
      setCurrentPet(restored); setProfileStatus(`${restored.name} 已恢复并设为当前宠物。`);
    } catch { setProfileStatus("恢复失败，归档数据没有改变。请重试。"); }
    finally { setProfileBusy(false); }
  }
  return (
    <section className="us-page" aria-labelledby="us-title">
      <header className="us-hero"><div><p className="eyebrow">US · 我们的关系档案</p><h2 id="us-title">我们</h2><p>不是一份冷冰冰的数据档案，而是你们共同生活留下的纹理。</p><span className="pet-handnote">这些是我们一起留下的</span></div><PetBotanicalSketch scene="us" /></header>
      {pet ? <div className="pet-identity"><div className="pet-avatar">{pet.name.slice(0, 1).toUpperCase()}</div><div><p className="eyebrow">MY COMPANION</p><h3>{pet.name}</h3><p>{[pet.species, pet.breed].filter(Boolean).join(" · ")}</p></div><span className="pet-identity__caption">从相识开始，慢慢记录</span></div> : <div className="card"><h3>还没有宠物档案</h3><button onClick={onAddPet}>添加宠物</button></div>}
      {pet && <MemoryBaselinePanel petId={pet.id} />}
      {pet && <RelationshipTimeline key={`${session?.user_id ?? "anonymous"}:${pet.id}`} pet={pet} pets={pets} />}
      <div className="us-info-grid supporting-models">
        <section className={`card us-disclosure-card us-profile-entry${panel === "profile" ? " is-expanded" : ""}`}>
          <button type="button" className="us-disclosure-trigger" aria-expanded={panel === "profile"} aria-controls="us-profile-detail" onClick={() => togglePanel("profile")}><span><span className="eyebrow">01 · 它的资料页</span><strong>查看它的档案</strong><small>查看当前保存的身份与基本资料</small></span><b aria-hidden="true">⌄</b></button>
          {panel === "profile" && <div id="us-profile-detail" className="us-disclosure-content" aria-live="polite"><JournalSticker name="cat" />{pet ? <>
            {profileMode === "view" && <><dl><dt>名字</dt><dd>{pet.name}</dd><dt>物种</dt><dd>{pet.species || "尚未填写"}</dd><dt>品种</dt><dd>{pet.breed || "尚未填写"}</dd><dt>年龄</dt><dd>{pet.birth_date || pet.approximate_age || "尚未填写"}</dd><dt>性别</dt><dd>{pet.sex || "尚未填写"}</dd></dl><div className="inline-actions"><button type="button" onClick={() => { setAgeMode(pet.birth_date ? "birth_date" : pet.approximate_age ? "approximate_age" : "none"); setProfileMode("edit"); setProfileStatus(""); }}>编辑资料</button><button type="button" onClick={() => { setProfileMode("archive"); setProfileStatus(""); }}>归档档案</button><button type="button" onClick={() => void loadArchivedPets()}>管理已归档档案</button></div></>}
            {profileMode === "edit" && <form onSubmit={saveProfile}><label>名字<input name="name" required maxLength={100} defaultValue={pet.name} /></label><label>物种<input name="species" required maxLength={50} defaultValue={pet.species} /></label><label>品种<input name="breed" defaultValue={pet.breed ?? ""} /></label><label>年龄填写方式<select aria-label="资料年龄填写方式" value={ageMode} onChange={(event) => setAgeMode(event.target.value as typeof ageMode)}><option value="none">暂不填写</option><option value="birth_date">出生日期</option><option value="approximate_age">大约年龄</option></select></label>{ageMode === "birth_date" && <label>出生日期<input name="birth_date" type="date" defaultValue={pet.birth_date ?? ""} /></label>}{ageMode === "approximate_age" && <label>大约年龄<input name="approximate_age" defaultValue={pet.approximate_age ?? ""} /></label>}<label>性别<input name="sex" defaultValue={pet.sex ?? ""} /></label><label>是否绝育<select name="neutered" defaultValue={pet.neutered === true ? "yes" : pet.neutered === false ? "no" : ""}><option value="">暂不填写</option><option value="yes">是</option><option value="no">否</option></select></label><div className="inline-actions"><button type="button" disabled={profileBusy} onClick={() => setProfileMode("view")}>取消</button><button className="primary" type="submit" disabled={profileBusy}>{profileBusy ? "正在保存…" : "保存资料"}</button></div></form>}
            {profileMode === "archive" && <div role="alert"><p>归档后，这只宠物及其记录不会出现在日常工作区；数据不会被删除，后续可以恢复。</p><div className="inline-actions"><button type="button" disabled={profileBusy} onClick={() => setProfileMode("view")}>保留档案</button><button type="button" disabled={profileBusy} onClick={() => void archivePet()}>{profileBusy ? "正在归档…" : `确认归档 ${pet.name}`}</button></div></div>}
            {profileStatus && <p role={profileStatus.includes("失败") ? "alert" : "status"}>{profileStatus}</p>}
            {archiveListState === "loading" && <p role="status">正在读取已归档档案…</p>}
            {archiveListState === "error" && <div role="alert"><p>无法读取已归档档案。</p><button type="button" onClick={() => void loadArchivedPets()}>重试读取归档</button></div>}
            {archiveListState === "ready" && (archivedPets.length === 0 ? <p>没有已归档的宠物档案。</p> : <ul>{archivedPets.map((item) => <li key={item.id}>{item.name} · {item.species} <button type="button" disabled={profileBusy} onClick={() => void restorePet(item)}>恢复 {item.name}</button></li>)}</ul>)}
          </> : <p>还没有建立宠物档案。</p>}</div>}
        </section>
        <section className={`card us-disclosure-card us-principle-card${panel === "principles" ? " is-expanded" : ""}`}>
          <button type="button" className="us-disclosure-trigger" aria-expanded={panel === "principles"} aria-controls="us-principles-detail" onClick={() => togglePanel("principles")}><span><span className="eyebrow">02 · 我们怎样记录</span><strong>记录原则</strong><small>事实与理解分开呈现，不替宠物下心理诊断</small></span><b aria-hidden="true">⌄</b></button>
          {panel === "principles" && <div id="us-principles-detail" className="us-disclosure-content"><JournalSticker name="bow" /><ul><li>先保留亲眼观察到的事实、原话与来源。</li><li>你的理解单独记录，不会被包装成客观结论。</li><li>AI 只提出带证据和不确定性的候选理解。</li></ul></div>}
        </section>
        <section className={`card us-disclosure-card us-principle-card privacy-card${panel === "privacy" ? " is-expanded" : ""}`}>
          <button type="button" className="us-disclosure-trigger" aria-expanded={panel === "privacy"} aria-controls="us-privacy-detail" onClick={() => togglePanel("privacy")}><span><span className="eyebrow">03 · 由你决定保留</span><strong>数据与隐私</strong><small>长期记忆由你决定纳入，也可以随时撤回</small></span><b aria-hidden="true">⌄</b></button>
          {panel === "privacy" && <div id="us-privacy-detail" className="us-disclosure-content"><JournalSticker name="star" /><ul><li>普通记录不会自动成为长期记忆。</li><li>候选内容只有在你确认后才会纳入。</li><li>撤回长期记忆不会改写原始记录与事实来源。</li></ul>
            <div className="privacy-actions"><button type="button" onClick={() => void downloadAccountExport().then(() => setPrivacyStatus("数据副本已开始下载。")).catch(() => setPrivacyStatus("下载失败，请稍后重试。"))}>下载我的数据</button>
            <label>输入 DELETE MY ACCOUNT 以确认<input value={deleteConfirmation} onChange={(event) => setDeleteConfirmation(event.target.value)} /></label>
            <button type="button" disabled={deleteConfirmation !== "DELETE MY ACCOUNT" || deleteBusy} onClick={() => {
              setDeleteBusy(true); setPrivacyStatus(null);
              void requestAccountDeletion().then(() => window.location.reload()).catch(() => {
                setPrivacyStatus("删除请求失败，请稍后重试。"); setDeleteBusy(false);
              });
            }}>{deleteBusy ? "正在提交…" : "请求删除账户"}</button></div>
            {privacyStatus && <p role="status">{privacyStatus}</p>}
          </div>}
        </section>
      </div>
    </section>
  );
}
