export interface Observation {
  id: number;
  episode_id: number;
  behavior_type: string;
  description: string;
  source_type: string;
  confidence: number | null;
  measured_value: number | null;
  unit: string | null;
  created_at: string;
  updated_at: string;
}

export interface OwnerInterpretation {
  id: number;
  episode_id: number;
  interpretation: string;
  created_at: string;
  updated_at: string;
}

export type SafetyStatus = "NORMAL" | "NEED_MORE_INFO" | "ESCALATE_TO_VET";
export type DangerSignal = "breathing_difficulty" | "prolonged_seizure" | "collapse_or_unable_to_stand" | "severe_bleeding" | "suspected_poisoning" | "other_urgent_concern";
export type FollowUpStatus = "PENDING" | "COMPLETED" | "CANCELLED";
export type FollowUpOutcome = "PERSISTING" | "IMPROVED" | "WORSENED" | "RESOLVED" | "NEW_SIGNS";
export type ObservationPlanStatus = "DRAFT" | "ACTIVE" | "COMPLETED" | "CANCELLED";
export type VeterinaryEscalationStatus = "OPEN" | "SHARED_WITH_VET" | "CLOSED";
export interface VeterinaryEscalation { id: number; episode_id: number; reason: string; status: VeterinaryEscalationStatus; vet_brief: string | null; }
export interface ObservationPlanItem { id: number; plan_id: number; label: string; description: string | null; sort_order: number; is_required: boolean; created_at: string; }
export interface ObservationPlan { id: number; pet_id: number; status: ObservationPlanStatus; start_at: string | null; end_at: string | null; goal: string; items_to_observe: Array<Record<string, unknown>>; items: ObservationPlanItem[]; }

export interface FollowUp {
  id: number;
  source_episode_id: number;
  result_episode_id: number | null;
  scheduled_at: string;
  status: FollowUpStatus;
  outcome: FollowUpOutcome | null;
  created_at: string;
  completed_at: string | null;
  source_episode_type?: string;
  source_raw_owner_input?: string;
  source_happened_at?: string;
  timing_status?: "DUE" | "OVERDUE" | "UPCOMING";
}

export interface SafetyCheck {
  id: number;
  episode_id: number;
  result: SafetyStatus;
  danger_signals: DangerSignal[];
  other_concern: string | null;
  acknowledged_at: string;
  created_at: string;
}

export interface EvidenceReference {
  id: number;
  episode_id: number;
  source_type: "RAW_OWNER_INPUT" | "OBSERVATION" | "OWNER_INTERPRETATION" | "FOLLOW_UP";
  source_id: number | null;
  field_path: string;
  observed_at: string;
  recorded_at: string;
  created_at: string;
}

export interface Episode {
  id: number;
  pet_id: number;
  happened_at: string;
  episode_type: string;
  raw_owner_input: string;
  context: Record<string, unknown> | null;
  duration_seconds: number | null;
  frequency_count: number | null;
  intensity: number | null;
  location: string | null;
  trigger_context: string | null;
  created_at: string;
  updated_at: string;
  observations: Observation[];
  owner_interpretations: OwnerInterpretation[];
  safety_check: SafetyCheck | null;
  evidence_references: EvidenceReference[];
  plan_links: { id: number; episode_id: number; plan_id: number; created_at: string }[];
  veterinary_escalations: VeterinaryEscalation[];
  scheduled_follow_ups: FollowUp[];
  result_of_follow_up: FollowUp | null;
}

export interface EpisodeUpdate {
  happened_at: string;
  episode_type: string;
  raw_owner_input: string;
  context: Record<string, unknown> | null;
  duration_seconds: number | null;
  frequency_count: number | null;
  intensity: number | null;
  location: string | null;
  trigger_context: string | null;
  observations: Array<Omit<Observation, "id" | "episode_id" | "created_at" | "updated_at">>;
  owner_interpretations: Array<{ interpretation: string }>;
}

export interface TimelineFilters { from?: string; to?: string; episode_type?: string; plan_id?: number; }

export interface CompleteEpisodeCreate {
  pet_id: number;
  happened_at: string;
  episode_type: string;
  raw_owner_input: string;
  duration_seconds?: number;
  frequency_count?: number;
  intensity?: number;
  location?: string;
  trigger_context?: string;
  plan_id?: number;
  observations: Array<{ behavior_type: string; description: string; source_type: "owner_direct" }>;
  owner_interpretations: Array<{ interpretation: string }>;
  safety_check: {
    result: SafetyStatus;
    danger_signals: DangerSignal[];
    other_concern?: string;
    acknowledged_at: string;
  };
}

export interface FollowUpComplete {
  outcome: FollowUpOutcome;
  happened_at: string;
  episode_type: string;
  raw_owner_input: string;
  observations: Array<{ behavior_type: string; description: string; source_type: "owner_direct" }>;
  owner_interpretations: Array<{ interpretation: string }>;
  safety_check: { result: SafetyStatus; danger_signals: DangerSignal[]; acknowledged_at: string };
}

export interface TimelinePage {
  items: Episode[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface Pet {
  id: number;
  name: string;
  species: string;
  breed: string | null;
  birth_date: string | null;
  approximate_age: string | null;
  sex: string | null;
  neutered: boolean | null;
  created_at: string;
}

export interface PetCreate {
  name: string;
  species: string;
  breed?: string;
  birth_date?: string;
  approximate_age?: string;
  sex?: string;
  neutered?: boolean;
}
