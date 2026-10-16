import { useEffect, useRef, useState, type ReactNode } from "react";
import firstMeetingStickers from "../assets/relapaw-first-meeting-stickers-v1.png";

const slides = [
  { title: "先看见，再慢慢理解", subtitle: "OBSERVE BEFORE INTERPRETING", body: "先记下它做了什么，再写下你的想法。观察和猜想，是两件不同的事。", note: "这一页，先留给事实", mood: "look" },
  { title: "看见变化，不替它说话", subtitle: "NOTICE CHANGE WITH CARE", body: "从日常、生活事件与持续观察中，看见变化，也为不确定留一点位置。", note: "陪它多看一会儿", mood: "listen" },
  { title: "不舒服时，安全最重要", subtitle: "SAFETY COMES FIRST", body: "Relapaw 不诊断，也不代替兽医。需要帮助时，先联系真正能照顾它的人。", note: "理解可以慢一点", mood: "safe" },
];

function StoryCompanion({ mood }: { mood: string }) {
  return <svg className={`onboarding-companion onboarding-companion--${mood}`} viewBox="0 0 220 180" aria-hidden="true">
    <path className="onboarding-companion__body" d="M48 145c8-55 34-91 69-91 38 0 61 35 67 91" />
    <path d="m68 71 6-37 32 29M157 69l16-31-2 47" />
    <circle cx="94" cy="94" r="3.5"/><circle cx="139" cy="94" r="3.5"/><path d="M106 111c7 7 15 7 22 0M117 102v12"/>
    {mood === "look" && <><path d="M17 137c24-23 39-25 58-14M183 121c15-7 27-2 35 9"/><circle cx="24" cy="132" r="5"/></>}
    {mood === "listen" && <><path d="M21 132c22 0 32 18 51 18M174 142c16-15 31-17 46-7"/><path d="M186 52c11-11 22-11 29-2-4 16-13 24-28 25"/></>}
    {mood === "safe" && <><path d="M23 136c25-20 48-21 72 4M113 141c22-24 45-25 65-5"/><path d="M106 34c10-15 26-15 35 0-9 12-18 18-18 18s-10-6-17-18Z"/></>}
    <path className="onboarding-companion__ground" d="M29 146h169"/>
  </svg>;
}

export const firstMeetingStickerCrops = {
  magnifier: [14, 42, 312, 286],
  bowl: [326, 72, 304, 250],
  bone: [646, 70, 300, 258],
  pawPink: [938, 65, 282, 270],
  pawGreen: [1207, 65, 292, 270],
  path: [18, 323, 282, 306],
  ball: [288, 334, 276, 288],
  flowers: [556, 333, 302, 300],
  sparkles: [864, 334, 282, 292],
  house: [1145, 342, 354, 282],
  heart: [1470, 330, 322, 300],
  medkit: [10, 631, 286, 258],
  blanket: [270, 652, 252, 226],
  cat: [1288, 666, 232, 214],
} as const;

const moodStickers = {
  look: ["magnifier", "bowl", "bone", "pawPink", "path"],
  listen: ["ball", "flowers", "sparkles", "cat", "pawGreen"],
  safe: ["house", "heart", "medkit", "blanket", "sparkles"],
} as const;

export type FirstMeetingSticker = keyof typeof firstMeetingStickerCrops;

export function CroppedSticker({ name }: { name: FirstMeetingSticker }) {
  const [x, y, width, height] = firstMeetingStickerCrops[name];
  return <svg viewBox={`${x} ${y} ${width} ${height}`} preserveAspectRatio="xMidYMid meet" aria-hidden="true">
    <image href={firstMeetingStickers} width="1792" height="896" />
  </svg>;
}

function StickerCluster({ mood }: { mood: keyof typeof moodStickers }) {
  return <div className={`onboarding-stickers onboarding-stickers--${mood}`} aria-hidden="true">
    {moodStickers[mood].map((name, index) => <span key={`${name}-${index}`}><CroppedSticker name={name} /></span>)}
  </div>;
}

export function Onboarding({ onComplete, finalUnderlay }: { onComplete: () => void; finalUnderlay?: ReactNode }) {
  const [index, setIndex] = useState(0);
  const [turn, setTurn] = useState<{ to: number | null; direction: "forward" | "back" } | null>(null);
  const timers = useRef<number[]>([]);
  const slide = slides[index];

  useEffect(() => () => timers.current.forEach(window.clearTimeout), []);

  function turnPage(direction: 1 | -1) {
    if (turn) return;
    const nextIndex = index + direction;
    const isComplete = nextIndex >= slides.length;
    if (isComplete) {
      setTurn({ to: null, direction: "forward" });
      timers.current.push(window.setTimeout(onComplete, 850));
      return;
    }
    setTurn({ to: isComplete ? null : nextIndex, direction: direction === 1 ? "forward" : "back" });
    timers.current.push(window.setTimeout(() => {
      setIndex(nextIndex);
      setTurn(null);
    }, 850));
  }

  function storyCard(cardIndex: number, layer: "current" | "under" | "turning") {
    const card = slides[cardIndex];
    const motionClass = layer === "turning" && turn
      ? ` onboarding-story--turn-${turn.direction}`
      : layer === "under" ? " onboarding-story--under" : "";
    return <section className={`onboarding-story onboarding-story--${card.mood}${motionClass}`} aria-live={layer === "current" ? "polite" : undefined} aria-hidden={layer !== "current"}>
      <span className="onboarding-tape" aria-hidden="true" />
      <div className="onboarding-story__copy">
        <p className="eyebrow">第 {cardIndex + 1} 张小纸条</p>
        <h1>{card.title}</h1>
        <p className="onboarding-subtitle">{card.subtitle}</p>
        <p>{card.body}</p>
        <p className="onboarding-hand-note">{card.note}</p>
      </div>
      <div className="onboarding-story__art"><StickerCluster mood={card.mood as keyof typeof moodStickers}/><StoryCompanion mood={card.mood}/></div>
    </section>;
  }

  return (
    <main className={`onboarding ${turn?.to === null ? "onboarding--final-turn" : ""}`}>
      {turn?.to === null && finalUnderlay && <div className="onboarding-final-underlay" aria-hidden="true">{finalUnderlay}</div>}
      <div className="onboarding-progress" aria-label={`第 ${index + 1} 页，共 ${slides.length} 页`}>
        {slides.map((_, step) => <span key={step} className={step === index ? "active" : ""} />)}
      </div>
      <div className="onboarding-stage">
        {turn?.to != null && storyCard(turn.to, "under")}
        {storyCard(index, turn ? "turning" : "current")}
      </div>
      <div className="onboarding-actions">
        <button type="button" className="text-button" onClick={onComplete} disabled={Boolean(turn)}>跳过</button>
        {index > 0 && <button type="button" onClick={() => turnPage(-1)} disabled={Boolean(turn)}>返回</button>}
        <button type="button" className="primary" onClick={() => turnPage(1)} disabled={Boolean(turn)}>
          {index === slides.length - 1 ? "翻到它的档案" : "翻到下一页"}
        </button>
      </div>
    </main>
  );
}
