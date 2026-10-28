import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AssistantGuidancePanel } from "./AssistantGuidancePanel";
import type { AssistantGuidanceRun, Episode } from "../types";

const episode = { id: 8, safety_check: { result: "NORMAL" } } as Episode;
const run: AssistantGuidanceRun = {
  id: 3, episode_id: 8, request_id: "guide-1", mode: "RECORD_REVIEW", status: "COMPLETED",
  adapter_name: "fake", model_provider: "test", model_name: "fixture", model_version: "v1",
  prompt_contract_version: "assistant-guidance/v1", input_contract_version: "assistant-guidance-input/v1",
  output_contract_version: "assistant-guidance-output/v4", input_snapshot: {}, error_code: null,
  source_episode_updated_at: "2026-10-25T08:00:00Z", created_at: "2026-10-25T08:01:00Z", completed_at: "2026-10-25T08:01:01Z", is_stale: false,
  knowledge_snapshot: { set_version: "controlled/v1", selected_at: "2026-10-25T08:01:00Z", entries: [{
    id: "observe-context", version: "v1", species: ["cat"], title: "记录情境", summary: "记录时间地点", topics: ["context"],
    published_at: "2026-10-25", review_status: "APPROVED", reviewed_at: "2026-10-25", withdrawn_at: null,
    scope: "recording_method_only", source: { title: "受控观察指南", version: "v1", locator: "context", url: null },
  }] },
  normalized_output: {
    contract_version: "assistant-guidance-output/v4", records_show: ["在门口停留 25 秒"], owner_interpretation: ["主人觉得它在等待"],
    possibly_relevant_background: ["相同字段便于比较"], cannot_determine: ["目前不能确定原因"],
    continue_observing: ["继续记录地点和时长"], contact_vet_when: ["出现新的紧急情况时联系兽医"],
    sources_used: [{ citation_id: "knowledge:observe-context@v1", knowledge_id: "observe-context", knowledge_version: "v1", supports_section: "possibly_relevant_background", item_index: 0 }, { citation_id: "knowledge:observe-context@v1", knowledge_id: "observe-context", knowledge_version: "v1", supports_section: "continue_observing", item_index: 0 }],
    record_sources: [{ section: "records_show", item_index: 0, episode_ids: [8] }, { section: "owner_interpretation", item_index: 0, episode_ids: [8] }],
  },
};

afterEach(() => vi.restoreAllMocks());

describe("AssistantGuidancePanel", () => {
  it("renders the required seven user-facing sections and source lineage", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify([run]), { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<AssistantGuidancePanel episode={episode} enabled />);
    expect(await screen.findByText("我从记录中看到什么")).toBeInTheDocument();
    for (const title of ["哪些是你的理解", "可能相关的背景", "目前不能确定什么", "建议继续观察什么", "何时应联系兽医", "使用了哪些资料"]) expect(screen.getByText(title)).toBeInTheDocument();
    expect(screen.getByText(/受控观察指南/)).toBeInTheDocument();
    expect(screen.getByText(/AI 生成，待你核对/)).toBeInTheDocument();
  });

  it("keeps AI-off mode useful and makes no generation request", async () => {
    const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<AssistantGuidancePanel episode={episode} enabled={false} />);
    expect(await screen.findByText(/记录、复评、搜索、媒体、长期记忆和导出仍可正常使用/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "生成辅助整理" })).not.toBeInTheDocument();
    expect(fetcher).not.toHaveBeenCalledWith(expect.anything(), expect.objectContaining({ method: "POST" }));
  });

  it("blocks abnormal safety before any model request", async () => {
    const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<AssistantGuidancePanel episode={{ ...episode, safety_check: { ...episode.safety_check!, result: "ESCALATE_TO_VET" } }} enabled />);
    expect(await screen.findByText(/不会调用外部模型/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "生成辅助整理" })).not.toBeInTheDocument();
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
  });

  it("generates the selected mode without replacing the record", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => Promise.resolve(new Response(JSON.stringify(init?.method === "POST" ? run : []), { status: init?.method === "POST" ? 201 : 200, headers: { "Content-Type": "application/json" } })));
    render(<AssistantGuidancePanel episode={episode} enabled />);
    await screen.findByText("尚无已完成的辅助整理。");
    fireEvent.click(screen.getByRole("button", { name: "生成辅助整理" }));
    expect(await screen.findByText("我从记录中看到什么")).toBeInTheDocument();
  });
});
