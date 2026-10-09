import type { CompleteEpisodeCreate, Episode, EpisodeUpdate, FollowUp, FollowUpComplete, ObservationPlan, ObservationPlanStatus, Pet, PetCreate, TimelineFilters, TimelinePage, VeterinaryEscalation, VeterinaryEscalationStatus } from "./types";

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

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    let payload: { error?: { code?: string; message?: string } } | undefined;
    try {
      payload = await response.json();
    } catch {
      // The status code remains actionable even when a proxy returns non-JSON.
    }
    throw new ApiError(payload?.error?.message ?? "Request failed", response.status, payload?.error?.code);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function listPets(): Promise<Pet[]> {
  return request("/api/v1/pets");
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

export function getTimeline(petId: number, page = 1, pageSize = 20, filters: TimelineFilters = {}): Promise<TimelinePage> {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (filters.from) query.set("from", filters.from);
  if (filters.to) query.set("to", filters.to);
  if (filters.episode_type) query.set("episode_type", filters.episode_type);
  if (filters.plan_id) query.set("plan_id", String(filters.plan_id));
  return request(`/api/v1/pets/${petId}/timeline?${query}`);
}

export function getEpisode(episodeId: number): Promise<Episode> { return request(`/api/v1/episodes/${episodeId}`); }
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
export function updateObservationPlan(planId: number, status: ObservationPlanStatus): Promise<ObservationPlan> { return request(`/api/v1/observation-plans/${planId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) }); }
