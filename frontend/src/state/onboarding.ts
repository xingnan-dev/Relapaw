const LEGACY_ONBOARDING_KEY = "relapaw.onboarding.completed";

/** Compatibility only for isolated component tests and pre-account Alpha browsers.
 * Authenticated product flow always uses AuthSession.onboarding_complete.
 */
export function isOnboardingComplete(): boolean {
  try { return localStorage.getItem(LEGACY_ONBOARDING_KEY) === "true"; }
  catch { return false; }
}
