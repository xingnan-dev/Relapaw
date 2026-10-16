type Direction = {
  id: "orbit" | "poster" | "storybook" | "journal";
  number: string;
  name: string;
  note: string;
  traits: string[];
};

const directions: Direction[] = [
  {
    id: "orbit",
    number: "01",
    name: "漂浮陪伴轨道",
    note: "把三条原则变成围绕伙伴的轻盈线索，强调探索感，但压低科技气质。",
    traits: ["中心角色 132px", "弧形路径与悬浮胶囊", "雾蓝＋鼠尾草＋柔黄", "无硬描边，柔和内阴影"],
  },
  {
    id: "poster",
    number: "02",
    name: "伙伴编辑海报",
    note: "用强标题和从边缘探出的抽象伙伴制造记忆点，适合比赛演示。",
    traits: ["标题 40–48px / 800", "不对称满版构图", "暖杏＋雾紫高反差", "1.5px 墨绿线稿"],
  },
  {
    id: "storybook",
    number: "03",
    name: "安静关系绘本",
    note: "每页是一幕连续小故事：看见、陪伴、安全，情绪最温柔。",
    traits: ["宋体标题 36–42px", "大留白与低重心插画", "奶油白＋旧玫瑰＋雾灰绿", "极浅描边与纸张阴影"],
  },
  {
    id: "journal",
    number: "04",
    name: "相识手账拼贴",
    note: "把原则页和建档问答统一成一册手账，最接近当前品牌页面。",
    traits: ["标题 34–40px / 650", "错层纸页＋贴签＋胶带", "品牌四色分区", "虚线缝边与 1px 暖灰描边"],
  },
];

function Companion({ mood = "look" }: { mood?: "look" | "listen" | "safe" }) {
  return <svg className={`ov-companion ov-companion--${mood}`} viewBox="0 0 180 150" aria-hidden="true">
    <path className="ov-companion__body" d="M37 119c6-44 27-74 55-74 31 0 49 28 54 74" />
    <path d="m53 59 5-29 26 23M124 57l13-24-2 37" />
    <circle cx="74" cy="77" r="3" /><circle cx="111" cy="77" r="3" />
    <path d="M84 91c6 6 12 6 18 0M93 84v10" />
    {mood === "look" && <><path d="M18 105c19-18 30-20 45-11M146 93c12-5 21-1 27 7" /><circle cx="22" cy="101" r="4" /></>}
    {mood === "listen" && <><path d="M24 104c18 0 26 14 41 14M138 112c13-12 25-13 37-5" /><path d="M154 54c9-9 18-9 23-2-3 13-10 19-22 20" /></>}
    {mood === "safe" && <><path d="M28 106c19-15 38-17 57 3M100 110c18-19 36-20 53-4" /><path d="M84 30c8-12 21-12 28 0-7 10-14 15-14 15S90 40 84 30Z" /></>}
    <path className="ov-companion__ground" d="M22 120h138" />
  </svg>;
}

function PrincipleCopy() {
  return <div className="ov-copy">
    <p>01 · 先看见</p>
    <h3>观察，和猜想<br/>是两件事</h3>
    <span>先记下它做了什么，再慢慢理解为什么。</span>
  </div>;
}

function StoryDots() {
  return <div className="ov-story-dots" aria-label="三页故事进度"><i className="active"/><i/><i/></div>;
}

function OrbitDoodle({ kind }: { kind: "bone" | "star" | "paw" | "bowl" }) {
  return <svg className="ov-orbit-doodle" viewBox="0 0 44 44" aria-hidden="true">
    {kind === "bone" && <path d="M12 17c-4 0-6-3-4-6 2-3 6-2 8 1h12c2-3 6-4 8-1 2 3 0 6-4 6v10c4 0 6 3 4 6-2 3-6 2-8-1H16c-2 3-6 4-8 1-2-3 0-6 4-6Z"/>}
    {kind === "star" && <path d="m22 6 4 11 12 1-9 7 3 12-10-6-10 6 3-12-9-7 12-1Z"/>}
    {kind === "paw" && <><circle cx="14" cy="13" r="4"/><circle cx="29" cy="13" r="4"/><circle cx="9" cy="24" r="4"/><circle cx="35" cy="24" r="4"/><path d="M13 34c0-8 5-13 9-13s9 5 9 13c-5 4-13 4-18 0Z"/></>}
    {kind === "bowl" && <><path d="M8 20h28l-4 14H12Z"/><path d="M13 16c4-6 14-6 18 0M18 28h8"/></>}
  </svg>;
}

