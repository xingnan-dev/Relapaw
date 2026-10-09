import { type FormEvent, useEffect, useState } from "react";
import { createCompleteEpisode, listObservationPlans } from "../api";
import { useCurrentPet } from "../state/CurrentPetContext";
import type { DangerSignal, ObservationPlan } from "../types";

const dangerOptions: Array<{ value: DangerSignal; label: string }> = [
  { value: "breathing_difficulty", label: "呼吸困难" },
  { value: "prolonged_seizure", label: "持续抽搐" },
  { value: "collapse_or_unable_to_stand", label: "昏厥或无法站立" },
  { value: "severe_bleeding", label: "严重出血" },
  { value: "suspected_poisoning", label: "疑似中毒" },
  { value: "other_urgent_concern", label: "其他紧急情况" },
];

function localDateTimeValue() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

export function Understand({ onSaved }: { onSaved: () => void }) {
  const { pet } = useCurrentPet();
  const [happenedAt, setHappenedAt] = useState(localDateTimeValue);
  const [episodeType, setEpisodeType] = useState("behavior_change");
  const [rawInput, setRawInput] = useState("");
  const [observation, setObservation] = useState("");
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
  const [planId, setPlanId] = useState("");
  useEffect(() => { if (pet) void listObservationPlans(pet.id).then((items) => setPlans(items.filter((item) => item.status === "ACTIVE"))).catch(() => setPlans([])); }, [pet]);

  function toggleSignal(signal: DangerSignal) {
    setDangerSignals((current) => current.includes(signal)
      ? current.filter((item) => item !== signal)
      : [...current, signal]);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!pet) { setError("请先建立宠物档案。"); return; }
    if (!rawInput.trim() || !observation.trim()) {
      setError("请填写原始描述和至少一条客观观察。");
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

    setSubmitting(true);
    try {
      await createCompleteEpisode({
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
        observations: [{ behavior_type: episodeType, description: observation.trim(), source_type: "owner_direct" }],
        owner_interpretations: interpretation.trim() ? [{ interpretation: interpretation.trim() }] : [],
        safety_check: {
          result: urgent ? "ESCALATE_TO_VET" : "NORMAL",
          danger_signals: urgent ? dangerSignals : [],
          ...(urgent && otherConcern.trim() ? { other_concern: otherConcern.trim() } : {}),
          acknowledged_at: new Date().toISOString(),
        },
      });
      onSaved();
    } catch {
      setError("记录暂时无法保存。你的输入仍保留在页面中，请重试。");
    } finally {
      setSubmitting(false);
    }
  }

  if (!pet) {
    return <section aria-labelledby="understand-title"><p className="eyebrow">UNDERSTAND</p><h2 id="understand-title">它怎么啦？</h2><p role="status">请先建立宠物档案，再开始记录。</p></section>;
  }

  return (
    <section aria-labelledby="understand-title">
      <p className="eyebrow">UNDERSTAND</p>
      <h2 id="understand-title">它怎么啦？</h2>
      <ol className="step-rail" aria-label="记录流程"><li className="active">输入</li><li className="active">区分</li><li className="active">安全</li><li>保存</li></ol>
      <form onSubmit={(event) => void submit(event)} noValidate>
        <div className="form-pair">
          <label>发生时间<input aria-label="发生时间" type="datetime-local" value={happenedAt} onChange={(event) => setHappenedAt(event.target.value)} /></label>
          <label>记录类型<select aria-label="记录类型" value={episodeType} onChange={(event) => setEpisodeType(event.target.value)}><option value="behavior_change">行为变化</option><option value="daily_observation">日常观察</option><option value="feeding_change">饮食变化</option><option value="rest_change">休息变化</option><option value="owner_concern">主人担忧</option></select></label>
        </div>
        <label>原始描述<textarea rows={5} value={rawInput} onChange={(event) => setRawInput(event.target.value)} placeholder="先原样记下你看到的情况和当时的想法，下面再将两者分开。" /></label>
        <div className="lens-grid">
          <label className="lens-card"><strong>发生了什么</strong><span>只记录可以观察、听到或计量的事实</span><textarea rows={4} aria-label="发生了什么" value={observation} onChange={(event) => setObservation(event.target.value)} /></label>
          <label className="lens-card interpretation"><strong>你的理解</strong><span>这是你的想法，不会被当成客观事实</span><textarea rows={4} aria-label="你的理解" value={interpretation} onChange={(event) => setInterpretation(event.target.value)} /></label>
        </div>

        <fieldset className="form-section"><legend>当时的背景（可选）</legend>
          <label>关联观察计划<select aria-label="关联观察计划" value={planId} onChange={(event) => setPlanId(event.target.value)}><option value="">不关联计划</option>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.goal}</option>)}</select></label>
          <div className="form-pair"><label>地点<input value={location} onChange={(event) => setLocation(event.target.value)} /></label><label>刚发生了什么<input aria-label="触发背景" value={triggerContext} onChange={(event) => setTriggerContext(event.target.value)} /></label></div>
          <div className="form-triple"><label>持续时间（分钟）<input type="number" min="0" step="1" value={durationMinutes} onChange={(event) => setDurationMinutes(event.target.value)} /></label><label>发生次数<input type="number" min="1" step="1" value={frequency} onChange={(event) => setFrequency(event.target.value)} /></label><label>强度<select value={intensity} onChange={(event) => setIntensity(event.target.value)}><option value="">未填写</option><option value="1">1 很轻</option><option value="2">2</option><option value="3">3 中等</option><option value="4">4</option><option value="5">5 很明显</option></select></label></div>
        </fieldset>

        <fieldset className="form-section safety-section"><legend>人工安全确认</legend>
          <p>Relapaw 不进行诊断，也不替代兽医。请根据你实际看到的情况选择。</p>
          <label className="choice-row"><input type="radio" name="urgent" checked={!urgent} onChange={() => { setUrgent(false); setDangerSignals([]); }} />未发现上述紧急情况</label>
          <label className="choice-row"><input type="radio" name="urgent" checked={urgent} onChange={() => setUrgent(true)} />存在需要尽快联系兽医的情况</label>
          {urgent && <div className="danger-panel" role="alert"><strong>请尽快联系兽医或当地急诊机构</strong><p>选择你实际观察到的情况：</p>{dangerOptions.map((option) => <label className="choice-row" key={option.value}><input type="checkbox" checked={dangerSignals.includes(option.value)} onChange={() => toggleSignal(option.value)} />{option.label}</label>)}<label>补充说明<textarea rows={2} value={otherConcern} onChange={(event) => setOtherConcern(event.target.value)} /></label></div>}
        </fieldset>

        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary" type="submit" disabled={submitting}>{submitting ? "正在保存…" : "保存手工记录"}</button>
      </form>
      <p className="notice">只保存你输入的内容。本阶段不会进行 AI 分析、情绪判断或医学诊断。</p>
    </section>
  );
}
