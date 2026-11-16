import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { createInteractionPattern, decideInteractionPattern, deleteInteractionPattern, listInteractionPatterns, updateInteractionPattern } from "../api";
import type { InteractionPatternCandidate, InteractionPatternDecisionAction, Pet, RelationshipEvent, RelationshipKind } from "../types";
import { Button, StatusNotice, Surface } from "./ui";

const statusLabels = { ELIGIBLE: "等待你判断", CONFIRMED: "你已确认", REJECTED: "你已拒绝", WITHDRAWN: "已撤回" } as const;
const memoryLabels = { NOT_INCLUDED: "未纳入长期变化", INCLUDED: "已纳入长期变化", WITHDRAWN: "已从长期变化撤回" } as const;
type EvidenceRole = "IGNORE" | "SUPPORTS" | "CONTRADICTS";

export function InteractionPatterns({ pet, pets, events }: { pet: Pet; pets: Pet[]; events: RelationshipEvent[] }) {
  const [items, setItems] = useState<InteractionPatternCandidate[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [kind, setKind] = useState<RelationshipKind>("OWNER_PET");
  const [otherPetId, setOtherPetId] = useState("");
  const [selfReport, setSelfReport] = useState("");
  const [title, setTitle] = useState("");
  const [pattern, setPattern] = useState("");
  const [counterexample, setCounterexample] = useState("");
  const [limit, setLimit] = useState("这只描述当前记录覆盖的时段，不能代表固定性格或关系类型。");
  const [roles, setRoles] = useState<Record<number, EvidenceRole>>({});
  const [editingId, setEditingId] = useState<number | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const load = useCallback(async () => { setLoadState("loading"); try { setItems(await listInteractionPatterns(pet.id)); setLoadState("ready"); } catch { setLoadState("error"); } }, [pet.id]);
  useEffect(() => { void load(); }, [load]);
  const participantIds = useMemo(() => kind === "OWNER_PET" ? [pet.id] : [pet.id, Number(otherPetId)].filter(Boolean), [kind, otherPetId, pet.id]);
  const matchingEvents = events.filter((item) => item.relationship_kind === kind && item.participants.map((part) => part.pet_id).sort().join(",") === [...participantIds].sort().join(","));
  const chosenCount = Object.values(roles).filter((role) => role !== "IGNORE").length;
  const supportCount = Object.values(roles).filter((role) => role === "SUPPORTS").length;
  const otherPets = pets.filter((item) => item.id !== pet.id && !item.archived_at);
  function resetForm() { setSelfReport(""); setTitle(""); setPattern(""); setCounterexample(""); setLimit("这只描述当前记录覆盖的时段，不能代表固定性格或关系类型。"); setRoles({}); setEditingId(null); }
  async function create(event: FormEvent) {
    event.preventDefault(); setMessage("");
    if (kind === "PET_PET" && !otherPetId) { setMessage("请先选择另一只参与宠物。"); return; }
    if (supportCount < 2 || chosenCount < 3) { setMessage("至少选择 3 条记录，其中至少 2 条支持候选；反例也会被保留。"); return; }
    setBusy(true);
    try {
      await createInteractionPattern({ relationship_kind: kind, participant_pet_ids: participantIds, initial_self_report: selfReport.trim() || null, title: title.trim(), observable_pattern: pattern.trim(), support_event_ids: Object.keys(roles).filter((id) => roles[Number(id)] === "SUPPORTS").map(Number), contradiction_event_ids: Object.keys(roles).filter((id) => roles[Number(id)] === "CONTRADICTS").map(Number), counterevidence_summary: counterexample.trim(), confidence_limit: limit.trim() });
      resetForm(); setMessage("候选已建立，尚未确认，也没有自动进入长期变化。"); await load();
    } catch { setMessage("候选未建立。请确认记录属于同一关系、至少跨越 7 天后重试。"); }
    finally { setBusy(false); }
  }
  async function decide(id: number, action: InteractionPatternDecisionAction) { setBusy(true); setMessage(""); try { await decideInteractionPattern(id, action); setMessage("你的决定已保存，历史记录不会被覆盖。"); await load(); } catch { setMessage("操作未完成；候选可能已撤回，或尚未确认就尝试纳入长期变化。"); } finally { setBusy(false); } }
  async function saveEdit(event: FormEvent<HTMLFormElement>, item: InteractionPatternCandidate) { event.preventDefault(); const data = new FormData(event.currentTarget); setBusy(true); try { await updateInteractionPattern(item.id, { title: String(data.get("title")), observable_pattern: String(data.get("pattern")), counterevidence_summary: String(data.get("counterexample")), confidence_limit: String(data.get("limit")), change_summary: String(data.get("summary") || "").trim() || null }); setEditingId(null); setMessage("候选修订已保存，旧版本仍可查看。"); await load(); } catch { setMessage("修订保存失败，请重试。"); } finally { setBusy(false); } }
  async function remove(id: number) { setBusy(true); try { await deleteInteractionPattern(id); setDeleteId(null); setMessage("候选及其派生记录已删除；原始关系事件仍保留。"); await load(); } catch { setMessage("删除失败，请重试。"); } finally { setBusy(false); } }
  return <section className="interaction-patterns" aria-labelledby="interaction-pattern-title"><header><p className="eyebrow">从记录到候选</p><h3 id="interaction-pattern-title">互动模式候选</h3><p>先保留你的初始想法，再用多次可观察记录支持或反驳。候选不是诊断、关系评分或固定画像。</p></header>
    <ol className="pattern-steps"><li><strong>初始自述</strong><span>只是你的起点，不当作事实。</span></li><li><strong>多次记录</strong><span>至少 3 条、跨 7 天，并保留反例。</span></li><li><strong>候选理解</strong><span>由你确认后，才能另行纳入长期变化。</span></li></ol>
    <details><summary>根据已有记录建立候选</summary><form className="editor-form" onSubmit={(event) => void create(event)}>
      <label>关系范围<select aria-label="候选关系范围" value={kind} onChange={(event) => { setKind(event.target.value as RelationshipKind); setRoles({}); }}><option value="OWNER_PET">我与 {pet.name}</option><option value="PET_PET">{pet.name} 与另一只宠物</option></select></label>
      {kind === "PET_PET" && <label>另一只宠物<select value={otherPetId} onChange={(event) => { setOtherPetId(event.target.value); setRoles({}); }}><option value="">请选择</option>{otherPets.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>}
      <label>我最初怎么想（可选）<textarea value={selfReport} maxLength={4000} onChange={(event) => setSelfReport(event.target.value)} /></label>
      <fieldset><legend>把每条记录标为支持、反例或暂不使用</legend>{matchingEvents.length === 0 ? <p>这个关系范围还没有可用记录。</p> : matchingEvents.map((item) => <label key={item.id} className="pattern-evidence-row"><span>{new Date(item.happened_at).toLocaleDateString()} · {item.observation_text}</span><select aria-label={`记录 ${item.id} 的作用`} value={roles[item.id] ?? "IGNORE"} onChange={(event) => setRoles((current) => ({ ...current, [item.id]: event.target.value as EvidenceRole }))}><option value="IGNORE">暂不使用</option><option value="SUPPORTS">支持候选</option><option value="CONTRADICTS">反例或矛盾</option></select></label>)}</fieldset>
      <p className="meta-line">已选 {chosenCount} 条，其中支持 {supportCount} 条。系统还会检查这些记录是否跨越至少 7 天。</p>
      <label>候选标题<input required maxLength={200} value={title} onChange={(event) => setTitle(event.target.value)} /></label><label>具体可观察的重复现象<textarea required maxLength={4000} value={pattern} onChange={(event) => setPattern(event.target.value)} /></label><label>反例或仍不一致的地方<textarea required maxLength={4000} value={counterexample} onChange={(event) => setCounterexample(event.target.value)} /></label><label>这项候选不能说明什么<textarea required maxLength={2000} value={limit} onChange={(event) => setLimit(event.target.value)} /></label><Button type="submit" busy={busy}>建立候选</Button></form></details>
    {loadState === "loading" && <p role="status">正在读取互动模式候选…</p>}{loadState === "error" && <StatusNotice tone="warning" role="alert" action={<Button onClick={() => void load()}>重试</Button>}>候选读取失败。</StatusNotice>}{loadState === "ready" && items.length === 0 && <StatusNotice>尚无候选。继续记录真实互动即可，不必急着概括关系。</StatusNotice>}
    {items.map((item) => <Surface key={item.id} className="memory-card pattern-card"><div className="state-heading"><strong>{item.title}</strong><span>{statusLabels[item.status]} · {memoryLabels[item.memory_status]}</span></div><p><b>初始自述：</b>{item.initial_self_report || "未填写"}</p><p><b>多次记录呈现：</b>{item.observable_pattern}</p><p><b>反例或矛盾：</b>{item.counterevidence_summary}</p><p><b>不能据此确定：</b>{item.confidence_limit}</p><p className="meta-line">证据 {item.evidence_count} 条 · 覆盖 {new Date(item.coverage_start).toLocaleDateString()} 至 {new Date(item.coverage_end).toLocaleDateString()} · 生成规则 {item.generator_version}</p>
      <details><summary>查看证据、版本与决定</summary><h5>记录证据</h5><ul>{item.evidences.map((evidence) => <li key={evidence.id}>{evidence.role === "SUPPORTS" ? "支持" : "反例"} · {new Date(evidence.happened_at).toLocaleDateString()} · {evidence.observation_snapshot}</li>)}</ul><h5>修订历史</h5><ol>{item.revisions.map((revision) => <li key={revision.id}>版本 {revision.revision_number} · {revision.change_summary || "建立候选"}</li>)}</ol><h5>你的决定</h5>{item.decisions.length ? <ol>{item.decisions.map((decision) => <li key={decision.id}>{decision.action} · {new Date(decision.created_at).toLocaleString()}</li>)}</ol> : <p>尚无决定。</p>}</details>
      {editingId === item.id ? <form className="editor-form" onSubmit={(event) => void saveEdit(event, item)}><label>标题<input name="title" required defaultValue={item.title} /></label><label>可观察现象<textarea name="pattern" required defaultValue={item.observable_pattern} /></label><label>反例<textarea name="counterexample" required defaultValue={item.counterevidence_summary} /></label><label>置信限制<textarea name="limit" required defaultValue={item.confidence_limit} /></label><label>这次修改了什么<input name="summary" maxLength={500} /></label><div className="button-row"><Button type="submit" busy={busy}>保存修订</Button><Button type="button" onClick={() => setEditingId(null)}>取消</Button></div></form> : <div className="button-row">{item.status === "ELIGIBLE" && <><Button disabled={busy} onClick={() => void decide(item.id, "CONFIRM")}>确认候选</Button><Button disabled={busy} onClick={() => void decide(item.id, "REJECT")}>拒绝候选</Button></>} {item.status !== "WITHDRAWN" && <><Button disabled={busy} onClick={() => setEditingId(item.id)}>修订</Button><Button disabled={busy} onClick={() => void decide(item.id, "WITHDRAW")}>撤回候选</Button></>} {item.status === "CONFIRMED" && item.memory_status !== "INCLUDED" && <Button disabled={busy} onClick={() => void decide(item.id, "INCLUDE_IN_MEMORY")}>纳入长期变化</Button>} {item.memory_status === "INCLUDED" && <Button disabled={busy} onClick={() => void decide(item.id, "WITHDRAW_FROM_MEMORY")}>从长期变化撤回</Button>}<Button disabled={busy} onClick={() => setDeleteId(item.id)}>删除候选</Button></div>}
      {deleteId === item.id && <div role="alert"><p>删除会移除这项候选、版本和决定，但保留作为来源的原始关系事件。</p><Button disabled={busy} onClick={() => void remove(item.id)}>确认删除</Button><Button disabled={busy} onClick={() => setDeleteId(null)}>取消</Button></div>}
    </Surface>)}{message && loadState === "ready" && <p role={message.includes("失败") || message.includes("未完成") ? "alert" : "status"}>{message}</p>}</section>;
}
