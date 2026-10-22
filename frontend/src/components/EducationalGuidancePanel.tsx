import { useEffect, useState } from "react";
import { getEducationalGuidance } from "../api";
import type { EducationalGuidance, Episode } from "../types";

export function EducationalGuidancePanel({ episode }: { episode: Episode }) {
  const [state, setState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [guidance, setGuidance] = useState<EducationalGuidance | null>(null);
  async function load() {
    setState("loading");
    try { setGuidance(await getEducationalGuidance(episode.id)); setState("ready"); }
    catch { setGuidance(null); setState("error"); }
  }
  useEffect(() => { setGuidance(null); setState("idle"); }, [episode.id]);
  const blocked = episode.safety_check?.result !== "NORMAL";
  return <section className="detail-block" aria-labelledby="education-title">
    <h3 id="education-title">教育性观察参考</h3>
    <p className="safety-note">独立于宠物长期记忆；仅引用当前记录事实和本地知识来源，不诊断、不治疗，也不提供药物或剂量。</p>
    {blocked ? <p role="status">当前 Safety 不是 NORMAL。请先处理安全事项，本功能保持阻断。</p> : <>
      {state === "idle" && <button type="button" onClick={() => void load()}>查看有来源的观察参考</button>}
      {state === "loading" && <p role="status">正在读取本地知识…</p>}
      {state === "error" && <div role="alert"><p>暂时无法读取参考，记录本身没有改变。</p><button type="button" onClick={() => void load()}>重试</button></div>}
      {state === "ready" && guidance && <div>
        <p role="status">知识版本：{guidance.knowledge_version} · {guidance.review_status}</p><p>{guidance.review_note}</p>
        <h4>本次引用的已记录事实</h4>{guidance.fact_summary.length ? <ul>{guidance.fact_summary.map((fact) => <li key={fact}>{fact}</li>)}</ul> : <p>当前记录没有可引用的结构化事实。</p>}
        <h4>观察参考</h4>{guidance.entries.length ? guidance.entries.map((item) => <article key={item.id}><strong>{item.title}</strong><p>{item.summary}</p><small>来源：{item.source.title} · {item.source.version} · {item.source.locator}</small></article>) : <p>本地示例集中没有适用于当前物种的条目。</p>}
        <ul>{guidance.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
      </div>}
    </>}
  </section>;
}
