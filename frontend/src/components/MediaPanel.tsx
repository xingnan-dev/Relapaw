import { useCallback, useEffect, useRef, useState } from "react";
import { decideMediaCandidate, deleteMedia, listSourceMedia, updateMediaMetadata, uploadSourceMedia, type MediaSource } from "../api";
import type { MediaAttachment } from "../types";

function localValue(value: string | null) { if (!value) return ""; const date = new Date(value); return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16); }
function videoDuration(file: File): Promise<number | undefined> {
  if (!file.type.startsWith("video/")) return Promise.resolve(undefined);
  return new Promise((resolve, reject) => { const url = URL.createObjectURL(file); const video = document.createElement("video"); video.preload = "metadata"; video.onloadedmetadata = () => { const duration = video.duration; URL.revokeObjectURL(url); Number.isFinite(duration) ? resolve(duration) : reject(new Error("duration")); }; video.onerror = () => { URL.revokeObjectURL(url); reject(new Error("video")); }; video.src = url; });
}

export function MediaPanel({ episodeId, source, title = "照片和视频证据" }: { episodeId?: number; source?: MediaSource; title?: string }) {
  const activeSource: MediaSource = source ?? { type: "episode", id: episodeId! };
  const headingId = `media-title-${activeSource.type}-${activeSource.id}`;
  const [items, setItems] = useState<MediaAttachment[]>([]);
  const generation = useRef(0);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState("");
  const load = useCallback(async () => { const requestGeneration = ++generation.current; setItems([]); setState("loading"); try { const loaded = await listSourceMedia(activeSource); if (!Array.isArray(loaded)) throw new Error("Invalid media response"); if (requestGeneration === generation.current) { setItems(loaded); setState("ready"); } } catch { if (requestGeneration === generation.current) setState("error"); } }, [activeSource.type, activeSource.id, activeSource.petId]);
  useEffect(() => { void load(); return () => { generation.current += 1; }; }, [load]);
  async function select(file?: File) {
    if (!file) return; setBusy(true); setMessage("");
    try { const duration = await videoDuration(file); const uploaded = await uploadSourceMedia(activeSource, file, duration); setItems((current) => [uploaded, ...current]); setMessage("媒体已保存并绑定到这条具体记录。请补充原始说明；它不会自动成为长期结论。"); }
    catch { setMessage("上传失败；请确认格式、25 MB 单文件限制、视频不超过 5 分钟及账户容量后重试。"); } finally { setBusy(false); }
  }
  async function saveMetadata(item: MediaAttachment, form: HTMLFormElement) { const data = new FormData(form); setBusy(true); setMessage(""); try { const updated = await updateMediaMetadata(item.id, { captured_at: data.get("captured_at") ? new Date(String(data.get("captured_at"))).toISOString() : null, owner_caption: String(data.get("owner_caption") || "").trim() || null, change_summary: String(data.get("change_summary") || "").trim() || null }); setItems((all) => all.map((entry) => entry.id === item.id ? updated : entry)); setMessage("拍摄时间和主人原始说明已保存，旧版本仍可查看。"); } catch { setMessage("媒体说明保存失败，原内容仍保留。"); } finally { setBusy(false); } }
  async function decide(item: MediaAttachment, action: "CONFIRM" | "REJECT" | "WITHDRAW") { setBusy(true); try { const updated = await decideMediaCandidate(item.id, action); setItems((all) => all.map((entry) => entry.id === item.id ? updated : entry)); setMessage("候选观察状态已更新；主人原始说明没有被覆盖。"); } catch { setMessage("候选状态更新失败，请重试。"); } finally { setBusy(false); } }
  async function remove(item: MediaAttachment) { if (!confirm(`删除附件 ${item.original_filename}？本地文件将不可恢复。`)) return; setBusy(true); try { await deleteMedia(item.id); setItems((all) => all.filter((entry) => entry.id !== item.id)); setMessage("附件及本地文件已删除。"); } catch { setMessage("删除失败，附件仍保留。"); } finally { setBusy(false); } }
  return <section className="detail-block media-panel" aria-labelledby={headingId}><h4 id={headingId}>{title}</h4><p>图片和视频先绑定这条具体记录。支持 JPG、PNG、WebP、MP4、WebM；单文件 25 MB、视频最长 5 分钟、账户总容量 1 GB。媒体不能用于疾病诊断。</p>
    <label>添加照片或视频<input type="file" disabled={busy} accept="image/jpeg,image/png,image/webp,video/mp4,video/webm" onChange={(event) => { void select(event.target.files?.[0]); event.currentTarget.value = ""; }} /></label>
    {state === "loading" && <p role="status">正在读取媒体…</p>}{state === "error" && <div role="status"><p>无法读取媒体。</p><button onClick={() => void load()}>重试</button></div>}
    {state === "ready" && items.length === 0 && <p role="status">这条记录还没有照片或视频。</p>}
    {items.map((item) => <article key={item.id} className="media-card"><strong>{item.original_filename}</strong><p>{item.media_type} · {(item.byte_size / 1024).toFixed(1)} KB{item.duration_seconds ? ` · ${item.duration_seconds} 秒` : ""} · {item.status}</p>
      {item.status === "AVAILABLE" && item.media_type.startsWith("image/") && <img className="media-preview" loading="lazy" decoding="async" src={`/api/v1/media/${item.id}/content`} alt={item.owner_caption || `${item.original_filename} 预览`} />}
      {item.status === "AVAILABLE" && item.media_type.startsWith("video/") && <video className="media-preview" src={`/api/v1/media/${item.id}/content`} controls preload="metadata">你的浏览器不支持视频预览。</video>}
      {item.status === "AVAILABLE" && <a href={`/api/v1/media/${item.id}/content`} target="_blank" rel="noreferrer">打开或下载原文件</a>}
      <form onSubmit={(event) => { event.preventDefault(); void saveMetadata(item, event.currentTarget); }}><label>拍摄时间（如已知）<input name="captured_at" type="datetime-local" defaultValue={localValue(item.captured_at)} /></label><label>我的原始说明<textarea name="owner_caption" defaultValue={item.owner_caption ?? ""} maxLength={5000} placeholder="只写你看到、听到或拍摄时知道的事实。" /></label><label>修改说明（可选）<input name="change_summary" maxLength={500} /></label><button type="submit" disabled={busy}>保存媒体说明</button></form>
      {item.ai_candidate_observation && <div className="candidate-observation"><p><b>AI 候选观察（非诊断）：</b>{item.ai_candidate_observation}</p><p>状态：{item.ai_candidate_status}</p>{item.ai_candidate_status === "PENDING" && <div className="button-row"><button disabled={busy} onClick={() => void decide(item, "CONFIRM")}>确认候选观察</button><button disabled={busy} onClick={() => void decide(item, "REJECT")}>拒绝候选观察</button></div>}{item.ai_candidate_status === "CONFIRMED" && <button disabled={busy} onClick={() => void decide(item, "WITHDRAW")}>撤回候选观察</button>}</div>}
      <details><summary>修改历史（{item.revisions.length}）</summary><ol>{item.revisions.slice().reverse().map((revision) => <li key={revision.id}>版本 {revision.revision_number} · {revision.change_summary || "更新"} · {new Date(revision.created_at).toLocaleString()}<br />主人说明：{revision.owner_caption || "未填写"}<br />AI 候选：{revision.ai_candidate_observation || "无"}（{revision.ai_candidate_status}）</li>)}</ol></details>
      <button type="button" disabled={busy} onClick={() => void remove(item)}>删除媒体</button></article>)}
    {message && <p role={message.includes("失败") ? "alert" : "status"}>{message}</p>}
  </section>;
}
