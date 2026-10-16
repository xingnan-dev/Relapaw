import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { deleteEpisode, getEpisode, getTimeline, scheduleFollowUp, updateEpisode, updateVeterinaryEscalation } from "../api";
import { useCurrentPet } from "../state/CurrentPetContext";
import { UnderstandingPanel } from "../components/UnderstandingPanel";
import type { Episode, EpisodeUpdate, TimelineFilters, VeterinaryEscalation } from "../types";
import { PetBotanicalSketch } from "../components/brand";

type Range = "all" | "30" | "7" | "today";
const ranges: Array<[Range, string]> = [["all", "全部"], ["30", "30 天"], ["7", "7 天"], ["today", "今天"]];
const episodeTypeLabels: Record<string, string> = {
  behavior_change: "行为变化",
  daily_observation: "日常观察",
  feeding_change: "饮食变化",
  rest_change: "休息变化",
  owner_concern: "主人担忧",
  moving_home: "搬家",
  new_person_or_pet: "新成员或访客",
  environment_change: "环境变化",
  routine_change: "作息变化",
  care_event: "医疗或护理事件",
  follow_up: "复评记录",
};

function episodeTypeLabel(value: string) {
  return episodeTypeLabels[value] || "其他记录";
}

function rangeFilters(range: Range): TimelineFilters {
  if (range === "all") return {};
  const now = new Date();
  if (range === "today") {
    const start = new Date(now); start.setHours(0, 0, 0, 0);
    const end = new Date(now); end.setHours(23, 59, 59, 999);
    return { from: start.toISOString(), to: end.toISOString() };
  }
  return { from: new Date(now.getTime() - Number(range) * 86400000).toISOString(), to: now.toISOString() };
}

