type Variant = {
  id: string;
  index: string;
  name: string;
  summary: string;
  recommendation: string;
  traits: string[];
  swatches: string[];
};

const variants: Variant[] = [
  {
    id: "storybook",
    index: "01",
    name: "柔和绘本卡片",
    summary: "最贴近当前品牌：大留白、温暖奶油底、手绘宠物和低对比粉彩模块。",
    recommendation: "推荐作为主方向",
    traits: ["圆润黑体标题", "16–24px 大间距", "1px 暖灰描边", "低阴影纸片卡"],
    swatches: ["#FFF8EE", "#E9D8F2", "#CDE8DE", "#F0B8A7", "#403746"],
  },
  {
    id: "editorial",
    index: "02",
    name: "编辑拼贴",
    summary: "借鉴高饱和活动类界面，用不规则色块、粗标题和黑色胶囊形成强记忆点。",
    recommendation: "适合 Today 与演示页",
    traits: ["超大标题 36–48px", "2–3 色强对比", "黑色实心按钮", "错位叠卡"],
    swatches: ["#FFF4D8", "#F5D65B", "#EE9FC2", "#A8BE78", "#171719"],
  },
  {
    id: "mist",
    index: "03",
    name: "轻玻璃梦雾",
    summary: "参考柔和健康类产品的雾面渐变与半透明卡片，但压低光效，避免 AI 科技感。",
    recommendation: "适合 Understanding 与 Baseline",
    traits: ["24–32px 中粗标题", "乳白玻璃卡", "低饱和渐变", "无可见硬描边"],
    swatches: ["#F8F6FF", "#DED5F4", "#CFE9E5", "#F2D6DE", "#51465E"],
  },
  {
    id: "ink",
    index: "04",
    name: "线稿粉彩",
    summary: "以黑白线稿和大面积白底建立高级感，粉彩只用于功能分区和状态，不铺满页面。",
    recommendation: "适合长期使用与无障碍",
    traits: ["粗黑标题 32–44px", "黑色 1.5px 描边", "粉彩状态块", "极轻或零阴影"],
    swatches: ["#FFFEFB", "#F3CADB", "#D8E6C9", "#D9D6F3", "#161619"],
  },
];

function PawSketch() {
  return <svg viewBox="0 0 96 96" aria-hidden="true"><path d="M48 71c-12 0-26-5-26-16 0-9 9-20 18-20 5 0 6 4 8 4s3-4 8-4c9 0 18 11 18 20 0 11-14 16-26 16Z"/><ellipse cx="24" cy="32" rx="8" ry="11"/><ellipse cx="43" cy="22" rx="8" ry="11"/><ellipse cx="72" cy="32" rx="8" ry="11"/><ellipse cx="57" cy="22" rx="8" ry="11"/></svg>;
}

function PhonePreview({ variant }: { variant: Variant }) {
  return <div className={`variant-phone variant-phone--${variant.id}`}>
    <div className="variant-phone__status"><span>9:41</span><span>● ◒</span></div>
    <header className="variant-phone__header">
      <div><small>TODAY · 今天</small><h2>早上好，cancan12</h2><p>今天，想留意什么？</p></div>
      <span className="variant-avatar">C</span>
    </header>
    <div className="variant-days" aria-label="日期示意">
      {["一 12", "二 13", "三 14", "四 15"].map((day, index) => <span className={index === 3 ? "is-active" : ""} key={day}>{day}</span>)}
    </div>
    <section className="variant-focus">
      <div className="variant-focus__art"><PawSketch /></div>
      <small>从真实发生的事开始</small>
      <h3>记下一刻</h3>
      <p>先写下真实发生的事，再记录你的理解。</p>
      <button type="button">开始记录 <span>→</span></button>
    </section>
    <div className="variant-grid">
      <section><small>REVISIT</small><h3>回来看看</h3><p>今天没有需要回看的记录。</p></section>
      <section><small>OBSERVATION</small><h3>一段观察</h3><p>还没有正在进行的观察。</p></section>
    </div>
    <nav className="variant-nav"><span className="is-active">⌂<b>今天</b></span><span>♡<b>理解</b></span><span>⌁<b>足迹</b></span><span>♙<b>我们</b></span></nav>
  </div>;
}

export function VisualVariants() {
  return <main className="variants-lab">
    <header className="variants-hero">
      <div><p>RELAPAW · VISUAL STUDY</p><h1>四种可落地的<br/>视觉方向</h1></div>
      <p>从参考图提炼规则，再用同一组真实产品内容比较。这里仅改变视觉语言，不改变状态机、Safety、Evidence 或人工决定语义。</p>
    </header>
    <section className="reference-rules" aria-labelledby="rules-title">
      <div><p>REFERENCE SYNTHESIS</p><h2 id="rules-title">参考图共同语言</h2></div>
      <dl>
        <div><dt>字体</dt><dd>圆润几何黑体为主；标题 700–850，正文 400–550；少量衬线或斜体只做情绪点缀。</dd></div>
        <div><dt>字号</dt><dd>移动端标题 32–48px，页面标题与正文至少形成约 2.2–3 倍反差；辅助信息 11–13px。</dd></div>
        <div><dt>排版</dt><dd>高留白、大标题、模块化卡片；核心内容一次只强调一件事，避免平均分配视觉权重。</dd></div>
        <div><dt>组件</dt><dd>胶囊按钮、圆角卡、彩色功能块、底部浮岛导航；主要动作使用实心高对比。</dd></div>
        <div><dt>颜色</dt><dd>奶油白承载内容，1–2 个主色加 2–3 个粉彩辅助色；状态色必须与装饰色分离。</dd></div>
        <div><dt>描边</dt><dd>两条路线最有效：1px 极浅暖灰描边，或 1.5px 黑色线稿；避免中灰粗边配重阴影。</dd></div>
      </dl>
    </section>
    <section className="variant-list" aria-label="视觉方向">
      {variants.map((variant) => <article className={`variant-card variant-card--${variant.id}`} key={variant.id}>
        <div className="variant-copy">
          <p className="variant-index">{variant.index}</p>
          <p className="variant-rec">{variant.recommendation}</p>
          <h2>{variant.name}</h2>
          <p>{variant.summary}</p>
          <ul>{variant.traits.map((trait) => <li key={trait}>{trait}</li>)}</ul>
          <div className="variant-swatches" aria-label={`${variant.name} 色板`}>{variant.swatches.map((color) => <span key={color} style={{ background: color }} title={color}/>)}</div>
        </div>
        <PhonePreview variant={variant}/>
      </article>)}
    </section>
    <footer className="variants-footer"><strong>建议组合</strong><p>以 01 为基础，吸收 04 的清晰描边与信息层级；在开场和 Today 局部使用 02 的编辑感；03 仅用于分析与长期记忆页面的低强度背景。</p></footer>
  </main>;
}
