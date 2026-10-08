import { useCurrentPet } from "../state/CurrentPetContext";

export function Today({ onAddPet, onUnderstand }: { onAddPet: () => void; onUnderstand: () => void }) {
  const { pet, status, retry } = useCurrentPet();
  if (status === "error") return <section><h2>暂时无法读取宠物资料</h2><button onClick={retry}>重试</button></section>;
  if (!pet) return <section className="empty-state" aria-labelledby="today-title"><p className="eyebrow">TODAY</p><h2 id="today-title">从认识它平时的样子开始</h2><p>建立宠物档案后，Relapaw 才能帮助你记录变化，而不是展示伪造的状态。</p><button className="primary" type="button" onClick={onAddPet}>添加我的宠物</button></section>;
  const days = Array.from({ length: 7 }, (_, index) => { const date = new Date(); date.setDate(date.getDate() - (6 - index)); return date; });
  return (
    <section aria-labelledby="today-title">
      <p className="eyebrow">TODAY</p>
      <div className="pet-heading"><div className="pet-avatar" aria-hidden="true">{pet.name.slice(0, 1).toUpperCase()}</div><div><h2 id="today-title">{pet.name}</h2><p>今天需要留意什么</p></div></div>
      <div className="date-rail" aria-label="最近七天">{days.map((day, index) => <button type="button" key={day.toISOString()} className={index === 6 ? "active" : ""}><span>{day.toLocaleDateString("zh-CN", { weekday: "short" })}</span><strong>{day.getDate()}</strong></button>)}</div>
      <div className="card focus-card"><p className="eyebrow">今日重点</p><h3>尚无今日观察</h3><p>记录事实，之后再讨论它可能意味着什么。</p><button type="button" onClick={onUnderstand}>快速记录</button></div>
      <div className="card"><h3>Observation Plan</h3><p>暂无进行中的观察计划。</p><small>未来会在这里显示观察目标、时间范围与今日项目。</small></div>
      <div className="card"><h3>最近变化</h3><p>还没有足够记录用于比较日常基线。</p></div>
    </section>
  );
}
