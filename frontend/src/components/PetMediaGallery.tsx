import { useCallback, useEffect, useState } from "react";
import { listPetMedia } from "../api";
import type { MediaAttachment } from "../types";
import { Button, StatusNotice } from "./ui";

function sourceLabel(item: MediaAttachment) { return item.episode_id ? `普通记录 #${item.episode_id}` : item.life_event_id ? `生活事件 #${item.life_event_id}` : `关系事件 #${item.relationship_event_id}`; }
function qualityHints(item: MediaAttachment) { const hints: string[] = []; if (!item.captured_at) hints.push("尚未填写拍摄时间"); if (!item.owner_caption) hints.push("尚未填写主人原始说明"); if (item.media_type.startsWith("image/") && item.byte_size < 10 * 1024) hints.push("文件较小，放大比较时可能缺少细节"); return hints; }

export function PetMediaGallery({ petId }: { petId: number }) {
  const [items, setItems] = useState<MediaAttachment[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const load = useCallback(async () => { setState("loading"); try { const values = await listPetMedia(petId); setItems(values.slice().sort((a, b) => new Date(b.captured_at || b.created_at).getTime() - new Date(a.captured_at || a.created_at).getTime())); setState("ready"); } catch { setState("error"); } }, [petId]);
  useEffect(() => { void load(); }, [load]);
  function toggle(id: number) { setSelected((current) => current.includes(id) ? current.filter((value) => value !== id) : current.length < 2 ? [...current, id] : [current[1], id]); }
  const compared = selected.map((id) => items.find((item) => item.id === id)).filter((item): item is MediaAttachment => Boolean(item));
  return <section aria-labelledby="pet-media-gallery-title"><h3 id="pet-media-gallery-title">跨时间媒体</h3><p className="section-help">按你填写的拍摄时间排列；未填写时使用上传时间。最多选择两项并排查看，系统不据此诊断或自动推断变化原因。</p>
    {state === "loading" && <p role="status">正在读取媒体时间线…</p>}{state === "error" && <StatusNotice tone="warning" role="alert" action={<Button onClick={() => void load()}>重试</Button>}>媒体时间线读取失败。</StatusNotice>}{state === "ready" && items.length === 0 && <StatusNotice>尚无媒体。请先在具体记录、生活事件或关系事件中上传。</StatusNotice>}
    {items.length > 0 && <ul className="media-timeline">{items.map((item) => <li key={item.id}><label><input type="checkbox" checked={selected.includes(item.id)} onChange={() => toggle(item.id)} />选择比较</label><strong>{item.original_filename}</strong><span>{new Date(item.captured_at || item.created_at).toLocaleString()} · {sourceLabel(item)}</span>{qualityHints(item).map((hint) => <small key={hint}>{hint}</small>)}</li>)}</ul>}
    {compared.length > 0 && <div className="media-compare" aria-label="媒体并排比较">{compared.map((item) => <article key={item.id}><h4>{item.original_filename}</h4>{item.media_type.startsWith("image/") ? <img className="media-preview" loading="lazy" decoding="async" src={`/api/v1/media/${item.id}/content`} alt={item.owner_caption || item.original_filename} /> : <video className="media-preview" src={`/api/v1/media/${item.id}/content`} controls preload="metadata" />}<p>{new Date(item.captured_at || item.created_at).toLocaleString()} · {item.owner_caption || "未填写主人说明"}</p></article>)}</div>}
  </section>;
}
