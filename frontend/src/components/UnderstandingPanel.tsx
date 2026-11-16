import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, createAnalysisRun, createMemoryCandidate, decideClaim, listAnalysisRuns } from "../api";
import type { AnalysisClaim, AnalysisRun, ConfirmationDecision, Episode } from "../types";
import { Button, StatusNotice } from "./ui";

type RequestState = "idle" | "loading" | "completed" | "safety-blocked" | "model-not-configured" | "invalid-output" | "network-error" | "provider-auth" | "provider-timeout" | "provider-rate-limit" | "provider-unavailable";

function requestId() {
  return globalThis.crypto?.randomUUID?.() ?? `analysis-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function stateForRun(run: AnalysisRun): RequestState {
  if (run.status === "RUNNING") return "loading";
  if (run.status === "BLOCKED_BY_SAFETY") return "safety-blocked";
  if (run.status === "COMPLETED") return "completed";
  if (run.error_code === "MODEL_NOT_CONFIGURED") return "model-not-configured";
  if (run.error_code === "MODEL_OUTPUT_INVALID" || run.error_code === "MODEL_EVIDENCE_INVALID" || run.error_code?.startsWith("MODEL_EXTRACTION_")) return "invalid-output";
  return "network-error";
}

const stateCopy: Record<Exclude<RequestState, "idle" | "loading" | "completed">, string> = {
  "safety-blocked": "人工 Safety Check 不允许启动文本分析。请优先处理安全问题；本页不会修改 Safety Check 或兽医升级记录。",
  "model-not-configured": "MODEL_NOT_CONFIGURED：真实文本模型尚未配置。本次失败已记录，没有生成或伪造分析结果。",
  "invalid-output": "模型输出未通过契约校验，已安全拒绝。没有把无效内容展示为结果。",
  "network-error": "网络请求失败，当前页面、历史记录和已完成的逐条决定均已保留。",
  "provider-auth": "模型服务认证或权限配置无效。没有生成分析结果；请由服务端管理员检查 API 配置。",
  "provider-timeout": "模型服务响应超时。本次失败已记录，页面状态保持不变，可以重试。",
  "provider-rate-limit": "模型服务当前达到调用限制。本次失败已记录，请稍后重试。",
  "provider-unavailable": "模型服务暂时不可用或拒绝了本次请求。没有保存部分分析结果，请稍后重试。",
};

export function UnderstandingPanel({ episode, aiAnalysisEnabled, onOpenMemory = () => undefined }: { episode: Episode; aiAnalysisEnabled: boolean; onOpenMemory?: () => void }) {
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [historyState, setHistoryState] = useState<"loading" | "ready" | "error">("loading");
  const [requestState, setRequestState] = useState<RequestState>("idle");
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const retryRequestId = useRef<string | null>(null);

  const loadHistory = useCallback(async () => {
    setHistoryState("loading");
    try {
      const response = await listAnalysisRuns(episode.id);
      const items = Array.isArray(response) ? response : [];
      setRuns(items);
      setHistoryState("ready");
      if (items.length) setActiveRunId((current) => current ?? items[0].id);
    } catch {
      setHistoryState("error");
    }
  }, [episode.id]);

  useEffect(() => { void loadHistory(); }, [episode.id]);

  useEffect(() => {
    const running = runs.find((run) => run.id === activeRunId && run.status === "RUNNING");
    if (!running) return;
    const timer = window.setTimeout(() => {
      void listAnalysisRuns(episode.id).then((items) => {
        const next = Array.isArray(items) ? items : [];
        setRuns(next);
        const current = next.find((run) => run.id === activeRunId);
        if (current && current.status !== "RUNNING") setRequestState(stateForRun(current));
      }).catch(() => setRequestState("network-error"));
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [runs, activeRunId, episode.id]);

  async function analyze() {
    if (episode.safety_check?.result !== "NORMAL") {
      setRequestState("safety-blocked");
      return;
    }
    setRequestState("loading");
    const id = retryRequestId.current ?? requestId();
    retryRequestId.current = id;
    try {
      const run = await createAnalysisRun(episode.id, id);
      retryRequestId.current = null;
      setRuns((current) => [run, ...current.filter((item) => item.id !== run.id)]);
      setActiveRunId(run.id);
      setRequestState(stateForRun(run));
    } catch (error) {
      if (error instanceof ApiError) {
        retryRequestId.current = null;
        if (error.code === "MODEL_NOT_CONFIGURED") setRequestState("model-not-configured");
        else if (error.code === "MODEL_OUTPUT_INVALID" || error.code === "MODEL_EVIDENCE_INVALID" || error.code?.startsWith("MODEL_EXTRACTION_")) setRequestState("invalid-output");
        else if (error.code === "ANALYSIS_BLOCKED_BY_SAFETY" || error.code === "SAFETY_CHECK_REQUIRED") setRequestState("safety-blocked");
        else if (error.code === "MODEL_AUTHENTICATION_FAILED" || error.code === "MODEL_PERMISSION_DENIED") setRequestState("provider-auth");
        else if (error.code === "MODEL_TIMEOUT") setRequestState("provider-timeout");
        else if (error.code === "MODEL_RATE_LIMITED") setRequestState("provider-rate-limit");
        else if (error.code?.startsWith("MODEL_")) setRequestState("provider-unavailable");
        else setRequestState("network-error");
        await loadHistory();
      } else {
        setRequestState("network-error");
      }
    }
  }

  function updateClaim(runId: number, claimId: number, decision: ConfirmationDecision, confirmationId: number, createdAt: string) {
    setRuns((current) => current.map((run) => run.id !== runId ? run : {
      ...run,
      claims: run.claims.map((claim) => claim.id !== claimId ? claim : {
        ...claim,
        status: decision,
        confirmations: [{ id: confirmationId, claim_id: claimId, decision, note: null, created_at: createdAt }],
      }),
    }));
  }

  const activeRun = runs.find((run) => run.id === activeRunId) ?? null;
  const blocked = episode.safety_check?.result !== "NORMAL";
  return <section className="understanding-panel" aria-labelledby="understanding-title">
    <p className="eyebrow">AI 辅助 · 原文抽取</p><h3 id="understanding-title">从原话中提取可核对片段</h3>
    <StatusNotice tone="warning" title="只允许引用你的原话">模型只能逐字摘取可观察事实候选，并单独标出你明确表达的理解；不得补写原因、意图、诊断或其他事实。每条仍需你确认或拒绝。</StatusNotice>
    <div className="input-preview" aria-label="分析输入预览">
      <Detail label="你的原话"><p>{episode.raw_owner_input}</p></Detail>
      <Detail label="用于核对分类的事实字段">{episode.observations.length ? episode.observations.map((item) => <p key={item.id}>{item.description}</p>) : <p>无；模型不得生成事实候选</p>}</Detail>
      <Detail label="用于核对分类的主人理解">{episode.owner_interpretations.length ? episode.owner_interpretations.map((item) => <p key={item.id}>{item.interpretation}</p>) : <p>未填写；模型不得生成主人理解</p>}</Detail>
    </div>
    {!blocked && aiAnalysisEnabled && <Button variant="primary" className="primary" busy={requestState === "loading"} onClick={() => void analyze()}>{requestState === "loading" ? "正在分析…" : "开始文本分析"}</Button>}
    {!blocked && !aiAnalysisEnabled && <StatusNotice tone="info" title="当前未启用运行时 AI">可以查看已有评估结果，但不能创建新的分析。当前模型尚未通过资格评估。</StatusNotice>}
    {blocked && <StatusNotice tone="danger" role="status" title="已因安全状态阻断">{stateCopy["safety-blocked"]}</StatusNotice>}
    {requestState !== "idle" && requestState !== "loading" && requestState !== "completed" && !blocked && <StatusNotice tone="warning" role="alert" action={<Button onClick={() => void analyze()}>重试分析</Button>}>{stateCopy[requestState]}</StatusNotice>}
    {requestState === "completed" && <StatusNotice tone="success" role="status">原文抽取完成。请逐条确认或拒绝；系统没有改写你的记录。</StatusNotice>}
    <section aria-labelledby="analysis-history-title"><h4 id="analysis-history-title">分析历史</h4>
      {historyState === "loading" && <p role="status">正在读取分析历史…</p>}
      {historyState === "error" && <StatusNotice tone="warning" role="status" action={<Button onClick={() => void loadHistory()}>重试历史</Button>}>分析历史读取失败，当前记录仍保留。</StatusNotice>}
      {historyState === "ready" && runs.length === 0 && <p>尚无分析历史。</p>}
      {runs.length > 0 && <div className="analysis-history">{runs.map((run) => <button key={run.id} aria-pressed={run.id === activeRunId} onClick={() => setActiveRunId(run.id)}>分析 #{run.id} · {runStatus(run.status)}{run.is_stale ? " · 来源已变化" : ""}<small>{new Date(run.created_at).toLocaleString()} · {run.error_code || "无错误"}</small></button>)}</div>}
    </section>
    {activeRun && <AnalysisRunView run={activeRun} readOnly={!aiAnalysisEnabled} onOpenMemory={onOpenMemory} onDecision={(claimId, decision, confirmationId, createdAt) => updateClaim(activeRun.id, claimId, decision, confirmationId, createdAt)} />}
  </section>;
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return <section><strong>{label}</strong>{children}</section>;
}

function runStatus(status: AnalysisRun["status"]) {
  return ({ RUNNING: "进行中", COMPLETED: "已完成", FAILED: "失败", BLOCKED_BY_SAFETY: "已被安全状态阻断" } as const)[status];
}

function AnalysisRunView({ run, readOnly, onDecision, onOpenMemory }: { run: AnalysisRun; readOnly: boolean; onDecision: (claimId: number, decision: ConfirmationDecision, confirmationId: number, createdAt: string) => void; onOpenMemory: () => void }) {
  const observations = run.claims.filter((claim) => claim.candidate_kind === "OBSERVATION");
  const interpretations = run.claims.filter((claim) => claim.candidate_kind === "OWNER_INTERPRETATION");
  const legacy = run.claims.filter((claim) => claim.candidate_kind === "LEGACY_INTERPRETATION");
  return <article className="analysis-run" aria-label={`分析 ${run.id}`}>
    <header><h4>分析 #{run.id}</h4>{run.is_stale && <strong className="stale-badge">来源已变化 · 结果可能过期</strong>}</header>
    <p><strong>状态：</strong>{runStatus(run.status)}{run.error_code ? ` · ${run.error_code}` : ""}</p>
    <details><summary>技术详情</summary><dl className="contract-meta"><dt>模型</dt><dd>{run.model_provider} / {run.model_name} / {run.model_version}</dd><dt>接入方式</dt><dd>{run.adapter_name}</dd><dt>提示契约</dt><dd>{run.prompt_contract_version}</dd><dt>输入契约</dt><dd>{run.input_contract_version}</dd><dt>输出契约</dt><dd>{run.output_contract_version}</dd></dl></details>
    {run.status === "BLOCKED_BY_SAFETY" && <StatusNotice tone="danger" title="已因安全状态阻断">没有调用模型，也没有生成候选。</StatusNotice>}
    {run.status === "RUNNING" && <StatusNotice tone="info">此请求已被服务端接收，分析仍在进行；相同 request_id 不会重复调用模型。</StatusNotice>}
    {run.status === "FAILED" && <StatusNotice tone="warning">此次分析失败，没有可确认的模型结果。</StatusNotice>}
    {observations.length > 0 && <section><h5>可观察事实候选</h5>{observations.map((claim) => <ClaimView key={claim.id} claim={claim} runStale={run.is_stale} readOnly={readOnly} onDecision={onDecision} onOpenMemory={onOpenMemory} />)}</section>}
    {interpretations.length > 0 && <section><h5>主人明确表达的理解</h5>{interpretations.map((claim) => <ClaimView key={claim.id} claim={claim} runStale={run.is_stale} readOnly={readOnly} onDecision={onDecision} onOpenMemory={onOpenMemory} />)}</section>}
    {legacy.length > 0 && <section><h5>历史候选理解</h5>{legacy.map((claim) => <ClaimView key={claim.id} claim={claim} runStale={run.is_stale} readOnly={readOnly} onDecision={onDecision} onOpenMemory={onOpenMemory} />)}</section>}
  </article>;
}

function ClaimView({ claim, runStale, readOnly, onDecision, onOpenMemory }: { claim: AnalysisClaim; runStale: boolean; readOnly: boolean; onDecision: (claimId: number, decision: ConfirmationDecision, confirmationId: number, createdAt: string) => void; onOpenMemory: () => void }) {
  const [pending, setPending] = useState<ConfirmationDecision | null>(null);
  const [error, setError] = useState("");
  const [candidateState, setCandidateState] = useState<"idle" | "saving" | "created">("idle");
  const [candidateError, setCandidateError] = useState("");
  async function decide(decision: ConfirmationDecision) {
    setPending(decision); setError("");
    try {
      const confirmation = await decideClaim(claim.id, decision);
      onDecision(claim.id, decision, confirmation.id, confirmation.created_at);
    } catch {
      setError("决定保存失败；当前 Claim、分析结果与既有决定均保留，请重试。");
    } finally { setPending(null); }
  }
  async function materializeCandidate() {
    setCandidateState("saving"); setCandidateError("");
    try { await createMemoryCandidate(claim.id); setCandidateState("created"); }
    catch { setCandidateError("候选建立失败；候选理解与用户确认状态均已保留，请重试。"); setCandidateState("idle"); }
  }
  const provenanceLabel = claim.status === "PROPOSED"
    ? "模型生成、尚未确认"
    : claim.status === "CONFIRMED"
      ? "模型生成、用户已确认"
      : "模型生成、用户已拒绝";
  return <section className="claim-card">
    <StatusNotice tone="warning" title={provenanceLabel}>确认或拒绝只记录用户决定，不会改写原始记录。</StatusNotice>
    <p>{claim.statement}</p><p><strong>类型：</strong>{claim.candidate_kind === "OBSERVATION" ? "可观察事实候选" : claim.candidate_kind === "OWNER_INTERPRETATION" ? "主人明确表达的理解" : claim.claim_type}{claim.candidate_kind === "LEGACY_INTERPRETATION" ? ` · 把握程度：${claim.confidence_label === "LOW" ? "低" : claim.confidence_label === "MEDIUM" ? "中" : "高"}` : " · 原文逐字摘取"} · <strong>状态：</strong>{claim.status === "PROPOSED" ? "待确认" : claim.status === "CONFIRMED" ? "已确认" : "已拒绝"}</p>
    <h5>依据</h5>{claim.evidence_references.map((item) => <blockquote key={item.id}><strong>{item.role === "SUPPORTS" ? "支持" : item.role === "LIMITS" ? "限制" : "背景"}</strong><br />{item.excerpt || "无摘录"}</blockquote>)}
    {claim.uncertainties.length > 0 && <><h5>不确定之处</h5>{claim.uncertainties.map((item) => <p key={item.id}>{item.description}</p>)}</>}
    {readOnly && <StatusNotice tone="info">当前只读展示历史模型结果，不接受新的候选决定或长期记忆候选。</StatusNotice>}
    {!readOnly && (claim.status === "PROPOSED" ? <div className="claim-actions"><Button busy={pending === "CONFIRMED"} disabled={pending !== null} onClick={() => void decide("CONFIRMED")}>{pending === "CONFIRMED" ? "正在确认…" : "确认此候选"}</Button><Button variant="danger" busy={pending === "REJECTED"} disabled={pending !== null} onClick={() => void decide("REJECTED")}>{pending === "REJECTED" ? "正在拒绝…" : "拒绝此候选"}</Button></div> : <p className="decision-state">用户已{claim.status === "CONFIRMED" ? "确认" : "拒绝"}；这是用户决定，不会改写原始记录。</p>)}
    {!readOnly && claim.candidate_kind === "LEGACY_INTERPRETATION" && claim.status === "CONFIRMED" && !runStale && candidateState !== "created" && <Button busy={candidateState === "saving"} onClick={() => void materializeCandidate()}>{candidateState === "saving" ? "正在建立候选…" : "建立长期记忆候选"}</Button>}
    {claim.status === "CONFIRMED" && runStale && <StatusNotice tone="warning">来源记录已变化，不能建立新的长期记忆候选。</StatusNotice>}
    {candidateState === "created" && <StatusNotice tone="success" role="status" action={<Button onClick={onOpenMemory}>去我们页面确认</Button>}>候选已建立，尚未纳入长期记忆。</StatusNotice>}
    {candidateError && <StatusNotice tone="danger" role="alert">{candidateError}</StatusNotice>}
    {error && <StatusNotice tone="danger" role="alert">{error}</StatusNotice>}
  </section>;
}
