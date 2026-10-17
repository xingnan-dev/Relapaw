import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { CapabilitiesProvider } from "./state/CapabilitiesContext";
import "./styles.css";

async function loadRoot() {
  if (!import.meta.env.DEV) return App;

  if (window.location.pathname === "/visual-variants") {
    await import("./visual-variants.css");
    return (await import("./VisualVariants")).VisualVariants;
  }
  if (window.location.pathname === "/onboarding-variants") {
    await import("./onboarding-variants.css");
    return (await import("./OnboardingVariants")).OnboardingVariants;
  }
  if (window.location.pathname === "/first-meeting-preview") {
    await import("./onboarding-variants.css");
    return (await import("./FirstMeetingPreview")).FirstMeetingPreview;
  }
  return App;
}

void loadRoot().then((Root) => {
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode><CapabilitiesProvider><Root /></CapabilitiesProvider></React.StrictMode>,
  );
});