function OrbitPreview() {
  return <div className="ov-screen ov-screen--orbit">
    <StoryDots />
    <div className="ov-orbit-stage">
      <Companion />
      <span className="ov-float ov-float--one"><OrbitDoodle kind="bone"/></span>
      <span className="ov-float ov-float--two"><OrbitDoodle kind="star"/></span>
      <span className="ov-float ov-float--three"><OrbitDoodle kind="bowl"/></span>
      <span className="ov-float ov-float--paw"><OrbitDoodle kind="paw"/></span>
    </div>
    <PrincipleCopy />
    <button type="button">继续认识它 <b>→</b></button>
  </div>;
}

function PosterPreview() {
  return <div className="ov-screen ov-screen--poster">
    <StoryDots />
    <span className="ov-poster-tag">RELAPAW PRINCIPLE 01</span>
    <PrincipleCopy />
    <div className="ov-poster-character"><Companion /></div>
    <span className="ov-poster-note">不是答案，<br/>是小发现</span>
    <button type="button">翻到下一页</button>
  </div>;
}

function StorybookPreview() {
  return <div className="ov-screen ov-screen--storybook">
    <StoryDots />
    <p className="ov-story-kicker">今天，先坐在它身边</p>
    <PrincipleCopy />
    <div className="ov-story-scene"><Companion mood="listen"/><span className="ov-human-mark"/></div>
    <p className="ov-hand-note">“我先把看到的记下来。”</p>
    <button type="button">继续</button>
  </div>;
}

function JournalPreview() {
  return <div className="ov-screen ov-screen--journal">
    <StoryDots />
    <div className="ov-journal-tape" />
    <section className="ov-journal-paper">
      <span className="ov-journal-index">第一张小纸条</span>
      <PrincipleCopy />
      <Companion mood="look" />
      <span className="ov-sticker">先看见</span>
    </section>
    <section className="ov-profile-tease">
      <span>下一页</span><strong>先认识它</strong><small>名字 · 物种 · 一张慢慢补完的档案</small>
    </section>
    <button type="button">把这一页收好</button>
  </div>;
}

function Preview({ id }: { id: Direction["id"] }) {
  if (id === "orbit") return <OrbitPreview />;
  if (id === "poster") return <PosterPreview />;
  if (id === "storybook") return <StorybookPreview />;
  return <JournalPreview />;
}

export function OnboardingVariants() {
  return <main className="onboarding-lab">
    <header className="onboarding-lab__hero">
      <div><p>RELAPAW · FIRST MEETING STUDY</p><h1>第一次相识，<br/>不该像读说明书</h1></div>
      <p>四个方向都使用“连续故事＋独立构图”，并把英文降为注释。抽象伙伴和生活线索共同出现，资料填写将采用手账资料卡与分步问答。</p>
    </header>

    <section className="onboarding-rules" aria-labelledby="onboarding-rules-title">
      <div><p>REFERENCE LANGUAGE</p><h2 id="onboarding-rules-title">从参考图保留什么</h2></div>
      <dl>
        <div><dt>字体</dt><dd>中文主标题承担情绪；无衬线粗体用于现代活力，宋体用于温柔叙事。英文只保留 10–12px 注释。</dd></div>
        <div><dt>字号</dt><dd>移动主标题 36–48px，正文 16–18px，注释 11–13px；用尺度差代替堆叠装饰。</dd></div>
        <div><dt>排版</dt><dd>中心角色、边缘探出、低重心故事、错层纸页四种构图；每一页只讲一个原则。</dd></div>
        <div><dt>组件</dt><dd>环绕标签、实心胶囊按钮、分步问答、资料卡和进度点；所有可点击元素保持明确反馈。</dd></div>
        <div><dt>颜色</dt><dd>沿用奶油纸、鼠尾草绿、雾紫、暖杏和柔黄；高饱和色仅作 10–15% 的视觉锚点。</dd></div>
        <div><dt>描边</dt><dd>插画使用 1.5px 墨绿手绘线；功能卡使用 1px 暖灰线，避免黑色硬框和厚重投影。</dd></div>
      </dl>
    </section>

    <section className="onboarding-directions" aria-label="前置流程视觉方向">
      {directions.map((direction) => <article className={`onboarding-direction onboarding-direction--${direction.id}`} key={direction.id}>
        <div className="onboarding-direction__copy">
          <span>{direction.number}</span><p>VISUAL DIRECTION</p><h2>{direction.name}</h2><p>{direction.note}</p>
          <ul>{direction.traits.map((trait) => <li key={trait}>{trait}</li>)}</ul>
        </div>
        <Preview id={direction.id} />
      </article>)}
    </section>

    <footer className="onboarding-lab__recommendation"><strong>当前建议</strong><p>以 04“相识手账拼贴”为产品主方向，吸收 03 的故事节奏和 01 的少量漂浮标签；02 保留给比赛展示封面，不整套用于日常建档。</p></footer>
  </main>;
}
