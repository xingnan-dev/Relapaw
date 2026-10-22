import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EducationalGuidancePanel } from "./EducationalGuidancePanel";

const episode = { id: 2, safety_check: { result: "NORMAL" } } as never;
afterEach(() => vi.restoreAllMocks());

describe("EducationalGuidancePanel", () => {
  it("loads facts, version and citations with retryable states", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ status: "EDUCATIONAL_ONLY", knowledge_version: "local/v1", review_status: "UNREVIEWED_EXAMPLE", review_note: "Not veterinarian approved", fact_summary: ["Observation: rested"], entries: [{ id: "one", species: ["cat"], title: "Observe context", summary: "Record place", topics: [], source: { title: "Local guide", version: "v1", locator: "context", url: null } }], limitations: ["No diagnosis"] }), { status: 200, headers: { "Content-Type": "application/json" } }));
    render(<EducationalGuidancePanel episode={episode} />);
    fireEvent.click(screen.getByRole("button", { name: /查看有来源/ }));
    await waitFor(() => expect(screen.getByText(/Observation: rested/)).toBeInTheDocument());
    expect(screen.getByText(/Local guide/)).toBeInTheDocument();
    expect(screen.getByText(/Not veterinarian approved/)).toBeInTheDocument();
  });
  it("keeps non-normal safety blocked without a request", () => {
    const fetcher = vi.spyOn(globalThis, "fetch");
    render(<EducationalGuidancePanel episode={{ id: 3, safety_check: { result: "NEED_MORE_INFO" } } as never} />);
    expect(screen.getByRole("status")).toHaveTextContent(/保持阻断/);
    expect(fetcher).not.toHaveBeenCalled();
  });
});
