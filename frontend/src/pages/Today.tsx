import { useCallback, useEffect, useState, type FormEvent } from "react";
import { cancelFollowUp, completeFollowUp, createObservationPlan, listFollowUps, listObservationPlans, updateObservationPlan } from "../api";
import { useCurrentPet } from "../state/CurrentPetContext";
import type { DangerSignal, FollowUp, FollowUpOutcome, ObservationPlan } from "../types";
import { PetBotanicalSketch } from "../components/brand";

const outcomes: Array<[FollowUpOutcome, string]> = [["PERSISTING", "持续"], ["IMPROVED", "改善"], ["WORSENED", "加重"], ["RESOLVED", "已消失"], ["NEW_SIGNS", "新情况"]];
const dangers: Array<[DangerSignal, string]> = [["breathing_difficulty", "呼吸困难"], ["prolonged_seizure", "持续抽搐"], ["collapse_or_unable_to_stand", "昏厥或无法站立"], ["severe_bleeding", "严重出血"], ["suspected_poisoning", "疑似中毒"], ["other_urgent_concern", "其他紧急情况"]];

export function Today({ onAddPet, onUnderstand, onOpenEpisode }: { onAddPet: () => void; onUnderstand: () => void; onOpenEpisode: (episodeId: number) => void }) {
  const { pet, status, retry } = useCurrentPet();
  const [followUps, setFollowUps] = useState<FollowUp[]>([]);
  const [followState, setFollowState] = useState<"loading" | "ready" | "error">("loading");
  const [selected, setSelected] = useState<FollowUp | null>(null);
  const [cancelTarget, setCancelTarget] = useState<FollowUp | null>(null);
  const [actionError, setActionError] = useState("");
  const [plans, setPlans] = useState<ObservationPlan[]>([]);
  const [planState, setPlanState] = useState<"loading" | "ready" | "error">("loading");

  const load = useCallback(async () => {
    if (!pet) { setFollowUps([]); setFollowState("ready"); return; }
    setFollowState("loading");
    try { setFollowUps(await listFollowUps(pet.id)); setFollowState("ready"); }
    catch { setFollowState("error"); }
    setPlanState("loading");
    try { setPlans((await listObservationPlans(pet.id)).filter((item) => item.status === "ACTIVE")); setPlanState("ready"); } catch { setPlanState("error"); }
  }, [pet]);
  useEffect(() => { void load(); }, [load]);

  async function confirmCancel() {
    if (!cancelTarget) return;
    setActionError("");
    try { await cancelFollowUp(cancelTarget.id); setCancelTarget(null); await load(); }
    catch { setActionError("取消复评失败，原待办仍然保留。请重试。"); }
  }

  if (status === "error") return <section><h2>暂时无法读取宠物资料</h2><button onClick={retry}>重试</button></section>;
  if (!pet) return <section className="empty-state" aria-labelledby="today-title"><p className="eyebrow">TODAY</p><h2 id="today-title">从认识它平时的样子开始</h2><p>建立宠物档案后，Relapaw 才能帮助你记录变化，而不是展示伪造的状态。</p><button className="primary" type="button" onClick={onAddPet}>添加我的宠物</button></section>;
  if (selected) return <FollowUpForm followUp={selected} onCancel={() => { setSelected(null); setActionError(""); }} onCompleted={(episodeId) => { setSelected(null); onOpenEpisode(episodeId); }} />;

  const days = Array.from({ length: 7 }, (_, index) => { const date = new Date(); date.setDate(date.getDate() - (6 - index)); return date; });
  return <section className="today-page" aria-labelledby="today-title">
    <p className="eyebrow">TODAY · 今天</p><div className="pet-heading"><div className="pet-avatar" aria-hidden="true">{pet.name.slice(0, 1).toUpperCase()}</div><div><h2 id="today-title">{pet.name}</h2><p>今天，想留意什么？</p></div></div>
    <div className="date-rail" aria-label="最近七天">{days.map((day, index) => <div key={day.toISOString()} className={`date-chip${index === 6 ? " active" : ""}`} aria-current={index === 6 ? "date" : undefined}><span>{day.toLocaleDateString("zh-CN", { weekday: "short" })}</span><strong>{day.getDate()}</strong></div>)}</div>
    <div className="card focus-card"><div className="focus-card__copy"><p className="eyebrow">从真实发生的事开始</p><h3>记下一刻</h3><p>先写下真实发生的事，再记录你的理解。</p><span className="pet-handnote">这个先记下来</span><button type="button" aria-label="快速记录" onClick={onUnderstand}>开始记录</button></div><PetBotanicalSketch scene="today" /></div>
    <section className="today-followups" aria-labelledby="follow-up-title"><p className="eyebrow">REVISIT</p><h3 id="follow-up-title">回来看看</h3>
      {followState === "loading" && <p role="status">正在读取待复评项目…</p>}
      {followState === "error" && <div role="alert"><p>暂时无法读取待复评项目。</p><button onClick={() => void load()}>重试待复评</button></div>}
      {followState === "ready" && followUps.length === 0 && <div className="today-empty-action"><p role="status">今天没有需要回看的记录。</p><small>从某条记录安排复评后，到期提醒会出现在这里。</small></div>}
      {actionError && <p role="alert" className="form-error">{actionError}</p>}
      {followUps.map((item) => <article className="card" key={item.id}><p className="eyebrow">{item.timing_status === "OVERDUE" ? "已逾期" : "今日到期"}</p><h3>{item.source_episode_type}</h3><p>{item.source_raw_owner_input}</p><small>计划时间：{new Date(item.scheduled_at).toLocaleString()}</small><div className="panel-actions"><button onClick={() => onOpenEpisode(item.source_episode_id)}>查看原记录</button><button onClick={() => setSelected(item)}>开始复评</button><button className="danger-button" onClick={() => setCancelTarget(item)}>取消复评</button></div></article>)}
    </section>
    {cancelTarget && <section role="dialog" aria-modal="true" aria-labelledby="cancel-follow-up-title" className="card"><h3 id="cancel-follow-up-title">取消这次复评？</h3><p>取消后不会创建新记录，原 Episode 保持不变。</p><div className="panel-actions"><button onClick={() => setCancelTarget(null)}>返回</button><button className="danger-button" onClick={() => void confirmCancel()}>确认取消复评</button></div></section>}
    <PlanSection petId={pet.id} plans={plans} state={planState} reload={load} />
  </section>;
}

