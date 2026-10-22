import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, createLifeEvent, createManualMemoryCandidate, decideMemoryCandidate, getLatestBaselineSnapshot, getPetBaseline, getTimeline, listLifeEvents, listMemoryCandidates, recomputeBaselineSnapshot, savePetBaseline, updateLifeEvent, updateManualMemoryCandidate } from "../api";
import type { BaselineMetric, BaselineSnapshot, BaselineWindow, Episode, LifeEvent, LifeEventType, ManualMemoryCategory, MemoryCandidate, MemoryDecisionType, PetBaseline, TimelinePage } from "../types";
import { Button, StatusNotice, Surface } from "./ui";

const windows: Array<{ value: BaselineWindow; label: string }> = [
  { value: "7d", label: "7 天" },
  { value: "30d", label: "30 天" },
  { value: "90d", label: "90 天" },
  { value: "all", label: "全部" },
];
const memoryStateLabels: Record<MemoryCandidate["state"], string> = {
  ELIGIBLE: "待决定", ACTIVE: "已纳入", WITHDRAWN: "已撤回", STALE: "来源已变化",
};
const memoryCategoryLabels: Record<ManualMemoryCategory, string> = {
  ROUTINE: "日常规律", PREFERENCE: "偏好", TRIGGER: "触发背景", COMFORT: "安抚方式", HEALTH_CONTEXT: "健康背景（非诊断）", OTHER: "其他",
};
const snapshotStatusLabels: Record<BaselineSnapshot["status"], string> = {
  READY: "数据充足", INSUFFICIENT_DATA: "数据不足", EMPTY: "暂无数据",
};
const windowLabels: Record<BaselineWindow, string> = { "7d": "7 天", "30d": "30 天", "90d": "90 天", all: "全部时间" };
const baselineLabels: Record<keyof Omit<PetBaseline, "id" | "pet_id">, string> = {
  social_behavior: "社交行为", activity_pattern: "活动规律", feeding_pattern: "饮食规律",
  resting_pattern: "休息规律", handling_preference: "接触偏好", hiding_pattern: "躲藏规律",
};
const lifeEventLabels: Record<LifeEventType, string> = { moving: "搬家", new_pet: "新宠物加入", owner_absence: "主人离开", visitor: "访客", surgery: "手术经历", diet_change: "饮食变化", environment_change: "环境变化", other: "其他" };

