import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { UnderstandingPanel } from "./UnderstandingPanel";
import type { AnalysisRun, Episode } from "../types";

function json(data: unknown, ok = true, status = ok ? 200 : 500) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(data) });
}

const episode: Episode = {
  id: 21, pet_id: 7, happened_at: "2026-10-09T01:30:00Z", episode_type: "behavior_change",
  raw_owner_input: "她在门口停下，我不确定原因。", context: null, duration_seconds: null,
  frequency_count: null, intensity: null, location: null, trigger_context: null,
  created_at: "2026-10-09T01:30:00Z", updated_at: "2026-10-09T01:35:00Z",
  observations: [{ id: 31, episode_id: 21, behavior_type: "pause", description: "在门口停留 25 秒", source_type: "owner_direct", confidence: null, measured_value: 25, unit: "seconds", created_at: "2026-10-09T01:30:00Z", updated_at: "2026-10-09T01:30:00Z" }],
  owner_interpretations: [{ id: 41, episode_id: 21, interpretation: "我觉得她可能犹豫", created_at: "2026-10-09T01:30:00Z", updated_at: "2026-10-09T01:30:00Z" }],
  safety_check: { id: 51, episode_id: 21, result: "NORMAL", danger_signals: [], other_concern: null, acknowledged_at: "2026-10-09T01:31:00Z", created_at: "2026-10-09T01:31:00Z" },
  evidence_references: [], plan_links: [], veterinary_escalations: [], scheduled_follow_ups: [], result_of_follow_up: null,
};

const completedRun: AnalysisRun = {
  id: 61, episode_id: 21, request_id: "request-1", status: "COMPLETED", adapter_name: "test-fake",
  model_provider: "test", model_name: "contract-fixture", model_version: "1",
  prompt_contract_version: "text-understanding/v1", input_contract_version: "understanding-input/v1", output_contract_version: "understanding-output/v1",
  input_snapshot: {}, normalized_output: {}, error_code: null, source_episode_updated_at: episode.updated_at,
  created_at: "2026-10-09T01:36:00Z", completed_at: "2026-10-09T01:36:00Z", is_stale: false,
  claims: [{ id: 71, analysis_run_id: 61, claim_type: "behavior_hypothesis", statement: "一种可能解释与当时环境有关。", confidence_label: "LOW", status: "PROPOSED", created_at: "2026-10-09T01:36:00Z",
    evidence_references: [{ id: 81, claim_id: 71, evidence_reference_id: 1, source_type: "RAW_OWNER_INPUT", source_id: null, field_path: "raw_owner_input", observed_at: episode.happened_at, recorded_at: episode.created_at, excerpt: episode.raw_owner_input, role: "SUPPORTS", created_at: "2026-10-09T01:36:00Z" }],
    uncertainties: [{ id: 91, claim_id: 71, kind: "LIMITED_OBSERVATION", description: "只有一次短时观察。", created_at: "2026-10-09T01:36:00Z" }], confirmations: [] }],
};

beforeEach(() => vi.restoreAllMocks());

