import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { createCompleteEpisode, listObservationPlans } from "../api";
import { useCurrentPet } from "../state/CurrentPetContext";
import type { BehaviorCategory, DangerSignal, MeasurementUnit, ObservationPlan } from "../types";
import { JournalSticker, PetBotanicalSketch } from "../components/brand";
import { useAuth } from "../state/AuthContext";

const dangerOptions: Array<{ value: DangerSignal; label: string }> = [
  { value: "breathing_difficulty", label: "呼吸困难" },
  { value: "prolonged_seizure", label: "持续抽搐" },
  { value: "collapse_or_unable_to_stand", label: "昏厥或无法站立" },
  { value: "severe_bleeding", label: "严重出血" },
  { value: "suspected_poisoning", label: "疑似中毒" },
  { value: "other_urgent_concern", label: "其他紧急情况" },
];

type RecordStep = "record-input" | "record-facts" | "record-meaning" | "record-safety" | "record-save";
type DraftStatus = "none" | "restored" | "saved" | "unavailable";

interface RecordDraft {
  happenedAt: string; episodeType: string; rawInput: string; observation: string;
  behaviorCategory: BehaviorCategory; measuredValue: string; measurementUnit: MeasurementUnit;
  interpretation: string; location: string; triggerContext: string; durationMinutes: string;
  frequency: string; intensity: string; urgent: boolean; dangerSignals: DangerSignal[];
  otherConcern: string; planId: string; savedAt: string;
}

function draftKey(userId: string, petId: number) { return `relapaw.recordDraft.v1:${userId}:${petId}`; }
function safeReadDraft(key: string): RecordDraft | null {
  try {
    const value = JSON.parse(localStorage.getItem(key) ?? "null") as unknown;
    if (!value || typeof value !== "object") return null;
    const item = value as Partial<RecordDraft>;
    const categories: BehaviorCategory[] = ["ACTIVITY", "FEEDING", "RESTING", "SOCIAL", "ELIMINATION", "VOCALIZATION", "GROOMING", "MOBILITY", "OTHER"];
    const units: MeasurementUnit[] = ["seconds", "minutes", "count", "meters", "grams", "milliliters"];
    if (typeof item.rawInput !== "string" || typeof item.observation !== "string" || typeof item.happenedAt !== "string" || typeof item.episodeType !== "string") return null;
    if (!categories.includes(item.behaviorCategory as BehaviorCategory) || !units.includes(item.measurementUnit as MeasurementUnit)) return null;
    if (!Array.isArray(item.dangerSignals)) return null;
    return item as RecordDraft;
  } catch { return null; }
}
function safeRemoveDraft(key: string) { try { localStorage.removeItem(key); } catch { /* saving status already explains unavailable storage */ } }

function localDateTimeValue() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

function planRange(plan: ObservationPlan): string {
  if (!plan.start_at && !plan.end_at) return "未设置时间范围";
  const format = (value: string | null) => value ? new Date(value).toLocaleDateString() : "不限";
  return `${format(plan.start_at)} 至 ${format(plan.end_at)}`;
}