function newRequestId(prefix: string) {
  return globalThis.crypto?.randomUUID?.() ?? `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function MemoryBaselinePanel({ petId }: { petId: number }) {
  return <div className="memory-baseline-stack">
    <ManualBaseline key={`manual-${petId}`} petId={petId} />
    <MemoryCandidates key={`memory-${petId}`} petId={petId} />
    <LifeEvents key={`events-${petId}`} petId={petId} />
    <EvidenceGuidance key={`guidance-${petId}`} petId={petId} />
    <QuantitativeBaseline key={`quantitative-${petId}`} petId={petId} />
  </div>;
}

function ManualBaseline({ petId }: { petId: number }) {
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error">("loading");
  const [baseline, setBaseline] = useState<PetBaseline | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Record<keyof typeof baselineLabels, string>>(() => emptyBaselineDraft());
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const load = useCallback(async () => {
    setState("loading");
    try { const value = await getPetBaseline(petId); setBaseline(value); setDraft(baselineToDraft(value)); setState("ready"); }
    catch (error) { setBaseline(null); setDraft(emptyBaselineDraft()); setState(error instanceof ApiError && error.status === 404 ? "empty" : "error"); }
  }, [petId]);
  useEffect(() => { void load(); }, [load]);
  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setSaveError("");
    const originalDraft = baseline ? baselineToDraft(baseline) : emptyBaselineDraft();
    const payload = Object.fromEntries(Object.keys(baselineLabels).map((key) => {
      const typedKey = key as keyof typeof baselineLabels;
      if (baseline && draft[typedKey] === originalDraft[typedKey]) return [key, baseline[typedKey]];
      return [key, draft[typedKey].trim() ? { summary: draft[typedKey].trim() } : null];
    })) as Omit<PetBaseline, "id" | "pet_id">;
    try { const value = await savePetBaseline(petId, payload); setBaseline(value); setDraft(baselineToDraft(value)); setState("ready"); setEditing(false); }
    catch { setSaveError("Baseline 保存失败；你的编辑内容仍保留，请重试。"); }
    finally { setSaving(false); }
  }
  return <section aria-labelledby="manual-baseline-title"><h3 id="manual-baseline-title">人工档案 Baseline</h3>
    <p className="section-help">由用户明确填写的日常模式，与模型候选和量化快照分开保存。</p>
    {state === "loading" && <p role="status">正在读取人工 Baseline…</p>}
    {state === "empty" && <StatusNotice>尚未填写人工 Baseline。</StatusNotice>}
    {state === "error" && <StatusNotice tone="warning" role="alert" action={<Button onClick={() => void load()}>重试</Button>}>读取失败，页面其他状态已保留。</StatusNotice>}
    {!editing && state === "empty" && <Button onClick={() => setEditing(true)}>创建人工 Baseline</Button>}
    {!editing && state === "ready" && baseline && <><Surface className="baseline-definition-list"><dl>{Object.entries(baselineLabels).map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{baselineSummary(baseline[key as keyof typeof baselineLabels])}</dd></div>)}</dl></Surface><Button onClick={() => setEditing(true)}>编辑人工 Baseline</Button></>}
    {editing && <form className="editor-form" onSubmit={(event) => void save(event)}>{Object.entries(baselineLabels).map(([key, label]) => <label key={key}>{label}<textarea maxLength={2000} value={draft[key as keyof typeof baselineLabels]} onChange={(event) => setDraft((current) => ({ ...current, [key]: event.target.value }))} /></label>)}<div className="button-row"><Button type="submit" busy={saving}>{saving ? "正在保存…" : "保存 Baseline"}</Button><Button type="button" onClick={() => { setEditing(false); setSaveError(""); setDraft(baseline ? baselineToDraft(baseline) : emptyBaselineDraft()); }}>取消</Button></div>{saveError && <StatusNotice tone="danger" role="alert">{saveError}</StatusNotice>}</form>}
  </section>;
}

function emptyBaselineDraft(): Record<keyof typeof baselineLabels, string> {
  return Object.fromEntries(Object.keys(baselineLabels).map((key) => [key, ""])) as Record<keyof typeof baselineLabels, string>;
}

function baselineSummary(value: Record<string, unknown> | null): string {
  if (!value) return "未填写";
  return typeof value.summary === "string" ? value.summary : JSON.stringify(value);
}

function baselineToDraft(value: PetBaseline): Record<keyof typeof baselineLabels, string> {
  return Object.fromEntries(Object.keys(baselineLabels).map((key) => [key, baselineSummary(value[key as keyof typeof baselineLabels]) === "未填写" ? "" : baselineSummary(value[key as keyof typeof baselineLabels])])) as Record<keyof typeof baselineLabels, string>;
}

function MemoryCandidates({ petId }: { petId: number }) {
  const [items, setItems] = useState<MemoryCandidate[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [category, setCategory] = useState<ManualMemoryCategory>("ROUTINE");
  const [statement, setStatement] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");
  const [query, setQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<ManualMemoryCategory | "ALL">("ALL");
  const [stateFilter, setStateFilter] = useState<MemoryCandidate["state"] | "ALL">("ALL");
  const load = useCallback(async () => {
    setState("loading");
    try { setItems(await listMemoryCandidates(petId)); setState("ready"); }
    catch { setState("error"); }
  }, [petId]);
  useEffect(() => { void load(); }, [load]);
  async function createManual(event: FormEvent) {
    event.preventDefault();
    const wording = statement.trim();
    if (!wording) return;
    setCreating(true); setCreateError("");
    try {
      const candidate = await createManualMemoryCandidate(petId, { category, statement: wording });
      setItems((current) => [candidate, ...current]);
      setStatement("");
      setState("ready");
    } catch { setCreateError("手工候选保存失败；你的输入仍保留在表单中，请重试。"); }
    finally { setCreating(false); }
  }
  const visibleItems = items.filter((item) => {
    const matchesText = item.claim_snapshot.statement.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase());
    return matchesText && (categoryFilter === "ALL" || item.claim_snapshot.claim_type === categoryFilter) && (stateFilter === "ALL" || item.state === stateFilter);
  });
  return <section aria-labelledby="memory-title"><h3 id="memory-title">长期记忆候选</h3>
    <p className="section-help">可以由你直接写下，也可以来自你已确认的 Claim；建立候选不等于纳入，撤回也不会改写原始记录。</p>
    <form className="editor-form" onSubmit={(event) => void createManual(event)}>
      <label>记忆类别<select value={category} onChange={(event) => setCategory(event.target.value as ManualMemoryCategory)}>{Object.entries(memoryCategoryLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label>你的原话<textarea required maxLength={2000} value={statement} onChange={(event) => setStatement(event.target.value)} placeholder="例如：它在窗边放着蓝色毯子时更容易安定下来。" /></label>
      <Button variant="primary" busy={creating} type="submit">{creating ? "正在保存…" : "建立手工候选"}</Button>
      {createError && <StatusNotice tone="danger" role="alert">{createError}</StatusNotice>}
    </form>
    <div className="timeline-filters" aria-label="长期记忆筛选">
      <label>搜索<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索用户原话或候选内容" /></label>
      <label>类别<select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value as typeof categoryFilter)}><option value="ALL">全部类别</option>{Object.entries(memoryCategoryLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label>状态<select value={stateFilter} onChange={(event) => setStateFilter(event.target.value as typeof stateFilter)}><option value="ALL">全部状态</option>{Object.entries(memoryStateLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    </div>
    {state === "loading" && <p role="status">正在读取长期记忆候选…</p>}
    {state === "error" && <StatusNotice tone="warning" role="alert" action={<Button onClick={() => void load()}>重试</Button>}>候选读取失败。</StatusNotice>}
    {state === "ready" && items.length === 0 && <StatusNotice>尚无长期记忆候选。请先在 Episode 的已确认 Claim 中建立候选。</StatusNotice>}
    {state === "ready" && items.length > 0 && visibleItems.length === 0 && <StatusNotice>没有符合当前搜索与筛选条件的长期记忆。</StatusNotice>}
    {state === "ready" && visibleItems.map((item) => <CandidateCard key={item.id} candidate={item} onChange={(next) => setItems((current) => current.map((value) => value.id === next.id ? next : value))} />)}
  </section>;
}

function CandidateCard({ candidate, onChange }: { candidate: MemoryCandidate; onChange: (candidate: MemoryCandidate) => void }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const retry = useRef<{ decision: MemoryDecisionType; id: string } | null>(null);
  const [editing, setEditing] = useState(false);
  const [editCategory, setEditCategory] = useState<ManualMemoryCategory>(candidate.claim_snapshot.claim_type as ManualMemoryCategory);
  const [editStatement, setEditStatement] = useState(candidate.claim_snapshot.statement);
  const [savingEdit, setSavingEdit] = useState(false);
  const [editError, setEditError] = useState("");
  const revisions = candidate.revisions ?? [];
  const action: MemoryDecisionType | null = candidate.is_stale ? (candidate.decisions.at(-1)?.decision === "INCLUDE" ? "WITHDRAW" : null) : candidate.state === "ACTIVE" ? "WITHDRAW" : "INCLUDE";
  async function decide(decision: MemoryDecisionType) {
    setPending(true); setError("");
    const id = retry.current?.decision === decision ? retry.current.id : newRequestId("memory");
    retry.current = { decision, id };
    try { onChange(await decideMemoryCandidate(candidate.id, id, decision)); retry.current = null; }
    catch { setError("决定保存失败；候选内容和当前状态均已保留，请重试。"); }
    finally { setPending(false); }
  }
  async function saveEdit(event: FormEvent) {
    event.preventDefault();
    if (!editStatement.trim()) return;
    setSavingEdit(true); setEditError("");
    try { onChange(await updateManualMemoryCandidate(candidate.id, { category: editCategory, statement: editStatement.trim() })); setEditing(false); }
    catch { setEditError("修改保存失败；你的编辑内容仍保留，请重试。"); }
    finally { setSavingEdit(false); }
  }
  return <Surface tone={candidate.state === "ACTIVE" ? "emphasis" : "default"} className="memory-card">
    <div className="state-heading"><strong>候选 #{candidate.id}</strong><span>{memoryStateLabels[candidate.state]}{candidate.is_stale && candidate.state !== "STALE" ? " · 来源已变化" : ""}</span></div>
    <p>{candidate.claim_snapshot.statement}</p>
    <p className="meta-line">{candidate.source_type === "MANUAL" ? "用户原话" : "模型生成，经用户确认"} · {candidate.claim_snapshot.claim_type}{candidate.source_type === "CLAIM" ? ` · 置信度 ${candidate.claim_snapshot.confidence_label}` : ""}</p>
    {candidate.source_type === "MANUAL" && !editing && <Button onClick={() => setEditing(true)}>编辑手工记忆</Button>}
    {editing && <form className="editor-form" onSubmit={(event) => void saveEdit(event)}><label>类别<select value={editCategory} onChange={(event) => setEditCategory(event.target.value as ManualMemoryCategory)}>{Object.entries(memoryCategoryLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>用户原话<textarea required maxLength={2000} value={editStatement} onChange={(event) => setEditStatement(event.target.value)} /></label><div className="button-row"><Button type="submit" busy={savingEdit}>{savingEdit ? "正在保存…" : "保存修改"}</Button><Button type="button" onClick={() => { setEditing(false); setEditError(""); setEditCategory(candidate.claim_snapshot.claim_type as ManualMemoryCategory); setEditStatement(candidate.claim_snapshot.statement); }}>取消</Button></div>{editError && <StatusNotice tone="danger" role="alert">{editError}</StatusNotice>}</form>}
    {revisions.length > 0 && <details><summary>修订历史（{revisions.length}）</summary><ol>{revisions.slice().reverse().map((revision) => <li key={revision.id}>版本 {revision.revision_number} · {memoryCategoryLabels[revision.category]} · {new Date(revision.created_at).toLocaleString()}<br />{revision.statement}</li>)}</ol></details>}
    {candidate.is_stale && <StatusNotice tone="warning">来源 Episode 已变化；该候选不可重新纳入，但仍可撤回既有纳入决定。</StatusNotice>}
    {action && <Button variant={action === "WITHDRAW" ? "danger" : "primary"} busy={pending} onClick={() => void decide(action)}>{pending ? "正在保存…" : action === "INCLUDE" ? (candidate.state === "WITHDRAWN" ? "重新纳入长期记忆" : "纳入长期记忆") : "撤回长期记忆"}</Button>}
    {error && <StatusNotice tone="danger" role="alert">{error}</StatusNotice>}
  </Surface>;
}

function LifeEvents({ petId }: { petId: number }) {
  const [items, setItems] = useState<LifeEvent[]>([]);
  const [nearbyPages, setNearbyPages] = useState<Record<number, TimelinePage>>({});
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [eventType, setEventType] = useState<LifeEventType>("environment_change");
  const [happenedAt, setHappenedAt] = useState(toLocalInput(new Date().toISOString()));
  const [description, setDescription] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const generation = useRef(0);
  const load = useCallback(async () => {
    const current = ++generation.current;
    setState("loading"); setItems([]); setNearbyPages({});
    try {
      const events = await listLifeEvents(petId);
      const pageEntries = await Promise.all(events.map(async (item) => {
        const center = new Date(item.happened_at).getTime();
        const page = await getTimeline(petId, 1, 100, { from: new Date(center - 7 * 86400000).toISOString(), to: new Date(center + 7 * 86400000).toISOString() });
        return [item.id, page] as const;
      }));
      if (current !== generation.current) return;
      setItems(events); setNearbyPages(Object.fromEntries(pageEntries)); setState("ready");
    } catch { if (current === generation.current) setState("error"); }
  }, [petId]);
  useEffect(() => { void load(); return () => { generation.current += 1; }; }, [load]);
  function resetForm() { setEditingId(null); setEventType("environment_change"); setHappenedAt(toLocalInput(new Date().toISOString())); setDescription(""); setSaveError(""); }
  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setSaveError("");
    const payload = { event_type: eventType, happened_at: new Date(happenedAt).toISOString(), description: description.trim() || null };
    try {
      if (editingId === null) await createLifeEvent(petId, payload);
      else await updateLifeEvent(editingId, payload);
      resetForm();
      await load();
    } catch { setSaveError("生活事件保存失败；输入仍保留，请重试。"); }
    finally { setSaving(false); }
  }
  function edit(item: LifeEvent) { setEditingId(item.id); setEventType(item.event_type); setHappenedAt(toLocalInput(item.happened_at)); setDescription(item.description ?? ""); setSaveError(""); }
  return <section aria-labelledby="life-events-title"><h3 id="life-events-title">生活事件与时间邻近记录</h3>
    <p className="section-help">事件与“前 7 天（含起点）至后 7 天（不含上界）”的已记录事实按时间并列；时间接近不代表事件导致了行为变化。</p>
    <form className="editor-form" onSubmit={(event) => void save(event)}><label>事件类型<select value={eventType} onChange={(event) => setEventType(event.target.value as LifeEventType)}>{Object.entries(lifeEventLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>发生时间<input required type="datetime-local" value={happenedAt} onChange={(event) => setHappenedAt(event.target.value)} /></label><label>事实描述<textarea maxLength={2000} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="只写发生了什么，不推断原因" /></label><div className="button-row"><Button type="submit" busy={saving}>{saving ? "正在保存…" : editingId === null ? "添加生活事件" : "保存修改"}</Button>{editingId !== null && <Button type="button" onClick={resetForm}>取消编辑</Button>}</div>{saveError && <StatusNotice tone="danger" role="alert">{saveError}</StatusNotice>}</form>
    {state === "loading" && <p role="status">正在读取生活事件与记录…</p>}
    {state === "error" && <StatusNotice tone="warning" role="alert" action={<Button onClick={() => void load()}>重试</Button>}>生活事件读取失败。</StatusNotice>}
    {state === "ready" && items.length === 0 && <StatusNotice>尚无生活事件。添加后可查看时间邻近的事实记录。</StatusNotice>}
    {items.map((item) => { const nearby = nearbyPages[item.id]; return <Surface key={item.id} className="memory-card"><div className="state-heading"><strong>{lifeEventLabels[item.event_type]}</strong><span>{new Date(item.happened_at).toLocaleString()}</span></div><p>{item.description || "未填写描述"}</p><Button onClick={() => edit(item)}>编辑事件</Button><details><summary>前后 7 天的事实记录（{nearby?.total ?? 0}）</summary>{!nearby || nearby.total === 0 ? <p>这段时间暂无已记录事实。</p> : <ul>{nearby.items.map((episode) => <li key={episode.id}>{new Date(episode.happened_at).toLocaleString()} · {episode.raw_owner_input}</li>)}</ul>}{nearby?.has_more && <p className="meta-line">共有 {nearby.total} 条；此处展示最近 100 条，可在 Timeline 按日期查看完整记录。</p>}<p className="meta-line">这里只展示时间邻近，不生成因果解释或诊断。</p></details></Surface>; })}
  </section>;
}

function toLocalInput(value: string): string {
  const date = new Date(value);
  const shifted = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return shifted.toISOString().slice(0, 16);
}

function EvidenceGuidance({ petId }: { petId: number }) {
  const [recentPage, setRecentPage] = useState<TimelinePage | null>(null);
  const [previousPage, setPreviousPage] = useState<TimelinePage | null>(null);
  const [anchor, setAnchor] = useState<number | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const generation = useRef(0);
  const load = useCallback(async () => {
    const current = ++generation.current; setState("loading"); setRecentPage(null); setPreviousPage(null); setAnchor(null);
    try {
      const latest = await getTimeline(petId, 1, 1);
      if (current !== generation.current) return;
      if (latest.items.length === 0) { setState("ready"); return; }
      const latestAt = new Date(latest.items[0].happened_at).getTime();
      const currentStart = new Date(latestAt - 7 * 86400000).toISOString();
      const previousStart = new Date(latestAt - 14 * 86400000).toISOString();
      const exclusiveEnd = new Date(latestAt + 1).toISOString();
      const [recent, previous] = await Promise.all([
        getTimeline(petId, 1, 100, { from: currentStart, to: exclusiveEnd }),
        getTimeline(petId, 1, 100, { from: previousStart, to: currentStart }),
      ]);
      if (current === generation.current) { setAnchor(latestAt); setRecentPage(recent); setPreviousPage(previous); setState("ready"); }
    }
    catch { if (current === generation.current) setState("error"); }
  }, [petId]);
  useEffect(() => { void load(); return () => { generation.current += 1; }; }, [load]);
  if (state === "loading") return <section aria-labelledby="evidence-guidance-title"><h3 id="evidence-guidance-title">重要变化与观察提示</h3><p role="status">正在整理已记录事实…</p></section>;
  if (state === "error") return <section aria-labelledby="evidence-guidance-title"><h3 id="evidence-guidance-title">重要变化与观察提示</h3><StatusNotice tone="warning" role="alert" action={<Button onClick={() => void load()}>重试</Button>}>记录读取失败，未生成摘要。</StatusNotice></section>;
  if (!recentPage || !previousPage || anchor === null) return <section aria-labelledby="evidence-guidance-title"><h3 id="evidence-guidance-title">重要变化与观察提示</h3><StatusNotice>尚无事实记录；不会用空数据生成变化结论。</StatusNotice></section>;
  const recent = recentPage.items;
  const previous = previousPage.items;
  const suggestions: string[] = [];
  if (recent.some((item) => item.duration_seconds === null)) suggestions.push("下次可记录持续时长，便于按相同单位回看。");
  if (recent.some((item) => !item.location)) suggestions.push("下次可记录发生地点，帮助区分不同环境下的事实。");
  if (recent.some((item) => !item.trigger_context)) suggestions.push("下次可记录发生前刚刚出现的可观察背景，不必解释原因。");
  if (new Set(recent.map((item) => item.happened_at.slice(0, 10))).size < 3) suggestions.push("可在不同日期重复观察；当前日期覆盖较少，不宜概括稳定规律。");
  return <section aria-labelledby="evidence-guidance-title"><h3 id="evidence-guidance-title">重要变化与观察提示</h3>
    <p className="section-help">固定规则直接读取事实记录；不调用 AI，不把记录次数当作症状严重程度，也不作因果或诊断判断。</p>
    <Surface tone="subtle" className="memory-card"><h4>相对最新记录的两个 7 天窗口</h4><p className="meta-line">锚点：{new Date(anchor).toLocaleString()}</p><p>记录数量：当前窗口 {recentPage.total} 条，前一窗口 {previousPage.total} 条。{recentPage.total === previousPage.total ? "数量没有变化。" : "数量存在差异；这只反映记录频次。"}</p><details><summary>查看已加载来源（{recent.length + previous.length}）</summary><ul>{[...recent.map((item) => ({ item, window: "current" })), ...previous.map((item) => ({ item, window: "previous" }))].map(({ item, window }) => <li key={`${window}-${item.id}`}>Episode #{item.id} · {new Date(item.happened_at).toLocaleString()} · {item.raw_owner_input}</li>)}</ul>{(recentPage.has_more || previousPage.has_more) && <p>来源超过 100 条；数量使用完整查询计数，列表仅展示每个窗口最近 100 条。</p>}</details></Surface>
    <Surface className="memory-card"><h4>可能还需要观察什么</h4>{suggestions.length === 0 ? <p>已加载样本的时间、地点、持续时长和发生前背景较完整；可以继续用相同字段记录。</p> : <ul>{suggestions.map((item) => <li key={item}>{item}</li>)}</ul>}<p className="meta-line">提示基于当前窗口已加载的最多 100 条记录；它们只反映记录完整性，不是对宠物状态的解释。</p></Surface>
  </section>;
}

function QuantitativeBaseline({ petId }: { petId: number }) {
  const [window, setWindow] = useState<BaselineWindow>("7d");
  const [snapshot, setSnapshot] = useState<BaselineSnapshot | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error">("loading");
  const [recomputing, setRecomputing] = useState(false);
  const [recomputeError, setRecomputeError] = useState("");
  const load = useCallback(async () => {
    setState("loading"); setSnapshot(null);
    try { setSnapshot(await getLatestBaselineSnapshot(petId, window)); setState("ready"); }
    catch (error) { setState(error instanceof ApiError && error.status === 404 ? "empty" : "error"); }
  }, [petId, window]);
  useEffect(() => { void load(); }, [load]);
  async function recompute() {
    setRecomputing(true); setRecomputeError("");
    try { setSnapshot(await recomputeBaselineSnapshot(petId, window, new Date().toISOString())); setState("ready"); }
    catch { setRecomputeError("重算失败；当前已显示的快照保持不变，请重试。"); }
    finally { setRecomputing(false); }
  }
  return <section aria-labelledby="quantitative-baseline-title"><h3 id="quantitative-baseline-title">量化 Baseline</h3>
    <p className="section-help">由已记录数据按固定算法计算，不是模型判断；每个快照冻结时间边界与来源。</p>
    <div className="window-tabs" aria-label="Baseline 时间窗口">{windows.map((item) => <Button key={item.value} variant={item.value === window ? "primary" : "secondary"} aria-pressed={item.value === window} onClick={() => setWindow(item.value)}>{item.label}</Button>)}</div>
    {state === "loading" && <p role="status">正在读取 {windowLabels[window]}快照…</p>}
    {state === "error" && <StatusNotice tone="warning" role="alert" action={<Button onClick={() => void load()}>重试读取</Button>}>快照读取失败。</StatusNotice>}
    {state === "empty" && <StatusNotice title="尚无快照" action={<Button busy={recomputing} onClick={() => void recompute()}>计算 {windowLabels[window]} Baseline</Button>}>不会用空数据推测趋势。</StatusNotice>}
    {snapshot && <SnapshotView snapshot={snapshot} onRecompute={recompute} recomputing={recomputing} />}
    {recomputeError && <StatusNotice tone="danger" role="alert" action={<Button onClick={() => void recompute()}>重试重算</Button>}>{recomputeError}</StatusNotice>}
  </section>;
}

function SnapshotView({ snapshot, onRecompute, recomputing }: { snapshot: BaselineSnapshot; onRecompute: () => void; recomputing: boolean }) {
  return <Surface tone="subtle" className="snapshot-card">
    <div className="state-heading"><strong>{windowLabels[snapshot.window]}快照 · {snapshotStatusLabels[snapshot.status]}</strong>{snapshot.is_stale && <span className="stale-badge">来源已变化</span>}</div>
    <p className="meta-line">样本 {snapshot.sample_count} · 截止 {new Date(snapshot.as_of).toLocaleString()} · 算法 {snapshot.algorithm_version}</p>
    {snapshot.status !== "READY" && <StatusNotice tone="info">{snapshot.status === "EMPTY" ? "窗口内没有可计算的数据。" : "样本不足，不生成趋势。"}</StatusNotice>}
    <Button busy={recomputing} onClick={onRecompute}>{recomputing ? "正在重算…" : "按当前数据重算"}</Button>
    <div className="metric-list">{snapshot.metrics_json.map((metric) => <MetricView key={metric.key} metric={metric} evidences={snapshot.evidences.filter((item) => item.metric_key === metric.key)} />)}</div>
  </Surface>;
}

function MetricView({ metric, evidences }: { metric: BaselineMetric; evidences: BaselineSnapshot["evidences"] }) {
  const currentTrendValue = metric.trend?.current_median ?? metric.trend?.current_count;
  const comparisonTrendValue = metric.trend?.comparison_median ?? metric.trend?.comparison_count;
  const trendMax = Math.max(currentTrendValue ?? 0, comparisonTrendValue ?? 0, 1);
  const directionLabels = { INCREASED: "增加", DECREASED: "减少", STABLE: "相近" } as const;
  return <article className="metric-card"><h4>{metric.behavior_type || metric.episode_type || metric.field}</h4>
    <p>{"median" in metric ? `中位数 ${metric.median ?? "—"}${metric.unit ? ` ${metric.unit}` : ""} · 范围 ${metric.min ?? "—"}–${metric.max ?? "—"}` : `出现 ${metric.count} 次 · 覆盖 ${metric.observation_days ?? 0} 天`}</p>
    <p className="meta-line">样本 {metric.count} · {snapshotStatusLabels[metric.status as keyof typeof snapshotStatusLabels] ?? metric.status}{metric.trend ? ` · 与前一等长窗口相比：${directionLabels[metric.trend.direction]}` : " · 无趋势结论"}</p>
    {metric.trend && currentTrendValue !== undefined && comparisonTrendValue !== undefined && <div className="trend-bars" aria-label={`当前 ${currentTrendValue}，前一窗口 ${comparisonTrendValue}`}><div><span>前一窗口</span><i style={{ width: `${comparisonTrendValue / trendMax * 100}%` }} /><b>{comparisonTrendValue}</b></div><div><span>当前窗口</span><i style={{ width: `${currentTrendValue / trendMax * 100}%` }} /><b>{currentTrendValue}</b></div></div>}
    <details><summary>查看来源（{evidences.length}）</summary>{evidences.length === 0 ? <p>无来源项。</p> : <ul>{evidences.map((item) => <li key={item.id}><strong>{item.window_segment}</strong> · {item.source_type} · {item.field_path}<br />值：{formatValue(item.value_snapshot)} · {new Date(item.observed_at).toLocaleString()}{item.episode_id === null ? " · 原记录已删除，保留快照" : ""}</li>)}</ul>}</details>
  </article>;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "未填写";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value, null, 2);
}
