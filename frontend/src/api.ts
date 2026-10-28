import type { AnalysisRun, AssistantGuidanceRun, BaselineSnapshot, BaselineWindow, Capabilities, CaregiverProfile, CompleteEpisodeCreate, ConfirmationDecision, EducationalGuidance, Episode, EpisodeUpdate, FollowUp, FollowUpComplete, GuidanceMode, InteractionPatternCandidate, InteractionPatternDecisionAction, LifeEvent, LifeEventType, ManualMemoryCategory, MediaAttachment, MemoryCandidate, MemoryDecisionType, ObservationPlan, ObservationPlanStatus, Pet, PetAvatar, PetBaseline, PetCreate, RelationshipEvent, RelationshipKind, RelationshipObservationType, TimelineFilters, TimelinePage, UserConfirmation, VeterinaryEscalation, VeterinaryEscalationStatus } from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

let activeCsrfToken: string | null = null;

export function setCsrfToken(token: string | null): void {
  activeCsrfToken = token;
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(init?.headers);
  if (!["GET", "HEAD", "OPTIONS"].includes(method) && activeCsrfToken && !headers.has("X-CSRF-Token")) {
    headers.set("X-CSRF-Token", activeCsrfToken);
  }
  const response = await fetch(url, { ...init, headers, credentials: "include" });
  if (!response.ok) {
    let payload: { error?: { code?: string; message?: string } } | undefined;
    try {
      payload = await response.json();
    } catch {
      // The status code remains actionable even when a proxy returns non-JSON.
    }
    if (response.status === 401) window.dispatchEvent(new Event("relapaw:session-expired"));
    if (response.status === 403 && payload?.error?.code === "CONSENT_REQUIRED") {
      window.dispatchEvent(new Event("relapaw:consent-required"));
    }
    throw new ApiError(payload?.error?.message ?? "Request failed", response.status, payload?.error?.code);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export interface AuthSession { user_id: string; status: "ACTIVE"; consent_required: boolean; onboarding_complete: boolean; }

export interface PrivacyNotice {
  terms_version: string;
  privacy_version: string;
  legal_review_status: "APPROVED" | "PENDING";
  data_inventory_version: string;
}

export function getAuthSession(): Promise<AuthSession> {
  return request("/api/v1/auth/session");
}

export function requestLoginChallenge(email: string): Promise<{ status: string }> {
  return request("/api/v1/auth/otp/request", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }),
  });
}

export function verifyLoginChallenge(email: string, code: string): Promise<AuthSession> {
  return request("/api/v1/auth/otp/verify", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, code }),
  });
}

export function getCsrfToken(): Promise<{ csrf_token: string }> {
  return request("/api/v1/auth/csrf", { method: "POST" });
}

export function logout(csrfToken: string): Promise<void> {
  return request("/api/v1/auth/logout", {
    method: "POST", headers: { "X-CSRF-Token": csrfToken },
  });
}

export function completeAccountOnboarding(): Promise<AuthSession> {
  return request("/api/v1/auth/onboarding/complete", { method: "POST" });
}

export function getPrivacyNotice(): Promise<PrivacyNotice> {
  return request("/api/v1/privacy/notice");
}

export function acceptPrivacyConsent(notice: PrivacyNotice): Promise<{ status: string }> {
  return request("/api/v1/privacy/consent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      terms_version: notice.terms_version,
      privacy_version: notice.privacy_version,
      source: "ONBOARDING",
      affirm_adult_owner: true,
    }),
  });
}

export async function downloadAccountExport(): Promise<void> {
  const response = await fetch("/api/v1/privacy/export", { credentials: "include" });
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event("relapaw:session-expired"));
    let code: string | undefined;
    try { code = (await response.clone().json() as { error?: { code?: string } }).error?.code; } catch { /* proxy response */ }
    if (response.status === 403 && code === "CONSENT_REQUIRED") window.dispatchEvent(new Event("relapaw:consent-required"));
    throw new ApiError("Export failed", response.status, code);
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = "relapaw-account-export.json";
  link.click();
  URL.revokeObjectURL(url);
}

export function requestAccountDeletion(): Promise<{ status: string; deletion_due_at: string }> {
  return request("/api/v1/privacy/account", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirmation: "DELETE MY ACCOUNT" }),
  });
}

export function listPets(includeArchived = false): Promise<Pet[]> {
  return request(`/api/v1/pets${includeArchived ? "?include_archived=true" : ""}`);
}

export function getCapabilities(): Promise<Capabilities> {
  return request("/api/v1/capabilities");
}

