import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { createRelationshipEvent, listRelationshipEvents, updateRelationshipEvent } from "../api";
import type { Pet, RelationshipEvent, RelationshipKind, RelationshipObservationType } from "../types";
import { Button, StatusNotice, Surface } from "./ui";

const typeLabels: Record<RelationshipObservationType, string> = { OWNER_INTERACTION: "主人与宠物互动", SHARED_REST: "共同休息", INTERACTION: "互动", AVOIDANCE: "回避", CONFLICT: "冲突", RESOURCE_SHARING: "资源共享", OTHER: "其他" };
function localValue(value: string) { const date = new Date(value); return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16); }

export function RelationshipTimeline({ pet, pets }: { pet: Pet; pets: Pet[] }) {
  const [items, setItems] = useState<RelationshipEvent[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [kind, setKind] = useState<RelationshipKind>("OWNER_PET");
  const [otherPetId, setOtherPetId] = useState("");
  const [happenedAt, setHappenedAt] = useState(localValue(new Date().toISOString()));
  const [observationType, setObservationType] = useState<RelationshipObservationType>("OWNER_INTERACTION");
  const [observation, setObservation] = useState("");
  const [interpretation, setInterpretation] = useState("");
  const [sourceEpisodeId, setSourceEpisodeId] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const generation = useRef(0);
  const load = useCallback(async () => { const current = ++generation.current; setState("loading"); setItems([]); try { const values = await listRelationshipEvents(pet.id); if (current === generation.current) { setItems(values); setState("ready"); } } catch { if (current === generation.current) setState("error"); } }, [pet.id]);
  useEffect(() => { void load(); return () => { generation.current += 1; }; }, [load]);
  const otherPets = pets.filter((item) => item.id !== pet.id && !item.archived_at);
  const patternCounts = Object.entries(items.reduce<Record<string, number>>((counts, item) => ({ ...counts, [item.observation_type]: (counts[item.observation_type] ?? 0) + 1 }), {}));
  function reset() { setEditingId(null); setKind("OWNER_PET"); setOtherPetId(""); setHappenedAt(localValue(new Date().toISOString())); setObservationType("OWNER_INTERACTION"); setObservation(""); setInterpretation(""); setSourceEpisodeId(""); }
  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setMessage("");
    if (kind === "PET_PET" && !otherPetId) { setSaving(false); setMessage("Pet↔Pet 事件需要选择另一只宠物。"); return; }
    const payload = { relationship_kind: kind, participant_pet_ids: kind === "OWNER_PET" ? [pet.id] : [pet.id, Number(otherPetId)], happened_at: new Date(happenedAt).toISOString(), observation_type: observationType, observation_text: observation.trim(), owner_interpretation: interpretation.trim() || null, source_episode_id: sourceEpisodeId ? Number(sourceEpisodeId) : null };
    try { if (editingId === null) await createRelationshipEvent(payload); else await updateRelationshipEvent(editingId, payload); reset(); setMessage("关系事件已保存；客观观察与主人理解分别存储。"); await load(); }
    catch { setMessage("关系事件保存失败；你的输入仍保留，请检查参与宠物和来源记录后重试。"); }
    finally { setSaving(false); }
  }
  function edit(item: RelationshipEvent) { const participant = item.participants.find((value) => value.pet_id !== pet.id); setEditingId(item.id); setKind(item.relationship_kind); setOtherPetId(participant ? String(participant.pet_id) : ""); setHappenedAt(localValue(item.happened_at)); setObservationType(item.observation_type); setObservation(item.observation_text); setInterpretation(item.current_owner_interpretation ?? ""); setSourceEpisodeId(item.source_episode_id ? String(item.source_episode_id) : ""); setMessage(""); }
  return <section aria-labelledby="relationship-title"><h3 id="relationship-title">关系事件时间线</h3><p className="section-help">只记录可观察互动；主人理解单独保存。系统不生成嫉妒、爱意指数、依恋障碍或其他心理诊断。</p>
    <form className="editor-form" onSubmit={(event) => void save(event)}><label>关系类型<select value={kind} onChange={(event) => { const next = event.target.value as RelationshipKind; setKind(next); setObservationType(next === "OWNER_PET" ? "OWNER_INTERACTION" : "INTERACTION"); }}><option value="OWNER_PET">主人 ↔ {pet.name}</option><option value="PET_PET">{pet.name} ↔ 另一只宠物</option></select></label>{kind === "PET_PET" && <label>另一位参与者<select value={otherPetId} onChange={(event) => setOtherPetId(event.target.value)}><option value="">请选择</option>{otherPets.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>}<label>发生时间<input required type="datetime-local" value={happenedAt} onChange={(event) => setHappenedAt(event.target.value)} /></label><label>客观观察类型<select value={observationType} onChange={(event) => setObservationType(event.target.value as RelationshipObservationType)}>{Object.entries(typeLabels).filter(([value]) => kind === "OWNER_PET" ? value === "OWNER_INTERACTION" || value === "OTHER" : value !== "OWNER_INTERACTION").map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>客观 Observation<textarea required maxLength={4000} value={observation} onChange={(event) => setObservation(event.target.value)} placeholder="例如：两只猫在同一张沙发两端休息了十分钟。" /></label><label>主人 Interpretation（可选）<textarea maxLength={4000} value={interpretation} onChange={(event) => setInterpretation(event.target.value)} placeholder="写下你的理解；它不会被当作事实。" /></label><label>来源 Episode ID（可选）<input type="number" min="1" value={sourceEpisodeId} onChange={(event) => setSourceEpisodeId(event.target.value)} /></label><div className="button-row"><Button type="submit" busy={saving}>{saving ? "正在保存…" : editingId === null ? "记录关系事件" : "保存修订"}</Button>{editingId !== null && <Button type="button" onClick={reset}>取消编辑</Button>}</div>{message && <StatusNotice tone={message.includes("失败") || message.includes("需要") ? "danger" : "success"} role={message.includes("失败") || message.includes("需要") ? "alert" : "status"}>{message}</StatusNotice>}</form>
    {state === "loading" && <p role="status">正在读取关系事件…</p>}{state === "error" && <StatusNotice tone="warning" role="alert" action={<Button onClick={() => void load()}>重试</Button>}>关系时间线读取失败。</StatusNotice>}{state === "ready" && items.length === 0 && <StatusNotice>尚无关系事件。可以从一次可观察互动开始记录。</StatusNotice>}
    {state === "ready" && items.length > 0 && <Surface tone="subtle" className="memory-card"><h4>已记录互动概览</h4><ul>{patternCounts.map(([type, count]) => <li key={type}>{typeLabels[type as RelationshipObservationType] ?? type}：{count} 条</li>)}</ul><p className="meta-line">范围：{new Date(items.at(-1)!.happened_at).toLocaleDateString()} 至 {new Date(items[0].happened_at).toLocaleDateString()}。这里只汇总记录数量，不计算爱意、依恋或关系质量分数。</p></Surface>}
    {items.map((item) => <Surface key={item.id} className="memory-card"><div className="state-heading"><strong>{typeLabels[item.observation_type]}</strong><span>{new Date(item.happened_at).toLocaleString()}</span></div><p><b>客观 Observation：</b>{item.observation_text}</p><p><b>主人 Interpretation：</b>{item.revisions.at(-1)?.owner_interpretation ?? "未填写"}</p><p className="meta-line">参与宠物 ID：{item.participants.map((value) => value.pet_id).join("、")} · 来源：{item.source_episode_id ? `Episode #${item.source_episode_id}` : "手工关系记录"}</p><Button onClick={() => edit(item)}>编辑关系事件</Button><details><summary>修订历史（{item.revisions.length}）</summary><ol>{item.revisions.slice().reverse().map((revision) => <li key={revision.id}>版本 {revision.revision_number} · 事件时间 {new Date(revision.happened_at).toLocaleString()}<br />参与宠物：{revision.participant_pet_ids.join("、")} · 来源：{revision.source_episode_id ? `Episode #${revision.source_episode_id}` : "手工记录"}<br />Observation：{revision.observation_text}<br />主人理解：{revision.owner_interpretation ?? "未填写"}</li>)}</ol></details><p className="meta-line">系统提示：无。此页面不自动推断关系含义。</p></Surface>)}
  </section>;
}
