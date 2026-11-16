import { useCallback, useEffect, useState } from "react";
import { ApiError, createAssistantGuidanceRun, listAssistantGuidanceRuns } from "../api";
import type { AssistantGuidanceOutput, AssistantGuidanceRun, Episode, GuidanceMode } from "../types";
import { Button, StatusNotice } from "./ui";

const modeLabels: Record<GuidanceMode, string> = {
  RECORD_REVIEW: "整理这条记录",
  RECENT_CHANGE_COMPARISON: "比较近期变化",
  VET_TIMELINE: "整理就诊时间线",
};

const sections: Array<[keyof AssistantGuidanceOutput, string]> = [
  ["records_show", "我从记录中看到什么"],
  ["owner_interpretation", "哪些是你的理解"],
  ["possibly_relevant_background", "可能相关的背景"],
  ["cannot_determine", "目前不能确定什么"],
  ["continue_observing", "建议继续观察什么"],
  ["contact_vet_when", "何时应联系兽医"],
];

function requestId() {
  return globalThis.crypto?.randomUUID?.() ?? `guidance-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function AssistantGuidancePanel({ episode, enabled }: { episode: Episode; enabled: boolean }) {
  const [runs, setRuns] = useState<AssistantGuidanceRun[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "running" | "error">("loading");
  const [mode, setMode] = useState<GuidanceMode>("RECORD_REVIEW");
  const [message, setMessage] = useState("");
  const load = useCallback(async () => {
    setState("loading");
    try { const items = await listAssistantGuidanceRuns(episode.id); setRuns(Array.isArray(items) ? items : []); setState("ready"); }
    catch { setState("error"); }
  }, [episode.id]);
  useEffect(() => { void load(); }, [load]);

  async function generate() {
    setState("running"); setMessage("");
    try {
      const run = await createAssistantGuidanceRun(episode.id, requestId(), mode);
      setRuns((current) => [run, ...current.filter((item) => item.id !== run.id)]);
      setState("ready");
    } catch (error) {
      setMessage(error instanceof ApiError && error.code?.startsWith("MODEL_")
        ? "模型结果未通过安全或来源校验，没有展示不可靠内容。"
        : "辅助整理暂时失败，原始记录没有改变。");
      setState("error");
    }
  }

  const blocked = episode.safety_check?.result !== "NORMAL";
  const completed = runs.find((item) => item.status === "COMPLETED" && item.normalized_output);
  return <section className="detail-block" aria-labelledby="assistant-guidance-title">
    <h3 id="assistant-guidance-title">AI 辅助整理</h3>
    <p className="safety-note">模型生成内容不会覆盖你的原话，也不是诊断、治疗或用药建议。背景说明只能使用已审核的本地资料。</p>
    {blocked && <StatusNotice tone="danger" title="先处理当前安全事项">当前记录存在需要关注的安全情况，不会调用外部模型，也不会生成安慰性解释。</StatusNotice>}
    {!blocked && !enabled && <StatusNotice tone="info" title="AI 当前关闭">记录、复评、搜索、媒体、长期记忆和导出仍可正常使用。真实模型通过评估前不会启用。</StatusNotice>}
    {!blocked && enabled && <div className="panel-actions"><label>整理方式<select value={mode} onChange={(event) => setMode(event.target.value as GuidanceMode)}>{Object.entries(modeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><Button busy={state === "running"} onClick={() => void generate()}>{state === "running" ? "正在安全整理…" : "生成辅助整理"}</Button></div>}
    {state === "loading" && <p role="status">正在读取辅助整理历史…</p>}
    {state === "error" && <StatusNotice tone="warning" action={<Button onClick={() => void load()}>重试读取</Button>}>{message || "历史暂时无法读取，原始记录仍然保留。"}</StatusNotice>}
    {completed && completed.normalized_output && <GuidanceResult run={completed} />}
    {state === "ready" && !completed && <p>尚无已完成的辅助整理。</p>}
  </section>;
}

function GuidanceResult({ run }: { run: AssistantGuidanceRun }) {
  const output = run.normalized_output!;
  const sourceIds = new Set(output.sources_used.map((item) => item.knowledge_id));
  const sources = run.knowledge_snapshot.entries.filter((item) => sourceIds.has(item.id));
  return <article className="assistant-guidance-result">
    <StatusNotice tone="warning" title="AI 生成，待你核对">请以原始记录和专业兽医判断为准。{run.is_stale ? "原记录后来已修改，这份整理可能已过期。" : ""}</StatusNotice>
    {sections.map(([key, title]) => {
      const values = output[key] as string[];
      return <section key={key}><h4>{title}</h4>{values.length ? <ul>{values.map((item, index) => <li key={`${key}-${index}`}>{item}</li>)}</ul> : <p>没有可可靠整理的内容。</p>}</section>;
    })}
    <section><h4>使用了哪些资料</h4>{sources.length ? <ul>{sources.map((item) => <li key={item.id}>{item.source.title} · {item.version} · {item.source.locator}</li>)}</ul> : <p>这份结果没有使用背景资料。</p>}</section>
    <details><summary>技术详情</summary><dl><dt>生成时间</dt><dd>{new Date(run.created_at).toLocaleString()}</dd><dt>知识集合</dt><dd>{run.knowledge_snapshot.set_version}</dd><dt>模型版本</dt><dd>{run.model_provider} / {run.model_name} / {run.model_version}</dd><dt>提示契约</dt><dd>{run.prompt_contract_version}</dd></dl></details>
  </article>;
}
