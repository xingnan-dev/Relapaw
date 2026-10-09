import { useEffect, useState } from "react";
import { Onboarding } from "./components/Onboarding";
import { PetSetup } from "./components/PetSetup";
import { Splash } from "./components/Splash";
import { CurrentPetProvider, useCurrentPet } from "./state/CurrentPetContext";
import { completeOnboarding, isOnboardingComplete } from "./state/onboarding";
import { Timeline } from "./pages/Timeline";
import { Today } from "./pages/Today";
import { Understand } from "./pages/Understand";
import { Us } from "./pages/Us";

const tabs = ["Today", "Understand", "Timeline", "Us"] as const;
type Tab = (typeof tabs)[number];

function AppFlow() {
  const { status } = useCurrentPet();
  const [booted, setBooted] = useState(false);
  const [onboarded, setOnboarded] = useState(isOnboardingComplete);
  const [showSetup, setShowSetup] = useState(false);

  useEffect(() => { if (status !== "loading") setBooted(true); }, [status]);
  if (!booted) return <Splash />;
  if (!onboarded) return <Onboarding onComplete={() => { completeOnboarding(); setOnboarded(true); setShowSetup(true); }} />;
  if (showSetup) return <PetSetup onDone={() => setShowSetup(false)} onSkip={() => setShowSetup(false)} />;
  return <MainShell onAddPet={() => setShowSetup(true)} />;
}

function MainShell({ onAddPet }: { onAddPet: () => void }) {
  const [active, setActive] = useState<Tab>("Today");
  const [targetEpisodeId, setTargetEpisodeId] = useState<number | null>(null);
  const openEpisode = (episodeId: number) => { setTargetEpisodeId(episodeId); setActive("Timeline"); };
  const pages = {
    Today: <Today onAddPet={onAddPet} onUnderstand={() => setActive("Understand")} onOpenEpisode={openEpisode} />,
    Understand: <Understand onSaved={() => setActive("Timeline")} />,
    Timeline: <Timeline initialEpisodeId={targetEpisodeId} onInitialEpisodeOpened={() => setTargetEpisodeId(null)} />,
    Us: <Us onAddPet={onAddPet} />,
  };
  return (
    <div className="app-shell">
      <header className="app-header"><div><h1>Relapaw</h1><p>Beyond the Paw. The Bond.</p></div></header>
      <main className="page-transition" key={active}>{pages[active]}</main>
      <nav className="bottom-nav" aria-label="Primary navigation">
        {tabs.map((tab) => <button key={tab} type="button" aria-current={active === tab ? "page" : undefined} onClick={() => setActive(tab)}><span aria-hidden="true">{tab === "Today" ? "○" : tab === "Understand" ? "◇" : tab === "Timeline" ? "≡" : "◎"}</span>{tab}</button>)}
      </nav>
    </div>
  );
}

export default function App() {
  return <CurrentPetProvider><AppFlow /></CurrentPetProvider>;
}