function localDateTime(value: string) {
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

export function Timeline({ initialEpisodeId = null, onInitialEpisodeOpened = () => undefined, onOpenMemory = () => undefined }: { initialEpisodeId?: number | null; onInitialEpisodeOpened?: () => void; onOpenMemory?: () => void }) {
  const { pet, status } = useCurrentPet();
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [listState, setListState] = useState<"loading" | "ready" | "error">("loading");
  const [loadingMore, setLoadingMore] = useState(false);
  const [range, setRange] = useState<Range>("all");
  const [episodeType, setEpisodeType] = useState("");
  const [selected, setSelected] = useState<Episode | null>(null);
  const [detailState, setDetailState] = useState<"idle" | "loading" | "error">("idle");
  const [mode, setMode] = useState<"list" | "detail" | "edit" | "delete" | "schedule">("list");
  const [actionError, setActionError] = useState("");
  const filters = useMemo(() => ({ ...rangeFilters(range), ...(episodeType ? { episode_type: episodeType } : {}) }), [range, episodeType]);

  const load = useCallback(async () => {
    if (!pet) { setEpisodes([]); setListState("ready"); return; }
    setListState("loading");
    try {
      const result = await getTimeline(pet.id, 1, 20, filters);
      setEpisodes(result.items); setPage(1); setHasMore(result.has_more); setListState("ready");
    } catch { setListState("error"); }
  }, [pet, filters]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { if (initialEpisodeId !== null) { void openDetail(initialEpisodeId); onInitialEpisodeOpened(); } }, [initialEpisodeId]);

  async function openDetail(id: number) {
    setSelected(episodes.find((item) => item.id === id) || null);
    setMode("detail"); setDetailState("loading"); setActionError("");
    try { setSelected(await getEpisode(id)); setDetailState("idle"); }
    catch { setDetailState("error"); }
  }

  async function loadMore() {
    if (!pet || loadingMore) return;
    setLoadingMore(true); setActionError("");
    try {
      const next = await getTimeline(pet.id, page + 1, 20, filters);
      setEpisodes((items) => [...items, ...next.items]); setPage(next.page); setHasMore(next.has_more);
    } catch { setActionError("无法加载更多记录，请重试。"); }
    finally { setLoadingMore(false); }
  }

  if (!pet) return <section className="timeline-page" aria-labelledby="timeline-title"><p className="eyebrow">TIMELINE</p><h2 id="timeline-title">长期记录</h2><p role="status">{status === "loading" ? "正在读取…" : "添加宠物后，Timeline 会出现在这里。"}</p></section>;

  if (mode !== "list") return <EpisodePanel episode={selected} state={detailState} mode={mode} error={actionError}
    onBack={() => { setMode("list"); setActionError(""); }}
    onRetry={() => selected ? void openDetail(selected.id) : undefined}
    onEdit={() => setMode("edit")} onDelete={() => setMode("delete")} onSchedule={() => setMode("schedule")} onOpenRelated={(episodeId) => void openDetail(episodeId)}
    onEscalationChanged={(updated) => { setSelected((current) => current ? { ...current, veterinary_escalations: current.veterinary_escalations.map((item) => item.id === updated.id ? updated : item) } : current); }}
    onSaved={(episode) => { setSelected(episode); setEpisodes((items) => items.map((item) => item.id === episode.id ? episode : item)); setMode("detail"); setActionError(""); }}
    onOpenMemory={onOpenMemory} onError={setActionError} onDeleted={() => { setSelected(null); setMode("list"); void load(); }} />;

  return <section className="timeline-page" aria-labelledby="timeline-title">
    <header className="timeline-hero"><div><p className="eyebrow">TIMELINE · 一起走过的日子</p><h2 id="timeline-title">长期记录</h2><p>每一条都保留原话、时间和来源，慢慢连成它真实的生活轨迹。</p><span className="pet-handnote">过几天再回来看看</span></div><PetBotanicalSketch scene="timeline" /><div className="timeline-count"><strong>{episodes.length}</strong><span>条记录</span></div></header>
    <div className="timeline-filters"><label>记录类型筛选<select value={episodeType} onChange={(event) => setEpisodeType(event.target.value)}><option value="">全部类型</option>{Object.entries(episodeTypeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    <div className="filter-chips" aria-label="时间范围">{ranges.map(([value, label]) => <button key={value} className={range === value ? "active" : ""} aria-pressed={range === value} onClick={() => setRange(value)}>{label}</button>)}</div></div>
    {listState === "loading" && <p role="status">正在读取…</p>}
    {listState === "error" && <div role="alert"><p>暂时无法读取 Timeline。</p><button onClick={() => void load()}>重试</button></div>}
    {listState === "ready" && episodes.length === 0 && <p role="status">当前筛选下还没有事件记录。</p>}
    {actionError && <p role="alert" className="form-error">{actionError}</p>}
    <ol className="timeline">{episodes.map((episode) => <li key={episode.id}><button className="timeline-summary" onClick={() => void openDetail(episode.id)}><span><time dateTime={episode.happened_at}>{new Date(episode.happened_at).toLocaleString()}</time><strong>{episodeTypeLabel(episode.episode_type)}</strong><span className="sr-only">{episode.episode_type}</span></span><span>打开记录 <span aria-hidden="true">→</span></span></button><p>{episode.raw_owner_input}</p></li>)}</ol>
    {hasMore && <button disabled={loadingMore} onClick={() => void loadMore()}>{loadingMore ? "正在加载…" : "加载更多"}</button>}
  </section>;
}

type PanelProps = { episode: Episode | null; state: "idle" | "loading" | "error"; mode: "detail" | "edit" | "delete" | "schedule"; error: string; onBack: () => void; onRetry: () => void; onEdit: () => void; onDelete: () => void; onSchedule: () => void; onOpenRelated: (episodeId: number) => void; onOpenMemory: () => void; onSaved: (episode: Episode) => void; onDeleted: () => void; onError: (value: string) => void; onEscalationChanged: (updated: VeterinaryEscalation) => void };

function EpisodePanel({ episode, state, mode, error, onBack, onRetry, onEdit, onDelete, onSchedule, onOpenRelated, onOpenMemory, onSaved, onDeleted, onError, onEscalationChanged }: PanelProps) {
  if (state === "loading") return <section><button onClick={onBack}>返回 Timeline</button><p role="status">正在读取详情…</p></section>;
  if (state === "error" || !episode) return <section><button onClick={onBack}>返回 Timeline</button><div role="alert"><p>暂时无法读取记录详情。</p><button onClick={onRetry}>重试</button></div></section>;
  if (mode === "edit") return <EpisodeEdit episode={episode} error={error} onCancel={() => onSaved(episode)} onSaved={onSaved} onError={onError} />;
  if (mode === "delete") return <DeleteConfirm episode={episode} error={error} onCancel={() => onSaved(episode)} onDeleted={onDeleted} onError={onError} />;
  if (mode === "schedule") return <ScheduleFollowUp episode={episode} onCancel={() => onSaved(episode)} onScheduled={async () => onSaved(await getEpisode(episode.id))} />;
  const hasFollowUpHistory = Boolean(episode.result_of_follow_up || episode.scheduled_follow_ups?.length);
  return <section className="episode-panel" aria-labelledby="episode-detail-title">
    <button onClick={onBack}>返回 Timeline</button><p className="eyebrow">EPISODE DETAIL</p><h2 id="episode-detail-title">记录详情</h2>
    <Detail title="原始输入"><p>{episode.raw_owner_input}</p></Detail>
    <Detail title="发生了什么"><small>Observation</small>{episode.observations.map((item) => <p key={item.id}>{item.description}</p>)}</Detail>
    <Detail title="你的理解"><small>Owner Interpretation</small>{episode.owner_interpretations.length ? episode.owner_interpretations.map((item) => <p key={item.id}>{item.interpretation}</p>) : <p>未填写主人解释</p>}</Detail>
    <Detail title="结构化背景"><dl><dt>发生时间</dt><dd>{new Date(episode.happened_at).toLocaleString()}</dd><dt>更新时间</dt><dd>{new Date(episode.updated_at).toLocaleString()}</dd><dt>类型</dt><dd>{episodeTypeLabel(episode.episode_type)}</dd><dt>地点</dt><dd>{episode.location || "未填写"}</dd><dt>触发背景</dt><dd>{episode.trigger_context || "未填写"}</dd><dt>Context</dt><dd>{episode.context ? JSON.stringify(episode.context) : "未填写"}</dd></dl></Detail>
    <Detail title="人工 Safety Check"><p>{episode.safety_check?.result || "未进行"}</p>{episode.safety_check?.danger_signals.map((signal) => <p key={signal}>{signal}</p>)}</Detail>
    {episode.veterinary_escalations?.length > 0 && <VeterinaryEscalationPanel episode={episode} onChanged={onEscalationChanged} />}
    <UnderstandingPanel episode={episode} onOpenMemory={onOpenMemory} />
    <Detail title="Evidence 来源信息">{episode.evidence_references?.length ? episode.evidence_references.map((item) => <p key={item.id}>{item.source_type} · {item.field_path} · {new Date(item.observed_at).toLocaleString()}</p>) : <p>暂无来源记录</p>}</Detail>
    <Detail title="Observation Plan">{episode.plan_links?.length ? episode.plan_links.map((item) => <p key={item.id}>关联计划 #{item.plan_id}</p>) : <p>未关联观察计划</p>}</Detail>
    <Detail title="复评关系">{episode.result_of_follow_up && <p><button onClick={() => onOpenRelated(episode.result_of_follow_up!.source_episode_id)}>查看原记录</button></p>}{episode.scheduled_follow_ups?.length ? episode.scheduled_follow_ups.map((item) => <p key={item.id}>{new Date(item.scheduled_at).toLocaleString()} · {item.status}{item.result_episode_id && <button onClick={() => onOpenRelated(item.result_episode_id!)}>查看复评记录</button>}</p>) : <p>尚未安排复评</p>}</Detail>
    {hasFollowUpHistory && <p className="safety-note">这条记录已有复评关系。为保留可追溯历史，不能删除。</p>}
    {error && <p role="alert" className="form-error">{error}</p>}<div className="panel-actions episode-actions"><button onClick={onSchedule}>安排复评</button><button onClick={onEdit}>编辑记录</button><button className="danger-button" disabled={hasFollowUpHistory} onClick={onDelete}>删除记录</button></div>
  </section>;
}

function VeterinaryEscalationPanel({ episode, onChanged }: { episode: Episode; onChanged: (updated: VeterinaryEscalation) => void }) {
  const [submittingId, setSubmittingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  async function transition(id: number, status: "SHARED_WITH_VET" | "CLOSED") {
    setSubmittingId(id); setError("");
    try { onChanged(await updateVeterinaryEscalation(id, status)); }
    catch { setError("更新兽医升级状态失败，原状态仍然保留。请重试。"); }
    finally { setSubmittingId(null); }
  }
  return <div className="danger-panel" role="alert"><strong>Veterinary Escalation</strong>{episode.veterinary_escalations.map((item) => <div key={item.id}><p>{item.reason}（{item.status}）</p>{item.vet_brief && <p>给兽医的摘要：{item.vet_brief}</p>}<div className="panel-actions">{item.status === "OPEN" && <button disabled={submittingId === item.id} onClick={() => void transition(item.id, "SHARED_WITH_VET")}>标记已分享给兽医</button>}{item.status !== "CLOSED" && <button disabled={submittingId === item.id} onClick={() => void transition(item.id, "CLOSED")}>关闭升级</button>}</div></div>)}<p>Relapaw 不进行诊断，也不替代兽医。</p>{error && <p className="form-error">{error}</p>}</div>;
}

function Detail({ title, children }: { title: string; children: ReactNode }) { return <section className="card"><h3>{title}</h3>{children}</section>; }

function ScheduleFollowUp({ episode, onCancel, onScheduled }: { episode: Episode; onCancel: () => void; onScheduled: () => Promise<void> }) {
  const initial = new Date(Date.now() + 2 * 60 * 60 * 1000);
  const [scheduledAt, setScheduledAt] = useState(localDateTime(initial.toISOString()));
  const [error, setError] = useState(""); const [submitting, setSubmitting] = useState(false);
  function preset(hours: number) { setScheduledAt(localDateTime(new Date(Date.now() + hours * 60 * 60 * 1000).toISOString())); }
  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    const date = new Date(scheduledAt);
    if (!scheduledAt || Number.isNaN(date.getTime()) || date <= new Date()) { setError("请选择当前时间之后的复评时间。"); return; }
    setSubmitting(true); try { await scheduleFollowUp(episode.id, date.toISOString()); await onScheduled(); } catch { setError("安排复评失败，请保留当前选择并重试。"); } finally { setSubmitting(false); }
  }
  return <section><h2>安排复评</h2><p>复评会创建一条新记录，不会覆盖当前 Episode。</p><div className="filter-chips" aria-label="复评快捷时间"><button onClick={() => preset(2)}>2 小时后</button><button onClick={() => preset(24)}>次日</button><button onClick={() => preset(72)}>3 天后</button></div><form onSubmit={(event) => void submit(event)}><label>自定义复评时间<input aria-label="自定义复评时间" type="datetime-local" value={scheduledAt} onChange={(event) => setScheduledAt(event.target.value)} /></label>{error && <p role="alert" className="form-error">{error}</p>}<div className="panel-actions"><button type="button" onClick={onCancel}>取消</button><button className="primary" disabled={submitting}>{submitting ? "正在安排…" : "确认安排"}</button></div></form></section>;
}

function EpisodeEdit({ episode, error, onCancel, onSaved, onError }: { episode: Episode; error: string; onCancel: () => void; onSaved: (episode: Episode) => void; onError: (value: string) => void }) {
  const [raw, setRaw] = useState(episode.raw_owner_input);
  const [observations, setObservations] = useState(episode.observations.map((item) => ({ ...item })));
  const [interpretations, setInterpretations] = useState(episode.owner_interpretations.map((item) => item.interpretation));
  const [episodeType, setEpisodeType] = useState(episode.episode_type);
  const [happened, setHappened] = useState(localDateTime(episode.happened_at));
  const [location, setLocation] = useState(episode.location || "");
  const [trigger, setTrigger] = useState(episode.trigger_context || "");
  const [duration, setDuration] = useState(episode.duration_seconds?.toString() || "");
  const [frequency, setFrequency] = useState(episode.frequency_count?.toString() || "");
  const [intensity, setIntensity] = useState(episode.intensity?.toString() || "");
  const [context, setContext] = useState(episode.context ? JSON.stringify(episode.context, null, 2) : "");
  const [submitting, setSubmitting] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); onError("");
    if (!raw.trim() || observations.length === 0 || observations.some((item) => !item.description.trim()) || !episodeType.trim()) { onError("原始输入、每条 Observation 和记录类型为必填项。"); return; }
    let parsedContext: Record<string, unknown> | null = null;
    try { parsedContext = context.trim() ? JSON.parse(context) : null; if (parsedContext !== null && (Array.isArray(parsedContext) || typeof parsedContext !== "object")) throw new Error(); }
    catch { onError("结构化背景必须是有效的 JSON 对象。"); return; }
    const numberOrNull = (value: string) => value === "" ? null : Number(value);
    const payload: EpisodeUpdate = { happened_at: new Date(happened).toISOString(), episode_type: episodeType.trim(), raw_owner_input: raw.trim(), context: parsedContext, duration_seconds: numberOrNull(duration), frequency_count: numberOrNull(frequency), intensity: numberOrNull(intensity), location: location.trim() || null, trigger_context: trigger.trim() || null, observations: observations.map(({ behavior_type, description, source_type, confidence, measured_value, unit }) => ({ behavior_type, description: description.trim(), source_type, confidence, measured_value, unit })), owner_interpretations: interpretations.filter((item) => item.trim()).map((interpretation) => ({ interpretation: interpretation.trim() })) };
    setSubmitting(true); try { onSaved(await updateEpisode(episode.id, payload)); } catch { onError("保存失败，输入仍保留。请检查网络后重试。"); } finally { setSubmitting(false); }
  }
  return <section><h2>编辑记录</h2><p className="notice">人工 Safety Check 与 Veterinary Escalation 是历史记录，本页不会修改它们。</p><form className="editor-form" onSubmit={(event) => void submit(event)}>
    <label>发生时间<input aria-label="发生时间" type="datetime-local" value={happened} onChange={(event) => setHappened(event.target.value)} /></label><label>记录类型<input aria-label="记录类型" value={episodeType} onChange={(event) => setEpisodeType(event.target.value)} /></label>
    <label>原始输入<textarea aria-label="原始输入" value={raw} onChange={(event) => setRaw(event.target.value)} /></label>
    <fieldset className="form-section"><legend>Observation</legend>{observations.map((item, index) => <div key={item.id || index}><label>Observation {index + 1}<textarea aria-label={index === 0 ? "Observation" : `Observation ${index + 1}`} value={item.description} onChange={(event) => setObservations((current) => current.map((value, itemIndex) => itemIndex === index ? { ...value, description: event.target.value } : value))} /></label>{observations.length > 1 && <button type="button" onClick={() => setObservations((current) => current.filter((_, itemIndex) => itemIndex !== index))}>删除 Observation {index + 1}</button>}</div>)}<button type="button" onClick={() => setObservations((current) => [...current, { id: 0, episode_id: episode.id, behavior_type: "manual_observation", description: "", source_type: "owner_direct", confidence: null, measured_value: null, unit: null, created_at: "", updated_at: "" }])}>添加 Observation</button></fieldset>
    <fieldset className="form-section"><legend>Owner Interpretation</legend>{interpretations.map((item, index) => <div key={index}><label>Owner Interpretation {index + 1}<textarea aria-label={index === 0 ? "Owner Interpretation" : `Owner Interpretation ${index + 1}`} value={item} onChange={(event) => setInterpretations((current) => current.map((value, itemIndex) => itemIndex === index ? event.target.value : value))} /></label><button type="button" onClick={() => setInterpretations((current) => current.filter((_, itemIndex) => itemIndex !== index))}>删除 Owner Interpretation {index + 1}</button></div>)}<button type="button" onClick={() => setInterpretations((current) => [...current, ""])}>添加 Owner Interpretation</button></fieldset>
    <div className="form-triple"><label>持续秒数<input type="number" min="0" value={duration} onChange={(event) => setDuration(event.target.value)} /></label><label>发生次数<input type="number" min="1" value={frequency} onChange={(event) => setFrequency(event.target.value)} /></label><label>强度（1–5）<input type="number" min="1" max="5" value={intensity} onChange={(event) => setIntensity(event.target.value)} /></label></div>
    <label>地点<input value={location} onChange={(event) => setLocation(event.target.value)} /></label><label>触发背景<textarea value={trigger} onChange={(event) => setTrigger(event.target.value)} /></label><label>结构化背景（JSON 对象）<textarea aria-label="结构化背景" value={context} onChange={(event) => setContext(event.target.value)} /></label>{error && <p role="alert" className="form-error">{error}</p>}<div className="panel-actions"><button type="button" onClick={onCancel}>取消</button><button className="primary" disabled={submitting}>{submitting ? "正在保存…" : "保存修改"}</button></div></form></section>;
}

function DeleteConfirm({ episode, error, onCancel, onDeleted, onError }: { episode: Episode; error: string; onCancel: () => void; onDeleted: () => void; onError: (value: string) => void }) {
  const [submitting, setSubmitting] = useState(false);
  async function remove() { setSubmitting(true); onError(""); try { await deleteEpisode(episode.id); onDeleted(); } catch { onError("删除失败，记录仍然保留。请重试。"); } finally { setSubmitting(false); } }
  return <section role="dialog" aria-modal="true" aria-labelledby="delete-title"><h2 id="delete-title">确认删除这条记录？</h2><p>删除后，原始记录及关联的 Observation、Owner Interpretation、Safety Check、Veterinary Escalation、Evidence 来源和计划关联都会被移除，且当前无法恢复。</p>{error && <p role="alert" className="form-error">{error}</p>}<div className="panel-actions"><button onClick={onCancel}>取消删除</button><button className="danger-button" disabled={submitting} onClick={() => void remove()}>{submitting ? "正在删除…" : "确认删除"}</button></div></section>;
}
