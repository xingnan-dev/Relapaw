import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Onboarding } from "./components/Onboarding";
import { isOnboardingComplete } from "./state/onboarding";
import { PetSetup } from "./components/PetSetup";
import { Splash } from "./components/Splash";
import { CurrentPetProvider, useCurrentPet } from "./state/CurrentPetContext";
import { Timeline } from "./pages/Timeline";
import { Today } from "./pages/Today";
import { Understand } from "./pages/Understand";
import { Us } from "./pages/Us";
import { BrandAtmosphere, BrandMark, NavIcon, type NavIconName } from "./components/brand";
import { CapabilitiesProvider, useCapabilities } from "./state/CapabilitiesContext";
import { useAuth } from "./state/AuthContext";

const tabs = ["Today", "Understand", "Timeline", "Us"] as const;
type Tab = (typeof tabs)[number];
const tabMeta: Record<Tab, { label: string; description: string; icon: NavIconName }> = {
  Today: { label: "今天", description: "TODAY · 待回看", icon: "today" },
  Understand: { label: "记录", description: "RECORD · 事实与理解", icon: "understand" },
  Timeline: { label: "足迹", description: "TIMELINE · 时间线与来源", icon: "timeline" },
  Us: { label: "我们", description: "US · 关系与长期记忆", icon: "us" },
};

function AppFlow() {
  const { session, finishOnboarding } = useAuth();
  const { status } = useCurrentPet();
  const [booted, setBooted] = useState(false);
  const [showSetup, setShowSetup] = useState(false);
  const [onboardingCompletedHere, setOnboardingCompletedHere] = useState(false);
  const [reviewOnboarding, setReviewOnboarding] = useState(false);
  const [onboardingError, setOnboardingError] = useState("");

  useEffect(() => { if (status !== "loading") setBooted(true); }, [status]);
  if (!booted) return <Splash />;
  const onboardingComplete = session?.onboarding_complete ?? isOnboardingComplete();
  if (!onboardingComplete && !onboardingCompletedHere) return <><Onboarding
    onComplete={() => { setOnboardingError(""); void finishOnboarding().then(() => { setOnboardingCompletedHere(true); setShowSetup(true); }).catch(() => setOnboardingError("引导完成状态暂时无法保存，请重试。")); }}
    finalUnderlay={<PetSetup onDone={() => setShowSetup(false)} onSkip={() => setShowSetup(false)} />}
  />{onboardingError && <p className="onboarding-save-error" role="alert">{onboardingError}</p>}</>;
  if (showSetup) return <PetSetup onDone={() => setShowSetup(false)} onSkip={() => setShowSetup(false)} />;
  if (reviewOnboarding) return <Onboarding reviewMode onComplete={() => setReviewOnboarding(false)} />;
  return <MainShell onAddPet={() => setShowSetup(true)} onReviewOnboarding={() => setReviewOnboarding(true)} />;
}