function PlanSection({ petId, plans, state, reload }: { petId: number; plans: ObservationPlan[]; state: "loading" | "ready" | "error"; reload: () => Promise<void> }) {
  const [creating, setCreating] = useState(false); const [goal, setGoal] = useState(""); const [item, setItem] = useState(""); const [error, setError] = useState(""); const [cancelId, setCancelId] = useState<number | null>(null);
  async function create(event: FormEvent) { event.preventDefault(); setError(""); if (!goal.trim() || !item.trim()) { setError("请填写观察目标和至少一个观察项目。"); return; } const start = new Date(); const end = new Date(start.getTime() + 7 * 86400000); try { await createObservationPlan(petId, { status: "ACTIVE", start_at: start.toISOString(), end_at: end.toISOString(), goal: goal.trim(), items: [{ label: item.trim(), is_required: true }] }); setCreating(false); setGoal(""); setItem(""); await reload(); } catch { setError("计划保存失败，输入仍保留。请重试。"); } }
  async function transition(id: number, status: "COMPLETED" | "CANCELLED") { setError(""); try { await updateObservationPlan(id, status); setCancelId(null); await reload(); } catch { setError("计划状态更新失败，请重试。"); } }
  return <section className="card" aria-labelledby="plan-title"><p className="eyebrow">OBSERVATION</p><h3 id="plan-title">一段观察</h3>{state === "loading" && <p role="status">正在读取观察计划…</p>}{state === "error" && <div role="status"><p>暂时无法读取观察计划。</p><button onClick={() => void reload()}>重试计划</button></div>}{state === "ready" && !plans.length && <p>还没有正在进行的观察。</p>}{plans.map((plan) => <article key={plan.id}><strong>{plan.goal}</strong><ul>{plan.items.map((entry) => <li key={entry.id}>{entry.label}</li>)}</ul><div className="panel-actions"><button onClick={() => void transition(plan.id, "COMPLETED")}>完成计划</button><button className="danger-button" onClick={() => setCancelId(plan.id)}>取消计划</button></div></article>)}{cancelId && <div role="dialog" aria-modal="true"><p>确认取消这个观察计划？已有记录不会删除。</p><button onClick={() => setCancelId(null)}>返回</button><button onClick={() => void transition(cancelId, "CANCELLED")}>确认取消计划</button></div>}{creating ? <form onSubmit={(event) => void create(event)}><label>观察目标<input aria-label="观察目标" value={goal} onChange={(event) => setGoal(event.target.value)} /></label><label>观察项目<input aria-label="观察项目" value={item} onChange={(event) => setItem(event.target.value)} /></label>{error && <p role="alert">{error}</p>}<button type="button" onClick={() => setCreating(false)}>取消创建</button><button>保存计划</button></form> : <button aria-label="创建观察计划" onClick={() => setCreating(true)}>开始一段观察</button>}</section>;
}

