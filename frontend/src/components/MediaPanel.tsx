import { useCallback, useEffect, useRef, useState } from "react";
import { deleteMedia, listMedia, updateMediaFacts, uploadMedia } from "../api";
import type { MediaAttachment } from "../types";

export function MediaPanel({ episodeId }: { episodeId: number }) {
  const [items, setItems] = useState<MediaAttachment[]>([]);
  const generation = useRef(0);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState("");
  const load = useCallback(async () => { const requestGeneration = ++generation.current; setItems([]); setState("loading"); try { const loaded = await listMedia(episodeId); if (!Array.isArray(loaded)) throw new Error("Invalid media response"); if (requestGeneration === generation.current) { setItems(loaded); setState("ready"); } } catch { if (requestGeneration === generation.current) setState("error"); } }, [episodeId]);
  useEffect(() => { void load(); return () => { generation.current += 1; }; }, [load]);
  async function select(file?: File) {
    if (!file) return; setBusy(true); setMessage("");
    try { const uploaded = await uploadMedia(episodeId, file); setItems((current) => [uploaded, ...current]); setMessage("附件已保存到本地并关联此记录。"); }
    catch { setMessage("上传失败；请选择支持且不超过 25 MB 的文件后重试。"); } finally { setBusy(false); }
  }
  async function saveFacts(item: MediaAttachment, value: string) { setBusy(true); setMessage(""); try { const updated = await updateMediaFacts(item.id, value.trim() || null); setItems((all) => all.map((entry) => entry.id === item.id ? updated : entry)); setMessage("媒体中的可观察事实已保存。"); } catch { setMessage("保存事实失败，原内容仍保留。请重试。"); } finally { setBusy(false); } }
  async function remove(item: MediaAttachment) { if (!confirm(`删除附件 ${item.original_filename}？本地文件将不可恢复。`)) return; setBusy(true); try { await deleteMedia(item.id); setItems((all) => all.filter((entry) => entry.id !== item.id)); setMessage("附件及本地文件已删除。"); } catch { setMessage("删除失败，附件仍保留。请重试。"); } finally { setBusy(false); } }
  return <section className="detail-block" aria-labelledby="media-title"><h3 id="media-title">本地媒体附件</h3><p>支持 JPG、PNG、WebP、MP4、WebM、PDF、TXT，单文件上限 25 MB。自动识别未启用；事实只由你填写。</p>
    <label>添加附件<input type="file" disabled={busy} accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,application/pdf,text/plain" onChange={(event) => { void select(event.target.files?.[0]); event.currentTarget.value = ""; }} /></label>
    {state === "loading" && <p role="status">正在读取附件…</p>}{state === "error" && <div role="status"><p>无法读取附件。</p><button onClick={() => void load()}>重试</button></div>}
    {state === "ready" && items.length === 0 && <p role="status">这条记录还没有附件。</p>}
    {items.map((item) => <article key={item.id}><strong>{item.original_filename}</strong><p>{item.media_type} · {(item.byte_size / 1024).toFixed(1)} KB · {item.status}</p>{item.status === "AVAILABLE" && <a href={`/api/v1/media/${item.id}/content`} target="_blank" rel="noreferrer">打开附件</a>}<label>媒体中可观察到的事实<textarea defaultValue={item.observable_facts ?? ""} maxLength={5000} onBlur={(event) => { if (event.target.value !== (item.observable_facts ?? "")) void saveFacts(item, event.target.value); }} /></label><button type="button" disabled={busy} onClick={() => void remove(item)}>删除附件</button></article>)}
    {message && <p role={message.includes("失败") ? "alert" : "status"}>{message}</p>}
  </section>;
}
