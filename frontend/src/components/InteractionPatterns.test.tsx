import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { InteractionPatterns } from "./InteractionPatterns";
import type { InteractionPatternCandidate, Pet, RelationshipEvent } from "../types";

function json(data: unknown, ok = true, status = ok ? 200 : 500) { return Promise.resolve({ ok, status, json: () => Promise.resolve(data) }); }
const pet: Pet = { id: 1, name: "Mochi", species: "cat", breed: null, birth_date: null, approximate_age: null, sex: null, neutered: null, created_at: "2026-10-01T00:00:00Z", archived_at: null };
function relationship(id: number, day: string, text: string): RelationshipEvent { return { id, owner_user_id: "owner", relationship_kind: "OWNER_PET", happened_at: `2026-10-${day}T08:00:00Z`, observation_type: "OWNER_INTERACTION", observation_text: text, source_episode_id: null, created_at: `2026-10-${day}T08:00:00Z`, updated_at: `2026-10-${day}T08:00:00Z`, current_owner_interpretation: null, participants: [{ id, pet_id: 1 }], interpretations: [], revisions: [] }; }
const events = [relationship(1, "01", "主动靠近并停留。"), relationship(2, "08", "主动走近并坐下。"), relationship(3, "15", "停在门边，没有靠近。")];
const candidate: InteractionPatternCandidate = { id: 9, relationship_kind: "OWNER_PET", participant_pet_ids: [1], initial_self_report: "我觉得傍晚更常靠近。", title: "傍晚主动靠近", observable_pattern: "两次主动靠近。", counterevidence_summary: "一次没有靠近。", evidence_count: 3, coverage_start: events[0].happened_at, coverage_end: events[2].happened_at, generator_version: "interaction-pattern/owner-reviewed-v1", confidence_limit: "不能代表固定性格。", status: "ELIGIBLE", memory_status: "NOT_INCLUDED", created_at: events[2].happened_at, updated_at: events[2].happened_at, evidences: events.map((item, index) => ({ id: item.id, relationship_event_id: item.id, role: index === 2 ? "CONTRADICTS" : "SUPPORTS", observation_type: item.observation_type, observation_snapshot: item.observation_text, happened_at: item.happened_at })), revisions: [{ id: 1, revision_number: 1, title: "傍晚主动靠近", observable_pattern: "两次主动靠近。", counterevidence_summary: "一次没有靠近。", confidence_limit: "不能代表固定性格。", change_summary: "建立候选", created_at: events[2].happened_at }], decisions: [] };

beforeEach(() => vi.restoreAllMocks());
describe("interaction patterns", () => {
  it("keeps three layers, contradictions and memory consent separate", async () => {
    let patterns: InteractionPatternCandidate[] = [];
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/pets/1/interaction-patterns")) return json(patterns);
      if (url.endsWith("/interaction-patterns") && init?.method === "POST") { patterns = [candidate]; return json(candidate, true, 201); }
      if (url.endsWith("/interaction-patterns/9/decisions") && init?.method === "POST") { const action = JSON.parse(String(init.body)).action; const updated = { ...candidate, status: action === "CONFIRM" ? "CONFIRMED" as const : candidate.status, decisions: action === "CONFIRM" ? [{ id: 1, action: "CONFIRM" as const, previous_status: "ELIGIBLE", resulting_status: "CONFIRMED", previous_memory_status: "NOT_INCLUDED", resulting_memory_status: "NOT_INCLUDED", note: null, created_at: candidate.updated_at }] : [] }; patterns = [updated]; return json(updated); }
      return json({}, false, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<InteractionPatterns pet={pet} pets={[pet]} events={events} />);
    await screen.findByText(/尚无候选/);
    fireEvent.click(screen.getByText("根据已有记录建立候选"));
    fireEvent.change(screen.getByLabelText("记录 1 的作用"), { target: { value: "SUPPORTS" } });
    fireEvent.change(screen.getByLabelText("记录 2 的作用"), { target: { value: "SUPPORTS" } });
    fireEvent.change(screen.getByLabelText("记录 3 的作用"), { target: { value: "CONTRADICTS" } });
    fireEvent.change(screen.getByLabelText("我最初怎么想（可选）"), { target: { value: "我觉得傍晚更常靠近。" } });
    fireEvent.change(screen.getByLabelText("候选标题"), { target: { value: candidate.title } });
    fireEvent.change(screen.getByLabelText("具体可观察的重复现象"), { target: { value: candidate.observable_pattern } });
    fireEvent.change(screen.getByLabelText("反例或仍不一致的地方"), { target: { value: candidate.counterevidence_summary } });
    fireEvent.click(screen.getByRole("button", { name: "建立候选" }));
    const card = (await screen.findByText(candidate.title)).closest<HTMLElement>(".pattern-card")!;
    expect(within(card).getByText(/一次没有靠近/)).toBeInTheDocument();
    expect(within(card).getByText(/未纳入长期变化/)).toBeInTheDocument();
    expect(within(card).queryByRole("button", { name: "纳入长期变化" })).not.toBeInTheDocument();
    fireEvent.click(within(card).getByRole("button", { name: "确认候选" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/interaction-patterns/9/decisions"), expect.objectContaining({ method: "POST" })));
  });
});