export function getPet(petId: number): Promise<Pet> {
  return request(`/api/v1/pets/${petId}`);
}

export function createPet(payload: PetCreate): Promise<Pet> {
  return request("/api/v1/pets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function uploadPetAvatar(petId: number, file: File): Promise<PetAvatar> {
  return request(`/api/v1/pets/${petId}/avatar`, { method: "PUT", headers: { "Content-Type": file.type, "X-Filename": encodeURIComponent(file.name) }, body: file });
}
export function deletePetAvatar(petId: number): Promise<void> { return request(`/api/v1/pets/${petId}/avatar`, { method: "DELETE" }); }
export function petAvatarUrl(petId: number, version?: string): string { return `/api/v1/pets/${petId}/avatar/content${version ? `?v=${encodeURIComponent(version)}` : ""}`; }
export function getCaregiverProfile(): Promise<CaregiverProfile> { return request("/api/v1/owner-profile"); }
export function saveCaregiverProfile(payload: Omit<CaregiverProfile, "id" | "ai_context_consent_updated_at">): Promise<CaregiverProfile> {
  return request("/api/v1/owner-profile", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
}
export function deleteCaregiverProfile(): Promise<void> { return request("/api/v1/owner-profile", { method: "DELETE" }); }

export function updatePet(petId: number, payload: Omit<Partial<PetCreate>, "breed" | "birth_date" | "approximate_age" | "sex" | "neutered" | "weight_kg" | "known_conditions" | "medications" | "allergies" | "living_environment" | "veterinarian_confirmed_facts" | "owner_observations"> & {
  breed?: string | null;
  birth_date?: string | null;
  approximate_age?: string | null;
  sex?: string | null;
  neutered?: boolean | null;
  weight_kg?: number | null;
  known_conditions?: string[] | null;
  medications?: string[] | null;
  allergies?: string[] | null;
  living_environment?: string | null;
  veterinarian_confirmed_facts?: Array<Record<string, string>> | null;
  owner_observations?: Record<string, string> | null;
  archived?: boolean;
}): Promise<Pet> {
  return request(`/api/v1/pets/${petId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getTimeline(petId: number, page = 1, pageSize = 20, filters: TimelineFilters = {}): Promise<TimelinePage> {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (filters.from) query.set("from", filters.from);
  if (filters.to) query.set("to", filters.to);
  if (filters.episode_type) query.set("episode_type", filters.episode_type);
  if (filters.plan_id) query.set("plan_id", String(filters.plan_id));
  if (filters.q) query.set("q", filters.q);
  if (filters.category) query.set("category", filters.category);
  return request(`/api/v1/pets/${petId}/timeline?${query}`);
}

export function getEpisode(episodeId: number): Promise<Episode> { return request(`/api/v1/episodes/${episodeId}`); }
export function getEducationalGuidance(episodeId: number): Promise<EducationalGuidance> { return request(`/api/v1/episodes/${episodeId}/educational-guidance`); }
export function listMedia(episodeId: number): Promise<MediaAttachment[]> { return request(`/api/v1/episodes/${episodeId}/media`); }
export type MediaSource = { type: "episode" | "life-event" | "relationship-event"; id: number; petId?: number };
function mediaSourceUrl(source: MediaSource): string { return source.type === "episode" ? `/api/v1/episodes/${source.id}/media` : source.type === "life-event" ? `/api/v1/life-events/${source.id}/media` : `/api/v1/relationship-events/${source.id}/media`; }
export function listSourceMedia(source: MediaSource): Promise<MediaAttachment[]> { return request(mediaSourceUrl(source)); }
export function listPetMedia(petId: number): Promise<MediaAttachment[]> { return request(`/api/v1/pets/${petId}/media`); }
export function uploadSourceMedia(source: MediaSource, file: File, durationSeconds?: number): Promise<MediaAttachment> { const headers: Record<string, string> = { "Content-Type": file.type, "X-Filename": encodeURIComponent(file.name) }; if (source.petId) headers["X-Pet-ID"] = String(source.petId); if (durationSeconds) headers["X-Media-Duration-Seconds"] = String(Math.ceil(durationSeconds)); return request(mediaSourceUrl(source), { method: "POST", headers, body: file }); }
export function uploadMedia(episodeId: number, file: File): Promise<MediaAttachment> { return uploadSourceMedia({ type: "episode", id: episodeId }, file); }
export function updateMediaFacts(id: number, observable_facts: string | null): Promise<MediaAttachment> { return request(`/api/v1/media/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ observable_facts }) }); }
export function updateMediaMetadata(id: number, payload: { captured_at: string | null; owner_caption: string | null; change_summary: string | null }): Promise<MediaAttachment> { return request(`/api/v1/media/${id}/metadata`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); }
export function decideMediaCandidate(id: number, action: "CONFIRM" | "REJECT" | "WITHDRAW"): Promise<MediaAttachment> { return request(`/api/v1/media/${id}/candidate`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action }) }); }
export function deleteMedia(id: number): Promise<void> { return request(`/api/v1/media/${id}`, { method: "DELETE" }); }
export function addMemoryMediaReference(candidateId: number, mediaAttachmentId: number): Promise<MemoryCandidate> { return request(`/api/v1/memory-candidates/${candidateId}/media-references`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ media_attachment_id: mediaAttachmentId }) }); }
export function removeMemoryMediaReference(candidateId: number, mediaAttachmentId: number): Promise<MemoryCandidate> { return request(`/api/v1/memory-candidates/${candidateId}/media-references/${mediaAttachmentId}`, { method: "DELETE" }); }
export function updateEpisode(episodeId: number, payload: EpisodeUpdate): Promise<Episode> {
  return request(`/api/v1/episodes/${episodeId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
}
export function deleteEpisode(episodeId: number): Promise<void> { return request(`/api/v1/episodes/${episodeId}`, { method: "DELETE" }); }
export function updateVeterinaryEscalation(escalationId: number, status: VeterinaryEscalationStatus): Promise<VeterinaryEscalation> {
  return request(`/api/v1/veterinary-escalations/${escalationId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
}

export function createCompleteEpisode(payload: CompleteEpisodeCreate): Promise<Episode> {
  return request("/api/v1/episodes/complete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function scheduleFollowUp(episodeId: number, scheduledAt: string): Promise<FollowUp> {
  return request(`/api/v1/episodes/${episodeId}/follow-ups`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ scheduled_at: scheduledAt }) });
}
export function listFollowUps(petId: number): Promise<FollowUp[]> {
  const offset = new Date().getTimezoneOffset();
  return request(`/api/v1/pets/${petId}/follow-ups?status=PENDING&timing=ACTIONABLE&timezone_offset_minutes=${offset}`);
}
export function completeFollowUp(followUpId: number, payload: FollowUpComplete): Promise<Episode> {
  return request(`/api/v1/follow-ups/${followUpId}/complete`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
}
export function cancelFollowUp(followUpId: number): Promise<FollowUp> {
  return request(`/api/v1/follow-ups/${followUpId}/cancel`, { method: "POST" });
}
export function listObservationPlans(petId: number): Promise<ObservationPlan[]> { return request(`/api/v1/pets/${petId}/observation-plans`); }
export function createObservationPlan(petId: number, payload: { status: ObservationPlanStatus; start_at: string; end_at: string; goal: string; items: Array<{ label: string; description?: string; is_required: boolean }> }): Promise<ObservationPlan> { return request(`/api/v1/pets/${petId}/observation-plans`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); }
export function updateObservationPlan(planId: number, payload: ObservationPlanStatus | { goal?: string; start_at?: string; end_at?: string; items?: Array<{ label: string; description?: string; is_required: boolean }>; status?: ObservationPlanStatus }): Promise<ObservationPlan> { return request(`/api/v1/observation-plans/${planId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(typeof payload === "string" ? { status: payload } : payload) }); }

export function listAnalysisRuns(episodeId: number): Promise<AnalysisRun[]> {
  return request(`/api/v1/episodes/${episodeId}/analysis-runs`);
}

export function createAnalysisRun(episodeId: number, requestId: string): Promise<AnalysisRun> {
  return request(`/api/v1/episodes/${episodeId}/analysis-runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request_id: requestId }),
  });
}

