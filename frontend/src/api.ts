import type { Pet, PetCreate, TimelinePage } from "./types";

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

export function getTimeline(petId: number, page = 1, pageSize = 20): Promise<TimelinePage> {
  return request(`/api/v1/pets/${petId}/timeline?page=${page}&page_size=${pageSize}`);
}
