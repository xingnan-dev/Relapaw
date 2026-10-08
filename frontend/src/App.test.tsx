import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const pet = { id: 7, name: "Mochi", species: "cat", breed: null, birth_date: null, approximate_age: null, sex: null, neutered: null, created_at: "2026-01-01T00:00:00Z" };

function json(data: unknown, ok = true, status = ok ? 200 : 500) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(data) });
}

function mockApi(options: { pets?: typeof pet[]; storedPetValid?: boolean; storedPetUnavailable?: boolean; timeline?: unknown } = {}) {
  const pets = options.pets ?? [];
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/v1/pets" && init?.method === "POST") return json(pet);
    if (url === "/api/v1/pets") return json(pets);
    if (url === "/api/v1/pets/7") {
      if (options.storedPetUnavailable) return json({}, false, 503);
      return options.storedPetValid === false ? json({}, false, 404) : json(pet);
    }
    if (url.startsWith("/api/v1/pets/7/timeline")) return json(options.timeline ?? { items: [], total: 0, page: 1, page_size: 20, has_more: false });
    return json({}, false);
  });
}

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal("fetch", mockApi());
});

describe("entry flow", () => {
  it("shows onboarding on first use", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Observation ≠ Interpretation" })).toBeInTheDocument();
  });

  it("can skip onboarding and reach pet setup", async () => {
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "跳过" }));
    expect(screen.getByRole("heading", { name: "先认识它" })).toBeInTheDocument();
    expect(localStorage.getItem("relapaw.onboarding.completed")).toBe("true");
  });

  it("shows an honest empty state when there is no pet", async () => {
    localStorage.setItem("relapaw.onboarding.completed", "true");
    render(<App />);
    expect(await screen.findByRole("heading", { name: "从认识它平时的样子开始" })).toBeInTheDocument();
  });

  it("creates a pet and makes it current", async () => {
    localStorage.setItem("relapaw.onboarding.completed", "true");
    vi.stubGlobal("fetch", mockApi());
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "添加我的宠物" }));
    fireEvent.change(screen.getByLabelText("名字"), { target: { value: "Mochi" } });
    fireEvent.change(screen.getByLabelText("物种"), { target: { value: "cat" } });
    fireEvent.click(screen.getByRole("button", { name: "完成建档" }));
    expect(await screen.findByRole("heading", { name: "Mochi" })).toBeInTheDocument();
    expect(localStorage.getItem("relapaw.currentPetId")).toBe("7");
  });

  it("restores an interrupted pet setup draft", async () => {
    localStorage.setItem("relapaw.onboarding.completed", "true");
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "添加我的宠物" }));
    fireEvent.change(screen.getByLabelText("名字"), { target: { value: "Mochi" } });
    fireEvent.change(screen.getByLabelText("物种"), { target: { value: "cat" } });
    fireEvent.click(screen.getByRole("button", { name: "稍后添加" }));
    fireEvent.click(screen.getByRole("button", { name: "添加我的宠物" }));
    expect(screen.getByLabelText("名字")).toHaveValue("Mochi");
    expect(screen.getByLabelText("物种")).toHaveValue("cat");
  });

  it("makes birth date and approximate age mutually exclusive in the form", async () => {
    localStorage.setItem("relapaw.onboarding.completed", "true");
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "添加我的宠物" }));
    const mode = screen.getByLabelText("年龄填写方式");
    expect(screen.queryByLabelText("出生日期")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("大约年龄")).not.toBeInTheDocument();
    fireEvent.change(mode, { target: { value: "birth_date" } });
    expect(screen.getByLabelText("出生日期")).toBeInTheDocument();
    expect(screen.queryByLabelText("大约年龄")).not.toBeInTheDocument();
    fireEvent.change(mode, { target: { value: "approximate_age" } });
    expect(screen.queryByLabelText("出生日期")).not.toBeInTheDocument();
    expect(screen.getByLabelText("大约年龄")).toBeInTheDocument();
  });

  it("restores a valid current pet", async () => {
    localStorage.setItem("relapaw.onboarding.completed", "true");
    localStorage.setItem("relapaw.currentPetId", "7");
    vi.stubGlobal("fetch", mockApi({ pets: [pet] }));
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Mochi" })).toBeInTheDocument();
  });

  it("clears an invalid stored pet", async () => {
    localStorage.setItem("relapaw.onboarding.completed", "true");
    localStorage.setItem("relapaw.currentPetId", "7");
    vi.stubGlobal("fetch", mockApi({ storedPetValid: false }));
    render(<App />);
    expect(await screen.findByRole("heading", { name: "从认识它平时的样子开始" })).toBeInTheDocument();
    expect(localStorage.getItem("relapaw.currentPetId")).toBeNull();
  });

  it("keeps the stored pet when restoration fails temporarily", async () => {
    localStorage.setItem("relapaw.onboarding.completed", "true");
    localStorage.setItem("relapaw.currentPetId", "7");
    vi.stubGlobal("fetch", mockApi({ storedPetUnavailable: true }));
    render(<App />);
    expect(await screen.findByRole("heading", { name: "暂时无法读取宠物资料" })).toBeInTheDocument();
    expect(localStorage.getItem("relapaw.currentPetId")).toBe("7");
  });
});

describe("main shell", () => {
  beforeEach(() => {
    localStorage.setItem("relapaw.onboarding.completed", "true");
    vi.stubGlobal("fetch", mockApi({ pets: [pet] }));
  });

  it.each([["Today", "Mochi"], ["Understand", "它怎么啦？"], ["Timeline", "长期记录"], ["Us", "我们"]])("switches to %s", async (tab, heading) => {
    render(<App />);
    await screen.findByRole("heading", { name: "Mochi" });
    fireEvent.click(screen.getByRole("button", { name: tab }));
    expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
  });

  it("loads timeline with the current pet and separates both lenses", async () => {
    const timeline = { items: [{ id: 1, pet_id: 7, happened_at: "2026-01-01T00:00:00Z", episode_type: "change", raw_owner_input: "A change", context: null, created_at: "2026-01-01T00:00:00Z", observations: [{ id: 1, episode_id: 1, behavior_type: "hiding", description: "Under bed for 20 minutes", source_type: "owner_direct", confidence: null }], owner_interpretations: [{ id: 1, episode_id: 1, interpretation: "Upset with me" }] }], total: 1, page: 1, page_size: 20, has_more: false };
    vi.stubGlobal("fetch", mockApi({ pets: [pet], timeline }));
    render(<App />);
    await screen.findByRole("heading", { name: "Mochi" });
    fireEvent.click(screen.getByRole("button", { name: "Timeline" }));
    fireEvent.click(await screen.findByRole("button", { name: /change/ }));
    expect(screen.getByText("发生了什么")).toBeInTheDocument();
    expect(screen.getByText("你的理解")).toBeInTheDocument();
  });

  it("does not depend on motion to navigate", async () => {
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }));
    render(<App />);
    await screen.findByRole("heading", { name: "Mochi" });
    fireEvent.click(screen.getByRole("button", { name: "Understand" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "它怎么啦？" })).toBeInTheDocument());
  });
});