export function Understand({ onSaved, onCreatePlan = () => undefined, onDirtyChange = () => undefined, onSubmittingChange = () => undefined }: { onSaved: (episodeId: number) => void; onCreatePlan?: () => void; onDirtyChange?: (dirty: boolean) => void; onSubmittingChange?: (submitting: boolean) => void }) {
  const { pet } = useCurrentPet();
  const { session } = useAuth();
  const draftOwnerId = session?.user_id ?? "local-session";
  const [happenedAt, setHappenedAt] = useState(localDateTimeValue);
  const [episodeType, setEpisodeType] = useState("behavior_change");
  const [rawInput, setRawInput] = useState("");
  const [observation, setObservation] = useState("");
  const [behaviorCategory, setBehaviorCategory] = useState<BehaviorCategory>("ACTIVITY");
  const [measuredValue, setMeasuredValue] = useState("");
  const [measurementUnit, setMeasurementUnit] = useState<MeasurementUnit>("seconds");
  const [interpretation, setInterpretation] = useState("");
  const [location, setLocation] = useState("");
  const [triggerContext, setTriggerContext] = useState("");
  const [durationMinutes, setDurationMinutes] = useState("");
  const [frequency, setFrequency] = useState("");
  const [intensity, setIntensity] = useState("");
  const [urgent, setUrgent] = useState(false);
  const [dangerSignals, setDangerSignals] = useState<DangerSignal[]>([]);
  const [otherConcern, setOtherConcern] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [plans, setPlans] = useState<ObservationPlan[]>([]);
  const [planState, setPlanState] = useState<"loading" | "ready" | "error">("loading");
  const [planId, setPlanId] = useState("");
  const [activeStep, setActiveStep] = useState<RecordStep>("record-input");
  const [hydratedScope, setHydratedScope] = useState("");
  const [draftStatus, setDraftStatus] = useState<DraftStatus>("none");
  const [draftSavedAt, setDraftSavedAt] = useState("");
  const hydratedDraftSignature = useRef("");
  const initialHappenedAt = useRef(happenedAt);
  const currentDraftScope = pet ? draftKey(draftOwnerId, pet.id) : "";
  const isDirty = draftStatus === "restored" || Boolean(rawInput || observation || measuredValue || interpretation || location || triggerContext || durationMinutes || frequency || intensity || urgent || dangerSignals.length || otherConcern || planId || episodeType !== "behavior_change" || behaviorCategory !== "ACTIVITY" || happenedAt !== initialHappenedAt.current);
  useEffect(() => {
    onDirtyChange(isDirty);
    return () => onDirtyChange(false);
  }, [isDirty, onDirtyChange]);
  useEffect(() => {
    if (!pet) { setHydratedScope(""); return; }
    const scope = draftKey(draftOwnerId, pet.id);
    const draft = safeReadDraft(scope);
    const restoredHappenedAt = draft?.happenedAt || localDateTimeValue(); initialHappenedAt.current = restoredHappenedAt;
    setHappenedAt(restoredHappenedAt); setEpisodeType(draft?.episodeType || "behavior_change");
    setRawInput(draft?.rawInput || ""); setObservation(draft?.observation || ""); setBehaviorCategory(draft?.behaviorCategory || "ACTIVITY");
    setMeasuredValue(draft?.measuredValue || ""); setMeasurementUnit(draft?.measurementUnit || "seconds"); setInterpretation(draft?.interpretation || "");
    setLocation(draft?.location || ""); setTriggerContext(draft?.triggerContext || ""); setDurationMinutes(draft?.durationMinutes || "");
    setFrequency(draft?.frequency || ""); setIntensity(draft?.intensity || ""); setUrgent(draft?.urgent || false);
    setDangerSignals(draft?.dangerSignals || []); setOtherConcern(draft?.otherConcern || ""); setPlanId(draft?.planId || "");
    hydratedDraftSignature.current = draft ? JSON.stringify({ ...draft, savedAt: undefined }) : "";
    setDraftSavedAt(draft?.savedAt || ""); setDraftStatus(draft ? "restored" : "none"); setHydratedScope(scope);
  }, [pet?.id, draftOwnerId]);
  useEffect(() => {
    if (!pet || hydratedScope !== currentDraftScope) return;
    const key = currentDraftScope;
    if (!isDirty) { safeRemoveDraft(key); setDraftStatus("none"); setDraftSavedAt(""); return; }
    const values = { happenedAt, episodeType, rawInput, observation, behaviorCategory, measuredValue, measurementUnit, interpretation, location, triggerContext, durationMinutes, frequency, intensity, urgent, dangerSignals, otherConcern, planId };
    const signature = JSON.stringify({ ...values, savedAt: undefined });
    if (draftStatus === "restored" && signature === hydratedDraftSignature.current) return;
    const savedAt = new Date().toISOString();
    const draft: RecordDraft = { ...values, savedAt };
    try { localStorage.setItem(key, JSON.stringify(draft)); hydratedDraftSignature.current = signature; setDraftStatus("saved"); setDraftSavedAt(savedAt); }
    catch { setDraftStatus("unavailable"); }
  }, [pet, currentDraftScope, hydratedScope, draftStatus, isDirty, happenedAt, episodeType, rawInput, observation, behaviorCategory, measuredValue, measurementUnit, interpretation, location, triggerContext, durationMinutes, frequency, intensity, urgent, dangerSignals, otherConcern, planId]);

  function discardDraft() {
    if (!pet) return;
    safeRemoveDraft(draftKey(draftOwnerId, pet.id));
    const now = localDateTimeValue(); initialHappenedAt.current = now; hydratedDraftSignature.current = "";
    setHappenedAt(now); setEpisodeType("behavior_change"); setBehaviorCategory("ACTIVITY"); setMeasurementUnit("seconds");
    setRawInput(""); setObservation(""); setMeasuredValue(""); setInterpretation(""); setLocation(""); setTriggerContext(""); setDurationMinutes(""); setFrequency(""); setIntensity(""); setUrgent(false); setDangerSignals([]); setOtherConcern(""); setPlanId(""); setDraftStatus("none"); setDraftSavedAt("");
  }
  const loadPlans = useCallback(async () => {
    if (!pet) return;
    setPlanState("loading");
    try {
      setPlans((await listObservationPlans(pet.id)).filter((item) => item.status === "ACTIVE"));
      setPlanState("ready");
    } catch {
      setPlanState("error");
    }
  }, [pet]);
  useEffect(() => { void loadPlans(); }, [loadPlans]);

  function goToStep(targetId: RecordStep) {
    setActiveStep(targetId);
    const target = document.getElementById(targetId);
    if (target instanceof HTMLDetailsElement) target.open = true;
    target?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }

  function toggleSignal(signal: DangerSignal) {
    setDangerSignals((current) => current.includes(signal)
      ? current.filter((item) => item !== signal)
      : [...current, signal]);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!pet) { setError("请先建立宠物档案。"); return; }
    if (!rawInput.trim()) {
      setError("请先简单记录当时发生的事。其他内容都可以稍后补充。");
      return;
    }
    if (!happenedAt || Number.isNaN(new Date(happenedAt).getTime())) {
      setError("请填写有效的发生时间。");
      return;
    }
    if (urgent && dangerSignals.length === 0 && !otherConcern.trim()) {
      setError("请选择危险信号，或填写其他紧急情况。");
      return;
    }
    if (measuredValue && (!Number.isFinite(Number(measuredValue)) || Number(measuredValue) < 0)) {
      setError("计量值必须是大于或等于 0 的数字。");
      return;
    }
    if (durationMinutes && (!Number.isInteger(Number(durationMinutes)) || Number(durationMinutes) < 0)) {
      setError("持续时间必须是大于或等于 0 的整分钟。");
      return;
    }
    if (frequency && (!Number.isInteger(Number(frequency)) || Number(frequency) < 1)) {
      setError("发生次数必须是大于或等于 1 的整数。");
      return;
    }

    setSubmitting(true); onSubmittingChange(true);
    try {
      const episode = await createCompleteEpisode({
        pet_id: pet.id,
        happened_at: new Date(happenedAt).toISOString(),
        episode_type: episodeType,
        raw_owner_input: rawInput.trim(),
        ...(durationMinutes ? { duration_seconds: Math.round(Number(durationMinutes) * 60) } : {}),
        ...(frequency ? { frequency_count: Number(frequency) } : {}),
        ...(intensity ? { intensity: Number(intensity) } : {}),
        ...(location.trim() ? { location: location.trim() } : {}),
        ...(triggerContext.trim() ? { trigger_context: triggerContext.trim() } : {}),
        ...(planId ? { plan_id: Number(planId) } : {}),
        observations: observation.trim() ? [{
          behavior_type: episodeType,
          standardized_category: behaviorCategory,
          description: observation.trim(),
          source_type: "owner_direct",
          ...(measuredValue ? {
            measured_value: Number(measuredValue),
            unit: measurementUnit,
            standardized_unit: measurementUnit,
          } : {}),
        }] : [],
        owner_interpretations: interpretation.trim() ? [{ interpretation: interpretation.trim() }] : [],
        safety_check: {
          result: urgent ? "ESCALATE_TO_VET" : "NORMAL",
          danger_signals: urgent ? dangerSignals : [],
          ...(urgent && otherConcern.trim() ? { other_concern: otherConcern.trim() } : {}),
          acknowledged_at: new Date().toISOString(),
        },
      });
      safeRemoveDraft(draftKey(draftOwnerId, pet.id));
      setDraftStatus("none"); setDraftSavedAt("");
      onSaved(episode.id);
    } catch {
      setError("记录暂时无法保存。你的输入仍保留在页面中，请重试。");
    } finally {
      setSubmitting(false); onSubmittingChange(false);
    }
  }

  if (!pet) {
    return <section className="understand-page" aria-labelledby="understand-title"><p className="eyebrow">RECORD</p><h2 id="understand-title">记下一刻</h2><p role="status">请先建立宠物档案，再开始记录。</p></section>;
  }

  return (
    <section className="understand-page" aria-labelledby="understand-title">
      <header className="understand-hero">
        <div><p className="eyebrow">RECORD · 温柔地分开看</p><h2 id="understand-title">记下一刻</h2><p>先保存当时那一刻，再慢慢分清事实和你的理解。</p><span className="pet-handnote">不是答案，是小发现</span></div>
        <PetBotanicalSketch scene="understand" />
      </header>
      <ol className="step-rail" aria-label="记录流程">
        <li className={activeStep === "record-input" ? "active" : ""}><button type="button" aria-current={activeStep === "record-input" ? "step" : undefined} onClick={() => goToStep("record-input")}>简单记录</button></li>
        <li className={activeStep === "record-facts" ? "active" : ""}><button type="button" aria-current={activeStep === "record-facts" ? "step" : undefined} onClick={() => goToStep("record-facts")}>补充事实</button></li>
        <li className={activeStep === "record-meaning" ? "active" : ""}><button type="button" aria-current={activeStep === "record-meaning" ? "step" : undefined} onClick={() => goToStep("record-meaning")}>我的理解</button></li>
        <li className={activeStep === "record-safety" ? "active" : ""}><button type="button" aria-current={activeStep === "record-safety" ? "step" : undefined} onClick={() => goToStep("record-safety")}>安全</button></li>
        <li className={activeStep === "record-save" ? "active" : ""}><button type="button" aria-current={activeStep === "record-save" ? "step" : undefined} onClick={() => goToStep("record-save")}>保存</button></li>
      </ol>
      <form className="editor-form" onSubmit={(event) => void submit(event)} noValidate>
        <fieldset className="record-freeze" disabled={submitting}>
        {draftStatus === "restored" && <div className="inline-retry" role="status"><span>已恢复这只宠物上次未完成的草稿。</span><button type="button" onClick={discardDraft}>丢弃草稿</button></div>}
        {draftStatus === "saved" && <p className="field-status" role="status">草稿已自动保存在本机{draftSavedAt ? ` · ${new Date(draftSavedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : ""}</p>}
        {draftStatus === "unavailable" && <p className="form-error" role="alert">浏览器无法保存本地草稿；请保持此页面打开并尽快提交。</p>}
        <section id="record-input" className="journal-sheet record-simple"><h3>先简单记录</h3><p>用你自然的说法写下来即可。系统会原样保存，不要求重复填写。</p><label>原始描述<textarea rows={5} value={rawInput} onChange={(event) => setRawInput(event.target.value)} placeholder="例如：晚饭后它一直在门口走动，我有点担心。" /></label></section>
        <details id="record-facts" className="form-section progressive-section"><summary>补充事实（可选）</summary><p>按当时能记住的程度填写即可；不知道的项目直接留空，不影响保存。</p>
          <div className="form-pair journal-sheet journal-sheet--time">
            <label>发生时间<input aria-label="发生时间" type="datetime-local" value={happenedAt} onChange={(event) => setHappenedAt(event.target.value)} /></label>
            <label>这次主要记录什么<select aria-label="记录类型" value={episodeType} onChange={(event) => setEpisodeType(event.target.value)}><option value="behavior_change">行为变化</option><option value="daily_observation">日常观察</option><option value="feeding_change">饮食变化</option><option value="rest_change">休息变化</option><option value="owner_concern">我有些担心</option><option value="moving_home">搬家</option><option value="new_person_or_pet">新成员或访客</option><option value="environment_change">环境变化</option><option value="routine_change">作息变化</option><option value="care_event">医疗或护理事件</option></select></label>
          </div>
          <label className="lens-card"><JournalSticker name="spiral" /><strong>具体看到了什么？</strong><span>写动作、声音或能量到的变化，不用解释原因</span><textarea rows={4} aria-label="发生了什么" value={observation} onChange={(event) => setObservation(event.target.value)} /></label>
        <details className="advanced-fields"><summary>补充次数、时长或当时情境（可选）</summary>
        <fieldset className="form-section direct-facts"><legend>它持续了多久、发生了几次？</legend>
          <div className="form-triple"><label>大约持续几分钟<input aria-label="持续时间（分钟）" type="number" inputMode="numeric" min="0" step="1" placeholder="例如 2" value={durationMinutes} onChange={(event) => setDurationMinutes(event.target.value)} /></label><label>大约发生几次<input aria-label="发生次数" type="number" inputMode="numeric" min="1" step="1" placeholder="例如 3" value={frequency} onChange={(event) => setFrequency(event.target.value)} /></label><label>变化有多明显<select aria-label="强度" value={intensity} onChange={(event) => setIntensity(event.target.value)}><option value="">不确定</option><option value="1">很轻微</option><option value="2">比较轻</option><option value="3">比较明显</option><option value="4">很明显</option><option value="5">非常明显</option></select></label></div>
        </fieldset>
        <fieldset className="form-section journal-sheet journal-sheet--context"><legend>当时在哪里、刚发生了什么？</legend>
          <div className="form-pair"><label>地点<input value={location} onChange={(event) => setLocation(event.target.value)} /></label><label>刚发生了什么<input aria-label="触发背景" value={triggerContext} onChange={(event) => setTriggerContext(event.target.value)} /></label></div>
        </fieldset>
        <details className="comparison-fields"><summary>用于长期比较的精确数据（进阶，可选）</summary><fieldset className="form-section"><legend>你明确量到的数据</legend><p>只有实际计时、称重或计数时才需要填写。</p>
          <label>想比较哪一方面<select aria-label="行为类别" value={behaviorCategory} onChange={(event) => setBehaviorCategory(event.target.value as BehaviorCategory)}><option value="ACTIVITY">活动</option><option value="FEEDING">饮食</option><option value="RESTING">休息</option><option value="SOCIAL">社交</option><option value="ELIMINATION">排泄</option><option value="VOCALIZATION">发声</option><option value="GROOMING">梳理</option><option value="MOBILITY">行动能力</option><option value="OTHER">其他</option></select></label>
          <div className="form-pair"><label>实际量到的数值<input aria-label="计量值" type="number" inputMode="decimal" min="0" step="any" value={measuredValue} onChange={(event) => setMeasuredValue(event.target.value)} /></label><label>单位<select aria-label="标准单位" value={measurementUnit} disabled={!measuredValue} onChange={(event) => setMeasurementUnit(event.target.value as MeasurementUnit)}><option value="seconds">秒</option><option value="minutes">分钟</option><option value="count">次数</option><option value="meters">米</option><option value="grams">克</option><option value="milliliters">毫升</option></select></label></div>
        </fieldset></details></details></details>

        <details id="record-meaning" className="form-section progressive-section"><summary>我的理解（可选）</summary><p>这里记录你的想法。它不会被当成客观事实，也不会覆盖原始描述。</p><label className="lens-card interpretation"><JournalSticker name="bow" /><strong>我的理解</strong><textarea rows={4} aria-label="你的理解" value={interpretation} onChange={(event) => setInterpretation(event.target.value)} /></label></details>

        <section className="form-section plan-link-section" aria-labelledby="plan-link-title"><h3 id="plan-link-title">加入观察计划（可选）</h3><p>计划把同一主题的多天记录放在一起比较；不加入时，这就是一条独立记录。</p>
          {planState === "loading" && <p role="status">正在读取观察计划…</p>}
          {planState === "error" && <div role="alert" className="inline-retry"><span>观察计划读取失败；仍可作为独立记录继续保存。</span><button type="button" onClick={() => void loadPlans()}>重试计划</button></div>}
          {planState === "ready" && plans.length === 0 && <div className="empty-state"><strong>这是一条独立记录</strong><p>当前没有进行中的观察计划。</p><button type="button" onClick={onCreatePlan}>新建观察计划</button></div>}
          {planState === "ready" && plans.length > 0 && <fieldset><legend>选择记录归属</legend><label className="plan-choice"><input type="radio" name="plan" value="" checked={!planId} onChange={() => setPlanId("")} /><span><strong>这是一条独立记录</strong><small>不加入任何计划</small></span></label>{plans.map((plan) => <label className="plan-choice" key={plan.id}><input type="radio" name="plan" value={plan.id} checked={planId === String(plan.id)} onChange={() => setPlanId(String(plan.id))} /><span><strong>{plan.goal}</strong><small>{planRange(plan)}{plan.items.length ? ` · ${plan.items.map((item) => item.label).join("、")}` : ""}</small></span></label>)}</fieldset>}
          {planState === "ready" && plans.length > 0 && <button type="button" className="text-button" onClick={onCreatePlan}>新建观察计划</button>}
        </section>

        <fieldset id="record-safety" className="form-section safety-section"><legend>人工安全确认</legend>
          <p>Relapaw 不进行诊断，也不替代兽医。请根据你实际看到的情况选择。</p>
          <label className="choice-row"><input type="radio" name="urgent" checked={!urgent} onChange={() => { setUrgent(false); setDangerSignals([]); }} />未发现上述紧急情况</label>
          <label className="choice-row"><input type="radio" name="urgent" checked={urgent} onChange={() => setUrgent(true)} />存在需要尽快联系兽医的情况</label>
          {urgent && <div className="danger-panel" role="alert"><strong>请尽快联系兽医或当地急诊机构</strong><p>选择你实际观察到的情况：</p>{dangerOptions.map((option) => <label className="choice-row" key={option.value}><input type="checkbox" checked={dangerSignals.includes(option.value)} onChange={() => toggleSignal(option.value)} />{option.label}</label>)}<label>补充说明<textarea rows={2} value={otherConcern} onChange={(event) => setOtherConcern(event.target.value)} /></label></div>}
        </fieldset>

        {error && <p className="form-error" role="alert">{error}</p>}
        <p className="record-media-note">保存后可以在记录详情中继续添加照片或视频。</p>
        <button id="record-save" className="primary" type="submit">{submitting ? "正在保存…" : "保存这条记录"}</button>
        </fieldset>
      </form>
      <p className="notice">只保存你输入的内容。本阶段不会进行 AI 分析、情绪判断或医学诊断。</p>
    </section>
  );
}
