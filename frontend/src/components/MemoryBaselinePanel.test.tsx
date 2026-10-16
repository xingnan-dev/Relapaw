import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryBaselinePanel } from "./MemoryBaselinePanel";
import type { BaselineSnapshot, MemoryCandidate } from "../types";

function json(data: unknown, ok = true, status = ok ? 200 : 500) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(data) });
}

const candidate: MemoryCandidate = {
  id: 4, pet_id: 7, claim_id: 71, claim_snapshot: { claim_type: "POSSIBLE_EXPLANATION", statement: "一种经用户确认的可能解释。", confidence_label: "LOW" },
  evidence_snapshot: [], uncertainty_snapshot: [], model_snapshot: {}, source_episode_updated_at: "2026-10-11T08:00:00Z", created_at: "2026-10-11T08:00:00Z",
  is_stale: false, state: "ELIGIBLE", decisions: [],
};

const snapshot: BaselineSnapshot = {
  id: 8, pet_id: 7, window: "7d", window_start: "2026-10-05T00:00:00Z", window_end: "2026-10-12T00:00:00Z", as_of: "2026-10-12T00:00:00Z",
  status: "READY", algorithm_version: "quantitative-baseline/v1", source_fingerprint: "abc", sample_count: 3, created_at: "2026-10-12T00:00:01Z", is_stale: false,
  metrics_json: [{ key: "duration_seconds:walk:seconds", field: "duration_seconds", behavior_type: "walk", unit: "seconds", count: 3, min: 10, max: 30, median: 20, status: "READY", trend: null }],
  evidences: [{ id: 9, snapshot_id: 8, episode_id: 21, observation_id: null, source_type: "EPISODE", window_segment: "CURRENT", metric_key: "duration_seconds:walk:seconds", field_path: "duration_seconds", value_snapshot: 20, source_snapshot: {}, observed_at: "2026-10-10T00:00:00Z", source_updated_at: "2026-10-10T00:00:00Z", created_at: "2026-10-12T00:00:01Z" }],
};

beforeEach(() => vi.restoreAllMocks());

