export interface Observation {
  id: number;
  episode_id: number;
  behavior_type: string;
  description: string;
  source_type: string;
  confidence: number | null;
}

export interface OwnerInterpretation {
  id: number;
  episode_id: number;
  interpretation: string;
}

export interface Episode {
  id: number;
  pet_id: number;
  happened_at: string;
  episode_type: string;
  raw_owner_input: string;
  context: Record<string, unknown> | null;
  created_at: string;
  observations: Observation[];
  owner_interpretations: OwnerInterpretation[];
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
