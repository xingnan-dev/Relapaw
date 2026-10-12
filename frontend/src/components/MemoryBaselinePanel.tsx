import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, decideMemoryCandidate, getLatestBaselineSnapshot, getPetBaseline, listMemoryCandidates, recomputeBaselineSnapshot } from "../api";
import type { BaselineMetric, BaselineSnapshot, BaselineWindow, MemoryCandidate, MemoryDecisionType, PetBaseline } from "../types";
import { Button, StatusNotice, Surface } from "./ui";

const windows: BaselineWindow[] = ["7d", "30d", "90d", "all"];
const baselineLabels: Record<keyof Omit<PetBaseline, "id" | "pet_id">, string> = {
  social_behavior: "社交行为", activity_pattern: "活动规律", feeding_pattern: "饮食规律",
  resting_pattern: "休息规律", handling_preference: "接触偏好", hiding_pattern: "躲藏规律",
};

function newRequestId(prefix: string) {
  return globalThis.crypto?.randomUUID?.() ?? `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function MemoryBaselinePanel({ petId }: { petId: number }) {
  return <div className="memory-baseline-stack">
    <ManualBaseline petId={petId} />
    <MemoryCandidates petId={petId} />
    <QuantitativeBaseline petId={petId} />
  </div>;
}

function ManualBaseline({ petId }: { petId: number }) {
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error">("loading");
  const [baseline, setBaseline] = useState<PetBaseline | null>(null);
  const load = useCallback(async () => {
    setState("loading");
    try { setBaseline(await getPetBaseline(petId)); setState("ready"); }
    catch (error) { setState(error instanceof ApiError && error.status === 404 ? "empty" : "error"); }
  }, [petId]);
  useEffect(() => { void load(); }, [load]);
  return <section aria-labelledby="manual-baseline-title"><h3 id="manual-baseline-title">人工档案 Baseline</h3>
    <p className="section-help">由用户明确填写的日常模式，与模型候选和量化快照分开保存。</p>
    {state === "loading" && <p role="status">正在读取人工 Baseline…</p>}
    {state === "empty" && <StatusNotice>尚未填写人工 Baseline。</StatusNotice>}
    {state === "error" && <StatusNotice tone="warning" role="alert" action={<Button onClick={() => void load()}>重试</Button>}>读取失败，页面其他状态已保留。</StatusNotice>}
    {state === "ready" && baseline && <Surface className="baseline-definition-list"><dl>{Object.entries(baselineLabels).map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{formatValue(baseline[key as keyof typeof baselineLabels])}</dd></div>)}</dl></Surface>}
  </section>;
}

function MemoryCandidates({ petId }: { petId: number }) {
  const [items, setItems] = useState<MemoryCandidate[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const load = useCallback(async () => {
    setState("loading");
    try { setItems(await listMemoryCandidates(petId)); setState("ready"); }
    catch { setState("error"); }
  }, [petId]);
  useEffect(() => { void load(); }, [load]);
  return <section aria-labelledby="memory-title"><h3 id="memory-title">长期记忆候选</h3>
    <p className="section-help">仅来自用户已确认的 Claim；建立候选不等于纳入，撤回也不会改写原始记录。</p>
    {state === "loading" && <p role="status">正在读取长期记忆候选…</p>}
    {state === "error" && <StatusNotice tone="warning" role="alert" action={<Button onClick={() => void load()}>重试</Button>}>候选读取失败。</StatusNotice>}
    {state === "ready" && items.length === 0 && <StatusNotice>尚无长期记忆候选。请先在 Episode 的已确认 Claim 中建立候选。</StatusNotice>}
    {items.map((item) => <CandidateCard key={item.id} candidate={item} onChange={(next) => setItems((current) => current.map((value) => value.id === next.id ? next : value))} />)}
  </section>;
}

function CandidateCard({ candidate, onChange }: { candidate: MemoryCandidate; onChange: (candidate: MemoryCandidate) => void }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const retry = useRef<{ decision: MemoryDecisionType; id: string } | null>(null);
  const action: MemoryDecisionType | null = candidate.is_stale ? (candidate.decisions.at(-1)?.decision === "INCLUDE" ? "WITHDRAW" : null) : candidate.state === "ACTIVE" ? "WITHDRAW" : "INCLUDE";
  async function decide(decision: MemoryDecisionType) {
    setPending(true); setError("");
    const id = retry.current?.decision === decision ? retry.current.id : newRequestId("memory");
    retry.current = { decision, id };
    try { onChange(await decideMemoryCandidate(candidate.id, id, decision)); retry.current = null; }
    catch { setError("决定保存失败；候选内容和当前状态均已保留，请重试。"); }
    finally { setPending(false); }
  }
  return <Surface tone={candidate.state === "ACTIVE" ? "emphasis" : "default"} className="memory-card">
    <div className="state-heading"><strong>候选 #{candidate.id}</strong><span>{candidate.state}{candidate.is_stale ? " · stale" : ""}</span></div>
    <p>{candidate.claim_snapshot.statement}</p>
    <p className="meta-line">模型生成，经用户确认 · {candidate.claim_snapshot.claim_type} · 置信度 {candidate.claim_snapshot.confidence_label}</p>
    {candidate.is_stale && <StatusNotice tone="warning">来源 Episode 已变化；该候选不可重新纳入，但仍可撤回既有纳入决定。</StatusNotice>}
    {action && <Button variant={action === "WITHDRAW" ? "danger" : "primary"} busy={pending} onClick={() => void decide(action)}>{pending ? "正在保存…" : action === "INCLUDE" ? (candidate.state === "WITHDRAWN" ? "重新纳入长期记忆" : "纳入长期记忆") : "撤回长期记忆"}</Button>}
    {error && <StatusNotice tone="danger" role="alert">{error}</StatusNotice>}
  </Surface>;
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
    <div className="window-tabs" aria-label="Baseline 时间窗口">{windows.map((item) => <Button key={item} variant={item === window ? "primary" : "secondary"} aria-pressed={item === window} onClick={() => setWindow(item)}>{item}</Button>)}</div>
    {state === "loading" && <p role="status">正在读取 {window} 快照…</p>}
    {state === "error" && <StatusNotice tone="warning" role="alert" action={<Button onClick={() => void load()}>重试读取</Button>}>快照读取失败。</StatusNotice>}
    {state === "empty" && <StatusNotice title="尚无快照" action={<Button busy={recomputing} onClick={() => void recompute()}>计算 {window} Baseline</Button>}>不会用空数据推测趋势。</StatusNotice>}
    {snapshot && <SnapshotView snapshot={snapshot} onRecompute={recompute} recomputing={recomputing} />}
    {recomputeError && <StatusNotice tone="danger" role="alert" action={<Button onClick={() => void recompute()}>重试重算</Button>}>{recomputeError}</StatusNotice>}
  </section>;
}

function SnapshotView({ snapshot, onRecompute, recomputing }: { snapshot: BaselineSnapshot; onRecompute: () => void; recomputing: boolean }) {
  return <Surface tone="subtle" className="snapshot-card">
    <div className="state-heading"><strong>{snapshot.window} 快照 · {snapshot.status}</strong>{snapshot.is_stale && <span className="stale-badge">stale · 来源已变化</span>}</div>
    <p className="meta-line">样本 {snapshot.sample_count} · 截止 {new Date(snapshot.as_of).toLocaleString()} · 算法 {snapshot.algorithm_version}</p>
    {snapshot.status !== "READY" && <StatusNotice tone="info">{snapshot.status === "EMPTY" ? "窗口内没有可计算的数据。" : "样本不足，不生成趋势。"}</StatusNotice>}
    <Button busy={recomputing} onClick={onRecompute}>{recomputing ? "正在重算…" : "按当前数据重算"}</Button>
    <div className="metric-list">{snapshot.metrics_json.map((metric) => <MetricView key={metric.key} metric={metric} evidences={snapshot.evidences.filter((item) => item.metric_key === metric.key)} />)}</div>
  </Surface>;
}

function MetricView({ metric, evidences }: { metric: BaselineMetric; evidences: BaselineSnapshot["evidences"] }) {
  return <article className="metric-card"><h4>{metric.behavior_type || metric.episode_type || metric.field}</h4>
    <p>{"median" in metric ? `中位数 ${metric.median ?? "—"}${metric.unit ? ` ${metric.unit}` : ""} · 范围 ${metric.min ?? "—"}–${metric.max ?? "—"}` : `出现 ${metric.count} 次 · 覆盖 ${metric.observation_days ?? 0} 天`}</p>
    <p className="meta-line">样本 {metric.count} · {metric.status}{metric.trend ? ` · 趋势 ${formatValue(metric.trend)}` : " · 无趋势结论"}</p>
    <details><summary>查看来源（{evidences.length}）</summary>{evidences.length === 0 ? <p>无来源项。</p> : <ul>{evidences.map((item) => <li key={item.id}><strong>{item.window_segment}</strong> · {item.source_type} · {item.field_path}<br />值：{formatValue(item.value_snapshot)} · {new Date(item.observed_at).toLocaleString()}{item.episode_id === null ? " · 原记录已删除，保留快照" : ""}</li>)}</ul>}</details>
  </article>;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "未填写";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value, null, 2);
}