export function listAssistantGuidanceRuns(episodeId: number): Promise<AssistantGuidanceRun[]> {
  return request(`/api/v1/episodes/${episodeId}/assistant-guidance-runs`);
}

export function createAssistantGuidanceRun(episodeId: number, requestId: string, mode: GuidanceMode): Promise<AssistantGuidanceRun> {
  return request(`/api/v1/episodes/${episodeId}/assistant-guidance-runs`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request_id: requestId, mode }),
  });
}

export function decideClaim(claimId: number, decision: ConfirmationDecision): Promise<UserConfirmation> {
  return request(`/api/v1/claims/${claimId}/confirmations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision }),
  });
}

export function createMemoryCandidate(claimId: number): Promise<MemoryCandidate> {
  return request(`/api/v1/claims/${claimId}/memory-candidate`, { method: "POST" });
}

export function getPetBaseline(petId: number): Promise<PetBaseline> {
  return request(`/api/v1/pets/${petId}/baseline`);
}

export function savePetBaseline(petId: number, payload: Omit<PetBaseline, "id" | "pet_id">): Promise<PetBaseline> {
  return request(`/api/v1/pets/${petId}/baseline`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function listLifeEvents(petId: number): Promise<LifeEvent[]> {
  return request(`/api/v1/pets/${petId}/life-events`);
}

export function createLifeEvent(petId: number, payload: { event_type: LifeEventType; happened_at: string; description: string | null }): Promise<LifeEvent> {
  return request(`/api/v1/pets/${petId}/life-events`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
}

export function updateLifeEvent(eventId: number, payload: { event_type: LifeEventType; happened_at: string; description: string | null }): Promise<LifeEvent> {
  return request(`/api/v1/life-events/${eventId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
}
export function deleteLifeEvent(eventId: number): Promise<void> { return request(`/api/v1/life-events/${eventId}`, { method: "DELETE" }); }

export type RelationshipEventPayload = { relationship_kind: RelationshipKind; participant_pet_ids: number[]; happened_at: string; observation_type: RelationshipObservationType; observation_text: string; owner_interpretation: string | null; source_episode_id: number | null };
export function listRelationshipEvents(petId: number): Promise<RelationshipEvent[]> { return request(`/api/v1/pets/${petId}/relationship-events`); }
export function createRelationshipEvent(payload: RelationshipEventPayload): Promise<RelationshipEvent> { return request("/api/v1/relationship-events", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); }
export function updateRelationshipEvent(eventId: number, payload: RelationshipEventPayload): Promise<RelationshipEvent> { return request(`/api/v1/relationship-events/${eventId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); }
export function deleteRelationshipEvent(eventId: number): Promise<void> { return request(`/api/v1/relationship-events/${eventId}`, { method: "DELETE" }); }
export type InteractionPatternCreatePayload = { relationship_kind: RelationshipKind; participant_pet_ids: number[]; initial_self_report: string | null; title: string; observable_pattern: string; support_event_ids: number[]; contradiction_event_ids: number[]; counterevidence_summary: string; confidence_limit: string };
export type InteractionPatternUpdatePayload = Pick<InteractionPatternCreatePayload, "title" | "observable_pattern" | "counterevidence_summary" | "confidence_limit"> & { change_summary: string | null };
export function listInteractionPatterns(petId: number): Promise<InteractionPatternCandidate[]> { return request(`/api/v1/pets/${petId}/interaction-patterns`); }
export function createInteractionPattern(payload: InteractionPatternCreatePayload): Promise<InteractionPatternCandidate> { return request("/api/v1/interaction-patterns", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); }
export function updateInteractionPattern(id: number, payload: InteractionPatternUpdatePayload): Promise<InteractionPatternCandidate> { return request(`/api/v1/interaction-patterns/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); }
export function decideInteractionPattern(id: number, action: InteractionPatternDecisionAction, note: string | null = null): Promise<InteractionPatternCandidate> { return request(`/api/v1/interaction-patterns/${id}/decisions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, note }) }); }
export function deleteInteractionPattern(id: number): Promise<void> { return request(`/api/v1/interaction-patterns/${id}`, { method: "DELETE" }); }

export function listMemoryCandidates(petId: number): Promise<MemoryCandidate[]> {
  return request(`/api/v1/pets/${petId}/memory-candidates`);
}

export function createManualMemoryCandidate(
  petId: number,
  payload: { category: ManualMemoryCategory; statement: string },
): Promise<MemoryCandidate> {
  return request(`/api/v1/pets/${petId}/memory-candidates/manual`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateManualMemoryCandidate(candidateId: number, payload: { category: ManualMemoryCategory; statement: string }): Promise<MemoryCandidate> {
  return request(`/api/v1/memory-candidates/${candidateId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function decideMemoryCandidate(candidateId: number, requestId: string, decision: MemoryDecisionType): Promise<MemoryCandidate> {
  return request(`/api/v1/memory-candidates/${candidateId}/decisions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request_id: requestId, decision }),
  });
}

export function getLatestBaselineSnapshot(petId: number, window: BaselineWindow): Promise<BaselineSnapshot> {
  return request(`/api/v1/pets/${petId}/baseline-snapshots/latest?window=${window}`);
}

export function recomputeBaselineSnapshot(petId: number, window: BaselineWindow, asOf: string): Promise<BaselineSnapshot> {
  return request(`/api/v1/pets/${petId}/baseline-snapshots/recompute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ window, as_of: asOf }),
  });
}
