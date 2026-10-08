import { useCurrentPet } from "../state/CurrentPetContext";

export function Us({ onAddPet }: { onAddPet: () => void }) {
  const { pet } = useCurrentPet();
  return (
    <section aria-labelledby="us-title">
      <p className="eyebrow">US</p><h2 id="us-title">我们</h2>
      {pet ? <div className="pet-identity"><div className="pet-avatar">{pet.name.slice(0, 1).toUpperCase()}</div><div><h3>{pet.name}</h3><p>{[pet.species, pet.breed].filter(Boolean).join(" · ")}</p></div></div> : <div className="card"><h3>还没有宠物档案</h3><button onClick={onAddPet}>添加宠物</button></div>}
      <div className="model-grid">
        <div className="card"><h3>Pet Profile</h3><p>身份与基本资料</p></div>
        <div className="card"><h3>Daily Baseline</h3><p>平时的活动、饮食与休息</p></div>
        <div className="card"><h3>Owner Profile</h3><p>互动与信息偏好，不做心理诊断</p></div>
        <div className="card"><h3>Relationship</h3><p>长期互动关系记录</p></div>
        <div className="card"><h3>Life Events</h3><p>搬家、访客与环境变化</p></div>
        <div className="card"><h3>数据与隐私</h3><p>导出、删除与记忆管理占位</p></div>
      </div>
    </section>
  );
}
