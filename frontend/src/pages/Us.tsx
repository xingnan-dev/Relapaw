import { useEffect, useRef, useState, type FormEvent } from "react";
import { useCurrentPet } from "../state/CurrentPetContext";
import { useAuth } from "../state/AuthContext";
import { MemoryBaselinePanel } from "../components/MemoryBaselinePanel";
import { RelationshipTimeline } from "../components/RelationshipTimeline";
import { JournalSticker, PetBotanicalSketch } from "../components/brand";
import { CaregiverProfilePanel } from "../components/CaregiverProfile";
import { deletePetAvatar, downloadAccountExport, listPets, petAvatarUrl, requestAccountDeletion, updatePet, uploadPetAvatar } from "../api";
import type { Pet } from "../types";
import { PET_IMAGE_ACCEPT, validatePetImageSelection } from "../platform/petImage";

type UsPanel = "profile" | "caregiver" | "principles" | "privacy" | null;

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
  const panelReturnFocus = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (initialSection !== "memory") return;
    requestAnimationFrame(() => document.getElementById("memory-title")?.scrollIntoView?.({ behavior: "smooth", block: "start" }));
    onInitialSectionOpened();
  }, [initialSection, onInitialSectionOpened]);
  useEffect(() => {
    if (!panel) return;
    const dialog = document.querySelector<HTMLElement>(".us-disclosure-content[role='dialog']");
    const scroller = dialog?.closest<HTMLElement>(".page-transition");
    const previousOverflow = scroller?.style.overflow ?? "";
    if (scroller) scroller.style.overflow = "hidden";
    const focusable = () => Array.from(dialog?.querySelectorAll<HTMLElement>("button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex='-1'])") ?? []);
    focusable()[0]?.focus();
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setPanel(null);
        panelReturnFocus.current?.focus();
        return;
      }
      if (event.key !== "Tab") return;
      const items = focusable();
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("keydown", handleKey);
      if (scroller) scroller.style.overflow = previousOverflow;
    };
  }, [panel]);
  const closePanel = () => {
    setPanel(null);
    panelReturnFocus.current?.focus();
  };
  const togglePanel = (next: Exclude<UsPanel, null>, trigger: HTMLElement) => {
    if (panel === next) { closePanel(); return; }
    panelReturnFocus.current = trigger;
    setPanel(next);
  };
  const openSupportingPanel = (next: Exclude<UsPanel, null>, id: string, trigger?: HTMLElement) => {
    panelReturnFocus.current = trigger ?? (document.activeElement instanceof HTMLElement ? document.activeElement : document.getElementById(id));
    setPanel(next);
  };
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
        weight_kg: data.get("weight_kg") ? Number(data.get("weight_kg")) : null,
        known_conditions: String(data.get("known_conditions") || "").split("\n").map((item) => item.trim()).filter(Boolean),
        medications: String(data.get("medications") || "").split("\n").map((item) => item.trim()).filter(Boolean),
        allergies: String(data.get("allergies") || "").split("\n").map((item) => item.trim()).filter(Boolean),
        living_environment: String(data.get("living_environment") || "").trim() || null,
        owner_observations: Object.fromEntries(["feeding", "drinking", "sleep", "elimination", "activity", "social", "likes", "avoids", "triggers"].map((key) => [key, String(data.get(`observation_${key}`) || "").trim()]).filter(([, value]) => value)),
      });
      setCurrentPet(updated); setProfileMode("view"); setProfileStatus("资料已保存。");
    } catch { setProfileStatus("保存失败，原资料没有改变。请重试。"); }
    finally { setProfileBusy(false); }
  }
  async function replaceAvatar(file: File) {
    if (!pet) return;
    const selectionError = validatePetImageSelection(file);
    if (selectionError) { setProfileStatus(selectionError); return; }
    setProfileBusy(true); setProfileStatus("");
    try { const avatar = await uploadPetAvatar(pet.id, file); setCurrentPet({ ...pet, avatar }); setProfileStatus("头像已更新。" ); }
    catch { setProfileStatus("头像上传失败。请确认图片格式和大小后重试。" ); }
    finally { setProfileBusy(false); }
  }
  async function removeAvatar() {
    if (!pet) return;
    setProfileBusy(true);
    try { await deletePetAvatar(pet.id); setCurrentPet({ ...pet, avatar: null }); setProfileStatus("头像已删除，已恢复默认头像。" ); }
    catch { setProfileStatus("头像删除失败，请重试。" ); }
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
      {panel && <div className="us-dialog-backdrop" aria-hidden="true" />}
      <header className="us-hero"><div><p className="eyebrow">US · 我们的关系档案</p><h2 id="us-title">我们</h2><p>不是一份冷冰冰的数据档案，而是你们共同生活留下的纹理。</p><span className="pet-handnote">这些是我们一起留下的</span></div><PetBotanicalSketch scene="us" /></header>
      <nav className="us-layer-nav" aria-label="我们页面分区"><a href="#pet-profile-layer"><strong>宠物档案</strong><small>它是谁、平时是什么样</small></a><a href="#long-change-layer"><strong>长期变化</strong><small>生活事件与多次记录</small></a><a href="#relationship-family-layer"><strong>关系与家庭</strong><small>互动事实与照护背景</small></a></nav>
      <section id="pet-profile-layer" className="us-layer" aria-labelledby="pet-profile-layer-title"><header><p className="eyebrow">01 · 宠物档案</p><h3 id="pet-profile-layer-title">它是谁，平时是什么样</h3><p>身份和客观资料由你维护；日常模式不会与系统候选混在一起。</p></header>
        {pet ? <><div className="pet-identity"><div className="pet-avatar">{pet.avatar ? <img src={petAvatarUrl(pet.id, pet.avatar.updated_at)} alt={`${pet.name} 的头像`} /> : pet.name.slice(0, 1).toUpperCase()}</div><div><p className="eyebrow">我的伙伴</p><h4>{pet.name}</h4><p>{[pet.species, pet.breed].filter(Boolean).join(" · ")}</p></div><span className="pet-identity__caption">从相识开始，慢慢记录</span></div><button type="button" onClick={(event) => openSupportingPanel("profile", "us-profile-card", event.currentTarget)}>查看或编辑完整档案</button><button type="button" onClick={onAddPet}>添加另一只宠物</button><MemoryBaselinePanel petId={pet.id} section="profile" /></> : <div className="card"><h4>还没有宠物档案</h4><button onClick={onAddPet}>添加宠物</button></div>}
      </section>
      <section id="long-change-layer" className="us-layer" aria-labelledby="long-change-layer-title"><header><p className="eyebrow">02 · 长期变化</p><h3 id="long-change-layer-title">把多次记录放回时间里</h3><p>只总结已有记录的范围、数量和来源；样本不足时不会生成趋势。</p></header>{pet ? <MemoryBaselinePanel petId={pet.id} section="changes" /> : <p>建立宠物档案后，这里会呈现长期变化。</p>}</section>
      <section id="relationship-family-layer" className="us-layer" aria-labelledby="relationship-family-layer-title"><header><p className="eyebrow">03 · 关系与家庭</p><h3 id="relationship-family-layer-title">一起生活的人、动物与情境</h3><p>关系只记录可观察互动；家庭背景全部可选，不用于心理侧写。</p></header>{pet && <RelationshipTimeline key={`${session?.user_id ?? "anonymous"}:${pet.id}`} pet={pet} pets={pets} />}<button type="button" onClick={(event) => openSupportingPanel("caregiver", "us-caregiver-card", event.currentTarget)}>查看照护背景与偏好</button></section>
      <div className="us-info-grid supporting-models">
        <section id="us-profile-card" className={`card us-disclosure-card us-profile-entry${panel === "profile" ? " is-expanded" : ""}`}>
          <button type="button" className="us-disclosure-trigger" aria-expanded={panel === "profile"} aria-controls="us-profile-detail" onClick={(event) => togglePanel("profile", event.currentTarget)}><span><span className="eyebrow">01 · 它的资料页</span><strong>查看它的档案</strong><small>查看当前保存的身份与基本资料</small></span><b aria-hidden="true">⌄</b></button>
          {panel === "profile" && <div id="us-profile-detail" className="us-disclosure-content" role="dialog" aria-modal="true" aria-label="宠物完整档案"><button type="button" className="us-dialog-close" onClick={closePanel}>关闭</button><JournalSticker name="cat" />{pet ? <>
            {profileMode === "view" && <><dl><dt>名字</dt><dd>{pet.name}</dd><dt>物种</dt><dd>{pet.species || "尚未填写"}</dd><dt>品种</dt><dd>{pet.breed || "尚未填写"}</dd><dt>年龄</dt><dd>{pet.birth_date || pet.approximate_age || "尚未填写"}</dd><dt>性别</dt><dd>{pet.sex || "尚未填写"}</dd><dt>体重</dt><dd>{pet.weight_kg ? `${pet.weight_kg} kg` : "尚未填写"}</dd><dt>生活环境</dt><dd>{pet.living_environment || "尚未填写"}</dd><dt>健康背景</dt><dd>{[...(pet.known_conditions ?? []), ...(pet.medications ?? []), ...(pet.allergies ?? [])].join("；") || "尚未填写"}</dd><dt>主人日常观察</dt><dd>{Object.values(pet.owner_observations ?? {}).join("；") || "尚未填写"}</dd></dl><label>替换头像<input type="file" accept={PET_IMAGE_ACCEPT} disabled={profileBusy} onChange={(event) => { const file = event.target.files?.[0]; if (file) void replaceAvatar(file); }} /></label>{pet.avatar && <button type="button" disabled={profileBusy} onClick={() => void removeAvatar()}>删除头像</button>}<div className="inline-actions"><button type="button" onClick={() => { setAgeMode(pet.birth_date ? "birth_date" : pet.approximate_age ? "approximate_age" : "none"); setProfileMode("edit"); setProfileStatus(""); }}>编辑资料</button><button type="button" onClick={() => { setProfileMode("archive"); setProfileStatus(""); }}>归档档案</button><button type="button" onClick={() => void loadArchivedPets()}>管理已归档档案</button></div></>}
            {profileMode === "edit" && <form onSubmit={saveProfile}><h4>客观资料</h4><label>名字<input name="name" required maxLength={100} defaultValue={pet.name} /></label><label>物种<input name="species" required maxLength={50} defaultValue={pet.species} /></label><label>品种<input name="breed" defaultValue={pet.breed ?? ""} /></label><label>年龄填写方式<select aria-label="资料年龄填写方式" value={ageMode} onChange={(event) => setAgeMode(event.target.value as typeof ageMode)}><option value="none">暂不填写</option><option value="birth_date">出生日期</option><option value="approximate_age">大约年龄</option></select></label>{ageMode === "birth_date" && <label>出生日期<input name="birth_date" type="date" defaultValue={pet.birth_date ?? ""} /></label>}{ageMode === "approximate_age" && <label>大约年龄<input name="approximate_age" defaultValue={pet.approximate_age ?? ""} /></label>}<label>性别<input name="sex" defaultValue={pet.sex ?? ""} /></label><label>是否绝育<select name="neutered" defaultValue={pet.neutered === true ? "yes" : pet.neutered === false ? "no" : ""}><option value="">暂不填写</option><option value="yes">是</option><option value="no">否</option></select></label><label>体重（kg）<input name="weight_kg" type="number" min="0.01" max="500" step="0.01" defaultValue={pet.weight_kg ?? ""} /></label><label>已知疾病（每行一项）<textarea name="known_conditions" defaultValue={(pet.known_conditions ?? []).join("\n")} /></label><label>用药（每行一项）<textarea name="medications" defaultValue={(pet.medications ?? []).join("\n")} /></label><label>过敏（每行一项）<textarea name="allergies" defaultValue={(pet.allergies ?? []).join("\n")} /></label><label>生活环境<textarea name="living_environment" defaultValue={pet.living_environment ?? ""} /></label><h4>主人观察</h4>{[["feeding","饮食"],["drinking","饮水"],["sleep","睡眠"],["elimination","排泄"],["activity","活动"],["social","对人和动物的反应"],["likes","喜欢"],["avoids","回避"],["triggers","已知触发情境"]].map(([key,label]) => <label key={key}>{label}<textarea name={`observation_${key}`} defaultValue={pet.owner_observations?.[key] ?? ""} /></label>)}<p>系统候选理解会根据多次记录另行呈现，绝不会覆盖这里的客观资料或主人观察。</p><div className="inline-actions"><button type="button" disabled={profileBusy} onClick={() => setProfileMode("view")}>取消</button><button className="primary" type="submit" disabled={profileBusy}>{profileBusy ? "正在保存…" : "保存资料"}</button></div></form>}
            {profileMode === "archive" && <div role="alert"><p>归档后，这只宠物及其记录不会出现在日常工作区；数据不会被删除，后续可以恢复。</p><div className="inline-actions"><button type="button" disabled={profileBusy} onClick={() => setProfileMode("view")}>保留档案</button><button type="button" disabled={profileBusy} onClick={() => void archivePet()}>{profileBusy ? "正在归档…" : `确认归档 ${pet.name}`}</button></div></div>}
          </> : <><p>当前没有启用的宠物档案。</p><button type="button" onClick={() => void loadArchivedPets()}>管理已归档档案</button></>}
            {profileStatus && <p role={profileStatus.includes("失败") ? "alert" : "status"}>{profileStatus}</p>}
            {archiveListState === "loading" && <p role="status">正在读取已归档档案…</p>}
            {archiveListState === "error" && <div role="alert"><p>无法读取已归档档案。</p><button type="button" onClick={() => void loadArchivedPets()}>重试读取归档</button></div>}
            {archiveListState === "ready" && (archivedPets.length === 0 ? <p>没有已归档的宠物档案。</p> : <ul>{archivedPets.map((item) => <li key={item.id}>{item.name} · {item.species} <button type="button" disabled={profileBusy} onClick={() => void restorePet(item)}>恢复 {item.name}</button></li>)}</ul>)}
          </div>}
        </section>
        <section id="us-caregiver-card" className={`card us-disclosure-card${panel === "caregiver" ? " is-expanded" : ""}`}>
          <button type="button" className="us-disclosure-trigger" aria-expanded={panel === "caregiver"} aria-controls="us-caregiver-detail" onClick={(event) => togglePanel("caregiver", event.currentTarget)}><span><span className="eyebrow">02 · 照护背景</span><strong>照护背景与偏好</strong><small>全部可选；说明现实条件，不做心理侧写</small></span><b aria-hidden="true">⌄</b></button>
          {panel === "caregiver" && <div id="us-caregiver-detail" className="us-disclosure-content" role="dialog" aria-modal="true" aria-label="照护背景与偏好"><button type="button" className="us-dialog-close" onClick={closePanel}>关闭</button><CaregiverProfilePanel /></div>}
        </section>
        <section className={`card us-disclosure-card us-principle-card${panel === "principles" ? " is-expanded" : ""}`}>
          <button type="button" className="us-disclosure-trigger" aria-expanded={panel === "principles"} aria-controls="us-principles-detail" onClick={(event) => togglePanel("principles", event.currentTarget)}><span><span className="eyebrow">02 · 我们怎样记录</span><strong>记录原则</strong><small>事实与理解分开呈现，不替宠物下心理诊断</small></span><b aria-hidden="true">⌄</b></button>
          {panel === "principles" && <div id="us-principles-detail" className="us-disclosure-content" role="dialog" aria-modal="true" aria-label="记录原则"><button type="button" className="us-dialog-close" onClick={closePanel}>关闭</button><JournalSticker name="bow" /><ul><li>先保留亲眼观察到的事实、原话与来源。</li><li>你的理解单独记录，不会被包装成客观结论。</li><li>AI 只提出带证据和不确定性的候选理解。</li></ul></div>}
        </section>
        <section className={`card us-disclosure-card us-principle-card privacy-card${panel === "privacy" ? " is-expanded" : ""}`}>
          <button type="button" className="us-disclosure-trigger" aria-expanded={panel === "privacy"} aria-controls="us-privacy-detail" onClick={(event) => togglePanel("privacy", event.currentTarget)}><span><span className="eyebrow">03 · 由你决定保留</span><strong>数据与隐私</strong><small>长期记忆由你决定纳入，也可以随时撤回</small></span><b aria-hidden="true">⌄</b></button>
          {panel === "privacy" && <div id="us-privacy-detail" className="us-disclosure-content" role="dialog" aria-modal="true" aria-label="数据与隐私"><button type="button" className="us-dialog-close" onClick={closePanel}>关闭</button><JournalSticker name="star" /><ul><li>普通记录不会自动成为长期记忆。</li><li>候选内容只有在你确认后才会纳入。</li><li>撤回长期记忆不会改写原始记录与事实来源。</li></ul>
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
