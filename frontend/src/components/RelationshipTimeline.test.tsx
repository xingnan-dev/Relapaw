import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RelationshipTimeline } from "./RelationshipTimeline";
import type { Pet, RelationshipEvent } from "../types";

function json(data: unknown, ok = true, status = ok ? 200 : 500) { return Promise.resolve({ ok, status, json: () => Promise.resolve(data) }); }
const mochi: Pet = { id: 1, name: "Mochi", species: "cat", breed: null, birth_date: null, approximate_age: null, sex: null, neutered: null, created_at: "2026-10-01T00:00:00Z", archived_at: null };
const nori: Pet = { ...mochi, id: 2, name: "Nori" };
const relationship: RelationshipEvent = { id: 5, owner_user_id: "local", relationship_kind: "PET_PET", happened_at: "2026-10-20T08:00:00Z", observation_type: "SHARED_REST", observation_text: "Both rested on opposite ends of the sofa.", source_episode_id: 9, created_at: "2026-10-20T08:01:00Z", updated_at: "2026-10-20T08:01:00Z", current_owner_interpretation: "I wondered whether the room felt familiar.", participants: [{ id: 1, pet_id: 1 }, { id: 2, pet_id: 2 }], interpretations: [{ id: 1, interpretation: "I wondered whether the room felt familiar.", created_at: "2026-10-20T08:01:00Z" }], revisions: [{ id: 1, revision_number: 1, relationship_kind: "PET_PET", happened_at: "2026-10-20T08:00:00Z", participant_pet_ids: [1, 2], observation_type: "SHARED_REST", observation_text: "Both rested on opposite ends of the sofa.", owner_interpretation: "I wondered whether the room felt familiar.", source_episode_id: 9, created_at: "2026-10-20T08:01:00Z" }] };

beforeEach(() => vi.restoreAllMocks());
describe("relationship timeline", () => {
  it("keeps observation, owner interpretation, source and revisions visibly separate", async () => {
    let current = relationship;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/pets/1/relationship-events")) return json([current]);
      if (url.endsWith("/relationship-events/5") && init?.method === "PUT") {
        const body = JSON.parse(String(init.body));
        current = { ...current, observation_text: body.observation_text, revisions: [...current.revisions, { ...current.revisions[0], id: 2, revision_number: 2, observation_text: body.observation_text, owner_interpretation: body.owner_interpretation }] };
        return json(current);
      }
      return json({}, false, 404);
    }));
    render(<RelationshipTimeline pet={mochi} pets={[mochi, nori]} />);
    const card = (await screen.findAllByText(/Both rested/))[0].closest<HTMLElement>(".memory-card")!;
    expect(within(card).getByText(/主人 Interpretation/)).toBeInTheDocument();
    expect(within(card).getAllByText(/Episode #9/).length).toBeGreaterThan(0);
    expect(within(card).getByText(/系统提示：无/)).toBeInTheDocument();
    fireEvent.click(within(card).getByRole("button", { name: "编辑关系事件" }));
    fireEvent.change(screen.getByLabelText("客观 Observation"), { target: { value: "Both remained two metres apart for twelve minutes." } });
    fireEvent.click(screen.getByRole("button", { name: "保存修订" }));
    expect(await screen.findByText(/two metres apart/)).toBeInTheDocument();
    expect(screen.getByText(/修订历史（2）/)).toBeInTheDocument();
  });

  it("requires a second participant for pet-to-pet records", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => String(input).endsWith("/pets/1/relationship-events") ? json([]) : json({}, false, 404)));
    render(<RelationshipTimeline pet={mochi} pets={[mochi]} />);
    await screen.findByText(/尚无关系事件/);
    fireEvent.change(screen.getByLabelText("关系类型"), { target: { value: "PET_PET" } });
    fireEvent.change(screen.getByLabelText("客观 Observation"), { target: { value: "Mochi rested alone." } });
    fireEvent.click(screen.getByRole("button", { name: "记录关系事件" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("需要选择另一只宠物");
  });
});
