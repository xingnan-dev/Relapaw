import { useEffect, useState } from "react";
import { getTimeline } from "../api";
import { useCurrentPet } from "../state/CurrentPetContext";
import type { Episode } from "../types";

export function Timeline() {
  const { pet, status } = useCurrentPet();
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [message, setMessage] = useState("");
  const [loadingMore, setLoadingMore] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    if (!pet) { setEpisodes([]); setMessage(status === "loading" ? "正在读取…" : "添加宠物后，Timeline 会出现在这里。"); return; }
    setMessage("正在读取…");
    getTimeline(pet.id, 1).then((result) => {
      if (!active) return;
      setEpisodes(result.items); setPage(1); setHasMore(result.has_more); setMessage(result.items.length ? "" : "还没有事件记录");
    }).catch(() => { if (active) setMessage("暂时无法读取 Timeline，请稍后重试。"); });
    return () => { active = false; };
  }, [pet, status]);

  async function loadMore() {
    if (!pet || loadingMore) return;
    setLoadingMore(true);
    setMessage("");
    try {
      const next = await getTimeline(pet.id, page + 1);
      setEpisodes((items) => [...items, ...next.items]); setPage(next.page); setHasMore(next.has_more);
    } catch {
      setMessage("无法加载更多记录，请重试。");
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <section aria-labelledby="timeline-title">
      <p className="eyebrow">TIMELINE</p><h2 id="timeline-title">长期记录</h2>
      <div className="timeline-tools"><input aria-label="搜索 Timeline" placeholder="搜索记录（占位）" disabled /><button type="button" disabled>筛选</button></div>
      <div className="filter-chips" aria-label="时间范围"><button className="active">全部</button><button>30 天</button><button>7 天</button><button>今天</button></div>
      {message && <p role="status">{message}</p>}
      <ol className="timeline">
        {episodes.map((episode) => <li key={episode.id}>
          <button className="timeline-summary" aria-expanded={expanded === episode.id} onClick={() => setExpanded(expanded === episode.id ? null : episode.id)}><span><time dateTime={episode.happened_at}>{new Date(episode.happened_at).toLocaleString()}</time><strong>{episode.episode_type}</strong></span><span>{expanded === episode.id ? "收起" : "展开"}</span></button>
          <p>{episode.raw_owner_input}</p>
          {expanded === episode.id && <div className="timeline-detail">
            <div className="lens-card"><strong>发生了什么</strong>{episode.observations.length ? episode.observations.map((item) => <p key={item.id}>{item.description}</p>) : <p>尚无客观观察</p>}</div>
            <div className="lens-card interpretation"><strong>你的理解</strong>{episode.owner_interpretations.length ? episode.owner_interpretations.map((item) => <p key={item.id}>{item.interpretation}</p>) : <p>尚无主人解释</p>}</div>
            <small>未来复评将追加显示，不会覆盖原记录。</small>
          </div>}
        </li>)}
      </ol>
      {hasMore && <button type="button" disabled={loadingMore} onClick={() => void loadMore()}>{loadingMore ? "正在加载…" : "加载更多"}</button>}
    </section>
  );
}