function FollowUpForm({ followUp, onCancel, onCompleted }: { followUp: FollowUp; onCancel: () => void; onCompleted: (episodeId: number) => void }) {
  const [outcome, setOutcome] = useState<FollowUpOutcome>("PERSISTING");
  const [raw, setRaw] = useState(""); const [observation, setObservation] = useState(""); const [interpretation, setInterpretation] = useState("");
  const [urgent, setUrgent] = useState(false); const [signals, setSignals] = useState<DangerSignal[]>([]);
  const [error, setError] = useState(""); const [submitting, setSubmitting] = useState(false);
  function toggle(signal: DangerSignal) { setSignals((current) => current.includes(signal) ? current.filter((item) => item !== signal) : [...current, signal]); }
  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    if (!raw.trim() || !observation.trim()) { setError("请填写原始输入和至少一条 Observation。"); return; }
    if (urgent && signals.length === 0) { setError("请选择至少一个需要联系兽医的情况。"); return; }
    setSubmitting(true);
    try {
      const now = new Date().toISOString();
      const result = await completeFollowUp(followUp.id, { outcome, happened_at: now, episode_type: "follow_up", raw_owner_input: raw.trim(), observations: [{ behavior_type: "follow_up_observation", description: observation.trim(), source_type: "owner_direct" }], owner_interpretations: interpretation.trim() ? [{ interpretation: interpretation.trim() }] : [], safety_check: { result: urgent ? "ESCALATE_TO_VET" : "NORMAL", danger_signals: urgent ? signals : [], acknowledged_at: now } });
      onCompleted(result.id);
    } catch { setError("保存复评失败，输入仍保留。请检查网络后重试。"); }
    finally { setSubmitting(false); }
  }
  return <section aria-labelledby="complete-follow-up-title"><button onClick={onCancel}>返回 Today</button><p className="eyebrow">FOLLOW-UP</p><h2 id="complete-follow-up-title">完成复评</h2><div className="card"><h3>原记录</h3><p>{followUp.source_raw_owner_input}</p><small>计划复评：{new Date(followUp.scheduled_at).toLocaleString()}</small></div>
    <form className="editor-form" onSubmit={(event) => void submit(event)}><fieldset className="form-section"><legend>复评结果</legend>{outcomes.map(([value, label]) => <label className="choice-row" key={value}><input type="radio" name="outcome" checked={outcome === value} onChange={() => setOutcome(value)} />{label}</label>)}</fieldset>
      <label>原始输入<textarea aria-label="复评原始输入" value={raw} onChange={(event) => setRaw(event.target.value)} /></label><div className="lens-grid"><label className="lens-card">发生了什么（Observation）<textarea aria-label="复评 Observation" value={observation} onChange={(event) => setObservation(event.target.value)} /></label><label className="lens-card interpretation">你的理解（Owner Interpretation）<textarea aria-label="复评 Owner Interpretation" value={interpretation} onChange={(event) => setInterpretation(event.target.value)} /></label></div>
      <fieldset className="form-section safety-section"><legend>人工 Safety Check</legend><p className="safety-note">请按当前实际情况重新检查；Relapaw 不进行诊断，也不替代兽医。</p><label className="choice-row"><input type="checkbox" checked={urgent} onChange={(event) => { setUrgent(event.target.checked); if (!event.target.checked) setSignals([]); }} />存在需要尽快联系兽医的情况</label>{urgent && <div className="danger-panel" role="alert"><strong>请尽快联系兽医</strong><p>Relapaw 不进行诊断，也不替代兽医。</p>{dangers.map(([value, label]) => <label className="choice-row" key={value}><input type="checkbox" checked={signals.includes(value)} onChange={() => toggle(value)} />{label}</label>)}</div>}</fieldset>
      {error && <p role="alert" className="form-error">{error}</p>}<div className="panel-actions"><button type="button" onClick={onCancel}>取消</button><button className="primary" disabled={submitting}>{submitting ? "正在保存…" : "保存复评"}</button></div>
    </form></section>;
}
