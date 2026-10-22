import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MediaPanel } from "./MediaPanel";

afterEach(() => vi.restoreAllMocks());
describe("MediaPanel", () => {
  it("shows empty state then persists an uploaded file", async () => {
    const fetcher = vi.spyOn(globalThis, "fetch");
    fetcher.mockResolvedValueOnce(new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } }));
    fetcher.mockResolvedValueOnce(new Response(JSON.stringify({ id: 4, episode_id: 2, original_filename: "note.txt", media_type: "text/plain", byte_size: 4, sha256: "hash", status: "AVAILABLE", observable_facts: null, created_at: "2026-10-21T00:00:00Z" }), { status: 201, headers: { "Content-Type": "application/json" } }));
    render(<MediaPanel episodeId={2} />);
    await waitFor(() => expect(screen.getByText(/还没有附件/)).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText("添加附件"), { target: { files: [new File(["note"], "note.txt", { type: "text/plain" })] } });
    await waitFor(() => expect(screen.getByText("note.txt")).toBeInTheDocument());
    expect(screen.getByRole("status")).toHaveTextContent(/已保存到本地/);
  });
});