describe("text Understanding panel", () => {
  it("shows separated inputs, loading, completed contract metadata and saves a decision", async () => {
    let resolveRun!: (value: Awaited<ReturnType<typeof json>>) => void;
    const pending = new Promise<Awaited<ReturnType<typeof json>>>((resolve) => { resolveRun = resolve; });
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/analysis-runs") && init?.method === "POST") return pending;
      if (url.endsWith("/analysis-runs")) return json([]);
      if (url === "/api/v1/claims/71/confirmations") return json({ id: 101, claim_id: 71, decision: "CONFIRMED", note: null, created_at: "2026-10-09T01:37:00Z" }, true, 201);
      return json({}, false, 404);
    });
    vi.stubGlobal("fetch", fetchMock); render(<UnderstandingPanel episode={episode} />);
    expect(await screen.findByText("Raw Input")).toBeInTheDocument();
    expect(screen.getByText("Observation")).toBeInTheDocument(); expect(screen.getByText("Owner Interpretation")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "开始文本分析" }));
    expect(screen.getByRole("button", { name: "正在分析…" })).toBeDisabled();
    resolveRun(await json(completedRun, true, 201));
    expect(await screen.findByText("分析完成。请逐条确认或拒绝；确认前均不是事实。")).toBeInTheDocument();
    const run = screen.getByLabelText("AnalysisRun 61");
    expect(run).toHaveTextContent("一种可能解释"); expect(run).toHaveTextContent("SUPPORTS"); expect(run).toHaveTextContent("LIMITED_OBSERVATION");
    expect(run).toHaveTextContent("test / contract-fixture / 1"); expect(run).toHaveTextContent("understanding-output/v1");
    fireEvent.click(within(run).getByRole("button", { name: "确认此 Claim" }));
    expect(await within(run).findByText("用户已确认；这是用户决定，不会改写原始记录。")).toBeInTheDocument();
    expect(within(run).getByText("模型生成、用户已确认")).toBeInTheDocument();
    expect(within(run).queryByText("模型生成、尚未确认")).not.toBeInTheDocument();
  });

  it("shows MODEL_NOT_CONFIGURED and its audited failed run without invented claims", async () => {
    const failed = { ...completedRun, id: 62, status: "FAILED" as const, adapter_name: "disabled", model_provider: "none", model_name: "none", model_version: "none", error_code: "MODEL_NOT_CONFIGURED", normalized_output: null, claims: [] };
    let posted = false;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === "POST") { posted = true; return json({ error: { code: "MODEL_NOT_CONFIGURED", message: "not configured" } }, false, 503); }
      return json(posted ? [failed] : []);
    }));
    render(<UnderstandingPanel episode={episode} />); await screen.findByText("尚无 AnalysisRun。");
    fireEvent.click(screen.getByRole("button", { name: "开始文本分析" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("MODEL_NOT_CONFIGURED");
    expect(await screen.findByLabelText("AnalysisRun 62")).toHaveTextContent("没有可确认的模型结果");
    expect(screen.queryByText("一种可能解释与当时环境有关。")).not.toBeInTheDocument();
  });

  it("distinguishes invalid output and offers retry", async () => {
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => init?.method === "POST"
      ? json({ error: { code: "MODEL_OUTPUT_INVALID", message: "invalid" } }, false, 502)
      : json([])));
    render(<UnderstandingPanel episode={episode} />); await screen.findByText("尚无 AnalysisRun。");
    fireEvent.click(screen.getByRole("button", { name: "开始文本分析" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("未通过契约校验");
    expect(screen.getByRole("button", { name: "重试分析" })).toBeInTheDocument();
  });

  it("shows a network error and retries with the same request id", async () => {
    let attempts = 0;
    const bodies: string[] = [];
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === "POST") {
        attempts += 1; bodies.push(String(init.body));
        return attempts === 1 ? Promise.reject(new TypeError("offline")) : json(completedRun, true, 201);
      }
      return json([]);
    }));
    render(<UnderstandingPanel episode={episode} />); await screen.findByText("尚无 AnalysisRun。");
    fireEvent.click(screen.getByRole("button", { name: "开始文本分析" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("网络请求失败");
    fireEvent.click(screen.getByRole("button", { name: "重试分析" }));
    expect(await screen.findByText("分析完成。请逐条确认或拒绝；确认前均不是事实。")).toBeInTheDocument();
    expect(JSON.parse(bodies[0]).request_id).toBe(JSON.parse(bodies[1]).request_id);
  });

  it.each([
    ["MODEL_AUTHENTICATION_FAILED", "认证或权限配置无效"],
    ["MODEL_TIMEOUT", "响应超时"],
    ["MODEL_RATE_LIMITED", "达到调用限制"],
    ["MODEL_PROVIDER_UNAVAILABLE", "暂时不可用"],
  ])("shows a safe message for provider error %s", async (code, message) => {
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => init?.method === "POST"
      ? json({ error: { code, message: "provider detail must not be displayed" } }, false, 503)
      : json([])));
    render(<UnderstandingPanel episode={episode} />); await screen.findByText("尚无 AnalysisRun。");
    fireEvent.click(screen.getByRole("button", { name: "开始文本分析" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.getByRole("alert")).not.toHaveTextContent("provider detail");
  });

  it("preserves completed content when a confirmation has a network error", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => String(input).includes("confirmations") ? Promise.reject(new TypeError("offline")) : json([completedRun])));
    render(<UnderstandingPanel episode={episode} />); const run = await screen.findByLabelText("AnalysisRun 61");
    fireEvent.click(within(run).getByRole("button", { name: "拒绝此 Claim" }));
    expect(await within(run).findByRole("alert")).toHaveTextContent("分析结果与既有决定均保留");
    expect(within(run).getByText("一种可能解释与当时环境有关。")).toBeInTheDocument();
    expect(within(run).getByRole("button", { name: "拒绝此 Claim" })).toBeInTheDocument();
  });

  it("blocks non-normal safety and displays stale history", async () => {
    const stale = { ...completedRun, is_stale: true };
    vi.stubGlobal("fetch", vi.fn(() => json([stale])));
    render(<UnderstandingPanel episode={{ ...episode, safety_check: { ...episode.safety_check!, result: "ESCALATE_TO_VET" } }} />);
    expect(await screen.findByText(/stale · 输入快照已过期/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "开始文本分析" })).toBeDisabled();
    expect(screen.getByText(/Safety blocked/)).toBeInTheDocument();
  });
});
