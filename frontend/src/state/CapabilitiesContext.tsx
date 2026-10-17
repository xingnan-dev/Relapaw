import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { getCapabilities } from "../api";
import type { Capabilities } from "../types";

type CapabilityStatus = "loading" | "ready" | "error";

const safeDefaults: Capabilities = {
  environment: "unknown",
  synthetic_data: false,
  dataset_version: null,
  ai_analysis_enabled: false,
  model_qualification: "NOT_QUALIFIED",
};

interface CapabilitiesValue {
  capabilities: Capabilities;
  status: CapabilityStatus;
  retry: () => void;
}

const CapabilitiesContext = createContext<CapabilitiesValue>({
  capabilities: safeDefaults,
  status: "loading",
  retry: () => undefined,
});

export function CapabilitiesProvider({ children }: { children: ReactNode }) {
  const [capabilities, setCapabilities] = useState(safeDefaults);
  const [status, setStatus] = useState<CapabilityStatus>("loading");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setStatus("loading");
    getCapabilities().then((result) => {
      if (!active) return;
      setCapabilities(result);
      setStatus("ready");
    }).catch(() => {
      if (!active) return;
      setCapabilities(safeDefaults);
      setStatus("error");
    });
    return () => { active = false; };
  }, [attempt]);

  const value = useMemo<CapabilitiesValue>(() => ({
    capabilities,
    status,
    retry: () => setAttempt((current) => current + 1),
  }), [capabilities, status]);

  return <CapabilitiesContext.Provider value={value}>{children}</CapabilitiesContext.Provider>;
}

export function useCapabilities(): CapabilitiesValue {
  return useContext(CapabilitiesContext);
}
