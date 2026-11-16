import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { ApiError, getPet, listPets } from "../api";
import type { Pet } from "../types";

const CURRENT_PET_KEY = "relapaw.currentPetId";

type CurrentPetStatus = "loading" | "available" | "none" | "error";

interface CurrentPetValue {
  pet: Pet | null;
  pets: Pet[];
  status: CurrentPetStatus;
  setCurrentPet: (pet: Pet) => void;
  clearCurrentPet: () => void;
  retry: () => void;
}

const CurrentPetContext = createContext<CurrentPetValue | null>(null);

export function CurrentPetProvider({ children }: { children: ReactNode }) {
  const [pet, setPet] = useState<Pet | null>(null);
  const [pets, setPets] = useState<Pet[]>([]);
  const [status, setStatus] = useState<CurrentPetStatus>("loading");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    async function restore() {
      setStatus("loading");
      const stored = localStorage.getItem(CURRENT_PET_KEY);
      if (stored) {
        const storedId = Number(stored);
        if (!Number.isInteger(storedId) || storedId < 1) {
          localStorage.removeItem(CURRENT_PET_KEY);
        } else {
        try {
          const restored = await getPet(storedId);
          if (!active) return;
          setPet(restored);
          const available = await listPets();
          if (!active) return;
          setPets(available);
          setStatus("available");
          return;
        } catch (error) {
          if (!active) return;
          if (error instanceof ApiError && error.status === 404) {
            localStorage.removeItem(CURRENT_PET_KEY);
          } else {
            setPet(null);
            setStatus("error");
            return;
          }
        }
        }
      }
      try {
        const pets = await listPets();
        if (!active) return;
        if (pets.length > 0) {
          setPets(pets);
          localStorage.setItem(CURRENT_PET_KEY, String(pets[0].id));
          setPet(pets[0]);
          setStatus("available");
        } else {
          setPets([]);
          setPet(null);
          setStatus("none");
        }
      } catch {
        if (!active) return;
        setPet(null);
        setStatus("error");
      }
    }
    void restore();
    return () => { active = false; };
  }, [attempt]);

  const value = useMemo<CurrentPetValue>(() => ({
    pet,
    pets,
    status,
    setCurrentPet(nextPet) {
      localStorage.setItem(CURRENT_PET_KEY, String(nextPet.id));
      setPet(nextPet);
      setPets((current) => current.some((item) => item.id === nextPet.id)
        ? current.map((item) => item.id === nextPet.id ? nextPet : item)
        : [...current, nextPet]);
      setStatus("available");
    },
    clearCurrentPet() {
      localStorage.removeItem(CURRENT_PET_KEY);
      setPet(null);
      setStatus("none");
    },
    retry() { setAttempt((value) => value + 1); },
  }), [pet, pets, status]);

  return <CurrentPetContext.Provider value={value}>{children}</CurrentPetContext.Provider>;
}

export function useCurrentPet(): CurrentPetValue {
  const value = useContext(CurrentPetContext);
  if (!value) throw new Error("useCurrentPet must be used within CurrentPetProvider");
  return value;
}