function MainShell({ onAddPet, onReviewOnboarding }: { onAddPet: () => void; onReviewOnboarding: () => void }) {
  const { capabilities } = useCapabilities();
  const { signOut } = useAuth();
  const { pet, pets, setCurrentPet } = useCurrentPet();
  const [active, setActive] = useState<Tab>("Today");
  const pageRef = useRef<HTMLElement>(null);
  const [showDailyOpening, setShowDailyOpening] = useState(() => {
    try { return localStorage.getItem("relapaw:daily-opening") !== new Date().toLocaleDateString("en-CA"); }
    catch { return false; }
  });
  const [targetEpisodeId, setTargetEpisodeId] = useState<number | null>(null);
  const [targetUsMemory, setTargetUsMemory] = useState(false);
  const [targetPlanCreate, setTargetPlanCreate] = useState(false);
  const [signOutBusy, setSignOutBusy] = useState(false);
  const [signOutError, setSignOutError] = useState("");
  const [recordSubmitting, setRecordSubmitting] = useState(false);
  useEffect(() => { setTargetEpisodeId(null); setTargetUsMemory(false); setTargetPlanCreate(false); }, [pet?.id]);
  useLayoutEffect(() => {
    const page = pageRef.current;
    if (page && typeof page.scrollTo === "function") page.scrollTo({ top: 0, left: 0, behavior: "auto" });
    else if (page) page.scrollTop = 0;
    const frame = requestAnimationFrame(() => {
      const current = pageRef.current;
      if (current && typeof current.scrollTo === "function") current.scrollTo({ top: 0, left: 0, behavior: "auto" });
      else if (current) current.scrollTop = 0;
    });
    return () => cancelAnimationFrame(frame);
  }, [active]);
  const navigate = (page: Tab) => {
    if (window.location.hash) window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
    setActive(page);
  };
  const openEpisode = (episodeId: number) => { setTargetEpisodeId(episodeId); navigate("Timeline"); };
  const openMemory = () => { setTargetUsMemory(true); navigate("Us"); };
  const pages = {
    Today: <Today onAddPet={onAddPet} onUnderstand={() => navigate("Understand")} onOpenEpisode={openEpisode} startPlanCreation={targetPlanCreate} onPlanCreationOpened={() => setTargetPlanCreate(false)} />,
    Understand: <Understand onSaved={openEpisode} onCreatePlan={() => { setTargetPlanCreate(true); navigate("Today"); }} onSubmittingChange={setRecordSubmitting} />,
    Timeline: <Timeline initialEpisodeId={targetEpisodeId} onInitialEpisodeOpened={() => setTargetEpisodeId(null)} onOpenMemory={openMemory} />,
    Us: <Us onAddPet={onAddPet} initialSection={targetUsMemory ? "memory" : null} onInitialSectionOpened={() => setTargetUsMemory(false)} />,
  };
  const enterToday = () => {
    try { localStorage.setItem("relapaw:daily-opening", new Date().toLocaleDateString("en-CA")); } catch { /* non-persistent environments still continue */ }
    navigate("Today");
    setShowDailyOpening(false);
  };
  return (
    <div className="app-shell">
      <BrandAtmosphere/>
      <header className="app-header">
        <div className="brand-lockup"><BrandMark/><div><h1>Relapaw</h1><p>Beyond the Paw. The Bond.</p></div></div>
        <div className="app-header__context">
          <p className="brand-promise">先看见发生了什么，再慢慢理解彼此。</p>
          {pets.length > 0 && <label className="pet-switcher"><span>当前宠物</span>
            <select aria-label="当前宠物" value={pet?.id ?? ""} disabled={recordSubmitting} onChange={(event) => {
              const next = pets.find((item) => item.id === Number(event.target.value));
              if (!next || next.id === pet?.id) return;
              setCurrentPet(next);
            }}>{pets.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select>
          </label>}
        </div>
        <div className="app-header__actions">
          <button type="button" className="text-button signout-button" disabled={signOutBusy} onClick={() => {
            setSignOutBusy(true); setSignOutError("");
            void signOut().catch(() => setSignOutError("退出失败，请检查网络后重试。")).finally(() => setSignOutBusy(false));
          }}>{signOutBusy ? "正在退出…" : "安全退出"}</button>
          <button type="button" className="text-button onboarding-review-button" onClick={onReviewOnboarding}>重看三页介绍</button>
        </div>
        {signOutError && <p role="alert">{signOutError}</p>}
      </header>
      {capabilities.synthetic_data && <p className="demo-data-banner" role="status">合成演示数据 · {capabilities.dataset_version ?? "数据集待验证"}</p>}
      <main ref={pageRef} className="page-transition" key={`${active}:${pet?.id ?? "none"}`}>{pages[active]}</main>
      <nav className="bottom-nav" aria-label="Primary navigation">
        <p className="nav-label">RELAPAW</p>
        {tabs.map((tab) => <button key={tab} type="button" data-nav={tab.toLowerCase()} aria-label={tab} aria-current={active === tab ? "page" : undefined} onClick={() => navigate(tab)}>
          <span className="nav-icon"><NavIcon name={tabMeta[tab].icon}/></span><span className="nav-copy"><strong>{tabMeta[tab].label}</strong><small>{tabMeta[tab].description}</small></span>
        </button>)}
      </nav>
      {showDailyOpening && <section className="daily-opening" role="region" aria-labelledby="daily-opening-title">
        <div className="daily-opening__copy">
          <p className="eyebrow">RELAPAW · 今日相见</p>
          <h2 id="daily-opening-title"><span>今天，也</span><span>好好看见它</span></h2>
          <p>它不会说出全部感受，但每个小动作，都值得被温柔地记住。</p>
          <button className="primary" type="button" onClick={enterToday}>和它一起开始 <span aria-hidden="true">→</span></button>
        </div>
        <div className="daily-opening__media">
          <img src="/brand/relapaw-welcome-corgi-v4.png" width="1672" height="941" decoding="async" alt="怀旧绘本中的柯基依偎在主人身边，窗外是安静的草坡与云" />
        </div>
      </section>}
    </div>
  );
}

export default function App() {
  return <CapabilitiesProvider><CurrentPetProvider><AppFlow /></CurrentPetProvider></CapabilitiesProvider>;
}
