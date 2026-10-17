import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CapabilitiesProvider, useCapabilities } from "./CapabilitiesContext";

function Consumer() {
  const { capabilities, status, retry } = useCapabilities();
  return <div>
    <span>{status}</span>
    <span>{capabilities.ai_analysis_enabled ? "ai-on" : "ai-off"}</span>
    <span>{capabilities.synthetic_data ? capabilities.dataset_version : "not-demo"}</span>
    <button onClick={retry}>retry</button>
  </div>;
}

function response(data: unknown, ok = true) {
  return Promise.resolve({ ok, status: ok ? 200 : 500, json: () => Promise.resolve(data) });
}

beforeEach(() => vi.restoreAllMocks());

describe("CapabilitiesProvider", () => {
  it("loads server capabilities", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({
      environment: "demo",
      synthetic_data: true,
      dataset_version: "relapaw-demo/v1-observe-review-baseline",
      ai_analysis_enabled: false,
      model_qualification: "NOT_QUALIFIED",
    })));

    render(<CapabilitiesProvider><Consumer /></CapabilitiesProvider>);

    expect(await screen.findByText("ready")).toBeInTheDocument();
    expect(screen.getByText("ai-off")).toBeInTheDocument();
    expect(screen.getByText("relapaw-demo/v1-observe-review-baseline")).toBeInTheDocument();
  });

  it("fails closed and can retry", async () => {
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new TypeError("offline"))
      .mockImplementationOnce(() => response({
        environment: "development",
        synthetic_data: false,
        dataset_version: null,
        ai_analysis_enabled: true,
        model_qualification: "NOT_QUALIFIED",
      }));
    vi.stubGlobal("fetch", fetchMock);

    render(<CapabilitiesProvider><Consumer /></CapabilitiesProvider>);

    expect(await screen.findByText("error")).toBeInTheDocument();
    expect(screen.getByText("ai-off")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "retry" }));
    expect(await screen.findByText("ready")).toBeInTheDocument();
    expect(screen.getByText("ai-on")).toBeInTheDocument();
  });
});
