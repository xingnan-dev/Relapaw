import { useEffect, useState, type FormEvent } from "react";
import { ApiError, deleteCaregiverProfile, getCaregiverProfile, saveCaregiverProfile } from "../api";
import type { CaregiverProfile } from "../types";

const EMPTY: CaregiverProfile = {
  living_together_since: null, primary_caregiver: null, household_members: null, daily_routine: null,
  pet_alone_hours: null, pet_care_experience: null, current_concerns: null, explanation_preference: null,
  reminder_preference: null, recording_capacity: null, household_context: null, caregiving_constraints: null,
  interaction_preference: null, observation_preference: null, response_preference: null,
  ai_context_enabled: false, ai_context_fields: null,
};

const AI_FIELDS = [
  ["daily_routine", "作息"], ["pet_alone_hours", "独处时间"], ["pet_care_experience", "养宠经验"],
  ["current_concerns", "当前关心的问题"], ["recording_capacity", "记录与复评能力"],
  ["household_context", "家庭环境"], ["caregiving_constraints", "实际照护限制"],
] as const;

const lines = (value: FormDataEntryValue | null) => String(value || "").split("\n").map((item) => item.trim()).filter(Boolean);
const text = (value: FormDataEntryValue | null) => String(value || "").trim() || null;

export function CaregiverProfilePanel() {
  const [profile, setProfile] = useState<CaregiverProfile>(EMPTY);
  const [state, setState] = useState<"loading" | "ready" | "saving">("loading");
  const [status, setStatus] = useState("");
  useEffect(() => { void getCaregiverProfile().then(setProfile).catch((error) => {
    if (!(error instanceof ApiError && error.status === 404)) setStatus("暂时无法读取照护背景，请稍后重试。");
  }).finally(() => setState("ready")); }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setState("saving"); setStatus("");
    const data = new FormData(event.currentTarget);
    const aiEnabled = data.get("ai_context_enabled") === "on";
    const payload = {
      ...EMPTY,
      living_together_since: text(data.get("living_together_since")), primary_caregiver: text(data.get("primary_caregiver")),
      household_members: lines(data.get("household_members")), daily_routine: text(data.get("daily_routine")),
      pet_alone_hours: text(data.get("pet_alone_hours")) ? Number(data.get("pet_alone_hours")) : null,
      pet_care_experience: text(data.get("pet_care_experience")), current_concerns: text(data.get("current_concerns")),
      explanation_preference: text(data.get("explanation_preference")), reminder_preference: text(data.get("reminder_preference")),
      recording_capacity: text(data.get("recording_capacity")), caregiving_constraints: text(data.get("caregiving_constraints")),
      household_context: { children: data.get("children") === "on", older_adults: data.get("older_adults") === "on", other_pets: data.get("other_pets") === "on" },
      ai_context_enabled: aiEnabled,
      ai_context_fields: aiEnabled ? AI_FIELDS.filter(([key]) => data.get(`ai_${key}`) === "on").map(([key]) => key) : null,
    };
    try { const saved = await saveCaregiverProfile(payload); setProfile(saved); setStatus("照护背景已保存。你可以随时修改、撤回 AI 使用同意或删除。" ); }
    catch { setStatus("保存失败，原有信息没有改变。请重试。" ); }
    finally { setState("ready"); }
  }

  if (state === "loading") return <p role="status">正在读取照护背景…</p>;
  return <form className="caregiver-profile" onSubmit={save}>
    <p>全部为可选项，只用于让提醒与记录方式更贴合现实照护条件；不会据此推断人格或心理状态。</p>
    <label>从什么时候一起生活<small>帮助按共同生活时长解释时间线，不用于给关系贴标签。</small><input type="date" name="living_together_since" defaultValue={profile.living_together_since ?? ""} /></label>
    <label>主要照护者<small>帮助明确提醒应由谁执行。</small><input name="primary_caregiver" maxLength={200} defaultValue={profile.primary_caregiver ?? ""} /></label>
    <label>家庭成员（每行一项）<small>只记录照护相关角色，例如儿童、老人或共同照护者。</small><textarea name="household_members" defaultValue={(profile.household_members ?? []).join("\n")} /></label>
    <label>日常作息<small>用于把观察计划放到真正可执行的时间。</small><textarea name="daily_routine" defaultValue={profile.daily_routine ?? ""} /></label>
    <label>宠物通常独处多久（小时/天）<small>帮助避免提出无法执行的观察安排。</small><input name="pet_alone_hours" type="number" min="0" max="24" step="0.5" defaultValue={profile.pet_alone_hours ?? ""} /></label>
    <label>养宠经验<small>用于选择简短说明或补充基础背景，不评价照护能力。</small><textarea name="pet_care_experience" defaultValue={profile.pet_care_experience ?? ""} /></label>
    <label>当前最关心的问题<small>用于排列记录重点，不能降低任何危险信号等级。</small><textarea name="current_concerns" defaultValue={profile.current_concerns ?? ""} /></label>
    <label>解释偏好<select name="explanation_preference" defaultValue={profile.explanation_preference ?? ""}><option value="">暂不设置</option><option value="简短">简短</option><option value="详细">详细</option></select><small>只改变呈现详略，不改变安全建议。</small></label>
    <label>提醒偏好<input name="reminder_preference" maxLength={100} defaultValue={profile.reminder_preference ?? ""} /><small>用于安排复评提示。</small></label>
    <label>能持续完成什么<small>例如简短记录、拍照或按时复评，用于控制计划负担。</small><textarea name="recording_capacity" defaultValue={profile.recording_capacity ?? ""} /></label>
    <fieldset><legend>必要家庭环境</legend><label><input type="checkbox" name="children" defaultChecked={profile.household_context?.children} />有儿童</label><label><input type="checkbox" name="older_adults" defaultChecked={profile.household_context?.older_adults} />有老人</label><label><input type="checkbox" name="other_pets" defaultChecked={profile.household_context?.other_pets} />有其他宠物</label><small>用于安全和环境提醒，不形成家庭标签。</small></fieldset>
    <label>实际照护限制<small>例如出行、行动或时间限制，用于排除不可行建议。</small><textarea name="caregiving_constraints" defaultValue={profile.caregiving_constraints ?? ""} /></label>
    <fieldset><legend>是否允许 AI 使用所选照护背景</legend><label><input type="checkbox" name="ai_context_enabled" defaultChecked={profile.ai_context_enabled} />我明确同意 AI 在新的辅助请求中使用下列选中信息</label><p>不勾选时，这些内容只保存在档案中，不会进入新的 AI 上下文。撤回后立即停止后续使用。</p>{AI_FIELDS.map(([key, label]) => <label key={key}><input type="checkbox" name={`ai_${key}`} defaultChecked={profile.ai_context_fields?.includes(key)} />{label}</label>)}</fieldset>
    <div className="inline-actions"><button className="primary" disabled={state === "saving"}>{state === "saving" ? "正在保存…" : "保存照护背景"}</button><button type="button" onClick={() => { if (window.confirm("删除全部照护背景？宠物记录不会被删除。")) void deleteCaregiverProfile().then(() => { setProfile(EMPTY); setStatus("照护背景已删除，AI 使用同意也已撤回。" ); }); }}>删除照护背景</button></div>
    {status && <p role={status.includes("失败") || status.includes("无法") ? "alert" : "status"}>{status}</p>}
  </form>;
}