describe("memory and baseline closure", () => {
  it("keeps manual, memory and quantitative data distinct and drills into frozen evidence", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/baseline")) return json({ id: 2, pet_id: 7, social_behavior: { greeting: "calm" }, activity_pattern: null, feeding_pattern: null, resting_pattern: null, handling_preference: null, hiding_pattern: null });
      if (url.endsWith("/memory-candidates")) return json([candidate]);
      if (url.includes("baseline-snapshots/latest")) return json(snapshot);
      return json({}, false, 404);
    }));
    render(<MemoryBaselinePanel petId={7} />);
    expect(await screen.findByText("人工档案 Baseline")).toBeInTheDocument();
    expect(await screen.findByText(/一种经用户确认/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "7 天" })).toHaveAttribute("aria-pressed", "true");
    expect((await screen.findAllByText(/样本 3/)).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByText("查看来源（1）"));
    expect(screen.getByText(/EPISODE · duration_seconds/)).toBeInTheDocument();
  });

  it("preserves a candidate and reuses its request id after a failed include", async () => {
    const bodies: string[] = [];
    let decisions = 0;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/baseline")) return json({ error: { code: "NOT_FOUND" } }, false, 404);
      if (url.endsWith("/memory-candidates")) return json([candidate]);
      if (url.includes("baseline-snapshots/latest")) return json({ error: { code: "BASELINE_SNAPSHOT_NOT_FOUND" } }, false, 404);
      if (url.includes("/decisions") && init?.method === "POST") {
        bodies.push(String(init.body)); decisions += 1;
        return decisions === 1 ? Promise.reject(new TypeError("offline")) : json({ ...candidate, state: "ACTIVE", decisions: [{ id: 1, candidate_id: 4, request_id: JSON.parse(bodies[0]).request_id, decision: "INCLUDE", note: null, created_at: "2026-10-12T00:01:00Z" }] }, true, 201);
      }
      return json({}, false, 404);
    }));
    render(<MemoryBaselinePanel petId={7} />);
    const card = (await screen.findByText(/一种经用户确认/)).closest<HTMLElement>(".memory-card")!;
    fireEvent.click(within(card).getByRole("button", { name: "纳入长期记忆" }));
    expect(await within(card).findByRole("alert")).toHaveTextContent("当前状态均已保留");
    expect(within(card).getByText(/一种经用户确认/)).toBeInTheDocument();
    fireEvent.click(within(card).getByRole("button", { name: "纳入长期记忆" }));
    await waitFor(() => expect(within(card).getByText("已纳入")).toBeInTheDocument());
    expect(JSON.parse(bodies[0]).request_id).toBe(JSON.parse(bodies[1]).request_id);
  });

  it("supports withdraw and re-include while stale candidates cannot be newly included", async () => {
    let current = { ...candidate, state: "ACTIVE" as const, decisions: [{ id: 1, candidate_id: 4, request_id: "include-1", decision: "INCLUDE" as const, note: null, created_at: "2026-10-12T00:01:00Z" }] };
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/baseline")) return json({ error: {} }, false, 404);
      if (url.endsWith("/memory-candidates")) return json([current, { ...candidate, id: 5, is_stale: true, state: "STALE" }]);
      if (url.includes("baseline-snapshots/latest")) return json({ error: {} }, false, 404);
      if (url.includes("/decisions") && init?.method === "POST") {
        const decision = JSON.parse(String(init.body)).decision;
        current = { ...current, state: decision === "WITHDRAW" ? "WITHDRAWN" : "ACTIVE", decisions: [...current.decisions, { id: current.decisions.length + 1, candidate_id: 4, request_id: "next", decision, note: null, created_at: "2026-10-12T00:02:00Z" }] } as typeof current;
        return json(current, true, 201);
      }
      return json({}, false, 404);
    }));
    render(<MemoryBaselinePanel petId={7} />);
    const activeCard = (await screen.findByText("候选 #4")).closest<HTMLElement>(".memory-card")!;
    fireEvent.click(within(activeCard).getByRole("button", { name: "撤回长期记忆" }));
    expect(await within(activeCard).findByRole("button", { name: "重新纳入长期记忆" })).toBeInTheDocument();
    fireEvent.click(within(activeCard).getByRole("button", { name: "重新纳入长期记忆" }));
    expect(await within(activeCard).findByRole("button", { name: "撤回长期记忆" })).toBeInTheDocument();
    const staleCard = screen.getByText("候选 #5").closest<HTMLElement>(".memory-card")!;
    expect(within(staleCard).getByText(/不可重新纳入/)).toBeInTheDocument();
    expect(within(staleCard).queryByRole("button", { name: /纳入长期记忆/ })).not.toBeInTheDocument();
  });

  it("shows insufficient data and stale explicitly rather than inventing a trend", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/baseline")) return json({ error: {} }, false, 404);
      if (url.endsWith("/memory-candidates")) return json([]);
      if (url.includes("baseline-snapshots/latest")) return json({ ...snapshot, status: "INSUFFICIENT_DATA", sample_count: 2, metrics_json: [], is_stale: true });
      return json({}, false, 404);
    }));
    render(<MemoryBaselinePanel petId={7} />);
    expect(await screen.findByText("来源已变化")).toBeInTheDocument();
    expect(screen.getByText(/7 天快照 · 数据不足/)).toBeInTheDocument();
    expect(screen.getByText("样本不足，不生成趋势。")).toBeInTheDocument();
  });

  it("preserves the current snapshot when recompute fails", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/baseline")) return json({ error: {} }, false, 404);
      if (url.endsWith("/memory-candidates")) return json([]);
      if (url.includes("baseline-snapshots/recompute") && init?.method === "POST") return Promise.reject(new TypeError("offline"));
      if (url.includes("baseline-snapshots/latest")) return json(snapshot);
      return json({}, false, 404);
    }));
    render(<MemoryBaselinePanel petId={7} />);
    expect((await screen.findAllByText(/样本 3/)).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "按当前数据重算" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("当前已显示的快照保持不变");
    expect(screen.getAllByText(/样本 3/).length).toBeGreaterThan(0);
  });
});
