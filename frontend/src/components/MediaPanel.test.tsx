import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MediaPanel } from "./MediaPanel";

afterEach(() => vi.restoreAllMocks());
describe("MediaPanel", () => {
  it("shows empty state then persists an uploaded file", async () => {
    const fetcher = vi.spyOn(globalThis, "fetch");
    fetcher.mockResolvedValueOnce(new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } }));
    fetcher.mockResolvedValueOnce(new Response(JSON.stringify({ id: 4, pet_id: 1, episode_id: 2, life_event_id: null, relationship_event_id: null, original_filename: "note.png", media_type: "image/png", byte_size: 8, sha256: "hash", status: "AVAILABLE", observable_facts: null, captured_at: null, owner_caption: null, duration_seconds: null, ai_candidate_observation: null, ai_candidate_status: "NONE", created_at: "2026-10-21T00:00:00Z", updated_at: "2026-10-21T00:00:00Z", revisions: [{ id: 1, revision_number: 1, captured_at: null, owner_caption: null, ai_candidate_observation: null, ai_candidate_status: "NONE", change_summary: "上传附件", created_at: "2026-10-21T00:00:00Z" }] }), { status: 201, headers: { "Content-Type": "application/json" } }));
    render(<MediaPanel episodeId={2} />);
    await waitFor(() => expect(screen.getByText(/还没有照片或视频/)).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText("添加照片或视频"), { target: { files: [new File(["image"], "note.png", { type: "image/png" })] } });
    await waitFor(() => expect(screen.getByText("note.png")).toBeInTheDocument());
    expect(screen.getByRole("status")).toHaveTextContent(/绑定到这条具体记录/);
    expect(screen.getByRole("img", { name: /note.png/ })).toBeInTheDocument();
    expect(screen.getByText(/修改历史（1）/)).toBeInTheDocument();
  });
});
