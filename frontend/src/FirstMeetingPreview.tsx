import { useState } from "react";
import { Onboarding } from "./components/Onboarding";
import { PetSetup } from "./components/PetSetup";
import { CurrentPetProvider } from "./state/CurrentPetContext";

function PreviewFlow() {
  const [stage, setStage] = useState<"onboarding" | "profile">("onboarding");
  return stage === "onboarding"
    ? <Onboarding onComplete={() => setStage("profile")} finalUnderlay={<PetSetup onDone={() => setStage("onboarding")} onSkip={() => setStage("onboarding")} />} />
    : <PetSetup onDone={() => setStage("onboarding")} onSkip={() => setStage("onboarding")} />;
}

export function FirstMeetingPreview() {
  return <CurrentPetProvider><PreviewFlow /></CurrentPetProvider>;
}
